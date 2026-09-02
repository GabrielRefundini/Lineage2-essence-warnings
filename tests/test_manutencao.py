"""O aviso de manutencao do servidor: ler o banner e sobreviver a cegueira.

Este arquivo existe por causa de uma cegueira de 90 s e outra de 5 min em
2026-08-24. A causa era o servidor caindo para manutencao, e a Fase 5 aprendeu
a reconhecer o servidor DEPOIS da queda. Mas o jogo ANUNCIA a queda com 40
minutos de antecedencia, em texto, na tela — e o scanner atravessava esse
anuncio inteiro sem ver.

DISCIPLINA DESTE ARQUIVO: nenhum teste pode depender de uma leitura de OCR bem
sucedida. O Python que roda a suite NAO tem as bindings do WinRT (so o `.venv`
do usuario tem), entao o caminho "sem OCR" e o caminho PADRAO daqui. Todo teste
que precisa de texto INJETA um `ler_texto` falso — que e exatamente por que
`VigiaDeManutencao` recebe `ler_texto` por parametro.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from l2scanner.agenda import RegistroEmDisco
from l2scanner.manutencao import (
    TipoDeAvisoDeManutencao,
    chave_do_marcador,
    descrever_duracao,
    eh_banner_de_manutencao,
    interpretar_banner,
)

# OS TEXTOS ABAIXO SAO SAIDA MEDIDA DO MOTOR DE OCR, NAO TEXTO INVENTADO.
#
# Todos vieram da fonte REAL do jogo — a fixture
# `tests/fixtures/manutencao/banner_40min26s.png` (360x135) e o screenshot
# inteiro de onde ela foi recortada. Verdade na tela: 40 minutos e 26 segundos.
#
#   BANNER_REAL       — as passadas em cinza que ACERTAM (2x, 3x, 4x)
#   TEXTO_EMBARALHADO — a imagem em COR, sem converter para cinza
#   TEXTO_GRUDADO     — uma passada em cinza que comeu o espaco da unidade
#
# UMA HONESTIDADE SOBRE A PROVENIENCIA: qual escala produz qual texto MUDOU
# entre duas medicoes honestas — a primeira feita na imagem inteira com
# pre-processamento manual, a segunda na fixture recortada com o codigo de
# hoje. O modulo `ocr` carrega a tabela e a refutacao. Aqui isso nao importa: o
# que estes tres textos guardam sao as FORMAS de embaralhamento que o motor
# produz de verdade, e o parser tem que dar conta delas venham de onde vierem.
#
# Estes tres sao a regressao PERMANENTE do parser: rodam sem OCR nenhum, no
# Python da suite, e por isso valem em qualquer maquina.
BANNER_REAL = "Server Maintence 40 minutes 26 seconds Please avoid entering instance"

# O BUG. Em cor, o motor comeu o `40 minutes` inteiro e sobrou `__40nin? es`.
# O parser antigo nao achava minuto nenhum, achava `26 seconds` e devolvia 26
# segundos com cara de resposta boa — quando faltavam 40 minutos e 26 segundos.
TEXTO_EMBARALHADO = (
    "12 Server Maintence __40nin? es 26 seconds "
    "Please avoid entering instance Korzis O' Kaus"
)

# Cinza: a unidade sobreviveu, mas grudada no numero e com `m` virando `n`.
# Medido de novo em 6x, entao nao e artefato de uma escala so — e a forma que
# D-c existe para recuperar.
TEXTO_GRUDADO = (
    "12 Server Maintence 40ninutes 26 seconds "
    "Please avoid entering instance ( 3>YKorzis"
)

# O caso bom — e o alvo do que a conversao para cinza (D-a) entrega. E o que as
# duas escalas de producao (2x e 3x) leem na fixture real.
TEXTO_LIMPO = (
    "12 Server Maintence 40 minutes 26 seconds "
    "Please avoid entering instance Korzis O' Kaus"
)

# AS OITO LEITURAS DE 2026-08-31: A PRIMEIRA MEDICAO CONTRA UM BANNER DE VERDADE
# ==============================================================================
#
# Tudo que estava acima veio de UMA fixture recortada de um screenshot. Estas
# oito vieram do jogo, com o servidor entrando em manutencao as ~18:20 e o
# banner na tela por quase uma hora. O scanner NAO anunciou nada, e a docstring
# do modulo ja avisava por que isso podia acontecer: "OCR na FONTE DO JOGO nunca
# foi provada".
#
# Sao QUATRO RODADAS de `--testar-manutencao --janela`, cada uma com as duas
# escalas de producao lendo os MESMOS pixels. Os recortes estao em
# `logs/banner-manutencao-1759{08,54}.png` e `-1816{08,10}.png`. A faixa ja e a
# corrigida (`banner_manutencao` = (0,110) 735x325); a derivada da party window
# pegava so a ultima linha.
#
# O QUE ELAS PROVAM, e cada numero abaixo esta cobrado por um teste:
#
#   1. O `M` de Maintence NUNCA sobrevive. Sai `aintence`, sai `aiptence`, ou a
#      palavra some inteira. Em 8 de 8 a raiz exata `mainten` esta AUSENTE.
#   2. `avoid entering instance` aparece em 8 de 8, limpo em 7.
#   3. A escala 2x acertou o tempo em 1 de 4 rodadas; a 3x em 4 de 4. As tres
#      falhas da 2x foram ABSTENCAO (`minutes` saiu com vogal trocada, e a
#      guarda estrutural calou), NUNCA um numero errado.
#
# Sao texto: rodam sem OCR, sem jogo e sem rede, no Python da suite.
CAMPO_1_2X = (
    "11 Servergqaiptenceatl JJ »20 minåtes 27 seconds "
    "4—vvaÅZidentering instance Welazkez Mostarda"
)
CAMPO_1_3X = (
    "11 Server 20 minutes 27 seconds "
    "Please avoid entering instance Welazkez Mostarda"
)
CAMPO_2_2X = (
    "13 04 minütes 13 seconds "
    "Please avoid entering instance Welazkez Mosta rda"
)
CAMPO_2_3X = (
    "13 04 minutes 13 seconds "
    "Please avoid entering instance Welazkez Mostarda"
)
CAMPO_3_2X = (
    "13 04 minutes 12 seconds "
    "Please avoid entering instance Welazkez Mostarda"
)
CAMPO_3_3X = (
    "13 Server \"aintencea2J 04 minutes 12 seconds "
    "Please avoid entering instance Welazkez Mostarda"
)
CAMPO_4_2X = (
    "13 04 minåtes 11 seconds "
    "'Please avoid entering instance Welazkez Mosta rda Farcran"
)
CAMPO_4_3X = (
    "13 Server \"aintencea,QJ 04 minutes 11 seconds "
    "Please avoid entering instance Welazkez Mostarda Farcran"
)

# (rotulo, texto, duracao que `interpretar_banner` tem que devolver)
CAMPO_31_08 = [
    ("rodada 1 / 2x", CAMPO_1_2X, None),
    ("rodada 1 / 3x", CAMPO_1_3X, timedelta(minutes=20, seconds=27)),
    ("rodada 2 / 2x", CAMPO_2_2X, None),
    ("rodada 2 / 3x", CAMPO_2_3X, timedelta(minutes=4, seconds=13)),
    ("rodada 3 / 2x", CAMPO_3_2X, timedelta(minutes=4, seconds=12)),
    ("rodada 3 / 3x", CAMPO_3_3X, timedelta(minutes=4, seconds=12)),
    ("rodada 4 / 2x", CAMPO_4_2X, None),
    ("rodada 4 / 3x", CAMPO_4_3X, timedelta(minutes=4, seconds=11)),
]

HOJE = datetime(2026, 8, 25, 14, 0, 0)

# O EPISODIO DE CAMPO DE 2026-09-02 — O SPAM, MEDIDO NO PRINT DO GRUPO.
#
# Entre 11:58 e 12:52 o grupo recebeu ~19 vezes a MESMA mensagem de anuncio
# ("MANUTENCAO DO SERVIDOR em X (as HH:MM). Nao entre em instance."), para UMA
# unica manutencao, mais 3 mensagens do segundo tipo (12:11, 12:41 e 12:52).
#
# Estes sao os 17 horarios-alvo que as mensagens de anuncio carregaram, na
# ordem em que chegaram. Eles se espalham de 12:11 a 13:05 — 54 minutos de
# desacordo sobre QUANDO o servidor cai, para uma manutencao so:
HORARIOS_ALVO_DO_CAMPO = (
    (12, 59),
    (12, 56),
    (12, 59),
    (13, 5),
    (12, 18),
    (12, 11),
    (12, 26),
    (12, 29),
    (12, 30),
    (12, 34),
    (12, 35),
    (12, 37),
    (12, 38),
    (12, 40),
    (13, 5),
    (12, 43),
    (12, 56),
)

# A janela do episodio: 11:58 (a primeira mensagem) ate 12:52 (a ultima).
INICIO_DO_CAMPO = datetime(2026, 9, 2, 11, 58, 0)
DURACAO_DO_CAMPO = timedelta(minutes=54)

# Cada alvo e lido DUAS cadencias seguidas, 5 s uma da outra. NAO e conveniencia
# de teste: em campo a leitura seguinte repetia o MESMO erro sistematico de OCR,
# entao as duas caiam dentro dos 60 s de `TOLERANCIA_DO_CONSENSO` UMA DA OUTRA —
# e e exatamente essa concordancia que abre a porta da REMARCACAO em
# `_registrar`. O consenso TEMPORAL e cego a erro de METODO por construcao, e
# isso ja esta escrito por extenso na docstring de `VigiaDeManutencao`.
SEGUNDOS_DE_LEITURA_POR_ALVO = 10

# 150 s entre alvos, e o numero nao e livre: a partir de 156 s a leitura do
# sexto alvo (12:11) cairia DEPOIS de 12:11 e pediria uma duracao negativa, que
# o banner do jogo nunca mostra. 17 alvos x 150 s = 42:30 de leituras dentro dos
# 54 minutos do episodio; os 11:30 finais o vigia atravessa CEGO, como em campo.
SEGUNDOS_ENTRE_ALVOS_DO_CAMPO = 150


def banner_dizendo(duracao: timedelta) -> str:
    """O banner do jogo anunciando `duracao`, na forma que o OCR entrega limpa."""
    minutos, segundos = divmod(int(duracao.total_seconds()), 60)
    return f"Server Maintence {minutos} minutes {segundos} seconds"


def texto_do_campo(agora: datetime) -> str | None:
    """O que o OCR devolve em `agora` durante o replay de 02/09, ou None.

    A duracao e sempre `alvo - agora` NO INSTANTE DA LEITURA: e assim que as
    duas leituras de um mesmo alvo implicam o MESMO momento e batem entre si.

    Fora das janelas de leitura nao ha leitura nenhuma — e e ai que a ANCORA tem
    de segurar sozinha, que e a razao de ela existir (D-10).
    """
    decorrido = int((agora - INICIO_DO_CAMPO).total_seconds())
    if decorrido < 0:
        return None
    indice, dentro_da_janela = divmod(decorrido, SEGUNDOS_ENTRE_ALVOS_DO_CAMPO)
    if indice >= len(HORARIOS_ALVO_DO_CAMPO):
        return None
    if dentro_da_janela >= SEGUNDOS_DE_LEITURA_POR_ALVO:
        return None
    hora, minuto = HORARIOS_ALVO_DO_CAMPO[indice]
    alvo = INICIO_DO_CAMPO.replace(hour=hora, minute=minuto, second=0)
    return banner_dizendo(alvo - agora)


def pixels():
    """Um recorte qualquer. O conteudo nao importa: o `ler_texto` e injetado."""
    return np.zeros((10, 10, 3), dtype=np.uint8)


class TestLeituraDoBanner:
    def test_o_banner_real_do_jogo_e_reconhecido_e_interpretado(self):
        assert eh_banner_de_manutencao(BANNER_REAL) is True
        assert interpretar_banner(BANNER_REAL) == timedelta(minutes=40, seconds=26)

    def test_o_texto_real_embaralhado_devolve_none_e_nao_26_segundos(self):
        """O BUG, nominalmente. Este teste e a razao inteira desta tarefa (D-b).

        Medido contra `banner_40min26s.png` lida em COR: o motor devolveu
        `__40nin? es 26 seconds`, e o parser antigo — que so procurava numero
        colado em unidade — nao achava minuto nenhum, achava os segundos e
        devolvia 26 segundos. Plausivel, silencioso e errado por 40 minutos.

        A assercao contra `timedelta(seconds=26)` esta escrita a parte de
        proposito: e o valor exato que o produto anunciaria, e um dia alguem vai
        "simplificar" a guarda e precisa ver este nome de teste falhar.
        """
        assert eh_banner_de_manutencao(TEXTO_EMBARALHADO) is True
        assert interpretar_banner(TEXTO_EMBARALHADO) is None
        assert interpretar_banner(TEXTO_EMBARALHADO) != timedelta(seconds=26)

    def test_o_texto_real_grudado_devolve_os_40_minutos(self):
        """Cinza 2x: `40ninutes`. O `m` virou `n` E o espaco sumiu (D-c).

        D-c e D-b sao complementares, nao alternativos: aqui a unidade AINDA
        carrega o numero, entao recuperar a leitura e melhor do que calar.
        """
        assert eh_banner_de_manutencao(TEXTO_GRUDADO) is True
        assert interpretar_banner(TEXTO_GRUDADO) == timedelta(minutes=40, seconds=26)

    def test_o_texto_real_limpo_devolve_os_40_minutos(self):
        assert eh_banner_de_manutencao(TEXTO_LIMPO) is True
        assert interpretar_banner(TEXTO_LIMPO) == timedelta(minutes=40, seconds=26)

    @pytest.mark.parametrize(
        "texto",
        [
            "Server Maintence nin es 26 seconds",
            "Server Maintence __40nin? es 26 seconds",
            "Server Maintence minutes 26 seconds",
        ],
    )
    def test_unidade_de_minutos_sem_numero_cala_a_leitura(self, texto):
        """A guarda estrutural de D-b, isolada das formas que a disparam.

        `is None`, e nunca "um numero pequeno": cair para "entao e so os
        segundos" foi EXATAMENTE como 40min26s virou 26s. Perder a leitura
        custa 5 segundos, uma cadencia; anunciar manutencao iminente sem motivo
        custa a farm da party inteira.
        """
        assert interpretar_banner(texto) is None

    def test_a_guarda_nao_e_uma_rede_que_pega_tudo(self):
        """Banner sem parte de minutos NENHUMA segue valendo.

        Sem este teste a guarda poderia virar "na duvida devolve None", que
        desliga o recurso sem ninguem perceber.
        """
        assert interpretar_banner("SERVER MAINTENCE 26 SECONDS") == timedelta(
            seconds=26
        )

    def test_a_grafia_correta_tambem_vale(self):
        """O jogo escreve `Maintence`; a grafia certa e `Maintenance`.

        Aceitar so uma seria apostar que o jogo nunca corrige o proprio typo.
        """
        texto = "Server Maintenance 5 minutes"
        assert eh_banner_de_manutencao(texto) is True
        assert interpretar_banner(texto) == timedelta(minutes=5)

    def test_caixa_e_espaco_nao_importam(self):
        texto = "  SERVER   MAINTENCE   26 SECONDS "
        assert eh_banner_de_manutencao(texto) is True
        assert interpretar_banner(texto) == timedelta(seconds=26)

    def test_as_confusoes_de_ocr_viram_digito(self):
        """`4O` -> 40 e `2l` -> 21: o OCR troca O/0, l/1 e S/5 o tempo todo."""
        texto = "Server Maintence 4O minutes 2l seconds"
        assert interpretar_banner(texto) == timedelta(minutes=40, seconds=21)

    def test_a_normalizacao_nao_atropela_a_lingua(self):
        """A palavra `seconds` sai INTACTA — e um token sem digito nao vira numero.

        Normalizar o texto inteiro era o caminho obvio e ERRADO: ele trocaria o
        `s` e o `o` de `seconds` por `5` e `0`, quebrando justamente a palavra
        que da sentido ao numero. E um `SO` solto viraria `50`, deixando
        qualquer palavra da tela virar duracao.
        """
        assert interpretar_banner("Server Maintenance 5 seconds") == timedelta(
            seconds=5
        )
        assert interpretar_banner("Server Maintenance SO seconds") is None

    def test_a_forma_com_horas_se_aparecer(self):
        assert interpretar_banner("Server Maintence 1 hour 5 minutes") == timedelta(
            hours=1, minutes=5
        )

    @pytest.mark.parametrize(
        "texto",
        [
            # O TESTE MAIS IMPORTANTE DO ARQUIVO. Frase REAL dos prints do
            # usuario: contem `server`, `restart` E `minutes`, e mesmo assim
            # NAO e o banner de manutencao. Um parser frouxo anunciaria uma
            # manutencao a cada vez que alguem tentasse usar um item.
            "You cannot use this item because the server will restart in a few minutes",
            "Please avoid entering instance",
            "Korzis 40 minutes",
            "",
            None,
        ],
    )
    def test_texto_que_nao_e_o_banner_nao_vira_nada(self, texto):
        assert eh_banner_de_manutencao(texto) is False

    def test_descrever_duracao_diz_o_tempo_como_esta_na_tela(self):
        """GOAL-01 pede o tempo COMO ESTA NA TELA — entao nao arredonda."""
        assert descrever_duracao(timedelta(minutes=40, seconds=26)) == (
            "40 minutos e 26 segundos"
        )
        assert descrever_duracao(timedelta(minutes=5)) == "5 minutos"
        assert descrever_duracao(timedelta(seconds=26)) == "26 segundos"
        assert "1 hora" in descrever_duracao(timedelta(hours=1, minutes=5))


class TestChaveDoMarcador:
    def test_a_chave_comeca_com_a_data_e_sobrevive_ao_podar(self, tmp_path):
        """Sem o prefixo de data o `podar()` PULA o arquivo e a pasta cresce.

        O `podar` faz `date.fromisoformat(nome.split("_", 1)[0])` e da
        `continue` quando levanta. Um marcador sem data na frente nunca seria
        apagado — o defeito silencioso que D-09 manda evitar.
        """
        registro = RegistroEmDisco(tmp_path)
        velho = chave_do_marcador(
            HOJE - timedelta(days=4), TipoDeAvisoDeManutencao.ANUNCIADA
        )
        registro.marcar(velho)
        registro.podar(hoje=HOJE.date())
        assert not (tmp_path / velho).exists()

        novo = chave_do_marcador(HOJE, TipoDeAvisoDeManutencao.ANUNCIADA)
        registro.marcar(novo)
        registro.podar(hoje=HOJE.date())
        assert (tmp_path / novo).exists()

    def test_a_chave_sai_do_momento_da_manutencao_nao_do_aviso(self):
        """E o que faz as DUAS instancias do usuario convergirem na mesma chave."""
        a = chave_do_marcador(HOJE, TipoDeAvisoDeManutencao.ANUNCIADA)
        b = chave_do_marcador(HOJE, TipoDeAvisoDeManutencao.ANUNCIADA)
        assert a == b

        do_segundo_aviso = chave_do_marcador(HOJE, TipoDeAvisoDeManutencao.ANTES)
        assert do_segundo_aviso != a


# Sentinela do ESPELHO. Nao pode ser None nem "": os dois sao textos legitimos
# de conferencia (None = o motor nao leu nada), e usa-los como "nao configurado"
# tornaria impossivel testar a discordancia contra um None.
_ESPELHO = object()


class LeitorFalso:
    """As DUAS leitoras injetaveis: conta chamadas e deixa trocar o texto no meio.

    O Python que roda a suite nao tem as bindings do WinRT, entao esta e a
    UNICA forma de exercitar o caminho COM texto. Trocar o texto no meio e o
    que permite simular o banner sumindo da tela.

    A conferencia ESPELHA `texto` por padrao (D-d). E a escolha que mantem
    todos os testes de consenso TEMPORAL que ja existiam exercitando exatamente
    o que exercitavam — duas escalas que concordam trivialmente. So os testes
    novos apontam as duas para lados diferentes.

    `chamadas` conta SO a passada barata. Se ela passasse a somar as duas,
    `TestCadencia` mediria outra coisa sem ninguem perceber.
    """

    def __init__(self, texto: str | None = None) -> None:
        self.texto = texto
        self._conferencia = _ESPELHO
        self.chamadas = 0
        self.chamadas_de_conferencia = 0

    @property
    def texto_de_conferencia(self):
        if self._conferencia is _ESPELHO:
            return self.texto
        return self._conferencia

    @texto_de_conferencia.setter
    def texto_de_conferencia(self, valor) -> None:
        self._conferencia = valor

    def __call__(self, _pixels):
        self.chamadas += 1
        return self.texto

    def conferir(self, _pixels):
        self.chamadas_de_conferencia += 1
        return self.texto_de_conferencia


class PixelsFalsos:
    """O `obter_pixels` chamavel — passar um CHAMAVEL e o que faz a cadencia valer."""

    def __init__(self, tem_recorte: bool = True) -> None:
        self._tem_recorte = tem_recorte
        self.chamadas = 0

    def __call__(self):
        self.chamadas += 1
        return pixels() if self._tem_recorte else None


def novo_vigia(texto=None):
    from l2scanner.manutencao import VigiaDeManutencao

    leitor = LeitorFalso(texto)
    vigia = VigiaDeManutencao(
        ler_texto=leitor, ler_texto_conferencia=leitor.conferir
    )
    return vigia, leitor


def rodar(vigia, obter_pixels, inicio, segundos, passo=1):
    """Roda `avaliar` um tick por segundo e junta tudo que saiu."""
    colhidos = []
    for i in range(0, segundos, passo):
        colhidos.extend(vigia.avaliar(obter_pixels, inicio + timedelta(seconds=i)))
    return colhidos


class TestCadencia:
    def test_o_ocr_nao_roda_a_cada_tick(self):
        """D-06: 12 ticks, 3 leituras. O motivo e o mesmo do `VigiaDoCliente`.

        Uma chamada cara rodando a cada tick comeria o CPU do scanner inteiro —
        e ela nao precisa dessa frequencia, porque um banner de manutencao nao
        pisca: ele aparece e FICA.
        """
        vigia, leitor = novo_vigia("Server Maintence 40 minutes")
        obter = PixelsFalsos()

        rodar(vigia, obter, HOJE, segundos=12)

        assert leitor.chamadas == 3, "esperava leituras em t=0, 5 e 10"

    def test_os_pixels_so_sao_pedidos_quando_a_busca_vence(self):
        """O contador de pixels acompanha o de leituras, nunca o de ticks."""
        vigia, leitor = novo_vigia("Server Maintence 40 minutes")
        obter = PixelsFalsos()

        rodar(vigia, obter, HOJE, segundos=12)

        assert obter.chamadas == leitor.chamadas == 3

    def test_pixels_none_nao_quebram_e_nao_consomem_consenso(self):
        """Sem recorte nao ha leitura — e nao ha meia leitura guardada tambem."""
        vigia, leitor = novo_vigia("Server Maintence 40 minutes")
        obter = PixelsFalsos(tem_recorte=False)

        assert rodar(vigia, obter, HOJE, segundos=60) == []
        assert leitor.chamadas == 0
        assert vigia.momento is None


class TestConsenso:
    def test_duas_leituras_concordantes_anunciam(self):
        vigia, leitor = novo_vigia("Server Maintence 40 minutes")
        obter = PixelsFalsos()

        saiu = vigia.avaliar(obter, HOJE)
        assert saiu == [], "uma leitura so nunca anuncia"

        leitor.texto = "Server Maintence 39 minutes 55 seconds"
        saiu = vigia.avaliar(obter, HOJE + timedelta(seconds=5))

        assert len(saiu) == 1
        assert saiu[0].tipo is TipoDeAvisoDeManutencao.ANUNCIADA
        esperado = HOJE + timedelta(minutes=40)
        assert abs((vigia.momento - esperado).total_seconds()) <= 1

    def test_a_leitura_discrepante_nao_anuncia(self):
        """40, depois 4, depois 40 minutos: NADA sai (D-05).

        Sem esta regra um digito comido pelo OCR anunciaria "faltam 4 minutos"
        quando faltam 40, e a party largaria o farm por nada. Numa contagem de
        40 minutos, atrasar o primeiro aviso uma cadencia (~5 s) nao custa nada
        — e e o preco inteiro desta protecao.
        """
        vigia, leitor = novo_vigia("Server Maintence 40 minutes")
        obter = PixelsFalsos()
        saiu = []

        saiu += vigia.avaliar(obter, HOJE)
        leitor.texto = "Server Maintence 4 minutes"
        saiu += vigia.avaliar(obter, HOJE + timedelta(seconds=5))
        leitor.texto = "Server Maintence 40 minutes"
        saiu += vigia.avaliar(obter, HOJE + timedelta(seconds=10))

        assert saiu == []
        assert vigia.momento is None

    def test_uma_leitura_discrepante_nao_move_uma_ancora_ja_confirmada(self):
        vigia, leitor = novo_vigia("Server Maintence 40 minutes")
        obter = PixelsFalsos()
        vigia.avaliar(obter, HOJE)
        vigia.avaliar(obter, HOJE + timedelta(seconds=5))
        ancorado = vigia.momento
        assert ancorado is not None

        leitor.texto = "Server Maintence 4 minutes"
        saiu = vigia.avaliar(obter, HOJE + timedelta(seconds=10))

        assert vigia.momento == ancorado
        assert saiu == []

    def test_a_re_ancora_acontece_dentro_da_tolerancia(self):
        """A leitura mais recente e a mais precisa (D-04)."""
        vigia, leitor = novo_vigia("Server Maintence 40 minutes")
        obter = PixelsFalsos()
        vigia.avaliar(obter, HOJE)
        vigia.avaliar(obter, HOJE + timedelta(seconds=5))
        ancorado = vigia.momento

        leitor.texto = "Server Maintence 40 minutes 15 seconds"
        vigia.avaliar(obter, HOJE + timedelta(seconds=10))

        assert vigia.momento != ancorado
        esperado = HOJE + timedelta(seconds=10) + timedelta(minutes=40, seconds=15)
        assert abs((vigia.momento - esperado).total_seconds()) <= 1

    def test_uma_manutencao_remarcada_re_ancora_sem_reanunciar(self):
        """DUAS coisas ao mesmo tempo, e ate 2026-09-02 elas eram uma linha so.

        A ANCORA TROCA, e tem de trocar: a ancora anterior nao pode prender o
        vigia num horario que sumiu. Essa era a intencao original do
        `_emitidos.clear()` deste ramo e ela continua inteira — as assercoes
        sobre a ancora abaixo sao as mesmas de sempre.

        O ANUNCIO NAO VOLTA. Ate 02/09 este teste afirmava que a remarcacao
        re-emitia ANUNCIADA, e era ele que CODIFICAVA o defeito: naquele dia,
        entre 11:58 e 12:52, o grupo recebeu ~19 vezes a mesma mensagem para
        UMA manutencao so, porque cada deslize do OCR passava por aqui e fazia
        o anuncio parecer novo. Mover a ancora e re-armar o anuncio viraram
        duas coisas separadas, e o episodio agora so termina em `_expirar`.
        """
        vigia, leitor = novo_vigia("Server Maintence 40 minutes")
        obter = PixelsFalsos()
        vigia.avaliar(obter, HOJE)
        vigia.avaliar(obter, HOJE + timedelta(seconds=5))
        antigo = vigia.momento

        leitor.texto = "Server Maintence 90 minutes"
        vigia.avaliar(obter, HOJE + timedelta(seconds=10))
        saiu = vigia.avaliar(obter, HOJE + timedelta(seconds=15))

        assert vigia.momento != antigo
        esperado = HOJE + timedelta(seconds=15) + timedelta(minutes=90)
        assert abs((vigia.momento - esperado).total_seconds()) <= 1
        assert saiu == [], "a ancora se move; o grupo NAO recebe o anuncio de novo"


class TestCruzamentoDeEscalas:
    """D-d: duas ESCALAS sobre o MESMO frame, antes do consenso temporal.

    Este e o teste que o consenso temporal sozinho nao consegue fazer. Duas
    leituras pelo MESMO metodo, com 5 s de intervalo, concordam no MESMO erro
    sistematico — foi assim que o erro medido (cor -> 0:00:26) atravessaria a
    protecao de 260825-onz inteira e chegaria no WhatsApp da party.

    Tudo aqui roda com leitores INJETADOS: zero OCR, vale em qualquer maquina.
    """

    # A conferencia dizendo so os segundos: e a forma do erro real, com a
    # barata acertando os 40 minutos e a cara discordando por 40 minutos.
    DISCORDANTE = "Server Maintence 26 seconds"

    def test_escalas_que_discordam_nao_anunciam_e_nao_ancoram(self):
        """O bug reproduzido: 40 minutos contra 26 segundos, e NADA sai.

        Repetido por varios ticks de proposito. Um erro sistematico e estavel —
        se a guarda so olhasse o tick isolado, a repeticao acabaria confirmando.
        """
        vigia, leitor = novo_vigia(TEXTO_LIMPO)
        leitor.texto_de_conferencia = self.DISCORDANTE
        obter = PixelsFalsos()

        saiu = rodar(vigia, obter, HOJE, segundos=60)

        assert saiu == []
        assert vigia.momento is None

    def test_escalas_que_concordam_seguem_alimentando_o_consenso_temporal(self):
        """As duas guardas sao COMPLEMENTARES — cruzar escalas nao substitui repetir.

        Cruzar escalas pega erro de METODO; repetir no tempo pega erro de FRAME
        (uma captura no meio do desenho do banner). Guardar so uma deixaria uma
        das duas classes descoberta.
        """
        vigia, leitor = novo_vigia(TEXTO_LIMPO)
        obter = PixelsFalsos()

        assert vigia.avaliar(obter, HOJE) == [], "uma leitura so nunca anuncia"

        saiu = vigia.avaliar(obter, HOJE + timedelta(seconds=5))

        assert [a.tipo for a in saiu] == [TipoDeAvisoDeManutencao.ANUNCIADA]

    def test_uma_discordancia_nao_destroi_a_candidata(self):
        """Nem confirma, nem apaga: a discordancia sai sem tocar no estado.

        Se ela zerasse a candidata, um unico frame ruim no meio de uma contagem
        de 40 minutos adiaria o anuncio indefinidamente.
        """
        vigia, leitor = novo_vigia(TEXTO_LIMPO)
        obter = PixelsFalsos()

        vigia.avaliar(obter, HOJE)  # candidata guardada

        leitor.texto_de_conferencia = self.DISCORDANTE
        assert vigia.avaliar(obter, HOJE + timedelta(seconds=5)) == []

        leitor.texto_de_conferencia = _ESPELHO  # volta a concordar
        saiu = vigia.avaliar(obter, HOJE + timedelta(seconds=10))

        assert [a.tipo for a in saiu] == [TipoDeAvisoDeManutencao.ANUNCIADA]

    def test_uma_discordancia_nao_derruba_uma_ancora_ja_confirmada(self):
        vigia, leitor = novo_vigia(TEXTO_LIMPO)
        obter = PixelsFalsos()
        vigia.avaliar(obter, HOJE)
        vigia.avaliar(obter, HOJE + timedelta(seconds=5))
        ancorado = vigia.momento
        assert ancorado is not None

        leitor.texto_de_conferencia = self.DISCORDANTE
        saiu = vigia.avaliar(obter, HOJE + timedelta(seconds=10))

        assert saiu == []
        assert vigia.momento == ancorado

    def test_a_escala_cara_nao_roda_quando_a_barata_nao_ve_o_banner(self):
        """D-e — e a razao dele MUDOU, entao vale registrar aqui tambem.

        Nao e mais orcamento: medidas de novo e ja aquecidas, na banda de
        producao, a passada de deteccao custa 23 ms e a de conferencia 31 ms.
        Rodar as duas sempre caberia folgado. O que esta ordem preserva e a
        disciplina de nao gastar trabalho lendo o chao quando nao ha banner
        nenhum na tela — e o teste continua valendo igual.
        """
        vigia, leitor = novo_vigia("Korzis: bora upar? Kaus ta on")
        obter = PixelsFalsos()

        rodar(vigia, obter, HOJE, segundos=12)

        assert leitor.chamadas == 3, "esperava leituras em t=0, 5 e 10"
        assert leitor.chamadas_de_conferencia == 0

    def test_a_escala_cara_roda_uma_vez_por_cadencia_quando_a_barata_detecta(self):
        vigia, leitor = novo_vigia(TEXTO_LIMPO)
        obter = PixelsFalsos()

        rodar(vigia, obter, HOJE, segundos=12)

        assert leitor.chamadas == 3
        assert leitor.chamadas_de_conferencia == 3

    def test_o_desacordo_entre_escalas_vai_para_o_log(self, caplog):
        """"O banner esta na tela e nos NAO vamos anunciar" e o estado mais
        perigoso deste recurso — e o log rotativo e a unica forense pos-farm.

        Os DOIS textos crus precisam estar la: e a unica coisa que diz se o
        conserto e a faixa (chave `banner_manutencao`) ou o motor de OCR.
        """
        import logging

        vigia, leitor = novo_vigia(TEXTO_LIMPO)
        leitor.texto_de_conferencia = self.DISCORDANTE
        obter = PixelsFalsos()

        with caplog.at_level(logging.WARNING, logger="l2scanner.manutencao"):
            vigia.avaliar(obter, HOJE)

        mensagens = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
        assert mensagens
        juntas = " ".join(mensagens)
        assert self.DISCORDANTE in juntas
        assert TEXTO_LIMPO in juntas


class TestBannerRealDe31De08:
    """A PRIMEIRA leitura de campo, e o defeito que ela reprovou.

    Ate 2026-08-31 a porta 1 exigia a raiz exata `mainten`, e o argumento
    escrito era que ela e o token mais RARO da tela. O raciocinio continua
    certo; o TOKEN e que estava errado. Nas oito leituras reais a raiz aparece
    ZERO vezes, entao a porta 1 nunca fechava e o scanner atravessou uma hora
    de banner na tela em silencio.
    """

    @pytest.mark.parametrize("rotulo,texto,_esperado", CAMPO_31_08)
    def test_a_raiz_exata_mainten_esta_ausente_nas_oito(self, rotulo, texto, _esperado):
        """O defeito, afirmado antes do conserto. 8 de 8.

        Este teste nao cobra o conserto: ele cobra a MEDICAO em que o conserto
        se apoia. Se um dia o motor de OCR passar a entregar o `M`, e este
        teste ficar vermelho, a razao escrita na porta 1 caiu junto e o proximo
        a mexer precisa saber disso.
        """
        assert "mainten" not in texto.lower(), rotulo

    @pytest.mark.parametrize("rotulo,texto,_esperado", CAMPO_31_08)
    def test_as_oito_leituras_reais_fecham_a_porta_1(self, rotulo, texto, _esperado):
        """O CONSERTO. Volte a porta 1 para `mainten` exato e as oito caem.

        E o teste que faltava em 24/08: o spike leu um banner sintetico, este
        le o banner que o servidor mostrou de verdade.
        """
        assert eh_banner_de_manutencao(texto) is True, rotulo

    @pytest.mark.parametrize("rotulo,texto,esperado", CAMPO_31_08)
    def test_a_duracao_de_cada_uma_das_oito(self, rotulo, texto, esperado):
        """As tres abstencoes da 2x sao ESPERADAS, e nao um segundo defeito.

        `minåtes` e `minütes` derrubam a captura do numero de minutos, e a
        guarda estrutural (D-b) manda CALAR em vez de cair para "entao e so os
        segundos". Devolver 27 ou 13 segundos aqui seria o bug de 40min26s de
        volta, com outra roupa.
        """
        assert interpretar_banner(texto) == esperado, rotulo

    def test_a_semelhanca_reconhece_a_palavra_com_o_M_comido(self):
        """A porta 1, ramo da PALAVRA. Cai se alguem voltar ao `in` exato.

        Medido com `difflib.SequenceMatcher` contra `maintence`/`maintenance`:
        `aintence` da 0,941 e passa; `aiptence` da 0,824 e NAO passa, porque
        `main entrance` da 0,833 e nenhum corte escalar separa os dois. O
        `aiptence` e recuperado pelo outro ramo, o da ancora.
        """
        from l2scanner.manutencao import parece_palavra_de_manutencao

        assert parece_palavra_de_manutencao('13 Server "aintencea2J 04 minutes') is True
        assert parece_palavra_de_manutencao("Server Maintence 40 minutes") is True
        assert parece_palavra_de_manutencao("Server Maintenance 40 minutes") is True

        # A colisao medida, e por isso o corte esta acima dela.
        assert parece_palavra_de_manutencao("visit the main entrance") is False
        assert parece_palavra_de_manutencao("Korzis: bora upar? Kaus ta on") is False

    def test_a_ancora_sozinha_nao_basta_e_isso_e_deliberado(self):
        """`avoid entering instance` sem contagem NAO e o banner.

        Ela e o sinal mais confiavel (8 de 8, limpo em 7) e mesmo assim nao
        pode abrir a porta sozinha: o jogo diz essa frase, e uma manutencao
        inventada custa uma mensagem falsa no grupo. Ancora E contagem.
        """
        assert eh_banner_de_manutencao("Please avoid entering instance") is False
        assert eh_banner_de_manutencao(
            "Please avoid entering instance 04 minutes 12 seconds"
        ) is True


class TestConsensoComAbstencao:
    """A porta 3 continua de pe, com a REGRA trocada: abstencao nao e discordancia.

    Medido em 31/08: em 4 rodadas as duas escalas NUNCA produziram numeros
    diferentes. O que aconteceu em 3 delas foi a 2x se abster. A regra antiga
    ("as duas precisam produzir a mesma duracao") tratava abstencao como
    discordancia e jogava fora 3 das 4 leituras boas.
    """

    def test_a_rodada_real_de_31_08_teria_anunciado(self):
        """O incidente inteiro, com os textos que o motor leu de verdade.

        Antes do conserto: nada sai. Este e o teste que responde "por que o
        scanner ficou calado enquanto o banner estava na tela".
        """
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()

        leitor.texto = CAMPO_1_2X  # a 2x se absteve
        leitor.texto_de_conferencia = CAMPO_1_3X  # a 3x leu 20:27
        assert vigia.avaliar(obter, HOJE) == [], "uma leitura so nunca anuncia"

        saiu = vigia.avaliar(obter, HOJE + timedelta(seconds=5))

        assert [a.tipo for a in saiu] == [TipoDeAvisoDeManutencao.ANUNCIADA]
        esperado = HOJE + timedelta(minutes=20, seconds=27)
        assert abs((vigia.momento - esperado).total_seconds()) <= 6
        assert "20 minutos e 27 segundos" in saiu[0].texto

    def test_o_bloco_das_18h16_ancora_com_as_duas_formas_de_leitura(self):
        """Rodada 2 (so a conferencia) e rodada 3 (as duas) se somam.

        As duas formas alimentam o MESMO consenso temporal, que continua
        exigindo duas leituras concordantes para ancorar.
        """
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()

        leitor.texto = CAMPO_2_2X
        leitor.texto_de_conferencia = CAMPO_2_3X
        assert vigia.avaliar(obter, HOJE) == []

        leitor.texto = CAMPO_3_2X
        leitor.texto_de_conferencia = CAMPO_3_3X
        saiu = vigia.avaliar(obter, HOJE + timedelta(seconds=5))

        assert [a.tipo for a in saiu] == [
            TipoDeAvisoDeManutencao.ANUNCIADA,
            TipoDeAvisoDeManutencao.ANTES,
        ]

    def test_a_escala_de_deteccao_sozinha_nunca_ancora(self):
        """O outro lado da regra, e ele NAO foi afrouxado.

        Medido: a 3x acertou 4 de 4 e a 2x 1 de 4. Quem le sozinha tem de ser a
        de conferencia. Perder a leitura da 2x solitaria custa uma cadencia,
        5 s; ancorar na escala medida como pior custa a farm da party.
        """
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()

        leitor.texto = CAMPO_3_2X  # a barata leu 04:12
        leitor.texto_de_conferencia = CAMPO_2_2X  # a cara se absteve

        assert rodar(vigia, obter, HOJE, segundos=60) == []
        assert vigia.momento is None

    def test_duas_duracoes_diferentes_seguem_recusadas(self):
        """D-d intacto: contradicao continua sendo contradicao.

        E a forma do erro que criou esta guarda (cor lendo 26 s contra cinza
        lendo 40min26s). Trocar a regra do consenso nao podia comprar a leitura
        de campo ao preco de reabrir esta porta.
        """
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()

        leitor.texto = CAMPO_1_3X  # 20:27
        leitor.texto_de_conferencia = CAMPO_3_3X  # 04:12

        assert rodar(vigia, obter, HOJE, segundos=60) == []
        assert vigia.momento is None

    def test_a_abstencao_das_duas_nao_ancora_e_vai_para_o_log(self, caplog):
        """Banner na tela e nenhuma duracao: o estado mais perigoso, nunca mudo."""
        import logging

        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()
        leitor.texto = CAMPO_2_2X
        leitor.texto_de_conferencia = CAMPO_4_2X

        with caplog.at_level(logging.WARNING, logger="l2scanner.manutencao"):
            assert vigia.avaliar(obter, HOJE) == []

        juntas = " ".join(r.getMessage() for r in caplog.records)
        assert CAMPO_2_2X in juntas and CAMPO_4_2X in juntas
        assert vigia.momento is None


class TestVeredito:
    """O diagnostico nao pode mentir sobre o proprio diagnostico.

    Medido em 31/08, rodada 1: as duas escalas leram texto IDENTICO, as duas
    deram `eh_banner=False, interpretar=None`, e o `--testar-manutencao`
    imprimiu "As duas escalas DISCORDAM". Elas concordavam. O usuario foi
    mandado conferir a faixa por causa de uma frase errada.
    """

    def test_duas_leituras_identicas_e_ilegiveis_nao_sao_discordancia(self):
        from l2scanner.manutencao import MotivoDoVeredito, julgar_as_duas_escalas

        v = julgar_as_duas_escalas(CAMPO_2_2X, CAMPO_2_2X)

        assert v.motivo is MotivoDoVeredito.ILEGIVEL
        assert v.anunciaria is False
        assert "DISCORD" not in v.explicacao.upper()
        assert "CONTRADI" not in v.explicacao.upper()

    def test_a_contradicao_de_verdade_continua_sendo_nomeada(self):
        from l2scanner.manutencao import MotivoDoVeredito, julgar_as_duas_escalas

        v = julgar_as_duas_escalas(CAMPO_1_3X, CAMPO_3_3X)

        assert v.motivo is MotivoDoVeredito.CONTRADICAO
        assert v.anunciaria is False
        assert v.duracao is None

    def test_o_veredito_diz_qual_escala_leu_sozinha(self):
        from l2scanner.manutencao import MotivoDoVeredito, julgar_as_duas_escalas

        so_conferencia = julgar_as_duas_escalas(CAMPO_1_2X, CAMPO_1_3X)
        assert so_conferencia.motivo is MotivoDoVeredito.SO_A_CONFERENCIA
        assert so_conferencia.anunciaria is True
        assert so_conferencia.duracao == timedelta(minutes=20, seconds=27)

        so_deteccao = julgar_as_duas_escalas(CAMPO_3_2X, CAMPO_2_2X)
        assert so_deteccao.motivo is MotivoDoVeredito.SO_A_DETECCAO
        assert so_deteccao.anunciaria is False

    def test_sem_banner_na_barata_a_cara_nem_conta(self):
        """D-e dentro do veredito: em producao a conferencia nem roda.

        Se o veredito ignorasse essa ordem, o `--testar-manutencao` diria
        "anunciaria" para um caso que em producao nunca chega a ser lido.
        """
        from l2scanner.manutencao import MotivoDoVeredito, julgar_as_duas_escalas

        v = julgar_as_duas_escalas("Korzis: bora upar?", CAMPO_1_3X)

        assert v.motivo is MotivoDoVeredito.SEM_BANNER
        assert v.anunciaria is False

    def test_as_escalas_que_concordam_devolvem_a_leitura_da_conferencia(self):
        from l2scanner.manutencao import MotivoDoVeredito, julgar_as_duas_escalas

        v = julgar_as_duas_escalas(CAMPO_3_2X, CAMPO_3_3X)

        assert v.motivo is MotivoDoVeredito.ACORDO
        assert v.anunciaria is True
        assert v.duracao == timedelta(minutes=4, seconds=12)

    def test_nenhuma_explicacao_tem_travessao(self):
        """Elas saem no console e no log, e o console do usuario e cp1252."""
        from l2scanner.manutencao import MotivoDoVeredito, julgar_as_duas_escalas

        for a, b in (
            (CAMPO_1_2X, CAMPO_1_3X),
            (CAMPO_3_2X, CAMPO_2_2X),
            (CAMPO_1_3X, CAMPO_3_3X),
            (CAMPO_2_2X, CAMPO_2_2X),
            (CAMPO_3_2X, CAMPO_3_3X),
            ("Korzis: bora upar?", None),
        ):
            v = julgar_as_duas_escalas(a, b)
            assert "—" not in v.explicacao
            assert "–" not in v.explicacao
            assert isinstance(v.motivo, MotivoDoVeredito)

    def test_o_testar_manutencao_usa_o_veredito_de_producao(self):
        """O defeito era o diagnostico ter LOGICA PROPRIA e ela divergir.

        A prova estrutural e mais barata que subir captura e OCR num teste, e
        pega exatamente a reincidencia: alguem reescrevendo o veredito a mao
        dentro do comando.
        """
        import inspect

        from l2scanner import __main__ as principal

        fonte = inspect.getsource(principal.comando_testar_manutencao)

        assert "julgar_as_duas_escalas" in fonte
        assert "DISCORDAM" not in fonte


class TestAncoraSobreviveACegueira:
    """O coracao de D-10, e a razao inteira de a ancora existir."""

    def _ancorar(self, vigia, leitor, obter, texto):
        leitor.texto = texto
        saiu = vigia.avaliar(obter, HOJE)
        saiu += vigia.avaliar(obter, HOJE + timedelta(seconds=5))
        return saiu

    def test_o_segundo_aviso_sai_com_o_ocr_devolvendo_none_depois(self):
        """GOAL-02 sobrevive ao banner sumir, ao jogo coberto e ao alt-tab.

        Sem a ancora, o segundo aviso dependeria de uma leitura bem sucedida no
        instante exato — e manutencao e justamente quando o cliente comeca a
        engasgar e a leitura falha. E o unico teste deste arquivo que prova o
        motivo de a ancora existir.

        A DURACAO SUBIU DE 8 PARA 15 MINUTOS quando `ANTECEDENCIA` virou dez
        (2026-09-02), e a conta e esta: com 8 minutos lidos o restante ja nasce
        ABAIXO do limiar novo, os dois avisos sairiam no MESMO tick da
        ancoragem, e este teste — que existe para provar que o segundo aviso sai
        com o OCR CEGO — deixaria de provar isso. Com 15 minutos a ancora cai em
        HOJE+15:05, o restante toca 10 minutos no tick 305, e a corrida de 400 s
        a partir do tick 6 atravessa esse instante com o leitor devolvendo None.
        """
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()
        na_ancoragem = self._ancorar(
            vigia, leitor, obter, "Server Maintence 15 minutes"
        )
        assert vigia.momento is not None
        assert [a.tipo for a in na_ancoragem] == [
            TipoDeAvisoDeManutencao.ANUNCIADA
        ], "com 15 minutos, na ancoragem sai SO o anuncio"

        leitor.texto = None  # o banner sumiu; o OCR nao le mais nada
        antes = leitor.chamadas
        momento = vigia.momento

        saiu = rodar(vigia, obter, HOJE + timedelta(seconds=6), segundos=400)

        assert [a.tipo for a in saiu] == [TipoDeAvisoDeManutencao.ANTES]
        assert momento.strftime("%H:%M") in saiu[0].texto
        assert leitor.chamadas > antes, "o OCR rodou, so nao leu nada util"

    def test_os_dois_avisos_saem_quando_o_scanner_sobe_com_pouco_tempo(self):
        """E o segundo aviso diz 3 minutos, nao 10 — nunca mente sobre o tempo.

        3 minutos continua ABAIXO do limiar nos dois mundos (5 e 10), entao a
        aritmetica deste teste sobreviveu intacta a mudanca de 2026-09-02: so o
        numero CITADO mudou, porque o que ele nega e o numero do limiar.
        """
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()

        saiu = self._ancorar(vigia, leitor, obter, "Server Maintence 3 minutes")

        assert [a.tipo for a in saiu] == [
            TipoDeAvisoDeManutencao.ANUNCIADA,
            TipoDeAvisoDeManutencao.ANTES,
        ]
        assert "3 minutos" in saiu[1].texto
        assert "5 minutos" not in saiu[1].texto

    def test_cada_tipo_sai_uma_vez_so(self):
        """A DURACAO SUBIU DE 6 PARA 15 MINUTOS, e a conta e a mesma de cima.

        Com 6 minutos e o limiar novo de dez, os DOIS avisos sairiam no MESMO
        tick da ancoragem e a contagem de um-de-cada deixaria de medir alguma
        coisa: ela so tem forca enquanto os dois tipos saem em ticks DISTINTOS.
        Com 15 minutos a ancora cai em HOJE+15:05, o anuncio sai no tick 5, o
        segundo aviso no tick 305, e a corrida de 400 s a partir do tick 6
        cobre os dois com folga.
        """
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()
        saiu = self._ancorar(vigia, leitor, obter, "Server Maintence 15 minutes")
        leitor.texto = None

        saiu += rodar(vigia, obter, HOJE + timedelta(seconds=6), segundos=400)

        tipos = [a.tipo for a in saiu]
        assert tipos.count(TipoDeAvisoDeManutencao.ANUNCIADA) == 1
        assert tipos.count(TipoDeAvisoDeManutencao.ANTES) == 1


class TestOLimiarDoSegundoAviso:
    """ANTECEDENCIA = 10 minutos, pedido pelo usuario em 2026-09-02.

    Pedido literal: "avise apenas quando aparece o anuncio e quando faltar 10m".
    O limiar antigo eram 5 minutos, e 5 minutos numa manutencao anunciada com 40
    e tempo de mais nada — nem de sair da instance, nem de recolher o chao.
    """

    def _ancorar(self, vigia, leitor, obter, texto):
        leitor.texto = texto
        saiu = vigia.avaliar(obter, HOJE)
        saiu += vigia.avaliar(obter, HOJE + timedelta(seconds=5))
        return saiu

    def test_o_segundo_aviso_sai_quando_o_restante_cai_a_dez_minutos(self):
        """AS DUAS BORDAS DO LIMIAR, e a conta esta escrita.

        A ancora nasce na SEGUNDA leitura, em HOJE+5 s, com 15 minutos lidos:
        ela cai em HOJE+15:05. O restante toca 10 minutos exatos em HOJE+5:05,
        ou seja no tick 305. A corrida de 299 s a partir do tick 6 cobre os
        ticks 6 a 304 — todo o intervalo em que o restante ainda e MAIOR que 10
        minutos — e nao pode produzir nada.
        """
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()

        na_ancoragem = self._ancorar(
            vigia, leitor, obter, "Server Maintence 15 minutes"
        )
        assert [a.tipo for a in na_ancoragem] == [TipoDeAvisoDeManutencao.ANUNCIADA]

        leitor.texto = None
        momento = vigia.momento

        assert rodar(vigia, obter, HOJE + timedelta(seconds=6), segundos=299) == []

        saiu = vigia.avaliar(obter, HOJE + timedelta(seconds=305))

        assert [a.tipo for a in saiu] == [TipoDeAvisoDeManutencao.ANTES]
        assert "10 minutos" in saiu[0].texto
        assert momento.strftime("%H:%M") in saiu[0].texto

    def test_com_menos_de_dez_minutos_os_dois_saem_juntos_dizendo_o_tempo_real(self):
        """O aviso NUNCA mente sobre o tempo — nem depois de o limiar mudar.

        Quando o scanner sobe no meio de uma contagem de 4 minutos os dois
        avisos saem juntos e atrasados, e o segundo tem de dizer QUATRO. Cravar
        o numero do limiar ali faria o grupo se programar para seis minutos que
        nao existem.
        """
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()

        saiu = self._ancorar(vigia, leitor, obter, "Server Maintence 4 minutes")

        assert [a.tipo for a in saiu] == [
            TipoDeAvisoDeManutencao.ANUNCIADA,
            TipoDeAvisoDeManutencao.ANTES,
        ]
        assert "4 minutos" in saiu[1].texto
        assert "10 minutos" not in saiu[1].texto

    def test_um_deslize_dentro_da_tolerancia_nao_re_emite_nada(self):
        """O lado (a) da regra de re-armar, e o caso COMUM em campo.

        A ancora cai em HOJE+4:05. A leitura seguinte diz 3 min 30 s e implica
        HOJE+3:40 — 25 segundos de deslize, dentro dos 60 s de
        `TOLERANCIA_DO_CONSENSO`. Este ramo nao encosta em `_emitidos`, hoje e
        depois, e e por isso que o OCR pode escorregar a cada cadencia sem que
        o grupo receba nada de novo.
        """
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()
        saiu = self._ancorar(vigia, leitor, obter, "Server Maintence 4 minutes")
        assert len(saiu) == 2

        leitor.texto = "Server Maintence 3 minutes 30 seconds"
        depois = vigia.avaliar(obter, HOJE + timedelta(seconds=10))

        assert depois == []

    def test_so_uma_remarcacao_acima_do_limiar_re_arma_o_segundo_aviso(self):
        """O lado (b): manutencao genuinamente ADIADA merece o aviso de novo.

        Duas leituras concordantes trazem o alvo para 25 minutos —
        `duracao > ANTECEDENCIA` —, entao o segundo aviso volta a ficar ARMADO.
        Armado nao e emitido: nada sai no tick da remarcacao. A ancora nova cai
        em HOJE+15 s + 25 min = HOJE+25:15, o restante toca 10 minutos no tick
        915, e a corrida de 899 s a partir do tick 16 cobre os ticks 16 a 914
        sem produzir nada.

        O ANUNCIADA nao volta em nenhum dos dois momentos: so `_expirar`
        encerra o episodio.
        """
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()
        saiu = self._ancorar(vigia, leitor, obter, "Server Maintence 4 minutes")
        assert len(saiu) == 2

        leitor.texto = "Server Maintence 25 minutes"
        vigia.avaliar(obter, HOJE + timedelta(seconds=10))
        na_remarcacao = vigia.avaliar(obter, HOJE + timedelta(seconds=15))

        assert na_remarcacao == [], "re-armar nao e re-emitir"

        leitor.texto = None
        assert rodar(vigia, obter, HOJE + timedelta(seconds=16), segundos=899) == []

        voltou = vigia.avaliar(obter, HOJE + timedelta(seconds=915))

        assert [a.tipo for a in voltou] == [TipoDeAvisoDeManutencao.ANTES]
        assert "10 minutos" in voltou[0].texto


class TestOValorDuravelDoSegundoAviso:
    def test_o_membro_renomeado_carrega_o_valor_antigo(self):
        """O NOME perdeu o numero; o VALOR nao pode perder. E deliberado.

        O membro se chama `ANTES` — o mesmo vocabulario que
        `agenda.TipoDeAviso.ANTES` ja usa para o aviso de antecedencia — porque
        um nome com numero dentro envelhece junto com o limiar, e o limiar
        acabou de mudar de 5 para 10.

        O `.value` continua sendo `faltam5` porque ele NAO e descricao, e
        identidade duravel: entra em `chave_do_marcador`, vira nome de arquivo
        em `.agenda/`, e e o que faz um scanner reiniciado no meio de uma
        manutencao em curso saber que o aviso ja saiu. Trocar o valor custaria
        uma mensagem duplicada no grupo para cada manutencao ja em andamento;
        mante-lo custa um nome de arquivo que so faz sentido com esta docstring
        ao lado. A lei ja estava escrita em `agenda.py`, no membro
        `TipoDeAviso.CHAMADA`, e no proprio enum deste modulo.
        """
        assert TipoDeAvisoDeManutencao.ANTES.value == "faltam5"
        assert chave_do_marcador(
            HOJE, TipoDeAvisoDeManutencao.ANTES
        ).endswith("_faltam5")


class TestOSpamDeCampoDe0209:
    """O DEFEITO MEDIDO EM CAMPO, replayado tick a tick.

    Em 2026-09-02, entre 11:58 e 12:52, o grupo de WhatsApp do usuario recebeu
    ~19 vezes a MESMA mensagem de anuncio para UMA unica manutencao, com o
    horario-alvo pulando entre 17 leituras espalhadas por 54 minutos — de 12:11
    a 13:05 (`HORARIOS_ALVO_DO_CAMPO`).

    A MECANICA que este replay reproduz, e que nenhuma das guardas anteriores
    alcancava: uma leitura fora da tolerancia vira `_candidata`; a leitura
    seguinte chega 5 s depois (`SEGUNDOS_ENTRE_LEITURAS`) repetindo o MESMO erro
    sistematico de OCR e portanto cai dentro dos 60 s de
    `TOLERANCIA_DO_CONSENSO` em relacao a candidata; a ancora TROCA — e ate este
    conserto a troca zerava `_emitidos` inteiro, fazendo o anuncio parecer novo.

    A DEDUP EM DISCO NAO SEGUROU, E NAO PODIA: `chave_do_marcador` deriva do
    MOMENTO DA ANCORA arredondado ao minuto, entao cada deslize de minuto
    produzia uma chave inedita e o `marcar` criava um arquivo novo em vez de
    barrar. A guarda de uma-vez-por-episodio tem de viver no vigia.
    """

    def _replay(self):
        """Os 54 minutos do episodio, um tick por segundo, com o relogio injetado.

        Um tick por segundo e nao um por cadencia porque o que se prova aqui
        inclui os ticks SEM leitura: e neles que a ancora segura sozinha.
        """
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()
        saiu = []
        primeira_ancora = None
        for segundo in range(int(DURACAO_DO_CAMPO.total_seconds())):
            agora = INICIO_DO_CAMPO + timedelta(seconds=segundo)
            leitor.texto = texto_do_campo(agora)
            saiu += vigia.avaliar(obter, agora)
            if primeira_ancora is None and vigia.momento is not None:
                primeira_ancora = vigia.momento
        return vigia, saiu, primeira_ancora

    def test_a_sequencia_deslizante_do_campo_produz_UM_anuncio_so(self):
        """~19 mensagens em campo; UMA depois do conserto.

        Medido contra a producao MUTILADA (com o `_emitidos.clear()` deste ramo
        restaurado) esta mesma sequencia produz 14 anuncios — a forma do defeito
        que o usuario viu, com os 5 que faltam para os ~19 do print explicados
        pelos deslizes que caem DENTRO da tolerancia e que nem chegam a este
        ramo.
        """
        vigia, saiu, primeira_ancora = self._replay()

        tipos = [a.tipo for a in saiu]
        assert tipos.count(TipoDeAvisoDeManutencao.ANUNCIADA) == 1

    def test_o_segundo_aviso_do_campo_tem_o_residuo_MEDIDO_e_aceito(self):
        """SEIS. O numero e feio, esta medido, e fica escrito em vez de escondido.

        O anuncio virou UMA vez por episodio, mas o SEGUNDO aviso ainda pode
        repetir, e a regra que o re-arma e a razao: uma remarcacao confirmada
        que traz o alvo de volta para ACIMA de 10 minutos volta a arma-lo, e
        nesta sequencia o OCR faz isso seis vezes. O aviso sai as 12:08:05,
        12:20, 12:25, 12:27, 12:35:35 e 12:46 — e as tres do meio saem dizendo
        "10 minutos" para tres horarios-alvo DIFERENTES (12:30, 12:35, 12:37).

        E CUSTO ACEITO, e o preco da alternativa e o que decide: nao re-armar
        nunca significaria que uma manutencao genuinamente ADIADA — de 4 para
        25 minutos, digamos — nunca mais avisaria o grupo quando o horario novo
        chegasse perto. Perder o aviso de antecedencia de uma manutencao real
        custa a instance e o loot do chao; recebe-lo seis vezes custa incomodo.

        A COMPARACAO HONESTA com o campo: la o segundo tipo saiu 3 vezes
        (12:11, 12:41, 12:52), com o limiar de 5 minutos. Com o limiar de 10 a
        janela e o DOBRO, entao mais deslizes da ancora caem dentro dela — 6 e
        o preco do que o usuario pediu, e nao uma regressao do conserto. O
        episodio inteiro saiu de ~22 mensagens (~19 anuncios + 3) para 7.
        """
        _vigia, saiu, _primeira = self._replay()

        tipos = [a.tipo for a in saiu]
        assert tipos.count(TipoDeAvisoDeManutencao.ANTES) == 6

    def test_a_ancora_continua_deslizando_ao_longo_do_episodio(self):
        """SEM ISTO O TESTE ACIMA PASSARIA DE GRACA.

        Um vigia que simplesmente parasse de reancorar tambem produziria um
        anuncio so — e estaria quebrado do outro lado, preso num horario que a
        remarcacao apagou. A ancora nasce em 12:59 (o primeiro alvo do print) e
        termina em 12:56 (o ultimo), tendo passado por 13:05 e por 12:11 no
        meio.
        """
        vigia, _saiu, primeira_ancora = self._replay()

        assert primeira_ancora == datetime(2026, 9, 2, 12, 59)
        assert vigia.momento == datetime(2026, 9, 2, 12, 56)
        assert vigia.momento != primeira_ancora


class TestExpiracao:
    """D-10: a ancora tem que morrer, senao a manutencao seguinte morre com ela."""

    def _ancorar(self, vigia, leitor, obter, texto="Server Maintence 6 minutes"):
        leitor.texto = texto
        vigia.avaliar(obter, HOJE)
        vigia.avaliar(obter, HOJE + timedelta(seconds=5))
        leitor.texto = None

    def test_a_ancora_expira_depois_do_momento_com_folga(self):
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()
        self._ancorar(vigia, leitor, obter)
        momento = vigia.momento

        vigia.avaliar(obter, momento + timedelta(minutes=11))

        assert vigia.momento is None

    def test_nao_reavisa_depois_de_expirar(self):
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()
        self._ancorar(vigia, leitor, obter)
        momento = vigia.momento

        saiu = rodar(vigia, obter, momento + timedelta(minutes=11), segundos=300)

        assert saiu == []

    def test_depois_de_expirar_uma_manutencao_nova_pode_ser_anunciada(self):
        """Limpar `_emitidos` na expiracao e OBRIGATORIO.

        Sem isso a proxima manutencao de verdade seria detectada e nunca
        anunciada — o pior modo de falha deste projeto, porque o scanner
        pareceria estar funcionando.
        """
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()
        self._ancorar(vigia, leitor, obter)
        depois = vigia.momento + timedelta(minutes=11)
        vigia.avaliar(obter, depois)
        assert vigia.momento is None

        leitor.texto = "Server Maintence 40 minutes"
        saiu = vigia.avaliar(obter, depois + timedelta(seconds=10))
        saiu += vigia.avaliar(obter, depois + timedelta(seconds=15))

        assert [a.tipo for a in saiu] == [TipoDeAvisoDeManutencao.ANUNCIADA]


class TestModuloPuro:
    def test_manutencao_nao_importa_winrt_cv2_nem_ocr(self):
        """Assercao ESTRUTURAL de proposito (D-03).

        Uma regra de arquitetura que so vive num comentario e uma regra que ja
        quebrou. O dia em que alguem escrever `from .ocr import ler_texto`
        aqui, o modulo puro deixa de ser testavel no Python da suite — e o
        recurso inteiro fica sem rede.
        """
        import ast
        from pathlib import Path

        import l2scanner.manutencao as modulo

        arvore = ast.parse(Path(modulo.__file__).read_text(encoding="utf-8"))

        importados = []
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                importados += [a.name for a in no.names]
            elif isinstance(no, ast.ImportFrom):
                importados.append(no.module or "")

        for nome in importados:
            assert not nome.startswith("winrt"), nome
            assert nome != "cv2", nome
            assert not nome.endswith("ocr"), nome


class TestRegiaoDoBanner:
    """D-07: de onde saem os pixels do banner, e o que acontece sem calibracao."""

    FIXTURE = (
        Path(__file__).parent
        / "fixtures"
        / "party_estavel_com_vazamento"
        / "calibracao.json"
    )

    def _calibracao(self, **extra):
        """Parte da calibracao REAL de fixture, e nao de uma montada a mao.

        Uma calibracao inventada aqui divergiria do formato do usuario sem
        ninguem perceber — e o formato e justamente o que este teste guarda.
        """
        from dataclasses import replace

        from l2scanner.calibracao import Calibracao
        from l2scanner.frames import Regiao

        cal = Calibracao.carregar(self.FIXTURE)
        base = dict(
            party_window_na_janela=Regiao(
                esquerda=62, topo=328, largura=120, altura=400
            )
        )
        base.update(extra)
        return replace(cal, **base)

    def test_a_regiao_calibrada_vence_o_padrao(self):
        from l2scanner.frames import Regiao

        minha = Regiao(esquerda=10, topo=20, largura=300, altura=40)
        cal = self._calibracao(banner_manutencao=minha)

        assert cal.regiao_do_banner(na_janela=True) is minha
        assert cal.regiao_do_banner(na_janela=False) is minha

    def test_sem_calibracao_no_caminho_janela_o_padrao_cobre_o_canto(self):
        """O banner aparece POR CIMA da party window, e e mais largo que ela."""
        cal = self._calibracao()
        party = cal.party_window_na_janela

        r = cal.regiao_do_banner(na_janela=True)

        assert r is not None
        assert r.esquerda <= party.esquerda
        assert r.topo <= party.topo
        assert r.esquerda + r.largura >= party.esquerda
        assert r.topo + r.altura >= party.topo
        assert r.largura > party.largura, "o banner e mais largo que as barras"

    def test_a_faixa_cobre_o_banner_da_calibracao_REAL_com_folga(self):
        """D-f, medido contra a calibracao que o usuario tirou da tela dele.

        Os numeros estao INLINE porque `calibration.json` e ignorado pelo git:
        um teste que dependesse do arquivo dele nao rodaria em clone nenhum.
        Sao os valores de 2026-08-24 — esquerda 20, topo 222, 172x522.

        A FOLGA ENTRA NA ASSERCAO DE PROPOSITO. Cobrir por 1 px passaria neste
        teste e falharia na tela: a estimativa do banner (y 168..253) TEM
        incerteza, e cortar o titulo `Server Maintence` cala o recurso inteiro
        sem sintoma nenhum. Com os numeros antigos (60/140) a folga era de ~6 px
        no topo — e este teste teria falhado.
        """
        from l2scanner.frames import Regiao

        cal = self._calibracao(
            party_window_na_janela=Regiao(
                esquerda=20, topo=222, largura=172, altura=522
            )
        )

        r = cal.regiao_do_banner(na_janela=True)

        TOPO_DO_BANNER, BASE_DO_BANNER = 168, 253
        FOLGA_MINIMA = 40

        assert r is not None
        assert TOPO_DO_BANNER - r.topo >= FOLGA_MINIMA, (
            f"faixa comeca em y={r.topo}; o banner estimado comeca em "
            f"y={TOPO_DO_BANNER} — folga insuficiente no topo"
        )
        assert (r.topo + r.altura) - BASE_DO_BANNER >= FOLGA_MINIMA, (
            f"faixa termina em y={r.topo + r.altura}; o banner estimado termina "
            f"em y={BASE_DO_BANNER} — folga insuficiente embaixo"
        )

    def test_sem_calibracao_no_caminho_mss_devolve_none(self):
        """O "simplesmente nao liga" de D-07.

        No modo `mss` nao existe janela de referencia, entao um padrao seria um
        palpite sobre coordenadas de desktop — inventar deteccao onde nao ha
        pixels e pior do que nao ligar.
        """
        cal = self._calibracao()
        assert cal.regiao_do_banner(na_janela=False) is None

    def test_o_padrao_nunca_sai_com_coordenada_negativa(self):
        """Party window colada no canto: as margens nao podem virar negativo.

        `Regiao` aceita negativo de proposito (monitor a esquerda do
        principal), entao um clamp errado aqui passaria calado e o recorte
        sairia do lugar.
        """
        from l2scanner.frames import Regiao

        cal = self._calibracao(
            party_window_na_janela=Regiao(
                esquerda=0, topo=0, largura=120, altura=400
            )
        )

        r = cal.regiao_do_banner(na_janela=True)

        assert r.esquerda >= 0 and r.topo >= 0

    def test_a_calibracao_v2_antiga_carrega_sem_a_chave_nova(self, tmp_path):
        from l2scanner.calibracao import Calibracao
        from l2scanner.frames import Regiao

        caminho = tmp_path / "calibration.json"
        self._calibracao().salvar(caminho)
        assert Calibracao.carregar(caminho).banner_manutencao is None

        minha = Regiao(esquerda=5, topo=6, largura=700, altura=60)
        self._calibracao(banner_manutencao=minha).salvar(caminho)
        assert Calibracao.carregar(caminho).banner_manutencao == minha

    def test_a_versao_do_esquema_nao_mudou(self):
        """Um bump forcaria o usuario a recalibrar por causa de um campo opcional.

        O `carregar` recusa qualquer versao diferente da constante, entao subir
        para 3 invalidaria o `calibration.json` REAL que ele mediu a mao — pelo
        preco de nada.
        """
        from l2scanner import calibracao as modulo

        assert modulo.VERSAO_DO_ESQUEMA == 2


class TestMontagemNoArranque:
    """Ligar ou nao o recurso e LOGICA, e logica precisa de teste.

    Mesmo morando no `__main__`, que e a camada de 20% de cobertura onde todos
    os bugs de integracao deste projeto ja moraram.
    """

    def _regiao(self):
        from l2scanner.frames import Regiao

        return Regiao(esquerda=10, topo=10, largura=600, altura=120)

    def test_sem_ocr_devolve_none_e_avisa_em_warning(self, monkeypatch, caplog):
        """Silencio aqui seria o pior desfecho (D-02).

        O usuario acharia que esta coberto contra a manutencao e nao esta — e
        so descobriria na proxima queda do servidor, que e exatamente a
        situacao que este recurso existe para evitar.
        """
        import logging

        from l2scanner import __main__ as principal
        from l2scanner import ocr

        monkeypatch.setattr(ocr, "disponivel", lambda: False)
        monkeypatch.setattr(ocr, "motivo_indisponivel", lambda: "faltam as bindings")

        with caplog.at_level(logging.INFO, logger="l2scanner"):
            assert principal.montar_vigia_de_manutencao(self._regiao()) is None

        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_sem_regiao_devolve_none(self, monkeypatch):
        """D-07: sem pixels nao ha o que ler, mesmo com o OCR funcionando."""
        from l2scanner import __main__ as principal
        from l2scanner import ocr

        monkeypatch.setattr(ocr, "disponivel", lambda: True)

        assert principal.montar_vigia_de_manutencao(None) is None

    def test_com_ocr_e_regiao_devolve_o_vigia_ligado_no_ocr(self, monkeypatch):
        from l2scanner import __main__ as principal
        from l2scanner import ocr
        from l2scanner.manutencao import VigiaDeManutencao

        monkeypatch.setattr(ocr, "disponivel", lambda: True)

        vigia = principal.montar_vigia_de_manutencao(self._regiao())

        assert isinstance(vigia, VigiaDeManutencao)
        assert vigia._ler_texto is ocr.ler_texto
        assert vigia._ler_texto_conferencia is ocr.ler_texto_ampliado
