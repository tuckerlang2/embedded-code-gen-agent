# 4WD wiring diagram (dual Sabertooth)

Block diagram of the 2026-11-19 4WD conversion — shows signal and power
relationships, not a wire-gauge/connector-level schematic. Pin numbers
match `esp32_firmware.ino` and `hardware_reference/esp32_devkitc_v4.md`.

```mermaid
flowchart TD
    BATT["Battery pack"]
    ESTOP["Hardware E-stop\n(NC pushbutton relay)\nSTATUS: coverage of BOTH\nSabertooths NOT YET CONFIRMED"]
    PDB["Power distribution\n(main feed, after E-stop)"]

    BATT --> ESTOP --> PDB

    PI["Raspberry Pi Zero 2 W"]
    ESP["ESP32 DevKitC V4"]
    GAMEPAD["Xbox gamepad"]

    GAMEPAD -.USB.-> PI
    PI <--"USB serial, UART0\nGPIO1 TX / GPIO3 RX\n115200 baud"--> ESP

    SABF["Sabertooth 2x12 (FRONT)\nM1=front-left, M2=front-right\nDIP switches: baud NOT physically\nverified (assumed 9600 simplified serial)"]
    SABR["Sabertooth 2x12 (REAR)\nM1=rear-left, M2=rear-right\nNEW unit -- DIP switches NOT YET SET/VERIFIED"]

    ESP --"UART2 TX only, GPIO17\n9600 baud, simplified serial"--> SABF
    ESP --"UART1 TX only, GPIO19\n(remapped from default pins)\n9600 baud, simplified serial"--> SABR

    PDB --"main power feed"--> SABF
    PDB --"main power feed\n(own feed, not daisy-chained\noff FRONT's terminals)"--> SABR

    ESP =="common ground"== SABF
    ESP =="common ground"== SABR

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
1. **E-stop coverage of both Sabertooths — not yet confirmed.** If the
   E-stop relay's contacts only interrupt the original (FRONT) unit's
   feed, the rear axle keeps running when E-stop is pressed. This must
   be checked on the actual relay/power distribution wiring, not
   assumed from this diagram.
2. **REAR Sabertooth DIP switches — not yet set or verified.** The
   firmware assumes 9600 baud, simplified serial mode, same as the
   FRONT unit's assumed (also never directly verified) configuration.
3. **Common ground and independent power feed for the REAR unit** —
   shown above as a requirement, not yet confirmed done on the physical
   build.

See `rover/README.md`'s "Before this drives real motors" checklist —
these three items are listed there too; this diagram exists to make
them visually obvious at the point in the circuit they apply to.
