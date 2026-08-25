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
# Todos vieram da fixture REAL `tests/fixtures/manutencao/banner_40min26s.png`
# (360x135, fonte do jogo, verdade na tela = 40 minutos e 26 segundos), cada um
# de uma passada diferente do motor do Windows:
#
#   BANNER_REAL       — cinza 1x e cinza 3x/4x (as passadas que ACERTAM)
#   TEXTO_EMBARALHADO — a imagem em COR, sem converter para cinza
#   TEXTO_GRUDADO     — cinza 2x
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

# Cinza 2x: a unidade sobreviveu, mas grudada no numero e com `m` virando `n`.
TEXTO_GRUDADO = (
    "12 Server Maintence 40ninutes 26 seconds "
    "Please avoid entering instance ( 3>YKorzis"
)

# Cinza 1x, o caso bom — e o alvo do que a conversao para cinza (D-a) entrega.
TEXTO_LIMPO = (
    "12 Server Maintence 40 minutes 26 seconds "
    "Please avoid entering instance Korzis O' Kaus"
)

HOJE = datetime(2026, 8, 25, 14, 0, 0)


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

        faltam5 = chave_do_marcador(HOJE, TipoDeAvisoDeManutencao.FALTAM5)
        assert faltam5 != a


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

    def test_uma_manutencao_remarcada_re_ancora_com_duas_leituras(self):
        """A ancora anterior nao pode prender o vigia num horario que sumiu."""
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
        assert [a.tipo for a in saiu] == [TipoDeAvisoDeManutencao.ANUNCIADA]


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
        """D-e, o orcamento inteiro deste recurso.

        A barata custa 44 ms medidos e a cara 308 ms. Em regime permanente — que
        e o dia inteiro, com o banner ausente — so a barata pode rodar.
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


class TestAncoraSobreviveACegueira:
    """O coracao de D-10, e a razao inteira de a ancora existir."""

    def _ancorar(self, vigia, leitor, obter, texto):
        leitor.texto = texto
        saiu = vigia.avaliar(obter, HOJE)
        saiu += vigia.avaliar(obter, HOJE + timedelta(seconds=5))
        return saiu

    def test_o_aviso_de_5_minutos_sai_com_o_ocr_devolvendo_none_depois(self):
        """GOAL-02 sobrevive ao banner sumir, ao jogo coberto e ao alt-tab.

        Sem a ancora, o segundo aviso dependeria de uma leitura bem sucedida no
        instante exato — e manutencao e justamente quando o cliente comeca a
        engasgar e a leitura falha. E o unico teste deste arquivo que prova o
        motivo de a ancora existir.
        """
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()
        self._ancorar(vigia, leitor, obter, "Server Maintence 8 minutes")
        assert vigia.momento is not None

        leitor.texto = None  # o banner sumiu; o OCR nao le mais nada
        antes = leitor.chamadas
        momento = vigia.momento

        saiu = rodar(vigia, obter, HOJE + timedelta(seconds=6), segundos=4 * 60)

        assert [a.tipo for a in saiu] == [TipoDeAvisoDeManutencao.FALTAM5]
        assert momento.strftime("%H:%M") in saiu[0].texto
        assert leitor.chamadas > antes, "o OCR rodou, so nao leu nada util"

    def test_os_dois_avisos_saem_quando_o_scanner_sobe_com_pouco_tempo(self):
        """E o FALTAM5 diz 3 minutos, nao 5 — o aviso nunca mente sobre o tempo."""
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()

        saiu = self._ancorar(vigia, leitor, obter, "Server Maintence 3 minutes")

        assert [a.tipo for a in saiu] == [
            TipoDeAvisoDeManutencao.ANUNCIADA,
            TipoDeAvisoDeManutencao.FALTAM5,
        ]
        assert "3 minutos" in saiu[1].texto
        assert "5 minutos" not in saiu[1].texto

    def test_cada_tipo_sai_uma_vez_so(self):
        vigia, leitor = novo_vigia()
        obter = PixelsFalsos()
        saiu = self._ancorar(vigia, leitor, obter, "Server Maintence 6 minutes")
        leitor.texto = None

        saiu += rodar(vigia, obter, HOJE + timedelta(seconds=6), segundos=200)

        tipos = [a.tipo for a in saiu]
        assert tipos.count(TipoDeAvisoDeManutencao.ANUNCIADA) == 1
        assert tipos.count(TipoDeAvisoDeManutencao.FALTAM5) == 1


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
