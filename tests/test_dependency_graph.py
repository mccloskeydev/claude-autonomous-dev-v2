"""Tests for feature dependency graph and priority scoring."""

import json
import tempfile
from pathlib import Path

from src.dependency_graph import (
    CriticalPathAnalyzer,
    DependencyGraph,
    ExecutionPlanner,
    Feature,
    FeatureStatus,
)


class TestFeature:
    """Tests for Feature data class."""

    def test_feature_creation(self):
        """Should create a feature with required fields."""
        feature = Feature(
            id="F001",
            description="Test feature",
            priority=1,
        )
        assert feature.id == "F001"
        assert feature.priority == 1
        assert feature.status == FeatureStatus.PENDING

    def test_feature_with_dependencies(self):
        """Should create feature with dependencies."""
        feature = Feature(
            id="F002",
            description="Depends on F001",
            priority=2,
            dependencies=["F001"],
        )
        assert "F001" in feature.dependencies

    def test_feature_status_transitions(self):
        """Should allow status transitions."""
        feature = Feature(id="F001", description="Test", priority=1)
        assert feature.status == FeatureStatus.PENDING

        feature.status = FeatureStatus.IN_PROGRESS
        assert feature.status == FeatureStatus.IN_PROGRESS

        feature.status = FeatureStatus.COMPLETE
        assert feature.status == FeatureStatus.COMPLETE


class TestDependencyGraph:
    """Tests for dependency graph construction."""

    def test_empty_graph(self):
        """Should handle empty graph."""
        graph = DependencyGraph()
        assert graph.node_count == 0

    def test_add_feature(self):
        """Should add features to graph."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Feature 1", priority=1)
        graph.add_feature(f1)

        assert graph.node_count == 1
        assert graph.get_feature("F001") == f1

    def test_add_dependency(self):
        """Should add dependency edges."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Feature 1", priority=1)
        f2 = Feature(id="F002", description="Feature 2", priority=2, dependencies=["F001"])

        graph.add_feature(f1)
        graph.add_feature(f2)

        deps = graph.get_dependencies("F002")
        assert "F001" in deps

    def test_get_dependents(self):
        """Should find features that depend on a given feature."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Base", priority=1)
        f2 = Feature(id="F002", description="Dep 1", priority=2, dependencies=["F001"])
        f3 = Feature(id="F003", description="Dep 2", priority=2, dependencies=["F001"])

        graph.add_feature(f1)
        graph.add_feature(f2)
        graph.add_feature(f3)

        dependents = graph.get_dependents("F001")
        assert "F002" in dependents
        assert "F003" in dependents

    def test_detect_cycle(self):
        """Should detect circular dependencies."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Feature 1", priority=1, dependencies=["F003"])
        f2 = Feature(id="F002", description="Feature 2", priority=2, dependencies=["F001"])
        f3 = Feature(id="F003", description="Feature 3", priority=3, dependencies=["F002"])

        graph.add_feature(f1)
        graph.add_feature(f2)
        graph.add_feature(f3)

        assert graph.has_cycle()
        cycles = graph.find_cycles()
        assert len(cycles) > 0

    def test_no_cycle_valid_graph(self):
        """Should not report cycle in valid graph."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Feature 1", priority=1)
        f2 = Feature(id="F002", description="Feature 2", priority=2, dependencies=["F001"])
        f3 = Feature(id="F003", description="Feature 3", priority=3, dependencies=["F002"])

        graph.add_feature(f1)
        graph.add_feature(f2)
        graph.add_feature(f3)

        assert not graph.has_cycle()

    def test_topological_sort(self):
        """Should return features in valid execution order."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Base", priority=1)
        f2 = Feature(id="F002", description="Mid", priority=2, dependencies=["F001"])
        f3 = Feature(id="F003", description="Top", priority=3, dependencies=["F002"])

        graph.add_feature(f1)
        graph.add_feature(f2)
        graph.add_feature(f3)

        order = graph.topological_sort()
        ids = [f.id for f in order]

        # F001 must come before F002, F002 must come before F003
        assert ids.index("F001") < ids.index("F002")
        assert ids.index("F002") < ids.index("F003")

    def test_load_from_features_json(self):
        """Should load graph from features.json format."""
        features_data = {
            "version": "2.0",
            "features": [
                {"id": "F001", "description": "Base", "priority": 1, "dependencies": []},
                {"id": "F002", "description": "Mid", "priority": 2, "dependencies": ["F001"]},
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(features_data, f)
            f.flush()

            graph = DependencyGraph.from_json(Path(f.name))

            assert graph.node_count == 2
            assert "F001" in graph.get_dependencies("F002")


class TestFeatureStatus:
    """Tests for feature status tracking."""

    def test_ready_features(self):
        """Should identify features ready to start."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Base", priority=1)
        f2 = Feature(id="F002", description="Dep", priority=2, dependencies=["F001"])

        graph.add_feature(f1)
        graph.add_feature(f2)

        # Only F001 should be ready (no deps)
        ready = graph.get_ready_features()
        assert len(ready) == 1
        assert ready[0].id == "F001"

    def test_ready_after_completion(self):
        """Should mark dependent features ready after deps complete."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Base", priority=1, status=FeatureStatus.COMPLETE)
        f2 = Feature(id="F002", description="Dep", priority=2, dependencies=["F001"])

        graph.add_feature(f1)
        graph.add_feature(f2)

        ready = graph.get_ready_features()
        assert any(f.id == "F002" for f in ready)

    def test_blocked_features(self):
        """Should identify blocked features."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Base", priority=1)  # Not complete
        f2 = Feature(id="F002", description="Blocked", priority=2, dependencies=["F001"])

        graph.add_feature(f1)
        graph.add_feature(f2)

        blocked = graph.get_blocked_features()
        assert any(f.id == "F002" for f in blocked)


class TestCriticalPath:
    """Tests for critical path analysis."""

    def test_critical_path_simple(self):
        """Should find critical path in simple graph."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Base", priority=1, effort_estimate=2)
        f2 = Feature(id="F002", description="Mid", priority=2, dependencies=["F001"], effort_estimate=3)
        f3 = Feature(id="F003", description="Top", priority=3, dependencies=["F002"], effort_estimate=1)

        graph.add_feature(f1)
        graph.add_feature(f2)
        graph.add_feature(f3)

        analyzer = CriticalPathAnalyzer(graph)
        path = analyzer.find_critical_path()

        assert len(path) == 3
        assert path[0].id == "F001"
        assert path[-1].id == "F003"

    def test_critical_path_parallel(self):
        """Should find longest path when multiple exist."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Base", priority=1, effort_estimate=1)
        # Two parallel paths from F001
        f2 = Feature(id="F002", description="Short", priority=2, dependencies=["F001"], effort_estimate=1)
        f3 = Feature(id="F003", description="Long", priority=2, dependencies=["F001"], effort_estimate=5)
        f4 = Feature(id="F004", description="End", priority=3, dependencies=["F002", "F003"], effort_estimate=1)

        graph.add_feature(f1)
        graph.add_feature(f2)
        graph.add_feature(f3)
        graph.add_feature(f4)

        analyzer = CriticalPathAnalyzer(graph)
        path = analyzer.find_critical_path()

        # Should include the longer path through F003
        path_ids = [f.id for f in path]
        assert "F003" in path_ids

    def test_priority_scoring(self):
        """Should calculate priority scores."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Base", priority=1)
        f2 = Feature(id="F002", description="Dep", priority=2, dependencies=["F001"])
        f3 = Feature(id="F003", description="Independent", priority=1)

        graph.add_feature(f1)
        graph.add_feature(f2)
        graph.add_feature(f3)

        analyzer = CriticalPathAnalyzer(graph)
        scores = analyzer.calculate_priority_scores()

        # F001 should have higher score (blocks F002)
        assert scores["F001"] >= scores["F003"]


