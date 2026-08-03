from __future__ import annotations

import re


COMMON_CHINESE_TEAM_NAMES = {
    "AFC Ajax": "阿贾克斯",
    "AFC Bournemouth": "伯恩茅斯",
    "Arsenal": "阿森纳",
    "Bayer 04 Leverkusen": "勒沃库森",
    "Club Atlético Boca Juniors": "博卡青年",
    "Coventry City": "考文垂",
    "Crystal Palace": "水晶宫",
    "Eintracht Frankfurt": "法兰克福",
    "FC Heidenheim 1846": "海登海姆",
    "Feyenoord Rotterdam": "费耶诺德",
    "Newcastle United": "纽卡斯尔联",
    "Oriental Dragon": "东方龙",
    "RC Lens": "朗斯",
    "RC Strasbourg Alsace": "斯特拉斯堡",
    "Sheffield United": "谢菲尔德联",
    "Sportklub Sturm Graz": "格拉茨风暴",
    "Stade Rennais F.C.": "雷恩",
    "West Ham United": "西汉姆联",
    "A. Madrid": "马德里竞技",
    "AC Milan": "AC米兰",
    "Barcelona": "巴塞罗那",
    "Brighton & Hove Albion": "布莱顿",
    "Como 1907": "科莫",
    "Everton": "埃弗顿",
    "FC Bayern München": "拜仁慕尼黑",
    "FK Bodø/Glimt": "博德闪耀",
    "FK Crvena zvezda Beograd": "贝尔格莱德红星",
    "Leeds United": "利兹联",
    "Leicester City": "莱斯特城",
    "Napoli": "那不勒斯",
    "Olympique Lyonnais": "里昂",
    "Paris Saint-Germain": "巴黎圣日耳曼",
    "RB Leipzig": "RB莱比锡",
    "River Plate": "河床",
    "Sport Lisboa e Benfica": "本菲卡",
    "Sporting Clube de Portugal": "葡萄牙体育",
    "A. Bilbao": "毕尔巴鄂竞技",
    "Associazione Sportiva Roma": "罗马",
    "Aston Villa": "阿斯顿维拉",
    "Borussia Dortmund": "多特蒙德",
    "Chelsea": "切尔西",
    "FC Schalke 04": "沙尔克04",
    "FLA": "弗拉门戈",
    "Inter": "国际米兰",
    "Juventus": "尤文图斯",
    "Liverpool": "利物浦",
    "Manchester City": "曼城",
    "Manchester United": "曼联",
    "Nottingham Forest": "诺丁汉森林",
    "Olympique de Marseille": "马赛",
    "R. Madrid": "皇家马德里",
    "Southampton": "南安普顿",
    "Sunderland": "桑德兰",
    "Tottenham Hotspur": "托特纳姆热刺",
}

TEAM_NAME_ALIASES = {
    "Ajax": "AFC Ajax",
    "Bournemouth": "AFC Bournemouth",
    "Bayer 04": "Bayer 04 Leverkusen",
    "Bayern": "FC Bayern München",
    "Benfica": "Sport Lisboa e Benfica",
    "Boca": "Club Atlético Boca Juniors",
    "Brighton": "Brighton & Hove Albion",
    "Como": "Como 1907",
    "Coventry": "Coventry City",
    "Dortmund": "Borussia Dortmund",
    "Frankfurt": "Eintracht Frankfurt",
    "Heidenheim": "FC Heidenheim 1846",
    "Leicester": "Leicester City",
    "Man Utd": "Manchester United",
    "Nottm Forest": "Nottingham Forest",
    "OL": "Olympique Lyonnais",
    "OM": "Olympique de Marseille",
    "PSG": "Paris Saint-Germain",
    "R.Madrid": "R. Madrid",
    "Real Madrid": "R. Madrid",
    "RBL": "RB Leipzig",
    "Schalke": "FC Schalke 04",
    "Sheff Utd": "Sheffield United",
    "Sporting CP": "Sporting Clube de Portugal",
    "Sporing CP": "Sporting Clube de Portugal",
    "Strasbourg": "RC Strasbourg Alsace",
    "Sturm Graz": "Sportklub Sturm Graz",
    "Tottenham": "Tottenham Hotspur",
    "West Ham": "West Ham United",
    "A.Madrid": "A. Madrid",
    "At Madrid": "A. Madrid",
    "AS Roma": "Associazione Sportiva Roma",
}


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


_CHINESE_BY_NORMALIZED_NAME: dict[str, str] = {
    _normalize(name): chinese_name
    for name, chinese_name in COMMON_CHINESE_TEAM_NAMES.items()
}
for alias, canonical_name in TEAM_NAME_ALIASES.items():
    _CHINESE_BY_NORMALIZED_NAME[_normalize(alias)] = COMMON_CHINESE_TEAM_NAMES[canonical_name]

_TEXT_REPLACEMENTS = sorted(
    {
        **COMMON_CHINESE_TEAM_NAMES,
        **{alias: COMMON_CHINESE_TEAM_NAMES[canonical] for alias, canonical in TEAM_NAME_ALIASES.items()},
    }.items(),
    key=lambda item: len(item[0]),
    reverse=True,
)


def common_chinese_team_name(team_name: str | None) -> str:
    raw_name = str(team_name or "").strip()
    return _CHINESE_BY_NORMALIZED_NAME.get(_normalize(raw_name), raw_name)


def localize_team_names_in_text(value: str | None) -> str:
    text = str(value or "")
    for source_name, chinese_name in _TEXT_REPLACEMENTS:
        pattern = rf"(?<![A-Za-z0-9]){re.escape(source_name)}(?![A-Za-z0-9])"
        text = re.sub(pattern, chinese_name, text, flags=re.IGNORECASE)
    return text
