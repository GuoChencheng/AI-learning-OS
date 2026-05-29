from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


Intent = Literal[
    "ask_concept",
    "ask_plan",
    "do_exercise",
    "derive",
    "review",
    "run_next",
    "update_goal",
    "upload_reference",
]
Urgency = Literal["low", "medium", "high"]
UserSelectedMode = Literal["explain", "compare", "socratic", "derive", "exercise", "critic", "review", "auto"]
LearningAction = Literal["explain", "compare", "socratic", "derive", "exercise", "critic", "review"]
PermissionBoundary = Literal["direct_answer", "guided_hint", "no_ai_test_first"]
LearningState = Literal["confused", "unstable", "progressing", "over_dependent", "ready_for_derivation", "needs_review"]
KnowledgeLayer = Literal["no_ai_internalization", "positioning", "index"]
RecordIntensity = Literal["light", "medium", "heavy"]
InteractionMode = Literal["direct_response", "guided_question", "test_first"]
AssessmentLevel = Literal["A0", "A1", "A2", "A3", "A4"]
AssessmentResult = Literal["passed", "partial", "failed", "skipped"]
ReviewTriggerStatus = Literal["pending", "completed", "failed", "skipped"]
DistinctionStatus = Literal["needs_test", "partially_clear", "clear", "failed", "needs_retest"]
ClaimStatus = Literal["active", "revised", "deprecated", "verified", "misleading", "wrong", "open_question"]
EpistemicStatus = Literal[
    "strict_fact",
    "derived_result",
    "standard_interpretation",
    "heuristic",
    "analogy",
    "inference",
    "speculation",
    "learning_strategy",
    "wrong",
    "open_question",
]
ReviewType = Literal["explain", "distinguish", "derive", "transfer", "error_check"]
SourceType = Literal[
    "user_explicit",
    "user_question",
    "user_answer",
    "user_error",
    "user_revision",
    "system_trace",
    "ai_suggested_draft",
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequestIntakeOutput(ContractModel):
    intent: Intent
    topic: str
    urgency: Urgency
    needs_reference: bool
    needs_state_read: bool
    user_selected_mode: UserSelectedMode


class ProjectResolverOutput(ContractModel):
    project_id: str
    confidence: float = Field(ge=0, le=1)
    reason: str


class ContextExtractorOutput(ContractModel):
    relevant_goals: list[dict[str, Any]]
    relevant_references: list[dict[str, Any]]
    relevant_reference_chunks: list[dict[str, Any]] = Field(default_factory=list)
    relevant_claims: list[dict[str, Any]]
    relevant_distinctions: list[dict[str, Any]]
    recent_traces: list[dict[str, Any]]
    active_review_triggers: list[dict[str, Any]]


class ContextPackBuilderOutput(ContractModel):
    current_request: str
    goal_context: str
    reference_context: str
    learning_state_context: str
    known_confusions: list[str]
    must_respect_constraints: list[str]
    suggested_learning_action: LearningAction
    ai_permission_boundary: PermissionBoundary


class StateJudgeOutput(ContractModel):
    learning_state: LearningState
    knowledge_layer: KnowledgeLayer
    record_intensity: RecordIntensity
    risk_flags: list[str]


class ModuleRouterOutput(ContractModel):
    module: str
    secondary_module: str | None = None
    reason: str
    interaction_mode: InteractionMode


class AnswerComposerOutput(ContractModel):
    answer: str
    exercise: str | None = None
    follow_up_question: str | None = None
    suggested_next_action: str


class NewClaim(ContractModel):
    original_statement: str
    normalized_statement: str
    related_concept: str
    epistemic_status: EpistemicStatus
    confidence: float = Field(ge=0, le=1)
    correction: str | None = None


class NewDistinction(ContractModel):
    concept_a: str
    concept_b: str
    boundary: str
    common_confusion: str
    example: str
    test_question: str


class NewTemporalTrace(ContractModel):
    event_type: str
    user_question: str
    system_response_summary: str
    state_change_summary: str
    next_step: str


class KnowledgePositionUpdate(ContractModel):
    concept: str
    layer: KnowledgeLayer
    reason: str
    target_level: Literal["A0", "A1", "A2", "A3", "A4"]
    current_level: Literal["A0", "A1", "A2", "A3", "A4"]
    review_needed: bool


class DerivationTrustUpdate(ContractModel):
    result_or_tool: str
    assumptions: list[str]
    key_steps: list[str]
    done_by_user: list[str]
    hinted_by_ai: list[str]
    untrusted_steps: list[str]
    failure_conditions: list[str]
    no_ai_reconstruction_status: str
    next_rederive_time: str | None = None


class NewReviewTrigger(ContractModel):
    target: str
    trigger_reason: str
    review_type: ReviewType
    scheduled_time: str
    success_criteria: str


class SourceMetadata(ContractModel):
    source_type: SourceType = "system_trace"
    source_message_id: str | None = None
    evidence_text: str = ""


class StateWriterOutput(ContractModel):
    new_claims: list[NewClaim]
    updated_claims: list[dict[str, Any]]
    new_distinctions: list[NewDistinction]
    new_temporal_trace: NewTemporalTrace
    knowledge_position_updates: list[KnowledgePositionUpdate]
    derivation_trust_updates: list[DerivationTrustUpdate]
    review_triggers: list[NewReviewTrigger]
    next_recommended_action: str
    source_metadata: SourceMetadata = Field(default_factory=SourceMetadata)
    user_originated_updates: dict[str, Any] = Field(default_factory=dict)
    ai_only_observations: dict[str, Any] = Field(default_factory=dict)
    discarded_ephemeral_judgments: dict[str, Any] = Field(default_factory=dict)


class NoAIReconstructionAssessmentOutput(ContractModel):
    concept: str
    previous_level: AssessmentLevel
    new_level: AssessmentLevel
    result: Literal["passed", "partial", "failed"]
    evidence_text: str
    reason: str
    next_action: str
    should_schedule_review: bool


class DerivationStepAssessmentOutput(ContractModel):
    result_or_tool: str
    done_by_user: list[str]
    hinted_by_ai: list[str]
    untrusted_steps: list[str]
    no_ai_reconstruction_status: str
    reason: str
    next_action: str
    should_schedule_rederive: bool


class DistinctionAssessmentOutput(ContractModel):
    concept_a: str
    concept_b: str
    status: DistinctionStatus
    confusion_count_delta: int
    evidence_text: str
    reason: str
    next_test_question: str | None = None
    should_schedule_retest: bool


class ClaimEpistemicAssessmentOutput(ContractModel):
    claim_id: str | None = None
    original_statement: str
    epistemic_status: EpistemicStatus
    status: ClaimStatus
    confidence: float = Field(ge=0, le=1)
    strict_part: str | None = None
    caveat: str | None = None
    correction: str | None = None
    evidence_text: str
    reason: str


class MisconceptionRecurrenceOutput(ContractModel):
    misconception_key: str
    statement: str
    related_claim_ids: list[str]
    related_distinction_ids: list[str]
    recurrence_count_delta: int
    severity: Literal["low", "medium", "high"]
    evidence_text: str
    next_action: str
