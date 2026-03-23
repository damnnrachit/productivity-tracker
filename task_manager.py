from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import threading
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class Task:
    title: str
    is_completed: bool = False
    due_date: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Task":
        title = str(data.get("title", "")).strip()
        is_completed = bool(data.get("is_completed", False))
        due_date = str(data.get("due_date", "")).strip()
        return Task(title=title, is_completed=is_completed, due_date=due_date)


class TaskRepository:
    """
    File-backed persistence for tasks.json.

    Keeps file I/O and JSON parsing here, so the manager stays focused on operations.
    """

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)
        self._lock = threading.Lock()

    def load_tasks(self) -> list[Task]:
        with self._lock:
            if not self.file_path.exists():
                return []

            try:
                raw = self.file_path.read_text(encoding="utf-8")
                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    raise ValueError("tasks.json root must be a list")

                tasks: list[Task] = []
                for item in parsed:
                    if isinstance(item, dict):
                        task = Task.from_dict(item)
                        if task.title:
                            tasks.append(task)
                return tasks
            except (json.JSONDecodeError, OSError, ValueError):
                # Backup the corrupted file (best-effort) and start fresh.
                backup_path = self.file_path.with_suffix(".json.bak")
                try:
                    self.file_path.replace(backup_path)
                except OSError:
                    pass
                return []

    def save_tasks(self, tasks: list[Task]) -> None:
        with self._lock:
            payload = [task.to_dict() for task in tasks]
            # Ensure the parent directory exists (important for per-user files).
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )


class TaskManager:
    """
    OOP facade for task operations (add/toggle/delete/clear) backed by TaskRepository.
    """

    def __init__(
        self,
        file_path: Optional[str | Path] = None,
        repository: Optional[TaskRepository] = None,
    ) -> None:
        if repository is not None:
            self._repo = repository
        else:
            default_file = Path(__file__).resolve().parent / "tasks.json"
            self._repo = TaskRepository(file_path or default_file)

        self._tasks: list[Task] = self._repo.load_tasks()

    @property
    def tasks(self) -> list[Task]:
        # Return a copy so callers don't mutate our internal state.
        return list(self._tasks)

    def reload(self) -> None:
        self._tasks = self._repo.load_tasks()

    def add_task(self, title: str, due_date: str = "") -> Task:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("title must not be empty")

        due_date_clean = due_date.strip()
        task = Task(title=clean_title, is_completed=False, due_date=due_date_clean)
        self._tasks.append(task)
        self._repo.save_tasks(self._tasks)
        return task

    def toggle_task(self, index: int) -> Task:
        if not (0 <= index < len(self._tasks)):
            raise IndexError("task index out of range")

        current = self._tasks[index]
        updated = Task(
            title=current.title,
            is_completed=not current.is_completed,
            due_date=current.due_date,
        )
        self._tasks[index] = updated
        self._repo.save_tasks(self._tasks)
        return updated

    def mark_complete(self, index: int) -> Task:
        if not (0 <= index < len(self._tasks)):
            raise IndexError("task index out of range")

        current = self._tasks[index]
        if current.is_completed:
            return current

        updated = Task(
            title=current.title,
            is_completed=True,
            due_date=current.due_date,
        )
        self._tasks[index] = updated
        self._repo.save_tasks(self._tasks)
        return updated

    def edit_task(self, index: int, title: str, due_date: str = "") -> Task:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("title must not be empty")

        if not (0 <= index < len(self._tasks)):
            raise IndexError("task index out of range")

        current = self._tasks[index]
        due_date_clean = due_date.strip()
        updated = Task(
            title=clean_title,
            is_completed=current.is_completed,
            due_date=due_date_clean,
        )
        self._tasks[index] = updated
        self._repo.save_tasks(self._tasks)
        return updated

    def delete_task(self, index: int) -> Task:
        if not (0 <= index < len(self._tasks)):
            raise IndexError("task index out of range")

        removed = self._tasks.pop(index)
        self._repo.save_tasks(self._tasks)
        return removed

    def clear_completed(self) -> int:
        before = len(self._tasks)
        self._tasks = [task for task in self._tasks if not task.is_completed]
        removed_count = before - len(self._tasks)
        self._repo.save_tasks(self._tasks)
        return removed_count

