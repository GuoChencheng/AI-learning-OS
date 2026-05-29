from __future__ import annotations

import os
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .ai_runs import list_ai_runs, load_ai_run, preview_as_dict, preview_payload, save_ai_run_artifact
from .config import load_config, public_config_summary
from .context import build_context_pack, context_policy_text
from .doctor import run_doctor
from .events import LearningEvent, append_event, build_timeline, compact_event_snapshot, load_events
from .ids import new_id, now_utc
from .indexes import index_paths, refresh_indexes, show_index, topic_summary
from .models import (
    ClaimRecord,
    ClassificationPolicy,
    ConceptClusterRecord,
    DerivationRecord,
    DistinctionRecord,
    Goal,
    MisconceptionRecord,
    PositionDecision,
    ReferenceRecord,
    SessionFootprint,
    TestRecord,
    VisualResourceRecord,
)
from .method_router import recommend_methods
from .prompts import (
    claim_verification_prompt,
    classify_with_policy_prompt,
    deep_research_prompt,
    derivation_guidance_prompt,
    distinction_prompt,
    distinction_test_prompt,
    dynamic_positioning_prompt,
    extract_positioning_from_research_prompt,
    extract_references_prompt,
    goal_intake_prompt,
    method_router_prompt,
    misconception_correction_prompt,
    prompt_with_context_reference,
    refine_policy_prompt,
    socratic_drill_prompt,
    temporal_review_prompt,
    test_record_prompt,
    test_topic_prompt,
    visual_explanation_prompt,
    visual_suggestion_prompt,
    weekly_review_prompt,
)
from .providers.base import ChatRequest, ProviderError
from .providers.registry import build_provider, configured_provider_summaries
from .review import generate_weekly_review
from .review import due_review_items
from .status import project_status, render_status, suggest_next_actions
from .storage import (
    active_goal,
    copy_research_import,
    find_research_import,
    init_project,
    list_sessions,
    list_yaml_records,
    load_session,
    load_yaml_model,
    save_record,
    save_session,
    save_yaml_model,
)
from .test_mode import suggest_tests
from .validate import validate_project
from .web_server import serve_ui

app = typer.Typer(help="AI Learning OS local learning-state CLI.")
goal_app = typer.Typer(help="Manage learning goals.")
position_app = typer.Typer(help="Manage knowledge positioning decisions.")
claim_app = typer.Typer(help="Manage student-generated claims.")
derivation_app = typer.Typer(help="Manage derivation trust records.")
session_app = typer.Typer(help="Manage lightweight session footprints.")
reference_app = typer.Typer(help="Manage durable source references.")
policy_app = typer.Typer(help="Manage dynamic classification policies.")
visual_app = typer.Typer(help="Manage lightweight visual resource metadata.")
distinction_app = typer.Typer(help="Manage adjacent-concept distinction records.")
misconception_app = typer.Typer(help="Manage recurring misconception records.")
cluster_app = typer.Typer(help="Manage lightweight learning-state concept clusters.")
event_app = typer.Typer(help="Inspect append-only learning event logs.")
method_app = typer.Typer(help="Suggest learning methods.")
test_app = typer.Typer(help="Manage test mode records.")
prompt_app = typer.Typer(help="Generate copyable AI prompts.")
import_app = typer.Typer(help="Import external research suggestions.")
review_app = typer.Typer(help="Generate local reviews.")
index_app = typer.Typer(help="Generate and inspect derived indexes.")
context_app = typer.Typer(help="Build minimal task-specific AI context packs.")
provider_app = typer.Typer(help="Inspect optional local AI providers.")
ai_app = typer.Typer(help="Run explicit provider-backed AI actions.")
ai_runs_app = typer.Typer(help="Inspect AI run artifacts.")
console = Console()


def _root() -> Path:
    return Path.cwd()


def _require_goal(goal_id: str | None = None) -> Goal:
    if goal_id:
        path = _root() / "data" / "goals" / f"{goal_id}.yaml"
        if not path.exists():
            raise typer.BadParameter(f"Goal not found: {goal_id}")
        return load_yaml_model(path, Goal)
    goal = active_goal(_root())
    if goal is None:
        raise typer.BadParameter("No active goal found. Create one with `learn goal create`.")
    return goal


def _print_model(model: object) -> None:
    if hasattr(model, "model_dump_json"):
        console.print_json(model.model_dump_json(indent=2))
    else:
        console.print(model)


def _log_record_event(
    event_type: str,
    target_type: str,
    record: object,
    summary: str,
    before: dict[str, object] | None = None,
) -> None:
    after = record.model_dump(mode="json") if hasattr(record, "model_dump") else None
    append_event(
        LearningEvent.new(
            event_type=event_type,
            target_type=target_type,
            target_id=getattr(record, "id"),
            goal_id=getattr(record, "goal_id", None),
            summary=summary,
            before=compact_event_snapshot(before),
            after=compact_event_snapshot(after),
            source="user",
        ),
        root=_root(),
    )


def _print_prompt(
    prompt: str,
    *,
    with_context: bool = False,
    task_type: str,
    record_id: str | None = None,
    topic: str | None = None,
    goal_id: str | None = None,
    budget: str = "medium",
) -> None:
    if with_context:
        pack = build_context_pack(
            _root(),
            task_type=task_type,
            record_id=record_id,
            topic=topic,
            goal_id=goal_id,
            budget=budget,
        )
        prompt = prompt_with_context_reference(prompt, pack.path)
    console.print(prompt)


def _selected_config(config_path: Path | None = None):
    return load_config(_root(), config_path=config_path)


def _print_provider_summary(provider_id: str, model: str | None, preview_text: str, preview_source: Path | None = None) -> None:
    preview = preview_payload(preview_text, preview_source)
    console.print("[bold]Connected-mode send preview[/bold]")
    table = Table("Field", "Value")
    table.add_row("provider", provider_id)
    table.add_row("model", model or "provider default")
    table.add_row("context size", f"{preview.size_bytes} bytes")
    table.add_row("records included", ", ".join(preview.records_included[:12]) or "none detected")
    table.add_row("references included", ", ".join(preview.references_included[:12]) or "none detected")
    table.add_row("raw sessions included", str(preview.raw_sessions_included))
    table.add_row("raw references included", str(preview.raw_references_included))
    console.print(table)


def _run_provider_text(
    *,
    provider_id: str,
    text: str,
    prompt_type: str,
    prompt_file_path: Path | None = None,
    context_pack_path: Path | None = None,
    model: str | None = None,
    yes: bool = False,
    config_path: Path | None = None,
) -> Path:
    config = _selected_config(config_path)
    provider = build_provider(config, provider_id)
    selected_model = model or config.default_model
    _print_provider_summary(provider_id, selected_model, text, prompt_file_path or context_pack_path)
    if not yes and not typer.confirm("Send only this selected prompt/context to the configured provider?"):
        raise typer.Exit(1)
    result = provider.run_chat(
        ChatRequest(
            system_prompt=(
                "You are assisting ai-learning-os. Treat local records as learner state, not final truth. "
                "Do not invent facts absent from selected context."
            ),
            user_prompt=text,
            model=selected_model,
        )
    )
    metadata_path = save_ai_run_artifact(
        _root(),
        result=result,
        prompt_text=text,
        prompt_type=prompt_type,
        related_record_ids=preview_payload(text).records_included,
        context_pack_path=context_pack_path,
        prompt_file_path=prompt_file_path,
    )
    console.print(result.text)
    console.print(f"\nSaved AI run artifact: {metadata_path}")
    return metadata_path


@app.command("init")
def init(project_name: str = typer.Argument(..., help="Project directory, or '.' for current directory.")) -> None:
    root = init_project(Path(project_name))
    console.print(f"Initialized learning project at {root}")


