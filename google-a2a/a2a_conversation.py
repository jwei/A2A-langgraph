#!/usr/bin/env python3
"""Conversation runner using the standard Google A2A Python SDK client."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any

from a2a.client import ClientConfig, ClientFactory, create_text_message_object
from a2a.types import Message, Task
from a2a.utils.message import get_message_text
from dotenv import load_dotenv

load_dotenv(override=True)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class ConversationTarget:
    name: str
    url: str
    context_id: str | None = None
    task_id: str | None = None


def extract_text(event: Message | tuple[Task, Any]) -> tuple[str, str | None, str | None]:
    if isinstance(event, Message):
        return get_message_text(event), event.context_id, event.task_id

    task, _update = event
    if task.artifacts:
        latest_artifact = task.artifacts[-1]
        text = "\n".join(
            part.root.text
            for part in latest_artifact.parts
            if hasattr(part.root, "text")
        )
    elif task.history:
        text = get_message_text(task.history[-1])
    else:
        text = ""

    return text, task.context_id, task.id


async def send_text(client: Any, target: ConversationTarget, text: str) -> str:
    message = create_text_message_object(content=text)
    message.context_id = target.context_id
    message.task_id = target.task_id

    logger.info(
        "sending target=%s url=%s context_id=%s task_id=%s text=%r",
        target.name,
        target.url,
        target.context_id,
        target.task_id,
        text,
    )

    latest_text = ""
    async for event in client.send_message(message):
        latest_text, context_id, task_id = extract_text(event)
        target.context_id = context_id or target.context_id
        target.task_id = task_id or target.task_id
        logger.info(
            "received target=%s context_id=%s task_id=%s text=%r",
            target.name,
            target.context_id,
            target.task_id,
            latest_text,
        )

    return latest_text


async def main() -> None:
    rounds = int(os.getenv("ROUNDS", "3"))
    message = os.getenv("INITIAL_MESSAGE", "Hello! Let's have a conversation.")

    target_a = ConversationTarget(
        name="Agent A",
        url=os.getenv("AGENT_A_URL", "http://127.0.0.1:21024"),
    )
    target_b = ConversationTarget(
        name="Agent B",
        url=os.getenv("AGENT_B_URL", "http://127.0.0.1:21025"),
    )

    client_config = ClientConfig(streaming=False, polling=False)
    client_a = await ClientFactory.connect(
        target_a.url,
        client_config=client_config,
        relative_card_path="/.well-known/agent-card.json",
    )
    client_b = await ClientFactory.connect(
        target_b.url,
        client_config=client_config,
        relative_card_path="/.well-known/agent-card.json",
    )

    for round_index in range(rounds):
        print(f"--- Round {round_index + 1} ---")

        message = await send_text(client_a, target_a, message)
        print(f"🔵 {target_a.name}: {message}")

        message = await send_text(client_b, target_b, message)
        print(f"🔴 {target_b.name}: {message}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
