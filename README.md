Voice Intake + Parking Reservations (FastAPI)

Minimal FastAPI backend that:
- **Cartesia Sonet Voice Agent**: Automated voice agent that takes calls and creates parking reservations through natural conversation
- Answers Twilio calls, collects caller info via speech, and stores records in SQLite
- Exposes a Parking Reservation API (SQLModel + SQLite) with smart spot assignment, pricing, and email confirmations

## Quick Start

### Prerequisites
- Python 3.10+
- Cartesia account (get API key from https://play.cartesia.ai/)
- Twilio account (for phone number)
- SMTP credentials (optional, for email confirmations)

### Setup

1. **Clone and create virtual environment:**
   ```bash
   # Windows PowerShell
   python -m venv .venv
   .venv\Scripts\activate
   
   # Linux/macOS
   python -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Cartesia API key, Twilio credentials, etc.
   ```

4. **Run the server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

5. **Health check:**
   ```bash
   curl http://localhost:8000/health
   ```

## Cartesia Voice Agent Integration

### Setup Cartesia Agent

1. **Install Cartesia CLI:**
   ```bash
   pip install cartesia
   ```

2. **Create agent using Cartesia CLI:**
   ```bash
   cartesia agents create \
     --name "RapidPark Reservation Agent" \
     --webhook-url "https://YOUR_DOMAIN/cartesia/webhook" \
     --voice-id "a0e99841-438c-4a64-b679-ae501e7d6091" \
     --first-message "Hello! Welcome to RapidPark automated reservation system. I can help you reserve a parking spot. May I have your name please?"
   ```

3. **Configure Twilio to use Cartesia:**
   - In Twilio Console, set your phone number's voice webhook to Cartesia's webhook URL
   - Cartesia will handle the call and communicate with your `/cartesia/webhook` endpoint

### Voice Agent Endpoints

- **`POST /cartesia/webhook`** - Main webhook for Cartesia agent conversation flow
- **`GET /cartesia/sessions`** - View active conversation sessions (debug)
- **`DELETE /cartesia/sessions/{call_id}`** - Clear a specific session

### Conversation Flow

The voice agent guides callers through:
1. **Name collection**: "May I have your name please?"
2. **Vehicle info**: "Please tell me your vehicle registration number and type"
3. **Arrival time**: "When do you plan to arrive? You can say 'today at 3 PM'"
4. **Duration**: "How long do you need the parking spot?"
5. **Email (optional)**: "Would you like to provide an email for your confirmation ticket?"
6. **Quote & Confirmation**: Reviews details, provides price, confirms reservation
7. **Completion**: Provides confirmation code and spot assignment

### How It Works

```
Caller → Twilio → Cartesia Sonet → /cartesia/webhook → Parking API → Response → Cartesia → Twilio → Caller
```

1. Caller dials your Twilio number
2. Twilio forwards to Cartesia
3. Cartesia's AI handles speech recognition and natural conversation
4. Cartesia posts conversation turns to `/cartesia/webhook`
5. Your webhook processes the conversation state and calls parking APIs
6. Response sent back to Cartesia with next agent message
7. Cartesia speaks to the caller and continues conversation

## Parking Reservation API
- Create reservation (voice agent will POST here):
  - `POST /api/reservations`
  - JSON body:
    {
      "customer_name": "Jane Doe",
      "email": "jane@example.com",
      "phone": "+15551234567",
      "vehicle_reg": "ABC-1234",
      "vehicle_type": "car",                  // optional: car | motorcycle | truck
      "start_time": "2025-01-01T10:00:00",   // optional; defaults to now
      "end_time": "2025-01-01T13:30:00"       // OR provide "duration_hours": 3.5
    }
  - Response:
    {
      "id": 1,
      "confirmation_code": "RP-ABC1234-01011000",
      "lot_name": "RapidPark-A",
      "spot_number": 7,
      "spot_label": "A7",
      "start_time": "2025-01-01T10:00:00",
      "end_time": "2025-01-01T13:30:00",
      "price_cents": 1600
    }
  - List last reservations: `GET /api/reservations?limit=20`

- Parse arrival time (for voice agent):
  - `POST /api/parse-arrival`
  - Body: `{ "utterance": "today at 3 PM" }`
  - Response: `{ "start_time": "2025-01-01T15:00:00" }` (UTC naive)

- Parse duration (for voice agent):
  - `POST /api/parse-duration`
  - Body: `{ "utterance": "2 hours 30 minutes", "start_time": "2025-01-01T10:00:00" }`
  - Response: `{ "duration_minutes": 150, "duration_hours": 2.5, "end_time": "2025-01-01T12:30:00" }`

- Parse email (for voice agent):
  - `POST /api/parse-email`
  - Body: `{ "utterance": "john dot doe at gmail dot com" }`
  - Response: `{ "email": "john.doe@gmail.com", "valid": true }`

- Quote (summarize and price before confirm):
  - `POST /api/quote`
  - Body:
    {
      "vehicle_reg": "KA01AB1234",
      "vehicle_type": "car",              // optional
      "start_time": "2025-11-08T15:00:00", // or omit for now
      "duration_hours": 2.5                 // or duration_minutes / end_time
    }
  - Response:
    {
      "lot_name": "RapidPark-A",
      "vehicle_reg": "KA01AB1234",
      "vehicle_type": "car",
      "start_time": "2025-11-08T15:00:00",
      "end_time": "2025-11-08T17:30:00",
      "duration_minutes": 150,
      "duration_hours": 2.5,
      "price_cents": 1000,
      "available": true,
      "suggested_spot": 12,
      "suggested_label": "A12"
    }

Spot assignment and pricing
- Capacity: `LOT_CAPACITY` env (default 50). Assigns the lowest numbered spot not overlapping the requested time.
- Price: rounded up to next hour with minimum `MIN_CHARGE_MINUTES` (default 60).
  - Base: `RATE_CENTS_PER_HOUR` (default 400 = $4/h)
  - Per-type overrides: `RATE_CENTS_PER_HOUR_CAR`, `RATE_CENTS_PER_HOUR_MOTORCYCLE`, `RATE_CENTS_PER_HOUR_TRUCK`

Optional ticket e‑mail
- Set SMTP env to send the ticket in background when email is provided:
  - `SMTP_HOST`, `SMTP_PORT` (default 587), `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`

Environment variables
- `PARKING_DATABASE_URL` (default `sqlite:///./parking.db`)
- `LOT_NAME` (default `RapidPark-A`)
- `LOT_CAPACITY` (default `50`)
- `RATE_CENTS_PER_HOUR` (default `400`)
- `RATE_CENTS_PER_HOUR_CAR` (default `RATE_CENTS_PER_HOUR`)
- `RATE_CENTS_PER_HOUR_MOTORCYCLE` (default `300`)
- `RATE_CENTS_PER_HOUR_TRUCK` (default `600`)
- `MIN_CHARGE_MINUTES` (default `60`)
- SMTP variables as above
- `CARTESIA_API_KEY` - Your Cartesia API key
- `CARTESIA_AGENT_ID` - Your Cartesia agent ID
- `CARTESIA_VOICE_ID` - Voice ID (default: friendly woman)
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`

## Testing the Voice Agent

### Local Development with ngrok

1. **Start your FastAPI server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. **Expose locally with ngrok:**
   ```bash
   ngrok http 8000
   ```

3. **Use the ngrok HTTPS URL for Cartesia webhook:**
   ```
   https://YOUR_NGROK_ID.ngrok.io/cartesia/webhook
   ```

4. **Test the conversation:**
   - Call your Twilio number
   - Follow the voice prompts
   - Agent will guide you through the reservation process

### Manual API Testing

You can also test the parking API directly:

```bash
# Get a quote
curl -X POST http://localhost:8000/api/quote \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_reg": "KA01AB1234",
    "vehicle_type": "car",
    "start_time": "2025-11-08T15:00:00",
    "duration_hours": 2.5
  }'

