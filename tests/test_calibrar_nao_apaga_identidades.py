"""O `calibrar.bat` nao pode alcancar o acervo de identidades.

O INCIDENTE QUE DA NOME A ESTE ARQUIVO, medido em campo em 2026-08-30
(WINDOWS #13): uma rodada de `calibrar.bat` apagou do `calibration.json` os 13
moldes de glifo e as 3 ancoras do painel de mercado. Cada molde e um arrasto de
mouse mais um rotulo digitado pela mao do usuario; o arquivo e gitignored, entao
nao ha `git checkout` que os traga de volta. O resgate foi manual
(`calibration.RESGATE-13-glifos.json`).

O QUE SEPARA ESTE ARQUIVO DO IRMAO `tests/test_calibrar_nao_apaga_mercado.py`

O irmao afirma que a party PRESERVA o que nao e dela dentro do MESMO arquivo.
Este afirma outra coisa, e mais forte: que existe um lugar que o caminho de
escrita NAO ALCANCA. `CAMPOS_DA_PARTY` inclui `assinaturas`, entao o conserto de
subtracao do irmao nao protege assinatura nenhuma — e corretamente, porque a
party as possui. Uma assinatura aprendida dentro do `calibration.json` nao
morreria por bug; morreria por DESENHO, toda vez que alguem recalibrasse. A
separacao em `.identidades/` (D-04) e a unica defesa, e um teste que so afirmasse
"a pasta e outra" seria uma REPETICAO da decisao, e nao uma prova dela.

Por isso este arquivo RODA a rodada. Com entradas de verdade na pasta, pelo
caminho de verdade, olhando o disco depois — byte a byte.

DISCIPLINA INEGOCIAVEL, COPIADA DO IRMAO: todo caso monkeypatcha
`l2scanner.calibrar.ARQUIVO_CALIBRACAO` para dentro de `tmp_path`, mais
`ler_personagem_do_jogo`, `listar_janelas_do_jogo`, `janela_que_contem`,
`achar_barra_do_proprio` e `conferir_visualmente`. Sem eles a suite le a
configuracao da maquina de quem a roda e, pior, pode reproduzir o incidente
dentro do CI — desta vez sem resgate. NAO REMOVA.

A GUARDA CONTRA PROVA VAZIA, e por que ela e metade deste arquivo: uma rodada
que abortasse cedo deixaria a pasta intacta e passaria como prova de
sobrevivencia sem nunca ter chegado perto de gravar nada. Entao todo caso que
afirma "o acervo sobreviveu" afirma TAMBEM que `cal.nomes` e `cal.assinaturas`
foram reescritos — os dois campos que a party POSSUI — exatamente como sao hoje.
"""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import fields
from pathlib import Path

import cv2
import numpy as np
import pytest

import l2scanner.calibrar
from l2scanner.acervo import PREFIXO_ASSINATURA, PREFIXO_NOME, chave_da_assinatura
from l2scanner.calibracao import Calibracao
from l2scanner.identidade import Assinatura, criar_assinatura
from l2scanner.visao import _recorte_do_nome

RAIZ = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "identidade"

# A ORDEM DAS LINHAS DA FIXTURE. E ela que passamos em `--nomes`, para que cada
# recorte caia sobre o nome que ele de fato mostra e a rodada produza assinaturas
# REAIS — nao avisos de "quase nenhum texto no recorte".
NOMES_DA_FIXTURE = ["Korzis", "J4guar", "Kaus", "TioMad"]

# O PNG da fixture E a party window inteira (shape 522x174x3, e
# `party_window = {esquerda: 1738, topo: 325, largura: 174, altura: 522}`).
#
# Entao `capturar_tela` tem de devolver a imagem com ESTES offsets: o bloco de
# `--nomes` recorta `pixels[pw.topo - oy : ..., pw.esquerda - ox : ...]`, e
# 325 - 325 = 0 e 1738 - 1738 = 0 fazem `janela_px` cair exatamente sobre a
# imagem. Com qualquer outro offset o recorte sai fora e `cal.assinaturas` volta
# vazio — e a guarda contra prova vazia nao teria o que afirmar.
OFFSET_X = 1738
OFFSET_Y = 325

