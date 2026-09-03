"""A CONTA da renda: os quatro deltas negativos que NAO sao prejuizo, a janela
movel por tempo, as duas taxas, e o tempo ate o proximo nivel.

O QUE ESTE ARQUIVO PROVA
========================
Que a subtracao ingenua mente em quatro casos ORDINARIOS — nao de borda — e que
esta conta acerta nos quatro:

1. **Subir de nivel.** `80_012 - 685_632 = -605_620`: a melhor coisa da noite
   registrando o pior numero. A conta certa e `(um nivel inteiro - o EXP de
   antes) + o EXP de agora`, e o par de campo REAL da Faerlina sai `394_380`
   decimos de milesimo — os 39,438 pontos percentuais que o usuario viu.
2. **Gastar adena.** O gasto entra negativo na taxa de ganho e a taxa cai sem o
   usuario saber por que. Aqui ele vai para um campo PROPRIO.
3. **O nivel recusado.** Ou vira renda negativa, ou vira um level up
   INVENTADO — e o LEIT-11 mediu que 3 das 4 leituras erradas de nivel passaram
   POR CONCORDANCIA das duas escalas, que e o pior jeito de errar.
4. **O carimbo andando para tras.** O PC do usuario e dual boot e o Windows
   volta ~3h adiantado do Linux. Um intervalo negativo entra no denominador e a
   taxa sai negativa ou infinita, SEM LEVANTAR.

O QUE ELE **NAO** PROVA
=======================
Nada sobre pixel, OCR, calibracao, disco ou rede. Todas as amostras sao montadas
a mao com carimbos escolhidos. A fatia de ponta a ponta — regras de par, passo,
CSV, leitor tolerante e taxa num caminho so — e do
`tests/test_renda_conta_tracer.py`, e ela ja passa.

ESTE ARQUIVO NAO PULA POR NADA
==============================
Um `skip` aqui e falha, e nao configuracao de maquina.

OS NUMEROS QUE ENTRAM EM ASSERCAO SAO OS VERSIONADOS
====================================================
O par de campo do level up (`tests/test_renda_par.py:99-100`) e o ganho que sai
dele. Os numeros do `02-CONTEXT.md:145-153` — 466 mil adena/h, 2,41 M XP/h, ~104
abates/min — vieram de um script de bancada e NAO estao em artefato versionado:
eles aparecem aqui em prosa e em comentario, para dar escala, e nunca como valor
esperado. Um teste construido sobre numero que ninguem reproduz a partir de um
clone e um teste que envelhece calado.

A UNICA EXCECAO E ESCOPADA E ESTA EM `TestADisponibilidadeMedida`: as tres taxas
de recusa por campo (nivel 79%, adena 21%, EXP 0% — `02-CONTEXT.md:150`, sobre
14 amostras) entram como RECEITA DE CONSTRUCAO DA ENTRADA, e nunca como valor
esperado da SAIDA. Mover 79% para 70% nao muda nenhuma assercao daquele teste.
"""

from __future__ import annotations

import ast
from pathlib import Path

import l2scanner.renda_conta as rc
import l2scanner.renda_leitura as rl
from l2scanner.renda_conta import (
    DESCONTINUIDADE_DA_ANCORA,
    DESCONTINUIDADE_DA_LACUNA,
    DESCONTINUIDADE_DO_NIVEL_INDISPONIVEL_COM_EXP_CAINDO,
    DESCONTINUIDADE_DO_NIVEL_INDISPONIVEL_COM_EXP_SUBINDO,
    DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS,
    GRANDEZA_DA_ADENA,
    GRANDEZA_DO_EXP,
    SEM_DESCONTINUIDADE,
    passo_entre,
    passo_entre_campos,
    taxa_por_hora,
)
from l2scanner.renda_leitura import (
    CAMPO_DA_ADENA,
    CAMPO_DO_EXP,
    CAMPO_DO_NIVEL,
    CamposDaRenda,
    LeituraDaRenda,
    RecusaDaRenda,
    ValorDaAdena,
    ValorDaRenda,
)

FONTE_DA_CONTA = Path(__file__).parent.parent / "l2scanner" / "renda_conta.py"

# O fator de salto de exemplo, o mesmo literal de `tests/test_renda_par.py` e
# pela mesma razao: aqui ele e ARGUMENTO DE TESTE. No fonte ele nao existe.
FATOR = 10

# Sessenta segundos a ~1 Hz sao sessenta amostras perdidas seguidas: cegueira, e
# nao cadencia. E o default da secao `[renda]` do `config.toml`.
LIMIAR = 60.0

PISO_DE_AMOSTRAS = 8
PISO_DA_JANELA = 120.0

# Os pisos DESLIGADOS, para os testes que querem ver o numero sair de um par so.
# Eles existem porque o piso e assunto de testes proprios — misturar as duas
# coisas faria um teste que nao diz o que quebrou quando quebra.
PISO_DE_AMOSTRAS_DESLIGADO = 1
PISO_DA_JANELA_DESLIGADO = 0.0


# ---------------------------------------------------------------------------
# O RELOGIO FALSO, no idioma que a arvore ja tem
# ---------------------------------------------------------------------------
#
# O original e `tests/test_relogio.py:23-53` — `Maquina`, com `andar()` e
# `pular_parede()` e a docstring "o que o dual boot faz: so o relogio de parede
# salta". Ele e reescrito aqui em cinco linhas, com o endereco acima, porque
# `tests/` nao e pacote e importar de la amarraria dois arquivos de teste.
TRES_HORAS = 3 * 3600.0


