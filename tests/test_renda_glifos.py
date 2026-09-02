"""A peneira de forma da barra: `renda_leitura._glifos_do_numero`.

Ele e SINTETICO em quase tudo, e a razao nao e comodidade: os vetores de corrida
que ele monta a mao sao os que a medicao de campo produziu (M-J, M-K, M-L, M-N,
M-O), e monta-los aqui e o que permite afirmar cada regra da peneira ISOLADA —
sem OCR e sem `recordings/`. Uma peneira testada so contra o frame inteiro fica
verde por acidente: o frame certo passa por qualquer peneira que nao recuse
nada.

A EXCECAO, NO FIM DO ARQUIVO, LE AS FIXTURAS VERSIONADAS DE CAMPO — e ela e
deliberada. Os numeros da GEOMETRIA desta fonte nao podem sair de um bloco que
o proprio teste desenhou: isso seria afirmar a propria suposicao. Eles saem de
pixel de jogo, das quatro imagens que o `01-01` resgatou para
`tests/fixtures/renda/` e que vem em qualquer clone. Nao e `recordings/`, que e
gitignored (precedente literal: `tests/test_mercado_glifos.py:4-8`).

A CONVENCAO DE LARGURA E DECLARADA, E ELA JA CUSTOU UMA REFUTACAO A ESTA FASE
=============================================================================
Todas as larguras deste arquivo estao na convencao **EXCLUSIVA** (`fim -
inicio`) — a de `segmentar_glifos_no_brilho` e a de `larguras_de_molde`, que e
a convencao em que a peneira decide. O `01-MEDICOES-DE-CAMPO.md` relata os
MESMOS runs numa convencao **inclusiva** (`fim - inicio + 1`), e as duas diferem
por um pixel (M-P):

    elemento          neste arquivo (exclusiva)   no documento (inclusiva)
    digito                   4, 5, 6                      5, 6, 7
    virgula                     1                            2
    icone de ponta           14, 15                       15, 16

Uma peneira escrita com os numeros do documento, rodando na convencao do
codigo, RECUSA o digito mais largo e ACEITA um icone estreito — silencioso nos
dois sentidos. Por isso os vetores daqui sao os do `01-01-SUMMARY.md`, que ja
os traduziu medindo com `segmentar_glifos_no_brilho` nas quatro fixturas.

O CASO QUE ESTE ARQUIVO EXISTE PARA PRENDER
===========================================
`test_a_faixa_e_MEDIDA_DEPOIS_do_descarte...` e o M-K virado teste. O M-I mediu
a altura da fonte da barra sobre um recorte que continha os icones de moeda,
porque `segmentar_glifos` devolve UMA faixa para o retangulo inteiro, e o icone
empurrou o topo e a base. Sem este caso a correcao do M-K seria uma frase no
plano em vez de um comportamento no codigo — e uma guarda de altura escrita
contra a altura contaminada recusaria todo molde legitimo desta barra,
produzindo um cortador que roda, sai com codigo 0 e nunca corta nada.

E OS NUMEROS DO PROPRIO M-K CAIRAM UM PIXEL, MEDIDO AQUI. Ele publicou faixa
bruta 17 e fonte 10; nesta convencao — a de `faixa[1] - faixa[0]`, que e a mesma
em que a guarda do cortador compara — as quatro fixturas de campo dao, nos tres
pisos da banda de glifo, **16 e 9**, invariavel nas doze medicoes. E o mesmo
pixel de convencao que o M-P ja tinha achado nas LARGURAS, agora na ALTURA. Os
casos sinteticos continuam com 17 e 10 porque o que eles afirmam e o
COMPORTAMENTO (a faixa encolhe do icone para a fonte); quem afirma o VALOR e o
bloco de campo no fim do arquivo.
"""

from __future__ import annotations

import ast
import pathlib

import cv2
import numpy as np
import pytest

from l2scanner.mercado_leitura import (
    limite_de_glifo_unico,
    mascara_de_numero,
    segmentar_glifos_no_brilho,
)
from l2scanner.renda_leitura import (
    MOTIVO_DA_FORMA,
    MOTIVO_DO_RUN_ANORMAL,
    GlifosDoNumero,
    RecusaDeForma,
    _glifos_do_numero,
)

