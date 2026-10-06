"""Exact rational state; explicit decimal display/float metric boundaries."""

from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction


def text_money(value: Fraction | None) -> str | None:
    if value is None:
        return None
    with localcontext() as context:
        context.prec = 76
        context.rounding = ROUND_HALF_EVEN
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def rational(value: Fraction) -> str:
    # Decimal's exact integer conversion avoids Python's int/string digit limit;
    # long exact replays can legitimately accumulate large rational denominators.
    return f"{Decimal(value.numerator)}/{Decimal(value.denominator)}"


def parse_rational(value: str) -> Fraction:
    numerator, denominator = value.split("/")
    return Fraction(Decimal(numerator)) / Fraction(Decimal(denominator))
