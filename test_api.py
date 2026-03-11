
import requests
import json

base_url = "http://127.0.0.1:8001"

print("=== 获取所有球队 ===")
teams_res = requests.get(f"{base_url}/api/teams")
teams = teams_res.json()
print(f"共 {len(teams)} 个球队")

print("\n=== 查找包含Bodø或Glimt的球队 ===")
for t in teams:
    if "Bodø" in t["name"] or "Glimt" in t["name"]:
        print(f"  - {t['name']}")
        print(f"    人数: {t['team_size']}")
        team_name = t["name"]

print(f"\n=== 获取球队 {team_name} 的球员 ===")
players_res = requests.get(f"{base_url}/api/players/team/{requests.utils.quote(team_name)}")
players = players_res.json()
print(f"找到 {len(players)} 名球员")
for p in players:
    print(f"  - {p['name']}: {p['team_name']}")
