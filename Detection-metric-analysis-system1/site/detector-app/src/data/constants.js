export const CLRS = [
  '#818cf8','#4ade80','#fbbf24','#f87171','#38bdf8',
  '#e879f9','#fb923c','#a3e635','#22d3ee','#f472b6',
];

export const PRESET_DATASETS = [
  { id: 'coco',  name: 'MS COCO 2017',    classes: 80, images: 118287, desc: 'Large-scale object detection', size: '25 GB' },
  { id: 'voc',   name: 'Pascal VOC 2012', classes: 20, images: 11540,  desc: 'Visual Object Challenge',      size: '2.1 GB' },
  { id: 'kitti', name: 'KITTI Vision',    classes: 8,  images: 14999,  desc: 'Autonomous driving benchmark', size: '12 GB' },
];

export const PRESET_MODELS = [
  { id: 'yolov8n', name: 'YOLOv8n',   params: '3.2M',  gflops: '8.7',  speed: '<1ms', type: 'Nano' },
  { id: 'yolov8s', name: 'YOLOv8s',   params: '11.2M', gflops: '28.6', speed: '~2ms', type: 'Small' },
  { id: 'yolov8m', name: 'YOLOv8m',   params: '25.9M', gflops: '78.9', speed: '~5ms', type: 'Medium' },
  { id: 'rtdetr',  name: 'RT-DETR-L', params: '32M',   gflops: '108',  speed: '~9ms', type: 'Transformer' },
];
