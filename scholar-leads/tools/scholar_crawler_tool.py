from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import asyncio
import json
import re
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from bs4 import BeautifulSoup
from models import ScholarProfile, Article, Coauthor

class ScholarProfileInput(BaseModel):
    """Input schema para a ferramenta ScholarCrawler."""
    profile_url: str = Field(..., description="Google Scholar Profile URL to be crawled") 

class ScholarCrawlerTool(BaseTool):
    name: str = "Google Scholar Crawler"
    description: str = (
        "Essa ferramenta analisa um perfil do Google Scholar e extrai informações como "
        "area principal de pesquisa, URLs de artigos relevantes, número de citações e coautores."
    )
    args_schema: Type[BaseModel] = ScholarProfileInput
    
    def _run(self, profile_url: str) -> str:
        result = asyncio.run(crawl_scholar_profile(profile_url))
        return result

async def extract_coauthor_info(crawler, coauthor_element):
    """Extrai informações detalhadas de um coautor acessando seu perfil individual."""
    # Obter o texto completo
    full_text = coauthor_element.text.strip()
    
    # Inicializar valores padrão
    name = full_text
    profile_url = None
    institution = None
    email_domain = None
    
    # Tentar extrair a URL do perfil
    # Primeiro, verificar se o próprio elemento tem um atributo href
    href = coauthor_element.get('href')
    
    # Se não tiver, procurar por um elemento <a> dentro dele
    if not href and hasattr(coauthor_element, 'find'):
        a_element = coauthor_element.find('a')
        if a_element and a_element.get('href'):
            href = a_element.get('href')
    
    if href:
        # Certifique-se de que href contém "user="
        if 'user=' in href:
            profile_url = f"https://scholar.google.com{href}"
            print(f"URL do perfil encontrada: {profile_url}")
        else:
            print(f"Link encontrado mas não é perfil de usuário: {href}")
    else:
        print(f"Nenhum link encontrado para o coautor: {name}")
    
    # Tentar separar nome, instituição e email
    if "E-mail confirmado em" in full_text or "verificado em" in full_text:
        # Padrão: Nome + Instituição + Email
        parts = re.split(r'(E-mail confirmado em|verificado em)', full_text, maxsplit=1)
        if len(parts) >= 2:
            # Primeira parte é nome + possível instituição
            name_inst = parts[0].strip()
            
            # Verificar se há informação de instituição
            if any(inst_marker in name_inst for inst_marker in ['University', 'Universidade', 'Instituto', 'UFRJ', 'UERJ', 'UFOPA']):
                # Tentar separar nome da instituição
                name_parts = re.split(r'(University|Universidade|Instituto|UFRJ|UERJ|UFOPA|Professor|Doutor)', name_inst, maxsplit=1)
                if len(name_parts) >= 2:
                    name = name_parts[0].strip()
                    institution = (name_parts[1] + (name_parts[2] if len(name_parts) > 2 else "")).strip()
            
            # Extrair domínio de email
            email_part = parts[1] + (parts[2] if len(parts) > 2 else "")
            domain_match = re.search(r'(?:confirmado|verificado) em ([\w.-]+\.\w+)', email_part)
            if domain_match:
                email_domain = domain_match.group(1)
    
    return Coauthor(
        name=name,
        profile_url=profile_url,
        institution=institution,
        email_domain=email_domain
    )