# As palavras que nomeariam um campo do acervo dentro da `Calibracao`.
#
# `assinaturas` NAO esta aqui de proposito: ela E um campo da party, e a party a
# possui. O que nao pode existir e um campo que aponte para a PASTA.
TERMOS_DO_ACERVO = frozenset({"acervo", "identidades", "pasta_identidades"})

# Quem grava uma `Calibracao` em disco. Os modulos de CALIBRACAO, e mais
# ninguem: o laco do scanner LE o arquivo e nunca o reescreve.
#
# `calibrar_renda_moldes.py` entrou em 2026-09-02 (plano 01-05 da renda), e o
# portao FEZ o que existe para fazer: ele quebrou, e o escritor novo passou por
# olhos humanos antes de ser admitido. O que foi conferido, e por que ele e
# admissivel:
#
#   - ele carrega com `Calibracao.carregar` na primeira linha util, muta SO
#     `renda_moldes_da_barra` e reemite tudo (`gravar_os_moldes`), que e o molde
#     literal de `calibrar.py:1188` e `:1234-1236`;
#   - ele nao nomeia a chave de digitos do mercado em lugar nenhum do fonte, e
#     ha teste afirmando que aquela chave volta identica depois de uma rodada,
#     com os 13 moldes contados ANTES da comparacao;
#   - ele nao conhece o acervo, que e o que o caso abaixo confere de verdade.
#
# `calibrar_renda.py` ENTROU AQUI EM 2026-09-02, e a inscricao e o portao
# funcionando e nao o portao sendo afrouxado: ele existe justamente para que um
# escritor novo do `calibration.json` passe por olhos humanos, porque foi um
# escritor que apagou 13 moldes de glifo em 2026-08-30. O que se conferiu antes
# de inscreve-lo:
#
#   - ele CARREGA o arquivo inteiro na primeira linha util e muta so a entrada
#     do personagem dentro de `renda_por_personagem` (mais `cal.janela`, o
#     emprestimo que o `calibrar_tiat` ja faz);
#   - a mutacao e por COPIA COM SUBSTITUICAO da chave do personagem, e nunca por
#     reconstrucao do dicionario;
#   - `tests/test_calibrar_renda_nao_apaga_nada.py` prende as duas coisas, com
#     controle positivo e com o caso do PERSONAGEM VIZINHO;
#   - ele NAO importa o acervo, entao a interseccao que o caso abaixo exige
#     continua vazia.
MODULOS_QUE_GRAVAM = frozenset(
    {"calibrar.py", "calibrar_mercado.py", "calibrar_renda.py", "calibrar_renda_moldes.py"}
)


@pytest.fixture
def pixels() -> np.ndarray:
    px = cv2.imread(str(FIXTURES / "party_ordem_original.png"), cv2.IMREAD_COLOR)
    assert px is not None, "fixture da party nao pode ser lida"
    return px


def _calibracao_da_fixture() -> Calibracao:
    """A geometria real da fixture, com `nomes` e `assinaturas` ZERADOS.

    A rodada os regrava — e disso que a guarda contra prova vazia trata. Zerar
    aqui e o que impede o teste de confundir "a rodada gravou" com "o arquivo ja
    vinha assim".
    """
    cal = Calibracao.carregar(FIXTURES / "calibracao.json")
    cal.nomes = []
    cal.assinaturas = []
    return cal


def _assinatura_da_linha(px: np.ndarray, cal: Calibracao, indice: int) -> Assinatura:
    recorte = _recorte_do_nome(px, cal, indice)
    assert recorte is not None
    return criar_assinatura("", recorte)


