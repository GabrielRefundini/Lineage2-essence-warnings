"""Uma rodada do calibrador da RENDA nao pode apagar nada -- nem do vizinho.

O DANO, COM ENDERECO E DATA. Em 2026-08-30 uma rodada de `calibrar.bat` apagou
do `calibration.json` os 13 moldes de glifo cortados a mao, as 3 ancoras do
painel, a grade de negociacao e o `mercado_limiar_de_glifo` -- mais
`banner_manutencao`, `tiat_chat` e `tiat_alvo`, pelo mesmo mecanismo:
`calibrar_automatico` montava uma `Calibracao` DO ZERO e o `salvar` gravava o
objeto inteiro. Era load-mutate-save SEM o load. O arquivo e gitignored
(`.gitignore:51`), entao nao existe `git checkout` que traga nada de volta; o
resgate foi manual e o arquivo dele ainda esta na raiz do repositorio com o
nome que o denuncia.

O calibrador da renda e o QUARTO escritor daquele arquivo, e o mais novo.

DOIS CRITERIOS PLAUSIVEIS QUE SAO VACUOS AQUI, escritos para o proximo leitor
nao os reintroduzir:

- `git status --porcelain calibration.json` sai VAZIO SEMPRE. O arquivo e
  gitignored, entao o git nao tem opiniao sobre ele: o comando devolve string
  vazia com o arquivo intacto, com o arquivo destruido e com o arquivo apagado.
  Um teste construido sobre ele passaria com a calibracao no lixo.
- `git diff --numstat` sobre um arquivo NAO RASTREADO devolve 0 tendo removido
  zero ou quatrocentas linhas, pela mesma razao.

O QUE DISCRIMINA e comparar o CONTEUDO PARSEADO antes e depois, chave por
chave, com as chaves ENUMERADAS A PARTIR DO ARQUIVO DE ANTES -- assim o caso
cobre tambem as chaves de topo que ainda nem existem hoje.

O QUE ESTE ARQUIVO NAO ESTA PROVANDO, dito com endereco para ninguem concluir
que ha teste duplicado e apagar o errado. O defeito que o `01-CONTEXT.md` desta
fase citou (`calibrar_mercado.py:2721`) JA FOI CONSERTADO no commit `f8dbfe2` e
JA ESTA PRESO por `tests/test_calibrar_layout_nao_apaga_negociacao.py`. Nao se
planeja teste contra defeito morto. Este arquivo mira o risco VIVO, que e outro
e e pior: o `salvar` e uma enumeracao literal e nao preserva chave desconhecida.

E O IRMAO NOVO, QUE A MEDICAO DE CAMPO OBRIGOU: O PERSONAGEM VIZINHO. Ele nao
duplica o teste estrutural do `01-01` (`tests/test_calibracao_renda.py`), e a
diferenca e de CAMADA. Aquele prende a SUPERFICIE do dataclass: ele ve que
`renda_por_personagem` e emitida. Ele NAO VE NADA DENTRO DELA, e desde o achado
M-F ha uma dimensao inteira la dentro -- um personagem por chave. Um calibrador
que remontasse aquele dicionario a partir do personagem que acabou de calibrar
apagaria o outro SEM QUE TESTE NENHUM DESTE REPOSITORIO PERCEBESSE: o campo
continuaria presente, a versao continuaria 2, o `carregar` continuaria feliz, e
a Yazalaque simplesmente pararia de ser lida.

E o incidente de 2026-08-30 outra vez, uma camada abaixo e com a mesma forma:
um escritor montando do zero o que devia ter carregado.

DISCIPLINA INEGOCIAVEL DESTE ARQUIVO, herdada verbatim dos dois precedentes:
todo caso monkeypatcha `ARQUIVO_CALIBRACAO` para dentro de `tmp_path`. E a
unica coisa que mantem o `calibration.json` da maquina do usuario fora do
alcance desta suite. Quem remover a linha achando que e ruido reproduz o
incidente dentro do CI, desta vez sem resgate.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from dataclasses import fields, make_dataclass
from pathlib import Path

import numpy as np
import pytest

import l2scanner.calibrar
import l2scanner.calibrar_renda as cr
from l2scanner.calibracao import Calibracao, descrever_geometria_da_tela
from l2scanner.frames import Regiao

sys.path.insert(0, str(Path(__file__).resolve().parent))

# O SEMEADOR E IMPORTADO E NAO COPIADO. Ele carrega 27 campos que a party nao
# possui, ja com os valores que passam por todos os validadores do arranque, e
# ele SE PROVA antes de o teste acusar o codigo sob teste (a linha
# `Calibracao.carregar(alvo)` no fim dele). Uma copia divergiria da fixtura de
# mercado no primeiro campo novo, e a divergencia apareceria como vermelho com
# sintoma indistinguivel do defeito real. O precedente de import entre arquivos
# de teste desta casa e `test_aprendiz.py` importando de `test_acervo.py`.
from test_calibrar_nao_apaga_mercado import (  # noqa: E402
    _dirigir,
    _nova_party,
    _semear,
)

RAIZ = Path(__file__).resolve().parent.parent

# Os retangulos MEDIDOS de cada instancia (M-F). Eles estao aqui como DADO DE
# TESTE e nao como constante de producao: sao 14 px na vertical e 10 na
# horizontal de diferenca, e e essa distancia que faz o caso do vizinho valer
# alguma coisa. Dois personagens com o mesmo retangulo nao provariam nada.
NIVEL_DA_FAERLINA = {"esquerda": 246, "topo": 736, "largura": 30, "altura": 20}
NIVEL_DA_YAZALAQUE = {"esquerda": 236, "topo": 750, "largura": 30, "altura": 20}

# O retangulo que a rodada VAI marcar, propositalmente diferente dos dois acima:
# e ele que faz o CONTROLE POSITIVO conseguir ver a diferenca.
RETANGULO_NOVO = (300, 400, 50, 30)


@pytest.fixture(scope="module")
def geo() -> str:
    return descrever_geometria_da_tela()


def _bloco(regiao: dict, piso: int, largura: int) -> dict:
    return {
        "regiao": dict(regiao),
        "piso_de_brilho": piso,
        "largura_da_banda": largura,
    }


def _entrada(nivel: dict, *, piso: int) -> dict:
    return {
        "barra_esquerda": _bloco(
            {"esquerda": 0, "topo": 1368, "largura": 520, "altura": 24}, piso, 7
        ),
        "barra_direita": _bloco(
            {"esquerda": 1540, "topo": 1358, "largura": 160, "altura": 34}, 185, 3
        ),
        "nivel": _bloco(nivel, piso + 40, 5),
        "geometria_da_janela": {"largura": 1720, "altura": 1392},
        # A SUB-CHAVE QUE ESTE CODIGO NAO CONHECE. Ela existe para provar que a
        # mutacao e por COPIA COM SUBSTITUICAO e nao por reconstrucao: um
        # dicionario remontado a partir do que o calibrador conhece hoje apaga
        # o campo que uma versao futura acrescentar, calado.
        "uma_chave_que_o_codigo_de_hoje_nao_conhece": {"vale": 42},
    }


def _semear_com_renda(alvo: Path, geo: str) -> dict:
    """Semeia party + mercado + tiat, e ACRESCENTA os dois personagens.

    A ordem importa: `_semear` grava e depois se prova pelo `carregar`. A renda
    entra por cima e o arquivo e reprovado, porque um arquivo que o `carregar`
    recusa faria os casos ficarem vermelhos com sintoma indistinguivel do
    defeito real.
    """
    _semear(alvo, geo)
    dados = json.loads(alvo.read_text(encoding="utf-8"))
    dados["renda_por_personagem"] = {
        "Faerlina": _entrada(NIVEL_DA_FAERLINA, piso=160),
        "Yazalaque": _entrada(NIVEL_DA_YAZALAQUE, piso=150),
    }
    alvo.write_text(json.dumps(dados, indent=2), encoding="utf-8")
    Calibracao.carregar(alvo)
    return json.loads(alvo.read_text(encoding="utf-8"))


def _rodar_a_renda(
    monkeypatch,
    alvo: Path,
    personagem: str,
    *,
    retangulo=RETANGULO_NOVO,
    varredura=None,
) -> int:
    """Uma rodada inteira do calibrador da renda, sem mouse e sem highgui.

    `_selecionar_regiao` e o seam, como na suite inteira desta casa. O
    `cv2.selectROI` de verdade e trocado por uma BOMBA no mesmo gesto: se algum
    caminho novo passar por fora do seam, o teste estoura em vez de abrir uma
    janela de verdade no meio do CI.

    A VARREDURA DE OCR E DUBLADA POR PADRAO. Nao e para acelerar: e para o
    arquivo inteiro rodar no Python global, que nao tem as bindings de WinRT.
    O que se mede aqui e a NAO-DESTRUICAO, e ela nao depende do motor de OCR.
    """
    import cv2

    def _bomba(*_a, **_k):
        raise AssertionError(
            "cv2.selectROI de VERDADE foi chamado: algum caminho escapou do "
            "seam `_selecionar_regiao` e abriria uma janela no CI"
        )

    monkeypatch.setattr(cv2, "selectROI", _bomba)
    # NAO REMOVA: e o que mantem o calibration.json REAL fora do alcance.
    monkeypatch.setattr(cr, "ARQUIVO_CALIBRACAO", alvo)
    monkeypatch.setattr(
        cr, "_selecionar_regiao", lambda *_a, **_k: retangulo
    )
    monkeypatch.setattr(cr, "_gravar_conferencia", lambda _tela: None)
    monkeypatch.setattr(
        cr, "_varrer_as_regioes_de_ocr", varredura or (lambda *_a, **_k: {})
    )
    frame = np.zeros((1392, 1720, 3), dtype=np.uint8)
    monkeypatch.setattr(
        cr, "_resolver_a_fonte", lambda _args, _cal: (frame, personagem, None, None)
    )
    return cr.main(["--imagem", "irrelevante.png", "--personagem", personagem])


def _rodar_o_tiat(monkeypatch, alvo: Path) -> int:
    """O SEGUNDO escritor, que e o unico que pega o esquecimento no `salvar`."""
    import cv2

    class _JanelaFalsa:
        def __init__(self, *a, **k):
            pass

        def capturar_completo(self):
            return np.zeros((400, 400, 3), dtype=np.uint8)

        def fechar(self):
            pass

    monkeypatch.setattr(l2scanner.calibrar, "ARQUIVO_CALIBRACAO", alvo)
    monkeypatch.setattr(l2scanner.calibrar, "JanelaSource", _JanelaFalsa)
    monkeypatch.setattr(
        l2scanner.calibrar, "_selecionar_regiao", lambda *_a, **_k: (1, 2, 3, 4)
    )
    monkeypatch.setattr(
        l2scanner.calibrar, "_gravar_conferencia", lambda _tela: None
    )
    monkeypatch.setattr(cv2, "rectangle", lambda *a, **k: None)
    monkeypatch.setattr(cv2, "putText", lambda *a, **k: None)
    return l2scanner.calibrar.calibrar_tiat("Faerlina - XM Essence")


def _chaves_de_topo_de_antes(antes: dict) -> list[str]:
    """Enumeradas A PARTIR DO ARQUIVO, e nunca de uma lista escrita a mao.

    `renda_por_personagem` fica de fora porque ela E o destino legitimo da
    escrita. Toda outra chave de topo tem de voltar identica -- inclusive as
    que ainda nem existem hoje.
    """
    return [chave for chave in antes if chave != "renda_por_personagem"]


class TestARendaNaoApagaOQueEDosOutros:
    def test_NENHUMA_CHAVE_DE_TOPO_MUDOU_DE_VALOR(self, monkeypatch, tmp_path, geo):
        alvo = tmp_path / "calibration.json"
        antes = _semear_com_renda(alvo, geo)

        assert _rodar_a_renda(monkeypatch, alvo, "Faerlina") == 0

        depois = json.loads(alvo.read_text(encoding="utf-8"))
        mudadas = [
            chave
            for chave in _chaves_de_topo_de_antes(antes)
            if depois.get(chave) != antes[chave]
        ]
        assert not mudadas, (
            f"a rodada da renda MUDOU chaves que nao sao dela: {mudadas}"
        )

    def test_NENHUMA_CHAVE_DE_TOPO_DESAPARECEU(self, monkeypatch, tmp_path, geo):
        alvo = tmp_path / "calibration.json"
        antes = _semear_com_renda(alvo, geo)

        assert _rodar_a_renda(monkeypatch, alvo, "Faerlina") == 0

        depois = json.loads(alvo.read_text(encoding="utf-8"))
        sumidas = sorted(set(antes) - set(depois))
        assert not sumidas, f"a rodada da renda APAGOU chaves de topo: {sumidas}"

    def test_OS_TREZE_MOLDES_DE_GLIFO_CONTINUAM_IDENTICOS(
        self, monkeypatch, tmp_path, geo
    ):
        """Treze, e a contagem e afirmada ANTES da comparacao.

        Sao os treze que o incidente de 2026-08-30 custou. Se a fixtura mudar de
        tamanho, este caso precisa ser reapontado -- e a mensagem diz isso, em
        vez de o caso passar comparando duas listas vazias.
        """
        alvo = tmp_path / "calibration.json"
        antes = _semear_com_renda(alvo, geo)
        moldes = antes["mercado_templates_de_digito"]
        assert len(moldes) == 13, (
            f"a fixtura tem {len(moldes)} moldes e nao 13 -- retarget este caso "
            f"em vez de afrouxa-lo"
        )

        assert _rodar_a_renda(monkeypatch, alvo, "Faerlina") == 0

        depois = json.loads(alvo.read_text(encoding="utf-8"))
        assert depois["mercado_templates_de_digito"] == moldes

    def test_CONTROLE_POSITIVO_A_RODADA_GRAVOU_RETANGULOS_DIFERENTES(
        self, monkeypatch, tmp_path, geo
    ):
        """Sem este caso, um calibrador que NAO ESCREVE NADA passa nos tres

        acima com louvor. E o par que discrimina.
        """
        alvo = tmp_path / "calibration.json"
        antes = _semear_com_renda(alvo, geo)

        assert _rodar_a_renda(monkeypatch, alvo, "Faerlina") == 0

        depois = json.loads(alvo.read_text(encoding="utf-8"))
        novo = depois["renda_por_personagem"]["Faerlina"]["nivel"]["regiao"]
        velho = antes["renda_por_personagem"]["Faerlina"]["nivel"]["regiao"]
        assert novo != velho, "a rodada nao escreveu nada; os casos acima sao vacuos"
        assert novo == Regiao(*RETANGULO_NOVO).como_dict()

    def test_CONTROLE_POSITIVO_A_RODADA_GRAVOU_O_PISO_MEDIDO(
        self, monkeypatch, tmp_path, geo
    ):
        """O outro lado do controle: a rodada tambem escreve PISO, e nao so

        retangulo. Sem ele, um calibrador que gravasse retangulo e ignorasse a
        varredura passaria.
        """
        alvo = tmp_path / "calibration.json"
        antes = _semear_com_renda(alvo, geo)

        def _varredura(_frame, _entrada, _pisos):
            linhas = cr.varrer_o_piso(
                None,
                (200, 205, 210),
                campo="nivel",
                gramatica=cr.inteiro_pela_gramatica_do_jogo,
                ler_escalas=lambda _r, _p: {
                    cr.ESCALA_DE_DETECCAO: "67",
                    cr.ESCALA_DE_CONFERENCIA: "67",
                },
            )
            return {"nivel": (linhas, None)}

        assert (
            _rodar_a_renda(monkeypatch, alvo, "Faerlina", varredura=_varredura) == 0
        )

        depois = json.loads(alvo.read_text(encoding="utf-8"))
        bloco = depois["renda_por_personagem"]["Faerlina"]["nivel"]
        assert bloco["piso_de_brilho"] == 205, "o piso gravado nao e o CENTRO da banda"
        assert bloco["largura_da_banda"] == 3
        assert (
            bloco["piso_de_brilho"]
            != antes["renda_por_personagem"]["Faerlina"]["nivel"]["piso_de_brilho"]
        )


class TestOPersonagemVizinhoSobrevive:
    """O caso que a medicao de campo obrigou, e que nenhum arquivo deste

    repositorio tinha -- porque nenhuma feature era por personagem ate hoje.
    Ver a docstring do modulo para por que ele NAO e duplicata do teste
    estrutural do `01-01`.
    """

    def test_CALIBRAR_A_FAERLINA_DEIXA_A_YAZALAQUE_BYTE_A_BYTE_IDENTICA(
        self, monkeypatch, tmp_path, geo
    ):
        alvo = tmp_path / "calibration.json"
        antes = _semear_com_renda(alvo, geo)
        vizinha = antes["renda_por_personagem"]["Yazalaque"]

        assert _rodar_a_renda(monkeypatch, alvo, "Faerlina") == 0

        depois = json.loads(alvo.read_text(encoding="utf-8"))
        assert depois["renda_por_personagem"]["Yazalaque"] == vizinha, (
            "a entrada da Yazalaque mudou numa rodada da Faerlina. O campo "
            "continuaria presente, a versao continuaria 2 e o `carregar` "
            "continuaria feliz -- e ela simplesmente pararia de ser lida."
        )

    def test_AS_REGIOES_OS_PISOS_E_A_GEOMETRIA_DA_VIZINHA_SAO_OS_MESMOS(
        self, monkeypatch, tmp_path, geo
    ):
        """A afirmacao campo a campo, para a mensagem de falha dizer QUAL parte

        se perdeu em vez de "o dicionario mudou".
        """
        alvo = tmp_path / "calibration.json"
        antes = _semear_com_renda(alvo, geo)
        vizinha = antes["renda_por_personagem"]["Yazalaque"]

        assert _rodar_a_renda(monkeypatch, alvo, "Faerlina") == 0
        agora = json.loads(alvo.read_text(encoding="utf-8"))[
            "renda_por_personagem"
        ]["Yazalaque"]

        for regiao in ("barra_esquerda", "barra_direita", "nivel"):
            assert agora[regiao]["regiao"] == vizinha[regiao]["regiao"], regiao
            assert (
                agora[regiao]["piso_de_brilho"] == vizinha[regiao]["piso_de_brilho"]
            ), regiao
            assert (
                agora[regiao]["largura_da_banda"]
                == vizinha[regiao]["largura_da_banda"]
            ), regiao
        assert agora["geometria_da_janela"] == vizinha["geometria_da_janela"]
        assert agora["nivel"]["regiao"] == NIVEL_DA_YAZALAQUE, (
            "a Yazalaque ficou com o retangulo da Faerlina: sao 14 px na "
            "vertical, e o retangulo do vizinho devolve numero PLAUSIVEL e "
            "errado, nao campo vazio (M-F)"
        )

    def test_UMA_SUBCHAVE_DESCONHECIDA_DO_VIZINHO_TAMBEM_SOBREVIVE(
        self, monkeypatch, tmp_path, geo
    ):
        alvo = tmp_path / "calibration.json"
        _semear_com_renda(alvo, geo)

        assert _rodar_a_renda(monkeypatch, alvo, "Faerlina") == 0

        depois = json.loads(alvo.read_text(encoding="utf-8"))
        assert depois["renda_por_personagem"]["Yazalaque"][
            "uma_chave_que_o_codigo_de_hoje_nao_conhece"
        ] == {"vale": 42}

    def test_A_SUBCHAVE_DESCONHECIDA_DO_PROPRIO_CALIBRADO_TAMBEM_SOBREVIVE(
        self, monkeypatch, tmp_path, geo
    ):
        """A mutacao e por COPIA COM SUBSTITUICAO e nao por reconstrucao.

        Este e o caso que separa as duas: numa reconstrucao o vizinho some E o
        campo novo do proprio personagem some junto, e so o primeiro tem teste.
        """
        alvo = tmp_path / "calibration.json"
        _semear_com_renda(alvo, geo)

        assert _rodar_a_renda(monkeypatch, alvo, "Faerlina") == 0

        depois = json.loads(alvo.read_text(encoding="utf-8"))
        assert depois["renda_por_personagem"]["Faerlina"][
            "uma_chave_que_o_codigo_de_hoje_nao_conhece"
        ] == {"vale": 42}


class TestAIdaEVoltaComOutroEscritor:
    """O unico caso em que um SEGUNDO escritor passa por cima -- e e ele que

    pega o esquecimento no `salvar`, porque o `salvar` e uma enumeracao literal
    e uma chave que nao esta nela some sem uma linha de log.
    """

    def test_RENDA_E_DEPOIS_TIAT_DEIXA_OS_DOIS_PERSONAGENS_DE_PE(
        self, monkeypatch, tmp_path, geo
    ):
        alvo = tmp_path / "calibration.json"
        _semear_com_renda(alvo, geo)

        assert _rodar_a_renda(monkeypatch, alvo, "Faerlina") == 0
        da_renda = json.loads(alvo.read_text(encoding="utf-8"))[
            "renda_por_personagem"
        ]

        assert _rodar_o_tiat(monkeypatch, alvo) == 0

        depois = json.loads(alvo.read_text(encoding="utf-8"))
        assert depois["renda_por_personagem"] == da_renda, (
            "o calibrador do aviso de boss passou por cima da renda"
        )
        assert sorted(depois["renda_por_personagem"]) == ["Faerlina", "Yazalaque"]

    def test_RENDA_E_DEPOIS_A_PARTY_DEIXA_OS_DOIS_PERSONAGENS_DE_PE(
        self, monkeypatch, tmp_path, geo
    ):
        """O caminho da party e o que causou o incidente de 2026-08-30, e o que

        o `fundir_com_a_calibracao_em_disco` consertou. A renda e um campo NOVO
        naquele caminho: ela sobrevive por SUBTRACAO de `fields(Calibracao)`, e
        nao por alguem ter lembrado de inscreve-la numa lista.
        """
        alvo = tmp_path / "calibration.json"
        _semear_com_renda(alvo, geo)

        assert _rodar_a_renda(monkeypatch, alvo, "Faerlina") == 0
        da_renda = json.loads(alvo.read_text(encoding="utf-8"))[
            "renda_por_personagem"
        ]

        assert _dirigir(monkeypatch, alvo, ["--auto"], _nova_party(geo)) == 0

        depois = json.loads(alvo.read_text(encoding="utf-8"))
        assert depois["renda_por_personagem"] == da_renda
        assert sorted(depois["renda_por_personagem"]) == ["Faerlina", "Yazalaque"]

    def test_O_TIAT_TAMBEM_NAO_APAGA_A_CHAVE_DOS_MOLDES_DA_BARRA(
        self, monkeypatch, tmp_path, geo
    ):
        """A outra chave da renda, que e de TOPO e nao mora dentro da primeira.

        Ela e escrita pelo `01-05` e nao por este calibrador, mas quem apaga uma
        apaga a outra pelo mesmo mecanismo.
        """
        alvo = tmp_path / "calibration.json"
        _semear_com_renda(alvo, geo)
        dados = json.loads(alvo.read_text(encoding="utf-8"))
        dados["renda_moldes_da_barra"] = {
            "moldes": [
                {
                    "glifo": "0",
                    "altura": 9,
                    "largura": 4,
                    "molde": {
                        "altura": 9,
                        "largura": 4,
                        "bytes": bytes(range(36)).hex(),
                    },
                }
            ],
            "piso_de_leitura": 0.47,
            "margem_de_leitura": 0.037,
            "folga_de_cola": None,
        }
        alvo.write_text(json.dumps(dados, indent=2), encoding="utf-8")
        Calibracao.carregar(alvo)
        antes = json.loads(alvo.read_text(encoding="utf-8"))["renda_moldes_da_barra"]

        assert _rodar_a_renda(monkeypatch, alvo, "Faerlina") == 0
        assert _rodar_o_tiat(monkeypatch, alvo) == 0

        depois = json.loads(alvo.read_text(encoding="utf-8"))
        assert depois["renda_moldes_da_barra"] == antes


class TestOControleDoCampoNovo:
    """A conferencia estrutural pegaria um campo que AINDA NAO EXISTE.

    ELE MORA AQUI E NAO NO ARQUIVO DO `01-01`, e a diferenca e o ponto: o
    controle de la REMOVE uma chave do dicionario emitido e prova que a
    conferencia FUNCIONA. Este SINTETIZA uma dataclass com um campo A MAIS e
    prova que ela pegaria um campo que ainda nao existe -- que e o modo de
    falha de verdade, porque ninguem remove uma chave do `salvar` de proposito,
    mas todo mundo acrescenta campo ao dataclass.

    A dataclass sintetica e montada A PARTIR de `fields(Calibracao)` mais um
    campo, sem enumerar nomes a mao: uma lista escrita a mao envelheceria
    contra o dataclass no primeiro campo novo, que e exatamente o evento que
    este caso existe para cobrir.
    """

    NOME_DO_CAMPO_NOVO = "renda_um_campo_que_ainda_nao_existe"

    def _campos_menos_chaves(self, tipo, dados: dict) -> set[str]:
        return {campo.name for campo in fields(tipo)} - set(dados)

    def _emitido(self, tmp_path: Path, geo: str) -> dict:
        alvo = tmp_path / "emitido.json"
        _semear_com_renda(alvo, geo)
        return json.loads(alvo.read_text(encoding="utf-8"))

    def test_HOJE_A_CONFERENCIA_ESTA_VERDE(self, tmp_path, geo):
        """O portao nasce verde -- e por isso o controle abaixo e obrigatorio."""
        dados = self._emitido(tmp_path, geo)
        assert not self._campos_menos_chaves(Calibracao, dados)

    def test_CONTROLE_UM_CAMPO_A_MAIS_E_ACUSADO_PELO_NOME(self, tmp_path, geo):
        sintetica = make_dataclass(
            "CalibracaoComUmCampoAMais",
            [
                (campo.name, campo.type, dataclasses.field(default=None))
                for campo in fields(Calibracao)
            ]
            + [(self.NOME_DO_CAMPO_NOVO, "dict | None", dataclasses.field(default=None))],
        )
        dados = self._emitido(tmp_path, geo)

        faltando = self._campos_menos_chaves(sintetica, dados)
        assert faltando == {self.NOME_DO_CAMPO_NOVO}, (
            f"a conferencia estrutural NAO acusou o campo novo pelo nome: "
            f"{sorted(faltando)}. Ela pegaria a remocao de uma chave e nao o "
            f"acrescimo de um campo -- que e o que de fato acontece."
        )

    def test_O_CONTROLE_USA_A_LISTA_DO_DATACLASS_E_NAO_UMA_ESCRITA_A_MAO(self):
        sintetica = make_dataclass(
            "CalibracaoComUmCampoAMais",
            [
                (campo.name, campo.type, dataclasses.field(default=None))
                for campo in fields(Calibracao)
            ]
            + [(self.NOME_DO_CAMPO_NOVO, "dict | None", dataclasses.field(default=None))],
        )
        assert {campo.name for campo in fields(sintetica)} == {
            campo.name for campo in fields(Calibracao)
        } | {self.NOME_DO_CAMPO_NOVO}


class TestOArquivoNaoEscreveForaDoTmpPath:
    def test_TODA_RODADA_APONTA_ARQUIVO_CALIBRACAO_PARA_O_TMP_PATH(self):
        """A disciplina afirmada por leitura do proprio arquivo de teste.

        Ela e a unica coisa que mantem o `calibration.json` da maquina do
        usuario fora do alcance desta suite, e ela e facil de remover sem
        querer num refator.
        """
        fonte = Path(__file__).read_text(encoding="utf-8")
        assert fonte.count("ARQUIVO_CALIBRACAO") >= 1
        assert "NAO REMOVA" in fonte
