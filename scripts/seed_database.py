"""Seed the development database with a default user and sample data."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bson import ObjectId


async def seed() -> None:
    # Import after path setup
    from server.app.models.database.connection import Database

    await Database.connect()
    db = Database.get_db()

    now = datetime.now(timezone.utc)

    # ── Default User ──────────────────────────────────────────────
    default_user_id = ObjectId("000000000000000000000001")
    user = await db.users.find_one({"_id": default_user_id})
    if not user:
        await db.users.insert_one({
            "_id": default_user_id,
            "username": "aegis_user",
            "display_name": "AEGIS User",
            "email": "user@aegis.local",
            "created_at": now,
            "settings": {
                "penalty_duration_minutes": 30,
                "focus_zone_radius_meters": 30,
                "grace_period_seconds": 120,
                "notification_preferences": {"preference": "both"},
            },
            "trusted_contacts": [],
            "current_state": {
                "in_penalty_box": False,
                "penalty_expires_at": None,
                "in_focus_zone": False,
                "active_task_id": None,
            },
        })
        print("[+] Created default user: aegis_user")
    else:
        print("[=] Default user already exists")

    # ── Sample Tasks ──────────────────────────────────────────────
    user_id = str(default_user_id)
    task_count = await db.tasks.count_documents({"user_id": user_id})
    if task_count == 0:
        sample_tasks = [
            {
                "user_id": user_id,
                "title": "Morning Code Review",
                "description": "Review open PRs and provide feedback",
                "category": "work",
                "priority": 4,
                "scheduled_start": now + timedelta(hours=1),
                "scheduled_end": now + timedelta(hours=2),
                "duration_minutes": 60,
                "recurrence": {"pattern": "daily", "days": [1, 2, 3, 4, 5]},
                "verification": {
                    "method": "activity_log",
                    "config": {"app_names": ["GitHub", "GitLab"]},
                    "required_confidence": 0.7,
                },
                "status": "pending",
                "completion_evidence": [],
                "verification_result": None,
                "failure_count": 0,
                "tags": ["work", "code-review"],
                "created_at": now,
                "updated_at": now,
            },
            {
                "user_id": user_id,
                "title": "Afternoon Workout",
                "description": "30-minute HIIT session",
                "category": "health",
                "priority": 3,
                "scheduled_start": now + timedelta(hours=6),
                "scheduled_end": now + timedelta(hours=6, minutes=30),
                "duration_minutes": 30,
                "recurrence": {"pattern": "daily", "days": [1, 2, 3, 4, 5]},
                "verification": {
                    "method": "manual",
                    "config": {},
                    "required_confidence": 0.8,
                },
                "status": "pending",
                "completion_evidence": [],
                "verification_result": None,
                "failure_count": 0,
                "tags": ["health", "exercise"],
                "created_at": now,
                "updated_at": now,
            },
            {
                "user_id": user_id,
                "title": "Read ML Chapter",
                "description": "Read one chapter from current ML textbook",
                "category": "learning",
                "priority": 2,
                "scheduled_start": now + timedelta(hours=10),
                "scheduled_end": now + timedelta(hours=11),
                "duration_minutes": 60,
                "recurrence": None,
                "verification": {
                    "method": "manual",
                    "config": {},
                    "required_confidence": 0.8,
                },
                "status": "pending",
                "completion_evidence": [],
                "verification_result": None,
                "failure_count": 0,
                "tags": ["learning", "ml"],
                "created_at": now,
                "updated_at": now,
            },
        ]
        await db.tasks.insert_many(sample_tasks)
        print(f"[+] Created {len(sample_tasks)} sample tasks")
    else:
        print(f"[=] {task_count} tasks already exist")

    await Database.disconnect()
    print("[*] Seed complete")


if __name__ == "__main__":
    asyncio.run(seed())