def _semear_acervo(pasta: Path, px: np.ndarray) -> dict[str, bytes]:
    """Escreve quatro entradas A MAO e devolve o retrato da pasta.

    ESCRITAS A MAO, NUNCA POR `AcervoDeIdentidades.gravar`: esta fase prova que
    uma entrada posta a mao se comporta certo, e o semeador nao pode depender do
    codigo que ele existe para vigiar.

    Duas ganham o irmao `nome_<chave>` e duas ficam anonimas, porque as anonimas
    sao as mais frageis do acervo: elas tem `nome: ""`, e sao exatamente as que
    morreriam junto com `cal.assinaturas` se algum dia a fusao em memoria vazasse
    para o arquivo.
    """
    pasta.mkdir(parents=True, exist_ok=True)
    cal = Calibracao.carregar(FIXTURES / "calibracao.json")
    for indice in range(4):
        assinatura = _assinatura_da_linha(px, cal, indice)
        chave = chave_da_assinatura(assinatura)
        corpo = assinatura.como_dict()
        corpo.pop("nome", None)
        (pasta / f"{PREFIXO_ASSINATURA}{chave}.json").write_text(
            json.dumps(corpo), encoding="utf-8"
        )
        if indice < 2:
            (pasta / f"{PREFIXO_NOME}{chave}").write_text(
                NOMES_DA_FIXTURE[indice], encoding="utf-8"
            )
    return _retrato(pasta)


def _retrato(pasta: Path) -> dict[str, bytes]:
    """Nome de arquivo E bytes de cada um.

    Comparar BYTES, e nunca contagem: uma rodada que reescrevesse uma entrada com
    o mesmo nome de arquivo e conteudo diferente passaria numa comparacao de
    contagem, e e exatamente esse o desfecho que corrompe uma identidade em
    silencio.
    """
    return {c.name: c.read_bytes() for c in sorted(pasta.iterdir())}


def _dirigir(monkeypatch, alvo: Path, argv: list[str], px: np.ndarray) -> int:
    """Roda o `main()` de verdade, com o disco preso a `tmp_path`."""
    # ESTA LINHA E O QUE MANTEM O calibration.json REAL FORA DO ALCANCE DA
    # SUITE. Sem ela, esta suite reproduz o incidente de 2026-08-30 dentro do
    # CI, apagando os moldes de glifo da maquina de quem rodar os testes.
    # NAO REMOVA.
    monkeypatch.setattr(l2scanner.calibrar, "ARQUIVO_CALIBRACAO", alvo)

    # A MIRA DA JANELA, NEUTRALIZADA: sem isto estes casos passariam a ler o
    # `config.toml` da maquina de quem os roda e a tentar abrir uma janela de
    # jogo de verdade. Um teste que le a configuracao da maquina de quem o roda
    # nao esta afirmando nada.
    monkeypatch.setattr(
        l2scanner.calibrar, "ler_personagem_do_jogo", lambda *a, **k: None
    )
    monkeypatch.setattr(
        l2scanner.calibrar, "listar_janelas_do_jogo", lambda *a, **k: []
    )

    monkeypatch.setattr(
        l2scanner.calibrar, "capturar_tela", lambda: (px, OFFSET_X, OFFSET_Y)
    )
    monkeypatch.setattr(
        l2scanner.calibrar,
        "calibrar_automatico",
        lambda *a, **k: _calibracao_da_fixture(),
    )
    monkeypatch.setattr(
        l2scanner.calibrar,
        "calibrar_selecionando",
        lambda *a, **k: _calibracao_da_fixture(),
    )
    monkeypatch.setattr(l2scanner.calibrar, "janela_que_contem", lambda *a, **k: None)
    monkeypatch.setattr(
        l2scanner.calibrar, "achar_barra_do_proprio", lambda *a, **k: None
    )
    # Grava PNG na RAIZ do repositorio e nada tem a dizer sobre a invariante.
    monkeypatch.setattr(
        l2scanner.calibrar, "conferir_visualmente", lambda *a, **k: None
    )
    monkeypatch.setattr(sys, "argv", ["l2scanner.calibrar", *argv])
    return l2scanner.calibrar.main()


