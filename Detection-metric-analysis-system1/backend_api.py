#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from PIL import Image

from db_interface import connect, _fetch_dicts, load_run_config

ROOT = Path(__file__).resolve().parent
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

def dump(data):
    print(json.dumps(data, ensure_ascii=False, default=str))

def load_yaml(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]

def image_dirs_from_dataset_yaml(path, split="test"):
    y = load_yaml(path)
    root = Path(y["path"]) if y.get("path") else None
    out = []
    for raw in as_list(y.get(split, y.get("val"))):
        p = Path(str(raw))
        if not p.is_absolute() and root is not None:
            p = root / p
        out.append(str(p))
    return out

def label_dir_for_image_dir(img_dir):
    s = str(img_dir)
    return s.replace("images", "labels") if "images" in s else str(Path(s).parent / "labels")

def cmd_setup(_args):
    cfg = load_run_config("run_all_current")
    ds_out = []
    for name, d in cfg["datasets"].items():
        if not Path(d["path"]).exists():
            continue
        dirs = image_dirs_from_dataset_yaml(d["path"])
        ds_out.append({
            "id": name,
            "name": name,
            "path": d["path"],
            "imagePath": dirs[0] if dirs else "",
            "imageDirs": dirs,
            "classes": 1,
            "images": None,
            "desc": d.get("description") or "",
        })
    ms_out = []
    for name, m in cfg["models"].items():
        if not Path(m["weights"]).exists() or not Path(m["script_path"]).exists():
            continue
        ms_out.append({
            "id": name,
            "name": name,
            "weightsPath": m["weights"],
            "scriptPath": m["script_path"],
            "desc": m.get("description") or "",
            "type": "Custom",
            "params": "?",
            "gflops": "?",
            "speed": "?",
        })
    dump({"datasets": ds_out, "models": ms_out})

def parse_label(path, w, h):
    if not path.exists():
        return [], 1, 0
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    boxes, broken = [], 0
    for line in lines:
        parts = line.strip().split()
        if not parts:
            continue
        if len(parts) < 5:
            broken += 1
            continue
        try:
            cls = int(float(parts[0]))
            xc, yc, bw, bh = map(float, parts[1:5])
        except Exception:
            broken += 1
            continue
        if not (0 <= xc <= 1 and 0 <= yc <= 1 and 0 < bw <= 1 and 0 < bh <= 1):
            broken += 1
            continue
        boxes.append((cls, bw * w, bh * h, bw * bh * w * h, xc, yc))
    return boxes, 0, broken

def build_eda_report(dataset_name, dataset_path):
    y = load_yaml(dataset_path)
    names = y.get("names", {"0": "object"})
    if isinstance(names, list):
        class_names = {str(i): n for i, n in enumerate(names)}
    else:
        class_names = {str(k): v for k, v in names.items()}
    image_dirs = image_dirs_from_dataset_yaml(dataset_path)
    stats = []
    class_counter = Counter()
    channels = Counter()
    resolutions = Counter()
    objects_per_image = Counter()
    bbox_widths, bbox_heights, bbox_areas, bbox_centers = [], [], [], []
    missing, broken, background = 0, 0, 0
    for img_dir in image_dirs:
        img_dir_p = Path(img_dir)
        lbl_dir_p = Path(label_dir_for_image_dir(img_dir))
        for img in sorted(p for p in img_dir_p.rglob("*") if p.suffix.lower() in IMG_EXTS):
            try:
                with Image.open(img) as im:
                    w, h = im.size
                    ch = len(im.getbands())
            except Exception:
                continue
            label = (lbl_dir_p / img.relative_to(img_dir_p)).with_suffix(".txt")
            boxes, miss, br = parse_label(label, w, h)
            missing += miss
            broken += br
            if not boxes:
                background += 1
            channels[str(ch)] += 1
            resolutions[f"{w}x{h}"] += 1
            objects_per_image[str(len(boxes))] += 1
            for cls, bw, bh, area, xc, yc in boxes:
                class_counter[str(cls)] += 1
                bbox_widths.append(bw)
                bbox_heights.append(bh)
                bbox_areas.append(area)
                bbox_centers.append([xc, yc])
            stats.append(img)
    small = sum(1 for a in bbox_areas if a < 32 ** 2)
    medium = sum(1 for a in bbox_areas if 32 ** 2 <= a < 96 ** 2)
    large = sum(1 for a in bbox_areas if a >= 96 ** 2)
    total = len(stats)
    obj_total = sum(class_counter.values())
    return {
        "_singleSplit": True,
        "title": dataset_name,
        "yaml_name": Path(dataset_path).name,
        "group_key": dataset_path,
        "generation_time": "",
        "target_split": "test",
        "analyzed_image_dirs": image_dirs,
        "images_total": total,
        "objects_total": obj_total,
        "nc": len(class_names),
        "class_names": class_names,
        "class_distribution": dict(class_counter),
        "broken_label_lines": broken,
        "missing_label_files": missing,
        "empty_label_files": background,
        "only_broken_label_files": 0,
        "corrupted_label_images": 0,
        "background_images": background,
        "background_definition": "Images without valid labels",
        "min_objects_per_image": min((int(k) for k in objects_per_image), default=0),
        "max_objects_per_image": max((int(k) for k in objects_per_image), default=0),
        "channels": dict(channels),
        "resolutions": dict(resolutions),
        "unified_channels": len(channels) <= 1,
        "unified_resolution": len(resolutions) <= 1,
        "small_count": small,
        "medium_count": medium,
        "large_count": large,
        "small_area_threshold": 32 ** 2,
        "medium_area_threshold": 96 ** 2,
        "objects_per_image": dict(objects_per_image),
        "objects_per_image_distribution": dict(objects_per_image),
        "bbox_widths": bbox_widths[:5000],
        "bbox_heights": bbox_heights[:5000],
        "bbox_areas": bbox_areas[:5000],
        "bbox_centers": bbox_centers[:5000],
        "intensity_histogram": None,
        "condition_metadata_present": False,
        "condition_by_image": {},
        "condition_by_sequence": {},
        "images_with_conditions": 0,
        "sequences_with_conditions": 0,
        "condition_source_files": [],
    }

