import { useState } from "react";
import { useVehicle } from "./VehicleContext.jsx";
import electricCarIcon from "../../assets/electric.png";
import fuelCarIcon from "../../assets/fuel.png";
import mockCarIcon from "../../assets/mock.png";

function getVehicleIcon(engineType) {
    const normalizedEngineType = String(engineType || "").toLowerCase();

    if (normalizedEngineType.includes("electric")) {
        return electricCarIcon;
    }

    if (
        normalizedEngineType.includes("combustion") ||
        normalizedEngineType.includes("fuel") ||
        normalizedEngineType.includes("internal")
    ) {
        return fuelCarIcon;
    }

    return mockCarIcon;
}

export function VehicleSelector() {
    const {
        vehicles,
        loading,
        error,
        selectedVehicle,
        selectVehicle,
        createVehicle,
        deleteVehicle,
    } = useVehicle();
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [creating, setCreating] = useState(false);
    const [createError, setCreateError] = useState("");
    const [deleteError, setDeleteError] = useState("");
    const [deletingVehicleId, setDeletingVehicleId] = useState(null);
    const [vehicleImageStatus, setVehicleImageStatus] = useState({});
    const [form, setForm] = useState({
        nickname: "",
        engine_type: "electric",
        total_capacity: "100",
        current_fuel: "100",
        avg_consumption: "15",
        service_due_km: "15000",
        service_due_date: "",
    });

    if (selectedVehicle || (
        loading &&
        sessionStorage.getItem("selectedVehicleId") &&
        sessionStorage.getItem("selectedVehicle")
    )) {
        return null;
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/20 backdrop-blur-xs p-4">
            <section
                aria-labelledby="vehicle-selector-title"
                className="w-full max-w-lg rounded-xl border border-white bg-white/40 p-6 text-white shadow-2xl"
            >
                <h2 id="vehicle-selector-title" className="text-xl font-bold">
                    Select your vehicle
                </h2>
                <p className="mt-1 text-sm text-gray-700">
                    Choose the vehicle you want to use for this session.
                </p>

                <button
                    type="button"
                    onClick={() => {
                        setShowCreateForm((visible) => !visible);
                        setCreateError("");
                    }}
                    className="mt-4 flex items-center gap-2 rounded-lg border border-white/70 bg-white/30 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-white/70 hover:text-gray-900"
                >
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/50">
                        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                            <path d="M3 17h18M5 17l1.5-6h8l3 3H21v3M8 17a2 2 0 1 1-4 0m14 0a2 2 0 1 1-4 0M9 11V8h4l2.5 3" />
                            <path d="M19 3v5m-2.5-2.5h5" />
                        </svg>
                    </span>
                    Add vehicle
                </button>

                {showCreateForm && (
                    <form
                        className="mt-4 grid gap-3 rounded-xl border border-white/50 bg-white/20 p-4 sm:grid-cols-2"
                        onSubmit={async (event) => {
                            event.preventDefault();
                            setCreating(true);
                            setCreateError("");

                            try {
                                await createVehicle({
                                    nickname: form.nickname,
                                    engine_type: form.engine_type,
                                    total_capacity: Number(form.total_capacity),
                                    telemetry: {
                                        current_fuel: Number(form.current_fuel),
                                        avg_consumption: Number(form.avg_consumption),
                                        service_due_km: Number(form.service_due_km),
                                        service_due_date: `${form.service_due_date}T00:00:00Z`,
                                    },
                                });
                            } catch (creationError) {
                                setCreateError(creationError.message);
                            } finally {
                                setCreating(false);
                            }
                        }}
                    >
                        <label className="text-sm text-gray-800 sm:col-span-2">
                            Vehicle nickname
                            <input
                                required
                                maxLength="100"
                                type="text"
                                value={form.nickname}
                                onChange={(event) => setForm({...form, nickname: event.target.value})}
                                className="mt-1 w-full rounded-md border border-white/60 bg-white/50 p-2 text-gray-900"
                            />
                        </label>
                        <label className="text-sm text-gray-800">
                            Engine type
                            <select
                                value={form.engine_type}
                                onChange={(event) => setForm({...form, engine_type: event.target.value})}
                                className="mt-1 w-full rounded-md border border-white/60 bg-white/50 p-2 text-gray-900"
                            >
                                <option value="electric">Electric</option>
                                <option value="internal_combustion">Internal combustion</option>
                            </select>
                        </label>
                        <label className="text-sm text-gray-800">
                            Total capacity
                            <input
                                required
                                min="1"
                                type="number"
                                value={form.total_capacity}
                                onChange={(event) => setForm({...form, total_capacity: event.target.value})}
                                className="mt-1 w-full rounded-md border border-white/60 bg-white/50 p-2 text-gray-900"
                            />
                        </label>
                        <label className="text-sm text-gray-800">
                            Current fuel / battery
                            <input
                                required
                                min="0"
                                max="100"
                                type="number"
                                value={form.current_fuel}
                                onChange={(event) => setForm({...form, current_fuel: event.target.value})}
                                className="mt-1 w-full rounded-md border border-white/60 bg-white/50 p-2 text-gray-900"
                            />
                        </label>
                        <label className="text-sm text-gray-800">
                            Average consumption
                            <input
                                required
                                min="0"
                                type="number"
                                value={form.avg_consumption}
                                onChange={(event) => setForm({...form, avg_consumption: event.target.value})}
                                className="mt-1 w-full rounded-md border border-white/60 bg-white/50 p-2 text-gray-900"
                            />
                        </label>
                        <label className="text-sm text-gray-800">
                            Service due (km)
                            <input
                                required
                                min="0"
                                type="number"
                                value={form.service_due_km}
                                onChange={(event) => setForm({...form, service_due_km: event.target.value})}
                                className="mt-1 w-full rounded-md border border-white/60 bg-white/50 p-2 text-gray-900"
                            />
                        </label>
                        <label className="text-sm text-gray-800">
                            Service due date
                            <input
                                required
                                type="date"
                                value={form.service_due_date}
                                onChange={(event) => setForm({...form, service_due_date: event.target.value})}
                                className="mt-1 w-full rounded-md border border-white/60 bg-white/50 p-2 text-gray-900"
                            />
                        </label>
                        {createError && (
                            <p className="sm:col-span-2 text-sm text-red-700">{createError}</p>
                        )}
                        <button
                            type="submit"
                            disabled={creating}
                            className="sm:col-span-2 rounded-md bg-white/70 px-3 py-2 font-semibold text-gray-900 transition-colors hover:bg-white disabled:opacity-50"
                        >
                            {creating ? "Creating..." : "Create vehicle"}
                        </button>
                    </form>
                )}

                {!showCreateForm && loading && (
                    <p className="mt-5 text-sm text-gray-700">Loading vehicles...</p>
                )}
                {!showCreateForm && error && (
                    <p className="mt-5 text-sm text-red-600">{error}</p>
                )}
                {deleteError && (
                    <p className="mt-5 text-sm text-red-600">{deleteError}</p>
                )}
                {!showCreateForm && !loading && !error && vehicles.length === 0 && (
                    <p className="mt-5 text-sm text-gray-700">
                        No vehicles are associated with this account.
                    </p>
                )}
                {!showCreateForm && !loading && !error && vehicles.length > 0 && (
                    <ul className="mt-5 grid max-h-[28rem] grid-cols-2 gap-4 overflow-y-auto pr-1">
                    {vehicles.map((vehicle) => (
                        <li
                            key={vehicle.vehicle_id}
                            className="relative rounded-xl border border-white/50 bg-white/20 p-3 transition-colors hover:bg-white/40"
                        >
                            <button
                                type="button"
                                onClick={() => selectVehicle(vehicle)}
                                className="flex w-full flex-col items-center rounded-lg p-2 text-center transition-colors hover:bg-white/50"
                            >
                                <div className="relative flex h-28 w-full items-center justify-center rounded-lg bg-white/30 p-3">
                                    {vehicleImageStatus[vehicle.vehicle_id] !== "loaded" &&
                                        vehicleImageStatus[vehicle.vehicle_id] !== "error" && (
                                            <span
                                                className="loading-shimmer absolute inset-3 rounded-md"
                                                role="status"
                                                aria-label="Loading vehicle image"
                                            />
                                        )}
                                    <img
                                        src={getVehicleIcon(vehicle.engine_type)}
                                        alt={`${vehicle.engine_type} vehicle`}
                                        className={`h-full object-contain transition-opacity duration-300 ${
                                            vehicleImageStatus[vehicle.vehicle_id] === "loaded"
                                                ? "opacity-100"
                                                : vehicleImageStatus[vehicle.vehicle_id] === "error"
                                                    ? "opacity-50"
                                                    : "opacity-0"
                                        }`}
                                        onLoad={() =>
                                            setVehicleImageStatus((currentStatus) => ({
                                                ...currentStatus,
                                                [vehicle.vehicle_id]: "loaded",
                                            }))
                                        }
                                        onError={() =>
                                            setVehicleImageStatus((currentStatus) => ({
                                                ...currentStatus,
                                                [vehicle.vehicle_id]: "error",
                                            }))
                                        }
                                    />
                                    {vehicleImageStatus[vehicle.vehicle_id] === "error" && (
                                        <span className="absolute text-xs font-medium text-white/80">
                                            Image unavailable
                                        </span>
                                    )}
                                </div>
                                <p className="mt-3 w-full truncate text-base font-semibold text-white">
                                        {vehicle.nickname}
                                </p>
                                <p className="mt-1 text-xs font-medium uppercase tracking-wide text-gray-700">
                                    {vehicle.engine_type === 'electric'?'Electric':'Internal Combustion'}
                                </p>
                            </button>
                            <button
                                type="button"
                                aria-label={`Delete vehicle ${vehicle.nickname}`}
                                disabled={deletingVehicleId === vehicle.vehicle_id}
                                onClick={async (event) => {
                                    event.stopPropagation();
                                    if (!window.confirm(`Delete vehicle ${vehicle.nickname}?`)) {
                                        return;
                                    }

                                    setDeletingVehicleId(vehicle.vehicle_id);
                                    setDeleteError("");
                                    try {
                                        await deleteVehicle(vehicle.vehicle_id);
                                    } catch (deletionError) {
                                        setDeleteError(deletionError.message);
                                    } finally {
                                        setDeletingVehicleId(null);
                                    }
                                }}
                                className="absolute right-2 top-2 rounded-md bg-red-500/70 px-2 py-1 text-xs font-semibold text-white transition-colors hover:bg-red-600 disabled:opacity-50"
                            >
                                {deletingVehicleId === vehicle.vehicle_id ? "..." : "Delete"}
                            </button>
                        </li>
                    ))}
                    </ul>
                )}
            </section>
        </div>
    );
}
