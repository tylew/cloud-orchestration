"""Terraform HCL generation from an Envelope."""

import logging
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

log = logging.getLogger(__name__)

from packages.core.schemas.base import Envelope, BaseNode
from packages.core.schemas.configs.bigquery import BqTable, BigQueryTableConfig
from packages.core.schemas.configs.cloud_sql import SqlDatabase, CloudSqlDatabaseConfig
from packages.core.schemas.enums import CHILD_PARENT_MAP
from packages.core.registry import REGISTRY
from packages.core.terraform.resolver import resolve_node_ref, topological_sort
from packages.core.validation import reconstruct_collection_tree


_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def _collect_ttl_collections(collections, prefix=""):
    """Flatten collection tree into list of dicts with full path and ttl_field for TTL generation."""
    result = []
    for coll in collections:
        full_path = coll.path if not prefix else f"{prefix}/{coll.path}"
        if coll.ttl_field:
            result.append({"path": full_path, "collection_name": coll.path, "ttl_field": coll.ttl_field})
        result.extend(_collect_ttl_collections(coll.subcollections, full_path))
    return result


# Set of child types that are embedded in parent TF templates (not standalone)
_EMBEDDED_CHILD_TYPES = {"bigquery_table", "cloud_sql_database"}


def attach_child_resources(nodes: list[BaseNode]) -> None:
    """Attach flat child resources to parent config for TF template rendering.

    Groups bigquery_table children into parent BigQueryConfig.tables[],
    and cloud_sql_database children into parent CloudSqlConfig.databases[].
    Unlike Firestore's recursive tree, BQ and SQL are flat (max 2 levels).
    """
    def _get_slug(n: BaseNode) -> str | None:
        # slug may be an extra field (not defined on BaseNode)
        if hasattr(n, 'model_extra') and n.model_extra:
            return n.model_extra.get('slug')
        return getattr(n, 'slug', None)

    slug_map = {}
    for n in nodes:
        s = _get_slug(n)
        if s:
            slug_map[s] = n

    # Clear parent arrays to prevent duplicate attachment
    for node in nodes:
        ntype = node.type.value if hasattr(node.type, 'value') else str(node.type)
        if ntype == "bigquery" and hasattr(node.config, 'tables'):
            node.config.tables = []
        elif ntype == "cloud_sql" and hasattr(node.config, 'databases'):
            node.config.databases = []

    for node in nodes:
        cfg = node.config
        parent_ref = getattr(cfg, 'parentRef', None)
        if not parent_ref:
            continue

        parent = slug_map.get(parent_ref)
        if not parent:
            continue

        ntype = node.type.value if hasattr(node.type, 'value') else str(node.type)

        if ntype == "bigquery_table":
            table = BqTable(
                table_id=cfg.name,
                columns=cfg.columns,
                description=cfg.description,
                time_partitioning=cfg.time_partitioning,
                range_partitioning=cfg.range_partitioning,
                clustering=cfg.clustering or None,
                deletion_protection=cfg.deletion_protection,
            )
            if hasattr(parent.config, 'tables'):
                parent.config.tables.append(table)

        elif ntype == "cloud_sql_database":
            db = SqlDatabase(
                name=cfg.name,
                charset=cfg.charset,
                collation=cfg.collation,
            )
            if hasattr(parent.config, 'databases'):
                parent.config.databases.append(db)
        # cloud_sql_table nodes are intentionally NOT attached -- no TF generation (per D-09)


# Node type -> required GCP APIs mapping
_NODE_TYPE_APIS: dict[str, list[str]] = {
    "cloud_run": ["run.googleapis.com"],
    "cloud_run_job": ["run.googleapis.com"],
    "cloud_function": ["cloudfunctions.googleapis.com", "cloudbuild.googleapis.com", "eventarc.googleapis.com"],
    "cloud_sql": ["sqladmin.googleapis.com"],
    "cloud_sql_database": ["sqladmin.googleapis.com"],
    "firestore": ["firestore.googleapis.com"],
    "bigquery": ["bigquery.googleapis.com"],
    "bigquery_table": ["bigquery.googleapis.com"],
    "bigtable": ["bigtable.googleapis.com", "bigtableadmin.googleapis.com"],
    "pubsub_topic": ["pubsub.googleapis.com"],
    "pubsub_subscription": ["pubsub.googleapis.com"],
    "pubsub_schema": ["pubsub.googleapis.com"],
    "cloud_task_queue": ["cloudtasks.googleapis.com"],
    "vpc": ["compute.googleapis.com"],
    "subnet": ["compute.googleapis.com"],
    "vpc_connector": ["vpcaccess.googleapis.com", "compute.googleapis.com"],
    "external_lb": ["compute.googleapis.com"],
    "service_account": ["iam.googleapis.com"],
    "secret_manager": ["secretmanager.googleapis.com"],
    "gcs_bucket": ["storage.googleapis.com"],
}


