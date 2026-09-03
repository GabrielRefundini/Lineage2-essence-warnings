"""A pausa declarada e o parado que grava: o laco com os quatro sinais na mao.

O QUE ESTE ARQUIVO EXISTE PARA IMPEDIR
======================================
**Uma amostra de tela preta entrando em `.renda/` como renda zero** (T-03-10), e
o seu inverso, que e igualmente caro: **suprimir a evidencia legitima de que o
usuario ficou uma hora parado** (T-03-11).

As duas metades sao afirmadas LADO A LADO, num teste so, porque e a comparacao
que o CEGO-01/CEGO-02 existe para garantir: com renda zero **ha linha**, com
cegueira **nao ha**. Um teste que provasse so uma das duas ficaria verde com a
outra invertida.

CEGO-01 E A AUSENCIA DE UMA CHAMADA
====================================
Nao ha coluna nova, nao ha valor de `descontinuidade` novo e nao ha segundo
portao de admissao. O laco simplesmente **nao chama `registrar`** durante a
cegueira e **nao mexe no `carimbo_anterior`** -- e ai o primeiro par depois dela
vira `lacuna` sozinho, pela regra que a Fase 2 ja tem
(`lacuna_maxima_segundos = 60`). A fronteira do `03-CONTEXT.md:17-19` -- *"Duas
portas para o mesmo arquivo e como um arquivo passa a ter duas verdades"* -- nao
e so respeitada aqui: ela e de graca.
"""

from __future__ import annotations

import argparse
import ast
import logging
import re
from pathlib import Path

import numpy as np
import pytest

from l2scanner.calibracao import Calibracao
from l2scanner.captura_janela import JanelaSource, esta_minimizada
from l2scanner.cliente import EstadoDoCliente
from l2scanner.frames import Frame, Regiao, SaudeDoFrame
from l2scanner.recaptura import (
    CONGELADOS_SEGUIDOS_PARA_RELIGAR,
    FonteRecuperavel,
)
from l2scanner.renda_conta import DESCONTINUIDADE_DA_LACUNA, ContagemDaRenda
from l2scanner.renda_laco import (
    SEGUNDOS_PARA_DECLARAR_PARADO,
    _montar_a_fonte,
    laco_da_renda,
)
from l2scanner.renda_leitura import (
    CAMPO_DA_ADENA,
    CAMPO_DO_EXP,
    CAMPO_DO_NIVEL,
    MOTIVO_DO_CAMPO_VAZIO,
    CamposDaRenda,
    RecusaDaRenda,
    ValorDaAdena,
    ValorDaRenda,
)
from l2scanner.renda_console import (
    ESTADOS_QUE_SOMAM,
    PREFIXO_DA_LINHA,
    LARGURA_MAXIMA_DA_LINHA_DO_TIQUE,
    MARCA_POR_ESTADO,
    RECORTE_DO_EXP_SEM_LEITURA,
    linha_do_tique,
)
from l2scanner.renda_estado import EstadoDaRenda, RastreioDoValor, classificar_a_visao
from l2scanner.renda_registro import arquivo_do_personagem

FIXTURES = Path(__file__).parent / "fixtures" / "renda"
CALIBRACAO = FIXTURES / "calibracao_de_fixture.json"
PASTA_DO_PACOTE = Path(__file__).parent.parent / "l2scanner"

PERSONAGEM = "Faerlina"
TITULO = f"{PERSONAGEM} - XM Essence"

LARGURA_DA_JANELA = 1720
ALTURA_DA_JANELA = 1392


# ---------------------------------------------------------------------------
# O IDIOMA DE TESTE DE LACO -- o mesmo de `tests/test_renda_laco.py`
# ---------------------------------------------------------------------------


def campos_de(
    nivel: int | None = 68,
    exp_em_decimos: int | None = 480_075,
    adena: int | None = 23_986_985,
) -> CamposDaRenda:
    """Os valores por omissao sao os MEDIDOS ao vivo em 2026-09-03."""

    def _valor(campo, valor):
        if valor is None:
            return RecusaDaRenda(
                campo=campo,
                motivo=MOTIVO_DO_CAMPO_VAZIO,
                detalhe="a mascara nao deixou nada de pe",
            )
        return ValorDaRenda(
            campo=campo, valor=valor, escalas=2, texto=str(valor)
        )

    def _adena(valor):
        if valor is None:
            return RecusaDaRenda(
                campo=CAMPO_DA_ADENA,
                motivo=MOTIVO_DO_CAMPO_VAZIO,
                detalhe="nenhum glifo sobreviveu a peneira",
            )
        return ValorDaAdena(
            campo=CAMPO_DA_ADENA, valor=valor, glifos=10, texto=str(valor)
        )

    return CamposDaRenda(
        personagem=PERSONAGEM,
        nivel=_valor(CAMPO_DO_NIVEL, nivel),
        exp=_valor(CAMPO_DO_EXP, exp_em_decimos),
        adena=_adena(adena),
    )


class FonteComSaude:
    """A porta de captura, com a saude de CADA frame escrita no teste.

    E o dublê minimo que CEGO-01 pede: o `03-01` deixou `frame.saude` chegando
    ao laco e nao consultado, e esta fase e quem o consulta. `estado_do_cliente`
    e `hwnd` sao opcionais de proposito -- ha teste para a fonte que NAO os tem.
    """

    def __init__(
        self,
        saudes,
        *,
        estados_do_cliente=None,
        hwnd: int | None = None,
    ) -> None:
        self._saudes = list(saudes)
        self._estados = list(estados_do_cliente or [])
        self._indice = 0
        self.fechada = False
        self.perguntas_de_cliente = 0
        if hwnd is not None:
            self.hwnd = hwnd

    def capturar(self) -> Frame:
        if self._indice >= len(self._saudes):
            raise StopIteration
        saude = self._saudes[self._indice]
        self._indice += 1
        return Frame(
            pixels=np.zeros((4, 4, 3), dtype=np.uint8),
            indice=self._indice,
            saude=saude,
        )

    def estado_do_cliente(self):
        self.perguntas_de_cliente += 1
        if not self._estados:
            return EstadoDoCliente.EM_JOGO
        return self._estados[min(self._indice - 1, len(self._estados) - 1)]

    def fechar(self) -> None:
        self.fechada = True


