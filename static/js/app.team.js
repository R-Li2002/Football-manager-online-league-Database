var fetchWithTimeout = globalThis.fetchWithTimeout || ((...args) => globalThis.fetch(...args));

let currentTeamDetailName = '';
let teamDetailLoadSequence = 0;
let teamDetailAbortController = null;
let currentTeamDetailData = null;
let teamRosterExportBusy = false;
let teamLineupExportBusy = false;
let teamPowerSummariesPromise = null;
let teamCenterCoachAuthReady = false;
let teamCenterCoachAuthPromise = null;
let teamRosterCopyToastTimer = null;
let currentTeamJourneyView = 'league';
let currentTeamPlayerLeaderMetric = 'goals';
const teamDetailCache = new Map();
const TEAM_DETAIL_CACHE_TTL_MS = 60 * 1000;
const TEAM_ROSTER_VIEW_MODES = new Set(['compact', 'detail', 'cards']);
const teamCenterExpandedLevels = new Set();
let teamCenterExpandedInitialized = false;
let teamCenterSearchQuery = '';
let teamCenterSearchActiveIndex = -1;
let currentMatchPreviewData = null;
let currentMatchPreviewTab = 'summary';
let matchPreviewAbortController = null;
let matchPreviewReturnFocus = null;
let matchPreviewHistoryActive = false;
let currentMatchPreviewRequest = null;
const matchPreviewCache = new Map();
const MATCH_PREVIEW_CACHE_TTL_MS = 90 * 1000;

function getCachedTeamDetail(teamName) {
    const cached = teamDetailCache.get(teamName);
    if (!cached) return null;
    if (Date.now() - Number(cached.cachedAt || 0) > TEAM_DETAIL_CACHE_TTL_MS) {
        teamDetailCache.delete(teamName);
        return null;
    }
    return cached.data || null;
}

function setCachedTeamDetail(teamName, data) {
    teamDetailCache.set(teamName, {data, cachedAt: Date.now()});
    return data;
}

function invalidateTeamDetailCache(teamName = '') {
    const normalizedName = String(teamName || '').trim();
    if (normalizedName) teamDetailCache.delete(normalizedName);
    else teamDetailCache.clear();
}

function teamDetailSafeNumber(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
}

function teamDetailFormatNumber(value, digits = 0) {
    return teamDetailSafeNumber(value).toLocaleString('zh-CN', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
    });
}

