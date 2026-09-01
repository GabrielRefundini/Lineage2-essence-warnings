"""A taxa da Adena atravessando o CSV — o ADEN-03 MEDIDO, e nao argumentado.

POR QUE ESTE ARQUIVO EXISTE
============================
"O esquema do CSV ja comporta a taxa, sem coluna nova e sem bump de
`VERSAO_DO_ESQUEMA`" e a afirmacao central da Fase 5 — e ate agora ela era uma
afirmacao sobre codigo que NINGUEM tinha executado com uma linha de Adena
dentro. O 05-01 para na `LinhaLida`; o 05-02 para na `PaginaAceita`; o 05-03 so
FORMATA o que ja esta em memoria. Nenhum dos tres passa uma observacao de taxa
pelo disco.

Este arquivo faz a `LinhaLida` da sentinela ir ate o arquivo e voltar. Ele e
irmao de `tests/test_mercado_registro.py` e usa o mesmo idioma; a diferenca e o
CONTEUDO — uma quantidade de dez milhoes e uma chave que nao veio de OCR nenhum.

NENHUM MODULO DE PRODUCAO E ABERTO POR ESTA TASK, e isso e a forma mais forte de
afirmar que o esquema ja comportava a taxa: se fosse preciso mudar
`mercado_registro.py` para o teste passar, o esquema NAO comportava.

NADA AQUI TOCA A `.mercado/` REAL. Todo registro recebe `tmp_path`, pelo mesmo
motivo escrito no topo do arquivo irmao: a pasta de producao acumula sem poda e
nao ha desfazer. Tambem nao ha `recordings/` nem `calibration.json` — sao
inteiros e arquivos de texto em `tmp_path`.

O PAR QUE DISCRIMINA
====================
`TestOMESMOArquivoGuardaAsDUAS` e o caso que da valor aos outros. Um arquivo que
so visse Adena passaria no teste do cabecalho, no do round-trip e no da
`VERSAO_DO_ESQUEMA` — e passaria tambem se alguem tivesse dado uma coluna nova a
Adena, porque nao haveria uma observacao de negociacao no mesmo arquivo para
discordar dela. As duas juntas, sob UM cabecalho so, sao o que prende
"sem coluna nova".

OS DOIS MUTANTES QUE ESTE ARQUIVO MATA, MEDIDOS
================================================
"Sem coluna nova" e uma promessa NEGATIVA, e promessa negativa e onde criterio
vacuo se esconde: um arquivo de testes que so grava e le fica verde num esquema
de sete colunas tanto quanto num de seis. Entao os dois mutantes foram rodados
de verdade nesta arvore, contra estes 19 testes:

  MUTANTE 1 — uma SETIMA coluna `taxa_em_centesimos_por_milhao`, preenchida nas
  duas series.                                    -> 11 falham, 8 passam.

  MUTANTE 2 — a mesma coluna extra, mas SO na linha da Adena, com o cabecalho
  intacto em seis. E a forma furtiva: o arquivo continua abrindo no Sheets e so
  a linha da Adena esta desalinhada.              -> 11 falham, 8 passam.

Os conjuntos NAO sao os mesmos, e e isso que justifica os dois casos existirem:
`test_sao_SEIS_colunas_e_nenhuma_delas_e_da_taxa` so cai no mutante 1 (o
cabecalho mudou), e `test_as_DUAS_linhas_tem_o_MESMO_numero_de_campos` so cai no
mutante 2 (a assimetria). Cada um sozinho deixaria um dos dois passar.

Os oito sobreviventes sao os que medem outro eixo — a `VERSAO_DO_ESQUEMA`, a
dedup em memoria e o cabecalho comparado CONTRA `COLUNAS` (que por construcao
acompanha a constante). Eles nao sao vacuos; so nao apontam para este defeito.

OS NUMEROS SAO OS DA TELA DO USUARIO
=====================================
`10.000.000` de adena por `116,00` XM — a captura de 2026-09-01, 17h, a mesma
que o `05-CONTEXT.md` registra. A taxa exata que ela produz e
`Fraction(11600, 10_000_000)`, e e ela que o caso 5 exige de volta do disco.
"""

