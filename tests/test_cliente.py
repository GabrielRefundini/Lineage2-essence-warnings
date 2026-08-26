"""O cliente caiu — tela de login ou desconexao — e isso e um EVENTO.

Ate 2026-08-24 o scanner so sabia dizer "sem visao da party", e essa frase
cobria coisas muito diferentes: o jogo coberto por outra janela, um menu aberto
por cima, o servidor em manutencao, e o cliente de volta na tela de login.

Naquele dia o servidor entrou em manutencao e o scanner passou 90 s, e depois
5 min, repetindo "sem visao" sem nunca dizer o motivo. Os dois silencios estao
no `outbox.jsonl`. Cegueira com causa conhecida nao e cegueira: e um evento, e
e o evento que explica todos os silencios que vierem depois dele.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

from l2scanner.cliente import (
    FAIXA_DO_DIALOGO,
    EstadoDoCliente,
    carregar_template,
    casar_dialogo,
    esta_na_tela_de_login,
    estado_do_cliente,
    nome_do_personagem,
)
from l2scanner.notificador import formatar, formatar_console
from l2scanner.rastreador import Ajustes, Evento, Rastreador, TipoDeEvento
from l2scanner.visao import EstadoDaLinha, LeituraDeLinha, Observacao

FIXTURES = Path(__file__).parent / "fixtures" / "cliente"
FIXTURES_DE_GAMEPLAY = Path(__file__).parent / "fixtures" / "gameplay"
FAIXA_DE_GAMEPLAY = "faixa_com_inventario.png"

# A janela real do cliente do usuario, de onde a fixture de gameplay foi
# recortada: altura x largura, na ordem de `ndarray.shape`. O tripwire da
# geometria refaz a conta da faixa a partir daqui.
JANELA_MEDIDA = (1392, 1720)


class TestTituloDaJanela:
    """O titulo e o sinal mais confiavel do projeto: texto do Windows.

    Sem limiar, sem HSV, sem calibracao, e nao quebra quando o usuario muda a
    resolucao. Verificado ao vivo com as duas instancias do usuario abertas ao
    mesmo tempo: 'Faerlina - XM Essence' (jogando) e 'XM Essence' (login).
    """

    @pytest.mark.parametrize(
        "titulo",
        ["XM Essence", "  XM Essence  ", "XM Essence "],
    )
    def test_titulo_sem_personagem_e_tela_de_login(self, titulo):
        assert esta_na_tela_de_login(titulo)

    @pytest.mark.parametrize(
        "titulo",
        [
            "Yazalaque - XM Essence",
            "Faerlina - XM Essence",
            "J4guar - XM Essence",
        ],
    )
    def test_titulo_com_personagem_nao_e_tela_de_login(self, titulo):
        assert not esta_na_tela_de_login(titulo)

    def test_endswith_seria_errado(self):
        """`endswith` casaria a janela do JOGO e inverteria a deteccao."""
        assert "Faerlina - XM Essence".endswith("XM Essence")
        assert not esta_na_tela_de_login("Faerlina - XM Essence")

    def test_titulo_ausente_nao_decide_nada(self):
        assert not esta_na_tela_de_login(None)
        assert not esta_na_tela_de_login("")

    def test_extrai_o_personagem(self):
        assert nome_do_personagem("Yazalaque - XM Essence") == "Yazalaque"
        assert nome_do_personagem("XM Essence") is None
        assert nome_do_personagem(None) is None


class TestTemplateDoDialogo:
    def test_o_template_esta_no_pacote(self):
        """Sem ele a deteccao de desconexao nao existe."""
        assert carregar_template() is not None

    def test_casa_o_dialogo_real(self):
        """Contra o frame capturado da desconexao de verdade."""
        recorte = cv2.imread(str(FIXTURES / "dialogo_desconexao_recorte.png"))
        assert recorte is not None
        pontuacao = casar_dialogo(recorte, carregar_template())
        assert pontuacao is not None
        assert pontuacao >= 0.99, f"casou apenas {pontuacao:.4f}"

    def test_frame_menor_que_o_template_e_nao_sei(self):
        """`None` e 'nao sei', nunca 0.0.

        Confundir os dois faz o scanner anunciar o contrario do que ve.
        """
        import numpy as np

        minusculo = np.zeros((5, 5, 3), dtype=np.uint8)
        assert casar_dialogo(minusculo, carregar_template()) is None

    def test_sem_template_nao_afirma_desconexao(self):
        assert casar_dialogo(None, None) is None
        estado = estado_do_cliente("Yazalaque - XM Essence", None, None)
        assert estado is EstadoDoCliente.EM_JOGO


class TestOTemplateContraGameplayNormal:
    """O negativo que faltava: o frame contra o qual o scanner roda 99% do tempo.

    Ate hoje o template do dialogo so tinha sido medido contra o positivo real
    (0.9997) e contra a tela de login (0.5051). Nunca contra a janela do jogo
    RODANDO NORMAL — que e, justamente, o frame que o scanner ve o dia inteiro.
    "O risco e baixo porque terreno com textura nao se parece com uma caixa
    cinza" era INFERENCIA, e a regra do projeto e explicita: nada de limiar no
    chute.

    MEDIDO em 2026-08-26, n=10 frames de janela inteira 1720x1392, capturados
    da tela do usuario com o jogo rodando:

        score minimo              0.3068
        score maximo              0.4662
        limiar de producao        0.90
        margem no pior frame      0.4338

    Os 10 frames incluem o pior negativo que o jogo produz naturalmente:
    INVENTARIO E MERCADO ABERTOS ao mesmo tempo — que sao literalmente caixas
    cinzas com botoes, a coisa na tela mais parecida com o dialogo. Mesmo esse
    ficou na METADE do limiar.

    Por que so a FAIXA foi guardada, e nao a janela inteira: 464 KB contra
    3,6 MB (as fixtures do projeto ficam entre 76 KB e 192 KB), com o score
    PRESERVADO — 0.4618 na faixa, identico ao da janela inteira, porque a busca
    de producao ja acontece dentro da faixa. E o recorte cumpre o passo 4 da
    propria pendencia: o chat, que fica embaixo a esquerda com nomes e
    mensagens de outros jogadores, cai FORA da faixa central.
    """

    def test_gameplay_normal_com_inventario_aberto_nao_casa(self):
        """O pior negativo real fica na metade do limiar. Medido: 0.4618.

        `cv2.matchTemplate` e chamado DIRETO, e nao `casar_dialogo`, porque a
        fixture JA E a faixa de busca: `casar_dialogo` recortaria uma faixa DA
        FAIXA e mediria outra regiao (ver o terceiro teste desta classe).
        """
        faixa = cv2.imread(str(FIXTURES_DE_GAMEPLAY / FAIXA_DE_GAMEPLAY))
        assert faixa is not None
        template = carregar_template()
        assert template is not None

        pontuacao = float(
            cv2.matchTemplate(faixa, template, cv2.TM_CCOEFF_NORMED).max()
        )
        # O criterio de aceite escrito pela propria pendencia de 2026-08-24.
        assert pontuacao < 0.70, f"casou {pontuacao:.4f}"
        # E a folga ate o limiar de producao, que e o que de fato protege.
        assert 0.90 - pontuacao > 0.40, f"folga de {0.90 - pontuacao:.4f}"

    def test_a_fixture_e_exatamente_a_faixa_de_busca(self):
        """Tripwire: a medicao acima so vale enquanto a faixa for ESTA.

        Alargar `FAIXA_DO_DIALOGO` sem remedir deixaria o teste anterior verde
        medindo uma regiao que o scanner nao usa mais — verde MENTINDO. A conta
        e escrita aqui de proposito, em vez dos numeros prontos: ela e a mesma
        que `casar_dialogo` faz sobre a janela real.
        """
        altura, largura = JANELA_MEDIDA
        fx0, fy0, fx1, fy1 = FAIXA_DO_DIALOGO
        esperado = (
            int(altura * fy1) - int(altura * fy0),
            int(largura * fx1) - int(largura * fx0),
        )

        faixa = cv2.imread(str(FIXTURES_DE_GAMEPLAY / FAIXA_DE_GAMEPLAY))
        assert faixa is not None
        assert faixa.shape[:2] == esperado, (
            f"a fixture e {faixa.shape[:2]}, mas FAIXA_DO_DIALOGO sobre "
            f"{JANELA_MEDIDA} da {esperado} — remedir antes de mexer na faixa"
        )

    def test_casar_dialogo_sobre_a_faixa_mede_uma_regiao_menor(self):
        """A armadilha, registrada como teste para ninguem cair nela de novo.

        `casar_dialogo` calcula a faixa A PARTIR do que recebe. Entregar a ele
        a faixa ja recortada faz ele recortar uma faixa DA FAIXA: as posicoes
        candidatas viram um SUBCONJUNTO das anteriores, entao o maximo so pode
        CAIR. Medido: 0.3586 contra 0.4618 do `matchTemplate` direto.

        Por isso a faixa-da-faixa nao serve como medicao — ela travaria um
        numero otimista por acidente, e o otimismo estaria do lado errado.
        """
        faixa = cv2.imread(str(FIXTURES_DE_GAMEPLAY / FAIXA_DE_GAMEPLAY))
        template = carregar_template()

        direto = float(
            cv2.matchTemplate(faixa, template, cv2.TM_CCOEFF_NORMED).max()
        )
        faixa_da_faixa = casar_dialogo(faixa, template)
        assert faixa_da_faixa is not None

        assert faixa_da_faixa <= direto, (
            f"recortar duas vezes mediu MAIS ({faixa_da_faixa:.4f} contra "
            f"{direto:.4f}) — a conta da faixa mudou"
        )
        assert direto < 0.70, f"matchTemplate direto casou {direto:.4f}"
        assert faixa_da_faixa < 0.70, f"casou {faixa_da_faixa:.4f}"


class TestEstadoDoCliente:
    def test_login_vence_o_dialogo(self):
        """Um dialogo aberto NA tela de login ainda e tela de login.

        O titulo e prova; o template e evidencia. Prova vence.
        """
        recorte = cv2.imread(str(FIXTURES / "dialogo_desconexao_recorte.png"))
        assert (
            estado_do_cliente("XM Essence", recorte, carregar_template())
            is EstadoDoCliente.TELA_DE_LOGIN
        )

    def test_dialogo_com_titulo_de_jogo_e_desconectado(self):
        """O caso que MAIS importa: AFK e desconectado.

        Com o dialogo aberto o cliente continua se chamando
        'Faerlina - XM Essence' — pela janela ele ainda esta no jogo. Se o
        usuario esta AFK, o dialogo fica parado na tela para sempre e o titulo
        nunca muda. Sem o template, isso e silencio permanente.
        """
        recorte = cv2.imread(str(FIXTURES / "dialogo_desconexao_recorte.png"))
        assert (
            estado_do_cliente(
                "Faerlina - XM Essence", recorte, carregar_template()
            )
            is EstadoDoCliente.DESCONECTADO
        )

    def test_sem_titulo_e_desconhecido(self):
        """Janela fechada nao e 'caiu' — e 'nao sei'."""
        assert estado_do_cliente(None) is EstadoDoCliente.DESCONHECIDO


def _obs(estado, ui=True, nomes=("Kaus", "Korzis")):
    linhas = tuple(
        LeituraDeLinha(
            i, EstadoDaLinha.COM_MEMBRO, 1.0, 1.0, nome=n, confianca_do_nome=0.98
        )
        for i, n in enumerate(nomes)
    )
    return Observacao(0, ui, linhas, hp_proprio=1.0, estado_do_cliente=estado)


def _novo():
    return Rastreador(
        nomes=["Kaus", "Korzis"],
        nome_proprio="Yazalaque",
        ajustes=Ajustes(
            confirmacoes_para_jogo_caiu=2, confirmacoes_para_jogo_voltou=4
        ),
    )


def _alimentar(r, obs, vezes, inicio=0.0):
    eventos = []
    for i in range(vezes):
        eventos.extend(r.observar(obs, inicio + i))
    return eventos


class TestRastreadorAnunciaAQueda:
    def test_queda_para_a_tela_de_login_avisa(self):
        r = _novo()
        _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 10)

        eventos = _alimentar(
            r, _obs(EstadoDoCliente.TELA_DE_LOGIN, ui=False, nomes=()), 6, 100
        )
        quedas = [e for e in eventos if e.tipo is TipoDeEvento.JOGO_CAIU]
        assert len(quedas) == 1
        assert quedas[0].detalhe == "tela de login"

    def test_desconexao_avisa_com_o_motivo_certo(self):
        r = _novo()
        _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 10)

        eventos = _alimentar(
            r, _obs(EstadoDoCliente.DESCONECTADO, ui=False, nomes=()), 6, 100
        )
        quedas = [e for e in eventos if e.tipo is TipoDeEvento.JOGO_CAIU]
        assert len(quedas) == 1
        assert quedas[0].detalhe == "desconectado do servidor"

    def test_avisa_uma_vez_so(self):
        """Meia hora de manutencao nao vira meia hora de mensagens."""
        r = _novo()
        _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 10)

        eventos = _alimentar(
            r, _obs(EstadoDoCliente.TELA_DE_LOGIN, ui=False, nomes=()), 300, 100
        )
        assert len([e for e in eventos if e.tipo is TipoDeEvento.JOGO_CAIU]) == 1

    def test_a_volta_avisa(self):
        r = _novo()
        _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 10)
        _alimentar(
            r, _obs(EstadoDoCliente.TELA_DE_LOGIN, ui=False, nomes=()), 10, 100
        )

        eventos = _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 10, 500)
        voltas = [e for e in eventos if e.tipo is TipoDeEvento.JOGO_VOLTOU]
        assert len(voltas) == 1

    def test_jogo_caido_nao_gera_evento_de_party(self):
        """O silencio passa a ter nome, e nada mais e inventado.

        Com o jogo caido a party window nao esta escondida: ela nao existe.
        Deixar as avaliacoes de party rodarem produziria "voce saiu da party"
        e "fulano saiu" a partir de uma tela de login.
        """
        r = _novo()
        _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 15)

        eventos = _alimentar(
            r, _obs(EstadoDoCliente.TELA_DE_LOGIN, ui=False, nomes=()), 200, 100
        )
        proibidos = {
            TipoDeEvento.SAIU,
            TipoDeEvento.VOCE_SEM_PARTY,
            TipoDeEvento.MORREU,
            TipoDeEvento.CEGUEIRA_LONGA,
        }
        vazou = [e.tipo.value for e in eventos if e.tipo in proibidos]
        assert vazou == [], f"o jogo caiu, mas vazou: {vazou}"

    def test_comeco_frio_com_o_jogo_ja_caido_nao_avisa(self):
        """Ligar o scanner com o jogo na tela de login nao e uma queda.

        O usuario esta olhando para a tela — ele sabe.
        """
        r = _novo()
        eventos = _alimentar(
            r, _obs(EstadoDoCliente.TELA_DE_LOGIN, ui=False, nomes=()), 20
        )
        assert [e for e in eventos if e.tipo is TipoDeEvento.JOGO_CAIU] == []

    def test_comeco_frio_nao_anuncia_volta_no_primeiro_login(self):
        """O espelho: sem queda anunciada, nao ha volta a anunciar."""
        r = _novo()
        _alimentar(r, _obs(EstadoDoCliente.TELA_DE_LOGIN, ui=False, nomes=()), 20)

        eventos = _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 15, 100)
        assert [e for e in eventos if e.tipo is TipoDeEvento.JOGO_VOLTOU] == []

    def test_sem_o_sinal_o_comportamento_antigo_e_preservado(self):
        """Quem nao passa `estado_do_cliente` nao muda de comportamento."""
        r = _novo()
        obs_sem = Observacao(
            0,
            True,
            (
                LeituraDeLinha(
                    0, EstadoDaLinha.COM_MEMBRO, 1.0, 1.0, "Kaus", 0.98
                ),
            ),
            hp_proprio=1.0,
        )
        eventos = _alimentar(r, obs_sem, 20)
        do_cliente = [
            e
            for e in eventos
            if e.tipo in (TipoDeEvento.JOGO_CAIU, TipoDeEvento.JOGO_VOLTOU)
        ]
        assert do_cliente == []

    def test_desconhecido_congela_em_vez_de_concluir(self):
        r = _novo()
        _alimentar(r, _obs(EstadoDoCliente.EM_JOGO), 10)
        eventos = _alimentar(r, _obs(EstadoDoCliente.DESCONHECIDO), 50, 100)
        assert [e for e in eventos if e.tipo is TipoDeEvento.JOGO_CAIU] == []


class TestMensagens:
    def _ev(self, tipo, detalhe=None):
        return Evento(
            tipo=tipo, momento=1787600000.0, membro="Yazalaque", detalhe=detalhe
        )

    def test_whatsapp_diz_o_motivo(self):
        texto = formatar(self._ev(TipoDeEvento.JOGO_CAIU, "tela de login"))
        assert "tela de login" in texto
        assert "Yazalaque" in texto

    def test_whatsapp_distingue_desconexao_de_login(self):
        desc = formatar(
            self._ev(TipoDeEvento.JOGO_CAIU, "desconectado do servidor")
        )
        assert "desconectado do servidor" in desc
        assert "tela de login" not in desc

    def test_a_volta_tem_mensagem_propria(self):
        texto = formatar(self._ev(TipoDeEvento.JOGO_VOLTOU))
        assert "voltou" in texto.lower()

    def test_console_nao_cai_no_texto_generico(self):
        """Sem tratamento explicito sairia 'JOGO_CAIU', que nao ajuda ninguem."""
        linha = formatar_console(self._ev(TipoDeEvento.JOGO_CAIU, "tela de login"))
        assert "JOGO_CAIU" not in linha
        assert "TELA DE LOGIN" in linha


class TestVigiaDoCliente:
    """A cadencia da busca cara, agora testavel.

    Esta logica morava no `JanelaSource`, num modulo de 19% de cobertura que so
    um jogo aberto consegue exercitar — a mesma camada onde os tres warnings do
    code review moravam. Foi movida para ca justamente por isso.

    Medido: o titulo custa ~0,001 ms e o matchTemplate ~45 ms, contra 0,7 ms de
    toda a analise da party window. A 1 Hz o template sozinho seria ~98% do CPU
    do scanner, para procurar um evento que acontece uma vez por manutencao.
    """

    def _vigia(self, casa_o_dialogo, intervalo=5.0):
        """Vigia com um template falso e um casamento controlado."""
        import numpy as np

        from l2scanner.cliente import VigiaDoCliente

        vigia = VigiaDoCliente(
            template=np.zeros((2, 2, 3), dtype=np.uint8),
            segundos_entre_buscas=intervalo,
        )
        # O que importa e a CADENCIA, entao trocamos a medicao por um valor fixo
        vigia._contagem = 0

        def falso(pixels, template):
            vigia._contagem += 1
            return 0.99 if casa_o_dialogo else 0.10

        import l2scanner.cliente as mod

        vigia._original = mod.casar_dialogo
        mod.casar_dialogo = falso
        return vigia, mod

    def _restaurar(self, vigia, mod):
        mod.casar_dialogo = vigia._original

    def test_a_busca_cara_nao_roda_a_cada_tick(self):
        vigia, mod = self._vigia(casa_o_dialogo=False, intervalo=5.0)
        try:
            for tick in range(10):  # 10 segundos, 1 Hz
                vigia.avaliar("Faerlina - XM Essence", lambda: object(), float(tick))
            assert vigia._contagem == 2, (
                f"buscou {vigia._contagem} vezes em 10s; esperado 2 (a cada 5s)"
            )
        finally:
            self._restaurar(vigia, mod)

    def test_o_titulo_e_avaliado_a_cada_tick_mesmo_assim(self):
        """A tela de login nao pode esperar cinco segundos.

        O titulo custa microssegundos — nao ha motivo para atrasar.
        """
        from l2scanner.cliente import EstadoDoCliente

        vigia, mod = self._vigia(casa_o_dialogo=False)
        try:
            vigia.avaliar("Faerlina - XM Essence", lambda: object(), 0.0)
            # 1 segundo depois, MUITO antes da proxima busca cara
            estado = vigia.avaliar("XM Essence", lambda: object(), 1.0)
            assert estado is EstadoDoCliente.TELA_DE_LOGIN
        finally:
            self._restaurar(vigia, mod)

    def test_o_veredito_de_desconexao_GRUDA_entre_buscas(self):
        """Sem isto o debounce do rastreador nunca fecharia.

        O estado oscilaria DESCONECTADO/EM_JOGO a cada tick, as confirmacoes
        nunca chegariam a 2 seguidas, e o alerta simplesmente nao sairia.
        """
        from l2scanner.cliente import EstadoDoCliente

        vigia, mod = self._vigia(casa_o_dialogo=True, intervalo=5.0)
        try:
            estados = [
                vigia.avaliar("Faerlina - XM Essence", lambda: object(), float(t))
                for t in range(5)
            ]
            assert all(e is EstadoDoCliente.DESCONECTADO for e in estados), estados
            assert vigia._contagem == 1, "buscou mais de uma vez em 5 segundos"
        finally:
            self._restaurar(vigia, mod)

    def test_a_primeira_chamada_sempre_busca(self):
        """Subir o scanner com o dialogo ja na tela tem que detectar na hora."""
        from l2scanner.cliente import EstadoDoCliente

        vigia, mod = self._vigia(casa_o_dialogo=True)
        try:
            estado = vigia.avaliar("Faerlina - XM Essence", lambda: object(), 0.0)
            assert estado is EstadoDoCliente.DESCONECTADO
            assert vigia._contagem == 1
        finally:
            self._restaurar(vigia, mod)

    def test_os_pixels_so_sao_pedidos_quando_a_busca_vence(self):
        """Passar um chamavel e o que faz a cadencia valer a pena.

        Nos ticks sem busca, o frame nem chega a ser copiado.
        """
        vigia, mod = self._vigia(casa_o_dialogo=False, intervalo=5.0)
        pedidos = []
        try:
            for tick in range(5):
                vigia.avaliar(
                    "Faerlina - XM Essence",
                    lambda t=tick: pedidos.append(t) or object(),
                    float(tick),
                )
            assert pedidos == [0], f"pixels pedidos em {pedidos}, esperado so no 0"
        finally:
            self._restaurar(vigia, mod)

    def test_voltar_para_o_login_limpa_o_veredito_grudado(self):
        """Senao um dialogo antigo sobreviveria a volta ao login."""
        from l2scanner.cliente import EstadoDoCliente

        vigia, mod = self._vigia(casa_o_dialogo=True, intervalo=100.0)
        try:
            assert (
                vigia.avaliar("Faerlina - XM Essence", lambda: object(), 0.0)
                is EstadoDoCliente.DESCONECTADO
            )
            assert (
                vigia.avaliar("XM Essence", lambda: object(), 1.0)
                is EstadoDoCliente.TELA_DE_LOGIN
            )
            # de volta ao jogo, e o dialogo velho nao pode ressuscitar
            assert (
                vigia.avaliar("Faerlina - XM Essence", lambda: object(), 2.0)
                is EstadoDoCliente.EM_JOGO
            )
        finally:
            self._restaurar(vigia, mod)

    def test_sem_titulo_e_desconhecido_sem_gastar_a_busca(self):
        from l2scanner.cliente import EstadoDoCliente

        vigia, mod = self._vigia(casa_o_dialogo=True)
        try:
            assert vigia.avaliar(None, lambda: object(), 0.0) is (
                EstadoDoCliente.DESCONHECIDO
            )
            assert vigia._contagem == 0
        finally:
            self._restaurar(vigia, mod)
