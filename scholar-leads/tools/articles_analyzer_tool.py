from typing import List, Dict, Any, Type
from pydantic import BaseModel, Field
import json
import asyncio
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crewai.tools import BaseTool

class ArticleAnalyzerInput(BaseModel):
    """Input schema para a ferramenta ArticleAnalyzer."""
    perfil_data: str = Field(
        ..., 
        description="JSON string contendo os dados do perfil do pesquisador, incluindo nome, área de pesquisa, artigos e coautores. Deve ser o resultado completo da task anterior sem modificações."
    )

class ArticleAnalyzer(BaseTool):
    name: str = "Article Analyzer"
    description: str = (
        "Esta ferramenta analisa os artigos de um pesquisador para determinar "
        "se sua pesquisa está relacionada ao campo da pesquisa qualitativa. "
        "Fornece uma análise detalhada explicando os indicadores encontrados, "
        "metodologias qualitativas identificadas e justificativa para a classificação. "
        "Também busca e adiciona os links para os artigos completos quando disponíveis."
    )
    args_schema: Type[BaseModel] = ArticleAnalyzerInput
    
    def _run(self, perfil_data: str) -> str:
        """Executa a análise dos artigos e retorna o resultado, preservando o JSON original."""
        try:
            # Converter string JSON para dicionário
            try:
                data = json.loads(perfil_data)
            except json.JSONDecodeError as e:
                print(f"Erro ao decodificar JSON: {str(e)}")
                return json.dumps({
                    "error": f"Dados inválidos: não foi possível converter para JSON. Erro: {str(e)}",
                    "contains_qualitative_research": False,
                    "is_qualitative_researcher": False,
                    "detailed_analysis": "Não foi possível analisar os dados devido a um erro de formato JSON."
                })
            
            # Extrair artigos e suas URLs
            articles = data.get('articles', [])
            article_urls = [article['url'] for article in articles]
            
            # Executar análise assíncrona em memória (sem depender de arquivo)
            analyzer = ArticleAnalyzerHelper()
            full_links = asyncio.run(analyzer.get_full_article_links(article_urls))
            
            # Adicionar os links completos aos artigos correspondentes
            for article, full_link in zip(articles, full_links):
                if full_link:
                    article['artigo_completo'] = full_link
            
            # Retornar o JSON original com os links adicionados aos artigos
            return json.dumps(data, ensure_ascii=False)
            
        except Exception as e:
            # Capturar qualquer erro e retornar informações úteis para diagnóstico
            error_msg = f"Erro ao processar análise: {type(e).__name__}: {str(e)}"
            print(error_msg)
            return json.dumps({
                "error": error_msg,
                "articles": []
            })

# Classe auxiliar para obter os links completos dos artigos
class ArticleAnalyzerHelper:
    async def get_full_article_links(self, urls: List[str]) -> List[str]:
        crawler = AsyncWebCrawler()
        await crawler.start()
        
        try:
            full_links = []
            
            async def process_url(url: str):
                if not url.startswith("http"):
                    url = f"https://scholar.google.com{url}"
                    
                config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
                result = await crawler.arun(url=url, config=config)
                
                if result.success:
                    soup = BeautifulSoup(result.html, 'html.parser')
                    link_elem = soup.select_one("div.gsc_oci_title_ggi a")
                    if link_elem and link_elem.get('href'):
                        return link_elem['href']
                return None
                
            tasks = [process_url(url) for url in urls]
            results = await asyncio.gather(*tasks)
            
            return [link for link in results if link]
            
        finally:
            await crawler.close()

# Método principal para teste direto
async def main(json_path: str):
    # Ler o arquivo JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extrair URLs dos artigos
    article_urls = [article['url'] for article in data.get('articles', [])]
    
    # Obter links completos
    analyzer = ArticleAnalyzerHelper()
    full_links = await analyzer.get_full_article_links(article_urls)
    
    print("\nLinks completos obtidos:")
    for link in full_links:
        print(link)
    
    return full_links

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Uso: python articles_analyzer.py caminho/para/arquivo.json")
    else:
        asyncio.run(main(sys.argv[1]))