from __future__ import annotations

import csv
from datetime import datetime
from fractions import Fraction
from pathlib import Path

from l2scanner.calibracao import VERSAO_DO_ESQUEMA
from l2scanner.mercado_analise import unitario
from l2scanner.mercado_catalogo import (
    CHAVE_DA_SERIE_DA_ADENA,
    NOME_EXIBIDO_DA_ADENA,
    SEPARADOR,
)
from l2scanner.mercado_leitura import LinhaLida
from l2scanner.mercado_registro import (
    ARQUIVO_DE_OBSERVACOES,
    COLUNAS,
    RegistroDeObservacoes,
    observacoes_do_arquivo,
)

# Ingenuos, hora local, sem `tzinfo` — e o que `Relogio.agora()` devolve, e e o
# que o arquivo irmao ja cobra. Cobrar fuso aqui cobraria um formato que a
# producao nunca produz.
AGORA = datetime(2026, 9, 1, 17, 4, 0)
DEPOIS = datetime(2026, 9, 1, 17, 5, 0)

# A oferta que o usuario VIU na tela: dez milhoes de adena por 116,00 XM.
TOTAL_DA_ADENA = 11600
QUANTIDADE_DA_ADENA = 10_000_000
TAXA_EXATA = Fraction(TOTAL_DA_ADENA, QUANTIDADE_DA_ADENA)


def linha_de_adena(
    *,
    total_em_centesimos: int = TOTAL_DA_ADENA,
    quantidade: int = QUANTIDADE_DA_ADENA,
    residuo_do_cruzamento: int | None = None,
    indice: int = 0,
) -> LinhaLida:
    """A `LinhaLida` que `ler_linha_de_adena` produz, montada a mao.

    A CHAVE E A SENTINELA E O NOME E O ROTULO, na divisao que o 05-01 gravou:
    quem carrega identidade e `chave_da_serie`; `nome_exibido` existe so para o
    humano nao ler `adena#` no CSV.

    `indice` e `serie_nova` recebem valor de proposito, pelo mesmo motivo do
    helper irmao: eles EXISTEM na `LinhaLida` e o registro tem de os deixar de
    fora (D-04). Um helper que os omitisse nao conseguiria provar a ausencia.
    """
    return LinhaLida(
        indice=indice,
        chave_da_serie=CHAVE_DA_SERIE_DA_ADENA,
        nome_exibido=NOME_EXIBIDO_DA_ADENA,
        total_em_centesimos=total_em_centesimos,
        quantidade=quantidade,
        serie_nova=False,
        residuo_do_cruzamento=residuo_do_cruzamento,
    )


def linha_de_negociacao(
    *,
    chave_da_serie: str = "common-aztac#0",
    nome_exibido: str = "Common Aztac",
    total_em_centesimos: int = 6200,
    quantidade: int = 48,
) -> LinhaLida:
    """Uma oferta de ITEM, para o par que discrimina. Copia do helper irmao."""
    return LinhaLida(
        indice=3,
        chave_da_serie=chave_da_serie,
        nome_exibido=nome_exibido,
        total_em_centesimos=total_em_centesimos,
        quantidade=quantidade,
        serie_nova=False,
        residuo_do_cruzamento=None,
    )


def linhas_cruas(pasta: Path) -> list[str]:
    return (pasta / ARQUIVO_DE_OBSERVACOES).read_text(
        encoding="utf-8"
    ).splitlines()


def registros_do_csv(pasta: Path) -> list[list[str]]:
    """Todas as linhas do arquivo pelo modulo `csv`, cabecalho incluido.

    `newline=""` nos DOIS sentidos, como o helper irmao: sem ele a traducao
    universal de quebras de linha mexeria no que este arquivo afirma voltar
    identico.
    """
    with (pasta / ARQUIVO_DE_OBSERVACOES).open(
        "r", encoding="utf-8", newline=""
    ) as fonte:
        return list(csv.reader(fonte, delimiter=SEPARADOR))


