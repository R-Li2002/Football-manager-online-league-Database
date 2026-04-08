from __future__ import annotations

import re

WORKBOOK_SHEET_OVERVIEW = "信息总览"

WORKBOOK_SHEET_LEAGUE_PLAYERS = "联赛名单"

WORKBOOK_SHEET_PLAYER_TEAM_MAP = "球员对应球队"

HIDDEN_SEA_TEAM_NAME = "85大海"

HIDDEN_SEA_TEAM_LEVEL = "隐藏"

HIDDEN_SEA_TEAM_MANAGER = "系统"

ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff\xa0]")

GK_COEFFICIENT_RE = re.compile(r"GK系数为\s*([0-9.]+)")

SUPPORTED_INFO_KEY_ALIASES = {
    "8M名额": "8M名额系数",
    "7M名额": "7M名额系数",
    "可成长名额": "可成长名额系数",
    "非名PA6M": "非名PA6M系数",
    "非名身价1M": "非名身价1M系数",
    "非名其他": "非名其他系数",
}

DEFAULT_LEAGUE_INFO_VALUES = {
    "届数": 85,
    "本版首届": 84,
    "成长年龄上限": 24,
    "超级级工资帽": 9.4,
    "甲级级工资帽": 8.9,
    "乙级级工资帽": 8.6,
    "总工资": 446.71,
    "总平均工资": 8.27,
    "总身价": 4876.5,
    "总平均身价": 261.53,
    "身价极差": 30.0,
    "总平均CA": 7638.88,
    "CA极差": 31.4,
    "总平均PA": 8473.48,
    "PA极差": 11.72,
    "总平均成长": 83.17,
    "8M名额系数": 1.5,
    "7M名额系数": 1.3,
    "可成长名额系数": 1.1,
    "非名PA6M系数": 0.9,
    "非名身价1M系数": 1.0,
    "非名其他系数": 0.7,
    "GK系数": 1.0,
}

TEAM_COLUMN_ALIASES = {
    "name": ["球队名"],
    "manager": ["主教"],
    "level": ["级别"],
    "extra_wage": ["额外工资"],
    "after_tax": ["税后"],
    "notes": ["备注"],
}

PLAYER_COLUMN_ALIASES = {
    "uid": ["编号"],
    "name": ["姓名", "球员"],
    "age": ["年龄"],
    "initial_ca": ["初始CA"],
    "ca": ["当前CA"],
    "pa": ["PA"],
    "position": ["位置"],
    "nationality": ["国籍"],
    "team_name": ["联赛球队", "俱乐部", "更新俱乐部"],
}

PLAYER_TEAM_MAP_COLUMN_ALIASES = {
    "uid": ["UID"],
    "team_name": ["球队"],
    "position": ["位置"],
}

ATTRIBUTE_COLUMN_ALIASES = {
    "uid": ["UID"],
    "name": ["姓名", "球员"],
    "position": ["位置"],
    "age": ["年龄"],
    "ca": ["ca", "CA"],
    "pa": ["pa", "PA"],
    "nationality": ["国籍"],
    "club": ["俱乐部"],
    "corner": ["角球"],
    "crossing": ["传中"],
    "dribbling": ["盘带"],
    "finishing": ["射门"],
    "first_touch": ["接球"],
    "free_kick": ["任意球"],
    "heading": ["头球"],
    "long_shots": ["远射"],
    "long_throws": ["界外球"],
    "marking": ["盯人"],
    "passing": ["传球"],
    "penalty": ["罚点球"],
    "tackling": ["抢断"],
    "technique": ["技术"],
    "aggression": ["侵略性"],
    "anticipation": ["预判"],
    "bravery": ["勇敢"],
    "composure": ["镇定"],
    "concentration": ["集中"],
    "decisions": ["决断"],
    "determination": ["意志力"],
    "flair": ["想象力"],
    "leadership": ["领导力"],
    "off_the_ball": ["无球跑动"],
    "positioning": ["防守站位"],
    "teamwork": ["团队合作"],
    "vision": ["视野"],
    "work_rate": ["工作投入"],
    "acceleration": ["爆发力"],
    "agility": ["灵活"],
    "balance": ["平衡"],
    "jumping": ["弹跳"],
    "natural_fitness": ["体质"],
    "pace": ["速度"],
    "stamina": ["耐力"],
    "strength": ["强壮"],
    "consistency": ["稳定"],
    "dirtiness": ["肮脏"],
    "important_matches": ["大赛"],
    "injury_proneness": ["伤病"],
    "versatility": ["多样"],
    "adaptability": ["适应性"],
    "ambition": ["雄心"],
    "controversy": ["争论"],
    "loyalty": ["忠诚"],
    "pressure": ["抗压能力"],
    "professionalism": ["职业"],
    "sportsmanship": ["体育道德"],
    "temperament": ["情绪控制"],
    "aerial_ability": ["制空能力"],
    "command_of_area": ["拦截传中"],
    "communication": ["沟通"],
    "eccentricity": ["神经指数"],
    "handling": ["手控球"],
    "kicking": ["大脚开球"],
    "one_on_ones": ["一对一"],
    "reflexes": ["反应"],
    "rushing_out": ["出击"],
    "tendency_to_punch": ["击球倾向"],
    "throwing": ["手抛球的能力"],
    "pos_gk": ["GK"],
    "pos_dl": ["DL"],
    "pos_dc": ["DC"],
    "pos_dr": ["DR"],
    "pos_wbl": ["WBL"],
    "pos_wbr": ["WBR"],
    "pos_dm": ["DM"],
    "pos_ml": ["ML"],
    "pos_mc": ["MC"],
    "pos_mr": ["MR"],
    "pos_aml": ["AML"],
    "pos_amc": ["AMC"],
    "pos_amr": ["AMR"],
    "pos_st": ["ST"],
    "height": ["身高"],
    "weight": ["体重"],
    "left_foot": ["左脚"],
    "right_foot": ["右脚"],
    "radar_defense": ["防守"],
    "radar_physical": ["身体"],
    "radar_speed": ["速度.1", "速度"],
    "radar_creativity": ["创造"],
    "radar_attack": ["进攻"],
    "radar_technical": ["技术.1", "技术"],
    "radar_aerial": ["制空"],
    "radar_mental": ["精神"],
    "radar_gk_shot_stopping": ["拦截射门"],
    "radar_gk_physical": ["身体.1"],
    "radar_gk_speed": ["速度.2"],
    "radar_gk_mental": ["精神.1"],
    "radar_gk_command": ["指挥防守"],
    "radar_gk_eccentricity": ["意外性"],
    "radar_gk_aerial": ["制空.1"],
    "radar_gk_kicking": ["大脚"],
    "birth_date": ["出生日期", "生日"],
    "national_caps": ["国家队出场"],
    "national_goals": ["国家队进球"],
    "player_habits": ["球员习惯"],
    "player_habits_raw_code": ["球员习惯原始码"],
    "player_habits_high_bits": ["球员习惯高位码"],
}

