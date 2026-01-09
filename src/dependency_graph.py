"""Feature dependency graph and priority scoring.

This module provides dependency graph analysis for feature tracking,
including:

- Dependency graph construction
- Cycle detection
- Topological sorting
- Critical path analysis
- Priority scoring
- Execution planning
- Mermaid visualization
"""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class FeatureStatus(Enum):
    """Status of a feature in the development lifecycle."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"


@dataclass
class Feature:
    """A feature with dependencies and metadata."""

    id: str
    description: str
    priority: int
    dependencies: list[str] = field(default_factory=list)
    status: FeatureStatus = FeatureStatus.PENDING
    effort_estimate: int = 1  # Story points or hours
    passes: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Feature":
        """Create Feature from dictionary.

        Args:
            data: Dictionary with feature data

        Returns:
            Feature instance
        """
        status_str = data.get("status", "pending")
        status = FeatureStatus(status_str) if status_str in [s.value for s in FeatureStatus] else FeatureStatus.PENDING

        return cls(
            id=data["id"],
            description=data.get("description", ""),
            priority=data.get("priority", 99),
            dependencies=data.get("dependencies", []),
            status=status,
            effort_estimate=data.get("effort_estimate", 1),
            passes=data.get("passes", False),
        )


class DependencyGraph:
    """Graph of feature dependencies.

    Provides methods for:
    - Adding features and dependencies
    - Cycle detection
    - Topological sorting
    - Finding ready/blocked features
    - Mermaid diagram generation
    """

    def __init__(self) -> None:
        """Initialize empty dependency graph."""
        self._features: dict[str, Feature] = {}
        self._edges: dict[str, set[str]] = defaultdict(set)  # feature -> dependencies
        self._reverse_edges: dict[str, set[str]] = defaultdict(set)  # feature -> dependents

    @property
    def node_count(self) -> int:
        """Number of features in graph."""
        return len(self._features)

    def add_feature(self, feature: Feature) -> None:
        """Add a feature to the graph.

        Args:
            feature: Feature to add
        """
        self._features[feature.id] = feature

        # Add dependency edges
        for dep_id in feature.dependencies:
            self._edges[feature.id].add(dep_id)
            self._reverse_edges[dep_id].add(feature.id)

    def get_feature(self, feature_id: str) -> Feature | None:
        """Get feature by ID.

        Args:
            feature_id: The feature ID

        Returns:
            Feature if found, None otherwise
        """
        return self._features.get(feature_id)

    def get_dependencies(self, feature_id: str) -> set[str]:
        """Get direct dependencies of a feature.

        Args:
            feature_id: The feature ID

        Returns:
            Set of dependency feature IDs
        """
        return self._edges.get(feature_id, set())

    def get_dependents(self, feature_id: str) -> set[str]:
        """Get features that depend on this feature.

        Args:
            feature_id: The feature ID

        Returns:
            Set of dependent feature IDs
        """
        return self._reverse_edges.get(feature_id, set())

    def has_cycle(self) -> bool:
        """Check if graph has cycles.

        Returns:
            True if cycle detected
        """
        return len(self.find_cycles()) > 0

    def find_cycles(self) -> list[list[str]]:
        """Find all cycles in the graph.

        Returns:
            List of cycles (each cycle is a list of feature IDs)
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self._edges.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for node in self._features:
            if node not in visited:
                dfs(node)

        return cycles

    def topological_sort(self) -> list[Feature]:
        """Sort features in dependency order.

        Returns:
            Features in valid execution order (dependencies first)
        """
        if self.has_cycle():
            return []

        in_degree = defaultdict(int)
        for node in self._features:
            in_degree[node] = len(self._edges.get(node, set()))

        # Start with nodes that have no dependencies
        queue = [node for node in self._features if in_degree[node] == 0]
        result = []

        while queue:
            # Sort by priority within available nodes
            queue.sort(key=lambda x: self._features[x].priority)
            node = queue.pop(0)
            result.append(self._features[node])

            # Reduce in-degree for dependents
            for dependent in self._reverse_edges.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        return result

    def get_ready_features(self) -> list[Feature]:
        """Get features that are ready to start.

        A feature is ready if all its dependencies are complete.

        Returns:
            List of ready features
        """
        ready = []

        for feature in self._features.values():
            if feature.status == FeatureStatus.COMPLETE:
                continue
            if feature.status == FeatureStatus.IN_PROGRESS:
                continue

            # Check all dependencies are complete
            deps_complete = True
            for dep_id in feature.dependencies:
                dep = self._features.get(dep_id)
                if dep is None or dep.status != FeatureStatus.COMPLETE:
                    deps_complete = False
                    break

            if deps_complete:
                ready.append(feature)

        # Sort by priority
        ready.sort(key=lambda f: f.priority)
        return ready

    def get_blocked_features(self) -> list[Feature]:
        """Get features that are blocked by incomplete dependencies.

        Returns:
            List of blocked features
        """
        blocked = []

        for feature in self._features.values():
            if feature.status == FeatureStatus.COMPLETE:
                continue

            # Check if any dependency is not complete
            for dep_id in feature.dependencies:
                dep = self._features.get(dep_id)
                if dep is None or dep.status != FeatureStatus.COMPLETE:
                    blocked.append(feature)
                    break

        return blocked

    def to_mermaid(self) -> str:
        """Generate Mermaid diagram of the graph.

        Returns:
            Mermaid flowchart syntax
        """
        lines = ["graph TD"]

        # Add nodes with status styling
        for feature in self._features.values():
            style = ""
            if feature.status == FeatureStatus.COMPLETE:
                style = ":::complete"
            elif feature.status == FeatureStatus.IN_PROGRESS:
                style = ":::inprogress"
            elif feature.status == FeatureStatus.BLOCKED:
                style = ":::blocked"

            label = f"{feature.id}: {feature.description[:30]}"
            lines.append(f"    {feature.id}[\"{label}\"]{style}")

        # Add edges
        for feature_id, deps in self._edges.items():
            for dep_id in deps:
                lines.append(f"    {dep_id} --> {feature_id}")

        # Add style definitions
        lines.append("")
        lines.append("    classDef complete fill:#90EE90")
        lines.append("    classDef inprogress fill:#FFE4B5")
        lines.append("    classDef blocked fill:#FFB6C1")

        return "\n".join(lines)

    @classmethod
    def from_json(cls, filepath: Path) -> "DependencyGraph":
        """Load graph from features.json file.

        Args:
            filepath: Path to JSON file

        Returns:
            DependencyGraph instance
        """
        with open(filepath) as f:
            data = json.load(f)

        graph = cls()

        for feature_data in data.get("features", []):
            feature = Feature.from_dict(feature_data)
            graph.add_feature(feature)

        return graph


