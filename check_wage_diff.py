import sys
import os
sys.path.append(os.path.dirname(__file__))

from database import SessionLocal
from models import Team, Player, LeagueInfo
from wage_calculator import calculate_wage

db = SessionLocal()

print("检查球员详情工资计算与显示差异...\n")

# 获取成长年龄上限
growth_age_limit = 24
league_info = db.query(LeagueInfo).filter(LeagueInfo.key == "成长年龄上限").first()
if league_info:
    try:
        growth_age_limit = int(float(league_info.value))
    except:
        pass

print(f"成长年龄上限: {growth_age_limit}\n")

# 获取几个球员进行检查
players = db.query(Player).limit(10).all()
print(f"检查 {len(players)} 名球员的工资计算:\n")
print("="*80)

has_diff = False

for player in players:
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
        has_diff = True
        print(f"\n⚠️  {player.name} (UID: {player.uid})")
        print(f"   存储工资: {stored_wage:.3f}M")
        print(f"   计算工资: {calculated_wage:.3f}M")
        print(f"   差异: {abs(stored_wage - calculated_wage):.3f}M")
        print(f"   详细信息:")
        print(f"     初始CA: {player.initial_ca}, 当前CA: {player.ca}, PA: {player.pa}, 年龄: {player.age}")
        print(f"     位置: {player.position}")
        print(f"     计算详情:")
        print(f"       初始身价: {wage_result['initial_value']}")
        print(f"       当前身价: {wage_result['current_value']}")
        print(f"       潜力身价: {wage_result['potential_value']}")
        print(f"       最终身价: {wage_result['final_value']:.3f}")
        print(f"       初始字段: {wage_result['initial_field']:.3f}")
        print(f"       系数: {wage_result['coefficient']}")
        print(f"       名额: {wage_result['slot_type']}")

if not has_diff:
    print("\n✓ 所有球员的存储工资与计算工资一致！")
else:
    print("\n" + "="*80)
    print("\n发现差异，正在修复所有球员的工资...")
    
    # 重新计算并更新所有球员的工资
    all_players = db.query(Player).all()
    updated_count = 0
    
    for player in all_players:
        wage_result = calculate_wage(
            initial_ca=player.initial_ca,
            current_ca=player.ca,
            pa=player.pa,
            age=player.age,
            position=player.position,
            growth_age_limit=growth_age_limit
        )
        
        old_wage = player.wage
        player.wage = wage_result['wage']
        player.slot_type = wage_result['slot_type']
        
        if abs(old_wage - player.wage) > 0.001:
            updated_count += 1
    
    db.commit()
    print(f"\n✓ 已更新 {updated_count} 名球员的工资！")
    
    # 重新计算球队统计
    from main1 import recalculate_team_stats
    print("\n重新计算球队统计...")
    recalculate_team_stats(db)
    print("✓ 球队统计已更新！")

db.close()
