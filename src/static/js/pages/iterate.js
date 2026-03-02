window.Pages = window.Pages || {};

let _selectedBookId = null;
let _unsubscribe = null;

function modelIdToLabel(modelId) {
  const model = OpenRouter.MODELS.find((m) => m.id === modelId);
  return model?.label || modelId;
}

function statusTagClass(status) {
  if (status === 'completed') return 'tag-success';
  if (status === 'failed' || status === 'cancelled') return 'tag-failed';
  if (status === 'queued') return 'tag-queued';
  return 'tag-pending';
}

function qualityClass(score) {
  if (score >= 0.75) return 'high';
  if (score >= 0.5) return 'medium';
  return 'low';
}

function resolvePrompt(templateObj, book, customPrompt) {
  if (customPrompt && customPrompt.trim()) return customPrompt.trim();
  const base = templateObj?.prompt_template || `Create a vivid circular illustration for "${book.title}" by ${book.author}.`;
  return String(base)
    .replaceAll('{title}', book.title)
    .replaceAll('{author}', book.author)
    .concat(' No text, no letters, no logos, no border, no frame, no ribbons, vivid colors.');
}

function renderModelCheckboxes(defaultChecked = 3) {
  return OpenRouter.MODELS.map((model, idx) => `
    <label class="checkbox-item">
      <input type="checkbox" class="iter-model-check" value="${model.id}" ${idx < defaultChecked ? 'checked' : ''} />
      <span>${model.label}</span>
      <span class="tag tag-gold">$${Number(model.cost || 0).toFixed(3)}</span>
    </label>
  `).join('');
}

