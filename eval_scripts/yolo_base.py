from ultralytics import YOLO
from pathlib import Path
import json

def predict(weights: str, data_cfg: dict, params: dict, preds_outfile: str) -> str:
    model = YOLO(weights)
    results = model.predict(source=data_cfg["images"], conf = 0.001, **params)

    single_class = len(data_cfg["names"]) == 1
    file_to_id = {img["file_name"].lower(): img["id"] for img in data_cfg["coco_gt"].dataset["images"]}

    preds = []
    for r in results:
        file_name = Path(r.path).name.lower()
        if file_name not in file_to_id:
            continue
        image_id = file_to_id[file_name]
        for box in r.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            w, h = x2 - x1, y2 - y1
            preds.append({
                "image_id": image_id,
                "category_id": 0 if single_class else int(box.cls),
                "bbox": [x1, y1, w, h],
                "score": float(box.conf)
            })


    with open(preds_outfile, "w") as f:
        json.dump(preds, f, indent=2)

    return preds_outfile
