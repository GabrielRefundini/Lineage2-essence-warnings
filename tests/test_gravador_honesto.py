"""Testes do gravador honesto: so conta o que o disco confirmou.

O `Gravador` jogava fora o retorno de `cv2.imwrite` e incrementava o contador na
TENTATIVA. Quando a escrita falhava, tres coisas mentiam juntas: o contador de
frames, a linha do `observacoes.jsonl` citando um arquivo inexistente, e o
resumo final da sessao.

Isso importa mais do que parece. As gravacoes sao a base de calibracao e o
material de regressao do projeto — evidencia nao-confirmada e o pesadelo
documentado desta casa. Uma sessao que diz "118 frames gravados" e tem 40 PNGs
no disco desperdica o tempo do usuario duas vezes: uma gravando, outra
descobrindo tarde.

Estes testes prendem o contrato: escrita confirmada e o portao das TRES saidas
(contador, JSONL, resumo), a falha aparece como erro ALTO, e nada disso levanta
excecao — `gravar` roda dentro de `Sessao.tick`, que nao tem try/except no laco
principal, entao levantar por disco cheio derrubaria os alertas de morte da
party junto.
"""

from __future__ import annotations

import inspect
import json
import logging
import threading
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pytest

from l2scanner.__main__ import alarme_de_divergencia, montar_gravador
from l2scanner.captura_janela import JanelaSource
from l2scanner.frames import Frame, Regiao, SaudeDoFrame, _ClassificadorDeSaude
from l2scanner.gravador import FALHAS_ENTRE_GRITOS, Gravador

# A janela do jogo do usuario, medida em recordings/inv3/f000_JANELA.png.
# O recorte da party window, que e o que o --record de hoje grava, mede
# 172x522 — as duas formas juntas sao o que torna o teste do modo janela
# capaz de distinguir "gravou a janela" de "gravou o recorte de sempre".
ALTURA_DA_JANELA, LARGURA_DA_JANELA = 1392, 1720
ALTURA_DA_PARTY, LARGURA_DA_PARTY = 522, 172


def _frame(indice: int, altura: int = 20, largura: int = 30) -> Frame:
    """Um frame qualquer, so para ter pixels validos para gravar.

    O desenho nunca importa nestes testes: o que se afirma e a contagem, o
    indice no JSONL e a mensagem de erro — nunca o conteudo da imagem.
    """
    pixels = np.full((altura, largura, 3), 40 + (indice % 100), dtype=np.uint8)
    return Frame(pixels=pixels, indice=indice, saude=SaudeDoFrame.OK)


def _linhas_do_jsonl(pasta: Path) -> list[dict]:
    texto = (pasta / "observacoes.jsonl").read_text(encoding="utf-8")
    return [json.loads(linha) for linha in texto.splitlines() if linha.strip()]


def _pngs_no_disco(pasta: Path) -> list[Path]:
    """A contagem independente, lida do disco.

    O `is_file` nao e preciosismo: a falha deterministica destes testes e um
    DIRETORIO com nome de PNG, e um glob cru o contaria como frame gravado —
    reintroduzindo a mentira dentro da propria conferencia.
    """
    return [caminho for caminho in pasta.glob("frame_*.png") if caminho.is_file()]


def _ocupar_o_nome_com_um_diretorio(pasta: Path, indice: int) -> None:
    """A falha deterministica que funciona em QUALQUER SO.

    O somente-leitura depende de permissoes que variam entre maquinas (o
    proprio `test_conferencia_gravada.py` precisa de um `pytest.skip` para
    ele). Um diretorio ocupando o nome do arquivo faz o `cv2.imwrite` falhar
    em todo lugar, sem depender de permissao nenhuma.
    """
    (pasta / f"frame_{indice:06d}.png").mkdir()


class _IndiceQueRecusaEscrita:
    """O `observacoes.jsonl` com o disco cheio, sem encher o disco de verdade.

    O `errno 28` nao e enfeite: disco cheio e o UNICO cenario que a docstring
    do `Gravador.gravar` nomeia, e era justamente por ele que o metodo
    levantava. O `cv2.imwrite` ja estava embrulhado; a escrita do indice, logo
    abaixo dele, nao estava — e como `Sessao.tick` chama `gravar` ANTES do seu
    proprio try/except e o laco principal nao envolve o tick em try nenhum, a
    excecao subia ate `main()` e levava os alertas de morte da party junto.
    """

    def __init__(self, real: object) -> None:
        self._real = real

    def write(self, _texto: str) -> int:
        raise OSError(28, "No space left on device")

    def flush(self) -> None:
        raise OSError(28, "No space left on device")

    def close(self) -> None:
        self._real.close()  # type: ignore[attr-defined]


