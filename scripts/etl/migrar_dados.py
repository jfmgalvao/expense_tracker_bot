import os
import sys
import pandas as pd
import logging
from typing import List, Dict
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.config.settings import settings
from src.infrastructure.database import DatabaseConnection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ETLProcessor:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    def process_excel(self, file_path: str) -> List[Dict]:
        logger.info(f"Lendo o arquivo Excel em múltiplas páginas: {file_path}")
        
        # sheet_name=None lê TODAS as planilhas/páginas do arquivo
        all_sheets = pd.read_excel(file_path, engine='openpyxl', sheet_name=None)
        
        transactions = []
        default_date = datetime.now()

        for sheet_name, df in all_sheets.items():
            logger.info(f"Processando página: {sheet_name}")
            
            import re
            meses = {
                'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
                'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
            }
            default_reference = datetime.now().strftime("%Y-%m")
            m = re.search(r'(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*\s*(20\d{2}|\d{2})', sheet_name.lower())
            if m:
                mes = meses[m.group(1)]
                ano_str = m.group(2)
                ano = ano_str if len(ano_str) == 4 else f"20{ano_str}"
                default_reference = f"{ano}-{mes}"
                try:
                    default_date = datetime(int(ano), int(mes), 1)
                except ValueError:
                    pass

            for index, row in df.iterrows():
                if index == 0:
                    continue  # Pula os cabeçalhos internos

                # Função auxiliar para extrair status da observação
                def extrair_status(obs: str) -> str:
                    if not pd.isna(obs):
                        obs_lower = str(obs).lower()
                        if 'pago' in obs_lower:
                            return 'PAGO'
                        if 'pendente' in obs_lower:
                            return 'PENDENTE'
                    return 'PAGO' # Assumimos PAGO para histórico antigo se não especificado

                # 1. Despesas Gerais (Colunas 0 a 3)
                if pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                    try:
                        amount = float(row.iloc[1])
                        obs = row.iloc[3] if len(row) > 3 else None
                        
                        transactions.append({
                            'created_at': default_date,
                            'reference': default_reference,
                            'description': str(row.iloc[0]),
                            'amount': amount,
                            'category': 'Geral',
                            'payment_method': 'Outros',
                            'type': 'EXPENSE',
                            'status': extrair_status(obs),
                            'is_fixed': False,
                            'notes': f"Histórico. Obs: {obs}" if pd.notna(obs) else 'Importado do Excel'
                        })
                    except (ValueError, TypeError):
                        pass

                # 2. Despesas Fixas (Colunas 5 a 7)
                if len(row) > 6 and pd.notna(row.iloc[5]) and pd.notna(row.iloc[6]):
                    try:
                        amount = float(row.iloc[6])
                        obs = row.iloc[7] if len(row) > 7 else None
                        
                        transactions.append({
                            'created_at': default_date,
                            'reference': default_reference,
                            'description': str(row.iloc[5]),
                            'amount': amount,
                            'category': 'Despesa Fixa',
                            'payment_method': 'Outros',
                            'type': 'EXPENSE',
                            'status': extrair_status(obs),
                            'is_fixed': True,
                            'notes': f"Fixa. Obs: {obs}" if pd.notna(obs) else 'Importado do Excel'
                        })
                    except (ValueError, TypeError):
                        pass

                # 3. Renda (Colunas 9 a 11)
                if len(row) > 10 and pd.notna(row.iloc[9]) and pd.notna(row.iloc[10]):
                    try:
                        amount = float(row.iloc[10])
                        obs = row.iloc[11] if len(row) > 11 else None
                        
                        transactions.append({
                            'created_at': default_date,
                            'reference': default_reference,
                            'description': str(row.iloc[9]),
                            'amount': amount,
                            'category': 'Renda',
                            'payment_method': 'Conta Corrente',
                            'type': 'INCOME',
                            'status': extrair_status(obs),
                            'is_fixed': False,
                            'notes': f"Renda. Obs: {obs}" if pd.notna(obs) else 'Importado do Excel'
                        })
                    except (ValueError, TypeError):
                        pass

                # 4. Despesas de Cartões (Colunas 13 a 17)
                if len(row) > 15 and pd.notna(row.iloc[14]) and pd.notna(row.iloc[15]):
                    try:
                        amount = float(row.iloc[15])
                        
                        dt = default_date
                        if len(row) > 16 and pd.notna(row.iloc[16]):
                            if isinstance(row.iloc[16], datetime):
                                dt = row.iloc[16]

                        obs = row.iloc[17] if len(row) > 17 else None

                        transactions.append({
                            'created_at': dt,
                            'reference': dt.strftime("%Y-%m"), # Referência da data da parcela se existir
                            'description': str(row.iloc[14]),
                            'amount': amount,
                            'category': 'Cartão',
                            'payment_method': str(row.iloc[13]) if pd.notna(row.iloc[13]) else 'Cartão',
                            'type': 'EXPENSE',
                            'status': extrair_status(obs),
                            'is_fixed': False,
                            'notes': f"Cartão. Obs: {obs}" if pd.notna(obs) else 'Importado do Excel'
                        })
                    except ValueError:
                        pass

        return transactions

    def load_to_database(self, transactions: List[Dict]):
        if not transactions:
            logger.warning("Nenhuma transação válida encontrada para importar.")
            return

        logger.info(f"Iniciando inserção de {len(transactions)} transações no PostgreSQL...")
        
        query = """
            INSERT INTO transactions (
                created_at, reference, description, amount, 
                category, payment_method, type, status, is_fixed, notes
            )
            VALUES %s
        """
        
        conn = None
        try:
            conn = self.db.get_connection()
            import psycopg2.extras
            with conn.cursor() as cur:
                batch_data = [
                    (
                        t.get('created_at'),
                        t.get('reference'),
                        t.get('description'),
                        t.get('amount'),
                        t.get('category'),
                        t.get('payment_method'),
                        t.get('type'),
                        t.get('status'),
                        t.get('is_fixed'),
                        t.get('notes')
                    ) for t in transactions
                ]
                
                psycopg2.extras.execute_values(cur, query, batch_data)
                conn.commit()
                logger.info(f"✅ Carga histórica (ETL) concluída! {len(transactions)} registros salvos.")
                
        except Exception as e:
            logger.error(f"Erro ao inserir no banco durante o ETL: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()


def main():
    if not settings.database_url:
        logger.error("A variável DATABASE_URL não está configurada no .env.")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_file_path = os.path.join(script_dir, 'dados.xlsx')
    
    if not os.path.exists(excel_file_path):
        logger.error(f"Arquivo não encontrado: {excel_file_path}")
        return

    db_connection = DatabaseConnection(settings.database_url)
    etl = ETLProcessor(db_connection)
    
    try:
        transactions = etl.process_excel(excel_file_path)
        etl.load_to_database(transactions)
    except Exception as e:
        logger.error(f"Falha crítica no processo ETL: {e}")

if __name__ == '__main__':
    main()
