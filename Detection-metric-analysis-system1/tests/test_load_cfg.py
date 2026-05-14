"""Тестируется подгрузка из конфига датасета/модели"""
from pathlib import Path

import pytest
import yaml

from eval_all_coco import load_dataset_cfg, load_model_cfg


def test_load_model_cfg_dict_entry():
    entry = {
        "name":        "iter5_11s_base",
        "weights":     "/w/iter5.pt",
        "script_path": "/s/yolo_base.py",
        "description": "iter5",
    }
    out = load_model_cfg("iter5_11s_base", entry)
    assert out == {
        "config_name": "iter5_11s_base",
        "name":        "iter5_11s_base",
        "weights":     "/w/iter5.pt",
        "script_path": "/s/yolo_base.py",
        "desc":        "iter5",
    }


def test_load_model_cfg_dict_without_name_falls_back_to_key():
    out = load_model_cfg(
        "key_xyz",
        {"weights": "/w/x.pt", "script_path": "/s.py"},
    )
    assert out["name"] == "key_xyz"
    assert out["desc"] == ""


def test_load_model_cfg_string_entry_yields_no_script_path():
    out = load_model_cfg("legacy", "/some/weights.pt")
    assert out == {
        "config_name": "legacy",
        "name":        "weights",
        "weights":     "/some/weights.pt",
        "desc":        "",
        "script_path": None,
    }

def _write_dataset_yaml(yaml_path: Path, body: dict):
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(yaml.safe_dump(body, allow_unicode=True), encoding="utf-8")


def test_load_dataset_cfg_uses_test_when_present(tmp_path):
    ds_root = tmp_path / "ds"
    (ds_root / "images" / "test").mkdir(parents=True)
    (ds_root / "labels" / "test").mkdir(parents=True)

    yaml_path = tmp_path / "dataset.yaml"
    _write_dataset_yaml(
        yaml_path,
        {
            "test":  str(ds_root / "images" / "test"),
            "names": ["car", "person"],
        },
    )

    out = load_dataset_cfg("ds_key", {"path": str(yaml_path), "description": "x"})

    assert out["short"] == "ds_key"
    assert out["names"] == ["car", "person"]
    assert out["desc"] == "x"
    assert any("images" in p for p in out["images"])
    assert any("labels" in p for p in out["labels"])


def test_load_dataset_cfg_falls_back_to_val(tmp_path):
    ds_root = tmp_path / "ds"
    (ds_root / "images" / "val").mkdir(parents=True)
    (ds_root / "labels" / "val").mkdir(parents=True)

    yaml_path = tmp_path / "dataset.yaml"
    _write_dataset_yaml(
        yaml_path,
        {
            "val":   str(ds_root / "images" / "val"),
            "names": ["object"],
        },
    )

    out = load_dataset_cfg("ds_key", {"path": str(yaml_path)})
    assert out["names"] == ["object"]
    assert out["desc"] == ""


def test_load_dataset_cfg_single_class_overrides_names(tmp_path):
    ds_root = tmp_path / "ds"
    (ds_root / "images" / "test").mkdir(parents=True)

    yaml_path = tmp_path / "ds.yaml"
    _write_dataset_yaml(
        yaml_path,
        {"test": str(ds_root / "images" / "test"), "names": ["a", "b", "c"]},
    )

    out = load_dataset_cfg("k", {"path": str(yaml_path)}, single_class=True)
    assert out["names"] == ["object"]


def test_load_dataset_cfg_raises_when_no_test_or_val(tmp_path):
    yaml_path = tmp_path / "ds.yaml"
    _write_dataset_yaml(yaml_path, {"train": "/somewhere", "names": ["x"]})

    with pytest.raises(RuntimeError, match="no 'test' or 'val'"):
        load_dataset_cfg("k", {"path": str(yaml_path)})


def test_load_dataset_cfg_accepts_list_of_image_entries(tmp_path):
    ds_root = tmp_path / "ds"
    (ds_root / "images" / "test").mkdir(parents=True)
    (ds_root / "images2" / "test").mkdir(parents=True)

    yaml_path = tmp_path / "ds.yaml"
    _write_dataset_yaml(
        yaml_path,
        {
            "test":  [str(ds_root / "images" / "test"), str(ds_root / "images2" / "test")],
            "names": ["o"],
        },
    )

    out = load_dataset_cfg("k", {"path": str(yaml_path)})
    assert len(out["images"]) == 2
    assert len(out["labels"]) == 2
