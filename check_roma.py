import sys
import os
sys.path.append(os.path.dirname(__file__))

from database import SessionLocal
from models import Team, Player

db = SessionLocal()

print("检查AS Roma相关问题...\n")

# 检查所有球队
teams = db.query(Team).all()
print(f"找到 {len(teams)} 支球队:")
for team in teams:
    if 'Roma' in team.name:
        print(f"\n⚠️  找到可能的Roma球队: {team.name}")
        
        # 查找该球队的球员
        players = db.query(Player).filter(Player.team_name == team.name).all()
        print(f"  该球队在数据库中有 {len(players)} 名球员")
        
        if players:
            print("  球员名单:")
            for p in players[:5]:
                print(f"    - {p.name} (UID: {p.uid})")

# 检查Player表中的所有球队名
print("\n" + "="*50)
print("检查Player表中所有球队名...")
player_team_names = set()
players = db.query(Player).all()
for p in players:
    if p.team_name:
        player_team_names.add(p.team_name)

print(f"\nPlayer表中有 {len(player_team_names)} 个不同的球队名:")
for team_name in sorted(player_team_names):
    if 'Roma' in team_name:
        print(f"  ⚠️  {team_name}")
    else:
        print(f"  {team_name}")

db.close()
