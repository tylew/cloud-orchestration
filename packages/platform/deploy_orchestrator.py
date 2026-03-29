"""Deploy orchestration -- extracted from handlers/projects.py."""

import logging
import os
import time

from packages.platform.gcp.cloud_build import (
    get_build_apply_output,
    get_build_plan_output,
    get_build_terraform_output,
    get_build_status,
    submit_terraform_build,
)
from packages.platform.store.blueprints import get_env_blueprint
from packages.platform.store.deploys import update_deploy_status
from packages.platform.store.projects import mark_env_deployed

log = logging.getLogger(__name__)

FUNCTION_TYPES = {"cloud_function"}


def _package_function_sources(
    envelope: dict, project_ref_id: str, env_name: str, host_project_id: str
) -> dict:
    """Package Cloud Function source files from GCS into zip archives.

    For each cloud_function node in code_editor mode, reads source files from
    the code file storage path, creates a zip archive in the CB source bucket,
    and injects source_bucket/source_object into the node config.
    """
    import io
    import zipfile
    from datetime import datetime, timezone
    from google.cloud import storage as gcs

    cb_source_bucket = os.environ.get("CB_SOURCE_BUCKET", f"{host_project_id}-cb-source")
    nodes = envelope.get("nodes", [])

    for node in nodes:
        ntype = node.get("type", "")
        if ntype not in FUNCTION_TYPES:
            continue

        config = node.get("config", {})
        mode = config.get("mode", "workflow")
        node_name = node.get("name", "")
        node_slug = node.get("slug", node_name)

        # Skip if source already set
        if config.get("source") and config["source"].get("storage_source"):
            continue
        if config.get("source_bucket"):
            continue

        # Read source files from GCS (same path as write_code_file uses)
        from packages.platform.gcp.storage import list_files, read_file

        # Try project_ref_id + slug first (MCP path), then project_ref_id + name
        file_list = list_files(project_ref_id, env_name, node_slug)
        gcs_id, gcs_node = project_ref_id, node_slug
        if not file_list:
            file_list = list_files(project_ref_id, env_name, node_name)
            gcs_id, gcs_node = project_ref_id, node_name

        if not file_list:
            log.warning("No source files for function %s — skipping source packaging", node_name)
            continue

        source_files = {}
        for f in file_list:
            content = read_file(gcs_id, env_name, gcs_node, f)
            if content is not None:
                source_files[f] = content

        if not source_files:
            continue

        # Create zip archive in memory
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename, content in source_files.items():
                zf.writestr(filename, content)
        buf.seek(0)

        # Upload to GCS
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        blob_path = f"{project_ref_id}/functions/{env_name}/{node_slug}/{timestamp}.zip"
        client = gcs.Client()
        bucket = client.bucket(cb_source_bucket)
        blob = bucket.blob(blob_path)
        blob.upload_from_file(buf, content_type="application/zip")
        log.info("Packaged function source to gs://%s/%s (%d files)", cb_source_bucket, blob_path, len(source_files))

        # Inject source into node config
        config["source_bucket"] = cb_source_bucket
        config["source_object"] = blob_path

    return envelope


def _parse_terraform_outputs(raw: dict, node_names: list[str] | None = None) -> dict:
    """Parse terraform output -json into structured format for Firestore (D-04).

    Input format: {"output_name": {"sensitive": bool, "type": ..., "value": ...}, ...}
    Output format: {
        "outputs": {"output_name": value, ...},
        "by_node": {"node_name": {"attr": value}, ...}
    }

    When node_names is provided, uses prefix matching against known node names
    (longest-first) to correctly split multi-underscore output names like
    "my-zone_name_servers" -> ("my-zone", "name_servers").
    Falls back to rsplit("_", 1) when node_names is None or no match found.
    """
    flat = {}
    by_node = {}
    # Sort node names longest-first for greedy prefix matching
    sorted_names = sorted(node_names or [], key=len, reverse=True)
    for key, entry in raw.items():
        value = entry.get("value") if isinstance(entry, dict) else entry
        flat[key] = value
        # Try prefix match against known node names
        matched = False
        for name in sorted_names:
            prefix = f"{name}_"
            if key.startswith(prefix) and len(key) > len(prefix):
                attr = key[len(prefix):]
                if name not in by_node:
                    by_node[name] = {}
                by_node[name][attr] = value
                matched = True
                break
        # Fallback: rsplit for unknown nodes (backward compat)
        if not matched:
            parts = key.rsplit("_", 1)
            if len(parts) == 2:
                node_name, attr = parts
                if node_name not in by_node:
                    by_node[node_name] = {}
                by_node[node_name][attr] = value
    return {"outputs": flat, "by_node": by_node}


