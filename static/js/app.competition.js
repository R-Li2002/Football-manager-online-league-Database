var fetchWithTimeout = globalThis.fetchWithTimeout || ((...args) => globalThis.fetch(...args));

var currentCompetitionSubtab = 'standings';
var currentCompetitionLevel = '超级';
var currentCupPhase = 'knockout';
var standingsData = {levels: [], rows: []};
var scheduleData = {levels: [], rounds: [], matches: []};
var playerRankingData = {levels: [], rows: []};
var rankingData = {initial_points: 1000, appearance_bonus: 20, transfer_rate: 0.1, cutoff_floor: null, total_matches: 0, rows: [], matches: []};
var suspensionData = {levels: [], teams: []};
var seasonArchiveData = [];
var siteNotesData = {};
var cupBracketData = {};
var cupGroupStageData = {};
var wumingjianQualificationData = null;
var currentCupGroupScheduleView = 'groups';
var cupGroupScoreSaveTimers = new Map();
var cupGroupScoreSaveVersions = new Map();
var cupGroupScoreSaveInFlight = new Set();
var currentCupResultsGroupNo = null;
var cupGroupVisiblePairKeys = new Set();
var competitionDataLoaded = false;
var competitionLoadedSections = new Set();
var competitionSectionLoadPromises = new Map();
var competitionSectionDataCache = new Map();
var currentPlayerRankingType = 'goals';
var activeSuspensionEditorTeamId = null;
var competitionImageExportBusy = false;
var currentMobileStandingsScope = 'total';
var expandedMobileStandingRows = new Set();
var standingsHistoryCache = new Map();
var standingsHistoryState = {
    level: '',
    data: null,
    index: 0,
    speed: 1,
    playing: false,
    timer: null,
    focusMode: 'all',
    selectedTeamIds: new Set(),
    returnFocus: null,
    resizeObserver: null,
};
var matchTeamPlayerCache = new Map();
var activeMatchEventSuggestionContext = null;
var activeSuspensionSuggestionContext = null;
var activeCupGroupSuggestionContext = null;
var activeMobileScheduleEditMatchId = null;
var activeMatchEventEditorMatchId = null;
var matchEventEditorDirty = false;
var matchEventEditorReturnFocus = null;
var matchEventDraftSaveTimer = null;
const MATCH_EVENT_DRAFT_STORAGE_PREFIX = 'heigoMatchEventDraft:v1:';
const MATCH_EVENT_DRAFT_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;
var matchEventRowDomIdSeed = 0;
var scheduleAutoSaveTimers = new Map();
var scheduleMatchSaveStates = new Map();
var scheduleMatchSaveVersions = new Map();
var scheduleMatchSaveInFlight = new Set();
var scheduleMatchSaveQueued = new Set();
var expandedMobileScheduleMatches = new Set();
var expandedMobilePlayerRankingRows = new Set();
var expandedMobileSuspensionTeams = new Set();
var currentSuspensionViewFilter = 'active';
var suspensionProgressSaveTimers = new Map();
var suspensionProgressSaveVersions = new Map();
var suspensionProgressSaveInFlight = new Set();
var suspensionRecordSaveTimers = new Map();
var suspensionRecordSaveVersions = new Map();
var suspensionRecordSaveInFlight = new Set();
var suspensionRecordDrafts = new Map();
var suspensionRecordLastSavedSignatures = new Map();
var suspensionRecordEntryModes = new Map();
var competitionWorkData = null;
var competitionWorkLoadPromise = null;
var competitionWorkLoadError = '';
var currentCompetitionWorkFilter = 'all';
var currentCompetitionWorkTargetMatchId = null;
var competitionAssignableAccounts = [];
var competitionWorkPanelExpanded = false;
var rankingMatchMutationBusy = false;
var rankingCutoffMutationBusy = false;
const SUSPENSION_IMAGE_MAX_BYTES = (4 * 1024 * 1024) - (64 * 1024);
const SUSPENSION_IMAGE_TARGET_PIXELS = 6500000;
const SUSPENSION_IMAGE_MIN_WIDTH = 640;

function renderCompetitionDataStatus() {
    const container = document.getElementById('competitionDataStatus');
    if (!container) return;
    if (['rating', 'archives'].includes(currentCompetitionSubtab)) {
        container.hidden = true;
        return;
    }
    const keys = {
        standings: 'standings',
        schedule: 'schedule',
        playerRankings: 'player_rankings',
        suspensions: 'suspensions',
    };
    const labels = {
        standings: '积分榜',
        schedule: '赛程',
        playerRankings: '球员榜',
        suspensions: '伤停',
    };
    const moduleLabel = labels[currentCompetitionSubtab] || '积分榜';
    const metrics = getCompetitionModuleMetrics();
    const item = isCupCompetitionLevel() ? null : getDataStatusItem(keys[currentCompetitionSubtab] || 'standings', currentCompetitionLevel);
    const status = item?.status || (isCupCompetitionLevel() ? 'normal' : 'unknown');
    const isWumingjianSchedule = getCurrentCupConfig()?.key === 'wumingjian_cup' && currentCompetitionSubtab === 'schedule';
    const cupScheduleLabel = isWumingjianSchedule ? '预选赛' : (currentCupGroupScheduleView === 'results' ? '小组赛赛况' : '小组赛分组');
    const cupStandingLabel = currentCupPhase === 'group' ? '小组赛积分榜' : '淘汰赛阶段';
    const statusLabel = item
        ? getDataStatusDisplayLabel(item)
        : (isCupCompetitionLevel() ? (currentCompetitionSubtab === 'schedule' ? cupScheduleLabel : cupStandingLabel) : '读取中');
    const updateTime = item?.updated_at ? formatDataStatusTime(item.updated_at) : '';
    const statusMeta = item ? dataStatusMeta(item) : [];
    const cupPhaseLabel = currentCompetitionSubtab === 'schedule' ? cupScheduleLabel : cupStandingLabel;
    const headline = isCupCompetitionLevel()
        ? `${currentCompetitionLevel} · ${cupPhaseLabel}`
        : `${currentCompetitionLevel}${moduleLabel}`;
    const description = isCupCompetitionLevel()
        ? (currentCompetitionSubtab === 'schedule'
            ? (isWumingjianSchedule
                ? '联赛第15至16轮完赛后锁定资格；44支球队通过22场单场淘汰争夺32强席位'
                : (currentCupGroupScheduleView === 'results' ? '填写小组赛比分后，积分与跨组晋级顺位自动更新' : '维护小组球队名单；输入球队名的几个字母即可自动补全'))
            : (currentCupPhase === 'group' ? '查看各组积分、跨组顺位和当前晋级去向' : '查看淘汰赛对阵、比分与晋级关系'))
        : (item?.message || `${moduleLabel}会随当前赛事数据自动更新`);
    const compactForWorker = !isCupCompetitionLevel() && hasLeagueCompetitionWorkAccess();
    container.hidden = false;
    container.innerHTML = `
        <section class="competition-module-status is-${escapeHtml(status)} ${compactForWorker ? 'is-worker-compact' : ''}" aria-label="${escapeHtml(headline)}数据摘要">
            <div class="competition-module-status-head">
                <div class="competition-module-status-title">
                    <span>${isCupCompetitionLevel() ? 'CUP STAGE' : 'MATCHDAY DATA'}</span>
                    <strong>${escapeHtml(headline)}</strong>
                    <p>${escapeHtml(description)}</p>
                    ${statusMeta.length ? `<small class="competition-module-status-meta">${statusMeta.map(value => escapeHtml(value)).join('<i>·</i>')}</small>` : ''}
                </div>
                <div class="competition-module-status-badge">
                    ${dataStatusIconSvg(status)}
                    <span>${escapeHtml(statusLabel)}</span>
                    ${updateTime ? `<small>${escapeHtml(updateTime)}</small>` : ''}
                </div>
            </div>
            <div class="competition-module-metrics">
                ${metrics.map(metric => `
                    <span class="competition-module-metric ${metric.tone ? `is-${escapeHtml(metric.tone)}` : ''}">
                        <small>${escapeHtml(metric.label)}</small>
                        <strong>${escapeHtml(metric.value)}</strong>
                        ${metric.note ? `<em>${escapeHtml(metric.note)}</em>` : ''}
                    </span>
                `).join('')}
            </div>
        </section>
    `;
}

function getCompetitionModuleMetrics() {
    if (isCupCompetitionLevel()) {
        const cupConfig = getCurrentCupConfig();
        if (currentCompetitionSubtab === 'schedule' && cupConfig?.key === 'wumingjian_cup') {
            const qualification = wumingjianQualificationData;
            const matches = qualification?.preliminary_matches || [];
            return [
                {label: '直通32强', value: `${qualification?.direct_qualifiers?.length || 0}/10`, tone: qualification?.qualification_locked ? 'normal' : 'warning', note: qualification?.qualification_locked ? '资格已锁定' : '当前暂列'},
                {label: '预选已抽签', value: `${qualification?.assigned_match_count || 0}/22`},
                {label: '已决晋级', value: `${qualification?.played_match_count || 0}/${matches.length || 22}`, tone: qualification?.played_match_count === 22 ? 'normal' : ''},
            ];
        }
        const groupStage = cupConfig ? cupGroupStageData[cupConfig.key] : null;
        if (currentCupPhase === 'group') {
            if (currentCompetitionSubtab === 'schedule' && currentCupGroupScheduleView === 'results') {
                const matches = (groupStage?.groups || []).flatMap(group => group.matches || []);
                const played = matches.filter(match => match.status === 'played').length;
                return [
                    {label: '小组数量', value: String(groupStage?.group_count || cupConfig?.groupCount || 0)},
                    {label: '已赛', value: `${played}/${matches.length || 0}`},
                    {label: '待赛', value: String(Math.max(0, matches.length - played)), tone: played === matches.length && matches.length ? 'normal' : ''},
                ];
            }
            const totalSlots = Number(groupStage?.group_count || cupConfig?.groupCount || 0) * Number(groupStage?.teams_per_group || cupConfig?.teamsPerGroup || 0);
            const assigned = Number(groupStage?.assigned_team_count || 0);
            return [
                {label: '小组数量', value: String(groupStage?.group_count || cupConfig?.groupCount || 0)},
                {label: '每组球队', value: String(groupStage?.teams_per_group || cupConfig?.teamsPerGroup || 0)},
                {label: '已分配', value: `${assigned}/${totalSlots || 0}`, tone: assigned === totalSlots && totalSlots ? 'normal' : 'warning'},
            ];
        }
        const bracket = cupConfig ? cupBracketData[cupConfig.key] : null;
        const stages = bracket?.stages || [];
        const stageMatches = stages.flatMap(stage => stage.matches || []);
        const resolved = stageMatches.filter(match => String(match.status || '') !== 'scheduled' && match.home_score !== null && match.away_score !== null).length;
        return [
            {label: '当前阶段', value: currentCupPhase === 'group' ? '小组赛' : '淘汰赛'},
            {label: '淘汰轮次', value: String(stages.length || 0), note: stages.length ? '阶段' : '待初始化'},
            {label: '已决对阵', value: `${resolved}/${stageMatches.length || 0}`},
        ];
    }
    if (currentCompetitionSubtab === 'schedule') {
        const levelMatches = (scheduleData.matches || []).filter(match => match.level === currentCompetitionLevel);
        const rounds = getScheduleRoundsForCurrentLevel();
        const currentRound = getCurrentScheduleRound();
        const pair = buildRoundPairs(rounds).find(item => item.pairStart === getRoundPairStart(currentRound)) || {rounds: [currentRound].filter(Boolean)};
        const pairMatches = levelMatches.filter(match => pair.rounds.includes(Number(match.round_no)));
        const pairPlayed = pairMatches.filter(isScheduleMatchPlayed).length;
        const totalPlayed = levelMatches.filter(isScheduleMatchPlayed).length;
        return [
            {label: '当前轮次', value: formatRoundPairLabel(pair.rounds)},
            {label: '本轮已赛', value: `${pairPlayed}/${pairMatches.length || 0}`, tone: pairPlayed === pairMatches.length && pairMatches.length ? 'normal' : ''},
            {label: '全部进度', value: `${totalPlayed}/${levelMatches.length || 0}`},
        ];
    }
    if (currentCompetitionSubtab === 'playerRankings') {
        const coverage = getPlayerRankingCoverage();
        const rows = getPlayerRankingRows();
        return [
            {label: '上榜球员', value: String(rows.length)},
            {label: '已赛覆盖', value: `${coverage.matches_with_events}/${coverage.played_matches}`},
            {label: '待补明细', value: String(coverage.matches_missing_events), tone: coverage.matches_missing_events ? 'warning' : 'normal'},
        ];
    }
    if (currentCompetitionSubtab === 'suspensions') {
        const teams = (suspensionData.teams || []).filter(team => team.level === currentCompetitionLevel);
        const suspended = teams.reduce((total, team) => total + (team.suspended || []).length, 0);
        const cautions = teams.reduce((total, team) => total + (team.one_yellow || []).length + (team.two_yellows || []).length, 0);
        const roundNo = getSuspensionUpdateRound(currentCompetitionLevel);
        return [
            {label: '球队', value: String(teams.length)},
            {label: '黄牌关注', value: String(cautions)},
            {label: '停赛', value: String(suspended), tone: suspended ? 'warning' : 'normal', note: formatSuspensionRoundProgress(roundNo, '轮次待标注')},
        ];
    }
    const rows = (standingsData.rows || []).filter(row => row.level === currentCompetitionLevel);
    const leader = rows[0];
    const played = Math.round(rows.reduce((total, row) => total + Number(row.played || 0), 0) / 2);
    return [
        {label: '参赛球队', value: String(rows.length)},
        {label: '已赛场次', value: String(played)},
        {label: '当前领跑', value: leader?.team_name || '待定', note: leader ? `${Number(leader.points || 0)} 分` : ''},
    ];
}

function renderCompetitionIssueNavigator(summary) {
    return `
        <div class="competition-issue-navigator" aria-label="当前工作轮次问题分类">
            <span>工作定位</span>
            <button type="button" class="${summary.missing_result_count ? 'has-issue' : 'is-clear'}" onclick="openCompetitionWorkQueue('missing_result')"><strong>${Number(summary.missing_result_count || 0)}</strong><small>待录比分</small></button>
            <button type="button" class="${summary.missing_event_count ? 'has-issue' : 'is-clear'}" onclick="openCompetitionWorkQueue('missing_events')"><strong>${Number(summary.missing_event_count || 0)}</strong><small>缺少事件</small></button>
            <button type="button" class="${summary.invalid_count ? 'has-error' : 'is-clear'}" onclick="openCompetitionWorkQueue('invalid')"><strong>${Number(summary.invalid_count || 0)}</strong><small>数据异常</small></button>
            <button type="button" class="${summary.suspension_confirmed ? 'is-clear' : 'has-issue'}" onclick="showCompetitionSubtab('suspensions')"><strong>${summary.suspension_confirmed ? '✓' : '!'}</strong><small>${summary.suspension_confirmed ? '伤停已确认' : '伤停待确认'}</small></button>
        </div>
    `;
}

const COMPETITION_LEVEL_ORDER = {'超级': 1, '甲级': 2, '乙级': 3, '冠军杯': 4, '联盟杯': 5, '无铭剑杯': 6};
const LEAGUE_COMPETITION_LEVELS = ['超级', '甲级', '乙级'];
const CUP_COMPETITIONS = {
    '冠军杯': {key: 'champions_cup', className: 'champion-cup', initializeLabel: '初始化冠军杯', englishName: 'Champions Cup', groupCount: 5, teamsPerGroup: 6},
    '联盟杯': {key: 'league_cup', className: 'league-cup', initializeLabel: '初始化联盟杯', englishName: 'League Cup', groupCount: 4, teamsPerGroup: 6},
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
    'Bayer 04': 'Bayer 04 Leverkusen',
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

function setCupPhase(phase) {
    currentCupPhase = phase === 'group' ? 'group' : 'knockout';
    syncCupPhaseTabs();
    renderCompetitionAdminActions();
    if (currentCompetitionSubtab === 'schedule') {
        renderScheduleBoard();
    } else {
        renderCompetitionPrimaryBoard();
    }
    renderCompetitionDataStatus();
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
}

function syncCupPhaseTabs() {
    const container = document.getElementById('cupPhaseTabs');
    if (!container) return;
    const cupConfig = getCurrentCupConfig();
    const visible = Boolean(cupConfig && ['standings', 'schedule'].includes(currentCompetitionSubtab));
    container.hidden = !visible;
    container.className = `cup-phase-switch surface-card ${cupConfig?.className || ''}`;
    if (!visible) return;
    if (currentCompetitionSubtab === 'schedule' && cupConfig?.key === 'wumingjian_cup') {
        container.setAttribute('aria-label', '无铭剑杯预选赛阶段');
        container.innerHTML = `
            <button class="cup-phase-tab active is-single" id="cupPhaseGroupTab" type="button" role="tab" aria-selected="true">
                <span class="cup-phase-index">QR</span><span class="cup-phase-copy"><strong>预选赛</strong><small>QUALIFYING ROUND</small></span>
            </button>
        `;
        return;
    }
    if (currentCompetitionSubtab === 'schedule' && cupConfig?.groupCount) {
        container.setAttribute('aria-label', '杯赛小组赛内容切换');
        container.innerHTML = `
            <button class="cup-phase-tab ${currentCupGroupScheduleView === 'groups' ? 'active' : ''}" id="cupPhaseGroupTab" type="button" onclick="setCupGroupScheduleView('groups')" role="tab" aria-selected="${currentCupGroupScheduleView === 'groups' ? 'true' : 'false'}">
                <span class="cup-phase-index">01</span><span class="cup-phase-copy"><strong>小组赛分组</strong><small>GROUP DRAW</small></span>
            </button>
            <span class="cup-phase-connector" aria-hidden="true"><i></i></span>
            <button class="cup-phase-tab ${currentCupGroupScheduleView === 'results' ? 'active' : ''}" id="cupPhaseKnockoutTab" type="button" onclick="setCupGroupScheduleView('results')" role="tab" aria-selected="${currentCupGroupScheduleView === 'results' ? 'true' : 'false'}">
                <span class="cup-phase-index">02</span><span class="cup-phase-copy"><strong>小组赛赛况</strong><small>RESULTS & STANDINGS</small></span>
            </button>
        `;
        return;
    }
    if (currentCompetitionSubtab === 'standings' && cupConfig?.groupCount) {
        container.setAttribute('aria-label', '杯赛积分榜内容切换');
        container.innerHTML = `
            <button class="cup-phase-tab ${currentCupPhase === 'group' ? 'active' : ''}" id="cupPhaseGroupTab" type="button" onclick="setCupPhase('group')" role="tab" aria-selected="${currentCupPhase === 'group' ? 'true' : 'false'}">
                <span class="cup-phase-index">GS</span><span class="cup-phase-copy"><strong>小组赛积分榜</strong><small>GROUP STANDINGS</small></span>
            </button>
            <span class="cup-phase-connector" aria-hidden="true"><i></i></span>
            <button class="cup-phase-tab ${currentCupPhase === 'knockout' ? 'active' : ''}" id="cupPhaseKnockoutTab" type="button" onclick="setCupPhase('knockout')" role="tab" aria-selected="${currentCupPhase === 'knockout' ? 'true' : 'false'}">
                <span class="cup-phase-index">KO</span><span class="cup-phase-copy"><strong>淘汰赛阶段</strong><small>KNOCKOUT STAGE</small></span>
            </button>
        `;
        return;
    }
    container.setAttribute('aria-label', '杯赛淘汰赛阶段');
    container.innerHTML = `
        <button class="cup-phase-tab active is-single" id="cupPhaseKnockoutTab" type="button" role="tab" aria-selected="true">
            <span class="cup-phase-index">KO</span><span class="cup-phase-copy"><strong>淘汰赛阶段</strong><small>KNOCKOUT STAGE</small></span>
        </button>
    `;
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
    if (status === 'away_forfeit') return {home_score: 2, away_score: 0};
    if (status === 'double_forfeit') return {home_score: 0, away_score: 0};
    return null;
}

function getForfeitRuleNote(status) {
    if (status === 'home_forfeit') return '主队判负：本场记为 0:0，双方各得 1 分。';
    if (status === 'away_forfeit') return '客队判负：本场记为 2:0，主队得 3 分、客队不得分。';
    if (status === 'double_forfeit') return '双方判负：本场记为 0:0，双方均记负且不得分。';
    return '';
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
    currentCompetitionSubtab = ['schedule', 'playerRankings', 'rating', 'suspensions', 'archives'].includes(subtab) ? subtab : 'standings';
    if (['playerRankings', 'suspensions'].includes(currentCompetitionSubtab) && !LEAGUE_COMPETITION_LEVELS.includes(currentCompetitionLevel)) {
        currentCompetitionLevel = '超级';
    }
    if (isCupCompetitionLevel()) {
        if (currentCompetitionSubtab === 'schedule') currentCupPhase = 'group';
        else if (!getCurrentCupConfig()?.groupCount) currentCupPhase = 'knockout';
    }
    [
        ['competitionSubtabStandings', 'standings'],
        ['competitionSubtabSchedule', 'schedule'],
        ['competitionSubtabPlayerRankings', 'playerRankings'],
        ['competitionSubtabRating', 'rating'],
        ['competitionSubtabSuspensions', 'suspensions'],
        ['competitionSubtabArchives', 'archives'],
    ].forEach(([id, value]) => {
        const button = document.getElementById(id);
        if (!button) return;
        const active = currentCompetitionSubtab === value;
        button.classList.toggle('active', active);
        button.setAttribute('aria-selected', active ? 'true' : 'false');
        button.tabIndex = active ? 0 : -1;
    });
    document.getElementById('competitionStandingsView')?.classList.toggle('active', currentCompetitionSubtab === 'standings');
    document.getElementById('competitionScheduleView')?.classList.toggle('active', currentCompetitionSubtab === 'schedule');
    document.getElementById('competitionPlayerRankingsView')?.classList.toggle('active', currentCompetitionSubtab === 'playerRankings');
    document.getElementById('competitionRatingView')?.classList.toggle('active', currentCompetitionSubtab === 'rating');
    document.getElementById('competitionSuspensionsView')?.classList.toggle('active', currentCompetitionSubtab === 'suspensions');
    document.getElementById('competitionArchivesView')?.classList.toggle('active', currentCompetitionSubtab === 'archives');
    const isStandalone = ['rating', 'archives'].includes(currentCompetitionSubtab);
    const selector = document.getElementById('competitionSelector');
    const statusHost = document.getElementById('competitionDataStatus');
    const workPanel = document.getElementById('competitionWorkPanel');
    if (selector) selector.hidden = isStandalone;
    if (statusHost) statusHost.hidden = isStandalone;
    if (workPanel && isStandalone) workPanel.hidden = true;
    syncCompetitionLevelTabs();
    syncCupPhaseTabs();
    renderCompetitionAdminActions();
    renderCompetitionWorkPanel();
    renderCompetitionDataStatus();
    (globalThis.requestAnimationFrame || (callback => callback()))(() => globalThis.refreshHorizontalScrollAffordances?.(document.getElementById('competition') || document));
    const cacheKey = getCompetitionSectionCacheKey(currentCompetitionSubtab);
    if (competitionLoadedSections.has(cacheKey)) {
        applyCompetitionSectionPayload(currentCompetitionSubtab, competitionSectionDataCache.get(cacheKey));
        renderCompetitionSection(currentCompetitionSubtab);
    } else {
        renderCompetitionSectionLoading(currentCompetitionSubtab);
        loadCompetitionSection(currentCompetitionSubtab);
    }
    if (typeof syncAppHistory === 'function') {
        syncAppHistory('replace');
    }
}

function canManageRankingMatches() {
    return Boolean(canManageRankings);
}

function formatRankingPoints(value) {
    return new Intl.NumberFormat('zh-CN', {minimumFractionDigits: 0, maximumFractionDigits: 4}).format(Number(value || 0));
}

function getRankingTeamMark(row) {
    if (row?.logo_path) return `<img src="${escapeHtml(row.logo_path)}" alt="" loading="lazy" decoding="async">`;
    return escapeHtml(getScheduleTeamInitials(row?.team_name || '—'));
}

function renderMobileRankingList(rows) {
    return `<ol class="mobile-ranking-list" aria-label="排位积分榜">${rows.map(row => `
        <li class="${Number(row.rank) <= 3 ? `is-podium is-rank-${Number(row.rank)}` : ''}">
            <span class="mobile-ranking-position">${String(Number(row.rank)).padStart(2, '0')}</span>
            <span class="ranking-team-mark ${row.logo_path ? 'has-logo' : ''}">${getRankingTeamMark(row)}</span>
            <span class="mobile-ranking-team"><strong>${escapeHtml(row.team_name)}</strong><small>${escapeHtml(row.level)} · 基础 ${formatRankingPoints(row.base_points)} · ${Number(row.matches)}场 · ${Number(row.wins)}胜 ${Number(row.draws || 0)}平 ${Number(row.losses)}负</small></span>
            <strong class="mobile-ranking-points">${formatRankingPoints(row.total_points)}</strong>
        </li>
    `).join('')}</ol>`;
}

function renderRankingEntryForm() {
    if (!canManageRankingMatches()) {
        return '<div class="ranking-entry-locked"><strong>比赛记录</strong><span>拥有“排位统计”权限后可在这里添加胜平负结果。</span></div>';
    }
    const options = (rankingData.rows || [])
        .slice()
        .sort((a, b) => String(a.team_name || '').localeCompare(String(b.team_name || ''), 'en'))
        .map(row => `<option value="${Number(row.team_id)}">${escapeHtml(row.team_name)}</option>`)
        .join('');
    return `
        <form class="ranking-entry-form" onsubmit="event.preventDefault(); saveRankingMatch();">
            <div class="ranking-entry-heading"><div><span>NEW RESULT</span><strong>添加排位比赛</strong></div><small>保存后即时重算</small></div>
            <label><span>主队</span><select id="rankingHomeTeam" required><option value="">选择球队</option>${options}</select></label>
            <fieldset class="ranking-result-entry">
                <legend>比赛结果</legend>
                <label><input type="radio" name="rankingResult" value="home" required><span>主队胜</span></label>
                <label><input type="radio" name="rankingResult" value="draw" required><span>平局</span></label>
                <label><input type="radio" name="rankingResult" value="away" required><span>客队胜</span></label>
            </fieldset>
            <label><span>客队</span><select id="rankingAwayTeam" required><option value="">选择球队</option>${options}</select></label>
            <button class="btn btn-primary" id="rankingSaveButton" type="submit">记入排位</button>
        </form>
    `;
}

function renderRankingMatches() {
    const matches = rankingData.matches || [];
    if (!matches.length) {
        return '<div class="ranking-matches-empty"><strong>暂无逐场赛果</strong><span>Excel 导入的是累计积分；从现在录入的胜平负会显示在这里。</span></div>';
    }
    const resultLabels = {home: '主胜', draw: '平局', away: '客胜'};
    return `<div class="ranking-match-list" aria-label="排位比赛结果">${matches.map(match => `
        <article class="ranking-match-ticket">
            <div class="ranking-ticket-team"><span>${escapeHtml(getScheduleTeamInitials(match.home_team_name))}</span><strong title="${escapeHtml(match.home_team_name)}">${escapeHtml(getCupTeamDisplayName(match.home_team_name))}</strong></div>
            <div class="ranking-ticket-result is-${escapeHtml(match.result)}">${escapeHtml(resultLabels[match.result] || '赛果')}</div>
            <div class="ranking-ticket-team is-away"><strong title="${escapeHtml(match.away_team_name)}">${escapeHtml(getCupTeamDisplayName(match.away_team_name))}</strong><span>${escapeHtml(getScheduleTeamInitials(match.away_team_name))}</span></div>
            ${canManageRankingMatches() ? `<button class="ranking-ticket-delete" type="button" onclick="deleteRankingMatch(${Number(match.id)})" aria-label="撤销 ${escapeHtml(match.home_team_name)} 对 ${escapeHtml(match.away_team_name)} 的比赛">×</button>` : ''}
        </article>
    `).join('')}</div>`;
}

function renderRankingCutoff() {
    const cutoff = Number(rankingData.cutoff_floor || 0);
    return `
        <div class="ranking-cutoff-row">
            <p>统计截止到排位贴<strong>${cutoff > 0 ? `第 ${cutoff} 楼` : '尚未填写'}</strong></p>
            ${canManageRankingMatches() ? `
                <label class="ranking-cutoff-editor capture-exclude">
                    <span>截止楼层</span>
                    <input id="rankingCutoffFloor" type="number" min="1" max="1000000" step="1" inputmode="numeric" value="${cutoff || ''}" placeholder="例如 128" onchange="saveRankingCutoff()">
                    <em id="rankingCutoffSaveState">修改后自动保存</em>
                </label>
            ` : ''}
        </div>
    `;
}

function renderRankingBoard() {
    const container = document.getElementById('ratingBoard');
    if (!container) return;
    const rows = rankingData.rows || [];
    if (!rows.length) {
        container.innerHTML = renderUiState({tone: 'empty', title: '排位积分尚未建立', message: '完成初始积分导入后，所有当前联赛球队会出现在这里。', compact: true});
        return;
    }
    container.innerHTML = `
        <section class="ranking-desk ${canManageRankingMatches() ? 'is-manager' : ''}">
            <div class="ranking-leaderboard-panel exportable-panel" data-export-view="rankings-HEIGO">
                <header class="ranking-board-head">
                    <div class="ranking-board-copy">
                        <span class="panel-kicker">HEIGO RATING DESK</span>
                        <h2>排位积分榜</h2>
                        <p>胜者取得败者赛前基础分的 10%；每完成一场，总分另加 ${formatRankingPoints(rankingData.appearance_bonus)}。</p>
                        ${renderRankingCutoff()}
                    </div>
                    <div class="ranking-board-meta">
                        <div class="ranking-export-actions capture-exclude">
                            <button class="btn btn-secondary competition-excel-btn" type="button" onclick="exportRankingExcel()">Excel表格</button>
                            <button class="btn btn-secondary competition-image-btn" type="button" onclick="saveCompetitionImage('rankings', 'HEIGO')">保存图片</button>
                        </div>
                        <div class="ranking-rule-strip" aria-label="排位规则"><span><small>初始基础分</small><strong>${formatRankingPoints(rankingData.initial_points)}</strong></span><span><small>胜负转移</small><strong>${Number(rankingData.transfer_rate || 0) * 100}%</strong></span><span><small>每场奖励</small><strong>+${formatRankingPoints(rankingData.appearance_bonus)}</strong></span></div>
                    </div>
                </header>
                <div class="ranking-table-wrap">
                    <table class="ranking-table">
                        <thead><tr><th>排名</th><th>球队</th><th>基础分</th><th>总分</th><th>场次</th><th>胜</th><th>负</th></tr></thead>
                        <tbody>${rows.map(row => `
                            <tr class="${Number(row.rank) <= 3 ? `is-podium is-rank-${Number(row.rank)}` : ''}">
                                <td><span class="ranking-position">${Number(row.rank)}</span></td>
                                <td><div class="ranking-team-cell"><span class="ranking-team-mark ${row.logo_path ? 'has-logo' : ''}">${getRankingTeamMark(row)}</span><div><strong>${escapeHtml(row.team_name)}</strong><small>${escapeHtml(row.level)}</small></div></div></td>
                                <td><strong class="ranking-base-points" title="${Number(row.base_points).toFixed(4)}">${formatRankingPoints(row.base_points)}</strong></td>
                                <td><strong class="ranking-total-points" title="${Number(row.total_points).toFixed(4)}">${formatRankingPoints(row.total_points)}</strong></td>
                                <td>${Number(row.matches)}</td><td>${Number(row.wins)}</td><td>${Number(row.losses)}</td>
                            </tr>
                        `).join('')}</tbody>
                    </table>
                </div>
                ${renderMobileRankingList(rows)}
            </div>
            <aside class="ranking-results-panel">
                ${renderRankingEntryForm()}
                <div class="ranking-results-heading"><div><span>RESULT LOG</span><strong>比赛结果</strong></div><b>${Number(rankingData.total_matches || 0)} 场</b></div>
                ${renderRankingMatches()}
            </aside>
        </section>
    `;
}

async function saveRankingCutoff() {
    if (!canManageRankingMatches() || rankingCutoffMutationBusy) return;
    const input = document.getElementById('rankingCutoffFloor');
    const state = document.getElementById('rankingCutoffSaveState');
    const raw = String(input?.value || '').trim();
    const cutoffFloor = raw === '' ? null : Number(raw);
    if (cutoffFloor !== null && (!Number.isInteger(cutoffFloor) || cutoffFloor < 1 || cutoffFloor > 1000000)) {
        if (state) state.textContent = '请填写有效楼层';
        input?.focus();
        return;
    }
    rankingCutoffMutationBusy = true;
    if (input) input.disabled = true;
    if (state) state.textContent = '保存中';
    try {
        const result = await workJsonRequest('/api/admin/rankings/cutoff', {
            method: 'PATCH', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({cutoff_floor: cutoffFloor}),
        });
        if (!result) return;
        if (!result.response.ok) {
            if (state) state.textContent = result.data.detail || '保存失败';
            return;
        }
        rankingData = result.data;
        renderRankingBoard();
    } finally {
        rankingCutoffMutationBusy = false;
        if (input?.isConnected) input.disabled = false;
    }
}

async function saveRankingMatch() {
    if (!canManageRankingMatches() || rankingMatchMutationBusy) return;
    const homeTeamId = Number(document.getElementById('rankingHomeTeam')?.value || 0);
    const awayTeamId = Number(document.getElementById('rankingAwayTeam')?.value || 0);
    const resultValue = document.querySelector('input[name="rankingResult"]:checked')?.value || '';
    if (!homeTeamId || !awayTeamId || !['home', 'draw', 'away'].includes(resultValue)) {
        showModal('比赛结果未填写完整', '请选择主客队，并选择主队胜、平局或客队胜。');
        return;
    }
    if (homeTeamId === awayTeamId) {
        showModal('球队选择重复', '排位比赛双方不能是同一支球队。');
        return;
    }
    rankingMatchMutationBusy = true;
    const button = document.getElementById('rankingSaveButton');
    if (button) { button.disabled = true; button.textContent = '正在计算…'; }
    try {
        const result = await workJsonRequest('/api/admin/rankings/matches', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({home_team_id: homeTeamId, away_team_id: awayTeamId, result: resultValue}),
        });
        if (!result) return;
        if (!result.response.ok) {
            showModal('录入失败', escapeHtml(result.data.detail || '排位比赛保存失败。'));
            return;
        }
        rankingData = result.data;
        renderRankingBoard();
    } finally {
        rankingMatchMutationBusy = false;
    }
}

async function deleteRankingMatch(matchId) {
    if (!canManageRankingMatches() || rankingMatchMutationBusy) return;
    const match = (rankingData.matches || []).find(item => Number(item.id) === Number(matchId));
    const resultLabel = {home: '主队胜', draw: '平局', away: '客队胜'}[match?.result] || '已录赛果';
    if (!match || !await showConfirmDialog({title: '撤销排位比赛', message: `撤销 ${match.home_team_name} vs ${match.away_team_name}（${resultLabel}）后，后续积分会按比赛顺序重新计算。`, confirmLabel: '确认撤销', danger: true})) return;
    rankingMatchMutationBusy = true;
    try {
        const result = await workJsonRequest(`/api/admin/rankings/matches/${Number(matchId)}`, {method: 'DELETE'});
        if (!result) return;
        if (!result.response.ok) {
            showModal('撤销失败', escapeHtml(result.data.detail || '排位比赛撤销失败。'));
            return;
        }
        rankingData = result.data;
        renderRankingBoard();
    } finally {
        rankingMatchMutationBusy = false;
    }
}

function setCompetitionLevel(level) {
    currentCompetitionLevel = [...LEAGUE_COMPETITION_LEVELS, ...Object.keys(CUP_COMPETITIONS)].includes(level) ? level : '超级';
    if (['playerRankings', 'suspensions'].includes(currentCompetitionSubtab) && !LEAGUE_COMPETITION_LEVELS.includes(currentCompetitionLevel)) {
        currentCompetitionLevel = '超级';
    }
    if (isCupCompetitionLevel()) {
        if (currentCompetitionSubtab === 'schedule') currentCupPhase = 'group';
        else if (!getCurrentCupConfig()?.groupCount) currentCupPhase = 'knockout';
    }
    syncCompetitionLevelTabs({revealActive: true});
    syncCupPhaseTabs();
    renderCompetitionAdminActions();
    renderCompetitionWorkPanel();
    renderCompetitionDataStatus();
    if (currentCompetitionWorkFilter !== 'all') {
        const summary = getCompetitionWorkSummary();
        const roundSelect = document.getElementById('scheduleRoundSelect');
        if (summary && roundSelect) roundSelect.value = String(summary.round_start);
    }
    const cacheKey = getCompetitionSectionCacheKey(currentCompetitionSubtab);
    if (competitionLoadedSections.has(cacheKey)) {
        applyCompetitionSectionPayload(currentCompetitionSubtab, competitionSectionDataCache.get(cacheKey));
        renderCompetitionSection(currentCompetitionSubtab);
    } else {
        renderCompetitionSectionLoading(currentCompetitionSubtab);
        loadCompetitionSection(currentCompetitionSubtab);
    }
    if (typeof syncAppHistory === 'function') {
        syncAppHistory('replace');
    }
}

function updateCompetitionSelectorOverflow(options = {}) {
    const selector = document.getElementById('competitionSelector');
    const viewport = document.getElementById('competitionSelectorViewport');
    const hint = document.getElementById('competitionSelectorHint');
    if (!selector || !viewport) return;

    if (viewport.dataset.overflowBound !== 'true') {
        viewport.dataset.overflowBound = 'true';
        viewport.addEventListener('scroll', () => updateCompetitionSelectorOverflow(), {passive: true});
        window.addEventListener('resize', () => updateCompetitionSelectorOverflow(), {passive: true});
    }

    if (options.revealActive === true && isMobileViewport()) {
        const active = viewport.querySelector('.competition-level-tab.active');
        if (active) {
            const viewportRect = viewport.getBoundingClientRect();
            const activeRect = active.getBoundingClientRect();
            const targetLeft = viewport.scrollLeft + activeRect.left - viewportRect.left - (viewport.clientWidth - activeRect.width) / 2;
            const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
            viewport.scrollTo({left: Math.max(0, targetLeft), behavior: reducedMotion ? 'auto' : 'smooth'});
        }
    }

    window.requestAnimationFrame(() => {
        const hasOverflow = viewport.scrollWidth > viewport.clientWidth + 2;
        const atStart = viewport.scrollLeft <= 2;
        const atEnd = viewport.scrollLeft + viewport.clientWidth >= viewport.scrollWidth - 2;
        selector.classList.toggle('has-overflow', hasOverflow);
        selector.classList.toggle('is-at-start', atStart);
        selector.classList.toggle('is-at-end', atEnd);
        if (hint) hint.textContent = hasOverflow && !atEnd ? '横滑查看更多' : '联赛与杯赛';
    });
}

