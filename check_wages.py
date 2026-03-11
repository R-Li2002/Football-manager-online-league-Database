import sqlite3
from database import SessionLocal
from models import Team, Player

db = SessionLocal()

# 检查inter球队
inter_team = db.query(Team).filter(Team.name == 'Inter').first()
if inter_team:
    print(f"Inter球队信息:")
    print(f"  级别: {inter_team.level}")
    print(f"  球员总工资: {inter_team.wage}")
    print(f"  额外工资: {inter_team.extra_wage}")
    print(f"  最终工资: {inter_team.final_wage}")
    print(f"  备注: {inter_team.notes}")
    
    # 获取Inter球员
    inter_players = db.query(Player).filter(Player.team_name == 'Inter').all()
    print(f"\nInter球员数量: {len(inter_players)}")
    total_wage = sum(p.wage for p in inter_players)
    print(f"Inter球员工资总和: {total_wage}")
    
    print("\n" + "="*50)
    
    # 检查liverpool球队
    liverpool_team = db.query(Team).filter(Team.name == 'Liverpool').first()
    if liverpool_team:
    print(f"Liverpool球队信息:")
    print(f"  级别: {liverpool_team.level}")
    print(f"  球员总工资: {liverpool_team.wage}")
    print(f"  额外工资: {liverpool_team.extra_wage}")
    print(f"  最终工资: {liverpool_team.final_wage}")
    print(f"  备注: {liverpool_team.notes}")
    
    # 获取Liverpool球员
    liverpool_players = db.query(Player).filter(Player.team_name == 'Liverpool').all()
    print(f"\nLiverpool球员数量: {len(liverpool_players)}")
    total_wage = sum(p.wage for p in liverpool_players)
    print(f"Liverpool球员工资总和: {total_wage}")

db.close()
