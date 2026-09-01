"""Uma rodada `--layout adena` NAO pode apagar a calibracao de negociacao.

O DANO QUE ESTE ARQUIVO EXISTE PARA IMPEDIR. Ate 2026-09-01 `calibrar` gravava
as chaves de TOPO incondicionalmente -- `mercado_ancora`,
`mercado_molde_da_ancora`, `mercado_limiar_da_ancora`,
`mercado_geometria_da_captura`, `mercado_ancoras`, `mercado_grade` e as QUATRO
colunas -- qualquer que fosse o `--layout`. A calibracao de negociacao que
aquelas chaves guardam foi conferida EM CAMPO em 2026-09-01: 353 paginas lidas
contra 2 perdidas, 99,4% de aproveitamento, com a banda vertical de oclusao
consertada no mesmo dia. Ela custou 13 moldes de glifo cortados a mao e 3
ancoras marcadas com o mouse, e o `calibration.json` e GITIGNORED
(`.gitignore:51`): nao existe `git checkout` que a traga de volta. O projeto ja
pagou esse preco uma vez, em 2026-08-30, e o resgate foi manual
(`calibration.RESGATE-13-glifos.json`).

DOIS CRITERIOS PLAUSIVEIS QUE SAO VACUOS AQUI, escritos para o proximo leitor
nao os reintroduzir:

- `git status --porcelain calibration.json` sai VAZIO SEMPRE. O arquivo e
  gitignored, entao o git nao tem opiniao sobre ele: o comando devolve string
  vazia com o arquivo intacto, com o arquivo destruido e com o arquivo
  apagado. Um teste construido sobre ele passaria com a calibracao no lixo.
- `git diff --numstat` sobre um arquivo NAO RASTREADO devolve 0 tendo removido
  zero ou quatrocentas linhas, pela mesma razao.

O QUE DISCRIMINA e comparar o CONTEUDO PARSEADO antes e depois, chave por
chave, com as chaves ENUMERADAS a partir do arquivo de ANTES -- assim o caso
cobre tambem as chaves de topo que ainda nem existem.

E O CASO 3 E QUEM IMPEDE O CASO 1 DE SER VACUO. Um portao que simplesmente
parasse de escrever em tudo passaria nos casos 1 e 2 com louvor. O par que
discrimina e a rodada `--layout negociacao` com retangulos DIFERENTES dos
semeados, afirmando que `mercado_grade` e as quatro colunas de topo MUDARAM.

DISCIPLINA INEGOCIAVEL DESTE ARQUIVO, herdada inteira de
`test_calibrar_nao_apaga_mercado.py`: todo caso aponta `--calibracao` para
dentro de `tmp_path`. E a unica coisa que mantem o `calibration.json` da
maquina do usuario fora do alcance desta suite. Quem remover a linha achando
que e ruido reproduz o incidente dentro do CI, e desta vez sem resgate. Nenhum
caso le `recordings/`, nenhum usa glob, e nenhum escreve em `.mercado/`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np
import pytest

import l2scanner.calibrar_mercado
from l2scanner.calibracao import Calibracao
from l2scanner.calibrar_mercado import MercadoNaoCalibravel
from l2scanner.mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA
from l2scanner.mercado_pagina import LeitorDePagina
from l2scanner.mercado_visao import RastreioDoPainel, ancoras_de_calibracao

FIXTURAS = Path(__file__).parent / "fixtures" / "mercado"
SEMENTE = FIXTURAS / "calibracao_de_fixture.json"

FRAME_DA_ADENA = FIXTURAS / "janela_adena_f014.png"
FRAME_DA_NEGOCIACAO = FIXTURAS / "janela_negociacao_f005.png"


# ---------------------------------------------------------------------------
# Os retangulos, MEDIDOS e nao inventados
# ---------------------------------------------------------------------------
#
# Sao os da propria fixtura, reconvertidos para coordenadas absolutas por
# `localizar_o_titulo` sobre os dois frames versionados (origem do painel medida
# em (1010, 212) nos dois, casamento 0,9999). Escrever numeros absolutos a mao
# mediria uma geometria que a producao nao usa; estes sao os que o leitor ja
# consome, e por isso o caso 5 consegue ler as nove linhas de taxa.
CAIXAS_DA_ADENA = {
    "Ancora: titulo": (1010, 212, 98, 27),
    "Grade": (583, 468, 944, 450),
    "Primeira linha": (583, 468, 944, 45),
    # AS DUAS QUE A RODADA DE ADENA NAO DEVE PEDIR ESTAO AQUI DE PROPOSITO.
    #
    # Sem elas, o mutante que reverte o portao morre no PROPRIO ARNES ("sem
    # sugestao para 'Coluna: nome'") em vez de morrer na afirmacao — e um teste
    # cuja rede e o arnes nao mediu o portao, mediu o arnes. Com elas
    # disponiveis, o mutante roda ate o fim e a reprovacao vem de onde tem de
    # vir: `mercado_grade`, `mercado_cabecalho_de_coluna` e os 13 moldes de
    # glifo destruidos. Que a rodada boa NAO as peca e afirmado a parte, em
    # `TestOQueARodadaDeAdenaNemCHEGA_A_PEDIR`.
    "Coluna: nome": (625, 468, 324, 450),
    "Coluna: quantidade": (949, 468, 123, 450),
    "Coluna: total": (1072, 468, 209, 450),
    "Coluna: unitario": (1281, 468, 174, 450),
    "Cabecalho de coluna": (583, 436, 944, 30),
}

# DE PROPOSITO DIFERENTES DOS SEMEADOS, e essa e a razao de o caso 3 existir.
# Grade: dx -425 contra -427, dy 258 contra 256, largura 940 contra 944, altura
# 448 contra 450, altura_da_linha 46 contra 45. Colunas: cada dx deslocado de
# 2 px e cada largura encolhida. Todas continuam DENTRO da grade desenhada
# (x de 585 a 1525), que `conferir_a_coluna_na_grade` exige.
CAIXAS_DA_NEGOCIACAO = {
    "Ancora: titulo": (1010, 212, 98, 27),
    "Grade": (585, 470, 940, 448),
    "Primeira linha": (585, 470, 940, 46),
    "Coluna: nome": (627, 470, 320, 448),
    "Coluna: quantidade": (951, 470, 120, 448),
    "Coluna: total": (1074, 470, 205, 448),
    "Coluna: unitario": (1283, 470, 170, 448),
    "Cabecalho de coluna": (585, 438, 940, 30),
}


def _semear(tmp_path: Path, *, com_layouts: bool = False) -> Path:
    """A calibracao de PARTIDA, dentro de `tmp_path`. Nunca a da maquina.

    `mercado_layouts` sai FORA por padrao, e isso e um discriminante e nao uma
    conveniencia: a fixtura ja traz um bloco `adena` identico ao que a
    ferramenta produz, entao um caso que so afirmasse "o bloco existe depois"
    passaria com a ferramenta gravando NADA. Sem a chave na semente, "existe
    depois" so pode ter vindo desta rodada.

    E e tambem o estado REAL de toda instalacao que existe hoje: `mercado_layouts`
    nasceu opcional no 05-02, e nenhum `calibration.json` de usuario a tem.
    """
    dados = json.loads(SEMENTE.read_text(encoding="utf-8"))
    if not com_layouts:
        dados.pop("mercado_layouts", None)
    alvo = tmp_path / "calibration.json"
    alvo.write_text(json.dumps(dados), encoding="utf-8")
    return alvo


def _ler(alvo: Path) -> dict:
    return json.loads(alvo.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _o_calibration_json_da_maquina_fica_FORA_DE_ALCANCE(monkeypatch, tmp_path):
    """A rede que nao depende de ninguem lembrar de passar `--calibracao`.

    `test_calibrar_nao_apaga_mercado.py` chama isto de disciplina inegociavel, e
    ela e disciplina porque e por caso. Aqui ela vira ESTRUTURA: o padrao do
    modulo aponta para um caminho inexistente dentro de `tmp_path`, entao um
    caso futuro que esqueca a flag falha com "nao encontrei" em vez de LER — ou,
    pior, ESCREVER — a calibracao conferida em campo da maquina do usuario.
    """
    monkeypatch.setattr(
        l2scanner.calibrar_mercado,
        "ARQUIVO_CALIBRACAO",
        tmp_path / "nunca-a-da-maquina" / "calibration.json",
    )


class Rodada(NamedTuple):
    """O que uma rodada devolve, alem do codigo de saida.

    `titulos` sao as janelas de selecao que ela ABRIU e `perguntas` o texto que
    ela DIGITOU pedir. Os dois existem porque "recusou" e "recusou depois de
    gastar a sessao de marcacao" sao coisas diferentes, e so a primeira protege
    o trabalho do usuario.
    """

    rc: int
    titulos: list[str]
    perguntas: list[str]


def _rodar(
    monkeypatch,
    tmp_path: Path,
    alvo: Path,
    *,
    layout: str,
    frame: Path,
    caixas: dict[str, tuple[int, int, int, int]],
    so_digitos: bool = False,
) -> tuple[int, list[str]]:
    """Uma rodada inteira de `calibrar`, sem mouse e sem highgui.

    `_selecionar_regiao` e o seam: e ele que embrulha `cv2.selectROI`, e a suite
    inteira desta casa o dubla (ver `test_calibrar_mercado.py`). O `selectROI`
    de verdade e trocado por uma BOMBA no mesmo gesto — se algum caminho novo
    passar por fora do seam, o teste estoura em vez de abrir uma janela de
    verdade no meio do CI.
    """
    titulos: list[str] = []

    def _selecao_falsa(_pixels, titulo, _instrucao, sugestao=None):
        titulos.append(titulo)
        if titulo in caixas:
            return caixas[titulo]
        # As duas ancoras derivadas: a ferramenta as PROPOE a partir do titulo,
        # e aceitar a proposta e o que o usuario faz com o ENTER.
        assert sugestao is not None, f"sem sugestao para {titulo!r}"
        return sugestao

    def _bomba(*_a, **_k):
        raise AssertionError(
            "cv2.selectROI de VERDADE foi chamado: algum caminho escapou do "
            "seam `_selecionar_regiao` e abriria uma janela no CI"
        )

    monkeypatch.setattr(cv2, "selectROI", _bomba)
    monkeypatch.setattr(cv2, "imshow", lambda *a, **k: None)
    monkeypatch.setattr(cv2, "destroyAllWindows", lambda *a, **k: None)
    monkeypatch.setattr(cv2, "destroyWindow", lambda *a, **k: None)
    monkeypatch.setattr(
        l2scanner.calibrar_mercado, "_selecionar_regiao", _selecao_falsa
    )
    monkeypatch.setattr(
        l2scanner.calibrar_mercado,
        "_gravar_conferencia",
        lambda _tela: tmp_path / "conferencia.png",
    )
    # `"f"` = TERMINAR o passo de corte de glifos, que so a rodada de
    # negociacao alcanca. E a resposta que a suite da casa ja da
    # (`test_calibrar_mercado.py`), e as perguntas ficam GRAVADAS para o caso
    # da adena poder afirmar que nao houve nenhuma.
    perguntas: list[str] = []

    def _fala(prompt="", *_a, **_k):
        perguntas.append(str(prompt))
        return "f"

    monkeypatch.setattr("builtins.input", _fala)

    args = argparse.Namespace(
        calibracao=str(alvo),
        gravacao=None,
        frame=str(frame),
        indice=None,
        layout=layout,
        so_digitos=so_digitos,
    )
    return Rodada(
        l2scanner.calibrar_mercado.calibrar(args), titulos, perguntas
    )


def _chaves_de_topo_de_mercado(dados: dict) -> list[str]:
    """Enumeradas a partir do arquivo, nunca de uma lista escrita a mao.

    `mercado_layouts` fica de fora porque ela E o destino legitimo da escrita.
    Toda outra chave `mercado_*` e chave de TOPO, e nenhuma delas pode mudar
    numa rodada de layout aninhado — inclusive as que ainda nem existem.
    """
    return [
        chave
        for chave in dados
        if chave.startswith("mercado_") and chave != "mercado_layouts"
    ]


# ---------------------------------------------------------------------------
# Caso 1 — a rodada de adena PRESERVA o topo
# ---------------------------------------------------------------------------


class TestARodadaDeAdenaPreservaOTopo:
    """A truth central da fase, medida sobre o JSON PARSEADO.

    Nao sobre o git (o arquivo e gitignored e o git nao tem opiniao), nao sobre
    bytes (a ordem das chaves e o espacamento nao sao a calibracao), e nao sobre
    uma lista de chaves escrita a mao (ela envelhece calada). Chave por chave,
    enumeradas a partir do arquivo de ANTES.
    """

    def test_nenhuma_chave_de_topo_de_mercado_mudou_de_valor(
        self, monkeypatch, tmp_path: Path
    ):
        alvo = _semear(tmp_path)
        antes = _ler(alvo)

        assert (
            _rodar(
                monkeypatch,
                tmp_path,
                alvo,
                layout="adena",
                frame=FRAME_DA_ADENA,
                caixas=CAIXAS_DA_ADENA,
            ).rc
            == 0
        )

        depois = _ler(alvo)
        mudaram = {
            chave: (antes[chave], depois.get(chave))
            for chave in _chaves_de_topo_de_mercado(antes)
            if antes[chave] != depois.get(chave)
        }
        assert mudaram == {}, (
            f"uma rodada --layout adena mudou chave de TOPO: "
            f"{sorted(mudaram)} — e esta e a calibracao conferida em campo"
        )

    def test_nenhuma_chave_de_topo_DESAPARECEU(self, monkeypatch, tmp_path: Path):
        """Igualdade de valor nao pega a chave que sumiu — `.get` devolve
        `None` dos dois lados quando as duas somem, e o CR-04 e exatamente o
        defeito de uma chave desaparecer calada."""
        alvo = _semear(tmp_path)
        antes = _ler(alvo)

        _rodar(
            monkeypatch,
            tmp_path,
            alvo,
            layout="adena",
            frame=FRAME_DA_ADENA,
            caixas=CAIXAS_DA_ADENA,
        )

        depois = _ler(alvo)
        sumiram = [chave for chave in antes if chave not in depois]
        assert sumiram == [], sumiram

    def test_os_TREZE_moldes_de_glifo_continuam_la(self, monkeypatch, tmp_path: Path):
        """A forma cara do caso acima, dita com o numero que custou o resgate
        manual de 2026-08-30. Cada molde e um arrasto mais um rotulo digitado."""
        alvo = _semear(tmp_path)
        antes = _ler(alvo)
        quantos = len(antes["mercado_templates_de_digito"])
        assert quantos == 13, f"a fixtura mudou de {quantos} moldes — retarget"

        _rodar(
            monkeypatch,
            tmp_path,
            alvo,
            layout="adena",
            frame=FRAME_DA_ADENA,
            caixas=CAIXAS_DA_ADENA,
        )

        depois = _ler(alvo)
        assert depois["mercado_templates_de_digito"] == (
            antes["mercado_templates_de_digito"]
        )

    def test_a_rodada_de_adena_nem_CORTA_glifo(self, monkeypatch, tmp_path: Path):
        """Preservar por igualdade nao distingue "nao cortou" de "cortou e o
        resultado bateu". Aqui a prova e de CHAMADA: `cortar_glifos` nao roda."""
        alvo = _semear(tmp_path)
        chamadas = []
        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "cortar_glifos",
            # `{}` e nao `[]`: `fundir_glifos` recebe um MAPA de rotulo para
            # molde, e devolver lista estoura la dentro.
            lambda *a, **k: chamadas.append(a) or {},
        )

        _rodar(
            monkeypatch,
            tmp_path,
            alvo,
            layout="adena",
            frame=FRAME_DA_ADENA,
            caixas=CAIXAS_DA_ADENA,
        )

        assert chamadas == [], (
            "a rodada de adena cortou glifo: fundir moldes de uma aba com outra "
            "iluminacao arrisca o conjunto de que a NEGOCIACAO depende"
        )

    def test_o_CONTROLE_NEGATIVO_cortar_glifos_roda_na_negociacao(
        self, monkeypatch, tmp_path: Path
    ):
        """Sem ele, "zero chamadas" nao distinguiria o portao de um
        monkeypatch que nunca alcancou o alvo."""
        alvo = _semear(tmp_path)
        chamadas = []
        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "cortar_glifos",
            # `{}` e nao `[]`: `fundir_glifos` recebe um MAPA de rotulo para
            # molde, e devolver lista estoura la dentro.
            lambda *a, **k: chamadas.append(a) or {},
        )

        _rodar(
            monkeypatch,
            tmp_path,
            alvo,
            layout="negociacao",
            frame=FRAME_DA_NEGOCIACAO,
            caixas=CAIXAS_DA_NEGOCIACAO,
        )

        assert len(chamadas) == 1


