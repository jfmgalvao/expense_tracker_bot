import logging
from src.domain.entities import Expense
from src.domain.interfaces import IExpenseRepository
from src.infrastructure.database import DatabaseConnection

logger = logging.getLogger(__name__)

class PostgresExpenseRepository(IExpenseRepository):
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    def save(self, expense: Expense) -> int:
        query = """
            INSERT INTO transactions (
                amount, payment_method, description, category, reference, status, is_fixed, notes, type, family_group
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    expense.transaction_type.value,
                    expense.family_group
                ))
                expense_id = cur.fetchone()[0]
                conn.commit()
                return expense_id
        finally:
            if conn:
                conn.close()

    def get_monthly_summary(self, reference: str, family_group: str) -> dict:
        query = """
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'EXPENSE' THEN amount ELSE 0 END), 0) as total_expenses,
                COALESCE(SUM(CASE WHEN type = 'INCOME' THEN amount ELSE 0 END), 0) as total_revenues
            FROM transactions
            WHERE reference = %s AND family_group = %s
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (reference, family_group))
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
        query = """
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE reference = %s AND type = 'EXPENSE' AND family_group = %s
            GROUP BY category
            ORDER BY total DESC
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (reference, family_group))
                return {row[0]: float(row[1]) for row in cur.fetchall()}
        finally:
            if conn:
                conn.close()

    def get_expenses_by_payment_method(self, reference: str, family_group: str) -> dict:
        query = """
            SELECT payment_method, SUM(amount) as total
            FROM transactions
            WHERE reference = %s AND type = 'EXPENSE' AND family_group = %s
            GROUP BY payment_method
            ORDER BY total DESC
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (reference, family_group))
                return {row[0]: float(row[1]) for row in cur.fetchall()}
        finally:
            if conn:
                conn.close()

    def get_card_expenses_details(self, card_name: str, reference: str, family_group: str) -> list:
        query = """
            SELECT id, amount, category, description, created_at
            FROM transactions
            WHERE reference = %s AND type = 'EXPENSE' AND payment_method ILIKE %s AND family_group = %s
            ORDER BY created_at DESC
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (reference, f"%{card_name}%", family_group))
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

    def get_all_expenses_by_month(self, reference: str, family_group: str) -> list:
        query = """
            SELECT id, amount, category, description, created_at, payment_method
            FROM transactions
            WHERE reference = %s AND type = 'EXPENSE' AND family_group = %s
            ORDER BY created_at DESC
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (reference, family_group))
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
        query = """
            SELECT id, amount, category, payment_method, description, created_at
            FROM transactions
            WHERE type = 'EXPENSE' AND family_group = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (family_group, limit))
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
        query = "INSERT INTO users (telegram_id, name, family_group) VALUES (%s, %s, %s)"
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (telegram_id, name, family_group))
                conn.commit()
        finally:
            if conn:
                conn.close()
