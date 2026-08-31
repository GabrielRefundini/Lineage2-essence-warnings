"""A leitura tipada do `observacoes.csv` e a estatistica honesta sobre ela.

NADA AQUI TOCA A `.mercado/` REAL, e nada aqui monta frame. Os arquivos nascem
em `tmp_path` e a analise recebe listas montadas a mao — e o que permite a suite
inteira rodar no Python global, sem WinRT e sem material gravado.

O FATO QUE GOVERNA TODOS ESTES TESTES
======================================
Uma linha do CSV NAO e "o preco as 14:32": e "esta oferta especifica — este
item, este total, esta quantidade — foi vista pela PRIMEIRA vez as 14:32". A
chave de dedup da Fase 3 e `(chave_da_serie, total_em_centesimos, quantidade)`,
SEM tempo (`mercado_registro.py:149-166`). Logo nao existe serie temporal de
preco: existe uma sequencia de OFERTAS DISTINTAS ordenada pela primeira vez que
cada uma apareceu. Toda a aritmetica exercitada aqui respeita isso.
"""

from __future__ import annotations

import ast
import inspect
import logging
import statistics
from datetime import datetime, timedelta
from fractions import Fraction
from pathlib import Path

import pytest

from l2scanner import mercado_analise as analise
from l2scanner.mercado_catalogo import SEPARADOR
from l2scanner.mercado_registro import (
    ARQUIVO_DE_OBSERVACOES,
    COLUNAS,
    ContratoDoArquivoQuebrado,
    ObservacaoLida,
    observacoes_do_arquivo,
)

LOGGER = "l2scanner.mercado_registro"

# Ingenuos, hora local, sem `tzinfo` — e o que `Relogio.agora()` devolve
# (`l2scanner/relogio.py:156-163`) e o que `campos_da_observacao` escreve com
# `.isoformat()`. Cobrar fuso aqui cobraria um formato que a producao nunca
# produz.
AGORA = datetime(2026, 8, 30, 21, 15, 0)


# ===========================================================================
# TASK 1 — `observacoes_do_arquivo`, pelo portao de contrato que ja existe
# ===========================================================================


def _linha_crua(
    *,
    chave: str = "common-aztac#0",
    nome: str = "Common Aztac",
    carimbo: datetime = AGORA,
    total: int = 6200,
    quantidade: int = 48,
    residuo: str = "0",
) -> str:
    return SEPARADOR.join(
        (chave, nome, carimbo.isoformat(), str(total), str(quantidade), residuo)
    )


def _fabricar(pasta: Path, *linhas: str, terminador: str = "\r\n") -> Path:
    """Escreve um CSV com cabecalho e as linhas dadas. Bytes exatos.

    O terminador e `\\r\\n` porque e o que `csv.writer` com `newline=""` emite
    no Windows, que e o arquivo que a producao produz.
    """
    alvo = pasta / ARQUIVO_DE_OBSERVACOES
    corpo = terminador.join((SEPARADOR.join(COLUNAS), *linhas)) + terminador
    alvo.write_bytes(corpo.encode("utf-8"))
    return alvo


class TestAsLinhasParseadasVoltamTIPADAS:
    """Tres linhas boas viram tres registros, com os tipos que a analise usa."""

    def test_tres_linhas_boas_devolvem_TRES_registros(self, tmp_path):
        _fabricar(
            tmp_path,
            _linha_crua(total=6200, quantidade=48),
            _linha_crua(total=4500, quantidade=100),
            _linha_crua(total=1000, quantidade=1),
        )
        itens = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)
        assert len(itens) == 3

    def test_os_numeros_voltam_INTEIROS_e_o_carimbo_volta_DATETIME(self, tmp_path):
        """O tipo e o contrato: a analise faz `Fraction(total, quantidade)`, e
        `Fraction` de string nao e a mesma coisa que `Fraction` de inteiro."""
        _fabricar(tmp_path, _linha_crua())
        itens = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)
        assert type(itens[0].total_em_centesimos) is int
        assert type(itens[0].quantidade) is int
        assert type(itens[0].primeira_vez) is datetime

    def test_os_campos_de_texto_voltam_INTEIROS_de_conteudo(self, tmp_path):
        _fabricar(tmp_path, _linha_crua(chave="k#1", nome="Common Aztac"))
        (item,) = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)
        assert item.chave_da_serie == "k#1"
        assert item.nome_exibido == "Common Aztac"
        assert item.primeira_vez == AGORA

    def test_o_registro_e_FROZEN(self, tmp_path):
        """Ninguem reescreve uma observacao lida do disco depois de le-la."""
        _fabricar(tmp_path, _linha_crua())
        (item,) = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)
        with pytest.raises(Exception):
            item.total_em_centesimos = 1  # type: ignore[misc]


