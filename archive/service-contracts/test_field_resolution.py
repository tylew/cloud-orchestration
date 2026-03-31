"""Field reference resolution tests for Firestore, Cloud SQL, and BigQuery."""

from packages.core.field_resolution import resolve_field_ref, collect_storage_fields


class TestFirestoreResolution:
    def test_simple_collection_field(self):
        config = {
            "location_id": "us-central",
            "collections": [
                {"path": "users", "fields": [{"name": "email", "type": "string"}]},
            ],
        }
        assert resolve_field_ref("firestore", config, "users.email") is True

    def test_missing_field(self):
        config = {
            "location_id": "us-central",
            "collections": [
                {"path": "users", "fields": [{"name": "email", "type": "string"}]},
            ],
        }
        assert resolve_field_ref("firestore", config, "users.nonexistent") is False

    def test_missing_collection(self):
        config = {"location_id": "us-central", "collections": []}
        assert resolve_field_ref("firestore", config, "users.email") is False


class TestCloudSqlResolution:
    def test_valid_column_path(self):
        config = {
            "database_version": "POSTGRES_15",
            "tier": "db-f1-micro",
            "databases": [{
                "name": "app_db",
                "tables": [{
                    "name": "users",
                    "columns": [{"name": "email", "type": "VARCHAR"}],
                }],
            }],
        }
        assert resolve_field_ref("cloud_sql", config, "app_db.users.email") is True

    def test_invalid_column(self):
        config = {
            "database_version": "POSTGRES_15",
            "tier": "db-f1-micro",
            "databases": [{
                "name": "app_db",
                "tables": [{
                    "name": "users",
                    "columns": [{"name": "email", "type": "VARCHAR"}],
                }],
            }],
        }
        assert resolve_field_ref("cloud_sql", config, "app_db.users.nope") is False


class TestBigQueryResolution:
    def test_valid_column(self):
        config = {
            "dataset_id": "analytics",
            "tables": [{
                "table_id": "events",
                "columns": [{"name": "user_id", "type": "STRING"}],
            }],
        }
        assert resolve_field_ref("bigquery", config, "events.user_id") is True

    def test_invalid_table(self):
        config = {
            "dataset_id": "analytics",
            "tables": [{
                "table_id": "events",
                "columns": [{"name": "user_id", "type": "STRING"}],
            }],
        }
        assert resolve_field_ref("bigquery", config, "nope.user_id") is False


class TestCollectStorageFields:
    def test_collect_firestore_fields(self):
        config = {
            "location_id": "us-central",
            "collections": [
                {"path": "users", "fields": [
                    {"name": "email", "type": "string"},
                    {"name": "name", "type": "string"},
                ]},
            ],
        }
        fields = collect_storage_fields("firestore", config)
        assert "users.email" in fields
        assert "users.name" in fields

    def test_unsupported_type_returns_empty(self):
        fields = collect_storage_fields("unknown_type", {})
        assert fields == []
