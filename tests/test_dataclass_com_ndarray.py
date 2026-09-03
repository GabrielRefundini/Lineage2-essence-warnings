"""Portao: nenhum dataclass que carregue ndarray nasce com `eq` gerado.

O QUE ESTE PORTAO IMPEDE, com o traceback que o pariu

Em 02/09/2026 21:09 o aprendizado de identidades morreu em campo:

    File "l2scanner/aprendiz.py", line 1013, in observar
      disponiveis.remove(vigia)
    File "<string>", line 4, in __eq__
    ValueError: The truth value of an array with more than one element is
    ambiguous. Use a.any() or a.all()

`_Vigia` era um `@dataclass` com `ancora: np.ndarray`. O `__eq__` que o
`dataclasses` gera compara os campos como TUPLA, a comparacao de tupla comeca
no campo 0, e `array == array` devolve um ARRAY. `bool()` de um array com mais
de um elemento nao existe, e a excecao sobe.

POR QUE UM PORTAO, E NAO SO O CONSERTO DAQUELA LINHA

Porque o defeito nao mora na chamada, mora na CLASSE. Qualquer `in`, `remove`,
`index`, `count`, `==` ou `sorted` que alguem escreva depois sobre uma dessas
classes traz o mesmo `ValueError` de volta, e nao ha nada no codigo que avise.
Um `@dataclass` novo com um campo de mascara nasce defeituoso por default, que
e a pior forma de nascer.

E, PRINCIPALMENTE, PORQUE A SUITE NAO PEGA

`list.remove`, `in`, `index` e `count` usam `PyObject_RichCompareBool`, que tem
ATALHO DE IDENTIDADE: se o item da lista E o proprio objeto procurado, ele
devolve `True` sem nunca chamar `__eq__`. Com um elemento so na lista, ou com o
alvo na primeira posicao, o array nunca chega a ser comparado e o teste fica
VERDE sobre codigo quebrado. Foi exatamente isso que deixou o defeito atravessar
5000 testes: a suite do `Aprendiz` observava uma candidata por vez, e nesse
arranjo o alvo cai sempre na frente da lista.

Um portao que le a ESTRUTURA nao depende de nenhum arranjo de runtime, e por
isso e o unico controle que fecha esta classe de defeito de verdade.

POR QUE `eq=False` E NAO "compare com `np.array_equal`"

Um `__eq__` escrito a mao que compare mascaras por conteudo seria pior: duas
sequencias de leitura DIFERENTES, em linhas diferentes da party window, viram
"o mesmo objeto" quando a mascara coincide, e remover uma tira a outra da mesa
sem erro nenhum. A semantica dessas classes e IDENTIDADE. `eq=False` faz
`__eq__` cair para `object.__eq__`, que ja e identidade, e custa zero linha.

O QUE ESTE PORTAO NAO PROMETE

Ele nao olha `dict`, `list` ou `tuple` de objetos que POR DENTRO tenham ndarray
sem anotacao que diga isso, nem `Any`, nem um campo cujo tipo real so aparece em
runtime. Ele cobre o que da para ler no texto: anotacao que mencione `ndarray`,
`np.` ou `NDArray`. Prometer mais seria mentir sobre a cobertura.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PASTAS_VARRIDAS = ("l2scanner", "tools", "tests")

# Marcas de tipo que denunciam um campo de array no texto da anotacao.
MARCAS_DE_ARRAY = ("ndarray", "np.", "NDArray")

# A DIVIDA CONHECIDA, nominal e curta de proposito.
#
# As tres foram ACHADAS por este portao, e nao ignoradas antes de aparecer.
# Todas ficaram de fora do conserto de 02/09/2026 por escopo, e nao por
# estarem certas: os tres arquivos pertencem a outros workstreams e estavam
# explicitamente fechados naquele encargo.
#
#   l2scanner/mercado_visao.py    workstream do mercado
#   tools/medir_largura_de_run.py ferramenta de medicao do mercado
#   tools/medir_oclusao.py        ferramenta de medicao do mercado
#
# Nenhuma chegou a estourar porque ninguem faz `in`, `remove`, `index` ou `==`
# sobre elas hoje. O defeito nelas e LATENTE, e continua latente ate a primeira
# linha que compare duas.
#
# Ficar NOMEADA aqui e o ponto. Uma varredura que simplesmente pulasse
# `mercado_*` e `medir_*` deixaria toda classe FUTURA daqueles arquivos entrar
# sem portao nenhum; nomear tres deixa a quarta barrada. Uma lista vazia seria
# um portao mais bonito e menos honesto.
DIVIDA_CONHECIDA = frozenset(
    {
        ("l2scanner/mercado_visao.py", "AncoraDoPainel"),
        ("tools/medir_largura_de_run.py", "CelulaColhida"),
        ("tools/medir_oclusao.py", "LeituraDeFrame"),
    }
)


def _decorador_de_dataclass(classe: ast.ClassDef) -> ast.expr | None:
    """O decorador `@dataclass` da classe, com ou sem parenteses."""
    for decorador in classe.decorator_list:
        alvo = decorador.func if isinstance(decorador, ast.Call) else decorador
        nome = getattr(alvo, "attr", None) or getattr(alvo, "id", None)
        if nome == "dataclass":
            return decorador
    return None


def _campos_de_array(classe: ast.ClassDef) -> list[str]:
    """Os campos anotados cuja anotacao denuncia um ndarray."""
    achados = []
    for corpo in classe.body:
        if not isinstance(corpo, ast.AnnAssign) or corpo.annotation is None:
            continue
        anotacao = ast.unparse(corpo.annotation)
        if any(marca in anotacao for marca in MARCAS_DE_ARRAY):
            achados.append(f"{ast.unparse(corpo.target)}: {anotacao}")
    return achados


def _eq_declarado(decorador: ast.expr) -> str | None:
    """O valor literal passado em `eq=`, ou `None` se ninguem passou."""
    if not isinstance(decorador, ast.Call):
        return None
    for chave in decorador.keywords:
        if chave.arg == "eq":
            return ast.unparse(chave.value)
    return None


def dataclasses_com_array(fonte: str) -> list[tuple[str, list[str], str | None]]:
    """Cada dataclass do texto que carrega array: nome, campos e o `eq=`.

    Funcao PURA, sobre texto, para que o teste de mutacao logo abaixo consiga
    provar que o detector morde sem precisar escrever um modulo defeituoso
    dentro de `l2scanner/`.
    """
    achados = []
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, ast.ClassDef):
            continue
        decorador = _decorador_de_dataclass(no)
        if decorador is None:
            continue
        campos = _campos_de_array(no)
        if campos:
            achados.append((no.name, campos, _eq_declarado(decorador)))
    return achados


def arquivos_varridos() -> list[Path]:
    encontrados = []
    for pasta in PASTAS_VARRIDAS:
        encontrados.extend(sorted((RAIZ / pasta).rglob("*.py")))
    assert encontrados, "a varredura nao achou arquivo nenhum: o portao seria vazio"
    return encontrados


def test_todo_dataclass_com_ndarray_declara_eq_False() -> None:
    """O portao. Um `eq` gerado sobre ndarray e um ValueError esperando."""
    culpados = []
    for arquivo in arquivos_varridos():
        relativo = arquivo.relative_to(RAIZ).as_posix()
        for nome, campos, eq in dataclasses_com_array(
            arquivo.read_text(encoding="utf-8")
        ):
            if (relativo, nome) in DIVIDA_CONHECIDA:
                continue
            if eq == "False":
                continue
            culpados.append(f"{relativo}::{nome}  campos={campos}  eq={eq}")

    assert not culpados, (
        "dataclass com ndarray e `__eq__` gerado. Comparar dois ndarray devolve "
        "um ARRAY, e `bool()` dele levanta ValueError: foi assim que o "
        "aprendizado de identidades morreu em campo em 02/09/2026, dentro de um "
        "`list.remove`. Declare `eq=False` (a semantica dessas classes e "
        "IDENTIDADE, nao igualdade de conteudo). Culpados:\n  "
        + "\n  ".join(culpados)
    )


def test_a_divida_conhecida_ainda_existe_e_ainda_e_divida() -> None:
    """Uma excecao que sobreviveu ao arquivo que ela protegia e lixo.

    Se `AncoraDoPainel` ganhar `eq=False` ou sumir, esta entrada tem de sair
    junto. Sem isto a lista so cresce, e uma lista de excecoes que so cresce
    para de ser divida e vira o novo default.
    """
    for relativo, nome in sorted(DIVIDA_CONHECIDA):
        arquivo = RAIZ / relativo
        assert arquivo.exists(), f"{relativo} sumiu: tire a entrada da lista"

        achados = {
            achado[0]: achado[2]
            for achado in dataclasses_com_array(arquivo.read_text(encoding="utf-8"))
        }
        assert nome in achados, (
            f"{relativo}::{nome} nao carrega mais ndarray: tire a entrada da lista"
        )
        assert achados[nome] != "False", (
            f"{relativo}::{nome} ja declara eq=False: tire a entrada da lista, "
            "porque o portao normal ja cobre essa classe"
        )


class TestODetectorMorde:
    """A prova por MUTACAO, que e o que separa um portao de um teste decorativo.

    Sem ela, um bug no leitor de AST deixaria a varredura verde para sempre e
    ninguem notaria: e o modo de falha mais caro que um controle destes tem, e
    o unico que ele nao consegue reportar sozinho.
    """

    @pytest.mark.parametrize(
        "fonte",
        [
            "@dataclass\nclass X:\n    m: np.ndarray\n",
            "@dataclass()\nclass X:\n    m: np.ndarray\n",
            "@dataclass(frozen=True)\nclass X:\n    m: np.ndarray\n",
            "@dataclasses.dataclass\nclass X:\n    m: np.ndarray\n",
            "@dataclass(frozen=True)\nclass X:\n    m: NDArray[np.uint8]\n",
            "@dataclass\nclass X:\n    m: dict[str, np.ndarray]\n",
            "@dataclass(eq=True)\nclass X:\n    m: np.ndarray\n",
        ],
    )
    def test_a_classe_defeituosa_e_ACUSADA(self, fonte: str) -> None:
        achados = dataclasses_com_array(fonte)
        assert achados, f"passou batido: {fonte!r}"
        assert achados[0][2] != "False"

    @pytest.mark.parametrize(
        "fonte",
        [
            "@dataclass(eq=False)\nclass X:\n    m: np.ndarray\n",
            "@dataclass(frozen=True, eq=False)\nclass X:\n    m: np.ndarray\n",
        ],
    )
    def test_a_classe_consertada_PASSA(self, fonte: str) -> None:
        achados = dataclasses_com_array(fonte)
        assert achados and achados[0][2] == "False"

    @pytest.mark.parametrize(
        "fonte",
        [
            "@dataclass\nclass X:\n    n: int\n",
            "class X:\n    m: np.ndarray\n",
            "@dataclass\nclass X:\n    nome: str\n    quantos: int\n",
        ],
    )
    def test_quem_nao_carrega_array_nao_e_incomodado(self, fonte: str) -> None:
        """Um portao que acusa todo mundo e desligado na primeira semana."""
        assert dataclasses_com_array(fonte) == []


class TestOPortaoCobreOndeODefeitoAconteceu:
    """A ancora: se a varredura parar de enxergar `_Vigia`, ela nao vale nada.

    Um portao pode ficar verde por estar certo ou por estar cego, e as duas
    coisas parecem iguais na saida do pytest. Esta classe desempata.
    """

    def test_a_varredura_enxerga_o_Vigia_do_aprendiz(self) -> None:
        fonte = (RAIZ / "l2scanner" / "aprendiz.py").read_text(encoding="utf-8")
        achados = {nome: eq for nome, _, eq in dataclasses_com_array(fonte)}

        assert "_Vigia" in achados, (
            "a classe onde o crash de 02/09/2026 aconteceu saiu do radar da "
            "varredura: o portao passou a estar cego, e nao correto"
        )
        assert achados["_Vigia"] == "False"

    def test_o_aprendiz_registra_o_atalho_de_identidade(self) -> None:
        """A causa da intermitencia fica escrita, ou volta como surpresa.

        Quem ler so `eq=False` conclui "estilo" e desfaz na primeira limpeza.
        `PyObject_RichCompareBool` no texto e o que impede isso.
        """
        fonte = (RAIZ / "l2scanner" / "aprendiz.py").read_text(encoding="utf-8")

        assert "PyObject_RichCompareBool" in fonte
        assert "disponiveis.remove(vigia)" in fonte, "o traceback de campo"
