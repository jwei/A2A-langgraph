"""Run a minimal local A2A server for manual testing."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

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
    """Deterministic demo executor with summarize/add/echo behaviors."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_text = context.get_user_input().strip()
        response = self._handle(user_text)

        await event_queue.enqueue_event(
            new_agent_text_message(
                text=response,
                context_id=context.context_id,
                task_id=context.task_id,
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("Cancellation is not implemented for this demo server.")

    def _handle(self, text: str) -> str:
        if not text:
            return "I did not receive any text input."

        lowered = text.lower()
        if lowered.startswith("summarize "):
            payload = text[len("summarize ") :].strip()
            if not payload:
                return "Provide text after 'summarize'."
            return payload[:80] + ("..." if len(payload) > 80 else "")

        if lowered.startswith("add "):
            parts = text.split()
            if len(parts) == 3:
                try:
                    total = int(parts[1]) + int(parts[2])
                    return f"{parts[1]} + {parts[2]} = {total}"
                except ValueError:
                    return "Use: add <int> <int>"
            return "Use: add <int> <int>"

        return f"Echo: {text}"


def build_agent_card(base_url: str, config: AgentConfig) -> AgentCard:
    rpc_url = base_url.rstrip("/") + "/"
    return AgentCard(
        name=config.agent_name,
        description="Minimal A2A demo agent supporting summarize/add/echo text commands.",
        url=rpc_url,
        version="1.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="demo-tools",
                name="Demo Text Tools",
                description="Commands: 'summarize <text>', 'add <a> <b>', or free-form echo.",
                tags=["demo", "a2a", "text"],
                examples=[
                    "summarize This is a long message that should be shortened.",
                    "add 7 5",
                    "Hello there!",
                ],
            )
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