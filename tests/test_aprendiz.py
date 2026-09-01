"""O scanner aprendendo sozinho quem ele nunca viu, e continuando calado.

O QUE ESTA FASE ENTREGA

Uma linha OCUPADA cuja imagem de nome nao casa com nada conhecido deixa de ser
misterio permanente: depois de N leituras seguidas com o recorte ESTAVEL, a
assinatura dela e gravada no acervo da Fase 1, SEM nome.

O QUE ELA DELIBERADAMENTE NAO ENTREGA

Ela nao PERGUNTA, nao BATIZA e nao ANUNCIA. Nenhum alerta novo sai daqui, nem no
console nem no WhatsApp: perguntar e a Fase 3 inteira (BATI-01). O aprendizado
aparece no `ResultadoDoTick` e no `scanner.log`, e em nenhum outro lugar.

O SILENCIO DA RECEM-APRENDIDA E HERDADO, E NAO REMENDADO POR CIMA

Ele vem de duas pecas que ja existem, somadas a um elo novo:

- a assinatura entra com `nome=""`, e a string vazia e FALSY, entao
  `_chave_da_linha` (`linha.nome or f"#linha{N}"`) e `_rotular` (`if
  linha.nome:`) degradam sozinhos para `#linhaN` e "Membro N" — desenho da
  Fase 1, sem uma linha de mudanca no rastreador;
- `Rastreador.assinaturas_configuradas` decide entre calar e pegar emprestado o
  nome da lista por POSICAO, e ele nasce `False` numa instalacao sem assinatura
  nenhuma — que e exatamente a instalacao onde esta fase mais importa.

Sem o elo do meio (ligar a flag no instante do primeiro aprendizado) a primeira
pessoa aprendida seria gravada como ANONIMA no disco e ANUNCIADA COM O NOME DE
OUTRA na tela: o defeito que a Fase 1 acabou de consertar, chegando por outra
porta. E por isso que a fatia atravessa mascara, aprendiz, acervo, lista viva,
rastreador e console.

E A GARANTIA NAO E TOTAL. O aprendizado roda DEPOIS do `rastreador.observar` do
mesmo tick, entao nas N leituras ate a primeira assinatura existir a flag ainda
e `False`. Esta fase ENCURTA para N leituras uma janela que hoje dura a sessao
inteira; ela nao a fecha. Quem ler "a linha continua sem anunciar nada" como
valendo desde o primeiro frame vai escrever um teste que nao passa, e concluir
que o codigo esta errado quando e a leitura que esta.
"""

from __future__ import annotations

import ast
import inspect
import logging
import os
import re
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
import pytest

import l2scanner.acervo as mod_acervo
import l2scanner.rastreador
from l2scanner.acervo import (
    AcervoDeIdentidades,
    carregar_identidades,
    chave_da_assinatura,
)
from l2scanner.agenda import AgendaInvalida, RegistroEmDisco
from l2scanner.aprendiz import (
    LEITURAS_PARA_APRENDER,
    REGIME_DE_CINTILACAO,
    REGIME_DE_TURBULENCIA,
    TETO_DE_CELULAS_TOLERADAS,
    AjustesDoAprendiz,
    Aprendiz,
    Candidata,
    ToleranciaAlemDoTeto,
    distancia_de_hamming,
    resumo_das_recusas,
    retrato_das_distancias,
)
from l2scanner.config import ler_ajustes_do_aprendiz
from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.identidade import (
    LIMIAR_DE_CASAMENTO,
    LIMIAR_DO_ORNAMENTO,
    MARGEM_MINIMA_SOBRE_O_SEGUNDO,
    PIXELS_MINIMOS_DE_TEXTO,
    Assinatura,
    _pontuar_mascara,
    criar_assinatura,
    mascara_de_texto,
)
from l2scanner.rastreador import (
    Ajustes,
    PortaoGlobal,
    Rastreador,
    TipoDeEvento,
)
from l2scanner.sessao import ResultadoDoTick, Sessao
from l2scanner.visao import EstadoDaLinha, LeituraDeLinha, Observacao, _recorte_do_nome, extrair

# OS TRES HELPERS DA FASE 1 SAO IMPORTADOS, E NAO COPIADOS.
#
# `BITS_VIRADOS` vale 8 porque foi MEDIDO, e a tabela que o justifica mora
# no comentario dele em `tests/test_acervo.py`. Duplicar o numero aqui o
# transformaria, na primeira leitura de outra pessoa, de numero medido em
# constante inventada — e constante inventada e exatamente o que este
# projeto proibe. `quase_igual` produz a copia com aquele numero de celulas
# viradas, e `semear` escreve uma entrada A MAO, sem passar por nenhum
# caminho de escrita de producao: e assim que o acervo de partida destes
# casos e montado sem depender da propria feature sob teste.
from test_acervo import (  # noqa: E402 - helper irmao, ver o bloco acima
    BITS_VIRADOS,
    assinatura_da_linha,
    falhar_dentro_de,
    quase_igual,
    semear,
)

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures" / "identidade"

# A linha da fixture que fica DESCONHECIDA nos casos da fatia.
#
# A segunda, e nao a primeira, para que o rotulo esperado ("Membro 2") nao possa
# coincidir por acidente com um "Membro 1" vindo de um indice zerado. E a mesma
# escolha, pela mesma razao, de `LINHA_DA_FATIA` em `tests/test_acervo.py`.
LINHA_ALVO = 1

# O nome que a calibracao da fixture da a essa linha. Ele e REMOVIDO das
# assinaturas nos casos da fatia e continua na lista `cal.nomes` de proposito:
# e a lista por POSICAO que a recem-aprendida nao pode pegar emprestada.
NOME_DA_LINHA_ALVO = "J4guar"


# ---------------------------------------------------------------------------
# Fixtures e helpers, no idioma de `tests/test_acervo.py`
# ---------------------------------------------------------------------------


@pytest.fixture
def pixels() -> np.ndarray:
    px = cv2.imread(str(FIXTURES / "party_ordem_original.png"), cv2.IMREAD_COLOR)
    assert px is not None, "fixture da party nao pode ser lida"
    return px


@pytest.fixture
def calibracao() -> Calibracao:
    """A calibracao da fixture com as QUATRO assinaturas que ela ja traz."""
    return Calibracao.carregar(FIXTURES / "calibracao.json")


@pytest.fixture
def tres_conhecidas(calibracao: Calibracao) -> Calibracao:
    """Tres das quatro linhas ja conhecidas; a linha alvo, nao.

    A lista `cal.nomes` continua INTEIRA, com o nome de gente de verdade em
    todas as posicoes. E ela que o rotulo por posicao usaria se o elo do
    `assinaturas_configuradas` faltasse.
    """
    calibracao.assinaturas = [
        a for a in calibracao.assinaturas if a.nome != NOME_DA_LINHA_ALVO
    ]
    return calibracao


@pytest.fixture
def sem_assinatura_nenhuma(calibracao: Calibracao) -> Calibracao:
    """A instalacao nova: `cal.nomes` cheio e NENHUMA assinatura."""
    calibracao.assinaturas = []
    return calibracao


class SilencioParado:
    def ativo(self):
        return False

    def atualizar(self, agora):
        return None


def montar_sessao(cal, tmp_path, *, aprendiz, configuradas=False, ajustes=None):
    """Uma `Sessao` de verdade, com o disco inteiro preso a `tmp_path`.

    A TOLERANCIA DA VOLTA DA VISAO E ZERADA NO DEFAULT, e isso e uma decisao
    escrita e nao um descuido.

    Desde 2026-08-31 o aprendiz so aprende com o portao global em `RASTREANDO`,
    e o portao NASCE `CEGO`: o primeiro tick visivel de qualquer sessao e uma
    REAQUISICAO, que dura `segundos_de_tolerancia_na_volta` (3.0 s em
    producao). Os casos desta suite contam ticks de um em um segundo e falam de
    OUTRA coisa — quantas leituras estaveis viram uma entrada, o que a cegueira
    congela, quem nunca e candidato. Deixar a tolerancia de producao ligada
    neles deslocaria toda contagem em tres ticks sem que nenhum deles passasse
    a medir a reaquisicao: eles apenas mediriam o mesmo de antes, com numeros
    piores de ler.

    Quem fala da reaquisicao PEDE A TOLERANCIA DE VOLTA, pelo parametro
    `ajustes` (ver `TestReaquisicaoNaoEnsina`). Ou seja: o portao novo continua
    provado, e provado num lugar so.
    """
    rastreador = Rastreador(
        nomes=list(cal.nomes),
        assinaturas_configuradas=configuradas,
        ajustes=ajustes
        or Ajustes(confirmacoes_para_morte=2, segundos_de_tolerancia_na_volta=0.0),
    )
    return Sessao(
        cal=cal,
        rastreador=rastreador,
        eventos_agendados=[],
        registro=RegistroEmDisco(tmp_path / ".agenda"),
        silencio=SilencioParado(),
        aprendiz=aprendiz,
    )


def montar_aprendiz(tmp_path, **ajustes):
    pasta = tmp_path / ".identidades"
    return Aprendiz(AcervoDeIdentidades(pasta), AjustesDoAprendiz(**ajustes)), pasta


def rodar(sessao, px, quantos, *, inicio=0):
    """Ticks consecutivos sobre o MESMO frame. Devolve o ultimo resultado."""
    resultado = None
    for i in range(quantos):
        resultado = sessao.tick(
            Frame(pixels=px, indice=inicio + i, saude=SaudeDoFrame.OK),
            momento=1_700_000_000 + inicio + i,
        )
    return resultado


def assinaturas_gravadas(pasta: Path) -> list[str]:
    if not pasta.exists():
        return []
    return sorted(c.name for c in pasta.iterdir() if c.name.startswith("assinatura_"))


def com_hp_zerado(px: np.ndarray, cal: Calibracao, indice: int) -> np.ndarray:
    """O MESMO frame com a barra de HP daquela linha apagada.

    So o INTERIOR da barra e apagado. A moldura mora em `barra_x - 1` e em
    `barra_x + barra_largura` e fica intacta de proposito: apaga-la derrubaria
    `_bordas_da_barra_intactas` e, com ela, o `ui_visivel` do frame inteiro — e
    o caso passaria a provar cegueira em vez de morte.
    """
    layout = cal.layout
    copia = px.copy()
    topo = layout.hp_y + indice * layout.passo
    copia[
        topo : topo + layout.barra_altura,
        layout.barra_x : layout.barra_x + layout.barra_largura,
    ] = 0
    return copia


def cego(px: np.ndarray) -> np.ndarray:
    """Um frame em que a party window nao esta visivel.

    Preto: a ancora nao tem contraste, `ui_visivel` cai, e nenhuma linha e
    lida. E o mesmo desfecho de "outra janela do jogo por cima", que e o caso
    que D-01 recusa.
    """
    return np.zeros_like(px)


def observacao_de(px, cal):
    return extrair(Frame(pixels=px, indice=0, saude=SaudeDoFrame.OK), cal)


def mortes_apos_zerar(obs, indice: int, configuradas: bool, nomes: list[str]):
    """Roda o rastreador de verdade sobre uma sequencia que confirma morte.

    Copiado de `tests/test_acervo.py` de proposito: e a MESMA prova
    comportamental de silencio, agora sobre uma entrada que o proprio scanner
    aprendeu em vez de uma posta a mao.
    """
    r = Rastreador(
        nomes=list(nomes),
        assinaturas_configuradas=configuradas,
        ajustes=Ajustes(confirmacoes_para_morte=2),
    )
    for i in range(15):
        r.observar(obs, -100 + i)
    linhas = list(obs.linhas)
    linhas[indice] = replace(linhas[indice], hp=0.0)
    zerada = replace(obs, linhas=tuple(linhas))
    eventos = []
    for i in range(6):
        eventos.extend(r.observar(zerada, 10 + i))
    return r, [e.membro for e in eventos if e.tipo is TipoDeEvento.MORREU]


# ---------------------------------------------------------------------------
# A GUARDA CONTRA PROVA VAZIA, PRIMEIRO
# ---------------------------------------------------------------------------


class TestOCenarioProvaAlgumaCoisa:
    """Sem esta afirmacao, "gravou exatamente uma entrada" nao prova nada.

    Ela passaria igualzinho num cenario em que NENHUMA linha era candidata e a
    entrada veio de outro lugar. O caso abaixo fixa o cenario: a linha alvo e a
    UNICA que o scanner nao reconhece, e as outras tres ele reconhece pelo nome.
    """

    def test_a_linha_alvo_e_a_unica_nao_reconhecida(self, pixels, tres_conhecidas):
        obs = observacao_de(pixels, tres_conhecidas)
        assert obs.ui_visivel

        alvo = obs.linhas[LINHA_ALVO]
        assert alvo.estado is EstadoDaLinha.COM_MEMBRO
        assert alvo.nome is None, "a linha alvo tem de estar DESCONHECIDA"
        assert alvo.confianca_do_nome < 0.75, (
            "ela tem de falhar por LIMIAR e nao por margem: falha por margem "
            "significa 'conheco DOIS parecidos demais', e D-02 manda calar"
        )

        outras = [
            l
            for l in obs.linhas[:4]
            if l.indice != LINHA_ALVO
        ]
        assert [l.nome for l in outras] == ["Korzis", "Kaus", "TioMad"], (
            "as outras tres tem de ser reconhecidas pelo nome; se nao forem, "
            "o caso nao esta provando aprendizado, esta provando cegueira"
        )

    def test_a_mascara_do_candidato_viaja_na_observacao(self, pixels, tres_conhecidas):
        """`Observacao.mascaras_de_nome` e por onde o candidato chega ao laco."""
        obs = observacao_de(pixels, tres_conhecidas)
        assert LINHA_ALVO in obs.mascaras_de_nome

        mascara = obs.mascaras_de_nome[LINHA_ALVO]
        esperada = mascara_de_texto(_recorte_do_nome(pixels, tres_conhecidas, LINHA_ALVO))
        assert np.array_equal(mascara, esperada)
        assert int(mascara.sum()) >= PIXELS_MINIMOS_DE_TEXTO


# ---------------------------------------------------------------------------
# A FATIA: N leituras estaveis viram UMA entrada sem nome
# ---------------------------------------------------------------------------


class TestAFatiaInteira:
    """Criterio 1 (APRE-01), de ponta a ponta e por comportamento."""

    def test_n_menos_uma_leitura_nao_grava_nada(self, tmp_path, pixels, tres_conhecidas):
        """Vem ANTES do caso que grava, e de proposito.

        Sem ele, "gravou" nao pode ser distinguido de "gravou no primeiro
        frame" — que e literalmente o que o APRE-02 proibe.
        """
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(tres_conhecidas, tmp_path, aprendiz=aprendiz)

        rodar(sessao, pixels, 4)

        assert assinaturas_gravadas(pasta) == [], (
            "quatro leituras nao podem gravar quando o ajuste pede cinco"
        )

    def test_a_enesima_leitura_grava_exatamente_uma_entrada_sem_nome(
        self, tmp_path, pixels, tres_conhecidas
    ):
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(tres_conhecidas, tmp_path, aprendiz=aprendiz)

        resultado = rodar(sessao, pixels, 5)

        gravadas = assinaturas_gravadas(pasta)
        assert len(gravadas) == 1, f"esperava UMA entrada, achei {gravadas}"

        chave = gravadas[0][len("assinatura_") : -len(".json")]
        assert not (pasta / f"nome_{chave}").exists(), (
            "esta fase grava ANONIMO: batizar e a Fase 3 (BATI-02)"
        )

        assert len(resultado.aprendizados) == 1
        aprendizado = resultado.aprendizados[0]
        assert aprendizado.desfecho == "criado"
        assert aprendizado.indice == LINHA_ALVO
        assert aprendizado.assinatura.nome == ""
        assert aprendizado.confianca < 0.75

        esperada = mascara_de_texto(
            _recorte_do_nome(pixels, tres_conhecidas, LINHA_ALVO)
        )
        assert np.array_equal(aprendizado.assinatura.mascara, esperada), (
            "o conteudo gravado tem de ser a mascara DAQUELA linha"
        )

    def test_continuar_rodando_nao_grava_mais_nada(
        self, tmp_path, pixels, tres_conhecidas
    ):
        """A metade de D-03 que o criterio 1 cobra.

        Sem a insercao na lista VIVA a mesma pessoa voltaria a ser candidata no
        tick seguinte, e o acervo ganharia uma entrada nova a cada N ticks para
        a MESMA pessoa — o inchaco que o APRE-04 existe para proibir.
        """
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(tres_conhecidas, tmp_path, aprendiz=aprendiz)

        rodar(sessao, pixels, 5)
        assert len(assinaturas_gravadas(pasta)) == 1

        resultado = rodar(sessao, pixels, 10, inicio=5)
        assert len(assinaturas_gravadas(pasta)) == 1, (
            "dez ticks depois o acervo ainda tem de ter UMA entrada"
        )
        assert resultado.aprendizados == []

    def test_a_recem_aprendida_entra_no_reconhecimento_vivo(
        self, tmp_path, pixels, tres_conhecidas
    ):
        """D-03: e a lista VIVA que o proximo `extrair` entrega."""
        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(tres_conhecidas, tmp_path, aprendiz=aprendiz)

        antes = rodar(sessao, pixels, 4)
        assert antes.observacao.linhas[LINHA_ALVO].nome is None

        rodar(sessao, pixels, 1, inicio=4)
        depois = rodar(sessao, pixels, 1, inicio=5)

        linha = depois.observacao.linhas[LINHA_ALVO]
        assert linha.nome == "", (
            "a recem-aprendida tem de ser RECONHECIDA e continuar anonima"
        )
        assert linha.confianca_do_nome > 0.9, (
            "ela casa contra ela mesma; se nao casar, D-02 nao a veta e o "
            "acervo incha com a MESMA pessoa a cada N ticks"
        )

    def test_a_linha_aprendida_continua_calada(
        self, tmp_path, pixels, tres_conhecidas
    ):
        """A prova e COMPORTAMENTAL, com `cal.nomes` cheio de gente de verdade.

        O reflexo errado aqui e deixar a linha falar, porque reconhece-la parece
        progresso. Nao e: uma entrada anonima nao tem sujeito, e um alerta sem
        sujeito so pode pegar emprestado o nome de outra pessoa.
        """
        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(tres_conhecidas, tmp_path, aprendiz=aprendiz)

        rodar(sessao, pixels, 5)
        depois = rodar(sessao, pixels, 1, inicio=5)

        assert NOME_DA_LINHA_ALVO in tres_conhecidas.nomes, (
            "premissa: ha um nome de gente de verdade naquela posicao da lista"
        )

        rastreador, mortes = mortes_apos_zerar(
            depois.observacao,
            LINHA_ALVO,
            sessao.rastreador.assinaturas_configuradas,
            tres_conhecidas.nomes,
        )
        assert mortes == [], f"uma linha sem sujeito nao morre. Saiu: {mortes}"

        identidade = rastreador._identidade_por_linha[LINHA_ALVO]
        assert identidade == f"#linha{LINHA_ALVO}"
        assert rastreador._nome_exibido(identidade) == f"Membro {LINHA_ALVO + 1}"

    def test_o_elo_do_assinaturas_configuradas(
        self, tmp_path, pixels, sem_assinatura_nenhuma
    ):
        """Sem este elo a fase entrega o defeito que a Fase 1 consertou.

        `_rotular` cairia em `nome_de(indice)` e a pessoa recem-aprendida como
        ANONIMA seria anunciada com o nome de OUTRA.
        """
        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=3)
        sessao = montar_sessao(sem_assinatura_nenhuma, tmp_path, aprendiz=aprendiz)

        assert sessao.rastreador.assinaturas_configuradas is False, (
            "premissa: a instalacao comeca SEM identidade visual nenhuma"
        )

        rodar(sessao, pixels, 2)
        assert sessao.rastreador.assinaturas_configuradas is False

        rodar(sessao, pixels, 1, inicio=2)
        assert sessao.rastreador.assinaturas_configuradas is True

    def test_nada_e_despachado_e_nada_e_anunciado(
        self, tmp_path, pixels, tres_conhecidas
    ):
        """Esta fase e CALADA por decisao de escopo: perguntar e a Fase 3."""
        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(tres_conhecidas, tmp_path, aprendiz=aprendiz)

        resultado = rodar(sessao, pixels, 5)

        assert resultado.aprendizados, "premissa: este tick APRENDEU"
        assert resultado.despachos == []
        assert resultado.eventos == []


