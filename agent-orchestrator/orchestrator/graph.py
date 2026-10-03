"""LangGraph definition: a classifier routes each turn to one answer node.

    START -> classify -> clarify     -> END
                      -> greet       -> END
                      -> plato       -> END
                      -> homer       -> END
                      -> unsupported -> END

`classify` writes `intent` to state; a conditional edge reads it to pick the
next node. Conversation memory is kept by the checkpointer, keyed by `thread_id`.
"""

import logging
import time
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel, Field

from orchestrator.config import Settings, get_settings

logger = logging.getLogger(__name__)

Intent = Literal["clarify", "greet", "philosophy", "literature", "unsupported"]

CLASSIFIER_PROMPT = """\
Classify what the user wants in their latest message, using the earlier \
conversation as context (e.g. "tell me more" continues the previous topic).

- greet: the user is only greeting (hello, hi, good morning) with no other request.
- philosophy: the user wants to talk about philosophy.
- literature: the user wants to talk about literature or poetry.
- unsupported: the request is clear but about any other subject.
- clarify: the message is unclear and you can't tell what the user wants."""

CLARIFY_PROMPT = (
    "You could not understand what the user wants. Say so briefly and ask one short "
    "clarifying question. Mention that you can talk about philosophy (as Plato) or "
    "literature and poetry (as Homer)."
)
GREET_PROMPT = (
    "The user is greeting you. Greet them back briefly and offer to talk about "
    "philosophy with Plato or literature and poetry with Homer."
)
PLATO_PROMPT = (
    "You are Plato, the Athenian philosopher. Answer in the first person, in a "
    "Socratic style with questions and dialogue, drawing on your works and ideas."
)
HOMER_PROMPT = (
    "You are Homer, the epic poet of the Iliad and the Odyssey. Answer in the first "
    "person, in an epic, bardic voice, about literature and poetry."
)
UNSUPPORTED_REPLY = (
    "Sorry, this system can't help with that subject. I can talk about philosophy "
    "(as Plato) or literature and poetry (as Homer)."
)


class State(MessagesState):
    # No reducer: each turn's classification overwrites the previous one.
    intent: Intent


class Route(BaseModel):
    intent: Intent
    reason: str = Field(description="One short sentence explaining the choice.")


def route_intent(state: State) -> Literal["clarify", "greet", "plato", "homer", "unsupported"]:
    intent = state["intent"]
    if intent == "philosophy":
        return "plato"
    if intent == "literature":
        return "homer"
    return intent


def build_graph(settings: Settings | None = None):
    settings = settings or get_settings()
    logger.info("building graph model=%s", settings.openai_model)

    llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)
    classifier = llm.with_structured_output(Route)

    def classify(state: State) -> dict:
        last = state["messages"][-1]
        logger.info("user message: %s", last.content)
        route = classifier.invoke([SystemMessage(CLASSIFIER_PROMPT), *state["messages"]])
        logger.info("intent=%s reason: %s", route.intent, route.reason)
        # Only the routing decision is written; no message is added.
        return {"intent": route.intent}

    def reply(state: State, system_prompt: str) -> dict:
        # The system prompt is added on each call and is not stored in state.
        messages = [SystemMessage(system_prompt), *state["messages"]]
        logger.debug("calling LLM with %d messages (history + system prompt)", len(messages))

        start = time.perf_counter()
        response = llm.invoke(messages)
        elapsed = time.perf_counter() - start

        logger.info("assistant reply: %s", response.content)
        usage = response.usage_metadata or {}
        logger.info(
            "LLM responded in %.2fs tokens in=%s out=%s total=%s",
            elapsed,
            usage.get("input_tokens"),
            usage.get("output_tokens"),
            usage.get("total_tokens"),
        )
        # MessagesState appends, so return only the new message.
        return {"messages": [response]}

    def unsupported(state: State) -> dict:
        # A fixed reply: nodes don't have to call an LLM.
        logger.info("assistant reply: %s", UNSUPPORTED_REPLY)
        return {"messages": [AIMessage(UNSUPPORTED_REPLY)]}

    answer_nodes = {
        "clarify": lambda state: reply(state, CLARIFY_PROMPT),
        "greet": lambda state: reply(state, GREET_PROMPT),
        "plato": lambda state: reply(state, PLATO_PROMPT),
        "homer": lambda state: reply(state, HOMER_PROMPT),
        "unsupported": unsupported,
    }

    builder = StateGraph(State)
    builder.add_node("classify", classify)
    builder.add_edge(START, "classify")
    for name, node in answer_nodes.items():
        builder.add_node(name, node)
        builder.add_edge(name, END)
    # The explicit target list lets the drawn graph show every branch.
    builder.add_conditional_edges("classify", route_intent, list(answer_nodes))

    # In-memory only: fine for local development, lost when the process stops.
    graph = builder.compile(checkpointer=InMemorySaver())
    drawable = graph.get_graph()
    logger.debug(
        "graph compiled nodes=%s edges=%s",
        list(drawable.nodes),
        [f"{e.source}->{e.target}" for e in drawable.edges],
    )
    return graph
