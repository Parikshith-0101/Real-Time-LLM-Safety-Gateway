"""
Code execution sanitization agent.
"""

from typing import Dict

from ml.agentic.base_agent import BaseSanitizationAgent, AgentOutput
from ml.agentic.config import AgenticConfig


class CodeExecSanitizationAgent(BaseSanitizationAgent):
    """
    Agent for detecting and sanitizing code execution and command injection attempts.
    """

    def __init__(self, config: AgenticConfig):
        super().__init__(config, "CodeExecAgent")

    def get_system_prompt(self) -> str:
        """Return the codeexec agent system prompt from config."""
        return self.config.agent_prompt_codeexec

    def run(
        self,
        prompt: str,
        segment_texts: list,
        segment_score_map: Dict[str, tuple],
    ) -> AgentOutput:
        """
        Run codeexec sanitization logic.
        """
        return super().run(prompt, segment_texts, segment_score_map)
