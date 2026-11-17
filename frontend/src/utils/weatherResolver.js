const codeGroups = [
  { codes: [0], day: ["Sunny", "☀️"], night: ["Clear", "🌙"] },
  { codes: [1, 2], day: ["Partly cloudy", "🌤️"], night: ["Partly cloudy", "☁️"] },
  { codes: [3], day: ["Cloudy", "☁️"], night: ["Cloudy", "☁️"] },
  { codes: [45, 48], day: ["Foggy", "🌫️"], night: ["Foggy", "🌫️"] },
  { codes: [51, 53, 55, 56, 57], day: ["Drizzle", "🌦️"], night: ["Drizzle", "🌧️"] },
  { codes: [61, 63, 65, 66, 67, 80, 81, 82], day: ["Rain", "🌧️"], night: ["Rain", "🌧️"] },
  { codes: [71, 73, 75, 77, 85, 86], day: ["Snow", "❄️"], night: ["Snow", "❄️"] },
  { codes: [95, 96, 99], day: ["Thunderstorm", "⛈️"], night: ["Thunderstorm", "⛈️"] },
];

export function resolveWeather(weatherCode, isDay) {
  const group = codeGroups.find(({ codes }) => codes.includes(Number(weatherCode)));
  const [condition, icon] = group?.[isDay ? "day" : "night"] || ["Unknown", "☁️"];
  return { condition, icon };
}
