"""As costuras da ferramenta de replay que produz o `observacoes.csv` do portao.

O QUE ESTE ARQUIVO NAO FAZ, E POR QUE
======================================
Ele NAO toca `recordings/`, NAO chama o motor de OCR e NAO roda a varredura do
censo. As tres coisas andam juntas: a varredura passa de dez minutos, precisa do
`calibration.json` da maquina do usuario e do motor de OCR do `.venv`, e nenhum
dos dois vem de clone limpo. Um teste que dependesse deles ficaria verde nesta
maquina e amarelo em toda outra — e a mesma disciplina ja escrita em
`tests/test_medir_brilho_da_quantidade.py`.

O que da para provar aqui e o que a ferramenta tem de proprio: a COSTURA DE
GRAVACAO (paginas aceitas -> registro em disco), a GUARDA DA SAIDA (a pasta de
producao recusada por caminho resolvido) e o CAMINHO DE FALHA (a saida quebrada
de proposito virando aviso alto e codigo diferente de zero). As paginas sao
construidas a mao e o registro mora em `tmp_path`.

A VARREDURA DE VERDADE E DO USUARIO, no portao humano de fim de fase, no
checkout PRINCIPAL. Ela nao e gate de teste nenhum daqui.
"""

from __future__ import annotations

import ast
import csv
import importlib.util
import inspect
import logging
import os
import sys
from pathlib import Path

import pytest

from l2scanner.mercado_catalogo import SEPARADOR
from l2scanner.mercado_leitura import LinhaLida
from l2scanner.mercado_pagina import PaginaAceita

RAIZ = Path(__file__).resolve().parent.parent
CALIBRACAO_DE_FIXTURE = RAIZ / "tests" / "fixtures" / "mercado" / "calibracao_de_fixture.json"

# O logger que a montagem do 03-02 usa. Filtrar por NOME e obrigatorio: o
# `mercado_registro` grita no logger dele sobre o MESMO evento, e sem o filtro o
# assert provaria a mensagem da camada errada (03-02, padrao estabelecido).
LOGGER_DA_MONTAGEM = "l2scanner"
A_PROMESSA = "morte, saida e ressurreicao"