def _afirmar_que_a_rodada_aconteceu(alvo: Path) -> None:
    """GUARDA CONTRA PROVA VAZIA — os dois campos que a party POSSUI.

    Sem esta afirmacao, uma rodada que abortasse cedo (recorte fora da janela,
    `calibrar_automatico` devolvendo None, argumento mal formado) deixaria a
    pasta do acervo intacta e passaria como prova de sobrevivencia. A pasta ficar
    igual so significa alguma coisa quando o `calibration.json` mudou.
    """
    depois = json.loads(alvo.read_text(encoding="utf-8"))

    assert depois["nomes"] == NOMES_DA_FIXTURE, (
        "a rodada nao gravou os nomes de --nomes; ela nao chegou onde o teste "
        f"precisa. Saiu: {depois['nomes']}"
    )
    assert len(depois["assinaturas"]) == 4, (
        "a rodada nao regravou as 4 assinaturas de party; provavelmente o "
        "recorte caiu fora da janela ou o texto ficou abaixo de "
        f"PIXELS_MINIMOS_DE_TEXTO. Saiu: {len(depois['assinaturas'])}"
    )
    for gravada, nome in zip(depois["assinaturas"], NOMES_DA_FIXTURE):
        assert gravada["nome"] == nome
        assert gravada["altura"] > 0
        assert gravada["largura"] > 0
        assert gravada["bits"]


class TestUmaRodadaDeVerdadeNaoEncostaNoAcervo:
    """O criterio 1 da Fase 1 (DURA-01), provado por EXECUCAO.

    Nao por leitura de codigo, nao por "a pasta e outra": a rodada acontece, com
    o acervo cheio, e o disco e conferido depois.
    """

    def test_auto_com_nomes_deixa_o_acervo_byte_a_byte_igual(
        self, monkeypatch, tmp_path, pixels
    ):
        alvo = tmp_path / "calibration.json"
        acervo = tmp_path / ".identidades"
        antes = _semear_acervo(acervo, pixels)
        assert len(antes) == 6, "premissa: 4 assinaturas mais 2 irmaos de nome"

        rc = _dirigir(
            monkeypatch,
            alvo,
            ["--auto", "--nomes", ",".join(NOMES_DA_FIXTURE)],
            pixels,
        )
        assert rc == 0

        _afirmar_que_a_rodada_aconteceu(alvo)

        depois = _retrato(acervo)
        assert depois == antes, (
            "uma rodada de calibrar.bat ALCANCOU o acervo de identidades. "
            "Diferenca: "
            + str(sorted(set(antes) ^ set(depois)))
            + " | conteudo alterado: "
            + str(sorted(n for n in set(antes) & set(depois) if antes[n] != depois[n]))
        )

    def test_selecionar_passa_pelo_mesmo_portao(self, monkeypatch, tmp_path, pixels):
        """`--selecionar` delega para o mesmo `cal.salvar` — mesmo caminho."""
        alvo = tmp_path / "calibration.json"
        acervo = tmp_path / ".identidades"
        antes = _semear_acervo(acervo, pixels)

        rc = _dirigir(
            monkeypatch,
            alvo,
            ["--selecionar", "--nomes", ",".join(NOMES_DA_FIXTURE)],
            pixels,
        )
        assert rc == 0

        _afirmar_que_a_rodada_aconteceu(alvo)
        assert _retrato(acervo) == antes

    def test_com_o_calibration_json_JA_no_disco_o_acervo_continua_intocado(
        self, monkeypatch, tmp_path, pixels
    ):
        """A rodada que passa pela FUSAO, e nao pelo atalho do arquivo ausente.

        `fundir_com_a_calibracao_em_disco` devolve `nova` sem ler nada quando o
        arquivo nao existe. Uma rodada sobre disco VAZIO nunca exercita o ramo em
        que a fusao de fato carrega e copia campos — e e nesse ramo que um
        conserto futuro poderia, sem querer, arrastar o acervo para dentro do
        arquivo.
        """
        alvo = tmp_path / "calibration.json"
        acervo = tmp_path / ".identidades"

        # Primeira rodada: cria o arquivo.
        assert _dirigir(monkeypatch, alvo, ["--auto"], pixels) == 0
        assert alvo.exists()

        antes = _semear_acervo(acervo, pixels)

        # Segunda rodada: agora COM o arquivo no disco, entao a fusao carrega.
        rc = _dirigir(
            monkeypatch,
            alvo,
            ["--auto", "--nomes", ",".join(NOMES_DA_FIXTURE)],
            pixels,
        )
        assert rc == 0

        _afirmar_que_a_rodada_aconteceu(alvo)
        assert _retrato(acervo) == antes

    def test_o_acervo_inexistente_nao_quebra_a_rodada_e_nao_e_criado(
        self, monkeypatch, tmp_path, pixels
    ):
        """A pasta e do SCANNER, nao do calibrador.

        O calibrador nao a le, nao a escreve e nao a cria. Se ele passasse a
        cria-la, ele teria adquirido uma opiniao sobre ela — e uma opiniao e o
        primeiro passo para uma escrita.
        """
        alvo = tmp_path / "calibration.json"
        acervo = tmp_path / ".identidades"
        assert not acervo.exists()

        rc = _dirigir(
            monkeypatch,
            alvo,
            ["--auto", "--nomes", ",".join(NOMES_DA_FIXTURE)],
            pixels,
        )
        assert rc == 0

        _afirmar_que_a_rodada_aconteceu(alvo)
        assert not acervo.exists(), (
            "o calibrador criou a pasta do acervo; ele nao tem nada a fazer la"
        )


