import sys

import requests

BASE_URL = "http://127.0.0.1:8001"


def configure_console_output() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="backslashreplace")


def main() -> int:
    configure_console_output()

    print("=== 获取所有球队 ===")
    teams_res = requests.get(f"{BASE_URL}/api/teams", timeout=10)
    teams_res.raise_for_status()
    teams = teams_res.json()
    print(f"共 {len(teams)} 个球队")

    print("\n=== 查找包含Bodø或Glimt的球队 ===")
    team_name = None
    for team in teams:
        if "Bodø" in team["name"] or "Glimt" in team["name"]:
            print(f"  - {team['name']}")
            print(f"    人数: {team['team_size']}")
            team_name = team["name"]

    if not team_name:
        print("\n[ERROR] 未找到包含 Bodø 或 Glimt 的球队")
        return 1

    print(f"\n=== 获取球队 {team_name} 的球员 ===")
    players_res = requests.get(
        f"{BASE_URL}/api/players/team/{requests.utils.quote(team_name)}",
        timeout=10,
    )
    players_res.raise_for_status()
    players = players_res.json()
    print(f"找到 {len(players)} 名球员")
    for player in players:
        print(f"  - {player['name']}: {player['team_name']}")

    print("\n=== 检查更新记录与数据纠错页面 ===")
    updates_res = requests.get(f"{BASE_URL}/updates", timeout=10)
    updates_res.raise_for_status()
    print(f"/updates -> {updates_res.status_code}")

    feedback_res = requests.get(f"{BASE_URL}/data-feedback", timeout=10)
    feedback_res.raise_for_status()
    print(f"/data-feedback -> {feedback_res.status_code}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
