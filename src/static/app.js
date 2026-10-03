const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));

const state = {
  projects: [],
  selectedProjectId: null,
  projectMatches: null,
  selectedMatchId: null,
  matchLimit: 10,
  matchOffset: 0,
  matchStatus: '',
  reviewAudits: {},
  outreachDrafts: {},
  outreachAudits: {},
  outreachQueues: {},
  queue: [],
  demoLimits: null,
  message: null,
  workspaceRequestId: 0,
  projectsLoaded: false,
  queueLoaded: false,
};

// Data integrity: a field the API did not send renders as an em dash. The
// workspace never substitutes a guessed value, metric, date or score.
const MISSING = '\u2014';
const valueOrDash = (value) => {
  if (value === null || value === undefined) return MISSING;
  const text = String(value).trim();
  return text ? text : MISSING;
};

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

// A pure reformat of a value the server sent. Anything that is not a
// recognisable date is passed through untouched rather than guessed at.
function formatDate(value) {
  const raw = value === null || value === undefined ? '' : String(value).trim();
  if (!raw) return MISSING;
  const parts = /^(\d{4})-(\d{2})-(\d{2})/.exec(raw);
  if (!parts) return raw;
  const month = MONTHS[Number(parts[2]) - 1];
  if (!month) return raw;
  return month + ' ' + Number(parts[3]) + ', ' + parts[1];
}

function formatStamp(value) {
  const raw = value === null || value === undefined ? '' : String(value).trim();
  if (!raw) return MISSING;
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  const hours = parsed.getHours();
  const hour12 = hours % 12 === 0 ? 12 : hours % 12;
  const suffix = hours >= 12 ? 'PM' : 'AM';
  return formatDate(raw) + ', ' + hour12 + ':' + String(parsed.getMinutes()).padStart(2, '0') + ' ' + suffix;
}

// Derived arithmetic on a real deadline only. No deadline means no text.
function deadlineMeta(value) {
  const raw = value === null || value === undefined ? '' : String(value).trim();
  if (!raw) return { text: '', tone: '' };
  const text = formatDate(raw);
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(raw);
  const target = Date.parse(dateOnly ? raw + 'T23:59:59Z' : raw);
  if (!Number.isFinite(target)) return { text: text, tone: '' };
  const days = Math.ceil((target - Date.now()) / 86400000);
  if (days < 0) return { text: text + ' (' + Math.abs(days) + 'd past)', tone: 'late' };
  if (days <= 7) return { text: text + ' (' + days + 'd left)', tone: 'soon' };
  return { text: text, tone: '' };
}

const CHIP_TONES = {
  ACTIVE: 'success', INACTIVE: 'subtle', APPROVED: 'success', REJECTED: 'danger',
  SKIPPED: 'warning', UNREVIEWED: 'subtle', DRAFT: 'warning', QUEUED: 'accent',
};

function statusChip(value) {
  const tone = CHIP_TONES[String(value || '').toUpperCase()] || 'subtle';
  return `<span class="badge badge-${tone}">${escapeHtml(valueOrDash(value))}</span>`;
}

function statusBadge(status) {
  const map = { APPROVED: 'success', REJECTED: 'danger', SKIPPED: 'warning', UNREVIEWED: 'subtle' };
  return map[status] || 'subtle';
}

function setSyncMode(mode, label) {
  const chip = document.getElementById('syncMode');
  if (!chip) return;
  const tone = { live: 'accent', fixture: 'subtle', running: 'accent', success: 'success', error: 'danger', idle: 'subtle' }[mode] || 'subtle';
  chip.textContent = label;
  chip.dataset.mode = mode;
  chip.className = 'mode mode-' + tone;
}

function renderSyncStats(stats) {
  const row = document.getElementById('syncStats');
  if (!row) return;
  if (!stats) { row.innerHTML = ''; return; }
  row.innerHTML = [
    ['Fetched', stats.fetched], ['Accepted', stats.accepted],
    ['Qualified', stats.qualified], ['Matches', stats.matches],
  ].map(([label, value]) => `<div class="count"><dt>${label}</dt><dd>${escapeHtml(valueOrDash(value))}</dd></div>`).join('');
}

function setKpi(valueId, noteId, value, note) {
  const el = document.getElementById(valueId);
  if (el) el.textContent = value;
  const noteEl = document.getElementById(noteId);
  if (noteEl && note !== undefined && note !== null) noteEl.textContent = note;
}

