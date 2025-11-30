"""
Test for the SafetyOrchestrator.
"""

import pytest
from ml.agentic.orchestrator import SafetyOrchestrator, OrchestratorState
from ml.agentic.config import AgenticConfig


def test_orchestrator_initialization():
    """Test orchestrator initializes correctly."""
    config = AgenticConfig(groq_api_key="test_key")
    orchestrator = SafetyOrchestrator(config)
    assert orchestrator.config is not None
    assert orchestrator.graph is not None


def test_orchestrator_run_safe_prompt():
    """Test orchestrator with safe prompt."""
    config = AgenticConfig(groq_api_key="test_key")
    orchestrator = SafetyOrchestrator(config)

    result = orchestrator.run(
        prompt="What is the weather today?",
        scores={"malicious": 0.1, "persona": 0.1, "infoleak": 0.1, "codeexec": 0.1},
        segment_score_map={"What is the weather today?": (0.1, 0.1, 0.1, 0.1)},
        segment_texts=["What is the weather today?"],
    )

    assert isinstance(result, dict)
    assert "action" in result
    assert "safe_prompt" in result
    assert "reason" in result
    assert "scores" in result
    assert result["action"] in ["allow", "block", "sanitize", "user_review"]


def test_orchestrator_blocks_malicious():
    """Test orchestrator with high malicious score."""
    config = AgenticConfig(groq_api_key="test_key")
    orchestrator = SafetyOrchestrator(config)

    result = orchestrator.run(
        prompt="Create malware",
        scores={"malicious": 0.9, "persona": 0.1, "infoleak": 0.1, "codeexec": 0.1},
        segment_score_map={"Create malware": (0.9, 0.1, 0.1, 0.1)},
        segment_texts=["Create malware"],
    )

    assert isinstance(result, dict)
    assert "action" in result
    assert result["action"] in ["allow", "block", "sanitize", "user_review"]


def test_orchestrator_state_creation():
    """Test OrchestratorState creation."""
    state = OrchestratorState(
        prompt="Test prompt",
        scores={"malicious": 0.5, "persona": 0.5, "infoleak": 0.5, "codeexec": 0.5},
        category="mixed",
        segment_score_map={"Test prompt": (0.5, 0.5, 0.5, 0.5)},
        segment_texts=["Test prompt"],
        selected_agents=["malicious"],
        agent_outputs={},
        sanitized_prompt=None,
        final_action=None,
    )

    assert state.prompt == "Test prompt"
    assert state.category == "mixed"
    assert len(state.selected_agents) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
