"""O lancador do MERCADO nao pode anunciar o que nao conferiu.

MOLDE LITERAL DE `tests/test_calibrar_mercado_bat.py`, e pelo mesmo defeito
MEDIDO EM CAMPO em 2026-08-28: aquele .bat imprimia o bloco de conferencia
depois de a ferramenta ter saido em codigo 1, mandando o usuario abrir um
arquivo que nunca foi gerado.

ESTE .bat FECHA O DEFEITO PELA ESTRUTURA, e nao por uma guarda: os blocos de
erro ficam ANTES da linha de execucao, e DEPOIS dela nao ha `echo` nenhum. O
resumo da sessao sai do proprio programa, no `finally` do laco -- que e quem
sabe o que aconteceu.

O SEGUNDO DEFEITO QUE ESTE ARQUIVO PRENDE foi medido em 2026-08-31: o usuario
rodou o `--mercado` pelo Python GLOBAL, o modo recusou por falta de OCR, e a
mensagem de recusa mandou rodar o `vigiar-party.bat` -- o lancador da PARTY,
para consertar o MERCADO. Este .bat existe para que exista o conselho certo, e
os testes abaixo prendem que ele nao repita o torto.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BAT = RAIZ / "vigiar-mercado.bat"

# As duas flags que fazem deste .bat o modo mercado. `--mercado` sozinho e
# recusado pelo proprio argparse ("--mercado exige --janela").
FLAGS_DO_MODO = ("--mercado", "--janela")

# Flags que dizem ONDE ESCREVER ou DE ONDE LER ARQUIVO. Nenhuma pode entrar
# pelo lancador: a `.mercado/` do usuario e dado acumulado sem desfazer, e o
# `--replay` alimentaria o registro com uma gravacao antiga como se fosse a
# tela de agora. O lancador nao pode ser essa porta.
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


def _texto() -> str:
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
    """Onde termina a linha que roda o modo mercado."""
    for casamento in re.finditer(r"^.*-m l2scanner .*$", texto, re.MULTILINE):
        linha = casamento.group(0)
        if linha.strip().lower().startswith("rem"):
            continue
        if all(flag in linha for flag in FLAGS_DO_MODO):
            return casamento.end()
    return -1


def test_o_bat_existe():
    assert BAT.is_file(), "vigiar-mercado.bat sumiu"


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
    """`--mercado` e `--janela` na MESMA linha, executada e nao comentada."""
    t = _texto()
    assert _posicao_da_execucao(t) != -1, (
        "nao ha nenhuma linha EXECUTADA que rode `-m l2scanner` com "
        f"{FLAGS_DO_MODO} juntas"
    )


def test_a_linha_de_execucao_so_carrega_as_duas_flags_do_modo():
    """Nenhuma terceira flag entra escondida na linha de execucao.

    O `%*` no fim continua deixando o usuario acrescentar o que quiser na
    linha de comando -- o que este guarda prende e o que o .bat decide
    SOZINHO, sem o usuario ver.
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

    MEDIDO NA MAQUINA DO USUARIO: ele roda DUAS instancias de party. Com
    `--janela` pelado e sem `janela` gravada na calibracao, o `__main__`
    enumera as janelas do jogo, acha duas e RECUSA -- o lancador de dois
    cliques morreria pedindo uma linha de comando, que e exatamente o que ele
    existe para evitar.
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
    recurso e PERDE para a chave -- ha um teste de bancada em `cmd` que mediu
    os dois desfechos ao escrever este arquivo.
    """
    t = _texto()
    assert "ler_personagem_do_jogo" in t, (
        "o .bat nao le mais a chave [jogo] personagem: a mira voltou a ser um "
        "nome escrito a mao, errado para qualquer outra maquina"
    )
    fim = _posicao_da_execucao(t)
    assert t.index("ler_personagem_do_jogo") < fim, (
        "a leitura da chave acontece DEPOIS da execucao, entao ela nao mira "
        "nada"
    )


def test_o_lancador_recusa_quando_nao_consegue_montar_a_mira():
    """Sem titulo resolvido, ele PARA -- nao chuta e nao roda pelado.

    Um TOML quebrado faz a leitura da chave falhar; medido em bancada, o
    `for /f` nao produz linha nenhuma e a variavel fica indefinida. Rodar
    assim passaria um `--janela` vazio para o programa.
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
    assert fim != -1, "sumiu a linha de execucao do modo mercado"

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
    """A guarda que protege a `.mercado/` nao pode ser furada pelo lancador."""
    t = _texto()
    achadas = [flag for flag in FLAGS_DE_DESTINO_DE_ARQUIVO if flag in t]
    assert not achadas, (
        f"o lancador carrega flag de destino de arquivo: {achadas}. O modo "
        f"grava em .mercado/, que e dado acumulado sem desfazer."
    )


def test_nenhum_echo_manda_rodar_o_lancador_da_party():
    """O conselho torto medido em campo, prendido no lancador certo.

    Em 2026-08-31 o usuario rodou o `--mercado` pelo Python global, o modo
    recusou por falta de OCR e a mensagem mandou rodar o `vigiar-party.bat`.
    Este arquivo pode CITAR o lancador da party para dizer o que ele faz e
    este aqui nao -- em `REM`, que o cmd nao imprime -- mas nao pode MANDAR o
    usuario rodar a party para consertar o mercado.
    """
    t = _texto()
    culpados = [
        linha for _, linha in _linhas_de_echo(t) if "vigiar-party" in linha
    ]
    assert not culpados, (
        f"o lancador do mercado manda rodar o lancador da party: {culpados}"
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
