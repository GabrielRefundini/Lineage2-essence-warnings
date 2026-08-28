"""O portao do SPIKE-RESPOSTAS.md -- que ate agora nao tinha um unico teste.

O irmao dele, `tools/conferir_gravacoes_do_spike.py`, tem
`tests/test_conferir_gravacoes_do_spike.py`. Este nao tinha nada, e ele decide
se as 9 respostas que sustentam a grade, os glifos e a forma da ancora se
sustentam.

Foi assim que o defeito mais caro possivel neste arquivo sobreviveu: `Secao.selos`
procurava os selos por substring comecando por `VERIFICADO`, entao

    "NAO VERIFICADO em campo -- nao deu tempo."

devolvia `['VERIFICADO']`. Uma resposta que o usuario REBAIXOU virava um selo
POSITIVO, passava na conferencia de "exatamente um selo", passava a exigir um
frame (qualquer um que existisse servia) e saia impressa como `VERIFICADO` na
tabela final -- que e a saida que um leitor futuro usa como resumo. Num arquivo
cujo proposito declarado e "que a mesma mentira nao volte pela porta da
analise", promover um selo negativo a positivo e o modo de falha exato que ele
existe para impedir.

Um unico teste com o texto `NAO VERIFICADO` teria pego. Ele esta aqui agora,
junto dos outros comportamentos que os comentarios do modulo descrevem como
resultado de teste por mutacao -- mutacao feita a mao, que nunca ficou presa.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.conferir_spike_respostas import (
    Problema,
    Secao,
    conferir,
    conferir_a_numeracao,
    conferir_a_secao,
    evidencia_resolvida,
    separar_secoes,
)

LEGENDA = """\
# SPIKE-RESPOSTAS

## Legenda dos selos

