window.Pages = window.Pages || {};

function esc(str) {
  return String(str || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

window.Pages.prompts = {
  _builtinPrompts: [
    { name: 'Sevastopol / Dramatic Conflict', category: 'Cossacks/Military', template: 'Create a powerful circular medallion illustration for "{title}" by {author}. Depict a dramatic battle or conflict scene with figures in dynamic motion, smoke, fire, and chaos. Rich dramatic lighting, deep shadows and highlights. Oil painting style with broad confident brushstrokes. Circular vignette composition, edges fading to black.', negative_prompt: 'modern weapons, anachronistic elements', style_profile: 'Classical Oil' },
    { name: 'Cossack / Epic Journey', category: 'Cossacks/Military', template: 'Create a sweeping circular medallion illustration for "{title}" by {author}. Show a lone Cossack rider on horseback crossing a vast steppe landscape under a dramatic sky. Epic scale, sense of adventure and freedom. Rich earth tones and golden light. Circular vignette, figure centred.', negative_prompt: '', style_profile: 'Romantic Landscape' },
    { name: 'Golden Atmosphere', category: 'Classical Library', template: 'Create a luminous circular medallion illustration for "{title}" by {author}. Suffuse the scene with warm golden-hour light filtering through trees or windows. Soft, nostalgic, painterly quality. The key scene or symbol from this story, rendered in a circular vignette with the subject centred.', negative_prompt: 'harsh lighting, cold colors', style_profile: 'Romantic Landscape' },
    { name: 'Dark Romantic', category: 'Classical Library', template: 'Create a moody, atmospheric circular medallion illustration for "{title}" by {author}. Deep shadows, mysterious midnight blues and greens, a single source of dramatic light. Gothic romanticism. The most emotionally resonant scene from this story as a circular vignette.', negative_prompt: 'bright cheerful, pastel', style_profile: 'Dark Romantic' },
    { name: 'Gentle Nostalgia', category: 'Classical Library', template: 'Create a tender, nostalgic circular medallion illustration for "{title}" by {author}. Soft watercolour washes, gentle morning light, a quiet pastoral or domestic scene from the story. Delicate, sentimental mood. Circular vignette, softly fading edges.', negative_prompt: 'dramatic, violent, harsh', style_profile: 'Delicate Watercolour' },
    { name: 'Art Nouveau Symbolic', category: 'Wildcard', template: 'Create a decorative Art Nouveau circular medallion illustration for "{title}" by {author}. Sinuous organic lines, stylised botanical motifs, symbolic figures. Flat areas of rich colour with fine linear detail. The central symbolic element of the story encircled by flowing ornamental borders.', negative_prompt: 'photorealistic, 3D render', style_profile: 'Art Nouveau' },
    { name: 'Ukiyo-e Reimagining', category: 'Wildcard', template: 'Reimagine the world of "{title}" by {author} as a Japanese ukiyo-e woodblock print circular medallion. Bold outlines, flat areas of colour, dynamic diagonal compositions, stylised natural elements. A key scene or iconic moment from the story.', negative_prompt: 'western art style, photorealistic', style_profile: 'Ukiyo-e Woodblock' },
    { name: 'Noir Tension', category: 'Wildcard', template: 'Create a film noir circular medallion illustration for "{title}" by {author}. Stark black and white with deep shadows, dramatic chiaroscuro lighting, a figure in silhouette or partial shadow. The moment of highest tension or mystery in the story.', negative_prompt: 'colour, bright, cheerful', style_profile: 'Film Noir' },
    { name: 'Natural History Study', category: 'Wildcard', template: 'Create a detailed botanical/natural history engraving style circular medallion for "{title}" by {author}. Fine crosshatching, precise scientific illustration aesthetic, sepia tones with delicate colour washes. The central natural or symbolic motif of the story.', negative_prompt: 'painterly, loose, abstract', style_profile: 'Botanical Engraving' },
  ],

  async render() {
    const content = document.getElementById('content');
    content.innerHTML = `
      <div class="card">
        <div class="flex justify-between mb-8">
          <h3 class="card-title">Prompt Templates</h3>
          <div class="flex gap-8">
            <button class="btn btn-secondary" id="promptSeedBtn">Seed Built-in Prompts</button>
            <button class="btn btn-primary" id="promptNewBtn">+ New Prompt</button>
          </div>
        </div>
        <div class="grid-3" id="promptGrid"></div>
      </div>
    `;

    document.getElementById('promptSeedBtn')?.addEventListener('click', () => this.seedBuiltins());
    document.getElementById('promptNewBtn')?.addEventListener('click', () => this.openPromptModal(null));
    this.renderGrid();
  },

  renderGrid() {
    const grid = document.getElementById('promptGrid');
    if (!grid) return;
    const prompts = DB.dbGetAll('prompts').sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());
    if (!prompts.length) {
      grid.innerHTML = '<div class="text-muted">No prompts saved yet.</div>';
      return;
    }

    grid.innerHTML = prompts.map((prompt) => `
      <div class="prompt-card">
        <div class="flex justify-between">
          <span class="fw-600">${esc(prompt.name)}</span>
          <span class="tag tag-style">${esc(prompt.category || 'Saved')}</span>
        </div>
        <p class="text-sm text-muted mt-8">${esc((prompt.prompt_template || '').slice(0, 120))}${(prompt.prompt_template || '').length > 120 ? '…' : ''}</p>
        <div class="flex gap-4 mt-8">
          <button class="btn btn-sm btn-secondary" data-edit="${prompt.id}">Edit</button>
          <button class="btn btn-sm btn-danger" data-delete="${prompt.id}">Delete</button>
        </div>
      </div>
    `).join('');

    grid.querySelectorAll('[data-edit]').forEach((btn) => {
      btn.addEventListener('click', () => this.openPromptModal(DB.dbGet('prompts', Number(btn.dataset.edit) || btn.dataset.edit)));
    });
    grid.querySelectorAll('[data-delete]').forEach((btn) => {
      btn.addEventListener('click', () => {
        DB.dbDelete('prompts', Number(btn.dataset.delete) || btn.dataset.delete);
        Toast.success('Prompt deleted');
        this.renderGrid();
      });
    });
  },

  openPromptModal(existing) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    const isEdit = Boolean(existing);

    overlay.innerHTML = `
      <div class="modal">
        <div class="modal-header"><h2 class="modal-title">${isEdit ? 'Edit Prompt' : 'New Prompt'}</h2><button class="close-btn">×</button></div>
        <div class="modal-body">
          <div class="form-group"><label class="form-label">Name</label><input id="promptName" class="form-input" value="${esc(existing?.name || '')}" /></div>
          <div class="form-group"><label class="form-label">Category</label>
            <select id="promptCategory" class="form-select">
              ${['style', 'mood', 'subject', 'Cossacks/Military', 'Classical Library', 'Wildcard', 'Saved'].map((c) => `<option value="${c}" ${existing?.category === c ? 'selected' : ''}>${c}</option>`).join('')}
            </select>
          </div>
          <div class="form-group"><label class="form-label">Template</label><textarea id="promptTemplate" class="form-textarea" rows="6">${esc(existing?.prompt_template || '')}</textarea></div>
          <div class="form-group"><label class="form-label">Negative Prompt</label><textarea id="promptNegative" class="form-textarea" rows="3">${esc(existing?.negative_prompt || '')}</textarea></div>
          <div class="form-group"><label class="form-label">Style Profile</label><input id="promptStyleProfile" class="form-input" value="${esc(existing?.style_profile || '')}" /></div>
          <div class="card">
            <div class="form-row">
              <input id="previewTitle" class="form-input" placeholder="Book title" value="Moby Dick" />
              <input id="previewAuthor" class="form-input" placeholder="Author" value="Herman Melville" />
            </div>
            <p class="text-sm mt-8" id="previewOutput"></p>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" id="promptCancelBtn">Cancel</button>
          <button class="btn btn-primary" id="promptSaveBtn">Save</button>
        </div>
      </div>
    `;

    const close = () => overlay.remove();
    const updatePreview = () => {
      const t = overlay.querySelector('#promptTemplate').value || '';
      const title = overlay.querySelector('#previewTitle').value || 'Book';
      const author = overlay.querySelector('#previewAuthor').value || 'Author';
      overlay.querySelector('#previewOutput').textContent = t.replaceAll('{title}', title).replaceAll('{author}', author);
    };

    ['#promptTemplate', '#previewTitle', '#previewAuthor'].forEach((sel) => {
      overlay.querySelector(sel).addEventListener('input', updatePreview);
    });
    updatePreview();

    overlay.querySelector('.close-btn')?.addEventListener('click', close);
    overlay.querySelector('#promptCancelBtn')?.addEventListener('click', close);
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });

    overlay.querySelector('#promptSaveBtn')?.addEventListener('click', () => {
      const payload = {
        id: existing?.id,
        name: overlay.querySelector('#promptName').value.trim(),
        category: overlay.querySelector('#promptCategory').value,
        prompt_template: overlay.querySelector('#promptTemplate').value.trim(),
        negative_prompt: overlay.querySelector('#promptNegative').value.trim(),
        style_profile: overlay.querySelector('#promptStyleProfile').value.trim(),
        created_at: existing?.created_at || new Date().toISOString(),
      };
      if (!payload.name || !payload.prompt_template) {
        Toast.warning('Name and template are required.');
        return;
      }
      DB.dbPut('prompts', payload);
      Toast.success('Prompt saved');
      close();
      this.renderGrid();
    });

    document.body.appendChild(overlay);
  },

  seedBuiltins() {
    const now = new Date().toISOString();
    this._builtinPrompts.forEach((prompt) => {
      DB.dbPut('prompts', {
        name: prompt.name,
        category: prompt.category,
        prompt_template: prompt.template,
        negative_prompt: prompt.negative_prompt,
        style_profile: prompt.style_profile,
        created_at: now,
      });
    });
    Toast.success('9 prompts seeded');
    this.renderGrid();
  },
};
