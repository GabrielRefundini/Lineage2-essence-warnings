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


# ===========================================================================
# O BLOCO POR INTERVALO (CONS-01) -- o que o programa CALCULOU
# ===========================================================================
#
# A LINHA mostra o que a tela do jogo AFIRMA; o BLOCO mostra o que o programa
# DERIVOU. Derivacao carrega `n` e recencia, e `n` nao cabe numa linha: os dez
# valores juntos medem 87 colunas e a largura desta casa e 76.

from fractions import Fraction  # noqa: E402

from l2scanner.mercado_analise import Evidencia  # noqa: E402
from l2scanner.mercado_console import (  # noqa: E402
    LARGURA_DO_AVISO,
    OrcamentoDoTick,
)
from l2scanner.renda_conta import (  # noqa: E402
    GRANDEZA_DA_ADENA,
    GRANDEZA_DO_EXP,
    MOTIVO_DA_TAXA_DE_EXP_NEGATIVA,
    MOTIVO_DA_TAXA_DE_EXP_ZERADA,
    UNIDADE_DA_JANELA,
    AsDuasTaxas,
    TaxaDaRenda,
    TempoAteONivel,
)
from l2scanner.renda_console import (  # noqa: E402
    bloco_da_renda,
    resumo_da_sessao_da_renda,
)

# A NOITE MEDIDA que o `03-CONTEXT.md` descreve: 4h52 de pe, 4h12 farmadas,
# 466 mil adena/h na janela curta contra 226 mil na sessao -- e a diferenca
# inteira entre as duas e TEMPO PARADO.
DESDE = 1_000_000.0
AGORA = DESDE + 4 * 3600 + 52 * 60  # 4h52 de pe
FARMADAS = 4 * 3600 + 12 * 60  # 4h12 farmadas
RECENCIA = AGORA - 3.0  # "ha 3s"


def taxa(
    grandeza: str,
    por_hora: int | None,
    *,
    n: int = 142,
    piso: int = 8,
    motivo: str | None = None,
    farmada: float = FARMADAS,
    lacunas: int = 0,
    segundos_em_lacuna: float = 0.0,
) -> TaxaDaRenda:
    valor = None if por_hora is None else Fraction(por_hora)
    return TaxaDaRenda(
        grandeza=grandeza,
        evidencia=Evidencia(n=n, piso=piso),
        por_hora=valor,
        por_minuto=None if valor is None else valor / 60,
        motivo_da_ausencia=motivo,
        janela_farmada_em_segundos=farmada,
        unidade_da_janela=UNIDADE_DA_JANELA,
        lacunas_excluidas=lacunas,
        segundos_em_lacuna=segundos_em_lacuna,
        ate=None if por_hora is None else RECENCIA,
    )


def duas(janela, sessao) -> AsDuasTaxas:
    return AsDuasTaxas(janela=janela, sessao=sessao)


def bloco(**trocas) -> str:
    base = {
        "campos": campos(),
        "taxas_de_exp": duas(
            taxa(GRANDEZA_DO_EXP, 2_410_000, n=142, farmada=600.0),
            taxa(GRANDEZA_DO_EXP, 1_880_000, n=3210),
        ),
        "taxas_de_adena": duas(
            taxa(GRANDEZA_DA_ADENA, 466_000, n=88, farmada=600.0),
            taxa(GRANDEZA_DA_ADENA, 226_000, n=1980),
        ),
        "eta": TempoAteONivel(
            segundos=Fraction(3 * 3600 + 20 * 60), motivo_da_ausencia=None
        ),
        "contagem": ContagemDaRenda(aceitas=3210, lacunas=2),
        "desde": DESDE,
        "agora": AGORA,
        # AS TAXAS DE RECUSA MEDIDAS EM CAMPO na Fase 1, sobre 14 amostras.
        "recusas_por_campo": {
            CAMPO_DO_NIVEL: 79,
            CAMPO_DA_ADENA: 21,
            CAMPO_DO_EXP: 0,
        },
        "tiques": 100,
    }
    base.update(trocas)
    return bloco_da_renda(**base)


