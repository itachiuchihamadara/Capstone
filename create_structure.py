import os

base_dir = r"c:\Project\PythonEngine\Google_ADK\google-adk\lab\capstone_demo"

dirs = [
    os.path.join(base_dir, "src", "agents"),
    os.path.join(base_dir, "src", "tools"),
    os.path.join(base_dir, "src", "services"),
    os.path.join(base_dir, "src", "rag", "data"),
    os.path.join(base_dir, "src", "ui"),
    os.path.join(base_dir, "src", "voice"),
    os.path.join(base_dir, "src", "guardrails"),
    os.path.join(base_dir, "src", "observability"),
    os.path.join(base_dir, "src", "config"),
    os.path.join(base_dir, "tests"),
    os.path.join(base_dir, "evals"),
    os.path.join(base_dir, ".github", "workflows")
]

for d in dirs:
    os.makedirs(d, exist_ok=True)

files = [
    os.path.join(base_dir, "src", "agents", "orchestrator.py"),
    os.path.join(base_dir, "src", "tools", "order_tools.py"),
    os.path.join(base_dir, "src", "tools", "product_tools.py"),
    os.path.join(base_dir, "src", "services", "mcp_orders.py"),
    os.path.join(base_dir, "src", "services", "mcp_inventory.py"),
    os.path.join(base_dir, "src", "rag", "embed_catalog.py"),
    os.path.join(base_dir, "src", "rag", "retriever.py"),
    os.path.join(base_dir, "src", "rag", "data", "products.json"),
    os.path.join(base_dir, "src", "rag", "data", "faq.json"),
    os.path.join(base_dir, "src", "ui", "app.py"),
    os.path.join(base_dir, "src", "voice", "pipeline.py"),
    os.path.join(base_dir, "src", "guardrails", "input_guard.py"),
    os.path.join(base_dir, "src", "guardrails", "output_guard.py"),
    os.path.join(base_dir, "src", "observability", "langsmith_config.py"),
    os.path.join(base_dir, "tests", "test_tools.py"),
    os.path.join(base_dir, "tests", "test_routing.py"),
    os.path.join(base_dir, "tests", "test_guardrails.py"),
    os.path.join(base_dir, "evals", "promptfoo.yaml"),
    os.path.join(base_dir, ".github", "workflows", "ci.yml"),
    os.path.join(base_dir, "docker-compose.yml"),
    os.path.join(base_dir, "Dockerfile"),
    os.path.join(base_dir, ".env.example"),
    os.path.join(base_dir, "README.md")
]

for f in files:
    if not os.path.exists(f):
        with open(f, 'w') as file:
            pass

print("Structure created.")
