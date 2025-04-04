import os
import json
import yaml
import sys
from crewai import Agent, Task, Crew, Process
from tools.scholar_search_tool import ScholarSearchTool
from tools.scholar_crawler_tool import ScholarCrawlerTool
from tools.articles_analyzer_tool import ArticleAnalyzer
import asyncio

# Garantir que o diretório atual esteja no path do Python
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from llm_config import llm
from langchain_openai import ChatOpenAI

# Obter o diretório base do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')

def load_yaml(file_path):
    """Carrega arquivo YAML usando caminho absoluto"""
    absolute_path = os.path.join(CONFIG_DIR, os.path.basename(file_path))
    with open(absolute_path, 'r') as file:
        return yaml.safe_load(file)

def create_agents():
    """Criar os agentes da crew"""
    agents_config = load_yaml('agents.yaml')
    
    # Agente buscador
    buscador = Agent(
        role=agents_config['buscador_scholar']['role'],
        goal=agents_config['buscador_scholar']['goal'],
        backstory=agents_config['buscador_scholar']['backstory'],
        verbose=True,
        allow_delegation=False,
        tools=[ScholarSearchTool()]
    )
    
    # Agente analista
    analista = Agent(
        role=agents_config['analista_scholar']['role'],
        goal=agents_config['analista_scholar']['goal'],
        backstory=agents_config['analista_scholar']['backstory'],
        verbose=True,
        allow_delegation=False,
        tools=[ScholarCrawlerTool()]
    )
    
    # Agente de análise de artigos (corrigido nome)
    analista_artigos = Agent(
        role=agents_config['analista_artigos']['role'],
        goal=agents_config['analista_artigos']['goal'],
        backstory=agents_config['analista_artigos']['backstory'],
        verbose=True,
        allow_delegation=False,
        tools=[ArticleAnalyzer()]
    )

    return [buscador, analista, analista_artigos]

def create_tasks(agents, researcher_name, email=None, institution=None):
    """Criar as tasks da crew"""
    tasks_config = load_yaml('tasks.yaml')
    
    # Task de busca
    task_busca = Task(
        description=tasks_config['task_busca_perfil']['description'].format(
            researcher_name=researcher_name,
            email=email or "Não fornecido",
            institution=institution or "Não fornecido"
        ),
        agent=agents[0],  # buscador
        expected_output=tasks_config['task_busca_perfil']['expected_output'],
        output_key="perfil_url"  # Captura a saída como variável para a próxima task
    )
    
    # Task de análise de perfil
    task_analise = Task(
        description=tasks_config['task_analise_scholar']['description'],
        agent=agents[1],  # analista
        expected_output=tasks_config['task_analise_scholar']['expected_output'],
        inputs={"perfil_url": "{{ perfil_url }}"},  # Usa a saída da task anterior
        output_key="perfil_data"  # Captura a saída para a próxima task
    )
    
    # Task de análise de artigos
    task_analisa_artigos = Task(
        description=tasks_config['task_analisa_artigos']['description'],
        agent=agents[2],  # analista_artigos
        expected_output=tasks_config['task_analisa_artigos']['expected_output'],
        inputs={"perfil_data": "{{ perfil_data }}"}  # Usa a saída da task anterior
    )
    
    return [task_busca, task_analise, task_analisa_artigos]

def executar(nome_pesquisador, email=None, institution=None):
    """Executar o fluxo do CrewAI"""
    print(f"\n🔍 Iniciando busca para: {nome_pesquisador}")
    
    # Exibir informações adicionais usadas na busca
    if email or institution:
        print("\n📋 Informações adicionais:")
        if email:
            print(f"  - Email: {email}")
        if institution:
            print(f"  - Instituição: {institution}")
    
    # Criar agentes
    agents = create_agents()
    
    # Criar tasks
    tasks = create_tasks(agents, nome_pesquisador, email, institution)
    
    # Configurar LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        verbose=True
    )
    
    # Criar e executar crew
    crew = Crew(
        agents=agents,
        tasks=tasks,
        manager_llm=llm,
        process=Process.sequential,
        verbose=True
    )

    resultado = crew.kickoff()                                                                                                                                                                                                                                                                            
    print("\n✅ Análise concluída com sucesso!")
    
    return resultado

if __name__ == "__main__":
    nome_pesquisador = input("Digite o nome do pesquisador: ")
    
    # Opcionalmente solicitar informações adicionais
    print("\nInformações adicionais para melhorar a busca (opcionais):")
    email = input("Digite o domínio de email (ex: ufjf.br, pressione Enter para pular): ") or None
    institution = input("Digite a instituição (ex: UFJF, pressione Enter para pular): ") or None
    
    result = executar(nome_pesquisador, email, institution)

    try:
        # Se for JSON, formatar bonitinho
        parsed_result = json.loads(result)
        print("\n📊 Resultado formatado:")
        print(json.dumps(parsed_result, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(result)  # Caso tenha erro, exibir normalmente
