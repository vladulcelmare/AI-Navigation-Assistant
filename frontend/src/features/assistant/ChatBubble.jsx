function formatTimestamp(rawTimestamp) {
    if (!rawTimestamp) {
        return "";
    }

    const match = rawTimestamp
        .trim()
        .match(/^(\d{4})-(\d{2})-(\d{2})\s(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?$/);

    if (!match) {
        return rawTimestamp;
    }

    const [, year, month, day, hours, minutes, seconds, fraction = ""] = match;
    const milliseconds = Number((fraction + "000").slice(0, 3));
    const parsedDate = new Date(
        Number(year),
        Number(month) - 1,
        Number(day),
        Number(hours),
        Number(minutes),
        Number(seconds),
        milliseconds,
    );

    if (Number.isNaN(parsedDate.getTime())) {
        return rawTimestamp;
    }

    return new Intl.DateTimeFormat(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
    }).format(parsedDate);
}

export function ChatBubble({text, sender, timestamp, isLoading = false}) {
    const formattedTimestamp = formatTimestamp(timestamp);
    const loading_messages = [
        "Checking the map for the best turn",
        "Asking the route where it wants to go",
        "Calculating your snack-friendly detour",
        "Consulting the navigation gremlins",
        "Wait a second, that's not the north star",
        "Making sure the next turn is not dramatic",
    ];
    const idx = Math.floor(Math.random()*loading_messages.length)
    return (
        <div className={`pt-2.5 text-gray-900 font-lettera flex ${sender === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[45%] wrap-break-word p-3 pl-3 pr-3 rounded-xl text-sm font-normal text-left
            ${sender === "user" ? "bg-blue-200 rounded-br-none" :
                "bg-red-200 rounded-bl-none"}`
            }>
                {isLoading ? (
                    <div className="flex items-center gap-1.5" aria-label="Assistant is typing">
                        <div>{loading_messages[idx]} </div>
                        <span className="h-2 w-2 animate-bounce rounded-full bg-gray-600 [animation-delay:0ms]" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-gray-600 [animation-delay:120ms]" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-gray-600 [animation-delay:240ms]" />
                    </div>
                ) : (
                    text
                )}
                {formattedTimestamp && (
                    <div className="mt-1 text-right text-[10px] leading-none text-gray-500">
                        {formattedTimestamp}
                    </div>
                )}
            </div>
        </div>
    );
}