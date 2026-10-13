import {useEffect, useRef, useState} from "react";
import "maplibre-gl/dist/maplibre-gl.css";
import { Map, setWorkerUrl } from "maplibre-gl";

import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import {useMap} from "./MapContext.jsx";

setWorkerUrl(workerUrl);

const GEOAPIFY_API_KEY = import.meta.env.VITE_GEOAPIFY_KEY;
const GEOAPIFY_MAP_STYLE_URL = import.meta.env.VITE_GEOAPIFY_MAP_STYLE_URL;
const USE_MOCK = import.meta.env.VITE_USE_MOCK_MAP;

function LoadingSkeleton({label}) {
    return (
        <div className="flex w-full flex-col items-center gap-4 px-8" role="status" aria-label={label}>
            <div className="loading-shimmer h-8 w-2/3 rounded-lg" />
            <div className="loading-shimmer h-4 w-1/3 rounded" />
        </div>
    );
}

export function RealMap(){
    const {setMap} = useMap();
    const mapContainerRef = useRef(null);
    const [mapLoaded, setMapLoaded] = useState(false);
    const [mapError, setMapError] = useState(false);

    useEffect(() => {
        const map = new Map({
            container: mapContainerRef.current,

            style:
                GEOAPIFY_MAP_STYLE_URL +
                "?apiKey=" +
                GEOAPIFY_API_KEY,

            center: [26.8, 45.8],
            zoom: 6,
        });

        const handleLoad = () => setMapLoaded(true);
        const handleError = () => setMapError(true);

        map.once("load", handleLoad);
        map.on("error", handleError);
        setMap(map);

        return () => {
            map.off("error", handleError);
            map.remove();
        };
    }, []);

    return (
        <div
            ref={mapContainerRef}
            className="fixed left-0 top-0 z-0 flex h-screen w-screen items-center justify-center bg-[#e5e7eb]"
        >
            {!mapLoaded && (
                <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-900/70 backdrop-blur-sm">
                    {mapError ? (
                        <p className="text-sm font-medium text-white">Unable to load the map.</p>
                    ) : (
                        <LoadingSkeleton label="Loading map" />
                    )}
                </div>
            )}
        </div>
    );
}

export function MockMap() {
    const [mapLoaded, setMapLoaded] = useState(false);
    const [mapError, setMapError] = useState(false);

    return (
        <div
            className="fixed left-0 top-0 -z-10 flex h-screen w-screen items-center justify-center bg-[#e5e7eb]"
        >
            {!mapLoaded && (
                <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-900/70">
                    {mapError ? (
                        <p className="text-sm font-medium text-white">Unable to load the map.</p>
                    ) : (
                        <LoadingSkeleton label="Loading map" />
                    )}
                </div>
            )}
            <img
                src="../src/assets/mock.png"
                alt="mock_map"
                className={`h-full transition-opacity duration-300 ${mapLoaded ? "opacity-100" : "opacity-0"}`}
                onLoad={() => setMapLoaded(true)}
                onError={() => setMapError(true)}
            />
        </div>
    );
}

export function MapComponent() {
    if(USE_MOCK === "true"){
        return <MockMap />;
    }
    else
        return <RealMap />;
}
