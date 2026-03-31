"""Terraform HCL generation from an Envelope."""

import logging
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

log = logging.getLogger(__name__)

from core.schemas.base import Envelope, BaseNode
from core.schemas.configs.bigquery import BqTable, BigQueryTableConfig
from core.schemas.configs.cloud_sql import SqlDatabase, CloudSqlDatabaseConfig
from core.schemas.enums import CHILD_PARENT_MAP
from core.registry import REGISTRY
from core.terraform.naming import resolve_gcp_name
from core.terraform.resolver import resolve_node_ref, topological_sort


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

# Map: (node_type, registry_output_name) -> (tf_attribute, resource_name_suffix)
# resource_name_suffix is appended to node.name when building the TF resource reference
# (e.g., external_lb IP resource is named {name}_ip in the template)
_OUTPUT_ATTR_MAP: dict[tuple[str, str], tuple[str, str]] = {
    ("cloud_run", "endpoint"): ("uri", ""),
    ("cloud_run", "service_account_email"): ("template[0].service_account", ""),
    ("cloud_run_job", "job_name"): ("name", ""),
    ("cloud_function", "endpoint"): ("service_config[0].uri", ""),
    ("cloud_sql", "connection_name"): ("connection_name", ""),
    ("cloud_sql", "private_ip"): ("private_ip_address", ""),
    ("external_lb", "ip_address"): ("address", "_ip"),
    ("gcs_bucket", "url"): ("url", ""),
    ("gcs_bucket", "bucket"): ("name", ""),
    ("cloud_dns", "name_servers"): ("name_servers", ""),
    ("cloud_dns", "dns_name"): ("dns_name", ""),
    ("firestore", "database"): ("name", ""),
    ("bigquery", "dataset"): ("dataset_id", ""),
    ("bigtable", "instance"): ("name", ""),
    ("pubsub_topic", "topic"): ("id", ""),
    ("pubsub_subscription", "subscription"): ("id", ""),
    ("pubsub_schema", "name"): ("id", ""),
    ("cloud_task_queue", "queue"): ("id", ""),
    ("service_account", "email"): ("email", ""),
}

_INTERNAL_ONLY_TYPES = {"vpc", "subnet", "vpc_connector"}


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
    "cloud_function": ["cloudfunctions.googleapis.com", "cloudbuild.googleapis.com", "eventarc.googleapis.com", "artifactregistry.googleapis.com"],
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
    "cloud_dns": ["dns.googleapis.com"],
    "service_account": ["iam.googleapis.com"],
    "gcs_bucket": ["storage.googleapis.com"],
}


def _render_iam_bindings(nodes: list) -> str:
    """Generate IAM role bindings inferred from dependency graph edges (AGT-10).

    For each compute node with a service_account, look at its depends_on targets.
    Map each (dependency_type) to the required IAM role and generate a
    google_project_iam_member binding.
    """
    from core.iam_mappings import IAM_ROLE_MAP
    from core.schemas.enums import COMPUTE_TYPES

    # Build node lookup by both name and slug
    node_lookup = {}
    for n in nodes:
        ntype = n.type.value if hasattr(n.type, 'value') else str(n.type)
        name = n.name if hasattr(n, 'name') else ''
        slug = n.slug if hasattr(n, 'slug') else ''
        node_lookup[name] = ntype
        if slug:
            node_lookup[slug] = ntype

    compute_types = {t.value for t in COMPUTE_TYPES}
    lines = [
        '# Auto-inferred IAM bindings from dependency graph (AGT-10)',
        '# Managed by the orchestration platform',
        '',
    ]
    bindings_added = set()

    for node in nodes:
        ntype = node.type.value if hasattr(node.type, 'value') else str(node.type)
        if ntype not in compute_types:
            continue

        # Find the service account for this compute node
        config = node.config if hasattr(node, 'config') else None
        sa_ref = None
        if config:
            sa_val = getattr(config, 'service_account', None) or ''
            if isinstance(sa_val, str) and sa_val.startswith('node:'):
                # node:sa-frontend-api.email -> sa-frontend-api
                sa_name = sa_val.split(':')[1].split('.')[0]
                sa_ref = f'google_service_account.{sa_name}.email'
            elif sa_val:
                sa_ref = f'"{sa_val}"'

        if not sa_ref:
            continue

        # Check each dependency and infer IAM roles
        for dep in node.depends_on:
            dep_type = node_lookup.get(dep)
            if not dep_type or dep_type in compute_types or dep_type == 'service_account':
                continue

            # Try Read action first (most common for dependencies)
            role = IAM_ROLE_MAP.get(("Read", dep_type))
            if not role:
                role = IAM_ROLE_MAP.get(("Write", dep_type))
            if not role:
                role = IAM_ROLE_MAP.get(("Emit", dep_type))
            if not role:
                role = IAM_ROLE_MAP.get(("Enqueue", dep_type))
            if not role:
                continue

            _rid = getattr(node, 'resource_id', None) or node.name
            node_id = f"n_{_rid}" if _rid[0:1].isdigit() else _rid
            dep_id = dep  # deps reference by name still — keep for binding key
            binding_key = (node_id, dep, role)
            if binding_key in bindings_added:
                continue
            bindings_added.add(binding_key)

            safe_name = f'{node_id}-{dep_id}-{role.split("/")[-1]}'.replace('.', '-')
            lines.append(f'resource "google_project_iam_member" "{safe_name}" {{')
            lines.append(f'  project = var.gcp_project_id')
            lines.append(f'  role    = "{role}"')
            lines.append(f'  member  = "serviceAccount:${{{sa_ref}}}"')
            lines.append(f'}}')
            lines.append('')

    if len(bindings_added) == 0:
        return ""

    return "\n".join(lines)


