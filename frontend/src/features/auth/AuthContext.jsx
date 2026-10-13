import { createContext, useContext, useEffect, useState } from "react";
import {
    currentUserRequest,
    loginRequest,
    registerRequest,
    updatePreferencesRequest,
} from "./authApi.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [authLoading, setAuthLoading] = useState(true);

    async function getCurrentUser() {
        const token = localStorage.getItem("token");
        if (!token) {
            setUser(null);
            return null;
        }

        const response = await currentUserRequest();

        if (!response.ok) {
            localStorage.removeItem("token");
            sessionStorage.removeItem("selectedVehicleId");
            sessionStorage.removeItem("selectedVehicle");
            setUser(null);
            return null;
        }

        const currentUser = await response.json();
        setUser(currentUser);
        return currentUser;
    }

    async function login(email, password) {
        const data = await loginRequest(email, password);
        localStorage.setItem("token", data.access_token);
        return getCurrentUser();
    }

    async function register(username, email, password, confirmPassword, preferences) {
        if (password !== confirmPassword) {
            throw new Error("Passwords do not match");
        }

        return registerRequest({ username, email, password, preferences });
    }

    function logout() {
        localStorage.removeItem("token");
        sessionStorage.removeItem("selectedVehicleId");
        sessionStorage.removeItem("selectedVehicle");
        setUser(null);
    }

    async function updatePreferences(preferences) {
        const updatedUser = await updatePreferencesRequest(preferences);
        setUser(updatedUser);
        return updatedUser;
    }

    useEffect(() => {
        getCurrentUser().finally(() => setAuthLoading(false));
    }, []);

    return (
        <AuthContext.Provider value={{ user, login, register, logout, updatePreferences, authLoading }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used inside AuthProvider");
    }
    return context;
}