# O piso de brilho destas imagens sinteticas. Elas sao 0 ou 255, entao qualquer
# piso no meio separa tinta de fundo — este numero NAO e geometria de campo, e
# por isso ele mora aqui e nao no fonte.
PISO_SINTETICO = 128

# A geometria vertical dos blocos sinteticos, na convencao de `faixa` (base
# EXCLUSIVA, como `segmentar_glifos_no_brilho` devolve).
ALTURA_DA_IMAGEM = 30
TOPO_DO_DIGITO, BASE_DO_DIGITO = 12, 22  # altura 10  -> a fonte da barra (M-K)
TOPO_DA_VIRGULA = 20  # altura 2, e ela e BAIXA: e a posicao que a distingue
TOPO_DO_ICONE = 5  # altura 17 -> o que contaminou a faixa unica do M-I

# O limite de glifo unico dos moldes desta fonte, na convencao exclusiva:
# digito 4, 5 ou 6 (M-P / 01-01-SUMMARY). O maior e 6.
LIMITE_DA_BARRA = 6


def imagem_de_blocos(blocos: list[tuple[int, int, int]]) -> np.ndarray:
    """Uma imagem BGR com um bloco de tinta por `(largura, topo, base)`.

    Os blocos sao separados por UMA coluna vazia, que e a menor lacuna real
    medida entre dois glifos vizinhos e a que `segmentar_glifos_no_brilho`
    exige para separar. Ha uma coluna vazia sobrando em cada ponta para que
    nenhum run encoste na borda da imagem por acidente.
    """
    largura = sum(b[0] for b in blocos) + (len(blocos) - 1) + 2
    imagem = np.zeros((ALTURA_DA_IMAGEM, largura, 3), dtype=np.uint8)
    x = 1
    for largura_do_bloco, topo, base in blocos:
        imagem[topo:base, x : x + largura_do_bloco] = 255
        x += largura_do_bloco + 1
    return imagem


def icone(largura: int) -> tuple[int, int, int]:
    return (largura, TOPO_DO_ICONE, BASE_DO_DIGITO)


def digito(largura: int) -> tuple[int, int, int]:
    return (largura, TOPO_DO_DIGITO, BASE_DO_DIGITO)


def virgula() -> tuple[int, int, int]:
    return (1, TOPO_DA_VIRGULA, BASE_DO_DIGITO)


def segmentar(blocos: list[tuple[int, int, int]]):
    """`(mascara, faixa, runs)` pelo MESMO caminho que a producao usa.

    A imagem passa por `mascara_de_numero` e `segmentar_glifos_no_brilho` em vez
    de a faixa e os runs serem escritos a mao. Isso amarra o teste a convencao
    de PRODUCAO: se a convencao de faixa ou de run mudar la, este arquivo
    percebe, em vez de continuar verde contra numeros congelados.
    """
    imagem = imagem_de_blocos(blocos)
    mascara = mascara_de_numero(imagem, PISO_SINTETICO)
    faixa, runs = segmentar_glifos_no_brilho(imagem, PISO_SINTETICO)
    return mascara, faixa, runs


# ---------------------------------------------------------------------------
# Os vetores de campo, na convencao exclusiva (01-01-SUMMARY, medidos com
# `segmentar_glifos_no_brilho` sobre as quatro fixturas)
# ---------------------------------------------------------------------------
#
#   00h45 faerlina   [14, 4, 4, 1, 4, 4, 4, 1, 4, 4, 6, 15]  -> 10  `13,160,684`
#   00h45 yazalaque  [14, 4, 1, 4, 4, 4, 1, 4, 4, 4, 15]     ->  9  `1,696,020`
#   09h30 faerlina   [14, 4, 4, 1, 4, 4, 6, 1, 5, 4, 4, 15]  -> 10  `15,134,779`


def barra_da_yazalaque_00h45() -> list[tuple[int, int, int]]:
    """`1,696,020` — nove caracteres entre dois icones."""
    return [
        icone(14),
        digito(4),
        virgula(),
        digito(4),
        digito(4),
        digito(4),
        virgula(),
        digito(4),
        digito(4),
        digito(4),
        icone(15),
    ]


