"""O modo `--mercado` de ponta a ponta, sobre fixturas VERSIONADAS.

POR QUE ESTE ARQUIVO PODE AFIRMAR A FASE INTEIRA SEM O JOGO ABERTO
==================================================================
Ele nao toca `recordings/`, nao precisa das bindings WinRT e nao le o
`calibration.json` da maquina: um clone limpo o roda verde. O material e o
mesmo de `tests/test_mercado_replay.py` - janelas inteiras copiadas BIT a BIT de
frames do censo, mais as 3.511 leituras REAIS do Windows OCR gravadas em
`leituras_de_nome.json`. As leitoras injetadas nao inventam nome: elas devolvem
exatamente o que o motor de verdade devolveu naquele recorte.

O TESTE PONTA A PONTA E O TERCEIRO FIO
=======================================
A Fase 2 escreve o catalogo de NOMES; a Fase 3 escreve o CSV de OBSERVACOES.
Ate agora nenhum processo de producao escrevia os dois na MESMA sessao - a
ferramenta do censo so escreve o CSV, e o replay da Fase 2 so escreve o
catalogo. `test_uma_sessao_grava_nos_DOIS_arquivos` e a primeira prova de que os
dois fios estao ligados ao mesmo laco, e e por isso que ele afirma as duas
metades numa execucao so.

NADA AQUI ESCREVE NA `.mercado/` DO USUARIO. Todo teste que persiste passa
`pasta=tmp_path`, pelo parametro nomeado que a linha de comando nao alcanca.
"""

from __future__ import annotations

import argparse
import copy
import logging
from pathlib import Path

import pytest

from l2scanner.__main__ import montar_catalogo_de_mercado
from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.mercado_catalogo import ARQUIVO_DO_CATALOGO
from l2scanner.mercado_modo import laco_do_mercado
from l2scanner.mercado_pagina import pecas_de_calibracao_de_mercado_faltando
from l2scanner.mercado_registro import ARQUIVO_DE_OBSERVACOES
from l2scanner.relogio import Relogio
from tests.test_mercado_replay import (
    CALIBRACAO,
    FIXTURES,
    PAGINA_CHEIA,
    PAGINA_CHEIA_VIZINHA,
    PROVENIENCIA,
    LeitoraDeRecorte,
    alimentar,
    ler_fixtura,
)

# As quinze pecas que `pecas_de_calibracao_de_mercado_faltando` exige. A lista
# esta AQUI, escrita a mao, de proposito: le-la do proprio modulo faria o teste
# concordar consigo mesmo se alguem apagasse uma chave da producao.
PECAS_DO_MERCADO = (
    "mercado_grade",
    "mercado_sonda_do_fundo",
    "mercado_templates_de_digito",
    "mercado_cabecalho_de_coluna",
    "mercado_limiar_do_cabecalho",
    "mercado_limiar_de_leitura_de_glifo",
    "mercado_margem_de_leitura_de_glifo",
    "mercado_corte_de_similaridade",
    "mercado_piso_de_similaridade",
    "mercado_coluna_do_unitario",
    "mercado_limiar_de_brilho_da_quantidade",
    "mercado_minimo_de_linhas_comparadas",
    "mercado_ancoras",
    "mercado_limiar_da_ancora",
    "mercado_geometria_da_captura",
)


@pytest.fixture(scope="module")
def cal() -> Calibracao:
    return Calibracao.carregar(CALIBRACAO)


@pytest.fixture(scope="module")
def leituras() -> dict:
    """As leituras REAIS do Windows OCR, indexadas como o replay ja faz."""
    import json

    bruto = json.loads(
        (FIXTURES / "leituras_de_nome.json").read_text(encoding="utf-8")
    )
    return {
        (r["gravacao"], r["arquivo"], int(r["linha"])): (r["texto2x"], r["texto3x"])
        for r in bruto
    }


class FonteFalsa:
    """A porta `FrameSource` sobre fixturas de janela inteira.

    Ela devolve os quadros EM SEQUENCIA e depois levanta `StopIteration`, que e
    o mesmo sinal de fim que `ReplaySource` da ao laco principal. Guardar
    `fechada` deixa o teste provar que o `finally` do laco fechou a captura.
    """

    def __init__(self, quadros) -> None:
        self._quadros = list(quadros)
        self._indice = 0
        self.fechada = False

    def capturar(self) -> Frame:
        if self._indice >= len(self._quadros):
            raise StopIteration
        pixels = self._quadros[self._indice]
        self._indice += 1
        return Frame(
            pixels=pixels, indice=self._indice, saude=SaudeDoFrame.OK
        )

    def fechar(self) -> None:
        self.fechada = True


def montar_as_leitoras(cal: Calibracao, leituras: dict, nomes: list[str]):
    """As duas leitoras de OCR REPRODUZIDO, ja ensinadas sobre estes frames."""
    duas, tres = LeitoraDeRecorte(), LeitoraDeRecorte()
    quadros = []
    for nome in nomes:
        frame = ler_fixtura(FIXTURES / nome)
        gravacao, arquivo = PROVENIENCIA[nome]
        alimentar(duas, tres, frame, cal, gravacao, arquivo, leituras)
        quadros.append(frame)
    return duas, tres, quadros