TEAM_NAME_ALIASES = {
    "AFC Bournemouth": "Bournemouth",
    "Associazione Sportiva Roma": "As Roma",
    "Bayer 04 Leverkusen": "Bayer 04",
    "Blu-neri Milano": "Inter",
    "Brighton & Hove Albion": "Brighton",
    "Capitolini Celesti": "Lazio",
    "Casciavit Milano": "AC Milan",
    "Club Atlético Boca Juniors": "Boca",
    "Club Atlético Talleres de Córdoba": "Talleres",
    "Como 1907": "Como",
    "FC Bayern München": "FC Bayern",
    "FC Schalke 04": "Schalke 04",
    "Futebol Clube do Porto": "FC Porto",
    "Inter Miami CF": "Inter Miami",
    "Leicester City": "Leicester",
    "Manchester City": "Man City",
    "Manchester United": "Man UFC",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nottm Forest",
    "Olympique de Marseille": "OM",
    "Paris Saint-Germain": "Paris SG",
    "Parthenope": "Napoli",
    "RC Strasbourg Alsace": "Strasbourg",
    "Sheffield United": "Sheff Utd",
    "Sport Lisboa e Benfica": "Benfica",
    "Sporting Clube de Portugal": "Sporting CP",
    "Sportklub Sturm Graz": "Sturm Graz",
    "Tottenham Hotspur": "Tottenham",
    "West Ham United": "West Ham",
    "Zhejiang FC": "Zhejiang",
}

ERROR_DETAIL_SAMPLE_LIMIT = 50

ATTRIBUTE_SOURCE_PATTERNS = ["*球员属性.csv", "*球员属性.xlsx"]

ATTRIBUTE_XLSX_HEADER_SCAN_ROWS = 5

ATTRIBUTE_XLSX_SHEET_INDEX = 0

ATTRIBUTE_HEADER_CANONICAL_RENAMES = {
    "名字": "姓名",
    "在此输入名字": "姓名",
    "当前能力": "ca",
    "当前ca": "ca",
    "当前PA": "pa",
    "球队": "俱乐部",
    "停球": "接球",
    "点球": "罚点球",
    "平衡2": "平衡",
    "指挥防守": "沟通",
    "手抛球": "手抛球的能力",
    "稳定性": "稳定",
    "肮脏动作": "肮脏",
    "大赛发挥": "大赛",
    "多样性": "多样",
    "受伤倾向": "伤病",
    "野心": "雄心",
    "争论倾向": "争论",
    "职业素养": "职业",
    "体育精神": "体育道德",
    "前腰": "AMC",
    "左前腰": "AML",
    "右前腰": "AMR",
    "中后卫": "DC",
    "左后卫": "DL",
    "右后卫": "DR",
    "后腰": "DM",
    "门将": "GK",
    "中前卫": "MC",
    "左前卫": "ML",
    "右前卫": "MR",
    "前锋": "ST",
    "进攻型左边卫": "WBL",
    "进攻型右边卫": "WBR",
    "习惯": "球员习惯",
}