function teamDetailHandlerArg(value) {
    return encodeURIComponent(String(value || '')).replace(/'/g, '%27');
}

function teamDetailLevelBadge(level, options = {}) {
    return options.compact ? renderLeagueLevelSignature(level, {compact: true}) : renderLeagueLevelBadge(level);
}

async function ensureTeamCenterCoachAuth(options = {}) {
    if (options.force === true) {
        teamCenterCoachAuthReady = false;
        teamCenterCoachAuthPromise = null;
    }
    if (teamCenterCoachAuthReady) return currentCoachAccount;
    if (!teamCenterCoachAuthPromise) {
        teamCenterCoachAuthPromise = (typeof syncCoachAuthStatus === 'function'
            ? syncCoachAuthStatus()
            : Promise.resolve(currentCoachAccount || {authenticated: false})
        ).then(account => {
            teamCenterCoachAuthReady = true;
            return account;
        }).finally(() => {
            teamCenterCoachAuthPromise = null;
        });
    }
    return teamCenterCoachAuthPromise;
}

async function openCoachLinkedTeam(account = currentCoachAccount) {
    if (account?.authenticated && (account.must_change_password || !account.qq_number)) {
        await ensureAppModule('coaches');
        beginCoachSecuritySetup();
        return;
    }
    const linkedTeam = (teams || []).find(team => (
        (Number(account?.team_id) > 0 && Number(team.id) === Number(account.team_id))
        || (account?.team_name && team.name === account.team_name)
    ));
    if (!linkedTeam) {
        showModal('未关联球队', '当前教练账号没有关联到有效球队，请联系管理员检查账号资料。');
        return;
    }
    await openTeamDetail(linkedTeam.name, {historyMode: 'replace', smooth: false});
}

async function openTeamCenterCoachAccess() {
    const account = await ensureTeamCenterCoachAuth({force: true});
    if (account?.authenticated) {
        if (account.must_change_password || !account.qq_number) {
            await ensureAppModule('coaches');
            beginCoachSecuritySetup();
            return;
        }
        await openCoachLinkedTeam(account);
        return;
    }
    if (typeof showCoachLoginPanel === 'function') {
        showCoachLoginPanel({context: 'team-center'});
    }
}

function teamCenterCoachAccessMarkup() {
    const authenticated = Boolean(currentCoachAccount?.authenticated);
    const label = authenticated ? '进入我的球队' : '教练登录';
    const detail = authenticated
        ? escapeHtml(currentCoachAccount.nickname || currentCoachAccount.username || '已登录教练')
        : '登录后直达关联球队';
    return `<button class="team-center-coach-access" type="button" onclick="openTeamCenterCoachAccess()"><span>${label}</span><small>${detail}</small><b aria-hidden="true">${uiIconSvg('arrow-right')}</b></button>`;
}

function teamDetailPositionGroup(position) {
    const normalized = String(position || '').toUpperCase().replace(/\s+/g, '');
    if (normalized.includes('GK')) return 'gk';
    if (/(ST|(^|\/)S($|\/))/.test(normalized)) return 'att';
    if (normalized.includes('AM')) return 'att';
    if (/(DM|(^|\/)M)/.test(normalized)) return 'mid';
    if (/(WB|(^|\/)D)/.test(normalized)) return 'def';
    return 'mid';
}

function teamDetailBuildSpine(players, powerByUid) {
    const groups = {gk: [], def: [], mid: [], att: []};
    players.forEach(player => {
        const power = powerByUid.get(Number(player.uid)) || {};
        groups[teamDetailPositionGroup(player.position)].push({...player, power});
    });
    Object.values(groups).forEach(items => items.sort((a, b) => (
        teamDetailSafeNumber(b.power.heigo_power, b.ca) - teamDetailSafeNumber(a.power.heigo_power, a.ca)
    )));
    return groups;
}

function teamDetailGetMatches(payload, team) {
    const matches = Array.isArray(payload?.matches) ? payload.matches : [];
    return matches.filter(match => (
        Number(match.home_team_id) === Number(team.id)
        || Number(match.away_team_id) === Number(team.id)
        || match.home_team_name === team.name
        || match.away_team_name === team.name
    ));
}

function teamDetailHasScore(value) {
    return value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
}

function teamDetailGetLeagueInfoNumber(key, fallback) {
    const record = (leagueInfo || []).find(item => item.key === key);
    const rawValue = record?.value ?? record?.float_value ?? record?.int_value;
    const value = Number.parseFloat(rawValue);
    return Number.isFinite(value) ? value : fallback;
}

function teamDetailGetWageCap(team) {
    const override = Number.parseFloat(team?.wage_cap);
    if (Number.isFinite(override) && override > 0) return override;
    const defaults = {'超级': 9.4, '甲级': 8.9, '乙级': 8.6};
    const keys = {'超级': '超级级工资帽', '甲级': '甲级级工资帽', '乙级': '乙级级工资帽'};
    const base = teamDetailGetLeagueInfoNumber(keys[team.level], defaults[team.level] || 9.4);
    const compactNotes = String(team.notes || '').replace(/\s+/g, '');
    const match = compactNotes.match(/([+-]?\d+(?:\.\d+)?)\s*[mMＭ](?:工资帽)?/i);
    const extra = match && (compactNotes.includes('工资帽') || compactNotes.includes('+')) ? Number.parseFloat(match[1]) : 0;
    return base + (Number.isFinite(extra) && extra > 0 ? extra : 0);
}

function teamDetailMatchMeta(match, team) {
    const isHome = Number(match.home_team_id) === Number(team.id) || match.home_team_name === team.name;
    const opponent = isHome ? match.away_team_name : match.home_team_name;
    const played = teamDetailHasScore(match.home_score) && teamDetailHasScore(match.away_score);
    const ownScore = isHome ? match.home_score : match.away_score;
    const opponentScore = isHome ? match.away_score : match.home_score;
    return {isHome, opponent, played, ownScore, opponentScore};
}

function teamDetailGroupMatchSeries(matches, team, direction = 'asc') {
    const sorted = [...matches].sort((a, b) => teamDetailSafeNumber(a.round_no) - teamDetailSafeNumber(b.round_no));
    const groups = [];
    sorted.forEach(match => {
        const meta = teamDetailMatchMeta(match, team);
        const previous = groups[groups.length - 1];
        const previousMatch = previous?.[previous.length - 1];
        const previousMeta = previousMatch ? teamDetailMatchMeta(previousMatch, team) : null;
        const consecutive = previousMatch && teamDetailSafeNumber(match.round_no) === teamDetailSafeNumber(previousMatch.round_no) + 1;
        if (previous && previous.length < 2 && consecutive && previousMeta?.opponent === meta.opponent) {
            previous.push(match);
        } else {
            groups.push([match]);
        }
    });
    return direction === 'desc' ? groups.reverse() : groups;
}

function teamDetailMatchCard(match, team, compact = false) {
    if (!match) return '<div class="team-detail-muted">暂无比赛数据</div>';
    const isHome = Number(match.home_team_id) === Number(team.id) || match.home_team_name === team.name;
    const opponent = isHome ? match.away_team_name : match.home_team_name;
    const played = teamDetailHasScore(match.home_score) && teamDetailHasScore(match.away_score);
    const ownScore = isHome ? match.home_score : match.away_score;
    const opponentScore = isHome ? match.away_score : match.home_score;
    const resultClass = !played ? 'is-upcoming' : ownScore > opponentScore ? 'is-win' : ownScore < opponentScore ? 'is-loss' : 'is-draw';
    const resultText = played ? `${ownScore} : ${opponentScore}` : '';
    const tag = played ? 'article' : 'button';
    const interaction = played ? '' : ` type="button" onclick="openMatchPreview('league', ${Number(match.id)}, this)" aria-label="查看${escapeHtml(opponent || '')}赛前情报"`;
    return `<${tag} class="team-match-card ${resultClass} ${compact ? 'is-compact' : ''}"${interaction}>
        <div class="team-match-round"><span>${escapeHtml(match.level || '')}</span> 第 ${teamDetailSafeNumber(match.round_no)} 轮</div>
        <div class="team-match-opponent"><small class="team-match-venue ${isHome ? 'is-home' : 'is-away'}">${isHome ? '主场' : '客场'}</small><strong>${escapeHtml(opponent || '-')}</strong></div>
        ${resultText ? `<div class="team-match-score">${resultText}</div>` : ''}
        ${played ? '' : '<span class="team-match-preview-hint">赛前情报 <b aria-hidden="true">→</b></span>'}
    </${tag}>`;
}

function teamDetailMatchSeriesCard(series, team, compact = false) {
    if (!Array.isArray(series) || !series.length) return '<div class="team-detail-muted">暂无比赛数据</div>';
    if (series.length === 1) return teamDetailMatchCard(series[0], team, compact);
    const metas = series.map(match => ({match, ...teamDetailMatchMeta(match, team)}));
    const opponent = metas[0].opponent;
    const rounds = metas.map(item => teamDetailSafeNumber(item.match.round_no));
    const hasPreviewableLeg = metas.some(item => !item.played);
    return `<article class="team-match-series-card ${hasPreviewableLeg ? 'has-previewable-legs' : ''} ${compact ? 'is-compact' : ''}">
        <div class="team-match-series-head"><div><span>${escapeHtml(series[0].level || '')}</span><small>第 ${Math.min(...rounds)}–${Math.max(...rounds)} 轮</small></div><strong>${escapeHtml(opponent || '-')}</strong></div>
        <div class="team-match-series-legs">${metas.map(item => {
            const resultClass = !item.played ? 'is-upcoming' : item.ownScore > item.opponentScore ? 'is-win' : item.ownScore < item.opponentScore ? 'is-loss' : 'is-draw';
            const legTag = item.played ? 'div' : 'button';
            const interaction = item.played
                ? ''
                : ` type="button" onclick="openMatchPreview('league', ${Number(item.match.id)}, this)" aria-label="查看第${teamDetailSafeNumber(item.match.round_no)}轮对阵${escapeHtml(opponent || '')}的赛前情报"`;
            return `<${legTag} class="team-match-series-leg ${resultClass}"${interaction}><span class="team-match-leg-meta"><small>第 ${teamDetailSafeNumber(item.match.round_no)} 轮</small><b class="team-match-venue ${item.isHome ? 'is-home' : 'is-away'}">${item.isHome ? '主场' : '客场'}</b></span>${item.played ? `<strong>${item.ownScore} : ${item.opponentScore}</strong>` : '<strong class="team-match-leg-preview">前瞻 <b aria-hidden="true">→</b></strong>'}</${legTag}>`;
        }).join('')}</div>
    </article>`;
}

function teamDetailCupThemeClass(item) {
    return ['champion', 'league', 'wumingjian'].includes(item?.theme) ? `is-${item.theme}` : '';
}

function teamDetailCupFixtureCard(match) {
    const roundLabel = match.phase === 'knockout'
        ? match.stage_label
        : `第 ${teamDetailSafeNumber(match.round_no)} 轮`;
    return `<button class="team-cup-next-row" type="button" onclick="openMatchPreview('cup', ${Number(match.id)}, this)" aria-label="查看${escapeHtml(match.opponent_team_name || '')}杯赛前瞻"><span><small>${escapeHtml(roundLabel || '杯赛')}</small><b class="team-match-venue ${match.is_home ? 'is-home' : 'is-away'}">${match.is_home ? '主场' : '客场'}</b></span><strong>${escapeHtml(match.opponent_team_name || '待定')}</strong><i aria-hidden="true">→</i></button>`;
}

function teamDetailCupOpponentProgress(item) {
    const pending = (item.opponents || []).filter(opponent => teamDetailSafeNumber(opponent.remaining_legs) > 0);
    const completedCount = (item.opponents || []).length - pending.length;
    return `<div class="team-cup-opponent-list">
        ${pending.map(opponent => `<div class="team-cup-opponent-row"><strong>${escapeHtml(opponent.team_name)}</strong><span class="team-cup-leg-progress"><b>${teamDetailSafeNumber(opponent.played_legs)}</b>/2</span></div>`).join('')}
        ${completedCount > 0 ? `<div class="team-cup-completed">已完成 ${completedCount} 个对手的主客两回合</div>` : ''}
    </div>`;
}

function teamDetailCupJourney(item) {
    if (!item) return '<div class="team-detail-empty-inline">暂无杯赛征程数据。</div>';
    const groupMeta = item.phase === 'group'
        ? `<span>${escapeHtml(item.group_name || '-')}组</span><span>第 ${teamDetailSafeNumber(item.rank, '-')} 名</span><span>${teamDetailSafeNumber(item.points)} 分</span><span>净胜球 ${teamDetailSafeNumber(item.goal_difference) > 0 ? '+' : ''}${teamDetailSafeNumber(item.goal_difference)}</span>`
        : `<span>${escapeHtml(item.qualification_label || '淘汰赛')}</span>`;
    const statusPrefix = item.qualification_provisional ? '当前' : '最终';
    const nextFixtures = Array.isArray(item.next_matches) ? item.next_matches : [];
    const knockoutNext = nextFixtures.length || item.phase === 'knockout'
        ? `<div class="team-cup-next"><div class="team-cup-section-title"><strong>下一场</strong><small>${item.phase === 'group' ? '小组赛前瞻' : '当前淘汰赛阶段'}</small></div>${nextFixtures.map(match => teamDetailCupFixtureCard({...match, phase: item.phase})).join('') || '<div class="team-detail-empty-inline">当前没有待进行的杯赛。</div>'}</div>`
        : '';
    return `<div class="team-cup-outlook ${teamDetailCupThemeClass(item)}">
        <div class="team-cup-summary">${groupMeta}</div>
        <div class="team-cup-qualification"><small>${statusPrefix}去向</small><strong>${escapeHtml(item.qualification_label || '待定')}</strong>${item.qualification_context ? `<span>${escapeHtml(item.qualification_context)}</span>` : ''}</div>
        <div class="team-cup-remaining"><strong>剩余 ${teamDetailSafeNumber(item.remaining_opponent_count)} 个对手</strong><span>${teamDetailSafeNumber(item.remaining_match_count)} 场比赛</span></div>
        ${teamDetailCupOpponentProgress(item)}
        ${knockoutNext}
    </div>`;
}

function teamDetailJourneyPanel(team, leagueSeries, cupPayload) {
    const cups = Array.isArray(cupPayload?.competitions) ? cupPayload.competitions : [];
    const availableViews = new Set(['league', ...cups.map(item => item.competition)]);
    if (!availableViews.has(currentTeamJourneyView)) currentTeamJourneyView = 'league';
    const activeCup = cups.find(item => item.competition === currentTeamJourneyView);
    const tabs = cups.length ? `<div class="team-journey-tabs" role="tablist" aria-label="赛事征程切换">
        <button class="team-journey-tab ${currentTeamJourneyView === 'league' ? 'active' : ''}" type="button" onclick="setTeamJourneyView('league')">联赛 <small>${leagueSeries.reduce((sum, series) => sum + series.length, 0)}场</small></button>
        ${cups.map(item => `<button class="team-journey-tab ${currentTeamJourneyView === item.competition ? 'active' : ''}" type="button" onclick="setTeamJourneyView('${escapeHtml(item.competition)}')">${escapeHtml(item.title)} <small>${teamDetailSafeNumber(item.remaining_match_count)}场</small></button>`).join('')}
    </div>` : '';
    const content = activeCup
        ? teamDetailCupJourney(activeCup)
        : `<div class="team-next-series-list">${leagueSeries.map(series => teamDetailMatchSeriesCard(series, team, true)).join('') || '<div class="team-detail-empty-inline">当前导入赛程中暂无该队后续比赛。</div>'}</div>`;
    const action = activeCup
        ? `<button class="team-panel-link" type="button" onclick="openTeamCupJourney('${escapeHtml(activeCup.title)}', '${escapeHtml(activeCup.phase)}')">查看杯赛 →</button>`
        : `<button class="team-panel-link" type="button" onclick="openTeamSchedule('${escapeHtml(team.level)}')">完整赛程 →</button>`;
    return `<section class="team-panel team-next-panel team-journey-panel surface-card"><div class="team-panel-header"><div><span class="panel-kicker">Competition Journey</span><h2>赛事征程</h2></div>${action}</div>${tabs}${content}</section>`;
}

function setTeamJourneyView(view) {
    currentTeamJourneyView = String(view || 'league');
    if (currentTeamDetailData) renderTeamDetailLoaded(currentTeamDetailData);
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
}

function matchPreviewCacheKey(fixtureType, matchId) {
    return `${String(fixtureType || '').toLowerCase()}:${Number(matchId)}`;
}

function getCachedMatchPreview(fixtureType, matchId) {
    const key = matchPreviewCacheKey(fixtureType, matchId);
    const cached = matchPreviewCache.get(key);
    if (!cached) return null;
    if (Date.now() - Number(cached.cachedAt || 0) > MATCH_PREVIEW_CACHE_TTL_MS) {
        matchPreviewCache.delete(key);
        return null;
    }
    return cached.data;
}

function matchPreviewTeamLogo(team) {
    if (team?.logo_path) {
        return `<span class="match-preview-team-logo has-logo"><img src="${escapeHtml(team.logo_path)}" alt="${escapeHtml(team.team_name)}队徽"></span>`;
    }
    return `<span class="match-preview-team-logo" aria-hidden="true">${escapeHtml(String(team?.team_name || '--').slice(0, 2))}</span>`;
}

function matchPreviewForm(form = []) {
    const labels = {W: '胜', D: '平', L: '负'};
    return `<span class="match-preview-form" aria-label="最近比赛：${form.map(item => labels[item] || item).join('、') || '暂无'}">${form.map(item => `<i class="is-${String(item).toLowerCase()}">${escapeHtml(labels[item] || item)}</i>`).join('') || '<em>暂无赛果</em>'}</span>`;
}

function teamDetailRecentLeagueForm(matches, team) {
    const form = (Array.isArray(matches) ? matches : []).slice(0, 5).reverse().map(match => {
        const meta = teamDetailMatchMeta(match, team);
        if (teamDetailSafeNumber(meta.ownScore) > teamDetailSafeNumber(meta.opponentScore)) return 'W';
        if (teamDetailSafeNumber(meta.ownScore) < teamDetailSafeNumber(meta.opponentScore)) return 'L';
        return 'D';
    });
    return matchPreviewForm(form);
}

function matchPreviewStandingProbability(value) {
    const number = teamDetailSafeNumber(value);
    return `${Math.round((number <= 1 ? number * 100 : number) * 10) / 10}%`;
}

function matchPreviewTeamHeadline(team) {
    const prediction = team.predicted_rank
        ? `预测第 ${team.predicted_rank} 名 · 区间 ${team.predicted_rank_min || team.predicted_rank}–${team.predicted_rank_max || team.predicted_rank}`
        : '预测排名待形成';
    return `<div class="match-preview-team-headline">
        ${matchPreviewTeamLogo(team)}
        <div><strong>${escapeHtml(team.team_name)}</strong><small>${escapeHtml(team.level)} · ${team.rank ? `第 ${team.rank} 名 / ${team.points} 分` : '积分榜数据待更新'}</small><em>${escapeHtml(prediction)}</em></div>
    </div>`;
}

function matchPreviewAvailability(team, compact = false) {
    const availability = team.availability || {};
    const tone = availability.reliable ? (availability.missing_count > 0 ? 'warning' : 'clear') : 'uncertain';
    const missing = Array.isArray(availability.missing_players) ? availability.missing_players : [];
    return `<section class="match-preview-availability is-${tone} ${compact ? 'is-compact' : ''}">
        <div class="match-preview-availability-head"><span>${availability.reliable ? (availability.missing_count ? '确认缺席' : '阵容完整') : '时效待确认'}</span><strong>${availability.reliable ? `${teamDetailSafeNumber(availability.missing_count)} 人` : '不计入模型'}</strong></div>
        <p>${escapeHtml(availability.detail || availability.title || '暂时无法判断伤停数据时效')}</p>
        ${missing.length ? `<div class="match-preview-missing-list">${missing.map(player => `<span><b>${escapeHtml(player.player_name)}</b><small>${escapeHtml(player.absence_label || '停赛')}</small></span>`).join('')}</div>` : ''}
    </section>`;
}

function matchPreviewComparisonTeam(team, side) {
    const power = team.lineup_power ?? team.roster_power;
    return `<article class="match-preview-comparison-team is-${side}">
        ${matchPreviewTeamHeadline(team)}
        <div class="match-preview-team-metrics">
            <span><small>近5场</small>${matchPreviewForm(team.recent_form)}</span>
            <span><small>${escapeHtml(team.venue_label || '综合')}战绩</small><strong>${team.venue_wins}-${team.venue_draws}-${team.venue_losses}</strong><em>${team.venue_points} 分 / ${team.venue_played} 场</em></span>
            <span><small>预计阵容战力</small><strong>${power === null || power === undefined ? '--' : teamDetailFormatNumber(power, 2)}</strong><em>${team.lineup_saved ? `${escapeHtml(team.formation)} 已保存` : '系统推荐阵容'}</em></span>
        </div>
        ${matchPreviewAvailability(team, true)}
    </article>`;
}

function matchPreviewSummaryMarkup(data) {
    const prediction = data.prediction || {};
    const probabilities = [
        {label: `${data.home.team_name}胜`, value: teamDetailSafeNumber(prediction.home_win_probability), className: 'home'},
        {label: '平局', value: teamDetailSafeNumber(prediction.draw_probability), className: 'draw'},
        {label: `${data.away.team_name}胜`, value: teamDetailSafeNumber(prediction.away_win_probability), className: 'away'},
    ];
    return `<div class="match-preview-summary">
        <section class="match-preview-prediction-card">
            <div class="match-preview-prediction-title"><div><span>模型参考</span><strong>${escapeHtml(prediction.advantage_label || '势均力敌')}</strong></div><small>可信度 ${escapeHtml(prediction.confidence_label || '低')} · ${Math.round(teamDetailSafeNumber(prediction.confidence) * 100)}%</small></div>
            <div class="match-preview-probabilities">${probabilities.map(item => `<div class="is-${item.className}"><span><b>${escapeHtml(item.label)}</b><strong>${teamDetailFormatNumber(item.value, 1)}%</strong></span><i style="--match-preview-probability:${Math.max(0, Math.min(100, item.value))}%"><b></b></i></div>`).join('')}</div>
            <ul>${(prediction.reasons || []).map(reason => `<li>${escapeHtml(reason)}</li>`).join('')}</ul>
            <p>${escapeHtml(prediction.note || '模型结果仅供赛前参考')}</p>
        </section>
        <div class="match-preview-team-comparison">
            ${matchPreviewComparisonTeam(data.home, 'home')}
            <div class="match-preview-versus" aria-hidden="true"><span>VS</span><i></i></div>
            ${matchPreviewComparisonTeam(data.away, 'away')}
        </div>
    </div>`;
}

function matchPreviewLeaderRows(team) {
    const leaders = Array.isArray(team.leaders) ? team.leaders : [];
    if (!leaders.length) return '<div class="match-preview-empty">暂无足够的球员榜数据。</div>';
    return `<div class="match-preview-leaders">${leaders.map(player => `<article class="${player.is_unavailable ? 'is-unavailable' : ''}">
        <div><strong>${escapeHtml(player.player_name)}</strong><small>${escapeHtml(player.position || '位置待补充')} · ${player.appearances} 场</small></div>
        <span>${(player.roles || []).map(role => `<i>${escapeHtml(role)}</i>`).join('')}</span>
        <dl><div><dt>进球</dt><dd>${player.goals}</dd></div><div><dt>助攻</dt><dd>${player.assists}</dd></div><div><dt>最佳</dt><dd>${player.mvps}</dd></div><div><dt>HEIGO</dt><dd>${player.heigo_power === null || player.heigo_power === undefined ? '--' : teamDetailFormatNumber(player.heigo_power, 2)}</dd></div></dl>
        ${player.is_unavailable ? `<em>${escapeHtml(player.absence_label || '本场缺席')}</em>` : ''}
    </article>`).join('')}</div>`;
}

function matchPreviewPlayersMarkup(data) {
    return `<div class="match-preview-player-grid">
        ${[data.home, data.away].map(team => `<section class="match-preview-player-team">
            ${matchPreviewTeamHeadline(team)}
            <div class="match-preview-section-heading"><div><span>Key Players</span><h3>关键球员</h3></div><small>射手、助攻、最佳与战力核心合并</small></div>
            ${matchPreviewLeaderRows(team)}
            <div class="match-preview-section-heading is-availability"><div><span>Availability</span><h3>伤停与停赛</h3></div></div>
            ${matchPreviewAvailability(team)}
        </section>`).join('')}
    </div>`;
}

function matchPreviewProbabilityContext(team) {
    if (team.level === '超级') {
        return `<span>争冠 ${matchPreviewStandingProbability(team.title_race_probability)}</span><span>降级 ${matchPreviewStandingProbability(team.relegation_probability)}</span>`;
    }
    return `<span>升级 ${matchPreviewStandingProbability(team.promotion_probability)}</span><span>降级 ${matchPreviewStandingProbability(team.relegation_probability)}</span>`;
}

function matchPreviewStakesTeam(team) {
    const cupContext = team.competition_context
        ? `<p>${team.competition_rank ? `杯赛第 ${team.competition_rank} 名 · ${team.competition_points} 分 · ` : ''}${escapeHtml(team.competition_context)}</p>`
        : '';
    return `<article>${matchPreviewTeamHeadline(team)}<div class="match-preview-stakes-probabilities">${matchPreviewProbabilityContext(team)}</div>${cupContext}</article>`;
}

function matchPreviewHeadToHead(data) {
    const rows = Array.isArray(data.head_to_head) ? data.head_to_head : [];
    if (!rows.length) return '<div class="match-preview-empty">本赛季暂无双方已完成交锋。</div>';
    return `<div class="match-preview-h2h-list">${rows.map(row => `<article><div><span>${escapeHtml(row.competition_title)}</span><small>${escapeHtml(row.round_label)}</small></div><p><b>${escapeHtml(row.home_team_name)}</b><strong>${row.home_score} : ${row.away_score}</strong><b>${escapeHtml(row.away_team_name)}</b></p></article>`).join('')}</div>`;
}

function matchPreviewStakesMarkup(data) {
    return `<div class="match-preview-stakes">
        <section class="match-preview-stakes-hero"><span>Match Stakes</span><h3>${escapeHtml(data.stakes_label || '常规比赛')}</h3><p>${escapeHtml(data.stakes_detail || '')}</p></section>
        <div class="match-preview-stakes-teams">${matchPreviewStakesTeam(data.home)}${matchPreviewStakesTeam(data.away)}</div>
        <section class="match-preview-h2h"><div class="match-preview-section-heading"><div><span>Head to Head</span><h3>本赛季交锋</h3></div><small>最多显示最近 4 场</small></div>${matchPreviewHeadToHead(data)}</section>
    </div>`;
}

function renderMatchPreviewBody() {
    const body = document.getElementById('matchPreviewBody');
    if (!body || !currentMatchPreviewData) return;
    if (currentMatchPreviewTab === 'players') body.innerHTML = matchPreviewPlayersMarkup(currentMatchPreviewData);
    else if (currentMatchPreviewTab === 'stakes') body.innerHTML = matchPreviewStakesMarkup(currentMatchPreviewData);
    else body.innerHTML = matchPreviewSummaryMarkup(currentMatchPreviewData);
}

function renderMatchPreviewShell(data) {
    const root = document.getElementById('matchPreviewRoot');
    if (!root) return;
    const fixture = data.fixture;
    document.getElementById('matchPreviewTitle').textContent = `${fixture.home_team_name} vs ${fixture.away_team_name}`;
    root.innerHTML = `<div class="match-preview-fixture-head">
        <div class="match-preview-fixture-meta"><span>${escapeHtml(fixture.competition_title)}</span><strong>${escapeHtml(fixture.round_label)}</strong>${fixture.neutral_venue ? '<small>中立场地模型</small>' : ''}</div>
        <div class="match-preview-matchup"><div>${matchPreviewTeamLogo(data.home)}<strong>${escapeHtml(data.home.team_name)}</strong><small>${fixture.neutral_venue ? '对阵上方' : '主队'}</small></div><b aria-hidden="true">VS</b><div>${matchPreviewTeamLogo(data.away)}<strong>${escapeHtml(data.away.team_name)}</strong><small>${fixture.neutral_venue ? '对阵下方' : '客队'}</small></div></div>
        <nav class="match-preview-tabs" role="tablist" aria-label="比赛前瞻内容">
            ${[['summary', '综合'], ['players', '球员'], ['stakes', '形势']].map(([key, label]) => `<button class="${currentMatchPreviewTab === key ? 'active' : ''}" type="button" role="tab" aria-selected="${currentMatchPreviewTab === key ? 'true' : 'false'}" onclick="setMatchPreviewTab('${key}')">${label}</button>`).join('')}
        </nav>
    </div><div id="matchPreviewBody" class="match-preview-body" role="tabpanel"></div>`;
    renderMatchPreviewBody();
}

function setMatchPreviewTab(tab) {
    if (!['summary', 'players', 'stakes'].includes(tab) || tab === currentMatchPreviewTab) return;
    currentMatchPreviewTab = tab;
    if (currentMatchPreviewData) renderMatchPreviewShell(currentMatchPreviewData);
}

function renderMatchPreviewLoading() {
    const root = document.getElementById('matchPreviewRoot');
    if (!root) return;
    document.getElementById('matchPreviewTitle').textContent = '正在生成比赛前瞻';
    root.innerHTML = `<div class="match-preview-loading" aria-label="正在加载比赛前瞻"><div class="match-preview-loading-matchup"><span></span><i></i><span></span></div><div class="match-preview-loading-tabs"></div><div class="match-preview-loading-grid"><span></span><span></span></div></div>`;
}

async function loadMatchPreview(fixtureType, matchId, options = {}) {
    const cached = options.force ? null : getCachedMatchPreview(fixtureType, matchId);
    if (cached) return cached;
    const data = await fetchJsonOrThrow(`/api/match-previews/${encodeURIComponent(fixtureType)}/${Number(matchId)}`, {signal: options.signal});
    matchPreviewCache.set(matchPreviewCacheKey(fixtureType, matchId), {data, cachedAt: Date.now()});
    return data;
}

async function retryMatchPreview() {
    if (!currentMatchPreviewRequest) return;
    await openMatchPreview(currentMatchPreviewRequest.fixtureType, currentMatchPreviewRequest.matchId, matchPreviewReturnFocus, {force: true, preserveHistory: true});
}

function handleMatchPreviewKeydown(event) {
    const modal = document.getElementById('matchPreviewModal');
    if (!modal?.classList.contains('active')) return;
    if (event.key === 'Escape') {
        event.preventDefault();
        closeMatchPreview();
        return;
    }
    if (event.key !== 'Tab') return;
    const focusable = [...modal.querySelectorAll('button:not(:disabled), a[href], [tabindex]:not([tabindex="-1"])')].filter(element => !element.hidden && element.getClientRects().length);
    if (!focusable.length) {
        event.preventDefault();
        modal.querySelector('.match-preview-dialog')?.focus();
        return;
    }
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

async function openMatchPreview(fixtureType, matchId, triggerElement = null, options = {}) {
    const modal = document.getElementById('matchPreviewModal');
    if (!modal || !Number(matchId)) return;
    matchPreviewAbortController?.abort();
    matchPreviewAbortController = new AbortController();
    const requestController = matchPreviewAbortController;
    currentMatchPreviewRequest = {fixtureType: String(fixtureType), matchId: Number(matchId)};
    currentMatchPreviewData = null;
    currentMatchPreviewTab = 'summary';
    if (triggerElement instanceof HTMLElement) matchPreviewReturnFocus = triggerElement;
    else if (!matchPreviewReturnFocus) matchPreviewReturnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    modal.hidden = false;
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('match-preview-open');
    renderMatchPreviewLoading();
    requestAnimationFrame(() => {
        modal.classList.add('active');
        modal.querySelector('.match-preview-close')?.focus();
    });
    modal.removeEventListener('keydown', handleMatchPreviewKeydown);
    modal.addEventListener('keydown', handleMatchPreviewKeydown);
    if (!matchPreviewHistoryActive && options.preserveHistory !== true) {
        history.pushState({...history.state, __matchPreview: true}, '', window.location.href);
        matchPreviewHistoryActive = true;
    }
    try {
        const data = await loadMatchPreview(fixtureType, matchId, {force: options.force, signal: requestController.signal});
        if (requestController !== matchPreviewAbortController) return;
        currentMatchPreviewData = data;
        renderMatchPreviewShell(data);
    } catch (error) {
        if (error?.name === 'AbortError' || requestController !== matchPreviewAbortController) return;
        const root = document.getElementById('matchPreviewRoot');
        if (root) root.innerHTML = renderUiState({tone: 'danger', title: '比赛前瞻暂时无法加载', message: error.message || '请稍后重试。', actionLabel: '重新加载', actionClass: 'btn-primary', actionOnclick: 'retryMatchPreview()'});
    }
}

function closeMatchPreview(options = {}) {
    const modal = document.getElementById('matchPreviewModal');
    if (!modal || modal.hidden) return;
    matchPreviewAbortController?.abort();
    matchPreviewAbortController = null;
    currentMatchPreviewData = null;
    currentMatchPreviewRequest = null;
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('match-preview-open');
    window.setTimeout(() => {
        if (!modal.classList.contains('active')) modal.hidden = true;
    }, 220);
    const returnFocus = matchPreviewReturnFocus;
    matchPreviewReturnFocus = null;
    const shouldPopHistory = matchPreviewHistoryActive && options.fromPopState !== true && history.state?.__matchPreview;
    matchPreviewHistoryActive = false;
    if (shouldPopHistory) history.back();
    if (returnFocus?.isConnected) requestAnimationFrame(() => returnFocus.focus());
}

window.addEventListener('popstate', event => {
    if (matchPreviewHistoryActive && !event.state?.__matchPreview) closeMatchPreview({fromPopState: true});
});

function teamDetailGrowthStepFromCa(player) {
    const gain = Math.max(0, teamDetailSafeNumber(player.ca) - teamDetailSafeNumber(player.initial_ca));
    if (gain >= 90) return 5;
    if (gain >= 70) return 4;
    if (gain >= 50) return 3;
    if (gain >= 30) return 2;
    if (gain >= 11) return 1;
    return 0;
}

function teamDetailSelectPowerShapes(players, items) {
    const shapesByUid = new Map();
    items.forEach(item => {
        const uid = Number(item.uid);
        if (!shapesByUid.has(uid)) shapesByUid.set(uid, new Map());
        shapesByUid.get(uid).set(Number(item.growth_step || 0), item);
    });
    const selected = new Map();
    players.forEach(player => {
        const shapes = shapesByUid.get(Number(player.uid));
        if (!shapes) return;
        const estimatedStep = teamDetailGrowthStepFromCa(player);
        let appliedStep = estimatedStep;
        while (appliedStep > 0 && !shapes.has(appliedStep)) appliedStep -= 1;
        const power = shapes.get(appliedStep) || shapes.get(0);
        if (!power) return;
        selected.set(Number(player.uid), {
            ...power,
            growth_step: appliedStep,
            estimated_growth_step: estimatedStep,
            league_ca: teamDetailSafeNumber(player.ca),
            league_pa: teamDetailSafeNumber(player.pa),
            league_ca_gain: Math.max(0, teamDetailSafeNumber(player.ca) - teamDetailSafeNumber(player.initial_ca)),
        });
    });
    return selected;
}

function teamDetailGrowthBadge(power) {
    if (!power || !power.growth_step) return '<span class="team-power-shape-badge is-current">当前形态</span>';
    return `<span class="team-power-shape-badge">+${Number(power.growth_step)} 估算</span>`;
}

function teamDetailPlayerButton(player, className = '') {
    return `<button class="team-detail-player-link ${className}" type="button" onclick="openPlayerAttributeDetail(${Number(player.uid)}, {returnTab: 'team'})">
        <span>${escapeHtml(player.name || player.display_name || '-')}</span>
    </button>`;
}

function teamDetailSpineBand(key, label, items, powerByUid) {
    const averageCa = items.length ? items.reduce((sum, item) => sum + teamDetailSafeNumber(item.ca), 0) / items.length : 0;
    const powered = items.map(item => powerByUid.get(Number(item.uid))).filter(Boolean);
    const averagePower = powered.length ? powered.reduce((sum, item) => sum + teamDetailSafeNumber(item.heigo_power), 0) / powered.length : 0;
    return `<section class="team-spine-band team-spine-${key}">
        <div class="team-spine-label"><span>${label}</span><strong>${items.length}</strong></div>
        <div class="team-spine-metrics"><span>平均 CA <b>${teamDetailFormatNumber(averageCa, 1)}</b></span><span>HEIGO <b>${powered.length ? teamDetailFormatNumber(averagePower, 2) : '--'}</b></span></div>
        <div class="team-spine-players">${items.slice(0, 3).map(player => teamDetailPlayerButton(player)).join('') || '<span class="team-detail-muted">暂无球员</span>'}</div>
    </section>`;
}

function teamDetailPowerCore(items) {
    if (!items.length) return '<div class="team-detail-empty-inline">当前球队暂无可用战力数据。</div>';
    return `<div class="team-power-core-list">${items.slice(0, 4).map((item, index) => `<article class="team-power-core-item">
        <span class="team-power-rank">${String(index + 1).padStart(2, '0')}</span>
        <div class="team-power-player">${teamDetailPlayerButton(item)}<small>${escapeHtml(item.position || '-')} · 当前 CA ${teamDetailSafeNumber(item.league_ca, item.ca)} ${teamDetailGrowthBadge(item)}</small></div>
        <div class="team-power-metric team-power-compact-score"><strong>${teamDetailFormatNumber(item.heigo_power, 2)}</strong><span>HEIGO 战力</span><small>加权 ${teamDetailFormatNumber(item.weighted_power, 2)} · 前 ${teamDetailFormatNumber(item.top_percent, 2)}%</small></div>
    </article>`).join('')}</div>`;
}

function teamDetailPlayerLeaderConfig(metric = currentTeamPlayerLeaderMetric) {
    return {
        goals: {label: '射手榜', unit: '球', empty: '暂无进球记录'},
        assists: {label: '助攻榜', unit: '次', empty: '暂无助攻记录'},
        mvps: {label: '最佳球员榜', unit: '次', empty: '暂无最佳球员记录'},
    }[metric] || {label: '射手榜', unit: '球', empty: '暂无进球记录'};
}

function teamDetailPlayerLeaderRows(payload, metric = currentTeamPlayerLeaderMetric) {
    return (Array.isArray(payload?.rows) ? payload.rows : [])
        .filter(row => Number(row?.[metric] || 0) > 0)
        .sort((a, b) => {
            const metricDiff = Number(b?.[metric] || 0) - Number(a?.[metric] || 0);
            if (metricDiff) return metricDiff;
            const goalsDiff = Number(b?.goals || 0) - Number(a?.goals || 0);
            if (goalsDiff) return goalsDiff;
            const assistsDiff = Number(b?.assists || 0) - Number(a?.assists || 0);
            if (assistsDiff) return assistsDiff;
            const mvpsDiff = Number(b?.mvps || 0) - Number(a?.mvps || 0);
            if (mvpsDiff) return mvpsDiff;
            return String(a?.player_name || '').localeCompare(String(b?.player_name || ''));
        })
        .slice(0, 5);
}

function teamDetailPlayerLeaderLink(row) {
    const uid = Number(row?.player_uid || 0);
    const name = escapeHtml(row?.player_name || '-');
    if (!Number.isInteger(uid) || uid <= 0) return `<span class="team-player-leader-name">${name}</span>`;
    return `<button class="team-detail-player-link team-player-leader-name" type="button" onclick="openPlayerAttributeDetail(${uid}, {returnTab: 'team'})"><span>${name}</span></button>`;
}

function teamDetailPlayerLeaderTabs() {
    return `<div class="team-player-leader-tabs" role="tablist" aria-label="队内球员数据榜">
        ${[['goals', '射手', '射手榜'], ['assists', '助攻', '助攻榜'], ['mvps', '最佳', '最佳球员榜']].map(([key, label, ariaLabel]) => `<button class="team-player-leader-tab ${currentTeamPlayerLeaderMetric === key ? 'active' : ''}" type="button" role="tab" data-team-player-leader-metric="${key}" aria-label="${ariaLabel}" aria-selected="${currentTeamPlayerLeaderMetric === key ? 'true' : 'false'}" onclick="setTeamPlayerLeaderMetric('${key}')">${label}</button>`).join('')}
    </div>`;
}

function teamDetailPlayerLeaders(payload) {
    const metric = currentTeamPlayerLeaderMetric;
    const config = teamDetailPlayerLeaderConfig(metric);
    const rows = teamDetailPlayerLeaderRows(payload, metric);
    return `<div class="team-player-leader-list" role="tabpanel" aria-label="${config.label}">
        ${rows.length ? rows.map((row, index) => `<article class="team-player-leader-row ${index === 0 ? 'is-first' : ''}">
            <span class="team-player-leader-rank">${String(index + 1).padStart(2, '0')}</span>
            <div class="team-player-leader-player">${teamDetailPlayerLeaderLink(row)}<small>${teamDetailSafeNumber(row.appearances)} 场</small></div>
            <strong>${teamDetailSafeNumber(row[metric])}<small>${config.unit}</small></strong>
        </article>`).join('') : `<div class="team-player-leader-empty">${config.empty}</div>`}
    </div>`;
}

function setTeamPlayerLeaderMetric(metric) {
    currentTeamPlayerLeaderMetric = ['goals', 'assists', 'mvps'].includes(metric) ? metric : 'goals';
    document.querySelectorAll('.team-player-leader-tab').forEach(button => {
        const active = button.dataset.teamPlayerLeaderMetric === currentTeamPlayerLeaderMetric;
        button.classList.toggle('active', active);
        button.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    const root = document.getElementById('teamPlayerLeadersContent');
    if (root && currentTeamDetailData) root.innerHTML = teamDetailPlayerLeaders(currentTeamDetailData.playerRankingsPayload);
}

function teamDetailSuspensionFreshness(teamSuspensions) {
    const progress = teamSuspensions?.progress;
    if (!progress || !['current', 'ahead', 'stale', 'gap', 'unknown'].includes(progress.state)) {
        return {state: 'unknown', title: '伤停轮次待确认', detail: '暂时无法判断数据时效'};
    }
    return {
        state: progress.state,
        title: String(progress.title || '伤停轮次待确认'),
        detail: String(progress.detail || '暂时无法判断数据时效'),
        matchLatestRound: teamDetailSafeNumber(progress.match_latest_recorded_round, progress.match_completed_round),
        matchContinuousRound: teamDetailSafeNumber(progress.match_continuous_completed_round, progress.match_completed_round),
        matchGapRounds: Array.isArray(progress.match_gap_rounds) ? progress.match_gap_rounds.map(Number).filter(Number.isInteger) : [],
        suspensionCheckedRound: progress.suspension_checked_round === null || progress.suspension_checked_round === undefined ? null : teamDetailSafeNumber(progress.suspension_checked_round),
        appliesFromRound: progress.applies_from_round === null || progress.applies_from_round === undefined ? null : teamDetailSafeNumber(progress.applies_from_round),
    };
}

function teamDetailEffectiveUpcomingMatches(matches, progress) {
    const floorRound = teamDetailSafeNumber(progress?.progress_floor_round);
    const gapRounds = new Set((progress?.match_gap_rounds || []).map(Number).filter(Number.isInteger));
    return matches.filter(match => (
        match.status === 'postponed'
        || gapRounds.has(teamDetailSafeNumber(match.round_no))
        || teamDetailSafeNumber(match.round_no) > floorRound
    ));
}

function teamDetailSuspensionLabel(item) {
    const total = Math.max(1, teamDetailSafeNumber(item?.suspension_matches, 1));
    const remaining = Math.max(0, teamDetailSafeNumber(item?.suspension_remaining_matches, total));
    const rounds = [...new Set((item?.suspension_affected_rounds || []).map(Number).filter(Number.isInteger))];
    const roundLabel = rounds.length ? ` · 影响${rounds.map(roundNo => `第${roundNo}轮`).join('、')}` : '';
    return `停赛共${total}场 · 剩余${remaining}场${roundLabel}`;
}

function teamDetailDisciplinePlayers(items, tone) {
    if (tone !== 'danger') return items.map(item => escapeHtml(item.player_name || item.name || String(item))).join('、') || '无';
    return items.map(item => `<span class="team-discipline-player"><b>${escapeHtml(item.player_name || item.name || String(item))}</b><small>${escapeHtml(teamDetailSuspensionLabel(item))}</small></span>`).join('') || '无';
}

function teamDetailDiscipline(teamSuspensions, freshness) {
    const status = freshness || {state: 'unknown', title: '伤停轮次待确认', detail: '暂时无法判断数据时效'};
    const statusIcon = status.state === 'current' ? '✓' : status.state === 'ahead' ? '↗' : ['stale', 'gap'].includes(status.state) ? '!' : '?';
    const freshnessMarkup = `<div class="team-discipline-freshness is-${escapeHtml(status.state)}"><span aria-hidden="true">${statusIcon}</span><div><strong>${escapeHtml(status.title)}</strong><small>${escapeHtml(status.detail)}</small></div></div>`;
    const hasGaps = Boolean(status.matchGapRounds?.length);
    const progressMarkup = `<div class="team-discipline-progress" aria-label="赛果与伤停轮次进度">
        <span><small>${hasGaps ? '赛果连续至' : '赛果至'}</small><strong>第 ${teamDetailSafeNumber(hasGaps ? status.matchContinuousRound : status.matchLatestRound)} 轮</strong>${hasGaps ? `<em>最高第 ${teamDetailSafeNumber(status.matchLatestRound)} 轮</em>` : ''}</span>
        <span><small>伤停至</small><strong>${status.suspensionCheckedRound === null || status.suspensionCheckedRound === undefined ? '--' : `第 ${teamDetailSafeNumber(status.suspensionCheckedRound)} 轮`}</strong></span>
        <span><small>适用于</small><strong>${status.appliesFromRound === null || status.appliesFromRound === undefined ? '--' : `第 ${teamDetailSafeNumber(status.appliesFromRound)} 轮`}</strong></span>
    </div>`;
    if (!teamSuspensions) return `${freshnessMarkup}${progressMarkup}<div class="team-detail-empty-inline">暂无纪律数据。</div>`;
    const sections = [
        ['停赛', teamSuspensions.suspended || [], 'danger'],
        ['两黄', teamSuspensions.two_yellows || [], 'warning'],
        ['一黄', teamSuspensions.one_yellow || [], 'neutral'],
    ];
    const hasAny = sections.some(([, items]) => items.length);
    if (!hasAny) {
        const clearTitle = status.state === 'current' ? '阵容可用' : '暂无已登记伤停';
        const clearDetail = ['current', 'ahead'].includes(status.state) ? '暂无黄牌累积或停赛记录' : '伤停轮次未匹配，阵容状态仍需确认';
        return `${freshnessMarkup}${progressMarkup}<div class="team-discipline-clear is-${escapeHtml(status.state)}"><span>${status.state === 'current' ? '✓' : '!'}</span><div><strong>${clearTitle}</strong><small>${clearDetail}</small></div></div>`;
    }
    return `${freshnessMarkup}${progressMarkup}<div class="team-discipline-list">${sections.map(([label, items, tone]) => `<div class="team-discipline-row is-${tone}${items.length ? ' has-records' : ''}"><span>${label}</span><strong>${items.length}</strong><p>${teamDetailDisciplinePlayers(items, tone)}</p></div>`).join('')}</div>`;
}

function teamDetailRoster(players, powerByUid) {
    const sorted = teamDetailSortedRoster(players, powerByUid);
    return `<div class="team-roster-list">${sorted.map(player => {
        const power = powerByUid.get(Number(player.uid));
        return `<article class="team-roster-row">
            <div class="team-roster-position">${escapeHtml(player.position || '-')}</div>
            <div class="team-roster-name">${teamDetailPlayerButton(player)}<small>${escapeHtml(player.nationality || '-')} · ${teamDetailSafeNumber(player.age)} 岁</small></div>
            <div class="team-roster-stat"><span>CA / PA</span><strong>${teamDetailSafeNumber(player.ca)} / ${teamDetailSafeNumber(player.pa)}</strong></div>
            <div class="team-roster-stat team-roster-power"><span>HEIGO</span><strong>${power ? teamDetailFormatNumber(power.heigo_power, 2) : '--'}</strong>${power ? teamDetailGrowthBadge(power) : ''}</div>
            <div class="team-roster-stat team-roster-wage"><span>工资</span><strong>${teamDetailFormatNumber(player.wage, 2)}M</strong></div>
            <button class="team-roster-player-copy" type="button" onclick="copyTeamRosterPlayer(event, ${Number(player.uid)})">复制</button>
        </article>`;
    }).join('')}</div>`;
}

function teamDetailSortedRoster(players, powerByUid) {
    return [...players].sort((a, b) => {
        const powerA = powerByUid.get(Number(a.uid));
        const powerB = powerByUid.get(Number(b.uid));
        return teamDetailSafeNumber(powerB?.heigo_power, b.ca) - teamDetailSafeNumber(powerA?.heigo_power, a.ca);
    });
}

function teamDetailRosterStorageKey() {
    return window.matchMedia?.('(max-width: 700px)').matches
        ? 'heigo_team_roster_view_mobile'
        : 'heigo_team_roster_view_desktop';
}

function getTeamRosterViewMode() {
    const saved = localStorage.getItem(teamDetailRosterStorageKey());
    if (TEAM_ROSTER_VIEW_MODES.has(saved)) return saved;
    return window.matchMedia?.('(max-width: 700px)').matches ? 'cards' : 'compact';
}

function teamDetailRosterViewSwitch(mode = getTeamRosterViewMode()) {
    const options = [
        ['compact', '简略版'],
        ['detail', '详细版'],
        ['cards', '卡片版'],
    ];
    return `<div class="team-roster-view-switch" id="teamRosterViewSwitch" role="tablist" aria-label="球队名单视图">${options.map(([value, label]) => `<button type="button" role="tab" class="team-roster-view-button ${mode === value ? 'is-active' : ''}" aria-selected="${mode === value}" onclick="setTeamRosterViewMode('${value}')">${label}</button>`).join('')}</div>`;
}

function teamDetailRosterSlotBadge(slot) {
    const normalized = String(slot || '').trim();
    if (!normalized) return '<span class="team-roster-slot-empty">普通</span>';
    const tone = {'7M': 'slot-7m', '8M': 'slot-8m', '伪名': 'slot-fake'}[normalized] || '';
    return `<span class="slot-badge ${tone}">${escapeHtml(normalized)}</span>`;
}

function teamDetailRosterPositionClass(position) {
    const group = teamDetailPositionGroup(position);
    return group === 'gk' ? 'is-gk' : group === 'def' ? 'is-defender' : group === 'att' ? 'is-attacker' : 'is-midfielder';
}

function teamDetailRosterGrowth(player) {
    return teamDetailSafeNumber(player.ca) - teamDetailSafeNumber(player.initial_ca);
}

function teamDetailCompactNationality(value, maxLength = 18) {
    if (typeof formatCompactNationality === 'function') return formatCompactNationality(value || '-', {maxLength});
    const normalized = String(value || '-');
    return normalized.length > maxLength ? `${normalized.slice(0, maxLength - 1)}…` : normalized;
}

function teamDetailDetailedRoster(players, powerByUid) {
    const sorted = teamDetailSortedRoster(players, powerByUid);
    return `<div class="team-roster-detail-scroll"><table class="team-roster-detail-table" aria-label="球队详细名单">
        <thead><tr><th>球员</th><th>年龄</th><th>初始 CA</th><th>当前 CA</th><th>当前 PA</th><th>位置</th><th>国籍</th><th>工资</th><th>名额</th><th>复制</th></tr></thead>
        <tbody>${sorted.map(player => {
            const power = powerByUid.get(Number(player.uid));
            return `<tr><td class="team-roster-detail-player">${teamDetailPlayerButton(player)}<small>UID ${Number(player.uid)}${power ? ` · HEIGO ${teamDetailFormatNumber(power.heigo_power, 2)}` : ''}</small></td><td>${teamDetailSafeNumber(player.age)}</td><td>${teamDetailSafeNumber(player.initial_ca)}</td><td><strong>${teamDetailSafeNumber(player.ca)}</strong></td><td>${teamDetailSafeNumber(player.pa)}</td><td class="team-roster-detail-position">${escapeHtml(player.position || '-')}</td><td title="${escapeHtml(player.nationality || '-')}">${escapeHtml(teamDetailCompactNationality(player.nationality, 14))}</td><td>${teamDetailFormatNumber(player.wage, 3)}M</td><td>${teamDetailRosterSlotBadge(player.slot_type)}</td><td><button class="team-roster-player-copy" type="button" onclick="copyTeamRosterPlayer(event, ${Number(player.uid)})">复制</button></td></tr>`;
        }).join('')}</tbody>
    </table></div>`;
}

function teamDetailRosterCards(players, powerByUid) {
    const sorted = teamDetailSortedRoster(players, powerByUid);
    return `<div class="team-roster-card-grid" aria-label="球队卡片名单">${sorted.map(player => {
        const power = powerByUid.get(Number(player.uid));
        const growth = teamDetailRosterGrowth(player);
        const growthClass = growth > 0 ? 'is-positive' : growth < 0 ? 'is-negative' : 'is-flat';
        return `<article class="team-roster-card">
            <div class="team-roster-card-head"><div>${teamDetailPlayerButton(player, 'team-roster-card-name')}<small>UID ${Number(player.uid)} · ${escapeHtml(teamDetailCompactNationality(player.nationality, 20))}</small></div><span class="team-roster-card-position ${teamDetailRosterPositionClass(player.position)}">${escapeHtml(player.position || '-')}</span></div>
            <div class="team-roster-card-meta"><span>${teamDetailRosterSlotBadge(player.slot_type)}</span><span class="team-roster-card-power">HEIGO <strong>${power ? teamDetailFormatNumber(power.heigo_power, 2) : '--'}</strong></span></div>
            <div class="team-roster-card-stats"><span><strong>${teamDetailSafeNumber(player.age)}</strong><em>年龄</em></span><span><strong>${teamDetailSafeNumber(player.initial_ca)}</strong><em>初始 CA</em></span><span><strong>${teamDetailSafeNumber(player.ca)}</strong><em>当前 CA</em></span><span><strong>${teamDetailSafeNumber(player.pa)}</strong><em>当前 PA</em></span><span class="${growthClass}"><strong>${growth > 0 ? '+' : ''}${growth}</strong><em>成长</em></span><span><strong>${teamDetailFormatNumber(player.wage, 3)}M</strong><em>工资</em></span></div>
            <button class="team-roster-card-copy" type="button" onclick="copyTeamRosterPlayer(event, ${Number(player.uid)})">复制球员信息</button>
        </article>`;
    }).join('')}</div>`;
}

function teamDetailRosterView(players, powerByUid, mode = getTeamRosterViewMode()) {
    if (mode === 'detail') return teamDetailDetailedRoster(players, powerByUid);
    if (mode === 'cards') return teamDetailRosterCards(players, powerByUid);
    return teamDetailRoster(players, powerByUid);
}

function setTeamRosterViewMode(mode) {
    if (!TEAM_ROSTER_VIEW_MODES.has(mode) || !currentTeamDetailData) return;
    localStorage.setItem(teamDetailRosterStorageKey(), mode);
    const body = document.getElementById('teamRosterViewBody');
    const switcher = document.getElementById('teamRosterViewSwitch');
    if (body) body.innerHTML = teamDetailRosterView(currentTeamDetailData.players, currentTeamDetailData.powerByUid, mode);
    if (switcher) switcher.outerHTML = teamDetailRosterViewSwitch(mode);
}

function teamDetailFallbackCopyText(text) {
    if (typeof fallbackCopyRosterText === 'function') return fallbackCopyRosterText(text);
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.top = '-1000px';
    document.body.appendChild(textarea);
    textarea.select();
    try {
        return document.execCommand('copy');
    } catch (_error) {
        return false;
    } finally {
        textarea.remove();
    }
}

function showTeamRosterCopyStatus(message, tone = 'success') {
    if (typeof showDetailExportToast === 'function') {
        showDetailExportToast(message, tone);
        return;
    }
    let toast = document.getElementById('teamRosterCopyToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'teamRosterCopyToast';
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', 'polite');
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.className = `detail-export-toast is-visible is-${tone}`;
    window.clearTimeout(teamRosterCopyToastTimer);
    teamRosterCopyToastTimer = window.setTimeout(() => toast.classList.remove('is-visible'), 1800);
}

async function copyTeamRosterPlayer(event, uid) {
    event?.preventDefault();
    event?.stopPropagation();
    const player = currentTeamDetailData?.players?.find(item => Number(item.uid) === Number(uid));
    if (!player) return;
    const text = [player.uid, player.name, player.age, player.initial_ca, player.ca, player.pa, player.position, player.nationality, `${teamDetailFormatNumber(player.wage, 3)}M`, player.slot_type || '普通'].map(value => String(value ?? '').trim()).join(' ');
    let copied = false;
    try {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(text);
            copied = true;
        }
    } catch (_error) {
        copied = false;
    }
    if (!copied) copied = teamDetailFallbackCopyText(text);
    showTeamRosterCopyStatus(copied ? '已复制球员信息' : '浏览器未允许写入剪贴板，请手动复制', copied ? 'success' : 'warning');
}

function teamDetailPlayersWithPower(players, powerByUid, teamName, teamSuspensions = null) {
    const suspendedByUid = new Map((teamSuspensions?.suspended || []).map(item => [Number(item.player_uid), item]));
    return players.map(player => ({
        ...player,
        team_name: player.team_name || teamName,
        heigo_power: powerByUid.has(Number(player.uid)) ? teamDetailSafeNumber(powerByUid.get(Number(player.uid)).heigo_power) : null,
        is_unavailable: suspendedByUid.has(Number(player.uid)),
        suspension_label: suspendedByUid.has(Number(player.uid)) ? teamDetailSuspensionLabel(suspendedByUid.get(Number(player.uid))) : '',
    }));
}

function teamDetailPreviewPicks(players, lineupPayload) {
    const savedPicks = lineupPayload?.picks && typeof lineupPayload.picks === 'object' ? lineupPayload.picks : {};
    if (Object.keys(savedPicks).length) return savedPicks;
    if (typeof buildAutoRosterFormationPicks !== 'function') return {};
    return buildAutoRosterFormationPicks(players, lineupPayload?.formation || '4-3-3');
}

function teamDetailAveragePowerForPicks(picks, powerByUid) {
    const items = Object.values(picks || {}).map(uid => powerByUid.get(Number(uid))).filter(Boolean);
    return {
        value: items.length ? items.reduce((sum, item) => sum + teamDetailSafeNumber(item.heigo_power), 0) / items.length : null,
        count: items.length,
    };
}

function teamDetailPowerRankLabel(level, rank, total) {
    if (!rank) return `${escapeHtml(level || '当前级别')}暂无排名`;
    return `${escapeHtml(level || '当前级别')}第 ${Number(rank)} / ${Number(total || 0)}`;
}

async function loadTeamPowerSummaries(options = {}) {
    if (options.force === true) teamPowerSummariesPromise = null;
    if (!teamPowerSummariesPromise) {
        teamPowerSummariesPromise = fetchJsonOrThrow('/api/teams/power-summaries').catch(error => {
            teamPowerSummariesPromise = null;
            throw error;
        });
    }
    return teamPowerSummariesPromise;
}

function openTeamLineupEditor() {
    if (!currentTeamDetailData || typeof openRosterFormationModal !== 'function') return;
    const {team, lineupPayload} = currentTeamDetailData;
    openRosterFormationModal(team.name, {
        teamId: team.id,
        players: currentTeamDetailData.lineupPlayers || [],
        formation: lineupPayload?.formation || '4-3-3',
        picks: lineupPayload?.picks || {},
        canEdit: Boolean(lineupPayload?.can_edit),
    });
}

function teamDetailHandleLineupSaved(payload) {
    if (!currentTeamDetailData || Number(payload?.team_id) !== Number(currentTeamDetailData.team.id)) return;
    currentTeamDetailData.lineupPayload = payload;
    setCachedTeamDetail(currentTeamDetailData.team.name, currentTeamDetailData);
    renderTeamDetailLoaded(currentTeamDetailData);
    loadTeamPowerSummaries({force: true}).then(powerSummaries => {
        if (!currentTeamDetailData || Number(payload?.team_id) !== Number(currentTeamDetailData.team.id)) return;
        currentTeamDetailData.teamPowerSummaries = powerSummaries;
        setCachedTeamDetail(currentTeamDetailData.team.name, currentTeamDetailData);
        renderTeamDetailLoaded(currentTeamDetailData);
    }).catch(error => console.warn('Failed to refresh team power summaries:', error));
}

function teamDetailRosterExportMarkup(data) {
    const {team, players, powerByUid} = data;
    const sorted = [...players].sort((a, b) => teamDetailSafeNumber(powerByUid.get(Number(b.uid))?.heigo_power, b.ca) - teamDetailSafeNumber(powerByUid.get(Number(a.uid))?.heigo_power, a.ca));
    const logo = team.logo_path ? `<img src="${escapeHtml(team.logo_path)}" alt="">` : `<span>${escapeHtml(team.name.slice(0, 2).toUpperCase())}</span>`;
    return `<article class="team-roster-export-card">
        <header><div class="team-roster-export-crest">${logo}</div><div><span>HEIGO Team Roster</span><h2>${escapeHtml(team.name)}</h2><p>${escapeHtml(team.level)} · 主教练 ${escapeHtml(team.manager || '待定')} · ${players.length} 人</p></div><strong>${teamDetailFormatNumber(data.avgHeigo, 2)}<small>平均 HEIGO</small></strong></header>
        <div class="team-roster-export-head"><span>位置</span><span>球员</span><span>CA / PA</span><span>HEIGO</span><span>工资</span></div>
        <div class="team-roster-export-list">${sorted.map(player => {
            const power = powerByUid.get(Number(player.uid));
            return `<div class="team-roster-export-row"><span>${escapeHtml(player.position || '-')}</span><strong>${escapeHtml(player.name || '-')}<small>${escapeHtml(player.nationality || '-')} · ${teamDetailSafeNumber(player.age)} 岁</small></strong><b>${teamDetailSafeNumber(player.ca)} / ${teamDetailSafeNumber(player.pa)}</b><b>${power ? teamDetailFormatNumber(power.heigo_power, 2) : '--'}</b><b>${teamDetailFormatNumber(player.wage, 2)}M</b></div>`;
        }).join('')}</div>
        <footer><span>HEIGO 联赛数据台</span><span>生成于 ${new Date().toLocaleDateString('zh-CN')}</span></footer>
    </article>`;
}

function buildTeamRosterImageFileName(teamName) {
    const cleanTeam = String(teamName || '球队').replace(/[\\/:*?"<>|\s]+/g, '_');
    const date = new Date();
    const stamp = `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, '0')}${String(date.getDate()).padStart(2, '0')}`;
    return `HEIGO_${cleanTeam}_球队名单_${stamp}.png`;
}

function downloadTeamRosterBlob(blob, fileName) {
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1200);
}

function showTeamRosterImageFallback(blob, fileName) {
    const objectUrl = URL.createObjectURL(blob);
    showModal('保存球队名单图', `<div class="player-image-fallback"><div class="player-image-fallback-copy"><span class="panel-kicker">Team Roster</span><h2>球队名单图已生成</h2><p>当前环境无法直接复制图片，请下载保存；手机端也可以长按下方图片。</p></div><div class="player-image-fallback-preview"><img src="${escapeHtml(objectUrl)}" alt="球队名单图片预览"></div><div class="player-image-fallback-actions"><a class="btn btn-primary player-image-fallback-action" href="${escapeHtml(objectUrl)}" download="${escapeHtml(fileName)}"><span class="player-image-action-icon" aria-hidden="true">${uiIconSvg('download', 'ui-icon is-small')}</span><span>下载球队名单</span></a><button class="btn btn-secondary player-image-fallback-action" type="button" onclick="closeModal()">返回球队中心</button></div></div>`);
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 120000);
}

function buildTeamLineupImageFileName(teamName, formation) {
    const cleanTeam = String(teamName || '球队').replace(/[\\/:*?"<>|\s]+/g, '_');
    const cleanFormation = String(formation || '阵型').replace(/[\\/:*?"<>|\s]+/g, '_');
    const date = new Date();
    const stamp = `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, '0')}${String(date.getDate()).padStart(2, '0')}`;
    return `HEIGO_${cleanTeam}_${cleanFormation}_阵容预览_${stamp}.png`;
}

function showTeamLineupImageFallback(blob, fileName) {
    const objectUrl = URL.createObjectURL(blob);
    showModal('保存阵容图', `<div class="player-image-fallback"><div class="player-image-fallback-copy"><span class="panel-kicker">Starting XI</span><h2>阵容图已生成</h2><p>当前环境无法直接复制图片，请下载保存；手机端也可以长按下方图片。</p></div><div class="player-image-fallback-preview"><img src="${escapeHtml(objectUrl)}" alt="阵容预览图片"></div><div class="player-image-fallback-actions"><a class="btn btn-primary player-image-fallback-action" href="${escapeHtml(objectUrl)}" download="${escapeHtml(fileName)}"><span class="player-image-action-icon" aria-hidden="true">${uiIconSvg('download', 'ui-icon is-small')}</span><span>下载阵容图</span></a><button class="btn btn-secondary player-image-fallback-action" type="button" onclick="closeModal()">返回球队中心</button></div></div>`);
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 120000);
}

async function copyTeamLineupImage() {
    if (teamLineupExportBusy || !currentTeamDetailData) return;
    try {
        await ensureHtmlToImage();
    } catch (error) {
        console.error('Failed to load lineup export component:', error);
    }
    if (!window.htmlToImage || typeof window.htmlToImage.toBlob !== 'function') {
        showModal('导出组件未就绪', '阵容图片组件加载失败，请刷新页面后重试。');
        return;
    }
    const captureCard = document.querySelector('.team-lineup-panel .team-center-lineup-capture');
    if (!captureCard) {
        showModal('暂时无法保存', '当前没有可导出的阵容预览。');
        return;
    }
    teamLineupExportBusy = true;
    captureCard.classList.add('is-exporting');
    try {
        if (document.fonts?.ready) await document.fonts.ready;
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        const blobPromise = window.htmlToImage.toBlob(captureCard, {
            cacheBust: true,
            pixelRatio: Math.max(2, Math.min(3, window.devicePixelRatio || 1)),
        });
        const canCopy = Boolean(window.isSecureContext && navigator.clipboard?.write && typeof ClipboardItem !== 'undefined');
        let copyPromise = null;
        if (canCopy) {
            try {
                copyPromise = navigator.clipboard.write([new ClipboardItem({'image/png': blobPromise})]).then(() => true, () => false);
            } catch (error) {
                copyPromise = null;
            }
        }
        const blob = await blobPromise;
        if (!blob) throw new Error('capture-blob-empty');
        const formation = currentTeamDetailData.lineupPayload?.formation || '4-3-3';
        const fileName = buildTeamLineupImageFileName(currentTeamDetailData.team.name, formation);
        const copied = copyPromise ? await copyPromise : false;
        if (copied) {
            showSuccessToast('阵容图片已复制到剪贴板');
        } else {
            showTeamLineupImageFallback(blob, fileName);
        }
    } catch (error) {
        console.error('Failed to export team lineup image:', error);
        showModal('生成阵容图失败', '阵容图片生成失败，请刷新页面后重试。');
    } finally {
        captureCard.classList.remove('is-exporting');
        teamLineupExportBusy = false;
    }
}

async function copyTeamRosterImage() {
    if (teamRosterExportBusy || !currentTeamDetailData) return;
    try {
        await ensureHtmlToImage();
    } catch (error) {
        console.error('Failed to load roster export component:', error);
    }
    if (!window.htmlToImage || typeof window.htmlToImage.toBlob !== 'function') {
        showModal('导出组件未就绪', '球队名单图片组件加载失败，请刷新页面后重试。');
        return;
    }
    teamRosterExportBusy = true;
    const captureRoot = document.createElement('div');
    captureRoot.className = 'capture-export-root';
    captureRoot.innerHTML = teamDetailRosterExportMarkup(currentTeamDetailData);
    document.body.appendChild(captureRoot);
    try {
        if (document.fonts?.ready) await document.fonts.ready;
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        const captureCard = captureRoot.firstElementChild;
        const blobPromise = window.htmlToImage.toBlob(captureCard, {cacheBust: true, pixelRatio: 2});
        const canCopy = Boolean(window.isSecureContext && navigator.clipboard?.write && typeof ClipboardItem !== 'undefined');
        let copyPromise = null;
        if (canCopy) {
            try {
                copyPromise = navigator.clipboard.write([new ClipboardItem({'image/png': blobPromise})]).then(() => true, () => false);
            } catch (error) {
                copyPromise = null;
            }
        }
        const blob = await blobPromise;
        if (!blob) throw new Error('capture-blob-empty');
        const fileName = buildTeamRosterImageFileName(currentTeamDetailData.team.name);
        const copied = copyPromise ? await copyPromise : false;
        if (copied) {
            showSuccessToast('球队名单图片已复制到剪贴板');
        } else {
            showTeamRosterImageFallback(blob, fileName);
        }
    } catch (error) {
        console.error('Failed to export team roster image:', error);
        showModal('生成球队名单失败', '球队名单图片生成失败，请刷新页面后重试。');
    } finally {
        captureRoot.remove();
        teamRosterExportBusy = false;
    }
}

function teamDetailTeamSwitcher(activeTeam) {
    const levels = ['超级', '甲级', '乙级'];
    const options = levels.map(level => {
        const levelTeams = teams.filter(team => team.level === level).sort((a, b) => a.name.localeCompare(b.name));
        return `<optgroup label="${level}">${levelTeams.map(team => `<option value="${escapeHtml(team.name)}" ${team.name === activeTeam.name ? 'selected' : ''}>${escapeHtml(team.name)}</option>`).join('')}</optgroup>`;
    }).join('');
    const orderedTeams = levels.flatMap(level => teams.filter(team => team.level === level).sort((a, b) => a.name.localeCompare(b.name)));
    const activeIndex = orderedTeams.findIndex(team => team.name === activeTeam.name);
    return `<section class="team-center-switcher surface-card" aria-label="切换球队">
        <div class="team-center-switcher-copy"><span class="panel-kicker">54 Teams</span><strong>球队中心</strong><small>切换球队查看完整阵容与赛程</small></div>
        <div class="team-center-switcher-control">
            <button type="button" onclick="shiftTeamCenter(-1)" aria-label="上一支球队">‹</button>
            <label for="teamCenterTeamSelect"><span>当前球队</span><select id="teamCenterTeamSelect" aria-label="当前球队，选择另一支球队" onchange="switchTeamCenter(this.value)">${options}</select></label>
            <button type="button" onclick="shiftTeamCenter(1)" aria-label="下一支球队">›</button>
        </div>
        <button class="team-center-overview-link" type="button" onclick="showTab('overview')">浏览 54 队概览</button>
        <span class="team-center-index">${activeIndex + 1} / ${orderedTeams.length}</span>
    </section>`;
}

function getTeamCenterSearchMatches(query, limit = 8) {
    const normalizedQuery = String(query || '').trim().toLocaleLowerCase();
    if (!normalizedQuery) return [];
    return [...(teams || [])]
        .filter(team => [team.name, team.manager].some(value => String(value || '').toLocaleLowerCase().includes(normalizedQuery)))
        .sort((a, b) => {
            const aName = String(a.name || '').toLocaleLowerCase();
            const bName = String(b.name || '').toLocaleLowerCase();
            const aExact = aName === normalizedQuery ? 0 : aName.startsWith(normalizedQuery) ? 1 : 2;
            const bExact = bName === normalizedQuery ? 0 : bName.startsWith(normalizedQuery) ? 1 : 2;
            return aExact - bExact || String(a.name || '').localeCompare(String(b.name || ''));
        })
        .slice(0, Math.max(1, Number(limit) || 8));
}

function closeTeamCenterSuggestions() {
    const panel = document.getElementById('teamCenterSearchSuggestions');
    const input = document.getElementById('teamCenterSearchInput');
    if (panel) {
        panel.hidden = true;
        panel.innerHTML = '';
    }
    if (input) {
        input.setAttribute('aria-expanded', 'false');
        input.removeAttribute('aria-activedescendant');
    }
    teamCenterSearchActiveIndex = -1;
}

function renderTeamCenterSearchSuggestions(query = teamCenterSearchQuery) {
    const panel = document.getElementById('teamCenterSearchSuggestions');
    const input = document.getElementById('teamCenterSearchInput');
    if (!panel || !input) return;
    const matches = getTeamCenterSearchMatches(query);
    if (!String(query || '').trim() || !matches.length) {
        closeTeamCenterSuggestions();
        return;
    }
    teamCenterSearchActiveIndex = Math.min(teamCenterSearchActiveIndex, matches.length - 1);
    panel.innerHTML = matches.map((team, index) => `
        <button id="teamCenterSuggestion${index}" class="team-center-search-option ${index === teamCenterSearchActiveIndex ? 'is-active' : ''}" type="button" role="option" aria-selected="${index === teamCenterSearchActiveIndex ? 'true' : 'false'}" onmousedown="event.preventDefault()" onclick="selectTeamCenterSuggestion('${teamDetailHandlerArg(team.name)}')">
            <span><strong>${escapeHtml(team.name)}</strong><small>主教练 ${escapeHtml(team.manager || '待定')}</small></span>
            ${teamDetailLevelBadge(team.level, {compact: true})}
        </button>
    `).join('');
    panel.hidden = false;
    input.setAttribute('aria-expanded', 'true');
    if (teamCenterSearchActiveIndex >= 0) {
        input.setAttribute('aria-activedescendant', `teamCenterSuggestion${teamCenterSearchActiveIndex}`);
    } else {
        input.removeAttribute('aria-activedescendant');
    }
}

function selectTeamCenterSuggestion(teamName) {
    const normalizedName = decodeURIComponent(String(teamName || ''));
    if (!teams.some(team => team.name === normalizedName)) return;
    teamCenterSearchQuery = normalizedName;
    closeTeamCenterSuggestions();
    openTeamDetail(normalizedName);
}

function handleTeamCenterSearchKeydown(event) {
    const matches = getTeamCenterSearchMatches(event.currentTarget?.value || teamCenterSearchQuery);
    if (event.key === 'Escape') {
        closeTeamCenterSuggestions();
        return;
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        if (!matches.length) return;
        event.preventDefault();
        const direction = event.key === 'ArrowDown' ? 1 : -1;
        teamCenterSearchActiveIndex = teamCenterSearchActiveIndex < 0
            ? (direction > 0 ? 0 : matches.length - 1)
            : (teamCenterSearchActiveIndex + direction + matches.length) % matches.length;
        renderTeamCenterSearchSuggestions(event.currentTarget.value);
        return;
    }
    if (event.key === 'Enter') {
        event.preventDefault();
        const selected = matches[teamCenterSearchActiveIndex >= 0 ? teamCenterSearchActiveIndex : 0];
        if (selected) selectTeamCenterSuggestion(encodeURIComponent(selected.name));
    }
}

function teamCenterDirectoryCard(team) {
    const logo = team.logo_path
        ? `<img src="${escapeHtml(team.logo_path)}" alt="" loading="lazy">`
        : `<span>${escapeHtml(team.name.slice(0, 2).toUpperCase())}</span>`;
    const encodedName = teamDetailHandlerArg(team.name);
    return `<button class="team-center-club-card" type="button" onclick="openTeamDetail(decodeURIComponent('${encodedName}'))" aria-label="查看 ${escapeHtml(team.name)} 球队中心">
        <span class="team-center-club-crest ${team.logo_path ? 'has-logo' : ''}">${logo}</span>
        <span class="team-center-club-copy"><strong>${escapeHtml(team.name)}</strong><small>主教练 ${escapeHtml(team.manager || '待定')}</small></span>
        <span class="team-center-club-stats"><b>${teamDetailSafeNumber(team.team_size)}</b><small>球员</small></span>
        <span class="team-center-club-arrow" aria-hidden="true">${uiIconSvg('arrow-right', 'ui-icon is-small')}</span>
    </button>`;
}

function teamCenterDefaultExpandedLevel() {
    const linkedTeam = (teams || []).find(team => (
        (Number(currentCoachAccount?.team_id) > 0 && Number(team.id) === Number(currentCoachAccount.team_id))
        || (currentCoachAccount?.team_name && team.name === currentCoachAccount.team_name)
    ));
    return linkedTeam?.level || '超级';
}

function ensureTeamCenterExpandedLevel() {
    if (teamCenterExpandedInitialized) return;
    teamCenterExpandedLevels.add(teamCenterDefaultExpandedLevel());
    teamCenterExpandedInitialized = true;
}

function toggleTeamCenterLeague(level) {
    if (!window.matchMedia?.('(max-width: 700px)').matches) return;
    if (teamCenterExpandedLevels.has(level)) {
        teamCenterExpandedLevels.delete(level);
    } else {
        teamCenterExpandedLevels.add(level);
    }
    renderTeamCenterDirectory(document.getElementById('teamCenterSearchInput')?.value || '');
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
}

function renderTeamCenterDirectory(query = '') {
    const root = document.getElementById('teamCenterDirectory');
    if (!root) return;
    const normalizedQuery = String(query || '').trim().toLocaleLowerCase();
    ensureTeamCenterExpandedLevel();
    const levels = ['超级', '甲级', '乙级'];
    const sections = levels.map(level => {
        const levelTeams = teams
            .filter(team => team.level === level)
            .filter(team => !normalizedQuery || [team.name, team.manager].some(value => String(value || '').toLocaleLowerCase().includes(normalizedQuery)))
            .sort((a, b) => a.name.localeCompare(b.name));
        if (!levelTeams.length) return '';
        const expanded = Boolean(normalizedQuery) || teamCenterExpandedLevels.has(level);
        const contentId = `teamCenterLeague${level}`;
        return `<section class="team-center-league-group ${expanded ? 'is-expanded' : 'is-collapsed'} ${normalizedQuery ? 'is-searching' : ''}">
            <header><button class="team-center-league-toggle" type="button" onclick="toggleTeamCenterLeague('${level}')" aria-expanded="${expanded ? 'true' : 'false'}" aria-controls="${contentId}"><span>${teamDetailLevelBadge(level, {compact: true})}<span class="team-center-league-heading"><strong>${level}联赛</strong><small>${levelTeams.length} 支球队</small></span></span><i aria-hidden="true"><svg viewBox="0 0 24 24" focusable="false"><path d="m7 10 5 5 5-5"/></svg></i></button></header>
            <div class="team-center-club-grid" id="${contentId}">${levelTeams.map(teamCenterDirectoryCard).join('')}</div>
        </section>`;
    }).join('');
    root.innerHTML = sections || `<div class="team-center-no-results"><strong>没有找到匹配的球队</strong><p>试试输入球队名或主教练名称。</p><button type="button" onclick="clearTeamCenterSearch()">清除搜索</button></div>`;
}

function filterTeamCenterDirectory(query) {
    teamCenterSearchQuery = String(query || '');
    teamCenterSearchActiveIndex = -1;
    renderTeamCenterDirectory(teamCenterSearchQuery);
    renderTeamCenterSearchSuggestions(teamCenterSearchQuery);
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
}

function clearTeamCenterSearch() {
    const input = document.getElementById('teamCenterSearchInput');
    if (input) {
        input.value = '';
        input.focus();
    }
    teamCenterSearchQuery = '';
    closeTeamCenterSuggestions();
    renderTeamCenterDirectory();
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
}

function openSelectedTeamCenter() {
    const input = document.getElementById('teamCenterSearchInput');
    const query = String(input?.value || teamCenterSearchQuery).trim();
    const exactMatch = teams.find(team => String(team.name || '').toLocaleLowerCase() === query.toLocaleLowerCase());
    const selected = exactMatch || getTeamCenterSearchMatches(query, 1)[0];
    if (selected) {
        selectTeamCenterSuggestion(encodeURIComponent(selected.name));
        return;
    }
    input?.focus();
    renderTeamCenterSearchSuggestions(query);
}

function renderTeamCenterLanding() {
    const root = document.getElementById('teamDetailRoot');
    if (!root) return;
    root.innerHTML = `<div class="team-center-landing">
        <section class="team-center-welcome surface-card">
            <div class="team-center-welcome-copy"><span class="panel-kicker">HEIGO Team Center</span><div class="team-center-welcome-title-row"><h1>选择你的球队</h1>${teamCenterCoachAccessMarkup()}</div><p>从 54 支球队中选择一队，查看完整阵容、HEIGO 战力、赛程表现与纪律状态。</p></div>
            <div class="team-center-welcome-count" aria-label="球队中心共有54支球队"><strong>${teams.length || 54}</strong><span>支球队</span>${renderLeagueTierSet()}</div>
        </section>
        <section class="team-center-picker surface-card" aria-labelledby="teamCenterPickerTitle">
            <div class="team-center-picker-heading"><span class="panel-kicker">Find a Club</span><h2 id="teamCenterPickerTitle">查找球队</h2></div>
            <div class="team-center-search-combobox">
                <label class="team-center-search-field" for="teamCenterSearchInput"><span>搜索球队或主教练</span><input id="teamCenterSearchInput" type="search" role="combobox" aria-autocomplete="list" aria-controls="teamCenterSearchSuggestions" aria-expanded="false" autocomplete="off" placeholder="输入球队名或主教练" value="${escapeHtml(teamCenterSearchQuery)}" oninput="filterTeamCenterDirectory(this.value)" onfocus="renderTeamCenterSearchSuggestions(this.value)" onblur="window.setTimeout(closeTeamCenterSuggestions, 120)" onkeydown="handleTeamCenterSearchKeydown(event)"></label>
                <div id="teamCenterSearchSuggestions" class="team-center-search-suggestions" role="listbox" aria-label="球队搜索建议" hidden></div>
            </div>
            <button class="btn btn-primary team-center-enter-button" type="button" onclick="openSelectedTeamCenter()">进入球队中心</button>
        </section>
        <div id="teamCenterDirectory" class="team-center-directory" aria-live="polite"></div>
    </div>`;
    renderTeamCenterDirectory(teamCenterSearchQuery);
}

function renderTeamDetailLoaded(data) {
    const root = document.getElementById('teamDetailRoot');
    if (!root || data.team.name !== currentTeamDetailName) return;
    const {team, players, standings, matchesPayload, suspensionsPayload, playerRankingsPayload, powerPayload, lineupPayload, teamPowerSummaries, cupOutlookPayload} = data;
    const allPowerItems = Array.isArray(powerPayload?.items) ? powerPayload.items : [];
    const powerByUid = teamDetailSelectPowerShapes(players, allPowerItems);
    const powerItems = [...powerByUid.values()].sort((a, b) => teamDetailSafeNumber(b.heigo_power) - teamDetailSafeNumber(a.heigo_power));
    const standingRows = Array.isArray(standings?.rows) ? standings.rows : [];
    const standing = standingRows.find(row => row.team_name === team.name);
    const matches = teamDetailGetMatches(matchesPayload, team);
    const playedMatches = matches.filter(match => teamDetailHasScore(match.home_score) && teamDetailHasScore(match.away_score)).sort((a, b) => teamDetailSafeNumber(b.round_no) - teamDetailSafeNumber(a.round_no));
    const rawUpcomingMatches = matches.filter(match => !teamDetailHasScore(match.home_score) || !teamDetailHasScore(match.away_score)).sort((a, b) => teamDetailSafeNumber(a.round_no) - teamDetailSafeNumber(b.round_no));
    const teamSuspensions = (Array.isArray(suspensionsPayload?.teams) ? suspensionsPayload.teams : []).find(item => item.team_name === team.name);
    const upcomingMatches = teamDetailEffectiveUpcomingMatches(rawUpcomingMatches, teamSuspensions?.progress);
    const playedSeries = teamDetailGroupMatchSeries(playedMatches, team, 'desc');
    const upcomingFourSeries = teamDetailGroupMatchSeries(upcomingMatches.slice(0, 4), team, 'asc');
    const suspensionFreshness = teamDetailSuspensionFreshness(teamSuspensions);
    const estimatedRosterAverage = powerItems.length ? powerItems.reduce((sum, item) => sum + teamDetailSafeNumber(item.heigo_power), 0) / powerItems.length : null;
    const wageCap = teamDetailGetWageCap(team);
    const lineupPlayers = teamDetailPlayersWithPower(players, powerByUid, team.name, teamSuspensions);
    const previewPicks = teamDetailPreviewPicks(lineupPlayers, lineupPayload);
    const lineupAverage = teamDetailAveragePowerForPicks(previewPicks, powerByUid);
    const levelPowerRows = (Array.isArray(teamPowerSummaries?.items) ? teamPowerSummaries.items : []).filter(item => item.level === team.level);
    const teamPowerSummary = levelPowerRows.find(item => Number(item.team_id) === Number(team.id));
    const hasRosterSummary = teamPowerSummary?.roster_average !== null && teamPowerSummary?.roster_average !== undefined && Number.isFinite(Number(teamPowerSummary.roster_average));
    const hasLineupSummary = teamPowerSummary?.lineup_average !== null && teamPowerSummary?.lineup_average !== undefined && Number.isFinite(Number(teamPowerSummary.lineup_average));
    const rosterAverage = hasRosterSummary ? Number(teamPowerSummary.roster_average) : estimatedRosterAverage;
    const previewAverage = hasLineupSummary ? Number(teamPowerSummary.lineup_average) : lineupAverage.value;
    const unavailableLineupPlayers = lineupPlayers.filter(player => player.is_unavailable);
    data.powerByUid = powerByUid;
    data.avgHeigo = rosterAverage;
    data.lineupPlayers = lineupPlayers;
    currentTeamDetailData = data;
    const logo = team.logo_path
        ? `<img src="${escapeHtml(team.logo_path)}" alt="${escapeHtml(team.name)}队徽">`
        : `<span>${escapeHtml(team.name.slice(0, 2).toUpperCase())}</span>`;
    const encodedName = teamDetailHandlerArg(team.name);

    root.innerHTML = `${teamDetailTeamSwitcher(team)}<div class="team-detail-toolbar">
        <button class="team-detail-back" type="button" onclick="closeTeamDetail()" aria-label="返回上一页"><span aria-hidden="true">${uiIconSvg('arrow-left', 'ui-icon is-small')}</span> 返回</button>
        <div class="team-detail-toolbar-meta">${teamDetailLevelBadge(team.level)}<span>数据版本 ${escapeHtml(powerPayload?.data_version || currentAttributeVersion || '--')}</span></div>
    </div>
    <section class="team-hero surface-card">
        <div class="team-hero-identity"><div class="team-hero-crest ${team.logo_path ? 'has-logo' : ''}">${logo}</div><div><span class="panel-kicker">HEIGO Team Hub</span><h1>${escapeHtml(team.name)}</h1><p>主教练 ${renderCoachProfileLink(team.manager || '待定', 'coach-profile-link team-hero-coach')}</p></div></div>
        <div class="team-hero-standing"><div class="team-hero-form">${teamDetailRecentLeagueForm(playedMatches, team)}</div><div><span>联赛排名</span><strong>${standing ? `#${standing.rank}` : '--'}</strong></div><div><span>积分</span><strong>${standing ? standing.points : '--'}</strong></div><div><span>战绩</span><strong>${standing ? `${standing.wins}-${standing.draws}-${standing.losses}` : '--'}</strong></div></div>
    </section>
    <section class="team-stat-strip">
        <article><span>一线队人数</span><strong>${teamDetailSafeNumber(team.team_size, players.length)}</strong><small>${teamDetailSafeNumber(team.gk_count)} 名门将</small></article>
        <article><span>球队工资 / 工资帽</span><strong>${teamDetailFormatNumber(team.final_wage, 2)}M / ${teamDetailFormatNumber(wageCap, 2)}M</strong><small>球员工资 ${teamDetailFormatNumber(team.wage, 2)}M</small></article>
        <article><span>平均 CA / PA</span><strong>${teamDetailFormatNumber(team.avg_ca, 1)} / ${teamDetailFormatNumber(team.avg_pa, 1)}</strong><small>总成长 ${teamDetailFormatNumber(team.total_growth)}</small></article>
        <article class="team-power-summary-stat"><span class="team-power-summary-title">平均 HEIGO 战力</span><div class="team-power-summary-values">
            <section><span>阵型预览 · 估计值</span><strong>${previewAverage !== null ? teamDetailFormatNumber(previewAverage, 2) : '--'}</strong><small>${teamDetailPowerRankLabel(team.level, teamPowerSummary?.lineup_rank, levelPowerRows.length)}</small></section>
            <section><span>全队球员 · 估计值</span><strong>${rosterAverage !== null ? teamDetailFormatNumber(rosterAverage, 2) : '--'}</strong><small>${teamDetailPowerRankLabel(team.level, teamPowerSummary?.roster_rank, levelPowerRows.length)}</small></section>
        </div></article>
    </section>
    <div class="team-detail-primary-grid">
        <section class="team-panel team-lineup-panel surface-card"><div class="team-panel-header"><div><span class="panel-kicker">Starting XI</span><h2>11 人阵容预览</h2><p class="team-lineup-explain">${lineupPayload?.is_saved ? '主教练自定义阵容' : '当前展示系统推荐阵容，主教练可保存自定义阵型与首发。'}</p></div><div class="team-panel-actions"><button class="team-panel-link team-lineup-action team-lineup-copy" type="button" onclick="copyTeamLineupImage()">复制阵容图</button><button class="team-panel-link team-lineup-action team-lineup-edit" type="button" onclick="openTeamLineupEditor()">${lineupPayload?.can_edit ? '编辑阵容' : '查看阵容'} →</button></div></div>${unavailableLineupPlayers.length ? `<div class="team-lineup-suspension-alert"><strong>下场不可用</strong><span>${unavailableLineupPlayers.map(player => `${escapeHtml(player.name)}（${escapeHtml(player.suspension_label)}）`).join('、')}</span></div>` : ''}${renderRosterFormationPreview({teamName: team.name, players: lineupPlayers, formation: lineupPayload?.formation || '4-3-3', picks: lineupPayload?.picks || {}})}</section>
        <aside class="team-detail-side-stack">
            ${teamDetailJourneyPanel(team, upcomingFourSeries, cupOutlookPayload)}
            <section class="team-panel surface-card"><div class="team-panel-header"><div><span class="panel-kicker">Availability</span><h2>纪律状态</h2></div></div>${teamDetailDiscipline(teamSuspensions, suspensionFreshness)}</section>
        </aside>
    </div>
    <div class="team-detail-secondary-grid">
        <section class="team-panel team-performance-panel surface-card"><div class="team-panel-header team-performance-header"><div><span class="panel-kicker">Team Leaders</span><h2>队内表现</h2></div><span class="team-panel-note">比赛数据与球员榜同步</span></div><div class="team-performance-grid">
            <section class="team-performance-section team-power-core-section"><div class="team-performance-section-header"><div><span>Power Core</span><h3>队内战力核心</h3></div><button class="team-panel-link team-panel-link-compact" type="button" onclick="openTeamPowerRanking(decodeURIComponent('${encodedName}'))">完整战力榜 →</button></div>${teamDetailPowerCore(powerItems)}</section>
            <section class="team-performance-section team-player-leaders-section"><div class="team-performance-section-header"><div><span>Match Leaders</span><h3>队内球员榜</h3></div>${teamDetailPlayerLeaderTabs()}</div><div id="teamPlayerLeadersContent">${teamDetailPlayerLeaders(playerRankingsPayload)}</div></section>
        </div></section>
        <section class="team-panel surface-card"><div class="team-panel-header"><div><span class="panel-kicker">Form</span><h2>最近赛果</h2></div><span class="team-panel-note">按同一对手两轮合并</span></div><div class="team-match-stack">${playedSeries.slice(0, 3).map(series => teamDetailMatchSeriesCard(series, team, true)).join('') || '<div class="team-detail-empty-inline">导入赛程暂未产生赛果。</div>'}</div></section>
    </div>
    <section class="team-panel team-roster-panel surface-card"><div class="team-panel-header team-roster-panel-header"><div><span class="panel-kicker">First Team · ${players.length}</span><h2>完整球队名单</h2><p class="team-roster-explain">简略版突出战力，详细版完整展示名单字段，卡片版适合移动浏览。</p></div><div class="team-roster-header-actions">${teamDetailRosterViewSwitch()}<button class="team-panel-link team-roster-copy-button" type="button" onclick="copyTeamRosterImage()">复制球队名单图</button></div></div><div id="teamRosterViewBody">${teamDetailRosterView(players, powerByUid)}</div></section>`;
}

async function loadTeamDetailData(teamName, options = {}) {
    const cached = options.force === true ? null : getCachedTeamDetail(teamName);
    if (cached) return cached;
    const team = teams.find(item => item.name === teamName);
    if (!team) throw new Error(`未找到球队：${teamName}`);
    const payload = await fetchJsonOrThrow(`/api/teams/${team.id}/center`, {signal: options.signal});
    const data = {
        team: payload.team || team,
        players: Array.isArray(payload.players) ? payload.players : [],
        standings: payload.standings,
        matchesPayload: payload.matches,
        suspensionsPayload: payload.suspensions,
        playerRankingsPayload: payload.player_rankings || {levels: [team.level], rows: [], coverage: []},
        powerPayload: payload.power,
        lineupPayload: payload.lineup || {team_id: team.id, team_name: team.name, formation: '4-3-3', picks: {}, is_saved: false, can_edit: false},
        teamPowerSummaries: payload.team_power_summaries,
        cupOutlookPayload: payload.cup_outlook || {team_id: team.id, team_name: team.name, competitions: []},
    };
    return setCachedTeamDetail(teamName, data);
}

async function renderTeamDetail(options = {}) {
    const root = document.getElementById('teamDetailRoot');
    if (!root) return;
    if (!currentTeamDetailName) {
        teamDetailAbortController?.abort();
        teamDetailAbortController = null;
        await ensureTeamCenterCoachAuth();
        renderTeamCenterLanding();
        return;
    }
    teamDetailAbortController?.abort();
    const abortController = new AbortController();
    teamDetailAbortController = abortController;
    const sequence = ++teamDetailLoadSequence;
    root.innerHTML = `<div class="team-detail-skeleton" aria-label="正在加载 ${escapeHtml(currentTeamDetailName)}"><div class="team-skeleton-hero"></div><div class="team-skeleton-stats"></div><div class="team-skeleton-grid"><span></span><span></span></div></div>`;
    try {
        const data = await loadTeamDetailData(currentTeamDetailName, {...options, signal: abortController.signal});
        if (sequence !== teamDetailLoadSequence) return;
        renderTeamDetailLoaded(data);
    } catch (error) {
        if (error?.name === 'AbortError') return;
        console.error('球队详情加载失败:', error);
        if (sequence !== teamDetailLoadSequence) return;
        root.innerHTML = renderUiState({tone: 'danger', title: '球队详情暂时无法加载', message: error.message || '请稍后重试。', actionLabel: '重新加载', actionClass: 'btn-primary', actionOnclick: 'renderTeamDetail({force:true})'});
    } finally {
        if (teamDetailAbortController === abortController) teamDetailAbortController = null;
    }
}

async function openTeamDetail(teamName, options = {}) {
    if (String(teamName || '').trim() !== currentTeamDetailName) {
        currentTeamJourneyView = 'league';
        currentTeamPlayerLeaderMetric = 'goals';
    }
    currentTeamDetailName = String(teamName || '').trim();
    await showTab('team', options.triggerElement || null, {syncHistory: false});
    window.scrollTo({top: 0, behavior: options.smooth === false ? 'auto' : 'smooth'});
    if (options.pushHistory !== false) syncAppHistory(options.historyMode || 'push');
}

async function switchTeamCenter(teamName) {
    if (!teams.some(team => team.name === teamName) || teamName === currentTeamDetailName) return;
    await openTeamDetail(teamName, {historyMode: 'replace', smooth: false});
}

async function shiftTeamCenter(direction) {
    if (!teams.length) return;
    const levels = ['超级', '甲级', '乙级'];
    const orderedTeams = levels.flatMap(level => teams.filter(team => team.level === level).sort((a, b) => a.name.localeCompare(b.name)));
    const index = Math.max(0, orderedTeams.findIndex(team => team.name === currentTeamDetailName));
    const nextIndex = (index + Number(direction || 0) + orderedTeams.length) % orderedTeams.length;
    await switchTeamCenter(orderedTeams[nextIndex].name);
}

function closeTeamDetail() {
    if (canUseAppHistoryBack()) {
        history.back();
        return;
    }
    openTeamCenter({historyMode: 'replace', smooth: false});
}

async function openTeamPowerRanking(teamName) {
    await showTab('database', null, {syncHistory: false});
    if (typeof currentDatabaseSubtab !== 'undefined') currentDatabaseSubtab = 'power';
    if (typeof syncDatabaseSubtabUI === 'function') syncDatabaseSubtabUI();
    if (typeof populatePowerRankingTeamSelect === 'function') populatePowerRankingTeamSelect();
    const select = document.getElementById('dbPowerTeamSelect');
    if (select) select.value = teamName;
    if (typeof loadPowerRanking === 'function') await loadPowerRanking({pushHistory: false});
    syncAppHistory('push');
}

async function openTeamSchedule(level) {
    await showTab('competition', null, {syncHistory: false});
    if (typeof currentCompetitionLevel !== 'undefined') currentCompetitionLevel = level || '超级';
    if (typeof showCompetitionSubtab === 'function') showCompetitionSubtab('schedule');
    syncAppHistory('push');
}

async function openTeamCupJourney(competition, phase = 'group') {
    await showTab('competition', null, {syncHistory: false});
    if (typeof currentCompetitionLevel !== 'undefined') currentCompetitionLevel = competition || '冠军杯';
    if (typeof currentCupPhase !== 'undefined') currentCupPhase = phase === 'group' ? 'group' : 'knockout';
    if (phase === 'group') {
        if (typeof currentCupGroupScheduleView !== 'undefined') currentCupGroupScheduleView = 'results';
        if (typeof showCompetitionSubtab === 'function') showCompetitionSubtab('schedule');
    } else if (typeof showCompetitionSubtab === 'function') {
        showCompetitionSubtab('standings');
    }
    syncAppHistory('push');
}
