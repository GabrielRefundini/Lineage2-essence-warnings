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
import inspect
import logging
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from l2scanner.__main__ import montar_catalogo_de_mercado
from l2scanner.agenda import AgendaInvalida
from l2scanner.calibracao import Calibracao
from l2scanner.frames import Frame, SaudeDoFrame
from l2scanner.mercado_analise import (
    ABAIXO_DA_MEDIANA,
    ACIMA_DA_MEDIANA,
    N_MINIMO_PARA_MEDIANA,
    SEM_DESTAQUE,
    ModeloDeMercado,
)
from l2scanner.mercado_catalogo import ARQUIVO_DO_CATALOGO
from l2scanner.mercado_leitura import (
    MOTIVO_DA_GRAMATICA,
    MOTIVO_DA_OCLUSAO,
    LinhaLida,
)
from l2scanner.mercado_modo import Contagem, laco_do_mercado
from l2scanner.mercado_pagina import pecas_de_calibracao_de_mercado_faltando
from l2scanner.mercado_registro import (
    ARQUIVO_DE_OBSERVACOES,
    ObservacaoLida,
    RegistroDeObservacoes,
)
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
            layout_recusado=False,
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
            LeitorFalso(paginas_lidas=0, paginas_perdidas=3),
            Contagem(),
            None,
            layout_recusado=False,
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


def linhas_ao_vivo_emitidas(caplog) -> list[str]:
    """As linhas ao vivo REALMENTE emitidas pelo laco, e nao o texto da funcao.

    A diferenca e o defeito inteiro: `linha_ao_vivo` sempre soube montar as
    duas metades, e havia teste sobre o texto que ela DEVOLVE. O que nao havia
    era teste sobre a CADENCIA em que o laco a chama - e era ali que a metade
    perdida sumia.

    O casamento e pelo prefixo que a propria funcao escreve. Um `in` solto
    ("perdidas" em qualquer lugar) casaria tambem no RESUMO DA SESSAO, que sai
    no `finally` de toda execucao: o teste ficaria verde com zero linha ao vivo,
    que e exatamente o estado que ele existe para reprovar.
    """
    return [
        r.getMessage()
        for r in caplog.records
        if r.getMessage().startswith("mercado | ")
    ]


