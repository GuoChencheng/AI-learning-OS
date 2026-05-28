# Codex 启动 Prompt

You are building a CLI-first local project called `ai-learning-os`.

## Product identity

This is an AI-native learning state manager.

It is NOT:
- a knowledge graph app;
- an encyclopedia;
- a note summarizer;
- a frontend app;
- an AI-generated course database.

It stores learning state, not world knowledge.

The product supports an AI-native learning workflow:
- learning goals;
- dynamic knowledge positioning;
- student-generated claims;
- epistemic verification status;
- derivation/trust-building records;
- lightweight session footprints;
- weekly reviews;
- prompt generation for AI assistance.

## Core philosophy

AI can dynamically generate explanations, examples, comparisons, and knowledge relations at runtime.
Therefore, the local system should not duplicate a static world knowledge graph.

The local system preserves:
- why the learner is studying;
- how a knowledge point is currently positioned relative to a goal;
- what the learner thinks;
- whether that thought is fact, interpretation, analogy, inference, speculation, or wrong;
- whether important results have been personally derived or merely accepted from AI;
- when something should be revisited.

## MVP scope

Build a Python CLI application.

Do not build a frontend.
Do not integrate OpenAI API yet.
Generate copyable prompts instead.

## Tech stack

Use:
- Python 3.11+
- Typer for CLI
- Pydantic for schemas
- PyYAML for YAML IO
- python-frontmatter or equivalent for Markdown frontmatter
- Rich for terminal output
- pytest for tests

## Repository structure

Create:

src/ailearn/
  __init__.py
  cli.py
  models.py
  storage.py
  prompts.py
  review.py
  validate.py
  ids.py

data/
  goals/
  positioning/
  claims/
  derivations/
  sessions/
  reviews/
  research_imports/

templates/
  goal.yaml
  position.yaml
  claim.yaml
  derivation.yaml
  session.md
  review.md

tests/
  test_models.py
  test_storage.py
  test_prompts.py
  test_review.py

Also create:
- README.md
- AGENTS.md
- pyproject.toml

## Core models

Implement Pydantic models:

1. Goal
2. PositionDecision
3. ClaimRecord
4. DerivationRecord
5. SessionFootprint
6. ReviewDraft

### Goal

Fields:
- id
- title
- main_goal
- stage_goal
- transfer_goal
- external_goal
- active
- priority_topics: list[str]
- created_at
- updated_at

### PositionDecision

Fields:
- id
- goal_id
- knowledge_point
- position:
  - A_no_ai_internalization
  - B_knowledge_positioning
  - C_index_recall
- tool_role:
  - core_tool
  - non_core_tool
  - none
- reason
- confidence:
  - low
  - medium
  - high
- epistemic_status:
  - strict_fact
  - derived_result
  - standard_interpretation
  - heuristic
  - analogy
  - inference
  - speculation
  - learning_strategy
  - wrong
  - open_question
- revisit_when: list[str]
- record_strength:
  - light
  - medium
  - heavy
- created_at
- updated_at

### ClaimRecord

Fields:
- id
- goal_id
- text
- context
- type:
  - definition
  - analogy
  - hypothesis
  - connection
  - calculation
  - interpretation
- status:
  - unverified
  - verified
  - partially_correct
  - misleading
  - wrong
  - open_question
- epistemic_status: same enum as above
- strict_part
- caveat
- counterexample_or_boundary
- next_action
- created_at
- updated_at

### DerivationRecord

Fields:
- id
- goal_id
- topic
- importance:
  - core_concept
  - core_tool
  - optional
- status:
  - not_started
  - partial
  - trusted
  - needs_rederive
- result_to_trust
- user_derived_steps: list[str]
- ai_hinted_steps: list[str]
- not_yet_trusted: list[str]
- next_action
- created_at
- updated_at

### SessionFootprint

Store as Markdown with YAML frontmatter.

Frontmatter fields:
- id
- goal_id
- topic
- mode
- created_at

Body sections:
- Started with
- AI used for
- Student outputs
- New claims
- New positioning decisions
- Unresolved
- Next actions

