from __future__ import annotations

import math
import os
import re
import smtplib
import uuid
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Optional, List

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from sqlmodel import SQLModel, Field, create_engine, Session, select


# -------------------- Config --------------------
DB_URL = os.getenv("PARKING_DATABASE_URL", "sqlite:///./parking.db")
LOT_NAME = os.getenv("LOT_NAME", "RapidPark-A")
LOT_CAPACITY = int(os.getenv("LOT_CAPACITY", "50"))

# Pricing (cents per hour)
RATE_CENTS_PER_HOUR = int(os.getenv("RATE_CENTS_PER_HOUR", "400"))  # base $4/h
RATE_CENTS_PER_HOUR_CAR = int(os.getenv("RATE_CENTS_PER_HOUR_CAR", str(RATE_CENTS_PER_HOUR)))
RATE_CENTS_PER_HOUR_MOTORCYCLE = int(os.getenv("RATE_CENTS_PER_HOUR_MOTORCYCLE", "300"))
RATE_CENTS_PER_HOUR_TRUCK = int(os.getenv("RATE_CENTS_PER_HOUR_TRUCK", "600"))
MIN_CHARGE_MINUTES = int(os.getenv("MIN_CHARGE_MINUTES", "60"))

# SMTP (optional)
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "tickets@rapidpark.local")


# -------------------- Models --------------------
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


class ReserveIn(SQLModel):
    customer_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    vehicle_reg: str
    vehicle_type: Optional[str] = None  # car|motorcycle|truck
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_hours: Optional[float] = None
    duration_minutes: Optional[int] = None


class ReserveOut(SQLModel):
    id: int
    ticket_id: str
    confirmation_code: str
    lot_name: str
    spot_number: int
    spot_label: str
    vehicle_type: Optional[str]
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    duration_hours: float
    price_cents: int
    price_display: str


class QuoteIn(SQLModel):
    vehicle_reg: str
    vehicle_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
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
    price_display: str
    available: bool
    suggested_spot: Optional[int]
    suggested_label: Optional[str]


engine = create_engine(DB_URL, echo=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


app = FastAPI(title="RapidPark Voice Reservation API")


# -------------------- Helpers --------------------
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
    return hours * _rate_for_vehicle_type(vehicle_type)


def _price_display(cents: int) -> str:
    return f"${cents/100:.2f}"


def _generate_code(vehicle_reg: str, when: datetime) -> str:
    return f"RP-{vehicle_reg.replace(' ', '').upper()}-{when.strftime('%m%d%H%M')}"


def _spot_label(lot_name: str, spot_number: Optional[int]) -> Optional[str]:
    if not spot_number:
        return None
    zone = None
    if "-" in lot_name:
        tail = lot_name.split("-")[-1].strip()
        zone = tail[:1].upper() if tail else None
    if not zone and lot_name:
        zone = lot_name[:1].upper()
    return f"{zone}{spot_number}" if zone else str(spot_number)


def _assign_spot(session: Session, lot_name: str, start: datetime, end: datetime) -> Optional[int]:
    stmt = select(Reservation.spot_number, Reservation.start_time, Reservation.end_time).where(
        (Reservation.lot_name == lot_name)
        & (Reservation.status == "confirmed")
        & (Reservation.spot_number.is_not(None))
    )
    rows = session.exec(stmt).all()
    taken_by_spot: dict[int, list[tuple[datetime, datetime]]] = {}
    for spot, s, e in rows:
        taken_by_spot.setdefault(spot, []).append((s, e))

    for spot in range(1, LOT_CAPACITY + 1):
        intervals = taken_by_spot.get(spot, [])
        if all(not _overlaps(start, end, s, e) for s, e in intervals):
            return spot
    return None


def _is_valid_email(email: str) -> bool:
    return bool(email and re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))


def _send_ticket_email(res: Reservation) -> None:
    if not (SMTP_HOST and SMTP_FROM and res.email):
        return
    body = (
        f"Hello {res.customer_name},\n\n"
        f"Your RapidPark reservation is confirmed.\n"
        f"Confirmation: {res.confirmation_code}\n"
        f"Lot: {res.lot_name}\n"
        f"Spot: {_spot_label(res.lot_name, res.spot_number) or res.spot_number}\n"
        f"Vehicle: {res.vehicle_reg}\n"
        f"Start: {res.start_time}\n"
        f"End: {res.end_time}\n"
        f"Price: {_price_display(res.price_cents)}\n\n"
        f"Show this email upon arrival.\n"
        f"Thank you for choosing RapidPark!\n"
    )

    msg = EmailMessage()
    msg["Subject"] = f"Your RapidPark Ticket {res.confirmation_code}"
    msg["From"] = SMTP_FROM
    msg["To"] = res.email
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as s:
            s.starttls()
            if SMTP_USER and SMTP_PASS:
                s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
    except Exception:
        # Silent for demo; add logging in production
        pass


