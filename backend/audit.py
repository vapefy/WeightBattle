"""
Audit logging for transparent change tracking.
All modifications are logged with who, when, and what changed.
"""

import json
from datetime import datetime
from typing import Any, Optional
from models import get_db


def log_change(
    entity: str,
    entity_id: int,
    old_value: Any,
    new_value: Any,
    changed_by: str,
    cursor=None
) -> int:
    """
    Log a change to the audit log.

    Args:
        entity: The type of entity changed (e.g., 'user', 'weigh_in')
        entity_id: The ID of the entity
        old_value: The previous value (will be JSON serialized)
        new_value: The new value (will be JSON serialized)
        changed_by: Who made the change
        cursor: Optional cursor to reuse existing connection

    Returns:
        The ID of the audit log entry
    """
    old_json = json.dumps(old_value) if old_value is not None else None
    new_json = json.dumps(new_value) if new_value is not None else None

    if cursor:
        cursor.execute("""
            INSERT INTO audit_log (entity, entity_id, old_value, new_value, changed_by)
            VALUES (?, ?, ?, ?, ?)
        """, (entity, entity_id, old_json, new_json, changed_by))
        return cursor.lastrowid
    else:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO audit_log (entity, entity_id, old_value, new_value, changed_by)
                VALUES (?, ?, ?, ?, ?)
            """, (entity, entity_id, old_json, new_json, changed_by))
            return cur.lastrowid


def get_audit_log(
    entity: Optional[str] = None,
    entity_id: Optional[int] = None,
    limit: int = 100
) -> list[dict]:
    """
    Retrieve audit log entries.

    Args:
        entity: Filter by entity type
        entity_id: Filter by entity ID
        limit: Maximum number of entries to return

    Returns:
        List of audit log entries
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []

        if entity:
            query += " AND entity = ?"
            params.append(entity)

        if entity_id is not None:
            query += " AND entity_id = ?"
            params.append(entity_id)

        query += " ORDER BY changed_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "entity": row["entity"],
                "entity_id": row["entity_id"],
                "old_value": json.loads(row["old_value"]) if row["old_value"] else None,
                "new_value": json.loads(row["new_value"]) if row["new_value"] else None,
                "changed_by": row["changed_by"],
                "changed_at": row["changed_at"]
            }
            for row in rows
        ]


def get_recent_changes(limit: int = 10) -> list[dict]:
    """Get the most recent changes across all entities."""
    return get_audit_log(limit=limit)
