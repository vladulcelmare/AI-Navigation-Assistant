import {useEffect, useRef} from "react";
import {useMap} from "./MapContext.jsx";

const SOURCE_ID = "ai-route-source";
const LINE_LAYER_ID = "ai-route-line";
const END_LAYER_ID = "ai-route-end";
const STOP_LAYER_ID = "ai-route-stops";
const ROUTE_CORRIDOR_KM = 0.1;

function routeGeometryCoordinates(route) {
    return (route?.geometry || [])
        .map((point) => {
            if (Array.isArray(point)) {
                return [Number(point[0]), Number(point[1])];
            }

            return [Number(point.longitude), Number(point.latitude)];
        })
        .filter(([longitude, latitude]) => Number.isFinite(longitude) && Number.isFinite(latitude));
}

function distanceBetweenPointsKm(first, second) {
    const earthRadiusKm = 6371;
    const toRadians = (value) => (value * Math.PI) / 180;
    const latitudeDelta = toRadians(second[1] - first[1]);
    const longitudeDelta = toRadians(second[0] - first[0]);
    const firstLatitude = toRadians(first[1]);
    const secondLatitude = toRadians(second[1]);
    const haversine =
        Math.sin(latitudeDelta / 2) ** 2 +
        Math.cos(firstLatitude) *
            Math.cos(secondLatitude) *
            Math.sin(longitudeDelta / 2) ** 2;

    return earthRadiusKm * 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
}

function distanceToSegmentKm(point, start, end) {
    const latitudeScale = 111.32;
    const longitudeScale = latitudeScale * Math.cos((point[1] * Math.PI) / 180);
    const segmentX = (end[0] - start[0]) * longitudeScale;
    const segmentY = (end[1] - start[1]) * latitudeScale;
    const pointX = (point[0] - start[0]) * longitudeScale;
    const pointY = (point[1] - start[1]) * latitudeScale;
    const lengthSquared = segmentX ** 2 + segmentY ** 2;
    const position = lengthSquared === 0
        ? 0
        : Math.max(
            0,
            Math.min(1, (pointX * segmentX + pointY * segmentY) / lengthSquared),
        );
    const closestPoint = [
        start[0] + (end[0] - start[0]) * position,
        start[1] + (end[1] - start[1]) * position,
    ];

    return distanceBetweenPointsKm(point, closestPoint);
}

function isOffRoute(route, userLocation) {
    const coordinates = routeGeometryCoordinates(route);
    const currentPosition = [Number(userLocation?.lng), Number(userLocation?.lat)];

    if (
        coordinates.length === 0 ||
        !Number.isFinite(currentPosition[0]) ||
        !Number.isFinite(currentPosition[1])
    ) {
        return false;
    }

    if (coordinates.length === 1) {
        return distanceBetweenPointsKm(currentPosition, coordinates[0]) > ROUTE_CORRIDOR_KM;
    }

    let closestDistance = Number.POSITIVE_INFINITY;
    for (let index = 1; index < coordinates.length; index += 1) {
        closestDistance = Math.min(
            closestDistance,
            distanceToSegmentKm(currentPosition, coordinates[index - 1], coordinates[index]),
        );
    }

    return closestDistance > ROUTE_CORRIDOR_KM;
}

function routeCoordinates(route, userLocation, lastOnRouteIndexRef) {
    const coordinates = routeGeometryCoordinates(route);

    const currentPosition = [
        Number(userLocation?.lng),
        Number(userLocation?.lat),
    ];

    if (
        coordinates.length > 1 &&
        Number.isFinite(currentPosition[0]) &&
        Number.isFinite(currentPosition[1]) &&
        !isOffRoute(route, userLocation)
    ) {
        let nearestPointIndex = 0;
        let nearestDistance = Number.POSITIVE_INFINITY;

        coordinates.forEach(([longitude, latitude], index) => {
            const distance =
                (longitude - currentPosition[0]) ** 2 +
                (latitude - currentPosition[1]) ** 2;

            if (distance < nearestDistance) {
                nearestDistance = distance;
                nearestPointIndex = index;
            }
        });

        lastOnRouteIndexRef.current = nearestPointIndex;
        const remainingCoordinates = coordinates.slice(Math.max(1, nearestPointIndex));

        return [
            currentPosition,
            ...(remainingCoordinates.length
                ? remainingCoordinates
                : [coordinates[coordinates.length - 1]]),
        ];
    }

    return coordinates.slice(lastOnRouteIndexRef.current);
}

