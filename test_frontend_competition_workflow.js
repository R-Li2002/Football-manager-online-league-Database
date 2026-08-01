const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const competitionCode = fs.readFileSync(path.join(__dirname, 'static/js/app.competition.js'), 'utf8');
const appCode = fs.readFileSync(path.join(__dirname, 'static/app.js'), 'utf8');

assert.match(
    appCode,
    /competition:\s*\[[^\]]*app\.admin\.js[^\]]*app\.competition\.js[^\]]*\]/,
    'competition module must load the shared admin request helpers before app.competition.js',
);
assert.match(
    appCode,
    /tabName === 'competition'[\s\S]*?Promise\.all\(\[ensureAppModule\('competition'\), ensureTeamsLoaded\(\), ensurePlayersLoaded\(\)\]\)/,
    'competition must load league players before rendering match-event and suspension suggestions',
);
assert.match(competitionCode, /function invalidateCompetitionPlayerCaches\(\)/, 'competition player caches should be reset when the roster dataset changes');
assert.match(competitionCode, /competition\.suspensions\.team\.\$\{Number\(teamId\)\}/);
assert.match(competitionCode, /\/api\/export\/suspensions\.xlsx\?level=/);
assert.match(competitionCode, /导出 Excel/);
assert.match(
    competitionCode,
    /oninput="updateMatchEventSuggestions\(this, \$\{Number\(match\.id\)\}\)" onchange="scheduleMatchAutoSave/,
    'typing a scorer name should update suggestions without triggering an immediate auto-save',
);
assert.match(competitionCode, /<option value="own_goal"[^>]*>乌龙球<\/option>/, 'match events should offer an own-goal entry');
assert.match(competitionCode, /<details class="match-event-editor"/, 'match-event editing should use a native collapsible region');
assert.match(competitionCode, /<summary class="match-event-toggle">/, 'collapsed match-event editing should keep a clear accessible toggle');
assert.doesNotMatch(competitionCode, /<details class="match-event-editor"[^>]*\sopen(?:\s|>)/, 'match-event editing should default to collapsed so schedule cards stay aligned');
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
    let loadOptions = null;
    context.confirm = () => true;
    context.adminJsonRequest = async url => {
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
    context.currentCompetitionLevel = '冠军杯';
    context.canManageSchedule = true;

    await context.initializeCupBracket();

    assert.equal(requestedUrl, '/api/admin/cups/champions_cup/initialize?reset=true');
    assert.equal(loadOptions?.force, true);
    assert.equal(modalPayload.title, '初始化完成');
    assert.match(modalPayload.body, /重置 15 个对阵槽位/);
    assert.equal(initializeButton.disabled, false);
    assert.equal(initializeButton.textContent, '初始化冠军杯');
}

async function main() {
    assertWorkPanelShowsActionableRoundProgress();
    assertReviewActionsFollowBackendCapabilities();
    assertTaskFiltersUseBackendIssueCodes();
    assertSaveStateIsVisibleAndRetryable();
    await assertResponsibilityDialogRefreshesEligibleAccounts();
    await assertCupInitializationUsesExplicitResetAndFeedback();
}

main().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
