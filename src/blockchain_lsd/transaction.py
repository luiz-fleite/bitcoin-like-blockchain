"""
Módulo de Transações
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Transaction:
    """
    Representa uma transação na blockchain.
    
    Campos obrigatórios:
    - id: identificador único
    - origem: endereço de origem
    - destino: endereço de destino  
    - valor: quantidade transferida
    - timestamp: momento da criação
    """
    origem: str
    destino: str
    valor: float
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """Valida a transação após criação."""
        if self.valor <= 0:
            raise ValueError("Valor da transação deve ser positivo")
        if not self.origem or not self.destino:
            raise ValueError("Origem e destino são obrigatórios")
    
    def to_dict(self) -> dict[str, Any]:
        """Converte transação para dicionário (serialização JSON)."""
        return {
            "id": self.id,
            "origem": self.origem,
            "destino": self.destino,
            "valor": self.valor,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        """Cria transação a partir de dicionário."""
        return cls(
            id=data["id"],
            origem=data["origem"],
            destino=data["destino"],
            valor=data["valor"],
            timestamp=data["timestamp"],
        )
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, Transaction):
            return self.id == other.id
        return False
