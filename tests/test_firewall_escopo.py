"""Firewall de escopo: nenhuma biblioteca de sintese de input na arvore.

A restricao fundadora deste projeto e uma so: **o scanner e somente leitura e
nunca envia input ao jogo.** Ela nao existe por gosto — e o que mantem o risco
de ban em zero. `requirements.txt` ja pede por escrito que ninguem adicione
`pyautogui` e companhia; este modulo transforma o pedido escrito em portao
executavel, que e a diferenca entre uma regra e um invariante.

**Por que TRES varreduras e nao uma.** Medido nesta maquina: o `pytest` deste
repo roda no Python **GLOBAL** (101 distribuicoes, pytest 9.1.1), nao no
`.venv` de producao (15 distribuicoes, sem pytest). Um
`importlib.metadata.distributions()` ingenuo dentro do teste varreria o
ambiente que roda a suite e passaria batido por um `pip install pyautogui`
feito dentro do `.venv` — o firewall ficaria verde para sempre exatamente
enquanto a violacao acontecia. Por isso: o `requirements.txt` DECLARADO, o
ambiente que roda a suite, e o `.venv` de producao via
`distributions(path=[...])`, mais uma varredura best-effort de `Requires-Dist`
que pega a transitiva DECLARADA antes mesmo de ela ser instalada.

**Como ver o vermelho com as proprias maos** (criterio de sucesso 5 da fase):

    .venv\\Scripts\\pip install keyboard
    python -m pytest tests/test_firewall_escopo.py     -> VERMELHO
    .venv\\Scripts\\pip uninstall keyboard

Instalar uma banida de verdade dentro de um teste automatizado seria cometer o
proprio pecado que o teste existe para impedir. Por isso a prova automatizada e
por MUTACAO (`test_o_detector_acusa_uma_distribuicao_banida_injetada`): sem ela,
um bug no normalizador deixaria as tres varreduras verdes para sempre e ninguem
notaria, que e o modo de falha mais caro que um controle desses tem.
"""

from __future__ import annotations

import importlib.metadata as md
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
REQUIREMENTS = RAIZ / "requirements.txt"
SITE_PACKAGES_DO_VENV = RAIZ / ".venv" / "Lib" / "site-packages"

# Onde a tabela Out of Scope vive. A mensagem de falha aponta para ca.
TABELA_FORA_DE_ESCOPO = ".planning/workstreams/mercado/REQUIREMENTS.md"

# Banlist AMPLA e nomeada, de proposito: pre-recusa a categoria inteira de
# sintese de input, nao so o exemplo citado no CLAUDE.md. Quem procura uma
# forma de "so mover o mouse uma vez" vai encontrar uma destas, e o custo de
# listar nove nomes hoje e menor que o de descobrir a decima em producao.
BANIDAS = {
    "pyautogui",
    "pydirectinput",
    "pynput",
    "keyboard",
    "mouse",
    "autoit",
    "pyautoit",
    "ahk",
    "pywinauto",
}

# Onde um nome de pacote termina numa linha de requirement.
_FIM_DO_NOME = re.compile(r"[=<>!~\[\];(,\s]")


def _normalizar(nome: str) -> str:
    """Normalizacao PEP 503: caixa baixa, `_` e `.` viram `-`.

    Sem isto, `PyAutoGUI` e `py_autogui` seriam tres nomes diferentes do mesmo
    pacote e dois deles passariam pelo firewall.
    """
    return nome.strip().lower().replace("_", "-").replace(".", "-")


def _banidas_presentes(nomes: set[str]) -> set[str]:
    """O UNICO ponto de decisao do modulo — e por isso o alvo da mutacao.

    Manter a decisao numa funcao pura e o que permite provar que o detector
    acusa sem instalar nada de verdade.
    """
    return {_normalizar(nome) for nome in nomes} & BANIDAS


def _mensagem(encontradas: set[str], onde: str) -> str:
    return (
        f"BIBLIOTECA DE SINTESE DE INPUT NA ARVORE: "
        f"{', '.join(sorted(encontradas))} (encontrada em {onde}).\n"
        f"\n"
        f"O scanner e somente leitura, nunca envia input ao jogo. Essa e a "
        f"restricao fundadora do projeto: e ela que mantem o risco de ban em "
        f"zero. Manter estas bibliotecas fora da arvore de dependencias torna "
        f"a violacao estruturalmente impossivel, em vez de apenas proibida "
        f"por escrito.\n"
        f"\n"
        f"Se voce precisa da funcionalidade que essa lib traz, ela esta na "
        f"tabela Out of Scope de {TABELA_FORA_DE_ESCOPO} — a decisao precisa "
        f"ser revisitada la, com o usuario, antes de qualquer codigo."
    )


