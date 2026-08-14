## Agente de Dados Futebolísticos (Zero-Framework)
Este projeto foi desenvolvido para o Desafio de Nivelamento, com o objetivo de implementar um agente de IA funcional em Python, sem o uso de frameworks prontos (como LangChain ou CrewAI), utilizando o Gemini 3.1 Flash Lite e a API-Football.

## O Que o Agente Faz
O agente atua como um analista de futebol avançado. Ele não apenas busca dados, mas raciocina sobre as limitações das ferramentas para entregar a melhor resposta possível. Ele é capaz de:

Identificar IDs de clubes e jogadores para consultas precisas.

Extrair estatísticas de desempenho (gols/assistências) por temporada.

Listar o histórico de títulos (troféus) de atletas.

## Arquitetura e Ferramentas
A arquitetura usa o SDK atual `google.genai` com um loop ReAct manual. O modelo raciocina em texto, o script intercepta a ação solicitada e executa a ferramenta correspondente, sem depender do pacote legado `google.generativeai`.

Ferramentas (Python Functions):
get_team_id: Busca o ID único de um clube (parâmetro obrigatório para filtros de busca).

get_player_id: Localiza o identificador do jogador cruzando o nome com o ID do time.

get_player_stats: Extrai os dados numéricos de performance de uma temporada específica.

get_player_trophies: Recupera o histórico de conquistas do atleta.

## Implementação Manual do Loop ReAct
Conforme os novos requisitos, o mecanismo automático de chamadas de função do SDK do Gemini foi desativado. Agora, controlamos explicitamente o ciclo no arquivo `agent.py`:

1. **User Prompt**: O usuário faz uma pergunta no terminal ([main.py](main.py)).
2. **Thought (Pensamento)**: O Gemini avalia o histórico e determina se precisa coletar dados externos ou se já pode responder.
3. **Action (Ação)**: Caso precise de dados, o modelo emite uma requisição estruturada indicando qual ferramenta usar. O script intercepta essa requisição e executa a função correspondente em [tools.py](tools.py).
4. **Observation (Observação)**: O resultado retornado pela API-Football é encapsulado e injetado de volta no histórico de mensagens do modelo.
5. **Loop**: Esse processo se repete até que o modelo decida que possui dados suficientes para formular a resposta final.

## Como Rodar o Projeto
Dependências:

Bash
pip install google-genai requests python-dotenv
Configuração:
Crie um arquivo .env na raiz com suas chaves:

Plaintext
GEMINI_API_KEY=sua_chave_aqui
FOOTBALL_API_KEY=sua_chave_aqui
Execução:

Bash
python main.py

## Desafios e Aprendizados
O desenvolvimento deste agente foi um exercício intenso de resolução de problemas reais de integração.

1. O Problema da Ambiguidade de Dados
A maior dificuldade encontrada foi a rigidez da API de futebol. Buscas simples por "Al-Hilal" ou "Neymar" retornavam resultados inesperados (como times homônimos de ligas menores).

Solução: Implementei uma lógica de encadeamento de dependências. O agente aprendeu que não pode buscar um jogador sem antes confirmar o ID exato do time, reduzindo drasticamente as alucinações.

2. Resiliência e Autonomia (Auto-Healing)
Durante os testes, a API falhou em retornar o Neymar no Al-Hilal por questões de registro na base de dados.

Aprendizado: O agente demonstrou autonomia ao "raciocinar" que, se o jogador não estava no time atual, ele poderia ser encontrado em clubes anteriores (como o PSG). Isso validou a escolha da arquitetura de agentes em vez de scripts lineares de "if/else".

3. Tratamento de Tipos em APIs REST
Lidar com retornos que oscilavam entre float e int nos IDs causou erros de execução. Refinei as ferramentas para garantir o casting correto dos dados antes de qualquer interpolação de strings em URLs.

4. Estabilidade do Loop ReAct e Lidar com Limitações do SDK
Durante a evolução, o parsing das estruturas de resposta (como `function_calls` vs `Candidate.parts`) causou crashes, além da interrupção prematura do modelo por limite de iterações do loop.

Solução implementada:
- Aumentamos e tornamos o `MAX_REACT_ITERATIONS` configurável via variáveis de ambiente, prevenindo cortes antecipados na linha de pensamento do agente. Adicionamos rastreio via console (logs `[DEBUG] Iteração X/Y`) para facilitar debug.
- Tornamos o wrapper que interage com o SDK do Gemini super-resiliente a falhas de parsing (extratificando argumentos com iteradores no protobuffer) e forçamos a devolutiva do resultado de ações como `"user"` prompt para manter o modelo ativado no processo.

5. Correspondência Confusa de Buscas na API-Football (Fuzzy Match)
Para equipes de nomes longos e compostos (como o Al Hilal), o "search" da API trazia retornos duvidosos pela confusão de "Fuzzy Matching" da plataforma (ex: "Al Hilal Kadougli" do Sudão no lugar do Saudi).

Solução: Aplicamos um filtro estrito direto na ferramenta de `get_team_id` em Python, percorrendo o JSON das respostas identificando chaves de países (ex: `Saudi` ou `Arábia`) dentro do dicionário retornado, garantindo que o agente manipule somente IDs de contexto correto e continue o fluxo de forma exata rumo à pesquisa final do jogador.
