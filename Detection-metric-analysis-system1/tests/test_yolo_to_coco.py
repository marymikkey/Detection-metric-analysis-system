"""Тестируется yolo_to_coco()"""
import json
from pathlib import Path

import pytest
from PIL import Image

from eval_all_coco import yolo_to_coco


def _make_image(path: Path, size=(100, 100), color="white"):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


def _make_label(path: Path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def test_single_box_converted_correctly(tmp_path):
    img_dir = tmp_path / "images"
    lbl_dir = tmp_path / "labels"
    _make_image(img_dir / "a.jpg", size=(100, 100))
    # cx=0.5, cy=0.5, w=0.2, h=0.2 => bbox=[40,40,20,20], area=400
    _make_label(lbl_dir / "a.txt", ["0 0.5 0.5 0.2 0.2"])

    out = tmp_path / "coco.json"
    yolo_to_coco(str(lbl_dir), str(img_dir), ["object"], str(out))

    data = json.loads(out.read_text())

    assert len(data["images"]) == 1
    assert data["images"][0]["file_name"] == "a.jpg"
    assert data["images"][0]["width"] == 100
    assert data["images"][0]["height"] == 100

    assert data["categories"] == [{"id": 0, "name": "object", "supercategory": "none"}]

    assert len(data["annotations"]) == 1
    ann = data["annotations"][0]
    assert ann["category_id"] == 0
    assert ann["image_id"] == 1
    assert ann["bbox"] == [40.0, 40.0, 20.0, 20.0]
    assert ann["area"] == 400.0
    assert ann["iscrowd"] == 0


def test_multiple_classes_and_boxes_get_unique_ann_ids(tmp_path):
    img_dir = tmp_path / "images"
    lbl_dir = tmp_path / "labels"
    _make_image(img_dir / "x.jpg", size=(200, 100))
    _make_label(
        lbl_dir / "x.txt",
        [
            "0 0.5 0.5 0.5 0.5",
            "1 0.25 0.25 0.1 0.2",
        ],
    )

    out = tmp_path / "coco.json"
    yolo_to_coco(str(lbl_dir), str(img_dir), ["a", "b"], str(out))

    data = json.loads(out.read_text())
    assert {c["name"] for c in data["categories"]} == {"a", "b"}
    assert len(data["annotations"]) == 2

    ids = [a["id"] for a in data["annotations"]]
    assert ids == sorted(set(ids))

    by_cat = {a["category_id"]: a for a in data["annotations"]}
    # box 0: cx=0.5 cy=0.5 w=0.5 h=0.5 on 200x100 => [50,25,100,50], area=5000
    assert by_cat[0]["bbox"] == [50.0, 25.0, 100.0, 50.0]
    assert by_cat[0]["area"] == 5000.0
    # box 1: cx=0.25 cy=0.25 w=0.1 h=0.2 on 200x100 => [40,15,20,20], area=400
    assert by_cat[1]["bbox"] == [40.0, 15.0, 20.0, 20.0]
    assert by_cat[1]["area"] == 400.0


def test_broken_lines_are_skipped(tmp_path, capsys):
    img_dir = tmp_path / "images"
    lbl_dir = tmp_path / "labels"
    _make_image(img_dir / "b.jpg", size=(50, 50))
    _make_label(
        lbl_dir / "b.txt",
        [
            "0 0.5 0.5 0.4 0.4",
            "0 0.5 0.5 0.4",
            "0 0.5 0.5 abc 0.4",
            "",
        ],
    )

    out = tmp_path / "coco.json"
    yolo_to_coco(str(lbl_dir), str(img_dir), ["object"], str(out))

    data = json.loads(out.read_text())
    assert len(data["annotations"]) == 1


def test_label_without_image_is_warned_and_skipped(tmp_path):
    img_dir = tmp_path / "images"
    lbl_dir = tmp_path / "labels"
    img_dir.mkdir()
    _make_label(lbl_dir / "ghost.txt", ["0 0.5 0.5 0.2 0.2"])

    out = tmp_path / "coco.json"
    yolo_to_coco(str(lbl_dir), str(img_dir), ["object"], str(out))

    data = json.loads(out.read_text())
    assert data["images"] == []
    assert data["annotations"] == []


def test_missing_labels_dir_is_warned(tmp_path, capsys):
    img_dir = tmp_path / "images"; img_dir.mkdir()
    out = tmp_path / "coco.json"

    yolo_to_coco(str(tmp_path / "no_such_labels"), str(img_dir), ["o"], str(out))

    data = json.loads(out.read_text())
    assert data["images"] == []
    assert data["annotations"] == []


def test_multiple_label_dirs_and_image_dirs_merge(tmp_path):
    img_dir1 = tmp_path / "imgs1"; lbl_dir1 = tmp_path / "lbls1"
    img_dir2 = tmp_path / "imgs2"; lbl_dir2 = tmp_path / "lbls2"
    _make_image(img_dir1 / "p.jpg", size=(100, 100))
    _make_image(img_dir2 / "q.jpg", size=(100, 100))
    _make_label(lbl_dir1 / "p.txt", ["0 0.5 0.5 0.2 0.2"])
    _make_label(lbl_dir2 / "q.txt", ["0 0.5 0.5 0.4 0.4"])

    out = tmp_path / "coco.json"
    yolo_to_coco(
        [str(lbl_dir1), str(lbl_dir2)],
        [str(img_dir1), str(img_dir2)],
        ["object"],
        str(out),
    )

    data = json.loads(out.read_text())
    assert len(data["images"]) == 2
    assert len(data["annotations"]) == 2
    file_names = {im["file_name"] for im in data["images"]}
    assert file_names == {"p.jpg", "q.jpg"}
