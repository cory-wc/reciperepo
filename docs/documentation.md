# Documentation map

Where to put new information so README, USER_GUIDE, and notes stay distinct.

| File | Audience | Put here |
|------|----------|----------|
| [README.md](../README.md) | You, contributors, forkers | Repo setup and forking; directory layout; CLI workflows (add, update, remove, batch publish); CI and GitHub Pages; pointers to other docs |
| [USER_GUIDE.md](../USER_GUIDE.md) | Non-technical day-to-day use | Step-by-step tasks in plain language; how to *use* the collection (binder PDFs, GitHub Pages, shopping lists); Git sync across devices; troubleshooting; “what you usually skip” |
| [notes.md](../notes.md) | YAML authors and migration | ORF shape and naming; metadata checklist and verification rules; special entry types (binder index, in-progress paths, scaling tables); batch-fix priority; audit issue codes |
| [to-do.md](../to-do.md) | Project backlog | Incomplete recipes, manual-review queue, in-progress drafts, tooling improvements |

## Decision guide

**Adding content?** Ask:

1. **Is it a command, file path, or CI rule?** → README
2. **Is it “how do I do this?” without assuming terminal fluency?** → USER_GUIDE
3. **Is it a YAML field rule, convention, or reference table?** → notes
4. **Is it a task not done yet?** → to-do

**Avoid duplicating** the same checklist or command sequence in more than one file. Link instead (e.g. USER_GUIDE → notes for metadata detail; README → USER_GUIDE for non-technical walkthrough).

## Overlap that is intentional

- **Add / publish** appears in both README (commands, flags) and USER_GUIDE (numbered steps). Same pipeline, different depth.
- **Metadata** — USER_GUIDE may summarize common fixes; full rules live only in notes.

## Not documentation

- `prompts/` — LLM instructions, not user docs
- Generated output (`pdfs/`, `site/`, `recipes/index.yaml`) — do not document by hand; regenerate via CLI
