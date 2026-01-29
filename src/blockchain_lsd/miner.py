"""
Módulo de Mineração (Proof of Work)
"""

import time
from typing import Callable

from .block import Block
from .blockchain import Blockchain
from .transaction import Transaction


class Miner:
    """
    Implementa o algoritmo de Proof of Work.
    
    O minerador deve encontrar um nonce tal que o hash do bloco
    comece com a dificuldade especificada (ex: "000").
    """
    
    def __init__(self, blockchain: Blockchain, miner_address: str):
        self.blockchain = blockchain
        self.miner_address = miner_address
        self.mining = False
    
    def mine_block(
        self,
        transactions: list[Transaction] = None,
        on_progress: Callable[[int], None] = None,
    ) -> Block | None:
        """
        Minera um novo bloco com as transações pendentes.
        
        Args:
            transactions: Lista de transações (usa pendentes se None)
            on_progress: Callback para reportar progresso (nonce atual)
        
        Returns:
            Bloco minerado ou None se interrompido
        """
        if transactions is None:
            transactions = self.blockchain.pending_transactions.copy()
        
        if not transactions:
            return None
        
        self.mining = True
        
        # Cria bloco candidato
        block = Block(
            index=len(self.blockchain.chain),
            previous_hash=self.blockchain.last_block.hash,
            transactions=transactions,
            nonce=0,
            timestamp=time.time(),
        )
        
        # Proof of Work: encontra nonce válido
        while self.mining:
            block.hash = block.calculate_hash()
            
            if block.is_valid_hash(Blockchain.DIFFICULTY):
                self.mining = False
                return block
            
            block.nonce += 1
            
            # Reporta progresso a cada 10000 tentativas
            if on_progress and block.nonce % 10000 == 0:
                on_progress(block.nonce)
        
        return None
    
    def stop_mining(self):
        """Interrompe a mineração em andamento."""
        self.mining = False
