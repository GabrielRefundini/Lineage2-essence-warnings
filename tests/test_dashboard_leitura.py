"""A LEITURA AO VIVO DO CSV, e as TRES PROVAS que o DASH-01 cobra.

AS TRES PROVAS, E POR QUE CADA UMA PRECISA DE UM CONTROLE
==========================================================
1. **Somente leitura.** O `.mercado/observacoes.csv` e o dado do usuario, e este
   processo nao e o escritor dele. A prova e IMPRESSAO DIGITAL de tres
   componentes — `(st_size, st_mtime_ns, sha256)` — antes e depois de 300
   leituras, mais um TRIPWIRE por leitura de fonte que afirma a ausencia dos
   modos de escrita nas duas funcoes que tocam o disco. A impressao digital pega
   a escrita que aconteceu; o tripwire pega a que ainda nao aconteceu.

2. **A cauda cortada cai SOZINHA.** O escritor legitimo esta rodando no outro
   processo, e recusar o arquivo inteiro por causa de uma cauda de meio segundo
   apagaria o grafico da tela sem causa visivel. A degradacao correta e ler ate
   a ultima linha COMPLETA. Ela vem com CONTROLE NEGATIVO: um texto que termina
   em quebra de linha tem de reportar `cauda_incompleta` FALSO. Sem esse
   controle, um defeito que devolvesse `True` sempre deixaria os quatro casos de
   corte verdes.

3. **Uma linha ruim cai SOZINHA, e o log NOMEIA o numero dela.** A forense deste
   projeto acontece depois do farm, com o log na mao: "uma linha caiu" sem o
   numero nao conserta nada, porque o usuario nao acha a linha para editar no
   Sheets.

O QUE ESTE ARQUIVO **NAO** PROVA, E ISSO E DE PROPOSITO
=======================================================
Ele nao prova que a leitura parcial e FREQUENTE — porque ela nao e. Medido na
pesquisa desta fase: **ZERO** leituras sem terminador em **22.970** leituras de
cauda durante 200.000 appends concorrentes, com um controle positivo de
line-tearing deliberado acusando **3.252 de 4.079**. A sonda enxerga o defeito
quando ele existe; ela nao o viu porque ele nao acontece com este escritor. A
degradacao continua sendo REDE DE SEGURANCA — para o arquivo editado a mao no
Sheets e salvo sem quebra final, e para a queda de energia — e nao o caminho
normal. O numero mora tambem na docstring de `observacoes_ao_vivo`, ao lado do
codigo que ele explica.

NADA AQUI TOCA A `.mercado/` REAL, pela mesma razao escrita em
`tests/test_mercado_registro.py:1-11`: toda fixture mora em `tmp_path`. E o CSV
de fixture e montado A MAO, no molde de `tests/test_mercado_analise.py:283-300`,
porque o que se quer provar e a LEITURA — construir o arquivo com o escritor
faria o teste depender do escritor para julgar o leitor.
"""

from __future__ import annotations

import hashlib
import inspect
import logging
from pathlib import Path

import pytest

from l2scanner import dashboard_dados, mercado_registro
from l2scanner.mercado_catalogo import CHAVE_DA_SERIE_DA_ADENA, SEPARADOR

# O terminador que `csv.writer` emite, e por isso o que a fixture escreve. Ler um
# arquivo com `\n` puro esconderia a diferenca entre o que o escritor produz e o
# que o leitor aceita.
TERMINADOR = "\r\n"


# ---------------------------------------------------------------------------
# O CSV DE FIXTURE, MONTADO A MAO
# ---------------------------------------------------------------------------

LINHAS_DE_FIXTURE = (
    (CHAVE_DA_SERIE_DA_ADENA, "Adena", "2026-09-01T14:00:00", "11600", "10000000", "0"),
    (CHAVE_DA_SERIE_DA_ADENA, "Adena", "2026-09-01T14:05:00", "30000", "15000000", "0"),
    (CHAVE_DA_SERIE_DA_ADENA, "Adena", "2026-09-01T14:10:00", "12000", "10000000", "0"),
    ("common-aztac#0", "Common Aztac", "2026-09-01T13:00:00", "6200", "48", "0"),
)


