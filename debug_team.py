
from database import SessionLocal, engine
from models import Player, Team

db = SessionLocal()

print("=== 查找包含Bodø或Glimt的球队 ===")
teams = db.query(Team).all()
for t in teams:
    if "Bodø" in t.name or "Glimt" in t.name:
        print(f"  - {repr(t.name)}: 人数 {t.team_size}")
        team_name = t.name

print(f"\n=== 查找球员表中所有不同的team_name，包含Bodø或Glimt ===")
players = db.query(Player).all()
team_names = set()
for p in players:
    if "Bodø" in p.team_name or "Glimt" in p.team_name:
        team_names.add(p.team_name)

print(f"找到的球队名:")
for tn in team_names:
    print(f"  - {repr(tn)}")

print(f"\n=== 测试查询球队 {repr(team_name)} 的球员 ===")
players_by_team = db.query(Player).filter(Player.team_name == team_name).all()
print(f"找到 {len(players_by_team)} 名球员")
for p in players_by_team[:5]:
    print(f"  - {p.name}: {repr(p.team_name)}")

db.close()