class FonteSemCliente:
    """Uma fonte que NAO tem `estado_do_cliente` nem `hwnd`.

    E o caso do `MssSource`, e o laco nao pode cair por causa dele.
    """

    def __init__(self, quantos: int) -> None:
        self._restam = quantos
        self._indice = 0
        self.fechada = False

    def capturar(self) -> Frame:
        if self._restam <= 0:
            raise StopIteration
        self._restam -= 1
        self._indice += 1
        return Frame(
            pixels=np.zeros((4, 4, 3), dtype=np.uint8),
            indice=self._indice,
            saude=SaudeDoFrame.OK,
        )

    def fechar(self) -> None:
        self.fechada = True


class LeitoraFalsa:
    def __init__(self, sequencia) -> None:
        self._sequencia = list(sequencia)
        self._indice = 0
        self.chamadas = 0

    def __call__(self, frame, *, personagem, calibracao) -> CamposDaRenda:
        self.chamadas += 1
        campos = self._sequencia[min(self._indice, len(self._sequencia) - 1)]
        self._indice += 1
        return campos


class RelogioFalso:
    def __init__(self, carimbos) -> None:
        self._carimbos = list(carimbos)
        self._indice = 0

    def agora_epoch(self) -> float:
        carimbo = self._carimbos[min(self._indice, len(self._carimbos) - 1)]
        self._indice += 1
        return float(carimbo)


def argumentos(**extras) -> argparse.Namespace:
    base = {"janela": TITULO, "intervalo": 0.0, "status_a_cada": 10_000.0}
    base.update(extras)
    return argparse.Namespace(**base)


@pytest.fixture(scope="module")
def cal() -> Calibracao:
    return Calibracao.carregar(CALIBRACAO)


def linhas_de_dado(caminho: Path) -> list[str]:
    texto = caminho.read_text(encoding="utf-8")
    return [linha for linha in texto.splitlines()[1:] if linha.strip()]


def coluna(caminho: Path, nome: str) -> list[str]:
    import csv

    from l2scanner.renda_registro import SEPARADOR

    with caminho.open("r", encoding="utf-8", newline="") as fonte:
        return [
            linha[nome] for linha in csv.DictReader(fonte, delimiter=SEPARADOR)
        ]


def rodar(cal, tmp_path, *, sequencia, carimbos, fonte, ticks, **extras):
    leitora = LeitoraFalsa(sequencia)
    codigo = laco_da_renda(
        argumentos(**extras),
        cal,
        fonte=fonte,
        ler_campos=leitora,
        relogio=RelogioFalso(carimbos),
        pasta=tmp_path,
        ticks_maximos=ticks,
    )
    return codigo, leitora


# ---------------------------------------------------------------------------
# CEGO-01 -- A CEGUEIRA SUSPENDE A GRAVACAO
# ---------------------------------------------------------------------------