def _render_api_services(nodes: list) -> str:
    """Generate google_project_service resources for all APIs required by the blueprint."""
    apis: set[str] = set()
    for node in nodes:
        ntype = node.type.value if hasattr(node.type, 'value') else str(node.type)
        for api in _NODE_TYPE_APIS.get(ntype, []):
            apis.add(api)

    if not apis:
        return ""

    # Check if cloud_function nodes exist — need to grant CF robot access to source bucket
    has_functions = any(
        (n.type.value if hasattr(n.type, 'value') else str(n.type)) in ("cloud_function",)
        for n in nodes
    )

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

    # Grant CF service agents access to source bucket and build permissions
    if has_functions:
        lines.append('# Cloud Functions v2 needs project number for service agent emails')
        lines.append('data "google_project" "current" {')
        lines.append('  project_id = var.gcp_project_id')
        lines.append('}')
        lines.append('')
        lines.append('# CF admin robot needs read access to source bucket (cross-project)')
        lines.append('resource "google_storage_bucket_iam_member" "cf-source-reader" {')
        lines.append('  bucket = var.cb_source_bucket')
        lines.append('  role   = "roles/storage.objectViewer"')
        lines.append('  member = "serviceAccount:service-${data.google_project.current.number}@gcf-admin-robot.iam.gserviceaccount.com"')
        lines.append('  depends_on = [google_project_service.cloudfunctions-googleapis-com]')
        lines.append('}')
        lines.append('')
        lines.append('# CF v2 uses Cloud Build internally — default CB SA needs builder + AR writer roles')
        lines.append('resource "google_project_iam_member" "cf-cloudbuild-builder" {')
        lines.append('  project = var.gcp_project_id')
        lines.append('  role    = "roles/cloudbuild.builds.builder"')
        lines.append('  member  = "serviceAccount:${data.google_project.current.number}@cloudbuild.gserviceaccount.com"')
        lines.append('  depends_on = [google_project_service.cloudbuild-googleapis-com]')
        lines.append('}')
        lines.append('')
        lines.append('resource "google_project_iam_member" "cf-ar-writer" {')
        lines.append('  project = var.gcp_project_id')
        lines.append('  role    = "roles/artifactregistry.writer"')
        lines.append('  member  = "serviceAccount:${data.google_project.current.number}@cloudbuild.gserviceaccount.com"')
        lines.append('  depends_on = [google_project_service.cloudbuild-googleapis-com]')
        lines.append('}')
        lines.append('')
        lines.append('resource "google_project_iam_member" "cf-logging" {')
        lines.append('  project = var.gcp_project_id')
        lines.append('  role    = "roles/logging.logWriter"')
        lines.append('  member  = "serviceAccount:${data.google_project.current.number}@cloudbuild.gserviceaccount.com"')
        lines.append('  depends_on = [google_project_service.cloudbuild-googleapis-com]')
        lines.append('}')
        lines.append('')
        lines.append('# Default compute SA needs broad roles for CF v2 internal builds')
        for role in [
            'roles/cloudfunctions.developer',
            'roles/cloudbuild.builds.editor',
            'roles/storage.admin',
            'roles/artifactregistry.admin',
            'roles/logging.logWriter',
        ]:
            safe = role.replace('/', '-').replace('.', '-')
            lines.append(f'resource "google_project_iam_member" "cf-compute-{safe}" {{')
            lines.append(f'  project = var.gcp_project_id')
            lines.append(f'  role    = "{role}"')
            lines.append(f'  member  = "serviceAccount:${{data.google_project.current.number}}-compute@developer.gserviceaccount.com"')
            lines.append(f'}}')
            lines.append('')
        lines.append('# AR repo for CF v2 built containers')
        lines.append('resource "google_artifact_registry_repository" "gcf-artifacts" {')
        lines.append('  location      = var.gcp_region')
        lines.append('  repository_id = "gcf-artifacts"')
        lines.append('  format        = "DOCKER"')
        lines.append('  project       = var.gcp_project_id')
        lines.append('  depends_on    = [google_project_service.artifactregistry-googleapis-com]')
        lines.append('}')
        lines.append('')

    return "\n".join(lines)


