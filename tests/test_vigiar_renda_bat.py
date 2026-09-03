"""O lancador da RENDA nao pode anunciar o que nao conferiu.

MOLDE LITERAL DE `tests/test_vigiar_mercado_bat.py`, e pelos MESMOS DOIS
DEFEITOS MEDIDOS EM CAMPO. Os onze testes desta familia nao sao cerimonia:
cada um deles prende um desfecho que ja custou uma sessao ao usuario.

O PRIMEIRO DEFEITO, em 2026-08-28: um `.bat` desta arvore imprimiu o bloco de
conferencia DEPOIS de a ferramenta ter saido em codigo 1, mandando o usuario
abrir um arquivo que nunca foi gerado. Este `.bat` fecha o defeito PELA
ESTRUTURA e nao por uma guarda: os blocos de erro ficam ANTES da linha de
execucao, e DEPOIS dela nao ha `echo` nenhum. O resumo da sessao sai do
proprio programa, no `finally` do laco -- que e quem sabe o que aconteceu.

O SEGUNDO DEFEITO, em 2026-08-31: o usuario rodou o `--mercado` pelo Python
GLOBAL, o modo recusou por falta de OCR, e a mensagem de recusa mandou rodar o
`vigiar-party.bat` -- o lancador da PARTY, para consertar o MERCADO. Aqui o
conselho certo e `calibrar-renda.bat`, e o teste do conselho e AMPLIADO: ele
nao so proibe os lancadores das outras features, ele EXIGE que o certo
apareca. Um lancador que nao diz como consertar e tao inutil quanto um que diz
errado.

OS DOIS HELPERS TEM CONTROLE POSITIVO, e isso e regra desta casa e nao
preferencia. `_posicao_da_execucao` e `_linhas_de_echo` ignoram `REM`, porque
a versao ingenua de cada um ja passou sobre um `.bat` QUEBRADO nesta arvore --
enganada pelo proprio comentario que explicava o defeito. Um portao sem
controle que prove que ele ACUSA e um portao que nao mede nada.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BAT = RAIZ / "vigiar-renda.bat"

# As duas flags que fazem deste .bat o modo renda. `--renda` sozinho e
# recusado pelo proprio argparse ("--renda exige --janela").
FLAGS_DO_MODO = ("--renda", "--janela")

# Flags que dizem ONDE ESCREVER ou DE ONDE LER ARQUIVO. Nenhuma pode entrar
# pelo lancador: a `.renda/` do usuario e dado acumulado sem desfazer, e o
# `--replay` alimentaria o registro com uma gravacao antiga como se fosse a
# tela de agora -- uma noite antiga entrando como a de hoje envenenaria toda
# taxa dali para a frente. O lancador nao pode ser essa porta.
FLAGS_DE_DESTINO_DE_ARQUIVO = (
    "--record",
    "--record-janela",
    "--replay",
    "--gravacao",
    "--frame",
    "--pasta",
    "--saida",
    "--destino",
    "--arquivo",
    "--out",
)

# Os lancadores das OUTRAS features. Este arquivo pode CITA-LOS em `REM`, que
# o cmd nao imprime, para dizer o que eles fazem e este aqui nao -- mas nao
# pode MANDAR o usuario rodar um deles para consertar a renda.
LANCADORES_DE_OUTRA_FEATURE = (
    "vigiar-party.bat",
    "vigiar-mercado.bat",
    "calibrar.bat",
)

# O conselho CERTO desta feature.
CONSELHO_CERTO = "calibrar-renda.bat"


def _texto() -> str:
    # cp1252 e nao utf-8: e a pagina de codigo em que o cmd do Windows le o
    # arquivo, e e por isso que o `.bat` inteiro e ASCII puro. Ler aqui na
    # mesma codificacao do interpretador de verdade e o que faz este arquivo
    # medir o que o usuario vai executar.
    return BAT.read_text(encoding="cp1252")


def _linhas_de_echo(texto: str) -> list[tuple[int, str]]:
    """(posicao, linha) de cada linha que o cmd EXECUTA como `echo`.

    Comentario `REM` NAO CONTA, e a razao e a mesma do teste irmao: a primeira
    versao daquele guarda foi enganada pelo proprio comentario que explicava o
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
    """Onde termina a linha que roda o modo renda."""
    for casamento in re.finditer(r"^.*-m l2scanner .*$", texto, re.MULTILINE):
        linha = casamento.group(0)
        if linha.strip().lower().startswith("rem"):
            continue
        if all(flag in linha for flag in FLAGS_DO_MODO):
            return casamento.end()
    return -1


