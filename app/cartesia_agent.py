"""
Cartesia Sonet Voice Agent for Parking Reservations
This module handles the Cartesia agent webhook and manages conversation state
"""
from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
import httpx


router = APIRouter(prefix="/cartesia", tags=["voice-agent"])


class ConversationState(str, Enum):
    """Stages of the parking reservation conversation"""
    GREETING = "greeting"
    COLLECT_NAME = "collect_name"
    COLLECT_VEHICLE = "collect_vehicle"
    COLLECT_ARRIVAL = "collect_arrival"
    COLLECT_DURATION = "collect_duration"
    COLLECT_EMAIL = "collect_email"
    PROVIDE_QUOTE = "provide_quote"
    CONFIRM_RESERVATION = "confirm_reservation"
    COMPLETED = "completed"


class AgentContext(BaseModel):
    """Maintains state across conversation turns"""
    state: ConversationState = ConversationState.GREETING
    customer_name: Optional[str] = None
    vehicle_reg: Optional[str] = None
    vehicle_type: Optional[str] = None
    arrival_time: Optional[str] = None
    duration_hours: Optional[float] = None
    email: Optional[str] = None
    quote: Optional[Dict[str, Any]] = None
    reservation: Optional[Dict[str, Any]] = None


class CartesiaWebhookRequest(BaseModel):
    """Incoming webhook payload from Cartesia"""
    call_id: str
    event_type: str
    user_message: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class CartesiaWebhookResponse(BaseModel):
    """Response to Cartesia with agent instructions"""
    message: str
    context: Dict[str, Any]
    actions: Optional[List[Dict[str, Any]]] = None
    end_call: bool = False


# In-memory session storage (use Redis/DB for production)
sessions: Dict[str, AgentContext] = {}


def get_session(call_id: str) -> AgentContext:
    """Retrieve or create session for this call"""
    if call_id not in sessions:
        sessions[call_id] = AgentContext()
    return sessions[call_id]


def save_session(call_id: str, context: AgentContext):
    """Save session state"""
    sessions[call_id] = context