class TestOPortaoDeContratoEOMESMO:
    """Uma verdade so sobre o que o arquivo e — nunca um parser novo.

    Duas implementacoes divergentes de leitura do mesmo arquivo reintroduziriam
    exatamente a truncagem parseavel que a Fase 3 gastou um plano inteiro para
    pegar: `80` virando `8` passa na contagem de campos e na validacao por tipo,
    e SO o terminador a pega.
    """

    def test_sem_quebra_de_linha_final_LEVANTA(self, tmp_path):
        alvo = _fabricar(tmp_path, _linha_crua())
        bruto = alvo.read_bytes()
        assert bruto.endswith(b"\n")
        alvo.write_bytes(bruto[:-1])
        with pytest.raises(ContratoDoArquivoQuebrado):
            observacoes_do_arquivo(alvo)

    def test_o_ultimo_byte_cortado_deixa_seis_campos_PARSEAVEIS_e_ainda_LEVANTA(
        self, tmp_path
    ):
        """O corte medido: `...;48;80\\r\\n` truncado vira `...;48;8` — seis
        campos, todos validos, residuo de 8 onde o disco dizia 80."""
        alvo = _fabricar(tmp_path, _linha_crua(residuo="80"))
        alvo.write_bytes(alvo.read_bytes()[:-3])  # tira `0\r\n`
        with pytest.raises(ContratoDoArquivoQuebrado):
            observacoes_do_arquivo(alvo)

    def test_cabecalho_divergente_LEVANTA(self, tmp_path):
        alvo = _fabricar(tmp_path, _linha_crua())
        texto = alvo.read_text(encoding="utf-8")
        trocado = texto.replace("total_em_centesimos", "total", 1)
        alvo.write_bytes(trocado.encode("utf-8"))
        with pytest.raises(ContratoDoArquivoQuebrado):
            observacoes_do_arquivo(alvo)

    def test_arquivo_AUSENTE_devolve_lista_vazia_sem_levantar(self, tmp_path):
        """A `.mercado/` nasce vazia e a analise tem de dizer 'sem evidencia',
        nao explodir."""
        assert observacoes_do_arquivo(tmp_path / "nao-existe.csv") == []

    def test_a_leitura_NAO_CRIA_o_arquivo_ausente(self, tmp_path):
        alvo = tmp_path / "nao-existe.csv"
        observacoes_do_arquivo(alvo)
        assert not alvo.exists()

    def test_arquivo_de_ZERO_BYTES_devolve_lista_vazia(self, tmp_path):
        alvo = tmp_path / ARQUIVO_DE_OBSERVACOES
        alvo.write_bytes(b"")
        assert observacoes_do_arquivo(alvo) == []

    def test_so_o_cabecalho_devolve_lista_vazia(self, tmp_path):
        alvo = _fabricar(tmp_path)
        assert observacoes_do_arquivo(alvo) == []


class TestUmaLinhaRuimCaiSOZINHA:
    """Passado o portao, linha ruim nunca condena o arquivo (D-14)."""

    def test_contagem_de_campos_errada_e_DESCARTADA_e_as_demais_continuam(
        self, tmp_path, caplog
    ):
        alvo = _fabricar(
            tmp_path,
            _linha_crua(total=6200),
            "so;tres;campos",
            _linha_crua(total=4500),
        )
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            itens = observacoes_do_arquivo(alvo)
        assert len(itens) == 2
        assert [i.total_em_centesimos for i in itens] == [6200, 4500]

    def test_o_aviso_NOMEIA_o_numero_da_linha(self, tmp_path, caplog):
        """A forense deste projeto acontece depois do farm, com o log na mao:
        'linha descartada' sem o numero nao conserta nada."""
        alvo = _fabricar(
            tmp_path,
            _linha_crua(),
            "so;tres;campos",
        )
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            observacoes_do_arquivo(alvo)
        avisos = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert avisos, "a linha ruim tem de produzir aviso"
        assert any("3" in r.getMessage() for r in avisos), [
            r.getMessage() for r in avisos
        ]

    def test_carimbo_que_nao_e_ISO_tambem_CAI_sozinho(self, tmp_path, caplog):
        alvo = _fabricar(
            tmp_path,
            SEPARADOR.join(("k#1", "Nome", "ontem de tarde", "6200", "48", "")),
            _linha_crua(),
        )
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            itens = observacoes_do_arquivo(alvo)
        assert len(itens) == 1


