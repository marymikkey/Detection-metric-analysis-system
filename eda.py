#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import yaml
from PIL import Image


# =========================
# CONFIG
# =========================

INPUT_YAMLS = [
    "/home/src/dataset.yaml",
]

OUTPUT_ROOT = "/home/src/bd"

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

SMALL_AREA = 32 ** 2
MEDIUM_AREA = 96 ** 2

SHOOTING_CONDITIONS_FILENAME = "shooting_conditions.json"
TARGET_SPLIT = "test"


# =========================
# DATA STRUCTURES
# =========================

@dataclass
class SampleStat:
    image_path: str
    label_path: Optional[str]

    width: int
    height: int
    channels: int

    valid_objects: int
    broken_lines: int
    missing_label: bool

    bbox_widths: List[float]
    bbox_heights: List[float]
    bbox_areas: List[float]
    bbox_centers: List[List[float]]
    class_ids: List[int]

    intensity_hist: np.ndarray

    condition_tags: List[str] = field(default_factory=list)
    condition_sequence_id: Optional[str] = None


# =========================
# BASIC UTILS
# =========================

def load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if data is not None else {}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def safe_name(text: str) -> str:
    text = str(text).strip().replace("\\", "/")
    text = re.sub(r"[^\w\-.]+", "_", text, flags=re.UNICODE)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")[:180] if text else "dataset"


def to_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def resolve_path(raw_path: str, yaml_root: Optional[Path], yaml_path: Path) -> Path:
    path = Path(str(raw_path))

    if path.is_absolute():
        return path

    if yaml_root is not None:
        return (yaml_root / path).resolve()

    return (yaml_path.parent / path).resolve()


def list_images(img_dir: Path) -> List[Path]:
    return sorted(
        p for p in img_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMG_EXTS
    )


# =========================
# LABEL PATH RESOLUTION
# =========================

