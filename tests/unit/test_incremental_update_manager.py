"""Unit tests for IncrementalUpdateManager."""

import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import networkx as nx
import pytest

from agents.incremental_update_manager import IncrementalUpdateManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_graph(*nodes, edges=None):
    """Build a simple DiGraph with optional path attributes and edges."""
    g = nx.DiGraph()
    for n in nodes:
        g.add_node(n, path=n)
    for u, v in (edges or []):
        g.add_edge(u, v)
    return g


# ---------------------------------------------------------------------------
# detect_changes
# ---------------------------------------------------------------------------

class TestDetectChanges:
    def test_returns_empty_when_no_git_dir(self, tmp_path):
        mgr = IncrementalUpdateManager()
        result = mgr.detect_changes(str(tmp_path), datetime.now())
        assert result == []

    def test_returns_changed_files_from_git(self, tmp_path):
        (tmp_path / ".git").mkdir()
        mgr = IncrementalUpdateManager()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "src/foo.py\nsrc/bar.py\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = mgr.detect_changes(str(tmp_path), datetime(2024, 1, 1))

        assert result == ["src/foo.py", "src/bar.py"]
        called_cmd = mock_run.call_args[0][0]
        assert "git" in called_cmd
        assert "--name-only" in called_cmd

    def test_falls_back_on_nonzero_returncode(self, tmp_path):
        (tmp_path / ".git").mkdir()
        # Create a file that is "new"
        new_file = tmp_path / "changed.py"
        new_file.write_text("x = 1")

        mgr = IncrementalUpdateManager()
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        past = datetime.now() - timedelta(seconds=10)
        # Make the file appear newer than `past`
        os.utime(new_file, (datetime.now().timestamp() + 5,) * 2)

        with patch("subprocess.run", return_value=mock_result):
            result = mgr.detect_changes(str(tmp_path), past)

        assert "changed.py" in result

    def test_falls_back_on_timeout(self, tmp_path):
        (tmp_path / ".git").mkdir()
        new_file = tmp_path / "recent.py"
        new_file.write_text("pass")
        os.utime(new_file, (datetime.now().timestamp() + 5,) * 2)

        mgr = IncrementalUpdateManager()
        past = datetime.now() - timedelta(seconds=10)

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 30)):
            result = mgr.detect_changes(str(tmp_path), past)

        assert "recent.py" in result

    def test_falls_back_when_git_not_found(self, tmp_path):
        (tmp_path / ".git").mkdir()
        new_file = tmp_path / "new.py"
        new_file.write_text("pass")
        os.utime(new_file, (datetime.now().timestamp() + 5,) * 2)

        mgr = IncrementalUpdateManager()
        past = datetime.now() - timedelta(seconds=10)

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = mgr.detect_changes(str(tmp_path), past)

        assert "new.py" in result

    def test_strips_blank_lines_from_git_output(self, tmp_path):
        (tmp_path / ".git").mkdir()
        mgr = IncrementalUpdateManager()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "\nsrc/a.py\n\nsrc/b.py\n\n"

        with patch("subprocess.run", return_value=mock_result):
            result = mgr.detect_changes(str(tmp_path), datetime(2024, 1, 1))

        assert result == ["src/a.py", "src/b.py"]

    def test_since_flag_uses_last_analysis_time(self, tmp_path):
        (tmp_path / ".git").mkdir()
        mgr = IncrementalUpdateManager()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        ts = datetime(2025, 6, 15, 12, 0, 0)
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            mgr.detect_changes(str(tmp_path), ts)

        cmd = mock_run.call_args[0][0]
        assert any("2025-06-15T12:00:00" in arg for arg in cmd)


# ---------------------------------------------------------------------------
# _fallback_detect_changes
# ---------------------------------------------------------------------------

class TestFallbackDetectChanges:
    def test_returns_files_newer_than_cutoff(self, tmp_path):
        old_file = tmp_path / "old.py"
        new_file = tmp_path / "new.py"
        old_file.write_text("old")
        new_file.write_text("new")

        cutoff = datetime.now()
        # Make new_file appear 10 s in the future
        os.utime(new_file, (cutoff.timestamp() + 10,) * 2)
        # Make old_file appear 10 s in the past
        os.utime(old_file, (cutoff.timestamp() - 10,) * 2)

        mgr = IncrementalUpdateManager()
        result = mgr._fallback_detect_changes(tmp_path, cutoff)

        assert "new.py" in result
        assert "old.py" not in result

    def test_returns_relative_paths(self, tmp_path):
        f = tmp_path / "sub" / "file.py"
        f.parent.mkdir()
        f.write_text("x")
        os.utime(f, (datetime.now().timestamp() + 10,) * 2)

        mgr = IncrementalUpdateManager()
        result = mgr._fallback_detect_changes(tmp_path, datetime.now() - timedelta(seconds=5))

        assert any("file.py" in r for r in result)
        # Must be relative, not absolute
        assert not any(r.startswith("/") for r in result)

    def test_empty_when_no_new_files(self, tmp_path):
        f = tmp_path / "old.py"
        f.write_text("x")
        os.utime(f, (datetime.now().timestamp() - 100,) * 2)

        mgr = IncrementalUpdateManager()
        result = mgr._fallback_detect_changes(tmp_path, datetime.now())

        assert result == []


# ---------------------------------------------------------------------------
# get_affected_modules
# ---------------------------------------------------------------------------