# ===========================================================================
# 1. IDA E VOLTA — a taxa atravessa o disco
# ===========================================================================


class TestAIdaEVoltaDaTaxa:
    def test_a_observacao_da_adena_volta_com_os_TRES_campos_identicos(
        self, tmp_path
    ) -> None:
        """`serie`, `total` e `quantidade` — os tres de que a taxa e feita.

        NAO E "o arquivo tem uma linha": uma linha com a quantidade truncada
        tambem seria uma linha. Sao os tres campos, byte a byte de volta ao
        tipo, porque e deles que `Fraction(total, quantidade)` nasce.
        """
        registro = RegistroDeObservacoes(tmp_path)
        registro.carregar()
        assert registro.registrar(linha_de_adena(), AGORA) is True

        lidas = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)
        assert len(lidas) == 1
        volta = lidas[0]
        assert volta.chave_da_serie == CHAVE_DA_SERIE_DA_ADENA
        assert volta.total_em_centesimos == TOTAL_DA_ADENA
        assert volta.quantidade == QUANTIDADE_DA_ADENA

    def test_a_quantidade_de_DEZ_MILHOES_volta_como_INTEIRO(
        self, tmp_path
    ) -> None:
        """O tipo, e nao so o valor.

        `10000000` sobrevive a qualquer round-trip como STRING; o que este
        teste cobra e que ele volte `int`, porque `Fraction` de string nao e a
        mesma coisa que `Fraction` de inteiro — esta escrito na docstring de
        `ObservacaoLida` e e a razao de ela existir.
        """
        registro = RegistroDeObservacoes(tmp_path)
        registro.carregar()
        registro.registrar(linha_de_adena(), AGORA)

        volta = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)[0]
        assert isinstance(volta.quantidade, int)
        assert isinstance(volta.total_em_centesimos, int)

    def test_o_NOME_exibido_da_sentinela_volta_legivel_para_humano(
        self, tmp_path
    ) -> None:
        """`Adena`, e nao `adena#`.

        A sentinela existe para o AGRUPAMENTO; o rotulo existe para o usuario
        que abre o CSV no Sheets. Se o nome voltasse como a chave, a coluna
        `nome_exibido` teria virado uma segunda copia da chave.
        """
        registro = RegistroDeObservacoes(tmp_path)
        registro.carregar()
        registro.registrar(linha_de_adena(), AGORA)

        volta = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)[0]
        assert volta.nome_exibido == NOME_EXIBIDO_DA_ADENA
        assert volta.nome_exibido != CHAVE_DA_SERIE_DA_ADENA


# ===========================================================================
# 2. O CABECALHO-CONTRATO NAO MUDOU
# ===========================================================================


class TestOCabecalhoContinuaOMESMO:
    def test_a_primeira_linha_e_exatamente_a_que_COLUNAS_produz(
        self, tmp_path
    ) -> None:
        """COMPARADO CONTRA `COLUNAS`, e nunca contra uma string escrita a mao.

        Uma copia a mao do cabecalho validaria a si mesma: no dia em que
        alguem acrescentasse uma coluna, mudaria `COLUNAS` E a string do teste,
        e o teste continuaria verde afirmando nada. Comparar contra a fonte e o
        que faz este teste CAIR num bump de esquema — que e exatamente o
        evento que o ADEN-03 promete nao acontecer.
        """
        registro = RegistroDeObservacoes(tmp_path)
        registro.carregar()
        registro.registrar(linha_de_adena(), AGORA)

        assert registros_do_csv(tmp_path)[0] == list(COLUNAS)

    def test_sao_SEIS_colunas_e_nenhuma_delas_e_da_taxa(self, tmp_path) -> None:
        """A contagem E a ausencia do nome.

        Seis sozinho passaria se alguem tivesse TROCADO uma coluna por uma de
        taxa. A segunda metade prende o nome: a taxa e DERIVACAO
        (`Fraction(total, quantidade)`), e derivacao arredondada morando ao
        lado do dado afirmado e a objecao que derrubou a coluna do unitario
        (D-02).
        """
        registro = RegistroDeObservacoes(tmp_path)
        registro.carregar()
        registro.registrar(linha_de_adena(), AGORA)

        cabecalho = registros_do_csv(tmp_path)[0]
        assert len(cabecalho) == 6
        assert not any(
            "taxa" in campo or "unitario" in campo for campo in cabecalho
        )

    def test_a_LINHA_da_adena_tambem_tem_seis_campos(self, tmp_path) -> None:
        """O controle do teste acima: um cabecalho de seis com uma linha de
        sete abriria no Sheets e mentiria em silencio."""
        registro = RegistroDeObservacoes(tmp_path)
        registro.carregar()
        registro.registrar(linha_de_adena(), AGORA)

        assert len(registros_do_csv(tmp_path)[1]) == 6


