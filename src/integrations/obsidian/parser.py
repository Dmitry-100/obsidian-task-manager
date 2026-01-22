"""Parser for Obsidian Tasks Plugin format.

Parses markdown task lines in the format:
- [ ] Task title 🔼 📅 2026-01-25 #tag1 #tag2
- [x] Completed task ⏫ 📅 2026-01-20 #tag ✅ 2026-01-20
"""

import contextlib
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass
class ParsedTask:
    """Represents a task parsed from Obsidian markdown."""

    title: str
    status: str  # "todo" | "done"
    priority: str  # "low" | "medium" | "high"
    due_date: date | None = None
    completed_at: date | None = None
    tags: list[str] = field(default_factory=list)
    description: str | None = None

    # Source information
    source_file: str = ""
    source_line: int = 0
    section: str | None = None
    raw_line: str = ""

    # For conflict detection
    file_modified: datetime | None = None


# Priority emoji mappings
PRIORITY_MAP: dict[str, str] = {
    "🔺": "high",  # highest
    "⏫": "high",  # high
    "🔼": "medium",  # medium
    "🔽": "low",  # low
    "⏬": "low",  # lowest
}

# Reverse mapping for writing
PRIORITY_TO_EMOJI: dict[str, str] = {
    "high": "⏫",
    "medium": "🔼",
    "low": "🔽",
}

# Regex patterns
CHECKBOX_PATTERN = re.compile(r"^(\s*)-\s*\[([ xX])\]\s*")
DUE_DATE_PATTERN = re.compile(r"📅\s*(\d{4}-\d{2}-\d{2})")
COMPLETED_DATE_PATTERN = re.compile(r"✅\s*(\d{4}-\d{2}-\d{2})")
TAG_PATTERN = re.compile(r"#([\w\-/]+)")
PRIORITY_PATTERN = re.compile(r"[🔺⏫🔼🔽⏬]")
SECTION_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")

# Emoji and metadata to strip from title
METADATA_PATTERN = re.compile(
    r"\s*("
    r"[🔺⏫🔼🔽⏬]"  # Priority emojis
    r"|📅\s*\d{4}-\d{2}-\d{2}"  # Due date
    r"|✅\s*\d{4}-\d{2}-\d{2}"  # Completed date
    r"|🔁[^📅]*"  # Recurrence
    r"|#[\w\-/]+"  # Tags
    r")\s*"
)


class ObsidianParser:
    """Parser for Obsidian Tasks Plugin markdown format."""

    def parse_file(self, file_path: str | Path) -> list[ParsedTask]:
        """Parse all tasks from a markdown file.

        Args:
            file_path: Path to the markdown file

        Returns:
            List of parsed tasks
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        file_modified = datetime.fromtimestamp(file_path.stat().st_mtime)

        return self.parse_content(
            content,
            source_file=str(file_path),
            file_modified=file_modified,
        )

    def parse_content(
        self,
        content: str,
        source_file: str = "",
        file_modified: datetime | None = None,
    ) -> list[ParsedTask]:
        """Parse tasks from markdown content.

        Args:
            content: Markdown content
            source_file: Source file path for reference
            file_modified: File modification timestamp

        Returns:
            List of parsed tasks
        """
        tasks: list[ParsedTask] = []
        current_section: str | None = None
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            # Track current section
            section_match = SECTION_PATTERN.match(line)
            if section_match:
                current_section = section_match.group(2).strip()
                continue

            # Try to parse as task
            task = self.parse_line(line)
            if task:
                task.source_file = source_file
                task.source_line = line_num
                task.section = current_section
                task.file_modified = file_modified
                task.raw_line = line
                tasks.append(task)

        return tasks

    def parse_line(self, line: str) -> ParsedTask | None:
        """Parse a single line as a task.

        Args:
            line: A line of markdown text

        Returns:
            ParsedTask if the line is a valid task, None otherwise
        """
        # Check for checkbox
        checkbox_match = CHECKBOX_PATTERN.match(line)
        if not checkbox_match:
            return None

        checkbox_char = checkbox_match.group(2)
        status = "done" if checkbox_char.lower() == "x" else "todo"

        # Get content after checkbox
        content = line[checkbox_match.end() :]

        # Extract priority
        priority = "medium"  # default
        priority_match = PRIORITY_PATTERN.search(content)
        if priority_match:
            priority = PRIORITY_MAP.get(priority_match.group(), "medium")

        # Extract due date
        due_date: date | None = None
        due_match = DUE_DATE_PATTERN.search(content)
        if due_match:
            with contextlib.suppress(ValueError):
                due_date = date.fromisoformat(due_match.group(1))

        # Extract completed date
        completed_at: date | None = None
        completed_match = COMPLETED_DATE_PATTERN.search(content)
        if completed_match:
            with contextlib.suppress(ValueError):
                completed_at = date.fromisoformat(completed_match.group(1))

        # Extract tags
        tags = TAG_PATTERN.findall(content)

        # Extract title (remove metadata)
        title = METADATA_PATTERN.sub(" ", content).strip()

        # Clean up extra whitespace
        title = re.sub(r"\s+", " ", title).strip()

        if not title:
            return None

        return ParsedTask(
            title=title,
            status=status,
            priority=priority,
            due_date=due_date,
            completed_at=completed_at,
            tags=tags,
        )

    def task_to_markdown(self, task: ParsedTask) -> str:
        """Convert a ParsedTask back to markdown format.

        Args:
            task: The task to convert

        Returns:
            Markdown string representation
        """
        parts: list[str] = []

        # Checkbox
        checkbox = "[x]" if task.status == "done" else "[ ]"
        parts.append(f"- {checkbox} {task.title}")

        # Priority (if not medium)
        if task.priority != "medium" and task.priority in PRIORITY_TO_EMOJI:
            parts.append(PRIORITY_TO_EMOJI[task.priority])

        # Due date
        if task.due_date:
            parts.append(f"📅 {task.due_date.isoformat()}")

        # Tags
        for tag in task.tags:
            if not tag.startswith("#"):
                tag = f"#{tag}"
            parts.append(tag)

        # Completed date (if done)
        if task.status == "done" and task.completed_at:
            parts.append(f"✅ {task.completed_at.isoformat()}")

        return " ".join(parts)

    def find_task_in_content(
        self,
        content: str,
        task_title: str,
    ) -> tuple[int, str] | None:
        """Find a task in content by title.

        Args:
            content: Markdown content
            task_title: Title to search for

        Returns:
            Tuple of (line_number, line_content) or None if not found
        """
        lines = content.split("\n")
        title_lower = task_title.lower()

        for line_num, line in enumerate(lines, start=1):
            task = self.parse_line(line)
            if task and task.title.lower() == title_lower:
                return (line_num, line)

        return None

    def update_task_in_content(
        self,
        content: str,
        line_number: int,
        new_task: ParsedTask,
    ) -> str:
        """Update a specific task line in content.

        Args:
            content: Original markdown content
            line_number: Line number to update (1-indexed)
            new_task: New task data

        Returns:
            Updated content
        """
        lines = content.split("\n")

        if 1 <= line_number <= len(lines):
            # Preserve indentation from original line
            original_line = lines[line_number - 1]
            indent_match = re.match(r"^(\s*)", original_line)
            indent = indent_match.group(1) if indent_match else ""

            new_line = self.task_to_markdown(new_task)
            # Apply original indentation
            if new_line.startswith("- "):
                new_line = indent + new_line

            lines[line_number - 1] = new_line

        return "\n".join(lines)
