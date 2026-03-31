"""Code generator — produces application code for compute nodes based on internal graph steps.

For each compute node, examines the internal graph and generates:
1. Application code (Python/Node.js) with client libraries for each step
2. Dockerfile
3. Requirements/package dependencies
4. A computed image URI for Terraform to reference
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Client library mappings ─────────────────────────────────────────

PYTHON_CLIENTS: dict[str, dict] = {
    "cloud_sql": {
        "import": "from google.cloud.sql.connector import Connector\nimport sqlalchemy",
        "pip": ["cloud-sql-python-connector[pymysql]", "SQLAlchemy"],
        "init": 'connector = Connector()\ndef get_connection():\n    return connector.connect("{instance}", "pymysql", user="{user}", password="{password}", db="{db}")',
        "read": 'def read_{target}(query: str):\n    with engine.connect() as conn:\n        result = conn.execute(sqlalchemy.text(query))\n        return [dict(row._mapping) for row in result]',
        "write": 'def write_{target}(query: str, params: dict = None):\n    with engine.connect() as conn:\n        conn.execute(sqlalchemy.text(query), params or {{}})\n        conn.commit()',
    },
    "firestore": {
        "import": "from google.cloud import firestore",
        "pip": ["google-cloud-firestore"],
        "init": "db = firestore.Client()",
        "read": 'def read_{target}(collection: str, doc_id: str = None):\n    if doc_id:\n        return db.collection(collection).document(doc_id).get().to_dict()\n    return [doc.to_dict() for doc in db.collection(collection).stream()]',
        "write": 'def write_{target}(collection: str, doc_id: str, data: dict):\n    db.collection(collection).document(doc_id).set(data)',
    },
    "bigquery": {
        "import": "from google.cloud import bigquery",
        "pip": ["google-cloud-bigquery"],
        "init": "bq_client = bigquery.Client()",
        "read": 'def read_{target}(query: str):\n    return [dict(row) for row in bq_client.query(query).result()]',
        "write": 'def write_{target}(dataset: str, table: str, rows: list[dict]):\n    table_ref = bq_client.dataset(dataset).table(table)\n    errors = bq_client.insert_rows_json(table_ref, rows)\n    if errors:\n        raise RuntimeError(f"BigQuery insert errors: {{errors}}")',
    },
    "bigtable": {
        "import": "from google.cloud import bigtable\nfrom google.cloud.bigtable import row_filters",
        "pip": ["google-cloud-bigtable"],
        "init": 'bt_client = bigtable.Client(admin=True)\nbt_instance = bt_client.instance("{instance_id}")',
        "read": 'def read_{target}(table_id: str, row_key: str = None):\n    table = bt_instance.table(table_id)\n    if row_key:\n        row = table.read_row(row_key.encode())\n        return {{cf: {{q: [c.value for c in cells] for q, cells in cols.items()}} for cf, cols in row.cells.items()}} if row else None\n    return [row for row in table.read_rows()]',
        "write": 'def write_{target}(table_id: str, row_key: str, data: dict):\n    table = bt_instance.table(table_id)\n    row = table.direct_row(row_key.encode())\n    for cf, columns in data.items():\n        for col, val in columns.items():\n            row.set_cell(cf, col, val.encode() if isinstance(val, str) else val)\n    row.commit()',
    },
    "gcs_bucket": {
        "import": "from google.cloud import storage",
        "pip": ["google-cloud-storage"],
        "init": "storage_client = storage.Client()",
        "read": 'def read_{target}(bucket_name: str, blob_name: str):\n    bucket = storage_client.bucket(bucket_name)\n    blob = bucket.blob(blob_name)\n    return blob.download_as_bytes()',
        "write": 'def write_{target}(bucket_name: str, blob_name: str, data: bytes, content_type: str = "application/octet-stream"):\n    bucket = storage_client.bucket(bucket_name)\n    blob = bucket.blob(blob_name)\n    blob.upload_from_string(data, content_type=content_type)',
    },
    "pubsub_topic": {
        "import": "from google.cloud import pubsub_v1",
        "pip": ["google-cloud-pubsub"],
        "init": "publisher = pubsub_v1.PublisherClient()",
        "emit": 'def emit_{target}(topic_path: str, data: bytes, **attrs):\n    future = publisher.publish(topic_path, data, **attrs)\n    return future.result()',
    },
    "cloud_task_queue": {
        "import": "from google.cloud import tasks_v2\nimport json",
        "pip": ["google-cloud-tasks"],
        "init": "tasks_client = tasks_v2.CloudTasksClient()",
        "enqueue": 'def enqueue_{target}(queue_path: str, url: str, payload: dict):\n    task = {{"http_request": {{"http_method": "POST", "url": url, "body": json.dumps(payload).encode(), "headers": {{"Content-Type": "application/json"}}}}}}\n    return tasks_client.create_task(parent=queue_path, task=task)',
    },
    "cloud_run": {
        "import": "import httpx",
        "pip": ["httpx"],
        "init": "",
        "invoke": 'async def invoke_{target}(url: str, payload: dict = None):\n    async with httpx.AsyncClient() as client:\n        resp = await client.post(url, json=payload, timeout=30)\n        resp.raise_for_status()\n        return resp.json()',
    },
    "cloud_function": {
        "import": "import httpx",
        "pip": ["httpx"],
        "init": "",
        "invoke": 'async def invoke_{target}(url: str, payload: dict = None):\n    async with httpx.AsyncClient() as client:\n        resp = await client.post(url, json=payload, timeout=30)\n        resp.raise_for_status()\n        return resp.json()',
    },
    "third_party_api": {
        "import": "import httpx",
        "pip": ["httpx"],
        "init": "",
        "invoke": 'async def invoke_{target}(base_url: str, path: str, payload: dict = None, headers: dict = None):\n    async with httpx.AsyncClient() as client:\n        resp = await client.post(f"{{base_url}}{{path}}", json=payload, headers=headers, timeout=30)\n        resp.raise_for_status()\n        return resp.json()',
    },
}

NODEJS_CLIENTS: dict[str, dict] = {
    "cloud_sql": {
        "import": 'const { Connector } = require("@google-cloud/cloud-sql-connector");\nconst knex = require("knex");',
        "npm": ["@google-cloud/cloud-sql-connector", "knex", "pg"],
    },
    "firestore": {
        "import": 'const { Firestore } = require("@google-cloud/firestore");',
        "npm": ["@google-cloud/firestore"],
    },
    "bigquery": {
        "import": 'const { BigQuery } = require("@google-cloud/bigquery");',
        "npm": ["@google-cloud/bigquery"],
    },
    "gcs_bucket": {
        "import": 'const { Storage } = require("@google-cloud/storage");',
        "npm": ["@google-cloud/storage"],
    },
    "pubsub_topic": {
        "import": 'const { PubSub } = require("@google-cloud/pubsub");',
        "npm": ["@google-cloud/pubsub"],
    },
    "cloud_task_queue": {
        "import": 'const { CloudTasksClient } = require("@google-cloud/tasks");',
        "npm": ["@google-cloud/tasks"],
    },
}


@dataclass
class GeneratedCode:
    """Result of code generation for a single compute node."""
    files: dict[str, str] = field(default_factory=dict)
    image_uri: str = ""
    summary: str = ""


def generate_compute_code(
    node: dict,
    all_nodes: list[dict],
    global_config: dict,
) -> GeneratedCode:
    """Generate application code for a compute node based on its internal graph."""

    node_type = node["type"]
    node_name = node["name"]
    config = node.get("config", {})
    steps = (node.get("internalGraph") or {}).get("steps", [])

    if not steps:
        return GeneratedCode(summary="No internal steps defined")

    # Determine language
    is_function = node_type == "cloud_function"
    runtime = config.get("runtime", "") if is_function else ""
    is_python = not runtime or runtime.startswith("python")

    project_id = global_config.get("project_id", "my-project")
    region = global_config.get("region", "us-central1")
    image_uri = f"{region}-docker.pkg.dev/{project_id}/platform-builds/{node_name}:latest"

    if is_python:
        return _generate_python(node, steps, all_nodes, global_config, image_uri)
    else:
        return _generate_nodejs(node, steps, all_nodes, global_config, image_uri)


def _generate_python(
    node: dict,
    steps: list[dict],
    all_nodes: list[dict],
    global_config: dict,
    image_uri: str,
) -> GeneratedCode:
    """Generate Python application code."""

    node_name = node["name"]
    node_type = node["type"]
    config = node.get("config", {})
    is_function = node_type == "cloud_function"
    is_job = node_type == "cloud_run_job"

    # Collect unique target types and their clients
    imports = set()
    inits = []
    functions = []
    pip_deps = {"flask", "gunicorn"} if not is_function and not is_job else set()
    if is_function:
        pip_deps.add("functions-framework")

    seen_targets = set()
    step_calls = []

    nodes_by_name = {n["name"]: n for n in all_nodes}

    for step in sorted(steps, key=lambda s: s.get("order", 0)):
        action = step.get("actionType", "").lower()
        target_name = step.get("targetNodeName", "")
        target_type = step.get("targetNodeType", "")
        purpose = step.get("purpose", "")
        safe_target = target_name.replace("-", "_")

        if not target_type or target_type not in PYTHON_CLIENTS:
            continue

        client = PYTHON_CLIENTS[target_type]
        target_key = f"{target_type}_{action}"

        if target_type not in seen_targets:
            imports.add(client["import"])
            if client.get("init"):
                inits.append(client["init"].format(
                    instance=f"{global_config.get('project_id', 'project')}:{global_config.get('region', 'us-central1')}:{target_name}",
                    instance_id=target_name,
                    user="app",
                    password="",
                    db="app",
                ))
            pip_deps.update(client.get("pip", []))
            seen_targets.add(target_type)

        fn_template = client.get(action, "")
        if fn_template and target_key not in seen_targets:
            functions.append(f"# {purpose}" if purpose else f"# {action} {target_name}")
            functions.append(fn_template.format(target=safe_target))
            seen_targets.add(target_key)

        # Build concrete function call if step has details
        details = step.get("details") or {}
        concrete = _build_concrete_call(action, target_type, details, safe_target, nodes_by_name.get(target_name))
        if concrete:
            step_calls.append(f'    # Step {step.get("order", 0) + 1}: {purpose or f"{action} {target_name}"}')
            step_calls.append(f'    {concrete}')
        else:
            step_calls.append(f'    # Step {step.get("order", 0) + 1}: {purpose or f"{action} {target_name}"}')
            step_calls.append(f'    # {action}_{safe_target}(...)')

    # Assemble main.py
    lines = ['"""Auto-generated application code for {name}."""\n'.format(name=node_name)]
    lines.append("import os\nimport json\nimport logging\n")
    lines.extend(sorted(imports))
    lines.append("")
    lines.append("logging.basicConfig(level=logging.INFO)")
    lines.append("logger = logging.getLogger(__name__)\n")

    if inits:
        lines.append("# ── Client initialization ──")
        lines.extend(inits)
        lines.append("")

    if functions:
        lines.append("# ── Data access functions ──")
        lines.extend(functions)
        lines.append("")

    # Entry point
    if is_function:
        entry = config.get("entry_point", "handle_request")
        lines.append(f"def {entry}(request):")
        lines.append('    """Cloud Function entry point."""')
        lines.extend(step_calls)
        lines.append('    return json.dumps({"status": "ok"}), 200, {"Content-Type": "application/json"}')
    elif is_job:
        lines.append("def main():")
        lines.append('    """Cloud Run Job entry point."""')
        lines.append("    logger.info(f\"Starting job: {node_name}\")")
        lines.extend(step_calls)
        lines.append("    logger.info(\"Job complete\")")
        lines.append("")
        lines.append('if __name__ == "__main__":')
        lines.append("    main()")
    else:
        lines.append("from flask import Flask, request, jsonify\n")
        lines.append("app = Flask(__name__)\n")
        lines.append('@app.route("/", methods=["GET", "POST"])')
        lines.append("def handle():")
        lines.append('    """Main request handler."""')
        lines.extend(step_calls)
        lines.append('    return jsonify({"status": "ok"})')
        lines.append("")
        lines.append('if __name__ == "__main__":')
        lines.append('    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))')

    main_code = "\n".join(lines)

    # Requirements
    requirements = "\n".join(sorted(pip_deps))

    # Dockerfile
    port = config.get("port", 8080)
    if is_function:
        dockerfile = f"""FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT={port}
