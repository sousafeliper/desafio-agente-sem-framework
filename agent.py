"""
Módulo do agente conversacional para consultas futebolísticas.

Este módulo encapsula a integração com o modelo generativo (Gemini via
`google.genai`) e orquestra chamadas às ferramentas locais (`tools.py`)
quando o modelo solicita ações (padrão ReAct).

Responsabilidades principais:
- Configurar o cliente do modelo com a chave de ambiente.
- Definir as ferramentas disponíveis que o modelo pode invocar.
- Executar um loop de raciocínio/ação até o modelo gerar a resposta final.

Este arquivo foca em clareza operacional para uso em produção e para
documentação pública no GitHub.
"""

from google import genai
from google.genai import types
import os
import re
from dotenv import load_dotenv
from tools import get_team_id, get_player_id, get_player_trophies, get_player_stats

# Carrega variáveis de ambiente do arquivo .env (se existir)
load_dotenv()

# Configura o SDK com a chave da API (espera a variável GEMINI_API_KEY)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Mapeamento de funções que o modelo pode chamar. Mantemos apenas funções
# puras/side-effect-free ou que encapsulam side-effects controlados (chamadas HTTP).
available_tools = {
    "get_team_id": get_team_id,
    "get_player_id": get_player_id,
    "get_player_trophies": get_player_trophies,
    "get_player_stats": get_player_stats
}

# Instancia o modelo sem o parâmetro tools. O agente passa a operar por
# protocolo textual estrito (Thought/Action) + parser Regex local.
MODEL_NAME = 'gemini-3.1-flash-lite-preview'
SYSTEM_INSTRUCTION = """
    Você é um Analista de Futebol Pro.
    Regras de Operação:
    1. Para qualquer informação, você DEVE raciocinar e depois agir se precisar de dados.
    2. Nunca invente dados.

    FORMATO OBRIGATÓRIO:
    Sempre que precisar de uma ferramenta, responda EXATAMENTE neste formato:
    Thought: [Seu raciocínio do porquê precisa da ferramenta]
    Action: [nome_da_ferramenta]: [argumentos separados por vírgula]

    Ferramentas disponíveis:
    - get_team_id: Busca ID do time (ex: Action: get_team_id: Goiás)
    - get_player_id: Busca ID do jogador (ex: Action: get_player_id: Tadeu, 123)
    - get_player_stats: Busca stats (ex: Action: get_player_stats: 456, 2023)
    - get_player_trophies: Busca títulos (ex: Action: get_player_trophies: 456)

    Se você já tem a resposta final, apenas digite o texto final ao usuário sem usar "Action:".
    """


def _content(role: str, text: str) -> types.Content:
    return types.Content(
        role=role,
        parts=[types.Part.from_text(text=text)],
    )


def executar_loop_react(pergunta_usuario: str, max_iteracoes: int = 10) -> str:
    """
    Executa o loop ReAct com o modelo generativo.

    O padrão ReAct combina raciocínio do modelo com ações (chamadas a ferramentas).
    A função mantém um histórico de mensagens e itera até o modelo retornar texto
    final ou até atingir um número máximo de iterações.

    Parâmetros:
    - pergunta_usuario: texto da pergunta do usuário que inicia a conversa.

    Retorna:
    - string com a resposta final do agente ou mensagem de erro se exceder iterações.
    """
    historico_mensagens = [_content("user", pergunta_usuario)]

    for i in range(max_iteracoes):
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=historico_mensagens,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
            ),
        )
        text_part = response.text

        historico_mensagens.append(_content("model", text_part))

        # Extrai Action no formato: Action: nome_ferramenta: arg1, arg2
        match = re.search(r'Action:\s*(\w+):\s*(.+)', text_part)

        if match:
            tool_name = match.group(1).strip()
            args_string = match.group(2).strip()

            print(f"[AÇÃO DETECTADA]: {tool_name} com args: {args_string}")

            # Tratando argumentos simples separados por vírgula
            argumentos = [arg.strip() for arg in args_string.split(',')]

            if tool_name in available_tools:
                try:
                    resultado = available_tools[tool_name](*argumentos)
                except Exception as e:
                    resultado = f"Erro: {str(e)}"
            else:
                resultado = "Ferramenta não encontrada."

            historico_mensagens.append(_content("user", f"Observation: {resultado}"))
        else:
            # Sem Action, tratamos como resposta final.
            return text_part

    return "Limite de iterações atingido."


def perguntar_agente(pergunta: str, max_iteracoes: int = None) -> str:
    """Wrapper público simples para usar o agente no restante da aplicação.

    Mantém a API do módulo pequena e intencional: recebe uma pergunta e retorna
    a resposta do agente.
    """
    return executar_loop_react(pergunta, max_iteracoes if max_iteracoes is not None else 10)