def barra_da_faerlina_09h30() -> list[tuple[int, int, int]]:
    """`15,134,779` — o vetor com digitos de 4, 5 E 6, que uma peneira de
    largura unica recusaria inteiro."""
    return [
        icone(14),
        digito(4),
        digito(4),
        virgula(),
        digito(4),
        digito(4),
        digito(6),
        virgula(),
        digito(5),
        digito(4),
        digito(4),
        icone(15),
    ]


# ---------------------------------------------------------------------------
# REGRA 1 -- um run largo em cada PONTA e icone, e sai
# ---------------------------------------------------------------------------


def test_as_duas_pontas_saem_e_o_meio_fica_INTEIRO():
    mascara, faixa, runs = segmentar(barra_da_yazalaque_00h45())
    assert [b - a for a, b in runs] == [14, 4, 1, 4, 4, 4, 1, 4, 4, 4, 15]

    peneirado = _glifos_do_numero(mascara, faixa, runs, limite=LIMITE_DA_BARRA)

    assert isinstance(peneirado, GlifosDoNumero)
    # NOVE do meio: `1,696,020` tem nove caracteres, e a contagem bate com a
    # verdade de campo caractere por caractere (M-J / M-O).
    assert len(peneirado.runs) == 9
    assert [b - a for a, b in peneirado.runs] == [4, 1, 4, 4, 4, 1, 4, 4, 4]
    assert peneirado.runs[0] == runs[1]
    assert peneirado.runs[-1] == runs[-2]


def test_o_digito_NAO_TEM_UMA_LARGURA_SO_e_a_peneira_aceita_as_tres():
    """`15,134,779` tem digitos de 4, 5 e 6. Uma peneira que exigisse UMA
    largura recusaria o numero inteiro (01-01-SUMMARY, desvio 2)."""
    mascara, faixa, runs = segmentar(barra_da_faerlina_09h30())

    peneirado = _glifos_do_numero(mascara, faixa, runs, limite=LIMITE_DA_BARRA)

    assert isinstance(peneirado, GlifosDoNumero)
    assert len(peneirado.runs) == 10
    larguras = sorted({b - a for a, b in peneirado.runs})
    assert larguras == [1, 4, 5, 6]


def test_o_limite_vem_dos_MOLDES_e_nao_de_uma_constante():
    """O limite e `limite_de_glifo_unico(moldes)` — DERIVADO e nunca gravado.

    A regra esta escrita na docstring daquela funcao: gravar uma copia criaria
    duas verdades sobre uma so geometria, e a copia envelheceria contra os
    moldes que ela descreve.
    """
    moldes = {
        "0": np.zeros((10, 4), dtype=np.uint8),
        "4": np.zeros((10, 6), dtype=np.uint8),
        ",": np.zeros((10, 1), dtype=np.uint8),
    }
    assert limite_de_glifo_unico(moldes) == LIMITE_DA_BARRA

    mascara, faixa, runs = segmentar(barra_da_yazalaque_00h45())
    peneirado = _glifos_do_numero(
        mascara, faixa, runs, limite=limite_de_glifo_unico(moldes)
    )
    assert isinstance(peneirado, GlifosDoNumero)
    assert len(peneirado.runs) == 9


# ---------------------------------------------------------------------------
# REGRA 2 -- um run largo no MEIO derruba o recorte, e NAO e descartado
# ---------------------------------------------------------------------------


def test_run_largo_no_MEIO_derruba_o_recorte_em_vez_de_ser_descartado():
    """O caso do M-N: o recorte `1500,1360 200x32` pega a cauda da L-Coin, o
    icone da moeda de ouro e SO ENTAO a adena — produzindo uma corrida larga no
    meio. Descarta-la apagaria um digito e devolveria um numero mais curto e
    plausivel, que e exatamente o que esta fase existe para nao produzir.
    """
    blocos = [
        icone(14),
        digito(4),
        digito(4),
        virgula(),
        digito(4),
        icone(17),  # o icone da moeda de ouro DENTRO do numero (M-N / M-Q)
        digito(4),
        digito(4),
        icone(15),
    ]
    mascara, faixa, runs = segmentar(blocos)

    peneirado = _glifos_do_numero(mascara, faixa, runs, limite=LIMITE_DA_BARRA)

    assert isinstance(peneirado, RecusaDeForma)
    assert peneirado.motivo == MOTIVO_DA_FORMA
    assert "17" in peneirado.detalhe  # a largura sai NOMEADA
    assert "meio" in peneirado.detalhe.lower()


