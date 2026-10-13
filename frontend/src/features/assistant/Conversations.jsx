import {useEffect, useRef, useState} from "react";
import {useMap} from "../map/MapContext.jsx";
import {useVehicle} from "../vehicles/VehicleContext.jsx";
import {ChatBubble} from "./ChatBubble.jsx";
import {ChatInput} from "./ChatInput.jsx";
import {
    acceptConversationRecommendation,
    createConversation,
    deleteConversation,
    getConversation,
    getConversations,
    sendConversationMessage,
} from "./conversationsApi.js";
import {useRoutes} from "react-router-dom";

export function NewConversation({onConversationCreated}) {
    const [title, setTitle] = useState("");
    const [isCreating, setIsCreating] = useState(false);
    const [error, setError] = useState("");

    async function handleCreateConversation(event) {
        event.preventDefault();
        const trimmedTitle = title.trim();

        if (!trimmedTitle || isCreating) {
            return;
        }

        setIsCreating(true);
        setError("");

        try {
            const conversation = await createConversation(trimmedTitle);
            setTitle("");
            onConversationCreated?.(conversation);
        } catch (createError) {
            console.error(createError);
            setError(createError.message);
        } finally {
            setIsCreating(false);
        }
    }

    return (
        <form className="flex w-full gap-2 border-b border-white/20 p-3" onSubmit={handleCreateConversation}>
            <label className="sr-only" htmlFor="new-conversation-title">
                New conversation title
            </label>
            <input
                id="new-conversation-title"
                type="text"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Conversation title"
                disabled={isCreating}
                className="min-w-0 flex-1 rounded border border-white/40 bg-black/20 px-3 py-2 text-sm text-white outline-none placeholder:text-white/60 focus:border-white"
            />
            <button
                type="submit"
                disabled={isCreating || !title.trim()}
                className="rounded border border-white px-3 py-2 text-sm text-white disabled:opacity-50"
            >
                {isCreating ? "..." : "New"}
            </button>
            {error && <p className="basis-full text-xs text-red-200">{error}</p>}
        </form>
    );
}

export function ConversationList({
    setConversation,
    activeConversation,
    onConversationDeleted,
    refreshKey = 0,
}) {
    const [conversations, setConversations] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState("");
    const [deletingConversationId, setDeletingConversationId] = useState(null);

    useEffect(() => {
        const controller = new AbortController();
        setIsLoading(true);
        setError("");

        getConversations(controller.signal)
            .then(setConversations)
            .catch((loadError) => {
                if (loadError.name !== "AbortError") {
                    console.error(loadError);
                    setError(loadError.message);
                }
            })
            .finally(() => {
                if (!controller.signal.aborted) {
                    setIsLoading(false);
                }
            });

        return () => controller.abort();
    }, [refreshKey]);

    async function handleDeleteConversation(event, conversationId) {
        event.stopPropagation();

        if (deletingConversationId) {
            return;
        }

        setDeletingConversationId(conversationId);

        try {
            await deleteConversation(conversationId);
            setConversations((currentConversations) =>
                currentConversations.filter(
                    (conversation) => conversation.conversation_id !== conversationId,
                ),
            );
            onConversationDeleted?.(conversationId);
        } catch (deleteError) {
            console.error(deleteError);
            setError(deleteError.message);
        } finally {
            setDeletingConversationId(null);
        }
    }

    if (isLoading) {
        return <p className="p-4 text-sm text-white/70">Loading conversations...</p>;
    }

    if (error) {
        return <p className="p-4 text-sm text-red-200">{error}</p>;
    }

    if (conversations.length === 0) {
        return <p className="p-4 text-sm text-white/70">Create a conversation to ask the assistant for help.</p>;
    }

    return (
        <div className="flex w-full flex-col text-left text-white">
            {conversations.map((conversation) => {
                const isActive = activeConversation === conversation.conversation_id;
                const isDeleting = deletingConversationId === conversation.conversation_id;

                return (
                    <div
                        key={conversation.conversation_id}
                        className={`flex items-center gap-3 border-b border-white/10 p-3 ${
                            isActive ? "bg-white/15" : "hover:bg-white/10"
                        }`}
                    >
                        <button
                            type="button"
                            onClick={() => setConversation(conversation.conversation_id)}
                            className="min-w-0 flex-1 text-left"
                        >
                            <h3 className="truncate text-sm font-semibold">{conversation.title}</h3>
                        </button>
                        <button
                            type="button"
                            className="rounded border border-white/40 px-2 py-1 text-xs disabled:opacity-50"
                            disabled={isDeleting}
                            onClick={(event) =>
                                handleDeleteConversation(event, conversation.conversation_id)
                            }
                        >
                            {isDeleting ? "..." : "Delete"}
                        </button>
                    </div>
                );
            })}
        </div>
    );
}

