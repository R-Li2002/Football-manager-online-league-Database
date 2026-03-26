from database import SessionLocal
from models import Player, Team

db = SessionLocal()

# 妫€鏌nter鐞冮槦
inter_team = db.query(Team).filter(Team.name == "Inter").first()
if inter_team:
    print("Inter鐞冮槦淇℃伅:")
    print(f"  绾у埆: {inter_team.level}")
    print(f"  鐞冨憳鎬诲伐璧? {inter_team.wage}")
    print(f"  棰濆宸ヨ祫: {inter_team.extra_wage}")
    print(f"  鏈€缁堝伐璧? {inter_team.final_wage}")
    print(f"  澶囨敞: {inter_team.notes}")

    # 鑾峰彇Inter鐞冨憳
    inter_players = db.query(Player).filter(Player.team_name == "Inter").all()
    print(f"\nInter鐞冨憳鏁伴噺: {len(inter_players)}")
    total_wage = sum(player.wage for player in inter_players)
    print(f"Inter鐞冨憳宸ヨ祫鎬诲拰: {total_wage}")

    print("\n" + "=" * 50)

    # 妫€鏌iverpool鐞冮槦
    liverpool_team = db.query(Team).filter(Team.name == "Liverpool").first()
    if liverpool_team:
        print("Liverpool鐞冮槦淇℃伅:")
        print(f"  绾у埆: {liverpool_team.level}")
        print(f"  鐞冨憳鎬诲伐璧? {liverpool_team.wage}")
        print(f"  棰濆宸ヨ祫: {liverpool_team.extra_wage}")
        print(f"  鏈€缁堝伐璧? {liverpool_team.final_wage}")
        print(f"  澶囨敞: {liverpool_team.notes}")

        # 鑾峰彇Liverpool鐞冨憳
        liverpool_players = db.query(Player).filter(Player.team_name == "Liverpool").all()
        print(f"\nLiverpool鐞冨憳鏁伴噺: {len(liverpool_players)}")
        total_wage = sum(player.wage for player in liverpool_players)
        print(f"Liverpool鐞冨憳宸ヨ祫鎬诲拰: {total_wage}")

db.close()
