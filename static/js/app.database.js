async function searchDatabase(nameOverride = null) {
    const name = nameOverride ?? document.getElementById('dbPlayerSearch').value.trim();
    if (!name) {
        document.getElementById('dbPlayersTable').innerHTML = '<div class="no-data">请输入球员姓名或 UID 进行搜索</div>';
        return;
    }
    if (/^\d+$/.test(name)) {
        await showPlayerDetail(name, {returnTab: 'database'});
        return;
    }
    document.getElementById('dbPlayersTable').innerHTML = '<div class="loading">搜索中...</div>';
    currentDbPlayers = await fetchDatabaseSearchResults(name);
    document.getElementById('dbSortField').value = '';
    renderDbPlayers(currentDbPlayers);
}

function sortDbPlayers() {
    const field = document.getElementById('dbSortField').value;
    const order = document.getElementById('dbSortOrder').value;
    if (!field) {
        renderDbPlayers(currentDbPlayers);
        return;
    }
    const sorted = [...currentDbPlayers];
    sorted.sort((a, b) => {
        const left = a[field];
        const right = b[field];
        if (typeof left === 'string' || typeof right === 'string') {
            const lhs = String(left || '');
            const rhs = String(right || '');
            return order === 'asc' ? lhs.localeCompare(rhs, 'zh-CN') : rhs.localeCompare(lhs, 'zh-CN');
        }
        return order === 'asc' ? Number(left || 0) - Number(right || 0) : Number(right || 0) - Number(left || 0);
    });
    renderDbPlayers(sorted);
}

function renderDbPlayers(players) {
    if (players.length === 0) {
        document.getElementById('dbPlayersTable').innerHTML = '<div class="no-data">没有找到符合条件的球员</div>';
        return;
    }
    document.getElementById('dbTableTitle').textContent = `球员库搜索结果 (${players.length} 名球员)`;
    const html = `
        <table>
            <thead>
                <tr>
                    <th>姓名</th>
                    <th>位置</th>
                    <th>年龄</th>
                    <th>CA</th>
                    <th>PA</th>
                    <th>国籍</th>
                    <th>HEIGO俱乐部</th>
                    <th>现实俱乐部</th>
                </tr>
            </thead>
            <tbody>
                ${players.map(p => `
                    <tr>
                        <td><span class="player-link" onclick="showPlayerDetail(${p.uid}, {returnTab: 'database'})">${escapeHtml(p.name)}</span></td>
                        <td>${escapeHtml(p.position || '-')}</td>
                        <td>${escapeHtml(p.age ?? '-')}</td>
                        <td><strong>${escapeHtml(p.ca ?? '-')}</strong></td>
                        <td>${escapeHtml(p.pa ?? '-')}</td>
                        <td>${escapeHtml(p.nationality || '-')}</td>
                        <td class="${p.heigo_club !== '大海' ? 'heigo-club' : ''}">${escapeHtml(p.heigo_club || '-')}</td>
                        <td class="real-club">${escapeHtml(p.club || '-')}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    document.getElementById('dbPlayersTable').innerHTML = html;
}

async function viewPlayerInDatabase(uid) {
    if (typeof selectRosterPlayer === 'function') {
        selectRosterPlayer(uid);
    }
    await showPlayerDetail(uid, {returnTab: 'players'});
}

async function showPlayerDetail(uid, options = {}) {
    const returnTab = options.returnTab || 'database';
    dbDetailReturnState = {tab: returnTab};
    currentGrowthPreviewStep = 0;
    playerReactionSubmitting = false;
    clearPlayerReactionCooldownTimer();
    clearPlayerReactionBounce();
    showTab('database');
    document.getElementById('dbListView').classList.remove('active');
    document.getElementById('dbDetailView').classList.add('active');
    document.getElementById('playerDetailContent').innerHTML = '<div class="loading">加载中...</div>';
    const detailToolbar = document.getElementById('playerDetailToolbar');
    if (detailToolbar) detailToolbar.innerHTML = '';
    const res = await fetch(`/api/attributes/${uid}`);
    const player = await res.json();
    if (!player) {
        document.getElementById('playerDetailContent').innerHTML = '<div class="no-data">找不到球员信息</div>';
        return;
    }
    if (typeof selectRosterPlayer === 'function') {
        selectRosterPlayer(uid);
    }
    currentDetailPlayer = player;
    syncComparedPlayerState(player);
    renderPlayerDetail(player);
}

function getAttrClass(val) {
    const normalized = Math.min(20, Math.max(1, Number(val) || 1));
    if (normalized <= 4) return 'attr-tier-1';
    if (normalized <= 8) return 'attr-tier-2';
    if (normalized <= 12) return 'attr-tier-3';
    if (normalized <= 16) return 'attr-tier-4';
    return 'attr-tier-5';
}

function renderAttributeList(attrs) {
    return attrs.map(attr => {
        const value = Number(attr.value) || 0;
        return `<div class="attribute-bar ${getAttrClass(value)}"><span class="attr-name">${escapeHtml(attr.label)}</span><span class="attr-value">${value}</span></div>`;
    }).join('');
}

function formatRadarValue(value) {
    const numeric = Number(value) || 0;
    return numeric % 1 === 0 ? String(numeric) : numeric.toFixed(2).replace(/\.0+$/, '').replace(/(\.\d*[1-9])0+$/, '$1');
}

function averageValues(values) {
    const numericValues = values.map(item => Number(item) || 0).filter(item => item > 0);
    if (!numericValues.length) return 0;
    const total = numericValues.reduce((sum, item) => sum + item, 0);
    return total / numericValues.length;
}

const HALF_STEP_PREVIEW_KEYS = new Set(['bravery', 'leadership']);
const STATIC_PREVIEW_KEYS = new Set(['aggression', 'determination', 'natural_fitness', 'flair']);
const DETAIL_PREVIEW_KEYS = [
    'reflexes', 'aerial_ability', 'kicking', 'handling', 'command_of_area', 'throwing', 'one_on_ones', 'communication',
    'tendency_to_punch', 'rushing_out', 'eccentricity',
    'passing', 'crossing', 'marking', 'technique', 'dribbling', 'tackling', 'finishing', 'first_touch', 'heading', 'long_shots',
    'penalty', 'corner', 'long_throws', 'free_kick',
    'flair', 'positioning', 'work_rate', 'concentration', 'decisions', 'leadership', 'aggression', 'vision',
    'teamwork', 'off_the_ball', 'determination', 'bravery', 'anticipation', 'composure',
    'acceleration', 'jumping', 'agility', 'stamina', 'balance', 'strength', 'pace', 'natural_fitness',
    'consistency', 'adaptability', 'pressure', 'ambition', 'professionalism', 'important_matches', 'injury_proneness',
    'versatility', 'sportsmanship', 'temperament', 'loyalty',
];
const GOALKEEPER_TECHNICAL_FIELDS = [
    ['reflexes', '反应'], ['aerial_ability', '制空能力'], ['kicking', '大脚开球'], ['handling', '手控球'],
    ['command_of_area', '拦截传中'], ['throwing', '手抛球'], ['one_on_ones', '一对一'], ['communication', '沟通'],
    ['tendency_to_punch', '击球倾向'], ['rushing_out', '出击'], ['eccentricity', '意外性'],
];
const OUTFIELD_TECHNICAL_FIELDS = [
    ['passing', '传球'], ['crossing', '传中'], ['marking', '盯人'], ['technique', '技术'],
    ['dribbling', '盘带'], ['tackling', '抢断'], ['finishing', '射门'], ['first_touch', '停球'],
    ['heading', '头球'], ['long_shots', '远射'],
];
const SET_PIECE_FIELDS = [
    ['penalty', '罚点球'], ['corner', '角球'], ['long_throws', '界外球'], ['free_kick', '任意球'],
];
const MENTAL_FIELDS = [
    ['flair', '才华'], ['positioning', '站位'], ['work_rate', '投入'], ['concentration', '集中'],
    ['decisions', '决断'], ['leadership', '领导力'], ['aggression', '侵略性'], ['vision', '视野'],
    ['teamwork', '团队合作'], ['off_the_ball', '无球跑动'], ['determination', '意志力'], ['bravery', '勇敢'],
    ['anticipation', '预判'], ['composure', '镇定'],
];
const PHYSICAL_FIELDS = [
    ['acceleration', '爆发力'], ['jumping', '弹跳'], ['agility', '灵活'], ['stamina', '耐力'],
    ['balance', '平衡'], ['strength', '强壮'], ['pace', '速度'], ['natural_fitness', '体质'],
];
const HIDDEN_FIELDS = [
    ['consistency', '稳定'], ['adaptability', '适应性'], ['pressure', '抗压'], ['ambition', '雄心'],
    ['professionalism', '职业'], ['important_matches', '大赛'], ['injury_proneness', '伤病'], ['versatility', '多样性'],
    ['sportsmanship', '体育道德'], ['temperament', '情绪控制'], ['loyalty', '忠诚'],
];
var playerDetailExportBusy = false;
var detailExportToastTimer = null;
var playerReactionSubmitting = false;
var playerReactionCooldownTimer = null;
var playerReactionAnimatingType = '';
var playerReactionAnimationTimer = null;
var compareDockExpanded = false;