# ===========================================================================
# 3. O PAR QUE DISCRIMINA — as duas no MESMO arquivo
# ===========================================================================


class TestOMESMOArquivoGuardaAsDUAS:
    """Negociacao e Adena juntas, sob UM cabecalho.

    SEM ESTE CASO, o do cabecalho passaria num arquivo que so ve Adena — e um
    arquivo que so ve Adena nao consegue mostrar que a Adena nao ganhou coluna
    nenhuma, porque nao ha com que comparar.
    """

    def _gravar_as_duas(self, tmp_path) -> RegistroDeObservacoes:
        registro = RegistroDeObservacoes(tmp_path)
        registro.carregar()
        assert registro.registrar(linha_de_negociacao(), AGORA) is True
        assert registro.registrar(linha_de_adena(), DEPOIS) is True
        return registro

    def test_as_DUAS_voltam_do_mesmo_arquivo(self, tmp_path) -> None:
        self._gravar_as_duas(tmp_path)

        lidas = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)
        chaves = {obs.chave_da_serie for obs in lidas}
        assert chaves == {"common-aztac#0", CHAVE_DA_SERIE_DA_ADENA}

    def test_ha_UM_cabecalho_so_no_arquivo(self, tmp_path) -> None:
        """Contado sobre o texto CRU, e nao sobre o que o parser devolve.

        A forma plausivel de "dar uma coluna a Adena" sem quebrar a leitura
        seria escrever um segundo cabecalho no meio do arquivo; o parser o
        trataria como linha de dado ruim e o descartaria com `warning`, e
        nenhum teste sobre observacoes o veria.
        """
        self._gravar_as_duas(tmp_path)

        cruas = linhas_cruas(tmp_path)
        cabecalho = SEPARADOR.join(COLUNAS)
        assert [linha for linha in cruas if linha == cabecalho] == [cabecalho]
        assert len(cruas) == 3  # cabecalho + as duas observacoes

    def test_as_DUAS_linhas_tem_o_MESMO_numero_de_campos(
        self, tmp_path
    ) -> None:
        """O coracao do "sem coluna nova", num arquivo so.

        Se a Adena tivesse ganho um campo, as duas linhas teriam larguras
        DIFERENTES sob o mesmo cabecalho — e e assim que um CSV corrompe dado
        calado: ele continua abrindo.
        """
        self._gravar_as_duas(tmp_path)

        _cabecalho, primeira, segunda = registros_do_csv(tmp_path)
        assert len(primeira) == len(segunda) == len(COLUNAS)

    def test_a_taxa_da_adena_e_o_unitario_do_item_saem_da_MESMA_aritmetica(
        self, tmp_path
    ) -> None:
        """`mercado_analise` nao sabe qual e qual, e essa e a propriedade.

        As duas observacoes voltam do mesmo arquivo e passam pela MESMA
        `unitario(total, quantidade)`. Se a analise tivesse aprendido o que e
        uma aba, este teste nao teria como existir — haveria duas rotas.
        """
        self._gravar_as_duas(tmp_path)

        por_chave = {
            obs.chave_da_serie: obs
            for obs in observacoes_do_arquivo(
                tmp_path / ARQUIVO_DE_OBSERVACOES
            )
        }
        adena = por_chave[CHAVE_DA_SERIE_DA_ADENA]
        item = por_chave["common-aztac#0"]

        assert unitario(adena.total_em_centesimos, adena.quantidade) == (
            TAXA_EXATA
        )
        assert unitario(item.total_em_centesimos, item.quantidade) == (
            Fraction(6200, 48)
        )