class Maquina:
    """O relogio da maquina, sob controle do teste (`tests/test_relogio.py:23`)."""

    def __init__(self, parede: float = 1_000.0) -> None:
        self.parede = parede

    def andar(self, segundos: float) -> None:
        self.parede += segundos

    def pular_parede(self, segundos: float) -> None:
        """O que o dual boot faz: so o relogio de parede salta."""
        self.parede += segundos


# ---------------------------------------------------------------------------
# AS AMOSTRAS, montadas a mao
# ---------------------------------------------------------------------------


def leitura(*, nivel: int, exp: int, adena: int, carimbo: float) -> LeituraDaRenda:
    """Uma `LeituraDaRenda` montada a mao. Sem pixel, sem OCR, sem relogio."""
    return LeituraDaRenda(
        personagem="Faerlina", nivel=nivel, exp=exp, adena=adena, carimbo=carimbo
    )


def recusado(campo: str) -> RecusaDaRenda:
    """O campo que NAO virou numero, no molde de `_recusar`.

    O motivo e `campo-vazio` porque e o mais comum dos cinco na tela do nivel: o
    OCR se abstem nas duas escalas. Qual dos cinco e nao muda nada aqui — o que
    importa e que o campo saiu como RECUSA e nao como numero.
    """
    return RecusaDaRenda(
        campo=campo, motivo=rl.MOTIVO_DO_CAMPO_VAZIO, detalhe=">>><<<"
    )


def campos(
    *, nivel: int | None, exp: int | None, adena: int | None
) -> CamposDaRenda:
    """Os tres campos como o leitor de producao os entrega. `None` vira RECUSA.

    E o objeto que SOBREVIVE ao nivel recusado: `LeituraDaRenda` exige os tres
    inteiros, e com o nivel fora ela nao existe. E por isso que a decisao de nao
    adivinhar level up mora sobre `CamposDaRenda`, e nao dentro de
    `conferir_o_par`.
    """
    return CamposDaRenda(
        personagem="Faerlina",
        nivel=(
            recusado(CAMPO_DO_NIVEL)
            if nivel is None
            else ValorDaRenda(
                campo=CAMPO_DO_NIVEL, valor=nivel, escalas=2, texto=str(nivel)
            )
        ),
        exp=(
            recusado(CAMPO_DO_EXP)
            if exp is None
            else ValorDaRenda(
                campo=CAMPO_DO_EXP, valor=exp, escalas=1, texto=str(exp)
            )
        ),
        adena=(
            recusado(CAMPO_DA_ADENA)
            if adena is None
            else ValorDaAdena(
                campo=CAMPO_DA_ADENA, valor=adena, glifos=10, texto=str(adena)
            )
        ),
    )


def passos_da_sequencia(amostras, *, limiar=LIMIAR):
    """A sequencia inteira virando passos, com a ANCORA na frente."""
    passos = []
    anterior = None
    for atual in amostras:
        passos.append(
            passo_entre(
                anterior,
                atual,
                fator_de_salto=FATOR,
                limiar_de_lacuna_em_segundos=limiar,
            )
        )
        anterior = atual
    return passos


def passos_dos_campos(pares, *, limiar=LIMIAR):
    """O mesmo laco pelo caminho de `CamposDaRenda`. `pares` = (campos, carimbo)."""
    passos = []
    anterior = None
    carimbo_anterior = None
    for atual, carimbo in pares:
        passos.append(
            passo_entre_campos(
                anterior,
                atual,
                carimbo_anterior=carimbo_anterior,
                carimbo=carimbo,
                fator_de_salto=FATOR,
                limiar_de_lacuna_em_segundos=limiar,
            )
        )
        anterior = atual
        carimbo_anterior = carimbo
    return passos


# ---------------------------------------------------------------------------
# O PAR DE CAMPO DO LEVEL UP, e ele e REAL
# ---------------------------------------------------------------------------
#
#   2026-09-01 ~23h50   Faerlina, nivel 66, EXP 68,5632%, adena 10.673.628
#   2026-09-02 ~00h45   Faerlina, nivel 67, EXP  8,0012%, adena 13.160.684
#
# Procedencia das duas pontas: leitura de tela do proprio usuario, versionada em
# `tests/test_renda_par.py:99-100` e citada no `02-CONTEXT.md` (Specific Ideas).
# O CARIMBO NAO E O DE CAMPO, e isso vai dito em voz alta: as duas pontas foram
# lidas com ~55 minutos de diferenca, e com esse intervalo o passo seria `lacuna`
# — que e o comportamento CERTO e esta provado mais abaixo. O que este par prova
# sao os VALORES e o ganho que sai deles.
LEVEL_UP_ANTES = leitura(nivel=66, exp=685_632, adena=10_673_628, carimbo=0.0)
LEVEL_UP_DEPOIS = leitura(nivel=67, exp=80_012, adena=13_160_684, carimbo=30.0)

# `(1_000_000 - 685_632) + 80_012` em decimos de milesimo de ponto percentual.
GANHO_DO_LEVEL_UP = 394_380

# O que a subtracao ingenua `80_012 - 685_632` produziria. Ele e CONSTANTE porque
# um teste que so afirmasse "o ganho e 394_380" nao diria a quem o quebrasse o
# que ele acabou de reinventar.
GANHO_INGENUO_DO_LEVEL_UP = -605_620

# Dois niveis de uma vez: `66 -> 68`. Acontece com o scanner cego no meio, e o
# ganho tem de contar os niveis ATRAVESSADOS e nao so o ultimo:
# (100 - 68,5632) + 100 + 8,0012 = 139,438 pontos percentuais.
GANHO_DE_DOIS_NIVEIS = 1_394_380


