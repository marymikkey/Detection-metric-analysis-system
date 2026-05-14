#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional


# =========================================================
# CONFIG
# =========================================================

# mask bits order:
# FP FN LOW_IOU LOW_CONF DUPLICATE
MASK_ORDER = [
    "FP",
    "FN",
    "LOW_IOU",
    "LOW_CONF",
    "DUPLICATE",
]

ERROR_META = {
    "FP": {
        "label": "False Positive",
        "short_label": "FP",
        "color": "#f87171",
        "description": "False positive detection",
        "line_style": "solid",
    },
    "FN": {
        "label": "False Negative",
        "short_label": "FN",
        "color": "#fbbf24",
        "description": "Missed object",
        "line_style": "solid",
    },
    "LOW_IOU": {
        "label": "Low IoU",
        "short_label": "LOW_IOU",
        "color": "#38bdf8",
        "description": "Poor localization",
        "line_style": "solid",
    },
    "LOW_CONF": {
        "label": "Low Confidence",
        "short_label": "LOW_CONF",
        "color": "#a78bfa",
        "description": "Low confidence prediction",
        "line_style": "solid",
    },
    "DUPLICATE": {
        "label": "Duplicate",
        "short_label": "DUP",
        "color": "#4ade80",
        "description": "Duplicate prediction",
        "line_style": "solid",
    },
    "GT": {
        "label": "Ground Truth",
        "short_label": "GT",
        "color": "#22c55e",
        "description": "Ground truth annotation",
        "line_style": "dashed",   # ← ВОТ ЭТО ДЛЯ ПУНКТИРА
    },
}


# =========================================================
# IO
# =========================================================

def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
        )


# =========================================================
# MASK DECODER
# =========================================================

def decode_mask(mask: str) -> Dict[str, bool]:
    """
    Example:
        10010

    means:
        FP=True
        FN=False
        LOW_IOU=False
        LOW_CONF=True
        DUPLICATE=False
    """

    mask = str(mask).strip()

    decoded = {}

    for i, error_type in enumerate(MASK_ORDER):
        decoded[error_type] = (
            i < len(mask)
            and mask[i] == "1"
        )

    return decoded


# =========================================================
# IMAGE URL CONVERTER
# =========================================================

def make_image_url(
    image_path: str,
    image_root_fs: Optional[str],
    image_url_prefix: Optional[str],
) -> str:
    """
    Converts filesystem path → browser URL

    Example:
        FS:
            /mnt/datasets/test/images/a.jpg

        URL:
            /api/images/test/images/a.jpg
    """

    if not image_root_fs or not image_url_prefix:
        return image_path

    img = Path(image_path).resolve()
    root = Path(image_root_fs).resolve()

    try:
        rel = img.relative_to(root)

        return (
            f"{image_url_prefix.rstrip('/')}"
            f"/{rel.as_posix()}"
        )

    except ValueError:
        return image_path


# =========================================================
# ERROR NORMALIZATION
# =========================================================

def format_error_text(error: Dict[str, Any]) -> str:
    error_type = error.get("type", "UNKNOWN")

    if error_type == "LOW_CONF":
        conf = error.get("confidence")

        if conf is not None:
            return f"LOW_CONF conf={conf:.3f}"

    if error_type == "LOW_IOU":
        iou = error.get("iou")

        if iou is not None:
            return f"LOW_IOU IoU={iou:.3f}"

    return error_type


def normalize_error(
    error: Dict[str, Any],
    idx: int,
) -> Dict[str, Any]:

    error_type = error.get("type", "UNKNOWN")

    meta = ERROR_META.get(
        error_type,
        {
            "label": error_type,
            "short_label": error_type,
            "color": "#ffffff",
            "description": "Unknown error type",
            "line_style": "solid",
        },
    )

    bbox = error.get("bbox")

    if bbox is None or len(bbox) != 4:
        raise ValueError(
            f"Invalid bbox in error:\n{error}"
        )

    x, y, w, h = bbox

    out = {
        "id": idx,

        "type": error_type,

        "label": meta["label"],
        "short_label": meta["short_label"],

        "color": meta["color"],

        "description": meta["description"],

        "line_style": meta["line_style"],

        "text": format_error_text(error),

        "bbox": {
            "x": float(x),
            "y": float(y),
            "w": float(w),
            "h": float(h),
        },

        "raw_bbox": [
            float(x),
            float(y),
            float(w),
            float(h),
        ],
    }

    if "confidence" in error:
        out["confidence"] = float(
            error["confidence"]
        )

    if "iou" in error:
        out["iou"] = float(
            error["iou"]
        )

    return out


