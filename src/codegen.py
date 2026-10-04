"""
codegen.py
Calls the LLM to generate code from a spec + hardware reference context.
Kept deliberately simple (single call, no framework) so the loop in
agent.py stays easy to reason about and debug.
"""
import os
import anthropic
from pathlib import Path
from dotenv import load_dotenv
from spec_schema import ProjectSpec
from hardware_lookup import get_reference_text, get_board_meta

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SYSTEM_PROMPT = """You generate embedded code (Arduino sketches or Python for \
Raspberry Pi) from a project spec. You are given real hardware reference \
documentation for the target board - use it as ground truth for pin numbers, \
voltage levels, and library usage. Do not invent pin assignments not \
supported by the reference doc. If the spec is ambiguous about wiring, \
state your assumption in a code comment rather than guessing silently. \
Output only the code, in a single code block, with brief inline comments."""


def generate_code(spec: ProjectSpec, compile_error: str | None = None) -> str:
    """
    Generates code for the given spec. If compile_error is provided, this is
    a retry - the previous attempt's compiler error is included so the model
    can fix it, rather than regenerating blind.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    reference_doc = get_reference_text(spec.board)
    board_meta = get_board_meta(spec.board)

    components_desc = "\n".join(
        f"- {c.name} ({c.connection}){': ' + c.notes if c.notes else ''}"
        for c in spec.components
    )

    prompt = f"""Board: {board_meta['display_name']} (logic level: {board_meta['logic_level_v']}V)

Hardware reference:
{reference_doc}

Goal: {spec.goal}

Components:
{components_desc}

Constraints: {', '.join(spec.constraints) if spec.constraints else 'none'}
"""

    if compile_error:
        prompt += f"\nThe previous attempt failed to compile with this error - fix it:\n{compile_error}"

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return _strip_code_fence(response.content[0].text)


def _strip_code_fence(text: str) -> str:
    """Removes markdown code fences (```cpp ... ``` or ``` ... ```) if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()