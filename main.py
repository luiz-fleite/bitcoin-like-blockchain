#!/usr/bin/env python3
"""
Bitcoin Blockchain - Ponto de entrada principal

Uso:
    python main.py --port 5000 --bootstrap localhost:5001
"""

import argparse
import threading
import time
import sys
import logging

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
import questionary

from src.blockchain import Node, Transaction

console = Console()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Nó da rede blockchain distribuída"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host do nó (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Porta do nó (default: 5000)"
    )
    parser.add_argument(
        "--bootstrap",
        nargs="*",
        default=[],
        help="Endereços de nós bootstrap (ex: localhost:5001)"
    )
    return parser.parse_args()


def create_transaction(node: Node):
    console.print(Panel("[bold blue]Nova Transação[/bold blue]", expand=False))
    
    origem = node.address
    console.print(f"Origem: [bold cyan]{origem}[/bold cyan]")
    
    choices = [
        questionary.Choice("Digitar endereço manualmente", "manual")
    ]
    for peer in node.peers:
        choices.append(questionary.Choice(f"Peer: {peer}", peer))
        
    destino_choice = questionary.select(
        "Escolha o destino:",
        choices=choices
    ).ask()
    
    if not destino_choice: return
    
    if destino_choice == "manual":
        destino = questionary.text("Destino:").ask()
        if not destino: return
    else:
        destino = destino_choice
        
    valor_str = questionary.text("Valor:").ask()
    if not valor_str: return
    
    try:
        valor = float(valor_str)
        tx = Transaction(origem=origem, destino=destino, valor=valor)
        
        # Verifica saldo antes de adicionar
        saldo = node.blockchain.get_balance(origem)
        if origem not in ("genesis", "coinbase") and saldo < valor:
            console.print(f"[bold red]✗ Saldo insuficiente![/bold red] {origem} tem {saldo}, precisa de {valor}")
            return
        
        node.broadcast_transaction(tx)
        console.print(f"[bold green]✓ Transação criada:[/bold green] {tx.id[:8]}...")
    except ValueError as e:
        console.print(f"[bold red]✗ Erro:[/bold red] {e}")


def show_pending(node: Node):
    if not node.blockchain.pending_transactions:
        console.print(Panel("[yellow]Nenhuma transação pendente.[/yellow]", title="Transações Pendentes", expand=False))
        return
    
    table = Table(title="Transações Pendentes", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=12)
    table.add_column("Origem")
    table.add_column("Destino")
    table.add_column("Valor", justify="right")
    
    for tx in node.blockchain.pending_transactions:
        table.add_row(tx.id[:8] + "...", tx.origem, tx.destino, str(tx.valor))
        
    console.print(table)


def mine_block(node: Node):
    num_txs = len(node.blockchain.pending_transactions)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description=f"Minerando bloco com {num_txs} transação(ões)...", total=None)
        start = time.time()
        block = node.mine()
        elapsed = time.time() - start
    
    if block:
        console.print(Panel(
            f"[bold green]✓ Bloco #{block.index} minerado em {elapsed:.2f}s[/bold green]\n"
            f"Hash: [cyan]{block.hash}[/cyan]\n"
            f"Nonce: [yellow]{block.nonce}[/yellow]",
            title="Mineração Concluída",
            expand=False
        ))
    else:
        console.print("[bold red]✗ Mineração interrompida[/bold red]")


def show_blockchain(node: Node):
    for block in node.blockchain.chain:
        table = Table(show_header=True, header_style="bold blue", expand=True)
        table.add_column("Origem")
        table.add_column("Destino")
        table.add_column("Valor", justify="right")
        
        for tx in block.transactions:
            table.add_row(tx.origem, tx.destino, str(tx.valor))
            
        panel_content = (
            f"Hash: [cyan]{block.hash[:32]}...[/cyan]\n"
            f"Previous: [dim]{block.previous_hash[:32]}...[/dim]\n"
            f"Nonce: [yellow]{block.nonce}[/yellow]\n"
            f"Transações: {len(block.transactions)}"
        )
        
        console.print(Panel(
            panel_content,
            title=f"[bold magenta]Bloco #{block.index}[/bold magenta]",
            expand=False
        ))
        if block.transactions:
            console.print(table)
        console.print()


def show_balance(node: Node):
    choices = [
        questionary.Choice(f"Meu nó ({node.address})", node.address),
        questionary.Choice("Digitar endereço manualmente", "manual")
    ]
    for peer in node.peers:
        choices.append(questionary.Choice(f"Peer: {peer}", peer))
        
    address_choice = questionary.select(
        "Escolha o endereço para ver o saldo:",
        choices=choices
    ).ask()
    
    if not address_choice: return
    
    if address_choice == "manual":
        address = questionary.text("Endereço:").ask()
        if not address: return
    else:
        address = address_choice
        
    balance = node.blockchain.get_balance(address)
    console.print(Panel(f"Saldo de [bold cyan]{address}[/bold cyan]: [bold green]{balance}[/bold green]", expand=False))


