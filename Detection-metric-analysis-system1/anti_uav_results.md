# Evaluation results
Generated at: 2026-05-14 23:02:15.875298


## Dataset: ANTI-UAV_visible_day_medium_1seq_124000_1_6

    Description: ANTI-UAV visible day medium, one sequence 20190925_124000_1_6

| Model               | mAP@0.5 | mAP@0.5:0.95 | AP_small | AP_medium | AP_large | Precision | Recall | F1     |
|---------------------|---------|--------------|----------|-----------|----------|-----------|--------|--------|
| yolo12s_120326_base | 0.4183  | 0.0697       | -        | -         | 0.0774   | 0.1466    | 0.1694 | 0.1571 |
| best_base           | 0.8733  | 0.3724       | -        | -         | 0.3772   | 0.4480    | 0.4917 | 0.4688 |

### GT object counts
    - small: 0 (area 0–1024), avg_area=None
    - medium: 0 (area 1024–9216), avg_area=None
    - large: 421 (area 9216–1000000000000.0), avg_area=14894.926964751507


## Dataset: ANTI-UAV_visible_day_medium_2seq

    Description: ANTI-UAV visible day medium, two sequences 20190925_134301_1_3 and 20190925_134301_1_4

| Model               | mAP@0.5 | mAP@0.5:0.95 | AP_small | AP_medium | AP_large | Precision | Recall | F1     |
|---------------------|---------|--------------|----------|-----------|----------|-----------|--------|--------|
| yolo12s_120326_base | 0.6329  | 0.1763       | -        | 0.1962    | 0.0583   | 0.2320    | 0.3282 | 0.2719 |
| best_base           | 0.8146  | 0.4016       | -        | 0.4088    | 0.3396   | 0.4745    | 0.5094 | 0.4913 |

### GT object counts
    - small: 0 (area 0–1024), avg_area=None
    - medium: 1739 (area 1024–9216), avg_area=7586.0288038242625
    - large: 175 (area 9216–1000000000000.0), avg_area=10064.78267452021


## Models Description

### Model 1
    Name in results: yolo12s_120326_base
    Weights path: C:/system_analytics/yolo12s_120326_best.pt
    Script path: C:/system_analytics/Detection-metric-analysis-system1/eval_scripts/yolo_base.py
    Description: Local YOLO12s weights yolo12s_120326_best.pt

### Model 2
    Name in results: best_base
    Weights path: C:/system_analytics/best.pt
    Script path: C:/system_analytics/Detection-metric-analysis-system1/eval_scripts/yolo_base.py
    Description: Local best.pt model


## Datasets Information

### ANTI-UAV_visible_day_medium_1seq_124000_1_6
    Path: C:/system_analytics/anti_uav_visible_day_medium_1_seq_124000_1_6.yaml
    Description: ANTI-UAV visible day medium, one sequence 20190925_124000_1_6

### ANTI-UAV_visible_day_medium_2seq
    Path: C:/system_analytics/Anti_UAV_vis_2seq.yaml
    Description: ANTI-UAV visible day medium, two sequences 20190925_134301_1_3 and 20190925_134301_1_4
