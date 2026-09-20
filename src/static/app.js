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
        message: null,
      };

      function renderProjects() {
        const list = document.getElementById('projectList');
        list.innerHTML = '';
        for (const project of state.projects) {
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
              <h2>${project.name || 'Unknown project'}</h2>
              <div class="project-meta">${project.city || 'Unknown'}${project.state ? ', ' + project.state : ''} • ${project.bid_date || 'Unknown'}</div>
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
              <div class="match-card ${match.id === state.selectedMatchId ? 'selected' : ''}" data-id="${match.id}">
                <div class="match-head">
                  <div>
                    <strong>#${match.ranking} ${match.contractor_name || 'Unknown contractor'}</strong>
                    <div class="project-meta">${match.match_score != null ? 'Score ' + match.match_score.toFixed(2) : 'Score unknown'} • ${escapeHtml(match.confidence || 'Unknown')} • ${escapeHtml(match.review_status || 'UNREVIEWED')}</div>
                  </div>
                  <span class="badge ${statusBadge(match.review_status)}">${match.review_status || 'UNREVIEWED'}</span>
                </div>
                <div class="actions">
                  <button class="secondary" onclick="openMatch('${match.id}')">Open</button>
                  <button class="approve" onclick="reviewMatch('${match.id}', 'APPROVED')">Approve</button>
                  <button class="reject" onclick="reviewMatch('${match.id}', 'REJECTED')">Reject</button>
                  <button class="skip" onclick="reviewMatch('${match.id}', 'SKIPPED')">Skip</button>
                </div>
              </div>
            `).join('') : '<p class="muted">No matches have been generated for this project yet.</p>'}
          </div>

          ${selectedMatch ? `
            <div class="detail">
              <h3>Match Detail</h3>
              <div class="evidence">
                <div>
                  <div class="section-title">Project</div>
                  <div>${project.name || 'Unknown project'} • ${project.city || 'Unknown'}${project.state ? ', ' + project.state : ''}</div>
                </div>
                <div>
                  <div class="section-title">Contractor</div>
                  <div>${escapeHtml(selectedMatch.contractor_name || 'Unknown contractor')}</div>
                </div>
                <div>
                  <div class="section-title">Match</div>
                  <div>Score: ${selectedMatch.match_score}</div>
                  <div>Confidence: ${escapeHtml(selectedMatch.confidence || 'Unknown')}</div>
                  <div>Ranking: ${selectedMatch.ranking}</div>
                  <div>Matcher: ${escapeHtml(selectedMatch.matcher_version || 'Unknown')}</div>
                  <div>Status: ${escapeHtml(selectedMatch.review_status)}</div>
                </div>
                <div>
                  <div class="section-title">Positive Factors</div>
                  <div>${(selectedMatch.positive_factors || []).length ? selectedMatch.positive_factors.join('<br>') : 'None'}</div>
                </div>
                <div>
                  <div class="section-title">Negative Factors</div>
                  <div>${(selectedMatch.negative_factors || []).length ? selectedMatch.negative_factors.join('<br>') : 'None'}</div>
                </div>
                <div>
                  <div class="section-title">Unknown Factors</div>
                  <div>${(selectedMatch.unknown_factors || []).length ? selectedMatch.unknown_factors.join('<br>') : 'None'}</div>
                </div>
                <div>
                  <div class="section-title">Outreach Draft</div>
                  ${selectedMatch.review_status !== 'APPROVED'
                    ? '<div class="muted">Approve this match to generate an outreach draft.</div>'
                    : state.outreachDrafts[selectedMatch.id]?.error
                      ? '<div class="error">' + state.outreachDrafts[selectedMatch.id].error + '</div>'
                      : state.outreachDrafts[selectedMatch.id]
                        ? '<div class="match-card"><div class="project-meta">Status: ' + state.outreachDrafts[selectedMatch.id].status + ' • To: ' + state.outreachDrafts[selectedMatch.id].recipient_email + '</div><strong>' + state.outreachDrafts[selectedMatch.id].subject + '</strong><pre style="white-space: pre-wrap; font-family: inherit; margin-bottom: 0;">' + state.outreachDrafts[selectedMatch.id].body + '</pre><div class="actions">' + (state.outreachDrafts[selectedMatch.id].status === 'DRAFT' ? '<button class="approve" onclick="updateOutreachDraftStatus(\'' + state.outreachDrafts[selectedMatch.id].id + '\', \'APPROVED\', \'' + selectedMatch.id + '\')">Approve Draft</button><button class="reject" onclick="updateOutreachDraftStatus(\'' + state.outreachDrafts[selectedMatch.id].id + '\', \'REJECTED\', \'' + selectedMatch.id + '\')">Reject Draft</button>' : state.outreachDrafts[selectedMatch.id].status === 'APPROVED' ? '<button class="reject" onclick="updateOutreachDraftStatus(\'' + state.outreachDrafts[selectedMatch.id].id + '\', \'REJECTED\', \'' + selectedMatch.id + '\')">Reject Draft</button>' : '<button class="approve" onclick="updateOutreachDraftStatus(\'' + state.outreachDrafts[selectedMatch.id].id + '\', \'APPROVED\', \'' + selectedMatch.id + '\')">Approve Draft</button>') + '</div></div>'
                        : '<button class="secondary" onclick="generateOutreachDraft(\'' + selectedMatch.id + '\')">Generate Outreach Draft</button>'}
                </div>
                <div>
                  <div class="section-title">Review History</div>
                  <div id="reviewHistory">
                    ${state.reviewAudits[selectedMatch.id]?.error ? `<div class="error">${state.reviewAudits[selectedMatch.id].error}</div>` : state.reviewAudits[selectedMatch.id] ? (state.reviewAudits[selectedMatch.id].length ? state.reviewAudits[selectedMatch.id].map(audit => `<div class="match-card"><strong>${audit.previous_status || 'UNREVIEWED'} → ${audit.new_status}</strong><div class="project-meta">Actor: ${audit.actor || 'Unknown'} • Source: ${audit.source || 'Unknown'} • ${audit.created_at || 'Unknown time'}</div></div>`).join('') : '<div class="muted">No review history yet.</div>') : '<div class="muted">Loading review history...</div>'}
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
          const projects = await response.json();
          state.projects = projects.map(project => ({ ...project, match_count: project.match_count ?? 0 }));
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
        try {
          const params = new URLSearchParams({ limit: String(state.matchLimit), offset: String(state.matchOffset) });
          if (state.matchStatus) params.set('review_status', state.matchStatus);
          const response = await fetch(`/projects/${state.selectedProjectId}/matches?${params.toString()}`);
          if (!response.ok) throw new Error('Unable to load matches');
          state.projectMatches = await response.json();
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
            const body = await response.json();
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
          const body = await response.json();
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
          const body = await response.json();
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
          const body = await response.json();
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
          const body = await response.json();
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
          const body = await response.json();
          if (!response.ok) throw new Error(body.detail || 'Review action failed');
          state.message = { type: 'success', text: `Match marked ${status}.` };
          await refreshProjectMatches();
        } catch (error) {
          state.message = { type: 'error', text: error.message };
          renderWorkspace();
        }
      }

      loadProjects();
