# Blockchain LSD - Criptomoeda Distribuída Simplificada

Implementação de um sistema distribuído de criptomoeda inspirado no Bitcoin para a disciplina de Laboratório de Sistemas Distribuídos (UFPA).

## 👥 Equipe

- **Luiz Antonio**
- **Max**

## 🎯 Objetivo

Sistema distribuído onde cada nó mantém uma cópia local da blockchain, comunicando-se via sockets com serialização JSON e utilizando Proof of Work simplificado.

## 🏗️ Estrutura do Projeto

```
blockchain-lsd/
├── src/
│   └── blockchain_lsd/
│       ├── __init__.py
│       ├── block.py         # Estrutura do bloco
│       ├── blockchain.py    # Gerenciamento da cadeia
│       ├── transaction.py   # Transações
│       ├── node.py          # Nó da rede P2P
│       ├── miner.py         # Proof of Work
│       └── protocol.py      # Protocolo de comunicação
├── main.py                  # Ponto de entrada
├── pyproject.toml
└── README.md
```

## 🚀 Instalação

```bash
# Instalar dependências
uv sync

# Executar nó
uv run python main.py --port 5000 --bootstrap localhost:5001
```

## 📡 Protocolo de Mensagens

| Tipo | Descrição |
|------|-----------|
| `NEW_TRANSACTION` | Nova transação |
| `NEW_BLOCK` | Bloco minerado |
| `REQUEST_CHAIN` | Solicita blockchain |
| `RESPONSE_CHAIN` | Resposta com blockchain |

## ⚙️ Requisitos

- Proof of Work: hash iniciando com `000`
- Comunicação: sockets TCP + JSON
- Hash: SHA-256