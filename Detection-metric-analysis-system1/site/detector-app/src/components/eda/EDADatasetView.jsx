import { useState, useMemo } from 'react';
import { EDA_REPORT } from '../../data/edaReport';
import { adaptRealReport } from '../../data/edaAdapter';
import sampleEdaReport from '../../data/sampleEdaReport.json';
import Card from '../ui/Card';
import MonoLabel from '../ui/MonoLabel';
import KpiCard from '../ui/KpiCard';
import HealthPill from '../ui/HealthPill';
import CopyPath from '../ui/CopyPath';
import ChannelBar from '../ui/ChannelBar';
import ConditionsBlock from '../ui/ConditionsBlock';
import InlineBarChart from '../charts/InlineBarChart';
import InlineDonutChart from '../charts/InlineDonutChart';
import IntensityChart from '../charts/IntensityChart';
import BBoxCenterHeatmap from '../charts/BBoxCenterHeatmap';
import BBoxSizeChart, { BBoxAreaChart } from '../charts/BBoxSizeChart';

// Computed once at module load — input is a constant JSON import
const ANTIUAV_REPORT = adaptRealReport(sampleEdaReport);

function resolveReport(datasetId) {
  if (datasetId === 'antiuav_sample') return ANTIUAV_REPORT;
  return EDA_REPORT[datasetId] || EDA_REPORT.coco;
}

