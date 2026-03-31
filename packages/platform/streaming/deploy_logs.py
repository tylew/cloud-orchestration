"""Cloud Logging API wrapper for build log streaming (per D-04/D-07)."""

import asyncio
import json
import logging

from packages.platform.store.deploys import get_deploy_status

log = logging.getLogger(__name__)


async def stream_build_logs(host_project_id: str, build_id: str,
                            tenant_id: str, deploy_id: str):
    """Async generator that streams Cloud Build log entries via Cloud Logging API.

    Polls Cloud Logging for new entries, yields SSE-formatted dicts.
    Checks deploy status to detect terminal states and stop streaming.
    Sleeps 3s between polls (per D-04/D-07).
    """
    from google.cloud import logging as cloud_logging

    client = cloud_logging.Client(project=host_project_id)
    last_timestamp = None

    while True:
        # Build filter for Cloud Build logs
        filter_str = f'resource.type="build" resource.labels.build_id="{build_id}"'
        if last_timestamp:
            filter_str += f' timestamp>"{last_timestamp}"'

        try:
            entries = list(client.list_entries(
                filter_=filter_str,
                order_by="timestamp asc",
                page_size=100,
            ))
        except Exception as e:
            log.warning("Error fetching build logs for %s: %s", build_id, e)
            entries = []

        for entry in entries:
            payload = entry.payload if hasattr(entry, "payload") else str(entry)
            timestamp = entry.timestamp.isoformat() if hasattr(entry.timestamp, "isoformat") else str(entry.timestamp)
            severity = entry.severity if hasattr(entry, "severity") else "DEFAULT"

            yield {
                "event": "log",
                "data": json.dumps({
                    "text": str(payload),
                    "timestamp": timestamp,
                    "severity": severity,
                }),
            }
            last_timestamp = timestamp

        # Check deploy status for terminal state
        deploy = get_deploy_status(tenant_id, deploy_id)
        if deploy:
            terminal_status = deploy.get("status")
            if terminal_status in ("ready", "failed"):
                yield {
                    "event": "done",
                    "data": json.dumps({"status": terminal_status}),
                }
                break

        await asyncio.sleep(3)
