# 4WD wiring diagram (dual Sabertooth)

Block diagram of the 2026-11-19 4WD conversion — shows signal and power
relationships, not a wire-gauge/connector-level schematic. Pin numbers
match `esp32_firmware.ino` and `hardware_reference/esp32_devkitc_v4.md`.

Note: the I/O co-processor board here is the **ESP32 DevKitC V4**, not
an Arduino — the ESP32 pin numbers below are the ones that matter for
this build. (If you're ever adding a Sabertooth to an actual Arduino
Uno/Mega board instead, the pin numbers are different and 5V-tolerant,
unlike the ESP32 — don't reuse these numbers on different hardware.)

## New pins to add for the second (REAR) Sabertooth

Only **one new ESP32 pin carries a real signal** — Sabertooth
simplified serial is receive-only, so the "RX" pin below is wired for
completeness/future use but currently carries nothing.

| Connection | ESP32 pin | Sabertooth 2x12 (REAR) terminal | Notes |
|---|---|---|---|
| Serial signal (new) | **GPIO19** | S1 | This is the only new wire that actually does anything. Add it now. |
| Serial RX (unused) | GPIO27 | — (not connected) | Reserved in firmware (`Serial1.begin(...)`) but Sabertooth never talks back. You can skip wiring this pin to anything; nothing listens on it. |
| Ground (new) | Any ESP32 **GND** pin | 0V | Must be a *separate* ground wire from the FRONT Sabertooth's — see below, this is not optional. |

For reference, what's already wired for the existing FRONT Sabertooth
(unchanged by this conversion):

| Connection | ESP32 pin | Sabertooth 2x12 (FRONT) terminal |
|---|---|---|
| Serial signal | GPIO17 | S1 |
| Serial RX (unused) | GPIO16 | — (not connected) |
| Ground | ESP32 GND | 0V |

**Why GPIO19/27 and not the UART1 default pins:** ESP32's UART1 defaults
to pins that conflict with the onboard SPI flash, so the firmware remaps
it explicitly (`Serial1.begin(baud, SERIAL_8N1, 27, 19)`). GPIO19 and 27
were already reserved as free "margin" pins in this repo's own pin
budget before this conversion — confirmed against
`hardware_reference/esp32_devkitc_v4.md`: neither is a flash pin
(GPIO6–11) or a strapping pin (0/2/5/12/15), and GPIO19 is in that doc's
list of safe general-purpose/PWM pins.

**Don't skip the ground wire.** Each Sabertooth needs its own ground
connection back to the ESP32 (or a shared ground bus the ESP32 is also
on) — grounding only the FRONT unit and assuming the REAR unit "shares"
it through the battery's power distribution is not reliable for a
signal-level connection; a Sabertooth with a floating/indirect ground
reference relative to the ESP32's TX pin can read garbled serial data.

```mermaid
flowchart TD
    BATT["Battery pack"]
    ESTOP["Hardware E-stop\n(NC pushbutton relay)\nCONFIRMED: covers BOTH\nSabertooths' power feed"]
    PDB["Power distribution\n(main feed, after E-stop)"]

    BATT --> ESTOP --> PDB

    PI["Raspberry Pi Zero 2 W"]
    ESP["ESP32 DevKitC V4"]
    GAMEPAD["Xbox gamepad"]

    GAMEPAD -.USB.-> PI
    PI <--"USB serial, UART0\nGPIO1 TX / GPIO3 RX\n115200 baud"--> ESP

    SABF["Sabertooth 2x12 (FRONT)\nM1=front-left, M2=front-right\nDIP switches: assumed 9600 simplified\nserial, never independently checked"]
    SABR["Sabertooth 2x12 (REAR) -- NEW WIRING\nM1=rear-left, M2=rear-right\nDIP switches set IDENTICAL to FRONT\n(confirmed) -- same unverified baud\nassumption as FRONT, not a new one"]

    ESP --"existing: GPIO17 -> S1\n9600 baud, simplified serial"--> SABF
    ESP =="NEW: GPIO19 -> S1\n(UART1, remapped from\ndefault pins)\n9600 baud, simplified serial"==> SABR

    PDB --"main power feed"--> SABF
    PDB --"main power feed\n(own feed, not daisy-chained\noff FRONT's terminals)"--> SABR

    ESP =="existing: GND -> 0V"== SABF
    ESP =="NEW: separate GND -> 0V\n(do not skip -- see notes)"== SABR

    FL["Front-left motor"]
    FR["Front-right motor"]
    RL["Rear-left motor"]
    RR["Rear-right motor"]

    SABF --> FL
    SABF --> FR
    SABR --> RL
    SABR --> RR
```

## What this does and doesn't show
- **Shown:** which board talks to which, which pins, which Sabertooth
  drives which wheel pair, and where power/ground relationships exist.
- **Not shown:** wire gauge, connector types, physical layout/routing,
  fusing. This is a logic/block diagram for getting the architecture
  right before wiring, not a build sheet.
- Soil probe (ADC, GPIO34) and probe servo (GPIO13) are omitted here —
  unaffected by the 4WD change. See `esp32_firmware.ino`'s pin
  assignment block for those.

## Open items this diagram deliberately flags, not resolves
1. ~~E-stop coverage of both Sabertooths.~~ **Confirmed 2026-11-19
   (user): the relay covers both units' power feed.**
2. **Sabertooth DIP switches (both units) — baud assumption still
   unverified.** The REAR unit is confirmed set identically to the
   FRONT unit (2026-11-19), which rules out the two units disagreeing
   with each other, but neither unit's switches have been read off and
   checked against the firmware's `SABERTOOTH_BAUD` (9600, simplified
   serial) assumption. This is now one shared open item, not two.
3. **Common ground and independent power feed for the REAR unit** —
   shown above as a requirement, not yet confirmed done on the physical
   build.

See `rover/README.md`'s "Before this drives real motors" checklist —
these items are listed there too; this diagram exists to make them
visually obvious at the point in the circuit they apply to.
