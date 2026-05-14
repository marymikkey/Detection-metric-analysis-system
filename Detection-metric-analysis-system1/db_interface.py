#!/usr/bin/env python3
# coding: utf-8

from __future__ import annotations

import json as _json
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, unquote

import pg8000.dbapi


DEFAULT_DB_URL = (
    os.environ.get("DATABASE_URL")
    or "postgresql://postgres:postgres@localhost:5432/pr_bd"
)


def _parse_dsn(url: str) -> Dict[str, Any]:
    u = urlparse(url)
    if u.scheme not in ("postgresql", "postgres"):
        raise ValueError(f"Unsupported DSN scheme: {u.scheme!r} (expected postgresql://)")
    return {
        "user":     unquote(u.username) if u.username else "postgres",
        "password": unquote(u.password) if u.password else None,
        "host":     u.hostname or "localhost",
        "port":     u.port or 5432,
        "database": (u.path or "/").lstrip("/") or "postgres",
    }


def _open_connection(url: str):
    params = _parse_dsn(url)
    try:
        return pg8000.dbapi.connect(**params)
    except pg8000.dbapi.DatabaseError as e:
        raise RuntimeError(
            "PostgreSQL connection failed.\n"
            f"  DSN:    {url}\n"
            f"  Params: user={params['user']} host={params['host']} "
            f"port={params['port']} database={params['database']}\n"
            f"  Server: {e}\n"
            "Check DB name, user/password, port. Override via --db-url or $DATABASE_URL."
        ) from e


@contextmanager
def connect(db_url: Optional[str] = None):
    url = db_url or DEFAULT_DB_URL
    conn = _open_connection(url)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _fetch_dicts(cur) -> List[Dict[str, Any]]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _fetch_one_dict(cur) -> Optional[Dict[str, Any]]:
    row = cur.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def _to_jsonb_param(value: Any) -> str:
    return _json.dumps(value, ensure_ascii=False, default=str)


