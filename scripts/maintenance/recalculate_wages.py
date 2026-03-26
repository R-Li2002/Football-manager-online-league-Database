import sys
import os
sys.path.append(os.path.dirname(__file__))

from database import SessionLocal
from models import Team, Player
from main1 import recalculate_team_stats

db = SessionLocal()

print("开始重新计算所有球队的工资...")

# 获取所有球队
teams = db.query(Team).filter(Team.level != '隐藏').all()

print(f"\n找到 {len(teams)} 支球队")

for team in teams:
    # 获取该球队的所有球员
    players = db.query(Player).filter(Player.team_name == team.name).all()
    
    # 计算球员总工资
    player_total_wage = sum(p.wage for p in players)
    
    print(f"\n{team.name} ({team.level}):")
    print(f"  球员数量: {len(players)}")
    print(f"  球员总工资(计算): {player_total_wage:.2f}M")
    print(f"  数据库中的工资: {team.wage:.2f}M")
    
    if abs(team.wage - player_total_wage) > 0.01:
        print(f"  ⚠️  工资不一致！需要更新")
    else:
        print(f"  ✓ 工资一致")

# 调用重新计算函数
print("\n" + "="*50)
print("重新计算球队统计...")
recalculate_team_stats(db)

print("\n重新计算完成！")

# 再次检查几个球队
print("\n" + "="*50)
print("验证结果:")

for team in db.query(Team).filter(Team.name.in_(['Inter', 'Liverpool'])).all():
    players = db.query(Player).filter(Player.team_name == team.name).all()
    player_total_wage = sum(p.wage for p in players)
    
    print(f"\n{team.name}:")
    print(f"  球员总工资(计算): {player_total_wage:.2f}M")
    print(f"  数据库中的工资: {team.wage:.2f}M")
    print(f"  最终工资: {team.final_wage:.2f}M")

db.close()