class TestAGarantiaEEstrutural:
    """Nao ha CAMPO por onde `cal.salvar` alcance o acervo.

    A rodada acima prova o comportamento de hoje. Estes dois casos provam que o
    comportamento nao depende de sorte: nao existe caminho.
    """

    def test_nenhum_campo_da_calibracao_e_do_acervo(self):
        """Afirmado por igualdade de CONJUNTOS, e em forma positiva.

        `assinaturas` nao entra no vocabulario de proposito: ela E um campo da
        party e a party a possui. O que nao pode existir e um campo que aponte
        para a PASTA — porque um campo assim entraria no dict de `salvar` e o
        acervo passaria a ser reescrito junto com o resto.
        """
        campos = {f.name for f in fields(Calibracao)}
        assert campos, "premissa: a dataclass tem campos"

        do_acervo = campos & TERMOS_DO_ACERVO
        assert do_acervo == frozenset(), (
            "a Calibracao ganhou um campo do acervo, e com ele um caminho por "
            "onde `cal.salvar` reescreve a pasta: " + str(sorted(do_acervo))
        )

    def test_quem_grava_a_calibracao_nao_conhece_o_acervo(self):
        """Interseccao vazia entre os dois conjuntos, ambos lidos da arvore.

        Este caso NAO envelhece com a Fase 2. Ela vai fazer o laco do scanner
        aprender assinaturas, entao mais modulos vao importar o acervo — e nenhum
        deles vai gravar `calibration.json`. O que este portao proibe e a
        SOBREPOSICAO: um modulo que grava a calibracao E conhece a pasta e um
        modulo a uma linha de distancia de gravar a pasta tambem.
        """
        gravam = _modulos_que_gravam_calibracao()
        conhecem = _modulos_que_importam_o_acervo()

        assert gravam == MODULOS_QUE_GRAVAM, (
            "o conjunto de quem grava uma Calibracao mudou. Isso nao e "
            "necessariamente errado — mas um escritor novo do calibration.json "
            "precisa de olhos humanos, porque foi um escritor que apagou 13 "
            f"moldes de glifo em 2026-08-30. Achado: {sorted(gravam)}"
        )
        assert conhecem, "premissa: alguem conhece o acervo"
        assert gravam & conhecem == frozenset(), (
            "um modulo grava a calibracao E conhece o acervo: "
            + str(sorted(gravam & conhecem))
        )


