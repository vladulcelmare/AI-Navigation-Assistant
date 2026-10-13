import { apiClient, getApiError } from "../../lib/apiClient.js";

export async function loginRequest(email, password) {
    const response = await apiClient("/users/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
        throw new Error(await getApiError(response, "Login failed"));
    }

    return response.json();
}

export async function registerRequest(payload) {
    const response = await apiClient("/users/register", {
        method: "POST",
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        throw new Error(await getApiError(response, "Registration failed"));
    }

    return response.json();
}

export async function currentUserRequest() {
    const response = await apiClient("/users/me");
    return response;
}

export async function updatePreferencesRequest(preferences) {
    const response = await apiClient("/users/me/preferences", {
        method: "PATCH",
        body: JSON.stringify({ preferences }),
    });

    if (!response.ok) {
        throw new Error(await getApiError(response, "Unable to update preferences"));
    }

    return response.json();
}
