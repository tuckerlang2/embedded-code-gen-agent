# Raspberry Pi 4 — hardware reference

This file is fed to the LLM as grounding context whenever a spec targets
this board. Keep it factual and specific — this is what prevents pin
hallucination. Expand with peripheral-specific notes as you add support
for them.

(Note: this doc was previously referenced in config/boards.yaml but did
not exist on disk, which would have caused a FileNotFoundError the first
time anyone generated code for this board. Filled in now with standard,
well-established Pi 4 specs — verify against the official pinout if a
spec needs something safety-critical.)

## Logic level
3.3V. GPIO pins are NOT 5V tolerant. Any 5V peripheral needs a level
shifter or divider on signals going into the Pi.

## GPIO header
Standard 2x20 (40-pin) header — SPI, I2C, UART, PWM, and generic digital
I/O via the usual BCM pin numbers. No onboard ADC — the Pi has no native
analog input; reading an analog sensor requires an external ADC chip
(e.g. MCP3008 over SPI) or a co-processor microcontroller feeding
digitized values over serial/I2C.

## Default serial / UART
Primary UART on the header: TXD=GPIO14 (physical pin 8), RXD=GPIO15
(physical pin 10). May default to a Linux login console — disable via
`raspi-config` before using it for a peripheral connection, or use USB
serial instead to avoid the conflict entirely.

## USB
Two USB 2.0 and two USB 3.0 full-size Type-A ports (USB 3.0 ports are
blue). No OTG mode on the main USB ports (that's a Pi Zero feature);
standard host-mode USB peripherals (gamepad, USB-serial adapter) plug in
directly.

## Camera (CSI)
Standard-size 22-pin (15-pin on very early revisions — Pi 4 uses the
newer 22-pin) CSI connector. The Pi Camera Module 3's stock ribbon cable
fits directly, no adapter needed.

## I2C / SPI
Default I2C: SDA=GPIO2 (pin 3), SCL=GPIO3 (pin 5). Default SPI0:
SCK=GPIO11, MOSI=GPIO10, MISO=GPIO9, CE0=GPIO8, CE1=GPIO7.

## Power
USB-C power input, 5V (3A recommended for Pi 4 under load). Logic-level
GPIO/3.3V/5V header pins are for peripherals, not for driving motors or
other actuators directly.

## WiFi / networking
Onboard 2.4GHz/5GHz 802.11ac WiFi, Bluetooth, and a Gigabit Ethernet port
— relevant for any spec involving networking, remote control, or cloud
upload.