@goal_app.command("create")
def goal_create(
    title: str = typer.Option(..., "--title"),
    main_goal: str = typer.Option("", "--main-goal"),
    stage_goal: str = typer.Option("", "--stage-goal"),
    transfer_goal: str = typer.Option("", "--transfer-goal"),
    external_goal: str = typer.Option("", "--external-goal"),
    priority_topic: list[str] | None = typer.Option(None, "--priority-topic"),
    inactive: bool = typer.Option(False, "--inactive"),
) -> None:
    goal = Goal(
        id=new_id("goal"),
        title=title,
        main_goal=main_goal,
        stage_goal=stage_goal,
        transfer_goal=transfer_goal,
        external_goal=external_goal,
        active=not inactive,
        priority_topics=priority_topic or [],
    )
    path = save_record(_root(), "goals", goal)
    _log_record_event("record_created", "goals", goal, f"Created goal: {goal.title}")
    console.print(f"Created goal {goal.id}: {path}")


@goal_app.command("list")
def goal_list() -> None:
    goals = list_yaml_records(_root(), "goals", Goal)
    table = Table("ID", "Title", "Active", "Updated")
    for goal in goals:
        table.add_row(goal.id, goal.title, str(goal.active), goal.updated_at.isoformat())
    console.print(table)


@goal_app.command("show")
def goal_show(goal_id: str) -> None:
    _print_model(load_yaml_model(_root() / "data" / "goals" / f"{goal_id}.yaml", Goal))


@position_app.command("add")
def position_add(
    knowledge_point: str,
    goal_id: str | None = typer.Option(None, "--goal-id"),
    policy_id: str | None = typer.Option(None, "--policy-id"),
    position: str = typer.Option("B_knowledge_positioning", "--position"),
    tool_role: str = typer.Option("none", "--tool-role"),
    reason: str = typer.Option("", "--reason"),
    confidence: str = typer.Option("medium", "--confidence"),
    epistemic_status: str = typer.Option("learning_strategy", "--epistemic-status"),
    revisit_when: list[str] | None = typer.Option(None, "--revisit-when"),
    record_strength: str = typer.Option("light", "--record-strength"),
    record_intensity: str = typer.Option("light", "--record-intensity"),
    internalization_level: str = typer.Option("none", "--internalization-level"),
) -> None:
    goal = _require_goal(goal_id)
    decision = PositionDecision(
        id=new_id("pos"),
        goal_id=goal.id,
        policy_id=policy_id,
        knowledge_point=knowledge_point,
        position=position,
        tool_role=tool_role,
        reason=reason,
        confidence=confidence,
        epistemic_status=epistemic_status,
        revisit_when=revisit_when or [],
        record_strength=record_strength,
        record_intensity=record_intensity,
        internalization_level=internalization_level,
    )
    path = save_record(_root(), "positioning", decision)
    _log_record_event("record_created", "positioning", decision, f"Created position decision: {decision.knowledge_point}")
    console.print(f"Created position decision {decision.id}: {path}")


@position_app.command("list")
def position_list() -> None:
    records = list_yaml_records(_root(), "positioning", PositionDecision)
    table = Table("ID", "Knowledge Point", "Position", "Tool Role", "Confidence")
    for record in records:
        table.add_row(record.id, record.knowledge_point, record.position, record.tool_role, record.confidence)
    console.print(table)


@position_app.command("show")
def position_show(position_id: str) -> None:
    _print_model(load_yaml_model(_root() / "data" / "positioning" / f"{position_id}.yaml", PositionDecision))


@position_app.command("revisit")
def position_revisit() -> None:
    records = [record for record in list_yaml_records(_root(), "positioning", PositionDecision) if record.revisit_when]
    for record in records:
        console.print(f"{record.id}: {record.knowledge_point} -> {', '.join(record.revisit_when)}")


@claim_app.command("add")
def claim_add(
    text: str,
    goal_id: str | None = typer.Option(None, "--goal-id"),
    context: str = typer.Option("", "--context"),
    type: str = typer.Option("hypothesis", "--type"),
    status: str = typer.Option("unverified", "--status"),
    epistemic_status: str = typer.Option("speculation", "--epistemic-status"),
    next_action: str = typer.Option("", "--next-action"),
    record_intensity: str = typer.Option("light", "--record-intensity"),
) -> None:
    goal = _require_goal(goal_id)
    claim = ClaimRecord(
        id=new_id("claim"),
        goal_id=goal.id,
        text=text,
        context=context,
        type=type,
        status=status,
        epistemic_status=epistemic_status,
        strict_part="",
        caveat="",
        counterexample_or_boundary="",
        next_action=next_action,
        record_intensity=record_intensity,
    )
    path = save_record(_root(), "claims", claim)
    _log_record_event("record_created", "claims", claim, f"Created claim: {claim.text}")
    console.print(f"Created claim {claim.id}: {path}")


@claim_app.command("list")
def claim_list() -> None:
    claims = list_yaml_records(_root(), "claims", ClaimRecord)
    table = Table("ID", "Status", "Epistemic", "Text")
    for claim in claims:
        table.add_row(claim.id, claim.status, claim.epistemic_status, claim.text)
    console.print(table)


@claim_app.command("show")
def claim_show(claim_id: str) -> None:
    _print_model(load_yaml_model(_root() / "data" / "claims" / f"{claim_id}.yaml", ClaimRecord))


@claim_app.command("update")
def claim_update(
    claim_id: str,
    status: str | None = typer.Option(None, "--status"),
    epistemic_status: str | None = typer.Option(None, "--epistemic-status"),
    strict_part: str | None = typer.Option(None, "--strict-part"),
    caveat: str | None = typer.Option(None, "--caveat"),
    counterexample_or_boundary: str | None = typer.Option(None, "--counterexample-or-boundary"),
    next_action: str | None = typer.Option(None, "--next-action"),
    record_intensity: str | None = typer.Option(None, "--record-intensity"),
) -> None:
    path = _root() / "data" / "claims" / f"{claim_id}.yaml"
    claim = load_yaml_model(path, ClaimRecord)
    before = claim.model_dump(mode="json")
    data = claim.model_dump()
    for key, value in {
        "status": status,
        "epistemic_status": epistemic_status,
        "strict_part": strict_part,
        "caveat": caveat,
        "counterexample_or_boundary": counterexample_or_boundary,
        "next_action": next_action,
        "record_intensity": record_intensity,
    }.items():
        if value is not None:
            data[key] = value
    data["updated_at"] = now_utc()
    updated = ClaimRecord.model_validate(data)
    save_yaml_model(path, updated)
    event_type = "claim_status_changed" if status is not None and status != claim.status else "record_updated"
    _log_record_event(event_type, "claims", updated, f"Updated claim: {updated.text}", before=before)
    console.print(f"Updated claim {claim_id}")


@derivation_app.command("add")
def derivation_add(
    topic: str,
    goal_id: str | None = typer.Option(None, "--goal-id"),
    importance: str = typer.Option("core_concept", "--importance"),
    status: str = typer.Option("not_started", "--status"),
    result_to_trust: str = typer.Option("", "--result-to-trust"),
    next_action: str = typer.Option("", "--next-action"),
    record_intensity: str = typer.Option("light", "--record-intensity"),
) -> None:
    goal = _require_goal(goal_id)
    derivation = DerivationRecord(
        id=new_id("der"),
        goal_id=goal.id,
        topic=topic,
        importance=importance,
        status=status,
        result_to_trust=result_to_trust,
        user_derived_steps=[],
        ai_hinted_steps=[],
        not_yet_trusted=[],
        next_action=next_action,
        record_intensity=record_intensity,
    )
    path = save_record(_root(), "derivations", derivation)
    _log_record_event("record_created", "derivations", derivation, f"Created derivation: {derivation.topic}")
    console.print(f"Created derivation {derivation.id}: {path}")


