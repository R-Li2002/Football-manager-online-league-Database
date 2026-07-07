var currentCompetitionSubtab = 'standings';
var currentCompetitionLevel = '超级';
var standingsData = {levels: [], rows: []};
var scheduleData = {levels: [], rounds: [], matches: []};
var playerRankingData = {levels: [], rows: []};
var suspensionData = {levels: [], teams: []};
var siteNotesData = {};
var cupBracketData = {};
var competitionDataLoaded = false;
var currentPlayerRankingType = 'goals';
var activeSuspensionEditorTeamId = null;
var competitionImageExportBusy = false;
var currentMobileStandingsScope = 'total';
var matchTeamPlayerCache = new Map();
var activeMatchEventSuggestionContext = null;
var activeSuspensionSuggestionContext = null;
var activeMobileScheduleEditMatchId = null;
var matchEventRowDomIdSeed = 0;
var scheduleAutoSaveTimers = new Map();

const COMPETITION_LEVEL_ORDER = {'超级': 1, '甲级': 2, '乙级': 3, '冠军杯': 4, '联盟杯': 5, '无铭剑杯': 6};
const LEAGUE_COMPETITION_LEVELS = ['超级', '甲级', '乙级'];
const CUP_COMPETITIONS = {
    '冠军杯': {key: 'champions_cup', className: 'champion-cup', initializeLabel: '初始化冠军杯', englishName: 'Champions Cup'},
    '联盟杯': {key: 'league_cup', className: 'league-cup', initializeLabel: '初始化联盟杯', englishName: 'League Cup'},
    '无铭剑杯': {key: 'wumingjian_cup', className: 'wumingjian-cup', initializeLabel: '初始化无铭剑杯', englishName: 'Wumingjian Cup'},
};
const MATCH_STATUS_LABELS = {
    scheduled: '未赛',
    played: '已赛',
    postponed: '延期',
    cancelled: '取消',
    home_forfeit: '主队判负',
    away_forfeit: '客队判负',
    double_forfeit: '双方判负',
};
const CUP_TEAM_SHORT_NAMES = {
    'Associazione Sportiva Roma': 'AS Roma',
    'Bayer 04 Leverkusen': 'Bayer 04',
    'Borussia Dortmund': 'Dortmund',
    'Brighton & Hove Albion': 'Brighton',
    'Club Atlético Boca Juniors': 'Boca Juniors',
    'Club Atlético Talleres de Córdoba': 'Talleres',
    'Eintracht Frankfurt': 'Frankfurt',
    'FC Bayern München': 'Bayern',
    'FC Heidenheim 1846': 'Heidenheim',
    'Futebol Clube do Porto': 'FC Porto',
    'Manchester United': 'Man United',
    'Newcastle United': 'Newcastle',
    'Nottingham Forest': 'Nottm Forest',
    'Olympique Lyonnais': 'Lyon',
    'Olympique de Marseille': 'Marseille',
    'Paris Saint-Germain': 'PSG',
    'RC Strasbourg Alsace': 'Strasbourg',
    'Sheffield United': 'Sheffield Utd',
    'Sport Lisboa e Benfica': 'Benfica',
    'Sporting Clube de Portugal': 'Sporting CP',
    'Sportklub Sturm Graz': 'Sturm Graz',
    'Tottenham Hotspur': 'Tottenham',
    'Wolverhampton Wanderers': 'Wolves',
};
const SCHEDULE_TEAM_ALIASES = {
    'A.Bilbao': 'A. Bilbao',
    Ajax: 'AFC Ajax',
    'AS Roma': 'Associazione Sportiva Roma',
    'At Madrid': 'A. Madrid',
    Bayern: 'FC Bayern München',
    Benfica: 'Sport Lisboa e Benfica',
    Boca: 'Club Atlético Boca Juniors',
    Bournemouth: 'AFC Bournemouth',
    Brighton: 'Brighton & Hove Albion',
    Como: 'Como 1907',
    Coventry: 'Coventry City',
    Dortmund: 'Borussia Dortmund',
    Frankfurt: 'Eintracht Frankfurt',
    Heidenheim: 'FC Heidenheim 1846',
    Leeds: 'Leeds United',
    Leicester: 'Leicester City',
    'Man Utd': 'Manchester United',
    Newcastle: 'Newcastle United',
    'Nottm Forest': 'Nottingham Forest',
    OL: 'Olympique Lyonnais',
    OM: 'Olympique de Marseille',
    PSG: 'Paris Saint-Germain',
    'R.Madrid': 'R. Madrid',
    RBL: 'RB Leipzig',
    Schalke: 'FC Schalke 04',
    'Sheff Utd': 'Sheffield United',
    'Sporing CP': 'Sporting Clube de Portugal',
    Strasbourg: 'RC Strasbourg Alsace',
    'Sturm Graz': 'Sportklub Sturm Graz',
    Talleres: 'Club Atlético Talleres de Córdoba',
    Tottenham: 'Tottenham Hotspur',
    'West Ham': 'West Ham United',
    Wolves: 'Wolverhampton Wanderers',
    Zhejiang: 'Oriental Dragon',
};

function getCompetitionLevelOrder(level) {
    return COMPETITION_LEVEL_ORDER[level] || 99;
}

function isCupCompetitionLevel(level = currentCompetitionLevel) {
    return Boolean(CUP_COMPETITIONS[level]);
}

function getCurrentCupConfig() {
    return CUP_COMPETITIONS[currentCompetitionLevel] || null;
}

function getCupTeamDisplayName(teamName) {
    const raw = String(teamName || '').trim();
    if (!raw || raw === '待定') return raw || '待定';
    if (CUP_TEAM_SHORT_NAMES[raw]) return CUP_TEAM_SHORT_NAMES[raw];
    if (raw.length <= 15) return raw;
    const compact = raw
        .replace(/\bFootball Club\b/gi, '')
        .replace(/\bFutebol Clube\b/gi, 'FC')
        .replace(/\bAssociazione Sportiva\b/gi, 'AS')
        .replace(/\bSport Lisboa e Benfica\b/gi, 'Benfica')
        .replace(/\bSporting Clube de Portugal\b/gi, 'Sporting CP')
        .replace(/\bClub Atlético\b/gi, '')
        .replace(/\bOlympique de\b/gi, '')
        .replace(/\bOlympique\b/gi, '')
        .replace(/\bUnited\b/gi, 'Utd')
        .replace(/\bWanderers\b/gi, 'Wolves')
        .replace(/\s+/g, ' ')
        .trim();
    if (compact && compact.length <= 15) return compact;
    const words = (compact || raw).split(/\s+/).filter(Boolean);
    if (words.length >= 3) return words.slice(0, 2).join(' ');
    return compact || raw;
}

function getMatchStatusLabel(status) {
    return MATCH_STATUS_LABELS[status] || status || '未赛';
}

function isScheduleForfeitStatus(status) {
    return ['home_forfeit', 'away_forfeit', 'double_forfeit'].includes(String(status || ''));
}

function getForfeitScoreForStatus(status) {
    if (status === 'home_forfeit') return {home_score: 0, away_score: 0};
    if (status === 'away_forfeit') return {home_score: 3, away_score: 0};
    if (status === 'double_forfeit') return {home_score: 0, away_score: 0};
    return null;
}

function getScheduleStatusTone(status) {
    return isScheduleForfeitStatus(status) ? 'is-forfeit' : status === 'played' ? 'is-played' : '';
}

function htmlJsString(value) {
    return escapeHtml(JSON.stringify(String(value ?? '')));
}

function formatMatchScore(match) {
    if (match.home_score === null || match.home_score === undefined || match.away_score === null || match.away_score === undefined) {
        return '-';
    }
    return `${match.home_score} - ${match.away_score}`;
}

function isMobileViewport() {
    return window.matchMedia?.('(max-width: 780px)').matches || window.innerWidth <= 780;
}

function showCompetitionSubtab(subtab) {
    currentCompetitionSubtab = ['schedule', 'playerRankings', 'suspensions'].includes(subtab) ? subtab : 'standings';
    if (['playerRankings', 'suspensions'].includes(currentCompetitionSubtab) && !LEAGUE_COMPETITION_LEVELS.includes(currentCompetitionLevel)) {
        currentCompetitionLevel = '超级';
    }
    document.getElementById('competitionSubtabStandings')?.classList.toggle('active', currentCompetitionSubtab === 'standings');
    document.getElementById('competitionSubtabSchedule')?.classList.toggle('active', currentCompetitionSubtab === 'schedule');
    document.getElementById('competitionSubtabPlayerRankings')?.classList.toggle('active', currentCompetitionSubtab === 'playerRankings');
    document.getElementById('competitionSubtabSuspensions')?.classList.toggle('active', currentCompetitionSubtab === 'suspensions');
    document.getElementById('competitionStandingsView')?.classList.toggle('active', currentCompetitionSubtab === 'standings');
    document.getElementById('competitionScheduleView')?.classList.toggle('active', currentCompetitionSubtab === 'schedule');
    document.getElementById('competitionPlayerRankingsView')?.classList.toggle('active', currentCompetitionSubtab === 'playerRankings');
    document.getElementById('competitionSuspensionsView')?.classList.toggle('active', currentCompetitionSubtab === 'suspensions');
    syncCompetitionLevelTabs();
    if (currentCompetitionSubtab === 'schedule') {
        renderScheduleBoard();
    } else if (currentCompetitionSubtab === 'playerRankings') {
        renderPlayerRankingsBoard();
    } else if (currentCompetitionSubtab === 'suspensions') {
        renderSuspensionsBoard();
    } else {
        renderCompetitionPrimaryBoard();
    }
    if (typeof syncAppHistory === 'function') {
        syncAppHistory('replace');
    }
}

function setCompetitionLevel(level) {
    currentCompetitionLevel = [...LEAGUE_COMPETITION_LEVELS, ...Object.keys(CUP_COMPETITIONS)].includes(level) ? level : '超级';
    if (['playerRankings', 'suspensions'].includes(currentCompetitionSubtab) && !LEAGUE_COMPETITION_LEVELS.includes(currentCompetitionLevel)) {
        currentCompetitionLevel = '超级';
    }
    syncCompetitionLevelTabs();
    if (currentCompetitionSubtab === 'playerRankings') {
        renderPlayerRankingsBoard();
        if (typeof syncAppHistory === 'function') {
            syncAppHistory('replace');
        }
        return;
    }
    if (currentCompetitionSubtab === 'suspensions') {
        renderSuspensionsBoard();
        if (typeof syncAppHistory === 'function') {
            syncAppHistory('replace');
        }
        return;
    }
    renderCompetitionPrimaryBoard();
    renderScheduleBoard();
    if (typeof syncAppHistory === 'function') {
        syncAppHistory('replace');
    }
}

function syncCompetitionLevelTabs() {
    const hideCupLevels = ['playerRankings', 'suspensions'].includes(currentCompetitionSubtab);
    document.getElementById('competitionLevelSuper')?.classList.toggle('active', currentCompetitionLevel === '超级');
    document.getElementById('competitionLevelFirst')?.classList.toggle('active', currentCompetitionLevel === '甲级');
    document.getElementById('competitionLevelSecond')?.classList.toggle('active', currentCompetitionLevel === '乙级');
    [
        ['competitionLevelChampionsCup', '冠军杯'],
        ['competitionLevelLeagueCup', '联盟杯'],
        ['competitionLevelWumingjianCup', '无铭剑杯'],
    ].forEach(([id, level]) => {
        const button = document.getElementById(id);
        if (!button) return;
        button.classList.toggle('active', currentCompetitionLevel === level);
        button.style.display = hideCupLevels ? 'none' : '';
    });
}

function renderCompetitionAdminActions() {
    const container = document.getElementById('competitionAdminActions');
    if (!container) return;
    const cupConfig = getCurrentCupConfig();
    if (currentCompetitionSubtab === 'suspensions') {
        if (!canManageSuspensions) {
            container.innerHTML = '';
            return;
        }
        container.innerHTML = `
            <button class="btn btn-primary" type="button" onclick="loadCompetitionData({force: true})">刷新</button>
            <button class="btn btn-secondary" type="button" onclick="logoutCurrentWorkAccount()">退出登录</button>
        `;
        return;
    }
    if (!canManageSchedule) {
        container.innerHTML = '';
        return;
    }
    container.innerHTML = `
        ${cupConfig ? `<button class="btn btn-secondary" type="button" onclick="initializeCupBracket()">${escapeHtml(cupConfig.initializeLabel)}</button>` : '<button class="btn btn-secondary" type="button" onclick="importLatestSchedule()">导入最新赛程</button>'}
        <button class="btn btn-primary" type="button" onclick="loadCompetitionData({force: true})">刷新</button>
        <button class="btn btn-secondary" type="button" onclick="logoutCurrentWorkAccount()">退出登录</button>
    `;
}

function groupStandingsByLevel(rows) {
    return rows.reduce((groups, row) => {
        const level = row.level || '未分级';
        if (!groups[level]) groups[level] = [];
        groups[level].push(row);
        return groups;
    }, {});
}

function formatStandingRecord(row, prefix = '') {
    const wins = Number(row[`${prefix}wins`] || 0);
    const draws = Number(row[`${prefix}draws`] || 0);
    const losses = Number(row[`${prefix}losses`] || 0);
    return `${wins}-${draws}-${losses}`;
}

function formatWinRate(row) {
    const value = Number(row.win_rate || 0);
    return `${Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1)}%`;
}

function formatRateValue(value, digits = 0, suffix = '%') {
    const numeric = Number(value || 0);
    const formatted = Number.isInteger(numeric) ? numeric.toFixed(0) : numeric.toFixed(digits);
    return `${formatted}${suffix}`;
}

function formatGoalRate(row) {
    return Number(row.goal_rate || 0).toFixed(2);
}

function getTeamCrestText(teamName) {
    const raw = String(teamName || '').trim();
    if (!raw) return '-';
    const tokens = raw.split(/\s+/).filter(Boolean);
    if (tokens.length >= 2) {
        return `${tokens[0][0] || ''}${tokens[1][0] || ''}`.toUpperCase();
    }
    return raw.slice(0, 2).toUpperCase();
}

function getTeamCrestClass(teamName) {
    const key = normalizeSearchText(teamName || '');
    let sum = 0;
    for (const char of key) sum += char.charCodeAt(0);
    return `crest-tone-${(sum % 6) + 1}`;
}

function getStandingZoneClass(row, levelRows) {
    const rank = Number(row.rank || 0);
    const total = Array.isArray(levelRows) ? levelRows.length : 0;
    if (rank >= 1 && rank <= 5) return 'is-promotion-zone';
    if (total && rank > Math.max(0, total - 5)) return 'is-relegation-zone';
    return '';
}

