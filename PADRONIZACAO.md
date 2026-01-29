# Checklist de Padronização - Blockchain LSD

Este documento lista **TUDO** que as equipes precisam acordar juntas para que os nós de diferentes grupos possam se comunicar na rede distribuída.

---

## 🔴 CRÍTICO - Sem acordo = sistema não funciona

### 1. Porta Padrão da Rede
- [ ] Definir porta única para todos os nós (ex: `5000`, `8333`, `9000`)
- [ ] Ou definir range de portas permitidas (ex: `5000-5100`)

### 2. Formato das Mensagens JSON
Todas as equipes devem usar **exatamente** a mesma estrutura:

```json
{
  "type": "TIPO_DA_MENSAGEM",
  "payload": { ... },
  "sender": "host:port"
}
```

- [ ] Confirmar campos obrigatórios
- [ ] Confirmar encoding: UTF-8
- [ ] Confirmar delimitador de mensagem (tamanho em 4 bytes no início? newline? outro?)

### 3. Tipos de Mensagem (MessageType)
- [ ] `NEW_TRANSACTION` - nova transação
- [ ] `NEW_BLOCK` - bloco minerado
- [ ] `REQUEST_CHAIN` - solicitar blockchain
- [ ] `RESPONSE_CHAIN` - resposta com blockchain
- [ ] Outros tipos necessários? (PING/PONG, DISCOVER_PEERS, etc.)

### 4. Estrutura da Transação
```json
{
  "id": "uuid-string",
  "origem": "string",
  "destino": "string",
  "valor": 123.45,
  "timestamp": 1234567890.123
}
```
- [ ] Formato do ID (UUID v4?)
- [ ] Formato do timestamp (Unix epoch em segundos? milissegundos?)
- [ ] Tipo do valor (float? int? string?)
- [ ] Campos adicionais?

### 5. Estrutura do Bloco
```json
{
  "index": 0,
  "previous_hash": "64 caracteres hex",
  "transactions": [...],
  "nonce": 12345,
  "timestamp": 1234567890.123,
  "hash": "64 caracteres hex"
}
```
- [ ] Ordem dos campos para cálculo do hash
- [ ] Formato do timestamp
- [ ] Incluir ou não o campo `hash` no cálculo do hash

### 6. Bloco Gênesis
**TODAS as equipes devem ter o MESMO bloco gênesis!**

- [ ] Index: `0`
- [ ] Previous hash: `"0000000000000000000000000000000000000000000000000000000000000000"` (64 zeros)
- [ ] Transactions: `[]` (lista vazia)
- [ ] Nonce: `0`
- [ ] Timestamp: `0` (ou data fixa acordada)
- [ ] **Hash resultante:** `_________________` (calcular juntos!)

### 7. Algoritmo de Hash
- [ ] SHA-256 (confirmado no enunciado)
- [ ] Ordem dos campos no JSON antes do hash
- [ ] `sort_keys=True` no JSON? (importante para consistência!)

### 8. Dificuldade do Proof of Work
- [ ] Prefixo: `"000"` (confirmado no enunciado)
- [ ] Dificuldade fixa (não muda)

---

## 🟡 IMPORTANTE - Afeta interoperabilidade

### 9. Protocolo de Comunicação
- [ ] TCP (recomendado) ou UDP?
- [ ] Conexão persistente ou nova conexão por mensagem?
- [ ] Timeout para conexões (sugestão: 10 segundos)
- [ ] Tamanho máximo de mensagem

### 10. Descoberta de Nós
- [ ] Lista inicial de bootstrap nodes (IPs/portas do lab)
- [ ] Mecanismo de descoberta de novos peers
- [ ] Formato da mensagem DISCOVER_PEERS / PEERS_LIST

### 11. Sincronização
- [ ] Quando solicitar REQUEST_CHAIN? (ao entrar na rede? periodicamente?)
- [ ] Critério para aceitar nova chain (mais longa E válida)

### 12. Validação de Transações
- [ ] Não permitir valor negativo ou zero
- [ ] Não permitir saldo negativo
- [ ] Como tratar transações duplicadas?
- [ ] Origem especial "genesis" ou "coinbase" para criar moedas iniciais?

### 13. Propagação
- [ ] Propagar transação para todos os peers conhecidos?
- [ ] Propagar bloco para todos os peers conhecidos?
- [ ] Evitar loops de propagação (não reenviar para quem enviou)

---

## 🟢 RECOMENDADO - Facilita testes

### 14. Endereços/Carteiras
- [ ] Formato dos endereços (nomes simples? hashes? chaves públicas?)
- [ ] Sugestão simples: usar nomes como "alice", "bob", "luiz", "max"

### 15. Saldo Inicial
- [ ] Criar transações iniciais no gênesis?
- [ ] Ou usar origem especial "coinbase" para dar moedas?

### 16. Logs
- [ ] Formato padronizado de logs para debug conjunto
- [ ] Nível de log (INFO, DEBUG)

---

## 📝 Template de Acordo

```
ACORDO DE PADRONIZAÇÃO - BLOCKCHAIN LSD 2025
Data: ___/___/______
Equipes presentes: ________________________

1. Porta padrão: _______
2. Bloco gênesis hash: ________________________________
3. Prefixo de dificuldade: "000"
4. Timestamp: Unix epoch em segundos (float)
5. Delimitador de mensagem: 4 bytes big-endian com tamanho
6. Bootstrap nodes:
   - _______________:_____
   - _______________:_____
   - _______________:_____

Assinaturas:
_______________ (Equipe 1)
_______________ (Equipe 2)
_______________ (Equipe 3)
...
```

---

## ⚠️ DICA IMPORTANTE

Antes da apresentação final, façam um **teste de integração**:
1. Cada equipe sobe seu nó em uma máquina diferente
2. Conectam todos na mesma rede
3. Uma equipe cria uma transação
4. Verificam se TODOS os nós receberam
5. Uma equipe minera o bloco
6. Verificam se TODOS os nós aceitaram o mesmo bloco
