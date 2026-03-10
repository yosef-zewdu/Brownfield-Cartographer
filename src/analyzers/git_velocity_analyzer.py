"""Git velocity analyzer for tracking file change frequency."""

import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


class GitVelocityAnalyzer:
    """Analyzes git history to identify high-velocity files."""
    
    def __init__(self, repo_path: str):
        """
        Initialize git velocity analyzer.
        
        Args:
            repo_path: Path to the git repository
        """
        self.repo_path = Path(repo_path)
        self.has_git = (self.repo_path / '.git').exists()
    
    def get_change_velocity(self, file_path: str, days: int = 30) -> Optional[int]:
        """
        Get the number of commits for a file in the last N days.
        
        Args:
            file_path: Path to the file relative to repo root
            days: Number of days to look back (default: 30)
        
        Returns:
            Number of commits, or None if git is not available
        """
        if not self.has_git:
            return None
        
        try:
            # Calculate date threshold
            since_date = datetime.now() - timedelta(days=days)
            since_str = since_date.strftime('%Y-%m-%d')
            
            # Run git log with --follow to track file renames
            result = subprocess.run(
                [
                    'git', 'log',
                    '--follow',
                    '--oneline',
                    f'--since={since_str}',
                    '--',
                    file_path
                ],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Count lines in output (each line is a commit)
                lines = result.stdout.strip().split('\n')
                return len([line for line in lines if line])
            else:
                return 0
        
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return None
    
    def get_all_file_velocities(self, days: int = 30) -> Dict[str, int]:
        """
        Get change velocities for all files in the repository.
        
        Args:
            days: Number of days to look back (default: 30)
        
        Returns:
            Dictionary mapping file paths to commit counts
        """
        if not self.has_git:
            return {}
        
        try:
            # Get all files that have been modified in the time period
            since_date = datetime.now() - timedelta(days=days)
            since_str = since_date.strftime('%Y-%m-%d')
            
            result = subprocess.run(
                [
                    'git', 'log',
                    '--name-only',
                    '--oneline',
                    f'--since={since_str}',
                    '--pretty=format:'
                ],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {}
            
            # Count occurrences of each file
            file_counts: Dict[str, int] = {}
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line:
                    file_counts[line] = file_counts.get(line, 0) + 1
            
            return file_counts
        
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return {}
    
    def get_high_velocity_files(self, threshold: float = 0.8, days: int = 30) -> List[str]:
        """
        Identify high-velocity files using Pareto analysis.
        
        Args:
            threshold: Cumulative percentage threshold (default: 0.8 for 80%)
            days: Number of days to look back (default: 30)
        
        Returns:
            List of file paths that account for the threshold percentage of changes
        """
        if not self.has_git:
            return []
        
        # Get all file velocities
        velocities = self.get_all_file_velocities(days)
        
        if not velocities:
            return []
        
        # Sort files by velocity (descending)
        sorted_files = sorted(velocities.items(), key=lambda x: x[1], reverse=True)
        
        # Calculate total changes
        total_changes = sum(velocities.values())
        
        # Find files that account for threshold% of changes
        cumulative = 0
        high_velocity_files = []
        
        for file_path, count in sorted_files:
            cumulative += count
            high_velocity_files.append(file_path)
            
            if cumulative >= total_changes * threshold:
                break
        
        return high_velocity_files
    
    def get_file_last_modified(self, file_path: str) -> Optional[datetime]:
        """
        Get the last commit date for a file.
        
        Args:
            file_path: Path to the file relative to repo root
        
        Returns:
            Datetime of last commit, or None if git is not available
        """
        if not self.has_git:
            return None
        
        try:
            result = subprocess.run(
                [
                    'git', 'log',
                    '-1',
                    '--format=%ci',
                    '--',
                    file_path
                ],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse git date format
                date_str = result.stdout.strip()
                return datetime.strptime(date_str[:19], '%Y-%m-%d %H:%M:%S')
            else:
                return None
        
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError, ValueError):
            return None
