type ControlPanelProps = {
  vehicleTypes: string[];
  months: number[];
  vehicleType: string;
  month: number;
  dayOfWeek: number;
  hour: number;
  onVehicleTypeChange: (value: string) => void;
  onMonthChange: (value: number) => void;
  onDayOfWeekChange: (value: number) => void;
  onHourChange: (value: number) => void;
  onReset: () => void;
};

const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

export function ControlPanel({
  vehicleTypes,
  months,
  vehicleType,
  month,
  dayOfWeek,
  hour,
  onVehicleTypeChange,
  onMonthChange,
  onDayOfWeekChange,
  onHourChange,
  onReset,
}: ControlPanelProps) {
  return (
    <section className="rounded-2xl border border-slate-800/80 bg-slate-900/80 p-6 shadow-[0_20px_60px_rgba(2,6,23,0.45)] backdrop-blur-xl">
      <div>
        <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-100">
          <span className="text-sky-400">☰</span>
          Heatmap Filters
        </h2>
        <p className="mt-1 max-w-2xl text-sm text-slate-400">
          Explore predicted delay intensity by transit mode, seasonality, weekday, and time of day.
        </p>
      </div>

      <div className="mt-6 grid gap-5">
        <label className="flex flex-col gap-2">
          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Vehicle type</span>
          <select
            className="rounded-xl border border-slate-700 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-500"
            value={vehicleType}
            onChange={(e) => onVehicleTypeChange(e.target.value)}
          >
            {vehicleTypes.map((vt) => (
              <option key={vt} value={vt}>
                {vt === 'BUS' ? 'Bus Network' : vt.charAt(0) + vt.slice(1).toLowerCase()}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Month</span>
          <select
            className="rounded-xl border border-slate-700 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-500"
            value={month}
            onChange={(e) => onMonthChange(Number(e.target.value))}
          >
            {months.map((m) => (
              <option key={m} value={m}>
                {MONTH_NAMES[m - 1] ?? m}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Day of week</span>
          <select
            className="rounded-xl border border-slate-700 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none transition focus:border-sky-500"
            value={dayOfWeek}
            onChange={(e) => onDayOfWeekChange(Number(e.target.value))}
          >
            {DAY_NAMES.map((dayName, idx) => (
              <option key={dayName} value={idx}>
                {dayName}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-5">
        <label className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Time of day</span>
            <span className="text-sm font-semibold text-sky-400">{hour.toString().padStart(2, '0')}:00</span>
          </div>
          <div className="rounded-xl border border-slate-700 bg-slate-950/80 px-4 py-4">
            <input
              className="w-full accent-sky-500"
              type="range"
              min={0}
              max={23}
              value={hour}
              onChange={(e) => onHourChange(Number(e.target.value))}
            />
            <div className="mt-2 flex justify-between text-[10px] text-slate-500">
              <span>00:00</span>
              <span>06:00</span>
              <span>12:00</span>
              <span>18:00</span>
              <span>23:00</span>
            </div>
          </div>
        </label>
      </div>

      <div className="mt-6 border-t border-slate-800 pt-4">
        <button
          type="button"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-sm font-medium text-slate-300 transition hover:border-slate-500 hover:text-white"
          onClick={onReset}
        >
          Reset defaults
        </button>
      </div>
    </section>
  );
}