class TestOLacoDoScannerNaoRegravaACalibracao:
    """O portao que prende a fusao em memoria dentro da memoria (T-01-08).

    O plano 01-01 funde as assinaturas do acervo em `cal.assinaturas` EM
    MEMORIA. Se algum dia algo no laco gravar essa `Calibracao`, as entradas do
    acervo entram no arquivo que o `calibrar.bat` reescreve — inclusive as
    ANONIMAS, que viram `{"nome": ""}` la dentro — e D-04 e desfeito pelo lado de
    DENTRO, sem ninguem mexer no `.identidades/`.
    """

    def test_so_os_modulos_de_calibracao_chamam_salvar(self):
        assert _modulos_que_gravam_calibracao() == MODULOS_QUE_GRAVAM

    @pytest.mark.parametrize("modulo", ["__main__.py", "sessao.py", "visao.py"])
    def test_o_laco_esta_do_lado_de_fora(self, modulo):
        """Consequencia da igualdade acima, dita com nome e sobrenome.

        Ela nao acrescenta forca — acrescenta a MENSAGEM: quem quebrar isto le
        exatamente qual modulo do laco passou a gravar.
        """
        assert modulo not in MODULOS_QUE_GRAVAM
        assert modulo not in _modulos_que_gravam_calibracao()

    def test_o_detector_acusa_um_caso_plantado(self):
        """GUARDA CONTRA PROVA VAZIA do proprio detector.

        Um detector quebrado devolveria conjunto vazio e a igualdade la em cima
        falharia — mas a igualdade e com um conjunto NAO vazio justamente para
        isso. Este caso fecha o outro lado: o detector realmente reconhece uma
        chamada.
        """
        plantado = "def tick(self):\n    self.cal.salvar(ARQUIVO)\n"
        assert _chama_salvar(plantado)

    def test_a_prosa_de_docstring_nao_conta_como_chamada(self):
        """A licao do plano 01-01, repetida aqui porque a armadilha e a mesma.

        Um portao TEXTUAL acusaria a documentacao que protege a regra. A leitura
        e da arvore sintatica: prosa que explica `salvar` nao e uma chamada a
        `salvar`.
        """
        so_prosa = (
            '"""Este modulo NAO chama cal.salvar(caminho) em lugar nenhum."""\n'
            "# nem mesmo aqui: cal.salvar(caminho)\n"
            "def tick(self):\n    return None\n"
        )
        assert not _chama_salvar(so_prosa)


def _chama_salvar(fonte: str) -> bool:
    """Alguem chama `.salvar(...)` neste texto?

    LIDO DA ARVORE SINTATICA, e nao do texto com os comentarios removidos. Os
    comentarios sao so metade do problema: em 2026-08-31, no plano 01-01, um
    portao textual acusou tres modulos que citavam o acervo em PROSA DE
    DOCSTRING — e docstring nao e linha de comentario, entao remove-las nao
    resolveria. A arvore nao tem esse problema por construcao.
    """
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute):
            if no.func.attr == "salvar":
                return True
    return False


def _modulos_que_gravam_calibracao() -> frozenset[str]:
    achados = set()
    for caminho in sorted((RAIZ / "l2scanner").glob("*.py")):
        if _chama_salvar(caminho.read_text(encoding="utf-8")):
            achados.add(caminho.name)
    return frozenset(achados)


def _modulos_que_importam_o_acervo() -> frozenset[str]:
    achados = {"acervo.py"}  # quem define o modulo
    for caminho in sorted((RAIZ / "l2scanner").glob("*.py")):
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.ImportFrom) and no.module == "acervo":
                achados.add(caminho.name)
            elif isinstance(no, ast.Import):
                if any(a.name.split(".")[-1] == "acervo" for a in no.names):
                    achados.add(caminho.name)
    return frozenset(achados)