def _texto_do_csv(linhas=LINHAS_DE_FIXTURE) -> str:
    """O texto exato do arquivo, com cabecalho e terminador em TODA linha."""
    montadas = [SEPARADOR.join(mercado_registro.COLUNAS)]
    montadas.extend(SEPARADOR.join(campos) for campos in linhas)
    return "".join(linha + TERMINADOR for linha in montadas)


def _escrever(arquivo: Path, texto: str) -> None:
    """`newline=""` obrigatorio: sem ele o Windows traduz `\\n` e o `\\r\\n` da
    fixture viraria `\\r\\r\\n`, que nao e o que o escritor produz."""
    arquivo.write_text(texto, encoding="utf-8", newline="")


def _ler(arquivo: Path) -> str:
    """O texto CRU, sem traducao de quebra de linha.

    `Path.read_text(newline="")` so existe a partir do 3.13, e esta arvore roda
    3.12 — dai o `open` explicito. Sem o `newline=""` o Python traduziria os
    `\\r\\n` da fixture para `\\n` na leitura, e os testes de corte estariam
    medindo o texto traduzido em vez do que esta no disco.
    """
    with arquivo.open("r", encoding="utf-8", newline="") as fonte:
        return fonte.read()


def _impressao_do_arquivo(caminho: Path) -> tuple[int, int, str]:
    """(tamanho, mtime_ns, sha256) — a impressao digital de UM arquivo.

    O MOLDE E DE `tests/test_mercado_firewall_de_fase.py:481`, e a razao dos TRES
    juntos e a mesma que esta escrita la: uma reescrita com bytes identicos nao
    muda o hash, e "escreveu por cima com o mesmo conteudo" continua sendo
    escrita — o `mtime_ns` pega esse caso; e o sha256 pega o caso em que o
    relogio do sistema de arquivos e grosso demais para separar duas escritas.
    """
    bruto = caminho.read_bytes()
    estado = caminho.stat()
    return (estado.st_size, estado.st_mtime_ns, hashlib.sha256(bruto).hexdigest())


@pytest.fixture
def arquivo(tmp_path: Path) -> Path:
    alvo = tmp_path / mercado_registro.ARQUIVO_DE_OBSERVACOES
    _escrever(alvo, _texto_do_csv())
    return alvo


# ---------------------------------------------------------------------------
# O PORTAO DE CONTRATO CONTINUA SENDO O MESMO
# ---------------------------------------------------------------------------