class TestExecutionPlanner:
    """Tests for execution planning."""

    def test_sequential_plan(self):
        """Should create sequential execution plan."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="First", priority=1)
        f2 = Feature(id="F002", description="Second", priority=2, dependencies=["F001"])

        graph.add_feature(f1)
        graph.add_feature(f2)

        planner = ExecutionPlanner(graph)
        plan = planner.create_sequential_plan()

        assert len(plan) == 2
        assert plan[0].id == "F001"
        assert plan[1].id == "F002"

    def test_parallel_plan(self):
        """Should identify features that can run in parallel."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Base 1", priority=1)
        f2 = Feature(id="F002", description="Base 2", priority=1)
        f3 = Feature(id="F003", description="Dep", priority=2, dependencies=["F001", "F002"])

        graph.add_feature(f1)
        graph.add_feature(f2)
        graph.add_feature(f3)

        planner = ExecutionPlanner(graph)
        waves = planner.create_parallel_plan()

        # First wave should have F001 and F002
        assert len(waves) >= 2
        first_wave_ids = [f.id for f in waves[0]]
        assert "F001" in first_wave_ids
        assert "F002" in first_wave_ids

    def test_next_feature(self):
        """Should return next feature to work on."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="First", priority=1)
        f2 = Feature(id="F002", description="Second", priority=2, dependencies=["F001"])

        graph.add_feature(f1)
        graph.add_feature(f2)

        planner = ExecutionPlanner(graph)
        next_feature = planner.get_next_feature()

        assert next_feature is not None
        assert next_feature.id == "F001"

    def test_next_feature_respects_priority(self):
        """Should prefer higher priority features when multiple ready."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Low priority", priority=3)
        f2 = Feature(id="F002", description="High priority", priority=1)

        graph.add_feature(f1)
        graph.add_feature(f2)

        planner = ExecutionPlanner(graph)
        next_feature = planner.get_next_feature()

        # Should pick the higher priority (lower number)
        assert next_feature.id == "F002"


class TestVisualization:
    """Tests for graph visualization."""

    def test_generate_mermaid(self):
        """Should generate Mermaid diagram."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Base", priority=1)
        f2 = Feature(id="F002", description="Dep", priority=2, dependencies=["F001"])

        graph.add_feature(f1)
        graph.add_feature(f2)

        mermaid = graph.to_mermaid()

        assert "graph TD" in mermaid or "flowchart" in mermaid
        assert "F001" in mermaid
        assert "F002" in mermaid
        assert "-->" in mermaid  # Edge notation

    def test_mermaid_status_colors(self):
        """Should include status indicators in mermaid."""
        graph = DependencyGraph()
        f1 = Feature(id="F001", description="Complete", priority=1, status=FeatureStatus.COMPLETE)
        f2 = Feature(id="F002", description="Pending", priority=2, dependencies=["F001"])

        graph.add_feature(f1)
        graph.add_feature(f2)

        mermaid = graph.to_mermaid()

        # Should indicate status somehow (color, style, etc.)
        assert "F001" in mermaid
