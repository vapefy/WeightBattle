"""
FastAPI application for Weight Battle.
All endpoints return JSON only.
"""

from datetime import date
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import os

import crud
import stats
import audit
import models

app = FastAPI(
    title="Weight Battle API",
    description="API for the family weight battle competition",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    start_weight: float = Field(..., gt=30, lt=300)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    start_weight: Optional[float] = Field(None, gt=30, lt=300)


class WeighInCreate(BaseModel):
    user_id: int
    weight: float = Field(..., gt=30, lt=300)
    week_start: Optional[str] = None  # ISO format date, defaults to current week


class ParticipantSetup(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    start_weight: float = Field(..., gt=30, lt=300)


class SetupCreate(BaseModel):
    participants: list[ParticipantSetup] = Field(..., min_length=1)
    pot_contribution: int = Field(..., ge=1, le=100)
    total_amount: int = Field(..., ge=10, le=1000)
    battle_end_date: str  # ISO format date


class ConfigUpdate(BaseModel):
    pot_contribution: Optional[int] = Field(None, ge=1, le=100)
    battle_end_date: Optional[str] = None


# ============================================================================
# Setup & Config Endpoints
# ============================================================================

@app.get("/setup/status")
def get_setup_status():
    """Check if the initial setup has been completed."""
    return {
        "setup_complete": models.is_setup_complete(),
        "has_users": len(crud.get_all_users()) > 0,
        "has_config": models.get_config("setup_complete") is not None,
    }


@app.post("/setup")
def complete_setup(setup: SetupCreate):
    """Complete the initial setup with participants and configuration."""
    # Validate end date
    try:
        date.fromisoformat(setup.battle_end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ungultiges Datum. Format: YYYY-MM-DD")

    # Check if already set up
    if models.is_setup_complete():
        raise HTTPException(status_code=400, detail="Setup wurde bereits abgeschlossen")

    # Save config
    models.set_config("pot_contribution", str(setup.pot_contribution))
    models.set_config("total_amount", str(setup.total_amount))
    models.set_config("battle_end_date", setup.battle_end_date)

    # Create participants
    created_users = []
    for participant in setup.participants:
        try:
            user = crud.create_user(
                name=participant.name,
                start_weight=participant.start_weight,
                created_by="setup"
            )
            created_users.append(user)
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                raise HTTPException(
                    status_code=400,
                    detail=f"Teilnehmer '{participant.name}' existiert bereits"
                )
            raise HTTPException(status_code=500, detail=str(e))

    # Mark setup as complete
    models.set_config("setup_complete", "true")

    return {
        "success": True,
        "participants": created_users,
        "config": {
            "pot_contribution": setup.pot_contribution,
            "total_amount": setup.total_amount,
            "battle_end_date": setup.battle_end_date,
        }
    }


@app.get("/config")
def get_config():
    """Get the current configuration."""
    return {
        "pot_contribution": models.get_pot_contribution(),
        "battle_end_date": models.get_battle_end_date(),
        "setup_complete": models.is_setup_complete(),
    }


@app.put("/config")
def update_config(config: ConfigUpdate):
    """Update the configuration."""
    if config.pot_contribution is not None:
        models.set_config("pot_contribution", str(config.pot_contribution))

    if config.battle_end_date is not None:
        try:
            date.fromisoformat(config.battle_end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Ungultiges Datum. Format: YYYY-MM-DD")
        models.set_config("battle_end_date", config.battle_end_date)

    return get_config()


@app.post("/setup/demo")
def load_demo_data():
    """Load demo data for testing purposes."""
    from datetime import timedelta

    # Check if already set up
    if models.is_setup_complete():
        raise HTTPException(status_code=400, detail="Setup wurde bereits abgeschlossen")

    # Demo participants with realistic starting weights
    participants = [
        ("Papa", 98.5),
        ("Mama", 72.3),
        ("Max", 88.0),
        ("Lisa", 65.8),
    ]

    # Weight change patterns (weekly kg change)
    patterns = {
        "Papa": [-0.8, -0.5, -0.3, +0.2, -0.6, -0.4, -0.7, -0.5],
        "Mama": [-0.4, -0.3, -0.5, -0.2, -0.4, -0.3, -0.2, -0.4],
        "Max":  [-1.0, -0.8, +0.5, -0.6, -0.9, +0.3, -0.7, -0.8],
        "Lisa": [-0.3, -0.4, -0.2, -0.3, -0.5, -0.3, -0.4, -0.3],
    }

    # Set config
    models.set_config("pot_contribution", "5")
    models.set_config("total_amount", "100")
    models.set_config("battle_end_date", "2026-04-05")

    # Create users
    users = {}
    for name, start_weight in participants:
        user = crud.create_user(name, start_weight, created_by="demo")
        users[name] = user

    # Generate weigh-ins for the past 8 weeks
    today = date.today()
    start_date = crud.get_week_start(today - timedelta(weeks=8))

    for week_num in range(8):
        week_start = start_date + timedelta(weeks=week_num)

        for name, (_, start_weight) in zip(users.keys(), participants):
            user = users[name]
            total_change = sum(patterns[name][:week_num + 1])
            weight = round(start_weight + total_change, 1)

            crud.create_weigh_in(
                user_id=user["id"],
                weight=weight,
                week_start=week_start,
                created_by=name
            )

    # Mark setup as complete
    models.set_config("setup_complete", "true")

    return {
        "success": True,
        "message": "Demo-Daten wurden geladen",
        "participants": len(participants),
        "weeks": 8,
    }


# ============================================================================
# User Endpoints
# ============================================================================

@app.get("/users")
def get_users():
    """Get all users/participants."""
    return crud.get_all_users()


@app.post("/users")
def create_user(user: UserCreate):
    """Create a new user/participant."""
    try:
        return crud.create_user(name=user.name, start_weight=user.start_weight)
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            raise HTTPException(status_code=400, detail="User with this name already exists")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}")
def get_user(user_id: int):
    """Get a specific user by ID."""
    user = crud.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/users/{user_id}")
def update_user(user_id: int, user: UserUpdate):
    """Update a user's information."""
    updated = crud.update_user(
        user_id=user_id,
        name=user.name,
        start_weight=user.start_weight
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated


# ============================================================================
# Week Endpoints
# ============================================================================

@app.get("/weeks/current")
def get_current_week():
    """Get information about the current week."""
    week_start = crud.get_current_week_start()
    weigh_ins = crud.get_week_weigh_ins(week_start)
    result = crud.get_weekly_result(week_start)
    users = crud.get_all_users()

    # Calculate who hasn't weighed in yet
    weighed_in_ids = {wi["user_id"] for wi in weigh_ins}
    missing = [u for u in users if u["id"] not in weighed_in_ids]

    return {
        "week_start": week_start.isoformat(),
        "week_end": (week_start + __import__("datetime").timedelta(days=6)).isoformat(),
        "weigh_ins": weigh_ins,
        "result": result,
        "missing_participants": missing,
        "all_weighed_in": len(missing) == 0 and len(users) > 0,
    }


@app.get("/weeks/{week_start}")
def get_week(week_start: str):
    """Get information about a specific week."""
    try:
        week_date = date.fromisoformat(week_start)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    weigh_ins = crud.get_week_weigh_ins(week_date)
    result = crud.get_weekly_result(week_date)
    comparison = stats.get_weekly_comparison(week_date)

    return {
        "week_start": week_start,
        "weigh_ins": weigh_ins,
        "result": result,
        "comparison": comparison,
    }


# ============================================================================
# Weigh-in Endpoints
# ============================================================================

@app.post("/weigh-ins")
def create_weigh_in(weigh_in: WeighInCreate):
    """Record a weigh-in for a user."""
    # Validate user exists
    user = crud.get_user(weigh_in.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Parse week_start if provided
    week_start = None
    if weigh_in.week_start:
        try:
            week_start = date.fromisoformat(weigh_in.week_start)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    result = crud.create_weigh_in(
        user_id=weigh_in.user_id,
        weight=weigh_in.weight,
        week_start=week_start,
        created_by=user["name"]
    )

    # Calculate percentage change for response
    actual_week = week_start or crud.get_current_week_start()
    prev_weight = crud.get_previous_weight(weigh_in.user_id, actual_week)
    pct_change = crud.calculate_percentage_change(prev_weight, weigh_in.weight) if prev_weight else 0

    return {
        "weigh_in": result,
        "previous_weight": prev_weight,
        "percent_change": round(pct_change, 2),
    }


@app.get("/weigh-ins/user/{user_id}")
def get_user_weigh_ins(user_id: int):
    """Get all weigh-ins for a specific user."""
    user = crud.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return crud.get_user_weigh_ins(user_id)


@app.get("/weigh-ins/preview")
def preview_weigh_in(user_id: int, weight: float):
    """Preview what the percentage change would be without saving."""
    user = crud.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    week_start = crud.get_current_week_start()
    prev_weight = crud.get_previous_weight(user_id, week_start)

    if not prev_weight:
        prev_weight = user["start_weight"]

    pct_change = crud.calculate_percentage_change(prev_weight, weight)

    return {
        "user_id": user_id,
        "weight": weight,
        "previous_weight": prev_weight,
        "percent_change": round(pct_change, 2),
    }


# ============================================================================
# Statistics Endpoints
# ============================================================================

@app.get("/stats/overview")
def get_overview():
    """Get a complete overview of the battle state."""
    return stats.get_overview()


@app.get("/stats/user/{user_id}")
def get_user_stats(user_id: int):
    """Get detailed statistics for a specific user."""
    user_stats = stats.get_user_stats(user_id)
    if not user_stats:
        raise HTTPException(status_code=404, detail="User not found")
    return user_stats


@app.get("/stats/pot")
def get_pot():
    """Get POT information (total, contributions, who pays at the end)."""
    return stats.get_pot_info()


@app.get("/stats/prognosis")
def get_prognosis():
    """Get weight projections until battle end."""
    return stats.get_prognosis()


@app.get("/stats/leaderboard")
def get_leaderboard():
    """Get the current leaderboard."""
    return stats.get_leaderboard()


@app.get("/stats/progress")
def get_progress():
    """Get relative progress data for charting."""
    return stats.get_relative_progress()


# ============================================================================
# Audit Endpoints
# ============================================================================

@app.get("/audit")
def get_audit_log(
    entity: Optional[str] = None,
    entity_id: Optional[int] = None,
    limit: int = 100
):
    """Get audit log entries."""
    return audit.get_audit_log(entity=entity, entity_id=entity_id, limit=limit)


# ============================================================================
# Serve Frontend (optional - for simple deployment)
# ============================================================================

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
