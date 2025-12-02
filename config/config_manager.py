from pathlib import Path
from typing import Any, Optional, Union
from lmstudio import LlmPredictionConfigDict, LlmLoadModelConfigDict, Chat, AnyChatMessageDict
import json
import os
import yaml

CONFIG_PATH = Path(__file__).parent
PROMPTS_PATH = CONFIG_PATH.parent

PathLike = Union[Path, str]

class ConfigManager:
    def __init__(self, config_path: Optional[PathLike] = None, prompts_path: Optional[PathLike] = None) -> None:
        if not config_path:
            self._config_path = CONFIG_PATH / 'config.json'
        else:
            self._config_path = config_path

        if not prompts_path:
            self._prompts_path = PROMPTS_PATH / 'prompts.yaml'
        else:
            self._prompts_path = prompts_path
        
        self._config: dict[str, Any] = {}
        self._is_first_conversation: bool = False
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

            
    def update_system_prompt(self, chat: Chat, is_first: bool = False) -> Chat:
            """
            Reconstrói o Chat inserindo o System Prompt correto no INÍCIO (Index 0).
            Remove prompts antigos para evitar duplicação.
            Retorna uma NOVA instância de Chat.
            """
            print(f'{self.emojis["loading"]}{self.colors["dim"]}Carregando persona da Ami...{self.colors["default"]}')

            try:
                with open(self._prompts_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                # Seções compartilhadas
                bridge = data.get('bridge', '')
                persona = data.get('persona', '')
                tool_usage = data.get('tool_usage', '')
                response_style = data.get('response_style', '')
                
                if is_first:
                    context_rules = data.get('first_conversation_rules', '')
                    print(f'{self.emojis["info"]}{self.colors["info"]}Usando prompt de primeira conversa{self.colors["default"]}')
                else:
                    context_rules = data.get('continuation_rules', '')
                    print(f'{self.emojis["info"]}{self.colors["info"]}Usando prompt de continuação{self.colors["default"]}')
                
                # Monta prompt completo
                full_prompt = f"""
{bridge}
{persona}
{context_rules}
{tool_usage}
{response_style}
"""
                
                # 1. Pega o histórico cru (dicionário)
                history = chat._get_history()
                messages = history.get('messages', [])
                
                # 2. Filtra mensagens antigas do sistema (remove o prompt anterior)
                # Isso garante que não acumule lixo: [Sys_Old, User, Assistant, Sys_New...]
                clean_messages = [msg for msg in messages if msg.get('role') != 'system']
                
                # 3. Cria a nova mensagem de sistema formatada para o LM Studio
                new_system_msg: AnyChatMessageDict = {
                    "role": "system", 
                    "content": [{"type": "text", "text": full_prompt}]
                }
                
                # 4. Insere no TOPO (Index 0)
                # Nota: Colocar no index 0 é mais seguro para o 'rollingWindow' do que no meio.
                # O modelo lerá: [Novas Regras] -> [Histórico da conversa...]
                clean_messages.insert(0, new_system_msg)
                
                # 5. Retorna um NOVO objeto Chat reconstruído
                return Chat.from_history({"messages": clean_messages})
                
            except Exception as e:
                print(f'{self.emojis["error"]}{self.colors["error"]}Erro ao carregar prompts.yaml: {e}{self.colors["default"]}')
                # Fallback: Retorna o chat original com um append simples (melhor que quebrar)
                chat.add_system_prompt("Você é Ami, assistente pessoal do Arthur.")
                return chat

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
    def host(self) -> str:
        return self.get('host', 'localhost:1234')
    
    @property
    def history_limit(self) -> int:
        return self.get('advanced.history_limit', 16)

    @property
    def load_params(self) -> LlmLoadModelConfigDict:
        return self.get(
            'advanced.load_params',
            {
                "contextLength": 10240,
                "ropeFrequencyBase": 12000, 
                "flashAttention": True
            }
        )
    
    @property
    def infer_params(self) -> LlmPredictionConfigDict:
        params: dict[str, Any] = self.get( 
            'advanced.infer_params',
            # Se não acha, padroniza para uma média segura entre modelos do LM Studio
            {
            "contextOverflowPolicy": "rollingWindow",
            "temperature": 0.25,
            "topPSampling": 0.9,
            "topKSampling": 40,
            "repeatPenalty": 1.1,
            "minPSampling": 0.05
            }
        )
        # Se especificado em config.json, carrega template jinja e adiciona aos parâmetros com suporte a palavra chave "root" para diretório absoluto do projeto
        if full_path := self.get('advanced.jinja_template', None):
            full_path = Path(full_path.replace('root', str(PROMPTS_PATH)))
            params['promptTemplate'] = {
                "type": "jinja",
                "stopStrings": [],
                "jinjaPromptTemplate": {
                    "template": full_path.read_text(encoding='utf-8')
                }
            }

        return LlmPredictionConfigDict(params) #type:ignore Pylance fala que `LlmPredictionConfigDict` não aceita `dict[str, Any]` mas aceita sim

config = ConfigManager()