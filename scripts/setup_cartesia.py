"""
Cartesia Agent Setup Script
Run this to create and configure your Cartesia voice agent for parking reservations
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Your public URL + /cartesia/webhook
VOICE_ID = os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091")

AGENT_CONFIG = {
    "name": "RapidPark Reservation Agent",
    "description": "Automated voice agent for parking spot reservations",
    "first_message": "Hello! Welcome to RapidPark automated reservation system. I can help you reserve a parking spot. May I have your name please?",
    "voice_id": VOICE_ID,
    "webhook_url": WEBHOOK_URL,
    "language": "en",
    "context": {
        "role": "parking_reservation_agent",
        "instructions": [
            "You are a friendly and professional parking reservation agent for RapidPark.",
            "Your goal is to collect: customer name, vehicle registration, vehicle type, arrival time, duration, and optionally email.",
            "Be conversational and natural. If you don't understand something, politely ask the customer to repeat.",
            "Always confirm details before finalizing the reservation.",
            "Speak clearly when providing the confirmation code and spot assignment."
        ]
    }
}


def main():
    print("=" * 60)
    print("Cartesia Voice Agent Setup for RapidPark")
    print("=" * 60)
    print()
    
    if not CARTESIA_API_KEY:
        print("❌ Error: CARTESIA_API_KEY not found in .env file")
        print("Please add your Cartesia API key to .env:")
        print("  CARTESIA_API_KEY=your_api_key_here")
        print()
        print("Get your API key from: https://play.cartesia.ai/")
        sys.exit(1)
    
    if not WEBHOOK_URL:
        print("❌ Error: WEBHOOK_URL not found in .env file")
        print("Please add your public webhook URL to .env:")
        print("  WEBHOOK_URL=https://your-domain.com/cartesia/webhook")
        print()
        print("For local development, use ngrok:")
        print("  1. Run: ngrok http 8000")
        print("  2. Copy the HTTPS URL (e.g., https://abc123.ngrok.io)")
        print("  3. Add to .env: WEBHOOK_URL=https://abc123.ngrok.io/cartesia/webhook")
        sys.exit(1)
    
    print("Configuration:")
    print(f"  Agent Name: {AGENT_CONFIG['name']}")
    print(f"  Webhook URL: {WEBHOOK_URL}")
    print(f"  Voice ID: {VOICE_ID}")
    print()
    
    print("To create your agent, run the following command:")
    print()
    print("cartesia agents create \\")
    print(f'  --name "{AGENT_CONFIG["name"]}" \\')
    print(f'  --webhook-url "{WEBHOOK_URL}" \\')
    print(f'  --voice-id "{VOICE_ID}" \\')
    print(f'  --first-message "{AGENT_CONFIG["first_message"]}"')
    print()
    print("Or use the Cartesia web interface at: https://play.cartesia.ai/")
    print()
    print("After creating the agent:")
    print("1. Copy the AGENT_ID from the response")
    print("2. Add to .env: CARTESIA_AGENT_ID=your_agent_id")
    print("3. Configure your Twilio number to use the Cartesia phone number")
    print()
    print("=" * 60)
    print()
    
    print("Available Voice Options:")
    print("  - Friendly Woman (default): a0e99841-438c-4a64-b679-ae501e7d6091")
    print("  - Professional Man: 694f9389-aac1-45b6-b726-9d9369183238")
    print("  - Calm Woman: 79a125e8-cd45-4c13-8a67-188112f4dd22")
    print()
    print("To use a different voice, update CARTESIA_VOICE_ID in .env")
    print()


if __name__ == "__main__":
    main()
