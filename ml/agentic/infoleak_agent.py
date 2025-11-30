"""
Information leakage sanitization agent.
"""

from typing import Dict

from ml.agentic.base_agent import BaseSanitizationAgent, AgentOutput
from ml.agentic.config import AgenticConfig


class InfoLeakSanitizationAgent(BaseSanitizationAgent):
    """
    Agent for detecting and sanitizing information leakage attempts.
    """

    def __init__(self, config: AgenticConfig):
        super().__init__(config, "InfoLeakAgent")

    def get_system_prompt(self) -> str:
        """Return the infoleak agent system prompt from config."""
        return self.config.agent_prompt_infoleak

    def run(
        self,
        prompt: str,
        segment_texts: list,
        segment_score_map: Dict[str, tuple],
    ) -> AgentOutput:
        """
        Run infoleak sanitization logic.
        """
        return super().run(prompt, segment_texts, segment_score_map)
