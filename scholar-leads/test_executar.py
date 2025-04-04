#!/usr/bin/env python3
"""
Script para testar a função executar do módulo crew diretamente,
sem envolver o FastAPI.
"""

import os
import sys
import json
from datetime import datetime

# Adicionar o diretório atual ao path do Python
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

def main():
    """Função principal para testar a execução"""
    print("Iniciando teste da função executar...")
    print(f"Diretório atual: {current_dir}")
    print(f"Python path: {sys.path}")
    
    try:
        # Importar a função executar
        from crew import executar
        print("✓ Função executar importada com sucesso")
        
        # Solicitar dados do pesquisador
        nome = input("Digite o nome do pesquisador: ")
        instituicao = input("Digite a instituição (opcional, pressione Enter para pular): ") or None
        email = input("Digite o domínio de email (opcional, pressione Enter para pular): ") or None
        
        # Registrar início da execução
        start_time = datetime.now()
        print(f"Iniciando análise para {nome} às {start_time.strftime('%H:%M:%S')}")
        
        # Executar a função
        result = executar(
            nome_pesquisador=nome, 
            email=email, 
            institution=instituicao
        )
        
        # Registrar fim da execução
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"Análise concluída em {duration:.2f} segundos")
        
        # Processar e exibir o resultado
        if isinstance(result, str):
            try:
                # Tentar processar como JSON
                json_result = json.loads(result)
                print("\n📊 Resultado da análise (JSON):")
                print(json.dumps(json_result, indent=2, ensure_ascii=False))
            except json.JSONDecodeError:
                print("\n📄 Resultado da análise (texto):")
                print(result)
        else:
            print("\n📊 Resultado da análise (objeto):")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
    except ImportError as e:
        print(f"❌ Erro ao importar função executar: {e}")
        print("Verifique se o arquivo crew.py está no diretório correto e contém a função executar.")
    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()