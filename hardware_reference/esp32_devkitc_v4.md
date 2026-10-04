# ESP32 DevKitC V4 (WROOM-32) — hardware reference

This file is fed to the LLM as grounding context whenever a spec targets
this board. Keep it factual and specific — this is what prevents pin
hallucination. Expand with peripheral-specific notes as you add support
for them.

## Logic level
3.3V ONLY. Unlike classic Arduino boards, GPIO pins are NOT 5V tolerant —
driving a pin from a 5V signal can damage it. Any 5V peripheral (e.g. some
older sensor breakouts) needs a level shifter or voltage divider on its
output to this board.

## Pins to avoid entirely
- GPIO6–GPIO11: wired to the onboard SPI flash. Never use for I/O — using
  these will likely crash or brick the board.
- GPIO0, GPIO2, GPIO5, GPIO12, GPIO15: strapping pins that set boot mode
  at reset/power-on. Avoid driving these from external circuitry at boot
  (e.g. don't tie to a pulled-down relay or switch) or the board can fail
  to boot or boot into the wrong mode.

## Input-only pins
GPIO34, GPIO35, GPIO36 (labeled VP), GPIO39 (labeled VN): input only, no
internal pull-up/pull-down resistors. Fine for analog input or a digital
input with an external pull resistor; cannot drive outputs or PWM.

## Analog input (ADC)
Two ADC units, both 12-bit:
- ADC1 (safe to use alongside WiFi): GPIO32, 33, 34, 35, 36, 39
- ADC2 (shared with the WiFi radio — readings are unreliable while WiFi is
  active): GPIO0, 2, 4, 12, 13, 14, 15, 25, 26, 27

Prefer an ADC1 pin for any analog sensor (e.g. a capacitive soil
moisture probe) if WiFi may ever run on this chip. Note ESP32 ADC is
non-linear and not pre-calibrated to a precise voltage — don't assume raw
`analogRead()` counts map linearly to volts without characterizing it
against known references.

## PWM
No dedicated PWM pins — PWM is done in software via the LEDC peripheral
and can be assigned to nearly any GPIO. Safe general-purpose choices that
avoid strapping/input-only/flash pins: GPIO4, 13, 14, 16, 17, 18, 19, 21,
22, 23, 25, 26, 27, 32, 33.

## UART (serial)
- UART0: TX=GPIO1, RX=GPIO3 — this is the pair wired to the onboard
  USB-to-serial bridge (CP2102/CH340 depending on clone). This is what a
  USB cable to a host (e.g. a Raspberry Pi) talks to by default.
- UART2: TX=GPIO17, RX=GPIO16 — free pair for a second serial device, e.g.
  a motor controller's TTL serial input. For a transmit-only device (such
  as Sabertooth simplified/packetized serial, which only reads), only the
  TX pin needs to be wired; RX16 can be left unused.

## I2C
Default (Wire library): SDA=GPIO21, SCL=GPIO22. Both are shared with other
suggested-safe PWM pins above — note the conflict if a spec uses I2C and
also wants PWM on 21/22.

## SPI
Default (VSPI): SCK=GPIO18, MISO=GPIO19, MOSI=GPIO23, CS=GPIO5. CS/GPIO5
is also a strapping pin — be cautious using it as a chip-select that could
be asserted (pulled low) during boot.

## Power
- 5V/VIN pin: accepts 5V in from USB or external supply, feeds the onboard
  3.3V regulator — do NOT treat this as a 5V logic rail for sensors.
- 3.3V pin: regulated output, limited current (check specific board's
  regulator, often ~500mA–600mA) — fine for small sensors/modules, not for
  motors or servos.
- Servos and motor-controller logic inputs should be powered from their
  own appropriately-rated supply, with only a GND and the relevant
  PWM/serial signal line shared back to the ESP32.

Sources: https://esp32.co.uk/esp32-devkitc-v4-pinout-diagram-safe-gpios/
