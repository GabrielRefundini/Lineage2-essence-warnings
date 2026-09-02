"""A fatia fina da leitura da renda: de um PNG resgatado ao EXP com quatro casas.

O QUE ESTE ARQUIVO EXISTE PARA IMPEDIR
======================================
1. **Que um numero errado saia com cara de numero certo.** A gramatica do EXP
   e uma TRAVA: quatro casas ou recusa. Tres casas, cinco casas ou ausencia do
   sinal de porcentagem NAO viram arredondamento e NAO viram completar com
   zero. Um EXP de duas casas tratado como se tivesse quatro e uma mentira que
   ninguem consegue ver depois de gravada.
2. **Que um retangulo grande demais seja fatiado em silencio.** Medido: numa
   janela de altura 1392, `frame[1368 : 1368+26]` devolve **24 linhas**, sem
   levantar, sem avisar e sem marcar o array. Uma leitura de 24 linhas em vez
   de 26 e plausivel e errada.
3. **Que a leitura de um personagem caia na calibracao do outro.** Medido com
   as duas instancias vivas: a janela de status da Faerlina poe o nivel em
   `246,736` e a da Yazalaque em `236,750`. Ler uma com o retangulo da outra
   nao devolve campo vazio — devolve `349` ou `112`, numeros desenhados ao lado
   do nivel que passam por qualquer validacao sem reclamar.
4. **Que o cruzamento de escalas volte a exigir IGUALDADE.** Medido, as duas
   escalas de OCR quase nunca concordam: elas se revezam. Com "as duas tem que
   dar o mesmo numero" o nivel de uma das instancias seria recusado PARA
   SEMPRE, e recusar 100% das amostras e o mesmo que nao ter medidor.
5. **Que uma chave nova do `calibration.json` derrube o arranque de quem nao
   calibrou.** As duas chaves da renda sao opcionais e a versao do esquema NAO
   sobe; o conjunto de moldes tem TRES posicoes legitimas — ausente, completo e
   **incompleto** — e so a malformada e recusada.

DE ONDE VEM CADA FIXTURA
========================
Todas foram **resgatadas** para `tests/fixtures/renda/`, e nenhum teste deste
arquivo abre a pasta de gravacoes: ela e gitignored e nao vem de clone limpo,
entao um teste apoiado nela ficaria verde nesta maquina e amarelo em qualquer
outra. A proveniencia de cada uma esta em `tests/fixtures/renda/LEIA-ME.md`,
com a verdade de campo lida a olho.

A VERDADE DE CAMPO, e ela e o que separa "o codigo faz alguma coisa" de "o
codigo faz a coisa certa":

    Faerlina    nivel 67   EXP 8,0012%    adena 13.160.684
    Yazalaque   nivel 69   EXP 76,6646%   adena 1.696.020

O SKIP POR AUSENCIA DE OCR
==========================
As bindings do WinRT sao modulares e nao existem no Python que roda esta suite
por padrao — so no ambiente de producao do usuario. As classes que dependem do
motor pulam, e a razao do skip carrega o COMANDO que as faz rodar. As outras
— gramatica, cruzamento, guarda de recorte, ida e volta da calibracao — rodam
em qualquer Python, porque foram escritas para nao precisar de motor nenhum.
"""

from __future__ import annotations

import ast
import copy
import json
import re
from pathlib import Path

import cv2
import numpy as np
import pytest

import l2scanner.ocr as ocr
from l2scanner import renda_leitura, renda_modo
from l2scanner.calibracao import Calibracao, CalibracaoInvalida
from l2scanner.frames import Regiao

# As fixturas foram produzidas UMA vez por `tools/resgatar_fixturas_da_renda.py`,
# que mora fora de `tests/` de proposito: ele PRECISA nomear a pasta de
# gravacoes para funcionar, e este arquivo tem um portao que proibe essa string
# aqui dentro. As duas coisas nao cabem no mesmo arquivo, e quem cede e o
# resgate — ele roda na mao, e o que fica versionado sao os PNGs.
FIXTURAS = Path(__file__).parent / "fixtures" / "renda"
CALIBRACAO_DE_FIXTURE = FIXTURAS / "calibracao_de_fixture.json"
MONTAGEM = FIXTURAS / "montagem_da_janela.png"

FONTE_DO_MODULO_PURO = (
    Path(__file__).parent.parent / "l2scanner" / "renda_leitura.py"
)

# Calculado UMA vez, no nivel do modulo, porque a decisao de pular a classe
# inteira e tomada na COLETA — antes de qualquer fixture rodar.
TEM_OCR = ocr.disponivel()
MOTIVO_SEM_OCR = ocr.motivo_indisponivel()
ocr._resetar_cache()

RAZAO_DO_SKIP = (
    "Este Python nao tem as bindings de OCR do Windows"
    f" ({MOTIVO_SEM_OCR.splitlines()[0] if MOTIVO_SEM_OCR else 'motivo desconhecido'})."
    " O ambiente de producao tem, e o global tem pytest: rode com os dois,"
    ' PYTHONPATH=".;<repo>/.venv/Lib/site-packages" python -m pytest'
    " tests/test_renda_tracer.py"
)

precisa_de_ocr = pytest.mark.skipif(not TEM_OCR, reason=RAZAO_DO_SKIP)


def carregar_dados_da_fixtura() -> dict:
    return json.loads(CALIBRACAO_DE_FIXTURE.read_text(encoding="utf-8"))


def gravar(tmp_path: Path, dados: dict) -> Path:
    alvo = tmp_path / "calibration.json"
    alvo.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
    return alvo


def moldes_de_exemplo(rotulos: str) -> dict:
    """Um conjunto de moldes no formato exato do empacotador do mercado.

    A altura 10 e uma MEDIDA da fonte desta barra e nao um numero de
    conveniencia. A largura 5 aqui e so um valor de exemplo: medido na segunda
    rodada de campo, o digito desta fonte NAO tem uma largura so — o `4`, o `7`
    e o `9` saem mais largos que os outros, e uma peneira que exigisse UMA
    largura recusaria `15,134,779` inteiro. Quem cortar os moldes de verdade
    grava a largura de cada um.

    (O numero que este conjunto NAO carrega e o `17` da primeira medicao: ela
    foi feita sobre um recorte contaminado pelos icones das pontas, e uma guarda
    de altura escrita contra ele recusaria todo molde legitimo desta barra.)
    """
    return {
        "moldes": [
            {
                "glifo": rotulo,
                "altura": 10,
                "largura": 5,
                "molde": {"altura": 10, "largura": 5, "bytes": "ff" * 50},
            }
            for rotulo in rotulos
        ],
        "piso_de_leitura": 0.47,
        "margem_de_leitura": 0.037,
        "folga_de_cola": None,
    }