# =========================================================
# IMAGE ITEM NORMALIZATION
# =========================================================

def normalize_item(
    item: Dict[str, Any],
    image_root_fs: Optional[str],
    image_url_prefix: Optional[str],
) -> Dict[str, Any]:

    image_path = item.get("image_path")

    if not image_path:
        raise ValueError(
            f"No image_path in item:\n{item}"
        )

    raw_errors = item.get("errors", [])

    normalized_errors = [
        normalize_error(error, idx=i)
        for i, error in enumerate(raw_errors)
    ]

    error_types = sorted(
        set(
            error["type"]
            for error in normalized_errors
        )
    )

    return {
        "image_id": item.get("image_id"),

        "image_path": image_path,

        "image_url": make_image_url(
            image_path=image_path,
            image_root_fs=image_root_fs,
            image_url_prefix=image_url_prefix,
        ),

        "file_name": Path(image_path).name,

        "mask": str(item.get("mask", "")),

        "mask_decoded": decode_mask(
            str(item.get("mask", ""))
        ),

        "error_types": error_types,

        "errors_count": len(normalized_errors),

        "errors": normalized_errors,
    }


# =========================================================
# SUMMARY
# =========================================================

def build_summary(
    items: List[Dict[str, Any]]
) -> Dict[str, Any]:

    error_counter = Counter()
    image_counter_by_type = Counter()

    for item in items:

        image_types = set()

        for error in item["errors"]:

            error_type = error["type"]

            error_counter[error_type] += 1

            image_types.add(error_type)

        for error_type in image_types:
            image_counter_by_type[error_type] += 1

    return {
        "images_with_errors": len(items),

        "total_errors": sum(
            error_counter.values()
        ),

        "errors_by_box": dict(error_counter),

        "errors_by_image": dict(
            image_counter_by_type
        ),

        "available_error_types": [
            error_type
            for error_type in (
                MASK_ORDER + ["GT"]
            )
            if (
                error_counter.get(error_type, 0) > 0
                or image_counter_by_type.get(error_type, 0) > 0
            )
        ],
    }


# =========================================================
# PAYLOAD BUILDER
# =========================================================

def build_frontend_payload(
    raw_data: List[Dict[str, Any]],
    image_root_fs: Optional[str],
    image_url_prefix: Optional[str],
) -> Dict[str, Any]:

    items = [
        normalize_item(
            item=item,
            image_root_fs=image_root_fs,
            image_url_prefix=image_url_prefix,
        )
        for item in raw_data
    ]

    return {
        "schema_version": "1.0",

        "mask_order": MASK_ORDER,

        "legend": ERROR_META,

        "summary": build_summary(items),

        "items": items,
    }


# =========================================================
# CLI
# =========================================================

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "Prepare detector errors JSON "
            "for frontend visualization"
        )
    )

    parser.add_argument(
        "--errors-json",
        required=True,
        help="Path to raw backend JSON",
    )

    parser.add_argument(
        "--output-json",
        required=True,
        help="Where to save frontend JSON",
    )

    parser.add_argument(
        "--image-root-fs",
        default=None,
        help="Filesystem root for images",
    )

    parser.add_argument(
        "--image-url-prefix",
        default=None,
        help="Browser URL prefix",
    )

    return parser.parse_args()


# =========================================================
# MAIN
# =========================================================

def main() -> None:

    args = parse_args()

    raw_path = Path(
        args.errors_json
    ).resolve()

    out_path = Path(
        args.output_json
    ).resolve()

    raw_data = load_json(raw_path)

    if not isinstance(raw_data, list):
        raise ValueError(
            "Input JSON must be a list"
        )

    payload = build_frontend_payload(
        raw_data=raw_data,
        image_root_fs=args.image_root_fs,
        image_url_prefix=args.image_url_prefix,
    )

    save_json(out_path, payload)

    print()
    print("=" * 60)
    print("[OK] Frontend JSON generated")
    print("=" * 60)

    print(
        f"Input JSON:  {raw_path}"
    )

    print(
        f"Output JSON: {out_path}"
    )

    print()

    print(
        f"Images with errors: "
        f"{payload['summary']['images_with_errors']}"
    )

    print(
        f"Total errors: "
        f"{payload['summary']['total_errors']}"
    )

    print()

    print("Errors by type:")

    for k, v in payload["summary"][
        "errors_by_box"
    ].items():

        print(f"  {k:<12} {v}")

    print("=" * 60)
    print()


if __name__ == "__main__":
    main()