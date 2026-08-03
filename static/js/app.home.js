var fetchWithTimeout = globalThis.fetchWithTimeout || ((...args) => globalThis.fetch(...args));

const HOME_PROMOTION_DISMISSED_STORAGE_KEY = 'heigoHomePromotionsDismissed';
const HOME_PROMOTION_MODAL_SEEN_STORAGE_KEY = 'heigoHomePromotionModalsSeen';
const HOME_PROMOTION_MODAL_DELAY_MS = 6500;
function homePromotionIconSvg(icon = 'megaphone') {
    const icons = {
        megaphone: '<path d="M4 13V9l11-4v12L4 13Z"/><path d="M7 14v4h4l-1.5-3.5M18 8.5c1 .8 1.5 2 1.5 3.5s-.5 2.7-1.5 3.5"/>',
        trophy: '<path d="M8 4h8v4c0 3-1.6 5-4 5s-4-2-4-5V4Z"/><path d="M8 6H5v2c0 2 1.2 3 3 3M16 6h3v2c0 2-1.2 3-3 3M12 13v4M8 20h8M9 17h6"/>',
        list: '<path d="M9 6h10M9 12h10M9 18h10"/><circle cx="5" cy="6" r="1"/><circle cx="5" cy="12" r="1"/><circle cx="5" cy="18" r="1"/>',
        star: '<path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9L12 3Z"/>',
        whistle: '<path d="M5 14a5 5 0 1 0 10 0 5 5 0 0 0-10 0Z"/><path d="m13.5 10.5 4-4H21v4h-4M5.8 10.8 3 8"/>',
        info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5M12 8h.01"/>',
        close: '<path d="m7 7 10 10M17 7 7 17"/>',
    };
    return `<svg class="ui-icon home-promotion-icon" viewBox="0 0 24 24" focusable="false" aria-hidden="true">${icons[icon] || icons.megaphone}</svg>`;
}
let homePromotions = [];
let homePromotionsLoaded = false;
let homePromotionsLoading = null;
let activeHomePromotionModalId = 0;
let homePromotionModalShownThisVisit = false;
let homePromotionModalPendingTimer = null;
let homeDashboardState = {data: null, teamId: 0, loadedAt: 0, error: ''};
let homeDashboardLoading = null;
let homeDailyReportPage = 0;
let homeDailyReportReport = null;
let homeDailyReportLoading = false;
let homeDailyReportError = '';
let homeDailyReportRequestId = 0;
const HOME_DAILY_REPORT_EVENTS_PER_PAGE = 6;
const HOME_DAILY_REPORT_SECTION_DEFINITIONS = [
    {key: 'super', label: '超级', patterns: [/^超级(?:联赛|第)/, /超级联赛/]},
    {key: 'first', label: '甲级', patterns: [/^甲级(?:联赛|第)/, /甲级联赛/]},
    {key: 'second', label: '乙级', patterns: [/^乙级(?:联赛|第)/, /乙级联赛/]},
    {key: 'champions', label: '冠军杯', patterns: [/冠军杯/]},
    {key: 'europa', label: '联盟杯', patterns: [/联盟杯/]},
    {key: 'wumingjian', label: '无铭剑杯', patterns: [/无铭剑杯/]},
    {key: 'suspensions', label: '伤停', patterns: []},
    {key: 'other', label: '其他', patterns: []},
];

function updateHeroBadgeState() {
    const heroTeamCount = document.getElementById('heroTeamCount');
    const heroPlayerCount = document.getElementById('heroPlayerCount');
    const heroDbPlayerCount = document.getElementById('heroDbPlayerCount');
    const heroModeBadge = document.getElementById('heroModeBadge');
    if (heroTeamCount) {
        heroTeamCount.textContent = teams.length || Number(homeSummary.team_count || 0);
    }
    if (heroPlayerCount) {
        heroPlayerCount.textContent = allPlayers.length || Number(homeSummary.player_count || 0);
    }
    if (heroDbPlayerCount) {
        heroDbPlayerCount.textContent = Number(defaultAttributeVersionPlayerCount || 0).toLocaleString();
    }
    if (heroModeBadge) {
        heroModeBadge.textContent = isAdmin ? '管理员维护已启用' : '公开查询模式';
    }
    loadHomePromotions();
    loadHomeDashboard();
}

function homeDashboardJsString(value) {
    return escapeHtml(JSON.stringify(String(value ?? '')));
}

function homeDashboardLevelClass(level) {
    return level === '超级' ? 'is-super' : level === '甲级' ? 'is-first' : 'is-second';
}

function homeDashboardLevelMark(level) {
    return level === '超级' ? '超' : level === '甲级' ? '甲' : '乙';
}

function homeDashboardLevelLabel(level) {
    return `${level || '未知'}联赛`;
}

function formatHomeDashboardTime(value) {
    if (!value) return '刚刚更新';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '刚刚更新';
    return `${date.toLocaleDateString('zh-CN', {month: 'numeric', day: 'numeric'})} ${date.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})}`;
}

function homeDashboardMatchScore(match) {
    if (match?.home_score === null || match?.home_score === undefined || match?.away_score === null || match?.away_score === undefined) {
        return '<span class="home-dashboard-score is-pending">待赛</span>';
    }
    return `<span class="home-dashboard-score"><strong>${Number(match.home_score)}</strong><i>:</i><strong>${Number(match.away_score)}</strong></span>`;
}

function homeDashboardTeamMatchMeta(match, teamName) {
    if (!match || !teamName) return null;
    const isHome = String(match.home_team_name || '') === String(teamName);
    return {
        venue: isHome ? '主场' : '客场',
        opponent: isHome ? match.away_team_name : match.home_team_name,
        isHome,
    };
}

function homeDashboardTeamResultTone(match, teamName) {
    if (!match || match.home_score === null || match.away_score === null) return '';
    const isHome = String(match.home_team_name || '') === String(teamName);
    const own = Number(isHome ? match.home_score : match.away_score);
    const rival = Number(isHome ? match.away_score : match.home_score);
    return own > rival ? 'is-win' : own < rival ? 'is-loss' : 'is-draw';
}

function renderHomeDashboardCrest(logoPath, teamName, fallback, className = 'home-dashboard-team-mark') {
    if (!logoPath) {
        return `<span class="${className}" aria-hidden="true">${escapeHtml(fallback)}</span>`;
    }
    return `
        <span class="${className} has-logo">
            <img src="${escapeHtml(logoPath)}" alt="${escapeHtml(teamName)}队徽" width="512" height="512" loading="lazy" decoding="async" onerror="this.hidden=true;this.nextElementSibling.hidden=false">
            <b hidden aria-hidden="true">${escapeHtml(fallback)}</b>
        </span>
    `;
}

function renderHomeDashboardTeamCrest(team) {
    return renderHomeDashboardCrest(team?.logo_path, team?.team_name, homeDashboardLevelMark(team?.level));
}

async function openHomeDashboardCompetition(level, subtab = 'standings') {
    await showTab('competition', null, {syncHistory: false});
    if (typeof showCompetitionSubtab === 'function') showCompetitionSubtab(subtab);
    if (typeof setCompetitionLevel === 'function') setCompetitionLevel(level);
    if (typeof syncAppHistory === 'function') syncAppHistory('push');
    window.scrollTo({top: 0, behavior: 'auto'});
}

async function openHomeDashboardLogin() {
    await ensureAppModule('coaches');
    showCoachLoginPanel({context: 'home-dashboard'});
}

async function openHomeDashboardTeam(teamName = '') {
    await openTeamCenter({smooth: false});
    if (teamName && typeof openTeamDetail === 'function') {
        await openTeamDetail(teamName);
    }
}

