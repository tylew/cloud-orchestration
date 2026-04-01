"""Structural validation tests for the OPTIONS_REGISTRY."""

from core.options import OPTIONS_REGISTRY, GCP_REGIONS, GCP_MULTI_REGIONS, _LAST_UPDATED
from core.schemas.enums import NodeType
from core.schemas.configs import TYPE_TO_CONFIG


def test_last_updated_is_date_string():
    assert isinstance(_LAST_UPDATED, str)
    parts = _LAST_UPDATED.split("-")
    assert len(parts) == 3, "Expected YYYY-MM-DD format"


def test_all_registry_keys_use_valid_node_types():
    valid_types = set(NodeType)
    for (node_type, _field_path) in OPTIONS_REGISTRY:
        assert node_type in valid_types, f"Invalid NodeType: {node_type}"


def test_all_option_lists_are_nonempty_with_correct_shape():
    for key, options in OPTIONS_REGISTRY.items():
        assert len(options) > 0, f"Empty options for {key}"
        for opt in options:
            assert isinstance(opt, dict), f"Option is not a dict for {key}"
            assert "value" in opt and "label" in opt, f"Missing value/label for {key}"
            assert isinstance(opt["value"], str), f"value not str for {key}: {opt}"
            assert isinstance(opt["label"], str), f"label not str for {key}: {opt}"


def test_field_paths_resolve_against_config_models():
    """Verify that top-level field paths (no dots) exist on the Pydantic config model."""
    for (node_type, field_path) in OPTIONS_REGISTRY:
        if node_type not in TYPE_TO_CONFIG:
            continue  # child types without config models
        config_cls = TYPE_TO_CONFIG[node_type]
        top_field = field_path.split(".")[0]
        all_fields = set(config_cls.model_fields.keys())
        assert top_field in all_fields, (
            f"Field '{top_field}' (from path '{field_path}') "
            f"not found on {config_cls.__name__}. "
            f"Available: {sorted(all_fields)}"
        )


def test_gcp_regions_has_40_plus_entries():
    assert len(GCP_REGIONS) >= 40, f"Only {len(GCP_REGIONS)} regions"


def test_gcp_multi_regions():
    assert len(GCP_MULTI_REGIONS) >= 3
    values = {r["value"] for r in GCP_MULTI_REGIONS}
    assert "US" in values
    assert "EU" in values


def test_no_duplicate_values_per_option_list():
    for key, options in OPTIONS_REGISTRY.items():
        values = [o["value"] for o in options]
        assert len(values) == len(set(values)), f"Duplicate values in {key}"


def test_registry_covers_expected_node_types():
    """At least 15 distinct node types should have options."""
    node_types = {nt for (nt, _) in OPTIONS_REGISTRY}
    assert len(node_types) >= 15, f"Only {len(node_types)} node types covered"