def _carregar_a_ferramenta(nome: str):
    """`tools/` nao e pacote, entao o import vem do caminho do arquivo."""
    caminho = RAIZ / "tools" / (nome + ".py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    assert spec and spec.loader, f"nao carreguei {caminho}"
    modulo = importlib.util.module_from_spec(spec)
    # Registrar ANTES de executar: `@dataclass` resolve as anotacoes por
    # `sys.modules[cls.__module__]`, e sem isto ele encontra None.
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


ferramenta = _carregar_a_ferramenta("gerar_observacoes_do_censo")

# O MODULO DO CENSO, CAPTURADO NO INSTANTE EM QUE A FERRAMENTA O REGISTROU.
#
# A identidade so vale contra o objeto que o proprio `_carregar_o_censo` da
# ferramenta pos em `sys.modules` — e ler `sys.modules["medir_oclusao"]` mais
# tarde NAO serve: `tests/test_medir_brilho_da_quantidade.py` e as irmas dele
# carregam a mesma ferramenta na mesma sessao, rodam o proprio
# `_carregar_o_censo`, e a entrada passa a apontar para um SEGUNDO objeto com o
# mesmo conteudo. Lendo la na hora do teste, a identidade falharia sobre codigo
# CORRETO, e so quando os arquivos rodassem juntos — o pior tipo de teste
# amarelo, porque ele passa isolado.
CENSO_DA_FERRAMENTA = sys.modules["medir_oclusao"]


# ---------------------------------------------------------------------------
# As paginas construidas a mao — nenhum pixel, nenhum OCR
# ---------------------------------------------------------------------------


def linha(
    indice: int = 0,
    chave: str = "agathion-alpha",
    nome: str = "+6 Agathion Alpha Hunter Sealed",
    total: int = 6200,
    quantidade: int = 1,
    residuo: int | None = 0,
) -> LinhaLida:
    return LinhaLida(
        indice=indice,
        chave_da_serie=chave,
        nome_exibido=nome,
        total_em_centesimos=total,
        quantidade=quantidade,
        serie_nova=False,
        residuo_do_cruzamento=residuo,
    )


def pagina(*linhas: LinhaLida) -> PaginaAceita:
    return PaginaAceita(linhas=tuple(linhas))


@pytest.fixture()
def registro(tmp_path):
    """Um registro de verdade, em `tmp_path` — nunca a `.mercado/` do usuario."""
    from l2scanner.mercado_registro import RegistroDeObservacoes

    return RegistroDeObservacoes(tmp_path / ".mercado")


class RelogioFixo:
    """O carimbo por parametro, sem depender do relogio da maquina no teste."""

    def __init__(self, momento) -> None:
        self._momento = momento

    def agora(self):
        return self._momento


@pytest.fixture()
def relogio():
    from datetime import datetime

    return RelogioFixo(datetime(2026, 8, 31, 10, 30, 0))


def linhas_do_arquivo(registro) -> list[list[str]]:
    with registro.arquivo.open("r", encoding="utf-8", newline="") as fonte:
        return list(csv.reader(fonte, delimiter=SEPARADOR))


# ===========================================================================
# TASK 1 — A COSTURA DE GRAVACAO
# ===========================================================================


class TestACosturaDeGravacao:
    """Paginas aceitas entram, linhas de CSV saem, e a contagem nao mente."""

    def test_duas_paginas_IDENTICAS_dao_uma_observacao_e_uma_duplicada(
        self, registro, relogio
    ) -> None:
        """A dedup do 03-01 vista de fora, pela costura que a ferramenta usa.

        Duas paginas identicas na MESMA chamada e o caso real: o leitor aceita
        uma pagina por par de frames concordantes, e uma grade parada produz a
        mesma pagina tick apos tick.
        """
        antes = len(linhas_do_arquivo(registro))

        contagem = ferramenta.gravar_as_paginas(
            [pagina(linha()), pagina(linha())], registro, relogio
        )

        assert contagem.observacoes == 1, contagem
        assert contagem.duplicadas == 1, contagem
        assert contagem.perdidas == 0, contagem
        assert len(linhas_do_arquivo(registro)) == antes + 1

    def test_a_contagem_de_SERIES_DISTINTAS_conta_serie_e_nao_linha(
        self, registro, relogio
    ) -> None:
        """Duas observacoes da MESMA serie sao uma serie so.

        Sem isto o relatorio diria "12 series" onde ha 12 precos do mesmo item,
        e o usuario compararia esse numero com o catalogo de nomes da Fase 2 —
        que conta serie — e acharia um desencontro que nao existe.
        """
        contagem = ferramenta.gravar_as_paginas(
            [
                pagina(
                    linha(indice=0, total=6200),
                    linha(indice=1, total=7100),
                    linha(indice=2, chave="cristal-b", total=900),
                )
            ],
            registro,
            relogio,
        )

        assert contagem.observacoes == 3, contagem
        assert len(contagem.series) == 2, contagem.series

    def test_a_costura_rodada_DUAS_VEZES_nao_aumenta_as_linhas_do_arquivo(
        self, registro, relogio
    ) -> None:
        """PERS-02 pela porta da ferramenta — e a prova de campo do criterio 3.

        E exatamente o que o passo 6 do roteiro humano manda o usuario contar:
        a mesma ferramenta, a mesma saida, o mesmo subconjunto, e o arquivo com
        o mesmo numero de linhas.
        """
        paginas = [pagina(linha(indice=0, total=6200), linha(indice=1, total=7100))]

        primeira = ferramenta.gravar_as_paginas(paginas, registro, relogio)
        depois_da_primeira = len(linhas_do_arquivo(registro))

        segunda = ferramenta.gravar_as_paginas(paginas, registro, relogio)

        assert primeira.observacoes == 2, primeira
        assert segunda.observacoes == 0, segunda
        assert segunda.duplicadas == 2, segunda
        assert len(linhas_do_arquivo(registro)) == depois_da_primeira

    def test_uma_SESSAO_NOVA_sobre_o_mesmo_arquivo_tambem_nao_duplica(
        self, tmp_path, relogio
    ) -> None:
        """O indice reconstruido do disco, que e o que a segunda RODADA usa.

        A ferramenta e um processo que abre e fecha: entre a primeira e a
        segunda execucao nao sobra indice em memoria nenhum. O que impede a
        duplicata e o `carregar` do arranque, e e ele que este teste exercita.
        """
        from l2scanner.mercado_registro import RegistroDeObservacoes

        pasta = tmp_path / ".mercado"
        paginas = [pagina(linha())]

        primeiro = RegistroDeObservacoes(pasta)
        ferramenta.gravar_as_paginas(paginas, primeiro, relogio)
        depois_da_primeira = len(linhas_do_arquivo(primeiro))

        segundo = RegistroDeObservacoes(pasta)
        contagem = ferramenta.gravar_as_paginas(paginas, segundo, relogio)

        assert contagem.observacoes == 0, contagem
        assert contagem.duplicadas == 1, contagem
        assert len(linhas_do_arquivo(segundo)) == depois_da_primeira

    def test_a_costura_le_SO_as_linhas_e_nunca_as_descartadas(
        self, registro, relogio
    ) -> None:
        """`descartadas` e `motivos` sao proibidos no CSV pela decisao da Fase 2.

        Escrever a linha recusada misturaria descarte com dado, que e a confusao
        que a falha fechada existe para evitar. Uma pagina com descartes e ZERO
        linhas nao pode produzir linha nenhuma.
        """
        so_descartes = PaginaAceita(
            linhas=(), descartadas=(3, 4), motivos=("faixa-cinzenta", "coberta")
        )

        contagem = ferramenta.gravar_as_paginas([so_descartes], registro, relogio)

        assert contagem.observacoes == 0, contagem
        assert contagem.duplicadas == 0, contagem
        assert len(linhas_do_arquivo(registro)) == 1, "so o cabecalho"

    def test_o_registro_DESLIGADO_conta_perdida_e_nunca_duplicada(
        self, registro, relogio
    ) -> None:
        """Uma feature morta no meio da rodada nao pode se disfarcar de dedup.

        `registrar` devolve `False` nos DOIS casos — chave repetida e registro
        desligado — e somar os dois num contador so faria o relatorio dizer
        "descartei 300 duplicadas" sobre uma sessao em que o disco encheu.
        """
        registro.ligado = False

        contagem = ferramenta.gravar_as_paginas([pagina(linha())], registro, relogio)

        assert contagem.observacoes == 0, contagem
        assert contagem.duplicadas == 0, contagem
        assert contagem.perdidas == 1, contagem


class TestOConjuntoDeMEDICAOEFechado:
    """A lista das 8 vem importada, nunca redigitada e nunca de um glob."""

    def test_a_lista_da_ferramenta_e_a_MESMA_TUPLA_das_ferramentas_de_medicao(
        self,
    ) -> None:
        """Identidade de objeto, e nao igualdade de conteudo.

        Igualdade passaria sobre uma lista redigitada que por acaso bate hoje —
        e e justamente amanha, quando uma das duas mudar, que a guarda importa.
        """
        assert (
            ferramenta.GRAVACOES_DO_CENSO is CENSO_DA_FERRAMENTA.GRAVACOES_DO_CENSO
        ), "a lista tem de ser a MESMA tupla, nao uma copia"

    def test_sao_oito_gravacoes_e_nenhuma_delas_e_a_pre_voo(self) -> None:
        """O numero do censo da pesquisa, e a pasta que um glob arrastaria.

        A `pre-voo` sozinha tem 1.502 PNGs de outro dia e dominaria qualquer
        distribuicao; ela e o motivo de a lista ser NOMEADA.
        """
        assert len(ferramenta.GRAVACOES_DO_CENSO) == 8
        assert not any("pre-voo" in n for n in ferramenta.GRAVACOES_DO_CENSO)


class TestAsSaidasDeErroLegiveis:
    """Ninguem ve traceback: cada recusa tem codigo proprio e frase inteira."""

    def test_uma_pasta_de_gravacoes_AUSENTE_sai_diferente_de_zero(
        self, tmp_path, capsys
    ) -> None:
        codigo = ferramenta.main(
            [
                "--gravacoes",
                str(tmp_path / "nao-existe"),
                "--saida",
                str(tmp_path / "rascunho"),
            ]
        )

        assert codigo != 0
        assert "nao e um diretorio" in capsys.readouterr().out

    def test_uma_pasta_do_CENSO_ausente_sai_diferente_de_zero(
        self, tmp_path, capsys
    ) -> None:
        """Uma pasta so, sem as outras sete: medir sobre um conjunto diferente
        do censo produz um numero que nao se compara com nada deste projeto."""
        gravacoes = tmp_path / "recordings"
        (gravacoes / ferramenta.GRAVACOES_DO_CENSO[0]).mkdir(parents=True)

        codigo = ferramenta.main(
            [
                "--gravacoes",
                str(gravacoes),
                "--saida",
                str(tmp_path / "rascunho"),
            ]
        )

        assert codigo != 0
        assert "AUSENTE" in capsys.readouterr().out

    def test_um_SUBCONJUNTO_fora_do_censo_e_recusado(self, tmp_path, capsys) -> None:
        """O argumento de atalho nao pode virar a porta dos fundos do glob."""
        gravacoes = tmp_path / "recordings"
        for nome in ferramenta.GRAVACOES_DO_CENSO:
            (gravacoes / nome).mkdir(parents=True)
        (gravacoes / "pre-voo").mkdir()

        codigo = ferramenta.main(
            [
                "--gravacoes",
                str(gravacoes),
                "--saida",
                str(tmp_path / "rascunho"),
                "--gravacao",
                "pre-voo",
            ]
        )

        assert codigo != 0
        assert "fora do censo" in capsys.readouterr().out

    def test_a_SAIDA_e_obrigatoria_e_nao_tem_padrao(self, tmp_path) -> None:
        """Sem padrao de proposito: o padrao seria a pasta de producao, e uma
        linha de replay carrega o carimbo de agora sobre preco de dias atras."""
        with pytest.raises(SystemExit):
            ferramenta.main(["--gravacoes", str(tmp_path)])


class TestAsCosturasDoModulo:
    """As afirmacoes estruturais que um comentario nunca pode invalidar."""

    def test_main_recebe_argv(self) -> None:
        parametros = inspect.signature(ferramenta.main).parameters
        assert "argv" in parametros, parametros

    def test_a_ferramenta_nao_chama_o_relogio_do_sistema(self) -> None:
        """D-16 preso por AST, e nao por leitura.

        O carimbo vem de `Relogio.agora()`. Um `datetime.now()` solto voltaria a
        por no arquivo a hora crua do Windows — que num dual boot esta errada, e
        e o defeito que o relogio ancorado do projeto existe para consertar.
        """
        arvore = ast.parse(inspect.getsource(ferramenta))
        chamadas = {
            no.func.attr
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
        }
        assert "now" not in chamadas, chamadas
        assert "agora" in chamadas, chamadas

    def test_a_ferramenta_nao_acrescenta_flag_ao_scanner(self) -> None:
        """Ela e de bancada, e o scanner nao sabe que ela existe.

        ATUALIZADO NA FASE 4. A forma original tambem afirmava que
        `"--mercado"` NAO aparecia no `__main__.py`, porque quando ela foi
        escrita o modo era DETC-02 e ainda nao existia. Ele existe agora
        (04-01), entao aquela metade virou uma afirmacao sobre o calendario e
        nao sobre a ferramenta - e foi trocada pelo que ela sempre quis dizer:
        a flag, quando nascesse, nasceria do modo de mercado e NUNCA desta
        ferramenta de bancada.

        A conferencia e sobre o FONTE do scanner, e nao sobre a arvore de
        trabalho, que pode estar suja de outro plano ou de outro workstream.
        """
        principal = (RAIZ / "l2scanner" / "__main__.py").read_text(encoding="utf-8")
        assert "gerar_observacoes_do_censo" not in principal
        assert "razao_para_recusar_a_saida" not in principal
        # A flag existe, e ela desce para o LACO DE PRODUCAO. Se um dia ela
        # chamar a ferramenta de bancada, este teste cai.
        assert '"--mercado"' in principal
        assert "mercado_modo" in principal

    def test_a_ferramenta_continua_exigindo_a_propria_saida(self) -> None:
        """A guarda que o `--mercado` NAO pode ter, e por isso ela e daqui.

        `--saida` sem padrao existe para impedir que uma linha derivada de
        replay entre na `.mercado/` com carimbo de agora sobre um preco visto
        dias atras. O modo ao vivo nao ganha flag de destino nenhuma, senao a
        mesma protecao seria furada pelo outro lado.
        """
        modo = (RAIZ / "l2scanner" / "mercado_modo.py").read_text(encoding="utf-8")
        assert "add_argument" not in modo
        assert "--saida" in inspect.getsource(ferramenta)


# ===========================================================================
# TASK 2 — AS GUARDAS DA SAIDA E O CAMINHO DE FALHA
# ===========================================================================


@pytest.fixture()
def censo_vazio(tmp_path):
    """As 8 pastas do censo, VAZIAS — a fiacao minima para `main` chegar longe.

    Sem imagem nenhuma: estes testes provam as GUARDAS, e uma guarda que so
    dispara depois de dez minutos de varredura nao seria guarda.
    """
    gravacoes = tmp_path / "recordings"
    for nome in ferramenta.GRAVACOES_DO_CENSO:
        (gravacoes / nome).mkdir(parents=True)
    return gravacoes


@pytest.fixture()
def ocr_fingido(monkeypatch):
    """O motor de OCR nao e o assunto destes testes, e nao vem de clone limpo."""
    monkeypatch.setattr(ferramenta.ocr, "disponivel", lambda: True)


@pytest.fixture()
def sem_instalar_log(monkeypatch):
    """`configurar_log` de verdade acrescenta manipuladores ao logger do projeto
    a cada chamada, e escreve em `logs/scanner.log`. Nestes testes ele e um
    no-op; que ele E CHAMADO, e em que ordem, tem teste proprio."""
    monkeypatch.setattr(ferramenta, "configurar_log", lambda verboso: None)


def _grafias_do_mesmo_caminho(pasta: Path) -> dict[str, str]:
    """As tres formas de escrever a MESMA pasta que o Windows aceita."""
    return {
        "separador-trocado": str(pasta).replace(os.sep, "/"),
        "caixa-trocada": str(pasta).upper(),
        "com-dotdot": str(pasta.parent / "outra" / ".." / pasta.name),
    }


class TestAGuardaDaSaida:
    """A pasta de producao e recusada por caminho RESOLVIDO, nunca por texto."""

    @pytest.mark.parametrize(
        "grafia",
        ["separador-trocado", "caixa-trocada", "com-dotdot"],
    )
    def test_a_pasta_de_PRODUCAO_e_recusada_em_qualquer_grafia(
        self, grafia, tmp_path, monkeypatch, capsys
    ) -> None:
        """No Windows a mesma pasta chega escrita de tres jeitos.

        Uma comparacao de STRING aprovaria dois deles — e uma linha derivada de
        replay carrega o carimbo de agora sobre um preco visto dias atras. O
        registro de producao e dado acumulado e sem desfazer.

        A caixa trocada e um fato do WINDOWS: em sistema de arquivos sensivel a
        caixa `.MERCADO` E outra pasta, e afirmar a recusa la seria afirmar uma
        mentira. Por isso `os.path.normcase`, que e no-op fora do Windows.
        """
        if grafia == "caixa-trocada" and os.name != "nt":
            pytest.skip("caixa insensivel e fato do Windows, nao do POSIX")

        producao = tmp_path / ".mercado"
        monkeypatch.setattr(ferramenta, "PASTA_DO_MERCADO", producao)

        codigo = ferramenta.main(
            [
                "--gravacoes",
                str(tmp_path),
                "--saida",
                _grafias_do_mesmo_caminho(producao)[grafia],
            ]
        )

        assert codigo != 0
        assert not producao.exists(), "a guarda tem de vir ANTES de qualquer mkdir"
        saiu = capsys.readouterr().out
        assert "RECUSADA" in saiu
        assert "carimbo" in saiu, "a mensagem diz a razao inteira, nao so 'recusado'"

    def test_uma_saida_DENTRO_da_pasta_de_producao_tambem_e_recusada(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        """Uma subpasta de `.mercado/` continua sendo a pasta do usuario.

        Recusar so a raiz deixaria `--saida .mercado/rascunho` passar, e o
        proximo arranque do registro leria aquela pasta como se fosse dela.
        """
        producao = tmp_path / ".mercado"
        monkeypatch.setattr(ferramenta, "PASTA_DO_MERCADO", producao)

        codigo = ferramenta.main(
            [
                "--gravacoes",
                str(tmp_path),
                "--saida",
                str(producao / "rascunho"),
            ]
        )

        assert codigo != 0
        assert not producao.exists()
        assert "RECUSADA" in capsys.readouterr().out

    def test_a_pasta_de_producao_REAL_e_recusada(self, capsys) -> None:
        """Sem monkeypatch nenhum: a `.mercado/` de verdade deste checkout.

        Os testes acima usam uma producao fingida para poder afirmar que NADA
        foi criado. Este afirma que o alvo de verdade tambem esta coberto — sem
        ele, a guarda poderia estar comparando contra a constante errada.
        """
        from l2scanner.mercado_registro import PASTA_DO_MERCADO

        assert ferramenta.razao_para_recusar_a_saida(PASTA_DO_MERCADO) is not None
        assert (
            ferramenta.razao_para_recusar_a_saida(PASTA_DO_MERCADO / "rascunho")
            is not None
        )
        assert capsys.readouterr().out == "", "a guarda pura nao imprime"

    def test_uma_pasta_de_rascunho_qualquer_NAO_e_recusada(self, tmp_path) -> None:
        """A guarda que recusa tudo seria uma ferramenta que nao roda."""
        assert ferramenta.razao_para_recusar_a_saida(tmp_path / "portao") is None


class TestOCaminhoDeFalhaQueOUsuarioVE:
    """PERS-03 pela unica porta que existe nesta fase: a ferramenta de bancada.

    O mercado ainda nao tem chamador no scanner, entao "a feature desligou e os
    alertas continuam" nao tem onde acontecer. O que da para ver e a outra
    metade — o aviso alto, com o texto EXATO que a Fase 4 vai mostrar.
    """

    def test_um_ARQUIVO_ocupando_o_nome_da_saida_desliga_alto_sem_traceback(
        self, tmp_path, censo_vazio, ocr_fingido, sem_instalar_log, caplog, capsys
    ) -> None:
        """O `mkdir` do construtor levanta `FileExistsError` (errno 17, medido).

        Quem o defende e a montagem do 03-02. A ferramenta so precisa nao
        atrapalhar: nada de traceback, e codigo diferente de zero.
        """
        ocupado = tmp_path / "portao-quebrado"
        ocupado.write_text("nao sou uma pasta", encoding="utf-8")

        with caplog.at_level(logging.ERROR, logger=LOGGER_DA_MONTAGEM):
            codigo = ferramenta.main(
                [
                    "--gravacoes",
                    str(censo_vazio),
                    "--calibracao",
                    str(CALIBRACAO_DE_FIXTURE),
                    "--saida",
                    str(ocupado),
                ]
            )

        assert codigo != 0
        erros = [
            r
            for r in caplog.records
            if r.levelno >= logging.ERROR and r.name == LOGGER_DA_MONTAGEM
        ]
        assert erros, "sair calado faria o usuario achar que produziu dado"
        assert "Traceback" not in capsys.readouterr().out

    def test_o_aviso_e_o_TEXTO_DA_MONTAGEM_e_nao_um_texto_proprio(
        self, tmp_path, censo_vazio, ocr_fingido, sem_instalar_log, caplog
    ) -> None:
        """A prova de que a ferramenta usa a montagem do 03-02.

        Se ela tivesse texto proprio, o usuario veria aqui uma frase e na Fase 4
        outra — e duas versoes da mesma frase e como elas divergem. A promessa
        de que morte, saida e ressurreicao continuam so existe na montagem.
        """
        ocupado = tmp_path / "portao-quebrado"
        ocupado.write_text("nao sou uma pasta", encoding="utf-8")

        with caplog.at_level(logging.ERROR, logger=LOGGER_DA_MONTAGEM):
            ferramenta.main(
                [
                    "--gravacoes",
                    str(censo_vazio),
                    "--calibracao",
                    str(CALIBRACAO_DE_FIXTURE),
                    "--saida",
                    str(ocupado),
                ]
            )

        mensagens = [
            r.getMessage()
            for r in caplog.records
            if r.levelno >= logging.ERROR and r.name == LOGGER_DA_MONTAGEM
        ]
        assert any(A_PROMESSA in m for m in mensagens), mensagens

    def test_o_log_do_projeto_e_instalado_ANTES_de_montar_o_registro(
        self, tmp_path, censo_vazio, ocr_fingido, monkeypatch
    ) -> None:
        """Sem isto o `log.error` da montagem nao teria manipulador nenhum.

        E o criterio 5 da fase e literalmente "o usuario VE o aviso alto". A
        metade console do D-13 so vale aqui se a instalacao vier primeiro.
        """
        ordem: list[str] = []
        monkeypatch.setattr(
            ferramenta, "configurar_log", lambda verboso: ordem.append("log")
        )
        monkeypatch.setattr(
            ferramenta,
            "montar_registro_de_mercado",
            lambda pasta: ordem.append("montagem") or None,
        )

        codigo = ferramenta.main(
            [
                "--gravacoes",
                str(censo_vazio),
                "--calibracao",
                str(CALIBRACAO_DE_FIXTURE),
                "--saida",
                str(tmp_path / "portao"),
            ]
        )

        assert ordem == ["log", "montagem"], ordem
        assert codigo != 0, "montagem que devolve None nao pode sair com 0"

    def test_uma_varredura_SEM_OBSERVACAO_NENHUMA_sai_diferente_de_zero(
        self, tmp_path, censo_vazio, ocr_fingido, sem_instalar_log, capsys
    ) -> None:
        """As 8 pastas existem e estao vazias: zero frames, zero observacoes.

        Um arquivo so com cabecalho nao serve para o portao, e sair com 0
        esconderia isso do usuario.
        """
        codigo = ferramenta.main(
            [
                "--gravacoes",
                str(censo_vazio),
                "--calibracao",
                str(CALIBRACAO_DE_FIXTURE),
                "--saida",
                str(tmp_path / "portao"),
            ]
        )

        assert codigo != 0
        saiu = capsys.readouterr().out
        assert "NENHUMA observacao" in saiu
        assert "frames lidos" in saiu, "o relatorio sai mesmo quando nao houve dado"