function syncCompetitionLevelTabs(options = {}) {
    const hideCupLevels = ['playerRankings', 'suspensions'].includes(currentCompetitionSubtab);
    [
        ['competitionLevelSuper', '超级'],
        ['competitionLevelFirst', '甲级'],
        ['competitionLevelSecond', '乙级'],
        ['competitionLevelChampionsCup', '冠军杯'],
        ['competitionLevelLeagueCup', '联盟杯'],
        ['competitionLevelWumingjianCup', '无铭剑杯'],
    ].forEach(([id, level]) => {
        const button = document.getElementById(id);
        if (!button) return;
        const active = currentCompetitionLevel === level;
        button.classList.toggle('active', active);
        button.setAttribute('aria-selected', active ? 'true' : 'false');
        button.tabIndex = active ? 0 : -1;
    });
    const cupGroup = document.getElementById('competitionCupGroup');
    if (cupGroup) cupGroup.hidden = hideCupLevels;
    updateCompetitionSelectorOverflow(options);
    syncCupPhaseTabs();
}

function hasCompetitionWorkAccess() {
    return Boolean(canManageSchedule || canManageCupStandings || canManageSuspensions);
}

function hasLeagueCompetitionWorkAccess() {
    return Boolean(canManageSchedule || canManageSuspensions);
}

function canManageCurrentCompetitionSchedule() {
    if (!canManageSchedule) return false;
    if (isCupCompetitionLevel()) return true;
    const summary = getCompetitionWorkSummary();
    return Boolean(isCompetitionWorkAdmin() || summary?.is_my_schedule_task);
}

function canManageCurrentCupStandings() {
    return Boolean(isCupCompetitionLevel() && canManageCupStandings);
}

function canManageCurrentCompetitionSuspensions() {
    if (!canManageSuspensions || isCupCompetitionLevel()) return false;
    const summary = getCompetitionWorkSummary();
    return Boolean(isCompetitionWorkAdmin() || summary?.is_my_suspension_task);
}

function getCompetitionWorkSummary(level = currentCompetitionLevel) {
    return (competitionWorkData?.levels || []).find(item => item.level === level) || null;
}

function competitionWorkTaskMatchesFilter(task, filter = currentCompetitionWorkFilter) {
    const codes = task?.issue_codes || [];
    if (filter === 'missing_result') return codes.includes('missing_result');
    if (filter === 'missing_events') return codes.includes('missing_events');
    if (filter === 'invalid') return codes.some(code => String(code).startsWith('invalid_'));
    return true;
}

function getCompetitionWorkTasks(filter = currentCompetitionWorkFilter) {
    const summary = getCompetitionWorkSummary();
    return (summary?.tasks || []).filter(task => competitionWorkTaskMatchesFilter(task, filter));
}

function getCompetitionWorkVisibleMatchIds() {
    if (currentCompetitionWorkFilter === 'all') return null;
    return new Set(getCompetitionWorkTasks().map(task => Number(task.match_id)).filter(Boolean));
}

function getCompetitionWorkTaskForMatch(matchId) {
    return (getCompetitionWorkSummary()?.tasks || []).find(task => Number(task.match_id) === Number(matchId)) || null;
}

function getCompetitionWorkMatchClass(matchId) {
    const task = getCompetitionWorkTaskForMatch(matchId);
    const classes = [];
    if (task) classes.push('has-work-issue');
    if (Number(currentCompetitionWorkTargetMatchId) === Number(matchId)) classes.push('is-work-target');
    return classes.join(' ');
}

function renderCompetitionWorkMatchIssue(matchId) {
    const task = getCompetitionWorkTaskForMatch(matchId);
    if (!task) return '';
    const invalid = (task.issue_codes || []).some(code => String(code).startsWith('invalid_'));
    return `<div class="schedule-work-issue ${invalid ? 'is-invalid' : ''}">${escapeHtml((task.issue_messages || []).join('；'))}</div>`;
}

function getCompetitionWorkStatusLabel(summary) {
    if (summary.workflow_status_label) return summary.workflow_status_label;
    if (summary.completed) return '本轮已完成';
    if (summary.changed_after_completion) return '完成后有修改，需重新确认';
    if (summary.completion_ready) return '可以提交复核';
    return '处理中';
}

function isCompetitionWorkAdmin() {
    return Boolean(typeof workspaceSessionState !== 'undefined' && workspaceSessionState?.identity?.is_full_admin);
}

function getCompetitionWorkAccountLabel() {
    const identity = typeof workspaceSessionState !== 'undefined' ? workspaceSessionState?.identity : null;
    return identity?.display_name || identity?.username || '工作账号';
}

function renderCompetitionAccountMenu() {
    return `
        <details class="competition-account-menu">
            <summary aria-label="打开工作账号菜单">
                <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3"/><path d="M5.5 19a6.5 6.5 0 0 1 13 0"/></svg>
                <span class="competition-account-label">${escapeHtml(getCompetitionWorkAccountLabel())}</span>
                <span class="competition-account-chevron" aria-hidden="true">⌄</span>
            </summary>
            <div>
                <button type="button" onclick="loadCompetitionData({force: true}); this.closest('details')?.removeAttribute('open')">刷新数据</button>
                <button type="button" onclick="logoutCurrentWorkAccount()">退出登录</button>
            </div>
        </details>
    `;
}

function getCompetitionWorkIssueLabels(summary) {
    const labels = [];
    if (summary.changed_after_completion) labels.push('完成后有修改');
    if (summary.changed_after_submission) labels.push('提交后有修改');
    if (Number(summary.missing_result_count || 0) > 0) labels.push(`${Number(summary.missing_result_count)} 场待录比分`);
    if (Number(summary.missing_event_count || 0) > 0) labels.push(`${Number(summary.missing_event_count)} 场待补事件`);
    if (Number(summary.invalid_count || 0) > 0) labels.push(`${Number(summary.invalid_count)} 项数据异常`);
    if (!summary.suspension_confirmed) labels.push('伤停待确认');
    return labels.length ? labels : [summary.completed ? '本轮已完成' : '本轮数据已齐'];
}

function toggleCompetitionWorkPanel(forceExpanded = null) {
    competitionWorkPanelExpanded = forceExpanded === null
        ? !competitionWorkPanelExpanded
        : Boolean(forceExpanded);
    renderCompetitionWorkPanel();
}

function renderCompetitionWorkHistory(summary) {
    const history = summary.history || [];
    if (!history.length) return '';
    return `
        <details class="competition-work-history">
            <summary>工作记录 <span>${history.length}</span></summary>
            <div>${history.slice(0, 6).map(row => `
                <div class="competition-work-history-row">
                    <strong>${escapeHtml(row.action_label || row.action)}</strong>
                    <span>${escapeHtml(row.operator_display_name || '-')}</span>
                    <time>${row.created_at ? new Date(row.created_at).toLocaleString() : '-'}</time>
                    ${row.detail ? `<em>${escapeHtml(row.detail)}</em>` : ''}
                </div>
            `).join('')}</div>
        </details>
    `;
}

function renderCompetitionWorkTaskPreview(tasks) {
    if (currentCompetitionWorkFilter === 'all') return '';
    if (!tasks.length) {
        return '<div class="competition-work-empty">当前筛选下没有待处理比赛。</div>';
    }
    return `
        <div class="competition-work-task-list">
            ${tasks.slice(0, 5).map(task => `
                <button type="button" class="competition-work-task" onclick="focusCompetitionWorkMatch(${Number(task.match_id)})">
                    <span>第 ${Number(task.round_no)} 轮</span>
                    <strong>${escapeHtml(task.home_team_name)} vs ${escapeHtml(task.away_team_name)}</strong>
                    <em>${escapeHtml((task.issue_messages || []).join('；'))}</em>
                </button>
            `).join('')}
            ${tasks.length > 5 ? `<span class="competition-work-more">另有 ${tasks.length - 5} 场待处理</span>` : ''}
        </div>
    `;
}

function renderCompetitionWorkPanel() {
    const container = document.getElementById('competitionWorkPanel');
    if (!container) return;
    if (['rating', 'archives'].includes(currentCompetitionSubtab) || !hasLeagueCompetitionWorkAccess() || isCupCompetitionLevel()) {
        container.hidden = true;
        container.innerHTML = '';
        return;
    }
    const summary = getCompetitionWorkSummary();
    container.hidden = false;
    if (!summary) {
        container.innerHTML = competitionWorkLoadError
            ? `<div class="competition-work-warning">${escapeHtml(competitionWorkLoadError)} <button class="btn btn-secondary" type="button" onclick="refreshCompetitionWorkSummary()">重试</button></div>`
            : '<div class="competition-work-loading">正在读取当前轮次工作状态...</div>';
        return;
    }
    const tasks = getCompetitionWorkTasks();
    const isFullAdmin = isCompetitionWorkAdmin();
    const issueLabels = getCompetitionWorkIssueLabels(summary);
    container.innerHTML = `
        <div class="competition-work-summary-bar">
            <div class="competition-work-summary-title">
                <span class="competition-work-signal" aria-hidden="true"></span>
                <div>
                    <span class="competition-work-kicker">工作轮次</span>
                    <strong>${escapeHtml(summary.level)} · ${escapeHtml(summary.round_label)}</strong>
                </div>
            </div>
            <div class="competition-work-summary-issues" aria-label="当前待办">${issueLabels.map((label, index) => `<span class="${index === 0 && issueLabels.length === 1 && (summary.completed || summary.completion_ready) ? 'is-clear' : ''}">${escapeHtml(label)}</span>`).join('')}</div>
            <span class="competition-work-status is-${escapeHtml(summary.workflow_status || 'in_progress')} ${summary.completed ? 'is-complete' : summary.changed_after_completion ? 'is-warning' : ''}">${escapeHtml(getCompetitionWorkStatusLabel(summary))}</span>
            <div class="competition-work-summary-actions">
                ${renderCompetitionAccountMenu()}
                <button class="competition-work-toggle" type="button" aria-label="${competitionWorkPanelExpanded ? '收起工作台' : '展开工作台'}" aria-expanded="${competitionWorkPanelExpanded ? 'true' : 'false'}" onclick="toggleCompetitionWorkPanel()">
                    <span>${competitionWorkPanelExpanded ? '收起工作台' : '展开工作台'}</span>
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>
                </button>
            </div>
        </div>
        <div class="competition-work-details" ${competitionWorkPanelExpanded ? '' : 'hidden'}>
            <div class="competition-work-owner-grid">
                <div><span>赛程与比赛事件</span><strong>${escapeHtml(summary.schedule_display_name || '尚未任命')}</strong>${summary.is_my_schedule_task ? '<em>我的职责</em>' : ''}</div>
                <div><span>伤停</span><strong>${escapeHtml(summary.suspension_display_name || '尚未任命')}</strong>${summary.is_my_suspension_task ? '<em>我的职责</em>' : ''}</div>
                ${summary.submitted_at ? `<span>提交于 ${escapeHtml(new Date(summary.submitted_at).toLocaleString())}</span>` : ''}
            </div>
            <div class="competition-work-progress">
                <button type="button" class="competition-work-metric ${currentCompetitionWorkFilter === 'missing_result' ? 'active' : ''}" onclick="openCompetitionWorkQueue('missing_result')">
                    <span>比分</span><strong>${Number(summary.result_ready_count)}/${Number(summary.total_matches)}</strong><em>${Number(summary.missing_result_count)} 场待录</em>
                </button>
                <button type="button" class="competition-work-metric ${currentCompetitionWorkFilter === 'missing_events' ? 'active' : ''}" onclick="openCompetitionWorkQueue('missing_events')">
                    <span>球员事件</span><strong>${Number(summary.event_ready_count)}/${Number(summary.total_matches)}</strong><em>${Number(summary.missing_event_count)} 场待补</em>
                </button>
                ${Number(summary.invalid_count || 0) > 0 ? `<button type="button" class="competition-work-metric ${currentCompetitionWorkFilter === 'invalid' ? 'active' : ''}" onclick="openCompetitionWorkQueue('invalid')">
                    <span>数据异常</span><strong>${Number(summary.invalid_count)}</strong><em>需要修正</em>
                </button>` : ''}
                <button type="button" class="competition-work-metric ${summary.suspension_confirmed ? 'is-complete' : ''}" onclick="showCompetitionSubtab('suspensions')">
                    <span>伤停</span><strong>${summary.suspension_confirmed ? '已确认' : '待确认'}</strong><em>${escapeHtml(summary.suspension_confirmed_by || '尚未核对')}</em>
                </button>
            </div>
            <div class="competition-work-actions">
                ${currentCompetitionWorkFilter !== 'all' ? '<button class="btn btn-secondary" type="button" onclick="openCompetitionWorkQueue(\'all\')">显示本轮全部比赛</button>' : ''}
                ${isFullAdmin ? '<button class="btn btn-secondary" type="button" onclick="showCompetitionAssignmentDialog()">设置级别职责</button>' : ''}
                ${summary.can_confirm_suspensions ? `<button class="btn btn-secondary" type="button" onclick="updateCompetitionSuspensionConfirmation(${summary.suspension_confirmed ? 'false' : 'true'})">${summary.suspension_confirmed ? '取消伤停确认' : '确认本轮伤停'}</button>` : ''}
                ${summary.can_submit ? '<button class="btn btn-primary" type="button" onclick="submitCompetitionRoundWork()">提交复核</button>' : ''}
                ${summary.can_review ? '<button class="btn btn-secondary" type="button" onclick="showCompetitionReviewDialog(false)">退回修改</button><button class="btn btn-primary" type="button" onclick="showCompetitionReviewDialog(true)">复核通过</button>' : ''}
                ${summary.completed ? '<button class="btn btn-primary" type="button" disabled>本轮已完成</button>' : ''}
            </div>
            ${summary.changed_after_completion ? '<div class="competition-work-warning">本轮在完成后又发生了数据修改，请重新检查并再次提交复核。</div>' : ''}
            ${summary.changed_after_submission ? '<div class="competition-work-warning">提交复核后比赛数据发生变化，任务已自动退回处理中。</div>' : ''}
            ${summary.note ? `<div class="competition-work-note"><strong>工作备注</strong><span>${escapeHtml(summary.note)}</span></div>` : ''}
            ${renderCompetitionWorkTaskPreview(tasks)}
            ${renderCompetitionWorkHistory(summary)}
        </div>
    `;
}

async function loadCompetitionWorkSummary(options = {}) {
    if (!hasLeagueCompetitionWorkAccess()) {
        competitionWorkData = null;
        renderCompetitionWorkPanel();
        return null;
    }
    if (competitionWorkData && options.force !== true) {
        renderCompetitionWorkPanel();
        return competitionWorkData;
    }
    if (competitionWorkLoadPromise && options.force !== true) return competitionWorkLoadPromise;
    competitionWorkLoadError = '';
    renderCompetitionWorkPanel();
    const shouldRenderBoards = options.renderBoards !== false;
    competitionWorkLoadPromise = fetchWithTimeout('/api/workspace/competition-work', {credentials: 'same-origin'})
        .then(async response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            competitionWorkData = await response.json();
            competitionWorkLoadError = '';
            renderCompetitionWorkPanel();
            renderCompetitionAdminActions();
            if (shouldRenderBoards && currentCompetitionSubtab === 'schedule') renderScheduleBoard();
            if (shouldRenderBoards && currentCompetitionSubtab === 'suspensions') renderSuspensionsBoard();
            return competitionWorkData;
        })
        .catch(error => {
            console.error('数据统计工作状态加载失败:', error);
            competitionWorkData = null;
            competitionWorkLoadError = '当前轮次工作状态加载失败。';
            renderCompetitionWorkPanel();
            return null;
        })
        .finally(() => {
            competitionWorkLoadPromise = null;
        });
    return competitionWorkLoadPromise;
}

async function refreshCompetitionWorkSummary(options = {}) {
    return loadCompetitionWorkSummary({...options, force: true});
}

function focusCompetitionWorkMatch(matchId) {
    currentCompetitionWorkTargetMatchId = Number(matchId) || null;
    const match = findScheduleMatchById(currentCompetitionWorkTargetMatchId);
    if (match) {
        const roundSelect = document.getElementById('scheduleRoundSelect');
        if (roundSelect) roundSelect.value = String(getRoundPairStart(match.round_no));
        renderScheduleBoard();
    }
    window.requestAnimationFrame(() => {
        const target = document.querySelector(`[data-match-id="${currentCompetitionWorkTargetMatchId}"]`);
        target?.scrollIntoView({behavior: 'smooth', block: 'center'});
        target?.classList.add('is-work-target');
        if (isMobileViewport() && canManageCurrentCompetitionSchedule() && currentCompetitionWorkTargetMatchId) {
            openMatchEventEditor(currentCompetitionWorkTargetMatchId);
        }
    });
}

function openCompetitionWorkQueue(filter = 'all') {
    const summary = getCompetitionWorkSummary();
    if (!summary) return;
    currentCompetitionWorkFilter = ['missing_result', 'missing_events', 'invalid'].includes(filter) ? filter : 'all';
    currentCompetitionWorkTargetMatchId = getCompetitionWorkTasks()[0]?.match_id || null;
    showCompetitionSubtab('schedule');
    const roundSelect = document.getElementById('scheduleRoundSelect');
    if (roundSelect) roundSelect.value = String(summary.round_start);
    renderScheduleBoard();
    renderCompetitionWorkPanel();
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
    if (currentCompetitionWorkTargetMatchId) focusCompetitionWorkMatch(currentCompetitionWorkTargetMatchId);
}

async function updateCompetitionSuspensionConfirmation(confirmed) {
    const summary = getCompetitionWorkSummary();
    if (!summary || !summary.can_confirm_suspensions) return;
    let response;
    try {
        response = await fetchWithTimeout(`/api/workspace/competition-work/${encodeURIComponent(summary.level)}/${summary.round_start}/suspensions`, {
            method: 'PATCH',
            credentials: 'same-origin',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({confirmed: Boolean(confirmed)}),
        });
    } catch (error) {
        showModal('伤停确认失败', '网络连接失败，请稍后重试。');
        return;
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        showModal('伤停确认失败', escapeHtml(data.detail || '暂时无法更新伤停确认状态。'));
        return;
    }
    competitionWorkData = data;
    renderCompetitionWorkPanel();
    if (typeof loadWorkspaceDashboard === 'function') loadWorkspaceDashboard({force: true});
}

function invalidateCompetitionAssignableAccounts() {
    competitionAssignableAccounts = [];
}

async function loadCompetitionAssignableAccounts(options = {}) {
    if (competitionAssignableAccounts.length && options.force !== true) return competitionAssignableAccounts;
    const response = await fetchWithTimeout('/api/workspace/accounts', {credentials: 'same-origin'});
    if (!response.ok) throw new Error('负责人列表加载失败');
    const data = await response.json();
    competitionAssignableAccounts = (data.items || []).filter(item => (
        item.is_active
        && (item.capabilities || []).some(capability => capability !== 'coach_profile.write_self')
    ));
    return competitionAssignableAccounts;
}

function renderCompetitionResponsibilityOptions(accounts, capability, currentPrincipalId, accountLabel) {
    const eligible = accounts.filter(item => (item.capabilities || []).includes(capability));
    const ineligible = accounts.filter(item => !(item.capabilities || []).includes(capability));
    const permissionLabel = capability === 'schedule.write' ? '赛程权限' : '伤停权限';
    const renderOption = (item, disabled = false) => `
        <option value="${escapeHtml(item.principal_id)}" ${item.principal_id === currentPrincipalId ? 'selected' : ''} ${disabled ? 'disabled' : ''}>
            ${escapeHtml(item.display_name)} · ${escapeHtml(accountLabel(item))}${disabled ? ` · 需先授予${permissionLabel}` : ''}
        </option>
    `;
    return `
        <optgroup label="可任命账号">${eligible.map(item => renderOption(item)).join('')}</optgroup>
        ${ineligible.length ? `<optgroup label="其他工作账号（缺少当前权限）">${ineligible.map(item => renderOption(item, true)).join('')}</optgroup>` : ''}
    `;
}

async function showCompetitionAssignmentDialog() {
    const summary = getCompetitionWorkSummary();
    if (!summary || !isCompetitionWorkAdmin()) return;
    try {
        const accounts = await loadCompetitionAssignableAccounts({force: true});
        const accountLabel = item => item.account_type === 'coach_worker' ? '教练工作账号' : item.account_type === 'administrator' ? '管理员' : '工作人员';
        showModal(`设置 ${escapeHtml(summary.level)} 职责`, `
            <div class="competition-work-dialog">
                <p>任命后将负责 ${escapeHtml(summary.level)} 当前及后续全部轮次。所有启用的工作账号都会显示；缺少对应权限的账号需先在“人员与权限”中授权。</p>
                <label class="form-group"><span>赛程与比赛事件负责人</span><select id="competitionScheduleResponsible">
                    <option value="">尚未任命</option>
                    ${renderCompetitionResponsibilityOptions(accounts, 'schedule.write', summary.schedule_principal_id, accountLabel)}
                </select></label>
                <label class="form-group"><span>伤停负责人</span><select id="competitionSuspensionResponsible">
                    <option value="">尚未任命</option>
                    ${renderCompetitionResponsibilityOptions(accounts, 'suspensions.write', summary.suspension_principal_id, accountLabel)}
                </select></label>
                <div class="modal-action-row"><button class="btn btn-secondary" type="button" onclick="closeModal()">取消</button><button class="btn btn-primary" type="button" onclick="saveCompetitionAssignment()">保存职责</button></div>
            </div>
        `);
    } catch (error) {
        showModal('负责人加载失败', '暂时无法读取可分配账号，请稍后重试。');
    }
}

async function saveCompetitionAssignment() {
    const summary = getCompetitionWorkSummary();
    if (!summary) return;
    const schedulePrincipal = document.getElementById('competitionScheduleResponsible')?.value || null;
    const suspensionPrincipal = document.getElementById('competitionSuspensionResponsible')?.value || null;
    const response = await fetchWithTimeout(`/api/workspace/competition-responsibilities/${encodeURIComponent(summary.level)}`, {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({schedule_principal_id: schedulePrincipal, suspension_principal_id: suspensionPrincipal}),
    }).catch(() => null);
    const data = response ? await response.json().catch(() => ({})) : {};
    if (!response?.ok) {
        showModal('职责设置失败', escapeHtml(data.detail || '网络连接失败，请稍后重试。'));
        return;
    }
    closeModal();
    competitionWorkData = data;
    renderCompetitionWorkPanel();
    if (typeof loadWorkspaceDashboard === 'function') loadWorkspaceDashboard({force: true});
}

async function submitCompetitionRoundWork() {
    const summary = getCompetitionWorkSummary();
    if (!summary || !summary.can_submit) return;
    let response;
    try {
        response = await fetchWithTimeout(`/api/workspace/competition-work/${encodeURIComponent(summary.level)}/${summary.round_start}/submit`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({note: summary.note || null}),
        });
    } catch (error) {
        showModal('提交失败', '网络连接失败，请稍后重试。');
        return;
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        showModal('暂时无法提交', escapeHtml(data.detail || '请先处理当前轮次的未完成项目。'));
        return;
    }
    competitionWorkData = data;
    renderCompetitionWorkPanel();
    showSuccessToast(`${summary.level} ${summary.round_label} 已提交复核`);
    if (typeof loadWorkspaceDashboard === 'function') loadWorkspaceDashboard({force: true});
}

function showCompetitionReviewDialog(approved) {
    const summary = getCompetitionWorkSummary();
    if (!summary?.can_review) return;
    showModal(approved ? '确认复核通过' : '退回修改', `
        <div class="competition-work-dialog">
            <p>${escapeHtml(summary.level)} · ${escapeHtml(summary.round_label)} · 负责人 ${escapeHtml(summary.assignee_display_name || '-')}</p>
            <label class="form-group"><span>${approved ? '复核备注（可选）' : '退回原因'}</span><textarea id="competitionWorkReviewNote" rows="3" placeholder="${approved ? '填写复核说明' : '说明需要修改的内容'}"></textarea></label>
            <div class="modal-action-row"><button class="btn btn-secondary" type="button" onclick="closeModal()">取消</button><button class="btn ${approved ? 'btn-primary' : 'btn-danger'}" type="button" onclick="reviewCompetitionRoundWork(${approved ? 'true' : 'false'})">${approved ? '确认通过' : '确认退回'}</button></div>
        </div>
    `);
}

async function reviewCompetitionRoundWork(approved) {
    const summary = getCompetitionWorkSummary();
    if (!summary?.can_review) return;
    const noteInput = document.getElementById('competitionWorkReviewNote');
    const note = noteInput?.value || '';
    if (!approved && !note.trim()) {
        noteInput?.focus();
        return;
    }
    const response = await fetchWithTimeout(`/api/workspace/competition-work/${encodeURIComponent(summary.level)}/${summary.round_start}/review`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({approved: Boolean(approved), note: note || null}),
    }).catch(() => null);
    const data = response ? await response.json().catch(() => ({})) : {};
    if (!response?.ok) {
        showModal('复核失败', escapeHtml(data.detail || '网络连接失败，请稍后重试。'));
        return;
    }
    closeModal();
    competitionWorkData = data;
    renderCompetitionWorkPanel();
    showUiToast(approved ? '本轮复核已通过' : '任务已退回负责人修改', approved ? 'success' : 'warning');
    if (typeof loadWorkspaceDashboard === 'function') loadWorkspaceDashboard({force: true});
}

async function completeCompetitionRoundWork() {
    return submitCompetitionRoundWork();
}

function renderCompetitionAdminActions() {
    const container = document.getElementById('competitionAdminActions');
    if (!container) return;
    if (['rating', 'archives'].includes(currentCompetitionSubtab)) {
        container.innerHTML = '';
        return;
    }
    const cupConfig = getCurrentCupConfig();
    if (!hasCompetitionWorkAccess()) {
        container.innerHTML = '';
        return;
    }
    if (!cupConfig) {
        container.innerHTML = '';
        return;
    }
    container.innerHTML = `
        ${canManageSchedule && cupConfig && currentCupPhase === 'knockout' ? `<button class="btn btn-secondary" id="initializeCupBracketButton" type="button" onclick="initializeCupBracket()">${escapeHtml(cupConfig.initializeLabel)}</button>` : ''}
        ${renderCompetitionAccountMenu()}
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

function getStandingsPredictionSummary(level) {
    return (standingsData.prediction_summaries || []).find(item => item.level === level) || null;
}

function formatPredictionProbability(value) {
    const percent = Math.round(Math.max(0, Math.min(1, Number(value || 0))) * 100);
    return `${percent}%`;
}

function getStandingPredictionTone(row, level) {
    if (Number(row.title_race_probability || 0) >= 0.3) return 'is-title-race';
    if (level !== '超级' && Number(row.promotion_probability || 0) >= 0.45) return 'is-promotion-race';
    if (Number(row.relegation_probability || 0) >= 0.45) return 'is-relegation-race';
    return 'is-neutral';
}

function getStandingPredictionRail(row, total) {
    const count = Math.max(1, Number(total || 1));
    const denominator = Math.max(1, count - 1);
    const minimum = Math.max(1, Math.min(count, Number(row.predicted_rank_min || row.rank || 1)));
    const maximum = Math.max(minimum, Math.min(count, Number(row.predicted_rank_max || row.rank || count)));
    const predicted = Math.max(minimum, Math.min(maximum, Number(row.predicted_rank || row.rank || minimum)));
    return {
        start: ((minimum - 1) / denominator) * 100,
        end: ((maximum - 1) / denominator) * 100,
        point: ((predicted - 1) / denominator) * 100,
    };
}

function renderStandingPrediction(row, rows, level, options = {}) {
    const total = Array.isArray(rows) ? rows.length : 0;
    const predicted = Number(row.predicted_rank || row.rank || 0);
    const minimum = Number(row.predicted_rank_min || predicted);
    const maximum = Number(row.predicted_rank_max || predicted);
    const rail = getStandingPredictionRail(row, total);
    const tone = getStandingPredictionTone(row, level);
    const probabilityLabel = level === '超级'
        ? `争冠 ${formatPredictionProbability(row.title_race_probability)} · 降级 ${formatPredictionProbability(row.relegation_probability)}`
        : `升级 ${formatPredictionProbability(row.promotion_probability)} · 降级 ${formatPredictionProbability(row.relegation_probability)}`;
    const title = `${row.prediction_label || '排名观察'}；最可能第 ${predicted} 名；90% 预测区间第 ${minimum}–${maximum} 名；${probabilityLabel}`;
    return `
        <span class="standing-prediction ${tone} ${options.mobile ? 'is-mobile' : ''}" title="${escapeHtml(title)}" aria-label="${escapeHtml(title)}">
            <span class="standing-prediction-copy"><strong>${predicted}</strong><small>${minimum === maximum ? `第 ${minimum} 名` : `${minimum}–${maximum}`}</small></span>
            <span class="standing-prediction-rail" style="--prediction-start:${rail.start.toFixed(2)}%;--prediction-end:${rail.end.toFixed(2)}%;--prediction-point:${rail.point.toFixed(2)}%" aria-hidden="true"><i></i><b></b></span>
            ${options.mobile ? `<span class="standing-prediction-context"><em>${escapeHtml(row.prediction_label || '排名观察')}</em><small>${escapeHtml(probabilityLabel)}</small></span>` : ''}
        </span>
    `;
}

function renderStandingsPredictionSummary(level) {
    const summary = getStandingsPredictionSummary(level);
    if (!summary) return '';
    if (!Number(summary.total_match_count || 0)) {
        return '<div class="standings-prediction-summary is-pending"><strong>排名预测待启动</strong><span>完整赛程导入后，将按真实对阵持续模拟并逐轮收束。</span></div>';
    }
    const progress = Math.round(Number(summary.progress || 0) * 100);
    const simulationText = Number(summary.simulations || 0) > 0 ? `${Number(summary.simulations).toLocaleString('zh-CN')} 次赛季模拟` : '最终排名已确定';
    return `
        <div class="standings-prediction-summary is-${escapeHtml(summary.phase || 'early')}">
            <strong>${escapeHtml(summary.phase_label || '排名预测')}</strong>
            <span>赛程完成 ${progress}% · ${escapeHtml(simulationText)} · ${escapeHtml(summary.interval_label || '90%预测区间')}</span>
        </div>
    `;
}

function setMobileStandingsScope(scope) {
    currentMobileStandingsScope = ['total', 'home', 'away'].includes(scope) ? scope : 'total';
    renderStandingsBoard();
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
}

function toggleMobileStandingRow(level, teamName) {
    const key = `${level}:${teamName}`;
    if (expandedMobileStandingRows.has(key)) {
        expandedMobileStandingRows.delete(key);
    } else {
        expandedMobileStandingRows.add(key);
    }
    renderStandingsBoard();
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
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
                const expandedKey = `${level}:${row.team_name || ''}`;
                const expanded = expandedMobileStandingRows.has(expandedKey);
                const detailsId = `mobileStandingDetails-${level}-${Number(row.rank || 0)}`;
                return `
                    <article class="mobile-standings-card ${zoneClass} ${expanded ? 'is-expanded' : ''}">
                        <button class="mobile-standings-row-toggle" type="button" onclick="toggleMobileStandingRow(${htmlJsString(level)}, ${htmlJsString(row.team_name || '')})" aria-expanded="${expanded ? 'true' : 'false'}" aria-controls="${detailsId}" aria-label="${expanded ? '收起' : '展开'} ${escapeHtml(row.team_name || '-')} 积分榜详情">
                            <span class="mobile-standings-rank">${row.rank}</span>
                            <span class="mobile-standings-team"><strong class="mobile-standings-team-name">${escapeHtml(row.team_name || '-')}</strong><small class="mobile-standings-coach">${escapeHtml(row.manager || '待定')}</small></span>
                            <span class="mobile-standings-quick-stats">
                                <span><small>场</small><b>${scope.played(row)}</b></span>
                                <span><small>净</small><b>${goalDifference > 0 ? '+' : ''}${goalDifference}</b></span>
                                <strong>${points}<small>分</small></strong>
                            </span>
                            <span class="mobile-standings-chevron" aria-hidden="true"><svg viewBox="0 0 24 24" focusable="false"><path d="m7 10 5 5 5-5"/></svg></span>
                        </button>
                        ${expanded ? `<div class="mobile-standings-details" id="${detailsId}"><div class="mobile-standings-strip">
                                <span><em>胜</em>${wins}</span>
                                <span><em>平</em>${draws}</span>
                                <span><em>负</em>${losses}</span>
                                <span><em>进</em>${goalsFor}</span>
                                <span><em>失</em>${goalsAgainst}</span>
                                <span><em>胜率</em>${scope.rate(row)}</span>
                            </div><div class="mobile-standing-prediction-row"><span>预测排名</span>${renderStandingPrediction(row, rows, level, {mobile: true})}</div><div class="mobile-standings-detail-actions"><button type="button" onclick="viewTeamPlayers(${htmlJsString(row.team_name || '')})">查看球队</button>${renderCoachProfileLink(row.manager, 'coach-profile-link standings-coach-link')}</div></div>` : ''}
                    </article>
                `;
            }).join('')}
        </div>
    `;
}

