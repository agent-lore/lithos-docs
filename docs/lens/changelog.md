# Lens changelog

Lens has no tagged releases yet; the package version on `main` is 0.5.0 and the site documents `main`. Milestones are tracked as PRDs in the repo's `docs/prd/` directory.

## Unreleased (`main`)

- **K2 — knowledge graph view** (October 2026): `/knowledge/graph` with a scope picker over the edge table, a Cytoscape canvas coloured by namespace or note type, server-rendered node and edge panels (`?selected=`, `?edge=`), weight and provenance filters, typed-node expansion (*Show its neighbours* / *Collapse*), a full-page canvas, and a "graph changed" refresh pill driven by `GET /knowledge/events`.
- **Knowledge fix-up** after K1: one search box across the knowledge pages, back links that return where you came from, the collapsed-search-input bug fixed.
- **Gates on the dashboard**: under a scope filter the board shows the gates in-scope tasks wait on, with *Proceed anyway…* for an operator.
- **T3 — curated write actions**: operator identity (`/operator`, `lens_operator` cookie), New task / epic / gate form with a request id, Cancel… with consequences, Reopen, Add a dependency with *Check relation…*, receipts and refusals.
- **T2 — task relationship graphs**: `/tasks/graph` by project or epic, the text baseline with layers and cycle callouts, the nearby mini-graph on task detail.
- **T1 — graph-native operator view**: needs-attention rules, ready/blocked frontiers, epic and project strips.

Earlier: the Tasks MVP (dashboard, detail, findings timeline, live SSE updates, degraded mode) and the K1 knowledge note view.
