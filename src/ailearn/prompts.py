from __future__ import annotations

from pathlib import Path

from .models import (
    ClaimRecord,
    ClassificationPolicy,
    DerivationRecord,
    DistinctionRecord,
    Goal,
    MisconceptionRecord,
    TestRecord,
    VisualResourceRecord,
)


def _goal_context(goal: Goal) -> str:
    topics = ", ".join(goal.priority_topics) if goal.priority_topics else "None recorded"
    return (
        f"Active learning goal: {goal.title}\n"
        f"Main goal: {goal.main_goal}\n"
        f"Stage goal: {goal.stage_goal}\n"
        f"Transfer goal: {goal.transfer_goal}\n"
        f"External goal: {goal.external_goal}\n"
        f"Priority topics: {topics}"
    )


def dynamic_positioning_prompt(
    goal: Goal,
    knowledge_point: str,
    current_context: str | None = None,
    policy: ClassificationPolicy | None = None,
    current_user_state: str | None = None,
    reference_hints: str | None = None,
    deep_research_hints: str | None = None,
) -> str:
    context = current_context or "No additional context recorded."
    policy_text = _policy_context(policy) if policy else "No classification policy supplied; infer a provisional policy from the active goal only."
    user_state = current_user_state or "No current user state supplied."
    references = reference_hints or "No reference hints supplied."
    research = deep_research_hints or "No Deep Research hints supplied."
    return f"""You are helping classify learning state, not building a world knowledge graph.

{_goal_context(goal)}

Knowledge point: {knowledge_point}
Current context: {context}
Current user state: {user_state}

Classification policy:
{policy_text}

References / source-index hints:
{references}

Deep Research hints:
{research}

Collide the knowledge point with the active learning goal, classification policy, current user state, references / Deep Research hints, and user history if supplied. In other words, collide these inputs instead of classifying the term in isolation.

Classify this knowledge point relative to the active learning goal:
- A_no_ai_internalization: must enter the learner's head as disciplinary language.
- B_knowledge_positioning: know its position, use, and relation; details can be restored by AI.
- C_index_recall: remember it only as an entry point.

Also classify its tool role as core_tool / non_core_tool / none.

Return:
- recommended A/B/C position: A_no_ai_internalization / B_knowledge_positioning / C_index_recall
- recommended learning depth
- tool_role: core_tool / non_core_tool / none
- reason
- evidence used
- next action
- revisit triggers
- whether this classification is a learning strategy judgment, not a strict fact
- whether the evidence is strict_fact, inference, or learning_strategy
- confidence: low / medium / high
"""


def _format_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) or "- None recorded."


def _policy_context(policy: ClassificationPolicy) -> str:
    return f"""Policy id: {policy.id}
Title: {policy.title}
Description: {policy.description}
A-zone criteria:
{_format_list(policy.a_zone_criteria)}
B-zone criteria:
{_format_list(policy.b_zone_criteria)}
C-zone criteria:
{_format_list(policy.c_zone_criteria)}
Core-tool criteria:
{_format_list(policy.core_tool_criteria)}
Non-core-tool criteria:
{_format_list(policy.non_core_tool_criteria)}
Test-mode criteria:
{_format_list(policy.test_mode_criteria)}
Upgrade triggers:
{_format_list(policy.upgrade_triggers)}
Downgrade triggers:
{_format_list(policy.downgrade_triggers)}
Revisit triggers:
{_format_list(policy.revisit_triggers)}
Optional examples:
{_format_list(policy.examples_optional)}"""


def refine_policy_prompt(goal: Goal) -> str:
    return f"""You are helping refine a ClassificationPolicy for a local learning-state manager.

{_goal_context(goal)}

A/B/C are a classification grammar, not a fixed map of a whole field.
Do not try to classify all knowledge points in the domain.
Derive policy criteria from the active learning goal and likely workflow:
- A-zone criteria
- B-zone criteria
- C-zone criteria
- core-tool criteria
- non-core-tool criteria
- test-mode criteria
- upgrade triggers
- downgrade triggers
- revisit triggers
- optional examples

Deep Research should produce classification policies, not only lists of topics.
Return concise policy text compatible with ClassificationPolicy. Treat it as evolving learning strategy, not final truth.
"""


