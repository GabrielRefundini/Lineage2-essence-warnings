"""O PISO do veredito, o R$ que some sozinho, e a mediana como CONTEXTO.

O QUE ESTE ARQUIVO PRENDE, EM UMA FRASE
========================================
Que a calculadora do plano 02-01 -- que ja atravessava do `config.toml` ao JSON
-- so ABRE A BOCA quando ha evidencia dos DOIS lados da comparacao, e que o
numero em R$ e a unica coisa que some quando o cambio nao foi informado.

ELE NAO REPETE O `test_dashboard_rotas_tracer.py`. Aquele prende a CONTA (a
exatidao em `Fraction`, a faixa de empate, a ordem da lista, o tracer ate o
servidor). Este prende o JULGAMENTO: quanta evidencia autoriza um veredito, o
que acontece com quem fica abaixo dela, e o que a tela NAO pode imprimir.

NADA AQUI TOCA A `.mercado/` REAL NEM O `config.toml` REAL. Todo CSV nasce em
`tmp_path` e todo item e montado a mao.

ESTE ARQUIVO NAO LEVA LETRA ACENTUADA, como o resto de `tests/`. As frases
acentuadas de que ele precisa sao IMPORTADAS do Python que as define -- copiar
uma frase para ca seria a segunda copia que o DASH-03 recusa.

TODA CONTAGEM DE OFERTA SAI DA CONSTANTE, E NUNCA DE UM NUMERO ESCRITO A MAO.
Um `5` digitado aqui continuaria verde no dia em que o piso descesse, e o teste
passaria a medir o numero antigo em silencio.
"""

from __future__ import annotations

import importlib
import re
from datetime import datetime
from fractions import Fraction
from pathlib import Path

import pytest

from l2scanner import (
    dashboard_dados,
    dashboard_rotas,
    mercado_analise,
    mercado_registro,
)
from l2scanner.config import ItemDeRota
from l2scanner.mercado_analise import ModeloDeMercado
from l2scanner.mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA, SEPARADOR
from l2scanner.mercado_registro import ObservacaoLida

TERMINADOR = "\r\n"
AGORA = datetime(2026, 9, 1, 15, 0, 0)

# A TAXA REAL MEDIDA no `.mercado/observacoes.csv` de 2026-09-03: o menor pedido
# da Adena e 45,00 XM por 5.000.000 de adena.
TAXA_MEDIDA = Fraction(9, 10000)

CHAVE_DO_ITEM = "gemstone-c#0"
NOME_DO_ITEM = "Gemstone C"


# ---------------------------------------------------------------------------
# O MATERIAL -- todas as contagens DERIVADAS do piso
# ---------------------------------------------------------------------------


def _piso() -> int:
    """O piso do veredito, lido na hora.

    Lido A CADA CHAMADA, e nao guardado numa constante de modulo: o teste do
    controle da ligacao recarrega `dashboard_rotas` no meio da sessao, e uma
    copia congelada no import deste arquivo deixaria de acompanhar.
    """
    return dashboard_rotas.N_MINIMO_PARA_O_VEREDITO


def _item(nome=NOME_DO_ITEM, preco=15000, pacote=1) -> ItemDeRota:
    return ItemDeRota(
        nome=nome, preco_npc_adena=preco, quantidade_do_pacote=pacote
    )


def _obs(chave, nome, quando, total, quantidade) -> ObservacaoLida:
    return ObservacaoLida(
        chave_da_serie=chave,
        nome_exibido=nome,
        primeira_vez=quando,
        total_em_centesimos=total,
        quantidade=quantidade,
        residuo_do_cruzamento=0,
    )


def _serie(chave, nome, totais, quantidade=1):
    """`n` observacoes distintas da mesma serie, uma por minuto.

    O MENOR E SEMPRE O PRIMEIRO TOTAL da lista, por construcao das fixturas
    abaixo -- e por isso trocar a CAUDA da serie muda a mediana sem mover o
    menor pedido visivel, que e exatamente o controle de que a mediana nao
    decide nada.
    """
    base = datetime(2026, 9, 1, 14, 0, 0)
    return [
        _obs(chave, nome, base.replace(minute=indice), total, quantidade)
        for indice, total in enumerate(totais)
    ]


def _totais_do_item(quantas, menor=5900):
    """`quantas` totais distintos, com o MENOR cravado no primeiro."""
    return [menor] + [menor + 100 * (i + 1) for i in range(quantas - 1)]


def _modelo_do_item(quantas=None, menor=5900, quantidade=1):
    quantas = _piso() if quantas is None else quantas
    return ModeloDeMercado.de_observacoes(
        _serie(
            CHAVE_DO_ITEM,
            NOME_DO_ITEM,
            _totais_do_item(quantas, menor),
            quantidade,
        )
    )


