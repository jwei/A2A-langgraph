"""Agent logic for the Google A2A SDK example."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils.message import new_agent_text_message
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AgentConfig:
    """Runtime configuration for a single A2A agent process."""

    agent_name: str
    system_prompt: str
    model: str = "gpt-4o-mini"
    max_tokens: int = 100
    temperature: float = 0.7


class ChatAgentExecutor(AgentExecutor):
    """Minimal A2A executor that replies with OpenAI text responses.

    The executor keeps lightweight in-memory history per `context_id` to make
    the flow easy to inspect while debugging. This is separate from the SDK's
    task store and exists only to keep the example explicit.
    """

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._history: dict[str, list[dict[str, str]]] = {}
        self._lock = asyncio.Lock()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_text = context.get_user_input().strip()
        context_id = context.context_id or "unknown-context"
        task_id = context.task_id

        logger.info(
            "execute agent=%s context_id=%s task_id=%s user_text=%r",
            self.config.agent_name,
            context_id,
            task_id,
            user_text,
        )

        if not user_text:
            reply_text = "I did not receive any text input."
        else:
            reply_text = await self._generate_reply(context_id, user_text)

        await event_queue.enqueue_event(
            new_agent_text_message(
                text=reply_text,
                context_id=context_id,
                task_id=task_id,
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        logger.info(
            "cancel requested for agent=%s task_id=%s",
            self.config.agent_name,
            context.task_id,
        )
        raise NotImplementedError("This demo agent does not support cancellation.")

    async def _generate_reply(self, context_id: str, user_text: str) -> str:
        async with self._lock:
            history = self._history.setdefault(context_id, [])
            history.append({"role": "user", "content": user_text})

            openai_messages = [
                {"role": "system", "content": self.config.system_prompt},
                *history,
            ]

        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=openai_messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )
            reply_text = response.choices[0].message.content or ""
        except Exception as exc:
            logger.exception("OpenAI request failed")
            reply_text = (
                "I received your message but could not process it. "
                f"Error: {str(exc)[:120]}"
            )

        async with self._lock:
            self._history.setdefault(context_id, []).append(
                {"role": "assistant", "content": reply_text}
            )

        return reply_text
