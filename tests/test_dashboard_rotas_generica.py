"""A prova do CALC-05: um TERCEIRO item atravessa a pilha SEM CODIGO NOVO.

O requisito diz que a calculadora e generica — que os dois itens que o ROADMAP
nomeia sao as duas primeiras INSTANCIAS e nao casos especiais no codigo, e que
acrescentar um terceiro e **uma entrada de configuracao**, sem uma linha de
calculo nem de tela. A generalidade e a diferenca entre uma calculadora e dois
`if`, e ela nao se prova afirmando: prova-se instanciando algo que o codigo nunca
viu e mostrando que ele atravessa tudo.

OS CINCO ELOS QUE O TERCEIRO ITEM ATRAVESSA
============================================
  1. CONFIGURACAO — `ler_itens_de_rota` sobre um `config.toml` de tres blocos
     devolve os tres na ordem escrita, e o terceiro tem exatamente os campos dos
     dois primeiros;
  2. CALCULO      — `vereditos_das_rotas` devolve tres vereditos, e o conjunto
     de campos do terceiro e IDENTICO ao dos dois primeiros, seja qual for o
     estado em que cada um caia;
  3. PAYLOAD      — `payload` traz tres entradas em `calculadora.itens`, com
     chaves identicas entre si;
  4. SERVIDOR     — `GET /dados` entrega as tres, e nenhum campo se perde na
     serializacao;
  5. TELA         — por leitura de fonte: toda propriedade que a pintura LE
     existe nas TRES entradas, e o conjunto que resolve e o mesmo nas tres.

E O ELO TRANSVERSAL: nenhum nome de item aparece como LITERAL no codigo de
calculo nem no de tela. Sem ele os cinco de cima passariam sobre um `if` por
item — contar chaves iguais mostra que o terceiro ATRAVESSA, e nao que ele
atravessa sem o nome dele escrito dentro do codigo.

CADA ELO CARREGA O CONTROLE QUE PROVA QUE A SONDA DELE DISCRIMINA
==================================================================
O `01-VERIFICATION.md` registrou por escrito que o quinto elo do analogo
(`tests/test_dashboard_serie_generica.py`, DASH-05) **passaria por VACUIDADE sem
um controle negativo no extrator**: um extrator que nao encontra propriedade
nenhuma devolve conjunto vazio, e conjunto vazio esta contido em qualquer coisa.
A mesma armadilha existe aqui nos cinco elos, e a regra deste arquivo e curta —
toda assercao positiva vem acompanhada da prova de que a sonda dela ACUSA. Um
guarda que passa sobre uma implementacao vazia e pior que nenhum guarda, porque
anuncia uma garantia que nao existe.

ESTE ARQUIVO ESTENDE, E NAO REPETE
===================================
O plano 02-02 ja abriu o CALC-05 pelo lado do CALCULO, em
`tests/test_dashboard_rotas.py`: a sonda de nome de item no codigo Python, os
dois controles dela, e o terceiro item atravessando `vereditos_das_rotas` e
`_linha_da_rota`. **Aquela sonda e as constantes que dizem QUEM e o terceiro sao
IMPORTADAS daqui, e nunca reescritas** — duas copias da mesma invariante divergem
na primeira correcao, uma fica verde por engano, e a mais fraca e a que a proxima
pessoa com pressa apaga achando que remove duplicacao.

O QUE ESTE ARQUIVO ACRESCENTA, e que nao existia: o elo da CONFIGURACAO (do TOML
em disco, e nao de um `ItemDeRota` montado a mao), o do `payload` inteiro, o do
SERVIDOR, o da TELA, e a sonda de literal estendida ao `dashboard.js` e ao
`dashboard.css` — que ate aqui varria so os dois modulos Python.

OS NOMES PROCURADOS NAO ESTAO ESCRITOS NESTE ARQUIVO
=====================================================
Nem no codigo, nem nos comentarios. Eles vem das constantes de dado do 02-02 e,
na sonda, da CONFIGURACAO DE TESTE — `ler_itens_de_rota` sobre o arquivo que a
fixture escreveu. Sao duas razoes, e as duas ja custaram caro nesta arvore:

  1. uma busca futura por "onde este projeto conhece esses nomes" cairia num
     comentario de teste que existe justamente para dizer que o codigo NAO os
     conhece (a licao que o 02-02 registrou no cabecalho da secao dele);
  2. uma sonda cuja lista de procurados esta escrita a mao no proprio teste para
     de cobrir o dia em que um quarto item entrar na fixture — ela mediria a
     lista, e nao a configuracao.

AS CHAVES DE SERIE TAMBEM NAO SAO ESCRITAS A MAO: elas saem de
`mercado_catalogo.chave_da_serie`, que e a funcao de PRODUCAO que as constroi.
Escreve-las a mao seria reimplementar por fora o que a producao ja faz por
dentro, que e a primeira regra medida do `CLAUDE.md`.

O QUE ESTA PROVA **NAO** ALCANCA, dito por extenso para nao ser confundido com o
que ela alcanca
=================================================================================
Ela garante o PISO, e o piso e inteiro: a configuracao chega, a conta roda, o
payload carrega, o servidor entrega e os vaos existem para o terceiro item
exatamente como para os dois primeiros.

Ela **nao** garante o DESENHO. Que a terceira linha fique legivel na tela — que
as tres se distingam, que a coluna nao estoure, que a marca da vencedora
continue chamando atencao com tres linhas empilhadas — exige um navegador de
verdade, e esta casa recusou instalador pesado de automacao de navegador por
decisao travada no `01-CONTEXT.md`.

Essa metade e VERIFICACAO HUMANA DECLARADA, esta registrada como tal no SUMMARY
deste plano, e nao esta escondida atras de um teste verde.

ESTE ARQUIVO NAO LEVA LETRA ACENTUADA, como o resto de `tests/`.
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from l2scanner import dashboard, dashboard_dados, dashboard_rotas
from l2scanner.config import (
    CHAVE_DOS_ITENS,
    SECAO_DO_DASHBOARD,
    ItemDeRota,
    ItemDeRotaInvalido,
    ler_itens_de_rota,
)
from l2scanner.mercado_analise import ModeloDeMercado, menor_pedido_visivel
from l2scanner.mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA, chave_da_serie
from l2scanner.mercado_registro import ARQUIVO_DE_OBSERVACOES

# A SONDA DE LITERAL E AS CONSTANTES DE QUEM E O TERCEIRO SAO IMPORTADAS.
# Ver o cabecalho: uma segunda copia divergiria, e a mais fraca seria a
# sobrevivente.
from tests.test_dashboard_calculadora_pagina import (
    caminho_existe,
    molde_da_linha,
    propriedades_do_item_consumidas,
    vaos_de,
    vaos_escritos_pela_pintura,
)
from tests.test_dashboard_js import _so_o_codigo
from tests.test_dashboard_rotas import (
    NOME_DO_TERCEIRO,
    NOMES_DO_ROADMAP,
    _nomes_de_item_no_codigo,
    _so_o_codigo_python,
)
from tests.test_dashboard_rotas_tracer import (
    ARQUIVO_DO_CSS,
    ARQUIVO_DO_HTML,
    ARQUIVO_DO_JS,
    LINHAS_DA_ADENA,
    _escrever_csv,
    _get_dados,
    _linhas_de_uma_serie,
    _piso,
)
from tests.test_dashboard_servidor import _impressao_do_arquivo

RAIZ = Path(__file__).resolve().parent.parent
ESTE_ARQUIVO = Path(__file__).resolve()

ARQUIVO_DE_CONFIGURACAO = "config.toml"


# ---------------------------------------------------------------------------
# O MATERIAL: TRES ITENS, E O TERCEIRO E O QUE O CODIGO NUNCA VIU
# ---------------------------------------------------------------------------
#
# A TABELA E `(nome, preco_npc_adena, quantidade_do_pacote, menor_no_mercado)`.
# Os tres primeiros campos viram bloco no `config.toml` de teste; o quarto vira
# a serie do CSV, e nao entra na configuracao — e justamente a metade que o
# programa OBSERVA, contra a metade que o usuario INFORMA.
#
# OS PRECOS FORAM ESCOLHIDOS PARA OS TRES CAIREM EM ESTADO DECIDIDO E COM
# VENCEDORAS DIFERENTES ENTRE SI. Com os tres caindo no mesmo estado, a
# igualdade de conjuntos de campos seria uma afirmacao mais fraca: ela passaria
# tambem numa implementacao que so soubesse montar UM estado.
#
# A CONTA, EM CENTESIMOS DE XM POR UNIDADE, com a taxa da Adena da fixture
# (`Fraction(9, 10000)` centesimos de XM por adena, medida em 2026-09-03):
#
#   1o item: NPC 15000 x 9/10000 = 13,5 contra 5900 do mercado -> o NPC ganha;
#   2o item: NPC 1000000 x 9/10000 = 900 contra 500 do mercado -> o MERCADO
#            ganha (a distancia e de 44%);
#   3o item: NPC 15000 x 9/10000 = 13,5 contra 3100 do mercado -> o NPC ganha.
#
# **O SEGUNDO PRECO E ALTO DE PROPOSITO, E A PRIMEIRA VERSAO DESTA TABELA ESTAVA
# ERRADA.** Ela pedia `preco=20000, pacote=2` contra um mercado a 500, na conta
# de cabeca de que 9 < 500 faria o mercado ganhar — trocando os dois lados. O
# unitario do mercado ja E centesimo de XM (500 = 5,00 XM), enquanto o do NPC sai
# de adena e passa pela taxa (20000 adena = 9 centesimos = 0,09 XM): o NPC era
# cinquenta e cinco vezes MAIS BARATO, e as tres vencedoras sairam `npc`. Quem
# acusou foi `test_as_VENCEDORAS_dos_tres_NAO_sao_todas_a_mesma`, que existe
# exatamente para isso — sem ele a fixture teria degenerado em silencio e a
# igualdade de campos passaria sobre tres vereditos identicos.
#
# As tres distancias estao MUITO acima de `MARGEM_DE_EMPATE_PERCENTUAL` (3%),
# entao nenhuma delas depende de arredondamento para nao virar empate.
_ITENS_DA_PROVA = (
    (NOMES_DO_ROADMAP[0], 15000, 1, 5900),
    (NOMES_DO_ROADMAP[1], 1_000_000, 1, 500),
    (NOME_DO_TERCEIRO, 15000, 1, 3100),
)

# O TERCEIRO E O ULTIMO DA TABELA, E O INDICE SAI DA TABELA e nao de um `2`
# escrito a mao: acrescentar um quarto item aqui nao deve calar nenhuma
# assercao sobre "o ultimo".
INDICE_DO_TERCEIRO = len(_ITENS_DA_PROVA) - 1

# A ASSINATURA DAS CHAVES DE TESTE. Ela e um detalhe do CSV de fixture e nao do
# casamento: `resolver_o_nome` casa por `nome_normalizado` sobre o
# `nome_exibido`, e nunca pela chave.
_ASSINATURA_DA_FIXTURE = "0"

# O INSTANTE DAS OFERTAS E RELATIVO AO RELOGIO REAL, E ISSO E OBRIGATORIO PARA O
# ELO 4. Aquele elo compara o `payload` em memoria com o que voltou do soquete,
# campo a campo — e o servidor usa o relogio dele, que e `datetime.now()`. Com um
# instante FIXO na fixture, a recencia em memoria ("ha 30 min") e a do servidor
# ("ha 3 d") divergiriam por uma razao que nao tem nada a ver com serializacao, e
# o teste ficaria vermelho acusando o que nao mede.
#
# Tres horas atras cai no balde de HORAS de `_recencia_em_duas_formas`, que so
# muda de valor a cada hora inteira: as duas chamadas acontecem com
# milissegundos de diferenca, entao elas caem no mesmo balde.
_INSTANTE_DAS_OFERTAS = (datetime.now() - timedelta(hours=3)).replace(
    minute=30, second=0, microsecond=0
)


def _chave_de(nome: str) -> str:
    """A chave da serie, PELA FUNCAO DE PRODUCAO que a constroi.

    Nunca escrita a mao. Uma chave digitada no teste concordaria com o CSV de
    fixture e com mais nada — e no dia em que `_slug` mudasse, a fixture
    continuaria verde descrevendo um arquivo que o programa nao escreve mais.
    """
    return chave_da_serie(nome, _ASSINATURA_DA_FIXTURE)


def _texto_do_config_de_teste(itens=_ITENS_DA_PROVA) -> str:
    """Os blocos `[[dashboard.item]]`, montados a partir da TABELA.

    Os nomes das SECOES saem de `config.SECAO_DO_DASHBOARD` e
    `config.CHAVE_DOS_ITENS`: escreve-los a mao criaria uma segunda autoridade
    sobre como a secao se chama, e o dia em que ela fosse renomeada este arquivo
    ficaria verde sobre um TOML que o leitor de producao ignora.
    """
    blocos = []
    for nome, preco, pacote, _menor in itens:
        blocos.append(
            f"[[{SECAO_DO_DASHBOARD}.{CHAVE_DOS_ITENS}]]\n"
            f'nome = "{nome}"\n'
            f"preco_npc_adena = {preco}\n"
            f"quantidade_do_pacote = {pacote}\n"
        )
    return "\n".join(blocos)


def _escrever_config(pasta: Path, texto: str) -> Path:
    alvo = pasta / ARQUIVO_DE_CONFIGURACAO
    alvo.write_text(texto, encoding="utf-8")
    return alvo


def _linhas_das_tres_series() -> list:
    """A serie de mercado de cada um dos tres, com o piso em ofertas distintas.

    O piso sai de `_piso()`, que le `N_MINIMO_PARA_O_VEREDITO`. Um numero a mao
    aqui faria as tres series cairem em `ROTA_SEM_EVIDENCIA` no dia em que o
    piso subisse — e o teste acusaria a fixture achando que acusa a producao.
    """
    linhas = []
    for indice, (nome, _preco, _pacote, menor) in enumerate(_ITENS_DA_PROVA):
        linhas.extend(
            _linhas_de_uma_serie(
                _chave_de(nome),
                nome,
                menor,
                1,
                _INSTANTE_DAS_OFERTAS - timedelta(minutes=indice),
            )
        )
    return linhas


@pytest.fixture(scope="module")
def pasta_do_mercado(tmp_path_factory) -> Path:
    """A Adena e as TRES series, em pasta temporaria.

    NADA AQUI TOCA A `.mercado/` REAL nem o `config.toml` real — e ha um gate no
    fim deste arquivo medindo exatamente isso.
    """
    pasta = tmp_path_factory.mktemp("mercado-generica") / ".mercado"
    pasta.mkdir()
    _escrever_csv(pasta, LINHAS_DA_ADENA, _linhas_das_tres_series())
    return pasta


@pytest.fixture(scope="module")
def config_de_teste(tmp_path_factory) -> Path:
    return _escrever_config(
        tmp_path_factory.mktemp("config-generica"), _texto_do_config_de_teste()
    )


@pytest.fixture(scope="module")
def itens(config_de_teste: Path) -> list:
    """A SAIDA DO ELO 1 E A ENTRADA DO ELO 2, e e por isso que ela e fixture.

    Montar `ItemDeRota` a mao aqui cortaria o primeiro elo fora da cadeia — e a
    afirmacao do CALC-05 e sobre a CONFIGURACAO chegar ate a tela, e nao sobre um
    objeto construido dentro do teste chegar.
    """
    return ler_itens_de_rota(caminho=config_de_teste)


def _modelo_e_taxa(pasta: Path):
    """O modelo e a taxa da Adena, PELA MESMA CADEIA QUE O `payload` PERCORRE.

    `observacoes_ao_vivo` -> `ModeloDeMercado.de_observacoes` ->
    `menor_pedido_visivel` sobre a serie sentinela. Nenhum passo reimplementado:
    montar o modelo a mao aqui mediria a copia, e a primeira regra medida do
    `CLAUDE.md` existe porque isso ja saiu errado tres vezes num dia so.
    """
    leitura = dashboard_dados.observacoes_ao_vivo(pasta / ARQUIVO_DE_OBSERVACOES)
    modelo = ModeloDeMercado.de_observacoes(leitura.observacoes)
    menor = menor_pedido_visivel(modelo.observacoes_de(CHAVE_DA_SERIE_DA_ADENA))
    return modelo, menor.unitario


@pytest.fixture(scope="module")
def vereditos(itens, pasta_do_mercado: Path):
    modelo, taxa = _modelo_e_taxa(pasta_do_mercado)
    return dashboard_rotas.vereditos_das_rotas(itens, modelo, taxa, datetime.now())


@pytest.fixture(scope="module")
def bloco(itens, pasta_do_mercado: Path) -> dict:
    agora = datetime.now()
    dados = dashboard_dados.payload(
        pasta_do_mercado,
        agora,
        cambio=None,
        itens=itens,
        itens_lidos_em=agora,
    )
    return dados["calculadora"]


def _campos_do_veredito(veredito) -> set:
    """O conjunto de campos de um veredito. O EXTRATOR do elo 2.

    Conjunto VAZIO significa "objeto sem campo nenhum", e nao cegueira — quem
    prova isso e o controle da classe do elo 2.
    """
    import dataclasses

    return {campo.name for campo in dataclasses.fields(veredito)}


def _chaves_profundas(entrada, prefixo: str = "") -> set:
    """Todo caminho de chave da entrada, inclusive os aninhados. O EXTRATOR do
    elo 3.

    O caminho aninhado importa: `diferenca` existir nas tres entradas nao diz
    nada se numa delas ela vier sem `reais`. Um conjunto so de chaves de topo
    deixaria passar exatamente o campo que some.

    SOBRE UM DICIONARIO VAZIO ELE DEVOLVE CONJUNTO VAZIO, e e por isso que quem
    usa este extrator afirma NAO-VAZIO antes de comparar — sem essa metade,
    `vazio == vazio` seria a prova de generalidade mais forte que este arquivo
    teria.
    """
    if not isinstance(entrada, dict):
        return set()
    achados = set()
    for chave, valor in entrada.items():
        caminho = prefixo + chave
        achados.add(caminho)
        achados |= _chaves_profundas(valor, caminho + ".")
    return achados


# ===========================================================================
# ELO 1 — A CONFIGURACAO ACEITA O TERCEIRO
# ===========================================================================


class TestElo1AConfiguracaoAceitaOTerceiro:
    """Do TOML em disco, e nao de um objeto montado a mao.

    O CALC-05 afirma que acrescentar um item e **uma entrada de configuracao**.
    Uma prova que comecasse em `ItemDeRota(...)` estaria assumindo o elo que
    precisa demonstrar.
    """

    def test_os_TRES_blocos_viram_TRES_itens_na_ordem_ESCRITA(self, itens):
        assert len(itens) == len(_ITENS_DA_PROVA)
        assert [item.nome for item in itens] == [
            nome for nome, _p, _q, _m in _ITENS_DA_PROVA
        ]

    def test_o_TERCEIRO_tem_os_MESMOS_campos_dos_dois_primeiros(self, itens):
        """Igualdade de CONJUNTO, e nao inclusao num sentido so.

        A inclusao deixaria passar um campo que existisse apenas no terceiro —
        o mesmo defeito espelhado, e ele obrigaria a tela a testar por ausencia.
        """
        campos = [_campos_do_veredito(item) for item in itens]
        assert campos[0], "o extrator nao achou campo nenhum no primeiro item"
        for outro in campos[1:]:
            assert outro == campos[0]

    def test_nenhum_campo_do_TERCEIRO_veio_VAZIO(self, itens):
        """A igualdade de conjuntos acima seria satisfeita por tres itens com
        todos os campos nulos."""
        terceiro = itens[INDICE_DO_TERCEIRO]
        assert terceiro.nome
        assert terceiro.preco_npc_adena > 0
        assert terceiro.quantidade_do_pacote > 0

    def test_CONTROLE_um_TERCEIRO_bloco_TORTO_derruba_e_a_mensagem_o_NOMEIA(
        self, tmp_path: Path
    ):
        """O controle do elo 1, e ele mede uma coisa precisa: que a validacao
        ALCANCA a terceira posicao.

        Um leitor que validasse so os dois primeiros passaria em todo teste de
        bloco torto ja escrito nesta arvore — todos usam um ou dois blocos — e
        entregaria o terceiro item sem preco para a conta, que e onde ele viraria
        um `None` no meio de uma multiplicacao.
        """
        torto = _texto_do_config_de_teste(_ITENS_DA_PROVA[:INDICE_DO_TERCEIRO])
        nome_do_terceiro = _ITENS_DA_PROVA[INDICE_DO_TERCEIRO][0]
        torto += (
            f"\n[[{SECAO_DO_DASHBOARD}.{CHAVE_DOS_ITENS}]]\n"
            f'nome = "{nome_do_terceiro}"\n'
            "quantidade_do_pacote = 1\n"
        )
        alvo = _escrever_config(tmp_path, torto)

        with pytest.raises(ItemDeRotaInvalido) as erro:
            ler_itens_de_rota(caminho=alvo)

        mensagem = str(erro.value)
        assert nome_do_terceiro in mensagem, mensagem
        assert "preco_npc_adena" in mensagem, mensagem

    def test_CONTROLE_a_guarda_de_REPETIDO_tambem_alcanca_a_terceira_posicao(
        self, tmp_path: Path
    ):
        """A outra metade do controle acima, sobre uma guarda DIFERENTE.

        A validacao de campo e por bloco; a de nome repetido e sobre a lista
        inteira. As duas podem parar de alcancar o terceiro por razoes
        diferentes, entao as duas sao medidas.
        """
        primeiro = _ITENS_DA_PROVA[0]
        repetido = (*_ITENS_DA_PROVA[:INDICE_DO_TERCEIRO], primeiro)
        alvo = _escrever_config(tmp_path, _texto_do_config_de_teste(repetido))

        with pytest.raises(ItemDeRotaInvalido) as erro:
            ler_itens_de_rota(caminho=alvo)
        assert primeiro[0] in str(erro.value)


# ===========================================================================
# ELO 2 — O CALCULO TRATA OS TRES IGUAL
# ===========================================================================


class TestElo2OCalculoTrataOsTRESIgual:
    def test_vereditos_das_rotas_devolve_TRES(self, vereditos):
        assert len(vereditos) == len(_ITENS_DA_PROVA)

    def test_o_conjunto_de_campos_do_TERCEIRO_e_IDENTICO_ao_dos_dois_primeiros(
        self, vereditos
    ):
        """ESTA E A FORMA CORRETA DE PROVAR GENERALIDADE NO CALCULO.

        Se existisse UM campo so dos dois primeiros — um `taxa_do_gemstone`, um
        `desconto_do_item_conhecido` —, entao instanciar o terceiro exigiria
        codigo novo do lado do desenho para lidar com a ausencia dele. E o
        requisito proibe exatamente isso.

        A ASSERCAO DE NAO-VAZIO VEM ANTES DA COMPARACAO. Sem ela, um extrator
        quebrado devolveria tres conjuntos vazios e `vazio == vazio` seria a
        prova.
        """
        campos = [_campos_do_veredito(veredito) for veredito in vereditos]
        assert campos[0], "o extrator nao achou campo nenhum no primeiro veredito"
        for indice, outro in enumerate(campos[1:], start=1):
            assert outro == campos[0], (
                f"o veredito #{indice + 1} diverge em campo: so nele "
                f"{sorted(outro - campos[0])}, so no primeiro "
                f"{sorted(campos[0] - outro)}"
            )

    def test_CONTROLE_a_comparacao_ACUSA_um_veredito_com_um_campo_A_MENOS(
        self, vereditos
    ):
        """O controle do elo 2, sobre a COMPARACAO e nao sobre o dado.

        Sem ele, comparar dois conjuntos vazios passaria — e essa e literalmente
        a forma que o `01-VERIFICATION.md` registrou como imprescindivel.
        """
        completo = _campos_do_veredito(vereditos[0])
        assert completo
        mutilado = set(completo)
        mutilado.discard(sorted(mutilado)[0])
        assert mutilado != completo

    def test_os_TRES_caem_em_estados_do_VOCABULARIO_do_python(self, vereditos):
        for veredito in vereditos:
            assert veredito.estado in dashboard_rotas.ESTADOS_DA_ROTA

    def test_as_VENCEDORAS_dos_tres_NAO_sao_todas_a_mesma(self, vereditos):
        """A guarda anti-vacuidade do elo 2.

        Tres vereditos identicos em tudo satisfariam a igualdade de campos com
        folga — inclusive numa implementacao que so soubesse montar um estado.
        A fixture foi construida para as vencedoras DIFERIREM, e esta assercao e
        o que avisa no dia em que ela deixar de ser assim.
        """
        vencedoras = {veredito.vencedora for veredito in vereditos}
        assert len(vencedoras) > 1, vencedoras
        assert None not in vencedoras, "algum item nao decidiu; a fixture mudou"

    def test_RENOMEAR_o_terceiro_item_NAO_muda_o_veredito_dele(
        self, itens, pasta_do_mercado: Path
    ):
        """A prova de que o codigo nao ramifica pelo NOME, medida e nao afirmada.

        A sonda de literal (mais abaixo) mostra que nenhum nome esta ESCRITO no
        codigo. Esta aqui mostra o MECANISMO pelo outro lado: trocado o nome do
        terceiro item por um texto qualquer — na configuracao E na serie, que e o
        que uma renomeacao de verdade faria —, o veredito sai identico campo a
        campo, com a excecao dos dois campos que CARREGAM o nome.

        Um `if` por nome sobreviveria a sonda de literal se o nome fosse montado
        por concatenacao; ele nao sobrevive a esta.
        """
        outro_nome = "Item Renomeado Para Esta Prova"
        renomeados = (
            *_ITENS_DA_PROVA[:INDICE_DO_TERCEIRO],
            (outro_nome, *_ITENS_DA_PROVA[INDICE_DO_TERCEIRO][1:]),
        )

        pasta = pasta_do_mercado.parent / ".mercado-renomeado"
        pasta.mkdir(exist_ok=True)
        linhas = []
        for indice, (nome, _p, _q, menor) in enumerate(renomeados):
            linhas.extend(
                _linhas_de_uma_serie(
                    _chave_de(nome),
                    nome,
                    menor,
                    1,
                    _INSTANTE_DAS_OFERTAS - timedelta(minutes=indice),
                )
            )
        _escrever_csv(pasta, LINHAS_DA_ADENA, linhas)

        agora = datetime.now()
        modelo, taxa = _modelo_e_taxa(pasta)
        novos = dashboard_rotas.vereditos_das_rotas(
            [
                ItemDeRota(
                    nome=nome, preco_npc_adena=preco, quantidade_do_pacote=pacote
                )
                for nome, preco, pacote, _m in renomeados
            ],
            modelo,
            taxa,
            agora,
        )

        modelo_original, taxa_original = _modelo_e_taxa(pasta_do_mercado)
        antigos = dashboard_rotas.vereditos_das_rotas(
            itens, modelo_original, taxa_original, agora
        )

        antigo = antigos[INDICE_DO_TERCEIRO]
        novo = novos[INDICE_DO_TERCEIRO]

        # OS CAMPOS QUE CARREGAM O NOME sao os unicos que podem diferir, e eles
        # estao nomeados aqui em vez de a comparacao ser afrouxada em silencio.
        CARREGAM_O_NOME = {"item", "nome_exibido", "chave"}
        for campo in sorted(_campos_do_veredito(antigo) - CARREGAM_O_NOME):
            assert getattr(novo, campo) == getattr(antigo, campo), campo

        # E a outra metade: os que carregam o nome REALMENTE mudaram. Sem ela, a
        # comparacao acima passaria sobre uma renomeacao que nao aconteceu.
        assert novo.item == outro_nome
        assert novo.item != antigo.item


# ===========================================================================
# ELO 3 — O PAYLOAD CARREGA OS TRES
# ===========================================================================


class TestElo3OPayloadCarregaOsTRES:
    def test_calculadora_itens_tem_TRES_entradas(self, bloco: dict):
        assert bloco["estado"] == dashboard_dados.CALCULADORA_COM_ITENS
        assert len(bloco["itens"]) == len(_ITENS_DA_PROVA)

    def test_as_chaves_de_cada_entrada_sao_IDENTICAS_entre_si(self, bloco: dict):
        """Comparacao PROFUNDA, e com a assercao de nao-vazio antes.

        Chaves de topo iguais nao bastariam: `diferenca` presente nas tres nao
        diz nada se numa delas ela vier sem `reais`.
        """
        caminhos = [_chaves_profundas(item) for item in bloco["itens"]]
        assert caminhos[0], (
            "o extrator nao achou caminho nenhum na primeira entrada; a "
            "comparacao abaixo passaria por vacuidade"
        )
        for indice, outro in enumerate(caminhos[1:], start=1):
            assert outro == caminhos[0], (
                f"a entrada #{indice + 1} diverge: so nela "
                f"{sorted(outro - caminhos[0])}, so na primeira "
                f"{sorted(caminhos[0] - outro)}"
            )

    def test_CONTROLE_o_extrator_de_chaves_sobre_um_dicionario_VAZIO_devolve_VAZIO(
        self,
    ):
        """O CONTROLE QUE O `01-VERIFICATION.md` REGISTRA COMO IMPRESCINDIVEL.

        Ele tem duas metades, e as duas sao necessarias:

        1. sobre o vazio, o extrator devolve vazio — entao um conjunto vazio
           significa AUSENCIA, e nao cegueira;
        2. sobre um dicionario com conteudo, ele ACHA — entao um extrator que
           devolvesse sempre vazio (por um erro de expressao ou de recursao)
           seria pego aqui, e nao passaria calado fazendo `vazio == vazio` valer
           como prova de generalidade.
        """
        assert _chaves_profundas({}) == set()
        assert _chaves_profundas({"a": {"b": 1}, "c": None}) == {"a", "a.b", "c"}

    def test_CONTROLE_a_comparacao_ACUSA_uma_entrada_sem_um_campo_ANINHADO(
        self, bloco: dict
    ):
        """A mutacao acontece sobre uma COPIA do dado real, e nao sobre o
        payload — assim ela mede a comparacao contra a forma que o defeito
        tomaria de verdade, que e um campo aninhado sumindo."""
        import copy

        adulterada = copy.deepcopy(bloco["itens"][INDICE_DO_TERCEIRO])
        assert isinstance(adulterada.get("diferenca"), dict)
        alvo = sorted(adulterada["diferenca"])[0]
        del adulterada["diferenca"][alvo]

        assert _chaves_profundas(adulterada) != _chaves_profundas(
            bloco["itens"][0]
        )

    def test_o_TERCEIRO_traz_NUMERO_e_nao_so_estrutura(self, bloco: dict):
        """A igualdade de caminhos seria satisfeita por tres entradas com todos
        os valores nulos."""
        terceiro = bloco["itens"][INDICE_DO_TERCEIRO]
        assert terceiro["vencedora"] is not None
        assert terceiro["npc"]["texto"]
        assert terceiro["mercado"]["texto"]
        assert terceiro["diferenca"]["xm"]
        assert terceiro["n"] >= _piso()


# ===========================================================================
# ELO 4 — O SERVIDOR ENTREGA OS TRES
# ===========================================================================


@pytest.fixture
def servidor(pasta_do_mercado: Path, itens):
    """PORTA ZERO, NUNCA A FIXA: a suite nao pode brigar com o dashboard que o
    usuario deixou aberto na `PORTA_PADRAO`."""
    montado = dashboard.montar_servidor(
        porta=0,
        pasta_do_mercado=pasta_do_mercado,
        itens=itens,
        itens_lidos_em=datetime.now(),
    )
    tarefa = threading.Thread(
        target=montado.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
    )
    tarefa.start()
    try:
        yield montado
    finally:
        montado.shutdown()
        montado.server_close()
        tarefa.join(timeout=5)
        assert not tarefa.is_alive()


class TestElo4OServidorEntregaOsTRES:
    """A travessia de verdade, com soquete e JSON serializado.

    O payload em memoria pode conter tipos que nao sobrevivem ao JSON — esta
    arvore ja teve `Fraction` e `Decimal` na fronteira. Provar a generalidade so
    em memoria deixaria de fora justamente a serializacao, que e por onde o
    navegador recebe.
    """

    def test_o_GET_dados_entrega_as_TRES_entradas(self, servidor):
        status, dados = _get_dados(servidor.server_address[1])
        assert status == 200
        assert len(dados["calculadora"]["itens"]) == len(_ITENS_DA_PROVA)

    def test_cada_entrada_volta_do_HTTP_IDENTICA_a_do_payload(
        self, servidor, pasta_do_mercado: Path, itens
    ):
        """A COMPARACAO E CONTRA O `payload`, E NAO CONTRA A PROPRIA RESPOSTA.

        Afirmar que a resposta tem status 200 e tres entradas nao mede
        serializacao nenhuma: uma serializacao que deixasse `diferenca.reais`
        para tras entregaria 200 e tres entradas do mesmo jeito. O que pega esse
        defeito e comparar, campo a campo, o dicionario que o Python montou com
        o que voltou do soquete.

        O `json.dumps`/`json.loads` do lado da memoria NAO e a serializacao sob
        prova — ele so normaliza tupla em lista, para que a comparacao meca o que
        o SERVIDOR fez e nao a diferenca entre dois tipos de sequencia do Python.
        """
        agora = datetime.now()
        em_memoria = json.loads(
            json.dumps(
                dashboard_dados.payload(
                    pasta_do_mercado,
                    agora,
                    cambio=None,
                    itens=itens,
                    itens_lidos_em=agora,
                )["calculadora"]
            )
        )
        _status, dados = _get_dados(servidor.server_address[1])
        do_soquete = dados["calculadora"]

        assert _chaves_profundas(em_memoria), "o extrator nao achou caminho nenhum"
        assert _chaves_profundas(do_soquete) == _chaves_profundas(em_memoria)

        for indice, (esperado, veio) in enumerate(
            zip(em_memoria["itens"], do_soquete["itens"])
        ):
            for caminho in sorted(_chaves_profundas(esperado)):
                assert caminho_existe(veio, caminho), (indice, caminho)
            assert veio == esperado, indice

    def test_CONTROLE_a_comparacao_ACUSA_um_campo_perdido_na_serializacao(
        self, servidor
    ):
        """Sem esta metade, a igualdade acima passaria tambem se os dois lados
        viessem vazios — ou se `caminho_existe` respondesse sempre `True`."""
        _status, dados = _get_dados(servidor.server_address[1])
        entrada = dados["calculadora"]["itens"][INDICE_DO_TERCEIRO]

        import copy

        mutilada = copy.deepcopy(entrada)
        alvo = sorted(mutilada["diferenca"])[0]
        del mutilada["diferenca"][alvo]

        assert not caminho_existe(mutilada, "diferenca." + alvo)
        assert caminho_existe(entrada, "diferenca." + alvo)
        assert mutilada != entrada


# ===========================================================================
# ELO 5 — A TELA, POR LEITURA DE FONTE
# ===========================================================================


class TestElo5ATelaLeOsTRESIgual:
    """O elo que fecha a prova.

    Sem ele, os quatro primeiros mostrariam que o SERVIDOR e generico e nao que
    o DESENHO e — a pintura poderia estar lendo `item.gemstone_pacote` que
    ninguem perceberia.

    Os dois extratores sao IMPORTADOS de
    `tests/test_dashboard_calculadora_pagina.py`, onde nasceram no plano 02-03.
    """

    def test_toda_propriedade_que_a_pintura_LE_existe_nas_TRES_entradas(
        self, bloco: dict
    ):
        """A ASSERCAO DE NAO-VAZIO VEM ANTES DA COMPARACAO, E E OBRIGATORIA.

        Com o conjunto vazio, `vazio <= qualquer_coisa` e VERDADE: a comparacao
        passaria sobre um `dashboard.js` sem funcao de pintura nenhuma, sobre um
        arquivo apagado, e sobre um extrator quebrado.
        """
        consumidas = propriedades_do_item_consumidas(
            ARQUIVO_DO_JS.read_text(encoding="utf-8")
        )
        assert consumidas, (
            "o extrator nao achou NENHUMA propriedade lida pela pintura. A "
            "comparacao abaixo passaria por vacuidade."
        )

        for indice, entrada in enumerate(bloco["itens"]):
            faltando = sorted(
                caminho
                for caminho in consumidas
                if not caminho_existe(entrada, caminho)
            )
            assert not faltando, (
                f"a pintura le {faltando} e a entrada #{indice + 1} nao tem "
                f"esse(s) campo(s): desenhar este item exigiria codigo de tela "
                f"novo, que e o que o CALC-05 proibe"
            )

    def test_o_conjunto_que_RESOLVE_e_o_MESMO_nas_TRES_entradas(
        self, bloco: dict
    ):
        """A metade que a assercao de cima nao cobre.

        Aquela exige que TODAS resolvam nas tres. Esta mede a mesma coisa por um
        angulo que sobrevive a ela ser afrouxada um dia: seja qual for o
        subconjunto que resolve, ele tem de ser o MESMO nos tres — uma
        propriedade que resolvesse nos dois primeiros e nao no terceiro seria
        exatamente o caso especial que o requisito recusa.
        """
        consumidas = propriedades_do_item_consumidas(
            ARQUIVO_DO_JS.read_text(encoding="utf-8")
        )
        assert consumidas

        resolvem = [
            {c for c in consumidas if caminho_existe(entrada, c)}
            for entrada in bloco["itens"]
        ]
        assert resolvem[0]
        for indice, outro in enumerate(resolvem[1:], start=1):
            assert outro == resolvem[0], (indice, sorted(outro ^ resolvem[0]))

    def test_a_pintura_escreve_em_TODOS_os_vaos_do_molde_e_SO_neles(self):
        """As duas direcoes, com o nao-vazio nos dois lados.

        Um vao orfao e copia morta com cara de campo — o `02-03` encontrou um
        real assim. Um vao inexistente e escrita silenciosa no vazio.
        """
        escritos = vaos_escritos_pela_pintura(
            ARQUIVO_DO_JS.read_text(encoding="utf-8")
        )
        do_molde = set(
            vaos_de(molde_da_linha(ARQUIVO_DO_HTML.read_text(encoding="utf-8")))
        )
        assert escritos, "o extrator nao achou vao escrito nenhum"
        assert do_molde, "o extrator nao achou vao nenhum no molde"
        assert escritos == do_molde, sorted(escritos ^ do_molde)

    def test_CONTROLE_o_extrator_ACUSA_o_que_diz_medir(self):
        """O controle do elo 5, nos DOIS sentidos, sobre JS fabricado aqui.

        A mutacao nao acontece sobre o arquivo real: e a unica forma de provar
        que o extrator enxerga sem depender do que ele deveria estar medindo.
        """
        fabricado = (
            "function montarUmaRota(molde, item) {\n"
            '  escreverNoVao(f, "item", item.nome_exibido);\n'
            "  return item.diferenca.reais;\n"
            "}\n"
        )
        assert propriedades_do_item_consumidas(fabricado) == {
            "nome_exibido",
            "diferenca",
            "diferenca.reais",
        }
        assert vaos_escritos_pela_pintura(fabricado) == {"item"}

        # O outro sentido: com a funcao de pintura PRESENTE e sem leitura
        # nenhuma dentro dela, conjunto VAZIO. Sem esta metade, um extrator que
        # devolvesse SEMPRE o mesmo conjunto tambem passaria na assercao de cima.
        sem_leitura = "function montarUmaRota(molde, item) {\n  return molde;\n}\n"
        assert propriedades_do_item_consumidas(sem_leitura) == set()
        assert vaos_escritos_pela_pintura(sem_leitura) == set()

    def test_o_extrator_QUEBRA_quando_a_funcao_de_pintura_SUMIU(self):
        """A terceira metade do controle, e ela e uma MEDICAO e nao um desejo.

        O modo de falha mais perigoso de um extrator por leitura de fonte e
        devolver conjunto vazio quando o alvo sumiu — ai `vazio <= qualquer
        coisa` vale, e o elo 5 inteiro passa sobre um `dashboard.js` apagado.

        MEDIDO: `_corpo_da_funcao` **levanta `ValueError`** nesse caso, em vez de
        devolver vazio. Fica preso aqui porque e uma propriedade da qual este
        arquivo DEPENDE, e ela mora em outro arquivo: no dia em que alguem
        trocar aquele `index` por um `find` que devolve -1, esta assercao fica
        vermelha antes de o elo 5 comecar a mentir.
        """
        sem_pintura = "function pintar(dados) {\n  return dados.destaque;\n}\n"
        with pytest.raises(ValueError):
            propriedades_do_item_consumidas(sem_pintura)

    def test_CONTROLE_um_payload_de_MENTIRA_sem_uma_propriedade_e_ACUSADO(
        self, bloco: dict
    ):
        """E a prova de que a comparacao do primeiro teste discrimina."""
        import copy

        consumidas = propriedades_do_item_consumidas(
            ARQUIVO_DO_JS.read_text(encoding="utf-8")
        )
        de_topo = sorted(c for c in consumidas if "." not in c)
        assert de_topo

        mentira = copy.deepcopy(bloco["itens"][INDICE_DO_TERCEIRO])
        del mentira[de_topo[0]]

        assert [c for c in consumidas if not caminho_existe(mentira, c)]


# ===========================================================================
# O ELO TRANSVERSAL — NENHUM NOME DE ITEM E LITERAL NA PRODUCAO
# ===========================================================================
#
# A SONDA DO 02-02 VARRIA OS DOIS MODULOS PYTHON. Este arquivo a estende aos
# dois arquivos de TELA, que sao a outra metade do que o CALC-05 proibe: "sem
# codigo novo de calculo NEM DE TELA".
#
# A LISTA DO QUE PROCURAR SAI DA CONFIGURACAO DE TESTE, e nao de nomes escritos
# aqui. Ver o cabecalho: uma lista a mao mede a lista, e para de cobrir no dia em
# que um quarto item entrar na fixture.
#
# **AS SONDAS LEEM SO O CODIGO, E ISSO ESTA MEDIDO.** Rodada sobre o texto cru, a
# sonda ACUSA o `dashboard_rotas.py` — as acusacoes estao dentro da docstring que
# explica por que o casamento exato existe. Uma sonda que pune o arquivo por
# NOMEAR o defeito que ele evita ensina a apagar a explicacao, e a explicacao e
# metade do valor do arquivo. O 02-02 mediu isso do lado do Python e o
# `test_dashboard_js._so_o_codigo` do lado do JS; aqui as duas limpezas sao
# REUSADAS, e nao reescritas.

_COMENTARIO_DE_CSS = re.compile(r"/\*.*?\*/", re.DOTALL)


def _so_o_codigo_css(css: str) -> str:
    """O CSS sem comentario. A unica forma de comentario que o CSS tem e
    `/* */`, entao a limpeza cabe numa linha — e ela existe separada porque o
    removedor de JS tambem tira linhas iniciadas por `//`, que em CSS nao e
    comentario e sim texto de conteudo possivel."""
    return _COMENTARIO_DE_CSS.sub("", css)


def nomes_de_item_no_texto(texto: str, nomes, limpeza) -> list:
    """Os nomes que aparecem como LITERAL no codigo. A SONDA GENERICA.

    POR QUE ELA NAO E `_nomes_de_item_no_codigo` DO 02-02, e a diferenca nao e
    cosmetica: aquela tem a lista de procurados FIXA dentro dela e so sabe ler
    Python. Esta recebe a lista (que sai da configuracao) e a limpeza (que sai do
    arquivo que a definiu), e por isso alcanca os quatro arquivos.

    A COERENCIA ENTRE AS DUAS E MEDIDA por
    `test_esta_sonda_CONCORDA_com_a_do_02_02` — sem isso seriam duas autoridades
    sobre a mesma invariante, que e o defeito que esta arvore ja pagou.
    """
    codigo = limpeza(texto).lower()
    return [nome for nome in nomes if nome.lower() in codigo]


ARQUIVOS_VARRIDOS = (
    (Path(dashboard_rotas.__file__), _so_o_codigo_python),
    (Path(dashboard_dados.__file__), _so_o_codigo_python),
    (ARQUIVO_DO_JS, _so_o_codigo),
    (ARQUIVO_DO_CSS, _so_o_codigo_css),
)


@pytest.fixture(scope="module")
def nomes(itens) -> list:
    """A lista de procurados SAI DA CONFIGURACAO, e nao do fonte deste teste.

    Ver o cabecalho: uma lista escrita a mao mede a lista, e para de cobrir no
    dia em que um quarto item entrar na fixture.
    """
    return [item.nome for item in itens]


class TestNenhumNomeDeItemEhLiteralNaProducao:
    """O elo NEGATIVO, e o que faz os cinco de cima valerem alguma coisa.

    Um `if` por item passaria em TODA contagem de chaves deste arquivo com
    folga.
    """

    def test_a_lista_procurada_sai_mesmo_da_CONFIGURACAO_e_nao_esta_VAZIA(
        self, nomes
    ):
        """A guarda anti-vacuidade da sonda transversal.

        Com a lista vazia, todas as varreduras abaixo devolveriam `[]` e o elo
        inteiro passaria sobre um `if` por nome escrito em letras garrafais.
        """
        assert len(nomes) == len(_ITENS_DA_PROVA)
        assert all(nome.strip() for nome in nomes)

    @pytest.mark.parametrize(
        "caminho,limpeza",
        ARQUIVOS_VARRIDOS,
        ids=[caminho.name for caminho, _limpeza in ARQUIVOS_VARRIDOS],
    )
    def test_o_arquivo_de_producao_NAO_traz_nome_de_item_nenhum(
        self, caminho: Path, limpeza, nomes
    ):
        fonte = caminho.read_text(encoding="utf-8")
        assert nomes_de_item_no_texto(fonte, nomes, limpeza) == [], caminho.name

    def test_CONTROLE_a_sonda_ACUSA_um_texto_com_um_if_por_NOME(self, nomes):
        """Sem este controle, a sonda passaria sobre um arquivo vazio."""
        mentira = (
            "def preco(item):\n"
            f'    if item.nome == "{nomes[0]}":\n'
            "        return 1\n"
            "    return 2\n"
        )
        assert nomes_de_item_no_texto(mentira, nomes, _so_o_codigo_python) == [
            nomes[0]
        ]

    def test_CONTROLE_a_sonda_NAO_acusa_o_nome_citado_so_na_PROSA(self, nomes):
        """A metade que protege a explicacao — as tres linguagens."""
        so_na_prosa_python = (
            f'"""A refutacao: o corte juntaria {nomes[0]} com {nomes[1]}."""\n'
            "def preco(item):\n"
            "    return item.preco_npc_adena\n"
        )
        assert (
            nomes_de_item_no_texto(so_na_prosa_python, nomes, _so_o_codigo_python)
            == []
        )

        so_na_prosa_js = f"// A pintura nao conhece {nomes[0]}.\nvar a = 1;\n"
        assert nomes_de_item_no_texto(so_na_prosa_js, nomes, _so_o_codigo) == []

        so_na_prosa_css = f"/* Nem o tema conhece {nomes[0]}. */\n.rota {{}}\n"
        assert (
            nomes_de_item_no_texto(so_na_prosa_css, nomes, _so_o_codigo_css) == []
        )

    def test_CONTROLE_as_limpezas_NAO_engolem_o_codigo_junto_com_a_prosa(
        self, nomes
    ):
        """O outro sentido do controle acima, e ele e o que importa mais.

        Uma limpeza que devolvesse cadeia vazia deixaria a sonda VERDE sobre
        qualquer coisa — inclusive sobre os quatro arquivos reais. As tres tem
        de ACUSAR quando o nome esta no codigo.
        """
        assert nomes_de_item_no_texto(
            f'X = "{nomes[0]}"\n', nomes, _so_o_codigo_python
        ) == [nomes[0]]
        assert nomes_de_item_no_texto(
            f'var x = "{nomes[0]}";\n', nomes, _so_o_codigo
        ) == [nomes[0]]
        assert nomes_de_item_no_texto(
            f'.rota::after {{ content: "{nomes[0]}"; }}\n', nomes, _so_o_codigo_css
        ) == [nomes[0]]

    def test_esta_sonda_CONCORDA_com_a_do_02_02_sobre_os_modulos_PYTHON(self):
        """A guarda contra as DUAS AUTORIDADES.

        Onde os dominios se sobrepoem — os dois modulos Python — as duas sondas
        tem de dar o mesmo veredito. No dia em que uma delas for afrouxada, esta
        assercao fica vermelha em vez de a mais fraca sobreviver calada.
        """
        procurados = list(NOMES_DO_ROADMAP) + [NOME_DO_TERCEIRO]
        for modulo in (dashboard_rotas, dashboard_dados):
            fonte = Path(modulo.__file__).read_text(encoding="utf-8")
            assert nomes_de_item_no_texto(
                fonte, procurados, _so_o_codigo_python
            ) == _nomes_de_item_no_codigo(fonte), modulo.__name__

    def test_o_nome_do_TERCEIRO_nao_aparece_em_ARQUIVO_DE_PRODUCAO_NENHUM(self):
        """A afirmacao mais forte deste arquivo, e ela e sobre a arvore inteira.

        Nao "nao aparece nos quatro que a sonda varre", e sim **em nenhum arquivo
        da cerca de producao** — `l2scanner/**` mais o `config.toml`. Sobre o
        TEXTO CRU, comentario incluso: aqui a prosa nao e perdoada, porque a
        afirmacao e "o codigo nunca viu este item", e um item citado num
        comentario ja foi visto por alguem.

        `tests/**` esta fora da varredura pela razao obvia — o nome mora neste
        arquivo e no do 02-02 — e `.planning/**` tambem, porque e la que o
        SUMMARY deste plano vai morar.
        """
        alvos = [caminho for caminho in (RAIZ / "l2scanner").rglob("*") if caminho.is_file()]
        arquivo_de_config = RAIZ / ARQUIVO_DE_CONFIGURACAO
        if arquivo_de_config.exists():
            alvos.append(arquivo_de_config)
        assert alvos, "a varredura nao achou arquivo de producao nenhum"

        acusados = []
        for caminho in alvos:
            try:
                texto = caminho.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if NOME_DO_TERCEIRO.lower() in texto.lower():
                acusados.append(str(caminho.relative_to(RAIZ)))
        assert acusados == [], acusados

    def test_CONTROLE_a_varredura_da_arvore_ACUSA_o_que_diz_medir(
        self, tmp_path: Path, nomes
    ):
        """Sem esta metade, a varredura acima passaria tambem se ela nao
        estivesse LENDO arquivo nenhum — que e o modo de falha de toda varredura
        por `rglob`."""
        (tmp_path / "fingido.py").write_text(
            f'NOME = "{NOME_DO_TERCEIRO}"\n', encoding="utf-8"
        )
        (tmp_path / "limpo.py").write_text("NOME = 1\n", encoding="utf-8")

        acusados = [
            caminho.name
            for caminho in tmp_path.rglob("*")
            if caminho.is_file()
            and NOME_DO_TERCEIRO.lower()
            in caminho.read_text(encoding="utf-8", errors="ignore").lower()
        ]
        assert acusados == ["fingido.py"]


# ===========================================================================
# A FRONTEIRA DESTA PROVA, DECLARADA
# ===========================================================================


class TestAFronteiraDestaProvaEstaDECLARADA:
    """Uma reserva de verificacao que nao esta escrita nao existe."""

    @staticmethod
    def _cabecalho() -> str:
        return ESTE_ARQUIVO.read_text(encoding="utf-8").split('"""')[1]

    def test_o_cabecalho_diz_por_extenso_o_que_esta_prova_NAO_alcanca(self):
        """Se o cabecalho perder a frase, o proximo leitor vai achar que o verde
        aqui cobre o desenho — e a metade que so o olho ve some do registro sem
        ninguem decidir isso."""
        cabecalho = self._cabecalho()
        assert "**nao** garante o DESENHO" in cabecalho
        assert "VERIFICACAO HUMANA DECLARADA" in cabecalho
        assert "fique legivel na tela" in cabecalho

    def test_o_cabecalho_declara_que_os_NOMES_nao_estao_escritos_aqui(self):
        cabecalho = self._cabecalho()
        assert "NAO ESTAO ESCRITOS NESTE ARQUIVO" in cabecalho

    def test_o_arquivo_NAO_escreve_os_nomes_que_ele_procura(self):
        """A declaracao do cabecalho, MEDIDA — e nao so afirmada.

        A varredura e sobre o fonte inteiro deste arquivo, comentarios inclusos,
        e cobre todos os nomes procurados. A unica excecao e a linha da propria
        assercao, que precisa nomear o que procura.
        """
        fonte = ESTE_ARQUIVO.read_text(encoding="utf-8")
        for nome in list(NOMES_DO_ROADMAP) + [NOME_DO_TERCEIRO]:
            assert nome.lower() not in fonte.lower(), nome


