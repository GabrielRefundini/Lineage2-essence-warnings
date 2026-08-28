"""Configuracao da suite.

MEDIDO NESTA MAQUINA, e a razao inteira deste arquivo existir
-------------------------------------------------------------
`test_uma_escrita_que_falha_nao_conta_nem_indexa` falhava em cerca de METADE
das rodadas, com uma mensagem que nao fazia sentido nenhum:

    json.decoder.JSONDecodeError: Expecting value: line 1 column 3 (char 2)

O `observacoes.jsonl` daquela sessao — que deveria estar VAZIO, porque a
escrita do PNG falhou — continha isto:

    [ WARN:0@0.032] global loadsave.cpp:1164 cv::imwrite_ imwrite_(
    '...\\frame_000007.png'): can't open file for writing: permission denied

Ou seja: o aviso NATIVO do OpenCV foi parar DENTRO do arquivo de indice da
gravacao. (`json.loads` le o `[`, pula o espaco, encontra `W` no indice 2 — dai
o "column 3 (char 2)".)

O mecanismo: a captura padrao do pytest e no nivel de FILE DESCRIPTOR — ela
redireciona os fds 1 e 2 para arquivos temporarios. O codigo nativo do OpenCV
guarda o descritor de stderr de quando foi carregado. Quando o `Gravador` abre
o `observacoes.jsonl`, o sistema pode entregar justamente o numero de fd que o
OpenCV ainda pensa ser o stderr — e o proximo aviso nativo dele cai no indice
da gravacao. Com `-s` (captura desligada) o teste passa sempre; sem `-s`,
falha em cerca de metade das rodadas. Nada disso passa pelo Python, entao
`capsys`, `caplog` e `contextlib.redirect_stderr` nao alcancam.

Isto e ANTERIOR a qualquer mudanca desta rodada de correcoes: reproduzido no
commit 6aa7b74 com o codigo intocado, 5 falhas em 10 rodadas.

O conserto e calar o log NATIVO do OpenCV durante a suite. Nao afrouxa nenhuma
assertiva: os testes continuam exigindo que o indice esteja vazio, que o
contador nao suba e que o ERROR do `l2scanner.gravador` (que passa pelo
`logging` do Python, e portanto pelo `caplog`) apareca. O que sai e so o ruido
nativo de terceiro que estava vazando para o arquivo errado.

Em producao o fd 2 e um console de verdade e o aviso vai para onde deve.
"""

from __future__ import annotations


def pytest_configure(config) -> None:
    """Cala o logger NATIVO do OpenCV. Ver a docstring do modulo."""
    try:
        import cv2

        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
    except Exception:  # noqa: BLE001 - sem cv2 ou sem essa API, segue o baile
        pass
