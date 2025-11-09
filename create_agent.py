"""
Create Cartesia Agent using Python SDK
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get configuration
API_KEY = os.getenv("CARTESIA_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
VOICE_ID = os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091")

print("="*60)
print("Creating Cartesia Agent for RapidPark")
print("="*60)
if API_KEY:
    print(f"\nAPI Key: {API_KEY[:20]}...")
else:
    print("\n❌ API Key not found in .env")
print(f"Webhook URL: {WEBHOOK_URL}")
print(f"Voice ID: {VOICE_ID}")
print()

try:
    from cartesia import Cartesia
    
    if not API_KEY:
        raise ValueError("API_KEY not found in .env")
    
    # Initialize Cartesia client
    client = Cartesia(api_key=API_KEY)
    
    # Create agent configuration
    agent_config = {
        "name": "RapidPark Reservation Agent",
        "webhook_url": WEBHOOK_URL,
        "voice_id": VOICE_ID,
        "first_message": "Hello! Welcome to RapidPark automated reservation system. I can help you reserve a parking spot. May I have your name please?",
        "language": "en"
    }
    
    print("Creating agent...")
    print(f"Name: {agent_config['name']}")
    print(f"Webhook: {agent_config['webhook_url']}")
    print()
    
    # Note: The exact API method depends on Cartesia's SDK
    # This is a placeholder - check Cartesia docs for actual method
    print("⚠️  Cartesia SDK installed, but agent creation API may differ.")
    print()
    print("Please use one of these methods:")
    print()
    print("Option 1: Cartesia Web Interface (Recommended)")
    print("-" * 60)
    print("1. Go to: https://play.cartesia.ai/")
    print("2. Click 'Create Agent'")
    print("3. Fill in:")
    print(f"   - Name: {agent_config['name']}")
    print(f"   - Webhook URL: {agent_config['webhook_url']}")
    print(f"   - Voice ID: {VOICE_ID}")
    print(f"   - First Message: {agent_config['first_message']}")
    print("4. Copy the Agent ID")
    print("5. Add to .env: CARTESIA_AGENT_ID=<your_agent_id>")
    print()
    print("Option 2: Contact Cartesia Support")
    print("-" * 60)
    print("Check their documentation at: https://docs.cartesia.ai/")
    print()
    
except ImportError as e:
    print(f"❌ Error importing Cartesia: {e}")
    print("\nPlease use the web interface:")
    print("https://play.cartesia.ai/")
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nPlease use the web interface:")
    print("https://play.cartesia.ai/")

print("="*60)