function normalizeMessages(conversationId, messages = []) {
    return messages.map((message, index) => ({
        message_id: `${conversationId}-${index}`,
        message_text: message.content,
        sent_by: message.role,
    }));
}

export function locationPayload(userLocation) {
    if (!userLocation) {
        return undefined;
    }

    return {
        latitude: Number(userLocation.lat),
        longitude: Number(userLocation.lng),
    };
}

function RecommendationCard({
    recommendation,
    isAccepting,
    error,
    onAccept,
}) {

    const route = recommendation?.route;
    return (
        <div className="mt-3 rounded-xl border border-cyan-200/60 bg-cyan-950/50 p-3 text-sm text-white">
            <p className="font-semibold">AI route recommendation</p>
            {route && (
                <p className="mt-1 text-white/80">
                    {Number(route.distance_km).toFixed(1)} km,{" "}
                    {Math.round(Number(route.duration_minutes))} minutes
                </p>
            )}
            <PartnerRouteSummary partnerRoute={recommendation?.partner_route} />
            <p className="mt-2 text-white/80">Would you like to accept this route?</p>
            {error && <p className="mt-2 text-sm text-red-200">{error}</p>}
            <button
                type="button"
                onClick={() => {onAccept(recommendation)}}
                disabled={isAccepting || recommendation.accepted_trip_id}
                className="mt-3 rounded-lg bg-cyan-200 px-3 py-2 font-semibold text-gray-900 disabled:opacity-50"
            >
                {recommendation.accepted_trip_id
                    ? "Route accepted"
                    : isAccepting
                        ? "Accepting..."
                        : "Accept route"}
            </button>
        </div>
    );
}

export function PartnerRouteSummary({partnerRoute}) {
    if (!partnerRoute) {
        return null;
    }

    const station = partnerRoute.station || {};
    const stationName = station.name || station.station_name || "partner stop";
    const detourMinutes = Number(partnerRoute.detour_minutes);
    const detourDistance = Number(partnerRoute.detour_distance_km);
    const details = [];

    if (Number.isFinite(detourMinutes)) {
        details.push(`${Math.round(detourMinutes)} min detour`);
    }
    if (Number.isFinite(detourDistance)) {
        details.push(`${detourDistance.toFixed(1)} km extra`);
    }

    return (
        <div className="mt-2 rounded-lg border border-amber-200/50 bg-amber-950/40 p-2 text-xs text-amber-100">
            <p className="font-semibold">Partner route available</p>
            <p>
                Via {stationName}
                {details.length > 0 ? ` (${details.join(", ")})` : ""}
            </p>
        </div>
    );
}

