import { useVehicle } from "./VehicleContext.jsx";

export function RangeComponent() {
    const { selectedVehicle } = useVehicle();
    const telemetry = selectedVehicle?.telemetry;
    const currentFuel = Number(telemetry?.current_fuel ?? 0);
    const consumption = Number(telemetry?.avg_consumption ?? 0);
    const range = consumption > 0 ? Math.round((currentFuel / consumption) * 100) : 0;
    const capacity = Number(selectedVehicle?.total_capacity ?? 0);
    const maxRange = consumption > 0
        ? Math.max(Math.round((capacity / consumption) * 100), 1)
        : 1;

    const pct = Number((range / maxRange * 100).toFixed(0));
    const color = pct >= 60 ? '#16a34a' : (pct >= 20 ? '#f59e0b' : '#ef4444');

    return (
        <div className="h-full bg-white/20 border border-white flex flex-col p-2 rounded-2xl font-sans font-bold justify-center" style={{ color }}>
            {!selectedVehicle ? (
                <div className="text-xs text-white/70">Select vehicle</div>
            ) : (
                <>
                    <span className={`text-xs text-[#ddd]  font-light cursor-pointer ${color}`}>Range</span>
                    <div className="flex items-center text-sm">{Math.round(range)} KM</div>
                    <div className="relative w-full bg-white/10 h-2 mt-2">
                        <div className="h-full" style={{ width: `${pct}%`, backgroundColor: color }} />
                    </div>
                </>
            )}
        </div>
    );
}
