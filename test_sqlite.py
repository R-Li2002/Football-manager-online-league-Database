
import sqlite3

conn = sqlite3.connect('heigo.db')
cursor = conn.cursor()

print("=== 检查表名 ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for t in tables:
    print(f"  - {t[0]}")

print("\n=== 查找包含Bodø或Glimt的球队 ===")
cursor.execute("SELECT name, team_size FROM teams WHERE name LIKE ? OR name LIKE ?", ('%Bodø%', '%Glimt%'))
teams = cursor.fetchall()
for t in teams:
    print(f"  - {t[0]}: 人数 {t[1]}")
    team_name = t[0]

print(f"\n=== 获取球队 {team_name} 的球员 ===")
cursor.execute("SELECT name, team_name FROM players WHERE team_name = ?", (team_name,))
players = cursor.fetchall()
print(f"找到 {len(players)} 名球员")
for p in players:
    print(f"  - {p[0]}: {p[1]}")

print("\n=== 检查players表中所有不同的team_name值 ===")
cursor.execute("SELECT DISTINCT team_name FROM players WHERE team_name LIKE ? OR team_name LIKE ?", ('%Bodø%', '%Glimt%'))
all_team_names = cursor.fetchall()
print("找到的球队名:")
for tn in all_team_names:
    print(f"  - {tn[0]}")

conn.close()
