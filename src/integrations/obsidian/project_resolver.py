"""Project resolver for mapping Obsidian tasks to projects.

Uses a cascading logic:
1. Explicit project tag (#project/name)
2. Section in file (## Section Name)
3. Folder path (01_Projects/Name/)
4. Regular tags (#tag -> mapping)
5. Default project
"""

import re
from dataclasses import dataclass
from pathlib import Path

from src.integrations.obsidian.parser import ParsedTask


@dataclass
class SyncConfig:
    """Configuration for sync mappings."""

    vault_path: str
    sync_sources: list[str]
    folder_mapping: dict[str, str]
    tag_mapping: dict[str, str]
    section_mapping: dict[str, str]
    default_project: str = "Inbox"
    default_conflict_resolution: str = "ask"


class ProjectResolver:
    """Resolves project name for a parsed task."""

    def __init__(self, config: SyncConfig):
        """Initialize with sync configuration.

        Args:
            config: Sync configuration with mappings
        """
        self.config = config
        self._compiled_section_patterns: dict[re.Pattern, str] = {}

        # Compile section patterns
        for pattern, project in config.section_mapping.items():
            try:
                self._compiled_section_patterns[re.compile(pattern, re.IGNORECASE)] = project
            except re.error:
                # If pattern is invalid, use as literal string
                escaped = re.escape(pattern)
                self._compiled_section_patterns[re.compile(escaped, re.IGNORECASE)] = project

    def resolve(self, task: ParsedTask) -> str:
        """Resolve project name for a task.

        Uses cascading logic:
        1. Explicit project tag (#project/name)
        2. Section in file
        3. Folder path
        4. Regular tags
        5. Default

        Args:
            task: Parsed task to resolve project for

        Returns:
            Project name
        """
        # 1. Check for explicit project tag
        project = self._resolve_from_project_tag(task.tags)
        if project:
            return project

        # 2. Check section name
        if task.section:
            project = self._resolve_from_section(task.section)
            if project:
                return project

        # 3. Check folder path
        if task.source_file:
            project = self._resolve_from_folder(task.source_file)
            if project:
                return project

        # 4. Check regular tags
        project = self._resolve_from_tags(task.tags)
        if project:
            return project

        # 5. Return default
        return self.config.default_project

    def _resolve_from_project_tag(self, tags: list[str]) -> str | None:
        """Extract project from explicit #project/name tag.

        Args:
            tags: List of tags

        Returns:
            Project name or None
        """
        for tag in tags:
            if tag.startswith("project/"):
                return tag[8:]  # Remove "project/" prefix
        return None

    def _resolve_from_section(self, section: str) -> str | None:
        """Match section name against section mapping patterns.

        Args:
            section: Section header text

        Returns:
            Project name or None
        """
        for pattern, project in self._compiled_section_patterns.items():
            if pattern.search(section):
                return project
        return None

    def _resolve_from_folder(self, file_path: str) -> str | None:
        """Match file path against folder mapping.

        Args:
            file_path: Full path to source file

        Returns:
            Project name or None
        """
        # Make path relative to vault
        vault_path = Path(self.config.vault_path)
        try:
            file_path_obj = Path(file_path)
            relative_path = file_path_obj.relative_to(vault_path)
        except ValueError:
            # File not in vault
            return None

        relative_str = str(relative_path)

        # Check folder mappings
        for folder_pattern, project in self.config.folder_mapping.items():
            if relative_str.startswith(folder_pattern):
                return project

        return None

    def _resolve_from_tags(self, tags: list[str]) -> str | None:
        """Match tags against tag mapping.

        Args:
            tags: List of tags

        Returns:
            Project name or None (first match wins)
        """
        for tag in tags:
            # Remove project/ prefix if present (already handled)
            if tag.startswith("project/"):
                continue

            # Check tag mapping
            tag_lower = tag.lower()
            if tag_lower in self.config.tag_mapping:
                return self.config.tag_mapping[tag_lower]

        return None

    def get_tags_for_project(self, project_name: str) -> list[str]:
        """Get tags associated with a project name.

        Args:
            project_name: Project name to look up

        Returns:
            List of tags that map to this project
        """
        tags = []
        for tag, project in self.config.tag_mapping.items():
            if project == project_name:
                tags.append(tag)
        return tags


def load_sync_config(config_path: str | Path) -> SyncConfig:
    """Load sync configuration from YAML file.

    Args:
        config_path: Path to sync_config.yaml

    Returns:
        SyncConfig instance
    """
    import yaml

    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return SyncConfig(
        vault_path=data.get("vault_path", ""),
        sync_sources=data.get("sync_sources", []),
        folder_mapping=data.get("folder_mapping", {}),
        tag_mapping=data.get("tag_mapping", {}),
        section_mapping=data.get("section_mapping", {}),
        default_project=data.get("default_project", "Inbox"),
        default_conflict_resolution=data.get("default_conflict_resolution", "ask"),
    )


def create_default_config() -> SyncConfig:
    """Create default sync configuration.

    Returns:
        Default SyncConfig instance
    """
    return SyncConfig(
        vault_path="",
        sync_sources=[
            "00_Inbox/TODO - Неделя*.md",
            "01_Projects/*/Tasks.md",
            "02_Areas/*/TODO.md",
        ],
        folder_mapping={
            "01_Projects/Столовая КХП": "Столовая КХП",
            "01_Projects/Оплата простоев": "Оплата простоев",
            "01_Projects/Вайб-Кодинг": "Вайб-Кодинг",
            "02_Areas/Health": "Здоровье",
            "02_Areas/Crypto": "Крипто",
        },
        tag_mapping={
            "health": "Здоровье",
            "family": "Семья",
            "crypto": "Крипто",
            "khp": "Столовая КХП",
            "work": "Работа: Разное",
            "vibe-coding": "Вайб-Кодинг",
            "fitness": "Тренировки",
            "learning": "Обучение",
            "urgent": "Здоровье",  # urgent health tasks
        },
        section_mapping={
            r"Здоровье|Health|CRITICAL.*Здоровье": "Здоровье",
            r"Семья|Family|CRITICAL.*Семья": "Семья",
            r"Крипто|Crypto|Polkadot|Финансы": "Крипто",
            r"Столовая КХП|KHP": "Столовая КХП",
            r"Оплата простоев": "Оплата простоев",
            r"AI Safety": "AI Safety NLMK",
            r"Вайб-Кодинг": "Вайб-Кодинг",
            r"Тренировки|Fitness|ROUTINE.*Тренировки": "Тренировки",
            r"Творчество": "Творчество",
            r"Обучение|Learning": "Обучение",
        },
        default_project="Inbox",
        default_conflict_resolution="ask",
    )


def get_config() -> SyncConfig:
    """Get sync configuration.

    Tries to load from config/sync_config.yaml, falls back to default.

    Returns:
        SyncConfig instance
    """
    config_paths = [
        Path("config/sync_config.yaml"),
        Path(__file__).parent.parent.parent.parent / "config" / "sync_config.yaml",
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                return load_sync_config(config_path)
            except Exception:
                pass

    return create_default_config()
