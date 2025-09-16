import os
import asyncio
import argparse
import re

from Models.agent_deps import AgentDeps
from main_agent import create_main_agent

import logfire

def process_slash_commands(user_text):
    """
    Process slash commands by replacing them with content from markdown files.
    
    Only processes slash commands that appear at the start of the prompt
    (after trimming whitespace). Adds two newlines after inserted command content.
    """
    # Look for slash commands like /research, /plan
    pattern = r'/([a-zA-Z0-9_]+)'
    
    # Only process slash commands if they appear at the start of the prompt
    trimmed_text = user_text.strip()
    if not trimmed_text.startswith('/'):
        return user_text
    
    # Find the first slash command at the start
    match = re.search(pattern, trimmed_text)
    if not match:
        return user_text
    
    command = match.group(1)
    
    # Check for markdown files in .cogent/commands directory
    commands_dir = os.path.join(os.getcwd(), '.cogent', 'commands')
    
    if not os.path.exists(commands_dir):
        return user_text
    
    # Replace only the first occurrence of the slash command with content followed by 2 newlines
    md_file_path = os.path.join(commands_dir, f"{command}.md")
    if os.path.exists(md_file_path):
        try:
            with open(md_file_path, 'r') as f:
                content = f.read()
                # Replace only the first occurrence with markdown content followed by 2 newlines
                return re.sub(f'/{command}', content + "\n\n", user_text, count=1)
        except Exception:
            # If we can't read the file, keep original text
            pass
    
    return user_text

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
        
        # Process slash commands before sending to agent
        processed_text = process_slash_commands(user_text)
        
        try:
            result = await agent.run(processed_text, message_history=history, deps=deps)
            history = result.all_messages()
            out = result.output
            print(out)
        except Exception as e:
            print(f"[error invoking model: {e}]")

if __name__ == "__main__":
    asyncio.run(main())