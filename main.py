"""
CLI simples para interagir com o agente de dados futebolísticos.

Este módulo fornece uma interface em linha de comando minimalista que lê
perguntas do usuário e encaminha para `perguntar_agente` do módulo `agent`.
Use para testes manuais ou demonstrações locais antes de integrar a outros
front-ends.
"""

from agent import perguntar_agente


def iniciar_chat() -> None:
    """
    Loop interativo que recebe perguntas do usuário e exibe respostas.

    Instruções de uso (simples):
    - Execute o script e digite perguntas sobre jogadores/times.
    - Digite 'sair' (ou 'exit'/'quit') para encerrar o programa.
    """
    print("Agente de Dados Futebolísticos Ativo")
    print("Digite 'sair' para encerrar.\n")

    while True:
        pergunta = input("Você: ")

        if pergunta.lower() in ["sair", "exit", "quit"]:
            # Encerramento limpo do loop principal
            break

        try:
            # Encaminha a pergunta ao agente e imprime a resposta
            resposta = perguntar_agente(pergunta)
            print(f"\nAgente: {resposta}\n")
        except Exception as e:
            # Em desenvolvimento, é útil ver o erro. Em produção, trocar por logging.
            print(f"\n[Erro do Sistema]: {e}\n")


if __name__ == "__main__":
    iniciar_chat()