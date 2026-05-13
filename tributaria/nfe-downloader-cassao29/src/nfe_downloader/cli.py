"""
CLI do nfe-downloader — interface humana e didática para o cliente SEFAZ.

Comandos:
    nfe-downloader status              # Status do CNPJ (validação + último NSU)
    nfe-downloader sync                # Baixa NF-e pendentes
    nfe-downloader list                # Lista NF-e já baixadas
    nfe-downloader get <chave>         # Mostra dados parseados de uma NF-e
    nfe-downloader download <chave>    # Baixa uma NF-e específica por chave
    nfe-downloader info                # Mostra a configuração atual (.env)

Flag global:
    --json                     # Saída em JSON (para integração com outros sistemas)

A primeira execução tipicamente é: status → (corrigir erros) → sync.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from . import __version__
from .client import SEFAZClient, PathTraversalError
from .masking import mask_chave, mask_cnpj
from .parser import NFeParser

console = Console()
err_console = Console(stderr=True, style="bold red")


# Mensagens didáticas para erros comuns.
def _format_friendly_error(exc: Exception) -> str:
    msg = str(exc)
    cls = type(exc).__name__

    if isinstance(exc, FileNotFoundError):
        return (
            f"Arquivo não encontrado: {exc.filename or msg}\n\n"
            f"Se for o certificado: verifique o caminho em SEFAZ_CERT_PATH no .env.\n"
            f"Use caminho absoluto (ex: /home/usuario/cert.pfx)."
        )

    if "Invalid password" in msg or "wrong" in msg.lower() and "password" in msg.lower():
        return (
            "Senha do certificado incorreta.\n\n"
            "Verifique SEFAZ_CERT_PASSWORD no .env. Letras maiúsculas/minúsculas importam."
        )

    if "Could not deserialize" in msg or "PKCS12" in msg:
        return (
            "O arquivo não parece ser um certificado .pfx/.p12 válido.\n\n"
            "Verifique se o arquivo foi baixado corretamente e não está corrompido.\n"
            "Confirme que é tipo A1 (arquivo). A3 (token/cartão) não é suportado."
        )

    if "Variáveis de ambiente obrigatórias" in msg:
        return (
            f"{msg}\n\n"
            "Passo a passo:\n"
            "  1. cp .env.example .env\n"
            "  2. Edite .env e preencha os campos\n"
            "  3. Tente novamente"
        )

    if "Connection" in cls or "Timeout" in cls or "communication" in msg.lower():
        return (
            "Erro de comunicação com a SEFAZ.\n\n"
            "Possíveis causas:\n"
            "  • Sem acesso à internet\n"
            "  • Firewall bloqueando porta 443\n"
            "  • SEFAZ temporariamente fora do ar\n"
            "  • URL incorreta para o ambiente (homologacao vs producao)"
        )

    return f"[{cls}] {msg}"


def _print_error(exc: Exception, as_json: bool = False):
    if as_json:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": str(exc),
                    "type": type(exc).__name__,
                },
                ensure_ascii=False,
            )
        )
    else:
        err_console.print(Panel.fit(_format_friendly_error(exc), title="ERRO", border_style="red"))


def _make_client_or_exit(as_json: bool) -> SEFAZClient:
    try:
        return SEFAZClient.from_env()
    except Exception as exc:
        _print_error(exc, as_json=as_json)
        sys.exit(2)


# ============================================================
# Comandos
# ============================================================


def cmd_info(args, as_json: bool):
    """Mostra a configuração atual carregada do .env (sem expor senhas)."""
    import os

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    cfg = {
        "SEFAZ_CNPJ": os.environ.get("SEFAZ_CNPJ", "(não definido)"),
        "SEFAZ_CERT_PATH": os.environ.get("SEFAZ_CERT_PATH", "(não definido)"),
        "SEFAZ_CERT_PASSWORD": "***" if os.environ.get("SEFAZ_CERT_PASSWORD") else "(não definido)",
        "SEFAZ_AMBIENTE": os.environ.get("SEFAZ_AMBIENTE", "(não definido — default: homologacao)"),
        "SEFAZ_UF": os.environ.get("SEFAZ_UF", "(não definido — default: 35)"),
        "SEFAZ_STORAGE_DIR": os.environ.get("SEFAZ_STORAGE_DIR", "(não definido — default: ./nfe_storage)"),
    }

    if as_json:
        print(json.dumps(cfg, ensure_ascii=False, indent=2))
        return

    table = Table(title="Configuração atual (do .env)", show_header=False, border_style="cyan")
    table.add_column("Variável", style="bold")
    table.add_column("Valor")
    for k, v in cfg.items():
        table.add_row(k, str(v))
    console.print(table)

    cert_path = os.environ.get("SEFAZ_CERT_PATH", "")
    if cert_path and not Path(cert_path).exists():
        console.print(
            f"\n[yellow]⚠[/yellow]  O arquivo de certificado [bold]{cert_path}[/bold] não existe."
        )


def cmd_status(args, as_json: bool):
    client = _make_client_or_exit(as_json)
    try:
        status = client.get_sync_status()
    except Exception as exc:
        _print_error(exc, as_json=as_json)
        sys.exit(1)

    if as_json:
        print(json.dumps(status, ensure_ascii=False, indent=2, default=str))
        return

    table = Table(title=f"Status SEFAZ — {status['cnpj_masked']}", border_style="cyan")
    table.add_column("Campo", style="bold")
    table.add_column("Valor")
    table.add_row("CNPJ", status["cnpj_masked"])
    table.add_row("Ambiente", status["ambiente"])
    table.add_row("Último NSU consumido", status["ultimo_nsu"])
    table.add_row("Max NSU disponível", status["max_nsu"])
    table.add_row("Última sincronização", str(status["last_sync"] or "(nunca)"))
    table.add_row("Total de NF-e baixadas", str(status["total_downloaded"]))
    table.add_row("  ↳ XMLs completos", str(status["completos"]))
    table.add_row("  ↳ Marcadas como processadas", str(status["processados"]))
    table.add_row(
        "Pode sincronizar agora?",
        "[green]sim[/green]" if status["can_sync"] else f"[yellow]não — aguarde {status['wait_seconds']//60} min[/yellow]",
    )
    console.print(table)


def cmd_sync(args, as_json: bool):
    client = _make_client_or_exit(as_json)

    if not as_json:
        console.print(
            f"[cyan]Iniciando sincronização[/cyan] (ambiente: [bold]{client.ambiente}[/bold], "
            f"CNPJ: [bold]{mask_cnpj(client.cnpj)}[/bold])"
        )

    try:
        if as_json:
            result = client.sincronizar_tudo(
                max_iterations=args.max_iterations, force=args.force
            )
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[bold green]{task.completed}[/bold green] documentos"),
                console=console,
            ) as progress:
                task = progress.add_task("Consultando SEFAZ...", total=None)
                result = client.sincronizar_tudo(
                    max_iterations=args.max_iterations, force=args.force
                )
                progress.update(task, completed=result["total_baixados"])
    except Exception as exc:
        _print_error(exc, as_json=as_json)
        sys.exit(1)

    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        sys.exit(0 if not result.get("rate_limited") else 1)

    if result["rate_limited"]:
        wait_min = result["wait_seconds"] // 60
        console.print(
            Panel.fit(
                f"Rate limit ativo. Aguarde [bold]{wait_min} min[/bold] antes da próxima sincronização.\n"
                "Isso é uma regra da SEFAZ — bater nesse limite reseta o timer.",
                title="⏸  Rate Limited",
                border_style="yellow",
            )
        )
        sys.exit(1)

    summary = Table(title="Resultado da sincronização", show_header=False, border_style="green")
    summary.add_column("", style="bold")
    summary.add_column("")
    summary.add_row("Total baixado", str(result["total_baixados"]))
    summary.add_row("  ↳ XMLs completos (procNFe)", str(result["completos"]))
    summary.add_row("  ↳ Resumos (resNFe)", str(result["resumos"]))
    summary.add_row("  ↳ Eventos", str(result["eventos"]))
    summary.add_row("Erros", str(len(result["erros"])))
    console.print(summary)

    if result["erros"]:
        for err in result["erros"]:
            console.print(f"  [red]✗[/red] iter {err['iteracao']}: [{err['codigo']}] {err['motivo']}")

    if result["total_baixados"] > 0:
        console.print(
            f"\n[green]✓[/green] Os XMLs estão em: [bold]{client.storage_dir}[/bold]"
        )


def cmd_list(args, as_json: bool):
    client = _make_client_or_exit(as_json)
    try:
        result = client.listar_nfe_baixadas(
            apenas_completas=args.completas,
            apenas_nao_processadas=args.pendentes,
            cnpj_emitente=args.emitente,
            limit=args.limit,
            offset=args.offset,
        )
    except Exception as exc:
        _print_error(exc, as_json=as_json)
        sys.exit(1)

    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return

    if not result["data"]:
        console.print("[yellow]Nenhuma NF-e encontrada com esses filtros.[/yellow]")
        return

    table = Table(
        title=f"NF-e baixadas — exibindo {len(result['data'])} de {result['total']}",
        border_style="cyan",
    )
    table.add_column("Chave", overflow="fold")
    table.add_column("Emitente", overflow="fold")
    table.add_column("Data emissão")
    table.add_column("Valor (R$)", justify="right")
    table.add_column("Tipo")
    for row in result["data"]:
        tipo = "✓ completo" if row["is_complete"] else "resumo"
        valor = (row["valor_total"] or 0) / 100
        chave_curta = (row["chave"] or "")[-12:] if row["chave"] else "(sem chave)"
        table.add_row(
            chave_curta,
            (row["nome_emitente"] or "")[:30],
            (row["data_emissao"] or "")[:10],
            f"{valor:,.2f}",
            tipo,
        )
    console.print(table)


def cmd_get(args, as_json: bool):
    client = _make_client_or_exit(as_json)
    try:
        xml = client.obter_xml(args.chave)
    except PathTraversalError:
        _print_error(ValueError("Caminho do XML inválido (path traversal detectado)."), as_json=as_json)
        sys.exit(1)
    except Exception as exc:
        _print_error(exc, as_json=as_json)
        sys.exit(1)

    if not xml:
        _print_error(
            ValueError(f"NF-e {mask_chave(args.chave)} não foi baixada ainda. Rode 'nfe-downloader sync' primeiro."),
            as_json=as_json,
        )
        sys.exit(1)

    parser = NFeParser()
    nfe = parser.parse(xml)
    data = parser.to_dict(nfe)
    data.pop("xml_original", None)

    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        return

    console.print(
        Panel.fit(
            f"[bold]Chave:[/bold] {nfe.chave}\n"
            f"[bold]Número:[/bold] {nfe.numero}  [bold]Série:[/bold] {nfe.serie}\n"
            f"[bold]Emissão:[/bold] {nfe.data_emissao}\n"
            f"[bold]Natureza:[/bold] {nfe.natureza_operacao}\n"
            f"[bold]Protocolo:[/bold] {nfe.protocolo}",
            title="NF-e",
            border_style="cyan",
        )
    )
    console.print(
        f"[bold]Emitente:[/bold] {nfe.emitente.nome} ({nfe.emitente.cnpj})"
    )
    console.print(
        f"[bold]Destinatário:[/bold] {nfe.destinatario.nome} ({nfe.destinatario.cnpj})"
    )
    console.print(f"[bold]Valor total:[/bold] R$ {nfe.totais.valor_nota:,.2f}")
    console.print(f"[bold]Itens:[/bold] {len(nfe.itens)}")


def cmd_download(args, as_json: bool):
    client = _make_client_or_exit(as_json)
    try:
        result = client.consultar_por_chave(args.chave)
    except Exception as exc:
        _print_error(exc, as_json=as_json)
        sys.exit(1)

    payload = {
        "success": result.status == "success",
        "status": result.status,
        "codigo": result.codigo,
        "motivo": result.motivo,
        "documentos": len(result.documentos),
    }

    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        sys.exit(0 if payload["success"] else 1)

    if result.status == "success":
        console.print(
            f"[green]✓[/green] Baixado: {mask_chave(args.chave)}  ({len(result.documentos)} doc)"
        )
    else:
        console.print(
            f"[red]✗[/red] Falha [{result.codigo}]: {result.motivo}"
        )
        sys.exit(1)


# ============================================================
# Argparse
# ============================================================


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nfe-downloader",
        description=(
            "Baixa NF-e (compras) da SEFAZ via Distribuição DF-e.\n\n"
            "Comece com:\n"
            "  nfe-downloader info     — verifica configuração\n"
            "  nfe-downloader status   — testa conexão e mostra estado\n"
            "  nfe-downloader sync     — baixa NF-e pendentes\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Saída em JSON (para integração com outros sistemas)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suprime logs INFO (mantém apenas WARNING/ERROR)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"nfe-downloader {__version__}",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "info",
        help="Mostra a configuração atual carregada do .env (sem expor senhas)",
    )
    sub.add_parser(
        "status",
        help="Mostra o estado de sincronização (último NSU, total baixado, rate limit)",
    )

    p_sync = sub.add_parser(
        "sync",
        help="Sincroniza NF-e pendentes da SEFAZ",
    )
    p_sync.add_argument(
        "--max-iterations",
        type=int,
        default=100,
        help="Número máximo de iterações (cada uma retorna até 50 docs). Default: 100",
    )
    p_sync.add_argument(
        "--force",
        action="store_true",
        help="Ignora verificação de rate limit local (USE COM CUIDADO — pode bater na SEFAZ e resetar o timer)",
    )

    p_list = sub.add_parser("list", help="Lista NF-e já baixadas localmente")
    p_list.add_argument("--completas", action="store_true", help="Apenas XMLs completos")
    p_list.add_argument("--pendentes", action="store_true", help="Apenas não processadas")
    p_list.add_argument("--emitente", help="Filtra por CNPJ do emitente")
    p_list.add_argument("--limit", type=int, default=50, help="Quantos resultados mostrar (default: 50)")
    p_list.add_argument("--offset", type=int, default=0, help="Offset para paginação")

    p_get = sub.add_parser("get", help="Mostra dados parseados de uma NF-e por chave")
    p_get.add_argument("chave", help="Chave de acesso de 44 dígitos")

    p_dl = sub.add_parser("download", help="Baixa uma NF-e específica por chave")
    p_dl.add_argument("chave", help="Chave de acesso de 44 dígitos")

    return parser


COMMANDS = {
    "info": cmd_info,
    "status": cmd_status,
    "sync": cmd_sync,
    "list": cmd_list,
    "get": cmd_get,
    "download": cmd_download,
}


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    handler = COMMANDS.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    try:
        handler(args, as_json=args.json)
    except KeyboardInterrupt:
        err_console.print("\nInterrompido pelo usuário.")
        sys.exit(130)


if __name__ == "__main__":
    main()