@derivation_app.command("list")
def derivation_list() -> None:
    records = list_yaml_records(_root(), "derivations", DerivationRecord)
    table = Table("ID", "Topic", "Importance", "Status")
    for record in records:
        table.add_row(record.id, record.topic, record.importance, record.status)
    console.print(table)


@derivation_app.command("show")
def derivation_show(derivation_id: str) -> None:
    _print_model(load_yaml_model(_root() / "data" / "derivations" / f"{derivation_id}.yaml", DerivationRecord))


@derivation_app.command("update")
def derivation_update(
    derivation_id: str,
    status: str | None = typer.Option(None, "--status"),
    user_step: list[str] | None = typer.Option(None, "--user-step"),
    ai_hinted_step: list[str] | None = typer.Option(None, "--ai-hinted-step"),
    not_yet_trusted: list[str] | None = typer.Option(None, "--not-yet-trusted"),
    next_action: str | None = typer.Option(None, "--next-action"),
    record_intensity: str | None = typer.Option(None, "--record-intensity"),
) -> None:
    path = _root() / "data" / "derivations" / f"{derivation_id}.yaml"
    derivation = load_yaml_model(path, DerivationRecord)
    before = derivation.model_dump(mode="json")
    data = derivation.model_dump()
    if status is not None:
        data["status"] = status
    if user_step:
        data["user_derived_steps"] = [*derivation.user_derived_steps, *user_step]
    if ai_hinted_step:
        data["ai_hinted_steps"] = [*derivation.ai_hinted_steps, *ai_hinted_step]
    if not_yet_trusted:
        data["not_yet_trusted"] = [*derivation.not_yet_trusted, *not_yet_trusted]
    if next_action is not None:
        data["next_action"] = next_action
    if record_intensity is not None:
        data["record_intensity"] = record_intensity
    data["updated_at"] = now_utc()
    updated = DerivationRecord.model_validate(data)
    save_yaml_model(path, updated)
    event_type = "derivation_status_changed" if status is not None and status != derivation.status else "record_updated"
    _log_record_event(event_type, "derivations", updated, f"Updated derivation: {updated.topic}", before=before)
    console.print(f"Updated derivation {derivation_id}")


@session_app.command("new")
def session_new(
    topic: str,
    goal_id: str | None = typer.Option(None, "--goal-id"),
    mode: str = typer.Option("study", "--mode"),
    learning_state: str | None = typer.Option(None, "--learning-state"),
    method_used: list[str] | None = typer.Option(None, "--method-used"),
    reference_used: list[str] | None = typer.Option(None, "--reference-used"),
    provisional_understanding: str = typer.Option("", "--provisional-understanding"),
    test_mode_triggered: bool = typer.Option(False, "--test-mode-triggered"),
    reference_added: list[str] | None = typer.Option(None, "--reference-added"),
) -> None:
    goal = _require_goal(goal_id)
    session = SessionFootprint(
        id=new_id("session"),
        goal_id=goal.id,
        topic=topic,
        mode=mode,
        learning_state=learning_state,
        methods_used=method_used or [],
        references_used=reference_used or [],
        provisional_understanding=provisional_understanding,
        test_mode_triggered=test_mode_triggered,
        references_added=reference_added or [],
    )
    path = _root() / "data" / "sessions" / f"{session.id}.md"
    save_session(path, session)
    _log_record_event("session_created", "sessions", session, f"Created session: {session.topic}")
    console.print(f"Created session {session.id}: {path}")


@session_app.command("list")
def session_list() -> None:
    table = Table("ID", "Topic", "Mode", "Created")
    for _, session, _ in list_sessions(_root()):
        table.add_row(session.id, session.topic, session.mode, session.created_at.isoformat())
    console.print(table)


@session_app.command("show")
def session_show(session_id: str) -> None:
    path = _root() / "data" / "sessions" / f"{session_id}.md"
    session, body = load_session(path)
    _print_model(session)
    for section, content in body.items():
        console.print(f"\n[bold]{section}[/bold]\n{content}")


@reference_app.command("add")
def reference_add(
    title: str = typer.Option(..., "--title"),
    authors_or_source: str = typer.Option("", "--authors-or-source"),
    reference_type: str = typer.Option("other", "--reference-type"),
    path_or_url: str = typer.Option("", "--path-or-url"),
    topic: list[str] | None = typer.Option(None, "--topic"),
    relevance_to_goal: str = typer.Option("", "--relevance-to-goal"),
    usage_stage: str = typer.Option("initial_map", "--usage-stage"),
    reading_status: str = typer.Option("unread", "--reading-status"),
    notes: str = typer.Option("", "--notes"),
    goal_id: str | None = typer.Option(None, "--goal-id"),
) -> None:
    goal = _require_goal(goal_id)
    reference = ReferenceRecord(
        id=new_id("ref"),
        goal_id=goal.id,
        title=title,
        authors_or_source=authors_or_source,
        reference_type=reference_type,
        path_or_url=path_or_url,
        topics=topic or [],
        relevance_to_goal=relevance_to_goal,
        usage_stage=usage_stage,
        reading_status=reading_status,
        notes=notes,
    )
    path = save_record(_root(), "references", reference)
    _log_record_event("reference_added", "references", reference, f"Added reference: {reference.title}")
    console.print(f"Created reference {reference.id}: {path}")


@reference_app.command("list")
def reference_list() -> None:
    records = list_yaml_records(_root(), "references", ReferenceRecord)
    table = Table("ID", "Title", "Type", "Stage", "Status")
    for record in records:
        table.add_row(record.id, record.title, record.reference_type, record.usage_stage, record.reading_status)
    console.print(table)


@reference_app.command("show")
def reference_show(reference_id: str) -> None:
    _print_model(load_yaml_model(_root() / "data" / "references" / f"{reference_id}.yaml", ReferenceRecord))


@reference_app.command("update")
def reference_update(
    reference_id: str,
    reading_status: str | None = typer.Option(None, "--reading-status"),
    usage_stage: str | None = typer.Option(None, "--usage-stage"),
    notes: str | None = typer.Option(None, "--notes"),
    relevance_to_goal: str | None = typer.Option(None, "--relevance-to-goal"),
) -> None:
    path = _root() / "data" / "references" / f"{reference_id}.yaml"
    reference = load_yaml_model(path, ReferenceRecord)
    before = reference.model_dump(mode="json")
    data = reference.model_dump()
    for key, value in {
        "reading_status": reading_status,
        "usage_stage": usage_stage,
        "notes": notes,
        "relevance_to_goal": relevance_to_goal,
    }.items():
        if value is not None:
            data[key] = value
    data["updated_at"] = now_utc()
    updated = ReferenceRecord.model_validate(data)
    save_yaml_model(path, updated)
    _log_record_event("record_updated", "references", updated, f"Updated reference: {updated.title}", before=before)
    console.print(f"Updated reference {reference_id}")