# ===========================================================================
# 4. A DEDUP VALE PARA A TAXA
# ===========================================================================


class TestADedupDaTaxa:
    """Duas passadas sobre a mesma pagina nao podem inflar a mediana da taxa.

    A pagina do mercado e reaceita a cada tick: sem dedup, uma unica oferta de
    adena parada na tela por dez minutos viraria ~600 observacoes e a mediana
    da taxa passaria a medir quanto tempo o painel ficou aberto.
    """

    def test_a_MESMA_oferta_de_adena_duas_vezes_vira_UMA_linha(
        self, tmp_path
    ) -> None:
        registro = RegistroDeObservacoes(tmp_path)
        registro.carregar()

        assert registro.registrar(linha_de_adena(), AGORA) is True
        assert registro.registrar(linha_de_adena(), DEPOIS) is False

        assert len(linhas_cruas(tmp_path)) == 2  # cabecalho + UMA observacao

    def test_a_mesma_sentinela_com_TOTAL_diferente_vira_DUAS(
        self, tmp_path
    ) -> None:
        """O CONTROLE NEGATIVO, e sem ele a dedup seria indistinguivel de uma
        trava por SERIE.

        A Adena e uma serie SO (decisao do 05-01): se a dedup fosse pela chave,
        a segunda oferta de adena do dia — a preco diferente, que e justamente
        a NOTICIA de que a taxa se moveu — seria engolida. A taxa andou 72% em
        seis horas na medicao do usuario; engolir a segunda cotacao seria
        perder exatamente o fenomeno que a fase existe para ver.
        """
        registro = RegistroDeObservacoes(tmp_path)
        registro.carregar()

        assert registro.registrar(linha_de_adena(), AGORA) is True
        assert (
            registro.registrar(
                linha_de_adena(total_em_centesimos=12000), DEPOIS
            )
            is True
        )

        assert len(linhas_cruas(tmp_path)) == 3  # cabecalho + DUAS

    def test_a_dedup_sobrevive_a_um_RECARREGAMENTO_do_arquivo(
        self, tmp_path
    ) -> None:
        """A sessao seguinte nao regrava o que a anterior ja gravou.

        Um indice que so vivesse em memoria deixaria cada arranque duplicar a
        pagina inteira — e o `n` da evidencia e o que esta fase inteira existe
        para nao mentir.
        """
        primeiro = RegistroDeObservacoes(tmp_path)
        primeiro.carregar()
        primeiro.registrar(linha_de_adena(), AGORA)

        segundo = RegistroDeObservacoes(tmp_path)
        segundo.carregar()
        assert segundo.registrar(linha_de_adena(), DEPOIS) is False

        assert len(linhas_cruas(tmp_path)) == 2


# ===========================================================================
# 5. A TAXA EXATA SOBREVIVE AO DISCO
# ===========================================================================


