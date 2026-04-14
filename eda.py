#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import matplotlib.pyplot as plt
import numpy as np
import yaml
from PIL import Image


# USER CONFIG

INPUT_YAMLS = [
    "/home/src/diploma/train/configs/ir_cfg.yaml",
]

OUTPUT_ROOT = "/home/src/bd"

# False -> split is determined by YAML / selected_splits
# True  -> split is determined by dataset path
USE_PATH_SPLIT_INFERENCE = False

# Optional outputs
SAVE_JSON = True
SAVE_MARKDOWN = True
SAVE_PLOTS = True

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
SPLIT_NAMES = ("train", "val", "test", "valid")
CANONICAL_SPLITS = ("train", "val", "test")

SMALL_AREA = 32 ** 2
MEDIUM_AREA = 96 ** 2

DEFAULT_CONDITION_LABELS = ("day", "night", "blur", "overexposed", "low_visibility")
SHOOTING_CONDITIONS_FILENAME = "shooting_conditions.json"


# DATA STRUCTURES
@dataclass
class SampleStat:
    image_path: Path
    label_path: Optional[Path]
    split_name: str
    width: int
    height: int
    channels: int
    yaml_split: Optional[str] = None
    path_split: Optional[str] = None
    valid_objects: int = 0
    broken_label_lines: int = 0
    missing_label_file: bool = False
    intensity_hist_256: Optional[np.ndarray] = None
    rgb_hists_256: Optional[np.ndarray] = None
    bbox_widths_px: List[float] = field(default_factory=list)
    bbox_heights_px: List[float] = field(default_factory=list)
    bbox_areas_px: List[float] = field(default_factory=list)
    bbox_centers_xy: List[Tuple[float, float]] = field(default_factory=list)
    class_ids: List[int] = field(default_factory=list)

    dataset_name: str = ""
    dataset_yaml_name: str = ""

    condition_tags: List[str] = field(default_factory=list)
    condition_annotation_level: Optional[str] = None
    condition_source_file: Optional[str] = None
    condition_sequence_id: Optional[str] = None