# ===========================================================================
# TAREFA 2 — OS GATES DE ESCOPO DESTA FASE
# ===========================================================================
#
# POR QUE ELES SAO TESTE E NAO SO PARAGRAFO DE SUMMARY: um gate que so existe no
# documento e um gate que ninguem roda de novo. O SUMMARY registra a MEDICAO de
# uma vez; o teste a refaz a cada rodada, e fica vermelho no dia em que a
# premissa cair.
#
# O QUE NAO CABE EM TESTE, E POR QUE: a atribuicao por COMMIT dos sete arquivos
# da cerca dura. O `01-08` mediu que **um `git diff` cru contra a base nao mede o
# que esta fase fez** — a branch e compartilhada com outros workstreams, e o diff
# cru acusa commits de gente que nao e daqui. A atribuicao correta e por commit,
# ela mora no SUMMARY com o comando e a saida, e o que sobra para o teste e o que
# da para afirmar sem git: a DIRECAO da dependencia.

CERCA_DURA = (
    "rastreador.py",
    "visao.py",
    "console.py",
    "mercado_registro.py",
    "mercado_analise.py",
    "mercado_console.py",
    "mercado_catalogo.py",
)

MODULOS_DO_DASHBOARD = ("dashboard.py", "dashboard_dados.py", "dashboard_rotas.py")


