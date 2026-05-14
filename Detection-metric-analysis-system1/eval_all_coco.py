#!/usr/bin/env python3
# coding: utf-8

import argparse, yaml, os, json, csv, importlib.util
from pathlib import Path
from typing import Any, Dict, List, Union
from datetime import datetime
from PIL import Image
import numpy as np
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

from db_interface import (
    load_run_config,
    create_experiment,
    save_metrics,
    finish_experiment,
    DEFAULT_DB_URL,
)

def fmt(x): return "-" if x is None or x < 0 else f"{x:.4f}"

def render_table(headers: List[str], rows: List[List[str]]) -> str:
    widths = [max(len(str(x)) for x in col) for col in zip(headers, *rows)]
    line = lambda row: "| " + " | ".join(str(c).ljust(w) for c, w in zip(row, widths)) + " |"
    sep  = "|-" + "-|-".join("-"*w for w in widths) + "-|"
    return "\n".join([line(headers), sep] + [line(r) for r in rows])


def yolo_to_coco(yolo_labels_dirs: Union[str, List[str]], images_dirs: Union[str, List[str]], classes: List[str], output_json: str):
    """Convert YOLO-style labels (possibly from multiple label/image folders) to a single COCO json."""
    if isinstance(yolo_labels_dirs, str):
        yolo_labels_dirs = [yolo_labels_dirs]
    if isinstance(images_dirs, str):
        images_dirs = [images_dirs]

    yolo_labels_dirs = [str(Path(p)) for p in yolo_labels_dirs]
    images_dirs = [str(Path(p)) for p in images_dirs]

    images, annotations, categories = [], [], []
    ann_id = 1
    for i, cls in enumerate(classes):
        categories.append({"id": i, "name": cls, "supercategory": "none"})

    image_path_to_id = {}
    img_id = 1
    exts = ["jpg","jpeg","png","bmp","tif","tiff","webp"]

    label_files = []
    for ld in yolo_labels_dirs:
        p = Path(ld)
        if not p.exists():
            print(f"[warn] labels dir not found: {p}")
            continue
        label_files.extend(sorted(p.glob("*.txt")))

    for label_file in label_files:
        stem = label_file.stem
        img_path = None
        for images_dir in images_dirs:
            for ext in exts:
                cand = Path(images_dir) / f"{stem}.{ext}"
                if cand.exists() and cand.is_file():
                    img_path = str(cand)
                    break
            if img_path:
                break
        if img_path is None:
            for images_dir in images_dirs:
                candidates = list(Path(images_dir).glob(f"{stem}.*"))
                for cand in candidates:
                    if cand.is_file() and cand.suffix.lower().lstrip('.') in exts:
                        img_path = str(cand)
                        break
                if img_path:
                    break
        if img_path is None:
            print(f"[warn] image for label '{label_file}' not found in any of {images_dirs}; skipping")
            continue

        if img_path in image_path_to_id:
            image_id = image_path_to_id[img_path]
        else:
            image_id = img_id
            image_path_to_id[img_path] = image_id
            try:
                with Image.open(img_path) as im:
                    w, h = im.size
            except Exception as e:
                print(f"[warn] cannot open image {img_path}: {e}; skipping")
                continue
            images.append({"id": image_id, "file_name": Path(img_path).name, "width": w, "height": h})
            img_id += 1

        with open(label_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 5:
                    print(f"[warn] bad annotation line in {label_file}: '{line}'; skipping")
                    continue
                cls_str, x_str, y_str, bw_str, bh_str = parts[:5]
                try:
                    cls_i = int(float(cls_str))
                    x = float(x_str)
                    y = float(y_str)
                    bw = float(bw_str)
                    bh = float(bh_str)
                except Exception as e:
                    print(f"[warn] cannot parse annotation in {label_file}: '{line}': {e}; skipping")
                    continue
                x_min = (x - bw / 2) * w
                y_min = (y - bh / 2) * h
                box_w = bw * w
                box_h = bh * h
                annotations.append({"id": ann_id, "image_id": image_id, "category_id": cls_i,
                                    "bbox": [x_min, y_min, box_w, box_h], "area": box_w * box_h, "iscrowd": 0})
                ann_id += 1

    coco_dict = {"info": {"description": "COCO", "version": "1.0", "year": 2025,
                           "date_created": str(datetime.now())},
                 "licenses": [], "images": images, "annotations": annotations, "categories": categories}
    with open(output_json, "w") as f:
        json.dump(coco_dict, f, indent=2)

def count_objects_by_size(coco_gt: COCO, area_ranges=None):
    if area_ranges is None:
        area_ranges={"small":(0,32**2),"medium":(32**2,96**2),"large":(96**2,1e12)}
    counts={k:0 for k in area_ranges}
    areas={k:[] for k in area_ranges}
    for ann in coco_gt.dataset["annotations"]:
        area=ann["area"]
        for label,(amin,amax) in area_ranges.items():
            if amin<=area<amax:
                counts[label]+=1
                areas[label].append(area)
                break

    avg_area={k:(np.mean(v) if v else None) for k,v in areas.items()}
    return counts,area_ranges,avg_area

def eval_model_on_dataset_coco(weights: str, data_cfg: Dict[str,Any], params: Dict[str,Any],
                               coco_cache: Path, pred_cache: Path, script_path: str, model_name: str):
    dataset_name=data_cfg["short"]
    coco_json=coco_cache/f"{dataset_name}.json"
    if not coco_json.exists():
        os.makedirs(coco_cache,exist_ok=True)
        yolo_to_coco(data_cfg["labels"], data_cfg["images"], data_cfg["names"],str(coco_json))
    coco_gt=COCO(str(coco_json))
    counts,ranges,avg_area=count_objects_by_size(coco_gt)

    os.makedirs(pred_cache,exist_ok=True)
    preds_outfile=pred_cache/f"{dataset_name}_{model_name}.json"

    data_cfg = dict(data_cfg)
    data_cfg["coco_gt"] = coco_gt


    spec = importlib.util.spec_from_file_location("predict_module", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    default_metrics = {"mAP@0.5:0.95":0.0,"mAP@0.5":0.0,"AP_small":-1,"AP_medium":-1,"AP_large":-1,
                      "Precision":0.0,"Recall":0.0,"F1":0.0,
                      "counts":counts,"ranges":ranges,"avg_area":avg_area}

    all_preds = []
    if isinstance(data_cfg["images"], list):
        for i, img_dir in enumerate(data_cfg["images"]):
            sub_outfile = pred_cache / f"{dataset_name}_{model_name}_{i}.json"
            sub_cfg = dict(data_cfg)
            sub_cfg["images"] = img_dir
            out_path = module.predict(weights, sub_cfg, params, str(sub_outfile))
            if Path(out_path).exists() and os.path.getsize(out_path) > 0:
                try:
                    with open(out_path) as f:
                        preds_data = json.load(f)
                    if preds_data:
                        all_preds.extend(preds_data)
                except Exception as e:
                    print(f"[warn] cannot load preds from {out_path}: {e}")
        with open(preds_outfile, "w") as f:
            json.dump(all_preds, f)
    else:
        preds_outfile = module.predict(weights, data_cfg, params, str(preds_outfile))

    if not Path(preds_outfile).exists() or os.path.getsize(preds_outfile) == 0:
        return default_metrics
    try:
        with open(preds_outfile) as f:
            preds_data = json.load(f)
        if not preds_data:
            return default_metrics
    except Exception:
        return default_metrics

    coco_dt=coco_gt.loadRes(str(preds_outfile))
    coco_eval=COCOeval(coco_gt,coco_dt,iouType='bbox')
    coco_eval.evaluate()
    coco_eval.accumulate()
    coco_eval.summarize()
    P,R=coco_eval.stats[6],coco_eval.stats[7]
    F1=2*P*R/(P+R+1e-16)
    return {"mAP@0.5:0.95":coco_eval.stats[0],"mAP@0.5":coco_eval.stats[1],
            "AP_small":coco_eval.stats[3],"AP_medium":coco_eval.stats[4],"AP_large":coco_eval.stats[5],
            "Precision":P,"Recall":R,"F1":F1,
            "counts":counts,"ranges":ranges,"avg_area":avg_area}

def load_dataset_cfg(key:str, entry:dict, single_class=False):
    ds_yaml = yaml.safe_load(Path(entry["path"]).read_text())
    names = ["object"] if single_class else ds_yaml.get("names", ["object"])
    images_entries = ds_yaml.get("test", ds_yaml.get("val"))
    if images_entries is None:
        raise RuntimeError(f"Dataset {key} in {entry['path']} has no 'test' or 'val' entry")
    if not isinstance(images_entries, list):
        images_entries = [images_entries]

    all_images, all_labels = [], []
    for img_entry in images_entries:
        p = Path(img_entry)
        if p.exists() and p.is_file():
            p = p.parent
        if p.exists() and (p / "images").exists():
            images_dir = str((p / "images" / "test") if (p / "images" / "test").exists()
                             else ((p / "images" / "val") if (p / "images" / "val").exists() else (p / "images")))
        else:
            if p.name.lower() in ("images", "test", "val"):
                images_dir = str(p)
            else:
                images_dir = str(p)
        if "images" in images_dir:
            labels_dir = images_dir.replace("images", "labels")
        else:
            labels_dir = str(Path(images_dir).parent / "labels")
        images_dir = images_dir.replace("/images/images", "/images")
        labels_dir = labels_dir.replace("/labels/labels", "/labels")
        all_images.append(images_dir)
        all_labels.append(labels_dir)

    return {"short": key, "path": entry["path"], "images": all_images,
            "labels": all_labels, "names": names, "desc": entry.get("description", "")}

def load_model_cfg(key:str, entry:dict):
    if isinstance(entry, str):
        return {"config_name": key, "name": Path(entry).stem, "weights": entry, "desc": "", "script_path": None}
    return {"config_name": key, "name": entry.get("name", key), "weights": entry["weights"],
            "desc": entry.get("description", ""), "script_path": entry.get("script_path")}



DEFAULT_RUN_CONFIG = os.environ.get("RUN_CONFIG", "run_all_current")


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Evaluate models x datasets. By default pulls configuration from PostgreSQL "
            "(run_config). Use -c/--config <yaml> to fall back to legacy YAML master config."
        )
    )
    ap.add_argument("-c", "--config", default=None,
                    help="Legacy mode: path to master_config.yaml. If provided, DB is NOT used.")
    ap.add_argument("-r", "--run-config", default=DEFAULT_RUN_CONFIG,
                    help=f"DB mode: run_config name in DB (default: {DEFAULT_RUN_CONFIG}, "
                         f"also settable via $RUN_CONFIG)")
    ap.add_argument("--db-url", default=DEFAULT_DB_URL,
                    help="PostgreSQL DSN (default: $DATABASE_URL or "
                         "postgresql://postgres:postgres@localhost:5432/pr_bd)")
    ap.add_argument("-o", "--out", default=None,
                    help="Override output markdown path (defaults to run_config.output_md or results.md)")
    ap.add_argument("--single-class", action="store_true",
                    help="Force single-class mode")
    ap.add_argument("--no-persist", action="store_true",
                    help="DB mode only: do not write experiment / metric rows back to DB")
    args = ap.parse_args()

    use_db = args.config is None

    if use_db:
        cfg = load_run_config(args.run_config, db_url=args.db_url)
        print(f"[INFO] Loaded run_config '{cfg['name']}' from DB "
              f"({len(cfg['datasets'])} datasets, {len(cfg['models'])} models)")
    else:
        cfg = yaml.safe_load(Path(args.config).read_text())
        cfg.setdefault("name", Path(args.config).stem)
        cfg.setdefault("single_class", False)
        cfg.setdefault("output_md", None)
        print(f"[INFO] Loaded legacy YAML config from {args.config} "
              f"({len(cfg.get('datasets', {}))} datasets, {len(cfg.get('models', {}))} models)")

    single_class = bool(args.single_class or cfg.get("single_class", False))

    datasets = [load_dataset_cfg(k, v, single_class) for k, v in cfg["datasets"].items()]

    models = []
    for model_key, model_entry in cfg["models"].items():
        model_cfg = load_model_cfg(model_key, model_entry)
        models.append(model_cfg)

    for m in models:
        if not m["script_path"]:
            src = "DB" if use_db else "YAML config"
            raise RuntimeError(f"Model {m['config_name']} missing script_path in {src}. Config: {m}")

    params = cfg.get("eval_params", {}) or {}

    if args.out is None:
        args.out = cfg.get("output_md") or "results.md"


    base_out=Path("coco_test_metrics")

    coco_cache,pred_cache=base_out/"coco_datasets",base_out/"predictions"
    stats_dir=base_out/"statistics"
    base_out.mkdir(exist_ok=True)
    stats_dir.mkdir(exist_ok=True)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    args.out=str(out_path)

    out_path.write_text(f"# Evaluation results\nGenerated at: {datetime.now()}\n\n", encoding="utf-8")
    with open(stats_dir/"statistics.json", "w") as f: json.dump([], f)
    with open(stats_dir/"statistics.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["dataset", "model", "size_class", "count", "avg_area", "range_min", "range_max"])


    for ds in datasets:
        rows = []
        counts = None
        ranges = None
        avg_area = None
        for m in models:
            print(f"Processing dataset: {ds['short']}, model: {m['config_name']}")

            experiment_id = None
            persist_to_db = use_db and not args.no_persist
            if persist_to_db:
                try:
                    experiment_id = create_experiment(
                        run_config_name=cfg["name"],
                        dataset_name=ds["short"],
                        model_name=m["config_name"],
                        eval_params=params,
                        status="running",
                        db_url=args.db_url,
                    )
                except Exception as e:
                    print(f"[warn] cannot create experiment row in DB: {e}")

            try:
                metrics = eval_model_on_dataset_coco(
                    m["weights"], ds, params, coco_cache, pred_cache, m["script_path"], m["config_name"]
                )
            except Exception as e:
                if experiment_id is not None:
                    try:
                        finish_experiment(experiment_id, status="failed", db_url=args.db_url)
                    except Exception:
                        pass
                raise

            row = [m["config_name"]] + [fmt(metrics[h]) for h in ["mAP@0.5","mAP@0.5:0.95","AP_small","AP_medium","AP_large","Precision","Recall","F1"]]
            rows.append(row)

            if experiment_id is not None:
                try:
                    save_metrics(experiment_id, metrics, db_url=args.db_url)
                    finish_experiment(experiment_id, status="done", db_url=args.db_url)
                except Exception as e:
                    print(f"[warn] cannot persist metrics to DB: {e}")

            counts = metrics["counts"]
            ranges = metrics["ranges"]
            avg_area = metrics["avg_area"]

            stats_path = stats_dir/"statistics.json"
            with open(stats_path) as f: cur = json.load(f)
            cur.append({"dataset": ds["short"], "model": m["config_name"], "counts": counts, "ranges": ranges, "avg_area": avg_area})
            with open(stats_path, "w") as f: json.dump(cur, f, indent=2)

            with open(stats_dir/"statistics.csv", "a", newline="") as f:
                writer = csv.writer(f)
                for k, v in counts.items():
                    writer.writerow([ds["short"], m["config_name"], k, v, avg_area[k], ranges[k][0], ranges[k][1]])


        headers = ["Model", "mAP@0.5", "mAP@0.5:0.95", "AP_small", "AP_medium", "AP_large", "Precision", "Recall", "F1"]
        block = []
        block.append(f"\n## Dataset: {ds['short']}\n")
        if ds["desc"]:
            block.append(f"    Description: {ds['desc']}\n")
        block.append(render_table(headers, rows))
        if counts is not None:
            block.append("\n### GT object counts")
            for k, v in counts.items():
                block.append(f"    - {k}: {v} (area {ranges[k][0]}–{ranges[k][1]}), avg_area={avg_area[k]}")
        block.append("")

        with open(args.out, "a", encoding="utf-8") as f:
            f.write("\n".join(block)+"\n")


    out = []
    out.append("\n## Models Description\n")
    for i, m in enumerate(models, 1):
        out.append(f"### Model {i}")
        out.append(f"    Name in results: {m['config_name']}")
        out.append(f"    Weights path: {m['weights']}")
        out.append(f"    Script path: {m['script_path']}")
        out.append(f"    Description: {m['desc']}")
        out.append("")

    out.append("\n## Datasets Information\n")
    for d in datasets:
        out.append(f"### {d['short']}")
        out.append(f"    Path: {d['path']}")
        out.append(f"    Description: {d['desc']}")
        out.append("")

    with open(args.out, "a", encoding="utf-8") as f:
        f.write("\n".join(out))

    print(f"[done] incremental results written to {args.out}, statistics in {stats_dir}")

if __name__=="__main__":
    main()