from pathlib import Path

from ailearn.models import Goal, SessionFootprint
from ailearn.storage import (
    init_project,
    load_session,
    load_yaml_model,
    save_session,
    save_yaml_model,
)


def test_init_project_creates_expected_directories_and_templates(tmp_path: Path):
    project = tmp_path / "learn-os"

    init_project(project)

    assert (project / "src" / "ailearn").is_dir()
    assert (project / "data" / "goals").is_dir()
    assert (project / "data" / "reviews").is_dir()
    assert (project / "data" / "references").is_dir()
    assert (project / "data" / "tests").is_dir()
    assert (project / "data" / "events").is_dir()
    assert (project / "data" / "distinctions").is_dir()
    assert (project / "data" / "misconceptions").is_dir()
    assert (project / "data" / "clusters").is_dir()
    assert (project / "data" / "policies").is_dir()
    assert (project / "data" / "visuals").is_dir()
    assert (project / "data" / "indexes").is_dir()
    assert (project / "data" / "context_packs").is_dir()
    assert (project / "templates" / "goal.yaml").is_file()
    assert (project / "templates" / "reference.yaml").is_file()
    assert (project / "templates" / "test.yaml").is_file()
    assert (project / "templates" / "distinction.yaml").is_file()
    assert (project / "templates" / "misconception.yaml").is_file()
    assert (project / "templates" / "cluster.yaml").is_file()
    assert (project / "templates" / "policy.yaml").is_file()
    assert (project / "templates" / "visual.yaml").is_file()
    assert (project / "templates" / "session.md").is_file()


def test_save_and_load_yaml_model_round_trip(tmp_path: Path):
    goal = Goal(
        id="goal_roundtrip",
        title="Linear algebra",
        main_goal="Understand vector spaces",
        stage_goal="Basis and dimension",
        transfer_goal="Use in quantum mechanics",
        external_goal="Course prep",
        priority_topics=["basis", "eigenvectors"],
    )
    path = tmp_path / "goal.yaml"

    save_yaml_model(path, goal)
    loaded = load_yaml_model(path, Goal)

    assert loaded == goal


def test_save_and_load_markdown_session_frontmatter(tmp_path: Path):
    session = SessionFootprint(
        id="session_roundtrip",
        goal_id="goal_roundtrip",
        topic="perturbation_theory",
        mode="problem_solving",
    )
    body = {
        "Started with": "A question about first-order corrections.",
        "AI used for": "Hints only.",
        "Student outputs": "Wrote expansion ansatz.",
        "New claims": "Effective Hamiltonian resembles perturbation.",
        "New positioning decisions": "density_matrix is B for now.",
        "Unresolved": "Degenerate case.",
        "Next actions": "Verify claim.",
    }
    path = tmp_path / "session.md"

    save_session(path, session, body)
    loaded_session, loaded_body = load_session(path)

    assert loaded_session == session
    assert loaded_body["AI used for"] == "Hints only."
