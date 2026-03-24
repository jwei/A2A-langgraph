"""Run a local A2A server using the standard Google A2A Python SDK."""

from __future__ import annotations

import logging
import os

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from dotenv import load_dotenv

from agent_executor import AgentConfig, ChatAgentExecutor

load_dotenv(override=True)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def build_agent_card(base_url: str, config: AgentConfig) -> AgentCard:
    rpc_url = base_url.rstrip("/") + "/"
    return AgentCard(
        name=config.agent_name,
        description=os.getenv(
            "AGENT_DESCRIPTION",
            "Conversational A2A agent built with the standard Google A2A SDK.",
        ),
        url=rpc_url,
        version="1.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id=os.getenv("AGENT_SKILL_ID", "conversation"),
                name=os.getenv("AGENT_SKILL_NAME", "Conversation"),
                description=(
                    "Holds short text conversations and responds to another agent."
                ),
                tags=["conversation", "demo", "a2a"],
                examples=["Hello! Let's have a conversation."],
            )
        ],
    )


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "21024"))
    public_base_url = os.getenv("PUBLIC_BASE_URL", f"http://{host}:{port}")

    config = AgentConfig(
        agent_name=os.getenv("AGENT_NAME", "Google A2A Agent"),
        system_prompt=os.getenv(
            "AGENT_PROMPT",
            "You are a helpful conversational agent. Keep responses brief and engaging.",
        ),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "100")),
        temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
    )

    agent_card = build_agent_card(public_base_url, config)
    request_handler = DefaultRequestHandler(
        agent_executor=ChatAgentExecutor(config),
        task_store=InMemoryTaskStore(),
    )
    application = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )

    logging.getLogger(__name__).info(
        "starting agent name=%s host=%s port=%s public_base_url=%s",
        config.agent_name,
        host,
        port,
        public_base_url,
    )
    uvicorn.run(application.build(), host=host, port=port)


if __name__ == "__main__":
    main()
