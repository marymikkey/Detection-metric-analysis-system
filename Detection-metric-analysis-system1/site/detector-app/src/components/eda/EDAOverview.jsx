import { EDA_REPORT } from '../../data/edaReport';
import { CLRS } from '../../data/constants';
import Card from '../ui/Card';
import MonoLabel from '../ui/MonoLabel';
import InlineBarChart from '../charts/InlineBarChart';
import InlineGroupedBar from '../charts/InlineGroupedBar';

export default function EDAOverview({ datasets, reports: apiReports = {} }) {
  const reports = datasets.map(d => {
    const r = apiReports[d.id] || EDA_REPORT[d.id] || EDA_REPORT.coco;
    return { ...r, _id: d.id, _name: d.name, _overall: r._singleSplit ? r : r.splits.overall };
  });
  const imageData = reports.map(r => r._overall.images_total);
  const objData = reports.map(r => r._overall.objects_total);
  const names = reports.map(r => r._name);

  const classSets = reports.map(r => new Set(Object.values(r.class_names).map(s => s.toLowerCase())));
  const allClasses = [...new Set(classSets.flatMap(s => [...s]))].sort();
  const overlapClasses = allClasses.filter(cls => classSets.filter(s => s.has(cls)).length > 1);

  const sizeDs = [
    { label: 'Small',  data: reports.map(r => r.small_count)  },
    { label: 'Medium', data: reports.map(r => r.medium_count) },
    { label: 'Large',  data: reports.map(r => r.large_count)  },
  ];

  const n = v => v != null ? v.toLocaleString() : '—';

  return (
    <div style={{ padding: '18px 24px 48px', overflowY: 'auto', height: '100%' }}>
      <MonoLabel style={{ marginBottom: 14 }}>Сравнение датасетов</MonoLabel>

      {/* Summary table */}
      <Card style={{ padding: 0, marginBottom: 14, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              {['Датасет', 'Изображений', 'Объектов', 'Классов', 'Splits', 'Channels', 'Resolution'].map(h => (
                <th key={h} style={{ fontFamily: 'IBM Plex Mono', fontSize: 9, color: 'var(--muted)', fontWeight: 400, textAlign: 'left', padding: '10px 14px' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {reports.map((r, i) => (
              <tr key={r._id} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,.01)' }}>
                <td style={{ padding: '10px 14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 8, height: 8, borderRadius: '50%', background: CLRS[i % CLRS.length], flexShrink: 0 }} />
                    <span style={{ fontFamily: 'Syne', fontWeight: 700, fontSize: 12 }}>{r.title}</span>
                  </div>
                </td>
                <td style={{ fontFamily: 'IBM Plex Mono', fontSize: 11, padding: '10px 14px' }}>{n(r._overall.images_total)}</td>
                <td style={{ fontFamily: 'IBM Plex Mono', fontSize: 11, padding: '10px 14px' }}>{n(r._overall.objects_total)}</td>
                <td style={{ fontFamily: 'IBM Plex Mono', fontSize: 11, padding: '10px 14px' }}>{r._overall.nc}</td>
                <td style={{ fontFamily: 'IBM Plex Mono', fontSize: 11, padding: '10px 14px' }}>{r._singleSplit ? 'test' : r.selected_splits.join('/')}</td>
                <td style={{ fontFamily: 'IBM Plex Mono', fontSize: 11, padding: '10px 14px', color: r.unified_channels ? 'var(--green)' : 'var(--amber)' }}>{r.unified_channels ? '✓ Unified' : '✗ Mixed'}</td>
                <td style={{ fontFamily: 'IBM Plex Mono', fontSize: 11, padding: '10px 14px', color: r.unified_resolution ? 'var(--green)' : 'var(--muted)' }}>{r.unified_resolution ? '✓ Fixed' : 'Variable'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Bar charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        <Card style={{ padding: '14px 18px' }}>
          <MonoLabel style={{ marginBottom: 10 }}>Изображений по датасетам</MonoLabel>
          <InlineBarChart labels={names} data={imageData} colors={CLRS.slice(0, names.length)} height={160} />
        </Card>
        <Card style={{ padding: '14px 18px' }}>
          <MonoLabel style={{ marginBottom: 10 }}>Объектов по датасетам</MonoLabel>
          <InlineBarChart labels={names} data={objData} colors={CLRS.slice(0, names.length)} height={160} />
        </Card>
      </div>

      {/* Size grouped */}
      <Card style={{ padding: '14px 18px', marginBottom: 12 }}>
        <MonoLabel style={{ marginBottom: 10 }}>Распределение размеров объектов (Small/Medium/Large)</MonoLabel>
        <InlineGroupedBar labels={names} datasets={sizeDs} height={200} />
      </Card>

      {/* Class overlap */}
      {overlapClasses.length > 0 && (
        <Card style={{ padding: '14px 18px' }}>
          <MonoLabel style={{ marginBottom: 12 }}>Общие классы ({overlapClasses.length} пересечений)</MonoLabel>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {overlapClasses.map(cls => {
              const inWhich = reports.filter(r => new Set(Object.values(r.class_names).map(s => s.toLowerCase())).has(cls));
              return (
                <div key={cls} style={{ padding: '4px 10px', borderRadius: 20, background: 'var(--accent-dim)', border: '1px solid var(--accent)22', fontSize: 10, color: 'var(--accent)' }}>
                  {cls} <span style={{ color: 'var(--muted)', fontSize: 9 }}>×{inWhich.length}</span>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}