function clampAttributeValue(value) {
    return Math.max(1, Math.min(20, Math.floor(Number(value) || 0)));
}

function getPreviewCaGain(step) {
    const lookup = [0, 11, 30, 50, 70, 90];
    return lookup[clampGrowthPreviewStep(step)] || 0;
}

function getWeakFootPreview(player, step) {
    if (clampGrowthPreviewStep(step) < 5) return null;
    const left = Number(player.left_foot) || 0;
    const right = Number(player.right_foot) || 0;
    if (!left || !right || left === right) return null;
    return left < right ? {label: '左脚', value: Math.min(20, left + 1)} : {label: '右脚', value: Math.min(20, right + 1)};
}

function buildPreviewPlayer(player, step) {
    const previewStep = clampGrowthPreviewStep(step);
    const previewPlayer = {...player};

    DETAIL_PREVIEW_KEYS.forEach(key => {
        const baseValue = Number(player[key]);
        if (!Number.isFinite(baseValue) || baseValue <= 0) return;
        if (STATIC_PREVIEW_KEYS.has(key)) {
            previewPlayer[key] = clampAttributeValue(baseValue);
            return;
        }
        const gain = HALF_STEP_PREVIEW_KEYS.has(key) ? Math.floor(previewStep / 2) : previewStep;
        previewPlayer[key] = clampAttributeValue(baseValue + gain);
    });

    const weakFootPreview = getWeakFootPreview(player, previewStep);
    if (weakFootPreview) {
        if (weakFootPreview.label === '左脚') {
            previewPlayer.left_foot = weakFootPreview.value;
        } else {
            previewPlayer.right_foot = weakFootPreview.value;
        }
    }

    previewPlayer.preview_step = previewStep;
    previewPlayer.preview_ca = (Number(player.ca) || 0) + getPreviewCaGain(previewStep);
    previewPlayer.preview_weak_foot = weakFootPreview;
    return previewPlayer;
}

function buildRadarProfile(player) {
    const isGoalkeeper = Number(player.pos_gk) >= 15;
    if (isGoalkeeper) {
        const profile = [
            ['扑救', averageValues([player.reflexes, player.handling, player.one_on_ones])],
            ['身体', averageValues([player.acceleration, player.agility, player.balance, player.strength, player.jumping])],
            ['速度', averageValues([player.acceleration, player.pace, player.agility, player.rushing_out])],
            ['精神', averageValues([player.anticipation, player.concentration, player.decisions, player.positioning])],
            ['指挥防线', averageValues([player.command_of_area, player.communication, player.leadership, player.positioning])],
            ['意外性', Number(player.eccentricity) || 0],
            ['制空', averageValues([player.aerial_ability, player.jumping, player.command_of_area, player.bravery])],
            ['大脚', averageValues([player.kicking, player.throwing, player.passing])],
        ];
        return profile.map(([label, value]) => ({label, value: value || 0}));
    }

    return [
        ['防守', averageValues([player.marking, player.tackling, player.positioning, player.anticipation])],
        ['身体', averageValues([player.stamina, player.strength, player.balance, player.natural_fitness])],
        ['速度', averageValues([player.acceleration, player.pace, player.agility])],
        ['创造', averageValues([player.passing, player.technique, player.vision, player.flair, player.first_touch])],
        ['进攻', averageValues([player.finishing, player.off_the_ball, player.first_touch, player.composure, player.long_shots])],
        ['技术', averageValues([player.dribbling, player.technique, player.passing, player.first_touch, player.crossing])],
        ['制空', averageValues([player.heading, player.jumping, player.bravery])],
        ['精神', averageValues([player.decisions, player.concentration, player.teamwork, player.determination, player.work_rate])],
    ].map(([label, value]) => ({label, value: value || 0}));
}

function buildComparisonRadarProfile(player) {
    const isGoalkeeper = Number(player.pos_gk) >= 15;
    if (isGoalkeeper) {
        return [
            ['防守', averageValues([player.command_of_area, player.one_on_ones, player.positioning, player.anticipation])],
            ['身体', averageValues([player.acceleration, player.agility, player.balance, player.strength, player.jumping])],
            ['速度', averageValues([player.acceleration, player.pace, player.agility, player.rushing_out])],
            ['创造', averageValues([player.throwing, player.kicking, player.passing, player.vision])],
            ['进攻', averageValues([player.one_on_ones, player.rushing_out, player.eccentricity])],
            ['技术', averageValues([player.reflexes, player.handling, player.kicking, player.throwing])],
            ['制空', averageValues([player.aerial_ability, player.jumping, player.command_of_area, player.bravery])],
            ['精神', averageValues([player.communication, player.concentration, player.decisions, player.determination, player.leadership])],
        ].map(([label, value]) => ({label, value: value || 0}));
    }

    return buildRadarProfile(player);
}

function getRadarThemePalette() {
    if (document.body.classList.contains('light-mode')) {
        return {
            gridStroke: 'rgba(76,79,105,0.08)',
            axisMetricStroke: 'rgba(76,79,105,0.1)',
            shapeFill: 'rgba(30, 102, 245, 0.14)',
            shapeStroke: 'rgba(30, 102, 245, 0.84)',
            pointFill: '#ffffff',
            pointStroke: 'rgba(30, 102, 245, 0.88)',
            labelFill: '#6c6f85',
        };
    }
    return {
        gridStroke: 'rgba(255,255,255,0.08)',
        axisMetricStroke: 'rgba(255,255,255,0.1)',
        shapeFill: 'rgba(122, 162, 247, 0.18)',
        shapeStroke: 'rgba(122, 162, 247, 0.94)',
        pointFill: '#f8fafc',
        pointStroke: 'rgba(122, 162, 247, 0.96)',
        labelFill: '#9aa5ce',
    };
}

function getComparisonRadarThemePalette() {
    if (document.body.classList.contains('light-mode')) {
        return {
            gridStroke: 'rgba(76,79,105,0.08)',
            labelFill: '#6c6f85',
            blueFill: 'rgba(32, 156, 255, 0.16)',
            blueStroke: 'rgba(32, 156, 255, 0.92)',
            redFill: 'rgba(255, 92, 114, 0.16)',
            redStroke: 'rgba(255, 92, 114, 0.92)',
        };
    }
    return {
        gridStroke: 'rgba(255,255,255,0.08)',
        labelFill: '#9aa5ce',
        blueFill: 'rgba(32, 156, 255, 0.16)',
        blueStroke: 'rgba(32, 156, 255, 0.92)',
        redFill: 'rgba(255, 92, 114, 0.16)',
        redStroke: 'rgba(255, 92, 114, 0.92)',
    };
}