@policy_app.command("add")
def policy_add(
    title: str = typer.Option(..., "--title"),
    description: str = typer.Option("", "--description"),
    a_zone_criterion: list[str] | None = typer.Option(None, "--a-zone-criterion"),
    b_zone_criterion: list[str] | None = typer.Option(None, "--b-zone-criterion"),
    c_zone_criterion: list[str] | None = typer.Option(None, "--c-zone-criterion"),
    core_tool_criterion: list[str] | None = typer.Option(None, "--core-tool-criterion"),
    non_core_tool_criterion: list[str] | None = typer.Option(None, "--non-core-tool-criterion"),
    test_mode_criterion: list[str] | None = typer.Option(None, "--test-mode-criterion"),
    upgrade_trigger: list[str] | None = typer.Option(None, "--upgrade-trigger"),
    downgrade_trigger: list[str] | None = typer.Option(None, "--downgrade-trigger"),
    revisit_trigger: list[str] | None = typer.Option(None, "--revisit-trigger"),
    example: list[str] | None = typer.Option(None, "--example"),
    goal_id: str | None = typer.Option(None, "--goal-id"),
) -> None:
    goal = _require_goal(goal_id)
    policy = ClassificationPolicy(
        id=new_id("policy"),
        goal_id=goal.id,
        title=title,
        description=description,
        a_zone_criteria=a_zone_criterion or [],
        b_zone_criteria=b_zone_criterion or [],
        c_zone_criteria=c_zone_criterion or [],
        core_tool_criteria=core_tool_criterion or [],
        non_core_tool_criteria=non_core_tool_criterion or [],
        test_mode_criteria=test_mode_criterion or [],
        upgrade_triggers=upgrade_trigger or [],
        downgrade_triggers=downgrade_trigger or [],
        revisit_triggers=revisit_trigger or [],
        examples_optional=example or [],
    )
    path = save_record(_root(), "policies", policy)
    _log_record_event("record_created", "policies", policy, f"Created classification policy: {policy.title}")
    console.print(f"Created policy {policy.id}: {path}")


@policy_app.command("list")
def policy_list() -> None:
    records = list_yaml_records(_root(), "policies", ClassificationPolicy)
    table = Table("ID", "Title", "Goal", "Updated")
    for record in records:
        table.add_row(record.id, record.title, record.goal_id, record.updated_at.isoformat())
    console.print(table)


@policy_app.command("show")
def policy_show(policy_id: str) -> None:
    _print_model(load_yaml_model(_root() / "data" / "policies" / f"{policy_id}.yaml", ClassificationPolicy))


@policy_app.command("update")
def policy_update(
    policy_id: str,
    title: str | None = typer.Option(None, "--title"),
    description: str | None = typer.Option(None, "--description"),
    a_zone_criterion: list[str] | None = typer.Option(None, "--a-zone-criterion"),
    b_zone_criterion: list[str] | None = typer.Option(None, "--b-zone-criterion"),
    c_zone_criterion: list[str] | None = typer.Option(None, "--c-zone-criterion"),
    upgrade_trigger: list[str] | None = typer.Option(None, "--upgrade-trigger"),
    downgrade_trigger: list[str] | None = typer.Option(None, "--downgrade-trigger"),
    revisit_trigger: list[str] | None = typer.Option(None, "--revisit-trigger"),
) -> None:
    path = _root() / "data" / "policies" / f"{policy_id}.yaml"
    record = load_yaml_model(path, ClassificationPolicy)
    before = record.model_dump(mode="json")
    data = record.model_dump()
    if title is not None:
        data["title"] = title
    if description is not None:
        data["description"] = description
    if a_zone_criterion:
        data["a_zone_criteria"] = [*record.a_zone_criteria, *a_zone_criterion]
    if b_zone_criterion:
        data["b_zone_criteria"] = [*record.b_zone_criteria, *b_zone_criterion]
    if c_zone_criterion:
        data["c_zone_criteria"] = [*record.c_zone_criteria, *c_zone_criterion]
    if upgrade_trigger:
        data["upgrade_triggers"] = [*record.upgrade_triggers, *upgrade_trigger]
    if downgrade_trigger:
        data["downgrade_triggers"] = [*record.downgrade_triggers, *downgrade_trigger]
    if revisit_trigger:
        data["revisit_triggers"] = [*record.revisit_triggers, *revisit_trigger]
    data["updated_at"] = now_utc()
    updated = ClassificationPolicy.model_validate(data)
    save_yaml_model(path, updated)
    _log_record_event("record_updated", "policies", updated, f"Updated classification policy: {updated.title}", before=before)
    console.print(f"Updated policy {policy_id}")


@visual_app.command("add")
def visual_add(
    topic: str = typer.Option(..., "--topic"),
    title: str = typer.Option(..., "--title"),
    visual_type: str = typer.Option("other", "--visual-type"),
    source_priority: str = typer.Option("reliable_web", "--source-priority"),
    source_url_or_path: str = typer.Option("", "--source-url-or-path"),
    source_detail: str = typer.Option("", "--source-detail"),
    reliability: str = typer.Option("medium", "--reliability"),
    usage: str = typer.Option("explanation", "--usage"),
    why_needed: str = typer.Option("", "--why-needed"),
    related_record_id: list[str] | None = typer.Option(None, "--related-record-id"),
    copyright_note: str = typer.Option("", "--copyright-note"),
    goal_id: str | None = typer.Option(None, "--goal-id"),
) -> None:
    goal = _require_goal(goal_id)
    visual = VisualResourceRecord(
        id=new_id("visual"),
        goal_id=goal.id,
        topic=topic,
        title=title,
        visual_type=visual_type,
        source_priority=source_priority,
        source_url_or_path=source_url_or_path,
        source_detail=source_detail,
        reliability=reliability,
        usage=usage,
        why_needed=why_needed,
        related_record_ids=related_record_id or [],
        copyright_note=copyright_note,
    )
    path = save_record(_root(), "visuals", visual)
    _log_record_event("record_created", "visuals", visual, f"Created visual resource: {visual.title}")
    console.print(f"Created visual resource {visual.id}: {path}")


@visual_app.command("list")
def visual_list() -> None:
    records = list_yaml_records(_root(), "visuals", VisualResourceRecord)
    table = Table("ID", "Topic", "Title", "Type", "Usage")
    for record in records:
        table.add_row(record.id, record.topic, record.title, record.visual_type, record.usage)
    console.print(table)


@visual_app.command("show")
def visual_show(visual_id: str) -> None:
    _print_model(load_yaml_model(_root() / "data" / "visuals" / f"{visual_id}.yaml", VisualResourceRecord))


@visual_app.command("update")
def visual_update(
    visual_id: str,
    reliability: str | None = typer.Option(None, "--reliability"),
    usage: str | None = typer.Option(None, "--usage"),
    why_needed: str | None = typer.Option(None, "--why-needed"),
    source_url_or_path: str | None = typer.Option(None, "--source-url-or-path"),
    copyright_note: str | None = typer.Option(None, "--copyright-note"),
) -> None:
    path = _root() / "data" / "visuals" / f"{visual_id}.yaml"
    record = load_yaml_model(path, VisualResourceRecord)
    before = record.model_dump(mode="json")
    data = record.model_dump()
    for key, value in {
        "reliability": reliability,
        "usage": usage,
        "why_needed": why_needed,
        "source_url_or_path": source_url_or_path,
        "copyright_note": copyright_note,
    }.items():
        if value is not None:
            data[key] = value
    data["updated_at"] = now_utc()
    updated = VisualResourceRecord.model_validate(data)
    save_yaml_model(path, updated)
    _log_record_event("record_updated", "visuals", updated, f"Updated visual resource: {updated.title}", before=before)
    console.print(f"Updated visual resource {visual_id}")


