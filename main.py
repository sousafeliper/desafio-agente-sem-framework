from agent import perguntar_agente

def iniciar_chat():
    print("Agente de Dados Futebolísticos Ativo")
    print("Digite 'sair' para encerrar.\n")

    while True:
        pergunta = input("Você: ")

        if pergunta.lower() in ["sair", "exit", "quit"]:
            break

        try:
            resposta = perguntar_agente(pergunta)
            print(f"\nAgente: {resposta}\n")
        except Exception as e:
            print(f"\n[Erro do Sistema]: {e}\n")

if __name__ == "__main__":
    iniciar_chat()