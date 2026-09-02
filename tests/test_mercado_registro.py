"""O registro de observacoes em `.mercado/observacoes.csv` — as duas metades.

NADA AQUI TOCA A `.mercado/` REAL. Toda instancia recebe `tmp_path`, pelo mesmo
motivo que `tests/test_mercado_catalogo.py:504-514` ja escreve para o catalogo
irmao: um teste que escrevesse na pasta de producao contaminaria dado ACUMULADO
e sem poda — nao ha desfazer. O construtor de `RegistroDeObservacoes` recebe a
pasta justamente para que esta linha seja possivel.

Tambem nao ha `recordings/` nem `calibration.json` aqui: sao strings, inteiros e
arquivos de texto em `tmp_path`. Um teste que dependesse de material gravado
ficaria verde nesta maquina e amarelo em toda outra.

OS NUMEROS QUE ESTE ARQUIVO COBRA, E DE ONDE VIERAM
====================================================
Os CINCO CORTES BYTE A BYTE de `TestOPortaoDoTerminador` sao os medidos na
`03-RESEARCH.md`, secao "Lacuna 4", sobre a linha de seis colunas
`k;nome;2026-08-30T14:03:21;6200;48;80\r\n`:

    corte= 36 bytes -> [...,'6200','48','8']  campos=6 (esperado 6)  <- passa na contagem
    corte= 35 bytes -> [...,'6200','48','']   campos=6 (esperado 6)  <- passa na contagem
    corte= 34 bytes -> [...,'6200','48']      campos=5
    corte= 33 bytes -> [...,'6200','4']       campos=5
    corte= 31 bytes -> [...,'6200']           campos=4

DOIS DOS CINCO passam pela contagem de campos com o ultimo campo PARCIAL — `80`
vira `8`, e um residuo de 8 centesimos onde o disco dizia 80 e dado parcial com
aparencia plausivel. E por isso que o portao do TERMINADOR vem primeiro e a
contagem de campos e a SEGUNDA rede, nunca a primeira (D-17).

Os QUATRO CONTEUDOS HOSTIS de `TestOConteudoHostilDoOCR` sao os da secao
"Lacuna 3": delimitador dentro do nome, aspas, quebra de linha e virgula
decimal. Todos medidos como sobreviventes do round-trip do modulo `csv`, e
nenhum precisa ser saneado — sanear alteraria o rotulo que o usuario le.
"""

from __future__ import annotations

import ast
import csv
import inspect
import logging
import os
import shutil
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from l2scanner.mercado_catalogo import PASTA_DO_MERCADO, SEPARADOR
from l2scanner.mercado_leitura import LinhaLida
from l2scanner.mercado_registro import (
    ARQUIVO_DE_OBSERVACOES,
    ARQUIVO_DO_LEIAME,
    COLUNAS,
    ContratoDoArquivoQuebrado,
    RegistroDeObservacoes,
    campos_da_observacao,
    chave_da_observacao,
    chave_dos_campos,
    escrever_leiame,
    residuo_dos_campos,
)

LOGGER = "l2scanner.mercado_registro"

# Ingenuos, hora local, sem `tzinfo` — e o que `Relogio.agora()` devolve
# (`l2scanner/relogio.py:156-163`). Cobrar timezone aqui cobraria um formato que
# a producao nunca vai produzir.
AGORA = datetime(2026, 8, 30, 21, 15, 0)
DEPOIS = datetime(2026, 8, 31, 9, 0, 0)


def _linha(
    *,
    chave_da_serie: str = "common-aztac#0",
    nome_exibido: str = "Common Aztac",
    total_em_centesimos: int = 6200,
    quantidade: int = 48,
    residuo_do_cruzamento: int | None = None,
    indice: int = 3,
    serie_nova: bool = False,
) -> LinhaLida:
    """Uma `LinhaLida` de bancada, com tudo nomeado.

    `indice` e `serie_nova` tem valor aqui de proposito: eles EXISTEM na
    `LinhaLida` e o registro tem de os deixar de fora (D-04). Um helper que os
    omitisse nao conseguiria provar a ausencia.
    """
    return LinhaLida(
        indice=indice,
        chave_da_serie=chave_da_serie,
        nome_exibido=nome_exibido,
        total_em_centesimos=total_em_centesimos,
        quantidade=quantidade,
        serie_nova=serie_nova,
        residuo_do_cruzamento=residuo_do_cruzamento,
    )


def _linhas_cruas(pasta: Path) -> list[str]:
    return (pasta / ARQUIVO_DE_OBSERVACOES).read_text(encoding="utf-8").splitlines()


def _campos_da_primeira_observacao(pasta: Path) -> list[str]:
    """Os campos da linha 2 do arquivo, relidos pelo modulo `csv`.

    `newline=""` no `open` e obrigatorio nos DOIS sentidos: sem ele a traducao
    universal de quebras de linha alteraria um `nome_exibido` que contem `\\r`,
    e este helper existe justamente para provar que o nome volta IDENTICO.
    """
    with (pasta / ARQUIVO_DE_OBSERVACOES).open(
        "r", encoding="utf-8", newline=""
    ) as fonte:
        return list(csv.reader(fonte, delimiter=SEPARADOR))[1]


# ===========================================================================
# A METADE PURA: chave, campos e o caminho de volta
# ===========================================================================


class TestAChaveDeDedup:
    """`chave_da_observacao` — serie + total + quantidade, e SO isso (D-05)."""

    def test_a_chave_e_a_TRIPLA_serie_total_quantidade(self):
        assert chave_da_observacao(_linha()) == ("common-aztac#0", 6200, 48)

    def test_a_chave_NAO_carrega_o_carimbo_nem_o_nome(self):
        """Incluir o tempo tornaria a dedup VACUA: cada tick tem carimbo novo.

        A prova e estrutural — a tripla tem tres elementos e nenhum deles e
        texto de data — e nao "o carimbo nao aparece", que um refactor quebraria
        sem ninguem ver.
        """
        chave = chave_da_observacao(_linha())
        assert len(chave) == 3
        assert chave[0] == "common-aztac#0"
        assert isinstance(chave[1], int)
        assert isinstance(chave[2], int)

    def test_mesmo_conteudo_com_NOME_diferente_da_a_MESMA_chave(self):
        """O nome e ROTULO e o OCR o faz oscilar; a chave e a identidade (D-03)."""
        primeira = _linha(nome_exibido="Common Aztac")
        segunda = _linha(nome_exibido="Cornmon Aztac")
        assert chave_da_observacao(primeira) == chave_da_observacao(segunda)

    def test_quantidade_diferente_da_chave_DIFERENTE(self):
        assert chave_da_observacao(_linha(quantidade=48)) != chave_da_observacao(
            _linha(quantidade=47)
        )

    def test_total_diferente_da_chave_DIFERENTE(self):
        assert chave_da_observacao(_linha(total_em_centesimos=6200)) != (
            chave_da_observacao(_linha(total_em_centesimos=6201))
        )

    def test_a_chave_e_TUPLA_e_nao_texto_juntado(self):
        """Um `;` dentro da chave da serie tornaria duas observacoes distintas
        indistinguiveis se a chave fosse texto concatenado."""
        assert isinstance(chave_da_observacao(_linha()), tuple)


class TestOsCamposDaLinha:
    """`campos_da_observacao` — seis strings, na ordem de `COLUNAS`."""

    def test_sao_exatamente_len_COLUNAS_campos(self):
        campos = campos_da_observacao(_linha(), AGORA)
        assert len(campos) == len(COLUNAS)
        assert all(isinstance(campo, str) for campo in campos)

    def test_a_ordem_e_a_de_COLUNAS_e_os_numeros_saem_INTEIROS(self):
        campos = campos_da_observacao(
            _linha(total_em_centesimos=6200, quantidade=48), AGORA
        )
        assert campos == (
            "common-aztac#0",
            "Common Aztac",
            "2026-08-30T21:15:00",
            "6200",
            "48",
            "",
        )

    def test_o_carimbo_sai_em_isoformat(self):
        campos = campos_da_observacao(_linha(), AGORA)
        assert campos[COLUNAS.index("primeira_vez")] == AGORA.isoformat()

    def test_o_relogio_entra_por_PARAMETRO_e_nao_de_dentro(self):
        """Dois carimbos, dois resultados — a prova de comportamento do D-16."""
        assert campos_da_observacao(_linha(), AGORA) != campos_da_observacao(
            _linha(), DEPOIS
        )


