import sqlite3

conn = sqlite3.connect("database.db")

# Users table
conn.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

# Complaints table
conn.execute("""
CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT NOT NULL,
    complaint TEXT NOT NULL,
    status TEXT DEFAULT 'Pending'
)
""")

print("Database and tables created successfully")

conn.close()