def test_o_contrato_estrutural_do_gravador() -> None:
    """A assinatura e o contador de falhas existem antes de qualquer gravacao."""
    assert inspect.signature(Gravador.gravar).return_annotation == "bool", (
        "gravar precisa declarar que devolve bool — quem chama tem o direito "
        "de saber se a escrita foi confirmada"
    )


def test_o_caminho_feliz_conta_exatamente_o_que_esta_no_disco(tmp_path: Path) -> None:
    gravador = Gravador(tmp_path, "ok")
    assert gravador.falhas_de_gravacao == 0, "o contador de falhas nasce no __init__"

    for indice in range(3):
        assert gravador.gravar(_frame(indice), float(indice)) is True
    gravador.fechar()

    assert gravador.frames_gravados == 3
    assert gravador.falhas_de_gravacao == 0
    assert len(_pngs_no_disco(gravador.pasta)) == 3
    assert len(_linhas_do_jsonl(gravador.pasta)) == 3


def test_uma_escrita_que_falha_nao_conta_nem_indexa(tmp_path: Path) -> None:
    """O portao das tres saidas: nem contador, nem JSONL, nem resumo."""
    gravador = Gravador(tmp_path, "falha")
    _ocupar_o_nome_com_um_diretorio(gravador.pasta, 7)

    assert gravador.gravar(_frame(7), 7.0) is False
    gravador.fechar()

    assert gravador.frames_gravados == 0, "um frame nao escrito nao pode ser contado"
    assert gravador.falhas_de_gravacao == 1
    assert _linhas_do_jsonl(gravador.pasta) == [], (
        "consertar o contador e deixar a linha do JSONL sair e o pitfall 1: o "
        "indice passaria a citar um arquivo que nao existe"
    )


def test_toda_linha_do_jsonl_cita_um_arquivo_que_existe(tmp_path: Path) -> None:
    """Varredura do indice inteiro depois de uma sessao MISTA."""
    gravador = Gravador(tmp_path, "mista")
    _ocupar_o_nome_com_um_diretorio(gravador.pasta, 7)

    for indice in [0, 1, 2, 3, 4, 7, 8, 9, 10]:
        gravador.gravar(_frame(indice), float(indice))
    gravador.fechar()

    linhas = _linhas_do_jsonl(gravador.pasta)
    assert gravador.falhas_de_gravacao == 1
    assert gravador.frames_gravados == 8
    assert len(linhas) == gravador.frames_gravados
    assert gravador.frames_gravados == len(_pngs_no_disco(gravador.pasta))
    for linha in linhas:
        caminho = gravador.pasta / linha["arquivo"]
        assert caminho.is_file(), (
            f"o indice cita {linha['arquivo']}, que nao existe como arquivo "
            f"no disco"
        )


