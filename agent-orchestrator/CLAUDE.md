# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A study project for learning **LangGraph**: a chat app with a LangGraph workflow, an OpenAI model, and a Streamlit UI. LangGraph is the topic being studied; Streamlit is only the front end. Version 2 routes each turn: `START -> classify -> {clarify | greet | plato | homer | unsupported} -> END`.

## Commands

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then set OPENAI_API_KEY (OPENAI_MODEL, LOG_LEVEL optional)
streamlit run app.py          # http://localhost:8501; logs go to this terminal
```

No test suite, linter, or formatter is configured. To exercise the graph without the UI:

```bash
python -c "from langchain_core.messages import HumanMessage; from orchestrator.graph import build_graph; from orchestrator.logging_config import setup_logging; from orchestrator.tracing import GraphLoggingHandler; setup_logging(); g = build_graph(); print(g.invoke({'messages': [HumanMessage('hi')]}, {'configurable': {'thread_id': 't1'}, 'callbacks': [GraphLoggingHandler()]})['messages'][-1].content)"
```

Optional LangSmith tracing: set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` in `.env`.

## Architecture

- `orchestrator/graph.py` — `build_graph()` builds and compiles a `StateGraph(State)` with an `InMemorySaver` checkpointer. `State` extends `MessagesState` with an `intent` field (no reducer, overwritten each turn). `classify` uses `llm.with_structured_output(Route)` over the full history and writes only `intent`; `route_intent` maps it to a node name for `add_conditional_edges` (`philosophy -> plato`, `literature -> homer`). `clarify`/`greet`/`plato`/`homer` share a `reply()` helper with per-node system prompts; `unsupported` returns a fixed `AIMessage` without an LLM call. Nodes are closures over the `ChatOpenAI` client and return only the *new* messages (the `MessagesState` reducer appends). System prompts are prepended on each LLM call and never stored in state.
- `app.py` — Streamlit reruns the whole script on every interaction, so:
  - the compiled graph is cached with `@st.cache_resource` (one per server process). That single `InMemorySaver` holds every conversation, keyed by `thread_id`.
  - `thread_id` lives in `st.session_state`; "New conversation" just generates a new UUID.
  - the **checkpointer is the source of truth** for chat history: the UI reads `graph.get_state(config)` to render messages and keeps no message list of its own. History is lost when the server stops.
- `orchestrator/tracing.py` — `GraphLoggingHandler` is a LangChain callback handler passed in the run config (`"callbacks": [...]`). It logs graph runs and node steps using the metadata LangGraph attaches (`langgraph_step`, `langgraph_node`, `langgraph_triggers`), so new nodes are logged without changes to node code.
- `orchestrator/logging_config.py` — `setup_logging()` runs once per process (guarded against Streamlit reruns). Root logger is at WARNING so third-party libs stay quiet; only loggers listed in `PROJECT_LOGGERS` (`orchestrator`, `app`) use `LOG_LEVEL`. A new top-level package needs to be added there to get its logs. `app.py` uses the explicit logger name `"app"` because `__name__` is `"__main__"` under Streamlit.
- `orchestrator/config.py` — `get_settings()` loads `.env` and raises `ConfigError` if `OPENAI_API_KEY` is missing or still the placeholder; `app.py` shows that error in the UI. Never log the API key.

The README documents the graph diagram, logging behavior, and an example log of one chat turn. Keep it in sync when the graph or logging changes.

## Agent skills

LangChain/LangGraph skills are installed project-scoped in `.agents/skills/` (symlinked from `.claude/skills/`, tracked by `skills-lock.json`); see `docs/skills.md`. For LangGraph work, the most relevant ones are `langgraph-fundamentals`, `langgraph-persistence`, and `langgraph-human-in-the-loop`. Reinstall/update with `npx skills add langchain-ai/langchain-skills --skill '*' --yes`.
