"""A FATIA INTEIRA do modo `--renda`: um frame entra, uma linha sai no disco.

O QUE ESTE ARQUIVO PROVA
=========================
Que as tres fases estao LIGADAS. `renda_leitura` (Fase 1), `renda_conta` e
`renda_registro` (Fase 2) nasceram sem chamador de producao, de proposito;
`renda_laco` e o chamador. Um teste que so importasse os tres modulos ficaria
verde com o fio cortado.

ELE RODA SEM JOGO ABERTO E SEM OCR, pelas CINCO alavancas de injecao —
`fonte=`, `ler_campos=`, `relogio=`, `pasta=` e `ticks_maximos=`. A alavanca
`ler_campos=` e o seam que o mercado NAO tem: `renda_leitura.py:66` importa
`ler_texto` por NOME no topo do modulo, entao a injecao sobe um nivel, do OCR
para a leitura inteira (Achado 9 da pesquisa).
"""

from __future__ import annotations

import argparse
import ast
import logging
from pathlib import Path

import numpy as np
import pytest

from l2scanner.calibracao import Calibracao
from l2scanner.config import AgendaInvalida, AjustesDaRenda
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.relogio import Relogio
from l2scanner.renda_conta import (
    DESCONTINUIDADE_DA_ANCORA,
    DESCONTINUIDADE_DA_LACUNA,
    DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS,
    SEM_DESCONTINUIDADE,
)
from l2scanner.renda_laco import (
    ERROS_SEGUIDOS_PARA_DESISTIR,
    SAIDA_CEGA,
    SAIDA_RECUSADA,
    _com_o_pack_da_linha_de_comando,
    laco_da_renda,
)
from l2scanner.renda_leitura import (
    CAMPO_DA_ADENA,
    CAMPO_DO_EXP,
    CAMPO_DO_NIVEL,
    MOTIVO_DO_CAMPO_VAZIO,
    CamposDaRenda,
    RecusaDaRenda,
    ValorDaAdena,
    ValorDaRenda,
)
from l2scanner.renda_console import PREFIXO_DA_LINHA
from l2scanner.renda_registro import ARQUIVO_DO_LEIAME, arquivo_do_personagem

FIXTURES = Path(__file__).parent / "fixtures" / "renda"
CALIBRACAO = FIXTURES / "calibracao_de_fixture.json"

FONTE_DO_LACO = Path(__file__).parent.parent / "l2scanner" / "renda_laco.py"
FONTE_DO_CONSOLE = (
    Path(__file__).parent.parent / "l2scanner" / "renda_console.py"
)

PERSONAGEM = "Faerlina"
TITULO = f"{PERSONAGEM} - XM Essence"

# A janela gravada nas DUAS entradas da calibracao de fixtura, e a mesma das
# duas instancias do usuario no `calibration.json` real (P-1, remedida no
# checkout PRINCIPAL em 2026-09-03).
LARGURA_DA_JANELA = 1720
ALTURA_DA_JANELA = 1392


# ---------------------------------------------------------------------------
# O IDIOMA DE TESTE DE LACO, copiado de `tests/test_mercado_modo.py:121-167`
# ---------------------------------------------------------------------------


class FonteFalsa:
    """A porta de captura, e ela ACABA — `StopIteration` e o sinal de fim.

    `fechada` existe para o teste provar que o `finally` do laco fechou a
    captura, exatamente como a `FonteFalsa` do mercado.
    """

    def __init__(self, quantos: int) -> None:
        self._restam = quantos
        self._indice = 0
        self.fechada = False

    def capturar(self) -> Frame:
        if self._restam <= 0:
            raise StopIteration
        self._restam -= 1
        self._indice += 1
        return Frame(
            pixels=np.zeros((4, 4, 3), dtype=np.uint8),
            indice=self._indice,
            saude=SaudeDoFrame.OK,
        )

    def fechar(self) -> None:
        self.fechada = True


class FonteQueQuebra:
    """Levanta sempre, para provar o desfecho de dez erros seguidos."""

    def __init__(self, quebras_antes_de_acertar: int | None = None) -> None:
        self.quebras = 0
        self._ate = quebras_antes_de_acertar
        self.fechada = False

    def capturar(self) -> Frame:
        if self._ate is not None and self.quebras >= self._ate:
            self.quebras = 0
            return Frame(
                pixels=np.zeros((4, 4, 3), dtype=np.uint8),
                indice=0,
                saude=SaudeDoFrame.OK,
            )
        self.quebras += 1
        raise RuntimeError("a WGC perdeu a janela")

    def fechar(self) -> None:
        self.fechada = True


