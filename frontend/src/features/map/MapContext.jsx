import {useCallback, useRef, useContext, createContext, useMemo, useState} from "react";

const MapContext = createContext(null);
const USER_LOCATION_STORAGE_KEY = "lastUserLocation";

function normalizeLocation(location) {
    const lat = Number(location?.lat);
    const lng = Number(location?.lng);

    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        return null;
    }

    return {lat, lng};
}

function readStoredLocation() {
    try {
        const storedLocation = sessionStorage.getItem(USER_LOCATION_STORAGE_KEY);

        if (!storedLocation) {
            return null;
        }

        const location = normalizeLocation(JSON.parse(storedLocation));
        if (!location) {
            sessionStorage.removeItem(USER_LOCATION_STORAGE_KEY);
        }
        return location;
    } catch (error) {
        console.warn("Unable to restore the last user location.", error);
        return null;
    }
}

function persistLocation(location) {
    try {
        sessionStorage.setItem(USER_LOCATION_STORAGE_KEY, JSON.stringify(location));
    } catch (error) {
        console.warn("Unable to persist the last user location.", error);
    }
}

export function MapProvider({ children }) {
    const mapContainerRef = useRef(null);
    const [map, setMap] = useState(null);
    const [userLocation, setUserLocationState] = useState(readStoredLocation);
    const [distanceTravelled, setDistanceTravelled] = useState(0);
    const [currentRouteId, setCurrentRouteId] = useState(null);
    const previousLocationRef = useRef(userLocation);
    const publishedLocationRef = useRef(userLocation);
    const totalDistanceRef = useRef(0);
    const lastPublishedAtRef = useRef(0);

    const setUserLocation = useCallback((location) => {
        const normalizedLocation = normalizeLocation(location);

        if (!normalizedLocation) return;

        const previousLocation = previousLocationRef.current;
        if (previousLocation) {
            const earthRadiusKm = 6371;
            const toRadians = (value) => (value * Math.PI) / 180;
            const latDelta = toRadians(normalizedLocation.lat - previousLocation.lat);
            const lngDelta = toRadians(normalizedLocation.lng - previousLocation.lng);
            const lat1 = toRadians(previousLocation.lat);
            const lat2 = toRadians(normalizedLocation.lat);
            const haversine =
                Math.sin(latDelta / 2) ** 2 +
                Math.cos(lat1) * Math.cos(lat2) * Math.sin(lngDelta / 2) ** 2;
            totalDistanceRef.current +=
                earthRadiusKm * 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
        }
        previousLocationRef.current = normalizedLocation;

        const now = performance.now();
        if (!publishedLocationRef.current || now - lastPublishedAtRef.current >= 100) {
            lastPublishedAtRef.current = now;
            publishedLocationRef.current = normalizedLocation;
            setUserLocationState(normalizedLocation);
            setDistanceTravelled(totalDistanceRef.current);
            persistLocation(normalizedLocation);
        }
    }, []);

    const value = useMemo(
        () => ({
            map,
            setMap,
            mapContainerRef,
            userLocation,
            setUserLocation,
            distanceTravelled,
            setDistanceTravelled,
            currentRouteId,
            setCurrentRouteId,
        }),
        [map, userLocation, distanceTravelled, setUserLocation, currentRouteId]
    );

    return (
        <MapContext.Provider value={value}>
            {children}
        </MapContext.Provider>
    );
}

export function useMap() {
    const context = useContext(MapContext);

    if (context === null) {
        throw new Error("useMap must be used inside MapProvider");
    }

    return context;
}