function buildRadarShell(profile, options = {}) {
    if (!profile.length) return '';
    const size = options.size || 224;
    const center = size / 2;
    const radius = options.radius || 72;
    const labelRadius = options.labelRadius || 94;
    const stepCount = options.stepCount || 5;
    const shapeClass = options.shapeClass || 'radar-shape';
    const pointClass = options.pointClass || 'radar-point';
    const metricClass = options.metricClass || 'radar-metric';
    const palette = getRadarThemePalette();

    const getPoint = (index, value, distance) => {
        const angle = (-Math.PI / 2) + (index / profile.length) * Math.PI * 2;
        return {
            x: center + Math.cos(angle) * distance * value,
            y: center + Math.sin(angle) * distance * value,
        };
    };

    const grid = Array.from({length: stepCount}, (_, index) => {
        const ratio = (index + 1) / stepCount;
        const points = profile.map((_, axisIndex) => {
            const point = getPoint(axisIndex, ratio, radius);
            return `${point.x.toFixed(2)},${point.y.toFixed(2)}`;
        }).join(' ');
        return `<polygon class="radar-grid" points="${points}" style="fill:none;stroke:${palette.gridStroke};stroke-width:1;"></polygon>`;
    }).join('');

    const axes = profile.map((_, axisIndex) => {
        const edge = getPoint(axisIndex, 1, radius);
        return `<line class="radar-axis" x1="${center}" y1="${center}" x2="${edge.x.toFixed(2)}" y2="${edge.y.toFixed(2)}" style="fill:none;stroke:${palette.gridStroke};stroke-width:1;"></line>`;
    }).join('');

    const shapePoints = profile.map((item, axisIndex) => {
        const point = getPoint(axisIndex, Math.max(0, Math.min(20, item.value)) / 20, radius);
        return `${point.x.toFixed(2)},${point.y.toFixed(2)}`;
    }).join(' ');

    const metrics = profile.map((item, axisIndex) => {
        const normalized = Math.max(0, Math.min(20, item.value)) / 20;
        const point = getPoint(axisIndex, normalized, radius);
        const edge = getPoint(axisIndex, 1, radius);
        const label = getPoint(axisIndex, 1, labelRadius);
        const textAnchor = label.x < center - 10 ? 'end' : label.x > center + 10 ? 'start' : 'middle';
        const labelY = label.y > center ? label.y + 10 : label.y - 4;
        return `
            <g class="${metricClass}" tabindex="0" aria-label="${escapeHtml(item.label)} ${formatRadarValue(item.value)}">
                <line class="radar-axis-metric" x1="${point.x.toFixed(2)}" y1="${point.y.toFixed(2)}" x2="${edge.x.toFixed(2)}" y2="${edge.y.toFixed(2)}" style="stroke:${palette.axisMetricStroke};stroke-width:1;"></line>
                <circle class="${pointClass}" cx="${point.x.toFixed(2)}" cy="${point.y.toFixed(2)}" r="4" style="fill:${palette.pointFill};stroke:${palette.pointStroke};stroke-width:1.35;"></circle>
                <text class="radar-label" x="${label.x.toFixed(2)}" y="${labelY.toFixed(2)}" text-anchor="${textAnchor}" style="fill:${palette.labelFill};">${escapeHtml(item.label)}</text>
                <circle class="radar-hit" cx="${point.x.toFixed(2)}" cy="${point.y.toFixed(2)}" r="12" style="fill:transparent;stroke:transparent;"></circle>
                <title>${escapeHtml(item.label)}：${formatRadarValue(item.value)}</title>
            </g>
        `;
    }).join('');

    return `
        <svg class="player-radar-svg" viewBox="0 0 ${size} ${size}" role="img" aria-label="球员能力雷达图">
            ${grid}
            ${axes}
            <polygon class="${shapeClass}" points="${shapePoints}" style="fill:${palette.shapeFill};stroke:${palette.shapeStroke};stroke-width:1.8;"></polygon>
            ${metrics}
        </svg>
    `;
}

function buildRadarSvg(profile) {
    if (!profile.length) return '';
    return `
        <div class="player-radar-card">
            <div class="player-radar-title">能力雷达</div>
            <div class="player-radar-figure">
                ${buildRadarShell(profile)}
            </div>
        </div>
    `;
}

function buildComparisonRadarSvg(leftPlayer, rightPlayer) {
    const leftProfile = buildComparisonRadarProfile(leftPlayer);
    const rightProfile = buildComparisonRadarProfile(rightPlayer);
    if (!leftProfile.length || !rightProfile.length) return '';

    const size = 288;
    const center = size / 2;
    const radius = 96;
    const labelRadius = 122;
    const stepCount = 5;
    const palette = getComparisonRadarThemePalette();

    const getPoint = (index, value, distance) => {
        const angle = (-Math.PI / 2) + (index / leftProfile.length) * Math.PI * 2;
        return {
            x: center + Math.cos(angle) * distance * value,
            y: center + Math.sin(angle) * distance * value,
        };
    };

    const buildPoints = profile => profile.map((item, axisIndex) => {
        const point = getPoint(axisIndex, Math.max(0, Math.min(20, item.value)) / 20, radius);
        return `${point.x.toFixed(2)},${point.y.toFixed(2)}`;
    }).join(' ');

    const grid = Array.from({length: stepCount}, (_, index) => {
        const ratio = (index + 1) / stepCount;
        const points = leftProfile.map((_, axisIndex) => {
            const point = getPoint(axisIndex, ratio, radius);
            return `${point.x.toFixed(2)},${point.y.toFixed(2)}`;
        }).join(' ');
        return `<polygon class="comparison-radar-grid" points="${points}" style="fill:none;stroke:${palette.gridStroke};stroke-width:1;"></polygon>`;
    }).join('');

    const axes = leftProfile.map((item, axisIndex) => {
        const edge = getPoint(axisIndex, 1, radius);
        const label = getPoint(axisIndex, 1, labelRadius);
        const textAnchor = label.x < center - 10 ? 'end' : label.x > center + 10 ? 'start' : 'middle';
        const labelY = label.y > center ? label.y + 10 : label.y - 4;
        return `
            <line class="comparison-radar-axis" x1="${center}" y1="${center}" x2="${edge.x.toFixed(2)}" y2="${edge.y.toFixed(2)}" style="fill:none;stroke:${palette.gridStroke};stroke-width:1;"></line>
            <text class="comparison-radar-label" x="${label.x.toFixed(2)}" y="${labelY.toFixed(2)}" text-anchor="${textAnchor}" style="fill:${palette.labelFill};">${escapeHtml(item.label)}</text>
        `;
    }).join('');

    return `
        <section class="comparison-radar-card">
            <div class="comparison-radar-head">
                <div class="comparison-radar-legend">
                    <span class="comparison-legend-item is-blue"><span class="comparison-legend-swatch"></span>${escapeHtml(leftPlayer.name)}</span>
                    <span class="comparison-legend-item is-red"><span class="comparison-legend-swatch"></span>${escapeHtml(rightPlayer.name)}</span>
                </div>
            </div>
            <div class="comparison-radar-shell">
                <svg class="comparison-radar-svg" viewBox="0 0 ${size} ${size}" role="img" aria-label="球员对比雷达图">
                    ${grid}
                    ${axes}
                    <polygon class="comparison-radar-shape comparison-radar-shape-blue" points="${buildPoints(leftProfile)}" style="fill:${palette.blueFill};stroke:${palette.blueStroke};stroke-width:2.2;"></polygon>
                    <polygon class="comparison-radar-shape comparison-radar-shape-red" points="${buildPoints(rightProfile)}" style="fill:${palette.redFill};stroke:${palette.redStroke};stroke-width:2.2;"></polygon>
                </svg>
            </div>
        </section>
    `;
}

