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

import logging
import os
import shutil
import tempfile
from pathlib import Path

from l2scanner.raiz import RAIZ

# ===========================================================================
# A SUITE NAO ESCREVE NO LOG DE PRODUCAO
# ===========================================================================
#
# DUAS CACAS DE FANTASMA NUM UNICO DIA (2026-09-02), e as duas custaram pericia
# de verdade antes de a saida se revelar de teste:
#
#   1. `Presenca: 2 party-mate(s) ... (Korzis, J4guar)` mais
#      `CHATWOOT_TELEFONES_COMANDO vazio, qualquer remetente alcanca TODO
#      comando` quase viraram um relato de "ha um scanner sem contencao de
#      seguranca rodando em campo". Era saida da SUITE, no mesmo
#      `logs/scanner.log`.
#   2. `Aprendi uma assinatura nova ... confianca 0.7492` quase virou uma
#      acusacao de que o aprendiz gravava duplicata em campo. O `0.7492` era a
#      fixture de `tests/test_aprendiz.py`.
#
# E na mesma noite, investigando a party sumindo de verdade, nao houve como
# dizer se os blocos `[vigiando]` VAZIOS eram da instancia do Yazalaque
# (defeito) ou da Faerlina, que nao esta em party nenhuma (normal). A pericia
# parou ali.
#
# MEDIDO NESTA ARVORE: uma rodada completa da suite criava `logs/scanner.log`
# com 654.907 bytes MAIS um `logs/scanner.log.1` de 2.000.709 bytes. A suite nao
# so sujava o log de campo - ela ROTACIONAVA, e cada rodada empurrava duas horas
# de farm real para fora da janela de tres backups.
#
# AS TRES PORTAS, achadas instrumentando o construtor do `RotatingFileHandler` e
# nomeando o teste corrente:
#
#     tests/test_aprendiz.py::TestARecusaAcontecENoARRANQUE
#         ::test_main_chamada_de_verdade_devolve_2_com_o_jogo_fechado
#     tests/test_aprendiz.py::TestARecusaAcontecENoARRANQUE
#         ::test_um_config_bom_nao_impede_o_arranque
#     tests/test_bosses.py::TestOArranque
#         ::test_um_bloco_torto_derruba_o_arranque_com_codigo_2
#
# Sao TRES construtores e 2,6 MB de saida: o manipulador ficava INSTALADO no
# logger `l2scanner` depois de o teste terminar, entao as outras ~5300 linhas de
# teste que logam por ele iam junto para o arquivo de producao.
#
# SAO DUAS CAMADAS, E ELAS RESOLVEM PROBLEMAS DIFERENTES:
#
#   (a) O DESVIO. `PASTA_LOGS` do arranque passa a apontar para um diretorio
#       temporario do sistema durante a suite inteira. Isso conserta as tres
#       portas de hoje SEM editar um unico teste, e conserta de antemao a quarta
#       que alguem escrever amanha. A alternativa - um `monkeypatch` por teste -
#       foi recusada porque depende de cada autor lembrar, que e exatamente a
#       forma de falha que ja custou as duas cacas acima.
#
#       O DESVIO E FEITO POR VARIAVEL DE AMBIENTE, E NAO SO POR ATRIBUTO. Havia
#       uma QUARTA porta que o instrumento em processo nao enxergava:
#       `tests/test_agenda.py::TestModoAgendaSemJogo` roda `python -m l2scanner
#       --testar-agenda --dry-run` num SUBPROCESSO, e processo filho nao ve
#       `monkeypatch` nenhum. Ele deixava no log de campo justamente as linhas
#       mais enganosas possiveis - "Modo simulacao: alertas so no console" e
#       "Enviado: TvT comeca em 10 minutos" - indistinguiveis de saida real.
#       `subprocess.run` herda o ambiente do pai por padrao, entao a variavel
#       alcanca todo subprocesso da suite sem nenhum teste precisar saber disso.
#       O atributo continua sendo ajustado tambem, para nao depender da ordem em
#       que os modulos foram importados.
#
#   (b) O PORTAO. Qualquer manipulador de arquivo apontado para `<repo>/logs/`
#       levanta `AssertionError` com o conserto escrito na mensagem. E a rede
#       para o caso que o desvio nao alcanca: um caminho montado a mao dentro de
#       um teste, sem passar por `PASTA_LOGS`. FALHA ALTO, em vez de sujar o log
#       de campo em silencio e cobrar a conta semanas depois.
#
# O portao mora em `logging.FileHandler.__init__` e nao em `RotatingFileHandler`
# porque `RotatingFileHandler` herda dele: prender o pai fecha o
# `FileHandler`, o `RotatingFileHandler` e o `WatchedFileHandler` de uma vez.

_PASTA_DE_LOGS_DE_PRODUCAO = (RAIZ / "logs").resolve()
_pasta_temporaria: str | None = None
_abrir_arquivo_original = logging.FileHandler.__init__


def _e_log_de_producao(caminho) -> bool:
    try:
        alvo = Path(caminho).resolve()
    except (OSError, ValueError):
        return False
    return alvo == _PASTA_DE_LOGS_DE_PRODUCAO or (
        _PASTA_DE_LOGS_DE_PRODUCAO in alvo.parents
    )


def _abrir_arquivo_com_portao(self, filename, *args, **kwargs):
    assert not _e_log_de_producao(filename), (
        f"a suite tentou abrir o log de producao: {filename}\n"
        "Nenhum teste pode escrever em <repo>/logs/ - ja custou duas cacas a "
        "fantasma num unico dia (ver o cabecalho de tests/conftest.py).\n"
        "Conserto: aponte o destino para `tmp_path`, ou\n"
        "    monkeypatch.setattr(principal, 'PASTA_LOGS', tmp_path / 'logs')"
    )
    return _abrir_arquivo_original(self, filename, *args, **kwargs)


def pytest_configure(config) -> None:
    """Cala o logger NATIVO do OpenCV, e tranca o log de producao."""
    global _pasta_temporaria

    try:
        import cv2

        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
    except Exception:  # noqa: BLE001 - sem cv2 ou sem essa API, segue o baile
        pass

    logging.FileHandler.__init__ = _abrir_arquivo_com_portao

    # O desvio. Fora da arvore do repositorio de proposito: dentro dela, um
    # `logs-de-teste/` acabaria versionado por engano ou confundido com o de
    # campo justamente por quem estivesse fazendo pericia.
    _pasta_temporaria = tempfile.mkdtemp(prefix="l2scanner-logs-de-teste-")

    # A VARIAVEL VEM ANTES DO IMPORT: `PASTA_LOGS` e calculada no import de
    # `__main__`, entao inverter a ordem deixaria o modulo nascer apontando para
    # o log de campo.
    os.environ["L2SCANNER_PASTA_DE_LOGS"] = _pasta_temporaria
    from l2scanner import __main__ as principal

    principal.PASTA_LOGS = Path(_pasta_temporaria)


def pytest_unconfigure(config) -> None:
    logging.FileHandler.__init__ = _abrir_arquivo_original
    os.environ.pop("L2SCANNER_PASTA_DE_LOGS", None)
    if _pasta_temporaria:
        # `ignore_errors` porque no Windows um manipulador que algum teste
        # deixou instalado ainda segura o arquivo aberto. Lixo em `%TEMP%` e
        # barato; derrubar a rodada inteira no fim, nao.
        shutil.rmtree(_pasta_temporaria, ignore_errors=True)
