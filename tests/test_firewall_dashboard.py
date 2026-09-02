"""VEND-1..3 — o firewall do arquivo de terceiro vendorizado do dashboard.

Este projeto passou quatro fases sem uma unica linha de codigo de terceiro na
arvore alem das distribuicoes do `requirements.txt`. O dashboard quebra isso:
`l2scanner/recursos/dashboard/vendor/` guarda uma biblioteca de grafico
minificada, que **executa no navegador do usuario**, na mesma maquina em que o
jogo roda e na mesma arvore em que mora o `.env` com o token do Chatwoot.

O `01-UI-SPEC.md`, secao `Registry Safety`, nao deixa isso entrar por confianca.
Ele converte o portao em quatro provas separadas e individualmente verificaveis
— e diz por extenso que **incompletas no momento do merge sao BLOCK**:

    VEND-1  proveniencia conferivel   -> `vendor/README.md`, e este modulo
    VEND-2  revisao do fonte escrita  -> `vendor/README.md`, e este modulo
    VEND-3  um teste que QUEBRA       -> este modulo
    VEND-4  a CSP no cabecalho        -> `l2scanner/dashboard.py`

**Por que o hash e a prova de VEND-1, e nao a URL.** Uma linha de README dizendo
"baixado de tal lugar" e declaratoria: ninguem consegue apontar onde ela falhou.
O SHA-256 recalculado sobre o arquivo em disco e conferivel — uma troca
silenciosa do `.min.js` (T-01-14) muda o byte, muda o hash, e derruba a suite.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
VENDOR = RAIZ / "l2scanner" / "recursos" / "dashboard" / "vendor"
README = VENDOR / "README.md"

# Onde a regra mora. A mensagem de falha aponta para ca.
DOCUMENTO_DA_REGRA = (
    ".planning/workstreams/dashboard/phases/"
    "01-dashboard-do-cambio-ao-vivo/01-UI-SPEC.md"
)

# As licencas que o UI-SPEC aceita para um artefato vendorizado. Copyleft foi
# RECUSADO por aquele documento, e por isso a lista e de tres itens e nao "as
# permissivas em geral": uma lista fechada e o que permite um teste dizer nao.
LICENCAS_PERMISSIVAS = {"MIT", "Apache-2.0", "ISC"}

# O ALCANCE da varredura, e o ponto em que este modulo pode se auto-anular.
#
# So arquivos de CODIGO e de ESTILO entram. O `README.md` fica de fora POR
# CONSTRUCAO — e nao por descuido — porque o VEND-2 EXIGE que ele cite as
# primitivas pelo nome na nota de revisao. Uma varredura ingenua sobre o
# diretorio inteiro acusaria o proprio documento que a regra manda escrever, e
# o conserto obvio (afrouxar a varredura) mataria o guarda.
#
# `uPlot.LICENSE` e `.gitattributes` tambem ficam de fora: nao sao executaveis,
# e o texto de uma licenca MIT nao roda no navegador de ninguem.
EXTENSOES_DE_CODIGO = (".js", ".mjs", ".cjs", ".css", ".ts")


def _arquivos_de_codigo_do_vendor() -> list[Path]:
    """Os arquivos vendorizados que EXECUTAM. Ver `EXTENSOES_DE_CODIGO`."""
    if not VENDOR.is_dir():
        return []
    return sorted(
        caminho
        for caminho in VENDOR.iterdir()
        if caminho.is_file() and caminho.suffix in EXTENSOES_DE_CODIGO
    )


def _sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# VEND-1 — a proveniencia e CONFERIVEL, e nao declaratoria
# ---------------------------------------------------------------------------


def test_o_sha256_do_README_bate_com_o_arquivo_EM_DISCO() -> None:
    """A unica assercao que torna VEND-1 conferivel em vez de declaratoria.

    O hash e calculado AQUI, sobre os bytes que estao no disco desta arvore, e
    exigido dentro do README. Nao ha como passar copiando um valor de documento
    de pesquisa: se o arquivo em disco for outro, o hash calculado e outro e a
    string nao aparece.

    E o guarda de T-01-14 (troca silenciosa do arquivo vendorizado): quem
    substituir o `.min.js` por uma versao com telemetria tem de tambem editar
    este README, e ai a substituicao deixa rastro no diff.
    """
    arquivos = _arquivos_de_codigo_do_vendor()
    # Sem esta linha, uma pasta vazia deixaria o laco abaixo verde por vacuidade
    # — o modo de falha mais caro que um controle destes tem. O teste dedicado a
    # isso esta em `test_a_varredura_enumerou_ao_menos_UM_arquivo`.
    assert arquivos, f"{VENDOR} nao tem arquivo de codigo nenhum"

    texto = README.read_text(encoding="utf-8")
    for arquivo in arquivos:
        digest = _sha256(arquivo)
        assert digest in texto, (
            f"O SHA-256 de {arquivo.name} NAO esta registrado em "
            f"{README.relative_to(RAIZ)}.\n"
            f"\n"
            f"Calculado agora, sobre os bytes em disco: {digest}\n"
            f"\n"
            f"Ou o arquivo vendorizado foi trocado sem que a proveniencia "
            f"fosse atualizada — que e exatamente a troca silenciosa que o "
            f"VEND-1 existe para tornar visivel — ou o README foi escrito com "
            f"o hash de outra origem em vez do recalculado.\n"
            f"\n"
            f"Ver a secao `Registry Safety` de {DOCUMENTO_DA_REGRA}."
        )


def test_o_README_nomeia_a_versao_e_uma_licenca_PERMISSIVA() -> None:
    """Versao exata e licenca sao campos do VEND-1, e a licenca e fechada.

    "MIT" nao esta aqui por gosto: o UI-SPEC recusa copyleft por escrito. Uma
    atualizacao futura que trocasse a biblioteca por uma GPL passaria batida se
    este teste aceitasse "qualquer licenca declarada".
    """
    texto = README.read_text(encoding="utf-8")
    assert "1.6.32" in texto, "o README nao nomeia a versao exata da biblioteca"

    declaradas = {nome for nome in LICENCAS_PERMISSIVAS if nome in texto}
    assert declaradas, (
        f"O README nao declara nenhuma das licencas que o UI-SPEC aceita "
        f"({', '.join(sorted(LICENCAS_PERMISSIVAS))}). Copyleft foi RECUSADO "
        f"por aquele documento — ver {DOCUMENTO_DA_REGRA}."
    )
    assert "MIT" in declaradas


def test_o_texto_da_licenca_esta_na_arvore_e_NAO_esta_vazio() -> None:
    """A licenca acompanha o codigo, que e a obrigacao que a MIT impoe.

    Um arquivo de licenca vazio (ou um download que falhou devolvendo 0 byte)
    satisfaria "o arquivo existe" e nao satisfaria nada do que a licenca pede.
    """
    licenca = VENDOR / "uPlot.LICENSE"
    assert licenca.is_file(), f"{licenca} nao existe"
    texto = licenca.read_text(encoding="utf-8")
    assert "Copyright" in texto, "o texto da licenca nao traz aviso de copyright"
    assert "MIT" in texto


def test_o_README_registra_a_proveniencia_BYTES_URL_e_DATA() -> None:
    """Os campos restantes do VEND-1, conferidos contra o disco.

    O tamanho em bytes e o campo que se confere A OLHO: um hash diferente diz
    "mudou", um tamanho de 197 KB onde deveria haver 51 KB diz O QUE mudou.
    """
    texto = README.read_text(encoding="utf-8")
    for arquivo in (*_arquivos_de_codigo_do_vendor(), VENDOR / "uPlot.LICENSE"):
        tamanho = str(arquivo.stat().st_size)
        assert tamanho in texto, (
            f"O README nao registra o tamanho de {arquivo.name} "
            f"({tamanho} bytes em disco agora)."
        )
        assert arquivo.name in texto, f"o README nao nomeia {arquivo.name}"

    assert "https://cdn.jsdelivr.net/npm/uplot@1.6.32/" in texto, (
        "o README nao registra a URL de origem — sem ela nao ha como refazer "
        "o download e reconferir o hash (VEND-1, campo de proveniencia)"
    )
    assert "2026-09-01" in texto, "o README nao registra a data do download"
