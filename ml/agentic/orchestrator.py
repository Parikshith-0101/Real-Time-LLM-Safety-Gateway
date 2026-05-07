"""
LangGraph orchestrator for agentic safety workflow.
"""

import json
from typing import Dict, Any, Optional

from dataclasses import dataclass
# Try to import AgenticConfig; if unavailable, provide minimal defaults so orchestrator can initialize
try:
    from ml.agentic.config import AgenticConfig  # type: ignore
except Exception:
    class AgenticConfig:  # fallback minimal config
        groq_api_key: str = ""
        groq_model: str = "llama-3.3-70b-versatile"
        malicious_threshold: float = 0.7
        persona_threshold: float = 0.6
        infoleak_threshold: float = 0.65
        codeexec_threshold: float = 0.65
        safe_threshold: float = 0.5
        rerun_ml_on_sanitized: bool = False
from ml.agentic.utils import build_final_action_object, map_dim_to_agent_name

# NOTE: Defer heavy imports (langgraph, agents, SafetyGateway) to runtime to avoid import-time failures
# when optional dependencies are not installed. This allows orchestrator to initialize and make
# threshold-based decisions without agent graph.



@dataclass
class OrchestratorState:
    """State object for the orchestration workflow."""
    prompt: str
    scores: Dict[str, float]
    category: str
    segment_score_map: Dict[str, tuple]
    segment_texts: list
    selected_agents: list
    agent_outputs: Dict[str, Any]
    sanitized_prompt: Optional[str]
    final_action: Optional[str]
    reason: str = ""


# Simple, explicit thresholds for decisioning
LOW_RISK_THRESHOLD = 0.25
HIGH_RISK_THRESHOLD = 0.50