| Selo | Significa |
|---|---|
| VERIFICADO | eu vi no frame citado |
| PARCIAL | eu vi, mas so numa aba |
| NAO RESPONDIDO | o frame nao mostra |
"""


def _secao(texto: str, numero: int = 1, nivel: int = 2) -> Secao:
    """Uma `Secao` isolada, para afirmar sobre `selos` sem montar documento."""
    s = Secao(numero, f"## {numero}. teste", 1, nivel)
    s.corpo = texto.splitlines()
    return s


def _documento(corpos: list[str]) -> str:
    """Um documento com legenda + N secoes numeradas a partir de 1."""
    partes = [LEGENDA]
    for i, corpo in enumerate(corpos, start=1):
        partes.append(f"\n## {i}. pergunta {i}\n\n{corpo}\n")
    return "".join(partes)


@pytest.fixture
def raiz_com_frame(tmp_path: Path) -> Path:
    """Uma arvore com UM frame de verdade, e um arquivo fora de `recordings/`."""
    pasta = tmp_path / "recordings" / "20260828-060622-mercado-pagina-cheia"
    pasta.mkdir(parents=True)
    (pasta / "frame_000010.png").write_bytes(b"png de mentira")
    (tmp_path / "l2scanner").mkdir()
    (tmp_path / "l2scanner" / "visao.py").write_text("# fora de recordings")
    return tmp_path


FRAME_BOM = "recordings/20260828-060622-mercado-pagina-cheia/frame_000010.png"


class TestOSeloNegado:
    """CR-05: `NAO VERIFICADO` nao pode contar como `VERIFICADO`."""

    @pytest.mark.parametrize(
        "texto",
        [
            "**Selo: NAO VERIFICADO** em campo -- nao deu tempo.",
            "Isto ficou NAO VERIFICADO ate hoje.",
            "**Selo: NAO PARCIAL**",
        ],
        ids=["nao-verificado-selo", "nao-verificado-frase", "nao-parcial"],
    )
    def test_a_negacao_explicita_vira_o_selo_mais_fraco(self, texto: str):
        assert _secao(texto).selos == ["NAO RESPONDIDO"], (
            f"{texto!r} foi lido como selo POSITIVO. Uma resposta que o usuario "
            f"rebaixou a mao seria promovida de volta, e a tabela final "
            f"imprimiria VERIFICADO para ela."
        )

    def test_a_negacao_com_acento_tambem_conta(self):
        """O usuario escreve `NAO` com til; o portao nao pode punir isso."""
        assert _secao("Selo: NÃO VERIFICADO").selos == ["NAO RESPONDIDO"]

    def test_uma_secao_negada_NAO_passa_a_exigir_frame(self, raiz_com_frame: Path):
        """A cascata inteira: sem o fix, a secao virava positiva e pedia frame.

        Com o selo lido certo, ela e `NAO RESPONDIDO` -- que e o selo honesto
        para uma pergunta que a gravacao nao responde, e nao precisa de
        evidencia.
        """
        secao = _secao("**Selo: NAO VERIFICADO** -- faltou gravar de perto.")

        selo, confirmados, faltando = conferir_a_secao(secao, raiz_com_frame)

        assert selo == "NAO RESPONDIDO"
        assert (confirmados, faltando) == (0, [])

    def test_o_selo_positivo_de_verdade_continua_positivo(self):
        """A guarda nao pode virar 'nunca aprova nada'."""
        assert _secao("**Selo: VERIFICADO**").selos == ["VERIFICADO"]
        assert _secao("**Selo: PARCIAL**").selos == ["PARCIAL"]


class TestAContagemDeSelos:
    def test_zero_selos_e_uma_resposta_sem_compromisso(self, raiz_com_frame: Path):
        with pytest.raises(Problema, match="nao tem selo"):
            conferir_a_secao(_secao("uma resposta sem selo nenhum"), raiz_com_frame)

    def test_dois_selos_sao_recusados_e_os_dois_sao_nomeados(
        self, raiz_com_frame: Path
    ):
        secao = _secao("**Selo: VERIFICADO**\n\nmas na verdade PARCIAL")
        with pytest.raises(Problema) as erro:
            conferir_a_secao(secao, raiz_com_frame)
        assert "2 selos" in str(erro.value)
        assert "VERIFICADO" in str(erro.value) and "PARCIAL" in str(erro.value)

    def test_o_mesmo_selo_duas_vezes_tambem_e_erro(self, raiz_com_frame: Path):
        secao = _secao("**Selo: VERIFICADO**\n\nrepetindo: VERIFICADO")
        with pytest.raises(Problema, match="2 selos"):
            conferir_a_secao(secao, raiz_com_frame)


class TestOSeloPositivoPrecisaDeFrame:
    def test_positivo_sem_frame_nenhum_e_recusado(self, raiz_com_frame: Path):
        secao = _secao("**Selo: VERIFICADO**\n\nsao 10 linhas, eu lembro.")
        with pytest.raises(Problema) as erro:
            conferir_a_secao(secao, raiz_com_frame)
        assert "nao cita nenhum frame" in str(erro.value)

    def test_positivo_com_frame_que_nao_existe_e_apontado(
        self, raiz_com_frame: Path
    ):
        secao = _secao(
            "**Selo: VERIFICADO**\n\n`recordings/nao-existe/frame_000099.png`"
        )
        _selo, confirmados, faltando = conferir_a_secao(secao, raiz_com_frame)
        assert confirmados == 0
        assert faltando == ["recordings/nao-existe/frame_000099.png"]

    def test_positivo_com_frame_que_existe_passa(self, raiz_com_frame: Path):
        secao = _secao(f"**Selo: VERIFICADO**\n\n`{FRAME_BOM}`")
        selo, confirmados, faltando = conferir_a_secao(secao, raiz_com_frame)
        assert (selo, confirmados, faltando) == ("VERIFICADO", 1, [])


class TestAResolucaoDeEvidencia:
    """WR-02: o prefixo `recordings/` NAO garante que o caminho fique na arvore."""

    def test_um_caminho_com_dois_pontos_e_recusado_mesmo_existindo(
        self, raiz_com_frame: Path
    ):
        fugitivo = "recordings/../l2scanner/visao.py"
        assert (raiz_com_frame / fugitivo).exists(), (
            "o proprio teste precisa que o alvo EXISTA -- senao ele passaria "
            "por acidente e nao provaria nada"
        )
        assert not evidencia_resolvida(raiz_com_frame, fugitivo), (
            "um caminho que sai da arvore de gravacoes foi resolvido, mas nao e "
            "evidencia de spike nenhum"
        )

    def test_um_DIRETORIO_com_nome_de_png_nao_e_evidencia(self, tmp_path: Path):
        """O modo de falha deterministico dos testes deste projeto.

        `.exists()` aceitava; `is_file()` nao. Mesma escolha, pelo mesmo motivo,
        que ja foi feita a mao em `__main__.py`.
        """
        (tmp_path / "recordings" / "x" / "frame_000012.png").mkdir(parents=True)
        assert not evidencia_resolvida(
            tmp_path, "recordings/x/frame_000012.png"
        )

    def test_um_arquivo_de_verdade_e_evidencia(self, raiz_com_frame: Path):
        assert evidencia_resolvida(raiz_com_frame, FRAME_BOM)


class TestOsCabecalhos:
    def test_a_legenda_NAO_entra_na_contagem(self):
        """Ela tem as tres palavras de selo e satisfaria a conferencia 2 sozinha."""
        secoes = separar_secoes(_documento(["**Selo: VERIFICADO**"]))
        assert [s.numero for s in secoes] == [1], (
            "a legenda (cabecalho NAO numerado) foi contada como resposta"
        )

    def test_um_numero_pulado_e_recusado(self):
        secoes = [
            Secao(n, f"## {n}.", n, 2) for n in (1, 2, 3, 4, 5, 6, 7, 8, 10)
        ]
        with pytest.raises(Problema) as erro:
            conferir_a_numeracao(secoes)
        assert "10" in str(erro.value)

    def test_faltar_uma_secao_e_recusado(self):
        with pytest.raises(Problema, match="8 secao"):
            conferir_a_numeracao([Secao(n, "", n, 2) for n in range(1, 9)])

    def test_nove_secoes_em_ordem_passam(self):
        conferir_a_numeracao([Secao(n, "", n, 2) for n in range(1, 10)])

    def test_um_subcabecalho_NAO_encerra_a_secao(self):
        """A resposta 8 real tem sub-secoes `###`; elas pertencem a ela.

        Encerrar em QUALQUER cabecalho partia a secao e produzia duas
        reprovacoes FALSAS: 'nao tem selo' e 'nao cita frame'.
        """
        documento = _documento(
            ["texto\n\n### detalhe\n\n**Selo: VERIFICADO**\n\n`" + FRAME_BOM + "`"]
        )
        (secao,) = separar_secoes(documento)
        assert secao.selos == ["VERIFICADO"]
        assert secao.frames == [FRAME_BOM]


class TestOPortaoInteiro:
    """Ponta a ponta, pelo `conferir()` -- codigo de saida e tudo."""

    def _nove(self, corpo_da_primeira: str) -> list[str]:
        outras = [f"**Selo: VERIFICADO**\n\n`{FRAME_BOM}`"] * 8
        return [corpo_da_primeira] + outras

    def test_um_documento_que_se_sustenta_aprova(
        self, tmp_path: Path, raiz_com_frame: Path
    ):
        doc = tmp_path / "SPIKE.md"
        doc.write_text(
            _documento(self._nove(f"**Selo: VERIFICADO**\n\n`{FRAME_BOM}`")),
            encoding="utf-8",
        )
        assert conferir(doc, raiz_com_frame) == 0

    def test_uma_secao_NEGADA_nao_derruba_o_portao_nem_vira_VERIFICADO(
        self, tmp_path: Path, raiz_com_frame: Path, capsys
    ):
        """O desfecho que CR-05 corrompia: a linha impressa na tabela final."""
        doc = tmp_path / "SPIKE.md"
        doc.write_text(
            _documento(
                self._nove("**Selo: NAO VERIFICADO** -- faltou gravar de perto.")
            ),
            encoding="utf-8",
        )

        assert conferir(doc, raiz_com_frame) == 0

        linhas = capsys.readouterr().out.splitlines()
        (linha_da_1,) = [ln for ln in linhas if ln.strip().startswith("1 ")]
        assert "NAO RESPONDIDO" in linha_da_1, (
            f"a tabela final imprimiu {linha_da_1!r} para uma secao que o "
            f"usuario rebaixou escrevendo NAO VERIFICADO"
        )

    def test_um_frame_inventado_reprova_com_o_caminho_nomeado(
        self, tmp_path: Path, raiz_com_frame: Path, capsys
    ):
        doc = tmp_path / "SPIKE.md"
        doc.write_text(
            _documento(
                self._nove(
                    "**Selo: VERIFICADO**\n\n"
                    "`recordings/20260827-1200-mercado-aberto/frame_000012.png`"
                )
            ),
            encoding="utf-8",
        )

        assert conferir(doc, raiz_com_frame) == 1
        assert "frame_000012.png" in capsys.readouterr().err

    def test_um_caminho_com_dois_pontos_reprova_o_documento(
        self, tmp_path: Path, raiz_com_frame: Path
    ):
        """O portao inteiro era satisfeito por `recordings/../qualquer/coisa`."""
        doc = tmp_path / "SPIKE.md"
        doc.write_text(
            _documento(
                self._nove(
                    "**Selo: VERIFICADO**\n\n`recordings/../l2scanner/visao.py.png`"
                )
            ),
            encoding="utf-8",
        )
        (raiz_com_frame / "l2scanner" / "visao.py.png").write_bytes(b"existe")

        assert conferir(doc, raiz_com_frame) == 1

    def test_documento_inexistente_reprova_sem_estourar(
        self, tmp_path: Path, raiz_com_frame: Path
    ):
        assert conferir(tmp_path / "nao-existe.md", raiz_com_frame) == 1
