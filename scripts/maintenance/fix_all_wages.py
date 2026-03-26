import sys
import os
sys.path.append(os.path.dirname(__file__))

from database import SessionLocal
from models import Player, LeagueInfo
from wage_calculator import calculate_wage

db = SessionLocal()

print("检查并修复所有球员的工资不一致问题...\n")

# 获取成长年龄上限
growth_age_limit = 24
league_info = db.query(LeagueInfo).filter(LeagueInfo.key == "成长年龄上限").first()
if league_info:
    try:
        growth_age_limit = int(float(league_info.value))
    except:
        pass

print(f"成长年龄上限: {growth_age_limit}\n")

# 获取所有球员
all_players = db.query(Player).all()
print(f"找到 {len(all_players)} 名球员\n")

updated_count = 0
first_diff = True

for player in all_players:
    # 计算实时工资
    wage_result = calculate_wage(
        initial_ca=player.initial_ca,
        current_ca=player.ca,
        pa=player.pa,
        age=player.age,
        position=player.position,
        growth_age_limit=growth_age_limit
    )
    
    stored_wage = player.wage
    calculated_wage = wage_result['wage']
    
    if abs(stored_wage - calculated_wage) > 0.001:
        if first_diff:
            print("发现工资不一致的球员:\n")
            first_diff = False
        
        print(f"{player.name} (UID: {player.uid}):")
        print(f"  存储: {stored_wage:.3f}M → 计算: {calculated_wage:.3f}M")
        
        # 更新
        player.wage = calculated_wage
        player.slot_type = wage_result['slot_type']
        updated_count += 1

db.commit()

if updated_count > 0:
    print(f"\n✓ 已更新 {updated_count} 名球员的工资！")
    
    # 重新计算球队统计
    from main1 import recalculate_team_stats
    print("\n重新计算球队统计...")
    recalculate_team_stats(db)
    print("✓ 球队统计已更新！")
else:
    print("✓ 所有球员的工资一致，无需更新！")

db.close()
