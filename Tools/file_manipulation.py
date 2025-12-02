"""
Ferramenta padrão de exemplo para gerenciamento de arquivos

Escrita originalmente por Arthur (Desenvolvedor original)
"""

from .tool_registry import tool
from typing import Optional, Literal
from config import config
from pathlib import Path
import lmstudio as lms
import os

FILE_SANDBOX = Path(__file__).parent.parent / 'file_sandbox'

class FileManager:
    def __init__(self):
        """
        Inicializa o FileManager com um diretório sandbox.
        Args:
            caminho_sandbox: Caminho personalizado opcional para o sandbox de arquivos. 
                           Se None, usa 'file_sandbox' no diretório atual.
        """
        FILE_SANDBOX.mkdir(parents=True, exist_ok=True)

    def _read_file(self, name: str | Path) -> str:
        """Lê o conteúdo de um arquivo."""
        try:
            FILE_SANDBOX.mkdir(exist_ok=True)
            with open(FILE_SANDBOX / name, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            return conteudo
        except FileNotFoundError:
            return f'Erro: Arquivo {name} não encontrado.'
        except Exception as e:
            return f'Erro ao ler arquivo {name}: {e}'

    def _delete_files(self, names: str) -> str:
        """Deleta um ou mais arquivos."""
        arquivos = names.split('|')
        erros = []
        sucesso = []
        for arquivo in arquivos:
            try:
                os.remove(FILE_SANDBOX / arquivo.strip())
                sucesso.append(arquivo.strip())
            except Exception as e:
                erros.append(f'Erro ao deletar {arquivo.strip()}: {e}')
        resultado = []
        if sucesso:
            resultado.append(f'Arquivos deletados: {", ".join(sucesso)}')
        if erros:
            resultado.append("\n".join(erros))
        return "\n".join(resultado) if resultado else "Nenhum arquivo foi processado."

    def _list_files(self) -> str:
        """Lista todos os arquivos no sandbox."""
        try:
            FILE_SANDBOX.mkdir(exist_ok=True)
            arquivos = os.listdir(FILE_SANDBOX)
            if arquivos:
                return "Arquivos:\n" + "\n".join(f"- {arquivo}" for arquivo in arquivos)
            else:
                return 'Diretório vazio.'
        except Exception as e:
            return f'Erro ao listar arquivos: {e}'

    def _summarize_file(self, name: str, foco: Optional[str]) -> str:
        """Lê um arquivo e gera um resumo."""
        try:
            conteudo = self._read_file(name)
            if conteudo.startswith('Erro'):
                return conteudo
            if len(conteudo.strip()) < 200:
                return f'Conteúdo muito curto. Conteúdo: {conteudo[:200]}'
            
            # Gerenciamento de memória
            modelos_carregados = []
            try:
                modelos_carregados = lms.list_loaded_models()
                for modelo in modelos_carregados:
                    lms.llm(modelo.identifier).unload()
            except Exception:
                pass

            try:
                resumo_llm = lms.llm(config.get('models.file_summarizer'))
                prompt = f"""Resuma concisamente o conteúdo abaixo do arquivo '{name}':
---
{conteudo[:35000]}
---
Forneça um resumo claro em 2-3 parágrafos"""
                prompt += f' focando em "{foco}".' if foco else '.'
                
                resumo = resumo_llm.respond(prompt)
                resumo_llm.unload()
                
                # Recarrega modelos
                for modelo in modelos_carregados:
                    try:
                        lms.llm(modelo.identifier)
                    except Exception:
                        pass
                        
                return f'Resumo de {name}:\n{resumo}'
            except Exception as e:
                return f'Erro ao gerar resumo: {e}'
        except Exception as e:
            return f'Erro ao resumir arquivo: {e}'

    @tool
    def criar_arquivo(self, nome: str, conteudo: str) -> str:
        """Cria um novo arquivo (ou sobrescreve) no sandbox.
        
        Use para salvar códigos, notas, listas ou qualquer texto gerado.
        Nomes de arquivos não podem conter "/" assim como em qualquer sistema operacional.
        
        Args:
            nome: Nome do arquivo com extensão (ex: nota.txt, script.py).
            conteudo: O texto completo que será escrito no arquivo.
        """
        try:            
            full_path = FILE_SANDBOX / nome
            
            if full_path.exists():
                current = full_path.read_text(encoding='utf-8')
                preview = current if len(current) < 200 else current[:200] + '[...]'
                return f'Arquivo já existe! Conteúdo: {preview}'
            
            full_path.write_text(conteudo or '', encoding='utf-8')
            return f'Arquivo {nome} criado com sucesso!'
            
        except PermissionError as e:
            return f'Erro de permissão ao criar o arquivo {nome}: {e}'
        except OSError as e:
            return f'Erro no sistema de arquivos ao criar {nome}: {e}'
        except Exception as e:
            return f'Erro inesperado ao criar arquivo {nome}: {e}'

    @tool
    def ler_arquivo(self, nome: str, foco: Optional[str] = None) -> str:
        """Lê um arquivo. Se for muito grande, resume automaticamente com IA auxiliar.
        
        O modelo deve usar 'foco' se estiver procurando algo específico num arquivo grande.
        
        Args:
            nome: Nome do arquivo.
            foco: (Opcional) Se o arquivo for resumido, foca neste tópico.
        """
        # Tenta ler primeiro
        conteudo = self._read_file(nome)
        
        # Se retornou erro, devolve o erro
        if conteudo.startswith("Erro"):
            return conteudo
            
        # Limite de caracteres "seguro" antes de decidir resumir (aprox 3k tokens)
        LIMITE_TAMANHO = 3000
        
        if len(conteudo) > LIMITE_TAMANHO:
            return (f"Arquivo '{nome}' é muito grande ({len(conteudo)} caracteres). "
                    f"Gerando resumo automático...\n\n" + 
                    self._summarize_file(nome, foco))
        
        return conteudo

    @tool
    def listar_arquivos(self) -> str:
        """Lista todos os nomes de arquivos presentes no diretório sandbox.
        
        Use para ver o que já foi criado antes de criar novos arquivos.
        """
        return self._list_files()

    @tool
    def deletar_arquivo(self, nome: str) -> str:
        """Remove arquivos do sistema.
        
        Args:
            nome: Nome do arquivo (ou arquivos separados por |) para deletar.
        """
        return self._delete_files(nome)