"""Logs each graph run and each node step through LangChain callbacks.

LangGraph tags every node run with metadata (`langgraph_step`,
`langgraph_node`, `langgraph_triggers`), so this handler works for any node
without changes to the node code. Pass it in the run config:

    graph.invoke(inputs, {"configurable": {...}, "callbacks": [GraphLoggingHandler()]})
"""

import logging
import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)


def _describe_update(outputs: Any) -> str:
    """Summarize a node's state update, e.g. 'messages(+1)'."""
    if not isinstance(outputs, dict):
        return type(outputs).__name__
    parts = []
    for key, value in outputs.items():
        if isinstance(value, list):
            parts.append(f"{key}(+{len(value)})")
        else:
            parts.append(key)
    return ", ".join(parts) or "nothing"


def _describe_state(state: Any) -> str:
    """Summarize state keys and sizes, e.g. 'messages=3'."""
    if not isinstance(state, dict):
        return type(state).__name__
    return ", ".join(
        f"{key}={len(value)}" if isinstance(value, list) else key
        for key, value in state.items()
    )


class GraphLoggingHandler(BaseCallbackHandler):
    def __init__(self) -> None:
        # run_id -> (kind, name, step, start time) for the runs we log.
        self._runs: dict[UUID, tuple[str, str, int | None, float]] = {}

    def on_chain_start(
        self,
        serialized: dict[str, Any] | None,
        inputs: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        metadata = metadata or {}
        name = kwargs.get("name") or "?"

        if parent_run_id is None:
            self._runs[run_id] = ("graph", name, None, time.perf_counter())
            messages = inputs.get("messages", []) if isinstance(inputs, dict) else []
            logger.info(
                "graph run started thread=%s input_messages=%d",
                metadata.get("thread_id"),
                len(messages),
            )
            return

        # Inner runnables inherit the node's metadata; only log the node run itself.
        if metadata.get("langgraph_node") != name:
            return
        step = metadata.get("langgraph_step")
        self._runs[run_id] = ("node", name, step, time.perf_counter())
        logger.info(
            "step %s -> node '%s' started (triggers=%s)",
            step,
            name,
            ", ".join(metadata.get("langgraph_triggers", ())),
        )
        logger.debug("node '%s' input state: %s", name, _describe_state(inputs))

    def on_chain_end(self, outputs: Any, *, run_id: UUID, **kwargs: Any) -> None:
        run = self._runs.pop(run_id, None)
        if run is None:
            return
        kind, name, step, start = run
        elapsed = time.perf_counter() - start
        if kind == "graph":
            logger.info("graph run finished in %.2fs", elapsed)
            logger.debug("final state: %s", _describe_state(outputs))
        else:
            logger.info(
                "node '%s' finished in %.2fs, wrote: %s",
                name,
                elapsed,
                _describe_update(outputs),
            )

    def on_chain_error(
        self, error: BaseException, *, run_id: UUID, **kwargs: Any
    ) -> None:
        run = self._runs.pop(run_id, None)
        if run is None:
            return
        kind, name, step, start = run
        elapsed = time.perf_counter() - start
        if kind == "graph":
            logger.error("graph run failed after %.2fs: %r", elapsed, error)
        else:
            logger.error(
                "step %s node '%s' failed after %.2fs: %r", step, name, elapsed, error
            )
