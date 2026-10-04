"""
test_protocol.py
Unit tests for protocol.py. Run with: python3 -m pytest test_protocol.py
(or just `python3 test_protocol.py` -- no pytest dependency required,
see the __main__ block).

These exist because the protocol's correctness (checksum, signed-byte
encoding, resync behavior) is exactly the kind of thing that's easy to
get subtly wrong and hard to notice by eye -- and it's safety-adjacent
(a corrupted drive frame should never produce an uncommanded motor
move). Worth real test coverage, not just manual spot-checks.
"""
import struct

from protocol import (
    encode_drive_frame,
    stop_frame,
    TelemetryFrameParser,
    SYNC_DRIVE,
    SYNC_TELEMETRY,
)


def test_drive_frame_roundtrip():
    cases = [
        (0, 0, 255),
        (100, 100, 255),
        (-100, -100, 90),
        (50, -50, 0),
        (127, -127, 255),  # out-of-range input, must clamp to +/-100
    ]
    for left, right, servo in cases:
        frame = encode_drive_frame(left, right, servo)
        assert len(frame) == 5
        assert frame[0] == SYNC_DRIVE
        assert frame[4] == sum(frame[1:4]) & 0xFF, f"checksum wrong for {(left, right, servo)}"

        decoded_left, decoded_right, decoded_servo = struct.unpack("<bbB", frame[1:4])
        expected_left = max(-100, min(100, left))
        expected_right = max(-100, min(100, right))
        assert decoded_left == expected_left
        assert decoded_right == expected_right
        assert decoded_servo == (servo if servo == 255 else max(0, min(180, servo)))


def test_stop_frame_is_zero_zero_nochange():
    assert stop_frame() == encode_drive_frame(0, 0, 255)


def test_telemetry_parses_valid_frame():
    soil_raw = 2048
    status = 0x01
    payload = bytes([(soil_raw >> 8) & 0xFF, soil_raw & 0xFF, status])
    checksum = sum(payload) & 0xFF
    frame = bytes([SYNC_TELEMETRY]) + payload + bytes([checksum])

    parser = TelemetryFrameParser()
    results = parser.feed_bytes(frame)
    assert len(results) == 1
    assert results[0]["soil_raw"] == soil_raw
    assert results[0]["watchdog_tripped"] is True


def test_telemetry_rejects_corrupted_checksum():
    soil_raw = 1000
    payload = bytes([(soil_raw >> 8) & 0xFF, soil_raw & 0xFF, 0x00])
    checksum = sum(payload) & 0xFF
    frame = bytearray([SYNC_TELEMETRY]) + bytearray(payload) + bytearray([checksum])
    frame[1] ^= 0xFF  # corrupt soil_high after computing a valid checksum for the original

    parser = TelemetryFrameParser()
    results = parser.feed_bytes(bytes(frame))
    assert results == []


def test_telemetry_resyncs_within_one_frame_cycle_after_embedded_sync_byte():
    """
    A stray SYNC_TELEMETRY byte sitting inside preceding garbage can eat
    into (desync) the very next real frame -- PROTOCOL.md documents this
    explicitly and guarantees recovery by the frame after that, not
    necessarily the one the garbage collided with. This test checks the
    guarantee as documented, not a stronger one.
    """
    soil_raw = 2048
    payload = bytes([(soil_raw >> 8) & 0xFF, soil_raw & 0xFF, 0x00])
    checksum = sum(payload) & 0xFF
    good_frame = bytes([SYNC_TELEMETRY]) + payload + bytes([checksum])

    garbage_with_embedded_sync = bytes([0x01, 0x02, SYNC_TELEMETRY, 0x03])
    stream = garbage_with_embedded_sync + good_frame + good_frame

    parser = TelemetryFrameParser()
    results = parser.feed_bytes(stream)
    assert any(r["soil_raw"] == soil_raw for r in results)


def test_telemetry_byte_at_a_time_matches_bulk_feed():
    """Confirms the state machine works fed one byte per call, not just via feed_bytes."""
    soil_raw = 3000
    payload = bytes([(soil_raw >> 8) & 0xFF, soil_raw & 0xFF, 0x00])
    checksum = sum(payload) & 0xFF
    frame = bytes([SYNC_TELEMETRY]) + payload + bytes([checksum])

    parser = TelemetryFrameParser()
    result = None
    for b in frame:
        r = parser.feed(b)
        if r is not None:
            result = r
    assert result is not None
    assert result["soil_raw"] == soil_raw


if __name__ == "__main__":
    # Lightweight runner so this works without pytest installed.
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL: {t.__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    if failures:
        raise SystemExit(1)
