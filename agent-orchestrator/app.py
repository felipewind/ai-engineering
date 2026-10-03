"""Streamlit chat UI for the agent orchestrator.

Run with:  streamlit run app.py
"""

import logging
import uuid

import streamlit as st
from langchain_core.messages import HumanMessage

from orchestrator.config import ConfigError, get_settings
from orchestrator.graph import build_graph
from orchestrator.logging_config import setup_logging
from orchestrator.tracing import GraphLoggingHandler

setup_logging()
# Under Streamlit __name__ is "__main__", so name the logger explicitly.
logger = logging.getLogger("app")

st.set_page_config(page_title="Agent Orchestrator", page_icon="🤖")
st.title("🤖 Agent Orchestrator")


@st.cache_resource
def get_graph():
    # Built once per server process; the InMemorySaver inside keeps all threads.
    return build_graph()


try:
    settings = get_settings()
    graph = get_graph()
except ConfigError as e:
    st.error(str(e))
    st.stop()

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
    logger.info("new session thread=%s", st.session_state.thread_id)

config = {"configurable": {"thread_id": st.session_state.thread_id}}

with st.sidebar:
    st.write(f"**Model:** `{settings.openai_model}`")
    if st.button("New conversation", width="stretch"):
        st.session_state.thread_id = str(uuid.uuid4())
        logger.info("new conversation thread=%s", st.session_state.thread_id)
        st.rerun()
    # Drawn from the compiled graph, so it reflects the nodes and edges actually built.
    # LangChain wraps "__start__"/"__end__" in <p> tags, which Streamlit shows as text.
    mermaid = graph.get_graph().draw_mermaid().replace("<p>", "").replace("</p>", "")
    with st.expander("Graph", expanded=True):
        st.mermaid_chart(
            mermaid,
            alt="Diagram of the compiled LangGraph workflow",
        )

# The checkpointer is the source of truth for the conversation history.
messages = graph.get_state(config).values.get("messages", [])
for message in messages:
    role = "user" if message.type == "human" else "assistant"
    with st.chat_message(role):
        st.markdown(message.content)

if prompt := st.chat_input("Send a message"):
    logger.info(
        "prompt received (%d chars) thread=%s", len(prompt), st.session_state.thread_id
    )
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # The callback handler logs each graph run and node step.
                run_config = {**config, "callbacks": [GraphLoggingHandler()]}
                graph.invoke({"messages": [HumanMessage(prompt)]}, run_config)
            except Exception as e:  # show API errors in the UI instead of a traceback
                logger.exception("graph invoke failed")
                st.error(f"Error calling the model: {e}")
                st.stop()
    st.rerun()
