"""Unit tests for the CLI (analyze and query subcommands)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import networkx as nx
import pytest

# cli lives in src/; tests run with src/ on sys.path
import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_cli(*argv):
    """Invoke cli.main() with the given argv and return the exit code."""
    with patch.object(sys, "argv", ["cli", *argv]):
        return cli.main()


def _mock_orchestrator(errors=None):
    """Return a mock CartographerOrchestrator."""
    orch = MagicMock()
    orch.errors = errors or []
    orch.analyze_repository.return_value = (nx.DiGraph(), nx.DiGraph())
    return orch


# ---------------------------------------------------------------------------
# main() – no subcommand
# ---------------------------------------------------------------------------

class TestMainNoCommand:
    def test_exits_1_with_no_subcommand(self, capsys):
        with pytest.raises(SystemExit) as exc:
            _run_cli()
        assert exc.value.code == 1


# ---------------------------------------------------------------------------
# analyze subcommand – argument parsing
# ---------------------------------------------------------------------------

class TestAnalyzeCommand:
    def test_returns_0_on_success(self, tmp_path):
        with patch("cli.CartographerOrchestrator", return_value=_mock_orchestrator()):
            code = _run_cli("analyze", str(tmp_path))
        assert code == 0

    def test_returns_1_when_path_missing(self, tmp_path, capsys):
        missing = str(tmp_path / "nonexistent")
        code = _run_cli("analyze", missing)
        assert code == 1

    def test_returns_1_when_path_is_file(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("x")
        code = _run_cli("analyze", str(f))
        assert code == 1

    def test_returns_1_when_orchestrator_has_errors(self, tmp_path):
        orch = _mock_orchestrator(errors=["something broke"])
        with patch("cli.CartographerOrchestrator", return_value=orch):
            code = _run_cli("analyze", str(tmp_path))
        assert code == 1

    def test_incremental_flag_passed_to_orchestrator(self, tmp_path):
        orch = _mock_orchestrator()
        with patch("cli.CartographerOrchestrator", return_value=orch):
            _run_cli("analyze", str(tmp_path), "--incremental")
        _, kwargs = orch.analyze_repository.call_args
        assert kwargs.get("incremental") is True

    def test_skip_surveyor_flag(self, tmp_path):
        orch = _mock_orchestrator()
        with patch("cli.CartographerOrchestrator", return_value=orch):
            _run_cli("analyze", str(tmp_path), "--skip-surveyor")
        _, kwargs = orch.analyze_repository.call_args
        assert kwargs.get("skip_surveyor") is True

    def test_skip_hydrologist_flag(self, tmp_path):
        orch = _mock_orchestrator()
        with patch("cli.CartographerOrchestrator", return_value=orch):
            _run_cli("analyze", str(tmp_path), "--skip-hydrologist")
        _, kwargs = orch.analyze_repository.call_args
        assert kwargs.get("skip_hydrologist") is True

    def test_skip_semanticist_flag(self, tmp_path):
        orch = _mock_orchestrator()
        with patch("cli.CartographerOrchestrator", return_value=orch):
            _run_cli("analyze", str(tmp_path), "--skip-semanticist")
        _, kwargs = orch.analyze_repository.call_args
        assert kwargs.get("skip_semanticist") is True

    def test_skip_archivist_flag(self, tmp_path):
        orch = _mock_orchestrator()
        with patch("cli.CartographerOrchestrator", return_value=orch):
            _run_cli("analyze", str(tmp_path), "--skip-archivist")
        _, kwargs = orch.analyze_repository.call_args
        assert kwargs.get("skip_archivist") is True

    def test_semanticist_max_modules_flag(self, tmp_path):
        orch = _mock_orchestrator()
        with patch("cli.CartographerOrchestrator", return_value=orch):
            _run_cli("analyze", str(tmp_path), "--semanticist-max-modules", "50")
        _, kwargs = orch.analyze_repository.call_args
        assert kwargs.get("semanticist_max_modules") == 50

    def test_custom_output_dir_passed_to_orchestrator(self, tmp_path):
        with patch("cli.CartographerOrchestrator") as MockOrch:
            MockOrch.return_value = _mock_orchestrator()
            _run_cli("analyze", str(tmp_path), "--output-dir", ".mydir")
        MockOrch.assert_called_once_with(output_dir=".mydir")

    def test_keyboard_interrupt_returns_130(self, tmp_path):
        orch = _mock_orchestrator()
        orch.analyze_repository.side_effect = KeyboardInterrupt
        with patch("cli.CartographerOrchestrator", return_value=orch):
            code = _run_cli("analyze", str(tmp_path))
        assert code == 130

    def test_unexpected_exception_returns_1(self, tmp_path):
        orch = _mock_orchestrator()
        orch.analyze_repository.side_effect = RuntimeError("boom")
        with patch("cli.CartographerOrchestrator", return_value=orch):
            code = _run_cli("analyze", str(tmp_path))
        assert code == 1


# ---------------------------------------------------------------------------
# analyze subcommand – GitHub URL cloning
# ---------------------------------------------------------------------------

class TestAnalyzeGitHubURL:
    def test_clones_https_url(self, tmp_path):
        url = "https://github.com/owner/repo"
        mock_clone = MagicMock()
        mock_clone.returncode = 0

        with patch("subprocess.run", return_value=mock_clone) as mock_run, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("cli.CartographerOrchestrator", return_value=_mock_orchestrator()):
            code = _run_cli("analyze", url)

        assert code == 0
        clone_call = mock_run.call_args_list[0]
        cmd = clone_call[0][0]
        assert "git" in cmd
        assert "clone" in cmd
        assert url in cmd

    def test_returns_1_when_clone_fails(self, tmp_path):
        url = "https://github.com/owner/repo"
        mock_clone = MagicMock()
        mock_clone.returncode = 1

        with patch("subprocess.run", return_value=mock_clone), \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)):
            code = _run_cli("analyze", url)

        assert code == 1

    def test_clones_git_at_url(self, tmp_path):
        url = "git@github.com:owner/repo.git"
        mock_clone = MagicMock()
        mock_clone.returncode = 0

        with patch("subprocess.run", return_value=mock_clone), \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)), \
             patch("cli.CartographerOrchestrator", return_value=_mock_orchestrator()):
            code = _run_cli("analyze", url)

        assert code == 0


# ---------------------------------------------------------------------------
# query subcommand
# ---------------------------------------------------------------------------

class TestQueryCommand:
    def _write_graphs(self, output_dir: Path):
        """Write minimal graph JSON files so the query command can load them."""
        import json
        from networkx.readwrite import json_graph

        g = nx.DiGraph()
        data = json_graph.node_link_data(g)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "module_graph.json").write_text(json.dumps(data))
        (output_dir / "lineage_graph.json").write_text(json.dumps(data))

    def test_returns_1_when_graphs_missing(self, tmp_path):
        code = _run_cli("query", str(tmp_path))
        assert code == 1

    def test_launches_interactive_mode(self, tmp_path):
        output_dir = tmp_path / ".cartography"
        self._write_graphs(output_dir)

        mock_navigator = MagicMock()
        mock_navigator.interactive_mode.return_value = None

        with patch("analyzers.graph_serializer.GraphSerializer.deserialize_graph", return_value=nx.DiGraph()), \
             patch("agents.navigator.NavigatorAgent", return_value=mock_navigator):
            code = _run_cli("query", str(tmp_path))

        assert code == 0
        mock_navigator.interactive_mode.assert_called_once()

    def test_custom_output_dir_for_query(self, tmp_path):
        output_dir = tmp_path / ".custom"
        self._write_graphs(output_dir)

        mock_navigator = MagicMock()
        mock_navigator.interactive_mode.return_value = None

        with patch("analyzers.graph_serializer.GraphSerializer.deserialize_graph", return_value=nx.DiGraph()), \
             patch("agents.navigator.NavigatorAgent", return_value=mock_navigator):
            code = _run_cli("query", str(tmp_path), "--output-dir", ".custom")

        assert code == 0