class TestAPausaSuspendeAGravacao:
    def test_dez_frames_cegos_NAO_ACRESCENTAM_LINHA_NENHUMA(
        self, cal, tmp_path
    ) -> None:
        """O dano que CEGO-01 existe para impedir (T-03-10).

        Duas linhas boas, dez frames pretos, duas linhas boas: o arquivo tem de
        ficar com QUATRO linhas. Se os dez entrassem, cada um deles seria uma
        amostra de tela preta com os tres campos recusados -- e a taxa da sessao
        os teria no denominador.
        """
        saudes = (
            [SaudeDoFrame.OK] * 2
            + [SaudeDoFrame.FALHA_DE_CAPTURA] * 10
            + [SaudeDoFrame.OK] * 2
        )
        sequencia = [campos_de(exp_em_decimos=480_000 + n * 10) for n in range(14)]
        codigo, _ = rodar(
            cal,
            tmp_path,
            sequencia=sequencia,
            carimbos=[float(n) for n in range(14)],
            fonte=FonteComSaude(saudes),
            ticks=14,
        )

        assert codigo == 0
        arquivo = arquivo_do_personagem(tmp_path, PERSONAGEM)
        assert len(linhas_de_dado(arquivo)) == 4, (
            "os dez frames cegos deixaram linha em .renda/: CEGO-01 quebrou"
        )

    def test_o_primeiro_tique_depois_da_cegueira_vira_LACUNA(
        self, cal, tmp_path
    ) -> None:
        """O `carimbo_anterior` NAO e zerado, e e isso que faz tudo funcionar.

        Mantido o carimbo de antes da cegueira, o intervalo do primeiro par
        depois dela passa de `lacuna_maxima_segundos` (60) e
        `passo_entre_campos` marca `lacuna` SOZINHO -- sem uma linha nova, sem
        coluna nova e sem um segundo portao (C-6).
        """
        saudes = (
            [SaudeDoFrame.OK] * 2
            + [SaudeDoFrame.FALHA_DE_CAPTURA] * 100
            + [SaudeDoFrame.OK] * 2
        )
        sequencia = [
            campos_de(exp_em_decimos=480_000 + n * 10) for n in range(104)
        ]
        rodar(
            cal,
            tmp_path,
            sequencia=sequencia,
            carimbos=[float(n) for n in range(104)],
            fonte=FonteComSaude(saudes),
            ticks=104,
        )

        arquivo = arquivo_do_personagem(tmp_path, PERSONAGEM)
        marcas = coluna(arquivo, "descontinuidade")
        assert len(marcas) == 4
        assert marcas[2] == DESCONTINUIDADE_DA_LACUNA, (
            "o primeiro passo depois da cegueira tinha de ser `lacuna` e veio "
            f"{marcas[2]!r} -- o `carimbo_anterior` foi zerado pela pausa"
        )

    def test_o_tempo_cego_SAI_DO_DENOMINADOR_e_aparece_no_bloco(
        self, cal, tmp_path, caplog
    ) -> None:
        """`lacunas_excluidas` e `segundos_em_lacuna` maiores que zero.

        E o que faz *"a taxa caiu"* nunca ser confundido com *"o scanner nao
        viu"* (`renda_conta.py:847-885`).
        """
        saudes = (
            [SaudeDoFrame.OK] * 2
            + [SaudeDoFrame.FALHA_DE_CAPTURA] * 100
            + [SaudeDoFrame.OK] * 2
        )
        sequencia = [
            campos_de(exp_em_decimos=480_000 + n * 10) for n in range(104)
        ]
        with caplog.at_level(logging.INFO):
            rodar(
                cal,
                tmp_path,
                sequencia=sequencia,
                carimbos=[float(n) for n in range(104)],
                fonte=FonteComSaude(saudes),
                ticks=104,
                status_a_cada=0.0,
            )

        linha = [
            linha
            for linha in caplog.text.splitlines()
            if "lacunas excluidas" in linha
        ]
        assert linha, caplog.text[-3000:]
        excluidas = re.search(r"lacunas excluidas\s+(\d+) \((\S+) cegos\)", linha[-1])
        assert excluidas, linha[-1]
        assert int(excluidas.group(1)) >= 1, linha[-1]
        assert excluidas.group(2) not in ("0s",), linha[-1]

    def test_O_LACO_NAO_SAI_POR_CAUSA_DE_CEGUEIRA(self, cal, tmp_path) -> None:
        """Vinte frames cegos devolvem 0, e a fonte foi fechada no `finally`.

        Os dois precedentes da arvore concordam: a party religa e depois roda
        cega SEM sair, o mercado congela em silencio. Os dois so saem por dez
        excecoes seguidas de CAPTURA. CEGO-01 diz "pausa declarada", nunca
        "encerra".
        """
        fonte = FonteComSaude([SaudeDoFrame.FALHA_DE_CAPTURA] * 20)
        codigo, _ = rodar(
            cal,
            tmp_path,
            sequencia=[campos_de(nivel=None, exp_em_decimos=None, adena=None)],
            carimbos=[float(n) for n in range(20)],
            fonte=fonte,
            ticks=20,
        )

        assert codigo == 0, "cegueira nao pode virar codigo de saida"
        assert fonte.fechada
        arquivo = arquivo_do_personagem(tmp_path, PERSONAGEM)
        assert linhas_de_dado(arquivo) == []

    def test_a_transicao_para_PAUSADO_loga_UMA_VEZ_com_o_motivo(
        self, cal, tmp_path, caplog
    ) -> None:
        """LATCH. Um aviso por tique vira ruido que o olho aprende a pular.

        O molde e `mercado_pagina.py:796-814`, e a licao e de producao
        (2026-09-01): o usuario concluiu que o scanner tinha parado porque o
        aviso repetido deixou de ser lido.
        """
        saudes = (
            [SaudeDoFrame.OK]
            + [SaudeDoFrame.FALHA_DE_CAPTURA] * 8
            + [SaudeDoFrame.OK] * 2
        )
        with caplog.at_level(logging.INFO):
            rodar(
                cal,
                tmp_path,
                sequencia=[
                    campos_de(exp_em_decimos=480_000 + n * 10) for n in range(11)
                ],
                carimbos=[float(n) for n in range(11)],
                fonte=FonteComSaude(saudes),
                ticks=11,
            )

        texto = caplog.text
        assert texto.count("A CAPTURA VEIO PRETA") == 1, (
            f"o aviso de pausa saiu {texto.count('A CAPTURA VEIO PRETA')} "
            "vezes; o latch nao esta segurando"
        )
        assert texto.count("o EXP voltou a mudar") == 1, (
            "a VOLTA tambem loga uma vez, e uma vez so"
        )

    def test_a_fonte_SEM_estado_do_cliente_nao_derruba_o_laco(
        self, cal, tmp_path
    ) -> None:
        """`hasattr`, como `sessao.py:468` faz. A ausencia vira "nao perguntei",
        e nunca um estado inventado que pausaria a sessao inteira."""
        fonte = FonteSemCliente(4)
        codigo, leitora = rodar(
            cal,
            tmp_path,
            sequencia=[
                campos_de(exp_em_decimos=480_000 + n * 10) for n in range(4)
            ],
            carimbos=[float(n) for n in range(4)],
            fonte=fonte,
            ticks=4,
        )

        assert codigo == 0
        assert leitora.chamadas == 4
        arquivo = arquivo_do_personagem(tmp_path, PERSONAGEM)
        assert len(linhas_de_dado(arquivo)) == 4, (
            "uma fonte sem `estado_do_cliente` fez o laco pausar: a ausencia "
            "do metodo virou um estado inventado"
        )

    def test_a_tela_de_login_pausa_com_o_frame_SAUDAVEL(
        self, cal, tmp_path, caplog
    ) -> None:
        """O frame esta perfeito e o jogo caiu: so o titulo da janela sabe."""
        with caplog.at_level(logging.INFO):
            rodar(
                cal,
                tmp_path,
                sequencia=[campos_de() for _ in range(4)],
                carimbos=[float(n) for n in range(4)],
                fonte=FonteComSaude(
                    [SaudeDoFrame.OK] * 4,
                    estados_do_cliente=[EstadoDoCliente.TELA_DE_LOGIN] * 4,
                ),
                ticks=4,
            )

        assert "JOGO CAIU - TELA DE LOGIN" in caplog.text
        arquivo = arquivo_do_personagem(tmp_path, PERSONAGEM)
        assert linhas_de_dado(arquivo) == []


# ---------------------------------------------------------------------------
# A FONTE RELIGAVEL, O `hwnd` E O PRIMEIRO CHAMADOR DE `esta_minimizada`
# ---------------------------------------------------------------------------


class JanelaFalsa:
    """Uma `JanelaSource` de mentira, com o hwnd e a regiao que a fabrica mira."""

    criadas: list["JanelaFalsa"] = []

    def __init__(self, titulo, regiao, relativa=False, **resto):
        self.titulo = titulo
        self.regiao_do_nascimento = regiao
        self.relativa = relativa
        self.resto = resto
        self.regiao = regiao
        self.hwnd = 1000 + len(JanelaFalsa.criadas)
        self.fechada = False
        self.saude = SaudeDoFrame.OK
        JanelaFalsa.criadas.append(self)

    def capturar_completo(self):
        return np.zeros((ALTURA_DA_JANELA, LARGURA_DA_JANELA, 3), dtype=np.uint8)

    def capturar(self) -> Frame:
        return Frame(
            pixels=np.zeros((4, 4, 3), dtype=np.uint8),
            indice=0,
            saude=self.saude,
        )

    def apontar_para(self, regiao) -> None:
        self.regiao = regiao

    def fechar(self) -> None:
        self.fechada = True