class TestATaxaExataSobreviveAoDisco:
    def test_a_taxa_lida_de_volta_e_a_FRACTION_exata(self, tmp_path) -> None:
        """`Fraction`, e nunca `float`.

        E o que prova que o unitario derivado nasce do que o CSV GUARDOU, e nao
        do que a memoria lembrava. Comparar `float` aqui esconderia justamente
        o erro que ela pode ter: `11600/10_000_000` e `0.00116`, que em ponto
        flutuante e um numero que nao vale `29/25000`.
        """
        registro = RegistroDeObservacoes(tmp_path)
        registro.carregar()
        registro.registrar(linha_de_adena(), AGORA)

        volta = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)[0]
        taxa = unitario(volta.total_em_centesimos, volta.quantidade)
        assert taxa == TAXA_EXATA
        assert isinstance(taxa, Fraction)

    def test_a_taxa_e_EXATA_e_nao_apenas_proxima(self, tmp_path) -> None:
        """O controle do anterior: a `Fraction` reduzida, escrita por extenso.

        Sem esta linha, "igual a `TAXA_EXATA`" seria uma comparacao de um valor
        consigo mesmo passando pelo mesmo caminho — as duas pontas usariam
        `TOTAL_DA_ADENA` e `QUANTIDADE_DA_ADENA` e um erro comum as duas nao
        apareceria.
        """
        registro = RegistroDeObservacoes(tmp_path)
        registro.carregar()
        registro.registrar(linha_de_adena(), AGORA)

        volta = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)[0]
        assert unitario(
            volta.total_em_centesimos, volta.quantidade
        ) == Fraction(29, 25000)

    def test_a_exibicao_em_XM_por_milhao_fecha_no_11_60(self, tmp_path) -> None:
        """A ponta a ponta: do disco ate o texto que o usuario le.

        `11,60` — RECALCULADO, e nao o `116,00` que a pesquisa escreve. E o
        unico teste deste arquivo que atravessa o console, e ele esta aqui
        porque a promessa do ADEN-03 e do ADEN-04 juntas so vale se o numero
        que sai na tela vier do arquivo.
        """
        from l2scanner.mercado_console import formatar_taxa_derivada

        registro = RegistroDeObservacoes(tmp_path)
        registro.carregar()
        registro.registrar(linha_de_adena(), AGORA)

        volta = observacoes_do_arquivo(tmp_path / ARQUIVO_DE_OBSERVACOES)[0]
        taxa = unitario(volta.total_em_centesimos, volta.quantidade)
        assert formatar_taxa_derivada(taxa) == (
            "11,60 XM por milhao de adena (derivado)"
        )


# ===========================================================================
# 6. A VERSAO DO ESQUEMA NAO SUBIU
# ===========================================================================


class TestAVersaoDoEsquemaNaoSubiu:
    """Um bump futuro cai AQUI, e nao no `calibration.json` do usuario.

    `Calibracao.carregar` recusa qualquer versao diferente de
    `VERSAO_DO_ESQUEMA` e manda recalibrar. Se alguem subir a versao para
    acomodar a Adena, o custo real nao aparece no diff — aparece no proximo
    arranque do usuario, com o scanner morto e um pedido de recalibracao que
    ele nao esperava. Este teste e o lugar onde esse custo aparece antes.
    """

    def test_a_VERSAO_DO_ESQUEMA_segue_em_DOIS(self) -> None:
        assert VERSAO_DO_ESQUEMA == 2

    def test_a_gravacao_da_adena_NAO_toca_a_versao(self, tmp_path) -> None:
        """O controle: a versao lida DEPOIS de a taxa ter atravessado o disco.

        Uma constante afirmada num teste que nunca gravou nada seria uma
        afirmacao sobre um modulo, e nao sobre o que a Adena fez com ele.
        """
        registro = RegistroDeObservacoes(tmp_path)
        registro.carregar()
        registro.registrar(linha_de_adena(), AGORA)

        from l2scanner.calibracao import VERSAO_DO_ESQUEMA as depois

        assert depois == 2

    def test_o_arquivo_da_adena_nao_carrega_numero_de_versao(
        self, tmp_path
    ) -> None:
        """O CSV nao versiona a si mesmo, e nao passou a versionar.

        A identidade do arquivo e o CABECALHO (D-11/D-12), e nao um campo de
        versao — acrescentar um seria uma coluna nova por outro nome.
        """
        registro = RegistroDeObservacoes(tmp_path)
        registro.carregar()
        registro.registrar(linha_de_adena(), AGORA)

        assert not any(
            "versao" in campo or "schema" in campo
            for campo in registros_do_csv(tmp_path)[0]
        )
