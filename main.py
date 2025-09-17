"""Legacy entrypoint re-exporting CLI helpers.

This module now delegates to `cli` package. Tests rely on the symbols
`init_prompt_session`, `get_user_input`, and `_reset_prompt_for_tests`,
which are re-exported for backward compatibility.
"""

from cli.prompt import (
    init_prompt_session,
    get_user_input,
    _reset_prompt_for_tests,
    process_slash_commands,
)
from cli.runner import run_loop as _run_loop
import asyncio
import sys  # exposed for tests that patch main.sys.stdin

async def main():  # kept for backward compatibility
    await _run_loop()

if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())