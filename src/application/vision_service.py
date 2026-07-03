import os
import json
import re
import google.generativeai as genai
from PIL import Image

class VisionService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Use gemini-1.5-flash as it is fast, free tier friendly, and excellent for OCR/Vision
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def is_configured(self) -> bool:
        return self.model is not None

    def extract_expense_from_image(self, image_path: str, caption_hint: str = "", user_categories: list = None) -> dict:
        if not self.is_configured():
            raise ValueError("GEMINI_API_KEY não configurada no servidor.")

        prompt = f"""
        Você é um assistente financeiro especialista em ler cupons fiscais e notas.
        Analise a imagem deste recibo e extraia as seguintes informações no formato JSON estrito:
        
        {{
            "valor": 0.00, // O valor TOTAL pago na nota, como float
            "categoria": "Nome da Categoria", // Deduza a categoria mais adequada (Ex: Alimentação, Transporte, Saúde, Moradia, Lazer, Compras)
            "descricao": "Nome do Local", // O nome principal do estabelecimento ou do item
            "parcelas": 1, // Se identificar que foi parcelado (ex: 1/5, Parcelado em 5x), coloque o total de parcelas (neste caso, 5). Se for à vista ou não mencionar, coloque 1.
            "metodo_pagamento": "Cartão" // Identifique a forma de pagamento (Ex: Pix, Dinheiro, Cartão de Crédito, Cartão de Débito, Vale Refeição). Se não tiver certeza, coloque "Cartão".
        }}

        Atenção:
        - Responda APENAS com o JSON. Não adicione markdown (```json), blocos de texto ou explicações antes ou depois.
        - Se o usuário forneceu a seguinte dica na legenda: "{caption_hint}", você pode considerar para ajustar a categoria ou descrição se fizer sentido.
        - Se a dica do usuário for um nome de método de pagamento ou um banco, use-o em "metodo_pagamento".
        - Categorias já cadastradas pelo usuário: {', '.join(user_categories) if user_categories else 'Nenhuma'}. Tente usar uma destas categorias se for adequada.
        - O valor deve usar ponto para decimais.
        """

        try:
            img = Image.open(image_path)
            response = self.model.generate_content([prompt, img])
            
            # Limpeza do texto para garantir que é um JSON puro
            text = response.text.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "", 1)
            if text.startswith("```"):
                text = text.replace("```", "", 1)
            if text.endswith("```"):
                text = text[::-1].replace("```", "", 1)[::-1]
            
            text = text.strip()
            data = json.loads(text)
            
            return {
                "valor": float(data.get("valor", 0.0)),
                "categoria": str(data.get("categoria", "Outros")),
                "descricao": str(data.get("descricao", "Despesa Lida")),
                "parcelas": int(data.get("parcelas", 1)),
                "metodo_pagamento": str(data.get("metodo_pagamento", "Cartão"))
            }
        except Exception as e:
            raise Exception(f"Falha ao ler o cupom fiscal: {str(e)}")