# O conjunto INCOMPLETO nao e um caso inventado: e o estado real de quem parou
# no meio de uma rodada do cortador. (A razao que este estado carregava —
# "esperar o farm produzir um 5 e um 7" — caiu por medicao: os dois estao na
# tela agora, no bonus de uma instancia e no EXP da outra. O estado continua
# legitimo; ele so deixou de ser o esperado.)
ROTULOS_COMPLETOS = "0123456789,"
ROTULOS_INCOMPLETOS = "01234689,"


class TestAIdaEVoltaDaCalibracaoDaRenda:
    """As duas chaves novas atravessam o `salvar` e o `carregar` sem perder nada."""

    def test_A_FIXTURA_CARREGA_COM_OS_DOIS_PERSONAGENS(self):
        cal = Calibracao.carregar(CALIBRACAO_DE_FIXTURE)
        assert set(cal.renda_por_personagem) == {"Faerlina", "Yazalaque"}

    def test_CADA_PERSONAGEM_VOLTA_COM_O_SEU_RETANGULO_DE_NIVEL(self):
        """O achado que obrigou a calibracao a ser por personagem, dentro da fixtura.

        Um leitor que ignorasse o personagem passaria em qualquer fixtura de um
        personagem so, e cai nesta.
        """
        cal = Calibracao.carregar(CALIBRACAO_DE_FIXTURE)
        faerlina = Regiao.de_dict(
            cal.renda_do_personagem("Faerlina")["nivel"]["regiao"]
        )
        yazalaque = Regiao.de_dict(
            cal.renda_do_personagem("Yazalaque")["nivel"]["regiao"]
        )
        assert (faerlina.esquerda, faerlina.topo) == (246, 736), (
            "o nivel da Faerlina foi medido em 246,736; se ele mudou, a fixtura "
            "deixou de carregar o achado que a justifica"
        )
        assert (yazalaque.esquerda, yazalaque.topo) == (236, 750), (
            "o nivel da Yazalaque foi medido em 236,750 — 14 px abaixo e 10 a "
            "esquerda do da Faerlina. Sao valores DIFERENTES de proposito"
        )
        assert faerlina != yazalaque

    def test_A_REGIAO_DA_BARRA_ESQUERDA_DE_CADA_UM_VOLTA_COMO_Regiao(self):
        cal = Calibracao.carregar(CALIBRACAO_DE_FIXTURE)
        for nome in ("Faerlina", "Yazalaque"):
            bloco = cal.renda_do_personagem(nome)["barra_esquerda"]
            regiao = Regiao.de_dict(bloco["regiao"])
            assert (regiao.largura, regiao.altura) == (520, 24), (
                "a altura e 24 e nao 26: 1368 + 26 = 1394 e a janela tem 1392, "
                "e numpy encurtaria o recorte EM SILENCIO"
            )

    def test_SEM_A_CHAVE_renda_por_personagem_O_CAMPO_SAI_None(self, tmp_path):
        dados = carregar_dados_da_fixtura()
        dados.pop("renda_por_personagem")
        cal = Calibracao.carregar(gravar(tmp_path, dados))
        assert cal.renda_por_personagem is None
        assert cal.versao == 2, (
            "a chave e OPCIONAL de proposito, entao a versao do esquema NAO "
            "sobe: subir invalidaria o calibration.json que o usuario mediu a "
            "mao e o obrigaria a recalibrar tudo"
        )

    def test_SEM_A_CHAVE_renda_moldes_da_barra_O_CAMPO_SAI_None(self, tmp_path):
        """A ausencia e MONTADA aqui, e ate a onda 3 ela era herdada.

        A fixtura nascia sem os moldes porque eles so existem depois da rodada
        do cortador (`01-05`), e este teste tomava aquela ausencia emprestada. O
        `01-04` FUNDIU a chave naquele arquivo — ele e o consumidor dos moldes,
        e sem o merge a adena recusaria em toda rodada com a mensagem certa para
        o motivo errado. O estado ausente continua sendo um dos TRES legitimos;
        o que mudou e que ele agora e construido em vez de emprestado.
        """
        dados = carregar_dados_da_fixtura()
        dados.pop("renda_moldes_da_barra", None)
        cal = Calibracao.carregar(gravar(tmp_path, dados))
        assert cal.renda_moldes_da_barra is None
        assert cal.versao == 2

    def test_COM_A_CHAVE_OS_MOLDES_VOLTAM_CRUS_E_AS_SOLEIRAS_COMO_FLOAT(
        self, tmp_path
    ):
        dados = carregar_dados_da_fixtura()
        dados["renda_moldes_da_barra"] = moldes_de_exemplo(ROTULOS_COMPLETOS)
        cal = Calibracao.carregar(gravar(tmp_path, dados))
        conjunto = cal.renda_moldes_da_barra
        assert isinstance(conjunto, dict)
        assert [m["glifo"] for m in conjunto["moldes"]] == list(ROTULOS_COMPLETOS)
        assert isinstance(float(conjunto["piso_de_leitura"]), float)
        assert isinstance(float(conjunto["margem_de_leitura"]), float)
        assert conjunto["folga_de_cola"] is None, (
            "a folga nasce fechada: as larguras da barra sao 5 e 2 limpas, com "
            "coluna vazia entre elas. Uma folga inteira aqui autorizaria fatiar "
            "um icone de 15 px em tres digitos de 5"
        )

    def test_A_ENTRADA_DE_UM_PERSONAGEM_AUSENTE_NAO_E_A_DE_OUTRO(self):
        """O controle que separa "recusou" de "devolveu o vizinho"."""
        cal = Calibracao.carregar(CALIBRACAO_DE_FIXTURE)
        ausente = cal.renda_do_personagem("Korzis")
        assert ausente is None
        for nome in ("Faerlina", "Yazalaque"):
            assert ausente != cal.renda_do_personagem(nome), (
                "a leitura NUNCA cai na calibracao de outro personagem: o "
                "retangulo do vizinho devolve numero plausivel e errado"
            )

    def test_SEM_NOME_NAO_HA_ENTRADA(self):
        cal = Calibracao.carregar(CALIBRACAO_DE_FIXTURE)
        assert cal.renda_do_personagem(None) is None
        assert cal.renda_do_personagem("") is None


