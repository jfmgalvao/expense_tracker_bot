import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
database_url = os.environ.get("DATABASE_URL")

conn = psycopg2.connect(database_url)
cur = conn.cursor()

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'transactions_%'")
tables = cur.fetchall()

for t in tables:
    table = t[0]
    print(f"Checking table: {table}")
    
    # Find duplicates
    cur.execute(f"""
        SELECT description, reference, COUNT(*), MIN(id)
        FROM {table}
        WHERE is_fixed = TRUE
        GROUP BY description, reference
        HAVING COUNT(*) > 1
    """)
    duplicates = cur.fetchall()
    
    for desc, ref, count, min_id in duplicates:
        print(f"  Found {count} entries for '{desc}' in {ref}. Keeping ID {min_id}.")
        # Delete all but the min_id
        cur.execute(f"""
            DELETE FROM {table}
            WHERE description = %s AND reference = %s AND is_fixed = TRUE AND id != %s
        """, (desc, ref, min_id))
        print(f"  Deleted duplicates for '{desc}' in {ref}")

conn.commit()
print("Duplicates removed.")