@pytest.fixture(autouse=True)
def _limpar_janelas_falsas():
    JanelaFalsa.criadas.clear()
    yield
    JanelaFalsa.criadas.clear()


class TestAFonteReligavel:
    def test_a_fonte_do_modo_renda_NASCE_ENVELOPADA(self) -> None:
        """A behaviour escolhida e a da PARTY, e o argumento e o caso de uso.

        O incidente medido em `recaptura.py:3-17` foram **33 minutos cegos** com
        o jogo VIVO na tela. O mercado nao religa e herda esse defeito; ele roda
        com o usuario olhando, e a farmada noturna nao.
        """
        fonte, problema = _montar_a_fonte(
            TITULO, {}, construir_janela=JanelaFalsa
        )
        assert problema is None
        assert isinstance(fonte, FonteRecuperavel)
        assert len(JanelaFalsa.criadas) == 1

    def test_a_MIRA_acontece_dentro_da_fabrica(self) -> None:
        """Se a mira ficasse FORA de `construir()`, a fonte reconstruida
        voltaria olhando para o retangulo UNITARIO e o laco leria UM PIXEL pelo
        resto da noite. E o mesmo defeito que `_regiao_reancorada` existe para
        impedir do lado da party.
        """
        _montar_a_fonte(TITULO, {}, construir_janela=JanelaFalsa)
        nascida = JanelaFalsa.criadas[0]

        assert nascida.regiao_do_nascimento == Regiao(
            esquerda=0, topo=0, largura=1, altura=1
        )
        assert nascida.relativa is True
        assert nascida.regiao == Regiao(
            esquerda=0,
            topo=0,
            largura=LARGURA_DA_JANELA,
            altura=ALTURA_DA_JANELA,
        )

    def test_a_fonte_RECONSTRUIDA_tambem_nasce_mirada(self) -> None:
        """Tres `CONGELADO` seguidos disparam a religacao, e a nova mira sozinha.

        O teste prova a religacao CONTANDO as chamadas da fabrica -- sem dormir
        os 30 s de `SEGUNDOS_ENTRE_TENTATIVAS`, porque a primeira tentativa nao
        espera.
        """
        fonte, _ = _montar_a_fonte(TITULO, {}, construir_janela=JanelaFalsa)
        JanelaFalsa.criadas[0].saude = SaudeDoFrame.CONGELADO

        for _ in range(CONGELADOS_SEGUIDOS_PARA_RELIGAR):
            fonte.capturar()

        assert len(JanelaFalsa.criadas) == 2, (
            "a fonte nao foi reconstruida depois de "
            f"{CONGELADOS_SEGUIDOS_PARA_RELIGAR} congelados"
        )
        assert JanelaFalsa.criadas[1].regiao == Regiao(
            esquerda=0,
            topo=0,
            largura=LARGURA_DA_JANELA,
            altura=ALTURA_DA_JANELA,
        ), "a fonte reconstruida ficou olhando para o retangulo unitario"

    def test_o_hwnd_do_envelope_e_o_da_fonte_CORRENTE(self) -> None:
        """Depois de uma religacao, `fonte.hwnd` reflete a fonte viva -- e nao
        o cadaver de onde ele foi lido. E por isso que o laco pergunta A FONTE
        qual hwnd ela esta lendo, em vez de chamar `achar_janela` por conta
        propria: com DUAS instancias abertas, `achar_janela` pode devolver a
        outra.
        """
        fonte, _ = _montar_a_fonte(TITULO, {}, construir_janela=JanelaFalsa)
        primeiro = fonte.hwnd
        assert primeiro == JanelaFalsa.criadas[0].hwnd

        JanelaFalsa.criadas[0].saude = SaudeDoFrame.CONGELADO
        for _ in range(CONGELADOS_SEGUIDOS_PARA_RELIGAR):
            fonte.capturar()

        assert fonte.hwnd == JanelaFalsa.criadas[1].hwnd
        assert fonte.hwnd != primeiro

    def test_a_JanelaSource_de_verdade_tem_a_PROPRIEDADE_hwnd(self) -> None:
        """Duas linhas, aditivas: `@property hwnd` devolve `self._hwnd`.

        O objeto e montado sem WGC pelo idioma de
        `tests/test_gravador_honesto.py:590-609` -- o `__init__` abre a captura
        de verdade e exige o cliente rodando, e o que este teste exercita e so a
        propriedade.
        """
        fonte = JanelaSource.__new__(JanelaSource)
        fonte._hwnd = 30216936
        assert fonte.hwnd == 30216936

    def test_o_envelope_ENCAMINHA_o_hwnd_em_vez_de_declarar(self) -> None:
        """`FonteRecuperavel` nao pode DECLARAR `hwnd`, pela mesma razao de
        `estado_do_cliente`: `sessao.py` decide por `hasattr`, e uma fonte de
        desktop nao tem hwnd nenhum.
        """
        assert "hwnd" not in vars(FonteRecuperavel)

        class SemHwnd:
            def capturar(self):
                raise NotImplementedError

            def fechar(self):
                pass

        envelope = FonteRecuperavel(lambda: SemHwnd())
        assert not hasattr(envelope, "hwnd")


# ---------------------------------------------------------------------------
# `esta_minimizada` GANHA O SEU PRIMEIRO CHAMADOR (C-7)
# ---------------------------------------------------------------------------


def chamadores_de(raiz: Path, nome: str) -> list[str]:
    """Quem CHAMA aquela funcao em `l2scanner/`, por arvore e nunca por `grep`.

    A varredura conta CHAMADAS e nao ocorrencias: a razao de `esta_minimizada`
    ser consultada -- em vez de se confiar no congelamento -- esta escrita em
    prosa no laco, e um `grep` a acusaria como se fosse uma segunda chamada.
    E o mesmo portao que o `03-01` construiu para `capturar_completo` depois de
    medir que o `grep` do plano devolvia 5 para UMA chamada.
    """
    chamadas: list[str] = []
    for modulo in sorted(Path(raiz).glob("*.py")):
        arvore = ast.parse(modulo.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Call):
                continue
            alvo = getattr(no.func, "id", None) or getattr(no.func, "attr", None)
            if alvo == nome:
                chamadas.append(f"{modulo.name}:{no.lineno}")
    return chamadas


