"""
Módulo da Blockchain
"""

from typing import Any
from collections import defaultdict

from .block import Block
from .transaction import Transaction


class Blockchain:
    """
    Gerencia a cadeia de blocos e transações pendentes.
    
    Responsabilidades:
    - Manter a cadeia de blocos válida
    - Gerenciar pool de transações pendentes
    - Validar blocos e transações
    - Calcular saldos
    """
    
    DIFFICULTY = "000"  # Hash deve começar com 000
    
    def __init__(self):
        self.chain: list[Block] = [Block.create_genesis()]
        self.pending_transactions: list[Transaction] = []
    
    @property
    def last_block(self) -> Block:
        """Retorna o último bloco da cadeia."""
        return self.chain[-1]
    
    def get_balance(self, address: str) -> float:
        """
        Calcula o saldo de um endereço.
        
        Soma todas as transações recebidas e subtrai as enviadas.
        """
        balance = 0.0
        
        for block in self.chain:
            for tx in block.transactions:
                if tx.destino == address:
                    balance += tx.valor
                if tx.origem == address:
                    balance -= tx.valor
        
        # Considera também transações pendentes
        for tx in self.pending_transactions:
            if tx.destino == address:
                balance += tx.valor
            if tx.origem == address:
                balance -= tx.valor
        
        return balance
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """
        Adiciona uma transação ao pool de pendentes.
        
        Valida:
        - Valor positivo
        - Saldo suficiente na origem
        - Transação não duplicada
        """
        # Verifica duplicata
        if transaction in self.pending_transactions:
            return False
        
        for block in self.chain:
            if transaction in block.transactions:
                return False
        
        # Verifica saldo (exceto para origem "genesis" ou "coinbase")
        if transaction.origem not in ("genesis", "coinbase"):
            balance = self.get_balance(transaction.origem)
            if balance < transaction.valor:
                return False
        
        self.pending_transactions.append(transaction)
        return True
    
    def add_block(self, block: Block) -> bool:
        """
        Adiciona um bloco à cadeia após validação.
        
        Valida:
        - Índice correto
        - Hash do bloco anterior
        - Proof of Work válido
        - Hash calculado corretamente
        """
        if not self.is_valid_block(block):
            return False
        
        # Remove transações do bloco do pool de pendentes
        for tx in block.transactions:
            if tx in self.pending_transactions:
                self.pending_transactions.remove(tx)
        
        self.chain.append(block)
        return True
    
    def is_valid_block(self, block: Block) -> bool:
        """Valida um bloco antes de adicionar à cadeia."""
        # Verifica índice
        if block.index != len(self.chain):
            return False
        
        # Verifica hash do bloco anterior
        if block.previous_hash != self.last_block.hash:
            return False
        
        # Verifica Proof of Work
        if not block.hash.startswith(self.DIFFICULTY):
            return False
        
        # Verifica se hash está correto
        if block.hash != block.calculate_hash():
            return False
        
        return True
    
    def is_valid_chain(self, chain: list[Block] = None) -> bool:
        """
        Valida toda a cadeia de blocos.
        
        Verifica:
        - Bloco gênesis correto
        - Encadeamento de hashes
        - Proof of Work de cada bloco
        """
        if chain is None:
            chain = self.chain
        
        if not chain:
            return False
        
        # Verifica bloco gênesis
        genesis = Block.create_genesis()
        if chain[0].hash != genesis.hash:
            return False
        
        # Verifica cada bloco
        for i in range(1, len(chain)):
            current = chain[i]
            previous = chain[i - 1]
            
            # Verifica encadeamento
            if current.previous_hash != previous.hash:
                return False
            
            # Verifica hash
            if current.hash != current.calculate_hash():
                return False
            
            # Verifica Proof of Work
            if not current.hash.startswith(self.DIFFICULTY):
                return False
        
        return True
    
    def replace_chain(self, new_chain: list[Block]) -> bool:
        """
        Substitui a cadeia atual por uma nova (mais longa e válida).
        
        Usado para resolução de conflitos (cadeia mais longa vence).
        """
        if len(new_chain) <= len(self.chain):
            return False
        
        if not self.is_valid_chain(new_chain):
            return False
        
        self.chain = new_chain
        return True
    
    def to_dict(self) -> dict[str, Any]:
        """Converte blockchain para dicionário (serialização JSON)."""
        return {
            "chain": [block.to_dict() for block in self.chain],
            "pending_transactions": [tx.to_dict() for tx in self.pending_transactions],
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Blockchain":
        """Cria blockchain a partir de dicionário."""
        blockchain = cls()
        blockchain.chain = [Block.from_dict(b) for b in data["chain"]]
        blockchain.pending_transactions = [
            Transaction.from_dict(tx) for tx in data["pending_transactions"]
        ]
        return blockchain
