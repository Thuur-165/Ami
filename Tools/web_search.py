"""
Ferramenta padrão de exemplo para pesquisas na Internet

Escrita originalmente por Arthur (Desenvolvedor original)
"""

from .tool_registry import tool
from ddgs import DDGS, exceptions
from pathlib import Path
from config import config
from typing import Literal, Optional, cast, Any
from json import dump, dumps
import lmstudio as lms
import numpy as np
import requests
import re
import json


COUNTRY = config.get('location')
CACHE_PAGES_PATH = Path(__file__).parent.parent / 'cache' / '_results.json'

class WebSearchEngine:
   
   def __init__(self, embedding_model: str = config.get('models.embedding')):
      self.model = embedding_model
      CACHE_PAGES_PATH.parent.mkdir(parents=True, exist_ok=True)


   def _save_results(self, results):
      with open(CACHE_PAGES_PATH, 'w', encoding='utf-8') as res:
         dump(results, res, indent=4, ensure_ascii=False)
   
   def _text_search(self, query: str, date: Optional[str], engine: Literal['google', 'wikipedia']):
      try:
         with DDGS() as ddgs:
            results: list[dict[str, str]] = ddgs.text(
               query=query,
               region=COUNTRY,
               max_results=5,
               timelimit=date,
               safesearch='moderate',
               backend=engine
            )

         for item in results:
            item['link'] = item.pop('href')
            item['snippet'] = item.pop('body')
            if len(item['snippet']) > 700:
               item['snippet'] = item['snippet'][:700] + "[...]"

         for i in range(len(results)):
            results[i]['id'] = str(i)

         self._save_results(results)

         for item in results:
            if len(item['link']) > 120:
               item['link'] = item['link'][:120] + "[...]"

         return dumps(results, indent=2, ensure_ascii=False)
      except exceptions.DDGSException:
         return "Nenhum resultado encontrado, tente outra pesquisa!"

   def _news_search(self, query: str, date: Optional[str]):
      try:
         with DDGS() as ddgs:
            results: list[dict[str, str]] = ddgs.news(
               query=query,
               region=COUNTRY,
               safesearch="moderate",
               timelimit=date,
               max_results=4
            )

         for item in results:
            item['snippet'] = item.pop('body')
            item['link'] = item.pop('url')

         for i in range(len(results)):
            results[i]['id'] = str(i)

         self._save_results(results)

         for item in results:
            if len(item['link']) > 120:
               item['link'] = item['link'][:120] + "[...]"

         return dumps(results, indent=2, ensure_ascii=False)

      except exceptions.DDGSException:
         return "Nenhum resultado encontrado, tente outra pesquisa!"

   def _image_search(self, query: str, date: Optional[str]):
      try:
         with DDGS() as ddgs:
            results: list[dict[str, str]] = ddgs.images(
               query=query,
               region=COUNTRY,
               safesearch="moderate",
               color="color",
               max_results=5,
               timelimit=date,
            )

         for item in results:
            item.pop('source', None)
            item.pop('thumbnail', None)
            item.pop('url', None)
            item['link'] = item.pop('image')

         self._save_results(results)

         for item in results:
            if len(item['link']) > 120:
               item['link'] = item['link'][:120] + "[...]"

         return dumps(results, indent=2, ensure_ascii=False)
      except exceptions.DDGSException:
         return "Nenhum resultado encontrado, tente outra pesquisa!"


   def _video_search(self, query: str, date: Optional[str]):
      try:
         with DDGS() as ddgs:
            results: list[dict[str, str]] = ddgs.videos(
               query=query,
               region=COUNTRY,
               safesearch="moderate",
               timelimit=date,
               max_results=5
            )

         for item in results:
            item['link'] = item.pop('content')

            desc = item.get('description', '')
            if len(desc) > 150:
               item['description'] = desc[:150] + "[...]"

            item.pop('embed_html', None)
            item.pop('embed_url', None)
            item.pop('image_token', None)
            item.pop('images', None)
            item.pop('provider', None)

            stats = cast(dict[str, Any], item.pop('statistics', {}))
            item['views'] = stats.get('viewCount', '')

         for i in range(len(results)):
            results[i]['id'] = str(i)

         self._save_results(results)

         return dumps(results, indent=2, ensure_ascii=False)

      except exceptions.DDGSException:
         return "Nenhum resultado encontrado, tente outra pesquisa!"

   def _clean_html_content(self, html_content: str) -> str:
        """
        Removes useless HTML tags and their contents using regex.
        """
        # Remove scripts, styles, head, comments, etc.
        patterns_to_remove = [
            r'<script[^>]*>.*?</script>',
            r'<style[^>]*>.*?</style>',
            r'<head[^>]*>.*?</head>',
            r'<meta[^>]*>',
            r'<link[^>]*>',
            r'<img[^>]*>',
            r'<svg[^>]*>.*?</svg>',
            r'<iframe[^>]*>.*?</iframe>',
            r'<video[^>]*>.*?</video>',
            r'<audio[^>]*>.*?</audio>',
            r'<nav[^>]*>.*?</nav>',
            r'<footer[^>]*>.*?</footer>',
            r'<header[^>]*>.*?</header>',
            r'<aside[^>]*>.*?</aside>',
            r'<!--.*?-->',
            r'<noscript[^>]*>.*?</noscript>',
        ]
        
        cleaned_content = html_content
        for pattern in patterns_to_remove:
            cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.DOTALL | re.IGNORECASE)

        # Remove todas as tags HTML restantes
        cleaned_content = re.sub(r'<[^>]+>', '', cleaned_content)

        # Remove múltiplos espaços, quebras de linha e caracteres especiais
        cleaned_content = re.sub(r'\s+', ' ', cleaned_content)
        cleaned_content = re.sub(r'&[a-zA-Z]+;', '', cleaned_content)  # Remove entidades HTML

        return cleaned_content.strip()

   def _split_text_into_chunks(self, text: str, max_chunk_size: int = 500) -> list[str]:
        """
        Splits long text into smaller chunks for embedding processing.
        """
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            if current_size + len(word) + 1 > max_chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_size = len(word)
            else:
                current_chunk.append(word)
                current_size += len(word) + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

   def _extract_relevant_content_with_embeddings(self, search_text: str, text_chunks: list[str]) -> str:
        """
        Uses embeddings to find the most relevant chunks of text for the search query.
        """
        try:
            embedding_client = lms.Client('localhost:1234')
            
            # ---
            loaded_models = []
            for model in embedding_client.list_loaded_models():
                loaded_models.append(
                    {
                        'type': 'llm' if isinstance(model, lms.LLM) else 'embedding',
                        'default_identifier': model.identifier
                    }
                )
            
            unloaded_models = []
            # Se o modelo a ser usado não estiver carregado
            if self.model not in (loaded_model['default_identifier'] for loaded_model in loaded_models):
                try:
                    # Tenta iniciar uma nova instância do modelo a ser usado
                    embed_model = embedding_client.embedding.load_new_instance(self.model)
                # Se não tiver memória o suficiente
                except lms.LMStudioServerError:
                    
                    # Descarrega os modelos
                    for model in loaded_models:
                        if model['default_identifier'] == 'llm':
                            embedding_client.llm.unload(model['default_identifier'])
                            unloaded_models.append(model)
                    embed_model = embedding_client.embedding.model(self.model)
            else:
                embed_model = embedding_client.embedding.model(self.model)
            # ---

            # Gera embedding para o texto de busca
            search_embedding = embed_model.embed(search_text)

            # Gera embeddings para todos os chunks
            chunk_embeddings = []
            for chunk in text_chunks:
                chunk_embedding = embed_model.embed(chunk)
                chunk_embeddings.append(chunk_embedding)
            
            # Calcula similaridade coseno entre o texto de busca e cada chunk
            similarities = []
            for chunk_embedding in chunk_embeddings:
                similarity = self._cosine_similarity(search_embedding, chunk_embedding) #type:ignore
                similarities.append(similarity)
            
            # Ordena chunks por similaridade (maior similaridade primeiro)
            chunk_similarity_pairs = list(zip(text_chunks, similarities))
            chunk_similarity_pairs.sort(key=lambda x: x[1], reverse=True)
            
            # Retorna os 3 chunks mais relevantes
            top_chunks = chunk_similarity_pairs[:3]
            relevant_content = '\n\n---\n\n'.join([chunk for chunk, _ in top_chunks])
            
            embed_model.unload()
            
            # Recarrega modelos descarregados para prevenir problemas
            for model in unloaded_models:
                if model['type'] == 'llm':
                    embedding_client.llm.load_new_instance(model['default_identifier'])
                else:
                    embedding_client.embedding.load_new_instance(model['default_identifier'])
            
            return relevant_content
            
        except Exception as e:
            return f'Erro ao processar embeddings: {str(e)}'

   def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calcula a similaridade coseno entre dois vetores
        """
        # Normaliza os vetores
        vec1_norm = vec1 / np.linalg.norm(vec1)
        vec2_norm = vec2 / np.linalg.norm(vec2)
        
        # Calcula o produto escalar (similaridade coseno)
        similarity = np.dot(vec1_norm, vec2_norm)
        
        return float(similarity)

   def _resolve_target(self, target: str) -> str | None:
      """Retorna a URL baseada no input (seja ID ou URL direta)."""
      # Caso 1: É um ID numérico (ex: "0", "1")
      if target.isdigit():
         try:
            with open(CACHE_PAGES_PATH, 'r', encoding='utf-8') as f:
                  cache = json.load(f)
            for item in cache:
                  if item.get('id') == target:
                     return item.get('link')
         except Exception:
            return None
      
      # Caso 2: É uma URL direta
      if target.startswith('http'):
         return target
         
      return None

   @tool
   def pesquisar_google(
      self,
      busca: str,
      periodo: Literal['todos', 'dia', 'semana', 'mes'] = 'todos'
   ) -> str:
      """Pesquisa texto/informações gerais no Google.
      
      Args:
         busca: Termo ou palavra a ser buscada.
         periodo: Tempo limite do resultado, onde
            `todos` = qualquer período;
            `d` = últimas 24h;
            `s` = última semana;
            `m` = último mês;
            Padroniza para `todos`.
      """
      return self._text_search(query=busca, date=periodo, engine='google')

   @tool
   def pesquisar_imagens(self, busca: str) -> str:
      """Pesquisa imagens na web. Retorna links e descrições."""
      return self._image_search(query=busca, date=None)

   @tool
   def pesquisar_videos(self, busca: str) -> str:
      """Pesquisa vídeos (YouTube/Web). Retorna títulos, links e visualizações."""
      return self._video_search(query=busca, date=None)

   @tool
   def pesquisar_noticias(self, busca: str) -> str:
      """Pesquisa notícias recentes (última semana) sobre um tema."""
      return self._news_search(query=busca, date='w')

   @tool
   def ler_pagina_web(self, alvo: str, busca: str) -> str:
      """Lê conteúdo de uma página web (via URL ou ID de pesquisa).
      
      Args:
         alvo: URL completa (https://...) OU o ID numérico de uma pesquisa anterior (ex: '0').
         busca: Tópico específico para extrair via IA (Embeddings).
      """
      url = self._resolve_target(alvo)
      if not url:
         return "Erro: URL inválida ou ID não encontrado."

      try:
         headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
         response = requests.get(url, headers=headers, timeout=10)
         response.raise_for_status()
         clean_content = self._clean_html_content(response.text)
      except Exception as e:
         return f'Erro ao acessar {url}: {str(e)}'

      chunks = self._split_text_into_chunks(clean_content)
      return self._extract_relevant_content_with_embeddings(busca, chunks)