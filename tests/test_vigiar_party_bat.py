"""O `vigiar-party.bat` pergunta qual char vigiar, so quando precisa.

O DEFEITO MEDIDO: com duas janelas do XM Essence abertas (Faerlina e
Yazalaque), o `.bat` sempre chamava `--janela` sem valor. Se a calibracao
tinha `janela` gravada, o scanner usava aquele titulo SEMPRE — mesmo que o
usuario tivesse aberto outro char nesta sessao, pegando o char errado sem
avisar nada.

V1, ESCOLHA UNICA: o `.bat` deixa escolher UMA das janelas abertas — nunca
vigiar as duas ao mesmo tempo. So pergunta no clique duplo (sem argumento
nenhum) e so quando ha DUAS OU MAIS janelas abertas. Zero ou uma janela
continuam sem pergunta nenhuma, exatamente como hoje.

MESMO PRINCIPIO JA CORRIGIDO NO `calibrar.bat`: quem passa argumento na
linha de comando NAO e perguntado de novo (ver `tests` daquele arquivo e o
comentario em `calibrar.bat` datado de 31/08/2026).

ESTE ARQUIVO TESTA TEXTO, NAO EXECUTA O `.bat` — o mesmo estilo de
`tests/test_vigiar_mercado_bat.py`: posicoes de string, nao um interpretador
de cmd. `cmd.exe` so existe no Windows, e a suite roda no CI tambem.
"""

from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BAT = RAIZ / "vigiar-party.bat"


def _texto() -> str:
    return BAT.read_text(encoding="cp1252")


def test_o_bat_existe():
    assert BAT.is_file(), "vigiar-party.bat sumiu"


def test_o_bat_e_ascii_puro():
    """Acento em .bat sai como lixo no console do cmd (codepage 850/437)."""
    bruto = BAT.read_bytes()
    ruins = [(i, b) for i, b in enumerate(bruto) if b > 127]
    assert not ruins, f"bytes nao-ASCII no .bat: {ruins[:5]}"


def test_usa_a_flag_listar_janelas_e_nao_um_python_dash_c_inline():
    """A razao de existir de --listar-janelas: aspas simples e duplas juntas
    dentro de um `for /f ('comando')` quebram o cmd.

    So conta linhas EXECUTADAS (nao REM): o proprio comentario que explica
    a razao de existir da flag cita "python -c" como o que NAO fazer, e
    isso nao pode derrubar o teste.
    """
    t = _texto()
    assert "--listar-janelas" in t, (
        "o .bat nao usa --listar-janelas para descobrir as janelas abertas"
    )
    executadas = [
        linha
        for linha in t.splitlines()
        if not linha.strip().lower().startswith("rem")
    ]
    assert not any("python -c" in linha.lower() for linha in executadas), (
        "o .bat tenta listar janelas com python -c inline (fora de um "
        "comentario) — isso quebra por causa do conflito de aspas com o "
        "for /f do cmd"
    )


def test_quem_passa_argumento_nao_e_perguntado():
    """`if "%~1"=="" ... call :escolher_janela` — mesmo principio do
    calibrar.bat: argumento na linha de comando pula a pergunta."""
    t = _texto()
    assert 'if "%~1"=="" call :escolher_janela' in t, (
        "nao ha guarda condicionando a escolha a `%~1` vazio — quem passa "
        "argumento tambem seria perguntado"
    )


def test_a_sub_rotina_de_escolha_existe_e_e_chamada_antes_da_execucao():
    t = _texto()
    chamada = t.find("call :escolher_janela")
    rotulo = t.find("\n:escolher_janela")
    execucao = t.find("-m l2scanner --janela")
    assert chamada != -1, "falta a chamada para a sub-rotina de escolha"
    assert rotulo != -1, "falta o rotulo :escolher_janela"
    assert chamada < execucao, (
        "a escolha precisa acontecer ANTES da linha que executa o scanner"
    )


def test_zero_janelas_nao_prompta_e_cai_no_caminho_de_hoje():
    """N==0: sem pergunta, JANELA_ESCOLHIDA fica vazia, o .bat cai no
    --janela sem valor de sempre e o proprio scanner explica que nao achou
    janela nenhuma."""
    t = _texto()
    assert 'if "!N!"=="0"' in t, "falta o caminho de 0 janelas (sem pergunta)"


def test_uma_janela_nao_prompta_e_usa_o_titulo_direto():
    t = _texto()
    assert 'if "!N!"=="1"' in t, "falta o caminho de 1 janela (sem pergunta)"


def test_duas_ou_mais_janelas_perguntam_com_menu_numerado():
    t = _texto()
    assert "set /p ESCOLHA=" in t, "falta o prompt interativo para 2+ janelas"
    # O menu precisa listar cada titulo com um numero na frente.
    assert "for /l %%i in (1,1,!N!)" in t, (
        "falta o loop que imprime o menu numerado com todas as janelas"
    )


def test_numero_invalido_ou_vazio_pede_de_novo_em_vez_de_travar():
    t = _texto()
    assert 'if "!ESCOLHA!"=="" goto pedir_numero' in t, (
        "entrada vazia deveria pedir de novo, e nao travar ou usar um "
        "default silencioso"
    )
    assert "Numero invalido" in t, (
        "escolha fora da faixa deveria avisar e pedir de novo"
    )


def test_a_janela_escolhida_entra_entre_aspas_na_execucao():
    """Os titulos tem espaco (`Yazalaque - XM Essence`) — sem aspas o cmd
    quebraria em varios argumentos."""
    t = _texto()
    assert '--janela "%JANELA_ESCOLHIDA%"' in t, (
        "a janela escolhida nao entra entre aspas na linha de execucao"
    )


def test_o_caminho_sem_escolha_continua_byte_a_byte_igual_a_hoje():
    """Quando ninguem escolheu nada (0 janelas, ou argumento passado), a
    invocacao cai de volta para `--janela %*` -- o comportamento de hoje,
    intocado."""
    t = _texto()
    assert "-m l2scanner --janela %*" in t, (
        "sumiu o caminho de fallback --janela %* (o comportamento de hoje)"
    )


def test_comentario_explica_por_que_so_uma_escolha_na_v1():
    t = _texto()
    baixo = t.lower()
    assert "vigiar as duas" in baixo or "uma escolha" in baixo, (
        "falta um comentario explicando por que a v1 nao oferece vigiar as "
        "duas janelas ao mesmo tempo"
    )


def test_os_sinais_de_maior_e_menor_estao_escapados():
    """Mesmo guarda de `test_vigiar_mercado_bat.py`: um `<`/`>` cru num echo
    vira redirecionamento no cmd."""
    t = _texto()
    for linha in t.splitlines():
        despido = linha.strip()
        if not despido.lower().startswith("echo "):
            continue
        for sinal in ("<", ">"):
            for pos in (i for i, c in enumerate(despido) if c == sinal):
                assert pos > 0 and despido[pos - 1] == "^", (
                    f"`{sinal}` sem escape num echo do .bat: {despido!r}"
                )