function setMobileStandingsScope(scope) {
    currentMobileStandingsScope = ['total', 'home', 'away'].includes(scope) ? scope : 'total';
    renderStandingsBoard();
}

function getMobileStandingsScopeMeta(scope = currentMobileStandingsScope) {
    if (scope === 'home') {
        return {
            key: 'home',
            label: '主场',
            played: row => Number(row.home_wins || 0) + Number(row.home_draws || 0) + Number(row.home_losses || 0),
            wins: 'home_wins',
            draws: 'home_draws',
            losses: 'home_losses',
            goalsFor: 'home_goals_for',
            goalsAgainst: 'home_goals_against',
            goalDifference: 'home_goal_difference',
            points: 'home_points',
            rate: row => formatRateValue(row.home_win_rate),
        };
    }
    if (scope === 'away') {
        return {
            key: 'away',
            label: '客场',
            played: row => Number(row.away_wins || 0) + Number(row.away_draws || 0) + Number(row.away_losses || 0),
            wins: 'away_wins',
            draws: 'away_draws',
            losses: 'away_losses',
            goalsFor: 'away_goals_for',
            goalsAgainst: 'away_goals_against',
            goalDifference: 'away_goal_difference',
            points: 'away_points',
            rate: row => formatRateValue(row.away_win_rate),
        };
    }
    return {
        key: 'total',
        label: '总数据',
        played: row => row.played,
        wins: 'wins',
        draws: 'draws',
        losses: 'losses',
        goalsFor: 'goals_for',
        goalsAgainst: 'goals_against',
        goalDifference: 'goal_difference',
        points: 'points',
        rate: row => formatRateValue(row.played ? (Number(row.wins || 0) / Number(row.played || 1)) * 100 : 0),
    };
}

function renderMobileStandingsScopeTabs(level) {
    return `
        <div class="mobile-standings-scope capture-exclude" role="tablist" aria-label="${escapeHtml(level)}积分榜数据范围">
            ${[
                ['total', '总'],
                ['home', '主场'],
                ['away', '客场'],
            ].map(([scope, label]) => `
                <button class="mobile-standings-scope-btn ${currentMobileStandingsScope === scope ? 'is-active' : ''}" type="button" onclick="setMobileStandingsScope('${scope}')" aria-selected="${currentMobileStandingsScope === scope ? 'true' : 'false'}">${label}</button>
            `).join('')}
        </div>
    `;
}

function renderMobileStandingsCards(level, rows) {
    const scope = getMobileStandingsScopeMeta();
    return `
        <div class="mobile-standings-list" aria-label="${escapeHtml(level)}${escapeHtml(scope.label)}积分榜">
            ${rows.map(row => {
                const zoneClass = getStandingZoneClass(row, rows);
                const wins = Number(row[scope.wins] || 0);
                const draws = Number(row[scope.draws] || 0);
                const losses = Number(row[scope.losses] || 0);
                const goalsFor = Number(row[scope.goalsFor] || 0);
                const goalsAgainst = Number(row[scope.goalsAgainst] || 0);
                const goalDifference = Number(row[scope.goalDifference] || 0);
                const points = Number(row[scope.points] || 0);
                return `
                    <article class="mobile-standings-card ${zoneClass}">
                        <div class="mobile-standings-rank">${row.rank}</div>
                        <div class="mobile-standings-team">
                            <button class="player-link mobile-standings-team-name" type="button" onclick="viewTeamPlayers(${htmlJsString(row.team_name || '')})">${escapeHtml(row.team_name || '-')}</button>
                            <div class="mobile-standings-coach">${renderCoachProfileLink(row.manager, 'coach-profile-link standings-coach-link')}</div>
                        </div>
                        <div class="mobile-standings-points">
                            <strong>${points}</strong>
                            <span>积分</span>
                        </div>
                        <div class="mobile-standings-strip">
                            <span><em>场</em>${scope.played(row)}</span>
                            <span><em>胜</em>${wins}</span>
                            <span><em>平</em>${draws}</span>
                            <span><em>负</em>${losses}</span>
                            <span><em>进</em>${goalsFor}</span>
                            <span><em>失</em>${goalsAgainst}</span>
                            <span><em>净</em>${goalDifference}</span>
                            <span><em>胜率</em>${scope.rate(row)}</span>
                        </div>
                    </article>
                `;
            }).join('')}
        </div>
    `;
}