class TestOResiduoQueNaoColapsa:
    """`None` e `0` sao fatos DIFERENTES e nao podem colapsar (D-01).

    `None` e "alguma das tres celulas nao leu, entao nao houve conferencia" e
    `0` e "conferi a aritmetica e ela bateu na casa do centesimo".
    """

    def test_vazio_volta_None_e_zero_volta_zero(self, tmp_path):
        alvo = _fabricar(
            tmp_path,
            _linha_crua(total=6200, residuo=""),
            _linha_crua(total=4500, residuo="0"),
        )
        vazio, zero = observacoes_do_arquivo(alvo)
        assert vazio.residuo_do_cruzamento is None
        assert zero.residuo_do_cruzamento == 0

    def test_um_residuo_medido_sobrevive_a_leitura(self, tmp_path):
        alvo = _fabricar(tmp_path, _linha_crua(residuo="80"))
        (item,) = observacoes_do_arquivo(alvo)
        assert item.residuo_do_cruzamento == 80


class TestAExtracaoEREFACTOR_PURO:
    """Os metodos do registro e a leitura nova chamam a MESMA funcao."""

    def test_o_registro_delega_o_terminador_a_funcao_de_modulo(self):
        import inspect

        from l2scanner import mercado_registro

        fonte = inspect.getsource(
            mercado_registro.RegistroDeObservacoes._conferir_o_terminador
        )
        assert "conferir_o_terminador(" in fonte

    def test_o_registro_delega_o_cabecalho_a_funcao_de_modulo(self):
        import inspect

        from l2scanner import mercado_registro

        fonte = inspect.getsource(
            mercado_registro.RegistroDeObservacoes._conferir_o_cabecalho
        )
        assert "conferir_o_cabecalho(" in fonte

    def test_a_leitura_nova_NAO_abre_o_arquivo_para_escrita(self):
        import inspect

        from l2scanner import mercado_registro

        fonte = inspect.getsource(mercado_registro.observacoes_do_arquivo)
        assert '"w"' not in fonte and '"a"' not in fonte
        assert "mkdir" not in fonte

    def test_ObservacaoLida_carrega_exatamente_as_COLUNAS(self):
        import dataclasses

        campos = tuple(f.name for f in dataclasses.fields(ObservacaoLida))
        assert campos == COLUNAS


# ===========================================================================
# TASK 2 — o unitario exato, o menor pedido visivel, a mediana e as recencias
# ===========================================================================


def _oferta(
    *,
    chave: str = "common-aztac#0",
    nome: str = "Common Aztac",
    carimbo: datetime = AGORA,
    total: int = 6200,
    quantidade: int = 48,
    residuo: int | None = 0,
) -> ObservacaoLida:
    """Uma oferta montada a mao — a analise nunca precisa de disco nem de frame."""
    return ObservacaoLida(
        chave_da_serie=chave,
        nome_exibido=nome,
        primeira_vez=carimbo,
        total_em_centesimos=total,
        quantidade=quantidade,
        residuo_do_cruzamento=residuo,
    )


