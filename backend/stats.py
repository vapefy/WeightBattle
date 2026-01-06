"""
Statistics and forecasting for Weight Battle.
Includes leaderboard, progress tracking, and linear regression forecasts.
"""

from datetime import date, datetime, timedelta
from typing import Optional
from models import get_db, get_battle_end_date, get_pot_contribution, get_total_amount
from crud import (
    get_all_users,
    get_user_weigh_ins,
    get_all_weekly_results,
    get_pot_total,
    get_pot_contributions,
    get_previous_weight,
    calculate_percentage_change,
    get_week_weigh_ins,
    get_current_week_start,
)


# Threshold for "head-to-head" race detection
HEAD_TO_HEAD_THRESHOLD = 0.3  # percent


def get_leaderboard() -> list[dict]:
    """
    Get the current leaderboard based on total weekly wins.
    Returns users sorted by wins (descending).
    """
    users = get_all_users()
    results = get_all_weekly_results()

    # Count wins per user
    win_counts = {u["id"]: 0 for u in users}
    for result in results:
        if result["winner_user_id"]:
            win_counts[result["winner_user_id"]] = win_counts.get(result["winner_user_id"], 0) + 1

    # Build leaderboard
    leaderboard = []
    for user in users:
        weigh_ins = get_user_weigh_ins(user["id"])
        current_weight = weigh_ins[-1]["weight"] if weigh_ins else user["start_weight"]
        total_change = calculate_percentage_change(user["start_weight"], current_weight)

        leaderboard.append({
            "user_id": user["id"],
            "name": user["name"],
            "wins": win_counts[user["id"]],
            "start_weight": user["start_weight"],
            "current_weight": current_weight,
            "total_percent_change": round(total_change, 2),
        })

    # Sort by wins (descending), then by total percent change (descending)
    leaderboard.sort(key=lambda x: (x["wins"], x["total_percent_change"]), reverse=True)

    # Add rank
    for i, entry in enumerate(leaderboard):
        entry["rank"] = i + 1

    return leaderboard


def get_user_stats(user_id: int) -> Optional[dict]:
    """
    Get detailed statistics for a specific user.
    """
    from crud import get_user
    user = get_user(user_id)
    if not user:
        return None

    weigh_ins = get_user_weigh_ins(user_id)
    results = get_all_weekly_results()

    # Count wins and losses
    wins = sum(1 for r in results if r["winner_user_id"] == user_id)
    losses = sum(1 for r in results if r["loser_user_id"] == user_id)

    # Calculate current stats
    current_weight = weigh_ins[-1]["weight"] if weigh_ins else user["start_weight"]
    total_change = calculate_percentage_change(user["start_weight"], current_weight)

    # Build weekly history
    weekly_data = []
    for wi in weigh_ins:
        week_start = date.fromisoformat(wi["week_start"]) if isinstance(wi["week_start"], str) else wi["week_start"]
        prev_weight = get_previous_weight(user_id, week_start)
        pct_change = calculate_percentage_change(prev_weight, wi["weight"]) if prev_weight else 0

        weekly_data.append({
            "week_start": wi["week_start"],
            "weight": wi["weight"],
            "percent_change": round(pct_change, 2),
            "relative_to_start": round((wi["weight"] / user["start_weight"]) * 100, 2),
        })

    return {
        "user_id": user_id,
        "name": user["name"],
        "start_weight": user["start_weight"],
        "current_weight": current_weight,
        "total_percent_change": round(total_change, 2),
        "wins": wins,
        "losses": losses,
        "weeks_participated": len(weigh_ins),
        "weekly_data": weekly_data,
    }


def get_overview() -> dict:
    """
    Get an overview of the current battle state.
    """
    users = get_all_users()
    leaderboard = get_leaderboard()
    pot_total = get_pot_total()
    current_week = get_current_week_start()

    # Get current week weigh-ins
    current_weigh_ins = get_week_weigh_ins(current_week)
    weighed_in_ids = {wi["user_id"] for wi in current_weigh_ins}
    missing_weigh_ins = [u["name"] for u in users if u["id"] not in weighed_in_ids]

    # Calculate current week standings
    week_standings = []
    for wi in current_weigh_ins:
        week_start = current_week
        prev_weight = get_previous_weight(wi["user_id"], week_start)
        if prev_weight:
            pct_change = calculate_percentage_change(prev_weight, wi["weight"])
            week_standings.append({
                "user_id": wi["user_id"],
                "name": wi["user_name"],
                "weight": wi["weight"],
                "percent_change": round(pct_change, 2),
            })

    week_standings.sort(key=lambda x: x["percent_change"], reverse=True)

    # Detect head-to-head race
    head_to_head = False
    if len(week_standings) >= 2:
        diff = abs(week_standings[0]["percent_change"] - week_standings[1]["percent_change"])
        head_to_head = diff < HEAD_TO_HEAD_THRESHOLD

    # Get leader info
    leader = leaderboard[0] if leaderboard else None

    # Calculate days until battle end
    battle_end_date = get_battle_end_date()
    end_date = date.fromisoformat(battle_end_date)
    days_remaining = (end_date - date.today()).days

    return {
        "current_week": current_week.isoformat(),
        "battle_end_date": battle_end_date,
        "days_remaining": max(0, days_remaining),
        "total_participants": len(users),
        "pot_total": pot_total,
        "leader": leader,
        "current_week_standings": week_standings,
        "missing_weigh_ins": missing_weigh_ins,
        "head_to_head": head_to_head,
        "leaderboard": leaderboard,
    }


