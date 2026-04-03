---
trigger: glob
glob: app/templates/**/*.html, app/static/**/*.js, app/static/**/*.css
---
# Frontend

## Stack

- **HTMX** — server-driven interactivity without a build pipeline.
- **Alpine.js** — lightweight reactivity for component state (dropzones, toggles,
  counters, per-item state). Do not use it as a full SPA framework.
- **Jinja2** — FastAPI template engine. Keep templates in `app/templates/`.
- **No build pipeline** — no npm, webpack, or Vite unless explicitly requested.
- Load HTMX and Alpine.js from CDN:

```html
<script src="https://unpkg.com/htmx.org@2/dist/htmx.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js" defer></script>
```

***

## Template structure

```
app/templates/
  base.html          ← layout, CDN scripts, nav
  partials/          ← HTMX partial responses (table rows, status badges, lists)
  pages/
    documents.html
    ...
app/static/
  js/
    upload.js        ← XHR upload logic (see 10-doc-upload.md)
  css/
    style.css
```

- Keep `base.html` as the single layout with `{% block content %}`.
- HTMX partial responses live in `app/templates/partials/` — return them from
  dedicated endpoints, not full-page endpoints.
- Keep JavaScript in `app/static/js/` — do not inline large scripts in templates.
- Inline `<script>` only for short Alpine.js `x-data` component definitions.

***

## HTMX patterns

### Server-side partial update
```html
<button
  hx-post="/api/documents/reindex"
  hx-target="#doc-list"
  hx-swap="outerHTML"
  hx-indicator="#spinner">
  Reindex
</button>
```

### Polling for async status
```html
<div
  id="job-{{ job_id }}"
  hx-get="/api/documents/{{ job_id }}/status"
  hx-trigger="every 2s"
  hx-swap="outerHTML">
  <span class="badge badge--pending">Processing…</span>
</div>
```

Stop polling by returning the partial without `hx-trigger` once status is terminal
(`indexed` or `failed`).

### Form submission
```html
<form
  hx-post="/api/endpoint"
  hx-target="#result"
  hx-swap="innerHTML">
  ...
</form>
```

***

## Alpine.js patterns

Use Alpine.js for UI state that doesn't need a server round-trip:
- toggle visibility (`x-show`, `x-if`)
- per-item state in lists (`x-data` on each row)
- drag-and-drop affordance styling
- local counter or progress value

```html
<div x-data="{ open: false }">
  <button @click="open = !open">Toggle</button>
  <div x-show="open">Content</div>
</div>
```

Do not use Alpine.js to manage application state that belongs on the server.

***

## General rules

- Return HTML from endpoints that HTMX calls, not JSON.
  JSON endpoints are for programmatic API consumers only (bots, external clients).
- Prefer `hx-swap="outerHTML"` for replacing a whole component,
  `hx-swap="innerHTML"` for updating content inside a container.
- Use `hx-indicator` for loading states — never leave the UI frozen.
- Keep CSS simple and scoped — no CSS-in-JS, no utility framework unless
  explicitly requested.
- Use semantic HTML: `<button>`, `<form>`, `<label>`, `<nav>`, `<main>`.
- Every interactive element must have a visible focus state.

***

## Do not

- Do not introduce React, Vue, or any SPA framework unless explicitly requested.
- Do not add npm, webpack, Vite, or any build toolchain unless explicitly requested.
- Do not use `fetch()` for file upload progress — use `XMLHttpRequest`
  (see `10-doc-upload.md`).
- Do not manage server state in Alpine.js — Alpine is for UI state only.
- Do not inline large JavaScript blocks in Jinja2 templates.
- Do not return full pages from HTMX partial endpoints — return only the fragment.