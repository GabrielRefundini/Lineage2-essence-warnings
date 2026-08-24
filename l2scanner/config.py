"""Configuracao do usuario: o .env com os dados do Chatwoot.

Separado da calibracao de proposito: isto aqui e escrito a mao e nunca
sobrescrito por ferramenta; a calibracao e o contrario.

O token nunca aparece em log nem em mensagem de erro.
"""

from __future__ import annotations

from pathlib import Path

from .notificador import ConfigChatwoot

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_ENV = RAIZ / ".env"


class ConfigAusente(Exception):
    """Falta configuracao para enviar alertas."""


def ler_env(caminho: Path | None = None) -> dict[str, str]:
    """Le o .env sem depender de biblioteca externa."""
    caminho = caminho or ARQUIVO_ENV
    if not caminho.exists():
        return {}

    valores: dict[str, str] = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        valores[chave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def config_do_chatwoot(caminho: Path | None = None) -> ConfigChatwoot:
    """Monta a configuracao de envio, ou explica exatamente o que falta."""
    env = ler_env(caminho)

    if not env:
        raise ConfigAusente(
            "Nao encontrei o .env.\n"
            "Copie ENV-EXEMPLO.txt para .env e preencha os dados do Chatwoot."
        )

    faltando = [
        chave
        for chave in ("CHATWOOT_URL", "CHATWOOT_ACCOUNT", "CHATWOOT_TOKEN")
        if not env.get(chave)
    ]
    if faltando:
        raise ConfigAusente("Faltam valores no .env: " + ", ".join(faltando))

    if env["CHATWOOT_TOKEN"] == "cole_seu_token_aqui":
        raise ConfigAusente("O CHATWOOT_TOKEN ainda esta com o valor de exemplo.")

    conversas = [
        pedaco.strip()
        for pedaco in env.get("CHATWOOT_CONVERSAS", "").split(",")
        if pedaco.strip()
    ]
    if not conversas:
        raise ConfigAusente(
            "CHATWOOT_CONVERSAS esta vazio no .env.\n"
            "Rode:  python tools/check_whatsapp.py conversas"
        )

    return ConfigChatwoot(
        url=env["CHATWOOT_URL"].rstrip("/"),
        conta=env["CHATWOOT_ACCOUNT"],
        token=env["CHATWOOT_TOKEN"],
        conversas=conversas,
    )