const POSITION_MARKERS = [
    {key: 'pos_st', label: 'ST', x: 50, y: 12},
    {key: 'pos_aml', label: 'AML', x: 10.5, y: 24},
    {key: 'pos_amc', label: 'AMC', x: 50, y: 24},
    {key: 'pos_amr', label: 'AMR', x: 89.5, y: 24},
    {key: 'pos_ml', label: 'ML', x: 10.5, y: 42},
    {key: 'pos_mc', label: 'MC', x: 50, y: 42},
    {key: 'pos_mr', label: 'MR', x: 89.5, y: 42},
    {key: 'pos_dm', label: 'DM', x: 50, y: 62},
    {key: 'pos_wbl', label: 'WBL', x: 10.5, y: 62},
    {key: 'pos_wbr', label: 'WBR', x: 89.5, y: 62},
    {key: 'pos_dl', label: 'DL', x: 10.5, y: 82},
    {key: 'pos_dc', label: 'DC', x: 50, y: 82},
    {key: 'pos_dr', label: 'DR', x: 89.5, y: 82},
    {key: 'pos_gk', label: 'GK', x: 50, y: 94},
];
const POSITION_COMPARISON_FIELDS = POSITION_MARKERS.map(({key, label}) => [key, label]);

function getPitchMarkerTone(score) {
    if (score <= 1) return 'pitch-rating-gray';
    if (score <= 9) return 'pitch-rating-red';
    if (score <= 14) return 'pitch-rating-yellow';
    return 'pitch-rating-green';
}

function getPitchTooltipClasses(marker) {
    const classes = [];
    if (marker.y <= 24) classes.push('tooltip-below');
    if (marker.x <= 12) classes.push('tooltip-align-left');
    if (marker.x >= 88) classes.push('tooltip-align-right');
    return classes.join(' ');
}

function buildPositionMap(player) {
    const activeMarkers = POSITION_MARKERS
        .map(marker => ({...marker, score: Number(player[marker.key]) || 0}))
        .filter(marker => marker.score > 1);

    if (!activeMarkers.length) return '';

    const markers = activeMarkers.map(marker => `
        <button class="pitch-marker ${getPitchMarkerTone(marker.score)}" style="left:${marker.x}%;top:${marker.y}%;background:none;border:none;padding:0;" type="button" aria-label="${marker.label} \u719f\u7ec3\u5ea6 ${marker.score}">
            <span class="pitch-marker-core">${marker.label}</span>
            <span class="pitch-marker-tooltip ${getPitchTooltipClasses(marker)}">${marker.label} \u00b7 \u719f\u7ec3\u5ea6 ${marker.score}</span>
        </button>
    `).join('');

    return `
        <div class="position-map-card">
            <h4>位置熟练度图</h4>
            <div class="pitch-board">
                <div class="pitch-field">
                    <span class="pitch-half-line"></span>
                    <span class="pitch-center-circle"></span>
                    <span class="pitch-center-spot"></span>
                    <span class="pitch-top-box"></span>
                    <span class="pitch-bottom-box"></span>
                    <span class="pitch-top-goal-box"></span>
                    <span class="pitch-bottom-goal-box"></span>
                    ${markers}
                </div>
            </div>
        </div>
    `;
}

function clampGrowthPreviewStep(step) {
    return Math.max(0, Math.min(5, Number(step) || 0));
}

function mapFieldCollection(definitions, player) {
    return definitions.map(([key, label]) => ({key, label, value: player[key]}));
}

function getPlayerFieldCollections(player) {
    const isGoalkeeper = Number(player.pos_gk) >= 15;
    return {
        isGoalkeeper,
        technical: mapFieldCollection(isGoalkeeper ? GOALKEEPER_TECHNICAL_FIELDS : OUTFIELD_TECHNICAL_FIELDS, player),
        setPieces: isGoalkeeper ? [] : mapFieldCollection(SET_PIECE_FIELDS, player),
        mental: mapFieldCollection(MENTAL_FIELDS, player),
        physical: mapFieldCollection(PHYSICAL_FIELDS, player),
        hidden: mapFieldCollection(HIDDEN_FIELDS, player),
        positions: mapFieldCollection(POSITION_COMPARISON_FIELDS, player),
    };
}

function formatHeight(value) {
    const height = Number(value);
    if (!height) return '-';
    return `${height} cm`;
}

function buildPlayerInfoRows(player, previewPlayer) {
    const caGrowth = getPreviewCaGain(currentGrowthPreviewStep);
    return [
        ['国籍', player.nationality || '-'],
        ['年龄', player.age ?? '-'],
        ['生日', player.birth_date || '未知'],
        ['位置', player.position || '-'],
        ['CA / PA', `<strong>${escapeHtml(previewPlayer.preview_ca ?? player.ca ?? '-')}</strong>${caGrowth > 0 ? `<span class="growth-indicator growth-positive">(+${caGrowth})</span>` : ''} / ${escapeHtml(player.pa ?? '-')}`, true],
        ['左脚', previewPlayer.left_foot ?? '-'],
        ['右脚', previewPlayer.right_foot ?? '-'],
        ['身高', formatHeight(player.height)],
        ['HEIGO俱乐部', `<span class="${player.heigo_club !== '大海' ? 'heigo-club' : ''}">${escapeHtml(player.heigo_club || '-')}</span>`, true],
        ['现实俱乐部', `<span class="real-club">${escapeHtml(player.club || '-')}</span>`, true],
    ];
}

function normalizeReactionSummary(summary = {}) {
    const cooldownSeconds = Math.max(0, Number(summary.cooldown_seconds) || 0);
    return {
        flowers: Math.max(0, Number(summary.flowers) || 0),
        eggs: Math.max(0, Number(summary.eggs) || 0),
        can_react: summary.can_react !== false && cooldownSeconds === 0,
        cooldown_seconds: cooldownSeconds,
        next_available_at: summary.next_available_at || null,
    };
}

function clearPlayerReactionCooldownTimer() {
    if (playerReactionCooldownTimer) {
        window.clearInterval(playerReactionCooldownTimer);
        playerReactionCooldownTimer = null;
    }
}

function ensurePlayerReactionSummary(player) {
    if (!player) return normalizeReactionSummary();
    player.reaction_summary = normalizeReactionSummary(player.reaction_summary);
    return player.reaction_summary;
}

function renderPlayerReactionControls(player) {
    const reactionHost = document.getElementById('playerReactionControls');
    if (!reactionHost || !player) return;

    const summary = ensurePlayerReactionSummary(player);
    const cooldownSeconds = Math.max(0, Number(summary.cooldown_seconds) || 0);
    const disabled = playerReactionSubmitting || cooldownSeconds > 0;
    const flowerAnimating = playerReactionAnimatingType === 'flower';
    const eggAnimating = playerReactionAnimatingType === 'egg';
    const flowerTitle = playerReactionSubmitting
        ? '正在送花'
        : cooldownSeconds > 0
            ? `${cooldownSeconds} 秒后可再次送花`
            : '送花';
    const eggTitle = playerReactionSubmitting
        ? '正在踩鸡蛋'
        : cooldownSeconds > 0
            ? `${cooldownSeconds} 秒后可再次踩鸡蛋`
            : '踩鸡蛋';

    reactionHost.innerHTML = `
        <div class="player-reaction-panel" aria-label="球员互动">
            <div class="player-reaction-buttons">
                <button
                    class="player-reaction-button is-flower ${flowerAnimating ? 'is-bouncing' : ''}"
                    type="button"
                    onclick="submitPlayerReaction('flower')"
                    title="${flowerTitle}"
                    aria-label="送花 ${summary.flowers}"
                    ${disabled ? 'disabled' : ''}
                >
                    <span class="player-reaction-icon is-flower" aria-hidden="true"></span>
                    <span class="player-reaction-count ${flowerAnimating ? 'is-popping' : ''}">${summary.flowers}</span>
                </button>
                <button
                    class="player-reaction-button is-egg ${eggAnimating ? 'is-bouncing' : ''}"
                    type="button"
                    onclick="submitPlayerReaction('egg')"
                    title="${eggTitle}"
                    aria-label="踩鸡蛋 ${summary.eggs}"
                    ${disabled ? 'disabled' : ''}
                >
                    <span class="player-reaction-icon is-egg" aria-hidden="true"></span>
                    <span class="player-reaction-count ${eggAnimating ? 'is-popping' : ''}">${summary.eggs}</span>
                </button>
            </div>
        </div>
    `;
}