# ---------------------------------------------------------------------------
# REGRA 3 -- exatamente um run largo em cada ponta, ou recusa de forma
# ---------------------------------------------------------------------------


def test_ZERO_run_largo_numa_ponta_e_recusa_de_forma():
    """Sem icone a esquerda, o recorte deixou de conter exatamente um numero:
    ele comeca no meio de outra coisa."""
    blocos = [
        digito(4),
        digito(4),
        virgula(),
        digito(4),
        digito(4),
        digito(4),
        icone(15),
    ]
    mascara, faixa, runs = segmentar(blocos)

    peneirado = _glifos_do_numero(mascara, faixa, runs, limite=LIMITE_DA_BARRA)

    assert isinstance(peneirado, RecusaDeForma)
    assert peneirado.motivo == MOTIVO_DA_FORMA
    assert "ponta" in peneirado.detalhe.lower()


def test_DOIS_runs_largos_numa_ponta_e_recusa_de_forma():
    """Dois icones colados numa ponta significam que o recorte pegou o campo
    vizinho junto — e o segundo icone NAO pode ser descartado como se fosse
    ponta, porque nao ha como saber onde o numero comeca."""
    blocos = [
        icone(14),
        icone(15),
        digito(4),
        virgula(),
        digito(4),
        digito(4),
        icone(15),
    ]
    mascara, faixa, runs = segmentar(blocos)

    peneirado = _glifos_do_numero(mascara, faixa, runs, limite=LIMITE_DA_BARRA)

    assert isinstance(peneirado, RecusaDeForma)
    assert peneirado.motivo == MOTIVO_DA_FORMA
    assert "ponta" in peneirado.detalhe.lower()


def test_recorte_curto_demais_para_ter_duas_pontas_e_um_meio_recusa():
    mascara, faixa, runs = segmentar([icone(14), icone(15)])

    peneirado = _glifos_do_numero(mascara, faixa, runs, limite=LIMITE_DA_BARRA)

    assert isinstance(peneirado, RecusaDeForma)
    assert peneirado.motivo == MOTIVO_DA_FORMA


def test_recorte_sem_corrida_nenhuma_recusa_e_nao_levanta():
    imagem = np.zeros((ALTURA_DA_IMAGEM, 20, 3), dtype=np.uint8)
    mascara = mascara_de_numero(imagem, PISO_SINTETICO)
    faixa, runs = segmentar_glifos_no_brilho(imagem, PISO_SINTETICO)
    assert runs == []

    peneirado = _glifos_do_numero(mascara, faixa, runs, limite=LIMITE_DA_BARRA)

    assert isinstance(peneirado, RecusaDeForma)
    assert peneirado.motivo == MOTIVO_DA_FORMA


# ---------------------------------------------------------------------------
# REGRA 4 -- a FAIXA e recomputada DEPOIS do descarte. O M-K virado teste.
# ---------------------------------------------------------------------------


def test_a_faixa_e_MEDIDA_DEPOIS_do_descarte_e_encolhe_do_ICONE_para_a_FONTE():
    """M-K, e este e o caso que prova que a correcao entrou no CODIGO.

    Os numeros deste caso sao SINTETICOS: os blocos foram desenhados com icone
    de 17 linhas e digito de 10, que sao os numeros que o M-K publicou. O que o
    caso afirma nao e o valor — e o COMPORTAMENTO: a faixa que sai e a do miolo,
    e nao a do retangulo inteiro. Os valores reais desta fonte, medidos sobre as
    fixturas de campo, estao no ultimo teste deste arquivo, e sao 16 e 9.

    O M-I mediu `faixa=(9, 25)` — altura **17** — sobre um recorte da adena que
    incluia os icones de moeda das duas pontas. `segmentar_glifos` devolve UMA
    faixa para o retangulo inteiro (decisao de projeto, documentada), entao o
    icone, mais alto, empurrou o topo e a base. Medido de novo sobre a L-Coin
    SEM icone: `faixa = (17, 26)`, altura **10**, nas duas instancias.

    Medir a altura ANTES do descarte e reproduzir o defeito do M-I por dentro
    da ferramenta que existe para nao reproduzi-lo.
    """
    mascara, faixa_bruta, runs = segmentar(barra_da_yazalaque_00h45())

    # A faixa BRUTA carrega os icones, e ela tem altura 17 — exatamente o
    # numero que circulou por uma revisao inteira como se fosse a fonte.
    assert faixa_bruta[1] - faixa_bruta[0] == 17

    peneirado = _glifos_do_numero(mascara, faixa_bruta, runs, limite=LIMITE_DA_BARRA)

    assert isinstance(peneirado, GlifosDoNumero)
    # E a faixa PENEIRADA e a da fonte: 10. Nao 17.
    assert peneirado.faixa[1] - peneirado.faixa[0] == 10
    assert peneirado.faixa == (TOPO_DO_DIGITO, BASE_DO_DIGITO)


