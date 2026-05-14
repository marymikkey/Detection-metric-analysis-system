"""
Tests for eval_model_on_dataset_coco() -- the actual metric pipeline.

To keep tests deterministic and free of heavy dependencies (no real YOLO,
no real images, no real COCOeval evaluation loop) we mock:

* eval_all_coco.COCO         -- returns a stub with .dataset and .loadRes()
* eval_all_coco.COCOeval     -- returns a stub with controllable .stats
* importlib.util.spec_from_file_location / module_from_spec -- so the
  dynamically loaded "predict" script is replaced with a fake module.
"""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import eval_all_coco as eac


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _stub_coco(annotations, images=None):
    """Return an object that quacks like pycocotools.COCO for our usage."""
    if images is None:
        images = [{"id": 1, "file_name": "a.jpg", "width": 100, "height": 100}]
    coco = MagicMock()
    coco.dataset = {"images": images, "annotations": annotations}
    # loadRes is called inside the function but not used unless we go past
    # the "no preds" branch -- we override it on a per-test basis if needed.
    return coco


def _patch_predict_module(predict_fn):
    """Swap importlib so spec_from_file_location returns a fake predict module."""
    fake_module = SimpleNamespace(predict=predict_fn)
    fake_spec = MagicMock()
    fake_spec.loader.exec_module = lambda m: None

    return [
        patch.object(eac.importlib.util, "spec_from_file_location",
                     return_value=fake_spec),
        patch.object(eac.importlib.util, "module_from_spec",
                     return_value=fake_module),
    ]


def _data_cfg(images_dir, labels_dir, name="object"):
    return {
        "short":  "ds",
        "path":   "/dummy.yaml",
        "images": str(images_dir),
        "labels": str(labels_dir),
        "names":  [name],
        "desc":   "",
    }


# ---------------------------------------------------------------------------
# default_metrics branch: predict produced an empty preds file
# ---------------------------------------------------------------------------
def test_returns_default_metrics_when_preds_file_empty(tmp_path):
    coco_cache = tmp_path / "coco"; coco_cache.mkdir()
    pred_cache = tmp_path / "pred"; pred_cache.mkdir()

    # pre-existing coco.json so yolo_to_coco isn't called
    (coco_cache / "ds.json").write_text("{}")

    def fake_predict(weights, cfg, params, outfile):
        Path(outfile).write_text("")  # empty
        return outfile

    with patch.object(eac, "COCO", return_value=_stub_coco([{"area": 100}])), \
         patch.object(eac, "COCOeval") as mock_eval, \
         _patch_predict_module(fake_predict)[0], \
         _patch_predict_module(fake_predict)[1]:

        out = eac.eval_model_on_dataset_coco(
            weights="w.pt",
            data_cfg=_data_cfg(tmp_path / "imgs", tmp_path / "lbls"),
            params={},
            coco_cache=coco_cache,
            pred_cache=pred_cache,
            script_path="/fake.py",
            model_name="m",
        )

    # COCOeval must NOT have been used -- we returned defaults early
    mock_eval.assert_not_called()

    assert out["mAP@0.5"] == 0.0
    assert out["mAP@0.5:0.95"] == 0.0
    assert out["AP_small"] == -1
    assert out["Precision"] == 0.0
    assert out["Recall"] == 0.0
    assert out["F1"] == 0.0
    assert out["counts"]["small"] == 1
    assert out["counts"]["medium"] == 0


def test_returns_default_metrics_when_preds_file_has_empty_array(tmp_path):
    coco_cache = tmp_path / "coco"; coco_cache.mkdir()
    pred_cache = tmp_path / "pred"; pred_cache.mkdir()
    (coco_cache / "ds.json").write_text("{}")

    def fake_predict(weights, cfg, params, outfile):
        Path(outfile).write_text("[]")  # valid json, but empty
        return outfile

    with patch.object(eac, "COCO", return_value=_stub_coco([{"area": 100}])), \
         patch.object(eac, "COCOeval") as mock_eval, \
         _patch_predict_module(fake_predict)[0], \
         _patch_predict_module(fake_predict)[1]:

        out = eac.eval_model_on_dataset_coco(
            weights="w.pt",
            data_cfg=_data_cfg(tmp_path / "imgs", tmp_path / "lbls"),
            params={},
            coco_cache=coco_cache,
            pred_cache=pred_cache,
            script_path="/fake.py",
            model_name="m",
        )

    mock_eval.assert_not_called()
    assert out["F1"] == 0.0


