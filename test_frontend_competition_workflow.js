const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const competitionCode = fs.readFileSync(path.join(__dirname, 'static/js/app.competition.js'), 'utf8');
const appCode = fs.readFileSync(path.join(__dirname, 'static/app.js'), 'utf8');
const adminCode = fs.readFileSync(path.join(__dirname, 'static/js/app.admin.js'), 'utf8');
const coachesCode = fs.readFileSync(path.join(__dirname, 'static/js/app.coaches.js'), 'utf8');
const coreCode = fs.readFileSync(path.join(__dirname, 'static/js/app.core.js'), 'utf8');
const competitionCss = fs.readFileSync(path.join(__dirname, 'static/css/pages/competition.css'), 'utf8');

assert.match(
    appCode,
    /competition:\s*\['\/static\/js\/app\.competition\.js'\]/,
    'competition module should load only its own implementation',
);
assert.doesNotMatch(appCode, /competition:\s*\[[^\]]*app\.admin\.js/, 'competition should not pull in the full admin workspace');
assert.match(
    appCode,
    /tabName === 'competition'[\s\S]*?Promise\.all\(\[ensureAppModule\('competition'\), ensureTeamsLoaded\(\)\]\)/,
    'public competition entry should load teams without preloading every player',
);
assert.doesNotMatch(appCode, /tabName === 'competition'[\s\S]{0,220}ensurePlayersLoaded/, 'competition entry should not preload league players');
assert.match(coreCode, /async function workJsonRequest\(url, options = \{\}\)/, 'work requests should live in the shared core layer');
assert.match(competitionCode, /function ensureCompetitionPlayersLoaded\(\)/, 'competition should expose an on-demand player loader');
assert.match(competitionCode, /await ensureCompetitionPlayersLoaded\(\)/, 'competition editors should request players when needed');
assert.match(competitionCode, /workJsonRequest\(/, 'competition writes should use the lightweight shared work request');
assert.doesNotMatch(competitionCode, /adminJsonRequest\(/, 'competition should not depend on admin workspace requests');
assert.match(competitionCode, /function invalidateCompetitionPlayerCaches\(\)/, 'competition player caches should be reset when the roster dataset changes');
assert.match(competitionCode, /function getCupGroupMatchPairs\(group\)/, 'cup results should combine both legs against one opponent');
assert.match(competitionCode, /function addCupGroupResultPair\(groupNo\)/, 'cup score entry should add one home-and-away pair at a time');
assert.match(competitionCode, /currentCupResultsGroupNo/, 'cup score entry should preserve the selected group');
assert.match(competitionCode, /canManageCurrentCupStandings\(\)/, 'cup standings writes should use their own capability');
assert.match(competitionCode, /添加一组主客场对阵/, 'cup score entry should expose an incremental pair action');
assert.match(competitionCode, /cup-group-results-tabs/, 'cup score entry should split fixtures by group');
assert.match(coreCode, /var canManageCupStandings = false;/, 'cup standings capability should have independent frontend state');
assert.match(adminCode, /id="workspaceEditCupStandings"/, 'workspace account editor should expose cup standings as a separate permission');
assert.match(adminCode, /can_manage_cup_standings: Boolean/, 'workspace account updates should persist the cup standings permission');
assert.match(coachesCode, /id="coachAccountCupStandings"/, 'legacy coach account editor should expose the same permission');
assert.match(coreCode, /var canManageDailyReports = false;/, 'daily reports should have independent frontend capability state');
assert.match(adminCode, /id="workspaceEditDailyReports"/, 'workspace account editor should expose daily reports as a separate permission');
assert.match(coachesCode, /id="coachAccountDailyReports"/, 'legacy coach account editor should expose the daily report permission');
assert.match(competitionCss, /\.cup-group-pair-legs::before/, 'paired legs should use a visual home-and-away connector');
assert.match(competitionCode, /competition\.suspensions\.team\.\$\{Number\(teamId\)\}/);
assert.match(competitionCode, /\/api\/export\/suspensions\.xlsx\?level=/);
assert.match(competitionCode, /导出 Excel/);
assert.match(competitionCode, /SUSPENSION_IMAGE_MAX_BYTES = \(4 \* 1024 \* 1024\) - \(64 \* 1024\)/, 'suspension images should keep a safety margin below 4 MB');
assert.match(competitionCode, /function getCompetitionImagePixelRatio\(kind, target\)[\s\S]*?SUSPENSION_IMAGE_TARGET_PIXELS/, 'long suspension captures should use an area-aware pixel ratio');
assert.match(competitionCode, /async function compressSuspensionImageBlob\(blob, backgroundColor\)[\s\S]*?'image\/jpeg'/, 'oversized suspension PNG files should be recompressed as JPEG');
assert.match(competitionCode, /optimized\.blob[\s\S]*?buildCompetitionImageFileName\(kind, level, optimized\.extension\)/, 'the downloaded file should use the optimized blob and matching extension');
assert.match(
    competitionCode,
    /oninput="updateMatchEventSuggestions\(this, \$\{Number\(match\.id\)\}\)" onchange="scheduleMatchAutoSave/,
    'typing a scorer name should update suggestions without triggering an immediate auto-save',
);
assert.match(competitionCode, /<option value="own_goal"[^>]*>乌龙球<\/option>/, 'match events should offer an own-goal entry');
assert.match(competitionCode, /class="schedule-event-summary-bar"[^>]+openMatchEventEditor/, 'the fixed event summary should launch the match data dialog directly');
assert.doesNotMatch(competitionCode, /<details class="match-event-editor"/, 'match-event editing should no longer expand inside schedule cards');
assert.match(competitionCode, /function renderMatchEventEditorDialog\(match\)/, 'schedule editors should use a dedicated match data dialog');
assert.match(competitionCode, /data-match-event-team-tab="\$\{side\}"/, 'the dialog should switch between the home and away teams');
assert.match(competitionCode, /function getMatchEventPositionSortRank\(position\)/, 'match editor players should expose a position order');
assert.match(competitionCode, /getMatchEventPositionSortRank\(a\.position\) - getMatchEventPositionSortRank\(b\.position\)/, 'match editor players should sort by position before name');
assert.match(competitionCode, /球员 · 按位置/, 'match editor should describe the position-based order');
assert.match(competitionCode, /data-event-count="goal"/, 'each player row should expose a direct goal count');
assert.match(competitionCode, /data-event-count="assist"/, 'each player row should expose a direct assist count');
assert.match(competitionCode, /type="checkbox"[^>]+data-match-event-mvp/, 'each player row should allow selecting the match MVP');
assert.match(competitionCode, /data-match-own-goals/, 'the matrix editor should preserve own-goal reporting');
assert.match(competitionCode, /renderScheduleCompactMatchRow[\s\S]*?renderScheduleMatchEventSummary\(match\)/, 'desktop schedule cards should use a fixed-height event summary instead of full event lists');
assert.match(competitionCode, /mobile-schedule-edit-actions[\s\S]*?编辑比赛数据/, 'mobile cards should expose one unified match-data action');
assert.doesNotMatch(competitionCode, /比分与状态|openMobileScheduleEditDrawer|buildAdminMatchControlGroup/, 'schedule cards should no longer own a separate score editor');
assert.match(competitionCode, /function renderMatchEventScoreEditor\(match\)/, 'the match dialog should own score and status editing');
assert.match(competitionCode, /id="match-home-\$\{Number\(match\.id\)\}"[\s\S]*?id="match-away-\$\{Number\(match\.id\)\}"/, 'the unified dialog should render both score inputs');
assert.match(competitionCode, /<option value="scheduled"[\s\S]*?<option value="played"[\s\S]*?<option value="home_forfeit"/, 'the unified dialog should handle unplayed, normal and forfeit results');
assert.match(competitionCode, /id="matchEventModalSaveNext"[\s\S]*?saveMatchEventEditor\(true\)/, 'the dialog should support save-and-next continuous entry');
assert.match(competitionCode, /event\.key === 'Enter'[\s\S]*?sequence\[nextIndex\]/, 'Enter should advance through score and player number inputs');
assert.match(competitionCode, /statusSelect\?\.value === 'scheduled'[\s\S]*?statusSelect\.value = 'played'/, 'typing a score while unplayed should switch the match to normal play');
assert.match(competitionCode, /function clearMatchEventMatrixValues\(\)/, 'returning a match to unplayed should expose one complete event reset helper');
assert.match(competitionCode, /isScheduled && \(options\.markDirty !== false \|\| options\.resetScheduled === true\)[\s\S]*?clearMatchEventMatrixValues\(\)/, 'an explicit unplayed selection should clear score and player data');
assert.match(competitionCode, /function readMatchScorePayload\(matchId, eventOverride = null\)/, 'the dialog should submit result and event data together');
assert.match(competitionCode, /isOwnGoal \? null : findMatchEventPlayer/, 'own goals should not require a player lookup');
assert.match(competitionCode, /\['goal', 'own_goal'\]\.includes\(event\.event_type\)/, 'mobile match totals should include own goals');
assert.doesNotMatch(
    competitionCode,
    /function addMatchEventRow[\s\S]*?insertAdjacentHTML\('beforeend', renderMatchEventRow\(match\)\);\s*scheduleMatchAutoSave/,
    'adding an empty goal or assist row must not auto-save before the editor can be completed',
);
assert.match(
    competitionCode,
    /refreshCompetitionWorkSummary\(\{renderBoards: false\}\)/,
    'quiet match saves should refresh workflow counts without rebuilding the active schedule editor',
);
assert.match(competitionCode, /scheduleMatchSaveVersions = new Map\(\)/, 'match saves should version local edits');
assert.match(competitionCode, /scheduleMatchSaveInFlight = new Set\(\)/, 'only one save request per match should be in flight');
assert.match(competitionCode, /scheduleMatchSaveQueued = new Set\(\)/, 'new edits should queue a follow-up save');
assert.match(competitionCode, /function invalidateCompetitionAssignableAccounts\(\)/, 'permission changes should be able to invalidate the responsibility account cache');
assert.match(competitionCode, /loadCompetitionAssignableAccounts\(\{force: true\}\)/, 'the responsibility dialog should always request the latest eligible accounts');
assert.match(
    competitionCode,
    /scheduleMatchSaveQueued\.has\(numericMatchId\) \|\| !isCurrentAttempt\(\)/,
    'a stale save response should trigger the latest queued save instead of winning',
);
for (const issueLabel of ['待录比分', '缺少事件', '数据异常', '伤停待确认']) {
    assert.match(competitionCode, new RegExp(issueLabel), `competition status should expose ${issueLabel}`);
}

function createElement() {
    return {
        hidden: false,
        innerHTML: '',
        textContent: '',
        className: '',
        tabIndex: -1,
        setAttribute(name, value) {
            this[name] = String(value);
        },
    };
}

const workPanel = createElement();
const saveBadge = createElement();
const initializeButton = createElement();
initializeButton.textContent = '初始化冠军杯';
initializeButton.isConnected = true;
const elements = new Map([
    ['competitionWorkPanel', workPanel],
    ['initializeCupBracketButton', initializeButton],
]);

const document = {
    body: {classList: {add() {}, remove() {}}},
    addEventListener() {},
    getElementById(id) {
        return elements.get(id) || null;
    },
    querySelectorAll(selector) {
        return selector === '[data-match-save-id="101"]' ? [saveBadge] : [];
    },
    querySelector() {
        return null;
    },
};

const context = {
    console,
    document,
    window: {
        innerWidth: 1280,
        matchMedia() {
            return {matches: false};
        },
    },
    escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    },
    workspaceSessionState: {identity: {is_full_admin: true}},
};

vm.createContext(context);
vm.runInContext(competitionCode, context, {filename: 'app.competition.js'});

context.canManageSchedule = true;
context.canManageCupStandings = true;
context.canManageSuspensions = true;
context.currentCompetitionLevel = '超级';
context.competitionWorkData = {
    levels: [{
        level: '超级',
        round_start: 17,
        round_end: 18,
        round_label: '第 17-18 轮',
        workflow_status: 'in_progress',
        workflow_status_label: '处理中',
        schedule_principal_id: 'admin:root',
        schedule_display_name: 'root',
        suspension_principal_id: 'admin:root',
        suspension_display_name: 'root',
        is_my_schedule_task: true,
        is_my_suspension_task: true,
        can_confirm_suspensions: true,
        assignee_principal_id: 'admin:root',
        assignee_display_name: 'root',
        is_mine: true,
        can_submit: false,
        can_review: false,
        total_matches: 16,
        result_ready_count: 16,
        event_ready_count: 0,
        missing_result_count: 0,
        missing_event_count: 16,
        invalid_count: 0,
        suspension_confirmed: false,
        completion_ready: false,
        completed: false,
        changed_after_completion: false,
        changed_after_submission: false,
        history: [{action: 'assign', action_label: '分配负责人', operator_display_name: 'root', detail: '未分配 → root'}],
        tasks: [{
            match_id: 101,
            level: '超级',
            round_no: 17,
            home_team_name: 'Alpha',
            away_team_name: 'Beta',
            issue_codes: ['missing_events'],
            issue_messages: ['还缺少 3 个进球事件', '缺少本场最佳球员'],
        }],
    }],
};

function assertWorkPanelShowsActionableRoundProgress() {
    context.renderCompetitionWorkPanel();

    assert.equal(workPanel.hidden, false);
    assert.match(workPanel.innerHTML, /超级 · 第 17-18 轮/);
    assert.match(workPanel.innerHTML, /16 场待补事件/);
    assert.match(workPanel.innerHTML, /伤停待确认/);
    assert.match(workPanel.innerHTML, /展开工作台/);
    assert.match(workPanel.innerHTML, /competition-work-details" hidden/);
    assert.match(workPanel.innerHTML, /刷新数据/);
    assert.match(workPanel.innerHTML, /退出登录/);
    assert.match(workPanel.innerHTML, /16\/16/);
    assert.match(workPanel.innerHTML, /0\/16/);
    assert.match(workPanel.innerHTML, /确认本轮伤停/);
    assert.match(workPanel.innerHTML, /赛程与比赛事件/);
    assert.match(workPanel.innerHTML, /伤停/);
    assert.match(workPanel.innerHTML, /我的职责/);
    assert.match(workPanel.innerHTML, /设置级别职责/);
    assert.match(workPanel.innerHTML, /工作记录/);
    assert.doesNotMatch(workPanel.innerHTML, /提交复核/);

    context.toggleCompetitionWorkPanel();
    assert.match(workPanel.innerHTML, /收起工作台/);
    assert.doesNotMatch(workPanel.innerHTML, /competition-work-details" hidden/);
}

function assertReviewActionsFollowBackendCapabilities() {
    const summary = context.competitionWorkData.levels[0];
    summary.workflow_status = 'pending_review';
    summary.workflow_status_label = '待复核';
    summary.can_review = true;
    context.renderCompetitionWorkPanel();
    assert.match(workPanel.innerHTML, /退回修改/);
    assert.match(workPanel.innerHTML, /复核通过/);
}

function assertTaskFiltersUseBackendIssueCodes() {
    context.currentCompetitionWorkFilter = 'missing_events';
    assert.equal(context.getCompetitionWorkTasks().length, 1);
    context.currentCompetitionWorkFilter = 'missing_result';
    assert.equal(context.getCompetitionWorkTasks().length, 0);
}

function assertSaveStateIsVisibleAndRetryable() {
    context.setScheduleMatchSaveState(101, 'saving');
    assert.equal(saveBadge.textContent, '保存中...');
    assert.match(saveBadge.className, /is-saving/);

    context.setScheduleMatchSaveState(101, 'error', '网络失败，点击重试');
    assert.equal(saveBadge.textContent, '网络失败，点击重试');
    assert.match(saveBadge.className, /is-error/);
    assert.equal(saveBadge.role, 'button');
}

function assertMatchEventMatrixUsesRosterAndExistingValues() {
    context.teams = [
        {id: 1, name: 'Alpha'},
        {id: 2, name: 'Beta'},
    ];
    context.allPlayers = [
        {uid: 12, name: 'Zed Forward', position: 'AMRLC/ST', team_id: 1, team_name: 'Alpha'},
        {uid: 13, name: 'Aaron Winger', position: 'D/WB/M/R', team_id: 1, team_name: 'Alpha'},
        {uid: 11, name: 'Barry Midfielder', position: 'DM/MC', team_id: 1, team_name: 'Alpha'},
        {uid: 14, name: 'Charlie Anchor', position: 'DM', team_id: 1, team_name: 'Alpha'},
        {uid: 15, name: 'David Defender', position: 'D/WB/LC', team_id: 1, team_name: 'Alpha'},
        {uid: 16, name: 'Evan Keeper', position: 'GK', team_id: 1, team_name: 'Alpha'},
        {uid: 21, name: 'Bob Defender', position: 'DC', team_id: 2, team_name: 'Beta'},
    ];
    context.uiIconSvg = () => '';
    context.formatMatchScore = () => '-';
    context.isScheduleForfeitStatus = () => false;
    const html = context.renderMatchEventEditorDialog({
        id: 101,
        home_team_id: 1,
        home_team_name: 'Alpha',
        away_team_id: 2,
        away_team_name: 'Beta',
        home_score: 2,
        away_score: 1,
        status: 'played',
        events: [
            {team_name: 'Alpha', player_uid: 12, player_name: 'Zed Forward', event_type: 'goal', quantity: 2},
            {team_name: 'Alpha', player_uid: 11, player_name: 'Barry Midfielder', event_type: 'assist', quantity: 1},
            {team_name: 'Beta', player_uid: 21, player_name: 'Bob Defender', event_type: 'mvp', quantity: 1},
        ],
    });
    const orderedHomePlayers = ['Zed Forward', 'Aaron Winger', 'Barry Midfielder', 'Charlie Anchor', 'David Defender', 'Evan Keeper'];
    orderedHomePlayers.slice(1).forEach((playerName, index) => {
        assert.ok(html.indexOf(orderedHomePlayers[index]) < html.indexOf(playerName), `home players should render ${orderedHomePlayers[index]} before ${playerName}`);
    });
    assert.match(html, /data-player-name="Zed Forward"[\s\S]*?data-event-count="goal"/);
    assert.match(html, /value="2" placeholder="0" data-event-count="goal"/);
    assert.match(html, /data-player-name="Bob Defender"[\s\S]*?type="checkbox" checked data-match-event-mvp/);
    assert.match(html, /data-match-event-team-tab="home"/);
    assert.match(html, /data-match-event-team-tab="away"/);
}

function assertUnifiedMatchResultPayloads() {
    context.scheduleData = {matches: [{id: 101, level: '超级', home_score: null, away_score: null, status: 'scheduled', events: []}]};
    const homeInput = {value: ''};
    const awayInput = {value: ''};
    const statusSelect = {value: 'scheduled'};
    elements.set('match-home-101', homeInput);
    elements.set('match-away-101', awayInput);
    elements.set('match-status-101', statusSelect);

    assert.equal(JSON.stringify(context.readMatchScorePayload(101, [])), JSON.stringify({match_id: 101, home_score: null, away_score: null, status: 'scheduled', events: []}));

    const scheduledHtml = context.renderMatchEventScoreEditor({id: 101, home_team_name: 'Alpha', away_team_name: 'Beta', home_score: null, away_score: null, status: 'scheduled'});
    assert.doesNotMatch(scheduledHtml.match(/id="match-home-101"[^>]*>/)?.[0] || '', /readonly/, 'unplayed matches should keep score inputs editable');

    homeInput.value = '1';
    awayInput.value = '0';
    assert.equal(JSON.stringify(context.readMatchScorePayload(101, [])), JSON.stringify({match_id: 101, home_score: 1, away_score: 0, status: 'played', events: []}));
    assert.equal(statusSelect.value, 'played');

    statusSelect.value = 'played';
    homeInput.value = '3';
    awayInput.value = '2';
    assert.equal(JSON.stringify(context.readMatchScorePayload(101, [])), JSON.stringify({match_id: 101, home_score: 3, away_score: 2, status: 'played', events: []}));

    statusSelect.value = 'home_forfeit';
    assert.equal(JSON.stringify(context.readMatchScorePayload(101, [{event_type: 'goal'}])), JSON.stringify({match_id: 101, home_score: 0, away_score: 0, status: 'home_forfeit', events: []}));

    statusSelect.value = 'away_forfeit';
    assert.equal(JSON.stringify(context.readMatchScorePayload(101, [{event_type: 'goal'}])), JSON.stringify({match_id: 101, home_score: 2, away_score: 0, status: 'away_forfeit', events: []}));
    assert.equal(context.getForfeitRuleNote('home_forfeit'), '主队判负：本场记为 0:0，双方各得 1 分。');
    assert.equal(context.getForfeitRuleNote('away_forfeit'), '客队判负：本场记为 2:0，主队得 3 分、客队不得分。');
}

async function assertResponsibilityDialogRefreshesEligibleAccounts() {
    let fetchCalls = 0;
    let modalPayload = null;
    let accountItems = [
        {principal_id: 'admin:root', display_name: 'root', account_type: 'administrator', is_active: true, capabilities: ['schedule.write', 'suspensions.write']},
        {principal_id: 'coach:schedule', display_name: '赛程教练', account_type: 'coach_worker', is_active: true, capabilities: ['schedule.write']},
        {principal_id: 'coach:suspensions', display_name: '伤停教练', account_type: 'coach_worker', is_active: true, capabilities: ['suspensions.write']},
        {principal_id: 'coach:candidates', display_name: '候选名单教练', account_type: 'coach_worker', is_active: true, capabilities: ['coach_profile.write_self', 'candidate_lists.write']},
    ];
    context.fetch = async () => {
        fetchCalls += 1;
        return {ok: true, json: async () => ({items: accountItems})};
    };
    context.showModal = (title, body) => {
        modalPayload = {title, body};
    };

    await context.showCompetitionAssignmentDialog();
    assert.match(modalPayload.body, /赛程教练/);
    assert.match(modalPayload.body, /伤停教练/);
    assert.match(modalPayload.body, /候选名单教练/);
    assert.match(modalPayload.body, /需先授予赛程权限/);
    assert.match(modalPayload.body, /需先授予伤停权限/);

    accountItems = [...accountItems, {principal_id: 'coach:new-worker', display_name: '新工作人员', account_type: 'coach_worker', is_active: true, capabilities: ['schedule.write']}];
    await context.showCompetitionAssignmentDialog();
    assert.equal(fetchCalls, 2, 'opening the dialog again should bypass the previous account cache');
    assert.match(modalPayload.body, /新工作人员/);
}

async function assertCupInitializationUsesExplicitResetAndFeedback() {
    let requestedUrl = '';
    let modalPayload = null;
    let toastMessage = '';
    let loadOptions = null;
    context.showConfirmDialog = async () => true;
    context.workJsonRequest = async url => {
        requestedUrl = url;
        return {
            response: {ok: true},
            data: {success: true, message: '冠军杯已重新初始化，共重置 15 个对阵槽位'},
        };
    };
    context.loadCompetitionData = async options => {
        loadOptions = options;
    };
    context.showModal = (title, body) => {
        modalPayload = {title, body};
    };
    context.showSuccessToast = message => {
        toastMessage = message;
    };
    context.currentCompetitionLevel = '冠军杯';
    context.canManageSchedule = true;

    await context.initializeCupBracket();

    assert.equal(requestedUrl, '/api/admin/cups/champions_cup/initialize?reset=true');
    assert.equal(loadOptions?.force, true);
    assert.equal(modalPayload, null);
    assert.match(toastMessage, /重置 15 个对阵槽位/);
    assert.equal(initializeButton.disabled, false);
    assert.equal(initializeButton.textContent, '初始化冠军杯');
}

function assertCupGroupScoreEntryUsesIncrementalPairs() {
    context.currentCompetitionLevel = '冠军杯';
    context.canManageCupStandings = true;
    const group = {
        group_no: 1,
        group_name: 'A',
        matches: [
            {id: 501, round_no: 1, home_team_id: 10, home_team_name: 'Alpha', away_team_id: 20, away_team_name: 'Beta', status: 'scheduled', home_score: null, away_score: null},
            {id: 502, round_no: 2, home_team_id: 20, home_team_name: 'Beta', away_team_id: 10, away_team_name: 'Alpha', status: 'scheduled', home_score: null, away_score: null},
        ],
    };
    const pairs = context.getCupGroupMatchPairs(group);
    assert.equal(pairs.length, 1);
    assert.equal(pairs[0].matches.length, 2, 'both legs should share one score-entry card');
    let html = context.renderCupGroupResults({groups: [group]}, true);
    assert.match(html, /添加一组主客场对阵/);
    assert.doesNotMatch(html, /cup-group-score-501-home/, 'unstarted pairs should stay hidden until explicitly added');
    context.cupGroupVisiblePairKeys.add(pairs[0].key);
    html = context.renderCupGroupResults({groups: [group]}, true);
    assert.match(html, /cup-group-score-501-home/);
    assert.match(html, /cup-group-score-502-home/);
    assert.equal(context.canManageCurrentCupStandings(), true);
}

function assertMatchEventDraftAndUndoProtection() {
    assert.match(competitionCode, /MATCH_EVENT_DRAFT_STORAGE_PREFIX/);
    assert.match(competitionCode, /function persistMatchEventDraftNow/);
    assert.match(competitionCode, /function restoreStoredMatchEventDraft/);
    assert.match(competitionCode, /本机草稿/);
    assert.match(competitionCode, /homeScore:[\s\S]*?awayScore:[\s\S]*?status:/, 'drafts should preserve score and match status');
    assert.match(competitionCode, /actionLabel: '撤销'/);
    assert.match(competitionCode, /function restoreScheduleMatchSnapshot/);
}

async function main() {
    assertWorkPanelShowsActionableRoundProgress();
    assertReviewActionsFollowBackendCapabilities();
    assertTaskFiltersUseBackendIssueCodes();
    assertSaveStateIsVisibleAndRetryable();
    assertMatchEventMatrixUsesRosterAndExistingValues();
    assertUnifiedMatchResultPayloads();
    assertMatchEventDraftAndUndoProtection();
    await assertResponsibilityDialogRefreshesEligibleAccounts();
    await assertCupInitializationUsesExplicitResetAndFeedback();
    assertCupGroupScoreEntryUsesIncrementalPairs();
}

main().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
