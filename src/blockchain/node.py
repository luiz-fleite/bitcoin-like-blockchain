"""
Módulo do Nó da Rede P2P
"""

import socket
import threading
import logging
from typing import Callable

from .blockchain import Blockchain
from .block import Block
from .transaction import Transaction
from .miner import Miner
from .protocol import Protocol, Message, MessageType


class Node:
    """
    Representa um nó na rede P2P da blockchain.
    
    Responsabilidades:
    - Executar como processo independente
    - Comunicar com outros nós via sockets
    - Manter cópia local da blockchain
    - Minerar novos blocos
    - Propagar transações e blocos
    """
    
    BUFFER_SIZE = 65536  # 64KB
    
    def __init__(self, host: str = "localhost", port: int = 5000):
        self.host = host
        self.port = port
        self.address = f"{host}:{port}"
        
        self.blockchain = Blockchain()
        self.miner = Miner(self.blockchain, self.address)
        
        self.peers: set[str] = set()  # Conjunto de peers conhecidos
        self.server_socket: socket.socket | None = None
        self.running = False
        
        self.logger = logging.getLogger(f"Node:{port}")
        
        # Callbacks para eventos
        self.on_new_block: Callable[[Block], None] | None = None
        self.on_new_transaction: Callable[[Transaction], None] | None = None
    
    def start(self):
        """Inicia o servidor do nó."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Bind em 0.0.0.0 para aceitar conexões de qualquer interface (útil para WSL/Docker)
        self.server_socket.bind(("0.0.0.0", self.port))
        self.server_socket.listen(10)
        
        self.running = True
        self.logger.info(f"Nó iniciado em {self.address}")
        
        # Thread para aceitar conexões
        accept_thread = threading.Thread(target=self._accept_connections)
        accept_thread.daemon = True
        accept_thread.start()
    
    def stop(self):
        """Para o servidor do nó."""
        self.running = False
        self.miner.stop_mining()
        if self.server_socket:
            self.server_socket.close()
        self.logger.info("Nó encerrado")
    
    def _accept_connections(self):
        """Loop para aceitar novas conexões."""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                if self.running:
                    self.logger.error(f"Erro ao aceitar conexão: {e}")
    
    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """Processa mensagens de um cliente."""
        try:
            # Lê tamanho da mensagem (4 bytes)
            length_data = client_socket.recv(4)
            if not length_data:
                return
            
            length = int.from_bytes(length_data, 'big')
            
            # Lê mensagem
            data = b""
            while len(data) < length:
                chunk = client_socket.recv(min(self.BUFFER_SIZE, length - len(data)))
                if not chunk:
                    break
                data += chunk
            
            if data:
                message = Message.from_bytes(data)
                response = self._process_message(message)
                
                if response:
                    client_socket.sendall(response.to_bytes())
        
        except Exception as e:
            self.logger.error(f"Erro ao processar cliente {address}: {e}")
        finally:
            client_socket.close()
    
    def _process_message(self, message: Message) -> Message | None:
        """Processa uma mensagem recebida e retorna resposta se necessário."""
        self.logger.info(f"Mensagem recebida: {message.type.value} de {message.sender}")
        
        match message.type:
            case MessageType.NEW_TRANSACTION:
                tx_data = message.payload["transaction"]
                transaction = Transaction.from_dict(tx_data)
                if self.blockchain.add_transaction(transaction):
                    self.logger.info(f"Nova transação adicionada: {transaction.id[:8]}...")
                    # Propaga para outros peers
                    self._broadcast(message, exclude=message.sender)
                    if self.on_new_transaction:
                        self.on_new_transaction(transaction)
            
            case MessageType.NEW_BLOCK:
                block_data = message.payload["block"]
                block = Block.from_dict(block_data)
                if self.blockchain.add_block(block):
                    self.logger.info(f"Novo bloco adicionado: #{block.index}")
                    # Para mineração atual (outro nó encontrou primeiro)
                    self.miner.stop_mining()
                    # Propaga para outros peers
                    self._broadcast(message, exclude=message.sender)
                    if self.on_new_block:
                        self.on_new_block(block)
                else:
                    # Bloco rejeitado: pode estar em fork ou atrás da chain.
                    # Solicita a chain completa do remetente para resolver.
                    self.logger.warning(
                        f"Bloco #{block.index} de {message.sender} rejeitado "
                        f"(nossa chain tem {len(self.blockchain.chain)} blocos). "
                        f"Solicitando chain completa para sync..."
                    )
                    if message.sender:
                        try:
                            response = self._send_message(message.sender, Protocol.request_chain())
                            if response and response.type == MessageType.RESPONSE_CHAIN:
                                chain_data = response.payload["blockchain"]
                                new_chain = [Block.from_dict(b) for b in chain_data["chain"]]
                                if self.blockchain.replace_chain(new_chain):
                                    self.logger.info(
                                        f"Chain sincronizada de {message.sender}: "
                                        f"{len(new_chain)} blocos"
                                    )
                                    self.miner.stop_mining()
                                    # Adiciona o remetente como peer se ainda não estava
                                    self.peers.add(message.sender)
                                else:
                                    self.logger.warning(
                                        f"Chain de {message.sender} também rejeitada "
                                        f"(mais curta ou inválida)"
                                    )
                        except Exception as e:
                            self.logger.error(f"Erro ao sincronizar com {message.sender}: {e}")
            
            case MessageType.REQUEST_CHAIN:
                return Protocol.response_chain(self.blockchain.to_dict())
            
            case MessageType.REQUEST_MEMPOOL:
                txs = [tx.to_dict() for tx in self.blockchain.pending_transactions]
                return Protocol.response_mempool(txs)
            
            case MessageType.RESPONSE_CHAIN:
                chain_data = message.payload["blockchain"]
                new_chain = [Block.from_dict(b) for b in chain_data["chain"]]
                if self.blockchain.replace_chain(new_chain):
                    self.logger.info(f"Blockchain atualizada: {len(new_chain)} blocos")
                # Registra o remetente como peer se ainda não estava.
                # Necessário para nós que respondem em nova conexão (estilo callback).
                if message.sender and message.sender != self.address:
                    if message.sender not in self.peers:
                        self.peers.add(message.sender)
                        self.logger.info(f"Peer auto-descoberto via RESPONSE_CHAIN: {message.sender}")
            
            case _:
                # Tenta processar mensagens não obrigatórias (PING, DISCOVER_PEERS, etc)
                # Se a outra equipe não suportar, eles simplesmente vão ignorar ou dar erro,
                # mas não quebra o fluxo principal.
                try:
                    if message.type == MessageType.PING:
                        if message.sender and message.sender != self.address:
                            self.peers.add(message.sender)
                            self.logger.info(f"Peer registrado via PING: {message.sender}")
                        return Protocol.pong()
                    
                    elif message.type == MessageType.DISCOVER_PEERS:
                        return Protocol.peers_list(list(self.peers))
                    
                    elif message.type == MessageType.PEERS_LIST:
                        new_peers = set(message.payload["peers"]) - {self.address}
                        discovered_peers = new_peers - self.peers
                        if discovered_peers:
                            self.peers.update(discovered_peers)
                            self.logger.info(f"Peers descobertos via broadcast: {len(discovered_peers)}")
                            for new_peer in discovered_peers:
                                try:
                                    self._send_message(new_peer, Protocol.ping())
                                except Exception:
                                    pass
                except Exception as e:
                    self.logger.debug(f"Mensagem não padrão ignorada ou falhou: {e}")
        
        return None
    
    def connect_to_peer(self, peer_address: str) -> bool:
        """Conecta a um peer e adiciona à lista.

        Usa REQUEST_CHAIN como handshake (mensagem obrigatória pelo padrão).
        
        Suporta dois estilos de resposta:
        - Mesmo socket (nosso estilo): RESPONSE_CHAIN volta na mesma conexão TCP.
        - Conexão nova (estilo callback): o peer abre nova conexão de volta para
          enviar o RESPONSE_CHAIN. Nesse caso o handler do servidor processa a
          chain e este método adiciona o peer mesmo sem resposta na mesma socket.
        """
        if peer_address == self.address:
            return False
        
        try:
            host, port = peer_address.split(":")
            
            # Testa alcançabilidade, envia REQUEST_CHAIN e tenta capturar
            # RESPONSE_CHAIN na mesma socket (nosso estilo).
            connected = False
            response = None
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((host, int(port)))  # lança exceção se inacessível
                connected = True
                
                msg = Protocol.request_chain()
                msg.sender = self.address
                sock.sendall(msg.to_bytes())
                
                try:
                    length_data = sock.recv(4)
                    if length_data:
                        length = int.from_bytes(length_data, 'big')
                        data = b""
                        while len(data) < length:
                            chunk = sock.recv(min(self.BUFFER_SIZE, length - len(data)))
                            if not chunk:
                                break
                            data += chunk
                        if data:
                            response = Message.from_bytes(data)
                except Exception:
                    # Sem resposta na mesma socket: peer usa estilo callback
                    # (abre nova conexão de volta). O servidor vai receber o
                    # RESPONSE_CHAIN e aplicar a chain automaticamente.
                    pass
            
            if not connected:
                return False
            
            # Adiciona peer independentemente do estilo de resposta:
            # - Mesmo socket: processa agora.
            # - Callback: RESPONSE_CHAIN chega pelo servidor em instantes,
            #   e o handler já adiciona o peer também (dupla garantia).
            self.peers.add(peer_address)
            self.logger.info(f"Conectado ao peer: {peer_address}")
            
            if response and response.type == MessageType.RESPONSE_CHAIN:
                chain_data = response.payload["blockchain"]
                new_chain = [Block.from_dict(b) for b in chain_data["chain"]]
                if self.blockchain.replace_chain(new_chain):
                    self.logger.info(
                        f"Blockchain atualizada no handshake: {len(new_chain)} blocos"
                    )
            else:
                self.logger.info(
                    f"Peer {peer_address} usa estilo callback; "
                    f"aguardando RESPONSE_CHAIN inbound..."
                )
            
            # Tenta descobrir peers adicionais (opcional, não-obrigatório)
            try:
                peers_response = self._send_message(peer_address, Protocol.discover_peers())
                if peers_response and peers_response.type == MessageType.PEERS_LIST:
                    new_peers = set(peers_response.payload["peers"]) - {self.address}
                    discovered_peers = new_peers - self.peers
                    if discovered_peers:
                        self.peers.update(discovered_peers)
                        self.logger.info(f"Peers descobertos: {len(discovered_peers)}")
                        for new_peer in discovered_peers:
                            try:
                                self._send_message(new_peer, Protocol.ping())
                            except Exception as e:
                                self.logger.debug(f"Não foi possível notificar {new_peer}: {e}")
            except Exception as e:
                self.logger.debug(f"DISCOVER_PEERS não suportado por {peer_address} (opcional): {e}")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Erro ao conectar ao peer {peer_address}: {e}")
        
        return False
    
    def sync_blockchain(self):
        """Sincroniza blockchain com os peers (baixa a cadeia mais longa)."""
        for peer in list(self.peers):
            try:
                response = self._send_message(peer, Protocol.request_chain())
                if response and response.type == MessageType.RESPONSE_CHAIN:
                    chain_data = response.payload["blockchain"]
                    new_chain = [Block.from_dict(b) for b in chain_data["chain"]]
                    if self.blockchain.replace_chain(new_chain):
                        self.logger.info(f"Blockchain sincronizada de {peer}")
                        break
            except Exception as e:
                self.logger.error(f"Erro ao sincronizar com {peer}: {e}")

    def sync_mempool(self) -> dict:
        """Sincroniza transações pendentes com os peers."""
        added = 0
        unreachable = []
        for peer in list(self.peers):
            try:
                response = self._send_message(peer, Protocol.request_mempool())
                if response and response.type == MessageType.RESPONSE_MEMPOOL:
                    for tx_data in response.payload["transactions"]:
                        tx = Transaction.from_dict(tx_data)
                        # trusted=True: confia que o peer já validou o saldo
                        if self.blockchain.add_transaction(tx, trusted=True):
                            added += 1
                else:
                    unreachable.append(peer)
            except Exception as e:
                self.logger.error(f"Erro ao sincronizar mempool com {peer}: {e}")
                unreachable.append(peer)
        self.logger.info(f"Mempool sincronizada: {added} nova(s) transação(ões) adicionada(s)")
        return {"added": added, "unreachable": unreachable}
        return added
    
    def broadcast_transaction(self, transaction: Transaction):
        """Propaga uma transação para todos os peers."""
        if self.blockchain.add_transaction(transaction):
            message = Protocol.new_transaction(transaction.to_dict())
            self._broadcast(message)
    
    def broadcast_block(self, block: Block):
        """Propaga um bloco minerado para todos os peers."""
        if self.blockchain.add_block(block):
            message = Protocol.new_block(block.to_dict())
            self._broadcast(message)
            self.logger.info(f"Bloco #{block.index} propagado para {len(self.peers)} peers")
    
    def mine(self) -> Block | None:
        """Inicia mineração de um novo bloco."""
        self.logger.info("Iniciando mineração...")
        
        def on_progress(nonce: int):
            self.logger.debug(f"Mineração em progresso... nonce={nonce}")
        
        block = self.miner.mine_block(on_progress=on_progress)
        
        if block:
            self.logger.info(f"Bloco minerado! #{block.index} hash={block.hash[:16]}...")
            self.broadcast_block(block)
        
        return block
    
    def _send_message(self, peer_address: str, message: Message) -> Message | None:
        """Envia mensagem para um peer e retorna resposta."""
        try:
            host, port = peer_address.split(":")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((host, int(port)))
                
                message.sender = self.address
                sock.sendall(message.to_bytes())
                
                # Aguarda resposta
                length_data = sock.recv(4)
                if length_data:
                    length = int.from_bytes(length_data, 'big')
                    data = b""
                    while len(data) < length:
                        chunk = sock.recv(min(self.BUFFER_SIZE, length - len(data)))
                        if not chunk:
                            break
                        data += chunk
                    if data:
                        return Message.from_bytes(data)
        
        except Exception as e:
            self.logger.error(f"Erro ao enviar para {peer_address}: {e}")
        
        return None
    
    def _broadcast(self, message: Message, exclude: str = ""):
        """Envia mensagem para todos os peers."""
        message.sender = self.address
        for peer in list(self.peers):
            if peer != exclude:
                threading.Thread(
                    target=self._send_message,
                    args=(peer, message)
                ).start()
