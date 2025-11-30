"""
Persona/jailbreak sanitization agent.
"""

from typing import Dict

from ml.agentic.base_agent import BaseSanitizationAgent, AgentOutput
from ml.agentic.config import AgenticConfig


class PersonaSanitizationAgent(BaseSanitizationAgent):
    """
    Agent for detecting and sanitizing persona-swap and jailbreak attempts.
    """

    def __init__(self, config: AgenticConfig):
        super().__init__(config, "PersonaAgent")

    def get_system_prompt(self) -> str:
        """Return the persona agent system prompt from config."""
        return self.config.agent_prompt_persona

    def run(
        self,
        prompt: str,
        segment_texts: list,
        segment_score_map: Dict[str, tuple],
    ) -> AgentOutput:
        """
        Run persona sanitization logic.
        """
        return super().run(prompt, segment_texts, segment_score_map)
