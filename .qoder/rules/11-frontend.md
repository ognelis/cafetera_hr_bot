---
trigger: glob
glob: templates/**/*.html, static/**/*.js, static/**/*.css
---
# Frontend

## Stack

- **HTMX** — server-driven interactivity without a build pipeline.
- **Alpine.js** — lightweight reactivity for UI state (dropzones, toggles, counters). Not a SPA framework.
- **Tailwind CSS v4** + **DaisyUI v5** — utility-first styling with ready-made components.
- **Jinja2** — FastAPI template engine. Templates in `templates/`.
- **No build pipeline** — no npm, webpack, or Vite unless explicitly requested.
- All libraries are vendored into `static/vendor/` — never load from CDN.

```html
<link rel="stylesheet" href="{{ url_for('static', path='vendor/daisyui/daisyui.min.css') }}">
<script src="{{ url_for('static', path='vendor/tailwindcss/tailwind-browser.js') }}"></script>
<script src="{{ url_for('static', path='vendor/htmx/htmx.min.js') }}" defer></script>
<script src="{{ url_for('static', path='vendor/alpinejs/cdn.min.js') }}" defer></script>
<script src="{{ url_for('static', path='vendor/marked/marked.min.js') }}" defer></script>
```

***

## Project structure

```
templates/
  base.html              ← layout, vendor scripts, sidebar nav
  documents.html         ← document management page
  category_files.html    ← category file management page
  login.html             ← admin login page
  partials/              ← HTMX fragments and reusable components (one component per file)
    category_slot.html
    document_row.html
    document_table.html
    pagination.html
    status_poller.html
  macros/                ← (planned) pure rendering helpers (badges, icons, labels)
  pages/                 ← (planned) full pages extending base.html
static/
  vendor/
    tailwindcss/tailwind-browser.js
    daisyui/daisyui.min.css
    htmx/htmx.min.js
    alpinejs/cdn.min.js
    marked/marked.min.js
  js/
    components.js        ← Alpine.data() and Alpine.store() definitions
    upload.js            ← XHR upload logic (see 10-doc-upload.md)
  css/
    style.css            ← custom overrides only
```

***

## Component reuse

Extract to `partials/` when a fragment is:
- used in ≥2 places, **or**
- returned as an HTMX endpoint response.

Use `{% include %}` with `with context` to pass the current template variables:

```html
{% include "partials/doc_row.html" with context %}
```

For pure rendering helpers (no server logic, no HTMX — just markup with parameters)
use Jinja2 macros in `macros/ui.html` (planned — not yet created):

```html
{% from "macros/ui.html" import status_badge %}
{{ status_badge(doc.status) }}
```

Keep partials focused: **one partial = one component**. Never put page-level
layout (base shell, nav, sidebar) inside a partial.

***

## Alpine.js patterns

| Tool | Use for | Not for |
|---|---|---|
| `x-data` inline | Local state of a single element | State needed by another component |
| `Alpine.data('name', ...)` | Reusable component (≥2 uses) | Global shared state |
| `Alpine.store('name', ...)` | Shared state across components | Server data |

Define all `Alpine.data()` and `Alpine.store()` in `static/js/components.js`. Use `document.addEventListener('alpine:init', ...)` for registration.

Functions called from template `onclick` must use `window.fnName = function(...)` in `static/js/upload.js`.

***

## HTMX rules

- Return HTML fragments from HTMX endpoints — never JSON.
- `hx-swap="outerHTML"` to replace a whole component; `hx-swap="innerHTML"` to update its contents.
- After any swap, Alpine won't auto-init new DOM. Add to the container:
  ```html
  <tbody id="doc-list" hx-on::htmx:after-settle="Alpine.initTree(this)">
  ```
- Stop polling by returning the fragment **without** `hx-trigger` on terminal states (`indexed`, `failed`).
- Use `hx-indicator` + DaisyUI `loading` spinner on every action that hits the server.

***

## UI rules

- **Empty states** — never show a blank container; always include a message and a primary action.
- **Toasts** — use HTMX `hx-swap="afterbegin"` into a `#toasts` container; auto-dismiss after 4s via Alpine `x-init="setTimeout(() => show = false, 4000)"`. Never `alert()`.
- **Confirmations** — `hx-confirm` for simple destructive actions; DaisyUI `<dialog>` modal for two-step flows.
- **Loading** — every server action shows a spinner or skeleton; never leave the UI frozen.

***

## Tailwind + DaisyUI rules

- Use DaisyUI component classes (`btn`, `card`, `badge`, `alert`, `table`, `input`, `modal`) before raw Tailwind utilities.
- Tailwind utilities only for spacing, sizing, or layout DaisyUI doesn't cover.
- Set theme on `<html data-theme="light">`.
- `style.css` for project-specific overrides only — never rewrite what DaisyUI provides.

***

## Responsive

This is a desktop admin panel (1024px+). Do not add mobile breakpoints (`sm:`, `md:`)
unless the page is explicitly marked as mobile-friendly in its task description.

***

## Do not

- Do not load libraries from CDN (`jsdelivr.net`, `unpkg.com`, `cdn.*`) — use `static/vendor/`.
- Do not introduce React, Vue, or any SPA framework unless explicitly requested.
- Do not add npm, webpack, Vite, or any build toolchain unless explicitly requested.
- Do not use `fetch()` for file upload progress — use `XMLHttpRequest` (see `10-doc-upload.md`).
- Do not manage server state in Alpine.js — Alpine is for UI state only.
- Do not inline JavaScript blocks in Jinja2 templates — put logic in `static/js/`.
- Do not declare functions called from templates as `const`/`let` — use `window.fnName = function(...)`.
- Do not store component state as bare module-level variables — use `Alpine.store` or `Alpine.data` closures.
- Do not return full pages from HTMX partial endpoints — return only the fragment.
- Do not duplicate markup — extract to `partials/` or macros when used in ≥2 places.
- Do not use `alert()` or `confirm()` — use DaisyUI modal and toast instead.
- Do not reload the full page after an action — update only the affected fragment.