# ---------------------------------------------------------------------------
# O MATERIAL EM CSV -- para os quatro cruzamentos, que passam pelo payload
# ---------------------------------------------------------------------------


def _linha(chave, nome, carimbo, total, quantidade) -> str:
    return SEPARADOR.join(
        (chave, nome, carimbo.isoformat(), str(total), str(quantidade), "0")
    )


def _escrever_csv(pasta: Path, linhas) -> Path:
    alvo = pasta / mercado_registro.ARQUIVO_DE_OBSERVACOES
    corpo = SEPARADOR.join(mercado_registro.COLUNAS) + TERMINADOR
    corpo += "".join(linha + TERMINADOR for linha in linhas)
    alvo.write_text(corpo, encoding="utf-8", newline="")
    return alvo


def _linhas_da_adena(quantas):
    """`quantas` ofertas da Adena, com o MENOR a `Fraction(9, 10000)` por adena.

    O menor e o primeiro (45,00 XM por 5.000.000); as demais sao mais caras, de
    modo que a taxa USADA nao muda com a contagem -- o que isola a evidencia
    como a unica variavel dos quatro cruzamentos.
    """
    base = datetime(2026, 9, 1, 14, 50, 0)
    return [
        _linha(
            CHAVE_DA_SERIE_DA_ADENA,
            "Adena",
            base.replace(minute=50 - indice),
            4500 + 100 * indice,
            5_000_000,
        )
        for indice in range(quantas)
    ]


def _linhas_do_item(quantas, menor=5900):
    base = datetime(2026, 9, 1, 14, 30, 0)
    return [
        _linha(
            CHAVE_DO_ITEM,
            NOME_DO_ITEM,
            base.replace(minute=30 - indice),
            total,
            1,
        )
        for indice, total in enumerate(_totais_do_item(quantas, menor))
    ]


@pytest.fixture
def pasta(tmp_path: Path) -> Path:
    alvo = tmp_path / ".mercado"
    alvo.mkdir()
    return alvo


def _bloco(pasta: Path, adena, item, cambio=None, itens=None):
    _escrever_csv(pasta, _linhas_da_adena(adena) + _linhas_do_item(item))
    return dashboard_dados.payload(
        pasta, AGORA, cambio, itens if itens is not None else [_item()], AGORA
    )["calculadora"]


# ===========================================================================
# O PISO DO VEREDITO -- LIGADO, E NAO COPIADO
# ===========================================================================


class TestOPisoDoVeredito:
    def test_o_piso_e_o_da_MEDIANA_e_NAO_o_do_MENOR(self):
        """A razao de a ligacao existir, e nao a ligacao.

        **ESTE TESTE NAO E O GUARDA.** Ele passa igual sobre um literal `5`
        escrito a mao. O que ele prende e o PORQUE: `N_MINIMO_PARA_MENOR` vale
        um, e um veredito sobre uma unica oferta e o que o CALC-04 nomeia como
        pior que nenhum veredito. Quem prende a ligacao e o teste seguinte.
        """
        assert (
            dashboard_rotas.N_MINIMO_PARA_O_VEREDITO
            == mercado_analise.N_MINIMO_PARA_MEDIANA
        )
        assert (
            dashboard_rotas.N_MINIMO_PARA_O_VEREDITO
            != mercado_analise.N_MINIMO_PARA_MENOR
        )
        assert mercado_analise.N_MINIMO_PARA_MENOR == 1

    def test_CONTROLE_o_piso_ACOMPANHA_a_mediana_quando_ela_muda(
        self, monkeypatch
    ):
        """O GUARDA da ligacao, com o mecanismo NOMEADO.

        SAO DOIS PASSOS E A RAZAO E MECANICA: `N_MINIMO_PARA_O_VEREDITO` recebe
        um `int` no momento do import, entao **o `monkeypatch` sozinho nao
        acorda nenhuma das duas implementacoes** -- nem a ligada nem a copiada.
        Um teste que parasse ali seria verde sobre as duas, e a primeira
        assercao abaixo e justamente essa metade, escrita para nao ser
        confundida com o guarda.

        QUAL IMPLEMENTACAO ESTE CONTROLE DEIXA VERMELHA: com o `reload`, a que
        copiou o numero como literal continua no valor antigo e reprova; a que
        le de `mercado_analise` no import passa a valer o novo e aprova.

        O VALOR ORIGINAL E RESTAURADO **E O MODULO E RECARREGADO DE NOVO**, para
        nao deixar um `dashboard_rotas` adulterado para os testes seguintes da
        mesma sessao.
        """
        original = mercado_analise.N_MINIMO_PARA_MEDIANA
        novo = original + 3
        monkeypatch.setattr(mercado_analise, "N_MINIMO_PARA_MEDIANA", novo)

        # A METADE QUE NAO DISCRIMINA, dita em voz alta.
        assert dashboard_rotas.N_MINIMO_PARA_O_VEREDITO == original

        importlib.reload(dashboard_rotas)
        try:
            assert dashboard_rotas.N_MINIMO_PARA_O_VEREDITO == novo
        finally:
            monkeypatch.setattr(
                mercado_analise, "N_MINIMO_PARA_MEDIANA", original
            )
            importlib.reload(dashboard_rotas)

        assert dashboard_rotas.N_MINIMO_PARA_O_VEREDITO == original

    def test_a_razao_do_piso_esta_ESCRITA_no_fonte_com_a_marca_de_ESCOLHA(self):
        """Um piso sem a razao ao lado vira numero magico na primeira leitura.

        A marca `ESCOLHA` e obrigatoria: ninguem mediu quantas ofertas
        distintas por serie o material real produz, e um numero que parece
        medido nao se discute.
        """
        fonte = Path(dashboard_rotas.__file__).read_text(encoding="utf-8")
        posicao = fonte.index("N_MINIMO_PARA_O_VEREDITO")
        janela = fonte[max(0, posicao - 2500) : posicao]
        assert "ESCOLHA" in janela
        assert "N_MINIMO_PARA_MENOR" in janela