# Create a reservation
curl -X POST http://localhost:8000/api/reservations \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "John Doe",
    "email": "john@example.com",
    "vehicle_reg": "ABC-1234",
    "vehicle_type": "car",
    "duration_hours": 2
  }'
```

Seeding (sample data)
- Seed both parking and intake demo tables:
  - `python scripts/seed_db.py`
- Output shows counts created. Parking DB uses `PARKING_DATABASE_URL` (default `sqlite:///./parking.db`).
- Voice intake demo DB uses `DATABASE_URL` (default `sqlite:///./voice_agent.db`).

Database
- Defaults to SQLite at `./voice_agent.db`.
- Override with env var: `DATABASE_URL=sqlite:///./voice_agent.db` (or any SQLAlchemy URL).

Twilio Configuration
1) Buy or use an existing Twilio phone number.
2) Set the Voice webhook (POST) to: `https://YOUR_DOMAIN/twilio/voice`
3) Twilio will send form-encoded parameters. No auth is required for this demo.

Call Flow
- `/twilio/voice` answers and asks for name using `<Gather input="speech">`.
- `/twilio/collect?step=name|email|issue` stores each response and advances steps.
- Once complete, it thanks the caller and hangs up; record is saved.

Notes
- This demo uses Twilio speech recognition. No external ASR/LLM is required.
- Add Twilio signature verification and authentication for production.
- Add migrations (e.g., Alembic) for production schema management.

