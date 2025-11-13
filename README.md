# Agent-to-Agent (A2A) Conversation with LangGraph

This project demonstrates Agent-to-Agent (A2A) conversations using LangGraph with the A2A protocol. It includes implementations in both **Python** and **TypeScript**, allowing you to explore A2A communication patterns across different language ecosystems.

## Overview

The project showcases how two conversational AI agents can communicate with each other using the standardized A2A protocol. Each agent:
- Uses OpenAI's GPT-4o-mini for generating responses
- Maintains independent conversation state
- Communicates via JSON-RPC 2.0 formatted messages
- Responds to messages from other agents in a conversational loop

## Project Structure

```
agent2agent/
├── python/                    # Python implementation
│   ├── langgraph_agent.py     # Agent definition
│   ├── a2a_conversation.py   # Conversation orchestrator
│   ├── langgraph.json         # LangGraph configuration
│   ├── requirements.txt       # Python dependencies
│   └── README.md              # Python-specific docs
│
├── typescript/                 # TypeScript implementation
│   ├── src/
│   │   ├── langgraph_agent.ts      # Agent definition
│   │   └── a2a_conversation.ts     # Conversation orchestrator
│   ├── langgraph.json              # LangGraph configuration
│   ├── package.json                # Node.js dependencies
│   ├── tsconfig.json               # TypeScript configuration
│   └── README.md                   # TypeScript-specific docs
│
└── README.md                  # This file
```

## Quick Start

### Python Implementation

1. **Setup:**
   ```bash
   cd python
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Add your OPENAI_API_KEY to .env
   ```

3. **Run agents:**
   ```bash
   # Terminal 1
   langgraph dev --port 2024
   
   # Terminal 2
   langgraph dev --port 2025
   ```

4. **Run conversation:**
   ```bash
   python a2a_conversation.py
   ```

See [python/README.md](python/README.md) for detailed Python setup instructions.

### TypeScript Implementation

1. **Setup:**
   ```bash
   cd typescript
   npm install
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Add your OPENAI_API_KEY to .env
   ```

3. **Run agents:**
   ```bash
   # Terminal 1
   npx @langchain/langgraph-cli dev --port 2024
   
   # Terminal 2
   npx @langchain/langgraph-cli dev --port 2025
   ```

4. **Run conversation:**
   ```bash
   npm run conversation
   ```

See [typescript/README.md](typescript/README.md) for detailed TypeScript setup instructions.

## Important Notes

### A2A Protocol Support

- **Python**: The local dev server (`langgraph dev`) fully supports A2A protocol endpoints at `/a2a/{assistant_id}`
- **TypeScript**: 
  - A2A protocol is **supported on LangGraph Cloud deployments**
  - The local dev server (`langgraph dev`) does **not** expose A2A endpoints
  - For local TypeScript development, use the Threads API instead

### Environment Variables

Both implementations require:
- `OPENAI_API_KEY`: Your OpenAI API key
- `AGENT_A_ID`: Assistant ID from the first server (port 2024)
- `AGENT_B_ID`: Assistant ID from the second server (port 2025)

## Architecture

### Agent Definition

Both implementations define a conversational agent using LangGraph's `StateGraph`:
- **State**: Maintains a list of messages using LangChain's `BaseMessage` types
- **Node**: Processes messages using OpenAI's GPT-4o-mini
- **Configuration**: Brief responses (max 100 tokens), temperature 0.7

### A2A Conversation Orchestrator

The orchestrator:
- Sends JSON-RPC 2.0 formatted messages between agents
- Uses the A2A protocol endpoint: `/a2a/{assistant_id}`
- Implements the `message/send` method
- Extracts responses from the `artifacts` array
- Simulates 3 rounds of back-and-forth conversation

## API Documentation

### Python
- Swagger UI: `http://localhost:2024/docs` or `http://localhost:2025/docs`
- LangGraph Studio: Available via the server output

### TypeScript
- LangGraph Studio: Available via the server output (e.g., `https://smith.langchain.com/studio?baseUrl=http://localhost:2025`)
- Note: `/docs` endpoint is not available in TypeScript dev server

## Differences Between Implementations

| Feature | Python | TypeScript |
|---------|--------|------------|
| A2A Local Dev | ✅ Supported | ❌ Not available (use Cloud) |
| A2A Cloud | ✅ Supported | ✅ Supported |
| Threads API | ✅ Available | ✅ Available |
| Swagger Docs | ✅ `/docs` endpoint | ❌ Use Studio UI |
| State Definition | Dataclass | Annotation API |

## Development

### Python Scripts
- Run conversation: `python a2a_conversation.py`

### TypeScript Scripts
- `npm run dev` - Watch mode for development
- `npm run build` - Build TypeScript to JavaScript
- `npm run conversation` - Run the A2A conversation simulation

## License

See [LICENSE](LICENSE) for details.