@distinction_app.command("add")
def distinction_add(
    title: str,
    concept: list[str] | None = typer.Option(None, "--concept"),
    confusion_statement: str = typer.Option("", "--confusion-statement"),
    status: str = typer.Option("needs_distinction", "--status"),
    internalization_target: str = typer.Option("none", "--internalization-target"),
    record_intensity: str = typer.Option("light", "--record-intensity"),
    next_action: str = typer.Option("", "--next-action"),
    goal_id: str | None = typer.Option(None, "--goal-id"),
) -> None:
    goal = _require_goal(goal_id)
    now = now_utc()
    record = DistinctionRecord(
        id=new_id("dist"),
        goal_id=goal.id,
        title=title,
        concepts=concept or [],
        confusion_statement=confusion_statement,
        status=status,
        internalization_target=internalization_target,
        record_intensity=record_intensity,
        first_confused_at=now,
        last_confused_at=now,
        confusion_count=1 if confusion_statement else 0,
        next_action=next_action,
    )
    path = save_record(_root(), "distinctions", record)
    _log_record_event("record_created", "distinctions", record, f"Created distinction: {record.title}")
    if confusion_statement:
        _log_record_event("confusion_recorded", "distinctions", record, f"Recorded confusion: {record.confusion_statement}")
    console.print(f"Created distinction {record.id}: {path}")


@distinction_app.command("list")
def distinction_list() -> None:
    records = list_yaml_records(_root(), "distinctions", DistinctionRecord)
    table = Table("ID", "Title", "Status", "Target", "Confusions")
    for record in records:
        table.add_row(record.id, record.title, record.status, record.internalization_target, str(record.confusion_count))
    console.print(table)


@distinction_app.command("show")
def distinction_show(distinction_id: str) -> None:
    _print_model(load_yaml_model(_root() / "data" / "distinctions" / f"{distinction_id}.yaml", DistinctionRecord))


@distinction_app.command("update")
def distinction_update(
    distinction_id: str,
    status: str | None = typer.Option(None, "--status"),
    shared_feature: list[str] | None = typer.Option(None, "--shared-feature"),
    criterion: list[str] | None = typer.Option(None, "--criterion"),
    minimal_example: list[str] | None = typer.Option(None, "--minimal-example"),
    boundary_case: list[str] | None = typer.Option(None, "--boundary-case"),
    common_misconception: list[str] | None = typer.Option(None, "--common-misconception"),
    next_action: str | None = typer.Option(None, "--next-action"),
    next_distinction_test_at: str | None = typer.Option(None, "--next-distinction-test-at"),
) -> None:
    path = _root() / "data" / "distinctions" / f"{distinction_id}.yaml"
    record = load_yaml_model(path, DistinctionRecord)
    before = record.model_dump(mode="json")
    data = record.model_dump()
    if status is not None:
        data["status"] = status
        if status in {"clear", "resolved", "partially_clear"}:
            data["last_distinguished_at"] = now_utc()
    if shared_feature:
        data["shared_features"] = [*record.shared_features, *shared_feature]
    if criterion:
        data["distinguishing_criteria"] = [*record.distinguishing_criteria, *criterion]
    if minimal_example:
        data["minimal_examples"] = [*record.minimal_examples, *minimal_example]
    if boundary_case:
        data["boundary_cases"] = [*record.boundary_cases, *boundary_case]
    if common_misconception:
        data["common_misconceptions"] = [*record.common_misconceptions, *common_misconception]
    if next_action is not None:
        data["next_action"] = next_action
    if next_distinction_test_at is not None:
        data["next_distinction_test_at"] = next_distinction_test_at
    data["updated_at"] = now_utc()
    updated = DistinctionRecord.model_validate(data)
    save_yaml_model(path, updated)
    event_type = "distinction_status_changed" if status is not None and status != record.status else "record_updated"
    _log_record_event(event_type, "distinctions", updated, f"Updated distinction: {updated.title}", before=before)
    if status == "resolved":
        _log_record_event("confusion_resolved", "distinctions", updated, f"Resolved confusion: {updated.title}")
    console.print(f"Updated distinction {distinction_id}")


@misconception_app.command("add")
def misconception_add(
    statement: str,
    why_wrong: str = typer.Option("", "--why-wrong"),
    corrected_view: str = typer.Option("", "--corrected-view"),
    related_topic: list[str] | None = typer.Option(None, "--related-topic"),
    severity: str = typer.Option("important", "--severity"),
    status: str = typer.Option("active", "--status"),
    next_action: str = typer.Option("", "--next-action"),
    goal_id: str | None = typer.Option(None, "--goal-id"),
) -> None:
    goal = _require_goal(goal_id)
    now = now_utc()
    record = MisconceptionRecord(
        id=new_id("misc"),
        goal_id=goal.id,
        statement=statement,
        why_wrong=why_wrong,
        corrected_view=corrected_view,
        related_topics=related_topic or [],
        severity=severity,
        status=status,
        first_seen_at=now,
        last_seen_at=now,
        recurrence_count=1,
        next_action=next_action,
    )
    path = save_record(_root(), "misconceptions", record)
    _log_record_event("record_created", "misconceptions", record, f"Created misconception: {record.statement}")
    console.print(f"Created misconception {record.id}: {path}")


@misconception_app.command("list")
def misconception_list() -> None:
    records = list_yaml_records(_root(), "misconceptions", MisconceptionRecord)
    table = Table("ID", "Status", "Severity", "Recurrences", "Statement")
    for record in records:
        table.add_row(record.id, record.status, record.severity, str(record.recurrence_count), record.statement)
    console.print(table)


@misconception_app.command("show")
def misconception_show(misconception_id: str) -> None:
    _print_model(load_yaml_model(_root() / "data" / "misconceptions" / f"{misconception_id}.yaml", MisconceptionRecord))


@misconception_app.command("update")
def misconception_update(
    misconception_id: str,
    status: str | None = typer.Option(None, "--status"),
    why_wrong: str | None = typer.Option(None, "--why-wrong"),
    corrected_view: str | None = typer.Option(None, "--corrected-view"),
    recur: bool = typer.Option(False, "--recur"),
    next_action: str | None = typer.Option(None, "--next-action"),
) -> None:
    path = _root() / "data" / "misconceptions" / f"{misconception_id}.yaml"
    record = load_yaml_model(path, MisconceptionRecord)
    before = record.model_dump(mode="json")
    data = record.model_dump()
    if status is not None:
        data["status"] = status
        if status == "corrected":
            data["corrected_at"] = now_utc()
    if why_wrong is not None:
        data["why_wrong"] = why_wrong
    if corrected_view is not None:
        data["corrected_view"] = corrected_view
    if recur:
        data["recurrence_count"] = record.recurrence_count + 1
        data["last_seen_at"] = now_utc()
        data["status"] = "recurring"
    if next_action is not None:
        data["next_action"] = next_action
    data["updated_at"] = now_utc()
    updated = MisconceptionRecord.model_validate(data)
    save_yaml_model(path, updated)
    _log_record_event("confusion_recorded" if recur else "record_updated", "misconceptions", updated, f"Updated misconception: {updated.statement}", before=before)
    console.print(f"Updated misconception {misconception_id}")


@cluster_app.command("add")
def cluster_add(
    title: str,
    core_question: str = typer.Option("", "--core-question"),
    concept: list[str] | None = typer.Option(None, "--concept"),
    current_status: str = typer.Option("provisional", "--current-status"),
    reason: str = typer.Option("", "--reason"),
    next_action: str = typer.Option("", "--next-action"),
    goal_id: str | None = typer.Option(None, "--goal-id"),
) -> None:
    goal = _require_goal(goal_id)
    record = ConceptClusterRecord(
        id=new_id("cluster"),
        goal_id=goal.id,
        title=title,
        core_question=core_question,
        concepts=concept or [],
        current_status=current_status,
        reason=reason,
        next_action=next_action,
    )
    path = save_record(_root(), "clusters", record)
    _log_record_event("record_created", "clusters", record, f"Created concept cluster: {record.title}")
    console.print(f"Created cluster {record.id}: {path}")


@cluster_app.command("list")
def cluster_list() -> None:
    records = list_yaml_records(_root(), "clusters", ConceptClusterRecord)
    table = Table("ID", "Title", "Status", "Concepts")
    for record in records:
        table.add_row(record.id, record.title, record.current_status, ", ".join(record.concepts))
    console.print(table)