function syncPlayerReactionControls() {
    if (!currentDetailPlayer) return;
    renderPlayerReactionControls(currentDetailPlayer);
}

function clearPlayerReactionBounce() {
    playerReactionAnimatingType = '';
    if (playerReactionAnimationTimer) {
        window.clearTimeout(playerReactionAnimationTimer);
        playerReactionAnimationTimer = null;
    }
}

function triggerPlayerReactionBounce(reactionType) {
    clearPlayerReactionBounce();
    playerReactionAnimatingType = reactionType;
    if (currentDetailPlayer) {
        renderPlayerReactionControls(currentDetailPlayer);
    }
    playerReactionAnimationTimer = window.setTimeout(() => {
        playerReactionAnimatingType = '';
        playerReactionAnimationTimer = null;
        if (currentDetailPlayer) {
            renderPlayerReactionControls(currentDetailPlayer);
        }
    }, 320);
}

function startPlayerReactionCooldownTimer() {
    clearPlayerReactionCooldownTimer();
    if (!currentDetailPlayer) return;

    const summary = ensurePlayerReactionSummary(currentDetailPlayer);
    if (summary.cooldown_seconds <= 0) return;

    playerReactionCooldownTimer = window.setInterval(() => {
        if (!currentDetailPlayer) {
            clearPlayerReactionCooldownTimer();
            return;
        }

        const activeSummary = ensurePlayerReactionSummary(currentDetailPlayer);
        if (activeSummary.cooldown_seconds <= 1) {
            currentDetailPlayer.reaction_summary = {
                ...activeSummary,
                cooldown_seconds: 0,
                can_react: true,
                next_available_at: null,
            };
            renderPlayerReactionControls(currentDetailPlayer);
            clearPlayerReactionCooldownTimer();
            return;
        }

        currentDetailPlayer.reaction_summary = {
            ...activeSummary,
            cooldown_seconds: activeSummary.cooldown_seconds - 1,
            can_react: false,
        };
        renderPlayerReactionControls(currentDetailPlayer);
    }, 1000);
}

async function submitPlayerReaction(reactionType) {
    if (!currentDetailPlayer || playerReactionSubmitting) return;

    const summary = ensurePlayerReactionSummary(currentDetailPlayer);
    if (summary.cooldown_seconds > 0) {
        showDetailExportToast(`请等待 ${summary.cooldown_seconds} 秒后再互动`, 'warning');
        renderPlayerReactionControls(currentDetailPlayer);
        return;
    }

    triggerPlayerReactionBounce(reactionType);
    playerReactionSubmitting = true;
    renderPlayerReactionControls(currentDetailPlayer);

    try {
        const response = await fetch(`/api/attributes/${currentDetailPlayer.uid}/reactions/${reactionType}`, {
            method: 'POST',
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload?.detail || payload?.message || '互动请求失败');
        }

        currentDetailPlayer.reaction_summary = normalizeReactionSummary(payload.summary);
        renderPlayerReactionControls(currentDetailPlayer);
        startPlayerReactionCooldownTimer();
        showDetailExportToast(payload.message || (reactionType === 'flower' ? '已送花' : '已踩鸡蛋'), payload.accepted ? 'success' : 'warning');
    } catch (error) {
        console.error('Failed to submit player reaction:', error);
        showModal('互动失败', '当前互动没有提交成功，请稍后重试。');
    } finally {
        playerReactionSubmitting = false;
        if (currentDetailPlayer) {
            renderPlayerReactionControls(currentDetailPlayer);
        }
    }
}

function getPlayerDetailCaptureNode() {
    return document.querySelector('#playerDetailContent .player-detail-container');
}

function ensureDetailExportToast() {
    let toast = document.getElementById('detailExportToast');
    if (toast) return toast;

    toast = document.createElement('div');
    toast.id = 'detailExportToast';
    toast.className = 'detail-export-toast';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    document.body.appendChild(toast);
    return toast;
}

function showDetailExportToast(message, tone = 'success') {
    const toast = ensureDetailExportToast();
    toast.textContent = message;
    toast.className = `detail-export-toast is-visible is-${tone}`;
    window.clearTimeout(detailExportToastTimer);
    detailExportToastTimer = window.setTimeout(() => {
        toast.classList.remove('is-visible');
    }, 2400);
}

function buildPlayerCaptureFileName(player) {
    const safeName = String(player?.name || 'player')
        .trim()
        .replace(/[\\/:*?"<>|]+/g, '_')
        .replace(/\s+/g, '_')
        .replace(/^_+|_+$/g, '') || 'player';
    return `${safeName}_${player?.uid || 'detail'}.png`;
}

function buildPlayerDetailCaptureSurface(sourceNode) {
    const captureRoot = document.createElement('div');
    captureRoot.className = 'capture-export-root';

    const captureFrame = document.createElement('div');
    captureFrame.className = 'player-detail-capture-frame';

    const sourceRect = sourceNode.getBoundingClientRect();
    const exportWidth = Math.ceil(Math.max(sourceNode.scrollWidth || 0, sourceRect.width || 0, 1180));
    captureFrame.style.width = `${exportWidth + 64}px`;

    const clonedDetail = sourceNode.cloneNode(true);
    clonedDetail.classList.add('is-capture-export');
    captureFrame.appendChild(clonedDetail);
    captureRoot.appendChild(captureFrame);
    document.body.appendChild(captureRoot);

    return {captureRoot, captureFrame};
}

async function copyBlobToClipboard(blob) {
    if (!navigator.clipboard || typeof ClipboardItem === 'undefined') {
        throw new Error('clipboard-unavailable');
    }
    await navigator.clipboard.write([
        new ClipboardItem({
            [blob.type]: blob,
        }),
    ]);
}

function downloadBlob(blob, fileName) {
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1200);
}

async function copyCurrentPlayerDetailImage() {
    if (playerDetailExportBusy) return;
    if (!currentDetailPlayer) {
        showModal('暂时无法复制', '当前没有可导出的球员详情。');
        return;
    }
    if (!window.htmlToImage || typeof window.htmlToImage.toBlob !== 'function') {
        showModal('导出组件未就绪', '页面截图组件加载失败，请刷新页面后重试。');
        return;
    }

    const sourceNode = getPlayerDetailCaptureNode();
    if (!sourceNode) {
        showModal('暂时无法复制', '未找到当前球员详情内容。');
        return;
    }

    playerDetailExportBusy = true;
    renderGrowthPreviewToolbar(currentDetailPlayer);

    let captureRoot = null;
    try {
        if (document.fonts?.ready) {
            await document.fonts.ready;
        }

        const captureSurface = buildPlayerDetailCaptureSurface(sourceNode);
        captureRoot = captureSurface.captureRoot;

        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));

        const blob = await window.htmlToImage.toBlob(captureSurface.captureFrame, {
            cacheBust: true,
            pixelRatio: Math.max(2, Math.min(3, window.devicePixelRatio || 1)),
        });

        if (!blob) {
            throw new Error('capture-blob-empty');
        }

        const fileName = buildPlayerCaptureFileName(currentDetailPlayer);
        try {
            await copyBlobToClipboard(blob);
            showDetailExportToast('已复制球员图到剪贴板');
        } catch (clipboardError) {
            downloadBlob(blob, fileName);
            showDetailExportToast('浏览器未允许写入剪贴板，已自动下载 PNG', 'warning');
        }
    } catch (error) {
        console.error('Failed to export player detail image:', error);
        showModal('生成球员图失败', '请刷新页面后重试。如果问题持续存在，我可以继续排查具体样式节点。');
    } finally {
        if (captureRoot) captureRoot.remove();
        playerDetailExportBusy = false;
        if (currentDetailPlayer) {
            renderGrowthPreviewToolbar(currentDetailPlayer);
        }
    }
}