def test_o_bat_existe():
    assert BAT.is_file(), "vigiar-renda.bat sumiu"


def test_o_bat_e_ascii_puro():
    """Acento em .bat sai como lixo no console do cmd.

    O console herda a codepage da maquina (850/437 no Brasil) e o arquivo e
    escrito como UTF-8 por quem edita. Um caractere acentuado vira dois
    caracteres ilegiveis para o usuario -- e este arquivo e, literalmente,
    texto para ser lido por ele.
    """
    bruto = BAT.read_bytes()
    ruins = [(i, b) for i, b in enumerate(bruto) if b > 127]
    assert not ruins, f"bytes nao-ASCII no .bat: {ruins[:5]}"


def test_a_linha_de_execucao_carrega_as_duas_flags_do_modo():
    """`--renda` e `--janela` na MESMA linha, executada e nao comentada."""
    t = _texto()
    assert _posicao_da_execucao(t) != -1, (
        "nao ha nenhuma linha EXECUTADA que rode `-m l2scanner` com "
        f"{FLAGS_DO_MODO} juntas"
    )


def test_a_linha_de_execucao_so_carrega_as_duas_flags_do_modo():
    """Nenhuma terceira flag entra escondida na linha de execucao.

    O `%*` no fim continua deixando o usuario acrescentar o que quiser na
    linha de comando -- inclusive `--intervalo` e `--status-a-cada`, que sao a
    cadencia do laco e a do bloco. O que este guarda prende e o que o .bat
    decide SOZINHO, sem o usuario ver.
    """
    t = _texto()
    fim = _posicao_da_execucao(t)
    comeco = t.rfind(chr(10), 0, fim) + 1
    linha = t[comeco:fim]
    flags = set(re.findall(r"--[a-z][a-z-]*", linha))
    assert flags == set(FLAGS_DO_MODO), (
        f"a linha de execucao carrega {sorted(flags)}, e nao "
        f"{sorted(FLAGS_DO_MODO)}: {linha!r}"
    )


def test_o_janela_vai_com_valor_e_nao_pelado():
    """`--janela` sem valor so acerta com UMA janela do jogo aberta.

    MEDIDO NA MAQUINA DO USUARIO: ele roda DUAS instancias. Com `--janela`
    pelado e sem `janela` gravada na calibracao, o `__main__` enumera as
    janelas do jogo, acha duas e RECUSA -- o lancador de dois cliques morreria
    pedindo uma linha de comando, que e exatamente o que ele existe para
    evitar. E aqui e pior que no mercado: EXP e adena sao DO PERSONAGEM, e
    mirar a instancia errada grava a renda de um char no arquivo do outro.
    """
    t = _texto()
    fim = _posicao_da_execucao(t)
    comeco = t.rfind(chr(10), 0, fim) + 1
    linha = t[comeco:fim]
    depois_do_janela = linha.split("--janela", 1)[1].lstrip()
    assert depois_do_janela.startswith('"'), (
        f"`--janela` foi passado sem valor entre aspas: {linha!r}"
    )