class TestOsNumerosQueAFixturaDeCalibracaoCarregaDentro:
    """A fixtura nao e um arquivo qualquer: ela carrega achados medidos."""

    def test_O_PISO_DA_barra_direita_ESTA_NA_BANDA_DE_GLIFO_E_NAO_NA_DE_OCR(self):
        """Aquele campo trocou de leitor, entao trocou de piso.

        A banda do caminho de OCR tinha largura 1 e ficava em 150; a do caminho
        de glifo e larga e vai de 180 a 190. Dois pisos onde so um tem
        consumidor seriam duas verdades esperando ser trocadas.
        """
        cal = Calibracao.carregar(CALIBRACAO_DE_FIXTURE)
        for nome in ("Faerlina", "Yazalaque"):
            piso = cal.renda_do_personagem(nome)["barra_direita"]["piso_de_brilho"]
            assert 180 <= piso <= 190, (
                f"{nome}: o piso da barra_direita e {piso}, fora da banda de "
                f"GLIFO 180-190 medida. Um piso de 150 aqui e o do caminho de "
                f"OCR, que foi ABANDONADO naquele campo por aceitar numero "
                f"errado (106020 no lugar de 1.696.020, 91 no lugar de "
                f"13.160.684)"
            )

    def test_O_RETANGULO_DA_barra_direita_E_O_QUE_SOBREVIVEU_A_QUATRO_FIXTURAS(
        self,
    ):
        """Ele ja caiu DUAS vezes, e as duas quedas ficam escritas.

        `1200,1368 520x24` era o da era do OCR: cinco campos e meia duzia de
        icones dentro do mesmo recorte. `1500,1360 200x32` o substituiu e caiu
        na segunda rodada de campo — ele foi medido em UMA fixtura, cuja L-Coin
        era curta o bastante para terminar antes da borda esquerda, e isso nao
        era margem, era sorte.
        """
        cal = Calibracao.carregar(CALIBRACAO_DE_FIXTURE)
        for nome in ("Faerlina", "Yazalaque"):
            regiao = Regiao.de_dict(
                cal.renda_do_personagem(nome)["barra_direita"]["regiao"]
            )
            atual = (regiao.esquerda, regiao.topo, regiao.largura, regiao.altura)
            assert atual == (1540, 1358, 160, 34), (
                f"{nome}: a barra_direita e {atual}. O que sobrevive as QUATRO "
                f"fixturas de campo e 1540,1358 160x34"
            )
            assert regiao.largura != 520, "o recorte da era do OCR"
            assert atual[:4] != (1500, 1360, 200, 32), (
                "este e o retangulo de UMA fixtura: com a L-Coin mais longa "
                "ele pega a cauda dela e o icone da moeda, produz run largo NO "
                "MEIO, e a peneira de forma recusaria sempre"
            )

    def test_CADA_REGIAO_TEM_O_SEU_PISO_E_NAO_EXISTE_UM_PISO_UNICO(self):
        """As bandas uteis medidas nao tem intersecao: um piso unico e impossivel."""
        cal = Calibracao.carregar(CALIBRACAO_DE_FIXTURE)
        for nome in ("Faerlina", "Yazalaque"):
            entrada = cal.renda_do_personagem(nome)
            pisos = {
                regiao: entrada[regiao]["piso_de_brilho"]
                for regiao in ("barra_esquerda", "barra_direita", "nivel")
            }
            assert len(set(pisos.values())) == 3, (
                f"{nome}: os tres pisos sao {pisos}. A banda util do nivel "
                f"(190-220) e a da adena nao tem intersecao NENHUMA: um piso "
                f"unico nao e ruim, e impossivel"
            )


@precisa_de_ocr
class TestAFormaDoRecorteDaAdenaNasQuatroFixturas:
    """O retangulo da adena, conferido contra pixel em QUATRO cenarios.

    ESTE TESTE EXISTE PORQUE O RETANGULO JA CAIU DUAS VEZES, e as duas quedas
    tiveram a mesma causa: ele foi escolhido contra UM frame. O `520x24` da era
    do OCR carregava cinco campos; o `1500,1360 200x32` que o substituiu foi
    medido numa instancia cuja L-Coin era curta o bastante para terminar antes
    da borda esquerda — e isso nao era margem, era sorte, o mesmo tipo de sorte
    que a banda de brilho de largura 1 ja tinha flagrado.

    A REGRA DE FORMA E A QUE A LEITURA POR GLIFO VAI USAR: **um run largo em
    cada ponta, e nada largo no meio**. Os runs largos das pontas sao os icones
    de moeda, e eles entram no recorte DE PROPOSITO — apertar o recorte para
    exclui-los foi o que produziu as concordancias erradas na L-Coin.

    A peneira em si e de outro plano; o que se afirma aqui e o FATO DE PIXEL de
    que ela vai depender, para que nenhuma onda seguinte herde um retangulo que
    ninguem reconferiu.
    """

    # A convencao de largura e `fim - inicio`, a mesma de `larguras_de_molde`, e
    # portanto a que a peneira vai usar. O documento de medicoes de campo relata
    # os mesmos runs numa convencao INCLUSIVA (um a mais em cada largura): as
    # duas descrevem a mesma tela, e foi um numero sem convencao declarada — o
    # "17" — que ja custou uma refutacao a esta fase.
    LARGURA_MAXIMA_DE_CARACTERE = 7

    ADENAS = [
        ("campo_faerlina_f000__barra_direita.png", 10),
        ("campo_yazalaque_f001__barra_direita.png", 9),
        ("segundo_cenario_faerlina__barra_direita.png", 10),
        ("segundo_cenario_yazalaque__barra_direita.png", 9),
    ]

    @pytest.mark.parametrize("arquivo, caracteres", ADENAS)
    @pytest.mark.parametrize("piso", [180, 185, 190])
    def test_UM_RUN_LARGO_EM_CADA_PONTA_E_NADA_LARGO_NO_MEIO(
        self, arquivo, caracteres, piso
    ):
        from l2scanner.mercado_leitura import segmentar_glifos_no_brilho

        recorte = cv2.imread(str(FIXTURAS / arquivo))
        _, runs = segmentar_glifos_no_brilho(recorte, piso)
        larguras = [fim - inicio for inicio, fim in runs]
        assert len(larguras) >= 3, larguras
        meio = larguras[1:-1]
        assert larguras[0] > self.LARGURA_MAXIMA_DE_CARACTERE, larguras
        assert larguras[-1] > self.LARGURA_MAXIMA_DE_CARACTERE, larguras
        assert all(l <= self.LARGURA_MAXIMA_DE_CARACTERE for l in meio), (
            f"{arquivo} piso={piso}: ha run largo NO MEIO ({larguras}). E o "
            f"icone da moeda dentro do numero, e e exatamente o defeito que "
            f"derrubou o retangulo 1500,1360 200x32"
        )
        assert len(meio) == caracteres, (
            f"{arquivo} piso={piso}: o meio tem {len(meio)} caracteres "
            f"({larguras}), e a verdade de campo tem {caracteres}"
        )

    def test_O_DIGITO_DESTA_FONTE_NAO_TEM_UMA_LARGURA_SO(self):
        """A refutacao que a segunda rodada de campo obrigou.

        A primeira medicao concluiu "largura 5" a partir de duas fixturas em que
        os digitos largos nao apareciam. Uma peneira escrita contra UMA largura
        recusaria `15,134,779` inteiro — e o modo de falha seria um leitor que
        nunca le, com a mensagem certa para o motivo errado.
        """
        from l2scanner.mercado_leitura import segmentar_glifos_no_brilho

        vistas = set()
        for arquivo, _ in self.ADENAS:
            recorte = cv2.imread(str(FIXTURAS / arquivo))
            _, runs = segmentar_glifos_no_brilho(recorte, 185)
            vistas.update(fim - inicio for inicio, fim in runs[1:-1])
        assert len(vistas) > 2, (
            f"as larguras do meio nas quatro fixturas sao {sorted(vistas)}. Se "
            f"elas colapsaram num valor so, a refutacao perdeu a evidencia e "
            f"precisa ser reescrita, e nao apagada"
        )


