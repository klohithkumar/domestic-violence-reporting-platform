import sqlite3
connection=sqlite3.connect("database.db")
cursor=connection.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,fullname TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL)")
cursor.execute("CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT,fullname TEXT NOT NULL,email TEXT NOT NULL,phone TEXT NOT NULL,location TEXT NOT NULL,incident_date TEXT NOT NULL,description TEXT NOT NULL,status TEXT DEFAULT 'Pending')")
try:
    cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
except sqlite3.OperationalError:
    pass
connection.commit()
connection.close()
print("Database tables created successfully!")