class TestOResiduoQueNaoColapsa:
    """`None` (nao mediu) e `0` (conferi e bateu) sao fatos DIFERENTES (D-01)."""

    def test_None_sai_VAZIO_e_zero_sai_ZERO(self):
        vazio = campos_da_observacao(_linha(residuo_do_cruzamento=None), AGORA)
        zero = campos_da_observacao(_linha(residuo_do_cruzamento=0), AGORA)
        indice = COLUNAS.index("residuo_do_cruzamento")
        assert vazio[indice] == ""
        assert zero[indice] == "0"
        assert vazio != zero

    def test_a_volta_devolve_None_e_zero_e_NUNCA_um_pelo_outro(self):
        vazio = campos_da_observacao(_linha(residuo_do_cruzamento=None), AGORA)
        zero = campos_da_observacao(_linha(residuo_do_cruzamento=0), AGORA)
        assert residuo_dos_campos(vazio) is None
        assert residuo_dos_campos(zero) == 0
        assert residuo_dos_campos(zero) is not None

    def test_um_residuo_medido_sobrevive_a_ida_e_volta(self):
        campos = campos_da_observacao(_linha(residuo_do_cruzamento=80), AGORA)
        assert residuo_dos_campos(campos) == 80


class TestOCaminhoDeVolta:
    """`chave_dos_campos` LEVANTA `ValueError` com o motivo em TEXTO."""

    def test_uma_linha_boa_volta_como_a_mesma_chave_da_ida(self):
        linha = _linha()
        campos = campos_da_observacao(linha, AGORA)
        assert chave_dos_campos(campos) == chave_da_observacao(linha)

    def test_campos_a_menos_levanta_com_o_motivo_em_texto(self):
        with pytest.raises(ValueError) as erro:
            chave_dos_campos(("a", "b", "c"))
        assert "campos" in str(erro.value)

    def test_campos_a_MAIS_tambem_levanta(self):
        campos = campos_da_observacao(_linha(), AGORA) + ("sobra",)
        with pytest.raises(ValueError):
            chave_dos_campos(campos)

    def test_chave_vazia_levanta(self):
        campos = list(campos_da_observacao(_linha(), AGORA))
        campos[0] = "   "
        with pytest.raises(ValueError):
            chave_dos_campos(tuple(campos))

    def test_carimbo_que_nao_e_ISO_levanta(self):
        campos = list(campos_da_observacao(_linha(), AGORA))
        campos[2] = "ontem de tarde"
        with pytest.raises(ValueError):
            chave_dos_campos(tuple(campos))

    def test_total_nao_inteiro_levanta(self):
        campos = list(campos_da_observacao(_linha(), AGORA))
        campos[3] = "62,00"
        with pytest.raises(ValueError):
            chave_dos_campos(tuple(campos))

    def test_quantidade_nao_inteira_levanta(self):
        campos = list(campos_da_observacao(_linha(), AGORA))
        campos[4] = "quarenta e oito"
        with pytest.raises(ValueError):
            chave_dos_campos(tuple(campos))

    def test_residuo_que_nao_e_vazio_nem_inteiro_levanta(self):
        campos = list(campos_da_observacao(_linha(), AGORA))
        campos[5] = "quase"
        with pytest.raises(ValueError):
            chave_dos_campos(tuple(campos))


class TestOContratoDasColunas:
    """`COLUNAS` vira contrato no disco do usuario no primeiro arquivo criado."""

    def test_as_seis_colunas_na_ordem_travada(self):
        assert COLUNAS == (
            "chave_da_serie",
            "nome_exibido",
            "primeira_vez",
            "total_em_centesimos",
            "quantidade",
            "residuo_do_cruzamento",
        )

    def test_NAO_ha_coluna_de_unitario_derivado(self):
        """`40,00` por 48 aparece como `0,83`, e `0,83 x 48 = 39,84` — um numero
        que nunca existiu. Total e quantidade bastam (D-02)."""
        assert not any("unitario" in coluna for coluna in COLUNAS)

    def test_NAO_ha_coluna_de_proveniencia_de_bancada(self):
        """`indice` e `serie_nova` sao da `LinhaLida`; gravacao e frame nao
        existem no farm ao vivo (D-04)."""
        proibidas = {"indice", "serie_nova", "gravacao", "frame"}
        assert proibidas.isdisjoint(COLUNAS)

    def test_a_unidade_esta_no_NOME_da_coluna(self):
        """`6200` so e autoexplicativo porque o cabecalho diz `centesimos`."""
        assert "total_em_centesimos" in COLUNAS

    def test_o_separador_e_a_pasta_vem_do_CATALOGO_e_nao_sao_redefinidos(self):
        """Duas definicoes do mesmo `;` e como elas divergem."""
        from l2scanner import mercado_registro

        assert mercado_registro.SEPARADOR is SEPARADOR
        assert mercado_registro.PASTA_DO_MERCADO == PASTA_DO_MERCADO


class TestOModuloNaoArrastaAMetadeDeVisao:
    """`LinhaLida` so sob `TYPE_CHECKING` — e a prova disso e um subprocesso.

    UM NUMERO QUE CAIU PRECISA DIZER QUE CAIU. O plano cobrava a forma mais
    forte: `cv2` e `numpy` ausentes de `sys.modules` depois de importar
    `mercado_registro`. MEDIDO: impossivel, e nao por culpa deste modulo —
    `import l2scanner.mercado_catalogo` SOZINHO ja deixa os dois la, porque ele
    importa `.config`, que importa `.visao`. Como importar `PASTA_DO_MERCADO` e
    `SEPARADOR` do catalogo (em vez de redefinir) e contrato desta fase, as duas
    exigencias se contradiziam.

    O que ficou e o que mede a mesma coisa e da para afirmar: este modulo nao
    acrescenta peso NENHUM por conta propria.

    E A FORMA FORTE FOI COBRADA DE VOLTA, na Fase 1 do workstream `dashboard`
    (2026-09-01). O `l2scanner/raiz.py` — modulo FOLHA — tirou `RAIZ` de
    `config`, e `mercado_catalogo.py` passou a importar dali. A contradicao que
    o paragrafo acima descreve DEIXOU DE EXISTIR: importar o catalogo nao
    arrasta mais `.config`, entao `cv2` e `numpy` podem ser cobrados ausentes
    sem ferir o contrato de importar `PASTA_DO_MERCADO` e `SEPARADOR` do
    catalogo em vez de redefinir.

    O teste abaixo foi VIRADO, e nao apagado: ele afirmava a PRESENCA dos dois
    pesados e agora afirma a AUSENCIA. Foi exatamente o que a docstring dele
    mandava fazer no dia em que ficasse vermelho. Medido na virada: `import
    l2scanner.mercado_catalogo` caiu de 341 para 108 modulos em `sys.modules`.
    """

    def test_importar_o_registro_acrescenta_UM_modulo_so_ao_que_o_catalogo_ja_traz(
        self,
    ):
        codigo = (
            "import sys\n"
            "import l2scanner.mercado_catalogo\n"
            "antes = set(sys.modules)\n"
            "import l2scanner.mercado_registro\n"
            "novos = sorted(set(sys.modules) - antes)\n"
            "print(';'.join(novos))\n"
        )
        saida = subprocess.run(
            [sys.executable, "-c", codigo],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).resolve().parent.parent,
        )
        assert saida.stdout.strip() == "l2scanner.mercado_registro"

    def test_mercado_leitura_NAO_e_carregado_pelo_registro(self):
        """O `TYPE_CHECKING` sendo real, e nao decorativo."""
        codigo = (
            "import sys\n"
            "import l2scanner.mercado_registro\n"
            "print('l2scanner.mercado_leitura' in sys.modules)\n"
        )
        saida = subprocess.run(
            [sys.executable, "-c", codigo],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).resolve().parent.parent,
        )
        assert saida.stdout.strip() == "False"

    def test_o_catalogo_NAO_traz_MAIS_cv2_nem_numpy_a_forma_forte_de_volta(self):
        """A FORMA FORTE, cobrada de volta depois do corte de `RAIZ`.

        ESTE TESTE JA FOI O OPOSTO DELE MESMO, e isso e deliberado. Ate a Fase 1
        do `dashboard` ele se chamava
        `test_o_catalogo_JA_traz_cv2_e_numpy_e_por_isso_o_criterio_original_caiu`,
        afirmava `"True True"` e carregava a instrucao escrita de que ficar
        vermelho seria BOA NOTICIA — "a hora de cobrar de volta a forma forte".
        Ele ficou vermelho no commit do corte, e esta e a cobranca de volta que
        ele mesmo mandava fazer. Virar um tripwire que avisou e o uso correto
        dele; apaga-lo teria jogado fora a unica prova de que o corte pegou.

        O QUE MUDOU NO FONTE: `mercado_catalogo.py` importa `RAIZ` de
        `l2scanner/raiz.py` (modulo folha) em vez de `l2scanner/config.py`, o
        que corta `config -> notificador -> rastreador -> visao -> cv2`.

        O QUE ELE NAO AFIRMA, e precisa estar escrito para nao virar folclore
        pela segunda vez: o PROCESSO do dashboard continua carregando `cv2`, por
        uma SEGUNDA aresta (`mercado_console -> console -> rastreador`) que
        aquela fase nao estava autorizada a tocar. Este teste fala do CATALOGO,
        e so dele.
        """
        codigo = (
            "import sys\n"
            "import l2scanner.mercado_catalogo\n"
            "print('cv2' in sys.modules, 'numpy' in sys.modules)\n"
        )
        saida = subprocess.run(
            [sys.executable, "-c", codigo],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).resolve().parent.parent,
        )
        assert saida.stdout.strip() == "False False"


