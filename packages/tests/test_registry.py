"""Registry completeness and lookup tests."""

from packages.core.registry import REGISTRY, get_definition, get_config_model, is_compute
from packages.core.schemas.enums import NodeType, COMPUTE_TYPES


class TestRegistryCompleteness:
    def test_all_node_types_registered(self):
        for nt in NodeType:
            assert nt in REGISTRY, f"{nt} missing from REGISTRY"

    def test_registry_count_matches_enum(self):
        assert len(REGISTRY) == len(NodeType)


class TestGetConfigModel:
    def test_returns_pydantic_class_for_each_type(self):
        for nt in NodeType:
            model = get_config_model(nt)
            assert model is not None, f"No config model for {nt}"

    def test_cloud_run_config_model_name(self):
        model = get_config_model(NodeType.CLOUD_RUN)
        assert model.__name__ == "CloudRunConfig"


class TestIsCompute:
    def test_compute_types_are_compute(self):
        for nt in COMPUTE_TYPES:
            assert is_compute(nt) is True

    def test_non_compute_types_are_not_compute(self):
        non_compute = set(NodeType) - COMPUTE_TYPES
        for nt in non_compute:
            assert is_compute(nt) is False
