import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FOOTBALL_API_KEY")
HEADERS = {"x-apisports-key": API_KEY}

def get_team_id(team_name: str):
    """
    Busca o ID de um time. Tenta encontrar a melhor correspondência.
    """
    # Remove hífens que costumam quebrar a busca da API-Football
    search_name = team_name.replace("-", " ")
    print(f"DEBUG: Tentando buscar time como: {search_name}")
    
    url = "https://v3.football.api-sports.io/teams"
    params = {"search": search_name}
    
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()

    # Se não achou nada, vamos imprimir o que a API respondeu pra você ver no terminal
    if not data.get('response'):
        print(f"DEBUG API DATA: {data}") # Aqui você vai ver se é erro de chave ou se é vazio mesmo
        return "Time não encontrado. Tente escrever o nome de outra forma (ex: Al Hilal em vez de Al-Hilal)."

    # Pega o primeiro resultado, mas imprime o nome real que a API encontrou
    team_data = data['response'][0]['team']
    print(f"DEBUG: Time encontrado na API: {team_data['name']} (ID: {team_data['id']})")
    
    return {"team_id": int(team_data['id']), "team_name": team_data['name']}

def get_player_id(player_name: str, team_id: int):
    """
    Busca o ID de um jogador usando o NOME do jogador e o ID do TIME (team_id).
    """
    # Garante que o ID seja inteiro para a URL da API
    team_id = int(float(team_id))
    
    print(f"DEBUG: Buscando jogador: {player_name} no time ID: {team_id}")
    url = "https://v3.football.api-sports.io/players"
    params = {
        "search": player_name,
        "team": team_id,
        "season": 2023 # Temporada base estável
    }
    
    response = requests.get(url, headers=HEADERS, params=params)
    data = response.json()

    if data.get('response'):
        p = data['response'][0]['player']
        return {"player_id": int(p['id']), "name": p['name']}
    return "Jogador não encontrado neste time específico."

def get_player_trophies(player_id: int):
    """
    Busca os títulos de um jogador usando o player_id (número inteiro).
    """
    player_id = int(float(player_id))
    url = f"https://v3.football.api-sports.io/trophies?player={player_id}"
    
    response = requests.get(url, headers=HEADERS)
    data = response.json()

    trophies = [f"{t['league']} ({t['place']})" for t in data.get('response', [])]
    return ", ".join(trophies) if trophies else "Nenhum título encontrado."

def get_player_stats(player_id: int, season: int = 2023):
    """
    Busca gols e assistências de um jogador por player_id e temporada (season).
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