function renderDesktopStandingsTable(level, rows) {
    const scope = getMobileStandingsScopeMeta();
    return `
        <div class="table-container competition-table-container standings-table-container">
            <table class="competition-table standings-table standings-table-compact" aria-label="${escapeHtml(level)}${escapeHtml(scope.label)}积分榜">
                <colgroup>
                    <col class="standings-col-rank">
                    <col class="standings-col-team">
                    <col class="standings-col-coach">
                    ${Array.from({length: 9}, () => '<col class="standings-col-total">').join('')}
                    <col class="standings-col-prediction">
                </colgroup>
                <thead>
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
                        <th>胜率</th>
                        <th>预测排名</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(row => {
                        const wins = Number(row[scope.wins] || 0);
                        const draws = Number(row[scope.draws] || 0);
                        const losses = Number(row[scope.losses] || 0);
                        const goalsFor = Number(row[scope.goalsFor] || 0);
                        const goalsAgainst = Number(row[scope.goalsAgainst] || 0);
                        const goalDifference = Number(row[scope.goalDifference] || 0);
                        const points = Number(row[scope.points] || 0);
                        return `
                            <tr class="${getStandingZoneClass(row, rows)}">
                                <td class="numeric-cell rank-cell">${row.rank}</td>
                                <td class="team-name-cell standings-team-cell" title="${escapeHtml(row.manager ? `${row.team_name || '-'} / ${row.manager}` : (row.team_name || '-'))}">
                                    <button class="player-link standings-team-link" type="button" onclick="viewTeamPlayers(${htmlJsString(row.team_name || '')})">${escapeHtml(row.team_name || '-')}</button>
                                </td>
                                <td class="coach-cell" title="${escapeHtml(row.manager || '-')}">${renderCoachProfileLink(row.manager, 'coach-profile-link standings-coach-link')}</td>
                                <td class="numeric-cell">${scope.played(row)}</td>
                                <td class="numeric-cell">${wins}</td>
                                <td class="numeric-cell">${draws}</td>
                                <td class="numeric-cell">${losses}</td>
                                <td class="numeric-cell">${goalsFor}</td>
                                <td class="numeric-cell">${goalsAgainst}</td>
                                <td class="numeric-cell">${goalDifference}</td>
                                <td class="numeric-cell points-cell">${points}</td>
                                <td class="numeric-cell win-rate-cell">${scope.rate(row)}</td>
                                <td class="numeric-cell standing-prediction-cell">${renderStandingPrediction(row, rows, level)}</td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function renderStandingsBoard() {
    const container = document.getElementById('standingsBoard');
    if (!container) return;
    const rows = Array.isArray(standingsData.rows) ? standingsData.rows : [];
    if (!rows.length) {
        container.innerHTML = renderUiState({tone: 'empty', title: '暂无积分榜数据', message: '导入赛程并录入比分后，这里会自动生成排名。', compact: true});
        renderCompetitionDataStatus();
        return;
    }

    const grouped = groupStandingsByLevel(rows.filter(row => row.level === currentCompetitionLevel));
    const levels = Object.keys(grouped).sort((a, b) => getCompetitionLevelOrder(a) - getCompetitionLevelOrder(b) || a.localeCompare(b));
    container.innerHTML = levels.map(level => `
        <section class="competition-level-section standings-level-section exportable-panel" data-export-view="standings-${escapeHtml(level)}">
            <div class="table-header-row standings-header-row">
                <h2 class="table-title">${escapeHtml(level)}积分榜</h2>
                <div class="competition-header-actions">
                    <div class="standings-zone-legend">
                        <span class="standings-zone-chip promotion">前五升级区</span>
                        <span class="standings-zone-chip relegation">后五降级区</span>
                    </div>
                    <button class="btn btn-secondary standings-history-open-btn capture-exclude" type="button" onclick="openStandingsHistory(${htmlJsString(level)})">位次走势</button>
                    <button class="btn btn-secondary competition-excel-btn capture-exclude" type="button" onclick="exportStandingsExcel(${htmlJsString(level)})">Excel表格</button>
                    <button class="btn btn-secondary competition-image-btn capture-exclude" type="button" onclick="saveCompetitionImage('standings', ${htmlJsString(level)})">保存图片</button>
                </div>
            </div>
            ${renderStandingsPredictionSummary(level)}
            ${renderMobileStandingsScopeTabs(level)}
            ${renderMobileStandingsCards(level, grouped[level])}
            ${renderDesktopStandingsTable(level, grouped[level])}
        </section>
    `).join('');
    renderCompetitionDataStatus();
}

function getStandingHistoryTeam(data, teamId) {
    return (data?.teams || []).find(team => Number(team.team_id) === Number(teamId)) || null;
}

function getStandingHistoryRow(round, teamId) {
    return (round?.rows || []).find(row => Number(row.team_id) === Number(teamId)) || null;
}

function getStandingHistoryTone(teamName) {
    const palette = ['#7c5cff', '#2384d8', '#1d9a73', '#dc7b28', '#d65072', '#5f7398'];
    const text = normalizeSearchText(teamName || '');
    let value = 0;
    for (const character of text) value = (value * 31 + character.charCodeAt(0)) >>> 0;
    return palette[value % palette.length];
}

function getStandingHistoryInitials(teamName) {
    return getScheduleTeamInitials(teamName || '').slice(0, 2) || '队';
}

function renderStandingHistoryCrest(team, className = 'standings-history-list-crest') {
    const fallback = escapeHtml(getStandingHistoryInitials(team?.team_name));
    return `<span class="${className}" style="--history-team-color:${getStandingHistoryTone(team?.team_name)}">${team?.logo_path ? `<img src="${escapeHtml(team.logo_path)}" alt="${escapeHtml(team.team_name)}队徽" loading="lazy" decoding="async" onerror="this.hidden=true">` : ''}<b>${fallback}</b></span>`;
}

function getStandingHistoryDimensions(host, data) {
    const width = Math.max(300, Math.round(host?.clientWidth || 920));
    const mobile = width < 620;
    const rowGap = mobile ? 29 : 34;
    const top = mobile ? 38 : 44;
    const bottom = 38;
    const left = mobile ? 36 : 48;
    const right = mobile ? 18 : 28;
    const teamCount = Math.max(1, (data?.teams || []).length);
    return {width, height: top + bottom + ((teamCount - 1) * rowGap), top, bottom, left, right, rowGap, mobile};
}

function getStandingHistoryPoint(index, rank, dimensions, roundCount) {
    const denominator = Math.max(1, roundCount - 1);
    return {
        x: dimensions.left + ((dimensions.width - dimensions.left - dimensions.right) * index / denominator),
        y: dimensions.top + ((Math.max(1, Number(rank || 1)) - 1) * dimensions.rowGap),
    };
}

function buildStandingHistoryPath(data, teamId, dimensions) {
    const rounds = data?.rounds || [];
    return rounds.map((round, index) => {
        const row = getStandingHistoryRow(round, teamId);
        const point = getStandingHistoryPoint(index, row?.rank || 1, dimensions, rounds.length);
        return `${index ? 'L' : 'M'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`;
    }).join(' ');
}

function standingHistoryFocusIncludes(teamId, row) {
    const mode = standingsHistoryState.focusMode;
    const total = standingsHistoryState.data?.teams?.length || 0;
    if (mode === 'all') return true;
    if (mode === 'promotion') return Number(row?.rank || 0) <= 5;
    if (mode === 'relegation') return Number(row?.rank || 0) > Math.max(0, total - 5);
    return standingsHistoryState.selectedTeamIds.has(Number(teamId));
}

function getStandingHistoryFocusClass(teamId, row) {
    if (standingsHistoryState.focusMode === 'all') return '';
    return standingHistoryFocusIncludes(teamId, row) ? 'is-focused' : 'is-muted';
}

function renderStandingHistorySvg() {
    const host = document.getElementById('standingsHistoryChart');
    const data = standingsHistoryState.data;
    if (!host || !data?.rounds?.length) return;
    const dimensions = getStandingHistoryDimensions(host, data);
    standingsHistoryState.dimensions = dimensions;
    const rounds = data.rounds;
    const currentRound = rounds[standingsHistoryState.index] || rounds[0];
    const tickEvery = Math.max(1, Math.ceil(rounds.length / (dimensions.mobile ? 6 : 11)));
    const teamCount = data.teams.length;
    const promotionBottom = dimensions.top + (Math.min(5, teamCount) - 0.5) * dimensions.rowGap;
    const relegationTop = dimensions.top + (Math.max(1, teamCount - 4) - 1.5) * dimensions.rowGap;
    host.innerHTML = `
        <svg class="standings-history-svg" viewBox="0 0 ${dimensions.width} ${dimensions.height}" role="img" aria-label="${escapeHtml(data.level)}积分榜逐轮位次走势">
            <defs>
                <clipPath id="standingsHistoryRevealClip"><rect id="standingsHistoryRevealRect" x="0" y="0" width="0" height="${dimensions.height}"></rect></clipPath>
            </defs>
            <rect class="standings-history-zone is-promotion" x="${dimensions.left}" y="${Math.max(0, dimensions.top - dimensions.rowGap * 0.5)}" width="${dimensions.width - dimensions.left - dimensions.right}" height="${Math.max(0, promotionBottom - dimensions.top + dimensions.rowGap * 0.5)}"></rect>
            <rect class="standings-history-zone is-relegation" x="${dimensions.left}" y="${Math.max(0, relegationTop)}" width="${dimensions.width - dimensions.left - dimensions.right}" height="${Math.max(0, dimensions.height - dimensions.bottom - relegationTop + dimensions.rowGap * 0.5)}"></rect>
            <g class="standings-history-grid">
                ${Array.from({length: teamCount}, (_, index) => {
                    const y = dimensions.top + index * dimensions.rowGap;
                    return `<line x1="${dimensions.left}" y1="${y}" x2="${dimensions.width - dimensions.right}" y2="${y}"></line><text x="${dimensions.left - 12}" y="${y + 4}" text-anchor="middle">${index + 1}</text>`;
                }).join('')}
            </g>
            <g class="standings-history-round-labels">
                ${rounds.map((round, index) => {
                    if (index !== 0 && index !== rounds.length - 1 && index % tickEvery !== 0) return '';
                    const point = getStandingHistoryPoint(index, 1, dimensions, rounds.length);
                    return `<text x="${point.x}" y="${dimensions.height - 10}" text-anchor="middle">${index === 0 ? '开赛' : `R${round.round_no}`}</text>`;
                }).join('')}
            </g>
            <g class="standings-history-paths" clip-path="url(#standingsHistoryRevealClip)">
                ${data.teams.map(team => {
                    const row = getStandingHistoryRow(currentRound, team.team_id);
                    return `<path data-history-path="${Number(team.team_id)}" class="standings-history-path ${getStandingHistoryFocusClass(team.team_id, row)}" style="--history-team-color:${getStandingHistoryTone(team.team_name)}" d="${buildStandingHistoryPath(data, team.team_id, dimensions)}"></path>`;
                }).join('')}
            </g>
            <line id="standingsHistoryRoundCursor" class="standings-history-round-cursor" x1="0" y1="${dimensions.top - dimensions.rowGap * 0.55}" x2="0" y2="${dimensions.height - dimensions.bottom + dimensions.rowGap * 0.35}"></line>
            <g class="standings-history-nodes">
                ${data.teams.map(team => {
                    const row = getStandingHistoryRow(currentRound, team.team_id);
                    const point = getStandingHistoryPoint(standingsHistoryState.index, row?.rank || 1, dimensions, rounds.length);
                    return `<g class="standings-history-node ${getStandingHistoryFocusClass(team.team_id, row)}" data-history-node="${Number(team.team_id)}" style="--history-team-color:${getStandingHistoryTone(team.team_name)};transform:translate3d(${point.x}px,${point.y}px,0)" role="button" tabindex="0" aria-label="关注${escapeHtml(team.team_name)}" onclick="toggleStandingHistoryTeam(${Number(team.team_id)})" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();toggleStandingHistoryTeam(${Number(team.team_id)})}">
                        <circle class="standings-history-node-halo" r="17"></circle>
                        <circle class="standings-history-node-base" r="14"></circle>
                        <text class="standings-history-node-fallback" text-anchor="middle" y="3.5">${escapeHtml(getStandingHistoryInitials(team.team_name))}</text>
                        ${team.logo_path ? `<image href="${escapeHtml(team.logo_path)}" x="-13" y="-13" width="26" height="26" preserveAspectRatio="xMidYMid meet"></image>` : ''}
                    </g>`;
                }).join('')}
            </g>
        </svg>
    `;
    updateStandingHistoryRound({animate: false});
}

function renderStandingHistoryLiveTable(round) {
    const data = standingsHistoryState.data;
    const list = document.getElementById('standingsHistoryLiveList');
    if (!data || !list || !round) return;
    list.innerHTML = [...(round.rows || [])].sort((a, b) => Number(a.rank) - Number(b.rank)).map(row => {
        const team = getStandingHistoryTeam(data, row.team_id);
        const focusClass = getStandingHistoryFocusClass(row.team_id, row);
        const change = Number(row.rank_change || 0);
        const changeLabel = change > 0 ? `↑${change}` : (change < 0 ? `↓${Math.abs(change)}` : '—');
        return `
            <button type="button" class="standings-history-live-row ${focusClass}" onclick="toggleStandingHistoryTeam(${Number(row.team_id)})">
                <strong>${Number(row.rank)}</strong>
                ${renderStandingHistoryCrest(team)}
                <span><b>${escapeHtml(row.team_name)}</b><small>${Number(row.played)} 场 · 净胜球 ${Number(row.goal_difference) > 0 ? '+' : ''}${Number(row.goal_difference)}</small></span>
                <em class="${change > 0 ? 'is-up' : (change < 0 ? 'is-down' : '')}">${changeLabel}</em>
                <mark>${Number(row.points)}<small>分</small></mark>
            </button>
        `;
    }).join('');
}