function renderKpis() {
  // Counts appear only once the matching request succeeded, so an unloaded
  // workspace never claims a number it does not have.
  setKpi(
    'kpiQualified', 'kpiQualifiedNote',
    state.projectsLoaded ? String(state.projects.length) : MISSING,
    state.projectsLoaded ? 'qualified and loaded' : 'not loaded yet',
  );
  const summary = state.projectMatches && state.projectMatches.summary;
  if (summary) {
    setKpi('kpiUnreviewed', 'kpiUnreviewedNote', String(summary.unreviewed ?? 0), 'this opportunity');
    setKpi('kpiApproved', 'kpiApprovedNote', String(summary.approved ?? 0), 'this opportunity');
  } else {
    setKpi('kpiUnreviewed', 'kpiUnreviewedNote', MISSING, 'no opportunity selected');
    setKpi('kpiApproved', 'kpiApprovedNote', MISSING, 'no opportunity selected');
  }
  setKpi('kpiQueue', null, state.queueLoaded ? String(state.queue.length) : MISSING, null);
}
function renderProjects() {
  const list = document.getElementById('projectList');
  if (!list) return;
  list.innerHTML = '';
  const search = (document.getElementById('projectSearch')?.value || '').trim().toLowerCase();
  const stateFilter = document.getElementById('stateFilter')?.value || '';
  const visibleProjects = state.projects.filter(project => {
    const haystack = [project.name, project.city, project.state, project.description].filter(Boolean).join(' ').toLowerCase();
    return (!search || haystack.includes(search)) && (!stateFilter || project.state === stateFilter);
  });

  const counter = document.getElementById('opportunityCount');
  if (counter) {
    counter.textContent = state.projectsLoaded
      ? (visibleProjects.length === state.projects.length
          ? String(state.projects.length)
          : visibleProjects.length + ' / ' + state.projects.length)
      : MISSING;
  }

  if (!visibleProjects.length) {
    // An unqualified notice is never shown here: this list is built from
    // the qualified opportunities the server returned.
    const filtered = search || stateFilter;
    list.innerHTML = '<li class="opp-empty">' + (filtered
      ? '<p class="empty-t">No matches for this filter</p><p class="empty-d">Clear the search or state filter to see all qualified opportunities.</p>'
      : '<p class="empty-t">No qualified opportunities yet</p><p class="empty-d">No opportunities currently meet the configured qualification rules. Run a sync to populate the queue.</p>') + '</li>';
    return;
  }

  visibleProjects.forEach((project, index) => {
    const item = document.createElement('li');
    const isActive = project.id === state.selectedProjectId;
    item.className = 'opp' + (isActive ? ' is-active' : '');
    item.setAttribute('role', 'option');
    item.setAttribute('aria-selected', isActive ? 'true' : 'false');
    item.tabIndex = isActive || (!state.selectedProjectId && index === 0) ? 0 : -1;
    item.dataset.projectId = project.id;

    const location = [project.city, project.state].filter(Boolean).join(', ');
    const due = deadlineMeta(project.response_deadline);
    if (due.tone) item.classList.add('is-' + due.tone);
    const matchCount = project.match_count;

    item.innerHTML =
      '<p class="opp-title">' + escapeHtml(valueOrDash(project.name)) + '</p>' +
      '<p class="opp-line"><span class="opp-loc">' + escapeHtml(location || MISSING) + '</span>' +
      (due.text ? '<span class="opp-due' + (due.tone ? ' is-' + due.tone : '') + '">' + escapeHtml(due.text) + '</span>' : '') + '</p>' +
      '<p class="opp-line opp-state">' + statusChip(project.status) +
      (matchCount === null || matchCount === undefined ? '' : '<span class="opp-count">' + escapeHtml(String(matchCount)) + ' match' + (Number(matchCount) === 1 ? '' : 'es') + '</span>') +
      '</p>';
    item.onclick = () => selectProject(project.id);
    list.appendChild(item);
  });
}

function populateStateFilter() {
  const select = document.getElementById('stateFilter');
  if (!select) return;
  const current = select.value;
  const states = [...new Set(state.projects.map(project => project.state).filter(Boolean))].sort();
  select.innerHTML = '<option value="">All states</option>' + states.map(value => '<option value="' + escapeHtml(value) + '">' + escapeHtml(value) + '</option>').join('');
  select.value = states.includes(current) ? current : '';
}

async function readJson(response) {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text.slice(0, 300) || 'Unexpected server response' };
  }
}

// Renders only what the API actually sent; an empty factor list is reported
// as such rather than padded with invented explanations.
function renderFactorList(factors) {
  if (!Array.isArray(factors) || !factors.length) {
    return '<p class="muted">None reported</p>';
  }
  return '<ul class="facts-list">' + factors.map(factor => '<li>' + escapeHtml(factor) + '</li>').join('') + '</ul>';
}

function setDemoStatus(text, type) {
  const el = document.getElementById('demoStatus');
  if (!el) return;
  el.className = 'status' + (type === 'error' ? ' is-error' : type === 'success' ? ' is-success' : type === 'running' ? ' is-running' : '');
  el.textContent = 'Sync status: ' + text;
}

// Quota countdown state. Only a real `retry_after` supplied by SAM.gov ever
// reaches this code; when it is absent the plain quota message is shown and
// no reset time is invented.
let quotaCountdownTimer = null;

function clearQuotaCountdown() {
  if (quotaCountdownTimer !== null) {
    clearInterval(quotaCountdownTimer);
    quotaCountdownTimer = null;
  }
}

function formatCountdown(totalSeconds) {
  const seconds = Math.max(Math.floor(totalSeconds), 0);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours) return hours + 'h ' + minutes + 'm';
  return minutes + 'm ' + (seconds % 60) + 's';
}