@cluster_app.command("show")
def cluster_show(cluster_id: str) -> None:
    _print_model(load_yaml_model(_root() / "data" / "clusters" / f"{cluster_id}.yaml", ConceptClusterRecord))


@cluster_app.command("update")
def cluster_update(
    cluster_id: str,
    current_status: str | None = typer.Option(None, "--current-status"),
    reason: str | None = typer.Option(None, "--reason"),
    next_action: str | None = typer.Option(None, "--next-action"),
) -> None:
    path = _root() / "data" / "clusters" / f"{cluster_id}.yaml"
    record = load_yaml_model(path, ConceptClusterRecord)
    before = record.model_dump(mode="json")
    data = record.model_dump()
    for key, value in {"current_status": current_status, "reason": reason, "next_action": next_action}.items():
        if value is not None:
            data[key] = value
    data["updated_at"] = now_utc()
    updated = ConceptClusterRecord.model_validate(data)
    save_yaml_model(path, updated)
    _log_record_event("record_updated", "clusters", updated, f"Updated concept cluster: {updated.title}", before=before)
    console.print(f"Updated cluster {cluster_id}")


@event_app.command("list")
def event_list(month: str | None = typer.Option(None, "--month")) -> None:
    table = Table("ID", "Time", "Type", "Target", "Summary")
    for event in load_events(month, root=_root()):
        table.add_row(event.id, event.timestamp_local.isoformat(), event.event_type, event.target_id, event.summary)
    console.print(table)


@event_app.command("show")
def event_show(event_id: str) -> None:
    for event in load_events(root=_root()):
        if event.id == event_id:
            _print_model(event)
            return
    raise typer.BadParameter(f"Event not found: {event_id}")


@event_app.command("timeline")
def event_timeline(target_id: str) -> None:
    for line in build_timeline(target_id, root=_root()):
        console.print(f"- {line}")


@method_app.command("suggest")
def method_suggest(
    state: str = typer.Option(..., "--state"),
    topic: str | None = typer.Option(None, "--topic"),
    goal_id: str | None = typer.Option(None, "--goal-id"),
) -> None:
    _require_goal(goal_id)
    recommendation = recommend_methods(state)
    target = f" for {topic}" if topic else ""
    console.print(f"Suggested methods{target}: {', '.join(recommendation.actions)}")
    console.print(recommendation.rationale)


@test_app.command("add")
def test_add(
    topic: str,
    goal_id: str | None = typer.Option(None, "--goal-id"),
    position_id: str | None = typer.Option(None, "--position-id"),
    test_type: str = typer.Option("mixed", "--test-type"),
    status: str = typer.Option("planned", "--status"),
    internalization_target: str = typer.Option("A3", "--internalization-target"),
    prompt: str | None = typer.Option(None, "--prompt"),
) -> None:
    goal = _require_goal(goal_id)
    record = TestRecord(
        id=new_id("test"),
        goal_id=goal.id,
        topic=topic,
        position_id=position_id,
        test_type=test_type,
        status=status,
        internalization_target=internalization_target,
        prompt=prompt or test_topic_prompt(goal, topic),
    )
    path = save_record(_root(), "tests", record)
    _log_record_event("record_created", "tests", record, f"Created test record: {record.topic}")
    console.print(f"Created test record {record.id}: {path}")


@test_app.command("list")
def test_list() -> None:
    records = list_yaml_records(_root(), "tests", TestRecord)
    table = Table("ID", "Topic", "Type", "Status", "Target")
    for record in records:
        table.add_row(record.id, record.topic, record.test_type, record.status, record.internalization_target)
    console.print(table)


@test_app.command("show")
def test_show(test_id: str) -> None:
    _print_model(load_yaml_model(_root() / "data" / "tests" / f"{test_id}.yaml", TestRecord))


@test_app.command("update")
def test_update(
    test_id: str,
    status: str | None = typer.Option(None, "--status"),
    learner_answer: str | None = typer.Option(None, "--learner-answer"),
    feedback: str | None = typer.Option(None, "--feedback"),
    next_retest_at: str | None = typer.Option(None, "--next-retest-at"),
) -> None:
    path = _root() / "data" / "tests" / f"{test_id}.yaml"
    record = load_yaml_model(path, TestRecord)
    before = record.model_dump(mode="json")
    data = record.model_dump()
    for key, value in {
        "status": status,
        "learner_answer": learner_answer,
        "feedback": feedback,
        "next_retest_at": next_retest_at,
    }.items():
        if value is not None:
            data[key] = value
    data["updated_at"] = now_utc()
    updated = TestRecord.model_validate(data)
    save_yaml_model(path, updated)
    event_type = "test_status_changed" if status is not None and status != record.status else "record_updated"
    _log_record_event(event_type, "tests", updated, f"Updated test record: {updated.topic}", before=before)
    console.print(f"Updated test record {test_id}")


@test_app.command("suggest")
def test_suggest() -> None:
    suggestions = suggest_tests(_root())
    if not suggestions:
        console.print("No test suggestions found.")
        return
    for suggestion in suggestions:
        console.print(f"- {suggestion}")


@prompt_app.command("dynamic-positioning")
def prompt_dynamic_positioning(
    knowledge_point: str,
    goal_id: str | None = typer.Option(None, "--goal-id"),
    current_context: str | None = typer.Option(None, "--current-context"),
    policy_id: str | None = typer.Option(None, "--policy"),
) -> None:
    policy = load_yaml_model(_root() / "data" / "policies" / f"{policy_id}.yaml", ClassificationPolicy) if policy_id else None
    console.print(dynamic_positioning_prompt(_require_goal(goal_id), knowledge_point, current_context, policy=policy))


@prompt_app.command("goal-intake")
def prompt_goal_intake(raw_goal: str | None = typer.Option(None, "--raw-goal")) -> None:
    console.print(goal_intake_prompt(raw_goal))


@prompt_app.command("deep-research")
def prompt_deep_research(goal_id: str | None = typer.Argument(None)) -> None:
    console.print(deep_research_prompt(_require_goal(goal_id)))


@prompt_app.command("extract-references")
def prompt_extract_references(import_id: str) -> None:
    path = find_research_import(_root(), import_id)
    console.print(extract_references_prompt(path.stem, path.read_text(encoding="utf-8")))


@prompt_app.command("extract-positioning-from-research")
def prompt_extract_positioning_from_research(import_id: str) -> None:
    path = find_research_import(_root(), import_id)
    console.print(extract_positioning_from_research_prompt(path.stem, path.read_text(encoding="utf-8")))


@prompt_app.command("method-router")
def prompt_method_router(
    state: str = typer.Option(..., "--state"),
    topic: str | None = typer.Option(None, "--topic"),
    goal_id: str | None = typer.Option(None, "--goal-id"),
    with_context: bool = typer.Option(False, "--with-context"),
    budget: str = typer.Option("medium", "--budget"),
) -> None:
    goal = _require_goal(goal_id)
    actions = recommend_methods(state).actions
    _print_prompt(
        method_router_prompt(goal, state, topic, actions),
        with_context=with_context,
        task_type="method_routing",
        topic=topic,
        goal_id=goal.id,
        budget=budget,
    )


@prompt_app.command("verify-claim")
def prompt_verify_claim(
    claim_id: str,
    with_context: bool = typer.Option(False, "--with-context"),
    budget: str = typer.Option("medium", "--budget"),
) -> None:
    claim = load_yaml_model(_root() / "data" / "claims" / f"{claim_id}.yaml", ClaimRecord)
    _print_prompt(
        claim_verification_prompt(_require_goal(claim.goal_id), claim),
        with_context=with_context,
        task_type="verify_claim",
        record_id=claim.id,
        goal_id=claim.goal_id,
        budget=budget,
    )


