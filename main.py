from typing import Dict, List, Any, Union
from interface import CLI
from config import config
from pathlib import Path
import lmstudio as lms
from Tools import ToolRegistry
from time import sleep
import json

# ------ consts ------
MODEL = config.model
INFER_CONFIG: lms.LlmPredictionConfigDict = config.infer_params
LOAD_CONFIG: lms.LlmLoadModelConfigDict = config.load_params
HISTORY_PATH = Path(__file__).parent / 'memory' / 'history.json'
HISTORY_LIMIT = config.history_limit
MessageType = Union[lms.AssistantResponse, lms.ToolResultMessage, lms.UserMessage]
# ---------------------

# -- Main components --
print(f'{config.emojis['loading']}{config.colors['dim']}Carregando modelo...{config.colors['default']}')
client = lms.Client(config.host)
model = client.llm.model(
    MODEL,
    config=LOAD_CONFIG
)
chat = lms.Chat()
cli = CLI()
tools = ToolRegistry.get_all_tools()
# ---------------------

def get_history_full() -> dict[str, list[Any]]:
    try:
        with open(HISTORY_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'messages': []}

def ensure_first_message_is_user(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Garante que a primeira mensagem tenha role='user', removendo mensagens iniciais se necessário."""
    if not messages:
        return messages
    
    # Remove mensagens do iní­cio até encontrar uma com role='user'
    while messages and messages[0].get('role') != 'user':
        messages.pop(0)
    
    return messages

def should_print_newline(message: MessageType) -> bool:
    """
    Determina se deve quebrar linha após message.
    """
    content = message.to_dict()['content']
    role = message.to_dict()['role']
    
    if role == 'tool': return False
    if content[0]['type'] == 'text' and content[0]['text'] == "": return False
    
    return True

def load_history() -> bool:
    """Carrega o histórico de mensagens aplicando o limite configurado."""
    try:
        print(f'{config.emojis['loading']}{config.colors['dim']}Carregando histórico...{config.colors['default']}')
        messages = get_history_full().get('messages', [])
        
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

        return True if len(messages) == 0 else False

    except (FileNotFoundError, json.JSONDecodeError):
        # Se não existe histórico ou está corrompido, começar do zero
        save_history_structure()
        return True

def save_history_structure() -> None:
    """Cria ou atualiza a estrutura do arquivo de histórico."""
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    history_data = get_history_full()

    # Aplicar limite no histórico salvo
    if HISTORY_LIMIT > 0:
        history_data['messages'] = history_data['messages'][-HISTORY_LIMIT:]
    
    # Garantir que a primeira mensagem seja do usuário
    history_data['messages'] = ensure_first_message_is_user(history_data['messages'])

    with open(HISTORY_PATH, 'w', encoding='utf-8') as file:
        json.dump(history_data, file, indent=2, ensure_ascii=False)

def save_message(message: MessageType) -> None:
    """Salva uma mensagem individual no histórico com sliding window."""
    
    history_data = get_history_full()

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
        json.dump(history_data, file, indent=2, ensure_ascii=False)

def print_fragment(fragment: lms.LlmPredictionFragment, _) -> None:
    """Callback para imprimir fragmentos da resposta em tempo real."""
    print(fragment.content, end='', flush=True)

def handle_message(message: MessageType) -> None:
    """Processa mensagens recebidas do modelo."""
    if should_print_newline(message):
        print()
    
    chat.append(message=message)
    save_message(message)


# Main loop
def main():
    global chat
    
    is_first = load_history()
    prompt_updates_needed = 2 if is_first else 1
    
    # ===== PRIMEIRO CARREGAMENTO DO PROMPT =====
    if prompt_updates_needed:
        prompt_updates_needed -= 1
        chat = config.update_system_prompt(chat, is_first)
    # ===============================================

    print(f'{config.emojis['success']}{config.colors['success']}Pronto!{config.colors['default']}')
    sleep(2) # Pequeno delay pra poder ver as mensagens
    cli.print_header()
    while True:
        
        # Obter entrada do usuário
        user_input, image_handles = cli.get_user_input()
        
        # ===== APÓS PRIMEIRA MENSAGEM, NÃO É MAIS "FIRST" =====
        if is_first: is_first = False  # Da próxima vez usa continuation_rules
        # ======================================================

        # Adicionar mensagem do usuário (com ou sem imagens)
        if image_handles:
            chat.add_user_message(user_input, images=image_handles)
            print(f'{config.colors['info']}🖼️ Mensagem enviada com {len(image_handles)} imagem(ns){config.colors['assistant']}')
        else:
            chat.add_user_message(user_input)

        # Salvar mensagem do usuário
        if isinstance(last_message := chat._get_last_message('user'), lms.UserMessage):
            save_message(last_message)

        print(f'\n{config.colors['assistant']}Ami{config.colors['default']}: ', end='')

        # Executar predição
        try:
            # cli.iprint("Chat", chat)
            model.act(
                chat=chat,
                tools=tools,
                on_prediction_fragment=print_fragment,
                on_message=handle_message,
                config=INFER_CONFIG
            )

            # ===== ATUALIZA SYSTEM PROMPT SE PRECISAR =====
            if prompt_updates_needed:
                prompt_updates_needed -= 1
                chat = config.update_system_prompt(chat, is_first)
            # ===============================================

        except Exception as e:
            print(f'{config.colors['error']}{config.emojis['error']} Erro durante a predição: {str(e)}{config.colors['default']}')
            try:
                history_data = get_history_full()
                messages = history_data.get('messages', [])
                if messages:  # ← Proteção
                    messages.pop()
                    history_data['messages'] = messages
                with open(HISTORY_PATH, 'w', encoding='utf-8') as history_file:
                    json.dump(history_data, history_file, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f'{config.colors['error']}{config.emojis['error']} Erro removendo última mensagem: {str(e)}{config.colors['default']}')

# Run
if __name__ == '__main__':
    main()