class TestALarguraDoBloco:
    def test_NENHUMA_linha_do_bloco_passa_de_76_colunas(self) -> None:
        """76 e a largura que este fonte cita com razao ao lado."""
        for linha in bloco().splitlines():
            assert len(linha) <= LARGURA_DO_AVISO, (
                f"{len(linha)} colunas:\n  {linha}"
            )

    def test_nem_com_o_motivo_MAIS_LONGO_de_ausencia_de_taxa(self) -> None:
        """O motivo real de `taxa_por_hora` tem ~95 caracteres: ele DOBRA em
        linhas de continuacao, e nunca e truncado -- o texto nomeia QUAL piso
        faltou, e um piso pela metade nao ensina o conserto."""
        longo = (
            "amostras abaixo do piso: 3 passo(s) aceito(s) e o piso "
            "'amostras_minimas_para_taxa' e 8. Faltam 5."
        )
        texto = bloco(
            taxas_de_exp=duas(
                taxa(GRANDEZA_DO_EXP, None, n=3, motivo=longo),
                taxa(GRANDEZA_DO_EXP, None, n=3, motivo=longo),
            )
        )

        for linha in texto.splitlines():
            assert len(linha) <= LARGURA_DO_AVISO, (
                f"{len(linha)} colunas:\n  {linha}"
            )
        assert "amostras_minimas_para_taxa" in texto, (
            "o motivo nomeia QUAL piso faltou, e ele nao pode ser truncado"
        )


class TestAsDuasTaxasSaemJUNTAS:
    def test_as_QUATRO_taxas_aparecem_e_ROTULADAS(self) -> None:
        """Apresentar so uma MENTE POR OMISSAO, e a mentira esta medida:
        226 mil adena/h na sessao contra 466 mil/h na janela -- um fator de
        dois, e a diferenca inteira e tempo parado."""
        texto = bloco()

        assert "2,41 M" in texto, "XP/h da janela"
        assert "1,88 M" in texto, "XP/h da sessao"
        assert "466 mil" in texto, "adena/h da janela"
        assert "226 mil" in texto, "adena/h da sessao"
        assert texto.count("janela") >= 2 and texto.count("sessao") >= 2

    def test_cada_taxa_sai_com_n_E_RECENCIA_COLADOS(self) -> None:
        """CONS-01 pede com todas as letras: `n` e recencia colados nos
        numeros como o `--mercado` ja faz. Um numero nu falha."""
        import re

        texto = bloco()
        for valor in ("2,41 M", "1,88 M", "466 mil", "226 mil"):
            linha = next(l for l in texto.splitlines() if valor in l)
            assert re.search(r"\(n=\d+, ha [^)]+\)", linha), (
                f"a taxa saiu como numero NU:\n  {linha}"
            )

    def test_o_denominador_diz_MINUTOS_FARMADOS_e_nao_de_relogio(self) -> None:
        assert UNIDADE_DA_JANELA in bloco()
        assert "minutos de relogio" not in bloco()

    def test_uma_taxa_SEM_EVIDENCIA_sai_como_o_motivo_DELA(self) -> None:
        """Nunca `0` e nunca `--`: zero e um fato sobre o farm."""
        motivo = "janela abaixo do piso: 40.0 segundos de minutos farmados"
        texto = bloco(
            taxas_de_adena=duas(
                taxa(GRANDEZA_DA_ADENA, None, n=2, motivo=motivo),
                taxa(GRANDEZA_DA_ADENA, 226_000, n=1980),
            )
        )

        assert "janela abaixo do piso" in texto
        linhas = [l for l in texto.splitlines() if "adena/h" in l]
        assert not any(
            l.rstrip().endswith(" 0") or "--" in l for l in linhas
        ), f"a taxa ausente virou zero ou tracos:\n{linhas}"


class TestOQueSaiuDoDenominador:
    def test_as_lacunas_e_o_tempo_cego_APARECEM(self) -> None:
        """E o que impede "a taxa caiu" de ser confundido com "o scanner nao
        viu"."""
        texto = bloco(
            taxas_de_exp=duas(
                taxa(GRANDEZA_DO_EXP, 2_410_000, farmada=600.0),
                taxa(
                    GRANDEZA_DO_EXP,
                    1_880_000,
                    n=3210,
                    lacunas=2,
                    segundos_em_lacuna=18 * 60,
                ),
            )
        )

        assert "lacunas excluidas" in texto
        assert "18min" in texto, "o tempo cego sai legivel, e nao em segundos"