# ===========================================================================
# A BORDA DO PISO, E O `n=1` QUE O CALC-04 NOMEIA
# ===========================================================================


class TestABordaDoPiso:
    def _veredito(self, quantas):
        return dashboard_rotas.veredito_de_uma_rota(
            _item(), _modelo_do_item(quantas), TAXA_MEDIDA, AGORA
        )

    def test_EXATAMENTE_no_piso_HA_vencedora(self):
        """O limite conta A PARTIR do piso, e nao depois dele."""
        veredito = self._veredito(_piso())
        assert veredito.estado == dashboard_rotas.ROTA_DECIDIDA
        assert veredito.vencedora == dashboard_rotas.VENCEDORA_NPC
        assert veredito.evidencia.n == _piso()

    def test_UMA_OFERTA_ABAIXO_do_piso_NAO_elege_rota(self):
        veredito = self._veredito(_piso() - 1)
        assert veredito.estado == dashboard_rotas.ROTA_SEM_EVIDENCIA
        assert veredito.vencedora is None
        assert veredito.npc is None and veredito.mercado is None

    def test_com_UMA_oferta_so_nunca_ha_vencedora(self):
        """O caso que o CALC-04 nomeia por extenso: um veredito chutado sobre
        `n=1` seria pior que nenhum veredito."""
        veredito = self._veredito(1)
        assert veredito.vencedora is None
        assert veredito.estado == dashboard_rotas.ROTA_SEM_EVIDENCIA

    def test_a_evidencia_do_veredito_carrega_o_piso_DELE_e_nao_o_do_menor(self):
        """`piso` e um CAMPO da `Evidencia` de proposito.

        Reusar a `Evidencia` que vem dentro do `MenorPedidoVisivel` traria o
        piso do MENOR (um), e a frase de falta na tela diria "1 de 1" ao lado de
        uma linha que se recusou a decidir.
        """
        veredito = self._veredito(_piso() - 1)
        assert veredito.evidencia.piso == _piso()
        assert veredito.evidencia.n == _piso() - 1
        assert veredito.evidencia.faltam == 1
        assert not veredito.evidencia.suficiente

    def test_o_motivo_diz_O_QUE_faltou_em_vez_de_um_nulo_mudo(self):
        """No molde de `MargemDeCraft.motivo`: um `None` mudo obrigaria quem
        desenha a adivinhar entre quatro causas."""
        quebrado = self._veredito(1)
        assert quebrado.motivo

        decidido = self._veredito(_piso())
        assert decidido.motivo == ""


# ===========================================================================
# O ITEM QUE E A PROPRIA ADENA
# ===========================================================================


