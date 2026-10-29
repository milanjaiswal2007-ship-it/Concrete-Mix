import sqlite3

conn = sqlite3.connect("data/concretemix.db")
c = conn.cursor()
c.execute("PRAGMA table_info(examples)")
cols = [r[1] for r in c.fetchall()]
print("Examples columns:", cols)
c.execute("SELECT count(1) FROM examples")
print("Total rows in examples:", c.fetchone()[0])