function renderStandingsBoard() {
    const container = document.getElementById('standingsBoard');
    if (!container) return;
    const rows = Array.isArray(standingsData.rows) ? standingsData.rows : [];
    if (!rows.length) {
        container.innerHTML = '<div class="no-data">暂无积分榜数据。导入赛程并录入比分后，这里会自动生成排名。</div>';
        return;
    }

    const grouped = groupStandingsByLevel(rows.filter(row => row.level === currentCompetitionLevel));
    const levels = Object.keys(grouped).sort((a, b) => getCompetitionLevelOrder(a) - getCompetitionLevelOrder(b) || a.localeCompare(b));
    const mobileMode = isMobileViewport();
    container.innerHTML = levels.map(level => `
        <section class="competition-level-section standings-level-section exportable-panel" data-export-view="standings-${escapeHtml(level)}">
            <div class="table-header-row standings-header-row">
                <h2 class="table-title">${escapeHtml(level)}积分榜</h2>
                <div class="competition-header-actions">
                    <div class="standings-zone-legend">
                        <span class="standings-zone-chip promotion">前五升级区</span>
                        <span class="standings-zone-chip relegation">后五降级区</span>
                    </div>
                    <button class="btn btn-secondary competition-image-btn capture-exclude" type="button" onclick="saveCompetitionImage('standings', ${htmlJsString(level)})">保存图片</button>
                </div>
            </div>
            ${mobileMode ? renderMobileStandingsScopeTabs(level) : ''}
            ${mobileMode ? renderMobileStandingsCards(level, grouped[level]) : `
            <div class="table-container competition-table-container standings-table-container">
                <table class="competition-table standings-table" aria-label="${escapeHtml(level)}积分榜">
                    <colgroup>
                        <col class="standings-col-rank">
                        <col class="standings-col-team">
                        <col class="standings-col-coach">
                        <col class="standings-col-total">
                        <col class="standings-col-total">
                        <col class="standings-col-total">
                        <col class="standings-col-total">
                        <col class="standings-col-total">
                        <col class="standings-col-total">
                        <col class="standings-col-total">
                        <col class="standings-col-total">
                        <col class="standings-col-total">
                        <col class="standings-col-split">
                        <col class="standings-col-split">
                        <col class="standings-col-split">
                        <col class="standings-col-split">
                        <col class="standings-col-split">
                        <col class="standings-col-split">
                        <col class="standings-col-split">
                        <col class="standings-col-split">
                        <col class="standings-col-split">
                        <col class="standings-col-split">
                        <col class="standings-col-split">
                        <col class="standings-col-split">
                        <col class="standings-col-split">
                        <col class="standings-col-split">
                        <col class="standings-col-split">
                        <col class="standings-col-split">
                    </colgroup>
                    <thead>
                        <tr>
                            <th class="standings-group-spacer" colspan="3"></th>
                            <th class="standings-group-title" colspan="9">总数据</th>
                            <th class="standings-group-title" colspan="8">主场数据</th>
                            <th class="standings-group-title" colspan="8">客场数据</th>
                        </tr>
                        <tr>
                            <th>排名</th>
                            <th>球队</th>
                            <th class="coach-column">主教练</th>
                            <th>场次</th>
                            <th>胜</th>
                            <th>平</th>
                            <th>负</th>
                            <th>进球</th>
                            <th>失球</th>
                            <th>净胜球</th>
                            <th>积分</th>
                            <th>进球率</th>
                            <th>胜</th>
                            <th>平</th>
                            <th>负</th>
                            <th>进</th>
                            <th>失</th>
                            <th>净</th>
                            <th>积</th>
                            <th>胜率</th>
                            <th>胜</th>
                            <th>平</th>
                            <th>负</th>
                            <th>进</th>
                            <th>失</th>
                            <th>净</th>
                            <th>积</th>
                            <th>胜率</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${grouped[level].map(row => `
                            <tr class="${getStandingZoneClass(row, grouped[level])}">
                                <td class="numeric-cell rank-cell">${row.rank}</td>
                                <td class="team-name-cell standings-team-cell" title="${escapeHtml(row.manager ? `${row.team_name || '-'} / ${row.manager}` : (row.team_name || '-'))}">
                                    <span class="player-link" onclick="viewTeamPlayers(${htmlJsString(row.team_name || '')})">${escapeHtml(row.team_name || '-')}</span>
                                </td>
                                <td class="coach-cell" title="${escapeHtml(row.manager || '-')}">${renderCoachProfileLink(row.manager, 'coach-profile-link standings-coach-link')}</td>
                                <td class="numeric-cell">${row.played}</td>
                                <td class="numeric-cell">${row.wins}</td>
                                <td class="numeric-cell">${row.draws}</td>
                                <td class="numeric-cell">${row.losses}</td>
                                <td class="numeric-cell">${row.goals_for}</td>
                                <td class="numeric-cell">${row.goals_against}</td>
                                <td class="numeric-cell">${row.goal_difference}</td>
                                <td class="numeric-cell points-cell">${row.points}</td>
                                <td class="numeric-cell rate-cell">${formatGoalRate(row)}</td>
                                <td class="numeric-cell">${row.home_wins}</td>
                                <td class="numeric-cell">${row.home_draws}</td>
                                <td class="numeric-cell">${row.home_losses}</td>
                                <td class="numeric-cell">${row.home_goals_for}</td>
                                <td class="numeric-cell">${row.home_goals_against}</td>
                                <td class="numeric-cell">${row.home_goal_difference}</td>
                                <td class="numeric-cell points-cell">${row.home_points}</td>
                                <td class="numeric-cell win-rate-cell">${formatRateValue(row.home_win_rate)}</td>
                                <td class="numeric-cell">${row.away_wins}</td>
                                <td class="numeric-cell">${row.away_draws}</td>
                                <td class="numeric-cell">${row.away_losses}</td>
                                <td class="numeric-cell">${row.away_goals_for}</td>
                                <td class="numeric-cell">${row.away_goals_against}</td>
                                <td class="numeric-cell">${row.away_goal_difference}</td>
                                <td class="numeric-cell points-cell">${row.away_points}</td>
                                <td class="numeric-cell win-rate-cell">${formatRateValue(row.away_win_rate)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            `}
        </section>
    `).join('');
}

function renderCompetitionPrimaryBoard() {
    const standingsContainer = document.getElementById('standingsBoard');
    const cupContainer = document.getElementById('cupBracketBoard');
    if (isCupCompetitionLevel()) {
        if (standingsContainer) standingsContainer.style.display = 'none';
        if (cupContainer) {
            cupContainer.style.display = '';
            renderCupBracketBoard();
        }
        return;
    }
    if (cupContainer) cupContainer.style.display = 'none';
    if (standingsContainer) {
        standingsContainer.style.display = '';
        renderStandingsBoard();
    }
}

function setPlayerRankingType(type) {
    currentPlayerRankingType = ['goals', 'assists', 'mvps'].includes(type) ? type : 'goals';
    document.getElementById('playerRankingGoalsTab')?.classList.toggle('active', currentPlayerRankingType === 'goals');
    document.getElementById('playerRankingAssistsTab')?.classList.toggle('active', currentPlayerRankingType === 'assists');
    document.getElementById('playerRankingMvpsTab')?.classList.toggle('active', currentPlayerRankingType === 'mvps');
    renderPlayerRankingsBoard();
}

function getPlayerRankingRows() {
    const metric = currentPlayerRankingType;
    return (playerRankingData.rows || [])
        .filter(row => row.level === currentCompetitionLevel && Number(row[metric] || 0) > 0)
        .sort((a, b) => {
            const metricDiff = Number(b[metric] || 0) - Number(a[metric] || 0);
            if (metricDiff) return metricDiff;
            const goalsDiff = Number(b.goals || 0) - Number(a.goals || 0);
            if (goalsDiff) return goalsDiff;
            const assistsDiff = Number(b.assists || 0) - Number(a.assists || 0);
            if (assistsDiff) return assistsDiff;
            const mvpsDiff = Number(b.mvps || 0) - Number(a.mvps || 0);
            if (mvpsDiff) return mvpsDiff;
            return String(a.player_name || '').localeCompare(String(b.player_name || ''));
        })
        .map((row, index) => ({...row, rank: index + 1}));
}

function renderPlayerRankingsBoard() {
    const container = document.getElementById('playerRankingsBoard');
    if (!container) return;
    const metricLabel = currentPlayerRankingType === 'assists' ? '助攻' : (currentPlayerRankingType === 'mvps' ? '最佳' : '进球');
    const title = currentPlayerRankingType === 'assists' ? '助攻榜' : (currentPlayerRankingType === 'mvps' ? '最佳球员榜' : '射手榜');
    const rows = getPlayerRankingRows();
    if (!rows.length) {
        container.innerHTML = `
            <section class="player-ranking-panel surface-card">
                <div class="table-header-row standings-header-row">
                    <h2 class="table-title">${escapeHtml(currentCompetitionLevel)}${title}</h2>
                </div>
                <div class="no-data">暂无${escapeHtml(currentCompetitionLevel)}${escapeHtml(title)}数据。当前系统还没有录入对应球员明细。</div>
            </section>
        `;
        return;
    }
    container.innerHTML = `
        <section class="player-ranking-panel surface-card">
            <div class="table-header-row standings-header-row">
                <h2 class="table-title">${escapeHtml(currentCompetitionLevel)}${title}</h2>
            </div>
            ${isMobileViewport() ? renderMobilePlayerRankingCards(rows, metricLabel) : `
            <div class="table-container competition-table-container player-ranking-table-container">
                <table class="competition-table player-ranking-table" aria-label="${escapeHtml(currentCompetitionLevel)}${escapeHtml(title)}">
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>球员</th>
                            <th>球队</th>
                            <th>进球</th>
                            <th>助攻</th>
                            <th>最佳</th>
                            <th>出场</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map(row => `
                            <tr>
                                <td class="numeric-cell rank-cell">${row.rank}</td>
                                <td class="team-name-cell" title="${escapeHtml(row.player_name || '-')}">${escapeHtml(row.player_name || '-')}</td>
                                <td class="team-name-cell" title="${escapeHtml(row.team_name || '-')}">${escapeHtml(row.team_name || '-')}</td>
                                <td class="numeric-cell ${currentPlayerRankingType === 'goals' ? 'points-cell' : ''}">${row.goals || 0}</td>
                                <td class="numeric-cell ${currentPlayerRankingType === 'assists' ? 'points-cell' : ''}">${row.assists || 0}</td>
                                <td class="numeric-cell ${currentPlayerRankingType === 'mvps' ? 'points-cell' : ''}">${row.mvps || 0}</td>
                                <td class="numeric-cell">${row.appearances || 0}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
            `}
        </section>
    `;
}

function renderMobilePlayerRankingCards(rows, metricLabel) {
    return `
        <div class="mobile-player-ranking-list" aria-label="${escapeHtml(currentCompetitionLevel)}${escapeHtml(metricLabel)}榜">
            ${rows.map(row => `
                <article class="mobile-player-ranking-card">
                    <div class="mobile-player-ranking-rank">${Number(row.rank || 0)}</div>
                    <div class="mobile-player-ranking-main">
                        <strong title="${escapeHtml(row.player_name || '-')}">${escapeHtml(row.player_name || '-')}</strong>
                        <button class="player-link mobile-player-ranking-team" type="button" onclick="viewTeamPlayers(${htmlJsString(row.team_name || '')})">${escapeHtml(row.team_name || '-')}</button>
                    </div>
                    <div class="mobile-player-ranking-metric">
                        <strong>${Number(currentPlayerRankingType === 'assists' ? row.assists || 0 : (currentPlayerRankingType === 'mvps' ? row.mvps || 0 : row.goals || 0))}</strong>
                        <span>${escapeHtml(metricLabel)}</span>
                    </div>
                    <div class="mobile-player-ranking-stats">
                        <span><em>进球</em>${Number(row.goals || 0)}</span>
                        <span><em>助攻</em>${Number(row.assists || 0)}</span>
                        <span><em>最佳</em>${Number(row.mvps || 0)}</span>
                        <span><em>出场</em>${Number(row.appearances || 0)}</span>
                    </div>
                </article>
            `).join('')}
        </div>
    `;
}

function getTeamPlayersForSuspension(team) {
    const teamId = Number(team?.team_id || team?.id || 0);
    const teamName = String(team?.team_name || team?.name || '');
    const meta = getScheduleTeamMeta(teamId, teamName);
    const teamNames = new Set([teamName, team?.name, meta?.name, SCHEDULE_TEAM_ALIASES[teamName]].filter(Boolean).map(String));
    const normalizedTeamNames = new Set([...teamNames].map(normalizeScheduleTeamLookupName).filter(Boolean));
    return (allPlayers || [])
        .filter(player => {
            if (teamId && Number(player.team_id || 0) === teamId) return true;
            if (meta?.id && Number(player.team_id || 0) === Number(meta.id)) return true;
            if (teamNames.has(String(player.team_name || ''))) return true;
            return normalizedTeamNames.has(normalizeScheduleTeamLookupName(player.team_name));
        })
        .sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')));
}

function getSuspensionPlayerSuggestions(teamId, query = '') {
    const team = findSuspensionTeam(teamId);
    const raw = String(query || '').trim().toLowerCase();
    const players = getTeamPlayersForSuspension(team);
    if (!raw) return players;
    return players.filter(player => {
        const name = String(player.name || '').toLowerCase();
        const uid = String(player.uid || '');
        return name.includes(raw) || uid.includes(raw);
    });
}

function renderSuspensionSuggestionList(teamId, query = '') {
    const players = getSuspensionPlayerSuggestions(teamId, query);
    if (!players.length) {
        return `
            <div class="suspension-suggestion-empty">
                未匹配到该球队球员，可继续输入完整姓名或 UID。
            </div>
        `;
    }
    return `
        <div class="suspension-suggestion-list" role="listbox">
            ${players.map(player => `
                <button class="suspension-suggestion-option" type="button" role="option" onclick="selectSuspensionSuggestion(this, ${Number(teamId)}, ${Number(player.uid || 0)})">
                    <span class="suspension-suggestion-name">${escapeHtml(player.name || '-')}</span>
                    <span class="suspension-suggestion-meta">${escapeHtml([player.position || '', player.uid ? `UID ${player.uid}` : ''].filter(Boolean).join(' / '))}</span>
                </button>
            `).join('')}
        </div>
    `;
}

function closeSuspensionSuggestions(exceptPanel = null) {
    const panel = document.getElementById('suspensionSuggestionPanel');
    if (panel && panel !== exceptPanel) panel.remove();
    if (panel !== exceptPanel) activeSuspensionSuggestionContext = null;
}

function getSuspensionSuggestionPanel() {
    let panel = document.getElementById('suspensionSuggestionPanel');
    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'suspensionSuggestionPanel';
        panel.className = 'suspension-suggestions suspension-suggestions-floating';
        panel.hidden = true;
        document.body.appendChild(panel);
    }
    return panel;
}

function positionSuspensionSuggestionPanel(input, panel) {
    const rect = input.getBoundingClientRect();
    const fieldRect = input.closest('.suspension-player-field')?.getBoundingClientRect() || rect;
    const panelWidth = Math.min(Math.max(fieldRect.width, 260), window.innerWidth - 24);
    const left = Math.max(12, Math.min(fieldRect.left, window.innerWidth - panelWidth - 12));
    const estimatedHeight = Math.min(360, Math.max(180, window.innerHeight * 0.42));
    const belowTop = rect.bottom + 6;
    const aboveTop = rect.top - estimatedHeight - 6;
    const top = belowTop + estimatedHeight > window.innerHeight - 12 && aboveTop > 12 ? aboveTop : belowTop;
    panel.style.width = `${panelWidth}px`;
    panel.style.left = `${left}px`;
    panel.style.top = `${top}px`;
}

function updateSuspensionSuggestions(input, teamId, forceOpen = false) {
    const panel = getSuspensionSuggestionPanel();
    if (!input || !panel) return;
    panel.innerHTML = renderSuspensionSuggestionList(teamId, input.value);
    const shouldOpen = forceOpen || Boolean(String(input.value || '').trim());
    if (shouldOpen) {
        activeSuspensionSuggestionContext = {teamId: Number(teamId), input};
        positionSuspensionSuggestionPanel(input, panel);
        closeSuspensionSuggestions(panel);
    }
    panel.hidden = !shouldOpen;
}

function toggleSuspensionSuggestions(button, teamId) {
    const field = button?.closest('.suspension-player-field');
    const input = field?.querySelector('.suspension-player-input');
    const panel = getSuspensionSuggestionPanel();
    if (!input || !panel) return;
    const shouldOpen = panel.hidden || Number(activeSuspensionSuggestionContext?.teamId || 0) !== Number(teamId);
    if (shouldOpen) {
        input.focus();
        updateSuspensionSuggestions(input, teamId, true);
    } else {
        closeSuspensionSuggestions();
    }
}

function scheduleCloseSuspensionSuggestions(input) {
    window.setTimeout(() => {
        const panel = document.getElementById('suspensionSuggestionPanel');
        if (!panel) return;
        if (activeSuspensionSuggestionContext?.input && activeSuspensionSuggestionContext.input !== input) return;
        if (!panel.contains(document.activeElement)) closeSuspensionSuggestions();
    }, 120);
}

function handleSuspensionPlayerKeydown(event) {
    if (event.key !== 'Escape') return;
    closeSuspensionSuggestions();
}

function selectSuspensionSuggestion(button, teamId, playerUid) {
    const input = document.getElementById(`suspension-player-${teamId}`) || activeSuspensionSuggestionContext?.input;
    const team = findSuspensionTeam(teamId);
    const player = getTeamPlayersForSuspension(team).find(item => Number(item.uid || 0) === Number(playerUid));
    if (!input || !player) return;
    input.value = player.name || '';
    closeSuspensionSuggestions();
    input.dispatchEvent(new Event('change', {bubbles: true}));
}

function handleSuspensionSuggestionDocumentPointerDown(event) {
    const panel = document.getElementById('suspensionSuggestionPanel');
    if (!panel || panel.hidden) return;
    if (panel.contains(event.target)) return;
    if (event.target?.closest?.('.suspension-player-field')) return;
    closeSuspensionSuggestions();
}

document.addEventListener('pointerdown', handleSuspensionSuggestionDocumentPointerDown, true);

function getSuspensionRecordLabel(record) {
    const labels = [];
    const yellows = Number(record.yellow_cards || 0);
    if (yellows > 0) labels.push(`${yellows}黄`);
    if (record.red_card_suspended) labels.push('红牌');
    if (record.red_injury_suspended) labels.push('红伤');
    return labels.join(' / ') || '记录';
}

function renderSuspensionPlayers(records, emptyText) {
    if (!records || !records.length) {
        return `<span class="suspension-empty" title="${escapeHtml(emptyText)}">-</span>`;
    }
    return records.map(record => `
        <div class="suspension-player-row">
            <div class="suspension-player-main">
                <strong title="${escapeHtml(record.player_name)}">${escapeHtml(record.player_name)}</strong>
                <span>${escapeHtml(getSuspensionRecordLabel(record))}</span>
                ${record.notes ? `<em title="${escapeHtml(record.notes)}">${escapeHtml(record.notes)}</em>` : ''}
            </div>
            ${canManageSuspensions ? `
                <div class="suspension-row-actions">
                    <button type="button" class="suspension-link-btn" onclick="openSuspensionEditor(${Number(record.team_id || 0)}, ${Number(record.player_uid)})">编辑</button>
                    <button type="button" class="suspension-link-btn danger" onclick="clearSuspensionRecord(${Number(record.player_uid)})">清除</button>
                </div>
            ` : ''}
        </div>
    `).join('');
}

function renderSuspensionEditor(team) {
    if (!canManageSuspensions) return '';
    const teamId = Number(team.team_id || 0);
    if (Number(activeSuspensionEditorTeamId || 0) !== teamId) return '';
    return `
        <div class="suspension-editor">
            <div class="suspension-player-field">
                <div class="suspension-player-input-row">
                    <input id="suspension-player-${teamId}" class="suspension-player-input" type="text" placeholder="输入球员名或 UID" autocomplete="off" oninput="updateSuspensionSuggestions(this, ${teamId})" onfocus="updateSuspensionSuggestions(this, ${teamId}, true)" onblur="scheduleCloseSuspensionSuggestions(this)" onkeydown="handleSuspensionPlayerKeydown(event)">
                    <button class="suspension-player-toggle" type="button" title="选择球员" aria-label="选择球员" onclick="toggleSuspensionSuggestions(this, ${teamId})">▾</button>
                </div>
            </div>
            <select id="suspension-yellows-${teamId}" aria-label="黄牌数">
                <option value="0">0黄</option>
                <option value="1">1黄</option>
                <option value="2">2黄</option>
                <option value="3">3黄停赛</option>
            </select>
            <label class="suspension-check"><input id="suspension-red-${teamId}" type="checkbox">红牌</label>
            <label class="suspension-check"><input id="suspension-injury-${teamId}" type="checkbox">红伤</label>
            <input id="suspension-notes-${teamId}" type="text" placeholder="备注">
            <button class="btn btn-primary" type="button" onclick="saveSuspensionRecord(${teamId})">保存</button>
        </div>
    `;
}

function renderSuspensionTeamActions(team) {
    if (!canManageSuspensions) return '';
    const teamId = Number(team.team_id || 0);
    const isOpen = Number(activeSuspensionEditorTeamId || 0) === teamId;
    return `
        <button class="suspension-maintain-btn" type="button" onclick="toggleSuspensionEditor(${teamId})">
            ${isOpen ? '收起' : '维护'}
        </button>
    `;
}

function renderSuspensionNotes(notes) {
    const cleanNotes = (notes || []).filter(Boolean);
    if (!cleanNotes.length) return '';
    return `
        <div class="suspension-notes">
            <strong>备注</strong>
            ${cleanNotes.map(note => `<p title="${escapeHtml(note)}">${escapeHtml(note)}</p>`).join('')}
        </div>
    `;
}

function getSuspensionNoteKey(level) {
    return `competition.suspensions.${String(level || '').trim()}`;
}

function getSuspensionUpdateNote(level) {
    return String(siteNotesData[getSuspensionNoteKey(level)]?.text || '').trim();
}

function renderSuspensionUpdateNote(level) {
    const note = getSuspensionUpdateNote(level);
    const displayText = note || '伤停更新时间待补充';
    return `
        <div class="suspension-update-note">
            <span class="suspension-update-note-text">${escapeHtml(displayText)}</span>
            ${canManageSuspensions ? `
                <div class="suspension-note-editor capture-exclude">
                    <input id="suspension-note-${escapeHtml(level)}" type="text" maxlength="160" value="${escapeHtml(note)}" placeholder="例如：伤停统计更新至第 8 轮赛后">
                    <button class="btn btn-secondary" type="button" onclick="saveSuspensionUpdateNote(${htmlJsString(level)})">保存注释</button>
                </div>
            ` : ''}
        </div>
    `;
}

function renderSuspensionsBoard() {
    closeSuspensionSuggestions();
    const container = document.getElementById('suspensionsBoard');
    if (!container) return;
    const teamsForLevel = (suspensionData.teams || []).filter(team => team.level === currentCompetitionLevel);
    if (!teamsForLevel.length) {
        container.innerHTML = '<div class="no-data">暂无伤停统计数据。</div>';
        return;
    }
    container.innerHTML = `
        <section class="suspension-board exportable-panel" data-export-view="suspensions-${escapeHtml(currentCompetitionLevel)}">
            <div class="table-header-row standings-header-row">
                <div class="competition-title-stack">
                    <h2 class="table-title">${escapeHtml(currentCompetitionLevel)}伤停统计</h2>
                    ${renderSuspensionUpdateNote(currentCompetitionLevel)}
                </div>
                <button class="btn btn-secondary competition-image-btn capture-exclude" type="button" onclick="saveCompetitionImage('suspensions', ${htmlJsString(currentCompetitionLevel)})">保存图片</button>
            </div>
            <div class="suspension-team-grid">
                ${teamsForLevel.map(team => `
                    <article class="suspension-team-card">
                        <header class="suspension-team-head">
                            <div>
                                <h3>${escapeHtml(team.team_name)}</h3>
                                <span>${renderCoachProfileLink(team.manager, 'coach-profile-link suspension-coach-link')}</span>
                            </div>
                            ${renderSuspensionTeamActions(team)}
                        </header>
                        <div class="suspension-columns">
                            <section class="is-one-yellow">
                                <h4>1张黄牌</h4>
                                <div class="suspension-section-list">${renderSuspensionPlayers(team.one_yellow, '暂无')}</div>
                            </section>
                            <section class="is-two-yellows">
                                <h4>2张黄牌</h4>
                                <div class="suspension-section-list">${renderSuspensionPlayers(team.two_yellows, '暂无')}</div>
                            </section>
                            <section class="is-suspended">
                                <h4>停赛</h4>
                                <div class="suspension-section-list">${renderSuspensionPlayers(team.suspended, '暂无')}</div>
                            </section>
                        </div>
                        ${renderSuspensionNotes(team.notes)}
                        ${renderSuspensionEditor(team)}
                    </article>
                `).join('')}
            </div>
        </section>
    `;
}

function toggleSuspensionEditor(teamId) {
    if (!canManageSuspensions) return;
    activeSuspensionEditorTeamId = Number(activeSuspensionEditorTeamId || 0) === Number(teamId) ? null : Number(teamId);
    renderSuspensionsBoard();
}

async function saveSuspensionUpdateNote(level) {
    if (!canManageSuspensions) return;
    const key = getSuspensionNoteKey(level);
    const input = document.getElementById(`suspension-note-${level}`);
    const text = String(input?.value || '').trim();
    const result = await adminJsonRequest(`/api/admin/site-notes/${encodeURIComponent(key)}`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text}),
    });
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('保存失败', escapeHtml(data.detail || data.message || '保存注释失败'));
        return;
    }
    siteNotesData[key] = {...(siteNotesData[key] || {}), key, text};
    renderSuspensionsBoard();
}

