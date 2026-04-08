const configuredApiUrl = import.meta.env.VITE_API_URL;
const apiBaseUrls = configuredApiUrl
  ? [configuredApiUrl]
  : ['http://localhost:8000', 'http://127.0.0.1:8001'];

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

async function fetchFromApi(path: string): Promise<Response> {
  let lastError: unknown;

  for (const baseUrl of apiBaseUrls) {
    try {
      const response = await fetch(`${baseUrl}${path}`);
      if (!response.ok) {
        throw new Error(`Request failed with ${response.status} from ${baseUrl}${path}`);
      }
      return response;
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError instanceof Error ? lastError : new Error(`Failed to fetch ${path}`);
}

export async function fetchMetadata(): Promise<MetadataResponse> {
  const response = await fetchFromApi('/metadata');
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

  const response = await fetchFromApi(`/heatmap?${query.toString()}`);
  return response.json();
}