function startQuotaCountdown(message, retryAfterIso) {
  // Always tear down first so repeated sync attempts cannot stack timers.
  clearQuotaCountdown();
  const target = Date.parse(retryAfterIso);
  if (!Number.isFinite(target)) {
    setDemoStatus(message, 'error');
    return;
  }
  const tick = () => {
    const remaining = Math.ceil((target - Date.now()) / 1000);
    if (remaining <= 0) {
      clearQuotaCountdown();
      setDemoStatus(message, 'error');
      return;
    }
    setDemoStatus(message + ' \u2022 Quota reset signal: ' + formatCountdown(remaining), 'error');
  };
  tick();
  quotaCountdownTimer = setInterval(tick, 1000);
}
// Score components appear only when the matcher reported the feature as
// known. A component the server did not compute is omitted, never shown as
// a zero, so the row never implies a comparison that was not made.
const COMPONENT_LABELS = { trade_overlap: 'Trade', geography: 'Geography', bid_timing: 'Bid timing' };

function renderComponentLine(match) {
  const components = match && match.components;
  if (!components || typeof components !== 'object') return '';
  const parts = Object.keys(COMPONENT_LABELS)
    .filter(key => components[key] && components[key].known)
    .map(key => escapeHtml(COMPONENT_LABELS[key]) + ' ' + escapeHtml(valueOrDash(components[key].score)) + '/' + escapeHtml(valueOrDash(components[key].max)));
  return parts.length ? parts.join(' \u00b7 ') : '';
}

function factorSentence(factors, limit) {
  const list = Array.isArray(factors) ? factors : [];
  if (!list.length) return '';
  const shown = list.slice(0, limit).map(factor => escapeHtml(factor));
  const extra = list.length - limit;
  if (extra > 0) shown.push('+' + extra + ' more');
  return shown.join(' \u00b7 ');
}

function renderMatch(match, isSelected) {
  const raw = match.match_score;
  const score = typeof raw === 'number' && Number.isFinite(raw) ? raw : null;
  const id = escapeHtml(match.id);
  const positives = Array.isArray(match.positive_factors) ? match.positive_factors : [];
  const negatives = Array.isArray(match.negative_factors) ? match.negative_factors : [];
  const comps = renderComponentLine(match);

  const meta = ['Rank ' + escapeHtml(valueOrDash(match.ranking)),
    escapeHtml(valueOrDash(match.confidence)) + ' confidence'];
  if (comps) meta.push(comps);
  const why = positives.length ? factorSentence(positives, 2) : 'No positive factors reported';
  const against = negatives.length ? factorSentence(negatives, 1) : '';

  return '<article class="match' + (isSelected ? ' is-selected' : '') + '" data-id="' + id + '">' +
    '<div class="match-main">' +
      '<p class="match-name">' + escapeHtml(valueOrDash(match.contractor_name)) + '</p>' +
      '<p class="match-meta">' + meta.join(' \u00b7 ') + '</p>' +
      '<p class="match-contact' + (match.contractor_email ? ' has' : ' hasnt') + '">' +
        (match.contractor_email ? 'Contact on file' : 'No contact email on file') + '</p>' +
    '</div>' +
    '<div class="score"><b>' + (score === null ? MISSING : escapeHtml(score.toFixed(2))) + '</b><span>Score</span></div>' +
    '<div class="match-side">' +
      '<p class="match-why">' + why + '</p>' +
      (against ? '<p class="match-why is-neg">' + against + '</p>' : '') +
      '<div class="match-acts">' +
        '<span class="badge badge-' + statusBadge(match.review_status) + '">' + escapeHtml(valueOrDash(match.review_status)) + '</span>' +
        '<button class="btn btn-sm btn-quiet" onclick="openMatch(' + "'" + id + "')" + '">Open</button>' +
        '<button class="btn btn-sm btn-primary" onclick="reviewMatch(' + "'" + id + "', 'APPROVED')" + '">Approve</button>' +
        '<button class="btn btn-sm btn-danger" onclick="reviewMatch(' + "'" + id + "', 'REJECTED')" + '">Reject</button>' +
        '<button class="btn btn-sm btn-quiet" onclick="reviewMatch(' + "'" + id + "', 'SKIPPED')" + '">Skip</button>' +
      '</div>' +
    '</div>' +
  '</article>';
}