function openSuspensionEditor(teamId, playerUid = null) {
    if (!canManageSuspensions) return;
    activeSuspensionEditorTeamId = Number(teamId);
    renderSuspensionsBoard();
    if (playerUid !== null && playerUid !== undefined) {
        fillSuspensionEditor(teamId, playerUid);
    }
}

function findSuspensionTeam(teamId) {
    return (suspensionData.teams || []).find(team => Number(team.team_id) === Number(teamId)) || null;
}

function resolveSuspensionPlayer(teamId) {
    const team = findSuspensionTeam(teamId);
    const raw = String(document.getElementById(`suspension-player-${teamId}`)?.value || '').trim();
    if (!team || !raw) return null;
    const players = getTeamPlayersForSuspension(team);
    const rawLower = raw.toLowerCase();
    const uidMatch = raw.match(/\d{4,}/);
    if (uidMatch) {
        const byUid = players.find(player => String(player.uid || '') === uidMatch[0]);
        if (byUid) return byUid;
    }
    const exact = players.find(player => String(player.name || '').toLowerCase() === rawLower);
    if (exact) return exact;
    const startsWith = players.filter(player => String(player.name || '').toLowerCase().startsWith(rawLower));
    if (startsWith.length === 1) return startsWith[0];
    if (startsWith.length > 1) {
        throw new Error(`“${raw}”匹配到多名球员，请继续输入完整姓名或从候选列表选择。`);
    }
    const fuzzy = players.filter(player => String(player.name || '').toLowerCase().includes(rawLower));
    if (fuzzy.length === 1) return fuzzy[0];
    if (fuzzy.length > 1) {
        throw new Error(`“${raw}”匹配到多名球员，请继续输入完整姓名或从候选列表选择。`);
    }
    return null;
}

async function saveSuspensionPayload(payload) {
    if (!canManageSuspensions) return false;
    const result = await adminJsonRequest('/api/admin/suspensions', {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });
    if (!result) return false;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('保存失败', escapeHtml(data.detail || data.message || '保存伤停记录失败'));
        return false;
    }
    competitionDataLoaded = false;
    await loadCompetitionData({force: true});
    return true;
}

async function saveSuspensionRecord(teamId) {
    if (!canManageSuspensions) return;
    let player = null;
    try {
        player = resolveSuspensionPlayer(teamId);
    } catch (error) {
        showModal('保存失败', escapeHtml(error.message || '请先从该球队中选择球员。'));
        return;
    }
    if (!player) {
        showModal('保存失败', '请先从该球队中选择球员。');
        return;
    }
    await saveSuspensionPayload({
        player_uid: Number(player.uid),
        yellow_cards: Number(document.getElementById(`suspension-yellows-${teamId}`)?.value || 0),
        red_card_suspended: Boolean(document.getElementById(`suspension-red-${teamId}`)?.checked),
        red_injury_suspended: Boolean(document.getElementById(`suspension-injury-${teamId}`)?.checked),
        notes: String(document.getElementById(`suspension-notes-${teamId}`)?.value || '').trim(),
    });
}

function fillSuspensionEditor(teamId, playerUid) {
    const team = findSuspensionTeam(teamId);
    const records = [...(team?.one_yellow || []), ...(team?.two_yellows || []), ...(team?.suspended || [])];
    const record = records.find(item => Number(item.player_uid) === Number(playerUid));
    if (!team || !record) return;
    const playerInput = document.getElementById(`suspension-player-${teamId}`);
    const yellowInput = document.getElementById(`suspension-yellows-${teamId}`);
    const redInput = document.getElementById(`suspension-red-${teamId}`);
    const injuryInput = document.getElementById(`suspension-injury-${teamId}`);
    const notesInput = document.getElementById(`suspension-notes-${teamId}`);
    if (playerInput) playerInput.value = record.player_name;
    if (yellowInput) yellowInput.value = String(Math.min(3, Number(record.yellow_cards || 0)));
    if (redInput) redInput.checked = Boolean(record.red_card_suspended);
    if (injuryInput) injuryInput.checked = Boolean(record.red_injury_suspended);
    if (notesInput) notesInput.value = record.notes || '';
}

async function clearSuspensionRecord(playerUid) {
    if (!canManageSuspensions) return;
    await saveSuspensionPayload({
        player_uid: Number(playerUid),
        yellow_cards: 0,
        red_card_suspended: false,
        red_injury_suspended: false,
        notes: '',
    });
}

function getTeamOptionsHtml(selectedId) {
    const selected = Number(selectedId || 0);
    return '<option value="">待定</option>' + (teams || [])
        .map(team => `<option value="${team.id}" ${Number(team.id) === selected ? 'selected' : ''}>${escapeHtml(team.name)}${team.manager ? ` / ${escapeHtml(team.manager)}` : ''}</option>`)
        .join('');
}

function formatCupScore(match) {
    if (match.home_score === null || match.home_score === undefined || match.away_score === null || match.away_score === undefined) {
        return '-';
    }
    return `${match.home_score} - ${match.away_score}`;
}

function findCupMatchById(matchId) {
    for (const bracket of Object.values(cupBracketData || {})) {
        for (const stage of bracket?.stages || []) {
            const found = (stage.matches || []).find(match => Number(match.id) === Number(matchId));
            if (found) return found;
        }
    }
    return null;
}

function isTwoLegCupStage(match) {
    if (!match) return false;
    if (match.competition === 'champions_cup' || match.competition === 'league_cup') return true;
    return match.competition === 'wumingjian_cup' && ['semi_final', 'final'].includes(match.stage);
}

function promptCupTieWinner(match) {
    const homeName = getCupTeamDisplayName(match?.home_team_name || '上方球队');
    const awayName = getCupTeamDisplayName(match?.away_team_name || '下方球队');
    const reason = isTwoLegCupStage(match) ? '两回合总比分相同，请按客场进球更多选择晋级球队。' : '比分相同，请选择晋级球队。';
    const answer = window.prompt(`${reason}\n输入 1：${homeName}\n输入 2：${awayName}`);
    if (answer === null) return null;
    const normalized = String(answer).trim();
    if (normalized === '1') return Number(match.home_team_id);
    if (normalized === '2') return Number(match.away_team_id);
    showModal('保存失败', '请输入 1 或 2 选择晋级球队。');
    return null;
}

function renderCupTeamLine(match, side) {
    const teamId = match[`${side}_team_id`];
    const teamName = match[`${side}_team_name`] || '待定';
    const displayName = getCupTeamDisplayName(teamName);
    const advancement = match[`${side}_advancement`] || (
        match.winner_team_id && Number(match.winner_team_id) === Number(teamId) ? 'winner' : 'pending'
    );
    const stateClass = advancement === 'winner'
        ? 'is-winner'
        : advancement === 'eliminated'
            ? 'is-eliminated'
            : 'is-pending';
    const stateLabel = advancement === 'winner' ? '晋级' : advancement === 'eliminated' ? '淘汰' : '';
    return `
        <div class="cup-team-line ${stateClass}">
            <span class="cup-team-name" title="${escapeHtml(teamName)}">${escapeHtml(displayName)}</span>
            <span class="cup-team-result">
                ${stateLabel ? `<span class="cup-team-state">${stateLabel}</span>` : ''}
                <span class="cup-team-score">${match[`${side}_score`] ?? ''}</span>
            </span>
        </div>
    `;
}

function buildCupTeamEditor(match) {
    const cupConfig = getCurrentCupConfig();
    const firstStage = cupConfig ? cupBracketData[cupConfig.key]?.stages?.[0]?.key : '';
    if (!canManageSchedule || match.stage !== firstStage) return '';
    return `
        <div class="cup-editor cup-team-editor">
            <select id="cup-home-team-${match.id}" aria-label="主队">${getTeamOptionsHtml(match.home_team_id)}</select>
            <select id="cup-away-team-${match.id}" aria-label="客队">${getTeamOptionsHtml(match.away_team_id)}</select>
            <button class="btn btn-secondary" type="button" onclick="saveCupMatchTeams(${match.id})">保存球队</button>
        </div>
    `;
}

function buildCupResultEditor(match) {
    if (!canManageSchedule) return '';
    const homeScore = match.home_score ?? '';
    const awayScore = match.away_score ?? '';
    const status = match.status || 'scheduled';
    return `
        <div class="cup-editor cup-result-editor">
            <input type="number" min="0" id="cup-home-score-${match.id}" value="${escapeHtml(homeScore)}" aria-label="主队进球">
            <span>-</span>
            <input type="number" min="0" id="cup-away-score-${match.id}" value="${escapeHtml(awayScore)}" aria-label="客队进球">
            <select id="cup-status-${match.id}" aria-label="比赛状态">
                <option value="scheduled" ${status === 'scheduled' ? 'selected' : ''}>未赛</option>
                <option value="played" ${status === 'played' ? 'selected' : ''}>已赛</option>
            </select>
            <button class="btn btn-primary" type="button" onclick="saveCupMatchResult(${match.id})">保存比分</button>
        </div>
    `;
}

function renderCupMatchCard(match) {
    return `
        <article class="cup-match-card ${match.status === 'played' ? 'is-played' : ''}">
            <div class="cup-match-slot">#${match.slot_no}</div>
            <div class="cup-match-teams">
                ${renderCupTeamLine(match, 'home')}
                ${renderCupTeamLine(match, 'away')}
            </div>
            <div class="cup-match-meta">
                <span>${escapeHtml(formatCupScore(match))}</span>
                <span>${match.status === 'played' ? '已赛' : '未赛'}</span>
            </div>
            ${match.notes ? `<div class="cup-match-note">${escapeHtml(match.notes)}</div>` : ''}
            ${buildCupTeamEditor(match)}
            ${buildCupResultEditor(match)}
        </article>
    `;
}

function getCupStage(bracket, key) {
    return (bracket.stages || []).find(stage => stage.key === key) || {key, label: '', matches: []};
}

function renderCupStageGroup(stage, matches, side = '') {
    return `
        <section class="cup-stage-column ${side ? `is-${escapeHtml(side)}` : ''}">
            <h3>${escapeHtml(stage.label)}</h3>
            <div class="cup-stage-matches">
                ${(matches || []).map(renderCupMatchCard).join('')}
            </div>
        </section>
    `;
}

function renderCupBracketBoard() {
    const container = document.getElementById('cupBracketBoard');
    if (!container) return;
    const cupConfig = getCurrentCupConfig();
    if (!cupConfig) {
        container.innerHTML = '';
        return;
    }
    const bracket = cupBracketData[cupConfig.key];
    if (!bracket) {
        container.innerHTML = '<div class="loading">加载中...</div>';
        return;
    }
    const finalStage = getCupStage(bracket, 'final');
    const finalMatch = finalStage?.matches?.[0] || {};
    const sideStages = (bracket.stages || []).filter(stage => stage.key !== 'final');
    const leftGroups = sideStages.map(stage => ({
        stage,
        matches: (stage.matches || []).slice(0, Math.ceil((stage.matches || []).length / 2)),
    }));
    const rightGroups = [...sideStages].reverse().map(stage => ({
        stage,
        matches: (stage.matches || []).slice(Math.ceil((stage.matches || []).length / 2)),
    }));
    container.innerHTML = `
        <section class="cup-bracket-shell ${escapeHtml(cupConfig.className)}">
            <div class="cup-hero surface-card">
                <div class="cup-hero-copy">
                    <h2>${escapeHtml(bracket.title)}</h2>
                    <p>${escapeHtml(cupConfig.englishName)}</p>
                </div>
            </div>
            <div class="cup-bracket-grid cup-bracket-symmetric" style="--cup-side-stage-count:${leftGroups.length};">
                ${leftGroups.map(group => renderCupStageGroup(group.stage, group.matches, 'left')).join('')}
                <section class="cup-final-column">
                    <div class="cup-final-trophy">
                        <img class="cup-trophy" src="${escapeHtml(bracket.trophy_url)}" alt="${escapeHtml(bracket.title)}奖杯">
                        <div class="cup-champion-box">
                            <span>冠军</span>
                            <strong title="${escapeHtml(finalMatch.winner_team_name || '待定')}">${escapeHtml(getCupTeamDisplayName(finalMatch.winner_team_name || '待定'))}</strong>
                        </div>
                    </div>
                    ${renderCupStageGroup(finalStage, finalStage.matches || [], 'center')}
                </section>
                ${rightGroups.map(group => renderCupStageGroup(group.stage, group.matches, 'right')).join('')}
            </div>
        </section>
    `;
}

function populateScheduleFilters() {
    const roundSelect = document.getElementById('scheduleRoundSelect');
    if (!roundSelect) return;
    const filters = roundSelect.closest('.search-section');
    if (filters) filters.style.display = 'none';
    if (isCupCompetitionLevel()) {
        roundSelect.innerHTML = '<option value="">杯赛无联赛轮次</option>';
        return;
    }
    const selectedRound = roundSelect.value;
    const rounds = [...new Set((scheduleData.matches || [])
        .filter(match => match.level === currentCompetitionLevel)
        .map(match => Number(match.round_no))
        .filter(Boolean))]
        .sort((a, b) => a - b);
    roundSelect.innerHTML = rounds
        .map(roundNo => `<option value="${roundNo}">第 ${roundNo} 轮</option>`)
        .join('');
    roundSelect.value = rounds.includes(Number(selectedRound)) ? selectedRound : String(rounds[0] || '');
}

function getFilteredScheduleMatches() {
    if (isCupCompetitionLevel()) return [];
    const selectedRound = Number(document.getElementById('scheduleRoundSelect')?.value || 0);
    return (scheduleData.matches || []).filter(match => {
        if (match.level !== currentCompetitionLevel) return false;
        if (selectedRound && Number(match.round_no) !== selectedRound) return false;
        return true;
    });
}

