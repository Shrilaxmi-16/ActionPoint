import re

ui_script = """<script>
let extractedData = null;

function switchTab(tabName) {
  document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.screen').forEach(scr => scr.classList.remove('active'));
  
  const targetTab = document.getElementById(`tab-${tabName}`);
  if (targetTab) targetTab.classList.add('active');
  const scr = document.getElementById(`screen-${tabName}`);
  if (scr) scr.classList.add('active');

  if (tabName === 'kanban') loadTasksFromDB();
  if (tabName === 'dashboard') loadMetrics();
}

function loadSampleTranscript() {
  document.getElementById('transcript-input').value = `[09:00] Sarah (Product Lead): Good morning everyone. Let's do a quick sync on Project Horizon launch readiness.
[09:01] Dave: Backend migration for Firestore is 90% done, but legacy auth latency spikes under 500 RPS.
[09:03] Dave: We decided to migrate auth to Cloud Identity instead of patching legacy service.
[09:04] Sarah: Locked in. Dave, draft the Cloud Identity migration RFC by Thursday 5 PM.
[09:06] Elena: Kanban mockups done. Open question: should mobile support drag-and-drop or view-only?
[09:07] Sarah: Elena, check Mixpanel mobile analytics by Friday.
[09:09] Marcus: Cloud Run is stable. Marcus will configure Cloud Monitoring alert policies by Monday EOD.`;
}

async function extractFromInput() {
  const text = document.getElementById('transcript-input').value.trim();
  if (!text) { alert('Please enter a transcript.'); return; }
  
  const btn = document.getElementById('btn-extract');
  if (btn) { btn.disabled = true; btn.textContent = 'Extracting...'; }

  appendMessage('user', 'Extract action items from meeting transcript');
  appendMessage('assistant', 'Extracting structured summary, decisions, and action items with Gemini...');
  
  try {
    const res = await fetch('/api/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transcript: text, meeting_title: 'Project Horizon Launch Readiness' })
    });
    const result = await res.json();
    if (result.status === 'success') {
      extractedData = result.data;
      populateReviewScreen(extractedData);
      switchTab('review');
      appendMessage('assistant', `Extracted **${extractedData.action_items.length} action items**, **${extractedData.decisions.length} decisions**, and **${extractedData.open_questions.length} open questions**. Switched to **Review Screen**!`);
    } else {
      appendMessage('assistant', 'Extraction failed: ' + result.message);
    }
  } catch (err) {
    appendMessage('assistant', 'Network error during extraction: ' + err.message);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Extract Action Items'; }
  }
}

function populateReviewScreen(data) {
  const overview = document.getElementById('review-overview');
  overview.innerHTML = `
    <strong>Title:</strong> ${data.title}<br>
    <strong>Attendees:</strong> ${(data.attendees || []).join(', ')}<br><br>
    <strong>Summary:</strong> ${data.summary}
  `;

  const decisionsEl = document.getElementById('review-decisions');
  if (data.decisions && data.decisions.length > 0) {
    decisionsEl.innerHTML = data.decisions.map(d => `
      <div style="margin-bottom:0.5rem; padding:0.4rem; background:#f1f5f9; border-radius:6px;">
        <strong>${d.decision}</strong><br>
        <span style="font-size:0.8rem; color:#64748b;">Rationale: ${d.context}</span>
      </div>
    `).join('');
  } else {
    decisionsEl.textContent = 'None';
  }

  const itemsEl = document.getElementById('review-action-items');
  if (data.action_items && data.action_items.length > 0) {
    itemsEl.innerHTML = data.action_items.map(it => `
      <div style="background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid #2563eb; border-radius:6px; padding:0.8rem 1rem; margin-bottom:0.6rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong>${it.title}</strong>
          <span class="tag ${(it.priority||'medium').toLowerCase()}">${(it.priority||'medium').toUpperCase()}</span>
        </div>
        <div style="font-size:0.82rem; color:#64748b; margin-top:0.3rem;">
          Owner: <strong>${it.owner}</strong> | Due: <strong>${it.due_date}</strong> | Status: <strong>${it.status}</strong>
        </div>
      </div>
    `).join('');
  } else {
    itemsEl.textContent = 'None';
  }
}

async function confirmAndSaveAll() {
  if (!extractedData) {
    alert('Please extract a transcript first.');
    return;
  }
  const btn = document.getElementById('btn-confirm');
  if (btn) { btn.disabled = true; btn.textContent = 'Saving...'; }

  try {
    const res = await fetch('/api/confirm_save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ meeting_analysis: extractedData, project: 'Project Horizon' })
    });
    const result = await res.json();
    if (result.status === 'success') {
      appendMessage('assistant', `Confirmed and saved to database! Meeting ID: **${result.meeting_id}**.`);
      switchTab('kanban');
      loadTasksFromDB();
      loadMetrics();
    } else {
      appendMessage('assistant', 'Error saving meeting: ' + result.message);
    }
  } catch (err) {
    appendMessage('assistant', 'Failed to connect: ' + err.message);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Confirm & Save to Board'; }
  }
}

async function loadTasksFromDB() {
  try {
    const res = await fetch('/api/tasks');
    const tasks = await res.json();

    const pendingCol = document.getElementById('col-pending');
    const progressCol = document.getElementById('col-progress');
    const blockedCol = document.getElementById('col-blocked');
    const doneCol = document.getElementById('col-done');

    pendingCol.innerHTML = '';
    progressCol.innerHTML = '';
    blockedCol.innerHTML = '';
    doneCol.innerHTML = '';

    let pending = 0, progress = 0, blocked = 0, done = 0;

    tasks.forEach(t => {
      const card = document.createElement('div');
      card.className = 'kanban-card';
      card.innerHTML = `
        <span class="tag ${(t.priority||'medium').toLowerCase()}">${(t.priority || 'medium').toUpperCase()}</span>
        <strong>${t.title}</strong>
        <div style="color:var(--text-muted); font-size:0.8rem;">Owner: ${t.owner} | Due: ${t.due_date}</div>
      `;
      const st = (t.status || 'pending').toLowerCase();
      if (st === 'pending') { pendingCol.appendChild(card); pending++; }
      else if (st === 'in_progress') { progressCol.appendChild(card); progress++; }
      else if (st === 'blocked') { blockedCol.appendChild(card); blocked++; }
      else if (st === 'done') { doneCol.appendChild(card); done++; }
      else { pendingCol.appendChild(card); pending++; }
    });

    document.getElementById('count-pending').textContent = pending;
    document.getElementById('count-progress').textContent = progress;
    document.getElementById('count-blocked').textContent = blocked;
    document.getElementById('count-done').textContent = done;
  } catch (err) {
    console.error('Failed to load tasks:', err);
  }
}

async function loadMetrics() {
  try {
    const res = await fetch('/api/metrics');
    const data = await res.json();
    document.getElementById('metric-meetings').textContent = data.meetings;
    document.getElementById('metric-active-items').textContent = data.active_items;
    document.getElementById('metric-decisions').textContent = data.decisions;
    document.getElementById('metric-questions').textContent = data.open_questions;
  } catch (err) {
    console.error('Failed to load metrics:', err);
  }
}

function appendMessage(role, text) {
  const log = document.getElementById('log');
  const msg = document.createElement('div');
  msg.className = `msg ${role}`;
  const b = document.createElement('div');
  b.className = 'bubble';

  if (role === 'assistant') {
    b.innerHTML = marked.parse(text);
  } else {
    b.textContent = text;
  }

  msg.appendChild(b);
  log.appendChild(msg);
  log.scrollTop = log.scrollHeight;
}

async function sendChat(message) {
  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    const data = await res.json();
    if (data.parts) {
      data.parts.forEach(p => {
        if (p.text) appendMessage('assistant', p.text);
      });
    }
  } catch (err) {
    appendMessage('assistant', 'Error communicating with agent: ' + err.message);
  }
}

document.getElementById('chat-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const input = document.getElementById('chat-input');
  const val = input.value.trim();
  if (!val) return;
  appendMessage('user', val);
  input.value = '';
  sendChat(val);
});

function sendQuickPrompt(prompt) {
  appendMessage('user', prompt);
  sendChat(prompt);
}

// Initial load
loadTasksFromDB();
loadMetrics();
</script>
"""

with open("/config/Desktop/BuildWithGemini/frontend/static/index.html", "r") as f:
    content = f.read()

# Replace <script>...</script> at the bottom
new_content = re.sub(r"<script>.*?</script>", ui_script, content, flags=re.DOTALL)

with open("/config/Desktop/BuildWithGemini/frontend/static/index.html", "w") as f:
    f.write(new_content)

print("Updated index.html successfully!")
