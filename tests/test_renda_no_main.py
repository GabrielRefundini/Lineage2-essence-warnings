"""`--renda` no `__main__`: a QUARTA invocacao, o portao da mira e o montador.

POR QUE O PORTAO DE VERIFICACAO AFIRMA AS DUAS METADES
=======================================================
Enquanto `--renda` nao existir, o `argparse` imprime a propria `usage` — que
JA contem `[--janela [JANELA]]`. Um teste que so procurasse `janela` na saida
passaria com a feature inteira por escrever. Entao aqui se afirma, sempre, que
(a) a flag foi RECONHECIDA e (b) a mensagem e a do PORTAO DA MIRA, e nao a do
`argparse` sobre uma flag desconhecida.

Era o defeito do portao anterior deste plano, e ele foi reproduzido e trocado.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from l2scanner.__main__ import montar_registro_da_renda
from l2scanner.renda_registro import (
    ARQUIVO_DO_LEIAME,
    RegistroDaRenda,
    arquivo_do_personagem,
)

RAIZ_DO_PROJETO = Path(__file__).parent.parent
FONTE_DO_MAIN = RAIZ_DO_PROJETO / "l2scanner" / "__main__.py"

PERSONAGEM = "Faerlina"

# O LITERAL EXATO com que a recusa abre, no molde de `--mercado exige --janela`
# (`__main__.py:3101-3106`). Ele e o contrato: o `.bat` do `03-04` e o usuario
# leem esta frase, e nao o codigo de saida.
ABERTURA_DA_RECUSA = "--renda exige --janela"


# ---------------------------------------------------------------------------
# A FLAG E O PORTAO DA MIRA
# ---------------------------------------------------------------------------


CALIBRACAO_DE_FIXTURA = (
    RAIZ_DO_PROJETO / "tests" / "fixtures" / "renda" / "calibracao_de_fixture.json"
)

# A assinatura de monitores gravada NAQUELA fixtura. `main` confere a geometria
# da tela antes de despachar, e uma suite que dependesse do monitor de quem
# roda mediria a maquina e nao o codigo.
GEOMETRIA_DA_FIXTURA = "1720x1392+0+0"

JANELA = "Faerlina - XM Essence"


def _ambiente() -> dict:
    import os

    ambiente = dict(os.environ)
    ambiente["PYTHONPATH"] = str(RAIZ_DO_PROJETO)
    return ambiente


def _rodar_main(monkeypatch, argv: list[str]) -> int:
    """`main()` com a calibracao de fixtura e a geometria dela."""
    import sys as _sys

    from l2scanner import __main__ as principal

    monkeypatch.setattr(principal, "ARQUIVO_CALIBRACAO", CALIBRACAO_DE_FIXTURA)
    monkeypatch.setattr(
        principal,
        "descrever_geometria_da_tela",
        lambda: GEOMETRIA_DA_FIXTURA,
    )
    monkeypatch.setattr(_sys, "argv", ["l2scanner", *argv])
    return principal.main()


def _recusa_da_linha_de_comando() -> str:
    """A saida REAL de `python -m l2scanner --renda`, sem `--janela`."""
    processo = subprocess.run(
        [sys.executable, "-m", "l2scanner", "--renda"],
        capture_output=True,
        text=True,
        cwd=RAIZ_DO_PROJETO,
        env=_ambiente(),
    )
    return processo.stdout + processo.stderr, processo.returncode


class TestAFlagEOPortaoDaMira:
    def test_a_flag_e_RECONHECIDA_e_a_recusa_e_a_do_PORTAO(self) -> None:
        """As DUAS metades, e a segunda so vale por causa da primeira.

        Enquanto `--renda` nao existir, o `argparse` imprime a propria `usage`,
        que JA contem `[--janela [JANELA]]` — um teste que so procurasse
        `janela` passaria com a feature inteira por escrever.
        """
        saida, codigo = _recusa_da_linha_de_comando()

        assert "unrecognized argument" not in saida, (
            "o `argparse` NAO conhece `--renda`: o portao passou sobre uma "
            f"flag inexistente. Saida:\n{saida}"
        )
        assert ABERTURA_DA_RECUSA in saida, (
            f"a recusa nao e a do portao da mira. Saida:\n{saida}"
        )
        assert "Traceback" not in saida, "a recusa sai sem traceback"
        assert codigo != 0

    def test_a_razao_da_recusa_e_A_DA_RENDA_e_nao_a_copiada_do_mercado(
        self,
    ) -> None:
        """O portao e o mesmo; a RAZAO e outra e vai escrita.

        No mercado o motivo e que o painel do World Exchange ANDA dentro da
        janela. Aqui e que EXP e adena sao DO PERSONAGEM, e o usuario roda duas
        instancias lado a lado. Copiar a frase do irmao seria dar a razao
        errada para o portao certo.
        """
        saida, _ = _recusa_da_linha_de_comando()

        assert "personagem" in saida.lower()
        assert "World Exchange" not in saida, (
            "esta e a razao do `--mercado`, e nao a da renda"
        )

    def test_sem_a_flag_nada_muda(self, monkeypatch) -> None:
        """O `--renda` e opt-in: quem nao o pede nao encosta no laco da renda."""
        from l2scanner import __main__ as principal

        def nao_deveria_chegar(*_a, **_k):
            raise AssertionError("o laco da renda subiu sem `--renda`")

        monkeypatch.setattr(
            "l2scanner.renda_laco.laco_da_renda", nao_deveria_chegar
        )
        monkeypatch.setattr(principal, "laco_principal", lambda *a, **k: 0)

        assert _rodar_main(monkeypatch, ["--janela", JANELA]) == 0


class TestODespacho:
    def test_renda_com_janela_despacha_e_devolve_o_codigo_DO_LACO(
        self, monkeypatch
    ) -> None:
        vistos = []

        def laco_falso(args, cal):
            vistos.append((args, cal))
            return 7

        monkeypatch.setattr("l2scanner.renda_laco.laco_da_renda", laco_falso)

        codigo = _rodar_main(monkeypatch, ["--renda", "--janela", JANELA])

        assert codigo == 7, "o `--renda` devolve o codigo DO LACO"
        assert len(vistos) == 1
        assert vistos[0][0].renda is True
        assert vistos[0][0].janela == JANELA

    def test_o_caminho_do_renda_NAO_alcanca_o_laco_da_party(
        self, monkeypatch
    ) -> None:
        """`--renda` NAO vigia a party e NAO envia alerta nenhum."""
        from l2scanner import __main__ as principal

        def explodir(*_a, **_k):
            raise AssertionError(
                "o caminho do `--renda` alcancou `laco_principal`: ele NAO "
                "vigia a party e NAO monta notificador nenhum"
            )

        monkeypatch.setattr(principal, "laco_principal", explodir)
        monkeypatch.setattr(
            "l2scanner.renda_laco.laco_da_renda", lambda args, cal: 0
        )

        assert _rodar_main(monkeypatch, ["--renda", "--janela", JANELA]) == 0

    def test_a_cadencia_chega_PELAS_FLAGS_QUE_JA_EXISTEM(
        self, monkeypatch
    ) -> None:
        """C-4 e P-4: `--intervalo` e `--status-a-cada` ja existem de graca.

        Nenhuma chave de CADENCIA entra na secao `[renda]` do `config.toml` —
        ela ja tem duas flags, e a chave duplicaria a verdade sobre elas. (A
        frase aqui dizia "nenhuma SEXTA chave" ate 2026-09-04, quando uma sexta
        entrou: `tamanho_do_pack_de_adena`, que nao e cadencia e nao tinha outra
        casa. A cerca continua de pe, e ela e sobre cadencia.)
        """
        vistos = []
        monkeypatch.setattr(
            "l2scanner.renda_laco.laco_da_renda",
            lambda args, cal: (vistos.append(args), 0)[1],
        )

        _rodar_main(monkeypatch, ["--renda", "--janela", JANELA])

        assert vistos[0].intervalo == pytest.approx(1.0)
        assert vistos[0].status_a_cada == pytest.approx(30.0)

    def test_os_valores_pedidos_na_linha_de_comando_CHEGAM(
        self, monkeypatch
    ) -> None:
        vistos = []
        monkeypatch.setattr(
            "l2scanner.renda_laco.laco_da_renda",
            lambda args, cal: (vistos.append(args), 0)[1],
        )

        _rodar_main(
            monkeypatch,
            [
                "--renda",
                "--janela",
                JANELA,
                "--intervalo",
                "2.5",
                "--status-a-cada",
                "90",
            ],
        )

        assert vistos[0].intervalo == pytest.approx(2.5)
        assert vistos[0].status_a_cada == pytest.approx(90.0)

    def test_SEM_a_flag_do_pack_o_valor_e_None_e_o_config_manda(
        self, monkeypatch
    ) -> None:
        """`None` e o dado, e nao a ausencia dele.

        Um default de `5_000_000` no `argparse` faria a linha de comando SEMPRE
        vencer o `config.toml`, e a chave que o usuario escreveu no arquivo
        nunca chegaria — o pior desfecho possivel, porque ele nao teria como
        saber por que.
        """
        vistos = []
        monkeypatch.setattr(
            "l2scanner.renda_laco.laco_da_renda",
            lambda args, cal: (vistos.append(args), 0)[1],
        )

        _rodar_main(monkeypatch, ["--renda", "--janela", JANELA])

        assert vistos[0].pack_de_adena is None

    def test_o_pack_pedido_na_linha_de_comando_CHEGA(self, monkeypatch) -> None:
        vistos = []
        monkeypatch.setattr(
            "l2scanner.renda_laco.laco_da_renda",
            lambda args, cal: (vistos.append(args), 0)[1],
        )

        _rodar_main(
            monkeypatch,
            ["--renda", "--janela", JANELA, "--pack-de-adena", "3000000"],
        )

        assert vistos[0].pack_de_adena == 3_000_000


# ---------------------------------------------------------------------------
# `montar_registro_da_renda`: o trilho que devolve `None` e NUNCA levanta
# ---------------------------------------------------------------------------


class TestOMontador:
    def test_o_caminho_feliz_devolve_um_RegistroDaRenda(self, tmp_path) -> None:
        registro = montar_registro_da_renda(tmp_path, PERSONAGEM)

        assert isinstance(registro, RegistroDaRenda)
        assert registro.arquivo == arquivo_do_personagem(tmp_path, PERSONAGEM)
        assert (tmp_path / ARQUIVO_DO_LEIAME).is_file(), (
            "a pasta nasce com o LEIAME ao lado do CSV (C-10)"
        )

    def test_um_ARQUIVO_no_lugar_da_pasta_devolve_None_e_nao_levanta(
        self, tmp_path, caplog
    ) -> None:
        """Medido nesta maquina: o `mkdir(parents=True, exist_ok=True)` do
        construtor levanta `FileExistsError` (errno 17, winerror 183) quando um
        ARQUIVO ocupa o nome da pasta, e ele roda ANTES de qualquer `try`."""
        ocupado = tmp_path / "ocupado"
        ocupado.write_text("nao sou uma pasta", encoding="utf-8")

        import logging

        with caplog.at_level(logging.ERROR):
            assert montar_registro_da_renda(ocupado, PERSONAGEM) is None

        assert "REGISTRO DA RENDA DESLIGADO" in caplog.text

    def test_um_arquivo_de_renda_CORROMPIDO_devolve_None_e_CITA_o_arquivo(
        self, tmp_path, caplog
    ) -> None:
        """Com dois personagens em `.renda/`, o usuario precisa saber QUAL
        mover."""
        alvo = arquivo_do_personagem(tmp_path, PERSONAGEM)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(
            "uma;coluna;que;nao;e;o;cabecalho\n", encoding="utf-8"
        )

        import logging

        with caplog.at_level(logging.ERROR):
            assert montar_registro_da_renda(tmp_path, PERSONAGEM) is None

        assert str(alvo) in caplog.text

    def test_o_montador_NAO_captura_Exception_nu(self) -> None:
        """Um `except Exception` esconderia um `AttributeError` de refactor
        futuro com a mesma cara de um disco cheio."""
        import ast
        import inspect

        import l2scanner.__main__ as principal

        arvore = ast.parse(inspect.getsource(montar_registro_da_renda))
        del principal
        for no in ast.walk(arvore):
            if not isinstance(no, ast.ExceptHandler):
                continue
            assert no.type is not None, "`except:` nu"
            nomes = (
                {n.id for n in no.type.elts if isinstance(n, ast.Name)}
                if isinstance(no.type, ast.Tuple)
                else {no.type.id}
                if isinstance(no.type, ast.Name)
                else set()
            )
            assert "Exception" not in nomes
            assert "BaseException" not in nomes

    def test_sem_pasta_ele_cai_na_PASTA_DA_RENDA_e_nao_num_literal(
        self,
    ) -> None:
        """A pasta padrao resolve em tempo de CHAMADA, e o teste NAO a monta —
        `.renda/` do usuario e dado acumulado e sem desfazer."""
        import inspect

        assert (
            inspect.signature(montar_registro_da_renda)
            .parameters["pasta"]
            .default
            is None
        )
        assert "PASTA_DA_RENDA" in inspect.getsource(montar_registro_da_renda)


# ---------------------------------------------------------------------------
# NADA MAIS ENTRA NO `__main__`
# ---------------------------------------------------------------------------


class TestNadaMaisEntra:
    def test_a_secao_renda_tem_SEIS_chaves_e_a_sexta_tem_nome(self) -> None:
        """A cerca e de CONJUNTO EXATO, e ela caiu uma vez — em 2026-09-04.

        ATE ENTAO ELA DIZIA **CINCO**, com esta razao ao lado: *"uma SEXTA chave
        entrou em `[renda]`. A cadencia ja tem dois argumentos de linha de
        comando (`--intervalo`, `--status-a-cada`) e inventar a chave duplicaria
        a verdade sobre ela."* A razao continua verdadeira e continua valendo —
        ela e sobre CADENCIA.

        `tamanho_do_pack_de_adena` nao e cadencia: ele e a META DO USUARIO ("de
        quanto em quanto eu quero ser avisado"), nao tinha nenhuma outra casa, e
        sem ele o numero seria constante magica dentro de `l2scanner/*.py`. Ele
        tem uma flag (`--pack-de-adena`) que o vence NAQUELA RODADA, e a
        precedencia e medida em `tests/test_renda_laco.py` — as duas nao sao a
        mesma verdade escrita duas vezes: uma persiste, a outra e desta vez.

        A cerca segue de conjunto exato: uma SETIMA chave ainda a derruba.
        """
        from dataclasses import fields

        from l2scanner.config import AjustesDaRenda

        nomes = {campo.name for campo in fields(AjustesDaRenda)}

        assert nomes == {
            "janela_movel_minutos",
            "lacuna_maxima_segundos",
            "fator_de_salto_da_adena",
            "amostras_minimas_para_taxa",
            "janela_minima_para_taxa_segundos",
            "tamanho_do_pack_de_adena",
        }, (
            "uma SETIMA chave entrou em `[renda]`. Antes de aceita-la: ela "
            "governa a CONTA, uma META do usuario, ou a CADENCIA? Se for "
            "cadencia, ela ja tem `--intervalo` e `--status-a-cada` e a chave "
            "duplicaria a verdade sobre eles."
        )

    def test_o_despacho_do_renda_fica_AO_LADO_do_do_mercado(self) -> None:
        """Depois da calibracao e da resolucao de `--janela AUTO`.

        Sair antes duplicaria a verdade sobre como a janela e escolhida — a
        razao ja escrita no comentario do irmao.
        """
        fonte = FONTE_DO_MAIN.read_text(encoding="utf-8")
        onde_mercado = fonte.index("if args.mercado:")
        onde_renda = fonte.index("if args.renda:")
        onde_auto = fonte.index('args.janela = janelas[0]')

        assert onde_auto < onde_mercado < onde_renda, (
            "o despacho do `--renda` tem de vir DEPOIS da resolucao do "
            "`--janela AUTO` e ao lado do do `--mercado`"
        )
