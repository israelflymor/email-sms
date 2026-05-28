const state = {
  auth: (() => { try { return JSON.parse(localStorage.getItem('admin_auth') || 'null'); } catch { return null; } })(),
  page: 'overview',
  overview: null, metrics: null, alerts: [], paused: [], campaigns: [], segments: []
};

function saveAuth(auth){ localStorage.setItem('admin_auth', JSON.stringify(auth)); }
function clearAuth(){ localStorage.removeItem('admin_auth'); }

function canAccess(page, role){
  if (role === 'admin') return true;
  if (role === 'viewer') return ['overview','monitoring','settings'].includes(page);
  if (role === 'reviewer') return ['overview','paused','campaigns','monitoring','settings'].includes(page);
  if (role === 'operator') return ['overview','segments','campaigns','paused','monitoring','settings'].includes(page);
  return false;
}

async function request(path, opts = {}){
  const headers = {'Content-Type': 'application/json', ...(opts.headers || {})};
  if (state.auth?.token) headers['Authorization'] = `Bearer ${state.auth.token}`;
  const res = await fetch(`/api${path}`, {...opts, headers});
  const text = await res.text();
  let body = {};
  try { body = text ? JSON.parse(text) : {}; } catch {}
  if (!res.ok) throw new Error(body.detail || body.error || `Request failed (${res.status})`);
  return body;
}

function tag(value){
  const v = String(value || '').toLowerCase();
  let cls = 'info';
  if (['approved','sent','success','healthy','active','required'].includes(v)) cls = 'success';
  if (['paused','warning','pending','queued','approved_for_retry','optional'].includes(v)) cls = 'warning';
  if (['rejected','failed','blocked','error'].includes(v)) cls = 'danger';
  return `<span class="tag ${cls}">${value || '-'}</span>`;
}

function kpi(label, value){ return `<div class="card kpi"><div class="label">${label}</div><div class="value">${value}</div></div>`; }

