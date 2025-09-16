import os
import asyncio
import argparse

from Models.agent_deps import AgentDeps
from main_agent import create_main_agent

import logfire

async def main():

    parser = argparse.ArgumentParser(description="Interactive agent CLI")
    args = parser.parse_args()

    logfire.configure()  
    logfire.instrument_pydantic_ai()  

    agent = create_main_agent()
    deps = AgentDeps(cwd=os.getcwd())
    
    history = []

    while True:
        try:
            user_text = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        user_text = user_text.strip()
        if not user_text:
            continue
        if user_text.lower() == "exit":
            print("Goodbye!")
            break
        try:
            result = await agent.run(user_text, message_history=history, deps=deps)
            history = result.all_messages()
            out = result.output
            print(out)
        except Exception as e:
            print(f"[error invoking model: {e}]")

if __name__ == "__main__":
    asyncio.run(main())