class FonteQueInterrompe:
    """`Ctrl+C` no meio do tique. Nao e erro: e o usuario mandando parar."""

    def __init__(self, ate: int) -> None:
        self.ate = ate
        self.vistas = 0
        self.fechada = False

    def capturar(self) -> Frame:
        self.vistas += 1
        if self.vistas > self.ate:
            raise KeyboardInterrupt
        return Frame(
            pixels=np.zeros((4, 4, 3), dtype=np.uint8),
            indice=self.vistas,
            saude=SaudeDoFrame.OK,
        )

    def fechar(self) -> None:
        self.fechada = True


def argumentos(**extras) -> argparse.Namespace:
    """`intervalo=0.0` e o que torna o teste instantaneo: o `sleep` compensado
    do laco so dorme quando sobra tempo."""
    base = {"janela": TITULO, "intervalo": 0.0, "status_a_cada": 10_000.0}
    base.update(extras)
    return argparse.Namespace(**base)


@pytest.fixture(scope="module")
def cal() -> Calibracao:
    return Calibracao.carregar(CALIBRACAO)


# ---------------------------------------------------------------------------
# A SEQUENCIA DE CAMPOS, montada A MAO — o mesmo construtor dos 286 casos
# que `tests/test_renda_conta.py` ja usa. Nada de PNG e nada de OCR.
# ---------------------------------------------------------------------------


def campos_de(
    nivel: int | None = 67,
    exp_em_decimos: int | None = 792_568,
    adena: int | None = 17_592_060,
) -> CamposDaRenda:
    """`None` em qualquer campo vira RECUSA nomeada naquele campo."""

    def _nivel(valor):
        if valor is None:
            return RecusaDaRenda(
                campo=CAMPO_DO_NIVEL,
                motivo=MOTIVO_DO_CAMPO_VAZIO,
                detalhe="a mascara nao deixou nada de pe",
            )
        return ValorDaRenda(
            campo=CAMPO_DO_NIVEL, valor=valor, escalas=2, texto=str(valor)
        )

    def _exp(valor):
        if valor is None:
            return RecusaDaRenda(
                campo=CAMPO_DO_EXP,
                motivo=MOTIVO_DO_CAMPO_VAZIO,
                detalhe="a barra nao deu leitura",
            )
        return ValorDaRenda(
            campo=CAMPO_DO_EXP, valor=valor, escalas=2, texto=str(valor)
        )

    def _adena(valor):
        if valor is None:
            return RecusaDaRenda(
                campo=CAMPO_DA_ADENA,
                motivo=MOTIVO_DO_CAMPO_VAZIO,
                detalhe="nenhum glifo sobreviveu a peneira",
            )
        return ValorDaAdena(
            campo=CAMPO_DA_ADENA, valor=valor, glifos=10, texto=str(valor)
        )

    return CamposDaRenda(
        personagem=PERSONAGEM,
        nivel=_nivel(nivel),
        exp=_exp(exp_em_decimos),
        adena=_adena(adena),
    )


class LeitoraFalsa:
    """A alavanca `ler_campos=`: devolve os campos DA VEZ, sem tocar em pixel.

    Ela afirma a assinatura de producao — `(frame, *, personagem, calibracao)` —
    para que trocar o default por ela nao esconda uma divergencia de contrato.
    """

    def __init__(self, sequencia) -> None:
        self._sequencia = list(sequencia)
        self._indice = 0
        self.chamadas = 0
        self.personagens = []

    def __call__(self, frame, *, personagem, calibracao) -> CamposDaRenda:
        self.chamadas += 1
        self.personagens.append(personagem)
        campos = self._sequencia[min(self._indice, len(self._sequencia) - 1)]
        self._indice += 1
        return campos


class RelogioFalso:
    """Os carimbos vem DAQUI e nunca de `datetime.now()` dentro do laco."""

    def __init__(self, carimbos) -> None:
        self._carimbos = list(carimbos)
        self._indice = 0

    def agora_epoch(self) -> float:
        carimbo = self._carimbos[
            min(self._indice, len(self._carimbos) - 1)
        ]
        self._indice += 1
        return float(carimbo)


def linhas_de_dado(caminho: Path) -> list[str]:
    texto = caminho.read_text(encoding="utf-8")
    return [linha for linha in texto.splitlines()[1:] if linha.strip()]


def coluna(caminho: Path, nome: str) -> list[str]:
    import csv

    from l2scanner.renda_registro import SEPARADOR

    with caminho.open("r", encoding="utf-8", newline="") as fonte:
        return [
            linha[nome]
            for linha in csv.DictReader(fonte, delimiter=SEPARADOR)
        ]


