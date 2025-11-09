# API Testing Examples

Test your parking reservation API with these examples.

## Using curl (Windows PowerShell)

### 1. Health Check
```powershell
curl http://localhost:8000/health
```

Expected response:
```json
{"ok": true}
```

---

### 2. Parse Arrival Time
```powershell
curl -X POST http://localhost:8000/api/parse-arrival `
  -H "Content-Type: application/json" `
  -d '{"utterance": "today at 3 PM"}'
```

Expected response:
```json
{"start_time": "2025-11-07T15:00:00"}
```

---

### 3. Parse Duration
```powershell
curl -X POST http://localhost:8000/api/parse-duration `
  -H "Content-Type: application/json" `
  -d '{"utterance": "2 hours 30 minutes", "start_time": "2025-11-07T15:00:00"}'
```

Expected response:
```json
{
  "duration_minutes": 150,
  "duration_hours": 2.5,
  "end_time": "2025-11-07T17:30:00"
}
```

---

### 4. Parse Email
```powershell
curl -X POST http://localhost:8000/api/parse-email `
  -H "Content-Type: application/json" `
  -d '{"utterance": "john dot doe at gmail dot com"}'
```

Expected response:
```json
{
  "email": "john.doe@gmail.com",
  "valid": true
}
```

---

### 5. Get Quote
```powershell
curl -X POST http://localhost:8000/api/quote `
  -H "Content-Type: application/json" `
  -d '{
    "vehicle_reg": "KA01AB1234",
    "vehicle_type": "car",
    "start_time": "2025-11-07T15:00:00",
    "duration_hours": 2.5
  }'
```

Expected response:
```json
{
  "lot_name": "RapidPark-A",
  "vehicle_reg": "KA01AB1234",
  "vehicle_type": "car",
  "start_time": "2025-11-07T15:00:00",
  "end_time": "2025-11-07T17:30:00",
  "duration_minutes": 150,
  "duration_hours": 2.5,
  "price_cents": 1200,
  "available": true,
  "suggested_spot": 1,
  "suggested_label": "A1"
}
```

---

### 6. Create Reservation
```powershell
curl -X POST http://localhost:8000/api/reservations `
  -H "Content-Type: application/json" `
  -d '{
    "customer_name": "John Doe",
    "email": "john@example.com",
    "phone": "+15551234567",
    "vehicle_reg": "KA01AB1234",
    "vehicle_type": "car",
    "start_time": "2025-11-07T15:00:00",
    "duration_hours": 2.5
  }'
```

Expected response:
```json
{
  "id": 1,
  "confirmation_code": "RP-KA01AB1234-11071500",
  "lot_name": "RapidPark-A",
  "spot_number": 1,
  "spot_label": "A1",
  "vehicle_type": "car",
  "start_time": "2025-11-07T15:00:00",
  "end_time": "2025-11-07T17:30:00",
  "price_cents": 1200
}
```

---

### 7. List Reservations
```powershell
curl http://localhost:8000/api/reservations?limit=10
```

Expected response:
```json
[
  {
    "id": 1,
    "confirmation_code": "RP-KA01AB1234-11071500",
    "lot_name": "RapidPark-A",
    "spot_number": 1,
    "spot_label": "A1",
    "vehicle_type": "car",
    "start_time": "2025-11-07T15:00:00",
    "end_time": "2025-11-07T17:30:00",
    "price_cents": 1200
  }
]
```

---

### 8. View Cartesia Sessions (Debug)
```powershell
curl http://localhost:8000/cartesia/sessions
```

Expected response:
```json
{
  "active_sessions": 0,
  "sessions": {}
}
```

---

## Using Python requests

```python
import requests

BASE_URL = "http://localhost:8000"

# Health check
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# Parse arrival
response = requests.post(
    f"{BASE_URL}/api/parse-arrival",
    json={"utterance": "today at 3 PM"}
)
print(response.json())

# Get quote
response = requests.post(
    f"{BASE_URL}/api/quote",
    json={
        "vehicle_reg": "ABC123",
        "vehicle_type": "car",
        "start_time": "2025-11-07T15:00:00",
        "duration_hours": 2
    }
)
print(response.json())

# Create reservation
response = requests.post(
    f"{BASE_URL}/api/reservations",
    json={
        "customer_name": "Jane Doe",
        "email": "jane@example.com",
        "vehicle_reg": "ABC123",
        "vehicle_type": "car",
        "start_time": "2025-11-07T15:00:00",
        "duration_hours": 2
    }
)
print(response.json())
```

---

## Using the Interactive API Docs

1. Start your server: `uvicorn app.main:app --reload`
2. Open browser: http://localhost:8000/docs
3. Click on any endpoint to expand it
4. Click "Try it out"
5. Fill in the parameters
6. Click "Execute"
7. View the response

---

## Testing Voice Agent Webhook (Advanced)

### Simulate Cartesia Webhook Call

```powershell
curl -X POST http://localhost:8000/cartesia/webhook `
  -H "Content-Type: application/json" `
  -d '{
    "call_id": "test-call-123",
    "event_type": "message",
    "user_message": "John Doe"
  }'
```

---

## Common Test Scenarios

### Scenario 1: Full Reservation Flow
1. Parse arrival: "today at 3 PM"
2. Parse duration: "2 hours"
3. Parse email: "john dot doe at gmail dot com"
4. Get quote with all info
5. Create reservation
6. Verify in list

### Scenario 2: Different Vehicle Types
Test pricing for different vehicle types:
- Car: 400 cents/hour
- Motorcycle: 300 cents/hour
- Truck: 600 cents/hour

```powershell
# Motorcycle reservation
curl -X POST http://localhost:8000/api/quote `
  -H "Content-Type: application/json" `
  -d '{
    "vehicle_reg": "BIKE123",
    "vehicle_type": "motorcycle",
    "duration_hours": 2
  }'
```

### Scenario 3: Spot Availability
Create multiple overlapping reservations to test spot assignment:

```powershell
# First reservation
curl -X POST http://localhost:8000/api/reservations `
  -H "Content-Type: application/json" `
  -d '{
    "customer_name": "User 1",
    "vehicle_reg": "CAR001",
    "start_time": "2025-11-07T15:00:00",
    "duration_hours": 2
  }'

# Second reservation (same time, should get different spot)
curl -X POST http://localhost:8000/api/reservations `
  -H "Content-Type: application/json" `
  -d '{
    "customer_name": "User 2",
    "vehicle_reg": "CAR002",
    "start_time": "2025-11-07T15:00:00",
    "duration_hours": 2
  }'
```

---

## Error Testing

### Invalid Email
```powershell
curl -X POST http://localhost:8000/api/parse-email `
  -H "Content-Type: application/json" `
  -d '{"utterance": "not an email"}'
```

Expected: 400 error

### End Before Start
```powershell
curl -X POST http://localhost:8000/api/quote `
  -H "Content-Type: application/json" `
  -d '{
    "vehicle_reg": "ABC123",
    "start_time": "2025-11-07T18:00:00",
    "end_time": "2025-11-07T15:00:00"
  }'
```

Expected: 400 error "end_time must be after start_time"

---

## Performance Testing

### Load Test (requires apache bench)
```bash
ab -n 100 -c 10 http://localhost:8000/health
```

---

## Tips

1. Use the interactive docs at `/docs` for easier testing
2. Check server logs in the terminal for debugging
3. Use `/cartesia/sessions` to debug conversation state
4. Clear sessions with `DELETE /cartesia/sessions/{call_id}`
5. Seed test data: `python scripts/seed_db.py`

---

**Note**: Replace `localhost:8000` with your actual server URL if deployed.