// A step is only ever marked complete because a real status said so.
function renderSteps(match, draft, queued) {
  const hasDraft = Boolean(draft && !draft.error);
  const flags = [
    match.review_status === 'APPROVED',
    hasDraft,
    hasDraft && draft.status === 'APPROVED',
    Boolean(queued),
  ];
  const labels = ['Match approved', 'Draft generated', 'Draft approved', 'Queued'];
  let done = 0;
  while (done < flags.length && flags[done]) done += 1;
  const items = labels.map((label, index) => {
    const cls = index < done ? 'is-done' : index === done ? 'is-now' : 'is-todo';
    return '<li class="step ' + cls + '"><span class="step-n">' + (index + 1) + '</span>' + escapeHtml(label) + '</li>' +
      (index < labels.length - 1 ? '<li class="step-arrow" aria-hidden="true">&rarr;</li>' : '');
  }).join('');
  return '<ol class="steps">' + items + '</ol>';
}
function renderWorkspace() {
  const target = document.getElementById('workspace');
  if (!target) return;
  if (!state.selectedProjectId) {
    target.innerHTML = '<div class="ws-empty"><p class="empty-t">No opportunity selected</p><p class="empty-d">Select an opportunity from the queue to review its contractor matches.</p></div>';
    return;
  }
  if (!state.projectMatches) {
    target.innerHTML = '<div class="ws-empty"><p class="empty-t"><span class="spin"></span>Loading match workspace</p><p class="empty-d">Fetching contractor matches for the selected opportunity.</p></div>';
    return;
  }

  const project = state.projectMatches.project;
  const matches = state.projectMatches.matches || [];
  const summary = state.projectMatches.summary || { total: 0, unreviewed: 0, approved: 0, rejected: 0, skipped: 0 };
  const pageTotal = state.projectMatches.total ?? 0;
  const pageStart = pageTotal ? state.projectMatches.offset + 1 : 0;
  const pageEnd = Math.min(state.projectMatches.offset + matches.length, pageTotal);

  const selectedMatch = matches.find(m => m.id === state.selectedMatchId) || null;
  const location = [project.city, project.state].filter(Boolean).join(', ') || MISSING;
  const due = deadlineMeta(project.response_deadline);
  const draftEntry = selectedMatch ? state.outreachDrafts[selectedMatch.id] : null;
  const queued = draftEntry && !draftEntry.error ? state.outreachQueues[draftEntry.id] : null;

  const matchList = matches.length
    ? matches.map(match => renderMatch(match, match.id === state.selectedMatchId)).join('')
    : '<div class="ws-empty"><p class="empty-t">No contractor matches yet</p><p class="empty-d">No matches have been generated for this opportunity.</p>' +
      '<button class="btn btn-primary btn-sm" onclick="generateMatches(' + "'" + escapeHtml(project.id) + "')" + '">Generate contractor matches</button></div>';

  const detail = selectedMatch ? [
    '<div class="sub">',
      '<p class="label">Match detail \u00b7 ' + escapeHtml(valueOrDash(selectedMatch.contractor_name)) + '</p>',
      '<div class="kv">',
        kvPair('Score', selectedMatch.match_score != null ? escapeHtml(selectedMatch.match_score.toFixed(2)) : MISSING),
        kvPair('Confidence', escapeHtml(valueOrDash(selectedMatch.confidence))),
        kvPair('Ranking', escapeHtml(valueOrDash(selectedMatch.ranking))),
        kvPair('Matcher', '<span class="mono">' + escapeHtml(valueOrDash(selectedMatch.matcher_version)) + '</span>'),
        kvPair('Primary email', '<span class="mono">' + (selectedMatch.contractor_email ? escapeHtml(selectedMatch.contractor_email) : MISSING) + '</span>'),
      '</div>',
    '</div>',
    '<div class="sub">',
      '<div class="fg"><p class="label">Positive factors</p>' + renderFactorList(selectedMatch.positive_factors) + '</div>',
      '<div class="fg"><p class="label">Negative factors</p>' + renderFactorList(selectedMatch.negative_factors) + '</div>',
      '<div class="fg"><p class="label">Unknown factors</p>' + renderFactorList(selectedMatch.unknown_factors) + '</div>',
    '</div>',
    '<div class="sub">',
      '<p class="label">Review History</p>',
      '<div id="reviewHistory">' + renderReviewHistory(selectedMatch.id) + '</div>',
    '</div>',
  ].join('') : '';

  // Only built when a match is actually selected; renderSteps reads review_status.
  const outreach = !selectedMatch ? '' : [
    renderSteps(selectedMatch, draftEntry, queued),
    !selectedMatch.contractor_email
      ? '<p class="muted">No primary email is available. Outreach generation will remain blocked.</p>'
      : selectedMatch.review_status !== 'APPROVED'
        ? '<p class="muted">Approve this match to generate an outreach draft.</p>'
        : draftEntry?.error
          ? '<p class="err">' + escapeHtml(draftEntry.error) + '</p>'
          : draftEntry
            ? renderOutreachDraft(selectedMatch.id)
            : '<button class="btn btn-secondary btn-sm" onclick="generateOutreachDraft(' + "'" + escapeHtml(selectedMatch.id) + "')" + '">Generate Outreach Draft</button>',
    '<div class="sub"><p class="label">Outreach draft history</p><div id="outreachHistory">' + renderOutreachHistory(selectedMatch.id) + '</div></div>',
  ].join('');

  target.innerHTML =
    '<header class="ws-head">' +
      '<div class="ws-head-t">' +
        '<p class="label">Opportunity</p>' +
        '<h1 class="ws-title">' + escapeHtml(valueOrDash(project.name)) + '</h1>' +
        '<p class="ws-meta"><span>' + escapeHtml(location) + '</span>' +
          (due.text ? '<span class="ws-sep"></span><span class="' + (due.tone ? 'is-' + due.tone : '') + '">Due ' + escapeHtml(due.text) + '</span>' : '') +
          '<span class="ws-sep"></span>' + statusChip(project.status) + '</p>' +
      '</div>' +
      '<div class="ws-head-a">' +
        (project.construction_relevance ? '<span class="badge badge-subtle">' + escapeHtml(valueOrDash(project.construction_relevance)) + '</span>' : '') +
        '<button class="btn btn-secondary btn-sm" onclick="refreshProjectMatches()">Refresh</button>' +
      '</div>' +
    '</header>' +

    '<div class="figs">' +
      figure('Unreviewed', 'kpiUnreviewed', 'kpiUnreviewedNote') +
      figure('Approved', 'kpiApproved', 'kpiApprovedNote') +
      figure('Queued', 'kpiQueue', null, 'Not sent') +
    '</div>' +

    (state.message ? '<p class="note note-' + escapeHtml(state.message.type) + '">' + escapeHtml(state.message.text) + '</p>' : '') +

    '<section class="sec">' +
      '<div class="sec-head"><h2 class="label">Contractor matches</h2>' +
        '<p class="sec-sub">Contractors ranked using trade, geography and bid timing.</p></div>' +
      '<div class="bar">' +
        '<select class="field field-sm" id="matchStatusFilter" onchange="changeMatchStatus(this.value)" aria-label="Filter matches by review status">' +
          '<option value="">All statuses</option>' +
          '<option value="UNREVIEWED" ' + (state.matchStatus === 'UNREVIEWED' ? 'selected' : '') + '>Unreviewed</option>' +
          '<option value="APPROVED" ' + (state.matchStatus === 'APPROVED' ? 'selected' : '') + '>Approved</option>' +
          '<option value="REJECTED" ' + (state.matchStatus === 'REJECTED' ? 'selected' : '') + '>Rejected</option>' +
          '<option value="SKIPPED" ' + (state.matchStatus === 'SKIPPED' ? 'selected' : '') + '>Skipped</option>' +
        '</select>' +
        '<span class="bar-sum">' + escapeHtml(String(summary.total ?? 0)) + ' total \u00b7 ' +
          escapeHtml(String(summary.unreviewed ?? 0)) + ' unreviewed \u00b7 ' +
          escapeHtml(String(summary.approved ?? 0)) + ' approved \u00b7 ' +
          escapeHtml(String(summary.rejected ?? 0)) + ' rejected \u00b7 ' +
          escapeHtml(String(summary.skipped ?? 0)) + ' skipped</span>' +
        '<span class="bar-end">' +
          '<button class="btn btn-secondary btn-sm" onclick="previousMatchPage()" ' + (state.projectMatches.offset <= 0 ? 'disabled' : '') + '>Previous</button>' +
          '<button class="btn btn-secondary btn-sm" onclick="nextMatchPage()" ' + (state.projectMatches.offset + matches.length >= pageTotal ? 'disabled' : '') + '>Next</button>' +
          '<span class="bar-range">' + pageStart + '\u2013' + pageEnd + ' of ' + pageTotal + '</span>' +
        '</span>' +
      '</div>' +
      '<div class="matches">' + matchList + '</div>' +
      detail +
    '</section>' +

    '<section class="sec">' +
      '<div class="sec-head"><h2 class="label">Outreach</h2>' +
        '<p class="sec-sub">Match approved, draft generated, draft approved, then queued. Nothing is ever sent.</p></div>' +
      (selectedMatch ? outreach :
        '<p class="muted">No outreach queued</p><p class="empty-d">Select a contractor match to review its outreach state.</p>') +
    '</section>';

  renderKpis();
}

