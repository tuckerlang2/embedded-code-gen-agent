# Pi <-> ESP32 serial protocol

This is the single source of truth for the link between the Raspberry Pi
Zero 2 W and the ESP32 DevKitC V4. Both `esp32_firmware/` and `pi/` are
hand-written to this spec (not generated) — see CLAUDE.md's "Open
decisions" note on why. If you change a value here, update both
implementations and bump the version note at the bottom.

This document only covers the Pi<->ESP32 link. The ESP32<->Sabertooth
link is a separate, standard protocol (Sabertooth simplified serial) —
see the comment block in `esp32_firmware/esp32_firmware.ino` for that.

## Physical link
USB, Pi to ESP32's onboard USB-serial bridge (ESP32 UART0 / GPIO1 TX,
GPIO3 RX — see `hardware_reference/esp32_devkitc_v4.md`). Appears on the
Pi as `/dev/ttyUSB0` or `/dev/ttyACM0` depending on the specific board's
USB-serial chip (CP2102 vs CH340) — check `ls /dev/tty*` after plugging in
and adjust the Pi-side config if needed.

**Baud: 115200.**

## Why a custom binary frame, not a text protocol
A short fixed-length binary frame is cheap to parse on the ESP32 (no
string parsing, no heap allocation, bounded worst-case parse time — all
relevant for a loop that also has to run the watchdog check) and leaves
no ambiguity about framing. The tradeoff is you can't just open a serial
terminal and read it — that's acceptable here since this is a
machine-to-machine link, not something a human inspects directly.

## Drive frame: Pi -> ESP32

Sent at a fixed cadence of **50 Hz (every 20 ms)**, whether or not the
commanded speed has changed — the ESP32 uses "a valid frame recently
arrived" as its liveness signal (see Watchdog below), so this frame
doubles as the heartbeat. Do not suppress sending just because the
command is unchanged from last time.

5 bytes, fixed length:

| Byte | Name          | Type        | Meaning                                                                 |
|------|---------------|-------------|--------------------------------------------------------------------------|
| 0    | SYNC          | uint8       | Always `0xAA`. Marks the start of a frame.                               |
| 1    | left_speed    | int8        | -100..100. Percent of max speed, left-side motor. Negative = reverse.    |
| 2    | right_speed   | int8        | -100..100. Percent of max speed, right-side motor. Negative = reverse.   |
| 3    | servo_cmd     | uint8       | 0-180 = target servo angle (degrees). 255 = "no change" (leave as-is).   |
| 4    | checksum      | uint8       | `(byte1 + byte2 + byte3) & 0xFF` — additive checksum, see note below.    |

Total: 5 bytes = ~0.4ms of airtime at 115200 baud (~8600 bytes/sec), so a
20ms cadence has enormous margin — this is not a bandwidth-constrained
link.

**Checksum is corruption detection, not security.** This is a USB-tethered
link between two boards you own; the goal is catching a torn/garbled
frame from a USB hiccup, not defending against a malicious sender. A
simple additive checksum is sufficient and cheap to compute on the ESP32.

**Resync behavior:** the ESP32 reads byte-by-byte. If it reads a byte that
would be a SYNC byte but the frame that follows fails its checksum, it
discards that byte and resumes scanning for the next `0xAA` — it does NOT
assume frame alignment. This matters because `0xAA` can appear inside a
torn frame's payload bytes by coincidence; checksum failure is what
actually confirms misalignment, the SYNC byte alone is just where to
start looking.

## Telemetry frame: ESP32 -> Pi

Sent at **5 Hz (every 200 ms)** — this is status reporting, not a control
loop, so it doesn't need drive-frame cadence.

5 bytes, fixed length:

| Byte | Name            | Type   | Meaning                                                          |
|------|-----------------|--------|-------------------------------------------------------------------|
| 0    | SYNC            | uint8  | Always `0xBB` (different from the drive frame's `0xAA` so a byte stream can't be ambiguous about which direction/frame type it's looking at mid-resync). |
| 1    | soil_raw_high   | uint8  | High byte of the 12-bit raw ADC soil reading (0-4095).            |
| 2    | soil_raw_low    | uint8  | Low byte of the same reading.                                     |
| 3    | status_flags    | uint8  | Bit 0: watchdog currently tripped (1 = ESP32 is in forced-stop). Bits 1-7 reserved, send 0. |
| 4    | checksum        | uint8  | `(byte1 + byte2 + byte3) & 0xFF`, same scheme as the drive frame.  |

`status_flags` bit 0 exists so the Pi-side UI can show "link OK but
ESP32 stopped itself" distinctly from "no telemetry at all" — the two
have different causes (watchdog trip vs. USB unplugged) and a person
driving the rover should be able to tell them apart at a glance.

## Watchdog (the actual safety mechanism)

This is the part that satisfies the project's requirement that drive
safety never depends on the Pi being alive.

- The ESP32 tracks the timestamp of the last drive frame that passed its
  checksum.
- If more than **400 ms** pass without one, the ESP32 stops trusting the
  last commanded speed and forces both Sabertooth channels to neutral
  (stop), and holds that forced-stop state — continuously re-sending the
  Sabertooth neutral bytes, since Sabertooth's own serial timeout will
  also cut the motors if it stops hearing from the ESP32, but the ESP32
  doesn't rely on that; it actively commands stop.
- This check lives entirely in the ESP32's own loop, independent of
  anything the Pi does. A hung or rebooting Pi simply stops sending
  frames; the ESP32 notices via its own clock and stops the motors on its
  own, with zero dependency on the Pi detecting its own failure.
- 400 ms is 20x the 20ms send interval — generous enough that normal USB
  scheduling jitter never trips it, short enough that a real Pi hang
  stops the rover well within human reaction time.
- This is layered *under* the hardware E-stop, not a replacement for it.
  The E-stop cuts the Sabertooth's main power feed directly and doesn't
  go through either board; this watchdog is the software-level backstop
  for "controller link died" specifically, a different failure mode.

## Pi-side link watchdog (secondary, not safety-critical)

The Pi should also notice when its own input source (gamepad) has
disconnected or stopped reporting, and send stop frames (left_speed=0,
right_speed=0) rather than silently stop sending entirely. This is a UX
nicety — if the Pi stops sending *at all*, the ESP32's own watchdog above
is what actually stops the rover. Don't skip the ESP32-side watchdog on
the assumption the Pi will always behave correctly; it won't, that's the
whole premise of this project's architecture.

## Version
v1 — 2026-10-04. No prior versions; this is the first definition.
