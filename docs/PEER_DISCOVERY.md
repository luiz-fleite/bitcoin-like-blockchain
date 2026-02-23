# Descoberta Automática de Peers (Opcional)

**Proposta por:** Luiz Antonio, Max  
**Data:** 23/02/2026  
**Status:** Opcional — não é obrigatório pelo padrão, mas acelera MUITO a apresentação

---

## O Problema

Na apresentação, teremos **várias equipes** conectando seus nós ao mesmo tempo. Sem descoberta automática de peers, cada nó precisaria digitar manualmente o IP:Porta de **todos os outros nós** da sala. Com 4+ equipes rodando múltiplos nós, isso vira um caos.

## A Solução

Implementar **3 mensagens extras** no protocolo que permitem que os nós se descubram automaticamente. Assim, basta conectar ao **1 nó bootstrap** e o seu nó descobre todos os outros sozinho.

---

## Mensagens Extras (3 tipos)

Todas seguem o **mesmo formato** do padrão já existente:

```
[4 bytes: tamanho big-endian] [JSON UTF-8]
```

### 1. `PING` — "Oi, eu existo!"

**Enviada por:** Quem quer se anunciar na rede.

```json
{
  "type": "PING",
  "payload": {},
  "sender": "192.168.1.10:5000"
}
```

**Resposta esperada:** `PONG`

```json
{
  "type": "PONG",
  "payload": {},
  "sender": "192.168.1.20:5000"
}
```

**O que fazer ao receber um `PING`:**
1. Ler o campo `sender` da mensagem.
2. Adicionar esse endereço na sua lista de peers (se ainda não estiver lá).
3. Responder com `PONG`.

**Pseudocódigo:**
```python
if message.type == "PING":
    if message.sender not in meus_peers:
        meus_peers.add(message.sender)
    responder({"type": "PONG", "payload": {}, "sender": meu_endereco})
```

---

### 2. `DISCOVER_PEERS` — "Quem você conhece?"

**Enviada por:** Quem acabou de entrar na rede e quer saber quem mais existe.

```json
{
  "type": "DISCOVER_PEERS",
  "payload": {},
  "sender": "192.168.1.10:5000"
}
```

**Resposta esperada:** `PEERS_LIST`

```json
{
  "type": "PEERS_LIST",
  "payload": {
    "peers": ["192.168.1.20:5000", "192.168.1.30:5000", "192.168.1.40:5001"]
  },
  "sender": "192.168.1.20:5000"
}
```

**O que fazer ao receber um `DISCOVER_PEERS`:**
1. Responder com a sua lista de peers conhecidos.

**O que fazer ao receber um `PEERS_LIST`:**
1. Pegar a lista de peers da resposta.
2. Remover o seu próprio endereço (para não se adicionar a si mesmo).
3. Para cada peer novo que você não conhecia, adicionar na sua lista.
4. **Importante:** Enviar um `PING` para cada peer novo, para que ele também te conheça.

**Pseudocódigo:**
```python
if message.type == "DISCOVER_PEERS":
    responder({
        "type": "PEERS_LIST",
        "payload": {"peers": list(meus_peers)},
        "sender": meu_endereco
    })

if message.type == "PEERS_LIST":
    novos = message.payload["peers"] - meus_peers - {meu_endereco}
    for peer in novos:
        meus_peers.add(peer)
        enviar(peer, {"type": "PING", "payload": {}, "sender": meu_endereco})
```

---

## Fluxo Completo (Exemplo Visual)

Imagine 3 nós: **A** (já na rede), **B** (já na rede, conectado ao A), e **C** (acabou de entrar).

```
C entra na rede e conhece apenas A (bootstrap)
│
├─► C envia PING para A
│   └─► A registra C como peer, responde PONG
│
├─► C envia DISCOVER_PEERS para A
│   └─► A responde PEERS_LIST: ["B"]
│
├─► C adiciona B na sua lista
│   └─► C envia PING para B
│       └─► B registra C como peer, responde PONG
│
└─► Resultado: A↔B↔C (todos se conhecem!)
```

**Sem essa funcionalidade**, o nó B nunca saberia que C existe até que alguém digitasse manualmente.

---

## Como Implementar (Mínimo Necessário)

Você precisa fazer **apenas 2 coisas** no seu código:

### 1. Tratar as mensagens recebidas

No seu handler de mensagens (onde você já trata `NEW_TRANSACTION`, `NEW_BLOCK`, etc.), adicione:

```python
# Ao receber PING → registrar peer + responder PONG
if tipo == "PING":
    peers.add(mensagem["sender"])
    responder({"type": "PONG", "payload": {}, "sender": meu_ip})

# Ao receber DISCOVER_PEERS → responder com lista de peers
elif tipo == "DISCOVER_PEERS":
    responder({"type": "PEERS_LIST", "payload": {"peers": list(peers)}, "sender": meu_ip})

# Ao receber PEERS_LIST → adicionar peers novos + pingar eles
elif tipo == "PEERS_LIST":
    for peer in mensagem["payload"]["peers"]:
        if peer != meu_ip and peer not in peers:
            peers.add(peer)
            enviar(peer, {"type": "PING", "payload": {}, "sender": meu_ip})
```