def argumentos(**extras) -> argparse.Namespace:
    base = {"janela": "Lineage II", "intervalo": 0.0}
    base.update(extras)
    return argparse.Namespace(**base)


def linhas_de_dado(caminho: Path) -> list[str]:
    """As linhas do CSV ALEM do cabecalho, sem a quebra final."""
    texto = caminho.read_text(encoding="utf-8")
    return [linha for linha in texto.splitlines()[1:] if linha.strip()]


# ---------------------------------------------------------------------------
# O PONTA A PONTA: os tres fios ligados numa sessao so
# ---------------------------------------------------------------------------


class TestOsTresFiosLigados:
    def test_uma_sessao_grava_nos_DOIS_arquivos(
        self, cal, leituras, tmp_path
    ) -> None:
        """Observacao E serie de nome, na MESMA execucao. E o fio que faltava.

        Duas fixturas: a pagina cheia e a sua VIZINHA. Uma sozinha nunca vira
        pagina aceita (LEIT-03 exige acordo entre dois frames), entao um teste
        de um frame so ficaria verde sobre zero linha gravada.
        """
        duas, tres, quadros = montar_as_leitoras(
            cal, leituras, [PAGINA_CHEIA, PAGINA_CHEIA_VIZINHA]
        )
        fonte = FonteFalsa(quadros)

        codigo = laco_do_mercado(
            argumentos(),
            cal,
            fonte=fonte,
            ler_texto=duas,
            ler_texto_conferencia=tres,
            relogio=Relogio(),
            pasta=tmp_path,
            ticks_maximos=4,
        )

        assert codigo == 0
        assert fonte.fechada, "o `finally` tem de fechar a captura"

        observacoes = tmp_path / ARQUIVO_DE_OBSERVACOES
        catalogo = tmp_path / ARQUIVO_DO_CATALOGO
        assert observacoes.is_file(), "o CSV de observacoes nao nasceu"
        assert catalogo.is_file(), "o catalogo de nomes nao nasceu"

        assert len(linhas_de_dado(observacoes)) >= 1, (
            "o registro de observacoes ficou so com o cabecalho: o fio da "
            "Fase 3 nao esta ligado"
        )
        assert len(linhas_de_dado(catalogo)) >= 1, (
            "o catalogo de nomes ficou so com o cabecalho: o fio da Fase 2 "
            "nao esta ligado. `Catalogo.gravar()` no `finally` e `registrar` "
            "por linha aceita sao os DOIS que precisam existir"
        )

    def test_o_console_mostra_as_duas_metades_e_o_ultimo_item(
        self, cal, leituras, tmp_path, caplog
    ) -> None:
        duas, tres, quadros = montar_as_leitoras(
            cal, leituras, [PAGINA_CHEIA, PAGINA_CHEIA_VIZINHA]
        )
        with caplog.at_level(logging.INFO):
            laco_do_mercado(
                argumentos(),
                cal,
                fonte=FonteFalsa(quadros),
                ler_texto=duas,
                ler_texto_conferencia=tres,
                relogio=Relogio(),
                pasta=tmp_path,
                ticks_maximos=4,
            )
        assert "paginas lidas" in caplog.text
        assert "perdidas" in caplog.text

    def test_a_linha_de_arranque_diz_o_orcamento_e_a_separacao(
        self, cal, leituras, tmp_path, caplog
    ) -> None:
        """Quem le o log precisa saber o custo ANTES de o farm comecar."""
        duas, tres, quadros = montar_as_leitoras(cal, leituras, [PAGINA_CHEIA])
        with caplog.at_level(logging.INFO):
            laco_do_mercado(
                argumentos(),
                cal,
                fonte=FonteFalsa(quadros),
                ler_texto=duas,
                ler_texto_conferencia=tres,
                relogio=Relogio(),
                pasta=tmp_path,
                ticks_maximos=2,
            )
        assert "110 ms" in caplog.text
        assert "TERCEIRO" in caplog.text


# ---------------------------------------------------------------------------
# OS PORTOES DE ARRANQUE: recusar a subir, nunca subir cego
# ---------------------------------------------------------------------------


def sem_as_pecas_de_mercado(cal: Calibracao) -> Calibracao:
    """A mesma calibracao, com TODA peca de mercado apagada."""
    copia = copy.deepcopy(cal)
    for nome in PECAS_DO_MERCADO:
        setattr(copia, nome, None)
    return copia