class TestAsTresPosicoesDoConjuntoDeMoldes:
    """Ausente, completo e INCOMPLETO carregam; malformado e recusado alto."""

    def test_AUSENTE_CARREGA(self, tmp_path):
        """O `pop` e do `01-04`: a fixtura passou a CARREGAR os moldes na onda 3."""
        dados = carregar_dados_da_fixtura()
        dados.pop("renda_moldes_da_barra", None)
        cal = Calibracao.carregar(gravar(tmp_path, dados))
        assert cal.renda_moldes_da_barra is None
        assert cal.versao == 2

    def test_COMPLETO_CARREGA(self, tmp_path):
        dados = carregar_dados_da_fixtura()
        dados["renda_moldes_da_barra"] = moldes_de_exemplo(ROTULOS_COMPLETOS)
        cal = Calibracao.carregar(gravar(tmp_path, dados))
        assert len(cal.renda_moldes_da_barra["moldes"]) == len(ROTULOS_COMPLETOS)
        assert cal.versao == 2

    def test_INCOMPLETO_TAMBEM_CARREGA(self, tmp_path):
        """O estado normal do usuario entre duas rodadas do cortador.

        Derrubar o arranque por causa dele trocaria uma recusa nomeada por uma
        ferramenta que nao abre: um conjunto incompleto nao impede o scanner de
        subir e de ler o EXP e o nivel, ele impede UM campo de ser lido.
        """
        dados = carregar_dados_da_fixtura()
        dados["renda_moldes_da_barra"] = moldes_de_exemplo(ROTULOS_INCOMPLETOS)
        cal = Calibracao.carregar(gravar(tmp_path, dados))
        rotulos = [m["glifo"] for m in cal.renda_moldes_da_barra["moldes"]]
        assert "5" not in rotulos and "7" not in rotulos
        assert cal.versao == 2

    def test_MALFORMADO_COM_ROTULO_DE_DOIS_CARACTERES_E_RECUSADO(self, tmp_path):
        dados = carregar_dados_da_fixtura()
        conjunto = moldes_de_exemplo(ROTULOS_COMPLETOS)
        conjunto["moldes"][0]["glifo"] = "07"
        dados["renda_moldes_da_barra"] = conjunto
        with pytest.raises(CalibracaoInvalida) as erro:
            Calibracao.carregar(gravar(tmp_path, dados))
        assert "Recalibre" in str(erro.value)

    def test_MALFORMADO_COM_SOLEIRA_FORA_DE_ZERO_UM_E_RECUSADO(self, tmp_path):
        dados = carregar_dados_da_fixtura()
        conjunto = moldes_de_exemplo(ROTULOS_COMPLETOS)
        conjunto["piso_de_leitura"] = 1.7
        dados["renda_moldes_da_barra"] = conjunto
        with pytest.raises(CalibracaoInvalida) as erro:
            Calibracao.carregar(gravar(tmp_path, dados))
        assert "piso_de_leitura" in str(erro.value)

    def test_MALFORMADO_COM_ALTURA_DISCREPANTE_E_RECUSADO(self, tmp_path):
        """Todo glifo sai da MESMA faixa de linhas compartilhada."""
        dados = carregar_dados_da_fixtura()
        conjunto = moldes_de_exemplo(ROTULOS_COMPLETOS)
        conjunto["moldes"][3]["altura"] = 17
        dados["renda_moldes_da_barra"] = conjunto
        with pytest.raises(CalibracaoInvalida):
            Calibracao.carregar(gravar(tmp_path, dados))


class TestAGuardaDoRecorte:
    """Um retangulo que nao cabe RECUSA. Um que cabe devolve a forma exata."""

    def test_UM_RETANGULO_MAIOR_QUE_O_FRAME_E_RECUSA_NOMEADA(self):
        frame = np.zeros((1392, 1720, 3), dtype=np.uint8)
        fora = Regiao(esquerda=0, topo=1368, largura=520, altura=26)
        recorte = renda_leitura.recortar(frame, fora, campo="exp")
        assert isinstance(recorte, renda_leitura.RecusaDaRenda)
        assert recorte.motivo == renda_leitura.MOTIVO_DO_RECORTE_FORA_DO_FRAME

    def test_CONTROLE_NEGATIVO_UM_RETANGULO_QUE_CABE_DEVOLVE_A_FORMA_PEDIDA(self):
        """Sem este controle, uma funcao que recusasse TUDO passaria no teste acima."""
        frame = np.zeros((1392, 1720, 3), dtype=np.uint8)
        dentro = Regiao(esquerda=0, topo=1368, largura=520, altura=24)
        recorte = renda_leitura.recortar(frame, dentro, campo="exp")
        assert not isinstance(recorte, renda_leitura.RecusaDaRenda)
        assert recorte.shape[:2] == (24, 520)

    def test_O_QUE_NUMPY_FARIA_SOZINHO_E_ENCURTAR_EM_SILENCIO(self):
        """A medicao que justifica a guarda, presa aqui para nao virar folclore."""
        frame = np.zeros((1392, 1720, 3), dtype=np.uint8)
        fatia_crua = frame[1368 : 1368 + 26]
        assert fatia_crua.shape[0] == 24, (
            "numpy devolveu uma fatia do tamanho pedido: se isso mudou, a "
            "guarda de recortar continua correta mas perdeu a medicao que a "
            "justifica, e ela precisa ser reescrita"
        )

    def test_UM_FRAME_VAZIO_E_RECUSA_E_NAO_EXCECAO(self):
        recorte = renda_leitura.recortar(
            np.zeros((0, 0, 3), dtype=np.uint8),
            Regiao(0, 0, 10, 10),
            campo="exp",
        )
        assert isinstance(recorte, renda_leitura.RecusaDaRenda)


