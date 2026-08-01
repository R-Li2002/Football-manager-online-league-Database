let currentTeamDetailName = '';
let teamDetailLoadSequence = 0;
let currentTeamDetailData = null;
let teamRosterExportBusy = false;
let teamLineupExportBusy = false;
let teamPowerSummariesPromise = null;
let teamCenterCoachAuthReady = false;
let teamCenterCoachAuthPromise = null;
let teamRosterCopyToastTimer = null;
let currentTeamJourneyView = 'league';
const teamDetailCache = new Map();
const TEAM_ROSTER_VIEW_MODES = new Set(['compact', 'detail', 'cards']);
const teamCenterExpandedLevels = new Set();
let teamCenterExpandedInitialized = false;

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
    return `<article class="team-match-card ${resultClass} ${compact ? 'is-compact' : ''}">
        <div class="team-match-round"><span>${escapeHtml(match.level || '')}</span> 第 ${teamDetailSafeNumber(match.round_no)} 轮</div>
        <div class="team-match-opponent"><small class="team-match-venue ${isHome ? 'is-home' : 'is-away'}">${isHome ? '主场' : '客场'}</small><strong>${escapeHtml(opponent || '-')}</strong></div>
        ${resultText ? `<div class="team-match-score">${resultText}</div>` : ''}
    </article>`;
}