class TestORecusaDeSubir:
    def test_sem_calibracao_de_mercado_o_modo_devolve_2_e_diz_o_que_falta(
        self, cal, tmp_path, caplog
    ) -> None:
        vazia = sem_as_pecas_de_mercado(cal)
        with caplog.at_level(logging.ERROR):
            codigo = laco_do_mercado(
                argumentos(),
                vazia,
                fonte=FonteFalsa([]),
                ler_texto=LeitoraDeRecorte(),
                ler_texto_conferencia=LeitoraDeRecorte(),
                relogio=Relogio(),
                pasta=tmp_path,
                ticks_maximos=1,
            )
        assert codigo == 2
        assert any(nome in caplog.text for nome in PECAS_DO_MERCADO), (
            "a recusa tem de NOMEAR a chave que falta - 'recalibre' sozinho "
            "nao diz o que recalibrar"
        )
        assert "calibrar-mercado" in caplog.text

    def test_sem_calibracao_o_modo_nao_escreve_arquivo_nenhum(
        self, cal, tmp_path
    ) -> None:
        """Recusar a subir e recusar ANTES de tocar o disco."""
        laco_do_mercado(
            argumentos(),
            sem_as_pecas_de_mercado(cal),
            fonte=FonteFalsa([]),
            ler_texto=LeitoraDeRecorte(),
            ler_texto_conferencia=LeitoraDeRecorte(),
            relogio=Relogio(),
            pasta=tmp_path,
            ticks_maximos=1,
        )
        assert list(tmp_path.iterdir()) == []

    def test_layout_de_outra_aba_devolve_2_e_diz_qual_esta_gravado(
        self, cal, tmp_path, caplog
    ) -> None:
        outra = copy.deepcopy(cal)
        grade = dict(outra.mercado_grade)
        grade["layout"] = "adena"
        outra.mercado_grade = grade
        with caplog.at_level(logging.ERROR):
            codigo = laco_do_mercado(
                argumentos(),
                outra,
                fonte=FonteFalsa([]),
                ler_texto=LeitoraDeRecorte(),
                ler_texto_conferencia=LeitoraDeRecorte(),
                relogio=Relogio(),
                pasta=tmp_path,
                ticks_maximos=1,
            )
        assert codigo == 2
        assert "adena" in caplog.text


# ---------------------------------------------------------------------------
# A VERDADE UNICA SOBRE "CALIBRADO PARA MERCADO"
# ---------------------------------------------------------------------------


class TestAsPecasDeCalibracao:
    def test_a_fixtura_completa_nao_tem_peca_faltando(self, cal) -> None:
        assert pecas_de_calibracao_de_mercado_faltando(cal) == []

    def test_uma_calibracao_sem_mercado_lista_TODAS_as_pecas(self, cal) -> None:
        faltando = pecas_de_calibracao_de_mercado_faltando(
            sem_as_pecas_de_mercado(cal)
        )
        assert set(faltando) == set(PECAS_DO_MERCADO)
        assert len(faltando) == len(PECAS_DO_MERCADO)

    @pytest.mark.parametrize("nome", PECAS_DO_MERCADO)
    def test_cada_peca_sozinha_aparece_na_lista(self, cal, nome) -> None:
        copia = copy.deepcopy(cal)
        setattr(copia, nome, None)
        assert pecas_de_calibracao_de_mercado_faltando(copia) == [nome]

    def test_as_TRES_do_arranque_entraram(self, cal) -> None:
        """Ate agora `mercado_ancoras`, `mercado_limiar_da_ancora` e
        `mercado_geometria_da_captura` eram conferidas em tres lugares soltos do
        `__main__.py`, e nunca pelo leitor. Uma lista so, num lugar so."""
        for nome in (
            "mercado_ancoras",
            "mercado_limiar_da_ancora",
            "mercado_geometria_da_captura",
        ):
            copia = copy.deepcopy(cal)
            setattr(copia, nome, None)
            assert nome in pecas_de_calibracao_de_mercado_faltando(copia)

    def test_a_folga_de_cola_continua_FORA(self, cal) -> None:
        """A ausencia dela degrada para MAIS SEGURO (02-08), entao ela nao pode
        desligar a leitura inteira."""
        copia = copy.deepcopy(cal)
        copia.mercado_folga_de_cola_do_glifo = None
        assert pecas_de_calibracao_de_mercado_faltando(copia) == []


# ---------------------------------------------------------------------------
# A MONTAGEM QUE FALHA PARA O LADO CERTO
# ---------------------------------------------------------------------------


class TestMontarCatalogoDeMercado:
    def test_a_pasta_ocupada_por_um_ARQUIVO_devolve_None_e_nao_levanta(
        self, tmp_path, caplog
    ) -> None:
        """O `mkdir` do `Catalogo.__init__` roda FORA de qualquer `try` hoje.

        Medido nesta maquina: ele levanta `FileExistsError` (errno 17, winerror
        183) quando um ARQUIVO ocupa o nome da pasta. Sem esta montagem o
        traceback subiria cru do arranque.
        """
        ocupado = tmp_path / "mercado"
        ocupado.write_text("eu sou um arquivo", encoding="utf-8")

        with caplog.at_level(logging.ERROR):
            assert montar_catalogo_de_mercado(ocupado) is None

        erros = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(erros) == 2, (
            "sao DUAS mensagens: o que quebrou e o que continua funcionando"
        )
        assert "CATALOGO DE NOMES DESLIGADO" in erros[0].getMessage()
        assert "continua igual" in erros[1].getMessage()

    def test_a_pasta_boa_devolve_um_catalogo(self, tmp_path) -> None:
        catalogo = montar_catalogo_de_mercado(tmp_path / "novo")
        assert catalogo is not None
        assert catalogo.arquivo.parent.is_dir()
