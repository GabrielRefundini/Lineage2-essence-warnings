"""Testes da gravacao da imagem de conferencia do calibrador.

O calibrador manda o usuario ABRIR a imagem de conferencia. Se ele rodar de
novo com a imagem aberta no visualizador de fotos do Windows, o `cv2.imwrite`
devolve `False` sem levantar excecao — e o calibrador, que jogava esse retorno
fora, anunciava "Imagem de conferencia: calibracao-conferencia.png" como se
tivesse dado certo. O usuario conferia A IMAGEM VELHA e validava uma calibracao
errada.

Numa ferramenta cujo unico trabalho e dizer "confie nisto", essa e a pior falha
possivel. Estes testes existem para garantir que o calibrador entrega uma imagem
nova ou diz alto que nao entregou.
"""

from __future__ import annotations

import inspect
import os
import re
import stat
from pathlib import Path

import cv2
import numpy as np
import pytest

import l2scanner.calibrar
from l2scanner.calibracao import Calibracao
from l2scanner.calibrar import (
    _conferencia_do_solo,
    _gravar_conferencia,
    _texto_final_do_solo,
    conferir_visualmente,
)
from l2scanner.frames import Regiao

FIXTURES = Path(__file__).parent / "fixtures"


def _imagem() -> np.ndarray:
    """Uma imagem qualquer, so para ter bytes validos para gravar.

    O conteudo nunca importa nestes testes: o que se afirma e a MENSAGEM
    impressa, nunca o desenho.
    """
    return np.full((20, 30, 3), 70, dtype=np.uint8)


def _pngs_citados(saida: str) -> list[str]:
    return re.findall(r"\S+\.png", saida)


def _afirmar_que_todo_png_citado_existe(saida: str) -> None:
    """Nenhuma mensagem pode citar um arquivo que o calibrador nao escreveu.

    A checagem exige caminho ABSOLUTO, e isso nao e preciosismo: a raiz do
    repositorio tem um `calibracao-conferencia.png` sobrando de rodadas
    anteriores, entao um nome solto ("calibracao-conferencia.png") resolveria
    para um arquivo que existe e passaria por acidente. Esse arquivo velho e
    exatamente o que engana o usuario — aceita-lo aqui seria repetir o bug
    dentro do teste que deveria pega-lo.
    """
    for nome in _pngs_citados(saida):
        caminho = Path(nome)
        assert caminho.is_absolute(), f"a saida cita {nome} sem o caminho completo"
        assert caminho.exists(), f"a saida cita {nome}, que nao existe no disco"


