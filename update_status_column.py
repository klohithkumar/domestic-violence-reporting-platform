import sqlite3
conn = sqlite3.connect("database.db")
cursor = conn.cursor()
cursor.execute("ALTER TABLE reports ADD COLUMN evidence TEXT DEFAULT ''")
conn.commit()
conn.close()
print("Evidence column added successfully!")