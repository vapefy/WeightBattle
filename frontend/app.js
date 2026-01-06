/**
 * Weight Battle Frontend Application
 * Vanilla JavaScript - German UI
 */

// ============================================================================
// Configuration
// ============================================================================

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : '';

// ============================================================================
// State
// ============================================================================

let state = {
    users: [],
    selectedUserId: null,
    selectedWeightUserId: null,
    userStatsCache: {},
    overview: null,
    progressChart: null,
    weightChart: null,
    setupComplete: false,
};

// ============================================================================
// API Functions
// ============================================================================

async function api(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unbekannter Fehler' }));
        throw new Error(error.detail || 'API Fehler');
    }

    return response.json();
}

// ============================================================================
// Setup Screen
// ============================================================================

async function checkSetupStatus() {
    try {
        const status = await api('/setup/status');
        state.setupComplete = status.setup_complete;
        return status.setup_complete;
    } catch (error) {
        console.error('Failed to check setup status:', error);
        return false;
    }
}

function showSetupScreen() {
    // Hide nav and all screens
    document.getElementById('main-nav').classList.add('hidden');
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));

    // Show setup screen
    document.getElementById('setup').classList.add('active');

    // Set default end date (Easter 2026)
    document.getElementById('setup-end-date').value = '2026-04-05';

    // Add initial participant rows
    addParticipantRow();
    addParticipantRow();
}

function showMainApp() {
    // Show nav
    document.getElementById('main-nav').classList.remove('hidden');

    // Hide setup, show dashboard
    document.getElementById('setup').classList.remove('active');
    document.getElementById('dashboard').classList.add('active');

    // Load dashboard data
    loadDashboard();
}

function initSetup() {
    // Add participant button
    document.getElementById('add-participant').addEventListener('click', addParticipantRow);

    // Start battle button
    document.getElementById('start-battle').addEventListener('click', startBattle);
}

let participantCounter = 0;

function addParticipantRow() {
    const container = document.getElementById('setup-participants');
    const id = ++participantCounter;

    const row = document.createElement('div');
    row.className = 'participant-row';
    row.dataset.participantId = id;
    row.innerHTML = `
        <div class="form-group">
            <input type="text"
                   class="form-input participant-name"
                   placeholder="Name"
                   maxlength="50">
        </div>
        <div class="form-group">
            <input type="number"
                   class="form-input participant-weight"
                   placeholder="kg"
                   step="0.1"
                   min="30"
                   max="300">
        </div>
        <button type="button" class="btn-remove" onclick="removeParticipantRow(${id})">x</button>
    `;

    container.appendChild(row);
}

function removeParticipantRow(id) {
    const container = document.getElementById('setup-participants');
    const row = container.querySelector(`[data-participant-id="${id}"]`);
    if (row && container.children.length > 1) {
        row.remove();
    } else if (container.children.length === 1) {
        showToast('Mindestens ein Teilnehmer erforderlich', 'error');
    }
}

async function startBattle() {
    // Gather data
    const endDate = document.getElementById('setup-end-date').value;
    const potAmount = parseInt(document.getElementById('setup-pot-amount').value);
    const totalAmount = parseInt(document.getElementById('setup-total-amount').value);

    if (!endDate) {
        showToast('Bitte Enddatum eingeben', 'error');
        return;
    }

    if (isNaN(potAmount) || potAmount < 1) {
        showToast('Bitte gultigen Einsatz eingeben', 'error');
        return;
    }

    if (isNaN(totalAmount) || totalAmount < 10) {
        showToast('Bitte gultige Gesamtsumme eingeben', 'error');
        return;
    }

    // Gather participants
    const participantRows = document.querySelectorAll('.participant-row');
    const participants = [];

    for (const row of participantRows) {
        const name = row.querySelector('.participant-name').value.trim();
        const weight = parseFloat(row.querySelector('.participant-weight').value);

        if (!name) {
            showToast('Bitte alle Namen eingeben', 'error');
            return;
        }

        if (isNaN(weight) || weight < 30 || weight > 300) {
            showToast(`Bitte gultiges Gewicht fur ${name} eingeben`, 'error');
            return;
        }

        participants.push({ name, start_weight: weight });
    }

    if (participants.length < 1) {
        showToast('Mindestens ein Teilnehmer erforderlich', 'error');
        return;
    }

    // Submit setup
    try {
        await api('/setup', {
            method: 'POST',
            body: JSON.stringify({
                participants: participants,
                pot_contribution: potAmount,
                total_amount: totalAmount,
                battle_end_date: endDate,
            }),
        });

        showToast('Battle gestartet!', 'success');
        state.setupComplete = true;

        // Switch to main app
        setTimeout(() => showMainApp(), 500);
    } catch (error) {
        showToast('Fehler: ' + error.message, 'error');
    }
}