function kvPair(label, valueHtml) {
  return '<div class="kv-p"><dt>' + escapeHtml(label) + '</dt><dd>' + valueHtml + '</dd></div>';
}

function figure(label, valueId, noteId, staticNote) {
  return '<div class="fig"><p class="label">' + escapeHtml(label) + '</p>' +
    '<p class="fig-n"><span id="' + valueId + '">\u2014</span>' +
    '<span class="fig-note"' + (noteId ? ' id="' + noteId + '"' : '') + '>' + escapeHtml(staticNote || '') + '</span></p></div>';
}
function renderOutreachDraft(matchId) {
  const draft = state.outreachDrafts[matchId];
  if (!draft) return '';
  const queued = state.outreachQueues[draft.id];
  const status = escapeHtml(draft.status);
  let actions = '';
  if (status === 'DRAFT') {
    actions = '<button class="btn btn-sm btn-primary" onclick="updateOutreachDraftStatus(' + "'" + draft.id + "', 'APPROVED', '" + matchId + "')" + '">Approve Draft</button>' +
      '<button class="btn btn-sm btn-danger" onclick="updateOutreachDraftStatus(' + "'" + draft.id + "', 'REJECTED', '" + matchId + "')" + '">Reject Draft</button>';
  } else if (status === 'APPROVED') {
    actions = '<button class="btn btn-sm btn-primary" onclick="queueOutreachDraft(' + "'" + draft.id + "', '" + matchId + "')" + '">Queue Draft (NOT SENT)</button>' +
      '<button class="btn btn-sm btn-danger" onclick="updateOutreachDraftStatus(' + "'" + draft.id + "', 'REJECTED', '" + matchId + "')" + '">Reject Draft</button>';
  } else {
    actions = '<button class="btn btn-sm btn-primary" onclick="updateOutreachDraftStatus(' + "'" + draft.id + "', 'APPROVED', '" + matchId + "')" + '">Approve Draft</button>';
  }
  const delivery = queued
    ? '<span class="badge badge-danger">NOT SENT</span>'
    : '<span class="badge badge-subtle">Not queued</span>';
  const queuedLine = queued
    ? '<p class="muted">Queued ' + escapeHtml(formatStamp(queued.queued_at)) + ' \u00b7 delivery ' + escapeHtml(queued.provenance?.delivery || 'not-sent') + '</p>'
    : '';
  return '<div class="draft">' +
    '<div class="draft-h"><span class="badge badge-' + (draft.status === 'APPROVED' ? 'accent' : draft.status === 'REJECTED' ? 'danger' : 'warning') + '">' + status + '</span>' + delivery +
      '<span class="mono draft-to">' + escapeHtml(valueOrDash(draft.recipient_email)) + '</span></div>' +
    '<p class="draft-sub">' + escapeHtml(valueOrDash(draft.subject)) + '</p>' +
    '<pre class="draft-body">' + escapeHtml(valueOrDash(draft.body)) + '</pre>' +
    (queuedLine ? '<div class="draft-f">' + queuedLine + '</div>' : '') +
    '<div class="draft-f"><div class="acts">' + actions + '</div></div>' +
  '</div>';
}

