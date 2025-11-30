"""
Utility functions for the agentic orchestration layer.
"""

from typing import Dict, List, Tuple


def select_segments_for_agent(
    scores: Dict[str, float],
    segment_score_map: Dict[str, Tuple[float, float, float, float]],
    agent_dim: int,
) -> List[str]:
    """
    Select segments where the agent dimension score >= 0.5.

    Args:
        scores: ML scores dict {"malicious": x, "persona": y, ...}
        segment_score_map: Mapping segment_text → (mal, persona, infoleak, codeexec)
        agent_dim: Dimension index (0=malicious, 1=persona, 2=infoleak, 3=codeexec)

    Returns:
        List of relevant segment texts
    """
    selected = []
    for seg_text, score_tuple in segment_score_map.items():
        if score_tuple[agent_dim] >= 0.5:
            selected.append(seg_text)
    return selected


def build_final_action_object(
    action: str,
    safe_prompt: str,
    reason: str,
    scores: Dict[str, float],
) -> Dict:
    """
    Build the final action object as JSON.

    Args:
        action: "allow", "block", "sanitize", or "user_review"
        safe_prompt: The final safe/sanitized prompt
        reason: Explanation for the action
        scores: ML scores dict

    Returns:
        JSON-serializable dict
    """
    return {
        "action": action,
        "safe_prompt": safe_prompt,
        "reason": reason,
        "scores": scores,
    }


def map_dim_to_agent_name(dim: int) -> str:
    """
    Map dimension index to agent name.

    Args:
        dim: 0=malicious, 1=persona, 2=infoleak, 3=codeexec

    Returns:
        Agent name string
    """
    names = ["malicious", "persona", "infoleak", "codeexec"]
    return names[dim] if 0 <= dim < len(names) else "unknown"