def cmd_eda(args):
    setup = json.loads(subprocess.check_output([sys.executable, __file__, "setup"], text=True, encoding="utf-8"))
    selected = set(args.datasets.split(",")) if args.datasets else {d["id"] for d in setup["datasets"]}
    reports = {}
    for d in setup["datasets"]:
        if d["id"] in selected:
            reports[d["id"]] = build_eda_report(d["name"], d["path"])
    dump(reports)

def cmd_validation(_args):
    proc = subprocess.run([sys.executable, str(ROOT / "eval_all_coco.py")], cwd=str(ROOT), text=True, capture_output=True)
    dump({"ok": proc.returncode == 0, "returncode": proc.returncode, "stdout": proc.stdout[-8000:], "stderr": proc.stderr[-8000:]})

def parse_results_md(path):
    rows = []
    current_ds = None
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("## Dataset:"):
            current_ds = line.split(":", 1)[1].strip()
        if line.startswith("| ") and not line.startswith("| Model") and not line.startswith("|-"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 9 and current_ds:
                rows.append({
                    "datasetId": current_ds,
                    "datasetName": current_ds,
                    "modelId": parts[0],
                    "modelName": parts[0],
                    "metrics": {
                        "map50": float(parts[1]) if parts[1] != "-" else 0,
                        "map5095": float(parts[2]) if parts[2] != "-" else 0,
                        "apSmall": parts[3],
                        "apMedium": parts[4],
                        "apLarge": parts[5],
                        "p": float(parts[6]) if parts[6] != "-" else 0,
                        "r": float(parts[7]) if parts[7] != "-" else 0,
                        "f1": float(parts[8]) if parts[8] != "-" else 0,
                    }
                })
    return rows

def cmd_results(_args):
    rows = parse_results_md(ROOT / "anti_uav_results.md")
    dump({"rows": rows})

def iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    union = aw * ah + bw * bh - inter
    return inter / union if union else 0

def cmd_detection_errors(_args):
    items = []
    cfg = load_run_config("run_all_current")
    conf_threshold = 0.4
    iou_threshold = 0.5
    for dataset_name in cfg["datasets"]:
        gt_path = ROOT / "coco_test_metrics" / "coco_datasets" / f"{dataset_name}.json"
        if not gt_path.exists():
            continue
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        images = {im["id"]: im for im in gt.get("images", [])}
        anns = defaultdict(list)
        for ann in gt.get("annotations", []):
            anns[ann["image_id"]].append(ann)
        for model_name in cfg["models"]:
            det_path = ROOT / "coco_test_metrics" / "predictions" / f"{dataset_name}_{model_name}.json"
            if not det_path.exists():
                continue
            det = json.loads(det_path.read_text(encoding="utf-8"))
            dets = defaultdict(list)
            for d in det:
                dets[d["image_id"]].append(d)
            for image_id, img in images.items():
                gt_list = anns.get(image_id, [])
                det_list = dets.get(image_id, [])
                errors = []
                overlays = []
                matched = set()
                for d in det_list:
                    best_i, best_gt = 0, None
                    for idx, g in enumerate(gt_list):
                        val = iou(d["bbox"], g["bbox"])
                        if val > best_i:
                            best_i, best_gt = val, idx
                    score = d.get("score", 0)
                    if best_i == 0 and score >= conf_threshold:
                        errors.append({"type": "false_positive", "bbox": d["bbox"], "score": d.get("score")})
                    elif 0 < best_i < iou_threshold and score >= conf_threshold:
                        errors.append({"type": "low_iou", "bbox": d["bbox"], "score": d.get("score"), "iou": best_i})
                    elif best_i >= iou_threshold:
                        if best_gt in matched:
                            if score >= conf_threshold:
                                errors.append({"type": "duplicate", "bbox": d["bbox"], "score": score, "iou": best_i})
                            else:
                                errors.append({"type": "low_conf", "bbox": d["bbox"], "score": score, "iou": best_i})
                        else:
                            matched.add(best_gt)
                            if score < conf_threshold:
                                errors.append({"type": "low_conf", "bbox": d["bbox"], "score": score, "iou": best_i})
                for idx, g in enumerate(gt_list):
                    overlays.append({"type": "ground_truth", "bbox": g["bbox"]})
                    if idx not in matched:
                        errors.append({"type": "false_negative", "bbox": g["bbox"]})
                if errors:
                    overlays.extend(errors)
                    items.append({
                        "image_id": f"{dataset_name}:{model_name}:{image_id}",
                        "dataset": dataset_name,
                        "model": model_name,
                        "file_name": img["file_name"],
                        "image_url": f"/api/image?path={img['file_name']}",
                        "width": img.get("width"),
                        "height": img.get("height"),
                        "errors": errors,
                        "overlays": overlays,
                    })
    summary = Counter(e["type"] for item in items for e in item["errors"])
    dump({"items": items[:300], "summary": dict(summary), "totalImages": len(items)})

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup")
    pe = sub.add_parser("eda")
    pe.add_argument("--datasets", default="")
    sub.add_parser("validation")
    sub.add_parser("results")
    sub.add_parser("detection-errors")
    args = p.parse_args()
    globals()[f"cmd_{args.cmd.replace('-', '_')}"](args)

if __name__ == "__main__":
    main()