class TestAGramaticaDoExp:
    """Quatro casas ou recusa. A ancora e a CONTAGEM, nunca o caractere."""

    @pytest.mark.parametrize(
        "texto, esperado",
        [
            ("EXP 8.0012% 592% 76", 80012),
            ("EXP 8,0012%", 80012),
            ("EXP 57.9749% t 615% 118", 579749),
            ("EXP 76.6646% t 612% 116", 766646),
            ("EXP 58.8189% 845% 120", 588189),
        ],
    )
    def test_QUATRO_CASAS_E_O_SINAL_DEVOLVEM_O_INTEIRO(self, texto, esperado):
        assert renda_leitura.decimos_de_milesimo(texto) == esperado

    def test_O_SEPARADOR_PODE_SER_PONTO_OU_VIRGULA_E_O_INTEIRO_E_O_MESMO(self):
        """O jogo escreve decimal com ponto num campo e milhar com ponto no
        outro, e o motor devolveu virgula para os dois. Quem decide o
        significado e a contagem de digitos, nunca o caractere."""
        assert renda_leitura.decimos_de_milesimo(
            "8.0012%"
        ) == renda_leitura.decimos_de_milesimo("8,0012%")

    @pytest.mark.parametrize(
        "texto",
        ["EXP 8.001%", "EXP 8.00123%", "EXP 8.0012", "EXP 80012%", "", None],
    )
    def test_TRES_CASAS_CINCO_CASAS_E_SEM_O_SINAL_SAO_RECUSA(self, texto):
        assert renda_leitura.decimos_de_milesimo(texto) is None

    def test_DUAS_CASAS_NAO_SAO_COMPLETADAS_COM_ZERO(self):
        """O controle sem o qual uma implementacao que arredondasse passaria."""
        resultado = renda_leitura.decimos_de_milesimo("EXP 8.00%")
        assert resultado is None
        assert resultado != 80000, (
            "completar as casas que faltam com zero transforma 8,00% em "
            "8,0000%: um valor perfeitamente formatado e a quase mil vezes de "
            "distancia do certo"
        )


class TestOCruzamentoDasEscalas:
    """Os quatro desfechos, testaveis sem motor de OCR nenhum."""

    def test_DUAS_VALIDAS_E_IGUAIS_ACEITAM_COM_DUAS_ESCALAS(self):
        valor = renda_leitura._cruzar_as_escalas(
            "exp", [("EXP 8.0012%", 80012), ("EXP 8.0012%", 80012)]
        )
        assert isinstance(valor, renda_leitura.ValorDaRenda)
        assert (valor.valor, valor.escalas) == (80012, 2)

    def test_UMA_VALIDA_COM_A_OUTRA_ABSTENDO_ACEITA_COM_UMA_ESCALA(self):
        """A refutacao medida em campo, com os dois textos REAIS.

        A regra antiga — "as duas tem que dar o mesmo numero, senao recusa" —
        recusaria esta amostra, e ela e a leitura crua de um frame de verdade.
        O ponto decimal sumiu na escala baixa; a alta leu certo.
        """
        valor = renda_leitura._cruzar_as_escalas(
            "exp",
            [
                ("76 EXP 80012% 592%", renda_leitura.decimos_de_milesimo(
                    "76 EXP 80012% 592%"
                )),
                ("EXP 8.0012% 592% 76", renda_leitura.decimos_de_milesimo(
                    "EXP 8.0012% 592% 76"
                )),
            ],
        )
        assert isinstance(valor, renda_leitura.ValorDaRenda), (
            "a regra da abstencao esta refutada por medicao: com igualdade "
            "obrigatoria, um dos campos seria recusado PARA SEMPRE"
        )
        assert (valor.valor, valor.escalas) == (80012, 1)

    def test_CONTROLE_DUAS_VALIDAS_E_DIFERENTES_RECUSAM_POR_DISCORDANCIA(self):
        """O par sem o qual a regra da abstencao passaria junto com uma
        implementacao que aceita qualquer coisa."""
        recusa = renda_leitura._cruzar_as_escalas(
            "exp", [("EXP 57.6499%", 576499), ("EXP 57.8499%", 578499)]
        )
        assert isinstance(recusa, renda_leitura.RecusaDaRenda)
        assert recusa.motivo == renda_leitura.MOTIVO_DA_DISCORDANCIA
        assert "576499" in recusa.detalhe and "578499" in recusa.detalhe

    def test_ZERO_VALIDAS_COM_TEXTO_VAZIO_E_RECUSA_DE_CAMPO_VAZIO(self):
        recusa = renda_leitura._cruzar_as_escalas("exp", [("", None), ("", None)])
        assert recusa.motivo == renda_leitura.MOTIVO_DO_CAMPO_VAZIO

    def test_ZERO_VALIDAS_COM_TEXTO_PRESENTE_E_RECUSA_DE_GRAMATICA(self):
        recusa = renda_leitura._cruzar_as_escalas(
            "exp", [("845%' 126", None), ("120", None)]
        )
        assert recusa.motivo == renda_leitura.MOTIVO_DA_GRAMATICA

    def test_CAMPO_VAZIO_E_GRAMATICA_SAO_MOTIVOS_DISTINTOS(self):
        """Eles parecem a mesma coisa e nao sao: sao dois consertos diferentes.

        Campo vazio aponta para calibracao ou para o jogo estar noutra tela;
        gramatica aponta para piso de brilho errado.
        """
        assert (
            renda_leitura.MOTIVO_DO_CAMPO_VAZIO
            != renda_leitura.MOTIVO_DA_GRAMATICA
        )

    def test_A_RECUSA_LEVA_AS_LEITURAS_CRUAS_ENTRE_DELIMITADORES(self):
        recusa = renda_leitura._cruzar_as_escalas(
            "exp", [("EXP 1.0000%", 10000), ("EXP 2.0000%", 20000)]
        )
        assert ">>>EXP 1.0000%<<<" in recusa.detalhe, (
            "espaco em branco e o que distingue duas leituras parecidas, e sem "
            "delimitador as duas saem iguais no log"
        )


