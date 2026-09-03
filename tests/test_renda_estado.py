"""A camada de VALOR da cegueira: quatro estados, e o quinto caso que os fecha.

O QUE ESTE ARQUIVO EXISTE PARA IMPEDIR
======================================
**Que "nao vejo" e "vejo e nao mudou" virem a mesma palavra na tela.**

As duas coisas produzem consequencias OPOSTAS no disco -- a cegueira SUSPENDE a
gravacao (CEGO-01) e o parado GRAVA normalmente (CEGO-02, CTX-3) --, e as 4 da
manha a diferenca entre elas e a unica coisa que o usuario precisa saber.

E HA UM TERCEIRO FATO QUE NAO PODE COLAPSAR NOS OUTROS DOIS: "o valor nao foi
LIDO". Medido na Fase 1: o nivel recusa em **79%** dos tiques e a adena em
**21%**. Um painel que contasse recusa como "parado" diria PARADO em quatro de
cada cinco tiques com o usuario matando mob -- e por isso a staleness e medida
sobre o **EXP**, que recusa em **0%**.

O QUINTO CASO, E ELE E O QUE UMA SOMA DE CONTADORES NAO PEGA
=============================================================
`EXP recusado ENQUANTO o nivel ou a adena SAEM`. Ele escapa dos quatro: nao e
pausa (o frame mostra o jogo), nao e "nenhum campo saiu" (a adena saiu), e o
rastreio nao tem o que dizer (nao houve valor novo). As duas consequencias de
deixa-lo cair sao erradas em direcoes OPOSTAS:

- quem estava PARADO **continua reportado PARADO**, com o programa ja nao lendo
  o campo sobre o qual "parado" e uma afirmacao;
- se o EXP recusar desde o PRIMEIRO tique, nao ha serie nenhuma e o estado cai
  em **LENDO para sempre** -- o pior dos dois, porque LENDO nao pede atencao.

O teste de exaustividade ("os contadores somam o total de tiques") passaria dos
dois jeitos, porque **algum** estado sempre sai. Ele prova que nenhum tique se
perde; ele nao prova que o tique recebeu o estado CERTO. Os portoes deste caso
sao os dois testes NOMINAIS aqui embaixo, um por consequencia errada.
"""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path

import pytest

