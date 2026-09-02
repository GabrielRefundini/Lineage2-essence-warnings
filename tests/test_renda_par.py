"""As tres recusas que so existem quando ha um PAR — e a prova de que distinguem.

O QUE ESTE ARQUIVO EXISTE PARA IMPEDIR
======================================
**Um numero valido, plausivel e errado sendo gravado como se fosse certo.**

E o modo de falha mais caro deste projeto, e a docstring de `numero_valido` ja
o nomeia: a gramatica pega glifo perdido e glifo a mais, e **nao pega
SUBSTITUICAO**. `100,00` e `180,00` sao os dois validos. Para esse modo servem
a margem calibrada, a guarda de cruzamento e o **acordo entre dois frames** —
e este arquivo e o acordo entre dois frames da renda.

**Nenhuma outra coisa na Fase 1 enxerga isso.** Nem a gramatica, nem o
cruzamento de escalas, nem a peneira de forma do caminho de glifo. Por isso
estas tres regras nascem aqui, mesmo que so a Fase 2 as va chamar.

OS TRES CASOS DE HONRA, E OS DOIS MELHORES VIERAM DO ADENDO DE CAMPO
====================================================================
Todos exercitam o mesmo modo: um numero que passou em `numero_valido`, passou
em `inteiro_de_quantidade`, e esta errado por ordens de grandeza.

    M19    `8.786`     contra `10.673.628`   -- o recorte cru em que a adena
                                                NAO aparece; tres ordens
    M-G a  `106.020`   contra  `1.696.020`   -- Yazalaque, medido em campo.
                                                O MAIS PERIGOSO: parece adena
    M-G b  `91`        contra `13.160.684`   -- Faerlina, medido em campo.
                                                O MAIS DURO: cinco ordens

**A troca do leitor da adena para o caminho de glifo NAO os tornou
redundantes.** A guarda de forma pega recorte que PERDEU o numero; ela nao pega
recorte deslocado para o campo do lado, porque o vizinho tem os proprios icones
nas proprias pontas e passa na forma exatamente como o campo certo. O M-H
mediu o quanto isso e provavel: quando o recorte encosta, as duas escalas
concordaram na L-Coin **173 vezes em 173**. Ninguem remove estes testes por
parecerem historicos.

A FASE 1 CONTINUA SEM ESTADO (CTX-9)
====================================
As tres sao funcoes puras sobre um par passado por parametro, e **nenhum
caminho de producao desta fase as chama** — porque uma fase sem memoria nao tem
a leitura anterior. Quem as chama e a Fase 2. Um portao de arvore de sintaxe no
fim deste arquivo afirma que o modulo nao ganhou memoria, com controle
positivo.

ESTE ARQUIVO NAO PULA POR NADA
==============================
Ele nao depende de OCR nem de pixel: e aritmetica inteira sobre pares montados
a mao. Um `skip` aqui e falha, e nao configuracao de maquina.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from l2scanner import renda_leitura as rl
from l2scanner.renda_leitura import LeituraDaRenda

FONTE_DO_MODULO_PURO = Path(__file__).parent.parent / "l2scanner" / "renda_leitura.py"

# O prefixo dos motivos deste modulo. O portao da distincao DERIVA a lista do
# modulo em vez de repeti-la: uma lista escrita a mao aqui envelheceria em
# silencio no dia em que um motivo novo nascesse.
PREFIXO_DO_MOTIVO = "MOTIVO_"

# Quantos motivos o modulo tem HOJE, contados na onda 3: cinco do `01-01`
# (recorte fora do frame, campo vazio, gramatica, discordancia, personagem),
# dois do `01-05` (forma do recorte, run anormalmente largo), dois do `01-04`
# Tarefa 1 (conjunto de moldes, pontuacao dos glifos) e tres desta tarefa (EXP
# para tras, nivel para tras, salto da adena).
#
# A CONTAGEM EXISTE PARA QUE FUNDIR DOIS MOTIVOS DERRUBE ALGUMA COISA. Sem ela,
# um modulo com um motivo so passaria no teste de distincao com folga. Ela e um
# PISO e nao uma igualdade: motivo novo entra sem cerimonia, motivo fundido nao.
MOTIVOS_DECLARADOS = 12

# Um fator de salto de exemplo. Ele NAO mora no fonte: quem tem duas leituras e
# a Fase 2, e e la que ele vem do `config.toml` do usuario. Aqui ele e um
# argumento de teste, e por isso pode ser um literal.
FATOR = 10


def leitura(*, nivel: int, exp: int, adena: int, carimbo: float = 0.0):
    """Uma `LeituraDaRenda` montada a mao. Sem pixel, sem OCR, sem relogio."""
    return LeituraDaRenda(
        personagem="Faerlina",
        nivel=nivel,
        exp=exp,
        adena=adena,
        carimbo=carimbo,
    )


# ---------------------------------------------------------------------------
# O PAR DE CAMPO, e ele e REAL. Ver a docstring da classe que o usa.
# ---------------------------------------------------------------------------
LEVEL_UP_ANTES = leitura(nivel=66, exp=685_632, adena=10_673_628)
LEVEL_UP_DEPOIS = leitura(nivel=67, exp=80_012, adena=13_160_684)


class TestOParDeCampoComOLevelUpVerdadeiro:
    """O CONTROLE NEGATIVO das tres regras, e ele aconteceu na tela do usuario.

    PROCEDENCIA DAS DUAS PONTAS, e as duas estao gravadas em disco:

        2026-09-01 ~23h50   o spike leu   nivel 66, EXP 68,5632%, adena 10.673.628
        2026-09-02 ~00h45   a medicao leu nivel 67, EXP  8,0012%, adena 13.160.684

    A segunda ponta e a verdade de campo de `01-MEDICOES-DE-CAMPO.md` (achado
    M-B), a mesma que `tests/fixtures/renda/LEIA-ME.md` escreve. E um **level up
    de verdade**, 55 minutos depois.

    ELE EXERCITA AS TRES REGRAS DE UMA VEZ E NENHUMA PODE RECUSAR:

    - o EXP CAIU (68,5632% -> 8,0012%), mas o nivel mudou -> a regra do EXP se
      ABSTEM, porque subir de nivel zera o EXP;
    - o nivel SUBIU -> a regra do nivel so olha para baixo;
    - a adena cresceu ~23% -> muito abaixo de qualquer fator de salto razoavel.

    **Um controle negativo inventado prova que a regra nao dispara com numeros
    que o autor escolheu; este prova que ela nao dispara com o que aconteceu na
    tela do usuario.**

    O QUE ELE *NAO* E DESTA FASE: a conta `(100 - 68,5632) + 8,0012 = 39,438`
    pontos percentuais em 55 minutos e o **REND-03**, e ela pertence a Fase 2.
    A Fase 1 so precisa que as tres regras se CALEM neste par; a Fase 2 herda o
    par para fazer a conta, e esta nota fica escrita aqui para que ela nao seja
    reinventada com numeros sinteticos la.
    """

    def test_AS_TRES_REGRAS_SE_CALAM_NUM_LEVEL_UP_VERDADEIRO(self):
        assert (
            rl.conferir_o_par(
                LEVEL_UP_ANTES, LEVEL_UP_DEPOIS, fator_de_salto=FATOR
            )
            == ()
        )

    def test_A_REGRA_DO_EXP_SE_ABSTEM_PORQUE_O_NIVEL_MUDOU(self):
        assert LEVEL_UP_DEPOIS.exp < LEVEL_UP_ANTES.exp, (
            "o par deixou de exercitar a regra do EXP: se o EXP nao cai, o "
            "controle negativo nao controla nada"
        )
        assert rl.o_exp_andou_para_tras(LEVEL_UP_ANTES, LEVEL_UP_DEPOIS) is None

    def test_A_REGRA_DO_NIVEL_SE_CALA_PORQUE_ELE_SUBIU(self):
        assert rl.o_nivel_andou_para_tras(LEVEL_UP_ANTES, LEVEL_UP_DEPOIS) is None

    def test_A_REGRA_DA_ADENA_SE_CALA_PORQUE_ELA_CRESCEU_23_PORCENTO(self):
        assert (
            rl.a_adena_saltou_ordem_de_grandeza(
                LEVEL_UP_ANTES, LEVEL_UP_DEPOIS, fator_de_salto=FATOR
            )
            is None
        )


class TestOExpAndandoParaTras:
    """Ela responde a UMA pergunta: o EXP caiu com o nivel PARADO?"""

    def test_COM_O_NIVEL_PARADO_O_EXP_MENOR_RECUSA(self):
        recusa = rl.o_exp_andou_para_tras(
            leitura(nivel=67, exp=80_012, adena=100),
            leitura(nivel=67, exp=70_000, adena=100),
        )
        assert recusa is not None
        assert recusa.motivo == rl.MOTIVO_DO_EXP_PARA_TRAS
        assert recusa.campo == rl.CAMPO_DO_EXP

    def test_CONTROLE_NEGATIVO_O_EXP_SUBINDO_NAO_RECUSA(self):
        """O evento mais normal do jogo: farmar."""
        assert (
            rl.o_exp_andou_para_tras(
                leitura(nivel=67, exp=80_012, adena=100),
                leitura(nivel=67, exp=90_000, adena=100),
            )
            is None
        )

    def test_CONTROLE_NEGATIVO_SUBIR_DE_NIVEL_ZERA_O_EXP_E_NAO_RECUSA(self):
        assert (
            rl.o_exp_andou_para_tras(
                leitura(nivel=66, exp=990_000, adena=100),
                leitura(nivel=67, exp=1_200, adena=100),
            )
            is None
        )

    def test_O_EXP_IGUAL_NAO_RECUSA(self):
        """Parado nao e para tras. Um `<=` aqui recusaria toda tela pausada."""
        assert (
            rl.o_exp_andou_para_tras(
                leitura(nivel=67, exp=80_012, adena=100),
                leitura(nivel=67, exp=80_012, adena=100),
            )
            is None
        )

    def test_COM_O_NIVEL_DESCENDO_A_REGRA_DO_EXP_SE_ABSTEM(self):
        """Cada recusa responde a UMA pergunta: o mesmo fato nao produz duas.

        Um nivel que desce ja tem a sua propria recusa. Se a regra do EXP
        tambem disparasse ali, um unico digito trocado no nivel produziria DUAS
        recusas e quem lesse a tela procuraria dois problemas.
        """
        assert (
            rl.o_exp_andou_para_tras(
                leitura(nivel=67, exp=800_000, adena=100),
                leitura(nivel=66, exp=1_000, adena=100),
            )
            is None
        )


class TestONivelAndandoParaTras:
    """O caminho comum para um nivel que desce nao e o jogo: e substituicao."""

    def test_O_NIVEL_MENOR_NO_SEGUNDO_RECUSA(self):
        recusa = rl.o_nivel_andou_para_tras(
            leitura(nivel=67, exp=80_012, adena=100),
            leitura(nivel=57, exp=80_012, adena=100),
        )
        assert recusa is not None
        assert recusa.motivo == rl.MOTIVO_DO_NIVEL_PARA_TRAS
        assert recusa.campo == rl.CAMPO_DO_NIVEL

    def test_CONTROLE_NEGATIVO_SUBIR_DE_NIVEL_NAO_RECUSA(self):
        assert (
            rl.o_nivel_andou_para_tras(
                leitura(nivel=66, exp=990_000, adena=100),
                leitura(nivel=67, exp=1_200, adena=100),
            )
            is None
        )

    def test_CONTROLE_NEGATIVO_O_NIVEL_PARADO_NAO_RECUSA(self):
        assert (
            rl.o_nivel_andou_para_tras(
                leitura(nivel=67, exp=80_012, adena=100),
                leitura(nivel=67, exp=90_000, adena=100),
            )
            is None
        )

    def test_A_SUBSTITUICAO_QUE_ELA_PEGA_PASSA_EM_numero_valido(self):
        """O par `67` -> `57` e a prova de que a gramatica nao bastava.

        Os dois sao numeros perfeitamente validos, e nenhuma peneira de FORMA
        desta arvore os distingue. So a comparacao com a leitura anterior pega.
        """
        from l2scanner.mercado_leitura import numero_valido

        assert numero_valido("67") and numero_valido("57")
        assert (
            rl.o_nivel_andou_para_tras(
                leitura(nivel=67, exp=1, adena=100),
                leitura(nivel=57, exp=1, adena=100),
            )
            is not None
        )


class TestAAdenaSaltandoOrdemDeGrandeza:
    """A regra e sobre a RAZAO, e nunca sobre a direcao."""

    def test_CRESCER_ACIMA_DO_FATOR_RECUSA(self):
        recusa = rl.a_adena_saltou_ordem_de_grandeza(
            leitura(nivel=67, exp=1, adena=1_000_000),
            leitura(nivel=67, exp=1, adena=50_000_000),
            fator_de_salto=FATOR,
        )
        assert recusa is not None
        assert recusa.motivo == rl.MOTIVO_DO_SALTO_DA_ADENA
        assert recusa.campo == rl.CAMPO_DA_ADENA

    def test_CAIR_ABAIXO_DO_FATOR_TAMBEM_RECUSA(self):
        """A direcao nao e criterio: gastar e normal, saltar ordem nao e."""
        recusa = rl.a_adena_saltou_ordem_de_grandeza(
            leitura(nivel=67, exp=1, adena=50_000_000),
            leitura(nivel=67, exp=1, adena=1_000_000),
            fator_de_salto=FATOR,
        )
        assert recusa is not None
        assert recusa.motivo == rl.MOTIVO_DO_SALTO_DA_ADENA

    def test_CONTROLE_NEGATIVO_GASTAR_DENTRO_DO_FATOR_NAO_RECUSA(self):
        """Comprar uma coisa cara e um evento normal do jogo."""
        assert (
            rl.a_adena_saltou_ordem_de_grandeza(
                leitura(nivel=67, exp=1, adena=13_160_684),
                leitura(nivel=67, exp=1, adena=2_000_000),
                fator_de_salto=FATOR,
            )
            is None
        )

    def test_CONTROLE_NEGATIVO_GANHAR_DE_LOOT_NAO_RECUSA(self):
        assert (
            rl.a_adena_saltou_ordem_de_grandeza(
                leitura(nivel=67, exp=1, adena=10_673_628),
                leitura(nivel=67, exp=1, adena=13_160_684),
                fator_de_salto=FATOR,
            )
            is None
        )

    def test_COM_ZERO_DE_UM_DOS_LADOS_A_REGRA_SE_ABSTEM(self):
        """Nao existe ordem de grandeza em relacao a zero.

        Toda razao contra zero e infinita, e a regra recusaria SEMPRE. O caso
        do zero pertence a recusa de campo vazio e a de gramatica, que ja
        existem e apontam para o conserto certo.
        """
        for antes, depois in ((0, 13_160_684), (13_160_684, 0), (0, 0)):
            assert (
                rl.a_adena_saltou_ordem_de_grandeza(
                    leitura(nivel=67, exp=1, adena=antes),
                    leitura(nivel=67, exp=1, adena=depois),
                    fator_de_salto=FATOR,
                )
                is None
            ), (antes, depois)

    def test_EXATAMENTE_NO_FATOR_NAO_RECUSA(self):
        """A fronteira e declarada: o fator e o limite ACEITO, nao o rejeitado."""
        assert (
            rl.a_adena_saltou_ordem_de_grandeza(
                leitura(nivel=67, exp=1, adena=1_000),
                leitura(nivel=67, exp=1, adena=10_000),
                fator_de_salto=FATOR,
            )
            is None
        )

    def test_O_FATOR_NAO_TEM_VALOR_DE_FABRICA(self):
        """Um limiar por omissao e a definicao de constante magica."""
        with pytest.raises(TypeError):
            rl.a_adena_saltou_ordem_de_grandeza(
                leitura(nivel=67, exp=1, adena=1),
                leitura(nivel=67, exp=1, adena=2),
            )

    def test_conferir_o_par_TAMBEM_EXIGE_O_FATOR(self):
        with pytest.raises(TypeError):
            rl.conferir_o_par(LEVEL_UP_ANTES, LEVEL_UP_DEPOIS)


class TestOsTresCasosDeNumeroValidoPlausivelEErrado:
    """Os UNICOS testes desta fase que enxergam este modo de falha.

    Cada caso vai com a procedencia e o numero. Nenhum deles e sintetico: os
    tres sao leituras que aconteceram, contra a verdade do mesmo frame.

    **A troca do leitor da adena para o caminho de glifo NAO os tornou
    redundantes**, e isto vai escrito para quem for tentado a apaga-los: a
    guarda de forma pega recorte que PERDEU o numero, e nao recorte deslocado
    para o campo do lado — o vizinho tem os proprios icones nas proprias pontas
    e passa na forma exatamente como o campo certo. O M-H mediu o quanto isso e
    provavel: 173 concordancias, 173 na L-Coin.
    """

    @pytest.mark.parametrize(
        "verdade,lido,procedencia",
        [
            (
                10_673_628,
                8_786,
                "M19: a extracao do ultimo grupo valido sobre `Special 8,786`, "
                "o recorte cru em que a adena NAO aparece. Tres ordens de "
                "grandeza, com a gramatica inteira satisfeita",
            ),
            (
                1_696_020,
                106_020,
                "M-G: a Yazalaque por OCR mascarado, contra a verdade do mesmo "
                "frame. O MAIS PERIGOSO dos tres, porque 106.020 parece adena",
            ),
            (
                13_160_684,
                91,
                "M-G: a Faerlina por OCR mascarado, contra a verdade do mesmo "
                "frame. O MAIS DURO: cinco ordens de grandeza",
            ),
        ],
    )
    def test_conferir_o_par_RECUSA_O_NUMERO_PLAUSIVEL_E_ERRADO(
        self, verdade, lido, procedencia
    ):
        recusas = rl.conferir_o_par(
            leitura(nivel=67, exp=80_012, adena=verdade),
            leitura(nivel=67, exp=80_012, adena=lido),
            fator_de_salto=FATOR,
        )
        motivos = [recusa.motivo for recusa in recusas]
        assert rl.MOTIVO_DO_SALTO_DA_ADENA in motivos, (
            f"{procedencia}\n  passou sem recusa: {verdade} -> {lido}"
        )

    def test_OS_TRES_PASSAM_NA_GRAMATICA_INTEIRA_E_E_POR_ISSO_QUE_DOEM(self):
        """A prova de que nenhuma trava de FORMA os pegaria."""
        from l2scanner.mercado_leitura import inteiro_de_quantidade, numero_valido

        for texto, inteiro in (("8,786", 8_786), ("106,020", 106_020), ("91", 91)):
            assert numero_valido(texto), texto
            assert inteiro_de_quantidade(texto) == inteiro, texto


class TestConferirOPar:
    """Todas as recusas, e nao a primeira."""

    def test_UM_PAR_COERENTE_DEVOLVE_TUPLA_VAZIA(self):
        assert (
            rl.conferir_o_par(
                leitura(nivel=67, exp=80_012, adena=1_000_000),
                leitura(nivel=67, exp=90_000, adena=1_100_000),
                fator_de_salto=FATOR,
            )
            == ()
        )

    def test_DOIS_PROBLEMAS_PRODUZEM_DUAS_RECUSAS_E_NAO_UMA(self):
        """Esconder o segundo atras do primeiro custaria a evidencia inteira."""
        recusas = rl.conferir_o_par(
            leitura(nivel=67, exp=80_012, adena=13_160_684),
            leitura(nivel=57, exp=80_012, adena=91),
            fator_de_salto=FATOR,
        )
        motivos = {recusa.motivo for recusa in recusas}
        assert motivos == {
            rl.MOTIVO_DO_NIVEL_PARA_TRAS,
            rl.MOTIVO_DO_SALTO_DA_ADENA,
        }, recusas

    def test_A_TUPLA_E_IMUTAVEL_E_NAO_UMA_LISTA(self):
        assert isinstance(
            rl.conferir_o_par(
                LEVEL_UP_ANTES, LEVEL_UP_DEPOIS, fator_de_salto=FATOR
            ),
            tuple,
        )


def motivos_do_modulo() -> dict[str, str]:
    """Os motivos DERIVADOS do modulo, e nunca uma lista escrita a mao.

    E a mesma funcao que o portao e o controle positivo usam. Um controle que
    reimplementasse a coleta provaria que a reimplementacao funciona, e nao que
    o portao funciona.
    """
    return {
        nome: valor
        for nome, valor in vars(rl).items()
        if nome.startswith(PREFIXO_DO_MOTIVO) and isinstance(valor, str)
    }


def duplicados(motivos: dict[str, str]) -> dict[str, list[str]]:
    """`{valor: [nomes]}` para os valores que aparecem mais de uma vez."""
    por_valor: dict[str, list[str]] = {}
    for nome, valor in motivos.items():
        por_valor.setdefault(valor, []).append(nome)
    return {valor: nomes for valor, nomes in por_valor.items() if len(nomes) > 1}


class TestOPortaoDaDistincaoDosMotivos:
    """O criterio 3 do roadmap virado teste: cada recusa nomeada e DISTINTA.

    A razao nao e estetica: **os consertos sao diferentes**. Campo vazio aponta
    para o retangulo ou o piso; gramatica aponta so para o piso; conjunto
    incompleto aponta para uma rodada do cortador; personagem aponta para o
    calibrador. Fundir dois deles "porque parecem a mesma coisa" faz dois
    consertos diferentes parecerem o mesmo, e custa uma noite a quem for
    seguir a mensagem.
    """

    def test_TODOS_OS_MOTIVOS_SAO_DISTINTOS_DOIS_A_DOIS(self):
        repetidos = duplicados(motivos_do_modulo())
        assert not repetidos, (
            "dois motivos com o MESMO valor:\n  "
            + "\n  ".join(
                f"{valor!r} <- {', '.join(nomes)}"
                for valor, nomes in repetidos.items()
            )
        )

    def test_A_CONTAGEM_NAO_CAIU_ABAIXO_DO_DECLARADO(self):
        """Sem isto, fundir dois motivos passaria com folga no teste acima."""
        motivos = motivos_do_modulo()
        assert len(motivos) >= MOTIVOS_DECLARADOS, (
            f"o modulo tem {len(motivos)} motivos e o teste declara "
            f"{MOTIVOS_DECLARADOS}. Se um motivo foi FUNDIDO com outro, dois "
            f"consertos diferentes viraram a mesma mensagem: {sorted(motivos)}"
        )

    def test_AS_TRES_RECUSAS_DE_PAR_SAO_DISTINTAS_DAS_DO_01_01(self):
        do_par = {
            rl.MOTIVO_DO_EXP_PARA_TRAS,
            rl.MOTIVO_DO_NIVEL_PARA_TRAS,
            rl.MOTIVO_DO_SALTO_DA_ADENA,
        }
        de_um_frame_so = {
            rl.MOTIVO_DO_RECORTE_FORA_DO_FRAME,
            rl.MOTIVO_DO_CAMPO_VAZIO,
            rl.MOTIVO_DA_GRAMATICA,
            rl.MOTIVO_DA_DISCORDANCIA,
            rl.MOTIVO_DO_PERSONAGEM,
        }
        assert len(do_par) == 3
        assert not (do_par & de_um_frame_so)

    def test_CONTROLE_POSITIVO_UM_VALOR_DUPLICADO_E_ACUSADO_PELO_NOME(self):
        """Sem ele, o portao passa de maos dadas com uma conferencia vazia."""
        repetidos = duplicados(
            {
                "MOTIVO_DO_CAMPO_VAZIO": "campo-vazio",
                "MOTIVO_DA_GRAMATICA": "campo-vazio",
                "MOTIVO_DO_PERSONAGEM": "personagem",
            }
        )
        assert repetidos == {
            "campo-vazio": ["MOTIVO_DO_CAMPO_VAZIO", "MOTIVO_DA_GRAMATICA"]
        }

    def test_O_CONTROLE_CHAMA_A_MESMA_FUNCAO_QUE_O_PORTAO(self):
        arvore = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        definicoes = [
            no.name for no in ast.walk(arvore) if isinstance(no, ast.FunctionDef)
        ]
        assert definicoes.count("duplicados") == 1


def memoria_de_modulo(caminho: Path) -> list[str]:
    """As marcas de estado vivo num fonte: `global` e mutavel no nivel do modulo.

    Compartilhada pelo portao e pelo controle positivo, pela mesma razao de
    `duplicados`.
    """
    arvore = ast.parse(Path(caminho).read_text(encoding="utf-8"))
    achados: list[str] = []

    for no in ast.walk(arvore):
        if isinstance(no, ast.Global):
            achados.append(f"linha {no.lineno}: global {', '.join(no.names)}")

    for no in arvore.body:
        if not isinstance(no, (ast.Assign, ast.AnnAssign)):
            continue
        valor = no.value
        if isinstance(valor, (ast.List, ast.Dict, ast.Set)):
            alvos = no.targets if isinstance(no, ast.Assign) else [no.target]
            nomes = [getattr(a, "id", "?") for a in alvos]
            achados.append(
                f"linha {no.lineno}: {', '.join(nomes)} = literal MUTAVEL de "
                f"nivel de modulo"
            )
    return achados


class TestOPortaoDaAusenciaDeMemoria:
    """A forma EXECUTAVEL de "a Fase 1 e sem estado" (CTX-9).

    Um leitor com memoria mente sobre a tela ATUAL usando a tela passada. As
    tres regras de par sao o jeito certo de comparar dois frames — puras, sobre
    um par que chega por parametro — e este portao existe para que ninguem
    "conserte" a ausencia de chamador ligando um acumulador dentro do modulo.
    """

    def test_O_MODULO_PURO_NAO_DECLARA_ESCOPO_GLOBAL_NEM_ACUMULADOR(self):
        achados = memoria_de_modulo(FONTE_DO_MODULO_PURO)
        assert not achados, (
            "renda_leitura.py ganhou memoria:\n  " + "\n  ".join(achados)
        )

    def test_CONTROLE_POSITIVO_UM_ACUMULADOR_DE_MODULO_E_ACUSADO(self, tmp_path):
        alvo = tmp_path / "com_memoria.py"
        alvo.write_text(
            "ULTIMA_LEITURA = {}\n"
            "\n"
            "def lembrar(x):\n"
            "    global ULTIMA_LEITURA\n"
            "    ULTIMA_LEITURA = x\n",
            encoding="utf-8",
        )
        achados = memoria_de_modulo(alvo)
        assert len(achados) == 2, achados
        assert any("global" in a for a in achados)
        assert any("MUTAVEL" in a for a in achados)

    def test_NENHUM_CAMINHO_DE_PRODUCAO_DESTA_FASE_CHAMA_AS_TRES_REGRAS(self):
        """Elas nascem aqui e sao chamadas na Fase 2. E de proposito.

        Uma fase sem memoria nao tem a leitura anterior — nao existe segunda
        leitura para passar. A varredura e sobre a arvore, e nao sobre `grep`,
        para que a prosa que explica as regras atravesse.
        """
        raiz = FONTE_DO_MODULO_PURO.parent
        das_regras = {
            "o_exp_andou_para_tras",
            "o_nivel_andou_para_tras",
            "a_adena_saltou_ordem_de_grandeza",
            "conferir_o_par",
        }
        chamadas = []
        for modulo in sorted(raiz.glob("*.py")):
            arvore = ast.parse(modulo.read_text(encoding="utf-8"))
            for no in ast.walk(arvore):
                if not isinstance(no, ast.Call):
                    continue
                nome = getattr(no.func, "id", None) or getattr(
                    no.func, "attr", None
                )
                if nome in das_regras:
                    chamadas.append(f"{modulo.name}:{no.lineno} -> {nome}")
        # As chamadas DENTRO de `conferir_o_par` sao a composicao dela, e nao
        # producao: elas moram no proprio modulo puro e nao tem chamador.
        de_fora = [c for c in chamadas if not c.startswith("renda_leitura.py")]
        assert not de_fora, (
            "uma das regras de par ganhou chamador de producao nesta fase:\n  "
            + "\n  ".join(de_fora)
            + "\nA Fase 1 nao tem a leitura anterior. Quem chama e a Fase 2"
        )
