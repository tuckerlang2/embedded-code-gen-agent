# Arduino Uno (R3) — hardware reference

This file is fed to the LLM as grounding context whenever a spec targets
this board. Keep it factual and specific — this is what prevents pin
hallucination. Expand with sensor-specific notes as you add support for them.

## Logic level
5V. Do NOT connect 3.3V-only sensor modules directly without a level
shifter — this is the most common wiring mistake on this board.

## Digital pins
- D0, D1: RX/TX (serial) — avoid using while USB serial is active
- D2, D3: support hardware interrupts (attachInterrupt)
- D3, D5, D6, D9, D10, D11: PWM-capable (~ symbol on board silkscreen)
- D13: onboard LED, also SPI SCK

## Analog pins
- A0–A5: analog input only by default (10-bit ADC, 0–5V range)
- A4, A5: also I2C (SDA/SCL) if using Wire library

## Power pins
- 5V: regulated 5V out (limited current, ~500mA shared with USB)
- 3.3V: regulated 3.3V out (limited current, ~50mA — do not power motors etc.)
- VIN: raw input voltage if powering via barrel jack (7–12V recommended)

## Common libraries
- Servo: `Servo.h` — note this disables PWM on D9/D10 while attached
- I2C devices: `Wire.h`
- DHT temp/humidity sensors: `DHT.h` (Adafruit) — needs pull-up resistor on data pin