def test_a_faixa_peneirada_de_um_recorte_SEM_icone_tambem_da_10():
    """O controle do caso acima: sobre a L-Coin sem icone nenhum, a faixa bruta
    ja e 10 — e a peneira nao a estraga. Se so o caso contaminado existisse,
    uma peneira que devolvesse `(0, 10)` fixo passaria."""
    blocos = [
        icone(14),
        digito(4),
        digito(4),
        virgula(),
        digito(4),
        digito(4),
        digito(4),
        icone(15),
    ]
    mascara, faixa_bruta, runs = segmentar(blocos)
    peneirado = _glifos_do_numero(mascara, faixa_bruta, runs, limite=LIMITE_DA_BARRA)

    assert isinstance(peneirado, GlifosDoNumero)
    assert peneirado.faixa[1] - peneirado.faixa[0] == 10


# ---------------------------------------------------------------------------
# A GUARDA DO RUN ANORMALMENTE LARGO -- os 141 px do M-L
# ---------------------------------------------------------------------------


def test_o_run_de_141_px_e_RECUSADO_com_a_largura_nomeada_e_NUNCA_fatiado():
    """M-L: a regiao do EXP da Yazalaque, em piso alto e recorte largo, cola
    tudo num run unico de 141 px porque a BARRA VERDE de progresso entra na
    mascara.

    141 px fatiados em glifos de 5 dariam VINTE E OITO digitos que nunca
    estiveram na tela. A peneira recusa; ela nao fatia.
    """
    mascara, faixa, runs = segmentar([(141, TOPO_DO_DIGITO, BASE_DO_DIGITO)])
    assert [b - a for a, b in runs] == [141]

    peneirado = _glifos_do_numero(mascara, faixa, runs, limite=LIMITE_DA_BARRA)

    assert isinstance(peneirado, RecusaDeForma)
    assert peneirado.motivo == MOTIVO_DO_RUN_ANORMAL
    assert "141" in peneirado.detalhe
    # NENHUM glifo saiu dele: a recusa nao tem `runs`, e o tipo do resultado e
    # o que garante isso — nao ha atalho que devolva "os glifos que deu".
    assert not hasattr(peneirado, "runs")


def test_o_icone_de_ponta_NAO_e_confundido_com_run_anormal():
    """O controle da guarda acima, e ele e obrigatorio: uma guarda de anomalia
    apertada demais transformaria todo icone de ponta em recusa, e o cortador
    nunca cortaria nada — o mesmo modo de falha da guarda de altura contra 17.
    """
    mascara, faixa, runs = segmentar(barra_da_faerlina_09h30())
    peneirado = _glifos_do_numero(mascara, faixa, runs, limite=LIMITE_DA_BARRA)
    assert isinstance(peneirado, GlifosDoNumero)


def test_a_recusa_do_run_anormal_diz_a_CAUSA_e_o_conserto():
    """Uma recusa que nao diz o conserto vira "a ferramenta nao funciona"."""
    mascara, faixa, runs = segmentar([(141, TOPO_DO_DIGITO, BASE_DO_DIGITO)])
    peneirado = _glifos_do_numero(mascara, faixa, runs, limite=LIMITE_DA_BARRA)
    detalhe = peneirado.detalhe.lower()
    assert "M-L" in peneirado.detalhe
    assert "recorte" in detalhe or "piso" in detalhe


# ---------------------------------------------------------------------------
# O LIMITE E SOMENTE-NOMEADO E SEM DEFAULT
# ---------------------------------------------------------------------------


