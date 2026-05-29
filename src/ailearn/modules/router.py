from __future__ import annotations

from pydantic import BaseModel

from ailearn.agents.contracts import ModuleRouterOutput


MODE_TO_MODULE = {
    "explain": "concept_explainer",
    "compare": "example_comparison",
    "socratic": "socratic_questioner",
    "derive": "derivation_coach",
    "exercise": "exercise_generator",
    "correct": "exercise_correction_loop",
    "critic": "flawed_interpretation_critic",
    "review": "review_point_runner",
    "no_ai_test": "no_ai_reconstruction_tester",
    "auto": "concept_explainer",
}


class ModuleRoutingInput(BaseModel):
    button_action: str | None = None
    selected_mode: str | None = "auto"
    project_default_mode: str | None = None
    state_recommendation: str | None = None


class ModuleRouter:
    def route(self, item: ModuleRoutingInput) -> ModuleRouterOutput:
        if item.button_action:
            key = item.button_action
            reason = "User teaching action button has highest priority."
        elif item.selected_mode and item.selected_mode != "auto":
            key = item.selected_mode
            reason = "User selected mode overrides project defaults."
        elif item.project_default_mode:
            key = item.project_default_mode
            reason = "Project setting supplies the default learning action."
        elif item.state_recommendation:
            key = item.state_recommendation
            reason = "State Judge recommended this learning action."
        else:
            key = "explain"
            reason = "Default explanation mode."
        module = MODE_TO_MODULE.get(key, key if key in set(MODE_TO_MODULE.values()) else "concept_explainer")
        interaction = "guided_question" if module == "socratic_questioner" else "test_first" if module == "no_ai_reconstruction_tester" else "direct_response"
        return ModuleRouterOutput(module=module, secondary_module="misconception_detector", reason=reason, interaction_mode=interaction)

