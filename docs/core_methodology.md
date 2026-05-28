# Core Methodology

`ai-learning-os` is a local-first AI-native learning state manager. It stores learning state, not world knowledge. It is not a knowledge base, not a static knowledge graph, not a note summarizer, and not an AI tutor clone.

Prompt-only mode is the default. Optional connected mode can call a user-configured provider, but only after explicit user action and only with selected prompts or context packs.

## A/B/C Positioning

A/B/C is a dynamic classification grammar relative to a learning goal and policy, not a fixed map of a field.

- `A_no_ai_internalization`: must enter the learner's head as disciplinary language.
- `B_knowledge_positioning`: must know role, use, and relation; details can be restored with AI or references.
- `C_index_recall`: only needs to be remembered as an entry point.

## Epistemic Discipline

Important claims must distinguish strict fact, derived result, standard interpretation, heuristic, analogy, inference, speculation, learning strategy, wrong statement, and open question.

## Derivation Trust

For core concepts and tools, record whether the learner personally reconstructed the result. Separate user-derived steps, AI-hinted steps, and not-yet-trusted steps.

## Distinction, Misconception, Claim

Use a `DistinctionRecord` when the learner cannot distinguish adjacent concepts. Use a `MisconceptionRecord` for a recurring wrong idea. Use a `ClaimRecord` for a student-generated statement that needs verification.

## Snapshot, Event, Session

Snapshot YAML records store current state only. JSONL event logs store history. Markdown sessions store raw learning footprint.

## Minimal Context

AI agents should load minimal context for the task. Read methodology and policy first, then the primary record, selected related records, compact timeline, and reference metadata only when useful.

## No-AI Internalization

AI can generate explanations, comparisons, prompts, and suggestions, but it should not replace no-AI internalization for A-zone knowledge.

## AI Output Is Not Understanding

Provider responses are artifacts for review. They are not automatically stored as facts, derivation trust, or internalization evidence.

## Visual Explanation

AI should actively consider visual explanation when concepts are geometric, dynamic, relational, experimental, diagrammatic, or repeatedly confused. Store visual metadata and usage purpose, not large media files by default. Literature figures have highest priority when explaining a paper. Reliable external visuals are second. AI-generated schematics are third and must be labeled illustrative, not evidence. System-generated diagrams are appropriate for learning-state timelines and workflows.
