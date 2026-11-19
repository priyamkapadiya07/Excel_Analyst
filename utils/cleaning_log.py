"""
Audit log for data cleaning operations.
Tracks every transformation applied, timestamps, affected rows/columns, and parameters.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class CleaningLogEntry:
    timestamp: str
    action: str
    column: Optional[str]
    description: str
    affected_count: int
    details: Dict[str, Any] = field(default_factory=dict)


class CleaningLogger:
    """Manages cleaning history and operation logs."""

    def __init__(self):
        self.entries: List[CleaningLogEntry] = []

    def log(
        self,
        action: str,
        description: str,
        column: Optional[str] = None,
        affected_count: int = 0,
        **details,
    ) -> CleaningLogEntry:
        entry = CleaningLogEntry(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action=action,
            column=column,
            description=description,
            affected_count=affected_count,
            details=details,
        )
        self.entries.append(entry)
        return entry

    def clear(self):
        self.entries.clear()

    def get_summary(self) -> List[Dict[str, Any]]:
        return [
            {
                "Timestamp": e.timestamp,
                "Action": e.action,
                "Target": e.column or "Dataset Level",
                "Description": e.description,
                "Affected Items": e.affected_count,
            }
            for e in self.entries
        ]