def _render_outputs(nodes: list) -> str:
    """Generate TF output blocks for external-facing resource attributes (D-01, D-02)."""
    lines = [
        '# Auto-generated outputs for external-facing resource attributes',
        '# Managed by the orchestration platform',
        '',
    ]
    for node in nodes:
        defn = REGISTRY.get(node.type)
        if not defn or not defn.terraform_resource:
            continue
        ntype = node.type.value if hasattr(node.type, 'value') else str(node.type)
        if ntype in _INTERNAL_ONLY_TYPES or ntype in _EMBEDDED_CHILD_TYPES:
            continue

        for out in defn.default_outputs:
            attr_key = (ntype, out["name"])
            mapping = _OUTPUT_ATTR_MAP.get(attr_key)
            if not mapping:
                continue  # Not mapped = not external-facing

            tf_attr, resource_suffix = mapping
            rid = node.resource_id or node.name
            tf_id = f"n_{rid}" if rid[0:1].isdigit() else rid
            output_name = f"{tf_id}_{out['name']}"
            tf_resource_name = f"{tf_id}{resource_suffix}"
            tf_ref = f"{defn.terraform_resource}.{tf_resource_name}.{tf_attr}"
            lines.append(f'output "{output_name}" {{')
            lines.append(f'  value       = {tf_ref}')
            lines.append(f'  description = "{node.name} {out["name"]}"')
            lines.append(f'}}')
            lines.append('')

    if len(lines) <= 3:  # only header comment
        return ""
    return "\n".join(lines)


def generate_terraform(envelope: Envelope) -> dict[str, str]:
    """Generate Terraform HCL files from a validated envelope.

    Returns a dict of filename -> HCL content.
    """
    files: dict[str, str] = {}
    env = _get_jinja_env()
    node_map = {n.name: n for n in envelope.nodes}
    sorted_nodes = topological_sort(envelope.nodes)

    global_cfg = envelope.global_

    # Attach flat child resources (BQ tables, SQL databases) to parents for template rendering
    attach_child_resources(envelope.nodes)

    # Helper for templates
    def resolve_ref(ref: str) -> str:
        return resolve_node_ref(ref, node_map)

    def resolve_sa_email(ref: str) -> str:
        """Resolve a service_account ref to a TF expression for the SA email."""
        if not ref:
            return '""'
        resolved = resolve_node_ref(ref, node_map)
        if resolved.startswith("google_service_account."):
            return resolved.replace(".id", ".email")
        return f'"{ref}"'

    # provider.tf
    files["provider.tf"] = _render_provider(env, global_cfg)

    # backend.tf
    if global_cfg.backend:
        files["backend.tf"] = _render_backend(env, global_cfg)

    # variables.tf
    files["variables.tf"] = _render_variables(env, global_cfg, sorted_nodes)

    # iam_bindings.tf -- auto-infer IAM roles from dependency graph (AGT-10)
    iam_block = _render_iam_bindings(sorted_nodes)
    if iam_block:
        files["iam_bindings.tf"] = iam_block

    # api_services.tf -- auto-enable required GCP APIs based on node types
    api_block = _render_api_services(sorted_nodes)
    if api_block:
        files["api_services.tf"] = api_block

    # outputs.tf -- external-facing TF output values (D-01, D-02)
    outputs_block = _render_outputs(sorted_nodes)
    if outputs_block:
        files["outputs.tf"] = outputs_block

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

            # Compute GCP-safe name from registry naming template
            gcp_name = resolve_gcp_name(node, global_cfg.environment)

            # TF resource label must be a valid HCL identifier (letter/underscore first)
            rid = node.resource_id or node.name
            tf_label = f"n_{rid}" if rid[0:1].isdigit() else rid

            block = tmpl.render(
                node=node,
                config=node.config,
                global_=global_cfg,
                resolve_ref=resolve_ref,
                resolve_sa_email=resolve_sa_email,
                defn=defn,
                api_depends_on=api_dep_refs,
                gcp_name=gcp_name,
                tf_label=tf_label,
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
        '      version = ">= 6.0"\n'
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


def _render_variables(env: Environment, global_cfg, nodes: list = None) -> str:
    lines = (
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
    # Add cb_source_bucket if cloud functions are present
    if nodes and any(
        (n.type.value if hasattr(n.type, 'value') else str(n.type)) == 'cloud_function'
        for n in nodes
    ):
        lines += (
            '\nvariable "cb_source_bucket" {\n'
            '  type        = string\n'
            '  description = "GCS bucket for Cloud Function source code"\n'
            '}\n'
        )
    return lines