class TestOParDeCampoDoLevelUp:
    """O criterio que da nome a fase, sobre o par medido na tela do usuario.

    AS DUAS PONTAS TEM PROCEDENCIA: `nivel 66, EXP 68,5632%, adena 10.673.628`
    as ~23h50 de 01/09/2026, e `nivel 67, EXP 8,0012%, adena 13.160.684` as
    ~00h45 de 02/09/2026, na Faerlina, lidas da tela pelo usuario e versionadas
    em `tests/test_renda_par.py:99-100`.
    """

    def test_O_GANHO_SAI_EM_394380_DECIMOS(self):
        passo = passos_da_sequencia([LEVEL_UP_ANTES, LEVEL_UP_DEPOIS])[-1]

        assert passo.ganho_de_exp_em_decimos == GANHO_DO_LEVEL_UP, (
            f"o par de campo do level up tem de render {GANHO_DO_LEVEL_UP} "
            "decimos de milesimo de ponto percentual, que sao os 39,438 PONTOS "
            "PERCENTUAIS que o usuario mediu na tela: (100 - 68,5632) + 8,0012 "
            f"= 39,438. Saiu {passo.ganho_de_exp_em_decimos}"
        )

    def test_CONTROLE_O_GANHO_NAO_E_A_SUBTRACAO_INGENUA_NEM_ZERO(self):
        """Sem ele, uma implementacao que devolvesse ZERO passaria no de cima.

        `max(0, 80_012 - 685_632)` da zero — que nao e negativo, e continua
        sendo errado. O portao do sinal deste arquivo proibe os tres nomes que
        absorvem sinal justamente por isso.
        """
        passo = passos_da_sequencia([LEVEL_UP_ANTES, LEVEL_UP_DEPOIS])[-1]

        assert passo.ganho_de_exp_em_decimos != GANHO_INGENUO_DO_LEVEL_UP, (
            "o ganho saiu como a SUBTRACAO INGENUA das duas leituras "
            f"({GANHO_INGENUO_DO_LEVEL_UP}). Subir de nivel zera o EXP: a conta "
            "e (um nivel inteiro - o EXP de antes) + o EXP de agora"
        )
        assert passo.ganho_de_exp_em_decimos > 0, (
            "subir de nivel e o melhor que acontece numa farmada, e ele nao "
            "pode entrar na conta como ganho zero nem como prejuizo"
        )

    def test_O_PASSO_E_ACEITO_E_UM_NIVEL_FOI_GANHO(self):
        passo = passos_da_sequencia([LEVEL_UP_ANTES, LEVEL_UP_DEPOIS])[-1]

        assert passo.niveis_ganhos == 1
        assert passo.recusas == (), (
            "as tres regras de par se calam neste par de proposito: "
            "`o_exp_andou_para_tras` se abstem quando o nivel mudou, "
            "`o_nivel_andou_para_tras` so olha para baixo, e a adena cresceu "
            "bem abaixo do fator"
        )
        assert passo.descontinuidade == SEM_DESCONTINUIDADE
        assert passo.aceito is True


class TestOLevelUpDeDoisNiveis:
    """Atravessar dois niveis num passo so, que e o que a cegueira produz."""

    def test_O_GANHO_CONTA_OS_NIVEIS_ATRAVESSADOS_E_NAO_SO_O_ULTIMO(self):
        antes = LEVEL_UP_ANTES
        depois = leitura(nivel=68, exp=80_012, adena=13_160_684, carimbo=30.0)

        passo = passos_da_sequencia([antes, depois])[-1]

        assert passo.niveis_ganhos == 2
        assert passo.ganho_de_exp_em_decimos == GANHO_DE_DOIS_NIVEIS, (
            "dois niveis atravessados num passo so acontecem com o scanner cego "
            "no meio — e uma formula que so soma UM nivel devolve um numero "
            f"menor sem avisar. Esperado {GANHO_DE_DOIS_NIVEIS} "
            "(= (100 - 68,5632) + 100 + 8,0012 pontos percentuais), saiu "
            f"{passo.ganho_de_exp_em_decimos}"
        )

    def test_CONTROLE_UM_NIVEL_SO_NAO_SOMA_NIVEL_INTEIRO_A_MAIS(self):
        """Sem ele, uma formula que somasse sempre um nivel passaria no de cima."""
        passo = passos_da_sequencia([LEVEL_UP_ANTES, LEVEL_UP_DEPOIS])[-1]

        assert passo.niveis_ganhos == 1
        assert passo.ganho_de_exp_em_decimos == GANHO_DO_LEVEL_UP, (
            "um level up de UM nivel nao pode render o ganho de dois: a formula "
            "soma `(niveis_ganhos - 1)` niveis inteiros, e aqui isso e ZERO. "
            f"Esperado {GANHO_DO_LEVEL_UP}, saiu "
            f"{passo.ganho_de_exp_em_decimos}"
        )