function stopCoordinates(route) {
    return (route?.stop_recommendations?.stops || [])
        .map((stop) => [
            Number(stop?.location?.longitude),
            Number(stop?.location?.latitude),
        ])
        .filter(([longitude, latitude]) => Number.isFinite(longitude) && Number.isFinite(latitude));
}

function routeGeoJson(coordinates, route) {
    return {
        type: "FeatureCollection",
        features: [
            {
                type: "Feature",
                properties: {kind: "route"},
                geometry: {type: "LineString", coordinates},
            },
            {
                type: "Feature",
                properties: {kind: "end"},
                geometry: {type: "Point", coordinates: coordinates[coordinates.length - 1]},
            },
            ...stopCoordinates(route).map((stop, index) => ({
                type: "Feature",
                properties: {kind: "stop", stopNumber: index + 1},
                geometry: {type: "Point", coordinates: stop},
            })),
        ],
    };
}

// export function RouteComponent({route, enabled = true}) {
//     const {map, userLocation} = useMap();
//     const lastOnRouteIndexRef = useRef(0);
//
//     useEffect(() => {
//         lastOnRouteIndexRef.current = 0;
//     }, [route]);
//
//     useEffect(() => {
//         const coordinates = routeCoordinates(route, userLocation, lastOnRouteIndexRef);
//
//         if (!map || !enabled || coordinates.length < 2) {
//             return undefined;
//         }
//
//         const routeGeo = routeGeoJson(coordinates);
//
//         const addSourceAndLayers = () => {
//             if (map.getSource?.(SOURCE_ID)) {
//                 map.getSource(SOURCE_ID).setData(routeGeo);
//                 return;
//             }
//
//             map.addSource(SOURCE_ID, {type: "geojson", data: routeGeo});
//             map.addLayer({
//                 id: LINE_LAYER_ID,
//                 type: "line",
//                 source: SOURCE_ID,
//                 layout: {"line-cap": "round", "line-join": "round"},
//                 paint: {"line-color": "#2563eb", "line-width": 5, "line-opacity": 0.95},
//                 filter: ["==", ["get", "kind"], "route"],
//             });
//             map.addLayer({
//                 id: END_LAYER_ID,
//                 type: "circle",
//                 source: SOURCE_ID,
//                 paint: {
//                     "circle-radius": 6,
//                     "circle-color": "#ef4444",
//                     "circle-stroke-color": "#ffffff",
//                     "circle-stroke-width": 2,
//                 },
//                 filter: ["==", ["get", "kind"], "end"],
//             });
//         };
//
//         if (map.isStyleLoaded?.()) {
//             addSourceAndLayers();
//         } else {
//             map.once?.("load", addSourceAndLayers);
//         }
//
//         return () => {
//             if (map.getLayer?.(LINE_LAYER_ID)) map.removeLayer(LINE_LAYER_ID);
//             if (map.getLayer?.(END_LAYER_ID)) map.removeLayer(END_LAYER_ID);
//             if (map.getSource?.(SOURCE_ID)) map.removeSource(SOURCE_ID);
//         };
//     }, [enabled, map, route]);
//
//     useEffect(() => {
//         if (!map || !enabled) {
//             return;
//         }
//
//         const coordinates = routeCoordinates(route, userLocation, lastOnRouteIndexRef);
//         const source = map.getSource?.(SOURCE_ID);
//
//         if (coordinates.length > 1 && source) {
//             source.setData(routeGeoJson(coordinates));
//         }
//     }, [enabled, map, route, userLocation]);
//
//     return null;
// }

