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
