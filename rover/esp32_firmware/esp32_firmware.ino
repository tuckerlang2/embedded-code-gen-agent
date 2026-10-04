/*
 * esp32_firmware.ino
 *
 * Real-time I/O co-processor firmware for the yard-monitoring rover.
 * Runs on an ESP32 DevKitC V4. Responsibilities:
 *   - Receive drive commands from the Pi over USB serial (UART0) and
 *     relay them to a Sabertooth 2x12 motor controller over a single TTL
 *     serial line (Sabertooth "simplified serial" mode).
 *   - Read a capacitive soil moisture probe on the native ADC.
 *   - Drive the probe-actuation servo.
 *   - Enforce a watchdog: if the Pi stops sending valid commands, force
 *     the drivetrain to stop, independent of anything the Pi does.
 *
 * Pin choices and all electrical facts below are grounded in
 * hardware_reference/esp32_devkitc_v4.md in the repo root (two levels up)
 * — do not change a pin assignment here without checking that doc first.
 *
 * Protocol (frame format, baud rates, timeout values) is defined in
 * ../PROTOCOL.md. This file and that doc must be kept in sync by hand.
 *
 * External library dependency: ESP32Servo (install via Arduino Library
 * Manager — search "ESP32Servo" by Kevin Harrington / madhephaestus).
 * Plain Servo.h is not ESP32-compatible; ESP32Servo provides a
 * compatible API backed by the ESP32's LEDC PWM peripheral.
 */

#include <ESP32Servo.h>

// ---------------------------------------------------------------------
// Pin assignments (see hardware_reference/esp32_devkitc_v4.md)
// ---------------------------------------------------------------------
// UART0 (GPIO1 TX / GPIO3 RX) is the default `Serial` object, wired to
// the onboard USB-serial bridge -> this is the link to the Pi. Don't
// reassign these pins to anything else.
#define PI_SERIAL_BAUD 115200

// UART2, used here as the Sabertooth link. TX only -- Sabertooth
// simplified serial is receive-only, so Serial2's RX pin (GPIO16) is
// wired but unused.
#define SABERTOOTH_TX_PIN 17
#define SABERTOOTH_RX_PIN 16  // unused, Sabertooth doesn't talk back
// ASSUMPTION, confirm against the Sabertooth's actual DIP switch
// setting before first use: simplified serial baud rates are selectable
// via onboard DIP switches (common options: 2400/9600/19200/38400).
// 9600 is the Sabertooth factory default for simplified serial mode.
#define SABERTOOTH_BAUD 9600

// ADC1 channel (safe to use alongside WiFi, though this project doesn't
// use WiFi on the ESP32 side). Input-only pin, no conflicts.
#define SOIL_PROBE_PIN 34

// PWM-safe GPIO, not a strapping pin, not in use by UART2/I2C/SPI above.
#define SERVO_PIN 13

// ---------------------------------------------------------------------
// Protocol constants -- MUST match ../PROTOCOL.md exactly.
// ---------------------------------------------------------------------
#define DRIVE_FRAME_SYNC 0xAA
#define TELEMETRY_FRAME_SYNC 0xBB
#define FRAME_LEN 5  // sync + 3 payload bytes + checksum

#define WATCHDOG_TIMEOUT_MS 400
#define TELEMETRY_INTERVAL_MS 200

// ---------------------------------------------------------------------
// Sabertooth simplified serial constants.
// Motor 1: 1-127 (1=full reverse, 64=stop, 127=full forward)
// Motor 2: 128-255 (128=full reverse, 192=stop, 255=full forward)
// Byte value 0 is reserved (autobaud character) -- never send it.
// ---------------------------------------------------------------------
#define SABERTOOTH_M1_STOP 64
#define SABERTOOTH_M2_STOP 192

Servo probeServo;

// Frame-parser state (byte-at-a-time state machine, see PROTOCOL.md's
// "Resync behavior" note for why this doesn't just blindly trust SYNC).
enum ParseState { WAIT_SYNC, READ_PAYLOAD };
ParseState parseState = WAIT_SYNC;
uint8_t frameBuf[FRAME_LEN];
uint8_t frameIdx = 0;

unsigned long lastValidFrameMillis = 0;
unsigned long lastTelemetryMillis = 0;
bool watchdogTripped = false;

// Last commanded servo angle, so we only call probeServo.write() when it
// actually changes (servo_cmd == 255 means "no change" per protocol).
int lastServoAngle = -1;

void setup() {
  Serial.begin(PI_SERIAL_BAUD);
  Serial2.begin(SABERTOOTH_BAUD, SERIAL_8N1, SABERTOOTH_RX_PIN, SABERTOOTH_TX_PIN);

  analogReadResolution(12);                       // 0-4095, explicit rather than relying on core default
  analogSetPinAttenuation(SOIL_PROBE_PIN, ADC_11db); // full ~0-3.3V input range

  probeServo.setPeriodHertz(50);                  // standard analog servo frame rate
  probeServo.attach(SERVO_PIN);

  // Force a known-safe state immediately on boot, before any frame has
  // arrived -- same code path the watchdog uses later.
  sendSabertoothStop();
  lastValidFrameMillis = millis();  // don't immediately read as "timed out" at t=0
}

