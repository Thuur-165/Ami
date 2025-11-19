from typing import Dict, List, Any
from interface import CLI
from config import config
from pathlib import Path
import lmstudio as lms
import Tools
import time
import json

# ------ consts ------
MODEL = config.model
SYSTEM_PROMPT = config.system_prompt
INFER_CONFIG: lms.LlmPredictionConfigDict = config.get('advanced.inferParams')
LOAD_CONFIG: lms.LlmLoadModelConfigDict = config.get('advanced.loadParams')
HISTORY_PATH = Path(__file__).parent / 'memory' / 'history.json'
HISTORY_LIMIT = config.history_limit
# ---------------------

# -- Main components --
print(f'{config.emojis['loading']}{config.colors['dim']}Carregando modelo...{config.colors['default']}')
client = lms.Client(config.host)
model = client.llm.model(MODEL, config=LOAD_CONFIG)
chat = lms.Chat(SYSTEM_PROMPT)
cli = CLI()
tools = Tools.ToolRegistry.get_all_tools()
# ---------------------

def ensure_first_message_is_user(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Garante que a primeira mensagem tenha role='user', removendo mensagens iniciais se necessário."""
    if not messages:
        return messages
    
    # Remove mensagens do início até encontrar uma com role='user'
    while messages and messages[0].get('role') != 'user':
        messages.pop(0)
    
    return messages

def load_history() -> None:
    """Carrega o histórico de mensagens aplicando o limite configurado."""
    try:
        print(f'{config.emojis['loading']}{config.colors['dim']}Carregando histórico...{config.colors['default']}')
        with open(HISTORY_PATH, 'r', encoding='utf-8') as history_file:
            history_data: Dict[str, List[Any]] = json.load(history_file)
            messages = history_data.get('messages', [])
            
            # Aplicar limite do histórico (mantém as mensagens mais recentes)
            if HISTORY_LIMIT > 0:
                messages = messages[-HISTORY_LIMIT:]
            
            # Garantir que a primeira mensagem seja do usuário
            messages = ensure_first_message_is_user(messages)

            for message in messages:
                # Recrear handles de imagem se existirem (apenas para carregamento)
                # Nota: As imagens não são persistidas entre sessões, apenas referências
                images = message['content'][-1].get('fileType')
                
                if images:
                    chat.add_entry(message['role'], message['content'][0])
                else:
                    chat.add_entry(message['role'], message['content'])

        print(f'{config.emojis['success']}{config.colors['success']}Pronto!{config.colors['default']}')
        time.sleep(0.3)

    except (FileNotFoundError, json.JSONDecodeError):
        # Se não existe histórico ou está corrompido, começar do zero
        save_history_structure()

def save_history_structure() -> None:
    """Cria ou atualiza a estrutura do arquivo de histórico."""
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(HISTORY_PATH, 'r', encoding='utf-8') as file:
            history_data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        history_data = {'messages': []}

    # Aplicar limite no histórico salvo
    if HISTORY_LIMIT > 0:
        history_data['messages'] = history_data['messages'][-HISTORY_LIMIT:]
    
    # Garantir que a primeira mensagem seja do usuário
    history_data['messages'] = ensure_first_message_is_user(history_data['messages'])

    with open(HISTORY_PATH, 'w', encoding='utf-8') as file:
        json.dump(history_data, file, indent=2, ensure_ascii=False)

def save_message(message: lms.AssistantResponse | lms.ToolResultMessage | lms.UserMessage) -> None:
    """Salva uma mensagem individual no histórico com sliding window."""
    try:
        with open(HISTORY_PATH, 'r', encoding='utf-8') as file:
            history_data: Dict[str, List[Any]] = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        history_data = {'messages': []}

    # Converter mensagem para dict
    message_dict = message.to_dict()

    # Adicionar nova mensagem
    history_data['messages'].append(message_dict)

    # Aplicar sliding window: remove a mais antiga se exceder o limite
    if HISTORY_LIMIT > 0 and len(history_data['messages']) > HISTORY_LIMIT:
        history_data['messages'] = history_data['messages'][-HISTORY_LIMIT:]
    
    # Garantir que a primeira mensagem seja do usuário após aplicar o limite
    history_data['messages'] = ensure_first_message_is_user(history_data['messages'])
    
    with open(HISTORY_PATH, 'w', encoding='utf-8') as file:
        json.dump(history_data, file, indent=4, ensure_ascii=False)

def print_fragment(fragment: lms.LlmPredictionFragment, _) -> None:
    """Callback para imprimir fragmentos da resposta em tempo real."""
    print(fragment.content, end='', flush=True)

def handle_message(message: lms.AssistantResponse | lms.ToolResultMessage) -> None:
    """Processa mensagens recebidas do modelo."""
    print()  # Nova linha após a resposta
    chat.append(message=message)
    save_message(message)


# Main loop
def main():
    load_history()
    cli.print_header()
    while True:
        # Obter entrada do usuário (agora retorna texto e imagens)
        user_input, image_handles = cli.get_user_input()
        
        # Adicionar mensagem do usuário (com ou sem imagens)
        if image_handles:
            chat.add_user_message(user_input, images=image_handles)
            print(f'{config.colors['info']}📤 Mensagem enviada com {len(image_handles)} imagem(ns){config.colors['assistant']}')
        else:
            chat.add_user_message(user_input)
        
        # Salvar mensagem do usuário
        if isinstance(last_message := chat._get_last_message('user'), lms.UserMessage):
            save_message(last_message)
        
        print(f'\n{config.colors['assistant']}Ami{config.colors['default']}: ', end='')
        
        # Executar predição
        try:
            model.act(
                chat=chat,
                tools=tools,
                on_prediction_fragment=print_fragment,
                on_message=handle_message,
                config=INFER_CONFIG
            )
        except Exception as e:
            print(f'{config.colors['error']}❌ Erro durante a predição: {str(e)}{config.colors['default']}')

# Run
if __name__ == '__main__':
    main()