// ============================================================================
// Navigation
// ============================================================================

function initNavigation() {
    const navButtons = document.querySelectorAll('.nav-btn');
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const screen = btn.dataset.screen;
            switchScreen(screen);
        });
    });
}

function switchScreen(screenId) {
    // Update nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.screen === screenId);
    });

    // Update screens
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.toggle('active', screen.id === screenId);
    });

    // Load data for the screen
    if (screenId === 'dashboard') {
        loadDashboard();
    } else if (screenId === 'weigh-in') {
        loadWeighInScreen();
    } else if (screenId === 'stats') {
        loadStatsScreen();
    }
}

// ============================================================================
// Dashboard
// ============================================================================

async function loadDashboard() {
    try {
        const [overview, potInfo, users] = await Promise.all([
            api('/stats/overview'),
            api('/stats/pot'),
            api('/users'),
        ]);

        state.overview = overview;
        state.users = users;
        renderDashboard(overview, potInfo);
        renderWeightPlayerButtons(users);

        // Select first user by default
        if (users.length > 0 && !state.selectedWeightUserId) {
            selectWeightPlayer(users[0].id);
        }
    } catch (error) {
        showToast('Fehler beim Laden: ' + error.message, 'error');
    }
}

function renderDashboard(overview, potInfo) {
    // Days remaining
    document.getElementById('days-remaining').textContent = `${overview.days_remaining} Tage`;

    // Progress period (from battle start to now)
    const periodEl = document.getElementById('progress-period');
    if (overview.leaderboard && overview.leaderboard.length > 0) {
        periodEl.textContent = `Seit Beginn bis heute`;
    } else {
        periodEl.textContent = '--';
    }

    // Total standings (percentage lost from start weight)
    const standingsEl = document.getElementById('total-standings');
    if (overview.leaderboard && overview.leaderboard.length > 0) {
        // Sort by total_percent_change (higher = more weight lost = better)
        const sorted = [...overview.leaderboard].sort((a, b) =>
            b.total_percent_change - a.total_percent_change
        );

        standingsEl.innerHTML = sorted.map(item => `
            <div class="standing-item">
                <span class="standing-name">${item.name}</span>
                <span class="standing-change ${item.total_percent_change >= 0 ? 'positive' : 'negative'}">
                    ${formatPercent(item.total_percent_change)}
                </span>
            </div>
        `).join('');
    } else {
        standingsEl.innerHTML = '<p class="text-muted">Noch keine Daten</p>';
    }

    // Leader
    const leaderEl = document.getElementById('leader-info');
    if (overview.leader) {
        leaderEl.innerHTML = `
            <span class="leader-name">${overview.leader.name}</span>
            <span class="leader-wins">${overview.leader.wins} Siege</span>
        `;
    } else {
        leaderEl.innerHTML = '<span class="leader-name">--</span>';
    }

    // POT
    document.getElementById('pot-total').textContent = overview.pot_total;

    // Recent contributions
    const recentEl = document.getElementById('recent-contributions');
    if (potInfo.recent_contributions.length > 0) {
        recentEl.innerHTML = potInfo.recent_contributions.map(item => `
            <div class="contribution-item">
                ${item.loser_name} (${formatDate(item.week_start)}): ${item.amount} EUR
            </div>
        `).join('');
    } else {
        recentEl.innerHTML = '<p>Noch keine Einzahlungen</p>';
    }
}

function renderWeightPlayerButtons(users) {
    const container = document.getElementById('weight-player-buttons');
    if (!container) return;

    container.innerHTML = users.map(user => `
        <button class="player-btn ${state.selectedWeightUserId === user.id ? 'active' : ''}"
                data-user-id="${user.id}"
                onclick="selectWeightPlayer(${user.id})">
            ${user.name}
        </button>
    `).join('');
}

async function selectWeightPlayer(userId) {
    state.selectedWeightUserId = userId;
    renderWeightPlayerButtons(state.users);

    // Fetch user stats if not cached
    if (!state.userStatsCache[userId]) {
        try {
            const userStats = await api(`/stats/user/${userId}`);
            state.userStatsCache[userId] = userStats;
        } catch (error) {
            showToast('Fehler beim Laden: ' + error.message, 'error');
            return;
        }
    }

    renderWeightChart(state.userStatsCache[userId]);
}

