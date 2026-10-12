"""Pluggable LLM provider. Default: built-in Cognitive ReAct engine."""

from typing import Any, Dict, List, Optional

from .rule_engine import cognitive_rule_engine


class LlmProvider:
    def __init__(self):
        self.provider = "BUILTIN_COGNITIVE_ENGINE"

    def configure(self, provider: str = "BUILTIN_COGNITIVE_ENGINE", **_kwargs):
        self.provider = provider or "BUILTIN_COGNITIVE_ENGINE"

    def generate_initial_plan(self, goal: str) -> List[Dict[str, Any]]:
        return cognitive_rule_engine.generate_initial_plan(goal)

    def decide_next_step(
        self,
        goal: str,
        memory,
        step_count: int = 0,
        tools: Optional[list] = None,
    ) -> Dict[str, Any]:
        return cognitive_rule_engine.decide_next_step(goal, memory, step_count, tools)

    def info(self) -> Dict[str, str]:
        return {
            "provider": self.provider,
            "label": "Cognitive ReAct v1" if self.provider == "BUILTIN_COGNITIVE_ENGINE" else self.provider,
        }


global_llm_provider = LlmProvider()
