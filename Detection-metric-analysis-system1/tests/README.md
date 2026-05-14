# tests/ — модульные тесты расчёта метрик

Юнит‑тесты для функций из `eval_all_coco.py` и `db_interface.py`. Не требуют
поднятого Postgres, не требуют YOLO/весов и не лезут в реальные датасеты —
тяжёлые зависимости (`pycocotools.COCO`, `pycocotools.COCOeval`,
`pg8000.dbapi.connect`, динамически загружаемый `predict()`) подменяются
заглушками.

## Как запустить

Из корня `Detection-metric-analysis-system/`:

```bash
pip install -r requirements.txt pytest pytest-cov
pytest -v
```

С покрытием:

```bash
pytest -v --cov=. --cov-report=term-missing
```

Запустить только один файл:

```bash
pytest -v tests/test_eval_pipeline.py
```

Запустить один конкретный тест:

```bash
pytest -v tests/test_eval_pipeline.py::test_perfect_predictions_give_f1_one
```

## Что покрыто

| Файл | Что проверяет |
|------|---------------|
| `test_fmt.py` | Форматирование `fmt()`: отрицательные/None → `"-"`, положительные → 4 знака. |
| `test_count_objects_by_size.py` | Корректность бинов small/medium/large по площади (включая граничные значения и пустой датасет). |
| `test_yolo_to_coco.py` | Конверсия YOLO→COCO: один бокс, несколько классов, битые строки, label без image, несколько каталогов. Использует реальные `tmp_path` + Pillow. |
| `test_load_cfg.py` | `load_dataset_cfg` (ветки `test`/`val`, `single_class`, `RuntimeError` при отсутствии `test`/`val`, список путей) и `load_model_cfg` (dict-вход и legacy-строка). |
| `test_eval_pipeline.py` | `eval_model_on_dataset_coco` целиком: пустые предсказания → `default_metrics`; известные `stats[..]` от `COCOeval` → корректное собирание dict; `F1 = 2PR/(P+R)`; идеальные P=R=1 → F1=1; нулевые P=R → F1=0 без ZeroDivisionError. |
| `test_db_interface.py` | DSN-парсер (URL-encoding, дефолты, отказ на чужой схеме), JSONB-хелперы, `_fetch_dicts`, `load_run_config`, `create_experiment`, `save_metrics`, `finish_experiment`, `export_eda_run_yaml`. |

## Принципы

- Тесты **детерминированные** — не зависят от ОС, GPU, локали и сети.
- Где можно, эталонные значения посчитаны **аналитически** (bbox = `[40,40,20,20]` для cx=cy=0.5 w=h=0.2 на 100×100 — проверяется руками), это ловит регрессии в нашей обёртке независимо от обновлений `pycocotools`.
- Где требуется внешний компонент (БД, COCOeval, динамически грузимый `predict.py`) — он подменяется через `unittest.mock`.
