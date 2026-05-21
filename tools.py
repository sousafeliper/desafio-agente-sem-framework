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
import os
from dotenv import load_dotenv

load_dotenv()

# Configuração de cabeçalhos para a API-Football; depende de FOOTBALL_API_KEY
API_KEY = os.getenv("FOOTBALL_API_KEY")
HEADERS = {"x-apisports-key": API_KEY}


def get_team_id(team_name: str):
    """
    Busca o ID de um time pela API.

    A função tenta uma correspondência por nome e retorna um dict com o ID e
    o nome canônico encontrado pela API. Em caso de resposta vazia, retorna
    uma mensagem de erro legível para o terminal/usuário.
    """
    # Remove hífens que costumam quebrar a busca da API-Football
    search_name = team_name.replace("-", " ")
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

    print(f"DEBUG: Time encontrado na API: {best_match['name']} (ID: {best_match['id']})")
    return {"team_id": int(best_match['id']), "team_name": best_match['name']}


def get_player_id(player_name: str, team_id: int = None):
    """
    Busca o ID de um jogador usando o nome do jogador e o ID do time.

    Retorna um dict com `player_id` e `name` quando encontrado, ou uma string
    informando que o jogador não foi localizado neste time.
    """
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
        return {"player_id": int(p['id']), "name": p['name']}
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