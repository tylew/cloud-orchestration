"""DAG topological sort, cycle detection, and parallel batch tests."""

import pytest
from core.dag import BlueprintDAG
from core.schemas.base import Envelope


class TestTopologicalSort:
    def test_simple_chain(self, minimal_envelope):
        dag = BlueprintDAG(minimal_envelope)
        ordered = dag.topological_sort()
        names = [n.name for n in ordered]
        assert names.index("my-service") > names.index("my-vpc")
        assert names.index("my-service") > names.index("my-sa")

    def test_complex_ordering(self, complex_envelope):
        dag = BlueprintDAG(complex_envelope)
        ordered = dag.topological_sort()
        names = [n.name for n in ordered]
        assert names.index("my-subnet") > names.index("my-vpc")
        for dep in ["my-sa", "my-db", "my-firestore", "my-bucket"]:
            assert names.index("my-service") > names.index(dep)

    def test_no_dependencies(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "a", "type": "vpc", "config": {"auto_create_subnetworks": False}},
                {"name": "b", "type": "vpc", "config": {"auto_create_subnetworks": False}},
            ],
        }
        envelope = Envelope.model_validate(data)
        dag = BlueprintDAG(envelope)
        ordered = dag.topological_sort()
        assert len(ordered) == 2


class TestCycleDetection:
    def test_cycle_raises_value_error(self, cyclic_envelope_data):
        envelope = Envelope.model_validate(cyclic_envelope_data)
        dag = BlueprintDAG(envelope)
        with pytest.raises(ValueError, match="Circular dependency"):
            dag.topological_sort()

    def test_validate_ordering_reports_cycle(self, cyclic_envelope_data):
        envelope = Envelope.model_validate(cyclic_envelope_data)
        dag = BlueprintDAG(envelope)
        errors = dag.validate_ordering()
        assert any("Circular" in e or "cycle" in e.lower() for e in errors)


class TestValidateOrdering:
    def test_missing_dependency(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "a", "type": "vpc", "config": {"auto_create_subnetworks": False},
                 "depends_on": ["nonexistent"]},
            ],
        }
        envelope = Envelope.model_validate(data)
        dag = BlueprintDAG(envelope)
        errors = dag.validate_ordering()
        assert any("nonexistent" in e for e in errors)

    def test_valid_graph_has_no_errors(self, minimal_envelope):
        dag = BlueprintDAG(minimal_envelope)
        errors = dag.validate_ordering()
        assert errors == []


class TestParallelBatches:
    def test_independent_nodes_in_same_batch(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "a", "type": "vpc", "config": {"auto_create_subnetworks": False}},
                {"name": "b", "type": "vpc", "config": {"auto_create_subnetworks": False}},
                {"name": "c", "type": "vpc", "config": {"auto_create_subnetworks": False}},
            ],
        }
        envelope = Envelope.model_validate(data)
        dag = BlueprintDAG(envelope)
        batches = dag.parallel_batches()
        assert len(batches) == 1
        assert batches[0] == {"a", "b", "c"}

    def test_dependent_nodes_in_different_batches(self, minimal_envelope):
        dag = BlueprintDAG(minimal_envelope)
        batches = dag.parallel_batches()
        assert len(batches) >= 2
        service_batch = next(i for i, b in enumerate(batches) if "my-service" in b)
        vpc_batch = next(i for i, b in enumerate(batches) if "my-vpc" in b)
        assert service_batch > vpc_batch