class TestAFormulaDoLevelUpSoDisparaComONivelMudando:
    """A guarda que impede um level up INVENTADO (CTX-5, LEIT-11)."""

    def test_MESMO_NIVEL_COM_EXP_CAINDO_MUITO_NAO_VIRA_LEVEL_UP(self):
        """Morrer derruba o EXP muito, e morrer nao e subir de nivel."""
        antes = leitura(nivel=67, exp=685_632, adena=10_673_628, carimbo=0.0)
        depois = leitura(nivel=67, exp=80_012, adena=10_700_000, carimbo=30.0)

        passo = passos_da_sequencia([antes, depois])[-1]

        assert passo.niveis_ganhos == 0, (
            "a formula do level up disparou com o nivel PARADO. A alternativa "
            "que a CTX-5 recusou por escrito e exatamente esta — 'um EXP que "
            "cai muito e um level up' —, e ela erra porque MORRER tambem "
            "derruba o EXP muito. O LEIT-11 mediu o preco: 3 das 4 leituras "
            "erradas de nivel passaram POR CONCORDANCIA das duas escalas, "
            "entao no nivel 'parece certo' prova menos que em qualquer outro "
            "campo. Inventar um level up e pior que perder um"
        )
        assert passo.ganho_de_exp_em_decimos != GANHO_DO_LEVEL_UP
        assert passo.ganho_de_exp_em_decimos == 80_012 - 685_632

        motivos = {recusa.motivo for recusa in passo.recusas}
        assert rl.MOTIVO_DO_EXP_PARA_TRAS in motivos, (
            "com o nivel PARADO, um EXP que anda para tras e a recusa nomeada "
            f"da Fase 1 chegando no passo. Recusas: {passo.recusas}"
        )
        assert passo.aceito is False

    def test_O_NIVEL_QUE_DESCE_E_RECUSA_E_O_PASSO_NAO_ENTRA_NO_DENOMINADOR(self):
        antes = leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=0.0)
        depois = leitura(nivel=66, exp=101_000, adena=10_005_000, carimbo=30.0)

        passo = passos_da_sequencia([antes, depois])[-1]

        motivos = {recusa.motivo for recusa in passo.recusas}
        assert rl.MOTIVO_DO_NIVEL_PARA_TRAS in motivos, passo.recusas
        assert passo.niveis_ganhos == 0, (
            "um nivel que DESCE nao pode produzir `niveis_ganhos` negativo: o "
            "caminho comum para um nivel que desce nao e o jogo, e um digito "
            "trocado"
        )
        assert passo.aceito is False

        taxa = taxa_por_hora(
            [passo],
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS_DESLIGADO,
            piso_da_janela_em_segundos=PISO_DA_JANELA_DESLIGADO,
        )
        assert taxa.evidencia.n == 0
        assert taxa.por_hora is None


class TestAAdenaQueCaiEGastoENaoRendaNegativa:
    """CTX-6: as duas grandezas nunca se somam nem se cancelam."""

    def test_O_GASTO_VAI_PARA_CAMPO_PROPRIO_E_O_GANHO_DAQUELE_PASSO_E_ZERO(self):
        antes = leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=0.0)
        depois = leitura(nivel=67, exp=101_000, adena=9_800_000, carimbo=30.0)

        passo = passos_da_sequencia([antes, depois])[-1]

        assert passo.ganho_de_adena == 0
        assert passo.gasto_de_adena == 200_000
        assert passo.aceito is True, (
            "gastar 200 mil adena de um saldo de dez milhoes e o que o usuario "
            "faz toda sessao, e nao pode derrubar o passo"
        )

    def test_A_SEQUENCIA_COM_GASTO_NO_MEIO_NAO_SOMA_PONTA_A_PONTA(self):
        """Ganho bruto e gasto sao DOIS fatos, e a soma deles nao e o delta.

        Sem esta assercao, uma implementacao que somasse os deltas com sinal
        passaria em todos os testes de passo isolado — e a taxa de ganho de uma
        noite em que o usuario comprou uma arma sairia pela metade.
        """
        amostras = [
            leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=0.0),
            leitura(nivel=67, exp=101_000, adena=10_005_000, carimbo=30.0),
            leitura(nivel=67, exp=102_000, adena=9_900_000, carimbo=60.0),
            leitura(nivel=67, exp=103_000, adena=9_950_000, carimbo=90.0),
        ]
        passos = [p for p in passos_da_sequencia(amostras) if p.aceito]

        ganho_bruto = sum(p.ganho_de_adena for p in passos)
        gasto = sum(p.gasto_de_adena for p in passos)
        ponta_a_ponta = amostras[-1].adena - amostras[0].adena

        assert ganho_bruto == 55_000, passos
        assert gasto == 105_000, passos
        assert ponta_a_ponta == -50_000
        assert ganho_bruto != ponta_a_ponta, (
            "o ganho bruto e a soma dos deltas POSITIVOS, e o delta ponta a "
            f"ponta ({ponta_a_ponta}) e outra coisa. Colapsar os dois faz uma "
            "noite de farm com uma compra no meio parecer uma noite ruim"
        )
        assert ganho_bruto - gasto == ponta_a_ponta, (
            "os dois numeros tem de RECONSTRUIR o delta quando somados com "
            "sinal — se nao reconstroem, um deles esta perdendo dinheiro"
        )

    def test_A_ADENA_QUE_SALTA_ORDEM_DE_GRANDEZA_E_RECUSA_E_NAO_GASTO(self):
        """`10.673.628` -> `91` e um digito perdido (M-G), e nao uma compra."""
        antes = leitura(nivel=67, exp=100_000, adena=10_673_628, carimbo=0.0)
        depois = leitura(nivel=67, exp=101_000, adena=91, carimbo=30.0)

        passo = passos_da_sequencia([antes, depois])[-1]

        motivos = {recusa.motivo for recusa in passo.recusas}
        assert rl.MOTIVO_DO_SALTO_DA_ADENA in motivos, passo.recusas
        assert passo.aceito is False, (
            "um salto de ordem de grandeza nao pode entrar como GASTO: gastar "
            "adena deixa o passo ACEITO (ha teste ao lado afirmando isso), e um "
            "digito perdido tem de deixa-lo RECUSADO. E a diferenca entre os "
            "dois desfechos que impede o `91` de virar 'o usuario gastou 10,6 "
            "milhoes'"
        )

        taxa = taxa_por_hora(
            [passo],
            grandeza=GRANDEZA_DA_ADENA,
            piso_de_amostras=PISO_DE_AMOSTRAS_DESLIGADO,
            piso_da_janela_em_segundos=PISO_DA_JANELA_DESLIGADO,
        )
        assert taxa.evidencia.n == 0


