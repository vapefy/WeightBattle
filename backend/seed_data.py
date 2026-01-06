"""
Seed script to populate the database with realistic test data.
Run this once to create sample data for testing.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from models import init_db, get_db, set_config
from crud import create_user, create_weigh_in, get_week_start

# Clear existing data and reinitialize
def clear_database():
    """Clear all data from the database."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM weekly_results")
        cursor.execute("DELETE FROM weigh_ins")
        cursor.execute("DELETE FROM audit_log")
        cursor.execute("DELETE FROM users")
        cursor.execute("DELETE FROM config")
    print("Database cleared.")


def setup_config():
    """Set up default configuration."""
    set_config("pot_contribution", "5")
    set_config("total_amount", "100")
    set_config("battle_end_date", "2026-04-05")
    set_config("setup_complete", "true")
    print("Config set up.")

def seed_data():
    """Seed the database with realistic test data."""

    # Create participants with realistic starting weights
    participants = [
        ("Papa", 98.5),
        ("Mama", 72.3),
        ("Max", 88.0),
        ("Lisa", 65.8),
    ]

    users = {}
    for name, start_weight in participants:
        user = create_user(name, start_weight, created_by="seed_script")
        users[name] = user
        print(f"Created user: {name} ({start_weight} kg)")

    # Generate weigh-ins for the past 8 weeks
    # Each person has a different weight loss pattern

    # Weight change patterns (weekly kg change, with some randomness)
    # Negative = weight loss, Positive = weight gain
    patterns = {
        "Papa": [-0.8, -0.5, -0.3, +0.2, -0.6, -0.4, -0.7, -0.5],  # Steady loser
        "Mama": [-0.4, -0.3, -0.5, -0.2, -0.4, -0.3, -0.2, -0.4],  # Consistent small losses
        "Max":  [-1.0, -0.8, +0.5, -0.6, -0.9, +0.3, -0.7, -0.8],  # Volatile
        "Lisa": [-0.3, -0.4, -0.2, -0.3, -0.5, -0.3, -0.4, -0.3],  # Very consistent
    }

    # Start 8 weeks ago
    today = date.today()
    start_date = get_week_start(today - timedelta(weeks=8))

    print(f"\nGenerating weigh-ins from {start_date} to {today}...")

    for week_num in range(8):
        week_start = start_date + timedelta(weeks=week_num)
        print(f"\nWeek {week_num + 1} ({week_start}):")

        for name, (_, start_weight) in zip(users.keys(), participants):
            user = users[name]

            # Calculate weight for this week
            total_change = sum(patterns[name][:week_num + 1])
            weight = round(start_weight + total_change, 1)

            # Create weigh-in
            create_weigh_in(
                user_id=user["id"],
                weight=weight,
                week_start=week_start,
                created_by=name
            )

            # Calculate percentage change for display
            if week_num == 0:
                prev_weight = start_weight
            else:
                prev_change = sum(patterns[name][:week_num])
                prev_weight = start_weight + prev_change

            pct_change = ((prev_weight - weight) / prev_weight) * 100
            print(f"  {name}: {weight} kg ({pct_change:+.2f}%)")

    print("\n" + "="*50)
    print("Seed data created successfully!")
    print("="*50)

    # Print summary
    print("\nSummary:")
    for name, (_, start_weight) in zip(users.keys(), participants):
        total_change = sum(patterns[name])
        final_weight = start_weight + total_change
        total_pct = ((start_weight - final_weight) / start_weight) * 100
        print(f"  {name}: {start_weight} kg -> {final_weight:.1f} kg ({total_pct:+.2f}% total)")


if __name__ == "__main__":
    print("Weight Battle - Seed Data Script")
    print("="*50)

    clear_database()
    setup_config()
    seed_data()