function renderWeightChart(userStats) {
    const canvas = document.getElementById('weight-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Destroy existing chart
    if (state.weightChart) {
        state.weightChart.destroy();
    }

    if (!userStats || !userStats.weekly_data || userStats.weekly_data.length === 0) {
        // Show start weight only
        if (userStats && userStats.start_weight) {
            state.weightChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Start'],
                    datasets: [{
                        label: userStats.name || 'Gewicht',
                        data: [userStats.start_weight],
                        borderColor: '#4299e1',
                        backgroundColor: '#4299e120',
                        tension: 0.3,
                        fill: true,
                        pointRadius: 6,
                        pointHoverRadius: 8,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            title: {
                                display: true,
                                text: 'Gewicht (kg)',
                            },
                        },
                    },
                    plugins: {
                        legend: {
                            display: false,
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `${context.parsed.y.toFixed(1)} kg`;
                                }
                            }
                        }
                    },
                },
            });
        }
        return;
    }

    // Build data points: start weight + all weigh-ins
    const labels = ['Start'];
    const weights = [userStats.start_weight];

    // Sort weekly data by week_start
    const sortedWeighIns = [...userStats.weekly_data].sort((a, b) =>
        new Date(a.week_start) - new Date(b.week_start)
    );

    sortedWeighIns.forEach(wi => {
        labels.push(formatDateShort(wi.week_start));
        weights.push(wi.weight);
    });

    // Calculate min/max for better Y axis scaling
    const minWeight = Math.min(...weights);
    const maxWeight = Math.max(...weights);
    const padding = (maxWeight - minWeight) * 0.2 || 2;

    state.weightChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: userStats.name || 'Gewicht',
                data: weights,
                borderColor: '#4299e1',
                backgroundColor: '#4299e120',
                tension: 0.3,
                fill: true,
                pointRadius: 6,
                pointHoverRadius: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    title: {
                        display: true,
                        text: 'Gewicht (kg)',
                    },
                    min: Math.floor(minWeight - padding),
                    max: Math.ceil(maxWeight + padding),
                },
            },
            plugins: {
                legend: {
                    display: false,
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.y.toFixed(1)} kg`;
                        }
                    }
                }
            },
        },
    });
}

// ============================================================================
// Weigh-in Screen
// ============================================================================

async function loadWeighInScreen() {
    try {
        state.users = await api('/users');
        renderUserSelect();
    } catch (error) {
        showToast('Fehler beim Laden: ' + error.message, 'error');
    }
}

function renderUserSelect() {
    const container = document.getElementById('user-select');
    if (state.users.length === 0) {
        container.innerHTML = '<p>Noch keine Teilnehmer</p>';
        return;
    }

    container.innerHTML = state.users.map(user => `
        <button class="user-btn ${state.selectedUserId === user.id ? 'selected' : ''}"
                data-user-id="${user.id}">
            ${user.name}
        </button>
    `).join('');

    // Add click handlers
    container.querySelectorAll('.user-btn').forEach(btn => {
        btn.addEventListener('click', () => selectUser(parseInt(btn.dataset.userId)));
    });
}

function selectUser(userId) {
    state.selectedUserId = userId;
    renderUserSelect();
    document.getElementById('weight-input').value = '';
    document.getElementById('preview').classList.add('hidden');
    updateSaveButton();
}

function initWeighInForm() {
    const weightInput = document.getElementById('weight-input');
    const saveBtn = document.getElementById('save-weight');

    // Live preview on input
    let debounceTimer;
    weightInput.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => updatePreview(), 300);
        updateSaveButton();
    });

    // Save button
    saveBtn.addEventListener('click', saveWeighIn);
}

async function updatePreview() {
    const weight = parseFloat(document.getElementById('weight-input').value);
    const previewEl = document.getElementById('preview');

    if (!state.selectedUserId || isNaN(weight) || weight < 30) {
        previewEl.classList.add('hidden');
        return;
    }

    try {
        const preview = await api(`/weigh-ins/preview?user_id=${state.selectedUserId}&weight=${weight}`);

        document.getElementById('preview-previous').textContent = `${preview.previous_weight} kg`;

        const changeEl = document.getElementById('preview-change');
        changeEl.textContent = formatPercent(preview.percent_change);
        changeEl.className = preview.percent_change >= 0 ? 'positive' : 'negative';

        previewEl.classList.remove('hidden');
    } catch (error) {
        previewEl.classList.add('hidden');
    }
}

function updateSaveButton() {
    const weight = parseFloat(document.getElementById('weight-input').value);
    const saveBtn = document.getElementById('save-weight');
    saveBtn.disabled = !state.selectedUserId || isNaN(weight) || weight < 30 || weight > 300;
}

async function saveWeighIn() {
    const weight = parseFloat(document.getElementById('weight-input').value);

    if (!state.selectedUserId || isNaN(weight)) {
        return;
    }

    try {
        const result = await api('/weigh-ins', {
            method: 'POST',
            body: JSON.stringify({
                user_id: state.selectedUserId,
                weight: weight,
            }),
        });

        showToast(`Gespeichert: ${formatPercent(result.percent_change)}`, 'success');

        // Reset form
        document.getElementById('weight-input').value = '';
        document.getElementById('preview').classList.add('hidden');
        state.selectedUserId = null;
        renderUserSelect();
        updateSaveButton();
    } catch (error) {
        showToast('Fehler: ' + error.message, 'error');
    }
}

// ============================================================================
// Statistics Screen
// ============================================================================

async function loadStatsScreen() {
    try {
        const [leaderboard, progress, prognosis, potInfo, auditLog] = await Promise.all([
            api('/stats/leaderboard'),
            api('/stats/progress'),
            api('/stats/prognosis'),
            api('/stats/pot'),
            api('/audit?limit=20'),
        ]);

        renderLeaderboard(leaderboard);
        renderProgressChart(progress);
        renderPrognosis(prognosis);
        renderPotDetails(potInfo);
        renderAuditLog(auditLog);
    } catch (error) {
        showToast('Fehler beim Laden: ' + error.message, 'error');
    }
}

function renderLeaderboard(leaderboard) {
    const container = document.getElementById('leaderboard');

    if (leaderboard.length === 0) {
        container.innerHTML = '<p>Noch keine Daten</p>';
        return;
    }

    container.innerHTML = leaderboard.map(item => `
        <div class="leaderboard-item">
            <div class="leaderboard-rank ${item.rank <= 3 ? 'rank-' + item.rank : ''}">
                ${item.rank}
            </div>
            <div class="leaderboard-info">
                <div class="leaderboard-name">${item.name}</div>
                <div class="leaderboard-stats">
                    ${item.current_weight} kg | ${formatPercent(item.total_percent_change)} gesamt
                </div>
            </div>
            <div class="leaderboard-wins">${item.wins}</div>
        </div>
    `).join('');
}

function renderProgressChart(progress) {
    const ctx = document.getElementById('progress-chart').getContext('2d');

    // Destroy existing chart
    if (state.progressChart) {
        state.progressChart.destroy();
    }

    if (progress.progress_data.length === 0) {
        return;
    }

    // Find all unique weeks (excluding Start)
    const allWeeks = new Set();
    progress.progress_data.forEach(user => {
        user.data.forEach(point => {
            if (point.week !== 'Start') allWeeks.add(point.week);
        });
    });
    const weeks = Array.from(allWeeks).sort();

    // Build datasets - convert to "% lost" (100 - relative value)
    // So 96.5% of start weight = 3.5% lost
    const colors = ['#4299e1', '#48bb78', '#ed8936', '#f56565', '#9f7aea', '#38b2ac', '#d69e2e'];
    const datasets = progress.progress_data.map((user, index) => {
        const dataMap = new Map();
        user.data.forEach(p => {
            if (p.week !== 'Start') {
                // Convert to percentage lost (higher = better)
                dataMap.set(p.week, 100 - p.value);
            }
        });

        return {
            label: user.name,
            data: weeks.map(week => {
                const val = dataMap.get(week);
                return val !== undefined ? val : null;
            }),
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length] + '40',
            tension: 0.3,
            fill: true,
            pointRadius: 4,
            pointHoverRadius: 6,
        };
    });

    state.progressChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: weeks.map(w => formatDateShort(w)),
            datasets: datasets,
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    title: {
                        display: true,
                        text: '% abgenommen',
                    },
                    beginAtZero: true,
                    suggestedMax: 10,
                },
            },
            plugins: {
                legend: {
                    position: 'bottom',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}% abgenommen`;
                        }
                    }
                }
            },
        },
    });
}

