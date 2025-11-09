# Quick Start Guide - Cartesia Voice Agent Setup

## Step 1: Install Dependencies

```powershell
# Activate virtual environment (if not already active)
.venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment

```powershell
# Copy environment template
copy .env.example .env

# Edit .env and add your credentials:
# - CARTESIA_API_KEY (get from https://play.cartesia.ai/)
# - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
# - SMTP credentials (optional, for email confirmations)
```

## Step 3: Start the Server

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Step 4: Expose Locally (for testing)

In a new terminal:

```powershell
# Install ngrok if you haven't: https://ngrok.com/download
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`) and add to .env:
```
WEBHOOK_URL=https://abc123.ngrok.io/cartesia/webhook
```

## Step 5: Create Cartesia Agent

### Option A: Using Cartesia CLI

```powershell
# Run the setup helper script
python scripts/setup_cartesia.py
```

This will show you the exact command to run. Example:

```bash
cartesia agents create \
  --name "RapidPark Reservation Agent" \
  --webhook-url "https://abc123.ngrok.io/cartesia/webhook" \
  --voice-id "a0e99841-438c-4a64-b679-ae501e7d6091" \
  --first-message "Hello! Welcome to RapidPark automated reservation system. I can help you reserve a parking spot. May I have your name please?"
```

### Option B: Using Cartesia Web Interface

1. Go to https://play.cartesia.ai/
2. Create a new agent
3. Set the webhook URL to: `https://your-ngrok-url.ngrok.io/cartesia/webhook`
4. Choose a voice (e.g., Friendly Woman)
5. Set first message: "Hello! Welcome to RapidPark..."
6. Copy the Agent ID and add to .env: `CARTESIA_AGENT_ID=your_agent_id`

## Step 6: Connect Twilio

1. Log in to Twilio Console: https://console.twilio.com/
2. Go to Phone Numbers → Manage → Active Numbers
3. Select your phone number
4. Under "Voice & Fax", set:
   - **A call comes in**: Webhook
   - **URL**: Use Cartesia's phone number or webhook URL (check Cartesia docs)
   - **HTTP Method**: POST
5. Save

## Step 7: Test the Voice Agent

Call your Twilio phone number and follow the conversation:

1. **Agent**: "Hello! Welcome to RapidPark... May I have your name please?"
   - **You**: "John Doe"

2. **Agent**: "Thank you, John Doe. Please tell me your vehicle registration number and type."
   - **You**: "KA 01 AB 1234, car"

3. **Agent**: "Got it, car with registration KA01AB1234. When do you plan to arrive?"
   - **You**: "Today at 3 PM"

4. **Agent**: "Perfect, arriving on [date] at 03:00 PM. How long do you need the parking spot?"
   - **You**: "2 hours"

5. **Agent**: "Great! For 2.0 hours of parking, the price will be $8.00..."
   - **You**: "john.doe@gmail.com" (or "skip")

6. **Agent**: "Let me confirm your reservation... Should I confirm?"
   - **You**: "Yes"

7. **Agent**: "Perfect! Your reservation is confirmed. Your confirmation code is RP-KA01AB1234-11071500. Your spot is A7 in RapidPark-A..."

## Step 8: Monitor & Debug

### View API Documentation
Open browser: http://localhost:8000/docs

### Check Active Sessions
```bash
curl http://localhost:8000/cartesia/sessions
```

### View Reservations
```bash
curl http://localhost:8000/api/reservations?limit=10
```

### Check Logs
Watch the terminal running `uvicorn` for real-time logs

## Troubleshooting

### Issue: Webhook not receiving calls
- Verify ngrok is running and URL is correct
- Check WEBHOOK_URL in .env matches ngrok URL
- Restart the FastAPI server after changing .env

### Issue: Agent not understanding speech
- Speak clearly and slowly
- Check Cartesia agent configuration
- Review logs at http://localhost:8000/cartesia/sessions

### Issue: Reservation fails
- Check parking database exists: `ls parking.db`
- Verify LOT_CAPACITY in .env
- Check if spots are available for requested time

### Issue: Email not sending
- Verify SMTP credentials in .env
- Check SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
- For Gmail, use an App Password (not regular password)

## Production Deployment

For production, deploy to a service like:
- **Railway**: https://railway.app/
- **Render**: https://render.com/
- **AWS EC2/ECS**
- **Google Cloud Run**

Don't forget to:
1. Set environment variables in production
2. Use a production database (PostgreSQL)
3. Enable HTTPS
4. Add authentication to admin endpoints
5. Set up logging and monitoring
6. Remove `--reload` flag from uvicorn

## Seeding Test Data

To populate the database with test reservations:

```powershell
python scripts/seed_db.py --parking 100 --intake 50 --days 7
```

This creates 100 parking reservations and 50 intake records spread across 7 days.

## Next Steps

- Test the full conversation flow
- Customize the agent's voice and responses
- Add authentication for production
- Set up proper logging
- Deploy to production environment
- Monitor usage and optimize

Happy parking! 🚗🅿️
