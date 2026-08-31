"""Os portoes de UM AVISO POR NASCIMENTO, afirmados por ESTRUTURA.

Tres regras desta fase nao sao afirmaveis por comportamento sem sorte:

  1. a ancora e escrita FORA do `if` do anuncio (criterio 6 / D-27);
  2. a ancora e escrita ANTES de a chave do episodio ser calculada (D-28);
  3. a decisao de anunciar E o `registrar_anuncio`, e nunca uma checagem
     anterior (UNIC-01 / D-21).

As tres tem a mesma propriedade desagradavel: violadas, TODO o resto da suite
continua verde. Com uma instancia so, a ordem entre a ancora e o anuncio e
indiferente; com uma instancia so, uma checagem anterior parece funcionar. O
sintoma so aparece com as DUAS instancias do usuario rodando, que e exatamente
o cenario que nenhum teste de processo unico consegue montar.

TUDO E LIDO POR AST E NUNCA POR BUSCA TEXTUAL, e a razao e especifica desta
fase: as docstrings que ela acabou de escrever citam `enviados`, `anuncios` e
"checagem anterior" DE PROPOSITO, para explicar por escrito o que a regra
proibe. Um `grep` acusaria justamente a documentacao que protege a regra.

OS HELPERS DE AST SAO COPIADOS de `tests/test_janela_no_relogio.py`, e a copia
e deliberada: quatro funcoes de dez linhas e o preco aceito para os dois
arquivos poderem ser lidos sozinhos. Aquele arquivo ja pagou o mesmo preco.
"""

from __future__ import annotations

import ast
from datetime import date, timedelta
from pathlib import Path

import pytest

from l2scanner import agenda
from l2scanner.agenda import RegistroEmDisco

RAIZ = Path(__file__).resolve().parent.parent


def _fonte(arquivo: str) -> str:
    return (RAIZ / "l2scanner" / arquivo).read_text(encoding="utf-8")


def _funcao(arquivo: str, nome: str) -> ast.FunctionDef:
    """A definicao de uma funcao ou metodo, por AST."""
    arvore = ast.parse(_fonte(arquivo))
    curto = nome.rsplit(".", 1)[-1]
    return next(
        no
        for no in ast.walk(arvore)
        if isinstance(no, ast.FunctionDef) and no.name == curto
    )


def _funcao_de_fonte(fonte: str, nome: str) -> ast.FunctionDef:
    """A mesma busca, sobre um fonte FABRICADO. E o que prova o detector."""
    return next(
        no
        for no in ast.walk(ast.parse(fonte))
        if isinstance(no, ast.FunctionDef) and no.name == nome
    )


def _chamadas(no: ast.AST, alvo: str) -> list[ast.Call]:
    """Toda chamada a `alvo` na subarvore, seja `alvo(...)` ou `x.alvo(...)`."""
    return [
        filho
        for filho in ast.walk(no)
        if isinstance(filho, ast.Call)
        and (
            getattr(filho.func, "id", None) == alvo
            or getattr(filho.func, "attr", None) == alvo
        )
    ]


def _chama(no: ast.AST, alvo: str) -> bool:
    return bool(_chamadas(no, alvo))


# ---------------------------------------------------------------------------
# OS DETECTORES.
# ---------------------------------------------------------------------------


def _ifs_que_engolem_a_ancora(funcao: ast.AST) -> list[ast.If]:
    """Todo `if` do anuncio que tem a escrita da ancora dentro dele."""
    return [
        no
        for no in ast.walk(funcao)
        if isinstance(no, ast.If)
        and _chama(no, "anunciar_nascimento")
        and _chama(no, "registrar_nascimento")
    ]


def _ordem_no_laco(funcao: ast.AST) -> tuple[int, int]:
    """Os indices, no corpo do laco, da ancora e do anuncio."""
    laco = next(no for no in ast.walk(funcao) if isinstance(no, ast.For))
    ancora = next(
        i
        for i, instrucao in enumerate(laco.body)
        if _chama(instrucao, "registrar_nascimento")
    )
    anuncio = next(
        i
        for i, instrucao in enumerate(laco.body)
        if _chama(instrucao, "anunciar_nascimento")
    )
    return ancora, anuncio


# O que `_processar_bosses` NAO pode chamar por conta propria.
#
# `enviados` e `nascimentos` sao leitura de disco: consultadas AQUI, viram a
# checagem anterior que `RegistroEmDisco.marcar` proibe por escrito, e o
# sintoma e um aviso PERDIDO e nao duplicado. `registrar_anuncio` esta na lista
# por outra razao: a decisao inteira mora em `respawn.anunciar_nascimento`, e
# uma segunda copia dela aqui divergiria da de la no primeiro ajuste — o mesmo
# defeito WR-08 que `presenca` ja pagou.
CHAMADAS_PROIBIDAS_NO_SITIO = ("enviados", "nascimentos", "registrar_anuncio")


def _acusacoes_no_sitio(no: ast.AST) -> list[str]:
    return sorted(alvo for alvo in CHAMADAS_PROIBIDAS_NO_SITIO if _chama(no, alvo))


