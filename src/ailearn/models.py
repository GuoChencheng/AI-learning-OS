from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .ids import now_utc


class PositionLayer(StrEnum):
    A_NO_AI_INTERNALIZATION = "A_no_ai_internalization"
    B_KNOWLEDGE_POSITIONING = "B_knowledge_positioning"
    C_INDEX_RECALL = "C_index_recall"


class ToolRole(StrEnum):
    CORE_TOOL = "core_tool"
    NON_CORE_TOOL = "non_core_tool"
    NONE = "none"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EpistemicStatus(StrEnum):
    STRICT_FACT = "strict_fact"
    DERIVED_RESULT = "derived_result"
    STANDARD_INTERPRETATION = "standard_interpretation"
    HEURISTIC = "heuristic"
    ANALOGY = "analogy"
    INFERENCE = "inference"
    SPECULATION = "speculation"
    LEARNING_STRATEGY = "learning_strategy"
    WRONG = "wrong"
    OPEN_QUESTION = "open_question"


class RecordStrength(StrEnum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class RecordIntensity(StrEnum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class InternalizationLevel(StrEnum):
    NONE = "none"
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"


class ClaimType(StrEnum):
    DEFINITION = "definition"
    ANALOGY = "analogy"
    HYPOTHESIS = "hypothesis"
    CONNECTION = "connection"
    CALCULATION = "calculation"
    INTERPRETATION = "interpretation"


class ClaimStatus(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    PARTIALLY_CORRECT = "partially_correct"
    MISLEADING = "misleading"
    WRONG = "wrong"
    OPEN_QUESTION = "open_question"


class DerivationImportance(StrEnum):
    CORE_CONCEPT = "core_concept"
    CORE_TOOL = "core_tool"
    OPTIONAL = "optional"


class DerivationStatus(StrEnum):
    NOT_STARTED = "not_started"
    PARTIAL = "partial"
    TRUSTED = "trusted"
    NEEDS_REDERIVE = "needs_rederive"


class ReferenceType(StrEnum):
    TEXTBOOK = "textbook"
    LECTURE_NOTE = "lecture_note"
    PAPER = "paper"
    REVIEW = "review"
    VIDEO = "video"
    WEBPAGE = "webpage"
    DOCUMENTATION = "documentation"
    OTHER = "other"


class UsageStage(StrEnum):
    INITIAL_MAP = "initial_map"
    CORE_LEARNING = "core_learning"
    LATER_REFERENCE = "later_reference"
    OPTIONAL = "optional"


class ReadingStatus(StrEnum):
    UNREAD = "unread"
    SKIMMED = "skimmed"
    PARTIAL = "partial"
    READ = "read"
    ARCHIVED = "archived"


class LearningState(StrEnum):
    TOTALLY_UNCLEAR = "totally_unclear"
    NAME_ONLY = "name_only"
    CONCEPTUALLY_CONFUSED = "conceptually_confused"
    NEARBY_CONCEPTS_CONFUSED = "nearby_concepts_confused"
    FEELS_UNDERSTOOD_BUT_CANNOT_EXPLAIN = "feels_understood_but_cannot_explain"
    FORMULA_WITHOUT_TRUST = "formula_without_trust"
    NEW_CLAIM = "new_claim"
    REPEATED_MISTAKE = "repeated_mistake"
    MECHANICAL_COMPUTATION = "mechanical_computation"
    ENTERING_CORE_TOPIC = "entering_core_topic"
    READY_FOR_TEST = "ready_for_test"
    TOO_MUCH_MATERIAL = "too_much_material"
    UNKNOWN_NEXT_STEP = "unknown_next_step"


class TestType(StrEnum):
    NO_AI_EXPLANATION = "no_ai_explanation"
    CONCEPT_DISTINCTION = "concept_distinction"
    BOUNDARY_COUNTEREXAMPLE = "boundary_counterexample"
    DERIVATION_RECONSTRUCTION = "derivation_reconstruction"
    MISTAKE_DIAGNOSIS = "mistake_diagnosis"
    TRANSFER_QUESTION = "transfer_question"
    DELAYED_RETRIEVAL = "delayed_retrieval"
    MIXED = "mixed"


class TestStatus(StrEnum):
    PLANNED = "planned"
    GENERATED = "generated"
    ATTEMPTED = "attempted"
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_RETEST = "needs_retest"


class InternalizationTarget(StrEnum):
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"


class DistinctionStatus(StrEnum):
    NEEDS_DISTINCTION = "needs_distinction"
    PARTIALLY_CLEAR = "partially_clear"
    CLEAR = "clear"
    NEEDS_TEST = "needs_test"
    RESOLVED = "resolved"
    NEEDS_RETEST = "needs_retest"


class MisconceptionSeverity(StrEnum):
    MINOR = "minor"
    IMPORTANT = "important"
    DANGEROUS = "dangerous"


class MisconceptionStatus(StrEnum):
    ACTIVE = "active"
    CORRECTED = "corrected"
    RECURRING = "recurring"
    ARCHIVED = "archived"


class ConceptClusterStatus(StrEnum):
    PROVISIONAL = "provisional"
    LEARNING = "learning"
    USABLE = "usable"
    NEEDS_REVIEW = "needs_review"
    STABLE = "stable"


class VisualType(StrEnum):
    PAPER_FIGURE = "paper_figure"
    TEXTBOOK_FIGURE = "textbook_figure"
    LECTURE_FIGURE = "lecture_figure"
    RELIABLE_WEB_IMAGE = "reliable_web_image"
    RELIABLE_WEB_VIDEO = "reliable_web_video"
    ANIMATION = "animation"
    INTERACTIVE = "interactive"
    AI_GENERATED_SCHEMATIC = "ai_generated_schematic"
    SYSTEM_GENERATED_DIAGRAM = "system_generated_diagram"
    OTHER = "other"


class VisualSourcePriority(StrEnum):
    PAPER_OR_TEXTBOOK = "paper_or_textbook"
    RELIABLE_WEB = "reliable_web"
    AI_GENERATED = "ai_generated"
    SYSTEM_GENERATED = "system_generated"


class Reliability(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VisualUsage(StrEnum):
    EXPLANATION = "explanation"
    DISTINCTION = "distinction"
    DERIVATION = "derivation"
    TEST = "test"
    REVIEW = "review"
    REFERENCE = "reference"


class LearningModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Goal(LearningModel):
    id: str
    title: str
    main_goal: str
    stage_goal: str
    transfer_goal: str
    external_goal: str
    active: bool = True
    priority_topics: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class PositionDecision(LearningModel):
    id: str
    goal_id: str
    policy_id: str | None = None
    knowledge_point: str
    position: PositionLayer
    tool_role: ToolRole
    reason: str
    confidence: Confidence
    epistemic_status: EpistemicStatus
    revisit_when: list[str] = Field(default_factory=list)
    record_strength: RecordStrength = RecordStrength.LIGHT
    record_intensity: RecordIntensity = RecordIntensity.LIGHT
    internalization_level: InternalizationLevel = InternalizationLevel.NONE
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    first_seen_at: datetime | None = None
    last_touched_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    last_tested_at: datetime | None = None
    next_review_at: datetime | None = None


class ClaimRecord(LearningModel):
    id: str
    goal_id: str
    text: str
    context: str
    type: ClaimType
    status: ClaimStatus
    epistemic_status: EpistemicStatus
    strict_part: str = ""
    caveat: str = ""
    counterexample_or_boundary: str = ""
    next_action: str = ""
    record_intensity: RecordIntensity = RecordIntensity.LIGHT
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    first_seen_at: datetime | None = None
    last_touched_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    last_tested_at: datetime | None = None
    next_review_at: datetime | None = None
    last_checked_at: datetime | None = None
    verified_at: datetime | None = None
    next_recheck_at: datetime | None = None


class DerivationRecord(LearningModel):
    id: str
    goal_id: str
    topic: str
    importance: DerivationImportance
    status: DerivationStatus
    result_to_trust: str
    user_derived_steps: list[str] = Field(default_factory=list)
    ai_hinted_steps: list[str] = Field(default_factory=list)
    not_yet_trusted: list[str] = Field(default_factory=list)
    next_action: str = ""
    record_intensity: RecordIntensity = RecordIntensity.LIGHT
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    first_seen_at: datetime | None = None
    last_touched_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    last_tested_at: datetime | None = None
    next_review_at: datetime | None = None
    first_attempted_at: datetime | None = None
    last_attempted_at: datetime | None = None
    trusted_at: datetime | None = None
    last_rederived_at: datetime | None = None
    next_rederive_at: datetime | None = None


class ReferenceRecord(LearningModel):
    id: str
    goal_id: str
    title: str
    authors_or_source: str
    reference_type: ReferenceType
    path_or_url: str
    topics: list[str] = Field(default_factory=list)
    relevance_to_goal: str
    usage_stage: UsageStage
    reading_status: ReadingStatus = ReadingStatus.UNREAD
    notes: str = ""
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class ClassificationPolicy(LearningModel):
    id: str
    goal_id: str
    title: str
    description: str
    a_zone_criteria: list[str] = Field(default_factory=list)
    b_zone_criteria: list[str] = Field(default_factory=list)
    c_zone_criteria: list[str] = Field(default_factory=list)
    core_tool_criteria: list[str] = Field(default_factory=list)
    non_core_tool_criteria: list[str] = Field(default_factory=list)
    test_mode_criteria: list[str] = Field(default_factory=list)
    upgrade_triggers: list[str] = Field(default_factory=list)
    downgrade_triggers: list[str] = Field(default_factory=list)
    revisit_triggers: list[str] = Field(default_factory=list)
    examples_optional: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class VisualResourceRecord(LearningModel):
    id: str
    goal_id: str
    topic: str
    title: str
    visual_type: VisualType
    source_priority: VisualSourcePriority
    source_url_or_path: str = ""
    source_detail: str = ""
    reliability: Reliability
    usage: VisualUsage
    why_needed: str
    related_record_ids: list[str] = Field(default_factory=list)
    copyright_note: str = ""
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class SessionFootprint(LearningModel):
    id: str
    goal_id: str
    topic: str
    mode: str
    learning_state: LearningState | None = None
    methods_used: list[str] = Field(default_factory=list)
    references_used: list[str] = Field(default_factory=list)
    provisional_understanding: str = ""
    test_mode_triggered: bool = False
    references_added: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class TestRecord(LearningModel):
    id: str
    goal_id: str
    topic: str
    position_id: str | None = None
    test_type: TestType
    status: TestStatus
    internalization_target: InternalizationTarget
    prompt: str
    learner_answer: str | None = None
    feedback: str | None = None
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    first_seen_at: datetime | None = None
    last_touched_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    last_tested_at: datetime | None = None
    next_review_at: datetime | None = None
    attempted_at: datetime | None = None
    passed_at: datetime | None = None
    failed_at: datetime | None = None
    next_retest_at: datetime | None = None
    test_interval_days: int | None = None


TestRecord.__test__ = False


class DistinctionRecord(LearningModel):
    id: str
    goal_id: str
    title: str
    concepts: list[str] = Field(default_factory=list)
    confusion_statement: str
    shared_features: list[str] = Field(default_factory=list)
    distinguishing_criteria: list[str] = Field(default_factory=list)
    minimal_examples: list[str] = Field(default_factory=list)
    boundary_cases: list[str] = Field(default_factory=list)
    common_misconceptions: list[str] = Field(default_factory=list)
    status: DistinctionStatus
    internalization_target: InternalizationLevel = InternalizationLevel.NONE
    record_intensity: RecordIntensity = RecordIntensity.LIGHT
    first_confused_at: datetime | None = None
    last_confused_at: datetime | None = None
    last_distinguished_at: datetime | None = None
    next_distinction_test_at: datetime | None = None
    confusion_count: int = 0
    related_claim_ids: list[str] = Field(default_factory=list)
    related_test_ids: list[str] = Field(default_factory=list)
    related_session_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    first_seen_at: datetime | None = None
    last_touched_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    last_tested_at: datetime | None = None
    next_review_at: datetime | None = None
    next_action: str = ""


class MisconceptionRecord(LearningModel):
    id: str
    goal_id: str
    statement: str
    why_wrong: str
    corrected_view: str
    related_topics: list[str] = Field(default_factory=list)
    severity: MisconceptionSeverity
    status: MisconceptionStatus
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    corrected_at: datetime | None = None
    recurrence_count: int = 0
    related_claim_ids: list[str] = Field(default_factory=list)
    related_distinction_ids: list[str] = Field(default_factory=list)
    related_session_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    last_touched_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    last_tested_at: datetime | None = None
    next_review_at: datetime | None = None
    next_action: str = ""


class ConceptClusterRecord(LearningModel):
    id: str
    goal_id: str
    title: str
    core_question: str
    concepts: list[str] = Field(default_factory=list)
    current_status: ConceptClusterStatus
    reason: str
    related_distinction_ids: list[str] = Field(default_factory=list)
    related_position_ids: list[str] = Field(default_factory=list)
    related_session_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)
    first_seen_at: datetime | None = None
    last_touched_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    last_tested_at: datetime | None = None
    next_review_at: datetime | None = None
    next_action: str = ""


class ReviewDraft(LearningModel):
    id: str
    created_at: datetime = Field(default_factory=now_utc)
    title: str
    sections: dict[str, list[str]] = Field(default_factory=dict)
