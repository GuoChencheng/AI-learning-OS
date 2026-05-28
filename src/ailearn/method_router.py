from __future__ import annotations

from dataclasses import dataclass

from .models import LearningState


@dataclass(frozen=True)
class MethodRecommendation:
    state: LearningState
    actions: list[str]
    rationale: str


METHODS: dict[LearningState, MethodRecommendation] = {
    LearningState.TOTALLY_UNCLEAR: MethodRecommendation(
        LearningState.TOTALLY_UNCLEAR,
        ["minimal usable model", "dynamic positioning", "reference lookup"],
        "Start with orientation before adding detail.",
    ),
    LearningState.NAME_ONLY: MethodRecommendation(
        LearningState.NAME_ONLY,
        ["dynamic positioning", "minimal usable model", "reference lookup"],
        "The learner needs role and use before depth.",
    ),
    LearningState.CONCEPTUALLY_CONFUSED: MethodRecommendation(
        LearningState.CONCEPTUALLY_CONFUSED,
        ["minimal usable model", "Socratic drill", "concept distinction"],
        "Confusion needs a small model and active checks.",
    ),
    LearningState.NEARBY_CONCEPTS_CONFUSED: MethodRecommendation(
        LearningState.NEARBY_CONCEPTS_CONFUSED,
        ["concept distinction", "comparison table", "Socratic drill"],
        "Neighboring ideas should be separated by boundaries and examples.",
    ),
    LearningState.FEELS_UNDERSTOOD_BUT_CANNOT_EXPLAIN: MethodRecommendation(
        LearningState.FEELS_UNDERSTOOD_BUT_CANNOT_EXPLAIN,
        ["no-AI explanation", "Socratic drill", "test mode"],
        "Explanation failure is a signal for retrieval and distinction testing.",
    ),
    LearningState.FORMULA_WITHOUT_TRUST: MethodRecommendation(
        LearningState.FORMULA_WITHOUT_TRUST,
        ["derivation trust", "Socratic drill", "boundary/counterexample"],
        "A usable formula without derivation trust needs reconstruction pressure.",
    ),
    LearningState.NEW_CLAIM: MethodRecommendation(
        LearningState.NEW_CLAIM,
        ["claim verification", "reference lookup", "dynamic positioning"],
        "Student-generated claims should be classified before reuse.",
    ),
    LearningState.REPEATED_MISTAKE: MethodRecommendation(
        LearningState.REPEATED_MISTAKE,
        ["mistake-bank entry", "Socratic drill", "concept distinction"],
        "Repeated errors need explicit diagnosis and targeted retrieval.",
    ),
    LearningState.MECHANICAL_COMPUTATION: MethodRecommendation(
        LearningState.MECHANICAL_COMPUTATION,
        ["minimal usable model", "boundary/counterexample", "transfer question"],
        "Mechanical fluency needs meaning, boundaries, and transfer.",
    ),
    LearningState.ENTERING_CORE_TOPIC: MethodRecommendation(
        LearningState.ENTERING_CORE_TOPIC,
        ["dynamic positioning", "reference lookup", "derivation trust"],
        "Core topics need depth choice, durable sources, and trust checks.",
    ),
    LearningState.READY_FOR_TEST: MethodRecommendation(
        LearningState.READY_FOR_TEST,
        ["test mode", "no-AI explanation", "transfer question"],
        "A nearly learned topic should be tested rather than reread.",
    ),
    LearningState.TOO_MUCH_MATERIAL: MethodRecommendation(
        LearningState.TOO_MUCH_MATERIAL,
        ["goal restructuring", "dynamic positioning", "reference lookup"],
        "Chaotic material needs pruning and prioritization.",
    ),
    LearningState.UNKNOWN_NEXT_STEP: MethodRecommendation(
        LearningState.UNKNOWN_NEXT_STEP,
        ["method-router prompt", "dynamic positioning", "Socratic drill"],
        "When the next move is unclear, choose a method before studying more.",
    ),
}


def recommend_methods(state: LearningState | str) -> MethodRecommendation:
    learning_state = state if isinstance(state, LearningState) else LearningState(state)
    return METHODS[learning_state]
