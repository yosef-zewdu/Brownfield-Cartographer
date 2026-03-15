"""Incremental update manager for re-analyzing only changed files."""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set
import networkx as nx


class IncrementalUpdateManager:
    """
    Manages incremental updates by detecting changed files via git diff
    and merging updated graphs without full re-analysis.

    Requirements: 19.1, 19.2, 19.3
    """

    def detect_changes(self, repo_path: str, last_analysis_time: datetime) -> List[str]:
        """
        Use git diff to find files changed since last_analysis_time.

        Args:
            repo_path: Path to the git repository.
            last_analysis_time: Timestamp of the previous analysis run.

        Returns:
            List of changed file paths (relative to repo_path).
        """
        repo = Path(repo_path)
        git_dir = repo / ".git"
        if not git_dir.exists():
            return []

        since_str = last_analysis_time.strftime("%Y-%m-%dT%H:%M:%S")
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", f"--since={since_str}", "HEAD"],
                cwd=str(repo),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                # Fallback: files modified after the timestamp
                return self._fallback_detect_changes(repo, last_analysis_time)

            changed = [
                line.strip()
                for line in result.stdout.splitlines()
                if line.strip()
            ]
            return changed
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return self._fallback_detect_changes(repo, last_analysis_time)

    def _fallback_detect_changes(
        self, repo: Path, last_analysis_time: datetime
    ) -> List[str]:
        """Fallback: scan filesystem for files newer than last_analysis_time."""
        changed = []
        cutoff = last_analysis_time.timestamp()
        for f in repo.rglob("*"):
            if f.is_file() and f.stat().st_mtime > cutoff:
                try:
                    changed.append(str(f.relative_to(repo)))
                except ValueError:
                    pass
        return changed

    def get_affected_modules(
        self, changed_files: List[str], module_graph: nx.DiGraph
    ) -> List[str]:
        """
        Find all modules that need re-analysis: changed files plus their
        direct dependents (nodes that import them).

        Args:
            changed_files: List of changed file paths.
            module_graph: Existing module dependency graph.

        Returns:
            List of module paths that should be re-analyzed.
        """
        affected: Set[str] = set()

        # Normalise changed_files to match graph node IDs
        changed_set = set(changed_files)

        for node in module_graph.nodes():
            node_path = module_graph.nodes[node].get("path", node)
            # Match by suffix so relative paths align with absolute node IDs
            if any(node_path.endswith(cf) or cf.endswith(node_path) for cf in changed_set):
                affected.add(node)
                # Add direct predecessors (modules that import this one)
                affected.update(module_graph.predecessors(node))

        return list(affected)

    def merge_graphs(
        self, old_graph: nx.DiGraph, new_graph: nx.DiGraph
    ) -> nx.DiGraph:
        """
        Merge new_graph into old_graph, overwriting nodes/edges that appear
        in new_graph and preserving everything else.

        Args:
            old_graph: Previously serialized graph.
            new_graph: Freshly built graph for changed modules.

        Returns:
            Merged graph.
        """
        merged = old_graph.copy()

        # Update / add nodes from new graph
        for node, attrs in new_graph.nodes(data=True):
            merged.add_node(node, **attrs)

        # Remove stale edges originating from updated nodes, then re-add
        updated_nodes = set(new_graph.nodes())
        stale_edges = [
            (u, v)
            for u, v in merged.edges()
            if u in updated_nodes or v in updated_nodes
        ]
        merged.remove_edges_from(stale_edges)

        for u, v, attrs in new_graph.edges(data=True):
            merged.add_edge(u, v, **attrs)

        return merged
