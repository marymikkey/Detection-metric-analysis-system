import { useRef, useEffect } from 'react';
import { Chart } from 'chart.js/auto';
import { CLRS } from '../../data/constants';

export default function InlineBarChart({ labels, data, color = '#818cf8', horizontal = false, height = 200, colors }) {
  const ref = useRef(null);
  const inst = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    inst.current?.destroy();
    const bgColors = colors || data.map((_, i) => CLRS[i % CLRS.length] + '88');
    const bdColors = colors || data.map((_, i) => CLRS[i % CLRS.length]);
    inst.current = new Chart(ref.current, {
      type: 'bar',
      data: {
        labels,
        datasets: [{ data, backgroundColor: colors ? bgColors : color + '66', borderColor: colors ? bdColors : color, borderWidth: 1, borderRadius: 2 }],
      },
      options: {
        indexAxis: horizontal ? 'y' : 'x',
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ' ' + c.raw.toLocaleString() } } },
        scales: {
          x: { grid: { color: '#1c1f35' }, ticks: { color: '#4e5270', font: { family: 'IBM Plex Mono', size: 9 }, maxTicksLimit: 10 } },
          y: { grid: { color: horizontal ? 'transparent' : '#1c1f35' }, ticks: { color: '#8c91b0', font: { size: horizontal ? 11 : 9 } } },
        },
      },
    });
    return () => inst.current?.destroy();
  }, [labels.join(','), data.join(','), color]);

  return <div style={{ position: 'relative', height }}><canvas ref={ref} /></div>;
}
