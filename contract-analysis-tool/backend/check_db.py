import sqlite3

conn = sqlite3.connect('app.db')
tables = [x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f'Tables: {tables}')
conn.close()
