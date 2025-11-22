"""
Voice agent for RapidPark parking reservations
"""

import asyncio
import os
from cartesia import AsyncCartesia
from line import Agent, AgentConfig, Context
from config import DEFAULT_MODEL_ID, DEFAULT_TEMPERATURE, SYSTEM_PROMPT

async def handle_new_call(system: Agent, ctx: Context):
    """Handle a new incoming call"""
    await system.start()
    await system.send_initial_message(
        "Hello! Welcome to RapidPark automated parking reservations. May I have your full name please?"
    )
    await system.wait_for_shutdown()

async def main():
    """Main entry point"""
    agent = Agent(
        config=AgentConfig(
            model_id=DEFAULT_MODEL_ID,
            temperature=DEFAULT_TEMPERATURE,
            system_prompt=SYSTEM_PROMPT,
        ),
        on_new_call=handle_new_call,
    )
    
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
