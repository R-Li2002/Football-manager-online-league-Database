import sys
import os
sys.path.append(os.path.dirname(__file__))

from database import SessionLocal
from models import Player, LeagueInfo
from wage_calculator import calculate_wage

db = SessionLocal()

print("检查UID 28122642的球员...\n")

player = db.query(Player).filter(Player.uid == 28122642).first()

if player:
    print(f"球员信息:")
    print(f"  UID: {player.uid}")
    print(f"  姓名: {player.name}")
    print(f"  年龄: {player.age}")
    print(f"  初始CA: {player.initial_ca}")
    print(f"  当前CA: {player.ca}")
    print(f"  PA: {player.pa}")
    print(f"  位置: {player.position}")
    print(f"  所属球队: {player.team_name}")
    print(f"  存储工资: {player.wage:.3f}M")
    print(f"  存储名额: {player.slot_type}")
    
    # 获取成长年龄上限
    growth_age_limit = 24
    league_info = db.query(LeagueInfo).filter(LeagueInfo.key == "成长年龄上限").first()
    if league_info:
        try:
            growth_age_limit = int(float(league_info.value))
        except:
            pass
    
    print(f"\n成长年龄上限: {growth_age_limit}")
    
    # 实时计算工资
    print("\n实时计算工资:")
    wage_result = calculate_wage(
        initial_ca=player.initial_ca,
        current_ca=player.ca,
        pa=player.pa,
        age=player.age,
        position=player.position,
        growth_age_limit=growth_age_limit
    )
    
    print(f"  初始身价: {wage_result['initial_value']}")
    print(f"  当前身价: {wage_result['current_value']}")
    print(f"  潜力身价: {wage_result['potential_value']}")
    print(f"  最终身价: {wage_result['final_value']:.3f}")
    print(f"  初始字段: {wage_result['initial_field']:.3f}")
    print(f"  系数: {wage_result['coefficient']}")
    print(f"  名额类型: {wage_result['slot_type']}")
    print(f"  计算工资: {wage_result['wage']:.3f}M")
    
    print("\n工资计算过程:")
    print(f"  {wage_result['final_value']:.3f} × {wage_result['coefficient']} = {wage_result['wage']:.3f}M")
    
    print("\n" + "="*60)
    print(f"差异:")
    print(f"  存储工资: {player.wage:.3f}M")
    print(f"  计算工资: {wage_result['wage']:.3f}M")
    diff = abs(player.wage - wage_result['wage'])
    print(f"  差值: {diff:.3f}M")
    
    if diff > 0.001:
        print("\n发现差异！正在修复...")
        player.wage = wage_result['wage']
        player.slot_type = wage_result['slot_type']
        db.commit()
        print(f"✓ 已更新为: {wage_result['wage']:.3f}M")
        
        # 重新计算球队统计
        from main1 import recalculate_team_stats
        print("\n重新计算球队统计...")
        recalculate_team_stats(db)
        print("✓ 球队统计已更新！")
    else:
        print("\n✓ 工资一致，无需修复！")
else:
    print("未找到该球员！")

db.close()
