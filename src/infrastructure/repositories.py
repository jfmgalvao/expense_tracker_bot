import logging
from src.domain.entities import Expense
from src.domain.interfaces import IExpenseRepository
from src.infrastructure.database import DatabaseConnection

logger = logging.getLogger(__name__)

class PostgresExpenseRepository(IExpenseRepository):
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    def save(self, expense: Expense) -> int:
        table_name = f"transactions_{expense.family_group.lower()}"
        query = f"""
            INSERT INTO {table_name} (
                amount, payment_method, description, category, reference, status, is_fixed, notes, type
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (
                    expense.amount,
                    expense.payment_method,
                    expense.description,
                    expense.category,
                    expense.reference,
                    expense.status,
                    expense.is_fixed,
                    expense.notes,
                    expense.transaction_type.value
                ))
                expense_id = cur.fetchone()[0]
                conn.commit()
                return expense_id
        finally:
            if conn:
                conn.close()

    def get_monthly_summary(self, reference: str, family_group: str) -> dict:
        table_name = f"transactions_{family_group.lower()}"
        query = f"""
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'EXPENSE' THEN amount ELSE 0 END), 0) as total_expenses,
                COALESCE(SUM(CASE WHEN type = 'INCOME' THEN amount ELSE 0 END), 0) as total_revenues
            FROM {table_name}
            WHERE reference = %s
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (reference,))
                row = cur.fetchone()
                expenses = float(row[0]) if row else 0.0
                revenues = float(row[1]) if row else 0.0
                return {
                    "total_expenses": expenses,
                    "total_revenues": revenues,
                    "balance": revenues - expenses
                }
        finally:
            if conn:
                conn.close()

    def get_expenses_by_category(self, reference: str, family_group: str) -> dict:
        table_name = f"transactions_{family_group.lower()}"
        query = f"""
            SELECT category, SUM(amount) as total
            FROM {table_name}
            WHERE reference = %s AND type = 'EXPENSE'
            GROUP BY category
            ORDER BY total DESC
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (reference,))
                return {row[0]: float(row[1]) for row in cur.fetchall()}
        finally:
            if conn:
                conn.close()

    def get_expenses_by_payment_method(self, reference: str, family_group: str) -> dict:
        table_name = f"transactions_{family_group.lower()}"
        query = f"""
            SELECT payment_method, SUM(amount) as total
            FROM {table_name}
            WHERE reference = %s AND type = 'EXPENSE'
            GROUP BY payment_method
            ORDER BY total DESC
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (reference,))
                return {row[0]: float(row[1]) for row in cur.fetchall()}
        finally:
            if conn:
                conn.close()

    def get_card_expenses_details(self, card_name: str, reference: str, family_group: str) -> list:
        table_name = f"transactions_{family_group.lower()}"
        query = f"""
            SELECT id, amount, category, description, created_at
            FROM {table_name}
            WHERE reference = %s AND type = 'EXPENSE' AND payment_method ILIKE %s
            ORDER BY created_at DESC
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (reference, f"%{card_name}%"))
                rows = cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "amount": float(row[1]),
                        "category": row[2],
                        "description": row[3],
                        "date": row[4].strftime("%d/%m") if row[4] else ""
                    }
                    for row in rows
                ]
        finally:
            if conn:
                conn.close()

    def get_expenses_by_keyword(self, keyword: str, reference: str, family_group: str) -> list:
        table_name = f"transactions_{family_group.lower()}"
        query = f"""
            SELECT id, amount, category, description, created_at, payment_method
            FROM {table_name}
            WHERE reference = %s AND type = 'EXPENSE' 
              AND (description ILIKE %s OR category ILIKE %s OR payment_method ILIKE %s)
            ORDER BY created_at DESC
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                search_term = f"%{keyword}%"
                cur.execute(query, (reference, search_term, search_term, search_term))
                rows = cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "amount": float(row[1]),
                        "category": row[2],
                        "description": row[3],
                        "date": row[4].strftime("%d/%m") if row[4] else "",
                        "payment_method": row[5]
                    }
                    for row in rows
                ]
        finally:
            if conn:
                conn.close()

    def get_all_expenses_by_month(self, reference: str, family_group: str) -> list:
        table_name = f"transactions_{family_group.lower()}"
        query = f"""
            SELECT id, amount, category, description, created_at, payment_method
            FROM {table_name}
            WHERE reference = %s AND type = 'EXPENSE'
            ORDER BY created_at DESC
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (reference,))
                rows = cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "amount": float(row[1]),
                        "category": row[2],
                        "description": row[3],
                        "date": row[4].strftime("%d/%m") if row[4] else "",
                        "payment_method": row[5]
                    }
                    for row in rows
                ]
        finally:
            if conn:
                conn.close()

    def get_recent_expenses(self, family_group: str, limit: int = 10) -> list:
        table_name = f"transactions_{family_group.lower()}"
        query = f"""
            SELECT id, amount, category, payment_method, description, created_at
            FROM {table_name}
            WHERE type = 'EXPENSE'
            ORDER BY created_at DESC
            LIMIT %s
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (limit,))
                rows = cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "amount": float(row[1]),
                        "category": row[2],
                        "payment_method": row[3],
                        "description": row[4],
                        "date": row[5].strftime("%d/%m") if row[5] else ""
                    }
                    for row in rows
                ]
        finally:
            if conn:
                conn.close()

    def get_user(self, telegram_id: int) -> dict:
        query = "SELECT telegram_id, name, family_group FROM users WHERE telegram_id = %s"
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (telegram_id,))
                row = cur.fetchone()
                if row:
                    return {"telegram_id": row[0], "name": row[1], "family_group": row[2]}
                return None
        finally:
            if conn:
                conn.close()

    def create_user(self, telegram_id: int, name: str, family_group: str) -> None:
        safe_group = family_group.lower()
        query_user = "INSERT INTO users (telegram_id, name, family_group) VALUES (%s, %s, %s)"
        query_table = f"""
            CREATE TABLE IF NOT EXISTS transactions_{safe_group} (
                id SERIAL PRIMARY KEY,
                amount DECIMAL(10, 2) NOT NULL,
                payment_method VARCHAR(50) NOT NULL,
                description TEXT NOT NULL,
                category VARCHAR(50) NOT NULL,
                reference VARCHAR(10) NOT NULL,
                status VARCHAR(20) DEFAULT 'PAGO',
                is_fixed BOOLEAN DEFAULT FALSE,
                notes TEXT,
                type VARCHAR(20) DEFAULT 'EXPENSE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query_user, (telegram_id, name, safe_group))
                cur.execute(query_table)
                conn.commit()
        finally:
            if conn:
                conn.close()
