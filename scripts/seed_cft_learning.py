from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from ailearn.agents.contracts import StateWriterOutput
from ailearn.db.database import Database
from ailearn.db.repository import Repository
from ailearn.references.chunking import chunk_text


def seed_cft_learning(repository: Repository | None = None, database_url: str = "sqlite:///data/ai_learn_os.sqlite3") -> dict[str, Any]:
    """Create a focused local demo project for learning two-dimensional CFT."""
    repo = repository or _repository_from_url(database_url)
    existing = next((project for project in repo.list_projects() if project.get("name") == "我要学习 CFT"), None)
    if existing:
        return existing

    project = repo.create_project(
        {
            "name": "我要学习 CFT",
            "description": "我要学习 CFT",
            "mode": "course",
            "stage_goal": "先分清临界点、标度不变性、共形不变性和 CFT 描述之间的边界。",
            "current_focus": "二维 CFT 的学习入口：critical phenomena -> scaling limit -> conformal data。",
            "next_action": "用一个具体问题检验：二阶相变处一定是 CFT 吗？",
        }
    )
    repo.update_project(
        project["id"],
        {
            "description": "围绕二维共形场论建立可验证的学习状态：从临界现象、标度极限、Ising CFT、tricritical Ising CFT、minimal models 到 modular data 与任意子融合的连接。"
        },
    )
    _replace_goal_stack(repo, project["id"])
    _add_seed_reference(repo, project["id"])
    repo.apply_state_writer_output(project["id"], None, _seed_state_writer_output().model_dump(mode="json"))
    return project


def _repository_from_url(database_url: str) -> Repository:
    database = Database(database_url)
    database.init()
    return Repository(database)


def _replace_goal_stack(repo: Repository, project_id: str) -> None:
    repo.create_goal_stack(
        project_id,
        {
            "main_goal": "我要学习 CFT",
            "stage_goal": "建立从临界现象到二维 CFT 的第一层概念边界。",
            "transfer_goal": "能把 Ising / tricritical Ising / minimal models 的例子迁移到新模型判断。",
            "external_goal": "为后续阅读 CFT 教材、临界格点模型和拓扑相相关论文做准备。",
            "conflict_goal": "避免把“出现在临界点附近的有效描述”误记成“所有临界点都自动是 CFT”。",
            "current_focus": "critical point vs scaling limit vs conformal field theory",
            "next_action": "比较 Ising CFT 与 tricritical Ising CFT 的数据和物理含义。",
            "version": 2,
        },
    )


def _add_seed_reference(repo: Repository, project_id: str) -> None:
    text = """
二维共形场论可以作为某些二维临界系统的连续极限描述。学习时应区分三个层次：
第一，物理系统是否处在临界点；第二，标度极限是否存在并具有足够强的对称性；
第三，是否能用 CFT 的局域算符、共形权重、OPE、central charge 与 modular data 来组织可观测量。

Ising CFT 是 minimal model 的核心例子之一，常用于连接二维 Ising 模型临界点、spin operator、
energy operator 与有限大小标度。Tricritical Ising CFT 则对应不同的 universality class；
它不是 Ising CFT 的简单别名，而是具有不同 central charge、算符谱和相关临界指数的数据结构。

对学习者来说，CFT 的关键不是背一个百科定义，而是建立可检验边界：什么时候 CFT 是有效描述，
哪些结论依赖二维、局域性、幺正性、旋转/洛伦兹不变性或标度不变性增强，哪些只是启发式类比。
""".strip()
    repo.add_reference(
        project_id,
        {
            "title": "CFT focused seed note",
            "source_type": "manual",
            "reliability_level": "medium",
            "scope": "Focused local demo reference for CFT learning-state behavior.",
            "metadata": {"copyright": "original seed text", "topic": "two-dimensional CFT"},
            "chunks": chunk_text(text, chunk_size=700),
        },
    )


