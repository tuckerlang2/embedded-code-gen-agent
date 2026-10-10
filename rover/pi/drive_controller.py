"""
drive_controller.py
Pi-side control loop: reads a USB/Bluetooth gamepad via pygame, mixes the
axes into left/right motor speeds, and sends drive frames to the ESP32 at
a fixed cadence over USB serial. See ../PROTOCOL.md for the wire format
and the safety reasoning behind the fixed-cadence send.

This is the "phone UI or gamepad talks to the Pi, Pi relays to ESP32"
half of the control architecture decided earlier -- the ESP32 is the
safety-critical side (it has its own independent watchdog); this script
is the convenience/UX side. If this script crashes, hangs, or the
gamepad disconnects, the right behavior is "stop sending commands" --
the ESP32 notices on its own and stops the motors regardless.
"""
import argparse
import sys
import time

import pygame
import serial

from protocol import encode_drive_frame, stop_frame, TelemetryFrameParser

SEND_HZ = 50
SEND_INTERVAL_S = 1.0 / SEND_HZ

# Joystick axis indices are NOT standardized across controllers/OSes.
# Confirmed 2026-10-10 against the T47 controller (Xbox-mode, SDL mapping)
# via debug_gamepad.py: axis 0/1 = left stick X/Y, axis 2 = left trigger
# (NOT a stick -- rests at -1), axis 3/4 = right stick X/Y, axis 5 = right
# trigger. Re-confirm with debug_gamepad.py if you swap controllers.
THROTTLE_AXIS = 1   # left stick, vertical
TURN_AXIS = 3        # right stick, horizontal (was wrongly 2 -- that's the left trigger)
DEADZONE = 0.08       # ignore stick drift near center

# Buttons that command the probe servo. Adjust indices to match your
# controller (printed at startup is NOT currently implemented for
# buttons -- check `jstest` or similar on Linux if these don't match).
SERVO_EXTEND_BUTTON = 0
SERVO_RETRACT_BUTTON = 1
SERVO_EXTEND_ANGLE = 90
SERVO_RETRACT_ANGLE = 0

# Max speed limiter, independent of the wire format's -100..100 range.
# Start conservative; raise once you've driven it and trust the mixing.
MAX_SPEED_PERCENT = 70


def apply_deadzone(value: float, deadzone: float = DEADZONE) -> float:
    if abs(value) < deadzone:
        return 0.0
    # Rescale so output still reaches -1..1 just past the deadzone,
    # rather than having a dead band followed by a jump.
    sign = 1.0 if value > 0 else -1.0
    return sign * (abs(value) - deadzone) / (1.0 - deadzone)


def mix_arcade_drive(throttle: float, turn: float) -> tuple[int, int]:
    """
    throttle, turn are each in -1..1. Returns (left_speed, right_speed)
    as integer percents in -100..100, scaled by MAX_SPEED_PERCENT.
    """
    left = throttle + turn
    right = throttle - turn
    # Normalize if the sum exceeds +/-1 (e.g. full throttle + full turn)
    largest = max(abs(left), abs(right), 1.0)
    left /= largest
    right /= largest
    return (
        int(round(left * MAX_SPEED_PERCENT)),
        int(round(right * MAX_SPEED_PERCENT)),
    )


def open_serial(port: str, baud: int) -> serial.Serial:
    try:
        return serial.Serial(port, baud, timeout=0)  # non-blocking reads
    except serial.SerialException as e:
        print(f"Could not open serial port {port}: {e}", file=sys.stderr)
        print("Check `ls /dev/tty*` for the ESP32's actual device name "
              "(commonly /dev/ttyUSB0 or /dev/ttyACM0) and pass it with --port.",
              file=sys.stderr)
        sys.exit(1)


def init_gamepad() -> "pygame.joystick.JoystickType | None":
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        return None
    js = pygame.joystick.Joystick(0)
    js.init()
    print(f"Gamepad connected: {js.get_name()} "
          f"({js.get_numaxes()} axes, {js.get_numbuttons()} buttons)")
    return js


def main():
    parser = argparse.ArgumentParser(description="Rover drive controller (gamepad -> ESP32 serial)")
    parser.add_argument("--port", default="/dev/ttyUSB0",
                         help="Serial device for the ESP32 (default: /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200,
                         help="Must match PROTOCOL.md / esp32_firmware.ino (default: 115200)")
    args = parser.parse_args()

    ser = open_serial(args.port, args.baud)
    telemetry_parser = TelemetryFrameParser()
    js = init_gamepad()
    if js is None:
        print("No gamepad detected at startup. The loop will keep checking "
              "and will send stop frames until one connects.", file=sys.stderr)

    last_soil_print = 0.0

    try:
        while True:
            loop_start = time.monotonic()

            # Re-check for gamepad connect/disconnect every iteration --
            # pygame doesn't raise on a mid-session unplug, it just stops
            # updating, so re-reading get_count() is how we notice.
            if js is None:
                js = init_gamepad()

            pygame.event.pump()

            if js is None or pygame.joystick.get_count() == 0:
                # No controller: this is the Pi-side link watchdog
                # described in PROTOCOL.md -- send explicit stop rather
                # than just not sending. Not the safety backstop (the
                # ESP32's own watchdog is), but correct UX behavior.
                left_speed, right_speed = 0, 0
                servo_cmd = 255
                js = None
            else:
                throttle = apply_deadzone(-js.get_axis(THROTTLE_AXIS))  # up = positive
                turn = apply_deadzone(js.get_axis(TURN_AXIS))
                left_speed, right_speed = mix_arcade_drive(throttle, turn)

                servo_cmd = 255
                if js.get_button(SERVO_EXTEND_BUTTON):
                    servo_cmd = SERVO_EXTEND_ANGLE
                elif js.get_button(SERVO_RETRACT_BUTTON):
                    servo_cmd = SERVO_RETRACT_ANGLE

            frame = encode_drive_frame(left_speed, right_speed, servo_cmd)
            ser.write(frame)

            # Drain and parse any telemetry bytes waiting in the input
            # buffer. Non-blocking (timeout=0 on the Serial object).
            incoming = ser.read(256)
            if incoming:
                for reading in telemetry_parser.feed_bytes(incoming):
                    now = time.monotonic()
                    if now - last_soil_print > 1.0:  # throttle console spam
                        last_soil_print = now
                        flag = " [WATCHDOG TRIPPED]" if reading["watchdog_tripped"] else ""
                        print(f"soil_raw={reading['soil_raw']}{flag}")

            elapsed = time.monotonic() - loop_start
            time.sleep(max(0.0, SEND_INTERVAL_S - elapsed))

    except KeyboardInterrupt:
        print("\nShutting down -- sending stop frames before exit.")
        for _ in range(5):  # a few, in case one gets dropped on the way out
            ser.write(stop_frame())
            time.sleep(0.02)
        ser.close()


if __name__ == "__main__":
    main()
