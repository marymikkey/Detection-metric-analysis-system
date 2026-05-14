// TODO: позже сюда добавится поле yaml_classes из dataset.yaml,
// которое будем сверять с class_names и подсвечивать расхождения.

function fmtTime(iso) {
  if (!iso) return '';
  try {
    const [date, time] = iso.split('T');
    const [Y, M, D] = date.split('-');
    const [h, m] = time.split(':');
    return `${h}:${m} ${D}.${M}.${Y}`;
  } catch {
    return iso;
  }
}

/**
 * Converts raw EDA-script JSON output into the normalized report shape
 * consumed by EDADatasetView. This is the only file that knows about
 * the script's output format.
 *
 * @param {object} raw — parsed stats.json
 * @returns {NormalizedReport}
 */
export function adaptRealReport(raw) {
  return {
    // ── Mode flag ────────────────────────────────────────────────────────
    _singleSplit: true,

    // ── Identity ─────────────────────────────────────────────────────────
    title:                raw.dataset_name,
    yaml_name:            raw.dataset_yaml_name,
    group_key:            raw.dataset_yaml_path,
    generation_time:      fmtTime(raw.generation_time),
    target_split:         raw.target_split,
    analyzed_image_dirs:  raw.analyzed_image_dirs || [],

    // ── Corpus stats ─────────────────────────────────────────────────────
    images_total:         raw.images_total,
    objects_total:        raw.objects_total,
    nc:                   raw.nc,
    class_names:          raw.class_names,
    class_distribution:   raw.class_distribution,

    // ── Label quality ─────────────────────────────────────────────────────
    broken_label_lines:       raw.broken_label_lines,
    missing_label_files:      raw.missing_label_files,
    empty_label_files:        raw.empty_label_files,
    only_broken_label_files:  raw.only_broken_label_files,
    corrupted_label_images:   raw.corrupted_label_images,
    background_images:        raw.background_images,
    background_definition:    raw.background_definition,
    min_objects_per_image:    raw.min_objects_per_image,
    max_objects_per_image:    raw.max_objects_per_image,

    // ── Image properties ──────────────────────────────────────────────────
    channels:             raw.channels,
    resolutions:          raw.resolutions,
    unified_channels:     raw.unified_channels,
    unified_resolution:   raw.unified_resolution,

    // ── Object sizes ──────────────────────────────────────────────────────
    small_count:              raw.small_count,
    medium_count:             raw.medium_count,
    large_count:              raw.large_count,
    small_area_threshold:     raw.small_area_threshold,
    medium_area_threshold:    raw.medium_area_threshold,

    // Dict histogram {count: images} — ready for bar chart
    objects_per_image: raw.objects_per_image_distribution,

    // ── Raw arrays for custom charts ──────────────────────────────────────
    bbox_widths:        raw.bbox_widths,
    bbox_heights:       raw.bbox_heights,
    bbox_areas:         raw.bbox_areas,
    bbox_centers:       raw.bbox_centers,           // [[x, y], ...]  normalized 0..1
    intensity_histogram: raw.intensity_histogram,   // number[256]

    // ── Shooting conditions ───────────────────────────────────────────────
    condition_metadata_present:  raw.condition_metadata_present,
    condition_labels:            Object.keys(raw.condition_by_image || {}),
    condition_by_image:          raw.condition_by_image || {},
    condition_by_sequence:       raw.condition_by_sequence || {},
    images_with_condition_tags:  raw.images_with_conditions,
    sequences_with_condition_tags: raw.sequences_with_conditions,
    condition_source_files:      raw.condition_source_files || [],
  };
}
