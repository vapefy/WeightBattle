"""
CRUD operations for Weight Battle database.
All database access should go through this module.
"""

from datetime import date, datetime, timedelta
from typing import Optional
from models import get_db, get_pot_contribution
from audit import log_change


# ============================================================================
# User Operations
# ============================================================================

def create_user(name: str, start_weight: float, created_by: str = "system") -> dict:
    """
    Create a new user/participant.

    Args:
        name: Display name of the user
        start_weight: Starting weight in kg
        created_by: Who created this user

    Returns:
        The created user record
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (name, start_weight)
            VALUES (?, ?)
        """, (name, round(start_weight, 1)))
        user_id = cursor.lastrowid

        # Log the creation (pass cursor to avoid nested connection)
        log_change(
            entity="user",
            entity_id=user_id,
            old_value=None,
            new_value={"name": name, "start_weight": start_weight},
            changed_by=created_by,
            cursor=cursor
        )

    return get_user(user_id)


def get_user(user_id: int) -> Optional[dict]:
    """Get a user by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_all_users() -> list[dict]:
    """Get all users."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]


def update_user(
    user_id: int,
    name: Optional[str] = None,
    start_weight: Optional[float] = None,
    changed_by: str = "system"
) -> Optional[dict]:
    """Update a user's information."""
    user = get_user(user_id)
    if not user:
        return None

    old_value = {"name": user["name"], "start_weight": user["start_weight"]}
    new_name = name if name is not None else user["name"]
    new_weight = round(start_weight, 1) if start_weight is not None else user["start_weight"]

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET name = ?, start_weight = ? WHERE id = ?
        """, (new_name, new_weight, user_id))

        log_change(
            entity="user",
            entity_id=user_id,
            old_value=old_value,
            new_value={"name": new_name, "start_weight": new_weight},
            changed_by=changed_by,
            cursor=cursor
        )

    return get_user(user_id)


# ============================================================================
# Weigh-in Operations
# ============================================================================

def get_week_start(d: date = None) -> date:
    """
    Get the Monday of the week for a given date.
    Week starts on Monday, weigh-in is on Sunday.
    """
    if d is None:
        d = date.today()
    # Monday is weekday 0
    days_since_monday = d.weekday()
    return d - timedelta(days=days_since_monday)


def get_current_week_start() -> date:
    """Get the start of the current week."""
    return get_week_start(date.today())


def create_weigh_in(
    user_id: int,
    weight: float,
    week_start: date = None,
    created_by: str = "system"
) -> dict:
    """
    Record a weigh-in for a user.
    If a weigh-in already exists for this week, it will be updated.

    Args:
        user_id: The user's ID
        weight: Weight in kg
        week_start: The Monday of the week (defaults to current week)
        created_by: Who recorded this weigh-in

    Returns:
        The weigh-in record
    """
    if week_start is None:
        week_start = get_current_week_start()

    weight = round(weight, 1)

    # Check if weigh-in already exists
    existing = get_weigh_in(user_id, week_start)

    with get_db() as conn:
        cursor = conn.cursor()

        if existing:
            # Update existing weigh-in
            old_value = {"weight": existing["weight"]}
            cursor.execute("""
                UPDATE weigh_ins
                SET weight = ?, created_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND week_start = ?
            """, (weight, user_id, week_start.isoformat()))

            log_change(
                entity="weigh_in",
                entity_id=existing["id"],
                old_value=old_value,
                new_value={"weight": weight},
                changed_by=created_by,
                cursor=cursor
            )
        else:
            # Create new weigh-in
            cursor.execute("""
                INSERT INTO weigh_ins (user_id, week_start, weight)
                VALUES (?, ?, ?)
            """, (user_id, week_start.isoformat(), weight))

            weigh_in_id = cursor.lastrowid
            log_change(
                entity="weigh_in",
                entity_id=weigh_in_id,
                old_value=None,
                new_value={"user_id": user_id, "week_start": week_start.isoformat(), "weight": weight},
                changed_by=created_by,
                cursor=cursor
            )

    # Recalculate weekly results after weigh-in
    calculate_weekly_result(week_start)

    return get_weigh_in(user_id, week_start)


def get_weigh_in(user_id: int, week_start: date) -> Optional[dict]:
    """Get a specific weigh-in."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM weigh_ins
            WHERE user_id = ? AND week_start = ?
        """, (user_id, week_start.isoformat()))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_user_weigh_ins(user_id: int) -> list[dict]:
    """Get all weigh-ins for a user, ordered by date."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM weigh_ins
            WHERE user_id = ?
            ORDER BY week_start
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_week_weigh_ins(week_start: date) -> list[dict]:
    """Get all weigh-ins for a specific week."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT wi.*, u.name as user_name
            FROM weigh_ins wi
            JOIN users u ON wi.user_id = u.id
            WHERE wi.week_start = ?
        """, (week_start.isoformat(),))
        return [dict(row) for row in cursor.fetchall()]