def _render_api_services(nodes: list) -> str:
    """Generate google_project_service resources for all APIs required by the blueprint."""
    apis: set[str] = set()
    for node in nodes:
        ntype = node.type.value if hasattr(node.type, 'value') else str(node.type)
        for api in _NODE_TYPE_APIS.get(ntype, []):
            apis.add(api)

    if not apis:
        return ""

    lines = [
        '# Auto-enabled GCP APIs based on blueprint resource types',
        '# Managed by the orchestration platform — do not edit manually',
        '',
    ]
    for api in sorted(apis):
        safe_name = api.replace(".", "-").rstrip("-")
        lines.append(f'resource "google_project_service" "{safe_name}" {{')
        lines.append(f'  project = var.gcp_project_id')
        lines.append(f'  service = "{api}"')
        lines.append(f'  disable_on_destroy = false')
        lines.append(f'}}')
        lines.append('')

    return "\n".join(lines)


def generate_terraform(envelope: Envelope) -> dict[str, str]:
    """Generate Terraform HCL files from a validated envelope.

    Returns a dict of filename -> HCL content.
    """
    files: dict[str, str] = {}
    env = _get_jinja_env()
    node_map = {n.name: n for n in envelope.nodes}
    sorted_nodes = topological_sort(envelope.nodes)

    # Reconstruct collection trees so Firestore templates have access to collections
    reconstruct_collection_tree(envelope.nodes)

    global_cfg = envelope.global_

    # Attach flat child resources (BQ tables, SQL databases) to parents for template rendering
    attach_child_resources(envelope.nodes)

    # Helper for templates
    def resolve_ref(ref: str) -> str:
        return resolve_node_ref(ref, node_map)

    # provider.tf
    files["provider.tf"] = _render_provider(env, global_cfg)

    # backend.tf
    if global_cfg.backend:
        files["backend.tf"] = _render_backend(env, global_cfg)

    # variables.tf
    files["variables.tf"] = _render_variables(env, global_cfg)

    # api_services.tf -- auto-enable required GCP APIs based on node types
    api_block = _render_api_services(sorted_nodes)
    if api_block:
        files["api_services.tf"] = api_block

    # main.tf -- all resources
    resource_blocks: list[str] = []
    for node in sorted_nodes:
        defn = REGISTRY.get(node.type)
        if not defn or not defn.terraform_resource:
            continue
        # Child nodes render inside parent templates, not as standalone resources
        # (cloud_sql_table has terraform_resource="" so the check above handles it)
        if node.type.value in _EMBEDDED_CHILD_TYPES:
            continue

        template_name = f"{node.type.value}.tf.j2"
        try:
            tmpl = env.get_template(template_name)

            # Compute TTL collections for firestore nodes
            extra_ctx = {}
            if node.type.value == "firestore" and hasattr(node.config, 'collections'):
                extra_ctx["collections_with_ttl"] = _collect_ttl_collections(node.config.collections)

            # Compute API dependencies for this node type
            ntype = node.type.value if hasattr(node.type, 'value') else str(node.type)
            api_deps = _NODE_TYPE_APIS.get(ntype, [])
            api_dep_refs = [f'google_project_service.{a.replace(".", "-").rstrip("-")}' for a in api_deps]

            block = tmpl.render(
                node=node,
                config=node.config,
                global_=global_cfg,
                resolve_ref=resolve_ref,
                defn=defn,
                api_depends_on=api_dep_refs,
                **extra_ctx,
            )
            # Inject depends_on for API enablement at the end of the resource block
            if api_dep_refs and block.rstrip().endswith('}'):
                dep_list = ", ".join(api_dep_refs)
                # Insert depends_on before the closing brace
                lines = block.rstrip().rsplit('}', 1)
                block = f'{lines[0]}  depends_on = [{dep_list}]\n}}'
            resource_blocks.append(block)
        except Exception:
            # Fallback: generate a comment placeholder
            resource_blocks.append(
                f'# Resource for {node.name} ({node.type.value})\n'
                f'# Template {template_name} not found — manual authoring required.\n'
            )

        # Companion resources (Eventarc triggers, Cloud Scheduler jobs)
        companion_blocks = _render_companion_resources(
            node, env, resolve_ref, global_cfg
        )
        resource_blocks.extend(companion_blocks)

    if resource_blocks:
        files["main.tf"] = "\n\n".join(resource_blocks) + "\n"

    return files


