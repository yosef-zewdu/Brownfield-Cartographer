"""Unit tests for CartographerOrchestrator."""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import networkx as nx
import pytest

from orchestrator import CartographerOrchestrator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_module_graph(*nodes):
    g = nx.DiGraph()
    for n in nodes:
        g.add_node(n, path=n, language="python", complexity_score=1,
                   imports=[], exports=[],
                   provenance={"evidence_type": "tree_sitter",
                               "source_file": n, "confidence": 1.0,
                               "resolution_status": "resolved"})
    return g


def _make_lineage_graph():
    return nx.DiGraph()


def _mock_surveyor(graph=None, modules=None):
    s = MagicMock()
    s.analyze_repository.return_value = (graph or _make_module_graph("a.py"), modules or [])
    s.errors = []
    s.detect_circular_dependencies.return_value = []
    return s


def _mock_hydrologist(graph=None):
    h = MagicMock()
    h.analyze_repository.return_value = (graph or _make_lineage_graph(), [], [])
    h.errors = []
    h.find_sources.return_value = []
    h.find_sinks.return_value = []
    h.serialize_lineage_graph.return_value = None
    return h


def _mock_semanticist():
    s = MagicMock()
    s.analyze_repository.return_value = ([], {})
    s.budget_tracker = MagicMock()
    s.budget_tracker.get_usage_summary.return_value = {}
    return s


def _mock_archivist():
    a = MagicMock()
    a.generate_artifacts.return_value = {}
    return a


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestInit:
    def test_default_output_dir(self):
        orch = CartographerOrchestrator()
        assert orch.output_dir_name == ".cartography"

    def test_custom_output_dir(self):
        orch = CartographerOrchestrator(output_dir=".mydir")
        assert orch.output_dir_name == ".mydir"

    def test_errors_list_starts_empty(self):
        orch = CartographerOrchestrator()
        assert orch.errors == []

    def test_agents_initialized(self):
        orch = CartographerOrchestrator()
        assert orch.surveyor is not None
        assert orch.hydrologist is not None
        assert orch.semanticist is not None
        assert orch.trace_logger is not None


# ---------------------------------------------------------------------------
# analyze_repository – validation
# ---------------------------------------------------------------------------

class TestAnalyzeRepositoryValidation:
    def test_raises_on_missing_path(self, tmp_path):
        orch = CartographerOrchestrator()
        with pytest.raises(ValueError, match="does not exist"):
            orch.analyze_repository(str(tmp_path / "nonexistent"))

    def test_raises_on_file_path(self, tmp_path):
        f = tmp_path / "file.py"
        f.write_text("x")
        orch = CartographerOrchestrator()
        with pytest.raises(ValueError, match="not a directory"):
            orch.analyze_repository(str(f))

    def test_creates_output_dir(self, tmp_path):
        orch = CartographerOrchestrator(output_dir=".out")
        orch.surveyor = _mock_surveyor()
        orch.hydrologist = _mock_hydrologist()
        orch.semanticist = _mock_semanticist()

        with patch("orchestrator.ArchivistAgent", return_value=_mock_archivist()):
            orch.analyze_repository(str(tmp_path), skip_semanticist=True, skip_archivist=True)

        assert (tmp_path / ".out").is_dir()


# ---------------------------------------------------------------------------
# analyze_repository – phase skipping
# ---------------------------------------------------------------------------

