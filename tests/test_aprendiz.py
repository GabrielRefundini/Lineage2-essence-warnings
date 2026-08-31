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
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
import pytest

import l2scanner.rastreador
from l2scanner.acervo import AcervoDeIdentidades
from l2scanner.agenda import AgendaInvalida, RegistroEmDisco
from l2scanner.aprendiz import (
    LEITURAS_PARA_APRENDER,
    TETO_DE_CELULAS_TOLERADAS,
    AjustesDoAprendiz,
    Aprendiz,
    Candidata,
    ToleranciaAlemDoTeto,
    distancia_de_hamming,
)
from l2scanner.config import ler_ajustes_do_aprendiz
from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.identidade import (
    PIXELS_MINIMOS_DE_TEXTO,
    Assinatura,
    criar_assinatura,
    mascara_de_texto,
)
from l2scanner.rastreador import Ajustes, Rastreador, TipoDeEvento
from l2scanner.sessao import ResultadoDoTick, Sessao
from l2scanner.visao import EstadoDaLinha, LeituraDeLinha, Observacao, _recorte_do_nome, extrair

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
    """Uma `Sessao` de verdade, com o disco inteiro preso a `tmp_path`."""
    rastreador = Rastreador(
        nomes=list(cal.nomes),
        assinaturas_configuradas=configuradas,
        ajustes=ajustes or Ajustes(confirmacoes_para_morte=2),
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


# ---------------------------------------------------------------------------
# O TETO QUE VEM DA MEDIDA, E A TOLERANCIA QUE O USUARIO CONSEGUE MEXER (D-06)
# ---------------------------------------------------------------------------


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
        fonte = (RAIZ / "l2scanner" / "aprendiz.py").read_text(encoding="utf-8")
        bloco = fonte[fonte.index("TETO_DE_CELULAS_TOLERADAS") :][:4000]

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
        fonte = (RAIZ / "l2scanner" / "aprendiz.py").read_text(encoding="utf-8")
        bloco = fonte[fonte.index("TETO_DE_CELULAS_TOLERADAS") :][:4000].lower()

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
        onde coloca-lo."""
        texto = (RAIZ / "config.toml").read_text(encoding="utf-8")
        bloco = texto[texto.index("[identidade]") :][:2000]
        assert "scanner.log" in bloco
        assert str(TETO_DE_CELULAS_TOLERADAS) in bloco, (
            "o teto e a razao dele cabem em uma linha"
        )

    def test_o_config_de_verdade_continua_lendo_os_defaults(self):
        """O `config.toml` versionado tem a secao COMENTADA, entao ela nao muda
        nada para quem nunca a preencheu."""
        assert ler_ajustes_do_aprendiz(RAIZ / "config.toml") == AjustesDoAprendiz()
