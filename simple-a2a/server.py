"""Run a minimal local A2A server for manual testing."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils.message import new_agent_text_message
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH, override=True)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SkillHandler = Callable[[str], str]


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Simple bearer-token auth guard for all server routes."""

    def __init__(self, app, api_key: str):
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request, call_next):
        auth_header = request.headers.get("Authorization")
        expected = f"Bearer {self.api_key}"
        if auth_header != expected:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        return await call_next(request)


@dataclass(slots=True)
class AgentConfig:
    agent_name: str = "Simple A2A Agent"


class SimpleAgentExecutor(AgentExecutor):
    """Deterministic demo executor with explicit skill dispatch."""

    def __init__(self) -> None:
        """
        Initialize the skill handler with a dictionary of available skills.

        The _skills dictionary maps skill names to their corresponding handler methods:
        - "summarize": Summarizes content using the _summarize method
        - "add": Performs addition using the _add method
        - "echo": Echoes input using the _echo method
        """
        self._skills: dict[str, SkillHandler] = {
            "summarize": self._summarize,
            "add": self._add,
            "echo": self._echo,
        }

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_text = context.get_user_input().strip()
        response = self._dispatch(context.metadata, user_text)

        await event_queue.enqueue_event(
            new_agent_text_message(
                text=response,
                context_id=context.context_id,
                task_id=context.task_id,
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancellation is not implemented for this demo server.")

    def _dispatch(self, metadata: dict[str, object], text: str) -> str:
        skill_id = metadata.get("skill_id")
        if not isinstance(skill_id, str) or not skill_id.strip():
            available = ", ".join(sorted(self._skills))
            return (
                "Missing request metadata 'skill_id'. "
                f"Choose one of: {available}."
            )

        handler = self._skills.get(skill_id.strip().lower())
        if handler is None:
            available = ", ".join(sorted(self._skills))
            return (
                f"Unknown skill_id '{skill_id}'. "
                f"Choose one of: {available}."
            )

        if not text:
            return "I did not receive any text input."

        return handler(text)

    def _summarize(self, text: str) -> str:
        payload = text.strip()
        if not payload:
            return "Provide text for summarize."
        return payload[:80] + ("..." if len(payload) > 80 else "")

    def _add(self, text: str) -> str:
        parts = text.split()
        if len(parts) != 2:
            return "Use add skill input: <int> <int>"

        try:
            left = int(parts[0])
            right = int(parts[1])
        except ValueError:
            return "Use add skill input: <int> <int>"

        return f"{left} + {right} = {left + right}"

    def _echo(self, text: str) -> str:
        return f"Echo: {text}"


def build_agent_card(base_url: str, config: AgentConfig) -> AgentCard:
    rpc_url = base_url.rstrip("/") + "/"
    return AgentCard(
        name=config.agent_name,
        description="Minimal A2A demo agent exposing summarize, add, and echo skills.",
        url=rpc_url,
        version="1.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="summarize",
                name="Summarize",
                description="Shortens input text to a brief summary preview.",
                tags=["demo", "a2a", "text"],
                examples=[
                    "Agent-to-Agent protocol allows standardized communication between assistants.",
                ],
            ),
            AgentSkill(
                id="add",
                name="Add",
                description="Adds two integers provided in the input text.",
                tags=["demo", "a2a", "math"],
                examples=["7 5"],
            ),
            AgentSkill(
                id="echo",
                name="Echo",
                description="Returns the input text unchanged except for an 'Echo:' prefix.",
                tags=["demo", "a2a", "text"],
                examples=["Hello there!"],
            ),
        ],
    )


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "21024"))
    api_key = os.getenv("REMOTE_AGENT_API_KEY")
    if not api_key:
        raise RuntimeError("Set REMOTE_AGENT_API_KEY before starting the server.")

    public_base_url = os.getenv("PUBLIC_BASE_URL", f"http://{host}:{port}")
    config = AgentConfig(agent_name=os.getenv("AGENT_NAME", "Simple A2A Agent"))

    request_handler = DefaultRequestHandler(
        agent_executor=SimpleAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    application = A2AStarletteApplication(
        agent_card=build_agent_card(public_base_url, config),
        http_handler=request_handler,
    )

    app = application.build()
    app.add_middleware(ApiKeyAuthMiddleware, api_key=api_key)

    logger.info("starting A2A server on %s:%s", host, port)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