# ===========================================================================
# A METADE DE DISCO: o arquivo que cresce por append
# ===========================================================================


class TestOArquivoNasceBem:
    """Arranque numa maquina limpa."""

    def test_pasta_vazia_cria_o_arquivo_com_CABECALHO_e_indice_vazio(self, tmp_path):
        registro = RegistroDeObservacoes(tmp_path / ".mercado")
        assert registro.chaves == set()
        assert registro.ligado is True
        assert _linhas_cruas(tmp_path / ".mercado")[0] == SEPARADOR.join(COLUNAS)

    def test_o_construtor_POSSUI_a_pasta(self, tmp_path):
        pasta = tmp_path / ".mercado"
        assert not pasta.exists()
        RegistroDeObservacoes(pasta)
        assert pasta.is_dir()

    def test_arquivo_ausente_e_estado_LEGITIMO_e_nao_levanta(self, tmp_path):
        """Primeira execucao numa maquina limpa nao e erro (D-11)."""
        registro = RegistroDeObservacoes(tmp_path / ".mercado")
        assert registro.arquivo.is_file()


class TestUmaObservacaoAtravessaInteira:
    """O TRACER: `LinhaLida` -> chave -> campos -> disco -> releitura -> dedup."""

    def test_registrar_uma_observacao_nova_devolve_True_e_escreve_UMA_linha(
        self, tmp_path
    ):
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)
        assert registro.registrar(_linha(), AGORA) is True
        assert len(_linhas_cruas(pasta)) == 2  # cabecalho + uma

    def test_a_MESMA_observacao_de_novo_devolve_False_e_NAO_cresce(self, tmp_path):
        """A dedup que tapa a borda 33 do `WINDOWS.md`, e ela precisa ser dita.

        ACEITO PELO USUARIO EM 2026-08-30: numa captura TRAVADA uma pagina e
        aceita antes de o congelamento disparar — o acordo fecha com 2 frames
        identicos e `JANELAS_IGUAIS_PARA_CONGELAR` e 3, entao o frame 2 concorda
        trivialmente e passa. O dado daquela pagina e o ULTIMO FRAME VIVO:
        verdadeiro, so velho. **Esta dedup e o que impede aquela pagina de virar
        linha duplicada no CSV** — foi com essa rede na mesa que a borda foi
        aceita em vez de baixar o limiar para 2 (que pagaria falso positivo).
        Sem este comentario o proximo leitor le "dedup generica" e nao ve a
        borda que ela tapa.
        """
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)
        registro.registrar(_linha(), AGORA)
        antes = len(_linhas_cruas(pasta))

        assert registro.registrar(_linha(), AGORA) is False

        assert len(_linhas_cruas(pasta)) == antes == 2

    def test_uma_SESSAO_NOVA_reconstroi_o_indice_do_disco(self, tmp_path):
        """PERS-02: a dedup de uma sessao nova enxerga o que a anterior gravou."""
        pasta = tmp_path / ".mercado"
        primeira = RegistroDeObservacoes(pasta)
        assert primeira.registrar(_linha(), AGORA) is True

        segunda = RegistroDeObservacoes(pasta)
        assert segunda.chaves == {chave_da_observacao(_linha())}
        assert segunda.registrar(_linha(), AGORA) is False
        assert len(_linhas_cruas(pasta)) == 2

    def test_observacoes_DIFERENTES_viram_linhas_diferentes(self, tmp_path):
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)
        assert registro.registrar(_linha(quantidade=48), AGORA) is True
        assert registro.registrar(_linha(quantidade=47), AGORA) is True
        assert len(_linhas_cruas(pasta)) == 3

    def test_o_arquivo_termina_em_QUEBRA_DE_LINHA_apos_cada_registro(self, tmp_path):
        """A bicondicional que o portao do terminador usa: `writerow` emite a
        linha E o terminador numa chamada so."""
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)
        registro.registrar(_linha(), AGORA)
        assert registro.arquivo.read_bytes().endswith(b"\n")
        registro.registrar(_linha(quantidade=1), AGORA)
        assert registro.arquivo.read_bytes().endswith(b"\n")

    def test_a_linha_gravada_carrega_os_seis_campos_e_nada_mais(self, tmp_path):
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)
        registro.registrar(_linha(residuo_do_cruzamento=80), AGORA)
        campos = _campos_da_primeira_observacao(pasta)
        assert campos == [
            "common-aztac#0",
            "Common Aztac",
            "2026-08-30T21:15:00",
            "6200",
            "48",
            "80",
        ]


class TestAPrimeiraVezMANDA:
    """O mesmo anuncio em dias diferentes e UMA linha, com a data da PRIMEIRA."""

    def test_o_mesmo_anuncio_em_OUTRO_DIA_continua_False(self, tmp_path):
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)
        registro.registrar(_linha(), AGORA)
        assert registro.registrar(_linha(), DEPOIS) is False

    def test_o_carimbo_no_arquivo_continua_sendo_o_da_PRIMEIRA_vez(self, tmp_path):
        """D-06 literal: a coluna chama `primeira_vez` porque e o que ela e."""
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)
        registro.registrar(_linha(), AGORA)
        registro.registrar(_linha(), DEPOIS)
        campos = _campos_da_primeira_observacao(pasta)
        assert campos[COLUNAS.index("primeira_vez")] == AGORA.isoformat()
        assert DEPOIS.isoformat() not in (pasta / ARQUIVO_DE_OBSERVACOES).read_text(
            encoding="utf-8"
        )

    def test_dois_carimbos_diferentes_produzem_ARQUIVOS_diferentes(self, tmp_path):
        """A prova de COMPORTAMENTO de que o relogio entra por parametro (D-16).

        A conferencia por AST prova que `now()` nao e chamado; esta prova que o
        carimbo recebido e o carimbo gravado.
        """
        cedo = tmp_path / "cedo"
        tarde = tmp_path / "tarde"
        RegistroDeObservacoes(cedo).registrar(_linha(), AGORA)
        RegistroDeObservacoes(tarde).registrar(_linha(), agora=DEPOIS)
        assert (cedo / ARQUIVO_DE_OBSERVACOES).read_bytes() != (
            tarde / ARQUIVO_DE_OBSERVACOES
        ).read_bytes()


class TestOConteudoHostilDoOCR:
    """Os quatro casos medidos na `03-RESEARCH.md`, secao Lacuna 3.

    O nome vem do motor de OCR e pode conter qualquer coisa que ele alucine: um
    `;` a partir de um `:`, aspas a partir do apostrofo de `Hardin's`, um `\\n`
    se o recorte pegar duas alturas de texto. O modulo `csv` com `QUOTE_MINIMAL`
    e `newline=""` nos DOIS sentidos protege todos — e sanear seria pior, porque
    alteraria o rotulo que o usuario le.
    """

    @pytest.mark.parametrize(
        "nome",
        [
            "Common; Aztac",  # o proprio delimitador dentro do campo
            'Hardin\'s "Soul" Crystal',  # aspas
            "Common\nAztac",  # quebra de linha
            "Preco 62,00 de bolso",  # virgula decimal, que NAO e citada
        ],
        ids=["delimitador", "aspas", "quebra-de-linha", "virgula-decimal"],
    )
    def test_o_nome_sobrevive_a_ida_e_volta_IDENTICO(self, tmp_path, nome):
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)
        assert registro.registrar(_linha(nome_exibido=nome), AGORA) is True

        campos = _campos_da_primeira_observacao(pasta)
        assert campos[COLUNAS.index("nome_exibido")] == nome

    @pytest.mark.parametrize(
        "nome",
        [
            "Common; Aztac",
            'Hardin\'s "Soul" Crystal',
            "Common\nAztac",
            "Preco 62,00 de bolso",
        ],
        ids=["delimitador", "aspas", "quebra-de-linha", "virgula-decimal"],
    )
    def test_o_nome_hostil_nao_parte_a_LINHA_e_a_sessao_nova_ainda_dedupa(
        self, tmp_path, nome
    ):
        pasta = tmp_path / ".mercado"
        RegistroDeObservacoes(pasta).registrar(_linha(nome_exibido=nome), AGORA)

        segunda = RegistroDeObservacoes(pasta)
        assert segunda.chaves == {chave_da_observacao(_linha())}
        assert segunda.registrar(_linha(nome_exibido=nome), AGORA) is False