CMD ["functions-framework", "--target={config.get('entry_point', 'handle_request')}", "--port={port}"]
"""
    elif is_job:
        dockerfile = """FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
"""
    else:
        dockerfile = f"""FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT={port}
EXPOSE {port}
CMD ["gunicorn", "--bind", "0.0.0.0:{port}", "--workers", "1", "--threads", "8", "main:app"]
"""

    files = {
        "main.py": main_code,
        "requirements.txt": requirements,
        "Dockerfile": dockerfile,
    }

    return GeneratedCode(
        files=files,
        image_uri=image_uri,
        summary=f"Generated {len(steps)} step(s) → {len(files)} files",
    )


def _build_concrete_call(
    action: str,
    target_type: str,
    details: dict,
    safe_target: str,
    target_node: dict | None,
) -> str | None:
    """Build a concrete function call from step details, or None to fall back to generic."""
    if not details:
        return None

    target_config = (target_node or {}).get("config", {})

    if target_type == "firestore":
        collection = details.get("collection", "")
        if not collection:
            return None
        if action == "read":
            doc_src = details.get("doc_id_source", "")
            if doc_src:
                return f'result = read_{safe_target}("{collection}", {doc_src})'
            return f'result = read_{safe_target}("{collection}")'
        if action == "write":
            doc_src = details.get("doc_id_source", "doc_id")
            return f'write_{safe_target}("{collection}", {doc_src}, data)'

    if target_type == "bigquery":
        table = details.get("table", "")
        dataset = details.get("dataset") or target_config.get("dataset_id", "")
        if action == "read":
            query = details.get("query", "")
            if query:
                return f'result = read_{safe_target}("""{query}""")'
            if table and dataset:
                return f'result = read_{safe_target}("SELECT * FROM `{dataset}.{table}`")'
        if action == "write" and table and dataset:
            return f'write_{safe_target}("{dataset}", "{table}", rows)'

    if target_type == "cloud_sql":
        query = details.get("query", "")
        if action == "read" and query:
            return f'result = read_{safe_target}("""{query}""")'
        table = details.get("table", "")
        if action == "read" and table:
            return f'result = read_{safe_target}("SELECT * FROM {table}")'
        if action == "write" and table:
            return f'write_{safe_target}("INSERT INTO {table} VALUES (...)", params)'

    if target_type == "gcs_bucket":
        prefix = details.get("prefix", "")
        content_type = details.get("content_type", "application/octet-stream")
        bucket_name = (target_node or {}).get("name", safe_target).replace("_", "-")
        if action == "read" and prefix:
            return f'data = read_{safe_target}("{bucket_name}", "{prefix}")'
        if action == "write" and prefix:
            return f'write_{safe_target}("{bucket_name}", "{prefix}", data, "{content_type}")'

    if target_type == "pubsub_topic" and action == "emit":
        return f'emit_{safe_target}(topic_path, message_data)'

    if target_type == "cloud_task_queue" and action == "enqueue":
        uri = details.get("relativeUri", "/")
        return f'enqueue_{safe_target}(queue_path, "{uri}", payload)'

    if target_type in ("cloud_run", "cloud_function", "third_party_api") and action == "invoke":
        path = details.get("path", "/")
        return f'result = await invoke_{safe_target}(url, "{path}", payload)'

    return None


def _generate_nodejs(
    node: dict,
    steps: list[dict],
    all_nodes: list[dict],
    global_config: dict,
    image_uri: str,
) -> GeneratedCode:
    """Generate Node.js application code (for node.js runtimes)."""

    node_name = node["name"]
    config = node.get("config", {})
    is_function = node["type"] == "cloud_function"
    port = config.get("port", 8080)

    imports = set()
    npm_deps = {}
    step_comments = []

    for step in sorted(steps, key=lambda s: s.get("order", 0)):
        target_type = step.get("targetNodeType", "")
        action = step.get("actionType", "")
        purpose = step.get("purpose", "")
        target_name = step.get("targetNodeName", "")

        if target_type in NODEJS_CLIENTS:
            client = NODEJS_CLIENTS[target_type]
            imports.add(client["import"])
            for pkg in client.get("npm", []):
                npm_deps[pkg] = "latest"

        step_comments.append(f"  // Step: {purpose or f'{action} {target_name}'}")

    if not is_function:
        npm_deps["express"] = "^4.18.0"

    # index.js
    lines = [f'// Auto-generated application code for {node_name}\n']
    lines.extend(sorted(imports))
    lines.append("")

    if is_function:
        entry = config.get("entry_point", "handleRequest")
        lines.append(f"exports.{entry} = async (req, res) => {{")
        lines.extend(step_comments)
        lines.append('  res.json({ status: "ok" });')
        lines.append("};")
    else:
        lines.append('const express = require("express");')
        lines.append("const app = express();")
        lines.append("app.use(express.json());\n")
        lines.append('app.all("/", async (req, res) => {')
        lines.extend(step_comments)
        lines.append('  res.json({ status: "ok" });')
        lines.append("});\n")
        lines.append(f"const PORT = process.env.PORT || {port};")
        lines.append("app.listen(PORT, () => console.log(`Listening on ${{PORT}}`));")

    index_code = "\n".join(lines)

    # package.json
    pkg_json = {
        "name": node_name,
        "version": "1.0.0",
        "main": "index.js",
        "scripts": {"start": "node index.js"},
        "dependencies": npm_deps,
    }
    import json
    pkg_str = json.dumps(pkg_json, indent=2)

    # Dockerfile
    dockerfile = f"""FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
ENV PORT={port}
EXPOSE {port}
CMD ["node", "index.js"]
"""

    files = {
        "index.js": index_code,
        "package.json": pkg_str,
        "Dockerfile": dockerfile,
    }

    return GeneratedCode(
        files=files,
        image_uri=image_uri,
        summary=f"Generated {len(steps)} step(s) → {len(files)} files (Node.js)",
    )