@pytest.fixture
def raiz(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redireciona a escrita do calibrador para o tmp_path do teste.

    `RAIZ` e lido como global dentro de `_gravar_conferencia` justamente para
    isto ser possivel — capturado em argumento com valor padrao, a gravacao
    cairia na raiz do repositorio de verdade.
    """
    monkeypatch.setattr(l2scanner.calibrar, "RAIZ", tmp_path)
    return tmp_path


@pytest.fixture
def raiz_impossivel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Uma raiz que nao existe: nem o arquivo padrao nem o alternativo cabem."""
    destino = tmp_path / "pasta-que-nao-existe"
    monkeypatch.setattr(l2scanner.calibrar, "RAIZ", destino)
    return destino


@pytest.fixture
def calibracao_da_party() -> Calibracao:
    return Calibracao.carregar(FIXTURES / "calibracao_de_referencia.json")


@pytest.fixture
def calibracao_solo(calibracao_da_party: Calibracao) -> Calibracao:
    # O fixture grava `hp_proprio: null` — o modo solo precisa desse campo,
    # entao ele e atribuido a mao (Calibracao e dataclass mutavel).
    calibracao_da_party.hp_proprio = Regiao(10, 10, 60, 20)
    return calibracao_da_party


@pytest.fixture
def pixels_da_party(calibracao_da_party: Calibracao) -> np.ndarray:
    pw = calibracao_da_party.party_window
    return np.full((pw.altura, pw.largura, 3), 40, dtype=np.uint8)


def _travar_com_arquivo_somente_leitura(caminho: Path) -> None:
    caminho.write_bytes(b"imagem velha, a que engana o usuario")
    os.chmod(caminho, stat.S_IREAD)


def test_gravacao_normal_devolve_o_caminho_e_a_imagem_e_legivel(raiz: Path) -> None:
    caminho = _gravar_conferencia(_imagem())

    assert caminho == raiz / "calibracao-conferencia.png"
    assert caminho.exists()
    assert cv2.imread(str(caminho), cv2.IMREAD_COLOR) is not None


def test_sucesso_imprime_caminho_absoluto_e_horario(
    raiz: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    caminho = _gravar_conferencia(_imagem())
    saida = capsys.readouterr().out

    assert str(caminho) in saida, "o caminho completo precisa aparecer, nao so o nome"
    assert re.search(r"\d{2}:\d{2}:\d{2}", saida), "falta o horario do arquivo escrito"


def test_destino_travado_por_arquivo_somente_leitura_cai_no_alternativo(
    raiz: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    padrao = raiz / "calibracao-conferencia.png"
    _travar_com_arquivo_somente_leitura(padrao)
    antes = padrao.read_bytes()

    try:
        caminho = _gravar_conferencia(_imagem())

        if caminho == padrao:
            pytest.skip(
                "este SO ignorou o somente-leitura e gravou por cima; "
                "o caso deterministico e o do diretorio ocupando o nome"
            )

        assert caminho is not None
        assert re.fullmatch(r"calibracao-conferencia-\d{6}\.png", caminho.name)
        assert cv2.imread(str(caminho), cv2.IMREAD_COLOR) is not None
        assert padrao.read_bytes() == antes, "o arquivo antigo foi mexido"
        _afirmar_que_todo_png_citado_existe(capsys.readouterr().out)
    finally:
        # Sem devolver a escrita o tmp_path nao pode ser limpo.
        os.chmod(padrao, stat.S_IWRITE)


def test_destino_travado_por_diretorio_cai_no_alternativo(
    raiz: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Um diretorio ocupando o nome do arquivo e o caso que falha em QUALQUER
    # SO — o somente-leitura depende de permissoes que variam.
    (raiz / "calibracao-conferencia.png").mkdir()

    caminho = _gravar_conferencia(_imagem())

    assert caminho is not None
    assert re.fullmatch(r"calibracao-conferencia-\d{6}\.png", caminho.name)
    assert cv2.imread(str(caminho), cv2.IMREAD_COLOR) is not None
    _afirmar_que_todo_png_citado_existe(capsys.readouterr().out)


def test_sem_nenhum_destino_gravavel_devolve_none(
    raiz_impossivel: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _gravar_conferencia(_imagem()) is None

    saida = capsys.readouterr().out
    assert "conferencia" in saida.lower()
    assert _pngs_citados(saida) == [], "sem imagem, nenhum nome de arquivo pode sair"


def test_conferir_visualmente_sem_destino_nao_promete_imagem(
    raiz_impossivel: Path,
    calibracao_da_party: Calibracao,
    pixels_da_party: np.ndarray,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A regressao: hoje o calibrador anuncia uma imagem que nao existe."""
    pw = calibracao_da_party.party_window
    conferir_visualmente(
        calibracao_da_party, pixels_da_party, pw.esquerda, pw.topo
    )

    saida = capsys.readouterr().out
    _afirmar_que_todo_png_citado_existe(saida)
    assert "nao" in saida.lower() and "conferencia" in saida.lower(), (
        "o calibrador precisa dizer alto que nao ha imagem de conferencia"
    )


def test_conferir_visualmente_com_destino_cita_o_arquivo_escrito(
    raiz: Path,
    calibracao_da_party: Calibracao,
    pixels_da_party: np.ndarray,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pw = calibracao_da_party.party_window
    conferir_visualmente(
        calibracao_da_party, pixels_da_party, pw.esquerda, pw.topo
    )

    saida = capsys.readouterr().out
    assert _pngs_citados(saida), "com imagem gravada, o caminho precisa aparecer"
    _afirmar_que_todo_png_citado_existe(saida)


def test_existe_um_unico_ponto_de_escrita_no_modulo() -> None:
    """Duplicar a gravacao foi o que permitiu os dois pontos calarem o erro.

    Se alguem voltar a chamar a gravacao direto, este teste cai antes de o
    calibrador voltar a mentir.
    """
    total = inspect.getsource(l2scanner.calibrar).count("imwrite")
    no_auxiliar = inspect.getsource(_gravar_conferencia).count("imwrite")

    assert no_auxiliar >= 1
    assert total == no_auxiliar, "ha gravacao de imagem fora de _gravar_conferencia"


def test_conferencia_do_solo_com_destino_travado_cai_no_alternativo(
    raiz: Path,
    calibracao_solo: Calibracao,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (raiz / "calibracao-conferencia.png").mkdir()
    pixels = np.full((120, 200, 3), 40, dtype=np.uint8)

    caminho = _conferencia_do_solo(calibracao_solo, pixels)

    assert caminho is not None
    assert re.fullmatch(r"calibracao-conferencia-\d{6}\.png", caminho.name)
    _afirmar_que_todo_png_citado_existe(capsys.readouterr().out)


def test_conferencia_do_solo_sem_destino_devolve_none(
    raiz_impossivel: Path,
    calibracao_solo: Calibracao,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pixels = np.full((120, 200, 3), 40, dtype=np.uint8)

    assert _conferencia_do_solo(calibracao_solo, pixels) is None

    saida = capsys.readouterr().out
    assert _pngs_citados(saida) == []
    assert "conferencia" in saida.lower()


def test_texto_final_do_solo_so_manda_conferir_quando_ha_imagem(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    caminho = tmp_path / "calibracao-conferencia-123456.png"
    caminho.write_bytes(b"qualquer coisa")

    _texto_final_do_solo(caminho)
    com_imagem = capsys.readouterr().out
    assert "CONFIRA" in com_imagem
    assert str(caminho) in com_imagem

    _texto_final_do_solo(None)
    sem_imagem = capsys.readouterr().out
    assert "CONFIRA" not in sem_imagem
    assert _pngs_citados(sem_imagem) == []
    # O alerta sobre a barra do alvo selecionado vale ainda MAIS sem imagem:
    # ninguem conferiu o retangulo.
    assert "alvo" in sem_imagem.lower()
