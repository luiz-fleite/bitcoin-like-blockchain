# Documentação Técnica - Blockchain LSD

## Visão Geral

Sistema distribuído de criptomoeda simplificado (Bitcoin-like) implementado em Python para a disciplina de Laboratório de Sistemas Distribuídos - UFPA.

**Equipe:** Luiz Antonio, Max

---

## Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                              │
│                    (Interface CLI)                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                          Node                                │
│  - Servidor TCP (aceita conexões)                           │
│  - Gerencia peers                                           │
│  - Processa mensagens do protocolo                          │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Blockchain  │ │   Miner     │ │  Protocol   │ │Transaction  │
│             │ │             │ │             │ │   & Block   │
│ - Chain     │ │ - PoW       │ │ - Messages  │ │             │
│ - Validate  │ │ - Mining    │ │ - Serialize │ │ - Estrutura │
│ - Balance   │ │             │ │             │ │ - Hash      │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

---

## Módulos Implementados

### 1. `transaction.py` - Transações

**Classe:** `Transaction`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | str | UUID v4 único |
| `origem` | str | Endereço de origem |
| `destino` | str | Endereço de destino |
| `valor` | float | Quantidade transferida |
| `timestamp` | float | Unix epoch (segundos) |

**Validações:**
- ✅ Valor deve ser positivo (> 0)
- ✅ Origem e destino obrigatórios

**Métodos:**
- `to_dict()` - Serializa para JSON
- `from_dict()` - Deserializa de JSON

---

### 2. `block.py` - Blocos

**Classe:** `Block`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `index` | int | Posição na cadeia |
| `previous_hash` | str | Hash do bloco anterior (64 hex) |
| `transactions` | list | Lista de transações |
| `nonce` | int | Valor para Proof of Work |
| `timestamp` | float | Unix epoch (segundos) |
| `hash` | str | Hash SHA-256 do bloco (64 hex) |

**Métodos:**
- `calculate_hash()` - Calcula SHA-256 do bloco
- `create_genesis()` - Cria bloco gênesis padronizado
- `is_valid_hash(difficulty)` - Verifica se hash atende PoW
- `to_dict()` / `from_dict()` - Serialização JSON

**Bloco Gênesis:**
```python
index = 0
previous_hash = "0" * 64  # 64 zeros
transactions = []
nonce = 0
timestamp = 0  # Fixo para consistência entre nós
```

---

### 3. `blockchain.py` - Cadeia de Blocos

**Classe:** `Blockchain`

**Atributos:**
- `chain` - Lista de blocos
- `pending_transactions` - Pool de transações não mineradas
- `DIFFICULTY = "000"` - Prefixo exigido no hash

**Métodos principais:**

| Método | Descrição |
|--------|-----------|
| `get_balance(address)` | Calcula saldo de um endereço |
| `add_transaction(tx)` | Adiciona tx ao pool (com validação) |
| `add_block(block)` | Adiciona bloco à chain (com validação) |
| `is_valid_block(block)` | Valida um bloco individual |
| `is_valid_chain(chain)` | Valida toda a cadeia |
| `replace_chain(new_chain)` | Substitui por chain mais longa |

**Validações de Transação:**
- ✅ Não duplicada
- ✅ Saldo suficiente na origem (exceto "genesis"/"coinbase")

**Validações de Bloco:**
- ✅ Índice correto (sequencial)
- ✅ Hash anterior correto
- ✅ Proof of Work válido (inicia com "000")
- ✅ Hash calculado corretamente

---

### 4. `miner.py` - Mineração (Proof of Work)

**Classe:** `Miner`

**Algoritmo:**
```
1. Criar bloco candidato com transações pendentes
2. nonce = 0
3. Enquanto hash não começar com "000":
   - Calcular hash do bloco
   - nonce++
4. Retornar bloco minerado
```

**Métodos:**
- `mine_block(transactions, on_progress)` - Minera novo bloco
- `stop_mining()` - Interrompe mineração (quando outro nó encontra primeiro)

---

### 5. `protocol.py` - Protocolo de Comunicação

**Tipos de Mensagem (`MessageType`):**

