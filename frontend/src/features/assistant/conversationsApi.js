import {apiClient, getApiError} from "../../lib/apiClient.js";

async function ensureSuccessful(response, fallback) {
    if (!response.ok) {
        throw new Error(await getApiError(response, fallback));
    }
}

export async function getConversations(signal) {
    const response = await apiClient("/users/me/conversations", {signal});
    await ensureSuccessful(response, "Unable to load conversations");
    const data = await response.json();
    return data.conversations || [];
}

export async function createConversation(title) {
    const response = await apiClient("/users/me/conversations", {
        method: "POST",
        body: JSON.stringify({title}),
    });
    await ensureSuccessful(response, "Unable to create conversation");
    return response.json();
}

export async function deleteConversation(conversationId) {
    const response = await apiClient(`/users/me/conversations/${conversationId}`, {
        method: "DELETE",
    });
    await ensureSuccessful(response, "Unable to delete conversation");
}

export async function getConversation(conversationId, signal) {
    const response = await apiClient(`/users/me/conversations/${conversationId}`, {signal});
    await ensureSuccessful(response, "Unable to load conversation");
    return response.json();
}

export async function sendConversationMessage(conversationId, payload) {
    const response = await apiClient(`/users/me/conversations/${conversationId}/messages`, {
        method: "POST",
        body: JSON.stringify(payload),
    });
    await ensureSuccessful(response, "Unable to send message");
    return response.json();
}

export async function acceptConversationRecommendation(
    conversationId,
    recommendationId,
    payload,
) {
    const response = await apiClient(
        `/users/me/conversations/${conversationId}/recommendations/${recommendationId}/accept`,
        {
            method: "POST",
            body: JSON.stringify(payload),
        },
    );
    await ensureSuccessful(response, "Unable to accept route");
    return response.json();
}