function renderPrognosis(prognosis) {
    const container = document.getElementById('prognosis');

    if (prognosis.projections.length === 0) {
        container.innerHTML = '<p>Noch keine Daten</p>';
        return;
    }

    container.innerHTML = `
        <p class="text-muted" style="margin-bottom: var(--space-md); font-size: var(--font-size-sm);">
            Noch ${prognosis.weeks_remaining} Wochen
        </p>
        ${prognosis.projections.map(item => {
            const trendClass = item.trend === 'losing' ? 'trend-losing' :
                              item.trend === 'gaining' ? 'trend-gaining' : 'trend-stable';
            const trendText = item.trend === 'losing' ? 'Abnehmend' :
                             item.trend === 'gaining' ? 'Zunehmend' : 'Stabil';

            return `
                <div class="prognosis-item">
                    <div>
                        <span class="prognosis-name">${item.name}</span>
                        ${item.projected_weight ? `
                            <span class="prognosis-value" style="margin-left: var(--space-sm);">
                                ${item.projected_weight} kg
                            </span>
                        ` : ''}
                    </div>
                    <span class="prognosis-trend ${trendClass}">${trendText}</span>
                </div>
            `;
        }).join('')}
    `;
}

function renderPotDetails(potInfo) {
    const container = document.getElementById('pot-details');

    container.innerHTML = `
        <div class="pot-detail-item" style="font-weight: 600;">
            <span>Gesamtsumme</span>
            <span>${potInfo.total_amount} EUR</span>
        </div>
        <div class="pot-detail-item">
            <span>Im Topf</span>
            <span>${potInfo.total} EUR</span>
        </div>
        <div class="pot-detail-item" style="font-weight: 600; color: var(--color-accent);">
            <span>Verlierer zahlt noch</span>
            <span>${potInfo.remaining_amount} EUR</span>
        </div>
        ${potInfo.contributions.filter(c => c.total_contributed > 0).length > 0 ? `
            <div style="margin-top: var(--space-md); border-top: 1px solid var(--color-border); padding-top: var(--space-md);">
                <strong style="font-size: var(--font-size-sm); color: var(--color-text-muted);">Einzahlungen:</strong>
            </div>
            ${potInfo.contributions.filter(c => c.total_contributed > 0).map(item => `
                <div class="pot-detail-item">
                    <span>${item.name} (${item.times_lost}x verloren)</span>
                    <span>${item.total_contributed} EUR</span>
                </div>
            `).join('')}
        ` : ''}
        ${potInfo.potential_final_payers.length > 0 ? `
            <div style="margin-top: var(--space-md); padding: var(--space-sm); background: rgba(245, 101, 101, 0.1); border: 1px solid var(--color-danger); border-radius: var(--radius-md);">
                <strong>Zahlt den Rest:</strong>
                ${potInfo.potential_final_payers.map(p => p.name).join(', ')}
                <span style="color: var(--color-text-muted);"></span>
            </div>
        ` : ''}
    `;
}