def importa_o_dashboard(fonte: str) -> list:
    """Os imports de modulo de dashboard que um fonte declara. A SONDA DO GATE 1.

    Ela le so o CODIGO: um comentario do `mercado_analise` que cite o dashboard
    e prosa, e prosa nao cria dependencia.
    """
    codigo = _so_o_codigo_python(fonte)
    achados = []
    for modulo in MODULOS_DO_DASHBOARD:
        nome = modulo[: -len(".py")]
        if re.search(r"\b(import|from)\s+\.?" + nome + r"\b", codigo):
            achados.append(modulo)
    return achados


class TestGate1ACercaDuraDoWorkstreamMercado:
    """Os sete arquivos que este workstream nao pode alterar.

    O QUE ESTA CLASSE MEDE E A DIRECAO DA DEPENDENCIA, e ela e uma invariante de
    verdade: o dashboard LE a cerca, e a cerca nao conhece o dashboard. Se
    alguma coisa desta fase tivesse exigido uma mudanca la dentro, o caminho mais
    barato — e o primeiro que alguem tomaria — seria um import de volta. Ele
    cairia aqui.

    **O QUE ESTE GATE ACRESCENTA AO QUE O PYTHON JA FAZ, MEDIDO.** A objecao
    obvia e que um import de volta ja quebra sozinho, e ela e METADE verdadeira:
    posto no topo de `mercado_analise.py`, um `from . import dashboard_rotas`
    derruba a COLETA inteira do pytest com `ImportError: cannot import name
    'N_MINIMO_PARA_MEDIANA' ... (most likely due to a circular import)` — medido
    em 2026-09-04.

    Mas o mesmo import DENTRO de uma funcao (`resolver_o_nome`) nao cria ciclo
    nenhum no carregamento do modulo, a suite inteira sobe, e nada quebra. E
    justamente essa a forma que alguem escreveria: e o conserto que o traceback
    do ciclo SUGERE. Medido na mesma sessao: com o import diferido, o unico teste
    vermelho da arvore e
    `test_o_modulo_da_cerca_NAO_importa_o_dashboard[mercado_analise.py]`.
    """

    @pytest.mark.parametrize("arquivo", CERCA_DURA)
    def test_o_modulo_da_cerca_NAO_importa_o_dashboard(self, arquivo: str):
        fonte = (RAIZ / "l2scanner" / arquivo).read_text(encoding="utf-8")
        assert importa_o_dashboard(fonte) == [], arquivo

    def test_os_modulos_do_dashboard_REALMENTE_LEEM_a_cerca(self):
        """A guarda anti-vacuidade do gate 1.

        Sem ela, os sete testes acima passariam sobre uma arvore em que o
        dashboard e a cerca nao se conhecem em direcao nenhuma — e ai a
        afirmacao "ele le e nunca escreve" nao estaria sendo feita sobre relacao
        nenhuma.
        """
        lidos = set()
        for modulo in (dashboard_rotas, dashboard_dados):
            codigo = _so_o_codigo_python(
                Path(modulo.__file__).read_text(encoding="utf-8")
            )
            for arquivo in CERCA_DURA:
                nome = arquivo[: -len(".py")]
                if re.search(r"\b(import|from)\s+\.?" + nome + r"\b", codigo):
                    lidos.add(arquivo)
        assert lidos, "nenhum modulo do dashboard importa a cerca dura"

    def test_CONTROLE_a_sonda_ACUSA_um_fonte_que_importa_o_dashboard(self):
        assert importa_o_dashboard(
            "from . import dashboard_rotas\n"
        ) == ["dashboard_rotas.py"]
        assert importa_o_dashboard("from .dashboard_dados import payload\n") == [
            "dashboard_dados.py"
        ]

    def test_CONTROLE_a_sonda_NAO_acusa_a_citacao_em_COMENTARIO(self):
        """A metade que protege a explicacao, de novo — e ela nao e teorica:
        `mercado_analise` e `mercado_console` explicam em prosa quem consome
        cada funcao deles."""
        assert (
            importa_o_dashboard(
                '"""Quem consome isto e o dashboard_dados."""\n'
                "# ver dashboard_rotas\n"
                "X = 1\n"
            )
            == []
        )


