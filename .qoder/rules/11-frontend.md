---
trigger: glob
glob: app/templates/**/*.html, app/static/**/*.js, app/static/**/*.css
---
# Frontend

## Stack

- **HTMX** — server-driven interactivity without a build pipeline.
- **Alpine.js** — lightweight reactivity for component state (dropzones, toggles,
  counters, per-item state). Do not use it as a full SPA framework.
- **Tailwind CSS v4** + **DaisyUI v5** — utility-first styling with ready-made components.
- **Jinja2** — FastAPI template engine. Keep templates in `app/templates/`.
- **No build pipeline** — no npm, webpack, or Vite unless explicitly requested.
- Load all libraries from CDN:

```html
<!-- Tailwind v4 + DaisyUI v5 -->
<link href="https://cdn.jsdelivr.net/npm/daisyui@5/themes.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
<style type="text/tailwindcss">
  @plugin "daisyui";
</style>

<!-- HTMX + Alpine.js -->
<script src="https://unpkg.com/htmx.org@2/dist/htmx.min.js" defer></script>
<script src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js" defer></script>
```

***

## Template structure

```
app/templates/
  base.html              ← layout, CDN scripts, sidebar nav
  partials/
    doc_row.html         ← one document row (used in table + after upload)
    job_status.html      ← HTMX polling fragment (indexed / failed / pending)
    toast.html           ← success / error notification
  pages/
    documents.html       ← document list + upload zone
app/static/
  js/
    upload.js            ← XHR upload logic (see 10-doc-upload.md)
  css/
    style.css            ← custom overrides only
```

***

## Page layout — admin shell

Every admin page follows the same shell: fixed sidebar + scrollable main content area.
Only `<main>` scrolls — never the whole page.

```html
<!-- base.html -->
<body class="flex h-screen overflow-hidden bg-base-200">

  <!-- Sidebar -->
  <aside class="w-56 flex-none bg-base-100 border-r border-base-300 flex flex-col">
    <div class="p-4 text-lg font-semibold border-b border-base-300">HR Admin</div>
    <nav class="flex-1 p-2 flex flex-col gap-1">
      <a href="/documents" class="btn btn-ghost btn-sm justify-start gap-2">
        📄 Документы
      </a>
      <!-- add more nav items here -->
    </nav>
  </aside>

  <!-- Main content -->
  <main class="flex-1 overflow-y-auto p-6">
    {% block content %}{% endblock %}
  </main>

</body>
```

***

## Page header pattern

Each page has a consistent header: title on the left, primary action on the right.

```html
<div class="flex items-center justify-between mb-6">
  <div>
    <h1 class="text-xl font-semibold">Документы</h1>
    <p class="text-sm text-base-content/60">Загруженные в базу знаний файлы</p>
  </div>
  <label for="upload-input" class="btn btn-primary btn-sm">
    + Загрузить документ
  </label>
</div>
```

***

## Upload zone

Use drag-and-drop + click-to-browse. Alpine.js handles visual drag state.
XHR handles upload progress (never `fetch` — see `10-doc-upload.md`).

```html
<div
  x-data="{ dragging: false }"
  @dragover.prevent="dragging = true"
  @dragleave.prevent="dragging = false"
  @drop.prevent="dragging = false; handleDrop($event)"
  :class="dragging ? 'border-primary bg-primary/5' : 'border-base-300'"
  class="border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer"
  @click="$refs.fileInput.click()">

  <div class="text-3xl mb-2">📁</div>
  <p class="text-sm text-base-content/60">
    Перетащите файл сюда или <span class="text-primary underline">выберите</span>
  </p>
  <p class="text-xs text-base-content/40 mt-1">.docx, .pdf, .txt — до 20 МБ</p>

  <input
    x-ref="fileInput"
    type="file"
    class="hidden"
    accept=".docx,.pdf,.txt,.md"
    multiple
    @change="handleFileSelect($event)">
</div>
```

***

## Document table

Show each document as a table row with inline status badge.
The table body is updated via HTMX — not the whole page.

