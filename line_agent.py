"""
Cartesia Line SDK Voice Agent for Parking Reservations
This uses Cartesia's Line SDK for proper integration
"""
from cartesia import Cartesia
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Cartesia client
client = Cartesia(api_key=os.getenv("CARTESIA_API_KEY"))

async def handle_call(call):
    """Main call handler using Cartesia Line SDK"""
    
    # Greet the user
    await call.say("Hello! Welcome to RapidPark. May I have your full name please?")
    
    # Collect name
    name_response = await call.listen()
    customer_name = name_response.transcript
    
    # Collect vehicle info
    await call.say(f"Thank you, {customer_name}. Please tell me your vehicle registration number and type.")
    vehicle_response = await call.listen()
    
    # Collect arrival time
    await call.say("When do you plan to arrive? You can say something like 'today at 3 PM'.")
    arrival_response = await call.listen()
    
    # Collect duration
    await call.say("How long will you need parking? For example, '2 hours' or '3 days'.")
    duration_response = await call.listen()
    
    # Collect email
    await call.say("What's your email address for the confirmation?")
    email_response = await call.listen()
    
    # Final confirmation
    await call.say(f"Perfect! I'm processing your reservation for {customer_name}. You'll receive a confirmation shortly at {email_response.transcript}. Thank you for choosing RapidPark!")
    
    await call.hangup()

# Export for Cartesia
agent = {
    "name": "RapidPark Reservation Agent",
    "voice": os.getenv("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091"),
    "on_call": handle_call
}