def test_a_mira_vem_da_chave_do_config_e_nao_so_de_um_nome_escrito_aqui():
    """O nome do personagem tem UMA fonte de verdade, e ela e o config.toml.

    Mesmo precedente do `calibrar --auto`, que le `ler_personagem_do_jogo()`
    em vez de carregar um nick no fonte. O padrao escrito no .bat e o ultimo
    recurso e PERDE para a chave.

    E o SUFIXO do titulo vem das constantes do CODIGO (`SEPARADOR` e
    `NOME_DO_CLIENTE`), e nao reescrito aqui: uma segunda copia de
    " - XM Essence" envelheceria sozinha, e a mira passaria a mirar um titulo
    que o jogo nao usa mais.

    A AFIRMACAO E SOBRE A LINHA QUE MONTA A MIRA, e nao sobre o arquivo
    inteiro. Medido ao escrever este teste: a versao do guarda irmao pergunta
    `"ler_personagem_do_jogo" in texto`, e ela PASSA sobre um `.bat` mutado
    para `print(sys.argv[1] + SEPARADOR + NOME_DO_CLIENTE)` -- porque o nome
    sobrevive na clausula `import` da mesma linha. Um `.bat` assim ignora a
    chave do config e mira sempre o padrao escrito a mao, que e exatamente o
    defeito que este teste existe para prender.
    """
    t = _texto()
    fim = _posicao_da_execucao(t)

    montagem = next(
        (
            linha
            for linha in t.splitlines()
            if 'set "JANELA=%%t"' in linha
        ),
        None,
    )
    assert montagem is not None, (
        "sumiu o `for /f` que monta o titulo da janela em JANELA"
    )
    assert "ler_personagem_do_jogo()" in montagem, (
        "a linha que monta a mira nao CHAMA `ler_personagem_do_jogo()`: a "
        "mira voltou a ser um nome escrito a mao, errado para qualquer outra "
        f"maquina. Linha: {montagem!r}"
    )
    assert t.index('set "JANELA=%%t"') < fim, (
        "a leitura da chave acontece DEPOIS da execucao, entao ela nao mira "
        "nada"
    )
    for constante in ("SEPARADOR", "NOME_DO_CLIENTE"):
        assert constante in montagem, (
            f"o sufixo do titulo deixou de vir de `{constante}`: o .bat "
            f"passou a carregar uma segunda verdade sobre o titulo da janela"
        )


def test_o_lancador_recusa_quando_nao_consegue_montar_a_mira():
    """Sem titulo resolvido, ele PARA -- nao chuta e nao roda pelado.

    Um TOML quebrado faz a leitura da chave falhar; o `for /f` nao produz
    linha nenhuma e a variavel fica indefinida. Rodar assim passaria um
    `--janela` vazio para o programa.
    """
    t = _texto()
    guarda = t.find("if not defined JANELA (")
    assert guarda != -1, "sumiu a recusa por mira nao resolvida"
    assert guarda < _posicao_da_execucao(t), (
        "a recusa por mira nao resolvida vem DEPOIS da execucao"
    )
    trecho = t[guarda : t.index(")", guarda) + 1]
    assert "exit /b 1" in trecho, (
        "a recusa nao encerra com `exit /b 1`; um chamador veria sucesso"
    )


def test_nenhum_echo_depois_da_execucao_fica_fora_de_guarda_de_errorlevel():
    """A promessa de nao anunciar o que nao conferiu, medida no texto.

    ESTE .bat PASSA PELA VIA MAIS FORTE: nao ha `echo` nenhum depois da linha
    de execucao, porque os blocos de erro moram ACIMA dela. As duas afirmacoes
    estao aqui de proposito -- a primeira e a regra que vale para qualquer
    edicao futura, a segunda registra por qual caminho o arquivo de hoje a
    satisfaz.
    """
    t = _texto()
    fim = _posicao_da_execucao(t)
    assert fim != -1, "sumiu a linha de execucao do modo renda"

    posteriores = [(p, linha) for p, linha in _linhas_de_echo(t) if p > fim]
    guarda = t.find("if errorlevel", fim)

    desprotegidos = [
        linha for p, linha in posteriores if guarda == -1 or p < guarda
    ]
    assert not desprotegidos, (
        "estes echos saem depois da execucao sem nenhuma checagem de "
        f"errorlevel entre eles e ela: {desprotegidos}"
    )

    assert not posteriores, (
        "o .bat ganhou echos depois da linha de execucao "
        f"({[linha for _, linha in posteriores]}). Eles ate podem ser "
        "legitimos atras de um `if errorlevel`, mas a via que este arquivo "
        "escolheu -- blocos de erro ACIMA da execucao, nada impresso abaixo "
        "-- deixou de valer, e este teste precisa ser reescrito de olho nela."
    )


