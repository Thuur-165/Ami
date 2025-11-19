from pathlib import Path
from typing import Any
import json
import os

CONFIG_PATH = Path(__file__).parent

class ConfigManager:
    def __init__(self, config_path: Path | str | None = None, system_prompt_path: Path | str | None = None) -> None:
        if not config_path:
            self._config_path = CONFIG_PATH / 'config.json'
        else:
            self._config_path = config_path
        if not system_prompt_path:
            self._sys_prompt = CONFIG_PATH / 'system.txt'
        else:
            self._sys_prompt = system_prompt_path
        
        self._config: dict[str, Any] = {}
        self.loadConfig()

    def loadConfig(self):
            """Carrega as configurações do arquivo JSON"""
            if not os.path.exists(self._config_path):
                 print('\u001b[31m❌ Erro ao abrir configurações:\u001b[0m', '\u001b[4mArquivo não existente ou caminho inválido\u001b[0m')
                
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print('\u001b[31m❌ Erro ao carregar configurações:\u001b[0m', '\u001b[4m'+ str(e) + '\u001b[0m')

    def get(self, key: str, default: Any = None) -> Any:
        """Obtém valor de configuração usando notação de ponto"""
        keys: list = key.split('.')
        value: dict = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value

    def set(self, key: str, value: Any):
        """Define valor de configuração usando notação de ponto"""
        keys: list = key.split('.')
        config_ref = self.config
        
        for k in keys[:-1]:
            if k not in config_ref:
                config_ref[k] = {}
            config_ref = config_ref[k]
        
        config_ref[keys[-1]] = value

    def isCommand(self, user_input: str, command_type: str) -> bool:
        """Verifica se entrada do usuário é um comando específico"""
        command_list = self.commands.get(command_type, [])
        return any(cmd in user_input.lower() for cmd in command_list)

    @property
    def model(self) -> str:
        return self.get('models.main', 'google/gemma-3-12b')
    
    @property
    def colors(self) -> dict[str, str]:
        return self.get('colors', {})
    
    @property
    def emojis(self) -> dict[str, str]:
        return self.get('emojis', {})
    
    @property
    def messages(self) -> dict[str, str]:
        return self.get('messages', {})
    
    @property
    def commands(self) -> dict[str, list[str]]:
        return self.get('commands', {})
    
    @property
    def system_prompt(self) -> str:
        print(f'{self.emojis['loading']}{self.colors['dim']}Carregando system prompt...{self.colors['default']}')
        with open(self._sys_prompt, 'r', encoding='utf-8') as prompt:
            return prompt.read()
    
    @property
    def host(self) -> str:
        return self.get('host', 'localhost:1234')
    
    @property
    def history_limit(self) -> int:
        return self.get('advanced.history_limit', 16)

config = ConfigManager()
