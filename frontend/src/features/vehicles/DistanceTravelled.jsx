import { useMap } from "../map/MapContext.jsx";
import { useVehicle } from "./VehicleContext.jsx";

export function DistanceTravelledComponent() {
    const { selectedVehicle } = useVehicle();
    const { distanceTravelled } = useMap();
    const distance = selectedVehicle ? Number(
        selectedVehicle?.telemetry?.distance_travelled ?? distanceTravelled,
    ) || 0 : 0;

    return (
        <div className="h-full bg-white/20 border border-white flex flex-col justify-center gap-1 p-2 rounded-2xl font-sans">
            <div className="text-xs text-white/80">Distance travelled today</div>
            <div className="text-sm font-bold text-white whitespace-nowrap">
                {selectedVehicle ? `${Math.round(distance)} km` : "Select vehicle"}
            </div>
        </div>
    );
}

export default DistanceTravelledComponent;
