# Google A2A Python SDK Example

This folder rewrites the Python example using the standard A2A Python SDK from the A2A project instead of LangGraph's built-in A2A endpoint.

## What is in this folder

- `agent_server.py`: Starts a real A2A server with `A2AStarletteApplication`
- `agent_executor.py`: Contains the agent logic by implementing `AgentExecutor`
- `a2a_conversation.py`: Uses the SDK client to send messages between two running agents
- `requirements.txt`: Python dependencies for this implementation
- `.env.example`: Example environment variables

## Architecture

The flow is intentionally explicit:

1. `agent_server.py` builds an `AgentCard` and wires `ChatAgentExecutor` into `DefaultRequestHandler`.
2. The A2A SDK exposes:
   - `/.well-known/agent-card.json` for discovery
   - `/` for A2A JSON-RPC requests
3. `a2a_conversation.py` resolves each agent card, creates SDK clients, then sends `Message` objects with `context_id` and `task_id`.
4. `ChatAgentExecutor.execute()` reads the incoming text from `RequestContext`, calls OpenAI, and enqueues an A2A `Message` reply.

That separation is the main difference from the `python/` folder:

- `python/`: LangGraph graph + handwritten A2A JSON-RPC call
- `google-a2a/`: standard A2A SDK server + standard A2A SDK client

## Setup

Python 3.10+ is required. On this machine, `a2a-sdk` installed successfully with Python 3.11.

1. Create and activate a virtual environment:

```bash
cd google-a2a
/opt/homebrew/bin/python3.11 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create environment files for two agents:

```bash
cp .env.example .env.agent-a
cp .env.example .env.agent-b
```

4. Edit both files:

- In `.env.agent-a`, keep `PORT=21024`, `PUBLIC_BASE_URL=http://127.0.0.1:21024`, and set `AGENT_NAME=Agent A`
- In `.env.agent-b`, change to `PORT=21025`, `PUBLIC_BASE_URL=http://127.0.0.1:21025`, and set `AGENT_NAME=Agent B`
- Set `OPENAI_API_KEY` in both files
- Optionally customize `AGENT_PROMPT` for each agent

## Run the servers

Terminal 1:

```bash
cd google-a2a
set -a
source .env.agent-a
set +a
python agent_server.py
```

Terminal 2:

```bash
cd google-a2a
set -a
source .env.agent-b
set +a
python agent_server.py
```

## Verify the servers

Check agent discovery:

```bash
curl -s http://127.0.0.1:21024/.well-known/agent-card.json
curl -s http://127.0.0.1:21025/.well-known/agent-card.json
```

You should see each agent's `name`, `url`, `skills`, and `capabilities`.

## Run the conversation

Use a third terminal:

```bash
cd google-a2a
set -a
source .env.agent-a
set +a
python a2a_conversation.py
```

The conversation script reads:

- `AGENT_A_URL`
- `AGENT_B_URL`
- `INITIAL_MESSAGE`
- `ROUNDS`

These values are already present in `.env.example`.

## Debugging guide

### 1. Confirm agent discovery works

If the client cannot connect, check:

```bash
curl -i http://127.0.0.1:21024/.well-known/agent-card.json
```

If this fails, the server is not running or `PUBLIC_BASE_URL` / `PORT` is wrong.

### 2. Turn on verbose logs

Set:

```bash
LOG_LEVEL=DEBUG
```

You will then see:

- incoming user text
- assigned `context_id`
- assigned `task_id`
- outgoing reply text

### 3. Understand state ownership

- The A2A SDK owns the transport, request handling, and task store
- `ChatAgentExecutor` owns only the agent behavior
- This demo also keeps a local in-memory history dictionary per `context_id`

That means:

- restart the server and the local history is gone
- restart the server and `InMemoryTaskStore` is also cleared

### 4. Understand `context_id` vs `task_id`

- `context_id`: the conversation identity
- `task_id`: the current task identity on that agent

`a2a_conversation.py` preserves both per remote agent so follow-up turns stay attached to the same conversation.

## Key code paths

- Agent entrypoint: `agent_server.py`
- Agent execution: `agent_executor.py`
- SDK client orchestration: `a2a_conversation.py`

## References

- A2A Python SDK docs: https://a2a-protocol.org/latest/sdk/python/
- A2A Python quickstart: https://a2a-protocol.org/latest/tutorials/python/1-introduction/
- A2A Python server setup: https://a2a-protocol.org/v0.2.5/tutorials/python/5-start-server/