# -------------------- API --------------------
@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/reservations", response_model=List[ReserveOut])
def list_reservations(limit: int = Query(50, ge=1, le=200)):
    with Session(engine) as session:
        stmt = select(Reservation).order_by(Reservation.id.desc()).limit(limit)
        items = session.exec(stmt).all()
        out: List[ReserveOut] = []
        for r in items:
            mins = int((r.end_time - r.start_time).total_seconds() // 60)
            out.append(
                ReserveOut(
                    id=r.id,
                    ticket_id=r.confirmation_code,
                    confirmation_code=r.confirmation_code,
                    lot_name=r.lot_name,
                    spot_number=r.spot_number or 0,
                    spot_label=_spot_label(r.lot_name, r.spot_number) or str(r.spot_number or ""),
                    vehicle_type=r.vehicle_type,
                    start_time=r.start_time,
                    end_time=r.end_time,
                    duration_minutes=mins,
                    duration_hours=round(mins / 60.0, 2),
                    price_cents=r.price_cents,
                    price_display=_price_display(r.price_cents),
                )
            )
        return out


@app.post("/quote", response_model=QuoteOut)
def quote(data: QuoteIn):
    if not data.vehicle_reg:
        raise HTTPException(status_code=400, detail="vehicle_reg is required")
    if data.vehicle_type and data.vehicle_type.lower() not in {"car", "motorcycle", "truck"}:
        raise HTTPException(status_code=400, detail="vehicle_type must be one of: car, motorcycle, truck")

    start = data.start_time or datetime.utcnow()
    end: Optional[datetime] = None
    if data.end_time:
        end = data.end_time
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
            price_display=_price_display(price),
            available=available,
            suggested_spot=spot,
            suggested_label=_spot_label(LOT_NAME, spot),
        )


@app.post("/reserve", response_model=ReserveOut)
def reserve(data: ReserveIn, background: BackgroundTasks):
    if not data.vehicle_reg or not data.customer_name:
        raise HTTPException(status_code=400, detail="customer_name and vehicle_reg are required")
    if data.vehicle_type and data.vehicle_type.lower() not in {"car", "motorcycle", "truck"}:
        raise HTTPException(status_code=400, detail="vehicle_type must be one of: car, motorcycle, truck")
    if data.email and not _is_valid_email(data.email):
        raise HTTPException(status_code=400, detail="invalid email format")

    start = data.start_time or datetime.utcnow()
    end: Optional[datetime] = None
    if data.end_time:
        end = data.end_time
    elif data.duration_hours is not None:
        end = start + timedelta(hours=float(data.duration_hours))
    elif data.duration_minutes is not None:
        end = start + timedelta(minutes=int(data.duration_minutes))
    else:
        raise HTTPException(status_code=400, detail="Provide end_time, duration_hours, or duration_minutes")

    if end <= start:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

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
            vehicle_type=(data.vehicle_type or None),
            lot_name=LOT_NAME,
            spot_number=spot,
            start_time=start,
            end_time=end,
            price_cents=price,
            confirmation_code=code,
            status="confirmed",
        )
        session.add(res)
        session.commit()
        session.refresh(res)

        # Send ticket email asynchronously (if configured and email provided)
        if res.email:
            background.add_task(_send_ticket_email, res)

        mins = int((res.end_time - res.start_time).total_seconds() // 60)
        return ReserveOut(
            id=res.id,
            ticket_id=res.confirmation_code,
            confirmation_code=res.confirmation_code,
            lot_name=res.lot_name,
            spot_number=res.spot_number or 0,
            spot_label=_spot_label(res.lot_name, res.spot_number) or str(res.spot_number or ""),
            vehicle_type=res.vehicle_type,
            start_time=res.start_time,
            end_time=res.end_time,
            duration_minutes=mins,
            duration_hours=round(mins / 60.0, 2),
            price_cents=res.price_cents,
            price_display=_price_display(res.price_cents),
        )