def classify_with_policy_prompt(
    goal: Goal,
    knowledge_point: str,
    policy: ClassificationPolicy,
    current_user_state: str | None = None,
    reference_hints: str | None = None,
    deep_research_hints: str | None = None,
) -> str:
    return dynamic_positioning_prompt(
        goal,
        knowledge_point,
        current_context="Use the supplied policy as the current classification language.",
        policy=policy,
        current_user_state=current_user_state,
        reference_hints=reference_hints,
        deep_research_hints=deep_research_hints,
    )


def goal_intake_prompt(raw_goal: str | None = None) -> str:
    starting_point = raw_goal or "The learner has not written a goal yet."
    return f"""You are helping clarify a learning goal for a local learning state manager.

Initial learner description:
{starting_point}

Ask concise clarification questions and then propose a structured goal record.
Clarify:
- main goal
- stage goal
- transfer goal
- external goal
- desired depth
- time budget
- prior knowledge
- output expectation
- what "learning enough" should mean

Distinguish exam, research, paper-reading, project work, long-term theoretical language, and general overview goals.
The result is a learning strategy, not final truth. Do not turn this into a knowledge database.
"""


def deep_research_prompt(goal: Goal) -> str:
    return f"""Use ChatGPT Deep Research to prepare initial learning guidance.

{_goal_context(goal)}

Produce:
- global course/topic map
- core questions
- initial A/B/C knowledge split
- core tools / non-core tools / none
- suggested references
- common misconceptions
- prerequisite map
- suggested spiral learning path
- topics likely to become important later
- what should be placed in the references folder

Important constraints:
- Deep Research output is only initial guidance and must not be treated as final truth.
- Do not produce an encyclopedia.
- Do not build a static knowledge graph.
- References should become durable source entries, not copied AI summaries.
"""


def extract_references_prompt(import_id: str, import_content: str) -> str:
    return f"""Extract durable source references from a Deep Research import.

Import id: {import_id}

Return items compatible with ReferenceRecord:
- id suggestion
- goal_id if visible, otherwise leave blank
- title
- authors_or_source
- reference_type: textbook | lecture_note | paper | review | video | webpage | documentation | other
- path_or_url
- topics
- relevance_to_goal
- usage_stage: initial_map | core_learning | later_reference | optional
- reading_status: unread | skimmed | partial | read | archived
- notes

These are suggestions only. Do not treat Deep Research as final truth.
Do not extract encyclopedic notes; extract durable source entries.

Deep Research content:
{import_content}
"""


def extract_positioning_from_research_prompt(import_id: str, import_content: str) -> str:
    return f"""Extract suggested learning-positioning records from Deep Research.

Import id: {import_id}

Extract suggestions only:
- A_no_ai_internalization knowledge items
- B_knowledge_positioning knowledge items
- C_index_recall knowledge items
- core tools
- non-core tools
- revisit triggers
- common misunderstandings
- possible record_intensity: light | medium | heavy

These are suggestions only and must be checked against the learner's current goal.
Do not treat Deep Research as final truth.
Do not build a static knowledge graph.

Deep Research content:
{import_content}
"""


def claim_verification_prompt(goal: Goal, claim: ClaimRecord) -> str:
    return f"""You are verifying a student-generated claim for learning purposes.

{_goal_context(goal)}

Claim: {claim.text}
Context: {claim.context}
Current claim type: {claim.type}
Current epistemic status: {claim.epistemic_status}

Distinguish exactly which parts are:
- strict fact
- derived result
- standard interpretation
- heuristic
- analogy
- inference
- speculation
- wrong or misleading statement
- open question

Return:
- strict_part
- caveat
- counterexample_or_boundary
- corrected version if needed
- next action for the learner
"""


def derivation_guidance_prompt(goal: Goal, derivation: DerivationRecord) -> str:
    user_steps = "\n".join(f"- {step}" for step in derivation.user_derived_steps) or "- None yet"
    hinted_steps = "\n".join(f"- {step}" for step in derivation.ai_hinted_steps) or "- None yet"
    untrusted = "\n".join(f"- {step}" for step in derivation.not_yet_trusted) or "- None recorded"
    return f"""You are guiding a derivation trust-building session.

{_goal_context(goal)}

Topic: {derivation.topic}
Result to trust: {derivation.result_to_trust}
Importance: {derivation.importance}

Existing user-completed steps:
{user_steps}

Existing AI-hinted steps:
{hinted_steps}

Not-yet-trusted steps:
{untrusted}

do not give the full derivation immediately.
Ask one step at a time.
After each learner response, mark user-completed steps and AI-hinted steps separately.
Distinguish strict derivation from physical interpretation.
Only provide a hint when the learner is blocked or explicitly asks.
"""


