# CLAUDE.md — context for every session

This file is read automatically by Claude Code at the start of a session.
Keep it current — it's the project's memory across days. Update the
"Current state" section at the end of every work session, before you stop.

## What this project is
An agent that generates Arduino/Raspberry Pi project code from a structured
spec (board, sensors/actuators, IO requirements, goal), grounded in real
hardware reference data (not LLM memory of pinouts), with an automated
compile-check loop and a mandatory human review gate before anything is
flashed to real hardware.

## Architecture (see ARCHITECTURE.md for the diagram/rationale)
spec -> hardware_lookup -> codegen (LLM) -> compile_check (arduino-cli/platformio)
     -> [loop back to codegen on compile error] -> human review -> flash

## Non-negotiable design rules
- Never let the LLM invent pin numbers/voltage specs from memory alone —
  always ground generation in `hardware_reference/*.md` for the specific
  board/module in use. This is the #1 reliability lever for this project.
- Compile check must run headless, no hardware attached, before any human
  review step.
- Human review is mandatory before flashing — never auto-flash. This is a
  safety boundary, not a convenience feature to remove later.
- Voltage/logic-level mismatches (5V vs 3.3V) are the main physical risk —
  hardware_lookup entries should always state logic level.

## Project structure
```
config/boards.yaml          - registry of supported boards + toolchain info
hardware_reference/*.md     - pinouts, logic levels, common sensor notes
src/spec_schema.py          - defines/validates the input spec format
src/hardware_lookup.py      - loads relevant reference docs for a spec
src/codegen.py              - calls LLM API to generate code from spec + refs
src/compile_check.py        - wraps arduino-cli/platformio, returns errors
src/agent.py                - orchestrates the loop above
generated/                  - output project code lands here (gitignored)
templates/                  - prompt templates used by codegen.py
PROGRESS.md                 - session-by-session log (append, don't rewrite)
```

## Current state
(Update this every session)
- Status: skeleton scaffolded, no working code yet
- Last worked on: initial repo setup
- Next step: decide on LLM API to call from codegen.py (Anthropic API
  recommended — see anthropic_api notes below), then implement
  hardware_lookup.py against the two seed reference docs
- Open decisions: none yet

## Environment notes
- Requires `arduino-cli` installed and on PATH for compile_check.py to work
  (`brew install arduino-cli` / see arduino-cli docs for other platforms)
- Python 3.10+, see requirements.txt
- API key for whichever LLM you call from codegen.py should go in a local
  `.env` file (already gitignored) — never commit it
