from __future__ import annotations

import math
import re
import os
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Optional, List

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from sqlmodel import SQLModel, Field, create_engine, Session, select, desc
from dateutil import parser as date_parser


# --- Config ---
DB_URL = os.getenv("PARKING_DATABASE_URL", "sqlite:///./parking.db")
LOT_NAME = os.getenv("LOT_NAME", "RapidPark-A")
LOT_CAPACITY = int(os.getenv("LOT_CAPACITY", "50"))
RATE_CENTS_PER_HOUR = int(os.getenv("RATE_CENTS_PER_HOUR", "400"))  # $4/hour (base)
# Optional per-vehicle-type overrides
RATE_CENTS_PER_HOUR_CAR = int(os.getenv("RATE_CENTS_PER_HOUR_CAR", str(RATE_CENTS_PER_HOUR)))
RATE_CENTS_PER_HOUR_MOTORCYCLE = int(os.getenv("RATE_CENTS_PER_HOUR_MOTORCYCLE", "300"))
RATE_CENTS_PER_HOUR_TRUCK = int(os.getenv("RATE_CENTS_PER_HOUR_TRUCK", "600"))
MIN_CHARGE_MINUTES = int(os.getenv("MIN_CHARGE_MINUTES", "60"))


# --- Models ---
class Reservation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    customer_name: str = Field(index=True)
    email: Optional[str] = Field(default=None, index=True)
    phone: Optional[str] = None
    vehicle_reg: str = Field(index=True)
    vehicle_type: Optional[str] = Field(default=None, index=True, description="car|motorcycle|truck")

    lot_name: str = Field(default=LOT_NAME, index=True)
    spot_number: Optional[int] = Field(default=None, index=True)

    start_time: datetime
    end_time: datetime

    price_cents: int
    confirmation_code: str = Field(index=True)
    status: str = Field(default="confirmed", index=True)


class ReservationCreate(SQLModel):
    customer_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    vehicle_reg: str
    vehicle_type: Optional[str] = None  # car|motorcycle|truck
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_hours: Optional[float] = None  # alternative to end_time


class ReservationOut(SQLModel):
    id: int
    confirmation_code: str
    lot_name: str
    spot_number: int
    spot_label: str
    vehicle_type: Optional[str]
    start_time: datetime
    end_time: datetime
    price_cents: int


class EmailParseIn(SQLModel):
    utterance: str


class ArrivalParseIn(SQLModel):
    utterance: str


class DurationParseIn(SQLModel):
    utterance: str
    start_time: Optional[str] = None


class QuoteIn(SQLModel):
    vehicle_reg: str
    vehicle_type: Optional[str] = None  # car|motorcycle|truck
    start_time: Optional[str] = None    # ISO; defaults to now
    end_time: Optional[str] = None      # ISO; or provide one of duration fields
    duration_hours: Optional[float] = None
    duration_minutes: Optional[int] = None


class QuoteOut(SQLModel):
    lot_name: str
    vehicle_reg: str
    vehicle_type: Optional[str]
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    duration_hours: float
    price_cents: int
    available: bool
    suggested_spot: Optional[int]
    suggested_label: Optional[str]


