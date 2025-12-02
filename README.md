# Ami – Assistente Pessoal 100% Local e Modular

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/github/license/Thuur-165/Ami)
![Stars](https://img.shields.io/github/stars/Thuur-165/Ami?style=social)

**Ami** é uma assistente pessoal completa, totalmente offline, rodando com modelos locais via LM Studio.  
Tudo feito em Python puro, sem depender de nuvem, sem API externa e sem custo.

Feito por um garoto de 14 anos que simplesmente decidiu que queria uma amiga de IA que lembrasse de tudo, tivesse ferramentas úteis, entendesse imagens e ainda fosse divertida de conversar.

## Funcionalidades (já funcionando hoje)

- Conversa com streaming em tempo real  
- Memória de longo prazo com busca semântica (SQLite + FTS5)  
- Tool calling dinâmico com decorator `@tool` e auto-discovery de ferramentas  
- Suporte nativo a imagens (envie com `/img caminho/da/imagem.jpg`)  
- Pesquisa na web (Google, imagens, vídeos, notícias) via DuckDuckGo  
- Leitura inteligente de páginas com limpeza de HTML + ranking por embedding local  
- Sistema de prompt dinâmico (primeira conversa × conversas normais) – elimina alucinações de “lembro de ontem”  
- Histórico persistente com sliding window configurável  
- CLI colorida, comandos (/help, /clear, /history), tratamento de erros robusto  
- 100% configurável via `config/config.json` e `prompts.yaml`

## Demo rápida (exemplo real, direto do terminal do dev)

```text
>>> /img prints/minecraft_pordosol.jpg
Ami: Uau! Que pôr do sol lindo no Minecraft! Esse é do All the Mods 9, né? 😍
>>> Pesquisa sobre o modpack All the Mods 9
Ami: [usa a ferramenta automaticamente]
Ami: Encontrei! ATM9 tem mais de 400 mods, quests, versão “To the Sky”… quer que eu te mostre os mods mais legais?
```

## Instalação (3 comandos)

```bash
git clone https://github.com/Thuur-165/Ami.git
cd Ami
pip install -r requirements.txt
python main.py
```

Primeira execução já baixa tudo, cria pastas e abre o chat.

## História do Projeto (resumida com carinho)

| Ano   | Nome   | Tecnologia principal     | Conquista marcante                              |
|------|--------|--------------------------|-------------------------------------------------|
| 2022 | Azi    | Ollama + loop básico     | Primeira conversa local                         |
| 2023 | Azi v2 “Michuruca” | Ollama + pseudo-tool calls | Memória persistente + personalidade            |
| 2024 | Azi/Ami| AnythingLLM → LM Studio  | Descoberta de tool calling de verdade          |
| 2025 | Ami    | LM Studio + arquitetura modular | Tudo que você vê hoje – agente completo local |

Ami nasceu de um desejo simples: ter uma IA que fosse amiga de verdade, lembrasse das coisas, pesquisasse quando precisasse e nunca alucinasse, por exemplo mentindo sobre “lembrar de conversa passada”.  
O que começou como um script de 20 linhas virou um framework.

## Como contribuir / adicionar ferramentas

É absurdamente simples:

```python
# Tools/sua_ferramenta.py
from tool_registry import tool

@tool # Importante ter dicstring e tipagens, além de nomes claros
def somar(a: int, b: int) -> int: # Tipagens e nomes claros
    """Soma dois números""" # Docstring
    return a + b
```

Pronto. Na próxima inicialização ela já aparece pro modelo.

## Próximos passos

- Refatoração completa com pastas separadas PT/EN  
- Suporte a múltiplos modelos simultâneos (MoE local)  
- Interface web opcional (Gradio/FastAPI)  
- Voice mode com Whisper + Piper  
- Compilação com Nuitka pra virar executável único

## Licença

MIT – faça o que quiser, só mantém o crédito do moleque de 14 anos que fez isso nas madrugadas.

## Agradecimentos

- LM Studio (melhor frontend de LLM local que existe)  
- Neuro-sama e Vedal (inspiração de personalidade)  
- Agent Zero, LlamaIndex, LangChain (fontes de estudo)

Qualquer estrela nesse repositório é combustível pra esse garoto continuar construindo o futuro da IA local brasileira.

Feito com poucas horas de sono, pouca paciência pra coisa meia-boca, ódio por coisa boa ser paga, vício por Python e alguns anos de vida a menos.

– Thuur (Arthur), 2025


Qualquer dúvida, abre uma issue ou me chama no Discord que eu ajudo.
