"""Blueprint validation tests — required fields, duplicates, dependencies, parent refs."""

import pytest
from dataclasses import asdict

from core.schemas.base import Envelope
from core.validation import (
    validate_blueprint,
    validate_required_fields,
    validate_per_type_name_uniqueness,
    validate_firestore_free_tier,
    validate_parent_refs,
    ValidationIssue,
)


def _issues_by_severity(issues):
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    return errors, warnings


class TestValidateBlueprint:
    def test_valid_blueprint_no_errors(self, minimal_envelope):
        issues = validate_blueprint(minimal_envelope)
        errors, _ = _issues_by_severity(issues)
        assert len(errors) == 0

    def test_duplicate_node_names(self, duplicate_names_envelope_data):
        envelope = Envelope.model_validate(duplicate_names_envelope_data)
        issues = validate_blueprint(envelope)
        errors, _ = _issues_by_severity(issues)
        dup_errors = [e for e in errors if "Duplicate" in e.message]
        assert len(dup_errors) >= 1





class TestRequiredFields:
    def test_cloud_run_missing_image(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-service", "type": "cloud_run", "config": {}},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_required_fields(envelope.nodes)
        errors, _ = _issues_by_severity(issues)
        img_errors = [e for e in errors if "image" in e.message.lower()]
        assert len(img_errors) >= 1

    def test_cloud_sql_requires_database_version_and_tier(self):
        # Cloud SQL config fields have no defaults — passing them explicitly as empty strings
        # triggers the required-field validation logic (empty string is falsy).
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-db", "type": "cloud_sql", "config": {
                    "database_version": "POSTGRES_15", "tier": "db-f1-micro",
                }},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_required_fields(envelope.nodes)
        # Valid config should produce no errors for these fields
        errors, _ = _issues_by_severity(issues)
        version_errors = [e for e in errors if "version" in e.message.lower()]
        tier_errors = [e for e in errors if "tier" in e.message.lower()]
        assert len(version_errors) == 0
        assert len(tier_errors) == 0

    def test_warnings_for_pubsub_schema_without_definition(self):
        # pubsub_schema with no definition generates a warning (definition is optional)
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-schema", "type": "pubsub_schema", "config": {}},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_required_fields(envelope.nodes)
        _, warnings = _issues_by_severity(issues)
        assert any("definition" in w.message.lower() for w in warnings)


class TestNameUniqueness:
    def test_duplicate_same_type(self, duplicate_names_envelope_data):
        envelope = Envelope.model_validate(duplicate_names_envelope_data)
        issues = validate_per_type_name_uniqueness(envelope.nodes)
        assert len(issues) >= 1
        assert issues[0].severity == "error"

    def test_same_name_different_types_ok(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-resource", "type": "vpc", "config": {"auto_create_subnetworks": False}},
                {"name": "my-resource", "type": "gcs_bucket", "config": {"location": "US"}},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_per_type_name_uniqueness(envelope.nodes)
        assert len(issues) == 0


class TestFirestoreFreeTier:
    def test_default_database_no_warning(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-fs", "type": "firestore", "config": {
                    "location_id": "us-central",
                }},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_firestore_free_tier(envelope.nodes)
        assert len(issues) == 0

    def test_non_default_database_warns(self):
        """With database_id removed from schema, this check is now a no-op."""
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-fs", "type": "firestore", "config": {
                    "location_id": "us-central",
                }},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_firestore_free_tier(envelope.nodes)
        assert len(issues) == 0


class TestChildParentValidation:
    def test_missing_parent_ref(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-db", "type": "cloud_sql", "config": {
                    "database_version": "POSTGRES_15", "tier": "db-f1-micro",
                }, "slug": "sql-abc123"},
                {"name": "orphan-db", "type": "cloud_sql_database", "config": {
                    "parentRef": "nonexistent-slug",
                    "name": "orphan-db",
                }, "slug": "sqldb-xyz"},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_parent_refs(envelope.nodes)
        errors = [i for i in issues if i.severity == "error"]
        assert any("non-existent" in e.message for e in errors)