class TestGate2NenhumaDependenciaNova:
    """O `requirements.txt` nao ganhou uma linha nesta fase.

    O extrator e a lista de distribuicoes sao IMPORTADOS de
    `tests/test_firewall_dashboard.py`, e nao reescritos: um segundo extrator com
    um corte de nome ligeiramente diferente seria a forma mais silenciosa de os
    firewalls discordarem sobre o que e um nome de pacote.
    """

    @staticmethod
    def _autoridade():
        from tests.test_firewall_dashboard import (
            DISTRIBUICOES_ANTES_DA_FASE_01_DASHBOARD,
        )
        from tests.test_firewall_escopo import _nomes_declarados_no_requirements

        return _nomes_declarados_no_requirements, (
            DISTRIBUICOES_ANTES_DA_FASE_01_DASHBOARD
        )

    def test_o_requirements_nao_ganhou_linha_nesta_FASE(self):
        extrair, esperadas = self._autoridade()
        texto = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
        assert extrair(texto) == esperadas

    def test_CONTROLE_o_guarda_REPROVA_quando_uma_linha_NOVA_e_declarada(self):
        """A mutacao acontece no TEXTO entregue ao extrator, e nunca no
        `requirements.txt` do disco — acrescentar uma dependencia de verdade
        dentro de um teste seria cometer o que o teste existe para impedir."""
        extrair, esperadas = self._autoridade()
        texto = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
        nomes = extrair(texto + "\nplotly>=6.0\n")
        assert nomes != esperadas
        assert "plotly" in nomes


