"""File scanner for finding Obsidian markdown files.

Scans vault directory using glob patterns to find files to sync.
"""

import glob
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class ScannedFile:
    """Information about a scanned file."""

    path: str
    relative_path: str
    modified_at: datetime
    size_bytes: int


class FileScanner:
    """Scans Obsidian vault for files matching patterns."""

    def __init__(self, vault_path: str | Path):
        """Initialize scanner with vault path.

        Args:
            vault_path: Path to Obsidian vault root
        """
        self.vault_path = Path(vault_path)
        if not self.vault_path.exists():
            raise ValueError(f"Vault path does not exist: {vault_path}")
        if not self.vault_path.is_dir():
            raise ValueError(f"Vault path is not a directory: {vault_path}")

    def scan(self, patterns: list[str]) -> list[ScannedFile]:
        """Scan vault for files matching patterns.

        Args:
            patterns: List of glob patterns (relative to vault root)

        Returns:
            List of ScannedFile objects
        """
        files: list[ScannedFile] = []
        seen_paths: set[str] = set()

        for pattern in patterns:
            # Make pattern absolute
            full_pattern = str(self.vault_path / pattern)

            # Find matching files
            for file_path in glob.glob(full_pattern, recursive=True):
                path = Path(file_path)

                # Skip if already seen (patterns may overlap)
                if str(path) in seen_paths:
                    continue

                # Skip directories
                if path.is_dir():
                    continue

                # Skip non-markdown files
                if path.suffix.lower() != ".md":
                    continue

                seen_paths.add(str(path))

                try:
                    stat = path.stat()
                    relative_path = path.relative_to(self.vault_path)

                    files.append(
                        ScannedFile(
                            path=str(path),
                            relative_path=str(relative_path),
                            modified_at=datetime.fromtimestamp(stat.st_mtime),
                            size_bytes=stat.st_size,
                        )
                    )
                except (OSError, ValueError):
                    # Skip files we can't access
                    continue

        # Sort by modification time (newest first)
        files.sort(key=lambda f: f.modified_at, reverse=True)

        return files

    def scan_single(self, file_path: str | Path) -> ScannedFile | None:
        """Get info about a single file.

        Args:
            file_path: Path to the file

        Returns:
            ScannedFile or None if file doesn't exist
        """
        path = Path(file_path)

        if not path.exists() or not path.is_file():
            return None

        try:
            stat = path.stat()
            try:
                relative_path = path.relative_to(self.vault_path)
            except ValueError:
                relative_path = path

            return ScannedFile(
                path=str(path),
                relative_path=str(relative_path),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                size_bytes=stat.st_size,
            )
        except OSError:
            return None

    def get_file_content(self, file_path: str | Path) -> str:
        """Read content of a file.

        Args:
            file_path: Path to the file

        Returns:
            File content as string
        """
        path = Path(file_path)
        return path.read_text(encoding="utf-8")

    def write_file_content(self, file_path: str | Path, content: str) -> None:
        """Write content to a file.

        Args:
            file_path: Path to the file
            content: Content to write
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def list_directories(self, relative_path: str = "") -> list[str]:
        """List subdirectories in vault.

        Args:
            relative_path: Relative path within vault

        Returns:
            List of directory names
        """
        target = self.vault_path / relative_path if relative_path else self.vault_path
        if not target.exists():
            return []

        return [d.name for d in target.iterdir() if d.is_dir() and not d.name.startswith(".")]

    def find_todo_files(self) -> list[ScannedFile]:
        """Find common TODO file patterns.

        Returns:
            List of ScannedFile objects
        """
        common_patterns = [
            "**/*TODO*.md",
            "**/*Tasks*.md",
            "**/tasks.md",
            "00_Inbox/**/*.md",
        ]
        return self.scan(common_patterns)