class TestGetAffectedModules:
    def test_returns_changed_node_itself(self):
        g = _make_graph("src/a.py", "src/b.py")
        mgr = IncrementalUpdateManager()

        result = mgr.get_affected_modules(["src/a.py"], g)

        assert "src/a.py" in result

    def test_includes_direct_predecessors(self):
        # b.py imports a.py  →  edge b → a
        g = _make_graph("src/a.py", "src/b.py", edges=[("src/b.py", "src/a.py")])
        mgr = IncrementalUpdateManager()

        result = mgr.get_affected_modules(["src/a.py"], g)

        assert "src/a.py" in result
        assert "src/b.py" in result  # predecessor of a.py

    def test_does_not_include_successors(self):
        # a.py imports c.py  →  edge a → c
        g = _make_graph("src/a.py", "src/c.py", edges=[("src/a.py", "src/c.py")])
        mgr = IncrementalUpdateManager()

        result = mgr.get_affected_modules(["src/a.py"], g)

        assert "src/a.py" in result
        assert "src/c.py" not in result  # successor, not predecessor

    def test_empty_changed_files_returns_empty(self):
        g = _make_graph("src/a.py", "src/b.py")
        mgr = IncrementalUpdateManager()

        result = mgr.get_affected_modules([], g)

        assert result == []

    def test_empty_graph_returns_empty(self):
        mgr = IncrementalUpdateManager()
        result = mgr.get_affected_modules(["src/a.py"], nx.DiGraph())
        assert result == []

    def test_suffix_matching_relative_vs_absolute(self):
        """Relative changed path should match absolute node path."""
        g = nx.DiGraph()
        g.add_node("/repo/src/a.py", path="/repo/src/a.py")

        mgr = IncrementalUpdateManager()
        result = mgr.get_affected_modules(["src/a.py"], g)

        assert "/repo/src/a.py" in result

    def test_multiple_changed_files(self):
        g = _make_graph("src/a.py", "src/b.py", "src/c.py")
        mgr = IncrementalUpdateManager()

        result = mgr.get_affected_modules(["src/a.py", "src/b.py"], g)

        assert "src/a.py" in result
        assert "src/b.py" in result


# ---------------------------------------------------------------------------
# merge_graphs
# ---------------------------------------------------------------------------

class TestMergeGraphs:
    def test_preserves_old_nodes_not_in_new(self):
        old = _make_graph("a", "b")
        new = _make_graph("b")  # only b updated
        mgr = IncrementalUpdateManager()

        merged = mgr.merge_graphs(old, new)

        assert "a" in merged.nodes()
        assert "b" in merged.nodes()

    def test_overwrites_node_attributes(self):
        old = nx.DiGraph()
        old.add_node("a", purpose="old purpose")

        new = nx.DiGraph()
        new.add_node("a", purpose="new purpose")

        mgr = IncrementalUpdateManager()
        merged = mgr.merge_graphs(old, new)

        assert merged.nodes["a"]["purpose"] == "new purpose"

    def test_adds_new_nodes(self):
        old = _make_graph("a")
        new = _make_graph("b")
        mgr = IncrementalUpdateManager()

        merged = mgr.merge_graphs(old, new)

        assert "a" in merged.nodes()
        assert "b" in merged.nodes()

    def test_removes_stale_edges_from_updated_nodes(self):
        old = _make_graph("a", "b", "c", edges=[("a", "b"), ("a", "c")])
        # new graph for "a" only has edge a→b (a→c is gone)
        new = _make_graph("a", "b", edges=[("a", "b")])
        mgr = IncrementalUpdateManager()

        merged = mgr.merge_graphs(old, new)

        assert merged.has_edge("a", "b")
        assert not merged.has_edge("a", "c")

    def test_adds_new_edges(self):
        old = _make_graph("a", "b")
        new = _make_graph("a", "b", edges=[("a", "b")])
        mgr = IncrementalUpdateManager()

        merged = mgr.merge_graphs(old, new)

        assert merged.has_edge("a", "b")

    def test_preserves_edges_between_unchanged_nodes(self):
        old = _make_graph("a", "b", "c", edges=[("b", "c")])
        new = _make_graph("a")  # only a updated, b and c untouched
        mgr = IncrementalUpdateManager()

        merged = mgr.merge_graphs(old, new)

        assert merged.has_edge("b", "c")

    def test_empty_new_graph_returns_copy_of_old(self):
        old = _make_graph("a", "b", edges=[("a", "b")])
        mgr = IncrementalUpdateManager()

        merged = mgr.merge_graphs(old, nx.DiGraph())

        assert set(merged.nodes()) == {"a", "b"}
        assert merged.has_edge("a", "b")

    def test_empty_old_graph_returns_new(self):
        new = _make_graph("x", "y", edges=[("x", "y")])
        mgr = IncrementalUpdateManager()

        merged = mgr.merge_graphs(nx.DiGraph(), new)

        assert set(merged.nodes()) == {"x", "y"}
        assert merged.has_edge("x", "y")

    def test_does_not_mutate_old_graph(self):
        old = _make_graph("a", "b")
        new = nx.DiGraph()
        new.add_node("a", path="a", purpose="updated")
        mgr = IncrementalUpdateManager()

        mgr.merge_graphs(old, new)

        # old should be unchanged
        assert old.nodes["a"].get("purpose") is None

    def test_edge_attributes_preserved(self):
        old = nx.DiGraph()
        old.add_node("a")
        old.add_node("b")

        new = nx.DiGraph()
        new.add_node("a")
        new.add_node("b")
        new.add_edge("a", "b", weight=0.9)

        mgr = IncrementalUpdateManager()
        merged = mgr.merge_graphs(old, new)

        assert merged["a"]["b"]["weight"] == 0.9