## Architecture

```
┌─────────────┐
│   Caller    │
└──────┬──────┘
       │ (voice call)
       ▼
┌─────────────┐
│   Twilio    │
└──────┬──────┘
       │ (WebSocket/HTTP)
       ▼
┌──────────────────┐
│ Cartesia Sonet   │ ◄─── Natural language understanding
│   Voice Agent    │      Speech-to-text, Text-to-speech
└──────┬───────────┘
       │ (webhook HTTP POST)
       ▼
┌────────────────────────────────────────┐
│   Your FastAPI Backend                 │
│   /cartesia/webhook                    │
│   ├─ Conversation state management     │
│   ├─ Call parking APIs                 │
│   └─ Return next agent message         │
└──────┬─────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────┐
│   Parking Reservation APIs             │
│   /api/parse-arrival                   │
│   /api/parse-duration                  │
│   /api/parse-email                     │
│   /api/quote                           │
│   /api/reservations                    │
└────────────────────────────────────────┘
```

## Features

✅ **Natural Language Processing**: Understands "today at 3 PM", "2 hours 30 minutes", "john dot doe at gmail dot com"
✅ **Smart Spot Assignment**: Automatically finds available spots with no time overlap
✅ **Dynamic Pricing**: Different rates for cars, motorcycles, and trucks
✅ **Email Confirmations**: Sends ticket via SMTP with confirmation code
✅ **Conversation State Management**: Maintains context across multiple conversation turns
✅ **Quote Before Booking**: Provides price estimate before confirming reservation
✅ **Graceful Error Handling**: Handles parsing errors and guides users to retry

## Project Structure

```
Voice/
├── app/
│   ├── main.py              # Main FastAPI app with Twilio voice intake
│   ├── cartesia_agent.py    # NEW: Cartesia voice agent webhook handler
│   ├── reservations.py      # Parking reservation API endpoints
│   ├── models.py            # Database models for intake
│   └── db.py                # Database configuration
├── scripts/
│   └── seed_db.py           # Seed databases with test data
├── parking_app.py           # Standalone parking app (can be consolidated)
├── requirements.txt         # Python dependencies
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## Next Steps

1. **Deploy to production**: Use a service like Railway, Render, or AWS
2. **Add authentication**: Protect admin endpoints with API keys
3. **Add logging**: Use structlog or loguru for better observability
4. **Add tests**: Write pytest tests for conversation flows
5. **Consolidate code**: Merge `parking_app.py` into `app/reservations.py`
6. **Add payment processing**: Integrate Stripe for actual payments
7. **Add cancellation support**: Allow users to cancel reservations

## Support

For issues or questions:
- Cartesia Documentation: https://docs.cartesia.ai/
- Twilio Documentation: https://www.twilio.com/docs/voice

Voice Agent Script (Parking)
- Greeting: "Hello! Welcome to RapidPark. I’ll book a parking spot for you. May I have your vehicle registration number?"
- Vehicle registration → confirm back.
- Arrival time: "What date and time will you arrive? You can say 'now'."
- Duration: "How long do you need the spot for? Say hours and minutes, for example '2 hours 30 minutes'."
- Name: "May I have your full name for the booking?"
- Email: "What email should I send the parking ticket to? You can say 'skip'."
  - Alternative prompt: "Please provide an email address so we can send your ticket."
- Confirmation: Read back summary (plate, start/end, estimated price) and ask to confirm.
- On confirm: POST to `/api/reservations` with collected fields; then read back confirmation code (ticket id) and spot label.
 - On decline: Offer to adjust time/duration or cancel.