function table(headers, rows){
  if (!rows.length) return '<div class="muted">No records found.</div>';
  return `<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}

function renderLogin(error=''){
  document.getElementById('app').innerHTML = `
    <div class="login-shell">
      <div class="card login-card">
        <h2 style="margin-top:0">Admin Sign In</h2>
        <p class="muted">Internal messaging operations access</p>
        <label class="muted small">Username</label>
        <input id="loginUsername" value="admin" />
        <label class="muted small" style="margin-top:8px">Password</label>
        <input id="loginPassword" type="password" />
        ${error ? `<div class="error">${error}</div>` : ''}
        <div style="margin-top:16px"><button id="loginBtn">Sign in</button></div>
      </div>
    </div>`;
  document.getElementById('loginBtn').onclick = async () => {
    try {
      const result = await request('/auth/login', {method:'POST', body: JSON.stringify({username: document.getElementById('loginUsername').value, password: document.getElementById('loginPassword').value})});
      state.auth = { ...result, token: result.access_token }; saveAuth(state.auth); await refreshAll(); renderApp();
    } catch(e){ renderLogin(e.message); }
  };
}

function sidebar(role){
  const pages = [['overview','Overview'],['segments','Segments'],['campaigns','Campaigns'],['paused','Paused Jobs'],['monitoring','Monitoring'],['settings','Settings']]
    .filter(([k]) => canAccess(k, role));
  return pages.map(([k,l])=>`<a href="#" class="nav-link ${state.page===k?'active':''}" data-page="${k}">${l}</a>`).join('');
}

function shell(content){
  return `<div class="app-shell">
    <aside class="sidebar">
      <h2>Control Plane</h2><p>US SMS operations and compliance</p>
      <nav>${sidebar(state.auth.role)}</nav>
    </aside>
    <main class="content">
      <div class="topbar">
        <div><div class="muted small">Internal environment</div><h1 style="margin:4px 0 0 0">Messaging Control Plane</h1></div>
        <div class="row">
          <div class="card" style="padding:10px 14px;margin:0"><div class="muted small">Role</div><div>${state.auth.role}</div></div>
          <button class="secondary" id="logoutBtn">Logout</button>
        </div>
      </div>
      ${content}
    </main>
  </div>`;
}

function overviewPage(){
  const o = state.overview || {}, m = state.metrics || {};
  return `
    <div class="kpi-grid">
      ${kpi('Campaigns', o.total_campaigns || 0)}
      ${kpi('Segments', o.total_segments || 0)}
      ${kpi('Paused Jobs', o.paused_jobs || 0)}
      ${kpi('Retry Ready', m.retry_ready_jobs || 0)}
      ${kpi('Open Alerts', o.open_alerts || 0)}
    </div>
    <div class="card"><h3>Metrics snapshot</h3><div class="row">
      <div>Attempts: <strong>${m.attempts_total || 0}</strong></div>
      <div>Sent: <strong>${m.sent_total || 0}</strong></div>
      <div>Failed: <strong>${m.failed_total || 0}</strong></div>
      <div>Queued: <strong>${m.queued_jobs || 0}</strong></div>
    </div></div>
    <div class="card"><h3>Open alerts</h3>
      ${table(['Level','Code','Message'], state.alerts.map(a=>[tag(a.level), a.code, a.message]))}
    </div>`;
}

function segmentsPage(){
  return `
    <div class="card">
      <h3>Create segment</h3>
      <div class="form-grid">
        <input id="seg_name" placeholder="Segment name" />
        <input id="seg_desc" placeholder="Description" />
        <input id="seg_cat" placeholder="Category filter" />
        <input id="seg_country" value="US" placeholder="Country code" />
      </div>
      <div style="margin-top:12px" class="row">
        <label class="muted small"><input id="seg_consent" type="checkbox" checked style="width:auto;margin-right:8px" />Requires marketing consent</label>
        <button id="createSegmentBtn">Create segment</button>
      </div>
    </div>
    <div class="card">
      <h3>Segment list</h3>
      ${table(['Name','Country','Category Filter','Consent','Actions'],
        state.segments.map(s=>[
          s.name, s.country_code || '-', s.category_filter || '-', tag(s.requires_marketing_consent ? 'required' : 'optional'),
          `<button data-action="gen-segment" data-id="${s.id}">Generate members</button>`
        ]))}
    </div>`;
}

function campaignsPage(){
  const options = ['<option value="">Select segment</option>'].concat(state.segments.map(s=>`<option value="${s.id}">${s.name}</option>`)).join('');
  return `
    <div class="card">
      <h3>Create campaign</h3>
      <div class="form-grid">
        <input id="camp_name" placeholder="Campaign name" />
        <select id="camp_category"><option value="promotional">promotional</option><option value="transactional">transactional</option></select>
        <select id="camp_segment">${options}</select>
        <input id="camp_daily" type="number" value="1000" placeholder="Daily cap" />
      </div>
      <div style="margin-top:12px" class="row">
        <input id="camp_hourly" type="number" value="100" placeholder="Hourly cap" style="max-width:240px" />
        <button id="createCampaignBtn">Create campaign</button>
      </div>
    </div>
    <div class="card">
      <h3>Campaign list</h3>
      ${table(['Name','Category','Status','Segment','Daily Cap','Hourly Cap','Actions'],
        state.campaigns.map(c=>[
          c.name, c.category, tag(c.status), c.segment_id || '-', c.daily_cap, c.hourly_cap,
          `<div class="row">
            <button data-action="approve-campaign" data-id="${c.id}">Approve</button>
            <button class="secondary" data-action="pause-campaign" data-id="${c.id}">Pause</button>
            <button class="secondary" data-action="gen-campaign" data-id="${c.id}">Generate members</button>
            <button class="warning" data-action="dispatch-campaign" data-id="${c.id}">Dispatch batch</button>
          </div>`
        ]))}
    </div>`;
}

function pausedPage(){
  return `
    <div class="card">
      <h3>Paused jobs review</h3>
      ${table(['Job ID','Campaign','Reason','Review','Retry Count','Actions'],
        state.paused.map(p=>[
          p.job_id, p.campaign_id || '-', p.pause_reason || '-', tag(p.review_status || 'pending'), p.retry_count ?? 0,
          `<div class="row">
            <button data-action="approve-job" data-id="${p.job_id}">Approve</button>
            <button class="secondary" data-action="retry-job" data-id="${p.job_id}">Retry</button>
            <button class="danger" data-action="reject-job" data-id="${p.job_id}">Reject</button>
          </div>`
        ]))}
    </div>`;
}

function monitoringPage(){
  const m = state.metrics || {};
  return `
    <div class="card"><h3>Service health</h3><div class="row">
      <div>API: ${tag('healthy')}</div><div>Webhook: ${tag('healthy')}</div><div>Worker: ${tag('healthy')}</div>
      <div>Scheduler: ${tag('healthy')}</div><div>DB: ${tag('healthy')}</div><div>Redis: ${tag('healthy')}</div>
    </div></div>
    <div class="card"><h3>Messaging metrics</h3><div class="row">
      <div>Attempts: <strong>${m.attempts_total || 0}</strong></div>
      <div>Sent: <strong>${m.sent_total || 0}</strong></div>
      <div>Failed: <strong>${m.failed_total || 0}</strong></div>
      <div>Retry Ready: <strong>${m.retry_ready_jobs || 0}</strong></div>
    </div></div>
    <div class="card"><h3>Open alerts</h3>${table(['Level','Code','Message'], state.alerts.map(a=>[tag(a.level), a.code, a.message]))}</div>`;
}

function settingsPage(){
  return `<div class="card"><h3>Current session</h3>
    <p><strong>Role:</strong> ${state.auth.role}</p>
    <p><strong>Auth mode:</strong> Bearer token session issued by backend login endpoint.</p>
    <p class="muted">This is internal-only auth. Next upgrade should be real JWT/session auth with stored users, passwords, MFA, and audit logs.</p>
  </div>`;
}

async function refreshAll(){
  const [overview, metrics, alerts, paused, campaigns, segments] = await Promise.all([
    request('/admin/dashboard/overview'),
    request('/admin/metrics/summary'),
    request('/admin/alerts'),
    request('/admin/dashboard/paused-jobs'),
    request('/admin/campaigns'),
    request('/admin/segments')
  ]);
  state.overview = overview;
  state.metrics = metrics;
  state.alerts = alerts.items || [];
  state.paused = paused.items || [];
  state.campaigns = campaigns.items || [];
  state.segments = segments.items || [];
}

function attachHandlers(){
  document.querySelectorAll('.nav-link').forEach(el => {
    el.onclick = async (e) => { e.preventDefault(); state.page = el.dataset.page; renderApp(); };
  });
  const logout = document.getElementById('logoutBtn');
  if (logout) logout.onclick = () => { clearAuth(); state.auth = null; renderLogin(); };

  const createSegmentBtn = document.getElementById('createSegmentBtn');
  if (createSegmentBtn) createSegmentBtn.onclick = async () => {
    await request('/admin/segments', {method:'POST', body: JSON.stringify({
      name: document.getElementById('seg_name').value,
      description: document.getElementById('seg_desc').value,
      category_filter: document.getElementById('seg_cat').value,
      country_code: document.getElementById('seg_country').value,
      requires_marketing_consent: document.getElementById('seg_consent').checked
    })});
    await refreshAll(); renderApp();
  };

  const createCampaignBtn = document.getElementById('createCampaignBtn');
  if (createCampaignBtn) createCampaignBtn.onclick = async () => {
    await request('/admin/campaigns', {method:'POST', body: JSON.stringify({
      name: document.getElementById('camp_name').value,
      category: document.getElementById('camp_category').value,
      segment_id: document.getElementById('camp_segment').value || null,
      daily_cap: Number(document.getElementById('camp_daily').value || 1000),
      hourly_cap: Number(document.getElementById('camp_hourly').value || 100)
    })});
    await refreshAll(); renderApp();
  };

  document.querySelectorAll('[data-action]').forEach(el => {
    el.onclick = async () => {
      const id = el.dataset.id;
      const action = el.dataset.action;
      if (action === 'gen-segment') await request(`/admin/segments/${id}/generate-members`, {method:'POST'});
      if (action === 'approve-campaign') await request(`/admin/campaigns/${id}/approve`, {method:'POST'});
      if (action === 'pause-campaign') await request(`/admin/campaigns/${id}/pause`, {method:'POST'});
      if (action === 'gen-campaign') await request(`/admin/campaigns/${id}/generate-members`, {method:'POST'});
      if (action === 'dispatch-campaign') await request(`/admin/campaigns/${id}/dispatch-batch`, {method:'POST'});
      if (action === 'approve-job') await request(`/admin/reviews/jobs/${id}/approve`, {method:'POST', body: JSON.stringify({reviewer:'ui_reviewer'})});
      if (action === 'reject-job') await request(`/admin/reviews/jobs/${id}/reject`, {method:'POST', body: JSON.stringify({reviewer:'ui_reviewer'})});
      if (action === 'retry-job') await request(`/admin/reviews/jobs/${id}/retry`, {method:'POST'});
      await refreshAll(); renderApp();
    };
  });
}

function renderApp(){
  if (!state.auth?.token) return renderLogin();
  if (!canAccess(state.page, state.auth.role)) state.page = 'overview';
  let content = '';
  if (state.page === 'overview') content = overviewPage();
  if (state.page === 'segments') content = segmentsPage();
  if (state.page === 'campaigns') content = campaignsPage();
  if (state.page === 'paused') content = pausedPage();
  if (state.page === 'monitoring') content = monitoringPage();
  if (state.page === 'settings') content = settingsPage();
  document.getElementById('app').innerHTML = shell(content);
  attachHandlers();
}

(async function init(){
  if (!state.auth?.token) return renderLogin();
  try {
    await refreshAll();
    renderApp();
  } catch (e) {
    clearAuth(); state.auth = null; renderLogin(e.message);
  }
})();