class TestAnalyzeRepositoryPhaseSkipping:
    def test_skip_surveyor_loads_existing_graph(self, tmp_path):
        output_dir = tmp_path / ".cartography"
        output_dir.mkdir()

        # Write a minimal graph file
        g = _make_module_graph("a.py")
        from analyzers.graph_serializer import GraphSerializer
        GraphSerializer.serialize_module_graph(g, str(output_dir / "module_graph.json"))

        orch = CartographerOrchestrator()
        mock_surveyor = _mock_surveyor()
        orch.surveyor = mock_surveyor
        orch.hydrologist = _mock_hydrologist()
        orch.semanticist = _mock_semanticist()

        with patch("orchestrator.ArchivistAgent", return_value=_mock_archivist()):
            module_graph, _ = orch.analyze_repository(
                str(tmp_path), skip_surveyor=True, skip_semanticist=True, skip_archivist=True
            )

        assert module_graph is not None
        mock_surveyor.analyze_repository.assert_not_called()

    def test_skip_surveyor_returns_none_when_no_graph_file(self, tmp_path):
        orch = CartographerOrchestrator()
        module_graph, lineage_graph = orch.analyze_repository(
            str(tmp_path), skip_surveyor=True
        )
        assert module_graph is None
        assert lineage_graph is None

    def test_skip_hydrologist(self, tmp_path):
        orch = CartographerOrchestrator()
        orch.surveyor = _mock_surveyor()
        orch.hydrologist = _mock_hydrologist()
        orch.semanticist = _mock_semanticist()

        with patch("orchestrator.ArchivistAgent", return_value=_mock_archivist()):
            orch.analyze_repository(
                str(tmp_path), skip_hydrologist=True, skip_semanticist=True, skip_archivist=True
            )

        orch.hydrologist.analyze_repository.assert_not_called()

    def test_skip_semanticist(self, tmp_path):
        orch = CartographerOrchestrator()
        orch.surveyor = _mock_surveyor()
        orch.hydrologist = _mock_hydrologist()
        orch.semanticist = _mock_semanticist()

        with patch("orchestrator.ArchivistAgent", return_value=_mock_archivist()):
            orch.analyze_repository(
                str(tmp_path), skip_semanticist=True, skip_archivist=True
            )

        orch.semanticist.analyze_repository.assert_not_called()

    def test_skip_archivist(self, tmp_path):
        orch = CartographerOrchestrator()
        orch.surveyor = _mock_surveyor()
        orch.hydrologist = _mock_hydrologist()
        orch.semanticist = _mock_semanticist()

        mock_archivist_cls = MagicMock()
        with patch("orchestrator.ArchivistAgent", mock_archivist_cls):
            orch.analyze_repository(
                str(tmp_path), skip_semanticist=True, skip_archivist=True
            )

        mock_archivist_cls.assert_not_called()


# ---------------------------------------------------------------------------
# analyze_repository – return values
# ---------------------------------------------------------------------------

class TestAnalyzeRepositoryReturnValues:
    def test_returns_module_and_lineage_graphs(self, tmp_path):
        mod_graph = _make_module_graph("a.py")
        lin_graph = _make_lineage_graph()

        orch = CartographerOrchestrator()
        orch.surveyor = _mock_surveyor(graph=mod_graph)
        orch.hydrologist = _mock_hydrologist(graph=lin_graph)
        orch.semanticist = _mock_semanticist()

        with patch("orchestrator.ArchivistAgent", return_value=_mock_archivist()):
            mg, lg = orch.analyze_repository(
                str(tmp_path), skip_semanticist=True, skip_archivist=True
            )

        # Graphs are returned (may be same object or equivalent)
        assert isinstance(mg, nx.DiGraph)
        assert isinstance(lg, nx.DiGraph)
        assert mg.number_of_nodes() == mod_graph.number_of_nodes()

    def test_returns_none_none_when_surveyor_fails(self, tmp_path):
        orch = CartographerOrchestrator()
        orch.surveyor = MagicMock()
        orch.surveyor.analyze_repository.side_effect = RuntimeError("parse error")
        orch.surveyor.errors = []

        mg, lg = orch.analyze_repository(str(tmp_path))

        assert mg is None
        assert lg is None

    def test_errors_list_populated_on_surveyor_failure(self, tmp_path):
        orch = CartographerOrchestrator()
        orch.surveyor = MagicMock()
        orch.surveyor.analyze_repository.side_effect = RuntimeError("boom")
        orch.surveyor.errors = []

        orch.analyze_repository(str(tmp_path))

        assert len(orch.errors) > 0
        assert any("Surveyor" in e for e in orch.errors)


# ---------------------------------------------------------------------------
# analyze_repository – metadata.json written
# ---------------------------------------------------------------------------

class TestMetadataFile:
    def test_metadata_json_written(self, tmp_path):
        orch = CartographerOrchestrator()
        orch.surveyor = _mock_surveyor()
        orch.hydrologist = _mock_hydrologist()
        orch.semanticist = _mock_semanticist()

        with patch("orchestrator.ArchivistAgent", return_value=_mock_archivist()):
            orch.analyze_repository(
                str(tmp_path), skip_semanticist=True, skip_archivist=True
            )

        metadata_path = tmp_path / ".cartography" / "metadata.json"
        assert metadata_path.exists()
        data = json.loads(metadata_path.read_text())
        assert "last_analysis_time" in data
        assert "repo_path" in data

    def test_metadata_contains_valid_iso_timestamp(self, tmp_path):
        orch = CartographerOrchestrator()
        orch.surveyor = _mock_surveyor()
        orch.hydrologist = _mock_hydrologist()
        orch.semanticist = _mock_semanticist()

        with patch("orchestrator.ArchivistAgent", return_value=_mock_archivist()):
            orch.analyze_repository(
                str(tmp_path), skip_semanticist=True, skip_archivist=True
            )

        data = json.loads((tmp_path / ".cartography" / "metadata.json").read_text())
        # Should parse without error
        datetime.fromisoformat(data["last_analysis_time"])


