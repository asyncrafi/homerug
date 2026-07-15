"""
Rug pricing utility.

Rules:
  - Tufted Wool: $30 / sqft
  - Knotted Wool: $55 / sqft
  - New Zealand Wool or Silk: $49 / sqft
  - Other materials: $39 / sqft
  - Final price always ends in .99
  - Size can be entered as feet  ("5x8 feet", "5x8 ft", "5 x 8")
    or centimetres               ("150x240 cm", "150 x 240 cm")
  - Minimum size: 3x3 ft (9 sqft)
"""

import math
import re

PREMIUM_MATERIALS = set()  # no longer used — every material has its own flat rate now

RATE_BY_MATERIAL = {
    "moroccan shaggy wool": 30,
    "hand tufted new zealand wool": 30,
    "hand-knotted new zealand wool": 55,
    "hand-knotted silk": 85,
    "cotton (dhurrie)": 30,
    "jute": 25,
    "printed synthetic": 15,
}

DEFAULT_RATE_PER_SQFT = 30  # fallback only, shouldn't normally be hit now that every material has an explicit rate


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
    Raise ValueError if either dimension is under 2 ft (or 61 cm).
    """
    d1, d2, unit = _parse_dimensions(size_str)

    if unit == "cm":
        min_dim = 61.0    # ~2 ft (60.96 cm exactly, rounded down to be lenient)
        unit_label = "cm"
    else:
        min_dim = 2.0
        unit_label = "ft"

    if d1 < min_dim or d2 < min_dim:
        raise ValueError(
            f"Minimum rug size is 2x2 ft (61x61 cm). "
            f"Got {d1:.0f}x{d2:.0f} {unit_label}."
        )


def _round_to_x99(price: float) -> float:
    """
    Round price so it always ends in .99.
    E.g. 312.00 → 312.99, 312.40 → 312.99, 312.99 → 312.99.
    """
    floored = math.floor(price)
    candidate = floored + 0.99
    if candidate < price:
        candidate = floored + 10 + 0.99
    return round(candidate, 2)


def calculate_price(size_str: str, material: str) -> dict:
    sqft = parse_size_to_sqft(size_str)
    material_key = material.strip().lower()
    rate = RATE_BY_MATERIAL.get(material_key, DEFAULT_RATE_PER_SQFT)
    raw = sqft * rate
    price = _round_to_x99(raw)

    return {
        "sqft": round(sqft, 2),
        "rate": rate,
        "raw_price": round(raw, 2),
        "price": price,
        "currency": "USD",
    }