function renderHomeDashboardPersonal(data) {
    const account = currentCoachAccount || {authenticated: false};
    if (!account.authenticated) {
        return `
            <article class="home-dashboard-card home-dashboard-personal is-guest">
                <div class="home-dashboard-card-head"><span class="home-dashboard-card-kicker">MY CLUB</span><span class="home-dashboard-live-dot">个人入口</span></div>
                <div class="home-dashboard-personal-copy">
                    <span class="home-dashboard-personal-mark" aria-hidden="true"><svg class="ui-icon" viewBox="0 0 24 24" focusable="false"><path d="m4 10 8-6 8 6v9H9v-6h6v6"/></svg></span>
                    <div><h3>登录后查看你的球队</h3><p>下一场、最近赛果与球队中心会直接出现在这里。</p></div>
                </div>
                <div class="home-dashboard-actions">
                    <button class="btn btn-primary" type="button" onclick="openHomeDashboardLogin()">教练登录</button>
                    <button class="btn btn-secondary" type="button" onclick="openHomeDashboardTeam()">先浏览球队</button>
                </div>
            </article>
        `;
    }

    if (account.must_change_password || !account.qq_number) {
        return `
            <article class="home-dashboard-card home-dashboard-personal is-security">
                <div class="home-dashboard-card-head"><span class="home-dashboard-card-kicker">ACCOUNT READY</span><span class="home-dashboard-live-dot is-warning">待完成</span></div>
                <div class="home-dashboard-personal-copy">
                    <span class="home-dashboard-personal-mark" aria-hidden="true">${uiIconSvg('alert')}</span>
                    <div><h3>${account.must_change_password ? '请先修改默认密码' : '请先绑定 QQ 号'}</h3><p>完成不可跳过的登录安全设置后，首页会自动关联你的球队。</p></div>
                </div>
                <div class="home-dashboard-actions"><button class="btn btn-primary" type="button" onclick="openGlobalCoachSecurity()">完成安全设置</button></div>
            </article>
        `;
    }

    const team = data?.team;
    if (!team) {
        return `
            <article class="home-dashboard-card home-dashboard-personal">
                <div class="home-dashboard-card-head"><span class="home-dashboard-card-kicker">MY CLUB</span><span class="home-dashboard-live-dot is-warning">未关联</span></div>
                <div class="home-dashboard-personal-copy">
                    <span class="home-dashboard-personal-mark" aria-hidden="true">${escapeHtml(getGlobalCoachInitials(account.nickname || account.username))}</span>
                    <div><h3>${escapeHtml(account.nickname || account.username || '教练')}</h3><p>当前账号尚未关联球队，可先进入球队中心浏览，或联系管理员设置关联。</p></div>
                </div>
                <div class="home-dashboard-actions"><button class="btn btn-primary" type="button" onclick="openHomeDashboardTeam()">进入球队中心</button></div>
            </article>
        `;
    }

    const nextMeta = homeDashboardTeamMatchMeta(team.next_match, team.team_name);
    const recentTone = homeDashboardTeamResultTone(team.recent_result, team.team_name);
    return `
        <article class="home-dashboard-card home-dashboard-personal ${homeDashboardLevelClass(team.level)}">
            <div class="home-dashboard-card-head"><span class="home-dashboard-card-kicker">MY CLUB</span><span class="home-dashboard-live-dot">${escapeHtml(team.level)}联赛</span></div>
            <div class="home-dashboard-team-heading">
                ${renderHomeDashboardTeamCrest(team)}
                <div><h3>${escapeHtml(team.team_name)}</h3><p>${escapeHtml(team.manager || account.nickname || '主教练')}</p></div>
            </div>
            ${team.next_match && nextMeta ? `
                <button class="home-dashboard-next-match" type="button" onclick="openHomeDashboardCompetition(${homeDashboardJsString(team.level)}, 'schedule')">
                    <span><b>下一场</b>第 ${Number(team.next_match.round_no)} 轮 · ${escapeHtml(nextMeta.venue)}</span>
                    <strong>${escapeHtml(nextMeta.opponent || '待定')}</strong>
                    <em>查看赛程 →</em>
                </button>
            ` : '<div class="home-dashboard-empty-inline">当前没有待赛赛程</div>'}
            ${team.recent_result ? `
                <div class="home-dashboard-recent-team ${recentTone}">
                    <span>最近赛果 · 第 ${Number(team.recent_result.round_no)} 轮</span>
                    <strong>${escapeHtml(team.recent_result.home_team_name)} ${Number(team.recent_result.home_score)} : ${Number(team.recent_result.away_score)} ${escapeHtml(team.recent_result.away_team_name)}</strong>
                </div>
            ` : ''}
            <div class="home-dashboard-actions"><button class="btn btn-primary" type="button" onclick="openHomeDashboardTeam(${homeDashboardJsString(team.team_name)})">进入我的球队</button></div>
        </article>
    `;
}

function renderHomeDashboardPulse(statuses) {
    const rows = Array.isArray(statuses) ? statuses : [];
    return `
        <article class="home-dashboard-card home-dashboard-pulse">
            <div class="home-dashboard-card-head"><div><span class="home-dashboard-card-kicker">LEAGUE PULSE</span><h3>三级联赛进度</h3></div><button class="home-dashboard-text-action" type="button" onclick="showTab('overview')">联赛概览</button></div>
            <div class="home-dashboard-pulse-list">
                ${rows.length ? rows.map(item => {
                    const total = Number(item.total_count || 0);
                    const completed = Number(item.completed_count || 0);
                    const progress = total > 0 ? Math.max(0, Math.min(100, Math.round((completed / total) * 100))) : 0;
                    const summary = Number(item.updated_round || 0) > 0
                        ? `连续完成至第 ${Number(item.updated_round)} 轮`
                        : Number(item.latest_round || 0) > 0 ? `已导入 ${Number(item.latest_round)} 轮赛程` : '等待赛程数据';
                    return `
                        <button class="home-dashboard-pulse-row ${homeDashboardLevelClass(item.scope)}" type="button" onclick="openDataStatusItem('schedule', ${homeDashboardJsString(item.scope)})">
                            <span class="home-dashboard-level-mark">${homeDashboardLevelMark(item.scope)}</span>
                            <span class="home-dashboard-pulse-copy"><strong>${escapeHtml(item.scope)}联赛</strong><small>${escapeHtml(summary)}</small></span>
                            <span class="home-dashboard-pulse-status is-${escapeHtml(item.status || 'unknown')}">${escapeHtml(item.status_label || '状态未知')}</span>
                            <span class="home-dashboard-progress"><i style="width:${progress}%"></i></span>
                            <span class="home-dashboard-pulse-count">${Number(item.issue_count || 0) > 0 ? `${Number(item.issue_count)} 项待补` : (total > 0 ? `${completed}/${total} 场` : '等待首轮')}</span>
                        </button>
                    `;
                }).join('') : '<div class="home-dashboard-empty-inline">联赛进度暂不可用</div>'}
            </div>
        </article>
    `;
}

function renderHomeDashboardResults(results) {
    const rows = Array.isArray(results) ? results : [];
    return `
        <article class="home-dashboard-card home-dashboard-results">
            <div class="home-dashboard-card-head"><div><span class="home-dashboard-card-kicker">LATEST RESULTS</span><h3>最近赛果</h3></div><button class="home-dashboard-text-action" type="button" onclick="openHomeDashboardCompetition('超级', 'schedule')">全部赛程</button></div>
            <div class="home-dashboard-result-list">
                ${rows.length ? rows.map(match => `
                    <button class="home-dashboard-result-row" type="button" onclick="openHomeDashboardCompetition(${homeDashboardJsString(match.level)}, 'schedule')">
                        <span class="home-dashboard-result-meta"><b class="${homeDashboardLevelClass(match.level)}">${homeDashboardLevelMark(match.level)}</b><small>第 ${Number(match.round_no)} 轮</small></span>
                        <span class="home-dashboard-result-team is-home">${escapeHtml(match.home_team_name)}</span>
                        ${homeDashboardMatchScore(match)}
                        <span class="home-dashboard-result-team is-away">${escapeHtml(match.away_team_name)}</span>
                    </button>
                `).join('') : '<div class="home-dashboard-empty-inline">本届联赛尚未产生赛果</div>'}
            </div>
        </article>
    `;
}