class TestGate3ODashboardNuncaEscreveNoCSV:
    """A promessa central do DASH-01 continua valendo depois desta fase.

    A MEDICAO ACONTECE SOBRE COPIA EM PASTA TEMPORARIA, E NUNCA SOBRE O ARQUIVO
    REAL. Um teste que medisse o `.mercado/` do usuario para provar que nao
    escreve nele ja teria falhado em espirito na primeira linha — e um teste que
    escrevesse la por acidente destruiria o material que este projeto inteiro
    depende de acumular.

    A IMPRESSAO E DE TRES COMPONENTES (tamanho, `mtime_ns`, sha256), e o
    extrator vem de `tests/test_dashboard_servidor.py`. A razao dos tres juntos
    esta escrita la: uma reescrita com bytes identicos nao muda o hash, e
    "escreveu por cima com o mesmo conteudo" continua sendo escrita.
    """

    def test_rodar_a_calculadora_NAO_muda_um_byte_do_CSV(
        self, pasta_do_mercado: Path, itens
    ):
        arquivo = next(pasta_do_mercado.glob("*.csv"))
        antes = _impressao_do_arquivo(arquivo)
        nomes_antes = {caminho.name for caminho in pasta_do_mercado.iterdir()}

        for _ in range(5):
            agora = datetime.now()
            dashboard_dados.payload(
                pasta_do_mercado,
                agora,
                cambio=None,
                itens=itens,
                itens_lidos_em=agora,
            )

        assert _impressao_do_arquivo(arquivo) == antes
        assert {
            caminho.name for caminho in pasta_do_mercado.iterdir()
        } == nomes_antes

    def test_CONTROLE_a_impressao_ACUSA_uma_escrita_de_MESMO_conteudo(
        self, tmp_path: Path
    ):
        """Sem este controle, a assercao acima passaria tambem se
        `_impressao_do_arquivo` devolvesse uma constante.

        A mutacao escolhida e a MAIS DIFICIL de pegar de proposito: reescrever o
        arquivo com bytes identicos. E ela que separa a impressao de tres
        componentes de um sha256 sozinho.
        """
        alvo = tmp_path / "observacoes.csv"
        alvo.write_text("a;b\n", encoding="utf-8", newline="")
        antes = _impressao_do_arquivo(alvo)

        import os
        import time

        time.sleep(0.01)
        alvo.write_text("a;b\n", encoding="utf-8", newline="")
        os.utime(alvo, ns=(antes[1] + 1_000_000, antes[1] + 1_000_000))

        assert _impressao_do_arquivo(alvo) != antes
