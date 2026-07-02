import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
database_url = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(database_url)
cur = conn.cursor()

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'transactions_%'")
tables = cur.fetchall()
print("Tables:", tables)

for t in tables:
    table = t[0]
    cur.execute(f"SELECT reference, count(*) FROM {table} WHERE is_fixed = TRUE GROUP BY reference ORDER BY reference")
    print(f"Table {table} references with fixed=True:", cur.fetchall())
    
    cur.execute(f"SELECT id, amount, description, category, reference, created_at FROM {table} WHERE is_fixed = TRUE ORDER BY reference, description")
    all_fixed = cur.fetchall()
    print(f"Details for {table}:")
    for r in all_fixed:
        print(f"  ID: {r[0]}, Amount: {r[1]}, Desc: {r[2]}, Cat: {r[3]}, Ref: {r[4]}, Date: {r[5]}")
