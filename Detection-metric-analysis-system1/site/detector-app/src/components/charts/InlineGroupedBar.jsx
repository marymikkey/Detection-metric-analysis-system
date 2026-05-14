import { useRef, useEffect } from 'react';
import { Chart } from 'chart.js/auto';
import { CLRS } from '../../data/constants';

export default function InlineGroupedBar({ labels, datasets, height = 220 }) {
  const ref = useRef(null);
  const inst = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    inst.current?.destroy();
    inst.current = new Chart(ref.current, {
      type: 'bar',
      data: {
        labels,
        datasets: datasets.map((ds, i) => ({
          ...ds,
          backgroundColor: CLRS[i % CLRS.length] + '88',
          borderColor: CLRS[i % CLRS.length],
          borderWidth: 1,
          borderRadius: 2,
        })),
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'top', align: 'end', labels: { color: '#8c91b0', font: { size: 10 }, boxWidth: 12, padding: 12 } } },
        scales: {
          x: { grid: { color: '#1c1f35' }, ticks: { color: '#4e5270', font: { family: 'IBM Plex Mono', size: 9 } } },
          y: { grid: { color: '#1c1f35' }, ticks: { color: '#4e5270', font: { family: 'IBM Plex Mono', size: 9 } } },
        },
      },
    });
    return () => inst.current?.destroy();
  }, [JSON.stringify(datasets)]);

  return <div style={{ position: 'relative', height }}><canvas ref={ref} /></div>;
}