class TestOItemQueEAPropriaAdena:
    def _modelo_com_adena(self):
        return ModeloDeMercado.de_observacoes(
            _serie(
                CHAVE_DA_SERIE_DA_ADENA,
                "Adena",
                [4500 + 100 * i for i in range(_piso())],
                quantidade=5_000_000,
            )
            + _serie(CHAVE_DO_ITEM, NOME_DO_ITEM, _totais_do_item(_piso()))
        )

    def test_um_item_cujo_nome_resolve_para_a_ADENA_e_RECUSADO(self):
        """Um veredito de adena contra adena seria um numero perfeitamente
        calculado e sem significado nenhum."""
        veredito = dashboard_rotas.veredito_de_uma_rota(
            _item(nome="Adena"), self._modelo_com_adena(), TAXA_MEDIDA, AGORA
        )
        assert veredito.estado == dashboard_rotas.ROTA_E_A_PROPRIA_ADENA
        assert veredito.vencedora is None
        assert veredito.chave == CHAVE_DA_SERIE_DA_ADENA

    def test_CONTROLE_o_MESMO_item_apontando_para_outra_serie_DECIDE(self):
        """Sem este controle, a recusa acima passaria por caminho quebrado.

        O material e o MESMO modelo, com as duas series dentro; so o nome do
        item muda. Se a recusa fosse por ausencia de dado, esta metade
        reprovaria junto.
        """
        veredito = dashboard_rotas.veredito_de_uma_rota(
            _item(nome=NOME_DO_ITEM),
            self._modelo_com_adena(),
            TAXA_MEDIDA,
            AGORA,
        )
        assert veredito.estado == dashboard_rotas.ROTA_DECIDIDA
        assert veredito.vencedora == dashboard_rotas.VENCEDORA_NPC


# ===========================================================================
# A MEDIANA E CONTEXTO, E NUNCA DECISAO
# ===========================================================================


class TestAMedianaEContexto:
    def test_a_mediana_viaja_no_veredito_com_o_PROPRIO_piso(self):
        veredito = dashboard_rotas.veredito_de_uma_rota(
            _item(), _modelo_do_item(), TAXA_MEDIDA, AGORA
        )
        assert veredito.mediana.unitario is not None
        assert (
            veredito.mediana.evidencia.piso
            == mercado_analise.N_MINIMO_PARA_MEDIANA
        )

    def test_CONTROLE_uma_mediana_ABSURDA_nao_move_a_vencedora(self):
        """A PROVA de que ela e contexto, e nao a frase de que ela e.

        As duas series tem o MESMO menor pedido visivel (5900) e a MESMA
        contagem; so a CAUDA muda, e com ela a mediana salta duas ordens de
        grandeza. Se a mediana entrasse na decisao, alguma coisa aqui se
        moveria.
        """
        magra = ModeloDeMercado.de_observacoes(
            _serie(CHAVE_DO_ITEM, NOME_DO_ITEM, _totais_do_item(_piso()))
        )
        gorda = ModeloDeMercado.de_observacoes(
            _serie(
                CHAVE_DO_ITEM,
                NOME_DO_ITEM,
                [5900] + [900_000 + i for i in range(_piso() - 1)],
            )
        )
        um = dashboard_rotas.veredito_de_uma_rota(
            _item(), magra, TAXA_MEDIDA, AGORA
        )
        outro = dashboard_rotas.veredito_de_uma_rota(
            _item(), gorda, TAXA_MEDIDA, AGORA
        )

        assert um.mediana.unitario != outro.mediana.unitario
        assert outro.mediana.unitario > um.mediana.unitario * 100

        assert um.vencedora == outro.vencedora
        assert um.estado == outro.estado
        assert um.diferenca_por_unidade == outro.diferenca_por_unidade
        assert um.diferenca_percentual == outro.diferenca_percentual


# ===========================================================================
# A ORDEM DE PRECEDENCIA, COM OS DOIS ESTADOS NOVOS
# ===========================================================================


class TestAOrdemContinuaFechada:
    def test_os_SEIS_estados_estao_na_tupla_e_na_ordem_de_precedencia(self):
        assert dashboard_rotas.ESTADOS_DA_ROTA == (
            dashboard_rotas.ROTA_NOME_AMBIGUO,
            dashboard_rotas.ROTA_NUNCA_VISTA,
            dashboard_rotas.ROTA_E_A_PROPRIA_ADENA,
            dashboard_rotas.ROTA_SEM_EVIDENCIA,
            dashboard_rotas.ROTA_EMPATADA,
            dashboard_rotas.ROTA_DECIDIDA,
        )

    def test_os_dois_estados_novos_sao_nomes_DISTINTOS_dos_quatro_antigos(self):
        assert len(set(dashboard_rotas.ESTADOS_DA_ROTA)) == 6


# ===========================================================================
# OS QUATRO CRUZAMENTOS: OS DOIS LADOS RESPONDEM AO MESMO PISO
# ===========================================================================