@prompt_app.command("derivation")
def prompt_derivation(
    derivation_id: str,
    with_context: bool = typer.Option(False, "--with-context"),
    budget: str = typer.Option("medium", "--budget"),
) -> None:
    derivation = load_yaml_model(_root() / "data" / "derivations" / f"{derivation_id}.yaml", DerivationRecord)
    _print_prompt(
        derivation_guidance_prompt(_require_goal(derivation.goal_id), derivation),
        with_context=with_context,
        task_type="derivation_guidance",
        record_id=derivation.id,
        topic=derivation.topic,
        goal_id=derivation.goal_id,
        budget=budget,
    )


@prompt_app.command("distinguish")
def prompt_distinguish(
    distinction_id: str,
    with_context: bool = typer.Option(False, "--with-context"),
    budget: str = typer.Option("medium", "--budget"),
) -> None:
    distinction = load_yaml_model(_root() / "data" / "distinctions" / f"{distinction_id}.yaml", DistinctionRecord)
    _print_prompt(
        distinction_prompt(_require_goal(distinction.goal_id), distinction),
        with_context=with_context,
        task_type="distinction",
        record_id=distinction.id,
        topic=distinction.title,
        goal_id=distinction.goal_id,
        budget=budget,
    )


@prompt_app.command("distinction-test")
def prompt_distinction_test(distinction_id: str) -> None:
    distinction = load_yaml_model(_root() / "data" / "distinctions" / f"{distinction_id}.yaml", DistinctionRecord)
    console.print(distinction_test_prompt(_require_goal(distinction.goal_id), distinction))


@prompt_app.command("misconception-correction")
def prompt_misconception_correction(
    misconception_id: str,
    with_context: bool = typer.Option(False, "--with-context"),
    budget: str = typer.Option("medium", "--budget"),
) -> None:
    misconception = load_yaml_model(_root() / "data" / "misconceptions" / f"{misconception_id}.yaml", MisconceptionRecord)
    _print_prompt(
        misconception_correction_prompt(_require_goal(misconception.goal_id), misconception),
        with_context=with_context,
        task_type="misconception",
        record_id=misconception.id,
        topic=misconception.related_topics[0] if misconception.related_topics else None,
        goal_id=misconception.goal_id,
        budget=budget,
    )


@prompt_app.command("temporal-review")
def prompt_temporal_review(target_id: str) -> None:
    console.print(temporal_review_prompt(build_timeline(target_id, root=_root())))


@prompt_app.command("socratic")
def prompt_socratic(topic: str, goal_id: str | None = typer.Option(None, "--goal-id")) -> None:
    console.print(socratic_drill_prompt(_require_goal(goal_id), topic))


@prompt_app.command("test-topic")
def prompt_test_topic(
    topic: str,
    goal_id: str | None = typer.Option(None, "--goal-id"),
    with_context: bool = typer.Option(False, "--with-context"),
    budget: str = typer.Option("medium", "--budget"),
) -> None:
    goal = _require_goal(goal_id)
    _print_prompt(
        test_topic_prompt(goal, topic),
        with_context=with_context,
        task_type="test_topic",
        topic=topic,
        goal_id=goal.id,
        budget=budget,
    )


@prompt_app.command("test-record")
def prompt_test_record(test_id: str) -> None:
    record = load_yaml_model(_root() / "data" / "tests" / f"{test_id}.yaml", TestRecord)
    console.print(test_record_prompt(_require_goal(record.goal_id), record))


@prompt_app.command("review")
def prompt_review(
    kind: str = typer.Argument("weekly"),
    with_context: bool = typer.Option(False, "--with-context"),
    budget: str = typer.Option("medium", "--budget"),
) -> None:
    if kind != "weekly":
        raise typer.BadParameter("Only weekly review prompts are supported.")
    _print_prompt(
        weekly_review_prompt(),
        with_context=with_context,
        task_type="weekly_review",
        budget=budget,
    )


@prompt_app.command("refine-policy")
def prompt_refine_policy(goal_id: str | None = typer.Argument(None)) -> None:
    console.print(refine_policy_prompt(_require_goal(goal_id)))


@prompt_app.command("classify-with-policy")
def prompt_classify_with_policy(
    knowledge_point: str,
    policy_id: str = typer.Option(..., "--policy"),
    goal_id: str | None = typer.Option(None, "--goal-id"),
    current_user_state: str | None = typer.Option(None, "--current-user-state"),
    reference_hints: str | None = typer.Option(None, "--reference-hints"),
    deep_research_hints: str | None = typer.Option(None, "--deep-research-hints"),
) -> None:
    policy = load_yaml_model(_root() / "data" / "policies" / f"{policy_id}.yaml", ClassificationPolicy)
    console.print(
        classify_with_policy_prompt(
            _require_goal(goal_id or policy.goal_id),
            knowledge_point,
            policy,
            current_user_state=current_user_state,
            reference_hints=reference_hints,
            deep_research_hints=deep_research_hints,
        )
    )


@prompt_app.command("visual-suggest")
def prompt_visual_suggest(topic: str = typer.Option(..., "--topic"), goal_id: str | None = typer.Option(None, "--goal-id")) -> None:
    console.print(visual_suggestion_prompt(_require_goal(goal_id), topic))


@prompt_app.command("visual-explain")
def prompt_visual_explain(visual_id: str) -> None:
    visual = load_yaml_model(_root() / "data" / "visuals" / f"{visual_id}.yaml", VisualResourceRecord)
    console.print(visual_explanation_prompt(_require_goal(visual.goal_id), visual))


@import_app.command("deep-research")
def import_deep_research(path_to_markdown: Path) -> None:
    timestamp = now_utc().strftime("%Y%m%d%H%M%S")
    path = copy_research_import(_root(), path_to_markdown, timestamp)
    console.print(f"Imported external suggestion file as {path}")


@review_app.command("weekly")
def review_weekly() -> None:
    path = generate_weekly_review(_root())
    console.print(f"Created weekly review: {path}")


@review_app.command("due")
def review_due() -> None:
    items = due_review_items(_root())
    if not items:
        console.print("No due review items found.")
        return
    for item in items:
        console.print(f"- {item}")


@review_app.command("timeline")
def review_timeline(target_id: str) -> None:
    for line in build_timeline(target_id, root=_root()):
        console.print(f"- {line}")


@index_app.command("refresh")
def index_refresh() -> None:
    paths = refresh_indexes(_root())
    console.print(f"Refreshed indexes under {paths.directory}")


@index_app.command("show")
def index_show() -> None:
    console.print(show_index(_root()))


@index_app.command("active-goal")
def index_active_goal() -> None:
    paths = refresh_indexes(_root())
    console.print(paths.active_goal_summary.read_text(encoding="utf-8"))


@index_app.command("open-loops")
def index_open_loops() -> None:
    paths = refresh_indexes(_root())
    console.print(paths.open_loops.read_text(encoding="utf-8"))


@index_app.command("recent")
def index_recent() -> None:
    paths = refresh_indexes(_root())
    console.print(paths.recent_activity.read_text(encoding="utf-8"))


@index_app.command("topic")
def index_topic(topic: str) -> None:
    console.print(topic_summary(_root(), topic))


@context_app.command("build")
def context_build(
    task: str = typer.Option(..., "--task"),
    record_id: str | None = typer.Option(None, "--id"),
    topic: str | None = typer.Option(None, "--topic"),
    goal_id: str | None = typer.Option(None, "--goal-id"),
    output: Path | None = typer.Option(None, "--output"),
    budget: str = typer.Option("medium", "--budget"),
) -> None:
    pack = build_context_pack(
        _root(),
        task_type=task,
        record_id=record_id,
        topic=topic,
        goal_id=goal_id,
        output=output,
        budget=budget,
    )
    console.print(f"Created context pack: {pack.path}")
    console.print(f"Size: {pack.size_bytes} bytes; records: {pack.record_count}")


