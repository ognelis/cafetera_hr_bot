// app/static/js/components.js
// Alpine.data() and Alpine.store() definitions
// Loaded in base.html before Alpine.js (both with defer)

document.addEventListener('alpine:init', () => {

  // ── Toast manager ──────────────────────────────────────────
  Alpine.data('toastManager', () => ({
    toasts: [],
    nextId: 0,
    addToast(detail) {
      const id = this.nextId++;
      this.toasts.push({ id, message: detail.message || detail, type: detail.type || 'info' });
      setTimeout(() => this.remove(id), 5000);
    },
    remove(id) {
      this.toasts = this.toasts.filter(t => t.id !== id);
    }
  }));

  // Listen for HX-Trigger "showToast" events from HTMX responses
  document.body.addEventListener('showToast', function(evt) {
    window.dispatchEvent(new CustomEvent('show-toast', { detail: evt.detail }));
  });

  // ── Upload activity counter ────────────────────────────────
  Alpine.store('uploads', {
    active: 0,
    inc() { this.active++; },
    dec() { this.active--; }
  });

  // ── Documents page ─────────────────────────────────────────
  Alpine.data('documentsPage', () => ({
    // Upload state
    dragOver: false,
    uploads: [],
    nextUploadId: 0,

    // Filter state (populated from data-config)
    searchQuery: '',
    statusFilter: 'all',
    sourceTypeFilter: 'all',
    dateFrom: '',
    dateTo: '',

    // Sort state
    sortField: '',
    sortDir: 'desc',

    // Selection state
    selectedIds: [],

    // Document question state
    docQuestionOpen: false,
    docQuestionId: '',
    docQuestionTitle: '',
    docQuestionText: '',
    docQuestionAnswer: '',
    docQuestionLoading: false,
    docQuestionError: '',

    // Global question state
    globalQuestionOpen: false,
    globalQuestion: '',
    globalAnswer: '',
    globalLoading: false,
    globalError: '',

    // Pagination state
    currentPage: 1,
    perPage: 10,
    total: 0,

    // Bulk confirm state
    bulkConfirmAction: null,
    bulkConfirmMessage: '',

    get statusFilterLabel() {
      const labels = {
        all: 'Все',
        completed: 'Готов',
        processing: 'Индексация',
        pending: 'Ожидание',
        failed: 'Ошибка'
      };
      return labels[this.statusFilter] || 'Все';
    },

    get sourceTypeFilterLabel() {
      const labels = {
        all: 'Все',
        docx: 'DOCX',
        doc: 'DOC',
        xlsx: 'XLSX',
        other: 'Другие'
      };
      return labels[this.sourceTypeFilter] || 'Все';
    },

    get dateFilterLabel() {
      const fromValue = String(this.dateFrom || '').trim();
      const toValue = String(this.dateTo || '').trim();
      const fromDate = fromValue ? new Date(fromValue) : null;
      const toDate = toValue ? new Date(toValue) : null;
      const hasFrom = fromDate && !isNaN(fromDate.getTime());
      const hasTo = toDate && !isNaN(toDate.getTime());

      if (hasFrom && hasTo) {
        return `${fromDate.toLocaleDateString('ru-RU')} – ${toDate.toLocaleDateString('ru-RU')}`;
      } else if (hasFrom) {
        return `С ${fromDate.toLocaleDateString('ru-RU')}`;
      } else if (hasTo) {
        return `По ${toDate.toLocaleDateString('ru-RU')}`;
      }
      return 'Все';
    },

    get visibleCount() {
      const rows = document.querySelectorAll('#document-table-body tr[data-document-id]');
      let count = 0;
      rows.forEach(row => {
        if (this.shouldShowRow(row)) count++;
      });
      return count;
    },

    get allSelected() {
      const visibleRows = document.querySelectorAll('#document-table-body tr[data-document-id]');
      if (visibleRows.length === 0) return false;
      for (const row of visibleRows) {
        const id = row.getAttribute('data-document-id');
        if (this.shouldShowRow(row) && !this.selectedIds.includes(id)) {
          return false;
        }
      }
      return true;
    },

    shouldShowRow(/* row */) {
      // All filtering is now server-side
      return true;
    },

    reloadWithFilters() {
      this.currentPage = 1;
      htmx.ajax('GET', this.buildTableUrl(), {target: '#document-table-container', swap: 'innerHTML'});
    },

    toggleSort(field) {
      if (this.sortField === field) {
        this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
      } else {
        this.sortField = field;
        this.sortDir = 'asc';
      }
      this.currentPage = 1;
      htmx.ajax('GET', this.buildTableUrl(), {target: '#document-table-container', swap: 'innerHTML'});
    },

    toggleSelectAll() {
      const visibleRows = document.querySelectorAll('#document-table-body tr[data-document-id]');
      const allVisibleSelected = this.allSelected;

      if (allVisibleSelected) {
        visibleRows.forEach(row => {
          const id = row.getAttribute('data-document-id');
          if (this.shouldShowRow(row)) {
            this.selectedIds = this.selectedIds.filter(i => i !== id);
            const checkbox = row.querySelector('input[type="checkbox"]');
            if (checkbox) checkbox.checked = false;
          }
        });
      } else {
        visibleRows.forEach(row => {
          const id = row.getAttribute('data-document-id');
          if (this.shouldShowRow(row) && !this.selectedIds.includes(id)) {
            this.selectedIds.push(id);
            const checkbox = row.querySelector('input[type="checkbox"]');
            if (checkbox) checkbox.checked = true;
          }
        });
      }
    },

    init() {
      // Read server-injected config from data-config attribute
      const cfg = JSON.parse(this.$el.dataset.config || '{}');
      this.searchQuery = cfg.search || '';
      this.statusFilter = cfg.status_filter || 'all';
      this.sourceTypeFilter = cfg.source_type_filter || 'all';
      this.dateFrom = cfg.date_from || '';
      this.dateTo = cfg.date_to || '';
      this.sortField = cfg.sort_field || '';
      this.sortDir = cfg.sort_dir || 'desc';
      this.currentPage = cfg.page || 1;
      this.perPage = cfg.per_page || 10;
      this.total = cfg.total || 0;

      // Watchers for filters that trigger server-side reload
      // Use a small delay to avoid triggering on initial value set
      setTimeout(() => {
        this.$watch('statusFilter', (newVal, oldVal) => {
          if (newVal !== oldVal) this.reloadWithFilters();
        });
        this.$watch('sourceTypeFilter', (newVal, oldVal) => {
          if (newVal !== oldVal) this.reloadWithFilters();
        });
      }, 0);

      // Sync date params from URL on page load
      const urlParams = new URLSearchParams(window.location.search);
      const df = urlParams.get('date_from');
      const dt = urlParams.get('date_to');
      if (df) this.dateFrom = df;
      if (dt) this.dateTo = dt;

      // Sync Alpine state after HTMX pagination swaps
      document.addEventListener('htmx:afterSettle', (evt) => {
        if (evt.detail.target && evt.detail.target.id === 'document-table-container') {
          if (evt.detail.xhr && evt.detail.xhr.responseURL) {
            const url = new URL(evt.detail.xhr.responseURL);
            const p = url.searchParams.get('page');
            const pp = url.searchParams.get('per_page');
            const status = url.searchParams.get('status');
            const sourceType = url.searchParams.get('source_type');
            const sortField = url.searchParams.get('sort_field');
            const sortDir = url.searchParams.get('sort_dir');
            if (p) this.currentPage = parseInt(p);
            if (pp) this.perPage = parseInt(pp);
            if (status) this.statusFilter = status;
            if (sourceType) this.sourceTypeFilter = sourceType;
            if (sortField) this.sortField = sortField;
            if (sortDir) this.sortDir = sortDir;
          }
          const totalEl = evt.detail.target.querySelector('[data-total]');
          if (totalEl) {
            this.total = parseInt(totalEl.dataset.total) || 0;
          }
          this.selectedIds = [];
        }
      });
    },

    buildTableUrl() {
      let url = '/partials/document-table?page=' + this.currentPage + '&per_page=' + this.perPage;
      if (this.searchQuery) {
        url += '&search=' + encodeURIComponent(this.searchQuery);
      }
      if (this.dateFrom) {
        url += '&date_from=' + encodeURIComponent(this.dateFrom);
      }
      if (this.dateTo) {
        url += '&date_to=' + encodeURIComponent(this.dateTo);
      }
      if (this.statusFilter && this.statusFilter !== 'all') {
        url += '&status=' + encodeURIComponent(this.statusFilter);
      }
      if (this.sourceTypeFilter && this.sourceTypeFilter !== 'all') {
        url += '&source_type=' + encodeURIComponent(this.sourceTypeFilter);
      }
      if (this.sortField) {
        url += '&sort_field=' + encodeURIComponent(this.sortField);
        url += '&sort_dir=' + encodeURIComponent(this.sortDir);
      }
      return url;
    },

    // Bulk action methods
    async executeBulkDelete() {
      try {
        const response = await fetch('/api/documents/bulk/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids: this.selectedIds })
        });
        if (response.ok) {
          this.selectedIds = [];
          htmx.ajax('GET', this.buildTableUrl(), {target: '#document-table-container', swap: 'innerHTML'});
          window.dispatchEvent(new CustomEvent('show-toast', {
            detail: { message: 'Документы удалены', type: 'success' }
          }));
        } else {
          window.dispatchEvent(new CustomEvent('show-toast', {
            detail: { message: 'Ошибка при удалении', type: 'error' }
          }));
        }
      } catch (err) {
        window.dispatchEvent(new CustomEvent('show-toast', {
          detail: { message: 'Ошибка при удалении', type: 'error' }
        }));
      }
    },

    async executeBulkReindex() {
      try {
        const response = await fetch('/api/documents/bulk/reindex', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids: this.selectedIds })
        });
        if (response.ok) {
          this.selectedIds = [];
          htmx.ajax('GET', this.buildTableUrl(), {target: '#document-table-container', swap: 'innerHTML'});
          window.dispatchEvent(new CustomEvent('show-toast', {
            detail: { message: 'Переиндексация запущена', type: 'success' }
          }));
        } else {
          window.dispatchEvent(new CustomEvent('show-toast', {
            detail: { message: 'Ошибка при переиндексации', type: 'error' }
          }));
        }
      } catch (err) {
        window.dispatchEvent(new CustomEvent('show-toast', {
          detail: { message: 'Ошибка при переиндексации', type: 'error' }
        }));
      }
    },

    async executeBulkSearch(enabled) {
      try {
        const response = await fetch('/api/documents/bulk/search', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids: this.selectedIds, enabled: enabled })
        });
        if (response.ok) {
          this.selectedIds = [];
          htmx.ajax('GET', this.buildTableUrl(), {target: '#document-table-container', swap: 'innerHTML'});
          window.dispatchEvent(new CustomEvent('show-toast', {
            detail: { message: enabled ? 'Документы включены в поиск' : 'Документы исключены из поиска', type: 'success' }
          }));
        } else {
          window.dispatchEvent(new CustomEvent('show-toast', {
            detail: { message: 'Ошибка при обновлении', type: 'error' }
          }));
        }
      } catch (err) {
        window.dispatchEvent(new CustomEvent('show-toast', {
          detail: { message: 'Ошибка при обновлении', type: 'error' }
        }));
      }
    },

    // Date filter methods
    applyDateFilter() {
      this.currentPage = 1;
      htmx.ajax('GET', this.buildTableUrl(), {target: '#document-table-container', swap: 'innerHTML'});
    },

    clearDateFilter() {
      this.dateFrom = '';
      this.dateTo = '';
      this.applyDateFilter();
    },

    // Bulk confirm modal helpers
    requestBulkConfirm(message, actionFn) {
      this.bulkConfirmMessage = message;
      this.bulkConfirmAction = actionFn;
      this.$refs.bulkConfirmModal.showModal();
    },

    confirmBulkAction() {
      this.$refs.bulkConfirmModal.close();
      if (this.bulkConfirmAction) {
        this.bulkConfirmAction();
        this.bulkConfirmAction = null;
      }
    },

    cancelBulkConfirm() {
      this.$refs.bulkConfirmModal.close();
      this.bulkConfirmAction = null;
      this.bulkConfirmMessage = '';
    },

    // Document question methods
    openDocQuestion(id, title) {
      this.docQuestionId = id;
      this.docQuestionTitle = title;
      this.docQuestionText = '';
      this.docQuestionAnswer = '';
      this.docQuestionError = '';
      this.docQuestionLoading = false;
      this.$refs.docQuestionModal.showModal();
    },

    closeDocQuestion() {
      this.$refs.docQuestionModal.close();
      this.docQuestionId = '';
      this.docQuestionTitle = '';
      this.docQuestionText = '';
      this.docQuestionAnswer = '';
      this.docQuestionError = '';
      this.docQuestionLoading = false;
    },

    // Global question methods
    openGlobalQuestion() {
      this.globalQuestionOpen = true;
      this.globalQuestion = '';
      this.globalAnswer = '';
      this.globalLoading = false;
      this.globalError = '';
      this.$refs.globalQuestionModal.showModal();
    },

    closeGlobalQuestion() {
      this.$refs.globalQuestionModal.close();
      this.globalQuestionOpen = false;
      this.globalQuestion = '';
      this.globalAnswer = '';
      this.globalError = '';
      this.globalLoading = false;
    },

    async submitGlobalQuestion() {
      if (!this.globalQuestion.trim()) return;
      this.globalLoading = true;
      this.globalError = '';
      this.globalAnswer = '';

      const fd = new FormData();
      fd.append('question', this.globalQuestion.trim());

      try {
        const resp = await fetch('/api/qa/ask-global', {
          method: 'POST',
          body: fd,
        });

        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          this.globalError = err.detail || 'Ошибка при получении ответа';
          this.globalLoading = false;
          return;
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.token) {
                  const unescapedToken = data.token.replace(/\\n/g, '\n').replace(/\\"/g, '"').replace(/\\\\/g, '\\');
                  this.globalAnswer += unescapedToken;
                }
                if (data.error) {
                  this.globalError = data.error;
                }
              } catch (e) {
                // skip malformed SSE lines
              }
            }
          }
        }
      } catch (e) {
        this.globalError = 'Ошибка сети при получении ответа';
      } finally {
        this.globalLoading = false;
      }
    },

    async submitDocQuestion() {
      if (!this.docQuestionText.trim()) return;
      this.docQuestionLoading = true;
      this.docQuestionAnswer = '';
      this.docQuestionError = '';

      const fd = new FormData();
      fd.append('question', this.docQuestionText.trim());

      try {
        const resp = await fetch(`/api/documents/${this.docQuestionId}/ask`, {
          method: 'POST',
          body: fd,
        });

        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          this.docQuestionError = err.detail || 'Ошибка при получении ответа';
          this.docQuestionLoading = false;
          return;
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.token) {
                  const unescapedToken = data.token.replace(/\\n/g, '\n').replace(/\\"/g, '"').replace(/\\\\/g, '\\');
                  this.docQuestionAnswer += unescapedToken;
                }
                if (data.error) {
                  this.docQuestionError = data.error;
                }
              } catch (e) {
                // skip malformed SSE lines
              }
            }
          }
        }
      } catch (e) {
        this.docQuestionError = 'Ошибка сети при получении ответа';
      } finally {
        this.docQuestionLoading = false;
      }
    },

    // Upload methods
    handleDrop(event) {
      this.dragOver = false;
      const files = event.dataTransfer.files;
      this.handleFiles(files);
    },

    handleFiles(files) {
      for (const file of files) {
        this.uploadFile(file);
      }
    },

    async uploadFile(file) {
      const MAX_SIZE = 10 * 1024 * 1024; // 10 MB
      if (file.size > MAX_SIZE) {
        const id = this.nextUploadId++;
        this.uploads.push({ id, name: file.name, progress: 0, status: 'error', error: 'Файл превышает 10 МБ' });
        setTimeout(() => {
          this.uploads = this.uploads.filter(u => u.id !== id);
        }, 5000);
        return;
      }

      const id = this.nextUploadId++;
      const entry = { id, name: file.name, progress: 0, status: 'uploading', error: null };
      this.uploads.push(entry);

      const formData = new FormData();
      formData.append('files', file);

      try {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/documents/upload');

        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            entry.progress = Math.round((e.loaded / e.total) * 100);
          }
        });

        await new Promise((resolve, reject) => {
          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve(xhr.response);
            } else {
              reject(new Error(`HTTP ${xhr.status}`));
            }
          };
          xhr.onerror = () => reject(new Error('Network error'));
          xhr.send(formData);
        });

        entry.status = 'done';
        entry.progress = 100;

        // Refresh table to show new document, reset to page 1
        this.currentPage = 1;
        htmx.ajax('GET', this.buildTableUrl(), {target: '#document-table-container', swap: 'innerHTML'});

        setTimeout(() => {
          this.uploads = this.uploads.filter(u => u.id !== id);
        }, 3000);

      } catch (err) {
        entry.status = 'error';
        entry.error = err.message;
      }
    }
  }));
});