def test_omitir_o_limite_levanta_TypeError():
    """Um default seria uma geometria entrando por omissao — e a geometria
    desta fonte vem dos moldes, que sao cortados por um humano."""
    mascara, faixa, runs = segmentar(barra_da_yazalaque_00h45())
    with pytest.raises(TypeError):
        _glifos_do_numero(mascara, faixa, runs)


def test_o_limite_NAO_pode_ser_passado_posicionalmente():
    mascara, faixa, runs = segmentar(barra_da_yazalaque_00h45())
    with pytest.raises(TypeError):
        _glifos_do_numero(mascara, faixa, runs, LIMITE_DA_BARRA)


def test_limite_ausente_recusa_em_vez_de_adivinhar():
    """`limite_de_glifo_unico({})` devolve `None` — conjunto vazio, primeira
    rodada. A peneira RECUSA com o motivo nomeado em vez de inventar um limite.
    """
    assert limite_de_glifo_unico({}) is None
    mascara, faixa, runs = segmentar(barra_da_yazalaque_00h45())

    peneirado = _glifos_do_numero(mascara, faixa, runs, limite=None)

    assert isinstance(peneirado, RecusaDeForma)
    assert peneirado.motivo == MOTIVO_DA_FORMA
    assert "limite" in peneirado.detalhe.lower()


# ---------------------------------------------------------------------------
# A SETA APONTA FERRAMENTA -> PURO, E ELA E AFIRMADA POR CODIGO
# ---------------------------------------------------------------------------


def test_o_modulo_puro_nao_importa_nenhum_calibrador():
    """Se `renda_leitura` importasse um `calibrar_*`, um modulo de producao
    pagaria `tornar_consciente_de_dpi()` e as janelas do OpenCV so por existir.
    """
    import l2scanner.renda_leitura as modulo

    arvore = ast.parse(pathlib.Path(modulo.__file__).read_text(encoding="utf-8"))
    importados: list[str] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados += [a.name for a in no.names]
        elif isinstance(no, ast.ImportFrom):
            importados.append(no.module or "")
    assert not [nome for nome in importados if "calibrar" in nome]


def test_existe_UMA_peneira_de_forma_nesta_fase():
    """Duas peneiras fariam os moldes serem cortados de um conjunto de corridas
    e lidos de outro, e o desalinhamento apareceria como pontuacao baixa que
    alguem consertaria baixando o piso de leitura — trocando um defeito visivel
    por um invisivel."""
    import l2scanner.renda_leitura as modulo

    arvore = ast.parse(pathlib.Path(modulo.__file__).read_text(encoding="utf-8"))
    definicoes = [
        no.name
        for no in ast.walk(arvore)
        if isinstance(no, ast.FunctionDef) and no.name == "_glifos_do_numero"
    ]
    assert definicoes == ["_glifos_do_numero"]


# ---------------------------------------------------------------------------
# A GEOMETRIA REAL DESTA FONTE, sobre as fixturas VERSIONADAS
# ---------------------------------------------------------------------------
#
# ESTE E O UNICO CASO DESTE ARQUIVO QUE TOCA O DISCO, E A EXCECAO E DELIBERADA.
# Todo o resto e sintetico porque so o sintetico consegue isolar UMA regra por
# vez. Mas os numeros da fonte — os que a guarda de altura do cortador vai
# comparar em campo — nao podem sair de um bloco que eu mesmo desenhei: isso
# seria afirmar a minha propria suposicao. Eles saem de PIXEL DE JOGO.
#
# As quatro imagens sao as fixturas VERSIONADAS de `tests/fixtures/renda/`,
# resgatadas pelo `01-01` e presentes em qualquer clone. NAO e `recordings/`,
# que e gitignored e ficaria verde nesta maquina e amarelo em toda outra
# (`tests/test_mercado_glifos.py:4-8` e o precedente literal: fixtura
# versionada, sim; gravacao, nunca).
#
# E ELE EXISTE PORQUE UM NUMERO CAIU AQUI. O M-K publicou faixa bruta 17 e fonte
# 10; medido nesta convencao — a mesma em que `faixa[1] - faixa[0]` e a mesma em
# que a guarda compara — sao 16 e 9. E o mesmo pixel de diferenca que o M-P ja
# tinha achado nas LARGURAS, agora na ALTURA. Sem este teste, a correcao seria
# prosa numa docstring, que e exatamente como o 17 sobreviveu a uma revisao
# inteira.


