
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main1 import Base, Player, Team
import os

DATABASE_URL = "sqlite:///./heigo.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db = SessionLocal()

print("=== 检查FK Bodø/Glimt的球队信息 ===")
team = db.query(Team).filter(Team.name.like("%Bodø%")).first()
if team:
    print(f"球队名称: {team.name}")
else:
    print("未找到FK Bodø/Glimt球队")

print("\n=== 检查球员表中的球队名称 ===")
players = db.query(Player).filter(Player.team_name.like("%Bodø%")).all()
print(f"找到 {len(players)} 名球员")
for p in players[:10]:  # 只显示前10个
    print(f"  - {p.name}: {p.team_name}")

print("\n=== 检查所有球队名称 ===")
all_teams = db.query(Team).all()
print(f"共 {len(all_teams)} 个球队")
for t in all_teams:
    if "Bodø" in t.name or "Glimt" in t.name:
        print(f"  - {t.name}")

db.close()