def test_o_bat_nao_carrega_flag_de_destino_de_arquivo():
    """A guarda que protege a `.renda/` nao pode ser furada pelo lancador."""
    t = _texto()
    achadas = [flag for flag in FLAGS_DE_DESTINO_DE_ARQUIVO if flag in t]
    assert not achadas, (
        f"o lancador carrega flag de destino de arquivo: {achadas}. O modo "
        f"grava em .renda/, que e dado acumulado sem desfazer."
    )


def test_nenhum_echo_manda_rodar_o_lancador_de_outra_feature():
    """O conselho torto medido em campo, prendido no lancador certo.

    Em 2026-08-31 o usuario rodou o `--mercado` pelo Python global, o modo
    recusou por falta de OCR e a mensagem mandou rodar o `vigiar-party.bat`.
    Este arquivo pode CITAR os outros lancadores em `REM` -- que o cmd nao
    imprime -- para dizer o que eles fazem e este aqui nao. O que ele nao pode
    e MANDAR o usuario rodar a party, ou o mercado, ou o calibrador da party,
    para consertar a renda.
    """
    t = _texto()
    culpados = [
        (alvo, linha)
        for _, linha in _linhas_de_echo(t)
        for alvo in LANCADORES_DE_OUTRA_FEATURE
        if alvo in linha
    ]
    assert not culpados, (
        f"o lancador da renda manda rodar o lancador de outra feature: "
        f"{culpados}"
    )


def test_o_conselho_certo_aparece_num_echo():
    """Nao basta nao dizer errado: tem de dizer certo.

    Um lancador que recusa sem apontar o conserto e tao inutil quanto um que
    aponta o conserto da feature errada -- o usuario fica com a mesma pergunta
    e sem a resposta. Quem grava os retangulos e os pisos da renda e o
    `calibrar-renda.bat`, e ele tem de estar numa linha que o cmd IMPRIME.
    """
    t = _texto()
    onde = [linha for _, linha in _linhas_de_echo(t) if CONSELHO_CERTO in linha]
    assert onde, (
        f"nenhum `echo` deste lancador cita o {CONSELHO_CERTO}: quando a mira "
        f"nao monta ou a leitura recusa, o usuario nao fica sabendo o que "
        f"rodar"
    )


def test_o_lancador_nao_carrega_personagem():
    """O nome sai do TITULO, e uma segunda verdade sobre a mesma janela e um
    defeito medido.

    `renda_modo.py:325-335` deriva o personagem do titulo da janela mirada, e
    o `03-CONTEXT.md` cravou esse caminho. Um `--personagem` no lancador seria
    a porta pela qual a leitura voltaria a poder cair no personagem errado:
    o titulo diria uma coisa e a flag outra, e a calibracao da renda -- que e
    POR PERSONAGEM -- seguiria a flag.
    """
    t = _texto()
    assert "--personagem" not in t, (
        "o lancador ganhou `--personagem`: agora ha duas verdades sobre de "
        "quem e a tela, e a mais facil de errar vence"
    )


def test_os_sinais_de_maior_e_menor_estao_escapados():
    """Um sinal cru dentro de um echo vira redirecionamento no cmd.

    Copiado do guarda irmao, onde o proprio bloco de erro morria com "A
    sintaxe do comando esta incorreta" antes de o escape entrar.
    """
    t = _texto()
    for _, despido in _linhas_de_echo(t):
        if not despido.lower().startswith("echo "):
            continue
        for sinal in ("<", ">"):
            for pos in (i for i, c in enumerate(despido) if c == sinal):
                assert pos > 0 and despido[pos - 1] == "^", (
                    f"`{sinal}` sem escape num echo do .bat, o cmd trata como "
                    f"redirecionamento: {despido!r}"
                )