# ---------------------------------------------------------------------------
# A TRANSICAO DE REGIME, QUE E DELIBERADA E AVISADA
# ---------------------------------------------------------------------------


class TestAViradaDoRegimeDaParty:
    """A virada muda o comportamento da party INTEIRA, e nao so da linha nova.

    A partir dela `_rotular` devolve "Membro N" para toda linha nao reconhecida
    e `_e_so_uma_posicao` VETA MORREU e RESSUSCITOU para toda identidade
    `#linhaN`. Para quem nunca calibrou assinatura mas preencheu `cal.nomes`, o
    efeito visivel e o scanner PARAR de anunciar mortes por nome no meio do
    farm.

    A virada continua sendo a decisao certa — silencio vence mentira plausivel —
    mas o usuario nao pode descobri-la pela ausencia de alertas.
    """

    def test_antes_morre_com_o_nome_da_lista_e_depois_nao_morre(
        self, tmp_path, pixels, sem_assinatura_nenhuma
    ):
        """As duas metades, atravessando uma `Sessao` real.

        Sem este caso a mudanca de regime da party inteira entraria em campo sem
        ninguem ter escrito que ela e deliberada.
        """
        cal = sem_assinatura_nenhuma
        morto = com_hp_zerado(pixels, cal, LINHA_ALVO)

        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=40)
        sessao = montar_sessao(cal, tmp_path, aprendiz=aprendiz)

        # METADE 1: o comportamento de HOJE, que a suite ja documenta como
        # intencional. Sem assinatura nenhuma o nome por posicao e a unica
        # informacao que existe, e a morte sai com ele.
        rodar(sessao, pixels, 15)
        eventos = []
        for i in range(6):
            antes = sessao.tick(
                Frame(pixels=morto, indice=100 + i, saude=SaudeDoFrame.OK),
                momento=1_700_000_100 + i,
            )
            eventos.extend(antes.eventos)
        mortes_antes = [e.membro for e in eventos if e.tipo is TipoDeEvento.MORREU]
        assert mortes_antes == [NOME_DA_LINHA_ALVO], (
            "antes da virada a morte sai com o nome da lista por POSICAO; se "
            f"nao sair, a metade 1 nao prova nada. Saiu: {mortes_antes}"
        )
        assert sessao.rastreador.assinaturas_configuradas is False

        # METADE 2: depois do aprendizado a mesma linha nao produz evento
        # nenhum e o rotulo e "Membro N".
        aprendiz2, _ = montar_aprendiz(tmp_path, leituras_para_aprender=3)
        sessao2 = montar_sessao(cal, tmp_path, aprendiz=aprendiz2)
        rodar(sessao2, pixels, 3)
        assert sessao2.rastreador.assinaturas_configuradas is True

        depois = rodar(sessao2, pixels, 1, inicio=3)
        rastreador, mortes_depois = mortes_apos_zerar(
            depois.observacao, LINHA_ALVO, True, cal.nomes
        )
        assert mortes_depois == [], (
            f"depois da virada a linha nao tem sujeito. Saiu: {mortes_depois}"
        )
        identidade = rastreador._identidade_por_linha[LINHA_ALVO]
        assert rastreador._nome_exibido(identidade) == f"Membro {LINHA_ALVO + 1}"

    def test_o_aviso_da_virada_sai_uma_vez_so(
        self, tmp_path, pixels, sem_assinatura_nenhuma, caplog
    ):
        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=3)
        sessao = montar_sessao(sem_assinatura_nenhuma, tmp_path, aprendiz=aprendiz)

        with caplog.at_level(logging.WARNING, logger="l2scanner"):
            rodar(sessao, pixels, 3)
            avisos = [
                r.message for r in caplog.records if r.levelno == logging.WARNING
            ]
            assert len(avisos) == 1, f"esperava UM aviso, saiu: {avisos}"
            assert "Membro" in avisos[0]

            caplog.clear()
            rodar(sessao, pixels, 10, inicio=3)
            repetidos = [
                r.message for r in caplog.records if r.levelno == logging.WARNING
            ]
            assert repetidos == [], (
                "repetir o aviso a cada tick e a outra forma de nao ser lido"
            )

    def test_o_aprendizado_e_registrado_ANTES_do_aviso_da_virada(
        self, tmp_path, pixels, sem_assinatura_nenhuma, caplog
    ):
        """A ordem das duas linhas do log, e ela nao e estetica.

        As duas saem no MESMO tick. Com o aviso primeiro, o `scanner.log` da
        primeira sessao real anuncia a mudanca de regime da party ANTES de dizer
        o que a causou — e quem for ler o log procurando o motivo nao acha,
        porque ele esta na linha de baixo.
        """
        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=3)
        sessao = montar_sessao(sem_assinatura_nenhuma, tmp_path, aprendiz=aprendiz)

        with caplog.at_level(logging.INFO, logger="l2scanner"):
            rodar(sessao, pixels, 3)

        niveis = [
            r.levelno
            for r in caplog.records
            if r.levelno in (logging.INFO, logging.WARNING)
        ]
        assert logging.WARNING in niveis, "premissa: a virada aconteceu"
        primeiro_aviso = niveis.index(logging.WARNING)
        assert logging.INFO in niveis[:primeiro_aviso], (
            "o log.info do aprendizado tem de sair ANTES do log.warning da "
            "virada; do contrario o log anuncia a consequencia antes da causa"
        )

    def test_o_log_do_aprendizado_diz_a_confianca_e_os_pixels(
        self, tmp_path, pixels, tres_conhecidas, caplog
    ):
        """T-02-11 e T-02-18: um acervo sem poda precisa de rastro por entrada.

        O pixel torna diagnosticavel, depois, um aprendizado de recorte
        contaminado (T-02-07). A confianca torna diagnosticavel uma SEGUNDA
        entrada da mesma pessoa nascida abaixo do limiar, que D-02 nao guarda:
        uma sequencia de aprendizados com confianca em torno de 0.70 e a
        assinatura desse caso, e sem o numero no log ele e invisivel.
        """
        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=3)
        sessao = montar_sessao(tres_conhecidas, tmp_path, aprendiz=aprendiz)

        with caplog.at_level(logging.INFO, logger="l2scanner"):
            resultado = rodar(sessao, pixels, 3)

        assert resultado.aprendizados, "premissa: este tick APRENDEU"
        aprendizado = resultado.aprendizados[0]
        linhas = [r.getMessage() for r in caplog.records]
        do_aprendizado = [m for m in linhas if aprendizado.chave[:12] in m]
        assert do_aprendizado, f"a chave nao aparece no log. Saiu: {linhas}"

        texto = do_aprendizado[0]
        assert str(aprendizado.assinatura.pixels_de_texto) in texto
        assert "0.37" in texto, (
            f"a confianca com que ele decidiu aprender tem de sair. Saiu: {texto}"
        )
        assert "—" not in texto, "travessao quebra o console cp1252"


# ---------------------------------------------------------------------------
# CEGUEIRA NAO ENSINA (D-01)
# ---------------------------------------------------------------------------


class TestCegueiraNaoEnsina:
    """Aprender sob cegueira gravaria a janela do navegador como se fosse gente.

    `ui_visivel` ja cai quando a moldura da barra some (outra janela por cima) e
    quando a party window aparece sem nenhum icone — os dois casos em que os
    pixels da linha nao sao a pessoa. E a gravacao e IRREVERSIVEL: o acervo nao
    tem comando de esquecer no v1.
    """

    def test_uma_sequencia_cega_inteira_nao_grava_nada(
        self, tmp_path, pixels, tres_conhecidas
    ):
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=3)
        sessao = montar_sessao(tres_conhecidas, tmp_path, aprendiz=aprendiz)

        resultado = rodar(sessao, cego(pixels), 10)
        assert resultado.observacao.ui_visivel is False, "premissa: cegueira"
        assert assinaturas_gravadas(pasta) == []

    def test_a_cegueira_congela_a_contagem_em_vez_de_zerar(
        self, tmp_path, pixels, tres_conhecidas
    ):
        """N-1 visiveis, 3 cegos, 1 visivel identico: a entrada sai no ultimo.

        A cegueira nao zerou a conta, e tambem nao contou como leitura. E o
        mesmo congelamento de `_contar_linhas_sem_nome`, pelo mesmo motivo: nao
        dava para ver, entao nao da para afirmar nada — nem que reconheceu, nem
        que deixou de reconhecer.
        """
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(tres_conhecidas, tmp_path, aprendiz=aprendiz)

        rodar(sessao, pixels, 4)
        assert assinaturas_gravadas(pasta) == []

        rodar(sessao, cego(pixels), 3, inicio=4)
        assert assinaturas_gravadas(pasta) == [], (
            "a cegueira nao pode CONTAR como leitura"
        )

        rodar(sessao, pixels, 1, inicio=7)
        assert len(assinaturas_gravadas(pasta)) == 1, (
            "a cegueira tambem nao pode ZERAR a conta"
        )


# ---------------------------------------------------------------------------
# REAQUISICAO NAO ENSINA (o conserto de 2026-08-31, medido em campo)
# ---------------------------------------------------------------------------


class TestReaquisicaoNaoEnsina:
    """O portao de `ui_visivel` NAO cobria a volta da visao, e isso custou lixo.

    MEDIDO NO `scanner.log` DO USUARIO EM 2026-08-31, com a party recem
    calibrada minutos antes:

        23:14:35 Monitorando: Welazkez, TITANDER, Mostarda, PIRULITO, Yazalaque
        23:14:37 [reajustando]  (todas as linhas com "?")
        23:15:03 Aprendi uma assinatura nova (criado) da linha 1: chave
                 6288ee95..., 77 pixels de texto, confianca 0.1083
        23:15:07 [vigiando]

    A linha 1 era o TITANDER, que ja tinha assinatura calibrada. Confianca
    0.1083 contra `LIMIAR_DE_CASAMENTO` 0.75 quer dizer que o recorte nao
    pareceu com NADA: ele foi colhido enquanto a UI ainda se redesenhava. Virou
    entrada permanente numa pasta que nao e podada.

    `ui_visivel` cai na CEGUEIRA, e so nela. A tolerancia da volta
    (`segundos_de_tolerancia_na_volta`, 3.0 s por padrao) existe justamente
    porque a party window redesenha em partes e as barras mentem por um ou dois
    frames — e o que vale para a barra vale para o RECORTE DO NOME, que e a
    coisa que o aprendiz grava para sempre. 0.1083 e a medida de campo de
    quanto uma leitura de reaquisicao pode divergir.
    """

    @staticmethod
    def _com_tolerancia_de_verdade() -> Ajustes:
        """Os ajustes de producao para a volta da visao.

        O helper `montar_sessao` zera a tolerancia de proposito (ver a
        docstring dele), entao os casos DESTA classe precisam pedir o valor
        real de volta — senao eles provariam o contrario do que afirmam.
        """
        return Ajustes(
            confirmacoes_para_morte=2, segundos_de_tolerancia_na_volta=3.0
        )

    def test_a_reaquisicao_nao_grava_nada(self, tmp_path, pixels, tres_conhecidas):
        """Tres leituras dentro da tolerancia, com o ajuste pedindo DUAS."""
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=2)
        sessao = montar_sessao(
            tres_conhecidas,
            tmp_path,
            aprendiz=aprendiz,
            ajustes=self._com_tolerancia_de_verdade(),
        )

        resultado = rodar(sessao, pixels, 3)

        assert resultado.observacao.ui_visivel is True, (
            "premissa: DA para ver. Um caso que caisse em cegueira estaria "
            "provando o portao velho, nao o novo"
        )
        assert sessao.rastreador.portao is PortaoGlobal.REAQUISICAO, (
            "premissa: o portao global ainda esta em reaquisicao"
        )
        assert sessao._candidatas_para_aprender(resultado.observacao), (
            "premissa: havia candidata neste tick. Sem ela o caso provaria "
            "ausencia de candidata, e nao o portao"
        )
        assert assinaturas_gravadas(pasta) == [], (
            "a reaquisicao nao pode gravar: foi assim que a confianca 0.1083 "
            "do TITANDER virou entrada permanente"
        )

    def test_passada_a_tolerancia_ele_volta_a_aprender(
        self, tmp_path, pixels, tres_conhecidas
    ):
        """O contraponto: o portao ADIA o aprendizado, nunca o mata."""
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=2)
        sessao = montar_sessao(
            tres_conhecidas,
            tmp_path,
            aprendiz=aprendiz,
            ajustes=self._com_tolerancia_de_verdade(),
        )

        rodar(sessao, pixels, 3)
        assert assinaturas_gravadas(pasta) == []

        rodar(sessao, pixels, 2, inicio=3)

        assert sessao.rastreador.portao is PortaoGlobal.RASTREANDO
        assert len(assinaturas_gravadas(pasta)) == 1, (
            "passada a tolerancia o aprendizado tem de acontecer; um portao "
            "que MATA o aprendizado deixaria a pessoa como Membro N para sempre"
        )

    def test_a_reaquisicao_congela_a_contagem_em_vez_de_zerar(
        self, tmp_path, pixels, tres_conhecidas
    ):
        """A MESMA semantica que a cegueira ja tem, e nao um segundo regime.

        Nao chamar o aprendiz e o que CONGELA a contagem em vez de zera-la. O
        congelamento e seguro porque a contagem e por CONTEUDO: se a pessoa
        mudou durante a reaquisicao, a mascara muda e a sequencia recomeca
        sozinha na primeira leitura ja assentada.
        """
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(
            tres_conhecidas,
            tmp_path,
            aprendiz=aprendiz,
            ajustes=self._com_tolerancia_de_verdade(),
        )

        # A reaquisicao do ARRANQUE: o portao global nasce CEGO, entao os
        # primeiros ticks visiveis ja sao volta de visao.
        rodar(sessao, pixels, 3)
        assert assinaturas_gravadas(pasta) == []

        # Quatro leituras assentadas, com o ajuste pedindo cinco.
        rodar(sessao, pixels, 4, inicio=3)
        assert assinaturas_gravadas(pasta) == []

        # Um alt-tab, e a volta dele: tres ticks visiveis DENTRO da tolerancia.
        rodar(sessao, cego(pixels), 1, inicio=7)
        rodar(sessao, pixels, 3, inicio=8)
        assert sessao.rastreador.portao is PortaoGlobal.REAQUISICAO
        assert assinaturas_gravadas(pasta) == [], (
            "a reaquisicao nao pode CONTAR como leitura"
        )

        rodar(sessao, pixels, 1, inicio=11)
        assert len(assinaturas_gravadas(pasta)) == 1, (
            "a reaquisicao tambem nao pode ZERAR a conta"
        )


# ---------------------------------------------------------------------------
# QUEM NUNCA E CANDIDATO
# ---------------------------------------------------------------------------


def _observacao_fabricada(linhas, mascaras, *, ui_visivel=True) -> Observacao:
    return Observacao(
        indice_do_frame=0,
        ui_visivel=ui_visivel,
        linhas=tuple(linhas),
        mascaras_de_nome=mascaras,
    )


class TestQuemNuncaECandidato:
    def test_uma_linha_vazia_nunca_e_candidata(self, tmp_path, tres_conhecidas):
        """Mesmo com `confianca_do_nome` valendo 0.0.

        `identificar_linhas` devolve exatamente 0.0 para ela, e 0.0 passa
        folgado na condicao de D-02.
        """
        aprendiz, _ = montar_aprendiz(tmp_path)
        sessao = montar_sessao(tres_conhecidas, tmp_path, aprendiz=aprendiz)

        mascara = np.ones((20, 100), dtype=np.uint8)
        obs = _observacao_fabricada(
            [LeituraDeLinha(indice=0, estado=EstadoDaLinha.VAZIA, hp=None, mp=None)],
            {0: mascara},
        )
        assert sessao._candidatas_para_aprender(obs) == ()

    def test_uma_linha_ja_reconhecida_e_anonima_nunca_e_candidata(
        self, tmp_path, tres_conhecidas
    ):
        """`linha.nome is None`, e NUNCA `not linha.nome`.

        `""` significa "reconheci esta pessoa e ninguem a batizou"; `None`
        significa "nao sei quem e". `not linha.nome` colapsaria os dois: toda
        pessoa ja aprendida voltaria a ser candidata em todo tick, o recorte
        dela mudaria por uma celula aqui e ali, e o acervo ganharia uma entrada
        nova a cada N ticks para a MESMA pessoa. E o inchaco que o APRE-04
        existe para proibir, escrito num operador.
        """
        aprendiz, _ = montar_aprendiz(tmp_path)
        sessao = montar_sessao(tres_conhecidas, tmp_path, aprendiz=aprendiz)

        mascara = np.ones((20, 100), dtype=np.uint8)
        obs = _observacao_fabricada(
            [
                LeituraDeLinha(
                    indice=0,
                    estado=EstadoDaLinha.COM_MEMBRO,
                    hp=1.0,
                    mp=1.0,
                    nome="",
                    confianca_do_nome=0.98,
                )
            ],
            {0: mascara},
        )
        assert sessao._candidatas_para_aprender(obs) == ()

    def test_sem_ui_visivel_nao_ha_candidata_nenhuma(self, tmp_path, tres_conhecidas):
        aprendiz, _ = montar_aprendiz(tmp_path)
        sessao = montar_sessao(tres_conhecidas, tmp_path, aprendiz=aprendiz)

        mascara = np.ones((20, 100), dtype=np.uint8)
        obs = _observacao_fabricada(
            [
                LeituraDeLinha(
                    indice=0, estado=EstadoDaLinha.COM_MEMBRO, hp=1.0, mp=1.0
                )
            ],
            {0: mascara},
            ui_visivel=False,
        )
        assert sessao._candidatas_para_aprender(obs) == ()

    def test_um_recorte_quase_sem_texto_nunca_vira_entrada(self, tmp_path):
        """O portao do aprendiz e o UNICO que existe na instalacao nova.

        Com a lista de assinaturas VAZIA, `identificar_linhas` retorna cedo e o
        portao de pixel de `_pontuar_mascara` nem chega a rodar. Sem este, a
        primeira coisa que o scanner aprenderia numa instalacao nova seria uma
        linha vazia.
        """
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=5)

        magra = np.zeros((20, 100), dtype=np.uint8)
        magra[0, : PIXELS_MINIMOS_DE_TEXTO - 1] = 1
        assert int(magra.sum()) < PIXELS_MINIMOS_DE_TEXTO

        for _ in range(100):
            saida = aprendiz.observar(
                (Candidata(indice=0, mascara=magra, confianca=0.0),)
            )
            assert saida.aprendizados == []

        assert assinaturas_gravadas(pasta) == []

    def test_uma_candidata_que_ja_casou_acima_do_limiar_nao_aprende(self, tmp_path):
        """D-02: falha por MARGEM cala, e nao aprende.

        Aprender ai acrescenta um quase-duplicado e faz a pessoa PARAR de ser
        reconhecida. Medido na Fase 1: virando 8 celulas, a original casa 1.000
        e a copia 0.921, diferenca 0.079, abaixo dos 0.12 de
        `MARGEM_MINIMA_SOBRE_O_SEGUNDO`.

        A prova exaustiva deste ramo e o plano 02-02; aqui basta a regra.
        """
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=3)

        gorda = np.zeros((20, 100), dtype=np.uint8)
        gorda[5, :40] = 1

        for _ in range(10):
            aprendiz.observar((Candidata(indice=0, mascara=gorda, confianca=0.90),))

        assert assinaturas_gravadas(pasta) == []


# ---------------------------------------------------------------------------
# O ACERVO, E O QUE `ja_existia` SIGNIFICA
# ---------------------------------------------------------------------------