class TestOPrimeiroChamadorDeEstaMinimizada:
    """O portao INVERTIDO: de "zero chamadores" para "um, e ele e o laco".

    `esta_minimizada` esta escrita em `captura_janela.py:203-204` desde o v1 e
    **nao tinha chamador nenhum em toda a arvore** (C-7). Ela e o unico caminho
    para dizer "minimizado" no segundo em que o usuario minimiza, em vez de
    esperar os 30 frames de `FRAMES_IDENTICOS_PARA_CONGELADO` e dizer a palavra
    ERRADA.
    """

    def test_ELA_TEM_UM_CHAMADOR_DE_PRODUCAO_E_ELE_ESTA_NO_LACO_DA_RENDA(
        self,
    ) -> None:
        achados = chamadores_de(PASTA_DO_PACOTE, "esta_minimizada")
        assert achados, (
            "`esta_minimizada` continua sem chamador. Ela e o sinal IMEDIATO de "
            "minimizado; sem ela o painel espera ~30 s e diz `congelado`, que e "
            "a palavra errada para uma janela que o usuario acabou de minimizar."
        )
        modulos = {achado.split(":")[0] for achado in achados}
        assert modulos == {"renda_laco.py"}, (
            f"o chamador tem de ser um so, e no laco da renda: {sorted(achados)}"
        )

    def test_CONTROLE_POSITIVO_DOIS_CHAMADORES_SAO_ACUSADOS(
        self, tmp_path
    ) -> None:
        """Sem ele, um portao que devolvesse sempre o mesmo achado passaria."""
        (tmp_path / "um.py").write_text(
            "from .captura_janela import esta_minimizada\n"
            "\n"
            "def olhar(h):\n"
            "    return esta_minimizada(h)\n",
            encoding="utf-8",
        )
        (tmp_path / "outro.py").write_text(
            "from . import captura_janela as cj\n"
            "\n"
            "def olhar(h):\n"
            "    return cj.esta_minimizada(h)\n",
            encoding="utf-8",
        )
        achados = chamadores_de(tmp_path, "esta_minimizada")
        assert len(achados) == 2, achados

    def test_A_FUNCAO_CHAMADA_E_A_DE_PRODUCAO_E_ELA_RECEBE_O_HWND_DA_FONTE(
        self, monkeypatch
    ) -> None:
        """O portao acima conta chamadas por NOME; este mede a CHAMADA.

        Ele troca a funcao de producao por uma que anota o hwnd recebido, e
        afirma que o numero e o da FONTE. Se o laco passasse a chamar
        `achar_janela(titulo)` por conta propria, com duas instancias abertas
        ele poderia ler a OUTRA -- que e o defeito que `--janela` existe para
        impedir.
        """
        import l2scanner.captura_janela as cj
        from l2scanner import renda_laco

        vistos: list[int] = []

        def _falsa(hwnd):
            vistos.append(hwnd)
            return True

        monkeypatch.setattr(cj, "esta_minimizada", _falsa)

        class ComHwnd:
            hwnd = 30216936

        assert renda_laco._a_janela_esta_minimizada(ComHwnd()) is True
        assert vistos == [30216936]

    def test_uma_fonte_SEM_hwnd_nao_pergunta_nada(self, monkeypatch) -> None:
        """Sem hwnd nao ha `IsIconic` a fazer, e a ausencia nao vira `True`."""
        import l2scanner.captura_janela as cj
        from l2scanner import renda_laco

        def _explode(hwnd):
            raise AssertionError("nao devia ter perguntado")

        monkeypatch.setattr(cj, "esta_minimizada", _explode)

        class SemHwnd:
            pass

        assert renda_laco._a_janela_esta_minimizada(SemHwnd()) is False


class TestOLimiarDaStaleness:
    def test_ELE_E_CONSTANTE_NOMEADA_DO_LACO_E_NAO_CHAVE_DO_CONFIG(self) -> None:
        """O molde e `FRAMES_IDENTICOS_PARA_CONGELADO = 30` -- o detector IRMAO.

        Ele e uma propriedade do DETECTOR e nao um numero de farm que o usuario
        ajusta, entao nao vira a sexta chave da secao `[renda]` (C-4).
        """
        from l2scanner.config import AjustesDaRenda

        assert isinstance(SEGUNDOS_PARA_DECLARAR_PARADO, float)
        assert SEGUNDOS_PARA_DECLARAR_PARADO > 0
        assert not any(
            "parado" in campo for campo in AjustesDaRenda.__dataclass_fields__
        ), (
            "o limiar da staleness virou chave de config: seis lugares novos "
            "por um numero que ninguem pediu para ajustar"
        )

    def test_ele_diz_QUE_E_ESCOLHA_E_NAO_MEDICAO(self) -> None:
        """Um numero que nao foi medido precisa dizer que nao foi -- a mesma
        disciplina de `MS_ENTRE_FRAMES_DA_RENDA` no `03-01`."""
        fonte = (PASTA_DO_PACOTE / "renda_laco.py").read_text(encoding="utf-8")
        antes = fonte.split("SEGUNDOS_PARA_DECLARAR_PARADO =")[0]
        bloco = antes.rsplit("\n\n", 1)[-1]
        assert "ESCOLHA E NAO MEDICAO" in bloco, bloco


# ---------------------------------------------------------------------------
# CEGO-02 -- PARADO GRAVA, E SO MUDA A TELA
# ---------------------------------------------------------------------------


def linhas_do_tique(caplog) -> list[str]:
    """So as linhas do tique, entre todo o resto do log da sessao.

    O `caplog.text` prefixa cada registro com nivel, logger e origem, entao a
    linha e recortada a partir do `PREFIXO_DA_LINHA` -- que e o mesmo motivo de
    ele existir: deixar a linha da renda reconhecivel no `scanner.log`
    rotativo, onde ela divide o arquivo com as da party e as do mercado.
    """
    marca = f"{PREFIXO_DA_LINHA} | "
    achadas = []
    for linha in caplog.text.splitlines():
        posicao = linha.find(marca)
        if posicao >= 0:
            achadas.append(linha[posicao:].strip())
    return achadas