engine = create_engine(DB_URL, echo=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


router = APIRouter(prefix="/api", tags=["parking"])


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return not (a_end <= b_start or b_end <= a_start)


def _rate_for_vehicle_type(vehicle_type: Optional[str]) -> int:
    vt = (vehicle_type or "").strip().lower()
    if vt == "car":
        return RATE_CENTS_PER_HOUR_CAR
    if vt == "motorcycle":
        return RATE_CENTS_PER_HOUR_MOTORCYCLE
    if vt == "truck":
        return RATE_CENTS_PER_HOUR_TRUCK
    return RATE_CENTS_PER_HOUR


def _compute_price_cents(start: datetime, end: datetime, vehicle_type: Optional[str]) -> int:
    total_minutes = max(0, int((end - start).total_seconds() // 60))
    billable_minutes = max(total_minutes, MIN_CHARGE_MINUTES)
    hours = math.ceil(billable_minutes / 60)
    rate = _rate_for_vehicle_type(vehicle_type)
    return hours * rate


def _generate_code(vehicle_reg: str, when: datetime) -> str:
    return f"RP-{vehicle_reg.replace(' ', '').upper()}-{when.strftime('%m%d%H%M')}"


def _spot_label(lot_name: str, spot_number: Optional[int]) -> Optional[str]:
    if not spot_number:
        return None
    zone = None
    if "-" in lot_name:
        # Use first letter after last hyphen, e.g., RapidPark-A -> A
        tail = lot_name.split("-")[-1].strip()
        zone = tail[:1].upper() if tail else None
    if not zone and lot_name:
        zone = lot_name[:1].upper()
    return f"{zone}{spot_number}" if zone else str(spot_number)


def _assign_spot(session: Session, lot_name: str, start: datetime, end: datetime) -> Optional[int]:
    stmt = select(Reservation.spot_number, Reservation.start_time, Reservation.end_time).where(
        (Reservation.lot_name == lot_name)
        & (Reservation.status == "confirmed")
        & (Reservation.spot_number != None)  # type: ignore
    )
    rows = session.exec(stmt).all()
    taken_by_spot = {}
    for spot, s, e in rows:
        taken_by_spot.setdefault(spot, []).append((s, e))

    # Try each spot from 1..capacity for availability (no overlap)
    for spot in range(1, LOT_CAPACITY + 1):
        intervals = taken_by_spot.get(spot, [])
        if all(not _overlaps(start, end, s, e) for s, e in intervals):
            return spot
    return None


@router.post("/reservations", response_model=ReservationOut)
def create_reservation(
    data: ReservationCreate,
    background: BackgroundTasks,
):
    create_db_and_tables()
    if not data.vehicle_reg or not data.customer_name:
        raise HTTPException(status_code=400, detail="customer_name and vehicle_reg are required")

    # Determine start/end
    start = data.start_time or datetime.utcnow()
    if data.end_time is None and data.duration_hours is None:
        raise HTTPException(status_code=400, detail="Provide end_time or duration_hours")
    end = data.end_time or (start + timedelta(hours=float(data.duration_hours or 0)))
    if end <= start:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    # Validate vehicle_type if provided
    if data.vehicle_type and data.vehicle_type.lower() not in {"car", "motorcycle", "truck"}:
        raise HTTPException(status_code=400, detail="vehicle_type must be one of: car, motorcycle, truck")

    if data.email and not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", data.email):
        raise HTTPException(status_code=400, detail="invalid email format")

    price = _compute_price_cents(start, end, data.vehicle_type)
    code = _generate_code(data.vehicle_reg, start)

    with Session(engine) as session:
        spot = _assign_spot(session, LOT_NAME, start, end)
        if spot is None:
            raise HTTPException(status_code=409, detail="No spots available for the requested time range")

        res = Reservation(
            customer_name=data.customer_name,
            email=data.email,
            phone=data.phone,
            vehicle_reg=data.vehicle_reg,
            lot_name=LOT_NAME,
            spot_number=spot,
            start_time=start,
            end_time=end,
            price_cents=price,
            vehicle_type=(data.vehicle_type or None),
            confirmation_code=code,
            status="confirmed",
        )
        session.add(res)
        session.commit()
        session.refresh(res)

        # Email in background if SMTP configured and email provided
        if data.email:
            background.add_task(_send_ticket_email, res)

        return ReservationOut(
            id=res.id or 0,  # type: ignore
            confirmation_code=res.confirmation_code,
            lot_name=res.lot_name,
            spot_number=res.spot_number or 0,
            spot_label=_spot_label(res.lot_name, res.spot_number) or str(res.spot_number or ""),
            vehicle_type=res.vehicle_type,
            start_time=res.start_time,
            end_time=res.end_time,
            price_cents=res.price_cents,
        )


@router.get("/reservations", response_model=List[ReservationOut])
def list_reservations(
    limit: int = Query(50, ge=1, le=200),
):
    create_db_and_tables()
    with Session(engine) as session:
        stmt = select(Reservation).order_by(desc(Reservation.id)).limit(limit)  # type: ignore
        items = session.exec(stmt).all()
        return [
            ReservationOut(
                id=r.id or 0,  # type: ignore
                confirmation_code=r.confirmation_code,
                lot_name=r.lot_name,
                spot_number=r.spot_number or 0,
                spot_label=_spot_label(r.lot_name, r.spot_number) or str(r.spot_number or ""),
                vehicle_type=r.vehicle_type,
                start_time=r.start_time,
                end_time=r.end_time,
                price_cents=r.price_cents,
            )
            for r in items
        ]


@router.post("/parse-arrival")
def parse_arrival(payload: ArrivalParseIn):
    """Parse natural language arrival time like 'today at 3 PM' into ISO datetime (UTC naive)."""
    text = (payload.utterance or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="utterance is required")

    now = datetime.utcnow()
    lowered = text.lower()
    # quick replacements for relative days
    if "today" in lowered:
        text = lowered.replace("today", now.strftime("%Y-%m-%d"))
    elif "tomorrow" in lowered:
        tomorrow = now + timedelta(days=1)
        text = lowered.replace("tomorrow", tomorrow.strftime("%Y-%m-%d"))

    # Remove filler words
    text = text.replace(" at ", " ")

    try:
        dt = date_parser.parse(text, default=now)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not parse arrival time")

    # If parsed time is in the past by > 5 minutes, assume next day
    if dt < now - timedelta(minutes=5):
        dt = dt + timedelta(days=1)

    return {"start_time": dt.replace(microsecond=0).isoformat()}


def _send_ticket_email(res: Reservation):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    sender = os.getenv("SMTP_FROM", user or "tickets@rapidpark.local")

    if not host or not sender or not res.email:
        return  # No SMTP configured; silently skip

    body = (
        f"Hello {res.customer_name},\n\n"
        f"Your RapidPark reservation is confirmed.\n"
        f"Confirmation: {res.confirmation_code}\n"
        f"Lot: {res.lot_name}\n"
        f"Spot: {res.spot_number}\n"
        f"Vehicle: {res.vehicle_reg}\n"
        f"Start: {res.start_time}\n"
        f"End: {res.end_time}\n"
        f"Price: ${res.price_cents/100:.2f}\n\n"
        f"Show this email upon arrival.\n"
        f"Thank you for choosing RapidPark!\n"
    )

    msg = EmailMessage()
    msg["Subject"] = f"Your RapidPark Ticket {res.confirmation_code}"
    msg["From"] = sender
    msg["To"] = res.email
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=10) as s:
            s.starttls()
            if user and password:
                s.login(user, password)
            s.send_message(msg)
    except Exception:
        # For demo, ignore errors; in prod, log or retry
        pass


def _is_valid_email(email: str) -> bool:
    return bool(email and re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))


def _normalize_email_from_speech(utterance: str) -> Optional[str]:
    if not utterance:
        return None
    text = utterance.strip().lower()

    # Remove common prefaces
    text = re.sub(r"\b(my|the|our)?\s*(email|mail|address|id)\s*(is|:)\s*", "", text)

    # Normalize common domain phrases
    text = re.sub(r"\bdot\s+com\b", ".com", text)
    text = re.sub(r"\bdot\s+org\b", ".org", text)
    text = re.sub(r"\bdot\s+net\b", ".net", text)

    token_map = {
        "at": "@",
        "dot": ".",
        "period": ".",
        "underscore": "_",
        "under_score": "_",
        "dash": "-",
        "hyphen": "-",
        "minus": "-",
        "plus": "+",
        "space": "",
        "spaces": "",
    }

    parts = []
    for raw in re.split(r"\s+", text):
        t = raw.strip().strip(",;.!?")
        mapped = token_map.get(t)
        parts.append(mapped if mapped is not None else t)

    candidate = "".join(parts)
    candidate = re.sub(r"\.+", ".", candidate)
    candidate = re.sub(r"@+", "@", candidate)
    candidate = candidate.rstrip('.')

    if candidate.count("@") != 1:
        return None
    return candidate if _is_valid_email(candidate) else None


@router.post("/parse-email")
def parse_email(payload: EmailParseIn):
    email = _normalize_email_from_speech(payload.utterance or "")
    if not email:
        raise HTTPException(status_code=400, detail="Could not parse email")
    return {"email": email, "valid": True}


@router.post("/quote", response_model=QuoteOut)
def quote(data: QuoteIn):
    create_db_and_tables()

    if not data.vehicle_reg:
        raise HTTPException(status_code=400, detail="vehicle_reg is required")
    if data.vehicle_type and data.vehicle_type.lower() not in {"car", "motorcycle", "truck"}:
        raise HTTPException(status_code=400, detail="vehicle_type must be one of: car, motorcycle, truck")

    now = datetime.utcnow()
    # Resolve start time
    if data.start_time:
        try:
            start = date_parser.isoparse(data.start_time)
        except Exception:
            raise HTTPException(status_code=400, detail="start_time must be ISO-8601")
    else:
        start = now

    # Resolve end time via precedence: explicit end_time > duration_hours > duration_minutes
    end: Optional[datetime] = None
    if data.end_time:
        try:
            end = date_parser.isoparse(data.end_time)
        except Exception:
            raise HTTPException(status_code=400, detail="end_time must be ISO-8601")
    elif data.duration_hours is not None:
        end = start + timedelta(hours=float(data.duration_hours))
    elif data.duration_minutes is not None:
        end = start + timedelta(minutes=int(data.duration_minutes))
    else:
        raise HTTPException(status_code=400, detail="Provide end_time, duration_hours, or duration_minutes")

    if end <= start:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    mins = int((end - start).total_seconds() // 60)
    price = _compute_price_cents(start, end, data.vehicle_type)

    with Session(engine) as session:
        spot = _assign_spot(session, LOT_NAME, start, end)
        available = spot is not None
        return QuoteOut(
            lot_name=LOT_NAME,
            vehicle_reg=data.vehicle_reg,
            vehicle_type=(data.vehicle_type or None),
            start_time=start,
            end_time=end,
            duration_minutes=mins,
            duration_hours=round(mins / 60.0, 2),
            price_cents=price,
            available=available,
            suggested_spot=spot,
            suggested_label=_spot_label(LOT_NAME, spot),
        )


def _parse_duration_minutes(utterance: str) -> Optional[int]:
    """Parse natural language duration like '2 hours 30 minutes', '2.5h', '90 min'.
    Returns total minutes or None if not parseable.
    """
    if not utterance:
        return None
    text = utterance.lower().strip()

    # Normalize common separators
    text = text.replace("hours and", "hours")
    text = text.replace("hour and", "hour")

    hours = 0.0
    minutes = 0

    # Decimal hours e.g., 1.5h or 1.5 hours
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours|hour|hrs|hr|h)\b", text)
    if m:
        hours = float(m.group(1))

    # Whole minutes e.g., 30m, 45 minutes
    m2 = re.search(r"(\d+)\s*(?:minutes|minute|mins|min|m)\b", text)
    if m2:
        minutes = int(m2.group(1))

    # If neither matched, try a single number with 'for X hours' style
    if hours == 0 and minutes == 0:
        m3 = re.search(r"for\s+(\d+)\s*(?:hours|hour|hrs|hr|h)\b", text)
        if m3:
            hours = float(m3.group(1))
        else:
            m4 = re.search(r"for\s+(\d+)\s*(?:minutes|minute|mins|min|m)\b", text)
            if m4:
                minutes = int(m4.group(1))

    total_minutes = int(round(hours * 60)) + minutes
    return total_minutes if total_minutes > 0 else None


@router.post("/parse-duration")
def parse_duration(payload: DurationParseIn):
    """Parse phrases like '2 hours 30 minutes' to duration and end_time.
    If start_time is provided (ISO), returns end_time as well.
    """
    mins = _parse_duration_minutes(payload.utterance)
    if mins is None:
        raise HTTPException(status_code=400, detail="Could not parse duration")

    hours = round(mins / 60.0, 2)
    result = {"duration_minutes": mins, "duration_hours": hours}

    if payload.start_time:
        try:
            start = date_parser.isoparse(payload.start_time)
        except Exception:
            raise HTTPException(status_code=400, detail="start_time must be ISO-8601")
        end = start + timedelta(minutes=mins)
        result["end_time"] = end.replace(microsecond=0).isoformat()

    return result
