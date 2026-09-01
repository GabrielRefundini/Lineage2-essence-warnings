"""Assinatura gravada com outra regiao de nome nao pode falhar em silencio.

O QUE ACONTECEU
---------------
`nome_largura` passou de 100 para 110 e `nome_dx` de 26 para 16, porque o
recorte comecava dentro do nome (ver tests/test_recorte_do_nome.py). Isso torna
obsoleta TODA assinatura ja gravada: no dia da mudanca existiam 4 no
`calibration.json` do usuario e 7 arquivos no acervo `.identidades/`, todas de
largura 100.

Uma assinatura de forma diferente nunca mais vai casar. O usuario ja aprovou
descartar o acervo atual, mas descartar e uma decisao DELE — o que o scanner
nao pode fazer e parar de reconhecer sem dizer nada. Silencio sem sintoma e o
modo de falha que este projeto mais combate: em 2026-08-25 um membro passou duas
horas como "Membro 1", atravessando ate um reinicio, sem uma linha de log
explicando por que.

A DECISAO, e ela esta testada aqui
----------------------------------
As assinaturas fora de forma sao ANUNCIADAS e MANTIDAS, nunca descartadas.
A razao inteira esta na docstring de `Identidades.aviso_de_forma`, e o resumo e:
`assinaturas_configuradas` do Rastreador e `bool(assinaturas)`, e esvaziar a
lista devolveria o scanner ao modo em que a POSICAO e a identidade — trocando
um "Membro 3" honesto por um "Mostarda morreu" com a Mostarda viva na linha de
cima.
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest

from l2scanner.acervo import (
    AcervoDeIdentidades,
    Identidades,
    carregar_identidades,
)
from l2scanner.calibracao import Calibracao
from l2scanner.identidade import (
    LIMIAR_DE_CASAMENTO,
    Assinatura,
    identificar_linhas,
)
from l2scanner.visao import _recorte_do_nome

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).parent / "fixtures" / "identidade"

FORMA_NOVA = (20, 110)
FORMA_ANTIGA = (20, 100)


def assinatura(nome: str, forma: tuple[int, int], semente: int = 0) -> Assinatura:
    """Uma assinatura com texto de verdade na forma pedida.

    Nao e ruido aleatorio puro: a mascara precisa ter mais que
    PIXELS_MINIMOS_DE_TEXTO acesos para valer como nome, e desvio nao nulo para
    a correlacao existir.
    """
    gerador = np.random.default_rng(semente)
    mascara = (gerador.random(forma) > 0.7).astype(np.uint8)
    return Assinatura(nome=nome, mascara=mascara)


class TestAContagem:
    def test_conta_as_que_nao_batem_com_a_regiao_atual(self):
        identidades = Identidades(
            assinaturas=[
                assinatura("Mostarda", FORMA_ANTIGA, 1),
                assinatura("Titander", FORMA_ANTIGA, 2),
                assinatura("Pirulito", FORMA_NOVA, 3),
            ],
            forma_esperada=FORMA_NOVA,
        )

        assert identidades.fora_de_forma == 2

    def test_sem_forma_esperada_nao_ha_nada_fora_de_forma(self):
        """Quem nao disse qual e a regiao atual nao pode acusar ninguem.

        Mantem a chamada de dois argumentos valendo exatamente como antes, que e
        o que a suite inteira ja usa.
        """
        identidades = Identidades(
            assinaturas=[assinatura("Mostarda", FORMA_ANTIGA, 1)]
        )

        assert identidades.fora_de_forma == 0
        assert identidades.aviso_de_forma is None

    def test_altura_diferente_tambem_conta(self):
        """A forma sao as DUAS dimensoes, e nao so a largura.

        `nome_altura` tambem e calibravel. Olhar so a largura deixaria passar
        exatamente a mesma falha silenciosa pela outra dimensao.
        """
        identidades = Identidades(
            assinaturas=[assinatura("Mostarda", (24, 110), 1)],
            forma_esperada=FORMA_NOVA,
        )

        assert identidades.fora_de_forma == 1


class TestOAviso:
    def test_diz_quantas_sao_que_forma_tinham_e_como_sair(self):
        identidades = Identidades(
            assinaturas=[
                assinatura("Mostarda", FORMA_ANTIGA, 1),
                assinatura("Titander", FORMA_ANTIGA, 2),
                assinatura("Pirulito", FORMA_NOVA, 3),
            ],
            forma_esperada=FORMA_NOVA,
        )

        aviso = identidades.aviso_de_forma

        assert aviso is not None
        assert "2" in aviso, f"o numero tem de aparecer: {aviso!r}"
        assert "20x100" in aviso, f"a forma gravada tem de aparecer: {aviso!r}"
        assert "20x110" in aviso, f"a forma atual tem de aparecer: {aviso!r}"
        assert "calibrar.bat" in aviso, f"a saida tem de aparecer: {aviso!r}"

    def test_nomeia_quem_precisa_ser_regravado(self):
        """Quem tem nome aparece, para o usuario saber de quem se trata."""
        identidades = Identidades(
            assinaturas=[
                assinatura("Mostarda", FORMA_ANTIGA, 1),
                assinatura("Titander", FORMA_ANTIGA, 2),
            ],
            forma_esperada=FORMA_NOVA,
        )

        aviso = identidades.aviso_de_forma

        assert "Mostarda" in aviso and "Titander" in aviso

    def test_o_comando_sai_com_reticencias_e_nao_com_a_lista_pronta(self):
        """`--nomes` e POSICIONAL, e esta lista e alfabetica.

        Preencher o comando entregaria uma ordem de party provavelmente errada
        — a posicao se passando por identidade, que e o defeito que a identidade
        visual existe para impedir. Os nomes vao como informacao, depois.
        """
        aviso = Identidades(
            assinaturas=[
                assinatura("Welazkez", FORMA_ANTIGA, 1),
                assinatura("Mostarda", FORMA_ANTIGA, 2),
            ],
            forma_esperada=FORMA_NOVA,
        ).aviso_de_forma

        assert '--nomes "..."' in aviso, f"comando preenchido: {aviso!r}"
        assert '--nomes "Welazkez' not in aviso
        assert '--nomes "Mostarda' not in aviso

    def test_assinatura_anonima_nao_inventa_nome(self):
        """Entrada do acervo antes do batismo nao tem nome, e mentir seria pior."""
        identidades = Identidades(
            assinaturas=[assinatura("", FORMA_ANTIGA, 1)],
            forma_esperada=FORMA_NOVA,
        )

        aviso = identidades.aviso_de_forma

        assert aviso is not None
        assert "1" in aviso
        assert "Afetadas" not in aviso, (
            f"listou nome nenhum como se fosse alguem: {aviso!r}"
        )

    def test_nao_avisa_quando_esta_tudo_na_forma_certa(self):
        identidades = Identidades(
            assinaturas=[assinatura("Mostarda", FORMA_NOVA, 1)],
            forma_esperada=FORMA_NOVA,
        )

        assert identidades.aviso_de_forma is None

    def test_nao_avisa_quando_nao_ha_assinatura_nenhuma(self):
        assert Identidades(forma_esperada=FORMA_NOVA).aviso_de_forma is None

    def test_o_aviso_nao_tem_acento_nem_travessao(self):
        """Texto que o usuario le, entao cp1252 e a regra."""
        aviso = Identidades(
            assinaturas=[assinatura("Mostarda", FORMA_ANTIGA, 1)],
            forma_esperada=FORMA_NOVA,
        ).aviso_de_forma

        assert aviso == aviso.encode("ascii", "ignore").decode("ascii"), (
            f"acento no aviso: {aviso!r}"
        )
        assert "—" not in aviso and "–" not in aviso


class TestElasContinuamNaLista:
    """A decisao: anunciar, nao descartar. Ver a docstring do modulo."""

    def test_a_fusao_nao_descarta_assinatura_fora_de_forma(self, tmp_path):
        calibradas = [assinatura("Mostarda", FORMA_ANTIGA, 1)]

        identidades = carregar_identidades(
            calibradas, AcervoDeIdentidades(tmp_path), forma_esperada=FORMA_NOVA
        )

        assert identidades.assinaturas == calibradas
        assert identidades.configuradas, (
            "esvaziar a lista desliga assinaturas_configuradas e devolve o "
            "scanner ao modo em que a POSICAO e a identidade — trocariamos um "
            "'Membro 3' honesto por um nome errado com cara de certeza"
        )

    def test_a_forma_esperada_chega_no_resultado_da_fusao(self, tmp_path):
        identidades = carregar_identidades(
            [assinatura("Mostarda", FORMA_ANTIGA, 1)],
            AcervoDeIdentidades(tmp_path),
            forma_esperada=FORMA_NOVA,
        )

        assert identidades.fora_de_forma == 1
        assert identidades.aviso_de_forma is not None

    def test_a_chamada_de_dois_argumentos_continua_valendo(self, tmp_path):
        identidades = carregar_identidades(
            [assinatura("Mostarda", FORMA_ANTIGA, 1)],
            AcervoDeIdentidades(tmp_path),
        )

        assert identidades.conhecidas == 1
        assert identidades.aviso_de_forma is None


class TestManterNaoCustaReconhecimento:
    """O outro lado da decisao, medido nos pixels da fixture.

    Manter lixo na lista so e aceitavel se o lixo for INERTE. Uma assinatura de
    largura 100 comparada contra um recorte de largura 110 e avaliada no
    alinhamento calibrado com o conteudo deslocado 10 colunas.
    """

    @pytest.fixture
    def calibracao(self) -> Calibracao:
        return Calibracao.carregar(FIXTURES / "calibracao.json")

    @pytest.fixture
    def pixels(self) -> np.ndarray:
        import cv2

        px = cv2.imread(
            str(FIXTURES / "party_ordem_original.png"), cv2.IMREAD_COLOR
        )
        assert px is not None
        return px

    def test_assinatura_de_forma_antiga_nao_ganha_linha_nenhuma(
        self, pixels, calibracao
    ):
        """Medido: o melhor dos 16 pares deu 0.281, contra um limiar de 0.75."""
        from dataclasses import fields, replace

        from l2scanner.calibracao import LayoutDaParty

        padrao = {
            campo.name: campo.default
            for campo in fields(LayoutDaParty)
            if campo.name.startswith("nome_")
        }
        cal = replace(calibracao, layout=replace(calibracao.layout, **padrao))
        recortes = {i: _recorte_do_nome(pixels, cal, i) for i in range(4)}

        res = identificar_linhas(recortes, calibracao.assinaturas)

        for i in range(4):
            assert res[i].nome is None, (
                f"a linha {i} recebeu {res[i].nome!r} de uma assinatura de "
                f"forma antiga, com confianca {res[i].confianca:.3f}"
            )
            assert res[i].confianca < LIMIAR_DE_CASAMENTO


class TestOArranqueRealmenteAvisa:
    """A costura em `__main__`, lida por AST.

    ESTE TESTE EXISTE POR CICATRIZ. `assinaturas_configuradas` ficou provado na
    suite e DESLIGADO em campo ate 2026-08-31, porque ninguem passava o
    argumento em producao — o default `False` cobria o buraco e nenhum teste
    de comportamento notava. Um aviso de arranque tem exatamente a mesma forma:
    a propriedade pode estar perfeita e nunca ser chamada.

    Lido por AST e nao por `grep` porque as docstrings desta rodada citam
    `aviso_de_forma` e `forma_esperada` de proposito, para explicar a regra; uma
    busca textual acusaria a documentacao que protege o codigo.
    """

    def _laco_principal(self) -> ast.FunctionDef:
        fonte = (RAIZ / "l2scanner" / "__main__.py").read_text(encoding="utf-8")
        return next(
            no
            for no in ast.walk(ast.parse(fonte))
            if isinstance(no, ast.FunctionDef) and no.name == "laco_principal"
        )

    def test_a_carga_diz_qual_e_a_regiao_de_nome_atual(self):
        chamadas = [
            no
            for no in ast.walk(self._laco_principal())
            if isinstance(no, ast.Call)
            and isinstance(no.func, ast.Name)
            and no.func.id == "carregar_identidades"
        ]

        assert chamadas, "producao nao chama carregar_identidades"
        for chamada in chamadas:
            assert any(
                palavra.arg == "forma_esperada" for palavra in chamada.keywords
            ), (
                "sem forma_esperada a carga nao tem como saber que a assinatura "
                "envelheceu, e o aviso nunca sai"
            )

    def test_o_aviso_e_lido_no_arranque(self):
        lidos = {
            no.attr
            for no in ast.walk(self._laco_principal())
            if isinstance(no, ast.Attribute)
        }

        assert "aviso_de_forma" in lidos, (
            "o aviso existe e ninguem o le — e o mesmo buraco que deixou "
            "assinaturas_configuradas desligado em campo"
        )