| Tipo | Direção | Descrição |
|------|---------|-----------|
| `NEW_TRANSACTION` | Broadcast | Nova transação criada |
| `NEW_BLOCK` | Broadcast | Bloco minerado |
| `REQUEST_CHAIN` | Request | Solicita blockchain completa |
| `RESPONSE_CHAIN` | Response | Envia blockchain |
| `PING` | Request | Verifica conectividade |
| `PONG` | Response | Resposta ao ping |
| `DISCOVER_PEERS` | Request | Descobre novos nós |
| `PEERS_LIST` | Response | Lista de peers conhecidos |

**Formato da Mensagem:**
```json
{
  "type": "NEW_TRANSACTION",
  "payload": { ... },
  "sender": "host:port"
}
```

**Protocolo de Transmissão:**
```
[4 bytes: tamanho] [N bytes: JSON UTF-8]
```

---

### 6. `node.py` - Nó da Rede P2P

**Classe:** `Node`

**Responsabilidades:**
- Servidor TCP multi-thread (aceita conexões)
- Gerencia lista de peers
- Processa mensagens do protocolo
- Propaga transações e blocos

**Métodos principais:**

| Método | Descrição |
|--------|-----------|
| `start()` | Inicia servidor TCP |
| `stop()` | Para servidor e mineração |
| `connect_to_peer(address)` | Conecta a outro nó |
| `sync_blockchain()` | Baixa chain mais longa dos peers |
| `broadcast_transaction(tx)` | Propaga transação |
| `broadcast_block(block)` | Propaga bloco minerado |
| `mine()` | Inicia mineração |

**Fluxo de Mensagens:**

```
Nó A                          Nó B
  │                             │
  │──── NEW_TRANSACTION ───────▶│  (A cria transação)
  │                             │
  │◀─── NEW_BLOCK ─────────────│  (B minera bloco)
  │                             │
  │──── REQUEST_CHAIN ─────────▶│  (A quer sincronizar)
  │◀─── RESPONSE_CHAIN ────────│
  │                             │
```

---

### 7. `main.py` - Interface CLI

**Argumentos:**
```bash
--host       # Host do nó (default: localhost)
--port       # Porta do nó (default: 5000)
--bootstrap  # Lista de nós para conectar inicialmente
```

**Menu Interativo:**
1. Criar transação
2. Ver transações pendentes
3. Minerar bloco
4. Ver blockchain
5. Ver saldo
6. Ver peers conectados
7. Conectar a peer
8. Sincronizar blockchain
0. Sair

---

## Status de Implementação

### ✅ Semana 1 - Comunicação (COMPLETO)
- [x] Estrutura básica do nó
- [x] Comunicação via sockets TCP
- [x] Envio/recebimento de mensagens JSON

### ✅ Semana 2 - Blockchain (COMPLETO)
- [x] Estrutura de bloco
- [x] Blockchain local
- [x] Validação da cadeia

### ✅ Semana 3 - Transações (COMPLETO)
- [x] Estrutura de transação
- [x] Pool de transações pendentes
- [x] Propagação entre nós

### ✅ Semana 4 - Consenso (COMPLETO)
- [x] Proof of Work (dificuldade "000")
- [x] Criação e propagação de blocos
- [x] Aceitação de blocos remotos

### ⏳ Semana 5 - Sincronização (PARCIAL)
- [x] Entrada tardia na rede
- [x] Sincronização da blockchain
- [x] Resolução de conflitos (cadeia mais longa)
- [ ] Testes de robustez

### ⏳ Semana 6 - Finalização
- [ ] Testes de integração com outras equipes
- [ ] Relatório técnico
- [ ] Apresentação

---

## Testes

### Teste Unitário Rápido
```bash
uv run python -c "
from src.blockchain_lsd import Block, Blockchain, Transaction, Miner

bc = Blockchain()
tx = Transaction(origem='genesis', destino='luiz', valor=50)
bc.add_transaction(tx)

miner = Miner(bc, 'luiz')
block = miner.mine_block()
bc.add_block(block)

print(f'Saldo: {bc.get_balance(\"luiz\")}')
print(f'Chain válida: {bc.is_valid_chain()}')
"
```

### Teste Multi-Nó Local
```bash
# Terminal 1
uv run python main.py --port 5000

# Terminal 2
uv run python main.py --port 5001 --bootstrap localhost:5000

# Terminal 3
uv run python main.py --port 5002 --bootstrap localhost:5000
```

---

## Dependências

- Python >= 3.12
- Nenhuma dependência externa (apenas stdlib)
- Gerenciador de pacotes: `uv`
