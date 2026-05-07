⚽ Agente de Dados Futebolísticos (Zero-Framework)
Este projeto foi desenvolvido para o Desafio de Nivelamento, com o objetivo de implementar um agente de IA funcional em Python, sem o uso de frameworks prontos (como LangChain ou CrewAI), utilizando o Gemini 3.1 Flash Lite e a API-Football.

🧠 O Que o Agente Faz
O agente atua como um analista de futebol avançado. Ele não apenas busca dados, mas raciocina sobre as limitações das ferramentas para entregar a melhor resposta possível. Ele é capaz de:

Identificar IDs de clubes e jogadores para consultas precisas.

Extrair estatísticas de desempenho (gols/assistências) por temporada.

Listar o histórico de títulos (troféus) de atletas.

🛠️ Arquitetura e Ferramentas
A arquitetura foi baseada no Function Calling nativo do Google Gemini. O fluxo de raciocínio é dinâmico: o modelo decide qual ferramenta chamar com base no retorno da anterior.

Ferramentas (Python Functions):
get_team_id: Busca o ID único de um clube (parâmetro obrigatório para filtros de busca).

get_player_id: Localiza o identificador do jogador cruzando o nome com o ID do time.

get_player_stats: Extrai os dados numéricos de performance de uma temporada específica.

get_player_trophies: Recupera o histórico de conquistas do atleta.

🚀 Como Rodar o Projeto
Dependências:

Bash
pip install google-generativeai requests python-dotenv
Configuração:
Crie um arquivo .env na raiz com suas chaves:

Plaintext
GEMINI_API_KEY=sua_chave_aqui
FOOTBALL_API_KEY=sua_chave_aqui
Execução:

Bash
python main.py
📈 Desafios e Aprendizados
O desenvolvimento deste agente foi um exercício intenso de resolução de problemas reais de integração.

1. O Problema da Ambiguidade de Dados
A maior dificuldade encontrada foi a rigidez da API de futebol. Buscas simples por "Al-Hilal" ou "Neymar" retornavam resultados inesperados (como times homônimos de ligas menores).

Solução: Implementei uma lógica de encadeamento de dependências. O agente aprendeu que não pode buscar um jogador sem antes confirmar o ID exato do time, reduzindo drasticamente as alucinações.

2. Resiliência e Autonomia (Auto-Healing)
Durante os testes, a API falhou em retornar o Neymar no Al-Hilal por questões de registro na base de dados.

Aprendizado: O agente demonstrou autonomia ao "raciocinar" que, se o jogador não estava no time atual, ele poderia ser encontrado em clubes anteriores (como o PSG). Isso validou a escolha da arquitetura de agentes em vez de scripts lineares de "if/else".

3. Tratamento de Tipos em APIs REST
Lidar com retornos que oscilavam entre float e int nos IDs causou erros de execução. Refinei as ferramentas para garantir o casting correto dos dados antes de qualquer interpolação de strings em URLs.