class TestOCarimboQueAndaParaTras:
    """CTX-10: o dual boot do usuario, e ele tem NOME e nao conserto."""

    def test_A_DESCONTINUIDADE_E_NOMEADA_E_O_INTERVALO_GUARDA_O_SINAL(self):
        maquina = Maquina(parede=1_000.0)
        antes = leitura(
            nivel=67, exp=100_000, adena=10_000_000, carimbo=maquina.parede
        )
        maquina.andar(30.0)
        maquina.pular_parede(-TRES_HORAS)
        depois = leitura(
            nivel=67, exp=101_000, adena=10_005_000, carimbo=maquina.parede
        )

        passo = passos_da_sequencia([antes, depois])[-1]

        assert passo.descontinuidade == DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS
        assert passo.intervalo_em_segundos == 30.0 - TRES_HORAS, (
            "o intervalo tem de continuar NEGATIVO: o sinal e a evidencia do "
            "salto, e um `abs()` ou um `max(0, ...)` a apagaria"
        )
        assert passo.aceito is False

    def test_O_PASSO_DO_SALTO_NAO_ENTRA_NO_DENOMINADOR(self):
        """Sem esta metade, um intervalo negativo ENCOLHERIA a janela farmada."""
        antes = leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=1_000.0)
        depois = leitura(nivel=67, exp=101_000, adena=10_005_000, carimbo=970.0)

        taxa = taxa_por_hora(
            passos_da_sequencia([antes, depois]),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS_DESLIGADO,
            piso_da_janela_em_segundos=PISO_DA_JANELA_DESLIGADO,
        )

        assert taxa.evidencia.n == 0
        assert taxa.janela_farmada_em_segundos == 0.0
        assert taxa.por_hora is None


class TestOsCarimbosIguais:
    """Intervalo ZERO e outro fato, e a divisao simplesmente nao acontece."""

    def test_INTERVALO_ZERO_TEM_MOTIVO_NOMEADO_E_NUNCA_INFINITO(self):
        antes = leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=500.0)
        depois = leitura(nivel=67, exp=101_000, adena=10_005_000, carimbo=500.0)

        passos = passos_da_sequencia([antes, depois])
        assert passos[-1].intervalo_em_segundos == 0.0

        taxa = taxa_por_hora(
            passos,
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS_DESLIGADO,
            piso_da_janela_em_segundos=PISO_DA_JANELA_DESLIGADO,
        )

        assert taxa.por_hora is None, (
            "uma taxa por hora sobre zero segundo nao e um numero grande, e "
            f"NENHUM. Saiu {taxa.por_hora}"
        )
        assert taxa.motivo_da_ausencia is not None
        assert "zero" in taxa.motivo_da_ausencia.lower()


