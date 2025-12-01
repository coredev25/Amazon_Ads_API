"""Utility functions for consistent percent/decimal conversions (#25)."""

from __future__ import annotations


def decimal_to_percentage(value: float) -> float:
    """
    Convert decimal fraction (0.05) to whole percentage (5.0).
    """
    return float(value or 0) * 100.0


def percentage_to_decimal(value: float) -> float:
    """
    Convert whole percentage (5.0) to decimal fraction (0.05).
    """
    return float(value or 0) / 100.0

