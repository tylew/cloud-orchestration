"""Firestore client singleton and shared reference helpers."""

import os
from google.cloud import firestore

_client = None

def get_client() -> firestore.Client:
    global _client
    if _client is None:
        project = os.environ.get("GCP_PROJECT_ID")
        database = os.environ.get("FIRESTORE_DATABASE", "(default)")
        _client = firestore.Client(project=project, database=database)
    return _client


def _tenants_ref(tenant_id: str):
    return get_client().collection("tenants").document(tenant_id)


def _project_ref(tenant_id: str, project_ref_id: str):
    return _tenants_ref(tenant_id).collection("projects").document(project_ref_id)


def _batch_commit(client, operations: list):
    """Commit a list of (batch) -> None callables in groups of 500 (Firestore limit)."""
    for i in range(0, len(operations), 500):
        batch = client.batch()
        for op in operations[i:i + 500]:
            op(batch)
        batch.commit()