class TestOPortaoDeContratoEOMESMO:
    """O corte acontece ANTES do portao, e por isso o portao continua existindo.

    O texto entregue ao parser termina em quebra de linha POR CONSTRUCAO, entao
    `conferir_o_terminador` e chamada e passa; `conferir_o_cabecalho` e chamada e
    continua desligando alto. Nenhum dos dois foi afrouxado — o primeiro passou a
    julgar um texto de que a ambiguidade ja foi retirada.
    """

    def test_o_cabecalho_trocado_LEVANTA_nomeando_o_arquivo_REAL(
        self, arquivo: Path
    ) -> None:
        """A mensagem so serve se o usuario souber QUAL arquivo abrir.

        E o risco inteiro da rota escolhida na §2 do plano 01-01: um recorte
        feito por arquivo temporario faria o portao acusar um caminho em
        `AppData` que nao existe mais quando o usuario for procurar, e a
        instrucao ("restaure a primeira linha") viraria letra morta.
        """
        bruto = _ler(arquivo)
        linhas = bruto.split(TERMINADOR)
        linhas[0] = SEPARADOR.join(("chave", "nome", "quando", "total", "qtd", "res"))
        _escrever(arquivo, TERMINADOR.join(linhas))

        with pytest.raises(mercado_registro.ContratoDoArquivoQuebrado) as erro:
            dashboard_dados.observacoes_ao_vivo(arquivo)

        assert str(arquivo) in str(erro.value)

    def test_arquivo_ausente_devolve_leitura_VAZIA_sem_levantar(
        self, tmp_path: Path
    ) -> None:
        """A `.mercado/` nasce vazia, e "ainda nao gravaram nada" e resposta."""
        leitura = dashboard_dados.observacoes_ao_vivo(tmp_path / "nao-existe.csv")

        assert leitura.arquivo_ausente is True
        assert leitura.observacoes == []
        assert leitura.linhas_completas == 0

    def test_a_leitura_NAO_CRIA_o_arquivo_ausente(self, tmp_path: Path) -> None:
        """Criar aqui seria o programa ESCREVENDO num caminho de LEITURA.

        `RegistroDeObservacoes.carregar` cria o arquivo com cabecalho porque ela
        e o arranque do ESCRITOR. Esta funcao nao e, e um arquivo que aparece
        sozinho porque alguem abriu o dashboard e um efeito colateral que o
        usuario nao pediu — inclusive num diretorio que ele apontou por engano.
        """
        ausente = tmp_path / "nao-existe.csv"

        dashboard_dados.observacoes_ao_vivo(ausente)

        assert not ausente.exists()
        # E a PASTA tambem nao: o `tmp_path` fica com o que tinha, e nada mais.
        assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# A CAUDA INCOMPLETA CAI SOZINHA — COM CONTROLE NEGATIVO
# ---------------------------------------------------------------------------