class TestOTempoAteONivel:
    def test_com_taxa_ele_sai_como_FALTA(self) -> None:
        assert "3h20" in bloco()

    def test_os_TRES_motivos_de_ausencia_produzem_TRES_TEXTOS_DIFERENTES(
        self,
    ) -> None:
        """O conserto do usuario e diferente em cada um: va farmar, pare de
        morrer, espere mais um pouco. Fundir dois faria dois consertos
        diferentes virarem a mesma mensagem."""
        textos = set()
        for motivo in (
            MOTIVO_DA_TAXA_DE_EXP_ZERADA,
            MOTIVO_DA_TAXA_DE_EXP_NEGATIVA,
            "amostras abaixo do piso: 3 passo(s) aceito(s)",
        ):
            texto = bloco(
                eta=TempoAteONivel(segundos=None, motivo_da_ausencia=motivo)
            )
            linhas = [l for l in texto.splitlines() if "nivel" in l.lower()]
            textos.add("\n".join(linhas))

        assert len(textos) == 3, (
            "os tres motivos de ausencia do ETA colapsaram em menos de tres "
            "mensagens"
        )


class TestHaQuantoTempoASessaoCorre:
    def test_a_sessao_sai_com_os_DOIS_tempos_e_nunca_com_um_so(self) -> None:
        """O criterio 1 do ROADMAP pede "ha quanto tempo a sessao corre" -- o
        tempo DE PE, contado do arranque. O `farmadas` e o denominador da
        taxa, com as lacunas subtraidas. Numa noite com 40 min cegos eles
        divergem em 40 min, e mostrar so o farmado responde uma pergunta que o
        usuario nao fez."""
        texto = bloco()

        assert "4h52" in texto, "o tempo DE PE (o que o criterio pede)"
        assert "4h12" in texto, "o tempo FARMADO (o denominador da taxa)"
        linha = next(l for l in texto.splitlines() if "4h52" in l)
        assert "4h12" in linha, "os dois saem na MESMA linha, e nao separados"

    def test_sem_lacuna_nenhuma_os_dois_numeros_saem_IGUAIS_e_MESMO_ASSIM(
        self,
    ) -> None:
        """A igualdade e um fato sobre a noite (nao houve cegueira);
        esconde-la faria o usuario adivinhar se o segundo numero sumiu ou
        coincidiu."""
        de_pe = 2 * 3600 + 30 * 60
        texto = bloco(
            agora=DESDE + de_pe,
            taxas_de_exp=duas(
                taxa(GRANDEZA_DO_EXP, 2_410_000, farmada=600.0),
                taxa(GRANDEZA_DO_EXP, 1_880_000, n=3210, farmada=float(de_pe)),
            ),
        )
        linha = next(l for l in texto.splitlines() if "sessao de pe" in l)

        assert linha.count("2h30") == 2, (
            f"os dois numeros tem de sair mesmo iguais:\n  {linha}"
        )

    def test_a_duracao_NAO_tem_casa_decimal_pendurada(self) -> None:
        """`dashboard_dados.py:624-628` mediu `total_seconds()` devolvendo
        `69713.696` onde o inteiro dizia `69713`. Um `timedelta` no meio deste
        caminho traz aquele erro de volta."""
        texto = bloco(agora=DESDE + 4 * 3600 + 52 * 60 + 0.696)
        linha = next(l for l in texto.splitlines() if "sessao de pe" in l)

        assert "." not in linha and "," not in linha, (
            f"a duracao vazou casa decimal:\n  {linha}"
        )