function renderOutreachHistory(matchId) {
  const draft = state.outreachDrafts[matchId];
  if (!draft) return '<p class="muted">No outreach draft yet.</p>';
  const audits = state.outreachAudits[draft.id];
  if (audits?.error) return '<p class="err">' + escapeHtml(audits.error) + '</p>';
  if (!audits) return '<p class="muted">Loading outreach history\u2026</p>';
  if (!audits.length) return '<p class="muted">No outreach approval history yet.</p>';
  return '<ul class="hist">' + audits.map(audit => '<li><p class="hist-m"><b>' + escapeHtml(audit.previous_status || 'DRAFT') + '</b> &rarr; <b>' + escapeHtml(audit.new_status) + '</b></p>' +
    '<p class="hist-t">' + escapeHtml(valueOrDash(audit.actor)) + ' \u00b7 ' + escapeHtml(formatStamp(audit.created_at)) + '</p></li>').join('') + '</ul>';
}

function renderReviewHistory(matchId) {
  const audits = state.reviewAudits[matchId];
  if (audits?.error) return '<p class="err">' + escapeHtml(audits.error) + '</p>';
  if (!audits) return '<p class="muted">Loading review history\u2026</p>';
  if (!audits.length) return '<p class="muted">No review history yet.</p>';
  return '<ul class="hist">' + audits.map(audit => '<li><p class="hist-m"><b>' + escapeHtml(audit.previous_status || 'UNREVIEWED') + '</b> &rarr; <b>' + escapeHtml(audit.new_status) + '</b></p>' +
    '<p class="hist-t">' + escapeHtml(valueOrDash(audit.actor)) + ' \u00b7 ' + escapeHtml(valueOrDash(audit.source)) + ' \u00b7 ' + escapeHtml(formatStamp(audit.created_at)) + '</p></li>').join('') + '</ul>';
}

async function loadProjects() {
  try {
    const response = await fetch('/opportunities?limit=100&active_only=true&construction_only=true');
    if (!response.ok) throw new Error('Unable to load projects');
    const projects = await readJson(response);
    state.projects = projects.map(project => ({ ...project, match_count: project.match_count ?? null }));
    state.projectsLoaded = true;
    populateStateFilter();
    if (!state.selectedProjectId && projects.length) {
      selectProject(projects[0].id);
    }
    renderProjects();
    renderKpis();
  } catch (error) {
    state.projectsLoaded = false;
    state.message = { type: 'error', text: error.message };
    renderProjects();
    renderKpis();
    renderWorkspace();
  }
}

async function loadDemoLimits() {
  try {
    const response = await fetch('/pipeline/demo/limits');
    if (!response.ok) return;
    state.demoLimits = await readJson(response);
    const el = document.getElementById('demoLimits');
    if (el && state.demoLimits) {
      el.textContent = 'server cap: ' + state.demoLimits.hard_max_records + ' records/page \u2022 live ' + (state.demoLimits.live_available ? 'available' : 'unavailable');
    }
    const liveBtn = document.getElementById('demoLiveBtn');
    if (liveBtn && state.demoLimits && !state.demoLimits.live_available) {
      liveBtn.disabled = true;
      liveBtn.title = 'Live demo requires INGESTION_MODE=samgov and a SAM.gov API key.';
    }
  } catch {
    /* limits are advisory for the UI */
  }
}

function setSyncButtonsDisabled(disabled) {
  for (const id of ['demoOfflineBtn', 'demoLiveBtn']) {
    const button = document.getElementById(id);
    if (button) button.disabled = disabled;
  }
}