class TestOTriEstadoDoAcervo:
    """`falhou` NAO conta como aprendido; `ja_existia` conta.

    As duas instancias do usuario (Yazalaque e Faerlina) aprendem sobre a mesma
    pasta. Tratar `ja_existia` como motivo para tentar de novo faria a instancia
    perdedora da corrida ficar tentando para sempre.
    """

    def test_ja_existia_conta_como_aprendido(self, tmp_path):
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=2)

        mascara = np.zeros((20, 100), dtype=np.uint8)
        mascara[5, :40] = 1
        AcervoDeIdentidades(pasta).gravar(Assinatura(nome="", mascara=mascara))
        assert len(assinaturas_gravadas(pasta)) == 1

        for _ in range(2):
            saida = aprendiz.observar(
                (Candidata(indice=0, mascara=mascara, confianca=0.1),)
            )

        assert [a.desfecho for a in saida.aprendizados] == ["ja_existia"]
        assert len(assinaturas_gravadas(pasta)) == 1

    def test_falhou_nao_conta_e_a_proxima_sequencia_comeca_do_zero(self, tmp_path):
        """A docstring de `acervo.gravar` antecipou exatamente isto.

        Colapsar `falhou` em `criado` faria esta fase acreditar que aprendeu uma
        pessoa que nao esta em disco.
        """

        class AcervoQueFalha:
            def gravar(self, assinatura):
                return "falhou"

        aprendiz = Aprendiz(AcervoQueFalha(), AjustesDoAprendiz(leituras_para_aprender=2))

        mascara = np.zeros((20, 100), dtype=np.uint8)
        mascara[5, :40] = 1

        for _ in range(2):
            saida = aprendiz.observar(
                (Candidata(indice=0, mascara=mascara, confianca=0.1),)
            )
        assert saida.aprendizados == [], "falhou nao e aprendido"


# ---------------------------------------------------------------------------
# OS PORTOES ESTRUTURAIS
# ---------------------------------------------------------------------------


def _modulos_do_pacote_importados(fonte: str) -> set[str]:
    """Os modulos IRMAOS que este fonte importa, lidos da arvore sintatica.

    AST e nunca `grep`: as docstrings deste projeto citam nomes de modulo em
    prosa ao explicar as proprias regras, e uma busca textual acusaria
    justamente a documentacao que protege a regra. Mesmo motivo que fez
    `_modulos_importados` nascer em `tests/test_presenca.py`.
    """
    achados: set[str] = set()
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.ImportFrom) and no.level and no.module:
            achados.add(no.module.split(".")[0])
        elif isinstance(no, ast.Import):
            for apelido in no.names:
                achados.add(apelido.name.split(".")[-1])
    return achados


class TestOAprendizNaoConheceOMundo:
    """D-09: o aprendiz fala `Assinatura` e `AcervoDeIdentidades`, e nada mais.

    E o mesmo isolamento que o `acervo` conquistou. Quem sabe o que e uma linha
    da party window e o `sessao`, e e la que a candidatura por `COM_MEMBRO` e
    por `ui_visivel` mora.
    """

    PROIBIDOS = {"visao", "sessao", "rastreador", "calibracao"}

    def test_o_conjunto_de_irmaos_importados(self):
        fonte = (RAIZ / "l2scanner" / "aprendiz.py").read_text(encoding="utf-8")
        achados = _modulos_do_pacote_importados(fonte)
        assert achados & self.PROIBIDOS == set(), (
            "aprendiz.py passou a conhecer o mundo. A candidatura mora no "
            f"sessao.py de proposito. Achado: {sorted(achados)}"
        )

    def test_a_prova_pega_um_import_proibido_enfiado(self):
        """Guarda contra prova vazia sobre o fonte REAL."""
        fonte = (RAIZ / "l2scanner" / "aprendiz.py").read_text(encoding="utf-8")
        envenenado = fonte + "\nfrom .rastreador import Rastreador\n"
        assert "rastreador" in _modulos_do_pacote_importados(envenenado)


class TestORastreadorNaoLeAMascara:
    """T-02-08: a seguranca vem de a leitura NAO EXISTIR para ele.

    A mesma protecao de `hp_proprio_aparente` e de `mercado_aberto_aparente`.
    Promover um campo de pixels "so para mostrar" a consumidor de DECISAO dentro
    do detector de morte e literalmente a manobra que produziu o incidente 27x.
    """

    def test_o_fonte_do_rastreador_nao_cita_a_mascara(self):
        fonte = inspect.getsource(l2scanner.rastreador)
        assert "mascaras_de_nome" not in fonte, (
            "rastreador.py passou a ler o campo de mascaras da Observacao. "
            "Apagar este teste NAO e a correcao: o campo existe SO PARA "
            "APRENDER, e um segundo consumidor de decisao dentro do detector "
            "de morte e o incidente 27x de novo"
        )

    def test_o_rastreador_nao_importa_o_aprendiz(self):
        fonte = inspect.getsource(l2scanner.rastreador)
        assert "aprendiz" not in fonte.lower()


# ---------------------------------------------------------------------------
# A DISTANCIA DE HAMMING, a unidade desta fase
# ---------------------------------------------------------------------------


class TestDistanciaDeHamming:
    """A unidade e CELULA porque e a unidade da unica medida que temos.

    Oito e doze celulas numa mascara de 2000, medidas na Fase 1. Comparar contra
    ela e comparar contra o perigo real.
    """

    def test_mascaras_iguais_dao_zero(self):
        a = np.zeros((4, 4), dtype=np.uint8)
        assert distancia_de_hamming(a, a.copy()) == 0

    def test_conta_as_celulas_diferentes(self):
        a = np.zeros((4, 4), dtype=np.uint8)
        b = a.copy()
        b[0, 0] = 1
        b[1, 1] = 1
        b[2, 2] = 1
        assert distancia_de_hamming(a, b) == 3

    def test_forma_diferente_nao_vira_distancia_inventada(self):
        """Nao e "muito diferente": e uma pergunta sem sentido.

        As duas mascaras nao descrevem o mesmo retangulo de tela.
        """
        assert (
            distancia_de_hamming(
                np.zeros((4, 4), dtype=np.uint8), np.zeros((4, 5), dtype=np.uint8)
            )
            is None
        )


# ---------------------------------------------------------------------------
# A INSTABILIDADE E RECUSADA E NAO MEDIADA, E A RECUSA DIZ QUANTO MEDIU (D-07)
# ---------------------------------------------------------------------------


def mascara_de(px: np.ndarray, cal: Calibracao, indice: int) -> np.ndarray:
    return mascara_de_texto(_recorte_do_nome(px, cal, indice))


def com_nome_perturbado(
    px: np.ndarray, cal: Calibracao, indice: int, celulas: int
) -> np.ndarray:
    """O MESMO frame com um numero CONHECIDO de celulas acesas a mais no nome.

    A perturbacao e MEDIDA e nao suposta: acende celulas que estavam APAGADAS na
    mascara, uma a uma, na ordem em que aparecem. Um caso que perturbasse "um
    pouco" e depois afirmasse o desfecho estaria provando outra coisa. E o mesmo
    idioma de `quase_igual` em `tests/test_acervo.py`, que vira bits
    deterministicamente para poder citar a tabela medida.
    """
    regiao = cal.regiao_do_nome(indice)
    apagadas = np.argwhere(mascara_de(px, cal, indice) == 0)
    assert len(apagadas) >= celulas, "a mascara nao tem celulas apagadas que cheguem"

    copia = px.copy()
    for y, x in apagadas[:celulas]:
        copia[regiao.topo + y, regiao.esquerda + x] = (255, 255, 255)
    return copia


def mascaras_com_distancia(base: np.ndarray, celulas: int) -> np.ndarray:
    """Uma copia da mascara a EXATAMENTE `celulas` de distancia de Hamming."""
    copia = base.copy()
    achatada = copia.reshape(-1)
    achatada[:celulas] ^= 1
    assert distancia_de_hamming(base, copia) == celulas
    return copia


def mascara_cheia(pixels_acesos: int = 40) -> np.ndarray:
    """Uma mascara sintetica com texto suficiente para passar o portao."""
    m = np.zeros((20, 100), dtype=np.uint8)
    m[10, :pixels_acesos] = 1
    return m


class TestAInstabilidadeERecusada:
    """Criterio 2 (APRE-02): instabilidade e recusada, e nao mediada.

    Uma assinatura media de duas leituras diferentes e uma assinatura de
    ninguem, e ela fica no acervo para sempre.
    """

    def test_o_recorte_que_muda_a_cada_leitura_nao_grava_nada(self, tmp_path):
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=5)

        base = mascara_cheia()
        for volta in range(15):
            mascara = base.copy()
            mascara.reshape(-1)[volta * 3 : volta * 3 + 3] ^= 1
            aprendiz.observar((Candidata(indice=0, mascara=mascara, confianca=0.1),))

        assert assinaturas_gravadas(pasta) == []

    def test_alternar_estavel_e_mudada_nunca_grava(self, tmp_path):
        """A sequencia REINICIA, e nao acumula."""
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=3)

        base = mascara_cheia()
        outra = mascaras_com_distancia(base, 6)
        for volta in range(30):
            mascara = base if volta % 2 == 0 else outra
            aprendiz.observar((Candidata(indice=0, mascara=mascara, confianca=0.1),))

        assert assinaturas_gravadas(pasta) == [], (
            "alternar duas leituras nunca chega a N; se gravou, a sequencia "
            "esta ACUMULANDO em vez de reiniciar"
        )

    def test_a_instabilidade_nao_e_mediada(self, tmp_path):
        """O que fica gravado bate BIT A BIT com as N leituras estaveis.

        Nem media, nem mediana, nem mistura das anteriores.
        """
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=3)

        instavel = mascara_cheia()
        for volta in range(6):
            mascara = instavel.copy()
            mascara.reshape(-1)[volta * 4 : volta * 4 + 4] ^= 1
            aprendiz.observar((Candidata(indice=0, mascara=mascara, confianca=0.1),))
        assert assinaturas_gravadas(pasta) == []

        estavel = mascaras_com_distancia(mascara_cheia(), 30)
        for _ in range(3):
            aprendiz.observar((Candidata(indice=0, mascara=estavel, confianca=0.1),))

        gravadas = AcervoDeIdentidades(pasta).assinaturas()
        assert len(gravadas) == 1
        assert np.array_equal(gravadas[0].mascara, estavel), (
            "a entrada tem de ser a mascara das leituras ESTAVEIS, e nao uma "
            "media das instaveis que vieram antes"
        )

    def test_forma_diferente_nao_vira_distancia_inventada(self, tmp_path):
        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)

        aprendiz.observar(
            (Candidata(indice=0, mascara=mascara_cheia(), confianca=0.1),)
        )

        outra_forma = np.zeros((30, 100), dtype=np.uint8)
        outra_forma[10, :40] = 1
        saida = aprendiz.observar(
            (Candidata(indice=0, mascara=outra_forma, confianca=0.1),)
        )

        assert len(saida.recusas) == 1
        assert saida.recusas[0].distancia is None
        assert saida.recusas[0].indice == 0


class TestOConteudoMandaENaoOIndice:
    """D-08, nas duas direcoes. Uma delas sozinha nao prova a regra."""

    def test_a_mesma_pessoa_trocando_de_linha_continua_somando(self, tmp_path):
        """A party window compacta quando alguem sai.

        Um contador por indice perderia a sequencia inteira nessa hora, e a
        pessoa nunca seria aprendida.
        """
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=5)

        mascara = mascara_cheia()
        for indice in (0, 2, 1, 3, 2):
            aprendiz.observar(
                (Candidata(indice=indice, mascara=mascara, confianca=0.1),)
            )

        assert len(assinaturas_gravadas(pasta)) == 1, (
            "a mesma pessoa passou por quatro posicoes e a sequencia e por "
            "CONTEUDO: ela tem de somar do mesmo jeito"
        )

    def test_duas_pessoas_na_mesma_linha_nunca_somam(self, tmp_path):
        """A metade cara da regra.

        Um contador por indice gravaria aqui, e o que ele gravaria seria uma
        assinatura de ninguem.
        """
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=4)

        uma = mascara_cheia()
        outra = mascaras_com_distancia(mascara_cheia(), 20)
        for volta in range(12):
            aprendiz.observar(
                (
                    Candidata(
                        indice=2,
                        mascara=uma if volta % 2 == 0 else outra,
                        confianca=0.1,
                    ),
                )
            )

        assert assinaturas_gravadas(pasta) == [], (
            "duas pessoas alternando na linha 2 nao sao uma sequencia. Um "
            "contador por INDICE teria gravado, e a entrada seria a mascara de "
            "ninguem"
        )


class TestATolerancia:
    """A tolerancia e um LIMITE, e nao uma sugestao."""

    def test_com_tres_toleradas_uma_diferenca_de_duas_soma(self, tmp_path):
        aprendiz, pasta = montar_aprendiz(
            tmp_path, leituras_para_aprender=4, celulas_toleradas=3
        )

        base = mascara_cheia()
        perto = mascaras_com_distancia(base, 2)
        for volta in range(4):
            aprendiz.observar(
                (
                    Candidata(
                        indice=0,
                        mascara=base if volta % 2 == 0 else perto,
                        confianca=0.1,
                    ),
                )
            )

        assert len(assinaturas_gravadas(pasta)) == 1

    def test_com_tres_toleradas_uma_diferenca_de_quatro_nao_soma(self, tmp_path):
        aprendiz, pasta = montar_aprendiz(
            tmp_path, leituras_para_aprender=4, celulas_toleradas=3
        )

        base = mascara_cheia()
        longe = mascaras_com_distancia(base, 4)
        for volta in range(12):
            aprendiz.observar(
                (
                    Candidata(
                        indice=0,
                        mascara=base if volta % 2 == 0 else longe,
                        confianca=0.1,
                    ),
                )
            )

        assert assinaturas_gravadas(pasta) == []

    def test_a_ancora_e_a_referencia_e_a_deriva_nao_passa_por_baixo(self, tmp_path):
        """Deriva de 2 celulas POR LEITURA, com tolerancia 3.

        Cada leitura fica a 2 celulas da ANTERIOR, mas a quinta fica a 8 da
        PRIMEIRA. Comparar com a leitura anterior aceitaria a sequencia inteira
        e gravaria uma assinatura longe da primeira; comparar com a ANCORA
        recusa. Este caso afirma qual das duas o codigo faz.
        """
        aprendiz, pasta = montar_aprendiz(
            tmp_path, leituras_para_aprender=5, celulas_toleradas=3
        )

        ancora = mascara_cheia()
        leituras = [mascaras_com_distancia(ancora, 2 * passo) for passo in range(5)]
        assert distancia_de_hamming(leituras[0], leituras[4]) == 8
        assert distancia_de_hamming(leituras[3], leituras[4]) == 2, (
            "premissa: cada leitura esta a 2 celulas da anterior"
        )

        for mascara in leituras:
            aprendiz.observar((Candidata(indice=0, mascara=mascara, confianca=0.1),))

        assert assinaturas_gravadas(pasta) == [], (
            "a referencia e a ANCORA: comparar com a leitura anterior deixaria "
            "a deriva somar N celulas ao longo da sequencia"
        )


class TestARecusaDizQuantoMediu:
    """D-07, a peca que substitui uma ferramenta de spike.

    Sem este numero, o desfecho de um `celulas_toleradas` errado e a feature
    simplesmente NAO ACONTECER, em silencio, sem nada no log dizendo por que.
    """

    CELULAS = 5

    def test_a_recusa_chega_ao_resultado_do_tick_com_a_distancia_medida(
        self, tmp_path, pixels, tres_conhecidas
    ):
        cal = tres_conhecidas
        outro = com_nome_perturbado(pixels, cal, LINHA_ALVO, self.CELULAS)
        assert (
            distancia_de_hamming(
                mascara_de(pixels, cal, LINHA_ALVO),
                mascara_de(outro, cal, LINHA_ALVO),
            )
            == self.CELULAS
        ), "a perturbacao e MEDIDA antes de o desfecho ser afirmado"

        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(cal, tmp_path, aprendiz=aprendiz)

        rodar(sessao, pixels, 1)
        resultado = rodar(sessao, outro, 1, inicio=1)

        assert len(resultado.recusas_de_aprendizado) == 1
        recusa = resultado.recusas_de_aprendizado[0]
        assert recusa.indice == LINHA_ALVO
        assert recusa.distancia == self.CELULAS
        assert recusa.tolerado == 0

    def test_o_mesmo_numero_sai_no_scanner_log_e_diz_o_que_fazer(
        self, tmp_path, pixels, tres_conhecidas, caplog
    ):
        """Um campo estruturado que so o teste ve nao ajuda o usuario.

        O `scanner.log` da primeira sessao real e o unico lugar onde o numero
        alcanca quem escolhe a tolerancia.
        """
        cal = tres_conhecidas
        outro = com_nome_perturbado(pixels, cal, LINHA_ALVO, self.CELULAS)

        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(cal, tmp_path, aprendiz=aprendiz)

        with caplog.at_level(logging.DEBUG, logger="l2scanner"):
            rodar(sessao, pixels, 1)
            rodar(sessao, outro, 1, inicio=1)

        texto = "\n".join(r.getMessage() for r in caplog.records)
        assert str(self.CELULAS) in texto
        assert "celulas_toleradas" in texto, (
            "a mensagem tem de dizer QUAL chave do config.toml mexer"
        )
        assert "identidade" in texto
        assert "—" not in texto, "travessao quebra o console cp1252"

    def test_trezentas_recusas_nao_viram_trezentas_linhas_de_resumo(
        self, tmp_path, calibracao, caplog
    ):
        """T-02-10: uma linha por segundo no log e a outra forma de nao ser lido.

        A emissao e por MUDANCA do retrato, e nao a cada K recusas: qualquer K
        seria um numero inventado, e este plano nao pode acrescentar um. Por
        mudanca ela e auto-limitada: assim que as distancias convergem, ela cala
        sozinha.
        """
        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(calibracao, tmp_path, aprendiz=aprendiz)

        uma = mascara_cheia()
        outra = mascaras_com_distancia(mascara_cheia(), 7)
        obs_a = _observacao_fabricada(
            [
                LeituraDeLinha(
                    indice=0, estado=EstadoDaLinha.COM_MEMBRO, hp=1.0, mp=1.0
                )
            ],
            {0: uma},
        )
        obs_b = _observacao_fabricada(
            [
                LeituraDeLinha(
                    indice=0, estado=EstadoDaLinha.COM_MEMBRO, hp=1.0, mp=1.0
                )
            ],
            {0: outra},
        )

        # O PORTAO GLOBAL PRECISA ESTAR ASSENTADO, e a linha nao e cerimonia.
        #
        # Desde 2026-08-31 o aprendiz so aprende com o portao em `RASTREANDO`,
        # e o portao NASCE `CEGO`. Este caso chama `_aprender` DIRETO, sem
        # passar por `tick`, entao ninguem levou o rastreador para frente: sem
        # esta leitura o laco de 300 voltas sairia cedo em todas elas e o caso
        # passaria a provar o portao novo, em vez do resumo das recusas.
        #
        # Uma leitura basta porque `montar_sessao` zera
        # `segundos_de_tolerancia_na_volta` (ver a docstring dele).
        sessao.rastreador.observar(obs_a, 0.0)
        assert sessao.rastreador.portao is PortaoGlobal.RASTREANDO, (
            "premissa: o portao global esta assentado"
        )

        with caplog.at_level(logging.INFO, logger="l2scanner"):
            for volta in range(300):
                sessao._aprender(
                    obs_a if volta % 2 == 0 else obs_b, ResultadoDoTick()
                )

        resumos = [
            r.getMessage()
            for r in caplog.records
            if r.levelno >= logging.INFO and "celulas_toleradas" in r.getMessage()
        ]
        assert 0 < len(resumos) <= 3, (
            f"o resumo tem de calar quando o retrato para de mudar. Saiu "
            f"{len(resumos)} vez(es)"
        )

    def test_o_retrato_acumula_a_faixa_das_distancias(self, tmp_path):
        """Minimo, maximo e MEDIANA. A mediana existe por causa do outlier.

        Um unico frame com algo claro passando por cima do nome esticaria o
        maximo e faria o usuario escolher uma tolerancia grande demais.
        """
        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=99)

        base = mascara_cheia()
        aprendiz.observar((Candidata(indice=0, mascara=base, confianca=0.1),))
        for celulas in (4, 2, 40):
            aprendiz.observar(
                (
                    Candidata(
                        indice=0,
                        mascara=mascaras_com_distancia(base, celulas),
                        confianca=0.1,
                    ),
                )
            )
            aprendiz.observar((Candidata(indice=0, mascara=base, confianca=0.1),))

        retrato = aprendiz.retrato()
        assert retrato.recusas == 6, (
            "cada troca de mascara e uma recusa, nos dois sentidos"
        )
        assert retrato.menor == 2
        assert retrato.maior == 40
        assert retrato.mediana is not None and retrato.mediana < 40, (
            "a mediana existe justamente para o outlier nao mandar sozinho"
        )


