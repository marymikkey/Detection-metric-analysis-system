"""Тестируется fmt()"""
import math

import pytest

from eval_all_coco import fmt


@pytest.mark.parametrize("value", [None, -1, -0.5, -100])
def test_fmt_returns_dash_for_negative_or_none(value):
    assert fmt(value) == "-"


@pytest.mark.parametrize(
    "value, expected",
    [
        (0,           "0.0000"),
        (1,           "1.0000"),
        (0.123456,    "0.1235"),
        (0.99995,     "1.0000"),
        (0.0001,      "0.0001"),
    ],
)
def test_fmt_formats_positive_to_four_decimals(value, expected):
    assert fmt(value) == expected


def test_fmt_handles_float_zero_explicitly():
    assert fmt(0.0) == "0.0000"


def test_fmt_does_not_lose_precision_below_threshold():
    assert fmt(1e-9) == "0.0000"
    assert fmt(1e-9) != "-"
