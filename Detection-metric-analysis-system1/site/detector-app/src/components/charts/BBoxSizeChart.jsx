import { useMemo } from 'react';
import InlineBarChart from './InlineBarChart';

function binArray(values, numBins) {
  if (!values?.length) return { labels: [], data: [] };
  const min = Math.min(...values), max = Math.max(...values);
  const range = max - min || 1;
  const bw = range / numBins;
  const counts = new Array(numBins).fill(0);
  values.forEach(v => { counts[Math.min(Math.floor((v - min) / bw), numBins - 1)]++; });
  return {
    labels: Array.from({ length: numBins }, (_, i) => (min + i * bw).toFixed(0)),
    data: counts,
  };
}

export function BBoxAreaChart({ areas, height = 130, numBins = 60 }) {
  const { labels, data } = useMemo(() => binArray(areas, numBins), [areas, numBins]);
  return <InlineBarChart labels={labels} data={data} color="#fb923c" height={height} />;
}

export default function BBoxSizeChart({ widths, heights, height = 140 }) {
  const wBins = useMemo(() => binArray(widths, 40), [widths]);
  const hBins = useMemo(() => binArray(heights, 40), [heights]);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
      <div>
        <div style={{ fontSize: 10, color: 'var(--text2)', marginBottom: 6 }}>Width (px)</div>
        <InlineBarChart labels={wBins.labels} data={wBins.data} color="#38bdf8" height={height} />
      </div>
      <div>
        <div style={{ fontSize: 10, color: 'var(--text2)', marginBottom: 6 }}>Height (px)</div>
        <InlineBarChart labels={hBins.labels} data={hBins.data} color="#4ade80" height={height} />
      </div>
    </div>
  );
}
