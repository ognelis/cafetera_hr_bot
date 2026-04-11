// app/static/js/upload.js
// Standalone window.* functions called from template onclick attributes
// and HTMX-triggered actions (delete, rename, doc question bridges)

// ── Delete confirmation ───────────────────────────────────────
let pendingDeleteId = null;

window.confirmDelete = function(docId) {
  pendingDeleteId = docId;
  document.getElementById('confirm-delete-dialog').showModal();
};

window.executeDelete = function() {
  if (!pendingDeleteId) return;
  const docId = pendingDeleteId;
  document.getElementById('confirm-delete-dialog').close();

  htmx.ajax('DELETE', `/api/documents/${docId}`, {
    target: `#row-${docId}`,
    swap: 'outerHTML'
  }).then(() => {
    window.dispatchEvent(new CustomEvent('show-toast', {
      detail: { message: 'Документ удален', type: 'success' }
    }));
    // Refresh the entire table to update pagination and counts
    const el = document.querySelector('[x-data="documentsPage()"]');
    if (el && el._x_dataStack && el._x_dataStack[0]) {
      const alpineData = el._x_dataStack[0];
      htmx.ajax('GET', alpineData.buildTableUrl(), {target: '#document-table-container', swap: 'innerHTML'});
    }
  });

  pendingDeleteId = null;
};

// ── Rename ────────────────────────────────────────────────────
let pendingRenameId = null;

window.openRename = function(docId, currentTitle) {
  pendingRenameId = docId;
  const input = document.getElementById('rename-input');
  input.value = currentTitle;
  document.getElementById('rename-dialog').showModal();
  input.focus();
  input.select();
};

window.submitRename = function() {
  if (!pendingRenameId) return;
  const docId = pendingRenameId;
  const title = document.getElementById('rename-input').value.trim();
  if (!title) return;

  document.getElementById('rename-dialog').close();

  const formData = new FormData();
  formData.append('title', title);

  fetch(`/api/documents/${docId}/title`, {
    method: 'PATCH',
    headers: { 'HX-Request': 'true' },
    body: formData
  }).then(res => res.text()).then(html => {
    const row = document.getElementById(`row-${docId}`);
    if (row) {
      row.outerHTML = html;
    }
    window.dispatchEvent(new CustomEvent('show-toast', {
      detail: { message: 'Название обновлено', type: 'success' }
    }));
  });

  pendingRenameId = null;
};

// ── Document question (global bridge into Alpine component) ───
window.openDocQuestion = function(docId, title) {
  const el = document.querySelector('[x-data="documentsPage()"]');
  if (el && el._x_dataStack && el._x_dataStack[0]) {
    el._x_dataStack[0].openDocQuestion(docId, title);
  }
};