function renderHomeDashboardLeaders(leaders) {
    const rows = Array.isArray(leaders) ? leaders : [];
    return `
        <article class="home-dashboard-card home-dashboard-leaders">
            <div class="home-dashboard-card-head"><div><span class="home-dashboard-card-kicker">TITLE RACE</span><h3>争冠形势</h3></div><button class="home-dashboard-text-action" type="button" onclick="openHomeDashboardCompetition('超级', 'standings')">积分榜</button></div>
            <div class="home-dashboard-leader-list">
                ${rows.length ? rows.map(row => `
                    <button class="home-dashboard-leader-row ${homeDashboardLevelClass(row.level)}" type="button" onclick="openHomeDashboardCompetition(${homeDashboardJsString(row.level)}, 'standings')">
                        ${renderHomeDashboardCrest(row.logo_path, row.team_name, homeDashboardLevelMark(row.level), 'home-dashboard-leader-crest')}
                        <span><strong>${escapeHtml(row.team_name)}</strong><small><em>${escapeHtml(homeDashboardLevelLabel(row.level))}</em><i>${escapeHtml(row.manager || '主教练待定')}</i></small></span>
                        <span class="home-dashboard-leader-score"><strong>${Number(row.points)}</strong><small>${Number(row.played) > 0 ? `${Number(row.played)} 场` : '待开赛'}</small></span>
                    </button>
                `).join('') : '<div class="home-dashboard-empty-inline">积分榜暂不可用</div>'}
            </div>
        </article>
    `;
}

function renderHomeDailyReport(report) {
    if (!report) return '';
    const lines = String(report.content || '').split('\n').map(line => line.trim()).filter(Boolean);
    const excerpt = lines.filter(line => !/^【.+】$/.test(line)).slice(0, 3).join(' ');
    const statusLabel = report.status === 'published' ? '人工终稿' : '自动成稿';
    return `
        <article class="home-dashboard-card home-dashboard-daily-report">
            <div class="home-dashboard-card-head"><div><span class="home-dashboard-card-kicker">LEAGUE NEWSWIRE</span><h3>${escapeHtml(report.title || 'HEIGO 联赛日报')}</h3></div><span class="home-dashboard-live-dot">${escapeHtml(statusLabel)}</span></div>
            <p>${escapeHtml(excerpt || '今日暂无新增赛果，完整日报仍会整理下一轮战力看点。')}</p>
            <div class="home-dashboard-daily-report-meta"><span>${Number(report.match_count || 0)} 场比赛</span><span>${Number(report.goal_count || 0)} 粒进球</span><span>${Number(report.suspension_count || 0)} 条伤停更新</span></div>
            <button class="home-dashboard-daily-report-open" type="button" onclick="openHomeDailyReport()">阅读完整日报 <span aria-hidden="true">→</span></button>
        </article>
    `;
}

function parseHomeDailyReportContent(content) {
    const overview = [];
    const sections = [];
    let activeSection = null;
    String(content || '').split('\n').forEach(rawLine => {
        const line = rawLine.trim();
        if (!line) return;
        const heading = line.match(/^【([^】]+)】$/);
        if (heading) {
            activeSection = {title: heading[1].trim(), lines: []};
            sections.push(activeSection);
            return;
        }
        if (activeSection) activeSection.lines.push(line);
        else overview.push(line);
    });
    return {overview, sections: sections.filter(section => section.lines.length)};
}

function buildHomeDailyReportPages(report) {
    const fullReport = parseHomeDailyReportContent(report?.content || '');
    const focusReport = parseHomeDailyReportContent(report?.focus_content || '');
    const focusSection = focusReport.sections.find(section => section.title === '焦点头版')
        || fullReport.sections.find(section => section.title === '焦点头版');
    let focusLines = focusSection?.lines || [];
    if (!focusLines.length && focusReport.overview.length > 1) focusLines = focusReport.overview.slice(1);
    if (!focusLines.length && focusReport.overview.length === 1 && !fullReport.overview.includes(focusReport.overview[0])) {
        focusLines = focusReport.overview;
    }
    const overview = focusReport.overview[0] || fullReport.overview[0] || '今日暂无新增赛果。';
    const pages = [{
        kind: 'focus',
        label: '焦点头版',
        overview,
        categoryKey: 'focus',
        entries: focusLines.map(line => ({section: '焦点头版', categoryKey: 'focus', categoryLabel: '焦点头版', line})),
    }];
    const otherEntries = fullReport.sections
        .filter(section => section.title !== '焦点头版')
        .flatMap(section => section.lines.map(line => classifyHomeDailyReportEntry({section: section.title, line})));
    const groupedEntries = new Map(HOME_DAILY_REPORT_SECTION_DEFINITIONS.map(section => [section.key, []]));
    otherEntries.forEach(entry => groupedEntries.get(entry.categoryKey)?.push(entry));
    HOME_DAILY_REPORT_SECTION_DEFINITIONS.forEach(section => {
        const entries = groupedEntries.get(section.key) || [];
        const sectionPageCount = Math.ceil(entries.length / HOME_DAILY_REPORT_EVENTS_PER_PAGE);
        for (let index = 0; index < entries.length; index += HOME_DAILY_REPORT_EVENTS_PER_PAGE) {
            const pageNumber = Math.floor(index / HOME_DAILY_REPORT_EVENTS_PER_PAGE) + 1;
            pages.push({
                kind: 'archive',
                categoryKey: section.key,
                label: sectionPageCount > 1 ? `${section.label} ${pageNumber}` : section.label,
                heading: section.label,
                overview: `${section.label}板块 · 当日共 ${entries.length} 条事件${sectionPageCount > 1 ? ` · 第 ${pageNumber}/${sectionPageCount} 页` : ''}`,
                entries: entries.slice(index, index + HOME_DAILY_REPORT_EVENTS_PER_PAGE),
            });
        }
    });
    return pages;
}

function classifyHomeDailyReportEntry(entry) {
    const sourceSection = String(entry?.section || '').trim();
    const line = String(entry?.line || '').trim();
    if (sourceSection.includes('伤停')) {
        return {...entry, categoryKey: 'suspensions', categoryLabel: '伤停'};
    }
    const event = parseHomeDailyReportEvent(line);
    const competition = String(event.competition || '').trim();
    const classificationText = `${competition} ${line}`.trim();
    const matchedSection = HOME_DAILY_REPORT_SECTION_DEFINITIONS
        .filter(section => !['suspensions', 'other'].includes(section.key))
        .find(section => section.patterns.some(pattern => pattern.test(classificationText)));
    const category = matchedSection || HOME_DAILY_REPORT_SECTION_DEFINITIONS.find(section => section.key === 'other');
    return {...entry, categoryKey: category.key, categoryLabel: category.label};
}

function getActiveHomeDailyReport() {
    return homeDailyReportReport || homeDashboardState.data?.daily_report || null;
}

function getHomeDailyReportToday() {
    return String(homeDashboardState.data?.daily_report?.report_date || homeDailyReportReport?.report_date || '').trim();
}