async def call_parking_api(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    """Helper to call internal parking API endpoints"""
    base_url = os.getenv("PARKING_API_BASE_URL", "http://localhost:8000")
    url = f"{base_url}{endpoint}"
    
    async with httpx.AsyncClient() as client:
        if method == "POST":
            response = await client.post(url, json=data)
        else:
            response = await client.get(url)
        
        response.raise_for_status()
        return response.json()


def extract_vehicle_info(text: str) -> tuple[Optional[str], Optional[str]]:
    """Extract vehicle registration and type from user speech"""
    text_lower = text.lower()
    
    # Detect vehicle type
    vehicle_type = None
    if "motorcycle" in text_lower or "bike" in text_lower or "motorbike" in text_lower:
        vehicle_type = "motorcycle"
    elif "truck" in text_lower or "van" in text_lower:
        vehicle_type = "truck"
    elif "car" in text_lower or "sedan" in text_lower or "suv" in text_lower:
        vehicle_type = "car"
    
    # Extract registration (simple pattern - enhance as needed)
    # Looking for patterns like "KA01AB1234", "ABC-1234", etc.
    import re
    reg_pattern = r'\b[A-Z]{2}\d{2}[A-Z]{2}\d{4}\b|\b[A-Z]{3}-?\d{4}\b'
    match = re.search(reg_pattern, text.upper())
    vehicle_reg = match.group(0) if match else None
    
    return vehicle_reg, vehicle_type


async def handle_conversation(call_id: str, user_message: str, context: AgentContext) -> CartesiaWebhookResponse:
    """Main conversation flow handler"""
    
    # GREETING
    if context.state == ConversationState.GREETING:
        context.state = ConversationState.COLLECT_NAME
        save_session(call_id, context)
        return CartesiaWebhookResponse(
            message="Hello! Welcome to RapidPark automated reservation system. I can help you reserve a parking spot. May I have your name please?",
            context=context.dict()
        )
    
    # COLLECT NAME
    elif context.state == ConversationState.COLLECT_NAME:
        if user_message and len(user_message.strip()) > 2:
            context.customer_name = user_message.strip()
            context.state = ConversationState.COLLECT_VEHICLE
            save_session(call_id, context)
            return CartesiaWebhookResponse(
                message=f"Thank you, {context.customer_name}. Please tell me your vehicle registration number and type. For example, you can say 'KA01AB1234, car' or 'ABC-1234, motorcycle'.",
                context=context.dict()
            )
        else:
            return CartesiaWebhookResponse(
                message="I didn't catch that. Could you please tell me your full name?",
                context=context.dict()
            )
    
    # COLLECT VEHICLE
    elif context.state == ConversationState.COLLECT_VEHICLE:
        vehicle_reg, vehicle_type = extract_vehicle_info(user_message)
        
        if vehicle_reg:
            context.vehicle_reg = vehicle_reg
            context.vehicle_type = vehicle_type or "car"
            context.state = ConversationState.COLLECT_ARRIVAL
            save_session(call_id, context)
            return CartesiaWebhookResponse(
                message=f"Got it, {context.vehicle_type} with registration {context.vehicle_reg}. When do you plan to arrive? You can say something like 'today at 3 PM' or 'tomorrow at 10 AM'.",
                context=context.dict()
            )
        else:
            return CartesiaWebhookResponse(
                message="I couldn't understand the vehicle registration. Please say your vehicle registration number clearly, like 'KA 01 AB 1234'.",
                context=context.dict()
            )
    
    # COLLECT ARRIVAL
    elif context.state == ConversationState.COLLECT_ARRIVAL:
        try:
            # Call parse-arrival API
            result = await call_parking_api(
                "/api/parse-arrival",
                "POST",
                {"utterance": user_message}
            )
            context.arrival_time = result.get("start_time")
            context.state = ConversationState.COLLECT_DURATION
            save_session(call_id, context)
            
            # Format time nicely
            if context.arrival_time:
                arrival_dt = datetime.fromisoformat(context.arrival_time)
                formatted_time = arrival_dt.strftime("%B %d at %I:%M %p")
            else:
                formatted_time = "the requested time"
            
            return CartesiaWebhookResponse(
                message=f"Perfect, arriving on {formatted_time}. How long do you need the parking spot? For example, '2 hours' or '3 hours 30 minutes'.",
                context=context.dict()
            )
        except Exception as e:
            return CartesiaWebhookResponse(
                message="I couldn't understand that time. Please try again, like 'today at 3 PM' or 'tomorrow at 10 AM'.",
                context=context.dict()
            )
    
    # COLLECT DURATION
    elif context.state == ConversationState.COLLECT_DURATION:
        try:
            # Call parse-duration API
            result = await call_parking_api(
                "/api/parse-duration",
                "POST",
                {"utterance": user_message, "start_time": context.arrival_time}
            )
            context.duration_hours = result.get("duration_hours")
            
            # Get quote
            quote = await call_parking_api(
                "/api/quote",
                "POST",
                {
                    "vehicle_reg": context.vehicle_reg,
                    "vehicle_type": context.vehicle_type,
                    "start_time": context.arrival_time,
                    "duration_hours": context.duration_hours
                }
            )
            context.quote = quote
            context.state = ConversationState.COLLECT_EMAIL
            save_session(call_id, context)
            
            price_display = f"${quote['price_cents']/100:.2f}"
            duration_text = f"{context.duration_hours} hours"
            
            return CartesiaWebhookResponse(
                message=f"Great! For {duration_text} of parking, the price will be {price_display}. "
                        f"We have spot {quote.get('suggested_label', 'available')} in {quote['lot_name']}. "
                        f"Would you like to provide an email address for your confirmation ticket? You can say your email or say 'skip'.",
                context=context.dict()
            )
        except Exception as e:
            return CartesiaWebhookResponse(
                message="I couldn't understand the duration. Please say how long you need parking, like '2 hours' or '90 minutes'.",
                context=context.dict()
            )
    
    # COLLECT EMAIL
    elif context.state == ConversationState.COLLECT_EMAIL:
        user_lower = user_message.lower()
        
        # Check if user wants to skip
        if any(word in user_lower for word in ["skip", "no email", "no thanks", "none"]):
            context.email = None
        else:
            try:
                # Call parse-email API
                result = await call_parking_api(
                    "/api/parse-email",
                    "POST",
                    {"utterance": user_message}
                )
                context.email = result.get("email")
            except:
                return CartesiaWebhookResponse(
                    message="I couldn't understand that email. Please say it clearly, like 'john dot doe at gmail dot com', or say 'skip'.",
                    context=context.dict()
                )
        
        context.state = ConversationState.CONFIRM_RESERVATION
        save_session(call_id, context)
        
        # Confirm details
        quote = context.quote
        if not quote:
            return CartesiaWebhookResponse(
                message="I'm sorry, there was an error getting your quote. Let's start over.",
                context=context.dict(),
                end_call=True
            )
        
        price = f"${quote['price_cents']/100:.2f}"
        if context.arrival_time:
            arrival_dt = datetime.fromisoformat(context.arrival_time)
            arrival_str = arrival_dt.strftime("%B %d at %I:%M %p")
        else:
            arrival_str = "the requested time"
        
        confirmation_msg = (
            f"Let me confirm your reservation. "
            f"Name: {context.customer_name}. "
            f"Vehicle: {context.vehicle_type}, registration {context.vehicle_reg}. "
            f"Arriving: {arrival_str}. "
            f"Duration: {context.duration_hours} hours. "
            f"Price: {price}. "
        )
        
        if context.email:
            confirmation_msg += f"Email: {context.email}. "
        
        confirmation_msg += "Should I confirm this reservation? Say 'yes' to confirm or 'no' to cancel."
        
        return CartesiaWebhookResponse(
            message=confirmation_msg,
            context=context.dict()
        )
    
    # CONFIRM RESERVATION
    elif context.state == ConversationState.CONFIRM_RESERVATION:
        user_lower = user_message.lower()
        
        if any(word in user_lower for word in ["yes", "confirm", "correct", "proceed", "book"]):
            try:
                # Create reservation
                reservation = await call_parking_api(
                    "/api/reservations",
                    "POST",
                    {
                        "customer_name": context.customer_name,
                        "email": context.email,
                        "vehicle_reg": context.vehicle_reg,
                        "vehicle_type": context.vehicle_type,
                        "start_time": context.arrival_time,
                        "duration_hours": context.duration_hours
                    }
                )
                context.reservation = reservation
                context.state = ConversationState.COMPLETED
                save_session(call_id, context)
                
                conf_code = reservation['confirmation_code']
                spot_label = reservation['spot_label']
                lot_name = reservation['lot_name']
                
                final_msg = (
                    f"Perfect! Your reservation is confirmed. "
                    f"Your confirmation code is {conf_code}. "
                    f"Your spot is {spot_label} in {lot_name}. "
                )
                
                if context.email:
                    final_msg += f"A confirmation email has been sent to {context.email}. "
                
                final_msg += "Thank you for choosing RapidPark. Have a great day!"
                
                return CartesiaWebhookResponse(
                    message=final_msg,
                    context=context.dict(),
                    end_call=True
                )
            except Exception as e:
                return CartesiaWebhookResponse(
                    message=f"I'm sorry, there was an error creating your reservation: {str(e)}. Please try again later or call our customer service.",
                    context=context.dict(),
                    end_call=True
                )
        else:
            # User cancelled
            context.state = ConversationState.COMPLETED
            save_session(call_id, context)
            return CartesiaWebhookResponse(
                message="No problem, I've cancelled this reservation. If you'd like to try again, please call back. Goodbye!",
                context=context.dict(),
                end_call=True
            )
    
    # Default fallback
    return CartesiaWebhookResponse(
        message="I'm sorry, I didn't understand that. Could you please repeat?",
        context=context.dict()
    )


@router.post("/webhook")
async def cartesia_webhook(request: Request):
    """
    Webhook endpoint for Cartesia voice agent
    Receives events from Cartesia and responds with conversation instructions
    """
    try:
        payload = await request.json()
        call_id = payload.get("call_id")
        event_type = payload.get("event_type", "message")
        user_message = payload.get("user_message", "")
        
        if not call_id:
            raise HTTPException(status_code=400, detail="call_id is required")
        
        # Get or create session
        context = get_session(call_id)
        
        # Handle different event types
        if event_type == "call_started":
            # Initialize conversation
            response = CartesiaWebhookResponse(
                message="Hello! Welcome to RapidPark automated reservation system. I can help you reserve a parking spot. May I have your name please?",
                context=context.dict()
            )
        elif event_type == "call_ended":
            # Clean up session
            if call_id in sessions:
                del sessions[call_id]
            return {"status": "ok"}
        else:
            # Regular conversation turn
            response = await handle_conversation(call_id, user_message, context)
        
        return response.dict()
        
    except Exception as e:
        print(f"Error in webhook: {e}")
        return {
            "message": "I'm sorry, I encountered an error. Please try again or contact customer service.",
            "context": {},
            "end_call": True
        }


@router.get("/sessions")
async def list_sessions():
    """Debug endpoint to view active sessions"""
    return {
        "active_sessions": len(sessions),
        "sessions": {k: v.dict() for k, v in sessions.items()}
    }


@router.delete("/sessions/{call_id}")
async def clear_session(call_id: str):
    """Clear a specific session"""
    if call_id in sessions:
        del sessions[call_id]
        return {"status": "cleared"}
    return {"status": "not_found"}


@router.post("/voice-call")
async def handle_twilio_call(request: Request):
    """
    Twilio webhook endpoint to connect incoming calls to Cartesia agent
    Configure this URL in Twilio: https://your-domain.com/cartesia/voice-call
    """
    # Get Cartesia agent ID from environment
    agent_id = os.getenv("CARTESIA_AGENT_ID")
    if not agent_id or agent_id == "your_agent_id_here":
        raise HTTPException(status_code=500, detail="CARTESIA_AGENT_ID not configured")
    
    # Get form data from Twilio
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    from_number = form_data.get("From", "")
    
    # Create TwiML response to connect to Cartesia
    # Cartesia provides a SIP endpoint or you can use their SDK
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Connecting you to our parking reservation system...</Say>
    <Dial>
        <Sip>sip:{agent_id}@cartesia.ai</Sip>
    </Dial>
</Response>"""
    
    return Response(content=twiml, media_type="application/xml")