@precisa_de_ocr
class TestALeituraDeVerdadeContraPixelReal:
    """O caminho inteiro, sobre PNGs resgatados de gravacoes de verdade."""

    def test_O_EXP_DA_FIXTURA_aba_para_calibrar_SAI_COMO_579749(self):
        """`20260901-164159-aba-para-calibrar/frame_000000`, o EXP legivel no cru."""
        recorte = cv2.imread(
            str(FIXTURAS / "aba_para_calibrar_f000__barra_esquerda.png")
        )
        leitura = renda_leitura.exp_da_barra(recorte, piso_de_brilho=160)
        assert isinstance(leitura, renda_leitura.ValorDaRenda), leitura
        assert leitura.valor == 579749

    def test_O_EXP_DO_FRAME_DE_CAMPO_DA_FAERLINA_SAI_COMO_80012(self):
        """A verdade de campo, lida a olho: 8,0012%.

        Este e o teste que separa "o codigo faz alguma coisa" de "o codigo faz
        a coisa certa".
        """
        recorte = cv2.imread(str(FIXTURAS / "campo_faerlina_f000__barra_esquerda.png"))
        leitura = renda_leitura.exp_da_barra(recorte, piso_de_brilho=160)
        assert isinstance(leitura, renda_leitura.ValorDaRenda), leitura
        assert leitura.valor == 80012

    def test_O_EXP_DO_FRAME_DE_CAMPO_DA_YAZALAQUE_SAI_COMO_766646(self):
        """A verdade de campo da outra instancia: 76,6646%."""
        recorte = cv2.imread(
            str(FIXTURAS / "campo_yazalaque_f001__barra_esquerda.png")
        )
        leitura = renda_leitura.exp_da_barra(recorte, piso_de_brilho=150)
        assert isinstance(leitura, renda_leitura.ValorDaRenda), leitura
        assert leitura.valor == 766646

    def test_O_VALOR_ACEITO_CARREGA_QUANTAS_ESCALAS_O_SUSTENTARAM(self):
        """1 no caso da abstencao, 2 no caso do acordo — no MESMO recorte.

        Os dois desfechos saem do mesmo pixel com pisos diferentes, o que e a
        prova de que `escalas` reflete a leitura e nao uma constante.
        """
        recorte = cv2.imread(str(FIXTURAS / "campo_faerlina_f000__barra_esquerda.png"))
        uma = renda_leitura.exp_da_barra(recorte, piso_de_brilho=150)
        duas = renda_leitura.exp_da_barra(recorte, piso_de_brilho=160)
        assert (uma.valor, uma.escalas) == (80012, 1), uma
        assert (duas.valor, duas.escalas) == (80012, 2), duas

    def test_A_MASCARA_RECUPERA_O_EXP_QUE_O_RECORTE_CRU_PERDE(self):
        """`20260901-172911-adena-diagnostico/frame_000005`: no cru o EXP SOME."""
        recorte = cv2.imread(
            str(FIXTURAS / "adena_diagnostico_f005__barra_esquerda.png")
        )
        cru = renda_leitura._cruzar_as_escalas(
            "exp",
            [
                (texto, renda_leitura.decimos_de_milesimo(texto))
                for texto in (ocr.ler_texto(recorte), ocr.ler_texto_ampliado(recorte))
            ],
        )
        assert isinstance(cru, renda_leitura.RecusaDaRenda), (
            "no recorte CRU deste frame o EXP nao esta la — a mascara nao e uma "
            "melhora, e um requisito"
        )
        com_mascara = renda_leitura.exp_da_barra(recorte, piso_de_brilho=170)
        assert isinstance(com_mascara, renda_leitura.ValorDaRenda), com_mascara
        assert com_mascara.valor == 588189

    def test_DOIS_CAMINHOS_DE_LEITURA_DO_MESMO_PIXEL_DISCORDAM_NUM_DIGITO(self):
        """`20260828-063240-mercado-farm-com-party/frame_000000`.

        E a prova, em pixel desta arvore, de que o cruzamento TEM trabalho a
        fazer: o recorte cru diz `57,6499%` e a mascara no piso alto diz
        `57,8499%`. Sem alguma forma de conferencia, um dos dois teria virado
        numero gravado — e depois de gravado um numero errado e indistinguivel
        de um certo.
        """
        recorte = cv2.imread(
            str(FIXTURAS / "mercado_farm_com_party_f000__barra_esquerda.png")
        )
        do_cru = renda_leitura.decimos_de_milesimo(ocr.ler_texto(recorte))
        da_mascara = renda_leitura.exp_da_barra(recorte, piso_de_brilho=180)
        assert do_cru == 576499, do_cru
        assert isinstance(da_mascara, renda_leitura.ValorDaRenda), da_mascara
        assert da_mascara.valor != do_cru, (
            "as duas leituras convergiram; reconfira se o caminho de leitura "
            "mudou. Este teste existe para afirmar que a divergencia e REAL "
            "nesta arvore, e nao um medo teorico"
        )
        assert da_mascara.valor == 578499

    def test_A_REGIAO_PRETA_DA_MONTAGEM_E_RECUSA_DE_CAMPO_VAZIO(self):
        """O caso oposto ao das fixturas de campo, e ele tambem precisa existir."""
        montagem = cv2.imread(str(MONTAGEM))
        cal = Calibracao.carregar(CALIBRACAO_DE_FIXTURE)
        bloco = cal.renda_do_personagem("Faerlina")["nivel"]
        recorte = renda_leitura.recortar(
            montagem, Regiao.de_dict(bloco["regiao"]), campo="nivel"
        )
        leitura = renda_leitura.exp_da_barra(
            recorte, piso_de_brilho=bloco["piso_de_brilho"]
        )
        assert isinstance(leitura, renda_leitura.RecusaDaRenda)
        assert leitura.motivo == renda_leitura.MOTIVO_DO_CAMPO_VAZIO


@precisa_de_ocr
class TestOComandoDeLeituraUnica:
    """De ponta a ponta: o comando roda contra a montagem e imprime o numero."""

    def test_A_MONTAGEM_IMPRIME_O_EXP_COM_QUATRO_CASAS(self, capsys):
        """A fatia fina inteira: PNG resgatado -> EXP com quatro casas na tela.

        O CODIGO DE SAIDA MUDOU NA ONDA 3, E A MUDANCA E O CUMPRIMENTO DE UMA
        PROMESSA E NAO UMA REGRESSAO. Na onda 1 este comando imprimia SO o EXP,
        por decisao escrita, e saia em 0. O `01-04` poe os TRES campos na tela —
        e a regiao do nivel desta montagem e PRETA de proposito, com a promessa
        registrada aqui desde a onda 1 de que ela viraria o caso de CAMPO VAZIO
        do plano consumidor.

        Entao o desfecho certo agora e o codigo de RECUSA: um campo nao saiu.
        O que este teste continua provando — e continua sendo o unico lugar que
        o prova de ponta a ponta na onda 1 — e que o EXP atravessa todas as
        camadas e chega a tela com as quatro casas. Quem quiser o desfecho 0 le
        `tests/test_renda_completa.py`, que roda contra `montagem_completa.png`.
        """
        codigo = renda_modo.main(
            [
                "--imagem",
                str(MONTAGEM),
                "--personagem",
                "Faerlina",
                "--calibracao",
                str(CALIBRACAO_DE_FIXTURE),
            ]
        )
        capturado = capsys.readouterr()
        saida = capturado.out + capturado.err
        assert re.search(r"\d+[.,]\d{4}%", saida), saida
        assert "8,0012%" in saida
        assert codigo == renda_modo.SAIDA_RECUSA, (
            "a regiao do nivel desta montagem e preta de PROPOSITO, e um campo "
            f"recusado nao pode sair com codigo 0:\n{saida}"
        )

    def test_SEM_personagem_O_COMANDO_RECUSA_SEM_TRACEBACK(self, capsys):
        """Quem nao sabe de quem e a tela nao le a tela."""
        codigo = renda_modo.main(
            [
                "--imagem",
                str(MONTAGEM),
                "--calibracao",
                str(CALIBRACAO_DE_FIXTURE),
            ]
        )
        erro = capsys.readouterr().err
        assert codigo != 0
        assert "Traceback" not in erro
        assert "--personagem" in erro

    def test_UM_PERSONAGEM_DESCONHECIDO_RECUSA_ANTES_DE_QUALQUER_OCR(self, capsys):
        codigo = renda_modo.main(
            [
                "--imagem",
                str(MONTAGEM),
                "--personagem",
                "Korzis",
                "--calibracao",
                str(CALIBRACAO_DE_FIXTURE),
            ]
        )
        erro = capsys.readouterr().err
        assert codigo == renda_modo.SAIDA_OPERACIONAL
        assert "Korzis" in erro
        assert "Traceback" not in erro


