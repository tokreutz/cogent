import os
import asyncio
import argparse
import logfire
from Models.agent_deps import AgentDeps
from main_agent import create_main_agent
from .prompt import get_user_input, process_slash_commands


async def run_loop():
    parser = argparse.ArgumentParser(description="Interactive agent CLI")
    parser.parse_args()  # reserved for future flags

    logfire.configure()
    logfire.instrument_pydantic_ai()

    agent = create_main_agent()
    deps = AgentDeps(cwd=os.getcwd())
    history = []

    while True:
        try:
            user_text = await get_user_input()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        user_text = user_text.strip()
        if not user_text:
            continue
        if user_text.lower() == "exit":
            print("Goodbye!")
            break
        processed_text = process_slash_commands(user_text)
        try:
            result = await agent.run(processed_text, message_history=history, deps=deps)
            history = result.all_messages()
            print(result.output)
        except Exception as e:  # pragma: no cover - broad safety
            print(f"[error invoking model: {e}]")


def main():  # sync entry for setuptools/console-script compatibility
    asyncio.run(run_loop())
