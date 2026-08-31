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
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from l2scanner.__main__ import montar_catalogo_de_mercado
from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.mercado_catalogo import ARQUIVO_DO_CATALOGO
from l2scanner.mercado_leitura import (
    MOTIVO_DA_GRAMATICA,
    MOTIVO_DA_OCLUSAO,
)
from l2scanner.mercado_modo import Contagem, laco_do_mercado
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


def cal_de_fixtura() -> Calibracao:
    """A calibracao versionada, como FUNCAO e nao so como fixtura.

    `tests/test_mercado_firewall_de_fase.py` precisa dela dentro de um teste que
    ja recebe `monkeypatch` e `tmp_path`, e uma fixtura de outro modulo nao se
    importa - se importa a funcao que ela chama.
    """
    return Calibracao.carregar(CALIBRACAO)


@pytest.fixture(scope="module")
def cal() -> Calibracao:
    return cal_de_fixtura()


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


# ---------------------------------------------------------------------------
# LEIT-04: o console ao vivo e o resumo das duas metades
# ---------------------------------------------------------------------------

# Numeros PRIMOS e distintos, de proposito: com 7 e 17 na mesma tela, um
# `str(valor) in texto` ingenuo aprovaria "7" por causa do "17". As afirmacoes
# abaixo usam fronteira de palavra justamente por isso.
CONTADORES_FALSOS = {
    "paginas_lidas": 7,
    "paginas_perdidas": 3,
    "paginas_vazias": 11,
    "paginas_de_outro_layout": 13,
    "ticks_com_painel_aberto": 17,
    "frames_congelados": 19,
    "linhas_descartadas": 23,
}


class LeitorFalso:
    """Os SETE contadores publicos do `LeitorDePagina`, e nada mais.

    O console recebe o leitor e nao sabe se ele leu pixel nenhum - e essa e a
    razao de as funcoes de desenho DEVOLVEREM texto: elas ficam afirmaveis sem
    fixtura, sem OCR e sem capturar stdout.
    """

    def __init__(self, **contadores) -> None:
        valores = dict(CONTADORES_FALSOS)
        valores.update(contadores)
        for nome, valor in valores.items():
            setattr(self, nome, valor)
        self.ultimo_motivo_de_perda = None
        self.ultima_leitura = None


def _orcamento_de_exemplo():
    from l2scanner.mercado_console import OrcamentoDoTick

    orcamento = OrcamentoDoTick(limite=1.0)
    for segundos in (0.10, 0.11, 0.12, 0.13, 1.40):
        orcamento.registrar(segundos)
    return orcamento


class TestALinhaAoVivo:
    def test_ela_tem_docstring(self) -> None:
        from l2scanner.mercado_console import linha_ao_vivo

        assert linha_ao_vivo.__doc__

    def test_mostra_as_duas_metades_e_o_ultimo_item(self) -> None:
        from l2scanner.mercado_console import linha_ao_vivo

        texto = linha_ao_vivo(
            LeitorFalso(paginas_lidas=7, paginas_perdidas=3),
            Contagem(),
            "Blessed Scroll of Escape",
        )
        assert re.search(r"\b7\b", texto)
        assert re.search(r"\b3\b", texto)
        assert "Blessed Scroll of Escape" in texto

    def test_com_zero_lidas_a_metade_PERDIDA_continua_visivel(self) -> None:
        """Nunca so a metade boa: o censo mediu 151 lidas contra 189 perdidas.

        Esconder a segunda faria o usuario confiar numa cobertura que nao
        existe - que e exatamente o defeito que LEIT-04 existe para impedir.
        """
        from l2scanner.mercado_console import linha_ao_vivo

        texto = linha_ao_vivo(
            LeitorFalso(paginas_lidas=0, paginas_perdidas=3), Contagem(), None
        )
        assert re.search(r"\b0\b", texto)
        assert re.search(r"\b3\b", texto)

    def test_ela_NAO_mostra_o_residuo_do_cruzamento(self) -> None:
        """A guarda de cruzamento esta DESLIGADA por medicao (02-02).

        O residuo e observacao, nao veredito, e ele ja esta no CSV para o
        usuario olhar no Sheets. No repintar de 1 Hz ele so competiria por
        atencao com os dois numeros que julgam a sessao.

        A AFIRMACAO E SOBRE O CODIGO, e nao sobre o fonte cru: a docstring da
        funcao EXPLICA a ausencia, e a doutrina da casa e que um numero que caiu
        precisa dizer que caiu. Um teste sobre o fonte cru proibiria a
        explicacao, que e o oposto do que ele quer.
        """
        import ast as _ast
        import inspect as _inspect

        from l2scanner.mercado_console import linha_ao_vivo

        arvore = _ast.parse(_inspect.getsource(linha_ao_vivo).lstrip())
        funcao = arvore.body[0]
        funcao.body = funcao.body[1:]  # fora a docstring
        assert "residuo" not in _ast.unparse(funcao)