```html
<div class="card bg-base-100 shadow-sm">
  <table class="table">
    <thead>
      <tr>
        <th>Файл</th>
        <th>Размер</th>
        <th>Добавлен</th>
        <th>Статус</th>
        <th></th>
      </tr>
    </thead>
    <tbody id="doc-list">
      {% for doc in documents %}
        {% include "partials/doc_row.html" %}
      {% endfor %}
    </tbody>
  </table>
</div>
```

### Document row partial (`partials/doc_row.html`)

```html
<tr id="doc-{{ doc.job_id }}">
  <td class="font-medium">{{ doc.filename }}</td>
  <td class="text-sm text-base-content/60">{{ doc.size_kb }} KB</td>
  <td class="text-sm text-base-content/60">{{ doc.created_at }}</td>
  <td>
    {% if doc.status == "indexed" %}
      <span class="badge badge-success badge-sm">Готов</span>
    {% elif doc.status == "ingesting" %}
      <span class="badge badge-warning badge-sm">Обработка…</span>
    {% elif doc.status == "pending" %}
      <span class="badge badge-ghost badge-sm">В очереди</span>
    {% elif doc.status == "failed" %}
      <span class="badge badge-error badge-sm">Ошибка</span>
    {% endif %}
  </td>
  <td>
    {% if doc.status == "indexed" %}
      <button
        class="btn btn-ghost btn-xs text-error"
        hx-delete="/api/documents/{{ doc.job_id }}"
        hx-target="#doc-{{ doc.job_id }}"
        hx-swap="outerHTML"
        hx-confirm="Удалить документ из базы знаний?">
        Удалить
      </button>
    {% elif doc.status == "failed" %}
      <button class="btn btn-ghost btn-xs" onclick="retryUpload('{{ doc.job_id }}')">
        Повторить
      </button>
    {% endif %}
  </td>
</tr>
```

***

## Per-file upload progress row

When a file is uploading, insert a temporary row into `#doc-list` showing progress.
Replace it with the real `doc_row.html` partial once the job is created.

```html
<!-- Inserted by upload.js before XHR completes -->
<tr id="uploading-{{ filename }}">
  <td class="font-medium">{{ filename }}</td>
  <td colspan="3">
    <progress class="progress progress-primary w-full" value="0" max="100"></progress>
  </td>
  <td></td>
</tr>
```

Update `value` attribute via JS as `xhr.upload.onprogress` fires.

***

## HTMX polling for job status

See `10-doc-upload.md` for the full polling pattern (`/status-partial` endpoint).

The partial `partials/job_status.html` should:
- Return the row **with** `hx-trigger="every 2s"` while status is `pending` or `ingesting`.
- Return the row **without** `hx-trigger` once status is `indexed` or `failed` — this stops polling automatically.

```html
<!-- partials/job_status.html — terminal state (no hx-trigger) -->
<tr
  id="doc-{{ job.job_id }}"
  hx-get="/api/documents/{{ job.job_id }}/status-partial"
  hx-swap="outerHTML">
  ...
</tr>

<!-- partials/job_status.html — non-terminal state (keeps polling) -->
<tr
  id="doc-{{ job.job_id }}"
  hx-get="/api/documents/{{ job.job_id }}/status-partial"
  hx-trigger="every 2s"
  hx-swap="outerHTML">
  ...
</tr>
```

***

## Empty state

Never show a blank table. When no documents are indexed yet:

```html
{% if not documents %}
<div class="flex flex-col items-center justify-center py-20 text-center text-base-content/50">
  <div class="text-5xl mb-4">📭</div>
  <p class="font-medium text-base-content/70">Документов пока нет</p>
  <p class="text-sm mt-1">Загрузите первый файл — он появится здесь</p>
</div>
{% endif %}
```

***

## Toast notifications

Use HTMX `hx-on::after-request` or an Alpine.js store for flash messages.
Never use `alert()`. Always auto-dismiss after 4 seconds.