class TestONivelRecusadoNaoViraLevelUpAdivinhado:
    """O caso mais caro, e ele e ESTRUTURAL (CTX-5, LEIT-11, T-02-09).

    As quatro regras de par exigem `LeituraDaRenda`, que exige os TRES campos
    inteiros. Com o nivel recusado esse objeto NAO EXISTE — entao
    `conferir_o_par` nao pode ser chamada, e a decisao mora sobre
    `CamposDaRenda`.

    E ela sao DUAS decisoes, porque os dois sentidos do EXP nao sao o mesmo
    caso: com o EXP CAINDO ha um level up a supor (e supor e proibido), e com o
    EXP SUBINDO nao ha — um level up faz o EXP CAIR.
    """

    def test_COM_O_EXP_CAINDO_O_GANHO_NAO_E_COMPUTADO(self):
        passo = passos_dos_campos(
            [
                (campos(nivel=None, exp=685_632, adena=10_673_628), 0.0),
                (campos(nivel=None, exp=80_012, adena=10_700_000), 30.0),
            ]
        )[-1]

        assert (
            passo.descontinuidade
            == DESCONTINUIDADE_DO_NIVEL_INDISPONIVEL_COM_EXP_CAINDO
        )
        assert passo.ganho_de_exp_em_decimos is None, (
            "sem o nivel, um EXP que CAI pode ser um level up ou pode ser uma "
            "morte, e nao ha como distinguir. Inventar o level up e pior que "
            "perder o passo: o LEIT-11 mediu que 3 das 4 leituras erradas de "
            "nivel passaram POR CONCORDANCIA das duas escalas"
        )
        assert passo.niveis_ganhos is None

    def test_COM_O_EXP_SUBINDO_O_GANHO_E_COMPUTADO_NORMALMENTE(self):
        """E o valor e IGUAL ao do mesmo par com o nivel presente.

        A regra que caiu — "sem o nivel, NENHUM ganho de EXP" — cobrava sem
        proteger: um level up faz o EXP CAIR, entao com o EXP subindo nao existe
        level up a supor. E o limiar de lacuna fecha o argumento: a ~104 abates
        por minuto e 0,001011 ponto percentual por abate (REND-08), a barra anda
        ~0,1 ponto percentual em SESSENTA segundos, contra os ~100 pontos que um
        level up exigiria no mesmo intervalo. Tres ordens de grandeza.
        """
        com_nivel = passos_da_sequencia(
            [
                leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=0.0),
                leitura(nivel=67, exp=101_000, adena=10_005_000, carimbo=30.0),
            ]
        )[-1]
        sem_nivel = passos_dos_campos(
            [
                (campos(nivel=None, exp=100_000, adena=10_000_000), 0.0),
                (campos(nivel=None, exp=101_000, adena=10_005_000), 30.0),
            ]
        )[-1]

        assert (
            sem_nivel.descontinuidade
            == DESCONTINUIDADE_DO_NIVEL_INDISPONIVEL_COM_EXP_SUBINDO
        )
        assert sem_nivel.ganho_de_exp_em_decimos == 1_000
        assert (
            sem_nivel.ganho_de_exp_em_decimos
            == com_nivel.ganho_de_exp_em_decimos
        ), (
            "o mesmo par com e sem o nivel tem de dar o MESMO ganho de EXP "
            "quando o EXP sobe. A ~104 abates/min a barra anda ~0,1 ponto "
            "percentual em 60 s; para o EXP subir ATRAVESSANDO um nivel dentro "
            "de um passo aceito ela teria de andar ~100 pontos no mesmo "
            "intervalo — tres ordens de grandeza acima do medido. Quem levantar "
            "`lacuna_maxima_segundos` para horas reabre este caso"
        )

    def test_O_PASSO_DO_EXP_SUBINDO_ENTRA_NO_DENOMINADOR_DO_EXP(self):
        """A descontinuidade de PROCEDENCIA nao exclui — e a diferenca inteira."""
        passos = passos_dos_campos(
            [
                (campos(nivel=None, exp=100_000, adena=10_000_000), 0.0),
                (campos(nivel=None, exp=101_000, adena=10_005_000), 30.0),
            ]
        )

        taxa = taxa_por_hora(
            passos,
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS_DESLIGADO,
            piso_da_janela_em_segundos=PISO_DA_JANELA_DESLIGADO,
        )

        assert taxa.evidencia.n == 1
        assert taxa.janela_farmada_em_segundos == 30.0
        assert taxa.por_hora == 120_000

    def test_OS_DOIS_MARCADORES_SAO_TEXTOS_DIFERENTES(self):
        """Sem esta assercao, uma implementacao que emitisse o MESMO marcador
        nos dois sentidos passaria em cada teste acima isoladamente — e "a
        guarda existe" ficaria indistinguivel de "a guarda virou supressao
        geral".
        """
        caindo = passos_dos_campos(
            [
                (campos(nivel=None, exp=685_632, adena=10_673_628), 0.0),
                (campos(nivel=None, exp=80_012, adena=10_700_000), 30.0),
            ]
        )[-1]
        subindo = passos_dos_campos(
            [
                (campos(nivel=None, exp=100_000, adena=10_000_000), 0.0),
                (campos(nivel=None, exp=101_000, adena=10_005_000), 30.0),
            ]
        )[-1]

        assert caindo.descontinuidade != subindo.descontinuidade, (
            "os dois sentidos do EXP com o nivel recusado sao casos DIFERENTES: "
            "um suprime o ganho e o outro so registra a procedencia. Um "
            "marcador unico apagaria a diferenca"
        )
        assert caindo.ganho_de_exp_em_decimos is None
        assert subindo.ganho_de_exp_em_decimos is not None
        assert subindo.descontinuidade not in rc.DESCONTINUIDADES_QUE_EXCLUEM, (
            "`nivel-indisponivel-com-exp-subindo` e PROCEDENCIA e nao exclusao: "
            "o passo CONTA. E este nome que impede que ela seja excluida por "
            "engano junto com as outras"
        )
        assert caindo.descontinuidade in rc.DESCONTINUIDADES_QUE_EXCLUEM

    def test_O_EXP_PARADO_COM_O_NIVEL_RECUSADO_TAMBEM_CONTA(self):
        """O EXP que nao mudou nao caiu, logo nao ha level up a supor.

        O ramo do `-caindo` existe para o EXP que ANDOU PARA TRAS. Um EXP
        identico nas duas pontas rende ganho ZERO, que e uma medicao legitima —
        e excluir o passo o tiraria do denominador e inflaria a taxa.
        """
        passo = passos_dos_campos(
            [
                (campos(nivel=None, exp=100_000, adena=10_000_000), 0.0),
                (campos(nivel=None, exp=100_000, adena=10_005_000), 30.0),
            ]
        )[-1]

        assert (
            passo.descontinuidade
            == DESCONTINUIDADE_DO_NIVEL_INDISPONIVEL_COM_EXP_SUBINDO
        )
        assert passo.ganho_de_exp_em_decimos == 0

    def test_A_ADENA_CONTINUA_CONTANDO_COM_O_NIVEL_RECUSADO(self):
        """O campo mais fragil dos tres nao pode derrubar os outros dois.

        Sem este teste, uma implementacao que descartasse a amostra INTEIRA
        passaria em todos os outros — e a adena, que recusa em 21% dos tiques,
        sumiria nos 79% em que o nivel recusa.
        """
        passos = passos_dos_campos(
            [
                (campos(nivel=None, exp=100_000, adena=10_000_000), 0.0),
                (campos(nivel=None, exp=101_000, adena=10_005_000), 30.0),
            ]
        )
        passo = passos[-1]

        assert passo.ganho_de_adena == 5_000
        assert passo.gasto_de_adena == 0

        taxa = taxa_por_hora(
            passos,
            grandeza=GRANDEZA_DA_ADENA,
            piso_de_amostras=PISO_DE_AMOSTRAS_DESLIGADO,
            piso_da_janela_em_segundos=PISO_DA_JANELA_DESLIGADO,
        )
        assert taxa.evidencia.n == 1
        assert taxa.por_hora == 600_000

    def test_A_ADENA_CONTA_ATE_QUANDO_O_EXP_SAIU_DO_DENOMINADOR(self):
        """O denominador e POR GRANDEZA: o `-caindo` tira o EXP e deixa a adena."""
        passos = passos_dos_campos(
            [
                (campos(nivel=None, exp=685_632, adena=10_673_628), 0.0),
                (campos(nivel=None, exp=80_012, adena=10_700_000), 30.0),
            ]
        )

        do_exp = taxa_por_hora(
            passos,
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS_DESLIGADO,
            piso_da_janela_em_segundos=PISO_DA_JANELA_DESLIGADO,
        )
        da_adena = taxa_por_hora(
            passos,
            grandeza=GRANDEZA_DA_ADENA,
            piso_de_amostras=PISO_DE_AMOSTRAS_DESLIGADO,
            piso_da_janela_em_segundos=PISO_DA_JANELA_DESLIGADO,
        )

        assert do_exp.evidencia.n == 0
        assert da_adena.evidencia.n == 1
        assert da_adena.janela_farmada_em_segundos == 30.0

    def test_CONFERIR_O_PAR_NAO_E_CHAMADA_NO_CAMINHO_DO_NIVEL_RECUSADO(
        self, monkeypatch
    ):
        """Nao ha par a conferir: as quatro regras exigem os TRES inteiros.

        A prova e por INJECAO — um substituto que registra a chamada — e nao por
        inspecao do fonte, porque o que importa e o caminho EXECUTADO.
        """
        chamadas = []

        def espia(anterior, atual, *, fator_de_salto):
            chamadas.append((anterior, atual, fator_de_salto))
            return ()

        monkeypatch.setattr(rl, "conferir_o_par", espia)

        passo = passos_dos_campos(
            [
                (campos(nivel=None, exp=100_000, adena=10_000_000), 0.0),
                (campos(nivel=None, exp=101_000, adena=10_005_000), 30.0),
            ]
        )[-1]

        assert chamadas == [], (
            "`conferir_o_par` foi chamada num par sem nivel. As quatro regras "
            "exigem `LeituraDaRenda`, que exige os TRES campos inteiros — com o "
            "nivel recusado esse objeto nao existe"
        )
        assert passo.recusas == ()
        assert passo.descontinuidade != SEM_DESCONTINUIDADE

    def test_CONTROLE_COM_OS_TRES_CAMPOS_CONFERIR_O_PAR_E_CHAMADA(
        self, monkeypatch
    ):
        """Sem ele, uma implementacao que NUNCA chamasse passaria no de cima."""
        chamadas = []

        def espia(anterior, atual, *, fator_de_salto):
            chamadas.append((anterior, atual, fator_de_salto))
            return ()

        monkeypatch.setattr(rl, "conferir_o_par", espia)

        passos_dos_campos(
            [
                (campos(nivel=67, exp=100_000, adena=10_000_000), 0.0),
                (campos(nivel=67, exp=101_000, adena=10_005_000), 30.0),
            ]
        )

        assert len(chamadas) == 1, chamadas


