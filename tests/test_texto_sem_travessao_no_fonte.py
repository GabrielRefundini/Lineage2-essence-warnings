"""O PORTAO CONTRA O TRAVESSAO NO FONTE: nao espera o texto sair para pegar o
defeito, varre o proprio codigo antes de rodar uma linha dele.

O DEFEITO QUE ESTE PORTAO EXISTE PARA IMPEDIR (medido em 2026-09-04, com
`texto_de_encerramento` de producao): o caminho ate o WhatsApp/Chatwoot passa
por cp1252 em algum ponto da cadeia, e um travessao (—) dentro de uma
f-string vira caractere corrompido no celular do usuario. E O MESMO defeito
ja consertado em `notificador.formatar` (commit 4085c2b) e em
`__main__.laco_principal` (commit eb44705) — cada vez numa frase nova, porque
nenhum dos dois consertos deixou um portao atras de si.

POR QUE VARRER O FONTE (AST), E NAO SO A SAIDA DAS FUNCOES. `TestAVozDaCasa`,
em `test_respawn.py`, ja faz a checagem por SAIDA: chama as funcoes que
produzem texto e afirma sobre a string devolvida. Essa forma tem um limite
estrutural — ela so cobre os textos que o proprio teste sabe enumerar, e uma
funcao nova (ou um ramo novo dentro de uma funcao ja coberta) fica de fora
ate alguem lembrar de acrescenta-la na lista de enumeracao. Varrer o FONTE
fecha esse buraco: qualquer string literal nova no arquivo, em qualquer
funcao, entra na varredura no mesmo commit em que o arquivo e salvo, sem
precisar que ninguem lembre de nada.

O QUE FICA DE FORA, DE PROPOSITO. Docstrings usam travessao livremente neste
projeto — a convencao ja esta em toda parte, inclusive acima — e comentarios
tambem. Excluir DOCSTRING (o primeiro `Expr` de string de um modulo, classe
ou funcao) e a unica exclusao que este scanner precisa fazer: comentarios
nunca entram na arvore (AST) porque o tokenizer do Python os descarta antes,
entao eles ja saem de graca.

MODULOS COBERTOS: os que formatam texto de WhatsApp ou console para o
usuario. `agenda.py` e o motivo deste arquivo existir (o defeito medido em
`texto_de_encerramento`); os outros nove ja foram medidos limpos nesta mesma
tarefa (2026-09-04, rodando `travessoes_fora_de_docstring` sobre cada um) e
entram no portao para nao precisarem ser medidos de novo na proxima frase que
alguem escrever ali.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

RAIZ_DO_PACOTE = pathlib.Path(__file__).resolve().parent.parent / "l2scanner"

# Modulos que produzem texto para o usuario (WhatsApp ou console). Todos os
# nove alem de agenda.py ja foram medidos limpos em 2026-09-04 -- ver a
# docstring acima.
MODULOS_COM_TEXTO_DE_USUARIO = [
    "agenda.py",
    "presenca.py",
    "bosses.py",
    "manutencao.py",
    "esquecimento.py",
    "batismo.py",
    "aprendiz.py",
    "reancoragem.py",
    "conferencia_do_proprio.py",
    "notificador.py",
    "respawn.py",
]

TRAVESSOES = ("—", "–")  # em dash (—), en dash (–)


def _nos_de_docstring(arvore: ast.AST) -> set[int]:
    """`id()` dos nos de `ast.Constant` que sao docstring.

    Docstring e o primeiro `Expr` de string de um Module/ClassDef/
    FunctionDef/AsyncFunctionDef -- a mesma regra que `ast.get_docstring` usa
    por dentro. Qualquer outra string, mesmo que pareca comentario de
    proposito (uma linha solta no meio de uma funcao), NAO e docstring e
    entra na varredura -- e essa e a intencao: so o PRIMEIRO statement de um
    escopo e imune.
    """
    ids: set[int] = set()
    for no in ast.walk(arvore):
        if isinstance(
            no, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            corpo = no.body
            if corpo and isinstance(corpo[0], ast.Expr):
                valor = corpo[0].value
                if isinstance(valor, ast.Constant) and isinstance(valor.value, str):
                    ids.add(id(valor))
    return ids


def travessoes_fora_de_docstring(caminho: pathlib.Path) -> list[tuple[int, str]]:
    """(linha, trecho) de toda string literal com travessao que NAO e docstring.

    Cobre f-strings tambem: o Python representa os pedacos literais de uma
    f-string como `ast.Constant` dentro de um `ast.JoinedStr`, e `ast.walk`
    desce ate eles do mesmo jeito que desce em qualquer outra string.
    """
    fonte = caminho.read_text(encoding="utf-8")
    arvore = ast.parse(fonte, filename=str(caminho))
    docstrings = _nos_de_docstring(arvore)

    achados: list[tuple[int, str]] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Constant) and isinstance(no.value, str):
            if id(no) in docstrings:
                continue
            if any(t in no.value for t in TRAVESSOES):
                achados.append((no.lineno, no.value))
    return achados


@pytest.mark.parametrize("nome_do_modulo", MODULOS_COM_TEXTO_DE_USUARIO)
def test_nenhum_travessao_fora_de_docstring(nome_do_modulo):
    """O portao em si: falha se QUALQUER string nao-docstring do modulo tiver
    travessao.

    A prova de que ele acusa de verdade (mutacao) e de que ele nao acusa
    docstring por engano (controle) moram nos dois testes abaixo, que chamam
    esta MESMA funcao de producao sobre um arquivo sintetico -- nunca uma
    reimplementacao paralela do scanner.
    """
    achados = travessoes_fora_de_docstring(RAIZ_DO_PACOTE / nome_do_modulo)
    assert achados == [], (
        f"{nome_do_modulo} tem travessao fora de docstring/comentario: {achados}"
    )


def test_o_portao_acusa_travessao_fora_de_docstring(tmp_path):
    """MUTACAO: um arquivo de mentira com o MESMO defeito tem que ser
    acusado, ou o portao acima e so decoracao que nunca falha de verdade."""
    arquivo = tmp_path / "modulo_de_mentira.py"
    arquivo.write_text(
        'def texto():\n'
        '    """Docstring com travessao — livre, nao conta."""\n'
        '    # comentario com travessao — tambem livre\n'
        '    return f"ola — mundo"\n',
        encoding="utf-8",
    )

    achados = travessoes_fora_de_docstring(arquivo)

    assert len(achados) == 1
    assert achados[0][1] == "ola — mundo"


def test_o_portao_nao_acusa_travessao_dentro_de_docstring(tmp_path):
    """CONTROLE: docstring com travessao passa limpo, senao o portao
    proibiria a propria convencao de documentacao do projeto."""
    arquivo = tmp_path / "modulo_limpo.py"
    arquivo.write_text(
        '"""Docstring de modulo com travessao — de sobra."""\n'
        "\n"
        "def f():\n"
        '    """Docstring de funcao — tambem livre."""\n'
        '    return "sem travessao nenhum aqui"\n',
        encoding="utf-8",
    )

    assert travessoes_fora_de_docstring(arquivo) == []
