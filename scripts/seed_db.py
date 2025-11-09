from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
import random
import string

# Parking (SQLModel)
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from parking_app import (
    Reservation as ParkingReservation,
    create_db_and_tables as parking_create,
    engine as parking_engine,
    LOT_NAME,
    _assign_spot,
    _compute_price_cents,
    _generate_code,
)
from sqlmodel import Session as SQLModelSession

# Voice intake demo (SQLAlchemy)
try:
    from app.db import Base as SA_Base, engine as sa_engine
    from app.models import Intake
    HAS_INTAKE = True
except Exception:
    HAS_INTAKE = False


FIRST_NAMES = [
    "Aarav", "Nikhil", "Maya", "Aisha", "Ishan", "Carlos", "Elena", "Noah", "Liam", "Olivia",
    "Emma", "Ava", "Sophia", "Isabella", "Mia", "Charlotte", "Amelia", "Harper", "Ethan", "Logan",
]
LAST_NAMES = [
    "Sharma", "Patel", "Khan", "Gupta", "Singh", "Garcia", "Rodriguez", "Martinez", "Chen", "Lee",
    "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White",
]
DOMAINS = ["example.com", "mail.com", "demo.net", "sample.org", "inbox.test"]


def random_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_email(name: str) -> str:
    local = name.lower().replace(" ", ".")
    return f"{local}{random.randint(1,9999)}@{random.choice(DOMAINS)}"


def random_phone() -> str:
    return "+1" + str(random.randint(2000000000, 9999999999))


def random_plate() -> str:
    # e.g., KA01AB1234 style
    letters = string.ascii_uppercase
    return f"{random.choice(letters)}{random.choice(letters)}{random.randint(0,9)}{random.randint(0,9)}" \
           f"{random.choice(letters)}{random.choice(letters)}{random.randint(1000,9999)}"


def seed_parking(count: int = 200, days: int = 14) -> int:
    parking_create()
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    created = 0
    attempts = 0
    max_attempts = count * 10
    vehicle_types = [None, "car", "motorcycle", "truck"]

    with SQLModelSession(parking_engine) as session:
        while created < count and attempts < max_attempts:
            attempts += 1
            start_day_offset = random.randint(0, max(1, days))
            start_hour = random.choice([7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18])
            start = (now + timedelta(days=start_day_offset)).replace(hour=start_hour)
            duration_hours = random.choice([1, 1.5, 2, 2.5, 3, 4])
            end = start + timedelta(hours=duration_hours)

            spot = _assign_spot(session, LOT_NAME, start, end)
            if spot is None:
                continue

            name = random_name()
            email = random_email(name)
            phone = random_phone()
            plate = random_plate()
            vtype = random.choice(vehicle_types)
            price = _compute_price_cents(start, end, vtype)
            code = _generate_code(plate, start)

            res = ParkingReservation(
                customer_name=name,
                email=email,
                phone=phone,
                vehicle_reg=plate,
                vehicle_type=vtype,
                lot_name=LOT_NAME,
                spot_number=spot,
                start_time=start,
                end_time=end,
                price_cents=price,
                confirmation_code=code,
                status="confirmed",
            )
            session.add(res)
            created += 1

        session.commit()

    return created


def seed_intake(count: int = 200) -> int:
    if not HAS_INTAKE:
        return 0
    # Ensure table exists
    SA_Base.metadata.create_all(sa_engine)

    from sqlalchemy.orm import Session as SASession
    import uuid

    issues = [
        "Issue with gate access",
        "Billing question",
        "General inquiry",
        "Update contact info",
        "Report lost ticket",
        "Request refund",
        "Feedback",
    ]

    created = 0
    with SASession(sa_engine) as db:
        for _ in range(count):
            name = random_name()
            email = random.choice([random_email(name), None])
            issue = random.choice(issues)
            call_sid = f"CA-{uuid.uuid4().hex[:24]}"
            item = Intake(
                call_sid=call_sid,
                from_number=random_phone(),
                name=name,
                email=email,
                issue_description=issue,
                step="done",
            )
            db.add(item)
            created += 1
        db.commit()
    return created


def main():
    parser = argparse.ArgumentParser(description="Seed parking and intake demo databases")
    parser.add_argument("--parking", type=int, default=500, help="Number of parking reservations to create")
    parser.add_argument("--intake", type=int, default=500, help="Number of intake demo records to create")
    parser.add_argument("--days", type=int, default=21, help="Distribute parking reservations across N future days")
    args = parser.parse_args()

    p = seed_parking(count=args.parking, days=args.days)
    i = seed_intake(count=args.intake)
    print(f"Seed complete: parking reservations created={p}, intake records created={i}")


if __name__ == "__main__":
    main()