class SafetyOrchestrator:
    """
    LangGraph-based orchestrator for safety decisions.
    Instantiable with no positional args and sets required attributes.
    """

    def __init__(self, config: Optional[AgenticConfig] = None):
        # Allow argument-free construction
        if config is None:
            config = AgenticConfig()
        self.config = config

        # Defer building the agent graph until needed (ambiguous zone)
        self.graph = None  # will be compiled on-demand

    def _build_graph(self):
        """Build the LangGraph workflow (imports deferred)."""
        try:
            from langgraph.graph import StateGraph, START, END  # type: ignore
            # Agents are imported lazily to avoid import-time dependency failures
            from ml.agentic.malicious_agent import MaliciousSanitizationAgent  # noqa: F401
            from ml.agentic.persona_agent import PersonaSanitizationAgent  # noqa: F401
            from ml.agentic.infoleak_agent import InfoLeakSanitizationAgent  # noqa: F401
            from ml.agentic.codeexec_agent import CodeExecSanitizationAgent  # noqa: F401
            from ml.inference.safety_gateway import SafetyGateway  # noqa: F401
        except Exception as e:
            raise RuntimeError(f"Agent graph dependencies missing: {e}")

        graph = StateGraph(OrchestratorState)

        # Add nodes
        graph.add_node("manager", self._manager_node)
        graph.add_node("malicious_agent", self._malicious_agent_node)
        graph.add_node("persona_agent", self._persona_agent_node)
        graph.add_node("infoleak_agent", self._infoleak_agent_node)
        graph.add_node("codeexec_agent", self._codeexec_agent_node)
        graph.add_node("aggregator", self._aggregator_node)
        graph.add_node("end", self._end_node)

        # Add edges (sequential agent chain)
        graph.add_edge(START, "manager")
        graph.add_edge("manager", "malicious_agent")
        graph.add_edge("malicious_agent", "persona_agent")
        graph.add_edge("persona_agent", "infoleak_agent")
        graph.add_edge("infoleak_agent", "codeexec_agent")
        graph.add_edge("codeexec_agent", "aggregator")
        graph.add_edge("aggregator", "end")
        graph.add_edge("end", END)

        return graph.compile()

    def _manager_node(self, state: OrchestratorState) -> OrchestratorState:
        """
        Manager node: select agents based on ML scores and thresholds.
        """
        selected = []

        if state.scores.get("malicious", 0) >= self.config.malicious_threshold:
            selected.append("malicious")

        if state.scores.get("persona", 0) >= self.config.persona_threshold:
            selected.append("persona")

        if state.scores.get("infoleak", 0) >= self.config.infoleak_threshold:
            selected.append("infoleak")

        if state.scores.get("codeexec", 0) >= self.config.codeexec_threshold:
            selected.append("codeexec")

        state.selected_agents = selected
        state.agent_outputs = {}

        return state

    def _malicious_agent_node(self, state: OrchestratorState) -> OrchestratorState:
        """Run malicious agent if selected."""
        if "malicious" not in state.selected_agents:
            return state

        agent = MaliciousSanitizationAgent(self.config)
        output = agent.run(state.prompt, state.segment_texts, state.segment_score_map)
        state.agent_outputs["malicious"] = output.dict()

        return state

    def _persona_agent_node(self, state: OrchestratorState) -> OrchestratorState:
        """Run persona agent if selected."""
        if "persona" not in state.selected_agents:
            return state

        agent = PersonaSanitizationAgent(self.config)
        output = agent.run(state.prompt, state.segment_texts, state.segment_score_map)
        state.agent_outputs["persona"] = output.dict()

        return state

    def _infoleak_agent_node(self, state: OrchestratorState) -> OrchestratorState:
        """Run infoleak agent if selected."""
        if "infoleak" not in state.selected_agents:
            return state

        agent = InfoLeakSanitizationAgent(self.config)
        output = agent.run(state.prompt, state.segment_texts, state.segment_score_map)
        state.agent_outputs["infoleak"] = output.dict()

        return state

    def _codeexec_agent_node(self, state: OrchestratorState) -> OrchestratorState:
        """Run codeexec agent if selected."""
        if "codeexec" not in state.selected_agents:
            return state

        agent = CodeExecSanitizationAgent(self.config)
        output = agent.run(state.prompt, state.segment_texts, state.segment_score_map)
        state.agent_outputs["codeexec"] = output.dict()

        return state

    def _aggregator_node(self, state: OrchestratorState) -> OrchestratorState:
        """
        Aggregator node: merge verdicts and pick final action.
        """
        if not state.agent_outputs:
            state.final_action = "allow"
            state.sanitized_prompt = state.prompt
            state.reason = "No agents selected; allowing prompt."
            return state

        # Check for blocked
        for agent_name, output in state.agent_outputs.items():
            if output.get("verdict") == "blocked":
                state.final_action = "block"
                state.sanitized_prompt = state.prompt
                state.reason = f"Blocked by {agent_name} agent: {output.get('explanation', '')}"
                return state

        # Check for sanitize
        sanitize_outputs = [
            (name, out)
            for name, out in state.agent_outputs.items()
            if out.get("verdict") == "sanitize"
        ]

        if sanitize_outputs:
            # Pick highest confidence sanitized prompt
            best = max(sanitize_outputs, key=lambda x: x[1].get("confidence", 0))
            agent_name, best_output = best
            state.sanitized_prompt = best_output.get("sanitized_prompt", state.prompt)
            state.reason = f"Sanitized by {agent_name} agent: {best_output.get('explanation', '')}"

            # ML rerun if enabled
            if self.config.rerun_ml_on_sanitized and state.sanitized_prompt:
                try:
                    sg = SafetyGateway(models_dir="ml/models")
                    simple_scores, _ = sg.predict(state.sanitized_prompt)
                    max_score = max(simple_scores.values())

                    if max_score > self.config.safe_threshold:
                        state.final_action = "user_review"
                        state.reason += f"; ML rerun score: {max_score:.2f} (requires review)"
                    else:
                        state.final_action = "sanitize"
                except Exception:
                    state.final_action = "sanitize"
            else:
                state.final_action = "sanitize"

            return state

        # Default: allow
        state.final_action = "allow"
        state.sanitized_prompt = state.prompt
        state.reason = "All agents approved; allowing prompt."

        return state

    def _end_node(self, state: OrchestratorState) -> Dict[str, Any]:
        """
        End node: build final JSON output.
        """
        return build_final_action_object(
            action=state.final_action or "allow",
            safe_prompt=state.sanitized_prompt or state.prompt,
            reason=state.reason,
            scores=state.scores,
        )

    def run(
        self,
        prompt: str,
        scores: Dict[str, float],
        category: str,
        segment_score_map: Dict[str, tuple],
        segment_texts: list,
    ) -> Dict[str, Any]:
        """
        Run the orchestrator workflow.

        REQUIRED CHANGE: apply threshold-based decision using ML scores
        - If max_score < LOW_RISK_THRESHOLD => allow
        - If max_score >= HIGH_RISK_THRESHOLD => sanitize
        - Else => run agent graph to refine; if no agents sanitize => allow
        """
        # 1) Basic sanity and max score computation
        safe_scores = scores or {}
        if not safe_scores:
            max_score = 0.0
        else:
            try:
                max_score = max(float(v) for v in safe_scores.values())
            except Exception:
                max_score = 0.0

        # 2) Immediate decisions based on thresholds
        if max_score < LOW_RISK_THRESHOLD:
            # Allow benign prompts
            return build_final_action_object(
                action="allow",
                safe_prompt=prompt,
                reason=f"max_score={max_score:.2f} < LOW_RISK_THRESHOLD={LOW_RISK_THRESHOLD}",
                scores=safe_scores,
            )

        if max_score >= HIGH_RISK_THRESHOLD:
            # Sanitize clearly malicious prompts
            return build_final_action_object(
                action="sanitize",
                safe_prompt=prompt,  # pipeline will replace if agents propose a sanitized prompt later
                reason=f"max_score={max_score:.2f} >= HIGH_RISK_THRESHOLD={HIGH_RISK_THRESHOLD}",
                scores=safe_scores,
            )

        # 3) Ambiguous zone: use existing agent graph as tie-breaker
        initial_state = OrchestratorState(
            prompt=prompt,
            scores=safe_scores,
            category=category,
            segment_score_map=segment_score_map,
            segment_texts=segment_texts,
            selected_agents=[],
            agent_outputs={},
            sanitized_prompt=None,
            final_action=None,
            reason="",
        )

        # Build graph on-demand
        if self.graph is None:
            self.graph = self._build_graph()

        result = self.graph.invoke(initial_state)

        # Ensure result is JSON-serializable and never default to sanitize
        if isinstance(result, OrchestratorState):
            return build_final_action_object(
                action=result.final_action or "allow",
                safe_prompt=result.sanitized_prompt or result.prompt,
                reason=result.reason or f"ambiguous: max_score={max_score:.2f}",
                scores=result.scores,
            )

        return result