PLAYER_HABIT_TEXT_COLUMN = "球员习惯"

PLAYER_HABIT_RAW_CODE_COLUMN = "球员习惯原始码"

PLAYER_HABIT_HIGH_BITS_COLUMN = "球员习惯高位码"

NUMERIC_HABIT_CODE_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$")

MAX_SAFE_PLAYER_HABIT_COUNT = 9

IEEE754_SAFE_INTEGER_MAX = (1 << 53) - 1

PLAYER_HABIT_BIT_LABELS: tuple[tuple[int, str], ...] = (
    (1 << 0, "沿左路带球突进"),
    (1 << 1, "沿右路带球突进"),
    (1 << 2, "中路带球突进"),
    (1 << 3, "插入对方禁区"),
    (1 << 4, "跑肋部空间接球"),
    (1 << 5, "有机会就前插"),
    (1 << 6, "习惯简单短传配合"),
    (1 << 7, "经常尝试传身后球"),
    (1 << 8, "远射"),
    (1 << 9, "大力射门"),
    (1 << 10, "角度刁钻的射门"),
    (1 << 11, "弧线球射门"),
    (1 << 12, "喜欢盘过门将后射门"),
    (1 << 13, "乐于反越位"),
    (1 << 14, "用外脚背"),
    (1 << 15, "贴身盯防"),
    (1 << 16, "激怒对手"),
    (1 << 17, "与裁判争论"),
    (1 << 18, "背身拿球"),
    (1 << 19, "回撤拿球"),
    (1 << 20, "撞墙式配合"),
    (1 << 21, "喜欢过顶球吊射"),
    (1 << 22, "控制节奏"),
    (1 << 23, "尝试倒勾球"),
    (1 << 24, "乐意把球传给位置更好的队友而不是射门"),
    (1 << 25, "不喜欢传身后球"),
    (1 << 26, "停球观察"),
    (1 << 27, "趟球变向加速过人"),
    (1 << 28, "在盘带前先将球停至右脚"),
    (1 << 29, "在盘带前先将球停至左脚"),
    (1 << 30, "长时间控球"),
    (1 << 31, "后排插上进攻"),
    (1 << 32, "利用脚下技术将球带出危险区"),
    (1 << 33, "从不前插"),
    (1 << 34, "避免使用弱势脚"),
    (1 << 35, "尝试花式动作"),
    (1 << 36, "主罚远距离任意球"),
    (1 << 37, "倒地铲球"),
    (1 << 38, "不喜欢倒地铲球"),
    (1 << 39, "喜欢从双侧内切"),
    (1 << 40, "拉边"),
    (1 << 41, "鼓动观众情绪"),
    (1 << 42, "第一时间射门"),
    (1 << 43, "长距离传球"),
    (1 << 44, "用脚触球"),
    (1 << 45, "任意球大力攻门"),
    (1 << 46, "喜欢连续过多人"),
    (1 << 47, "喜欢将球转移到边路"),
    (1 << 48, "倾向于在职业生涯巅峰期便选择退役（隐藏习惯）"),
    (1 << 49, "倾向于尽可能长地延续自己的职业生涯（隐藏习惯）"),
    (1 << 50, "喜欢掷长距离界外球"),
    (1 << 51, "经常带球"),
    (1 << 52, "尽量不带球"),
    (1 << 53, "尝试提高弱势脚能力"),
    (1 << 54, "喜欢顶在小禁区进攻"),
    (1 << 55, "喜欢通过长距离手抛球发起防守反击"),
    (1 << 56, "不喜欢尝试远射"),
    (1 << 57, "从左路内切"),
    (1 << 58, "从右路内切"),
    (1 << 59, "尽早传中"),
    (1 << 60, "把球带出防守区域"),
    (1 << 61, "脚控球倾向"),
)

PLAYER_HABIT_KNOWN_MASK = sum(bit for bit, _ in PLAYER_HABIT_BIT_LABELS)

DERIVED_RADAR_AVERAGE_RECIPES = {
    "防守": ("盯人", "抢断", "防守站位"),
    "身体": ("灵活", "平衡", "耐力", "强壮"),
    "速度.1": ("爆发力", "速度"),
    "创造": ("传球", "想象力", "视野"),
    "进攻": ("射门", "镇定", "无球跑动"),
    "技术.1": ("盘带", "接球", "技术"),
    "制空": ("头球", "弹跳"),
    "精神": ("预判", "勇敢", "集中", "决断", "意志力", "团队合作"),
    "拦截射门": ("一对一", "反应"),
    "指挥防守": ("拦截传中", "沟通"),
    "制空.1": ("制空能力", "手控球"),
    "大脚": ("大脚开球", "手抛球的能力"),
}

DERIVED_RADAR_COPY_RECIPES = {
    "身体.1": "身体",
    "速度.2": "速度.1",
    "精神.1": "精神",
    "意外性": "神经指数",
}
