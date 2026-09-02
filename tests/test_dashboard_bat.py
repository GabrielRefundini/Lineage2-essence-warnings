"""O lancador do DASHBOARD nao pode anunciar o que nao conferiu.

TERCEIRA INSTANCIA DO MESMO MOLDE, e pelo mesmo defeito MEDIDO EM CAMPO em
2026-08-28: o `calibrar-mercado.bat` imprimia o bloco de conferencia depois de a
ferramenta ter saido em codigo 1, mandando o usuario abrir um arquivo que nunca
foi gerado. `tests/test_calibrar_mercado_bat.py` prendeu aquele;
`tests/test_vigiar_mercado_bat.py` prendeu o irmao do mercado; este prende o do
dashboard, e os tres falam o MESMO dialeto de proposito -- um quarto dialeto
seria uma quarta chance de o guarda medir a coisa errada.

ESTE .bat FECHA O DEFEITO PELA ESTRUTURA, e nao por uma guarda: os blocos de
erro ficam ANTES da linha de execucao, com um desvio por cima, e DEPOIS dela nao
ha `echo` nenhum. A porta ocupada, a porta reservada e o encerramento normal sao
impressos pelo PROPRIO programa, que e quem sabe o que aconteceu.

O QUE E ESPECIFICO DESTE ARQUIVO, e nao vem do molde, e a SONDA. A sonda do
`vigiar-mercado.bat` cobre captura de tela, janela e OCR porque o modo mercado
precisa dos tres. O processo do dashboard nao precisa de nenhum: ele nao olha
para a tela do jogo. Um lancador que copiasse a sonda do irmao concordaria com o
que o irmao precisa e nao provaria nada sobre este processo -- e por isso a lista
de pacotes proibidos abaixo esta escrita A MAO, e nao derivada do outro `.bat`.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BAT = RAIZ / "dashboard.bat"

# A chamada que faz deste .bat o dashboard. O MODULO, e nao o pacote: e assim
# que `l2scanner/__main__.py` -- o caminho do `--mercado` -- fica intocado
# (DASH-06).
CHAMADA_DO_MODULO = "-m l2scanner.dashboard"

# Os dois pacotes que a MEDICAO mostrou serem carregados por este processo.
# Refeita em 2026-09-02 nesta arvore: `import l2scanner.dashboard` traz 342
# modulos e exatamente duas distribuicoes de site-packages, estas.
PACOTES_MEDIDOS = {"cv2", "numpy"}

# ESCRITA A MAO, E ESSE E O PONTO. Derivar esta lista da sonda do
# `vigiar-mercado.bat` faria o teste concordar com qualquer coisa que alguem
# copiasse de la -- inclusive com a copia errada que este arquivo existe para
# impedir. Sao os pacotes de CAPTURA DE TELA, de JANELA e de OCR: nenhum deles
# tem o que fazer num processo que so le um CSV e desenha um numero.
PACOTES_DE_CAPTURA_JANELA_E_OCR = (
    "mss",
    "dxcam",
    "windows_capture",
    "windows-capture",
    "winrt",
    "winsdk",
    "pytesseract",
    "rapidocr",
    "easyocr",
    "PIL",
    "Pillow",
    "pyautogui",
    "pygetwindow",
    "win32gui",
    "pywin32",
)


def _texto() -> str:
    # cp1252 e o encoding que os tres testes de lancador desta arvore usam, e o
    # arquivo e ASCII puro de proposito (ver `test_o_bat_e_ascii_puro`), entao a
    # leitura da o mesmo resultado em qualquer um dos dois encodings da raiz.
    return BAT.read_text(encoding="cp1252")


# ---------------------------------------------------------------------------
# OS AUXILIARES, COPIADOS DE `tests/test_vigiar_mercado_bat.py:53-78`.
#
# COPIADOS, E NAO IMPORTADOS, de proposito: um arquivo de teste importando outro
# arquivo de teste e um acoplamento que a suite desta casa nao usa -- ele faz uma
# falha no arquivo A pintar de vermelho o arquivo B, e faz um `-k` sobre um deles
# arrastar o outro. Se um dia os tres lancadores virarem quatro, o lugar de
# extrair isso e um modulo de apoio proprio, e nao um `from tests.x import y`.
# ---------------------------------------------------------------------------


def _linhas_de_echo(texto: str) -> list[tuple[int, str]]:
    """(posicao, linha) de cada linha que o cmd EXECUTA como `echo`.

    Comentario `REM` NAO CONTA, e a razao vem medida do teste irmao: a primeira
    versao daquele guarda foi enganada pelo PROPRIO comentario que explicava o
    defeito. O que precisa estar atras da guarda e o que o cmd IMPRIME.
    """
    achados: list[tuple[int, str]] = []
    posicao = 0
    for linha in texto.splitlines(keepends=True):
        despido = linha.strip()
        if despido.lower().startswith("echo"):
            achados.append((posicao, despido))
        posicao += len(linha)
    return achados


def _posicao_da_execucao(texto: str) -> int:
    """Onde termina a linha que roda o modulo do dashboard.

    `-1` quando nao existe linha EXECUTADA nenhuma com a chamada -- e esse `-1`
    e afirmado pelos testes, nunca engolido: um auxiliar que devolve `-1` calado
    faria toda comparacao de ordem passar por vacuidade.
    """
    for casamento in re.finditer(r"^.*-m l2scanner\.dashboard.*$", texto, re.MULTILINE):
        linha = casamento.group(0)
        if linha.strip().lower().startswith("rem"):
            continue
        return casamento.end()
    return -1


def _linhas_executaveis(texto: str) -> list[str]:
    """As linhas que o cmd EXECUTA. Comentario `REM` e linha vazia nao contam.

    Mesmo cuidado do `tests/test_ponte_bat.py`: descartar os `REM` antes de
    varrer nao e detalhe, porque o comentario que EXPLICA uma proibicao contem
    as mesmas palavras que a assercao procura. Um teste que fica vermelho por
    causa da propria justificativa e um teste que alguem apaga.
    """
    linhas = []
    for bruta in texto.splitlines():
        despida = bruta.strip()
        if not despida or despida.lower().startswith("rem"):
            continue
        linhas.append(despida)
    return linhas


def _pacotes_da_sonda(texto: str) -> set[str]:
    """Os pacotes que a sonda de dependencias do lancador NOMEIA.

    So linha EXECUTADA, e so na forma `-c "import a,b,c"`. Vazio quando nao ha
    sonda nenhuma -- e o `test_o_extrator_da_sonda_ACUSA...` abaixo e o que prova
    que esse vazio significa ausencia, e nao cegueira do extrator.
    """
    achados: set[str] = set()
    for linha in _linhas_executaveis(texto):
        for casamento in re.finditer(r'-c\s+"import\s+([^"]+)"', linha):
            for nome in casamento.group(1).split(","):
                limpo = nome.strip()
                if limpo:
                    achados.add(limpo)
    return achados


def _rotulos(texto: str) -> dict[str, int]:
    """(rotulo -> posicao) de cada `:rotulo` do arquivo."""
    return {
        casamento.group(1): casamento.start()
        for casamento in re.finditer(r"^\s*:([a-z_][a-z0-9_]*)\s*$", texto, re.MULTILINE | re.IGNORECASE)
    }


def _desvios(texto: str) -> set[str]:
    """Os alvos de `goto` das linhas EXECUTADAS."""
    alvos: set[str] = set()
    for linha in _linhas_executaveis(texto):
        for casamento in re.finditer(r"\bgoto\s+([a-z_][a-z0-9_]*)", linha, re.IGNORECASE):
            alvos.add(casamento.group(1))
    return alvos


def _normalizar(nome: str) -> str:
    return nome.strip().lower().replace("-", "_")


class TestOArquivoExiste:
    def test_o_bat_do_dashboard_existe(self):
        """Sem ele o usuario teria que abrir um cmd e digitar `-m`. DASH-06."""
        assert BAT.is_file(), "dashboard.bat sumiu"

    def test_o_bat_e_ascii_puro(self):
        """Acento em .bat sai como lixo no console do cmd.

        O console herda a codepage da maquina (850/437 no Brasil) e o arquivo e
        escrito como UTF-8 por quem edita. Um caractere acentuado vira dois
        caracteres ilegiveis para o usuario -- e este arquivo e, literalmente,
        texto para ser lido por ele.

        A assercao e sobre BYTES e nao sobre a decodificacao dar certo: `cp1252`
        decodifica quase qualquer byte sem levantar, entao um teste que so
        tentasse decodificar passaria com o arquivo ja estragado.
        """
        bruto = BAT.read_bytes()
        ruins = [(i, b) for i, b in enumerate(bruto) if b > 127]
        assert not ruins, f"bytes nao-ASCII no .bat: {ruins[:5]}"
        # A via forte, dita junto: em ASCII estrito a decodificacao NAO levanta.
        bruto.decode("ascii")


class TestAIdaParaAPastaDoProprioArquivo:
    def test_a_primeira_instrucao_efetiva_e_a_ida_para_a_pasta_do_arquivo(self):
        """Dois cliques abrem o `.bat` com a pasta dele como diretorio atual --
        mas um atalho, uma tarefa agendada ou um `cmd` aberto em outro lugar,
        nao. Sem esta linha, `.venv\\Scripts\\python.exe` e `requirements.txt`
        seriam procurados na pasta errada e o lancador morreria dizendo que
        falta Python.

        MEDIDO EM BANCADA em 2026-09-02: chamado com o diretorio atual em
        `C:\\Windows`, o `cd /d "%~dp0"` resolve para a pasta do proprio
        arquivo.
        """
        primeira = _linhas_executaveis(_texto())[0]
        # `@echo off` e `setlocal` sao preambulo do interpretador, e nao
        # instrucao que dependa de diretorio; a primeira que depende tem de ser
        # esta.
        efetivas = [
            linha
            for linha in _linhas_executaveis(_texto())
            if linha.lower() not in ("@echo off", "setlocal")
        ]
        assert primeira.lower() in ("@echo off", "setlocal", 'cd /d "%~dp0"')
        assert efetivas[0] == 'cd /d "%~dp0"', (
            f"a primeira instrucao efetiva do lancador e {efetivas[0]!r}, e nao "
            "a ida para a pasta do proprio arquivo"
        )


class TestARecusaDoAtalhoDaLoja:
    def test_o_lancador_recusa_o_atalho_da_microsoft_store(self):
        """O alias da Store e um stub que so ABRE A LOJA -- ele nao roda codigo.

        A recusa e por substituicao de string NATIVA do cmd, e nao por `find` ou
        `findstr`: os dois sao executaveis que podem estar sombreados por
        homonimos de outro shell no PATH, e uma recusa que depende de um binario
        externo e uma recusa que as vezes nao acontece. Mesma linha do irmao.
        """
        assert "%PY:WindowsApps=%" in _texto(), (
            "sumiu a recusa do atalho da Microsoft Store por substituicao de "
            "string nativa"
        )


class TestASondaDizAVerdadeMedidaSobreESTEProcesso:
    """A sonda cobre o que ESTE processo carrega, e foi MEDIDA.

    A pesquisa desta fase antecipava um lancador sem ambiente virtual nenhum --
    o dashboard viraria stdlib puro depois do corte de `RAIZ`. A medicao
    derrubou isso: o corte matou a aresta `mercado_catalogo -> config`, mas
    sobrou `mercado_console -> console -> rastreador -> visao`, e o DASH-03
    OBRIGA o dashboard a usar os formatadores de `mercado_console`. Logo cv2 e
    numpy entram, e a sonda tem de dizer isso em vez de prometer o contrario.
    """

    def test_a_sonda_nomeia_EXATAMENTE_os_dois_pacotes_medidos(self):
        achados = {_normalizar(nome) for nome in _pacotes_da_sonda(_texto())}
        esperados = {_normalizar(nome) for nome in PACOTES_MEDIDOS}
        assert achados == esperados, (
            f"a sonda do lancador nomeia {sorted(achados)}, e a medicao desta "
            f"arvore diz {sorted(esperados)}"
        )

    def test_a_sonda_nao_nomeia_pacote_de_captura_de_janela_nem_de_OCR(self):
        """A lista proibida esta escrita a mao no topo deste arquivo.

        Deriva-la da sonda do `vigiar-mercado.bat` faria este teste concordar
        com qualquer coisa que alguem copiasse de la.
        """
        proibidos = {_normalizar(nome) for nome in PACOTES_DE_CAPTURA_JANELA_E_OCR}
        achados = {_normalizar(nome) for nome in _pacotes_da_sonda(_texto())}
        intrusos = achados & proibidos
        assert not intrusos, (
            f"a sonda do dashboard nomeia pacote de captura/janela/OCR: "
            f"{sorted(intrusos)}. Este processo nao olha para a tela do jogo."
        )

    def test_nenhuma_linha_EXECUTADA_do_lancador_cita_captura_janela_ou_OCR(self):
        """A via mais forte da mesma proibicao, e ela vale para o arquivo todo.

        Os nomes PODEM aparecer em `REM` -- e aparecem, na medicao que explica
        por que eles NAO estao na sonda. O que nao pode e o cmd executar uma
        linha que os mencione.
        """
        proibidos = {_normalizar(nome) for nome in PACOTES_DE_CAPTURA_JANELA_E_OCR}
        culpadas = []
        for linha in _linhas_executaveis(_texto()):
            palavras = {_normalizar(p) for p in re.findall(r"[A-Za-z_][A-Za-z0-9_.-]*", linha)}
            if palavras & proibidos:
                culpadas.append(linha)
        assert not culpadas, (
            f"linhas executadas citando captura/janela/OCR: {culpadas}"
        )

    def test_o_extrator_da_sonda_ACUSA_o_que_diz_medir(self):
        """CONTROLE NEGATIVO do extrator. Sem ele, os tres testes acima ficariam
        verdes para sempre se `_pacotes_da_sonda` passasse a devolver vazio por
        um erro de expressao regular -- e a proibicao viraria teatro.

        A mutacao acontece na ENTRADA da funcao, com texto fabricado aqui, e nao
        no arquivo real.
        """
        com_sonda_errada = (
            '@echo off\r\n'
            '".venv\\Scripts\\python.exe" -c "import mss,cv2,winrt.windows.media.ocr" >nul 2>&1\r\n'
        )
        assert _pacotes_da_sonda(com_sonda_errada) == {
            "mss",
            "cv2",
            "winrt.windows.media.ocr",
        }

        # E o outro lado: sem sonda nenhuma, conjunto VAZIO -- e nao um vazio
        # que tambem sairia de um extrator quebrado, porque o caso acima ja
        # provou que ele enxerga.
        sem_sonda = '@echo off\r\ncd /d "%~dp0"\r\npause\r\n'
        assert _pacotes_da_sonda(sem_sonda) == set()

        # `REM` nao conta, pelo mesmo motivo do auxiliar de `echo`.
        so_em_comentario = 'REM a sonda antiga era -c "import mss,cv2"\r\n'
        assert _pacotes_da_sonda(so_em_comentario) == set()


class TestALinhaDeExecucao:
    def test_a_linha_de_execucao_chama_o_MODULO_do_dashboard(self):
        t = _texto()
        assert _posicao_da_execucao(t) != -1, (
            f"nao ha nenhuma linha EXECUTADA que rode `{CHAMADA_DO_MODULO}`"
        )

    def test_a_linha_de_execucao_NAO_chama_o_ponto_de_entrada_do_pacote(self):
        """`-m l2scanner` (pelado) e o caminho do `--mercado`.

        Chamar o pacote obrigaria `l2scanner/__main__.py` a saber que o
        dashboard existe -- e a promessa do DASH-06 e exatamente que ele NAO
        precisa mudar uma linha. A expressao usa `(?!\\.)` porque
        `-m l2scanner.dashboard` contem `-m l2scanner` como substring: um teste
        ingenuo acusaria a linha certa.
        """
        culpadas = [
            linha
            for linha in _linhas_executaveis(_texto())
            if re.search(r"-m\s+l2scanner(?![\w.])", linha)
        ]
        assert not culpadas, (
            f"o lancador do dashboard chama o ponto de entrada do pacote: "
            f"{culpadas}"
        )

    def test_a_linha_de_execucao_repassa_os_argumentos_extras(self):
        """Sem o `%*`, mudar a porta exigiria editar o fonte.

        Porta ocupada e o desfecho mais provavel deste lancador depois de "deu
        certo" -- as faixas que o Windows reserva mudam a cada boot --, e a
        saida que o programa oferece na mensagem de recusa e `--porta`. Ela so
        existe se o `.bat` repassar.
        """
        t = _texto()
        fim = _posicao_da_execucao(t)
        comeco = t.rfind(chr(10), 0, fim) + 1
        linha = t[comeco:fim]
        assert "%*" in linha, (
            f"a linha de execucao nao repassa os argumentos extras: {linha!r}"
        )

    def test_o_lancador_NAO_abre_o_navegador(self):
        """Quem abre e o `main` do Python, DEPOIS de o bind ter dado certo.

        Abrir aqui mostraria uma aba de erro de conexao justamente no caso da
        porta ocupada -- o caso em que o usuario mais precisa ler a mensagem que
        esta na janela preta.
        """
        culpadas = [
            linha
            for linha in _linhas_executaveis(_texto())
            if re.search(r"\bstart\b|explorer|rundll32", linha, re.IGNORECASE)
        ]
        assert not culpadas, (
            f"o lancador abre o navegador por conta propria: {culpadas}"
        )


class TestAOrdemDosBlocosEEstrutural:
    """O coracao do molde, e a razao de ele existir esta medida em campo.

    Em 2026-08-28 o `calibrar-mercado.bat` imprimiu o bloco de conferencia
    DEPOIS de a ferramenta ter saido em codigo 1. A correcao estrutural -- e nao
    por guarda -- e nao ter o que imprimir depois: os blocos de erro moram
    ACIMA da execucao, alcancados por desvio, e o resumo sai do proprio
    programa.
    """

    def test_toda_linha_de_mensagem_vem_ANTES_da_linha_de_execucao(self):
        t = _texto()
        fim = _posicao_da_execucao(t)
        assert fim != -1, "sumiu a linha de execucao do dashboard"

        posteriores = [(p, linha) for p, linha in _linhas_de_echo(t) if p > fim]
        assert not posteriores, (
            "o .bat ganhou echos depois da linha de execucao "
            f"({[linha for _, linha in posteriores]}). Eles ate poderiam ser "
            "legitimos atras de um `if errorlevel`, mas a via que este arquivo "
            "escolheu -- blocos de erro ACIMA da execucao, nada impresso abaixo "
            "-- deixou de valer, e este teste precisa ser reescrito de olho nela."
        )

    def test_a_ULTIMA_mensagem_esta_antes_da_execucao(self):
        """A mesma verdade dita como comparacao de posicao, que e a forma em que
        o criterio de aceitacao a cobra."""
        t = _texto()
        fim = _posicao_da_execucao(t)
        echos = _linhas_de_echo(t)
        assert echos, "o lancador nao tem mensagem nenhuma para o usuario"
        assert max(p for p, _ in echos) < fim

    def test_existe_rotulo_de_erro_alcancado_por_DESVIO(self):
        t = _texto()
        rotulos = _rotulos(t)
        desvios = _desvios(t)
        de_erro = {
            nome for nome in rotulos if nome.lower().startswith("erro")
        } & desvios
        assert de_erro, (
            f"nenhum rotulo de erro e alcancado por `goto`. Rotulos: "
            f"{sorted(rotulos)}; desvios: {sorted(desvios)}"
        )

    def test_o_desvio_POR_CIMA_dos_blocos_de_erro_existe(self):
        """`goto executar` acima, `:executar` abaixo dos blocos de erro.

        Sem o desvio, o caminho feliz CAIRIA dentro do primeiro bloco de erro e
        o lancador imprimiria uma falha que nao aconteceu -- a mesma familia de
        mentira, pela porta dos fundos.
        """
        t = _texto()
        rotulos = _rotulos(t)
        assert "executar" in rotulos, "sumiu o rotulo `:executar`"
        assert "executar" in _desvios(t), "sumiu o `goto executar`"

        posicao_do_desvio = t.index("goto executar")
        de_erro = [
            posicao
            for nome, posicao in rotulos.items()
            if nome.lower().startswith("erro")
        ]
        assert de_erro, "sumiram os blocos de erro"
        assert posicao_do_desvio < min(de_erro), (
            "o `goto executar` esta DEPOIS do primeiro bloco de erro"
        )
        assert rotulos["executar"] > max(de_erro), (
            "o `:executar` esta ACIMA de algum bloco de erro, entao o caminho "
            "feliz nao passa por cima deles"
        )

    def test_todo_bloco_de_erro_encerra_com_codigo_de_falha(self):
        """Sair com 0 depois de recusar mentiria para quem encadeia o `.bat`."""
        t = _texto()
        rotulos = _rotulos(t)
        for nome, posicao in sorted(rotulos.items(), key=lambda par: par[1]):
            if not nome.lower().startswith("erro"):
                continue
            proximos = [p for p in rotulos.values() if p > posicao]
            fim = min(proximos) if proximos else len(t)
            assert "exit /b 1" in t[posicao:fim], (
                f"o bloco `:{nome}` nao encerra com `exit /b 1`"
            )

    def test_o_auxiliar_de_ordem_ACUSA_uma_mensagem_depois_da_execucao(self):
        """CONTROLE NEGATIVO, e ele e a razao de os testes acima significarem
        alguma coisa.

        Sem esta prova, um erro no reconhecimento das linhas de mensagem (um
        `echo` que o auxiliar deixasse passar, ou uma execucao que ele nao
        achasse) deixaria `test_toda_linha_de_mensagem_vem_ANTES...` verde sobre
        QUALQUER arquivo -- inclusive sobre um que repetisse o defeito de
        2026-08-28 letra por letra. A promessa estrutural que o molde existe
        para garantir viraria decorativa.

        A mutacao acontece sobre texto fabricado aqui, e nao sobre o arquivo
        real.
        """
        torto = (
            "@echo off\r\n"
            'cd /d "%~dp0"\r\n'
            '".venv\\Scripts\\python.exe" -m l2scanner.dashboard %*\r\n'
            "echo  Pronto! O dashboard abriu, e nada deu errado.\r\n"
            "pause\r\n"
        )
        fim = _posicao_da_execucao(torto)
        assert fim != -1, "o auxiliar nao achou a execucao no texto fabricado"
        posteriores = [(p, linha) for p, linha in _linhas_de_echo(torto) if p > fim]
        assert posteriores, (
            "o auxiliar de ordem NAO acusou uma mensagem depois da execucao: "
            "ele nao esta medindo o que diz medir"
        )
        assert posteriores[0][1].startswith("echo  Pronto!")

        # E o outro sentido: com a mesma mensagem ACIMA da execucao, ele nao
        # acusa. Sem esta metade, um auxiliar que acusasse SEMPRE tambem
        # passaria na assercao de cima.
        certo = (
            "@echo off\r\n"
            "echo  Subindo o dashboard...\r\n"
            '".venv\\Scripts\\python.exe" -m l2scanner.dashboard %*\r\n'
            "pause\r\n"
        )
        fim_certo = _posicao_da_execucao(certo)
        assert fim_certo != -1
        assert not [p for p, _ in _linhas_de_echo(certo) if p > fim_certo]


class TestOLancadorNaoInstalaSobreUmAmbienteJaMontado:
    """Esta janela e feita para ser aberta COM O SCANNER FARMANDO.

    O motivo esta MEDIDO em `ponte-discord.bat` e prendido em
    `tests/test_ponte_bat.py`: os pinos do `requirements.txt` sao abertos, entao
    rodar o instalador com o outro processo de pe escreveria por cima de
    `cv2.pyd` e das DLLs do numpy com elas CARREGADAS -- falha de arquivo
    travado, ou um upgrade silencioso da pilha numerica no meio da coleta. Seria
    esta janela derrubando a coleta da noite, que e o oposto do que o DASH-06
    promete.

    O QUE CONTINUA PERMITIDO e montar o ambiente quando ele AINDA NAO EXISTE: se
    `.venv\\Scripts\\python.exe` nao esta no disco, nenhum processo pode estar
    rodando a partir dele.
    """

    def test_todo_pip_install_esta_dentro_da_guarda_de_ambiente_ausente(self):
        t = _texto()
        guarda = t.find('if not exist ".venv\\Scripts\\python.exe" (')
        assert guarda != -1, "sumiu a guarda de ambiente ausente"
        fim_da_guarda = t.index("\n)", guarda)

        fora = []
        posicao = 0
        for linha in t.splitlines(keepends=True):
            despida = linha.strip()
            comeco = posicao
            posicao += len(linha)
            if despida.lower().startswith("rem") or "pip install" not in despida:
                continue
            if not (guarda < comeco < fim_da_guarda):
                fora.append(despida)
        assert not fora, (
            f"ha `pip install` fora da guarda de ambiente ausente: {fora}. Com "
            f"a coleta rodando, isso escreveria por cima de bibliotecas "
            f"CARREGADAS pelo outro processo."
        )

    def test_a_sonda_que_falha_RECUSA_em_vez_de_instalar(self):
        """O irmao do mercado instala quando a sonda falha; este manda rodar o
        irmao. A diferenca e deliberada e mora na linha logo abaixo da sonda."""
        t = _texto()
        sonda = t.find('-c "import')
        assert sonda != -1, "sumiu a sonda de dependencias"
        proxima = t.index("\n", t.index("\n", sonda) + 1)
        trecho = t[sonda:proxima]
        assert "goto erro" in trecho, (
            f"a sonda que falha nao desvia para um bloco de recusa: {trecho!r}"
        )


class TestOsSinaisDeMaiorEMenorEstaoEscapados:
    def test_nenhum_sinal_cru_dentro_de_um_echo(self):
        """Um sinal cru dentro de um `echo` vira REDIRECIONAMENTO no cmd.

        Copiado do guarda irmao, onde o proprio bloco de erro morria com "A
        sintaxe do comando esta incorreta" antes de o escape entrar.
        """
        for _, despido in _linhas_de_echo(_texto()):
            if not despido.lower().startswith("echo "):
                continue
            for sinal in ("<", ">"):
                for pos in (i for i, c in enumerate(despido) if c == sinal):
                    assert pos > 0 and despido[pos - 1] == "^", (
                        f"`{sinal}` sem escape num echo do .bat, o cmd trata "
                        f"como redirecionamento: {despido!r}"
                    )
