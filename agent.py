"""
Módulo do agente conversacional para consultas futebolísticas.

Este módulo encapsula a integração com o modelo generativo (Gemini via
`google.generativeai`) e orquestra chamadas às ferramentas locais
(`tools.py`) quando o modelo solicita ações (padrão ReAct).

Responsabilidades principais:
- Configurar o cliente do modelo com a chave de ambiente.
- Definir as ferramentas disponíveis que o modelo pode invocar.
- Executar um loop de raciocínio/ação até o modelo gerar a resposta final.

Este arquivo foca em clareza operacional para uso em produção e para
documentação pública no GitHub.
"""

import google.generativeai as genai
import os
from dotenv import load_dotenv
from tools import get_team_id, get_player_id, get_player_trophies, get_player_stats

# Carrega variáveis de ambiente do arquivo .env (se existir)
load_dotenv()

# Configura o SDK com a chave da API (espera a variável GEMINI_API_KEY)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Mapeamento de funções que o modelo pode chamar. Mantemos apenas funções
# puras/side-effect-free ou que encapsulam side-effects controlados (chamadas HTTP).
available_tools = {
    "get_team_id": get_team_id,
    "get_player_id": get_player_id,
    "get_player_trophies": get_player_trophies,
    "get_player_stats": get_player_stats
}

# Instancia o modelo generativo com instruções de sistema que guiam o comportamento
# do agente (ex: fluxos obrigatórios de chamadas de API e regras sobre veracidade).
model = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite-preview',
    tools=list(available_tools.values()),
    system_instruction="""
    Você é um Analista de Futebol Pro.
    Regras de Operação:
    1. Para qualquer informação de jogador, você DEVE primeiro obter o ID do Time (get_team_id).
    2. Com o team_id e o nome do jogador, obtenha o player_id (get_player_id).
    3. Nunca invente dados. Se a API retornar vazio, informe ao usuário.
    4. Se o usuário pedir temporadas futuras (ex: 2025, 2026), explique que os dados reais só vão até 2024.
    5. Sempre forneça respostas educadas e baseadas nos dados retornados pelas funções.
    """
)


