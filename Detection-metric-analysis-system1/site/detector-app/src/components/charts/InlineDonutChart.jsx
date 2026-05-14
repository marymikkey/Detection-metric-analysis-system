import { useRef, useEffect } from 'react';
import { Chart } from 'chart.js/auto';

export default function InlineDonutChart({ labels, data, colors, height = 170, centerLabel }) {
  const ref = useRef(null);
  const inst = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    inst.current?.destroy();
    inst.current = new Chart(ref.current, {
      type: 'doughnut',
      data: { labels, datasets: [{ data, backgroundColor: colors.map(c => c + 'bb'), borderColor: colors, borderWidth: 1 }] },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '68%',
        plugins: { legend: { position: 'bottom', labels: { color: '#8c91b0', font: { size: 10 }, boxWidth: 10, padding: 10 } } },
      },
    });
    return () => inst.current?.destroy();
  }, [data.join(',')]);

  return (
    <div style={{ position: 'relative', height }}>
      <canvas ref={ref} />
      {centerLabel && (
        <div style={{ position: 'absolute', top: '36%', left: 0, right: 0, textAlign: 'center', pointerEvents: 'none' }}>
          <div style={{ fontFamily: 'Syne', fontSize: 18, fontWeight: 800 }}>{centerLabel.val}</div>
          <div style={{ fontSize: 8, color: 'var(--muted)', letterSpacing: '.1em' }}>{centerLabel.sub}</div>
        </div>
      )}
    </div>
  );
}
