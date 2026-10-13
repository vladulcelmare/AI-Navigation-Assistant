import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useRef,
    useState,
} from "react";
import { useMap } from "../map/MapContext.jsx";
import {
    createVehicleRequest,
    deleteVehicleRequest,
    listVehiclesRequest,
    updateVehicleTelemetryRequest,
} from "./vehiclesApi.js";

const VehicleContext = createContext(null);
const SELECTED_VEHICLE_STORAGE_KEY = "selectedVehicleId";
const SELECTED_VEHICLE_DATA_STORAGE_KEY = "selectedVehicle";
const roundToTwoDecimals = (value) => Math.round((Number(value) + Number.EPSILON) * 100) / 100;

export function VehicleProvider({ children }) {
    const [vehicles, setVehicles] = useState([]);
    const [selectedVehicle, setSelectedVehicle] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const { distanceTravelled } = useMap();
    const telemetryBaseRef = useRef(null);
    const distanceTravelledRef = useRef(0);
    const selectedVehicleRef = useRef(null);

    useEffect(() => {
        distanceTravelledRef.current = distanceTravelled;
    }, [distanceTravelled]);

    useEffect(() => {
        selectedVehicleRef.current = selectedVehicle;
    }, [selectedVehicle]);

    const fetchVehicles = useCallback(async () => {
        if (!localStorage.getItem("token")) {
            setVehicles([]);
            setSelectedVehicle(null);
            sessionStorage.removeItem(SELECTED_VEHICLE_STORAGE_KEY);
            sessionStorage.removeItem(SELECTED_VEHICLE_DATA_STORAGE_KEY);
            setLoading(false);
            return;
        }

        setLoading(true);
        setError("");

        const currentVehicles = await listVehiclesRequest();
        setVehicles(currentVehicles);
        const savedVehicleId = sessionStorage.getItem(SELECTED_VEHICLE_STORAGE_KEY);
        const serverVehicle = currentVehicles.find(
            (vehicle) => vehicle.vehicle_id === savedVehicleId,
        );
        let savedVehicle = serverVehicle;
        const savedVehicleData = sessionStorage.getItem(
            SELECTED_VEHICLE_DATA_STORAGE_KEY,
        );

        if (serverVehicle && savedVehicleData) {
            try {
                const persistedVehicle = JSON.parse(savedVehicleData);
                if (persistedVehicle.vehicle_id === serverVehicle.vehicle_id) {
                    savedVehicle = {
                        ...serverVehicle,
                        ...persistedVehicle,
                    };
                }
            } catch {
                sessionStorage.removeItem(SELECTED_VEHICLE_DATA_STORAGE_KEY);
            }
        }

        if (savedVehicle) {
            setSelectedVehicle(savedVehicle);
            sessionStorage.setItem(
                SELECTED_VEHICLE_DATA_STORAGE_KEY,
                JSON.stringify(savedVehicle),
            );
            telemetryBaseRef.current = {
                ...savedVehicle.telemetry,
                distanceTravelled: distanceTravelledRef.current,
            };
        } else {
            sessionStorage.removeItem(SELECTED_VEHICLE_STORAGE_KEY);
            sessionStorage.removeItem(SELECTED_VEHICLE_DATA_STORAGE_KEY);
            setSelectedVehicle(null);
        }
        setLoading(false);
    }, []);

    useEffect(() => {
        fetchVehicles().catch((fetchError) => {
            console.error(fetchError);
            setVehicles([]);
            setSelectedVehicle(null);
            setError("Unable to load your vehicles.");
            setLoading(false);
        });
    }, [fetchVehicles]);

    const selectVehicle = useCallback((vehicle) => {
        setSelectedVehicle(vehicle);
        sessionStorage.setItem(SELECTED_VEHICLE_STORAGE_KEY, vehicle.vehicle_id);
        sessionStorage.setItem(
            SELECTED_VEHICLE_DATA_STORAGE_KEY,
            JSON.stringify(vehicle),
        );
        telemetryBaseRef.current = {
            ...vehicle.telemetry,
            distanceTravelled: 0,
        };
    }, []);

    const getCurrentTelemetry = useCallback(() => {
        const base = telemetryBaseRef.current;
        if (!base) {
            return null;
        }

        const distance = Math.max(0, Number(distanceTravelledRef.current) || 0);
        const distanceSinceSelection = Math.max(
            0,
            distance - base.distanceTravelled,
        );
        const consumption = Number(base.avg_consumption) || 0;

        return {
            current_fuel: roundToTwoDecimals(Math.max(
                0,
                Number(base.current_fuel) - (distanceSinceSelection * consumption) / 100,
            )),
            avg_consumption: consumption,
            service_due_km: roundToTwoDecimals(Math.max(
                0,
                Number(base.service_due_km) - distanceSinceSelection,
            )),
            service_due_date: base.service_due_date,
            distance_travelled: roundToTwoDecimals(
                (Number(base.distance_travelled) || 0) + distanceSinceSelection,
            ),
        };
    }, []);

    const updateVehicleTelemetry = useCallback((telemetry) => {
        const currentVehicle = selectedVehicleRef.current;
        if (!currentVehicle || !telemetry) {
            return;
        }

        const updatedVehicle = { ...currentVehicle, telemetry };
        setSelectedVehicle(updatedVehicle);
        sessionStorage.setItem(
            SELECTED_VEHICLE_DATA_STORAGE_KEY,
            JSON.stringify(updatedVehicle),
        );
        setVehicles((currentVehicles) =>
            currentVehicles.map((vehicle) =>
                vehicle.vehicle_id === updatedVehicle.vehicle_id
                    ? updatedVehicle
                    : vehicle,
            ),
        );
    }, []);

    const persistCurrentTelemetry = useCallback(async () => {
        if (!selectedVehicle) {
            return;
        }

        const telemetry = getCurrentTelemetry();
        if (!telemetry) {
            return;
        }

        const telemetryForServer = {
            current_fuel: telemetry.current_fuel,
            avg_consumption: telemetry.avg_consumption,
            service_due_km: telemetry.service_due_km,
            service_due_date: telemetry.service_due_date,
        };
        const savedVehicle = await updateVehicleTelemetryRequest(
            selectedVehicle.vehicle_id,
            telemetryForServer,
        );
        telemetryBaseRef.current = {
            ...savedVehicle.telemetry,
            distanceTravelled: distanceTravelledRef.current,
        };
        updateVehicleTelemetry(savedVehicle.telemetry);
    }, [
        getCurrentTelemetry,
        selectedVehicle,
        updateVehicleTelemetry,
    ]);

    useEffect(() => {
        const timer = window.setInterval(() => {
            updateVehicleTelemetry(getCurrentTelemetry());
        }, 500);

        return () => window.clearInterval(timer);
    }, [getCurrentTelemetry, updateVehicleTelemetry]);

    useEffect(() => {
        const saveBeforeLogout = () => {
            persistCurrentTelemetry().catch((persistError) => {
                console.error(persistError);
            });
        };

        window.addEventListener("vehicle:logout", saveBeforeLogout);
        window.__saveVehicleTelemetry = persistCurrentTelemetry;
        return () => {
            window.removeEventListener("vehicle:logout", saveBeforeLogout);
            if (window.__saveVehicleTelemetry === persistCurrentTelemetry) {
                delete window.__saveVehicleTelemetry;
            }
        };
    }, [persistCurrentTelemetry]);

    const createVehicle = useCallback(async (vehicle) => {
        const createdVehicle = await createVehicleRequest(vehicle);
        setVehicles((currentVehicles) => [...currentVehicles, createdVehicle]);
        setSelectedVehicle(createdVehicle);
        sessionStorage.setItem(
            SELECTED_VEHICLE_STORAGE_KEY,
            createdVehicle.vehicle_id,
        );
        sessionStorage.setItem(
            SELECTED_VEHICLE_DATA_STORAGE_KEY,
            JSON.stringify(createdVehicle),
        );
        telemetryBaseRef.current = {
            ...createdVehicle.telemetry,
            distanceTravelled,
        };
        return createdVehicle;
    }, [distanceTravelled]);

    const deleteVehicle = useCallback(async (vehicleId) => {
        await deleteVehicleRequest(vehicleId);
        setVehicles((currentVehicles) =>
            currentVehicles.filter((vehicle) => vehicle.vehicle_id !== vehicleId),
        );
        setSelectedVehicle((currentVehicle) =>
            currentVehicle?.vehicle_id === vehicleId ? null : currentVehicle,
        );
        if (sessionStorage.getItem(SELECTED_VEHICLE_STORAGE_KEY) === vehicleId) {
            sessionStorage.removeItem(SELECTED_VEHICLE_STORAGE_KEY);
            sessionStorage.removeItem(SELECTED_VEHICLE_DATA_STORAGE_KEY);
        }
    }, []);

    const clearSelectedVehicle = useCallback(() => {
        setSelectedVehicle(null);
        telemetryBaseRef.current = null;
        sessionStorage.removeItem(SELECTED_VEHICLE_STORAGE_KEY);
        sessionStorage.removeItem(SELECTED_VEHICLE_DATA_STORAGE_KEY);
    }, []);

    return (
        <VehicleContext.Provider
            value={{
                vehicles,
                selectedVehicle,
                loading,
                error,
                selectVehicle,
                createVehicle,
                deleteVehicle,
                clearSelectedVehicle,
                fetchVehicles,
                persistCurrentTelemetry,
            }}
        >
            {children}
        </VehicleContext.Provider>
    );
}

export function useVehicle() {
    const context = useContext(VehicleContext);

    if (!context) {
        throw new Error("useVehicle must be used inside VehicleProvider");
    }

    return context;
}