def rodar(
    cal,
    tmp_path,
    *,
    sequencia,
    carimbos,
    ticks=4,
    fonte=None,
    **extras,
):
    fonte = fonte if fonte is not None else FonteFalsa(ticks)
    leitora = LeitoraFalsa(sequencia)
    codigo = laco_da_renda(
        argumentos(**extras),
        cal,
        fonte=fonte,
        ler_campos=leitora,
        relogio=RelogioFalso(carimbos),
        pasta=tmp_path,
        ticks_maximos=ticks,
    )
    return codigo, fonte, leitora


# ---------------------------------------------------------------------------
# O PONTA A PONTA: `.renda/` DEIXA DE ESTAR VAZIO
# ---------------------------------------------------------------------------


class TestAFatiaInteira:
    def test_quatro_frames_produzem_QUATRO_linhas_de_dado(
        self, cal, tmp_path
    ) -> None:
        """O produto desta fase, do ponto de vista do usuario, e este arquivo.

        UMA LINHA POR TIQUE E O PRODUTO, porque ela e o denominador da taxa
        (`renda_registro.py:895-903`). Um laco que deduplicasse apagaria a
        maioria das linhas de uma noite de farm.
        """
        sequencia = [
            campos_de(exp_em_decimos=792_568, adena=17_592_060),
            campos_de(exp_em_decimos=792_600, adena=17_600_000),
            campos_de(exp_em_decimos=792_640, adena=17_610_000),
            campos_de(exp_em_decimos=792_700, adena=17_620_000),
        ]
        codigo, fonte, leitora = rodar(
            cal, tmp_path, sequencia=sequencia, carimbos=[100, 101, 102, 103]
        )

        assert codigo == 0
        assert fonte.fechada, "o `finally` tem de fechar a captura"
        assert leitora.chamadas == 4

        arquivo = arquivo_do_personagem(tmp_path, PERSONAGEM)
        assert arquivo.is_file(), "o CSV da renda nao nasceu"
        assert len(linhas_de_dado(arquivo)) == 4, (
            "quatro tiques tem de deixar quatro linhas: o fio "
            "laco -> registro esta cortado"
        )

    def test_a_pasta_nasce_com_DOIS_arquivos_e_nao_com_um(
        self, cal, tmp_path
    ) -> None:
        """`LEIAME.txt` alem do CSV (C-10).

        `RegistroDaRenda.__init__` escreve o leiame logo DEPOIS do `mkdir` e
        antes de qualquer leitura. Quem for ler a pasta precisa saber que ela
        tem dois arquivos, e nao um.
        """
        pasta = tmp_path / "renda"
        rodar(
            cal,
            pasta,
            sequencia=[campos_de()],
            carimbos=[100, 101],
            ticks=2,
        )

        nomes = sorted(p.name for p in pasta.iterdir())
        assert nomes == sorted(
            [ARQUIVO_DO_LEIAME, arquivo_do_personagem(pasta, PERSONAGEM).name]
        ), f"a pasta nasceu com {nomes}"

    def test_a_leitura_e_sempre_do_personagem_DO_TITULO(
        self, cal, tmp_path
    ) -> None:
        """Nunca de `--personagem`: seria a segunda verdade sobre a janela.

        Medido (M-F): ler uma instancia com o retangulo da outra devolve `349`
        ou `112` — numeros plausiveis que passam por qualquer validacao.
        """
        _, _, leitora = rodar(
            cal, tmp_path, sequencia=[campos_de()], carimbos=[100], ticks=2
        )

        assert set(leitora.personagens) == {PERSONAGEM}


class TestAColunaDeDescontinuidade:
    def test_a_PRIMEIRA_amostra_sai_como_ancora_e_as_seguintes_vazias(
        self, cal, tmp_path
    ) -> None:
        rodar(
            cal,
            tmp_path,
            sequencia=[campos_de(), campos_de(), campos_de()],
            carimbos=[100, 101, 102],
            ticks=3,
        )

        marcas = coluna(
            arquivo_do_personagem(tmp_path, PERSONAGEM), "descontinuidade"
        )
        assert marcas[0] == DESCONTINUIDADE_DA_ANCORA
        assert marcas[1:] == [SEM_DESCONTINUIDADE] * 2

    def test_um_buraco_de_carimbo_vira_LACUNA(self, cal, tmp_path) -> None:
        """Um dos DOIS marcadores que so um laco ao vivo produz (C-3).

        `lacuna_maxima_segundos` = 60 por default, entao 500 s entre dois
        carimbos e cegueira e nao cadencia.
        """
        rodar(
            cal,
            tmp_path,
            sequencia=[campos_de(), campos_de()],
            carimbos=[100, 700],
            ticks=2,
        )

        marcas = coluna(
            arquivo_do_personagem(tmp_path, PERSONAGEM), "descontinuidade"
        )
        assert marcas == [
            DESCONTINUIDADE_DA_ANCORA,
            DESCONTINUIDADE_DA_LACUNA,
        ]

    def test_um_carimbo_que_anda_para_tras_e_NOMEADO(
        self, cal, tmp_path
    ) -> None:
        """O outro dos dois (C-3): o dual boot do usuario entre dois tiques."""
        rodar(
            cal,
            tmp_path,
            sequencia=[campos_de(), campos_de()],
            carimbos=[700, 100],
            ticks=2,
        )

        marcas = coluna(
            arquivo_do_personagem(tmp_path, PERSONAGEM), "descontinuidade"
        )
        assert marcas[1] == DESCONTINUIDADE_DO_RELOGIO_PARA_TRAS