function renderGrowthPreviewToolbar(player) {
    const detailToolbar = document.getElementById('playerDetailToolbar');
    if (!detailToolbar || !player) return;

    normalizeCompareSlots();
    currentGrowthPreviewStep = clampGrowthPreviewStep(currentGrowthPreviewStep);

    const labels = ['当前', '+1', '+2', '+3', '+4', '+5'];
    const previewCa = (Number(player.ca) || 0) + getPreviewCaGain(currentGrowthPreviewStep);
    const weakFootPreview = getWeakFootPreview(player, currentGrowthPreviewStep);
    const compareSlotIndex = getCompareSlotIndex(player.uid);

    detailToolbar.innerHTML = `
        <div class="detail-toolbar-actions">
            <button
                id="copyPlayerDetailButton"
                class="btn detail-toolbar-button detail-copy-button"
                type="button"
                onclick="copyCurrentPlayerDetailImage()"
                ${playerDetailExportBusy ? 'disabled' : ''}
            >
                ${playerDetailExportBusy ? '生成中...' : '复制球员图'}
            </button>
            <button
                class="btn detail-toolbar-button detail-compare-button ${compareSlotIndex !== -1 ? 'is-active' : ''}"
                type="button"
                onclick="queueCurrentPlayerForCompare()"
            >
                ${compareSlotIndex !== -1 ? `已加入对比 ${compareSlotIndex + 1}` : '加入对比'}
            </button>
            <div class="detail-growth-control" aria-label="成长预览进度条">
                <div class="detail-growth-scale">
                    ${labels.map((label, index) => `<span class="detail-growth-label ${index === currentGrowthPreviewStep ? 'is-active' : ''}">${label}</span>`).join('')}
                </div>
                <div class="growth-preview-slider-wrap">
                    <input
                        class="growth-preview-slider"
                        type="range"
                        min="0"
                        max="5"
                        step="1"
                        value="${currentGrowthPreviewStep}"
                        aria-label="成长预览"
                        oninput="setGrowthPreviewStep(this.value)"
                    >
                </div>
                <div class="foot-summary">
                    <span class="foot-badge">预览 CA <strong>${previewCa}</strong></span>
                    ${weakFootPreview ? `<span class="foot-badge">${weakFootPreview.label}逆足 <strong>+1</strong></span>` : ''}
                </div>
            </div>
        </div>
    `;
}

function setGrowthPreviewStep(step) {
    currentGrowthPreviewStep = clampGrowthPreviewStep(step);
    if (currentDetailPlayer) {
        renderPlayerDetail(currentDetailPlayer);
    }
}

function normalizeCompareSlots() {
    if (!Array.isArray(playerCompareSlots) || playerCompareSlots.length !== 2) {
        playerCompareSlots = [null, null];
    }
    playerCompareSlots = playerCompareSlots.map(slot => {
        if (!slot || !slot.player) return null;
        return {
            uid: slot.uid ?? slot.player.uid,
            player: slot.player,
            step: clampGrowthPreviewStep(slot.step),
        };
    });
    return playerCompareSlots;
}

function getCompareSlotIndex(uid) {
    normalizeCompareSlots();
    return playerCompareSlots.findIndex(slot => slot && String(slot.uid) === String(uid));
}

function syncComparedPlayerState(player) {
    const slotIndex = getCompareSlotIndex(player.uid);
    if (slotIndex === -1) return;
    playerCompareSlots[slotIndex] = {
        ...playerCompareSlots[slotIndex],
        player: {...player},
    };
    renderCompareDock();
    if (comparisonModalOpen) {
        renderComparisonWorkspace();
    }
}

function queueCurrentPlayerForCompare() {
    if (!currentDetailPlayer) return;
    queuePlayerForCompare(currentDetailPlayer);
}

function queuePlayerForCompare(player) {
    normalizeCompareSlots();
    const slotIndex = getCompareSlotIndex(player.uid);
    if (slotIndex !== -1) {
        playerCompareSlots[slotIndex] = {
            ...playerCompareSlots[slotIndex],
            player: {...player},
        };
        compareDockExpanded = true;
        renderCompareDock();
        if (currentDetailPlayer) renderGrowthPreviewToolbar(currentDetailPlayer);
        if (comparisonModalOpen) renderComparisonWorkspace();
        return;
    }

    const emptyIndex = playerCompareSlots.findIndex(slot => !slot);
    if (emptyIndex === -1) {
        compareDockExpanded = true;
        renderCompareDock();
        showModal('对比夹已满', '最多支持同时对比 2 名球员，请先从右侧对比夹移除一名后再加入。');
        return;
    }

    playerCompareSlots[emptyIndex] = {
        uid: player.uid,
        player: {...player},
        step: 0,
    };
    compareDockExpanded = true;
    renderCompareDock();
    if (currentDetailPlayer) renderGrowthPreviewToolbar(currentDetailPlayer);
}

function removePlayerFromCompare(slotIndex) {
    normalizeCompareSlots();
    if (slotIndex < 0 || slotIndex > 1) return;
    playerCompareSlots[slotIndex] = null;
    if (!playerCompareSlots.some(Boolean)) {
        compareDockExpanded = false;
    }
    renderCompareDock();
    if (currentDetailPlayer) renderGrowthPreviewToolbar(currentDetailPlayer);
    if (comparisonModalOpen) {
        if (playerCompareSlots.filter(Boolean).length < 2) {
            closeComparisonWorkspace();
        } else {
            renderComparisonWorkspace();
        }
    }
}

function clearCompareSlots() {
    playerCompareSlots = [null, null];
    compareDockExpanded = false;
    renderCompareDock();
    if (currentDetailPlayer) renderGrowthPreviewToolbar(currentDetailPlayer);
    if (comparisonModalOpen) {
        closeComparisonWorkspace();
    }
}

function toggleCompareDock() {
    compareDockExpanded = !compareDockExpanded;
    renderCompareDock();
}

