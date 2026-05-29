from __future__ import annotations

from ailearn.agents.contracts import StateWriterOutput
from ailearn.db.repository import Repository


class StateWriterService:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def apply(self, project_id: str, message_id: str | None, output: StateWriterOutput) -> dict[str, object]:
        return self.repository.apply_state_writer_output(project_id, message_id, output.model_dump(mode="json"))

