"""IAM role mapping tests — ActionType x NodeType -> GCP IAM role."""

import pytest

from packages.core.iam_mappings import IAM_ROLE_MAP, get_iam_role, infer_iam_roles, PRIVATE_ACCESS_TYPES


class TestIamRoleMap:
    """Verify the static mapping table covers all expected combos."""

    def test_map_has_minimum_entries(self):
        assert len(IAM_ROLE_MAP) >= 14

    @pytest.mark.parametrize("action,target,expected", [
        ("Read", "cloud_sql", "roles/cloudsql.client"),
        ("Write", "cloud_sql", "roles/cloudsql.client"),
        ("Read", "firestore", "roles/datastore.user"),
        ("Write", "firestore", "roles/datastore.user"),
        ("Read", "bigquery", "roles/bigquery.dataViewer"),
        ("Write", "bigquery", "roles/bigquery.dataEditor"),
        ("Read", "bigtable", "roles/bigtable.reader"),
        ("Write", "bigtable", "roles/bigtable.user"),
        ("Read", "gcs_bucket", "roles/storage.objectViewer"),
        ("Write", "gcs_bucket", "roles/storage.objectAdmin"),
        ("Invoke", "cloud_run", "roles/run.invoker"),
        ("Invoke", "cloud_function", "roles/cloudfunctions.invoker"),
        ("Emit", "pubsub_topic", "roles/pubsub.publisher"),
        ("Enqueue", "cloud_task_queue", "roles/cloudtasks.enqueuer"),
        ("Read", "secret_manager", "roles/secretmanager.secretAccessor"),
        ("Write", "secret_manager", "roles/secretmanager.secretVersionAdder"),
    ])
    def test_known_mappings(self, action, target, expected):
        assert get_iam_role(action, target) == expected

    def test_unknown_combo_returns_none(self):
        assert get_iam_role("Read", "external_lb") is None

    def test_invalid_action_returns_none(self):
        assert get_iam_role("Delete", "cloud_sql") is None


class TestPrivateAccessTypes:
    """Verify PRIVATE_ACCESS_TYPES marks types needing VPC connectivity."""

    def test_cloud_sql_is_private(self):
        from packages.core.schemas.enums import NodeType
        assert NodeType.CLOUD_SQL in PRIVATE_ACCESS_TYPES

    def test_bigtable_is_private(self):
        from packages.core.schemas.enums import NodeType
        assert NodeType.BIGTABLE in PRIVATE_ACCESS_TYPES

    def test_firestore_is_not_private(self):
        from packages.core.schemas.enums import NodeType
        assert NodeType.FIRESTORE not in PRIVATE_ACCESS_TYPES

    def test_pubsub_is_not_private(self):
        from packages.core.schemas.enums import NodeType
        assert NodeType.PUBSUB_TOPIC not in PRIVATE_ACCESS_TYPES


class TestInferIamRoles:
    """Verify role inference from node dependency graph."""

    def test_compute_with_read_step(self):
        """Cloud Run reading from Firestore should get datastore.user."""
        node = {
            "name": "api-service",
            "type": "cloud_run",
            "depends_on": ["my-db"],
            "internalGraph": {
                "steps": [
                    {
                        "id": "s1",
                        "order": 1,
                        "actionType": "Read",
                        "targetNodeName": "my-db",
                        "targetNodeType": "firestore",
                        "purpose": "Read user data",
                    }
                ]
            },
        }
        all_nodes = [
            node,
            {"name": "my-db", "type": "firestore", "depends_on": []},
        ]
        roles = infer_iam_roles(node, all_nodes)
        assert "roles/datastore.user" in roles

    def test_compute_with_multiple_deps(self):
        """Multiple depends_on should produce multiple roles."""
        node = {
            "name": "worker",
            "type": "cloud_run_job",
            "depends_on": ["my-db", "my-topic"],
        }
        all_nodes = [
            node,
            {"name": "my-db", "type": "cloud_sql", "depends_on": []},
            {"name": "my-topic", "type": "pubsub_topic", "depends_on": []},
        ]
        roles = infer_iam_roles(node, all_nodes)
        assert "roles/cloudsql.client" in roles
        # depends_on infers implicit Read — pubsub topic Read is not mapped
        # (publisher role will come from ServiceContract in the future)

    def test_no_internal_graph_returns_empty(self):
        """Non-compute node with no steps returns no roles."""
        node = {"name": "my-db", "type": "firestore", "depends_on": []}
        roles = infer_iam_roles(node, [node])
        assert roles == set()

    def test_depends_on_implicit_read(self):
        """depends_on without explicit steps should infer Read access."""
        node = {
            "name": "api",
            "type": "cloud_run",
            "depends_on": ["my-bucket"],
        }
        all_nodes = [
            node,
            {"name": "my-bucket", "type": "gcs_bucket", "depends_on": []},
        ]
        roles = infer_iam_roles(node, all_nodes)
        assert "roles/storage.objectViewer" in roles

    def test_dedup_roles(self):
        """Same role from multiple steps should appear once."""
        node = {
            "name": "api",
            "type": "cloud_run",
            "depends_on": ["my-db"],
            "internalGraph": {
                "steps": [
                    {
                        "id": "s1",
                        "order": 1,
                        "actionType": "Read",
                        "targetNodeName": "my-db",
                        "targetNodeType": "firestore",
                        "purpose": "Read",
                    },
                    {
                        "id": "s2",
                        "order": 2,
                        "actionType": "Write",
                        "targetNodeName": "my-db",
                        "targetNodeType": "firestore",
                        "purpose": "Write",
                    },
                ]
            },
        }
        all_nodes = [
            node,
            {"name": "my-db", "type": "firestore", "depends_on": []},
        ]
        roles = infer_iam_roles(node, all_nodes)
        # Both Read and Write on firestore map to roles/datastore.user
        assert roles == {"roles/datastore.user"}