async def extract_article_abstract(crawler, article_url):
    """Extrai o resumo de um artigo acessando sua página de detalhes."""
    print(f"Extraindo resumo do artigo: {article_url}")
    
    try:
        crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        result = await crawler.arun(url=article_url, config=crawl_config, session_id="article_abstract")
        
        if result.success:
            soup = BeautifulSoup(result.html, 'html.parser')
            abstract = None
            
            # Método 1: Extrair do campo de descrição específico do Google Scholar
            # Este é o seletor mais preciso, focado na estrutura do Google Scholar
            descr_label = soup.find('div', string='Descrição') or soup.find('div', string='Description')
            if descr_label and descr_label.parent:
                # O resumo geralmente está no próximo elemento após o label
                next_sibling = descr_label.find_next_sibling('div', {'class': 'gsc_oci_value'})
                if next_sibling:
                    abstract = next_sibling.text.strip()
                    print(f"Resumo extraído do campo de descrição para: {soup.title.text if soup.title else 'Artigo'}")
                    return abstract
            
            # Método 2: Extração por ID específico
            abstract_elem = soup.find(id='gsc_oci_desc')
            if abstract_elem and abstract_elem.text.strip():
                abstract = abstract_elem.text.strip()
                print(f"Resumo extraído por ID para: {soup.title.text if soup.title else 'Artigo'}")
                return abstract
            
            # Método 3: Buscar qualquer valor em gsc_oci_value que tenha conteúdo extenso
            values = soup.select('.gsc_oci_value')
            for value in values:
                text = value.text.strip()
                # Verificar se o texto parece um resumo (pelo menos 100 caracteres)
                if len(text) > 100 and not text.count("\n") > 5:  # Evitar listas de referências
                    abstract = text
                    print(f"Resumo extraído de gsc_oci_value para: {soup.title.text if soup.title else 'Artigo'}")
                    return abstract
            
            # Método 4: Buscar em "Resumo" ou "Abstract" em qualquer parte da página
            for string in ['Resumo', 'Abstract', 'Resumé', 'Summary', 'Descrição', 'Description']:
                elem = soup.find(string=lambda text: text and string in text)
                if elem and elem.parent:
                    next_text = elem.parent.find_next('p') or elem.parent.find_next('div')
                    if next_text and len(next_text.text.strip()) > 50:
                        abstract = next_text.text.strip()
                        print(f"Resumo extraído após '{string}' para: {soup.title.text if soup.title else 'Artigo'}")
                        return abstract
            
            # Método 5: Buscar o link para o PDF ou página do artigo
            pdf_links = soup.select('a[href*=".pdf"]') or soup.select('a.gsc_oci_title_link')
            for link in pdf_links:
                href = link.get('href')
                if href and (href.endswith('.pdf') or 'doi.org' in href or any(domain in href for domain in ['ieee.org', 'springer.com', 'acm.org'])):
                    print(f"Link para artigo original encontrado: {href}")
                    try:
                        ext_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, timeout=15000)
                        ext_result = await crawler.arun(url=href, config=ext_config, session_id="original_article")
                        if ext_result.success:
                            ext_soup = BeautifulSoup(ext_result.html, 'html.parser')
                            # Procurar abstract na página original
                            for selector in ['abstract', 'paper-abstract', 'abstractSection', '#abstract', '.abstract']:
                                abstract_section = ext_soup.select_one(selector)
                                if abstract_section:
                                    abstract = abstract_section.text.strip()
                                    print(f"Resumo extraído da fonte original para: {soup.title.text if soup.title else 'Artigo'}")
                                    return abstract
                    except Exception as e:
                        print(f"Erro ao acessar artigo original: {str(e)}")
            
            print(f"Resumo não encontrado na página do artigo: {article_url}")
            return abstract
        else:
            print(f"Falha ao acessar a página do artigo")
            return None
    except Exception as e:
        print(f"Erro ao extrair resumo: {str(e)}")
        return None