class TestOFonteDoModuloPuro:
    """O charter do modulo puro, preso por varredura de fonte."""

    def test_ELE_NAO_IMPORTA_argparse_NAO_ABRE_JANELA_E_NAO_LE_RELOGIO(self):
        """Um modulo de producao que importasse a ferramenta pagaria o efeito
        colateral de processo dela so por existir, e uma janela de conferencia
        acabaria abrindo dentro do tick de captura.

        A varredura ignora comentario de linha inteira e NADA mais: um teste
        que aceitasse a mencao em qualquer lugar deixaria de pegar a chamada de
        verdade no dia em que ela entrasse comentada e fosse descomentada.
        """
        proibidos = (
            "cv2." + "imshow",
            "cv2." + "selectROI",
            "cv2." + "createTrackbar",
            "datetime." + "now",
        )
        linhas = [
            linha
            for linha in FONTE_DO_MODULO_PURO.read_text(encoding="utf-8").splitlines()
            if not linha.lstrip().startswith("#")
        ]
        corpo = "\n".join(linhas)
        for proibido in proibidos:
            assert proibido not in corpo, f"{proibido} apareceu no modulo puro"
        for linha in linhas:
            assert not linha.lstrip().startswith("import argparse"), linha

    def test_ELE_E_UM_MODULO_SINTATICAMENTE_VALIDO(self):
        ast.parse(FONTE_DO_MODULO_PURO.read_text(encoding="utf-8"))

    def test_A_SETA_APONTA_FERRAMENTA_PARA_PURO_E_NUNCA_O_CONTRARIO(self):
        corpo = FONTE_DO_MODULO_PURO.read_text(encoding="utf-8")
        assert not re.search(r"^(from|import) +l2scanner\.calibrar", corpo, re.M)
        assert "from .calibrar" not in corpo


class TestQueEsteArquivoNaoDependeDaPastaDeGravacoes:
    """O portao que prova que a suite roda em clone limpo."""

    def test_NENHUM_TESTE_ABRE_A_PASTA_GITIGNORED(self):
        proibido = "record" + "ings/"
        corpo = "\n".join(
            linha
            for linha in Path(__file__).read_text(encoding="utf-8").splitlines()
            if not linha.lstrip().startswith("#")
        )
        assert proibido not in corpo, (
            "a pasta e gitignored: um teste apoiado nela fica verde nesta "
            "maquina e amarelo em qualquer clone"
        )

    def test_O_RESGATE_MORA_FORA_DE_tests_E_NENHUM_TESTE_O_IMPORTA(self):
        script = "resgatar_fixturas" + "_da_renda"
        assert (
            Path(__file__).parent.parent / "tools" / f"{script}.py"
        ).exists()
        corpo = "\n".join(
            linha
            for linha in Path(__file__).read_text(encoding="utf-8").splitlines()
            if not linha.lstrip().startswith("#")
        )
        assert script not in corpo

    def test_AS_FIXTURAS_ESTAO_VERSIONADAS_E_SAO_AO_MENOS_DEZ(self):
        pngs = sorted(FIXTURAS.glob("*.png"))
        assert len(pngs) >= 10, [p.name for p in pngs]
        assert MONTAGEM in pngs


class TestAMontagemNaoEUmaCaptura:
    """Ela e uma montagem, e o que ela prova e o que ela nao prova vai escrito."""

    def test_ELA_TEM_A_GEOMETRIA_DA_JANELA_E_A_REGIAO_DO_NIVEL_PRETA(self):
        montagem = cv2.imread(str(MONTAGEM))
        assert montagem.shape[:2] == (1392, 1720)
        cal = Calibracao.carregar(CALIBRACAO_DE_FIXTURE)
        nivel = Regiao.de_dict(
            cal.renda_do_personagem("Faerlina")["nivel"]["regiao"]
        )
        recorte = montagem[
            nivel.topo : nivel.topo + nivel.altura,
            nivel.esquerda : nivel.esquerda + nivel.largura,
        ]
        assert int(recorte.max()) == 0, (
            "a regiao do nivel e preta de PROPOSITO: o caso de campo vazio "
            "tambem precisa de uma fixtura, e as de campo entregam o oposto"
        )

    def test_O_RECORTE_DO_EXP_DA_MONTAGEM_E_BYTE_A_BYTE_O_DA_FIXTURA(self):
        """Ela e feita dos recortes REAIS colados nas posicoes de calibracao."""
        montagem = cv2.imread(str(MONTAGEM))
        original = cv2.imread(
            str(FIXTURAS / "campo_faerlina_f000__barra_esquerda.png")
        )
        colado = montagem[1368 : 1368 + 24, 0:520]
        assert np.array_equal(colado, original)