class TestOUnitarioEEXATO:
    """`Fraction`, nunca `float` — o arredondamento so acontece ao formatar.

    O D-02 recusou GUARDAR o unitario porque o que o jogo exibe e derivacao
    arredondada: `40,00` por 48 unidades vira `0,83`, e `0,83 x 48 = 39,84`, um
    numero que nunca existiu. Derivar na hora de comparar e outra coisa — desde
    que nao se arredonde ANTES de comparar.
    """

    def test_o_unitario_e_Fraction_e_nao_float(self):
        assert isinstance(analise.unitario(4000, 48), Fraction)
        assert not isinstance(analise.unitario(4000, 48), float)

    def test_o_unitario_multiplicado_de_volta_devolve_o_TOTAL_exato(self):
        """A prova de que nao houve arredondamento: `0,83 x 48 = 39,84` e o
        numero que nunca existiu; `Fraction(4000, 48) * 48` e `4000`."""
        assert analise.unitario(4000, 48) * 48 == 4000

    def test_quantidade_zero_ou_negativa_LEVANTA_com_o_motivo_em_texto(self):
        """O CSV e editado a mao no Sheets: `quantidade` zero e entrada
        possivel, e uma divisao por zero derrubaria o console inteiro."""
        with pytest.raises(ValueError):
            analise.unitario(4000, 0)
        with pytest.raises(ValueError):
            analise.unitario(4000, -1)


class TestOMenorPedidoVisivel:
    """A oferta de menor UNITARIO, com o carimbo DELA e os dois numeros juntos."""

    def test_a_escolhida_e_a_de_menor_unitario_e_carrega_a_quantidade(self):
        """O par literal do criterio do plano: `(6200, 48)` e `(4500, 100)`."""
        ofertas = [_oferta(total=6200, quantidade=48), _oferta(total=4500, quantidade=100)]
        r = analise.menor_pedido_visivel(ofertas)
        assert r.unitario == min(
            analise.unitario(o.total_em_centesimos, o.quantidade) for o in ofertas
        )
        assert r.total_em_centesimos == 4500
        assert r.quantidade == 100

    def test_o_MENOR_TOTAL_nao_e_o_menor_pedido_visivel(self):
        """O par que DISCRIMINA as duas ordens, e sem ele o criterio do plano
        nao provaria nada: `(1000, 1)` tem o menor TOTAL e o MAIOR unitario."""
        barato_por_unidade = _oferta(total=4500, quantidade=100)  # 45 por unidade
        total_menor = _oferta(total=1000, quantidade=1)  # 1000 por unidade
        r = analise.menor_pedido_visivel([total_menor, barato_por_unidade])
        assert r.total_em_centesimos == 4500
        assert r.quantidade == 100

    def test_o_carimbo_e_o_DAQUELA_oferta_e_nao_o_da_serie(self):
        """Um minimo de terca-feira ao lado da recencia de hoje e a mentira
        plausivel que este projeto inteiro combate."""
        antiga = datetime(2026, 8, 25, 10, 0, 0)
        nova = datetime(2026, 8, 30, 22, 0, 0)
        ofertas = [
            _oferta(total=4500, quantidade=100, carimbo=antiga),  # a mais barata
            _oferta(total=9900, quantidade=100, carimbo=nova),
        ]
        r = analise.menor_pedido_visivel(ofertas)
        assert r.primeira_vez == antiga
        assert r.primeira_vez != analise.recencia_do_preco(ofertas)

    def test_com_n_igual_a_UM_o_menor_EXISTE_e_vem_rotulado_com_n_1(self):
        """`n=1` e um FATO OBSERVADO, nao uma estimativa. A honestidade esta no
        rotulo, e o rotulo e obrigatorio."""
        r = analise.menor_pedido_visivel([_oferta()])
        assert r.evidencia.suficiente
        assert r.evidencia.n == 1

    def test_sem_oferta_nenhuma_o_resultado_diz_o_que_FALTA(self):
        r = analise.menor_pedido_visivel([])
        assert not r.evidencia.suficiente
        assert r.evidencia.n == 0
        assert r.evidencia.piso == analise.N_MINIMO_PARA_MENOR
        assert r.evidencia.faltam == 1
        assert r.total_em_centesimos is None


