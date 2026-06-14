"""
Rug pricing utility.

Rules:
  - Base rate: $39 / sqft
  - New Zealand Wool or Silk: $49 / sqft
  - Final price always ends in $9  (e.g. 159, 199, 319 ...)
  - Size can be entered as feet  ("5x8 feet", "5x8 ft", "5 x 8")
    or centimetres               ("150x240 cm", "150 x 240 cm")
  - Minimum size: 3x3 ft (9 sqft)
"""

import math
import re

PREMIUM_MATERIALS = {"new zealand wool", "silk"}

BASE_RATE_PER_SQFT = 39       # USD
PREMIUM_RATE_PER_SQFT = 49    # USD


def _parse_dimensions(size_str: str) -> tuple[float, float, str]:
    """
    Parse a size string and return (dim1, dim2, unit).

    Accepted formats (case-insensitive):
        "5x8 feet"   "5 x 8 ft"   "5x8"
        "150x240 cm" "150 x 240 cm"

    Returns unit as 'ft' or 'cm'.
    Raises ValueError on bad input.
    """
    s = size_str.strip().lower()

    # Detect unit
    if "cm" in s:
        unit = "cm"
    else:
        unit = "ft"   # default / feet / ft

    # Extract two numbers
    nums = re.findall(r"[\d]+(?:\.[\d]+)?", s)
    if len(nums) < 2:
        raise ValueError(
            f"Could not parse size '{size_str}'. "
            "Expected format like '5x8 feet' or '150x240 cm'."
        )

    d1, d2 = float(nums[0]), float(nums[1])
    return d1, d2, unit


def parse_size_to_sqft(size_str: str) -> float:
    """Return area in square feet for a given size string."""
    d1, d2, unit = _parse_dimensions(size_str)

    if unit == "cm":
        # Convert cm → feet  (1 ft = 30.48 cm)
        d1 = d1 / 30.48
        d2 = d2 / 30.48

    return d1 * d2


def validate_minimum_size(size_str: str) -> None:
    """
    Raise ValueError if either dimension is under 3 ft (or 91.44 cm).
    """
    d1, d2, unit = _parse_dimensions(size_str)

    if unit == "cm":
        min_dim = 91.0    # ~3 ft (91.44 cm exactly, we round down to be lenient)
        unit_label = "cm"
    else:
        min_dim = 3.0
        unit_label = "ft"

    if d1 < min_dim or d2 < min_dim:
        raise ValueError(
            f"Minimum rug size is 3x3 ft (91x91 cm). "
            f"Got {d1:.0f}x{d2:.0f} {unit_label}."
        )


def _round_to_x9(price: float) -> int:
    """
    Round price so it always ends in 9.
    E.g. 312 → 319,  319 → 319,  320 → 329.
    """
    floored = math.floor(price)
    # Find the nearest $X9 >= floored
    remainder = floored % 10
    if remainder <= 9:
        base = floored - remainder
    else:
        base = floored - remainder + 10

    candidate = base + 9
    if candidate < price:
        candidate += 10

    return int(candidate)


def calculate_price(size_str: str, material: str) -> dict:
    """
    Return a dict with:
        sqft        – area in square feet (float)
        rate        – rate used per sqft (int)
        raw_price   – sqft * rate before rounding (float)
        price       – final price ending in $9 (int)
        currency    – 'USD'
        is_premium  – bool (True for NZ Wool / Silk)
    """
    sqft = parse_size_to_sqft(size_str)
    is_premium = material.strip().lower() in PREMIUM_MATERIALS
    rate = PREMIUM_RATE_PER_SQFT if is_premium else BASE_RATE_PER_SQFT
    raw = sqft * rate
    price = _round_to_x9(raw)

    return {
        "sqft": round(sqft, 2),
        "rate": rate,
        "raw_price": round(raw, 2),
        "price": price,
        "currency": "USD",
        "is_premium": is_premium,
    }