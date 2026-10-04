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
- Status: codegen loop works end-to-end (confirmed on Arduino Uno PIR+LED
  example). Board registry expanded to support a two-board rover project
  (ESP32 DevKitC V4 + Raspberry Pi Zero 2 W) alongside the original Uno/Pi4.
- Last worked on: fixed a stale model string in codegen.py
  (`claude-sonnet-4-6` → `claude-sonnet-5`, the previous string was not a
  real model ID); added `esp32_devkitc_v4` and `raspberry_pi_zero_2w` board
  entries + reference docs; filled in `raspberry_pi_4.md`, which was
  registered in boards.yaml but missing from disk (would have thrown
  FileNotFoundError on first use — fixed as a latent bug, unrelated to the
  rover project).
- Next step: rover-specific work — serial protocol between the Pi and
  ESP32 (drive commands + heartbeat/watchdog), ESP32 firmware for
  Sabertooth control + soil probe + servo, Pi-side gamepad/phone control
  intake.
- Open decisions: the agent currently generates one file per single-board
  spec. The rover project needs two boards that agree on a shared serial
  protocol — nothing in spec_schema.py represents a relationship between
  two specs or shared protocol constants. Not resolved — decide whether to
  extend the schema for this or keep board firmware hand-written/reviewed
  outside the generator for now.

## Environment notes
- Requires `arduino-cli` installed and on PATH for compile_check.py to work
  (`brew install arduino-cli` / see arduino-cli docs for other platforms)
- ESP32 boards need the esp32 core installed separately — it's not bundled
  with arduino-cli by default. See the `core_install_note` / comment in
  `config/boards.yaml` under `esp32_devkitc_v4` for the exact commands.
- Python 3.10+, see requirements.txt
- API key for whichever LLM you call from codegen.py should go in a local
  `.env` file (already gitignored) — never commit it