def find_label_path(img_path: Path, img_dir: Path) -> Path:
    """
    Main expected YOLO structure:
        .../test/images/xxx.jpg
        .../test/labels/xxx.txt

    Also works with nested image paths:
        .../test/images/seq/img.jpg
        .../test/labels/seq/img.txt
    """
    rel = img_path.relative_to(img_dir)

    candidates = [
        (img_dir.parent / "labels" / rel).with_suffix(".txt"),
        img_path.with_suffix(".txt"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


# =========================
# CONDITIONS METADATA
# =========================

def load_shooting_conditions(img_dir: Path) -> Tuple[Optional[Dict[str, Any]], Optional[Path]]:
    """
    Ищет shooting_conditions.json рядом с images, visible, sequence, test и выше.
    Подходит для структуры:
        test/<sequence>/visible/images
        test/shooting_conditions.json
        dataset_root/shooting_conditions.json
    """
    candidates = []

    cur = img_dir
    for _ in range(6):
        candidates.append(cur / SHOOTING_CONDITIONS_FILENAME)
        cur = cur.parent

    seen = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)

        if candidate.exists() and candidate.is_file():
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    return json.load(f), candidate
            except Exception:
                return None, candidate

    return None, None


def strip_frame_suffix(name: str) -> str:
    patterns = [
        r"(.+)_f\d+$",
        r"(.+)_frame\d+$",
        r"(.+)_img\d+$",
        r"(.+)[_\-]\d+$",
        r"(.+)frame\d+$",
    ]

    for pattern in patterns:
        match = re.match(pattern, name, flags=re.IGNORECASE)
        if match:
            candidate = match.group(1).strip("_-")
            if candidate:
                return candidate

    return name


def build_sequence_candidates(img_path: Path, img_dir: Path) -> List[str]:
    candidates = []

    # Для структуры:
    # .../test/<sequence>/visible/images/img.jpg
    # img_dir = .../<sequence>/visible/images
    candidates.append(img_dir.parent.parent.name)  # sequence name
    candidates.append(img_dir.parent.name)         # visible / infrared
    candidates.append(img_dir.name)                # images

    try:
        rel = img_path.relative_to(img_dir)

        if len(rel.parts) > 1:
            candidates.append(rel.parts[0])
            candidates.append(str(rel.parent).replace("\\", "/"))
    except Exception:
        pass

    candidates.append(img_path.parent.name)
    candidates.append(strip_frame_suffix(img_path.stem))
    candidates.append(img_path.stem)

    out = []
    seen = set()

    for candidate in candidates:
        candidate = str(candidate).strip()
        if candidate and candidate.lower() not in {"images", "visible", "infrared"} and candidate not in seen:
            out.append(candidate)
            seen.add(candidate)

    return out


def build_image_candidates(img_path: Path, img_dir: Path) -> List[str]:
    candidates = []

    try:
        rel = img_path.relative_to(img_dir)
        candidates.append(rel.as_posix())
        candidates.append(rel.name)
    except Exception:
        pass

    candidates.append(img_path.name)
    candidates.append(str(img_path))
    candidates.append(img_path.as_posix())

    out = []
    seen = set()

    for candidate in candidates:
        candidate = str(candidate).strip()
        if candidate and candidate not in seen:
            out.append(candidate)
            seen.add(candidate)

    return out


def normalize_tags(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, str):
        raw_tags = [value]
    elif isinstance(value, list):
        raw_tags = value
    else:
        return []

    return [str(tag).strip() for tag in raw_tags if str(tag).strip()]


def get_condition_tags(
    img_path: Path,
    img_dir: Path,
    metadata: Optional[Dict[str, Any]],
) -> Tuple[List[str], Optional[str]]:
    if not metadata:
        return [], None

    annotation_level = str(metadata.get("annotation_level", "")).strip().lower()

    if annotation_level == "image":
        images_map = metadata.get("images", {})
        if not isinstance(images_map, dict):
            return [], None

        for candidate in build_image_candidates(img_path, img_dir):
            if candidate in images_map:
                return normalize_tags(images_map[candidate]), None

    if annotation_level == "sequence":
        sequences_map = metadata.get("sequences", {})
        if not isinstance(sequences_map, dict):
            return [], None

        for candidate in build_sequence_candidates(img_path, img_dir):
            if candidate in sequences_map:
                return normalize_tags(sequences_map[candidate]), candidate

    return [], None


# =========================
# LABEL PARSING
# =========================

def parse_yolo_label(
    label_path: Path,
    img_width: int,
    img_height: int,
) -> Tuple[int, int, List[float], List[float], List[float], List[List[float]], List[int]]:
    valid_objects = 0
    broken_lines = 0

    bbox_widths = []
    bbox_heights = []
    bbox_areas = []
    bbox_centers = []
    class_ids = []

    if not label_path.exists():
        return valid_objects, broken_lines, bbox_widths, bbox_heights, bbox_areas, bbox_centers, class_ids

    try:
        lines = label_path.read_text(encoding="utf-8").strip().splitlines()
    except Exception:
        return 0, 1, bbox_widths, bbox_heights, bbox_areas, bbox_centers, class_ids

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split()

        if len(parts) < 5:
            broken_lines += 1
            continue

        try:
            cls = int(float(parts[0]))
            xc = float(parts[1])
            yc = float(parts[2])
            w = float(parts[3])
            h = float(parts[4])
        except Exception:
            broken_lines += 1
            continue

        if not (0.0 <= xc <= 1.0 and 0.0 <= yc <= 1.0):
            broken_lines += 1
            continue

        if not (0.0 < w <= 1.0 and 0.0 < h <= 1.0):
            broken_lines += 1
            continue

        bw = w * img_width
        bh = h * img_height
        area = bw * bh

        valid_objects += 1
        bbox_widths.append(bw)
        bbox_heights.append(bh)
        bbox_areas.append(area)
        bbox_centers.append([xc, yc])
        class_ids.append(cls)

    return valid_objects, broken_lines, bbox_widths, bbox_heights, bbox_areas, bbox_centers, class_ids


# =========================
# IMAGE ANALYSIS
# =========================

def analyze_image(
    img_path: Path,
    img_dir: Path,
    conditions_metadata: Optional[Dict[str, Any]],
) -> SampleStat:
    label_path = find_label_path(img_path, img_dir)
    condition_tags, sequence_id = get_condition_tags(img_path, img_dir, conditions_metadata)

    with Image.open(img_path) as img:
        width, height = img.size
        channels = len(img.getbands())

        gray = np.array(img.convert("L"))
        intensity_hist, _ = np.histogram(gray, bins=256, range=(0, 256))

    (
        valid_objects,
        broken_lines,
        bbox_widths,
        bbox_heights,
        bbox_areas,
        bbox_centers,
        class_ids,
    ) = parse_yolo_label(label_path, width, height)

    return SampleStat(
        image_path=str(img_path),
        label_path=str(label_path) if label_path.exists() else None,

        width=width,
        height=height,
        channels=channels,

        valid_objects=valid_objects,
        broken_lines=broken_lines,
        missing_label=not label_path.exists(),

        bbox_widths=bbox_widths,
        bbox_heights=bbox_heights,
        bbox_areas=bbox_areas,
        bbox_centers=bbox_centers,
        class_ids=class_ids,

        intensity_hist=intensity_hist,

        condition_tags=condition_tags,
        condition_sequence_id=sequence_id,
    )


# =========================
# AGGREGATION
# =========================

def aggregate(samples: List[SampleStat], class_names: Dict[int, str], nc: Optional[int]) -> Dict[str, Any]:
    total_images = len(samples)
    total_objects = sum(s.valid_objects for s in samples)
    total_broken = sum(s.broken_lines for s in samples)
    
    # Background classification:
    # - missing_label: label file doesn't exist -> background
    # - empty_label_files: label exists but empty -> background  
    # - only_broken: label has only broken lines -> corrupted (NOT background)
    # - background_images: only missing + empty
    total_missing = sum(1 for s in samples if s.missing_label)
    empty_label_files = sum(
        1 for s in samples
        if (not s.missing_label) and s.valid_objects == 0 and s.broken_lines == 0
    )
    only_broken = sum(
        1 for s in samples
        if (not s.missing_label) and s.valid_objects == 0 and s.broken_lines > 0
    )
    background_images = total_missing + empty_label_files  # только missing + empty

    objects_per_image = [s.valid_objects for s in samples]

    bbox_widths = [x for s in samples for x in s.bbox_widths]
    bbox_heights = [x for s in samples for x in s.bbox_heights]
    bbox_areas = [x for s in samples for x in s.bbox_areas]
    bbox_centers = [x for s in samples for x in s.bbox_centers]
    class_ids = [x for s in samples for x in s.class_ids]

    resolutions = Counter(f"{s.width}x{s.height}" for s in samples)
    channels = Counter(s.channels for s in samples)
    objects_per_image_distribution = Counter(objects_per_image)

    small = sum(1 for area in bbox_areas if area < SMALL_AREA)
    medium = sum(1 for area in bbox_areas if SMALL_AREA <= area < MEDIUM_AREA)
    large = sum(1 for area in bbox_areas if area >= MEDIUM_AREA)

    intensity_hist = np.zeros(256, dtype=np.int64)
    for sample in samples:
        intensity_hist += sample.intensity_hist.astype(np.int64)

    condition_by_image = Counter()
    images_with_conditions = 0

    for sample in samples:
        if sample.condition_tags:
            images_with_conditions += 1
            for tag in set(sample.condition_tags):
                condition_by_image[tag] += 1

    sequence_to_tags: Dict[str, set] = defaultdict(set)

    for sample in samples:
        if sample.condition_sequence_id and sample.condition_tags:
            sequence_to_tags[sample.condition_sequence_id].update(sample.condition_tags)

    condition_by_sequence = Counter()
    for tags in sequence_to_tags.values():
        for tag in tags:
            condition_by_sequence[tag] += 1

    return {
        "images_total": total_images,
        "objects_total": total_objects,

        "broken_label_lines": total_broken,
        "missing_label_files": total_missing,
        "empty_label_files": empty_label_files,
        "only_broken_label_files": only_broken,
        "corrupted_label_images": only_broken,  # ← алиас для GUI
        "background_images": background_images,
        "background_definition": "Background = missing labels + empty labels (no valid objects). Corrupted label files (only broken lines) are NOT counted as background.",
        "nc": nc,
        "class_names": {str(k): v for k, v in class_names.items()},
        "class_distribution": {str(k): v for k, v in Counter(class_ids).items()},

        "channels": {str(k): v for k, v in channels.items()},
        "resolutions": dict(resolutions),
        "unified_channels": len(channels) == 1,
        "unified_resolution": len(resolutions) == 1,

        "objects_per_image": objects_per_image,
        "objects_per_image_distribution": {
            str(k): v for k, v in sorted(objects_per_image_distribution.items())
        },
        "min_objects_per_image": min(objects_per_image) if objects_per_image else 0,
        "max_objects_per_image": max(objects_per_image) if objects_per_image else 0,

        "bbox_widths": bbox_widths,
        "bbox_heights": bbox_heights,
        "bbox_areas": bbox_areas,
        "bbox_centers": bbox_centers,

        "small_count": small,
        "medium_count": medium,
        "large_count": large,

        "intensity_histogram": intensity_hist.tolist(),

        "condition_metadata_present": False,
        "images_with_conditions": images_with_conditions,
        "condition_by_image": dict(condition_by_image),
        "sequences_with_conditions": len(sequence_to_tags),
        "condition_by_sequence": dict(condition_by_sequence),

        "plot_data": {
            "objects_per_image_distribution": [
                {"objects": int(k), "images": int(v)}
                for k, v in sorted(objects_per_image_distribution.items())
            ],
            "object_size_distribution": [
                {"size": "small", "count": small},
                {"size": "medium", "count": medium},
                {"size": "large", "count": large},
            ],
            "resolution_distribution": [
                {"resolution": k, "count": v}
                for k, v in resolutions.items()
            ],
            "class_distribution": [
                {
                    "class_id": int(k),
                    "class_name": class_names.get(int(k), f"class_{k}"),
                    "count": int(v),
                }
                for k, v in Counter(class_ids).items()
            ],
            "condition_distribution_by_image": [
                {"condition": k, "count": v}
                for k, v in condition_by_image.items()
            ],
            "condition_distribution_by_sequence": [
                {"condition": k, "count": v}
                for k, v in condition_by_sequence.items()
            ],
            "intensity_histogram": [
                {"intensity": i, "count": int(count)}
                for i, count in enumerate(intensity_hist.tolist())
            ],
            "bbox_centers": [
                {"x": float(x), "y": float(y)}
                for x, y in bbox_centers
            ],
            "bbox_areas": [
                {"area": float(area)}
                for area in bbox_areas
            ],
            "background_stats": {
                "missing_label_files": total_missing,
                "empty_label_files": empty_label_files,
                "only_broken_label_files": only_broken,
                "corrupted_label_images": only_broken,  # ← алиас
                "total_background": background_images,
                "percentage": round((background_images / total_images) * 100, 2) if total_images > 0 else 0,
            }
        },
    }


# =========================
# YAML PROCESSING
# =========================

def normalize_names(names_raw: Any) -> Dict[int, str]:
    if names_raw is None:
        return {}

    if isinstance(names_raw, dict):
        result = {}
        for key, value in names_raw.items():
            try:
                result[int(key)] = str(value)
            except Exception:
                continue
        return result

    if isinstance(names_raw, list):
        return {i: str(name) for i, name in enumerate(names_raw)}

    return {}


def process_dataset_yaml(yaml_path: Path, out_root: Path) -> None:
    print(f"\n[INFO] Processing dataset YAML: {yaml_path}")

    yaml_data = load_yaml(yaml_path)

    test_entries = to_list(yaml_data.get(TARGET_SPLIT))
    if not test_entries:
        raise ValueError(f"No '{TARGET_SPLIT}' split found in YAML: {yaml_path}")

    yaml_root = Path(yaml_data["path"]).resolve() if yaml_data.get("path") else None

    dataset_name = str(yaml_data.get("name", yaml_path.stem))
    dataset_safe_name = safe_name(dataset_name)

    class_names = normalize_names(yaml_data.get("names"))
    nc = yaml_data.get("nc")

    all_samples: List[SampleStat] = []
    analyzed_dirs = []
    condition_source_files = set()

    for raw_entry in test_entries:
        img_dir = resolve_path(str(raw_entry), yaml_root, yaml_path)

        if not img_dir.exists():
            print(f"[WARN] Test image directory not found: {img_dir}")
            continue

        if not img_dir.is_dir():
            print(f"[WARN] Test entry is not a directory: {img_dir}")
            continue

        conditions_metadata, conditions_path = load_shooting_conditions(img_dir)
        if conditions_path is not None:
            condition_source_files.add(str(conditions_path))

        images = list_images(img_dir)
        print(f"[INFO] {img_dir}: {len(images)} images")

        analyzed_dirs.append(str(img_dir))

        for img_path in images:
            try:
                sample = analyze_image(
                    img_path=img_path,
                    img_dir=img_dir,
                    conditions_metadata=conditions_metadata,
                )
                all_samples.append(sample)
            except Exception as exc:
                print(f"[WARN] Failed to analyze {img_path}: {exc}")

    if not all_samples:
        raise RuntimeError(f"No images analyzed from YAML: {yaml_path}")

    stats = aggregate(all_samples, class_names=class_names, nc=nc)
    stats["condition_metadata_present"] = len(condition_source_files) > 0

    stats["dataset_name"] = dataset_name
    stats["dataset_yaml_name"] = yaml_path.name
    stats["dataset_yaml_path"] = str(yaml_path)
    stats["target_split"] = TARGET_SPLIT
    stats["analyzed_image_dirs"] = analyzed_dirs
    stats["condition_source_files"] = sorted(condition_source_files)
    stats["generation_time"] = datetime.now().isoformat(timespec="seconds")
    stats["small_area_threshold"] = SMALL_AREA
    stats["medium_area_threshold"] = MEDIUM_AREA

    out_dir = out_root / dataset_safe_name
    ensure_dir(out_dir)

    out_path = out_dir / "stats.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"[OK] Saved: {out_path}")
    print(f"  Images: {stats['images_total']}")
    print(f"  Objects: {stats['objects_total']}")
    print(f"  Missing labels: {stats['missing_label_files']}")
    print(f"  Empty label files: {stats['empty_label_files']}")
    print(f"  Only broken labels: {stats['only_broken_label_files']}")
    print(f"  Background images: {stats['background_images']} ({stats['plot_data']['background_stats']['percentage']}%)")
    print(f"  Broken label lines: {stats['broken_label_lines']}")


# =========================
# CLI
# =========================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EDA for YOLO dataset YAML files. Only the test split is analyzed."
    )

    parser.add_argument(
        "--yaml",
        type=str,
        default=None,
        help="Path to one YOLO dataset YAML",
    )

    parser.add_argument(
        "--yamls",
        nargs="+",
        default=None,
        help="Paths to one or more YOLO dataset YAML files",
    )

    parser.add_argument(
        "--output-root",
        type=str,
        default=OUTPUT_ROOT,
        help="Directory where JSON reports will be saved",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.yaml:
        yaml_paths = [Path(args.yaml).resolve()]
    elif args.yamls:
        yaml_paths = [Path(p).resolve() for p in args.yamls]
    else:
        yaml_paths = [Path(p).resolve() for p in INPUT_YAMLS]

    out_root = Path(args.output_root).resolve()
    ensure_dir(out_root)

    for yaml_path in yaml_paths:
        if not yaml_path.exists():
            print(f"[ERROR] YAML not found: {yaml_path}")
            continue

        try:
            process_dataset_yaml(yaml_path, out_root)
        except Exception as exc:
            print(f"[ERROR] Failed to process {yaml_path}: {exc}")


if __name__ == "__main__":
    main()
