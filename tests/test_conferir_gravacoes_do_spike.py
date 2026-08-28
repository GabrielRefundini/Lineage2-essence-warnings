"""Testes do portao que decide se as 8 sessoes do spike foram bem gastas.

O script `tools/conferir_gravacoes_do_spike.py` nasceu sem testes, e um portao
sem teste e uma placa, nao uma tranca. Ele decide se o usuario pode seguir ou
se precisa REGRAVAR — as duas decisoes caras: aprovar lixo desperdica as oito
sessoes, e reprovar material bom cobra uma segunda rodada de gravacao que so o
usuario pode fazer.

O que estes testes prendem, e por que cada um existe:

- As conferencias ESTRUTURAIS (indice, orfaos, paridade, dimensao) reprovam o
  que devem reprovar.
- O `arquivo` do indice e validado por FORMA antes de por existencia: um
  `../outra-sessao/frame_000001.png` resolvia para fora da pasta e passava.
- A paridade e de CONJUNTOS: um nome repetido mais um PNG solto empatam na
  contagem e cobriam um frame perdido.
- Uma sessao congelada REPROVA, pelas duas vias — a fracao de `saude` ruim, e a
  identidade byte a byte entre o primeiro e o ultimo PNG (que e a unica que
  pega a sessao curta, porque o classificador precisa de 30 frames identicos
  antes de dizer CONGELADO).
- Uma sessao boa continua APROVANDO: sem isto, o jeito mais facil de deixar os
  testes verdes seria um portao que reprova tudo.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parent.parent


def _carregar_o_portao():
    """`tools/` nao e pacote, entao o import vem do caminho do arquivo."""
    caminho = RAIZ / "tools" / "conferir_gravacoes_do_spike.py"
    spec = importlib.util.spec_from_file_location("conferir_do_spike", caminho)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


portao = _carregar_o_portao()

# A janela do jogo e o recorte da party, as duas formas que o portao precisa
# saber distinguir (medidas em recordings/inv3/f000_JANELA.png).
ALTURA_DA_JANELA, LARGURA_DA_JANELA = 140, 172
ALTURA_DA_PARTY, LARGURA_DA_PARTY = 52, 17


@pytest.fixture
def calibracao(tmp_path: Path) -> Path:
    """Um `calibration.json` minimo: so a forma que precisa ser RECUSADA."""
    caminho = tmp_path / "calibration.json"
    caminho.write_text(
        json.dumps(
            {
                "party_window": {
                    "esquerda": 0,
                    "topo": 0,
                    "largura": LARGURA_DA_PARTY,
                    "altura": ALTURA_DA_PARTY,
                }
            }
        ),
        encoding="utf-8",
    )
    return caminho


def _frame_vivo(indice: int, altura: int, largura: int) -> np.ndarray:
    """Um frame que MUDA com o indice — uma janela viva nao se repete."""
    pixels = np.zeros((altura, largura, 3), dtype=np.uint8)
    pixels[:, :] = (60 + indice * 3) % 200
    # Ruido determinístico: dois frames vizinhos nunca saem byte-identicos.
    pixels[indice % altura, :, 0] = 255
    return pixels


def _gravar_sessao(
    pasta_base: Path,
    rotulo: str,
    quantidade: int = 4,
    *,
    altura: int = ALTURA_DA_JANELA,
    largura: int = LARGURA_DA_JANELA,
    saude: str = "ok",
    congelada: bool = False,
) -> Path:
    """Fabrica uma pasta de gravacao no formato que o `Gravador` produz."""
    pasta = pasta_base / f"20260827-101500-{rotulo}"
    pasta.mkdir(parents=True)
    linhas = []
    for indice in range(quantidade):
        # `congelada`: a MESMA imagem em todos os frames, que e o que a janela
        # entrega depois de parar de produzir.
        pixels = _frame_vivo(0 if congelada else indice, altura, largura)
        nome = f"frame_{indice:06d}.png"
        cv2.imwrite(str(pasta / nome), pixels)
        linhas.append(
            json.dumps(
                {
                    "indice": indice,
                    "momento": float(indice),
                    "saude": saude,
                    "arquivo": nome,
                }
            )
        )
    (pasta / "observacoes.jsonl").write_text(
        "\n".join(linhas) + "\n", encoding="utf-8"
    )
    return pasta


def _todos_os_cenarios(pasta_base: Path, **kwargs) -> None:
    for sufixo in portao.SUFIXOS_DO_ROTEIRO:
        _gravar_sessao(pasta_base, sufixo, **kwargs)


# -- o caminho feliz, que e o que impede um portao "reprova tudo" ------------


def test_oito_sessoes_boas_sao_aprovadas(tmp_path: Path, calibracao: Path) -> None:
    gravacoes = tmp_path / "recordings"
    gravacoes.mkdir()
    _todos_os_cenarios(gravacoes)

    assert portao.conferir(gravacoes, calibracao) == 0


def test_sem_nenhuma_gravacao_o_portao_nomeia_os_oito_sufixos(
    tmp_path: Path, calibracao: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """O portao tem dentes antes de o usuario gravar qualquer coisa."""
    gravacoes = tmp_path / "recordings"
    gravacoes.mkdir()

    assert portao.conferir(gravacoes, calibracao) == 1

    erro = capsys.readouterr().err
    for sufixo in portao.SUFIXOS_DO_ROTEIRO:
        assert sufixo in erro


# -- conferencia 6 e 7: a sessao mostra alguma coisa -------------------------


def test_uma_sessao_congelada_e_reprovada_pelo_saude(tmp_path: Path) -> None:
    """O `saude` ja estava escrito em toda linha, e ninguem lia.

    Uma janela que para de produzir frames rende N PNGs identicos: todos
    confirmados, todos bem dimensionados, todos indexados. Sem esta conferencia
    o portao imprimia APROVADO para uma gravacao com UM frame util.
    """
    pasta = _gravar_sessao(
        tmp_path, "mercado-aberto", quantidade=8, saude="congelado"
    )

    with pytest.raises(portao.Problema, match="CONGELADO"):
        portao.conferir_o_indice(pasta)


def test_uma_falha_de_captura_majoritaria_e_reprovada(tmp_path: Path) -> None:
    pasta = _gravar_sessao(
        tmp_path, "mercado-aberto", quantidade=8, saude="falha_de_captura"
    )

    with pytest.raises(portao.Problema, match="FALHA_DE_CAPTURA"):
        portao.conferir_o_indice(pasta)


def test_uma_sessao_curta_e_congelada_e_pega_pelos_bytes(tmp_path: Path) -> None:
    """O buraco que a fracao de `saude` NAO alcanca.

    `_ClassificadorDeSaude` so marca CONGELADO depois de 30 frames identicos
    seguidos. Numa sessao de 30 segundos a 1 Hz — a duracao que o proprio
    ROTEIRO-SPIKE.md prescreve — uma janela totalmente congelada produz 30
    frames com `saude: ok` em TODAS as linhas. A conferencia 6 nao ve nada.
    """
    pasta = _gravar_sessao(
        tmp_path, "mercado-aberto", quantidade=6, saude="ok", congelada=True
    )

    # A prova de que a conferencia 6 realmente nao pega este caso.
    portao.conferir_o_indice(pasta)

    with pytest.raises(portao.Problema, match="MESMO arquivo byte a byte"):
        portao.conferir_a_dimensao(pasta, (ALTURA_DA_PARTY, LARGURA_DA_PARTY))


# -- conferencia 3: a forma do nome vem antes da existencia ------------------


def test_um_arquivo_que_escapa_da_pasta_e_recusado(tmp_path: Path) -> None:
    """`is_file()` sozinho confirmava um PNG de OUTRA sessao.

    Um indice hand-editado ou escrito por uma ferramenta futura com
    `"arquivo": "../vizinha/frame_000000.png"` resolve para fora da pasta e
    passava na conferencia que existe para provar que o indice nao cita o que
    nao existe.
    """
    vizinha = _gravar_sessao(tmp_path, "mercado-fechado", quantidade=1)
    pasta = _gravar_sessao(tmp_path, "mercado-aberto", quantidade=1)

    (pasta / "observacoes.jsonl").write_text(
        json.dumps(
            {
                "indice": 0,
                "momento": 0.0,
                "saude": "ok",
                "arquivo": f"../{vizinha.name}/frame_000000.png",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(portao.Problema, match="invalido"):
        portao.conferir_o_indice(pasta)


@pytest.mark.parametrize(
    "nome",
    [
        "frame_1.png",  # sem os seis digitos
        "frame_000000.PNG",  # o glob do disco e minusculo
        "observacoes.jsonl",  # nao e frame
        "",
        None,
        123,
    ],
)
def test_nomes_fora_da_forma_frame_NNNNNN_sao_recusados(
    tmp_path: Path, nome: object
) -> None:
    pasta = _gravar_sessao(tmp_path, "mercado-aberto", quantidade=1)
    (pasta / "observacoes.jsonl").write_text(
        json.dumps({"indice": 0, "momento": 0.0, "saude": "ok", "arquivo": nome})
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(portao.Problema, match="invalido"):
        portao.conferir_o_indice(pasta)


# -- conferencia 4: paridade de CONJUNTOS, nao de contagens ------------------


def test_um_nome_repetido_com_um_png_solto_nao_empata(tmp_path: Path) -> None:
    """O empate de cardinalidade que cobria um frame perdido.

    Duas linhas citando o mesmo PNG mais um PNG que ninguem cita: 4 linhas, 4
    arquivos. A comparacao de contagens passava satisfeita enquanto um frame
    tinha sumido do indice.
    """
    pasta = _gravar_sessao(tmp_path, "mercado-aberto", quantidade=4)

    linhas = (pasta / "observacoes.jsonl").read_text(encoding="utf-8").splitlines()
    registro = json.loads(linhas[3])
    registro["arquivo"] = "frame_000000.png"  # aponta para o mesmo do indice 0
    linhas[3] = json.dumps(registro)
    (pasta / "observacoes.jsonl").write_text(
        "\n".join(linhas) + "\n", encoding="utf-8"
    )

    assert len(linhas) == len(portao.pngs_de_frame(pasta)), (
        "a montagem do teste precisa EMPATAR na contagem, senao ele nao prova "
        "que a comparacao de conjuntos e que pegou"
    )
    with pytest.raises(portao.Problema, match="mais de uma vez|NAO cita"):
        portao.conferir_o_indice(pasta)


def test_um_png_que_o_indice_nao_cita_reprova(tmp_path: Path) -> None:
    pasta = _gravar_sessao(tmp_path, "mercado-aberto", quantidade=3)
    cv2.imwrite(
        str(pasta / "frame_000099.png"),
        _frame_vivo(99, ALTURA_DA_JANELA, LARGURA_DA_JANELA),
    )

    with pytest.raises(portao.Problema, match="NAO cita"):
        portao.conferir_o_indice(pasta)


def test_uma_linha_citando_arquivo_inexistente_reprova(tmp_path: Path) -> None:
    pasta = _gravar_sessao(tmp_path, "mercado-aberto", quantidade=3)
    (pasta / "frame_000001.png").unlink()

    with pytest.raises(portao.Problema, match="NAO existem no disco"):
        portao.conferir_o_indice(pasta)


# -- conferencia 5: a janela, nunca o recorte da party -----------------------


def test_o_recorte_da_party_no_lugar_da_janela_reprova(tmp_path: Path) -> None:
    """O engano de ~170 KB que gastaria as oito sessoes."""
    pasta = _gravar_sessao(
        tmp_path,
        "mercado-aberto",
        quantidade=3,
        altura=ALTURA_DA_PARTY,
        largura=LARGURA_DA_PARTY,
    )

    with pytest.raises(portao.Problema, match="recorte da party window"):
        portao.conferir_a_dimensao(pasta, (ALTURA_DA_PARTY, LARGURA_DA_PARTY))


def test_um_indice_vazio_reprova(tmp_path: Path) -> None:
    pasta = _gravar_sessao(tmp_path, "mercado-aberto", quantidade=2)
    (pasta / "observacoes.jsonl").write_text("", encoding="utf-8")

    with pytest.raises(portao.Problema, match="VAZIO"):
        portao.conferir_o_indice(pasta)