class TestAMedianaDEVOLVE_VALOR_OBSERVADO:
    """A PROVA CENTRAL: `median_low` contra `median`, com `n` par e acima do piso."""

    def _seis_unitarios_distintos(self) -> list[ObservacaoLida]:
        # quantidade fixa em 100 e totais em progressao: unitarios 10..60.
        return [
            _oferta(total=total, quantidade=100)
            for total in (1000, 2000, 3000, 4000, 5000, 6000)
        ]

    def test_n_SEIS_par_e_acima_do_piso_devolve_valor_que_EXISTIU_na_tela(self):
        """SEIS e a unica contagem que prova a escolha: PAR — onde
        `statistics.median` inventa a media dos dois do meio, um valor que nunca
        esteve na lista — e ACIMA do piso de cinco, onde a funcao pode devolver
        numero. As duas assercoes juntas sao a prova; nenhuma delas sozinha e.
        """
        ofertas = self._seis_unitarios_distintos()
        unitarios = [
            analise.unitario(o.total_em_centesimos, o.quantidade) for o in ofertas
        ]
        assert len(unitarios) == 6
        assert len(set(unitarios)) == 6

        r = analise.mediana_dos_unitarios(ofertas)

        assert r.unitario in unitarios
        assert r.unitario != statistics.median(unitarios)

    def test_a_mediana_carrega_o_n_da_evidencia(self):
        r = analise.mediana_dos_unitarios(self._seis_unitarios_distintos())
        assert r.evidencia.n == 6
        assert r.evidencia.suficiente

    def test_n_QUATRO_esta_abaixo_do_piso_e_informa_CINCO(self):
        """O UNICO teste com `n=4` neste arquivo, e ele e sobre o PISO — nao
        sobre a mediana. Com `N_MINIMO_PARA_MEDIANA = 5`, cobrar um VALOR de
        mediana para `n=4` seria cobrar o impossivel."""
        ofertas = [
            _oferta(total=total, quantidade=100) for total in (1000, 2000, 3000, 4000)
        ]
        r = analise.mediana_dos_unitarios(ofertas)
        assert not r.evidencia.suficiente
        assert r.evidencia.n == 4
        assert r.evidencia.piso == 5
        assert r.evidencia.faltam == 1
        assert r.unitario is None

    def test_a_mediana_de_lista_vazia_nao_LEVANTA(self):
        """`statistics.median([])` levanta `StatisticsError`. O piso pega antes."""
        r = analise.mediana_dos_unitarios([])
        assert not r.evidencia.suficiente
        assert r.unitario is None


class TestAsDUAS_RECENCIAS:
    """A do PRECO e `max(primeira_vez)`. A outra e do catalogo, e nao e esta."""

    def test_a_recencia_do_preco_e_o_MAXIMO_dos_carimbos(self):
        antiga = datetime(2026, 8, 25, 10, 0, 0)
        nova = datetime(2026, 8, 30, 22, 0, 0)
        meio = datetime(2026, 8, 28, 12, 0, 0)
        ofertas = [
            _oferta(total=1000, carimbo=antiga),
            _oferta(total=2000, carimbo=nova),
            _oferta(total=3000, carimbo=meio),
        ]
        assert analise.recencia_do_preco(ofertas) == nova

    def test_sem_oferta_nenhuma_a_recencia_e_None(self):
        assert analise.recencia_do_preco([]) is None

    def test_a_docstring_NOMEIA_a_outra_recencia_para_ninguem_confundir(self):
        """O `ultima_vez` do catalogo diz quando o ITEM foi visto pela ultima
        vez em qualquer preco, e pode ser de agora mesmo sobre um preco de tres
        dias atras. Trocar um pelo outro e mentir com cara de numero."""
        doc = analise.recencia_do_preco.__doc__ or ""
        assert "ultima_vez" in doc
        assert "catalogo" in doc.lower()


class TestOsPisosSaoESCOLHA_E_NAO_MEDICAO:
    """Nenhum piso desse tipo foi medido neste projeto, e o fonte diz isso."""

    def test_os_valores_travados(self):
        assert analise.N_MINIMO_PARA_MENOR == 1
        assert analise.N_MINIMO_PARA_MEDIANA == 5

    def test_o_modulo_DECLARA_por_escrito_que_os_pisos_sao_escolha(self):
        doc = (analise.__doc__ or "").lower()
        assert "escolha" in doc or "escolhid" in doc

    def test_o_fonte_diz_que_os_numeros_MEDIDOS_do_projeto_sao_sobre_a_LEITURA(self):
        """151 paginas lidas, 189 perdidas, 39 series, piso de 7 posicoes: sao
        medicoes sobre a LEITURA e nao servem de substituto para estes pisos."""
        fonte = inspect.getsource(analise)
        assert "151" in fonte and "189" in fonte

    def test_o_fonte_explica_por_que_os_pisos_NAO_moram_no_calibration_json(self):
        fonte = inspect.getsource(analise).lower()
        assert "calibration.json" in fonte