# ---------------------------------------------------------------------------
# Successful path: COCOeval returns known stats -> we verify F1 derivation
# ---------------------------------------------------------------------------
def test_metrics_assembled_from_cocoeval_stats(tmp_path):
    """
    eval_all_coco maps stats[0..7] from pycocotools.COCOeval.summarize() to:
        mAP@0.5:0.95 = stats[0]
        mAP@0.5      = stats[1]
        AP_small     = stats[3]
        AP_medium    = stats[4]
        AP_large     = stats[5]
        Precision    = stats[6]
        Recall       = stats[7]
        F1           = 2*P*R / (P+R+eps)
    """
    coco_cache = tmp_path / "coco"; coco_cache.mkdir()
    pred_cache = tmp_path / "pred"; pred_cache.mkdir()
    (coco_cache / "ds.json").write_text("{}")

    def fake_predict(weights, cfg, params, outfile):
        # write something non-empty so we go past the early-return branch
        Path(outfile).write_text(json.dumps([
            {"image_id": 1, "category_id": 0,
             "bbox": [0, 0, 10, 10], "score": 0.9}
        ]))
        return outfile

    fake_coco = _stub_coco([{"area": 100}])
    fake_coco.loadRes = MagicMock(return_value=MagicMock())

    fake_eval = MagicMock()
    # stats: [mAP, mAP@0.5, mAP@0.75, AP_s, AP_m, AP_l, P, R, ...]
    fake_eval.stats = [0.55, 0.80, 0.42, 0.10, 0.30, 0.70, 0.8, 0.6]

    with patch.object(eac, "COCO", return_value=fake_coco), \
         patch.object(eac, "COCOeval", return_value=fake_eval), \
         _patch_predict_module(fake_predict)[0], \
         _patch_predict_module(fake_predict)[1]:

        out = eac.eval_model_on_dataset_coco(
            weights="w.pt",
            data_cfg=_data_cfg(tmp_path / "imgs", tmp_path / "lbls"),
            params={},
            coco_cache=coco_cache,
            pred_cache=pred_cache,
            script_path="/fake.py",
            model_name="m",
        )

    assert out["mAP@0.5:0.95"] == pytest.approx(0.55)
    assert out["mAP@0.5"]      == pytest.approx(0.80)
    assert out["AP_small"]     == pytest.approx(0.10)
    assert out["AP_medium"]    == pytest.approx(0.30)
    assert out["AP_large"]     == pytest.approx(0.70)
    assert out["Precision"]    == pytest.approx(0.8)
    assert out["Recall"]       == pytest.approx(0.6)
    # F1 = 2*0.8*0.6 / (0.8+0.6) = 0.96 / 1.4 = 0.6857142857
    assert out["F1"] == pytest.approx(2 * 0.8 * 0.6 / (0.8 + 0.6), rel=1e-6)


def test_perfect_predictions_give_f1_one(tmp_path):
    """If COCOeval reports P=R=1.0, F1 must be 1.0."""
    coco_cache = tmp_path / "coco"; coco_cache.mkdir()
    pred_cache = tmp_path / "pred"; pred_cache.mkdir()
    (coco_cache / "ds.json").write_text("{}")

    def fake_predict(weights, cfg, params, outfile):
        Path(outfile).write_text(json.dumps(
            [{"image_id": 1, "category_id": 0, "bbox": [0, 0, 10, 10], "score": 0.99}]
        ))
        return outfile

    fake_coco = _stub_coco([{"area": 100}])
    fake_coco.loadRes = MagicMock(return_value=MagicMock())

    fake_eval = MagicMock()
    fake_eval.stats = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

    with patch.object(eac, "COCO", return_value=fake_coco), \
         patch.object(eac, "COCOeval", return_value=fake_eval), \
         _patch_predict_module(fake_predict)[0], \
         _patch_predict_module(fake_predict)[1]:

        out = eac.eval_model_on_dataset_coco(
            weights="w.pt",
            data_cfg=_data_cfg(tmp_path / "imgs", tmp_path / "lbls"),
            params={},
            coco_cache=coco_cache,
            pred_cache=pred_cache,
            script_path="/fake.py",
            model_name="m",
        )

    assert out["F1"] == pytest.approx(1.0, rel=1e-9)
    assert out["Precision"] == 1.0
    assert out["Recall"] == 1.0


def test_zero_precision_and_recall_give_zero_f1_without_division_error(tmp_path):
    """F1 = 2PR/(P+R+eps) -- with P=R=0 must not raise and must yield ~0."""
    coco_cache = tmp_path / "coco"; coco_cache.mkdir()
    pred_cache = tmp_path / "pred"; pred_cache.mkdir()
    (coco_cache / "ds.json").write_text("{}")

    def fake_predict(weights, cfg, params, outfile):
        Path(outfile).write_text(json.dumps(
            [{"image_id": 1, "category_id": 0, "bbox": [0, 0, 1, 1], "score": 0.1}]
        ))
        return outfile

    fake_coco = _stub_coco([{"area": 100}])
    fake_coco.loadRes = MagicMock(return_value=MagicMock())

    fake_eval = MagicMock()
    fake_eval.stats = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    with patch.object(eac, "COCO", return_value=fake_coco), \
         patch.object(eac, "COCOeval", return_value=fake_eval), \
         _patch_predict_module(fake_predict)[0], \
         _patch_predict_module(fake_predict)[1]:

        out = eac.eval_model_on_dataset_coco(
            weights="w.pt",
            data_cfg=_data_cfg(tmp_path / "imgs", tmp_path / "lbls"),
            params={},
            coco_cache=coco_cache,
            pred_cache=pred_cache,
            script_path="/fake.py",
            model_name="m",
        )

    assert out["F1"] == pytest.approx(0.0, abs=1e-9)
