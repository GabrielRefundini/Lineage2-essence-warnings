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
from l2scanner.agenda import RegistroEmDisco
from l2scanner.aprendiz import (
    AjustesDoAprendiz,
    Aprendiz,
    Candidata,
    distancia_de_hamming,
)
from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.identidade import (
    PIXELS_MINIMOS_DE_TEXTO,
    Assinatura,
    criar_assinatura,
    mascara_de_texto,
)
from l2scanner.rastreador import Ajustes, Rastreador, TipoDeEvento
from l2scanner.sessao import Sessao
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
        antes = None
        for i in range(6):
            antes = sessao.tick(
                Frame(pixels=morto, indice=100 + i, saude=SaudeDoFrame.OK),
                momento=1_700_000_100 + i,
            )
        mortes_antes = [
            e.membro for e in antes.eventos if e.tipo is TipoDeEvento.MORREU
        ]
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