void loop() {
  readIncomingFrames();
  enforceWatchdog();
  sendTelemetryIfDue();
}

// ---------------------------------------------------------------------
// Drive-frame reception from the Pi
// ---------------------------------------------------------------------
void readIncomingFrames() {
  while (Serial.available() > 0) {
    uint8_t b = (uint8_t)Serial.read();

    if (parseState == WAIT_SYNC) {
      if (b == DRIVE_FRAME_SYNC) {
        frameBuf[0] = b;
        frameIdx = 1;
        parseState = READ_PAYLOAD;
      }
      // else: not a sync byte, keep scanning
    } else {  // READ_PAYLOAD
      frameBuf[frameIdx++] = b;
      if (frameIdx >= FRAME_LEN) {
        uint8_t expectedChecksum = (uint8_t)(frameBuf[1] + frameBuf[2] + frameBuf[3]);
        if (frameBuf[4] == expectedChecksum) {
          handleValidDriveFrame(frameBuf);
        }
        // Checksum mismatch: silently discard. We do not log every
        // garbled frame over Serial -- that channel is the protocol
        // link itself, and interleaving debug text would corrupt
        // framing for whoever's parsing it next (the Pi). This is a
        // deliberate silence, not an oversight.
        frameIdx = 0;
        parseState = WAIT_SYNC;
      }
    }
  }
}

void handleValidDriveFrame(uint8_t *frame) {
  int8_t leftSpeed = (int8_t)frame[1];    // -100..100
  int8_t rightSpeed = (int8_t)frame[2];   // -100..100
  uint8_t servoCmd = frame[3];            // 0-180, or 255 = no change

  leftSpeed = constrain(leftSpeed, -100, 100);
  rightSpeed = constrain(rightSpeed, -100, 100);

  sendSabertoothDrive(leftSpeed, rightSpeed);

  if (servoCmd != 255 && servoCmd <= 180 && servoCmd != lastServoAngle) {
    probeServo.write(servoCmd);
    lastServoAngle = servoCmd;
  }

  lastValidFrameMillis = millis();
  watchdogTripped = false;
}

// ---------------------------------------------------------------------
// Watchdog -- the actual safety mechanism. See PROTOCOL.md.
// ---------------------------------------------------------------------
void enforceWatchdog() {
  if (millis() - lastValidFrameMillis > WATCHDOG_TIMEOUT_MS) {
    sendSabertoothStop();
    watchdogTripped = true;
    // Deliberately do NOT reset lastValidFrameMillis here -- doing so
    // would make this a one-shot stop instead of a held stop. We want
    // sendSabertoothStop() to keep firing every loop iteration until a
    // genuinely new valid frame arrives and updates the timestamp itself.
  }
}

// ---------------------------------------------------------------------
// Sabertooth simplified-serial output
// ---------------------------------------------------------------------
void sendSabertoothDrive(int8_t leftPercent, int8_t rightPercent) {
  uint8_t m1 = (uint8_t)map(leftPercent, -100, 100, 1, 127);
  uint8_t m2 = (uint8_t)map(rightPercent, -100, 100, 128, 255);

  // map() truncates; force exact, clean stop bytes when the commanded
  // speed is exactly zero rather than accepting whatever off-by-one
  // map() produces near the midpoint. Precision elsewhere doesn't
  // matter at yard-mowing speeds; the stop command being exact does.
  if (leftPercent == 0) m1 = SABERTOOTH_M1_STOP;
  if (rightPercent == 0) m2 = SABERTOOTH_M2_STOP;

  m1 = constrain(m1, 1, 127);
  m2 = constrain(m2, 128, 255);

  Serial2.write(m1);
  Serial2.write(m2);
}

void sendSabertoothStop() {
  Serial2.write((uint8_t)SABERTOOTH_M1_STOP);
  Serial2.write((uint8_t)SABERTOOTH_M2_STOP);
}

// ---------------------------------------------------------------------
// Telemetry to the Pi
// ---------------------------------------------------------------------
void sendTelemetryIfDue() {
  unsigned long now = millis();
  if (now - lastTelemetryMillis < TELEMETRY_INTERVAL_MS) return;
  lastTelemetryMillis = now;

  uint16_t soilRaw = analogRead(SOIL_PROBE_PIN);  // 0-4095
  uint8_t soilHigh = (uint8_t)((soilRaw >> 8) & 0xFF);
  uint8_t soilLow = (uint8_t)(soilRaw & 0xFF);
  uint8_t statusFlags = watchdogTripped ? 0x01 : 0x00;
  uint8_t checksum = (uint8_t)(soilHigh + soilLow + statusFlags);

  Serial.write((uint8_t)TELEMETRY_FRAME_SYNC);
  Serial.write(soilHigh);
  Serial.write(soilLow);
  Serial.write(statusFlags);
  Serial.write(checksum);
}
