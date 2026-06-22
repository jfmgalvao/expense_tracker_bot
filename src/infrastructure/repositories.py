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
                created_at, reference, description, amount, 
                category, payment_method, type, status, is_fixed, notes
            )
            VALUES (CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    query, 
                    (
                        expense.reference,
                        expense.description, 
                        expense.amount, 
                        expense.category,
                        expense.payment_method, 
                        expense.transaction_type.value, 
                        expense.status,
                        expense.is_fixed,
                        expense.notes
                    )
                )
                transaction_id = cur.fetchone()[0]
                conn.commit()
                return transaction_id
        except Exception as e:
            logger.error(f"Error saving expense to database: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def get_monthly_summary(self, reference: str) -> dict:
        query = """
            SELECT 
                COALESCE(SUM(CASE WHEN type = 'Despesa' THEN amount ELSE 0 END), 0) as total_expenses,
                COALESCE(SUM(CASE WHEN type = 'Renda' THEN amount ELSE 0 END), 0) as total_revenues
            FROM transactions
            WHERE reference = %s
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (reference,))
                row = cur.fetchone()
                return {
                    "total_expenses": float(row[0]),
                    "total_revenues": float(row[1]),
                    "balance": float(row[1] - row[0])
                }
        finally:
            if conn:
                conn.close()

    def get_expenses_by_category(self, reference: str) -> dict:
        query = """
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE reference = %s AND type = 'Despesa'
            GROUP BY category
            ORDER BY total DESC
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (reference,))
                rows = cur.fetchall()
                return {row[0]: float(row[1]) for row in rows}
        finally:
            if conn:
                conn.close()

    def get_expenses_by_payment_method(self, reference: str) -> dict:
        query = """
            SELECT payment_method, SUM(amount) as total
            FROM transactions
            WHERE reference = %s AND type = 'Despesa'
            GROUP BY payment_method
            ORDER BY total DESC
        """
        conn = None
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cur:
                cur.execute(query, (reference,))
                rows = cur.fetchall()
                return {row[0]: float(row[1]) for row in rows}
        finally:
            if conn:
                conn.close()

    def get_card_expenses_details(self, card_name: str, reference: str) -> list:
        query = """
            SELECT id, amount, category, description, created_at
            FROM transactions
            WHERE reference = %s AND type = 'Despesa' AND payment_method ILIKE %s
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

    def get_recent_expenses(self, limit: int = 10) -> list:
        query = """
            SELECT id, amount, category, payment_method, description, created_at
            FROM transactions
            WHERE type = 'Despesa'
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
