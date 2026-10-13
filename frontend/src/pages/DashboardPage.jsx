import { useCallback, useEffect, useState } from "react";
import {MapComponent} from "../features/map/Map.jsx";
import {TopNav} from "../components/layout/TopNav.jsx";
import {SideMenu} from "../components/layout/SideMenu.jsx";
import {EnergyIndicator} from "../features/vehicles/EnergyIndicator.jsx";
import { UserLocation } from "../features/map/UserLocation.jsx";
import {CenterMapButton} from "../features/map/CenterMapButton.jsx";
import {RangeComponent} from "../features/vehicles/RangeIndicator.jsx";
import ServiceIndicatorComponent from "../features/vehicles/ServiceIndicator.jsx";
import DistanceTravelledComponent from "../features/vehicles/DistanceTravelled.jsx";
import RouteComponent from "../features/map/RouteComponent.jsx";
import {UserCard} from "../features/auth/UserCard.jsx";
import {VehicleSelector} from "../features/vehicles/VehicleSelector.jsx";
import {VehicleProvider} from "../features/vehicles/VehicleContext.jsx";
import {
    ActiveConversation,
    ConversationList, locationPayload,
    NewConversation,
    PartnerRouteSummary,
} from "../features/assistant/Conversations.jsx";
import {useMap} from "../features/map/MapContext.jsx";

const ROUTE_STORAGE_KEY = "lastAiRoute";

function readStoredRoute() {
    try {
        const storedRoute = sessionStorage.getItem(ROUTE_STORAGE_KEY);
        if (!storedRoute) {
            return null;
        }

        const route = JSON.parse(storedRoute);
        if (!route || typeof route !== "object") {
            sessionStorage.removeItem(ROUTE_STORAGE_KEY);
            return null;
        }
        return route && typeof route === "object" ? route : null;
    } catch (error) {
        console.warn("Unable to restore the last AI route.", error);
        return null;
    }
}


function persistRoute(route) {
    try {
        if (route) {
            sessionStorage.setItem(ROUTE_STORAGE_KEY, JSON.stringify(route));
        } else {
            sessionStorage.removeItem(ROUTE_STORAGE_KEY);
        }
    } catch (error) {
        console.warn("Unable to persist the last AI route.", error);
    }
}

export function DashboardPage(){
    const [activeConversation, setActiveConversation] = useState(null);
    const [conversationRefreshKey, setConversationRefreshKey] = useState(0);
    const [menuView, setMenuView] = useState("conversations");
    const [previewRoute, setPreviewRoute] = useState(readStoredRoute);
    const {currentRouteId, userLocation} = useMap()

    useEffect(() => {
        persistRoute(previewRoute);
    }, [previewRoute]);

    const handleRouteChange = useCallback((route) => {
        setPreviewRoute(route);
    }, []);

    function handleConversationCreated(conversation) {
        setActiveConversation(conversation.conversation_id);
        setConversationRefreshKey((key) => key + 1);
        setPreviewRoute(null);
        setMenuView("current");
    }

    function handleConversationSelected(conversationId) {
        setActiveConversation(conversationId);
        setPreviewRoute(null);
        setMenuView("current");
    }

    function handleConversationDeleted(conversationId) {
        if (activeConversation === conversationId) {
            setActiveConversation(null);
            setPreviewRoute(null);
            setMenuView("conversations");
        }
    }

    const handleRouteRecalculation = useCallback(
        async () => {
            if (!currentRouteId || !userLocation) {
                return;
            }

            const token = localStorage.getItem("token");

            if (!token) {
                console.error("JWT token not found.");
                return;
            }

            try {
                const response = await fetch(
                    `http://localhost:8000/trips/${currentRouteId}/recalculate`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            Authorization: `Bearer ${token}`,
                        },
                        body: JSON.stringify({
                            current_location: locationPayload(userLocation),
                        }),
                    },
                );

                if (!response.ok) {
                    throw new Error(
                        `Route recalculation failed: ${response.status}`,
                    );
                }

                const result = await response.json();

                setPreviewRoute({
                    ...result.trip.route,
                    partner_route: result.partner_route || null,
                    stop_recommendations: result.stop_recommendations || null,
                });
            } catch (error) {
                console.error("Route recalculation failed.", error);
            }
        },
        [currentRouteId, userLocation],
    );


    return (
        <VehicleProvider>
            <MapComponent />
            <TopNav>
                <EnergyIndicator/>
                <RangeComponent/>
                <ServiceIndicatorComponent />
                <DistanceTravelledComponent />
                <UserCard />
            </TopNav>
            <SideMenu side={"left"}>
                <div className="flex h-[65vh] min-h-[280px] min-w-0 flex-col">
                    <nav
                        aria-label="Conversation navigation"
                        className="mb-3 flex shrink-0 rounded-lg border border-white/20 bg-black/20 p-1"
                    >
                        <button
                            type="button"
                            onClick={() => setMenuView("conversations")}
                            className={`flex-1 rounded px-3 py-2 text-sm ${
                                menuView === "conversations"
                                    ? "bg-white text-gray-900"
                                    : "text-white hover:bg-white/10"
                            }`}
                        >
                            Conversations
                        </button>
                        <button
                            type="button"
                            onClick={() => setMenuView("current")}
                            className={`flex-1 rounded px-3 py-2 text-sm ${
                                menuView === "current"
                                    ? "bg-white text-gray-900"
                                    : "text-white hover:bg-white/10"
                            }`}
                        >
                            Current conversation
                        </button>
                    </nav>
                    {menuView === "conversations" ? (
                        <>
                            <div className="shrink-0 px-3 pb-2 text-white">
                                <h2 className="text-lg font-semibold">Conversations</h2>
                                <p className="text-xs text-white/70">Ask the in-car assistant for help.</p>
                            </div>
                            <NewConversation onConversationCreated={handleConversationCreated} />
                            <div className="min-h-0 flex-1 overflow-y-auto">
                                <ConversationList
                                    activeConversation={activeConversation}
                                    setConversation={handleConversationSelected}
                                    onConversationDeleted={handleConversationDeleted}
                                    refreshKey={conversationRefreshKey}
                                />
                            </div>
                        </>
                    ) : (
                        <ActiveConversation
                            activeConversation={activeConversation}
                            embedded
                            onRouteChange={handleRouteChange}
                        />
                    )}
                </div>
            </SideMenu>
            <VehicleSelector/>
            <CenterMapButton/>
            <div className="pointer-events-none fixed bottom-5 left-1/2 z-10 w-[min(360px,calc(100vw-2rem))] -translate-x-1/2">
                <PartnerRouteSummary partnerRoute={previewRoute?.partner_route} />
            </div>
            <RouteComponent route={previewRoute} onRecalculateRoute={handleRouteRecalculation} />
            <UserLocation />
        </VehicleProvider>
    )
}