def test_o_bat_chama_o_python_do_venv_por_caminho_literal():
    """Sem `activate` e sem `uv`, como todos os .bat da raiz.

    O duodecimo teste da familia, herdado de `tests/test_ponte_bat.py:102`.
    Ele VALE aqui por uma razao propria e nao por simetria: o defeito de
    2026-08-31 foi o modo rodado pelo Python GLOBAL, onde o OCR nao existe. O
    caminho literal para o `.venv` e o que torna aquele desfecho impossivel
    por este lancador -- `activate` num duplo clique e o passo que o usuario
    esquece; o caminho entre aspas nao tem como ser esquecido.
    """
    t = _texto()
    assert '".venv\\Scripts\\python.exe" -m l2scanner --renda' in t, (
        "a execucao deixou de usar o python do .venv por caminho literal: um "
        "Python global sem OCR passaria a poder rodar o modo"
    )


# ---------------------------------------------------------------------------
# OS CONTROLES POSITIVOS.
#
# Todo portao desta casa nasce com um controle que prova que ele ACUSA. Estes
# tres nao olham para o `vigiar-renda.bat`: eles alimentam os helpers com um
# texto sintetico QUEBRADO e exigem que o helper o pegue. Sem eles, um helper
# que aceitasse qualquer coisa passaria -- e ja passou, com o `.bat` do
# calibrador quebrado na arvore.
# ---------------------------------------------------------------------------

_LINHA_DE_EXECUCAO = (
    '".venv\\Scripts\\python.exe" -m l2scanner --renda --janela "%JANELA%" %*'
)


def test_controle_a_posicao_da_execucao_nao_conta_a_linha_comentada():
    """As flags SO dentro de um `REM` tem de devolver -1.

    Este e o controle que faltava na primeira versao do helper irmao: o
    comentario que EXPLICAVA o defeito continha as flags, e o guarda ingenuo
    achou nele a "linha de execucao" de um `.bat` que nao executava nada.
    """
    comentado = "@echo off\r\nREM " + _LINHA_DE_EXECUCAO + "\r\npause\r\n"
    assert _posicao_da_execucao(comentado) == -1, (
        "o helper achou linha de execucao num texto onde as flags estao SO "
        "dentro de um REM -- ele passaria sobre um .bat que nao roda nada"
    )

    executado = "@echo off\r\n" + _LINHA_DE_EXECUCAO + "\r\npause\r\n"
    assert _posicao_da_execucao(executado) != -1, (
        "o helper deixou de achar a linha que o cmd DE FATO executa"
    )


def test_controle_as_linhas_de_echo_ignoram_rem_e_acusam_echo():
    """`REM echo ...` nao imprime nada; `echo ...` imprime."""
    texto = (
        "REM echo isto e comentario e o cmd nao mostra\r\n"
        "echo  isto o cmd mostra\r\n"
    )
    achados = [linha for _, linha in _linhas_de_echo(texto)]
    assert achados == ["echo  isto o cmd mostra"], (
        f"o helper de echo confundiu comentario com impressao: {achados}"
    )


def test_controle_o_guarda_acusa_echo_depois_da_execucao():
    """O defeito de 2026-08-28, sintetizado, tem de ser pego.

    Um `.bat` que imprime "Pronto, confira o arquivo" depois de rodar o
    programa anuncia um desfecho que nao conferiu. O guarda de verdade roda
    sobre o arquivo real; este aqui prova que ele SABE acusar.
    """
    quebrado = (
        _LINHA_DE_EXECUCAO
        + "\r\necho  Pronto! Confira o arquivo em .renda\\\r\npause\r\n"
    )
    fim = _posicao_da_execucao(quebrado)
    assert fim != -1
    posteriores = [linha for p, linha in _linhas_de_echo(quebrado) if p > fim]
    assert posteriores, (
        "o guarda nao acusaria um `echo` depois da linha de execucao -- que e "
        "exatamente o defeito medido em 2026-08-28"
    )
