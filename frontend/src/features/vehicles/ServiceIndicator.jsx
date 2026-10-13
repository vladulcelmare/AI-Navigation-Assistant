import React from "react";
import { useVehicle } from "./VehicleContext.jsx";

export function ServiceIndicatorComponent() {
  const { selectedVehicle } = useVehicle();
  const kmUntilNext = Math.max(0, Number(selectedVehicle?.telemetry?.service_due_km ?? 0));
  const pct = selectedVehicle
    ? Math.max(0, Math.min(100, Math.round((1 - kmUntilNext / 15000) * 100)))
    : 0;
  const color = pct < 50 ? '#16a34a' : (pct < 90 ? '#f59e0b' : '#ef4444');

  return (
    <div className="h-full bg-white/20 border border-white flex flex-col justify-center gap-1 p-2 rounded-2xl font-sans">
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs text-white/80">Service</div>
        <div className="text-sm font-bold text-white whitespace-nowrap">{Math.round(kmUntilNext)} km</div>
      </div>

      <div className="relative w-full bg-white/10 h-1 rounded-full">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>

      <div className="text-[10px] text-white/60 whitespace-nowrap">
        until next service
      </div>
    </div>
  );
}

export default ServiceIndicatorComponent;