# ---------------------------------------------------------------------------
# OS SHELLS DE MENTIRA. Um portao que nao pode falhar e decoracao.
# ---------------------------------------------------------------------------

ANCORA_DENTRO_DO_IF = '''
def _processar_bosses(self, frame, agora, resultado):
    """A ancora engolida pela supressao do anuncio."""
    for aviso in avisos:
        if anunciar_nascimento(self.registro, aviso.boss, agora, regras):
            if self.registro.registrar_nascimento(
                chave_do_nascimento(aviso.boss, agora, aviso.origem)
            ):
                resultado.ancoras_gravadas.append((aviso.boss, aviso.origem))
            self._despachar(aviso.texto)
'''

ORDEM_INVERTIDA = '''
def _processar_bosses(self, frame, agora, resultado):
    """A chave do episodio calculada antes de a ancora estar em disco."""
    for aviso in avisos:
        anunciou = anunciar_nascimento(
            self.registro, aviso.boss, agora, regras
        )
        if self.registro.registrar_nascimento(
            chave_do_nascimento(aviso.boss, agora, aviso.origem)
        ):
            resultado.ancoras_gravadas.append((aviso.boss, aviso.origem))
        if anunciou:
            self._despachar(aviso.texto)
'''

SITIO_COM_CHECAGEM_ANTERIOR = '''
def _processar_bosses(self, frame, agora, resultado):
    """O read-then-write que D-21 proibe, no sitio dos pixels."""
    ja_anunciados = self.registro.enviados()
    for aviso in avisos:
        if chave_do_anuncio(aviso.boss, agora) in ja_anunciados:
            continue
        self._despachar(aviso.texto)
'''


class TestOsElosDaFiacao:
    """Cada elo dito por nome, para a quebra dizer QUAL deles caiu."""

    @pytest.mark.parametrize(
        "alvo",
        ["chave_do_nascimento", "registrar_nascimento", "anunciar_nascimento"],
    )
    def test_o_sitio_dos_pixels_chama(self, alvo):
        """`chave_do_nascimento` e `registrar_nascimento` sao o elo da Fase 2,
        que esta fase nao pode romper; `anunciar_nascimento` e o desta."""
        assert _chama(_funcao("sessao.py", "_processar_bosses"), alvo), (
            f"_processar_bosses nao chama {alvo}"
        )

    def test_a_decisao_do_anuncio_marca_e_nao_le_enviados(self):
        """`respawn.anunciar_nascimento` e a UMA implementacao da decisao.

        Ela le `nascimentos()` para CALCULAR A CHAVE, e isso nao e uma
        checagem: nao pergunta se o aviso ja saiu. Ler `enviados()` seria a
        checagem anterior, e o sintoma dela e um aviso PERDIDO — as duas
        instancias se veriam livres para calar achando que a outra falou.
        """
        decisao = _funcao("respawn.py", "anunciar_nascimento")

        assert _chama(decisao, "registrar_anuncio")
        assert not _chama(decisao, "enviados")

    @pytest.mark.parametrize("alvo", CHAMADAS_PROIBIDAS_NO_SITIO)
    def test_o_sitio_dos_pixels_nao_decide_por_conta_propria(self, alvo):
        assert not _chama(
            _funcao("sessao.py", "_processar_bosses"), alvo
        ), (
            f"_processar_bosses chama {alvo} por conta propria: a decisao "
            "saiu de respawn.anunciar_nascimento"
        )

    @pytest.mark.parametrize(
        "alvo", ["chave_do_nascimento", "anunciar_nascimento"]
    )
    def test_o_modo_sem_tela_nao_inventa_nem_anuncia_nascimento(self, alvo):
        """Um modo sem pixels nao observa nascimento nenhum; anunciar um que
        nao viu seria inventar o fato, e nao so repeti-lo."""
        assert not _chamadas(ast.parse(_fonte("__main__.py")), alvo), (
            f"o --so-agenda passou a chamar {alvo}"
        )


class TestAAncoraSobreviveAoSilencio:
    """CRITERIO 6 POSTO NA FORMA DO CODIGO.

    "A ancora continua sendo gravada mesmo quando o anuncio e suprimido" e uma
    frase que um teste de comportamento afirma para os casos que alguem lembrou
    de escrever. Estes dois portoes a afirmam para TODOS.
    """

    def test_a_ancora_nao_mora_dentro_do_if_do_anuncio(self):
        """Dentro do `if`, a supressao engoliria a ancoragem junto — e a Fase 2
        pararia de contar seis horas sem uma linha de erro, porque o disco
        simplesmente nao teria o instante."""
        engolidos = _ifs_que_engolem_a_ancora(
            _funcao("sessao.py", "_processar_bosses")
        )

        assert engolidos == [], (
            "a escrita da ancora esta dentro do if do anuncio: uma supressao "
            "de mensagem passou a apagar tambem a contagem de respawn (D-27)"
        )

    def test_a_ancora_e_escrita_ANTES_de_a_chave_do_anuncio_ser_calculada(self):
        """A chave do episodio sai das ancoras que estao EM DISCO.

        Invertida a ordem, a PRIMEIRA deteccao de um episodio calcularia a
        chave sobre um disco que ainda nao tem a ancora dela, cairia no caminho
        do episodio vazio, e as duas instancias — ticando em minutos diferentes
        — produziriam duas chaves e duas mensagens. O defeito de campo voltaria
        inteiro, com todos os outros testes verdes: com uma instancia so a
        ordem e indiferente.
        """
        ancora, anuncio = _ordem_no_laco(
            _funcao("sessao.py", "_processar_bosses")
        )

        assert ancora < anuncio, (
            "o anuncio e decidido antes de a ancora desta deteccao estar em "
            "disco: a chave do episodio deixou de ser estavel entre instancias"
        )


