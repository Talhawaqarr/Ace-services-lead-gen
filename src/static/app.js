const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
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
        outreachQueue: {},
        demo: { status: 'idle', result: null },
        message: null,
        workspaceRequestId: 0,
      };

      function renderProjects() {
        const list = document.getElementById('projectList');
        list.innerHTML = '';
        const search = (document.getElementById('projectSearch')?.value || '').trim().toLowerCase();
        const stateFilter = document.getElementById('stateFilter')?.value || '';
        const visibleProjects = state.projects.filter(project => {
          const haystack = [project.name, project.city, project.state, project.description].filter(Boolean).join(' ').toLowerCase();
          return (!search || haystack.includes(search)) && (!stateFilter || project.state === stateFilter);
        });
        for (const project of visibleProjects) {
          const item = document.createElement('li');
          item.className = 'project-item' + (project.id === state.selectedProjectId ? ' active' : '');
          item.innerHTML = `
            <div><strong>${escapeHtml(project.name || 'Unknown project')}</strong></div>
            <div class="project-meta">${escapeHtml(project.city || 'Unknown')}${project.state ? ', ' + escapeHtml(project.state) : ''}</div>
            <div class="project-meta">Bid: ${escapeHtml(project.bid_date || 'Unknown')}</div>
            <div class="project-meta">Matches: ${project.match_count ?? 0}</div>
          `;
          item.onclick = () => selectProject(project.id);
          list.appendChild(item);
        }
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

      function statusBadge(status) {
        const map = {
          APPROVED: 'success',
          REJECTED: 'danger',
          SKIPPED: 'warning',
          UNREVIEWED: 'secondary'
        };
        return map[status] || 'secondary';
      }

      function renderWorkspace() {
        const target = document.getElementById('workspace');
        if (!state.selectedProjectId) {
          target.innerHTML = '<p class="muted">Select a project to review matches.</p>';
          return;
        }
        if (!state.projectMatches) {
          target.innerHTML = '<p class="muted">Loading project workspace...</p>';
          return;
        }

        const project = state.projectMatches.project;
        const matches = state.projectMatches.matches || [];
        const summary = state.projectMatches.summary || { total: 0, unreviewed: 0, approved: 0, rejected: 0, skipped: 0 };
        const pageTotal = state.projectMatches.total ?? 0;
        const pageStart = pageTotal ? state.projectMatches.offset + 1 : 0;
        const pageEnd = Math.min(state.projectMatches.offset + matches.length, pageTotal);

        const selectedMatch = matches.find(m => m.id === state.selectedMatchId) || null;

        const html = `
          <div class="workspace-header">
            <div>
              <h2>${escapeHtml(project.name || 'Unknown project')}</h2>
              <div class="project-meta">${escapeHtml(project.city || 'Unknown')}${project.state ? ', ' + escapeHtml(project.state) : ''} • ${escapeHtml(project.bid_date || 'Unknown')}</div>
            </div>
            <button class="secondary" onclick="refreshProjectMatches()">Refresh</button>
          </div>

          <div class="summary">
            <span class="badge">${summary.total ?? 0} Total</span>
            <span class="badge">${summary.unreviewed ?? 0} Unreviewed</span>
            <span class="badge">${summary.approved ?? 0} Approved</span>
            <span class="badge">${summary.rejected ?? 0} Rejected</span>
            <span class="badge">${summary.skipped ?? 0} Skipped</span>
          </div>

          ${state.message ? `<div class="${state.message.type}">${escapeHtml(state.message.text)}</div>` : ''}

          <div class="actions">
            <select id="matchStatusFilter" class="secondary" onchange="changeMatchStatus(this.value)">
              <option value="">All statuses</option>
              <option value="UNREVIEWED" ${state.matchStatus === 'UNREVIEWED' ? 'selected' : ''}>Unreviewed</option>
              <option value="APPROVED" ${state.matchStatus === 'APPROVED' ? 'selected' : ''}>Approved</option>
              <option value="REJECTED" ${state.matchStatus === 'REJECTED' ? 'selected' : ''}>Rejected</option>
              <option value="SKIPPED" ${state.matchStatus === 'SKIPPED' ? 'selected' : ''}>Skipped</option>
            </select>
            <button class="secondary" onclick="previousMatchPage()" ${state.projectMatches.offset <= 0 ? 'disabled' : ''}>Previous</button>
            <button class="secondary" onclick="nextMatchPage()" ${state.projectMatches.offset + matches.length >= pageTotal ? 'disabled' : ''}>Next</button>
            <span class="muted">${pageStart}-${pageEnd} of ${pageTotal}</span>
          </div>

          <div class="match-list">
            ${matches.length ? matches.map(match => `
              <div class="match-card ${match.id === state.selectedMatchId ? 'selected' : ''}" data-id="${escapeHtml(match.id)}">
                <div class="match-head">
                  <div>
                    <strong>#${escapeHtml(match.ranking)} ${escapeHtml(match.contractor_name || 'Unknown contractor')}</strong>
                    <div class="project-meta">${match.match_score != null ? 'Score ' + match.match_score.toFixed(2) : 'Score unknown'} • ${escapeHtml(match.confidence || 'Unknown')} • ${escapeHtml(match.review_status || 'UNREVIEWED')}</div>
                    <div class="project-meta">${match.contractor_email ? 'Contact: ' + escapeHtml(match.contractor_email) : 'Contact: email unavailable'}</div>
                  </div>
                  <span class="badge ${statusBadge(match.review_status)}">${escapeHtml(match.review_status || 'UNREVIEWED')}</span>
                </div>
                <div class="actions">
                  <button class="secondary" onclick="openMatch('${match.id}')">Open</button>
                  <button class="approve" onclick="reviewMatch('${match.id}', 'APPROVED')">Approve</button>
                  <button class="reject" onclick="reviewMatch('${match.id}', 'REJECTED')">Reject</button>
                  <button class="skip" onclick="reviewMatch('${match.id}', 'SKIPPED')">Skip</button>
                </div>
              </div>
            `).join('') : '<div class="empty"><p class="muted">No matches have been generated for this opportunity.</p><button class="secondary" onclick="generateMatches(\'' + escapeHtml(project.id) + '\')">Generate contractor matches</button></div>'}
          </div>

          ${selectedMatch ? `
            <div class="detail">
              <h3>Match Detail</h3>
              <div class="evidence">
                <div>
                  <div class="section-title">Project</div>
                  <div>${escapeHtml(project.name || 'Unknown project')} • ${escapeHtml(project.city || 'Unknown')}${project.state ? ', ' + escapeHtml(project.state) : ''}</div>
                </div>
                <div>
                  <div class="section-title">Contractor</div>
                  <div>${escapeHtml(selectedMatch.contractor_name || 'Unknown contractor')}</div>
                  <div class="project-meta">${selectedMatch.contractor_email ? 'Primary email: ' + escapeHtml(selectedMatch.contractor_email) : 'Primary email: unavailable — outreach will be blocked'}</div>
                </div>
                <div>
                  <div class="section-title">Match</div>
                  <div>Score: ${escapeHtml(selectedMatch.match_score)}</div>
                  <div>Confidence: ${escapeHtml(selectedMatch.confidence || 'Unknown')}</div>
                  <div>Ranking: ${escapeHtml(selectedMatch.ranking)}</div>
                  <div>Matcher: ${escapeHtml(selectedMatch.matcher_version || 'Unknown')}</div>
                  <div>Status: ${escapeHtml(selectedMatch.review_status)}</div>
                </div>
                <div>
                  <div class="section-title">Positive Factors</div>
                  <div>${(selectedMatch.positive_factors || []).length ? selectedMatch.positive_factors.map(escapeHtml).join('<br>') : 'None'}</div>
                </div>
                <div>
                  <div class="section-title">Negative Factors</div>
                  <div>${(selectedMatch.negative_factors || []).length ? selectedMatch.negative_factors.map(escapeHtml).join('<br>') : 'None'}</div>
                </div>
                <div>
                  <div class="section-title">Unknown Factors</div>
                  <div>${(selectedMatch.unknown_factors || []).length ? selectedMatch.unknown_factors.map(escapeHtml).join('<br>') : 'None'}</div>
                </div>
                <div>
                  <div class="section-title">Outreach</div>
                  ${selectedMatch.contractor_email ? '<div class="project-meta">Draft recipient: ' + escapeHtml(selectedMatch.contractor_email) + '</div>' : '<div class="muted">No primary email is available. Outreach generation will remain blocked.</div>'}
                  <div class="section-title">Outreach Draft</div>
                  ${selectedMatch.review_status !== 'APPROVED'
                    ? '<div class="muted">Approve this match to generate an outreach draft.</div>'
                    : state.outreachDrafts[selectedMatch.id]?.error
                      ? '<div class="error">' + escapeHtml(state.outreachDrafts[selectedMatch.id].error) + '</div>'
                      : state.outreachDrafts[selectedMatch.id]
                        ? '<div class="match-card"><div class="project-meta">Status: ' + escapeHtml(state.outreachDrafts[selectedMatch.id].status) + ' • To: ' + escapeHtml(state.outreachDrafts[selectedMatch.id].recipient_email) + '</div><strong>' + escapeHtml(state.outreachDrafts[selectedMatch.id].subject) + '</strong><pre style="white-space: pre-wrap; font-family: inherit; margin-bottom: 0;">' + escapeHtml(state.outreachDrafts[selectedMatch.id].body) + '</pre><div class="actions">' + (escapeHtml(state.outreachDrafts[selectedMatch.id].status) === 'DRAFT' ? '<button class="approve" onclick="updateOutreachDraftStatus(\'' + state.outreachDrafts[selectedMatch.id].id + '\', \'APPROVED\', \'' + selectedMatch.id + '\')">Approve Draft</button><button class="reject" onclick="updateOutreachDraftStatus(\'' + state.outreachDrafts[selectedMatch.id].id + '\', \'REJECTED\', \'' + selectedMatch.id + '\')">Reject Draft</button>' : escapeHtml(state.outreachDrafts[selectedMatch.id].status) === 'APPROVED' ? '<button class="reject" onclick="updateOutreachDraftStatus(\'' + state.outreachDrafts[selectedMatch.id].id + '\', \'REJECTED\', \'' + selectedMatch.id + '\')">Reject Draft</button>' : '<button class="approve" onclick="updateOutreachDraftStatus(\'' + state.outreachDrafts[selectedMatch.id].id + '\', \'APPROVED\', \'' + selectedMatch.id + '\')">Approve Draft</button>') + '</div></div>'
                        : '<button class="secondary" onclick="generateOutreachDraft(\'' + selectedMatch.id + '\')">Generate Outreach Draft</button>'}
                </div>
                <div>
                  <div class="section-title">Delivery Queue</div>
                  ${state.outreachDrafts[selectedMatch.id]?.status === 'APPROVED'
                    ? state.outreachQueue[state.outreachDrafts[selectedMatch.id].id]
                      ? '<div class="success">Queued safely — <strong>NOT SENT</strong>.</div>'
                      : '<button class="secondary" onclick="queueOutreachDraft(\\'' + state.outreachDrafts[selectedMatch.id].id + '\\', \\' + selectedMatch.id + '\\')">Queue outreach (not sent)</button>'
                    : '<div class="muted">Approve the outreach draft before queueing.</div>'}
                </div>
                <div>
                  <div class="section-title">Review History</div>
                  <div id="reviewHistory">
                    ${state.reviewAudits[selectedMatch.id]?.error ? `<div class="error">${escapeHtml(state.reviewAudits[selectedMatch.id].error)}</div>` : state.reviewAudits[selectedMatch.id] ? (state.reviewAudits[selectedMatch.id].length ? state.reviewAudits[selectedMatch.id].map(audit => `<div class="match-card"><strong>${escapeHtml(audit.previous_status || 'UNREVIEWED')} → ${escapeHtml(audit.new_status)}</strong><div class="project-meta">Actor: ${escapeHtml(audit.actor || 'Unknown')} • Source: ${escapeHtml(audit.source || 'Unknown')} • ${escapeHtml(audit.created_at || 'Unknown time')}</div></div>`).join('') : '<div class="muted">No review history yet.</div>') : '<div class="muted">Loading review history...</div>'}
                  </div>
                </div>
              </div>
            </div>
          ` : ''}
        `;

        target.innerHTML = html;
      }

      async function loadProjects() {
        try {
          const response = await fetch('/opportunities?limit=100&active_only=true&construction_only=true');
          if (!response.ok) throw new Error('Unable to load projects');
          const projects = await readJson(response);
          state.projects = projects.map(project => ({ ...project, match_count: project.match_count ?? 0 }));
          populateStateFilter();
          if (!state.selectedProjectId && projects.length) {
            selectProject(projects[0].id);
          }
          renderProjects();
        } catch (error) {
          state.message = { type: 'error', text: error.message };
          renderProjects();
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
          state.message = { type: 'success', text: `Match marked ${status}.` };
          await refreshProjectMatches();
        } catch (error) {
          state.message = { type: 'error', text: error.message };
          renderWorkspace();
        }
      }


      async function queueOutreachDraft(draftId, matchId) {
        try {
          const response = await fetch('/outreach-drafts/' + draftId + '/queue', { method: 'POST' });
          const body = await readJson(response);
          if (!response.ok) throw new Error(body.detail || 'Unable to queue outreach draft');
          state.outreachQueue[draftId] = body;
          state.message = { type: 'success', text: 'Outreach queued safely — NOT SENT.' };
          renderWorkspace();
        } catch (error) {
          state.message = { type: 'error', text: error.message };
          renderWorkspace();
        }
      }

      async function runDemo() {
        const status = document.getElementById('demoStatus');
        if (status) status.textContent = 'Running one bounded live SAM.gov request…';
        state.demo.status = 'running';
        try {
          const response = await fetch('/demo/run?keyword=36C26126Q1279&state=CA', { method: 'POST' });
          const body = await readJson(response);
          if (!response.ok) throw new Error(body.detail || 'Demo run failed');
          state.demo = { status: 'complete', result: body };
          if (status) {
            const opp = body.opportunities || {};
            status.textContent = 'Live sync complete: fetched ' + (opp.records_fetched ?? 0) +
              ', accepted ' + (opp.accepted ?? 0) +
              ', qualified ' + (body.qualified_projects ?? 0) +
              ', matches ' + (body.matches_generated ?? 0) + '.';
          }
          await loadProjects();
          if (body.matches_generated === 0) {
            state.message = { type: 'warning', text: 'Live data arrived, but no contractor match was generated. Review the opportunity and candidate coverage.' };
            renderWorkspace();
          }
        } catch (error) {
          state.demo = { status: 'error', result: null };
          if (status) status.textContent = 'Demo run failed: ' + error.message;
        }
      }

      document.getElementById('projectSearch')?.addEventListener('input', renderProjects);
      document.getElementById('stateFilter')?.addEventListener('change', renderProjects);
      loadProjects();