function getScheduleRoundsForCurrentLevel() {
    return [...new Set((scheduleData.matches || [])
        .filter(match => match.level === currentCompetitionLevel)
        .map(match => Number(match.round_no))
        .filter(Boolean))]
        .sort((a, b) => a - b);
}

function getCurrentScheduleRound() {
    const rounds = getScheduleRoundsForCurrentLevel();
    const selectedRound = Number(document.getElementById('scheduleRoundSelect')?.value || 0);
    return rounds.includes(selectedRound) ? selectedRound : (rounds[0] || 0);
}

function stepScheduleRound(direction) {
    const rounds = getScheduleRoundsForCurrentLevel();
    if (!rounds.length) return;
    const currentRound = getCurrentScheduleRound();
    const currentIndex = Math.max(0, rounds.indexOf(currentRound));
    const nextIndex = Math.max(0, Math.min(rounds.length - 1, currentIndex + Number(direction || 0)));
    const roundSelect = document.getElementById('scheduleRoundSelect');
    if (roundSelect) roundSelect.value = String(rounds[nextIndex]);
    renderScheduleBoard();
}

function setScheduleRound(roundNo) {
    const targetRound = Number(roundNo || 0);
    const rounds = getScheduleRoundsForCurrentLevel();
    if (!rounds.includes(targetRound)) return;
    const roundSelect = document.getElementById('scheduleRoundSelect');
    if (roundSelect) roundSelect.value = String(targetRound);
    renderScheduleBoard();
}

function getRoundPairStart(roundNo) {
    const numericRound = Number(roundNo) || 0;
    if (numericRound <= 0) return 0;
    return numericRound % 2 === 1 ? numericRound : numericRound - 1;
}

function buildRoundPairs(rounds) {
    const pairsByStart = new Map();
    for (const roundNo of rounds) {
        const pairStart = getRoundPairStart(roundNo);
        if (!pairStart) continue;
        if (!pairsByStart.has(pairStart)) pairsByStart.set(pairStart, []);
        pairsByStart.get(pairStart).push(roundNo);
    }
    return [...pairsByStart.entries()]
        .sort(([a], [b]) => a - b)
        .map(([pairStart, pairRounds]) => {
            const sortedRounds = [...new Set(pairRounds)].sort((a, b) => a - b);
            return {
                key: sortedRounds.join('-'),
                pairStart,
                rounds: sortedRounds,
            };
        });
}

function parseRoundPairKey(key) {
    return String(key || '')
        .split('-')
        .map(item => Number(item))
        .filter(Boolean);
}

function formatRoundPairLabel(rounds) {
    const sortedRounds = [...new Set((rounds || []).map(Number).filter(Boolean))].sort((a, b) => a - b);
    if (!sortedRounds.length) return '未知轮次';
    if (sortedRounds.length === 1) return `第 ${sortedRounds[0]} 轮`;
    return `第 ${sortedRounds[0]}-${sortedRounds[sortedRounds.length - 1]} 轮`;
}

function normalizeScheduleTeamLookupName(name) {
    return String(name || '')
        .toLowerCase()
        .replace(/&/g, 'and')
        .replace(/\b(fc|cf|club|football|futebol|sport|sporting|association|associazione|olympique|de|of|the)\b/g, '')
        .replace(/[^a-z0-9]+/g, '')
        .trim();
}

function getScheduleTeamMeta(teamId, teamName) {
    const numericId = Number(teamId || 0);
    const rawName = String(teamName || '');
    const aliasName = SCHEDULE_TEAM_ALIASES[rawName] || rawName;
    const normalizedRaw = normalizeScheduleTeamLookupName(rawName);
    const normalizedAlias = normalizeScheduleTeamLookupName(aliasName);
    return (teams || []).find(team => numericId && Number(team.id || 0) === numericId)
        || (teams || []).find(team => String(team.name || '') === rawName)
        || (teams || []).find(team => String(team.name || '') === aliasName)
        || (teams || []).find(team => {
            const normalizedTeam = normalizeScheduleTeamLookupName(team.name);
            return normalizedTeam === normalizedRaw || normalizedTeam === normalizedAlias;
        })
        || {id: numericId || null, name: teamName || '-', logo_path: ''};
}

function getScheduleTeamInitials(teamName) {
    const words = String(teamName || '-').match(/[A-Za-z0-9]+/g) || [];
    if (words.length >= 2) return `${words[0][0]}${words[1][0]}`.toUpperCase();
    return String(teamName || '-').slice(0, 2).toUpperCase();
}

function renderScheduleTeamSide(match, side) {
    const isHome = side === 'home';
    const teamId = isHome ? match.home_team_id : match.away_team_id;
    const teamName = isHome ? match.home_team_name : match.away_team_name;
    const team = getScheduleTeamMeta(teamId, teamName);
    const crest = team.logo_path
        ? `<img src="${escapeHtml(team.logo_path)}" alt="${escapeHtml(teamName || '-')}队徽">`
        : `<span>${escapeHtml(getScheduleTeamInitials(teamName))}</span>`;
    return `
        <div class="schedule-match-team schedule-match-team-${isHome ? 'home' : 'away'}">
            ${isHome ? `<div class="schedule-team-crest ${team.logo_path ? 'has-logo' : ''}">${crest}</div>` : ''}
            <button class="schedule-team-name" type="button" onclick="viewTeamPlayers(${htmlJsString(team.name || teamName || '')})" title="${escapeHtml(team.name || teamName || '-')}">${escapeHtml(teamName || '-')}</button>
            ${!isHome ? `<div class="schedule-team-crest ${team.logo_path ? 'has-logo' : ''}">${crest}</div>` : ''}
        </div>
    `;
}

function isScheduleMatchPlayed(match) {
    return (match?.status === 'played' || isScheduleForfeitStatus(match?.status))
        && match.home_score !== null
        && match.home_score !== undefined
        && match.away_score !== null
        && match.away_score !== undefined;
}

function getScheduleMatchScoreText(match) {
    return isScheduleMatchPlayed(match)
        ? `${Number(match.home_score)} - ${Number(match.away_score)}`
        : formatMatchScore(match);
}

function renderScheduleMobileTeam(match, side) {
    const isHome = side === 'home';
    const teamId = isHome ? match.home_team_id : match.away_team_id;
    const teamName = isHome ? match.home_team_name : match.away_team_name;
    const team = getScheduleTeamMeta(teamId, teamName);
    const crest = team.logo_path
        ? `<img src="${escapeHtml(team.logo_path)}" alt="${escapeHtml(teamName || '-')}队徽">`
        : `<span>${escapeHtml(getScheduleTeamInitials(teamName))}</span>`;
    return `
        <button class="mobile-schedule-team mobile-schedule-team-${side}" type="button" onclick="viewTeamPlayers(${htmlJsString(team.name || teamName || '')})" title="${escapeHtml(team.name || teamName || '-')}">
            <span class="mobile-schedule-crest ${team.logo_path ? 'has-logo' : ''}">${crest}</span>
            <span class="mobile-schedule-team-copy">
                <span class="mobile-schedule-team-role">${isHome ? '主队' : '客队'}</span>
                <strong>${escapeHtml(teamName || '-')}</strong>
            </span>
        </button>
    `;
}

function scheduleEventBelongsToSide(match, event, side) {
    const teamName = side === 'home' ? match.home_team_name : match.away_team_name;
    const teamId = side === 'home' ? match.home_team_id : match.away_team_id;
    return String(event.team_name || '') === String(teamName || '')
        || (teamId && Number(event.team_id || 0) === Number(teamId));
}

function getScheduleEventRows(match, type, side) {
    const events = (match.events || []).filter(event => event.event_type === type && scheduleEventBelongsToSide(match, event, side));
    if (!events.length) return '';
    const icon = type === 'assist' ? '👟' : '⚽';
    const label = type === 'assist' ? '助攻' : '进球';
    const groupedEvents = [];
    for (const event of events) {
        const playerUid = Number(event.player_uid || 0);
        const existing = groupedEvents.find(item => (
            playerUid && Number(item.player_uid || 0) === playerUid
        ) || (
            !playerUid && String(item.player_name || '') === String(event.player_name || '')
        ));
        if (existing) {
            existing.quantity = Number(existing.quantity || 0) + Number(event.quantity || 1);
        } else {
            groupedEvents.push({...event, quantity: Number(event.quantity || 1)});
        }
    }
    return `
        <div class="schedule-event-line">
            <span class="schedule-event-icon" aria-hidden="true">${icon}</span>
            <span>${label}</span>
            <span class="schedule-event-players">
                ${groupedEvents.map(event => `
                    <button class="schedule-event-player" type="button" onclick="showPlayerDetail(${Number(event.player_uid || 0)}, {returnTab: 'competition', returnSubtab: 'schedule'})">
                        ${escapeHtml(event.player_name || '-')}${Number(event.quantity || 1) > 1 ? `（${Number(event.quantity)}）` : ''}
                    </button>
                `).join('')}
            </span>
        </div>
    `;
}

function renderScheduleMvpLine(match) {
    const events = (match.events || []).filter(event => event.event_type === 'mvp');
    if (!events.length) {
        return `
            <div class="schedule-event-line schedule-event-muted">
                <span class="schedule-event-icon" aria-hidden="true">★</span>
                <span>本场最佳</span>
                <span class="schedule-event-placeholder">待评选</span>
            </div>
        `;
    }
    return `
        <div class="schedule-event-line schedule-event-mvp-line">
            <span class="schedule-event-icon" aria-hidden="true">★</span>
            <span>本场最佳</span>
            <span class="schedule-event-players">
                ${events.map(event => `
                    <button class="schedule-event-player" type="button" onclick="showPlayerDetail(${Number(event.player_uid || 0)}, {returnTab: 'competition', returnSubtab: 'schedule'})">
                        ${escapeHtml(event.player_name || '-')}
                    </button>
                `).join('')}
            </span>
        </div>
    `;
}

function renderScheduleTeamEventPanel(match, side) {
    const teamName = side === 'home' ? match.home_team_name : match.away_team_name;
    const goalLine = getScheduleEventRows(match, 'goal', side);
    const assistLine = getScheduleEventRows(match, 'assist', side);
    return `
        <div class="schedule-event-team-panel schedule-event-team-${side}">
            <div class="schedule-event-team-label">${escapeHtml(teamName || '-')}</div>
            ${goalLine || '<div class="schedule-event-empty">暂无进球</div>'}
            ${assistLine || '<div class="schedule-event-empty">暂无助攻</div>'}
        </div>
    `;
}

function renderScheduleMatchEvents(match) {
    return `
        <div class="schedule-match-events">
            <div class="schedule-event-sides">
                ${renderScheduleTeamEventPanel(match, 'home')}
                ${renderScheduleTeamEventPanel(match, 'away')}
            </div>
            <div class="schedule-event-mvp">${renderScheduleMvpLine(match)}</div>
        </div>
    `;
}

function renderScheduleRoundNavigator(rounds, currentRound, matches) {
    const currentIndex = rounds.indexOf(currentRound);
    const playedCount = matches.filter(isScheduleMatchPlayed).length;
    const isRoundComplete = Boolean(matches.length && playedCount === matches.length);
    return `
        <div class="schedule-round-nav">
            <button class="schedule-round-arrow" type="button" onclick="stepScheduleRound(-1)" ${currentIndex <= 0 ? 'disabled' : ''} aria-label="上一轮">‹</button>
            <div class="schedule-round-chip ${isRoundComplete ? 'is-complete' : ''}">
                <span>第 ${Number(currentRound) || '-'} 轮</span>
                <span class="schedule-round-check" aria-hidden="true">✓</span>
                <select class="schedule-round-direct-select" aria-label="选择赛程轮次" onchange="setScheduleRound(this.value)">
                    ${rounds.map(roundNo => `<option value="${Number(roundNo)}" ${Number(roundNo) === Number(currentRound) ? 'selected' : ''}>第 ${Number(roundNo)} 轮</option>`).join('')}
                </select>
            </div>
            <button class="schedule-round-arrow" type="button" onclick="stepScheduleRound(1)" ${currentIndex >= rounds.length - 1 ? 'disabled' : ''} aria-label="下一轮">›</button>
        </div>
    `;
}

function renderScheduleMatchRow(match, options = {}) {
    const played = isScheduleMatchPlayed(match);
    const score = getScheduleMatchScoreText(match);
    const includeAdmin = options.includeAdmin !== false;
    const statusToneClass = getScheduleStatusTone(match.status);
    return `
        <article class="schedule-match-row ${played ? 'is-played' : 'is-pending'}">
            ${renderScheduleTeamSide(match, 'home')}
            <div class="schedule-match-center">
                <div class="schedule-score-block">
                    <div class="schedule-score-status ${statusToneClass}">
                        <span class="schedule-status-check" aria-hidden="true">${played ? '✓' : '•'}</span>
                        <span>${escapeHtml(getMatchStatusLabel(match.status))}</span>
                    </div>
                    <strong class="schedule-score">${escapeHtml(score)}</strong>
                </div>
                ${renderScheduleMatchEvents(match)}
                ${canManageSchedule && includeAdmin ? `<div class="schedule-match-admin">${buildAdminMatchControlGroup(match)}</div>` : ''}
            </div>
            ${renderScheduleTeamSide(match, 'away')}
        </article>
    `;
}

function findScheduleMatchById(matchId) {
    return (scheduleData.matches || []).find(match => Number(match.id) === Number(matchId)) || null;
}

function getMatchTeamOptions(match) {
    return [
        {team_id: Number(match?.home_team_id || 0) || null, match_team_name: String(match?.home_team_name || '')},
        {team_id: Number(match?.away_team_id || 0) || null, match_team_name: String(match?.away_team_name || '')},
    ].filter(team => team.match_team_name).map(team => {
        const meta = getScheduleTeamMeta(team.team_id, team.match_team_name);
        return {
            team_id: Number(meta.id || team.team_id || 0) || null,
            team_name: String(meta.name || team.match_team_name || ''),
            match_team_name: team.match_team_name,
        };
    });
}

function matchTeamOptionMatchesEvent(team, event = {}) {
    const eventTeamId = Number(event.team_id || 0);
    const eventTeamName = String(event.team_name || '');
    return Boolean(
        (eventTeamId && Number(team.team_id || 0) === eventTeamId) ||
        eventTeamName === team.team_name ||
        eventTeamName === team.match_team_name
    );
}