def show_peers(node: Node):
    if not node.peers:
        console.print(Panel("[yellow]Nenhum peer conectado.[/yellow]", title="Peers Conectados", expand=False))
        return
    
    table = Table(title="Peers Conectados", show_header=True, header_style="bold green")
    table.add_column("Endereço")
    
    for peer in node.peers:
        table.add_row(peer)
        
    console.print(table)


def connect_peer(node: Node):
    peer = questionary.text("Endereço do peer (host:port):").ask()
    if not peer: return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description=f"Conectando a {peer}...", total=None)
        success = node.connect_to_peer(peer)
        
    if success:
        console.print(f"[bold green]✓ Conectado a {peer}[/bold green]")
    else:
        console.print(f"[bold red]✗ Falha ao conectar a {peer}[/bold red]")


def sync_chain(node: Node):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Sincronizando blockchain e mempool...", total=None)
        node.sync_blockchain()
        result = node.sync_mempool()
    
    added = result["added"]
    unreachable = result["unreachable"]
    
    console.print(
        f"[bold green]✓ Blockchain sincronizada com {len(node.blockchain.chain)} blocos[/bold green]\n"
        f"[bold green]✓ Mempool: {len(node.blockchain.pending_transactions)} transação(ões) pendente(s)"
        + (f" ([cyan]+{added} nova(s)[/cyan])" if added else "") +
        "[/bold green]"
    )
    for peer in unreachable:
        console.print(f"[bold yellow]⚠ Não foi possível conectar ao peer {peer} — verifique firewall/rede[/bold yellow]")


def main():
    args = parse_args()
    
    # Configura logging para arquivo em vez de stdout para não quebrar a CLI
    log_file = f"node_{args.port}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
        ]
    )
    
    banner = Text(
        "  ____  _ _            _          ____ _           _       \n"
        " | __ )(_) |_ ___ ___ (_)_ __    / ___| |__   __ _(_)_ __  \n"
        " |  _ \\| | __/ __/ _ \\| | '_ \\  | |   | '_ \\ / _` | | '_ \\ \n"
        " | |_) | | || (_| (_) | | | | | | |___| | | | (_| | | | | |\n"
        " |____/|_|\\__\\___\\___/|_|_| |_|  \\____|_| |_|\\__,_|_|_| |_|\n"
    )
    banner.stylize("bold yellow")
    console.print(banner)
    console.print(Panel.fit(
        f"[bold cyan]Node[/bold cyan] {args.host}:{args.port}\n"
        f"[dim]Logs → {log_file}[/dim]",
        border_style="cyan"
    ))
    
    # Cria e inicia o nó
    node = Node(host=args.host, port=args.port)
    node.start()
    
    # Conecta aos nós bootstrap
    for bootstrap in args.bootstrap:
        if node.connect_to_peer(bootstrap):
            console.print(f"[green]Conectado ao bootstrap:[/green] {bootstrap}")
    
    # Sincroniza blockchain se tiver peers
    if node.peers:
        node.sync_blockchain()
    
    choices = [
        questionary.Choice("1. Criar transação", "1"),
        questionary.Choice("2. Ver transações pendentes", "2"),
        questionary.Choice("3. Minerar bloco", "3"),
        questionary.Choice("4. Ver blockchain", "4"),
        questionary.Choice("5. Ver saldo", "5"),
        questionary.Choice("6. Ver peers conectados", "6"),
        questionary.Choice("7. Conectar a peer", "7"),
        questionary.Choice("8. Sincronizar blockchain", "8"),
        questionary.Separator(),
        questionary.Choice("0. Sair", "0")
    ]
    
    # Loop principal
    try:
        while True:
            console.print()
            choice = questionary.select(
                "Escolha uma ação:",
                choices=choices,
                style=questionary.Style([
                    ('qmark', 'fg:#673ab7 bold'),
                    ('question', 'bold'),
                    ('answer', 'fg:#f44336 bold'),
                    ('pointer', 'fg:#673ab7 bold'),
                    ('highlighted', 'fg:#673ab7 bold'),
                    ('selected', 'fg:#cc5454'),
                    ('separator', 'fg:#cc5454'),
                    ('instruction', ''),
                    ('text', ''),
                    ('disabled', 'fg:#858585 italic')
                ])
            ).ask()
            
            if choice is None or choice == "0":
                console.print("[yellow]Encerrando...[/yellow]")
                break
                
            match choice:
                case "1":
                    create_transaction(node)
                case "2":
                    show_pending(node)
                case "3":
                    mine_block(node)
                case "4":
                    show_blockchain(node)
                case "5":
                    show_balance(node)
                case "6":
                    show_peers(node)
                case "7":
                    connect_peer(node)
                case "8":
                    sync_chain(node)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrompido pelo usuário[/yellow]")
    
    finally:
        node.stop()


if __name__ == "__main__":
    main()