from l2scanner.cliente import EstadoDoCliente
from l2scanner.frames import SaudeDoFrame
from l2scanner.renda_estado import (
    MOTIVO_DA_DESCONEXAO,
    MOTIVO_DA_JANELA_MINIMIZADA,
    MOTIVO_DA_JANELA_SUMIDA,
    MOTIVO_DA_TELA_DE_LOGIN,
    MOTIVO_DO_CONGELAMENTO,
    MOTIVO_DO_EXP_SEM_LEITURA,
    MOTIVO_DO_FRAME_PRETO,
    MOTIVO_DOS_CAMPOS_SEM_LEITURA,
    EstadoDaRenda,
    RastreioDoValor,
    classificar_a_visao,
    motivo_da_pausa,
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

FONTE_DO_MODULO = (
    Path(__file__).parent.parent / "l2scanner" / "renda_estado.py"
)

PERSONAGEM = "Faerlina"

# O limiar de todos os casos deste arquivo. Ele entra SEMPRE por parametro
# nomeado: um valor de fabrica seria a definicao de constante magica, e o
# portao `test_O_LIMIAR_NAO_TEM_VALOR_DE_FABRICA` existe para isso.
LIMIAR = 120.0


def campos_de(
    nivel: int | None = 68,
    exp_em_decimos: int | None = 480_075,
    adena: int | None = 23_986_985,
) -> CamposDaRenda:
    """`None` em qualquer campo vira RECUSA nomeada naquele campo.

    Os valores por omissao sao os MEDIDOS ao vivo em 2026-09-03, depois do
    level up da Faerlina: `nivel 68  EXP 48,0075%  adena 23.986.985`.
    """

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


def visao_de(
    rastreio: RastreioDoValor,
    campos: CamposDaRenda,
    carimbo: float,
    *,
    saude: SaudeDoFrame = SaudeDoFrame.OK,
    estado_do_cliente: EstadoDoCliente = EstadoDoCliente.EM_JOGO,
    minimizada: bool = False,
    limiar: float = LIMIAR,
):
    return classificar_a_visao(
        saude=saude,
        estado_do_cliente=estado_do_cliente,
        minimizada=minimizada,
        campos=campos,
        rastreio=rastreio,
        carimbo=carimbo,
        segundos_para_parado=limiar,
    )


# ---------------------------------------------------------------------------
# A PAUSA: o frame nao mostra o jogo, e CADA motivo tem o SEU conserto
# ---------------------------------------------------------------------------


class TestAPausaDeclarada:
    """Os seis motivos, e os seis textos sao SEIS porque o conserto e outro.

    A regra e a que `__main__.py:840-849` ja escreveu: *"SEM VISAO" e verdade
    mas nao ajuda; "JOGO CAIU - TELA DE LOGIN" diz o que fazer a respeito*.
    Fundir dois motivos faria dois consertos diferentes virarem a mesma
    mensagem.
    """

    def test_frame_preto_e_PAUSADO_e_o_aviso_diz_o_que_fazer(self):
        visao = visao_de(
            RastreioDoValor(),
            campos_de(),
            100.0,
            saude=SaudeDoFrame.FALHA_DE_CAPTURA,
        )
        assert visao.estado is EstadoDaRenda.PAUSADO
        assert visao.motivo == MOTIVO_DO_FRAME_PRETO
        assert "PAUSADO" in visao.texto
        assert "monitor" in visao.aviso.lower()

    def test_congelado_e_PAUSADO_e_o_aviso_nomeia_AS_DUAS_causas(self):
        """Captura morta com o jogo vivo e jogo travado pedem consertos opostos.

        O incidente medido em `recaptura.py:3-17` foi o primeiro: 33 minutos
        cegos com a janela viva na tela. Um aviso que so citasse "o jogo
        travou" mandaria o usuario reiniciar o jogo quando o problema era o
        objeto de captura.
        """
        visao = visao_de(
            RastreioDoValor(),
            campos_de(),
            100.0,
            saude=SaudeDoFrame.CONGELADO,
        )
        assert visao.estado is EstadoDaRenda.PAUSADO
        assert visao.motivo == MOTIVO_DO_CONGELAMENTO
        minusculo = visao.aviso.lower()
        assert "captura" in minusculo
        assert "renderiz" in minusculo

    def test_MINIMIZADA_vence_o_congelamento(self):
        """Quem minimizou sabe que minimizou, e "congelado" seria a palavra errada.

        Sem esta precedencia o painel esperaria ~30 s -- os
        `FRAMES_IDENTICOS_PARA_CONGELADO` -- para dizer a palavra errada sobre
        uma janela que o usuario acabou de minimizar (C-7).
        """
        visao = visao_de(
            RastreioDoValor(),
            campos_de(),
            100.0,
            saude=SaudeDoFrame.CONGELADO,
            minimizada=True,
        )
        assert visao.motivo == MOTIVO_DA_JANELA_MINIMIZADA

    def test_MINIMIZADA_vence_tambem_o_frame_preto_e_a_tela_de_login(self):
        visao = visao_de(
            RastreioDoValor(),
            campos_de(),
            100.0,
            saude=SaudeDoFrame.FALHA_DE_CAPTURA,
            estado_do_cliente=EstadoDoCliente.TELA_DE_LOGIN,
            minimizada=True,
        )
        assert visao.motivo == MOTIVO_DA_JANELA_MINIMIZADA

    def test_tela_de_login_e_PAUSADO_com_a_frase_acionavel(self):
        visao = visao_de(
            RastreioDoValor(),
            campos_de(),
            100.0,
            estado_do_cliente=EstadoDoCliente.TELA_DE_LOGIN,
        )
        assert visao.estado is EstadoDaRenda.PAUSADO
        assert visao.motivo == MOTIVO_DA_TELA_DE_LOGIN
        assert "JOGO CAIU" in visao.aviso

    def test_desconectado_e_PAUSADO_com_o_motivo_do_dialogo(self):
        visao = visao_de(
            RastreioDoValor(),
            campos_de(),
            100.0,
            estado_do_cliente=EstadoDoCliente.DESCONECTADO,
        )
        assert visao.estado is EstadoDaRenda.PAUSADO
        assert visao.motivo == MOTIVO_DA_DESCONEXAO

    def test_desconhecido_diz_que_a_JANELA_SUMIU(self):
        visao = visao_de(
            RastreioDoValor(),
            campos_de(),
            100.0,
            estado_do_cliente=EstadoDoCliente.DESCONHECIDO,
        )
        assert visao.estado is EstadoDaRenda.PAUSADO
        assert visao.motivo == MOTIVO_DA_JANELA_SUMIDA
        assert "janela" in visao.aviso.lower()

    def test_desconhecido_NAO_INVENTA_EVENTO(self):
        """`EstadoDoCliente.DESCONHECIDO` diz *"na duvida o scanner nao inventa
        nada"* (`cliente.py:68-69`). O texto tem de dizer "nao sei", e nunca
        "voce caiu" -- que e uma afirmacao sobre o servidor que ninguem mediu.
        """
        visao = visao_de(
            RastreioDoValor(),
            campos_de(),
            100.0,
            estado_do_cliente=EstadoDoCliente.DESCONHECIDO,
        )
        assert "JOGO CAIU" not in visao.aviso
        assert "desconect" not in visao.aviso.lower()

    def test_OS_SEIS_MOTIVOS_TEM_SEIS_TEXTOS_DIFERENTES(self):
        """Fundir dois faria dois consertos diferentes virarem a mesma mensagem."""
        casos = [
            dict(minimizada=True),
            dict(estado_do_cliente=EstadoDoCliente.TELA_DE_LOGIN),
            dict(estado_do_cliente=EstadoDoCliente.DESCONECTADO),
            dict(estado_do_cliente=EstadoDoCliente.DESCONHECIDO),
            dict(saude=SaudeDoFrame.FALHA_DE_CAPTURA),
            dict(saude=SaudeDoFrame.CONGELADO),
        ]
        visoes = [
            visao_de(RastreioDoValor(), campos_de(), 100.0, **caso)
            for caso in casos
        ]
        assert len({v.motivo for v in visoes}) == 6
        assert len({v.texto for v in visoes}) == 6
        assert len({v.aviso for v in visoes}) == 6

    def test_a_pausa_e_perguntavel_SEM_os_campos(self):
        """`motivo_da_pausa` e a metade barata e o classificador a consome.

        Ela existe separada para que o portao de cegueira seja demonstravel sem
        montar `CamposDaRenda` -- e para que a ordem das perguntas, que e por
        CUSTO e nao por gravidade, tenha um teste proprio.
        """
        assert (
            motivo_da_pausa(
                saude=SaudeDoFrame.OK,
                estado_do_cliente=EstadoDoCliente.EM_JOGO,
                minimizada=False,
            )
            is None
        )
        assert (
            motivo_da_pausa(
                saude=SaudeDoFrame.OK,
                estado_do_cliente=EstadoDoCliente.EM_JOGO,
                minimizada=True,
            )
            == MOTIVO_DA_JANELA_MINIMIZADA
        )

    def test_A_FONTE_SEM_O_METODO_NAO_PAUSA_O_LACO(self):
        """`None` e `DESCONHECIDO` sao fatos DIFERENTES, e por isso `None` existe.

        `DESCONHECIDO` e *"eu perguntei e o cliente nao respondeu"* -- a janela
        sumiu, e isso pausa. `None` e *"eu nao perguntei"*: a fonte nem tem o
        metodo (o caso do `MssSource`, protegido por `hasattr` em
        `sessao.py:468`). Colapsar os dois pausaria a sessao inteira de
        qualquer fonte que nao fosse `JanelaSource`.
        """
        assert (
            motivo_da_pausa(
                saude=SaudeDoFrame.OK, estado_do_cliente=None, minimizada=False
            )
            is None
        )
        assert (
            motivo_da_pausa(
                saude=SaudeDoFrame.OK,
                estado_do_cliente=EstadoDoCliente.DESCONHECIDO,
                minimizada=False,
            )
            == MOTIVO_DA_JANELA_SUMIDA
        )


# ---------------------------------------------------------------------------
# O FRAME MOSTRA O JOGO: entao a pergunta passa a ser sobre o VALOR
# ---------------------------------------------------------------------------


class TestOsTresFatosDoValor:
    def test_os_tres_campos_recusados_e_SEM_LEITURA_e_NAO_pausado(self):
        """Recusa e uma afirmacao sobre a MEDICAO; pausa e sobre a VISAO.

        Com o frame saudavel e o cliente em jogo, o scanner esta vendo: o que
        falhou foi o retangulo virar numero. Chamar isso de cegueira suspenderia
        a gravacao (CEGO-01) e apagaria a linha que carrega o motivo.
        """
        visao = visao_de(
            RastreioDoValor(),
            campos_de(nivel=None, exp_em_decimos=None, adena=None),
            100.0,
        )
        assert visao.estado is EstadoDaRenda.SEM_LEITURA
        assert visao.motivo == MOTIVO_DOS_CAMPOS_SEM_LEITURA
        assert "SEM LEITURA" in visao.texto
        for rotulo in ("nivel", "EXP", "adena"):
            assert rotulo in visao.texto

    def test_o_EXP_que_MUDOU_e_LENDO(self):
        rastreio = RastreioDoValor()
        visao_de(rastreio, campos_de(exp_em_decimos=480_075), 100.0)
        visao = visao_de(rastreio, campos_de(exp_em_decimos=480_085), 101.0)
        assert visao.estado is EstadoDaRenda.LENDO

    def test_LENDO_nao_carrega_texto_proprio(self):
        """A linha do tique continua calculando o texto dela no caso normal.

        E o que preserva o motivo da recusa na tela nos 79% de tiques em que o
        nivel recusa com o EXP subindo -- `estado_da_leitura` do `03-01` diz
        `nivel: campo-vazio`, e sobrescrever isso com a palavra `LENDO` trocaria
        a pista do conserto por uma palavra que nao ajuda.
        """
        visao = visao_de(RastreioDoValor(), campos_de(), 100.0)
        assert visao.estado is EstadoDaRenda.LENDO
        assert visao.texto is None

    def test_o_nivel_recusado_com_o_EXP_SUBINDO_continua_LENDO(self):
        """O caso de 79% dos tiques. E o teste que prova o Achado 5."""
        rastreio = RastreioDoValor()
        visao_de(rastreio, campos_de(nivel=None, exp_em_decimos=480_075), 100.0)
        visao = visao_de(
            rastreio, campos_de(nivel=None, exp_em_decimos=480_085), 101.0
        )
        assert visao.estado is EstadoDaRenda.LENDO
        assert visao.estado is not EstadoDaRenda.PARADO
        assert visao.estado is not EstadoDaRenda.SEM_LEITURA

    def test_bit_identico_ABAIXO_do_limiar_ainda_e_LENDO(self):
        rastreio = RastreioDoValor()
        visao_de(rastreio, campos_de(exp_em_decimos=480_075), 100.0)
        visao = visao_de(rastreio, campos_de(exp_em_decimos=480_075), 219.0)
        assert visao.estado is EstadoDaRenda.LENDO

    def test_bit_identico_ACIMA_do_limiar_e_PARADO_com_tempo_e_amostras(self):
        rastreio = RastreioDoValor()
        for segundo in range(0, 200):
            visao = visao_de(
                rastreio, campos_de(exp_em_decimos=480_075), 100.0 + segundo
            )
        assert visao.estado is EstadoDaRenda.PARADO
        assert "PARADO" in visao.texto
        # Os DOIS numeros: o tempo, que e o que o usuario quer saber, e a
        # contagem, que e a letra do CEGO-02 ("bit-identicos por N amostras").
        assert "3min" in visao.texto, visao.texto
        assert "200" in visao.texto, visao.texto


class TestAsTresSaidasDoRastreio:
    """"mudou", "nao mudou" e "nao sei" sao TRES fatos, e nao dois.

    E o mesmo argumento que separa `lacunas` de `recusadas_por_motivo` em
    `ContagemDaRenda` (`renda_conta.py:1197-1254`): *"'o scanner nao viu' e 'o
    scanner viu e recusou' pedem consertos OPOSTOS do usuario, e somar um no
    outro apaga a pergunta"*.
    """

    def test_a_recusa_NAO_ZERA_a_serie(self):
        """Uma recusa unica nao pode apagar dez minutos de evidencia de parado."""
        rastreio = RastreioDoValor()
        rastreio.observar(480_075, carimbo=100.0, segundos_para_parado=LIMIAR)
        rastreio.observar(None, carimbo=101.0, segundos_para_parado=LIMIAR)
        veredito = rastreio.observar(
            480_075, carimbo=300.0, segundos_para_parado=LIMIAR
        )
        assert veredito.parado
        assert veredito.segundos == pytest.approx(200.0)

    def test_a_recusa_NAO_INCREMENTA_a_serie(self):
        """Se incrementasse, a recusa viraria parado -- o defeito do Achado 5."""
        rastreio = RastreioDoValor()
        rastreio.observar(480_075, carimbo=100.0, segundos_para_parado=LIMIAR)
        for passo in range(1, 11):
            veredito = rastreio.observar(
                None, carimbo=100.0 + passo * 60.0, segundos_para_parado=LIMIAR
            )
        assert not veredito.parado, (
            "dez recusas seguidas viraram PARADO: a recusa foi somada na serie"
        )
        assert veredito.amostras == 1
        assert rastreio.sem_leitura_seguidas == 10

    def test_dez_recusas_entre_dois_EXPs_identicos_nao_cancelam_a_serie(self):
        rastreio = RastreioDoValor()
        rastreio.observar(480_075, carimbo=0.0, segundos_para_parado=LIMIAR)
        for passo in range(1, 11):
            rastreio.observar(
                None, carimbo=float(passo), segundos_para_parado=LIMIAR
            )
        veredito = rastreio.observar(
            480_075, carimbo=500.0, segundos_para_parado=LIMIAR
        )
        assert veredito.parado
        assert veredito.amostras == 2

    def test_o_EXP_voltando_a_mudar_ZERA_a_serie_no_mesmo_tique(self):
        rastreio = RastreioDoValor()
        rastreio.observar(480_075, carimbo=0.0, segundos_para_parado=LIMIAR)
        assert rastreio.observar(
            480_075, carimbo=500.0, segundos_para_parado=LIMIAR
        ).parado
        veredito = rastreio.observar(
            480_085, carimbo=501.0, segundos_para_parado=LIMIAR
        )
        assert not veredito.parado
        assert veredito.amostras == 1
        assert veredito.segundos == pytest.approx(0.0)

    def test_UM_ABATE_SOLITARIO_desfaz_o_parado(self):
        """O degrau de um abate mede 10 unidades (censo de 55 Hz,
        `renda_ponte.py:33-35`), e por isso `valor_atual == valor_anterior` e a
        comparacao INTEIRA: uma tolerancia aqui esconderia justamente o abate
        que prova que o usuario nao parou.
        """
        rastreio = RastreioDoValor()
        rastreio.observar(480_075, carimbo=0.0, segundos_para_parado=LIMIAR)
        assert not rastreio.observar(
            480_076, carimbo=500.0, segundos_para_parado=LIMIAR
        ).parado

    def test_uma_amostra_sozinha_NUNCA_e_parado(self):
        """"Bit-identicos por N amostras" precisa de DUAS para ser afirmavel."""
        rastreio = RastreioDoValor()
        assert not rastreio.observar(
            480_075, carimbo=0.0, segundos_para_parado=0.0
        ).parado

    def test_o_relogio_andando_para_tras_nao_produz_parado(self):
        rastreio = RastreioDoValor()
        rastreio.observar(480_075, carimbo=500.0, segundos_para_parado=LIMIAR)
        assert not rastreio.observar(
            480_075, carimbo=0.0, segundos_para_parado=LIMIAR
        ).parado

    def test_O_LIMIAR_NAO_TEM_VALOR_DE_FABRICA(self):
        """Um limiar por omissao e a definicao de constante magica.

        O molde e `test_O_FATOR_NAO_TEM_VALOR_DE_FABRICA`
        (`tests/test_renda_par.py:337-343`): a constante mora no LACO, com
        "ESCOLHA E NAO MEDICAO" escrito ao lado, e o modulo puro a recebe
        somente-nomeada.
        """
        rastreio = RastreioDoValor()
        with pytest.raises(TypeError):
            rastreio.observar(480_075, carimbo=0.0)
        with pytest.raises(TypeError):
            rastreio.observar(480_075, 0.0, LIMIAR)

    def test_o_classificador_tambem_exige_o_limiar_nomeado(self):
        with pytest.raises(TypeError):
            classificar_a_visao(
                saude=SaudeDoFrame.OK,
                estado_do_cliente=EstadoDoCliente.EM_JOGO,
                minimizada=False,
                campos=campos_de(),
                rastreio=RastreioDoValor(),
                carimbo=0.0,
            )

    def test_DUAS_INSTANCIAS_NAO_SE_ENXERGAM(self):
        """O estado e do OBJETO e nunca do modulo."""
        um, outro = RastreioDoValor(), RastreioDoValor()
        um.observar(480_075, carimbo=0.0, segundos_para_parado=LIMIAR)
        um.observar(480_075, carimbo=500.0, segundos_para_parado=LIMIAR)
        assert not outro.observar(
            480_075, carimbo=500.0, segundos_para_parado=LIMIAR
        ).parado


# ---------------------------------------------------------------------------
# O QUINTO CASO -- e os dois portoes sao NOMINAIS, e nao uma soma que fecha
# ---------------------------------------------------------------------------


class TestOExpRecusadoComOsOutrosCamposSaindo:
    """`SEM LEITURA (EXP)`: congela a serie SEM consumi-la.

    A serie nao zera (uma recusa nao e prova de que o usuario voltou a matar) e
    nao avanca (nao ha valor novo com que comparar). O estado reportado deixa de
    ser LENDO ou PARADO e passa a dizer que o campo da staleness nao esta
    saindo -- porque o EXP e o campo sobre o qual "parado" e uma AFIRMACAO, e
    dizer PARADO ali seria afirmar sobre um numero que nao foi lido.
    """

    def test_o_estado_e_SEM_LEITURA_com_o_motivo_do_EXP(self):
        rastreio = RastreioDoValor()
        visao = visao_de(
            rastreio, campos_de(exp_em_decimos=None, adena=23_986_985), 100.0
        )
        assert visao.estado is EstadoDaRenda.SEM_LEITURA
        assert visao.motivo == MOTIVO_DO_EXP_SEM_LEITURA
        assert "EXP" in visao.texto

    def test_A_PRIMEIRA_CONSEQUENCIA_ERRADA_o_PARADO_GRUDADO(self):
        """Uma serie ja em PARADO seguida de um tique com o EXP recusado e a
        adena LIDA **para** de reportar PARADO.

        Sem este ramo, a tela continuaria afirmando "PARADO ha 8min" com o
        programa ja nao lendo o EXP -- afirmando um fato que a medicao parou de
        sustentar.
        """
        rastreio = RastreioDoValor()
        visao_de(rastreio, campos_de(exp_em_decimos=480_075), 0.0)
        parado = visao_de(rastreio, campos_de(exp_em_decimos=480_075), 500.0)
        assert parado.estado is EstadoDaRenda.PARADO

        depois = visao_de(
            rastreio,
            campos_de(exp_em_decimos=None, adena=23_990_000),
            501.0,
        )
        assert depois.estado is not EstadoDaRenda.PARADO
        assert depois.estado is EstadoDaRenda.SEM_LEITURA
        assert depois.motivo == MOTIVO_DO_EXP_SEM_LEITURA

    def test_A_SEGUNDA_CONSEQUENCIA_ERRADA_o_LENDO_ETERNO(self):
        """O EXP recusando DESDE O PRIMEIRO tique, com a adena saindo, nao
        reporta LENDO em nenhum deles.

        Sem serie nenhuma nao ha veredito de rastreio, e o estado cairia em
        LENDO para sempre -- o pior dos dois, porque LENDO e o estado que nao
        pede atencao.
        """
        rastreio = RastreioDoValor()
        for tique in range(10):
            visao = visao_de(
                rastreio,
                campos_de(exp_em_decimos=None, adena=23_986_985 + tique),
                float(tique),
            )
            assert visao.estado is not EstadoDaRenda.LENDO, (
                f"tique {tique} caiu em LENDO com o EXP recusado"
            )
            assert visao.estado is EstadoDaRenda.SEM_LEITURA

    def test_a_serie_RETOMA_DE_ONDE_PAROU_quando_o_EXP_volta(self):
        """O `PARADO ha ...` volta correto, contando o tempo INTEIRO.

        A serie foi congelada e nao consumida: os segundos sao contados desde a
        ultima MUDANCA, e nao desde o retorno da leitura.
        """
        rastreio = RastreioDoValor()
        visao_de(rastreio, campos_de(exp_em_decimos=480_075), 0.0)
        for tique in range(1, 20):
            visao_de(
                rastreio,
                campos_de(exp_em_decimos=None, adena=23_986_985),
                float(tique),
            )
        volta = visao_de(rastreio, campos_de(exp_em_decimos=480_075), 300.0)
        assert volta.estado is EstadoDaRenda.PARADO
        assert "5min" in volta.texto, volta.texto

    def test_os_tres_recusados_ganham_o_motivo_dos_CAMPOS_e_nao_o_do_EXP(self):
        """O caso "nenhum campo saiu" vem ANTES, e o texto nomeia os tres.

        Os dois sao SEM LEITURA -- mesmo valor de enum, mesmo efeito no disco --
        e o que muda e o campo nomeado no texto. Um enum proprio faria a soma
        dos contadores ter cinco parcelas para tres tipos de conserto.
        """
        visao = visao_de(
            RastreioDoValor(),
            campos_de(nivel=None, exp_em_decimos=None, adena=None),
            100.0,
        )
        assert visao.motivo == MOTIVO_DOS_CAMPOS_SEM_LEITURA
        assert visao.motivo != MOTIVO_DO_EXP_SEM_LEITURA

    def test_os_dois_casos_de_SEM_LEITURA_dizem_textos_diferentes(self):
        so_o_exp = visao_de(
            RastreioDoValor(), campos_de(exp_em_decimos=None), 100.0
        )
        os_tres = visao_de(
            RastreioDoValor(),
            campos_de(nivel=None, exp_em_decimos=None, adena=None),
            100.0,
        )
        assert so_o_exp.texto != os_tres.texto

    def test_a_pausa_NAO_consome_a_serie(self):
        """Trinta frames congelados com os mesmos pixels devolveriam os mesmos
        numeros, e uma serie alimentada durante a cegueira sairia dela
        anunciando PARADO sobre um tempo em que ninguem estava vendo nada.
        """
        rastreio = RastreioDoValor()
        visao_de(rastreio, campos_de(exp_em_decimos=480_075), 0.0)
        for tique in range(1, 40):
            visao_de(
                rastreio,
                campos_de(exp_em_decimos=480_075),
                float(tique),
                saude=SaudeDoFrame.CONGELADO,
            )
        assert rastreio.amostras == 1
        volta = visao_de(rastreio, campos_de(exp_em_decimos=480_075), 40.0)
        assert volta.estado is EstadoDaRenda.LENDO


# ---------------------------------------------------------------------------
# OS PORTOES DE PUREZA -- por ARVORE e com controle positivo
# ---------------------------------------------------------------------------


def alcances_proibidos(caminho: Path) -> list[str]:
    """Relogio, log, tela e imagem, por AST -- e nunca por `grep`.

    A VARREDURA E POR ARVORE PORQUE UM `grep` ANCORADO NAO VE QUATRO DOS CINCO
    CAMINHOS. Medido no `<verify>` que esta funcao substituiu: ele nao via
    `import time`, nao via `from datetime import datetime`, nao via `print(` e
    nao via `from logging import getLogger`. Um portao fraco ao lado de um forte
    ensina que o fraco basta.

    `ast.Import` E `ast.ImportFrom` sao os dois, porque `import time` e
    `from time import monotonic` alcancam a MESMA coisa por sintaxes
    diferentes.
    """
    proibidos = {
        "time",
        "datetime",
        "logging",
        "cv2",
        "numpy",
        "np",
        ".captura_janela",
        "captura_janela",
    }
    arvore = ast.parse(Path(caminho).read_text(encoding="utf-8"))
    achados: list[str] = []

    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                raiz = alias.name.split(".")[0]
                if raiz in proibidos or alias.name in proibidos:
                    achados.append(f"linha {no.lineno}: import {alias.name}")
        elif isinstance(no, ast.ImportFrom):
            nome = ("." * (no.level or 0)) + (no.module or "")
            raiz = (no.module or "").split(".")[0]
            if nome in proibidos or raiz in proibidos:
                achados.append(f"linha {no.lineno}: from {nome} import ...")
        elif isinstance(no, ast.Call):
            if getattr(no.func, "id", None) == "print":
                achados.append(f"linha {no.lineno}: print(...)")

    return achados


def memoria_de_modulo(caminho: Path) -> list[str]:
    """`global` e literal mutavel de nivel de modulo -- o portao da Fase 1.

    Copiado de `tests/test_renda_par.py:573-600`, e ele passa a varrer
    `renda_estado.py` tambem: o estado do rastreio e do OBJETO, e um acumulador
    de modulo faria duas sessoes do scanner se enxergarem.
    """
    arvore = ast.parse(Path(caminho).read_text(encoding="utf-8"))
    achados: list[str] = []

    for no in ast.walk(arvore):
        if isinstance(no, ast.Global):
            achados.append(f"linha {no.lineno}: global {', '.join(no.names)}")

    for no in arvore.body:
        if not isinstance(no, (ast.Assign, ast.AnnAssign)):
            continue
        if isinstance(no.value, (ast.List, ast.Dict, ast.Set)):
            alvos = no.targets if isinstance(no, ast.Assign) else [no.target]
            nomes = [getattr(a, "id", "?") for a in alvos]
            achados.append(
                f"linha {no.lineno}: {', '.join(nomes)} = literal MUTAVEL de "
                "nivel de modulo"
            )
    return achados


class TestOModuloEPuro:
    def test_ELE_NAO_ALCANCA_RELOGIO_LOG_TELA_NEM_IMAGEM(self):
        achados = alcances_proibidos(FONTE_DO_MODULO)
        assert not achados, (
            "renda_estado.py alcancou o que nao pode:\n  "
            + "\n  ".join(achados)
            + "\nO carimbo entra por PARAMETRO, a coleta e da casca e quem "
            "imprime e o laco."
        )

    def test_CONTROLE_POSITIVO_os_cinco_caminhos_sao_ACUSADOS(self):
        """Sem ele, o portao passa de maos dadas com uma varredura vazia."""
        with tempfile.TemporaryDirectory() as pasta:
            alvo = Path(pasta) / "impuro.py"
            alvo.write_text(
                "import time\n"
                "from datetime import datetime\n"
                "from logging import getLogger\n"
                "import numpy as np\n"
                "from .captura_janela import esta_minimizada\n"
                "\n"
                "def falar():\n"
                "    print(time.monotonic(), datetime, getLogger, np)\n",
                encoding="utf-8",
            )
            achados = alcances_proibidos(alvo)

        assert len(achados) == 6, achados
        assert any("print" in a for a in achados)
        assert any("captura_janela" in a for a in achados)

    def test_O_CONTROLE_CHAMA_A_MESMA_FUNCAO_QUE_O_PORTAO(self):
        arvore = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        definicoes = [
            no.name
            for no in ast.walk(arvore)
            if isinstance(no, ast.FunctionDef)
        ]
        assert definicoes.count("alcances_proibidos") == 1
        assert definicoes.count("memoria_de_modulo") == 1

    def test_O_PORTAO_DA_AUSENCIA_DE_MEMORIA_VARRE_O_ARQUIVO_NOVO(self):
        achados = memoria_de_modulo(FONTE_DO_MODULO)
        assert not achados, (
            "renda_estado.py ganhou memoria de modulo:\n  "
            + "\n  ".join(achados)
        )

    def test_CONTROLE_POSITIVO_UM_ACUMULADOR_DE_MODULO_E_ACUSADO(self, tmp_path):
        alvo = tmp_path / "com_memoria.py"
        alvo.write_text(
            "ULTIMO_EXP = {}\n"
            "\n"
            "def lembrar(x):\n"
            "    global ULTIMO_EXP\n"
            "    ULTIMO_EXP = x\n",
            encoding="utf-8",
        )
        achados = memoria_de_modulo(alvo)
        assert len(achados) == 2, achados
