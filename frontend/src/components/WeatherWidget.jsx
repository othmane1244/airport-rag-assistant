import GlassCard from "./GlassCard";

export default function WeatherWidget({ weather, loading }) {
  return (
    <GlassCard className="weather-widget weather-card-hero" aria-label="Current weather in Agadir">
      <div className="weather-hero-top">
        <span className="weather-hero-icon" aria-hidden="true">{loading ? "…" : weather?.icon || "☁️"}</span>
        <div>
          <div className="weather-hero-temp">{weather ? `${weather.temperature}°C` : "—"}</div>
          <div className="weather-hero-cond">
            {loading ? "Loading weather…" : weather?.condition || "Weather unavailable"}
          </div>
        </div>
      </div>
      <div className="weather-hero-location">Agadir, Morocco</div>
    </GlassCard>
  );
}
