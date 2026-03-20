const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export type MetadataResponse = {
  vehicle_types: string[];
  months: number[];
  days_of_week: number[];
  hours: number[];
};

export type HeatmapPoint = {
  latitude_bin: number;
  longitude_bin: number;
  pred_delay_mean: number;
  pred_delay_p90: number;
  n_events: number;
  weight: number;
};

export type HeatmapResponse = {
  points: HeatmapPoint[];
  kpis: {
    point_count: number;
    avg_delay: number;
    p90: number;
  };
};

export type HeatmapFilters = {
  vehicleType: string;
  month: number;
  dayOfWeek: number;
  hour: number;
  includeTimeDecay: boolean;
};

export async function fetchMetadata(): Promise<MetadataResponse> {
  const response = await fetch(`${API_BASE_URL}/metadata`);
  if (!response.ok) throw new Error('Failed to fetch metadata');
  return response.json();
}

export async function fetchHeatmap(filters: HeatmapFilters): Promise<HeatmapResponse> {
  const query = new URLSearchParams({
    vehicle_type: filters.vehicleType,
    month: String(filters.month),
    day_of_week: String(filters.dayOfWeek),
    hour: String(filters.hour),
    include_time_decay: String(filters.includeTimeDecay),
  });

  const response = await fetch(`${API_BASE_URL}/heatmap?${query.toString()}`);
  if (!response.ok) throw new Error('Failed to fetch heatmap data');
  return response.json();
}