# The legacy duplicated/CLI implementation was accidentally appended to this file.
# Wrap it in a different-quote multiline string so the legacy inner docstrings don't terminate it early.
'''
# Legacy duplicated block (accidentally appended during refactor) is intentionally disabled.

from dataclasses import asdict, dataclass
import json
import threading
from pathlib import Path
from typing import Any, List, Optional


@dataclass(frozen=True)
class Task:
    title: str
    is_completed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Task":
        title = str(data.get("title", "")).strip()
        is_completed = bool(data.get("is_completed", False))
        return Task(title=title, is_completed=is_completed)


class TaskRepository:
    """
    File-backed persistence for tasks.json.

    Keeps file I/O and JSON parsing here, so the manager stays focused on operations.
    """

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)
        self._lock = threading.Lock()

    def load_tasks(self) -> list[Task]:
        with self._lock:
            if not self.file_path.exists():
                return []

            try:
                raw = self.file_path.read_text(encoding="utf-8")
                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    raise ValueError("tasks.json root must be a list")

                tasks: list[Task] = []
                for item in parsed:
                    if isinstance(item, dict):
                        task = Task.from_dict(item)
                        if task.title:
                            tasks.append(task)
                return tasks
            except (json.JSONDecodeError, OSError, ValueError):
                # Backup the corrupted file (best-effort) and start fresh.
                backup_path = self.file_path.with_suffix(".json.bak")
                try:
                    self.file_path.replace(backup_path)
                except OSError:
                    pass
                return []

    def save_tasks(self, tasks: list[Task]) -> None:
        with self._lock:
            payload = [task.to_dict() for task in tasks]
            self.file_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )


class TaskManager:
    """
    OOP facade for task operations (add/toggle/delete/clear) backed by TaskRepository.
    """

    def __init__(
        self,
        file_path: Optional[str | Path] = None,
        repository: Optional[TaskRepository] = None,
    ) -> None:
        if repository is not None:
            self._repo = repository
        else:
            default_file = Path(__file__).resolve().parent / "tasks.json"
            self._repo = TaskRepository(file_path or default_file)

        self._tasks: list[Task] = self._repo.load_tasks()

    @property
    def tasks(self) -> list[Task]:
        # Return a copy so callers don't mutate our internal state.
        return list(self._tasks)

    def reload(self) -> None:
        self._tasks = self._repo.load_tasks()

    def add_task(self, title: str) -> Task:
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("title must not be empty")

        task = Task(title=clean_title, is_completed=False)
        self._tasks.append(task)
        self._repo.save_tasks(self._tasks)
        return task

    def toggle_task(self, index: int) -> Task:
        if not (0 <= index < len(self._tasks)):
            raise IndexError("task index out of range")

        current = self._tasks[index]
        updated = Task(title=current.title, is_completed=not current.is_completed)
        self._tasks[index] = updated
        self._repo.save_tasks(self._tasks)
        return updated

    def delete_task(self, index: int) -> Task:
        if not (0 <= index < len(self._tasks)):
            raise IndexError("task index out of range")

        removed = self._tasks.pop(index)
        self._repo.save_tasks(self._tasks)
        return removed

    def clear_completed(self) -> int:
        before = len(self._tasks)
        self._tasks = [task for task in self._tasks if not task.is_completed]
        removed_count = before - len(self._tasks)
        self._repo.save_tasks(self._tasks)
        return removed_count

"""Professional CLI task manager with JSON persistence.

This module provides:
- Task model with serialization helpers
- TaskManager service for task operations
- Loop-based CLI for morning input and evening review flows
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


DATA_FILE = "tasks.json"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class Task:
    """Represents a single task item."""

    description: str
    status: bool = False
    created_at: str = field(
        default_factory=lambda: datetime.now().strftime(DATETIME_FORMAT)
    )

    def mark_complete(self) -> None:
        """Mark the task as completed."""
        self.status = True

    def to_dict(self) -> dict:
        """Convert task object into dictionary for JSON serialization."""
        return {
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Create a Task object from dictionary data."""
        return cls(
            description=data.get("description", "").strip(),
            status=bool(data.get("status", False)),
            created_at=data.get(
                "created_at",
                datetime.now().strftime(DATETIME_FORMAT),
            ),
        )


class TaskManager:
    """Manages task operations and persistence."""

    def __init__(self, file_path: str = DATA_FILE) -> None:
        self.file_path = Path(file_path)
        self.tasks: List[Task] = []
        self.load_tasks()

    def add_task(self, description: str) -> bool:
        """Add a new task if valid and not duplicate.

        Returns True if task was added, otherwise False.
        """
        normalized_description = description.strip()
        if not normalized_description:
            return False

        if self._task_exists(normalized_description):
            return False

        new_task = Task(description=normalized_description)
        self.tasks.append(new_task)
        self._sort_tasks_by_created_time()
        self.save_tasks()
        return True

    def view_tasks(self, filter_by: Optional[str] = None) -> List[Task]:
        """Return tasks, optionally filtered by status.

        Args:
            filter_by: "completed", "pending", or None for all tasks.
        """
        if filter_by == "completed":
            return [task for task in self.tasks if task.status]
        if filter_by == "pending":
            return [task for task in self.tasks if not task.status]
        return list(self.tasks)

    def update_task(self, index: int, new_description: str) -> bool:
        """Update a task description by index.

        Returns True when update succeeds.
        """
        if not self._is_valid_index(index):
            return False

        normalized_description = new_description.strip()
        if not normalized_description:
            return False

        current_description = self.tasks[index].description
        if normalized_description.lower() != current_description.lower():
            if self._task_exists(normalized_description):
                return False

        self.tasks[index].description = normalized_description
        self.save_tasks()
        return True

    def delete_task(self, index: int) -> bool:
        """Delete a task by index. Returns True if successful."""
        if not self._is_valid_index(index):
            return False

        del self.tasks[index]
        self.save_tasks()
        return True

    def mark_task_complete(self, index: int) -> bool:
        """Mark a task as complete by index. Returns True if successful."""
        if not self._is_valid_index(index):
            return False

        self.tasks[index].mark_complete()
        self.save_tasks()
        return True

    def save_tasks(self) -> None:
        """Save tasks to JSON file."""
        task_data = [task.to_dict() for task in self.tasks]
        with self.file_path.open("w", encoding="utf-8") as file:
            json.dump(task_data, file, indent=4)

    def load_tasks(self) -> None:
        """Load tasks from JSON file or initialize empty list."""
        if not self.file_path.exists():
            self.tasks = []
            return

        try:
            with self.file_path.open("r", encoding="utf-8") as file:
                task_data = json.load(file)

            if not isinstance(task_data, list):
                self.tasks = []
                return

            loaded_tasks = []
            for item in task_data:
                if isinstance(item, dict):
                    task = Task.from_dict(item)
                    if task.description:
                        loaded_tasks.append(task)

            self.tasks = loaded_tasks
            self._sort_tasks_by_created_time()
        except (json.JSONDecodeError, OSError):
            self.tasks = []

    def _task_exists(self, description: str) -> bool:
        """Check duplicate tasks (case-insensitive)."""
        target = description.strip().lower()
        return any(task.description.lower() == target for task in self.tasks)

    def _is_valid_index(self, index: int) -> bool:
        """Return True if index is in valid range."""
        return 0 <= index < len(self.tasks)

    def _sort_tasks_by_created_time(self) -> None:
        """Sort tasks by created_at timestamp (oldest first)."""

        def parse_timestamp(value: str) -> datetime:
            try:
                return datetime.strptime(value, DATETIME_FORMAT)
            except ValueError:
                return datetime.max

        self.tasks.sort(key=lambda task: parse_timestamp(task.created_at))


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 52)
    print(f"{title:^52}")
    print("=" * 52)


def print_tasks(tasks: List[Task]) -> None:
    """Print indexed tasks with status icons."""
    if not tasks:
        print("\nNo tasks found.")
        return

    print("\nYour Tasks:")
    print("-" * 52)
    for index, task in enumerate(tasks, start=1):
        status_icon = "✔" if task.status else "✘"
        print(
            f"{index:>2}. [{status_icon}] {task.description} "
            f"(Created: {task.created_at})"
        )
    print("-" * 52)


def get_valid_menu_choice() -> int:
    """Read and validate menu choice input."""
    while True:
        choice = input("Select an option (1-6): ").strip()
        try:
            numeric_choice = int(choice)
            if 1 <= numeric_choice <= 6:
                return numeric_choice
            print("Please enter a number between 1 and 6.")
        except ValueError:
            print("Invalid input. Enter a numeric value.")


def get_valid_task_index(task_count: int, prompt: str) -> Optional[int]:
    """Read and validate task index input.

    Returns:
        Zero-based index if valid, else None.
    """
    if task_count == 0:
        print("No tasks available.")
        return None

    raw_value = input(prompt).strip()
    try:
        number = int(raw_value)
        if 1 <= number <= task_count:
            return number - 1
        print("Task number is out of range.")
    except ValueError:
        print("Invalid input. Please enter a valid task number.")
    return None


def handle_add_task(task_manager: TaskManager) -> None:
    """Handle add task menu option."""
    print_header("Morning Input: Add Task")
    while True:
        description = input("Enter task description (or 'done' to stop): ").strip()

        if description.lower() == "done":
            break

        if not description:
            print("Task description cannot be empty.")
            continue

        if task_manager.add_task(description):
            print("Task added successfully.")
        else:
            print("Task not added (empty or duplicate).")


def handle_view_tasks(task_manager: TaskManager) -> None:
    """Handle view task menu option with filtering."""
    print_header("Evening Review: View Tasks")
    print("1. All Tasks")
    print("2. Completed Tasks")
    print("3. Pending Tasks")

    filter_choice = input("Choose filter (1-3, default 1): ").strip()
    if filter_choice == "2":
        tasks = task_manager.view_tasks(filter_by="completed")
    elif filter_choice == "3":
        tasks = task_manager.view_tasks(filter_by="pending")
    else:
        tasks = task_manager.view_tasks()

    print_tasks(tasks)


def handle_mark_complete(task_manager: TaskManager) -> None:
    """Handle mark task complete menu option."""
    print_header("Mark Task Complete")
    all_tasks = task_manager.view_tasks()
    print_tasks(all_tasks)

    index = get_valid_task_index(
        len(all_tasks),
        "Enter task number to mark complete: ",
    )
    if index is None:
        return

    if all_tasks[index].status:
        print("Task is already completed.")
        return

    if task_manager.mark_task_complete(index):
        print("Task marked as completed.")
    else:
        print("Unable to mark task as completed.")


def handle_edit_task(task_manager: TaskManager) -> None:
    """Handle edit task menu option."""
    print_header("Edit Task")
    all_tasks = task_manager.view_tasks()
    print_tasks(all_tasks)

    index = get_valid_task_index(
        len(all_tasks),
        "Enter task number to edit: ",
    )
    if index is None:
        return

    new_description = input("Enter new task description: ").strip()
    if task_manager.update_task(index, new_description):
        print("Task updated successfully.")
    else:
        print("Update failed (empty, duplicate, or invalid task number).")


def handle_delete_task(task_manager: TaskManager) -> None:
    """Handle delete task menu option."""
    print_header("Delete Task")
    all_tasks = task_manager.view_tasks()
    print_tasks(all_tasks)

    index = get_valid_task_index(
        len(all_tasks),
        "Enter task number to delete: ",
    )
    if index is None:
        return

    confirmation = input("Are you sure? (y/n): ").strip().lower()
    if confirmation != "y":
        print("Delete operation cancelled.")
        return

    if task_manager.delete_task(index):
        print("Task deleted successfully.")
    else:
        print("Unable to delete task.")


def display_menu() -> None:
    """Display main menu options."""
    print_header("Task Manager")
    print("1. Add Task")
    print("2. View Tasks")
    print("3. Mark Task Complete")
    print("4. Edit Task")
    print("5. Delete Task")
    print("6. Exit")


def main() -> None:
    """Run the CLI application."""
    task_manager = TaskManager()

    while True:
        display_menu()
        choice = get_valid_menu_choice()

        if choice == 1:
            handle_add_task(task_manager)
        elif choice == 2:
            handle_view_tasks(task_manager)
        elif choice == 3:
            handle_mark_complete(task_manager)
        elif choice == 4:
            handle_edit_task(task_manager)
        elif choice == 5:
            handle_delete_task(task_manager)
        elif choice == 6:
            print("\nGoodbye! Your tasks are saved.")
            break


if __name__ == "__main__":
    main()
'''
