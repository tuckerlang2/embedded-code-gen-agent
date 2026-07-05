# Embedded Codegen Agent

Generates Arduino / Raspberry Pi project code from a structured spec
(board, sensors/actuators, IO needs, goal), grounded in real hardware
reference data, with an automated compile-check loop and a mandatory
human review step before anything gets flashed to real hardware.

## Setup
```bash
python -m venv venv
source venv/bin/activate        # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

Install `arduino-cli` (required for the compile-check loop):
https://arduino.github.io/arduino-cli/latest/installation/

Copy `.env.example` to `.env` and add your Anthropic API key.

## Resuming work
Read `CLAUDE.md` first — it has the architecture, design rules, and current
state. Then check `PROGRESS.md` for the session history. If you're using
Claude Code, it reads `CLAUDE.md` automatically.

## Status
Early scaffold — see PROGRESS.md for exactly where things stand.
