"""Deploy orchestration -- extracted from handlers/projects.py."""

import logging
import os
import time

from packages.platform.gcp.cloud_build import (
    get_build_apply_output,
    get_build_plan_output,
    get_build_status,
    submit_terraform_build,
)
from packages.platform.store.blueprints import get_env_blueprint
from packages.platform.store.deploys import update_deploy_status
from packages.platform.store.projects import mark_env_deployed

log = logging.getLogger(__name__)


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
            )
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
