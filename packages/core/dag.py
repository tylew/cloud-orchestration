"""Unified DAG service -- single source of truth for all graph operations (per D-01).

Consolidates topological sort, cycle detection, edge inference, and IAM inference
into a single BlueprintDAG class. Replaces custom Kahn's algorithm implementations
in resolver.py and validation.py with stdlib graphlib.TopologicalSorter (per D-03).
"""

from graphlib import TopologicalSorter, CycleError

from packages.core.schemas.base import BaseNode, Envelope


class BlueprintDAG:
    """Unified DAG service -- single source of truth for all graph operations (per D-01)."""

    def __init__(self, envelope: Envelope):
        self.envelope = envelope
        # Index by both name and slug so depends_on can use either
        self._node_map: dict[str, BaseNode] = {}
        for n in envelope.nodes:
            self._node_map[n.name] = n
            if n.slug and n.slug != n.name:
                self._node_map[n.slug] = n
        self._graph: dict[str, set[str]] = self._build_graph()

    def _build_graph(self) -> dict[str, set[str]]:
        """Build adjacency dict: node -> set of its dependencies (predecessors).

        graphlib.TopologicalSorter expects {node: {predecessors}} format.
        """
        graph: dict[str, set[str]] = {n.name: set() for n in self.envelope.nodes}
        # Also add slug keys so depends_on can reference either
        for n in self.envelope.nodes:
            if n.slug and n.slug != n.name and n.slug not in graph:
                graph[n.slug] = set()
        for node in self.envelope.nodes:
            node_key = node.name
            for dep in node.depends_on:
                if dep in graph:
                    graph[node_key].add(dep)
        return graph

    def topological_sort(self) -> list[BaseNode]:
        """Return nodes in dependency order using graphlib.TopologicalSorter (per D-03).

        Replaces custom Kahn's implementations in resolver.py and validation.py.
        Raises ValueError on circular dependencies.
        """
        sorter = TopologicalSorter(self._graph)
        try:
            ordered_names = list(sorter.static_order())
        except CycleError as e:
            raise ValueError(f"Circular dependency detected: {e}") from e
        return [self._node_map[name] for name in ordered_names if name in self._node_map]

    def validate_ordering(self) -> list[str]:
        """Validate dependency graph. Returns list of error messages (empty = valid).

        Checks for:
        1. References to non-existent nodes in depends_on
        2. Circular dependencies
        """
        errors: list[str] = []

        # Check for missing dependencies (accept both name and slug)
        all_names = set(self._node_map.keys())
        for node in self.envelope.nodes:
            for dep in node.depends_on:
                if dep not in all_names:
                    errors.append(f"Node '{node.name}' depends on unknown node: '{dep}'")

        # Check for cycles using graphlib
        try:
            sorter = TopologicalSorter(self._graph)
            sorter.prepare()
        except CycleError as e:
            cycle_nodes = e.args[1] if len(e.args) > 1 else []
            node_names = ", ".join(str(n) for n in cycle_nodes)
            errors.append(f"Circular dependency detected among nodes: {node_names}")

        return errors

    def parallel_batches(self) -> list[set[str]]:
        """Return groups of node names that can execute in parallel.

        Uses graphlib.TopologicalSorter.prepare()/get_ready()/done() protocol
        to produce parallel-safe batch ordering.
        """
        sorter = TopologicalSorter(self._graph)
        batches: list[set[str]] = []
        sorter.prepare()
        while sorter.is_active():
            batch = sorter.get_ready()
            batches.append(set(batch))
            for name in batch:
                sorter.done(name)
        return batches