# ---------------------------------------------------------------------------
# Caso 2 — e a rodada FEZ alguma coisa
# ---------------------------------------------------------------------------


class TestARodadaDeAdenaGravouOBloco:
    """Sem esta classe, a de cima passaria com um calibrador que nao grava nada.

    A semente vem SEM `mercado_layouts` (ver `_semear`): a fixtura ja traz um
    bloco `adena` identico ao que a ferramenta produz, e afirmar "existe depois"
    sobre a semente mediria a semente.
    """

    @pytest.fixture
    def bloco(self, monkeypatch, tmp_path: Path) -> dict:
        alvo = _semear(tmp_path)
        assert "mercado_layouts" not in _ler(alvo), (
            "a semente ja tem a chave: 'existe depois' viraria vacuo"
        )
        assert (
            _rodar(
                monkeypatch,
                tmp_path,
                alvo,
                layout="adena",
                frame=FRAME_DA_ADENA,
                caixas=CAIXAS_DA_ADENA,
            ).rc
            == 0
        )
        return _ler(alvo)["mercado_layouts"]["adena"]

    def test_o_cabecalho_tem_bytes_NAO_VAZIOS(self, bloco: dict):
        cabecalho = bloco["cabecalho"]
        assert cabecalho["bytes"], "molde vazio e o portao de layout OFF"
        assert cabecalho["layout"] == "adena"
        esperado = cabecalho["altura"] * cabecalho["largura"]
        assert len(cabecalho["bytes"]) == esperado * 2, (
            "a contagem de bytes tem de bater com altura x largura — e o que "
            "`_conferir_um_molde_de_cabecalho` confere no arranque"
        )

    def test_o_limiar_esta_no_intervalo_aberto_em_zero(self, bloco: dict):
        limiar = bloco["limiar_do_cabecalho"]
        assert isinstance(limiar, float)
        assert 0.0 < limiar <= 1.0, limiar

    def test_as_colunas_sao_EXATAMENTE_total_e_unitario(self, bloco: dict):
        """IGUALDADE e nao continencia, pelo mesmo W4 do 05-02: com
        `>= {"total","unitario"}` um terceiro recorte sobre a `Auction List`
        passaria calado, e a promessa de nao tocar naquela coluna viraria
        prosa."""
        assert set(bloco["colunas"]) == {"total", "unitario"}

    def test_as_colunas_sao_as_QUE_ESTA_RODADA_marcou(self, bloco: dict):
        """Amarra a saida a ENTRADA desta rodada, e nao a uma constante.

        `dx` e deslocamento a partir da origem do painel (1010 nesta fixtura),
        nunca coordenada absoluta: o painel anda 827x831 px nas gravacoes de
        campo, e uma coluna absoluta apontaria para o vazio.
        """
        ox = CAIXAS_DA_ADENA["Ancora: titulo"][0]
        for nome in ("total", "unitario"):
            x, _y, largura, _altura = CAIXAS_DA_ADENA[f"Coluna: {nome}"]
            assert bloco["colunas"][nome] == {
                "dx": x - ox,
                "largura": largura,
            }, nome

    def test_a_grade_do_bloco_sai_VAZIA_porque_e_delta_e_nao_copia(
        self, bloco: dict
    ):
        """D-D. Hoje a geometria da Adena e IDENTICA a da negociacao, entao o
        delta e vazio e a chave nem aparece — duas copias do mesmo numero
        envelhecem separadas, e a que envelhecer pior recorta fora do lugar."""
        assert "grade" not in bloco

    def test_o_CONTROLE_NEGATIVO_uma_grade_diferente_SAI_gravada(
        self, monkeypatch, tmp_path: Path
    ):
        """Sem ele, "sem grade" nao distinguiria delta vazio de um calibrador
        que simplesmente nunca escreve grade nenhuma no bloco."""
        alvo = _semear(tmp_path)
        caixas = dict(CAIXAS_DA_ADENA)
        # Uma primeira linha de 50 px em vez de 45: `altura_da_linha` passa a
        # DIFERIR da de topo, e `linhas_por_pagina` cai de 10 para 9.
        caixas["Primeira linha"] = (583, 468, 944, 50)

        _rodar(
            monkeypatch,
            tmp_path,
            alvo,
            layout="adena",
            frame=FRAME_DA_ADENA,
            caixas=caixas,
        )

        grade = _ler(alvo)["mercado_layouts"]["adena"]["grade"]
        assert grade == {"altura_da_linha": 50, "linhas_por_pagina": 9}, grade
        assert "layout" not in grade, (
            "o nome do layout vem da CHAVE do bloco (`modelo_de_layout`); "
            "grava-lo aqui criaria a segunda verdade que o delta evita"
        )

    def test_um_layout_ja_gravado_NAO_e_apagado_por_outro(
        self, monkeypatch, tmp_path: Path
    ):
        """`cal.mercado_layouts = {layout: bloco}` seria a forma pequena do
        mesmo defeito: recalibrar a Adena apagaria todo layout vizinho."""
        alvo = _semear(tmp_path)
        dados = _ler(alvo)
        dados["mercado_layouts"] = {
            "outro": {
                "limiar_do_cabecalho": 0.5,
                "colunas": {"total": {"dx": 1, "largura": 2}},
            }
        }
        alvo.write_text(json.dumps(dados), encoding="utf-8")

        _rodar(
            monkeypatch,
            tmp_path,
            alvo,
            layout="adena",
            frame=FRAME_DA_ADENA,
            caixas=CAIXAS_DA_ADENA,
        )

        layouts = _ler(alvo)["mercado_layouts"]
        assert set(layouts) == {"outro", "adena"}
        assert layouts["outro"] == dados["mercado_layouts"]["outro"]


