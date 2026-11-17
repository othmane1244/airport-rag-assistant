import { Cloud, Eye, Wind, Droplets } from "lucide-react";

function WeatherMetric({ icon: Icon, label, value }) {
  return (
    <div className="weather-metric">
      <span className="weather-metric-icon" aria-hidden="true"><Icon size={17} /></span>
      <span className="weather-metric-label">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function AirportToday({ weather, loading, error }) {
  const observedAt = weather?.observedAt?.slice(11, 16) || null;

  return (
    <div className="airport-today-card mockup-card" aria-live="polite" aria-busy={loading}>
      <div className="today-weather-heading">
        <div className="today-weather-title">
          <span className="today-weather-icon" aria-hidden="true"><Cloud size={19} /></span>
          <div>
            <h3>Weather at the airport</h3>
            <p>Current conditions · Agadir</p>
          </div>
        </div>
        {observedAt && <span className="weather-observed">Updated {observedAt}</span>}
      </div>

      {loading && !weather ? (
        <p className="weather-state">Loading current weather…</p>
      ) : error && !weather ? (
        <p className="weather-state" role="status">Current weather is unavailable right now.</p>
      ) : weather ? (
        <div className="weather-metrics-grid">
          <div className="weather-current-condition">
            <span aria-hidden="true">{weather.icon || "☁️"}</span>
            <strong>{weather.temperature}°C</strong>
            <span>{weather.condition || "Current conditions"}</span>
          </div>
          <WeatherMetric icon={Droplets} label="Humidity" value={weather.humidity == null ? "—" : `${weather.humidity}%`} />
          <WeatherMetric icon={Wind} label="Wind" value={weather.windSpeed == null ? "—" : `${weather.windSpeed} km/h`} />
          <WeatherMetric icon={Eye} label="Visibility" value={weather.visibility == null ? "—" : `${weather.visibility} km`} />
        </div>
      ) : (
        <p className="weather-state">Current weather is unavailable right now.</p>
      )}
      <p className="weather-attribution">Weather data by <a href="https://open-meteo.com/" target="_blank" rel="noreferrer">Open-Meteo</a></p>
    </div>
  );
}
