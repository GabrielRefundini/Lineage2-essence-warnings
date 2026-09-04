"""`--listar-janelas`: uma linha por titulo, sem decoracao, sem tela.

POR QUE ESTA FLAG EXISTE: o `vigiar-party.bat` precisa perguntar qual janela
do XM Essence vigiar quando ha mais de uma aberta (Faerlina e Yazalaque, por
exemplo). Listar as janelas com um `python -c "..."` inline dentro do `.bat`
quebra, porque o titulo das janelas e os proprios comandos python usam aspas
simples E duplas ao mesmo tempo, e isso conflita com o `for /f ('comando')`
do cmd, que usa aspas simples como delimitador do proprio comando. Esta flag
existe para o `.bat` ter uma saida PURA para ler com `for /f`.

O MESMO PORTAO DE `test_renda_no_main.py`: enquanto a flag nao existir, o
`argparse` cai no proprio erro de "unrecognized arguments" — um teste que so
conferisse a saida por cima passaria com a feature inteira por escrever.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ_DO_PROJETO = Path(__file__).parent.parent

ALFA = "Alfa - XM Essence"
BETA = "Beta - XM Essence"


def _ambiente() -> dict:
    import os

    ambiente = dict(os.environ)
    ambiente["PYTHONPATH"] = str(RAIZ_DO_PROJETO)
    return ambiente


def _rodar_main(monkeypatch, argv: list[str], janelas=()) -> int:
    """`main()` de verdade, com `listar_janelas_do_jogo` presa ao teste."""
    from l2scanner import __main__ as principal

    monkeypatch.setattr(
        principal, "listar_janelas_do_jogo", lambda *a, **k: list(janelas)
    )
    monkeypatch.setattr(sys, "argv", ["l2scanner", *argv])
    return principal.main()


class TestAFlagERECONHECIDA:
    def test_a_flag_e_reconhecida_pelo_argparse(self) -> None:
        """Enquanto a flag nao existir, o argparse recusa por flag
        desconhecida — este e o portao que prova que ela foi ligada."""
        processo = subprocess.run(
            [sys.executable, "-m", "l2scanner", "--listar-janelas"],
            capture_output=True,
            text=True,
            cwd=RAIZ_DO_PROJETO,
            env=_ambiente(),
        )
        saida = processo.stdout + processo.stderr
        assert "unrecognized argument" not in saida, (
            f"o argparse NAO conhece --listar-janelas ainda. Saida:\n{saida}"
        )
        assert "Traceback" not in saida, f"saiu com traceback:\n{saida}"
        assert processo.returncode == 0


class TestASaidaEPura:
    def test_uma_linha_por_titulo_sem_decoracao(self, monkeypatch, capsys) -> None:
        codigo = self._rodar(monkeypatch, [ALFA, BETA])
        saida = capsys.readouterr().out
        linhas = saida.splitlines()
        assert linhas == [ALFA, BETA], (
            f"saida deveria ser uma linha por titulo, sem prefixo nem "
            f"numeracao. Recebido: {linhas!r}"
        )
        assert codigo == 0

    def test_lista_vazia_sai_com_codigo_0_e_sem_linha_nenhuma(
        self, monkeypatch, capsys
    ) -> None:
        codigo = self._rodar(monkeypatch, [])
        saida = capsys.readouterr().out
        assert saida.strip() == ""
        assert codigo == 0

    def test_nao_abre_janela_grafica_nem_faz_mais_nada(
        self, monkeypatch, capsys
    ) -> None:
        """Chama `listar_janelas_do_jogo()` direto e sai — nao monta
        calibracao, nao configura log, nao entra no laco principal."""
        from l2scanner import __main__ as principal

        def _reprovado(*_a, **_k):
            raise AssertionError(
                "algo alem de listar_janelas_do_jogo() foi chamado"
            )

        monkeypatch.setattr(
            principal, "listar_janelas_do_jogo", lambda *a, **k: [ALFA]
        )
        monkeypatch.setattr(principal, "configurar_log", _reprovado)
        monkeypatch.setattr(principal.Calibracao, "carregar", _reprovado)
        monkeypatch.setattr(sys, "argv", ["l2scanner", "--listar-janelas"])

        codigo = principal.main()
        saida = capsys.readouterr().out
        assert codigo == 0
        assert saida.splitlines() == [ALFA]

    @staticmethod
    def _rodar(monkeypatch, janelas):
        return _rodar_main(monkeypatch, ["--listar-janelas"], janelas=janelas)
