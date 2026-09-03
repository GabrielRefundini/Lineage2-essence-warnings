"""As DUAS garantias da semeadura, presas por teste — e por isso elas moram aqui.

O QUE ESTE ARQUIVO EXISTE PARA RESOLVER, E VALE ESTAR ESCRITO
==============================================================
A versao anterior desta tarefa punha a decisao inteira dentro da ferramenta de
bancada e, no mesmo conjunto de criterios, exigia (a) que nenhum teste nomeasse
a ferramenta e (b) que houvesse teste rodando-a para afirmar que ela nao apaga
chave alheia e nao sobrescreve calada. **As duas coisas nao podem ser verdade
juntas:** `import`, `runpy` ou `subprocess` — qualquer forma de rodar a
ferramenta poe o nome dela no arquivo de teste. Do jeito que estava, "nao apaga
outra chave" e "nao sobrescreve calada" viviam em codigo que nenhum teste
tocava, que e o oposto do que aqueles criterios pareciam garantir.

A saida foi mover o COMPORTAMENTO para `l2scanner/renda_semeadura.py` e nao
afrouxar o portao. A ferramenta virou `argparse` e mais nada; a decisao virou
funcao importavel; e as duas garantias ficam presas por teste AO MESMO TEMPO em
que "nenhum teste importa a ferramenta" continua verdadeiro — agora porque nao
ha o que importar de la.

E OS PORTOES DA FERRAMENTA MUDARAM DE FORMA JUNTO. Em vez de negar um TEXTO — o
que qualquer docstring explicando a ferramenta invalidaria sozinha, e esta fase
ja tem duas armadilhas dessas catalogadas —, eles varrem os IMPORTS por arvore
de sintaxe e as constantes de texto que sao ARGUMENTO DE CHAMADA, que e por onde
um `runpy.run_path` ou um `subprocess` entraria. Assim este arquivo pode falar
da ferramenta pelo nome, como acabou de fazer, sem derrubar o proprio portao.
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import json
from pathlib import Path

import pytest

from l2scanner.calibracao import VERSAO_DO_ESQUEMA, Calibracao
from l2scanner.renda_semeadura import (
    ENTRADA_MEDIDA,
    RECUSADO_SEM_CONFIRMACAO,
    SEMEADO,
    EntradaDaPonte,
    semear,
)

RAIZ = Path(__file__).resolve().parent.parent
FIXTURA_DE_RENDA = (
    Path(__file__).parent / "fixtures" / "renda" / "calibracao_de_fixture.json"
)

# O NOME DA FERRAMENTA MORA NUMA CONSTANTE DE MODULO, E NAO DENTRO DE UMA
# CHAMADA, de proposito: o portao de execucao abaixo varre exatamente os textos
# que sao ARGUMENTO DE CHAMADA. Escrever o caminho inline aqui derrubaria o
# proprio portao — que e a armadilha que esta tarefa desarmou.
NOME_DA_FERRAMENTA = "semear_a_ponte_de_xp.py"
ARQUIVO_DA_FERRAMENTA = RAIZ / "tools" / NOME_DA_FERRAMENTA
AGULHA_DA_FERRAMENTA = NOME_DA_FERRAMENTA[:-3]

OUTRA_ENTRADA = EntradaDaPonte(
    personagem="Yazalaque",
    nivel=70,
    valores={
        "xp_por_ponto": 410_000,
        "medido_em": "2026-09-01",
        "n_abates": 80,
        "n_linhas_de_chat": 150,
        "janela_em_segundos": 120,
    },
)


def _arvore(caminho: Path) -> ast.Module:
    return ast.parse(caminho.read_text(encoding="utf-8"))


def _chamadas(arvore: ast.Module) -> set[str]:
    return {
        getattr(no.func, "attr", None) or getattr(no.func, "id", None)
        for no in ast.walk(arvore)
        if isinstance(no, ast.Call)
    }


def _campos_menos_a_ponte(cal: Calibracao) -> dict:
    """Todo campo do dataclass menos a ponte, para a comparacao antes/depois.

    A lista sai de `dataclasses.fields` e nunca de uma lista escrita a mao, pela
    mesma razao da amarra estrutural: a mao que esquece um campo aqui e a mesma
    que o esqueceria no `semear`.
    """
    return {
        campo.name: getattr(cal, campo.name)
        for campo in dataclasses.fields(Calibracao)
        if campo.name != "renda_ponte_de_xp"
    }


class TestSemearNaoApagaChaveAlheia:
    """A primeira garantia: a mudanca e CIRURGICA."""

    def test_NENHUM_OUTRO_CAMPO_MUDA(self):
        cal = Calibracao.carregar(FIXTURA_DE_RENDA)
        antes = _campos_menos_a_ponte(cal)

        resultado = semear(cal, ENTRADA_MEDIDA, confirmar=False)

        assert resultado.estado == SEMEADO
        assert _campos_menos_a_ponte(resultado.calibracao) == antes, (
            "a semeadura mexeu num campo que nao e dela"
        )

    def test_AS_DUAS_CHAVES_IRMAS_DA_RENDA_CONTINUAM_INTEIRAS(self):
        cal = Calibracao.carregar(FIXTURA_DE_RENDA)
        assert cal.renda_por_personagem, "a fixtura tem de ter as irmas preenchidas"
        assert cal.renda_moldes_da_barra, "senao esta assercao seria vacua"

        resultado = semear(cal, ENTRADA_MEDIDA, confirmar=False)

        assert resultado.calibracao.renda_por_personagem == cal.renda_por_personagem
        assert resultado.calibracao.renda_moldes_da_barra == cal.renda_moldes_da_barra

    def test_A_CALIBRACAO_RECEBIDA_NAO_E_MUTADA(self):
        """Ela devolve outra; a de quem chamou fica como estava.

        Um `semear` que mutasse no lugar tornaria impossivel mostrar as duas
        entradas lado a lado na recusa — a antiga ja teria sido sobrescrita.
        """
        cal = Calibracao.carregar(FIXTURA_DE_RENDA)
        cal.renda_ponte_de_xp = {"Yazalaque": {"70": dict(OUTRA_ENTRADA.valores)}}
        copia = copy.deepcopy(cal.renda_ponte_de_xp)

        semear(cal, ENTRADA_MEDIDA, confirmar=False)

        assert cal.renda_ponte_de_xp == copia

    def test_A_ENTRADA_DE_OUTRO_PERSONAGEM_SOBREVIVE(self):
        cal = Calibracao.carregar(FIXTURA_DE_RENDA)
        cal.renda_ponte_de_xp = {"Yazalaque": {"70": dict(OUTRA_ENTRADA.valores)}}

        resultado = semear(cal, ENTRADA_MEDIDA, confirmar=False)

        ponte = resultado.calibracao.renda_ponte_de_xp
        assert ponte["Yazalaque"]["70"]["xp_por_ponto"] == 410_000
        assert ponte["Faerlina"]["67"]["xp_por_ponto"] == 388_700

    def test_O_NIVEL_VIZINHO_DO_MESMO_PERSONAGEM_SOBREVIVE(self):
        cal = Calibracao.carregar(FIXTURA_DE_RENDA)
        cal.renda_ponte_de_xp = {
            "Faerlina": {"66": dict(OUTRA_ENTRADA.valores, xp_por_ponto=383_124)}
        }

        resultado = semear(cal, ENTRADA_MEDIDA, confirmar=False)

        ponte = resultado.calibracao.renda_ponte_de_xp
        assert ponte["Faerlina"]["66"]["xp_por_ponto"] == 383_124
        assert ponte["Faerlina"]["67"]["xp_por_ponto"] == 388_700


class TestSemearNaoSobrescreveCalada:
    """A segunda garantia: uma constante melhor nao morre em silencio."""

    def _com_a_entrada_ja_posta(self) -> Calibracao:
        cal = Calibracao.carregar(FIXTURA_DE_RENDA)
        cal.renda_ponte_de_xp = {
            "Faerlina": {
                "67": {
                    "xp_por_ponto": 389_000,
                    "medido_em": "2026-09-10",
                    "n_abates": 900,
                    "n_linhas_de_chat": 2_400,
                    "janela_em_segundos": 10_800,
                }
            }
        }
        return cal

    def test_SEM_CONFIRMACAO_ELA_RECUSA_E_DEVOLVE_A_MESMA_CALIBRACAO(self):
        """A existente foi medida em TRES HORAS; a semeada, em 2,5 minutos.

        Recalibrar por cima e o caminho normal previsto pela CTX-8 — mas nenhuma
        camada pode desfazer uma medicao melhor em silencio.
        """
        cal = self._com_a_entrada_ja_posta()

        resultado = semear(cal, ENTRADA_MEDIDA, confirmar=False)

        assert resultado.estado == RECUSADO_SEM_CONFIRMACAO
        assert resultado.calibracao is cal
        assert cal.renda_ponte_de_xp["Faerlina"]["67"]["xp_por_ponto"] == 389_000

    def test_A_RECUSA_CARREGA_AS_DUAS_ENTRADAS_LADO_A_LADO(self):
        """Quem chama precisa poder MOSTRAR as duas, e nao so dizer que recusou."""
        resultado = semear(
            self._com_a_entrada_ja_posta(), ENTRADA_MEDIDA, confirmar=False
        )
        assert resultado.existente["xp_por_ponto"] == 389_000
        assert resultado.existente["janela_em_segundos"] == 10_800
        assert resultado.entrando["xp_por_ponto"] == 388_700
        assert resultado.entrando["janela_em_segundos"] == 150

    def test_O_CONTROLE_COM_CONFIRMACAO_ELA_TROCA(self):
        """Sem este controle, uma implementacao que recusasse SEMPRE passaria."""
        cal = self._com_a_entrada_ja_posta()

        resultado = semear(cal, ENTRADA_MEDIDA, confirmar=True)

        assert resultado.estado == SEMEADO
        assert resultado.calibracao is not cal
        ponte = resultado.calibracao.renda_ponte_de_xp
        assert ponte["Faerlina"]["67"]["xp_por_ponto"] == 388_700
        assert ponte["Faerlina"]["67"]["janela_em_segundos"] == 150

    def test_SEM_ENTRADA_EXISTENTE_A_CONFIRMACAO_NAO_E_EXIGIDA(self):
        cal = Calibracao.carregar(FIXTURA_DE_RENDA)
        resultado = semear(cal, ENTRADA_MEDIDA, confirmar=False)
        assert resultado.estado == SEMEADO
        assert resultado.existente is None

    def test_A_ENTRADA_EXISTENTE_COM_CHAVE_INTEIRA_TAMBEM_E_VISTA(self):
        """O modo de falha que nao levanta, do lado da semeadura.

        Uma entrada gravada em memoria com a chave inteira `67` e a MESMA
        entrada. Um `semear` que so olhasse a chave de texto a sobrescreveria
        calada — e ainda deixaria as DUAS no arquivo.
        """
        cal = Calibracao.carregar(FIXTURA_DE_RENDA)
        cal.renda_ponte_de_xp = {"Faerlina": {67: {"xp_por_ponto": 389_000}}}

        recusa = semear(cal, ENTRADA_MEDIDA, confirmar=False)
        assert recusa.estado == RECUSADO_SEM_CONFIRMACAO

        trocada = semear(cal, ENTRADA_MEDIDA, confirmar=True)
        assert list(trocada.calibracao.renda_ponte_de_xp["Faerlina"]) == ["67"], (
            "a chave inteira e a de texto sao a MESMA entrada, e nao duas"
        )


class TestSemearNaoTocaDisco:
    """E o que a torna testavel sem `runpy`, sem `subprocess` e sem nomear a ferramenta."""

    def test_ELA_FUNCIONA_SEM_RECEBER_CAMINHO_NENHUM(self):
        cal = Calibracao.carregar(FIXTURA_DE_RENDA)
        assert semear(cal, ENTRADA_MEDIDA, confirmar=False).estado == SEMEADO

    def test_NENHUMA_ESCRITA_NEM_LEITURA_DE_ARQUIVO_NO_MODULO(self):
        """Conferido por ARVORE, e nao por leitura de codigo.

        `carregar` e `salvar` tambem estao na lista: se a decisao voltasse a
        conhecer o caminho do arquivo, ela voltaria a so poder ser testada
        rodando a ferramenta.
        """
        arvore = _arvore(RAIZ / "l2scanner" / "renda_semeadura.py")
        proibidas = {
            "open",
            "write_text",
            "write_bytes",
            "dump",
            "carregar",
            "salvar",
        }
        assert not (_chamadas(arvore) & proibidas)


class TestAIdaEVoltaRealPeloDisco:
    """A preservacao so vale se atravessar a persistencia de verdade."""

    def test_CARREGAR_SEMEAR_SALVAR_CARREGAR_PRESERVA_AS_IRMAS(self, tmp_path):
        origem = tmp_path / "calibration.json"
        origem.write_text(
            FIXTURA_DE_RENDA.read_text(encoding="utf-8"), encoding="utf-8"
        )

        antes = Calibracao.carregar(origem)
        resultado = semear(antes, ENTRADA_MEDIDA, confirmar=False)
        resultado.calibracao.salvar(origem)
        depois = Calibracao.carregar(origem)

        assert depois.versao == VERSAO_DO_ESQUEMA == 2
        assert depois.renda_por_personagem == antes.renda_por_personagem
        assert depois.renda_moldes_da_barra == antes.renda_moldes_da_barra
        assert depois.ponte_do_nivel("Faerlina", 67)["xp_por_ponto"] == 388_700

    def test_A_ENTRADA_MEDIDA_ATRAVESSA_SEM_PERDER_CAMPO(self, tmp_path):
        origem = tmp_path / "calibration.json"
        origem.write_text(
            FIXTURA_DE_RENDA.read_text(encoding="utf-8"), encoding="utf-8"
        )

        resultado = semear(
            Calibracao.carregar(origem), ENTRADA_MEDIDA, confirmar=False
        )
        resultado.calibracao.salvar(origem)

        de_volta = Calibracao.carregar(origem).ponte_do_nivel("Faerlina", 67)
        assert de_volta == ENTRADA_MEDIDA.valores

    def test_A_CHAVE_DO_NIVEL_VIRA_TEXTO_NO_ARQUIVO(self, tmp_path):
        """JSON nao tem chave inteira, e e por isso que o acessor normaliza."""
        origem = tmp_path / "calibration.json"
        origem.write_text(
            FIXTURA_DE_RENDA.read_text(encoding="utf-8"), encoding="utf-8"
        )
        resultado = semear(
            Calibracao.carregar(origem), ENTRADA_MEDIDA, confirmar=False
        )
        resultado.calibracao.salvar(origem)

        cru = json.loads(origem.read_text(encoding="utf-8"))
        assert list(cru["renda_ponte_de_xp"]["Faerlina"]) == ["67"]


class TestAEntradaMedidaCarregaAProcedencia:
    """A procedencia e o produto tanto quanto o numero (CTX-8)."""

    def test_OS_CINCO_NUMEROS_ESTAO_LA(self):
        assert ENTRADA_MEDIDA.personagem == "Faerlina"
        assert ENTRADA_MEDIDA.nivel == 67
        assert ENTRADA_MEDIDA.valores["xp_por_ponto"] == 388_700
        assert ENTRADA_MEDIDA.valores["medido_em"] == "2026-09-02"
        assert ENTRADA_MEDIDA.valores["n_linhas_de_chat"] == 240
        assert ENTRADA_MEDIDA.valores["n_abates"] == 114
        assert ENTRADA_MEDIDA.valores["janela_em_segundos"] == 150

    def test_A_OBSERVACAO_CARREGA_O_CENSO_QUE_TORNA_O_NUMERO_CONFIAVEL(self):
        """Um numero sem o censo ao lado e indistinguivel de um chute."""
        observacao = ENTRADA_MEDIDA.valores["observacao"]
        for pedaco in ("188", "1903", "8.555", "55 Hz", "383.124"):
            assert pedaco in observacao, (
                "a observacao precisa carregar o censo completo, as duas "
                "medicoes independentes e o aglomerado nao identificado"
            )

    def test_O_MODULO_CITA_O_ENDERECO_VERSIONADO_DA_MEDICAO(self):
        """A disciplina da C-6: nenhum numero vira dado sem denominador ao lado."""
        fonte = (RAIZ / "l2scanner" / "renda_semeadura.py").read_text(
            encoding="utf-8"
        )
        assert "REQUIREMENTS.md" in fonte


class TestOsPortoesDaFerramentaDeBancada:
    """A ferramenta e `argparse` e nada mais, e nenhum teste a alcanca."""

    def _testes(self):
        return sorted((RAIZ / "tests").rglob("test_*.py"))

    def test_NENHUM_TESTE_IMPORTA_A_FERRAMENTA(self):
        culpados = []
        for arquivo in self._testes():
            for no in ast.walk(_arvore(arquivo)):
                if isinstance(no, (ast.Import, ast.ImportFrom)):
                    alvo = (getattr(no, "module", None) or "") + " " + " ".join(
                        alias.name for alias in no.names
                    )
                    if AGULHA_DA_FERRAMENTA in alvo:
                        culpados.append(arquivo.name)
        assert not culpados, culpados

    def test_NENHUM_TESTE_A_EXECUTA_POR_CAMINHO(self):
        """O portao olha so os textos que sao ARGUMENTO DE CHAMADA.

        E por onde `runpy.run_path` ou `subprocess` entrariam. Qualquer texto do
        arquivo derrubaria uma docstring legitima — que e exatamente a armadilha
        que esta tarefa desarmou, e nao uma que ela deveria repetir.
        """
        culpados = []
        for arquivo in self._testes():
            for no in ast.walk(_arvore(arquivo)):
                if not isinstance(no, ast.Call):
                    continue
                for filho in ast.walk(no):
                    if (
                        isinstance(filho, ast.Constant)
                        and isinstance(filho.value, str)
                        and AGULHA_DA_FERRAMENTA in filho.value
                    ):
                        culpados.append(arquivo.name)
        assert not culpados, culpados

    def test_A_FERRAMENTA_E_FINA_E_A_DECISAO_NAO_MORA_NELA(self):
        """E isto e o que torna os dois portoes acima satisfaziveis JUNTO com
        as duas garantias: nao ha o que importar de la."""
        arvore = _arvore(ARQUIVO_DA_FERRAMENTA)
        funcoes = sorted(
            no.name for no in arvore.body if isinstance(no, ast.FunctionDef)
        )
        assert set(funcoes) <= {"_argumentos", "main"}, funcoes

        importa = any(
            "renda_semeadura"
            in ((getattr(no, "module", None) or "")
                + " "
                + " ".join(alias.name for alias in no.names))
            for no in ast.walk(arvore)
            if isinstance(no, (ast.Import, ast.ImportFrom))
        )
        assert importa, "a decisao vem do modulo, e nao do `argparse`"

    def test_A_FERRAMENTA_NAO_REDEFINE_A_ENTRADA_MEDIDA(self):
        """Um dado que so a ferramenta conhecesse seria um dado sem teste."""
        arvore = _arvore(ARQUIVO_DA_FERRAMENTA)
        redefinicoes = [
            alvo.id
            for no in ast.walk(arvore)
            if isinstance(no, ast.Assign)
            for alvo in no.targets
            if isinstance(alvo, ast.Name) and alvo.id == "ENTRADA_MEDIDA"
        ]
        assert not redefinicoes

    def test_A_FERRAMENTA_NUNCA_ESCREVE_O_ARQUIVO_A_MAO(self):
        """Um JSON truncado por Ctrl-C mata o scanner de party INTEIRO.

        O `calibration.json` e compartilhado por quatro features e carrega a
        party window, os limiares HSV afinados a mao contra o Gamma da tela e as
        assinaturas de nome. A escrita passa pelo `salvar`, com `.tmp` ao lado e
        troca atomica, e nao ha nenhuma outra escrita na ferramenta.
        """
        arvore = _arvore(ARQUIVO_DA_FERRAMENTA)
        assert not (
            _chamadas(arvore) & {"write_text", "write_bytes", "dump"}
        )

    def test_A_FERRAMENTA_PASSA_PELO_SALVAR_QUE_JA_EXISTE(self):
        """O controle do teste acima: sem ele, uma ferramenta que nao gravasse
        nada passaria."""
        assert {"carregar", "salvar"} <= _chamadas(_arvore(ARQUIVO_DA_FERRAMENTA))


class TestAFormaDoResultado:
    def test_ELE_E_CONGELADO(self):
        resultado = semear(
            Calibracao.carregar(FIXTURA_DE_RENDA), ENTRADA_MEDIDA, confirmar=False
        )
        with pytest.raises(Exception):
            resultado.estado = "outro"

    def test_OS_DOIS_ESTADOS_SAO_TEXTOS_DIFERENTES(self):
        assert SEMEADO != RECUSADO_SEM_CONFIRMACAO
        assert SEMEADO and RECUSADO_SEM_CONFIRMACAO