function updateStandingHistoryFocus() {
    const data = standingsHistoryState.data;
    const round = data?.rounds?.[standingsHistoryState.index];
    if (!data || !round) return;
    document.querySelectorAll('[data-history-focus]').forEach(button => {
        const active = button.dataset.historyFocus === standingsHistoryState.focusMode;
        button.classList.toggle('is-active', active);
        button.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
    data.teams.forEach(team => {
        const row = getStandingHistoryRow(round, team.team_id);
        const focusClass = getStandingHistoryFocusClass(team.team_id, row);
        const path = document.querySelector(`[data-history-path="${Number(team.team_id)}"]`);
        const node = document.querySelector(`[data-history-node="${Number(team.team_id)}"]`);
        path?.classList.toggle('is-muted', focusClass === 'is-muted');
        path?.classList.toggle('is-focused', focusClass === 'is-focused');
        node?.classList.toggle('is-muted', focusClass === 'is-muted');
        node?.classList.toggle('is-focused', focusClass === 'is-focused');
    });
    renderStandingHistoryLiveTable(round);
    const count = standingsHistoryState.focusMode === 'custom'
        ? standingsHistoryState.selectedTeamIds.size
        : (standingsHistoryState.focusMode === 'all' ? data.teams.length : Math.min(5, data.teams.length));
    const summary = document.getElementById('standingsHistoryFocusSummary');
    if (summary) summary.textContent = standingsHistoryState.focusMode === 'all' ? `显示全部 ${count} 队` : `重点显示 ${count} 队`;
}

function setStandingHistoryFocus(mode) {
    standingsHistoryState.focusMode = ['all', 'promotion', 'relegation', 'custom'].includes(mode) ? mode : 'all';
    updateStandingHistoryFocus();
}

function toggleStandingHistoryTeam(teamId) {
    const id = Number(teamId);
    standingsHistoryState.focusMode = 'custom';
    if (standingsHistoryState.selectedTeamIds.has(id)) {
        standingsHistoryState.selectedTeamIds.delete(id);
    } else {
        if (standingsHistoryState.selectedTeamIds.size >= 4) {
            showUiToast('最多同时关注 4 支球队', 'warning');
            return;
        }
        standingsHistoryState.selectedTeamIds.add(id);
    }
    if (!standingsHistoryState.selectedTeamIds.size) standingsHistoryState.focusMode = 'all';
    updateStandingHistoryFocus();
}

function updateStandingHistoryRound(options = {}) {
    const data = standingsHistoryState.data;
    const rounds = data?.rounds || [];
    if (!rounds.length) return;
    standingsHistoryState.index = Math.max(0, Math.min(rounds.length - 1, Number(standingsHistoryState.index || 0)));
    const round = rounds[standingsHistoryState.index];
    const dimensions = standingsHistoryState.dimensions;
    if (!dimensions) return;
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const interval = 860 / standingsHistoryState.speed;
    const motionMs = options.animate === false || reducedMotion ? 1 : Math.max(220, Math.min(520, interval * 0.7));
    const modal = document.getElementById('standingsHistoryModal');
    modal?.style.setProperty('--history-motion-ms', `${motionMs}ms`);
    data.teams.forEach(team => {
        const row = getStandingHistoryRow(round, team.team_id);
        const point = getStandingHistoryPoint(standingsHistoryState.index, row?.rank || 1, dimensions, rounds.length);
        const node = document.querySelector(`[data-history-node="${Number(team.team_id)}"]`);
        if (node) node.style.transform = `translate3d(${point.x}px,${point.y}px,0)`;
    });
    const currentPoint = getStandingHistoryPoint(standingsHistoryState.index, 1, dimensions, rounds.length);
    const reveal = document.getElementById('standingsHistoryRevealRect');
    if (reveal) reveal.setAttribute('width', String(Math.max(0, currentPoint.x + 2)));
    const cursor = document.getElementById('standingsHistoryRoundCursor');
    if (cursor) {
        cursor.setAttribute('x1', String(currentPoint.x));
        cursor.setAttribute('x2', String(currentPoint.x));
    }
    const label = document.getElementById('standingsHistoryCurrentRound');
    if (label) label.textContent = round.round_label;
    const state = document.getElementById('standingsHistoryRoundState');
    if (state) {
        const opening = Number(round.round_no) === 0;
        state.className = `standings-history-round-state ${opening || round.is_complete ? 'is-complete' : 'is-recording'}`;
        state.textContent = opening ? '赛季起点' : (round.is_complete ? `${round.played_match_count}/${round.total_match_count} 场已完成` : `本轮录入中 · ${round.played_match_count}/${round.total_match_count} 场`);
    }
    const range = document.getElementById('standingsHistoryRange');
    if (range) range.value = String(standingsHistoryState.index);
    const previous = document.getElementById('standingsHistoryPrevious');
    const next = document.getElementById('standingsHistoryNext');
    if (previous) previous.disabled = standingsHistoryState.index <= 0;
    if (next) next.disabled = standingsHistoryState.index >= rounds.length - 1;
    updateStandingHistoryFocus();
}

function stopStandingHistoryPlayback() {
    window.clearTimeout(standingsHistoryState.timer);
    standingsHistoryState.timer = null;
    standingsHistoryState.playing = false;
    const button = document.getElementById('standingsHistoryPlay');
    if (button) {
        button.classList.remove('is-playing');
        button.setAttribute('aria-label', '播放位次走势');
        button.innerHTML = `${uiIconSvg('play')}<span>播放</span>`;
    }
}

function scheduleStandingHistoryFrame() {
    if (!standingsHistoryState.playing) return;
    const rounds = standingsHistoryState.data?.rounds || [];
    if (standingsHistoryState.index >= rounds.length - 1) {
        stopStandingHistoryPlayback();
        return;
    }
    const delay = 860 / standingsHistoryState.speed;
    standingsHistoryState.timer = window.setTimeout(() => {
        standingsHistoryState.index += 1;
        updateStandingHistoryRound();
        scheduleStandingHistoryFrame();
    }, delay);
}

function toggleStandingHistoryPlayback() {
    if (standingsHistoryState.playing) {
        stopStandingHistoryPlayback();
        return;
    }
    const rounds = standingsHistoryState.data?.rounds || [];
    if (rounds.length <= 1) return;
    if (standingsHistoryState.index >= rounds.length - 1) {
        standingsHistoryState.index = 0;
        updateStandingHistoryRound({animate: false});
    }
    standingsHistoryState.playing = true;
    const button = document.getElementById('standingsHistoryPlay');
    if (button) {
        button.classList.add('is-playing');
        button.setAttribute('aria-label', '暂停位次走势');
        button.innerHTML = `${uiIconSvg('pause')}<span>暂停</span>`;
    }
    scheduleStandingHistoryFrame();
}

function stepStandingHistory(direction) {
    stopStandingHistoryPlayback();
    standingsHistoryState.index += Number(direction || 0);
    updateStandingHistoryRound();
}

function seekStandingHistory(index) {
    stopStandingHistoryPlayback();
    standingsHistoryState.index = Number(index || 0);
    updateStandingHistoryRound();
}

function setStandingHistorySpeed(speed) {
    standingsHistoryState.speed = [1, 1.5, 2].includes(Number(speed)) ? Number(speed) : 1;
    document.querySelectorAll('[data-history-speed]').forEach(button => {
        const active = Number(button.dataset.historySpeed) === standingsHistoryState.speed;
        button.classList.toggle('is-active', active);
        button.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
    if (standingsHistoryState.playing) {
        window.clearTimeout(standingsHistoryState.timer);
        scheduleStandingHistoryFrame();
    }
}

function renderStandingsHistoryModal(data) {
    const modal = document.getElementById('standingsHistoryModal');
    if (!modal) return;
    const rounds = data.rounds || [];
    const latestIndex = Math.max(0, rounds.length - 1);
    standingsHistoryState.data = data;
    standingsHistoryState.index = latestIndex;
    standingsHistoryState.speed = 1;
    standingsHistoryState.selectedTeamIds = new Set();
    standingsHistoryState.focusMode = 'all';
    modal.querySelector('.standings-history-modal')?.classList.remove('is-loading');
    const body = modal.querySelector('.standings-history-modal-body');
    if (!body) return;
    if (rounds.length <= 1) {
        body.innerHTML = `<div class="standings-history-empty">${renderUiState({tone: 'empty', title: '尚无位次变化', message: '录入第一轮比赛结果后，这里会生成队徽排名轨迹。', compact: true})}</div>`;
        return;
    }
    body.innerHTML = `
        <div class="standings-history-toolbar capture-exclude">
            <div class="standings-history-focus-tabs" role="group" aria-label="走势关注范围">
                <button type="button" data-history-focus="all" class="is-active" aria-pressed="true" onclick="setStandingHistoryFocus('all')">全部</button>
                <button type="button" data-history-focus="promotion" aria-pressed="false" onclick="setStandingHistoryFocus('promotion')">争冠区</button>
                <button type="button" data-history-focus="relegation" aria-pressed="false" onclick="setStandingHistoryFocus('relegation')">保级区</button>
                <button type="button" data-history-focus="custom" aria-pressed="false" onclick="setStandingHistoryFocus('custom')">自选</button>
            </div>
            <span id="standingsHistoryFocusSummary">显示全部 ${data.teams.length} 队</span>
            <button type="button" class="btn btn-secondary standings-history-save" onclick="saveStandingsHistoryImage()">保存图片</button>
        </div>
        <div class="standings-history-capture" data-export-view="standings-history-${escapeHtml(data.level)}">
            <div class="standings-history-round-head">
                <div><span>当前节点</span><strong id="standingsHistoryCurrentRound">${escapeHtml(rounds[latestIndex].round_label)}</strong></div>
                <em id="standingsHistoryRoundState" class="standings-history-round-state"></em>
            </div>
            <div class="standings-history-stage">
                <div class="standings-history-chart" id="standingsHistoryChart"></div>
                <aside class="standings-history-live" aria-label="当前轮次排名">
                    <header><span>LIVE TABLE</span><strong>当前排名</strong></header>
                    <div id="standingsHistoryLiveList"></div>
                </aside>
            </div>
        </div>
        <div class="standings-history-controls capture-exclude">
            <button type="button" id="standingsHistoryPrevious" onclick="stepStandingHistory(-1)" aria-label="上一轮">${uiIconSvg('arrow-left')}</button>
            <button type="button" id="standingsHistoryPlay" class="standings-history-play" onclick="toggleStandingHistoryPlayback()" aria-label="播放位次走势">${uiIconSvg('play')}<span>播放</span></button>
            <button type="button" id="standingsHistoryNext" onclick="stepStandingHistory(1)" aria-label="下一轮">${uiIconSvg('arrow-right')}</button>
            <input id="standingsHistoryRange" type="range" min="0" max="${Math.max(0, rounds.length - 1)}" value="${latestIndex}" step="1" aria-label="选择轮次" oninput="seekStandingHistory(this.value)">
            <div class="standings-history-speeds" role="group" aria-label="播放速度">
                ${[1, 1.5, 2].map(speed => `<button type="button" data-history-speed="${speed}" class="${speed === 1 ? 'is-active' : ''}" aria-pressed="${speed === 1 ? 'true' : 'false'}" onclick="setStandingHistorySpeed(${speed})">${speed}×</button>`).join('')}
            </div>
        </div>
    `;
    requestAnimationFrame(() => {
        renderStandingHistorySvg();
        standingsHistoryState.resizeObserver?.disconnect();
        if (typeof ResizeObserver === 'function') {
            standingsHistoryState.resizeObserver = new ResizeObserver(() => renderStandingHistorySvg());
            standingsHistoryState.resizeObserver.observe(document.getElementById('standingsHistoryChart'));
        }
    });
}

async function openStandingsHistory(level = currentCompetitionLevel) {
    closeStandingsHistory();
    standingsHistoryState.level = level;
    standingsHistoryState.returnFocus = document.activeElement;
    const host = document.createElement('div');
    host.innerHTML = `
        <div class="standings-history-modal-overlay" id="standingsHistoryModal" role="presentation" onclick="if(event.target===this)closeStandingsHistory()">
            <section class="standings-history-modal is-loading" role="dialog" aria-modal="true" aria-labelledby="standingsHistoryTitle" tabindex="-1">
                <header class="standings-history-modal-head">
                    <div><span>RANKING JOURNEY</span><h3 id="standingsHistoryTitle">${escapeHtml(level)}位次走势</h3><p>队徽按轮次移动，轨迹与当前积分榜采用相同排名规则。</p></div>
                    <button type="button" class="match-event-modal-close" onclick="closeStandingsHistory()" aria-label="关闭位次走势">${uiIconSvg('close')}</button>
                </header>
                <div class="standings-history-modal-body"><div class="standings-history-loading"><span></span><strong>正在生成逐轮排名轨迹</strong><small>从赛程比分实时累计，无需单独维护</small></div></div>
            </section>
        </div>
    `;
    document.body.appendChild(host.firstElementChild);
    document.body.classList.add('standings-history-modal-open');
    requestAnimationFrame(() => document.querySelector('.standings-history-modal')?.focus());
    try {
        const cached = standingsHistoryCache.get(level);
        let data = cached && Date.now() - cached.loadedAt < 60000 ? cached.data : null;
        if (!data) {
            data = await fetchCompetitionJson(`/api/standings/history?level=${encodeURIComponent(level)}`);
            standingsHistoryCache.set(level, {data, loadedAt: Date.now()});
        }
        if (!document.getElementById('standingsHistoryModal') || standingsHistoryState.level !== level) return;
        renderStandingsHistoryModal(data);
    } catch (error) {
        console.error('Failed to load standings history:', error);
        const body = document.querySelector('#standingsHistoryModal .standings-history-modal-body');
        if (body) body.innerHTML = renderUiState({tone: 'danger', title: '位次走势加载失败', message: '积分榜本身不受影响，可以稍后重新打开。', actionLabel: '重新读取', actionOnclick: `openStandingsHistory(${htmlJsString(level)})`, compact: true});
    }
}

function closeStandingsHistory() {
    stopStandingHistoryPlayback();
    standingsHistoryState.resizeObserver?.disconnect();
    standingsHistoryState.resizeObserver = null;
    document.getElementById('standingsHistoryModal')?.remove();
    document.body.classList.remove('standings-history-modal-open');
    const returnFocus = standingsHistoryState.returnFocus;
    standingsHistoryState.returnFocus = null;
    if (returnFocus?.isConnected) returnFocus.focus();
}

async function saveStandingsHistoryImage() {
    const target = document.querySelector('.standings-history-capture');
    if (!target || competitionImageExportBusy) return;
    try {
        await ensureHtmlToImage();
        if (!window.htmlToImage?.toBlob) throw new Error('image-export-unavailable');
        competitionImageExportBusy = true;
        target.classList.add('is-exporting');
        if (document.fonts?.ready) await document.fonts.ready;
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        renderStandingHistorySvg();
        await new Promise(resolve => requestAnimationFrame(resolve));
        const blob = await window.htmlToImage.toBlob(target, {cacheBust: true, pixelRatio: 2});
        if (!blob) throw new Error('capture-blob-empty');
        downloadCompetitionBlob(blob, `HEIGO_${standingsHistoryState.level}_位次走势_R${standingsHistoryState.data?.rounds?.[standingsHistoryState.index]?.round_no || 0}.png`);
        showUiToast('位次走势图已保存', 'success');
    } catch (error) {
        console.error('Failed to save standings history image:', error);
        showModal('生成图片失败', '位次走势图暂时无法保存，请刷新后重试。');
    } finally {
        target?.classList.remove('is-exporting');
        requestAnimationFrame(() => renderStandingHistorySvg());
        competitionImageExportBusy = false;
    }
}

function handleStandingsHistoryKeydown(event) {
    const modal = document.getElementById('standingsHistoryModal');
    if (!modal) return;
    if (event.key === 'Escape') {
        event.preventDefault();
        closeStandingsHistory();
        return;
    }
    if (event.key === 'ArrowLeft' && !event.target?.matches?.('input')) {
        event.preventDefault();
        stepStandingHistory(-1);
        return;
    }
    if (event.key === 'ArrowRight' && !event.target?.matches?.('input')) {
        event.preventDefault();
        stepStandingHistory(1);
        return;
    }
    if (event.key !== 'Tab') return;
    const focusable = Array.from(modal.querySelectorAll('button:not(:disabled), input:not(:disabled), [tabindex]:not([tabindex="-1"])'));
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
    }
}

document.addEventListener('keydown', handleStandingsHistoryKeydown);

function renderCompetitionPrimaryBoard() {
    const standingsContainer = document.getElementById('standingsBoard');
    const cupContainer = document.getElementById('cupBracketBoard');
    if (isCupCompetitionLevel()) {
        if (standingsContainer) standingsContainer.style.display = 'none';
        if (cupContainer) {
            cupContainer.style.display = '';
            if (currentCupPhase === 'group' && getCurrentCupConfig()?.groupCount) {
                renderCupGroupStandingsBoard();
            } else {
                renderCupBracketBoard();
            }
        }
        return;
    }
    if (cupContainer) cupContainer.style.display = 'none';
    if (standingsContainer) {
        standingsContainer.style.display = '';
        renderStandingsBoard();
    }
}

function getCurrentCupGroupStage() {
    const cupConfig = getCurrentCupConfig();
    return cupConfig ? cupGroupStageData[cupConfig.key] || null : null;
}

function getCupGroupAssignmentLocation(teamId) {
    const stage = getCurrentCupGroupStage();
    const numericId = Number(teamId || 0);
    if (!stage || !numericId) return null;
    for (const group of stage.groups || []) {
        const slot = (group.teams || []).find(item => Number(item.team_id || 0) === numericId);
        if (slot) return {groupNo: Number(group.group_no), groupName: group.group_name, slotNo: Number(slot.slot_no)};
    }
    return null;
}

function getCupGroupTeamSearchText(team) {
    const shortName = CUP_TEAM_SHORT_NAMES[String(team?.name || '')] || '';
    return [team?.name, shortName, team?.manager, team?.level].filter(Boolean).join(' ').toLowerCase();
}

function getCupGroupTeamSuggestions(query = '') {
    const raw = String(query || '').trim().toLowerCase();
    return [...(teams || [])]
        .filter(team => team.level !== '隐藏' && (!raw || getCupGroupTeamSearchText(team).includes(raw)))
        .sort((a, b) => String(a.name || '').localeCompare(String(b.name || '')))
        .slice(0, 14);
}

function renderCupGroupSuggestionList(groupNo, slotNo, query = '') {
    const suggestions = getCupGroupTeamSuggestions(query);
    if (!suggestions.length) {
        return '<div class="cup-group-suggestion-empty">未找到已有球队，请继续输入完整队名。</div>';
    }
    return `
        <div class="cup-group-suggestion-list" role="listbox">
            ${suggestions.map(team => {
                const location = getCupGroupAssignmentLocation(team.id);
                const assignedElsewhere = location && (location.groupNo !== Number(groupNo) || location.slotNo !== Number(slotNo));
                return `
                    <button class="cup-group-suggestion-option" type="button" role="option" ${assignedElsewhere ? 'disabled' : ''} onclick="selectCupGroupSuggestion(${Number(groupNo)}, ${Number(slotNo)}, ${Number(team.id)})">
                        <span class="cup-group-suggestion-crest">${team.logo_path ? `<img src="${escapeHtml(team.logo_path)}" alt="">` : escapeHtml(getScheduleTeamInitials(team.name))}</span>
                        <span class="cup-group-suggestion-copy"><strong>${escapeHtml(team.name || '-')}</strong><small>${escapeHtml([team.level ? `${team.level}联赛` : '', team.manager || ''].filter(Boolean).join(' / '))}</small></span>
                        ${assignedElsewhere ? `<em>已在 ${escapeHtml(location.groupName)} 组</em>` : ''}
                    </button>
                `;
            }).join('')}
        </div>
    `;
}

function closeCupGroupSuggestions(exceptPanel = null) {
    const panel = document.getElementById('cupGroupSuggestionPanel');
    if (panel && panel !== exceptPanel) panel.remove();
    if (panel !== exceptPanel) activeCupGroupSuggestionContext = null;
}

function getCupGroupSuggestionPanel() {
    let panel = document.getElementById('cupGroupSuggestionPanel');
    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'cupGroupSuggestionPanel';
        panel.className = 'cup-group-suggestions-floating';
        panel.hidden = true;
        document.body.appendChild(panel);
    }
    return panel;
}

function positionCupGroupSuggestionPanel(input, panel) {
    const rect = input.getBoundingClientRect();
    const fieldRect = input.closest('.cup-group-team-field')?.getBoundingClientRect() || rect;
    const panelWidth = Math.min(Math.max(fieldRect.width, 300), window.innerWidth - 24);
    const left = Math.max(12, Math.min(fieldRect.left, window.innerWidth - panelWidth - 12));
    const estimatedHeight = Math.min(380, Math.max(190, window.innerHeight * 0.46));
    const belowTop = rect.bottom + 6;
    const aboveTop = rect.top - estimatedHeight - 6;
    panel.style.width = `${panelWidth}px`;
    panel.style.left = `${left}px`;
    panel.style.top = `${belowTop + estimatedHeight > window.innerHeight - 12 && aboveTop > 12 ? aboveTop : belowTop}px`;
}

function updateCupGroupSuggestions(input, groupNo, slotNo, forceOpen = false) {
    const panel = getCupGroupSuggestionPanel();
    if (!input || !panel) return;
    panel.innerHTML = renderCupGroupSuggestionList(groupNo, slotNo, input.value);
    const shouldOpen = forceOpen || Boolean(String(input.value || '').trim());
    if (shouldOpen) {
        activeCupGroupSuggestionContext = {groupNo: Number(groupNo), slotNo: Number(slotNo), input};
        positionCupGroupSuggestionPanel(input, panel);
        closeCupGroupSuggestions(panel);
    }
    panel.hidden = !shouldOpen;
}

function handleCupGroupTeamInput(input, groupNo, slotNo) {
    input.dataset.teamId = '';
    updateCupGroupSuggestions(input, groupNo, slotNo);
}

function toggleCupGroupSuggestions(button, groupNo, slotNo) {
    const input = button?.closest('.cup-group-team-field')?.querySelector('.cup-group-team-input');
    const panel = getCupGroupSuggestionPanel();
    if (!input || !panel) return;
    const context = activeCupGroupSuggestionContext;
    const shouldOpen = panel.hidden || context?.input !== input;
    if (shouldOpen) {
        input.focus();
        updateCupGroupSuggestions(input, groupNo, slotNo, true);
    } else {
        closeCupGroupSuggestions();
    }
}

function scheduleCloseCupGroupSuggestions(input) {
    window.setTimeout(() => {
        const panel = document.getElementById('cupGroupSuggestionPanel');
        if (!panel || activeCupGroupSuggestionContext?.input !== input) return;
        if (!panel.contains(document.activeElement)) closeCupGroupSuggestions();
    }, 120);
}

function selectCupGroupSuggestion(groupNo, slotNo, teamId) {
    const input = document.getElementById(`cup-group-team-${groupNo}-${slotNo}`) || activeCupGroupSuggestionContext?.input;
    const team = (teams || []).find(item => Number(item.id) === Number(teamId));
    if (!input || !team) return;
    input.value = team.name || '';
    input.dataset.teamId = String(team.id);
    closeCupGroupSuggestions();
    input.dispatchEvent(new Event('change', {bubbles: true}));
}

function clearCupGroupTeam(groupNo, slotNo) {
    const input = document.getElementById(`cup-group-team-${groupNo}-${slotNo}`);
    if (!input) return;
    input.value = '';
    input.dataset.teamId = '';
    closeCupGroupSuggestions();
    input.focus();
}

function resolveCupGroupTeamInput(input) {
    const raw = String(input?.value || '').trim();
    if (!raw) return null;
    const selectedId = Number(input?.dataset.teamId || 0);
    const selected = (teams || []).find(team => Number(team.id) === selectedId);
    if (selected && String(selected.name || '') === raw) return selected;
    const lowered = raw.toLowerCase();
    const available = (teams || []).filter(team => team.level !== '隐藏');
    const exact = available.find(team => String(team.name || '').toLowerCase() === lowered || String(CUP_TEAM_SHORT_NAMES[team.name] || '').toLowerCase() === lowered);
    if (exact) return exact;
    const startsWith = available.filter(team => String(team.name || '').toLowerCase().startsWith(lowered) || String(CUP_TEAM_SHORT_NAMES[team.name] || '').toLowerCase().startsWith(lowered));
    if (startsWith.length === 1) return startsWith[0];
    const fuzzy = available.filter(team => getCupGroupTeamSearchText(team).includes(lowered));
    if (fuzzy.length === 1) return fuzzy[0];
    if (startsWith.length > 1 || fuzzy.length > 1) throw new Error(`“${raw}”匹配到多支球队，请继续输入或从候选列表选择。`);
    throw new Error(`球队库中没有“${raw}”，请选择已有球队。`);
}

function handleCupGroupSuggestionDocumentPointerDown(event) {
    const panel = document.getElementById('cupGroupSuggestionPanel');
    if (!panel || panel.hidden) return;
    if (panel.contains(event.target) || event.target?.closest?.('.cup-group-team-field')) return;
    closeCupGroupSuggestions();
}

document.addEventListener('pointerdown', handleCupGroupSuggestionDocumentPointerDown, true);

function renderCupGroupTeamSlot(group, slot, editable) {
    const groupNo = Number(group.group_no);
    const slotNo = Number(slot.slot_no);
    const teamName = slot.team_name || '';
    if (editable) {
        return `
            <div class="cup-group-team-slot ${teamName ? 'is-assigned' : 'is-empty'}">
                <span class="cup-group-slot-number">${slotNo}</span>
                <div class="cup-group-team-field">
                    <input id="cup-group-team-${groupNo}-${slotNo}" class="cup-group-team-input" type="text" value="${escapeHtml(teamName)}" data-team-id="${Number(slot.team_id || 0) || ''}" placeholder="输入球队名" autocomplete="off" aria-label="${escapeHtml(group.group_name)}组第 ${slotNo} 支球队" oninput="handleCupGroupTeamInput(this, ${groupNo}, ${slotNo})" onfocus="updateCupGroupSuggestions(this, ${groupNo}, ${slotNo}, true)" onblur="scheduleCloseCupGroupSuggestions(this)">
                    <button class="cup-group-team-toggle" type="button" aria-label="选择球队" onclick="toggleCupGroupSuggestions(this, ${groupNo}, ${slotNo})">▾</button>
                </div>
                <button class="cup-group-team-clear" type="button" aria-label="清空${escapeHtml(group.group_name)}组第 ${slotNo} 支球队" onclick="clearCupGroupTeam(${groupNo}, ${slotNo})">${uiIconSvg('close', 'ui-icon is-small')}</button>
            </div>
        `;
    }
    return `
        <div class="cup-group-team-slot ${teamName ? 'is-assigned' : 'is-empty'}">
            <span class="cup-group-slot-number">${slotNo}</span>
            <span class="cup-group-team-crest">${slot.logo_path ? `<img src="${escapeHtml(slot.logo_path)}" alt="">` : teamName ? escapeHtml(getScheduleTeamInitials(teamName)) : '—'}</span>
            <span class="cup-group-team-copy"><strong title="${escapeHtml(teamName || '待定')}">${escapeHtml(teamName || '待定')}</strong>${teamName ? `<small>${escapeHtml([slot.level ? `${slot.level}联赛` : '', slot.manager || ''].filter(Boolean).join(' / '))}</small>` : '<small>等待分配球队</small>'}</span>
        </div>
    `;
}

function renderCupGroupCard(group, teamsPerGroup, editable) {
    const assigned = (group.teams || []).filter(slot => slot.team_id).length;
    return `
        <article class="cup-group-card surface-card">
            <header class="cup-group-card-head">
                <div><span>${escapeHtml(group.group_name)}</span><strong>${escapeHtml(group.group_name)} 组</strong></div>
                <em>${assigned}/${teamsPerGroup}</em>
            </header>
            <div class="cup-group-team-list">
                ${(group.teams || []).map(slot => renderCupGroupTeamSlot(group, slot, editable)).join('')}
            </div>
            ${editable ? `<footer class="cup-group-card-actions"><span class="ui-save-state" id="cup-group-save-state-${Number(group.group_no)}" aria-live="polite">修改后保存本组</span><button class="btn btn-primary" id="cup-group-save-${Number(group.group_no)}" type="button" onclick="saveCupGroup(${Number(group.group_no)})">保存 ${escapeHtml(group.group_name)} 组</button></footer>` : ''}
        </article>
    `;
}

function setCupGroupScheduleView(view) {
    currentCupGroupScheduleView = view === 'results' ? 'results' : 'groups';
    closeCupGroupSuggestions();
    syncCupPhaseTabs();
    renderCupGroupStageBoard();
    renderCompetitionDataStatus();
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
}

function calculateCupGroupStandings(group) {
    const serverRows = new Map((group.standings || []).map(row => [Number(row.team_id), row]));
    const rows = new Map((group.teams || []).filter(team => team.team_id).map(team => [Number(team.team_id), {
        rank: 0,
        team_id: Number(team.team_id),
        team_name: team.team_name || '-',
        played: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goals_for: 0,
        goals_against: 0,
        goal_difference: 0,
        points: 0,
        qualification: serverRows.get(Number(team.team_id))?.qualification || 'pending',
        qualification_label: serverRows.get(Number(team.team_id))?.qualification_label || '待定',
        qualification_provisional: serverRows.get(Number(team.team_id))?.qualification_provisional ?? true,
    }]));
    (group.matches || []).forEach(match => {
        if (match.status !== 'played' || match.home_score === null || match.home_score === undefined || match.away_score === null || match.away_score === undefined) return;
        const home = rows.get(Number(match.home_team_id));
        const away = rows.get(Number(match.away_team_id));
        if (!home || !away) return;
        const homeScore = Number(match.home_score);
        const awayScore = Number(match.away_score);
        home.played += 1;
        away.played += 1;
        home.goals_for += homeScore;
        home.goals_against += awayScore;
        away.goals_for += awayScore;
        away.goals_against += homeScore;
        if (homeScore > awayScore) {
            home.wins += 1;
            away.losses += 1;
            home.points += 3;
        } else if (awayScore > homeScore) {
            away.wins += 1;
            home.losses += 1;
            away.points += 3;
        } else {
            home.draws += 1;
            away.draws += 1;
            home.points += 1;
            away.points += 1;
        }
        home.goal_difference = home.goals_for - home.goals_against;
        away.goal_difference = away.goals_for - away.goals_against;
    });
    return [...rows.values()]
        .sort((a, b) => b.points - a.points || b.goal_difference - a.goal_difference || b.goals_for - a.goals_for || String(a.team_name).localeCompare(String(b.team_name)))
        .map((row, index) => ({...row, rank: index + 1}));
}

function renderCupGroupStandingRows(group) {
    const rows = (group.standings || []).length ? group.standings : calculateCupGroupStandings(group);
    return rows.map(row => `
        <tr class="is-${escapeHtml(row.qualification || 'pending')}">
            <td><strong>${row.rank}</strong></td>
            <td title="${escapeHtml(row.team_name)}">${escapeHtml(row.team_name)}</td>
            <td>${row.played}</td>
            <td>${row.wins}</td>
            <td>${row.draws}</td>
            <td>${row.losses}</td>
            <td>${row.goal_difference > 0 ? '+' : ''}${row.goal_difference}</td>
            <td><strong>${row.points}</strong></td>
            <td><span class="cup-qualification-label is-${escapeHtml(row.qualification || 'pending')}">${escapeHtml(row.qualification_label || '待定')}</span></td>
        </tr>
    `).join('');
}

function renderCupGroupStandings(group) {
    return `
        <div class="cup-group-standings-wrap">
            <div class="cup-group-section-label"><span>积分榜</span><small>胜 3 · 平 1 · 负 0</small></div>
            <div class="cup-group-standings-table-wrap">
                <table class="cup-group-standings-table" aria-label="${escapeHtml(group.group_name)}组积分榜">
                    <thead><tr><th>#</th><th>球队</th><th>场</th><th>胜</th><th>平</th><th>负</th><th>净</th><th>分</th><th>去向</th></tr></thead>
                    <tbody id="cup-group-standings-${Number(group.group_no)}">${renderCupGroupStandingRows(group)}</tbody>
                </table>
            </div>
        </div>
    `;
}

function renderCupGroupStandingsCard(group) {
    const played = (group.matches || []).filter(match => match.status === 'played').length;
    return `
        <article class="cup-group-standing-card surface-card">
            <header><div><span>${escapeHtml(group.group_name)}</span><strong>${escapeHtml(group.group_name)} 组积分榜</strong></div><em>${played}/${(group.matches || []).length} 已赛</em></header>
            ${renderCupGroupStandings(group)}
        </article>
    `;
}

function renderCupGroupStandingsBoard() {
    const container = document.getElementById('cupBracketBoard');
    const cupConfig = getCurrentCupConfig();
    const stage = getCurrentCupGroupStage();
    if (!container || !cupConfig) return;
    if (!stage) {
        container.innerHTML = renderUiState({tone: 'danger', title: '小组积分榜读取失败', message: '请刷新页面后重新读取。', actionLabel: '重新读取', actionOnclick: 'loadCompetitionData({force:true})', compact: true});
        return;
    }
    container.innerHTML = `
        <section class="cup-group-standings-board cup-group-stage-shell ${escapeHtml(cupConfig.className)}">
            <div class="cup-group-stage-head surface-card">
                <div><span>GROUP STANDINGS</span><h2>${escapeHtml(currentCompetitionLevel)}小组赛积分榜</h2><p>胜 3 · 平 1 · 负 0；同分依次比较净胜球、进球数和球队名</p></div>
                <em>${stage.qualification_complete ? '晋级已确定' : '当前暂列'}</em>
            </div>
            ${renderCupQualificationSummary(stage)}
            <div class="cup-group-standings-grid">${(stage.groups || []).map(renderCupGroupStandingsCard).join('')}</div>
        </section>
    `;
}

function getCupGroupScorePayload(matchId) {
    const homeInput = document.getElementById(`cup-group-score-${matchId}-home`);
    const awayInput = document.getElementById(`cup-group-score-${matchId}-away`);
    if (!homeInput || !awayInput) return null;
    const homeRaw = String(homeInput.value || '').trim();
    const awayRaw = String(awayInput.value || '').trim();
    if (!homeRaw && !awayRaw) return {homeScore: null, awayScore: null};
    if (!homeRaw || !awayRaw) return {waiting: true};
    const homeScore = Number(homeRaw);
    const awayScore = Number(awayRaw);
    if (!Number.isInteger(homeScore) || !Number.isInteger(awayScore) || homeScore < 0 || awayScore < 0 || homeScore > 99 || awayScore > 99) {
        return {error: '比分只能填写 0 到 99'};
    }
    return {homeScore, awayScore};
}

function setCupGroupScoreSaveState(matchId, state, message) {
    const element = document.getElementById(`cup-group-score-state-${matchId}`);
    if (!element) return;
    element.className = `ui-save-state${state ? ` is-${state}` : ''}`;
    element.textContent = message;
}

function queueCupGroupScoreSave(matchId, immediate = false) {
    if (!canManageCurrentCupStandings()) return;
    const numericId = Number(matchId);
    const payload = getCupGroupScorePayload(numericId);
    if (!payload) return;
    const existingTimer = cupGroupScoreSaveTimers.get(numericId);
    if (existingTimer) window.clearTimeout(existingTimer);
    cupGroupScoreSaveTimers.delete(numericId);
    if (payload.error) {
        setCupGroupScoreSaveState(numericId, 'error', payload.error);
        return;
    }
    if (payload.waiting) {
        setCupGroupScoreSaveState(numericId, 'warning', '等待另一侧比分');
        return;
    }
    const version = Number(cupGroupScoreSaveVersions.get(numericId) || 0) + 1;
    cupGroupScoreSaveVersions.set(numericId, version);
    setCupGroupScoreSaveState(numericId, 'saving', immediate ? '正在保存' : '等待保存');
    if (immediate) {
        saveCupGroupScore(numericId, version);
        return;
    }
    cupGroupScoreSaveTimers.set(numericId, window.setTimeout(() => {
        cupGroupScoreSaveTimers.delete(numericId);
        saveCupGroupScore(numericId, version);
    }, 650));
}

function findCupGroupMatch(matchId) {
    const stage = getCurrentCupGroupStage();
    for (const group of stage?.groups || []) {
        const match = (group.matches || []).find(item => Number(item.id) === Number(matchId));
        if (match) return {group, match};
    }
    return null;
}

function updateCupGroupScoreDisplay(group, match) {
    group.standings = calculateCupGroupStandings(group);
    const tbody = document.getElementById(`cup-group-standings-${Number(group.group_no)}`);
    if (tbody) tbody.innerHTML = renderCupGroupStandingRows(group);
    const row = document.getElementById(`cup-group-match-${Number(match.id)}`);
    row?.classList.toggle('is-played', match.status === 'played');
    const played = (group.matches || []).filter(item => item.status === 'played').length;
    const progress = document.getElementById(`cup-group-progress-${Number(group.group_no)}`);
    if (progress) progress.textContent = `${played}/${(group.matches || []).length} 已赛`;
}

function renderCupQualificationSummary(stage) {
    const complete = Boolean(stage?.qualification_complete);
    const champions = stage?.champions_knockout_qualifiers || [];
    const league = stage?.league_knockout_qualifiers || [];
    const isChampions = stage?.competition === 'champions_cup';
    return `
        <section class="cup-qualification-summary surface-card" id="cupQualificationSummary" aria-label="小组赛晋级概览">
            <div><span>${complete ? '晋级名单' : '当前晋级顺位'}</span><strong>${isChampions ? '冠军杯：前 3 名 + 最佳小组第 4 名' : '联盟杯：每组前 3 名 + 冠军杯转入 4 队'}</strong></div>
            <div class="cup-qualification-counts">
                ${isChampions ? `<span><small>冠军杯淘汰赛</small><strong>${champions.length}/16</strong></span><span><small>转入联盟杯</small><strong>${league.length}/4</strong></span>` : `<span><small>联盟杯淘汰赛</small><strong>${league.length}/16</strong></span><span><small>本赛事晋级</small><strong>${league.filter(team => team.source_competition === 'league_cup').length}/12</strong></span>`}
            </div>
            <p>${complete ? '小组赛已全部结束，晋级去向已确定。' : '小组赛尚未全部结束，所有去向均为暂列；同分依次比较净胜球、进球数和球队名。'}</p>
        </section>
    `;
}

async function refreshCupGroupQualificationDisplays() {
    const cupConfig = getCurrentCupConfig();
    if (!cupConfig?.groupCount) return;
    const response = await fetchWithTimeout(`/api/cups/${cupConfig.key}/groups`, {credentials: 'same-origin'}).catch(() => null);
    if (!response?.ok) return;
    const stage = await response.json().catch(() => null);
    if (!stage) return;
    cupGroupStageData[cupConfig.key] = stage;
    (stage.groups || []).forEach(group => {
        const tbody = document.getElementById(`cup-group-standings-${Number(group.group_no)}`);
        if (tbody) tbody.innerHTML = renderCupGroupStandingRows(group);
    });
    const summary = document.getElementById('cupQualificationSummary');
    if (summary) summary.outerHTML = renderCupQualificationSummary(stage);
    renderCompetitionDataStatus();
}

async function saveCupGroupScore(matchId, requestedVersion = null) {
    const numericId = Number(matchId);
    const version = requestedVersion === null ? Number(cupGroupScoreSaveVersions.get(numericId) || 0) : Number(requestedVersion);
    if (version !== Number(cupGroupScoreSaveVersions.get(numericId) || 0) || cupGroupScoreSaveInFlight.has(numericId)) return;
    const payload = getCupGroupScorePayload(numericId);
    const located = findCupGroupMatch(numericId);
    const cupConfig = getCurrentCupConfig();
    if (!payload || payload.waiting || payload.error || !located || !cupConfig) return;
    cupGroupScoreSaveInFlight.add(numericId);
    setCupGroupScoreSaveState(numericId, 'saving', '保存中');
    try {
        const result = await workJsonRequest(`/api/admin/cups/${cupConfig.key}/group-matches/${numericId}`, {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({home_score: payload.homeScore, away_score: payload.awayScore}),
        });
        if (!result) return;
        const {response, data} = result;
        if (!response.ok || !data.success) {
            setCupGroupScoreSaveState(numericId, 'error', data.detail || data.message || '保存失败');
            return;
        }
        located.match.home_score = payload.homeScore;
        located.match.away_score = payload.awayScore;
        located.match.status = payload.homeScore === null ? 'scheduled' : 'played';
        updateCupGroupScoreDisplay(located.group, located.match);
        await refreshCupGroupQualificationDisplays();
        if (version === Number(cupGroupScoreSaveVersions.get(numericId) || 0)) setCupGroupScoreSaveState(numericId, 'saved', '已保存');
    } catch (error) {
        console.error('Failed to save cup group score:', error);
        setCupGroupScoreSaveState(numericId, 'error', '网络异常，修改后重试');
    } finally {
        cupGroupScoreSaveInFlight.delete(numericId);
        const nextVersion = Number(cupGroupScoreSaveVersions.get(numericId) || 0);
        if (nextVersion > version) saveCupGroupScore(numericId, nextVersion);
    }
}

function renderCupGroupMatchRow(match, editable) {
    const matchId = Number(match.id);
    const played = match.status === 'played';
    return `
        <div class="cup-group-match-row ${played ? 'is-played' : ''}" id="cup-group-match-${matchId}">
            <span class="cup-group-match-team is-home" title="${escapeHtml(match.home_team_name || '-')}">${escapeHtml(match.home_team_name || '-')}</span>
            ${editable ? `<div class="cup-group-score-editor">
                <input id="cup-group-score-${matchId}-home" type="number" min="0" max="99" inputmode="numeric" value="${match.home_score ?? ''}" aria-label="${escapeHtml(match.home_team_name || '主队')}进球数" oninput="queueCupGroupScoreSave(${matchId})" onblur="queueCupGroupScoreSave(${matchId}, true)">
                <span>:</span>
                <input id="cup-group-score-${matchId}-away" type="number" min="0" max="99" inputmode="numeric" value="${match.away_score ?? ''}" aria-label="${escapeHtml(match.away_team_name || '客队')}进球数" oninput="queueCupGroupScoreSave(${matchId})" onblur="queueCupGroupScoreSave(${matchId}, true)">
            </div>` : `<strong class="cup-group-score-readonly">${played ? `${Number(match.home_score)} : ${Number(match.away_score)}` : '未赛'}</strong>`}
            <span class="cup-group-match-team is-away" title="${escapeHtml(match.away_team_name || '-')}">${escapeHtml(match.away_team_name || '-')}</span>
            ${editable ? `<span class="ui-save-state" id="cup-group-score-state-${matchId}" aria-live="polite">自动保存</span>` : ''}
        </div>
    `;
}

function getCupGroupPairKey(group, match) {
    const teamIds = [Number(match.home_team_id), Number(match.away_team_id)].sort((a, b) => a - b);
    return `${getCurrentCupConfig()?.key || 'cup'}:${Number(group.group_no)}:${teamIds.join('-')}`;
}

function getCupGroupMatchPairs(group) {
    const pairs = new Map();
    (group.matches || []).forEach(match => {
        const key = getCupGroupPairKey(group, match);
        if (!pairs.has(key)) pairs.set(key, {key, matches: []});
        pairs.get(key).matches.push(match);
    });
    return [...pairs.values()].map(pair => {
        pair.matches.sort((a, b) => Number(a.round_no) - Number(b.round_no));
        const first = pair.matches[0] || {};
        pair.teamNames = [first.home_team_name || '-', first.away_team_name || '-'].sort((a, b) => String(a).localeCompare(String(b), 'zh-CN'));
        pair.playedLegs = pair.matches.filter(match => match.status === 'played').length;
        return pair;
    }).sort((a, b) => a.teamNames.join(' ').localeCompare(b.teamNames.join(' '), 'zh-CN'));
}

function renderCupGroupPairCard(pair, editable) {
    return `
        <section class="cup-group-pair-card ${pair.playedLegs === pair.matches.length ? 'is-complete' : ''}" data-cup-pair-key="${escapeHtml(pair.key)}">
            <header>
                <div><span>主客场对阵</span><strong>${pair.teamNames.map(name => escapeHtml(name)).join(' × ')}</strong></div>
                <em>${pair.playedLegs}/${pair.matches.length} 已录</em>
            </header>
            <div class="cup-group-pair-legs">
                ${pair.matches.map(match => `<div class="cup-group-pair-leg"><span class="cup-group-pair-round">第 ${Number(match.round_no)} 轮</span>${renderCupGroupMatchRow(match, editable)}</div>`).join('')}
            </div>
        </section>
    `;
}

function setCupResultsGroup(groupNo) {
    currentCupResultsGroupNo = Number(groupNo);
    renderCupGroupStageBoard();
}

function addCupGroupResultPair(groupNo) {
    const select = document.getElementById(`cup-group-pair-select-${Number(groupNo)}`);
    const pairKey = String(select?.value || '');
    if (!pairKey) return;
    cupGroupVisiblePairKeys.add(pairKey);
    renderCupGroupStageBoard();
    window.requestAnimationFrame(() => {
        document.querySelector(`[data-cup-pair-key="${pairKey}"] input[id^="cup-group-score-"]`)?.focus();
    });
}

function renderCupGroupResultsCard(group, editable) {
    const matches = group.matches || [];
    const played = matches.filter(match => match.status === 'played').length;
    if (!matches.length) {
        return `<article class="cup-group-results-card surface-card"><header><div><span>${escapeHtml(group.group_name)}</span><strong>${escapeHtml(group.group_name)} 组</strong></div><em>等待分组</em></header><div class="cup-group-results-empty">完成 6 支球队分组后，将自动生成主客场双循环赛程。</div></article>`;
    }
    const pairs = getCupGroupMatchPairs(group);
    const visiblePairs = editable
        ? pairs.filter(pair => pair.playedLegs > 0 || cupGroupVisiblePairKeys.has(pair.key))
        : pairs;
    const pendingPairs = editable
        ? pairs.filter(pair => pair.playedLegs === 0 && !cupGroupVisiblePairKeys.has(pair.key))
        : [];
    return `
        <article class="cup-group-results-card cup-group-ledger surface-card">
            <header><div><span>${escapeHtml(group.group_name)}</span><strong>${escapeHtml(group.group_name)} 组记分簿</strong></div><em id="cup-group-progress-${Number(group.group_no)}">${played}/${matches.length} 已赛</em></header>
            ${editable && pendingPairs.length ? `<div class="cup-group-pair-add">
                <label for="cup-group-pair-select-${Number(group.group_no)}"><span>添加一组主客场对阵</span><small>选择对手后，一次展开两个回合</small></label>
                <div><select id="cup-group-pair-select-${Number(group.group_no)}">${pendingPairs.map(pair => `<option value="${escapeHtml(pair.key)}">${pair.teamNames.map(name => escapeHtml(name)).join(' × ')}</option>`).join('')}</select><button class="btn btn-primary" type="button" onclick="addCupGroupResultPair(${Number(group.group_no)})">添加对阵</button></div>
            </div>` : ''}
            <div class="cup-group-pair-list">
                ${visiblePairs.map(pair => renderCupGroupPairCard(pair, editable)).join('') || `<div class="cup-group-results-empty"><strong>本组还没有录入比分</strong><span>${editable ? '从上方选择一组对手，主客场两个回合会一起出现。' : '等待比赛结果录入。'}</span></div>`}
            </div>
            ${editable && !pendingPairs.length ? '<div class="cup-group-pair-complete">本组全部主客场对阵均已加入记分簿</div>' : ''}
        </article>
    `;
}

function renderCupGroupResults(stage, editable) {
    const groups = stage.groups || [];
    if (!groups.length) return '<div class="cup-group-results-empty">当前没有可录入的小组。</div>';
    const selected = groups.find(group => Number(group.group_no) === Number(currentCupResultsGroupNo)) || groups[0];
    currentCupResultsGroupNo = Number(selected.group_no);
    return `
        <div class="cup-group-results-workbench">
            <nav class="cup-group-results-tabs" aria-label="选择杯赛小组">
                ${groups.map(group => {
                    const matches = group.matches || [];
                    const played = matches.filter(match => match.status === 'played').length;
                    return `<button class="${Number(group.group_no) === Number(selected.group_no) ? 'active' : ''}" type="button" onclick="setCupResultsGroup(${Number(group.group_no)})"><strong>${escapeHtml(group.group_name)} 组</strong><small>${played}/${matches.length || 0}</small></button>`;
                }).join('')}
            </nav>
            ${renderCupGroupResultsCard(selected, editable)}
        </div>
    `;
}

async function saveCupGroup(groupNo) {
    if (!canManageCurrentCompetitionSchedule()) return;
    const cupConfig = getCurrentCupConfig();
    const stage = getCurrentCupGroupStage();
    if (!cupConfig || !stage) return;
    const teamIds = [];
    try {
        for (let slotNo = 1; slotNo <= Number(stage.teams_per_group || 0); slotNo += 1) {
            const input = document.getElementById(`cup-group-team-${groupNo}-${slotNo}`);
            const team = resolveCupGroupTeamInput(input);
            teamIds.push(team ? Number(team.id) : null);
            if (team && input) {
                input.value = team.name;
                input.dataset.teamId = String(team.id);
            }
        }
        const selectedIds = teamIds.filter(Boolean);
        if (new Set(selectedIds).size !== selectedIds.length) throw new Error('同一小组不能重复选择球队。');
    } catch (error) {
        showModal('保存失败', escapeHtml(error.message || '请检查球队选择。'));
        return;
    }
    const button = document.getElementById(`cup-group-save-${groupNo}`);
    const state = document.getElementById(`cup-group-save-state-${groupNo}`);
    setUiButtonBusy(button, true, '保存中');
    if (state) state.textContent = '正在保存';
    const result = await workJsonRequest(`/api/admin/cups/${cupConfig.key}/groups/${groupNo}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({team_ids: teamIds}),
    });
    if (!result) {
        if (button?.isConnected) setUiButtonBusy(button, false);
        if (state?.isConnected) state.textContent = '保存失败';
        return;
    }
    const {response, data} = result;
    if (!response.ok || !data.success) {
        if (button?.isConnected) setUiButtonBusy(button, false);
        if (state?.isConnected) state.textContent = '保存失败';
        showModal('保存失败', escapeHtml(data.detail || data.message || '保存杯赛小组失败'));
        return;
    }
    invalidateCompetitionSections();
    await loadCompetitionData({force: true});
    showUiToast(data.message || '杯赛小组已保存', 'success');
}

function renderCupGroupStageBoard() {
    closeCupGroupSuggestions();
    const container = document.getElementById('cupGroupStageBoard');
    const cupConfig = getCurrentCupConfig();
    if (!container || !cupConfig) return;
    if (cupConfig.key === 'wumingjian_cup') {
        renderWumingjianQualificationBoard();
        return;
    }
    const stage = getCurrentCupGroupStage();
    if (!cupConfig.groupCount) {
        container.innerHTML = `
            <section class="cup-group-stage-shell ${escapeHtml(cupConfig.className)}">
                <div class="cup-group-stage-head surface-card"><div><span>GROUP STAGE</span><h2>${escapeHtml(currentCompetitionLevel)}小组赛</h2></div><em>暂未配置</em></div>
                <div class="cup-group-stage-empty surface-card"><div class="cup-group-stage-symbol" aria-hidden="true"><i></i><i></i><i></i><i></i></div><strong>当前杯赛没有小组赛配置</strong><p>无铭剑杯继续从淘汰赛阶段开始。</p></div>
            </section>
        `;
        return;
    }
    if (!stage) {
        container.innerHTML = renderUiState({tone: 'danger', title: '小组赛读取失败', message: '请刷新页面后重新读取。', actionLabel: '重新读取', actionOnclick: 'loadCompetitionData({force:true})', compact: true});
        return;
    }
    const totalSlots = Number(stage.group_count) * Number(stage.teams_per_group);
    const assigned = Number(stage.assigned_team_count || 0);
    const groupEditable = canManageCurrentCompetitionSchedule();
    const resultsEditable = canManageCurrentCupStandings();
    container.innerHTML = `
        <section class="cup-group-stage-shell ${escapeHtml(cupConfig.className)}">
            <div class="cup-group-stage-head surface-card">
                <div><span>GROUP STAGE</span><h2>${escapeHtml(currentCompetitionLevel)}小组赛</h2><p>${stage.group_count} 个小组，每组 ${stage.teams_per_group} 支球队 · 主客场双循环 10 轮</p></div>
                <em>${currentCupGroupScheduleView === 'results' ? '比分自动计分' : (assigned === totalSlots ? '分组已完整' : `已分配 ${assigned}/${totalSlots}`)}</em>
            </div>
            ${currentCupGroupScheduleView === 'groups'
                ? `${groupEditable ? '<div class="cup-group-edit-note surface-card">输入球队名的几个字母即可筛选现有球队；同一球队在本项杯赛中只能进入一个小组。修改完成后按组保存。</div>' : ''}<div class="cup-group-grid">${(stage.groups || []).map(group => renderCupGroupCard(group, Number(stage.teams_per_group), groupEditable)).join('')}</div>`
                : `${resultsEditable ? '<div class="cup-group-edit-note surface-card">先选组别，再逐对添加主客场双方；两个回合放在同一张卡中，比分完整后自动保存并更新积分榜。</div>' : ''}${renderCupGroupResults(stage, resultsEditable)}`}
        </section>
    `;
}

function setPlayerRankingType(type) {
    currentPlayerRankingType = ['goals', 'assists', 'mvps'].includes(type) ? type : 'goals';
    document.getElementById('playerRankingGoalsTab')?.classList.toggle('active', currentPlayerRankingType === 'goals');
    document.getElementById('playerRankingAssistsTab')?.classList.toggle('active', currentPlayerRankingType === 'assists');
    document.getElementById('playerRankingMvpsTab')?.classList.toggle('active', currentPlayerRankingType === 'mvps');
    document.getElementById('playerRankingGoalsTab')?.setAttribute('aria-selected', currentPlayerRankingType === 'goals' ? 'true' : 'false');
    document.getElementById('playerRankingAssistsTab')?.setAttribute('aria-selected', currentPlayerRankingType === 'assists' ? 'true' : 'false');
    document.getElementById('playerRankingMvpsTab')?.setAttribute('aria-selected', currentPlayerRankingType === 'mvps' ? 'true' : 'false');
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

function getPlayerRankingCoverage(level = currentCompetitionLevel) {
    const row = (playerRankingData.coverage || []).find(item => item.level === level) || {};
    return {
        level,
        played_matches: Number(row.played_matches || 0),
        matches_with_events: Number(row.matches_with_events || 0),
        matches_missing_events: Number(row.matches_missing_events || 0),
        event_rows: Number(row.event_rows || 0),
        goal_quantity: Number(row.goal_quantity || 0),
        assist_quantity: Number(row.assist_quantity || 0),
        mvp_quantity: Number(row.mvp_quantity || 0),
    };
}

function renderPlayerRankingCoverage() {
    const coverage = getPlayerRankingCoverage();
    const note = coverage.matches_missing_events > 0
        ? `还有 ${coverage.matches_missing_events} 场已赛比赛待补球员明细`
        : (coverage.played_matches > 0 ? '已赛比赛均已录入球员明细' : '暂无已赛比赛');
    return `
        <div class="player-ranking-coverage" aria-label="${escapeHtml(currentCompetitionLevel)}球员榜明细覆盖率">
            <span class="player-ranking-coverage-item"><strong>${coverage.played_matches}</strong><em>已赛</em></span>
            <span class="player-ranking-coverage-item"><strong>${coverage.matches_with_events}</strong><em>已录明细</em></span>
            <span class="player-ranking-coverage-item ${coverage.matches_missing_events > 0 ? 'is-warning' : ''}"><strong>${coverage.matches_missing_events}</strong><em>待补</em></span>
            <span class="player-ranking-coverage-note">${escapeHtml(note)}</span>
        </div>
    `;
}

function renderPlayerRankingPlayerName(row, extraClass = '') {
    const uid = Number(row.player_uid || 0);
    const name = escapeHtml(row.player_name || '-');
    if (!Number.isInteger(uid) || uid <= 0) {
        return `<span class="${extraClass}">${name}</span>`;
    }
    return `<button class="player-ranking-player-link ${extraClass}" type="button" onclick="openCompetitionPlayerAttributeDetail(${uid}, 'playerRankings')">${name}</button>`;
}

function renderPlayerRankingsBoard() {
    const container = document.getElementById('playerRankingsBoard');
    if (!container) return;
    const metricLabel = currentPlayerRankingType === 'assists' ? '助攻' : (currentPlayerRankingType === 'mvps' ? '最佳' : '进球');
    const title = currentPlayerRankingType === 'assists' ? '助攻榜' : (currentPlayerRankingType === 'mvps' ? '最佳球员榜' : '射手榜');
    const rows = getPlayerRankingRows();
    const coverage = getPlayerRankingCoverage();
    if (!rows.length) {
        const emptyText = coverage.played_matches > 0 && coverage.matches_with_events === 0
            ? `当前已赛 ${coverage.played_matches} 场，尚未录入球员明细。`
            : (coverage.matches_with_events > 0 ? `当前没有${metricLabel}记录，已有 ${coverage.matches_with_events} 场录入球员明细。` : `暂无${currentCompetitionLevel}${title}数据。`);
        container.innerHTML = `
            <section class="player-ranking-panel surface-card">
                <div class="table-header-row standings-header-row">
                    <h2 class="table-title">${escapeHtml(currentCompetitionLevel)}${title}</h2>
                </div>
                ${renderPlayerRankingCoverage()}
                <div class="no-data">${escapeHtml(emptyText)}</div>
            </section>
        `;
        renderCompetitionDataStatus();
        return;
    }
    container.innerHTML = `
        <section class="player-ranking-panel surface-card">
            <div class="table-header-row standings-header-row">
                <h2 class="table-title">${escapeHtml(currentCompetitionLevel)}${title}</h2>
            </div>
            ${renderPlayerRankingCoverage()}
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
                                <td class="team-name-cell" title="${escapeHtml(row.player_name || '-')}">${renderPlayerRankingPlayerName(row)}</td>
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
    renderCompetitionDataStatus();
}

function renderMobilePlayerRankingCards(rows, metricLabel) {
    return `
        <div class="mobile-player-ranking-list" aria-label="${escapeHtml(currentCompetitionLevel)}${escapeHtml(metricLabel)}榜">
            ${rows.map(row => {
                const rowKey = String(row.player_uid || `${row.player_name || ''}:${row.team_name || ''}`);
                const expanded = expandedMobilePlayerRankingRows.has(rowKey);
                const detailsId = `mobilePlayerRankingDetails-${Number(row.rank || 0)}`;
                const playerUid = Number(row.player_uid || 0);
                return `
                <article class="mobile-player-ranking-card ${expanded ? 'is-expanded' : ''}">
                    <button class="mobile-player-ranking-row-toggle" type="button" onclick="toggleMobilePlayerRankingRow(${htmlJsString(rowKey)})" aria-expanded="${expanded ? 'true' : 'false'}" aria-controls="${detailsId}" aria-label="${expanded ? '收起' : '展开'} ${escapeHtml(row.player_name || '-')}详细数据">
                        <span class="mobile-player-ranking-rank">${Number(row.rank || 0)}</span>
                        <strong class="mobile-player-ranking-name">${escapeHtml(row.player_name || '-')}</strong>
                        <span class="mobile-player-ranking-metric">
                            <strong>${Number(currentPlayerRankingType === 'assists' ? row.assists || 0 : (currentPlayerRankingType === 'mvps' ? row.mvps || 0 : row.goals || 0))}</strong>
                            <span>${escapeHtml(metricLabel)}</span>
                        </span>
                        <span class="mobile-player-ranking-chevron" aria-hidden="true">${uiIconSvg('chevron-down', 'ui-icon is-small')}</span>
                        <small class="mobile-player-ranking-team">${escapeHtml(row.team_name || '-')}</small>
                    </button>
                    ${expanded ? `<div class="mobile-player-ranking-details" id="${detailsId}"><div class="mobile-player-ranking-stats">
                            <span><em>进球</em>${Number(row.goals || 0)}</span>
                            <span><em>助攻</em>${Number(row.assists || 0)}</span>
                            <span><em>最佳</em>${Number(row.mvps || 0)}</span>
                            <span><em>出场</em>${Number(row.appearances || 0)}</span>
                        </div><div class="mobile-player-ranking-actions">${Number.isInteger(playerUid) && playerUid > 0 ? `<button type="button" onclick="openCompetitionPlayerAttributeDetail(${playerUid}, 'playerRankings')">查看球员</button>` : ''}<button type="button" onclick="viewTeamPlayers(${htmlJsString(row.team_name || '')})">查看球队</button></div></div>` : ''}
                </article>
            `;}).join('')}
        </div>
    `;
}

function toggleMobilePlayerRankingRow(rowKey) {
    const key = String(rowKey || '');
    if (!key) return;
    if (expandedMobilePlayerRankingRows.has(key)) expandedMobilePlayerRankingRows.delete(key);
    else expandedMobilePlayerRankingRows.add(key);
    renderPlayerRankingsBoard();
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
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

function resetSuspensionEditorFields(teamId, mode = 'merge') {
    const yellowInput = document.getElementById(`suspension-yellows-${teamId}`);
    const yellowSuspendedInput = document.getElementById(`suspension-yellow-suspended-${teamId}`);
    const redInput = document.getElementById(`suspension-red-${teamId}`);
    const injuryInput = document.getElementById(`suspension-injury-${teamId}`);
    const matchesInput = document.getElementById(`suspension-matches-${teamId}`);
    const notesInput = document.getElementById(`suspension-notes-${teamId}`);
    if (yellowInput) yellowInput.value = '0';
    if (yellowSuspendedInput) yellowSuspendedInput.checked = false;
    if (redInput) redInput.checked = false;
    if (injuryInput) injuryInput.checked = false;
    if (matchesInput) matchesInput.value = '1';
    if (notesInput) notesInput.value = '';
    suspensionRecordEntryModes.set(Number(teamId), mode);
    suspensionRecordLastSavedSignatures.delete(Number(teamId));
}

function selectSuspensionSuggestion(button, teamId, playerUid) {
    const input = document.getElementById(`suspension-player-${teamId}`) || activeSuspensionSuggestionContext?.input;
    const team = findSuspensionTeam(teamId);
    const player = getTeamPlayersForSuspension(team).find(item => Number(item.uid || 0) === Number(playerUid));
    if (!input || !player) return;
    const previousUid = Number(input.dataset.playerUid || 0);
    const keepManualEdit = suspensionRecordEntryModes.get(Number(teamId)) === 'replace'
        && previousUid === Number(player.uid || 0);
    input.value = player.name || '';
    input.dataset.playerUid = String(Number(player.uid || 0));
    closeSuspensionSuggestions();
    const existing = findLocalSuspensionRecordForPlayer(player, teamId);
    if (existing && keepManualEdit) {
        fillSuspensionEditor(teamId, player.uid);
    } else {
        resetSuspensionEditorFields(teamId, 'merge');
    }
    input.dispatchEvent(new Event('change', {bubbles: true}));
}

function handleSuspensionPlayerInput(input, teamId) {
    if (input?.dataset) delete input.dataset.playerUid;
    resetSuspensionEditorFields(teamId, 'merge');
    updateSuspensionSuggestions(input, teamId);
    setSuspensionRecordSaveState(teamId, '', '选择球员后自动保存');
}

function handleSuspensionPlayerBlur(input, teamId) {
    scheduleCloseSuspensionSuggestions(input);
    if (!Number(input?.dataset?.playerUid || 0)) {
        try {
            const player = resolveSuspensionPlayer(teamId);
            const existing = player ? findLocalSuspensionRecordForPlayer(player, teamId) : null;
            if (player) input.dataset.playerUid = String(Number(player.uid || 0));
            if (existing && suspensionRecordEntryModes.get(Number(teamId)) === 'replace') {
                fillSuspensionEditor(teamId, player.uid);
            }
        } catch (error) {
            setSuspensionRecordSaveState(teamId, 'error', error.message || '请从候选列表选择球员');
            return;
        }
    }
    queueSuspensionRecordSave(teamId, true);
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
    if (record.yellow_card_suspended) labels.push('3黄停赛');
    if (yellows > 0) labels.push(`额外${yellows}黄`);
    if (record.red_card_suspended) labels.push('红牌');
    if (record.red_injury_suspended) labels.push('红伤');
    if (record.yellow_card_suspended || record.red_card_suspended || record.red_injury_suspended) {
        const total = Math.max(1, Number(record.suspension_matches || 1));
        const remaining = Math.max(0, Number(record.suspension_remaining_matches ?? total));
        const rounds = [...new Set((record.suspension_affected_rounds || []).map(Number).filter(Number.isInteger))];
        labels.push(`停赛共${total}场${remaining < total ? `，剩余${remaining}场` : ''}${rounds.length ? `，影响${rounds.map(roundNo => `第${roundNo}轮`).join('、')}` : ''}`);
    }
    return labels.join(' / ') || '记录';
}

function renderSuspensionPlayers(records, emptyText, isOrphaned = false) {
    if (!records || !records.length) {
        return `<span class="suspension-empty" title="${escapeHtml(emptyText)}">-</span>`;
    }
    return records.map(record => `
        <div class="suspension-player-row">
            <div class="suspension-player-main">
                ${isOrphaned
                    ? `<strong title="${escapeHtml(record.player_name)}">${escapeHtml(record.player_name)}</strong>`
                    : `<button class="player-link suspension-player-detail-link" type="button" title="${escapeHtml(record.player_name)}" onclick="openCompetitionPlayerAttributeDetail(${Number(record.player_uid)}, 'suspensions')">${escapeHtml(record.player_name)}</button>`}
                <span>${escapeHtml(getSuspensionRecordLabel(record))}</span>
                ${isOrphaned ? `<span>原记录：${escapeHtml(record.team_name || '未知球队')}</span>` : ''}
                ${record.notes ? `<em title="${escapeHtml(record.notes)}">${escapeHtml(record.notes)}</em>` : ''}
            </div>
            ${canManageCurrentCompetitionSuspensions() ? `
                <div class="suspension-row-actions capture-exclude">
                    ${isOrphaned ? '' : `<button type="button" class="suspension-link-btn" onclick="openSuspensionEditor(${Number(record.team_id || 0)}, ${Number(record.player_uid)})">编辑</button>`}
                    <button type="button" class="suspension-link-btn danger" onclick="clearSuspensionRecord(${Number(record.player_uid)})">清除</button>
                </div>
            ` : ''}
        </div>
    `).join('');
}

function renderSuspensionEditor(team) {
    if (!canManageCurrentCompetitionSuspensions() || team.is_orphaned) return '';
    const teamId = Number(team.team_id || 0);
    if (Number(activeSuspensionEditorTeamId || 0) !== teamId) return '';
    return `
        <div class="suspension-editor capture-exclude">
            <div class="suspension-player-field">
                <div class="suspension-player-input-row">
                    <input id="suspension-player-${teamId}" class="suspension-player-input" type="text" placeholder="输入球员名或 UID" autocomplete="off" aria-describedby="suspension-record-state-${teamId}" oninput="handleSuspensionPlayerInput(this, ${teamId})" onchange="queueSuspensionRecordSave(${teamId})" onfocus="updateSuspensionSuggestions(this, ${teamId}, true)" onblur="handleSuspensionPlayerBlur(this, ${teamId})" onkeydown="handleSuspensionPlayerKeydown(event)">
                    <button class="suspension-player-toggle" type="button" title="选择球员" aria-label="选择球员" onclick="toggleSuspensionSuggestions(this, ${teamId})">▾</button>
                </div>
            </div>
            <select id="suspension-yellows-${teamId}" aria-label="本次新增或当前额外黄牌数" title="新增录入时填写本次黄牌；编辑已有记录时表示3黄停赛之外的额外黄牌" onchange="queueSuspensionRecordSave(${teamId}, true)">
                <option value="0">0黄</option>
                <option value="1">1黄</option>
                <option value="2">2黄</option>
                <option value="3">3黄（触发停赛）</option>
            </select>
            <label class="suspension-check"><input id="suspension-yellow-suspended-${teamId}" type="checkbox" onchange="queueSuspensionRecordSave(${teamId}, true)">3黄停赛</label>
            <label class="suspension-check"><input id="suspension-red-${teamId}" type="checkbox" onchange="queueSuspensionRecordSave(${teamId}, true)">红牌</label>
            <label class="suspension-check"><input id="suspension-injury-${teamId}" type="checkbox" onchange="queueSuspensionRecordSave(${teamId}, true)">红伤</label>
            <label class="suspension-matches-field"><span>停赛场次</span><input id="suspension-matches-${teamId}" type="number" min="1" max="99" step="1" inputmode="numeric" value="1" onchange="queueSuspensionRecordSave(${teamId}, true)" onblur="queueSuspensionRecordSave(${teamId}, true)"></label>
            <input id="suspension-notes-${teamId}" type="text" placeholder="备注" oninput="queueSuspensionRecordSave(${teamId})" onblur="queueSuspensionRecordSave(${teamId}, true)">
            <span class="ui-save-state suspension-record-save-state" id="suspension-record-state-${teamId}" aria-live="polite">选择球员后自动保存</span>
        </div>
    `;
}

function renderSuspensionTeamActions(team) {
    if (!canManageCurrentCompetitionSuspensions() || team.is_orphaned) return '';
    const teamId = Number(team.team_id || 0);
    const isOpen = Number(activeSuspensionEditorTeamId || 0) === teamId;
    return `
        <button class="suspension-maintain-btn capture-exclude" type="button" onclick="toggleSuspensionEditor(${teamId})" aria-label="${isOpen ? '完成编辑' : '编辑'} ${escapeHtml(team.team_name)}伤停记录">
            ${isOpen ? '完成' : '编辑'}
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

function getSuspensionUpdateRound(level) {
    const rawValue = siteNotesData[getSuspensionNoteKey(level)]?.round_no;
    if (rawValue === null || rawValue === undefined || rawValue === '') return null;
    const value = Number(rawValue);
    return Number.isInteger(value) && value >= 0 ? value : null;
}

function getSuspensionTeamNoteKey(teamId) {
    return `competition.suspensions.team.${Number(teamId)}`;
}

function getSuspensionTeamNote(teamId) {
    return String(siteNotesData[getSuspensionTeamNoteKey(teamId)]?.text || '').trim();
}

function getSuspensionTeamRound(teamId) {
    const rawValue = siteNotesData[getSuspensionTeamNoteKey(teamId)]?.round_no;
    if (rawValue === null || rawValue === undefined || rawValue === '') return null;
    const value = Number(rawValue);
    return Number.isInteger(value) && value >= 0 ? value : null;
}

function formatSuspensionRoundProgress(roundNo, missingLabel = '伤停轮次待补充') {
    if (roundNo === null || roundNo === undefined) return missingLabel;
    const numericRound = Number(roundNo);
    if (!Number.isInteger(numericRound) || numericRound < 0) return missingLabel;
    if (numericRound === 0) return '赛季初核对完成 · 适用于第 1 轮';
    if (numericRound >= 34) return `核对至第 ${numericRound} 轮 · 赛季轮次已核对完成`;
    return `核对至第 ${numericRound} 轮 · 适用于第 ${numericRound + 1} 轮`;
}

function renderSuspensionTeamNote(team) {
    if (team.is_orphaned) return '';
    const teamId = Number(team.team_id || 0);
    const note = getSuspensionTeamNote(teamId);
    const roundNo = getSuspensionTeamRound(teamId);
    const progress = team?.progress || null;
    const progressTitle = String(progress?.title || formatSuspensionRoundProgress(roundNo, '轮次未标注')).trim();
    const progressDetail = String(progress?.detail || '').trim();
    const editing = canManageCurrentCompetitionSuspensions() && Number(activeSuspensionEditorTeamId || 0) === teamId;
    return `
        <div class="suspension-team-note is-${escapeHtml(progress?.state || 'unknown')}">
            <strong>更新进度</strong>
            <div class="suspension-team-progress-copy">
                <span id="suspension-team-progress-display-${teamId}">${escapeHtml(progressTitle)}${note ? ` · ${escapeHtml(note)}` : ''}</span>
                ${progressDetail ? `<small>${escapeHtml(progressDetail)}</small>` : ''}
            </div>
        </div>
        ${editing ? `<div class="suspension-team-note-editor capture-exclude">
            <label class="suspension-round-field"><span>核对至第</span><input id="suspension-team-round-${teamId}" type="number" min="0" max="34" inputmode="numeric" value="${roundNo ?? ''}" placeholder="轮次" aria-label="伤停核对至第几轮" oninput="queueSuspensionProgressSave('team', ${teamId})" onblur="queueSuspensionProgressSave('team', ${teamId}, true)"><small>轮 · 适用于下一轮</small></label>
            <input id="suspension-team-note-${teamId}" type="text" maxlength="160" value="${escapeHtml(note)}" placeholder="可选备注，例如赛后已核对" oninput="queueSuspensionProgressSave('team', ${teamId})" onblur="queueSuspensionProgressSave('team', ${teamId}, true)">
            <span class="ui-save-state" id="suspension-progress-state-team-${teamId}" aria-live="polite">自动保存</span>
        </div>` : ''}
    `;
}

function renderSuspensionUpdateNote(level) {
    const note = getSuspensionUpdateNote(level);
    const roundNo = getSuspensionUpdateRound(level);
    const displayText = `${formatSuspensionRoundProgress(roundNo)}${note ? ` · ${note}` : ''}`;
    return `
        <div class="suspension-update-note">
            <span class="suspension-update-note-text" id="suspension-level-progress-display-${escapeHtml(level)}">${escapeHtml(displayText)}</span>
            ${canManageCurrentCompetitionSuspensions() ? `
                <div class="suspension-note-editor capture-exclude">
                    <label class="suspension-round-field"><span>核对至第</span><input id="suspension-round-${escapeHtml(level)}" type="number" min="0" max="34" inputmode="numeric" value="${roundNo ?? ''}" placeholder="轮次" aria-label="伤停核对至第几轮" oninput="queueSuspensionProgressSave('level', ${htmlJsString(level)})" onblur="queueSuspensionProgressSave('level', ${htmlJsString(level)}, true)"><small>轮 · 适用于下一轮</small></label>
                    <input id="suspension-note-${escapeHtml(level)}" type="text" maxlength="160" value="${escapeHtml(note)}" placeholder="可选备注，例如全部球队已核对" oninput="queueSuspensionProgressSave('level', ${htmlJsString(level)})" onblur="queueSuspensionProgressSave('level', ${htmlJsString(level)}, true)">
                    <span class="ui-save-state" id="suspension-progress-state-level-${escapeHtml(level)}" aria-live="polite">自动保存</span>
                </div>
            ` : ''}
        </div>
    `;
}

function getSuspensionTeamSummary(team) {
    const oneYellow = (team?.one_yellow || []).length;
    const twoYellows = (team?.two_yellows || []).length;
    const suspended = (team?.suspended || []).length;
    const notes = (team?.notes || []).filter(Boolean).length;
    return {
        cautionCount: oneYellow + twoYellows,
        suspendedCount: suspended,
        recordCount: oneYellow + twoYellows + suspended,
        hasContent: oneYellow + twoYellows + suspended + notes > 0,
    };
}

function suspensionTeamNeedsAttention(team) {
    if (team?.is_orphaned) return true;
    const levelRound = getSuspensionUpdateRound(currentCompetitionLevel);
    const teamRound = getSuspensionTeamRound(team?.team_id);
    return levelRound !== null && (teamRound === null || teamRound < levelRound);
}

function suspensionTeamMatchesFilter(team, filter = currentSuspensionViewFilter) {
    if (filter === 'all') return true;
    if (filter === 'attention') return suspensionTeamNeedsAttention(team);
    return getSuspensionTeamSummary(team).hasContent;
}

function setSuspensionViewFilter(filter) {
    currentSuspensionViewFilter = ['active', 'attention', 'all'].includes(filter) ? filter : 'active';
    activeSuspensionEditorTeamId = null;
    renderSuspensionsBoard();
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
}

function renderSuspensionViewFilters(teams) {
    const counts = {
        active: teams.filter(team => suspensionTeamMatchesFilter(team, 'active')).length,
        attention: teams.filter(team => suspensionTeamMatchesFilter(team, 'attention')).length,
        all: teams.length,
    };
    return `
        <div class="suspension-view-filters capture-exclude" role="tablist" aria-label="伤停球队筛选">
            ${[
                ['active', '有记录'],
                ['attention', '待处理'],
                ['all', '全部球队'],
            ].map(([value, label]) => `<button type="button" class="${currentSuspensionViewFilter === value ? 'active' : ''}" onclick="setSuspensionViewFilter('${value}')" role="tab" aria-selected="${currentSuspensionViewFilter === value ? 'true' : 'false'}"><span>${label}</span><strong>${counts[value]}</strong></button>`).join('')}
        </div>
    `;
}

function renderSuspensionFilteredEmpty() {
    const title = currentSuspensionViewFilter === 'attention' ? '当前没有待处理球队' : '当前没有伤停记录';
    const message = currentSuspensionViewFilter === 'attention'
        ? '历史异常以及伤停核对轮次缺失或落后的球队会集中显示在这里；正常停赛记录不会列入待处理。'
        : '当前级别没有黄牌关注或停赛记录，可切换到全部球队继续核对。';
    return `${renderUiState({tone: 'success', title, message, compact: true})}<button class="btn btn-secondary suspension-show-all-btn capture-exclude" type="button" onclick="setSuspensionViewFilter('all')">查看全部球队</button>`;
}

function renderSuspensionsBoard() {
    closeSuspensionSuggestions();
    const container = document.getElementById('suspensionsBoard');
    if (!container) return;
    const teamsForLevel = (suspensionData.teams || []).filter(team => team.level === currentCompetitionLevel);
    if (!teamsForLevel.length) {
        container.innerHTML = renderUiState({tone: 'empty', title: '暂无伤停统计数据', message: '当前级别没有已登记的伤停或纪律记录。', compact: true});
        renderCompetitionDataStatus();
        return;
    }
    const visibleTeams = teamsForLevel.filter(team => suspensionTeamMatchesFilter(team));
    container.innerHTML = `
        <section class="suspension-board exportable-panel" data-export-view="suspensions-${escapeHtml(currentCompetitionLevel)}">
            <div class="table-header-row standings-header-row">
                <div class="competition-title-stack">
                    <h2 class="table-title">${escapeHtml(currentCompetitionLevel)}伤停统计</h2>
                    ${renderSuspensionUpdateNote(currentCompetitionLevel)}
                </div>
                <div class="competition-header-actions capture-exclude">
                    <button class="btn btn-success competition-image-btn" type="button" onclick="exportSuspensionsExcel(${htmlJsString(currentCompetitionLevel)})">导出 Excel</button>
                    <button class="btn btn-secondary competition-image-btn" type="button" onclick="saveCompetitionImage('suspensions', ${htmlJsString(currentCompetitionLevel)})">保存图片</button>
                </div>
            </div>
            ${renderSuspensionViewFilters(teamsForLevel)}
            <div class="suspension-team-grid">
                ${visibleTeams.map(team => {
                    const teamId = Number(team.team_id || 0);
                    const summary = getSuspensionTeamSummary(team);
                    const editing = Number(activeSuspensionEditorTeamId || 0) === teamId;
                    const expanded = summary.hasContent || expandedMobileSuspensionTeams.has(teamId) || editing;
                    const editable = canManageCurrentCompetitionSuspensions() && !team.is_orphaned;
                    const detailsId = `suspensionTeamDetails-${teamId}`;
                    const {cautionCount, suspendedCount} = summary;
                    return `
                    <article class="suspension-team-card ${team.is_orphaned ? 'is-orphaned' : ''} ${expanded ? 'is-expanded' : ''} ${editable ? 'is-editable' : ''} ${editing ? 'is-editing' : ''}"
                        ${editable ? `onclick="handleSuspensionTeamCardClick(event, ${teamId})"` : ''}>
                        <header class="suspension-team-head">
                            <div>
                                <h3>${escapeHtml(team.team_name)}</h3>
                                <span>${team.is_orphaned ? '可直接清除已离队或球队不一致的历史记录' : renderCoachProfileLink(team.manager, 'coach-profile-link suspension-coach-link')}</span>
                            </div>
                            <div class="suspension-team-quick-stats"><span><strong>${cautionCount}</strong>黄牌关注</span><span class="${suspendedCount ? 'has-suspension' : ''}"><strong>${suspendedCount}</strong>停赛</span></div>
                            ${renderSuspensionTeamActions(team)}
                        </header>
                        ${renderSuspensionTeamNote(team)}
                        ${expanded ? `<div class="suspension-team-details" id="${detailsId}">
                        <div class="suspension-columns">
                            <section class="is-one-yellow">
                                <h4>1张黄牌</h4>
                                <div class="suspension-section-list">${renderSuspensionPlayers(team.one_yellow, '暂无', team.is_orphaned)}</div>
                            </section>
                            <section class="is-two-yellows">
                                <h4>2张黄牌</h4>
                                <div class="suspension-section-list">${renderSuspensionPlayers(team.two_yellows, '暂无', team.is_orphaned)}</div>
                            </section>
                            <section class="is-suspended">
                                <h4>停赛</h4>
                                <div class="suspension-section-list">${renderSuspensionPlayers(team.suspended, '暂无', team.is_orphaned)}</div>
                            </section>
                        </div>
                        ${renderSuspensionNotes(team.notes)}
                        ${renderSuspensionEditor(team)}
                        </div>` : ''}
                    </article>
                `;}).join('') || renderSuspensionFilteredEmpty()}
            </div>
        </section>
    `;
    renderCompetitionDataStatus();
}

function toggleMobileSuspensionTeam(teamId) {
    const numericTeamId = Number(teamId || 0);
    if (!numericTeamId) return;
    if (expandedMobileSuspensionTeams.has(numericTeamId)) expandedMobileSuspensionTeams.delete(numericTeamId);
    else expandedMobileSuspensionTeams.add(numericTeamId);
    renderSuspensionsBoard();
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
}

function suspensionCardClickTargetIsInteractive(target) {
    return Boolean(target?.closest?.('button, a, input, select, textarea, label'));
}

function handleSuspensionTeamCardClick(event, teamId) {
    if (!canManageCurrentCompetitionSuspensions() || suspensionCardClickTargetIsInteractive(event?.target)) return;
    if (Number(activeSuspensionEditorTeamId || 0) === Number(teamId)) return;
    openSuspensionEditor(teamId);
}

async function ensureCompetitionPlayersLoaded() {
    if ((allPlayers || []).length) return true;
    try {
        await ensurePlayersLoaded();
        invalidateCompetitionPlayerCaches();
        return true;
    } catch (error) {
        console.error('Failed to load players for competition editor:', error);
        showModal('球员名单加载失败', '暂时无法读取球员名单，请检查网络后重试。');
        return false;
    }
}

async function toggleSuspensionEditor(teamId) {
    if (!canManageCurrentCompetitionSuspensions()) return;
    const numericTeamId = Number(teamId);
    const opening = Number(activeSuspensionEditorTeamId || 0) !== numericTeamId;
    if (opening && !await ensureCompetitionPlayersLoaded()) return;
    if (activeSuspensionEditorTeamId) queueSuspensionRecordSave(activeSuspensionEditorTeamId, true);
    activeSuspensionEditorTeamId = opening ? numericTeamId : null;
    if (opening) {
        expandedMobileSuspensionTeams.add(numericTeamId);
        suspensionRecordEntryModes.set(numericTeamId, 'merge');
    }
    renderSuspensionsBoard();
}

function getSuspensionProgressSaveKey(scope, identifier) {
    return scope === 'team' ? `team:${Number(identifier)}` : `level:${String(identifier || '').trim()}`;
}

function getSuspensionProgressPayload(scope, identifier) {
    const normalizedScope = scope === 'team' ? 'team' : 'level';
    const normalizedId = normalizedScope === 'team' ? Number(identifier) : String(identifier || '').trim();
    const input = document.getElementById(normalizedScope === 'team' ? `suspension-team-note-${normalizedId}` : `suspension-note-${normalizedId}`);
    const roundInput = document.getElementById(normalizedScope === 'team' ? `suspension-team-round-${normalizedId}` : `suspension-round-${normalizedId}`);
    if (!input || !roundInput) return null;
    const roundValue = String(roundInput.value || '').trim();
    const roundNo = roundValue === '' ? null : Number(roundValue);
    if (roundNo !== null && (!Number.isInteger(roundNo) || roundNo < 0 || roundNo > 34)) {
        return {error: '已核对完轮次只能填写 0 到 34'};
    }
    return {
        scope: normalizedScope,
        identifier: normalizedId,
        noteKey: normalizedScope === 'team' ? getSuspensionTeamNoteKey(normalizedId) : getSuspensionNoteKey(normalizedId),
        text: String(input.value || '').trim(),
        roundNo,
    };
}

function setSuspensionProgressSaveState(scope, identifier, state, message) {
    const normalizedId = scope === 'team' ? Number(identifier) : String(identifier || '').trim();
    const element = document.getElementById(`suspension-progress-state-${scope}-${normalizedId}`);
    if (!element) return;
    element.className = `ui-save-state${state ? ` is-${state}` : ''}`;
    element.textContent = message;
}

function updateSuspensionProgressDisplay(payload) {
    const displayText = `${formatSuspensionRoundProgress(payload.roundNo, payload.scope === 'team' ? '轮次未标注' : '伤停轮次待补充')}${payload.text ? ` · ${payload.text}` : ''}`;
    const display = document.getElementById(payload.scope === 'team'
        ? `suspension-team-progress-display-${payload.identifier}`
        : `suspension-level-progress-display-${payload.identifier}`);
    if (display) display.textContent = displayText;
}

function queueSuspensionProgressSave(scope, identifier, immediate = false) {
    if (!canManageCurrentCompetitionSuspensions()) return;
    const normalizedScope = scope === 'team' ? 'team' : 'level';
    const key = getSuspensionProgressSaveKey(normalizedScope, identifier);
    const version = Number(suspensionProgressSaveVersions.get(key) || 0) + 1;
    suspensionProgressSaveVersions.set(key, version);
    const existingTimer = suspensionProgressSaveTimers.get(key);
    if (existingTimer) window.clearTimeout(existingTimer);
    setSuspensionProgressSaveState(normalizedScope, identifier, 'saving', immediate ? '正在保存' : '等待保存');
    if (immediate) {
        suspensionProgressSaveTimers.delete(key);
        saveSuspensionProgress(normalizedScope, identifier, version);
        return;
    }
    suspensionProgressSaveTimers.set(key, window.setTimeout(() => {
        suspensionProgressSaveTimers.delete(key);
        saveSuspensionProgress(normalizedScope, identifier, version);
    }, 650));
}

async function saveSuspensionProgress(scope, identifier, requestedVersion = null) {
    if (!canManageCurrentCompetitionSuspensions()) return;
    const key = getSuspensionProgressSaveKey(scope, identifier);
    const latestVersion = Number(suspensionProgressSaveVersions.get(key) || 0);
    const version = requestedVersion === null ? latestVersion : Number(requestedVersion);
    if (version !== latestVersion) return;
    if (suspensionProgressSaveInFlight.has(key)) return;
    const payload = getSuspensionProgressPayload(scope, identifier);
    if (!payload) return;
    if (payload.error) {
        setSuspensionProgressSaveState(scope, identifier, 'error', payload.error);
        return;
    }
    suspensionProgressSaveInFlight.add(key);
    setSuspensionProgressSaveState(scope, identifier, 'saving', '保存中');
    try {
        const requestOptions = {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text: payload.text, round_no: payload.roundNo}),
        };
        let result;
        try {
            result = await workJsonRequest(`/api/admin/site-notes/${encodeURIComponent(payload.noteKey)}`, requestOptions);
        } catch (error) {
            console.warn('Suspension progress autosave interrupted; retrying once:', error);
            setSuspensionProgressSaveState(scope, identifier, 'saving', '网络波动，正在重试');
            await new Promise(resolve => window.setTimeout(resolve, 900));
            if (Number(suspensionProgressSaveVersions.get(key) || 0) !== version) return;
            result = await workJsonRequest(`/api/admin/site-notes/${encodeURIComponent(payload.noteKey)}`, requestOptions);
        }
        if (!result) {
            setSuspensionProgressSaveState(scope, identifier, 'error', '保存失败');
            return;
        }
        const {response, data} = result;
        if (!response.ok || !data.success) {
            setSuspensionProgressSaveState(scope, identifier, 'error', data.detail || data.message || '保存失败');
            return;
        }
        siteNotesData[payload.noteKey] = {
            ...(siteNotesData[payload.noteKey] || {}),
            key: payload.noteKey,
            text: payload.text,
            round_no: payload.roundNo,
            updated_at: new Date().toISOString(),
        };
        updateSuspensionProgressDisplay(payload);
        if (Number(suspensionProgressSaveVersions.get(key) || 0) === version) {
            setSuspensionProgressSaveState(scope, identifier, 'saved', '已保存');
        }
        try {
            renderCompetitionDataStatus();
        } catch (renderError) {
            console.error('Suspension progress saved but status refresh failed:', renderError);
        }
    } catch (error) {
        console.error('Failed to autosave suspension progress:', error);
        setSuspensionProgressSaveState(scope, identifier, 'error', '网络异常，稍后修改将自动重试');
    } finally {
        suspensionProgressSaveInFlight.delete(key);
        const nextVersion = Number(suspensionProgressSaveVersions.get(key) || 0);
        if (nextVersion > version) {
            const pendingTimer = suspensionProgressSaveTimers.get(key);
            if (pendingTimer) window.clearTimeout(pendingTimer);
            suspensionProgressSaveTimers.delete(key);
            saveSuspensionProgress(scope, identifier, nextVersion);
        }
    }
}

async function openSuspensionEditor(teamId, playerUid = null) {
    if (!canManageCurrentCompetitionSuspensions()) return;
    if (!await ensureCompetitionPlayersLoaded()) return;
    activeSuspensionEditorTeamId = Number(teamId);
    suspensionRecordEntryModes.set(Number(teamId), playerUid === null || playerUid === undefined ? 'merge' : 'replace');
    expandedMobileSuspensionTeams.add(Number(teamId));
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
    const input = document.getElementById(`suspension-player-${teamId}`);
    const raw = String(input?.value || '').trim();
    if (!team || !raw) return null;
    const players = getTeamPlayersForSuspension(team);
    const selectedUid = Number(input?.dataset?.playerUid || 0);
    if (selectedUid > 0) {
        const selected = players.find(player => Number(player.uid || 0) === selectedUid);
        if (selected) return selected;
    }
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

function setSuspensionRecordSaveState(teamId, state, message) {
    const element = document.getElementById(`suspension-record-state-${Number(teamId)}`);
    if (!element) return;
    element.className = `ui-save-state suspension-record-save-state${state ? ` is-${state}` : ''}`;
    element.textContent = message;
}

function getSuspensionRecordDraft(teamId) {
    const numericTeamId = Number(teamId || 0);
    let player = null;
    try {
        player = resolveSuspensionPlayer(numericTeamId);
    } catch (error) {
        return {error: error.message || '请从候选列表选择球员。'};
    }
    if (!player) return {error: '请先选择球员'};
    const mergeMode = suspensionRecordEntryModes.get(numericTeamId) !== 'replace';
    const mergeBaseYellowCards = getLocalSuspensionRecordsForPlayer(player, numericTeamId)
        .reduce((total, record) => total + Number(record.yellow_cards || 0), 0);
    const yellowCards = Number(document.getElementById(`suspension-yellows-${numericTeamId}`)?.value || 0);
    const suspensionMatches = Number(document.getElementById(`suspension-matches-${numericTeamId}`)?.value || 1);
    if (!Number.isInteger(suspensionMatches) || suspensionMatches < 1 || suspensionMatches > 99) {
        return {error: '停赛场次只能填写 1 到 99'};
    }
    const payload = {
        player_uid: Number(player.uid),
        yellow_cards: yellowCards,
        yellow_card_suspended: Boolean(document.getElementById(`suspension-yellow-suspended-${numericTeamId}`)?.checked),
        red_card_suspended: Boolean(document.getElementById(`suspension-red-${numericTeamId}`)?.checked),
        red_injury_suspended: Boolean(document.getElementById(`suspension-injury-${numericTeamId}`)?.checked),
        suspension_matches: suspensionMatches,
        notes: String(document.getElementById(`suspension-notes-${numericTeamId}`)?.value || '').trim(),
        merge_existing: mergeMode,
        merge_base_yellow_cards: mergeMode ? mergeBaseYellowCards : null,
    };
    return {teamId: numericTeamId, player, payload, signature: JSON.stringify(payload)};
}

function findLocalSuspensionRecord(playerUid) {
    const uid = Number(playerUid || 0);
    for (const team of suspensionData.teams || []) {
        for (const group of ['one_yellow', 'two_yellows', 'suspended']) {
            const record = (team[group] || []).find(item => Number(item.player_uid || 0) === uid);
            if (record) return record;
        }
    }
    return null;
}

function normalizeSuspensionPlayerName(value) {
    return String(value || '').trim().toLocaleLowerCase().replace(/\s+/g, ' ');
}

function findLocalSuspensionRecordForPlayer(player, teamId) {
    return getLocalSuspensionRecordsForPlayer(player, teamId)[0] || null;
}

function getLocalSuspensionRecordsForPlayer(player, teamId) {
    const team = findSuspensionTeam(teamId);
    const normalizedName = normalizeSuspensionPlayerName(player?.name);
    if (!team || !normalizedName) return [];
    const records = [];
    const seenUids = new Set();
    for (const group of ['one_yellow', 'two_yellows', 'suspended']) {
        for (const record of team[group] || []) {
            if (Number(record.player_uid || 0) === Number(player?.uid || 0)
                || normalizeSuspensionPlayerName(record.player_name) === normalizedName) {
                const uid = Number(record.player_uid || 0);
                if (uid > 0 && seenUids.has(uid)) continue;
                if (uid > 0) seenUids.add(uid);
                records.push(record);
            }
        }
    }
    return records;
}

function removeSuspensionRecordFromLocalData(playerUid) {
    const uid = Number(playerUid || 0);
    for (const team of suspensionData.teams || []) {
        for (const group of ['one_yellow', 'two_yellows', 'suspended']) {
            team[group] = (team[group] || []).filter(item => Number(item.player_uid || 0) !== uid);
        }
        team.notes = [...new Set(['one_yellow', 'two_yellows', 'suspended']
            .flatMap(group => team[group] || [])
            .filter(item => String(item.notes || '').trim())
            .map(item => `${item.player_name}: ${item.notes}`))];
    }
}

function applySuspensionRecordToLocalData(teamId, player, payload, savedRecord = null) {
    const source = savedRecord || payload;
    removeSuspensionRecordFromLocalData(source.player_uid);
    const team = findSuspensionTeam(teamId);
    const normalizedName = normalizeSuspensionPlayerName(source.player_name || player?.name);
    if (team && normalizedName) {
        for (const group of ['one_yellow', 'two_yellows', 'suspended']) {
            team[group] = (team[group] || []).filter(item => normalizeSuspensionPlayerName(item.player_name) !== normalizedName);
        }
    }
    const isEmpty = Number(source.yellow_cards || 0) <= 0
        && !source.yellow_card_suspended
        && !source.red_card_suspended
        && !source.red_injury_suspended
        && !String(source.notes || '').trim();
    if (isEmpty) return;
    if (!team) return;
    const record = {
        player_uid: Number(source.player_uid),
        player_name: String(source.player_name || player?.name || ''),
        team_id: Number(source.team_id || team.team_id || teamId),
        team_name: String(source.team_name || team.team_name || ''),
        level: String(source.level || team.level || currentCompetitionLevel),
        yellow_cards: Number(source.yellow_cards || 0),
        yellow_card_suspended: Boolean(source.yellow_card_suspended),
        red_card_suspended: Boolean(source.red_card_suspended),
        red_injury_suspended: Boolean(source.red_injury_suspended),
        suspension_matches: Math.max(1, Number(source.suspension_matches || 1)),
        suspension_active: Boolean(source.suspension_active ?? (source.yellow_card_suspended || source.red_card_suspended || source.red_injury_suspended)),
        suspension_served_matches: Math.max(0, Number(source.suspension_served_matches || 0)),
        suspension_remaining_matches: Math.max(0, Number(source.suspension_remaining_matches ?? source.suspension_matches ?? 1)),
        suspension_affected_match_ids: Array.isArray(source.suspension_affected_match_ids) ? source.suspension_affected_match_ids.map(Number) : [],
        suspension_affected_rounds: Array.isArray(source.suspension_affected_rounds) ? source.suspension_affected_rounds.map(Number) : [],
        notes: String(source.notes || '').trim(),
        updated_at: source.updated_at || new Date().toISOString(),
    };
    const cautionGroup = record.yellow_cards === 2 ? 'two_yellows' : (record.yellow_cards === 1 ? 'one_yellow' : null);
    if (cautionGroup) team[cautionGroup] = [...(team[cautionGroup] || []), record]
        .sort((a, b) => String(a.player_name || '').localeCompare(String(b.player_name || '')));
    const isSuspended = record.yellow_card_suspended || record.red_card_suspended || record.red_injury_suspended;
    if (isSuspended) team.suspended = [...(team.suspended || []), record]
        .sort((a, b) => String(a.player_name || '').localeCompare(String(b.player_name || '')));
    team.notes = [...new Set(['one_yellow', 'two_yellows', 'suspended']
        .flatMap(itemGroup => team[itemGroup] || [])
        .filter(item => String(item.notes || '').trim())
        .map(item => `${item.player_name}: ${item.notes}`))];
    if (!cautionGroup && !isSuspended && record.notes) team.notes.push(`${record.player_name}: ${record.notes}`);
}

function queueSuspensionRecordSave(teamId, immediate = false) {
    if (!canManageCurrentCompetitionSuspensions()) return;
    const numericTeamId = Number(teamId || 0);
    const draft = getSuspensionRecordDraft(numericTeamId);
    if (draft.error) {
        setSuspensionRecordSaveState(numericTeamId, '', draft.error);
        return;
    }
    const existingRecords = getLocalSuspensionRecordsForPlayer(draft.player, numericTeamId);
    const existing = existingRecords[0] || null;
    const existingYellowCards = existingRecords
        .reduce((total, record) => total + Number(record.yellow_cards || 0), 0);
    const isEmpty = Number(draft.payload.yellow_cards || 0) <= 0
        && !draft.payload.yellow_card_suspended
        && !draft.payload.red_card_suspended
        && !draft.payload.red_injury_suspended
        && !draft.payload.notes;
    if (isEmpty) {
        const mergeMode = draft.payload.merge_existing;
        setSuspensionRecordSaveState(
            numericTeamId,
            '',
            existing && mergeMode
                ? `已有${existing?.yellow_card_suspended ? '3黄停赛' : ''}${existingYellowCards ? `${existing?.yellow_card_suspended ? '，另有' : ''}${existingYellowCards}张黄牌` : ''}；填写本次新增数量后自动合并`
                : (existing ? '如需清除，请使用记录旁的清除按钮' : '填写伤停信息后自动保存'),
        );
        return;
    }
    suspensionRecordDrafts.set(numericTeamId, draft);
    if (suspensionRecordLastSavedSignatures.get(numericTeamId) === draft.signature) {
        setSuspensionRecordSaveState(numericTeamId, 'saved', '已自动保存');
        return;
    }
    const version = Number(suspensionRecordSaveVersions.get(numericTeamId) || 0) + 1;
    suspensionRecordSaveVersions.set(numericTeamId, version);
    const existingTimer = suspensionRecordSaveTimers.get(numericTeamId);
    if (existingTimer) window.clearTimeout(existingTimer);
    setSuspensionRecordSaveState(numericTeamId, 'saving', immediate ? '正在保存' : '等待保存');
    if (immediate) {
        suspensionRecordSaveTimers.delete(numericTeamId);
        saveSuspensionRecord(numericTeamId, version);
        return;
    }
    suspensionRecordSaveTimers.set(numericTeamId, window.setTimeout(() => {
        suspensionRecordSaveTimers.delete(numericTeamId);
        saveSuspensionRecord(numericTeamId, version);
    }, 650));
}

async function saveSuspensionPayload(payload, options = {}) {
    if (!canManageCurrentCompetitionSuspensions()) return {success: false};
    const result = await workJsonRequest('/api/admin/suspensions', {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });
    if (!result) return {success: false};
    const {response, data} = result;
    if (!response.ok || !data.success) {
        if (!options.silent) showModal('保存失败', escapeHtml(data.detail || data.message || '保存伤停记录失败'));
        return {success: false, message: data.detail || data.message || '保存失败'};
    }
    invalidateCompetitionSections(['suspensions']);
    refreshCompetitionWorkSummary().catch(error => console.error('Suspension saved but work summary refresh failed:', error));
    return {success: true, data};
}

async function saveSuspensionRecord(teamId, requestedVersion = null) {
    if (!canManageCurrentCompetitionSuspensions()) return;
    const numericTeamId = Number(teamId || 0);
    const latestVersion = Number(suspensionRecordSaveVersions.get(numericTeamId) || 0);
    const version = requestedVersion === null ? latestVersion : Number(requestedVersion);
    if (version !== latestVersion || suspensionRecordSaveInFlight.has(numericTeamId)) return;
    const draft = suspensionRecordDrafts.get(numericTeamId);
    if (!draft) return;
    suspensionRecordSaveInFlight.add(numericTeamId);
    setSuspensionRecordSaveState(numericTeamId, 'saving', '保存中');
    try {
        let result;
        try {
            result = await saveSuspensionPayload(draft.payload, {silent: true});
        } catch (error) {
            console.warn('Suspension record autosave interrupted; retrying once:', error);
            setSuspensionRecordSaveState(numericTeamId, 'saving', '网络波动，正在重试');
            await new Promise(resolve => window.setTimeout(resolve, 900));
            if (Number(suspensionRecordSaveVersions.get(numericTeamId) || 0) !== version) return;
            result = await saveSuspensionPayload(draft.payload, {silent: true});
        }
        if (!result?.success) {
            setSuspensionRecordSaveState(numericTeamId, 'error', result?.message || '保存失败');
            return;
        }
        const savedRecord = result.data?.record || null;
        applySuspensionRecordToLocalData(numericTeamId, draft.player, draft.payload, savedRecord);
        if (savedRecord) fillSuspensionEditor(numericTeamId, savedRecord.player_uid, savedRecord);
        else suspensionRecordLastSavedSignatures.set(numericTeamId, draft.signature);
        if (Number(suspensionRecordSaveVersions.get(numericTeamId) || 0) === version) {
            setSuspensionRecordSaveState(numericTeamId, 'saved', result.data?.merged ? result.data.message : '已自动保存');
        }
    } catch (error) {
        console.error('Failed to autosave suspension record:', error);
        setSuspensionRecordSaveState(numericTeamId, 'error', '网络异常，稍后修改将自动重试');
    } finally {
        suspensionRecordSaveInFlight.delete(numericTeamId);
        const nextVersion = Number(suspensionRecordSaveVersions.get(numericTeamId) || 0);
        if (nextVersion > version) {
            const pendingTimer = suspensionRecordSaveTimers.get(numericTeamId);
            if (pendingTimer) window.clearTimeout(pendingTimer);
            suspensionRecordSaveTimers.delete(numericTeamId);
            saveSuspensionRecord(numericTeamId, nextVersion);
        }
    }
}

function fillSuspensionEditor(teamId, playerUid, recordOverride = null) {
    const team = findSuspensionTeam(teamId);
    const records = [...(team?.one_yellow || []), ...(team?.two_yellows || []), ...(team?.suspended || [])];
    const record = recordOverride || records.find(item => Number(item.player_uid) === Number(playerUid));
    if (!team || !record) return;
    const playerInput = document.getElementById(`suspension-player-${teamId}`);
    const yellowInput = document.getElementById(`suspension-yellows-${teamId}`);
    const yellowSuspendedInput = document.getElementById(`suspension-yellow-suspended-${teamId}`);
    const redInput = document.getElementById(`suspension-red-${teamId}`);
    const injuryInput = document.getElementById(`suspension-injury-${teamId}`);
    const matchesInput = document.getElementById(`suspension-matches-${teamId}`);
    const notesInput = document.getElementById(`suspension-notes-${teamId}`);
    if (playerInput) {
        playerInput.value = record.player_name;
        playerInput.dataset.playerUid = String(Number(record.player_uid || 0));
    }
    if (yellowInput) yellowInput.value = String(Number(record.yellow_cards || 0));
    if (yellowSuspendedInput) yellowSuspendedInput.checked = Boolean(record.yellow_card_suspended);
    if (redInput) redInput.checked = Boolean(record.red_card_suspended);
    if (injuryInput) injuryInput.checked = Boolean(record.red_injury_suspended);
    if (matchesInput) matchesInput.value = String(Math.max(1, Number(record.suspension_matches || 1)));
    if (notesInput) notesInput.value = record.notes || '';
    suspensionRecordEntryModes.set(Number(teamId), 'replace');
    const payload = {
        player_uid: Number(record.player_uid),
        yellow_cards: Number(record.yellow_cards || 0),
        yellow_card_suspended: Boolean(record.yellow_card_suspended),
        red_card_suspended: Boolean(record.red_card_suspended),
        red_injury_suspended: Boolean(record.red_injury_suspended),
        suspension_matches: Math.max(1, Number(record.suspension_matches || 1)),
        notes: String(record.notes || '').trim(),
        merge_existing: false,
        merge_base_yellow_cards: null,
    };
    suspensionRecordLastSavedSignatures.set(Number(teamId), JSON.stringify(payload));
    setSuspensionRecordSaveState(teamId, 'saved', '已保存');
}

async function clearSuspensionRecord(playerUid) {
    if (!canManageCurrentCompetitionSuspensions()) return;
    const result = await saveSuspensionPayload({
        player_uid: Number(playerUid),
        yellow_cards: 0,
        yellow_card_suspended: false,
        red_card_suspended: false,
        red_injury_suspended: false,
        suspension_matches: 1,
        notes: '',
    });
    if (!result.success) return;
    removeSuspensionRecordFromLocalData(playerUid);
    renderSuspensionsBoard();
}

function getTeamOptionsHtml(selectedId, allowedIds = null) {
    const selected = Number(selectedId || 0);
    return '<option value="">待定</option>' + (teams || [])
        .filter(team => !allowedIds || allowedIds.has(Number(team.id)))
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
    const preliminaryMatch = (wumingjianQualificationData?.preliminary_matches || [])
        .find(match => Number(match.id) === Number(matchId));
    if (preliminaryMatch) return preliminaryMatch;
    for (const bracket of Object.values(cupBracketData || {})) {
        for (const stage of bracket?.stages || []) {
            const found = (stage.matches || []).find(match => Number(match.id) === Number(matchId));
            if (found) return found;
        }
    }
    return null;
}

function getWumingjianMatchTeamIds(match) {
    if (!match || match.competition !== 'wumingjian_cup' || !wumingjianQualificationData) return null;
    if (match.stage === 'qualifying_round') {
        return new Set((wumingjianQualificationData.preliminary_eligible_teams || []).map(team => Number(team.team_id)));
    }
    if (match.stage === 'round_of_32' && Number(wumingjianQualificationData.played_match_count || 0) === 22) {
        return new Set([
            ...(wumingjianQualificationData.direct_qualifiers || []),
            ...(wumingjianQualificationData.preliminary_winners || []),
        ].map(team => Number(team.team_id)));
    }
    return new Set();
}

function isTwoLegCupStage(match) {
    if (!match) return false;
    if (match.competition === 'champions_cup' || match.competition === 'league_cup') return true;
    return match.competition === 'wumingjian_cup' && ['semi_final', 'final'].includes(match.stage);
}

function showCupTieDecision(match, payload) {
    const homeName = getCupTeamDisplayName(match?.home_team_name || '上方球队');
    const awayName = getCupTeamDisplayName(match?.away_team_name || '下方球队');
    showModal('确认总比分相同的晋级结果', `
        <form class="cup-tie-decision" onsubmit="event.preventDefault(); confirmCupTieDecision(${Number(match.id)});">
            <p>${isTwoLegCupStage(match) ? '网站只记录两回合总比分；首回合主场由双方自行协商。请选择实际晋级球队和决胜方式。' : '请选择实际晋级球队和决胜方式。'}</p>
            <fieldset><legend>晋级球队</legend><label><input type="radio" name="cupTieWinner" value="${Number(match.home_team_id)}" checked>${escapeHtml(homeName)}</label><label><input type="radio" name="cupTieWinner" value="${Number(match.away_team_id)}">${escapeHtml(awayName)}</label></fieldset>
            <label><span>晋级原因</span><select id="cupTieReason"><option value="away_goals">客场进球</option><option value="extra_time">加时赛</option><option value="penalties">点球大战</option><option value="other">其他</option></select></label>
            <label><span>补充说明（可选）</span><input id="cupTieNote" type="text" maxlength="160" placeholder="例如：客场进球 2:1"></label>
            <div><button class="btn btn-secondary" type="button" onclick="closeModal()">取消</button><button class="btn btn-primary" type="submit">确认并保存</button></div>
        </form>`);
    const form = document.querySelector('.cup-tie-decision');
    if (form) form.dataset.payload = JSON.stringify(payload);
}

async function confirmCupTieDecision(matchId) {
    const form = document.querySelector('.cup-tie-decision');
    if (!form) return;
    const payload = JSON.parse(form.dataset.payload || '{}');
    payload.winner_team_id = Number(document.querySelector('input[name="cupTieWinner"]:checked')?.value || 0) || null;
    payload.advancement_reason = document.getElementById('cupTieReason')?.value || 'away_goals';
    payload.notes = document.getElementById('cupTieNote')?.value || null;
    closeModal();
    await submitCupMatchResult(matchId, payload);
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
    const showVenue = match.competition === 'wumingjian_cup' && match.stage === 'qualifying_round';
    const venueLabel = side === 'home' ? '主场' : '客场';
    return `
        <div class="cup-team-line ${stateClass} ${showVenue ? 'has-venue-label' : ''}">
            ${showVenue ? `<span class="cup-team-venue is-${side}">${venueLabel}</span>` : ''}
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
    const isWumingjianManualStage = match.competition === 'wumingjian_cup' && ['qualifying_round', 'round_of_32'].includes(match.stage);
    if (!canManageCurrentCompetitionSchedule() || (match.stage !== firstStage && !isWumingjianManualStage)) return '';
    if (match.stage === 'qualifying_round' && !wumingjianQualificationData?.league_rounds_complete) return '';
    const allowedIds = getWumingjianMatchTeamIds(match);
    if (match.stage === 'round_of_32' && allowedIds && !allowedIds.size) return '';
    const isQualifying = match.competition === 'wumingjian_cup' && match.stage === 'qualifying_round';
    const teamFields = isQualifying
        ? `
            <label class="cup-team-venue-field"><span>主场球队</span><select id="cup-home-team-${match.id}" aria-label="主场球队">${getTeamOptionsHtml(match.home_team_id, allowedIds)}</select></label>
            <label class="cup-team-venue-field"><span>客场球队</span><select id="cup-away-team-${match.id}" aria-label="客场球队">${getTeamOptionsHtml(match.away_team_id, allowedIds)}</select></label>
        `
        : `
            <select id="cup-home-team-${match.id}" aria-label="主队">${getTeamOptionsHtml(match.home_team_id, allowedIds)}</select>
            <select id="cup-away-team-${match.id}" aria-label="客队">${getTeamOptionsHtml(match.away_team_id, allowedIds)}</select>
        `;
    return `
        <div class="cup-editor cup-team-editor ${isQualifying ? 'is-venue-editor' : ''}">
            ${teamFields}
            <button class="btn btn-secondary" type="button" onclick="saveCupMatchTeams(${match.id})">保存球队</button>
        </div>
    `;
}

function buildCupResultEditor(match) {
    if (!canManageCurrentCompetitionSchedule()) return '';
    if (match.competition === 'wumingjian_cup' && match.stage === 'qualifying_round' && !wumingjianQualificationData?.league_rounds_complete) return '';
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

function renderWumingjianQualificationTeam(team) {
    return `
        <div class="wumingjian-qualification-team">
            <span class="wumingjian-qualification-rank">${Number(team.source_rank)}</span>
            <span class="wumingjian-qualification-team-copy"><strong>${escapeHtml(team.team_name)}</strong><small>${escapeHtml(team.manager || '暂无教练信息')}</small></span>
            <em>${escapeHtml(team.level)}第${Number(team.source_rank)}名</em>
        </div>
    `;
}

function renderWumingjianDirectGroup(level, teamsInLevel) {
    return `
        <section class="wumingjian-direct-group">
            <header><span>${escapeHtml(level)}</span><strong>${teamsInLevel.length} 席</strong></header>
            <div>${teamsInLevel.map(renderWumingjianQualificationTeam).join('')}</div>
        </section>
    `;
}

function renderWumingjianQualificationBoard() {
    const container = document.getElementById('cupGroupStageBoard');
    const qualification = wumingjianQualificationData;
    if (!container) return;
    if (!qualification) {
        container.innerHTML = renderUiState({tone: 'danger', title: '预选赛读取失败', message: '请刷新页面后重新读取。', actionLabel: '重新读取', actionOnclick: "loadCompetitionData({force:true})", compact: true});
        return;
    }
    const directByLevel = ['超级', '甲级', '乙级'].map(level => ({
        level,
        teams: (qualification.direct_qualifiers || []).filter(team => team.level === level),
    }));
    const matches = qualification.preliminary_matches || [];
    const ready = Boolean(qualification.league_rounds_complete);
    const locked = Boolean(qualification.qualification_locked);
    const editable = canManageCurrentCompetitionSchedule() && ready;
    container.innerHTML = `
        <section class="wumingjian-qualification-shell cup-group-stage-shell wumingjian-cup">
            <header class="wumingjian-qualification-hero surface-card">
                <div class="wumingjian-qualification-hero-copy">
                    <span>WUMINGJIAN CUP · QUALIFYING ROUND</span>
                    <h2>无铭剑杯预选赛</h2>
                    <p>联赛第15至16轮全部完赛后，超级前6名、甲级前2名、乙级前2名共10队直通32强；其余44队经抽签进行22场单场淘汰，主客场同样由抽签决定。</p>
                </div>
                <div class="wumingjian-qualification-state ${locked ? 'is-locked' : ready ? 'is-ready' : 'is-pending'}">
                    <small>${locked ? '资格状态' : '联赛进度'}</small>
                    <strong>${locked ? '名单已锁定' : ready ? '可以正式抽签' : '等待第15–16轮完赛'}</strong>
                    <span>${locked ? '后续积分变化不影响本届资格' : ready ? '首次保存对阵时锁定名单' : '当前名单仅按实时积分榜暂列'}</span>
                </div>
            </header>
            <div class="wumingjian-format-strip" aria-label="预选赛赛制流程">
                <span><small>直通名额</small><strong>10</strong><em>超级6 · 甲级2 · 乙级2</em></span>
                <i aria-hidden="true"></i>
                <span><small>预选球队</small><strong>44</strong><em>抽签决定对手与主客场</em></span>
                <i aria-hidden="true"></i>
                <span><small>单场淘汰</small><strong>22</strong><em>胜者进入32强</em></span>
                <i aria-hidden="true"></i>
                <span><small>32强阵容</small><strong>${Number(qualification.round_of_32_pool_count || 0)}/32</strong><em>10支直通 + 22支胜者</em></span>
            </div>
            <section class="wumingjian-direct-board surface-card">
                <header class="wumingjian-section-head"><div><span>DIRECT QUALIFIERS</span><h3>直通32强</h3></div><em>${locked ? '正式名单' : '当前暂列'} · ${qualification.direct_qualifiers?.length || 0}/10</em></header>
                <div class="wumingjian-direct-grid">${directByLevel.map(group => renderWumingjianDirectGroup(group.level, group.teams)).join('')}</div>
            </section>
            <section class="wumingjian-preliminary-board">
                <header class="wumingjian-section-head surface-card">
                    <div><span>22 SINGLE-LEG TIES</span><h3>预选赛对阵</h3><p>每组为一场定胜负；平局时由工作人员选择最终晋级球队。</p></div>
                    <div class="wumingjian-progress-pills"><span>已抽签 <strong>${Number(qualification.assigned_match_count || 0)}/22</strong></span><span>已完赛 <strong>${Number(qualification.played_match_count || 0)}/22</strong></span></div>
                </header>
                ${canManageCurrentCompetitionSchedule() && !ready ? '<div class="cup-group-edit-note surface-card">当前仅供查看暂定资格。第15至16轮全部完赛后，球队选择与保存控件会自动开放。</div>' : ''}
                ${editable ? '<div class="cup-group-edit-note surface-card">按抽签结果逐场选择主队和客队；第一次保存会锁定本届资格名单，同一球队不能重复参赛。</div>' : ''}
                <div class="wumingjian-preliminary-grid">${matches.map(renderCupMatchCard).join('')}</div>
            </section>
        </section>
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
    const roundPairs = buildRoundPairs(rounds);
    const selectedPairStart = getRoundPairStart(selectedRound);
    roundSelect.innerHTML = roundPairs
        .map(pair => `<option value="${pair.pairStart}">${escapeHtml(formatRoundPairLabel(pair.rounds))}</option>`)
        .join('');
    roundSelect.value = roundPairs.some(pair => pair.pairStart === selectedPairStart)
        ? String(selectedPairStart)
        : String(roundPairs[0]?.pairStart || '');
}

function getFilteredScheduleMatches() {
    if (isCupCompetitionLevel()) return [];
    const selectedRound = Number(document.getElementById('scheduleRoundSelect')?.value || 0);
    const selectedPairStart = getRoundPairStart(selectedRound);
    const visibleMatchIds = getCompetitionWorkVisibleMatchIds();
    return (scheduleData.matches || []).filter(match => {
        if (match.level !== currentCompetitionLevel) return false;
        if (selectedPairStart && getRoundPairStart(match.round_no) !== selectedPairStart) return false;
        if (visibleMatchIds && !visibleMatchIds.has(Number(match.id))) return false;
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
    const pairs = buildRoundPairs(rounds);
    const currentPairStart = getRoundPairStart(getCurrentScheduleRound());
    const currentIndex = Math.max(0, pairs.findIndex(pair => pair.pairStart === currentPairStart));
    const nextIndex = Math.max(0, Math.min(pairs.length - 1, currentIndex + Number(direction || 0)));
    const roundSelect = document.getElementById('scheduleRoundSelect');
    if (roundSelect) roundSelect.value = String(pairs[nextIndex]?.pairStart || '');
    renderScheduleBoard();
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
}

function setScheduleRound(roundNo) {
    const targetRound = Number(roundNo || 0);
    const rounds = getScheduleRoundsForCurrentLevel();
    if (!rounds.includes(targetRound)) return;
    const roundSelect = document.getElementById('scheduleRoundSelect');
    if (roundSelect) roundSelect.value = String(targetRound);
    renderScheduleBoard();
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
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
    const acceptedTypes = type === 'goal' ? new Set(['goal', 'own_goal']) : new Set([type]);
    const events = (match.events || []).filter(event => acceptedTypes.has(event.event_type) && scheduleEventBelongsToSide(match, event, side));
    if (!events.length) return '';
    const icon = type === 'assist' ? '👟' : '⚽';
    const label = type === 'assist' ? '助攻' : '进球';
    const groupedEvents = [];
    for (const event of events) {
        const playerUid = Number(event.player_uid || 0);
        const eventKey = event.event_type === 'own_goal' ? 'own_goal' : 'player';
        const existing = groupedEvents.find(item => (
            String(item.event_type || '') === eventKey && playerUid && Number(item.player_uid || 0) === playerUid
        ) || (
            String(item.event_type || '') === eventKey && !playerUid && String(item.player_name || '') === String(event.player_name || '')
        ));
        if (existing) {
            existing.quantity = Number(existing.quantity || 0) + Number(event.quantity || 1);
        } else {
            groupedEvents.push({...event, event_type: eventKey, quantity: Number(event.quantity || 1)});
        }
    }
    return `
        <div class="schedule-event-line">
            <span class="schedule-event-icon" aria-hidden="true">${icon}</span>
            <span>${label}</span>
            <span class="schedule-event-players">
                ${groupedEvents.map(event => event.event_type === 'own_goal' ? `
                    <span class="schedule-event-player schedule-event-own-goal">乌龙球${Number(event.quantity || 1) > 1 ? `（${Number(event.quantity)}）` : ''}</span>
                ` : `
                    <button class="schedule-event-player" type="button" onclick="openCompetitionPlayerAttributeDetail(${Number(event.player_uid || 0)}, 'schedule')">
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
                    <button class="schedule-event-player" type="button" onclick="openCompetitionPlayerAttributeDetail(${Number(event.player_uid || 0)}, 'schedule')">
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

function getScheduleMatchEventSummary(match) {
    const events = Array.isArray(match?.events) ? match.events : [];
    const goals = events
        .filter(event => ['goal', 'own_goal'].includes(event.event_type))
        .reduce((total, event) => total + Number(event.quantity || 0), 0);
    const assists = events
        .filter(event => event.event_type === 'assist')
        .reduce((total, event) => total + Number(event.quantity || 0), 0);
    const mvp = events.find(event => event.event_type === 'mvp');
    return {goals, assists, mvpName: String(mvp?.player_name || '')};
}

function renderScheduleMatchEventSummary(match) {
    const summary = getScheduleMatchEventSummary(match);
    const actionLabel = canManageCurrentCompetitionSchedule() ? '编辑比赛数据' : '查看明细';
    return `
        <button class="schedule-event-summary-bar" type="button" onclick="openMatchEventEditor(${Number(match.id)})" aria-label="${escapeHtml(actionLabel)}：${escapeHtml(match.home_team_name || '-')} 对 ${escapeHtml(match.away_team_name || '-')}">
            <span class="schedule-event-summary-stat"><em>进球</em><strong>${summary.goals}</strong></span>
            <span class="schedule-event-summary-stat"><em>助攻</em><strong>${summary.assists}</strong></span>
            <span class="schedule-event-summary-mvp ${summary.mvpName ? 'is-ready' : ''}"><em>最佳</em><strong>${escapeHtml(summary.mvpName || '待评选')}</strong></span>
            <span class="schedule-event-summary-action">${escapeHtml(actionLabel)}<span aria-hidden="true">›</span></span>
        </button>
    `;
}

function renderScheduleRoundNavigator(rounds, currentRound, matches) {
    const roundPairs = buildRoundPairs(rounds);
    const currentPairStart = getRoundPairStart(currentRound);
    const currentPair = roundPairs.find(pair => pair.pairStart === currentPairStart) || roundPairs[0] || {rounds: []};
    const currentIndex = roundPairs.findIndex(pair => pair.pairStart === (currentPair.pairStart || currentPairStart));
    const playedCount = matches.filter(isScheduleMatchPlayed).length;
    const isRoundComplete = Boolean(matches.length && playedCount === matches.length);
    return `
        <div class="schedule-round-nav">
            <button class="schedule-round-arrow" type="button" onclick="stepScheduleRound(-1)" ${currentIndex <= 0 ? 'disabled' : ''} aria-label="上一轮">‹</button>
            <div class="schedule-round-chip ${isRoundComplete ? 'is-complete' : ''}">
                <span>${escapeHtml(formatRoundPairLabel(currentPair.rounds))}</span>
                <span class="schedule-round-check" aria-hidden="true">${uiIconSvg('check', 'ui-icon is-small')}</span>
                <select class="schedule-round-direct-select" aria-label="选择赛程轮次" onchange="setScheduleRound(this.value)">
                    ${roundPairs.map(pair => `<option value="${Number(pair.pairStart)}" ${Number(pair.pairStart) === Number(currentPair.pairStart) ? 'selected' : ''}>${escapeHtml(formatRoundPairLabel(pair.rounds))}</option>`).join('')}
                </select>
            </div>
            <button class="schedule-round-arrow" type="button" onclick="stepScheduleRound(1)" ${currentIndex >= roundPairs.length - 1 ? 'disabled' : ''} aria-label="下一轮">›</button>
        </div>
    `;
}

function renderScheduleMatchRow(match, options = {}) {
    const played = isScheduleMatchPlayed(match);
    const score = getScheduleMatchScoreText(match);
    const includeAdmin = options.includeAdmin !== false;
    const statusToneClass = getScheduleStatusTone(match.status);
    return `
        <article class="schedule-match-row ${played ? 'is-played' : 'is-pending'} ${getCompetitionWorkMatchClass(match.id)}" data-match-id="${Number(match.id) || 0}">
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
                ${renderCompetitionWorkMatchIssue(match.id)}
                ${canManageCurrentCompetitionSchedule() && includeAdmin ? renderScheduleMatchEventSummary(match) : ''}
            </div>
            ${renderScheduleTeamSide(match, 'away')}
        </article>
    `;
}

function renderScheduleCompactTeam(match, side) {
    const isHome = side === 'home';
    const teamId = isHome ? match.home_team_id : match.away_team_id;
    const teamName = isHome ? match.home_team_name : match.away_team_name;
    const team = getScheduleTeamMeta(teamId, teamName);
    const crest = team.logo_path
        ? `<img src="${escapeHtml(team.logo_path)}" alt="${escapeHtml(teamName || '-')}队徽">`
        : `<span>${escapeHtml(getScheduleTeamInitials(teamName))}</span>`;
    return `
        <div class="schedule-compact-team schedule-compact-team-${isHome ? 'home' : 'away'}">
            ${isHome ? `<div class="schedule-compact-crest ${team.logo_path ? 'has-logo' : ''}">${crest}</div>` : ''}
            <button class="schedule-compact-team-name" type="button" onclick="viewTeamPlayers(${htmlJsString(team.name || teamName || '')})" title="${escapeHtml(team.name || teamName || '-')}">${escapeHtml(teamName || '-')}</button>
            ${!isHome ? `<div class="schedule-compact-crest ${team.logo_path ? 'has-logo' : ''}">${crest}</div>` : ''}
        </div>
    `;
}

function renderScheduleCompactMatchRow(match, options = {}) {
    const played = isScheduleMatchPlayed(match);
    const score = getScheduleMatchScoreText(match);
    const includeAdmin = options.includeAdmin !== false;
    const statusToneClass = getScheduleStatusTone(match.status);
    return `
        <article class="schedule-match-row schedule-match-row-compact ${played ? 'is-played' : 'is-pending'} ${getCompetitionWorkMatchClass(match.id)}" data-match-id="${Number(match.id) || 0}">
            <div class="schedule-compact-matchup">
                ${renderScheduleCompactTeam(match, 'home')}
                <div class="schedule-compact-score-block">
                    <div class="schedule-score-status ${statusToneClass}">
                        <span class="schedule-status-check" aria-hidden="true">${played ? '✓' : '•'}</span>
                        <span>${escapeHtml(getMatchStatusLabel(match.status))}</span>
                    </div>
                    <strong class="schedule-score">${escapeHtml(score)}</strong>
                </div>
                ${renderScheduleCompactTeam(match, 'away')}
            </div>
            ${renderScheduleMatchEventSummary(match)}
            ${renderCompetitionWorkMatchIssue(match.id)}
        </article>
    `;
}

function sortScheduleMatches(matches) {
    return [...(matches || [])].sort((a, b) => {
        const roundDiff = Number(a.round_no || 0) - Number(b.round_no || 0);
        if (roundDiff) return roundDiff;
        return Number(a.id || 0) - Number(b.id || 0);
    });
}

function renderScheduleRoundColumn(roundNo, matches, options = {}) {
    const roundMatches = sortScheduleMatches((matches || []).filter(match => Number(match.round_no) === Number(roundNo)));
    const playedCount = roundMatches.filter(isScheduleMatchPlayed).length;
    const includeAdmin = options.includeAdmin !== false;
    return `
        <section class="schedule-round-column">
            <header class="schedule-round-column-head">
                <h3>第 ${Number(roundNo) || '-'} 轮</h3>
                <span>${playedCount}/${roundMatches.length} 已赛</span>
            </header>
            <div class="schedule-fixture-list schedule-round-column-list">
                ${roundMatches.length
                    ? roundMatches.map(match => renderScheduleCompactMatchRow(match, {includeAdmin})).join('')
                    : '<div class="schedule-round-empty">本轮暂无对阵</div>'}
            </div>
        </section>
    `;
}

function renderScheduleRoundPairGrid(rounds, matches, options = {}) {
    return `
        <div class="schedule-round-pair-grid schedule-desktop-fixture-list">
            ${rounds.map(roundNo => renderScheduleRoundColumn(roundNo, matches, options)).join('')}
        </div>
    `;
}

function findScheduleMatchById(matchId) {
    return (scheduleData.matches || []).find(match => Number(match.id) === Number(matchId)) || null;
}

function invalidateCompetitionPlayerCaches() {
    matchTeamPlayerCache.clear();
    activeMatchEventSuggestionContext = null;
    activeSuspensionSuggestionContext = null;
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
    const selectedType = isMvp ? 'mvp' : (['goal', 'own_goal', 'assist'].includes(event.event_type) ? event.event_type : 'goal');
    const isOwnGoal = selectedType === 'own_goal';
    const quantity = Math.max(1, Number(event.quantity || 1));
    const selectedPlayerName = isOwnGoal ? '' : (event.player_name || '');
    return `
        <div class="match-event-row ${isMvp ? 'match-mvp-row' : ''} ${isOwnGoal ? 'is-own-goal' : ''}" data-match-event-row data-event-type="${escapeHtml(selectedType)}">
            <select class="match-event-team" onchange="refreshMatchEventPlayerInput(this, ${Number(match.id)})" aria-label="事件球队">
                ${teams.map(team => `<option value="${escapeHtml(team.team_name)}" data-team-id="${Number(team.team_id || 0)}" data-match-team-name="${escapeHtml(team.match_team_name)}" ${team.team_name === selectedTeam ? 'selected' : ''}>${escapeHtml(team.match_team_name || team.team_name)}</option>`).join('')}
            </select>
            <div class="match-event-player-field">
                <div class="match-event-player-input-row">
                    <input class="match-event-player" type="text" value="${escapeHtml(selectedPlayerName)}" placeholder="${isOwnGoal ? '无需选择球员' : (isMvp ? '输入或选择本场最佳' : '输入或选择球员')}" aria-label="${isMvp ? '本场最佳球员' : '事件球员'}" autocomplete="off" ${isOwnGoal ? 'disabled' : ''} oninput="updateMatchEventSuggestions(this, ${Number(match.id)})" onchange="scheduleMatchAutoSave(${Number(match.id)})" onfocus="updateMatchEventSuggestions(this, ${Number(match.id)}, true)" onblur="scheduleCloseMatchEventSuggestions(this)" onkeydown="handleMatchEventPlayerKeydown(event, this)">
                    <button class="match-event-player-select" type="button" title="选择球员" aria-label="选择球员" ${isOwnGoal ? 'disabled' : ''} onclick="toggleMatchEventSuggestions(this, ${Number(match.id)})">▾</button>
                </div>
                <span class="match-event-own-goal-note">计入所选球队比分，无需选择具体球员</span>
            </div>
            ${isMvp ? `
                <input class="match-event-type" type="hidden" value="mvp">
                <input class="match-event-quantity" type="hidden" value="1">
                <button class="match-event-remove match-mvp-clear" type="button" onclick="clearMatchEventRow(this)" aria-label="清空本场最佳">清空</button>
            ` : `
                <select class="match-event-type" aria-label="事件类型" onchange="handleMatchEventTypeChange(this, ${Number(match.id)})">
                    <option value="goal" ${selectedType === 'goal' ? 'selected' : ''}>进球</option>
                    <option value="own_goal" ${selectedType === 'own_goal' ? 'selected' : ''}>乌龙球</option>
                    <option value="assist" ${selectedType === 'assist' ? 'selected' : ''}>助攻</option>
                </select>
                <input class="match-event-quantity" type="number" min="1" value="${quantity}" aria-label="事件数量" oninput="scheduleMatchAutoSave(${Number(match.id)})" onchange="scheduleMatchAutoSave(${Number(match.id)})">
                <button class="match-event-remove" type="button" onclick="removeMatchEventRow(this)" aria-label="删除明细">${uiIconSvg('close', 'ui-icon is-small')}</button>
            `}
        </div>
    `;
}

function getMatchEventPositionSortRank(position) {
    const compact = String(position || '').toUpperCase().replace(/[^A-Z]/g, '');
    const roles = [...compact.matchAll(/(GK|ST|AM|DM|WB|D|M|S)([RLC]*)/g)]
        .map(match => ({role: match[1], sides: match[2] || ''}));
    if (roles.some(item => item.role === 'ST' || item.role === 'S')) return 0;
    if (roles.some(item => ['AM', 'M'].includes(item.role) && /[RL]/.test(item.sides))) return 1;
    if (roles.some(item => item.role === 'AM' || item.role === 'M')) return 2;
    if (roles.some(item => item.role === 'DM')) return 3;
    if (roles.some(item => item.role === 'D' || item.role === 'WB')) return 4;
    if (roles.some(item => item.role === 'GK')) return 5;
    return 6;
}

function getMatchEventEditorPlayers(match, team) {
    const rosterPlayers = getMatchTeamPlayers(match, team.team_name).map(player => ({
        uid: Number(player.uid || 0),
        name: String(player.name || ''),
        position: String(player.position || ''),
        isRosterPlayer: true,
    }));
    const playersByKey = new Map(rosterPlayers.map(player => [player.uid ? `uid:${player.uid}` : `name:${player.name.toLowerCase()}`, player]));
    (match.events || [])
        .filter(event => event.event_type !== 'own_goal' && matchTeamOptionMatchesEvent(team, event))
        .forEach(event => {
            const uid = Number(event.player_uid || 0);
            const name = String(event.player_name || '').trim();
            if (!uid && !name) return;
            const key = uid ? `uid:${uid}` : `name:${name.toLowerCase()}`;
            if (!playersByKey.has(key)) {
                playersByKey.set(key, {uid, name, position: '', isRosterPlayer: false});
            }
        });
    return [...playersByKey.values()].sort((a, b) => (
        getMatchEventPositionSortRank(a.position) - getMatchEventPositionSortRank(b.position)
        || String(a.name || '').localeCompare(String(b.name || ''), 'en', {sensitivity: 'base', numeric: true})
    ));
}

function getMatchEventPlayerQuantity(match, team, player, eventType) {
    return (match.events || [])
        .filter(event => event.event_type === eventType && matchTeamOptionMatchesEvent(team, event))
        .filter(event => player.uid
            ? Number(event.player_uid || 0) === Number(player.uid)
            : String(event.player_name || '').trim() === String(player.name || '').trim())
        .reduce((total, event) => total + Number(event.quantity || 0), 0);
}

function isMatchEventMvp(match, team, player) {
    return (match.events || []).some(event => event.event_type === 'mvp'
        && matchTeamOptionMatchesEvent(team, event)
        && (player.uid
            ? Number(event.player_uid || 0) === Number(player.uid)
            : String(event.player_name || '').trim() === String(player.name || '').trim()));
}

function getMatchOwnGoalQuantity(match, team) {
    return (match.events || [])
        .filter(event => event.event_type === 'own_goal' && matchTeamOptionMatchesEvent(team, event))
        .reduce((total, event) => total + Number(event.quantity || 0), 0);
}

function renderMatchEventMatrixPlayer(match, team, player) {
    const goals = getMatchEventPlayerQuantity(match, team, player, 'goal');
    const assists = getMatchEventPlayerQuantity(match, team, player, 'assist');
    const isMvp = isMatchEventMvp(match, team, player);
    return `
        <div class="match-event-matrix-row ${player.isRosterPlayer ? '' : 'is-unmatched'}" data-match-event-matrix-row data-team-name="${escapeHtml(team.team_name)}" data-player-uid="${Number(player.uid || 0)}" data-player-name="${escapeHtml(player.name)}">
            <span class="match-event-matrix-player">
                <strong>${escapeHtml(player.name || '-')}</strong>
                <small>${escapeHtml(player.position || (player.isRosterPlayer ? '' : '历史事件球员'))}</small>
            </span>
            <label class="match-event-matrix-number">
                <span class="sr-only">${escapeHtml(player.name)}进球数</span>
                <input type="number" min="0" step="1" inputmode="numeric" value="${goals || ''}" placeholder="0" data-event-count="goal" oninput="markMatchEventEditorDirty()">
            </label>
            <label class="match-event-matrix-number">
                <span class="sr-only">${escapeHtml(player.name)}助攻数</span>
                <input type="number" min="0" step="1" inputmode="numeric" value="${assists || ''}" placeholder="0" data-event-count="assist" oninput="markMatchEventEditorDirty()">
            </label>
            <label class="match-event-matrix-mvp" title="本场最佳">
                <input type="checkbox" ${isMvp ? 'checked' : ''} data-match-event-mvp onchange="selectMatchEventMvp(this)">
                <span aria-hidden="true">★</span>
                <span class="sr-only">选择${escapeHtml(player.name)}为本场最佳</span>
            </label>
        </div>
    `;
}

function renderMatchEventMatrixTeam(match, team, side) {
    const players = getMatchEventEditorPlayers(match, team);
    const ownGoals = getMatchOwnGoalQuantity(match, team);
    return `
        <section class="match-event-matrix-team" data-match-event-team-panel="${side}" ${side === 'home' ? '' : 'hidden'}>
            <div class="match-event-matrix-columns" aria-hidden="true">
                <span>球员 · 按位置</span><span>进球</span><span>助攻</span><span>最佳</span>
            </div>
            <div class="match-event-matrix-list">
                ${players.length ? players.map(player => renderMatchEventMatrixPlayer(match, team, player)).join('') : '<div class="match-event-matrix-empty">当前球队没有可用球员名单</div>'}
            </div>
            <label class="match-event-own-goal-field">
                <span><strong>乌龙球</strong><small>计入当前球队比分，不关联具体球员</small></span>
                <input type="number" min="0" step="1" inputmode="numeric" value="${ownGoals || ''}" placeholder="0" data-match-own-goals data-team-name="${escapeHtml(team.team_name)}" oninput="markMatchEventEditorDirty()">
            </label>
        </section>
    `;
}

function renderMatchEventScoreEditor(match) {
    const hasScore = match.home_score !== null && match.home_score !== undefined
        && match.away_score !== null && match.away_score !== undefined;
    const status = isScheduleForfeitStatus(match.status)
        ? match.status
        : (hasScore ? 'played' : 'scheduled');
    const scoreReadonly = isScheduleForfeitStatus(status) ? 'readonly' : '';
    return `
        <section class="match-event-score-editor ${status === 'scheduled' ? 'is-scheduled' : ''} ${isScheduleForfeitStatus(status) ? 'is-forfeit' : ''}" aria-labelledby="matchEventScoreEditorTitle">
            <h4 id="matchEventScoreEditorTitle" class="sr-only">比分与比赛判定</h4>
            <div class="match-event-score-team is-home">
                <span>主队</span>
                <strong>${escapeHtml(match.home_team_name || '-')}</strong>
            </div>
            <label class="match-event-score-input">
                <span class="sr-only">主队比分</span>
                <input type="number" min="0" step="1" inputmode="numeric" id="match-home-${Number(match.id)}" value="${escapeHtml(match.home_score ?? '')}" ${scoreReadonly} data-match-score-side="home" aria-label="主队比分" oninput="handleMatchScoreEditorInput(${Number(match.id)})">
            </label>
            <span class="match-event-score-separator" aria-hidden="true">—</span>
            <label class="match-event-score-input">
                <span class="sr-only">客队比分</span>
                <input type="number" min="0" step="1" inputmode="numeric" id="match-away-${Number(match.id)}" value="${escapeHtml(match.away_score ?? '')}" ${scoreReadonly} data-match-score-side="away" aria-label="客队比分" oninput="handleMatchScoreEditorInput(${Number(match.id)})">
            </label>
            <div class="match-event-score-team is-away">
                <span>客队</span>
                <strong>${escapeHtml(match.away_team_name || '-')}</strong>
            </div>
            <label class="match-event-status-field">
                <span>比赛判定</span>
                <select class="match-status-select" id="match-status-${Number(match.id)}" onchange="handleMatchStatusChange(${Number(match.id)})">
                    <option value="scheduled" ${status === 'scheduled' ? 'selected' : ''}>未赛</option>
                    <option value="played" ${status === 'played' ? 'selected' : ''}>正常比赛</option>
                    <option value="home_forfeit" ${status === 'home_forfeit' ? 'selected' : ''}>主队判负</option>
                    <option value="away_forfeit" ${status === 'away_forfeit' ? 'selected' : ''}>客队判负</option>
                    <option value="double_forfeit" ${status === 'double_forfeit' ? 'selected' : ''}>双方判负</option>
                </select>
            </label>
            <p class="match-event-score-note" id="matchEventScoreNote">${status === 'scheduled'
                ? '直接填写比分会自动切换为正常比赛；主动改回未赛会清空本场数据。'
                : (isScheduleForfeitStatus(status)
                    ? getForfeitRuleNote(status)
                    : '比分、比赛判定和球员数据会一次提交。')}</p>
        </section>
    `;
}

function renderMatchEventEditorDialog(match) {
    const teams = getMatchTeamOptions(match);
    const summary = getScheduleMatchEventSummary(match);
    return `
        <div class="match-event-modal-overlay" id="matchEventEditorModal" data-match-id="${Number(match.id)}" data-home-score="${match.home_score ?? ''}" data-away-score="${match.away_score ?? ''}" role="presentation" onclick="if (event.target === this) closeMatchEventEditor()">
            <section class="match-event-modal" role="dialog" aria-modal="true" aria-labelledby="matchEventModalTitle" tabindex="-1">
                <header class="match-event-modal-head">
                    <div>
                        <span>比赛数据上报</span>
                        <h3 id="matchEventModalTitle">${escapeHtml(match.home_team_name || '-')} <em data-match-score-display>${escapeHtml(getScheduleMatchScoreText(match))}</em> ${escapeHtml(match.away_team_name || '-')}</h3>
                    </div>
                    <button type="button" class="match-event-modal-close" onclick="closeMatchEventEditor()" aria-label="关闭比赛数据窗口">${uiIconSvg('close')}</button>
                </header>
                ${renderMatchEventScoreEditor(match)}
                <div class="match-event-modal-summary">
                    <span><small>进球</small><strong data-match-event-summary-goals>${summary.goals}</strong></span>
                    <span><small>助攻</small><strong data-match-event-summary-assists>${summary.assists}</strong></span>
                    <span><small>本场最佳</small><strong data-match-event-summary-mvp>${escapeHtml(summary.mvpName || '待评选')}</strong></span>
                </div>
                <div class="match-event-team-tabs" role="tablist" aria-label="切换球队">
                    ${teams.map((team, index) => {
                        const side = index === 0 ? 'home' : 'away';
                        const teamEvents = (match.events || []).filter(event => matchTeamOptionMatchesEvent(team, event));
                        const teamGoals = teamEvents.filter(event => ['goal', 'own_goal'].includes(event.event_type)).reduce((total, event) => total + Number(event.quantity || 0), 0);
                        return `<button type="button" class="match-event-team-tab ${index === 0 ? 'active' : ''}" data-match-event-team-tab="${side}" role="tab" aria-selected="${index === 0 ? 'true' : 'false'}" onclick="switchMatchEventEditorTeam('${side}')"><span>${index === 0 ? '主队' : '客队'}</span><strong>${escapeHtml(team.match_team_name || team.team_name)}</strong><em data-match-event-team-total="${side}">${teamGoals} 球</em></button>`;
                    }).join('')}
                </div>
                <div class="match-event-modal-body">
                    ${teams.map((team, index) => renderMatchEventMatrixTeam(match, team, index === 0 ? 'home' : 'away')).join('')}
                </div>
                <footer class="match-event-modal-footer">
                    <span class="match-event-modal-status" id="matchEventModalStatus" role="status" aria-live="polite">填写数字后统一保存</span>
                    <div>
                        <button type="button" class="btn btn-secondary" onclick="closeMatchEventEditor()">取消</button>
                        <button type="button" class="btn btn-secondary" id="matchEventModalSaveNext" onclick="saveMatchEventEditor(true)">保存并下一场</button>
                        <button type="button" class="btn btn-primary" id="matchEventModalSave" onclick="saveMatchEventEditor(false)">保存比赛数据</button>
                    </div>
                </footer>
            </section>
        </div>
    `;
}

function renderMatchEventViewerDialog(match) {
    return `
        <div class="match-event-modal-overlay" id="matchEventEditorModal" data-match-id="${Number(match.id)}" role="presentation" onclick="if (event.target === this) closeMatchEventEditor(true)">
            <section class="match-event-modal match-event-viewer-modal" role="dialog" aria-modal="true" aria-labelledby="matchEventModalTitle" tabindex="-1">
                <header class="match-event-modal-head">
                    <div><span>比赛明细</span><h3 id="matchEventModalTitle">${escapeHtml(match.home_team_name || '-')} <em>${escapeHtml(getScheduleMatchScoreText(match))}</em> ${escapeHtml(match.away_team_name || '-')}</h3></div>
                    <button type="button" class="match-event-modal-close" onclick="closeMatchEventEditor(true)" aria-label="关闭比赛明细">${uiIconSvg('close')}</button>
                </header>
                <div class="match-event-viewer-body">${renderScheduleMatchEvents(match)}</div>
                <footer class="match-event-modal-footer"><span></span><div><button type="button" class="btn btn-primary" onclick="closeMatchEventEditor(true)">关闭</button></div></footer>
            </section>
        </div>
    `;
}

function getMatchEventDraftStorageKey(matchId) {
    return `${MATCH_EVENT_DRAFT_STORAGE_PREFIX}${Number(matchId || 0)}`;
}

function readStoredMatchEventDraft(matchId) {
    try {
        const raw = localStorage.getItem(getMatchEventDraftStorageKey(matchId));
        if (!raw) return null;
        const draft = JSON.parse(raw);
        if (!draft || Number(draft.matchId || 0) !== Number(matchId)) return null;
        if (Date.now() - Number(draft.updatedAt || 0) > MATCH_EVENT_DRAFT_MAX_AGE_MS) {
            localStorage.removeItem(getMatchEventDraftStorageKey(matchId));
            return null;
        }
        return draft;
    } catch (error) {
        return null;
    }
}

function clearStoredMatchEventDraft(matchId) {
    window.clearTimeout(matchEventDraftSaveTimer);
    matchEventDraftSaveTimer = null;
    try {
        localStorage.removeItem(getMatchEventDraftStorageKey(matchId));
    } catch (error) {
        // Restricted browsers may disable local storage; the editor still works normally.
    }
}

function normalizeMatchEventsForDraft(events) {
    return (events || []).map(event => ({
        team_name: String(event.team_name || ''),
        player_uid: event.player_uid === null || event.player_uid === undefined ? null : Number(event.player_uid || 0),
        player_name: String(event.player_name || ''),
        event_type: String(event.event_type || ''),
        quantity: Number(event.quantity || 0),
    })).sort((left, right) => JSON.stringify(left).localeCompare(JSON.stringify(right)));
}

function persistMatchEventDraftNow() {
    const matchId = Number(activeMatchEventEditorMatchId || 0);
    if (!matchId || !document.getElementById('matchEventEditorModal') || !matchEventEditorDirty) return;
    try {
        const events = readMatchEventMatrixPayload(matchId);
        const homeRaw = String(document.getElementById(`match-home-${matchId}`)?.value || '').trim();
        const awayRaw = String(document.getElementById(`match-away-${matchId}`)?.value || '').trim();
        const match = findScheduleMatchById(matchId);
        localStorage.setItem(getMatchEventDraftStorageKey(matchId), JSON.stringify({
            matchId,
            updatedAt: Date.now(),
            homeScore: homeRaw === '' ? null : Number(homeRaw),
            awayScore: awayRaw === '' ? null : Number(awayRaw),
            status: String(document.getElementById(`match-status-${matchId}`)?.value || match?.status || 'scheduled'),
            events: normalizeMatchEventsForDraft(events),
        }));
        const status = document.getElementById('matchEventModalStatus');
        if (status && !status.classList.contains('is-warning')) status.textContent = '草稿已保存在本机';
    } catch (error) {
        // Invalid in-progress values stay in the open form and will be validated on save.
    }
}

function scheduleMatchEventDraftSave() {
    window.clearTimeout(matchEventDraftSaveTimer);
    matchEventDraftSaveTimer = window.setTimeout(() => {
        matchEventDraftSaveTimer = null;
        persistMatchEventDraftNow();
    }, 350);
}

function restoreStoredMatchEventDraft(match) {
    const draft = readStoredMatchEventDraft(match.id);
    if (!draft) return false;
    const serverEvents = normalizeMatchEventsForDraft(match.events || []);
    const draftHasScoreState = Object.prototype.hasOwnProperty.call(draft, 'homeScore')
        || Object.prototype.hasOwnProperty.call(draft, 'awayScore')
        || Object.prototype.hasOwnProperty.call(draft, 'status');
    const serverStatus = isScheduleForfeitStatus(match.status)
        ? String(match.status)
        : (match.home_score === null || match.home_score === undefined ? 'scheduled' : 'played');
    const scoreStateMatches = !draftHasScoreState || (
        (draft.homeScore ?? null) === (match.home_score ?? null)
        && (draft.awayScore ?? null) === (match.away_score ?? null)
        && String(draft.status || serverStatus) === serverStatus
    );
    if (scoreStateMatches && JSON.stringify(serverEvents) === JSON.stringify(draft.events || [])) {
        clearStoredMatchEventDraft(match.id);
        return false;
    }
    const modal = document.getElementById('matchEventEditorModal');
    if (!modal) return false;
    if (draftHasScoreState) {
        const homeInput = document.getElementById(`match-home-${Number(match.id)}`);
        const awayInput = document.getElementById(`match-away-${Number(match.id)}`);
        const statusSelect = document.getElementById(`match-status-${Number(match.id)}`);
        if (homeInput) homeInput.value = draft.homeScore ?? '';
        if (awayInput) awayInput.value = draft.awayScore ?? '';
        if (statusSelect && ['scheduled', 'played', 'home_forfeit', 'away_forfeit', 'double_forfeit'].includes(String(draft.status || ''))) {
            statusSelect.value = String(draft.status);
        }
    }
    modal.querySelectorAll('[data-event-count], [data-match-own-goals]').forEach(input => { input.value = ''; });
    modal.querySelectorAll('[data-match-event-mvp]').forEach(input => { input.checked = false; });
    (draft.events || []).forEach(event => {
        if (event.event_type === 'own_goal') {
            const input = Array.from(modal.querySelectorAll('[data-match-own-goals]'))
                .find(item => String(item.dataset.teamName || '') === String(event.team_name || ''));
            if (input) input.value = Number(event.quantity || 0) || '';
            return;
        }
        const row = Array.from(modal.querySelectorAll('[data-match-event-matrix-row]')).find(item => {
            const sameTeam = String(item.dataset.teamName || '') === String(event.team_name || '');
            const samePlayer = Number(event.player_uid || 0) > 0
                ? Number(item.dataset.playerUid || 0) === Number(event.player_uid || 0)
                : String(item.dataset.playerName || '') === String(event.player_name || '');
            return sameTeam && samePlayer;
        });
        if (!row) return;
        if (event.event_type === 'mvp') row.querySelector('[data-match-event-mvp]').checked = true;
        else {
            const input = row.querySelector(`[data-event-count="${event.event_type}"]`);
            if (input) input.value = Number(event.quantity || 0) || '';
        }
    });
    handleMatchStatusChange(match.id, {markDirty: false, resetScheduled: true});
    matchEventEditorDirty = true;
    updateMatchEventEditorTotals();
    const status = document.getElementById('matchEventModalStatus');
    if (status) status.textContent = `已恢复 ${new Date(Number(draft.updatedAt || Date.now())).toLocaleString('zh-CN')} 的本机草稿`;
    return true;
}

function buildScheduleMatchSnapshot(match) {
    return {
        match_id: Number(match.id),
        home_score: match.home_score === null || match.home_score === undefined ? null : Number(match.home_score),
        away_score: match.away_score === null || match.away_score === undefined ? null : Number(match.away_score),
        status: String(match.status || ''),
        events: normalizeMatchEventsForDraft(match.events || []),
    };
}

async function restoreScheduleMatchSnapshot(snapshot) {
    if (!snapshot?.match_id) return;
    setScheduleMatchSaveState(snapshot.match_id, 'saving', '正在撤销');
    try {
        const result = await workJsonRequest('/api/admin/matches/batch', {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({matches: [snapshot]}),
        });
        if (!result || !result.response.ok || !result.data.success) throw new Error(result?.data?.detail || result?.data?.message || '撤销失败');
        applyMatchPayloadLocally(snapshot);
        setScheduleMatchSaveState(snapshot.match_id, 'saved', '已撤销上一次修改');
        renderScheduleBoard();
        invalidateCompetitionSections(['standings', 'playerRankings', 'suspensions']);
        await refreshPlayerRankingsData();
        await refreshCompetitionWorkSummary({renderBoards: false});
        renderCompetitionDataStatus();
        showUiToast('已撤销上一次比赛数据修改', 'success');
    } catch (error) {
        setScheduleMatchSaveState(snapshot.match_id, 'error', error.message || '撤销失败');
        showUiToast(error.message || '撤销失败，请重试', 'danger', {duration: 5200});
    }
}

async function openMatchEventEditor(matchId) {
    const match = findScheduleMatchById(matchId);
    if (!match) return;
    if (canManageCurrentCompetitionSchedule() && !await ensureCompetitionPlayersLoaded()) return;
    if (document.getElementById('matchEventEditorModal') && matchEventEditorDirty) persistMatchEventDraftNow();
    closeMatchEventEditor(true);
    activeMatchEventEditorMatchId = Number(matchId);
    matchEventEditorDirty = false;
    matchEventEditorReturnFocus = document.activeElement;
    const host = document.createElement('div');
    host.innerHTML = canManageCurrentCompetitionSchedule() ? renderMatchEventEditorDialog(match) : renderMatchEventViewerDialog(match);
    const modal = host.firstElementChild;
    if (!modal) return;
    document.body.appendChild(modal);
    document.body.classList.add('match-event-modal-open');
    if (canManageCurrentCompetitionSchedule()) {
        handleMatchStatusChange(match.id, {markDirty: false});
        restoreStoredMatchEventDraft(match);
    }
    globalThis.refreshHorizontalScrollAffordances?.(modal);
    window.requestAnimationFrame(() => modal.querySelector('.match-event-modal')?.focus());
}

async function closeMatchEventEditor(force = false) {
    if (!force && matchEventEditorDirty) {
        persistMatchEventDraftNow();
        if (!await showConfirmDialog({title: '关闭比赛数据', message: '当前修改已保存为本机草稿，再次打开这场比赛时会自动恢复。', confirmLabel: '保留草稿并关闭'})) return;
    }
    document.getElementById('matchEventEditorModal')?.remove();
    document.body.classList.remove('match-event-modal-open');
    activeMatchEventEditorMatchId = null;
    matchEventEditorDirty = false;
    const returnFocus = matchEventEditorReturnFocus;
    matchEventEditorReturnFocus = null;
    if (returnFocus?.isConnected) returnFocus.focus();
}

function switchMatchEventEditorTeam(side) {
    const modal = document.getElementById('matchEventEditorModal');
    if (!modal) return;
    modal.querySelectorAll('[data-match-event-team-tab]').forEach(button => {
        const active = button.dataset.matchEventTeamTab === side;
        button.classList.toggle('active', active);
        button.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    modal.querySelectorAll('[data-match-event-team-panel]').forEach(panel => {
        panel.hidden = panel.dataset.matchEventTeamPanel !== side;
    });
    modal.querySelector(`[data-match-event-team-panel="${side}"] input`)?.focus();
}

function markMatchEventEditorDirty() {
    matchEventEditorDirty = true;
    updateMatchEventEditorTotals();
    scheduleMatchEventDraftSave();
}

function getMatchEventEditorStatus(matchId) {
    const match = findScheduleMatchById(matchId);
    return String(document.getElementById(`match-status-${Number(matchId)}`)?.value || match?.status || 'scheduled');
}

function setMatchEventMatrixAvailability(disabled) {
    const modal = document.getElementById('matchEventEditorModal');
    if (!modal) return;
    modal.classList.toggle('is-result-only', Boolean(disabled));
    modal.querySelectorAll('.match-event-modal-body input').forEach(input => {
        input.disabled = Boolean(disabled);
    });
}

function clearMatchEventMatrixValues() {
    const modal = document.getElementById('matchEventEditorModal');
    if (!modal) return;
    modal.querySelectorAll('[data-event-count], [data-match-own-goals]').forEach(input => {
        input.value = '';
    });
    modal.querySelectorAll('[data-match-event-mvp]').forEach(input => {
        input.checked = false;
    });
}

function syncMatchEventScorePresentation(matchId) {
    const modal = document.getElementById('matchEventEditorModal');
    if (!modal || Number(modal.dataset.matchId || 0) !== Number(matchId)) return;
    const homeRaw = String(document.getElementById(`match-home-${Number(matchId)}`)?.value || '').trim();
    const awayRaw = String(document.getElementById(`match-away-${Number(matchId)}`)?.value || '').trim();
    modal.dataset.homeScore = homeRaw;
    modal.dataset.awayScore = awayRaw;
    const output = modal.querySelector('[data-match-score-display]');
    if (output) output.textContent = homeRaw !== '' && awayRaw !== '' ? `${homeRaw} - ${awayRaw}` : '-';
}

function handleMatchScoreEditorInput(matchId) {
    const statusSelect = document.getElementById(`match-status-${Number(matchId)}`);
    const homeRaw = String(document.getElementById(`match-home-${Number(matchId)}`)?.value || '').trim();
    const awayRaw = String(document.getElementById(`match-away-${Number(matchId)}`)?.value || '').trim();
    if (statusSelect?.value === 'scheduled' && (homeRaw !== '' || awayRaw !== '')) {
        statusSelect.value = 'played';
        handleMatchStatusChange(matchId, {markDirty: false});
    }
    syncMatchEventScorePresentation(matchId);
    markMatchEventEditorDirty();
}

function updateMatchEventEditorTotals() {
    const modal = document.getElementById('matchEventEditorModal');
    if (!modal) return;
    let totalGoals = 0;
    let totalAssists = 0;
    let mvpName = '';
    const teamGoals = {home: 0, away: 0};
    modal.querySelectorAll('[data-match-event-team-panel]').forEach(panel => {
        const side = panel.dataset.matchEventTeamPanel;
        panel.querySelectorAll('[data-match-event-matrix-row]').forEach(row => {
            const goals = Math.max(0, Number(row.querySelector('[data-event-count="goal"]')?.value || 0) || 0);
            const assists = Math.max(0, Number(row.querySelector('[data-event-count="assist"]')?.value || 0) || 0);
            teamGoals[side] += goals;
            totalGoals += goals;
            totalAssists += assists;
            if (row.querySelector('[data-match-event-mvp]')?.checked) mvpName = String(row.dataset.playerName || '');
        });
        const ownGoals = Math.max(0, Number(panel.querySelector('[data-match-own-goals]')?.value || 0) || 0);
        teamGoals[side] += ownGoals;
        totalGoals += ownGoals;
    });
    const goalsOutput = modal.querySelector('[data-match-event-summary-goals]');
    const assistsOutput = modal.querySelector('[data-match-event-summary-assists]');
    const mvpOutput = modal.querySelector('[data-match-event-summary-mvp]');
    if (goalsOutput) goalsOutput.textContent = String(totalGoals);
    if (assistsOutput) assistsOutput.textContent = String(totalAssists);
    if (mvpOutput) mvpOutput.textContent = mvpName || '待评选';
    Object.entries(teamGoals).forEach(([side, total]) => {
        const output = modal.querySelector(`[data-match-event-team-total="${side}"]`);
        if (output) output.textContent = `${total} 球`;
    });
    const status = document.getElementById('matchEventModalStatus');
    if (status && matchEventEditorDirty) {
        const homeScore = String(document.getElementById(`match-home-${Number(modal.dataset.matchId || 0)}`)?.value || '').trim();
        const awayScore = String(document.getElementById(`match-away-${Number(modal.dataset.matchId || 0)}`)?.value || '').trim();
        const scoreMismatch = getMatchEventEditorStatus(modal.dataset.matchId) === 'played' && homeScore !== '' && awayScore !== ''
            && (teamGoals.home !== Number(homeScore) || teamGoals.away !== Number(awayScore));
        status.textContent = scoreMismatch ? '有未保存修改 · 进球合计与比分不一致' : '有未保存修改';
        status.classList.toggle('is-warning', scoreMismatch);
    }
}

function selectMatchEventMvp(input) {
    if (input?.checked) {
        document.querySelectorAll('#matchEventEditorModal [data-match-event-mvp]').forEach(item => {
            if (item !== input) item.checked = false;
        });
    }
    markMatchEventEditorDirty();
}

function readMatchEventMatrixCount(input, label) {
    const raw = String(input?.value || '').trim();
    if (!raw) return 0;
    const value = Number(raw);
    if (!Number.isInteger(value) || value < 0) throw new Error(`${label}必须是 0 或正整数。`);
    return value;
}

function readMatchEventMatrixPayload(matchId) {
    const modal = document.getElementById('matchEventEditorModal');
    const match = findScheduleMatchById(matchId);
    if (!modal || !match || Number(modal.dataset.matchId || 0) !== Number(matchId)) throw new Error('比赛数据窗口已失效，请重新打开。');
    const validTeams = new Set(getMatchTeamOptions(match).map(team => team.team_name));
    const events = [];
    modal.querySelectorAll('[data-match-event-matrix-row]').forEach(row => {
        const teamName = String(row.dataset.teamName || '');
        const playerUid = Number(row.dataset.playerUid || 0);
        const playerName = String(row.dataset.playerName || '');
        if (!validTeams.has(teamName)) throw new Error('球员所属球队与本场比赛不一致。');
        const goals = readMatchEventMatrixCount(row.querySelector('[data-event-count="goal"]'), `${playerName}的进球数`);
        const assists = readMatchEventMatrixCount(row.querySelector('[data-event-count="assist"]'), `${playerName}的助攻数`);
        if (goals) events.push({team_name: teamName, player_uid: playerUid || null, player_name: playerName, event_type: 'goal', quantity: goals});
        if (assists) events.push({team_name: teamName, player_uid: playerUid || null, player_name: playerName, event_type: 'assist', quantity: assists});
        if (row.querySelector('[data-match-event-mvp]')?.checked) events.push({team_name: teamName, player_uid: playerUid || null, player_name: playerName, event_type: 'mvp', quantity: 1});
    });
    modal.querySelectorAll('[data-match-own-goals]').forEach(input => {
        const teamName = String(input.dataset.teamName || '');
        const quantity = readMatchEventMatrixCount(input, `${teamName}的乌龙球数`);
        if (quantity) events.push({team_name: teamName, player_uid: null, player_name: '乌龙球', event_type: 'own_goal', quantity});
    });
    if (events.filter(event => event.event_type === 'mvp').length > 1) throw new Error('本场最佳只能选择一名球员。');
    return events;
}

function getNextScheduleMatchForEntry(currentMatchId) {
    const matches = sortScheduleMatches(getFilteredScheduleMatches());
    const currentIndex = matches.findIndex(match => Number(match.id) === Number(currentMatchId));
    return currentIndex >= 0 ? (matches[currentIndex + 1] || null) : null;
}

async function saveMatchEventEditor(openNext = false) {
    const matchId = Number(activeMatchEventEditorMatchId || 0);
    const matchBeforeSave = findScheduleMatchById(matchId);
    const previousSnapshot = matchBeforeSave ? buildScheduleMatchSnapshot(matchBeforeSave) : null;
    const status = document.getElementById('matchEventModalStatus');
    const saveButton = document.getElementById('matchEventModalSave');
    const saveNextButton = document.getElementById('matchEventModalSaveNext');
    if (!matchId || !saveButton) return;
    let payload;
    try {
        payload = readMatchScorePayload(matchId, readMatchEventMatrixPayload(matchId));
    } catch (error) {
        if (status) status.textContent = error.message || '比赛数据填写不完整';
        return;
    }
    persistMatchEventDraftNow();
    if (scheduleMatchSaveInFlight.has(matchId)) {
        if (status) status.textContent = '比分正在保存，请稍后再保存球员数据';
        return;
    }
    if (scheduleAutoSaveTimers.has(matchId)) {
        window.clearTimeout(scheduleAutoSaveTimers.get(matchId));
        scheduleAutoSaveTimers.delete(matchId);
    }
    scheduleMatchSaveVersions.set(matchId, Number(scheduleMatchSaveVersions.get(matchId) || 0) + 1);
    scheduleMatchSaveInFlight.add(matchId);
    setScheduleMatchSaveState(matchId, 'saving');
    saveButton.disabled = true;
    saveButton.textContent = '保存中...';
    if (saveNextButton) saveNextButton.disabled = true;
    if (status) status.textContent = '正在保存比赛数据';
    try {
        const result = await workJsonRequest('/api/admin/matches/batch', {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({matches: [payload]}),
        });
        if (!result) throw new Error('保存请求失败');
        const {response, data} = result;
        if (!response.ok || !data.success) throw new Error(data.detail || data.message || '保存比赛数据失败');
        applyMatchPayloadLocally(payload);
        const nextMatch = openNext ? getNextScheduleMatchForEntry(matchId) : null;
        setScheduleMatchSaveState(matchId, 'saved');
        matchEventEditorDirty = false;
        clearStoredMatchEventDraft(matchId);
        closeMatchEventEditor(true);
        renderScheduleBoard();
        invalidateCompetitionSections(['standings', 'playerRankings', 'suspensions']);
        await refreshPlayerRankingsData();
        await refreshCompetitionWorkSummary({renderBoards: false});
        renderCompetitionDataStatus();
        if (nextMatch) await openMatchEventEditor(nextMatch.id);
        if (typeof showUiToast === 'function') {
            const successMessage = openNext
                ? (nextMatch ? `已保存，继续录入第 ${Number(nextMatch.round_no) || '-'} 轮下一场` : '已保存，当前范围没有下一场比赛')
                : '比赛数据已保存';
            showUiToast(successMessage, 'success', previousSnapshot ? {
                duration: 8000,
                actionLabel: '撤销',
                onAction: () => restoreScheduleMatchSnapshot(previousSnapshot),
            } : {});
        }
    } catch (error) {
        setScheduleMatchSaveState(matchId, 'error', error.message || '保存失败，点击重试');
        if (status) status.textContent = error.message || '保存失败，请重试';
        saveButton.disabled = false;
        saveButton.textContent = '重新保存';
        if (saveNextButton) saveNextButton.disabled = false;
    } finally {
        scheduleMatchSaveInFlight.delete(matchId);
    }
}

function handleMatchEventEditorKeydown(event) {
    const modal = document.getElementById('matchEventEditorModal');
    if (!modal) return;
    if (event.key === 'Escape') {
        closeMatchEventEditor();
        return;
    }
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        saveMatchEventEditor(false);
        return;
    }
    if (event.key === 'Enter' && event.target instanceof HTMLInputElement && event.target.type === 'number') {
        event.preventDefault();
        const visiblePanel = modal.querySelector('[data-match-event-team-panel]:not([hidden])');
        const scoreInputs = [modal.querySelector('[data-match-score-side="home"]'), modal.querySelector('[data-match-score-side="away"]')].filter(item => item && !item.disabled);
        const eventInputs = visiblePanel
            ? Array.from(visiblePanel.querySelectorAll('input[type="number"]:not(:disabled)'))
            : [];
        const sequence = [...scoreInputs, ...eventInputs];
        const currentIndex = sequence.indexOf(event.target);
        const nextIndex = currentIndex + (event.shiftKey ? -1 : 1);
        if (sequence[nextIndex]) {
            sequence[nextIndex].focus();
            sequence[nextIndex].select?.();
            return;
        }
        const activeSide = visiblePanel?.dataset.matchEventTeamPanel;
        if (!event.shiftKey && activeSide === 'home') {
            switchMatchEventEditorTeam('away');
            const firstAwayInput = modal.querySelector('[data-match-event-team-panel="away"] input[type="number"]:not(:disabled)');
            firstAwayInput?.focus();
            firstAwayInput?.select?.();
            return;
        }
        if (event.shiftKey && activeSide === 'away') {
            switchMatchEventEditorTeam('home');
            const homeInputs = modal.querySelectorAll('[data-match-event-team-panel="home"] input[type="number"]:not(:disabled)');
            const lastHomeInput = homeInputs[homeInputs.length - 1];
            lastHomeInput?.focus();
            lastHomeInput?.select?.();
            return;
        }
        document.getElementById('matchEventModalSaveNext')?.focus();
        return;
    }
    if (event.key !== 'Tab') return;
    const focusable = Array.from(modal.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex]:not([tabindex="-1"])'))
        .filter(item => !item.closest('[hidden]'));
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
    }
}

document.addEventListener('keydown', handleMatchEventEditorKeydown);

function addMatchEventRow(matchId) {
    const match = findScheduleMatchById(matchId);
    const list = document.querySelector(`#match-events-${matchId} .match-event-list`);
    if (!match || !list) return;
    list.insertAdjacentHTML('beforeend', renderMatchEventRow(match));
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

function handleMatchEventTypeChange(typeSelect, matchId) {
    const row = typeSelect?.closest('[data-match-event-row]');
    const playerInput = row?.querySelector('.match-event-player');
    const playerButton = row?.querySelector('.match-event-player-select');
    const isOwnGoal = String(typeSelect?.value || '') === 'own_goal';
    if (!row || !playerInput) return;
    row.dataset.eventType = isOwnGoal ? 'own_goal' : String(typeSelect.value || 'goal');
    row.classList.toggle('is-own-goal', isOwnGoal);
    playerInput.disabled = isOwnGoal;
    playerButton && (playerButton.disabled = isOwnGoal);
    playerInput.placeholder = isOwnGoal ? '无需选择球员' : '输入或选择球员';
    if (isOwnGoal) {
        playerInput.value = '';
        closeMatchEventSuggestions();
    }
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

function getScheduleMatchSaveState(matchId) {
    return scheduleMatchSaveStates.get(Number(matchId)) || {state: 'idle', message: '未修改'};
}

function renderScheduleMatchSaveState(matchId) {
    const status = getScheduleMatchSaveState(matchId);
    return `<span class="match-save-state ui-save-state is-${escapeHtml(status.state)}" data-match-save-id="${Number(matchId)}" role="status" aria-live="polite">${escapeHtml(status.message)}</span>`;
}

function setScheduleMatchSaveState(matchId, state, message = '') {
    const numericMatchId = Number(matchId || 0);
    if (!numericMatchId) return;
    const fallbackMessages = {
        idle: '未修改',
        dirty: '有未保存修改',
        saving: '保存中...',
        saved: `已保存 ${new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})}`,
        error: '保存失败，点击重试',
    };
    const nextState = {state, message: message || fallbackMessages[state] || ''};
    scheduleMatchSaveStates.set(numericMatchId, nextState);
    document.querySelectorAll(`[data-match-save-id="${numericMatchId}"]`).forEach(element => {
        element.className = `match-save-state ui-save-state is-${state}`;
        element.textContent = nextState.message;
        element.onclick = state === 'error' ? () => saveScheduleMatchQuietly(numericMatchId) : null;
        element.setAttribute('role', state === 'error' ? 'button' : 'status');
        element.setAttribute('aria-live', state === 'error' ? 'assertive' : 'polite');
        element.tabIndex = state === 'error' ? 0 : -1;
    });
}

function handleMatchStatusChange(matchId, options = {}) {
    const statusSelect = document.getElementById(`match-status-${matchId}`);
    const homeInput = document.getElementById(`match-home-${matchId}`);
    const awayInput = document.getElementById(`match-away-${matchId}`);
    const editor = statusSelect?.closest('.match-event-score-editor');
    const note = document.getElementById('matchEventScoreNote');
    const selectedStatus = String(statusSelect?.value || 'scheduled');
    const score = getForfeitScoreForStatus(selectedStatus);
    const isScheduled = selectedStatus === 'scheduled';
    const lockScore = Boolean(score);
    if (homeInput) homeInput.readOnly = lockScore;
    if (awayInput) awayInput.readOnly = lockScore;
    editor?.classList.toggle('is-forfeit', Boolean(score));
    editor?.classList.toggle('is-scheduled', isScheduled);
    if (score) {
        if (homeInput) homeInput.value = score.home_score;
        if (awayInput) awayInput.value = score.away_score;
    } else if (isScheduled && (options.markDirty !== false || options.resetScheduled === true)) {
        if (homeInput) homeInput.value = '';
        if (awayInput) awayInput.value = '';
        clearMatchEventMatrixValues();
    }
    if (note) {
        note.textContent = isScheduled
            ? '直接填写比分会自动切换为正常比赛；主动改回未赛会清空本场数据。'
            : (score
                ? getForfeitRuleNote(selectedStatus)
                : '比分、比赛判定和球员数据会一次提交。');
    }
    setMatchEventMatrixAvailability(Boolean(score) || isScheduled);
    syncMatchEventScorePresentation(matchId);
    if (options.markDirty !== false) markMatchEventEditorDirty();
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
    const events = Array.isArray(match.events) ? match.events : [];
    const goalCount = events.filter(event => ['goal', 'own_goal'].includes(event.event_type)).reduce((total, event) => total + Number(event.quantity || 0), 0);
    const assistCount = events.filter(event => event.event_type === 'assist').reduce((total, event) => total + Number(event.quantity || 0), 0);
    const hasMvp = events.some(event => event.event_type === 'mvp');
    const expanded = expandedMobileScheduleMatches.has(Number(match.id)) || Number(currentCompetitionWorkTargetMatchId || 0) === Number(match.id);
    const detailsId = `mobileScheduleDetails-${Number(match.id)}`;
    return `
        <article class="mobile-schedule-card ${played ? 'is-played' : 'is-pending'} ${expanded ? 'is-expanded' : ''} ${getCompetitionWorkMatchClass(match.id)}" data-match-id="${Number(match.id) || 0}">
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
            <div class="mobile-schedule-detail-bar">
                <span><strong>${goalCount}</strong>进球</span>
                <span><strong>${assistCount}</strong>助攻</span>
                <span class="${hasMvp ? 'is-ready' : ''}">${hasMvp ? '已评最佳' : '最佳待补'}</span>
                <button type="button" onclick="toggleMobileScheduleMatchDetails(${Number(match.id)})" aria-expanded="${expanded ? 'true' : 'false'}" aria-controls="${detailsId}">${expanded ? '收起' : '明细'}${uiIconSvg('chevron-down', 'ui-icon is-small')}</button>
            </div>
            ${expanded ? `<div class="mobile-schedule-card-events" id="${detailsId}">${renderScheduleMatchEvents(match)}</div>` : ''}
            ${renderCompetitionWorkMatchIssue(match.id)}
            ${canManageCurrentCompetitionSchedule() ? `
                <div class="mobile-schedule-edit-actions">
                    <button class="mobile-schedule-edit-trigger is-player-data" type="button" onclick="openMatchEventEditor(${Number(match.id)})">
                        <span>编辑比赛数据</span>
                        <span aria-hidden="true">›</span>
                    </button>
                </div>
            ` : ''}
        </article>
    `;
}

function toggleMobileScheduleMatchDetails(matchId) {
    const numericMatchId = Number(matchId || 0);
    if (!numericMatchId) return;
    if (expandedMobileScheduleMatches.has(numericMatchId)) expandedMobileScheduleMatches.delete(numericMatchId);
    else expandedMobileScheduleMatches.add(numericMatchId);
    renderScheduleBoard();
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
}

function renderMobileScheduleList(matches, rounds = []) {
    const visibleRounds = (rounds || []).length
        ? rounds
        : [...new Set((matches || []).map(match => Number(match.round_no)).filter(Boolean))].sort((a, b) => a - b);
    return `
        <div class="mobile-schedule-card-list">
            ${visibleRounds.map(roundNo => {
                const roundMatches = sortScheduleMatches((matches || []).filter(match => Number(match.round_no) === Number(roundNo)));
                return `
                    <section class="mobile-schedule-round-section">
                        <header class="mobile-schedule-round-section-head">
                            <h3>第 ${Number(roundNo) || '-'} 轮</h3>
                            <span>${roundMatches.filter(isScheduleMatchPlayed).length}/${roundMatches.length} 已赛</span>
                        </header>
                        <div class="mobile-schedule-round-section-list">
                            ${roundMatches.length
                                ? roundMatches.map(renderMobileScheduleMatchCard).join('')
                                : '<article class="mobile-schedule-card is-empty"><span>本轮暂无对阵</span></article>'}
                        </div>
                    </section>
                `;
            }).join('')}
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
            </div>
            <div class="mobile-schedule-list">
                ${buildSchedulePairRows(roundPair.matches).map(pair => renderMobileSchedulePair(pair, roundPair)).join('')}
            </div>
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

function getCompetitionImagePixelRatio(kind, target) {
    const deviceRatio = Math.max(1, Number(window.devicePixelRatio || 1));
    if (kind === 'rankings') return Math.max(1.5, Math.min(2, deviceRatio));
    if (kind !== 'suspensions') return Math.max(2, Math.min(3, deviceRatio));
    const cssWidth = Math.max(1, Number(target?.scrollWidth || target?.offsetWidth || 1));
    const cssHeight = Math.max(1, Number(target?.scrollHeight || target?.offsetHeight || 1));
    const preferredRatio = Math.max(1.25, Math.min(1.8, deviceRatio));
    const areaLimitedRatio = Math.sqrt(SUSPENSION_IMAGE_TARGET_PIXELS / (cssWidth * cssHeight));
    return Math.max(1, Math.min(preferredRatio, areaLimitedRatio));
}

function canvasToCompetitionBlob(canvas, type, quality) {
    return new Promise(resolve => canvas.toBlob(resolve, type, quality));
}

async function decodeCompetitionImageBlob(blob) {
    if (typeof window.createImageBitmap === 'function') {
        const bitmap = await window.createImageBitmap(blob);
        return {
            source: bitmap,
            width: bitmap.width,
            height: bitmap.height,
            release: () => bitmap.close?.(),
        };
    }
    const objectUrl = URL.createObjectURL(blob);
    try {
        const image = await new Promise((resolve, reject) => {
            const element = new Image();
            element.onload = () => resolve(element);
            element.onerror = reject;
            element.src = objectUrl;
        });
        return {
            source: image,
            width: image.naturalWidth || image.width,
            height: image.naturalHeight || image.height,
            release: () => {},
        };
    } finally {
        URL.revokeObjectURL(objectUrl);
    }
}

function getCompetitionImageBackground(target) {
    const backgroundColor = window.getComputedStyle?.(target)?.backgroundColor;
    if (backgroundColor && backgroundColor !== 'rgba(0, 0, 0, 0)' && backgroundColor !== 'transparent') {
        return backgroundColor;
    }
    return document.body.classList.contains('light-mode') ? '#f5f5f8' : '#1a1b26';
}

async function compressSuspensionImageBlob(blob, backgroundColor) {
    if (blob.size <= SUSPENSION_IMAGE_MAX_BYTES) {
        return {blob, extension: 'png', compressed: false};
    }
    const decoded = await decodeCompetitionImageBlob(blob);
    let scale = 1;
    let smallestBlob = null;
    try {
        for (let attempt = 0; attempt < 9; attempt += 1) {
            const width = Math.max(SUSPENSION_IMAGE_MIN_WIDTH, Math.round(decoded.width * scale));
            const height = Math.max(1, Math.round(decoded.height * (width / decoded.width)));
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const context = canvas.getContext('2d', {alpha: false});
            if (!context) throw new Error('capture-compression-context-missing');
            context.fillStyle = backgroundColor || '#ffffff';
            context.fillRect(0, 0, width, height);
            context.imageSmoothingEnabled = true;
            context.imageSmoothingQuality = 'high';
            context.drawImage(decoded.source, 0, 0, width, height);

            let smallestAtScale = null;
            for (const quality of [0.9, 0.82, 0.74, 0.66, 0.58, 0.5]) {
                const candidate = await canvasToCompetitionBlob(canvas, 'image/jpeg', quality);
                if (!candidate) continue;
                if (!smallestBlob || candidate.size < smallestBlob.size) smallestBlob = candidate;
                if (!smallestAtScale || candidate.size < smallestAtScale.size) smallestAtScale = candidate;
                if (candidate.size <= SUSPENSION_IMAGE_MAX_BYTES) {
                    return {blob: candidate, extension: 'jpg', compressed: true};
                }
            }
            if (width <= SUSPENSION_IMAGE_MIN_WIDTH || !smallestAtScale) break;
            const requiredScale = Math.sqrt(SUSPENSION_IMAGE_MAX_BYTES / Math.max(1, smallestAtScale.size));
            scale *= Math.min(0.86, Math.max(0.55, requiredScale * 0.92));
            if (decoded.width * scale < SUSPENSION_IMAGE_MIN_WIDTH) {
                scale = SUSPENSION_IMAGE_MIN_WIDTH / decoded.width;
            }
        }
    } finally {
        decoded.release();
    }
    if (smallestBlob && smallestBlob.size <= SUSPENSION_IMAGE_MAX_BYTES) {
        return {blob: smallestBlob, extension: 'jpg', compressed: true};
    }
    throw new Error('suspension-image-still-too-large');
}

function buildCompetitionImageFileName(kind, level, extension = 'png') {
    const cleanLevel = String(level || currentCompetitionLevel || 'HEIGO').replace(/[\\/:*?"<>|\s]+/g, '_');
    const label = kind === 'suspensions' ? '伤停统计' : kind === 'rankings' ? '排位积分榜' : '积分榜';
    const date = new Date();
    const stamp = [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, '0'),
        String(date.getDate()).padStart(2, '0'),
    ].join('');
    const safeExtension = extension === 'jpg' ? 'jpg' : 'png';
    return kind === 'rankings' ? `HEIGO_${label}_${stamp}.${safeExtension}` : `HEIGO_${cleanLevel}_${label}_${stamp}.${safeExtension}`;
}

function buildRankingExcelFileName() {
    const date = new Date();
    const stamp = [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, '0'),
        String(date.getDate()).padStart(2, '0'),
    ].join('');
    return `HEIGO_排位积分榜_${stamp}.xlsx`;
}

function buildSuspensionsExcelFileName(level) {
    const cleanLevel = String(level || currentCompetitionLevel || 'HEIGO').replace(/[\\/:*?"<>|\s]+/g, '_');
    const date = new Date();
    const stamp = [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, '0'),
        String(date.getDate()).padStart(2, '0'),
    ].join('');
    return `HEIGO_${cleanLevel}_伤停统计_${stamp}.xlsx`;
}

function buildStandingsExcelFileName(level) {
    const cleanLevel = String(level || currentCompetitionLevel || 'HEIGO').replace(/[\\/:*?"<>|\s]+/g, '_');
    const date = new Date();
    const stamp = [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, '0'),
        String(date.getDate()).padStart(2, '0'),
    ].join('');
    return `HEIGO_${cleanLevel}_积分榜与赛程_${stamp}.xlsx`;
}

async function exportStandingsExcel(level = currentCompetitionLevel) {
    try {
        const response = await fetchWithTimeout(`/api/export/standings.xlsx?level=${encodeURIComponent(level)}`);
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || '积分榜 Excel 导出失败');
        }
        downloadCompetitionBlob(await response.blob(), buildStandingsExcelFileName(level));
    } catch (error) {
        console.error('Failed to export standings Excel:', error);
        showModal('导出失败', escapeHtml(error.message || '积分榜 Excel 导出失败，请稍后重试。'));
    }
}

async function exportRankingExcel() {
    try {
        const response = await fetchWithTimeout('/api/export/rankings.xlsx');
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || '排位 Excel 导出失败');
        }
        downloadCompetitionBlob(await response.blob(), buildRankingExcelFileName());
    } catch (error) {
        console.error('Failed to export ranking Excel:', error);
        showModal('导出失败', escapeHtml(error.message || '排位 Excel 导出失败，请稍后重试。'));
    }
}

async function exportSuspensionsExcel(level = currentCompetitionLevel) {
    try {
        const response = await fetchWithTimeout(`/api/export/suspensions.xlsx?level=${encodeURIComponent(level)}`);
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || '伤停 Excel 导出失败');
        }
        downloadCompetitionBlob(await response.blob(), buildSuspensionsExcelFileName(level));
    } catch (error) {
        console.error('Failed to export suspensions Excel:', error);
        showModal('导出失败', escapeHtml(error.message || '伤停 Excel 导出失败，请稍后重试。'));
    }
}

function renderSuspensionCaptureRecords(records) {
    return (records || []).map(record => `
        <div class="suspension-capture-player">
            <strong>${escapeHtml(record.player_name || '-')}</strong>
            <span>${escapeHtml(getSuspensionRecordLabel(record))}</span>
            ${record.notes ? `<em>${escapeHtml(record.notes)}</em>` : ''}
        </div>
    `).join('');
}

function renderSuspensionCaptureSection(title, records, className) {
    if (!records || !records.length) return '';
    return `
        <section class="suspension-capture-section ${className}">
            <h4>${escapeHtml(title)}</h4>
            <div>${renderSuspensionCaptureRecords(records)}</div>
        </section>
    `;
}

function createSuspensionCapturePanel(level) {
    const levelTeams = (suspensionData.teams || []).filter(team => team.level === level);
    const activeTeams = levelTeams.filter(team => getSuspensionTeamSummary(team).hasContent);
    const clearTeams = levelTeams.filter(team => !getSuspensionTeamSummary(team).hasContent);
    const cautionCount = levelTeams.reduce((total, team) => total + getSuspensionTeamSummary(team).cautionCount, 0);
    const suspendedCount = levelTeams.reduce((total, team) => total + getSuspensionTeamSummary(team).suspendedCount, 0);
    const roundNo = getSuspensionUpdateRound(level);
    const updateNote = getSuspensionUpdateNote(level);
    const host = document.createElement('div');
    host.className = 'suspension-capture-host';
    host.setAttribute('aria-hidden', 'true');
    host.innerHTML = `
        <section class="suspension-capture-panel">
            <header class="suspension-capture-header">
                <div>
                    <span>HEIGO DISCIPLINE REPORT</span>
                    <h2>${escapeHtml(level)}伤停统计</h2>
                    <p>${escapeHtml(formatSuspensionRoundProgress(roundNo))}${updateNote ? ` · ${escapeHtml(updateNote)}` : ''}</p>
                </div>
                <strong class="${activeTeams.length ? 'is-active' : 'is-clear'}">${activeTeams.length ? `${activeTeams.length} 队有记录` : '本轮无伤停记录'}</strong>
            </header>
            <div class="suspension-capture-summary">
                <span><small>参赛球队</small><strong>${levelTeams.length}</strong></span>
                <span><small>黄牌关注</small><strong>${cautionCount}</strong></span>
                <span class="is-danger"><small>停赛球员</small><strong>${suspendedCount}</strong></span>
                <span><small>涉及球队</small><strong>${activeTeams.length}</strong></span>
            </div>
            ${activeTeams.length ? `<div class="suspension-capture-grid">
                ${activeTeams.map(team => {
                    const teamRound = getSuspensionTeamRound(team.team_id);
                    const teamNote = getSuspensionTeamNote(team.team_id);
                    return `<article class="suspension-capture-team">
                        <header><div><h3>${escapeHtml(team.team_name)}</h3><span>${escapeHtml(team.manager || '主教练待定')}</span></div><em>${teamRound !== null ? (teamRound >= 34 ? '赛季核对完成' : `核对至第 ${teamRound} 轮 · 适用于第 ${teamRound + 1} 轮`) : '轮次待补'}</em></header>
                        ${teamNote ? `<p class="suspension-capture-team-note">${escapeHtml(teamNote)}</p>` : ''}
                        <div class="suspension-capture-sections">
                            ${renderSuspensionCaptureSection('1张黄牌', team.one_yellow, 'is-one-yellow')}
                            ${renderSuspensionCaptureSection('2张黄牌', team.two_yellows, 'is-two-yellows')}
                            ${renderSuspensionCaptureSection('停赛', team.suspended, 'is-suspended')}
                        </div>
                        ${(team.notes || []).filter(Boolean).length ? `<p class="suspension-capture-notes">备注：${escapeHtml((team.notes || []).filter(Boolean).join('；'))}</p>` : ''}
                    </article>`;
                }).join('')}
            </div>` : `<div class="suspension-capture-clear-state"><strong>当前没有黄牌关注或停赛记录</strong><span>全部 ${levelTeams.length} 支球队均无伤停记录</span></div>`}
            ${clearTeams.length ? `<footer class="suspension-capture-clear-teams"><strong>暂无记录球队 · ${clearTeams.length}</strong><span>${clearTeams.map(team => escapeHtml(team.team_name)).join('、')}</span></footer>` : ''}
        </section>
    `;
    document.body.appendChild(host);
    return {host, panel: host.querySelector('.suspension-capture-panel')};
}

async function saveCompetitionImage(kind, level = currentCompetitionLevel) {
    if (competitionImageExportBusy) return;
    try {
        await ensureHtmlToImage();
    } catch (error) {
        console.error('Failed to load image export component:', error);
    }
    if (!window.htmlToImage || typeof window.htmlToImage.toBlob !== 'function') {
        showModal('导出组件未就绪', '页面截图组件加载失败，请刷新页面后重试。');
        return;
    }
    const exportKey = `${kind}-${level}`;
    const suspensionCapture = kind === 'suspensions' ? createSuspensionCapturePanel(level) : null;
    const target = suspensionCapture?.panel || Array.from(document.querySelectorAll('[data-export-view]'))
        .find(item => item.getAttribute('data-export-view') === exportKey);
    if (!target) {
        suspensionCapture?.host.remove();
        showModal('暂时无法保存', '当前没有可导出的统计内容。');
        return;
    }

    const exportButtons = Array.from(document.querySelectorAll('.competition-image-btn'));
    competitionImageExportBusy = true;
    exportButtons.forEach(button => {
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
    });
    target.classList.add('is-exporting');
    try {
        if (document.fonts?.ready) await document.fonts.ready;
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        const blob = await window.htmlToImage.toBlob(target, {
            cacheBust: true,
            pixelRatio: getCompetitionImagePixelRatio(kind, target),
            filter: node => !(node?.classList && node.classList.contains('capture-exclude')),
        });
        if (!blob) throw new Error('capture-blob-empty');
        const optimized = kind === 'suspensions'
            ? await compressSuspensionImageBlob(blob, getCompetitionImageBackground(target))
            : {blob, extension: 'png', compressed: false};
        downloadCompetitionBlob(optimized.blob, buildCompetitionImageFileName(kind, level, optimized.extension));
        if (optimized.compressed && typeof showUiToast === 'function') {
            showUiToast(`伤停图片已自动压缩至 ${(optimized.blob.size / 1024 / 1024).toFixed(2)} MB`, 'success');
        }
    } catch (error) {
        console.error('Failed to export competition image:', error);
        showModal(
            '生成图片失败',
            error?.message === 'suspension-image-still-too-large'
                ? '伤停图片内容过长，无法在保持可读性的同时压缩到 4MB 以下，请分级别保存或稍后重试。'
                : '统计图片生成失败，请刷新页面后重试。',
        );
    } finally {
        target.classList.remove('is-exporting');
        suspensionCapture?.host.remove();
        competitionImageExportBusy = false;
        exportButtons.forEach(button => {
            button.disabled = false;
            button.removeAttribute('aria-busy');
        });
    }
}

function renderScheduleBoard() {
    closeMatchEventSuggestions();
    if (document.getElementById('matchEventEditorModal')) closeMatchEventEditor(true);
    const container = document.getElementById('scheduleBoard');
    const groupContainer = document.getElementById('cupGroupStageBoard');
    const filters = document.getElementById('competitionScheduleFilters');
    if (!container) return;
    populateScheduleFilters();
    if (isCupCompetitionLevel()) {
        activeMobileScheduleEditMatchId = null;
        document.body.classList.remove('mobile-schedule-editor-open');
        if (filters) filters.hidden = true;
        if (groupContainer) {
            groupContainer.style.display = '';
            renderCupGroupStageBoard();
        }
        container.style.display = 'none';
        container.innerHTML = '';
        renderCompetitionDataStatus();
        return;
    }
    if (filters) filters.hidden = false;
    if (groupContainer) groupContainer.style.display = 'none';
    container.style.display = '';
    const matches = getFilteredScheduleMatches();
    if (!matches.length) {
        activeMobileScheduleEditMatchId = null;
        document.body.classList.remove('mobile-schedule-editor-open');
        container.innerHTML = currentCompetitionWorkFilter !== 'all'
            ? '<div class="no-data">当前工作筛选下没有待处理比赛。</div>'
            : renderUiState({tone: 'empty', title: '暂无赛程数据', message: '管理员可先从联赛工作台导入最新赛程文件。', compact: true});
        renderCompetitionDataStatus();
        return;
    }

    const rounds = getScheduleRoundsForCurrentLevel();
    const currentRound = getCurrentScheduleRound();
    const currentPairStart = getRoundPairStart(currentRound);
    const currentPair = buildRoundPairs(rounds).find(pair => pair.pairStart === currentPairStart) || {rounds: [currentRound].filter(Boolean)};
    const orderedMatches = sortScheduleMatches(matches);
    const includeDesktopAdmin = !isMobileViewport();
    container.innerHTML = `
        <section class="schedule-fixture-shell">
            ${renderScheduleRoundNavigator(rounds, currentRound, orderedMatches)}
            ${renderScheduleRoundPairGrid(currentPair.rounds, orderedMatches, {includeAdmin: includeDesktopAdmin})}
            ${renderMobileScheduleList(orderedMatches, currentPair.rounds)}
        </section>
    `;
    renderCompetitionDataStatus();
}

function renderSeasonArchivesBoard() {
    const container = document.getElementById('seasonArchivesBoard');
    if (!container) return;
    const rows = Array.isArray(seasonArchiveData) ? seasonArchiveData : [];
    container.innerHTML = `
        <section class="season-archives-public">
            <header class="season-archives-public-head surface-card">
                <div><span>HEIGO HISTORY</span><h2>历届赛季档案</h2><p>查看已封存赛季的三级联赛积分榜、球员榜、杯赛冠军和当届球队快照。</p></div>
                <strong>${rows.length} 个档案版本</strong>
            </header>
            ${rows.length ? `<div class="season-archives-public-list">${rows.map(item => `<button class="season-archive-public-card" type="button" onclick="showPublicSeasonArchive(${Number(item.id)})"><span>${escapeHtml(item.season_key)} · REV ${Number(item.revision_no)}</span><strong>${escapeHtml(item.title)}</strong><small>${item.revision_reason ? `修订：${escapeHtml(item.revision_reason)}` : '正式封存版本'} · ${item.confirmed_at ? new Date(item.confirmed_at).toLocaleDateString('zh-CN') : ''}</small></button>`).join('')}</div>` : renderUiState({tone: 'empty', title: '暂无历届档案', message: '赛季结束并通过完整性检查后，工作人员会在这里发布档案。', compact: true})}
        </section>`;
}

async function showPublicSeasonArchive(archiveId) {
    try {
        const data = await fetchCompetitionJson(`/api/season-archives/${archiveId}`);
        const standings = data.snapshot?.standings || [];
        const champions = data.snapshot?.cup_champions || {};
        const championLabels = {champions_cup: '冠军杯', league_cup: '联盟杯', wumingjian_cup: '无铭剑杯'};
        const levels = ['超级', '甲级', '乙级'];
        showModal(data.title, `<div class="public-archive-modal"><div class="public-archive-champions">${Object.entries(champions).map(([key, item]) => `<div><span>${escapeHtml(championLabels[key] || key)}</span><strong>${escapeHtml(item?.team_name || '未产生')}</strong></div>`).join('')}</div><div class="public-archive-levels">${levels.map(level => `<section><h4>${escapeHtml(level)}最终排名</h4><ol>${standings.filter(row => row.level === level).sort((a,b) => Number(a.rank)-Number(b.rank)).map(row => `<li><strong>${escapeHtml(row.team_name)}</strong> <span>${Number(row.points || 0)}分</span></li>`).join('')}</ol></section>`).join('')}</div><p>该版本同时保存了完整球员榜、球队、主教和队徽快照；修订版本不会覆盖原档案。</p></div>`);
    } catch (error) {
        showModal('档案加载失败', '该赛季档案暂时无法读取，请稍后重试。');
    }
}

const COMPETITION_SECTION_CONTAINERS = {
    standings: 'standingsBoard',
    schedule: 'scheduleBoard',
    playerRankings: 'playerRankingsBoard',
    rating: 'ratingBoard',
    suspensions: 'suspensionsBoard',
    archives: 'seasonArchivesBoard',
};

const COMPETITION_SECTION_LABELS = {
    standings: '积分榜',
    schedule: '赛程',
    playerRankings: '球员榜',
    rating: '排位',
    suspensions: '伤停',
    archives: '历届档案',
};

function getCompetitionSectionScope(section, level = currentCompetitionLevel) {
    if (['rating', 'archives'].includes(section)) return 'all';
    const cupConfig = CUP_COMPETITIONS[level];
    return cupConfig ? cupConfig.key : level;
}

function getCompetitionSectionCacheKey(section, level = currentCompetitionLevel) {
    return `${section}:${getCompetitionSectionScope(section, level)}`;
}

function applyCompetitionSectionPayload(section, payload) {
    if (!payload) return;
    if (section === 'schedule') {
        if (payload.schedule) scheduleData = payload.schedule;
        if (payload.cupKey) cupGroupStageData = {...cupGroupStageData, [payload.cupKey]: payload.groupStage || null};
        if (payload.qualification) wumingjianQualificationData = payload.qualification;
        return;
    }
    if (section === 'playerRankings') {
        playerRankingData = payload.playerRankings;
        return;
    }
    if (section === 'rating') {
        rankingData = payload.rankings;
        return;
    }
    if (section === 'suspensions') {
        suspensionData = payload.suspensions;
        siteNotesData = (payload.siteNotes || []).reduce((acc, note) => {
            acc[note.key] = note;
            return acc;
        }, {});
        return;
    }
    if (section === 'archives') {
        seasonArchiveData = payload.archives || [];
        return;
    }
    if (payload.standings) standingsData = payload.standings;
    if (payload.cupKey) {
        cupBracketData = {...cupBracketData, [payload.cupKey]: payload.bracket};
        cupGroupStageData = {...cupGroupStageData, [payload.cupKey]: payload.groupStage || null};
        if (payload.qualification) wumingjianQualificationData = payload.qualification;
    }
}

function invalidateCompetitionSections(sections = Object.keys(COMPETITION_SECTION_CONTAINERS)) {
    const targets = Array.isArray(sections) ? sections : [sections];
    targets.forEach(section => {
        if (section === 'standings') standingsHistoryCache.clear();
        for (const key of [...competitionLoadedSections]) {
            if (key.startsWith(`${section}:`)) competitionLoadedSections.delete(key);
        }
        for (const key of [...competitionSectionLoadPromises.keys()]) {
            if (key.startsWith(`${section}:`)) competitionSectionLoadPromises.delete(key);
        }
        for (const key of [...competitionSectionDataCache.keys()]) {
            if (key.startsWith(`${section}:`)) competitionSectionDataCache.delete(key);
        }
    });
    competitionDataLoaded = competitionLoadedSections.size > 0;
    if (typeof invalidateTeamDetailCache === 'function') invalidateTeamDetailCache();
}

function renderCompetitionSection(section) {
    if (section === 'schedule') renderScheduleBoard();
    else if (section === 'playerRankings') renderPlayerRankingsBoard();
    else if (section === 'rating') renderRankingBoard();
    else if (section === 'suspensions') renderSuspensionsBoard();
    else if (section === 'archives') renderSeasonArchivesBoard();
    else renderCompetitionPrimaryBoard();
    renderCompetitionDataStatus();
}

function renderCompetitionSectionLoading(section) {
    const containerId = section === 'standings' && isCupCompetitionLevel()
        ? 'cupBracketBoard'
        : section === 'schedule' && isCupCompetitionLevel()
            ? 'cupGroupStageBoard'
            : COMPETITION_SECTION_CONTAINERS[section];
    const container = document.getElementById(containerId);
    if (container) container.style.display = '';
    if (container) container.innerHTML = renderUiState({tone: 'loading', title: `正在读取${COMPETITION_SECTION_LABELS[section] || '数据'}`, message: '只加载当前模块所需数据。', compact: true});
}

function renderCompetitionSectionError(section, failureType = 'request') {
    const containerId = section === 'standings' && isCupCompetitionLevel()
        ? 'cupBracketBoard'
        : section === 'schedule' && isCupCompetitionLevel()
            ? 'cupGroupStageBoard'
            : COMPETITION_SECTION_CONTAINERS[section];
    const container = document.getElementById(containerId);
    if (!container) return;
    const label = COMPETITION_SECTION_LABELS[section] || '数据';
    const renderFailure = failureType === 'render';
    container.innerHTML = renderUiState({
        tone: 'danger',
        title: `${label}${renderFailure ? '显示' : '加载'}失败`,
        message: renderFailure
            ? '数据已经读取，但页面显示出现异常；其他统计模块不受影响。'
            : '其他统计模块不受影响，可稍后单独重试。',
        actionLabel: renderFailure ? '刷新页面' : '重新读取',
        actionOnclick: renderFailure ? 'window.location.reload()' : `loadCompetitionSection('${section}', {force:true})`,
        compact: true,
    });
}

function applyAndRenderCompetitionSectionPayload(section, cacheKey, payload) {
    if (cacheKey !== getCompetitionSectionCacheKey(currentCompetitionSubtab)) return true;
    try {
        applyCompetitionSectionPayload(section, payload);
        renderCompetitionSection(section);
        return true;
    } catch (error) {
        console.error(`Failed to render competition section ${section}:`, error);
        renderCompetitionSectionError(section, 'render');
        return false;
    }
}

async function fetchCompetitionJson(url, options = {}) {
    const response = await fetchWithTimeout(url);
    if (!response.ok && !options.optional) throw new Error(`${url}: HTTP ${response.status}`);
    if (!response.ok) return null;
    return response.json();
}

async function requestCompetitionSection(section, level = currentCompetitionLevel) {
    const cupConfig = CUP_COMPETITIONS[level] || null;
    if (section === 'schedule') {
        if (cupConfig) {
            if (cupConfig.key === 'wumingjian_cup') {
                return {
                    cupKey: cupConfig.key,
                    groupStage: null,
                    qualification: await fetchCompetitionJson('/api/cups/wumingjian_cup/qualification'),
                };
            }
            const groupStage = cupConfig.groupCount
                ? await fetchCompetitionJson(`/api/cups/${cupConfig.key}/groups`, {optional: true})
                : null;
            return {cupKey: cupConfig.key, groupStage};
        }
        return {schedule: await fetchCompetitionJson(`/api/matches?level=${encodeURIComponent(level)}`)};
    }
    if (section === 'playerRankings') {
        return {playerRankings: await fetchCompetitionJson(`/api/player-rankings?level=${encodeURIComponent(level)}`)};
    }
    if (section === 'rating') {
        return {rankings: await fetchCompetitionJson('/api/rankings')};
    }
    if (section === 'suspensions') {
        const [suspensions, siteNotes] = await Promise.all([
            fetchCompetitionJson(`/api/suspensions?level=${encodeURIComponent(level)}`),
            fetchCompetitionJson('/api/site-notes'),
        ]);
        return {suspensions, siteNotes};
    }
    if (section === 'archives') {
        return {archives: await fetchCompetitionJson('/api/season-archives')};
    }
    if (cupConfig) {
        const [bracket, groupStage, qualification] = await Promise.all([
            fetchCompetitionJson(`/api/cups/${cupConfig.key}/bracket`),
            cupConfig.groupCount
                ? fetchCompetitionJson(`/api/cups/${cupConfig.key}/groups`, {optional: true})
                : Promise.resolve(null),
            cupConfig.key === 'wumingjian_cup'
                ? fetchCompetitionJson('/api/cups/wumingjian_cup/qualification')
                : Promise.resolve(null),
        ]);
        return {cupKey: cupConfig.key, bracket, groupStage, qualification};
    }
    return {standings: await fetchCompetitionJson(`/api/standings?level=${encodeURIComponent(level)}`)};
}

async function loadCompetitionSection(section = currentCompetitionSubtab, options = {}) {
    const normalizedSection = Object.hasOwn(COMPETITION_SECTION_CONTAINERS, section) ? section : 'standings';
    const requestedLevel = currentCompetitionLevel;
    const cacheKey = getCompetitionSectionCacheKey(normalizedSection, requestedLevel);
    if (options.force === true) invalidateCompetitionSections(normalizedSection);
    if (competitionLoadedSections.has(cacheKey)) {
        return applyAndRenderCompetitionSectionPayload(
            normalizedSection,
            cacheKey,
            competitionSectionDataCache.get(cacheKey),
        );
    }
    if (competitionSectionLoadPromises.has(cacheKey)) return competitionSectionLoadPromises.get(cacheKey);
    renderCompetitionSectionLoading(normalizedSection);
    const promise = (async () => {
        try {
            let payload;
            try {
                payload = await requestCompetitionSection(normalizedSection, requestedLevel);
            } catch (error) {
                console.error(`Failed to request competition section ${normalizedSection}:`, error);
                if (cacheKey === getCompetitionSectionCacheKey(currentCompetitionSubtab)) renderCompetitionSectionError(normalizedSection, 'request');
                return false;
            }
            competitionSectionDataCache.set(cacheKey, payload);
            competitionLoadedSections.add(cacheKey);
            competitionDataLoaded = true;
            return applyAndRenderCompetitionSectionPayload(normalizedSection, cacheKey, payload);
        } finally {
            competitionSectionLoadPromises.delete(cacheKey);
        }
    })();
    competitionSectionLoadPromises.set(cacheKey, promise);
    return promise;
}

async function loadCompetitionData(options = {}) {
    renderCompetitionAdminActions();
    if (typeof loadDataStatus === 'function') loadDataStatus({force: options.force === true});
    if (hasLeagueCompetitionWorkAccess()) loadCompetitionWorkSummary({force: options.force === true});
    const loaded = await loadCompetitionSection(currentCompetitionSubtab, options);
    renderCompetitionAdminActions();
    renderCompetitionWorkPanel();
    return loaded;
}

async function refreshPlayerRankingsData() {
    try {
        const level = currentCompetitionLevel;
        const response = await fetchWithTimeout(`/api/player-rankings?level=${encodeURIComponent(level)}`);
        if (!response.ok) return false;
        const payload = {playerRankings: await response.json()};
        const cacheKey = getCompetitionSectionCacheKey('playerRankings', level);
        competitionSectionDataCache.set(cacheKey, payload);
        competitionLoadedSections.add(cacheKey);
        applyCompetitionSectionPayload('playerRankings', payload);
        if (currentCompetitionSubtab === 'playerRankings') {
            renderPlayerRankingsBoard();
        }
        return true;
    } catch (error) {
        return false;
    }
}

function resetScheduleFilters() {
    const levelSelect = document.getElementById('scheduleLevelSelect');
    const roundSelect = document.getElementById('scheduleRoundSelect');
    if (roundSelect) roundSelect.value = '';
    renderScheduleBoard();
}

async function importLatestSchedule() {
    if (!canManageSchedule) return;
    const confirmed = await showConfirmDialog({title: '导入最新赛程', message: '将读取 imports/schedules/ 下最新的赛程 Excel，同一场已录入的比分会保留。', confirmLabel: '开始导入'});
    if (!confirmed) return;
    const result = await workJsonRequest('/api/admin/matches/import', {method: 'POST'});
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('赛程导入失败', escapeHtml(data.detail || data.message || '导入失败'));
        return;
    }
    invalidateCompetitionSections();
    await loadCompetitionData({force: true});
    const warningHtml = (data.warnings || []).slice(0, 10).map(item => `<li>${escapeHtml(item)}</li>`).join('');
    showModal('赛程导入完成', `
        <div class="maintenance-note">${escapeHtml(data.message || '')}</div>
        <div class="maintenance-note" style="margin-top:8px;"><strong>来源：</strong><code>${escapeHtml(data.source_file || '')}</code></div>
        ${warningHtml ? `<div class="maintenance-note" style="margin-top:8px;"><strong>未匹配球队：</strong><ul style="margin:6px 0 0 18px;">${warningHtml}</ul></div>` : ''}
    `);
}

function selectScheduleImportFile() {
    if (!canManageSchedule) return;
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.xlsx,.xlsm';
    input.addEventListener('change', () => {
        const file = input.files?.[0];
        if (file) uploadScheduleImportFile(file);
    }, {once: true});
    input.click();
}

async function uploadScheduleImportFile(file) {
    if (!canManageSchedule || !file) return;
    const confirmed = await showConfirmDialog({title: '上传并更新赛程', message: `文件：${file.name}\n同一场比赛已录入的比分和状态会保留。`, confirmLabel: '上传并更新'});
    if (!confirmed) return;
    const formData = new FormData();
    formData.append('file', file, file.name);
    const result = await workJsonRequest('/api/admin/matches/import/upload', {method: 'POST', body: formData});
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('赛程更新失败', escapeHtml(data.detail || data.message || '上传或导入失败'));
        return;
    }
    invalidateCompetitionSections();
    await loadCompetitionData({force: true});
    const warningHtml = (data.warnings || []).slice(0, 10).map(item => `<li>${escapeHtml(item)}</li>`).join('');
    showModal('赛程更新完成', `
        <div class="maintenance-note">${escapeHtml(data.message || '')}</div>
        <div class="maintenance-note" style="margin-top:8px;"><strong>来源：</strong><code>${escapeHtml(data.source_file || '')}</code></div>
        ${warningHtml ? `<div class="maintenance-note" style="margin-top:8px;"><strong>未匹配球队：</strong><ul style="margin:6px 0 0 18px;">${warningHtml}</ul></div>` : ''}
    `);
}

function readMatchScorePayload(matchId, eventOverride = null) {
    const homeInput = document.getElementById(`match-home-${matchId}`);
    const awayInput = document.getElementById(`match-away-${matchId}`);
    const statusSelect = document.getElementById(`match-status-${matchId}`);
    const match = findScheduleMatchById(matchId);
    let selectedStatus = String(statusSelect?.value || match?.status || '').trim();
    const homeRaw = String(homeInput ? homeInput.value : (match?.home_score ?? '')).trim();
    const awayRaw = String(awayInput ? awayInput.value : (match?.away_score ?? '')).trim();
    if (selectedStatus === 'scheduled' && (homeRaw !== '' || awayRaw !== '')) {
        selectedStatus = 'played';
        if (statusSelect) statusSelect.value = 'played';
    }
    if (selectedStatus === 'scheduled') {
        if (homeInput) homeInput.value = '';
        if (awayInput) awayInput.value = '';
        return {
            match_id: Number(matchId),
            home_score: null,
            away_score: null,
            status: 'scheduled',
            events: [],
        };
    }
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
    if (homeRaw === '' || awayRaw === '') throw new Error('正常比赛需要填写完整的双方比分。');
    const homeScore = Number(homeRaw);
    const awayScore = Number(awayRaw);
    if (
        (homeScore !== null && (!Number.isInteger(homeScore) || homeScore < 0)) ||
        (awayScore !== null && (!Number.isInteger(awayScore) || awayScore < 0))
    ) {
        throw new Error('比分必须是 0 或正整数。');
    }
    const events = Array.isArray(eventOverride) ? eventOverride : readMatchEventPayload(matchId, match);
    return {
        match_id: Number(matchId),
        home_score: homeScore,
        away_score: awayScore,
        status: 'played',
        events,
    };
}

function readMatchEventPayload(matchId, match) {
    const rows = Array.from(document.querySelectorAll(`#match-events-${matchId} [data-match-event-row]`));
    if (!rows.length) return (match?.events || []).map(event => ({
        team_name: String(event.team_name || ''),
        player_uid: event.player_uid === null || event.player_uid === undefined ? null : Number(event.player_uid || 0),
        player_name: String(event.player_name || ''),
        event_type: String(event.event_type || ''),
        quantity: Number(event.quantity || 1),
    }));
    return rows.map(row => {
        const teamName = String(row.querySelector('.match-event-team')?.value || '').trim();
        const playerInput = String(row.querySelector('.match-event-player')?.value || '').trim();
        const eventType = String(row.querySelector('.match-event-type')?.value || '').trim();
        const quantity = Number(row.querySelector('.match-event-quantity')?.value || 0);
        const isOwnGoal = eventType === 'own_goal';
        if (!isOwnGoal && !playerInput && (!quantity || quantity === 1)) return null;
        const player = isOwnGoal ? null : findMatchEventPlayer(match, teamName, playerInput);
        if (!teamName) throw new Error('请选择事件球队。');
        if (!isOwnGoal && !player) throw new Error(`未找到球员：${playerInput}`);
        if (!['goal', 'own_goal', 'assist', 'mvp'].includes(eventType)) throw new Error('请选择进球、乌龙球、助攻或最佳。');
        if (eventType !== 'mvp' && (!Number.isInteger(quantity) || quantity <= 0)) throw new Error('事件数量必须是正整数。');
        const validTeam = getMatchTeamOptions(match).some(team => team.team_name === teamName);
        if (!validTeam) throw new Error('事件球队必须属于本场比赛。');
        return {
            team_name: teamName,
            player_uid: isOwnGoal ? null : Number(player.uid || 0),
            player_name: isOwnGoal ? '乌龙球' : (player.name || ''),
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
    if (!canManageCurrentCompetitionSchedule()) return;
    const numericMatchId = Number(matchId || 0);
    if (!numericMatchId) return;
    scheduleMatchSaveVersions.set(numericMatchId, Number(scheduleMatchSaveVersions.get(numericMatchId) || 0) + 1);
    setScheduleMatchSaveState(numericMatchId, 'dirty');
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
    if (!canManageCurrentCompetitionSchedule()) return;
    const numericMatchId = Number(matchId || 0);
    if (!numericMatchId) return;
    if (scheduleMatchSaveInFlight.has(numericMatchId)) {
        scheduleMatchSaveQueued.add(numericMatchId);
        return;
    }
    let payload;
    try {
        payload = readMatchScorePayload(numericMatchId);
    } catch (error) {
        setScheduleMatchSaveState(numericMatchId, 'error', error.message || '数据不完整，点击重试');
        return;
    }
    const saveVersion = Number(scheduleMatchSaveVersions.get(numericMatchId) || 0);
    const isCurrentAttempt = () => Number(scheduleMatchSaveVersions.get(numericMatchId) || 0) === saveVersion;
    scheduleMatchSaveInFlight.add(numericMatchId);
    setScheduleMatchSaveState(numericMatchId, 'saving');
    try {
        const result = await workJsonRequest('/api/admin/matches/batch', {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({matches: [payload]}),
        });
        if (!result) {
            if (isCurrentAttempt()) setScheduleMatchSaveState(numericMatchId, 'error');
            return;
        }
        const {response, data} = result;
        if (!response.ok || !data.success) {
            if (isCurrentAttempt()) setScheduleMatchSaveState(numericMatchId, 'error', data.detail || data.message || '保存失败，点击重试');
            return;
        }
        if (!isCurrentAttempt()) {
            scheduleMatchSaveQueued.add(numericMatchId);
            return;
        }
        applyMatchPayloadLocally(payload);
        setScheduleMatchSaveState(numericMatchId, 'saved');
        invalidateCompetitionSections(['standings', 'playerRankings', 'suspensions']);
        await refreshPlayerRankingsData();
        await refreshCompetitionWorkSummary({renderBoards: false});
        renderCompetitionDataStatus();
    } catch (error) {
        console.error('赛程自动保存失败:', error);
        if (isCurrentAttempt()) setScheduleMatchSaveState(numericMatchId, 'error');
    } finally {
        scheduleMatchSaveInFlight.delete(numericMatchId);
        if (scheduleMatchSaveQueued.has(numericMatchId) || !isCurrentAttempt()) {
            scheduleMatchSaveQueued.delete(numericMatchId);
            window.setTimeout(() => saveScheduleMatchQuietly(numericMatchId), 0);
        }
    }
}

async function saveCurrentMatchProgress(matchIds) {
    if (!canManageCurrentCompetitionSchedule()) return;
    let matches = [];
    try {
        matches = (matchIds || []).map(readMatchScorePayload);
    } catch (error) {
        showModal('保存失败', escapeHtml(error.message || '比分填写不完整'));
        return;
    }
    if (!matches.length) return;
    matches.forEach(item => setScheduleMatchSaveState(item.match_id, 'saving'));
    let result;
    try {
        result = await workJsonRequest('/api/admin/matches/batch', {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({matches}),
        });
    } catch (error) {
        matches.forEach(item => setScheduleMatchSaveState(item.match_id, 'error'));
        showModal('保存失败', '网络连接失败，请稍后重试。');
        return;
    }
    if (!result) {
        matches.forEach(item => setScheduleMatchSaveState(item.match_id, 'error'));
        return;
    }
    const {response, data} = result;
    if (!response.ok || !data.success) {
        matches.forEach(item => setScheduleMatchSaveState(item.match_id, 'error', data.detail || data.message || '保存失败，点击重试'));
        showModal('保存失败', escapeHtml(data.detail || data.message || '保存比分失败'));
        return;
    }
    matches.forEach(item => setScheduleMatchSaveState(item.match_id, 'saved'));
    invalidateCompetitionSections();
    await loadCompetitionData({force: true});
    await refreshCompetitionWorkSummary();
}

async function saveMatchResult(matchId) {
    return saveCurrentMatchProgress([matchId]);
}

async function resetMatchResult(matchId) {
    if (!canManageCurrentCompetitionSchedule()) return;
    const confirmed = await showConfirmDialog({title: '重置比赛结果', message: '这场比赛将恢复为未赛，双方比分会被清空。', confirmLabel: '确认重置', danger: true});
    if (!confirmed) return;
    const result = await workJsonRequest(`/api/admin/matches/${matchId}`, {
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
    setScheduleMatchSaveState(matchId, 'saved', '已重置为未赛');
    invalidateCompetitionSections();
    await loadCompetitionData({force: true});
    await refreshCompetitionWorkSummary();
}

async function initializeCupBracket() {
    if (!canManageSchedule) return;
    const cupConfig = getCurrentCupConfig();
    if (!cupConfig) return;
    const confirmed = await showConfirmDialog({title: `重新初始化${currentCompetitionLevel}`, message: '现有球队、比分和晋级结果将被清空，赛制槽位会重新生成。', confirmLabel: '确认重新初始化', danger: true});
    if (!confirmed) return;
    const button = document.getElementById('initializeCupBracketButton');
    const originalLabel = button?.textContent || cupConfig.initializeLabel;
    if (button) {
        button.disabled = true;
        button.textContent = '初始化中...';
    }
    try {
        const result = await workJsonRequest(`/api/admin/cups/${cupConfig.key}/initialize?reset=true`, {method: 'POST'});
        if (!result) return;
        const {response, data} = result;
        if (!response.ok || !data.success) {
            showModal('初始化失败', escapeHtml(data.detail || data.message || '初始化杯赛失败'));
            return;
        }
        invalidateCompetitionSections();
        await loadCompetitionData({force: true});
        showSuccessToast(data.message || `${currentCompetitionLevel}已重新初始化`);
    } catch (error) {
        showModal('初始化失败', '网络连接失败，请稍后重试。');
    } finally {
        if (button?.isConnected) {
            button.disabled = false;
            button.textContent = originalLabel;
        }
    }
}

async function saveCupMatchTeams(matchId) {
    if (!canManageSchedule) return;
    const homeTeamId = Number(document.getElementById(`cup-home-team-${matchId}`)?.value || 0) || null;
    const awayTeamId = Number(document.getElementById(`cup-away-team-${matchId}`)?.value || 0) || null;
    const result = await workJsonRequest(`/api/admin/cups/matches/${matchId}/teams`, {
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
    invalidateCompetitionSections();
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
        showCupTieDecision(match, payload);
        return;
    }
    await submitCupMatchResult(matchId, payload);
}

async function submitCupMatchResult(matchId, payload) {
    const result = await workJsonRequest(`/api/admin/cups/matches/${matchId}/result`, {
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
    invalidateCompetitionSections();
    await loadCompetitionData({force: true});
}