class TestOConselhoCitaOTetoESugereUmValorValido:
    """O defeito de 2026-09-01: a mensagem mandava fazer o que o arranque recusa.

    O texto antigo terminava em "suba [identidade] celulas_toleradas para um
    valor dentro dessa faixa". A faixa relatada em campo ia de 1 a 1067 celulas,
    e o TETO aceito e 12: quase todo "valor dentro dessa faixa" levantava
    `ToleranciaAlemDoTeto` no arranque seguinte. O usuario leu, foi seguir, e
    teve de perguntar.

    Tres coisas o texto passa a fazer, e cada uma tem um caso aqui: citar o teto
    junto da faixa, dizer QUANTAS das recusas cabem embaixo dele, e entregar um
    valor CONCRETO que o `__post_init__` aceita, ou dizer que subir a tolerancia
    nao resolve.
    """

    # A MEDICAO DE CAMPO DE 2026-09-01, contra a tela real do usuario: 12 frames
    # consecutivos, 1 s de intervalo, party estavel, mascara de 2200 celulas.
    #
    #     linha 0: 165 px de texto | min 3, MEDIANA 8, max 25
    #     linha 1: 123 px de texto | min 0, MEDIANA 2, max 31
    #     linha 2: 105 px de texto | min 1, MEDIANA 3, max 99
    #     linha 3: 106 px de texto | min 0, MEDIANA 0, max 176
    #
    # Esta tupla REPRODUZ a linha 0, que e a pior das quatro: min 3, mediana 8,
    # max 25. A linha 0 e a escolhida de proposito, porque um conselho que serve
    # para a pior linha serve para as outras tres.
    CINTILACAO = (3, 5, 8, 20, 25)

    # A TURBULENCIA de 2026-08-31, a party se remontando apos um disconnect:
    # 104 recusas, min 1, MEDIANA 298.5, max 1067. Esta tupla reproduz os tres
    # numeros com seis valores, que e o que o retrato precisa para decidir.
    TURBULENCIA = (1, 200, 297, 300, 900, 1067)

    def test_as_duas_medicoes_de_campo_caem_em_regimes_diferentes(self):
        """O discriminante e o TETO, e nao um numero novo.

        Acima de 12 celulas o proprio reconhecedor ja trata as duas leituras
        como pessoas DIFERENTES, entao uma mediana acima do teto nao pode ser
        "a mesma pessoa cintilando". As duas medicoes de campo caem uma de cada
        lado com folga (8 contra 298.5), que e o que torna o teto um
        discriminante medido em vez de uma constante inventada.
        """
        cintilacao = retrato_das_distancias(
            self.CINTILACAO, recusas=len(self.CINTILACAO)
        )
        turbulencia = retrato_das_distancias(
            self.TURBULENCIA, recusas=len(self.TURBULENCIA)
        )

        assert cintilacao.mediana == 8.0, "premissa: a mediana medida na linha 0"
        assert turbulencia.mediana == 298.5, "premissa: a mediana relatada ontem"

        assert cintilacao.regime == REGIME_DE_CINTILACAO
        assert turbulencia.regime == REGIME_DE_TURBULENCIA

    def test_o_valor_sugerido_e_aceito_pelo_arranque(self):
        """O caso que o defeito reprovava, e a razao inteira desta mudanca.

        Nao basta o texto ser mais bonito: o numero que ele entrega tem de
        passar pelo `__post_init__` que recusa acima do teto. Se este caso cair,
        a mensagem voltou a mandar o usuario num valor que o scanner recusa.
        """
        retrato = retrato_das_distancias(self.CINTILACAO, recusas=5)

        assert retrato.sugestao is not None
        assert 0 < retrato.sugestao <= TETO_DE_CELULAS_TOLERADAS
        ajustes = AjustesDoAprendiz(celulas_toleradas=retrato.sugestao)
        assert ajustes.celulas_toleradas == retrato.sugestao

    def test_o_valor_sugerido_sai_das_recusas_que_cabem_no_teto(self):
        """A mediana das que estao ABAIXO do teto, e nao a mediana de tudo.

        Incluir os outliers de 20 e de 25 celulas na conta empurraria a
        sugestao para cima sem necessidade: sao frames com algo por cima do
        nome, e nao a cintilacao que a tolerancia existe para absorver.
        """
        retrato = retrato_das_distancias(self.CINTILACAO, recusas=5)

        assert retrato.abaixo_do_teto == 3, "3, 5 e 8 cabem no teto; 20 e 25 nao"
        assert retrato.sugestao == 5, "a mediana de (3, 5, 8)"

    def test_o_resumo_cita_o_teto_e_quantas_recusas_cabem_nele(self):
        """O numero que decide se vale mexer.

        Se 90 das 104 recusas cabem no teto, subir resolve. Se 1 de 6 cabe, nao
        resolve, e o usuario precisa ler isso em vez de tentar valores.
        """
        retrato = retrato_das_distancias(self.TURBULENCIA, recusas=104)
        texto = resumo_das_recusas(retrato, tolerado=0)

        assert retrato.medidas == 6
        assert retrato.abaixo_do_teto == 1, "so o 1 cabe no teto de 12"
        assert str(TETO_DE_CELULAS_TOLERADAS) in texto, "o texto cita o TETO"
        assert f"{retrato.abaixo_do_teto} das {retrato.medidas}" in texto, (
            "o texto diz QUANTAS das recusas medidas cabem embaixo do teto"
        )

    def test_na_turbulencia_o_texto_nao_manda_escolher_dentro_da_faixa(self):
        """O defeito literal: nenhum valor sai da boca da mensagem aqui.

        Com mediana 298.5 nao existe tolerancia que conserte, porque o teto e
        12. Entregar qualquer numero seria repetir o erro com outra redacao.
        """
        retrato = retrato_das_distancias(self.TURBULENCIA, recusas=104)
        texto = resumo_das_recusas(retrato, tolerado=0)

        assert retrato.sugestao is None
        assert re.search(r"celulas_toleradas\s*=\s*\d", texto) is None, (
            "no regime de turbulencia a mensagem NAO entrega valor nenhum"
        )
        assert "dentro dessa faixa" not in texto, "o texto do defeito de 2026-09-01"
        assert "celulas_toleradas" in texto, "ainda diz QUAL chave nao resolve"

    def test_na_cintilacao_o_texto_entrega_a_linha_pronta_para_copiar(self):
        retrato = retrato_das_distancias(self.CINTILACAO, recusas=5)
        texto = resumo_das_recusas(retrato, tolerado=0)

        assert f"celulas_toleradas = {retrato.sugestao}" in texto, (
            "uma linha pronta para copiar, no idioma de `_EXEMPLO_DA_IDENTIDADE`"
        )
        assert "identidade" in texto, "diz a SECAO"

    def test_os_dois_regimes_sao_nomeados_no_texto(self):
        """O usuario tem de saber em qual dos dois esta.

        Uma mediana de 2 a 8 e cintilacao da borda das letras, normal e
        tratavel; uma mediana de centenas e a party se remontando, e nesse caso
        a resposta certa e ESPERAR, e nao configurar.
        """
        cintilacao = resumo_das_recusas(
            retrato_das_distancias(self.CINTILACAO, recusas=5), tolerado=0
        )
        turbulencia = resumo_das_recusas(
            retrato_das_distancias(self.TURBULENCIA, recusas=104), tolerado=0
        )

        assert "cintilacao" in cintilacao.lower()
        assert "esperar" in turbulencia.lower(), (
            "no regime de turbulencia a acao certa e esperar, e nao configurar"
        )

    def test_sem_distancia_medida_o_texto_nao_manda_configurar_nada(self):
        """Forma diferente nao e "muito diferente": e uma pergunta sem sentido.

        Duas mascaras de retangulos diferentes nao sao duas leituras da mesma
        coisa, e nenhum valor de tolerancia muda isso.
        """
        retrato = retrato_das_distancias((), recusas=4)
        texto = resumo_das_recusas(retrato, tolerado=0)

        assert retrato.regime is None
        assert retrato.sugestao is None
        assert re.search(r"celulas_toleradas\s*=\s*\d", texto) is None

    @pytest.mark.parametrize("distancias", [CINTILACAO, TURBULENCIA, ()])
    def test_o_texto_cabe_no_console_cp1252(self, distancias):
        texto = resumo_das_recusas(
            retrato_das_distancias(distancias, recusas=9), tolerado=0
        )
        assert "—" not in texto, "travessao quebra o console cp1252"
        assert texto == texto.encode("ascii", "ignore").decode("ascii"), (
            "portugues SEM acento em texto de usuario"
        )

    def test_o_aprendiz_de_verdade_produz_um_conselho_utilizavel(self, tmp_path):
        """A ponta a ponta: o retrato de uma sessao de verdade chega no valor.

        As distancias vao de 3 a 25 celulas, que e a faixa medida hoje na linha
        0. O que este caso prende e que o numero que sai do `Aprendiz` passa
        pelo `__post_init__` sem levantar.
        """
        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=99)

        base = mascara_cheia()
        aprendiz.observar((Candidata(indice=0, mascara=base, confianca=0.1),))
        for celulas in (3, 8, 25):
            aprendiz.observar(
                (
                    Candidata(
                        indice=0,
                        mascara=mascaras_com_distancia(base, celulas),
                        confianca=0.1,
                    ),
                )
            )
            aprendiz.observar((Candidata(indice=0, mascara=base, confianca=0.1),))

        retrato = aprendiz.retrato()
        assert retrato.regime == REGIME_DE_CINTILACAO
        assert retrato.sugestao is not None
        AjustesDoAprendiz(celulas_toleradas=retrato.sugestao)

    def test_o_conselho_chega_ao_scanner_log(
        self, tmp_path, pixels, tres_conhecidas, caplog
    ):
        """Um valor que so o teste ve nao ajuda quem escolhe a tolerancia."""
        cal = tres_conhecidas
        outro = com_nome_perturbado(pixels, cal, LINHA_ALVO, 5)

        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(cal, tmp_path, aprendiz=aprendiz)

        with caplog.at_level(logging.INFO, logger="l2scanner"):
            rodar(sessao, pixels, 1)
            rodar(sessao, outro, 1, inicio=1)

        texto = "\n".join(r.getMessage() for r in caplog.records)
        assert "celulas_toleradas = 5" in texto, (
            "a linha pronta para copiar, com o numero medido NA tela do usuario"
        )
        assert str(TETO_DE_CELULAS_TOLERADAS) in texto, "e o teto ao lado dela"


def _docstring_do_aprendiz() -> str:
    """O texto do modulo `aprendiz.py`, para prender uma medicao no lugar."""
    return (RAIZ / "l2scanner" / "aprendiz.py").read_text(encoding="utf-8")


class TestACintilacaoEstaMedidaEEscrita:
    """A hipotese errada ja circulou entre duas sessoes, e vai voltar.

    Ela e: "o cenario esta vazando pela mascara, sobe o `VALOR_MINIMO_DO_TEXTO`".
    Medida com `distanceTransform` sobre o nucleo estavel de 8 frames, a
    cintilacao esta COLADA no texto: 23 de 23 celulas da linha 0 a no maximo
    1.5 px de um pixel de texto. E serrilhado de borda de letra, e mexer no
    limiar de brilho nao conserta nada. Sem isso escrito, a terceira sessao
    reabre a mesma porta.
    """

    def test_a_medicao_da_cintilacao_esta_no_modulo(self):
        fonte = _docstring_do_aprendiz().lower()

        assert "distancetransform" in fonte, "diz COMO foi medido"
        assert "serrilhado" in fonte, "diz O QUE a cintilacao e"
        assert "valor_minimo_do_texto" in fonte.upper().lower(), (
            "nomeia o limiar que a medicao ABSOLVE, para a hipotese errada nao "
            "voltar pela terceira vez"
        )

    def test_o_modulo_registra_as_medianas_das_quatro_linhas(self):
        """Zero, 2, 3 e 8. Elas sao a base do regime de cintilacao."""
        fonte = _docstring_do_aprendiz()

        assert "2026-09-01" in fonte, "a medicao tem DATA"
        for numero in ("165", "123", "105", "106"):
            assert numero in fonte, (
                f"os pixels de texto por linha ({numero}) sao a condicao de "
                "validade da medida, do mesmo jeito que os 48 do teto"
            )


# ---------------------------------------------------------------------------
# O TETO QUE VEM DA MEDIDA, E A TOLERANCIA QUE O USUARIO CONSEGUE MEXER (D-06)
# ---------------------------------------------------------------------------


def _bloco_do_teto() -> str:
    """O texto ao redor de `TETO_DE_CELULAS_TOLERADAS` em `aprendiz.py`.

    Uma JANELA em volta da constante, e nao so o que vem depois: o idioma da
    casa e o comentario de bloco ANTES do valor, como em `identidade.py` e em
    `acervo.py`. O que este helper prende e a CO-LOCALIZACAO — a derivacao mora
    junto do numero, e nao num documento que ninguem abre.

    A ANCORA E A ATRIBUICAO, e nao a primeira mencao do nome. Em 2026-09-01 o
    modulo passou a CITAR `TETO_DE_CELULAS_TOLERADAS` na docstring do topo (ele
    virou o discriminante entre os dois regimes de instabilidade), e uma ancora
    na primeira ocorrencia passou a recortar uma janela la em cima, longe do
    valor. O caso caia sem que a co-localizacao tivesse se perdido, que e o
    modo de falha mais caro que um teste de texto tem: ele mente sobre o que
    quebrou. Buscar o `NOME = ` amarra a janela no unico ponto que interessa.
    """
    fonte = (RAIZ / "l2scanner" / "aprendiz.py").read_text(encoding="utf-8")
    onde = fonte.index("TETO_DE_CELULAS_TOLERADAS = ")
    return fonte[max(0, onde - 4000) : onde + 2000]


class TestOTetoEDerivadoENaoEscolhido:
    """O codigo tem de dizer DE ONDE o numero veio.

    A tolerancia diz "estas duas leituras sao a MESMA pessoa". O reconhecedor
    tambem responde essa pergunta, e as duas respostas nao podem se contradizer.
    """

    def test_o_teto_e_doze(self):
        assert TETO_DE_CELULAS_TOLERADAS == 12

    def test_a_docstring_cita_os_tres_numeros_que_a_sustentam(self):
        """Doze, vinte e QUARENTA E OITO.

        O terceiro e a condicao de validade: sem ele o teto parece uma
        propriedade do reconhecedor, quando e um limite aferido num nome de
        tamanho medio.
        """
        bloco = _bloco_do_teto()

        for numero in ("12", "20", "48"):
            assert numero in bloco, (
                f"a docstring do teto tem de citar {numero}: sem os tres "
                "numeros ele vira uma escolha em vez de uma derivacao"
            )

    def test_a_docstring_diz_que_os_48_pixels_sao_a_condicao_de_validade(self):
        """Doze celulas sao 25% do sinal DAQUELA mascara.

        Num nick curto, com 20 pixels de texto, as mesmas 12 celulas sao 60% do
        sinal e destroem a assinatura muito antes de o reconhecedor chegar perto
        da faixa medida. O teto protege contra o erro grosseiro — uma tolerancia
        de 30, 50 celulas — e nao promete seguranca para todo nick.
        """
        bloco = _bloco_do_teto().lower()

        assert "condicao de validade" in bloco
        assert "pixels de texto" in bloco
        assert "nick" in bloco, (
            "a docstring tem de dizer, em voz alta, que num nick curto as "
            "mesmas celulas sao uma fracao MAIOR do sinal"
        )


class TestAValidacaoDosAjustes:
    """A validacao mora no `__post_init__`, e nao no leitor do `config.toml`.

    O teto nao e uma pergunta de sintaxe de arquivo: e uma propriedade MEDIDA do
    reconhecedor, e ela tem de valer para TODO caminho de construcao — inclusive
    um teste, um script ou um chamador futuro que nunca encoste no
    `config.toml`. Validar so na leitura deixaria a porta aberta para todos os
    outros.
    """

    def test_no_teto_exato_e_aceito(self):
        """A recusa e sobre PASSAR do teto, e nao sobre chegar nele."""
        ajustes = AjustesDoAprendiz(celulas_toleradas=TETO_DE_CELULAS_TOLERADAS)
        assert ajustes.celulas_toleradas == TETO_DE_CELULAS_TOLERADAS

    def test_um_acima_do_teto_e_recusado(self):
        with pytest.raises(ToleranciaAlemDoTeto) as erro:
            AjustesDoAprendiz(celulas_toleradas=TETO_DE_CELULAS_TOLERADAS + 1)

        mensagem = str(erro.value)
        assert str(TETO_DE_CELULAS_TOLERADAS + 1) in mensagem, "diz o RECEBIDO"
        assert str(TETO_DE_CELULAS_TOLERADAS) in mensagem, "diz o TETO"
        assert "celula" in mensagem.lower(), "diz a UNIDADE"
        assert "—" not in mensagem, "travessao quebra o console cp1252"

    def test_tolerancia_negativa_e_recusada(self):
        with pytest.raises(ToleranciaAlemDoTeto) as erro:
            AjustesDoAprendiz(celulas_toleradas=-1)
        assert "celula" in str(erro.value).lower()

    def test_leituras_para_aprender_menor_que_um_e_recusado(self):
        """N igual a zero gravaria no primeiro frame.

        Que e literalmente o que o APRE-02 proibe.
        """
        with pytest.raises(ToleranciaAlemDoTeto) as erro:
            AjustesDoAprendiz(leituras_para_aprender=0)
        assert "leitura" in str(erro.value).lower()


class TestOLeitorDaSecaoIdentidade:
    """A disciplina e a da secao vizinha, copiada linha por linha.

    Arquivo ausente nao e erro, secao ausente nao e erro, chave ausente devolve
    o default daquela chave, TOML quebrado E erro de arranque, e a mensagem
    MOSTRA a secao pronta para copiar em vez de so descreve-la.
    """

    def test_arquivo_ausente_devolve_os_defaults(self, tmp_path):
        ajustes = ler_ajustes_do_aprendiz(tmp_path / "nao-existe.toml")
        assert ajustes == AjustesDoAprendiz()

    def test_secao_ausente_devolve_os_defaults(self, tmp_path):
        alvo = tmp_path / "config.toml"
        alvo.write_text('[mercado]\nwatchlist = []\n', encoding="utf-8")
        assert ler_ajustes_do_aprendiz(alvo) == AjustesDoAprendiz()

    def test_chave_ausente_devolve_o_default_daquela_chave(self, tmp_path):
        alvo = tmp_path / "config.toml"
        alvo.write_text("[identidade]\ncelulas_toleradas = 4\n", encoding="utf-8")

        ajustes = ler_ajustes_do_aprendiz(alvo)
        assert ajustes.celulas_toleradas == 4
        assert ajustes.leituras_para_aprender == LEITURAS_PARA_APRENDER

    def test_toml_quebrado_levanta(self, tmp_path):
        alvo = tmp_path / "config.toml"
        alvo.write_text("[identidade\ncelulas = ", encoding="utf-8")
        with pytest.raises(AgendaInvalida):
            ler_ajustes_do_aprendiz(alvo)

    def test_tipo_errado_levanta_mostrando_a_secao_pronta(self, tmp_path):
        alvo = tmp_path / "config.toml"
        alvo.write_text('[identidade]\ncelulas_toleradas = "tres"\n', encoding="utf-8")

        with pytest.raises(AgendaInvalida) as erro:
            ler_ajustes_do_aprendiz(alvo)

        mensagem = str(erro.value)
        assert "[identidade]" in mensagem
        assert "celulas_toleradas" in mensagem

    def test_a_secao_precisa_ser_uma_secao(self, tmp_path):
        alvo = tmp_path / "config.toml"
        alvo.write_text('identidade = "nao sou secao"\n', encoding="utf-8")
        with pytest.raises(AgendaInvalida):
            ler_ajustes_do_aprendiz(alvo)

    def test_um_booleano_nao_passa_por_inteiro(self, tmp_path):
        """`True` valendo 1 e a armadilha classica do Python.

        Uma tolerancia `true` significaria UMA celula, e o usuario que escreveu
        `true` nao quis dizer isso.
        """
        alvo = tmp_path / "config.toml"
        alvo.write_text("[identidade]\ncelulas_toleradas = true\n", encoding="utf-8")

        with pytest.raises(AgendaInvalida) as erro:
            ler_ajustes_do_aprendiz(alvo)
        assert "celulas_toleradas" in str(erro.value)

    def test_o_teto_continua_valendo_pela_leitura(self, tmp_path):
        alvo = tmp_path / "config.toml"
        alvo.write_text(
            f"[identidade]\ncelulas_toleradas = {TETO_DE_CELULAS_TOLERADAS + 1}\n",
            encoding="utf-8",
        )
        with pytest.raises(ToleranciaAlemDoTeto):
            ler_ajustes_do_aprendiz(alvo)