@dataclass
class DatasetGroup:
    group_key: str
    dataset_name: str
    split_entries: Dict[str, List[Tuple[Path, Path, str, Optional[str], str]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    yaml_name: str = ""
    class_names: Dict[int, str] = field(default_factory=dict)
    nc: Optional[int] = None


@dataclass
class DatasetRunSpec:
    yaml_path: Path
    selected_splits: List[str]


# UTILS
def utc3_now_str() -> str:
    tz = timezone(timedelta(hours=3))
    return datetime.now(tz).strftime("%H:%M %d.%m.%Y UTC+3")


def utc3_now_compact_str() -> str:
    tz = timezone(timedelta(hours=3))
    return datetime.now(tz).strftime("%H%M_%d_%m_%Y")


def safe_name(text: str) -> str:
    text = text.strip().replace("\\", "/")
    text = re.sub(r"[^\w\-.]+", "_", text, flags=re.UNICODE)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")[:180] if text else "dataset"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def normalize_names(names_raw) -> Dict[int, str]:
    if names_raw is None:
        return {}
    if isinstance(names_raw, dict):
        out = {}
        for k, v in names_raw.items():
            try:
                out[int(k)] = str(v)
            except Exception:
                continue
        return out
    if isinstance(names_raw, list):
        return {i: str(v) for i, v in enumerate(names_raw)}
    return {}


def load_yaml(yaml_path: Path) -> dict:
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if data is not None else {}


def to_list(v) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def resolve_entry_path(raw_entry: str, yaml_root_path: Optional[Path], yaml_file_path: Path) -> Path:
    p = Path(str(raw_entry))
    if p.is_absolute():
        return p
    if yaml_root_path is not None:
        return (yaml_root_path / p).resolve()
    return (yaml_file_path.parent / p).resolve()


def canonicalize_split(split_name: Optional[str]) -> Optional[str]:
    if split_name is None:
        return None
    s = split_name.lower()
    if s == "valid":
        return "val"
    if s in ("train", "val", "test"):
        return s
    return s


def normalize_selected_splits(raw_splits: Optional[List[str]]) -> List[str]:
    if raw_splits is None:
        raise ValueError("selected_splits is required")

    out = []
    for s in raw_splits:
        c = canonicalize_split(s)
        if c in CANONICAL_SPLITS and c not in out:
            out.append(c)

    if not out:
        raise ValueError("selected_splits must contain at least one of: train, val, test")

    return out


def infer_split_from_path(path: Path) -> Optional[str]:
    parts = [p.lower() for p in path.parts]

    for part in parts:
        if part == "train":
            return "train"
        if part in ("val", "valid"):
            return "val"
        if part == "test":
            return "test"

    last = path.name.lower()

    m = re.match(r"^(train|val|valid|test)([_\-].+)$", last)
    if m:
        return canonicalize_split(m.group(1))

    m = re.match(r"^(.+)([_\-])(train|val|valid|test)$", last)
    if m:
        return canonicalize_split(m.group(3))

    return None


def normalize_dataset_group_root(path: Path) -> Path:
    parts = list(path.parts)

    if parts and parts[-1].lower() == "images":
        parts = parts[:-1]

    if not parts:
        return path

    lowered = [p.lower() for p in parts]

    if lowered and lowered[-1] in SPLIT_NAMES:
        return Path(*parts[:-1])

    if len(parts) >= 2 and lowered[-2] in SPLIT_NAMES:
        new_parts = parts[:-2] + [parts[-1]]
        return Path(*new_parts)

    leaf = parts[-1]
    leaf_low = leaf.lower()

    m = re.match(r"^(train|val|valid|test)([_\-])(.+)$", leaf_low)
    if m:
        suffix = m.group(3)
        if suffix:
            return Path(*parts[:-1], suffix)
        return Path(*parts[:-1])

    m = re.match(r"^(.+)([_\-])(train|val|valid|test)$", leaf_low)
    if m:
        prefix = m.group(1)
        if prefix:
            return Path(*parts[:-1], prefix)
        return Path(*parts[:-1])

    return Path(*parts)


def derive_dataset_name(group_root: Path) -> str:
    parts = group_root.parts
    if len(parts) >= 3:
        return safe_name("_".join(parts[-3:]))
    if len(parts) >= 2:
        return safe_name("_".join(parts[-2:]))
    return safe_name(group_root.name)


def resolve_image_label_dirs(entry_path: Path) -> Tuple[Path, Path]:
    p = entry_path

    if p.name.lower() == "images":
        img_dir = p
        lbl_dir = p.parent / "labels"
        if lbl_dir.exists():
            return img_dir, lbl_dir

    if (p / "images").exists() and (p / "labels").exists():
        return p / "images", p / "labels"

    if p.name.lower() in SPLIT_NAMES and (p / "images").exists():
        if (p / "labels").exists():
            return p / "images", p / "labels"

    if p.name.lower() in SPLIT_NAMES and (p.parent / "labels" / p.name).exists():
        return p, p.parent / "labels" / p.name

    if p.exists() and p.is_dir():
        has_images = any(f.suffix.lower() in IMG_EXTS for f in p.iterdir() if f.is_file())
        if has_images:
            if (p.parent / "labels").exists():
                return p, p.parent / "labels"
            if p.name.lower() in SPLIT_NAMES and (p.parent / "labels" / p.name).exists():
                return p, p.parent / "labels" / p.name

    raise FileNotFoundError(f"Cannot determine images/labels for path: {entry_path}")


def list_images(img_dir: Path) -> List[Path]:
    return sorted([p for p in img_dir.rglob("*") if p.is_file() and p.suffix.lower() in IMG_EXTS])


def relative_label_path(img_path: Path, img_dir: Path, label_dir: Path) -> Path:
    rel = img_path.relative_to(img_dir)
    return (label_dir / rel).with_suffix(".txt")


def resolution_label(width: int, height: int) -> str:
    return f"{width}x{height}"


def pct(part: int, total: int) -> float:
    return 0.0 if total == 0 else 100.0 * part / total


def format_count_pct(part: int, total: int) -> str:
    return f"{part} ({pct(part, total):.2f}%)"


# CONDITIONS METADATA HELPERS
def normalize_condition_tags(raw_tags: Any) -> List[str]:
    if raw_tags is None:
        return []
    if isinstance(raw_tags, str):
        tags = [raw_tags]
    elif isinstance(raw_tags, list):
        tags = [str(x) for x in raw_tags]
    else:
        return []

    out = []
    for t in tags:
        t = str(t).strip()
        if t:
            out.append(t)
    return out


def load_json_file(json_path: Path) -> Optional[dict]:
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def find_conditions_json_near_dir(img_dir: Path) -> Optional[Path]:
    candidates = []

    p = img_dir
    candidates.append(p.parent / SHOOTING_CONDITIONS_FILENAME)
    if p.parent.parent != p.parent:
        candidates.append(p.parent.parent / SHOOTING_CONDITIONS_FILENAME)

    cur = p
    for _ in range(5):
        cur = cur.parent
        candidates.append(cur / SHOOTING_CONDITIONS_FILENAME)

    seen = set()
    uniq_candidates = []
    for c in candidates:
        try:
            rc = str(c.resolve())
        except Exception:
            rc = str(c)
        if rc not in seen:
            uniq_candidates.append(c)
            seen.add(rc)

    for c in uniq_candidates:
        if c.exists() and c.is_file():
            return c

    return None


def strip_frame_suffix(name: str) -> str:
    patterns = [
        r"(.+)_f\d+$",
        r"(.+)_frame\d+$",
        r"(.+)_img\d+$",
        r"(.+)[_\-]\d+$",
        r"(.+)frame\d+$",
    ]
    for pat in patterns:
        m = re.match(pat, name, flags=re.IGNORECASE)
        if m:
            candidate = m.group(1).strip("_-")
            if candidate:
                return candidate
    return name


def build_sequence_candidates(img_path: Path, img_dir: Path) -> List[str]:
    candidates = []

    if img_dir.name.lower() == "images":
        if img_dir.parent.parent != img_dir.parent:
            candidates.append(img_dir.parent.parent.name)
        candidates.append(img_dir.parent.name)

    try:
        rel = img_path.relative_to(img_dir)
        rel_parent = str(rel.parent).replace("\\", "/")
        if rel_parent and rel_parent != ".":
            first_part = rel.parts[0] if len(rel.parts) > 1 else ""
            if first_part:
                candidates.append(first_part)
            candidates.append(rel_parent)
    except Exception:
        pass

    candidates.append(strip_frame_suffix(img_path.stem))
    candidates.append(img_path.parent.name)
    if img_path.parent.parent != img_path.parent:
        candidates.append(img_path.parent.parent.name)

    out = []
    seen = set()
    for c in candidates:
        c = str(c).strip()
        if c and c not in seen:
            out.append(c)
            seen.add(c)
    return out


def build_image_candidates(img_path: Path, img_dir: Path) -> List[str]:
    candidates = []

    try:
        rel = img_path.relative_to(img_dir)
        rel_posix = rel.as_posix()
        candidates.append(rel_posix)
        candidates.append(rel.name)
    except Exception:
        pass

    candidates.append(img_path.name)
    candidates.append(str(img_path))
    candidates.append(img_path.as_posix())

    out = []
    seen = set()
    for c in candidates:
        c = str(c).strip()
        if c and c not in seen:
            out.append(c)
            seen.add(c)
    return out


def apply_conditions_metadata_to_sample(
    sample: SampleStat,
    img_dir: Path,
    metadata: Optional[dict],
    metadata_path: Optional[Path],
) -> None:
    if metadata is None or metadata_path is None:
        return

    sample.condition_source_file = str(metadata_path)

    annotation_level = str(metadata.get("annotation_level", "")).strip().lower()
    sample.condition_annotation_level = annotation_level if annotation_level else None

    if annotation_level == "sequence":
        sequences_map = metadata.get("sequences", {})
        if not isinstance(sequences_map, dict):
            return

        for candidate in build_sequence_candidates(sample.image_path, img_dir):
            if candidate in sequences_map:
                sample.condition_sequence_id = candidate
                sample.condition_tags = normalize_condition_tags(sequences_map[candidate])
                return

    elif annotation_level == "image":
        images_map = metadata.get("images", {})
        if not isinstance(images_map, dict):
            return

        for candidate in build_image_candidates(sample.image_path, img_dir):
            if candidate in images_map:
                sample.condition_tags = normalize_condition_tags(images_map[candidate])
                return

        seq_candidates = build_sequence_candidates(sample.image_path, img_dir)
        if seq_candidates:
            sample.condition_sequence_id = seq_candidates[0]


def collect_condition_labels_from_metadata(sample_stats: List[SampleStat]) -> List[str]:
    found = set()
    for s in sample_stats:
        for t in s.condition_tags:
            if t:
                found.add(t)

    ordered = [x for x in DEFAULT_CONDITION_LABELS if x in found]
    extras = sorted(found - set(DEFAULT_CONDITION_LABELS))
    if ordered or extras:
        return ordered + extras
    return list(DEFAULT_CONDITION_LABELS)


# INPUT YAML PARSING
def is_run_yaml(data: dict) -> bool:
    return isinstance(data, dict) and "datasets" in data and isinstance(data["datasets"], list)


def is_dataset_yaml(data: dict) -> bool:
    return any(k in data for k in ("train", "val", "valid", "test"))


def parse_run_yaml(run_yaml_path: Path) -> List[DatasetRunSpec]:
    data = load_yaml(run_yaml_path)
    if not is_run_yaml(data):
        raise ValueError(f"Input YAML must be a Run YAML with 'datasets' list: {run_yaml_path}")

    specs: List[DatasetRunSpec] = []
    for item in data.get("datasets", []):
        if not isinstance(item, dict):
            continue

        yaml_path_raw = item.get("yaml_path")
        if not yaml_path_raw:
            continue

        yaml_path = Path(str(yaml_path_raw))
        if not yaml_path.is_absolute():
            yaml_path = (run_yaml_path.parent / yaml_path).resolve()

        selected_splits = normalize_selected_splits(item.get("selected_splits"))
        specs.append(DatasetRunSpec(yaml_path=yaml_path, selected_splits=selected_splits))

    return specs


def get_target_yaml_keys(selected_splits: List[str]) -> List[str]:
    keys = []
    for s in selected_splits:
        if s == "val":
            keys.extend(["val", "valid"])
        else:
            keys.append(s)

    out = []
    for k in keys:
        if k not in out:
            out.append(k)
    return out


# PARSING / ANALYSIS
def parse_yolo_label_file(
    label_path: Path,
    img_w: int,
    img_h: int,
) -> Tuple[int, int, List[float], List[float], List[float], List[Tuple[float, float]], List[int]]:
    valid_objects = 0
    broken_lines = 0
    widths_px = []
    heights_px = []
    areas_px = []
    centers = []
    class_ids = []

    if not label_path.exists():
        return 0, 0, widths_px, heights_px, areas_px, centers, class_ids

    try:
        lines = label_path.read_text(encoding="utf-8").strip().splitlines()
    except Exception:
        return 0, 1, widths_px, heights_px, areas_px, centers, class_ids

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

        if not (0.0 <= xc <= 1.0 and 0.0 <= yc <= 1.0 and 0.0 <= w <= 1.0 and 0.0 <= h <= 1.0):
            broken_lines += 1
            continue

        if w <= 0.0 or h <= 0.0:
            broken_lines += 1
            continue

        bw = w * img_w
        bh = h * img_h
        area = bw * bh

        valid_objects += 1
        widths_px.append(bw)
        heights_px.append(bh)
        areas_px.append(area)
        centers.append((xc, yc))
        class_ids.append(cls)

    return valid_objects, broken_lines, widths_px, heights_px, areas_px, centers, class_ids


def image_channel_count_and_hist(img: Image.Image) -> Tuple[int, np.ndarray, Optional[np.ndarray]]:
    gray = img.convert("L")
    gray_np = np.array(gray)
    intensity_hist, _ = np.histogram(gray_np, bins=256, range=(0, 256))

    bands = img.getbands()
    channels = len(bands)

    rgb_hists = None
    if channels >= 3:
        rgb = img.convert("RGB")
        rgb_np = np.array(rgb)
        rgb_hists = []
        for ch in range(3):
            hist, _ = np.histogram(rgb_np[:, :, ch], bins=256, range=(0, 256))
            rgb_hists.append(hist)
        rgb_hists = np.stack(rgb_hists, axis=0)

    return channels, intensity_hist, rgb_hists


def analyze_image(
    img_path: Path,
    label_path: Path,
    split_name: str,
    dataset_name: str,
    dataset_yaml_name: str,
    yaml_split: Optional[str] = None,
    path_split: Optional[str] = None,
) -> SampleStat:
    with Image.open(img_path) as img:
        width, height = img.size
        channels, intensity_hist, rgb_hists = image_channel_count_and_hist(img)

    valid_objects, broken_label_lines, widths_px, heights_px, areas_px, centers, class_ids = parse_yolo_label_file(
        label_path, width, height
    )

    return SampleStat(
        image_path=img_path,
        label_path=label_path if label_path.exists() else None,
        split_name=split_name,
        width=width,
        height=height,
        channels=channels,
        yaml_split=yaml_split,
        path_split=path_split,
        valid_objects=valid_objects,
        broken_label_lines=broken_label_lines,
        missing_label_file=not label_path.exists(),
        intensity_hist_256=intensity_hist,
        rgb_hists_256=rgb_hists,
        bbox_widths_px=widths_px,
        bbox_heights_px=heights_px,
        bbox_areas_px=areas_px,
        bbox_centers_xy=centers,
        class_ids=class_ids,
        dataset_name=dataset_name,
        dataset_yaml_name=dataset_yaml_name,
    )


def aggregate_stats(sample_stats: List[SampleStat], class_names: Dict[int, str], nc: Optional[int]) -> dict:
    n_images = len(sample_stats)
    n_objects = sum(s.valid_objects for s in sample_stats)
    broken_label_lines = sum(s.broken_label_lines for s in sample_stats)
    missing_label_files = sum(1 for s in sample_stats if s.missing_label_file)
    backgrounds = sum(1 for s in sample_stats if s.valid_objects == 0)

    channels_counter = Counter(s.channels for s in sample_stats)
    resolutions_counter = Counter(resolution_label(s.width, s.height) for s in sample_stats)
    objects_per_image_counter = Counter(s.valid_objects for s in sample_stats)

    bbox_widths = [x for s in sample_stats for x in s.bbox_widths_px]
    bbox_heights = [x for s in sample_stats for x in s.bbox_heights_px]
    bbox_areas = [x for s in sample_stats for x in s.bbox_areas_px]
    centers = [xy for s in sample_stats for xy in s.bbox_centers_xy]
    class_ids = [c for s in sample_stats for c in s.class_ids]

    class_counter = Counter(class_ids)

    small = sum(1 for a in bbox_areas if a < SMALL_AREA)
    medium = sum(1 for a in bbox_areas if SMALL_AREA <= a < MEDIUM_AREA)
    large = sum(1 for a in bbox_areas if a >= MEDIUM_AREA)

    intensity_sum = None
    rgb_sum = None
    for s in sample_stats:
        if s.intensity_hist_256 is not None:
            intensity_sum = s.intensity_hist_256.copy() if intensity_sum is None else intensity_sum + s.intensity_hist_256
        if s.rgb_hists_256 is not None:
            rgb_sum = s.rgb_hists_256.copy() if rgb_sum is None else rgb_sum + s.rgb_hists_256

    unified_resolution = len(resolutions_counter) == 1
    unified_channels = len(channels_counter) == 1

    min_obj = min(objects_per_image_counter.keys()) if objects_per_image_counter else 0
    max_obj = max(objects_per_image_counter.keys()) if objects_per_image_counter else 0

    yaml_split_counter = Counter(s.yaml_split for s in sample_stats if s.yaml_split is not None)
    path_split_counter = Counter(s.path_split for s in sample_stats if s.path_split is not None)

    condition_labels = collect_condition_labels_from_metadata(sample_stats)
    condition_metadata_present = any(s.condition_source_file is not None for s in sample_stats)
    condition_annotation_levels = sorted(set(
        s.condition_annotation_level for s in sample_stats if s.condition_annotation_level
    ))
    condition_source_files = sorted(set(
        s.condition_source_file for s in sample_stats if s.condition_source_file
    ))

    condition_image_counter = Counter()
    images_with_condition_tags = 0

    for s in sample_stats:
        if s.condition_tags:
            images_with_condition_tags += 1
            for tag in set(s.condition_tags):
                condition_image_counter[tag] += 1

    sequence_to_tags: Dict[str, Set[str]] = defaultdict(set)
    for s in sample_stats:
        if s.condition_sequence_id and s.condition_tags:
            sequence_to_tags[s.condition_sequence_id].update(s.condition_tags)

    condition_sequence_counter = Counter()
    for _seq_id, tags in sequence_to_tags.items():
        for tag in tags:
            condition_sequence_counter[tag] += 1

    dataset_counter = Counter(s.dataset_name for s in sample_stats if s.dataset_name)

    return {
        "images_total": n_images,
        "objects_total": n_objects,
        "broken_label_lines": broken_label_lines,
        "missing_label_files": missing_label_files,
        "channels": {str(k): v for k, v in channels_counter.items()},
        "resolutions": dict(resolutions_counter),
        "unified_resolution": unified_resolution,
        "unified_channels": unified_channels,
        "objects_per_image": {str(k): v for k, v in objects_per_image_counter.items()},
        "background_images": backgrounds,
        "min_objects_per_image": min_obj,
        "max_objects_per_image": max_obj,
        "small_count": small,
        "medium_count": medium,
        "large_count": large,
        "class_distribution": {str(k): v for k, v in class_counter.items()},
        "class_names": {str(k): v for k, v in class_names.items()},
        "nc": nc,
        "yaml_splits": dict(yaml_split_counter),
        "path_splits": dict(path_split_counter),
        "datasets_included": dict(dataset_counter),

        "condition_metadata_present": condition_metadata_present,
        "condition_labels": condition_labels,
        "condition_annotation_levels": condition_annotation_levels,
        "condition_source_files": condition_source_files,
        "images_with_condition_tags": images_with_condition_tags,
        "condition_by_image": dict(condition_image_counter),
        "sequences_with_condition_tags": len(sequence_to_tags),
        "condition_by_sequence": dict(condition_sequence_counter),

        # Internal arrays for optional PNG generation
        "_intensity_hist": intensity_sum.tolist() if intensity_sum is not None else None,
        "_rgb_hist": rgb_sum.tolist() if rgb_sum is not None else None,
        "_bbox_widths": bbox_widths,
        "_bbox_heights": bbox_heights,
        "_bbox_areas": bbox_areas,
        "_bbox_centers": centers,
    }


# PLOTTING
def setup_ax(ax, title: str, xlabel: str = "", ylabel: str = ""):
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.7)
    ax.minorticks_on()


def save_objects_per_image_plot(counter: dict, out_path: Path, title: str):
    xs = sorted(int(k) for k in counter.keys())
    ys = [counter[str(x)] for x in xs]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(xs, ys, width=0.8)
    setup_ax(ax, title, "Objects per image", "Images count")
    ax.set_xticks(xs if len(xs) <= 30 else xs[::max(1, len(xs) // 20)])
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def save_bbox_wh_plot(widths: List[float], heights: List[float], out_path: Path, title: str):
    fig, axs = plt.subplots(1, 2, figsize=(14, 5))
    axs[0].hist(widths, bins=50)
    setup_ax(axs[0], f"{title} - width", "BBox width (px)", "Count")
    axs[1].hist(heights, bins=50)
    setup_ax(axs[1], f"{title} - height", "BBox height (px)", "Count")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def save_bbox_area_plot(areas: List[float], out_path: Path, title: str):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(areas, bins=60)
    setup_ax(ax, title, "BBox area (px^2)", "Count")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def save_bbox_centers_plot(centers: List[Tuple[float, float]], out_path: Path, title: str):
    fig, ax = plt.subplots(figsize=(7, 6))
    if centers:
        xs = [c[0] for c in centers]
        ys = [c[1] for c in centers]
        hb = ax.hexbin(xs, ys, gridsize=35, mincnt=1)
        fig.colorbar(hb, ax=ax, label="Count")
    setup_ax(ax, title, "X center (normalized)", "Y center (normalized)")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def save_resolutions_plot(resolutions_counter: dict, out_path: Path, title: str):
    items = sorted(resolutions_counter.items(), key=lambda x: -x[1])
    labels = [k for k, _ in items]
    counts = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(range(len(labels)), counts)
    setup_ax(ax, title, "Resolution", "Images count")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def save_intensity_plot(hist256: List[int], out_path: Path, title: str):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(np.arange(256), hist256)
    setup_ax(ax, title, "Intensity", "Pixels count")
    ax.set_xlim(0, 255)
    ax.set_xticks(range(0, 256, 10))
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def save_rgb_plot(rgb_hist: List[List[int]], out_path: Path, title: str):
    fig, ax = plt.subplots(figsize=(10, 6))
    labels = ["R", "G", "B"]
    for i in range(3):
        ax.plot(np.arange(256), rgb_hist[i], label=labels[i])
    setup_ax(ax, title, "Value", "Pixels count")
    ax.set_xlim(0, 255)
    ax.set_xticks(range(0, 256, 10))
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def save_conditions_plot(counter: dict, labels: List[str], out_path: Path, title: str, x_label: str):
    if not labels:
        return

    values = [counter.get(lbl, 0) for lbl in labels]

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.bar(range(len(labels)), values)
    setup_ax(ax, title, x_label, "Count")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=25, ha="right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def generate_plots(stats: dict, out_dir: Path, prefix: str):
    if not SAVE_PLOTS:
        return

    ensure_dir(out_dir)

    save_objects_per_image_plot(
        stats["objects_per_image"],
        out_dir / f"{prefix}_objects_per_image.png",
        f"{prefix}: objects per image",
    )

    if stats.get("_bbox_widths") and stats.get("_bbox_heights"):
        save_bbox_wh_plot(
            stats["_bbox_widths"],
            stats["_bbox_heights"],
            out_dir / f"{prefix}_bbox_wh.png",
            f"{prefix}: bbox width/height distribution",
        )

    if stats.get("_bbox_areas"):
        save_bbox_area_plot(
            stats["_bbox_areas"],
            out_dir / f"{prefix}_bbox_area.png",
            f"{prefix}: bbox area distribution",
        )

    if stats.get("_bbox_centers"):
        save_bbox_centers_plot(
            stats["_bbox_centers"],
            out_dir / f"{prefix}_bbox_centers.png",
            f"{prefix}: bbox center positions",
        )

    if stats.get("resolutions"):
        save_resolutions_plot(
            stats["resolutions"],
            out_dir / f"{prefix}_resolutions.png",
            f"{prefix}: image resolutions",
        )

    if stats.get("_intensity_hist") is not None:
        save_intensity_plot(
            stats["_intensity_hist"],
            out_dir / f"{prefix}_intensity.png",
            f"{prefix}: intensity histogram",
        )

    if stats.get("_rgb_hist") is not None:
        save_rgb_plot(
            stats["_rgb_hist"],
            out_dir / f"{prefix}_rgb.png",
            f"{prefix}: RGB histogram",
        )

    if stats.get("condition_metadata_present"):
        save_conditions_plot(
            stats["condition_by_image"],
            stats["condition_labels"],
            out_dir / f"{prefix}_conditions_images.png",
            f"{prefix}: shooting conditions by images",
            "Condition tag",
        )
        save_conditions_plot(
            stats["condition_by_sequence"],
            stats["condition_labels"],
            out_dir / f"{prefix}_conditions_sequences.png",
            f"{prefix}: shooting conditions by sequences",
            "Condition tag",
        )


# JSON OUTPUT
def save_json_report(out_path: Path, data: dict):
    if not SAVE_JSON:
        return
    json_data = {k: v for k, v in data.items() if not k.startswith("_")}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)


def save_session_meta(
    out_path: Path,
    input_yaml_files: List[Path],
    source_dataset_yamls: List[Path],
    selected_splits_union: List[str],
    use_path_split_inference: bool,
    output_root: Path,
):
    if not SAVE_JSON:
        return

    meta = {
        "generation_time": utc3_now_str(),
        "input_yaml_files": [str(p) for p in input_yaml_files],
        "source_dataset_yamls": [str(p) for p in source_dataset_yamls],
        "selected_splits_union": selected_splits_union,
        "use_path_split_inference": use_path_split_inference,
        "output_root": str(output_root),
        "shooting_conditions_filename": SHOOTING_CONDITIONS_FILENAME,
        "default_condition_labels": list(DEFAULT_CONDITION_LABELS),
        "small_area_threshold": SMALL_AREA,
        "medium_area_threshold": MEDIUM_AREA,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


# MARKDOWN
def markdown_for_stats(title: str, stats: dict) -> str:
    lines = []
    lines.append(f"## {title}")
    lines.append("")
    lines.append(f"- Total images: **{stats['images_total']}**")
    lines.append(f"- Total objects (labels): **{stats['objects_total']}**")
    lines.append(f"- Broken label lines: **{stats['broken_label_lines']}**")
    lines.append(f"- Missing label files: **{stats['missing_label_files']}**")
    lines.append(f"- Number of classes (nc): **{stats['nc'] if stats['nc'] is not None else 'not specified'}**")

    if stats["class_names"]:
        class_desc = ", ".join([f"{k}: {v}" for k, v in sorted(stats["class_names"].items(), key=lambda x: int(x[0]))])
        lines.append(f"- Class names: **{class_desc}**")

    if stats["channels"]:
        ch_desc = ", ".join([f"{k}ch: {v}" for k, v in sorted(stats["channels"].items(), key=lambda x: int(x[0]))])
        lines.append(f"- Channels: **{ch_desc}**")
        lines.append(f"- Unified channels: **{'yes' if stats['unified_channels'] else 'no'}**")

    if stats["resolutions"]:
        res_desc = ", ".join([f"{k}: {v}" for k, v in sorted(stats["resolutions"].items(), key=lambda x: -x[1])])
        lines.append(f"- Resolutions: **{res_desc}**")
        lines.append(f"- Unified resolution: **{'yes' if stats['unified_resolution'] else 'no'}**")

    if stats["yaml_splits"]:
        yaml_desc = ", ".join([f"{k}: {v}" for k, v in stats["yaml_splits"].items()])
        lines.append(f"- YAML sections where data came from: **{yaml_desc}**")

    if stats["path_splits"]:
        path_desc = ", ".join([f"{k}: {v}" for k, v in stats["path_splits"].items()])
        lines.append(f"- Split names found in paths: **{path_desc}**")

    if stats["datasets_included"]:
        ds_desc = ", ".join([f"{k}: {v}" for k, v in stats["datasets_included"].items()])
        lines.append(f"- Datasets in this analysis: **{ds_desc}**")

    lines.append(f"- Min objects per image: **{stats['min_objects_per_image']}**")
    lines.append(f"- Max objects per image: **{stats['max_objects_per_image']}**")
    lines.append(f"- Background images (0 objects): **{format_count_pct(stats['background_images'], stats['images_total'])}**")
    lines.append("")

    lines.append("### Objects per image distribution")
    lines.append("")
    lines.append("| Objects per image | Images count | Percentage |")
    lines.append("|---:|---:|---:|")
    for k in sorted((int(x) for x in stats["objects_per_image"].keys())):
        v = stats["objects_per_image"][str(k)]
        lines.append(f"| {k} | {v} | {pct(v, stats['images_total']):.2f}% |")
    lines.append("")

    lines.append("### Object sizes by COCO format")
    lines.append("")
    lines.append("| Category | Count | Percentage of all objects |")
    lines.append("|---|---:|---:|")
    lines.append(f"| small | {stats['small_count']} | {pct(stats['small_count'], stats['objects_total']):.2f}% |")
    lines.append(f"| medium | {stats['medium_count']} | {pct(stats['medium_count'], stats['objects_total']):.2f}% |")
    lines.append(f"| large | {stats['large_count']} | {pct(stats['large_count'], stats['objects_total']):.2f}% |")
    lines.append("")

    lines.append("### Shooting conditions")
    lines.append("")
    if stats["condition_metadata_present"]:
        levels = ", ".join(stats["condition_annotation_levels"]) if stats["condition_annotation_levels"] else "not specified"
        labels_desc = ", ".join(stats["condition_labels"]) if stats["condition_labels"] else "not specified"

        lines.append(f"- Metadata found: **yes**")
        lines.append(f"- Annotation level: **{levels}**")
        lines.append(f"- Available condition tags: **{labels_desc}**")
        lines.append(f"- Images with condition tags: **{format_count_pct(stats['images_with_condition_tags'], stats['images_total'])}**")
        lines.append(f"- Sequences with condition tags: **{stats['sequences_with_condition_tags']}**")
        if stats["condition_source_files"]:
            src_desc = "<br>".join(stats["condition_source_files"])
            lines.append(f"- Metadata files:<br>{src_desc}")
        lines.append("")

        lines.append("#### Distribution by images")
        lines.append("")
        lines.append("| Tag | Images count | Percentage of all images |")
        lines.append("|---|---:|---:|")
        for tag in stats["condition_labels"]:
            count = stats["condition_by_image"].get(tag, 0)
            lines.append(f"| {tag} | {count} | {pct(count, stats['images_total']):.2f}% |")
        lines.append("")

        lines.append("#### Distribution by sequences")
        lines.append("")
        lines.append("| Tag | Sequences count |")
        lines.append("|---|---:|")
        for tag in stats["condition_labels"]:
            count = stats["condition_by_sequence"].get(tag, 0)
            lines.append(f"| {tag} | {count} |")
        lines.append("")
    else:
        lines.append(f"- Metadata found: **no**")
        lines.append(f"- File `{SHOOTING_CONDITIONS_FILENAME}` not found for this analysis.")
        lines.append("")

    if stats["class_distribution"]:
        lines.append("### Class distribution")
        lines.append("")
        lines.append("| class_id | class_name | count | percent |")
        lines.append("|---:|---|---:|---:|")
        for cls_id, count in sorted(stats["class_distribution"].items(), key=lambda x: int(x[0])):
            cls_name = stats["class_names"].get(cls_id, f"class_{cls_id}")
            lines.append(f"| {cls_id} | {cls_name} | {count} | {pct(count, stats['objects_total']):.2f}% |")
        lines.append("")

    return "\n".join(lines)


def write_dataset_markdown(
    out_md: Path,
    title: str,
    yaml_name: str,
    group_key: str,
    overall_stats: Optional[dict],
    per_split_stats: Dict[str, dict],
    selected_splits: List[str],
):
    if not SAVE_MARKDOWN:
        return

    lines = []
    lines.append(f"# EDA report: {title}")
    lines.append("")
    lines.append(f"- YAML: **{yaml_name}**")
    lines.append(f"- Group key: **{group_key}**")
    lines.append(f"- Generation time: **{utc3_now_str()}**")
    lines.append(f"- Selected splits: **{', '.join(selected_splits)}**")
    lines.append(f"- Split interpretation mode: **{'path-based' if USE_PATH_SPLIT_INFERENCE else 'YAML / selected splits'}**")
    lines.append("")

    if overall_stats is not None:
        lines.append(markdown_for_stats("Overall statistics", overall_stats))

    for split_name in CANONICAL_SPLITS:
        if split_name in per_split_stats:
            lines.append(markdown_for_stats(f"Statistics for split = {split_name}", per_split_stats[split_name]))

    out_md.write_text("\n".join(lines), encoding="utf-8")


# DATASET YAML PROCESSING
def build_dataset_groups_for_dataset_yaml(
    yaml_path: Path,
    selected_splits: List[str],
) -> Dict[str, DatasetGroup]:
    y = load_yaml(yaml_path)
    yaml_root = Path(y["path"]).resolve() if y.get("path") else None
    class_names = normalize_names(y.get("names"))
    nc = y.get("nc")
    dataset_name_from_yaml = str(y.get("name", yaml_path.stem))

    target_yaml_keys = get_target_yaml_keys(selected_splits)
    groups: Dict[str, DatasetGroup] = {}

    for yaml_split_raw in target_yaml_keys:
        entries = to_list(y.get(yaml_split_raw))
        if not entries:
            continue

        yaml_split = canonicalize_split(yaml_split_raw)

        for raw in entries:
            resolved = resolve_entry_path(raw, yaml_root, yaml_path)
            img_dir, lbl_dir = resolve_image_label_dirs(resolved)

            group_root = normalize_dataset_group_root(resolved)
            group_key = str(group_root)

            dataset_name = dataset_name_from_yaml or derive_dataset_name(group_root)

            if group_key not in groups:
                groups[group_key] = DatasetGroup(
                    group_key=group_key,
                    dataset_name=dataset_name,
                    yaml_name=yaml_path.name,
                    class_names=class_names,
                    nc=nc,
                )

            path_split = infer_split_from_path(resolved)
            final_split = path_split if (USE_PATH_SPLIT_INFERENCE and path_split is not None) else yaml_split

            if final_split not in CANONICAL_SPLITS:
                final_split = yaml_split if yaml_split in CANONICAL_SPLITS else "train"

            groups[group_key].split_entries[final_split].append(
                (img_dir, lbl_dir, yaml_split, path_split, str(raw))
            )

    return groups


def analyze_split_dirs(
    dataset_name: str,
    dataset_yaml_name: str,
    split_name: str,
    dir_entries,
) -> List[SampleStat]:
    stats = []

    for img_dir, lbl_dir, yaml_split, path_split, _raw in dir_entries:
        images = list_images(img_dir)

        conditions_json_path = find_conditions_json_near_dir(img_dir)
        conditions_metadata = load_json_file(conditions_json_path) if conditions_json_path is not None else None

        for img_path in images:
            label_path = relative_label_path(img_path, img_dir, lbl_dir)
            try:
                stat = analyze_image(
                    img_path=img_path,
                    label_path=label_path,
                    split_name=split_name,
                    dataset_name=dataset_name,
                    dataset_yaml_name=dataset_yaml_name,
                    yaml_split=yaml_split,
                    path_split=path_split,
                )
                apply_conditions_metadata_to_sample(
                    sample=stat,
                    img_dir=img_dir,
                    metadata=conditions_metadata,
                    metadata_path=conditions_json_path,
                )
                stats.append(stat)
            except Exception as e:
                print(f"[WARN] Failed to analyze image: {img_path} | {e}")

    return stats


def process_dataset_yaml(
    dataset_yaml_path: Path,
    out_root: Path,
    selected_splits: List[str]
) -> List[SampleStat]:
    dataset_groups = build_dataset_groups_for_dataset_yaml(dataset_yaml_path, selected_splits)
    yaml_out_dir = out_root / f"EDA_{dataset_yaml_path.stem}"
    ensure_dir(yaml_out_dir)

    print(f"[INFO] Processing dataset YAML: {dataset_yaml_path}")
    print(f"[INFO] Output dir: {yaml_out_dir}")

    all_dataset_samples_across_groups: List[SampleStat] = []

    for _, group in dataset_groups.items():
        dataset_out = yaml_out_dir / safe_name(group.dataset_name)
        ensure_dir(dataset_out)

        all_samples: List[SampleStat] = []
        per_split_stats: Dict[str, dict] = {}

        for split_name in CANONICAL_SPLITS:
            dir_entries = group.split_entries.get(split_name, [])
            if not dir_entries:
                continue

            split_samples = analyze_split_dirs(
                dataset_name=group.dataset_name,
                dataset_yaml_name=group.yaml_name,
                split_name=split_name,
                dir_entries=dir_entries,
            )
            all_samples.extend(split_samples)

            split_stats = aggregate_stats(split_samples, group.class_names, group.nc)
            per_split_stats[split_name] = split_stats

            if SAVE_PLOTS:
                split_plot_dir = dataset_out / split_name
                generate_plots(split_stats, split_plot_dir, prefix=split_name)

            if SAVE_JSON:
                save_json_report(dataset_out / f"{split_name}.json", split_stats)

        overall_stats = aggregate_stats(all_samples, group.class_names, group.nc) if all_samples else None
        if overall_stats is not None:
            if SAVE_PLOTS:
                generate_plots(overall_stats, dataset_out / "overall", prefix="overall")
            if SAVE_JSON:
                save_json_report(dataset_out / "report.json", overall_stats)

        if SAVE_MARKDOWN:
            write_dataset_markdown(
                dataset_out / "report.md",
                title=group.dataset_name,
                yaml_name=group.yaml_name,
                group_key=group.group_key,
                overall_stats=overall_stats,
                per_split_stats=per_split_stats,
                selected_splits=selected_splits,
            )

        all_dataset_samples_across_groups.extend(all_samples)

    return all_dataset_samples_across_groups


# GLOBAL MERGED OUTPUT
def write_global_report(
    out_dir: Path,
    title: str,
    overall_stats: dict,
    per_split_stats: Dict[str, dict],
    selected_splits: List[str],
    source_dataset_yamls: List[Path],
):
    ensure_dir(out_dir)

    if SAVE_JSON:
        save_json_report(out_dir / "report.json", overall_stats)
        for split_name, stats in per_split_stats.items():
            save_json_report(out_dir / f"{split_name}.json", stats)

    if SAVE_MARKDOWN:
        lines = []
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"- Generation time: **{utc3_now_str()}**")
        lines.append(f"- Selected splits: **{', '.join(selected_splits)}**")
        lines.append("- Source dataset YAMLs:")
        for p in source_dataset_yamls:
            lines.append(f"  - `{p}`")
        lines.append("")
        lines.append(markdown_for_stats("Overall statistics across all selected datasets", overall_stats))

        for split_name in CANONICAL_SPLITS:
            if split_name in per_split_stats:
                lines.append(markdown_for_stats(f"Global statistics for split = {split_name}", per_split_stats[split_name]))

        (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")

    if SAVE_PLOTS:
        generate_plots(overall_stats, out_dir / "overall", prefix="overall")
        for split_name, stats in per_split_stats.items():
            generate_plots(stats, out_dir / split_name, prefix=split_name)


# =========================
# CLI
# =========================
def parse_args():
    parser = argparse.ArgumentParser(description="YOLO / Run YAML EDA")
    parser.add_argument("--yaml", type=str, default=None, help="Path to one Run YAML")
    parser.add_argument("--yamls", nargs="*", default=None, help="Paths to multiple Run YAML files")
    parser.add_argument(
        "--output-root",
        type=str,
        default=None,
        help="Where to place result directories",
    )
    parser.add_argument(
        "--use-path-split-inference",
        action="store_true",
        help="Classify split by path instead of YAML/selected_splits",
    )
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Disable JSON output",
    )
    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="Disable Markdown output",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Disable PNG plot generation",
    )
    return parser.parse_args()


# MAIN
def main():
    args = parse_args()

    global USE_PATH_SPLIT_INFERENCE, SAVE_JSON, SAVE_MARKDOWN, SAVE_PLOTS
    if args.use_path_split_inference:
        USE_PATH_SPLIT_INFERENCE = True
    if args.no_json:
        SAVE_JSON = False
    if args.no_markdown:
        SAVE_MARKDOWN = False
    if args.no_plots:
        SAVE_PLOTS = False

    input_yaml_files = []
    if INPUT_YAMLS:
        input_yaml_files.extend([Path(x).resolve() for x in INPUT_YAMLS])

    if args.yaml:
        input_yaml_files = [Path(args.yaml).resolve()]

    if args.yamls:
        input_yaml_files = [Path(x).resolve() for x in args.yamls]

    if not input_yaml_files:
        raise ValueError("No YAML files specified: set INPUT_YAMLS or pass --yaml / --yamls")

    for y in input_yaml_files:
        if not y.exists():
            raise FileNotFoundError(f"YAML not found: {y}")

    output_root = Path(OUTPUT_ROOT).resolve()
    if args.output_root:
        output_root = Path(args.output_root).resolve()
    ensure_dir(output_root)

    session_out = output_root / f"EDA_session_{utc3_now_compact_str()}"
    ensure_dir(session_out)

    all_global_samples: List[SampleStat] = []
    source_dataset_yamls: List[Path] = []
    selected_splits_union: Set[str] = set()

    for entry_yaml in input_yaml_files:
        run_specs = parse_run_yaml(entry_yaml)

        if not run_specs:
            print(f"[WARN] No dataset specs found in: {entry_yaml}")
            continue

        for spec in run_specs:
            if not spec.yaml_path.exists():
                print(f"[WARN] Dataset YAML not found: {spec.yaml_path}")
                continue

            ds_yaml_data = load_yaml(spec.yaml_path)
            if not is_dataset_yaml(ds_yaml_data):
                print(f"[WARN] Unsupported dataset YAML format: {spec.yaml_path}")
                continue

            samples = process_dataset_yaml(
                dataset_yaml_path=spec.yaml_path,
                out_root=session_out,
                selected_splits=spec.selected_splits,
            )
            all_global_samples.extend(samples)
            source_dataset_yamls.append(spec.yaml_path)

            selected_splits_union.update(spec.selected_splits)

    if not all_global_samples:
        raise RuntimeError("Failed to collect any images for analysis.")

    global_overall_stats = aggregate_stats(all_global_samples, class_names={}, nc=None)

    global_per_split_stats: Dict[str, dict] = {}
    for split_name in CANONICAL_SPLITS:
        split_samples = [s for s in all_global_samples if s.split_name == split_name]
        if split_samples:
            global_per_split_stats[split_name] = aggregate_stats(split_samples, class_names={}, nc=None)

    write_global_report(
        out_dir=session_out / "GLOBAL_MERGED",
        title="EDA report: GLOBAL MERGED",
        overall_stats=global_overall_stats,
        per_split_stats=global_per_split_stats,
        selected_splits=sorted(selected_splits_union),
        source_dataset_yamls=source_dataset_yamls,
    )

    if SAVE_JSON:
        save_session_meta(
            out_path=session_out / "session_meta.json",
            input_yaml_files=input_yaml_files,
            source_dataset_yamls=source_dataset_yamls,
            selected_splits_union=sorted(selected_splits_union),
            use_path_split_inference=USE_PATH_SPLIT_INFERENCE,
            output_root=output_root,
        )

    print("[INFO] Done.")
    print(f"[INFO] Session output: {session_out}")


if __name__ == "__main__":
    main()