def _render_companion_resources(node, env, resolve_ref, global_cfg):
    """Render companion TF resources (Eventarc triggers, Scheduler jobs)."""
    blocks = []
    config = node.config

    if hasattr(config, 'eventarc_triggers') and config.eventarc_triggers:
        try:
            tmpl = env.get_template('eventarc_trigger.tf.j2')
            for i, trigger in enumerate(config.eventarc_triggers):
                blocks.append(tmpl.render(
                    node=node, trigger=trigger, idx=i,
                    global_=global_cfg, resolve_ref=resolve_ref,
                ))
        except Exception as e:
            log.error("Failed to render eventarc_trigger template for %s: %s", node.name, e)
            blocks.append(f"# ERROR: eventarc_trigger rendering failed for {node.name}: {e}\n")

    if hasattr(config, 'scheduler_triggers') and config.scheduler_triggers:
        try:
            tmpl = env.get_template('cloud_scheduler_job.tf.j2')
            for i, trigger in enumerate(config.scheduler_triggers):
                blocks.append(tmpl.render(
                    node=node, trigger=trigger, idx=i,
                    global_=global_cfg, resolve_ref=resolve_ref,
                ))
        except Exception as e:
            log.error("Failed to render cloud_scheduler_job template for %s: %s", node.name, e)
            blocks.append(f"# ERROR: cloud_scheduler_job rendering failed for {node.name}: {e}\n")

    return blocks


def preview_resources(envelope: Envelope) -> list[dict]:
    """Return a list of TF resources that would be generated."""
    resources = []
    sorted_nodes = topological_sort(envelope.nodes)

    for node in sorted_nodes:
        defn = REGISTRY.get(node.type)
        if not defn or not defn.terraform_resource:
            continue
        resources.append({
            "node_name": node.name,
            "node_type": node.type.value,
            "terraform_resource": defn.terraform_resource,
            "resource_name": node.name,
        })

    return resources


def _render_provider(env: Environment, global_cfg) -> str:
    return (
        'terraform {\n'
        '  required_version = ">= 1.5"\n'
        '  required_providers {\n'
        '    google = {\n'
        '      source  = "hashicorp/google"\n'
        '      version = ">= 5.0"\n'
        '    }\n'
        '  }\n'
        '}\n\n'
        'provider "google" {\n'
        '  project = var.gcp_project_id\n'
        '  region  = var.gcp_region\n'
        '}\n'
    )


def _render_backend(env: Environment, global_cfg) -> str:
    if global_cfg.backend is None:
        return ""
    backend = global_cfg.backend
    return (
        'terraform {\n'
        '  backend "gcs" {\n'
        f'    bucket = var.tf_state_bucket\n'
        f'    prefix = "{backend.prefix}"\n'
        '  }\n'
        '}\n'
    )


def _render_variables(env: Environment, global_cfg) -> str:
    return (
        'variable "gcp_project_id" {\n'
        '  type        = string\n'
        '  description = "GCP project ID"\n'
        '}\n\n'
        'variable "gcp_region" {\n'
        '  type        = string\n'
        f'  default     = "{global_cfg.region}"\n'
        '  description = "Primary GCP region"\n'
        '}\n\n'
        'variable "environment" {\n'
        '  type        = string\n'
        f'  default     = "{global_cfg.environment}"\n'
        '  description = "Environment name"\n'
        '}\n\n'
        'variable "tf_state_bucket" {\n'
        '  type        = string\n'
        '  description = "GCS bucket for Terraform state"\n'
        '}\n'
    )
