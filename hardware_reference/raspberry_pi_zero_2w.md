# Raspberry Pi Zero 2 W — hardware reference

This file is fed to the LLM as grounding context whenever a spec targets
this board. Keep it factual and specific — this is what prevents pin
hallucination. Expand with peripheral-specific notes as you add support
for them.

## Logic level
3.3V. Standard across all Raspberry Pi models — GPIO pins are NOT 5V
tolerant. Any 5V peripheral needs a level shifter or divider.

## GPIO header
Standard 2x20 (40-pin) header, same pin function layout as other
40-pin Raspberry Pi boards (Pi 3/4/5) — SPI, I2C, UART, PWM, and generic
digital I/O all available via the usual BCM pin numbers. Unlike the
ESP32/Arduino boards in this project, there is no onboard ADC — the Pi
has no native analog input. Reading an analog sensor requires an external
ADC chip (e.g. MCP3008 over SPI) or offloading analog sensing to a
co-processor board (e.g. the ESP32) and reading the digitized value over
serial/I2C instead.

## Default serial / UART
Primary UART on the 40-pin header: TXD=GPIO14 (physical pin 8),
RXD=GPIO15 (physical pin 10). By default this UART may be used as a Linux
login console — if using it for a peripheral (e.g. another microcontroller),
disable the serial console in `raspi-config` first or the OS will fight
the connection.

This board is more commonly bridged to another microcontroller over
**USB serial** (via the micro-USB OTG port, see below) rather than the
GPIO UART, since USB serial doesn't require disabling the console and
appears as a standard `/dev/ttyUSB*` or `/dev/ttyACM*` device.

## USB
No full-size USB-A port. One micro-USB port is power-only; the other is
USB OTG (On-The-Go) and acts as the data port. To connect USB peripherals
(a gamepad, a USB-serial link to another board, a USB hub), use a
micro-USB OTG adapter, ideally into a powered hub if drawing more than
the OTG port's own current budget.

## Camera (CSI)
Uses a smaller 22-pin, 0.5mm-pitch CSI connector, physically different
from the larger CSI connector on Pi 4/5. The Pi Camera Module 3 ships with
a ribbon cable sized for the larger connector — connecting it to a Zero 2 W
requires the separate "Raspberry Pi Zero camera cable" adapter cable (small
connector on one end for the Zero, standard-size connector on the other
for the camera module). Don't assume the in-box camera cable fits this
board without that adapter.

## I2C / SPI
Default I2C: SDA=GPIO2 (pin 3), SCL=GPIO3 (pin 5). Default SPI0:
SCK=GPIO11, MOSI=GPIO10, MISO=GPIO9, CE0=GPIO8, CE1=GPIO7. Same as other
40-pin Pi boards.

## Power
Powered via the power-only micro-USB port, 5V input. The Zero 2 W's
onboard regulator steps this down for the SoC/peripherals — don't draw
heavy current (motors, servos) directly from the 3.3V/5V header pins;
those are for logic-level peripherals only, not actuators.

## WiFi / networking
Onboard 2.4GHz 802.11 b/g/n WiFi and Bluetooth — this is the board's only
network interface, relevant for any spec involving a phone UI, remote
control link, or cloud upload.

Sources: https://learn.sparkfun.com/tutorials/getting-started-with-the-raspberry-pi-zero-2-w/hardware-overview
