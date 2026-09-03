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
from fractions import Fraction
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
    UNIDADE_DA_JANELA,
    as_duas_taxas,
    passo_entre,
    passo_entre_campos,
    passos_da_janela,
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


# ===========================================================================
# TAREFA 2: A JANELA MOVEL POR TEMPO, O DENOMINADOR SEM LACUNA, AS DUAS TAXAS
# ===========================================================================


def sequencia_regular(
    *,
    n: int,
    passo_em_segundos: float,
    comeco: float = 0.0,
    exp_por_passo: int = 1_000,
    adena_por_passo: int = 5_000,
    exp_inicial: int = 100_000,
    adena_inicial: int = 10_000_000,
):
    """`n` amostras ordinarias, cadencia fixa, EXP e adena subindo em passo fixo.

    O GANHO POR PASSO E CONSTANTE DE PROPOSITO: e o que faz a taxa da sequencia
    com buraco ser EXATAMENTE a mesma da sequencia sem buraco, em vez de
    aproximadamente a mesma. Um teste de taxa que precisasse de tolerancia
    deixaria de medir a exclusao da lacuna e passaria a medir a tolerancia.
    """
    return [
        leitura(
            nivel=67,
            exp=exp_inicial + indice * exp_por_passo,
            adena=adena_inicial + indice * adena_por_passo,
            carimbo=comeco + indice * passo_em_segundos,
        )
        for indice in range(n)
    ]


class TestAJanelaEPorTempoENaoPorContagem:
    """CTX-1: "ultimos dez minutos" e o que o usuario entende.

    "Ultimas quarenta amostras" muda de significado quando a cadencia muda ou
    quando o scanner fica cego — e a Fase 3 tem cadencia variavel POR NATUREZA,
    porque o OCR custa dezenas de milissegundos e o jogo as vezes some da tela.
    """

    def test_DOBRAR_A_CADENCIA_NAO_MUDA_A_JANELA_COBERTA_E_MUDA_O_N(self):
        devagar = passos_da_sequencia(
            sequencia_regular(n=61, passo_em_segundos=1.0)
        )
        depressa = passos_da_sequencia(
            sequencia_regular(n=121, passo_em_segundos=0.5)
        )

        da_devagar = taxa_por_hora(
            passos_da_janela(devagar, janela_em_segundos=60.0),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS_DESLIGADO,
            piso_da_janela_em_segundos=PISO_DA_JANELA_DESLIGADO,
        )
        da_depressa = taxa_por_hora(
            passos_da_janela(depressa, janela_em_segundos=60.0),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS_DESLIGADO,
            piso_da_janela_em_segundos=PISO_DA_JANELA_DESLIGADO,
        )

        assert (
            da_devagar.janela_farmada_em_segundos
            == da_depressa.janela_farmada_em_segundos
            == 60.0
        ), (
            "a janela e por TEMPO: sessenta segundos de farm continuam sendo "
            "sessenta segundos, tenha a cadencia dobrado ou nao. Se este numero "
            "mudou, a janela virou 'as ultimas N amostras' — e ela muda de "
            "significado toda vez que o OCR fica mais lento"
        )
        assert da_devagar.evidencia.n == 60
        assert da_depressa.evidencia.n == 120, (
            "o `n` TEM de mudar: dobrar a cadencia dobra o numero de passos "
            "dentro da mesma janela. Se ele nao mudou, a janela cortou por "
            "contagem"
        )

    def test_A_JANELA_CORTA_A_PARTIR_DA_AMOSTRA_MAIS_RECENTE(self):
        """Uma sequencia de dez minutos, olhada por uma janela de um minuto."""
        passos = passos_da_sequencia(
            sequencia_regular(n=601, passo_em_segundos=1.0)
        )

        recortados = passos_da_janela(passos, janela_em_segundos=60.0)

        assert len(recortados) == 60
        assert recortados[-1] is passos[-1], (
            "a janela sai da amostra MAIS RECENTE para tras, e nao do comeco "
            "da sequencia para a frente"
        )


