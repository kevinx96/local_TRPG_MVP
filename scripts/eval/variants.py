from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Optional

from host import free_actions


@dataclass(frozen=True)
class Variant:
    # Each hook receives fresh data; variants cannot mutate the game's defaults.
    message_builder: Callable = free_actions.build_plan_messages
    config_builder: Callable = free_actions.planner_config
    system_prompt: Optional[str] = None
    few_shot: tuple = ()
    schema_transform: Optional[Callable] = None

    def prepare(self, session: dict[str, Any], text: str, config: dict[str, Any]) -> tuple:
        messages = deepcopy(self.message_builder(deepcopy(session), text))
        configured = deepcopy(self.config_builder(deepcopy(config)))
        if self.system_prompt is not None:
            messages[0]["content"] = self.system_prompt
        if self.few_shot:
            messages[-1:-1] = deepcopy(list(self.few_shot))
        if self.schema_transform:
            schema = configured["response_format"]["json_schema"]["schema"]
            configured["response_format"]["json_schema"]["schema"] = self.schema_transform(schema)
        return messages, configured


VARIANTS = {"default": Variant()}