function getMatchTeamPlayers(match, teamName) {
    const team = getMatchTeamOptions(match).find(item => item.team_name === teamName || item.match_team_name === teamName);
    const teamId = Number(team?.team_id || 0);
    const meta = getScheduleTeamMeta(teamId, teamName);
    const teamNames = new Set([teamName, team?.team_name, team?.match_team_name, meta?.name, SCHEDULE_TEAM_ALIASES[teamName]].filter(Boolean).map(String));
    const normalizedTeamNames = new Set([...teamNames].map(normalizeScheduleTeamLookupName).filter(Boolean));
    const cacheKey = `${teamId || 0}|${[...teamNames].sort().join('|')}|${[...normalizedTeamNames].sort().join('|')}|${(allPlayers || []).length}`;
    if (matchTeamPlayerCache.has(cacheKey)) return matchTeamPlayerCache.get(cacheKey);
    const players = (allPlayers || [])
        .filter(player => {
            if (teamId && Number(player.team_id || 0) === teamId) return true;
            if (meta?.id && Number(player.team_id || 0) === Number(meta.id)) return true;
            if (teamNames.has(String(player.team_name || ''))) return true;
            return normalizedTeamNames.has(normalizeScheduleTeamLookupName(player.team_name));
        })
        .sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')));
    matchTeamPlayerCache.set(cacheKey, players);
    return players;
}

function findMatchEventPlayer(match, teamName, inputValue) {
    const raw = String(inputValue || '').trim();
    if (!raw) return null;
    const players = getMatchTeamPlayers(match, teamName);
    const uidMatch = raw.match(/\d{4,}/);
    if (uidMatch) {
        const uid = Number(uidMatch[0]);
        const byUid = players.find(player => Number(player.uid || 0) === uid);
        if (byUid) return byUid;
    }
    const exact = players.find(player => String(player.name || '').trim() === raw);
    if (exact) return exact;
    const lowered = raw.toLowerCase();
    const fuzzy = players.filter(player => String(player.name || '').toLowerCase().includes(lowered));
    if (fuzzy.length === 1) return fuzzy[0];
    if (fuzzy.length > 1) {
        throw new Error(`“${raw}”匹配到多名球员，请继续输入完整姓名或选择建议项。`);
    }
    return null;
}

function getMatchEventPlayerSuggestions(match, teamName, query = '') {
    const raw = String(query || '').trim().toLowerCase();
    const players = getMatchTeamPlayers(match, teamName);
    const matched = raw
        ? players.filter(player => {
            const name = String(player.name || '').toLowerCase();
            const uid = String(player.uid || '');
            return name.includes(raw) || uid.includes(raw);
        })
        : players;
    return matched;
}

function renderMatchEventPlayerDatalist(match, teamName, listId) {
    const players = getMatchTeamPlayers(match, teamName);
    return `
        <datalist id="${escapeHtml(listId)}">
            ${players.map(player => `
                <option value="${escapeHtml(player.name || '')}" label="${escapeHtml([player.position || '', player.uid || ''].filter(Boolean).join(' / '))}"></option>
            `).join('')}
        </datalist>
    `;
}

function renderMatchEventPlayerSelectOptions(match, teamName) {
    const players = getMatchTeamPlayers(match, teamName);
    if (!players.length) return '<option value="">无可选球员</option>';
    return `
        <option value=""></option>
        ${players.map(player => `
            <option value="${Number(player.uid || 0)}">${escapeHtml(player.name || '-')}${player.position ? ` / ${escapeHtml(player.position)}` : ''}</option>
        `).join('')}
    `;
}

function renderMatchEventRow(match, event = {}, options = {}) {
    const teams = getMatchTeamOptions(match);
    const selectedTeam = (teams.find(team => matchTeamOptionMatchesEvent(team, event)) || teams[0])?.team_name || '';
    const isMvp = options.mode === 'mvp' || event.event_type === 'mvp';
    const selectedType = isMvp ? 'mvp' : (event.event_type === 'assist' ? 'assist' : 'goal');
    const quantity = Math.max(1, Number(event.quantity || 1));
    const selectedPlayerName = event.player_name || '';
    return `
        <div class="match-event-row ${isMvp ? 'match-mvp-row' : ''}" data-match-event-row>
            <select class="match-event-team" onchange="refreshMatchEventPlayerInput(this, ${Number(match.id)})" aria-label="事件球队">
                ${teams.map(team => `<option value="${escapeHtml(team.team_name)}" data-team-id="${Number(team.team_id || 0)}" data-match-team-name="${escapeHtml(team.match_team_name)}" ${team.team_name === selectedTeam ? 'selected' : ''}>${escapeHtml(team.match_team_name || team.team_name)}</option>`).join('')}
            </select>
            <div class="match-event-player-field">
                <div class="match-event-player-input-row">
                    <input class="match-event-player" type="text" value="${escapeHtml(selectedPlayerName)}" placeholder="${isMvp ? '输入或选择本场最佳' : '输入或选择球员'}" aria-label="${isMvp ? '本场最佳球员' : '事件球员'}" autocomplete="off" oninput="updateMatchEventSuggestions(this, ${Number(match.id)}); scheduleMatchAutoSave(${Number(match.id)})" onchange="scheduleMatchAutoSave(${Number(match.id)})" onfocus="updateMatchEventSuggestions(this, ${Number(match.id)}, true)" onblur="scheduleCloseMatchEventSuggestions(this)" onkeydown="handleMatchEventPlayerKeydown(event, this)">
                    <button class="match-event-player-select" type="button" title="选择球员" aria-label="选择球员" onclick="toggleMatchEventSuggestions(this, ${Number(match.id)})">▾</button>
                </div>
            </div>
            ${isMvp ? `
                <input class="match-event-type" type="hidden" value="mvp">
                <input class="match-event-quantity" type="hidden" value="1">
                <button class="match-event-remove match-mvp-clear" type="button" onclick="clearMatchEventRow(this)" aria-label="清空本场最佳">清空</button>
            ` : `
                <select class="match-event-type" aria-label="事件类型" onchange="scheduleMatchAutoSave(${Number(match.id)})">
                    <option value="goal" ${selectedType === 'goal' ? 'selected' : ''}>进球</option>
                    <option value="assist" ${selectedType === 'assist' ? 'selected' : ''}>助攻</option>
                </select>
                <input class="match-event-quantity" type="number" min="1" value="${quantity}" aria-label="事件数量" oninput="scheduleMatchAutoSave(${Number(match.id)})" onchange="scheduleMatchAutoSave(${Number(match.id)})">
                <button class="match-event-remove" type="button" onclick="removeMatchEventRow(this)" aria-label="删除明细">×</button>
            `}
        </div>
    `;
}

function renderMatchEventEditor(match) {
    const events = Array.isArray(match.events) ? match.events : [];
    const scorerEvents = events.filter(event => event.event_type !== 'mvp');
    const mvpEvent = events.find(event => event.event_type === 'mvp') || {event_type: 'mvp'};
    return `
        <div class="match-event-editor" id="match-events-${match.id}">
            <div class="match-event-head">
                <span>进球 / 助攻明细</span>
                <button type="button" class="match-event-add" onclick="addMatchEventRow(${Number(match.id)})">添加</button>
            </div>
            <div class="match-event-list">
                ${scorerEvents.map(event => renderMatchEventRow(match, event)).join('')}
            </div>
            <div class="match-mvp-editor">
                <div class="match-event-head">
                    <span>本场最佳</span>
                </div>
                ${renderMatchEventRow(match, mvpEvent, {mode: 'mvp'})}
            </div>
        </div>
    `;
}

function addMatchEventRow(matchId) {
    const match = findScheduleMatchById(matchId);
    const list = document.querySelector(`#match-events-${matchId} .match-event-list`);
    if (!match || !list) return;
    list.insertAdjacentHTML('beforeend', renderMatchEventRow(match));
    scheduleMatchAutoSave(matchId);
}

function removeMatchEventRow(button) {
    const matchId = Number(button?.closest('.match-event-editor')?.id?.replace('match-events-', '') || 0);
    button?.closest('[data-match-event-row]')?.remove();
    if (matchId) scheduleMatchAutoSave(matchId);
}

function clearMatchEventRow(button) {
    const matchId = Number(button?.closest('.match-event-editor')?.id?.replace('match-events-', '') || 0);
    const row = button?.closest('[data-match-event-row]');
    const input = row?.querySelector('.match-event-player');
    if (input) input.value = '';
    if (matchId) scheduleMatchAutoSave(matchId);
}

function renderMatchEventSuggestionList(match, teamName, query = '') {
    const raw = String(query || '').trim();
    const players = getMatchEventPlayerSuggestions(match, teamName, raw);
    if (!players.length) {
        return `
            <div class="match-event-suggestion-empty">
                未匹配到球队球员，可继续手动输入完整姓名。
            </div>
        `;
    }
    return `
        <div class="match-event-suggestion-list" role="listbox">
            ${players.map(player => `
                <button class="match-event-suggestion-option" type="button" role="option" onclick="selectMatchEventSuggestion(this, ${Number(player.uid || 0)})">
                    <span class="match-event-suggestion-name">${escapeHtml(player.name || '-')}</span>
                    <span class="match-event-suggestion-meta">${escapeHtml([player.position || '', player.uid ? `UID ${player.uid}` : ''].filter(Boolean).join(' / '))}</span>
                </button>
            `).join('')}
        </div>
    `;
}

function closeMatchEventSuggestions(exceptPanel = null) {
    const panel = document.getElementById('matchEventSuggestionPanel');
    if (panel && panel !== exceptPanel) panel.remove();
    if (panel !== exceptPanel) activeMatchEventSuggestionContext = null;
    document.querySelectorAll('.match-event-suggestions').forEach(legacyPanel => {
        if (legacyPanel !== panel && legacyPanel !== exceptPanel) legacyPanel.remove();
    });
}

function getMatchEventSuggestionPanel() {
    let panel = document.getElementById('matchEventSuggestionPanel');
    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'matchEventSuggestionPanel';
        panel.className = 'match-event-suggestions match-event-suggestions-floating';
        panel.hidden = true;
        document.body.appendChild(panel);
    }
    return panel;
}

function positionMatchEventSuggestionPanel(input, panel) {
    const rect = input.getBoundingClientRect();
    const fieldRect = input.closest('.match-event-player-field')?.getBoundingClientRect() || rect;
    const panelWidth = Math.min(Math.max(fieldRect.width, 260), window.innerWidth - 24);
    const left = Math.max(12, Math.min(fieldRect.left, window.innerWidth - panelWidth - 12));
    const estimatedHeight = Math.min(360, Math.max(180, window.innerHeight * 0.42));
    const belowTop = rect.bottom + 6;
    const aboveTop = rect.top - estimatedHeight - 6;
    const top = belowTop + estimatedHeight > window.innerHeight - 12 && aboveTop > 12 ? aboveTop : belowTop;
    panel.style.width = `${panelWidth}px`;
    panel.style.left = `${left}px`;
    panel.style.top = `${top}px`;
}

function scheduleCloseMatchEventSuggestions(input) {
    const row = input?.closest('[data-match-event-row]');
    window.setTimeout(() => {
        const panel = document.getElementById('matchEventSuggestionPanel');
        if (!panel) return;
        if (activeMatchEventSuggestionContext?.row && activeMatchEventSuggestionContext.row !== row) return;
        if (!panel.contains(document.activeElement)) closeMatchEventSuggestions();
    }, 120);
}

function handleMatchEventPlayerKeydown(event, input) {
    if (event.key !== 'Escape') return;
    closeMatchEventSuggestions();
}

function updateMatchEventSuggestions(input, matchId, forceOpen = false) {
    const match = findScheduleMatchById(matchId);
    const row = input?.closest('[data-match-event-row]');
    const panel = getMatchEventSuggestionPanel();
    const teamName = String(row?.querySelector('.match-event-team')?.value || '').trim();
    if (!match || !panel || !teamName) return;
    panel.innerHTML = renderMatchEventSuggestionList(match, teamName, input.value);
    const shouldOpen = forceOpen || Boolean(String(input.value || '').trim());
    if (shouldOpen) {
        activeMatchEventSuggestionContext = {matchId: Number(matchId), row};
        positionMatchEventSuggestionPanel(input, panel);
        closeMatchEventSuggestions(panel);
    }
    panel.hidden = !shouldOpen;
}

function toggleMatchEventSuggestions(button, matchId) {
    const row = button?.closest('[data-match-event-row]');
    const input = row?.querySelector('.match-event-player');
    const panel = getMatchEventSuggestionPanel();
    if (!input || !panel) return;
    const shouldOpen = panel.hidden || activeMatchEventSuggestionContext?.row !== row;
    if (shouldOpen) {
        input.focus();
        updateMatchEventSuggestions(input, matchId, true);
    } else {
        closeMatchEventSuggestions();
    }
}

function selectMatchEventSuggestion(button, playerUid) {
    const row = button?.closest('[data-match-event-row]') || activeMatchEventSuggestionContext?.row;
    const input = row?.querySelector('.match-event-player');
    const teamName = String(row?.querySelector('.match-event-team')?.value || '').trim();
    const matchId = Number(activeMatchEventSuggestionContext?.matchId || row?.closest('.match-event-editor')?.id?.replace('match-events-', '') || 0);
    const match = findScheduleMatchById(matchId);
    const player = getMatchTeamPlayers(match, teamName).find(item => Number(item.uid || 0) === Number(playerUid));
    if (!input || !player) return;
    input.value = player.name || '';
    closeMatchEventSuggestions();
    if (matchId) scheduleMatchAutoSave(matchId);
    input.dispatchEvent(new Event('change', {bubbles: true}));
}

function refreshMatchEventPlayerInput(teamSelect, matchId) {
    const match = findScheduleMatchById(matchId);
    const row = teamSelect?.closest('[data-match-event-row]');
    const playerInput = row?.querySelector('.match-event-player');
    const playerSelect = row?.querySelector('.match-event-player-select');
    const datalist = row?.querySelector('datalist');
    const teamName = String(teamSelect?.value || '').trim();
    if (!match || !playerInput) return;
    playerInput.value = '';
    if (playerSelect?.tagName === 'SELECT') playerSelect.innerHTML = renderMatchEventPlayerSelectOptions(match, teamName);
    if (datalist) {
        const listId = datalist.id;
        datalist.outerHTML = renderMatchEventPlayerDatalist(match, teamName, listId);
    }
    closeMatchEventSuggestions();
    scheduleMatchAutoSave(matchId);
}

function selectMatchEventPlayerOption(select) {
    const row = select?.closest('[data-match-event-row]');
    const input = row?.querySelector('.match-event-player');
    const teamName = String(row?.querySelector('.match-event-team')?.value || '').trim();
    const matchId = Number(row?.closest('.match-event-editor')?.id?.replace('match-events-', '') || 0);
    const match = findScheduleMatchById(matchId);
    const playerUid = Number(select?.value || 0);
    const player = getMatchTeamPlayers(match, teamName).find(item => Number(item.uid || 0) === playerUid);
    if (input && player) input.value = player.name || '';
    if (select) select.value = '';
    if (matchId) scheduleMatchAutoSave(matchId);
}

