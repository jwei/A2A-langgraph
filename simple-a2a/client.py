#!/usr/bin/env python3
"""Simple A2A client for local testing, including agent card verification."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import httpx
from a2a.client import ClientConfig, ClientFactory, create_text_message_object
from a2a.types import Message, Task
from a2a.utils.message import get_message_text
from dotenv import load_dotenv

ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH, override=True)


def extract_text(event: Message | tuple[Task, Any]) -> str:
    if isinstance(event, Message):
        return get_message_text(event)

    task, _update = event
    if task.artifacts:
        latest_artifact = task.artifacts[-1]
        return "\n".join(
            part.root.text
            for part in latest_artifact.parts
            if hasattr(part.root, "text")
        )
    if task.history:
        return get_message_text(task.history[-1])
    return ""


async def fetch_agent_card(base_url: str, headers: dict[str, str]) -> dict[str, Any]:
    card_url = base_url.rstrip("/") + "/.well-known/agent-card.json"
    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        response = await client.get(card_url)
        response.raise_for_status()
        return response.json()


async def send_text(a2a_client: Any, text: str) -> str:
    message = create_text_message_object(content=text)
    latest_text = ""

    async for event in a2a_client.send_message(message):
        latest_text = extract_text(event)

    return latest_text


async def main() -> None:
    server_url = os.getenv("AGENT_URL", "http://127.0.0.1:21024")
    api_key = os.getenv("REMOTE_AGENT_API_KEY")
    if not api_key:
        raise RuntimeError("Set REMOTE_AGENT_API_KEY before running the client.")

    auth_headers = {"Authorization": f"Bearer {api_key}"}

    print("1) Testing agent card discovery...")
    card = await fetch_agent_card(server_url, auth_headers)
    print(f"   Name: {card.get('name', 'N/A')}")
    print(f"   Description: {card.get('description', 'N/A')}")
    print(f"   RPC URL: {card.get('url', 'N/A')}")
    print(f"   Skills: {len(card.get('skills', []))}")
    print()

    print("2) Testing A2A message/send...")
    async with httpx.AsyncClient(timeout=20.0, headers=auth_headers) as http_client:
        client_config = ClientConfig(
            streaming=False,
            polling=False,
            httpx_client=http_client,
        )
        a2a_client = await ClientFactory.connect(
            server_url,
            client_config=client_config,
            relative_card_path="/.well-known/agent-card.json",
            resolver_http_kwargs={"headers": auth_headers},
        )

        tests = [
            "summarize Agent-to-Agent protocol allows standardized communication between assistants.",
            "add 7 5",
            "Hello from the client test.",
        ]

        for idx, text in enumerate(tests, start=1):
            response = await send_text(a2a_client, text)
            print(f"   Test {idx} input: {text}")
            print(f"   Test {idx} output: {response}")
            print()


if __name__ == "__main__":
    asyncio.run(main())