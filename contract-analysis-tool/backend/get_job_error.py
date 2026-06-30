import sqlite3

conn = sqlite3.connect('app.db')
cursor = conn.cursor()
cursor.execute('SELECT id, status, error_message FROM jobs ORDER BY created_at DESC LIMIT 1')
row = cursor.fetchone()
if row:
    error = row[2][:300] if row[2] else "None"
    print(f'Job: {row[0]}')
    print(f'Status: {row[1]}')
    print(f'Error: {error}')
conn.close()