class TestOCampoRecusadoNaoBloqueiaALinha:
    def test_um_nivel_recusado_GRAVA_A_LINHA_MESMO_ASSIM(
        self, cal, tmp_path
    ) -> None:
        """A fase NAO constroi um segundo portao de admissao.

        Medido na Fase 1: 79% de recusa no nivel. Um laco que so gravasse a
        amostra completa entregaria linha em ~4% dos tiques.
        """
        rodar(
            cal,
            tmp_path,
            sequencia=[campos_de(nivel=None), campos_de(nivel=None)],
            carimbos=[100, 101],
            ticks=2,
        )

        arquivo = arquivo_do_personagem(tmp_path, PERSONAGEM)
        assert len(linhas_de_dado(arquivo)) == 2
        assert coluna(arquivo, "motivo_do_nivel") == [MOTIVO_DO_CAMPO_VAZIO] * 2
        assert coluna(arquivo, "exp_decimos")[0], "o EXP continua saindo"


# ---------------------------------------------------------------------------
# O CONSOLE, medido por `caplog` — a MESMA string vai para o `scanner.log`
# ---------------------------------------------------------------------------


class TestOConsole:
    def test_a_linha_do_tique_sai_TODO_TIQUE(self, cal, tmp_path, caplog):
        """Nao ha analogo do latch de painel aberto do mercado: a barra de EXP
        esta SEMPRE na tela."""
        with caplog.at_level(logging.INFO):
            rodar(
                cal,
                tmp_path,
                sequencia=[campos_de()],
                carimbos=[100, 101, 102],
                ticks=3,
            )

        # `caplog.text` prefixa cada linha com nivel e logger, entao o teste
        # procura o PREFIXO da linha do tique dentro da linha, e nao no comeco.
        tiques = [
            linha
            for linha in caplog.text.splitlines()
            if f"{PREFIXO_DA_LINHA} | " in linha
        ]
        assert len(tiques) == 3, f"sairam {len(tiques)} linhas de tique"

    def test_a_linha_mostra_os_tres_valores_QUE_A_TELA_AFIRMA(
        self, cal, tmp_path, caplog
    ):
        with caplog.at_level(logging.INFO):
            rodar(
                cal, tmp_path, sequencia=[campos_de()], carimbos=[100], ticks=1
            )

        assert "nivel 67" in caplog.text
        assert "79,2568%" in caplog.text
        assert "17.592.060" in caplog.text

    def test_o_resumo_da_sessao_sai_no_finally_e_NOMEIA_O_ARQUIVO(
        self, cal, tmp_path, caplog
    ):
        with caplog.at_level(logging.INFO):
            rodar(
                cal, tmp_path, sequencia=[campos_de()], carimbos=[100], ticks=1
            )

        assert str(arquivo_do_personagem(tmp_path, PERSONAGEM)) in caplog.text

    def test_o_bloco_sai_UMA_VEZ_no_arranque_e_NAO_por_tique(
        self, cal, tmp_path, caplog
    ):
        """A razao esta em `mercado_console.py:490-496`: repintar um bloco de
        dezenas de linhas por segundo AFOGARIA a linha ao vivo.

        E ele sai ja na primeira volta, e nao so depois de trinta segundos:
        sem isso o usuario fica olhando para linhas de tique sem saber se o
        calculo esta vivo.
        """
        with caplog.at_level(logging.INFO):
            rodar(
                cal,
                tmp_path,
                sequencia=[campos_de()],
                carimbos=list(range(100, 120)),
                ticks=10,
                status_a_cada=10_000.0,
            )

        assert caplog.text.count("O QUE ISSO RENDE") == 1, (
            "o bloco saiu por TIQUE e nao por intervalo"
        )

    def test_com_intervalo_zero_o_bloco_sai_a_CADA_tique(
        self, cal, tmp_path, caplog
    ):
        """O controle do teste acima: sem ele, um bloco que nunca saisse
        passaria por 'saiu uma vez' com a contagem em zero."""
        with caplog.at_level(logging.INFO):
            rodar(
                cal,
                tmp_path,
                sequencia=[campos_de()],
                carimbos=list(range(100, 110)),
                ticks=3,
                status_a_cada=0.0,
            )

        assert caplog.text.count("O QUE ISSO RENDE") == 3

    def test_as_recusas_POR_CAMPO_sao_contadas_pelo_LACO_todo_tique(
        self, cal, tmp_path, caplog
    ):
        """`ContagemDaRenda.recusadas_por_motivo` NAO carrega este numero.

        Ela e somada em `contar_o_passo` a partir de `passo.recusas`, que e a
        tupla que `conferir_o_par` devolveu — e a docstring de `PassoDaRenda`
        diz que ela *"sai vazia no caminho de `CamposDaRenda` com um campo
        recusado"*. Os 79% do nivel medidos na Fase 1 nao passam por ali em
        tique nenhum: eles vem de `CamposDaRenda.por_campo`, e quem os conta e
        este laco.
        """
        with caplog.at_level(logging.INFO):
            rodar(
                cal,
                tmp_path,
                sequencia=[campos_de(nivel=None)],
                carimbos=[100, 101, 102, 103],
                ticks=4,
                status_a_cada=0.0,
            )

        bloco = caplog.text[caplog.text.rindex("POR QUE O `n` E ESSE") :]
        linha = next(
            l for l in bloco.splitlines() if "nivel" in l and "%" in l
        )
        assert "100%" in linha, (
            f"o laco nao esta contando a recusa POR CAMPO:\n  {linha}"
        )
        exp = next(l for l in bloco.splitlines() if "EXP" in l and "%" in l)
        assert "0%" in exp, "o campo que nunca recusou tem de sair como 0%"

    def test_o_resumo_sai_MESMO_numa_sessao_de_zero_linhas(
        self, cal, tmp_path, caplog
    ):
        """O `vigiar-renda.bat` do `03-04` nao tem bloco de encerramento: o
        resumo sai do proprio programa."""
        with caplog.at_level(logging.INFO):
            codigo, fonte, _ = rodar(
                cal,
                tmp_path,
                sequencia=[campos_de()],
                carimbos=[100],
                ticks=4,
                fonte=FonteFalsa(0),
            )

        assert codigo == 0
        assert fonte.fechada
        assert linhas_de_dado(arquivo_do_personagem(tmp_path, PERSONAGEM)) == []
        assert "RESUMO DA SESSAO DE RENDA" in caplog.text