class TestOQueARodadaDeAdenaNemCHEGA_A_PEDIR:
    """O custo da rodada, medido nas janelas que ela ABRE e nas que nao abre.

    Nao e ergonomia: a janela `Coluna: nome` da negociacao comeca a -1 px do
    primeiro run da `Auction List`, e aceitar aquele retangulo verde por
    reflexo cortaria o `1` de `10,000,000` para `0,000,000`. A unica forma de
    aquele numero nunca existir e a janela nunca abrir.
    """

    @pytest.fixture
    def rodada(self, monkeypatch, tmp_path: Path) -> Rodada:
        alvo = _semear(tmp_path)
        feita = _rodar(
            monkeypatch,
            tmp_path,
            alvo,
            layout="adena",
            frame=FRAME_DA_ADENA,
            caixas=CAIXAS_DA_ADENA,
        )
        assert feita.rc == 0
        return feita

    def test_nem_a_coluna_do_NOME_nem_a_de_QUANTIDADE_sao_pedidas(
        self, rodada: Rodada
    ):
        assert "Coluna: nome" not in rodada.titulos
        assert "Coluna: quantidade" not in rodada.titulos

    def test_as_janelas_de_coluna_sao_EXATAMENTE_duas(self, rodada: Rodada):
        """IGUALDADE, pelo mesmo W4: com continencia uma terceira janela
        passaria calada e a promessa viraria prosa."""
        colunas = [t for t in rodada.titulos if t.startswith("Coluna: ")]
        assert colunas == ["Coluna: total", "Coluna: unitario"]

    def test_a_rodada_de_adena_nao_DIGITA_pergunta_nenhuma(self, rodada: Rodada):
        """O passo de corte de glifos e o unico que pede texto, e ele nao
        acontece fora da negociacao."""
        assert rodada.perguntas == [], rodada.perguntas

    def test_o_CONTROLE_NEGATIVO_a_negociacao_pede_as_QUATRO_e_DIGITA(
        self, monkeypatch, tmp_path: Path
    ):
        """Sem ele, "duas janelas e zero perguntas" nao distinguiria o portao
        de um seam que simplesmente nunca foi alcancado."""
        alvo = _semear(tmp_path)
        feita = _rodar(
            monkeypatch,
            tmp_path,
            alvo,
            layout="negociacao",
            frame=FRAME_DA_NEGOCIACAO,
            caixas=CAIXAS_DA_NEGOCIACAO,
        )
        colunas = [t for t in feita.titulos if t.startswith("Coluna: ")]
        assert colunas == [
            "Coluna: nome",
            "Coluna: quantidade",
            "Coluna: total",
            "Coluna: unitario",
        ]
        assert feita.perguntas, "o corte de glifos da negociacao pede texto"


