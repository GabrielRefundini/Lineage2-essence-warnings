"""Mede se da para VETAR duplicata de assinatura antes de aprende-la.

O PROBLEMA MEDIDO (2026-09-04)

A `.identidades/` do usuario tinha 23 assinaturas ativas para 11 pessoas:
PIRULITO com 6 copias, Mostarda com 4, Welazkez, TITANDER, Disney e SabacCru
com 2 cada. Cada copia queimou um marcador `perguntado_` e disparou uma
pergunta no WhatsApp. Seis PIRULITOs sao seis perguntas para a mesma pessoa.

Nenhuma delas passa do teto de contaminacao (a maior tem 218 px, o teto e 220),
entao o teto esta fazendo o trabalho dele e o problema e outro: as copias nao
se PARECEM o bastante para o veto de D-02 (`confianca >= LIMIAR_DE_CASAMENTO`)
disparar.

O QUE ESTA FERRAMENTA RESPONDE

Ela pontua TODOS os pares do acervo real sob varios criterios de alinhamento e
separa os pares em dois conjuntos conhecidos — MESMA pessoa e pessoas
DIFERENTES —, usando os rotulos de campo de `tests/fixtures/`. Duas tabelas
saem daqui:

1. a tabela dos pares: pior par certo, melhor par errado, margem ate o limiar;
2. a simulacao de nascimento: percorrendo o acervo na ordem em que ele nasceu,
   quantas entradas cada criterio teria barrado.

A SEGUNDA E A QUE DECIDE, e nao a primeira. Um veto nao precisa alcancar TODO
par da mesma pessoa; ele precisa nunca disparar num par de pessoas diferentes
(senao duas viram uma, em silencio e para sempre) e barrar alguma coisa (senao
nao poupa pergunta nenhuma).

TUDO PONTUA PELA PRODUCAO. `_correlacionar` e `identificar_linhas` sao os de
`l2scanner.identidade`, e a linha de base e a `confianca` que a producao
devolve HOJE, com os dois passes do ornamento e o fator de contaminacao
dentro. A unica peca nova e o deslocamento, e `tests/test_aferir_duplicatas.py`
o amarra ao `_deslocar_para_a_esquerda` de producao para que as duas nao
divirjam.

USO

    .venv\\Scripts\\python.exe tools\\aferir_duplicatas.py
    .venv\\Scripts\\python.exe tools\\aferir_duplicatas.py --pasta .identidades

Sem argumento le a fixture versionada (53 assinaturas reais, copiadas em
2026-09-04). Com `--pasta` le uma pasta de verdade — mas ai so a simulacao de
nascimento vale, porque os rotulos sao os das 53.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from l2scanner.acervo import (  # noqa: E402
    PREFIXO_ASSINATURA,
    PREFIXO_ESQUECIDA,
    chave_da_assinatura,
)
from l2scanner.identidade import (  # noqa: E402
    LIMIAR_DE_CASAMENTO,
    Assinatura,
    _correlacionar,
    identificar_linhas,
    mascara_de_texto,
)

FIXTURES = RAIZ / "tests" / "fixtures"
PASTA_PADRAO = FIXTURES / "acervo_real_2026_09_04"
ROTULOS = FIXTURES / "duplicatas_2026_09_04.json"
NASCIMENTO = FIXTURES / "nascimento_2026_09_04.json"
CALIBRADAS = FIXTURES / "assinaturas_calibradas_2026_09_04.json"

# O rotulo de quem nao tem rotulo unico: pedra, poeira, ou dois nomes inteiros
# na mesma faixa. Fica FORA da tabela de pares (nao e "mesma pessoa" nem
# "pessoas diferentes") e DENTRO da simulacao de nascimento, porque ela
# aconteceu de verdade e o veto teria de lidar com ela.
INDETERMINADA = "indeterminada"


def deslocar(mascara: np.ndarray, colunas: int) -> np.ndarray:
    """Recorta e cola em vazio, para os DOIS lados.

    E o mesmo recorte-e-cola de `identidade._deslocar_para_a_esquerda`, que so
    aceita o sentido negativo porque um ornamento so empurra para a direita.
    Aqui os dois sentidos interessam: o que separa as copias e a coluna do nome
    andando entre sessoes, e ela anda para os dois lados.
    """
    saida = np.zeros_like(mascara)
    largura = mascara.shape[1] - abs(colunas)
    if largura <= 0:
        return saida
    if colunas >= 0:
        saida[:, colunas : colunas + largura] = mascara[:, :largura]
    else:
        saida[:, :largura] = mascara[:, -colunas :]
    return saida


def bgr_da_mascara(mascara: np.ndarray) -> np.ndarray:
    """Um recorte que `mascara_de_texto` devolve identico a `mascara`.

    A producao pontua RECORTES, e o acervo guarda MASCARAS. Esta ponte existe
    para que a linha de base seja a `identificar_linhas` de verdade, e nao uma
    reimplementacao dela — o erro que a licao 1 do CLAUDE.md descreve.
    """
    return np.dstack([mascara * 255] * 3).astype(np.uint8)


def criterio_alinhado(a: np.ndarray, b: np.ndarray) -> float:
    return _correlacionar(a, b)


def criterio_deslizante(colunas: int) -> Callable[[np.ndarray, np.ndarray], float]:
    def pontuar(a: np.ndarray, b: np.ndarray) -> float:
        melhor = 0.0
        for dx in range(-colunas, colunas + 1):
            melhor = max(
                melhor, _correlacionar(a, deslocar(b, dx)), _correlacionar(b, deslocar(a, dx))
            )
        return melhor

    return pontuar


def faixa_do_nome(mascara: np.ndarray, altura: int) -> np.ndarray:
    """A janela de `altura` linhas com mais tinta.

    Existe aqui para ser REFUTADA e ficar refutada: ver a tabela da varredura
    em `criterios()`.
    """
    if altura >= mascara.shape[0]:
        return mascara
    tinta = mascara.sum(axis=1).astype(np.int64)
    if tinta.sum() == 0:
        return mascara
    inicio = max(
        range(mascara.shape[0] - altura + 1),
        key=lambda y: int(tinta[y : y + altura].sum()),
    )
    return mascara[inicio : inicio + altura, :]


def criterio_por_faixa(
    altura: int, colunas: int
) -> Callable[[np.ndarray, np.ndarray], float]:
    deslizante = criterio_deslizante(colunas)

    def pontuar(a: np.ndarray, b: np.ndarray) -> float:
        return deslizante(faixa_do_nome(a, altura), faixa_do_nome(b, altura))

    return pontuar


def criterios() -> dict[str, Callable[[np.ndarray, np.ndarray], float]]:
    return {
        "alinhado (producao)": criterio_alinhado,
        "desliza h +-2": criterio_deslizante(2),
        "desliza h +-3": criterio_deslizante(3),
        "desliza h +-6": criterio_deslizante(6),
        "desliza h +-25": criterio_deslizante(25),
        "faixa 5 h +-6": criterio_por_faixa(5, 6),
        "faixa 8 h +-6": criterio_por_faixa(8, 6),
        "faixa 10 h +-6": criterio_por_faixa(10, 6),
        "faixa 12 h +-6": criterio_por_faixa(12, 6),
    }


def ler_assinaturas(pasta: Path) -> list[tuple[str, Assinatura]]:
    """Le `assinatura_*` e `esquecida_*`, conferindo a chave como o acervo faz.

    A conferencia nao e zelo: `acervo._ler` recalcula a chave a partir do
    conteudo justamente para que o nome do arquivo seja soma de verificacao e
    nao afirmacao. Uma medicao sobre um arquivo editado a mao mediria outra
    coisa.
    """
    achadas = []
    for caminho in sorted(pasta.glob("*.json")):
        nome = caminho.name
        if not (
            nome.startswith(PREFIXO_ASSINATURA) or nome.startswith(PREFIXO_ESQUECIDA)
        ):
            continue
        chave = nome.split("_", 1)[1].removesuffix(".json")
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
        assinatura = Assinatura.de_dict({"nome": "", **bruto})
        if chave_da_assinatura(assinatura) != chave:
            continue
        achadas.append((chave, assinatura))
    return achadas


def ler_calibradas() -> list[tuple[str, Assinatura]]:
    dados = json.loads(CALIBRADAS.read_text(encoding="utf-8"))
    return [("calibrada", Assinatura.de_dict(d)) for d in dados]


def tabela_dos_pares(
    itens: list[tuple[str, str, np.ndarray]], apenas: tuple[str, ...] = ()
) -> dict[str, dict]:
    """Por criterio: pior par certo, melhor par errado, margem, quantos passam.

    `itens` e `(rotulo, chave, mascara)`. Quem tem rotulo `indeterminada` fica
    de fora: um recorte sem dono nao pertence a nenhum dos dois conjuntos, e
    enfia-lo no de "pessoas diferentes" inventaria pares errados que ninguem
    mediu.

    `apenas` limita quais criterios rodam. Existe para a suite: a tabela
    inteira sao ~13 mil pontuacoes e 16 segundos, e o teste so precisa dos
    criterios que sustentam a decisao.
    """
    conhecidos = [i for i in itens if i[0] != INDETERMINADA]
    saida = {}
    for nome, pontuar in criterios().items():
        if apenas and nome not in apenas:
            continue
        certos, errados, pior_errado = [], [], (0.0, "")
        for a, b in itertools.combinations(conhecidos, 2):
            valor = pontuar(a[2], b[2])
            if a[0] == b[0]:
                certos.append(valor)
            else:
                errados.append(valor)
                if valor > pior_errado[0]:
                    pior_errado = (valor, f"{a[0]}/{a[1][:8]} x {b[0]}/{b[1][:8]}")
        saida[nome] = {
            "pares_certos": len(certos),
            "pares_errados": len(errados),
            "pior_certo": min(certos),
            "melhor_errado": max(errados),
            "quem_errado": pior_errado[1],
            "certos_acima_do_limiar": sum(1 for v in certos if v >= LIMIAR_DE_CASAMENTO),
            "margem": LIMIAR_DE_CASAMENTO - max(errados),
        }
    return saida


def veto_da_producao(mascara: np.ndarray, aceitas: list[tuple[str, np.ndarray]]) -> float:
    """A `confianca` que `identificar_linhas` devolve hoje. A linha de base."""
    if not aceitas:
        return 0.0
    casamentos = identificar_linhas(
        {0: bgr_da_mascara(mascara)},
        [Assinatura(nome=chave, mascara=m) for chave, m in aceitas],
    )
    return casamentos[0].confianca


def simulacao_de_nascimento(
    itens: list[tuple[str, str, np.ndarray]], nascimento: dict[str, str]
) -> dict[str, dict]:
    """Percorre o acervo na ordem em que ele nasceu e conta os vetos.

    A ORDEM VEM DE UM ARQUIVO, e nao do mtime, porque o git nao guarda mtime:
    num clone novo a ordem do disco seria arbitraria e a simulacao mediria o
    sistema de arquivos.
    """
    em_ordem = sorted(
        (i for i in itens if i[1] in nascimento), key=lambda i: nascimento[i[1]]
    )
    saida = {}
    for nome, pontuar in (
        ("producao hoje", None),
        ("producao + desliza h +-2", criterio_deslizante(2)),
        ("producao + desliza h +-6", criterio_deslizante(6)),
        ("producao + desliza h +-25", criterio_deslizante(25)),
    ):
        aceitas: list[tuple[str, np.ndarray]] = []
        vetadas: list[tuple[float, str, str]] = []
        for rotulo, chave, mascara in em_ordem:
            melhor = veto_da_producao(mascara, aceitas)
            barrada_por = rotulo
            if pontuar is not None:
                for chave_j, mj in aceitas:
                    valor = pontuar(mascara, mj)
                    if valor > melhor:
                        melhor, barrada_por = valor, chave_j
            if melhor >= LIMIAR_DE_CASAMENTO:
                vetadas.append((melhor, chave[:8], rotulo))
            else:
                aceitas.append((chave, mascara))
        saida[nome] = {
            "nascidas": len(aceitas),
            "vetadas": vetadas,
        }
    return saida


def retrato_dos_recortes(itens: list[tuple[str, str, np.ndarray]]) -> dict:
    """O que as copias SAO, medido, e nao o quanto elas se parecem.

    Duas grandezas por assinatura:

    - onde comeca a faixa de 10 linhas com mais tinta. Se o recorte estivesse
      ancorado no mesmo lugar toda sessao, este numero seria quase constante;
    - quanta tinta cai FORA dessa faixa. Tinta fora da faixa do nome e texto de
      OUTRA linha da party window dentro do mesmo recorte.

    E a resposta a pergunta que a tabela dos pares levanta e nao responde: por
    que as copias da mesma pessoa nao se parecem.
    """
    inicios: dict[int, int] = {}
    sujas = 0
    for _, _, mascara in itens:
        tinta = mascara.sum(axis=1).astype(np.int64)
        total = int(tinta.sum())
        if total == 0:
            continue
        inicio = max(
            range(mascara.shape[0] - 10 + 1),
            key=lambda y: int(tinta[y : y + 10].sum()),
        )
        dentro = int(tinta[inicio : inicio + 10].sum())
        inicios[inicio] = inicios.get(inicio, 0) + 1
        if (total - dentro) / total > 0.10:
            sujas += 1
    return {"inicios": dict(sorted(inicios.items())), "sujas": sujas, "total": len(itens)}


def carregar(pasta: Path) -> tuple[list[tuple[str, str, np.ndarray]], dict[str, str]]:
    rotulos = json.loads(ROTULOS.read_text(encoding="utf-8"))
    itens = [
        (rotulos.get(chave, INDETERMINADA), chave, a.mascara)
        for chave, a in ler_assinaturas(pasta)
    ]
    itens += [(a.nome, chave, a.mascara) for chave, a in ler_calibradas()]
    return itens, json.loads(NASCIMENTO.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pasta", type=Path, default=PASTA_PADRAO)
    args = parser.parse_args()

    itens, nascimento = carregar(args.pasta)
    conhecidos = [i for i in itens if i[0] != INDETERMINADA]
    print(
        f"{len(itens)} assinaturas ({len(conhecidos)} com rotulo de campo), "
        f"limiar {LIMIAR_DE_CASAMENTO}"
    )
    print()
    cabecalho = (
        f"{'criterio':22} {'pior CERTO':>10} {'melhor ERRADO':>13} "
        f"{'margem':>7} {'certos >= limiar':>17}"
    )
    print(cabecalho)
    print("-" * len(cabecalho))
    for nome, linha in tabela_dos_pares(itens).items():
        print(
            f"{nome:22} {linha['pior_certo']:10.3f} {linha['melhor_errado']:13.3f} "
            f"{linha['margem']:7.3f} "
            f"{linha['certos_acima_do_limiar']:8}/{linha['pares_certos']:<8}"
            f"  {linha['quem_errado']}"
        )

    print()
    print("simulacao de nascimento (a que decide)")
    print("-" * 38)
    for nome, linha in simulacao_de_nascimento(itens, nascimento).items():
        print(f"{nome:26} nascidas {linha['nascidas']:3}  vetadas {len(linha['vetadas']):3}")
        for valor, chave, rotulo in linha["vetadas"]:
            print(f"    {valor:.3f}  {chave}  ({rotulo})")

    print()
    print("o que as copias SAO")
    print("-" * 19)
    retrato = retrato_dos_recortes(itens)
    print(f"    inicio da faixa do nome (linha): {retrato['inicios']}")
    print(
        f"    {retrato['sujas']} de {retrato['total']} tem mais de 10% da tinta "
        f"FORA da faixa do nome"
    )


if __name__ == "__main__":
    main()
