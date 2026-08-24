"""Frozen pseudo-random algorithm and bounded-reduction contracts.

These pure helpers mirror the ca65 runtime and make the compatibility vectors
and rejection arithmetic independently testable.  They are compiler-side only;
generated ROMs do not contain Python support.
"""

from __future__ import annotations


LFSR16_XOR_MASK = 0xB400
LFSR16_PERIOD = 0xFFFF
ZERO_SEED_STATE = 0xACE1


def seed_to_state(seed: int) -> int:
    """Expand one public byte to the frozen nonzero 16-bit state."""

    if not 0 <= seed <= 0xFF:
        raise ValueError("random seed must be a byte")
    return ZERO_SEED_STATE if seed == 0 else (seed << 8) | seed


def automatic_seed_state(frame: int, controller_1: int = 0, controller_2: int = 0) -> int:
    """Mirror one-time runtime mixing for the cleared-RAM pending marker."""

    for value in (frame, controller_1, controller_2):
        if not 0 <= value <= 0xFF:
            raise ValueError("automatic seed inputs must be bytes")
    mixed = frame ^ controller_1 ^ controller_2
    return ((mixed ^ 0xAC) << 8) | (mixed ^ 0xE1)


def lfsr16_step(state: int) -> int:
    """Advance the right-shifting maximal 16-bit Galois LFSR once."""

    if not 1 <= state <= 0xFFFF:
        raise ValueError("LFSR state must be a nonzero 16-bit value")
    shifted = state >> 1
    if state & 1:
        shifted ^= LFSR16_XOR_MASK
    return shifted


def random_byte_from_state(state: int) -> tuple[int, int]:
    """Return ``(new_state, low_byte_output)`` after exactly one step."""

    new_state = lfsr16_step(state)
    return new_state, new_state & 0xFF


def rejection_cutoff(span: int) -> int:
    """Lowest accepted byte for a uniform inclusive-range reduction."""

    if not 1 <= span <= 0x100:
        raise ValueError("range span must be between 1 and 256")
    return 0 if span == 0x100 else 0x100 % span


def reduce_accepted_byte(source: int, span: int) -> int | None:
    """Map one byte uniformly to ``0..span-1``, or reject it."""

    if not 0 <= source <= 0xFF:
        raise ValueError("random source must be a byte")
    cutoff = rejection_cutoff(span)
    if source < cutoff:
        return None
    return (source - cutoff) % span