def _run_deploy(tenant_id: str, deploy_id: str, project_ref_id: str,
                project_id: str, env_name: str, region: str, tf_bucket: str):
    """Background task that submits terraform deploy via Cloud Build."""

    host_project_id = os.environ.get("GCP_PROJECT_ID", "pl4m-host")

    try:
        # Step 1: Get blueprint
        update_deploy_status(tenant_id, deploy_id, "generating")
        blueprint = get_env_blueprint(tenant_id, project_ref_id, env_name)
        if not blueprint or not blueprint.get("envelope"):
            update_deploy_status(tenant_id, deploy_id, "failed", error="No blueprint found for environment")
            return

        envelope = blueprint["envelope"]

        # Step 1.5: Inject built image URIs for workflow-mode compute nodes
        from packages.platform.deploy_service import inject_build_image_uris
        envelope = inject_build_image_uris(tenant_id, project_id, env_name, envelope)

        # Step 1.6: Package Cloud Function source files into GCS
        envelope = _package_function_sources(envelope, project_ref_id, env_name, host_project_id)

        update_deploy_status(tenant_id, deploy_id, "generating",
                             step_result={"step": "generate_tf", "success": True})

        # Step 2: Generate TF files
        from packages.core.schemas.base import Envelope
        from packages.core.terraform.generator import generate_terraform

        try:
            parsed = Envelope.model_validate(envelope)
            tf_files = generate_terraform(parsed)
        except Exception as e:
            update_deploy_status(tenant_id, deploy_id, "failed",
                                 error=f"TF generation failed: {e}")
            return

        # Step 3: Submit Cloud Build
        update_deploy_status(tenant_id, deploy_id, "building",
                             step_result={"step": "submit_build", "success": True})
        try:
            build_result = submit_terraform_build(
                host_project_id=host_project_id,
                target_project_id=project_id,
                env_name=env_name,
                tf_files=tf_files,
                tf_bucket=tf_bucket,
                region=region,
                tenant_id=tenant_id,
                project_ref_id=project_ref_id,
            )
        except Exception as e:
            update_deploy_status(tenant_id, deploy_id, "failed",
                                 error=f"Cloud Build submission failed: {e}")
            return

        build_id = build_result["build_id"]
        update_deploy_status(tenant_id, deploy_id, "building",
                             build_id=build_id,
                             log_url=build_result.get("log_url"))

        # Step 4: Poll Cloud Build until terminal state
        terminal_states = {"SUCCESS", "FAILURE", "TIMEOUT", "CANCELLED", "EXPIRED"}
        while True:
            status = get_build_status(host_project_id, build_id)
            if status["status"] in terminal_states:
                break
            time.sleep(10)

        # Step 5: Fetch plan/apply output from GCS
        plan_text = get_build_plan_output(host_project_id, build_id)
        apply_text = get_build_apply_output(host_project_id, build_id)

        # Step 5.5: Fetch terraform outputs from GCS (D-03)
        tf_outputs_raw = get_build_terraform_output(host_project_id, build_id)
        node_names = [n.get("name", n.get("slug", "")) for n in envelope.get("nodes", [])]
        tf_outputs = _parse_terraform_outputs(tf_outputs_raw, node_names=node_names) if tf_outputs_raw else None

        if status["status"] == "SUCCESS":
            mark_env_deployed(tenant_id, project_ref_id, env_name)

            # Create deploy snapshots for each node (per D-11/D-12)
            from packages.platform.deploy_service import create_deploy_snapshots
            try:
                create_deploy_snapshots(tenant_id, deploy_id, project_ref_id, env_name, envelope)
            except Exception as snap_err:
                log.warning("Failed to create deploy snapshots: %s", snap_err)

            update_deploy_status(
                tenant_id, deploy_id, "ready",
                step_result={"step": "cloud_build", "success": True, "build_status": status["status"]},
                plan_output=plan_text,
                apply_output=apply_text,
                terraform_outputs=tf_outputs,
            )

            # Write latest outputs to env_outputs doc for fast agent lookup (D-04)
            if tf_outputs:
                from packages.platform.store.deploys import save_env_outputs
                try:
                    save_env_outputs(tenant_id, project_ref_id, env_name, tf_outputs, deploy_id)
                except Exception as out_err:
                    log.warning("Failed to save env outputs: %s", out_err)
        else:
            update_deploy_status(
                tenant_id, deploy_id, "failed",
                error=f"Cloud Build {status['status']}",
                step_result={"step": "cloud_build", "success": False, "build_status": status["status"]},
                plan_output=plan_text,
                apply_output=apply_text,
            )

    except Exception as e:
        log.exception("Deploy failed for %s/%s", project_id, env_name)
        update_deploy_status(tenant_id, deploy_id, "failed", error=str(e))