class TestOsDoisLadosRespondemAoMesmoPiso:
    """A ASSIMETRIA QUE ESTE PLANO FECHA, e quais cruzamentos a discriminam.

    Ate o plano 02-01 o piso do veredito guardava so a serie do ITEM. Mas a
    rota do NPC e `preco x taxa`, e a taxa saia de `menor_pedido_visivel` sobre
    a serie da Adena, cujo piso e `N_MINIMO_PARA_MENOR` -- UM. Exigir cinco de
    um lado aceitando um do outro e uma regra que ninguem consegue justificar
    depois.

    **DOIS CRUZAMENTOS DISCRIMINAM contra a implementacao que deixasse a taxa
    no piso do menor: o 2 e o 4.** O **2** e o mais direto -- com a Adena rala
    aquela implementacao aceita a taxa (o piso do menor vale um, e `n>=1`
    passa) e produz um veredito onde este plano exige o estado de BLOCO. O
    **4** reprova pelo mesmo mecanismo com desfecho diferente: aquela
    implementacao tambem passa a taxa, cai no estado de LINHA
    `ROTA_SEM_EVIDENCIA` por causa do item, e o criterio exige o estado de
    BLOCO -- os dois nao sao a mesma resposta.

    OS CRUZAMENTOS 1 E 3 PASSAM SOBRE AS DUAS IMPLEMENTACOES e nao provam nada
    sozinhos -- isso esta escrito de proposito, para ninguem os ler como prova.
    Eles existem como controle: sem eles, uma implementacao que recusasse TUDO
    tambem ficaria verde nos dois que discriminam.
    """

    def test_cruzamento_1_item_farto_e_adena_farta_DECIDE(self, pasta):
        bloco = _bloco(pasta, adena=_piso(), item=_piso())
        assert bloco["estado"] == dashboard_dados.CALCULADORA_COM_ITENS
        assert bloco["itens"][0]["vencedora"] == dashboard_rotas.VENCEDORA_NPC

    def test_cruzamento_2_item_farto_e_adena_RALA_cai_no_estado_de_BLOCO(
        self, pasta
    ):
        """O cruzamento PRIMARIO: a taxa nao sustenta a conversao."""
        bloco = _bloco(pasta, adena=_piso() - 1, item=_piso())
        assert bloco["estado"] == dashboard_dados.CALCULADORA_SEM_TAXA
        assert bloco["itens"] == []

    def test_cruzamento_3_item_RALO_e_adena_farta_cai_no_estado_de_LINHA(
        self, pasta
    ):
        bloco = _bloco(pasta, adena=_piso(), item=_piso() - 1)
        assert bloco["estado"] == dashboard_dados.CALCULADORA_COM_ITENS
        assert bloco["itens"][0]["estado"] == dashboard_rotas.ROTA_SEM_EVIDENCIA
        assert bloco["itens"][0]["vencedora"] is None

    def test_cruzamento_4_os_dois_RALOS_o_BLOCO_vence_a_LINHA(self, pasta):
        """Sem taxa nao ha o que perguntar sobre item nenhum -- e por isso o
        estado de bloco vence, e nao o de linha."""
        bloco = _bloco(pasta, adena=_piso() - 1, item=_piso() - 1)
        assert bloco["estado"] == dashboard_dados.CALCULADORA_SEM_TAXA
        assert bloco["itens"] == []

    def test_a_frase_de_sem_taxa_diz_QUANTAS_ofertas_faltam(self, pasta):
        """A frase antiga afirmava que nao havia leitura NENHUMA da Adena.

        Com o piso novo isso passou a ser falso no caso novo: pode haver quatro
        ofertas e ainda faltar uma. Uma frase que mente sobre o proprio estado
        que ela nomeia e pior que nenhuma frase.
        """
        bloco = _bloco(pasta, adena=_piso() - 1, item=_piso())
        assert bloco["aviso"]
        numeros = re.findall(r"\d+", bloco["aviso"])
        assert str(_piso()) in numeros
        assert str(_piso() - 1) in numeros

    def test_a_nota_da_DECISAO_sobrevive_no_fonte_com_a_medicao(self):
        """A alternativa recusada tem de sobreviver escrita, com o numero.

        O argumento a favor de deixar a taxa no piso do menor era que o menor
        da Adena e um FATO OBSERVADO sobre a serie mais densa do arquivo --
        `adena#` com n=50 contra n=8 do item mais visto, medido em 2026-09-03.
        Ele e verdadeiro sobre o arquivo desta semana e nao e uma regra.
        """
        fonte = Path(dashboard_dados.__file__).read_text(encoding="utf-8")
        assert fonte.count("n=50") >= 1
