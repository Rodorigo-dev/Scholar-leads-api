from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

class Article(BaseModel):
    """Modelo para representar um artigo academico"""
    title: str = Field(..., description="article title")
    url: HttpUrl = Field(..., description="article URL")
    abstract: Optional[str] = Field(None, description="article abstract/summary extracted from the article page")
    artigo_completo: Optional[HttpUrl] = Field(None, description="URL do artigo completo encontrado pela ferramenta articles_analyzer_tool")

class Coauthor(BaseModel):
    """Modelo para representar um coautor"""
    name: str = Field(..., description="coauthor name")
    profile_url: Optional[HttpUrl] = Field(None, description="coauthor profile URL")
    institution: Optional[str] = Field(None, description="coauthor institution")
    email_domain: Optional[str] = Field(None, description="coauthor email domain")

class ScholarProfile(BaseModel):
    """Modelo para representar o perfil completo do Google Scholar"""
    name: str = Field(..., description="researcher name")
    profile_url: HttpUrl = Field(..., description="Google Scholar Profile URL")
    research_area: str = Field(..., description="researcher main research area")
    total_citations: int = Field(..., description="total number of citations")
    articles: List[Article] = Field(
        ..., 
        description="list of most relevant articles",
        max_items=5
    )
    coauthors: List[Coauthor] = Field(
        default_factory=list,
        description="list of coauthors"
    )
    veredict: Optional[str] = Field(None, description="If this researcher does qualitative research")

class CamposPesquisa(BaseModel):
    """Modelo para guiar o agente na busca de perfis de pesquisadores,
    após receber uma lista de urls de perfis de pesquisadores caso existam mais de um perfil com o mesmo nome.
    Dentre as informações opcionais temos:
    - email do pesquisador - opcional - Neste caso, sabe-se que o google scholar mostra apenas o domínio do email,
    por exemplo: "joaodasilva@ufjf.edu.br" é mostrado como "E-mail confirmado em ufjf.edu.br"
    - Instituição de ensino - opcional - Pode ser uma ou mais instituições de ensino
    - Coautor - opcional - Sabendo que o pesquisador que está sendo buscado é um coautor de um artigo,
    o agente pode usar a url do perfil do coautor para buscar o perfil do pesquisador na seção de coautores do perfil do pesquisador.
    """
    profiles: List[HttpUrl] = Field(..., description="list of researchers url profiles")  #A lista de urls estava dando problema na tool profile_filter_tool.py
    email: Optional[str] = Field(None, description="researcher email")
    institution: Optional[str] = Field(None, description="researcher institution")
    coauthor: Optional[HttpUrl] = Field(None, description="coauthor url")