class TestOParadoGrava:
    """A metade do CEGO-02 que o `03-CONTEXT.md` decidiu e o CTX-3 cravou.

    **"Parado" GRAVA normalmente e so muda a TELA. So a cegueira suspende a
    gravacao.** As tres razoes, na ordem do peso:

    1. Renda zero e um fato legitimo sobre o farm. Se "parado" virasse recusa, o
       arquivo perderia justamente a evidencia de que o usuario ficou uma hora
       parado -- que e a pergunta que ele mais quer de manha.
    2. A taxa mentiria PARA CIMA. Sem as linhas do tempo parado o denominador
       encolhe, e a diferenca medida entre a janela curta (466 mil adena/h) e a
       media longa (226 mil/h) e EXATAMENTE tempo parado.
    3. `renda_registro.py` diz por escrito que uma linha por tique **e o
       produto**, e a Fase 2 ja grava a recusa com o motivo.
    """

    def test_TRINTA_TIQUES_BIT_IDENTICOS_DEIXAM_TRINTA_LINHAS(
        self, cal, tmp_path
    ) -> None:
        rodar(
            cal,
            tmp_path,
            sequencia=[campos_de(exp_em_decimos=480_075)],
            carimbos=[float(n) * 10 for n in range(30)],
            fonte=FonteComSaude([SaudeDoFrame.OK] * 30),
            ticks=30,
        )
        arquivo = arquivo_do_personagem(tmp_path, PERSONAGEM)
        assert len(linhas_de_dado(arquivo)) == 30, (
            "PARADO deixou de gravar: a taxa da sessao passa a mentir para "
            "cima, porque o denominador encolheu"
        )

    def test_a_linha_diz_PARADO_DEPOIS_do_limiar_e_nao_antes(
        self, cal, tmp_path, caplog
    ) -> None:
        """E ela mostra OS DOIS numeros: o tempo e a contagem de amostras."""
        carimbos = [float(n) * 10 for n in range(30)]
        with caplog.at_level(logging.INFO):
            rodar(
                cal,
                tmp_path,
                sequencia=[campos_de(exp_em_decimos=480_075)],
                carimbos=carimbos,
                fonte=FonteComSaude([SaudeDoFrame.OK] * 30),
                ticks=30,
            )

        linhas = linhas_do_tique(caplog)
        assert len(linhas) == 30

        # Com um tique a cada 10 s, o limiar de 120 s vence no 13o tique
        # (carimbo 120), e nunca antes.
        vence = int(SEGUNDOS_PARA_DECLARAR_PARADO // 10) + 1
        assert "PARADO" not in linhas[vence - 2], linhas[vence - 2]
        assert "PARADO" in linhas[vence - 1], linhas[vence - 1]
        assert "2min" in linhas[vence - 1], linhas[vence - 1]
        assert "n=13" in linhas[vence - 1], linhas[vence - 1]

    def test_RENDA_ZERO_E_CEGUEIRA_LADO_A_LADO_produzem_o_OPOSTO_no_disco(
        self, cal, tmp_path, caplog
    ) -> None:
        """A comparacao que o CEGO-01/CEGO-02 existe para garantir.

        Uma metade sozinha ficaria verde com a outra invertida: um teste que so
        provasse "cegueira nao grava" passaria com PARADO tambem nao gravando --
        que e exatamente o defeito que apaga a evidencia do tempo parado.
        """
        parado = tmp_path / "parado"
        cego = tmp_path / "cego"

        with caplog.at_level(logging.INFO):
            rodar(
                cal,
                parado,
                sequencia=[campos_de(exp_em_decimos=480_075)],
                carimbos=[float(n) * 10 for n in range(20)],
                fonte=FonteComSaude([SaudeDoFrame.OK] * 20),
                ticks=20,
            )
            linhas_do_parado = linhas_do_tique(caplog)
            caplog.clear()
            rodar(
                cal,
                cego,
                sequencia=[campos_de(exp_em_decimos=480_075)],
                carimbos=[float(n) * 10 for n in range(20)],
                fonte=FonteComSaude([SaudeDoFrame.FALHA_DE_CAPTURA] * 20),
                ticks=20,
            )
            linhas_do_cego = linhas_do_tique(caplog)

        assert (
            len(linhas_de_dado(arquivo_do_personagem(parado, PERSONAGEM))) == 20
        ), "renda zero legitima TEM de deixar linha"
        assert linhas_de_dado(arquivo_do_personagem(cego, PERSONAGEM)) == [], (
            "cegueira NAO pode deixar linha"
        )

        # A COMPARACAO E SOBRE AS LINHAS DO TIQUE, e nao sobre o log inteiro:
        # o resumo da sessao cita as duas palavras nos ROTULOS dos contadores,
        # em toda sessao, e um teste sobre `caplog.text` estaria medindo o
        # resumo em vez da tela do tique.
        assert any("PARADO ha" in x for x in linhas_do_parado), linhas_do_parado
        assert not any("PAUSADO" in x for x in linhas_do_parado)
        assert all("PAUSADO" in x for x in linhas_do_cego), linhas_do_cego
        assert not any("PARADO ha" in x for x in linhas_do_cego)

    def test_o_EXP_recusado_com_a_adena_lida_GRAVA_e_diz_SEM_LEITURA_EXP(
        self, cal, tmp_path, caplog
    ) -> None:
        """O quinto caso, na fatia inteira: a linha vai ao disco E a tela nao
        afirma nem PARADO nem LENDO sobre um numero que nao foi lido."""
        with caplog.at_level(logging.INFO):
            rodar(
                cal,
                tmp_path,
                sequencia=[
                    campos_de(exp_em_decimos=None, adena=23_986_985 + n)
                    for n in range(6)
                ],
                carimbos=[float(n) * 10 for n in range(6)],
                fonte=FonteComSaude([SaudeDoFrame.OK] * 6),
                ticks=6,
            )

        arquivo = arquivo_do_personagem(tmp_path, PERSONAGEM)
        assert len(linhas_de_dado(arquivo)) == 6, "SEM LEITURA (EXP) tem de gravar"

        linhas = linhas_do_tique(caplog)
        assert all("SEM LEITURA (EXP)" in linha for linha in linhas), linhas
        assert not any("PARADO" in linha for linha in linhas)
        assert not any(linha.endswith("LENDO") for linha in linhas)

    def test_os_TRES_recusados_gravam_e_o_CSV_carrega_os_tres_motivos(
        self, cal, tmp_path, caplog
    ) -> None:
        """SEM LEITURA grava, e o motivo de cada campo viaja NA LINHA do CSV.

        O texto da tela nomeia os CAMPOS e o CSV nomeia os MOTIVOS, e a divisao
        e de largura: `SEM LEITURA (nivel, EXP, adena: campo-vazio)` custa 83
        colunas com o prefixo, contra um teto de 76. O motivo nao se perde -- ele
        esta no disco, na coluna propria de cada campo, e sai alto UMA vez no
        bloco da transicao.
        """
        with caplog.at_level(logging.INFO):
            rodar(
                cal,
                tmp_path,
                sequencia=[campos_de(nivel=None, exp_em_decimos=None, adena=None)],
                carimbos=[float(n) * 10 for n in range(4)],
                fonte=FonteComSaude([SaudeDoFrame.OK] * 4),
                ticks=4,
            )

        arquivo = arquivo_do_personagem(tmp_path, PERSONAGEM)
        assert len(linhas_de_dado(arquivo)) == 4
        for nome in ("motivo_do_nivel", "motivo_do_exp", "motivo_da_adena"):
            assert set(coluna(arquivo, nome)) == {MOTIVO_DO_CAMPO_VAZIO}, nome

        linhas = linhas_do_tique(caplog)
        assert all("SEM LEITURA (nivel, EXP, adena)" in x for x in linhas), linhas

    def test_o_nivel_recusado_com_o_EXP_SUBINDO_continua_LENDO_na_fatia(
        self, cal, tmp_path, caplog
    ) -> None:
        """O caso de 79% dos tiques, ponta a ponta.

        E a linha continua mostrando o MOTIVO daquela recusa -- que e a unica
        pista de conserto que o usuario tem na tela.
        """
        with caplog.at_level(logging.INFO):
            rodar(
                cal,
                tmp_path,
                sequencia=[
                    campos_de(nivel=None, exp_em_decimos=480_000 + n * 10)
                    for n in range(6)
                ],
                carimbos=[float(n) * 10 for n in range(6)],
                fonte=FonteComSaude([SaudeDoFrame.OK] * 6),
                ticks=6,
            )

        linhas = linhas_do_tique(caplog)
        assert not any("PARADO" in x for x in linhas), linhas
        assert not any("SEM LEITURA" in x for x in linhas), linhas
        assert all(MOTIVO_DO_CAMPO_VAZIO in x for x in linhas[1:]), linhas


class TestOsEstadosSaoDISTINGUIVEIS:
    """As 4 da manha, num console rolando, e SEM cor."""

    def test_os_cinco_textos_de_estado_sao_todos_DIFERENTES(self) -> None:
        rastreio = RastreioDoValor()
        classificar_a_visao(
            saude=SaudeDoFrame.OK,
            estado_do_cliente=EstadoDoCliente.EM_JOGO,
            minimizada=False,
            campos=campos_de(),
            rastreio=rastreio,
            carimbo=0.0,
            segundos_para_parado=SEGUNDOS_PARA_DECLARAR_PARADO,
        )
        parado = classificar_a_visao(
            saude=SaudeDoFrame.OK,
            estado_do_cliente=EstadoDoCliente.EM_JOGO,
            minimizada=False,
            campos=campos_de(),
            rastreio=rastreio,
            carimbo=1000.0,
            segundos_para_parado=SEGUNDOS_PARA_DECLARAR_PARADO,
        )
        so_exp = classificar_a_visao(
            saude=SaudeDoFrame.OK,
            estado_do_cliente=EstadoDoCliente.EM_JOGO,
            minimizada=False,
            campos=campos_de(exp_em_decimos=None),
            rastreio=RastreioDoValor(),
            carimbo=0.0,
            segundos_para_parado=SEGUNDOS_PARA_DECLARAR_PARADO,
        )
        os_tres = classificar_a_visao(
            saude=SaudeDoFrame.OK,
            estado_do_cliente=EstadoDoCliente.EM_JOGO,
            minimizada=False,
            campos=campos_de(nivel=None, exp_em_decimos=None, adena=None),
            rastreio=RastreioDoValor(),
            carimbo=0.0,
            segundos_para_parado=SEGUNDOS_PARA_DECLARAR_PARADO,
        )
        pausado = classificar_a_visao(
            saude=SaudeDoFrame.FALHA_DE_CAPTURA,
            estado_do_cliente=EstadoDoCliente.EM_JOGO,
            minimizada=False,
            campos=campos_de(),
            rastreio=RastreioDoValor(),
            carimbo=0.0,
            segundos_para_parado=SEGUNDOS_PARA_DECLARAR_PARADO,
        )

        textos = [parado.texto, so_exp.texto, os_tres.texto, pausado.texto]
        assert len(set(textos)) == 4, textos
        assert parado.texto.startswith("PARADO")
        assert so_exp.texto.startswith("SEM LEITURA")
        assert pausado.texto.startswith("PAUSADO")

    def test_a_LINHA_MAIS_LONGA_com_os_valores_reais_cabe_no_teto(self) -> None:
        """MEDIDO, e nao afirmado, com `nivel 68  EXP 48,0075%  adena
        23.986.985` -- os valores lidos ao vivo em 2026-09-03.

        O teto e `LARGURA_DO_AVISO`, *"a largura em que ela cabe num console
        padrao de 80"*. Nenhum dos cinco estados pode sair truncado: o que a
        truncagem come e sempre o FIM, e o fim e a contagem de amostras que o
        CEGO-02 pede pelo nome e o motivo da pausa que o CEGO-01 existe para
        dizer.
        """
        contagem = ContagemDaRenda()
        casos = []

        rastreio = RastreioDoValor()
        for carimbo in (0.0, 3599.0):
            visao = classificar_a_visao(
                saude=SaudeDoFrame.OK,
                estado_do_cliente=EstadoDoCliente.EM_JOGO,
                minimizada=False,
                campos=campos_de(),
                rastreio=rastreio,
                carimbo=carimbo,
                segundos_para_parado=SEGUNDOS_PARA_DECLARAR_PARADO,
            )
        casos.append((campos_de(), visao.texto))

        for saude, estado, mini, campos in (
            (SaudeDoFrame.OK, EstadoDoCliente.TELA_DE_LOGIN, False, campos_de()),
            (SaudeDoFrame.OK, EstadoDoCliente.DESCONECTADO, False, campos_de()),
            (SaudeDoFrame.OK, EstadoDoCliente.DESCONHECIDO, False, campos_de()),
            (SaudeDoFrame.CONGELADO, EstadoDoCliente.EM_JOGO, False, campos_de()),
            (
                SaudeDoFrame.FALHA_DE_CAPTURA,
                EstadoDoCliente.EM_JOGO,
                False,
                campos_de(),
            ),
            (SaudeDoFrame.OK, EstadoDoCliente.EM_JOGO, True, campos_de()),
            (
                SaudeDoFrame.OK,
                EstadoDoCliente.EM_JOGO,
                False,
                campos_de(exp_em_decimos=None),
            ),
            (
                SaudeDoFrame.OK,
                EstadoDoCliente.EM_JOGO,
                False,
                campos_de(nivel=None, exp_em_decimos=None, adena=None),
            ),
        ):
            visao = classificar_a_visao(
                saude=saude,
                estado_do_cliente=estado,
                minimizada=mini,
                campos=campos,
                rastreio=RastreioDoValor(),
                carimbo=0.0,
                segundos_para_parado=SEGUNDOS_PARA_DECLARAR_PARADO,
            )
            casos.append((campos, visao.texto))

        for campos, estado in casos:
            linha = linha_do_tique(campos, contagem, estado=estado)
            assert len(linha) <= LARGURA_MAXIMA_DA_LINHA_DO_TIQUE, (
                f"{len(linha)} colunas, teto "
                f"{LARGURA_MAXIMA_DA_LINHA_DO_TIQUE}:\n  {linha}"
            )
            assert "~" not in linha, (
                f"o estado saiu TRUNCADO, e a truncagem come o fim:\n  {linha}"
            )

    def test_PARADO_e_PAUSADO_nao_usam_a_MESMA_MARCA_no_bloco_alto(self) -> None:
        """A distincao tem de sobreviver SEM cor.

        `console._pintar` desliga o ANSI quando `isatty()` e falso -- o caso do
        `caplog`, de um pipe e do `scanner.log`, que e onde o usuario olha de
        manha. Um estado que so se distinguisse por cor sumiria justamente ali.
        """
        marcas = {
            MARCA_POR_ESTADO[estado.value] for estado in EstadoDaRenda
        }
        assert len(marcas) == len(list(EstadoDaRenda)), MARCA_POR_ESTADO
        assert (
            MARCA_POR_ESTADO["parado"] != MARCA_POR_ESTADO["pausado"]
        )

    def test_entrar_e_sair_de_PARADO_logam_UMA_VEZ_CADA(
        self, cal, tmp_path, caplog
    ) -> None:
        sequencia = (
            [campos_de(exp_em_decimos=480_075)] * 20
            + [campos_de(exp_em_decimos=480_085)] * 5
        )
        with caplog.at_level(logging.INFO):
            rodar(
                cal,
                tmp_path,
                sequencia=sequencia,
                carimbos=[float(n) * 10 for n in range(25)],
                fonte=FonteComSaude([SaudeDoFrame.OK] * 25),
                ticks=25,
            )

        texto = caplog.text
        assert texto.count("PARADO: o EXP esta bit-identico") == 1, (
            "a entrada em PARADO tem de logar uma vez, e uma so"
        )
        assert texto.count("o EXP voltou a mudar") == 1, (
            "a saida de PARADO tem de logar uma vez, e uma so"
        )


class TestOsQuatroContadoresDoResumo:
    """Eles NAO se somam entre si -- sao perguntas com consertos diferentes.

    E A SOMA PROVA POUCO, E ESTE ARQUIVO DIZ ISSO POR ESCRITO. A igualdade pega
    o tique que se PERDEU na classificacao; ela NAO pega o tique que recebeu o
    estado ERRADO, porque algum estado sempre sai e a soma fecha do mesmo jeito.
    Foi exatamente assim que o quinto caso (`SEM LEITURA (EXP)`) passou
    despercebido na versao anterior deste plano. Os portoes de classificacao
    correta sao os testes NOMINAIS de `test_renda_estado.py`, um por par de
    estados confundiveis; esta soma e a rede embaixo deles, e nao o portao.
    """

    def test_os_quatro_SOMAM_o_total_de_tiques(
        self, cal, tmp_path, caplog
    ) -> None:
        saudes = (
            [SaudeDoFrame.OK] * 4
            + [SaudeDoFrame.FALHA_DE_CAPTURA] * 3
            + [SaudeDoFrame.OK] * 5
        )
        sequencia = (
            [campos_de(exp_em_decimos=480_000 + n * 10) for n in range(4)]
            + [campos_de(nivel=None, exp_em_decimos=None, adena=None)] * 3
            + [campos_de(exp_em_decimos=None)] * 2
            + [campos_de(exp_em_decimos=480_500)] * 3
        )
        with caplog.at_level(logging.INFO):
            rodar(
                cal,
                tmp_path,
                sequencia=sequencia,
                carimbos=[float(n) * 10 for n in range(12)],
                fonte=FonteComSaude(saudes),
                ticks=12,
            )

        contadores = {}
        for linha in caplog.text.splitlines():
            for chave, rotulo in (
                ("lendo", "tiques LENDO"),
                ("parado", "tiques PARADO"),
                ("sem_leitura", "tiques SEM LEITURA"),
                (RECORTE_DO_EXP_SEM_LEITURA, "destes, SEM LEITURA (EXP)"),
                ("pausado", "tiques PAUSADO"),
            ):
                if rotulo in linha:
                    contadores[chave] = int(linha.strip().split()[-1])

        assert set(contadores) >= set(ESTADOS_QUE_SOMAM), contadores
        assert sum(contadores[c] for c in ESTADOS_QUE_SOMAM) == 12, contadores
        assert contadores["pausado"] == 3
        assert contadores[RECORTE_DO_EXP_SEM_LEITURA] == 2
        assert (
            contadores[RECORTE_DO_EXP_SEM_LEITURA] <= contadores["sem_leitura"]
        ), "o recorte do EXP e PARTE do SEM LEITURA, e nao uma quinta parcela"