# ---------------------------------------------------------------------------
# OS DESFECHOS: o laco DEVOLVE codigo e nunca levanta
# ---------------------------------------------------------------------------


class TestOsDesfechos:
    def test_a_fonte_que_acaba_encerra_LIMPO(self, cal, tmp_path) -> None:
        codigo, fonte, _ = rodar(
            cal,
            tmp_path,
            sequencia=[campos_de()],
            carimbos=[100],
            ticks=None,
            fonte=FonteFalsa(2),
        )
        assert codigo == 0
        assert fonte.fechada

    def test_dez_erros_seguidos_devolvem_UM_e_nao_levantam(
        self, cal, tmp_path
    ) -> None:
        fonte = FonteQueQuebra()
        codigo = laco_da_renda(
            argumentos(),
            cal,
            fonte=fonte,
            ler_campos=LeitoraFalsa([campos_de()]),
            relogio=RelogioFalso([100]),
            pasta=tmp_path,
            ticks_maximos=None,
        )

        assert codigo == SAIDA_CEGA
        assert fonte.quebras == ERROS_SEGUIDOS_PARA_DESISTIR
        assert fonte.fechada

    def test_UM_sucesso_no_meio_zera_o_contador_de_erros(
        self, cal, tmp_path
    ) -> None:
        """Sem isto, uma noite com um soluco a cada nove tiques morreria."""
        fonte = FonteQueQuebra(quebras_antes_de_acertar=3)
        codigo = laco_da_renda(
            argumentos(),
            cal,
            fonte=fonte,
            ler_campos=LeitoraFalsa([campos_de()]),
            relogio=RelogioFalso([100, 101, 102, 103]),
            pasta=tmp_path,
            ticks_maximos=20,
        )

        assert codigo == 0, "o contador nao zerou no sucesso"

    def test_ctrl_c_nao_e_erro_e_cai_no_finally(self, cal, tmp_path, caplog):
        fonte = FonteQueInterrompe(ate=2)
        with caplog.at_level(logging.INFO):
            codigo = laco_da_renda(
                argumentos(),
                cal,
                fonte=fonte,
                ler_campos=LeitoraFalsa([campos_de()]),
                relogio=RelogioFalso([100, 101, 102]),
                pasta=tmp_path,
                ticks_maximos=None,
            )

        assert codigo == 0
        assert fonte.fechada
        assert "Encerrado pelo usuario" in caplog.text