class TestOModuloDeAnaliseEPURO:
    """Sem disco, sem relogio, sem impressao — a suite roda no Python global."""

    def test_nao_traz_o_modulo_de_sistema_nem_abre_arquivo_nem_imprime(self):
        fonte = inspect.getsource(analise)
        assert "import os" not in fonte
        assert "open(" not in fonte
        assert "print(" not in fonte

    def test_o_carimbo_nunca_vem_de_dentro(self):
        """A mesma disciplina do D-16 que `campos_da_observacao` ja segue: o
        relogio entra por parametro, nunca de dentro do modulo."""
        chamadas = {
            no.func.attr
            for no in ast.walk(ast.parse(inspect.getsource(analise)))
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
        }
        assert "now" not in chamadas
        assert "today" not in chamadas


# ===========================================================================
# TASK 3 — a tendencia sobre o ORDINAL, com o tamanho da janela junto (ANAL-03)
# ===========================================================================


def _dez_em_queda() -> list[ObservacaoLida]:
    """Dez ofertas com carimbos a MICROSSEGUNDOS e unitarios em queda monotona.

    Os carimbos imitam o que a producao produz: `gravar_as_paginas` chama
    `relogio.agora()` POR LINHA (`tools/gerar_observacoes_do_censo.py:215`),
    entao as dez linhas de uma mesma pagina distam microssegundos.
    """
    base = datetime(2026, 8, 30, 21, 15, 0)
    return [
        _oferta(
            total=(100 - 5 * i) * 100,  # unitarios 100, 95, ... 55
            quantidade=100,
            carimbo=base + timedelta(microseconds=37 * i),
        )
        for i in range(10)
    ]


class TestATendenciaRodaSobreOORDINAL:
    """O carimbo nao pode ser o eixo `x`, e este e o coracao da task."""

    def test_dez_ofertas_em_queda_dao_variacao_NEGATIVA_e_PLAUSIVEL(self):
        r = analise.tendencia(_dez_em_queda())
        assert r.evidencia.suficiente
        assert r.variacao_percentual < 0
        assert abs(r.variacao_percentual) < 100

    def test_o_eixo_do_CARIMBO_devolveria_numero_errado_SEM_LEVANTAR(self):
        """A prova de que o ordinal nao e detalhe de estilo.

        Sobre o MESMO conjunto, uma regressao com o carimbo no eixo `x` NAO
        levanta `StatisticsError` — tecnicamente `x` varia — e devolve uma
        inclinacao de magnitude absurda por segundo, que ao virar percentual
        sobre a janela apaga a queda inteira. Numero plausivel e errado e o modo
        de falha que este projeto inteiro combate.

        O teste compara os dois resultados com o INTERVALO ACEITAVEL, e nao com
        um numero escolhido a mao: o do ordinal cai dentro, o do carimbo nao.
        """
        ofertas = _dez_em_queda()
        unitarios = [
            float(analise.unitario(o.total_em_centesimos, o.quantidade))
            for o in ofertas
        ]
        carimbos = [o.primeira_vez.timestamp() for o in ofertas]

        pelo_carimbo = statistics.linear_regression(carimbos, unitarios)
        # Nao levanta, e e exatamente esse o perigo.
        assert abs(pelo_carimbo.slope) > 1e4, pelo_carimbo

        variacao_pelo_carimbo = (
            pelo_carimbo.slope * (len(ofertas) - 1) / pelo_carimbo.intercept * 100
        )
        # A queda real e de dezenas por cento; o carimbo devolve praticamente
        # zero — ele APAGA a queda em vez de mede-la.
        assert abs(variacao_pelo_carimbo) < 1

        r = analise.tendencia(ofertas)
        assert r.variacao_percentual < -1
        assert abs(r.variacao_percentual) < 100

    def test_o_fonte_da_funcao_NOMEIA_o_ordinal(self):
        fonte = inspect.getsource(analise.tendencia).lower()
        assert "ordinal" in fonte

    def test_a_ordem_e_por_primeira_vez_e_nao_a_do_arquivo(self):
        """O ordinal e `1..n` sobre as ofertas ordenadas por `primeira_vez` —
        uma lista embaralhada tem de dar o mesmo resultado."""
        ofertas = _dez_em_queda()
        embaralhadas = [ofertas[i] for i in (4, 0, 9, 2, 7, 1, 8, 3, 6, 5)]
        assert (
            analise.tendencia(embaralhadas).variacao_percentual
            == analise.tendencia(ofertas).variacao_percentual
        )