def _nomes_de(dists: object) -> set[str]:
    nomes: set[str] = set()
    for dist in dists:  # type: ignore[attr-defined]
        try:
            nomes.add(_normalizar(dist.metadata["Name"] or ""))
        except Exception:  # noqa: BLE001 - metadado torto nao derruba a varredura
            continue
    return nomes


def _nomes_declarados_no_requirements(texto: str) -> set[str]:
    """Os nomes DECLARADOS, com os comentarios cortados primeiro.

    O corte de comentario nao e detalhe: o bloco final do `requirements.txt`
    ("NAO ADICIONE AQUI, POR DECISAO DE PROJETO") CITA os nomes banidos dentro
    de um comentario. Uma varredura que nao corta comentarios nasce vermelha
    por causa do proprio aviso que pede o contrario — e um teste que falha por
    motivo errado invalida a si mesmo.
    """
    nomes: set[str] = set()
    for linha_bruta in texto.splitlines():
        linha = linha_bruta.split("#", 1)[0].strip()
        if not linha or linha.startswith("-"):
            continue
        corte = _FIM_DO_NOME.search(linha)
        nome = linha[: corte.start()] if corte else linha
        if nome:
            nomes.add(_normalizar(nome))
    return nomes


def _requeridas_por(dists: object) -> set[str]:
    """Nomes citados em `Requires-Dist`, best-effort.

    Pega uma transitiva DECLARADA antes mesmo de ela ser instalada. O parse e
    tolerante de proposito: uma distribuicao com metadado estranho e ignorada,
    nunca derruba a varredura — esta e a rede secundaria, nao o mecanismo
    principal.
    """
    nomes: set[str] = set()
    for dist in dists:  # type: ignore[attr-defined]
        try:
            requisitos = dist.requires or []
        except Exception:  # noqa: BLE001
            continue
        for requisito in requisitos:
            try:
                texto = requisito.strip()
                corte = _FIM_DO_NOME.search(texto)
                nome = texto[: corte.start()] if corte else texto
                if nome:
                    nomes.add(_normalizar(nome))
            except Exception:  # noqa: BLE001
                continue
    return nomes


def _dists_do_venv() -> list[object]:
    return list(md.distributions(path=[str(SITE_PACKAGES_DO_VENV)]))


# -- as tres varreduras ------------------------------------------------------


def test_o_requirements_declarado_nao_pede_biblioteca_de_input() -> None:
    declarados = _nomes_declarados_no_requirements(
        REQUIREMENTS.read_text(encoding="utf-8")
    )
    assert declarados, "o requirements.txt nao declarou nenhum pacote — parse quebrado?"

    encontradas = _banidas_presentes(declarados)
    assert not encontradas, _mensagem(encontradas, "requirements.txt")


def test_o_ambiente_que_roda_a_suite_nao_tem_biblioteca_de_input() -> None:
    encontradas = _banidas_presentes(_nomes_de(md.distributions()))
    assert not encontradas, _mensagem(
        encontradas, "o ambiente Python que roda a suite de testes"
    )


def test_o_venv_de_producao_nao_tem_biblioteca_de_input() -> None:
    """A varredura que fecha o buraco: o pytest NAO roda aqui dentro."""
    if not SITE_PACKAGES_DO_VENV.is_dir():
        pytest.skip(
            f"{SITE_PACKAGES_DO_VENV} nao existe: num clone limpo ou em CI o "
            f"ambiente de producao ainda nao foi criado. As varreduras do "
            f"requirements.txt e do ambiente da suite continuam valendo, e "
            f"esta volta a valer assim que vigiar-party.bat rodar uma vez."
        )

    encontradas = _banidas_presentes(_nomes_de(_dists_do_venv()))
    assert not encontradas, _mensagem(encontradas, "o .venv de producao")


