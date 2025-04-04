from crewai.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup
import urllib.parse

class ScholarSearchInput(BaseModel):
    """Input schema para a ferramenta ScholarSearch."""
    researcher_name: str = Field(..., description="Nome do pesquisador a ser buscado no Google Scholar")
    email: Optional[str] = Field(None, description="Domínio de email do pesquisador (opcional)")
    institution: Optional[str] = Field(None, description="Instituição do pesquisador (opcional)")

class ScholarSearchTool(BaseTool):
    name: str = "Google Scholar Search"
    description: str = (
        "Essa ferramenta busca um pesquisador no Google Scholar e retorna as URLs dos perfis encontrados."
    )
    args_schema: Type[BaseModel] = ScholarSearchInput
    
    def _run(self, researcher_name: str, email: Optional[str] = None, institution: Optional[str] = None) -> str:
        if not researcher_name:
            raise ValueError("Nome do pesquisador não fornecido")
        result = asyncio.run(search_scholar_profile(researcher_name, email, institution))
        return result

async def search_scholar_profile(researcher_name: str, email: Optional[str] = None, institution: Optional[str] = None):
    print(f"\n*** Buscando perfil para: {researcher_name} ***")
    if email:
        print(f"Email: {email}")
    if institution:
        print(f"Instituição: {institution}")

    # Configurar o crawler
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    # Construir a query de busca concatenando as informações disponíveis
    search_query = researcher_name
    if institution:
        search_query += f" {institution}"
    if email:
        search_query += f" {email}"
    
    # Criar URL de busca para primeira página
    encoded_query = urllib.parse.quote(search_query)
    search_url = f"https://scholar.google.com/citations?view_op=search_authors&mauthors={encoded_query}&hl=pt-BR"

    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.start()

    try:
        # Buscar na primeira página
        print(f"Buscando perfis com a query: {search_query}")
        session_id = "scholar_search"
        result = await crawler.arun(url=search_url, config=crawl_config, session_id=session_id)
        
        if result.success:
            soup = BeautifulSoup(result.html, 'html.parser')
            profile_links = soup.select('div.gsc_1usr a[href*="user="]')
            
            profiles = []
            for link in profile_links:
                if link.get('href'):
                    profile_url = "https://scholar.google.com" + link['href']
                    profiles.append(profile_url)
            
            print(f"Encontrados {len(profiles)} perfis na busca")
            
            # Verificar se encontramos algum perfil
            if profiles:
                # Retorna todos os perfis encontrados, um por linha
                return "\n".join(profiles)
            else:
                return "Nenhum perfil encontrado para o pesquisador."
        else:
            return "Falha ao realizar a busca no Google Scholar."
    
    except Exception as e:
        print(f"Erro durante a busca: {str(e)}")
        return f"Erro ao buscar perfis: {str(e)}"
    
    finally:
        await crawler.close() 