class TestOResumoDaSessao:
    def test_os_SETE_contadores_aparecem_com_o_seu_valor(self) -> None:
        from l2scanner.mercado_console import resumo_da_sessao

        texto = resumo_da_sessao(
            LeitorFalso(), Contagem(), Counter(), _orcamento_de_exemplo()
        )
        for nome, valor in CONTADORES_FALSOS.items():
            assert re.search(rf"\b{valor}\b", texto), (nome, valor)

    def test_as_tres_contagens_de_escrita_nao_se_somam(self) -> None:
        """`observacoes`, `duplicadas` e `perdidas` sao fatos DIFERENTES."""
        from l2scanner.mercado_console import resumo_da_sessao

        texto = resumo_da_sessao(
            LeitorFalso(),
            Contagem(observacoes=41, duplicadas=43, perdidas=47),
            Counter(),
            _orcamento_de_exemplo(),
        )
        for valor in (41, 43, 47):
            assert re.search(rf"\b{valor}\b", texto)

    def test_os_motivos_somam_por_SESSAO_e_nao_por_pagina(self) -> None:
        """Dois ticks com o MESMO motivo produzem contagem 2.

        O campo `motivos` da pagina carrega so a ultima leitura, nao um
        acumulado - somar o acumulado e trabalho do laco, e e isso que este
        teste prende.
        """
        from l2scanner.mercado_console import acumular_motivos, resumo_da_sessao

        acumulados = Counter()
        for _ in range(2):
            acumular_motivos(acumulados, LeituraFalsa((MOTIVO_DA_OCLUSAO,)))

        texto = resumo_da_sessao(
            LeitorFalso(), Contagem(), acumulados, _orcamento_de_exemplo()
        )
        assert MOTIVO_DA_OCLUSAO in texto
        linha = [l for l in texto.splitlines() if MOTIVO_DA_OCLUSAO in l]
        assert linha and re.search(r"\b2\b", linha[0]), texto

    def test_o_motivo_usa_a_CONSTANTE_e_nao_a_palavra_do_CONTEXT(self) -> None:
        """O CONTEXT chama uma delas de "gramatica"; a constante vale `numero`."""
        from l2scanner.mercado_console import acumular_motivos, resumo_da_sessao

        acumulados = Counter()
        acumular_motivos(acumulados, LeituraFalsa((MOTIVO_DA_GRAMATICA,)))
        texto = resumo_da_sessao(
            LeitorFalso(), Contagem(), acumulados, _orcamento_de_exemplo()
        )
        assert MOTIVO_DA_GRAMATICA in texto
        assert "gramatica" not in texto

    def test_o_orcamento_traz_p50_p95_maximo_e_estouros(self) -> None:
        from l2scanner.mercado_console import resumo_da_sessao

        texto = resumo_da_sessao(
            LeitorFalso(), Contagem(), Counter(), _orcamento_de_exemplo()
        ).lower()
        assert "p50" in texto
        assert "p95" in texto
        assert "maximo" in texto
        assert "estouraram" in texto

    def test_o_resumo_diz_que_contencao_e_do_SISTEMA(self) -> None:
        """Os numeros dizem o que ESTE processo custou, e so isso."""
        from l2scanner.mercado_console import resumo_da_sessao

        texto = resumo_da_sessao(
            LeitorFalso(), Contagem(), Counter(), _orcamento_de_exemplo()
        )
        assert "sistema" in texto.lower()


class LeituraFalsa:
    """So o campo que o acumulador de motivos le."""

    def __init__(self, motivos) -> None:
        self.motivos = tuple(motivos)


class TestOAntiSpamDoPainelFechado:
    def test_painel_fechado_por_varios_ticks_da_UMA_linha_de_transicao(
        self, cal, tmp_path, caplog
    ) -> None:
        """Painel fechado e o estado NORMAL e majoritario de um farm real.

        Uma linha por tick seriam 3.600 linhas por hora - e o log rotativo
        perderia a forense que ele existe para guardar.
        """
        quadros = [
            np.full((400, 400, 3), 20 + i * 7, dtype=np.uint8) for i in range(6)
        ]
        with caplog.at_level(logging.INFO):
            laco_do_mercado(
                argumentos(),
                cal,
                fonte=FonteFalsa(quadros),
                ler_texto=LeitoraDeRecorte(),
                ler_texto_conferencia=LeitoraDeRecorte(),
                relogio=Relogio(),
                pasta=tmp_path,
                ticks_maximos=6,
            )
        transicoes = [
            r for r in caplog.records if "painel do mercado" in r.getMessage()
        ]
        # EXATAMENTE uma, e nao "no maximo uma": seis ticks fechados sao UMA
        # transicao (o estado inicial, que o usuario precisa ver para saber que
        # o modo esta vivo e nao esta achando nada). Um `<= 1` ficaria verde
        # tambem com ZERO, que e o modo de falha oposto - silencio
        # indistinguivel de travamento.
        assert len(transicoes) == 1, [r.getMessage() for r in transicoes]