function handleMatchEventSuggestionDocumentPointerDown(event) {
    const panel = document.getElementById('matchEventSuggestionPanel');
    if (!panel || panel.hidden) return;
    if (panel.contains(event.target)) return;
    if (event.target?.closest?.('.match-event-player-field')) return;
    closeMatchEventSuggestions();
}

document.addEventListener('pointerdown', handleMatchEventSuggestionDocumentPointerDown, true);

function buildAdminMatchControlGroup(match) {
    const homeScore = match.home_score ?? '';
    const awayScore = match.away_score ?? '';
    const status = isScheduleForfeitStatus(match.status) ? match.status : 'played';
    const isForfeit = isScheduleForfeitStatus(status);
    const scoreReadonly = isForfeit ? 'readonly' : '';
    return `
        <div class="match-edit-card ${isForfeit ? 'is-forfeit' : ''}">
            <div class="match-edit-controls">
                <span class="match-edit-round">第 ${Number(match.round_no) || '-'} 轮</span>
                <input type="number" min="0" id="match-home-${match.id}" value="${escapeHtml(homeScore)}" aria-label="主队进球" ${scoreReadonly} oninput="scheduleMatchAutoSave(${Number(match.id)})" onchange="scheduleMatchAutoSave(${Number(match.id)})">
                <span>-</span>
                <input type="number" min="0" id="match-away-${match.id}" value="${escapeHtml(awayScore)}" aria-label="客队进球" ${scoreReadonly} oninput="scheduleMatchAutoSave(${Number(match.id)})" onchange="scheduleMatchAutoSave(${Number(match.id)})">
                <select class="match-status-select" id="match-status-${match.id}" aria-label="比赛判定" onchange="handleMatchStatusChange(${Number(match.id)})">
                    <option value="played" ${status === 'played' ? 'selected' : ''}>正常比赛</option>
                    <option value="home_forfeit" ${status === 'home_forfeit' ? 'selected' : ''}>主队判负</option>
                    <option value="away_forfeit" ${status === 'away_forfeit' ? 'selected' : ''}>客队判负</option>
                    <option value="double_forfeit" ${status === 'double_forfeit' ? 'selected' : ''}>双方判负</option>
                </select>
                <button class="btn btn-secondary match-reset-btn" type="button" onclick="resetMatchResult(${match.id})">设为未赛</button>
            </div>
            <div class="match-forfeit-note" ${isForfeit ? '' : 'hidden'}>判负状态会按规则自动锁定比分，保存后不记录进球、助攻和本场最佳。</div>
            ${renderMatchEventEditor(match)}
        </div>
    `;
}

function handleMatchStatusChange(matchId) {
    const statusSelect = document.getElementById(`match-status-${matchId}`);
    const homeInput = document.getElementById(`match-home-${matchId}`);
    const awayInput = document.getElementById(`match-away-${matchId}`);
    const editCard = statusSelect?.closest('.match-edit-card');
    const note = editCard?.querySelector('.match-forfeit-note');
    const score = getForfeitScoreForStatus(statusSelect?.value);
    if (homeInput) homeInput.readOnly = Boolean(score);
    if (awayInput) awayInput.readOnly = Boolean(score);
    editCard?.classList.toggle('is-forfeit', Boolean(score));
    if (note) note.hidden = !score;
    if (score) {
        if (homeInput) homeInput.value = score.home_score;
        if (awayInput) awayInput.value = score.away_score;
    }
    scheduleMatchAutoSave(matchId);
}

function buildAdminMatchControls(match) {
    if (!canManageSchedule) return '';
    return `<td class="match-edit-cell">${buildAdminMatchControlGroup(match)}</td>`;
}

function groupMatchesByLevelAndRound(matches) {
    const groups = {};
    for (const match of matches) {
        const level = match.level || '未分级';
        const roundNo = Number(match.round_no) || 0;
        if (!groups[level]) groups[level] = {};
        if (!groups[level][roundNo]) groups[level][roundNo] = [];
        groups[level][roundNo].push(match);
    }
    return groups;
}

function groupRoundsIntoPairs(roundGroups) {
    const pairs = {};
    for (const roundKey of Object.keys(roundGroups || {})) {
        const roundNo = Number(roundKey);
        const pairStart = getRoundPairStart(roundNo);
        if (!pairStart) continue;
        if (!pairs[pairStart]) pairs[pairStart] = {rounds: [], matches: []};
        pairs[pairStart].rounds.push(roundNo);
        pairs[pairStart].matches.push(...roundGroups[roundNo]);
    }
    return Object.keys(pairs)
        .map(Number)
        .sort((a, b) => a - b)
        .map(pairStart => {
            const rounds = [...new Set(pairs[pairStart].rounds)].sort((a, b) => a - b);
            const matches = pairs[pairStart].matches.sort((a, b) => {
                const roundDiff = Number(a.round_no || 0) - Number(b.round_no || 0);
                if (roundDiff) return roundDiff;
                return String(a.home_team_name || '').localeCompare(String(b.home_team_name || ''));
            });
            return {pairStart, rounds, matches};
        });
}

function getMatchPairKey(match) {
    return [String(match.home_team_name || ''), String(match.away_team_name || '')]
        .map(name => name.trim())
        .sort((a, b) => a.localeCompare(b))
        .join('|||');
}

function buildSchedulePairRows(matches) {
    const rowsByPair = new Map();
    for (const match of matches || []) {
        const key = getMatchPairKey(match);
        if (!rowsByPair.has(key)) rowsByPair.set(key, []);
        rowsByPair.get(key).push(match);
    }
    return [...rowsByPair.values()].map(pairMatches => {
        const sortedMatches = [...pairMatches].sort((a, b) => {
            const roundDiff = Number(a.round_no || 0) - Number(b.round_no || 0);
            if (roundDiff) return roundDiff;
            return Number(a.id || 0) - Number(b.id || 0);
        });
        return {
            key: getMatchPairKey(sortedMatches[0]),
            teams: [sortedMatches[0]?.home_team_name || '-', sortedMatches[0]?.away_team_name || '-'],
            matches: sortedMatches,
        };
    }).sort((a, b) => {
        const firstRoundDiff = Number(a.matches[0]?.round_no || 0) - Number(b.matches[0]?.round_no || 0);
        if (firstRoundDiff) return firstRoundDiff;
        return Number(a.matches[0]?.id || 0) - Number(b.matches[0]?.id || 0);
    });
}

function renderScheduleLegCell(match) {
    if (!match) return '<td class="schedule-leg-cell is-empty">-</td>';
    return `
        <td class="schedule-leg-cell">
            <div class="schedule-leg-main">
                <span class="schedule-leg-teams">${escapeHtml(match.home_team_name || '-')} <strong>${escapeHtml(formatMatchScore(match))}</strong> ${escapeHtml(match.away_team_name || '-')}</span>
                <span class="match-status-pill is-${escapeHtml(match.status || 'scheduled')}">${escapeHtml(getMatchStatusLabel(match.status))}</span>
            </div>
        </td>
    `;
}

function renderSchedulePairAdminCell(pair) {
    if (!canManageSchedule) return '';
    return `
        <td class="match-edit-cell schedule-pair-edit-cell">
            ${(pair.matches || []).map(buildAdminMatchControlGroup).join('')}
        </td>
    `;
}

function buildScheduleBatchActions(matches) {
    if (!canManageSchedule) return '';
    const matchIds = (matches || []).map(match => Number(match.id)).filter(Boolean);
    if (!matchIds.length) return '';
    return `
        <div class="schedule-batch-actions">
            <button class="btn btn-primary" type="button" onclick="saveCurrentMatchProgress([${matchIds.join(',')}])">保存</button>
        </div>
    `;
}

function renderMobileScheduleMatchCard(match) {
    if (!match) {
        return `
            <article class="mobile-schedule-card is-empty">
                <span>本轮暂无对阵</span>
            </article>
        `;
    }
    const played = isScheduleMatchPlayed(match);
    const status = match.status || 'scheduled';
    const score = getScheduleMatchScoreText(match);
    const statusToneClass = getScheduleStatusTone(status);
    return `
        <article class="mobile-schedule-card ${played ? 'is-played' : 'is-pending'}" data-match-id="${Number(match.id) || 0}">
            <div class="mobile-schedule-card-head">
                <span class="mobile-schedule-round">第 ${Number(match.round_no) || '-'} 轮</span>
                <span class="mobile-schedule-status ${statusToneClass}">
                    <span aria-hidden="true">${played ? '✓' : '•'}</span>
                    ${escapeHtml(getMatchStatusLabel(status))}
                </span>
            </div>
            <div class="mobile-schedule-matchup">
                ${renderScheduleMobileTeam(match, 'home')}
                <div class="mobile-schedule-score-block">
                    <strong class="mobile-schedule-score">${escapeHtml(score)}</strong>
                </div>
                ${renderScheduleMobileTeam(match, 'away')}
            </div>
            <div class="mobile-schedule-card-events">
                ${renderScheduleMatchEvents(match)}
            </div>
            ${canManageSchedule ? `
                <button class="mobile-schedule-edit-trigger" type="button" onclick="openMobileScheduleEditDrawer(${Number(match.id)})">
                    <span>编辑事件</span>
                    <span aria-hidden="true">›</span>
                </button>
            ` : ''}
        </article>
    `;
}

function renderMobileScheduleList(matches) {
    return `
        <div class="mobile-schedule-card-list">
            ${(matches || []).map(renderMobileScheduleMatchCard).join('')}
        </div>
    `;
}

function renderMobileSchedulePair(pair, roundPair) {
    const pairMatches = roundPair.rounds.map(roundNo => pair.matches.find(match => Number(match.round_no) === Number(roundNo)));
    return `
        <article class="mobile-schedule-pair-card">
            <header class="mobile-schedule-pair-head">
                <strong title="${escapeHtml(pair.teams.join(' / '))}">${escapeHtml(pair.teams.join(' / '))}</strong>
            </header>
            <div class="mobile-schedule-match-list">
                ${pairMatches.map(renderMobileScheduleMatchCard).join('')}
            </div>
        </article>
    `;
}

function renderMobileScheduleRound(roundPair) {
    return `
        <div class="schedule-round-block mobile-schedule-round-block">
            <div class="schedule-round-header">
                <h3>${escapeHtml(formatRoundPairLabel(roundPair.rounds))}</h3>
                ${buildScheduleBatchActions(roundPair.matches)}
            </div>
            <div class="mobile-schedule-list">
                ${buildSchedulePairRows(roundPair.matches).map(pair => renderMobileSchedulePair(pair, roundPair)).join('')}
            </div>
        </div>
    `;
}

function flushScheduleMatchAutoSave(matchId) {
    const numericMatchId = Number(matchId || 0);
    if (!numericMatchId || !scheduleAutoSaveTimers.has(numericMatchId)) return;
    window.clearTimeout(scheduleAutoSaveTimers.get(numericMatchId));
    scheduleAutoSaveTimers.delete(numericMatchId);
    saveScheduleMatchQuietly(numericMatchId);
}

function openMobileScheduleEditDrawer(matchId) {
    if (!canManageSchedule) return;
    const match = findScheduleMatchById(matchId);
    if (!match) return;
    activeMobileScheduleEditMatchId = Number(matchId);
    renderScheduleBoard();
    window.requestAnimationFrame(() => {
        document.querySelector('.mobile-schedule-editor-sheet')?.focus();
    });
}

function closeMobileScheduleEditDrawer() {
    const matchId = activeMobileScheduleEditMatchId;
    if (matchId) flushScheduleMatchAutoSave(matchId);
    activeMobileScheduleEditMatchId = null;
    closeMatchEventSuggestions();
    document.body.classList.remove('mobile-schedule-editor-open');
    renderScheduleBoard();
}

function renderMobileScheduleEditDrawer() {
    if (!canManageSchedule || !activeMobileScheduleEditMatchId) {
        document.body.classList.remove('mobile-schedule-editor-open');
        return '';
    }
    const match = findScheduleMatchById(activeMobileScheduleEditMatchId);
    if (!match) {
        activeMobileScheduleEditMatchId = null;
        document.body.classList.remove('mobile-schedule-editor-open');
        return '';
    }
    const score = getScheduleMatchScoreText(match);
    document.body.classList.add('mobile-schedule-editor-open');
    return `
        <div class="mobile-schedule-editor-overlay" role="presentation" onclick="if (event.target === this) closeMobileScheduleEditDrawer()">
            <aside class="mobile-schedule-editor-sheet" role="dialog" aria-modal="true" aria-label="编辑赛程事件" tabindex="-1">
                <header class="mobile-schedule-editor-head">
                    <div>
                        <span>赛程维护</span>
                        <strong>${escapeHtml(match.home_team_name || '-')} vs ${escapeHtml(match.away_team_name || '-')}</strong>
                    </div>
                    <button type="button" class="mobile-schedule-editor-close" onclick="closeMobileScheduleEditDrawer()" aria-label="关闭编辑">×</button>
                </header>
                <div class="mobile-schedule-editor-summary">
                    <span>${escapeHtml(match.home_team_name || '-')}</span>
                    <strong>${escapeHtml(score)}</strong>
                    <span>${escapeHtml(match.away_team_name || '-')}</span>
                </div>
                <div class="mobile-schedule-editor-body">
                    ${buildAdminMatchControlGroup(match)}
                </div>
            </aside>
        </div>
    `;
}

function downloadCompetitionBlob(blob, fileName) {
    if (typeof downloadBlob === 'function') {
        downloadBlob(blob, fileName);
        return;
    }
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1200);
}