# ---------------------------------------------------------------------------
# Caso 3 — O PAR QUE DISCRIMINA
# ---------------------------------------------------------------------------


class TestARodadaDeNegociacaoCONTINUAEscrevendoOTopo:
    """A classe sem a qual todas as de cima sao vacuas.

    Um portao que simplesmente parasse de escrever em tudo passaria no caso 1
    (nada mudou) e no caso 2 seria pego so pelo bloco — mas um portao que
    gravasse o bloco e parasse de gravar o topo passaria nos dois. Aqui a
    rodada de negociacao marca retangulos DIFERENTES dos semeados e as chaves
    de topo TEM de mudar.
    """

    @pytest.fixture
    def par(self, monkeypatch, tmp_path: Path) -> tuple[dict, dict]:
        alvo = _semear(tmp_path)
        antes = _ler(alvo)
        assert (
            _rodar(
                monkeypatch,
                tmp_path,
                alvo,
                layout="negociacao",
                frame=FRAME_DA_NEGOCIACAO,
                caixas=CAIXAS_DA_NEGOCIACAO,
            ).rc
            == 0
        )
        return antes, _ler(alvo)

    def test_mercado_grade_MUDOU(self, par: tuple[dict, dict]):
        antes, depois = par
        assert depois["mercado_grade"] != antes["mercado_grade"]
        assert depois["mercado_grade"]["layout"] == "negociacao"

    def test_a_grade_gravada_e_a_QUE_ESTA_RODADA_desenhou(
        self, par: tuple[dict, dict]
    ):
        """"Mudou" sozinho nao diz que mudou para o CERTO."""
        _antes, depois = par
        gx, gy, glarg, galt = CAIXAS_DA_NEGOCIACAO["Grade"]
        ox, oy, _lt, _at = CAIXAS_DA_NEGOCIACAO["Ancora: titulo"]
        grade = depois["mercado_grade"]
        assert grade["dx"] == gx - ox
        assert grade["dy"] == gy - oy
        assert grade["largura"] == glarg
        assert grade["altura"] == galt
        assert grade["altura_da_linha"] == (
            CAIXAS_DA_NEGOCIACAO["Primeira linha"][3]
        )

    @pytest.mark.parametrize(
        ("chave", "titulo"),
        (
            ("mercado_coluna_do_nome", "Coluna: nome"),
            ("mercado_coluna_da_quantidade", "Coluna: quantidade"),
            ("mercado_coluna_do_total", "Coluna: total"),
            ("mercado_coluna_do_unitario", "Coluna: unitario"),
        ),
    )
    def test_as_QUATRO_colunas_de_topo_mudaram(
        self, par: tuple[dict, dict], chave: str, titulo: str
    ):
        antes, depois = par
        assert depois[chave] != antes[chave], chave
        x, _y, largura, _altura = CAIXAS_DA_NEGOCIACAO[titulo]
        ox = CAIXAS_DA_NEGOCIACAO["Ancora: titulo"][0]
        assert depois[chave] == {"dx": x - ox, "largura": largura}

    def test_a_rodada_de_negociacao_NAO_escreve_bloco_aninhado(
        self, par: tuple[dict, dict]
    ):
        """A negociacao mora nas chaves de TOPO e em lugar nenhum mais.
        `_conferir_os_layouts_de_mercado` RECUSA o arranque de uma calibracao
        com `mercado_layouts.negociacao` (05-02), entao grava-la aqui mataria o
        `--mercado` no proximo arranque."""
        _antes, depois = par
        assert "negociacao" not in (depois.get("mercado_layouts") or {})