class TestOPortaoDoSinal:
    """`abs`, `max` e `min` sao TRES nomes para a mesma falha (T-02-10).

    O `02-01-PLAN.md:433` proibe os tres em prosa, e a razao e executavel:
    `max(0, atual.carimbo - anterior.carimbo)` absorve o sinal EXATAMENTE como
    `abs(...)` faria. Um portao que so contasse `abs` deixaria passar a mesma
    falha com outro nome — que e a definicao de portao que nao e portao.
    """

    NOMES = ("abs", "max", "min")

    def test_NEM_ABS_NEM_MAX_NEM_MIN_SAO_CHAMADOS_NO_MODULO(self):
        assert len(self.NOMES) == 3, (
            "o conjunto conferido tem de ter TRES nomes e nao um: um portao que "
            "so contasse `abs` deixaria passar `max(0, delta)`, que absorve o "
            "sinal identicamente"
        )
        assert chamadas_de(FONTE_DA_CONTA, set(self.NOMES)) == [], (
            "o modulo da conta chamou um nome que absorve sinal. Os dois "
            "lugares em que a mao pede um deles — a separacao ganho/gasto da "
            "adena e a recencia — sao ramo EXPLICITO de proposito: o sinal vira "
            "DECISAO visivel no fonte, e nao uma absorcao que atravessa a "
            "revisao sem ser lida"
        )

    def test_CONTROLE_POSITIVO_O_PORTAO_ACUSA_UM_MAX_SINTETICO(self, tmp_path):
        """Sem ele, um portao que devolvesse sempre lista vazia passaria."""
        alvo = tmp_path / "com_max.py"
        alvo.write_text(
            "def intervalo(a, b):\n    return max(0, b - a)\n", encoding="utf-8"
        )

        assert chamadas_de(alvo, set(self.NOMES)) == ["max"]


def chamadas_de(fonte, nomes) -> list[str]:
    """Os nomes de `nomes` CHAMADOS no fonte, por arvore e nunca por `grep`.

    Compartilhada pelo portao e pelo controle positivo: um controle que
    reimplementasse a varredura provaria que a reimplementacao funciona.
    A varredura e por arvore para que a prosa — e ela e longa neste modulo —
    atravesse sem virar falso positivo.
    """
    arvore = ast.parse(Path(fonte).read_text(encoding="utf-8"))
    return sorted(
        {
            chamado
            for chamado in (
                getattr(no.func, "id", None) or getattr(no.func, "attr", None)
                for no in ast.walk(arvore)
                if isinstance(no, ast.Call)
            )
            if chamado in nomes
        }
    )


class TestOsCemPontosSaemDaConstanteDaFaseUm:
    """Um `1_000_000` literal seria uma SEGUNDA verdade sobre a mesma unidade."""

    def test_NENHUM_LITERAL_DE_UM_MILHAO_NO_MODULO(self):
        literais = literais_de_um_milhao(FONTE_DA_CONTA)

        assert literais == [], (
            "um nivel inteiro sao `DECIMOS_DE_MILESIMO_POR_PONTO * 100`, "
            "derivados da constante da Fase 1. Escrever `1_000_000` a mao cria "
            "duas verdades sobre a mesma unidade, e no dia em que a escala "
            f"mudar so uma delas muda. Achei {literais}"
        )

    def test_CONTROLE_POSITIVO_O_PORTAO_ACUSA_UM_LITERAL_SINTETICO(self, tmp_path):
        alvo = tmp_path / "com_literal.py"
        alvo.write_text("UM_NIVEL = 1_000_000\n", encoding="utf-8")

        assert literais_de_um_milhao(alvo) == [1_000_000]


