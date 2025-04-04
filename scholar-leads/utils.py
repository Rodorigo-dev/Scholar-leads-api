import os
import re
import json
from datetime import datetime

def normalize_name(name: str) -> str:
    """
    Normaliza o nome do pesquisador para criar um caminho seguro para arquivo.
    
    Args:
        name: Nome do pesquisador
        
    Returns:
        str: Nome normalizado e seguro para uso em caminhos de arquivo
    """
    # Remove espaços extras e converte para minúsculas
    normalized = name.strip()
    
    # Substitui caracteres especiais e espaços por underscore
    normalized = re.sub(r'[^a-zA-Z0-9\s]', '', normalized)
    normalized = normalized.replace(' ', '_')
    
    return normalized

def save_result(researcher_name: str, data: dict):
    """
    Salva o resultado em um arquivo JSON
    
    Args:
        researcher_name: Nome do pesquisador
        data: Dados a serem salvos em formato JSON
        
    Returns:
        str: Caminho do arquivo salvo
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{normalize_name(researcher_name)}_{timestamp}.json"
    filepath = os.path.join(data_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath

# verificar output e campos do json