def test_nenhuma_dependencia_instalada_declara_biblioteca_de_input() -> None:
    """Transitiva DECLARADA, nos dois ambientes. Best-effort por desenho."""
    requeridas = _requeridas_por(md.distributions())
    if SITE_PACKAGES_DO_VENV.is_dir():
        requeridas |= _requeridas_por(_dists_do_venv())

    encontradas = _banidas_presentes(requeridas)
    assert not encontradas, _mensagem(
        encontradas, "o Requires-Dist de uma dependencia ja instalada"
    )


# -- o teste-do-teste --------------------------------------------------------


def test_o_detector_acusa_uma_distribuicao_banida_injetada() -> None:
    """A prova do vermelho SEM instalar nada.

    Sem este teste, um bug no normalizador (ou uma banlist vazia por acidente
    numa refatoracao) deixaria as tres varreduras acima verdes para sempre, e
    o firewall viraria teatro de controle. A mutacao acontece na entrada da
    funcao pura de decisao, nao no ambiente.
    """
    assert _banidas_presentes({"numpy", "opencv-python", "keyboard"}) == {"keyboard"}
    assert _banidas_presentes({"numpy", "opencv-python"}) == set()
    # Normalizacao PEP 503: caixa e separadores nao podem virar um buraco.
    assert _banidas_presentes({"PyAutoGUI"}) == {"pyautogui"}
    assert _banidas_presentes({"PyDirectInput"}) == {"pydirectinput"}
    assert _banidas_presentes({"PyWinAuto"}) == {"pywinauto"}
    assert _banidas_presentes({" keyboard \n"}) == {"keyboard"}


def test_a_varredura_por_path_acusa_uma_dist_info_banida_fabricada(
    tmp_path: Path,
) -> None:
    """A prova do MECANISMO, nao so do predicado — e ainda sem instalar nada.

    A mutacao acima prova que `_banidas_presentes` decide certo. Ela nao prova
    que `_nomes_de` + `distributions(path=...)` chegam a ver o que existe no
    disco — e e justamente essa metade que carrega o `.venv` de producao, onde
    o `pytest` nao roda. Um `_nomes_de` quebrado devolveria conjunto vazio e as
    tres varreduras ficariam verdes com uma banida instalada.

    Fabricar um `dist-info` num tmp_path exercita o caminho inteiro com o
    mesmo mecanismo que le o `.venv`, sem cometer o pecado de instalar uma
    biblioteca de input de verdade.
    """
    dist_info = tmp_path / "keyboard-0.13.5.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: keyboard\nVersion: 0.13.5\n",
        encoding="utf-8",
    )

    nomes = _nomes_de(md.distributions(path=[str(tmp_path)]))

    assert nomes == {"keyboard"}, (
        "a varredura por path nao enxergou a distribuicao fabricada — o "
        "mecanismo que cobre o .venv de producao esta quebrado"
    )
    assert _banidas_presentes(nomes) == {"keyboard"}


def test_a_mensagem_de_falha_explica_o_porque() -> None:
    """Uma falha que so diz "keyboard encontrado" convida a contornar o teste.

    Quem esbarra neste portao daqui a seis meses precisa ler, na propria
    falha, por que ele existe e onde a decisao mora.
    """
    texto = _mensagem({"keyboard"}, "o .venv")

    assert "keyboard" in texto
    assert "somente leitura" in texto
    assert "nunca envia input ao jogo" in texto
    assert TABELA_FORA_DE_ESCOPO in texto
    assert "REQUIREMENTS.md" in texto


def test_o_bloco_de_aviso_do_requirements_continua_no_lugar() -> None:
    """O texto-fonte da mensagem mora no `requirements.txt`.

    Ele tambem e a armadilha da varredura declarada: cita os nomes banidos
    dentro de um comentario. Se alguem apagar o bloco, o corte de comentarios
    deixa de ser exercitado por dados reais e o teste acima passa a provar
    menos do que promete.
    """
    texto = REQUIREMENTS.read_text(encoding="utf-8")

    assert "NAO ADICIONE AQUI" in texto
    assert "pyautogui" in texto.lower()
    # E a prova de que o corte de comentarios funciona: os nomes estao la, no
    # comentario, e mesmo assim a varredura declarada passa verde.
    assert not _banidas_presentes(_nomes_declarados_no_requirements(texto))
