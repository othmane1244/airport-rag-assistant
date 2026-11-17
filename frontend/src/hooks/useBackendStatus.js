import { useEffect, useState } from "react";
import api from "../services/api";

export function useBackendStatus() {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let active = true;
    let controller;

    const check = async () => {
      controller?.abort();
      controller = new AbortController();
      try {
        await api.get("/ready", { timeout: 4000, signal: controller.signal });
        if (active) setStatus("ready");
      } catch (error) {
        if (active && error.code !== "ERR_CANCELED") setStatus("unavailable");
      }
    };

    check();
    const interval = window.setInterval(check, 30000);

    return () => {
      active = false;
      controller?.abort();
      window.clearInterval(interval);
    };
  }, []);

  return status;
}
