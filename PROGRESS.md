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

## 2026-10-04 — Session 4: rover control software, first pass
- Decided: rover/ is hand-written and reviewed, not agent-generated, for
  the reason flagged in Session 3. Revisit only if there's real appetite
  to extend spec_schema.py for multi-board specs with shared protocol
  constants.
- Designed and documented the Pi<->ESP32 serial protocol
  (rover/PROTOCOL.md): 5-byte binary frames, 50Hz drive frames from Pi
  (doubling as heartbeat), 5Hz telemetry frames from ESP32, additive
  checksum, 400ms ESP32-side watchdog that forces the Sabertooth to
  neutral independent of the Pi.
- Wrote rover/esp32_firmware/esp32_firmware.ino: parses drive frames,
  relays to Sabertooth via simplified serial (UART2), reads the soil
  probe on ADC1 (GPIO34), drives the probe servo (GPIO13, ESP32Servo
  lib), enforces the watchdog, sends telemetry. NOT YET COMPILED — this
  dev environment has no arduino-cli/ESP32 toolchain and installing one
  here failed (network allowlist blocked the installer). Must be
  compiled and reviewed locally before flashing; see rover/README.md.
- Wrote rover/pi/protocol.py (frame encode/decode) and
  rover/pi/drive_controller.py (gamepad -> serial loop, arcade-drive
  mixing, Pi-side link watchdog that sends stop on gamepad disconnect).
- Actually tested what's testable in this environment: wrote
  rover/pi/test_protocol.py (6 tests, all passing — checksum validation,
  signed-byte round-trip, corruption rejection, resync behavior) and
  smoke-tested drive_controller.py's pure logic (deadzone, arcade
  mixing, no-gamepad startup path) directly. The live serial+gamepad
  loop itself has NOT run against real hardware.
- One test bug found and fixed during this: an early resync test
  asserted a stronger guarantee than PROTOCOL.md actually makes (that a
  real frame would always survive a stray sync byte landing in the
  immediately preceding garbage) — fixed the test to match the
  documented, correct guarantee (recovery within one more frame cycle),
  not the firmware/parser.
- Next step: get this onto real hardware. Bench-test the watchdog
  (unplug Pi link mid-drive, confirm motors stop within ~400ms with
  wheels off the ground) before anything drives on grass. Then: Pi
  camera capture, phone UI, GPS/route planning (still deliberately
  deferred).
- Worked out but explicitly deferred: pin budget for 3x ultrasonic
  distance sensors, 3x status LEDs, 2x soil-probe limit switches —
  logged in rover/README.md's "Deferred scope" section, not built.
  Flagged a real voltage-mismatch risk (classic HC-SR04 ECHO is 5V,
  ESP32 is 3.3V-only) and an open question (passive logging vs. active
  obstacle avoidance) to resolve before wiring, not after.

## 2026-10-04 — Session 5: first hardware bring-up
- ESP32 firmware compiled and flashed successfully on real hardware
  (Arduino IDE, ESP32 Dev Module board, esp32:esp32 core + ESP32Servo
  library). Fixed an upload-time error along the way: Arduino IDE was
  defaulting to a board definition that uses DFU/native-USB upload
  ("No DFU capable USB device available") because the esp32:esp32 core
  wasn't installed yet, so it fell back to a different ESP32 board
  package. Installing the esp32:esp32 core and explicitly selecting
  "ESP32 Dev Module" fixed it.
- This satisfies the project's compile-check-before-review requirement
  for this file. Runtime behavior is still unverified — nothing has
  been bench-tested yet (no physical testing until solder/terminal
  breakout boards arrive).
- Next step: once hardware's in hand, bench-test the watchdog first
  (wheels off the ground) before anything else.
