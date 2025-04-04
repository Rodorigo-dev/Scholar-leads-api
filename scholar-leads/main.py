#!/usr/bin/env python
import sys
import warnings
import json
import os
from datetime import datetime
from crew import executar
from rich.console import Console
from rich.panel import Panel

console = Console()

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
    import re
    normalized = re.sub(r'[^a-zA-Z0-9\s]', '', normalized)
    normalized = normalized.replace(' ', '_')
    
    return normalized

def display_results(result_json: dict):
    """Exibe os resultados formatados no terminal"""
    console.print("\n✅ [green]Análise concluída com sucesso![/green]\n")

    # Nome do pesquisador
    if "name" in result_json:
        console.print("👤 [bold]Nome do Pesquisador[/bold]")
        console.print(Panel(result_json["name"]))

    # URL do perfil
    if "profile_url" in result_json:
        console.print("\n🔗 [bold]Perfil[/bold]")
        console.print(Panel(f"Google Scholar: {result_json['profile_url']}"))

    # Área Principal
    if "research_area" in result_json:
        console.print("\n📚 [bold]Área Principal[/bold]")
        console.print(Panel(result_json["research_area"]))

    # Citações
    if "total_citations" in result_json:
        console.print("\n📊 [bold]Total de Citações[/bold]")
        console.print(Panel(str(result_json["total_citations"])))

    # Artigos
    if "articles" in result_json and result_json["articles"]:
        console.print("\n📝 [bold]Artigos Relevantes[/bold]")
        for artigo in result_json["articles"]:
            titulo = artigo["title"]
            url = artigo.get("url", "")
            abstract = artigo.get("abstract", "")
            artigo_completo = artigo.get("artigo_completo", "")
            
            article_info = f"[bold]{titulo}[/bold]"
            if url:
                article_info += f"\n🔗 URL Scholar: {url}"
            if artigo_completo:
                article_info += f"\n📄 PDF/Artigo Completo: {artigo_completo}"
            if abstract:
                article_info += f"\n\n{abstract}"
            
            console.print(Panel(article_info))
            console.print()

    # Coautores
    if "coauthors" in result_json and result_json["coauthors"]:
        console.print("\n👥 [bold]Coautores[/bold]")
        for coauthor in result_json["coauthors"]:
            name = coauthor["name"]
            profile_url = coauthor.get("profile_url", "")
            institution = coauthor.get("institution", "")
            email_domain = coauthor.get("email_domain", "")
            
            info = []
            if profile_url:
                info.append(f"🔗 {profile_url}")
            if institution:
                info.append(f"🏫 {institution}")
            if email_domain:
                info.append(f"📧 {email_domain}")
            
            panel_content = f"{name}\n" + "\n".join(info)
            console.print(Panel(panel_content, expand=False))

    # Análise Qualitativa
    if "veredict" in result_json or "qualitative_research_analysis" in result_json:
        console.print("\n🔬 [bold]Análise de Pesquisa Qualitativa[/bold]")
        
        if "veredict" in result_json and result_json["veredict"]:
            console.print(Panel(result_json["veredict"]))
        
        if "qualitative_research_analysis" in result_json:
            analysis = result_json["qualitative_research_analysis"]
            if "detailed_analysis" in analysis and analysis["detailed_analysis"]:
                console.print(Panel(analysis["detailed_analysis"]))

def save_result(researcher_name: str, data: dict):
    """Salva o resultado em um arquivo JSON"""
    # Criar diretório data se não existir
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # Criar nome do arquivo com timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{normalize_name(researcher_name)}_{timestamp}.json"
    filepath = os.path.join(data_dir, filename)
    
    # Salvar arquivo
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath

def run():
    """
    Inicia a crew para busca e análise de perfil do Google Scholar.
    """
    try:
        console.print("[bold]🔍 Google Scholar Leads Search[/bold]\n")
        
        # Solicitar nome do pesquisador via input
        researcher_name = input("Digite o nome do pesquisador: ").strip()

        if not researcher_name:
            raise ValueError("Nome do pesquisador não pode estar vazio")
        
        # Solicitar informações adicionais para a busca (opcionais)
        console.print("\n[bold]Opções avançadas para melhorar a busca:[/bold]")
        console.print("Estas informações são usadas para melhorar a precisão da busca quando existem múltiplos pesquisadores com o mesmo nome.\n")
        
        email = input("Digite o domínio de email (ex: ufrj.br, pressione Enter para pular): ").strip() or None
        institution = input("Digite a instituição (ex: UFRJ, pressione Enter para pular): ").strip() or None
        
        # Executar o fluxo do CrewAI
        console.print("\n⏳ [bold]Buscando informações no Google Scholar...[/bold]")
        result = executar(researcher_name, email, institution)

        # Converter o resultado para string se necessário
        if hasattr(result, 'raw_output'):
            result_str = result.raw_output
        else:
            result_str = str(result)
            
        try:
            # Tentar parsear como JSON
            parsed_result = json.loads(result_str)
            
            # Verificar se há erro
            if "error" in parsed_result:
                console.print(f"\n⚠️ [red]Erro:[/red] {parsed_result['error']}")
                console.print("\nTente ajustar os termos da busca ou adicionar mais informações como instituição ou email para encontrar o perfil.")
                return
            
            # Salvar resultado em arquivo
            saved_file = save_result(researcher_name, parsed_result)
            
            # Exibir resultados formatados
            display_results(parsed_result)
            
            # Exibir o JSON completo
            console.print("\n📋 [bold]JSON Completo:[/bold]")
            console.print(json.dumps(parsed_result, indent=2, ensure_ascii=False))
            
            console.print(f"\n💾 [bold]Resultado salvo em:[/bold] {saved_file}")
            
        except json.JSONDecodeError:
            # Se não for JSON, mostrar como texto
            console.print("\n🔍 [bold]Resultado da análise (não-JSON):[/bold]\n")
            console.print(result_str)

    except Exception as e:
        console.print(f"\n❌ [red]Erro:[/red] {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")
    run()