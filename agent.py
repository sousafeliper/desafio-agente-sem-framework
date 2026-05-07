import google.generativeai as genai
import os
from dotenv import load_dotenv
from tools import get_team_id, get_player_id, get_player_trophies, get_player_stats

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

tools_list = [get_team_id, get_player_id, get_player_trophies, get_player_stats]

model = genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite-preview', 
    tools=tools_list,
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

# Chat com execução automática de funções
chat = model.start_chat(enable_automatic_function_calling=True)

def perguntar_agente(pergunta):
    response = chat.send_message(pergunta)
    return response.text