# Agent Skills installed in this project

This project uses **LangChain Skills**: instruction packs that help coding agents
(Claude Code and others) write correct, up-to-date code with LangChain, LangGraph and Deep Agents.

A skill is a folder with a `SKILL.md` file, plus optional reference docs or scripts.
Each skill has a short description. The agent reads the descriptions and loads a skill's
full instructions only when the current task matches it. For example, when writing a
`StateGraph`, the agent loads `langgraph-fundamentals`.

## Source

| | |
|---|---|
| GitHub project | [langchain-ai/langchain-skills](https://github.com/langchain-ai/langchain-skills) (official, maintained by LangChain) |
| Path in the repo | `config/skills/<skill-name>/` |
| Announcement | [LangChain Skills (LangChain blog)](https://www.langchain.com/blog/langchain-skills) |
| Installer | [`skills` CLI](https://github.com/vercel-labs/skills) (run through `npx`) |
| Status | Early development; skill content and APIs may change |

## How it was installed

From the `agent-orchestrator/` directory:

```bash
npx skills add langchain-ai/langchain-skills --skill '*' --yes
```

- `--skill '*'` installs every skill in the repo.
- `--yes` skips the confirmation prompts.
- No `--global`, so the install is **project-scoped**: nothing is written to `~/.claude`.
- No `--agent`, so the installer set the skills up for every supported agent, not just Claude Code.

## What was written to disk

```
agent-orchestrator/
├── .agents/skills/<skill-name>/     # the real files (22 skills, ~700 KB), shared by all agents
├── .claude/skills/<skill-name>  ->  ../../.agents/skills/<skill-name>   # symlinks for Claude Code
└── skills-lock.json                 # source repo, path and content hash for each skill
```

`skills-lock.json` records where each skill came from, so the same set can be
reinstalled or checked for changes later.

Most skills contain only Markdown. Two of them also ship code:
`swarm` (TypeScript scripts) and `eval-engineering` (Python helper scripts and templates).
Skills run with the agent's full permissions, so review them before relying on them.

## Skills installed

### Most relevant to this project (Python + LangGraph orchestrator)

| Skill | What it covers |
|---|---|
| `ecosystem-primer` | Starting point: when to pick LangChain, LangGraph or Deep Agents; install and env setup; which skill to load next |
| `langchain-dependencies` | Required packages, minimum versions and dependency management (Python and TS) |
| `langgraph-python-quickstart` | Scaffolds a minimal local LangGraph agent in Python, following the official quickstart |
| `langgraph-fundamentals` | `StateGraph`, state schemas, nodes, edges, `Command`, `Send`, `invoke`, streaming, error handling (includes a `references/python.md`) |
| `langgraph-persistence` | Checkpointers, `thread_id`, conversation memory, time travel, `Store`, subgraph persistence |
| `langgraph-human-in-the-loop` | `interrupt()`, `Command(resume=...)`, approval and validation flows, error-handling strategy |
| `langgraph-decision-models` | Routing a graph with a dedicated decision model instead of a full LLM call; auditing LLM calls that only make routing decisions |

### LangGraph tooling

| Skill | What it covers |
|---|---|
| `langgraph-cli` | `langgraph new / dev / build / up / deploy` and `langgraph.json` |
| `langgraph-typescript-quickstart` | The same quickstart, in TypeScript |

### LangChain (higher-level agent API built on LangGraph)

| Skill | What it covers |
|---|---|
| `langchain-fundamentals` | `create_agent`, defining tools, middleware basics |
| `langchain-middleware` | `HumanInTheLoopMiddleware`, custom middleware hooks, structured output (Pydantic/Zod) |
| `langchain-rag` | Document loaders, text splitters, embeddings, vector stores (Chroma, FAISS, Pinecone) |
| `langchain-python-quickstart` | Scaffolds a minimal LangChain agent in Python |
| `langchain-typescript-quickstart` | Scaffolds a minimal LangChain agent in TypeScript |

### Deep Agents (LangChain's ready-made agent harness)

| Skill | What it covers |
|---|---|
| `deep-agents-core` | `create_deep_agent()`, harness architecture, configuration |
| `deep-agents-memory` | State/Store/Filesystem backends for memory and files |
| `deep-agents-orchestration` | Subagents, todo-list planning, human approval |
| `deepagents-python-quickstart` | Minimal Deep Agent in Python |
| `deepagents-typescript-quickstart` | Minimal Deep Agent in TypeScript |
| `managed-deep-agents` | Building and deploying Managed Deep Agents on LangSmith (`mda` CLI) |

### Utilities

| Skill | What it covers |
|---|---|
| `eval-engineering` | Designing agent evaluations and benchmarks with the Harbor framework (needs Docker or a cloud environment) |
| `swarm` | Runs many independent tasks in parallel through subagents, then combines the results (needs a specific JS code-interpreter tool) |

## Requirements

- `OPENAI_API_KEY` (this project uses the OpenAI APIs) or `ANTHROPIC_API_KEY`
- Claude Code loads new skills only at session start, so restart it after installing or updating.

## Updating or removing

- **Update:** rerun the install command above. It overwrites the skills, and `skills-lock.json` is refreshed.
- **Remove:** delete `.agents/skills/`, `.claude/skills/` and `skills-lock.json`.
