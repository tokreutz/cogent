import os
import asyncio
import argparse
import logfire
from cli.prompt import _get_state  # internal access for model switch state
from models.agent_deps import AgentDeps
from models.session_recorder import SessionRecorder
from main_agent import create_main_agent
from .prompt import get_user_input, process_slash_commands


async def run_loop():
    parser = argparse.ArgumentParser(description="Interactive agent CLI")
    parser.parse_args()  # reserved for future flags

    logfire.configure()
    logfire.instrument_pydantic_ai()

    agent = create_main_agent()
    # Initialize prompt state model display if persistence or env selected a model
    state = _get_state()
    if getattr(agent, 'model', None) is not None:
        model_obj = agent.model
        prov = getattr(model_obj, '_cogent_provider_name', None)
        mod = getattr(model_obj, '_cogent_model_name', None)
        if prov and not state.selected_provider:
            state.selected_provider = prov
        if mod and not state.selected_model:
            state.selected_model = mod
    deps = AgentDeps(cwd=os.getcwd())
    history = []
    recorder = SessionRecorder(os.getcwd())

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
        state = _get_state()
        if state.model_switch_requested:
            # Recreate agent with new selection and reset history
            agent = create_main_agent(provider_name=state.selected_provider, model_name=state.selected_model)
            history = []
            state.model_switch_requested = False
            continue  # no user message this loop
        try:
            result = await agent.run(processed_text, message_history=history, deps=deps)
            history = result.all_messages()
            if history:
                # Persist the evolving transcript for this session
                recorder.record(history)
            print(result.output)
        except Exception as e:  # pragma: no cover - broad safety
            print(f"[error invoking model: {e}]")


def main():  # sync entry for setuptools/console-script compatibility
    asyncio.run(run_loop())