def socratic_drill_prompt(goal: Goal, topic: str) -> str:
    return f"""You are running a Socratic drill.

{_goal_context(goal)}

Topic: {topic}

ask one question at a time.
Focus on definition, boundary, misconception, example, counterexample, and transfer.
do not answer unless asked.
After each answer classify understanding as clear / incomplete / misleading / wrong.
Keep the drill tied to the active learning goal.
"""


def weekly_review_prompt() -> str:
    return """You are helping review local learning state. Analyze the deterministic review, but do not invent facts absent from local records.

Summarize:
- unresolved claims
- derivations needing rework
- positioning decisions needing revisit
- references added or used
- topics ready for test mode
- A-level internalization progress
- unresolved learning states
- possible Socratic drill topics
- next actions

Keep facts, interpretations, analogies, inferences, speculation, and learning_strategy judgments distinct.
"""


def method_router_prompt(
    goal: Goal,
    state: str,
    topic: str | None = None,
    local_actions: list[str] | None = None,
) -> str:
    actions = ", ".join(local_actions or []) or "No local actions suggested yet."
    target = topic or "No specific topic provided."
    return f"""You are choosing a learning method, not teaching content.

{_goal_context(goal)}

Learning state: {state}
Topic: {target}
Local deterministic suggestions: {actions}

Please choose a learning method that reduces friction:
- minimal usable model
- dynamic positioning
- concept distinction
- comparison table
- claim verification
- derivation trust
- Socratic drill
- mistake-bank entry
- no-AI explanation
- test mode
- goal restructuring
- reference lookup

do not teach the whole topic unless explicitly requested.
Return the next 1-3 method actions and why each fits the learner's state.
"""


def test_topic_prompt(goal: Goal, topic: str) -> str:
    return f"""Create a test-mode prompt for a learner who thinks this topic is almost learned.

{_goal_context(goal)}

Topic: {topic}

Generate tasks for:
- no-AI explanation
- concept distinction
- boundary/counterexample
- key derivation reconstruction
- mistake diagnosis
- transfer question
- delayed retrieval

Use the internalization ladder:
- A0: marked as important but not verified
- A1: can explain and distinguish
- A2: can handle boundary and counterexample
- A3: can reconstruct / derive / transfer
- A4: can retrieve after delay without AI

Do not answer the test. Ask the learner to respond first.
"""


def test_record_prompt(goal: Goal, test_record: TestRecord) -> str:
    return f"""Run this test-mode record.

{_goal_context(goal)}

Topic: {test_record.topic}
Test type: {test_record.test_type}
Target: {test_record.internalization_target}
Existing prompt: {test_record.prompt or 'No prompt recorded yet.'}

Use no-AI explanation pressure where appropriate.
Test concept distinction, boundary/counterexample, derivation reconstruction, mistake diagnosis, transfer, and delayed retrieval as relevant.
Do not provide the answer unless the learner asks after attempting.
"""


def distinction_prompt(goal: Goal, distinction: DistinctionRecord) -> str:
    concepts = ", ".join(distinction.concepts) or distinction.title
    return f"""You are helping clarify a learner-specific adjacent-concept confusion.

{_goal_context(goal)}

Distinction record: {distinction.title}
Concepts: {concepts}
Learner confusion: {distinction.confusion_statement}
Current status: {distinction.status}
Internalization target: {distinction.internalization_target}

Do not provide a broad encyclopedia explanation.
Focus only on the distinction needed for this learner's current goal.

Return:
- shared features
- precise distinguishing criteria
- minimal examples
- boundary cases
- common mistakes
- short test questions
- how to tell whether the learner has internalized the distinction
"""


