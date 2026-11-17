const configuredWidgetUrl = import.meta.env.VITE_AVIONIO_IFRAME_URL?.trim();
const widgetUrl = "https://www.avionio.com/widget/en/aga/departures?style=3";

export const AVIONIO_CONFIG = {
  iframeUrl: configuredWidgetUrl || widgetUrl,
  externalUrl: "https://www.avionio.com/en/airport/aga/departures",
  officialUrl:
    "https://www.onda.ma/mobile/Site-Mobile/Recherche",
  enabled: import.meta.env.VITE_AVIONIO_ENABLED !== "false",
};
