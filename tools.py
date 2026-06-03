"""
Ferramentas utilitárias que encapsulam chamadas à API-Football.

Este módulo contém funções pequenas e testáveis que consultam a API
externa para obter IDs de times, IDs de jogadores, títulos e estatísticas.
As funções retornam estruturas simples (dicts ou strings) fáceis de serializar
ou passar para o agente.

Observações de implementação:
- A chave da API é lida via `FOOTBALL_API_KEY` no ambiente (.env compatível).
- Funções levantam poucos erros explicitamente; em casos de falha a função
  normalmente retorna uma mensagem amigável. Em cenários de produção, refatorar
  para lançar exceções específicas ou retornar objetos Result.
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Configuração de cabeçalhos para a API-Football; depende de FOOTBALL_API_KEY
API_KEY = os.getenv("FOOTBALL_API_KEY")
HEADERS = {"x-apisports-key": API_KEY}
MEMORY_FILE = "memory.json"


def load_memory():
    """Carrega o cache local de times e jogadores em JSON."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("teams", {})
                    data.setdefault("players", {})
                    return data
        except Exception:
            pass
    return {"teams": {}, "players": {}}


def save_memory(memory_data):
    """Salva o cache local em JSON com indentação para leitura humana."""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory_data, f, ensure_ascii=False, indent=4)


def get_team_id(team_name: str):
    """
    Busca o ID de um time pela API.

    A função tenta uma correspondência por nome e retorna um dict com o ID e
    o nome canônico encontrado pela API. Em caso de resposta vazia, retorna
    uma mensagem de erro legível para o terminal/usuário.
    """
    memory = load_memory()
    # Remove hífens que costumam quebrar a busca da API-Football
    search_name = team_name.replace("-", " ")
    cache_key = search_name.lower().strip()

    # Verifica cache local antes de chamar API
    if cache_key in memory["teams"]:
        print("[MEMÓRIA] Time carregado do arquivo local!")
        return memory["teams"][cache_key]

    print(f"DEBUG: Tentando buscar time como: {search_name}")

    # Ajustes cruciais para a API-Sports: se buscar 'Al Hilal', ela pode retornar um time aleatório
    # com parte do nome (ex: Al Hilal Kadougli). O parâmetro 'search' da API faz um fuzzy match estranho.
    # Vamos buscar todos que combinam e tentar encontrar o país ou nome exato esperado.
    url = "https://v3.football.api-sports.io/teams"
    params = {"search": search_name}

    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()

    if not data.get('response'):
        print(f"DEBUG API DATA: {data}")
        return "Time não encontrado. Tente escrever o nome de outra forma (ex: Al Hilal em vez de Al-Hilal)."

    # Se procurou Al Hilal/Saudi, vamos iterar pra não pegar o do Sudão (Kadougli)
    responses = data['response']
    best_match = responses[0]['team']  # default first
    
    search_lower = search_name.lower()
    if 'hilal' in search_lower:
        for r in responses:
            team_info = r['team']
            country = team_info.get('country', '').lower()
            if 'saudi' in country or 'arábia' in country:
                best_match = team_info
                break

    print("[API] Buscando time na API-Football...")
    print(f"DEBUG: Time encontrado na API: {best_match['name']} (ID: {best_match['id']})")
    result = {"team_id": int(best_match['id']), "team_name": best_match['name']}

    # Persiste no cache local
    memory["teams"][cache_key] = result
    save_memory(memory)

    return result


def get_player_id(player_name: str, team_id: int = None):
    """
    Busca o ID de um jogador usando o nome do jogador e o ID do time.

    Retorna um dict com `player_id` e `name` quando encontrado, ou uma string
    informando que o jogador não foi localizado neste time.
    """
    memory = load_memory()
    normalized_player = player_name.lower().strip()
    normalized_team = "global" if team_id is None else str(team_id).strip()
    player_cache_key = f"{normalized_player}|{normalized_team}"

    # Verifica cache local antes de chamar API
    if player_cache_key in memory["players"]:
        print("[MEMÓRIA] Jogador carregado do arquivo local!")
        return memory["players"][player_cache_key]

    # Se forneceram team_id, inclui no filtro. Caso contrário, busca global.
    url = "https://v3.football.api-sports.io/players"
    params = {"search": player_name, "season": 2023}

    if team_id is not None:
        try:
            params["team"] = int(float(team_id))
            print(f"DEBUG: Buscando jogador: {player_name} no time ID: {params['team']}")
        except Exception:
            print(f"DEBUG: team_id inválido recebido: {team_id}; fazendo busca global para {player_name}")
    else:
        print(f"DEBUG: Buscando jogador globalmente: {player_name}")

    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()

    if data.get('response'):
        p = data['response'][0]['player']
        result = {"player_id": int(p['id']), "name": p['name']}
        memory["players"][player_cache_key] = result
        save_memory(memory)
        return result
    return "Jogador não encontrado neste time específico."


def get_player_trophies(player_id: int):
    """
    Retorna os títulos associados a um jogador (lista como string).

    Converte `player_id` para inteiro e consulta o endpoint de troféus. O
    formato retornado é uma string human-readable, adequada para exibição.
    """
    player_id = int(float(player_id))
    url = f"https://v3.football.api-sports.io/trophies?player={player_id}"

    response = requests.get(url, headers=HEADERS)
    data = response.json()

    trophies = [f"{t['league']} ({t['place']})" for t in data.get('response', [])]
    return ", ".join(trophies) if trophies else "Nenhum título encontrado."


def get_player_stats(player_id: int, season: int = 2023):
    """
    Coleta estatísticas básicas (gols e assistências) por jogador e temporada.

    Retorna um dict com `temporada`, `gols`, `assistencias` e `clube`, ou uma
    mensagem indicando que não foi possível encontrar os dados.
    """
    player_id = int(float(player_id))
    season = int(float(season))

    url = "https://v3.football.api-sports.io/players"
    params = {"id": player_id, "season": season}

    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()

    if data.get('response'):
        stats = data['response'][0]['statistics']
        gols = sum(s['goals']['total'] or 0 for s in stats)
        assists = sum(s['goals']['assists'] or 0 for s in stats)
        time = stats[0]['team']['name']

        return {
            "temporada": season,
            "gols": gols,
            "assistencias": assists,
            "clube": time
        }
    return f"Estatísticas não encontradas para a temporada {season}."