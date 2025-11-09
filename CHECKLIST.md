# Cartesia Voice Agent - Setup Checklist

Use this checklist to ensure everything is configured correctly.

## ✅ Installation & Setup

- [ ] Python 3.10+ installed
- [ ] Virtual environment created: `python -m venv .venv`
- [ ] Virtual environment activated: `.venv\Scripts\activate`
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] .env file created from .env.example: `copy .env.example .env`

## ✅ Configuration

### Required Environment Variables
- [ ] `CARTESIA_API_KEY` - From https://play.cartesia.ai/
- [ ] `TWILIO_ACCOUNT_SID` - From Twilio Console
- [ ] `TWILIO_AUTH_TOKEN` - From Twilio Console  
- [ ] `TWILIO_PHONE_NUMBER` - Your Twilio phone number

### Optional (Recommended)
- [ ] `SMTP_HOST` - For email confirmations
- [ ] `SMTP_USER` - Your email
- [ ] `SMTP_PASS` - App password (not regular password)
- [ ] `SMTP_FROM` - Sender email address
- [ ] `CARTESIA_VOICE_ID` - Custom voice (default is fine)

### Parking Configuration (Defaults are OK)
- [ ] `LOT_NAME` - Default: RapidPark-A
- [ ] `LOT_CAPACITY` - Default: 50
- [ ] `RATE_CENTS_PER_HOUR` - Default: 400 ($4/hour)

## ✅ Server Setup

- [ ] Server starts successfully: `uvicorn app.main:app --reload`
- [ ] Health endpoint works: http://localhost:8000/health
- [ ] API docs accessible: http://localhost:8000/docs
- [ ] No import errors in console

## ✅ ngrok Setup (for local testing)

- [ ] ngrok installed: https://ngrok.com/download
- [ ] ngrok running: `ngrok http 8000`
- [ ] HTTPS URL copied (e.g., https://abc123.ngrok.io)
- [ ] `WEBHOOK_URL` added to .env: `WEBHOOK_URL=https://abc123.ngrok.io/cartesia/webhook`

## ✅ Cartesia Agent Setup

- [ ] Cartesia account created: https://play.cartesia.ai/
- [ ] API key obtained and added to .env
- [ ] Setup helper run: `python scripts/setup_cartesia.py`
- [ ] Agent created (via CLI or web interface)
- [ ] Agent ID added to .env: `CARTESIA_AGENT_ID=your_agent_id`
- [ ] Webhook URL configured in agent: `https://your-ngrok.ngrok.io/cartesia/webhook`

## ✅ Twilio Setup

- [ ] Twilio phone number configured
- [ ] Voice webhook set to Cartesia (follow Cartesia docs for integration)
- [ ] Account SID and Auth Token in .env

## ✅ Testing

### API Endpoints
- [ ] Test health: `GET http://localhost:8000/health`
- [ ] Test reservations list: `GET http://localhost:8000/api/reservations`
- [ ] Test parse-arrival: `POST http://localhost:8000/api/parse-arrival` with `{"utterance": "today at 3 PM"}`
- [ ] Test parse-duration: `POST http://localhost:8000/api/parse-duration` with `{"utterance": "2 hours"}`
- [ ] Test quote: `POST http://localhost:8000/api/quote` with vehicle data

### Voice Agent
- [ ] Call Twilio number
- [ ] Agent answers and greets
- [ ] Agent understands your name
- [ ] Agent understands vehicle registration
- [ ] Agent understands arrival time
- [ ] Agent understands duration
- [ ] Agent can parse email (or accept skip)
- [ ] Agent provides quote
- [ ] Agent confirms reservation
- [ ] Agent provides confirmation code and spot number
- [ ] Email received (if SMTP configured)

## ✅ Database

- [ ] Database files created automatically on first run
- [ ] `parking.db` exists
- [ ] `voice_agent.db` exists
- [ ] Can view reservations: `GET http://localhost:8000/api/reservations`

## ✅ Optional Enhancements

- [ ] Seed test data: `python scripts/seed_db.py --parking 100`
- [ ] Review active sessions: `GET http://localhost:8000/cartesia/sessions`
- [ ] Test email sending (provide valid email during call)

## 🚨 Troubleshooting

If you encounter issues, check:

### Server won't start
- [ ] Virtual environment activated?
- [ ] All dependencies installed?
- [ ] .env file exists?
- [ ] No port conflicts (8000 already in use)?

### Webhook not receiving calls
- [ ] ngrok running?
- [ ] WEBHOOK_URL in .env matches ngrok URL?
- [ ] Server restarted after changing .env?
- [ ] Cartesia agent webhook URL configured correctly?

### Agent not understanding speech
- [ ] Speaking clearly?
- [ ] Check Cartesia agent logs
- [ ] Review `/cartesia/sessions` for conversation state
- [ ] Verify Cartesia API key is valid

### Reservations failing
- [ ] Database exists and is writable?
- [ ] LOT_CAPACITY not exceeded for requested time?
- [ ] Start time before end time?
- [ ] Valid vehicle registration format?

### Email not sending
- [ ] SMTP credentials correct in .env?
- [ ] Using App Password for Gmail (not regular password)?
- [ ] SMTP_HOST and SMTP_PORT correct?
- [ ] Email address valid format?

## 📚 Resources

- **Documentation**: README.md, QUICKSTART.md, IMPLEMENTATION_SUMMARY.md
- **API Docs**: http://localhost:8000/docs (when server is running)
- **Cartesia**: https://docs.cartesia.ai/
- **Twilio**: https://www.twilio.com/docs/voice
- **FastAPI**: https://fastapi.tiangolo.com/

## ✅ Production Readiness

Before deploying to production:

- [ ] Use PostgreSQL instead of SQLite
- [ ] Add authentication to admin endpoints
- [ ] Set up proper logging (structlog/loguru)
- [ ] Add monitoring (Sentry, DataDog)
- [ ] Enable rate limiting
- [ ] Add Twilio signature verification
- [ ] Use secrets management (not .env file)
- [ ] Set up CI/CD pipeline
- [ ] Add automated tests
- [ ] Enable HTTPS only
- [ ] Review and fix all security considerations

## 🎉 Success Criteria

You're ready when:

- ✅ Server starts without errors
- ✅ Can call Twilio number and hear agent greeting
- ✅ Agent successfully completes full conversation
- ✅ Reservation appears in database
- ✅ Confirmation code provided
- ✅ Email received (if configured)

---

**Last Updated**: November 7, 2025
**Status**: Ready for testing