FIXTURAS_DA_ADENA = sorted(
    pathlib.Path("tests/fixtures/renda").glob("*__barra_direita.png")
)
PISOS_DA_BANDA_DE_GLIFO = (180, 185, 190)


def test_ha_fixturas_de_campo_versionadas_para_medir():
    """O controle do caso abaixo: um `glob` vazio faria o laco nao rodar nenhuma
    asserção e o teste passar sem medir nada — o resultado mais tranquilizador
    possivel para a medicao que nao aconteceu."""
    assert len(FIXTURAS_DA_ADENA) >= 4


def test_a_geometria_MEDIDA_desta_fonte_e_faixa_bruta_16_e_peneirada_9():
    medidas = set()
    for arquivo in FIXTURAS_DA_ADENA:
        pixels = cv2.imread(str(arquivo))
        assert pixels is not None, arquivo
        for piso in PISOS_DA_BANDA_DE_GLIFO:
            mascara = mascara_de_numero(pixels, piso)
            faixa_bruta, runs = segmentar_glifos_no_brilho(pixels, piso)
            # O limite de arranque da primeira rodada: a maior largura que NAO
            # esta numa ponta. Ele nao e uma constante — sai das proprias
            # corridas daquele recorte.
            limite = max(b - a for a, b in runs[1:-1])
            peneirado = _glifos_do_numero(mascara, faixa_bruta, runs, limite=limite)
            assert isinstance(peneirado, GlifosDoNumero), (arquivo.name, piso)
            medidas.add(
                (
                    faixa_bruta[1] - faixa_bruta[0],
                    peneirado.faixa[1] - peneirado.faixa[0],
                )
            )

    # INVARIAVEL nas doze medicoes: a faixa bruta carrega o icone, a peneirada
    # carrega a fonte. Os numeros 17 e 10 do M-K sao os MESMOS pixels contados
    # de forma inclusiva (M-P, agora tambem para a altura).
    assert medidas == {(16, 9)}


def test_a_contagem_do_meio_bate_com_a_VERDADE_DE_CAMPO_caractere_a_caractere():
    """A prova de que a peneira nao esta apenas devolvendo alguma coisa.

    A verdade de campo esta no M-O, e ela foi lida na tela por um humano:

        campo_faerlina_f000        13.160.684   -> 10 caracteres
        campo_yazalaque_f001        1.696.020   ->  9
        segundo_cenario_faerlina   15.134.779   -> 10
    """
    verdade = {
        "campo_faerlina_f000__barra_direita.png": 10,
        "campo_yazalaque_f001__barra_direita.png": 9,
        "segundo_cenario_faerlina__barra_direita.png": 10,
        "segundo_cenario_yazalaque__barra_direita.png": 9,
    }
    for arquivo in FIXTURAS_DA_ADENA:
        esperado = verdade.get(arquivo.name)
        if esperado is None:
            continue
        pixels = cv2.imread(str(arquivo))
        for piso in PISOS_DA_BANDA_DE_GLIFO:
            mascara = mascara_de_numero(pixels, piso)
            faixa, runs = segmentar_glifos_no_brilho(pixels, piso)
            limite = max(b - a for a, b in runs[1:-1])
            peneirado = _glifos_do_numero(mascara, faixa, runs, limite=limite)
            assert len(peneirado.runs) == esperado, (arquivo.name, piso)


def test_o_digito_desta_fonte_NAO_tem_uma_largura_so_EM_CAMPO():
    """O `4`, o `7` e o `9` saem mais largos. Uma peneira que exigisse UMA
    largura recusaria `15,134,779` inteiro (01-01-SUMMARY, desvio 2)."""
    larguras = set()
    for arquivo in FIXTURAS_DA_ADENA:
        pixels = cv2.imread(str(arquivo))
        for piso in PISOS_DA_BANDA_DE_GLIFO:
            mascara = mascara_de_numero(pixels, piso)
            faixa, runs = segmentar_glifos_no_brilho(pixels, piso)
            limite = max(b - a for a, b in runs[1:-1])
            peneirado = _glifos_do_numero(mascara, faixa, runs, limite=limite)
            larguras |= {b - a for a, b in peneirado.runs}

    assert larguras == {1, 4, 5, 6}, larguras
