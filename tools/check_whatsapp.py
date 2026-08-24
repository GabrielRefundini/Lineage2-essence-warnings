"""Ferramenta do gate de entrega (DELV-01, DELV-02, DELV-03).

Responde tres perguntas, nesta ordem, antes de qualquer codigo de deteccao existir:

  1. Qual provedor de WhatsApp esta por tras do inbox?   -> comando `inboxes`
  2. Para onde os alertas vao?                            -> comando `conversas`
  3. Uma mensagem iniciada por nos chega mesmo no celular? -> comando `enviar`

ARMADILHA DO TESTE (importante): na API oficial da Meta, mandar uma mensagem
para o numero ANTES de testar abre a janela de 24h e faz o teste passar por
engano. Com um bridge nao-oficial (Baileys, Evolution, WAHA) a regra nao existe
e o teste e direto. O comando `inboxes` diz em qual caso voce esta.

Uso:
    python tools/check_whatsapp.py inboxes
    python tools/check_whatsapp.py conversas
    python tools/check_whatsapp.py enviar
    python tools/check_whatsapp.py enviar --texto "mensagem customizada"

O token e lido do arquivo .env e nunca e impresso nem gravado em log.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_ENV = RAIZ / ".env"

TIMEOUT_CONEXAO = 10

# O Chatwoot pode estar atras do Cloudflare, e o User-Agent padrao do urllib
# ("Python-urllib/3.x") e barrado pela verificacao de integridade de navegador
# com erro 1010. Um User-Agent normal resolve — nao e disfarce, e so nao se
# anunciar como script para um filtro que barra scripts por padrao.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# O que decide se mensagem livre e permitida NAO e o channel_type, e o PROVIDER.
#
# Descoberto na pratica: o fork fazer-ai/chatwoot usa `Channel::Whatsapp` com
# `provider: baileys`. Olhar so o channel_type classificava um bridge
# nao-oficial como se fosse a Cloud API da Meta, e o veredito saia invertido —
# dizia que o projeto precisava de template aprovado quando nao precisava.
PROVIDERS_NAO_OFICIAIS = {
    "baileys": "Baileys",
    "evolution": "Evolution API",
    "waha": "WAHA",
    "wppconnect": "WPPConnect",
    "unoapi": "UnoAPI",
}

PROVIDERS_OFICIAIS = {
    "default": "Cloud API oficial da Meta",
    "whatsapp_cloud": "WhatsApp Cloud API (Meta)",
    "360dialog": "360dialog",
    "twilio": "Twilio",
}

CANAIS_LIVRES = {
    "Channel::Api": "Canal API generico",
    "Channel::WebWidget": "Widget de site",
    "Channel::TelegramBot": "Telegram",
}


def classificar(inbox: dict) -> tuple[str, bool | None]:
    """Devolve (rotulo legivel, mensagem livre permitida?).

    `None` na segunda posicao significa "nao catalogado, confira a mao".
    """
    tipo = inbox.get("channel_type", "?")
    provider = (inbox.get("provider") or "").lower()

    if tipo == "Channel::Whatsapp":
        if provider in PROVIDERS_NAO_OFICIAIS:
            return (
                f"WhatsApp via {PROVIDERS_NAO_OFICIAIS[provider]} "
                f"(bridge nao-oficial)",
                True,
            )
        if provider in PROVIDERS_OFICIAIS:
            return f"WhatsApp via {PROVIDERS_OFICIAIS[provider]}", False
        if not provider:
            return "WhatsApp (provider nao informado — assumindo oficial)", False
        return f"WhatsApp via '{provider}' (provider nao catalogado)", None

    if tipo in CANAIS_LIVRES:
        return CANAIS_LIVRES[tipo], True

    return tipo, None


class ErroDeConfig(Exception):
    """Falta configuracao ou ela esta invalida."""


class ErroDeApi(Exception):
    """A API do Chatwoot respondeu com erro."""


def carregar_env() -> dict[str, str]:
    """Le o .env sem depender de biblioteca externa."""
    if not ARQUIVO_ENV.exists():
        raise ErroDeConfig(
            f"Nao encontrei {ARQUIVO_ENV}.\n"
            f"Copie ENV-EXEMPLO.txt para .env e preencha os seus dados."
        )

    valores: dict[str, str] = {}
    for linha in ARQUIVO_ENV.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        valores[chave.strip()] = valor.strip().strip('"').strip("'")

    faltando = [
        c for c in ("CHATWOOT_URL", "CHATWOOT_ACCOUNT", "CHATWOOT_TOKEN")
        if not valores.get(c)
    ]
    if faltando:
        raise ErroDeConfig(
            "Faltam valores no .env: " + ", ".join(faltando)
        )

    if valores["CHATWOOT_TOKEN"] == "cole_seu_token_aqui":
        raise ErroDeConfig("O CHATWOOT_TOKEN ainda esta com o valor de exemplo.")

    valores["CHATWOOT_URL"] = valores["CHATWOOT_URL"].rstrip("/")
    return valores


def chamar_api(
    env: dict[str, str],
    caminho: str,
    metodo: str = "GET",
    corpo: dict | None = None,
) -> object:
    """Faz uma chamada a API do Chatwoot.

    O token vai no header `api_access_token` — plano, sem prefixo Bearer.
    Nenhuma mensagem de erro daqui inclui o token.
    """
    url = f"{env['CHATWOOT_URL']}/api/v1/accounts/{env['CHATWOOT_ACCOUNT']}{caminho}"

    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    req = urllib.request.Request(url, data=dados, method=metodo)
    req.add_header("api_access_token", env["CHATWOOT_TOKEN"])
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_CONEXAO) as resposta:
            texto = resposta.read().decode("utf-8")
            return json.loads(texto) if texto else None
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode("utf-8", errors="replace")[:400]
        if erro.code == 401:
            raise ErroDeApi(
                "401 - token rejeitado. Confira o CHATWOOT_TOKEN no .env "
                "(deve ser o access token do seu perfil de usuario)."
            ) from erro
        if erro.code == 403 and "1010" in detalhe:
            raise ErroDeApi(
                "403 do Cloudflare (codigo 1010): a requisicao foi barrada "
                "antes de chegar no Chatwoot. Se persistir, libere o IP desta "
                "maquina nas regras do Cloudflare, ou desative a verificacao "
                "de integridade de navegador para o caminho /api/."
            ) from erro
        if erro.code == 404:
            raise ErroDeApi(
                f"404 - nao encontrado: {caminho}\n"
                f"Confira o CHATWOOT_ACCOUNT (numero da conta) no .env."
            ) from erro
        raise ErroDeApi(f"HTTP {erro.code} em {caminho}: {detalhe}") from erro
    except urllib.error.URLError as erro:
        raise ErroDeApi(
            f"Nao consegui falar com {env['CHATWOOT_URL']}: {erro.reason}\n"
            f"Confira o CHATWOOT_URL e se a VPS esta acessivel daqui."
        ) from erro


def cmd_inboxes(env: dict[str, str]) -> int:
    """DELV-01: identifica o provedor de WhatsApp por tras de cada inbox."""
    resposta = chamar_api(env, "/inboxes")
    inboxes = resposta.get("payload", []) if isinstance(resposta, dict) else []

    if not inboxes:
        print("Nenhum inbox encontrado nesta conta.")
        return 1

    print(f"\n{len(inboxes)} inbox(es) encontrado(s):\n")

    algum_livre = False
    for inbox in inboxes:
        rotulo, livre = classificar(inbox)
        provider = inbox.get("provider") or "-"
        print(f"  [{inbox.get('id')}] {inbox.get('name')}")
        print(f"       tipo: {inbox.get('channel_type')}  |  provider: {provider}")
        print(f"       ou seja: {rotulo}")

        if livre is True:
            print("       -> mensagem livre PERMITIDA, sem janela de 24h, grupo funciona")
            algum_livre = True
        elif livre is False:
            print("       -> ATENCAO: fora da janela de 24h exige TEMPLATE aprovado;")
            print("          o Chatwoot aceita o envio e a Meta descarta em silencio.")
            print("          Envio para grupo tambem nao e viavel neste caminho.")
        else:
            print("       -> tipo nao catalogado; verifique manualmente")
        print()

    if algum_livre:
        print("Veredito do gate: existe pelo menos um caminho de mensagem livre.")
        print("O scanner pode alertar a qualquer hora, com o pessoal AFK.\n")
    else:
        print("Veredito do gate: NENHUM caminho de mensagem livre.")
        print("Sera preciso template aprovado, ou trocar de canal.\n")
    return 0


def cmd_conversas(env: dict[str, str]) -> int:
    """Lista conversas para o usuario escolher os destinos dos alertas."""
    resposta = chamar_api(env, "/conversations")

    if isinstance(resposta, dict):
        carga = resposta.get("data", resposta)
        conversas = carga.get("payload", []) if isinstance(carga, dict) else []
    else:
        conversas = []

    if not conversas:
        print("Nenhuma conversa encontrada.")
        print("Abra uma conversa no WhatsApp com o numero/grupo de destino")
        print("e rode este comando de novo.")
        return 1

    print(f"\n{len(conversas)} conversa(s):\n")
    for conversa in conversas:
        meta = conversa.get("meta", {})
        contato = meta.get("sender", {}) or {}
        nome = contato.get("name") or "(sem nome)"
        telefone = contato.get("phone_number") or ""
        print(f"  ID {conversa.get('id'):<6} {nome} {telefone}")

    print("\nCopie os IDs que voce quer avisar para o CHATWOOT_CONVERSAS no .env,")
    print("separados por virgula. Ex.:  CHATWOOT_CONVERSAS=12,34\n")
    return 0


def cmd_enviar(env: dict[str, str], texto: str) -> int:
    """DELV-02: envia uma mensagem de teste iniciada por nos."""
    brutos = env.get("CHATWOOT_CONVERSAS", "")
    ids = [pedaco.strip() for pedaco in brutos.split(",") if pedaco.strip()]

    if not ids:
        print("CHATWOOT_CONVERSAS esta vazio no .env.")
        print("Rode primeiro:  python tools/check_whatsapp.py conversas")
        return 1

    print(f"\nEnviando para {len(ids)} conversa(s)...\n")

    falhas = 0
    for id_conversa in ids:
        try:
            chamar_api(
                env,
                f"/conversations/{id_conversa}/messages",
                metodo="POST",
                corpo={"content": texto, "message_type": "outgoing"},
            )
            print(f"  conversa {id_conversa}: aceita pelo Chatwoot")
        except ErroDeApi as erro:
            print(f"  conversa {id_conversa}: FALHOU - {erro}")
            falhas += 1

    print()
    if falhas:
        print(f"{falhas} envio(s) falharam.\n")
        return 1

    print("=" * 62)
    print("O Chatwoot aceitou. Isso NAO e confirmacao de entrega.")
    print("Va ate o celular de destino e confirme que a mensagem chegou.")
    print("So o celular fecha o gate — resposta 200 nao prova nada.")
    print("=" * 62 + "\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gate de entrega do L2 Party Scanner (Fase 1)."
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("inboxes", help="descobre o provedor de WhatsApp de cada inbox")
    sub.add_parser("conversas", help="lista conversas e seus IDs")

    p_enviar = sub.add_parser("enviar", help="envia uma mensagem de teste")
    p_enviar.add_argument(
        "--texto",
        default=(
            "Teste do L2 Party Scanner. Se voce recebeu isso sem ter falado "
            "comigo antes, o caminho de alerta esta funcionando."
        ),
        help="texto da mensagem de teste",
    )

    args = parser.parse_args()

    try:
        env = carregar_env()
    except ErroDeConfig as erro:
        print(f"\n{erro}\n", file=sys.stderr)
        return 2

    try:
        if args.comando == "inboxes":
            return cmd_inboxes(env)
        if args.comando == "conversas":
            return cmd_conversas(env)
        if args.comando == "enviar":
            return cmd_enviar(env, args.texto)
    except ErroDeApi as erro:
        print(f"\n{erro}\n", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
