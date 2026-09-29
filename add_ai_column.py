import sqlite3
conn = sqlite3.connect("database.db")
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE reports ADD COLUMN ai_analysis TEXT")
    print("AI analysis column added successfully.")
except sqlite3.OperationalError as e:
    print("Column may already exist:", e)
conn.commit()
conn.close()
print("Database update completed.")