def distinction_test_prompt(goal: Goal, distinction: DistinctionRecord) -> str:
    concepts = ", ".join(distinction.concepts) or distinction.title
    return f"""Run a Socratic distinction test for this learner.

{_goal_context(goal)}

Distinction: {distinction.title}
Concepts: {concepts}
Known confusion: {distinction.confusion_statement}

Ask one question at a time.
Focus on:
- identifying examples
- identifying counterexamples
- classifying boundary cases
- explaining the criterion without AI
- detecting misconception

Do not answer first. Wait for the learner's attempt, then classify the answer as clear / incomplete / misleading / wrong.
"""


def misconception_correction_prompt(goal: Goal, misconception: MisconceptionRecord) -> str:
    return f"""You are correcting a learner-specific misconception, not writing encyclopedia notes.

{_goal_context(goal)}

Misconception: {misconception.statement}
Current correction notes: {misconception.corrected_view or 'No corrected view recorded yet.'}
Related topics: {', '.join(misconception.related_topics) or 'None recorded'}
Severity: {misconception.severity}
Status: {misconception.status}

Please:
- explain why the statement is wrong;
- identify what part feels plausible;
- give the corrected view;
- give minimal counterexamples;
- generate a short retrieval test.

Keep the answer scoped to this misconception and the active learning goal.
"""


def temporal_review_prompt(timeline_lines: list[str]) -> str:
    evidence = "\n".join(f"- {line}" for line in timeline_lines) or "- No local timeline evidence supplied."
    return f"""You are reviewing temporal learning evidence.

Deterministic local evidence:
{evidence}

Diagnose whether this looks like:
- new confusion
- short-term unresolved understanding
- long-term forgetting
- repeated misconception
- trust gap
- test-mode candidate

Clearly distinguish deterministic local evidence from AI interpretation.
Do not invent facts absent from local records.
Return compact next actions for review, retrieval, derivation trust, or distinction testing.
"""


def visual_suggestion_prompt(goal: Goal, topic: str) -> str:
    return f"""You are deciding whether a learner needs visual support, not building an image database.

{_goal_context(goal)}

Topic: {topic}

Decide whether this topic needs visual explanation because it is geometric, dynamic, relational, experimental, diagrammatic, or repeatedly confused.

Prefer visuals in this priority order:
1. figure from the paper / textbook / lecture note currently being studied;
2. reliable web image or video from authoritative sources;
3. AI-generated schematic only if no suitable source exists;
4. system-generated diagram for learning-state visualization.

Distinguish evidence visuals from pedagogical schematics.
Mark AI-generated visuals as teaching aids, not evidence.
Do not download copyrighted materials automatically.
Provide search keywords or source suggestions rather than copying copyrighted media.

Return suggested VisualResourceRecord metadata:
- topic
- title
- visual_type
- source_priority
- source_url_or_path if known
- source_detail
- reliability
- usage
- why_needed
- related_record_ids if known
- copyright_note
"""


def visual_explanation_prompt(goal: Goal, visual: VisualResourceRecord) -> str:
    ai_note = (
        "This is AI-generated or illustrative; treat it as a teaching aid and not evidence."
        if visual.source_priority == "ai_generated" or visual.visual_type == "ai_generated_schematic"
        else "Use the source reliability and copyright note before treating this visual as evidence."
    )
    return f"""You are helping the learner use one visual resource for learning state.

{_goal_context(goal)}

Visual id: {visual.id}
Topic: {visual.topic}
Title: {visual.title}
Visual type: {visual.visual_type}
Source priority: {visual.source_priority}
Source/path: {visual.source_url_or_path or 'not recorded'}
Source detail: {visual.source_detail or 'not recorded'}
Reliability: {visual.reliability}
Usage: {visual.usage}
Why needed: {visual.why_needed}
Copyright note: {visual.copyright_note or 'not recorded'}

{ai_note}

Explain how to use this visual for the recorded learning problem.
Do not treat AI-generated schematics as evidence.
Do not write a broad encyclopedia explanation.
Return:
- what the visual helps distinguish or trust
- what it does not prove
- how the learner should test understanding after using it
"""


def prompt_with_context_reference(base_prompt: str, context_path: Path | str) -> str:
    return f"""{base_prompt.rstrip()}

---

Context loading instruction:
Use the generated context pack first: {context_path}
Do not read all local files, all sessions, all references, or all Deep Research imports unless the task clearly requires additional raw evidence.
Keep deterministic local evidence separate from AI interpretation.
"""


test_topic_prompt.__test__ = False
test_record_prompt.__test__ = False