def test_a_falha_de_escrita_aparece_como_erro_alto(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Erro ALTO, com o caminho citado — um resumo silencioso nao serve.

    O usuario descobre disco cheio no meio de uma hora de farm ou nunca.
    """
    gravador = Gravador(tmp_path, "erro")
    _ocupar_o_nome_com_um_diretorio(gravador.pasta, 7)

    with caplog.at_level(logging.ERROR, logger="l2scanner.gravador"):
        gravador.gravar(_frame(7), 7.0)
    gravador.fechar()

    erros = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert erros, "uma falha de gravacao precisa produzir pelo menos um ERROR"
    assert any("frame_000007.png" in r.getMessage() for r in erros), (
        "o erro precisa citar o arquivo que falhou; sem o caminho o usuario "
        "nao consegue diagnosticar nada"
    )


def test_gravar_nunca_levanta_nem_quando_o_imwrite_explode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O `False` documentado e uma excecao inesperada caem no MESMO caminho.

    `Sessao.tick` chama `gravar` ANTES do seu proprio try/except, e o laco
    principal nao envolve o tick em try/except nenhum. Uma excecao aqui
    derrubaria o scanner inteiro — os alertas de morte da party morreriam
    junto com a feature de gravacao. A doutrina da casa e degradar a feature,
    nunca o produto.
    """
    import cv2

    def explodir(*_args: object, **_kwargs: object) -> bool:
        raise RuntimeError("o disco pegou fogo")

    monkeypatch.setattr(cv2, "imwrite", explodir)

    gravador = Gravador(tmp_path, "explosao")
    assert gravador.gravar(_frame(1), 1.0) is False
    assert gravador.gravar(_frame(2), 2.0) is False
    gravador.fechar()

    assert gravador.frames_gravados == 0
    assert gravador.falhas_de_gravacao == 2
    assert _linhas_do_jsonl(gravador.pasta) == []


def test_o_indice_que_recusa_a_linha_nao_derruba_o_scanner(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A metade que faltava do portao: o JSONL falha como o imwrite falha.

    Antes deste teste o `imwrite` estava embrulhado e a escrita do indice nao.
    Um `OSError(28)` na linha do `observacoes.jsonl` subia por `Sessao.tick`,
    passava pelo laco principal (que nao tem try) e derrubava o scanner
    inteiro — a feature de gravacao levando o produto junto, que e a inversao
    exata da doutrina da casa.
    """
    gravador = Gravador(tmp_path, "disco-cheio")
    gravador._arquivo_meta = _IndiceQueRecusaEscrita(gravador._arquivo_meta)

    with caplog.at_level(logging.ERROR, logger="l2scanner.gravador"):
        assert gravador.gravar(_frame(3), 3.0) is False
    gravador.fechar()

    assert gravador.frames_gravados == 0, "um frame sem linha no indice nao existe"
    assert gravador.falhas_de_gravacao == 1, (
        "o contador que existe para nunca mentir reportava ZERO falhas para um "
        "frame perdido: a falha nem chegava a `_contabilizar_falha`"
    )
    assert [r for r in caplog.records if r.levelno >= logging.ERROR], (
        "sem ERROR o usuario farma uma hora sem saber que nada foi gravado"
    )


def test_a_linha_que_falha_nao_deixa_png_orfao_no_disco(tmp_path: Path) -> None:
    """O PNG sai junto com a linha que nao entrou.

    O PNG e escrito ANTES da linha do indice. Deixar o arquivo la depois de a
    linha falhar cria um orfao, e a conferencia 4 de
    `tools/conferir_gravacoes_do_spike.py` (linhas do JSONL == PNGs no disco)
    condenaria a sessao INTEIRA — "Regrave este cenario" — por causa de um
    unico solucar de metadado. As oito sessoes do spike sao irrecuperaveis;
    condenar uma delas por um orfao e caro demais.
    """
    gravador = Gravador(tmp_path, "orfao")
    gravador._arquivo_meta = _IndiceQueRecusaEscrita(gravador._arquivo_meta)

    gravador.gravar(_frame(3), 3.0)
    gravador.fechar()

    assert _pngs_no_disco(gravador.pasta) == [], (
        "o PNG ficou no disco sem linha no indice — o disco e o indice "
        "passaram a discordar, que e a mentira que este modulo veio fechar"
    )
    assert _linhas_do_jsonl(gravador.pasta) == []


def test_o_indice_que_falha_sempre_respeita_o_throttle_de_gritos(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """`FALHAS_ENTRE_GRITOS` precisa valer para ESTA classe de falha tambem.

    O throttle so dispara de dentro de `_contabilizar_falha`. Enquanto a falha
    do indice levantava, ela nunca passava por la: a 1 Hz com o disco cheio o
    caminho era derrubar o scanner na primeira volta, e nao gritar uma vez e
    depois a cada dez.
    """
    gravador = Gravador(tmp_path, "throttle")
    gravador._arquivo_meta = _IndiceQueRecusaEscrita(gravador._arquivo_meta)

    with caplog.at_level(logging.DEBUG, logger="l2scanner.gravador"):
        for indice in range(12):
            assert gravador.gravar(_frame(indice), float(indice)) is False
    gravador.fechar()

    assert gravador.falhas_de_gravacao == 12
    gritos = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(gritos) == 2, (
        f"esperava gritar na 1a e na 10a falha (FALHAS_ENTRE_GRITOS={FALHAS_ENTRE_GRITOS}), "
        f"gritou {len(gritos)} vez(es)"
    )


# -- modo janela completa (--record-janela) ---------------------------------
#
# O `--record` de hoje salva SO `frame.pixels`, o recorte da party window. Uma
# sessao gravada assim nao contem um unico pixel do painel do mercado, o que
# torna o spike de campo impossivel por construcao. O modo janela existe para
# resolver o ovo-e-galinha: a regiao do mercado so sera conhecida DEPOIS da
# calibracao, e a calibracao roda sobre frames GRAVADOS.


def _party() -> Frame:
    pixels = np.full(
        (ALTURA_DA_PARTY, LARGURA_DA_PARTY, 3), 40, dtype=np.uint8
    )
    return Frame(pixels=pixels, indice=0, saude=SaudeDoFrame.OK)


def test_o_modo_janela_grava_a_janela_completa_e_nao_o_recorte(
    tmp_path: Path,
) -> None:
    completa = np.full(
        (ALTURA_DA_JANELA, LARGURA_DA_JANELA, 3), 90, dtype=np.uint8
    )
    gravador = Gravador(tmp_path, "janela", fonte_completa=lambda: completa)

    assert gravador.gravar(_party(), 0.0) is True
    gravador.fechar()

    gravados = _pngs_no_disco(gravador.pasta)
    assert len(gravados) == 1
    imagem = cv2.imread(str(gravados[0]))
    assert imagem.shape == (ALTURA_DA_JANELA, LARGURA_DA_JANELA, 3), (
        "o PNG precisa ser a janela inteira; com o shape do recorte da party "
        "o painel do mercado nunca entraria na gravacao"
    )


def test_a_janela_sem_frame_falha_fechada_em_vez_de_gravar_o_recorte(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Nunca cair de volta em `frame.pixels`.

    Gravar o recorte errado em silencio gastaria as sessoes do usuario, que
    sao o recurso escasso desta fase: so ele pode grava-las, e ele so
    descobriria o engano depois de gastar as oito.
    """
    gravador = Gravador(tmp_path, "janela-vazia", fonte_completa=lambda: None)

    with caplog.at_level(logging.ERROR, logger="l2scanner.gravador"):
        assert gravador.gravar(_party(), 0.0) is False
    gravador.fechar()

    assert gravador.frames_gravados == 0
    assert gravador.falhas_de_gravacao == 1
    assert _pngs_no_disco(gravador.pasta) == [], (
        "nenhum consolo: o recorte da party nao pode ser gravado no lugar"
    )
    assert _linhas_do_jsonl(gravador.pasta) == []
    assert [r for r in caplog.records if r.levelno >= logging.ERROR]


def test_sem_fonte_completa_o_comportamento_e_o_de_hoje(tmp_path: Path) -> None:
    """Compatibilidade do `--record` atual, byte a byte de forma."""
    gravador = Gravador(tmp_path, "compat")

    assert gravador.gravar(_party(), 0.0) is True
    gravador.fechar()

    imagem = cv2.imread(str(_pngs_no_disco(gravador.pasta)[0]))
    assert imagem.shape == (ALTURA_DA_PARTY, LARGURA_DA_PARTY, 3)


# -- duas sessoes no mesmo segundo nao se destroem ---------------------------


class _RelogioParado:
    """`datetime.now()` cravado, para os dois gravadores colidirem sempre.

    Sem isto o teste dependeria de os dois `Gravador` nascerem dentro do mesmo
    segundo de parede — verdadeiro quase sempre, e por isso um teste que
    falharia sozinho de vez em quando.
    """

    @staticmethod
    def now() -> datetime:
        return datetime(2026, 8, 27, 10, 15, 0)


def test_duas_sessoes_no_mesmo_segundo_nao_compartilham_pasta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O `--rotulo` do roteiro e fixo, e o carimbo tem resolucao de 1 segundo.

    Duas instancias do scanner (que este projeto suporta de proposito) ou um
    duplo-clique no `.bat` caiam na MESMA pasta: o segundo gravador abria o
    `observacoes.jsonl` em `"w"` e truncava o indice do primeiro para zero,
    enquanto os PNGs dele seguiam no disco. Os dois entao escreviam
    `frame_000000.png` por cima um do outro, cada um confiando no proprio
    contador, e ninguem reportava nada.
    """
    import l2scanner.gravador as modulo

    monkeypatch.setattr(modulo, "datetime", _RelogioParado)

    primeiro = Gravador(tmp_path, "mercado-aberto")
    for indice in range(3):
        assert primeiro.gravar(_frame(indice), float(indice)) is True

    segundo = Gravador(tmp_path, "mercado-aberto")
    assert segundo.pasta != primeiro.pasta, (
        "o segundo gravador reutilizou a pasta do primeiro e truncou o indice "
        "dele — uma sessao do spike destruida em silencio"
    )

    assert segundo.gravar(_frame(0), 0.0) is True
    primeiro.fechar()
    segundo.fechar()

    # O primeiro sobreviveu inteiro.
    assert len(_linhas_do_jsonl(primeiro.pasta)) == 3
    assert len(_pngs_no_disco(primeiro.pasta)) == 3
    assert primeiro.frames_gravados == 3
    # E o segundo tem so o que ele proprio gravou.
    assert len(_linhas_do_jsonl(segundo.pasta)) == 1
    assert len(_pngs_no_disco(segundo.pasta)) == 1


def test_a_pasta_da_colisao_continua_visivel_para_o_portao_do_spike(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O sufixo entra no MEIO, nunca no fim.

    `pastas_do_sufixo` em `tools/conferir_gravacoes_do_spike.py` procura por
    `*-{rotulo}`. Um nome terminando em `-1` deixaria a gravacao invisivel para
    o portao: a sessao existiria no disco e o conferidor diria que o cenario
    nao foi gravado — trocar um modo de perda silenciosa por outro.
    """
    import l2scanner.gravador as modulo

    monkeypatch.setattr(modulo, "datetime", _RelogioParado)

    primeiro = Gravador(tmp_path, "mercado-aberto")
    segundo = Gravador(tmp_path, "mercado-aberto")
    primeiro.fechar()
    segundo.fechar()

    assert segundo.pasta.name.endswith("-mercado-aberto"), (
        f"{segundo.pasta.name} nao termina no rotulo: o glob `*-mercado-aberto` "
        f"do portao do spike nao encontraria esta sessao"
    )
    encontradas = sorted(p.name for p in tmp_path.glob("*-mercado-aberto"))
    assert encontradas == sorted([primeiro.pasta.name, segundo.pasta.name])


def test_sem_rotulo_a_colisao_tambem_e_resolvida(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import l2scanner.gravador as modulo

    monkeypatch.setattr(modulo, "datetime", _RelogioParado)

    primeiro = Gravador(tmp_path)
    segundo = Gravador(tmp_path)
    primeiro.fechar()
    segundo.fechar()

    assert primeiro.pasta != segundo.pasta


# -- um gravador que nao monta nao derruba o produto --------------------------
#
# `Gravador.__init__` faz `mkdir` e `open`, e era construido fora de qualquer
# try. `main()` so pega `JanelaNaoEncontrada` e `ConfiguracaoPerigosa`, entao um
# `recordings/` somente-leitura, um disco cheio ou um ARQUIVO ocupando o nome
# `recordings` produziam um traceback cru e nenhum scanner. Gravar e a feature
# mais opcional do projeto e era a unica capaz de impedir o produto de subir —
# a inversao da doutrina que o proprio `__main__.py` enuncia duas vezes, em
# `montar_despachante` e `montar_vigia_de_manutencao`.


class _ArgsDeGravacao:
    def __init__(self, record: bool = True, record_janela: bool = False) -> None:
        self.record = record
        self.record_janela = record_janela
        self.rotulo = "mercado-aberto"


def test_um_recordings_que_nao_da_para_criar_nao_derruba_o_scanner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Um ARQUIVO ocupando o nome `recordings` — falha deterministica em todo SO.

    Mesmo padrao do diretorio-com-nome-de-PNG usado acima: nao depende de
    permissao, que varia entre maquinas.
    """
    import l2scanner.__main__ as principal

    ocupado = tmp_path / "recordings"
    ocupado.write_text("nao sou uma pasta", encoding="utf-8")
    monkeypatch.setattr(principal, "PASTA_GRAVACOES", ocupado)

    with caplog.at_level(logging.ERROR, logger="l2scanner.__main__"):
        gravador = montar_gravador(_ArgsDeGravacao(), fonte=None)

    assert gravador is None, "a gravacao desliga; o scanner segue"
    erros = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert erros, "sair calado faria o usuario farmar 60 segundos para nada"
    assert any("GRAVACAO DESATIVADA" in r.getMessage() for r in erros)
    assert any(
        "continua igual" in r.getMessage() for r in erros
    ), "o log precisa dizer que morte, saida e ressurreicao seguem valendo"


def test_sem_record_o_gravador_nem_e_construido(tmp_path: Path) -> None:
    assert montar_gravador(_ArgsDeGravacao(record=False), fonte=None) is None


def test_o_gravador_montado_usa_a_janela_do_frame_atual(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fiacao do CR-02, presa no ponto onde ela e feita.

    `capturar_completo` le `_ultimo` DE NOVO e devolve um frame mais novo que o
    da volta corrente. Se alguem religar o parametro nele, o PNG volta a nao
    ser a imagem de onde saiu a linha do indice — e nada quebraria.
    """
    import l2scanner.__main__ as principal

    monkeypatch.setattr(principal, "PASTA_GRAVACOES", tmp_path / "recordings")
    regiao = Regiao(
        esquerda=0, topo=0, largura=LARGURA_DA_PARTY, altura=ALTURA_DA_PARTY
    )
    fonte = _janela_de_mentira(
        np.full((ALTURA_DA_JANELA, LARGURA_DA_JANELA, 3), 77, dtype=np.uint8),
        regiao,
    )

    gravador = montar_gravador(
        _ArgsDeGravacao(record_janela=True), fonte=fonte
    )
    assert gravador is not None
    gravador.fechar()

    assert gravador._fonte_completa == fonte.completo_do_frame_atual
    assert gravador._fonte_completa != fonte.capturar_completo


# -- o resumo final compara os dois numeros que imprime -----------------------


def test_o_resumo_acusa_quando_o_contador_e_o_disco_discordam() -> None:
    """118 contados e 40 no disco nao pode sair em INFO.

    O bloco de encerramento calculava `no_disco` certinho, imprimia os dois
    numeros lado a lado e nunca os comparava: a severidade saia SO de
    `falhas_de_gravacao`. Imprimir dois numeros lado a lado so e uma
    conferencia se alguma coisa ler os dois.
    """
    assert alarme_de_divergencia(118, 40), (
        "o cenario que abre a docstring deste modulo precisa disparar alarme"
    )
    assert "DIVERGIU" in alarme_de_divergencia(118, 40)
    assert "nao confie nesta sessao" in alarme_de_divergencia(118, 40)


def test_o_resumo_fica_calado_quando_os_numeros_fecham() -> None:
    """Sem isto, o jeito facil de passar seria alarmar sempre."""
    assert alarme_de_divergencia(0, 0) == ""
    assert alarme_de_divergencia(40, 40) == ""


def test_o_alarme_dispara_para_os_dois_lados_da_divergencia() -> None:
    """Sobrar PNG no disco tambem e divergir.

    Depois do fix do CR-01 um PNG orfao e descartado, mas um `--record` de uma
    sessao anterior na mesma pasta (ou uma escrita que o SO completou depois da
    falha) ainda pode deixar arquivo a mais. O contador nunca e a autoridade.
    """
    assert alarme_de_divergencia(40, 41)
    assert alarme_de_divergencia(41, 40)


# -- UMA captura por volta ---------------------------------------------------
#
# O PNG e a linha do indice que o descreve precisam sair do MESMO array. O laco
# capturava uma vez para o `Frame` (de onde saem `saude`, `indice` e `momento`)
# e a gravacao lia `_ultimo` DE NOVO, com um round-trip HTTP no Chatwoot no
# meio e a thread da WGC trocando o buffer a ~38 fps. O PNG no disco ficava
# rotineiramente dezenas a centenas de milissegundos mais novo que os pixels
# que produziram o `saude` gravado ao lado dele.
#
# Isso e um buraco de reprodutibilidade no artefato que a fase inteira existe
# para produzir: a gravacao e a "base de calibracao e teste de regressao
# permanente", e reproduzir `frame_NNNNNN.png` nao devolvia o `saude` que o
# indice afirma para ele, porque o valor veio de outra imagem.


def _janela_de_mentira(completo: np.ndarray, regiao: Regiao) -> JanelaSource:
    """Uma `JanelaSource` sem jogo aberto, sem WGC e sem hwnd.

    `__init__` abre a captura de verdade e espera o primeiro frame, o que exige
    o cliente rodando. O que este teste precisa exercitar e so o par
    `capturar()` / `completo_do_frame_atual()` — codigo de producao, nao um
    dublê —, entao montamos o objeto com exatamente os campos que esse par le.
    `relativa=True` e o que dispensa o hwnd: a regiao ja esta em coordenadas do
    canto da janela.
    """
    fonte = JanelaSource.__new__(JanelaSource)
    fonte._trava = threading.Lock()
    fonte._ultimo = completo
    fonte._completo_do_ultimo_frame = None
    fonte._relativa = True
    fonte._regiao = regiao
    fonte._extras = {}
    fonte._saude = _ClassificadorDeSaude()
    fonte._contador = 0
    return fonte


def test_o_png_gravado_e_a_janela_que_produziu_a_linha_do_indice(
    tmp_path: Path,
) -> None:
    """O PNG e o indice saem do MESMO array, mesmo com frame novo no meio."""
    regiao = Regiao(
        esquerda=10, topo=20, largura=LARGURA_DA_PARTY, altura=ALTURA_DA_PARTY
    )
    janela_do_frame = np.full(
        (ALTURA_DA_JANELA, LARGURA_DA_JANELA, 3), 111, dtype=np.uint8
    )
    fonte = _janela_de_mentira(janela_do_frame, regiao)

    frame = fonte.capturar()

    # A thread da WGC entrega ~38 fps, e entre o `capturar()` do laco e o
    # `gravar()` ainda cabe o round-trip HTTP do Chatwoot em
    # `atender_comandos`. Aqui isso vira uma linha.
    janela_mais_nova = np.full(
        (ALTURA_DA_JANELA, LARGURA_DA_JANELA, 3), 222, dtype=np.uint8
    )
    with fonte._trava:
        fonte._ultimo = janela_mais_nova

    # A prova de que o defeito era real e nao teorico: a fonte JA tem um frame
    # diferente para entregar a quem perguntar de novo.
    assert np.array_equal(fonte.capturar_completo(), janela_mais_nova)

    gravador = Gravador(
        tmp_path, "mesmo-frame", fonte_completa=fonte.completo_do_frame_atual
    )
    assert gravador.gravar(frame, 0.0) is True
    gravador.fechar()

    gravado = cv2.imread(str(_pngs_no_disco(gravador.pasta)[0]))
    assert np.array_equal(gravado, janela_do_frame), (
        "o PNG gravado nao e a janela que produziu `frame.pixels`: a linha do "
        "indice descreve (saude, momento, indice) uma imagem que nao esta no "
        "arquivo que ela nomeia"
    )
    assert not np.array_equal(gravado, janela_mais_nova)


def test_a_falha_de_captura_nao_deixa_a_gravacao_com_um_frame_velho(
    tmp_path: Path,
) -> None:
    """Fail-closed nas DUAS metades, e nao so na de cima.

    `capturar()` devolvendo FALHA_DE_CAPTURA enquanto a gravacao escrevia um
    PNG perfeito (lido de um `_ultimo` que nunca e limpo) era o pior par
    possivel: um frame marcado como cego no indice, com uma imagem boa e
    ANTIGA ao lado. Agora as duas metades falham juntas.
    """
    regiao = Regiao(
        esquerda=10, topo=20, largura=LARGURA_DA_PARTY, altura=ALTURA_DA_PARTY
    )
    fonte = _janela_de_mentira(None, regiao)

    frame = fonte.capturar()
    assert frame.saude is SaudeDoFrame.FALHA_DE_CAPTURA

    gravador = Gravador(
        tmp_path, "cega", fonte_completa=fonte.completo_do_frame_atual
    )
    assert gravador.gravar(frame, 0.0) is False
    gravador.fechar()

    assert gravador.falhas_de_gravacao == 1
    assert _pngs_no_disco(gravador.pasta) == []
    assert _linhas_do_jsonl(gravador.pasta) == []
