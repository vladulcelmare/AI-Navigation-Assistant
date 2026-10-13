import {useMap} from "./MapContext.jsx";

export function CenterMapButton() {
    const {map, userLocation, setUserLocation} = useMap();

    const handleCenterClick = () => {
        console.log("CenterMapButton: click", { mapExists: !!map, userLocation });
        if (!map || !userLocation) return;

        // request userloaction from browser and set it
        // if (!userLocation) {
        //     if (navigator.geolocation?.getCurrentPosition && setUserLocation) {
        //         console.log("CenterMapButton: requesting current position via geolocation API");
        //         navigator.geolocation.getCurrentPosition(
        //             (p) => {
        //                 const pos = { lat: p.coords.latitude, lng: p.coords.longitude };
        //                 console.log("CenterMapButton: geolocation success", pos);
        //                 setUserLocation(pos);
        //                 const lng = Number(pos.lng);
        //                 const lat = Number(pos.lat);
        //                 if (Number.isFinite(lng) && Number.isFinite(lat)) {
        //                     if (map.jumpTo) map.jumpTo({ center: [lng, lat], zoom: map.getZoom ? map.getZoom() : undefined });
        //                     else if (map.setCenter) map.setCenter([lng, lat]);
        //                 }
        //             },
        //             (err) => {
        //                 console.warn("CenterMapButton: geolocation error", err);
        //             },
        //             { enableHighAccuracy: true, timeout: 5000 }
        //         );
        //     } else {
        //         console.warn("CenterMapButton: no geolocation available and no userLocation");
        //     }
        //     return;
        // }

        const lng = Number(userLocation.lng);
        const lat = Number(userLocation.lat);
        console.log("CenterMapButton: click parsed coords", { lng, lat });
        if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
            console.warn("CenterMapButton: click invalid coords", { lng, lat });
            return;
        }
        if (map.jumpTo) {
            console.log("CenterMapButton: click using jumpTo");
            map.jumpTo({ center: [lng, lat], zoom: map.getZoom ? map.getZoom() : undefined });
            map.rotateTo(0, { center: [lng, lat], zoom: 15});
        } else if (map.setCenter) {
            console.log("CenterMapButton: click using setCenter");
            map.setCenter([lng, lat]);
        }
    };

    return(
        <button
            className="z-10 rounded-xl absolute bottom-10 right-10 p-3 bg-white/20 border border-white backdrop-blur-xs"
            onClick={handleCenterClick}
            aria-label="Center map"
        >
            <svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="white" strokeWidth="2">
                <circle cx="12" cy="12" r="3" />
                <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.5 4.5l1.5 1.5M18 18l1.5 1.5M4.5 19.5l1.5-1.5M18 6l1.5-1.5" />
            </svg>
        </button>
    )
}