## CLI commands

Implement:

learn init <project_name>

learn goal create
learn goal list
learn goal show <goal_id>

learn position add <knowledge_point>
learn position list
learn position show <position_id>
learn position revisit

learn claim add "<claim text>"
learn claim list
learn claim show <claim_id>
learn claim update <claim_id>

learn derivation add <topic>
learn derivation list
learn derivation show <derivation_id>
learn derivation update <derivation_id>

learn session new <topic>
learn session list
learn session show <session_id>

learn prompt dynamic-positioning <knowledge_point>
learn prompt verify-claim <claim_id>
learn prompt derivation <derivation_id>
learn prompt socratic <topic>
learn prompt review weekly

learn import deep-research <path_to_markdown>
learn review weekly
learn validate

## Prompt generators

Implement copyable prompt generators.

### Dynamic positioning prompt

Must include:
- active learning goal;
- knowledge point;
- current context if available;
- ask AI to classify as A/B/C;
- ask whether it is core_tool / non_core_tool / none;
- ask for reason, required depth, revisit triggers;
- ask whether the classification is strict fact, inference, or learning_strategy.

### Claim verification prompt

Must ask AI to distinguish:
- strict fact;
- derived result;
- standard interpretation;
- heuristic;
- analogy;
- inference;
- speculation;
- wrong or misleading statement;
- open question.

### Derivation guidance prompt

Must instruct AI:
- do not give full derivation immediately;
- ask one step at a time;
- mark user-completed steps;
- mark AI-hinted steps;
- distinguish strict derivation from physical interpretation.

### Socratic drill prompt

Must instruct AI:
- ask one question at a time;
- focus on definition, boundary, misconception, example, counterexample, transfer;
- do not answer unless asked;
- after each answer classify understanding as clear / incomplete / misleading / wrong.

### Weekly review prompt

Must summarize:
- unresolved claims;
- derivations needing rework;
- positioning decisions needing revisit;
- possible Socratic drill topics;
- next actions.

## Validation

Implement `learn validate`.

It should:
- validate all YAML records;
- validate Markdown frontmatter for sessions;
- report missing required fields;
- report invalid enum values;
- report broken references to goal_id where possible.

## Weekly review

Implement `learn review weekly`.

It should read:
- sessions;
- claims;
- derivations;
- positioning decisions.

It should create a Markdown review under data/reviews/.

The review should include:
- recent sessions;
- unverified claims;
- misleading or partially correct claims;
- derivations not trusted;
- positioning decisions with revisit triggers;
- suggested Socratic drill topics;
- suggested next actions.

No AI API call is needed.

## Deep Research import

Implement:

learn import deep-research <path_to_markdown>

It should copy the Markdown file into data/research_imports/ with timestamped filename.
Deep Research imports are external suggestions only, not final truth.
Do not parse them into a static knowledge graph.

## AGENTS.md content

Create AGENTS.md explaining:

- this is not a knowledge graph app;
- do not store world knowledge;
- store learning state;
- default to light records;
- important claims need epistemic status;
- important concepts need derivation trust;
- no frontend for MVP;
- no API integration for MVP;
- tests must pass.

## Tests

Add pytest tests for:
- model validation;
- YAML save/load;
- Markdown frontmatter parsing;
- ID generation;
- prompt generation;
- weekly review generation;
- validate command core logic.

## Demo workflow

After implementation, run a sample workflow:

1. initialize project;
2. create a goal;
3. add a position decision for `density_matrix`;
4. add a claim: "Perturbation theory can be seen as a low-order expansion of effective theory.";
5. add a derivation record for `nondegenerate_perturbation_theory`;
6. create a session on `perturbation_theory`;
7. generate a claim verification prompt;
8. generate a weekly review;
9. run validation;
10. run tests.

Print:
- file tree;
- key generated files;
- test results.

## Product constraints

Be simple.
Be local-first.
Do not over-engineer.
Do not add a frontend.
Do not build a static knowledge graph.
Prioritize clean schemas, reliable file IO, strong prompt generation, and a smooth CLI workflow.