window.Pages.iterate = {
  async render() {
    const content = document.getElementById('content');
    let books = DB.dbGetAll('books');
    if (!books.length) books = await DB.loadBooks('classics');

    const prompts = DB.dbGetAll('prompts');
    const options = books
      .sort((a, b) => Number(a.number || 0) - Number(b.number || 0))
      .map((book) => `<option value="${book.id}">${book.number}. ${book.title}</option>`)
      .join('');
    const promptOptions = ['<option value="">Default auto</option>']
      .concat(prompts.map((p) => `<option value="${p.id}">${p.name}</option>`))
      .join('');

    content.innerHTML = `
      <div class="card">
        <div class="card-header"><h3 class="card-title">Generate Illustrations</h3>
          <div class="filters-bar">
            <span class="text-muted">Quick</span>
            <label class="checkbox-item"><input id="iterModeToggle" type="checkbox" checked /> <span>Advanced</span></label>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">Book</label>
          <select class="form-select" id="iterBookSelect">
            <option value="">— Select a book —</option>
            ${options}
          </select>
        </div>

        <div id="iterAdvanced">
          <div class="form-group">
            <label class="form-label">Models (best → budget, top → bottom)</label>
            <div class="checkbox-group">${renderModelCheckboxes(3)}</div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Variants per model</label>
              <select class="form-select" id="iterVariants">${Array.from({ length: 10 }, (_, i) => `<option value="${i + 1}" ${i === 0 ? 'selected' : ''}>${i + 1}</option>`).join('')}</select>
            </div>
            <div class="form-group">
              <label class="form-label">Prompt template</label>
              <select class="form-select" id="iterPromptSel">${promptOptions}</select>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Custom prompt</label>
            <textarea class="form-textarea" id="iterPrompt" rows="4" placeholder="Override the prompt. Use {title} and {author} placeholders..."></textarea>
          </div>
        </div>

        <div class="flex justify-between items-center">
          <span class="text-muted" id="iterCostEst">Est. cost: $0.000</span>
          <div class="flex gap-8">
            <button class="btn btn-secondary" id="iterCancelBtn">Cancel All</button>
            <button class="btn btn-primary" id="iterGenBtn">Generate</button>
          </div>
        </div>
      </div>

      <div class="card hidden" id="pipelineCard">
        <div class="card-header"><h3 class="card-title">Running Jobs</h3></div>
        <div class="pipeline" id="pipelineArea"></div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Recent Results</h3>
          <span class="text-muted" id="iterResultCount">0 results</span>
        </div>
        <div class="grid-auto" id="resultsGrid"></div>
      </div>
    `;

    const selectEl = document.getElementById('iterBookSelect');
    const modeToggle = document.getElementById('iterModeToggle');
    const advanced = document.getElementById('iterAdvanced');
    const variantsEl = document.getElementById('iterVariants');

    modeToggle?.addEventListener('change', () => {
      advanced.classList.toggle('hidden', !modeToggle.checked);
    });

    selectEl?.addEventListener('change', () => {
      _selectedBookId = Number(selectEl.value || 0) || null;
      this.loadExistingResults();
    });

    const updateCost = () => {
      const selected = Array.from(document.querySelectorAll('.iter-model-check:checked')).map((el) => el.value);
      const variants = Number(variantsEl?.value || 1);
      const total = selected.reduce((sum, modelId) => sum + Number(OpenRouter.MODEL_COSTS[modelId] || 0) * variants, 0);
      const est = document.getElementById('iterCostEst');
      if (est) est.textContent = `Est. cost: $${total.toFixed(3)}`;
    };

    document.querySelectorAll('.iter-model-check').forEach((el) => el.addEventListener('change', updateCost));
    variantsEl?.addEventListener('change', updateCost);
    updateCost();

    document.getElementById('iterCancelBtn')?.addEventListener('click', () => JobQueue.cancelAll());
    document.getElementById('iterGenBtn')?.addEventListener('click', () => this.handleGenerate(books));

    if (_unsubscribe) _unsubscribe();
    _unsubscribe = JobQueue.onChange((snapshot) => {
      this.updatePipeline(snapshot.all || []);
      this.loadExistingResults();
    });

    const initialBook = Number(window.__ITERATE_BOOK_ID__ || 0);
    if (initialBook && books.some((b) => Number(b.id) === initialBook)) {
      selectEl.value = String(initialBook);
      _selectedBookId = initialBook;
    }
    this.loadExistingResults();
  },

  async handleGenerate(books) {
    const bookId = Number(document.getElementById('iterBookSelect')?.value || 0);
    if (!bookId) {
      Toast.warning('Select a book first.');
      return;
    }
    const selectedModels = Array.from(document.querySelectorAll('.iter-model-check:checked')).map((el) => el.value);
    if (!selectedModels.length) {
      Toast.warning('Select at least one model.');
      return;
    }

    const variantCount = Number(document.getElementById('iterVariants')?.value || 1);
    const promptId = Number(document.getElementById('iterPromptSel')?.value || 0);
    const customPrompt = document.getElementById('iterPrompt')?.value || '';
    const book = books.find((b) => Number(b.id) === bookId);
    if (!book) return;

    const templateObj = DB.dbGet('prompts', promptId);
    const styleSelections = StyleDiversifier.selectDiverseStyles(selectedModels.length * variantCount);

    const jobs = [];
    let styleIndex = 0;
    selectedModels.forEach((model) => {
      for (let variant = 1; variant <= variantCount; variant += 1) {
        const style = styleSelections[styleIndex % styleSelections.length];
        styleIndex += 1;
        const basePrompt = resolvePrompt(templateObj, book, customPrompt);
        const prompt = StyleDiversifier.buildDiversifiedPrompt(book.title, book.author, style) + ' ' + basePrompt;
        jobs.push({
          id: uuid(),
          book_id: bookId,
          model,
          variant,
          status: 'queued',
          prompt,
          style_id: style?.id || 'none',
          style_label: style?.label || 'Default',
          quality_score: null,
          cost_usd: 0,
          generated_image_blob: null,
          composited_image_blob: null,
          started_at: null,
          completed_at: null,
          error: null,
          results_json: null,
          retries: 0,
          _elapsed: 0,
          _subStatus: '',
          _compositeFailed: false,
          _compositeError: null,
          created_at: new Date().toISOString(),
        });
      }
    });

    JobQueue.addBatch(jobs);
    document.getElementById('pipelineCard')?.classList.remove('hidden');
    Toast.success(`${jobs.length} job(s) queued.`);
  },

  updatePipeline(allJobs) {
    const area = document.getElementById('pipelineArea');
    const card = document.getElementById('pipelineCard');
    if (!area || !_selectedBookId) {
      card?.classList.add('hidden');
      return;
    }

    const active = allJobs.filter((job) => Number(job.book_id) === Number(_selectedBookId) && !['completed', 'failed', 'cancelled'].includes(job.status));
    if (!active.length) {
      area.innerHTML = '<div class="text-muted text-sm">No active jobs.</div>';
      card?.classList.add('hidden');
      return;
    }
    card?.classList.remove('hidden');

    const mapStatusToStep = (status) => {
      if (status === 'downloading_cover') return 0;
      if (status === 'generating' || status === 'retrying') return 1;
      if (status === 'scoring') return 2;
      if (status === 'compositing') return 3;
      return -1;
    };

    area.innerHTML = active.map((job) => {
      const step = mapStatusToStep(job.status);
      const steps = ['⬇ Cover', '⚡ Generate', '⭐ Score', '🎨 Composite'];
      const renderedSteps = steps.map((label, idx) => {
        let cls = 'pipeline-step';
        if (idx < step) cls += ' done';
        if (idx === step) cls += ' active heartbeat-pulse';
        return `<span class="${cls}">${label}</span>`;
      }).join('');
      const book = DB.dbGet('books', job.book_id);
      return `
        <div class="pipeline-row">
          <span class="text-sm fw-600">${book?.title || `Book ${job.book_id}`} · v${job.variant}</span>
          <div class="pipeline-steps">${renderedSteps}</div>
          <span class="text-xs text-muted">${job._elapsed || 0}s</span>
          <span class="text-xs text-muted">${job._subStatus || ''}</span>
          <button class="btn-cancel-job" data-cancel="${job.id}">Cancel</button>
          <span class="text-xs">$${Number(job.cost_usd || 0).toFixed(3)}</span>
        </div>
      `;
    }).join('');

    area.querySelectorAll('[data-cancel]').forEach((btn) => {
      btn.addEventListener('click', () => JobQueue.abortJob(btn.dataset.cancel, 'Cancelled by user'));
    });
  },

  loadExistingResults() {
    const grid = document.getElementById('resultsGrid');
    const count = document.getElementById('iterResultCount');
    if (!grid || !_selectedBookId) {
      if (grid) grid.innerHTML = '<div class="text-muted">Select a book and generate illustrations</div>';
      if (count) count.textContent = '0 results';
      return;
    }

    const jobs = DB.dbGetByIndex('jobs', 'book_id', _selectedBookId)
      .filter((j) => ['completed', 'failed', 'cancelled'].includes(j.status))
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 20);

    if (!jobs.length) {
      grid.innerHTML = '<div class="text-muted">No results yet</div>';
      if (count) count.textContent = '0 results';
      return;
    }

    if (count) count.textContent = `${jobs.length} result${jobs.length === 1 ? '' : 's'}`;
    grid.innerHTML = jobs.map((job) => {
      const src = getBlobUrl(job.composited_image_blob || job.generated_image_blob, `${job.id}-display`);
      const quality = Number(job.quality_score || 0);
      return `
        <div class="result-card" data-view="${job.id}">
          <img class="thumb" src="${src}" alt="result" />
          <div class="card-body">
            <div class="flex justify-between">
              <span class="tag tag-model">${modelIdToLabel(job.model)}</span>
              <span class="tag ${statusTagClass(job.status)}">${job.status}</span>
            </div>
            <div class="quality-meter">
              <div class="quality-bar"><div class="quality-fill ${qualityClass(quality)}" style="width:${Math.round(quality * 100)}%"></div></div>
            </div>
            <div class="card-meta">$${Number(job.cost_usd || 0).toFixed(3)} · ${job.style_label || 'Default'}</div>
            <div class="flex gap-4 mt-8">
              <button class="btn btn-secondary btn-sm" data-dl-comp="${job.id}">⬇ Composite</button>
              <button class="btn btn-secondary btn-sm" data-dl-raw="${job.id}">⬇ Raw</button>
              <button class="btn btn-secondary btn-sm" data-save-prompt="${job.id}">💾 Prompt</button>
            </div>
          </div>
        </div>
      `;
    }).join('');

    grid.querySelectorAll('[data-view]').forEach((el) => {
      el.addEventListener('click', (event) => {
        if (event.target.closest('button')) return;
        this.viewFull(el.dataset.view, 'composite');
      });
    });
    grid.querySelectorAll('[data-dl-comp]').forEach((btn) => btn.addEventListener('click', (e) => { e.stopPropagation(); this.downloadComposite(btn.dataset.dlComp); }));
    grid.querySelectorAll('[data-dl-raw]').forEach((btn) => btn.addEventListener('click', (e) => { e.stopPropagation(); this.downloadGenerated(btn.dataset.dlRaw); }));
    grid.querySelectorAll('[data-save-prompt]').forEach((btn) => btn.addEventListener('click', (e) => { e.stopPropagation(); this.savePromptFromJob(btn.dataset.savePrompt); }));
  },

  viewFull(jobId, mode = 'composite') {
    const job = DB.dbGet('jobs', jobId);
    if (!job) return;
    const composite = getBlobUrl(job.composited_image_blob || job.generated_image_blob, `${job.id}-composite`);
    const raw = getBlobUrl(job.generated_image_blob || job.composited_image_blob, `${job.id}-raw`);
    const state = { mode };

    const overlay = document.createElement('div');
    overlay.className = 'view-modal';
    overlay.innerHTML = `
      <div class="view-modal-inner">
        <div class="modal-header">
          <h3 class="modal-title">Preview · ${modelIdToLabel(job.model)} · v${job.variant}</h3>
          <button class="close-btn" id="viewCloseBtn">×</button>
        </div>
        <div class="modal-body">
          <div class="tabs">
            <button class="tab ${state.mode === 'composite' ? 'active' : ''}" data-mode="composite">Composite</button>
            <button class="tab ${state.mode === 'raw' ? 'active' : ''}" data-mode="raw">Raw</button>
          </div>
          <img id="viewImg" src="${state.mode === 'composite' ? composite : raw}" style="width:100%;height:auto;border-radius:8px;border:1px solid var(--border)" />
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    const update = () => {
      overlay.querySelector('#viewImg').src = state.mode === 'composite' ? composite : raw;
      overlay.querySelectorAll('.tab').forEach((tab) => tab.classList.toggle('active', tab.dataset.mode === state.mode));
    };

    overlay.querySelectorAll('.tab').forEach((tab) => tab.addEventListener('click', () => {
      state.mode = tab.dataset.mode;
      update();
    }));
    overlay.querySelector('#viewCloseBtn')?.addEventListener('click', () => overlay.remove());
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
  },

  downloadComposite(jobId) {
    const job = DB.dbGet('jobs', jobId);
    if (!job) return;
    const href = getBlobUrl(job.composited_image_blob || job.generated_image_blob, `${job.id}-dlc`);
    const a = document.createElement('a');
    a.href = href;
    a.download = `${job.book_id}-${job.model.replaceAll('/', '_')}-v${job.variant}-composite.jpg`;
    a.click();
  },

  downloadGenerated(jobId) {
    const job = DB.dbGet('jobs', jobId);
    if (!job) return;
    const href = getBlobUrl(job.generated_image_blob || job.composited_image_blob, `${job.id}-dlg`);
    const a = document.createElement('a');
    a.href = href;
    a.download = `${job.book_id}-${job.model.replaceAll('/', '_')}-v${job.variant}-raw.jpg`;
    a.click();
  },

  savePromptFromJob(jobId) {
    const job = DB.dbGet('jobs', jobId);
    if (!job?.prompt) return;
    DB.dbPut('prompts', {
      name: `Saved Prompt ${new Date().toLocaleString()}`,
      prompt_template: job.prompt,
      category: 'Saved',
      created_at: new Date().toISOString(),
      usage_count: 0,
      win_count: 0,
    });
    Toast.success('Prompt saved');
  },
};
