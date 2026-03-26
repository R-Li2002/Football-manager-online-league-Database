
import sys
import os
sys.path.append(os.path.dirname(__file__))

from main1 import app
from database import SessionLocal, engine, Base
from models import Team, Player, LeagueInfo, PlayerAttribute, AdminUser, TransferLog
from sqlalchemy.orm import Session
import io
import pandas as pd
from datetime import datetime

def test_export():
    print("测试导出功能...")
    
    db = SessionLocal()
    try:
        # 测试数据读取
        print("1. 读取球队数据...")
        level_order = {'超级': 1, '甲级': 2, '乙级': 3}
        teams = db.query(Team).filter(Team.level != '隐藏').all()
        teams_sorted = sorted(teams, key=lambda t: (level_order.get(t.level, 99), t.name))
        print(f"   找到 {len(teams_sorted)} 支球队")
        
        teams_data = []
        for team in teams_sorted:
            teams_data.append({
                '级别': team.level,
                '球队名': team.name,
                '主教': team.manager or '',
                '球队人数': team.team_size,
                '门将人数': team.gk_count,
                '额外工资': 0,
                '税后': 0,
                '最终工资': team.final_wage,
                '8M': team.count_8m,
                '7M': team.count_7m,
                '伪名': team.count_fake,
                '总身价': team.total_value,
                '平均身价': team.avg_value,
                '平均CA': team.avg_ca,
                '平均PA': team.avg_pa,
                '成长总计': team.total_growth,
                '备注': team.notes or ''
            })
        
        print("2. 创建球队DataFrame...")
        df_teams = pd.DataFrame(teams_data)
        print(f"   球队DataFrame形状: {df_teams.shape}")
        
        print("3. 读取球员数据...")
        players = db.query(Player).filter(Player.team_name != "85大海").order_by(Player.team_name, Player.name).all()
        print(f"   找到 {len(players)} 名球员")
        
        players_data = []
        for player in players:
            players_data.append({
                '编号': player.uid,
                '姓名': player.name,
                '年龄': player.age,
                '初始CA': player.initial_ca,
                '当前CA': player.ca,
                'PA': player.pa,
                '位置': player.position,
                '国籍': player.nationality,
                '俱乐部': player.team_name,
                '工资': player.wage,
                '名额': player.slot_type or ''
            })
        
        print("4. 创建球员DataFrame...")
        df_players = pd.DataFrame(players_data)
        print(f"   球员DataFrame形状: {df_players.shape}")
        
        print("5. 生成Excel文件...")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_teams.to_excel(writer, sheet_name='信息总览', index=False, startrow=1)
            df_players.to_excel(writer, sheet_name='联赛名单', index=False)
        
        output.seek(0)
        
        filename = f"test_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        print(f"6. 保存测试文件: {filename}")
        with open(filename, 'wb') as f:
            f.write(output.getvalue())
        
        print("\n[OK] 导出测试成功！")
        print(f"   测试文件已保存为: {filename}")
        
    except Exception as e:
        print(f"\n[ERROR] 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_export()