class TestACadenciaDaLinhaAoVivo:
    """LEIT-04: a linha repinta por TICK COM O PAINEL ABERTO, nao por pagina.

    A decisao travada no `04-CONTEXT.md` e "mostra ao vivo: paginas lidas E
    perdidas" e "o resumo conta AS DUAS METADES - nunca so a metade boa". Emitir
    a linha so quando uma pagina e ACEITA calava o console exatamente no momento
    em que a metade perdida cresce, que e o oposto do requisito: no censo foram
    151 lidas contra 189 PERDIDAS.
    """

    def test_painel_ABERTO_com_pagina_PERDIDA_ainda_repinta_a_linha(
        self, cal, leituras, tmp_path, caplog
    ) -> None:
        """UM frame de pagina cheia: painel ABERTO, e pagina nenhuma aceita.

        O acordo entre dois frames que o LEIT-03 exige nao acontece com um
        frame so, entao este tick e literalmente "painel aberto, pagina
        perdida" - o caso medido na verificacao da Fase 4, onde saiam ZERO
        linhas ao vivo.
        """
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
                ticks_maximos=1,
            )

        # O TICK TEM DE TER SIDO DE PAINEL ABERTO E PAGINA PERDIDA, e isso e
        # afirmado e nao suposto: se um dia a fixtura passar a ser aceita como
        # pagina, o teste abaixo ficaria verde pelo caminho ERRADO - o antigo,
        # o de emitir por pagina aceita.
        assert "o painel do mercado ABRIU" in caplog.text, (
            "a fixtura parou de abrir o painel: este teste nao esta mais no "
            "caso que ele existe para cobrir"
        )
        assert "paginas PERDIDAS                 1" in caplog.text, (
            "a fixtura passou a ser ACEITA como pagina: este teste nao esta "
            "mais no caso 'painel aberto, pagina perdida'"
        )

        ao_vivo = linhas_ao_vivo_emitidas(caplog)
        assert ao_vivo, (
            "ZERO linhas ao vivo num tick de painel ABERTO com pagina "
            "PERDIDA. O console fica mudo justamente quando a metade perdida "
            "cresce - LEIT-04 e o 04-CONTEXT exigem as DUAS metades ao vivo."
        )
        assert "perdidas 1" in ao_vivo[-1], ao_vivo[-1]

    def test_painel_FECHADO_nao_repinta_a_linha_ao_vivo(
        self, cal, tmp_path, caplog
    ) -> None:
        """O CONTROLE NEGATIVO do teste acima, e a razao de o portao existir.

        "Por tick" sem portao seriam 3.600 linhas por hora com o painel fechado
        - o estado NORMAL e majoritario de um farm real - e o log rotativo
        perderia a forense que ele existe para guardar. E o mesmo raciocinio do
        latch de `transicao_do_painel`, logo acima.

        Sem este teste, "emitir sempre" passaria no teste de cima e o conserto
        viraria o defeito oposto.
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
        assert linhas_ao_vivo_emitidas(caplog) == []


def cal_que_recusa_o_layout(cal: Calibracao) -> Calibracao:
    """A MESMA calibracao, com o portao de layout impossivel de atravessar.

    O caso de producao e a aba Adena: a ancora e achada, o painel VOTA ABERTO, e
    so entao o casamento do cabecalho reprova e nenhuma linha e lida.
    Reproduzi-lo por cirurgia de pixel exigiria adivinhar quais pixels do
    cabecalho ainda deixam a ancora casar; subir o LIMIAR acima do maximo que um
    casamento normalizado pode devolver produz o mesmo estado por construcao,
    sem tocar em fixtura versionada.

    `deepcopy` E NAO MUTACAO DA FIXTURA: a `cal` e de escopo de MODULO, e mexer
    nela contaminaria todo teste que rodasse depois.
    """
    recusa = copy.deepcopy(cal)
    recusa.mercado_limiar_do_cabecalho = 2.0
    return recusa


class TestALinhaAoVivoNOMEIAOLayoutRecusado:
    """O defeito de producao de 2026-09-01 09:38, escrito como teste.

    O usuario estava na aba Adena. A linha ao vivo saia a cada tick com os
    MESMOS numeros e nada dizia por que - o aviso de layout tem latch, sai UMA
    vez na transicao e rola para fora da tela. O que sobra na tela e numero
    congelado sem explicacao, e ele PARECE defeito: e a mesma classe do "campo
    vazio parece defeito" que a docstring de `linha_ao_vivo` ja resolvia
    escrevendo "(nenhum ainda)".
    """

    def test_com_o_layout_RECUSADO_a_linha_NOMEIA_o_estado(self) -> None:
        from l2scanner.mercado_console import linha_ao_vivo

        texto = linha_ao_vivo(
            LeitorFalso(paginas_lidas=85, paginas_perdidas=2),
            Contagem(),
            "Blessed Scroll of Escape",
            layout_recusado=True,
        )
        # As duas metades continuam la: o estado ACRESCENTA, e nao substitui.
        assert re.search(r"\b85\b", texto)
        assert re.search(r"\b2\b", texto)
        # E o estado esta escrito por extenso, com o que fazer a respeito.
        assert "layout" in texto.lower()
        assert "World Exchange" in texto

    def test_com_o_layout_ACEITO_a_linha_sai_SEM_o_aviso(self) -> None:
        """O controle negativo. Um aviso permanente nao seria informacao.

        Sem este teste, "escrever o aviso sempre" ficaria verde no teste de
        cima e trocaria um defeito de silencio por um de ruido - o usuario
        leria "layout recusado" na linha do tick em que a pagina foi ACEITA.
        """
        from l2scanner.mercado_console import (
            AVISO_DO_LAYOUT_RECUSADO,
            linha_ao_vivo,
        )

        texto = linha_ao_vivo(
            LeitorFalso(paginas_lidas=85, paginas_perdidas=2),
            Contagem(),
            "Blessed Scroll of Escape",
            layout_recusado=False,
        )
        assert AVISO_DO_LAYOUT_RECUSADO not in texto

    def test_o_ESTADO_e_obrigatorio_na_assinatura(self) -> None:
        """Sem valor de fabrica, e isso e o que prende a fiacao.

        Um `layout_recusado=False` de fabrica deixaria o laco esquecer de
        passa-lo e o defeito voltaria inteiro, com a unidade verde. Sem
        default, quem chama TEM de decidir - a mesma disciplina de
        `TravaDoDestaque.anunciar`, que devolve o TEXTO para nao existir
        caminho que anuncie sem passar por ela.
        """
        import inspect as _inspect

        from l2scanner.mercado_console import linha_ao_vivo

        parametro = _inspect.signature(linha_ao_vivo).parameters[
            "layout_recusado"
        ]
        assert parametro.kind is _inspect.Parameter.KEYWORD_ONLY
        assert parametro.default is _inspect.Parameter.empty

    def test_o_laco_NOMEIA_o_estado_na_aba_RECUSADA(
        self, cal, leituras, tmp_path, caplog
    ) -> None:
        """A PROVA DE FIACAO: o laco de producao, na aba recusada.

        A unidade acima ficaria verde mesmo que o laco nunca passasse o estado.
        Este roda `laco_do_mercado` inteiro com o portao de layout reprovando e
        exige que a linha REALMENTE EMITIDA nomeie o estado.
        """
        _duas, _tres, quadros = montar_as_leitoras(
            cal, leituras, [PAGINA_CHEIA, PAGINA_CHEIA]
        )
        with caplog.at_level(logging.INFO):
            laco_do_mercado(
                argumentos(),
                cal_que_recusa_o_layout(cal),
                fonte=FonteFalsa(quadros),
                ler_texto=LeitoraDeRecorte(),
                ler_texto_conferencia=LeitoraDeRecorte(),
                relogio=Relogio(),
                pasta=tmp_path,
                ticks_maximos=2,
            )

        # AS DUAS PRECONDICOES SAO AFIRMADAS, e nao supostas: sem elas o teste
        # poderia ficar verde pelo caminho errado (painel fechado, ou layout
        # aceito), que sao estados com respostas DIFERENTES.
        assert "o painel do mercado ABRIU" in caplog.text, (
            "a fixtura parou de abrir o painel: este teste nao esta mais no "
            "caso 'painel ABERTO com layout RECUSADO'"
        )
        assert "NAO e o layout calibrado" in caplog.text, (
            "o portao de layout parou de reprovar: este teste nao esta mais "
            "no caso que ele existe para cobrir"
        )

        ao_vivo = linhas_ao_vivo_emitidas(caplog)
        assert ao_vivo, "nenhuma linha ao vivo num tick de painel ABERTO"
        for linha in ao_vivo:
            assert "layout" in linha.lower(), (
                "a linha ao vivo saiu com os numeros parados e sem dizer por "
                "que: e o defeito de producao de 2026-09-01 de volta"
            )

    def test_no_laco_com_o_layout_ACEITO_a_linha_sai_LIMPA(
        self, cal, leituras, tmp_path, caplog
    ) -> None:
        """O controle negativo da fiacao, sobre a MESMA fixtura.

        Se o laco passasse `layout_recusado=True` sempre, o teste acima ficaria
        verde e o console gritaria "layout recusado" no tick em que a pagina
        foi lida.
        """
        from l2scanner.mercado_console import AVISO_DO_LAYOUT_RECUSADO

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
                ticks_maximos=2,
            )
        ao_vivo = linhas_ao_vivo_emitidas(caplog)
        assert ao_vivo
        for linha in ao_vivo:
            assert AVISO_DO_LAYOUT_RECUSADO not in linha


# ---------------------------------------------------------------------------
# O MODELO NO LACO: carga UNICA, acrescimo por observacao, destaque ANTES
# ---------------------------------------------------------------------------


UM_MINUTO = timedelta(minutes=1)
COMECO = datetime(2026, 8, 31, 10, 0, 0)


def linha_de_grade(
    chave: str,
    total: int,
    quantidade: int,
    *,
    indice: int = 0,
    nome: str | None = None,
) -> LinhaLida:
    """Uma linha da grade, do jeito que a Fase 2 a entrega ao laco."""
    return LinhaLida(
        indice=indice,
        chave_da_serie=chave,
        nome_exibido=nome if nome is not None else chave,
        total_em_centesimos=total,
        quantidade=quantidade,
        serie_nova=False,
        residuo_do_cruzamento=None,
    )


def observacao_lida(
    chave: str, total: int, quantidade: int, *, quando=None
) -> ObservacaoLida:
    return ObservacaoLida(
        chave_da_serie=chave,
        nome_exibido=chave,
        primeira_vez=quando or COMECO,
        total_em_centesimos=total,
        quantidade=quantidade,
        residuo_do_cruzamento=None,
    )


def escrever_um_csv(pasta: Path, linhas) -> None:
    """Um `observacoes.csv` REAL, escrito pelo unico escritor que existe.

    Escrever o CSV a mao no teste seria um segundo formatador do arquivo, e o
    portao de contrato da Fase 3 existe justamente porque duas escritas
    divergem. Aqui o material de entrada e o que a producao produziria.
    """
    registro = RegistroDeObservacoes(pasta)
    for i, (chave, total, quantidade) in enumerate(linhas):
        registro.registrar(
            linha_de_grade(chave, total, quantidade, indice=i),
            COMECO + i * UM_MINUTO,
        )


@pytest.fixture
def modelos_montados(monkeypatch):
    """Todo `ModeloDeMercado` que o laco montar, na ordem em que montou.

    E o que permite afirmar CARGA UNICA sem acrescentar um parametro de
    producao so para o teste espiar: a lista com UM elemento e literalmente a
    prova de que o modelo nasceu uma vez.
    """
    montados: list[ModeloDeMercado] = []
    original = ModeloDeMercado.de_observacoes.__func__

    def espiao(cls, observacoes):
        modelo = original(cls, observacoes)
        montados.append(modelo)
        return modelo

    monkeypatch.setattr(ModeloDeMercado, "de_observacoes", classmethod(espiao))
    return montados


class TestOModeloCarregaUmaVezESoCresce:
    def test_o_modelo_conhece_o_CSV_PRE_EXISTENTE_antes_do_primeiro_tick(
        self, cal, tmp_path, modelos_montados
    ) -> None:
        """`ticks_maximos=0` e a prova mais forte de "antes do primeiro tick":
        nenhum tick chega a rodar, e o modelo ja sabe o que o arquivo diz."""
        escrever_um_csv(
            tmp_path,
            [("belt", 100, 1), ("belt", 200, 1), ("bota", 50, 1)],
        )

        laco_do_mercado(
            argumentos(),
            cal,
            fonte=FonteFalsa([]),
            ler_texto=LeitoraDeRecorte(),
            ler_texto_conferencia=LeitoraDeRecorte(),
            relogio=Relogio(),
            pasta=tmp_path,
            ticks_maximos=0,
        )

        assert len(modelos_montados) == 1, (
            "o modelo tem de nascer UMA vez, no arranque"
        )
        modelo = modelos_montados[0]
        assert sorted(modelo.series()) == ["belt", "bota"]
        assert modelo.contagem_de("belt") == 2

    def test_o_arquivo_de_observacoes_e_lido_UMA_VEZ_em_varios_ticks(
        self, cal, tmp_path, monkeypatch
    ) -> None:
        """Reler a 1 Hz seria desperdicio sobre milhares de linhas e, pior,
        abriria corrida com o usuario editando o CSV no Sheets."""
        import l2scanner.mercado_registro as registro_mod

        chamadas = []
        original = registro_mod.observacoes_do_arquivo

        def contando(arquivo):
            chamadas.append(arquivo)
            return original(arquivo)

        monkeypatch.setattr(registro_mod, "observacoes_do_arquivo", contando)

        quadros = [
            np.full((400, 400, 3), 20 + i * 7, dtype=np.uint8) for i in range(6)
        ]
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
        assert len(chamadas) == 1, (
            f"o CSV foi lido {len(chamadas)} vezes em seis ticks; o contrato "
            f"do arquivo e 'lido no arranque', e a analise segue o mesmo"
        )

    def test_a_MESMA_linha_duas_vezes_sobe_a_contagem_do_modelo_em_UM(
        self, cal, tmp_path, modelos_montados
    ) -> None:
        """`registrar` devolve `False` para duplicada, e so o `True` acrescenta.

        Acrescentar sem esse portao faria a mesma oferta contar duas vezes no
        `n` -- e o `n` e o que a fase inteira existe para nao mentir.
        """
        laco_do_mercado(
            argumentos(),
            cal,
            fonte=FonteFalsa([]),
            ler_texto=LeitoraDeRecorte(),
            ler_texto_conferencia=LeitoraDeRecorte(),
            relogio=Relogio(),
            pasta=tmp_path,
            ticks_maximos=0,
        )
        modelo = modelos_montados[0]
        registro = RegistroDeObservacoes(tmp_path)
        linha = linha_de_grade("belt", 4500, 100)

        antes = modelo.contagem_de("belt")
        for _ in range(2):
            if registro.registrar(linha, COMECO):
                modelo.acrescentar(
                    observacao_lida("belt", 4500, 100, quando=COMECO)
                )
        assert modelo.contagem_de("belt") - antes == 1


class TestODestaqueEContraAHistoriaDeANTES:
    """ANAL-02: o item nunca se compara consigo mesmo."""

    def test_abaixo_da_mediana_e_DESTAQUE_e_acima_NAO_E(self) -> None:
        modelo = ModeloDeMercado.de_observacoes(
            [
                observacao_lida("belt", 100 + i * 10, 1, quando=COMECO + i * UM_MINUTO)
                for i in range(N_MINIMO_PARA_MEDIANA)
            ]
        )
        # unitarios 100, 110, 120, 130, 140 -> mediana (median_low) = 120
        barata = modelo.veredito_do_destaque(linha_de_grade("belt", 50, 1))
        cara = modelo.veredito_do_destaque(linha_de_grade("belt", 900, 1))

        assert barata.estado == ABAIXO_DA_MEDIANA
        assert cara.estado == ACIMA_DA_MEDIANA
        assert barata.mediana_de_referencia == 120

    def test_a_referencia_e_a_mediana_de_ANTES_e_nao_a_de_DEPOIS(self) -> None:
        """O TESTE CENTRAL DA ORDEM DO TICK.

        Cinco ofertas (o piso exato) de unitarios 100, 110, 120, 130, 140 dao
        `median_low` = 120. Acrescentar uma sexta muito barata (unitario 1) faz
        a mediana de SEIS elementos -- 1, 100, 110, 120, 130, 140 -- cair para
        `median_low` = 110.

        Os dois numeros sao DIFERENTES, e e isso que faz este teste
        discriminar: uma implementacao que gravasse antes de julgar devolveria
        110 como referencia. O teste compara com 120, o valor que a mediana
        tinha ANTES da linha nova.
        """
        historia = [
            observacao_lida("belt", 100 + i * 10, 1, quando=COMECO + i * UM_MINUTO)
            for i in range(N_MINIMO_PARA_MEDIANA)
        ]
        modelo = ModeloDeMercado.de_observacoes(historia)

        nova = linha_de_grade("belt", 1, 1)
        veredito = modelo.veredito_do_destaque(nova)

        depois = ModeloDeMercado.de_observacoes(
            historia + [observacao_lida("belt", 1, 1, quando=COMECO + 9 * UM_MINUTO)]
        )
        mediana_de_depois = depois.veredito_do_destaque(
            linha_de_grade("belt", 1, 1)
        ).mediana_de_referencia

        assert mediana_de_depois == 110, (
            "o cenario nao discrimina: as duas medianas tem de DIFERIR"
        )
        assert veredito.mediana_de_referencia == 120, (
            "o destaque foi calculado contra a mediana que JA CONTEM a linha "
            "nova -- o item esta se comparando consigo mesmo"
        )

    def test_ABAIXO_DO_PISO_o_veredito_e_SEM_DESTAQUE_e_nao_abaixo_nem_acima(
        self,
    ) -> None:
        """Destacar contra uma mediana que nao vale seria pintar de vermelho um
        numero inventado."""
        modelo = ModeloDeMercado.de_observacoes(
            [
                observacao_lida("belt", 100 + i * 10, 1, quando=COMECO + i * UM_MINUTO)
                for i in range(N_MINIMO_PARA_MEDIANA - 1)
            ]
        )
        veredito = modelo.veredito_do_destaque(linha_de_grade("belt", 1, 1))
        assert veredito.estado == SEM_DESTAQUE
        assert veredito.mediana_de_referencia is None
        assert veredito.evidencia.faltam == 1

    def test_serie_DESCONHECIDA_nao_levanta_e_sai_SEM_DESTAQUE(self) -> None:
        modelo = ModeloDeMercado.de_observacoes([])
        assert (
            modelo.veredito_do_destaque(linha_de_grade("nunca-visto", 1, 1)).estado
            == SEM_DESTAQUE
        )

    def test_quantidade_NAO_POSITIVA_na_linha_nova_nao_derruba_o_veredito(
        self,
    ) -> None:
        """A grade e leitura de tela e `quantidade=0` e leitura possivel; um
        `ZeroDivisionError` aqui derrubaria o modo no meio do farm."""
        modelo = ModeloDeMercado.de_observacoes(
            [
                observacao_lida("belt", 100 + i * 10, 1, quando=COMECO + i * UM_MINUTO)
                for i in range(N_MINIMO_PARA_MEDIANA)
            ]
        )
        assert (
            modelo.veredito_do_destaque(linha_de_grade("belt", 100, 0)).estado
            == SEM_DESTAQUE
        )

    def test_a_RAZAO_DA_ORDEM_esta_escrita_no_laco(self) -> None:
        """E o tipo de ordem que um refactor futuro desfaz sem perceber."""
        import l2scanner.mercado_modo as modo

        assert "ANTES" in inspect.getsource(modo)


class TestACadenciaDaSecaoDeAnalise:
    """Ela nao repinta a cada segundo: ela muda quando uma serie ganha
    observacao nova."""

    def test_a_secao_sai_no_ARRANQUE_e_NAO_uma_vez_por_tick(
        self, cal, tmp_path, caplog
    ) -> None:
        escrever_um_csv(tmp_path, [("belt", 100, 1), ("belt", 200, 1)])
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
                watchlist=[],
            )
        secoes = [
            r
            for r in caplog.records
            if "VALE QUANTO AGORA" in r.getMessage()
        ]
        # EXATAMENTE uma em seis ticks: no arranque. Um `>= 1` ficaria verde
        # tambem com seis, que e o defeito - a secao repintando por tick
        # afogaria a linha ao vivo que o LEIT-04 exige.
        assert len(secoes) == 1, [r.getMessage()[:60] for r in secoes]

    def test_a_watchlist_e_LIDA_DO_CONFIG_quando_ninguem_injeta(
        self, cal, tmp_path, monkeypatch
    ) -> None:
        """Producao nao injeta nada: quem le o `config.toml` e o laco."""
        import l2scanner.mercado_modo as modo

        lidas = []

        def falsa():
            lidas.append(True)
            return ["Dragon Belt"]

        monkeypatch.setattr(modo, "ler_watchlist_do_mercado", falsa)
        laco_do_mercado(
            argumentos(),
            cal,
            fonte=FonteFalsa([]),
            ler_texto=LeitoraDeRecorte(),
            ler_texto_conferencia=LeitoraDeRecorte(),
            relogio=Relogio(),
            pasta=tmp_path,
            ticks_maximos=0,
        )
        assert len(lidas) == 1

    def test_config_toml_QUEBRADO_nao_derruba_a_COLETA(
        self, cal, tmp_path, monkeypatch, caplog
    ) -> None:
        """A watchlist e um FILTRO DE DESTAQUE, e nao o produto. Recusar a
        subir por causa dela desligaria a coleta por causa da vista.

        NAO ESTAVA NO PLANO: `ler_watchlist_do_mercado` LEVANTA de proposito
        para TOML quebrado (T-04-11), e um `raise` escapando aqui mataria o
        modo `--mercado` inteiro por uma virgula no `config.toml`.
        """
        import l2scanner.mercado_modo as modo

        def explodindo():
            raise AgendaInvalida("config.toml nao e um TOML valido")

        monkeypatch.setattr(modo, "ler_watchlist_do_mercado", explodindo)
        with caplog.at_level(logging.INFO):
            codigo = laco_do_mercado(
                argumentos(),
                cal,
                fonte=FonteFalsa([]),
                ler_texto=LeitoraDeRecorte(),
                ler_texto_conferencia=LeitoraDeRecorte(),
                relogio=Relogio(),
                pasta=tmp_path,
                ticks_maximos=0,
            )
        assert codigo == 0, "a coleta tem de continuar de pe"
        assert "COLETA CONTINUA" in caplog.text, (
            "as duas mensagens da casa: o que quebrou, e o que continua "
            "funcionando"
        )


class TestAMedianaNaoSeMoveDebaixoDaPagina:
    """O segundo defeito de producao de 2026-09-02, escrito como teste.

    QUATRO ofertas de Adena anunciadas NO MESMO SEGUNDO citaram medianas
    DIFERENTES — `11,00 contra 13,87 n=7`, `11,20 contra 13,00 n=8`,
    `11,40 contra 13,00 n=9`, `11,70 contra 12,00 n=10`. Cada linha entrava na
    populacao antes de a seguinte ser comparada, entao a MESMA oferta era
    noticia forte na primeira fatia da grade e quase nada na ultima.

    ISTO NAO E A TRAVA DO DESTAQUE FALHANDO. `TravaDoDestaque` fez o trabalho
    dela: sao quatro ofertas DISTINTAS, e cada uma tinha direito ao seu anuncio.
    O que estava errado era a REFERENCIA se mexendo por dentro da pagina.
    """

    # Sete observacoes (acima do piso da mediana, que e cinco) de unitarios
    # 100..160 -> `median_low` de sete = 130. As quatro linhas da pagina ficam
    # todas ABAIXO disso e com unitarios DISTINTOS entre si, que e o que faz os
    # quatro anuncios serem quatro textos diferentes e comparaveis um a um.
    _SEMENTE = tuple(range(100, 170, 10))
    _DA_PAGINA = (50, 60, 70, 80)

    def _modelo_semeado(self):
        return ModeloDeMercado.de_observacoes(
            [
                observacao_lida(
                    "belt", unitario, 1, quando=COMECO + i * UM_MINUTO
                )
                for i, unitario in enumerate(self._SEMENTE)
            ]
        )

    def _linhas(self, ordem):
        """As MESMAS quatro linhas, montadas na ordem pedida.

        `indice` acompanha a posicao na GRADE, que e a variavel independente
        deste teste: e exatamente "onde a linha calhou de estar" que o defeito
        fazia importar.
        """
        return [
            linha_de_grade("belt", unitario, 1, indice=i)
            for i, unitario in enumerate(ordem)
        ]

    def _rodar(self, tmp_path, ordem, *, sufixo: str):
        from l2scanner.mercado_console import TravaDoDestaque
        from l2scanner.mercado_modo import processar_a_pagina_aceita

        pasta = tmp_path / sufixo
        modelo = self._modelo_semeado()
        anuncios, ultimo = processar_a_pagina_aceita(
            self._linhas(ordem),
            modelo=modelo,
            catalogo=montar_catalogo_de_mercado(pasta),
            registro=RegistroDeObservacoes(pasta),
            trava_do_destaque=TravaDoDestaque(),
            contagem=Contagem(),
            agora=COMECO + 9 * UM_MINUTO,
        )
        return modelo, anuncios, ultimo

    def test_a_MESMA_pagina_em_DUAS_ORDENS_anuncia_os_MESMOS_textos(
        self, tmp_path
    ) -> None:
        """O CRITERIO CENTRAL: o veredito nao pode depender da posicao na grade.

        Compara TEXTO e nao campo, e de proposito: e o texto que o usuario copia
        para o WhatsApp, e e nele que a mediana e o `n` aparecem. Um teste sobre
        `destaque.mediana_de_referencia` mediria a mesma coisa por dentro e
        deixaria passar um formatador que escolhesse outro numero na hora de
        escrever.
        """
        _m1, direta, _u1 = self._rodar(tmp_path, (50, 60, 70, 80), sufixo="ida")
        _m2, inversa, _u2 = self._rodar(
            tmp_path, (80, 70, 60, 50), sufixo="volta"
        )

        assert len(direta) == 4, direta
        assert len(inversa) == 4, inversa
        # CASADOS LINHA A LINHA pelo unitario da oferta, e nao comparando as
        # duas listas na ordem em que sairam: a ordem de SAIDA acompanha a
        # ordem de ENTRADA de proposito (o log conta a pagina de cima para
        # baixo). O que nao pode mudar e o TEXTO de cada oferta.
        por_oferta_ida = {
            unitario: texto
            for unitario, texto in zip((50, 60, 70, 80), direta)
        }
        por_oferta_volta = {
            unitario: texto
            for unitario, texto in zip((80, 70, 60, 50), inversa)
        }
        assert por_oferta_ida == por_oferta_volta, (
            "o anuncio de uma oferta mudou porque ela estava em outra posicao "
            "da grade — a referencia se moveu por dentro da pagina"
        )

    def test_os_QUATRO_anuncios_citam_a_MESMA_mediana_e_o_MESMO_n(
        self, tmp_path
    ) -> None:
        """O desmentido direto da sequencia `n=7 -> 8 -> 9 -> 10` de producao.

        Sete observacoes semeadas: os quatro anuncios tem de dizer `n=7` e a
        mediana dessas sete (130), e nao uma escada.
        """
        _modelo, anuncios, _ultimo = self._rodar(
            tmp_path, (50, 60, 70, 80), sufixo="ns"
        )
        assert len(anuncios) == 4
        enes = {
            n for texto in anuncios for n in re.findall(r"n=(\d+)", texto)
        }
        assert enes == {"7"}, enes
        medianas = {
            m
            for texto in anuncios
            for m in re.findall(r"contra mediana de ([\d.,]+)", texto)
        }
        assert len(medianas) == 1, medianas

    def test_o_teste_DISCRIMINA_e_nao_passa_por_vacuidade(
        self, tmp_path
    ) -> None:
        """A mediana DEPOIS da pagina tem de DIFERIR da de antes.

        Se as quatro ofertas nao movessem a populacao, os dois testes acima
        passariam sobre nada — qualquer implementacao, congelada ou nao,
        devolveria a mesma referencia quatro vezes. Mesma tecnica de
        `test_a_referencia_e_a_mediana_de_ANTES_e_nao_a_de_DEPOIS`.
        """
        antes = self._modelo_semeado().veredito_do_destaque(
            linha_de_grade("belt", 50, 1)
        )
        modelo, _anuncios, _ultimo = self._rodar(
            tmp_path, (50, 60, 70, 80), sufixo="discrimina"
        )
        depois = modelo.veredito_do_destaque(linha_de_grade("belt", 50, 1))

        assert antes.mediana_de_referencia == 130
        assert depois.mediana_de_referencia != antes.mediana_de_referencia, (
            "o cenario nao discrimina: as quatro ofertas tem de MOVER a "
            "populacao, senao o congelamento nao muda nada e os outros dois "
            "testes passam sobre nada"
        )
        assert depois.evidencia.n == 11, depois.evidencia.n

    def test_a_RAZAO_esta_escrita_na_docstring_de_vereditos_da_pagina(
        self,
    ) -> None:
        """O custo aceito E o que foi recusado. Um dos dois seria meia decisao.

        Sem o custo escrito, o proximo a ler acha que a mudanca foi de graca.
        Sem a recusa escrita, ele nao sabe o que estava errado e desfaz.
        """
        texto = inspect.getdoc(ModeloDeMercado.vereditos_da_pagina)
        assert "congelada" in texto
        assert "grade" in texto
