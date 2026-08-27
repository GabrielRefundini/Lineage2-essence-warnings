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
from pathlib import Path

import numpy as np
import pytest

from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.gravador import Gravador


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


def _ocupar_o_nome_com_um_diretorio(pasta: Path, indice: int) -> None:
    """A falha deterministica que funciona em QUALQUER SO.

    O somente-leitura depende de permissoes que variam entre maquinas (o
    proprio `test_conferencia_gravada.py` precisa de um `pytest.skip` para
    ele). Um diretorio ocupando o nome do arquivo faz o `cv2.imwrite` falhar
    em todo lugar, sem depender de permissao nenhuma.
    """
    (pasta / f"frame_{indice:06d}.png").mkdir()


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
    assert len(list(gravador.pasta.glob("frame_*.png"))) == 3
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
    assert gravador.frames_gravados == len(list(gravador.pasta.glob("frame_*.png")))
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
