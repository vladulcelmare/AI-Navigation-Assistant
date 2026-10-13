from backend.integrations.openai_client import LLM_Agent


def main():
    agent = LLM_Agent()
    context = ""

    while True:
        user_query = input("You: ").strip()

        if user_query.lower() in {"exit", "quit"}:
            break

        if not user_query:
            continue

        response = agent.generate_response(user_query, context)
        print(f"Assistant: {response}")

        context = f"{context}\nUser: {user_query}\nAssistant: {response}".strip()


if __name__ == "__main__":
    main()