class TestAProvaNaoEVazia:
    """Os detectores aplicados a arvores FABRICADAS que violam a regra.

    Sem isto, um detector que procurasse o nome errado ficaria verde para
    sempre — e este projeto ja escreveu essa frase tres vezes.
    """

    def test_o_detector_acusa_a_ancora_dentro_do_if(self):
        fabricado = _funcao_de_fonte(ANCORA_DENTRO_DO_IF, "_processar_bosses")

        assert len(_ifs_que_engolem_a_ancora(fabricado)) == 1

    def test_o_detector_acusa_a_ordem_invertida(self):
        fabricado = _funcao_de_fonte(ORDEM_INVERTIDA, "_processar_bosses")

        ancora, anuncio = _ordem_no_laco(fabricado)
        assert ancora > anuncio

    def test_o_detector_acusa_uma_checagem_anterior_fabricada(self):
        fabricado = _funcao_de_fonte(
            SITIO_COM_CHECAGEM_ANTERIOR, "_processar_bosses"
        )

        assert _acusacoes_no_sitio(fabricado) == ["enviados"]

    def test_o_detector_de_elo_acusa_um_sitio_que_nao_anuncia(self):
        """O outro lado do portao: o elo QUEBRADO tambem tem que ser visto."""
        fabricado = _funcao_de_fonte(
            SITIO_COM_CHECAGEM_ANTERIOR, "_processar_bosses"
        )

        assert not _chama(fabricado, "anunciar_nascimento")


class TestOSilencioExpiraEmVezDeCalarParaSempre:
    """T-03-03: um marcador de anuncio imortal e um boss que nunca mais nasce.

    O sintoma seria um scanner que roda, loga, preve janela e nunca mais avisa
    um nascimento — sem erro, sem log, sem nada. E a familia de defeito mais
    barata de introduzir e mais cara de descobrir desta fase.
    """

    HOJE = date(2026, 8, 30)
    RECENTE = "anuncio_2026-08-30_tiat-north-2159"
    VELHO = "anuncio_2026-08-26_tiat-north-1430"

    def test_um_anuncio_de_quatro_dias_atras_e_apagado(self, tmp_path):
        pasta = tmp_path / "agenda"
        registro = RegistroEmDisco(pasta)
        (pasta / self.VELHO).touch()
        (pasta / self.RECENTE).touch()

        registro.podar(hoje=self.HOJE)

        assert not (pasta / self.VELHO).exists()
        assert (pasta / self.RECENTE).exists()

    def test_a_poda_alcanca_o_prefixo_porque_a_data_vem_logo_depois_dele(
        self, tmp_path
    ):
        """A prova nao e vazia: sem `PREFIXO_ANUNCIO` em
        `_PREFIXOS_CONHECIDOS`, `podar` nao saberia retira-lo e a data cairia
        no `except ValueError`, deixando o marcador em disco PARA SEMPRE.
        """
        pasta = tmp_path / "agenda"
        registro = RegistroEmDisco(pasta)
        (pasta / f"inventado_{self.VELHO[len('anuncio_') :]}").touch()

        registro.podar(hoje=self.HOJE)

        assert list(pasta.iterdir()), (
            "um prefixo desconhecido foi podado: a poda deixou de depender da "
            "lista de prefixos e este teste nao prova mais nada"
        )

    def test_o_marcador_de_anuncio_morre_em_DIAS_DE_MARCADOR(self, tmp_path):
        """O teto do estrago de uma troca de formato e tres dias de
        repeticoes, e nao um dano permanente. Foi para limitar essa familia de
        erro que o prefixo entrou no balde que a poda alcanca.
        """
        pasta = tmp_path / "agenda"
        registro = RegistroEmDisco(pasta)
        limite = self.HOJE - timedelta(days=agenda.DIAS_DE_MARCADOR)
        (pasta / f"anuncio_{limite.isoformat()}_tiat-north-1430").touch()

        registro.podar(hoje=self.HOJE)

        assert list(pasta.iterdir()), (
            "o marcador do proprio dia do limite foi apagado: a poda ficou um "
            "dia mais agressiva do que DIAS_DE_MARCADOR promete"
        )
