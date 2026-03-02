window.Pages = window.Pages || {};

window.Pages.dashboard = {
  async render() {
    const content = document.getElementById('content');
    const jobs = DB.dbGetAll('jobs');
    const ledger = DB.dbGetAll('cost_ledger');
    const winners = DB.dbGetAll('winners');
    const booksCount = DB.dbCount('books');

    const spent = ledger.reduce((sum, row) => sum + Number(row.cost_usd || 0), 0);
    const budget = Number(DB.getSetting('budget_limit', 50));
    const completedJobs = jobs.filter((j) => j.status === 'completed');
    const avgQuality = completedJobs.length ? completedJobs.reduce((sum, j) => sum + Number(j.quality_score || 0), 0) / completedJobs.length : 0;

    const byModel = new Map();
    ledger.forEach((row) => {
      const key = row.model || 'unknown';
      const value = byModel.get(key) || { model: key, jobs: 0, cost: 0, qualitySum: 0 };
      value.jobs += 1;
      value.cost += Number(row.cost_usd || 0);
      const job = DB.dbGet('jobs', row.job_id);
      value.qualitySum += Number(job?.quality_score || 0);
      byModel.set(key, value);
    });

    const recent = jobs
      .filter((j) => ['completed', 'failed'].includes(j.status))
      .sort((a, b) => new Date(b.completed_at || b.created_at).getTime() - new Date(a.completed_at || a.created_at).getTime())
      .slice(0, 10);

    const budgetPct = budget > 0 ? Math.min(100, Math.round((spent / budget) * 100)) : 0;

    content.innerHTML = `
      <div class="kpi-grid">
        <div class="kpi-card"><div class="kpi-label">Total Spent</div><div class="kpi-value">$${spent.toFixed(2)}</div><div class="progress-bar mt-8"><div class="progress-fill ${budgetPct > 90 ? 'danger' : ''}" style="width:${budgetPct}%"></div></div><div class="kpi-sub">$${spent.toFixed(2)} of $${budget.toFixed(2)} budget used</div></div>
        <div class="kpi-card"><div class="kpi-label">Books in Catalog</div><div class="kpi-value">${booksCount}</div></div>
        <div class="kpi-card"><div class="kpi-label">Avg Quality</div><div class="kpi-value">${Math.round(avgQuality * 100)}%</div></div>
        <div class="kpi-card"><div class="kpi-label">Total Images</div><div class="kpi-value">${completedJobs.length}</div></div>
        <div class="kpi-card"><div class="kpi-label">Approved</div><div class="kpi-value">${winners.length}</div></div>
      </div>

      <div class="grid-2">
        <div class="card">
          <h3 class="card-title mb-8">Model Breakdown</h3>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Model</th><th>Jobs</th><th>Cost</th><th>Avg Quality</th></tr></thead>
              <tbody>
                ${[...byModel.values()].map((row) => `<tr><td>${row.model}</td><td>${row.jobs}</td><td>$${row.cost.toFixed(3)}</td><td>${Math.round((row.qualitySum / Math.max(1, row.jobs)) * 100)}%</td></tr>`).join('') || '<tr><td colspan="4" class="text-muted">No cost entries yet.</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <h3 class="card-title mb-8">Recent Activity</h3>
          <div>
            ${recent.map((job) => {
              const book = DB.dbGet('books', job.book_id);
              return `<div class="activity-item"><div class="activity-dot ${job.status === 'failed' ? 'failed' : ''}"></div><div><div class="activity-text">${book?.title || `Book ${job.book_id}`} — ${job.model} (${job.status})</div><div class="activity-time">${timeAgo(job.completed_at || job.created_at)}</div></div></div>`;
            }).join('') || '<p class="text-muted">No activity yet.</p>'}
          </div>
        </div>
      </div>
    `;
  },
};