# ---------------------------------------------------------------------------
# Caso 4 — a recusa sem base
# ---------------------------------------------------------------------------


class TestARecusaQuandoNaoHaDeQuemHerdar:
    """Um layout aninhado guarda so o DELTA e herda o resto de `mercado_grade`.

    Sem a grade de negociacao no arquivo, o bloco gravado apontaria para o
    vazio. E a recusa tem de vir ANTES do primeiro arrasto: onze janelas mais
    tarde o usuario ja gastou a sessao de marcacao inteira.
    """

    def _sem_grade(self, tmp_path: Path) -> Path:
        alvo = _semear(tmp_path)
        dados = _ler(alvo)
        dados["mercado_grade"] = None
        alvo.write_text(json.dumps(dados), encoding="utf-8")
        return alvo

    def test_o_codigo_de_saida_e_DIFERENTE_de_zero(self, monkeypatch, tmp_path: Path):
        alvo = self._sem_grade(tmp_path)
        monkeypatch.setattr(
            cv2,
            "selectROI",
            lambda *a, **k: pytest.fail("pediu arrasto numa rodada recusada"),
        )
        rc = l2scanner.calibrar_mercado.main(
            [
                "--frame",
                str(FRAME_DA_ADENA),
                "--layout",
                "adena",
                "--calibracao",
                str(alvo),
            ]
        )
        assert rc == 1

    def test_a_mensagem_cita_a_grade_de_NEGOCIACAO(self, tmp_path: Path):
        alvo = self._sem_grade(tmp_path)
        args = argparse.Namespace(
            calibracao=str(alvo),
            gravacao=None,
            frame=str(FRAME_DA_ADENA),
            indice=None,
            layout="adena",
            so_digitos=False,
        )
        with pytest.raises(MercadoNaoCalibravel) as erro:
            l2scanner.calibrar_mercado.calibrar(args)
        texto = str(erro.value).lower()
        assert "negociacao" in texto
        assert "herda" in texto or "herdar" in texto

    def test_NENHUM_arrasto_foi_pedido(self, monkeypatch, tmp_path: Path):
        """A afirmacao que distingue "recusou" de "recusou no fim"."""
        alvo = self._sem_grade(tmp_path)
        pedidos: list[str] = []
        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "_selecionar_regiao",
            lambda _p, titulo, _i, sugestao=None: pedidos.append(titulo),
        )
        monkeypatch.setattr(
            cv2,
            "selectROI",
            lambda *a, **k: pedidos.append("cv2.selectROI"),
        )
        args = argparse.Namespace(
            calibracao=str(alvo),
            gravacao=None,
            frame=str(FRAME_DA_ADENA),
            indice=None,
            layout="adena",
            so_digitos=False,
        )
        with pytest.raises(MercadoNaoCalibravel):
            l2scanner.calibrar_mercado.calibrar(args)
        assert pedidos == [], pedidos

    def test_o_arquivo_NAO_foi_reescrito(self, monkeypatch, tmp_path: Path):
        """Recusar e nao gravar sao coisas diferentes, e so a segunda protege."""
        alvo = self._sem_grade(tmp_path)
        antes = alvo.read_text(encoding="utf-8")
        args = argparse.Namespace(
            calibracao=str(alvo),
            gravacao=None,
            frame=str(FRAME_DA_ADENA),
            indice=None,
            layout="adena",
            so_digitos=False,
        )
        with pytest.raises(MercadoNaoCalibravel):
            l2scanner.calibrar_mercado.calibrar(args)
        assert alvo.read_text(encoding="utf-8") == antes

    def test_o_CONTROLE_NEGATIVO_com_a_grade_no_lugar_a_rodada_ANDA(
        self, monkeypatch, tmp_path: Path
    ):
        """Sem ele, "recusou" nao distinguiria a guarda de uma fixtura
        ilegivel ou de um frame que o rastreio nao localiza."""
        alvo = _semear(tmp_path)
        rodada = _rodar(
            monkeypatch,
            tmp_path,
            alvo,
            layout="adena",
            frame=FRAME_DA_ADENA,
            caixas=CAIXAS_DA_ADENA,
        )
        assert rodada.rc == 0
        assert rodada.titulos, "a rodada boa tem de pedir arrasto"

    def test_uma_grade_que_NAO_e_de_negociacao_tambem_recusa(self, tmp_path: Path):
        """Herdar de uma grade de outra aba e herdar do numero errado."""
        alvo = _semear(tmp_path)
        dados = _ler(alvo)
        dados["mercado_grade"] = dict(dados["mercado_grade"], layout="busca")
        alvo.write_text(json.dumps(dados), encoding="utf-8")
        args = argparse.Namespace(
            calibracao=str(alvo),
            gravacao=None,
            frame=str(FRAME_DA_ADENA),
            indice=None,
            layout="adena",
            so_digitos=False,
        )
        with pytest.raises(MercadoNaoCalibravel, match="busca"):
            l2scanner.calibrar_mercado.calibrar(args)