# ---------------------------------------------------------------------------
# analyze_repository – incremental mode
# ---------------------------------------------------------------------------

class TestIncrementalMode:
    def _write_metadata(self, output_dir: Path, ts: str):
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "metadata.json").write_text(
            json.dumps({"last_analysis_time": ts, "repo_path": str(output_dir.parent)})
        )

    def test_incremental_calls_detect_changes(self, tmp_path):
        self._write_metadata(tmp_path / ".cartography", "2024-01-01T00:00:00+00:00")

        orch = CartographerOrchestrator()
        orch.surveyor = _mock_surveyor()
        orch.hydrologist = _mock_hydrologist()
        orch.semanticist = _mock_semanticist()

        mock_mgr = MagicMock()
        mock_mgr.detect_changes.return_value = []

        with patch("orchestrator.IncrementalUpdateManager", return_value=mock_mgr), \
             patch("orchestrator.ArchivistAgent", return_value=_mock_archivist()):
            orch.analyze_repository(
                str(tmp_path), incremental=True, skip_semanticist=True, skip_archivist=True
            )

        mock_mgr.detect_changes.assert_called_once()

    def test_incremental_skips_detect_when_no_metadata(self, tmp_path):
        orch = CartographerOrchestrator()
        orch.surveyor = _mock_surveyor()
        orch.hydrologist = _mock_hydrologist()
        orch.semanticist = _mock_semanticist()

        mock_mgr = MagicMock()

        with patch("orchestrator.IncrementalUpdateManager", return_value=mock_mgr), \
             patch("orchestrator.ArchivistAgent", return_value=_mock_archivist()):
            orch.analyze_repository(
                str(tmp_path), incremental=True, skip_semanticist=True, skip_archivist=True
            )

        mock_mgr.detect_changes.assert_not_called()


# ---------------------------------------------------------------------------
# run_* delegation methods
# ---------------------------------------------------------------------------

class TestRunMethods:
    def test_run_surveyor_delegates_to_agent(self):
        orch = CartographerOrchestrator()
        orch.surveyor = _mock_surveyor()
        orch.run_surveyor("/some/path")
        orch.surveyor.analyze_repository.assert_called_once_with("/some/path")

    def test_run_hydrologist_delegates_to_agent(self):
        orch = CartographerOrchestrator()
        orch.hydrologist = _mock_hydrologist()
        g = nx.DiGraph()
        orch.run_hydrologist("/some/path", g)
        orch.hydrologist.analyze_repository.assert_called_once_with("/some/path", g)

    def test_run_semanticist_delegates_to_agent(self):
        orch = CartographerOrchestrator()
        orch.semanticist = _mock_semanticist()
        g = nx.DiGraph()
        orch.run_semanticist([], g, g, [], [])
        orch.semanticist.analyze_repository.assert_called_once()

    def test_run_archivist_creates_archivist_and_calls_generate(self, tmp_path):
        orch = CartographerOrchestrator()
        mock_archivist = _mock_archivist()

        with patch("orchestrator.ArchivistAgent", return_value=mock_archivist) as MockCls:
            orch.run_archivist(tmp_path, [], {}, nx.DiGraph(), nx.DiGraph())

        MockCls.assert_called_once_with(output_dir=tmp_path)
        mock_archivist.generate_artifacts.assert_called_once()


# ---------------------------------------------------------------------------
# handle_errors
# ---------------------------------------------------------------------------

class TestHandleErrors:
    def test_returns_error_count(self):
        orch = CartographerOrchestrator()
        result = orch.handle_errors([ValueError("a"), RuntimeError("b")])
        assert result["error_count"] == 2

    def test_returns_error_strings(self):
        orch = CartographerOrchestrator()
        result = orch.handle_errors([ValueError("oops")])
        assert "oops" in result["errors"][0]

    def test_empty_errors(self):
        orch = CartographerOrchestrator()
        result = orch.handle_errors([])
        assert result["error_count"] == 0
        assert result["errors"] == []
