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

import csv
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from l2scanner.mercado_catalogo import PASTA_DO_MERCADO, SEPARADOR
from l2scanner.mercado_leitura import LinhaLida
from l2scanner.mercado_registro import (
    ARQUIVO_DE_OBSERVACOES,
    COLUNAS,
    RegistroDeObservacoes,
    campos_da_observacao,
    chave_da_observacao,
    chave_dos_campos,
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

    def test_o_catalogo_JA_traz_cv2_e_numpy_e_por_isso_o_criterio_original_caiu(self):
        """A medicao que derrubou o criterio, presa para nao se perder.

        Se um dia alguem aliviar a cadeia de `config` e este teste ficar
        vermelho, e boa noticia — e a hora de cobrar de volta a forma forte.
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
        assert saida.stdout.strip() == "True True"


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