async function runDemoSync(mode) {
  clearQuotaCountdown();
  setSyncMode('running', mode === 'live' ? 'Live \u00b7 running' : 'Fixture \u00b7 running');
  setDemoStatus('running ' + mode + ' sync...', 'running');
  setSyncButtonsDisabled(true);
  try {
    const response = await fetch('/pipeline/demo/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode })
    });
    const body = await readJson(response);
    if (!response.ok) {
      const failure = new Error(body.detail || 'Demo sync failed');
      // `retry_after` is present only when SAM.gov actually sent a usable
      // Retry-After. It is never synthesised by the server or here, so an
      // absent value keeps today's plain quota message.
      failure.status = response.status;
      failure.retryAfter = body.retry_after || null;
      throw failure;
    }
    const opps = body.opportunities || {};
    let summary = 'mode=' + body.mode + ' \u2022 fetched=' + (opps.records_fetched ?? 0) + ' \u2022 accepted=' + (opps.accepted ?? 0) + ' \u2022 qualified=' + (body.qualified_projects ?? 0) + ' \u2022 matches=' + (body.matches_generated ?? 0);
    if (body.empty) summary += ' \u2022 no opportunities returned';
    // The counts are rendered only from the numbers the server reported.
    renderSyncStats({
      fetched: opps.records_fetched,
      accepted: opps.accepted,
      qualified: body.qualified_projects,
      matches: body.matches_generated,
    });
    setSyncMode(body.mode === 'live' ? 'live' : 'fixture', body.mode === 'live' ? 'Live' : 'Fixture');
    setDemoStatus(summary, 'success');
    setSyncButtonsDisabled(false);
    state.message = { type: 'success', text: 'Demo sync complete: ' + summary };
    state.selectedProjectId = null;
    await loadProjects();
    // Only auto-open a project that actually qualified. `body.projects`
    // lists every project of the run, qualified or not, so taking the
    // first entry could surface a rejected notice (Special Notice,
    // non-US, non-construction) in the workspace as if it were a lead.
    // When nothing qualified, leave the selection empty so the workspace
    // falls back to its empty state.
    const firstId = body.projects?.find(project => project.qualified)?.id;
    if (firstId) await selectProject(firstId);
  } catch (error) {
    clearQuotaCountdown();
    setSyncButtonsDisabled(false);
    setDemoStatus(error.message, 'error');
    if (error.status === 429 && error.retryAfter) {
      // The countdown only ever runs on a real server-supplied instant.
      setSyncMode('error', 'Rate limited');
      startQuotaCountdown(error.message, error.retryAfter);
    } else {
      setSyncMode('error', 'Sync failed');
    }
    state.message = { type: 'error', text: error.message };
    renderWorkspace();
  }
}
async function loadOutreachQueue() {
  const target = document.getElementById('outreachQueue');
  if (!target) return;
  try {
    const response = await fetch('/outreach-queue');
    if (!response.ok) throw new Error('Unable to load outreach queue');
    const items = await readJson(response);
    state.queue = items;
    state.queueLoaded = true;
    renderKpis();
    if (!items.length) {
      target.innerHTML = '<div class="ws-empty"><p class="empty-t">Outreach queue is empty</p><p class="empty-d">Approve a match, generate a draft, approve the draft, then queue it. Nothing is ever sent.</p></div>';
      return;
    }
    // The queue payload carries subject/recipient/status/queued_at/body only.
    // Contractor and opportunity names are not part of this response, so
    // they are not shown rather than being guessed from the draft.
    target.innerHTML = items.map(item =>
      '<div class="qi">' +
        '<div class="qi-m">' +
          '<p class="qi-t">' + statusChip(item.status) + '<span class="qi-s">' + escapeHtml(valueOrDash(item.subject)) + '</span></p>' +
          '<p class="qi-meta"><span class="mono">' + escapeHtml(valueOrDash(item.recipient_email)) + '</span> \u00b7 Queued ' + escapeHtml(formatStamp(item.queued_at)) +
            ' \u00b7 Delivery ' + escapeHtml(valueOrDash(item.provenance?.delivery || 'not-sent')) + '</p>' +
          '<pre class="draft-body">' + escapeHtml(valueOrDash(item.body)) + '</pre>' +
        '</div>' +
        '<p class="qi-a"><span class="badge badge-danger">NOT SENT</span><span class="mono qi-id">' + escapeHtml(valueOrDash(item.draft_id)) + '</span></p>' +
      '</div>').join('');
  } catch (error) {
    state.queueLoaded = false;
    renderKpis();
    target.innerHTML = '<div class="ws-empty"><p class="empty-t">Outreach queue unavailable</p><p class="err">' + escapeHtml(error.message) + '</p></div>';
  }
}

async function queueOutreachDraft(draftId, matchId) {
  try {
    const response = await fetch('/outreach-drafts/' + draftId + '/queue', { method: 'POST' });
    const body = await readJson(response);
    if (!response.ok) throw new Error(body.detail || 'Unable to queue outreach draft');
    state.outreachQueues[draftId] = body;
    state.message = { type: 'success', text: 'Draft queued. Delivery state: NOT SENT.' };
    await loadOutreachQueue();
    renderWorkspace();
  } catch (error) {
    state.message = { type: 'error', text: error.message };
    renderWorkspace();
  }
}

async function refreshProjectMatches() {
  if (!state.selectedProjectId) return;
  const requestId = ++state.workspaceRequestId;
  const projectId = state.selectedProjectId;
  try {
    const params = new URLSearchParams({ limit: String(state.matchLimit), offset: String(state.matchOffset) });
    if (state.matchStatus) params.set('review_status', state.matchStatus);
    const response = await fetch(`/projects/${projectId}/matches?${params.toString()}`);
    const body = await readJson(response);
    if (requestId !== state.workspaceRequestId || projectId !== state.selectedProjectId) return;
    if (!response.ok) throw new Error(body.detail || 'Unable to load matches');
    state.projectMatches = body;
    const visibleMatchIds = new Set(state.projectMatches.matches.map(match => match.id));
    if (!visibleMatchIds.has(state.selectedMatchId)) {
      state.selectedMatchId = state.projectMatches.matches[0]?.id || null;
    }
    state.message = null;
    renderWorkspace();
  } catch (error) {
    state.message = { type: 'error', text: error.message };
    renderWorkspace();
  }
}

function changeMatchStatus(status) {
  state.matchStatus = status;
  state.matchOffset = 0;
  refreshProjectMatches();
}

function previousMatchPage() {
  state.matchOffset = Math.max(0, state.matchOffset - state.matchLimit);
  refreshProjectMatches();
}

