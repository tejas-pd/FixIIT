import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.app import app


QUERY = '''
    SELECT
        c.complaint_id,
        c.description,
        u.username,
        u.email,
        m.name AS member_name,
        s.status_name
    FROM complaint c
    JOIN member m ON c.member_id = m.member_id
    JOIN users u ON m.user_id = u.id
    JOIN status s ON c.status_id = s.status_id
    ORDER BY c.created_at DESC
'''

INDEXES = [
    "DROP INDEX IF EXISTS idx_complaint_member_id;",
    "DROP INDEX IF EXISTS idx_complaint_status_id;",
    "DROP INDEX IF EXISTS idx_complaint_created_at;",
]

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_complaint_member_id ON complaint(member_id);",
    "CREATE INDEX IF NOT EXISTS idx_complaint_status_id ON complaint(status_id);",
    "CREATE INDEX IF NOT EXISTS idx_complaint_created_at ON complaint(created_at DESC);",
]


def get_connection():
    return sqlite3.connect(ROOT / 'app' / 'local_database.db')


def benchmark_sql(cursor, runs=2000):
    start = time.perf_counter()
    for _ in range(runs):
        cursor.execute(QUERY).fetchall()
    return time.perf_counter() - start


def benchmark_api(client, token, runs=200):
    headers = {'x-access-token': token}
    start = time.perf_counter()
    for _ in range(runs):
        response = client.get('/complaints', headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"Benchmark request failed: {response.status_code} {response.get_json()}")
    return time.perf_counter() - start


def get_admin_token(client):
    response = client.post('/login', json={'user': 'admin', 'password': 'admin123'})
    payload = response.get_json()
    if response.status_code != 200:
        raise RuntimeError(f"Could not authenticate benchmark user: {payload}")
    return payload['session_token']


def explain_plan(cursor):
    return cursor.execute(f"EXPLAIN QUERY PLAN {QUERY}").fetchall()


def print_plan(label, plan_rows):
    print(label)
    for step in plan_rows:
        print(f" -> {step[3]}")
    print()


def run_benchmark():
    conn = get_connection()
    cursor = conn.cursor()

    for statement in INDEXES:
        cursor.execute(statement)
    conn.commit()

    print("==================================================")
    print(" PART 1: BEFORE INDEXING")
    print("==================================================")
    print_plan("Execution Plan:", explain_plan(cursor))
    sql_before = benchmark_sql(cursor)
    print(f"SQL Execution Time (2000 runs): {sql_before:.4f} seconds\n")

    with app.test_client() as client:
        token = get_admin_token(client)
        api_before = benchmark_api(client, token)
        print(f"API Response Time (200 runs): {api_before:.4f} seconds\n")

    print("==================================================")
    print(" PART 2: APPLYING INDEXES")
    print("==================================================")
    for statement in CREATE_INDEXES:
        cursor.execute(statement)
    conn.commit()
    print("Indexes created successfully!\n")

    print("==================================================")
    print(" PART 3: AFTER INDEXING")
    print("==================================================")
    print_plan("Execution Plan:", explain_plan(cursor))
    sql_after = benchmark_sql(cursor)
    print(f"SQL Execution Time (2000 runs): {sql_after:.4f} seconds\n")

    with app.test_client() as client:
        token = get_admin_token(client)
        api_after = benchmark_api(client, token)
        print(f"API Response Time (200 runs): {api_after:.4f} seconds\n")

    print("==================================================")
    print(f"SQL Speedup: {(sql_before / sql_after):.2f}x" if sql_after else "SQL Speedup: N/A")
    print(f"API Speedup: {(api_before / api_after):.2f}x" if api_after else "API Speedup: N/A")
    print("==================================================")

    conn.close()


if __name__ == '__main__':
    run_benchmark()