class TestOsPortoesDeArranque:
    def test_sem_personagem_no_titulo_o_laco_RECUSA_com_codigo_2(
        self, cal, tmp_path, caplog
    ) -> None:
        with caplog.at_level(logging.ERROR):
            codigo = laco_da_renda(
                argumentos(janela="uma janela sem separador"),
                cal,
                fonte=FonteFalsa(4),
                ler_campos=LeitoraFalsa([campos_de()]),
                relogio=RelogioFalso([100]),
                pasta=tmp_path,
                ticks_maximos=4,
            )

        assert codigo == SAIDA_RECUSADA
        assert not list(tmp_path.iterdir()), (
            "a recusa acontece ANTES de a pasta ser montada"
        )

    def test_personagem_SEM_CALIBRACAO_recusa_e_diz_quem_esta_calibrado(
        self, cal, tmp_path, caplog
    ) -> None:
        """A leitura NAO cai na calibracao do vizinho (LEIT-07)."""
        with caplog.at_level(logging.ERROR):
            codigo = laco_da_renda(
                argumentos(janela="Desconhecido - XM Essence"),
                cal,
                fonte=FonteFalsa(4),
                ler_campos=LeitoraFalsa([campos_de()]),
                relogio=RelogioFalso([100]),
                pasta=tmp_path,
                ticks_maximos=4,
            )

        assert codigo == SAIDA_RECUSADA
        assert "Faerlina" in caplog.text, "a recusa diz quem ESTA calibrado"
        assert "calibrar-renda" in caplog.text, "e diz o conserto"

    def test_o_registro_que_nao_monta_recusa_ANTES_da_captura(
        self, cal, tmp_path
    ) -> None:
        """A razao esta em `mercado_modo.py:428-431`: descobrir que a pasta nao
        abre depois de a janela estar de pe custa uma sessao WGC por nada."""
        ocupado = tmp_path / "ocupado"
        ocupado.write_text("um ARQUIVO no lugar da pasta", encoding="utf-8")

        fonte = FonteFalsa(4)
        codigo = laco_da_renda(
            argumentos(),
            cal,
            fonte=fonte,
            ler_campos=LeitoraFalsa([campos_de()]),
            relogio=RelogioFalso([100]),
            pasta=ocupado,
            ticks_maximos=4,
        )

        assert codigo == SAIDA_RECUSADA
        assert not fonte.fechada, "a fonte nem chegou a ser usada"


# ---------------------------------------------------------------------------
# OS PORTOES DE ARVORE DE SINTAXE — com CONTROLE POSITIVO
# ---------------------------------------------------------------------------


