import sqlite3
from pathlib import Path

base = Path('c:/Users/najma/OneDrive/Desktop/Medibot_Assignment_Resources/Medibot_Assignment_Resources')
db = base / 'mediassist_data' / 'mediassist_data' / 'db' / 'mediassist.db'
conn = sqlite3.connect(str(db))
cur = conn.cursor()
print('TABLES')
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    name = row[0]
    print('TABLE:', name)
    print('COLUMNS:', cur.execute(f'PRAGMA table_info({name})').fetchall())
    print('SAMPLE:', cur.execute(f'SELECT * FROM {name} LIMIT 5').fetchall())
    print('---')
conn.close()
