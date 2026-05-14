export function getMetrics(modelId, datasetId) {
  const base = {
    coco:  { map50: .892, map5095: .712, p: .874, r: .851 },
    voc:   { map50: .938, map5095: .761, p: .921, r: .889 },
    kitti: { map50: .963, map5095: .789, p: .947, r: .921 },
  };
  const boost = { yolov8n: 0, yolov8s: .018, yolov8m: .031, rtdetr: .042 };
  const b = base[datasetId] || base.coco;
  const d = boost[modelId] || 0;
  const speed = { yolov8n: 0.8, yolov8s: 1.9, yolov8m: 5.1, rtdetr: 9.3 };
  return {
    map50:    Math.min(.99, b.map50 + d),
    map5095:  Math.min(.99, b.map5095 + d * .9),
    p:        Math.min(.99, b.p + d * .8),
    r:        Math.min(.99, b.r + d * .7),
    msPerImg: speed[modelId] || 5.0,
  };
}

export function genValStream(totalImages, batchSize, modelId, datasetId) {
  const m = getMetrics(modelId, datasetId);
  const nBatches = Math.ceil(totalImages / batchSize);
  let s = 1234;
  const rng = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
  return Array.from({ length: nBatches }, (_, i) => {
    const prog = Math.min(1, (i + 1) / nBatches);
    const warm = Math.min(1, prog * 4);
    return {
      batch:    i + 1,
      images:   Math.min((i + 1) * batchSize, totalImages),
      map50:    +(m.map50    * warm * (0.97 + rng() * .06 - .03)).toFixed(4),
      map5095:  +(m.map5095  * warm * (0.97 + rng() * .06 - .03)).toFixed(4),
      p:        +(m.p        * warm * (0.97 + rng() * .06 - .03)).toFixed(4),
      r:        +(m.r        * warm * (0.97 + rng() * .06 - .03)).toFixed(4),
      msPerImg: +(m.msPerImg * (1 + rng() * .3 - .15)).toFixed(1),
    };
  });
}
