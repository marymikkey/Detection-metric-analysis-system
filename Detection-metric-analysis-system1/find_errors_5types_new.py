import json
import argparse
from collections import defaultdict

def compute_iou(bbox1, bbox2):
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2
    xi1 = max(x1, x2)
    yi1 = max(y1, y2)
    xi2 = min(x1 + w1, x2 + w2)
    yi2 = min(y1 + h1, y2 + h2)
    inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    area1 = w1 * h1
    area2 = w2 * h2
    union = area1 + area2 - inter_area
    return inter_area / union if union > 0 else 0.0

def parse_gt(gt_path):
    with open(gt_path, 'r') as f:
        data = json.load(f)
    images = {}
    for img in data.get('images', []):
        images[img['id']] = {'file_name': img['file_name'], 'width': img['width'], 'height': img['height']}
    annotations = defaultdict(list)
    for ann in data.get('annotations', []):
        annotations[ann['image_id']].append({'category_id': ann['category_id'], 'bbox': ann['bbox']})
    return images, annotations

def parse_detections(det_path):
    with open(det_path, 'r') as f:
        return json.load(f)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gt', required=True)
    parser.add_argument('--det', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--image_root', required=True)
    parser.add_argument('--iou_threshold', type=float, default=0.5)
    parser.add_argument('--conf_threshold', type=float, default=0.4)
    args = parser.parse_args()

    images, gt_annotations = parse_gt(args.gt)
    detections = parse_detections(args.det)

    det_by_img_cat = defaultdict(lambda: defaultdict(list))
    for det in detections:
        det_by_img_cat[det['image_id']][det['category_id']].append({'bbox': det['bbox'], 'score': det['score']})

    output_data = []
    all_image_ids = set(images.keys()) | set(det_by_img_cat.keys())

    for img_id in all_image_ids:
        img_info = images.get(img_id)
        if img_info is None:
            continue
        image_path = f"{args.image_root.rstrip('/')}/{img_info['file_name']}"

        gt_by_cat = defaultdict(list)
        for ann in gt_annotations.get(img_id, []):
            gt_by_cat[ann['category_id']].append(ann)

        all_errors = []
        flags = {'FP': False, 'FN': False, 'LOW_IOU': False, 'LOW_CONF': False, 'DUPLICATE': False}
        all_categories = set(gt_by_cat.keys()) | set(det_by_img_cat[img_id].keys())

        for cat_id in all_categories:
            gt_list = gt_by_cat.get(cat_id, [])
            det_list = det_by_img_cat[img_id].get(cat_id, [])

            if not gt_list:
                for det in det_list:
                    all_errors.append({'type': 'FP', 'bbox': det['bbox']})
                    flags['FP'] = True
                continue

            if not det_list:
                for gt in gt_list:
                    all_errors.append({'type': 'FN', 'bbox': gt['bbox']})
                    flags['FN'] = True
                continue

            # Для каждого детекта вычисляем максимальный IoU и лучший GT
            det_info = []
            for d_idx, det in enumerate(det_list):
                best_iou = 0.0
                best_gt_idx = -1
                for g_idx, gt in enumerate(gt_list):
                    iou = compute_iou(det['bbox'], gt['bbox'])
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_idx = g_idx
                det_info.append((d_idx, det['bbox'], det['score'], best_iou, best_gt_idx))

            # Фильтрация отсечённых: детекции с низким score и низким IoU игнорируются
            kept_det_info = []
            for info in det_info:
                _, _, score, max_iou, _ = info
                if score >= args.conf_threshold or max_iou >= args.iou_threshold:
                    kept_det_info.append(info)

            # Разделяем на хорошие (max_iou >= iou_threshold) и LOW_IOU
            good_dets = []      # max_iou >= iou_threshold
            low_iou_dets = []   # 0 < max_iou < iou_threshold и score >= conf_threshold
            fp_dets = []        # max_iou == 0 и score >= conf_threshold (не отсечены)
            for info in kept_det_info:
                d_idx, bbox, score, max_iou, best_gt_idx = info
                if max_iou >= args.iou_threshold:
                    good_dets.append(info)
                elif max_iou > 0:  # 0 < max_iou < iou_threshold
                    low_iou_dets.append(info)
                else:  # max_iou == 0 и score >= conf_threshold
                    fp_dets.append(info)

            # Обработка FP (нулевой IoU, но высокий confidence)
            for info in fp_dets:
                _, bbox, _, _, _ = info
                all_errors.append({'type': 'FP', 'bbox': bbox})
                flags['FP'] = True

            # Обработка LOW_IOU (ненулевой, но ниже порога) – добавляем значение iou
            for info in low_iou_dets:
                _, bbox, _, max_iou, _ = info
                all_errors.append({'type': 'LOW_IOU', 'bbox': bbox, 'iou': max_iou})
                flags['LOW_IOU'] = True

            # Группировка хороших детекций по лучшему GT
            gt_to_dets = defaultdict(list)  # gt_idx -> list of (det_idx, bbox, score, iou)
            for info in good_dets:
                d_idx, bbox, score, max_iou, best_gt_idx = info
                gt_to_dets[best_gt_idx].append((d_idx, bbox, score, max_iou))

            matched_gt = [False] * len(gt_list)

            for gt_idx, dets in gt_to_dets.items():
                # Сортировка по score (убывание), затем по iou
                dets.sort(key=lambda x: (-x[2], -x[3]))
                primary = dets[0]
                _, primary_bbox, primary_score, _ = primary
                matched_gt[gt_idx] = True

                if primary_score >= args.conf_threshold:
                    # True positive – без ошибки
                    pass
                else:
                    all_errors.append({'type': 'LOW_CONF', 'bbox': primary_bbox, 'confidence': primary_score})
                    flags['LOW_CONF'] = True

                # Остальные детекции для этого GT
                for _, bbox, score, _ in dets[1:]:
                    if score >= args.conf_threshold:
                        all_errors.append({'type': 'DUPLICATE', 'bbox': bbox})
                        flags['DUPLICATE'] = True
                    else:
                        all_errors.append({'type': 'LOW_CONF', 'bbox': bbox, 'confidence': score})
                        flags['LOW_CONF'] = True

            # Несматченные GT -> FN
            for gt_idx, gt in enumerate(gt_list):
                if not matched_gt[gt_idx]:
                    all_errors.append({'type': 'FN', 'bbox': gt['bbox']})
                    flags['FN'] = True

        if all_errors:
            mask = ''.join(str(int(flags[k])) for k in ['FP', 'FN', 'LOW_IOU', 'LOW_CONF', 'DUPLICATE'])
            output_data.append({
                'image_id': img_id,
                'image_path': image_path,
                'mask': mask,
                'errors': all_errors
            })

    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"Done. Output written to {args.output}")

if __name__ == '__main__':
    main()