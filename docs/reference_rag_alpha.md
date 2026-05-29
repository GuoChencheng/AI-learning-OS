# Reference / RAG Alpha

AI Learn OS currently implements deterministic reference chunk retrieval. It is intentionally not full embedding RAG yet.

## Current Pipeline

1. User pastes or uploads a reference.
2. Backend extracts text:
   - pasted text is used directly;
   - txt/md upload is decoded as UTF-8;
   - PDF upload uses `pypdf` when installed.
3. `chunk_text()` creates overlapping plain-text chunks.
4. `ContextExtractorAgent` ranks references and chunks deterministically against the current request.
5. `ContextPackBuilderAgent` formats selected chunk excerpts into `reference_context`.
6. At Learning Unit start, selected chunks are saved in `learning_units.context_snapshot_json`.
7. Reused Learning Unit turns reuse the snapshot instead of reranking every project reference.

## Ranking Behavior

The alpha ranker is keyword-based:

- English words are lowercased and matched by overlap.
- Chinese learning terms are kept with simple substring matching.
- Reference title/scope/chunk text all contribute.
- Pending review triggers, active records, no-AI gaps, and recent traces are preferred in state ranking.
- Deprecated, completed, skipped, or trusted records are penalized.

This is enough for local smoke tests and focused demos such as the CFT seed project.

## ContextPack Shape

When relevant chunks are found, `reference_context` includes source metadata and excerpts:

```text
Reference: CFT focused seed note
Reliability: medium
Scope: Focused local demo reference for CFT learning-state behavior.
Section: Chunk 1
Excerpt:
...
```

The same selected chunks also appear in `pipeline_trace` and can be surfaced by frontend metadata chips.

## Learning Unit Reuse

Learning Unit context is short-lived working memory, not durable learner memory.

- First unit turn runs full context extraction and stores a context snapshot.
- Follow-up turns reuse the snapshot and recent unit turn summaries.
- `/api/projects/:id/learning-units/:unit_id/refresh-context` marks the snapshot stale.
- The next chat/run-next refresh reruns extraction and clears `refresh_requested`.

## Persistence Rules

ContextPack table persistence is disabled by default. Set:

```bash
AI_LEARN_DEBUG_PERSIST_CONTEXT=1
```

to persist context packs for debug/audit. Reference chunks themselves remain durable because they are user-uploaded or user-selected source material.

## Current Limitations

- No embeddings or pgvector query path is active in local SQLite runtime.
- Chunk ranking can miss semantic matches with different wording.
- Citations are excerpt-level, not paragraph/page-perfect for every file type.
- PDF extraction quality depends on source PDF text layer and `pypdf`.
- UI source preview is currently a muted hover preview, not a full source inspector.

## Planned Upgrade

- Add embedding provider configuration.
- Store embeddings in Postgres `reference_chunks.embedding`.
- Use hybrid keyword + vector retrieval.
- Add reference source popover with title, page/section, reliability, and excerpt.
- Add a debug trace toggle that shows why chunks were selected without cluttering the default chat flow.