class CriticalPathAnalyzer:
    """Analyzes critical path through dependency graph."""

    def __init__(self, graph: DependencyGraph) -> None:
        """Initialize analyzer.

        Args:
            graph: The dependency graph to analyze
        """
        self.graph = graph

    def find_critical_path(self) -> list[Feature]:
        """Find the critical path (longest path through graph).

        The critical path determines the minimum time to complete all features.

        Returns:
            List of features on the critical path
        """
        if self.graph.has_cycle():
            return []

        # Calculate longest path to each node
        dist: dict[str, int] = {}
        pred: dict[str, str | None] = {}

        sorted_features = self.graph.topological_sort()

        for feature in sorted_features:
            dist[feature.id] = feature.effort_estimate
            pred[feature.id] = None

            # Check all dependencies
            for dep_id in feature.dependencies:
                if dep_id in dist:
                    new_dist = dist[dep_id] + feature.effort_estimate
                    if new_dist > dist[feature.id]:
                        dist[feature.id] = new_dist
                        pred[feature.id] = dep_id

        # Find the end of the critical path
        if not dist:
            return []

        end_node = max(dist.keys(), key=lambda x: dist[x])

        # Trace back to build path
        path = []
        current: str | None = end_node
        while current is not None:
            feature = self.graph.get_feature(current)
            if feature:
                path.append(feature)
            current = pred.get(current)

        return list(reversed(path))

    def calculate_priority_scores(self) -> dict[str, float]:
        """Calculate priority scores for all features.

        Score is based on:
        - Base priority value
        - Number of dependents (blocking factor)
        - Position in critical path

        Returns:
            Dictionary of feature ID to priority score
        """
        scores: dict[str, float] = {}
        critical_path = self.find_critical_path()
        critical_ids = {f.id for f in critical_path}

        for feature_id, feature in self.graph._features.items():
            # Base score from priority (lower priority number = higher score)
            base_score = 100 - feature.priority

            # Blocking factor (more dependents = higher priority)
            dependents = self.graph.get_dependents(feature_id)
            blocking_factor = len(dependents) * 10

            # Critical path bonus
            critical_bonus = 50 if feature_id in critical_ids else 0

            scores[feature_id] = base_score + blocking_factor + critical_bonus

        return scores


class ExecutionPlanner:
    """Plans execution order for features."""

    def __init__(self, graph: DependencyGraph) -> None:
        """Initialize planner.

        Args:
            graph: The dependency graph to plan
        """
        self.graph = graph
        self.analyzer = CriticalPathAnalyzer(graph)

    def create_sequential_plan(self) -> list[Feature]:
        """Create a sequential execution plan.

        Returns:
            Ordered list of features to execute
        """
        # Use topological sort with priority ordering
        return self.graph.topological_sort()

    def create_parallel_plan(self) -> list[list[Feature]]:
        """Create parallel execution plan (waves).

        Features in the same wave can be executed in parallel.

        Returns:
            List of waves, each wave is a list of features
        """
        if self.graph.has_cycle():
            return []

        waves: list[list[Feature]] = []
        remaining = set(self.graph._features.keys())
        completed: set[str] = set()

        while remaining:
            wave = []
            for feature_id in list(remaining):
                feature = self.graph.get_feature(feature_id)
                if feature is None:
                    remaining.remove(feature_id)
                    continue

                # Check if all deps are completed
                deps = self.graph.get_dependencies(feature_id)
                if deps <= completed:
                    wave.append(feature)

            if not wave:
                break  # No progress, likely a cycle

            # Sort wave by priority
            wave.sort(key=lambda f: f.priority)
            waves.append(wave)

            # Mark wave as completed
            for feature in wave:
                completed.add(feature.id)
                remaining.discard(feature.id)

        return waves

    def get_next_feature(self) -> Feature | None:
        """Get the next feature to work on.

        Returns:
            Next feature based on readiness and priority, or None
        """
        ready = self.graph.get_ready_features()
        if not ready:
            return None

        # Get priority scores
        scores = self.analyzer.calculate_priority_scores()

        # Sort by score (descending)
        ready.sort(key=lambda f: scores.get(f.id, 0), reverse=True)

        return ready[0]