function teamDetailMatchSeriesCard(series, team, compact = false) {
    if (!Array.isArray(series) || !series.length) return '<div class="team-detail-muted">暂无比赛数据</div>';
    if (series.length === 1) return teamDetailMatchCard(series[0], team, compact);
    const metas = series.map(match => ({match, ...teamDetailMatchMeta(match, team)}));
    const opponent = metas[0].opponent;
    const rounds = metas.map(item => teamDetailSafeNumber(item.match.round_no));
    return `<article class="team-match-series-card ${compact ? 'is-compact' : ''}">
        <div class="team-match-series-head"><div><span>${escapeHtml(series[0].level || '')}</span><small>第 ${Math.min(...rounds)}–${Math.max(...rounds)} 轮</small></div><strong>${escapeHtml(opponent || '-')}</strong></div>
        <div class="team-match-series-legs">${metas.map(item => {
            const resultClass = !item.played ? 'is-upcoming' : item.ownScore > item.opponentScore ? 'is-win' : item.ownScore < item.opponentScore ? 'is-loss' : 'is-draw';
            return `<div class="team-match-series-leg ${resultClass}"><span class="team-match-leg-meta"><small>第 ${teamDetailSafeNumber(item.match.round_no)} 轮</small><b class="team-match-venue ${item.isHome ? 'is-home' : 'is-away'}">${item.isHome ? '主场' : '客场'}</b></span>${item.played ? `<strong>${item.ownScore} : ${item.opponentScore}</strong>` : ''}</div>`;
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
    return `<div class="team-cup-next-row"><span><small>${escapeHtml(roundLabel || '杯赛')}</small><b class="team-match-venue ${match.is_home ? 'is-home' : 'is-away'}">${match.is_home ? '主场' : '客场'}</b></span><strong>${escapeHtml(match.opponent_team_name || '待定')}</strong></div>`;
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
    const knockoutNext = item.phase === 'knockout'
        ? `<div class="team-cup-next"><div class="team-cup-section-title"><strong>下一场</strong><small>当前淘汰赛阶段</small></div>${(item.next_matches || []).map(match => teamDetailCupFixtureCard({...match, phase: item.phase})).join('') || '<div class="team-detail-empty-inline">当前没有待进行的杯赛。</div>'}</div>`
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
}

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
    return `<div class="team-power-core-list">${items.slice(0, 5).map((item, index) => `<article class="team-power-core-item">
        <span class="team-power-rank">${String(index + 1).padStart(2, '0')}</span>
        <div class="team-power-player">${teamDetailPlayerButton(item)}<small>${escapeHtml(item.position || '-')} · 当前 CA ${teamDetailSafeNumber(item.league_ca, item.ca)} ${teamDetailGrowthBadge(item)}</small></div>
        <div class="team-power-metric team-power-weighted"><strong>${teamDetailFormatNumber(item.weighted_power, 2)}</strong><span>加权战力</span></div>
        <div class="team-power-metric team-power-heigo"><strong>${teamDetailFormatNumber(item.heigo_power, 2)}</strong><span>HEIGO 战力</span><small>前 ${teamDetailFormatNumber(item.top_percent, 2)}%</small></div>
    </article>`).join('')}</div>`;
}

function teamDetailSuspensionFreshness(team, siteNotesPayload, nextMatch) {
    const notes = Array.isArray(siteNotesPayload) ? siteNotesPayload : [];
    const teamKey = `competition.suspensions.team.${Number(team?.id)}`;
    const levelKey = `competition.suspensions.${String(team?.level || '')}`;
    const teamNote = notes.find(item => item?.key === teamKey && item.round_no !== null && item.round_no !== undefined);
    const levelNote = notes.find(item => item?.key === levelKey && item.round_no !== null && item.round_no !== undefined);
    const marker = teamNote || levelNote;
    const updatedRound = marker ? Number(marker.round_no) : null;
    const nextRound = nextMatch ? teamDetailSafeNumber(nextMatch.round_no) : null;
    const hasUpdatedRound = Number.isInteger(updatedRound) && updatedRound >= 0;

    if (!hasUpdatedRound) {
        return {
            state: 'unknown',
            title: '伤停轮次待确认',
            detail: nextRound ? `下一场为第 ${nextRound} 轮，尚未标注伤停核对轮次` : '尚未标注伤停核对轮次',
        };
    }
    if (!nextRound) {
        return {
            state: 'current',
            title: updatedRound > 0 ? `伤停已核对至第 ${updatedRound} 轮` : '已完成赛季初伤停确认',
            detail: '当前没有待进行的联赛比赛',
        };
    }
    if (updatedRound < nextRound - 1) {
        return {
            state: 'stale',
            title: `伤停仅核对至第 ${updatedRound} 轮`,
            detail: `下一场为第 ${nextRound} 轮，落后 ${nextRound - updatedRound - 1} 轮未确认`,
        };
    }
    const detail = updatedRound === nextRound - 1
        ? `与下一场第 ${nextRound} 轮匹配`
        : `已覆盖下一场第 ${nextRound} 轮`;
    return {
        state: 'current',
        title: updatedRound > 0 ? `伤停已核对至第 ${updatedRound} 轮` : '已完成赛季初伤停确认',
        detail,
    };
}

function teamDetailDiscipline(teamSuspensions, freshness) {
    const status = freshness || {state: 'unknown', title: '伤停轮次待确认', detail: '暂时无法判断数据时效'};
    const freshnessMarkup = `<div class="team-discipline-freshness is-${escapeHtml(status.state)}"><span aria-hidden="true">${status.state === 'current' ? '✓' : status.state === 'stale' ? '!' : '?'}</span><div><strong>${escapeHtml(status.title)}</strong><small>${escapeHtml(status.detail)}</small></div></div>`;
    if (!teamSuspensions) return `${freshnessMarkup}<div class="team-detail-empty-inline">暂无纪律数据。</div>`;
    const sections = [
        ['停赛', teamSuspensions.suspended || [], 'danger'],
        ['两黄', teamSuspensions.two_yellows || [], 'warning'],
        ['一黄', teamSuspensions.one_yellow || [], 'neutral'],
    ];
    const hasAny = sections.some(([, items]) => items.length);
    if (!hasAny) {
        const clearTitle = status.state === 'current' ? '阵容可用' : '暂无已登记伤停';
        const clearDetail = status.state === 'current' ? '暂无黄牌累积或停赛记录' : '伤停轮次未匹配，阵容状态仍需确认';
        return `${freshnessMarkup}<div class="team-discipline-clear is-${escapeHtml(status.state)}"><span>${status.state === 'current' ? '✓' : '!'}</span><div><strong>${clearTitle}</strong><small>${clearDetail}</small></div></div>`;
    }
    return `${freshnessMarkup}<div class="team-discipline-list">${sections.map(([label, items, tone]) => `<div class="team-discipline-row is-${tone}"><span>${label}</span><strong>${items.length}</strong><p>${items.map(item => escapeHtml(item.player_name || item.name || String(item))).join('、') || '无'}</p></div>`).join('')}</div>`;
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

function teamDetailPlayersWithPower(players, powerByUid, teamName) {
    return players.map(player => ({
        ...player,
        team_name: player.team_name || teamName,
        heigo_power: powerByUid.has(Number(player.uid)) ? teamDetailSafeNumber(powerByUid.get(Number(player.uid)).heigo_power) : null,
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
    teamDetailCache.set(currentTeamDetailData.team.name, currentTeamDetailData);
    renderTeamDetailLoaded(currentTeamDetailData);
    loadTeamPowerSummaries({force: true}).then(powerSummaries => {
        if (!currentTeamDetailData || Number(payload?.team_id) !== Number(currentTeamDetailData.team.id)) return;
        currentTeamDetailData.teamPowerSummaries = powerSummaries;
        teamDetailCache.set(currentTeamDetailData.team.name, currentTeamDetailData);
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
            showModal('复制成功', '阵容图片已复制到剪贴板。');
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
            showModal('复制成功', '球队名单图片已复制到剪贴板。');
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

function teamCenterLandingOptions() {
    const levels = ['超级', '甲级', '乙级'];
    return levels.map(level => {
        const levelTeams = teams.filter(team => team.level === level).sort((a, b) => a.name.localeCompare(b.name));
        return `<optgroup label="${level}">${levelTeams.map(team => `<option value="${escapeHtml(team.name)}">${escapeHtml(team.name)}</option>`).join('')}</optgroup>`;
    }).join('');
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
    renderTeamCenterDirectory(query);
}

function clearTeamCenterSearch() {
    const input = document.getElementById('teamCenterSearchInput');
    if (input) {
        input.value = '';
        input.focus();
    }
    renderTeamCenterDirectory();
}

function openSelectedTeamCenter() {
    const select = document.getElementById('teamCenterLandingSelect');
    if (!select?.value) return;
    openTeamDetail(select.value);
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
            <label class="team-center-search-field" for="teamCenterSearchInput"><span>搜索球队或主教练</span><input id="teamCenterSearchInput" type="search" autocomplete="off" placeholder="输入名称快速筛选" oninput="filterTeamCenterDirectory(this.value)"></label>
            <span class="team-center-picker-or">或</span>
            <label class="team-center-select-field" for="teamCenterLandingSelect"><span>直接选择球队</span><select id="teamCenterLandingSelect"><option value="">请选择球队</option>${teamCenterLandingOptions()}</select></label>
            <button class="btn btn-primary team-center-enter-button" type="button" onclick="openSelectedTeamCenter()">进入球队中心</button>
        </section>
        <div id="teamCenterDirectory" class="team-center-directory" aria-live="polite"></div>
    </div>`;
    renderTeamCenterDirectory();
}

