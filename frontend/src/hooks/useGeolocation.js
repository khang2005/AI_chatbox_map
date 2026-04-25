import { useEffect, useState, useCallback } from "react";

const STORAGE_KEY = "lastKnownLocation";

export function useGeolocation({ timeoutMs = 10000 } = {}) {
  const [coords, setCoords] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const [accuracy, setAccuracy] = useState(null);

  const loadFromStorage = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed.lat === "number" && typeof parsed.lng === "number") {
        return parsed;
      }
    } catch {}
    return null;
  };

  const saveToStorage = (c) => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(c)); } catch {}
  };

  const request = useCallback(() => {
    if (!navigator.geolocation) {
      setStatus("unavailable");
      setError("Geolocation not supported");
      return;
    }

    setStatus("loading");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const c = {
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: pos.coords.accuracy
        };
        setCoords({ lat: c.lat, lng: c.lng });
        setAccuracy(pos.coords.accuracy < 100 ? "gps" : "gps-approx");
        setStatus("ok");
        setError(null);
        saveToStorage({ lat: c.lat, lng: c.lng });
      },
      (err) => {
        console.warn("Browser geolocation failed:", err.message);
        setStatus("error");
        setError(err.message);
      },
      { enableHighAccuracy: true, maximumAge: 60000, timeout: timeoutMs }
    );
  }, [timeoutMs]);

  useEffect(() => {
    const stored = loadFromStorage();
    if (stored) {
      setCoords({ lat: stored.lat, lng: stored.lng });
      setAccuracy("stored");
      setStatus("ok");
    } else {
      request();
    }
  }, [request]);

  return { coords, status, error, accuracy, retry: request };
}