def _importados(caminho: Path) -> set[str]:
    """Varre `ast.Import` E `ast.ImportFrom`.

    Um `grep` por `import rich` NAO ve `from rich.live import Live`, e um
    portao fraco ao lado de um forte ensina que o fraco basta.
    """
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    achados: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            achados.update(alias.name.split(".")[0] for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            achados.add(no.module.split(".")[0])
    return achados


def _nomes_chamados(caminho: Path) -> set[str]:
    """Todo nome chamado, simples (`f(...)`) e por atributo (`a.f(...)`)."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    achados: set[str] = set()
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        alvo = no.func
        if isinstance(alvo, ast.Name):
            achados.add(alvo.id)
        elif isinstance(alvo, ast.Attribute):
            achados.add(alvo.attr)
    return achados


AS_QUATRO_REGRAS_DE_PAR = {
    "conferir_o_par",
    "o_exp_andou_para_tras",
    "o_nivel_andou_para_tras",
    "a_adena_saltou_ordem_de_grandeza",
}


class TestOPortaoDoChamadorUnico:
    """C-8: `tests/test_renda_par.py:704` exige que SO `renda_conta.py` chame
    as regras de par. Este portao afirma a mesma coisa PELO NOME do modulo
    novo, para que a causa apareca aqui e nao num teste de outra fase."""

    def test_o_laco_NAO_chama_nenhuma_das_quatro_regras_de_par(self) -> None:
        chamados = _nomes_chamados(FONTE_DO_LACO)

        assert not (chamados & AS_QUATRO_REGRAS_DE_PAR), (
            "o laco chama `renda_conta.passo_entre_campos` e mais nada. Duas "
            "portas para as regras de par sao duas politicas de recusa que "
            "divergem no dia em que uma delas mudar — e o portao de "
            "`tests/test_renda_par.py` fica VERMELHO com este modulo na arvore."
        )

    def test_o_laco_chama_a_UNICA_porta_da_conta(self) -> None:
        chamados = _nomes_chamados(FONTE_DO_LACO)

        assert "passo_entre_campos" in chamados
        assert "contar_o_passo" in chamados

    def test_CONTROLE_POSITIVO_um_modulo_que_chamasse_seria_ACUSADO(
        self, tmp_path
    ) -> None:
        """Sem controle, um portao que varre a arvore errada passa sempre."""
        falso = tmp_path / "falso.py"
        falso.write_text(
            "def x(a, b):\n    return conferir_o_par(a, b)\n", encoding="utf-8"
        )

        assert _nomes_chamados(falso) & AS_QUATRO_REGRAS_DE_PAR


class TestOPortaoDaFonteDeCaptura:
    """C-5: `capturar_completo()` PULA a classificacao de saude inteira.

    Sem `SaudeDoFrame` nao ha como distinguir FALHA de CONGELADO, e CEGO-01 e
    CEGO-02 ficam estruturalmente impossiveis no `03-02`.
    """

    def test_capturar_completo_aparece_NO_MAXIMO_UMA_VEZ(self) -> None:
        chamados = [
            no
            for no in ast.walk(
                ast.parse(FONTE_DO_LACO.read_text(encoding="utf-8"))
            )
            if isinstance(no, ast.Call)
            and isinstance(no.func, ast.Attribute)
            and no.func.attr == "capturar_completo"
        ]

        assert len(chamados) <= 1, (
            f"`capturar_completo` e chamada {len(chamados)} vezes; ela so pode "
            "existir no ARRANQUE, para medir a janela"
        )

    def test_o_corpo_do_tique_chama_capturar_e_nao_capturar_completo(
        self,
    ) -> None:
        """A medicao mora no arranque; o tique chama `capturar()`."""
        arvore = ast.parse(FONTE_DO_LACO.read_text(encoding="utf-8"))
        laco = next(
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.FunctionDef) and no.name == "laco_da_renda"
        )
        dentro_do_while = [
            no
            for while_ in ast.walk(laco)
            if isinstance(while_, ast.While)
            for no in ast.walk(while_)
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
        ]
        atributos = {no.func.attr for no in dentro_do_while}

        assert "capturar" in atributos
        assert "capturar_completo" not in atributos, (
            "o corpo do tique NAO pode usar `capturar_completo`: ele devolve "
            "pixels sem `SaudeDoFrame`, e a cegueira do `03-02` morre ali"
        )


class TestOPortaoDaTelaQueROLA:
    """C-1 e CTX-1: zero `print`, zero `\\r`, zero `rich`."""

    @pytest.mark.parametrize("fonte", [FONTE_DO_LACO, FONTE_DO_CONSOLE])
    def test_rich_nao_entra_nem_por_import_nem_por_from(self, fonte) -> None:
        assert "rich" not in _importados(fonte), (
            "`rich` NAO esta instalado nesta arvore, tem zero importacoes em "
            "`l2scanner/` e nao entra nesta fase (CTX-1)"
        )

    @pytest.mark.parametrize("fonte", [FONTE_DO_LACO, FONTE_DO_CONSOLE])
    def test_nenhum_print_e_nenhum_end_ou_flush(self, fonte) -> None:
        arvore = ast.parse(fonte.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Name):
                assert no.func.id != "print", (
                    "quem imprime e o laco, com `log.info` — assim a mesma "
                    "string vai para o console E para o `scanner.log`"
                )
            if isinstance(no, ast.keyword):
                assert no.arg not in {"end", "flush"}

    @pytest.mark.parametrize("fonte", [FONTE_DO_LACO, FONTE_DO_CONSOLE])
    def test_nenhuma_string_carrega_retorno_de_carro(self, fonte) -> None:
        """Um `\\r` seria repintura, e a tela desta casa ROLA."""
        arvore = ast.parse(fonte.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Constant) and isinstance(no.value, str):
                assert "\r" not in no.value

    def test_CONTROLE_POSITIVO_um_modulo_com_rich_e_print_e_ACUSADO(
        self, tmp_path
    ) -> None:
        falso = tmp_path / "falso.py"
        falso.write_text(
            "from rich.live import Live\n"
            "def x():\n"
            "    print('ola', end='\\r', flush=True)\n",
            encoding="utf-8",
        )

        assert "rich" in _importados(falso)
        arvore = ast.parse(falso.read_text(encoding="utf-8"))
        chamados = {
            no.func.id
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Name)
        }
        assert "print" in chamados
        assert any(
            isinstance(no, ast.keyword) and no.arg in {"end", "flush"}
            for no in ast.walk(arvore)
        )


class TestOPortaoDoRelogio:
    def test_o_laco_NAO_le_o_relogio_da_maquina_por_conta_propria(self) -> None:
        """O carimbo vem de `relogio.agora_epoch()`, injetavel por parametro.

        Um `datetime.now()` aqui tornaria o `relogio-andou-para-tras` inatingivel
        em teste e faria a taxa depender da maquina que roda a suite.
        """
        chamados = _nomes_chamados(FONTE_DO_LACO)

        assert "now" not in chamados
        assert "agora_epoch" in chamados


# ---------------------------------------------------------------------------
# A PRECEDENCIA DO PACK: a linha de comando vence o arquivo, e DIZ que venceu
# ---------------------------------------------------------------------------
#
# O molde e a regra que `ler_receitas` ja aplica ao `config.local.toml`: quando
# duas fontes discordam, uma vence E O AVISO NOMEIA O VENCEDOR. Uma precedencia
# silenciosa e a pior das tres saidas — pior que recusar e pior que ignorar a
# flag —, porque o usuario ve um numero que ele nao pediu e nao tem por onde
# comecar a procurar.


class TestOPackDaLinhaDeComandoVenceOArquivo:
    def test_SEM_a_flag_o_valor_e_o_do_ARQUIVO_e_nada_e_logado(
        self, cal, tmp_path, caplog
    ) -> None:
        do_arquivo = AjustesDaRenda(tamanho_do_pack_de_adena=7_000_000)

        with caplog.at_level(logging.INFO):
            usado = _com_o_pack_da_linha_de_comando(
                do_arquivo, argumentos()
            )

        assert usado == do_arquivo, (
            "sem a flag nada se substitui, e o objeto sai IGUAL — nem um campo "
            "vizinho pode mudar de carona"
        )
        assert "pack" not in caplog.text.lower(), (
            "sem discordancia nao ha vencedor a anunciar, e uma linha por "
            f"sessao que nao diz nada vira ruido. Saiu: {caplog.text}"
        )

    def test_COM_a_flag_o_valor_e_o_DELA_e_o_aviso_NOMEIA_os_dois_numeros(
        self, cal, tmp_path, caplog
    ) -> None:
        do_arquivo = AjustesDaRenda(tamanho_do_pack_de_adena=7_000_000)

        with caplog.at_level(logging.INFO):
            usado = _com_o_pack_da_linha_de_comando(
                do_arquivo, argumentos(pack_de_adena=3_000_000)
            )

        assert usado.tamanho_do_pack_de_adena == 3_000_000
        assert usado.janela_movel_minutos == do_arquivo.janela_movel_minutos, (
            "so o pack muda: `replace` de um campo nao pode arrastar os outros"
        )
        assert "3000000" in caplog.text.replace(".", "").replace(",", "")
        assert "7000000" in caplog.text.replace(".", "").replace(",", ""), (
            "o aviso mostra os DOIS numeros. So o vencedor faria o usuario "
            f"conferir o config.toml a mao para saber o que ele perdeu. Saiu: "
            f"{caplog.text}"
        )

    def test_a_flag_com_o_MESMO_valor_do_arquivo_nao_anuncia_nada(
        self, cal, tmp_path, caplog
    ) -> None:
        """Nao ha vencedor onde nao ha disputa."""
        do_arquivo = AjustesDaRenda(tamanho_do_pack_de_adena=5_000_000)

        with caplog.at_level(logging.INFO):
            usado = _com_o_pack_da_linha_de_comando(
                do_arquivo, argumentos(pack_de_adena=5_000_000)
            )

        assert usado.tamanho_do_pack_de_adena == 5_000_000
        assert caplog.text == ""

    @pytest.mark.parametrize("valor", [0, -5_000_000])
    def test_um_pack_ZERO_ou_NEGATIVO_na_linha_de_comando_e_RECUSADO(
        self, cal, tmp_path, valor
    ) -> None:
        """A linha de comando nao pode ser mais frouxa que o arquivo.

        `[renda] tamanho_do_pack_de_adena = 0` derruba o arranque com a chave
        nomeada; a mesma coisa escrita na flag tem de derrubar igual, senao a
        flag vira o buraco por onde o valor invalido entra.
        """
        with pytest.raises(AgendaInvalida) as erro:
            _com_o_pack_da_linha_de_comando(
                AjustesDaRenda(), argumentos(pack_de_adena=valor)
            )

        assert "--pack-de-adena" in str(erro.value)

    def test_um_Namespace_SEM_o_campo_nao_derruba_o_laco(
        self, cal, tmp_path
    ) -> None:
        """`getattr` com default, e nao acesso direto.

        Os `argparse.Namespace` montados nos testes deste arquivo e nos de
        `test_renda_cegueira.py` nao tem `pack_de_adena` — eles nascem de
        `argumentos()`, que so poe o que o teste precisa. Um acesso direto
        derrubaria o laco com `AttributeError` num caminho que nao tem nada a
        ver com pack.
        """
        padroes = AjustesDaRenda()

        assert (
            _com_o_pack_da_linha_de_comando(padroes, argparse.Namespace())
            == padroes
        )
