"""
Malicious prompt sanitization agent.
"""

from typing import Dict

from ml.agentic.base_agent import BaseSanitizationAgent, AgentOutput
from ml.agentic.config import AgenticConfig


class MaliciousSanitizationAgent(BaseSanitizationAgent):
    """
    Agent for detecting and sanitizing malicious prompts.
    """

    def __init__(self, config: AgenticConfig):
        super().__init__(config, "MaliciousAgent")

    def get_system_prompt(self) -> str:
        """Return the malicious agent system prompt from config."""
        return self.config.agent_prompt_malicious

    def run(
        self,
        prompt: str,
        segment_texts: list,
        segment_score_map: Dict[str, tuple],
    ) -> AgentOutput:
        """
        Run malicious sanitization logic.
        """
        return super().run(prompt, segment_texts, segment_score_map)