class TestOCaminhoInteiro:
    """Provado por COMPORTAMENTO, e nao por leitura do campo."""

    def test_um_config_com_tolerancia_produz_um_aprendiz_que_de_fato_tolera(
        self, tmp_path
    ):
        alvo = tmp_path / "config.toml"
        alvo.write_text(
            "[identidade]\nleituras_para_aprender = 4\ncelulas_toleradas = 3\n",
            encoding="utf-8",
        )

        aprendiz = Aprendiz(
            AcervoDeIdentidades(tmp_path / ".identidades"),
            ler_ajustes_do_aprendiz(alvo),
        )

        base = mascara_cheia()
        perto = mascaras_com_distancia(base, 2)
        for volta in range(4):
            aprendiz.observar(
                (
                    Candidata(
                        indice=0,
                        mascara=base if volta % 2 == 0 else perto,
                        confianca=0.1,
                    ),
                )
            )

        assert len(assinaturas_gravadas(tmp_path / ".identidades")) == 1, (
            "leituras a 2 celulas de distancia tem de somar quando o config "
            "pede 3 de tolerancia"
        )


class TestARecusaAcontecENoARRANQUE:
    """D-06 diz que o valor acima do teto e recusado NO ARRANQUE.

    E arranque e COMPORTAMENTO, e nao topologia de codigo. Um teste que
    afirmasse apenas "existe um `except ToleranciaAlemDoTeto` em `main()`"
    provaria que o bloco EXISTE, nunca que a excecao CHEGA nele: ele
    continuaria verde no dia em que alguem envolvesse a leitura de configuracao
    num `try/except Exception` e a recusa parasse de subir.
    """

    def test_main_chamada_de_verdade_devolve_2_com_o_jogo_fechado(
        self, tmp_path, monkeypatch, caplog
    ):
        """Roda com o jogo fechado e sem rede.

        Isso so e verdade porque a leitura acontece ANTES de qualquer fonte de
        captura ser construida. Dentro de `laco_principal` ela ficaria depois de
        `MssSource` / `JanelaSource`, e este caso precisaria de tela viva.
        """
        import sys

        import l2scanner.config
        from l2scanner import __main__ as principal

        alvo = tmp_path / "config.toml"
        alvo.write_text(
            f"[identidade]\ncelulas_toleradas = {TETO_DE_CELULAS_TOLERADAS + 1}\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(l2scanner.config, "ARQUIVO_CONFIG", alvo)

        def nao_deveria_chegar(*_a, **_k):
            raise AssertionError(
                "a recusa tinha de acontecer ANTES do laco: um `except` que "
                "existe nao e um `except` que recebe"
            )

        monkeypatch.setattr(principal, "laco_principal", nao_deveria_chegar)
        monkeypatch.setattr(
            principal, "ARQUIVO_CALIBRACAO", FIXTURES / "calibracao.json"
        )
        monkeypatch.setattr(sys, "argv", ["l2scanner", "--replay", "nao-usada"])

        with caplog.at_level(logging.ERROR, logger=principal.log.name):
            codigo = principal.main()

        assert codigo == 2, "recusar a subir, e nao subir com a configuracao ruim"
        assert str(TETO_DE_CELULAS_TOLERADAS) in caplog.text, (
            "a mensagem tem de chegar ao console, e sem traceback"
        )

    def test_um_config_bom_nao_impede_o_arranque(self, tmp_path, monkeypatch):
        """Guarda contra prova vazia: o caminho acima nao recusa tudo."""
        import sys

        import l2scanner.config
        from l2scanner import __main__ as principal

        alvo = tmp_path / "config.toml"
        alvo.write_text(
            f"[identidade]\ncelulas_toleradas = {TETO_DE_CELULAS_TOLERADAS}\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(l2scanner.config, "ARQUIVO_CONFIG", alvo)

        recebidos = []

        def registrar(args, cal, ajustes_do_aprendiz=None):
            recebidos.append(ajustes_do_aprendiz)
            return 0

        monkeypatch.setattr(principal, "laco_principal", registrar)
        monkeypatch.setattr(
            principal, "ARQUIVO_CALIBRACAO", FIXTURES / "calibracao.json"
        )
        monkeypatch.setattr(sys, "argv", ["l2scanner", "--replay", "nao-usada"])

        assert principal.main() == 0
        assert recebidos == [
            AjustesDoAprendiz(celulas_toleradas=TETO_DE_CELULAS_TOLERADAS)
        ], "os ajustes JA VALIDADOS descem para o laco pelo parametro"


class TestASecaoDoConfigToml:
    """Uma secao que o usuario nunca preencheu tem de continuar funcionando.

    Os dois valores entram COMENTADOS com os defaults, no molde do
    `[mercado] watchlist`: um numero escrito no arquivo e um numero que alguem
    vai achar que precisa ajustar.
    """

    def test_a_secao_identidade_existe_comentada(self):
        texto = (RAIZ / "config.toml").read_text(encoding="utf-8")
        assert "[identidade]" in texto

        bloco = texto[texto.index("[identidade]") :][:2000]
        for chave in ("leituras_para_aprender", "celulas_toleradas"):
            linhas = [
                linha
                for linha in bloco.splitlines()
                if chave in linha and "=" in linha
            ]
            assert linhas, f"{chave} tem de aparecer na secao"
            assert all(linha.lstrip().startswith("#") for linha in linhas), (
                f"{chave} tem de entrar COMENTADA com o default"
            )

    def test_o_comentario_diz_onde_achar_o_numero(self):
        """Fecha o circuito de D-07: o log produz o numero, o comentario diz
        onde coloca-lo.

        A JANELA e em volta de `[identidade]`, e nao so o que vem depois: o tom
        dos vizinhos deste arquivo e o comentario ANTES da secao, ensinando o
        que o numero faz antes de mostrar a linha para descomentar.
        """
        texto = (RAIZ / "config.toml").read_text(encoding="utf-8")
        onde = texto.index("[identidade]")
        bloco = texto[max(0, onde - 3000) : onde + 500]
        assert "scanner.log" in bloco
        assert str(TETO_DE_CELULAS_TOLERADAS) in bloco, (
            "o teto e a razao dele cabem em uma linha"
        )

    def test_o_config_de_verdade_continua_lendo_os_defaults(self):
        """O `config.toml` versionado tem a secao COMENTADA, entao ela nao muda
        nada para quem nunca a preencheu."""
        assert ler_ajustes_do_aprendiz(RAIZ / "config.toml") == AjustesDoAprendiz()


# ---------------------------------------------------------------------------
# APRE-04: A MESMA PESSOA NAO VIRA DUAS ENTRADAS
#
# Quatro caminhos por onde ela poderia virar, e um QUINTO que esta fase nao
# fecha e documenta em vez de esconder (T-02-18, no fim do arquivo).
#
# POR QUE TUDO AQUI COMPARA CONJUNTO DE CHAVES, E NUNCA CONTAGEM
#
# Uma chave trocada por outra passa numa comparacao de contagem. O acervo e
# IRREVERSIVEL no v1 (nao ha comando de esquecer), entao trocar silenciosamente
# a assinatura de alguem pela de outra pessoa e uma corrupcao permanente que
# `len(chaves) == 1` afirmaria estar tudo bem.
# ---------------------------------------------------------------------------


def pasta_do_acervo(tmp_path: Path) -> Path:
    """A MESMA pasta que `montar_aprendiz` usa, para semear antes dele existir."""
    return tmp_path / ".identidades"


def chaves_do_acervo(pasta: Path) -> set[str]:
    """O CONJUNTO de chaves em disco. Nunca a contagem. Ver o bloco acima."""
    if not pasta.exists():
        return set()
    return set(AcervoDeIdentidades(pasta).chaves())


def com_o_acervo_na_lista_viva(cal: Calibracao, pasta: Path) -> Calibracao:
    """As TRES linhas que o arranque de verdade executa, e nada mais.

    `l2scanner/__main__.py` faz exatamente isto com o acervo: constroi
    `AcervoDeIdentidades(pasta)`, chama `carregar_identidades(...)` e atribui o
    resultado a `cal.assinaturas`. Refazer as tres linhas AQUI e o que torna o
    caso de reinicio afirmavel com o jogo fechado, sem rede e sem subir
    processo nenhum.

    Ninguem deve "melhorar" isto depois com um `subprocess`: o que o reinicio
    muda, do ponto de vista desta fase, e so quem esta na lista viva. Um
    processo de verdade acrescentaria captura de tela, relogio e sistema de
    arquivos reais a um caso cuja pergunta nao depende de nenhum dos tres.
    """
    identidades = carregar_identidades(
        list(cal.assinaturas), AcervoDeIdentidades(pasta)
    )
    cal.assinaturas = identidades.assinaturas
    return cal


def pontuacoes_da_linha(px, cal, indice, assinaturas) -> list[float]:
    """As pontuacoes CRUAS daquela linha contra cada assinatura, na ordem.

    Existe para as premissas serem MEDIDAS antes do desfecho. Afirmar "nada foi
    gravado" sem antes afirmar POR QUE a linha nao foi aprendida deixaria o caso
    passar por qualquer motivo, inclusive o motivo errado.
    """
    return _pontuar_mascara(
        mascara_de_texto(_recorte_do_nome(px, cal, indice)), list(assinaturas)
    )


class TestOAcervoVazioAPRENDE_eEsteContrasteVemPrimeiro:
    """A guarda contra prova vazia da familia APRE-04 inteira.

    Toda afirmacao das classes abaixo tem a forma "o conjunto de chaves nao
    mudou". Essa frase passa IGUALZINHA num cenario em que a candidatura nunca
    funcionou: um `_candidatas_para_aprender` que devolvesse sempre `()` faria o
    arquivo inteiro ficar verde afirmando que a fase NAO funciona, com cara de
    estar provando o APRE-04.

    Por isso o contraste vem ANTES, e nao depois. E a mesma disciplina que a
    Fase 1 usou em `TestUmaEntradaAMaoAtravessaOScanner` e que este arquivo ja
    usa em `TestOCenarioProvaAlgumaCoisa`: primeiro se prova que o cenario
    produz alguma coisa, depois se prova que ele nao produz demais.
    """

    def test_a_MESMA_linha_com_o_acervo_VAZIO_e_aprendida(
        self, tmp_path, pixels, tres_conhecidas
    ):
        """A linha alvo das classes abaixo, sem nada no acervo, VIRA uma chave.

        E a mesma linha, a mesma calibracao e o mesmo numero de leituras que os
        casos de nao-aprendizado usam. A UNICA diferenca entre este caso e eles
        e o que esta gravado no acervo, que e precisamente o que APRE-04 afirma
        ser a causa.
        """
        pasta = pasta_do_acervo(tmp_path)
        antes = chaves_do_acervo(pasta)
        assert antes == set(), "o cenario comeca com o acervo vazio"

        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(tres_conhecidas, tmp_path, aprendiz=aprendiz)
        rodar(sessao, pixels, 5)

        depois = chaves_do_acervo(pasta)
        assert len(depois - antes) == 1, (
            "com o acervo vazio a linha alvo TEM de ser aprendida; sem isto "
            f"nenhum caso de nao-aprendizado prova nada. Achado: {depois}"
        )


class TestAPessoaJaRECONHECIDA_NuncaViraUmaSegundaEntrada:
    """Caminho 1: a linha que o casamento contra o acervo ja resolveu.

    Trivial no papel e a metade que quase todo mundo escreve errado. Ver a
    docstring do segundo caso.
    """

    def test_uma_entrada_COM_NOME_casa_a_linha_e_cem_leituras_nao_gravam_nada(
        self, tmp_path, pixels, tres_conhecidas
    ):
        pasta = pasta_do_acervo(tmp_path)
        gravada = assinatura_da_linha(pixels, tres_conhecidas, LINHA_ALVO)
        semear(pasta, gravada, nome=NOME_DA_LINHA_ALVO)
        antes = chaves_do_acervo(pasta)

        cal = com_o_acervo_na_lista_viva(tres_conhecidas, pasta)

        # A PREMISSA, antes do desfecho: a entrada do acervo de fato CASA a
        # linha. Sem esta medida, "nada foi gravado" poderia vir de a linha
        # nunca ter sido candidata por outro motivo.
        obs = observacao_de(pixels, cal)
        assert obs.linhas[LINHA_ALVO].nome == NOME_DA_LINHA_ALVO
        assert obs.linhas[LINHA_ALVO].confianca_do_nome > 0.9

        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(cal, tmp_path, aprendiz=aprendiz, configuradas=True)
        rodar(sessao, pixels, 100)

        assert chaves_do_acervo(pasta) == antes, (
            "uma pessoa que o scanner ja reconhece pelo nome nunca pode virar "
            "uma segunda entrada, nem depois de cem leituras"
        )

    def test_uma_entrada_SEM_NOME_casa_a_linha_e_cem_leituras_nao_gravam_nada(
        self, tmp_path, pixels, tres_conhecidas
    ):
        """O caso que UM OPERADOR quebra, e que nenhum outro teste pegaria.

        `Casamento.nome` de uma entrada ANONIMA do acervo e a string VAZIA, e
        nao `None`. `""` significa "reconheci esta pessoa e ninguem a batizou";
        `None` significa "nao sei quem e". Sao estados DIFERENTES e a condicao
        de candidatura separa os dois com `linha.nome is None`.

        `""` e FALSY. Trocar a condicao por `not linha.nome` compila, passa em
        todo caso que envolve uma pessoa desconhecida, passa em todo caso que
        envolve uma pessoa batizada, e falha SO AQUI: toda pessoa ja aprendida
        voltaria a ser candidata em todo tick. Como o recorte muda por uma
        celula aqui e ali entre uma sessao e outra, a cada N ticks nasceria uma
        entrada nova para a MESMA pessoa, num acervo que nunca e podado e nao
        tem comando de esquecer. E o inchaco que o APRE-04 existe para proibir,
        escrito num operador.

        A diferenca entre `""` e `None` so e observavel depois que existe uma
        entrada anonima E existe um caminho que aprende. As duas coisas passam a
        existir juntas nesta fase, e e por isso que este caso mora aqui e nao na
        Fase 1. (T-02-13)
        """
        pasta = pasta_do_acervo(tmp_path)
        gravada = assinatura_da_linha(pixels, tres_conhecidas, LINHA_ALVO)
        semear(pasta, gravada)  # ANONIMA: sem o irmao `nome_<chave>`
        antes = chaves_do_acervo(pasta)

        cal = com_o_acervo_na_lista_viva(tres_conhecidas, pasta)

        obs = observacao_de(pixels, cal)
        alvo = obs.linhas[LINHA_ALVO]
        assert alvo.nome == "", (
            "a premissa do caso e que a linha esta RECONHECIDA e ANONIMA. "
            f"Achado: {alvo.nome!r}"
        )
        assert alvo.confianca_do_nome > 0.9

        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(cal, tmp_path, aprendiz=aprendiz, configuradas=True)
        rodar(sessao, pixels, 100)

        assert chaves_do_acervo(pasta) == antes, (
            "uma pessoa que o scanner ja reconhece, ainda que ANONIMA, nunca "
            "pode virar uma segunda entrada. "
            f"Antes: {sorted(antes)}. Depois: {sorted(chaves_do_acervo(pasta))}"
        )

    def test_o_operador_e_o_PRIMEIRO_de_DOIS_portoes_e_nenhum_dos_dois_sobra(
        self, tmp_path, pixels, tres_conhecidas
    ):
        """MEDIDO NA EXECUCAO DESTE PLANO, e contraria o que o plano previa.

        O plano 02-02 mandava que o caso de ponta a ponta acima falhasse se
        alguem trocasse `linha.nome is None` por `not linha.nome` em
        `_candidatas_para_aprender`. Ele NAO falha, e a mutacao foi rodada para
        conferir em vez de supor: com o operador trocado, a linha anonima volta
        a ser candidata em todo tick, mas ela chega ao `Aprendiz` com
        `confianca` alta e o portao de D-02 (`confianca >= LIMIAR_DE_CASAMENTO`)
        a descarta antes de qualquer vigia nascer. O acervo continua com uma
        chave, e o desfecho de ponta a ponta e IDENTICO.

        A RAZAO E ESTRUTURAL, e nao sorte desta fixture. So existem dois lugares
        em `identificar_linhas` que atribuem um nome, e os dois exigem pontuacao
        acima de um limiar: `LIMIAR_DE_CASAMENTO` (0.75) no primeiro passe e
        `LIMIAR_DO_ORNAMENTO` (0.85) na repescagem da coroa. Como o segundo e
        MAIOR que o primeiro, "a linha tem nome" implica "a confianca passou de
        0.75" — e e exatamente essa a condicao que D-02 veta. Os dois portoes se
        sobrepoem por construcao.

        O QUE ISSO MUDA, E O QUE NAO MUDA. Nao muda que o operador esta certo:
        `""` significa "reconheci e ninguem batizou" e `None` significa "nao sei
        quem e", e sao estados diferentes. Muda ONDE a troca e observavel: no
        `_candidatas_para_aprender`, e nao no acervo. O caso que prende o
        operador e o unitario
        `TestQuemNuncaECandidato::test_uma_linha_ja_reconhecida_e_anonima_nunca_e_candidata`
        (plano 02-01), e foi ele — e so ele — que a mutacao derrubou.

        E POR ISSO NENHUM DOS DOIS PODE SER REMOVIDO como "redundante". Sao
        defesas em profundidade sobre um acervo IRREVERSIVEL: tirar o portao do
        operador poe toda pessoa ja aprendida na mesa do aprendiz em todo tick,
        e ai a unica coisa entre ela e uma segunda entrada passa a ser um
        `>=` — o mesmo `>=` que
        `TestOVetoESobreONumeroENaoSobreAOrigem` mostra ser sensivel a UM
        centesimo. Tirar D-02 abre a porta da margem. Este caso existe para que
        quem encontrar a sobreposicao um dia leia por que ela e deliberada,
        em vez de "limpar" uma das duas.
        """
        assert LIMIAR_DO_ORNAMENTO >= LIMIAR_DE_CASAMENTO, (
            "e este >= que faz 'tem nome' implicar 'passou do limiar'. Se a "
            "repescagem do ornamento ficasse MAIS BARATA que o primeiro passe, "
            "uma linha poderia receber nome com confianca abaixo de 0.75, D-02 "
            "deixaria de mascarar a troca do operador, e o portao do operador "
            "voltaria a ser a UNICA defesa deste caminho"
        )

        pasta = pasta_do_acervo(tmp_path)
        semear(pasta, assinatura_da_linha(pixels, tres_conhecidas, LINHA_ALVO))
        cal = com_o_acervo_na_lista_viva(tres_conhecidas, pasta)

        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(cal, tmp_path, aprendiz=aprendiz, configuradas=True)

        obs = observacao_de(pixels, cal)
        alvo = obs.linhas[LINHA_ALVO]
        assert alvo.nome == ""
        assert sessao._candidatas_para_aprender(obs) == (), (
            "o portao do operador e o que tira a linha da mesa ANTES do "
            "aprendiz; e aqui, e nao no acervo, que a troca por `not "
            "linha.nome` e observavel"
        )
        assert alvo.confianca_do_nome >= LIMIAR_DE_CASAMENTO, (
            "e este numero e o que D-02 vetaria se ela chegasse la assim mesmo"
        )


class TestAFalhaPorMARGEM_Cala:
    """Caminho 2: a linha calada por ter DOIS candidatos parecidos demais.

    `identificar_linhas` devolve `Casamento(None, ...)` por dois motivos
    diferentes, e eles pedem desfechos OPOSTOS (D-02):

        melhor pontuacao < 0.75      "nao conheco ninguem parecido"   APRENDE
        >= 0.75 e sem margem         "conheco DOIS parecidos demais"  CALA

    Aprender no segundo caso e o pior desfecho deste workstream, e ele ja esta
    escrito na docstring de `acervo.carregar_identidades`: acrescentar ao acervo
    um quase-duplicado de alguem faz essa pessoa PARAR de ser reconhecida, e as
    duas assinaturas caem no silencio pela margem.

    AS PREMISSAS SAO MEDIDAS, E NAO SUPOSTAS. `BITS_VIRADOS` e importado de
    `tests/test_acervo.py` de proposito: o numero 8 nao foi escolhido no olho, e
    a tabela que o justifica esta no comentario dele, na Fase 1. Duplicar o
    numero aqui sem a medicao ao lado o transformaria de numero medido em
    constante inventada, que e exatamente o que este projeto proibe.
    """

    def _semear_o_par(self, pasta, pixels, cal):
        exata = assinatura_da_linha(pixels, cal, LINHA_ALVO)
        copia = quase_igual(exata)
        semear(pasta, exata)
        semear(pasta, copia)
        return exata, copia

    def test_as_quatro_premissas_sao_medidas_ANTES_do_desfecho(
        self, tmp_path, pixels, tres_conhecidas
    ):
        """Na ordem, e cada uma sustenta a seguinte.

        (a) as chaves diferem, senao o caso seria o da deduplicacao por chave;
        (b) as duas pontuacoes passam do limiar, senao a recusa viria do limiar
            e nao da margem, e o caso estaria provando o outro ramo de D-02;
        (c) a diferenca entre elas fica abaixo da margem, que e o que faz
            `identificar_linhas` calar;
        (d) e a linha resultante tem `nome is None` COM confianca ALTA, que e a
            forma exata que a candidatura precisa vetar.
        """
        pasta = pasta_do_acervo(tmp_path)
        exata, copia = self._semear_o_par(pasta, pixels, tres_conhecidas)

        assert chave_da_assinatura(exata) != chave_da_assinatura(copia), (
            "um pixel basta para a chave mudar; se elas fossem iguais o caso "
            "seria o da deduplicacao por chave e nao o da margem"
        )

        cal = com_o_acervo_na_lista_viva(tres_conhecidas, pasta)
        pontos = pontuacoes_da_linha(pixels, cal, LINHA_ALVO, cal.assinaturas)
        duas = sorted(pontos, reverse=True)[:2]

        assert duas[0] > LIMIAR_DE_CASAMENTO, duas
        assert duas[1] > LIMIAR_DE_CASAMENTO, (
            f"as DUAS precisam passar do limiar para a recusa ser por margem: {duas}"
        )
        assert duas[0] - duas[1] < MARGEM_MINIMA_SOBRE_O_SEGUNDO, (
            f"as duas pontuacoes precisam EMPATAR para o caso existir: {duas}"
        )

        alvo = observacao_de(pixels, cal).linhas[LINHA_ALVO]
        assert alvo.nome is None, (
            "o desfecho de `identificar_linhas` aqui e SILENCIO, e e por isso "
            "que a linha chega a `_candidatas_para_aprender` como candidata"
        )
        assert alvo.confianca_do_nome >= LIMIAR_DE_CASAMENTO, (
            "e e ESTE numero, e nao a presenca de algo no acervo, que D-02 "
            f"manda vetar. Achado: {alvo.confianca_do_nome}"
        )

    def test_cem_leituras_estaveis_nao_gravam_NADA(
        self, tmp_path, pixels, tres_conhecidas
    ):
        pasta = pasta_do_acervo(tmp_path)
        self._semear_o_par(pasta, pixels, tres_conhecidas)
        antes = chaves_do_acervo(pasta)
        assert len(antes) == 2

        cal = com_o_acervo_na_lista_viva(tres_conhecidas, pasta)
        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(cal, tmp_path, aprendiz=aprendiz, configuradas=True)
        rodar(sessao, pixels, 100)

        assert chaves_do_acervo(pasta) == antes, (
            "aprender aqui seria acrescentar um TERCEIRO quase-duplicado da "
            "mesma pessoa a um acervo irreversivel, e cada copia torna a "
            "original MENOS reconhecivel, e nao mais"
        )

    def test_os_TRES_desfechos_juntos_mostram_que_a_recusa_e_sobre_a_CONFIANCA(
        self, tmp_path, pixels, calibracao
    ):
        """Vazio APRENDE, uma entrada CALA, duas entradas CALAM.

        Sozinho, "com duas entradas nada foi gravado" seria compativel com a
        regra errada "se ha alguma coisa no acervo, nao aprenda". O caso do meio
        e o que separa as duas leituras: com UMA entrada a linha nem sequer e
        candidata (`nome == ""`), e com DUAS ela e candidata e e VETADA pela
        confianca. Os desfechos coincidem e as causas nao, e e a causa que D-02
        governa.
        """
        desfechos = {}
        confiancas = {}

        for rotulo, quantas in (("vazio", 0), ("uma", 1), ("duas", 2)):
            pasta_da_rodada = tmp_path / rotulo
            cal = Calibracao.carregar(FIXTURES / "calibracao.json")
            cal.assinaturas = [
                a for a in cal.assinaturas if a.nome != NOME_DA_LINHA_ALVO
            ]
            pasta = pasta_do_acervo(pasta_da_rodada)
            exata = assinatura_da_linha(pixels, cal, LINHA_ALVO)
            if quantas >= 1:
                semear(pasta, exata)
            if quantas >= 2:
                semear(pasta, quase_igual(exata))

            antes = chaves_do_acervo(pasta)
            cal = com_o_acervo_na_lista_viva(cal, pasta)
            confiancas[rotulo] = observacao_de(pixels, cal).linhas[LINHA_ALVO]

            aprendiz, _ = montar_aprendiz(
                pasta_da_rodada, leituras_para_aprender=5
            )
            sessao = montar_sessao(
                cal,
                pasta_da_rodada,
                aprendiz=aprendiz,
                configuradas=bool(cal.assinaturas),
            )
            rodar(sessao, pixels, 10)
            desfechos[rotulo] = len(chaves_do_acervo(pasta) - antes)

        assert desfechos == {"vazio": 1, "uma": 0, "duas": 0}, desfechos

        # E as causas, que sao o ponto inteiro do caso.
        assert confiancas["vazio"].nome is None
        assert confiancas["vazio"].confianca_do_nome < LIMIAR_DE_CASAMENTO
        assert confiancas["uma"].nome == "", "reconhecida, e nem chega a ser candidata"
        assert confiancas["duas"].nome is None
        assert confiancas["duas"].confianca_do_nome >= LIMIAR_DE_CASAMENTO, (
            "candidata, e vetada pela CONFIANCA: o mesmo desfecho de 'uma', "
            "por um motivo completamente diferente"
        )


class TestOVetoESobreONumeroENaoSobreAOrigem:
    """A fronteira e no limiar EXATO, e `>=` cala.

    Alimenta o `Aprendiz` direto, sem frame e sem `identificar_linhas`, porque a
    pergunta aqui nao e sobre a party window: e sobre qual comparacao o portao
    de D-02 usa. No limiar exato `identificar_linhas` ainda ACEITA o casamento
    (`if valor < LIMIAR_DE_CASAMENTO: break`), entao um `>` no aprendiz deixaria
    passar uma linha que o reconhecedor considera casada.
    """

    @staticmethod
    def _mascara_com_texto():
        mascara = np.zeros((20, 100), dtype=np.uint8)
        mascara[5, :40] = 1
        return mascara

    def test_no_limiar_EXATO_nao_grava(self, tmp_path):
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=3)
        mascara = self._mascara_com_texto()

        for _ in range(10):
            saida = aprendiz.observar(
                (
                    Candidata(
                        indice=0, mascara=mascara, confianca=LIMIAR_DE_CASAMENTO
                    ),
                )
            )
            assert saida.aprendizados == []

        assert chaves_do_acervo(pasta) == set(), (
            "no limiar exato o reconhecedor ainda considera a linha CASADA; a "
            "comparacao do aprendiz tem de ser >= e nao >"
        )

    def test_um_centesimo_ABAIXO_do_limiar_grava(self, tmp_path):
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=3)
        mascara = self._mascara_com_texto()

        for _ in range(3):
            aprendiz.observar(
                (
                    Candidata(
                        indice=0,
                        mascara=mascara,
                        confianca=LIMIAR_DE_CASAMENTO - 0.01,
                    ),
                )
            )

        assert len(chaves_do_acervo(pasta)) == 1, (
            "sem este contraste o caso acima passaria num aprendiz que nunca "
            "grava nada"
        )


