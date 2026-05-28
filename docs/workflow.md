# AI Learning OS Workflow

The system stores learning state, not world knowledge.

## 1. Goal Intake

Clarify what to learn, why it matters, desired depth, time constraints, transfer goals, and what "learned enough" means. Use the Goal Intake prompt when the goal is still vague.

## 2. Deep Research

Deep Research happens outside this tool. The app generates a copyable prompt for ChatGPT Deep Research. Imported output is initial guidance only and is stored under `data/research_imports/`.

## 3. References

References are durable source entries under `data/references/`. They are not AI summaries and not an encyclopedia.

## 4. Classification Policy

Before treating A/B/C as a list, derive a ClassificationPolicy from the active goal. The policy records A/B/C criteria, core-tool criteria, test-mode criteria, upgrade triggers, downgrade triggers, and revisit triggers.

A/B/C is a classification grammar, not a static map of the field.

## 5. Initial Positioning

Classify knowledge points relative to the active goal:

- `A_no_ai_internalization`
- `B_knowledge_positioning`
- `C_index_recall`

Also classify tool role and record revisit triggers.

## 6. Spiral Learning

Learning proceeds as provisional understanding, forward progress, revisit, reposition, deepen, or downgrade. Lightweight records should stay lightweight.

## 7. Method Routing

Use deterministic local method suggestions and copyable prompts to decide the next learning method. Method routing should reduce friction rather than add bureaucracy.

## 8. Claim Verification

Student-generated claims are tracked separately from facts. Important claims need status, epistemic status, caveat, boundary, and next action.

## 9. Derivation Trust

For core concepts and tools, record whether the learner derived the steps, received AI hints, or still does not trust a step.

## 10. Visual Support

When a concept is geometric, dynamic, relational, experimental, diagrammatic, or repeatedly confused, add visual support metadata. Prefer figures from the studied paper/textbook/lecture note, then reliable web visuals, then AI-generated schematics clearly labeled as teaching aids and not evidence.

## 11. Test Mode

Test mode defines evidence of learning. Internalization levels move from A0 through A4:

- A0: important but not verified
- A1: can explain and distinguish
- A2: can handle boundary and counterexample
- A3: can reconstruct, derive, or transfer
- A4: can retrieve after delay without AI

## 12. Weekly Review

Weekly review summarizes sessions, references, claims, derivation trust gaps, positioning revisit triggers, A-level progress, test readiness, method recommendations, and top next actions.

## AI Context Loading

AI agents should not load all learner data by default. Refresh indexes and build a context pack for the task:

```bash
learn index refresh
learn context build --task verify_claim --id claim_example
```

Context packs are compact loading guides. They keep deterministic local evidence separate from AI interpretation.

## Codex + Browser Workflow

The Web UI is the human learning cockpit. Codex remains the agent/execution layer. A typical loop:

1. Open `learn ui`.
2. Inspect dashboard state.
3. Generate a prompt or Agent Task card.
4. Give the task to Codex or an external AI tool.
5. Codex edits local YAML/Markdown files.
6. Refresh the UI and validate.
