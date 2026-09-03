"""O DESENHO do modo `--renda`, medido em COLUNAS e nunca afirmado por leitura.

POR QUE ESTE ARQUIVO MEDE LARGURA
==================================
A forma da tela desta fase foi decidida MEDINDO (CTX-2), e a medicao derrubou
duas premissas: `console.LARGURA = 58` e PISO e nunca teto (`moldurar` usa
`max(LARGURA, ...)`, `console.py:110`), e a linha densa de dez valores mede 87
colunas contra as 76 que `LARGURA_DO_AVISO` (`mercado_console.py:748`) cita
como largura real de console desta casa. Um teste que so afirmasse "a linha
contem o nivel" deixaria a linha crescer para 87 sem ficar vermelho — e foi
exatamente assim que a decisao errada quase entrou.

Entao aqui se conta caractere.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from l2scanner.renda_console import (
    ESTADO_LENDO,
    LARGURA_MAXIMA_DA_LINHA_DO_TIQUE,
    SEM_LEITURA,
    linha_do_tique,
)
from l2scanner.renda_conta import ContagemDaRenda
from l2scanner.renda_leitura import (
    CAMPO_DA_ADENA,
    CAMPO_DO_EXP,
    CAMPO_DO_NIVEL,
    MOTIVO_DA_DISCORDANCIA,
    MOTIVO_DO_CAMPO_VAZIO,
    CamposDaRenda,
    RecusaDaRenda,
    ValorDaAdena,
    ValorDaRenda,
)

FONTE_DO_CONSOLE = (
    Path(__file__).parent.parent / "l2scanner" / "renda_console.py"
)

# OS VALORES REAIS, e eles vem do `03-CONTEXT.md:142-143` — a tela do usuario
# num farm de verdade. Medir a largura com `nivel 1` e `adena 0` mediria uma
# linha que ninguem ve.
NIVEL_REAL = 67
EXP_REAL_EM_DECIMOS = 792_568  # 79,2568%
ADENA_REAL = 17_592_060

# A BANDA MEDIDA no planejamento desta fase, com os valores acima:
#   `renda | nivel 67 | EXP 79,2568% | adena 17.592.060 | LENDO`            58
#   `renda | nivel -- | EXP 79,2568% | adena 17.592.060 | nivel: ...`    ate 72
# O piso e a linha limpa e o teto e o orcamento do modulo.
COLUNAS_DA_LINHA_LIMPA = 58


def nivel(valor: int = NIVEL_REAL) -> ValorDaRenda:
    return ValorDaRenda(
        campo=CAMPO_DO_NIVEL, valor=valor, escalas=2, texto=str(valor)
    )


def exp(valor: int = EXP_REAL_EM_DECIMOS) -> ValorDaRenda:
    return ValorDaRenda(
        campo=CAMPO_DO_EXP, valor=valor, escalas=2, texto="79,2568"
    )


def adena(valor: int = ADENA_REAL) -> ValorDaAdena:
    return ValorDaAdena(
        campo=CAMPO_DA_ADENA, valor=valor, glifos=10, texto="17.592.060"
    )


def recusa(campo: str, motivo: str = MOTIVO_DO_CAMPO_VAZIO) -> RecusaDaRenda:
    return RecusaDaRenda(
        campo=campo, motivo=motivo, detalhe="detalhe longo que NAO vai a tela"
    )


def campos(**trocas) -> CamposDaRenda:
    base = {
        "personagem": "Faerlina",
        "nivel": nivel(),
        "exp": exp(),
        "adena": adena(),
    }
    base.update(trocas)
    return CamposDaRenda(**base)


# ---------------------------------------------------------------------------
# A LARGURA, que e a decisao desta fase
# ---------------------------------------------------------------------------


class TestALarguraMedida:
    def test_a_linha_limpa_mede_EXATAMENTE_58_colunas(self) -> None:
        """O piso da banda medida, com os valores reais da tela do usuario."""
        linha = linha_do_tique(campos(), ContagemDaRenda())

        assert len(linha) == COLUNAS_DA_LINHA_LIMPA, (
            "a linha do tique com os TRES campos lidos mede 58 colunas na "
            f"medicao desta fase; esta mede {len(linha)}:\n  {linha}\n"
            "Se ela cresceu, a decisao de dividir a tela em LINHA (o que a "
            "tela do jogo afirma) e BLOCO (o que o programa calculou) esta "
            "sendo desfeita — e a linha densa de dez valores ja mediu 87 e foi "
            "REFUTADA."
        )

    @pytest.mark.parametrize(
        "trocas",
        [
            {"nivel": recusa(CAMPO_DO_NIVEL)},
            {"adena": recusa(CAMPO_DA_ADENA)},
            {"nivel": recusa(CAMPO_DO_NIVEL), "exp": recusa(CAMPO_DO_EXP)},
            {
                "nivel": recusa(CAMPO_DO_NIVEL),
                "exp": recusa(CAMPO_DO_EXP),
                "adena": recusa(CAMPO_DA_ADENA),
            },
            # O motivo MAIS LONGO da Fase 1 (26 caracteres). Sem truncagem esta
            # linha mede 85 e estoura o orcamento.
            {"nivel": recusa(CAMPO_DO_NIVEL, MOTIVO_DA_DISCORDANCIA)},
            {
                "nivel": recusa(CAMPO_DO_NIVEL, MOTIVO_DA_DISCORDANCIA),
                "exp": recusa(CAMPO_DO_EXP, MOTIVO_DA_DISCORDANCIA),
                "adena": recusa(CAMPO_DA_ADENA, MOTIVO_DA_DISCORDANCIA),
            },
        ],
    )
    def test_NENHUMA_combinacao_de_recusa_estoura_o_orcamento(
        self, trocas
    ) -> None:
        """72 colunas e o teto, e ele vale para as oito combinacoes de recusa.

        A recusa e o caso MAJORITARIO e nao a excecao: a Fase 1 mediu 79% de
        recusa no nivel. Uma linha que so coubesse no caso limpo estouraria o
        console na maior parte dos tiques de uma noite real.
        """
        linha = linha_do_tique(campos(**trocas), ContagemDaRenda())

        assert len(linha) <= LARGURA_MAXIMA_DA_LINHA_DO_TIQUE, (
            f"a linha mede {len(linha)} colunas e o orcamento e "
            f"{LARGURA_MAXIMA_DA_LINHA_DO_TIQUE}:\n  {linha}"
        )

    def test_o_orcamento_cabe_nas_76_colunas_que_esta_casa_cita(self) -> None:
        """O numero de largura de console desta arvore e 76, e nao 58."""
        from l2scanner.mercado_console import LARGURA_DO_AVISO

        assert LARGURA_MAXIMA_DA_LINHA_DO_TIQUE <= LARGURA_DO_AVISO


# ---------------------------------------------------------------------------
# O CONTEUDO: o que a tela do JOGO afirma, e a recusa nomeada
# ---------------------------------------------------------------------------


class TestOQueALinhaDiz:
    def test_os_tres_valores_saem_na_grafia_DO_JOGO(self) -> None:
        """O criterio 1 e uma comparacao entre o terminal e o monitor."""
        linha = linha_do_tique(campos(), ContagemDaRenda())

        assert "nivel 67" in linha
        assert "79,2568%" in linha, "o EXP sai com virgula decimal e 4 casas"
        assert "17.592.060" in linha, (
            "a adena sai com o PONTO de milhar que o jogo escreve; a virgula e "
            "a grafia do OCR e nao a da tela"
        )

    def test_um_campo_recusado_sai_como_dois_tracos_e_com_o_motivo(
        self,
    ) -> None:
        """Nunca espaco vazio e NUNCA zero: zero e um fato sobre o farm."""
        linha = linha_do_tique(
            campos(nivel=recusa(CAMPO_DO_NIVEL)), ContagemDaRenda()
        )

        assert f"nivel {SEM_LEITURA}" in linha, (
            "o campo recusado sai como `--`; um espaco vazio parece defeito de "
            "formatacao e um zero seria uma AFIRMACAO sobre o jogo"
        )
        assert "nivel 0" not in linha
        assert MOTIVO_DO_CAMPO_VAZIO in linha, (
            "o motivo da recusa vai na propria linha do tique: sem ele o "
            "usuario ve `--` a noite inteira sem nenhuma pista do conserto"
        )

    def test_os_outros_dois_campos_continuam_saindo(self) -> None:
        """Um campo que recusou NAO esconde os outros dois (criterio 1)."""
        linha = linha_do_tique(
            campos(nivel=recusa(CAMPO_DO_NIVEL)), ContagemDaRenda()
        )

        assert "79,2568%" in linha
        assert "17.592.060" in linha

    def test_a_linha_limpa_diz_LENDO(self) -> None:
        assert ESTADO_LENDO in linha_do_tique(campos(), ContagemDaRenda())

    def test_o_estado_INJETADO_substitui_o_padrao(self) -> None:
        """O seam do `03-02`: a cegueira troca o estado sem mexer na assinatura.

        Ele nasce aqui SEM CONSUMIDOR de proposito, no precedente das cinco
        chaves que o `02-01` deixou lidas e sem consumidor.
        """
        linha = linha_do_tique(
            campos(), ContagemDaRenda(), estado="PAUSADO: JOGO CAIU"
        )

        assert "PAUSADO: JOGO CAIU" in linha
        assert ESTADO_LENDO not in linha


# ---------------------------------------------------------------------------
# A TELA NAO E REPINTADA (C-1), e ela nao imprime (CTX-1)
# ---------------------------------------------------------------------------


class TestOQueEstaTelaNaoE:
    def test_a_linha_do_tique_e_UMA_linha_e_nao_tem_retorno_de_carro(
        self,
    ) -> None:
        """"Ao vivo" nesta casa e uma linha NOVA por tique, que ROLA.

        Nao ha `\\r`, nao ha clear e nao ha `print`: o laco faz `log.info` e a
        linha desce. Um `\\r` aqui apagaria a linha anterior no console E
        gravaria lixo no `scanner.log` rotativo, que e onde a forense mora.
        """
        linha = linha_do_tique(campos(), ContagemDaRenda())

        assert "\r" not in linha
        assert "\n" not in linha
        assert "\x1b" not in linha, "nenhum codigo ANSI e montado aqui"

    def test_a_funcao_DEVOLVE_texto_e_nunca_imprime(self, capsys) -> None:
        """O molde declarado em `mercado_console.py:1-10`."""
        devolvido = linha_do_tique(campos(), ContagemDaRenda())

        capturado = capsys.readouterr()
        assert capturado.out == ""
        assert capturado.err == ""
        assert isinstance(devolvido, str) and devolvido


class TestOPortaoDeArvoreDeSintaxe:
    """`rich` nao entra, e `print` nao entra. Medido no fonte, e nao no log."""

    def test_renda_console_nao_importa_rich(self) -> None:
        arvore = ast.parse(FONTE_DO_CONSOLE.read_text(encoding="utf-8"))
        importados = set()
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                importados.update(alias.name.split(".")[0] for alias in no.names)
            elif isinstance(no, ast.ImportFrom) and no.module:
                importados.add(no.module.split(".")[0])

        assert "rich" not in importados, (
            "`rich` NAO esta instalado nesta arvore e nao entra nesta fase "
            "(CTX-1). O `ROADMAP.md` e o `CLAUDE.md` que o citam estao velhos."
        )

    def test_renda_console_nao_chama_print(self) -> None:
        arvore = ast.parse(FONTE_DO_CONSOLE.read_text(encoding="utf-8"))
        chamados = {
            no.func.id
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Name)
        }

        assert "print" not in chamados, (
            "quem imprime e o laco, com `log.info` — assim a MESMA string vai "
            "para o console E para o `scanner.log` rotativo"
        )