# ---------------------------------------------------------------------------
# SAI E VOLTA, CAI E SOBE, RODA DUAS VEZES
#
# Caminhos 3 e 4 do APRE-04. A deduplicacao aqui NAO e pela chave de conteudo:
# um pixel basta para a `sha256` mudar, e o recorte de uma pessoa que volta
# nunca e byte a byte o que foi gravado. Ela e por CORRELACAO, e e por isso que
# D-03 exige que a recem-gravada entre na lista viva no MESMO tick.
# ---------------------------------------------------------------------------

# A linha usada nos casos de sair e voltar: a ULTIMA ocupada da fixture.
#
# A escolha e mecanica, e nao estetica. `extrair` PARA no primeiro vao (a party
# window acaba ali), entao apagar o icone de uma linha do meio derrubaria junto
# todas as linhas abaixo dela. Apagando o icone da ultima, so ela sai e as tres
# de cima continuam sendo lidas e reconhecidas — que e exatamente o que a party
# window faz quando alguem sai de verdade.
LINHA_QUE_SAI = 3
NOME_DA_LINHA_QUE_SAI = "TioMad"

# Quantas celulas da mascara sao viradas para a pessoa "voltar diferente".
#
# MEDIDO na execucao deste plano, na linha 3 da fixture (mascara 20x100, 2000
# celulas, 60 pixels de texto), virando celulas deterministicamente com
# `RandomState(42)` no molde de `quase_igual`:
#
#     celulas   pixels   correlacao contra a gravada   desfecho da linha
#         0        60          1.0000                  reconhecida ("")
#         1        61          0.9915                  reconhecida ("")
#         8        68          0.9374                  reconhecida ("")
#        12        70          0.9075                  reconhecida ("")
#        20        78          0.8578                  reconhecida ("")
#        40        98          0.7612                  reconhecida ("")
#        42       100          0.7531                  reconhecida ("")   <- ultima ACIMA
#        43       101          0.7492                  CANDIDATA (None)   <- primeira ABAIXO
#        50       108          0.7231                  CANDIDATA (None)
#
# 12 fica no meio da faixa em que a dedupe por correlacao FUNCIONA: a chave ja
# mudou (uma celula bastaria) e a correlacao continua folgadamente acima de
# `LIMIAR_DE_CASAMENTO`. E uma ESCOLHA, e o criterio 4 e construido dentro dessa
# faixa de proposito. Ver `TestAFronteiraDaDedupe` para a outra metade.
CELULAS_DA_VOLTA = 12

# As duas margens da fronteira, MEDIDAS e nao previstas. Ver a tabela acima e a
# docstring de `TestAFronteiraDaDedupe`.
CELULAS_LOGO_ACIMA_DO_LIMIAR = 42
CELULAS_LOGO_ABAIXO_DO_LIMIAR = 43


@pytest.fixture
def tres_conhecidas_menos_a_ultima(calibracao: Calibracao) -> Calibracao:
    """Tres linhas conhecidas; a ULTIMA, nao. Ver `LINHA_QUE_SAI`."""
    calibracao.assinaturas = [
        a for a in calibracao.assinaturas if a.nome != NOME_DA_LINHA_QUE_SAI
    ]
    return calibracao


def virar_celulas_no_frame(
    px: np.ndarray, cal: Calibracao, indice: int, quantas: int, semente: int = 42
) -> np.ndarray:
    """O MESMO frame com N celulas da mascara daquele nome viradas.

    A pessoa "volta diferente" perturbando o FRAME, e nao a mascara, porque e o
    frame que atravessa `extrair`: perturbar a mascara direto pularia
    `_recorte_do_nome`, `mascara_de_texto` e `identificar_linhas`, que sao
    justamente as tres pecas cuja tolerancia a ruido o criterio 4 afirma.

    A virada e por BRILHO porque a mascara e so um piso de brilho
    (`V > VALOR_MINIMO_DO_TEXTO`): branco puro acende a celula, preto puro a
    apaga. Isso torna a perturbacao EXATA — o numero de celulas pedido e o
    numero de celulas viradas, e o caso afirma a distancia de Hamming resultante
    antes de afirmar qualquer desfecho.

    Deterministico via `RandomState(semente)`, no molde de `quase_igual`: um
    caso que perturbasse "um pouco" e depois afirmasse o desfecho estaria
    provando outra coisa a cada rodada.
    """
    regiao = cal.regiao_do_nome(indice)
    mascara = mascara_de_texto(_recorte_do_nome(px, cal, indice))
    alvos = np.random.RandomState(semente).choice(
        mascara.size, size=quantas, replace=False
    )
    copia = px.copy()
    for plano in alvos:
        y, x = divmod(int(plano), mascara.shape[1])
        copia[regiao.topo + y, regiao.esquerda + x] = (
            (0, 0, 0) if mascara[y, x] else (255, 255, 255)
        )
    return copia


def sem_icone(px: np.ndarray, cal: Calibracao, indice: int) -> np.ndarray:
    """O MESMO frame com aquela linha VAZIA: a pessoa saiu da party.

    Apaga o CONTRASTE do icone (uma chapa cinza uniforme tem desvio zero), que e
    o que `_tem_contraste_de_icone` mede. As barras e a moldura ficam intactas
    de proposito: derrubar a moldura cairia em `_bordas_da_barra_intactas` e o
    caso passaria a provar CEGUEIRA em vez de saida, que sao coisas opostas
    (cegueira CONGELA a contagem, saida REINICIA a sequencia).
    """
    layout = cal.layout
    copia = px.copy()
    topo = layout.icone_y + indice * layout.passo
    copia[
        topo : topo + layout.icone_tamanho,
        layout.icone_x : layout.icone_x + layout.icone_tamanho,
    ] = 128
    return copia


def assinatura_do_frame(px, cal, indice) -> Assinatura:
    """A assinatura ANONIMA que aquele frame produziria para aquela linha."""
    return Assinatura(
        nome="", mascara=mascara_de_texto(_recorte_do_nome(px, cal, indice))
    )


def aprender_a_ultima_linha(tmp_path, pixels, cal, *, leituras=5):
    """Roda a fatia de verdade ate a ultima linha virar UMA entrada.

    Nao semeia nada a mao: o ponto de partida destes casos e uma entrada que o
    proprio scanner aprendeu, porque e a entrada aprendida que precisa vetar as
    proximas.
    """
    aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=leituras)
    sessao = montar_sessao(cal, tmp_path, aprendiz=aprendiz)
    rodar(sessao, pixels, leituras)
    chaves = chaves_do_acervo(pasta)
    assert len(chaves) == 1, f"a fatia tinha de aprender UMA entrada: {chaves}"
    return aprendiz, sessao, pasta, chaves


class TestSaiEVoltaNaMesmaSessao:
    """Criterio 4, primeira metade, e a razao de ela depender de D-03.

    A DEDUPLICACAO AQUI NAO PODE SER POR CHAVE. A chave e o `sha256` do conteudo
    inteiro da mascara, e um pixel basta para muda-la. Um caso que fizesse a
    pessoa voltar byte a byte igual provaria apenas que bytes iguais dao a mesma
    chave, que e trivial e nao e o caso real. Por isso a premissa (a) e que a
    chave MUDOU.

    O QUE SEGURA A DEDUPE E A CORRELACAO, e ela so existe porque a recem-gravada
    entrou na lista viva no mesmo tick (D-03). Sem essa insercao a pessoa
    voltaria a ser candidata e o acervo ganharia uma copia dela a cada N ticks.

    E A FAIXA E UMA ESCOLHA. `CELULAS_DA_VOLTA` fica DENTRO da zona em que a
    correlacao permanece acima de `LIMIAR_DE_CASAMENTO`, de proposito. Este caso
    afirma que a dedupe funciona NESSA faixa; ele nao afirma, e nao pode ser
    lido como afirmando, que toda volta cai nela. A outra metade da fronteira e
    `TestAFronteiraDaDedupe`, logo abaixo, e as duas vivem no mesmo arquivo
    justamente para ninguem ler esta sozinha.
    """

    def test_a_chave_da_volta_e_DIFERENTE_e_mesmo_assim_nada_novo_nasce(
        self, tmp_path, pixels, tres_conhecidas_menos_a_ultima
    ):
        cal = tres_conhecidas_menos_a_ultima
        _, sessao, pasta, antes = aprender_a_ultima_linha(tmp_path, pixels, cal)

        volta = virar_celulas_no_frame(
            pixels, cal, LINHA_QUE_SAI, CELULAS_DA_VOLTA
        )

        # (a) A CHAVE MUDOU. Sem esta medida o caso e trivial.
        gravada = assinatura_do_frame(pixels, cal, LINHA_QUE_SAI)
        de_volta = assinatura_do_frame(volta, cal, LINHA_QUE_SAI)
        assert chave_da_assinatura(de_volta) != chave_da_assinatura(gravada), (
            "se a chave da volta fosse igual a gravada, este caso provaria "
            "apenas que bytes iguais dao a mesma chave"
        )
        assert distancia_de_hamming(de_volta.mascara, gravada.mascara) == (
            CELULAS_DA_VOLTA
        ), "a perturbacao e EXATA, e o caso a mede antes de afirmar o desfecho"

        # (b) A CORRELACAO ficou acima do limiar e com margem.
        pontos = pontuacoes_da_linha(volta, cal, LINHA_QUE_SAI, cal.assinaturas)
        duas = sorted(pontos, reverse=True)[:2]
        assert duas[0] > LIMIAR_DE_CASAMENTO, duas
        assert duas[0] - duas[1] >= MARGEM_MINIMA_SOBRE_O_SEGUNDO, (
            f"com margem, senao a linha calaria por D-02 e nao por dedupe: {duas}"
        )

        # A pessoa sai da party por alguns ticks...
        rodar(sessao, sem_icone(pixels, cal, LINHA_QUE_SAI), 5, inicio=10)

        # ...e volta, com o recorte diferente.
        obs = observacao_de(volta, cal)
        # (c) Ela e RECONHECIDA, e anonima.
        assert obs.linhas[LINHA_QUE_SAI].nome == "", (
            "a volta tem de casar contra a propria entrada gravada; e este "
            "casamento, e nao a chave, que impede a segunda entrada"
        )

        # (d) E cem leituras depois o conjunto de chaves e o mesmo.
        rodar(sessao, volta, 100, inicio=20)
        assert chaves_do_acervo(pasta) == antes, (
            "sair da party e voltar com o recorte diferente nao pode gerar uma "
            "segunda entrada para a mesma pessoa"
        )


