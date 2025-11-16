# MedTainer MCP Server

This project is the FastAPI-based MCP (Modular Command Platform) server that will orchestrate MedTainer's cloud ecosystems (GoHighLevel, QuickBooks, Google Workspace, Amazon, Cloudflare, GoDaddy, etc.).

## Goals
- Provide a single API surface for AI agents to interact with business systems.
- Enforce auth, rate limits, and domain-specific rules per ecosystem.
- Ship as a Docker container so it can run locally or inside controlled infra.

## Getting Started
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Docker
```bash
docker build -t medtainer-mcp .
docker run -p 8000:8000 --env-file .env medtainer-mcp
```

## Configuration
Populate `.env` (see `.env.example`) with API keys and tenant IDs. Without credentials, each tool returns curated sample payloads so downstream agents can still see the expected schema.

## Project Phases (current progress)
1. **Docs & Knowledge Base** – AI-ready docs exist under `AI Projects/Docs/*`.  
2. **MCP Core Hardening** – FastAPI skeleton now includes logging, config, registry, and test scaffolding.  
3. **GoHighLevel Bundle** – Contact + pipeline digest tools registered with mock/sample data.  
4. **Finance & Workspace Bundles** – QuickBooks + Google Workspace tool bundles scaffolded.  
5. **Commerce & Infra Bundles** – Amazon + Cloudflare tool bundles scaffolded.  
6. **GoDaddy & Extras** – GoDaddy registrar/DNS bundle added to align DNS + email work.  
7. **Agent Q Layer (up next)** – Build orchestration + voice/CLI clients against `/mcp/tools` + `/mcp/run/{tool}` endpoints.

## Testing
```bash
pytest
```