class TestACaudaIncompletaCaiSOZINHA:
    """Os quatro cortes, mais o controle que impede o `True` constante de passar."""

    def test_arquivo_de_ZERO_BYTES_devolve_vazio_sem_levantar(
        self, tmp_path: Path
    ) -> None:
        """Nao ha byte do usuario para julgar, e tambem nao ha cauda."""
        vazio = tmp_path / mercado_registro.ARQUIVO_DE_OBSERVACOES
        _escrever(vazio, "")

        leitura = dashboard_dados.observacoes_ao_vivo(vazio)

        assert leitura.observacoes == []
        assert leitura.cauda_incompleta is False
        assert leitura.arquivo_ausente is False
        assert leitura.linhas_completas == 0

    def test_arquivo_SEM_NENHUMA_quebra_de_linha_nao_tem_nem_cabecalho(
        self, tmp_path: Path
    ) -> None:
        """Sem uma unica linha completa nao ha nem cabecalho a AFIRMAR.

        Julgar o cabecalho de uma linha que pode estar cortada no meio seria
        exatamente a ambiguidade que `conferir_o_terminador` existe para recusar:
        `adena` truncado de `adena#` passaria por um nome de coluna qualquer.
        """
        cortado = tmp_path / mercado_registro.ARQUIVO_DE_OBSERVACOES
        _escrever(cortado, SEPARADOR.join(mercado_registro.COLUNAS)[:20])

        leitura = dashboard_dados.observacoes_ao_vivo(cortado)

        assert leitura.observacoes == []
        assert leitura.cauda_incompleta is True
        assert leitura.linhas_completas == 0

    def test_o_corte_no_MEIO_da_ultima_linha_devolve_as_COMPLETAS(
        self, arquivo: Path
    ) -> None:
        antes = dashboard_dados.observacoes_ao_vivo(arquivo)
        bruto = _ler(arquivo)

        fim_da_penultima = bruto.rfind(TERMINADOR, 0, len(bruto) - len(TERMINADOR))
        fim_da_penultima += len(TERMINADOR)
        ultima = bruto[fim_da_penultima:]
        _escrever(arquivo, bruto[:fim_da_penultima] + ultima[: len(ultima) // 2])

        depois = dashboard_dados.observacoes_ao_vivo(arquivo)

        assert depois.cauda_incompleta is True
        assert len(depois.observacoes) == len(antes.observacoes) - 1
        assert depois.linhas_completas == len(LINHAS_DE_FIXTURE) - 1

    def test_CONTROLE_NEGATIVO_texto_terminado_em_quebra_tem_cauda_COMPLETA(
        self, arquivo: Path
    ) -> None:
        """O controle sem o qual os quatro cortes acima nao valem nada.

        Um defeito que devolvesse `cauda_incompleta=True` SEMPRE deixaria todos
        os testes de corte verdes e a tela permanentemente com a nota de linha
        ignorada — um aviso que nunca some vira ruido, e ruido e indistinguivel
        de defeito. Este teste e o que impede isso.
        """
        leitura = dashboard_dados.observacoes_ao_vivo(arquivo)

        assert _ler(arquivo).endswith(TERMINADOR)
        assert leitura.cauda_incompleta is False
        assert len(leitura.observacoes) == len(LINHAS_DE_FIXTURE)

    def test_linhas_completas_conta_o_DADO_e_nao_o_cabecalho(
        self, arquivo: Path
    ) -> None:
        """A contagem que alimenta a frase de prova do estado vazio.

        Ela conta LINHAS DE DADO, e nao linhas do arquivo, porque a frase que ela
        alimenta compara duas contagens do MESMO tipo — "N linhas, M da serie".
        Contar o cabecalho num lado e registros no outro seria comparar coisas
        diferentes com a mesma palavra.
        """
        leitura = dashboard_dados.observacoes_ao_vivo(arquivo)

        assert leitura.linhas_completas == len(LINHAS_DE_FIXTURE)
        assert len(_ler(arquivo).splitlines()) == len(LINHAS_DE_FIXTURE) + 1


# ---------------------------------------------------------------------------
# UMA LINHA RUIM CAI SOZINHA, E O AVISO NOMEIA O NUMERO DELA
# ---------------------------------------------------------------------------


class TestUmaLinhaRuimCaiSOZINHA:
    """D-14 herdado por CHAMADA, e nao reimplementado.

    O aviso vem de `mercado_registro.observacoes_do_arquivo` — o dashboard nao
    inventa outro nivel de log nem outra frase. Se ele inventasse, existiriam
    duas descricoes da mesma linha descartada, e uma delas ficaria para tras no
    primeiro ajuste.
    """

    @pytest.fixture
    def com_linha_ruim(self, tmp_path: Path) -> Path:
        ruim = (
            CHAVE_DA_SERIE_DA_ADENA,
            "Adena",
            "2026-09-01T14:20:00",
            "9000",
            "muitas",  # quantidade que nao e inteiro
            "0",
        )
        linhas = LINHAS_DE_FIXTURE[:2] + (ruim,) + LINHAS_DE_FIXTURE[2:]
        alvo = tmp_path / mercado_registro.ARQUIVO_DE_OBSERVACOES
        _escrever(alvo, _texto_do_csv(linhas))
        return alvo

    def test_o_aviso_NOMEIA_o_numero_da_linha_descartada(
        self, com_linha_ruim: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Sem o numero, o usuario nao acha a linha para consertar no Sheets."""
        caplog.set_level(logging.WARNING, logger=mercado_registro.log.name)

        dashboard_dados.observacoes_ao_vivo(com_linha_ruim)

        avisos = [
            registro.getMessage()
            for registro in caplog.records
            if registro.levelno == logging.WARNING
        ]
        assert avisos, "a linha ruim caiu em SILENCIO — e isso e repudio (T-01-07)"
        # A linha ruim e a 4a do arquivo: cabecalho + duas boas + ela.
        assert any("linha 4" in aviso for aviso in avisos), avisos

    def test_as_demais_linhas_carregam_NORMALMENTE(
        self, com_linha_ruim: Path
    ) -> None:
        """Uma linha ruim nunca condena o arquivo inteiro."""
        leitura = dashboard_dados.observacoes_ao_vivo(com_linha_ruim)

        assert len(leitura.observacoes) == len(LINHAS_DE_FIXTURE)
        # A contagem de linhas conta a RUIM tambem: ela esta no arquivo, e a
        # frase de prova fala do arquivo, nao do que sobreviveu ao parser.
        assert leitura.linhas_completas == len(LINHAS_DE_FIXTURE) + 1


# ---------------------------------------------------------------------------
# A LEITURA NAO ESCREVE NADA — IMPRESSAO DIGITAL E TRIPWIRE
# ---------------------------------------------------------------------------

# Os modos de abertura que este modulo NAO pode conter. Escritos com as aspas
# incluidas de proposito: procurar so a letra acusaria qualquer palavra que a
# contivesse, e um tripwire que acusa sozinho e um tripwire que alguem apaga.
MODOS_DE_ESCRITA = ('"w"', "'w'", '"a"', "'a'", '"r+"', "'r+'", '"x"', "'x'")


class TestALeituraNaoEscreveNADA:
    """T-01-04: o CSV e do usuario, e este processo so LE.

    DUAS PROVAS, E NAO UMA. A impressao digital prova o que aconteceu nesta
    arvore, hoje; o tripwire por leitura de fonte prova o que o codigo PODE
    fazer, e pega a regressao no commit em que ela e escrita, antes de existir um
    caso de teste que a exercite.
    """

    def test_TREZENTAS_leituras_nao_mudam_um_BYTE_do_arquivo(
        self, arquivo: Path
    ) -> None:
        """Trezentas, e nao uma: uma abertura em `r+` por engano pode nao mudar
        nada na primeira passada e truncar na centesima."""
        antes = _impressao_do_arquivo(arquivo)

        for _ in range(300):
            dashboard_dados.observacoes_ao_vivo(arquivo)

        assert _impressao_do_arquivo(arquivo) == antes

    def test_o_fonte_de_observacoes_ao_vivo_nao_tem_MODO_DE_ESCRITA(self) -> None:
        fonte = inspect.getsource(dashboard_dados.observacoes_ao_vivo)

        for modo in MODOS_DE_ESCRITA:
            assert modo not in fonte, modo
        assert "mkdir" not in fonte
        # CONTROLE: o tripwire so vale se ele estiver olhando para um fonte que
        # de fato abre arquivo. Sem isto, renomear a funcao deixaria a assercao
        # verde sobre uma cadeia de caracteres vazia.
        assert '"r"' in fonte

    def test_o_fonte_de_ArquivoRecortado_open_nao_tem_MODO_DE_ESCRITA(self) -> None:
        """O adaptador e a OUTRA porta para o disco, e por isso ele tambem.

        Ele nao abre arquivo nenhum hoje — devolve um `StringIO` sobre texto ja
        lido. O tripwire existe para o dia em que alguem "otimizar" o adaptador
        para ler direto do disco e escolher o modo errado.
        """
        fonte = inspect.getsource(dashboard_dados.ArquivoRecortado.open)

        for modo in MODOS_DE_ESCRITA:
            assert modo not in fonte, modo
        assert "mkdir" not in fonte

    def test_a_NOTA_DE_LINHA_PARCIAL_e_do_PYTHON_e_chega_pronta(self) -> None:
        """A frase e constante nomeada, e nao literal solto no corpo.

        Reacentua-la ou reescreve-la no navegador seria o SEGUNDO formatador que
        o DASH-03 recusa: as duas copias divergiriam no primeiro ajuste, e
        ninguem perceberia que havia duas.
        """
        assert isinstance(dashboard_dados.NOTA_DE_LINHA_PARCIAL, str)
        assert "incompleta" in dashboard_dados.NOTA_DE_LINHA_PARCIAL