export function ActiveConversation({
    activeConversation,
    embedded = false,
    onRouteChange,
}) {
    const {userLocation, setCurrentRouteId} = useMap();
    const {selectedVehicle, persistCurrentTelemetry} = useVehicle();
    const [conversation, setConversationData] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState("");
    const [waitingConversationId, setWaitingConversationId] = useState(null);
    const [acceptingRecommendationId, setAcceptingRecommendationId] = useState(null);
    const [acceptError, setAcceptError] = useState("");
    const messagesContainerRef = useRef(null);
    const activeConversationRef = useRef(activeConversation);

    useEffect(() => {
        activeConversationRef.current = activeConversation;
    }, [activeConversation]);

    useEffect(() => {
        if (!activeConversation) {
            setConversationData(null);
            return undefined;
        }

        const controller = new AbortController();
        setIsLoading(true);
        setError("");
        setConversationData(null);

        getConversation(activeConversation, controller.signal)
            .then((data) => {
                setConversationData({
                    ...data,
                    messages: normalizeMessages(activeConversation, data.messages),
                    recommendations: data.recommendations || [],
                });
            })
            .catch((loadError) => {
                if (loadError.name !== "AbortError") {
                    console.error(loadError);
                    setError(loadError.message);
                }
            })
            .finally(() => {
                if (!controller.signal.aborted) {
                    setIsLoading(false);
                }
            });

        return () => controller.abort();
    }, [activeConversation]);

    useEffect(() => {
        if (messagesContainerRef.current) {
            messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
        }
    }, [conversation]);

    useEffect(() => {
        const recommendations = conversation?.recommendations || [];
        const latestRecommendation = recommendations[recommendations.length - 1];
        onRouteChange?.(
            latestRecommendation?.route
                ? {
                    ...latestRecommendation.route,
                    partner_route: latestRecommendation.partner_route || null,
                    stop_recommendations: latestRecommendation.stop_recommendations || null,
                }
                : null,
        );
    }, [conversation?.recommendations, onRouteChange]);

    async function handleSendMessage(messageText) {
        if (!activeConversation || waitingConversationId) {
            return;
        }

        const conversationId = activeConversation;
        const optimisticMessage = {
            message_id: `pending-${Date.now()}`,
            message_text: messageText,
            sent_by: "user",
        };

        setConversationData((currentConversation) => ({
            ...currentConversation,
            messages: [...(currentConversation?.messages || []), optimisticMessage],
        }));
        setWaitingConversationId(conversationId);
        setError("");

        try {
            const response = await sendConversationMessage(conversationId, {
                content: messageText,
                vehicle_id: selectedVehicle?.vehicle_id,
                current_location: locationPayload(userLocation),
            });

            if (activeConversationRef.current !== conversationId) {
                return;
            }

            setConversationData((currentConversation) => ({
                ...currentConversation,
                messages: [
                    ...(currentConversation?.messages || []),
                    {
                        message_id: `assistant-${Date.now()}`,
                        message_text: response.response,
                        sent_by: "assistant",
                    },
                ],
                recommendations: response.recommendations?.length
                    ? response.recommendations
                    : currentConversation?.recommendations || [],
            }));
        } catch (sendError) {
            console.error(sendError);
            setError(sendError.message);
            setConversationData((currentConversation) => ({
                ...currentConversation,
                messages: (currentConversation?.messages || []).filter(
                    (message) => message.message_id !== optimisticMessage.message_id,
                ),
            }));
            throw sendError;
        } finally {
            setWaitingConversationId(null);
        }
    }

    async function handleAcceptRecommendation(recommendation) {
        if (!activeConversation || !userLocation || acceptingRecommendationId) {
            if (!userLocation) {
                setAcceptError("Your current location is not available yet.");
            }
            return;
        }

        setAcceptingRecommendationId(recommendation.recommendation_id);
        setAcceptError("");

        try {
            await persistCurrentTelemetry();

            const trip = await acceptConversationRecommendation(
                activeConversation,
                recommendation.recommendation_id,
                {
                    choices: recommendation.choices || {},
                    current_location: locationPayload(userLocation),
                },
            );

            setCurrentRouteId(trip.trip_id);

            setConversationData((currentConversation) => ({
                ...currentConversation,
                recommendations: (currentConversation?.recommendations || []).map((item) =>
                    item.recommendation_id === recommendation.recommendation_id
                        ? {
                            ...item,
                            accepted_trip_id: trip.trip_id,
                            route: trip.route,
                        }
                        : item,
                ),
            }));
            onRouteChange?.({
                ...trip.route,
                partner_route: recommendation.partner_route || null,
                stop_recommendations: recommendation.stop_recommendations || null,
            });
        } catch (acceptRouteError) {
            console.error(acceptRouteError);
            setAcceptError(acceptRouteError.message);
        } finally {
            setAcceptingRecommendationId(null);
        }
    }

    if (!activeConversation) {
        return embedded ? (
            <div className="flex min-h-0 flex-1 items-center justify-center p-6 text-center text-sm text-white/70">
                Select a conversation to start chatting.
            </div>
        ) : null;
    }

    return (
        <section
            className={
                embedded
                    ? "flex min-h-0 flex-1 flex-col overflow-hidden p-1 text-white"
                    : "fixed bottom-5 right-5 z-10 flex h-[min(70vh,600px)] w-[min(640px,calc(100vw-2rem))] flex-col overflow-hidden rounded-2xl border border-white/60 bg-black/55 p-4 text-white shadow-2xl backdrop-blur-sm"
            }
        >
            <header className="border-b border-white/20 pb-3">
                <h2 className="truncate text-lg font-semibold">
                    {conversation?.conversation_title || "Conversation"}
                </h2>
            </header>
            <div ref={messagesContainerRef} className="min-h-0 flex-1 overflow-y-auto py-3">
                {isLoading && <p className="text-sm text-white/70">Loading messages...</p>}
                {error && <p className="mb-2 text-sm text-red-200">{error}</p>}
                {conversation?.messages?.map((message) => (
                    <ChatBubble
                        key={message.message_id}
                        text={message.message_text}
                        sender={message.sent_by}
                        timestamp={message.sent_at}
                    />
                ))}
                {waitingConversationId === activeConversation && (
                    <ChatBubble text="" sender="assistant" isLoading />
                )}
                {conversation?.recommendations?.length > 0 && (
                    <RecommendationCard
                        recommendation={
                            conversation.recommendations[conversation.recommendations.length - 1]
                        }
                        isAccepting={Boolean(acceptingRecommendationId)}
                        error={acceptError}
                        onAccept={handleAcceptRecommendation}
                    />
                )}
            </div>
            <ChatInput
                onSend={handleSendMessage}
                disabled={isLoading || !conversation || Boolean(waitingConversationId)}
            />
        </section>
    );
}
