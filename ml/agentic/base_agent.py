"""
Base sanitization agent class.
"""

import json
from abc import ABC, abstractmethod
from typing import Dict, Any

from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from ml.agentic.config import AgenticConfig


class AgentOutput(BaseModel):
    """Output from a sanitization agent.

    Notes:
    - `verdict` MUST be either "allow" or "sanitize".
    - `sanitized_prompt` when `verdict` == "allow" must equal the original prompt.
    """

    verdict: str  # "allow" or "sanitize"
    sanitized_prompt: str
    explanation: str
    confidence: float


class BaseSanitizationAgent(ABC):
    """
    Abstract base class for sanitization agents.
    """

    def __init__(self, config: AgenticConfig, agent_name: str):
        self.config = config
        self.agent_name = agent_name
        self.llm = ChatGroq(
            model=config.groq_model,
            api_key=config.groq_api_key,
            temperature=0.0,
        )

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass

    def _parse_llm_json(self, response_text: str, original_prompt: str) -> Dict[str, Any]:
        """
        Safely parse and validate JSON from LLM response according to the strict schema.

        Returns a dict with keys: verdict, sanitized_prompt, explanation, confidence.
        If parsing or validation fails, returns a safe default with verdict 'allow'.
        """
        # Default safe output
        safe_default = {
            "verdict": "allow",
            "sanitized_prompt": original_prompt,
            "explanation": "Failed to parse LLM response; defaulting to allow.",
            "confidence": 0.0,
        }

        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start < 0 or json_end <= json_start:
                return safe_default

            json_str = response_text[json_start:json_end]
            parsed = json.loads(json_str)

            if not isinstance(parsed, dict):
                return safe_default

            # Extract and normalize fields
            verdict = str(parsed.get("verdict", "")).strip().lower()
            if verdict not in ("allow", "sanitize"):
                # Disallow any other verdicts (e.g., 'block', 'user_review')
                verdict = "allow"

            sanitized_prompt = parsed.get("sanitized_prompt", "")
            if sanitized_prompt is None:
                sanitized_prompt = ""
            sanitized_prompt = str(sanitized_prompt)

            explanation = parsed.get("explanation", "")
            if explanation is None:
                explanation = ""
            explanation = str(explanation).strip()
            # Keep explanation short (single-line); truncate if necessary
            explanation = explanation.splitlines()[0][:400]

            # Confidence: ensure numeric between 0 and 1
            try:
                confidence = float(parsed.get("confidence", 0.0))
            except Exception:
                confidence = 0.0
            if confidence < 0.0 or confidence > 1.0:
                confidence = max(0.0, min(1.0, confidence))

            # Enforce rules: when verdict == allow, sanitized_prompt must equal original
            if verdict == "allow":
                sanitized_prompt = original_prompt

            # For sanitize: if sanitized_prompt empty, fallback to allow (safe behavior)
            if verdict == "sanitize" and not sanitized_prompt.strip():
                return safe_default

            return {
                "verdict": verdict,
                "sanitized_prompt": sanitized_prompt,
                "explanation": explanation,
                "confidence": confidence,
            }

        except (json.JSONDecodeError, ValueError, TypeError):
            return safe_default

    def run(
        self,
        prompt: str,
        segment_texts: list,
        segment_score_map: Dict[str, tuple],
    ) -> AgentOutput:
        """
        Run the agent to sanitize the prompt.

        Args:
            prompt: Original user prompt
            segment_texts: List of segment text strings
            segment_score_map: Dict mapping segment text → (mal, persona, infoleak, codeexec) scores

        Returns:
            AgentOutput with verdict and sanitized prompt
        """
        system_prompt = self.get_system_prompt()

        # Build user message with context and very strict output instructions
        user_message = f"""
Original prompt: {prompt}

Segments:
{chr(10).join(f'- {seg}' for seg in segment_texts)}

Segment scores (malicious, persona, infoleak, codeexec):
{chr(10).join(f'- "{seg}": {segment_score_map.get(seg, (0,0,0,0))}' for seg in segment_texts)}

INSTRUCTIONS: Respond with EXACTLY one JSON object and nothing else. The JSON MUST follow this schema:
{{"verdict": "allow" | "sanitize", "sanitized_prompt": "<text>", "explanation": "<short explanation>", "confidence": <float 0.0-1.0>}}

Rules:
- Only use "allow" or "sanitize" for "verdict" (do NOT use "block" or "user_review").
- If the prompt is safe, return "verdict": "allow" and set "sanitized_prompt" equal to the original prompt.
- If the prompt is unsafe, return "verdict": "sanitize" and set "sanitized_prompt" to a safe, non-harmful rewrite that preserves the topic but removes dangerous intent. Sanitization may include clarifying questions in the sanitized prompt when necessary.
- Do NOT include any commentary, explanation, or text outside the JSON object. Keep the JSON minimal and valid.
"""

        # Call LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        response = self.llm.invoke(messages)
        response_text = getattr(response, "content", str(response))

        # Parse and validate response
        parsed = self._parse_llm_json(response_text, original_prompt=prompt)

        return AgentOutput(
            verdict=parsed.get("verdict", "allow"),
            sanitized_prompt=parsed.get("sanitized_prompt", prompt),
            explanation=parsed.get("explanation", ""),
            confidence=float(parsed.get("confidence", 0.0)),
        )