class TestSaiEVoltaDepoisDoReinicio:
    """Criterio 4, segunda metade: o acervo lido no arranque veta igual.

    O REINICIO NAO PRECISA DE PROCESSO, e isso e uma decisao e nao um atalho. O
    arranque de verdade faz exatamente tres coisas com o acervo, e
    `com_o_acervo_na_lista_viva` refaz as tres. Subir um `subprocess` aqui
    acrescentaria captura de tela, relogio e sistema de arquivos reais a um caso
    cuja pergunta — quem esta na lista viva depois do arranque — nao depende de
    nenhum dos tres. Ver a docstring daquele helper antes de "melhorar" isto.
    """

    def test_o_acervo_lido_no_arranque_produz_o_MESMO_veto(
        self, tmp_path, pixels, tres_conhecidas_menos_a_ultima
    ):
        cal = tres_conhecidas_menos_a_ultima
        _, sessao, pasta, antes = aprender_a_ultima_linha(tmp_path, pixels, cal)

        # A pessoa sai...
        rodar(sessao, sem_icone(pixels, cal, LINHA_QUE_SAI), 5, inicio=10)

        # ...e o scanner CAI. Aprendiz, Sessao e Acervo sao descartados, e a
        # calibracao volta a ser a do disco, sem a assinatura que a sessao
        # anterior tinha acrescentado em memoria.
        del sessao
        renascida = Calibracao.carregar(FIXTURES / "calibracao.json")
        renascida.assinaturas = [
            a
            for a in renascida.assinaturas
            if a.nome != NOME_DA_LINHA_QUE_SAI
        ]
        assert len(renascida.assinaturas) == 3, (
            "a lista viva do processo novo comeca SEM a aprendida; e o acervo "
            "em disco que tem de repo-la"
        )
        renascida = com_o_acervo_na_lista_viva(renascida, pasta)
        assert len(renascida.assinaturas) == 4, (
            "carregar_identidades tem de trazer a aprendida de volta"
        )

        aprendiz2, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao2 = montar_sessao(
            renascida, tmp_path, aprendiz=aprendiz2, configuradas=True
        )

        # ...e ela volta, com o recorte diferente do gravado.
        volta = virar_celulas_no_frame(
            pixels, renascida, LINHA_QUE_SAI, CELULAS_DA_VOLTA
        )
        assert observacao_de(volta, renascida).linhas[LINHA_QUE_SAI].nome == ""

        rodar(sessao2, volta, 100)
        assert chaves_do_acervo(pasta) == antes, (
            "derrubar e subir o scanner nao pode fazer a mesma pessoa virar uma "
            "segunda entrada: o acervo lido no arranque e a memoria da fase"
        )


class TestOReplayNaoEngorda:
    """Criterio 5: reproduzir a mesma sequencia duas vezes deixa a mesma conta.

    E a propriedade que torna esta fase depuravel sem morrer no jogo de novo: um
    `--replay` de uma sessao gravada tem de produzir o MESMO acervo que a sessao
    ao vivo produziu. Num acervo IRREVERSIVEL, uma divergencia entre replay e
    campo nao seria um teste instavel, seria uma entrada permanente que ninguem
    consegue reproduzir para investigar.
    """

    def test_a_party_inteira_desconhecida_vira_UMA_entrada_POR_PESSOA(
        self, tmp_path, pixels, sem_assinatura_nenhuma
    ):
        """Quatro linhas, quatro chaves distintas, e nenhuma quinta."""
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(sem_assinatura_nenhuma, tmp_path, aprendiz=aprendiz)

        rodar(sessao, pixels, 5)

        chaves = chaves_do_acervo(pasta)
        assert len(chaves) == 4, (
            f"quatro pessoas desconhecidas sao quatro entradas: {chaves}"
        )

    def test_a_MESMA_sequencia_de_novo_SEM_reinicio_nao_acrescenta_nada(
        self, tmp_path, pixels, sem_assinatura_nenhuma
    ):
        cal = sem_assinatura_nenhuma
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(cal, tmp_path, aprendiz=aprendiz)

        rodar(sessao, pixels, 5)
        primeira = chaves_do_acervo(pasta)
        assert len(primeira) == 4

        rodar(sessao, pixels, 50, inicio=5)

        assert chaves_do_acervo(pasta) == primeira, (
            "a segunda passada da mesma gravacao nao pode acrescentar nem "
            "TROCAR chave nenhuma"
        )

    def test_a_MESMA_sequencia_de_novo_COM_reinicio_no_meio_tambem_nao(
        self, tmp_path, pixels, sem_assinatura_nenhuma
    ):
        aprendiz, pasta = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(sem_assinatura_nenhuma, tmp_path, aprendiz=aprendiz)
        rodar(sessao, pixels, 5)
        primeira = chaves_do_acervo(pasta)
        assert len(primeira) == 4

        del sessao
        renascida = Calibracao.carregar(FIXTURES / "calibracao.json")
        renascida.assinaturas = []
        renascida = com_o_acervo_na_lista_viva(renascida, pasta)
        assert len(renascida.assinaturas) == 4

        aprendiz2, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao2 = montar_sessao(
            renascida, tmp_path, aprendiz=aprendiz2, configuradas=True
        )
        rodar(sessao2, pixels, 50)

        assert chaves_do_acervo(pasta) == primeira, (
            "o replay depois de um reinicio tem de bater com o da sessao viva"
        )


class TestDuasInstanciasUmaEntrada:
    """Yazalaque e Faerlina aprendendo a mesma pessoa sobre a mesma pasta.

    O `O_CREAT|O_EXCL` da Fase 1 ja decide a corrida. O que este caso prende e o
    comportamento de quem PERDE: `ja_existia` e SUCESSO, e o vigia tem de sair
    da mesa exatamente como sai em `criado`. Um `ja_existia` que deixasse o
    vigia vivo faria a instancia perdedora tentar gravar a mesma pessoa a cada
    leitura, pela sessao inteira (T-02-16).
    """

    @staticmethod
    def _mascara():
        mascara = np.zeros((20, 100), dtype=np.uint8)
        mascara[5, :40] = 1
        return mascara

    def test_uma_recebe_criado_a_outra_ja_existia_e_a_pasta_fica_com_UMA_chave(
        self, tmp_path
    ):
        pasta = pasta_do_acervo(tmp_path)
        yazalaque = Aprendiz(
            AcervoDeIdentidades(pasta), AjustesDoAprendiz(leituras_para_aprender=2)
        )
        faerlina = Aprendiz(
            AcervoDeIdentidades(pasta), AjustesDoAprendiz(leituras_para_aprender=2)
        )
        mascara = self._mascara()

        for _ in range(2):
            de_yaza = yazalaque.observar(
                (Candidata(indice=0, mascara=mascara, confianca=0.1),)
            )
            de_faer = faerlina.observar(
                (Candidata(indice=0, mascara=mascara, confianca=0.1),)
            )

        assert [a.desfecho for a in de_yaza.aprendizados] == ["criado"]
        assert [a.desfecho for a in de_faer.aprendizados] == ["ja_existia"], (
            "quem perde a corrida recebe ja_existia, e isso e SUCESSO: a "
            "entrada esta em disco, so nao foi este processo que a criou"
        )
        assert len(chaves_do_acervo(pasta)) == 1

    def test_quem_recebeu_ja_existia_nao_produz_aprendizado_na_leitura_seguinte(
        self, tmp_path
    ):
        """O vigia saiu da mesa; a sequencia recomeca do zero.

        A GARANTIA DESTA CAMADA E ESTA, e ela e menor do que parece: o
        `Aprendiz` sozinho nao sabe que aquela pessoa ja e conhecida, entao ele
        volta a contar do 1 e, N leituras depois, pede `gravar` de novo e recebe
        `ja_existia` de novo. O que faz a instancia perdedora PARAR de verdade e
        D-03, uma camada acima: a assinatura entra na lista viva e a linha deixa
        de ser candidata. O caso abaixo mede as duas coisas em vez de supor uma
        delas — quantos `ja_existia` saem em vinte leituras, e que a pasta
        continua com UMA chave o tempo todo.
        """
        pasta = pasta_do_acervo(tmp_path)
        acervo = AcervoDeIdentidades(pasta)
        mascara = self._mascara()
        acervo.gravar(Assinatura(nome="", mascara=mascara))
        antes = chaves_do_acervo(pasta)
        assert len(antes) == 1

        perdedora = Aprendiz(acervo, AjustesDoAprendiz(leituras_para_aprender=2))
        for _ in range(2):
            saida = perdedora.observar(
                (Candidata(indice=0, mascara=mascara, confianca=0.1),)
            )
        assert [a.desfecho for a in saida.aprendizados] == ["ja_existia"]

        seguinte = perdedora.observar(
            (Candidata(indice=0, mascara=mascara, confianca=0.1),)
        )
        assert seguinte.aprendizados == [], (
            "na leitura SEGUINTE nao pode sair aprendizado nenhum: o vigia tem "
            "de ter saido da mesa em ja_existia, exatamente como sai em criado"
        )

        for _ in range(20):
            perdedora.observar(
                (Candidata(indice=0, mascara=mascara, confianca=0.1),)
            )
        assert chaves_do_acervo(pasta) == antes, (
            "por mais que a perdedora insista, a pasta nunca ganha uma segunda "
            "chave: o O_EXCL da Fase 1 e o que sustenta isso"
        )


class TestFalhouNaoMenteENaoPara:
    """Um disco que falha e reportado como falha, e tentado de novo.

    Colapsar `falhou` em sucesso faria o scanner acreditar que conhece alguem
    que nao esta em disco: a pessoa pararia de ser candidata, ninguem
    perguntaria por ela na Fase 3, e ela ficaria anonima para sempre, sem erro
    em lugar nenhum. E o desfecho que a docstring de `acervo.gravar` nomeia como
    o motivo de o tri-estado existir (T-02-15).
    """

    def test_com_o_disco_fora_nada_entra_na_lista_viva_e_a_flag_nao_liga(
        self, tmp_path, pixels, tres_conhecidas_menos_a_ultima, monkeypatch
    ):
        cal = tres_conhecidas_menos_a_ultima
        pasta = pasta_do_acervo(tmp_path)
        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(cal, tmp_path, aprendiz=aprendiz)

        monkeypatch.setattr(
            mod_acervo.os, "open", falhar_dentro_de(pasta, os.open)
        )
        resultado = rodar(sessao, pixels, 5)

        assert resultado.aprendizados == [], "falhou NAO conta como aprendido"
        assert len(cal.assinaturas) == 3, (
            "uma assinatura que nao esta em disco nao pode entrar na lista viva"
        )
        assert sessao.rastreador.assinaturas_configuradas is False, (
            "e nao pode ligar o regime de identidade da party inteira"
        )
        assert chaves_do_acervo(pasta) == set()

    def test_a_proxima_sequencia_TENTA_DE_NOVO_e_com_o_disco_de_volta_grava(
        self, tmp_path, pixels, tres_conhecidas_menos_a_ultima, monkeypatch
    ):
        cal = tres_conhecidas_menos_a_ultima
        pasta = pasta_do_acervo(tmp_path)
        aprendiz, _ = montar_aprendiz(tmp_path, leituras_para_aprender=5)
        sessao = montar_sessao(cal, tmp_path, aprendiz=aprendiz)

        monkeypatch.setattr(
            mod_acervo.os, "open", falhar_dentro_de(pasta, os.open)
        )
        rodar(sessao, pixels, 5)
        assert chaves_do_acervo(pasta) == set()

        monkeypatch.undo()
        resultado = rodar(sessao, pixels, 5, inicio=5)

        assert [a.desfecho for a in resultado.aprendizados] == ["criado"], (
            "com o disco de volta a MESMA pessoa e aprendida: um falhou nao "
            "pode deixar ninguem anonimo para sempre"
        )
        assert len(chaves_do_acervo(pasta)) == 1


# ---------------------------------------------------------------------------
# T-02-18: A FRONTEIRA DA DEDUPE, DOCUMENTADA EM VEZ DE ESCONDIDA
# ---------------------------------------------------------------------------


class TestAFronteiraDaDedupe:
    """O quinto caminho, que esta fase NAO fecha, afirmado como ACEITO.

    (a) E O UNICO CAMINHO POR ONDE O APRE-04 AINDA PODE SER FURADO. Tudo acima
        prova que a mesma pessoa nao vira duas entradas. Isso vale enquanto a
        volta dela correlacionar ACIMA de `LIMIAR_DE_CASAMENTO` contra a propria
        entrada gravada. Abaixo disso, ela e candidata, e uma segunda entrada
        nasce.

    (b) ELE NASCE DA METADE DE D-02 QUE NAO EXISTE. D-02 veta ACIMA do limiar e
        nao tem nada a dizer abaixo dele: `nome is None and confianca_do_nome <
        LIMIAR_DE_CASAMENTO` e a condicao de candidatura inteira, e uma volta a
        0.70 contra a propria assinatura satisfaz as duas. Nao e um bug do
        codigo; e a regra funcionando na faixa em que ela nao alcanca.

    (c) FECHA-LO EXIGIRIA UM SEGUNDO LIMIAR, E NAO HA COMO CALIBRA-LO. Uma regra
        do tipo "aprenda so se nao parecer com ninguem NEM UM POUCO" precisaria
        de um numero abaixo de 0.75, e nao existe medida de campo do drift do
        recorte entre sessoes para escolhe-lo. A mesma ausencia ja obrigou
        `celulas_toleradas` a nascer em ZERO, e o 02-01-SUMMARY confirmou que
        ela e real: as duas capturas de party window versionadas sao BYTE A BYTE
        identicas, entao compara-las nao mede ruido nenhum, mede uma imagem
        consigo mesma. Um limiar inventado aqui e exatamente o tipo de constante
        que este projeto proibe.

    (d) O RASTRO QUE EXISTE HOJE E `Aprendizado.confianca` NO `log.info`. Uma
        sequencia de aprendizados com confianca em torno de 0.70 e a assinatura
        deste caso em campo. Sem o numero no log, ele e invisivel.

    NAO "CONSERTE" ESTE CASO. Transforma-lo num nao-aprendizado inventaria o
    limiar que nao ha como calibrar; simplesmente nao escreve-lo deixaria a
    suite verde afirmando uma dedupe sem faixa, que e pior do que nao ter a
    suite. Documentar a fronteira e a terceira opcao, e e a honesta.
    """

    def _cenario(self, tmp_path, pixels, cal, celulas):
        _, sessao, pasta, antes = aprender_a_ultima_linha(tmp_path, pixels, cal)
        volta = virar_celulas_no_frame(pixels, cal, LINHA_QUE_SAI, celulas)
        gravada = assinatura_do_frame(pixels, cal, LINHA_QUE_SAI)
        de_volta = assinatura_do_frame(volta, cal, LINHA_QUE_SAI)
        assert distancia_de_hamming(de_volta.mascara, gravada.mascara) == celulas
        correlacao = max(
            pontuacoes_da_linha(volta, cal, LINHA_QUE_SAI, cal.assinaturas)
        )
        return sessao, pasta, antes, volta, correlacao

    def test_o_invariante_que_faz_D02_bastar_ACIMA_do_limiar(
        self, tmp_path, pixels, tres_conhecidas_menos_a_ultima
    ):
        """Varre a perturbacao e mede onde a linha deixa de ser reconhecida.

        Enquanto a linha TEM nome, ela nem chega a ser candidata; quando ela
        perde o nome, a confianca ja caiu abaixo do limiar e D-02 nao a veta. As
        duas metades se encaixam sem sobra e sem vao, e e essa juncao exata que
        faz a fronteira ser uma LINHA e nao uma zona cinzenta.
        """
        cal = tres_conhecidas_menos_a_ultima
        aprender_a_ultima_linha(tmp_path, pixels, cal)

        virada = None
        for celulas in range(0, 60, 1):
            frame = (
                virar_celulas_no_frame(pixels, cal, LINHA_QUE_SAI, celulas)
                if celulas
                else pixels
            )
            linha = observacao_de(frame, cal).linhas[LINHA_QUE_SAI]
            if linha.nome is not None:
                assert linha.confianca_do_nome >= LIMIAR_DE_CASAMENTO, (
                    f"{celulas} celulas: uma linha COM nome sempre passou do "
                    f"limiar. Achado: {linha.confianca_do_nome}"
                )
            elif virada is None:
                virada = celulas
                assert linha.confianca_do_nome < LIMIAR_DE_CASAMENTO

        assert virada is not None, (
            "a varredura tem de alcancar a fronteira; se nao alcancou, o caso "
            "nao esta medindo nada"
        )
        assert virada == CELULAS_LOGO_ABAIXO_DO_LIMIAR, (
            "a fronteira MEDIDA mudou. Isto nao e um teste a afrouxar: e o "
            f"numero que a Fase 3 vai usar. Era {CELULAS_LOGO_ABAIXO_DO_LIMIAR}, "
            f"virou {virada}"
        )

    def test_logo_ACIMA_do_limiar_a_dedupe_VALE_e_nenhuma_chave_nova_nasce(
        self, tmp_path, pixels, tres_conhecidas_menos_a_ultima
    ):
        """A metade em que a garantia do criterio 4 existe de verdade."""
        cal = tres_conhecidas_menos_a_ultima
        sessao, pasta, antes, volta, correlacao = self._cenario(
            tmp_path, pixels, cal, CELULAS_LOGO_ACIMA_DO_LIMIAR
        )

        assert correlacao >= LIMIAR_DE_CASAMENTO, correlacao
        assert correlacao == pytest.approx(0.7531, abs=1e-3), (
            "a correlacao MEDIDA logo acima da fronteira; ela vai para o "
            f"02-02-SUMMARY. Achado: {correlacao:.4f}"
        )
        assert observacao_de(volta, cal).linhas[LINHA_QUE_SAI].nome == ""

        rodar(sessao, volta, 20, inicio=10)
        assert chaves_do_acervo(pasta) == antes, (
            "a 42 celulas de drift a dedupe por correlacao ainda segura"
        )

    def test_logo_ABAIXO_do_limiar_uma_SEGUNDA_chave_NASCE_e_isso_e_ACEITO(
        self, tmp_path, pixels, tres_conhecidas_menos_a_ultima
    ):
        """O desfecho que esta fase NAO impede, afirmado com as premissas medidas.

        Ler este caso como um defeito a consertar as pressas seria o erro. Ver a
        docstring da classe: (a) e o unico furo restante, (b) ele nasce da
        metade de D-02 que nao existe, (c) fecha-lo exige um limiar que nao ha
        como calibrar, e (d) o rastro em campo e a confianca no `log.info`.
        """
        cal = tres_conhecidas_menos_a_ultima
        sessao, pasta, antes, volta, correlacao = self._cenario(
            tmp_path, pixels, cal, CELULAS_LOGO_ABAIXO_DO_LIMIAR
        )

        # (a) A correlacao caiu abaixo do limiar, e o caso MEDE o valor.
        assert correlacao < LIMIAR_DE_CASAMENTO, correlacao
        assert correlacao == pytest.approx(0.7492, abs=1e-3), (
            "a correlacao MEDIDA logo abaixo da fronteira; ela vai para o "
            f"02-02-SUMMARY. Achado: {correlacao:.4f}"
        )

        # (b) E POR ISSO ela volta a ser candidata.
        obs = observacao_de(volta, cal)
        assert obs.linhas[LINHA_QUE_SAI].nome is None
        assert obs.linhas[LINHA_QUE_SAI].confianca_do_nome < LIMIAR_DE_CASAMENTO
        assert sessao._candidatas_para_aprender(obs), (
            "com a confianca abaixo do limiar, as DUAS condicoes de "
            "candidatura sao verdadeiras e a pessoa volta para a mesa"
        )

        # (c) E uma SEGUNDA chave nasce para a MESMA pessoa.
        rodar(sessao, volta, 5, inicio=10)
        depois = chaves_do_acervo(pasta)
        novas = depois - antes

        assert len(novas) == 1, (
            "ESTE DESFECHO E CONHECIDO E ACEITO (T-02-18), e nao um defeito a "
            "consertar aqui. A mesma pessoa voltou correlacionando "
            f"{correlacao:.4f} contra a PROPRIA entrada gravada, ficou abaixo "
            "de 0.75, virou candidata e ganhou uma segunda entrada. Fechar esta "
            "porta exigiria um SEGUNDO limiar abaixo de 0.75, e nao existe "
            "medida de campo do drift do recorte entre sessoes para calibra-lo. "
            "Se este caso comecou a falhar, alguem MUDOU o comportamento: "
            f"confira o que, antes de mexer no teste. Novas: {novas}"
        )
        assert antes < depois, (
            "e a entrada antiga continua la: sao DUAS assinaturas da mesma "
            "pessoa agora, e o acervo nao tem comando de esquecer"
        )

    def test_o_par_medido_que_o_SUMMARY_registra(
        self, tmp_path, pixels, tres_conhecidas_menos_a_ultima
    ):
        """A PRIMEIRA medida do projeto sobre quanto um recorte precisa mudar
        para a dedupe falhar.

        E o numero que decide, na Fase 3 ou depois, se vale um segundo limiar. O
        caso existe para que ele seja reproduzivel por comando, com o jogo
        fechado, em vez de viver so na prosa de um SUMMARY.
        """
        cal = tres_conhecidas_menos_a_ultima
        aprender_a_ultima_linha(tmp_path, pixels, cal)

        medidas = {}
        for celulas in (
            CELULAS_LOGO_ACIMA_DO_LIMIAR,
            CELULAS_LOGO_ABAIXO_DO_LIMIAR,
        ):
            frame = virar_celulas_no_frame(pixels, cal, LINHA_QUE_SAI, celulas)
            medidas[celulas] = max(
                pontuacoes_da_linha(frame, cal, LINHA_QUE_SAI, cal.assinaturas)
            )

        acima = medidas[CELULAS_LOGO_ACIMA_DO_LIMIAR]
        abaixo = medidas[CELULAS_LOGO_ABAIXO_DO_LIMIAR]

        assert acima >= LIMIAR_DE_CASAMENTO > abaixo, medidas
        assert acima - abaixo < 0.01, (
            "as duas margens sao VIZINHAS: uma unica celula de mascara separa "
            f"a dedupe que vale da que nao vale. {medidas}"
        )
        # 2000 celulas na mascara, 60 delas de texto: a fronteira fica em ~2.15%
        # da mascara inteira. O numero exato vai para o 02-02-SUMMARY.
        mascara = assinatura_do_frame(pixels, cal, LINHA_QUE_SAI).mascara
        fracao = CELULAS_LOGO_ABAIXO_DO_LIMIAR / mascara.size
        assert fracao < 0.03, fracao


