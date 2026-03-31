"""Client code generator — produces clients.py with LRU-cached factory functions.

Given a list of dependency declarations (from WorkflowDefinition refs) and
the full set of blueprint nodes, generates:
1. A `clients.py` module with @lru_cache decorated factory functions
2. Contextual code snippets per dependency type
"""

from __future__ import annotations

import logging
import re

import jinja2

log = logging.getLogger(__name__)

# ── Jinja2 environment ──────────────────────────────────────────────

_env = jinja2.Environment(
    undefined=jinja2.StrictUndefined,
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

# ── clients.py template ─────────────────────────────────────────────

CLIENTS_PY_TEMPLATE = _env.from_string('''\
"""Auto-generated client factories. DO NOT EDIT manually."""

from functools import lru_cache
import logging

log = logging.getLogger(__name__)

{% if not sections %}
# No dependencies declared — add dependencies to generate client factories.
{% endif %}
{% for section in sections %}
{{ section }}
{% endfor %}
''')

# ── Per-type factory templates ───────────────────────────────────────

_FIRESTORE_FACTORY = _env.from_string('''\
@lru_cache(maxsize=1)
def get_firestore_client():
    """Cached Firestore client for {{ node_name }}."""
    from google.cloud import firestore
    return firestore.Client()
''')

_CLOUD_SQL_FACTORY = _env.from_string('''\
@lru_cache(maxsize=1)
def get_cloud_sql_connection():
    """Cached Cloud SQL connection for {{ node_name }}."""
    from google.cloud.sql.connector import Connector
    connector = Connector()
    return connector.connect("{{ instance_connection_name }}", "pg8000")
''')

_GCS_FACTORY = _env.from_string('''\
@lru_cache(maxsize=1)
def get_gcs_bucket(bucket_name="{{ bucket_name }}"):
    """Cached GCS bucket client for {{ node_name }}."""
    from google.cloud import storage
    return storage.Client().bucket(bucket_name)
''')

_PUBSUB_PUBLISHER_FACTORY = _env.from_string('''\
@lru_cache(maxsize=1)
def get_publisher_client():
    """Cached Pub/Sub publisher for {{ node_name }}."""
    from google.cloud import pubsub_v1
    return pubsub_v1.PublisherClient()
''')

_PUBSUB_SUBSCRIBER_FACTORY = _env.from_string('''\
@lru_cache(maxsize=1)
def get_subscriber_client():
    """Cached Pub/Sub subscriber for {{ node_name }}."""
    from google.cloud import pubsub_v1
    return pubsub_v1.SubscriberClient()
''')

_CLOUD_RUN_INVOKE_FACTORY = _env.from_string('''\
import httpx


def call_{{ sanitized_name }}(path: str, method: str = "GET", **kwargs):
    """Call {{ target_node }} Cloud Run service."""
    import google.auth.transport.requests
    import google.oauth2.id_token
    url = f"{SERVICE_URL}{path}"
    audience = f"{SERVICE_URL}"
    auth_req = google.auth.transport.requests.Request()
    token = google.oauth2.id_token.fetch_id_token(auth_req, audience)
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client() as client:
        return client.request(method, url, headers=headers, **kwargs)
''')

# ── Snippet templates ────────────────────────────────────────────────

SNIPPET_TEMPLATES: dict[str, list[dict]] = {
    "firestore": [
        {
            "name": "Read document",
            "description": "Read a single Firestore document by ID",
            "code": 'doc = get_firestore_client().collection("{collection}").document("{doc_id}").get()\ndata = doc.to_dict()',
        },
        {
            "name": "Write document",
            "description": "Write data to a Firestore document",
            "code": 'get_firestore_client().collection("{collection}").document("{doc_id}").set({{"key": "value"}})',
        },
        {
            "name": "Query collection",
            "description": "Query a Firestore collection with filters",
            "code": 'docs = get_firestore_client().collection("{collection}").where("field", "==", value).stream()\nresults = [doc.to_dict() for doc in docs]',
        },
        {
            "name": "Batch write",
            "description": "Write multiple documents in a batch",
            "code": 'batch = get_firestore_client().batch()\nfor item in items:\n    ref = get_firestore_client().collection("{collection}").document(item["id"])\n    batch.set(ref, item)\nbatch.commit()',
        },
    ],
    "cloud_sql": [
        {
            "name": "Execute query",
            "description": "Execute a SQL query and fetch results",
            "code": 'conn = get_cloud_sql_connection()\ncursor = conn.cursor()\ncursor.execute("SELECT * FROM {table}")\nrows = cursor.fetchall()',
        },
        {
            "name": "Insert row",
            "description": "Insert a row into a table",
            "code": 'conn = get_cloud_sql_connection()\ncursor = conn.cursor()\ncursor.execute("INSERT INTO {table} (col1, col2) VALUES (%s, %s)", (val1, val2))\nconn.commit()',
        },
        {
            "name": "Transaction",
            "description": "Execute multiple statements in a transaction",
            "code": 'conn = get_cloud_sql_connection()\ntry:\n    cursor = conn.cursor()\n    cursor.execute("UPDATE {table} SET col = %s WHERE id = %s", (val, id))\n    conn.commit()\nexcept Exception:\n    conn.rollback()\n    raise',
        },
    ],
    "gcs_bucket": [
        {
            "name": "Upload file",
            "description": "Upload a file to the GCS bucket",
            "code": 'blob = get_gcs_bucket().blob("{path}")\nblob.upload_from_string(data, content_type="application/octet-stream")',
        },
        {
            "name": "Download file",
            "description": "Download a file from the GCS bucket",
            "code": 'blob = get_gcs_bucket().blob("{path}")\ndata = blob.download_as_bytes()',
        },
        {
            "name": "List objects",
            "description": "List objects in the bucket with optional prefix",
            "code": 'blobs = get_gcs_bucket().list_blobs(prefix="{prefix}")\nfor blob in blobs:\n    print(blob.name)',
        },
    ],
    "pubsub_topic": [
        {
            "name": "Publish message",
            "description": "Publish a message to the Pub/Sub topic",
            "code": 'from google.cloud import pubsub_v1\ntopic_path = get_publisher_client().topic_path("{project_id}", "{topic_name}")\nfuture = get_publisher_client().publish(topic_path, data=b"message")\nfuture.result()',
        },
        {
            "name": "Subscribe to topic",
            "description": "Subscribe and process messages from the topic",
            "code": 'from google.cloud import pubsub_v1\nsub_path = get_subscriber_client().subscription_path("{project_id}", "{subscription_name}")\ndef callback(message):\n    print(message.data)\n    message.ack()\nget_subscriber_client().subscribe(sub_path, callback=callback)',
        },
    ],
    "cloud_run": [
        {
            "name": "Call service endpoint",
            "description": "Make an authenticated call to the Cloud Run service",
            "code": 'response = call_{sanitized_name}("/api/endpoint", method="POST", json={{"key": "value"}})\nprint(response.status_code, response.json())',
        },
    ],
}


def _sanitize_name(name: str) -> str:
    """Convert a node name to a valid Python identifier."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", name)


def _resolve_node_type(node_name: str, all_nodes: list[dict]) -> str | None:
    """Look up a node's type from the full node list."""
    for n in all_nodes:
        if n.get("name") == node_name:
            return n.get("type")
    return None


def generate_clients_py(dependencies: list[dict], all_nodes: list[dict]) -> str:
    """Generate a clients.py module with LRU-cached factory functions.

    Args:
        dependencies: List of dependency dicts with ref_type and target info.
        all_nodes: Full list of blueprint nodes for type resolution.

    Returns:
        Generated Python source code string.
    """
    sections: list[str] = []
    seen_factories: set[str] = set()

    for dep in dependencies:
        ref_type = dep.get("ref_type", "")

        if ref_type == "db":
            node_name = dep.get("node_name", "")
            node_type = _resolve_node_type(node_name, all_nodes)

            if node_type == "firestore" and "firestore" not in seen_factories:
                sections.append(_FIRESTORE_FACTORY.render(node_name=node_name))
                seen_factories.add("firestore")

            elif node_type == "cloud_sql" and "cloud_sql" not in seen_factories:
                sections.append(_CLOUD_SQL_FACTORY.render(
                    node_name=node_name,
                    instance_connection_name=f"project:region:{node_name}",
                ))
                seen_factories.add("cloud_sql")

            elif node_type == "gcs_bucket" and "gcs_bucket" not in seen_factories:
                bucket_name = node_name.replace("_", "-")
                sections.append(_GCS_FACTORY.render(
                    node_name=node_name,
                    bucket_name=bucket_name,
                ))
                seen_factories.add("gcs_bucket")

        elif ref_type == "pubsub":
            node_name = dep.get("topic_node", "")
            direction = dep.get("direction", "publish")

            if direction == "publish" and "publisher" not in seen_factories:
                sections.append(_PUBSUB_PUBLISHER_FACTORY.render(node_name=node_name))
                seen_factories.add("publisher")

            elif direction == "subscribe" and "subscriber" not in seen_factories:
                sections.append(_PUBSUB_SUBSCRIBER_FACTORY.render(node_name=node_name))
                seen_factories.add("subscriber")

        elif ref_type == "invoke":
            target_node = dep.get("target_node", "")
            sanitized = _sanitize_name(target_node)
            factory_key = f"invoke_{sanitized}"

            if factory_key not in seen_factories:
                sections.append(_CLOUD_RUN_INVOKE_FACTORY.render(
                    sanitized_name=sanitized,
                    target_node=target_node,
                    SERVICE_URL="{SERVICE_URL}",
                ))
                seen_factories.add(factory_key)

    return CLIENTS_PY_TEMPLATE.render(sections=sections)


def generate_snippets(dependencies: list[dict], all_nodes: list[dict]) -> dict[str, list[dict]]:
    """Generate contextual code snippets per dependency.

    Args:
        dependencies: List of dependency dicts with ref_type and target info.
        all_nodes: Full list of blueprint nodes for type resolution.

    Returns:
        Dict keyed by dependency node name, value is list of snippet dicts
        with keys: name, description, code.
    """
    result: dict[str, list[dict]] = {}

    for dep in dependencies:
        ref_type = dep.get("ref_type", "")

        if ref_type == "db":
            node_name = dep.get("node_name", "")
            node_type = _resolve_node_type(node_name, all_nodes)
            templates = SNIPPET_TEMPLATES.get(node_type or "", [])
            if templates:
                result[node_name] = [
                    {"name": t["name"], "description": t["description"], "code": t["code"]}
                    for t in templates
                ]

        elif ref_type == "pubsub":
            node_name = dep.get("topic_node", "")
            templates = SNIPPET_TEMPLATES.get("pubsub_topic", [])
            if templates:
                result[node_name] = [
                    {"name": t["name"], "description": t["description"], "code": t["code"]}
                    for t in templates
                ]

        elif ref_type == "invoke":
            target_node = dep.get("target_node", "")
            sanitized = _sanitize_name(target_node)
            templates = SNIPPET_TEMPLATES.get("cloud_run", [])
            if templates:
                result[target_node] = [
                    {
                        "name": t["name"],
                        "description": t["description"],
                        "code": t["code"].format(sanitized_name=sanitized),
                    }
                    for t in templates
                ]

    return result