function renderAuditLog(auditLog) {
    const container = document.getElementById('audit-log');

    if (auditLog.length === 0) {
        container.innerHTML = '<p>Keine Anderungen</p>';
        return;
    }

    container.innerHTML = auditLog.map(item => {
        let changeText = '';
        if (item.entity === 'weigh_in' && item.new_value) {
            changeText = `Gewicht: ${item.new_value.weight} kg`;
        } else if (item.entity === 'user' && item.new_value) {
            changeText = `${item.new_value.name}`;
        }

        return `
            <div class="audit-item">
                <div class="audit-date">${formatDateTime(item.changed_at)}</div>
                <div class="audit-change">
                    ${item.changed_by}: ${changeText}
                </div>
            </div>
        `;
    }).join('');
}

// ============================================================================
// Toast Notifications
// ============================================================================

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;

    // Show
    setTimeout(() => toast.classList.remove('hidden'), 10);

    // Hide after 3 seconds
    setTimeout(() => toast.classList.add('hidden'), 3000);
}

// ============================================================================
// Utility Functions
// ============================================================================

function formatPercent(value) {
    if (value === null || value === undefined) return '--%';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
}

function formatDate(dateStr) {
    if (!dateStr) return '--';
    const date = new Date(dateStr);
    return date.toLocaleDateString('de-DE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
    });
}

function formatDateShort(dateStr) {
    if (!dateStr) return '--';
    const date = new Date(dateStr);
    return date.toLocaleDateString('de-DE', {
        day: '2-digit',
        month: '2-digit',
    });
}

function formatDateTime(dateStr) {
    if (!dateStr) return '--';
    const date = new Date(dateStr);
    return date.toLocaleDateString('de-DE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    initNavigation();
    initWeighInForm();
    initSetup();

    // Check if setup is complete
    const setupComplete = await checkSetupStatus();

    if (setupComplete) {
        showMainApp();
    } else {
        showSetupScreen();
    }
});