def _seed_state_writer_output() -> StateWriterOutput:
    scheduled = (datetime.now(UTC) + timedelta(days=2)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return StateWriterOutput.model_validate(
        {
            "new_claims": [
                {
                    "original_statement": "我要学习 CFT，并理解它与临界现象的关系。",
                    "normalized_statement": "Learner wants to study CFT through the boundary between critical phenomena and conformal descriptions.",
                    "related_concept": "CFT learning goal",
                    "epistemic_status": "learning_strategy",
                    "confidence": 0.8,
                    "correction": None,
                }
            ],
            "updated_claims": [],
            "new_distinctions": [
                {
                    "concept_a": "临界点",
                    "concept_b": "CFT 描述",
                    "boundary": "临界点是物理系统的相变位置；CFT 是在满足额外条件时用于组织连续极限数据的理论描述。",
                    "common_confusion": "把“临界点常常由 CFT 描述”误读为“任何二阶相变处一定是 CFT”。",
                    "example": "Ising CFT 与 tricritical Ising CFT 属于不同 universality class，不能只因都与临界性有关就等同。",
                    "test_question": "哪些假设缺失时，临界系统不应被直接当作 CFT？",
                }
            ],
            "new_temporal_trace": {
                "event_type": "seed_project",
                "user_question": "我要学习 CFT",
                "system_response_summary": "Created a focused CFT learning seed with goal, reference chunks, distinctions, internalization target, derivation trust, and review trigger.",
                "state_change_summary": "Initialized learner-state records for the local demo project.",
                "next_step": "Ask whether every second-order phase transition is necessarily described by CFT.",
            },
            "knowledge_position_updates": [
                {
                    "concept": "CFT 与临界点的边界",
                    "layer": "no_ai_internalization",
                    "reason": "This boundary must be reconstructed without AI because it controls later reading and error correction.",
                    "target_level": "A3",
                    "current_level": "A1",
                    "review_needed": True,
                }
            ],
            "derivation_trust_updates": [
                {
                    "result_or_tool": "从有限大小标度读出 conformal data 的基本逻辑",
                    "assumptions": ["二维临界系统", "存在合理的连续极限", "可使用 CFT 数据组织谱和关联函数"],
                    "key_steps": ["区分格点模型与连续极限", "标出 universal data", "检查哪些步骤由教材/论文支持"],
                    "done_by_user": [],
                    "hinted_by_ai": ["Seed project records the scaffold only."],
                    "untrusted_steps": ["Learner has not yet reconstructed the finite-size scaling argument."],
                    "failure_conditions": ["Cannot explain what data distinguishes Ising CFT from tricritical Ising CFT."],
                    "no_ai_reconstruction_status": "not_started",
                    "next_rederive_time": scheduled,
                }
            ],
            "review_triggers": [
                {
                    "target": "二阶相变处一定是 CFT 吗",
                    "trigger_reason": "This is the first high-value boundary check for the CFT project.",
                    "review_type": "distinguish",
                    "scheduled_time": scheduled,
                    "success_criteria": "Learner can state assumptions and counterexamples without AI help.",
                }
            ],
            "next_recommended_action": "比较 Ising CFT 与 tricritical Ising CFT，并做无 AI 边界复述。",
            "source_metadata": {
                "source_type": "user_explicit",
                "source_message_id": None,
                "evidence_text": "我要学习 CFT",
            },
            "user_originated_updates": {
                "claims": 1,
                "distinctions": 1,
                "temporal_traces": 1,
                "knowledge_positions": 1,
                "derivation_trust_records": 1,
                "review_triggers": 1,
            },
            "ai_only_observations": {"seed_scope": "focused CFT local demo"},
            "discarded_ephemeral_judgments": {"seed_reference": "not a source of final truth"},
        }
    )


if __name__ == "__main__":
    created = seed_cft_learning()
    print(f"Seeded project: {created['name']} ({created['id']})")