async def crawl_scholar_profile(profile_url: str) -> str:
    print("\n*** Crawleando perfil do Google Scholar ***")
    
    # Configurar o crawler
    browser_config = BrowserConfig(
        headless=True,
        verbose=False,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
    )
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    crawler = AsyncWebCrawler(config=browser_config)

    await crawler.start()

    try:
        session_id = "scholar_session"
        result = await crawler.arun(url=profile_url, config=crawl_config, session_id=session_id)
        
        if result.success:
            # Usar BeautifulSoup para parsear o HTML
            soup = BeautifulSoup(result.html, 'html.parser')

            # Extrair nome do pesquisador
            name = soup.select_one('#gsc_prf_in')
            name = name.text if name else "Unknown"
            print(f"Nome do pesquisador: {name}")
            
            # Extrair área principal (primeiro interesse de pesquisa listado)
            research_interests = soup.select_one('#gsc_prf_int')
            research_area = research_interests.text.split(',')[0] if research_interests else "Not found"
            print(f"Área de pesquisa: {research_area}")
            
            # Extrair número total de citações
            total_citations = soup.select_one('#gsc_rsb_st td.gsc_rsb_std')
            total_citations = int(total_citations.text) if total_citations else 0
            print(f"Total de citações: {total_citations}")

            # Extrair artigos (limitado a 5)
            article_elements = soup.select('#gsc_a_b .gsc_a_t a')[:5]
            print(f"Encontrados {len(article_elements)} artigos")
            
            # Para cada artigo, extrair informações básicas e resumo
            articles = []
            for article in article_elements:
                title = article.text
                url = f"https://scholar.google.com{article['href']}" if article.get('href') else ""
                
                # Extrair o resumo do artigo
                abstract = None
                if url:
                    abstract = await extract_article_abstract(crawler, url)
                    if abstract:
                        print(f"Resumo extraído com sucesso para: {title}")
                    else:
                        print(f"Não foi possível extrair resumo para: {title}")
                
                # Criar objeto Article, garantindo que abstract seja None quando não encontrado
                articles.append(Article(
                    title=title, 
                    url=url, 
                    abstract=abstract
                ))
            
            # Extrair coautores 
            coauthors = []
            coauthor_elements = soup.select('.gsc_rsb_aa')
            print(f"Encontrados {len(coauthor_elements)} coautores na página principal")
            
            # Processar cada coautor
            for elem in coauthor_elements:
                coauthor = await extract_coauthor_info(crawler, elem)
                coauthors.append(coauthor)
                print(f"Coautor adicionado: {coauthor.name}")
            
            # Verificar se há um link para "ver todos os coautores"
            view_all_link = soup.select_one('a.gsc_rsb_lbl')
            if view_all_link and any(term in view_all_link.text.lower() for term in ['coauthor', 'coautor', 'co-author']):
                all_coauthors_url = f"https://scholar.google.com{view_all_link['href']}"
                print(f"Buscando página completa de coautores: {all_coauthors_url}")
                
                result_all = await crawler.arun(url=all_coauthors_url, config=crawl_config, session_id="all_coauthors")
                if result_all.success:
                    soup_all = BeautifulSoup(result_all.html, 'html.parser')
                    # Os links dos coautores estão em elementos <a> dentro de blocos específicos
                    coauthor_links = soup_all.select('a[href*="user="]')
                    
                    print(f"Encontrados {len(coauthor_links)} links de coautores na página completa")
                    
                    for link in coauthor_links:
                        # Verificar se este coautor já foi processado
                        if link.get('href') and not any(href.endswith(link['href']) for href in [c.profile_url for c in coauthors if c.profile_url]):
                            coauthor = await extract_coauthor_info(crawler, link)
                            coauthors.append(coauthor)
                            print(f"Coautor adicional: {coauthor.name}")

            # Criar o modelo estruturado
            scholar_data = ScholarProfile(
                name=name,
                profile_url=profile_url,
                research_area=research_area,
                total_citations=total_citations,
                articles=articles,
                coauthors=coauthors
            )
            
            return scholar_data.model_dump_json()
        else:
            return json.dumps({"error": "Failed to crawl the profile"})

    except Exception as e:
        print(f"Erro ao processar o perfil: {str(e)}")
        return json.dumps({"error": f"Erro ao processar o perfil: {str(e)}"})

    finally:
        await crawler.close()