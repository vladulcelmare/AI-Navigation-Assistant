import { apiClient, getApiError } from "../../lib/apiClient.js";

export async function listVehiclesRequest() {
    const response = await apiClient("/vehicles");
    if (!response.ok) {
        throw new Error(await getApiError(response, "Unable to load vehicles"));
    }
    return response.json();
}

export async function createVehicleRequest(vehicle) {
    const response = await apiClient("/vehicles", {
        method: "POST",
        body: JSON.stringify(vehicle),
    });

    if (!response.ok) {
        throw new Error(await getApiError(response, "Unable to create vehicle"));
    }

    return response.json();
}

export async function deleteVehicleRequest(vehicleId) {
    const response = await apiClient("/vehicles/" + encodeURIComponent(vehicleId), {
        method: "DELETE",
    });

    if (!response.ok) {
        throw new Error(await getApiError(response, "Unable to delete vehicle"));
    }
}

export async function updateVehicleTelemetryRequest(vehicleId, telemetry) {
    const response = await apiClient(
        "/vehicles/" + encodeURIComponent(vehicleId) + "/telemetry",
        {
            method: "POST",
            body: JSON.stringify(telemetry),
        },
    );

    if (!response.ok) {
        throw new Error(await getApiError(response, "Unable to save vehicle telemetry"));
    }

    return response.json();
}