function buildCompetitionImageFileName(kind, level) {
    const cleanLevel = String(level || currentCompetitionLevel || 'HEIGO').replace(/[\\/:*?"<>|\s]+/g, '_');
    const label = kind === 'suspensions' ? '伤停统计' : '积分榜';
    const date = new Date();
    const stamp = [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, '0'),
        String(date.getDate()).padStart(2, '0'),
    ].join('');
    return `HEIGO_${cleanLevel}_${label}_${stamp}.png`;
}

async function saveCompetitionImage(kind, level = currentCompetitionLevel) {
    if (competitionImageExportBusy) return;
    if (!window.htmlToImage || typeof window.htmlToImage.toBlob !== 'function') {
        showModal('导出组件未就绪', '页面截图组件加载失败，请刷新页面后重试。');
        return;
    }
    const exportKey = `${kind}-${level}`;
    const target = Array.from(document.querySelectorAll('[data-export-view]'))
        .find(item => item.getAttribute('data-export-view') === exportKey);
    if (!target) {
        showModal('暂时无法保存', '当前没有可导出的统计内容。');
        return;
    }

    competitionImageExportBusy = true;
    target.classList.add('is-exporting');
    try {
        if (document.fonts?.ready) await document.fonts.ready;
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        const blob = await window.htmlToImage.toBlob(target, {
            cacheBust: true,
            pixelRatio: Math.max(2, Math.min(3, window.devicePixelRatio || 1)),
            filter: node => !(node?.classList && node.classList.contains('capture-exclude')),
        });
        if (!blob) throw new Error('capture-blob-empty');
        downloadCompetitionBlob(blob, buildCompetitionImageFileName(kind, level));
    } catch (error) {
        console.error('Failed to export competition image:', error);
        showModal('生成图片失败', '统计图片生成失败，请刷新页面后重试。');
    } finally {
        target.classList.remove('is-exporting');
        competitionImageExportBusy = false;
    }
}

function renderScheduleBoard() {
    closeMatchEventSuggestions();
    const container = document.getElementById('scheduleBoard');
    if (!container) return;
    populateScheduleFilters();
    if (isCupCompetitionLevel()) {
        activeMobileScheduleEditMatchId = null;
        document.body.classList.remove('mobile-schedule-editor-open');
        container.innerHTML = '<div class="no-data">杯赛小组赛阶段以后再开放；当前请在“积分榜”页查看淘汰赛晋级图。</div>';
        return;
    }
    const matches = getFilteredScheduleMatches();
    if (!matches.length) {
        activeMobileScheduleEditMatchId = null;
        document.body.classList.remove('mobile-schedule-editor-open');
        container.innerHTML = '<div class="no-data">暂无赛程数据。管理员可先导入 imports/schedules/ 下的最新赛程文件。</div>';
        return;
    }

    const rounds = getScheduleRoundsForCurrentLevel();
    const currentRound = getCurrentScheduleRound();
    const orderedMatches = [...matches].sort((a, b) => {
        const roundDiff = Number(a.round_no || 0) - Number(b.round_no || 0);
        if (roundDiff) return roundDiff;
        return Number(a.id || 0) - Number(b.id || 0);
    });
    const includeDesktopAdmin = !isMobileViewport();
    container.innerHTML = `
        <section class="schedule-fixture-shell">
            ${renderScheduleRoundNavigator(rounds, currentRound, orderedMatches)}
            <div class="schedule-fixture-list schedule-desktop-fixture-list">
                ${orderedMatches.map(match => renderScheduleMatchRow(match, {includeAdmin: includeDesktopAdmin})).join('')}
            </div>
            ${renderMobileScheduleList(orderedMatches)}
            ${renderMobileScheduleEditDrawer()}
        </section>
    `;
}

async function loadCompetitionData(options = {}) {
    renderCompetitionAdminActions();
    if (competitionDataLoaded && options.force !== true) {
        renderCompetitionPrimaryBoard();
        renderScheduleBoard();
        renderSuspensionsBoard();
        return;
    }

    const standingsContainer = document.getElementById('standingsBoard');
    const scheduleContainer = document.getElementById('scheduleBoard');
    if (standingsContainer) standingsContainer.innerHTML = '<div class="loading">加载中...</div>';
    if (scheduleContainer) scheduleContainer.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const [standingsRes, scheduleRes, playerRankingsRes, suspensionsRes, siteNotesRes, championsCupRes, leagueCupRes, wumingjianCupRes] = await Promise.all([
            fetch('/api/standings'),
            fetch('/api/matches'),
            fetch('/api/player-rankings'),
            fetch('/api/suspensions'),
            fetch('/api/site-notes'),
            fetch('/api/cups/champions_cup/bracket'),
            fetch('/api/cups/league_cup/bracket'),
            fetch('/api/cups/wumingjian_cup/bracket'),
        ]);
        standingsData = await standingsRes.json();
        scheduleData = await scheduleRes.json();
        playerRankingData = await playerRankingsRes.json();
        suspensionData = await suspensionsRes.json();
        siteNotesData = (await siteNotesRes.json()).reduce((acc, note) => {
            acc[note.key] = note;
            return acc;
        }, {});
        cupBracketData = {
            champions_cup: await championsCupRes.json(),
            league_cup: await leagueCupRes.json(),
            wumingjian_cup: await wumingjianCupRes.json(),
        };
        competitionDataLoaded = true;
    } catch (error) {
        if (standingsContainer) standingsContainer.innerHTML = '<div class="no-data">积分榜加载失败，请稍后重试。</div>';
        if (scheduleContainer) scheduleContainer.innerHTML = '<div class="no-data">赛程加载失败，请稍后重试。</div>';
        return;
    }

    renderCompetitionAdminActions();
    renderCompetitionPrimaryBoard();
    renderScheduleBoard();
    renderPlayerRankingsBoard();
    renderSuspensionsBoard();
}

function resetScheduleFilters() {
    const levelSelect = document.getElementById('scheduleLevelSelect');
    const roundSelect = document.getElementById('scheduleRoundSelect');
    if (roundSelect) roundSelect.value = '';
    renderScheduleBoard();
}

async function importLatestSchedule() {
    if (!canManageSchedule) return;
    const confirmed = confirm('确认导入 imports/schedules/ 下最新的赛程 Excel？同一场已录入比分会保留。');
    if (!confirmed) return;
    const result = await adminJsonRequest('/api/admin/matches/import', {method: 'POST'});
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('赛程导入失败', escapeHtml(data.detail || data.message || '导入失败'));
        return;
    }
    competitionDataLoaded = false;
    await loadCompetitionData({force: true});
    const warningHtml = (data.warnings || []).slice(0, 10).map(item => `<li>${escapeHtml(item)}</li>`).join('');
    showModal('赛程导入完成', `
        <div class="maintenance-note">${escapeHtml(data.message || '')}</div>
        <div class="maintenance-note" style="margin-top:8px;"><strong>来源：</strong><code>${escapeHtml(data.source_file || '')}</code></div>
        ${warningHtml ? `<div class="maintenance-note" style="margin-top:8px;"><strong>未匹配球队：</strong><ul style="margin:6px 0 0 18px;">${warningHtml}</ul></div>` : ''}
    `);
}

function readMatchScorePayload(matchId) {
    const homeInput = document.getElementById(`match-home-${matchId}`);
    const awayInput = document.getElementById(`match-away-${matchId}`);
    const statusSelect = document.getElementById(`match-status-${matchId}`);
    const selectedStatus = String(statusSelect?.value || '').trim();
    const forcedScore = getForfeitScoreForStatus(selectedStatus);
    if (forcedScore) {
        if (homeInput) homeInput.value = forcedScore.home_score;
        if (awayInput) awayInput.value = forcedScore.away_score;
        return {
            match_id: Number(matchId),
            home_score: forcedScore.home_score,
            away_score: forcedScore.away_score,
            status: selectedStatus,
            events: [],
        };
    }
    const homeRaw = String(homeInput?.value ?? '').trim();
    const awayRaw = String(awayInput?.value ?? '').trim();
    if ((homeRaw === '') !== (awayRaw === '')) {
        throw new Error('请填写完整的双方比分，或清空双方比分后再保存。');
    }
    const homeScore = homeRaw === '' ? null : Number(homeRaw);
    const awayScore = awayRaw === '' ? null : Number(awayRaw);
    if (
        (homeScore !== null && (!Number.isInteger(homeScore) || homeScore < 0)) ||
        (awayScore !== null && (!Number.isInteger(awayScore) || awayScore < 0))
    ) {
        throw new Error('比分必须是 0 或正整数。');
    }
    const match = findScheduleMatchById(matchId);
    const events = readMatchEventPayload(matchId, match);
    return {
        match_id: Number(matchId),
        home_score: homeScore,
        away_score: awayScore,
        status: '',
        events,
    };
}

function readMatchEventPayload(matchId, match) {
    const rows = Array.from(document.querySelectorAll(`#match-events-${matchId} [data-match-event-row]`));
    return rows.map(row => {
        const teamName = String(row.querySelector('.match-event-team')?.value || '').trim();
        const playerInput = String(row.querySelector('.match-event-player')?.value || '').trim();
        const eventType = String(row.querySelector('.match-event-type')?.value || '').trim();
        const quantity = Number(row.querySelector('.match-event-quantity')?.value || 0);
        if (!playerInput && (!quantity || quantity === 1)) return null;
        const player = findMatchEventPlayer(match, teamName, playerInput);
        if (!teamName) throw new Error('请选择事件球队。');
        if (!player) throw new Error(`未找到球员：${playerInput}`);
        if (!['goal', 'assist', 'mvp'].includes(eventType)) throw new Error('请选择进球、助攻或最佳。');
        if (eventType !== 'mvp' && (!Number.isInteger(quantity) || quantity <= 0)) throw new Error('事件数量必须是正整数。');
        const validTeam = getMatchTeamOptions(match).some(team => team.team_name === teamName);
        if (!validTeam) throw new Error('事件球队必须属于本场比赛。');
        return {
            team_name: teamName,
            player_uid: Number(player.uid || 0),
            player_name: player.name || '',
            event_type: eventType,
            quantity: eventType === 'mvp' ? 1 : quantity,
        };
    }).filter(Boolean);
}

function applyMatchPayloadLocally(payload) {
    const match = findScheduleMatchById(payload.match_id);
    if (!match) return;
    match.home_score = payload.home_score;
    match.away_score = payload.away_score;
    match.status = payload.status || (payload.home_score === null || payload.away_score === null ? 'scheduled' : 'played');
    match.events = payload.events || [];
}

function scheduleMatchAutoSave(matchId) {
    if (!canManageSchedule) return;
    const numericMatchId = Number(matchId || 0);
    if (!numericMatchId) return;
    if (scheduleAutoSaveTimers.has(numericMatchId)) {
        window.clearTimeout(scheduleAutoSaveTimers.get(numericMatchId));
    }
    const timer = window.setTimeout(() => {
        scheduleAutoSaveTimers.delete(numericMatchId);
        saveScheduleMatchQuietly(numericMatchId);
    }, 800);
    scheduleAutoSaveTimers.set(numericMatchId, timer);
}

async function saveScheduleMatchQuietly(matchId) {
    if (!canManageSchedule) return;
    let payload;
    try {
        payload = readMatchScorePayload(matchId);
    } catch (error) {
        return;
    }
    const result = await adminJsonRequest('/api/admin/matches/batch', {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({matches: [payload]}),
    });
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) return;
    applyMatchPayloadLocally(payload);
    competitionDataLoaded = false;
}

async function saveCurrentMatchProgress(matchIds) {
    if (!canManageSchedule) return;
    let matches = [];
    try {
        matches = (matchIds || []).map(readMatchScorePayload);
    } catch (error) {
        showModal('保存失败', escapeHtml(error.message || '比分填写不完整'));
        return;
    }
    if (!matches.length) return;
    const result = await adminJsonRequest('/api/admin/matches/batch', {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({matches}),
    });
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('保存失败', escapeHtml(data.detail || data.message || '保存比分失败'));
        return;
    }
    competitionDataLoaded = false;
    await loadCompetitionData({force: true});
}

async function saveMatchResult(matchId) {
    return saveCurrentMatchProgress([matchId]);
}

async function resetMatchResult(matchId) {
    if (!canManageSchedule) return;
    const confirmed = confirm('确认将这场比赛重置为未赛？双方比分会被清空。');
    if (!confirmed) return;
    const result = await adminJsonRequest(`/api/admin/matches/${matchId}`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({home_score: null, away_score: null, status: 'scheduled'}),
    });
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('重置失败', escapeHtml(data.detail || data.message || '重置比赛失败'));
        return;
    }
    competitionDataLoaded = false;
    await loadCompetitionData({force: true});
}

async function initializeCupBracket() {
    if (!canManageSchedule) return;
    const cupConfig = getCurrentCupConfig();
    if (!cupConfig) return;
    const result = await adminJsonRequest(`/api/admin/cups/${cupConfig.key}/initialize`, {method: 'POST'});
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('初始化失败', escapeHtml(data.detail || data.message || '初始化杯赛失败'));
        return;
    }
    competitionDataLoaded = false;
    await loadCompetitionData({force: true});
}

async function saveCupMatchTeams(matchId) {
    if (!canManageSchedule) return;
    const homeTeamId = Number(document.getElementById(`cup-home-team-${matchId}`)?.value || 0) || null;
    const awayTeamId = Number(document.getElementById(`cup-away-team-${matchId}`)?.value || 0) || null;
    const result = await adminJsonRequest(`/api/admin/cups/matches/${matchId}/teams`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({home_team_id: homeTeamId, away_team_id: awayTeamId}),
    });
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('保存失败', escapeHtml(data.detail || data.message || '保存杯赛球队失败'));
        return;
    }
    competitionDataLoaded = false;
    await loadCompetitionData({force: true});
}

async function saveCupMatchResult(matchId) {
    if (!canManageSchedule) return;
    const match = findCupMatchById(matchId);
    const homeRaw = String(document.getElementById(`cup-home-score-${matchId}`)?.value ?? '').trim();
    const awayRaw = String(document.getElementById(`cup-away-score-${matchId}`)?.value ?? '').trim();
    const status = document.getElementById(`cup-status-${matchId}`)?.value || 'scheduled';
    if ((homeRaw === '') !== (awayRaw === '')) {
        showModal('保存失败', '请填写完整的双方比分，或清空双方比分后再保存。');
        return;
    }
    const homeScore = homeRaw === '' ? null : Number(homeRaw);
    const awayScore = awayRaw === '' ? null : Number(awayRaw);
    if (
        (homeScore !== null && (!Number.isInteger(homeScore) || homeScore < 0)) ||
        (awayScore !== null && (!Number.isInteger(awayScore) || awayScore < 0))
    ) {
        showModal('保存失败', '比分必须是 0 或正整数。');
        return;
    }
    const payload = {
        home_score: homeScore,
        away_score: awayScore,
        status,
    };
    if (status === 'played' && homeScore !== null && awayScore !== null && homeScore === awayScore) {
        const winnerTeamId = promptCupTieWinner(match);
        if (!winnerTeamId) return;
        payload.winner_team_id = winnerTeamId;
        payload.notes = isTwoLegCupStage(match) ? '总比分相同，按客场进球规则晋级' : '比分相同，手动选择晋级球队';
    }
    const result = await adminJsonRequest(`/api/admin/cups/matches/${matchId}/result`, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('保存失败', escapeHtml(data.detail || data.message || '保存杯赛比分失败'));
        return;
    }
    competitionDataLoaded = false;
    await loadCompetitionData({force: true});
}