# ===========================================================================
# O PORTAO DE CONTRATO E AS DUAS REDES POR LINHA
# ===========================================================================
#
# A ORDEM E O ACHADO CENTRAL DA PESQUISA, e ela e: portao do TERMINADOR, portao
# do CABECALHO, depois as duas redes por linha. Inverter a ordem devolve o
# defeito que o D-17 existe para nao ter.
#
# A DIFERENCA DE NIVEL E DE ALCANCE ENTRE AS DUAS FAMILIAS E DELIBERADA:
#   - contrato quebrado  -> `log.error`   -> `ContratoDoArquivoQuebrado`, nada
#                                            e lido, a feature DESLIGA
#   - linha ruim no meio -> `log.warning` -> so ela cai, o arquivo carrega

# A linha de seis colunas que a `03-RESEARCH.md` cortou byte a byte.
LINHA_MEDIDA = b"k;nome;2026-08-30T14:03:21;6200;48;80\r\n"

# corte -> quantos campos o `csv.reader` devolve daquela cauda (medido)
CORTES_MEDIDOS = [(36, 6), (35, 6), (34, 5), (33, 5), (31, 4)]
IDS_DOS_CORTES = [f"corte-{corte}" for corte, _ in CORTES_MEDIDOS]


def _fabricar(pasta: Path, corpo: bytes) -> Path:
    """Escreve o arquivo em BYTES, sem traducao nenhuma de quebra de linha.

    `write_text` traduziria `\\n` para `\\r\\n` no Windows e destruiria
    justamente a propriedade que estes testes medem.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / ARQUIVO_DE_OBSERVACOES).write_bytes(corpo)
    return pasta


def _cabecalho() -> bytes:
    return SEPARADOR.join(COLUNAS).encode("utf-8") + b"\r\n"


class TestOPortaoDoTerminador:
    """Os CINCO cortes medidos. Arquivo sem quebra final e contrato quebrado."""

    @pytest.mark.parametrize(
        ("corte", "campos_daquela_cauda"), CORTES_MEDIDOS, ids=IDS_DOS_CORTES
    )
    def test_os_cinco_cortes_byte_a_byte_LEVANTAM(
        self, tmp_path, caplog, corte, campos_daquela_cauda
    ):
        """5 de 5 recusados. A contagem de campos aprovaria DOIS deles.

        Os cortes 36 e 35 devolvem SEIS campos — o numero certo — com o ultimo
        campo PARCIAL: `80` vira `8` e depois vira `''`. Um residuo de 8
        centesimos onde o disco dizia 80 e dado parcial com aparencia plausivel,
        e pior: viraria CHAVE DE DEDUP, bloqueando para sempre a gravacao da
        observacao correta. O `campos_daquela_cauda` do parametro esta aqui
        justamente para o teste AFIRMAR que a rede de contagem os aprovaria.
        """
        pasta = _fabricar(tmp_path / ".mercado", _cabecalho() + LINHA_MEDIDA[:corte])

        cauda = LINHA_MEDIDA[:corte].decode("utf-8")
        assert (
            len(list(csv.reader([cauda], delimiter=SEPARADOR))[0])
            == campos_daquela_cauda
        )

        with caplog.at_level("ERROR", logger=LOGGER):
            with pytest.raises(ContratoDoArquivoQuebrado):
                RegistroDeObservacoes(pasta)

    @pytest.mark.parametrize(
        "corte", [corte for corte, _ in CORTES_MEDIDOS], ids=IDS_DOS_CORTES
    )
    def test_NENHUM_byte_do_arquivo_do_usuario_e_tocado_na_recusa(
        self, tmp_path, corte
    ):
        """T-03-01b: o arranque nunca escreve sobre dado existente.

        As duas saidas que mexeriam no arquivo — truncar a cauda, ou completa-la
        com uma quebra de linha — estao refutadas por escrito no fonte. Este
        teste e a prova de que a refutacao virou comportamento.
        """
        pasta = _fabricar(tmp_path / ".mercado", _cabecalho() + LINHA_MEDIDA[:corte])
        antes = (pasta / ARQUIVO_DE_OBSERVACOES).read_bytes()

        with pytest.raises(ContratoDoArquivoQuebrado):
            RegistroDeObservacoes(pasta)

        assert (pasta / ARQUIVO_DE_OBSERVACOES).read_bytes() == antes

    def test_o_conteudo_CRU_da_cauda_aparece_no_log(self, tmp_path, caplog):
        """A unica coisa que o usuario tem para reconstruir a linha."""
        pasta = _fabricar(tmp_path / ".mercado", _cabecalho() + LINHA_MEDIDA[:36])

        with caplog.at_level("ERROR", logger=LOGGER):
            with pytest.raises(ContratoDoArquivoQuebrado):
                RegistroDeObservacoes(pasta)

        assert "k;nome;2026-08-30T14:03:21;6200;48;8" in caplog.text

    def test_a_mensagem_nomeia_as_DUAS_hipoteses_e_diz_o_que_fazer(
        self, tmp_path, caplog
    ):
        """O criterio nao distingue truncagem de estilo de editor, e o aviso
        tem de dizer isso — senao o usuario conserta a hipotese errada."""
        pasta = _fabricar(tmp_path / ".mercado", _cabecalho() + LINHA_MEDIDA[:36])

        with caplog.at_level("ERROR", logger=LOGGER):
            with pytest.raises(ContratoDoArquivoQuebrado):
                RegistroDeObservacoes(pasta)

        texto = caplog.text.lower()
        assert "nao termina em quebra de linha" in texto
        assert "interrompida" in texto  # hipotese 1
        assert "editado a mao" in texto  # hipotese 2
        assert "quebra de linha no fim" in texto  # o que fazer
        assert "proximo arranque" in texto  # o que isso religa

    def test_o_nivel_da_recusa_por_contrato_e_ERROR_e_nao_WARNING(
        self, tmp_path, caplog
    ):
        """Precedente explicito da casa: `warning` e linha descartada, `error`
        e feature desligada."""
        pasta = _fabricar(tmp_path / ".mercado", _cabecalho() + LINHA_MEDIDA[:36])

        with caplog.at_level("DEBUG", logger=LOGGER):
            with pytest.raises(ContratoDoArquivoQuebrado):
                RegistroDeObservacoes(pasta)

        assert any(r.levelname == "ERROR" for r in caplog.records)

    def test_so_o_CABECALHO_sem_quebra_final_tambem_e_contrato_quebrado(self, tmp_path):
        """Criacao interrompida. O programa NAO completa o cabecalho a mao."""
        corpo = SEPARADOR.join(COLUNAS).encode("utf-8")  # sem `\r\n`
        pasta = _fabricar(tmp_path / ".mercado", corpo)

        with pytest.raises(ContratoDoArquivoQuebrado):
            RegistroDeObservacoes(pasta)

        assert (pasta / ARQUIVO_DE_OBSERVACOES).read_bytes() == corpo

    def test_a_cauda_pode_ser_uma_linha_INTEIRA_sem_terminador_e_ainda_levanta(
        self, tmp_path
    ):
        """'Linha inteira, so sem o \\n' e a hipotese do editor — e ela cai pelo
        mesmo portao, porque o criterio nao consegue distinguir as duas."""
        pasta = _fabricar(
            tmp_path / ".mercado",
            _cabecalho() + b"k;nome;2026-08-30T14:03:21;6200;48;80",
        )
        with pytest.raises(ContratoDoArquivoQuebrado):
            RegistroDeObservacoes(pasta)

    def test_um_arquivo_INTEGRO_carrega_TODAS_as_linhas(self, tmp_path):
        pasta = _fabricar(
            tmp_path / ".mercado",
            _cabecalho()
            + b"a#0;Item A;2026-08-30T21:15:00;6200;48;\r\n"
            + b"b#0;Item B;2026-08-30T21:16:00;4000;12;80\r\n",
        )
        registro = RegistroDeObservacoes(pasta)
        assert registro.chaves == {("a#0", 6200, 48), ("b#0", 4000, 12)}
        assert registro.ligado is True


class TestOArquivoDeZeroBytes:
    """O UNICO caso que nao passa pelo portao — e o comentario diz por que."""

    def test_zero_bytes_recebe_o_cabecalho_e_carrega_VAZIO_sem_levantar(
        self, tmp_path, caplog
    ):
        """Nao ha dado a preservar num arquivo vazio.

        O que aconteceu ali foi uma CRIACAO INTERROMPIDA, nao uma escrita
        perdida: nenhum byte do usuario existe para ser destruido, entao
        escrever o cabecalho nao viola o T-03-01b. Qualquer arquivo NAO vazio
        que nao case com o contrato — inclusive um que contenha so o cabecalho
        sem a quebra final — desliga a feature.
        """
        pasta = _fabricar(tmp_path / ".mercado", b"")

        with caplog.at_level("WARNING", logger=LOGGER):
            registro = RegistroDeObservacoes(pasta)

        assert registro.chaves == set()
        assert registro.ligado is True
        assert _linhas_cruas(pasta)[0] == SEPARADOR.join(COLUNAS)
        assert caplog.records  # o aviso sai: zero bytes nao e o normal


class TestOCabecalhoEContrato:
    """D-12: divergiu, DESLIGA ALTO. Nenhuma migracao automatica."""

    def test_coluna_TROCADA_levanta(self, tmp_path):
        trocado = (
            "chave_da_serie",
            "nome_exibido",
            "primeira_vez",
            "total",  # era `total_em_centesimos`: a unidade sumiu do cabecalho
            "quantidade",
            "residuo_do_cruzamento",
        )
        pasta = _fabricar(
            tmp_path / ".mercado", SEPARADOR.join(trocado).encode("utf-8") + b"\r\n"
        )
        with pytest.raises(ContratoDoArquivoQuebrado):
            RegistroDeObservacoes(pasta)

    def test_as_mesmas_colunas_em_OUTRA_ORDEM_levanta(self, tmp_path):
        """A ORDEM e contrato tanto quanto o conjunto: o append escreveria os
        valores nas colunas erradas e ninguem veria."""
        outra = (COLUNAS[1], COLUNAS[0]) + COLUNAS[2:]
        pasta = _fabricar(
            tmp_path / ".mercado", SEPARADOR.join(outra).encode("utf-8") + b"\r\n"
        )
        with pytest.raises(ContratoDoArquivoQuebrado):
            RegistroDeObservacoes(pasta)

    def test_arquivo_NAO_VAZIO_sem_cabecalho_levanta(self, tmp_path):
        pasta = _fabricar(
            tmp_path / ".mercado", b"a#0;Item A;2026-08-30T21:15:00;6200;48;\r\n"
        )
        with pytest.raises(ContratoDoArquivoQuebrado):
            RegistroDeObservacoes(pasta)

    def test_a_recusa_por_cabecalho_tambem_nao_toca_BYTE_nenhum(self, tmp_path):
        corpo = b"a#0;Item A;2026-08-30T21:15:00;6200;48;\r\n"
        pasta = _fabricar(tmp_path / ".mercado", corpo)
        with pytest.raises(ContratoDoArquivoQuebrado):
            RegistroDeObservacoes(pasta)
        assert (pasta / ARQUIVO_DE_OBSERVACOES).read_bytes() == corpo

    def test_o_cabecalho_com_ESPACOS_ao_redor_ainda_serve(self, tmp_path):
        """`strip` em cada campo, igual ao analog — um editor que alinhou as
        colunas nao e um arquivo corrompido."""
        pasta = _fabricar(
            tmp_path / ".mercado",
            SEPARADOR.join(f" {coluna} " for coluna in COLUNAS).encode("utf-8")
            + b"\r\n",
        )
        registro = RegistroDeObservacoes(pasta)
        assert registro.chaves == set()

    def test_a_mensagem_do_cabecalho_diz_o_que_esperava_e_o_que_ACHOU(
        self, tmp_path, caplog
    ):
        pasta = _fabricar(tmp_path / ".mercado", b"a;b;c;d;e;f\r\n")
        with caplog.at_level("ERROR", logger=LOGGER):
            with pytest.raises(ContratoDoArquivoQuebrado):
                RegistroDeObservacoes(pasta)
        assert "chave_da_serie" in caplog.text  # o esperado
        assert "'a'" in caplog.text  # o encontrado, cru


class TestAsDuasRedesPorLinha:
    """D-14: uma linha ruim do MEIO cai sozinha. O arquivo nunca e condenado."""

    def test_linha_do_meio_com_campos_A_MENOS_cai_e_as_demais_CARREGAM(
        self, tmp_path, caplog
    ):
        pasta = _fabricar(
            tmp_path / ".mercado",
            _cabecalho()
            + b"a#0;Item A;2026-08-30T21:15:00;6200;48;\r\n"
            + b"b#0;Item B;2026-08-30T21:16:00\r\n"
            + b"c#0;Item C;2026-08-30T21:17:00;4000;12;0\r\n",
        )
        with caplog.at_level("DEBUG", logger=LOGGER):
            registro = RegistroDeObservacoes(pasta)

        assert registro.chaves == {("a#0", 6200, 48), ("c#0", 4000, 12)}
        assert registro.ligado is True
        assert "linha 3" in caplog.text
        assert "b#0" in caplog.text  # o conteudo CRU
        assert any(r.levelname == "WARNING" for r in caplog.records)
        assert not any(r.levelname == "ERROR" for r in caplog.records)

    def test_linha_com_campos_A_MAIS_tambem_cai_sozinha(self, tmp_path, caplog):
        pasta = _fabricar(
            tmp_path / ".mercado",
            _cabecalho()
            + b"a#0;Item A;2026-08-30T21:15:00;6200;48;;sobra\r\n"
            + b"c#0;Item C;2026-08-30T21:17:00;4000;12;0\r\n",
        )
        with caplog.at_level("WARNING", logger=LOGGER):
            registro = RegistroDeObservacoes(pasta)
        assert registro.chaves == {("c#0", 4000, 12)}

    @pytest.mark.parametrize(
        "corpo",
        [
            b"b#0;Item B;2026-08-30T21:16:00;seis mil;12;\r\n",
            b"b#0;Item B;2026-08-30T21:16:00;4000;doze;\r\n",
            b"b#0;Item B;ontem de tarde;4000;12;\r\n",
            b"   ;Item B;2026-08-30T21:16:00;4000;12;\r\n",
            b"b#0;Item B;2026-08-30T21:16:00;4000;12;quase\r\n",
        ],
        ids=["total", "quantidade", "carimbo", "chave-vazia", "residuo"],
    )
    def test_a_rede_de_TIPO_pega_cada_campo_e_as_demais_carregam(
        self, tmp_path, caplog, corpo
    ):
        pasta = _fabricar(
            tmp_path / ".mercado",
            _cabecalho()
            + b"a#0;Item A;2026-08-30T21:15:00;6200;48;\r\n"
            + corpo
            + b"c#0;Item C;2026-08-30T21:17:00;4000;12;0\r\n",
        )
        with caplog.at_level("WARNING", logger=LOGGER):
            registro = RegistroDeObservacoes(pasta)

        assert registro.chaves == {("a#0", 6200, 48), ("c#0", 4000, 12)}
        assert "linha 3" in caplog.text
        assert registro.ligado is True

    def test_uma_linha_de_residuo_ZERO_carrega_normalmente(self, tmp_path):
        """`0` e valor legitimo — 'conferi e bateu' — e nao motivo de descarte."""
        pasta = _fabricar(
            tmp_path / ".mercado",
            _cabecalho() + b"a#0;Item A;2026-08-30T21:15:00;6200;48;0\r\n",
        )
        assert RegistroDeObservacoes(pasta).chaves == {("a#0", 6200, 48)}

    def test_linhas_em_BRANCO_no_meio_sao_ignoradas_sem_aviso(self, tmp_path, caplog):
        pasta = _fabricar(
            tmp_path / ".mercado",
            _cabecalho()
            + b"a#0;Item A;2026-08-30T21:15:00;6200;48;\r\n"
            + b"\r\n"
            + b"c#0;Item C;2026-08-30T21:17:00;4000;12;0\r\n",
        )
        with caplog.at_level("WARNING", logger=LOGGER):
            registro = RegistroDeObservacoes(pasta)
        assert registro.chaves == {("a#0", 6200, 48), ("c#0", 4000, 12)}
        assert not caplog.records


class TestAChaveRepetidaComNomeDiferente:
    """D-08: a escolha e ANUNCIADA, nunca calada. E a feature NAO desliga."""

    CORPO = (
        b"a#0;Item Alfa;2026-08-30T21:15:00;6200;48;\r\n"
        b"a#0;Item Beta;2026-08-30T21:16:00;6200;48;\r\n"
    )

    def test_sai_em_ERROR_nomeando_as_DUAS_linhas_e_os_DOIS_nomes(
        self, tmp_path, caplog
    ):
        """A chave E o conteudo — chave igual so pode significar que o ROTULO
        oscilou no OCR. Quem decide entre duas etiquetas e o usuario."""
        pasta = _fabricar(tmp_path / ".mercado", _cabecalho() + self.CORPO)

        with caplog.at_level("DEBUG", logger=LOGGER):
            registro = RegistroDeObservacoes(pasta)

        assert [r for r in caplog.records if r.levelname == "ERROR"], caplog.text
        assert "Item Alfa" in caplog.text
        assert "Item Beta" in caplog.text
        assert "linha 2" in caplog.text
        assert "linha 3" in caplog.text
        assert registro.chaves == {("a#0", 6200, 48)}

    def test_a_PRIMEIRA_e_a_mantida_e_a_mensagem_diz_isso(self, tmp_path, caplog):
        """A primeira e tambem a mais antiga."""
        pasta = _fabricar(tmp_path / ".mercado", _cabecalho() + self.CORPO)
        with caplog.at_level("ERROR", logger=LOGGER):
            RegistroDeObservacoes(pasta)
        assert "Item Alfa" in caplog.text
        assert "mantida" in caplog.text.lower()

    def test_a_feature_NAO_desliga_e_o_arquivo_continua_INTACTO(self, tmp_path):
        """O arquivo esta legivel; o que esta errado e uma etiqueta."""
        pasta = _fabricar(tmp_path / ".mercado", _cabecalho() + self.CORPO)
        antes = (pasta / ARQUIVO_DE_OBSERVACOES).read_bytes()

        registro = RegistroDeObservacoes(pasta)

        assert registro.ligado is True
        assert (pasta / ARQUIVO_DE_OBSERVACOES).read_bytes() == antes

    def test_chave_repetida_com_o_MESMO_nome_e_silenciosa(self, tmp_path, caplog):
        """Isso e so a mesma observacao duas vezes — nao ha etiqueta em disputa."""
        pasta = _fabricar(
            tmp_path / ".mercado",
            _cabecalho()
            + b"a#0;Item Alfa;2026-08-30T21:15:00;6200;48;\r\n"
            + b"a#0;Item Alfa;2026-08-30T21:16:00;6200;48;\r\n",
        )
        with caplog.at_level("ERROR", logger=LOGGER):
            registro = RegistroDeObservacoes(pasta)
        assert not caplog.records
        assert registro.chaves == {("a#0", 6200, 48)}


class TestALeituraNAO_ESCREVE:
    """T-03-01b por inspecao de AST, para um comentario nunca a satisfazer."""

    def test_o_modulo_nao_chama_truncate_em_lugar_nenhum(self):
        """As duas saidas recusadas do D-17, presas estruturalmente.

        (a) truncar a cauda apagaria bytes do usuario num caminho de LEITURA — e
        uma das duas hipoteses do proprio aviso e 'linha boa salva sem quebra
        final', entao apagaria dado bom em metade dos casos que a saida existe
        para tratar. (b) completar a cauda com uma quebra de linha e pior ainda:
        preserva a linha possivelmente truncada E a PROMOVE — na leitura
        seguinte ela passa nas duas redes por linha e vira observacao permanente.
        """
        from l2scanner import mercado_registro

        arvore = ast.parse(inspect.getsource(mercado_registro))
        chamadas = {
            no.func.attr
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
        }
        assert "truncate" not in chamadas, chamadas


# ===========================================================================
# A ESCRITA QUE NUNCA LEVANTA (PERS-03)
# ===========================================================================
#
# SO OS CENARIOS QUE A MEDICAO PROVOU REPRODUTIVEIS NO WINDOWS estao aqui:
# arquivo marcado somente-leitura (`PermissionError`, errno 13) e pasta
# removida depois do arranque (`FileNotFoundError`, errno 2).
#
# NAO USAR `os.chmod` SOBRE A PASTA — a medicao desta pesquisa mostrou que
# criar subpasta e criar arquivo dentro dela CONTINUAM FUNCIONANDO com o bit
# ligado no Windows, e um teste escrito assim passaria por acidente, provando
# nada. E a mesma familia do levantamento ja citado em `gravador.py:146-149`.

# O que morte, saida e ressurreicao tem em comum: elas continuam. A frase e
# conferida por substring porque ela E o PERS-03 escrito uma vez, no molde
# literal de `montar_gravador` (`__main__.py:255-258`).
A_PROMESSA = "morte, saida e ressurreicao"


def _travar(arquivo: Path) -> None:
    os.chmod(arquivo, stat.S_IREAD)


def _destravar(arquivo: Path) -> None:
    """Devolve a permissao para o `tmp_path` poder ser limpo."""
    if arquivo.exists():
        os.chmod(arquivo, stat.S_IWRITE | stat.S_IREAD)


class TestUmaFalhaDeDiscoDESLIGA_A_FEATURE_E_NAO_O_PRODUTO:
    """Disco cheio nao pode derrubar o scanner e matar os alertas da party."""

    def test_arquivo_somente_leitura_devolve_False_e_NAO_levanta(
        self, tmp_path, caplog
    ):
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)
        _travar(registro.arquivo)
        try:
            with caplog.at_level("DEBUG", logger=LOGGER):
                resultado = registro.registrar(_linha(), AGORA)
        finally:
            _destravar(registro.arquivo)

        assert resultado is False
        assert any(r.levelname == "ERROR" for r in caplog.records)

    def test_a_SEGUNDA_mensagem_diz_o_que_CONTINUA_funcionando(
        self, tmp_path, caplog
    ):
        """`error` e nao `warning`, pelo precedente explicito da casa: `warning`
        e linha descartada, `error` e feature desligada."""
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)
        _travar(registro.arquivo)
        try:
            with caplog.at_level("ERROR", logger=LOGGER):
                registro.registrar(_linha(), AGORA)
        finally:
            _destravar(registro.arquivo)

        assert A_PROMESSA in caplog.text
        assert len([r for r in caplog.records if r.levelname == "ERROR"]) == 2

    def test_apos_a_falha_ligado_e_FALSO_e_a_proxima_nao_repete_o_erro(
        self, tmp_path, caplog
    ):
        """Um retry por tick a 1 Hz encheria o log com o mesmo erro e daria ao
        usuario a impressao de que ainda esta gravando. Quem religa e o proximo
        arranque, depois de o usuario consertar o arquivo."""
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)
        _travar(registro.arquivo)
        try:
            with caplog.at_level("ERROR", logger=LOGGER):
                registro.registrar(_linha(), AGORA)
                erros_depois_da_primeira = len(caplog.records)
                assert registro.ligado is False

                assert registro.registrar(_linha(quantidade=7), AGORA) is False
                assert len(caplog.records) == erros_depois_da_primeira
        finally:
            _destravar(registro.arquivo)

    def test_a_chave_que_FALHOU_nao_entra_no_indice(self, tmp_path):
        """O indice e a promessa de "isto ja esta no disco".

        Uma chave la sem linha no arquivo bloquearia PARA SEMPRE a gravacao da
        observacao correta — seria a dedup trabalhando contra o proprio dado.
        """
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)
        _travar(registro.arquivo)
        try:
            registro.registrar(_linha(), AGORA)
        finally:
            _destravar(registro.arquivo)

        assert chave_da_observacao(_linha()) not in registro.chaves
        assert registro.chaves == set()

    def test_a_pasta_removida_DEPOIS_do_arranque_nao_levanta(self, tmp_path):
        """`FileNotFoundError` (errno 2) e subclasse de `OSError` — coberto."""
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)
        shutil.rmtree(pasta)

        assert registro.registrar(_linha(), AGORA) is False
        assert registro.ligado is False

    def test_o_que_foi_gravado_ANTES_da_falha_continua_no_arquivo_e_no_indice(
        self, tmp_path
    ):
        """Degradar a feature nao e perder o que ja estava bom."""
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)
        assert registro.registrar(_linha(quantidade=48), AGORA) is True
        gravado = registro.arquivo.read_bytes()

        _travar(registro.arquivo)
        try:
            assert registro.registrar(_linha(quantidade=7), AGORA) is False
        finally:
            _destravar(registro.arquivo)

        assert registro.arquivo.read_bytes() == gravado
        assert chave_da_observacao(_linha(quantidade=48)) in registro.chaves
        assert chave_da_observacao(_linha(quantidade=7)) not in registro.chaves

    def test_com_a_feature_desligada_o_disco_NEM_E_TOCADO(self, tmp_path):
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)
        registro.ligado = False

        assert registro.registrar(_linha(), AGORA) is False
        assert len(_linhas_cruas(pasta)) == 1  # so o cabecalho


class TestAsCapturasSaoESTREITAS:
    """A conferencia e por AST e nao por texto: um comentario nunca a invalida
    nem a satisfaz."""

    def _arvore(self):
        from l2scanner import mercado_registro

        return ast.parse(inspect.getsource(mercado_registro))

    def test_nao_ha_except_largo_em_lugar_nenhum(self):
        """O analog do `Gravador` usa `except Exception` e ele e largo DEMAIS
        para o que a medicao mostrou: os quatro modos de falha desta maquina —
        `PermissionError` (13) para somente-leitura e para nome ocupado por
        diretorio, `FileNotFoundError` (2) para pasta inexistente e
        `FileExistsError` (17, winerror 183) para `mkdir` sobre nome de arquivo
        — sao TODOS subclasses de `OSError`. Um `except OSError` cobre as
        quatro, e um `except Exception` esconderia um `AttributeError` de
        refactor como se fosse disco cheio.
        """
        maus = [
            tratador
            for no in ast.walk(self._arvore())
            if isinstance(no, ast.Try)
            for tratador in no.handlers
            if tratador.type is None
            or (
                isinstance(tratador.type, ast.Name)
                and tratador.type.id in ("Exception", "BaseException")
            )
        ]
        assert not maus, [t.lineno for t in maus]

    def test_nao_ha_sincronizacao_forcada_nem_reescrita_atomica_nem_relogio(self):
        """`fsync` foi medido em 432x o custo do `flush` e nao compra o modo de
        falha desta fase; `os.replace` perderia a sessao inteira num corte; e
        `datetime.now()` violaria o D-16, que manda o carimbo entrar por
        parametro."""
        chamadas = {
            no.func.attr
            for no in ast.walk(self._arvore())
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
        }
        assert chamadas.isdisjoint({"fsync", "replace", "now"}), chamadas


# ===========================================================================
# A METADE DE MONTAGEM (03-02): a porta de entrada que a casa exige
# ===========================================================================
#
# `import l2scanner.__main__` fica DENTRO de cada funcao de teste, e nao no topo
# do arquivo, pelo mesmo motivo de `tests/test_gravador_honesto.py:484`:
# importar o ponto de entrada declara consciencia de DPI e arrasta `cv2`, e a
# metade de cima deste arquivo prova justamente que o modulo de registro NAO faz
# isso. Um import no topo apagaria essa prova sem nenhum aviso.
#
# A FORMA DE FALHA PREFERIDA E O NOME OCUPADO POR ARQUIVO, com a justificativa
# copiada do analog: ela e deterministica em todo sistema operacional e nao
# depende de permissao, que varia entre maquinas. Onde a permissao e inevitavel
# — o unico arranque que PRECISA escrever — quem e marcado somente-leitura e o
# ARQUIVO e nunca a PASTA: a medicao desta pesquisa mostrou que o bit e inerte
# sobre pasta no Windows, e um teste escrito assim passaria por acidente.

# `__main__.py:152` nomeia o logger `"l2scanner"`, e nao `__name__`. Filtrar
# pelo NOME importa porque o modulo de registro TAMBEM grita por conta propria
# nos dois casos de contrato quebrado: sem o filtro, estes testes provariam a
# mensagem que o 03-01 escreveu em vez da que a montagem escreve.
LOGGER_DA_MONTAGEM = "l2scanner"


def _erros_da_montagem(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [
        r
        for r in caplog.records
        if r.levelno >= logging.ERROR and r.name == LOGGER_DA_MONTAGEM
    ]


class TestAMontagemDoRegistroDeMercado:
    """Tenta, degrada com log alto, devolve `None` — e o scanner sobe sempre.

    As cinco regras do padrao da casa (`montar_gravador`, `__main__.py:227-262`)
    estao cobertas aqui uma a uma: o `try` sobre o construtor INTEIRO (o teste
    do nome ocupado prova o `mkdir`), a captura estreita e nomeada, `error` e
    nao `warning`, as DUAS mensagens com a segunda dizendo o que continua, e o
    `return None` que nunca vira `raise`.
    """

    def test_uma_pasta_normal_devolve_o_registro_e_nao_grita(self, tmp_path, caplog):
        import l2scanner.__main__ as principal

        with caplog.at_level(logging.DEBUG, logger=LOGGER_DA_MONTAGEM):
            registro = principal.montar_registro_de_mercado(tmp_path / ".mercado")

        assert isinstance(registro, RegistroDeObservacoes)
        assert registro.arquivo.exists()
        assert not _erros_da_montagem(caplog), "o caminho feliz nao grita"

    def test_um_ARQUIVO_ocupando_o_nome_da_pasta_devolve_None(self, tmp_path, caplog):
        """O `mkdir` do construtor levanta `FileExistsError` (errno 17) FORA de
        qualquer rede — e o bug que `montar_gravador` foi escrito para consertar.

        Quem o defende e a montagem, envolvendo o construtor INTEIRO.
        """
        import l2scanner.__main__ as principal

        ocupado = tmp_path / ".mercado"
        ocupado.write_text("nao sou uma pasta", encoding="utf-8")

        with caplog.at_level(logging.ERROR, logger=LOGGER_DA_MONTAGEM):
            registro = principal.montar_registro_de_mercado(ocupado)

        assert registro is None, "o mercado desliga; o scanner segue"
        assert _erros_da_montagem(
            caplog
        ), "sair calado faria o usuario farmar uma sessao inteira sem dado"

    def test_a_SEGUNDA_mensagem_diz_o_que_CONTINUA_funcionando(self, tmp_path, caplog):
        """`error` e nao `warning`, e DUAS mensagens: a segunda E o PERS-03.

        A frase e a mesma de `montar_gravador` (`__main__.py:255-258`), e por
        isso e conferida por substring: ela nao e decoracao, e o requisito
        escrito uma vez.
        """
        import l2scanner.__main__ as principal

        ocupado = tmp_path / ".mercado"
        ocupado.write_text("nao sou uma pasta", encoding="utf-8")

        with caplog.at_level(logging.ERROR, logger=LOGGER_DA_MONTAGEM):
            principal.montar_registro_de_mercado(ocupado)

        erros = _erros_da_montagem(caplog)
        assert len(erros) == 2
        assert any("continua igual" in r.getMessage() for r in erros)
        assert any(A_PROMESSA in r.getMessage() for r in erros)

    def test_o_cabecalho_divergente_desliga_pela_MONTAGEM(self, tmp_path, caplog):
        """`ContratoDoArquivoQuebrado` NAO e `OSError`, e nao pode subir cru.

        Esta e a divergencia declarada com a regra 2 da casa: a captura ganha um
        segundo tipo NOMEADO. Sem ela, a excecao sobe do arranque como traceback
        cru — o modo de falha que a montagem existe para consertar.
        """
        import l2scanner.__main__ as principal

        pasta = _fabricar(tmp_path / ".mercado", b"chave;nome;preco\r\n")

        with caplog.at_level(logging.ERROR, logger=LOGGER_DA_MONTAGEM):
            registro = principal.montar_registro_de_mercado(pasta)

        assert registro is None
        assert _erros_da_montagem(caplog)

    def test_o_arquivo_SEM_QUEBRA_FINAL_desliga_e_o_disco_fica_INTOCADO(
        self, tmp_path, caplog
    ):
        """O SEGUNDO motivo de `ContratoDoArquivoQuebrado` (D-17).

        E o assert que importa nao e so o `None`: e que nenhum byte do arquivo
        do usuario mudou. A montagem nao repara, nao trunca e nao completa cauda.
        """
        import l2scanner.__main__ as principal

        pasta = _fabricar(
            tmp_path / ".mercado", _cabecalho() + LINHA_MEDIDA[: -len(b"\r\n")]
        )
        alvo = pasta / ARQUIVO_DE_OBSERVACOES
        antes = alvo.read_bytes()

        with caplog.at_level(logging.ERROR, logger=LOGGER_DA_MONTAGEM):
            registro = principal.montar_registro_de_mercado(pasta)

        assert registro is None
        assert _erros_da_montagem(caplog)
        assert alvo.read_bytes() == antes, "D-17: nenhum byte e tocado"

    def test_o_CSV_somente_leitura_no_arranque_que_PRECISA_escrever(
        self, tmp_path, caplog
    ):
        """ZERO BYTES mais somente-leitura: o unico arranque que ESCREVE.

        Com o arquivo cheio e valido o arranque so LE, e o bit seria inerte —
        mesma familia da armadilha do `chmod` sobre pasta. O arquivo de zero
        bytes e o estado em que o cabecalho precisa nascer, e e ai que o
        `PermissionError` (errno 13) tem o que impedir.
        """
        import l2scanner.__main__ as principal

        pasta = _fabricar(tmp_path / ".mercado", b"")
        alvo = pasta / ARQUIVO_DE_OBSERVACOES
        _travar(alvo)
        try:
            with caplog.at_level(logging.ERROR, logger=LOGGER_DA_MONTAGEM):
                registro = principal.montar_registro_de_mercado(pasta)
        finally:
            _destravar(alvo)

        assert registro is None
        assert _erros_da_montagem(caplog)

    def test_SEM_argumento_a_pasta_e_a_de_PRODUCAO_do_modulo_de_registro(
        self, tmp_path, monkeypatch
    ):
        """A pasta padrao e resolvida em tempo de CHAMADA, e nao de import.

        E isso que permite ao teste apontar para `tmp_path` sem nunca tocar a
        `.mercado/` real, que e dado acumulado e sem desfazer.
        """
        import l2scanner.__main__ as principal
        from l2scanner import mercado_registro

        producao = tmp_path / "producao" / ".mercado"
        monkeypatch.setattr(mercado_registro, "PASTA_DO_MERCADO", producao)

        registro = principal.montar_registro_de_mercado()

        assert registro is not None
        assert registro.arquivo == producao / ARQUIVO_DE_OBSERVACOES
        assert registro.arquivo.exists()
        assert registro.arquivo.is_relative_to(tmp_path)

    def test_a_assinatura_tem_pasta_OPCIONAL(self):
        import l2scanner.__main__ as principal

        parametros = inspect.signature(principal.montar_registro_de_mercado).parameters
        assert parametros["pasta"].default is None


class TestAMontagemNUNCA_LEVANTA:
    """Conferencia por AST: um comentario nunca a invalida nem a satisfaz."""

    def _arvore(self):
        import l2scanner.__main__ as principal

        return ast.parse(inspect.getsource(principal.montar_registro_de_mercado))

    def test_nao_ha_raise_em_lugar_nenhum_da_montagem(self):
        """A regra 5 do padrao: `return None`, nunca `raise`. O chamador da
        Fase 4 trata `None` como feature desligada."""
        levantamentos = [
            no for no in ast.walk(self._arvore()) if isinstance(no, ast.Raise)
        ]
        assert not levantamentos, [no.lineno for no in levantamentos]

    def test_a_captura_e_ESTREITA_e_os_dois_tipos_sao_NOMEADOS(self):
        """A divergencia com a regra 2 e de UM tipo a mais, nao de largura.

        `except Exception` esconderia um `AttributeError` de refactor futuro
        como se fosse disco cheio — o mesmo motivo pelo qual o modulo de
        registro recusou o `except Exception` do analog do `Gravador`.
        """
        maus = [
            tratador
            for no in ast.walk(self._arvore())
            if isinstance(no, ast.Try)
            for tratador in no.handlers
            if tratador.type is None
            or (
                isinstance(tratador.type, ast.Name)
                and tratador.type.id in ("Exception", "BaseException")
            )
        ]
        assert not maus, [t.lineno for t in maus]


class TestOAvisoALTO_CHEGA_AO_CONSOLE:
    """A metade do D-13 que o `caplog` nao ve.

    `caplog` prova que o `log.error` SAIU; ele nao prova que o usuario o LE.
    Esta classe fecha a outra metade: `configurar_log` instala um manipulador de
    fluxo sobre `sys.stdout` alem do arquivo rotativo, entao o aviso da montagem
    chega ao console E ao log sem nenhuma linha de codigo nova.
    """

    def test_configurar_log_instala_console_sobre_stdout_e_arquivo_rotativo(
        self, tmp_path, monkeypatch
    ):
        from logging.handlers import RotatingFileHandler

        import l2scanner.__main__ as principal

        monkeypatch.setattr(principal, "PASTA_LOGS", tmp_path / "logs")
        anteriores = list(principal.log.handlers)
        nivel = principal.log.level
        try:
            principal.configurar_log(verboso=False)
            instalados = principal.log.handlers

            arquivos = [h for h in instalados if isinstance(h, RotatingFileHandler)]
            consoles = [
                h
                for h in instalados
                if isinstance(h, logging.StreamHandler)
                and not isinstance(h, RotatingFileHandler)
                and getattr(h, "stream", None) is sys.stdout
            ]

            assert arquivos, "sem arquivo, um farm de tres horas morre calado"
            assert (
                consoles
            ), "sem console, 'avisar alto' seria so um arquivo que ninguem abre"
        finally:
            # Devolver o logger global exatamente como estava: um manipulador
            # sobrando faria os testes seguintes gravarem dentro de `tmp_path`.
            for manipulador in list(principal.log.handlers):
                if manipulador not in anteriores:
                    manipulador.close()
            principal.log.handlers[:] = anteriores
            principal.log.setLevel(nivel)


# ===========================================================================
# O LEIAME AO LADO DO DADO (03-02)
# ===========================================================================
#
# Ele e a saida (c) da pesquisa, e existe porque as outras duas foram RECUSADAS
# com motivo: uma linha de instrucao no topo do CSV quebraria o
# cabecalho-contrato e o Sheets a importaria como dado; uma coluna
# `total_exibido` seria dois campos para o mesmo fato, e cai na mesma objecao
# que derrubou a coluna do unitario.
#
# O TEXTO E CONFERIDO POR SUBSTRING, e nao por igualdade: o que estes testes
# prendem sao os FATOS que o usuario vai procurar seis meses depois — o
# separador, os centesimos, a diferenca entre a celula vazia e o zero, e a
# pergunta em aberto do sinal de mais. Reescrever a prosa em volta deles e
# livre; apagar um deles nao e.


def _leiame(pasta: Path) -> str:
    return (pasta / ARQUIVO_DO_LEIAME).read_text(encoding="utf-8")


class TestOLeiameNasceComAPastaEnUNCA_E_REESCRITO:
    def test_construir_numa_pasta_vazia_cria_o_leiame_ao_lado_do_csv(self, tmp_path):
        pasta = tmp_path / ".mercado"
        registro = RegistroDeObservacoes(pasta)

        assert (pasta / ARQUIVO_DO_LEIAME).exists()
        assert registro.arquivo.exists()

    def test_o_leiame_NAO_TOCA_o_csv_nem_o_cabecalho_contrato(self, tmp_path):
        """Ele nao entra na importacao: e um arquivo ao lado, nao uma linha
        dentro. Era essa a objecao que derrubou a saida (b) da pesquisa."""
        pasta = tmp_path / ".mercado"
        RegistroDeObservacoes(pasta)

        assert _linhas_cruas(pasta) == [SEPARADOR.join(COLUNAS)]

    def test_um_leiame_EDITADO_A_MAO_sobrevive_ao_proximo_arranque(self, tmp_path):
        """E um arquivo para humano, na pasta dele. Um programa que o
        reescrevesse a cada arranque apagaria a anotacao calado — a mesma
        familia de erro que o cabecalho-contrato existe para impedir do outro
        lado."""
        pasta = tmp_path / ".mercado"
        RegistroDeObservacoes(pasta)
        alvo = pasta / ARQUIVO_DO_LEIAME
        alvo.write_text("minha anotacao: conferir o +6 no Sheets\n", encoding="utf-8")
        antes = alvo.read_bytes()

        RegistroDeObservacoes(pasta)

        assert alvo.read_bytes() == antes

    def test_escrever_leiame_diz_se_ESCREVEU_ou_se_ja_havia_um(self, tmp_path):
        pasta = tmp_path / ".mercado"
        pasta.mkdir(parents=True)

        assert escrever_leiame(pasta) is True
        assert escrever_leiame(pasta) is False


class TestOTextoDoLeiameRESPONDE_SOZINHO:
    def test_ele_ensina_o_separador_PERSONALIZADO_do_dialogo_do_sheets(self, tmp_path):
        """O dialogo do Sheets oferece deteccao automatica, tabulacao, virgula e
        personalizado — e NAO tem preset de ponto e virgula. Quem procurar um
        vai perder tempo, entao o texto diz por extenso qual opcao usar."""
        pasta = tmp_path / ".mercado"
        RegistroDeObservacoes(pasta)
        texto = _leiame(pasta)

        assert '";"' in texto, "o separador tem de aparecer entre aspas"
        assert "personalizado" in texto.lower()
        assert "Importar" in texto, "o caminho pelo menu e o que abre o dialogo"

    def test_ele_explica_os_centesimos_com_o_exemplo_CONCRETO(self, tmp_path):
        pasta = tmp_path / ".mercado"
        RegistroDeObservacoes(pasta)
        texto = _leiame(pasta)

        assert "6200" in texto
        assert "62,00" in texto

    def test_ele_distingue_a_celula_VAZIA_do_ZERO_no_residuo(self, tmp_path):
        """As duas leituras por extenso: sao fatos diferentes, e uma planilha
        que os tratasse como o mesmo estaria somando leituras que nunca
        aconteceram."""
        pasta = tmp_path / ".mercado"
        RegistroDeObservacoes(pasta)
        texto = _leiame(pasta)

        assert "residuo_do_cruzamento" in texto
        assert "VAZIA" in texto
        assert "ZERO" in texto
        assert "nao deu para medir" in texto
        assert "conferi e bateu" in texto

    def test_ele_carrega_o_sinal_de_mais_como_PERGUNTA_EM_ABERTO(self, tmp_path):
        """Nao e defeito conhecido do arquivo: e uma suposicao NAO MEDIDA, e o
        conserto seria na planilha, nunca no dado."""
        pasta = tmp_path / ".mercado"
        RegistroDeObservacoes(pasta)
        texto = _leiame(pasta)

        assert "+6 Agathion" in texto
        assert "formula" in texto.lower()
