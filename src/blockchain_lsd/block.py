"""
Módulo de Blocos
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any

from .transaction import Transaction


@dataclass
class Block:
    """
    Representa um bloco na blockchain.
    
    Campos obrigatórios:
    - index: índice do bloco na cadeia
    - previous_hash: hash do bloco anterior
    - transactions: lista de transações
    - nonce: valor para Proof of Work
    - timestamp: momento da criação
    - hash: hash do bloco atual (SHA-256)
    """
    index: int
    previous_hash: str
    transactions: list[Transaction]
    nonce: int = 0
    timestamp: float = field(default_factory=time.time)
    hash: str = ""
    
    def __post_init__(self):
        """Calcula hash se não fornecido."""
        if not self.hash:
            self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """
        Calcula o hash SHA-256 do bloco.
        
        O hash é baseado em todos os campos do bloco exceto o próprio hash.
        """
        block_data = {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "nonce": self.nonce,
            "timestamp": self.timestamp,
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def to_dict(self) -> dict[str, Any]:
        """Converte bloco para dicionário (serialização JSON)."""
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "nonce": self.nonce,
            "timestamp": self.timestamp,
            "hash": self.hash,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Block":
        """Cria bloco a partir de dicionário."""
        transactions = [Transaction.from_dict(tx) for tx in data["transactions"]]
        return cls(
            index=data["index"],
            previous_hash=data["previous_hash"],
            transactions=transactions,
            nonce=data["nonce"],
            timestamp=data["timestamp"],
            hash=data["hash"],
        )
    
    @classmethod
    def create_genesis(cls) -> "Block":
        """
        Cria o bloco gênesis (primeiro bloco da cadeia).
        
        O bloco gênesis tem índice 0 e previous_hash fixo.
        """
        genesis = cls(
            index=0,
            previous_hash="0" * 64,
            transactions=[],
            nonce=0,
            timestamp=0,  # Timestamp fixo para consistência
        )
        genesis.hash = genesis.calculate_hash()
        return genesis
    
    def is_valid_hash(self, difficulty: str = "000") -> bool:
        """Verifica se o hash atende à dificuldade (Proof of Work)."""
        return self.hash.startswith(difficulty)
