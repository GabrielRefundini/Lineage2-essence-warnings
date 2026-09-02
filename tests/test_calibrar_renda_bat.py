"""O .bat da renda nao pode mentir que deu certo.

Este arquivo e uma COPIA DELIBERADA de `tests/test_calibrar_mercado_bat.py`, e
a duplicacao e o produto: o `.bat` e um arquivo de TEXTO que ninguem importa, e
a unica coisa que impede o proximo a ser escrito de repetir o defeito e existir
uma guarda por `.bat`. O `calibrar-renda.bat` herda o ARQUIVO DE TESTE, e nao
so o formato.

O DANO, MEDIDO EM CAMPO EM 2026-08-28 no irmao dele. O usuario rodou
`calibrar-mercado.bat` sem argumento. A ferramenta recusou corretamente e saiu
com codigo 1 -- mas o .bat imprimia o bloco de conferencia MESMO ASSIM,
mandando o usuario conferir um arquivo que nunca foi gerado. E a mesma mentira
que o FUND-01 tirou do gravador, um nivel acima: dizer que deu certo sem ter
conferido que deu.

E O `_posicao_do_echo` VEM JUNTO, COM A RAZAO DELE. A primeira versao daquele
teste procurava a frase crua no arquivo e foi enganada pelo proprio comentario
`REM` que EXPLICAVA o defeito -- o comentario contem a frase, o teste achava a
frase, e o teste passava com o `.bat` quebrado. Uma guarda que se satisfaz com
prosa nao guarda nada: o que precisa vir depois do `if errorlevel` e a linha
que o cmd EXECUTA, e o `.bat` da renda tem um comentario `REM` explicando
exatamente esta armadilha, entao a versao ingenua deste teste passaria aqui
tambem.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BAT = RAIZ / "calibrar-renda.bat"

# A primeira linha do bloco de sucesso. E so uma ancora de posicao para os
# testes de ordem -- o conteudo dela e afirmado por
# `test_o_bloco_de_sucesso_nao_cita_o_nome_da_imagem`.
ANCORA_DO_SUCESSO = "A MENSAGEM ACIMA diz qual imagem"


def _texto() -> str:
    # cp1252 e nao utf-8: e a pagina de codigo em que o cmd do Windows le o
    # arquivo, e e por isso que o `.bat` inteiro e ASCII puro. Ler aqui na
    # mesma codificacao do interpretador de verdade e o que faz este arquivo
    # medir o que o usuario vai executar.
    return BAT.read_text(encoding="cp1252")


def _posicao_do_echo(texto: str, trecho: str, inicio: int = 0) -> int:
    """Onde um ECHO diz `trecho` -- comentario REM nao conta. Ver a docstring."""
    for casamento in re.finditer(re.escape(trecho), texto):
        if casamento.start() < inicio:
            continue
        comeco_da_linha = texto.rfind(chr(10), 0, casamento.start()) + 1
        linha = texto[comeco_da_linha : casamento.start()].strip().lower()
        if linha.startswith("echo"):
            return casamento.start()
    return -1


def test_o_bat_existe():
    assert BAT.is_file(), "calibrar-renda.bat sumiu"


def test_o_bat_repassa_os_argumentos():
    """Sem `%*` o usuario nao consegue dizer QUAL janela nem QUAL personagem.

    E a calibracao da renda e por personagem: um `.bat` que engolisse os
    argumentos so conseguiria calibrar a janela que a calibracao anterior
    gravou -- ou seja, sempre a mesma instancia.
    """
    t = _texto()
    chamada = t.find("l2scanner.calibrar_renda")
    assert chamada != -1, "o .bat nao chama l2scanner.calibrar_renda"
    fim_da_linha = t.find(chr(10), chamada)
    assert "%*" in t[chamada:fim_da_linha], (
        "a chamada nao repassa `%*`; --janela e --personagem nunca chegariam "
        "na ferramenta"
    )


def test_o_bloco_de_conferencia_vem_depois_de_uma_guarda_de_erro():
    """A guarda tem de estar ENTRE a chamada da ferramenta e o bloco de sucesso.

    Nao basta existir um `if errorlevel` em algum lugar do arquivo: ele precisa
    interromper o caminho antes da mensagem que manda conferir a imagem.
    """
    t = _texto()

    chamada = t.find("l2scanner.calibrar_renda")
    guarda = t.find("if errorlevel 1", chamada)
    conferencia = _posicao_do_echo(t, ANCORA_DO_SUCESSO, chamada)

    assert chamada != -1, "o .bat nao chama mais l2scanner.calibrar_renda"
    assert guarda != -1, "sumiu a guarda `if errorlevel 1` depois da chamada"
    assert conferencia != -1, "sumiu o bloco de conferencia"
    assert guarda < conferencia, (
        "o bloco de conferencia vem ANTES da guarda de erro -- uma recusa da "
        "ferramenta voltaria a anunciar uma calibracao que nao aconteceu"
    )


def test_a_guarda_encerra_o_script_com_codigo_de_falha():
    """Sair com 0 depois de falhar mentiria para quem encadeia o .bat."""
    t = _texto()
    guarda = t.find("if errorlevel 1")
    trecho = t[guarda : _posicao_do_echo(t, ANCORA_DO_SUCESSO, guarda)]
    assert "exit /b 1" in trecho, (
        "a guarda nao encerra com `exit /b 1`; um chamador veria sucesso"
    )


def test_a_mensagem_de_falha_diz_que_nada_foi_gravado():
    """O usuario precisa saber que o disco NAO mudou, nao so que 'deu erro'.

    E aqui isso vale duplo: o `calibration.json` e dividido por quatro features
    e por dois personagens. "Deu erro" deixa o usuario sem saber se ele acabou
    de perder a calibracao do outro personagem.
    """
    t = _texto()
    guarda = t.find("if errorlevel 1")
    trecho = t[guarda : _posicao_do_echo(t, ANCORA_DO_SUCESSO, guarda)]
    assert re.search(r"[Nn]ada foi gravado", trecho), (
        "a mensagem de falha nao afirma que nada foi gravado"
    )


def test_os_sinais_de_maior_e_menor_estao_escapados():
    """`<frame.png>` cru dentro de um echo vira redirecionamento no cmd.

    Sem o escape o proprio bloco de erro morre com 'A sintaxe do comando esta
    incorreta' -- medido ao escrever a guarda irma do mercado. E o bloco de
    erro e justamente o que o usuario ve quando ja esta com problema.
    """
    t = _texto()
    for linha in t.splitlines():
        despido = linha.strip()
        if not despido.lower().startswith("echo "):
            continue
        for sinal in ("<", ">"):
            for pos in (i for i, c in enumerate(despido) if c == sinal):
                assert pos > 0 and despido[pos - 1] == "^", (
                    f"`{sinal}` sem escape num echo do .bat, o cmd trata como "
                    f"redirecionamento: {despido!r}"
                )


def test_o_bloco_de_sucesso_nao_cita_o_nome_da_imagem():
    """O .bat nao sabe qual imagem foi gravada -- entao nao pode nomear nenhuma.

    `_gravar_conferencia` grava em `calibracao-conferencia.png`, OU num nome
    alternativo com horario quando aquele esta travado no visualizador de fotos
    (o caso mais comum, porque a propria ferramenta manda abrir a imagem), OU em
    lugar nenhum. Nos dois ultimos casos, um nome escrito a mao aqui manda o
    usuario abrir A IMAGEM DA CALIBRACAO ANTERIOR: validar a rodada nova
    olhando a antiga. Quem sabe o nome e a ferramenta, e ela ja o imprime.
    """
    t = _texto()
    for linha in t.splitlines():
        despido = linha.strip()
        if not despido.lower().startswith("echo"):
            continue
        assert "calibracao-conferencia" not in despido, (
            f"o .bat nomeia a imagem de conferencia num echo: {despido!r}. "
            f"Ele nao sabe qual arquivo foi gravado -- so a ferramenta sabe."
        )


def test_o_cabecalho_diz_que_a_calibracao_e_por_personagem():
    """O cabecalho `REM` e a unica documentacao que este usuario le.

    E a informacao que ele NAO tem como deduzir sozinho e que custa caro: com
    duas instancias abertas, calibrar uma vez e achar que acabou deixa a outra
    lendo o retangulo errado -- e o retangulo errado devolve numero plausivel,
    nao campo vazio (M-F).
    """
    t = _texto().lower()
    assert "por personagem" in t, (
        "o cabecalho nao diz que a calibracao e POR PERSONAGEM; o usuario com "
        "duas instancias calibraria uma so"
    )


def test_o_cabecalho_diz_quando_rodar():
    """Uma ferramenta que o usuario nao sabe QUANDO usar e uma que ele nao usa.

    As tres ocasioes sao as do plano: moveu a janela, mudou a resolucao, a
    leitura parou de bater com a tela.
    """
    t = _texto().lower()
    for gatilho in ("moveu", "resolucao", "parou de bater"):
        assert gatilho in t, (
            f"o cabecalho nao ensina o gatilho {gatilho!r} para rodar o .bat"
        )