export function RouteComponent({
                                   route,
                                   enabled = true,
                                   onRecalculateRoute,
                               }) {
    const {map, userLocation} = useMap();

    const lastOnRouteIndexRef = useRef(0);
    const offRouteCountRef = useRef(0);
    const recalculatingRef = useRef(false);

    useEffect(() => {
        lastOnRouteIndexRef.current = 0;
        offRouteCountRef.current = 0;
        recalculatingRef.current = false;
    }, [route]);

    useEffect(() => {
        if (!enabled || !route || !userLocation) {
            return;
        }

        const offRoute = isOffRoute(route, userLocation);

        if (offRoute) {
            offRouteCountRef.current += 1;
        } else {
            offRouteCountRef.current = 0;
            recalculatingRef.current = false;
        }

        if (
            offRouteCountRef.current >= 3 &&
            !recalculatingRef.current
        ) {
            recalculatingRef.current = true;

            onRecalculateRoute?.({
                lng: Number(userLocation.lng),
                lat: Number(userLocation.lat),
            });
        }
    }, [enabled, route, userLocation, onRecalculateRoute]);

    useEffect(() => {
        const coordinates = routeCoordinates(
            route,
            userLocation,
            lastOnRouteIndexRef,
        );

        if (!map || !enabled || coordinates.length < 2) {
            return undefined;
        }

        const routeGeo = routeGeoJson(coordinates, route);

        const addSourceAndLayers = () => {
            if (map.getSource?.(SOURCE_ID)) {
                map.getSource(SOURCE_ID).setData(routeGeo);
                return;
            }

            map.addSource(SOURCE_ID, {
                type: "geojson",
                data: routeGeo,
            });

            map.addLayer({
                id: LINE_LAYER_ID,
                type: "line",
                source: SOURCE_ID,
                layout: {
                    "line-cap": "round",
                    "line-join": "round",
                },
                paint: {
                    "line-color": "#2563eb",
                    "line-width": 5,
                    "line-opacity": 0.95,
                },
                filter: [
                    "==",
                    ["get", "kind"],
                    "route",
                ],
            });

            map.addLayer({
                id: END_LAYER_ID,
                type: "circle",
                source: SOURCE_ID,
                paint: {
                    "circle-radius": 6,
                    "circle-color": "#ef4444",
                    "circle-stroke-color": "#ffffff",
                    "circle-stroke-width": 2,
                },
                filter: [
                    "==",
                    ["get", "kind"],
                    "end",
                ],
            });

            map.addLayer({
                id: STOP_LAYER_ID,
                type: "circle",
                source: SOURCE_ID,
                paint: {
                    "circle-radius": 8,
                    "circle-color": "#f59e0b",
                    "circle-stroke-color": "#ffffff",
                    "circle-stroke-width": 2,
                },
                filter: [
                    "==",
                    ["get", "kind"],
                    "stop",
                ],
            });
        };

        if (map.isStyleLoaded?.()) {
            addSourceAndLayers();
        } else {
            map.once?.("load", addSourceAndLayers);
        }

        return () => {
            if (map.getLayer?.(LINE_LAYER_ID)) {
                map.removeLayer(LINE_LAYER_ID);
            }

            if (map.getLayer?.(END_LAYER_ID)) {
                map.removeLayer(END_LAYER_ID);
            }
            if (map.getLayer?.(STOP_LAYER_ID)) {
                map.removeLayer(STOP_LAYER_ID);
            }

            if (map.getSource?.(SOURCE_ID)) {
                map.removeSource(SOURCE_ID);
            }
        };
    }, [enabled, map, route]);

    useEffect(() => {
        if (!map || !enabled) {
            return;
        }

        const coordinates = routeCoordinates(
            route,
            userLocation,
            lastOnRouteIndexRef,
        );

        const source = map.getSource?.(SOURCE_ID);

        if (coordinates.length > 1 && source) {
            source.setData(routeGeoJson(coordinates, route));
        }
    }, [enabled, map, route, userLocation]);

    return null;
}

export default RouteComponent;