export default function EDADatasetView({ datasetId, report: apiReport }) {
  const [activeSplit, setActiveSplit] = useState('overall');
  const [classSearch, setClassSearch] = useState('');
  const [classSort, setClassSort] = useState('count');
  const [condTab, setCondTab] = useState('image');

  const report = useMemo(() => apiReport || resolveReport(datasetId), [datasetId, apiReport]);
  const isSingle = !!report._singleSplit;

  // For legacy multi-split reports, sd comes from splits[activeSplit].
  // For single-split (real) reports, stats live at the top level.
  const sd = isSingle ? report : (report.splits[activeSplit] || report.splits.overall);

  const totalObjs = Object.values(report.class_distribution).reduce((a, b) => a + b, 0) || 1;

  const classEntries = Object.entries(report.class_names).map(([id, name]) => ({
    id: +id, name,
    count: report.class_distribution[id] || 0,
    pct: (report.class_distribution[id] || 0) / totalObjs * 100,
  }));
  const filteredClasses = classEntries
    .filter(c => !classSearch || c.name.toLowerCase().includes(classSearch.toLowerCase()))
    .sort((a, b) => classSort === 'count' ? b.count - a.count : classSort === 'alpha' ? a.name.localeCompare(b.name) : a.id - b.id);
  const maxCC = Math.max(...classEntries.map(c => c.count), 1);

  const opiKeys = Object.keys(report.objects_per_image).map(Number).sort((a, b) => a - b);
  const opiVals = opiKeys.map(k => report.objects_per_image[k]);

  const resEntries = Object.entries(report.resolutions).sort((a, b) => b[1] - a[1]);

  const smallThresh  = report.small_area_threshold  || 1024;
  const medThresh    = report.medium_area_threshold || 9216;
  const splits       = isSingle ? [] : ['overall', ...(report.selected_splits || [])];

  const n   = v => v != null ? v.toLocaleString() : '—';
  const pct = (v, t) => t ? ((v / t) * 100).toFixed(1) + '%' : '—';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div style={{ flexShrink: 0, borderBottom: '1px solid var(--border)', padding: '6px 20px', background: 'var(--surf)', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 9, padding: '2px 7px', background: 'var(--accent-dim)', color: 'var(--accent)', borderRadius: 4 }}>
          {report.yaml_name}
        </span>
        <CopyPath path={report.group_key} />
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 9, color: 'var(--muted)' }}>{report.generation_time}</span>
          {isSingle
            ? <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 9, padding: '2px 8px', background: 'var(--accent-dim)', color: 'var(--accent)', borderRadius: 20, border: '1px solid var(--accent)33', letterSpacing: '.06em' }}>
                {report.target_split?.toUpperCase()}
              </span>
            : <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 9, padding: '2px 8px', border: '1px solid var(--border)', borderRadius: 20, color: 'var(--text2)' }}>
                {report.split_interpretation_mode}
              </span>
          }
        </div>
      </div>

      {/* ── Analyzed image dirs (only for real reports) ──────────────── */}
      {isSingle && report.analyzed_image_dirs?.length > 0 && (
        <div style={{ flexShrink: 0, background: 'var(--surf)', borderBottom: '1px solid var(--border)', padding: '0 20px' }}>
          <details>
            <summary style={{ padding: '5px 0', cursor: 'pointer', fontSize: 10, color: 'var(--muted)', fontFamily: 'IBM Plex Mono', letterSpacing: '.08em', userSelect: 'none' }}>
              ANALYZED DIRS ({report.analyzed_image_dirs.length})
            </summary>
            <div style={{ paddingBottom: 8, display: 'flex', flexDirection: 'column', gap: 3 }}>
              {report.analyzed_image_dirs.map((p, i) => <CopyPath key={i} path={p} />)}
            </div>
          </details>
        </div>
      )}

      {/* ── Split tabs (legacy only) ──────────────────────────────────── */}
      {!isSingle && (
        <div style={{ flexShrink: 0, borderBottom: '1px solid var(--border)', padding: '0 20px', background: 'var(--surf)', display: 'flex' }}>
          {splits.map(s => (
            <div key={s} onClick={() => setActiveSplit(s)} style={{ padding: '7px 13px', cursor: 'pointer', fontSize: 10, fontFamily: 'IBM Plex Mono', letterSpacing: '.1em', textTransform: 'uppercase', borderBottom: `2px solid ${activeSplit === s ? 'var(--accent)' : 'transparent'}`, color: activeSplit === s ? 'var(--accent)' : 'var(--text2)', transition: 'all .15s' }}>
              {s}
            </div>
          ))}
        </div>
      )}

      {/* ── Scrollable content ───────────────────────────────────────── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px 40px' }}>

        {/* KPI row 1 */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 7, marginBottom: 7 }}>
          <KpiCard label="Images"      value={n(sd.images_total)}  color="var(--accent)" />
          <KpiCard label="Objects"     value={n(sd.objects_total)} color="#a78bfa" />
          <KpiCard label="Classes (nc)" value={sd.nc ?? '—'}        color="var(--text2)" />
          <KpiCard
            label="Background"
            value={n(sd.background_images)}
            sub={pct(sd.background_images, sd.images_total)}
            color="var(--muted)"
            hint={report.background_definition || undefined}
          />
        </div>

        {/* KPI row 2 */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 7, marginBottom: isSingle ? 7 : 12 }}>
          <KpiCard label="Broken labels"  value={n(sd.broken_label_lines)}  color={sd.broken_label_lines  > 0 ? 'var(--red)'   : 'var(--green)'} warn={sd.broken_label_lines  > 0} />
          <KpiCard label="Missing labels" value={n(sd.missing_label_files)} color={sd.missing_label_files > 0 ? 'var(--amber)' : 'var(--green)'} warn={sd.missing_label_files > 0} />
          <KpiCard label="Min obj / img"  value={n(sd.min_objects_per_image)} color="var(--text2)" />
          <KpiCard label="Max obj / img"  value={n(sd.max_objects_per_image)} color="var(--text2)" />
        </div>

        {/* KPI row 3 — real reports only */}
        {isSingle && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 7, marginBottom: 12 }}>
            <KpiCard label="Empty labels"       value={n(report.empty_label_files)}       color={report.empty_label_files       > 0 ? 'var(--amber)' : 'var(--green)'} warn={report.empty_label_files       > 0} />
            <KpiCard label="Corrupted images"   value={n(report.corrupted_label_images)}  color={report.corrupted_label_images  > 0 ? 'var(--red)'   : 'var(--green)'} warn={report.corrupted_label_images  > 0} />
            <KpiCard
              label="Size thresholds"
              value={`<${smallThresh} | <${medThresh}`}
              sub="px² S | M bounds"
              color="var(--muted)"
            />
          </div>
        )}

        {/* Health */}
        <Card style={{ padding: '9px 16px', marginBottom: 12, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: 9, color: 'var(--muted)', fontFamily: 'IBM Plex Mono', letterSpacing: '.1em', marginRight: 4 }}>DATASET HEALTH</span>
          <HealthPill label="Unified resolution" ok={report.unified_resolution} />
          <HealthPill label="Unified channels"   ok={report.unified_channels} />
          <HealthPill label="Condition metadata" ok={report.condition_metadata_present} />
        </Card>

        {/* Class distribution */}
        <Card style={{ padding: '14px 18px', marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
            <MonoLabel>Class distribution</MonoLabel>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
              {classEntries.length > 8 && (
                <input value={classSearch} onChange={e => setClassSearch(e.target.value)} placeholder="Filter…"
                  style={{ padding: '3px 8px', background: 'var(--surf2)', border: '1px solid var(--border)', borderRadius: 5, color: 'var(--text)', fontFamily: 'IBM Plex Mono', fontSize: 9, width: 110 }} />
              )}
              {['count', 'alpha', 'id'].map(s => (
                <div key={s} onClick={() => setClassSort(s)} style={{ padding: '2px 7px', borderRadius: 4, cursor: 'pointer', fontSize: 9, fontFamily: 'IBM Plex Mono', border: `1px solid ${classSort === s ? 'var(--accent)' : 'var(--border)'}`, color: classSort === s ? 'var(--accent)' : 'var(--muted)', background: classSort === s ? 'var(--accent-dim)' : 'transparent' }}>
                  {s === 'count' ? 'Count↓' : s === 'alpha' ? 'A–Z' : 'ID'}
                </div>
              ))}
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 5, maxHeight: 260, overflowY: 'auto', paddingRight: 4 }}>
            {filteredClasses.map(c => (
              <div key={c.id} style={{ display: 'grid', gridTemplateColumns: '32px 100px 1fr 68px 46px', alignItems: 'center', gap: 7 }}>
                <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 9, color: 'var(--dim)', textAlign: 'right' }}>{c.id}</span>
                <span style={{ fontSize: 11, color: 'var(--text2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.name}</span>
                <div style={{ height: 8, background: 'var(--border)', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${c.count / maxCC * 100}%`, background: 'var(--accent)', opacity: .75 }} />
                </div>
                <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--text2)', textAlign: 'right' }}>{n(c.count)}</span>
                <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--muted)', textAlign: 'right' }}>{c.pct.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Object size donut + Objects per image */}
        <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 10, marginBottom: 12 }}>
          <Card style={{ padding: '14px 18px' }}>
            <MonoLabel style={{ marginBottom: 10 }}>Object size</MonoLabel>
            <InlineDonutChart
              labels={[
                `Small (<${smallThresh}px²)`,
                `Medium (<${medThresh}px²)`,
                `Large (≥${medThresh}px²)`,
              ]}
              data={[report.small_count, report.medium_count, report.large_count]}
              colors={['#fbbf24', '#818cf8', '#4ade80']} height={140}
              centerLabel={{ val: n(report.small_count + report.medium_count + report.large_count), sub: 'TOTAL' }}
            />
          </Card>
          <Card style={{ padding: '14px 18px' }}>
            <MonoLabel style={{ marginBottom: 10 }}>Objects per image</MonoLabel>
            <InlineBarChart labels={opiKeys.map(String)} data={opiVals} color="#818cf8" height={140} />
          </Card>
        </div>

        {/* BBox geometry — real reports only */}
        {report.bbox_widths?.length > 0 && (
          <Card style={{ padding: '14px 18px', marginBottom: 12 }}>
            <MonoLabel style={{ marginBottom: 12 }}>BBox geometry (pixels)</MonoLabel>
            <BBoxSizeChart widths={report.bbox_widths} heights={report.bbox_heights} height={130} />
          </Card>
        )}

        {/* BBox area distribution — real reports only */}
        {report.bbox_areas?.length > 0 && (
          <Card style={{ padding: '14px 18px', marginBottom: 12 }}>
            <MonoLabel style={{ marginBottom: 10 }}>BBox area distribution (px²)</MonoLabel>
            <BBoxAreaChart areas={report.bbox_areas} height={120} numBins={60} />
          </Card>
        )}

        {/* BBox center heatmap */}
        <Card style={{ padding: '14px 18px', marginBottom: 12 }}>
          <MonoLabel style={{ marginBottom: 10 }}>BBox center spatial bias (0…1 × 0…1)</MonoLabel>
          <BBoxCenterHeatmap
            seed={datasetId === 'voc' ? 2 : datasetId === 'kitti' ? 3 : 1}
            centers={report.bbox_centers}
          />
        </Card>

        {/* Image properties */}
        <Card style={{ padding: '14px 18px', marginBottom: 12 }}>
          <MonoLabel style={{ marginBottom: 12 }}>Image properties</MonoLabel>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 160px', gap: 16, alignItems: 'start' }}>
            <div>
              <div style={{ fontSize: 10, color: 'var(--text2)', marginBottom: 7 }}>Resolution distribution</div>
              <InlineBarChart labels={resEntries.slice(0, 7).map(([k]) => k)} data={resEntries.slice(0, 7).map(([, v]) => v)} color="#38bdf8" height={120} />
            </div>
            <div>
              <div style={{ fontSize: 10, color: 'var(--text2)', marginBottom: 7 }}>Channels</div>
              <ChannelBar channels={report.channels} />
              <div style={{ marginTop: 8, fontSize: 9, fontFamily: 'IBM Plex Mono', color: report.unified_channels ? 'var(--green)' : 'var(--amber)' }}>
                {report.unified_channels ? '✓ Unified' : '✗ Mixed'}
              </div>
            </div>
          </div>
        </Card>

        {/* Intensity */}
        <Card style={{ padding: '14px 18px', marginBottom: 12 }}>
          <MonoLabel style={{ marginBottom: 10 }}>
            {report.intensity_histogram ? 'Pixel intensity distribution' : 'RGB channel intensity distributions'}
          </MonoLabel>
          <IntensityChart
            seed={datasetId === 'voc' ? 4 : datasetId === 'kitti' ? 5 : 2}
            histogram={report.intensity_histogram}
            height={120}
          />
        </Card>

        {/* Shooting conditions */}
        <Card style={{ padding: '14px 18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: report.condition_metadata_present ? 12 : 4 }}>
            <MonoLabel>Shooting conditions</MonoLabel>
            <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 9, padding: '2px 8px', borderRadius: 12, background: report.condition_metadata_present ? 'rgba(74,222,128,.08)' : 'var(--surf2)', color: report.condition_metadata_present ? 'var(--green)' : 'var(--muted)', border: `1px solid ${report.condition_metadata_present ? 'rgba(74,222,128,.25)' : 'var(--border)'}` }}>
              {report.condition_metadata_present ? 'PRESENT' : 'ABSENT'}
            </span>
          </div>

          {!report.condition_metadata_present
            ? <div style={{ fontSize: 11, color: 'var(--muted)', fontStyle: 'italic' }}>No shooting_conditions.json found.</div>
            : <>
                <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--border)', marginBottom: 12 }}>
                  {['image', 'sequence'].map(t => (
                    <div key={t} onClick={() => setCondTab(t)} style={{ padding: '6px 12px', cursor: 'pointer', fontSize: 10, fontFamily: 'IBM Plex Mono', letterSpacing: '.08em', textTransform: 'uppercase', borderBottom: `2px solid ${condTab === t ? 'var(--accent)' : 'transparent'}`, color: condTab === t ? 'var(--accent)' : 'var(--text2)' }}>
                      {t}
                    </div>
                  ))}
                </div>
                <ConditionsBlock
                  data={condTab === 'image'
                    ? Object.entries(report.condition_by_image)
                    : Object.entries(report.condition_by_sequence)}
                  total={condTab === 'image'
                    ? report.images_with_condition_tags
                    : report.sequences_with_condition_tags}
                />

                {/* Condition source files — real reports only */}
                {report.condition_source_files?.length > 0 && (
                  <details style={{ marginTop: 12 }}>
                    <summary style={{ cursor: 'pointer', fontSize: 9, color: 'var(--muted)', fontFamily: 'IBM Plex Mono', letterSpacing: '.08em', userSelect: 'none' }}>
                      SOURCE FILES ({report.condition_source_files.length})
                    </summary>
                    <div style={{ paddingTop: 6, display: 'flex', flexDirection: 'column', gap: 3 }}>
                      {report.condition_source_files.map((p, i) => <CopyPath key={i} path={p} />)}
                    </div>
                  </details>
                )}
              </>
          }
        </Card>
      </div>
    </div>
  );
}
