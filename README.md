At a high level, the app is a Streamlit chat UI that sends each user message into the orchestrator, and the orchestrator decides whether to answer directly, delegate to Support, delegate to Sales, or run a mixed two-step flow

Streamlit is prefered over Gradio due to security raised by our organization on use it;

Used free model all-MiniLM-L6-v2 for embedding the sample documents in RAG flow;
