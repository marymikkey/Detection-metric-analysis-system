"""
Тестируется интерфейс БД db_interface.py.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

import db_interface as dbi


def test_parse_dsn_full_url():
    out = dbi._parse_dsn("postgresql://alice:s3cr3t@db.example:6543/mydb")
    assert out == {
        "user":     "alice",
        "password": "s3cr3t",
        "host":     "db.example",
        "port":     6543,
        "database": "mydb",
    }


def test_parse_dsn_url_encoded_password():
    out = dbi._parse_dsn("postgresql://u:%40hard%23pwd@h:5432/db")
    assert out["password"] == "@hard#pwd"


def test_parse_dsn_defaults_when_missing_parts():
    out = dbi._parse_dsn("postgresql:///pr_bd")
    assert out["host"] == "localhost"
    assert out["port"] == 5432
    assert out["user"] == "postgres"
    assert out["database"] == "pr_bd"


def test_parse_dsn_rejects_other_schemes():
    with pytest.raises(ValueError, match="Unsupported DSN scheme"):
        dbi._parse_dsn("mysql://u:p@h/db")


def test_jsonb_param_roundtrip():
    payload = {"batch": 64, "device": "0", "ru": "значение"}
    encoded = dbi._to_jsonb_param(payload)
    assert json.loads(encoded) == payload


def test_from_jsonb_handles_string():
    assert dbi._from_jsonb('{"x": 1}') == {"x": 1}


def test_from_jsonb_handles_dict_passthrough():
    assert dbi._from_jsonb({"x": 1}) == {"x": 1}


def test_from_jsonb_handles_none():
    assert dbi._from_jsonb(None) is None


def test_from_jsonb_handles_bytes():
    assert dbi._from_jsonb(b'{"y": 2}') == {"y": 2}


def test_from_jsonb_returns_string_when_unparseable():
    assert dbi._from_jsonb("not json") == "not json"


def test_fetch_dicts_zips_columns():
    cur = MagicMock()
    cur.description = [("id",), ("name",)]
    cur.fetchall.return_value = [(1, "a"), (2, "b")]

    out = dbi._fetch_dicts(cur)
    assert out == [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]


def test_fetch_one_dict_returns_none_when_no_row():
    cur = MagicMock()
    cur.fetchone.return_value = None
    assert dbi._fetch_one_dict(cur) is None


def _make_fake_conn(scripted_responses):

    cur = MagicMock()
    descriptions = []
    fetchones = []
    fetchalls = []
    for desc, one, many in scripted_responses:
        descriptions.append(desc)
        fetchones.append(one)
        fetchalls.append(many)

    desc_iter = iter(descriptions)
    one_iter = iter(fetchones)
    many_iter = iter(fetchalls)

    def execute_side_effect(*args, **kwargs):
        cur.description = next(desc_iter)
        cur._next_one = next(one_iter)
        cur._next_many = next(many_iter)

    cur.execute.side_effect = execute_side_effect
    cur.fetchone = lambda: cur._next_one
    cur.fetchall = lambda: cur._next_many

    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn


def test_load_run_config_assembles_expected_dict():
    conn = _make_fake_conn([
        (
            [("id",), ("name",), ("description",), ("single_class",),
             ("output_md",), ("eval_profile_id",), ("eval_profile_name",),
             ("eval_params",)],
            ("uuid-rc", "run_x", "desc", False, "results.md",
             "uuid-ep", "default_eval", '{"batch": 64, "device": "0"}'),
            None,
        ),
        (
            [("id",), ("name",), ("path",), ("description",),
             ("metadata",), ("position",)],
            None,
            [
                ("uuid-d1", "ds1", "/p1.yaml", "first",  None, 1),
                ("uuid-d2", "ds2", "/p2.yaml", None,     None, 2),
            ],
        ),
        (
            [("id",), ("name",), ("weights_path",), ("script_path",),
             ("description",), ("architecture",), ("metadata",), ("position",)],
            None,
            [
                ("uuid-m1", "m1", "/w1.pt", "/s1.py", "model 1", "yolo11s", None, 1),
            ],
        ),
    ])

    with patch.object(dbi, "_open_connection", return_value=conn):
        cfg = dbi.load_run_config("run_x")

    assert cfg["name"] == "run_x"
    assert cfg["description"] == "desc"
    assert cfg["single_class"] is False
    assert cfg["output_md"] == "results.md"
    assert cfg["eval_params"] == {"batch": 64, "device": "0"}

    assert set(cfg["datasets"].keys()) == {"ds1", "ds2"}
    assert cfg["datasets"]["ds1"] == {"path": "/p1.yaml", "description": "first"}
    assert cfg["datasets"]["ds2"]["description"] == ""  # NULL -> ""

    assert set(cfg["models"].keys()) == {"m1"}
    assert cfg["models"]["m1"] == {
        "name":        "m1",
        "weights":     "/w1.pt",
        "script_path": "/s1.py",
        "description": "model 1",
    }


def test_load_run_config_raises_when_not_found():
    conn = _make_fake_conn([
        (
            [("id",), ("name",), ("description",), ("single_class",),
             ("output_md",), ("eval_profile_id",), ("eval_profile_name",),
             ("eval_params",)],
            None,
            [],
        ),
    ])
    with patch.object(dbi, "_open_connection", return_value=conn):
        with pytest.raises(RuntimeError, match="not found in DB"):
            dbi.load_run_config("nope")


def test_create_experiment_inserts_and_returns_uuid():
    cur = MagicMock()
    cur.fetchone.return_value = ("uuid-exp",)
    conn = MagicMock()
    conn.cursor.return_value = cur

    with patch.object(dbi, "_open_connection", return_value=conn):
        eid = dbi.create_experiment(
            run_config_name="run_x",
            dataset_name="ds1",
            model_name="m1",
            eval_params={"batch": 64},
            status="running",
        )

    assert eid == "uuid-exp"
    cur.execute.assert_called_once()
    conn.commit.assert_called_once()


def test_save_metrics_separates_numeric_and_structured():
    cur = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value = cur

    metrics = {
        "mAP@0.5":   0.8,
        "Precision": 0.9,
        "F1":        "0.85",
        "counts":    {"small": 1},
        "ranges":    {"small": (0, 100)},
    }

    with patch.object(dbi, "_open_connection", return_value=conn):
        dbi.save_metrics("uuid-exp", metrics)

    assert cur.execute.call_count == 4
    conn.commit.assert_called_once()


def test_finish_experiment_runs_update_and_commits():
    cur = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value = cur

    with patch.object(dbi, "_open_connection", return_value=conn):
        dbi.finish_experiment("uuid-exp", status="done", log_file="run.log")

    cur.execute.assert_called_once()
    args, _ = cur.execute.call_args
    assert "UPDATE experiments" in args[0]
    assert args[1] == ("done", "run.log", "uuid-exp")
    conn.commit.assert_called_once()


def test_export_eda_run_yaml_writes_correct_format(tmp_path):
    fake_cfg = {
        "name":         "run_x",
        "description":  "",
        "single_class": False,
        "output_md":    None,
        "eval_params":  {},
        "datasets": {
            "ds1": {"path": "/a.yaml", "description": ""},
            "ds2": {"path": "/b.yaml", "description": ""},
        },
        "models":   {},
    }

    out_path = tmp_path / "eda.yaml"
    with patch.object(dbi, "load_run_config", return_value=fake_cfg):
        result_path = dbi.export_eda_run_yaml(
            "run_x", str(out_path), selected_splits=["test", "val"]
        )

    assert str(result_path) == str(out_path.resolve()) or result_path.endswith("eda.yaml")

    import yaml
    data = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert "datasets" in data
    yaml_paths = [d["yaml_path"] for d in data["datasets"]]
    assert yaml_paths == ["/a.yaml", "/b.yaml"]
    for d in data["datasets"]:
        assert d["selected_splits"] == ["test", "val"]