class TestAsOutrasDuasRecusasQueVemAntesDoArrasto:
    """As duas irmas da recusa acima, e as duas custam so um ENTER ao usuario."""

    def test_so_digitos_fora_da_negociacao_recusa(self, tmp_path: Path):
        """Os moldes de digito sao cortados das colunas de moeda da
        NEGOCIACAO, e a pesquisa mediu que eles ja leem a Adena exatamente.
        `--so-digitos --layout adena` pediria um arrasto para jogar fora.

        E o par negativo do retarget feito em `TestAPersistenciaDosGlifos`:
        aquele campo `layout` sempre foi decoracao naquele caminho, e este caso
        prova que a combinacao agora e REALMENTE recusada.
        """
        alvo = _semear(tmp_path)
        args = argparse.Namespace(
            calibracao=str(alvo),
            gravacao=None,
            frame=str(FRAME_DA_ADENA),
            indice=None,
            layout="adena",
            so_digitos=True,
        )
        with pytest.raises(MercadoNaoCalibravel, match="so-digitos"):
            l2scanner.calibrar_mercado.calibrar(args)

    def test_so_digitos_COM_negociacao_continua_valendo(
        self, monkeypatch, tmp_path: Path
    ):
        """O controle negativo: a recusa e sobre o LAYOUT, nao sobre a flag."""
        alvo = _semear(tmp_path)
        assert (
            _rodar(
                monkeypatch,
                tmp_path,
                alvo,
                layout="negociacao",
                frame=FRAME_DA_NEGOCIACAO,
                caixas=CAIXAS_DA_NEGOCIACAO,
                so_digitos=True,
            ).rc
            == 0
        )

    def test_o_layout_busca_recusa_por_nao_ter_modelo_de_coluna_medido(
        self, tmp_path: Path
    ):
        """Ela e um `choice` do CLI desde sempre, e ate hoje marcava as QUATRO
        colunas da negociacao e gravava o topo — a mesma bomba. Ninguem mediu o
        modelo de coluna dela e ela nao tem leitora de linha (05-02)."""
        alvo = _semear(tmp_path)
        args = argparse.Namespace(
            calibracao=str(alvo),
            gravacao=None,
            frame=str(FRAME_DA_ADENA),
            indice=None,
            layout="busca",
            so_digitos=False,
        )
        with pytest.raises(MercadoNaoCalibravel, match="busca"):
            l2scanner.calibrar_mercado.calibrar(args)