class TestQueOSalvarNaoPerdeOAninhado:
    """A ida e volta com dois personagens dentro, e uma sub-chave desconhecida."""

    def test_DOIS_PERSONAGENS_SOBREVIVEM_COM_OS_RETANGULOS_DISTINTOS(
        self, tmp_path
    ):
        cal = Calibracao.carregar(CALIBRACAO_DE_FIXTURE)
        alvo = tmp_path / "ida_e_volta.json"
        cal.salvar(alvo)
        de_volta = Calibracao.carregar(alvo)
        assert de_volta.renda_por_personagem == cal.renda_por_personagem

    def test_UMA_SUBCHAVE_DESCONHECIDA_SOBREVIVE(self, tmp_path):
        """O aninhado e REEMITIDO, e nao reconstruido campo a campo.

        E a mesma classe de defeito que o `salvar` tem uma camada acima: uma
        chave que este codigo nao conhece nao pode sumir calada, senao o campo
        novo do calibrador nasce apagado.
        """
        cal = Calibracao.carregar(CALIBRACAO_DE_FIXTURE)
        por_personagem = copy.deepcopy(cal.renda_por_personagem)
        por_personagem["Faerlina"]["campo_que_este_codigo_nao_conhece"] = {"x": 1}
        cal = Calibracao.carregar(CALIBRACAO_DE_FIXTURE)
        object.__setattr__(cal, "renda_por_personagem", por_personagem)
        alvo = tmp_path / "ida_e_volta.json"
        cal.salvar(alvo)
        de_volta = Calibracao.carregar(alvo)
        assert de_volta.renda_por_personagem["Faerlina"][
            "campo_que_este_codigo_nao_conhece"
        ] == {"x": 1}

    def test_UMA_ENTRADA_INCOMPLETA_E_RECUSADA_E_A_CHAVE_AUSENTE_PASSA(
        self, tmp_path
    ):
        dados = carregar_dados_da_fixtura()
        dados["renda_por_personagem"]["Faerlina"].pop("nivel")
        with pytest.raises(CalibracaoInvalida) as erro:
            Calibracao.carregar(gravar(tmp_path, dados))
        assert "nivel" in str(erro.value)

        sem_a_chave = carregar_dados_da_fixtura()
        sem_a_chave.pop("renda_por_personagem")
        assert (
            Calibracao.carregar(gravar(tmp_path, sem_a_chave)).renda_por_personagem
            is None
        ), "feature nao calibrada e feature desligada, e nao arquivo invalido"


class TestAAncoraDaGramatica:
    """A ancora e a CONTAGEM de casas, e ela precisa ser inatacavel pelos lados.

    A mesma barra carrega um segundo campo com sinal de porcentagem — o bonus,
    `592%` numa instancia e `612%` na outra — e o OCR desta arvore cola numero
    vizinho no comeco do texto o tempo todo (`76 EXP 80012% 592%` e uma leitura
    real). Uma gramatica ancorada so no fim casa DENTRO de um numero maior e
    devolve um numero que nunca esteve na tela.
    """

    def test_UM_DIGITO_COLADO_NA_FRENTE_NAO_VIRA_UM_NUMERO_MENOR(self):
        """`1234.5678%` nao pode virar `234,5678%`.

        O EXP e uma fracao de nivel e nunca passa de 100 pontos percentuais,
        entao um numero de quatro digitos na parte inteira NAO e um EXP — e
        recortar os tres ultimos para caber e fabricar leitura.
        """
        assert renda_leitura.decimos_de_milesimo("1234.5678%") is None, (
            "a gramatica casou DENTRO de um numero maior e devolveu 2345678, "
            "que nunca esteve na tela"
        )

    def test_DUAS_CANDIDATAS_NO_MESMO_TEXTO_SAO_RECUSA_E_NAO_A_PRIMEIRA(self):
        """Duas leituras validas no mesmo texto e ambiguidade, e nao escolha.

        Pegar a primeira e uma decisao tomada pela ordem em que o OCR devolveu
        as palavras, que nao e informacao sobre a tela.
        """
        assert renda_leitura.decimos_de_milesimo("EXP 8.0012% e 9.0012%") is None

    def test_A_MESMA_CANDIDATA_REPETIDA_NAO_E_AMBIGUIDADE(self):
        """O controle: repeticao do MESMO valor continua sendo uma leitura so."""
        assert renda_leitura.decimos_de_milesimo("8.0012% 8.0012%") == 80012

    def test_O_BONUS_DA_MESMA_BARRA_NAO_E_LIDO_COMO_EXP(self):
        """`592%` vem ANTES do EXP no texto real, e nao pode ancorar."""
        assert renda_leitura.decimos_de_milesimo("592% EXP 8.0012% 76") == 80012

    def test_ZERO_PORCENTO_COM_QUATRO_CASAS_E_UMA_LEITURA_VALIDA(self):
        """O controle que impede a correcao de virar "recuse o que for falsy"."""
        assert renda_leitura.decimos_de_milesimo("EXP 0.0000%") == 0


@precisa_de_ocr
class TestAsQuatroLeiturasReaisDoPlanejamento:
    """Cada caso cita a gravacao de origem: a proveniencia sobrevive ao proximo."""

    def test_M2_O_EXP_LEGIVEL_NO_RECORTE_CRU(self):
        """`20260901-164159-aba-para-calibrar/frame_000000`, 2x, sem mascara."""
        recorte = cv2.imread(
            str(FIXTURAS / "aba_para_calibrar_f000__barra_esquerda.png")
        )
        assert renda_leitura.decimos_de_milesimo(ocr.ler_texto(recorte)) == 579749

    def test_M4_O_EXP_QUE_O_RECORTE_CRU_PERDE(self):
        """`20260901-172911-adena-diagnostico/frame_000005`: no cru ele SOME."""
        recorte = cv2.imread(
            str(FIXTURAS / "adena_diagnostico_f005__barra_esquerda.png")
        )
        assert renda_leitura.decimos_de_milesimo(ocr.ler_texto(recorte)) is None

    def test_M5_E_A_MASCARA_O_RECUPERA(self):
        """O mesmo frame do M4, com a mascara no piso certo."""
        recorte = cv2.imread(
            str(FIXTURAS / "adena_diagnostico_f005__barra_esquerda.png")
        )
        leitura = renda_leitura.exp_da_barra(recorte, piso_de_brilho=170)
        assert isinstance(leitura, renda_leitura.ValorDaRenda), leitura
        assert leitura.valor == 588189

    def test_M6_OS_DOIS_CAMINHOS_DE_LEITURA_DIVERGEM_NUM_DIGITO(self):
        """`20260828-063240-mercado-farm-com-party/frame_000000`.

        O cru diz `57,6499%` e a mascara no piso alto diz `57,8499%`. Se um dia
        os dois convergirem, este teste tem de falhar por motivo escrito e nao
        passar em silencio: a divergencia e a evidencia de que o cruzamento tem
        trabalho a fazer nesta arvore.
        """
        recorte = cv2.imread(
            str(FIXTURAS / "mercado_farm_com_party_f000__barra_esquerda.png")
        )
        do_cru = renda_leitura.decimos_de_milesimo(ocr.ler_texto(recorte))
        da_mascara = renda_leitura.exp_da_barra(recorte, piso_de_brilho=180)
        assert do_cru == 576499
        assert da_mascara.valor == 578499
        assert do_cru != da_mascara.valor, (
            "as duas leituras convergiram; reconfira se o caminho de leitura "
            "mudou. Sem divergencia real, o cruzamento vira uma guarda que "
            "ninguem provou que faz alguma coisa"
        )
