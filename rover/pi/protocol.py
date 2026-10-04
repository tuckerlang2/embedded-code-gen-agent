"""
protocol.py
Encodes drive frames and parses telemetry frames for the Pi<->ESP32 link.
Implements ../PROTOCOL.md exactly -- if you change a value there, change
it here and in esp32_firmware.ino, by hand. Nothing auto-syncs these.
"""
import struct

SYNC_DRIVE = 0xAA
SYNC_TELEMETRY = 0xBB
FRAME_LEN = 5  # sync + 3 payload bytes + checksum

NO_SERVO_CHANGE = 255


def encode_drive_frame(left_speed: int, right_speed: int, servo_cmd: int = NO_SERVO_CHANGE) -> bytes:
    """
    Builds a 5-byte drive frame. left_speed/right_speed are clamped to
    -100..100. servo_cmd is 0-180, or NO_SERVO_CHANGE (255) to leave the
    probe servo where it is.
    """
    left = max(-100, min(100, int(left_speed)))
    right = max(-100, min(100, int(right_speed)))
    if servo_cmd != NO_SERVO_CHANGE:
        servo_cmd = max(0, min(180, int(servo_cmd)))

    # '<bbB' = little-endian int8, int8, uint8 -- matches the ESP32's
    # int8_t, int8_t, uint8_t reading of frame[1..3].
    payload = struct.pack("<bbB", left, right, servo_cmd)
    checksum = sum(payload) & 0xFF
    return bytes([SYNC_DRIVE]) + payload + bytes([checksum])


def stop_frame() -> bytes:
    """Convenience: a drive frame commanding zero speed, no servo change."""
    return encode_drive_frame(0, 0, NO_SERVO_CHANGE)


class TelemetryFrameParser:
    """
    Byte-at-a-time state machine for ESP32->Pi telemetry frames, mirroring
    the ESP32 firmware's own drive-frame parser (see PROTOCOL.md's
    "Resync behavior" note -- same reasoning applies here in reverse).
    Feed it bytes one at a time via `feed()`; it returns a parsed dict
    when a complete, checksum-valid frame is assembled, else None.
    """

    WAIT_SYNC = "wait_sync"
    READ_PAYLOAD = "read_payload"

    def __init__(self):
        self._state = self.WAIT_SYNC
        self._buf = bytearray(FRAME_LEN)
        self._idx = 0

    def feed(self, byte: int):
        if self._state == self.WAIT_SYNC:
            if byte == SYNC_TELEMETRY:
                self._buf[0] = byte
                self._idx = 1
                self._state = self.READ_PAYLOAD
            return None

        # READ_PAYLOAD
        self._buf[self._idx] = byte
        self._idx += 1
        if self._idx < FRAME_LEN:
            return None

        self._state = self.WAIT_SYNC
        self._idx = 0
        expected_checksum = sum(self._buf[1:4]) & 0xFF
        if self._buf[4] != expected_checksum:
            return None  # discard silently, same reasoning as firmware side

        soil_raw = (self._buf[1] << 8) | self._buf[2]
        status_flags = self._buf[3]
        return {
            "soil_raw": soil_raw,              # 0-4095
            "watchdog_tripped": bool(status_flags & 0x01),
        }

    def feed_bytes(self, data: bytes):
        """Feeds multiple bytes at once; returns a list of parsed frames (may be empty)."""
        results = []
        for b in data:
            result = self.feed(b)
            if result is not None:
                results.append(result)
        return results
