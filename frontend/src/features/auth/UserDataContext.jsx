import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useAuth } from "./AuthContext.jsx";

const UserDataContext = createContext(null);

export function UserProvider({ children }) {
    const { user, logout: authLogout, updatePreferences: authUpdatePreferences } = useAuth();
    const [loading, setLoading] = useState(false);

    const logout = useCallback(async () => {
        const saveVehicleTelemetry = window.__saveVehicleTelemetry;

        try {
            if (typeof saveVehicleTelemetry === "function") {
                await saveVehicleTelemetry();
            }
        } catch (saveError) {
            console.error(saveError);
        } finally {
            authLogout();
        }
    }, [authLogout]);

    useEffect(() => {
        setLoading(false);
    }, [user]);

    return (
        <UserDataContext.Provider
            value={{
                userData: user,
                loading,
                logout,
                updatePreferences: authUpdatePreferences,
            }}
        >
            {children}
        </UserDataContext.Provider>
    );
}

export function useUserData() {
    const context = useContext(UserDataContext);

    if (!context) {
        throw new Error("useUserData must be used inside UserProvider");
    }

    return context;
}
