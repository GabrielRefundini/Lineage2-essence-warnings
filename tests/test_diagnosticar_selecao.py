"""O diagnostico nao pode ler "o processo caiu" como "o defeito aconteceu".

WR-13. O veredito de cada fase vinha do `returncode` do subprocesso, com
`0 = PASSOU`, `1 = FALHOU`, `2 = ERRO`. Mas `1` e tambem o codigo com que o
CPython sai de QUALQUER excecao nao tratada -- um `cv2.error`, um
`ImportError`, um `FileNotFoundError` no `--gravacao`.

Nesse caso a ferramenta imprimia

    "FALHOU -- voltou sozinho, sem esperar ninguem"
    "CONCLUSAO: a tecla vem do NAVEGADOR DE FRAMES."

que e uma conclusao AFIRMADA sobre uma medicao que nunca aconteceu -- na
ferramenta escrita justamente para trocar "tenta mais um fix" por "mede qual
hipotese e a verdadeira". Ela custou duas rodadas do usuario para nascer; ler
um crash como evidencia teria custado mais.
"""

from __future__ import annotations

import subprocess

import pytest

import tools.diagnosticar_selecao as diag


class SubprocessoFalso:
    def __init__(self, codigos: list[int]) -> None:
        self.codigos = list(codigos)

    def __call__(self, *_a, **_k):
        class Resultado:
            returncode = self.codigos.pop(0)

        return Resultado()


@pytest.fixture
def rodar(monkeypatch: pytest.MonkeyPatch, capsys):
    """Roda `main` com as duas fases dubladas pelos codigos de saida dados."""

    def _rodar(sem: int, com: int) -> tuple[int, str]:
        monkeypatch.setattr(subprocess, "run", SubprocessoFalso([sem, com]))
        codigo = diag.main(["--gravacao", "qualquer"])
        return codigo, capsys.readouterr().out

    return _rodar


class TestOsCodigosNaoColidemComODoInterpretador:
    def test_os_tres_codigos_estao_fora_da_faixa_do_python(self):
        """`1` e o codigo de qualquer traceback; `2`, o de erro de argumento."""
        codigos = {diag.SAIDA_PASSOU, diag.SAIDA_FALHOU, diag.SAIDA_ERRO}
        assert codigos.isdisjoint({0, 1, 2}), (
            f"os codigos {codigos & {0, 1, 2}} colidem com os do CPython: um "
            f"traceback seria lido como veredito"
        )
        assert len(codigos) == 3, "dois vereditos com o mesmo codigo"


class TestUmCrashNaoVIRAVeredito:
    @pytest.mark.parametrize(
        "sem,com",
        [
            (1, 11),   # traceback na fase 1 -- era lido como FALHOU
            (11, 1),   # traceback na fase 2
            (1, 1),    # as duas cairam -- era lido como "navegador inocente"
            (0, 0),    # o codigo ANTIGO de PASSOU, agora desconhecido
            (3221225477, 11),  # 0xC0000005: crash nativo do cv2
        ],
        ids=["crash-1", "crash-2", "crash-nos-dois", "codigo-velho", "crash-nativo"],
    )
    def test_codigo_desconhecido_NAO_conclui_nada(self, rodar, sem: int, com: int):
        codigo, saida = rodar(sem, com)

        assert "CONCLUSAO: NENHUMA" in saida, (
            f"com os codigos ({sem}, {com}) a ferramenta ainda concluiu algo"
        )
        assert "a tecla vem do NAVEGADOR" not in saida
        assert "navegador esta inocente" not in saida
        assert "o defeito NAO acontece mais" not in saida
        assert codigo == diag.SAIDA_ERRO

    def test_o_crash_aparece_NOMEADO_na_tabela(self, rodar):
        """"?" nao ajuda ninguem; o numero do codigo, sim."""
        _codigo, saida = rodar(1, diag.SAIDA_FALHOU)

        (linha_da_fase_1,) = [
            ln for ln in saida.splitlines() if ln.strip().startswith("sem-navegador")
        ]
        assert "CRASH (codigo 1)" in linha_da_fase_1, (
            f"a fase que CAIU virou {linha_da_fase_1.strip()!r} -- um '?' nao "
            f"diz a ninguem que houve traceback, e um veredito mente"
        )
        assert "FALHOU" not in linha_da_fase_1
        assert "PASSOU" not in linha_da_fase_1


class TestAsConclusoesLEGITIMASContinuamSaindo:
    def test_so_a_fase_com_navegador_falha(self, rodar):
        _codigo, saida = rodar(diag.SAIDA_PASSOU, diag.SAIDA_FALHOU)
        assert "a tecla vem do NAVEGADOR DE FRAMES" in saida

    def test_as_duas_falham(self, rodar):
        _codigo, saida = rodar(diag.SAIDA_FALHOU, diag.SAIDA_FALHOU)
        assert "navegador esta inocente" in saida

    def test_as_duas_passam(self, rodar):
        codigo, saida = rodar(diag.SAIDA_PASSOU, diag.SAIDA_PASSOU)
        assert "o defeito NAO acontece mais" in saida
        assert codigo == 0

    def test_resultado_misto_e_reportado_como_misto(self, rodar):
        """FALHOU sem navegador e PASSOU com ele: possivel, e nao conclui nada.

        Nao e crash -- os dois codigos sao conhecidos --, entao a ferramenta
        diz "misto" em vez de fingir uma leitura.
        """
        _codigo, saida = rodar(diag.SAIDA_FALHOU, diag.SAIDA_PASSOU)
        assert "misto" in saida

    def test_um_ERRO_declarado_tambem_nao_conclui(self, rodar):
        """`SAIDA_ERRO` e conhecido, mas tambem nao mediu nada."""
        _codigo, saida = rodar(diag.SAIDA_ERRO, diag.SAIDA_FALHOU)
        assert "a tecla vem do NAVEGADOR" not in saida
