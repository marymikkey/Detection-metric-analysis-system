"""Тестируется count_objects_by_size().
small  = [0, 32**2),
medium = [32**2, 96**2),
large  = [96**2, +inf).
"""
from types import SimpleNamespace

import pytest

from eval_all_coco import count_objects_by_size


def _fake_coco(areas):
    return SimpleNamespace(dataset={"annotations": [{"area": a} for a in areas]})


def test_buckets_split_correctly():
    coco_gt = _fake_coco([
        100,           # small
        1023.99,       # small
        1024,          # medium
        5000,          # medium
        9215.99,       # medium
        9216,          # large
        100_000,       # large
    ])

    counts, ranges, avg_area = count_objects_by_size(coco_gt)

    assert counts == {"small": 2, "medium": 3, "large": 2}
    assert ranges == {
        "small":  (0,       32 ** 2),
        "medium": (32 ** 2, 96 ** 2),
        "large":  (96 ** 2, 1e12),
    }
    # 100, 1023.99 => small
    assert avg_area["small"] == pytest.approx((100 + 1023.99) / 2)
    # 1024, 5000, 9215.99 => medium
    assert avg_area["medium"] == pytest.approx((1024 + 5000 + 9215.99) / 3)
    # 9216, 100000 => large
    assert avg_area["large"] == pytest.approx((9216 + 100_000) / 2)


def test_empty_dataset_yields_none_avg_and_zero_counts():
    coco_gt = _fake_coco([])

    counts, _, avg_area = count_objects_by_size(coco_gt)

    assert counts == {"small": 0, "medium": 0, "large": 0}
    assert avg_area == {"small": None, "medium": None, "large": None}


def test_custom_area_ranges_are_respected():
    coco_gt = _fake_coco([10, 50, 100, 500, 1000])
    custom = {"tiny": (0, 100), "huge": (100, 1e9)}

    counts, ranges, avg_area = count_objects_by_size(coco_gt, area_ranges=custom)

    assert counts == {"tiny": 2, "huge": 3}
    assert ranges == custom
    assert avg_area["tiny"] == pytest.approx((10 + 50) / 2)
    assert avg_area["huge"] == pytest.approx((100 + 500 + 1000) / 3)


def test_object_outside_all_ranges_is_dropped():
    coco_gt = _fake_coco([2000])
    custom = {"a": (0, 100), "b": (100, 1000)}

    counts, _, avg_area = count_objects_by_size(coco_gt, area_ranges=custom)

    assert counts == {"a": 0, "b": 0}
    assert avg_area == {"a": None, "b": None}
