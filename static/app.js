let token = localStorage.getItem('fly_token') || '';
const $ = s => document.querySelector(s);
const money = c => '$' + (c/100).toFixed(2);
async function api(path, opts={}) {
  const r = await fetch(path, {headers: {'Content-Type':'application/json','X-Admin-Token': token, ...(opts.headers||{})}, ...opts});
  if (!r.ok) { const t = await r.text(); throw new Error(r.status + ' ' + t.slice(0,300)); }
  return r.json();
}
document.querySelectorAll('#tabs button').forEach(b => b.onclick = () => {
  document.querySelectorAll('#tabs button').forEach(x=>x.classList.remove('on')); b.classList.add('on');
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
  document.getElementById('tab-'+b.dataset.tab).classList.add('on');
  load(b.dataset.tab);
});
async function load(tab='dash') {
  try {
    if (tab==='dash') {
      const d = await api('/api/dashboard');
      $('#mode').textContent = 'Mode: ' + (d.llm.mode==='template' ? 'Template mode (no LLM key — deterministic, $0)' : 'LLM: '+d.llm.mode) + ' · Gumroad: ' + (d.gumroad_connected?'connected':'NOT CONNECTED');
      $('#apprCount').textContent = d.pending_approvals ? '('+d.pending_approvals+' pending)' : '';
      const f = d.finance;
      $('#cards').innerHTML = [
        ['Total revenue', money(f.gross_cents)], ['Net profit', money(f.net_cents)],
        ['Products', d.products.n + ' ('+d.products.listed+' listed)'], ['Orders (real)', f.orders],
        ['Expenses', money(f.expenses_cents)], ['Reinvestment balance', money(f.reinvestment_balance_cents)],
        ['LLM calls today', d.llm.calls_today + ' / ' + d.llm.daily_cap],
        ['Status', f.orders===0 ? 'Pre-launch: $0 revenue, 0 orders' : 'Selling'],
      ].map(([k,v])=>`<div class="card"><span>${k}</span><b>${v}</b></div>`).join('');
      const a = await api('/api/activity');
      $('#activity').innerHTML = a.activity.slice(0,8).map(x=>`<div class="item">${x.action} — ${x.detail||''} <span class="note">${x.created_at||''}</span></div>`).join('') || '<p>No activity yet.</p>';
      $('#errors').innerHTML = a.errors.slice(0,5).map(x=>`<div class="item bad">${x.source}: ${x.message}</div>`).join('') || '<p class="ok">No errors logged.</p>';
    }
    if (tab==='agents') {
      const agents = await api('/api/agents');
      $('#agents').innerHTML = agents.map(a=>`<div class="item"><b>${a.name}</b> — ${a.description}<br>Status: <span class="${a.status==='disabled'?'bad':'ok'}">${a.status}</span> · Last run: ${a.last_run||'never'}<br>
        <button onclick="runAgent('${a.name}')">Run now</button>
        <button onclick="toggleAgent('${a.name}', ${a.status==='disabled'})">${a.status==='disabled'?'Enable':'Disable'}</button>
        ${a.errors.length?`<div class="bad">Errors: ${a.errors.join('; ')}</div>`:''}
        ${a.recent.map(r=>`<div class="note">${r.job}: ${r.status} — ${r.detail||''}</div>`).join('')}</div>`).join('');
      const s = await api('/api/schedules');
      $('#jobs').innerHTML = s.jobs.map(j=>`<div class="item">${j.name} (${j.weekday} ${j.time_local}) <button onclick="runJob('${j.id}')">Run now</button></div>`).join('');
    }
    if (tab==='products') {
      const ps = await api('/api/products');
      $('#products').innerHTML = ps.map(p=>`<div class="item"><b>${p.title}</b> — ${money(p.price_cents)} · ${p.category} · status: ${p.status} · QC: ${p.qc_status}<br>${p.description||''}<br>
        ${p.file_path?`<a href="/api/products/${p.slug}/download"><button>Download file</button></a>`:''}
        <button onclick="qc('${p.slug}')">Run QC</button>
        <button onclick="listProd('${p.slug}')">Request listing</button>
        <button class="warn" onclick="archiveProd('${p.slug}')">Archive</button></div>`).join('');
    }
    if (tab==='marketing') {
      const m = await api('/api/marketing');
      $('#drafts').innerHTML = m.drafts.map(d=>`<div class="item"><b>[${d.kind}] ${d.title}</b> — ${d.status}<br>${d.body}</div>`).join('') || '<p>No drafts yet.</p>';
      $('#queue').innerHTML = m.queue.map(q=>`<div class="item">${q.channel}: ${q.copy_text.slice(0,120)}… — ${q.status} · ${q.link||''}</div>`).join('') || '<p>Queue empty.</p>';
    }
    if (tab==='finance') {
      const f = await api('/api/finance'); const s = f.summary;
      $('#finSummary').innerHTML = `<div class="cards">
        ${[['Gross',money(s.gross_cents)],['Fees',money(s.fees_cents)],['Refunds',money(s.refunds_cents)],['Expenses',money(s.expenses_cents)],['Net',money(s.net_cents)],['Distributable',money(s.distributable_cents)],['Retained 50%',money(s.allocation_cents.retained_profit)],['Infra+AI 25%',money(s.allocation_cents.infrastructure_ai)],['Expansion 15%',money(s.allocation_cents.expansion)],['Reserve 10%',money(s.allocation_cents.reserve)]].map(([k,v])=>`<div class="card"><span>${k}</span><b>${v}</b></div>`).join('')}</div>
        <p class="note">${s.note}</p>`;
      $('#orders').innerHTML = f.orders.map(o=>`<div class="item">${o.product_slug} — ${money(o.amount_cents)} (fee ${money(o.fee_cents)}) ${o.is_test?'· TEST':''} · ${o.created_at||''}</div>`).join('') || '<p>No orders recorded. Real orders only — none yet.</p>';
    }
    if (tab==='approvals') {
      const aps = await api('/api/approvals');
      $('#approvals').innerHTML = aps.map(a=>`<div class="item"><b>[${a.kind}] ${a.summary}</b> — ${a.status}<br>
        ${a.status==='pending'?`<button onclick="decide(${a.id},'approved')">Approve</button><button class="warn" onclick="decide(${a.id},'rejected')">Reject</button>`:''}</div>`).join('') || '<p>No approval requests.</p>';
    }
    if (tab==='settings') {
      const s = await api('/api/settings');
      $('#settings').innerHTML = `<div class="item">LLM daily cap: ${s.llm_daily_cap} calls · Spending limit: ${money(s.spending_limit_cents)} (default $0 — any spend needs approval)<br>
        LLM mode: ${s.llm.mode} · Calls today: ${s.llm.calls_today}<br>
        Keys configured (values never shown): Gemini ${s.secrets.GEMINI_API_KEY?'✓':'✗'} · OpenAI ${s.secrets.OPENAI_API_KEY?'✓':'✗'} · Gumroad ${s.secrets.GUMROAD_ACCESS_TOKEN?'✓':'✗'} · Admin password ${s.secrets.ADMIN_PASSWORD?'✓':'✗'}</div>
        <form id="capForm"><input name="llm_daily_cap" type="number" placeholder="LLM daily cap" value="${s.llm_daily_cap}"><button>Save settings</button></form>`;
      $('#capForm').onsubmit = async e => { e.preventDefault(); const fd = new FormData(e.target);
        await api('/api/settings', {method:'POST', body: JSON.stringify({llm_daily_cap: +fd.get('llm_daily_cap')})}); alert('Saved'); };
    }
  } catch(e) { alert('Error: ' + e.message); }
}
async function runAgent(n){ await api('/api/agents/'+n+'/run',{method:'POST',body:'{}'}); alert('Agent run finished'); load('agents'); }
async function toggleAgent(n, en){ await api('/api/agents/'+n+'/toggle',{method:'POST',body:JSON.stringify({enabled:en})}); load('agents'); }
async function runJob(id){ const r = await api('/api/jobs/'+id+'/run',{method:'POST',body:'{}'}); alert('Job: '+r.status); load('agents'); }
async function qc(slug){ const r = await api('/api/products/'+slug+'/qc',{method:'POST',body:'{}'}); alert('QC '+(r.passed?'PASSED':'FAILED')); load('products'); }
async function listProd(slug){ try{ const r = await api('/api/products/'+slug+'/approve-list',{method:'POST',body:'{}'}); alert(r.status==='approval_required'?'Approval requested — approve it in the Approvals tab.':'Listed!'); }catch(e){ alert(e.message);} load('products'); }
async function archiveProd(slug){ await api('/api/products/'+slug+'/archive',{method:'POST',body:'{}'}); load('products'); }
async function decide(id, d){ await api('/api/approvals/'+id+'/decide',{method:'POST',body:JSON.stringify({decision:d})}); load('approvals'); }
$('#genMarketing').onclick = async ()=>{ await api('/api/marketing/generate',{method:'POST',body:'{}'}); load('marketing'); };
$('#newProduct').onsubmit = async e=>{ e.preventDefault(); const fd=new FormData(e.target);
  await api('/api/products',{method:'POST',body:JSON.stringify({title:fd.get('title'),description:fd.get('description'),price_cents:+fd.get('price_cents')})}); e.target.reset(); load('products'); };
$('#testOrder').onsubmit = async e=>{ e.preventDefault(); const fd=new FormData(e.target);
  await api('/api/orders',{method:'POST',body:JSON.stringify({product_slug:fd.get('product_slug'),amount_cents:+fd.get('amount_cents'),fee_cents:+fd.get('fee_cents'),is_test:1})}); alert('TEST order recorded (excluded from real totals)'); e.target.reset(); load('finance'); };
$('#loginForm').onsubmit = async e=>{ e.preventDefault(); const fd=new FormData(e.target);
  try{ const r = await api('/api/login',{method:'POST',body:JSON.stringify({password:fd.get('password')})}); token=r.token; localStorage.setItem('fly_token',token); alert('Logged in'); }catch(err){ alert('Login failed: '+err.message); } };
load('dash');
