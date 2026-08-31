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
    ContratoDoArquivoQuebrado,
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
