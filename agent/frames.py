"""Perceptual fingerprints for screenshots, used to detect a user idling on one screen to farm points.

A difference hash survives the small changes an unchanged screen still produces between
captures (a blinking cursor, re-encoding noise), which an exact byte comparison would not.
"""
import io

from PIL import Image, UnidentifiedImageError

HASH_SIZE = 16
# Out of HASH_SIZE * HASH_SIZE = 256 bits. A scroll, new page or playing video moves far more bits.
SAME_FRAME_MAX_DISTANCE = 6


def frame_fingerprint(image_bytes: bytes) -> str | None:
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            small = img.convert("L").resize((HASH_SIZE + 1, HASH_SIZE), Image.Resampling.LANCZOS)
            pixels = small.tobytes()  # one byte per pixel in mode L
    except (UnidentifiedImageError, OSError, ValueError):
        return None

    bits = 0
    for row in range(HASH_SIZE):
        offset = row * (HASH_SIZE + 1)
        for col in range(HASH_SIZE):
            bits = (bits << 1) | (pixels[offset + col] > pixels[offset + col + 1])
    return f"{bits:0{HASH_SIZE * HASH_SIZE // 4}x}"


def is_same_frame(fingerprint: str | None, previous: str | None) -> bool:
    if not fingerprint or not previous or len(fingerprint) != len(previous):
        return False
    distance = bin(int(fingerprint, 16) ^ int(previous, 16)).count("1")
    return distance <= SAME_FRAME_MAX_DISTANCE
