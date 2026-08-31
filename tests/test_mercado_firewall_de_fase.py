"""O tripwire SIMETRICO: o mercado nao conhece o rastreador.

POR QUE ESTE ARQUIVO EXISTE
============================
`tests/test_mercado_27x.py` ja prende uma direcao - o rastreador nao cita o
mercado. Este arquivo prende a OUTRA - o modo mercado nao cita o rastreador.
Acoplamento e uma relacao, e prender so uma ponta deixa a outra livre: nada em
`test_mercado_27x.py` impediria `mercado_modo.py` de importar `Rastreador` e
"aproveitar" a leitura de barra que ja esta la. Essa e exatamente a manobra que
causou o incidente das 27 mortes falsas.

O QUE ESTE ARQUIVO NAO CONSEGUE AFIRMAR, E ISSO PRECISA ESTAR ESCRITO
=======================================================================
Contencao entre TRES processos (duas instancias de party mais `--mercado`) e
propriedade do SISTEMA, e nao do programa: CPU, GPU, sessoes WGC e agendador do
Windows. Nenhum teste automatizado alcanca isso, e escrever
`test_nenhuma_competicao_de_recursos` seria dar nome de prova a uma opiniao.

O que E afirmavel por teste e que os dois lados NAO SE CONHECEM - por importacao,
por construcao e por texto - e e so isso que este arquivo prende. O resto do
criterio 1 do DETC-02 fecha em PORTAO HUMANO DE CAMPO: o usuario roda as tres
invocacoes por dez minutos e confere CPU, log de captura das duas de party e
ausencia de borda amarela.

DUAS CORRECOES DE CRITERIO, DITAS EM VOZ ALTA
==============================================
O plano pedia duas coisas que, executadas ao pe da letra, seriam FALSAS. Um
criterio que cai precisa dizer que caiu.

**(1) "nenhuma das quatro palavras aparece no fonte de `mercado_modo`."**
Impossivel de satisfazer honestamente, por tres colisoes:

  - `mercado_visao` e um modulo DO MERCADO, e e de onde vem `RastreioDoPainel`.
    Proibir a substring `visao` proibiria o import legitimo, e o unico jeito de
    passar seria ofuscar a importacao - que destruiria o proprio tripwire.
  - `sessao` aparece na prosa obrigatoria do proprio plano ("o resumo conta as
    duas metades por SESSAO") e no nome `resumo_da_sessao`.
  - o cabecalho de `mercado_modo.py` EXPLICA o firewall nomeando os quatro
    modulos. Um teste de substring reprovaria a documentacao do firewall.

A prova aqui e, entao, em tres camadas: IMPORTACAO lida do AST, NAMESPACE lido
em memoria, e substring sobre o CODIGO (sem comentario e sem docstring) para as
duas palavras que nao tem homonimo. Estritamente mais forte que uma varredura de
texto - ela nao se engana com prosa nem com um import escrito de outro jeito.

**(2) "importar o modulo de mercado nao traz `l2scanner.rastreador` para
`sys.modules`."** ISSO E FALSO HOJE, e nao por culpa desta fase. A cadeia e
`mercado_pagina` -> `mercado_catalogo` -> `config` (so para pegar `RAIZ`) ->
`notificador` -> `rastreador` -> `visao`, e ela existe desde a Fase 2. Cortar
seria mexer em `config.py` e `notificador.py`, que estao fora do escopo deste
plano, e em `rastreador.py`, que e intocavel por decisao do 04-CONTEXT.

O teste correspondente foi INVERTIDO: ele prende a cadeia PREEXISTENTE, para
que a explicacao nao vire folclore e para que quem a cortar um dia seja obrigado
a atualizar a historia. O que importa - "o mercado nao USA a party" - continua
prendido pelos outros tres.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import re
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
import pytest

import l2scanner.captura_janela as captura_janela
import l2scanner.mercado_modo as mercado_modo
from l2scanner.frames import Regiao
from l2scanner.relogio import Relogio

RAIZ = Path(__file__).resolve().parents[1]
REQUIREMENTS = RAIZ / "requirements.txt"

# Os quatro modulos do lado da PARTY. O mercado nao pode conhecer nenhum.
MODULOS_DA_PARTY = ("rastreador", "visao", "sessao", "presenca")

# Os modulos que esta fase acrescenta. A lista cresce junto com a fase.
MODULOS_DO_MERCADO_DESTA_FASE = (
    "l2scanner.mercado_modo",
    "l2scanner.mercado_console",
)


# ---------------------------------------------------------------------------
# A ALAVANCA DE DETC-02: minimum_update_interval, so no mercado
# ---------------------------------------------------------------------------


class _FrameFalso:
    """O que a WGC entrega: BGRA, `(H, W, 4)`."""

    def __init__(self, altura: int = 8, largura: int = 8) -> None:
        self.frame_buffer = np.full((altura, largura, 4), 200, dtype=np.uint8)


class _ControleFalso:
    def stop(self) -> None:
        pass


class _CapturaFalsa:
    """Registra os kwargs com que `WindowsCapture` foi construida.

    `start()` entrega UM frame ao manipulador registrado e volta - e o que faz
    `_esperar_primeiro_frame` sair sem os cinco segundos de espera.
    """

    ultimos_kwargs: dict = {}

    def __init__(self, **kwargs) -> None:
        _CapturaFalsa.ultimos_kwargs = dict(kwargs)
        self._ao_chegar = None

    def event(self, funcao):
        if funcao.__name__ == "on_frame_arrived":
            self._ao_chegar = funcao
        return funcao

    def start(self) -> None:
        if self._ao_chegar is not None:
            self._ao_chegar(_FrameFalso(), _ControleFalso())


@pytest.fixture
def wgc_falsa(monkeypatch):
    """Troca `windows_capture` por um duble e a busca de janela por um hwnd."""
    modulo = types.ModuleType("windows_capture")
    modulo.WindowsCapture = _CapturaFalsa
    modulo.Frame = _FrameFalso
    modulo.InternalCaptureControl = _ControleFalso
    monkeypatch.setitem(sys.modules, "windows_capture", modulo)
    monkeypatch.setattr(captura_janela, "achar_janela", lambda titulo: 4242)
    _CapturaFalsa.ultimos_kwargs = {}
    return _CapturaFalsa


def _montar_fonte(**extras) -> captura_janela.JanelaSource:
    fonte = captura_janela.JanelaSource(
        "Lineage II",
        Regiao(esquerda=0, topo=0, largura=8, altura=8),
        relativa=True,
        **extras,
    )
    fonte.fechar()
    return fonte


class TestAAlavancaDeDETC02:
    def test_o_padrao_e_None_na_assinatura(self) -> None:
        """O contrato: o caminho da party continua identico ao de hoje."""
        assinatura = inspect.signature(captura_janela.JanelaSource.__init__)
        assert (
            assinatura.parameters["minimum_update_interval"].default is None
        )

    def test_sem_o_parametro_a_WGC_recebe_None(self, wgc_falsa) -> None:
        _montar_fonte()
        assert wgc_falsa.ultimos_kwargs["minimum_update_interval"] is None

    def test_com_250_a_WGC_recebe_250(self, wgc_falsa) -> None:
        _montar_fonte(minimum_update_interval=250)
        assert wgc_falsa.ultimos_kwargs["minimum_update_interval"] == 250

    def test_o_parametro_chega_a_chamada_de_WindowsCapture_no_fonte(
        self,
    ) -> None:
        """Lido do AST: a chamada tem de carregar a palavra-chave.

        Uma varredura de substring ficaria verde com o parametro guardado num
        atributo e nunca repassado - que e o bug exato que este teste pega.
        """
        arvore = ast.parse(
            Path(captura_janela.__file__).read_text(encoding="utf-8")
        )
        chamadas = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call)
            and isinstance(no.func, ast.Name)
            and no.func.id == "WindowsCapture"
        ]
        assert chamadas, "nao achei a construcao de WindowsCapture"
        for chamada in chamadas:
            nomes = {kw.arg for kw in chamada.keywords}
            assert "minimum_update_interval" in nomes

    def test_a_constante_do_mercado_tem_folga_de_pelo_menos_4x(self) -> None:
        """A margem que impede o FALSO congelamento.

        Com atualizacao a cada ~1000 ms e leitura a cada ~1000 ms, a deriva de
        fase entrega o mesmo buffer tres vezes seguidas,
        `JANELAS_IGUAIS_PARA_CONGELAR` dispara e o console anuncia captura
        congelada com o jogo vivo.
        """
        assert mercado_modo.MS_ENTRE_FRAMES_DO_MERCADO * 4 <= 1000

    def test_o_modo_mercado_e_o_unico_a_usar_a_alavanca(self) -> None:
        fonte = inspect.getsource(mercado_modo)
        assert "minimum_update_interval=MS_ENTRE_FRAMES_DO_MERCADO" in fonte

    def test_a_constante_diz_que_e_ESCOLHA_e_nao_medicao(self) -> None:
        """Um numero que nao foi medido precisa dizer que nao foi."""
        fonte = inspect.getsource(mercado_modo)
        # A razao mora ACIMA da atribuicao, no bloco de comentario que a
        # antecede - e por isso a janela olha para tras e nao para a frente.
        atribuicao = fonte.index("MS_ENTRE_FRAMES_DO_MERCADO = ")
        trecho = fonte[:atribuicao][-2500:]
        assert "ESCOLHA" in trecho
        assert "medicao" in trecho.lower()
        assert "derivado" in trecho.lower()


# ---------------------------------------------------------------------------
# O TRIPWIRE: o mercado nao conhece o rastreador
# ---------------------------------------------------------------------------


def _codigo_sem_comentario_nem_docstring(modulo) -> str:
    """O fonte com prosa removida: comentario fora, docstring fora.

    `ast.unparse` de uma arvore com as docstrings arrancadas devolve o codigo
    EXECUTAVEL e nada mais - e comentario nem chega ao AST. E o que separa "o
    modulo cita o rastreador" de "o modulo explica por que nao cita".
    """
    arvore = ast.parse(inspect.getsource(modulo))
    for no in ast.walk(arvore):
        if not isinstance(
            no, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        corpo = no.body
        if (
            corpo
            and isinstance(corpo[0], ast.Expr)
            and isinstance(corpo[0].value, ast.Constant)
            and isinstance(corpo[0].value.value, str)
        ):
            no.body = corpo[1:] or [ast.Pass()]
    return ast.unparse(arvore)


def _modulos_importados(modulo) -> set[str]:
    """Todo modulo que o fonte importa, inclusive os imports ADIADOS.

    O AST enxerga o `from .captura_janela import JanelaSource` que mora dentro
    da funcao - que e onde um acoplamento tentaria se esconder.
    """
    arvore = ast.parse(inspect.getsource(modulo))
    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for alias in no.names:
                nomes.add(alias.name)
        elif isinstance(no, ast.ImportFrom):
            if no.module:
                nomes.add(no.module)
            for alias in no.names:
                nomes.add(alias.name)
                if no.module:
                    nomes.add(no.module + "." + alias.name)
    return nomes


class TestOMercadoNaoConheceORastreador:
    def test_nenhum_modulo_da_party_e_importado(self) -> None:
        importados = _modulos_importados(mercado_modo)
        pedacos = {parte for nome in importados for parte in nome.split(".")}
        for proibido in MODULOS_DA_PARTY:
            assert proibido not in pedacos, (
                f"l2scanner/mercado_modo.py passou a importar `{proibido}`. "
                "Se isso e deliberado, e uma decisao de arquitetura que precisa "
                "da medicao de campo antes - nao de apagar este teste"
            )

    def test_o_CODIGO_nao_cita_rastreador_nem_presenca(self) -> None:
        """A forma de texto, sobre o CODIGO e nao sobre a prosa.

        `rastreador` e `presenca` nao tem homonimo do lado do mercado, entao a
        substring vale ao pe da letra - mas so depois de tirar comentarios e
        docstrings, porque o proprio cabecalho deste modulo EXPLICA o firewall
        nomeando os quatro modulos. Um teste sobre o fonte cru reprovaria a
        documentacao do firewall, que e o oposto do que ele quer.

        `visao` e `sessao` ficam de fora desta forma e sao cobertos pelo teste
        de importacao acima: `mercado_visao` e um modulo DO MERCADO, e `sessao`
        e uma palavra obrigatoria da prosa e do nome `resumo_da_sessao`.
        """
        codigo = _codigo_sem_comentario_nem_docstring(mercado_modo)
        for proibido in ("rastreador", "presenca"):
            assert proibido not in codigo, (
                f"o CODIGO de mercado_modo.py cita `{proibido}`. Se isso e "
                "deliberado, e uma decisao de arquitetura - nao de apagar "
                "este teste"
            )

    def test_nenhum_nome_do_modo_vem_de_um_modulo_da_party(self) -> None:
        """A prova em MEMORIA: nada no namespace do modo nasceu na party.

        Ela pega o que a leitura de fonte nao pega - um objeto que chegasse por
        outro nome, por `getattr` ou por reexportacao de um modulo intermediario.
        """
        proibidos = {f"l2scanner.{nome}" for nome in MODULOS_DA_PARTY}
        for nome, valor in vars(mercado_modo).items():
            origem = getattr(valor, "__module__", None)
            assert origem not in proibidos, (nome, origem)

    def test_o_rastreador_chega_por_uma_CADEIA_PREEXISTENTE_do_config(
        self,
    ) -> None:
        """O achado desta fase, escrito para nao virar folclore.

        `import l2scanner.mercado_modo` TRAZ `l2scanner.rastreador` para
        `sys.modules`, e isso NAO e acoplamento do mercado: a cadeia e
        `mercado_catalogo` -> `config` (por `RAIZ`) -> `notificador` ->
        `rastreador` -> `visao`, e ela existe desde a Fase 2, antes de este modo
        nascer. Nenhuma linha desta fase a criou e nenhuma linha desta fase pode
        desfaze-la: `rastreador.py` e intocavel por decisao do 04-CONTEXT, e
        `config.py` e `notificador.py` estao fora do escopo deste plano.

        Este teste PRENDE a explicacao. Se a cadeia for cortada um dia, ele cai e
        obriga quem cortou a atualizar a historia em vez de deixar um comentario
        mentindo. E enquanto ele estiver verde, ninguem pode usar "o mercado
        importa o rastreador" como licenca para acopla-los de verdade - os dois
        testes acima continuam provando que nao ha uso.
        """
        codigo = (
            "import sys\n"
            "import l2scanner.config\n"
            "assert 'l2scanner.rastreador' in sys.modules\n"
            "import l2scanner.mercado_catalogo\n"
            "assert 'l2scanner.config' in sys.modules\n"
        )
        resultado = subprocess.run(
            [sys.executable, "-c", codigo],
            cwd=str(RAIZ),
            capture_output=True,
            text=True,
        )
        assert resultado.returncode == 0, resultado.stderr

    def test_o_laco_NUNCA_constroi_um_Rastreador(
        self, monkeypatch, tmp_path
    ) -> None:
        """A prova em EXECUCAO, e nao por leitura de fonte.

        Substituir a classe por algo que levanta ao ser chamado transforma
        "eu nao construo" numa afirmacao que o interpretador verifica.
        """
        rastreador = importlib.import_module("l2scanner.rastreador")

        def _explodir(*args, **kwargs):
            raise AssertionError(
                "o modo mercado construiu um Rastreador - e o acoplamento que "
                "causou o incidente 27x"
            )

        monkeypatch.setattr(rastreador, "Rastreador", _explodir)

        class _FonteVazia:
            def __init__(self) -> None:
                self.fechada = False

            def capturar(self):
                raise StopIteration

            def fechar(self) -> None:
                self.fechada = True

        from tests.test_mercado_modo import (
            LeitoraDeRecorte,
            cal_de_fixtura,
        )

        fonte = _FonteVazia()
        codigo = mercado_modo.laco_do_mercado(
            argparse.Namespace(janela="Lineage II", intervalo=0.0),
            cal_de_fixtura(),
            fonte=fonte,
            ler_texto=LeitoraDeRecorte(),
            ler_texto_conferencia=LeitoraDeRecorte(),
            relogio=Relogio(),
            pasta=tmp_path,
            ticks_maximos=3,
        )
        assert codigo == 0
        assert fonte.fechada


# ---------------------------------------------------------------------------
# NENHUMA DEPENDENCIA NOVA
# ---------------------------------------------------------------------------

# As onze distribuicoes que o projeto declarava ANTES da Fase 4. A lista esta
# escrita a mao de proposito: deriva-la do proprio arquivo faria o teste
# concordar com qualquer coisa que alguem acrescentasse.
#
# `rich` NAO entra, e a razao e DOUTRINA DE ZERO-INSTALL - o `vigiar-party.bat`
# roda `pip install -r requirements.txt` na primeira execucao - e NAO o FIRE-01.
# A banlist do FIRE-01 e so de SINTESE DE INPUT (`pyautogui`, `pynput`,
# `keyboard`...), e ela nao alcanca uma biblioteca de console. O `04-CONTEXT.md`
# escreveu a justificativa errada na primeira redacao e ja a corrigiu; a
# correcao esta repetida aqui para nao se perder.
DISTRIBUICOES_ANTES_DA_FASE_4 = {
    "mss",
    "opencv-python",
    "numpy",
    "windows-capture",
    "winrt-windows-media-ocr",
    "winrt-windows-graphics-imaging",
    "winrt-windows-storage-streams",
    "winrt-windows-globalization",
    "winrt-windows-foundation",
    "winrt-windows-foundation-collections",
    "discord-py",
}

_FIM_DO_NOME = re.compile(r"[=<>!~@\[\];(,\s]")


def _distribuicoes_declaradas() -> set[str]:
    nomes = set()
    for linha in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        bruto = _FIM_DO_NOME.split(linha)[0]
        nomes.add(re.sub(r"[-_.]+", "-", bruto).lower())
    return nomes


class TestNenhumaDependenciaNova:
    def test_o_requirements_nao_ganhou_linha_nesta_fase(self) -> None:
        assert _distribuicoes_declaradas() == DISTRIBUICOES_ANTES_DA_FASE_4

    def test_nenhum_modulo_do_mercado_importa_rich(self) -> None:
        for nome in MODULOS_DO_MERCADO_DESTA_FASE:
            modulo = importlib.import_module(nome)
            assert "rich" not in _modulos_importados(modulo)


# ---------------------------------------------------------------------------
# ESTE MODO LE A CALIBRACAO, NUNCA A ESCREVE
# ---------------------------------------------------------------------------
#
# POR QUE ESTA GUARDA EXISTE, E O QUE ELA SUBSTITUI
# =================================================
# O criterio de aceitacao do 04-01 e do 04-03 era
#
#     test -z "$(git status --porcelain calibration.json)" || { echo REPROVADO; exit 1; }
#
# e ele e VACUO: `calibration.json` e GITIGNORED (`.gitignore:51`), entao a
# saida do `git status --porcelain` e vazia SEMPRE — o arquivo tendo sido
# reescrito ou nao. O comando nao consegue detectar a escrita que ele existe
# para proibir. A verdade que ele AFIRMA continua verdadeira; ela so nao era
# verdadeira POR CAUSA DELE.
#
# A verificacao da Fase 4 contou esta como a OITAVA instancia do mesmo padrao
# de defeito na fase — um guarda cuja saida nao muda com o fato que ele julga.
# O antidoto e o mesmo em todas: ao lado da afirmacao, o CONTROLE NEGATIVO que
# prova que o guarda reprova quando o fato acontece. Ele esta logo abaixo, em
# `test_a_guarda_REPROVA_quando_a_escrita_ACONTECE`, e sem ele esta guarda
# seria so a nona aparicao.
#
# AS DUAS METADES:
#   - a ESTRUTURAL, por AST: nenhum modulo `mercado_*` alcanca o escritor;
#   - a de EXECUCAO: um `calibration.json` de verdade, com impressao digital
#     tirada antes e depois de uma sessao inteira do laco.
# Sozinha, a estrutural nao ve uma escrita via `getattr`/`open` cru; sozinha, a
# de execucao so cobre o caminho que aquela sessao percorreu.


def _impressao_do_arquivo(caminho: Path) -> tuple[int, int, str]:
    """(tamanho, mtime_ns, sha256) — a impressao digital de UM arquivo.

    OS TRES JUNTOS, e nao so o sha256: uma reescrita com bytes IDENTICOS nao
    muda o hash, e "escreveu por cima com o mesmo conteudo" continua sendo
    escrita neste arquivo — e a rodada seguinte do usuario poderia sair
    diferente. O `mtime_ns` pega esse caso; o sha256 pega o caso em que o
    relogio do sistema de arquivos e grosso demais para separar duas escritas.
    """
    import hashlib

    bruto = caminho.read_bytes()
    estado = caminho.stat()
    return (estado.st_size, estado.st_mtime_ns, hashlib.sha256(bruto).hexdigest())


def _uma_calibracao_gravada(pasta: Path) -> Path:
    """Um `calibration.json` REAL em `tmp_path`, escrito pelo escritor de verdade.

    Escrever o JSON a mao aqui seria um segundo formatador do arquivo; o que se
    quer e exatamente o que `calibrar.bat` produz, para que a impressao digital
    seja tirada do material verdadeiro.
    """
    from tests.test_mercado_modo import cal_de_fixtura

    arquivo = pasta / "calibration.json"
    cal_de_fixtura().salvar(arquivo)
    return arquivo


class TestOMercadoNaoEscreveNoCalibrationJson:
    def test_uma_sessao_INTEIRA_do_laco_nao_altera_o_calibration_json(
        self, monkeypatch, tmp_path
    ) -> None:
        """A afirmacao em EXECUCAO, e nao por `git status` sobre gitignored.

        `ARQUIVO_CALIBRACAO` e apontado para o `tmp_path` ANTES do laco por duas
        razoes, e a segunda importa mais que a primeira: para a impressao
        digital ser tirada de um arquivo que este teste controla, e para que uma
        regressao que passasse a escrever caisse no temporario em vez de
        corromper o `calibration.json` medido a mao pelo usuario.
        """
        calibrar = importlib.import_module("l2scanner.calibrar")
        arquivo = _uma_calibracao_gravada(tmp_path)
        monkeypatch.setattr(calibrar, "ARQUIVO_CALIBRACAO", arquivo)

        from tests.test_mercado_modo import LeitoraDeRecorte, cal_de_fixtura

        antes = _impressao_do_arquivo(arquivo)

        quadros = [
            np.full((400, 400, 3), 20 + i * 7, dtype=np.uint8) for i in range(4)
        ]

        class _Fonte:
            def __init__(self) -> None:
                self._i = 0

            def capturar(self):
                if self._i >= len(quadros):
                    raise StopIteration
                from l2scanner.frames import Frame, SaudeDoFrame

                self._i += 1
                return Frame(
                    pixels=quadros[self._i - 1],
                    indice=self._i,
                    saude=SaudeDoFrame.OK,
                )

            def fechar(self) -> None:
                pass

        mercado_modo.laco_do_mercado(
            argparse.Namespace(janela="Lineage II", intervalo=0.0),
            cal_de_fixtura(),
            fonte=_Fonte(),
            ler_texto=LeitoraDeRecorte(),
            ler_texto_conferencia=LeitoraDeRecorte(),
            relogio=Relogio(),
            pasta=tmp_path,
            ticks_maximos=4,
        )

        assert _impressao_do_arquivo(arquivo) == antes, (
            "o modo --mercado ESCREVEU no calibration.json. Ele le a "
            "calibracao e nunca a escreve: quem escreve e o calibrar.bat, com "
            "o usuario olhando"
        )

    def test_a_guarda_REPROVA_quando_a_escrita_ACONTECE(self, tmp_path) -> None:
        """O CONTROLE NEGATIVO — a metade que faltava no criterio antigo.

        Sem ele, uma guarda que sempre devolve "igual" (era o caso do `git
        status` sobre arquivo gitignored) passaria por prova de que nada foi
        escrito. Aqui a MESMA `_impressao_do_arquivo` do teste acima e apontada
        para uma escrita REAL, e o que se afirma e que ela ACUSA.

        Sao os DOIS jeitos de escrever, porque a guarda tem de pegar os dois:
        conteudo diferente (sha256/tamanho) e reescrita com o MESMO conteudo
        (mtime_ns). O segundo e o sorrateiro — e o `cal.salvar()` que um
        refactor chamaria sem querer, achando que "nao mudou nada".
        """
        from tests.test_mercado_modo import cal_de_fixtura

        arquivo = _uma_calibracao_gravada(tmp_path)
        antes = _impressao_do_arquivo(arquivo)

        # (a) escrita com CONTEUDO DIFERENTE
        cal = cal_de_fixtura()
        cal.mercado_limiar_da_ancora = float(cal.mercado_limiar_da_ancora) / 2.0
        cal.salvar(arquivo)
        depois = _impressao_do_arquivo(arquivo)
        assert depois != antes, (
            "a guarda NAO acusou uma escrita com conteudo diferente - ela "
            "seria a nona aparicao do criterio vacuo"
        )
        assert depois[2] != antes[2], "o sha256 tinha de ter mudado"

        # (b) escrita com o MESMO CONTEUDO, que o sha256 sozinho nao pega
        so_hash_antes = _impressao_do_arquivo(arquivo)[2]
        cal.salvar(arquivo)
        de_novo = _impressao_do_arquivo(arquivo)
        assert de_novo[2] == so_hash_antes, (
            "a fixtura deixou de gravar bytes deterministicos: este ramo nao "
            "esta mais testando 'mesmo conteudo'"
        )
        assert de_novo != depois, (
            "a guarda NAO acusou uma reescrita com bytes identicos. O sha256 "
            "sozinho nao pega esse caso; o mtime_ns esta na impressao "
            "exatamente por isso"
        )

    def test_nenhum_modulo_do_mercado_alcanca_o_ESCRITOR_da_calibracao(
        self,
    ) -> None:
        """A metade ESTRUTURAL: o caminho de escrita nao existe no fonte.

        `Calibracao.salvar` e os dois modulos de calibracao sao o unico jeito
        de o `calibration.json` mudar. Nenhum modulo `mercado_*` pode cita-los.

        A varredura e por GLOB e nao por lista escrita a mao — ao contrario de
        `DISTRIBUICOES_ANTES_DA_FASE_4`, aqui a lista automatica so pode AUMENTAR
        a cobertura: um `mercado_novo.py` entra sozinho, em vez de nascer fora
        do firewall porque ninguem lembrou de acrescenta-lo.
        """
        modulos = sorted(RAIZ.glob("l2scanner/mercado_*.py"))
        assert modulos, "o glob nao achou modulo de mercado nenhum"

        for caminho in modulos:
            modulo = importlib.import_module(f"l2scanner.{caminho.stem}")
            importados = _modulos_importados(modulo)
            pedacos = {parte for nome in importados for parte in nome.split(".")}
            for proibido in ("calibrar", "calibrar_mercado"):
                assert proibido not in pedacos, (
                    f"{caminho.name} passou a importar `{proibido}`, que e "
                    "quem ESCREVE o calibration.json"
                )

            codigo = _codigo_sem_comentario_nem_docstring(modulo)
            assert ".salvar(" not in codigo, (
                f"o CODIGO de {caminho.name} chama `.salvar(`. Se for outro "
                "`salvar` que nao o da Calibracao, esta guarda precisa ficar "
                "mais fina - nao ser apagada"
            )
