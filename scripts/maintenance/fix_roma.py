import sys
import os
sys.path.append(os.path.dirname(__file__))

from database import SessionLocal
from models import Team, Player

db = SessionLocal()

print("检查并修复AS Roma球队名称问题...\n")

# 检查AS Roma球队
print("1. 检查Team表中的球队:")
team = db.query(Team).filter(Team.name == 'As Roma').first()
if team:
    print(f"   ✓ 找到球队: {team.name}")
    
    # 检查Player表中的AS Roma球员
    print("\n2. 检查Player表中的AS Roma球员:")
    players = db.query(Player).filter(Player.team_name == 'AS Roma').all()
    print(f"   找到 {len(players)} 名球员")
    
    if players:
        print("\n3. 修复球员球队名称...")
        for player in players:
            player.team_name = 'As Roma'
            print(f"   ✓ 更新: {player.name} (UID: {player.uid})")
        
        db.commit()
        print("\n✓ 修复完成！")
        
        # 验证修复
        print("\n4. 验证修复结果:")
        team = db.query(Team).filter(Team.name == 'As Roma').first()
        players_updated = db.query(Player).filter(Player.team_name == 'As Roma').all()
        print(f"   Team表: {team.name}")
        print(f"   Player表中该队球员数: {len(players_updated)}")
        
        # 重新计算球队统计
        from main1 import recalculate_team_stats
        print("\n5. 重新计算球队统计...")
        recalculate_team_stats(db)
        print("   ✓ 球队统计已更新")
    else:
        print("   没有找到AS Roma球员")
else:
    print("   未找到As Roma球队")

db.close()