@context_app.command("show")
def context_show(
    task: str = typer.Option(..., "--task"),
    record_id: str | None = typer.Option(None, "--id"),
    topic: str | None = typer.Option(None, "--topic"),
    goal_id: str | None = typer.Option(None, "--goal-id"),
    budget: str = typer.Option("medium", "--budget"),
) -> None:
    pack = build_context_pack(
        _root(),
        task_type=task,
        record_id=record_id,
        topic=topic,
        goal_id=goal_id,
        budget=budget,
    )
    console.print(pack.path.read_text(encoding="utf-8"))


@context_app.command("policy")
def context_policy() -> None:
    console.print(context_policy_text())


@provider_app.command("list")
def provider_list(config_path: Path | None = typer.Option(None, "--config")) -> None:
    config = _selected_config(config_path)
    table = Table("ID", "Type", "Default", "Model", "API Key Env", "Key Set", "Base URL")
    for item in configured_provider_summaries(config):
        table.add_row(
            str(item["id"]),
            str(item["type"]),
            str(item["is_default"]),
            str(item.get("default_model") or ""),
            str(item.get("api_key_env") or ""),
            str(item.get("api_key_present")),
            str(item.get("base_url") or ""),
        )
    if not config.providers:
        console.print("No providers configured. Prompt-only mode is available.")
        return
    console.print(table)


@provider_app.command("show")
def provider_show(provider_id: str, config_path: Path | None = typer.Option(None, "--config")) -> None:
    config = _selected_config(config_path)
    summary = public_config_summary(config)
    provider = next((item for item in summary["providers"] if item["id"] == provider_id), None)
    if provider is None:
        raise typer.BadParameter(f"Provider not configured: {provider_id}")
    console.print_json(data=provider)


@provider_app.command("test")
def provider_test(provider_id: str, config_path: Path | None = typer.Option(None, "--config")) -> None:
    config = _selected_config(config_path)
    try:
        provider = build_provider(config, provider_id)
        ok, message = provider.test_connection()
    except ProviderError as exc:
        ok, message = False, str(exc)
    console.print(message)
    if not ok:
        raise typer.Exit(1)


@ai_app.command("run-prompt")
def ai_run_prompt(
    provider_id: str = typer.Option(..., "--provider"),
    prompt_file: Path = typer.Option(..., "--prompt-file"),
    model: str | None = typer.Option(None, "--model"),
    yes: bool = typer.Option(False, "--yes", help="Skip interactive confirmation."),
    config_path: Path | None = typer.Option(None, "--config"),
) -> None:
    text = prompt_file.read_text(encoding="utf-8")
    _run_provider_text(
        provider_id=provider_id,
        text=text,
        prompt_type="prompt_file",
        prompt_file_path=prompt_file,
        model=model,
        yes=yes,
        config_path=config_path,
    )


@ai_app.command("run-context")
def ai_run_context(
    provider_id: str = typer.Option(..., "--provider"),
    context_pack: Path = typer.Option(..., "--context-pack"),
    model: str | None = typer.Option(None, "--model"),
    yes: bool = typer.Option(False, "--yes", help="Skip interactive confirmation."),
    config_path: Path | None = typer.Option(None, "--config"),
) -> None:
    text = context_pack.read_text(encoding="utf-8")
    _run_provider_text(
        provider_id=provider_id,
        text=text,
        prompt_type="context_pack",
        context_pack_path=context_pack,
        model=model,
        yes=yes,
        config_path=config_path,
    )


@ai_runs_app.command("list")
def ai_runs_list() -> None:
    table = Table("ID", "Provider", "Model", "Status", "Created")
    for item in list_ai_runs(_root()):
        table.add_row(
            str(item.get("id")),
            str(item.get("provider")),
            str(item.get("model")),
            str(item.get("user_review_status")),
            str(item.get("created_at")),
        )
    console.print(table)


@ai_runs_app.command("show")
def ai_runs_show(run_id: str) -> None:
    metadata, response = load_ai_run(_root(), run_id)
    console.print_json(data=metadata)
    console.print("\n[bold]Response[/bold]\n")
    console.print(response)


@ai_app.command("apply")
def ai_apply(run_id: str, target: str = typer.Option(..., "--target")) -> None:
    metadata, _ = load_ai_run(_root(), run_id)
    console.print(f"AI run {metadata['id']} is an artifact, not source of truth.")
    console.print(f"Review response manually, then update target record explicitly: {target}")
    console.print("Suggested workflow: inspect the response, copy only accepted fields, then run `learn validate`.")


ai_app.add_typer(ai_runs_app, name="runs")


@app.command("status")
def status() -> None:
    console.print(render_status(project_status(_root())))


@app.command("next")
def next_actions() -> None:
    actions = suggest_next_actions(_root())
    if not actions:
        console.print("No next actions found.")
        return
    for action in actions:
        console.print(f"- {action}")


@app.command("ui")
def ui(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8765, "--port"),
    dev: bool = typer.Option(False, "--dev", help="Start both the API server and Vite frontend dev server."),
) -> None:
    frontend_process: subprocess.Popen[bytes] | None = None
    if dev:
        frontend_process = start_frontend_dev_server(_root(), host, port)
        console.print("Frontend dev server: http://127.0.0.1:5173")
        console.print(f"Backend/API server: http://{host}:{port}")
    try:
        serve_ui(_root(), host=host, port=port)
    finally:
        if frontend_process is not None and frontend_process.poll() is None:
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend_process.kill()


def start_frontend_dev_server(root: Path, host: str, port: int) -> subprocess.Popen[bytes] | None:
    web_dir = root / "web"
    env = {
        **os.environ,
        "VITE_API_PROXY_TARGET": f"http://{host}:{port}",
    }
    try:
        return subprocess.Popen(["npm", "run", "dev"], cwd=web_dir, env=env)
    except FileNotFoundError:
        console.print("[yellow]npm was not found; API/static server will still start.[/yellow]")
        return None


@app.command("doctor")
def doctor() -> None:
    table = Table("Check", "OK", "Detail")
    ok = True
    for check in run_doctor(_root()):
        ok = ok and check.ok
        table.add_row(check.name, "yes" if check.ok else "no", check.detail)
    console.print(table)
    if not ok:
        raise typer.Exit(1)


@app.command("validate")
def validate() -> None:
    report = validate_project(_root())
    if report.ok:
        console.print("Validation passed.")
        raise typer.Exit(0)
    for error in report.errors:
        console.print(f"[red]ERROR[/red] {error}")
    raise typer.Exit(1)


app.add_typer(goal_app, name="goal")
app.add_typer(position_app, name="position")
app.add_typer(claim_app, name="claim")
app.add_typer(derivation_app, name="derivation")
app.add_typer(session_app, name="session")
app.add_typer(reference_app, name="reference")
app.add_typer(policy_app, name="policy")
app.add_typer(visual_app, name="visual")
app.add_typer(distinction_app, name="distinction")
app.add_typer(misconception_app, name="misconception")
app.add_typer(cluster_app, name="cluster")
app.add_typer(event_app, name="event")
app.add_typer(method_app, name="method")
app.add_typer(test_app, name="test")
app.add_typer(prompt_app, name="prompt")
app.add_typer(import_app, name="import")
app.add_typer(review_app, name="review")
app.add_typer(index_app, name="index")
app.add_typer(context_app, name="context")
app.add_typer(provider_app, name="provider")
app.add_typer(ai_app, name="ai")
