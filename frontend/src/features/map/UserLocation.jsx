import { useEffect, useRef } from "react";
import { useMap } from "./MapContext.jsx";

export function UserLocation() {
  const { map, setUserLocation, userLocation } = useMap();
  const posRef = useRef(userLocation || { lat: 47.159, lng: 27.587 });
  const movementRef = useRef({ latDir: 0, lonDir: 0 });
  const rafRef = useRef(null);
  const lastTsRef = useRef(null);
  const cameraPositionRef = useRef(null);

  useEffect(() => {
    if (!map) return;

    const sourceId = "user-location-source";
    const layerId = "user-location-layer";

    // try to use real geolocation for initial position
    if (navigator.geolocation?.getCurrentPosition) {
      navigator.geolocation.getCurrentPosition(
        (p) => {
          posRef.current = { lat: p.coords.latitude, lng: p.coords.longitude };
          cameraPositionRef.current = { ...posRef.current };
          setUserLocation?.(posRef.current);
          if (map?.setCenter) map.setCenter([posRef.current.lng, posRef.current.lat]);
          },
        () => {},
        { enableHighAccuracy: true, maximumAge: 10000, timeout: 5000 }
      );
    }

    const makePoint = () => (
        {
            type: "Feature",
            geometry: {
                type: "Point",
                coordinates: [posRef.current.lng, posRef.current.lat]
            }
        }
    );

    const addSourceAndLayer = () => {
      const point = makePoint();
      if (map.getSource && map.getSource(sourceId)) {
        map.getSource(sourceId).setData(point);
      } else if (map.addSource) {
        map.addSource(sourceId, { type: "geojson", data: point });
        if (!map.getLayer || !map.getLayer(layerId)) {
          try {
            map.addLayer({
              id: layerId,
              type: "circle",
              source: sourceId,
              paint: {
                "circle-radius": 8,
                "circle-color": "#007bff",
                "circle-stroke-color": "#ffffff",
                "circle-stroke-width": 2,
              },
            });
          } catch (e) {
            // layer add can fail if style not ready; ignore and rely on load handler
          }
        }
      }
    };

    if (map.isStyleLoaded && map.isStyleLoaded()) addSourceAndLayer();
    else map.once?.("load", addSourceAndLayer);

    if (map?.setCenter) {
      map.setCenter([posRef.current.lng, posRef.current.lat]);
      map.setZoom(14);
    }
    cameraPositionRef.current = { ...posRef.current };
    setUserLocation?.(posRef.current);

    const speedMps = 50; // meters per second
    const degPerMeter = 1 / 111111; // approx degrees latitude per meter
    const step = (ts) => {
      if (!lastTsRef.current) lastTsRef.current = ts;
      const dt = Math.min((ts - lastTsRef.current) / 1000, 0.05);
      lastTsRef.current = ts;

      const { latDir, lonDir } = movementRef.current;
      if (latDir !== 0 || lonDir !== 0) {
        const distance = speedMps * dt;
        const mag = Math.hypot(latDir, lonDir) || 1;
        const latMeters = (latDir / mag) * distance;
        const lonMeters = (lonDir / mag) * distance;

        const dLat = latMeters * degPerMeter;
        const dLon = lonMeters * degPerMeter / Math.cos((posRef.current.lat * Math.PI) / 180);

        posRef.current = {
          lat: posRef.current.lat + dLat,
          lng: posRef.current.lng + dLon,
        };

        const point = makePoint();
        try {
          map.getSource?.(sourceId)?.setData(point);
        } catch (e) {
          // ignore
        }
        setUserLocation?.(posRef.current);
      }

      if (map?.setCenter) {
        const cameraPosition = cameraPositionRef.current || { ...posRef.current };
        const smoothing = 1 - Math.exp(-dt / 0.12);
        const previousCameraPosition = { ...cameraPosition };

        cameraPosition.lat += (posRef.current.lat - cameraPosition.lat) * smoothing;
        cameraPosition.lng += (posRef.current.lng - cameraPosition.lng) * smoothing;
        cameraPositionRef.current = cameraPosition;

        if (
          cameraPosition.lat !== previousCameraPosition.lat ||
          cameraPosition.lng !== previousCameraPosition.lng
        ) {
          map.setCenter([cameraPosition.lng, cameraPosition.lat]);
        }
      }

      rafRef.current = requestAnimationFrame(step);
    };

    rafRef.current = requestAnimationFrame(step);

    const keyDown = (e) => {
      // Ignore auto-repeat keydown events; movement is handled by RAF loop
      if (e.repeat) return;
      const target = e.target;
      if (
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT" ||
        target?.isContentEditable
      ) {
        return;
      }
      const k = (e.key || "").toLowerCase();
      if (["arrowup", "w"].includes(k)) {
        e.preventDefault();
        movementRef.current.latDir = 1;
      } else if (["arrowdown", "s"].includes(k)) {
        e.preventDefault();
        movementRef.current.latDir = -1;
      } else if (["arrowleft", "a"].includes(k)) {
        e.preventDefault();
        movementRef.current.lonDir = -1;
      } else if (["arrowright", "d"].includes(k)) {
        e.preventDefault();
        movementRef.current.lonDir = 1;
      }
    };

    const keyUp = (e) => {
      const target = e.target;
      if (
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.tagName === "SELECT" ||
        target?.isContentEditable
      ) {
        return;
      }
      const k = (e.key || "").toLowerCase();
      if ((k === "arrowup" || k === "w") && movementRef.current.latDir === 1) {
        e.preventDefault();
        movementRef.current.latDir = 0;
      } else if ((k === "arrowdown" || k === "s") && movementRef.current.latDir === -1) {
        e.preventDefault();
        movementRef.current.latDir = 0;
      } else if ((k === "arrowleft" || k === "a") && movementRef.current.lonDir === -1) {
        e.preventDefault();
        movementRef.current.lonDir = 0;
      } else if ((k === "arrowright" || k === "d") && movementRef.current.lonDir === 1) {
        e.preventDefault();
        movementRef.current.lonDir = 0;
      }
    };

    const onBlur = () => {
      // Clear movement when window loses focus to avoid circling the earth 10000000 times while away
      movementRef.current.latDir = 0;
      movementRef.current.lonDir = 0;
    };

    window.addEventListener("keydown", keyDown);
    window.addEventListener("keyup", keyUp);
    window.addEventListener("blur", onBlur);

    return () => {
      window.removeEventListener("keydown", keyDown);
      window.removeEventListener("keyup", keyUp);
      window.removeEventListener("blur", onBlur);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      lastTsRef.current = null;
      cameraPositionRef.current = null;
      try {
        if (map.getLayer && map.getLayer(layerId)) map.removeLayer(layerId);
        if (map.getSource && map.getSource(sourceId)) map.removeSource(sourceId);
      } catch (e) {
        // ignore
      }
    };
  }, [map]);

  return null;
}