# ---------------------------------------------------------------------------
# W-01: AS TRES LIGACOES QUE SO EXISTEM EM PRODUCAO
# ---------------------------------------------------------------------------

ELO_SESSAO = "a Sessao recebe o aprendiz"
ELO_LISTA_VIVA = "o acervo entra na lista viva"
ELO_AJUSTES = "o aprendiz recebe os ajustes lidos"


def _alvo_da_chamada(no: ast.Call) -> str | None:
    return getattr(no.func, "id", None) or getattr(no.func, "attr", None)


def _nomes_ligados_a(arvore: ast.Module, construtor: str) -> set[str]:
    """Os nomes locais que recebem o resultado de `construtor(...)`."""
    ligados: set[str] = set()
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Assign) or not isinstance(no.value, ast.Call):
            continue
        if _alvo_da_chamada(no.value) != construtor:
            continue
        ligados |= {t.id for t in no.targets if isinstance(t, ast.Name)}
    return ligados


def _cita_nome_de_fora(no: ast.expr) -> bool:
    """A expressao menciona algo que nao seja o construtor de padroes.

    `ajustes_do_aprendiz or AjustesDoAprendiz()` cita; `AjustesDoAprendiz()`
    sozinho, nao. E exatamente essa a diferenca entre honrar o `[identidade]` do
    `config.toml` e descarta-lo.
    """
    nomes = {n.id for n in ast.walk(no) if isinstance(n, ast.Name)}
    return bool(nomes - {"AjustesDoAprendiz"})


def _volta_para_a_lista_viva(arvore: ast.Module, ligados: set[str]) -> bool:
    """Algum `<algo>.assinaturas = <ligado>.assinaturas` existe no modulo."""
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Assign):
            continue
        escreve = any(
            isinstance(alvo, ast.Attribute) and alvo.attr == "assinaturas"
            for alvo in no.targets
        )
        if not escreve:
            continue
        valor = no.value
        if (
            isinstance(valor, ast.Attribute)
            and valor.attr == "assinaturas"
            and isinstance(valor.value, ast.Name)
            and valor.value.id in ligados
        ):
            return True
    return False


def _elos_do_arranque(
    fonte: str, arquivo: str
) -> tuple[dict[str, list[str]], list[str]]:
    """Devolve (o que foi ACHADO por elo, as QUEIXAS) lendo a arvore sintatica.

    AST e nunca `grep`, pela mesma razao de `_modulos_do_pacote_importados`
    logo acima: as docstrings deste projeto citam `aprendiz=` e
    `cal.assinaturas` em prosa ao explicar as proprias regras, e uma busca
    textual passaria verde lendo o comentario que sobrou depois de a linha
    sumir.
    """
    arvore = ast.parse(fonte)
    achados: dict[str, list[str]] = {
        ELO_SESSAO: [],
        ELO_LISTA_VIVA: [],
        ELO_AJUSTES: [],
    }
    queixas: list[str] = []
    aprendizes = _nomes_ligados_a(arvore, "Aprendiz")

    for no in ast.walk(arvore):
        if isinstance(no, ast.Call):
            local = f"{arquivo}:{no.lineno}"
            alvo = _alvo_da_chamada(no)

            if alvo == "Sessao":
                passado = next(
                    (k.value for k in no.keywords if k.arg == "aprendiz"), None
                )
                if passado is None:
                    queixas.append(
                        f"{local}: este `Sessao(...)` nao passa `aprendiz=`, "
                        "entao o aprendizado de identidades esta DESLIGADO em "
                        "campo com a suite inteira verde"
                    )
                elif not (
                    isinstance(passado, ast.Name) and passado.id in aprendizes
                ):
                    queixas.append(
                        f"{local}: o `aprendiz=` desta `Sessao(...)` nao e um "
                        "nome vindo de um `Aprendiz(...)` deste modulo. Passar "
                        "`None` aqui desliga a feature inteira sem quebrar "
                        "teste nenhum, e foi isso que a mutacao M19 provou"
                    )
                else:
                    achados[ELO_SESSAO].append(local)

            elif alvo == "Aprendiz":
                ajustes: ast.expr | None = no.args[1] if len(no.args) >= 2 else None
                ajustes = next(
                    (k.value for k in no.keywords if k.arg == "ajustes"), ajustes
                )
                if ajustes is None:
                    queixas.append(
                        f"{local}: este `Aprendiz(...)` nao recebe ajustes, "
                        "entao a secao `[identidade]` do config.toml nao chega "
                        "nele e o usuario ajusta um numero que nao e lido"
                    )
                elif not _cita_nome_de_fora(ajustes):
                    queixas.append(
                        f"{local}: este `Aprendiz(...)` constroi os proprios "
                        "ajustes no lugar, entao o que veio do config.toml foi "
                        "descartado em silencio (mutacao M18)"
                    )
                else:
                    achados[ELO_AJUSTES].append(local)

        elif isinstance(no, ast.Assign) and isinstance(no.value, ast.Call):
            if _alvo_da_chamada(no.value) != "carregar_identidades":
                continue
            local = f"{arquivo}:{no.lineno}"
            ligados = {t.id for t in no.targets if isinstance(t, ast.Name)}
            if ligados and _volta_para_a_lista_viva(arvore, ligados):
                achados[ELO_LISTA_VIVA].append(local)
            else:
                queixas.append(
                    f"{local}: `carregar_identidades(...)` e chamado e o "
                    "resultado NUNCA volta para `.assinaturas`. O acervo em "
                    "disco fica fora da lista viva, e tudo que o scanner "
                    "aprendeu sozinho para de ser reconhecido no arranque "
                    "seguinte (mutacao M21)"
                )

    return achados, queixas


def _elos_em_producao() -> tuple[dict[str, list[str]], list[str]]:
    achados: dict[str, list[str]] = {
        ELO_SESSAO: [],
        ELO_LISTA_VIVA: [],
        ELO_AJUSTES: [],
    }
    queixas: list[str] = []
    for caminho in sorted((RAIZ / "l2scanner").glob("*.py")):
        parcial, reclamou = _elos_do_arranque(
            caminho.read_text(encoding="utf-8"), caminho.name
        )
        for elo, locais in parcial.items():
            achados[elo].extend(locais)
        queixas.extend(reclamou)
    return achados, queixas


# O fonte fabricado que CUMPRE as tres regras, escrito no formato do
# `laco_principal` real. As tres mutacoes plantadas mais abaixo sao os MESMOS
# tres cortes que a verificacao da Fase 2 rodou contra o `__main__.py`, e e por
# isso que eles moram aqui em vez de virarem prosa num relatorio.
FONTE_QUE_CUMPRE = """
def laco_principal(args, cal, ajustes_do_aprendiz=None):
    acervo = AcervoDeIdentidades(PASTA_IDENTIDADES)
    identidades = carregar_identidades(list(cal.assinaturas), acervo)
    cal.assinaturas = identidades.assinaturas
    aprendiz = Aprendiz(acervo, ajustes_do_aprendiz or AjustesDoAprendiz())
    sessao = Sessao(cal=cal, rastreador=rastreador, aprendiz=aprendiz)
    return sessao
"""


class TestNenhumaLigacaoDoAprendizSomeEmSilencio:
    """Tres linhas de `__main__.py` que a suite inteira nao defendia.

    A Fase 1 pagou por um defeito de FORMA, e nao de logica: `Rastreador` nascia
    com `assinaturas_configuradas` no default, oito testes atribuiam o valor
    certo, e o unico construtor de producao nao passava o argumento. A garantia
    estava provada na suite e DESLIGADA no jogo. A guarda que nasceu dessa licao
    e `tests/test_acervo.py::TestNenhumRastreadorNasceMudo`, e esta classe e o
    molde dela aplicado ao aprendiz.

    A Fase 2 repetiu a forma. A verificacao rodou tres mutacoes no fonte de
    producao contra os 3514 casos, e as tres sobreviveram com 0 falhas:

        `aprendiz=aprendiz` -> `aprendiz=None`            (M19, W-01a)
        `cal.assinaturas = identidades.assinaturas` sai   (M21, W-01b)
        `ajustes_do_aprendiz or AjustesDoAprendiz()`
            -> `AjustesDoAprendiz()`                      (M18, W-01c)

    A primeira desliga a feature INTEIRA em campo. A segunda faz o scanner
    esquecer, a cada arranque, tudo que aprendeu sozinho. A terceira descarta o
    `[identidade]` que o usuario editou a mao.

    POR QUE UM PORTAO SOBRE O FONTE, E NAO UM CAMINHO DE EXECUCAO. O defeito
    aqui nao e um comportamento errado: e ESQUECER de ligar. O que precisa ficar
    nao-mesclavel e o esquecimento, e o esquecimento so e observavel na forma do
    fonte. Um teste de execucao teria de atravessar `laco_principal`, que
    constroi a fonte de captura e entra num laco infinito com tela viva; o unico
    caminho de execucao que ja existe (`main()` chamada de verdade, em
    `TestARecusaAcontecENoARRANQUE`) para ANTES dele com o jogo fechado, por
    construcao e de proposito. O caso
    `test_o_laco_real_ESCREVE_no_acervo_e_escreve_uma_vez_so` monta a `Sessao` a
    mao, e por isso nao viu nenhuma das tres mutacoes.

    O portao NAO conserta os defaults. Tornar `aprendiz` obrigatorio na `Sessao`
    quebraria casos que passam, e esta correcao nao reescreve teste verde. Quem
    quiser uma `Sessao` sem aprendiz continua podendo, em teste; o que nao pode
    e um `Sessao(...)` de PRODUCAO nascer sem ele por esquecimento.
    """

    def test_as_tres_ligacoes_estao_no_fonte_de_producao(self):
        _, queixas = _elos_em_producao()
        assert not queixas, "\n".join(queixas)

    def test_o_portao_nao_passa_por_vacuidade(self):
        """Um portao que nao acha nada passa sem provar nada.

        Mesma assercao, pela mesma razao, de
        `TestNenhumRastreadorNasceMudo::test_o_portao_nao_passa_por_vacuidade`.
        Se `laco_principal` for renomeado, movido para outro pacote, ou o
        detector olhar para a pasta errada, e AQUI que aparece, em vez de os
        tres elos ficarem verdes por ausencia.
        """
        achados, _ = _elos_em_producao()
        vazios = [elo for elo, locais in achados.items() if not locais]
        assert not vazios, (
            "o detector nao encontrou NENHUMA ocorrencia destes elos em "
            f"l2scanner/: {vazios}. O portao esta olhando para o lugar errado"
        )

    def test_o_detector_nao_acusa_o_fonte_que_cumpre(self):
        """A outra metade: quem cumpriu a regra nao pode ser acusado."""
        achados, queixas = _elos_do_arranque(FONTE_QUE_CUMPRE, "<fabricado>")
        assert queixas == []
        assert all(achados.values()), achados

    def test_o_detector_acusa_o_aprendiz_arrancado_da_sessao(self):
        """M19 plantada: a feature inteira desligada em campo."""
        envenenado = FONTE_QUE_CUMPRE.replace("aprendiz=aprendiz", "aprendiz=None")
        assert envenenado != FONTE_QUE_CUMPRE, "a mutacao plantada nao pegou"
        achados, queixas = _elos_do_arranque(envenenado, "<fabricado>")
        assert queixas, "o detector nao acusaria um `Sessao(aprendiz=None)`"
        assert achados[ELO_SESSAO] == []

    def test_o_detector_acusa_o_acervo_fora_da_lista_viva(self):
        """M21 plantada: o scanner esquece o que aprendeu, a cada arranque."""
        envenenado = FONTE_QUE_CUMPRE.replace(
            "    cal.assinaturas = identidades.assinaturas\n", ""
        )
        assert envenenado != FONTE_QUE_CUMPRE, "a mutacao plantada nao pegou"
        achados, queixas = _elos_do_arranque(envenenado, "<fabricado>")
        assert queixas, (
            "o detector nao acusaria um `carregar_identidades(...)` cujo "
            "resultado nunca volta para a lista viva"
        )
        assert achados[ELO_LISTA_VIVA] == []

    def test_o_detector_acusa_os_ajustes_do_config_descartados(self):
        """M18 plantada: o `[identidade]` editado pelo usuario nao chega."""
        envenenado = FONTE_QUE_CUMPRE.replace(
            "ajustes_do_aprendiz or AjustesDoAprendiz()", "AjustesDoAprendiz()"
        )
        assert envenenado != FONTE_QUE_CUMPRE, "a mutacao plantada nao pegou"
        achados, queixas = _elos_do_arranque(envenenado, "<fabricado>")
        assert queixas, (
            "o detector nao acusaria um `Aprendiz(...)` que constroi os "
            "proprios ajustes e descarta o que veio de fora"
        )
        assert achados[ELO_AJUSTES] == []

    def test_o_detector_acusa_uma_Sessao_sem_o_argumento(self):
        """A porta que fica aberta depois de a linha ser apagada INTEIRA.

        Apagar `aprendiz=aprendiz` e diferente de troca-lo por `None`: o
        argumento simplesmente deixa de existir e o default da `Sessao` assume.
        Sem esta metade o portao pegaria a mutacao da verificacao e deixaria
        passar a versao mais provavel num diff de verdade.
        """
        envenenado = FONTE_QUE_CUMPRE.replace(", aprendiz=aprendiz", "")
        assert envenenado != FONTE_QUE_CUMPRE, "a mutacao plantada nao pegou"
        _, queixas = _elos_do_arranque(envenenado, "<fabricado>")
        assert queixas, "o detector nao acusaria uma `Sessao(...)` sem `aprendiz=`"


# ---------------------------------------------------------------------------
# W-02: O NUMERO DE LEITURAS, E POR QUE ELE NAO E 1
# ---------------------------------------------------------------------------


class TestOCincoLeiturasEstaPreso:
    """`LEITURAS_PARA_APRENDER = 5` e a unica defesa contra gravar lixo.

    O acervo e IRREVERSIVEL: `AcervoDeIdentidades` grava e le, e nao existe
    comando de esquecer. Uma entrada errada nao e um erro que o proximo tick
    conserta; e uma pessoa que passa a NAO ser mais reconhecida, porque o
    quase-duplicado sombreia a entrada boa pela margem e as duas caem no
    silencio.

    Todos os casos desta suite passavam `leituras_para_aprender=` explicito, e
    por isso trocar o default por 1 deixava os 3514 verdes (W-02). Com 1 o
    scanner gravaria na SEGUNDA leitura: cerca de 2 segundos a 1 Hz, dentro do
    tempo em que um icone de buff, uma janela arrastada ou o inventario passando
    por cima ainda estao parados no mesmo lugar. A estabilidade deixaria de ser
    prova de coisa nenhuma.

    O NUMERO NAO FOI ESCOLHIDO, FOI DERIVADO, e e por isso que esta classe
    prende a derivacao e nao so o literal. `rastreador.Ajustes` tem duas
    familias de confirmacao: as direcoes BARATAS de reverter custam 3 leituras
    (morte, entrada) e as CARAS custam 5 (ressurreicao, saida). Gravar num
    acervo sem desfazer e a direcao cara por definicao, entao paga o preco da
    familia cara. Se um dia a familia cara mudar, este caso cobra a mudanca dos
    dois lados juntos em vez de deixar os dois numeros divergirem calados.
    """

    def test_o_numero_e_o_da_familia_CARA_do_rastreador(self):
        padroes = Ajustes()
        assert LEITURAS_PARA_APRENDER == padroes.confirmacoes_para_ressurreicao, (
            "o aprendizado deixou de custar o mesmo que a familia CARA do "
            "rastreador. Se a mudanca foi deliberada, mude os dois lados e "
            "reescreva a derivacao na docstring de LEITURAS_PARA_APRENDER"
        )
        assert LEITURAS_PARA_APRENDER == padroes.confirmacoes_para_saida
        assert LEITURAS_PARA_APRENDER > padroes.confirmacoes_para_morte, (
            "gravar num acervo sem desfazer nao pode custar menos do que "
            "anunciar uma morte, que o proximo tick desmente de graca"
        )
        assert LEITURAS_PARA_APRENDER == 5

    def test_o_default_do_dataclass_e_o_mesmo_numero(self):
        """Um segundo literal aqui reabriria a porta pelo outro lado."""
        assert AjustesDoAprendiz().leituras_para_aprender == LEITURAS_PARA_APRENDER

    def test_com_o_default_quatro_leituras_ainda_nao_gravam(
        self, tmp_path, pixels, tres_conhecidas
    ):
        """O caso que a suite nao tinha: NENHUM ajuste explicito.

        Os irmaos de `TestAFatiaInteira` passam `leituras_para_aprender=5` a
        mao, entao provam o MECANISMO e nao o NUMERO. Este roda o que o usuario
        roda quando nao escreve nada no `config.toml`, e cai se o default virar
        1, 2, 3 ou 4.
        """
        aprendiz, pasta = montar_aprendiz(tmp_path)
        sessao = montar_sessao(tres_conhecidas, tmp_path, aprendiz=aprendiz)

        rodar(sessao, pixels, 4)

        assert assinaturas_gravadas(pasta) == [], (
            "com o default, quatro leituras nao podem gravar. Se este caso "
            "caiu, o default baixou e o scanner passou a gravar num acervo "
            "irreversivel antes de a leitura estar provada estavel"
        )

    def test_com_o_default_a_quinta_leitura_grava(
        self, tmp_path, pixels, tres_conhecidas
    ):
        """A outra metade: o default nao pode ser alto demais para gravar.

        Sozinho, o caso das quatro leituras seria satisfeito por um default de
        mil, que quebra a feature pelo lado oposto e tambem em silencio.
        """
        aprendiz, pasta = montar_aprendiz(tmp_path)
        sessao = montar_sessao(tres_conhecidas, tmp_path, aprendiz=aprendiz)

        resultado = rodar(sessao, pixels, 5)

        assert len(assinaturas_gravadas(pasta)) == 1
        assert len(resultado.aprendizados) == 1
