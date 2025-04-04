from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import sys
import json
import uvicorn
from datetime import datetime

# Garantir que o diretório atual esteja no path do Python
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Importar a função executar e funções utilitárias
from crew import executar
from utils import save_result, normalize_name

# Configuração
PORT = int(os.getenv("PORT", "8000"))

# Inicialização da API FastAPI
app = FastAPI(
    title="Scholar Leads API",
    description="API para busca de pesquisadores no Google Scholar",
    version="1.0.0"
)

# Modelo de dados para os pesquisadores
class Researcher(BaseModel):
    nome: str
    instituicao: Optional[str] = None
    email: Optional[str] = None

@app.get("/")
def root():
    """Endpoint raiz da API"""
    return {"message": "Scholar Leads API está online"}

def process_crew_output(result):
    """
    Processa o resultado do CrewOutput para torná-lo JSON serializável
    """
    # Se for um objeto CrewOutput, obter o raw_output
    if hasattr(result, 'raw_output'):
        result_str = result.raw_output
    else:
        result_str = str(result)
    
    # Tentar converter para JSON
    try:
        # Tentar carregar como JSON
        parsed_result = json.loads(result_str)
        return parsed_result
    except json.JSONDecodeError:
        # Se não for JSON, retornar como string
        return {"raw_output": result_str}

@app.post("/analyze")
def analyze_researcher(researcher: Researcher):
    """
    Endpoint para analisar um pesquisador acadêmico.
    Executa a análise e salva os resultados em um arquivo.
    """
    try:
        print(f"Iniciando análise para: {researcher.nome}")
        
        # Executar a análise usando a função executar
        result = executar(
            nome_pesquisador=researcher.nome,
            email=researcher.email,
            institution=researcher.instituicao
        )
        
        # Processar o resultado do CrewOutput
        processed_result = process_crew_output(result)
        
        # Verificar se há erro
        if isinstance(processed_result, dict) and "error" in processed_result:
            return {
                "status": "error",
                "message": processed_result["error"],
                "pesquisador": researcher.model_dump()
            }
        
        # Salvar o resultado processado em um arquivo
        file_path = save_result(researcher.nome, processed_result)
        
        # Retornar os resultados
        return {
            "status": "success",
            "pesquisador": researcher.model_dump(),
            "resultado": processed_result,
            "arquivo_gerado": file_path
        }
        
    except Exception as e:
        print(f"Erro durante a análise: {e}")
        return {
            "status": "error",
            "message": str(e),
            "pesquisador": researcher.model_dump()
        }

if __name__ == "__main__":
    # Obter o caminho do diretório de dados
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    
    print(f"🚀 Iniciando Scholar Leads API na porta {PORT}")
    print(f"📁 Diretório de dados: {data_dir}")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=PORT
    )