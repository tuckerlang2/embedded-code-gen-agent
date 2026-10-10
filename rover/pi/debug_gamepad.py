"""
debug_gamepad.py
Throwaway debug tool -- NOT part of the committed protocol/control code.
Prints raw axis and button values as they change, so you can visually
confirm which axis index is which stick and which button index is which
button on your specific controller, before trusting drive_controller.py's
THROTTLE_AXIS / TURN_AXIS / SERVO_EXTEND_BUTTON / SERVO_RETRACT_BUTTON
constants.

Run: python3 debug_gamepad.py
Ctrl+C to quit.
"""
import pygame
import time

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("No gamepad detected. Plug it in and try again.")
    raise SystemExit(1)

js = pygame.joystick.Joystick(0)
js.init()
print(f"Connected: {js.get_name()} ({js.get_numaxes()} axes, {js.get_numbuttons()} buttons)")
print("Move sticks / press buttons. Ctrl+C to quit.\n")

last_axes = [0.0] * js.get_numaxes()
last_buttons = [0] * js.get_numbuttons()

try:
    while True:
        pygame.event.pump()

        for i in range(js.get_numaxes()):
            val = js.get_axis(i)
            if abs(val - last_axes[i]) > 0.1:  # only print meaningful movement
                print(f"axis {i}: {val:.2f}")
                last_axes[i] = val

        for i in range(js.get_numbuttons()):
            val = js.get_button(i)
            if val != last_buttons[i]:
                print(f"button {i}: {'pressed' if val else 'released'}")
                last_buttons[i] = val

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nDone.")
