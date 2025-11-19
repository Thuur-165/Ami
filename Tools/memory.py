"""
Ferramenta padrão de exemplo para gerenciamento de memórias

Escrita originalmente por Arthur (Desenvolvedor original)
"""

from .tool_registry import tool
from datetime import datetime
from typing import Optional, Literal
from pathlib import Path
import sqlite3

DATABASE_PATH = Path(__file__).parent.parent / 'memory' / 'memories.db'

class MemorySystem:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DATABASE_PATH
        self._init_database()

    def _init_database(self):
        """Inicializa o banco de dados e cria as tabelas necessárias"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela principal simplificada
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            
            # Índice para busca case-insensitive por título
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_titulo_lower 
                ON memories(LOWER(titulo))
            ''')
            
            # Tabela FTS5 para busca de texto completo
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    titulo, descricao, 
                    content='memories', 
                    content_rowid='id'
                )
            ''')
            
            # Triggers para manter FTS sincronizado
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, titulo, descricao)
                    VALUES (new.id, new.titulo, new.descricao);
                END
            ''')
            
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, titulo, descricao)
                    VALUES('delete', old.id, old.titulo, old.descricao);
                END
            ''')
            
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, titulo, descricao)
                    VALUES('delete', old.id, old.titulo, old.descricao);
                    INSERT INTO memories_fts(rowid, titulo, descricao)
                    VALUES (new.id, new.titulo, new.descricao);
                END
            ''')
            
            conn.commit()

    def _normalize_titulo(self, titulo: str) -> str:
        """Normaliza título: remove espaços extras e converte para minúsculo"""
        return ' '.join(titulo.lower().strip().split())

    def _save_memory(self, titulo: str, descricao: str) -> str:
        """Salva uma memória no banco de dados"""
        try:
            if not titulo.strip():
                return 'Erro: Título não pode estar vazio'
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO memories (titulo, descricao, timestamp) VALUES (?, ?, ?)',
                    (titulo.strip(), descricao.strip(), timestamp)
                )
                memory_id = cursor.lastrowid
                conn.commit()
            
            return f'✓ Memória salva: "{titulo.strip()}" (ID: {memory_id})'
        except Exception as e:
            return f'Erro ao salvar: {str(e)}'

    def _search_memories(self, termo_busca: str, limit: int = 10) -> str:
        """Busca memórias por palavra-chave no título ou descrição"""
        try:
            if not termo_busca.strip():
                return self._get_recent_memories()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Busca FTS
                cursor.execute('''
                    SELECT m.id, m.titulo, m.descricao, m.timestamp
                    FROM memories_fts fts
                    JOIN memories m ON fts.rowid = m.id
                    WHERE memories_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                ''', (termo_busca, limit))
                
                results = cursor.fetchall()
                
                if not results:
                    return f'Nenhuma memória encontrada para "{termo_busca}"'
                
                output = f'Encontradas {len(results)} memória(s):\n\n'
                for mem_id, titulo, desc, ts in results:
                    try:
                        dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                        formatted = dt.strftime('%d/%m/%Y às %H:%M')
                    except ValueError:
                        formatted = ts
                    
                    output += f'• **{titulo}** (ID: {mem_id})\n'
                    output += f'  {desc}\n'
                    output += f'  📅 {formatted}\n\n'
                
                return output.strip()
        except Exception as e:
            return f'Erro ao buscar: {str(e)}'

    def _get_recent_memories(self, limit: int = 5) -> str:
        """Recupera as memórias mais recentes"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, titulo, descricao, timestamp
                    FROM memories 
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                results = cursor.fetchall()
                
                if not results:
                    return 'Nenhuma memória salva ainda'
                
                output = f'Últimas {len(results)} memória(s):\n\n'
                for mem_id, titulo, desc, ts in results:
                    try:
                        dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                        formatted = dt.strftime('%d/%m/%Y às %H:%M')
                    except ValueError:
                        formatted = ts
                    
                    output += f'• **{titulo}** (ID: {mem_id})\n'
                    output += f'  {desc}\n'
                    output += f'  📅 {formatted}\n\n'
                
                return output.strip()
        except Exception as e:
            return f'Erro ao recuperar memórias recentes: {str(e)}'

    def _delete_memory(self, titulo: str) -> str:
        """Remove memória pelo título (case-insensitive)"""
        try:
            normalized = self._normalize_titulo(titulo)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Busca a memória
                cursor.execute(
                    'SELECT id, titulo FROM memories WHERE LOWER(TRIM(titulo)) = ?',
                    (normalized,)
                )
                result = cursor.fetchone()
                
                if not result:
                    return f'Memória "{titulo}" não encontrada'
                
                mem_id, original_titulo = result
                
                # Deleta
                cursor.execute('DELETE FROM memories WHERE id = ?', (mem_id,))
                conn.commit()
                
                return f'✓ Memória deletada: "{original_titulo}" (ID: {mem_id})'
        except Exception as e:
            return f'Erro ao deletar: {str(e)}'

    @tool
    def gerenciar_memorias(
        self,
        acao: Literal['salvar', 'pesquisar', 'recentes', 'deletar'], 
        titulo: str = '',
        descricao: str = '',
        busca: str = ''
    ) -> str:
        """Gerencia informações armazenadas permanentemente no sistema de memória.
        
        Use esta ferramenta para:
        - 'salvar': Armazenar informações importantes para consulta futura
        - 'pesquisar': Encontrar memórias relacionadas a um termo específico
        - 'recentes': Ver as memórias mais recentemente salvas
        - 'deletar': Remover uma memória pelo título
        
        Args:
            acao: Ação a ser executada (obrigatório)
            titulo: Título da memória (obrigatório para 'salvar' e 'deletar')
            descricao: Conteúdo detalhado da memória (obrigatório para 'salvar')
            busca: Termo para pesquisa (obrigatório para 'pesquisar')
        
        Returns:
            Confirmação detalhada da operação realizada ou mensagem de erro explicativa
            com sugestões para correção
        """
        try:
            match acao:
                case 'salvar':
                    if not titulo:
                        return 'Erro: operação "salvar" requer título'
                    return self._save_memory(titulo, descricao)
                
                case 'pesquisar':
                    if not busca:
                        return 'Erro: operação "pesquisar" requer argumento "busca"'
                    return self._search_memories(busca)
                
                case 'recentes':
                    return self._get_recent_memories()
                
                case 'deletar':
                    if not titulo:
                        return 'Erro: operação "deletar" requer título'
                    return self._delete_memory(titulo)
                
                case _:
                    return f'Operação inválida: {acao}. Use: salvar, pesquisar, recentes ou deletar'
        
        except Exception as e:
            return f'Erro na operação "{acao}": {str(e)}'