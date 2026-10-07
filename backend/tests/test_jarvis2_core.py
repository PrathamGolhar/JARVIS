import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ai.router import ModelRouter, TaskCategory, TaskClassifier
from app.services.agents.task_graph import NodeStatus, TaskGraph
from app.services.events.bus import EventBus, EventType
from app.services.tools.math_engine import MathEngine
from app.services.file_processing.multi_doc import MultiDocumentReasoner
from app.services.plugins.base import JARVISPlugin, PermissionScope, PluginRegistry, PluginToolDefinition

client = TestClient(app)


def test_task_classifier_and_model_router() -> None:
    # 1. Classify simple query
    cat_simple = TaskClassifier.classify("What is the time?")
    assert cat_simple == TaskCategory.SIMPLE_CONVERSATION

    # 2. Classify vision query
    cat_vision = TaskClassifier.classify("Analyze this circuit", has_images=True)
    assert cat_vision == TaskCategory.VISION_MULTIMODAL

    # 3. Classify math query
    cat_math = TaskClassifier.classify("Calculate the derivative of x^3 + 5*x")
    assert cat_math == TaskCategory.MATHEMATICS_COMPUTE

    # 4. Classify coding query
    cat_code = TaskClassifier.classify("def fibonacci(n): fix the syntax error")
    assert cat_code == TaskCategory.CODING_AND_SYNTAX

    # 5. Route decision
    route = ModelRouter.route("Explain quantum computing")
    assert route.provider_name in ["gemini", "groq", "openai", "anthropic", "local"]
    assert route.recommended_model

    # 6. Anthropic Provider instance availability test
    from app.services.ai.anthropic_provider import AnthropicProvider
    anthropic = AnthropicProvider(api_key="test-key-mock")
    assert anthropic.name == "anthropic"
    assert anthropic.is_available() is True


@pytest.mark.anyio
async def test_task_graph_dag_execution() -> None:
    graph = TaskGraph(name="TestDAG")

    # Step 1: Data extraction
    def extract_data(doc_name: str) -> dict:
        return {"extracted": f"Data from {doc_name}"}

    # Step 2: Synthesis dependent on Step 1
    def synthesize_data(topic: str) -> dict:
        return {"summary": f"Synthesized report on {topic}"}

    graph.add_node("step_1", "Extract PDF", "file_extract", handler=extract_data, parameters={"doc_name": "circuit.pdf"})
    graph.add_node("step_2", "Generate Report", "generate_pdf", handler=synthesize_data, parameters={"topic": "Circuits"}, dependencies=["step_1"])

    res = await graph.execute_all()
    assert res["completed"] is True
    assert len(res["results"]) == 2
    assert "step_1" in res["results"]
    assert "step_2" in res["results"]


@pytest.mark.anyio
async def test_event_bus_publish_subscribe() -> None:
    bus = EventBus()
    received_events = []

    def on_task_complete(event) -> None:
        received_events.append(event)

    bus.subscribe(EventType.TASK_COMPLETED, on_task_complete)
    await bus.publish(EventType.TASK_COMPLETED, {"taskId": "job_101", "status": "success"})

    assert len(received_events) == 1
    assert received_events[0].type == EventType.TASK_COMPLETED
    assert received_events[0].payload["taskId"] == "job_101"


def test_math_engine_symbolic_and_numerical() -> None:
    # 1. Arithmetic & Functions
    calc_res = MathEngine.evaluate_math_query("calculate 15 * 4 + sqrt(256)")
    assert calc_res["ok"] is True
    assert calc_res["result"] == 76

    # 2. Matrix Determinant
    det_res = MathEngine.evaluate_math_query("det([[4, 2], [3, 1]])")
    assert det_res["ok"] is True
    assert det_res["determinant"] == -2

    # 3. Descriptive Statistics
    stats_res = MathEngine.evaluate_math_query("stats([10, 20, 30, 40, 50])")
    assert stats_res["ok"] is True
    assert stats_res["mean"] == 30.0
    assert stats_res["sampleSize"] == 5

    # 4. Symbolic Derivative
    diff_res = MathEngine.evaluate_math_query("derivative of 3*x^2 + 4*x")
    assert diff_res["ok"] is True
    assert "6*x" in diff_res["derivative"]


def test_multi_document_reasoner() -> None:
    docs = [
        {"filename": "Report_A.pdf", "content": "Microservices enhance scalability through decoupled services."},
        {"filename": "Report_B.pdf", "content": "Monolithic architectures reduce operational latency for small teams."},
    ]
    res = MultiDocumentReasoner.compare_documents(docs, focus_topic="Architecture Tradeoffs")
    assert len(res.documents_analyzed) == 2
    assert len(res.commonalities) >= 1
    assert len(res.differences) >= 1
    assert res.synthesis_markdown


def test_plugin_sdk_registration_and_execution() -> None:
    class MockMathPlugin(JARVISPlugin):
        name = "mock_math_plugin"
        version = "1.0.0"
        description = "Mock plugin for testing"

        def get_tools(self) -> list[PluginToolDefinition]:
            return [
                PluginToolDefinition(
                    name="add_numbers",
                    description="Adds two integers",
                    parameters_schema={"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}},
                    handler=lambda a, b: a + b,
                    required_permissions=[PermissionScope.READ],
                )
            ]

    registry = PluginRegistry()
    registry.register_plugin(MockMathPlugin())

    assert len(registry.list_plugins()) == 1
    assert registry.get_tool("add_numbers") is not None
    assert registry.execute_tool("add_numbers", {"a": 25, "b": 75}) == 100


def test_extended_health_probes() -> None:
    # 1. /health
    r1 = client.get("/health")
    assert r1.status_code == 200
    assert r1.json()["system"] == "JARVIS 2.0"

    # 2. /health/ai
    r2 = client.get("/health/ai")
    assert r2.status_code == 200
    assert "configuredProviders" in r2.json()

    # 3. /health/database
    r3 = client.get("/health/database")
    assert r3.status_code == 200
    assert r3.json()["connected"] is True

    # 4. /health/storage
    r4 = client.get("/health/storage")
    assert r4.status_code == 200
    assert "freeDiskGb" in r4.json()

    # 5. /health/workers
    r5 = client.get("/health/workers")
    assert r5.status_code == 200
    assert r5.json()["taskGraphEngine"] == "online"
