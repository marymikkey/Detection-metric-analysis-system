from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction
from sahi.utils.cv import visualize_object_predictions
import cv2
import os
from ultralytics import YOLO
from pathlib import Path
import json

def predict(weights: str, data_cfg: dict, params: dict, preds_outfile: str) -> str:
    # создаём SAHI-совместимую модель
    detection_model = AutoDetectionModel.from_pretrained(
        model_type="ultralytics",
        model_path=weights,
        confidence_threshold=0.001, #params.get("conf", 0.5),
        device=params.get("device", "cuda:0")
    )

    single_class = len(data_cfg["names"]) == 1
    preds = []

    for img in data_cfg["coco_gt"].dataset["images"]:
        img_path = Path(data_cfg["images"]) / img["file_name"]
        if not img_path.exists():
            continue

        image_id = img["id"]


        image = cv2.imread(str(img_path))
        original_height, original_width = image.shape[:2]

        result = get_sliced_prediction(
            image=str(img_path),
            detection_model=detection_model,
            slice_height=int(original_height / 1.8+1),
            slice_width=int(original_width / 1.8+1),
            overlap_height_ratio=params.get("overlap_height_ratio", 0.2),
            overlap_width_ratio=params.get("overlap_width_ratio", 0.2)
        )

        for det in result.to_coco_predictions(image_id=image_id):
            det["category_id"] = 0 if single_class else det["category_id"]
            preds.append(det)

    with open(preds_outfile, "w") as f:
        json.dump(preds, f, indent=2)

    return preds_outfile