def get_previous_weight(user_id: int, week_start: date) -> Optional[float]:
    """
    Get the reference weight for calculating percentage change.
    Uses previous week's weight, or start_weight if no previous weigh-in.
    """
    # Get previous week's weigh-in
    prev_week = week_start - timedelta(days=7)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT weight FROM weigh_ins
            WHERE user_id = ? AND week_start = ?
        """, (user_id, prev_week.isoformat()))
        row = cursor.fetchone()
        if row:
            return row["weight"]

        # No previous weigh-in, use start_weight
        cursor.execute("SELECT start_weight FROM users WHERE id = ?", (user_id,))
        user_row = cursor.fetchone()
        if user_row:
            return user_row["start_weight"]

    return None


# ============================================================================
# Weekly Results Operations
# ============================================================================

def calculate_percentage_change(previous_weight: float, current_weight: float) -> float:
    """
    Calculate the percentage weight change.
    Positive = weight loss (good), Negative = weight gain (bad)
    """
    if previous_weight == 0:
        return 0.0
    return ((previous_weight - current_weight) / previous_weight) * 100


def calculate_weekly_result(week_start: date) -> Optional[dict]:
    """
    Calculate and store the weekly result (winner/loser).
    Must be called after all weigh-ins for the week are recorded.
    """
    users = get_all_users()
    weigh_ins = get_week_weigh_ins(week_start)

    if len(weigh_ins) < len(users):
        # Not all participants have weighed in yet
        # Clear any existing result
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM weekly_results WHERE week_start = ?",
                          (week_start.isoformat(),))
        return None

    # Calculate percentage change for each participant
    changes = []
    for wi in weigh_ins:
        prev_weight = get_previous_weight(wi["user_id"], week_start)
        if prev_weight is None:
            continue

        pct_change = calculate_percentage_change(prev_weight, wi["weight"])
        changes.append({
            "user_id": wi["user_id"],
            "percent_change": pct_change
        })

    if not changes:
        return None

    # Sort by percentage change (highest = best)
    changes.sort(key=lambda x: x["percent_change"], reverse=True)

    winner_id = None
    loser_id = None
    pot_change = 0

    # Check for tie at the top (no winner)
    if len(changes) >= 2:
        top_change = changes[0]["percent_change"]
        second_change = changes[1]["percent_change"]

        # Not a tie at top
        if abs(top_change - second_change) >= 0.01:
            winner_id = changes[0]["user_id"]

        # Check for tie at bottom (no loser/pot payment)
        bottom_change = changes[-1]["percent_change"]
        second_bottom_change = changes[-2]["percent_change"]

        if abs(bottom_change - second_bottom_change) >= 0.01:
            loser_id = changes[-1]["user_id"]
            pot_change = get_pot_contribution()

    elif len(changes) == 1:
        # Only one participant - they're the winner by default
        winner_id = changes[0]["user_id"]

    # Store the result
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO weekly_results (week_start, winner_user_id, loser_user_id, pot_change)
            VALUES (?, ?, ?, ?)
        """, (week_start.isoformat(), winner_id, loser_id, pot_change))

    return get_weekly_result(week_start)


def get_weekly_result(week_start: date) -> Optional[dict]:
    """Get the result for a specific week."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT wr.*,
                   w.name as winner_name,
                   l.name as loser_name
            FROM weekly_results wr
            LEFT JOIN users w ON wr.winner_user_id = w.id
            LEFT JOIN users l ON wr.loser_user_id = l.id
            WHERE wr.week_start = ?
        """, (week_start.isoformat(),))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_all_weekly_results() -> list[dict]:
    """Get all weekly results."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT wr.*,
                   w.name as winner_name,
                   l.name as loser_name
            FROM weekly_results wr
            LEFT JOIN users w ON wr.winner_user_id = w.id
            LEFT JOIN users l ON wr.loser_user_id = l.id
            ORDER BY wr.week_start DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


# ============================================================================
# POT Operations
# ============================================================================

def get_pot_total() -> int:
    """Get the current total in the POT."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(pot_change), 0) as total FROM weekly_results")
        row = cursor.fetchone()
        return row["total"] if row else 0


def get_pot_contributions() -> list[dict]:
    """Get breakdown of who contributed to the POT."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.name,
                   COUNT(wr.loser_user_id) as times_lost,
                   COALESCE(SUM(wr.pot_change), 0) as total_contributed
            FROM users u
            LEFT JOIN weekly_results wr ON u.id = wr.loser_user_id
            GROUP BY u.id
            ORDER BY total_contributed DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