class TestOPisoDaTendencia:
    """Uma reta sobre tres pontos tem a mesma cara de uma sobre trezentos."""

    def test_o_valor_travado(self):
        assert analise.N_MINIMO_PARA_TENDENCIA == 8

    def test_com_SETE_ofertas_o_resultado_diz_o_que_FALTA_e_informa_OITO(self):
        sete = _dez_em_queda()[:7]
        r = analise.tendencia(sete)
        assert not r.evidencia.suficiente
        assert r.evidencia.n == 7
        assert r.evidencia.piso == 8
        assert r.evidencia.faltam == 1
        assert r.variacao_percentual is None

    def test_lista_vazia_nao_LEVANTA(self):
        """`linear_regression` de menos de dois pontos levanta
        `StatisticsError`. O piso pega muito antes."""
        r = analise.tendencia([])
        assert not r.evidencia.suficiente
        assert r.variacao_percentual is None


class TestATendenciaSemQueda:
    """Serie parada e serie sem intercepto: nenhuma das duas pode levantar."""

    def test_unitarios_todos_IGUAIS_dao_variacao_ZERO(self):
        base = datetime(2026, 8, 30, 21, 15, 0)
        iguais = [
            _oferta(
                total=6200,
                quantidade=100,
                carimbo=base + timedelta(microseconds=41 * i),
            )
            for i in range(10)
        ]
        r = analise.tendencia(iguais)
        assert r.evidencia.suficiente
        assert r.variacao_percentual == 0

    def test_intercepto_ZERO_nao_estoura_em_divisao_por_zero(self):
        """Totais zerados (o CSV e editado a mao) fariam `slope/intercept` ser
        `0/0`. O caso vira 'sem tendencia reportavel', com o motivo nomeado."""
        base = datetime(2026, 8, 30, 21, 15, 0)
        zerados = [
            _oferta(
                total=0,
                quantidade=100,
                carimbo=base + timedelta(microseconds=41 * i),
            )
            for i in range(10)
        ]
        r = analise.tendencia(zerados)
        assert r.variacao_percentual is None
        assert r.motivo_da_ausencia


class TestOTamanhoDaJanelaVIAJA_JUNTO:
    """Sem o `n`, a tendencia de 3 pontos parece a de 300 (ANAL-03)."""

    def test_o_n_da_janela_e_o_numero_de_ofertas_passadas(self):
        ofertas = _dez_em_queda()
        assert analise.tendencia(ofertas).evidencia.n == len(ofertas)

    def test_o_texto_usa_a_palavra_que_designa_OFERTAS_DISTINTAS(self):
        """Ela e o que impede o usuario de ler a reta como uma variacao ao longo
        de horas. A palavra que designa observacoes ao longo do tempo esta
        PROIBIDA: nao existe serie temporal de preco neste CSV."""
        texto = analise.descrever_a_tendencia(analise.tendencia(_dez_em_queda()))
        assert "ofertas distintas" in texto
        assert "observac" not in texto.lower()

    def test_o_texto_carrega_o_n_mesmo_ABAIXO_do_piso(self):
        texto = analise.descrever_a_tendencia(analise.tendencia(_dez_em_queda()[:7]))
        assert "7" in texto
        assert "8" in texto
        assert "ofertas distintas" in texto
        assert "observac" not in texto.lower()

    def test_o_texto_do_resultado_bom_carrega_o_n(self):
        texto = analise.descrever_a_tendencia(analise.tendencia(_dez_em_queda()))
        assert "10" in texto