class TestSemMoldeDeCabecalhoNadaEGravado:
    """T-05-11. O molde E o portao (`_casamento_do_layout`, 05-02).

    Um bloco sem molde e um layout que o leitor NUNCA escolhe: ele ficaria no
    arquivo afirmando uma calibracao que nao existe, e a proxima pessoa a abrir
    o JSON leria "a Adena esta calibrada".
    """

    def _rodar_sem_molde(self, monkeypatch, tmp_path: Path, alvo: Path):
        monkeypatch.setattr(
            l2scanner.calibrar_mercado,
            "_cortar_o_cabecalho",
            lambda *a, **k: (None, None),
        )
        return _rodar(
            monkeypatch,
            tmp_path,
            alvo,
            layout="adena",
            frame=FRAME_DA_ADENA,
            caixas=CAIXAS_DA_ADENA,
        )

    def test_a_rodada_recusa_dizendo_por_que(self, monkeypatch, tmp_path: Path):
        alvo = _semear(tmp_path)
        with pytest.raises(MercadoNaoCalibravel, match="cabecalho"):
            self._rodar_sem_molde(monkeypatch, tmp_path, alvo)

    def test_o_bloco_NAO_ficou_no_arquivo(self, monkeypatch, tmp_path: Path):
        alvo = _semear(tmp_path)
        with pytest.raises(MercadoNaoCalibravel):
            self._rodar_sem_molde(monkeypatch, tmp_path, alvo)
        assert "mercado_layouts" not in _ler(alvo)

    def test_e_o_topo_continua_intacto_tambem_nesse_caminho(
        self, monkeypatch, tmp_path: Path
    ):
        alvo = _semear(tmp_path)
        antes = _ler(alvo)
        with pytest.raises(MercadoNaoCalibravel):
            self._rodar_sem_molde(monkeypatch, tmp_path, alvo)
        assert _ler(alvo) == antes