### 2. Ao conectar a um nó bootstrap

Depois de conectar com sucesso ao nó bootstrap, faça:

```python
# 1. Envia PING para o bootstrap (ele te registra)
enviar(bootstrap, {"type": "PING", "payload": {}, "sender": meu_ip})

# 2. Pergunta quem ele conhece
resposta = enviar(bootstrap, {"type": "DISCOVER_PEERS", "payload": {}, "sender": meu_ip})

# 3. Para cada peer novo, envia PING
for peer in resposta["payload"]["peers"]:
    if peer != meu_ip:
        peers.add(peer)
        enviar(peer, {"type": "PING", "payload": {}, "sender": meu_ip})
```

---

## ⚠️ Importante

- **Isso NÃO quebra a compatibilidade** com quem não implementou. Se o outro nó não entender `PING`, ele simplesmente ignora (ou dá erro silencioso no lado dele). As mensagens obrigatórias (`NEW_TRANSACTION`, `NEW_BLOCK`, `REQUEST_CHAIN`, `RESPONSE_CHAIN`) continuam funcionando normalmente.
- **Mensagens não-obrigatórias devem ser tratadas com `try/except`** (ou equivalente) para não crashar se o outro nó não responder como esperado.
- O campo `sender` é sempre `"host:port"` (ex: `"192.168.1.10:5000"`).

---

## Checklist Rápido

- [ ] Ao receber `PING` → adicionar `sender` nos peers + responder `PONG`
- [ ] Ao receber `DISCOVER_PEERS` → responder `PEERS_LIST` com lista de peers
- [ ] Ao receber `PEERS_LIST` → adicionar peers novos + enviar `PING` para cada um
- [ ] Ao conectar no bootstrap → enviar `PING` + `DISCOVER_PEERS`
- [ ] Tratar erros com `try/except` para não crashar com nós que não suportam

---

## Snippet Python (Copiar e Colar)

Código funcional usando sockets TCP puros. Adapte `send_message` e `meu_endereco` para a sua implementação.

```python
import socket
import json

meu_endereco = "192.168.1.10:5000"  # trocar pelo seu host:port
peers = set()

def send_message(peer_address: str, msg: dict) -> dict | None:
    """Envia uma mensagem JSON para um peer e retorna a resposta (ou None)."""
    host, port = peer_address.split(":")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect((host, int(port)))
            data = json.dumps(msg).encode()
            sock.sendall(len(data).to_bytes(4, "big") + data)
            # Lê resposta
            length_data = sock.recv(4)
            if not length_data:
                return None
            length = int.from_bytes(length_data, "big")
            raw = b""
            while len(raw) < length:
                chunk = sock.recv(min(65536, length - len(raw)))
                if not chunk:
                    break
                raw += chunk
            return json.loads(raw.decode()) if raw else None
    except Exception:
        return None


def handle_peer_discovery(message: dict) -> dict | None:
    """
    Adicione esta função no seu handler de mensagens (onde já trata NEW_BLOCK etc).
    Retorna a resposta que deve ser enviada de volta, ou None.
    """
    tipo = message.get("type", "")
    sender = message.get("sender", "")

    if tipo == "PING":
        if sender and sender != meu_endereco:
            peers.add(sender)
        return {"type": "PONG", "payload": {}, "sender": meu_endereco}

    elif tipo == "DISCOVER_PEERS":
        return {"type": "PEERS_LIST", "payload": {"peers": list(peers)}, "sender": meu_endereco}

    elif tipo == "PEERS_LIST":
        for peer in message.get("payload", {}).get("peers", []):
            if peer != meu_endereco and peer not in peers:
                peers.add(peer)
                send_message(peer, {"type": "PING", "payload": {}, "sender": meu_endereco})
        return None

    return None  # tipo desconhecido, ignorar


def connect_to_bootstrap(bootstrap: str):
    """Chame após conectar ao bootstrap para descobrir a rede toda."""
    # 1. Pinga o bootstrap (ele te registra)
    send_message(bootstrap, {"type": "PING", "payload": {}, "sender": meu_endereco})
    peers.add(bootstrap)

    # 2. Pergunta quem ele conhece
    resp = send_message(bootstrap, {"type": "DISCOVER_PEERS", "payload": {}, "sender": meu_endereco})
    if resp and resp.get("type") == "PEERS_LIST":
        for peer in resp["payload"].get("peers", []):
            if peer != meu_endereco and peer not in peers:
                peers.add(peer)
                send_message(peer, {"type": "PING", "payload": {}, "sender": meu_endereco})

    print(f"Peers descobertos: {peers}")
```