def get_pot_info() -> dict:
    """
    Get detailed POT information.
    """
    total = get_pot_total()
    contributions = get_pot_contributions()
    results = get_all_weekly_results()
    total_amount = get_total_amount()

    # Get recent contributions (last 5)
    recent = []
    for result in results[:5]:
        if result["loser_user_id"] and result["pot_change"] > 0:
            recent.append({
                "week_start": result["week_start"],
                "loser_name": result["loser_name"],
                "amount": result["pot_change"],
            })

    # Determine who would pay the rest (most losses)
    if contributions:
        max_losses = max(c["times_lost"] for c in contributions)
        potential_payers = [c for c in contributions if c["times_lost"] == max_losses]
    else:
        potential_payers = []

    # Calculate remaining amount the loser needs to pay
    remaining_amount = max(0, total_amount - total)

    return {
        "total": total,
        "total_amount": total_amount,
        "remaining_amount": remaining_amount,
        "contributions": contributions,
        "recent_contributions": recent,
        "potential_final_payers": potential_payers,
    }


def linear_regression(x_values: list, y_values: list) -> tuple[float, float]:
    """
    Simple linear regression to find slope and intercept.
    Returns (slope, intercept)
    """
    n = len(x_values)
    if n < 2:
        return 0.0, y_values[0] if y_values else 0.0

    sum_x = sum(x_values)
    sum_y = sum(y_values)
    sum_xy = sum(x * y for x, y in zip(x_values, y_values))
    sum_x2 = sum(x * x for x in x_values)

    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        return 0.0, sum_y / n

    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n

    return slope, intercept


def get_prognosis() -> dict:
    """
    Get weight projections for all users until the battle end date.
    Uses simple linear regression on weekly weights.
    """
    users = get_all_users()
    battle_end_date = get_battle_end_date()
    end_date = date.fromisoformat(battle_end_date)
    today = date.today()
    weeks_remaining = max(0, (end_date - today).days // 7)

    projections = []

    for user in users:
        weigh_ins = get_user_weigh_ins(user["id"])

        if len(weigh_ins) < 2:
            # Not enough data for projection
            projections.append({
                "user_id": user["id"],
                "name": user["name"],
                "current_weight": weigh_ins[-1]["weight"] if weigh_ins else user["start_weight"],
                "projected_weight": None,
                "projected_total_change": None,
                "trend": "insufficient_data",
            })
            continue

        # Convert weigh-ins to numerical format for regression
        weights = [wi["weight"] for wi in weigh_ins]
        weeks = list(range(len(weights)))

        slope, intercept = linear_regression(weeks, weights)

        # Project to end date
        projected_week = len(weights) + weeks_remaining
        projected_weight = intercept + slope * projected_week

        # Don't allow negative weights
        projected_weight = max(projected_weight, 40.0)

        current_weight = weights[-1]
        projected_change = calculate_percentage_change(user["start_weight"], projected_weight)

        # Determine trend
        if slope < -0.1:
            trend = "losing"  # Weight going down (good)
        elif slope > 0.1:
            trend = "gaining"  # Weight going up
        else:
            trend = "stable"

        projections.append({
            "user_id": user["id"],
            "name": user["name"],
            "current_weight": current_weight,
            "projected_weight": round(projected_weight, 1),
            "projected_total_change": round(projected_change, 2),
            "weekly_trend": round(slope, 2),
            "trend": trend,
        })

    # Sort by projected change (best first)
    projections.sort(
        key=lambda x: x["projected_total_change"] if x["projected_total_change"] is not None else -999,
        reverse=True
    )

    return {
        "battle_end_date": battle_end_date,
        "weeks_remaining": weeks_remaining,
        "projections": projections,
    }


def get_weekly_comparison(week_start: date = None) -> dict:
    """
    Get side-by-side comparison of all users for a specific week.
    """
    if week_start is None:
        week_start = get_current_week_start()

    weigh_ins = get_week_weigh_ins(week_start)
    users = get_all_users()

    comparison = []
    for user in users:
        wi = next((w for w in weigh_ins if w["user_id"] == user["id"]), None)

        if wi:
            prev_weight = get_previous_weight(user["id"], week_start)
            pct_change = calculate_percentage_change(prev_weight, wi["weight"]) if prev_weight else 0

            comparison.append({
                "user_id": user["id"],
                "name": user["name"],
                "weight": wi["weight"],
                "percent_change": round(pct_change, 2),
                "weighed_in": True,
            })
        else:
            comparison.append({
                "user_id": user["id"],
                "name": user["name"],
                "weight": None,
                "percent_change": None,
                "weighed_in": False,
            })

    comparison.sort(
        key=lambda x: x["percent_change"] if x["percent_change"] is not None else -999,
        reverse=True
    )

    return {
        "week_start": week_start.isoformat(),
        "comparison": comparison,
    }


def get_relative_progress() -> dict:
    """
    Get progress data relative to start weight (start = 100%).
    Used for charting.
    """
    users = get_all_users()
    progress_data = []

    for user in users:
        weigh_ins = get_user_weigh_ins(user["id"])
        start = user["start_weight"]

        data_points = [{"week": "Start", "value": 100.0}]

        for wi in weigh_ins:
            relative = (wi["weight"] / start) * 100
            data_points.append({
                "week": wi["week_start"],
                "value": round(relative, 2),
            })

        progress_data.append({
            "user_id": user["id"],
            "name": user["name"],
            "data": data_points,
        })

    return {
        "progress_data": progress_data,
    }