```html
<!-- partials/toast.html -->
<div
  x-data="{ show: true }"
  x-init="setTimeout(() => show = false, 4000)"
  x-show="show"
  x-transition
  class="toast toast-top toast-end z-50">
  <div class="alert {% if type == 'success' %}alert-success{% else %}alert-error{% endif %}">
    <span>{{ message }}</span>
  </div>
</div>
```

Inject via HTMX `hx-target` + `hx-swap="afterbegin"` into a `#toasts` container in `base.html`.

***

## Loading states

Every action that triggers a server request must show a loading indicator.
Use DaisyUI `loading` classes and HTMX `hx-indicator`.

```html
<!-- Spinner next to a button -->
<button
  class="btn btn-primary btn-sm"
  hx-post="/api/documents/reindex"
  hx-indicator="#reindex-spinner">
  Переиндексировать
  <span id="reindex-spinner" class="loading loading-spinner loading-xs htmx-indicator"></span>
</button>
```

For full-table reloads, show a skeleton placeholder:

```html
<!-- Skeleton row while loading -->
<tr>
  <td><div class="skeleton h-4 w-40"></div></td>
  <td><div class="skeleton h-4 w-16"></div></td>
  <td><div class="skeleton h-4 w-24"></div></td>
  <td><div class="skeleton h-5 w-14 rounded-full"></div></td>
  <td></td>
</tr>
```

***

## Confirmation dialogs

Use the native `hx-confirm` for simple destructive actions.
For two-step confirmation (e.g. "delete all"), use a DaisyUI modal:

```html
<!-- Trigger -->
<button class="btn btn-error btn-sm" onclick="document.getElementById('confirm-modal').showModal()">
  Очистить базу
</button>

<!-- Modal -->
<dialog id="confirm-modal" class="modal">
  <div class="modal-box">
    <h3 class="font-bold text-lg">Вы уверены?</h3>
    <p class="py-4 text-sm text-base-content/70">
      Все документы будут удалены из базы знаний без возможности восстановления.
    </p>
    <div class="modal-action">
      <form method="dialog">
        <button class="btn btn-ghost btn-sm">Отмена</button>
      </form>
      <button
        class="btn btn-error btn-sm"
        hx-delete="/api/documents"
        hx-target="#doc-list"
        hx-swap="innerHTML"
        onclick="document.getElementById('confirm-modal').close()">
        Удалить всё
      </button>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>
```

***

## Tailwind + DaisyUI rules

- Use DaisyUI component classes (`btn`, `card`, `badge`, `alert`, `table`, `input`, `modal`, etc.)
  before reaching for raw Tailwind utilities.
- Use Tailwind utilities only to adjust spacing, sizing, or layout that DaisyUI doesn't cover.
- Set the DaisyUI theme in `<html data-theme="...">`. Default: `data-theme="light"`.
- Do not write custom CSS for things DaisyUI already provides.
- Keep `style.css` for project-specific overrides only.

***

## General rules

- Return HTML from endpoints that HTMX calls, not JSON.
  JSON endpoints are for programmatic API consumers only (bots, external clients).
- Prefer `hx-swap="outerHTML"` for replacing a whole component,
  `hx-swap="innerHTML"` for updating content inside a container.
- Use semantic HTML: `<button>`, `<form>`, `<label>`, `<nav>`, `<main>`.
- Every interactive element must have a visible focus state (DaisyUI handles this by default).
- Never leave the UI frozen after an action — always show a loading state or feedback.

***

## Do not

- Do not introduce React, Vue, or any SPA framework unless explicitly requested.
- Do not add npm, webpack, Vite, or any build toolchain unless explicitly requested.
- Do not use `fetch()` for file upload progress — use `XMLHttpRequest` (see `10-doc-upload.md`).
- Do not manage server state in Alpine.js — Alpine is for UI state only.
- Do not inline large JavaScript blocks in Jinja2 templates.
- Do not return full pages from HTMX partial endpoints — return only the fragment.
- Do not use the JSON `/status` endpoint as an HTMX polling target — use `/status-partial` (HTML).
- Do not write custom CSS for components DaisyUI already provides.
- Do not use `alert()` or `confirm()` — use DaisyUI modal and toast instead.
- Do not reload the full page after upload — update only the affected table row.