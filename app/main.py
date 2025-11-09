import os
import re
from fastapi import FastAPI, Depends, Request, BackgroundTasks
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Intake
from .reservations import router as reservations_router
from .cartesia_agent import router as cartesia_router


app = FastAPI(title="Voice Intake + Parking Reservation Backend")

# Create tables at startup (simple demo; use migrations in prod)
Base.metadata.create_all(bind=engine)


def twiml_response(xml: str) -> Response:
    return Response(content=xml, media_type="text/xml")


def gather(prompt: str, action: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>{prompt}</Say>
  <Gather input="speech" action="{action}" method="POST" timeout="5">
    <Say>{prompt}</Say>
  </Gather>
  <Say>Sorry, I didn't get that.</Say>
  <Redirect method="POST">{action}</Redirect>
</Response>"""


@app.post("/twilio/voice")
async def twilio_voice(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    call_sid = form.get("CallSid")
    from_number = form.get("From")

    intake = db.query(Intake).filter_by(call_sid=call_sid).first()
    if not intake:
        intake = Intake(call_sid=call_sid, from_number=from_number, step="name")
        db.add(intake)
        db.commit()

    action = str(request.url_for("twilio_collect")) + "?step=name"
    prompt = "Hello, thanks for calling. May I have your full name?"
    return twiml_response(gather(prompt, action))


@app.post("/twilio/collect")
async def twilio_collect(request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    form = await request.form()
    call_sid = form.get("CallSid")
    speech_result = form.get("SpeechResult")
    speech = str(speech_result).strip() if speech_result else ""
    step = request.query_params.get("step", "name")

    intake = db.query(Intake).filter_by(call_sid=call_sid).first()
    if not intake:
        intake = Intake(call_sid=call_sid, step=step)
        db.add(intake)
        db.commit()

    if step == "name":
        if len(speech) < 2:
            prompt = "Sorry, I didn't catch that. Please say your full name."
            action = str(request.url_for("twilio_collect")) + "?step=name"
            return twiml_response(gather(prompt, action))

        intake.name = speech  # type: ignore
        intake.step = "email"  # type: ignore
        db.commit()

        prompt = "Thanks. Do you have an email we can use? You can say skip."
        action = str(request.url_for("twilio_collect")) + "?step=email"
        return twiml_response(gather(prompt, action))

    elif step == "email":
        if speech.lower() not in ["skip", "no", "nope", "none", "nah"]:
            if re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", speech):
                intake.email = speech  # type: ignore
            else:
                prompt = "That didn't sound like an email. Please say the email address, or say skip."
                action = str(request.url_for("twilio_collect")) + "?step=email"
                db.commit()
                return twiml_response(gather(prompt, action))

        intake.step = "issue"  # type: ignore
        db.commit()

        prompt = "Please briefly describe your issue after the tone."
        action = str(request.url_for("twilio_collect")) + "?step=issue"
        return twiml_response(gather(prompt, action))

    elif step == "issue":
        if len(speech) < 3:
            prompt = "Sorry, please describe your issue."
            action = str(request.url_for("twilio_collect")) + "?step=issue"
            return twiml_response(gather(prompt, action))

        intake.issue_description = speech  # type: ignore
        intake.step = "done"  # type: ignore
        db.commit()

        # Optionally POST to an external API if configured (no auth)
        post_url = os.getenv("EXTERNAL_POST_URL")
        if post_url:
            payload = {
                "call_sid": intake.call_sid,
                "from_number": intake.from_number,
                "name": intake.name,
                "email": intake.email,
                "issue_description": intake.issue_description,
            }
            background.add_task(_post_external, post_url, payload)

        say = "Thank you. We have saved your information. We will contact you shortly. Goodbye."
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>{say}</Say>
  <Hangup/>
</Response>"""
        return twiml_response(xml)

    # Fallback
    prompt = "Let's try again. May I have your full name?"
    action = str(request.url_for("twilio_collect")) + "?step=name"
    return twiml_response(gather(prompt, action))


@app.get("/records")
def list_records(db: Session = Depends(get_db)):
    rows = db.query(Intake).order_by(Intake.id.desc()).all()
    out = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "call_sid": r.call_sid,
                "from_number": r.from_number,
                "name": r.name,
                "email": r.email,
                "issue_description": r.issue_description,
                "created_at": r.created_at.isoformat() if r.created_at is not None else None,  # type: ignore
            }
        )
    return JSONResponse(out)


@app.get("/health")
def health():
    return {"ok": True}


# Helper to POST externally without blocking the call flow
async def _post_external(url: str, payload: dict):
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json=payload)
    except Exception:
        # Silent failure for demo; add logging in production
        pass
app.include_router(reservations_router)
app.include_router(cartesia_router)
