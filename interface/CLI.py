from config import config
from pathlib import Path
import lmstudio as lms
import json
import os
import re

class CLI:
    def __init__(self):
        self.HISTORY_PATH = Path(__file__).parent.parent / 'memory' / 'history.json'

    @classmethod
    def iprint(cls, title: str, *values: object):
        """Info print"""
        print(f"\n\n[{config.colors['info']}INFO{config.colors['default']}]{config.colors['default']} {config.colors['bold']}{title}{config.colors['default']}:")
        for value in values:
            print(value, end="", flush=True)
        print("\n\n")

    def print_header(self):
        """Imprime o cabeçalho principal"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f'{config.colors["header"]}{config.colors["bold"]}\t\t{config.emojis["chat"]}Ami rodando!\n' + '='*50 + config.colors['default'])

    def is_command(self, user_input: str, command_type: str) -> bool:
        """Verifica se a entrada do usuário contém um comando específico"""
        commands = config.commands.get(command_type, [])
        return any(cmd in user_input.lower() for cmd in commands)

    def _extract_image_command(self, user_input: str) -> tuple[str, list[str]]:
        """
        Extrai comandos de imagem do input do usuário.
        Retorna: (texto_limpo, lista_de_caminhos_das_imagens)
        
        Suporta formatos:
        - /img caminho/para/imagem.jpg
        - /image caminho/para/imagem.png  
        - /img "caminho com espaços/imagem.webp"
        """
        # Padrão regex para capturar comandos de imagem
        # Suporta caminhos com aspas para lidar com espaços
        pattern = r'/(?:img|image)\s+(?:"([^"]+)"|(\S+))'
        
        matches = re.findall(pattern, user_input, re.IGNORECASE)
        image_paths = []
        
        # Processar matches - cada match tem duas capturas (com aspas, sem aspas)
        for quoted_path, unquoted_path in matches:
            path = quoted_path if quoted_path else unquoted_path
            image_paths.append(path)
        
        # Remove os comandos de imagem do texto original
        clean_text = re.sub(pattern, '', user_input, flags=re.IGNORECASE).strip()
        
        return clean_text, image_paths

    def _prepare_images(self, image_paths: list[str]) -> list:
        """
        Prepara as imagens para serem enviadas ao modelo.
        Retorna lista de handles de imagem válidos.
        """
        image_handles = []
        
        for path_str in image_paths:
            try:
                image_path = Path(path_str).resolve()
                
                # Verificar se o arquivo existe
                if not image_path.exists():
                    print(f'{config.colors["error"]}❌ Imagem não encontrada: {path_str}{config.colors["default"]}')
                    continue
                
                # Verificar se é um arquivo
                if not image_path.is_file():
                    print(f'{config.colors["error"]}❌ Caminho não é um arquivo: {path_str}{config.colors["default"]}')
                    continue
                
                # Verificar extensão suportada
                supported_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
                if image_path.suffix.lower() not in supported_extensions:
                    print(f'{config.colors["warning"]}⚠️  Formato não suportado: {path_str}')
                    print(f'{config.colors["info"]}Formatos suportados: JPG, PNG, WebP{config.colors["default"]}')
                    continue
                
                # Preparar imagem usando o SDK do LM Studio
                image_handle = lms.prepare_image(str(image_path))
                image_handles.append(image_handle)
                
                print(f'{config.colors["success"]}✅ Imagem carregada: {image_path.name}{config.colors["default"]}')
                
            except Exception as e:
                print(f'{config.colors["error"]}❌ Erro ao carregar imagem {path_str}: {str(e)}{config.colors["default"]}')
        
        return image_handles

    def process_user_input(self, user_input: str) -> tuple[str, list]:
        """
        Processa a entrada do usuário e extrai imagens se presentes.
        Retorna: (texto_processado, lista_de_handles_de_imagem)
        """
        # Extrair comandos de imagem
        clean_text, image_paths = self._extract_image_command(user_input)
        
        # Se não há texto limpo e há imagens, usar texto padrão
        if not clean_text.strip() and image_paths:
            clean_text = 'O que você vê na imagem?'
        
        # Preparar imagens
        image_handles = []
        if image_paths:
            print(f'{config.colors["info"]}🖼️  Processando {len(image_paths)} imagem(ns)...{config.colors["default"]}')
            image_handles = self._prepare_images(image_paths)
            
            if not image_handles:
                print(f'{config.colors["warning"]}⚠️  Nenhuma imagem válida foi carregada.{config.colors["default"]}')
        
        return clean_text, image_handles

    def get_user_input(self) -> tuple[str, list]:
        """
        Obtém entrada do usuário com formatação colorida e processa comandos.
        Retorna: (texto_do_usuario, lista_de_handles_de_imagem)
        """
        while True:
            try:
                prompt = input(f'\n{config.colors["user"]}>>> {config.colors["default"]}')
                
                if not prompt:
                    self._handle_empty_input()
                    continue
                
                # Verifica comandos de saída
                if self.is_command(prompt, 'exit'):
                    print(f'{config.colors["success"]}Tchau! 👋{config.colors["default"]}')
                    exit(0)
                
                # Verifica comando de ajuda
                if self.is_command(prompt, 'help'):
                    self._show_help()
                    continue
                
                # Verifica comando de limpar memória
                if self.is_command(prompt, 'clear_memory'):
                    self._handle_clear_history()
                    continue
                
                # Verifica comando de mostrar memória/histórico
                if self.is_command(prompt, 'show_history'):
                    self._handle_show_history()
                    continue
                
                if self.is_command(prompt, 'clear'):
                   self.print_header()
                   continue
                
                # Processar entrada (incluindo imagens)
                return self.process_user_input(prompt)
                
            except KeyboardInterrupt:
                if config.get('advanced.keyboard_interrupt'):
                    print(f'\n{config.colors["warning"]}{config.emojis["warning"]}Interrompido pelo usuário{config.colors["default"]}')
                    exit(0)
                else:
                    exit(1)
            except EOFError:
                print(f'\n{config.colors["success"]}Tchau! 👋{config.colors["default"]}')
                exit(0)

    def _handle_empty_input(self):
        """Manipula entrada vazia do usuário"""
        print(f'{config.colors["warning"]}Digite algo ou use um comando válido{config.colors["default"]}')
        print(f'{config.colors["info"]}Dica: digite "/help" para ver os comandos disponíveis{config.colors["default"]}')

    def _handle_clear_history(self):
        """Manipula comando de limpar histórico"""
        import time
        
        print('\n' + '='*85 + '\n')
        print(f'{config.emojis["warning"]}{config.colors["warning"]}Histórico será apagado em {config.get("advanced.data_clear_delay", 4)} segundos!! {config.colors["info"]}(Para interromper, Ctrl+C ou feche o terminal){config.colors["default"]}')
        print('\n' + '='*85)
        
        try:
            time.sleep(config.get('advanced.data_clear_delay', 4) + 1)
            
            # Limpa o histórico
            self.HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(self.HISTORY_PATH, 'w', encoding='utf-8') as file:
                json.dump({'messages': []}, file, indent=4, ensure_ascii=False)
            
            print(f'{config.colors["header"]}- {config.colors["info"]}Histórico limpo{config.colors["default"]}')
            print(f'{config.emojis["success"]}{config.colors["success"]}Histórico limpo com sucesso!{config.colors["default"]}\n')
            
        except KeyboardInterrupt:
            print(f'\n{config.colors["info"]}Operação cancelada{config.colors["default"]}')

    def _handle_show_history(self):
        """Manipula comando de mostrar histórico"""
        
        print('\n\n' + '='*50)
        print(f'{config.colors["header"]}{config.colors["bold"]}\t{config.emojis["history"]}Conteúdo do histórico:{config.colors["default"]}')
        print('='*50 + '\n')

        try:
            with open(self.HISTORY_PATH, 'r', encoding='utf-8') as file:
                history_data = json.load(file)
                messages = history_data.get('messages', [])
                
                if messages:
                    for i, message in enumerate(messages, 1):
                        role = message.get('role', 'unknown')
                        content = message.get('content', '')[:100] + '...' if len(message.get('content', '')) > 100 else message.get('content', '')
                        
                        color = config.colors['user'] if role == 'user' else config.colors['assistant']
                        
                        # Indicar se há imagens na mensagem
                        images_indicator = ' 🖼️' if message.get('images') else ''
                        
                        print(f'{config.colors["info"]}{i}. {color}[{role.upper()}]{images_indicator}{config.colors["default"]} {content}')
                else:
                    print(f'{config.colors["info"]}- {config.colors["header"]}{config.colors["underline"]}Vazio{config.colors["default"]}')
                    
        except (FileNotFoundError, json.JSONDecodeError):
            print(f'{config.colors["info"]}- {config.colors["header"]}{config.colors["underline"]}Nenhum histórico encontrado{config.colors["default"]}')

        print('\n' + '='*50)

    def _show_help(self):
        """Exibe ajuda dos comandos disponíveis dinamicamente"""
        print('\n\n' + '='*50)
        print(config.colors['header'] + config.colors['bold'] + '📋 Comandos disponíveis:' + config.colors['default'])
        print('='*50)
        
        # Itera pelos comandos disponíveis na configuração
        available_commands = config.commands
        
        for cmd_key, cmd_list in available_commands.items():
            if cmd_list:  # Só mostra se há comandos definidos
                cmd_str = ', '.join(cmd_list)
                print(f'{config.colors["header"]}- {config.colors["info"]}{cmd_str}{config.colors["default"]} - {cmd_key}')
        
        # Adicionar ajuda específica para imagens
        print(f'\n{config.colors["header"]}🖼️  Comandos de imagem:{config.colors["default"]}')
        print(f'{config.colors["info"]}/img caminho/para/imagem.jpg{config.colors["default"]} - Enviar imagem')
        print(f'{config.colors["info"]}/image "caminho com espaços/imagem.png"{config.colors["default"]} - Enviar imagem (com aspas)')
        print(f'{config.colors["info"]}Formatos suportados: JPG, PNG, WebP{config.colors["default"]}')
        
        print('='*50 + '\n')
