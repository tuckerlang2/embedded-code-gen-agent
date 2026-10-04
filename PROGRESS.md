# Progress log

Append a new entry every session. Don't delete old entries — this is the
history of decisions, not just current state. If you (or a Claude session)
need to know "why did we do it this way," it should be answerable here.

---

## 2026-07-05 — Session 1: project kickoff
- Defined the goal: agent that generates Arduino/RPi code from a structured
  spec, grounded in real hardware reference data, with a compile-check loop
  and mandatory human review before flashing.
- Decided on architecture: spec -> hardware_lookup -> codegen -> compile_check
  (loop on error) -> human review -> flash. Human review step is a hard
  safety boundary, not optional.
- Scaffolded repo structure, CLAUDE.md, and stub source files.
- Next session: implement hardware_lookup.py, seed 2-3 real board reference
  docs, wire up codegen.py to an actual LLM API call.

## 2026-07-05 — Session 2: first successful end-to-end run
(Backfilled on 2026-10-04 — this work was committed at the time but the
log entry was never written, so CLAUDE.md's "Current state" went stale.
Reconstructed from the actual code + an external record of the session.)
- Implemented hardware_lookup.py, seeded arduino_uno.md reference doc,
  wired codegen.py to the Anthropic API.
- Fixed three bugs found during first real test: .env wasn't being loaded
  (missing dotenv call with absolute path), Claude's response included
  markdown code fences that broke compilation (added _strip_code_fence),
  and a Unicode character (Ω) in generated comments broke the file write
  on Windows (added encoding="utf-8" to write_text).
- Confirmed first successful end-to-end run: PIR motion sensor + LED
  blink example, generated on attempt 1, compiled clean via arduino-cli.
- Incident: GitHub Copilot's inline suggestions silently rewrote agent.py
  twice during setup. Lesson: keep Copilot inline suggestions disabled
  inside src/ while actively building with Claude in chat.
- Next step: expand hardware_reference/ beyond Arduino Uno, test a second
  spec to validate the hardware-grounding approach generalizes.

## 2026-10-04 — Session 3: pre-flight fixes before starting rover project
- Found config/boards.yaml had raspberry_pi_4 registered with a
  reference_doc path that didn't exist on disk — hardware_lookup.py would
  have raised FileNotFoundError on first use. Not related to the rover
  work; fixed as a standing bug. Wrote hardware_reference/raspberry_pi_4.md.
- Found codegen.py was calling model "claude-sonnet-4-6", not a real model
  ID. Fixed to "claude-sonnet-5".
- Added board registry entries + reference docs for the two boards the
  rover project needs: esp32_devkitc_v4 and raspberry_pi_zero_2w. ESP32
  entry notes that the esp32 arduino-cli core isn't installed by default
  and has to be added separately (not an AVR board).
- Reconciled CLAUDE.md's "Current state" section, which still said
  "skeleton, no working code" despite Session 2's work being in the repo.
- Flagged, not resolved: spec_schema.py models one spec -> one board -> one
  file. The rover is two boards that need to agree on a shared serial
  protocol — the schema has no concept of a multi-board spec or shared
  protocol constants. Revisit if/when we want the generator (rather than
  hand-written + reviewed code) to produce both sides.
