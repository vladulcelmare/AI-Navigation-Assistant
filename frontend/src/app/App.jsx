import {DashboardPage} from "../pages/DashboardPage.jsx";
import {LoginCard} from "../pages/LoginPage.jsx";
import {AuthProvider, useAuth} from "../features/auth/AuthContext.jsx";
import {MapProvider} from "../features/map/MapContext.jsx";
import { UserProvider } from "../features/auth/UserDataContext.jsx";

function AppContent() {
    const {user, authLoading} = useAuth();

    if (authLoading) {
        return null;
    }

    if (!user) {
        return (
            <div
                className="relative min-h-screen overflow-hidden bg-[#07111f] flex items-center justify-center"
                style={{
                    backgroundImage: [
                        "radial-gradient(circle at 18% 22%, rgba(38, 180, 190, 0.24), transparent 26%)",
                        "radial-gradient(circle at 82% 78%, rgba(36, 92, 180, 0.28), transparent 30%)",
                        "linear-gradient(118deg, transparent 0 38%, rgba(120, 220, 210, 0.14) 38.2%, transparent 38.5% 100%)",
                        "linear-gradient(28deg, transparent 0 62%, rgba(255, 255, 255, 0.08) 62.2%, transparent 62.5% 100%)",
                        "linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px)",
                        "linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px)",
                    ].join(","),
                    backgroundSize: "auto, auto, auto, auto, 42px 42px, 42px 42px",
                }}
            >
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-cyan-300/10" />
                <LoginCard/>
            </div>
        );
    }

    return (
        <UserProvider>
            <MapProvider>
                <DashboardPage/>
            </MapProvider>
        </UserProvider>
    );
}

export default function App() {
    return (
        <AuthProvider>
            <AppContent/>
        </AuthProvider>
    );
}