function renderTeamDetailLoaded(data) {
    const root = document.getElementById('teamDetailRoot');
    if (!root || data.team.name !== currentTeamDetailName) return;
    const {team, players, standings, matchesPayload, suspensionsPayload, powerPayload, lineupPayload, teamPowerSummaries, cupOutlookPayload, siteNotesPayload} = data;
    const allPowerItems = Array.isArray(powerPayload?.items) ? powerPayload.items : [];
    const powerByUid = teamDetailSelectPowerShapes(players, allPowerItems);
    const powerItems = [...powerByUid.values()].sort((a, b) => teamDetailSafeNumber(b.heigo_power) - teamDetailSafeNumber(a.heigo_power));
    const standingRows = Array.isArray(standings?.rows) ? standings.rows : [];
    const standing = standingRows.find(row => row.team_name === team.name);
    const matches = teamDetailGetMatches(matchesPayload, team);
    const playedMatches = matches.filter(match => teamDetailHasScore(match.home_score) && teamDetailHasScore(match.away_score)).sort((a, b) => teamDetailSafeNumber(b.round_no) - teamDetailSafeNumber(a.round_no));
    const upcomingMatches = matches.filter(match => !teamDetailHasScore(match.home_score) || !teamDetailHasScore(match.away_score)).sort((a, b) => teamDetailSafeNumber(a.round_no) - teamDetailSafeNumber(b.round_no));
    const playedSeries = teamDetailGroupMatchSeries(playedMatches, team, 'desc');
    const upcomingFourSeries = teamDetailGroupMatchSeries(upcomingMatches.slice(0, 4), team, 'asc');
    const teamSuspensions = (Array.isArray(suspensionsPayload?.teams) ? suspensionsPayload.teams : []).find(item => item.team_name === team.name);
    const suspensionFreshness = teamDetailSuspensionFreshness(team, siteNotesPayload, upcomingMatches[0]);
    const estimatedRosterAverage = powerItems.length ? powerItems.reduce((sum, item) => sum + teamDetailSafeNumber(item.heigo_power), 0) / powerItems.length : null;
    const wageCap = teamDetailGetWageCap(team);
    const lineupPlayers = teamDetailPlayersWithPower(players, powerByUid, team.name);
    const previewPicks = teamDetailPreviewPicks(lineupPlayers, lineupPayload);
    const lineupAverage = teamDetailAveragePowerForPicks(previewPicks, powerByUid);
    const levelPowerRows = (Array.isArray(teamPowerSummaries?.items) ? teamPowerSummaries.items : []).filter(item => item.level === team.level);
    const teamPowerSummary = levelPowerRows.find(item => Number(item.team_id) === Number(team.id));
    const hasRosterSummary = teamPowerSummary?.roster_average !== null && teamPowerSummary?.roster_average !== undefined && Number.isFinite(Number(teamPowerSummary.roster_average));
    const hasLineupSummary = teamPowerSummary?.lineup_average !== null && teamPowerSummary?.lineup_average !== undefined && Number.isFinite(Number(teamPowerSummary.lineup_average));
    const rosterAverage = hasRosterSummary ? Number(teamPowerSummary.roster_average) : estimatedRosterAverage;
    const previewAverage = hasLineupSummary ? Number(teamPowerSummary.lineup_average) : lineupAverage.value;
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
        <div class="team-hero-standing"><div><span>联赛排名</span><strong>${standing ? `#${standing.rank}` : '--'}</strong></div><div><span>积分</span><strong>${standing ? standing.points : '--'}</strong></div><div><span>战绩</span><strong>${standing ? `${standing.wins}-${standing.draws}-${standing.losses}` : '--'}</strong></div></div>
    </section>
    <section class="team-stat-strip">
        <article><span>一线队人数</span><strong>${teamDetailSafeNumber(team.team_size, players.length)}</strong><small>${teamDetailSafeNumber(team.gk_count)} 名门将</small></article>
        <article><span>球队工资</span><strong>${teamDetailFormatNumber(team.final_wage, 2)}M</strong><small>工资帽 ${teamDetailFormatNumber(wageCap, 2)}M · 球员工资 ${teamDetailFormatNumber(team.wage, 2)}M</small></article>
        <article><span>平均 CA / PA</span><strong>${teamDetailFormatNumber(team.avg_ca, 1)} / ${teamDetailFormatNumber(team.avg_pa, 1)}</strong><small>总成长 ${teamDetailFormatNumber(team.total_growth)}</small></article>
        <article class="team-power-summary-stat"><span class="team-power-summary-title">平均 HEIGO 战力</span><div class="team-power-summary-values">
            <section><span>阵型预览 · 估计值</span><strong>${previewAverage !== null ? teamDetailFormatNumber(previewAverage, 2) : '--'}</strong><small>${teamDetailPowerRankLabel(team.level, teamPowerSummary?.lineup_rank, levelPowerRows.length)}</small></section>
            <section><span>全队球员 · 估计值</span><strong>${rosterAverage !== null ? teamDetailFormatNumber(rosterAverage, 2) : '--'}</strong><small>${teamDetailPowerRankLabel(team.level, teamPowerSummary?.roster_rank, levelPowerRows.length)}</small></section>
        </div></article>
    </section>
    <div class="team-detail-primary-grid">
        <section class="team-panel team-lineup-panel surface-card"><div class="team-panel-header"><div><span class="panel-kicker">Starting XI</span><h2>11 人阵容预览</h2><p class="team-lineup-explain">${lineupPayload?.is_saved ? '主教练自定义阵容' : '当前展示系统推荐阵容，主教练可保存自定义阵型与首发。'}</p></div><div class="team-panel-actions"><button class="team-panel-link team-lineup-action team-lineup-copy" type="button" onclick="copyTeamLineupImage()">复制阵容图</button><button class="team-panel-link team-lineup-action team-lineup-edit" type="button" onclick="openTeamLineupEditor()">${lineupPayload?.can_edit ? '编辑阵容' : '查看阵容'} →</button></div></div>${renderRosterFormationPreview({teamName: team.name, players: lineupPlayers, formation: lineupPayload?.formation || '4-3-3', picks: lineupPayload?.picks || {}})}</section>
        <aside class="team-detail-side-stack">
            ${teamDetailJourneyPanel(team, upcomingFourSeries, cupOutlookPayload)}
            <section class="team-panel surface-card"><div class="team-panel-header"><div><span class="panel-kicker">Availability</span><h2>纪律状态</h2></div></div>${teamDetailDiscipline(teamSuspensions, suspensionFreshness)}</section>
        </aside>
    </div>
    <div class="team-detail-secondary-grid">
        <section class="team-panel surface-card"><div class="team-panel-header"><div><span class="panel-kicker">Power Core</span><h2>队内战力核心</h2></div><button class="team-panel-link" type="button" onclick="openTeamPowerRanking(decodeURIComponent('${encodedName}'))">查看战力榜 →</button></div>${teamDetailPowerCore(powerItems)}</section>
        <section class="team-panel surface-card"><div class="team-panel-header"><div><span class="panel-kicker">Form</span><h2>最近赛果</h2></div><span class="team-panel-note">按同一对手两轮合并</span></div><div class="team-match-stack">${playedSeries.slice(0, 3).map(series => teamDetailMatchSeriesCard(series, team, true)).join('') || '<div class="team-detail-empty-inline">导入赛程暂未产生赛果。</div>'}</div></section>
    </div>
    <section class="team-panel team-roster-panel surface-card"><div class="team-panel-header team-roster-panel-header"><div><span class="panel-kicker">First Team · ${players.length}</span><h2>完整球队名单</h2><p class="team-roster-explain">简略版突出战力，详细版完整展示名单字段，卡片版适合移动浏览。</p></div><div class="team-roster-header-actions">${teamDetailRosterViewSwitch()}<button class="team-panel-link team-roster-copy-button" type="button" onclick="copyTeamRosterImage()">复制球队名单图</button></div></div><div id="teamRosterViewBody">${teamDetailRosterView(players, powerByUid)}</div></section>`;
}

async function loadTeamDetailData(teamName, options = {}) {
    if (teamDetailCache.has(teamName) && options.force !== true) return teamDetailCache.get(teamName);
    const team = teams.find(item => item.name === teamName);
    if (!team) throw new Error(`未找到球队：${teamName}`);
    const encoded = encodeURIComponent(teamName);
    const results = await Promise.allSettled([
        fetchJsonOrThrow(`/api/players/team/${encoded}`),
        fetchJsonOrThrow('/api/standings'),
        fetchJsonOrThrow('/api/matches'),
        fetchJsonOrThrow('/api/suspensions'),
        fetchJsonOrThrow(`/api/attributes/power-ranking?shape=all&limit=all&team=${encoded}`),
        fetchJsonOrThrow(`/api/teams/${team.id}/lineup`),
        loadTeamPowerSummaries(),
        fetchJsonOrThrow(`/api/teams/${team.id}/cup-outlook`),
        fetchJsonOrThrow('/api/site-notes'),
    ]);
    const value = index => results[index].status === 'fulfilled' ? results[index].value : null;
    const data = {
        team,
        players: Array.isArray(value(0)) ? value(0) : [],
        standings: value(1),
        matchesPayload: value(2),
        suspensionsPayload: value(3),
        powerPayload: value(4),
        lineupPayload: value(5) || {team_id: team.id, team_name: team.name, formation: '4-3-3', picks: {}, is_saved: false, can_edit: false},
        teamPowerSummaries: value(6),
        cupOutlookPayload: value(7) || {team_id: team.id, team_name: team.name, competitions: []},
        siteNotesPayload: Array.isArray(value(8)) ? value(8) : [],
    };
    teamDetailCache.set(teamName, data);
    return data;
}

async function renderTeamDetail(options = {}) {
    const root = document.getElementById('teamDetailRoot');
    if (!root) return;
    if (!currentTeamDetailName) {
        await ensureTeamCenterCoachAuth();
        renderTeamCenterLanding();
        return;
    }
    const sequence = ++teamDetailLoadSequence;
    root.innerHTML = `<div class="team-detail-skeleton" aria-label="正在加载 ${escapeHtml(currentTeamDetailName)}"><div class="team-skeleton-hero"></div><div class="team-skeleton-stats"></div><div class="team-skeleton-grid"><span></span><span></span></div></div>`;
    try {
        const data = await loadTeamDetailData(currentTeamDetailName, options);
        if (sequence !== teamDetailLoadSequence) return;
        renderTeamDetailLoaded(data);
    } catch (error) {
        console.error('球队详情加载失败:', error);
        if (sequence !== teamDetailLoadSequence) return;
        root.innerHTML = renderUiState({tone: 'danger', title: '球队详情暂时无法加载', message: error.message || '请稍后重试。', actionLabel: '重新加载', actionClass: 'btn-primary', actionOnclick: 'renderTeamDetail({force:true})'});
    }
}

async function openTeamDetail(teamName, options = {}) {
    if (String(teamName || '').trim() !== currentTeamDetailName) currentTeamJourneyView = 'league';
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