class TestALacunaSaiDoDenominadorEEContadaAParte:
    """CTX-2: vinte minutos de cegueira nao viram taxa baixa."""

    def test_COM_LACUNA_E_SEM_LACUNA_A_TAXA_POR_HORA_E_A_MESMA(self):
        """O par que discrimina, e ele precisa das DUAS metades.

        Uma implementacao que ignorasse lacunas passaria numa; outra que
        ignorasse tudo passaria na outra. So as duas juntas dizem que o tempo
        cego saiu do denominador e foi contado a parte.
        """
        sem_buraco = passos_da_sequencia(
            sequencia_regular(n=21, passo_em_segundos=30.0)
        )

        primeira = sequencia_regular(n=11, passo_em_segundos=30.0)
        segunda = sequencia_regular(
            n=10,
            passo_em_segundos=30.0,
            comeco=primeira[-1].carimbo + 1_230.0,
            exp_inicial=primeira[-1].exp + 1_000,
            adena_inicial=primeira[-1].adena + 5_000,
        )
        com_buraco = passos_da_sequencia(primeira + segunda)

        a = taxa_por_hora(
            sem_buraco,
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )
        b = taxa_por_hora(
            com_buraco,
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert a.por_hora == b.por_hora == 120_000, (
            "vinte minutos de cegueira no meio da noite nao podem mudar a taxa "
            "por hora: os minutos cegos NAO foram farmados do ponto de vista da "
            "medicao, e dividir por eles produz um numero baixo que o usuario "
            f"nao tem como distinguir de 'o farm piorou'. {a.por_hora} != "
            f"{b.por_hora}"
        )
        assert a.lacunas_excluidas == 0
        assert b.lacunas_excluidas == 1
        assert b.segundos_em_lacuna == 1_230.0
        assert a.segundos_em_lacuna == 0.0

    def test_DUAS_LACUNAS_CONTAM_DUAS_E_OS_SEGUNDOS_SOMAM(self):
        primeira = sequencia_regular(n=8, passo_em_segundos=30.0)
        segunda = sequencia_regular(
            n=8,
            passo_em_segundos=30.0,
            comeco=primeira[-1].carimbo + 600.0,
            exp_inicial=primeira[-1].exp + 1_000,
            adena_inicial=primeira[-1].adena + 5_000,
        )
        terceira = sequencia_regular(
            n=8,
            passo_em_segundos=30.0,
            comeco=segunda[-1].carimbo + 900.0,
            exp_inicial=segunda[-1].exp + 1_000,
            adena_inicial=segunda[-1].adena + 5_000,
        )

        taxa = taxa_por_hora(
            passos_da_sequencia(primeira + segunda + terceira),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert taxa.lacunas_excluidas == 2
        assert taxa.segundos_em_lacuna == 1_500.0
        assert taxa.por_hora == 120_000

    def test_UMA_SEQUENCIA_INTEIRA_DENTRO_DE_UMA_LACUNA_NAO_TEM_TAXA(self):
        """Duas amostras separadas por meia hora nao sao uma taxa por hora."""
        amostras = [
            leitura(nivel=67, exp=100_000, adena=10_000_000, carimbo=0.0),
            leitura(nivel=67, exp=190_000, adena=10_500_000, carimbo=1_800.0),
        ]

        taxa = taxa_por_hora(
            passos_da_sequencia(amostras),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS_DESLIGADO,
            piso_da_janela_em_segundos=PISO_DA_JANELA_DESLIGADO,
        )

        assert taxa.por_hora is None, (
            "nao ha denominador: o unico passo da sequencia e uma lacuna, e "
            "dividir o ganho de meia hora por zero segundo farmado nao produz "
            "um numero grande — produz nenhum"
        )
        assert taxa.motivo_da_ausencia is not None
        assert taxa.lacunas_excluidas == 1
        assert taxa.janela_farmada_em_segundos == 0.0


class TestAsDuasTaxasENaoUma:
    """CTX-4: apresentar so uma MENTE POR OMISSAO.

    Medido em campo: a media de 8h45 deu ~226 mil adena/h e a janela curta deu
    466 mil/h. A diferenca inteira e TEMPO PARADO — e as duas respondem perguntas
    diferentes: "o que esta acontecendo agora" e "o que a noite rendeu".
    """

    def test_A_JANELA_E_A_SESSAO_SAO_DIFERENTES_QUANDO_HOUVE_TEMPO_PARADO(self):
        devagar = sequencia_regular(
            n=20, passo_em_segundos=30.0, exp_por_passo=1_000
        )
        depressa = sequencia_regular(
            n=20,
            passo_em_segundos=30.0,
            comeco=devagar[-1].carimbo + 1_800.0,
            exp_por_passo=5_000,
            exp_inicial=devagar[-1].exp + 5_000,
            adena_inicial=devagar[-1].adena + 5_000,
        )

        duas = as_duas_taxas(
            passos_da_sequencia(devagar + depressa),
            grandeza=GRANDEZA_DO_EXP,
            janela_em_segundos=600.0,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert duas.janela.por_hora == 600_000
        assert duas.sessao.por_hora == 360_000
        assert duas.janela.por_hora != duas.sessao.por_hora, (
            "as duas taxas respondem perguntas DIFERENTES e nesta sequencia elas "
            "tem de divergir: a janela curta ve so o trecho recente e a sessao "
            "inteira carrega o trecho fraco de antes da pausa. Apresentar so uma "
            "mente por omissao"
        )
        assert (
            duas.sessao.janela_farmada_em_segundos
            > duas.janela.janela_farmada_em_segundos
        )

    def test_CONTROLE_SEM_TEMPO_PARADO_AS_DUAS_SAO_IGUAIS(self):
        """Sem ele, uma implementacao que devolvesse dois numeros QUAISQUER
        diferentes passaria no teste acima."""
        duas = as_duas_taxas(
            passos_da_sequencia(sequencia_regular(n=40, passo_em_segundos=30.0)),
            grandeza=GRANDEZA_DO_EXP,
            janela_em_segundos=3_600.0,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert duas.janela.por_hora == duas.sessao.por_hora == 120_000
        assert (
            duas.janela.janela_farmada_em_segundos
            == duas.sessao.janela_farmada_em_segundos
        )


class TestAAncoraEOReinicio:
    """REG-02 / C-7: reiniciar nao inventa nem apaga renda."""

    def test_A_PRIMEIRA_AMOSTRA_E_ANCORA_E_NAO_ENTRA_EM_DENOMINADOR_NENHUM(self):
        passos = passos_da_sequencia(
            sequencia_regular(n=21, passo_em_segundos=30.0)
        )

        assert passos[0].descontinuidade == DESCONTINUIDADE_DA_ANCORA
        assert passos[0].intervalo_em_segundos is None

        for grandeza in (GRANDEZA_DO_EXP, GRANDEZA_DA_ADENA):
            taxa = taxa_por_hora(
                passos,
                grandeza=grandeza,
                piso_de_amostras=PISO_DE_AMOSTRAS,
                piso_da_janela_em_segundos=PISO_DA_JANELA,
            )
            assert taxa.evidencia.n == 20, (
                f"a ancora entrou no denominador da grandeza {grandeza!r}: sao "
                "21 amostras e 20 PASSOS, porque a primeira nao tem anterior"
            )

    def test_SESSAO_1_REINICIO_SESSAO_2_SOMA_OS_DOIS_TRECHOS(self):
        """O criterio 4 do roadmap: reiniciar nao inventa nem apaga renda.

        Nenhum estado atravessa o reinicio — cada sessao vira passos por conta
        propria, exatamente como o processo novo faria. O ganho total tem de ser
        a SOMA dos dois trechos, e nunca um delta atravessando o buraco.
        """
        primeira = sequencia_regular(n=11, passo_em_segundos=30.0)
        segunda = sequencia_regular(
            n=11,
            passo_em_segundos=30.0,
            comeco=primeira[-1].carimbo + 3_600.0,
            exp_inicial=500_000,
            adena_inicial=20_000_000,
        )

        passos_1 = passos_da_sequencia(primeira)
        passos_2 = passos_da_sequencia(segunda)

        ganho_1 = sum(
            p.ganho_de_exp_em_decimos for p in passos_1 if p.aceito
        )
        ganho_2 = sum(
            p.ganho_de_exp_em_decimos for p in passos_2 if p.aceito
        )

        assert ganho_1 == ganho_2 == 10_000
        assert ganho_1 + ganho_2 == 20_000, (
            "o ganho de duas sessoes e a SOMA das duas, e o criterio 4 do "
            "roadmap chama isso de 'reiniciar nao inventa nem apaga renda'"
        )

        atravessando = segunda[0].exp - primeira[-1].exp
        assert atravessando == 390_000
        assert ganho_1 + ganho_2 != atravessando, (
            "existe um delta ATRAVESSANDO o reinicio, e ele e "
            f"{atravessando} decimos que ninguem farmou. A primeira amostra "
            "depois do arranque e ANCORA e nao delta — e e dai, e nao de indice "
            "em disco, que sai a garantia do REG-02 (criterio 4 do roadmap)"
        )

        assert passos_2[0].descontinuidade == DESCONTINUIDADE_DA_ANCORA
        assert passos_2[0].ganho_de_exp_em_decimos is None


class TestOsDoisPisosDizemQualFaltou:
    """Um motivo generico obrigaria quem desenha a adivinhar."""

    def test_ABAIXO_DO_PISO_DE_AMOSTRAS_O_MOTIVO_NOMEIA_AS_AMOSTRAS(self):
        taxa = taxa_por_hora(
            passos_da_sequencia(sequencia_regular(n=3, passo_em_segundos=50.0)),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert taxa.por_hora is None
        assert "amostras_minimas_para_taxa" in taxa.motivo_da_ausencia
        assert taxa.evidencia.faltam == 6

    def test_ABAIXO_DO_PISO_DE_JANELA_O_MOTIVO_NOMEIA_A_JANELA(self):
        taxa = taxa_por_hora(
            passos_da_sequencia(sequencia_regular(n=9, passo_em_segundos=1.0)),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert taxa.por_hora is None
        assert "janela_minima_para_taxa_segundos" in taxa.motivo_da_ausencia
        assert taxa.evidencia.suficiente is True, (
            "este e o caso que o piso de amostras NAO pega: oito passos em oito "
            "segundos sao ruido com cara de taxa horaria, e o criterio 1 do "
            "roadmap manda anuncia-lo como ruido"
        )

    def test_OS_DOIS_MOTIVOS_SAO_TEXTOS_DIFERENTES(self):
        """Um teste que so afirme "motivo nao vazio" nos dois nao vale."""
        poucas = taxa_por_hora(
            passos_da_sequencia(sequencia_regular(n=3, passo_em_segundos=50.0)),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )
        curta = taxa_por_hora(
            passos_da_sequencia(sequencia_regular(n=9, passo_em_segundos=1.0)),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert poucas.motivo_da_ausencia != curta.motivo_da_ausencia, (
            "os dois pisos sao dois FATOS diferentes: oito amostras em quarenta "
            "segundos e oito amostras em duas horas nao valem o mesmo, e quem "
            "desenha precisa poder dizer QUAL faltou"
        )


class TestARecenciaEAUnidadeViajamJUNTO:
    """REND-06: a taxa nunca e um numero nu."""

    def test_ATE_SAI_PREENCHIDO_MESMO_QUANDO_POR_HORA_E_NULO(self):
        amostras = sequencia_regular(n=9, passo_em_segundos=1.0)
        taxa = taxa_por_hora(
            passos_da_sequencia(amostras),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert taxa.por_hora is None
        assert taxa.ate == amostras[-1].carimbo, (
            "a recencia e um fato SEPARADO do valor: mesmo sem numero a dizer, "
            "quem desenha precisa saber de quando e a ultima amostra que entrou"
        )

    def test_A_UNIDADE_DA_JANELA_VIAJA_ESCRITA(self):
        taxa = taxa_por_hora(
            passos_da_sequencia(sequencia_regular(n=21, passo_em_segundos=30.0)),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert taxa.unidade_da_janela == "minutos farmados"
        assert UNIDADE_DA_JANELA == "minutos farmados", (
            "`minutos farmados` e um fato diferente de `minutos de relogio`, e "
            "sem a palavra viajando junto do numero quem desenha a tela le a "
            "taxa como se o denominador fosse o relogio"
        )


class TestAAritmeticaEExata:
    """Nenhum `float` participa de diferenca ou de acumulo (T-02-13)."""

    def test_POR_HORA_E_POR_MINUTO_SAO_FRACTION(self):
        taxa = taxa_por_hora(
            passos_da_sequencia(sequencia_regular(n=21, passo_em_segundos=30.0)),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert isinstance(taxa.por_hora, Fraction)
        assert isinstance(taxa.por_minuto, Fraction)
        assert taxa.por_minuto * 60 == taxa.por_hora
        assert taxa.por_minuto == 2_000

    def test_SEM_TAXA_OS_DOIS_SAO_NULOS_JUNTOS(self):
        taxa = taxa_por_hora(
            passos_da_sequencia(sequencia_regular(n=3, passo_em_segundos=50.0)),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert taxa.por_hora is None
        assert taxa.por_minuto is None

    def test_NENHUMA_CONVERSAO_A_PONTO_FLUTUANTE_NO_MODULO(self):
        assert chamadas_de(FONTE_DA_CONTA, {"float", "total_seconds"}) == [], (
            "a arvore ja mediu `total_seconds()` devolvendo `69713.696` onde o "
            "inteiro dizia `69713`. Diferenca sobre binario de ponto flutuante "
            "acumula erro que ninguem consegue ver depois de gravado — a divisao "
            "e `Fraction` e o resto e inteiro escalado"
        )

    def test_O_MODULO_TEM_DOCSTRING(self):
        assert rc.__doc__ is not None


# ---------------------------------------------------------------------------
# A DISPONIBILIDADE MEDIDA, e ela e o portao que discrimina
# ---------------------------------------------------------------------------
#
# AS TRES TAXAS DE RECUSA SAO RECEITA DE CONSTRUCAO DA ENTRADA, E NUNCA VALOR
# ESPERADO DA SAIDA. Elas vem de `02-CONTEXT.md:150` — nivel 79%, adena 21%, EXP
# 0%, sobre um denominador de 14 amostras, escrito na mesma linha. Mover 79% para
# 70% amanha nao muda nenhuma assercao deste teste: o que se afirma e que a taxa
# SAI e qual e o `n`.
#
# AS MASCARAS SAO DETERMINISTICAS POR CONSTRUCAO e nao por semente: `(i * 37) %
# 100 < 21` acerta exatamente 21 presencas a cada 100 indices, porque 37 e primo
# com 100 e o produto percorre todos os cem residuos. `(i * 53) % 100 < 79` faz o
# mesmo com 79. Os dois multiplicadores sao diferentes para que as duas recusas
# NAO andem em lockstep — se andassem, "o nivel recusou" e "a adena recusou"
# seriam o mesmo evento e o teste nao mediria o que afirma medir.
#
# Um portao que falha uma vez a cada dez execucoes e ruido, e ruido e o que este
# workstream existe para nao produzir.
AMOSTRAS_DA_DISPONIBILIDADE = 600
PRESENCA_DO_NIVEL_EM_CEM = 21
PRESENCA_DA_ADENA_EM_CEM = 79


def o_nivel_leu(indice: int) -> bool:
    return (indice * 37) % 100 < PRESENCA_DO_NIVEL_EM_CEM


def a_adena_leu(indice: int) -> bool:
    return (indice * 53) % 100 < PRESENCA_DA_ADENA_EM_CEM


def sequencia_da_disponibilidade(*, comeco: float = 1_700_000_000.0):
    """Dez minutos a ~1 Hz sob as recusas MEDIDAS. `(campos, carimbo)`.

    Ela e construida para NAO acionar por acidente nenhuma das outras guardas:
    nivel constante onde presente, EXP subindo dentro da mesma faixa e sem
    chegar perto dos 100 pontos percentuais, adena subindo sem salto de ordem de
    grandeza, e carimbos a exatamente 1 s — bem abaixo do limiar de lacuna.
    """
    return [
        (
            campos(
                nivel=67 if o_nivel_leu(indice) else None,
                exp=100_000 + indice * 100,
                adena=(
                    10_000_000 + indice * 5_000 if a_adena_leu(indice) else None
                ),
            ),
            comeco + indice * 1.0,
        )
        for indice in range(AMOSTRAS_DA_DISPONIBILIDADE)
    ]


class TestADisponibilidadeMedida:
    """O criterio 1 do roadmap sob a disponibilidade REAL, e nao sob a total.

    Um teste que so usasse amostras completas provaria o criterio num mundo em
    que o nivel sempre le — e ele le em ~21% dos tiques (`02-CONTEXT.md:150`,
    sobre 14 amostras).
    """

    def test_AS_MASCARAS_ENTREGAM_AS_RECUSAS_MEDIDAS(self):
        """A receita e conferida ANTES de o teste principal se apoiar nela."""
        niveis = sum(1 for i in range(AMOSTRAS_DA_DISPONIBILIDADE) if o_nivel_leu(i))
        adenas = sum(1 for i in range(AMOSTRAS_DA_DISPONIBILIDADE) if a_adena_leu(i))

        assert niveis == 126, "21 presencas a cada 100 indices, em 600 indices"
        assert adenas == 474, "79 presencas a cada 100 indices, em 600 indices"
        assert niveis != adenas, (
            "as duas mascaras nao podem andar em lockstep, senao 'o nivel "
            "recusou' e 'a adena recusou' viram o mesmo evento"
        )

    def test_O_EXP_SAI_COM_TODOS_OS_INTERVALOS_APESAR_DO_NIVEL_RECUSADO(self):
        passos = passos_dos_campos(sequencia_da_disponibilidade())

        taxa = taxa_por_hora(
            passos,
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert taxa.por_hora is not None, taxa.motivo_da_ausencia
        assert taxa.evidencia.n == 599, (
            "ESTE E O NUMERO QUE DISCRIMINA. A recusa de EXP e 0% "
            "(`02-CONTEXT.md:150`, sobre 14 amostras), entao TODOS os 599 "
            "intervalos de 600 amostras tem de contar. Sob a regra que caiu — "
            "passo de EXP so quando os DOIS lados trazem nivel — sobrariam "
            "0,21 x 0,21 = 4,4% dos pares, ou seja `n` da ordem de 26 e janela "
            "farmada de ~26 s, ABAIXO do piso de 120 s, e `por_hora` sairia "
            "`None`. Uma assercao que so pedisse 'nao nulo' passaria nas duas "
            f"regras e nao provaria nada. Saiu n={taxa.evidencia.n}"
        )
        assert taxa.janela_farmada_em_segundos == 599.0
        assert taxa.lacunas_excluidas == 0
        assert taxa.segundos_em_lacuna == 0.0

    def test_A_ADENA_SAI_COM_OS_PARES_EM_QUE_ELA_FOI_LIDA_DOS_DOIS_LADOS(self):
        passos = passos_dos_campos(sequencia_da_disponibilidade())

        taxa = taxa_por_hora(
            passos,
            grandeza=GRANDEZA_DA_ADENA,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        # DERIVADO DA MESMA MASCARA que construiu a sequencia, e nunca escrito a
        # mao: um numero copiado aqui envelheceria em silencio se a receita
        # mudasse, e o teste continuaria verde medindo outra coisa.
        pares_com_adena = sum(
            1
            for i in range(1, AMOSTRAS_DA_DISPONIBILIDADE)
            if a_adena_leu(i - 1) and a_adena_leu(i)
        )

        assert taxa.por_hora is not None, taxa.motivo_da_ausencia
        assert taxa.evidencia.n == pares_com_adena, (
            "o `n` da adena e o numero de pares em que ela foi lida DOS DOIS "
            f"LADOS: {pares_com_adena}. Saiu {taxa.evidencia.n}"
        )
        assert taxa.evidencia.n >= PISO_DE_AMOSTRAS
        assert taxa.janela_farmada_em_segundos >= PISO_DA_JANELA, (
            "dez minutos de farm a ~1 Hz tem de produzir janela farmada acima "
            "do piso tambem para a adena, com a recusa de 21% medida"
        )

    def test_O_NIVEL_RECUSADO_NAO_REDUZ_O_N_DO_EXP_EM_UM_UNICO_PASSO(self):
        """O mesmo `n` com e sem o nivel: 599 dos dois jeitos.

        O CONTROLE que prova que a assercao de cima nao passa por acidente: uma
        sequencia identica com o nivel SEMPRE presente da o mesmo `n`. Se a
        guarda tivesse virado supressao, os dois numeros divergiriam.
        """
        com_recusa = taxa_por_hora(
            passos_dos_campos(sequencia_da_disponibilidade()),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )
        sem_recusa = taxa_por_hora(
            passos_dos_campos(
                [
                    (
                        campos(
                            nivel=67,
                            exp=100_000 + indice * 100,
                            adena=10_000_000 + indice * 5_000,
                        ),
                        1_700_000_000.0 + indice * 1.0,
                    )
                    for indice in range(AMOSTRAS_DA_DISPONIBILIDADE)
                ]
            ),
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert com_recusa.evidencia.n == sem_recusa.evidencia.n == 599
        assert com_recusa.por_hora == sem_recusa.por_hora, (
            "o nivel recusado em 79% dos tiques nao pode mudar a taxa de EXP: "
            "com o EXP subindo nao existe level up a supor, e o ganho e o mesmo "
            "com e sem o nivel"
        )


class TestODenominadorEPorGrandeza:
    """A `janela_farmada` de uma grandeza nao e a da outra, e isso e o desenho."""

    def test_A_JANELA_DA_ADENA_E_MAIOR_QUE_A_DO_EXP_QUANDO_O_EXP_CAIU(self):
        """Passos com o nivel recusado e o EXP caindo saem do denominador do EXP
        e CONTINUAM no da adena, e as duas taxas saem da MESMA sequencia."""
        pares = []
        exp = 500_000
        adena = 10_000_000
        for indice in range(40):
            # Um em cada quatro tiques o EXP cai (morte), e o nivel nunca le.
            if indice % 4 == 3:
                exp = exp - 20_000
            else:
                exp = exp + 1_000
            adena = adena + 5_000
            pares.append(
                (campos(nivel=None, exp=exp, adena=adena), indice * 5.0)
            )

        passos = passos_dos_campos(pares)

        do_exp = taxa_por_hora(
            passos,
            grandeza=GRANDEZA_DO_EXP,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )
        da_adena = taxa_por_hora(
            passos,
            grandeza=GRANDEZA_DA_ADENA,
            piso_de_amostras=PISO_DE_AMOSTRAS,
            piso_da_janela_em_segundos=PISO_DA_JANELA,
        )

        assert da_adena.janela_farmada_em_segundos > do_exp.janela_farmada_em_segundos, (
            "o denominador e POR GRANDEZA: os passos em que o EXP caiu com o "
            "nivel recusado sairam do denominador do EXP, e a adena daqueles "
            "mesmos passos e perfeitamente boa. Adena: "
            f"{da_adena.janela_farmada_em_segundos}s, EXP: "
            f"{do_exp.janela_farmada_em_segundos}s"
        )
        assert do_exp.por_hora is not None
        assert da_adena.por_hora is not None
        assert da_adena.evidencia.n == 39
        assert do_exp.evidencia.n == 39 - 10
