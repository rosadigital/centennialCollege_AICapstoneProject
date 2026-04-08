import { useEffect, useMemo, useState } from 'react';
import { ControlPanel } from './components/ControlPanel';
import { HeatmapMap } from './components/HeatmapMap';
import { fetchHeatmap, fetchMetadata, type HeatmapPoint, type MetadataResponse } from './lib/api';

const defaultMetadata: MetadataResponse = {
  vehicle_types: ['BUS', 'STREETCAR', 'SUBWAY'],
  months: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
  days_of_week: [0, 1, 2, 3, 4, 5, 6],
  hours: Array.from({ length: 24 }, (_, idx) => idx),
};

function App() {
  const [metadata, setMetadata] = useState<MetadataResponse>(defaultMetadata);
  const [vehicleType, setVehicleType] = useState('BUS');
  const [month, setMonth] = useState(1);
  const [dayOfWeek, setDayOfWeek] = useState(1);
  const [hour, setHour] = useState(8);
  const [points, setPoints] = useState<HeatmapPoint[]>([]);
  const [pointCount, setPointCount] = useState(0);
  const [avgDelay, setAvgDelay] = useState(0);
  const [p90Delay, setP90Delay] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function resetDefaults() {
    setVehicleType(metadata.vehicle_types[0] ?? 'BUS');
    setMonth(metadata.months[0] ?? 1);
    setDayOfWeek(1);
    setHour(8);
  }

  useEffect(() => {
    async function loadMetadata() {
      try {
        const m = await fetchMetadata();
        setMetadata(m);
        setVehicleType(m.vehicle_types[0] ?? 'BUS');
        setMonth(m.months[0] ?? 1);
      } catch {
        setError('Could not load metadata from server. Showing defaults.');
      }
    }
    loadMetadata();
  }, []);

  const filters = useMemo(
    () => ({ vehicleType, month, dayOfWeek, hour, includeTimeDecay: false }),
    [vehicleType, month, dayOfWeek, hour],
  );

  useEffect(() => {
    const timeout = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchHeatmap(filters);
        setPoints(response.points);
        setPointCount(response.kpis.point_count);
        setAvgDelay(response.kpis.avg_delay);
        setP90Delay(response.kpis.p90);
      } catch {
        setPoints([]);
        setPointCount(0);
        setAvgDelay(0);
        setP90Delay(0);
        setError(
          'Unable to fetch heatmap data. Confirm the FastAPI app is running and reachable. If port 8000 is used by another app, start Uvicorn on another port (e.g. 8001) and set VITE_API_URL in client/.env — see client/README.md.',
        );
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => clearTimeout(timeout);
  }, [filters]);

  return (
    <div className="min-h-screen bg-[#0b1120] text-slate-50">
      <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-slate-950/85 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-[1600px] items-center gap-3 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500 shadow-[0_0_24px_rgba(59,130,246,0.35)]">
            <svg viewBox="0 0 24 24" className="h-5 w-5 text-white" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M8 18h8" />
              <path d="M7 14h10" />
              <path d="M7 4h10a2 2 0 0 1 2 2v8a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4V6a2 2 0 0 1 2-2Z" />
              <path d="m9 22 1.5-3" />
              <path d="m15 22-1.5-3" />
              <circle cx="9" cy="9" r="1" fill="currentColor" />
              <circle cx="15" cy="9" r="1" fill="currentColor" />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white">TTC Delay Intelligence</h1>
            <p className="text-xs font-medium text-slate-400">Predictive Heatmap Visualization</p>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-[1600px] flex-col gap-5 p-4 sm:p-6 lg:gap-6 lg:p-8">
        <section className="rounded-2xl border border-slate-800/80 bg-slate-900/70 p-5 shadow-[0_20px_60px_rgba(2,6,23,0.35)] backdrop-blur-xl sm:p-6">
          <h2 className="text-2xl font-bold text-white sm:text-3xl">Toronto Transit Delay Heatmap</h2>
          <p className="mt-3 max-w-4xl text-sm leading-relaxed text-slate-400 sm:text-base">
            Interactive visualization of predicted delay intensity across the TTC network. Adjust the
            filters on the left to explore historical patterns and model-backed predictions by vehicle
            type, time, and day.
          </p>
        </section>

        <div className="grid gap-5 lg:grid-cols-[320px_minmax(0,1fr)] lg:gap-6">
          <aside className="lg:sticky lg:top-[92px] lg:h-fit">
            <ControlPanel
              vehicleTypes={metadata.vehicle_types}
              months={metadata.months}
              vehicleType={vehicleType}
              month={month}
              dayOfWeek={dayOfWeek}
              hour={hour}
              onVehicleTypeChange={setVehicleType}
              onMonthChange={setMonth}
              onDayOfWeekChange={setDayOfWeek}
              onHourChange={setHour}
              onReset={resetDefaults}
            />
          </aside>

          <section className="flex min-w-0 flex-col gap-4">

          <section className="relative overflow-hidden rounded-2xl border border-slate-800/80 bg-slate-900/70 shadow-[0_24px_60px_rgba(2,6,23,0.42)] backdrop-blur-xl">
            <div className="absolute inset-x-0 top-0 z-10 flex items-center justify-between px-6 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Delay intensity map</p>
                <p className="mt-1 text-sm text-slate-400">Low to high delay concentration across the selected TTC scenario.</p>
              </div>
            </div>

            <div className="px-3 pb-3 pt-16 sm:px-4 sm:pb-4">
              <HeatmapMap points={points} />
            </div>

            <div className="pointer-events-none absolute bottom-6 left-6 z-10 rounded-xl border border-slate-700/70 bg-slate-950/80 p-4 shadow-xl backdrop-blur-md">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Delay intensity</p>
              <div className="mt-3 flex items-center gap-2">
                <span className="text-xs text-slate-500">Low</span>
                <div className="h-2 w-40 rounded-full bg-gradient-to-r from-sky-500 via-amber-400 to-rose-500" />
                <span className="text-xs text-slate-500">High</span>
              </div>
            </div>
          </section>

          {loading && <p className="text-sm text-slate-300">Loading heatmap...</p>}
          {error && <p className="text-sm text-rose-300">{error}</p>}

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <article className="rounded-2xl border border-slate-800/80 bg-slate-900/80 p-5 shadow-[0_12px_30px_rgba(2,6,23,0.28)]">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Points on map</p>
                  <p className="mt-2 text-3xl font-bold text-white">{pointCount.toLocaleString()}</p>
                </div>
                <div className="rounded-full bg-sky-500/10 p-3 text-sky-400">◎</div>
              </div>
            </article>

            <article className="rounded-2xl border border-slate-800/80 bg-slate-900/80 p-5 shadow-[0_12px_30px_rgba(2,6,23,0.28)]">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Mean delay</p>
                  <p className="mt-2 text-3xl font-bold text-white">{avgDelay.toFixed(2)} <span className="text-sm font-medium text-slate-400">min</span></p>
                </div>
                <div className="rounded-full bg-amber-500/10 p-3 text-amber-400">◔</div>
              </div>
            </article>

            <article className="rounded-2xl border border-slate-800/80 bg-slate-900/80 p-5 shadow-[0_12px_30px_rgba(2,6,23,0.28)]">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                    Delay in 90% of the cases
                  </p>
                  <p className="mt-2 text-3xl font-bold text-white">{p90Delay.toFixed(2)} <span className="text-sm font-medium text-slate-400">min</span></p>
                </div>
                <div className="rounded-full bg-rose-500/10 p-3 text-rose-400">▲</div>
              </div>
            </article>
          </section>
        </section>
        </div>
      </main>
    </div>
  );
}

export default App;
