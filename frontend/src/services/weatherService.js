// ONDA aerodrome reference point: 30°19'21"N, 009°24'41"W.
const AGADIR_LATITUDE = 30.3225;
const AGADIR_LONGITUDE = -9.4114;

const WEATHER_URL = "https://api.open-meteo.com/v1/forecast";

export async function getWeather() {
  const params = new URLSearchParams({
    latitude: AGADIR_LATITUDE,
    longitude: AGADIR_LONGITUDE,
    current: [
      "temperature_2m",
      "relative_humidity_2m",
      "weather_code",
      "wind_speed_10m",
      "visibility",
      "is_day",
    ].join(","),
    timezone: "Africa/Casablanca",
  });

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 8000);
  let response;
  try {
    response = await fetch(`${WEATHER_URL}?${params.toString()}`, { signal: controller.signal });
  } finally {
    window.clearTimeout(timeout);
  }

  if (!response.ok) throw new Error(`Weather service returned HTTP ${response.status}`);

  const data = await response.json();
  const current = data.current;
  if (!current) throw new Error("Weather service did not return current conditions");

  return {
    temperature: Math.round(current.temperature_2m),
    humidity: current.relative_humidity_2m,
    windSpeed: Math.round(current.wind_speed_10m),
    visibility: current.visibility == null ? null : Math.round(current.visibility / 1000),
    weatherCode: current.weather_code,
    isDay: Boolean(current.is_day),
    observedAt: current.time,
  };
}