def literais_de_um_milhao(fonte) -> list:
    """Os literais de valor `1_000_000` no fonte. Compartilhada com o controle."""
    arvore = ast.parse(Path(fonte).read_text(encoding="utf-8"))
    return [
        no.value
        for no in ast.walk(arvore)
        if isinstance(no, ast.Constant) and no.value == 1_000_000
    ]


# ---------------------------------------------------------------------------
# O PORTAO DA DISTINCAO DOS MOTIVOS DESTA FASE
# ---------------------------------------------------------------------------

# DOIS prefixos e nao um, e os dois sao derivados do fonte: a Fase 1 nomeia as
# recusas de LEITURA com `MOTIVO_`, e esta fase nomeia as descontinuidades de PAR
# com `DESCONTINUIDADE_`. Sao duas familias porque sao dois momentos — uma diz
# que um campo nao virou numero, a outra diz que dois numeros nao formam um
# passo —, e um prefixo so obrigaria uma das duas a mentir sobre o que e.
PREFIXOS_DO_MOTIVO = ("MOTIVO_", "DESCONTINUIDADE_")


def motivos_do_modulo(modulo) -> dict:
    """Os motivos DERIVADOS do modulo, e nunca uma lista escrita a mao.

    E a mesma funcao que o portao e o controle positivo usam. Um controle que
    reimplementasse a coleta provaria que a reimplementacao funciona, e nao que
    o portao funciona.
    """
    return {
        nome: valor
        for nome, valor in vars(modulo).items()
        if isinstance(valor, str)
        and valor
        and any(nome.startswith(prefixo) for prefixo in PREFIXOS_DO_MOTIVO)
    }


def duplicados(motivos: dict) -> dict:
    """`{valor: [nomes]}` para os valores que aparecem mais de uma vez."""
    por_valor: dict = {}
    for nome, valor in motivos.items():
        por_valor.setdefault(valor, []).append(nome)
    return {valor: nomes for valor, nomes in por_valor.items() if len(nomes) > 1}


class TestOPortaoDaDistincaoDosMotivosDaConta:
    """Cada motivo desta fase e DISTINTO — dos irmaos e dos da Fase 1.

    A razao nao e estetica: os CONSERTOS sao diferentes. `lacuna` pede olhar por
    que o scanner ficou cego; `relogio-andou-para-tras` pede olhar o dual boot;
    `nivel-indisponivel-com-exp-caindo` pede recalibrar o retangulo do nivel. E
    os dois marcadores de nivel indisponivel dizem coisas OPOSTAS sobre o mesmo
    passo — fundi-los apagaria a decisao inteira da CTX-5.
    """

    def test_TODOS_OS_MOTIVOS_DA_CONTA_SAO_DISTINTOS_DOIS_A_DOIS(self):
        repetidos = duplicados(motivos_do_modulo(rc))
        assert not repetidos, (
            "dois motivos com o MESMO valor:\n  "
            + "\n  ".join(
                f"{valor!r} <- {', '.join(nomes)}"
                for valor, nomes in repetidos.items()
            )
        )

    def test_NENHUM_MOTIVO_DESTA_FASE_COLIDE_COM_UM_DA_FASE_1(self):
        da_conta = set(motivos_do_modulo(rc).values())
        da_leitura = set(motivos_do_modulo(rl).values())

        assert not (da_conta & da_leitura), (
            "um motivo desta fase tem o mesmo texto de um da Fase 1: "
            f"{sorted(da_conta & da_leitura)}. Eles viajam na MESMA coluna do "
            "CSV, e um texto repetido faria duas causas diferentes virarem a "
            "mesma linha no arquivo"
        )
        assert da_conta, "o modulo da conta nao declara motivo nenhum"
        assert da_leitura, "a coleta nao achou os motivos da Fase 1"

    def test_OS_CINCO_MARCADORES_DA_CONTA_ESTAO_DECLARADOS(self):
        valores = set(motivos_do_modulo(rc).values())
        for marcador in (
            DESCONTINUIDADE_DA_ANCORA,
            DESCONTINUIDADE_DA_LACUNA,
            DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS,
            DESCONTINUIDADE_DO_NIVEL_INDISPONIVEL_COM_EXP_CAINDO,
            DESCONTINUIDADE_DO_NIVEL_INDISPONIVEL_COM_EXP_SUBINDO,
        ):
            assert marcador in valores, marcador

    def test_CONTROLE_POSITIVO_UM_VALOR_DUPLICADO_E_ACUSADO_PELO_NOME(self):
        """Sem ele, o portao passa de maos dadas com uma conferencia vazia."""
        repetidos = duplicados(
            {
                "DESCONTINUIDADE_DA_LACUNA": "lacuna",
                "DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS": "lacuna",
                "DESCONTINUIDADE_DA_ANCORA": "ancora",
            }
        )
        assert repetidos == {
            "lacuna": [
                "DESCONTINUIDADE_DA_LACUNA",
                "DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS",
            ]
        }

    def test_O_CONTROLE_CHAMA_A_MESMA_FUNCAO_QUE_O_PORTAO(self):
        arvore = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        definicoes = [
            no.name for no in ast.walk(arvore) if isinstance(no, ast.FunctionDef)
        ]
        assert definicoes.count("duplicados") == 1
        assert definicoes.count("motivos_do_modulo") == 1
        assert definicoes.count("chamadas_de") == 1
        assert definicoes.count("literais_de_um_milhao") == 1