function renderCompareDock() {
    const dock = document.getElementById('compareDock');
    if (!dock) return;

    normalizeCompareSlots();
    const activeTab = document.body.dataset.activeTab || document.querySelector('.tab-content.active')?.id || 'home';
    const shouldShowDock = activeTab === 'players' || activeTab === 'database';
    dock.classList.toggle('is-hidden', !shouldShowDock);
    if (!shouldShowDock) {
        dock.innerHTML = '';
        return;
    }

    const filledSlots = playerCompareSlots.filter(Boolean);
    const filledCount = filledSlots.length;
    const compareNames = filledSlots.map(slot => escapeHtml(slot.player.name));
    const detailReturnTab = activeTab === 'players' ? 'players' : 'database';

    dock.innerHTML = `
        <div class="compare-dock-shell ${compareDockExpanded ? 'is-expanded' : 'is-collapsed'} ${filledCount ? 'has-items' : 'is-empty'}">
            ${compareDockExpanded ? `
                <div class="compare-dock-card ${filledCount ? 'has-items' : 'is-empty'}">
                    <div class="compare-dock-head">
                        <div>
                            <span class="panel-kicker">Compare Folder</span>
                            <h4>对比夹</h4>
                            <div class="compare-dock-summary">${compareNames.length ? compareNames.join(' vs ') : '还没有加入对比球员'}</div>
                        </div>
                        ${filledCount ? '<button class="compare-dock-clear" type="button" onclick="clearCompareSlots()">清空</button>' : ''}
                    </div>
                    <div class="compare-slot-list">
                        ${playerCompareSlots.map((slot, index) => {
                            if (!slot) {
                                return `
                                    <div class="compare-slot is-empty">
                                        <span class="compare-slot-index">槽位 ${index + 1}</span>
                                        <p>在球员详情页点击“加入对比”</p>
                                    </div>
                                `;
                            }
                            const previewPlayer = buildPreviewPlayer(slot.player, slot.step);
                            return `
                                <div class="compare-slot is-filled is-${index === 0 ? 'blue' : 'red'}">
                                    <span class="compare-slot-index">槽位 ${index + 1}</span>
                                    <div class="compare-slot-name">${escapeHtml(slot.player.name)}</div>
                                    <div class="compare-slot-meta">${escapeHtml(slot.player.position || '-')} · CA ${escapeHtml(previewPlayer.preview_ca ?? slot.player.ca ?? '-')}</div>
                                    <div class="compare-slot-actions">
                                        <button class="compare-slot-action" type="button" onclick="showPlayerDetail(${slot.player.uid}, {returnTab: '${detailReturnTab}'})">查看球员</button>
                                        <button class="compare-slot-action is-danger" type="button" onclick="removePlayerFromCompare(${index})">移除</button>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                    <div class="compare-dock-actions">
                        <button class="btn btn-primary compare-run-button" type="button" onclick="openComparisonWorkspace()" ${filledCount < 2 ? 'disabled' : ''}>查看对比页</button>
                    </div>
                </div>
            ` : ''}
            <button
                class="compare-dock-handle ${filledCount ? 'has-items' : 'is-empty'} ${compareDockExpanded ? 'is-expanded' : ''}"
                type="button"
                onclick="toggleCompareDock()"
                aria-expanded="${compareDockExpanded}"
                aria-label="${compareDockExpanded ? '收起对比夹' : '展开对比夹'}"
            >
                <span class="compare-dock-handle-dot">${filledCount ? filledCount : '+'}</span>
                <span class="compare-dock-handle-label">${compareDockExpanded ? '收起' : '对比夹'}</span>
                <span class="compare-dock-handle-meta">${filledCount}/2</span>
            </button>
        </div>
    `;
}

function buildComparisonSlider(slotIndex, slot) {
    const labels = ['当前', '+1', '+2', '+3', '+4', '+5'];
    const accentClass = slotIndex === 0 ? 'is-blue' : 'is-red';
    return `
        <div class="comparison-slider-box ${accentClass}">
            <div class="comparison-slider-labels">
                ${labels.map((label, index) => `<span class="comparison-slider-label ${index === clampGrowthPreviewStep(slot.step) ? 'is-active' : ''}">${label}</span>`).join('')}
            </div>
            <input
                class="growth-preview-slider comparison-slider ${accentClass}"
                type="range"
                min="0"
                max="5"
                step="1"
                value="${clampGrowthPreviewStep(slot.step)}"
                aria-label="对比成长预览"
                oninput="setCompareSlotGrowthStep(${slotIndex}, this.value)"
            >
        </div>
    `;
}

function buildComparisonPlayerCard(slot, slotIndex) {
    const previewPlayer = buildPreviewPlayer(slot.player, slot.step);
    const accentClass = slotIndex === 0 ? 'is-blue' : 'is-red';
    const weakFootPreview = getWeakFootPreview(slot.player, slot.step);

    return `
        <section class="comparison-player-card ${accentClass}">
            <div class="comparison-player-head">
                <div>
                    <div class="comparison-player-name">${escapeHtml(slot.player.name)}</div>
                    <div class="comparison-player-version">UID ${escapeHtml(slot.player.uid)}</div>
                </div>
                <div class="comparison-player-tag">${escapeHtml(slot.player.position || '-')}</div>
            </div>
            <div class="comparison-player-club">${escapeHtml(slot.player.heigo_club || '-')} / ${escapeHtml(slot.player.club || '-')}</div>
            ${buildComparisonSlider(slotIndex, slot)}
            <div class="comparison-player-badges">
                <span class="foot-badge">CA <strong>${escapeHtml(previewPlayer.preview_ca ?? slot.player.ca ?? '-')}</strong></span>
                <span class="foot-badge">PA <strong>${escapeHtml(slot.player.pa ?? '-')}</strong></span>
                <span class="foot-badge">左脚 <strong>${escapeHtml(previewPlayer.left_foot ?? '-')}</strong></span>
                <span class="foot-badge">右脚 <strong>${escapeHtml(previewPlayer.right_foot ?? '-')}</strong></span>
                ${weakFootPreview ? `<span class="foot-badge">${weakFootPreview.label}逆足 <strong>+1</strong></span>` : ''}
            </div>
        </section>
    `;
}

function buildComparisonMetaCard(leftPreview, rightPreview) {
    const rows = [
        ['UID', leftPreview.uid, rightPreview.uid],
        ['国籍', leftPreview.nationality || '-', rightPreview.nationality || '-'],
        ['生日', leftPreview.birth_date || '未知', rightPreview.birth_date || '未知'],
        ['年龄', leftPreview.age ?? '-', rightPreview.age ?? '-'],
        ['位置', leftPreview.position || '-', rightPreview.position || '-'],
        ['CA / PA', `${leftPreview.preview_ca ?? leftPreview.ca ?? '-'} / ${leftPreview.pa ?? '-'}`, `${rightPreview.preview_ca ?? rightPreview.ca ?? '-'} / ${rightPreview.pa ?? '-'}`],
        ['身高', formatHeight(leftPreview.height), formatHeight(rightPreview.height)],
        ['左脚', leftPreview.left_foot ?? '-', rightPreview.left_foot ?? '-'],
        ['右脚', leftPreview.right_foot ?? '-', rightPreview.right_foot ?? '-'],
        ['HEIGO', leftPreview.heigo_club || '-', rightPreview.heigo_club || '-'],
    ];

    return `
        <section class="comparison-meta-card">
            <h4>基础信息</h4>
            <div class="comparison-meta-list">
                ${rows.map(([label, leftValue, rightValue]) => `
                    <div class="comparison-meta-row">
                        <span class="comparison-meta-value is-blue">${escapeHtml(leftValue)}</span>
                        <span class="comparison-meta-label">${escapeHtml(label)}</span>
                        <span class="comparison-meta-value is-red">${escapeHtml(rightValue)}</span>
                    </div>
                `).join('')}
            </div>
        </section>
    `;
}

function mergeCompareItems(leftItems, rightItems) {
    const registry = new Map();
    const merged = [];

    leftItems.forEach(item => {
        const entry = {key: item.key, label: item.label, left: Number(item.value) || 0, right: 0};
        registry.set(item.key, entry);
        merged.push(entry);
    });

    rightItems.forEach(item => {
        const rightValue = Number(item.value) || 0;
        if (registry.has(item.key)) {
            registry.get(item.key).right = rightValue;
            return;
        }
        const entry = {key: item.key, label: item.label, left: 0, right: rightValue};
        registry.set(item.key, entry);
        merged.push(entry);
    });

    return merged;
}

function renderComparisonMetricRow(item) {
    const leftValue = Math.max(0, Number(item.left) || 0);
    const rightValue = Math.max(0, Number(item.right) || 0);
    const delta = Math.abs(leftValue - rightValue);
    const leftLead = leftValue > rightValue;
    const rightLead = rightValue > leftValue;
    const leftWidth = leftLead ? Math.min(50, (delta / 20) * 50) : 0;
    const rightWidth = rightLead ? Math.min(50, (delta / 20) * 50) : 0;
    const leftDisplay = leftLead ? `+${delta}` : '';
    const rightDisplay = rightLead ? `+${delta}` : '';
    const rowState = delta === 0 ? 'is-even' : leftLead ? 'is-blue-win' : 'is-red-win';

    return `
        <div class="compare-row ${rowState}">
            <div class="compare-value is-blue ${leftLead ? 'is-lead' : 'is-muted'}">${leftDisplay || '&nbsp;'}</div>
            <div class="compare-track-wrap">
                <div class="compare-track-label">${escapeHtml(item.label)}</div>
                <div class="compare-track">
                    <span class="compare-track-center"></span>
                    <span class="compare-track-fill compare-track-fill-blue" style="width:${leftWidth}%;"></span>
                    <span class="compare-track-fill compare-track-fill-red" style="width:${rightWidth}%;"></span>
                </div>
            </div>
            <div class="compare-value is-red ${rightLead ? 'is-lead' : 'is-muted'}">${rightDisplay || '&nbsp;'}</div>
        </div>
    `;
}

function renderComparisonMetricPanel(title, leftItems, rightItems, options = {}) {
    const merged = mergeCompareItems(leftItems, rightItems).filter(item => options.includeLowValues || item.left > 0 || item.right > 0);
    if (!merged.length) return '';
    return `
        <section class="comparison-panel ${options.wide ? 'comparison-panel-wide' : ''}">
            <div class="comparison-panel-head">
                <h4>${escapeHtml(title)}</h4>
            </div>
            <div class="comparison-metric-list">
                ${merged.map(renderComparisonMetricRow).join('')}
            </div>
        </section>
    `;
}

function setCompareSlotGrowthStep(slotIndex, step) {
    normalizeCompareSlots();
    if (!playerCompareSlots[slotIndex]) return;
    playerCompareSlots[slotIndex].step = clampGrowthPreviewStep(step);
    renderCompareDock();
    if (comparisonModalOpen) {
        renderComparisonWorkspace();
    }
}

function openComparisonWorkspace() {
    normalizeCompareSlots();
    if (playerCompareSlots.filter(Boolean).length < 2) {
        showModal('无法开始对比', '请先在球员详情页加入两名球员，再打开对比界面。');
        return;
    }
    comparisonModalOpen = true;
    const overlay = document.getElementById('comparisonOverlay');
    overlay.classList.add('active');
    overlay.setAttribute('aria-hidden', 'false');
    renderComparisonWorkspace();
}

function closeComparisonWorkspace() {
    comparisonModalOpen = false;
    const overlay = document.getElementById('comparisonOverlay');
    overlay.classList.remove('active');
    overlay.setAttribute('aria-hidden', 'true');
}

function renderComparisonWorkspace() {
    const content = document.getElementById('comparisonContent');
    if (!content) return;

    normalizeCompareSlots();
    const leftSlot = playerCompareSlots[0];
    const rightSlot = playerCompareSlots[1];
    if (!leftSlot || !rightSlot) {
        content.innerHTML = '<div class="no-data">对比夹中需要同时存在两名球员。</div>';
        return;
    }

    const leftPreview = buildPreviewPlayer(leftSlot.player, leftSlot.step);
    const rightPreview = buildPreviewPlayer(rightSlot.player, rightSlot.step);
    const leftCollections = getPlayerFieldCollections(leftPreview);
    const rightCollections = getPlayerFieldCollections(rightPreview);
    const technicalTitle = leftCollections.isGoalkeeper || rightCollections.isGoalkeeper ? '技术 / 门将' : '技术 / 定位球';
    const positionItemsLeft = leftCollections.positions.filter(item => item.value > 1);
    const positionItemsRight = rightCollections.positions.filter(item => item.value > 1);

    content.innerHTML = `
        <div class="comparison-stage">
            <div class="comparison-hero-grid">
                ${buildComparisonPlayerCard(leftSlot, 0)}
                <div class="comparison-center-stack">
                    ${buildComparisonRadarSvg(leftPreview, rightPreview)}
                    ${buildComparisonMetaCard(leftPreview, rightPreview)}
                </div>
                ${buildComparisonPlayerCard(rightSlot, 1)}
            </div>
            <div class="comparison-grid">
                ${renderComparisonMetricPanel(technicalTitle, leftCollections.technical.concat(leftCollections.setPieces), rightCollections.technical.concat(rightCollections.setPieces))}
                ${renderComparisonMetricPanel('精神', leftCollections.mental, rightCollections.mental)}
                ${renderComparisonMetricPanel('身体', leftCollections.physical, rightCollections.physical)}
                ${renderComparisonMetricPanel('隐藏', leftCollections.hidden, rightCollections.hidden, {wide: true})}
                ${renderComparisonMetricPanel('位置熟练度', positionItemsLeft, positionItemsRight, {wide: true})}
            </div>
        </div>
    `;
}

function renderPlayerDetail(player) {
    const previewPlayer = buildPreviewPlayer(player, currentGrowthPreviewStep);
    const collections = getPlayerFieldCollections(previewPlayer);
    const radarMarkup = buildRadarSvg(buildRadarProfile(previewPlayer));
    const positionMapMarkup = buildPositionMap(player);
    const technicalMarkup = renderAttributeList(collections.technical);
    const setPieceMarkup = collections.setPieces.length ? renderAttributeList(collections.setPieces) : '';
    const infoRows = buildPlayerInfoRows(player, previewPlayer);

    const html = `
        <div class="player-detail-container">
            <div class="player-info-panel">
                <div class="player-identity-block">
                    <div class="player-identity-head">
                        <div class="player-name">${escapeHtml(player.name)}</div>
                    </div>
                    <div class="player-uid">UID: ${escapeHtml(player.uid)}</div>
                    <div id="playerReactionControls" class="player-reaction-host"></div>
                </div>
                ${infoRows.map(([label, value, isHtml]) => `
                    <div class="info-row">
                        <span class="info-label">${escapeHtml(label)}</span>
                        <span class="info-value">${isHtml ? value : escapeHtml(value)}</span>
                    </div>
                `).join('')}
                ${positionMapMarkup}
                ${player.player_habits ? `<div class="detail-note-block"><div class="detail-note-title">球员习惯</div><div class="detail-note-copy">${escapeHtml(player.player_habits)}</div></div>` : ''}
            </div>
            <div class="attributes-panel">
                <div class="attribute-group">
                    <h3>${collections.isGoalkeeper ? '门将属性' : '技术'}</h3>
                    <div class="attribute-list">${technicalMarkup}</div>
                    ${setPieceMarkup ? `<div class="attribute-subgroup"><h3>定位球</h3><div class="attribute-list">${setPieceMarkup}</div></div>` : ''}
                </div>
                <div class="attribute-group">
                    <h3>精神</h3>
                    <div class="attribute-list">${renderAttributeList(collections.mental)}</div>
                </div>
                <div class="attribute-group">
                    <h3>身体</h3>
                    <div class="attribute-list">${renderAttributeList(collections.physical)}</div>
                    ${radarMarkup}
                </div>
                <div class="attribute-group attribute-group-wide">
                    <h3>隐藏</h3>
                    <div class="attribute-list attribute-list-grid">${renderAttributeList(collections.hidden)}</div>
                </div>
            </div>
        </div>
    `;
    document.getElementById('playerDetailContent').innerHTML = html;
    renderPlayerReactionControls(player);
    startPlayerReactionCooldownTimer();
    renderGrowthPreviewToolbar(player);
    renderCompareDock();
}

function backToList() {
    clearPlayerReactionCooldownTimer();
    clearPlayerReactionBounce();
    playerReactionSubmitting = false;
    document.getElementById('dbDetailView').classList.remove('active');
    document.getElementById('dbListView').classList.add('active');
    const detailToolbar = document.getElementById('playerDetailToolbar');
    if (detailToolbar) detailToolbar.innerHTML = '';
    const returnTab = dbDetailReturnState.tab || 'database';
    if (returnTab !== 'database') {
        showTab(returnTab);
    } else {
        showTab('database');
    }
}

document.getElementById('dbPlayerSearch')?.addEventListener('keypress', event => {
    if (event.key === 'Enter') searchDatabase();
});

document.getElementById('comparisonOverlay')?.addEventListener('click', event => {
    if (event.target.id === 'comparisonOverlay') {
        closeComparisonWorkspace();
    }
});

document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && comparisonModalOpen) {
        closeComparisonWorkspace();
    }
});