class TestPorQueONEEsse:
    def test_as_taxas_de_recusa_POR_CAMPO_aparecem(self) -> None:
        """Medidas em campo: nivel 79%, adena 21%, EXP 0%. Um painel que as
        esconde faz o usuario concluir que o scanner travou -- e isso JA
        aconteceu em producao em 2026-09-01 com o aviso de layout do mercado.
        """
        texto = bloco()

        assert "79%" in texto
        assert "21%" in texto

    def test_o_campo_com_ZERO_recusa_sai_MESMO_ASSIM(self) -> None:
        """Sumir com o EXP faria parecer que ele nao foi medido."""
        texto = bloco()
        linhas = [l for l in texto.splitlines() if "EXP" in l and "%" in l]

        assert any("0%" in l for l in linhas), (
            f"o campo de 0% de recusa sumiu do bloco:\n{texto}"
        )

    def test_uma_recusa_RARA_nao_e_arredondada_para_zero(self) -> None:
        """Uma recusa em mil tiques e 0,1% e nao 0%: arredondar apagaria a
        unica evidencia de que o campo chegou a falhar."""
        texto = bloco(
            recusas_por_campo={
                CAMPO_DO_NIVEL: 1,
                CAMPO_DO_EXP: 0,
                CAMPO_DA_ADENA: 0,
            },
            tiques=1000,
        )
        linha = next(
            l for l in texto.splitlines() if "nivel" in l and "%" in l
        )

        assert "0,1%" in linha, (
            f"a recusa rara foi arredondada para zero:\n  {linha}"
        )


class TestOBlocoNaoImprime:
    def test_ele_devolve_texto(self, capsys) -> None:
        devolvido = bloco()
        capturado = capsys.readouterr()

        assert capturado.out == "" and capturado.err == ""
        assert isinstance(devolvido, str) and "\n" in devolvido


class TestOResumoDaSessao:
    def test_ele_sai_com_ZERO_linhas_gravadas(self, tmp_path) -> None:
        class RegistroFalso:
            arquivo = tmp_path / "faerlina.csv"

        texto = resumo_da_sessao_da_renda(
            ContagemDaRenda(),
            OrcamentoDoTick(limite=1.0),
            RegistroFalso(),
            recusas_por_campo={},
            tiques=0,
            tiques_por_estado={},
        )

        assert "RESUMO DA SESSAO DE RENDA" in texto
        assert str(tmp_path / "faerlina.csv") in texto

    def test_ele_traz_o_orcamento_de_tique(self, tmp_path) -> None:
        class RegistroFalso:
            arquivo = tmp_path / "faerlina.csv"

        orcamento = OrcamentoDoTick(limite=1.0)
        for tempo in (0.1, 0.2, 1.4):
            orcamento.registrar(tempo)

        texto = resumo_da_sessao_da_renda(
            ContagemDaRenda(aceitas=2),
            orcamento,
            RegistroFalso(),
            recusas_por_campo={CAMPO_DO_NIVEL: 2},
            tiques=3,
            tiques_por_estado={"lendo": 2, "sem_leitura": 1},
        )

        assert "p50" in texto and "p95" in texto and "maximo" in texto
        assert "1 de 3" in texto, "o tique que estourou o orcamento"

    def test_as_DUAS_secoes_de_recusa_tem_titulos_DIFERENTES(
        self, tmp_path
    ) -> None:
        """Recusa POR CAMPO e recusa DE PAR sao fatos diferentes.

        A primeira sai de `CamposDaRenda` (o pixel nao virou numero); a segunda
        sai de `contagem.recusadas_por_motivo`, alimentado por `passo.recusas`,
        que e a tupla que `conferir_o_par` devolveu. Os consertos sao opostos:
        calibrar o retangulo contra desconfiar da leitura. As duas ja tiveram o
        MESMO titulo por uma revisao deste arquivo, e quem procurava um numero
        pelo titulo achava o outro.
        """
        class RegistroFalso:
            arquivo = tmp_path / "faerlina.csv"

        texto = resumo_da_sessao_da_renda(
            ContagemDaRenda(aceitas=2, recusadas_por_motivo={"exp-andou": 1}),
            OrcamentoDoTick(limite=1.0),
            RegistroFalso(),
            recusas_por_campo={CAMPO_DO_NIVEL: 2},
            tiques=3,
            tiques_por_estado={"lendo": 2, "sem_leitura": 1},
        )

        assert "RECUSA POR CAMPO" in texto
        assert "RECUSA DE PAR" in texto
        titulos = [l for l in texto.splitlines() if l.startswith("RECUSA")]
        assert len(set(titulos)) == 2, f"os dois titulos colidiram: {titulos}"
