import os
import sys
import pandas as pd
import logging
from typing import List, Dict
from datetime import datetime
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from src.config.settings import settings
from src.infrastructure.database import DatabaseConnection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def is_valid_transaction(desc):
    desc_lower = str(desc).lower().strip()
    if not desc_lower: return False
    if desc_lower.startswith('total'): return False
    if 'saldo' in desc_lower or 'resumo' in desc_lower or 'balanço' in desc_lower: return False
    if desc_lower == 'descrição': return False
    if desc_lower == 'renda': return False
    return True

def extrair_status(obs: str) -> str:
    if not pd.isna(obs):
        obs_lower = str(obs).lower()
        if 'pago' in obs_lower: return 'PAGO'
        if 'pendente' in obs_lower: return 'PENDENTE'
    return 'PAGO'

def process_excel(file_path: str) -> List[Dict]:
    logger.info(f"Lendo Excel: {file_path}")
    all_sheets = pd.read_excel(file_path, engine='openpyxl', sheet_name=None)
    transactions = []
    
    meses = {
        'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
        'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
        'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
    }

    for sheet_name, df in all_sheets.items():
        if 'resumo' in sheet_name.lower():
            continue
            
        m = re.search(r'(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)[a-z]*\s*(20\d{2}|\d{2})', sheet_name.lower())
        if not m:
            continue
            
        mes = meses[m.group(1)]
        ano_str = m.group(2)
        ano = ano_str if len(ano_str) == 4 else f"20{ano_str}"
        default_reference = f"{ano}-{mes}"
        try:
            default_date = datetime(int(ano), int(mes), 1)
        except ValueError:
            continue

        for index, row in df.iterrows():
            if index == 0: continue

            # Bloco 1: Col 0 e 1
            if len(row) > 1 and pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                desc = row.iloc[0]
                if is_valid_transaction(desc):
                    try:
                        amt = float(row.iloc[1])
                        obs = row.iloc[3] if len(row) > 3 else None
                        transactions.append({
                            'created_at': default_date, 'reference': default_reference,
                            'description': str(desc), 'amount': amt, 'category': 'Geral/Cartão',
                            'payment_method': 'Outros', 'type': 'EXPENSE', 'status': extrair_status(obs), 'is_fixed': False
                        })
                    except (ValueError, TypeError): pass

            # Bloco 2: Col 5 e 6
            if len(row) > 6 and pd.notna(row.iloc[5]) and pd.notna(row.iloc[6]):
                desc = row.iloc[5]
                if is_valid_transaction(desc):
                    try:
                        amt = float(row.iloc[6])
                        obs = row.iloc[7] if len(row) > 7 else None
                        transactions.append({
                            'created_at': default_date, 'reference': default_reference,
                            'description': str(desc), 'amount': amt, 'category': 'Despesa Fixa',
                            'payment_method': 'Outros', 'type': 'EXPENSE', 'status': extrair_status(obs), 'is_fixed': True
                        })
                    except (ValueError, TypeError): pass

            # Bloco 3: Renda (Col 9,10 ou 10,11)
            inc_desc_idx, inc_amt_idx, inc_obs_idx = None, None, None
            if len(row) > 10 and pd.notna(row.iloc[9]) and pd.notna(row.iloc[10]):
                inc_desc_idx, inc_amt_idx, inc_obs_idx = 9, 10, 11
            elif len(row) > 11 and pd.notna(row.iloc[10]) and pd.notna(row.iloc[11]):
                inc_desc_idx, inc_amt_idx, inc_obs_idx = 10, 11, 12
                
            if inc_desc_idx is not None:
                desc = row.iloc[inc_desc_idx]
                if is_valid_transaction(desc) and isinstance(desc, str):
                    try:
                        amt = float(row.iloc[inc_amt_idx])
                        obs = row.iloc[inc_obs_idx] if len(row) > inc_obs_idx else None
                        transactions.append({
                            'created_at': default_date, 'reference': default_reference,
                            'description': str(desc), 'amount': amt, 'category': 'Renda',
                            'payment_method': 'Conta Corrente', 'type': 'INCOME', 'status': extrair_status(obs), 'is_fixed': False
                        })
                    except (ValueError, TypeError): pass

            # Bloco 4: Cartão antigo (Col 13,14 ou 14,15)
            card_desc_idx, card_amt_idx, card_obs_idx = None, None, None
            if len(row) > 15 and pd.notna(row.iloc[13]) and pd.notna(row.iloc[15]): # in Jan 2021: 13 desc, 15 amt
                card_desc_idx, card_amt_idx, card_obs_idx = 13, 15, 17
            elif len(row) > 14 and pd.notna(row.iloc[13]) and pd.notna(row.iloc[14]):
                card_desc_idx, card_amt_idx, card_obs_idx = 13, 14, 15
                
            if card_desc_idx is not None:
                desc = row.iloc[card_desc_idx]
                if is_valid_transaction(desc) and isinstance(desc, str):
                    try:
                        amt = float(row.iloc[card_amt_idx])
                        obs = row.iloc[card_obs_idx] if len(row) > card_obs_idx else None
                        transactions.append({
                            'created_at': default_date, 'reference': default_reference,
                            'description': str(desc), 'amount': amt, 'category': 'Cartão',
                            'payment_method': 'Cartão', 'type': 'EXPENSE', 'status': extrair_status(obs), 'is_fixed': False
                        })
                    except (ValueError, TypeError): pass

    return transactions

def load_to_database(db: DatabaseConnection, transactions: List[Dict]):
    logger.info(f"Inserindo {len(transactions)} transações...")
    conn = db.get_connection()
    import psycopg2.extras
    try:
        with conn.cursor() as cur:
            cur.execute('TRUNCATE TABLE transactions RESTART IDENTITY')
            query = """
                INSERT INTO transactions (created_at, reference, description, amount, category, payment_method, type, status, is_fixed)
                VALUES %s
            """
            batch = [(t['created_at'], t['reference'], t['description'], t['amount'], t['category'], t['payment_method'], t['type'], t['status'], t['is_fixed']) for t in transactions]
            psycopg2.extras.execute_values(cur, query, batch)
            conn.commit()
            logger.info("Migração perfeita concluída!")
    finally:
        conn.close()

if __name__ == '__main__':
    db = DatabaseConnection(settings.database_url)
    t = process_excel(os.path.join(os.path.dirname(__file__), 'dados.xlsx'))
    load_to_database(db, t)