function shiftHomeDailyReportIsoDate(value, dayOffset) {
    const match = String(value || '').match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return '';
    const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
    date.setUTCDate(date.getUTCDate() + Number(dayOffset || 0));
    return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}-${String(date.getUTCDate()).padStart(2, '0')}`;
}

function renderHomeDailyReportArchiveBar(report) {
    const selectedDate = String(report?.report_date || '').trim();
    const today = getHomeDailyReportToday() || selectedDate;
    const canMoveForward = Boolean(selectedDate && today && selectedDate < today);
    return `
        <section class="home-daily-report-archive" aria-label="往期日报选择">
            <div class="home-daily-report-archive-copy">
                <span>EDITION ARCHIVE</span><strong>往期日报</strong><small>选择日期查看当日焦点头版和全部事件</small>
            </div>
            <div class="home-daily-report-date-controls">
                <button type="button" onclick="shiftHomeDailyReportDate(-1)" aria-label="查看前一天日报">←</button>
                <label><span>日报日期</span><input type="date" value="${escapeHtml(selectedDate)}" max="${escapeHtml(today)}" onchange="loadHomeDailyReportDate(this.value)" ${homeDailyReportLoading ? 'disabled' : ''}></label>
                <button type="button" onclick="shiftHomeDailyReportDate(1)" aria-label="查看后一天日报" ${canMoveForward && !homeDailyReportLoading ? '' : 'disabled'}>→</button>
                <button class="home-daily-report-today" type="button" onclick="loadHomeDailyReportDate(${homeDashboardJsString(today)})" ${selectedDate === today || homeDailyReportLoading ? 'disabled' : ''}>返回今天</button>
            </div>
            ${homeDailyReportLoading ? '<span class="home-daily-report-archive-state is-loading">正在读取所选日报…</span>' : ''}
            ${homeDailyReportError ? `<span class="home-daily-report-archive-state is-error" role="alert">${escapeHtml(homeDailyReportError)}</span>` : ''}
        </section>
    `;
}

function homeDailyReportSectionClass(section) {
    if (section === '焦点头版' || section === 'focus') return 'is-focus';
    if (section === 'super') return 'is-super';
    if (section === 'first') return 'is-first';
    if (section === 'second') return 'is-second';
    if (section === 'champions') return 'is-champions';
    if (section === 'europa') return 'is-europa';
    if (section === 'wumingjian') return 'is-wumingjian';
    if (section === 'suspensions') return 'is-suspensions';
    if (section === '常规战报') return 'is-results';
    if (section === '伤停动态') return 'is-suspensions';
    if (section.includes('排名预测')) return 'is-predictions';
    if (section.includes('战力')) return 'is-power';
    return 'is-general';
}

function homeDailyReportEntityHtml(value, extraTeams = []) {
    const text = String(value || '');
    if (!text) return '';
    const styles = Array.from({length: text.length}, () => ({kind: 'plain', priority: 0}));
    const mark = (start, end, kind, priority) => {
        for (let index = Math.max(0, start); index < Math.min(text.length, end); index += 1) {
            if (priority >= styles[index].priority) styles[index] = {kind, priority};
        }
    };
    for (const match of text.matchAll(/\d{1,2}\s*[:：]\s*\d{1,2}/g)) {
        mark(match.index, match.index + match[0].length, 'score', 30);
    }
    const knownTeams = [...new Set([
        ...extraTeams,
        ...(typeof teams !== 'undefined' && Array.isArray(teams) ? teams.map(team => team.name) : []),
    ].map(team => String(team || '').trim()).filter(Boolean))].sort((a, b) => b.length - a.length);
    knownTeams.forEach(teamName => {
        let start = 0;
        const source = text.toLocaleLowerCase();
        const needle = teamName.toLocaleLowerCase();
        while (needle && (start = source.indexOf(needle, start)) >= 0) {
            mark(start, start + teamName.length, 'team', 10);
            start += teamName.length;
        }
    });
    const playerPatterns = [
        /(?:^|[。；！!?，：]\s*)([A-Za-zÀ-ÖØ-öø-ÿĀ-ž][A-Za-zÀ-ÖØ-öø-ÿĀ-ž'’.\-]*(?:\s+[A-Za-zÀ-ÖØ-öø-ÿĀ-ž][A-Za-zÀ-ÖØ-öø-ÿĀ-ž'’.\-]*){0,5}|[\u3400-\u9fff·]{2,12})(?=\s*(?:独中三元|上演帽子戏法|帽子戏法|梅开二度|送出\s*\d+\s*次助攻|贡献\s*\d+\s*球|当选本场最佳))/g,
        /^\s*([A-Za-zÀ-ÖØ-öø-ÿĀ-ž][A-Za-zÀ-ÖØ-öø-ÿĀ-ž'’.\-]*(?:\s+[A-Za-zÀ-ÖØ-öø-ÿĀ-ž][A-Za-zÀ-ÖØ-öø-ÿĀ-ž'’.\-]*){0,5}|[\u3400-\u9fff·]{2,12})(?=（[^）]*(?:黄|红牌|伤停))/g,
    ];
    playerPatterns.forEach(pattern => {
        for (const match of text.matchAll(pattern)) {
            const playerName = match[1] || '';
            const relativeStart = match[0].lastIndexOf(playerName);
            const start = match.index + Math.max(0, relativeStart);
            mark(start, start + playerName.length, 'player', 20);
        }
    });
    const chunks = [];
    let start = 0;
    let activeKind = styles[0]?.kind || 'plain';
    for (let index = 1; index <= text.length; index += 1) {
        const kind = styles[index]?.kind || '';
        if (index < text.length && kind === activeKind) continue;
        const escaped = escapeHtml(text.slice(start, index));
        chunks.push(activeKind === 'plain' ? escaped : `<strong class="home-daily-report-entity is-${activeKind}">${escaped}</strong>`);
        start = index;
        activeKind = kind;
    }
    return chunks.join('');
}

function parseHomeDailyReportEvent(line) {
    const raw = String(line || '').trim();
    const structured = raw.match(/^(?:【([^】]+)】)?([^｜：]+)｜([^：]+)：(.+)$/);
    if (!structured) {
        const tagged = raw.match(/^【([^】]+)】(.*)$/);
        return {
            tags: tagged ? tagged[1].split('·').map(tag => tag.trim()).filter(Boolean) : [],
            competition: '', matchup: '', teams: [], result: '', commentary: (tagged ? tagged[2] : raw).trim(),
        };
    }
    const matchup = structured[3].trim();
    const teamsInMatchup = matchup.split(/\s+(?:vs|VS|对)\s+/).map(team => team.trim()).filter(Boolean);
    const body = structured[4].trim();
    const sentenceEnd = body.indexOf('。');
    const firstSentence = sentenceEnd >= 0 ? body.slice(0, sentenceEnd) : body;
    const hasScore = /\d{1,2}\s*[:：]\s*\d{1,2}/.test(firstSentence);
    return {
        tags: String(structured[1] || '').split('·').map(tag => tag.trim()).filter(Boolean),
        competition: structured[2].trim(),
        matchup,
        teams: teamsInMatchup,
        result: hasScore ? firstSentence.trim() : '',
        commentary: hasScore && sentenceEnd >= 0 ? body.slice(sentenceEnd + 1).trim() : body,
    };
}

function renderHomeDailyReportEvent(entry, index, pageKind) {
    const event = parseHomeDailyReportEvent(entry.line);
    const sectionClass = homeDailyReportSectionClass(entry.categoryKey || entry.section);
    return `
        <article class="home-daily-report-event ${sectionClass} ${pageKind === 'focus' ? 'is-headline' : ''}">
            <div class="home-daily-report-event-meta">
                <span>${escapeHtml(event.competition || entry.section)}</span>
                ${event.tags.map(tag => `<em>${escapeHtml(tag)}</em>`).join('')}
                <i>${String(index + 1).padStart(2, '0')}</i>
            </div>
            ${event.matchup ? `<h3>${homeDailyReportEntityHtml(event.matchup, event.teams)}</h3>` : ''}
            ${event.result ? `<p class="home-daily-report-result">${homeDailyReportEntityHtml(event.result, event.teams)}</p>` : ''}
            ${event.commentary ? `<p class="home-daily-report-commentary">${homeDailyReportEntityHtml(event.commentary, event.teams)}</p>` : ''}
        </article>
    `;
}

function renderHomeDailyReportReader(report, requestedPage = 0) {
    const pages = buildHomeDailyReportPages(report);
    const pageIndex = Math.max(0, Math.min(pages.length - 1, Number(requestedPage) || 0));
    const page = pages[pageIndex];
    const reportDate = String(report.report_date || '').replaceAll('-', '.');
    return `
        <div class="home-daily-report-reader-shell">
            ${renderHomeDailyReportArchiveBar(report)}
            <nav class="home-daily-report-page-tabs" aria-label="日报页码">
                ${pages.map((item, index) => `
                    <button type="button" class="${index === pageIndex ? 'active' : ''}" onclick="setHomeDailyReportPage(${index})" ${index === pageIndex ? 'aria-current="page"' : ''}>
                        <b>${String(index + 1).padStart(2, '0')}</b><span>${escapeHtml(item.label)}</span>
                    </button>
                `).join('')}
            </nav>
            <section class="home-daily-report-sheet is-${page.kind} is-section-${escapeHtml(page.categoryKey || 'other')}" aria-live="polite">
                <div class="home-daily-report-sheet-head">
                    <div class="home-daily-report-sheet-identity">
                        <span>${page.kind === 'focus' ? 'HEIGO / FRONT PAGE' : 'HEIGO / FULL WIRE'}</span>
                        <h2>${page.kind === 'focus' ? '焦点头版' : escapeHtml(page.heading || '全部事件')}</h2>
                        <p>${escapeHtml(page.overview || `第 ${pageIndex + 1} 页 · 收录当日其余联赛事件`)}</p>
                    </div>
                    <div class="home-daily-report-sheet-folio"><span>PAGE</span><strong>${String(pageIndex + 1).padStart(2, '0')}</strong><small>${escapeHtml(reportDate)}</small></div>
                </div>
                <div class="home-daily-report-stat-rail">
                    <span><b>${Number(report.match_count || 0)}</b><small>比赛</small></span>
                    <span><b>${Number(report.goal_count || 0)}</b><small>进球</small></span>
                    <span><b>${Number(report.focus_count || 0)}</b><small>焦点</small></span>
                    <span><b>${Number(report.suspension_count || 0)}</b><small>伤停更新</small></span>
                </div>
                <div class="home-daily-report-event-grid">
                    ${page.entries.length
                        ? page.entries.map((entry, index) => renderHomeDailyReportEvent(entry, index, page.kind)).join('')
                        : `<div class="home-daily-report-empty"><strong>${page.kind === 'focus' ? '今日没有独立焦点事件' : '本页暂无其他事件'}</strong><p>${page.kind === 'focus' ? '日报仍会保留比赛总览，其他常规事件可通过后续页查看。' : '当天已记录的事件均已展示完毕。'}</p></div>`}
                </div>
                <footer class="home-daily-report-sheet-footer"><span>HEIGO 联机联赛数据库</span><span>${report.status === 'published' ? '人工终稿' : '自动成稿'} · ${pageIndex + 1} / ${pages.length}</span></footer>
            </section>
            <div class="home-daily-report-reader-actions">
                <button class="btn btn-secondary" type="button" onclick="setHomeDailyReportPage(${pageIndex - 1})" ${pageIndex === 0 ? 'disabled' : ''}>上一页</button>
                <span>第 ${pageIndex + 1} 页，共 ${pages.length} 页</span>
                <button class="btn btn-secondary" type="button" onclick="setHomeDailyReportPage(${pageIndex + 1})" ${pageIndex >= pages.length - 1 ? 'disabled' : ''}>下一页</button>
                <button class="btn btn-secondary" type="button" onclick="copyHomeDailyReport()">复制全文</button>
                <button class="btn btn-primary" type="button" onclick="closeModal()">阅读完成</button>
            </div>
        </div>
    `;
}

function setHomeDailyReportPage(pageIndex) {
    const report = getActiveHomeDailyReport();
    const reader = document.getElementById('homeDailyReportReader');
    if (!report || !reader) return;
    const pages = buildHomeDailyReportPages(report);
    homeDailyReportPage = Math.max(0, Math.min(pages.length - 1, Number(pageIndex) || 0));
    reader.innerHTML = renderHomeDailyReportReader(report, homeDailyReportPage);
    const modalBody = reader.closest('.modal-body');
    if (modalBody) modalBody.scrollTop = 0;
}

async function loadHomeDailyReportDate(reportDate) {
    const selectedDate = String(reportDate || '').trim();
    const currentReport = getActiveHomeDailyReport();
    const today = getHomeDailyReportToday();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(selectedDate) || (today && selectedDate > today)) {
        homeDailyReportError = '请选择今天或更早的有效日期。';
        const reader = document.getElementById('homeDailyReportReader');
        if (reader && currentReport) reader.innerHTML = renderHomeDailyReportReader(currentReport, homeDailyReportPage);
        return;
    }
    if (currentReport?.report_date === selectedDate && !homeDailyReportError) return;
    const requestId = ++homeDailyReportRequestId;
    homeDailyReportLoading = true;
    homeDailyReportError = '';
    const reader = document.getElementById('homeDailyReportReader');
    if (reader && currentReport) reader.innerHTML = renderHomeDailyReportReader(currentReport, homeDailyReportPage);
    try {
        const response = await fetchWithTimeout(`/api/daily-report?report_date=${encodeURIComponent(selectedDate)}`);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || '所选日期的日报读取失败');
        if (requestId !== homeDailyReportRequestId) return;
        homeDailyReportReport = data;
        homeDailyReportPage = 0;
        document.getElementById('modalTitle').textContent = data.title || 'HEIGO 联赛日报';
    } catch (error) {
        if (requestId !== homeDailyReportRequestId) return;
        homeDailyReportError = error.message || '所选日期的日报暂时无法读取，请稍后重试。';
    } finally {
        if (requestId !== homeDailyReportRequestId) return;
        homeDailyReportLoading = false;
        const activeReport = getActiveHomeDailyReport();
        const activeReader = document.getElementById('homeDailyReportReader');
        if (activeReader && activeReport) activeReader.innerHTML = renderHomeDailyReportReader(activeReport, homeDailyReportPage);
    }
}

function shiftHomeDailyReportDate(dayOffset) {
    const report = getActiveHomeDailyReport();
    const targetDate = shiftHomeDailyReportIsoDate(report?.report_date, dayOffset);
    if (targetDate) loadHomeDailyReportDate(targetDate);
}

function openHomeDailyReport() {
    const report = homeDashboardState.data?.daily_report;
    if (!report) return;
    homeDailyReportPage = 0;
    homeDailyReportReport = report;
    homeDailyReportLoading = false;
    homeDailyReportError = '';
    homeDailyReportRequestId += 1;
    showModal(report.title || 'HEIGO 联赛日报', `<article class="home-daily-report-reader" id="homeDailyReportReader">${renderHomeDailyReportReader(report, 0)}</article>`);
}

async function copyHomeDailyReport() {
    const report = getActiveHomeDailyReport();
    if (!report) return;
    const text = `${report.title || 'HEIGO 联赛日报'}\n\n${report.content || ''}`.trim();
    try {
        await navigator.clipboard.writeText(text);
        showSuccessToast('日报全文已复制');
    } catch (_error) {
        showModal('复制日报', `<textarea class="workspace-daily-copy-fallback" rows="18" readonly>${escapeHtml(text)}</textarea><p>当前浏览器无法直接写入剪贴板，请长按或全选复制。</p>`);
    }
}

function renderHomeDashboard() {
    const container = document.getElementById('homeDashboard');
    if (!container) return;
    const data = homeDashboardState.data;
    if (!data && homeDashboardState.error) {
        container.removeAttribute('aria-busy');
        container.innerHTML = `
            <div class="home-dashboard-head"><div><span class="panel-kicker">League Today</span><h2>今日联赛</h2></div></div>
            ${renderUiState({tone: 'danger', title: '动态数据暂时无法读取', message: '不影响其他页面使用，可以稍后重新读取。', actionLabel: '重新读取', actionOnclick: 'loadHomeDashboard({force:true})'})}
        `;
        return;
    }
    if (!data) return;
    container.removeAttribute('aria-busy');
    container.classList.remove('is-refreshing');
    container.innerHTML = `
        <div class="home-dashboard-head">
            <div><span class="panel-kicker">League Today</span><h2>今日联赛</h2></div>
            <div class="home-dashboard-meta"><span>${escapeHtml(formatHomeDashboardTime(data.generated_at))} 更新</span><button type="button" onclick="loadHomeDashboard({force:true})">刷新</button></div>
        </div>
        <div class="home-dashboard-grid">
            ${renderHomeDashboardPersonal(data)}
            ${renderHomeDashboardPulse(data.league_statuses)}
            ${renderHomeDashboardResults(data.recent_results)}
            ${renderHomeDashboardLeaders(data.leaders)}
            ${renderHomeDailyReport(data.daily_report)}
        </div>
    `;
}

async function loadHomeDashboard(options = {}) {
    const account = currentCoachAccount || {authenticated: false};
    const teamId = account.authenticated ? Number(account.team_id || 0) : 0;
    const cacheFresh = homeDashboardState.data
        && homeDashboardState.teamId === teamId
        && Date.now() - homeDashboardState.loadedAt < 120000;
    if (cacheFresh && options.force !== true) {
        renderHomeDashboard();
        return homeDashboardState.data;
    }
    if (homeDashboardLoading && options.force !== true) return homeDashboardLoading;
    const container = document.getElementById('homeDashboard');
    container?.classList.add('is-refreshing');
    const query = teamId > 0 ? `?team_id=${teamId}` : '';
    homeDashboardLoading = fetchWithTimeout(`/api/home/dashboard${query}`, {credentials: 'same-origin'})
        .then(async response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            homeDashboardState = {data, teamId, loadedAt: Date.now(), error: ''};
            return data;
        })
        .catch(error => {
            homeDashboardState.error = error?.message || '读取失败';
            return homeDashboardState.data;
        })
        .finally(() => {
            homeDashboardLoading = null;
            renderHomeDashboard();
        });
    return homeDashboardLoading;
}

async function syncHomeDashboardAccount() {
    if (document.body.dataset.activeTab && document.body.dataset.activeTab !== 'home') return;
    if (homeDashboardLoading) await homeDashboardLoading;
    const account = currentCoachAccount || {authenticated: false};
    const teamId = account.authenticated ? Number(account.team_id || 0) : 0;
    if (!homeDashboardState.data || homeDashboardState.teamId !== teamId) {
        await loadHomeDashboard({force: true});
        return;
    }
    renderHomeDashboard();
}

function homePromotionStorageGet(key) {
    try {
        return window.localStorage?.getItem(key) || '';
    } catch (error) {
        return '';
    }
}

function homePromotionStorageSet(key, value) {
    try {
        window.localStorage?.setItem(key, value);
    } catch (error) {
        // Home promotions remain usable when storage is unavailable.
    }
}

function getDismissedHomePromotionVersions() {
    try {
        const payload = JSON.parse(homePromotionStorageGet(HOME_PROMOTION_DISMISSED_STORAGE_KEY) || '{}');
        return payload && typeof payload === 'object' ? payload : {};
    } catch (error) {
        return {};
    }
}

function getSeenHomePromotionModalVersions() {
    try {
        const payload = JSON.parse(homePromotionStorageGet(HOME_PROMOTION_MODAL_SEEN_STORAGE_KEY) || '{}');
        return payload && typeof payload === 'object' ? payload : {};
    } catch (error) {
        return {};
    }
}

function homePromotionUsesBoard(promotion) {
    return !promotion.display_mode || ['board', 'both'].includes(promotion.display_mode);
}

function homePromotionUsesModal(promotion) {
    return ['modal', 'both'].includes(promotion.display_mode);
}

function getHomePromotionVersion(promotion) {
    return String(promotion.updated_at || promotion.updatedAt || promotion.id);
}

function getHomePromotionMedia(promotion) {
    if (promotion.image_url) {
        return `<span class="home-promotion-media"><img src="${escapeHtml(promotion.image_url)}" alt="" width="1600" height="900" loading="lazy" decoding="async" fetchpriority="low"></span>`;
    }
    return `<span class="home-promotion-media is-symbol" aria-hidden="true">${homePromotionIconSvg(promotion.icon)}</span>`;
}

function renderHomePromotions() {
    const board = document.getElementById('homePromotionBoard');
    if (!board) return;
    const dismissed = getDismissedHomePromotionVersions();
    const visible = homePromotions.filter(item => homePromotionUsesBoard(item) && dismissed[item.id] !== getHomePromotionVersion(item));
    board.classList.remove('is-loading');
    board.removeAttribute('aria-busy');
    if (!visible.length) {
        board.hidden = true;
        board.innerHTML = '';
        return;
    }
    board.hidden = false;
    board.className = `home-promotion-board${visible.length === 1 ? ' has-single' : ''}`;
    board.innerHTML = `
        <div class="home-promotion-board-head">
            <div><span>HEIGO BROADCAST</span><strong>联赛播报</strong></div>
            <p>重要荣誉、名单与联赛动态</p>
        </div>
        <div class="home-promotion-grid">
            ${visible.map((promotion, index) => `
                <article class="home-promotion-card is-${escapeHtml(promotion.theme || 'violet')} ${index === 0 ? 'is-featured' : ''}">
                    ${getHomePromotionMedia(promotion)}
                    <div class="home-promotion-copy">
                        <span>${escapeHtml(promotion.eyebrow || 'HEIGO Broadcast')}</span>
                        <h2>${escapeHtml(promotion.title || '')}</h2>
                        ${promotion.body ? `<p>${escapeHtml(promotion.body)}</p>` : ''}
                    </div>
                    <div class="home-promotion-actions">
                        ${promotion.action_kind !== 'none' && promotion.action_label ? `<button class="btn home-promotion-action" type="button" onclick="openHomePromotionAction(${Number(promotion.id)})">${escapeHtml(promotion.action_label)}</button>` : ''}
                    </div>
                    ${promotion.is_dismissible ? `<button class="home-promotion-dismiss" type="button" onclick="dismissHomePromotion(${Number(promotion.id)})" aria-label="关闭${escapeHtml(promotion.title || '宣传')}">${homePromotionIconSvg('close')}</button>` : ''}
                </article>
            `).join('')}
        </div>
    `;
}

function getHomePromotionModalPoints(promotion) {
    return String(promotion.body || '').split(/\r?\n/).map(line => line.trim()).filter(Boolean);
}

function getHomePromotionModalPointTag(title, index) {
    const normalized = String(title || '').replaceAll(' ', '').toLowerCase();
    if (normalized.includes('球队')) return 'TEAM';
    if (normalized.includes('联赛') || normalized.includes('积分')) return 'MATCH';
    if (normalized.includes('球员库') || normalized.includes('10w')) return 'DATABASE';
    if (normalized.includes('教练')) return 'PROFILE';
    return ['FOCUS', 'UPDATE', 'NOTICE', 'HEIGO'][index % 4];
}

function buildHomePromotionModalMarkup(promotion) {
    const points = getHomePromotionModalPoints(promotion);
    const hasPointGrid = points.length > 1;
    const bodyMarkup = hasPointGrid
        ? `<div class="home-promotion-modal-points">${points.map((line, index) => {
            const [rawTitle, ...descriptionParts] = line.split('｜');
            const title = rawTitle || `要点 ${index + 1}`;
            const description = descriptionParts.join('｜') || rawTitle;
            return `<article><span>${escapeHtml(getHomePromotionModalPointTag(title, index))}</span><strong>${escapeHtml(title)}</strong><p>${escapeHtml(description)}</p></article>`;
        }).join('')}</div>`
        : (promotion.body ? `<p class="home-promotion-modal-body">${escapeHtml(promotion.body)}</p>` : '');
    const media = promotion.image_url
        ? `<div class="home-promotion-modal-image"><img src="${escapeHtml(promotion.image_url)}" alt="" width="1600" height="900" decoding="async"></div>`
        : `<div class="home-promotion-modal-signal" aria-hidden="true"><i></i><i></i><i></i><b>${homePromotionIconSvg(promotion.icon)}</b></div>`;
    return `<section class="home-promotion-modal-card is-${escapeHtml(promotion.theme || 'violet')}">
        <div class="home-promotion-modal-hero">
            <div class="home-promotion-modal-brand"><span>HEIGO</span><em>COACH DESK</em></div>
            <div class="home-promotion-modal-heading">
                <span>${escapeHtml(promotion.eyebrow || 'HEIGO Broadcast')}</span>
                <h2 id="homePromotionModalTitle">${escapeHtml(promotion.title || '')}</h2>
                <p>少翻页面，多做决定。联赛信息和你的执教名片，都在这里。</p>
            </div>
            ${media}
        </div>
        ${bodyMarkup}
        <div class="home-promotion-modal-actions">
            ${promotion.action_kind !== 'none' && promotion.action_label ? `<button class="btn home-promotion-modal-primary" type="button" onclick="openHomePromotionModalAction(${Number(promotion.id)})">${escapeHtml(promotion.action_label)}</button>` : ''}
            <button class="home-promotion-modal-secondary" type="button" onclick="closeHomePromotionModal()">我知道了</button>
        </div>
        <footer><span>HEIGO · 联机联赛教练数据台</span><em>10W+ PLAYER DATABASE</em></footer>
    </section>`;
}

function showHomePromotionModal(promotion, options = {}) {
    const layer = document.getElementById('homePromotionModalLayer');
    const content = document.getElementById('homePromotionModalContent');
    if (!layer || !content || !promotion) return;
    activeHomePromotionModalId = options.preview ? 0 : Number(promotion.id);
    content.innerHTML = buildHomePromotionModalMarkup(promotion);
    layer.hidden = false;
    layer.setAttribute('aria-hidden', 'false');
    window.setTimeout(() => {
        layer.classList.add('active');
        document.getElementById('homePromotionModalClose')?.focus();
    }, 20);
}

function showPendingHomePromotionModal() {
    if (homePromotionModalShownThisVisit || document.body?.dataset?.activeTab !== 'home') return;
    if (currentCoachAccount?.authenticated || workspaceSessionState?.authenticated) return;
    const seen = getSeenHomePromotionModalVersions();
    const promotion = homePromotions.find(item => homePromotionUsesModal(item) && seen[item.id] !== getHomePromotionVersion(item));
    if (!promotion) return;
    homePromotionModalShownThisVisit = true;
    window.clearTimeout(homePromotionModalPendingTimer);
    homePromotionModalPendingTimer = window.setTimeout(() => {
        homePromotionModalPendingTimer = null;
        if (document.visibilityState !== 'visible' || document.body?.dataset?.activeTab !== 'home') {
            homePromotionModalShownThisVisit = false;
            return;
        }
        if (currentCoachAccount?.authenticated || workspaceSessionState?.authenticated) return;
        showHomePromotionModal(promotion);
    }, HOME_PROMOTION_MODAL_DELAY_MS);
}

function closeHomePromotionModal(options = {}) {
    const layer = document.getElementById('homePromotionModalLayer');
    if (!layer || layer.hidden) return;
    if (activeHomePromotionModalId && options.remember !== false) {
        const promotion = homePromotions.find(item => Number(item.id) === activeHomePromotionModalId);
        if (promotion) {
            const seen = getSeenHomePromotionModalVersions();
            seen[promotion.id] = getHomePromotionVersion(promotion);
            homePromotionStorageSet(HOME_PROMOTION_MODAL_SEEN_STORAGE_KEY, JSON.stringify(seen));
        }
    }
    layer.classList.remove('active');
    activeHomePromotionModalId = 0;
    window.setTimeout(() => {
        layer.hidden = true;
        layer.setAttribute('aria-hidden', 'true');
        const content = document.getElementById('homePromotionModalContent');
        if (content) content.innerHTML = '';
    }, 180);
}

async function openHomePromotionModalAction(promotionId) {
    closeHomePromotionModal();
    await openHomePromotionAction(promotionId);
}

function dismissHomePromotion(promotionId) {
    const promotion = homePromotions.find(item => Number(item.id) === Number(promotionId));
    if (!promotion) return;
    const dismissed = getDismissedHomePromotionVersions();
    dismissed[promotion.id] = getHomePromotionVersion(promotion);
    homePromotionStorageSet(HOME_PROMOTION_DISMISSED_STORAGE_KEY, JSON.stringify(dismissed));
    renderHomePromotions();
}

async function openHomePromotionAction(promotionId) {
    const promotion = homePromotions.find(item => Number(item.id) === Number(promotionId));
    if (!promotion || !promotion.action_target) return;
    if (promotion.action_kind === 'url') {
        window.location.assign(promotion.action_target);
        return;
    }
    const [tabName, rawSubtab, level] = String(promotion.action_target).split(':');
    const subtab = rawSubtab === 'rankings' ? 'playerRankings' : rawSubtab;
    if (tabName === 'team' && typeof openTeamCenter === 'function') {
        await openTeamCenter();
        return;
    }
    await showTab(tabName || 'home', null, {syncHistory: false});
    if (tabName === 'players' && typeof openFullLeagueRoster === 'function') {
        await openFullLeagueRoster({pushHistory: false, smooth: false});
    } else if (tabName === 'database' && subtab && typeof showDatabaseSubtab === 'function') {
        showDatabaseSubtab(subtab, {pushHistory: false});
    }
    if (tabName === 'competition' && subtab && typeof showCompetitionSubtab === 'function') showCompetitionSubtab(subtab);
    if (level && typeof setCompetitionLevel === 'function') setCompetitionLevel(level);
    if (typeof syncAppHistory === 'function') syncAppHistory('push');
}

async function loadHomePromotions(options = {}) {
    if (homePromotionsLoaded && options.force !== true) {
        renderHomePromotions();
        showPendingHomePromotionModal();
        return homePromotions;
    }
    if (homePromotionsLoading) return homePromotionsLoading;
    homePromotionsLoading = (async () => {
        try {
            const response = await fetchWithTimeout('/api/home-promotions');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            homePromotions = await response.json();
            homePromotionsLoaded = true;
            renderHomePromotions();
            showPendingHomePromotionModal();
            return homePromotions;
        } catch (error) {
            console.warn('主页宣传加载失败:', error);
            const board = document.getElementById('homePromotionBoard');
            if (board) board.hidden = true;
            return [];
        } finally {
            homePromotionsLoading = null;
        }
    })();
    return homePromotionsLoading;
}

document.addEventListener('keydown', event => {
    if (event.key === 'Escape') closeHomePromotionModal();
});

document.addEventListener('click', event => {
    const layer = document.getElementById('homePromotionModalLayer');
    if (layer && event.target === layer) closeHomePromotionModal();
});

const loadHomeChampionPromotions = loadHomePromotions;

function clearHeroSearchResults() {
    const container = document.getElementById('heroSearchResults');
    if (container) {
        container.innerHTML = '';
    }
}

function heroJsString(value) {
    return escapeHtml(JSON.stringify(String(value ?? '')));
}

function buildHeroSearchHaystack(values) {
    return values
        .map(value => [
            normalizeSearchText(value || ''),
            normalizeSearchTextLoose(value || ''),
            String(value || '').toLowerCase(),
        ])
        .flat()
        .filter(Boolean)
        .join(' ');
}

function heroMatchesQuery(values, query) {
    const queryKeys = buildSearchNormalizedKeys(query);
    const needles = [
        ...queryKeys.strictKeys,
        ...queryKeys.looseKeys,
        String(query || '').toLowerCase(),
    ].filter(Boolean);
    if (!needles.length) return false;
    const haystack = buildHeroSearchHaystack(values);
    return needles.some(needle => haystack.includes(needle));
}

function getHeroLocalSearchGroups(query, options = {}) {
    const leaguePlayers = Array.isArray(options.leaguePlayers) ? options.leaguePlayers : allPlayers;
    const teamMatches = (teams || [])
        .filter(team => heroMatchesQuery([team.name, team.manager, team.level], query))
        .slice(0, 5);
    const leaguePlayerMatches = (leaguePlayers || [])
        .filter(player => heroMatchesQuery([player.name, player.uid, player.team_name, player.position, player.nationality], query))
        .slice(0, 5);
    const coachMatches = ((window.coachesData && Array.isArray(window.coachesData.coaches)) ? window.coachesData.coaches : [])
        .filter(coach => heroMatchesQuery([coach.nickname, coach.team_name, coach.level, coach.title], query))
        .slice(0, 5);
    return {teamMatches, leaguePlayerMatches, coachMatches};
}

function isExactDatabaseMatch(player, query) {
    const queryKeys = buildSearchNormalizedKeys(query);
    const playerKeys = buildSearchNormalizedKeys(player.name || '');
    const allQueryKeys = [...queryKeys.strictKeys, ...queryKeys.looseKeys];
    const playerKeySet = new Set([...playerKeys.strictKeys, ...playerKeys.looseKeys]);
    if (!allQueryKeys.length) return false;
    return allQueryKeys.some(key => playerKeySet.has(key));
}

function renderHeroResultGroup(title, subtitle, itemsHtml, count, actionHtml = '') {
    if (!count) return '';
    return `
        <section class="home-result-group">
            <div class="home-result-group-head">
                <div>
                    <span>${escapeHtml(title)}</span>
                    <em>${escapeHtml(subtitle)}</em>
                </div>
                ${actionHtml}
            </div>
            <div class="home-results-list">${itemsHtml}</div>
        </section>
    `;
}

function renderHeroSearchResults(query, players, localGroups = getHeroLocalSearchGroups(query)) {
    const container = document.getElementById('heroSearchResults');
    if (!container) return;
    const databasePreview = players.slice(0, 6);
    const databaseMoreCount = Math.max(0, players.length - databasePreview.length);
    const teamMatches = localGroups.teamMatches || [];
    const leaguePlayerMatches = localGroups.leaguePlayerMatches || [];
    const coachMatches = localGroups.coachMatches || [];
    const totalLocalCount = teamMatches.length + leaguePlayerMatches.length + coachMatches.length;
    if (!players.length && !totalLocalCount) {
        container.innerHTML = `<div class="home-search-empty">没有找到和 “${escapeHtml(query)}” 相关的球队、球员或教练。</div>`;
        return;
    }
    container.innerHTML = `
        <div class="home-results-card surface-card">
            <div class="home-results-head">
                <div>
                    <span class="panel-kicker">Search Results</span>
                    <h3>找到 ${players.length + totalLocalCount} 条相关结果</h3>
                </div>
            </div>
            ${renderHeroResultGroup('球队', `${teamMatches.length} 条联赛球队`, teamMatches.map(team => `
                <button class="home-result-item home-result-team" onclick="viewTeamPlayers(${heroJsString(team.name || '')})">
                    <span class="home-result-main">
                        <strong>${escapeHtml(team.name || '-')}</strong>
                        <span>${escapeHtml(team.level || '-')} · 主教练 ${escapeHtml(team.manager || '-')}</span>
                    </span>
                    <span class="home-result-meta">联赛球队</span>
                </button>
            `).join(''), teamMatches.length)}
            ${renderHeroResultGroup('联赛球员', `${leaguePlayerMatches.length} 条当前名单`, leaguePlayerMatches.map(player => `
                <button class="home-result-item home-result-league-player" onclick="openDatabaseDetailFromHero(${Number(player.uid)})">
                    <span class="home-result-main">
                        <strong>${escapeHtml(player.name || '-')}</strong>
                        <span>${escapeHtml(player.position || '-')} · ${escapeHtml(String(player.age ?? '-'))} 岁 · ${escapeHtml(player.team_name || '-')}</span>
                    </span>
                    <span class="home-result-meta">球队中心</span>
                </button>
            `).join(''), leaguePlayerMatches.length)}
            ${renderHeroResultGroup('教练', `${coachMatches.length} 条教练主页`, coachMatches.map(coach => `
                <button class="home-result-item home-result-coach" onclick="openCoachProfileByName(${heroJsString(coach.nickname || '')})">
                    <span class="home-result-main">
                        <strong>${escapeHtml(coach.nickname || '-')}</strong>
                        <span>${escapeHtml(coach.team_name || '-')} · ${escapeHtml(coach.level || '-')}</span>
                    </span>
                    <span class="home-result-meta">教练主页</span>
                </button>
            `).join(''), coachMatches.length)}
            ${renderHeroResultGroup(
                '球员库',
                `${players.length} 条全库结果`,
                databasePreview.map(player => `
                    <button class="home-result-item" onclick="openDatabaseDetailFromHero(${player.uid}, {version: '${escapeHtml(player.data_version)}'})">
                        <span class="home-result-main">
                            <strong>${escapeHtml(player.name)}</strong>
                            <span>${escapeHtml(player.position || '-')} · ${escapeHtml(String(player.age ?? '-'))} 岁</span>
                        </span>
                        <span class="home-result-meta">${escapeHtml(player.heigo_club || '-')}</span>
                    </button>
                `).join(''),
                players.length,
                `<button class="btn btn-secondary home-result-group-action" onclick="openDatabaseResultsFromHero(decodeURIComponent('${encodeURIComponent(query)}'))">查看全部</button>`
            )}
            ${databaseMoreCount > 0 ? `<div class="home-search-more">球员库还有 ${databaseMoreCount} 条结果未展开。</div>` : ''}
        </div>
    `;
}

async function runHeroSearch(options = {}) {
    const heroSearch = document.getElementById('heroPlayerSearch');
    const query = heroSearch ? heroSearch.value.trim() : '';
    const shouldSyncHistory = options.pushHistory !== false;
    const historyMode = options.historyMode || 'push';

    if (!query) {
        clearHeroSearchResults();
        if (heroSearch) heroSearch.focus();
        return;
    }

    if (isAdminEntryQuery(query)) {
        clearHeroSearchResults();
        if (heroSearch) {
            heroSearch.value = '';
        }
        if (typeof openAdminEntry === 'function') {
            await openAdminEntry();
        } else {
            showAdminLoginPanel({reveal: true, focusLogin: false});
            showTab('admin', null, {syncHistory: false});
        }
        if (shouldSyncHistory && typeof syncAppHistory === 'function') {
            syncAppHistory(historyMode);
        }
        return;
    }

    const resultContainer = document.getElementById('heroSearchResults');
    if (resultContainer) {
        resultContainer.innerHTML = '<div class="home-search-empty">搜索中...</div>';
    }

    if (/^\d+$/.test(query)) {
        await openDatabaseDetailFromHero(query);
        return;
    }

    let leaguePlayers = [];
    try {
        const [, playerMatches] = await Promise.all([
            typeof ensureTeamsLoaded === 'function' ? ensureTeamsLoaded() : Promise.resolve(teams),
            fetchJsonOrThrow(`/api/players/search/${encodeURIComponent(query)}`),
            typeof ensureAppModule === 'function'
                ? ensureAppModule('coaches').then(() => ensureCoachesDataLoaded())
                : Promise.resolve(),
        ]);
        leaguePlayers = Array.isArray(playerMatches) ? playerMatches : [];
    } catch (error) {
        console.warn('首页搜索加载联赛数据失败:', error);
        if (typeof ensureCoachesDataLoaded === 'function') {
            try {
            await ensureCoachesDataLoaded();
            } catch (coachError) {
                console.warn('首页搜索加载教练数据失败:', coachError);
            }
        }
    }
    const localGroups = getHeroLocalSearchGroups(query, {leaguePlayers});
    const results = await fetchDatabaseSearchResults(query);
    const exactMatches = results.filter(player => isExactDatabaseMatch(player, query));
    const localMatchCount = localGroups.teamMatches.length + localGroups.leaguePlayerMatches.length + localGroups.coachMatches.length;
    if (exactMatches.length === 1 && !localMatchCount) {
        await openDatabaseDetailFromHero(exactMatches[0].uid, {version: exactMatches[0].data_version});
        return;
    }

    renderHeroSearchResults(query, results, localGroups);
}

async function openDatabaseDetailFromHero(uid, options = {}) {
    clearHeroSearchResults();
    await showTab('database', null, {syncHistory: false});
    if (typeof showPlayerDetail === 'function') {
        await showPlayerDetail(uid, {returnTab: 'home', ...options});
    }
}

async function openDatabaseResultsFromHero(query = '', options = {}) {
    const shouldSyncHistory = options.pushHistory !== false;
    const historyMode = options.historyMode || 'push';
    await showTab('database', null, {syncHistory: false});
    if (typeof activateDatabaseView === 'function') {
        activateDatabaseView('list');
    }
    const dbSearch = document.getElementById('dbPlayerSearch');
    if (dbSearch) {
        dbSearch.value = query;
    }
    if (query) {
        await searchDatabase(query, {pushHistory: shouldSyncHistory, historyMode});
        return;
    }
    if (shouldSyncHistory && typeof syncAppHistory === 'function') {
        syncAppHistory(historyMode);
    }
}

async function openAdvancedDatabaseSearchFromHero(options = {}) {
    const heroSearch = document.getElementById('heroPlayerSearch');
    const query = heroSearch ? heroSearch.value.trim() : '';
    const shouldSyncHistory = options.pushHistory !== false;
    const historyMode = options.historyMode || 'push';
    await showTab('database', null, {syncHistory: false});
    if (typeof activateDatabaseView === 'function') {
        activateDatabaseView('list');
    }
    if (typeof showDatabaseSubtab === 'function') {
        showDatabaseSubtab('search');
    }
    const dbSearch = document.getElementById('dbPlayerSearch');
    if (dbSearch) {
        dbSearch.value = query;
    }
    if (typeof toggleAdvancedSearchPanel === 'function') {
        await loadAttributeVersionCatalog();
        toggleAdvancedSearchPanel(true);
    }
    if (shouldSyncHistory && typeof syncAppHistory === 'function') {
        syncAppHistory(historyMode);
    }
}

async function goToTeamDirectory(options = {}) {
    await showTab('overview', null, {
        syncHistory: options.pushHistory !== false,
        historyMode: options.historyMode || 'push',
    });
    if (options.scroll === false) {
        return;
    }
    window.setTimeout(() => {
        document.getElementById('teamsTable')?.scrollIntoView({behavior: 'smooth', block: 'start'});
    }, 60);
}

document.getElementById('heroPlayerSearch')?.addEventListener('keypress', e => {
    if (e.key === 'Enter') runHeroSearch();
});