# ---------------------------------------------------------------------------
# Caso 5 — a ida e volta
# ---------------------------------------------------------------------------


class _ContadoraDeOCR:
    def __init__(self) -> None:
        self.chamadas = 0

    def __call__(self, _pixels) -> str:
        self.chamadas += 1
        return "Common Fafurion Doll"


class TestAIdaEVolta:
    """O que a ferramenta GRAVA, o leitor CONSOME.

    Um bloco que a ferramenta escreve e o leitor nao le e geometria morta, e ela
    passaria em todos os casos acima: eles medem o arquivo, e este mede a
    LEITURA. As nove linhas de taxa sao o mesmo numero que o 05-02 mediu sobre a
    fixtura versionada — a diferenca e que aqui a calibracao veio da ferramenta.
    """

    @pytest.fixture
    def calibracao_gravada(self, monkeypatch, tmp_path: Path) -> Calibracao:
        alvo = _semear(tmp_path)
        assert (
            _rodar(
                monkeypatch,
                tmp_path,
                alvo,
                layout="adena",
                frame=FRAME_DA_ADENA,
                caixas=CAIXAS_DA_ADENA,
            ).rc
            == 0
        )
        return Calibracao.carregar(alvo)

    def test_o_arquivo_gravado_CARREGA_sem_levantar(
        self, calibracao_gravada: Calibracao
    ):
        """`_conferir_os_layouts_de_mercado` roda no arranque (05-02): um bloco
        torto mataria o `--mercado` no proximo `run.bat`."""
        assert calibracao_gravada.mercado_layouts["adena"]["colunas"]

    def test_a_pagina_da_adena_sai_com_NOVE_linhas_de_taxa(
        self, calibracao_gravada: Calibracao
    ):
        aceita = self._pagina(calibracao_gravada)
        assert aceita is not None
        assert len(aceita.linhas) == 9

    def test_toda_linha_carrega_a_SENTINELA_da_adena(
        self, calibracao_gravada: Calibracao
    ):
        aceita = self._pagina(calibracao_gravada)
        assert {linha.chave_da_serie for linha in aceita.linhas} == {
            CHAVE_DA_SERIE_DA_ADENA
        }

    def test_o_CONTROLE_NEGATIVO_sem_o_bloco_a_pagina_e_RECUSADA(
        self, monkeypatch, tmp_path: Path
    ):
        """Sem ele, "nove linhas" nao distinguiria o bloco gravado pela
        ferramenta de uma pagina que sairia lida de qualquer jeito."""
        alvo = _semear(tmp_path)
        cal = Calibracao.carregar(alvo)
        assert cal.mercado_layouts is None
        assert self._pagina(cal) is None

    def _pagina(self, cal: Calibracao):
        """A pagina depois do ACORDO ENTRE DOIS FRAMES, como na producao."""
        janela = cv2.imread(str(FRAME_DA_ADENA), cv2.IMREAD_COLOR)
        assert isinstance(janela, np.ndarray)
        leitor = LeitorDePagina(
            RastreioDoPainel(
                ancoras_de_calibracao(cal.mercado_ancoras),
                float(cal.mercado_limiar_da_ancora),
            ),
            {},
            _ContadoraDeOCR(),
            _ContadoraDeOCR(),
            cal,
        )
        assert leitor.observar(janela) is None
        return leitor.observar(janela)


# ---------------------------------------------------------------------------
# A disciplina do arquivo, afirmada e nao so prometida
# ---------------------------------------------------------------------------


class TestNadaDesteArquivoAlcancaAMaquinaDoUsuario:
    def test_a_semente_e_apenas_COPIADA_e_nunca_escrita(self, tmp_path: Path):
        antes = SEMENTE.read_bytes()
        alvo = _semear(tmp_path)
        alvo.write_text("{}", encoding="utf-8")
        assert SEMENTE.read_bytes() == antes

    def test_todo_caso_aponta_calibracao_para_dentro_de_tmp_path(
        self, tmp_path: Path
    ):
        """A leitura literal do seam: `_semear` so sabe escrever em `tmp_path`."""
        alvo = _semear(tmp_path)
        assert alvo.parent == tmp_path

    def test_o_padrao_do_modulo_APONTA_PARA_FORA_da_maquina(self):
        """A guarda ESTRUTURAL, e nao uma promessa em prosa.

        A unica forma de esta suite alcancar o `calibration.json` da maquina
        seria omitir `--calibracao` e cair em `ARQUIVO_CALIBRACAO`. O fixture
        autouse acima desvia aquele padrao para um caminho INEXISTENTE dentro de
        `tmp_path`, entao um caso que esquecesse a flag nao leria o arquivo do
        usuario: ele estouraria com "nao encontrei". Varrer o fonte por
        substring seria mais fraco — e, como o proprio assert contem a
        substring, tambem seria autofalso.
        """
        padrao = l2scanner.calibrar_mercado.ARQUIVO_CALIBRACAO
        assert padrao.name == "calibration.json"
        assert not padrao.exists(), padrao
        assert "pytest" in str(padrao).lower() or "tmp" in str(padrao).lower(), (
            padrao
        )


def test_a_semente_existe_no_repositorio():
    """Guarda de vacuidade: se a fixtura sumisse, todo caso acima ficaria
    verde por erro de colecao em vez de por medicao."""
    assert SEMENTE.exists()
    assert FRAME_DA_ADENA.exists()
    assert FRAME_DA_NEGOCIACAO.exists()