def _from_jsonb(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        try:
            return _json.loads(value)
        except Exception:
            return value
    return value

def load_run_config(run_config_name: str, db_url: Optional[str] = None) -> Dict[str, Any]:
    with connect(db_url) as conn:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT rc.id, rc.name, rc.description, rc.single_class, rc.output_md,
                   ep.id   AS eval_profile_id,
                   ep.name AS eval_profile_name,
                   ep.params AS eval_params
            FROM run_configs rc
            JOIN eval_profiles ep ON ep.id = rc.eval_profile_id
            WHERE rc.name = %s
            """,
            (run_config_name,),
        )
        rc = _fetch_one_dict(cur)
        if rc is None:
            raise RuntimeError(f"run_config '{run_config_name}' not found in DB")

        cur.execute(
            """
            SELECT d.id, d.name, d.path, d.description, d.metadata, rcd.position
            FROM run_config_datasets rcd
            JOIN datasets d ON d.id = rcd.dataset_id
            WHERE rcd.run_config_id = %s
            ORDER BY rcd.position, d.name
            """,
            (rc["id"],),
        )
        datasets_rows = _fetch_dicts(cur)

        cur.execute(
            """
            SELECT m.id, m.name, m.weights_path, m.script_path, m.description,
                   m.architecture, m.metadata, rcm.position
            FROM run_config_models rcm
            JOIN models m ON m.id = rcm.model_id
            WHERE rcm.run_config_id = %s
            ORDER BY rcm.position, m.name
            """,
            (rc["id"],),
        )
        models_rows = _fetch_dicts(cur)

    datasets: Dict[str, Dict[str, Any]] = {}
    for d in datasets_rows:
        datasets[d["name"]] = {
            "path":        d["path"],
            "description": d["description"] or "",
        }

    models: Dict[str, Dict[str, Any]] = {}
    for m in models_rows:
        models[m["name"]] = {
            "name":        m["name"],
            "weights":     m["weights_path"],
            "script_path": m["script_path"],
            "description": m["description"] or "",
        }

    return {
        "name":         rc["name"],
        "description":  rc["description"] or "",
        "single_class": bool(rc["single_class"]),
        "output_md":    rc["output_md"],
        "eval_params":  _from_jsonb(rc["eval_params"]) or {},
        "datasets":     datasets,
        "models":       models,
    }

def create_experiment(
    run_config_name: str,
    dataset_name: str,
    model_name: str,
    eval_params: Dict[str, Any],
    status: str = "running",
    db_url: Optional[str] = None,
):
    with connect(db_url) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO experiments (run_config_id, model_id, dataset_id,
                                     eval_params, status, started_at)
            SELECT rc.id, m.id, d.id, %s::jsonb, %s, NOW()
            FROM run_configs rc, datasets d, models m
            WHERE rc.name = %s AND d.name = %s AND m.name = %s
            RETURNING id
            """,
            (
                _to_jsonb_param(eval_params or {}),
                status,
                run_config_name,
                dataset_name,
                model_name,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None


def save_metrics(
    experiment_id,
    metrics: Dict[str, Any],
    db_url: Optional[str] = None,
) -> None:
    numeric = {}
    structured = {}
    for k, v in metrics.items():
        try:
            numeric[k] = float(v)
        except (TypeError, ValueError):
            structured[k] = v

    with connect(db_url) as conn:
        cur = conn.cursor()
        for k, v in numeric.items():
            cur.execute(
                """
                INSERT INTO metrics (experiment_id, metric_name, metric_value, group_type)
                VALUES (%s, %s, %s, 'scalar')
                """,
                (experiment_id, k, v),
            )
        if structured:
            cur.execute(
                """
                INSERT INTO metrics (experiment_id, metric_name, group_type, metadata)
                VALUES (%s, 'stats', 'summary', %s::jsonb)
                """,
                (experiment_id, _to_jsonb_param(structured)),
            )
        conn.commit()


def finish_experiment(
    experiment_id,
    status: str,
    log_file: Optional[str] = None,
    db_url: Optional[str] = None,
) -> None:
    with connect(db_url) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE experiments
            SET status = %s,
                completed_at = NOW(),
                log_file = COALESCE(%s, log_file)
            WHERE id = %s
            """,
            (status, log_file, experiment_id),
        )
        conn.commit()

def export_eda_run_yaml(
    run_config_name: str,
    out_yaml_path: str,
    selected_splits: Optional[List[str]] = None,
    db_url: Optional[str] = None,
) -> str:
    """здесь нужно написать ямл файл для eda.py основанный на БДшном run_config."""
    import yaml
    if selected_splits is None:
        selected_splits = ["test"]

    cfg = load_run_config(run_config_name, db_url=db_url)

    data = {
        "datasets": [
            {"yaml_path": entry["path"], "selected_splits": list(selected_splits)}
            for _, entry in cfg["datasets"].items()
        ]
    }

    out_path = os.path.abspath(out_yaml_path)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    return out_path


def _cli():
    import argparse

    p = argparse.ArgumentParser(description="db_interface.py CLI helpers")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_show = sub.add_parser("show", help="Print run_config as JSON")
    p_show.add_argument("run_config")
    p_show.add_argument("--db-url", default=DEFAULT_DB_URL)

    p_ping = sub.add_parser("ping", help="Try to connect and print server version")
    p_ping.add_argument("--db-url", default=DEFAULT_DB_URL)

    p_eda = sub.add_parser("export-eda-yaml", help="Write a Run YAML for eda/eda.py")
    p_eda.add_argument("run_config")
    p_eda.add_argument("-o", "--out", required=True)
    p_eda.add_argument("--splits", nargs="+", default=["test"])
    p_eda.add_argument("--db-url", default=DEFAULT_DB_URL)

    args = p.parse_args()

    if args.cmd == "show":
        cfg = load_run_config(args.run_config, db_url=args.db_url)
        print(_json.dumps(cfg, indent=2, ensure_ascii=False, default=str))
    elif args.cmd == "ping":
        with connect(args.db_url) as conn:
            cur = conn.cursor()
            cur.execute("SELECT version()")
            ver = cur.fetchone()[0]
            print(f"[ok] connected to {args.db_url}")
            print(f"     {ver}")
    elif args.cmd == "export-eda-yaml":
        out = export_eda_run_yaml(
            args.run_config, args.out,
            selected_splits=args.splits, db_url=args.db_url,
        )
        print(f"[ok] wrote {out}")


if __name__ == "__main__":
    _cli()
