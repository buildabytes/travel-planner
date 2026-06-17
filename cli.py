import asyncio
from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.apps.app import App
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)

from agent import root_agent

import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=UserWarning)
load_dotenv()  # loads .env into os.environ

# Suppress ADK experimental warnings
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module=r"google\.adk\..*"
)

# Optional: suppress only function_call concatenation warnings
warnings.filterwarnings(
    "ignore",
    message=r".*non-text parts in the response.*"
)


# Task 9: Connect CLI with Root Agent
async def run_cli():
    """Run an interactive command-line chat agent the root_agent."""
    # 1. In-memory services for artifacts, sessions, and credentials.
    artifact_service = InMemoryArtifactService()
    session_service = InMemorySessionService()
    credential_service = InMemoryCredentialService()

    # 2. A session for the TravelPlanner app, tied to a user id.
    session = await session_service.create_session(
        app_name="TravelPlanner", user_id="user_1"
    )

    # 3. The App, rooted at our root_agent.
    app = App(name="TravelPlanner", root_agent=root_agent)

    runner = Runner(
        app=app,
        artifact_service=artifact_service,
        session_service=session_service,
        credential_service=credential_service,
    )

    # 5. Welcome message.
    print("Welcome to the Travel Planner CLI!")
    print("Type your travel request, or 'exit' / 'quit' to leave. \n")

    try:
        # 6. Read user inout, send it to the agent, stream the response.
        while True:
            user_input = input("You: ").strip()

            # 7. Stop on exit/quit
            if user_input.lower() in ("exit", "quit"):
                print("Goodbye! Safe travels.")
                break

            if not user_input:
                continue

            content = types.Content(
                role="user", parts=[types.Part(text=user_input)]
            )
            agen = runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=content,
            )

            async for event in agen:
                if event.content and event.content.parts:
                    text = "".join(
                        part.text for part in event.content.parts if part.text
                    )
                    if text:
                        print(f"[{event.author}]: {text}")
    finally:
        # 8. Always close the runner.
        await runner.close()


if __name__ == "__main__":
    asyncio.run(run_cli())
