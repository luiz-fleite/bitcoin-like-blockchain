"""
Módulo de Protocolo de Comunicação
"""

import json
from enum import Enum
from dataclasses import dataclass
from typing import Any


class MessageType(Enum):
    """
    Tipos de mensagens do protocolo.
    
    - NEW_TRANSACTION: envio de uma nova transação
    - NEW_BLOCK: envio de um bloco minerado
    - REQUEST_CHAIN: solicitação da blockchain completa
    - RESPONSE_CHAIN: envio da blockchain para sincronização
    - PING: verificação de conectividade
    - PONG: resposta ao ping
    - DISCOVER_PEERS: descoberta de novos nós
    - PEERS_LIST: lista de peers conhecidos
    """
    NEW_TRANSACTION = "NEW_TRANSACTION"
    NEW_BLOCK = "NEW_BLOCK"
    REQUEST_CHAIN = "REQUEST_CHAIN"
    RESPONSE_CHAIN = "RESPONSE_CHAIN"
    PING = "PING"
    PONG = "PONG"
    DISCOVER_PEERS = "DISCOVER_PEERS"
    PEERS_LIST = "PEERS_LIST"


@dataclass
class Message:
    """Representa uma mensagem do protocolo."""
    type: MessageType
    payload: dict[str, Any]
    sender: str = ""  # host:port do remetente
    
    def to_json(self) -> str:
        """Serializa mensagem para JSON."""
        return json.dumps({
            "type": self.type.value,
            "payload": self.payload,
            "sender": self.sender,
        })
    
    @classmethod
    def from_json(cls, data: str) -> "Message":
        """Deserializa mensagem de JSON."""
        parsed = json.loads(data)
        return cls(
            type=MessageType(parsed["type"]),
            payload=parsed["payload"],
            sender=parsed.get("sender", ""),
        )
    
    def to_bytes(self) -> bytes:
        """Converte para bytes para envio via socket."""
        json_str = self.to_json()
        # Adiciona tamanho da mensagem no início (4 bytes)
        length = len(json_str.encode())
        return length.to_bytes(4, 'big') + json_str.encode()
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "Message":
        """Cria mensagem a partir de bytes."""
        json_str = data.decode()
        return cls.from_json(json_str)


class Protocol:
    """
    Factory para criação de mensagens do protocolo.
    """
    
    @staticmethod
    def new_transaction(transaction_dict: dict) -> Message:
        """Cria mensagem de nova transação."""
        return Message(
            type=MessageType.NEW_TRANSACTION,
            payload={"transaction": transaction_dict},
        )
    
    @staticmethod
    def new_block(block_dict: dict) -> Message:
        """Cria mensagem de novo bloco minerado."""
        return Message(
            type=MessageType.NEW_BLOCK,
            payload={"block": block_dict},
        )
    
    @staticmethod
    def request_chain() -> Message:
        """Cria mensagem de solicitação da blockchain."""
        return Message(
            type=MessageType.REQUEST_CHAIN,
            payload={},
        )
    
    @staticmethod
    def response_chain(blockchain_dict: dict) -> Message:
        """Cria mensagem de resposta com a blockchain."""
        return Message(
            type=MessageType.RESPONSE_CHAIN,
            payload={"blockchain": blockchain_dict},
        )
    
    @staticmethod
    def ping() -> Message:
        """Cria mensagem de ping."""
        return Message(
            type=MessageType.PING,
            payload={},
        )
    
    @staticmethod
    def pong() -> Message:
        """Cria mensagem de pong."""
        return Message(
            type=MessageType.PONG,
            payload={},
        )
    
    @staticmethod
    def discover_peers() -> Message:
        """Cria mensagem de descoberta de peers."""
        return Message(
            type=MessageType.DISCOVER_PEERS,
            payload={},
        )
    
    @staticmethod
    def peers_list(peers: list[str]) -> Message:
        """Cria mensagem com lista de peers."""
        return Message(
            type=MessageType.PEERS_LIST,
            payload={"peers": peers},
        )