def executar_loop_react(pergunta_usuario: str, max_iteracoes: int = None) -> str:
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
    # Histórico inicial com a mensagem do usuário. A estrutura segue o formato
    # esperado pelo wrapper do SDK (roles e partes/payloads).
    historico_mensagens = [{"role": "user", "parts": [pergunta_usuario]}]
    # Permite configurar o limite via argumento ou variável de ambiente
    if max_iteracoes is None:
        try:
            max_iteracoes = int(os.getenv("MAX_REACT_ITERATIONS", "20"))
        except Exception:
            max_iteracoes = 20

    for i in range(max_iteracoes):
        # Log da iteração atual para debug
        try:
            print(f"[DEBUG] Iteração {i+1}/{max_iteracoes}")
        except Exception:
            pass

        # Gera conteúdo/comportamento do modelo com base no histórico atual
        response = model.generate_content(historico_mensagens)

        # Extrai o candidate principal (primeira opção) e suas partes.
        candidate = response.candidates[0]

        # Tenta extrair texto simples do response (acessador rápido do SDK)
        text_part = None
        try:
            text_part = response.text
        except Exception:
            # Monta texto a partir das partes do candidate quando não for simple text
            try:
                parts = candidate.content.parts
                texts = []
                for p in parts:
                    # Part pode conter um campo de texto ou outros tipos (function_call)
                    if hasattr(p, 'text') and p.text:
                        texts.append(p.text)
                if texts:
                    text_part = "\n".join(texts)
            except Exception:
                text_part = None

        # Se houver texto, anexa ao histórico para contexto; caso contrário, anexa
        # o objeto de conteúdo bruto para manter o formato que o SDK espera.
        try:
            if text_part:
                # Mantém formato consistente: mensagem com role e lista de parts
                historico_mensagens.append({"role": "model", "parts": [text_part]})
            else:
                historico_mensagens.append(candidate.content)
        except Exception:
            # fallback: append representação simples como role model
            historico_mensagens.append({"role": "model", "parts": [str(candidate)]})

        # Procura por uma function_call entre as parts do candidate
        function_call = None
        try:
            parts = candidate.content.parts
            for p in parts:
                fc = getattr(p, 'function_call', None)
                if fc:
                    function_call = fc
                    break
        except Exception:
            function_call = None

        if function_call:
            # Converte a função encontrada e extrai argumentos de forma robusta
            call = function_call
            nome_funcao = getattr(call, 'name', None)

            # parser genérico para argumentos que podem vir em formatos variados
            argumentos = {}
            try:
                # Alguns SDKs fornecem args como dicionário direto
                argumentos = dict(call.args)
            except Exception:
                # Estrutura protobuf-like: args.fields -> list of {key, value}
                try:
                    fields = getattr(call.args, 'fields', [])
                    for f in fields:
                        key = getattr(f, 'key', None) or getattr(f, 'name', None)
                        val_obj = getattr(f, 'value', None)
                        if val_obj is None:
                            continue
                        if hasattr(val_obj, 'string_value'):
                            val = val_obj.string_value
                        elif hasattr(val_obj, 'number_value'):
                            val = val_obj.number_value
                        elif hasattr(val_obj, 'bool_value'):
                            val = val_obj.bool_value
                        else:
                            # fallback: usar representação em string
                            try:
                                val = str(val_obj)
                            except Exception:
                                val = None
                        argumentos[key] = val
                except Exception:
                    argumentos = {}

            # Log de ação/diagnóstico — útil durante desenvolvimento
            print(f"[PENSAMENTO/AÇÃO]: O agente quer chamar '{nome_funcao}' com {argumentos}")

            # Executa a ferramenta se estiver disponível, capturando erros
            if nome_funcao in available_tools:
                try:
                    resultado_ferramenta = available_tools[nome_funcao](**argumentos)
                except Exception as e:
                    # Em produção, substituir por logging estruturado e tratamento adequado
                    resultado_ferramenta = f"Erro ao executar a ferramenta: {str(e)}"
            else:
                resultado_ferramenta = f"Ferramenta '{nome_funcao}' não encontrada."

            print(f"[OBSERVAÇÃO]: Retorno da ferramenta: {resultado_ferramenta}")
            # Informa o modelo sobre o resultado da ação. Repassamos como
            # 'user' para que o modelo entenda que é uma nova entrada do sistema.
            historico_mensagens.append({
                "role": "user",
                "parts": [f"Resultado da ferramenta '{nome_funcao}': {resultado_ferramenta}"]
            })

            # --- Fluxo automático como fallback ---
            # Se a ferramenta chamada foi `get_team_id` e retornou um team_id,
            # DEIXAMOS PARA O MODELO GERAR A PRÓXIMA CHAMADA.
            # O sistema anterior baseava em heurística falha: a extração do nome
            # catava falsos positivos como "SFC", "Club", etc. 
            pass

        else:
            # Quando não há função a ser chamada, tentamos retornar qualquer
            # texto extraído previamente (text_part). Se não houver texto, em
            # vez de encerrar imediatamente, permitimos que o loop continue
            # para dar ao modelo chance de produzir saída em iterações
            # subsequentes (útil quando o modelo usa apenas function calls
            # em passos intermediários).
            try:
                if text_part:
                    return text_part

                # Checa ratings de segurança que possam indicar bloqueio; se houver
                # sinalização, retornamos mensagem apropriada.
                safety = getattr(candidate, 'safety_ratings', None)
                if safety:
                    return "Resposta bloqueada por filtros de segurança do modelo."

                # Se chegar aqui repetidamente, algo está errado no contexto.
                # Em vez de apenas continue, forçamos o modelo a nos dar uma resposta.
                historico_mensagens.append({
                    "role": "user",
                    "parts": ["Você não retornou nenhum texto ou chamada de função na última resposta. Por favor, apresente o resultado final ao usuário de forma clara."]
                })
                # Não retornamos agora para dar chance ao loop numa próxima iteração.
                continue
            except Exception:
                return "Resposta do modelo indisponível (erro ao processar resposta)."

    # Caso o limite seja atingido, retorna mensagem amigável ao usuário
    return "Desculpe, o agente excedeu o limite máximo de interações para responder."


def perguntar_agente(pergunta: str, max_iteracoes: int = None) -> str:
    """Wrapper público simples para usar o agente no restante da aplicação.

    Mantém a API do módulo pequena e intencional: recebe uma pergunta e retorna
    a resposta do agente.
    """
    return executar_loop_react(pergunta, max_iteracoes)