function nextMatchPage() {
  const total = state.projectMatches?.total ?? 0;
  if (state.matchOffset + state.matchLimit < total) {
    state.matchOffset += state.matchLimit;
    refreshProjectMatches();
  }
}

async function generateMatches(projectId) {
  try {
    const response = await fetch('/projects/' + projectId + '/matches/generate', { method: 'POST' });
    const body = await readJson(response);
    if (!response.ok) throw new Error(body.detail || 'Unable to generate contractor matches');
    state.message = { type: 'success', text: 'Generated ' + (body.generated ?? 0) + ' contractor matches.' };
    await refreshProjectMatches();
  } catch (error) {
    state.message = { type: 'error', text: error.message };
    renderWorkspace();
  }
}

async function selectProject(projectId) {
  state.selectedProjectId = projectId;
  state.matchOffset = 0;
  state.matchStatus = '';
  state.message = null;
  renderProjects();
  await refreshProjectMatches();
}

async function loadOutreachDraft(matchId) {
  try {
    const response = await fetch('/matches/' + matchId + '/outreach-draft');
    if (response.status === 404) {
      state.outreachDrafts[matchId] = null;
    } else {
      const body = await readJson(response);
      if (!response.ok) throw new Error(body.detail || 'Unable to load outreach draft');
      state.outreachDrafts[matchId] = body;
      await loadOutreachDraftReviews(body.id);
    }
  } catch (error) {
    state.outreachDrafts[matchId] = { error: error.message };
  }
  renderWorkspace();
}

async function generateOutreachDraft(matchId) {
  try {
    const response = await fetch('/matches/' + matchId + '/outreach-draft', { method: 'POST' });
    const body = await readJson(response);
    if (!response.ok) throw new Error(body.detail || 'Unable to generate outreach draft');
    state.outreachDrafts[matchId] = body;
    state.message = { type: 'success', text: 'Outreach draft generated.' };
    await loadOutreachDraftReviews(body.id);
    renderWorkspace();
  } catch (error) {
    state.message = { type: 'error', text: error.message };
    renderWorkspace();
  }
}

async function updateOutreachDraftStatus(draftId, status, matchId) {
  try {
    const response = await fetch('/outreach-drafts/' + draftId + '/status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    const body = await readJson(response);
    if (!response.ok) throw new Error(body.detail || 'Unable to update outreach draft');
    state.outreachDrafts[matchId] = body;
    state.message = { type: 'success', text: 'Outreach draft marked ' + status + '.' };
    await loadOutreachDraftReviews(draftId);
    renderWorkspace();
  } catch (error) {
    state.message = { type: 'error', text: error.message };
    renderWorkspace();
  }
}

async function loadOutreachDraftReviews(draftId) {
  try {
    const response = await fetch('/outreach-drafts/' + draftId + '/reviews');
    const body = await readJson(response);
    if (!response.ok) throw new Error(body.detail || 'Unable to load outreach draft history');
    state.outreachAudits[draftId] = body;
  } catch (error) {
    state.outreachAudits[draftId] = { error: error.message };
  }
  renderWorkspace();
}

async function loadMatchReviews(matchId) {
  try {
    const response = await fetch(`/matches/${matchId}/reviews`);
    const body = await readJson(response);
    if (!response.ok) throw new Error(body.detail || 'Unable to load review history');
    state.reviewAudits[matchId] = body;
  } catch (error) {
    state.reviewAudits[matchId] = { error: error.message };
  }
  renderWorkspace();
}

function openMatch(matchId) {
  state.selectedMatchId = matchId;
  renderWorkspace();
  loadMatchReviews(matchId);
  loadOutreachDraft(matchId);
}

async function reviewMatch(matchId, status) {
  try {
    const response = await fetch(`/matches/${matchId}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    const body = await readJson(response);
    if (!response.ok) throw new Error(body.detail || 'Review action failed');
    await refreshProjectMatches();
    state.message = { type: 'success', text: `Match marked ${status}.` };
    renderWorkspace();
  } catch (error) {
    state.message = { type: 'error', text: error.message };
    renderWorkspace();
  }
}

// Keyboard support for the opportunity queue: roving tabindex plus arrow
// navigation, so the queue is fully operable without a pointer.
function wireQueueKeyboard() {
  const list = document.getElementById('projectList');
  if (!list) return;
  list.addEventListener('keydown', (event) => {
    const items = [...list.querySelectorAll('.opp[data-project-id]')];
    if (!items.length) return;
    const index = items.indexOf(document.activeElement);
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const start = index < 0 ? (event.key === 'ArrowDown' ? -1 : items.length) : index;
      const next = event.key === 'ArrowDown' ? Math.min(start + 1, items.length - 1) : Math.max(start - 1, 0);
      items.forEach(row => { row.tabIndex = -1; });
      items[next].tabIndex = 0;
      items[next].focus();
    } else if ((event.key === 'Enter' || event.key === ' ') && index >= 0) {
      event.preventDefault();
      selectProject(items[index].dataset.projectId);
    }
  });
}

document.getElementById('projectSearch')?.addEventListener('input', renderProjects);
document.getElementById('stateFilter')?.addEventListener('change', renderProjects);
wireQueueKeyboard();
setSyncMode('idle', 'Idle');
renderKpis();
renderWorkspace();
loadDemoLimits();
loadOutreachQueue();
loadProjects();