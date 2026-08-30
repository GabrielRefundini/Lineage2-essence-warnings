"""O texto da calibracao fala das REGIOES, e nunca de um mob.

O que `calibrar-tiat.bat` marca sao duas partes do HUD: as linhas do CHAT onde
o servidor anuncia um nascimento, e o NOME do ALVO selecionado. Nenhuma das
duas pertence a um mob. A MESMA calibracao serve para qualquer boss da lista do
`config.toml`, e quem acrescenta um `[[boss]]` novo nao recalibra nada.

POR QUE ISSO PRECISA DE UM GUARDA. Um nome proprio de mob no texto da
ferramenta nao e feiura: e uma afirmacao falsa sobre o que o usuario acabou de
fazer. Lendo "marque onde aparece o anuncio do Fulano", ele conclui que a
calibracao e POR MOB — e no dia em que acrescentar um boss no `config.toml`,
vai abrir o jogo e gastar o tempo de uma recalibracao que nao mudaria um pixel
do resultado. O custo do defeito e o tempo dele, e ninguem nunca vai reportar
isso como bug, porque para quem le o texto ele nao parece errado.

AST, E NUNCA `grep`. `l2scanner/calibrar.py` legitimamente carrega a palavra em
nomes de simbolo (`calibrar_tiat`, `cal.tiat_chat`) e em comentarios que
explicam justamente por que aqueles nomes NAO mudaram. Um `grep` cru acusaria
tudo isso, viraria ruido, e o proximo a passar por aqui afrouxaria o guarda ate
ele parar de guardar. Mesma razao escrita em
`tests/test_presenca.py::TestSemRelogioProprio`.

OS TERMOS PROCURADOS NAO SAO SO OS NOMES COMPLETOS, e este e o ponto onde um
guarda ingenuo passa VERDE sobre a mentira que ele existe para pegar. Ver a
docstring de `termos_procurados`.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from l2scanner.config import ler_bosses

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "l2scanner" / "calibrar.py"
BAT = RAIZ / "calibrar-tiat.bat"
CONFIG = RAIZ / "config.toml"

# A FUNCAO VIGIADA. So os literais dela entram na busca: o resto do arquivo tem
# comentario e nome de simbolo que carregam a palavra de proposito.
FUNCAO = "calibrar_tiat"

# OS TOKENS DE ENTRADA ESTAVEIS, removidos de cada string ANTES da busca.
#
# A flag de linha de comando e o nome do arquivo `.bat` carregam o token curto
# por heranca e continuam com esse nome DE PROPOSITO: sao a porta de entrada
# que o usuario ja tem no dedo e que o README ja documenta. Renomea-los custaria
# uma quebra real em troca de estetica. Confundi-los com o texto de instrucao
# faria este guarda pedir uma quebra que ninguem quer.
#
# A REMOCAO E ANTES DA BUSCA, e nunca depois: remover depois deixaria a
# comparacao acusar a propria flag e so entao perdoa-la, o que da no mesmo que
# nao ter guarda para o caso simetrico.
TOKENS_ESTAVEIS = ("calibrar-tiat.bat", "--tiat")

# Quantos caracteres um token precisa ter para ser procurado. Uma particula de
# duas letras dentro de um nome composto viraria falso positivo em qualquer
# frase em portugues.
TAMANHO_MINIMO_DO_TOKEN = 3


def termos_procurados(bosses) -> set[str]:
    """O nome inteiro de cada boss MAIS cada token dele separado por espaco.

    ESTA E A LINHA QUE DECIDE SE O ARQUIVO GUARDA OU DECORA.

    `ler_bosses` devolve `Tiat North` e `Tiat South`, e NENHUMA string do codigo
    que este arquivo vigia jamais conteve qualquer um desses dois. O texto que
    existia antes da limpeza dizia so o PRIMEIRO TOKEN, sozinho:

        "1/2 - marque as linhas do CHAT onde aparece o anuncio de Tiat."
        "Tiat: chat" / "TIAT ALVO"
        "Aviso de Tiat calibrado para ..."

    Um conjunto de termos com so os nomes completos ficaria VERDE sobre
    exatamente essas quatro strings — um guarda decorativo, que e pior do que
    guarda nenhum, porque parece protecao.
    `test_um_conjunto_so_com_nomes_completos_ficaria_cego` afirma isso por
    escrito, para que a explicacao acima nao dependa de alguem ler este
    paragrafo.

    Os termos saem do `config.toml` DO REPOSITORIO, e nao de um literal escrito
    aqui: assim o guarda continua valendo se a lista mudar, e fica ancorado na
    MESMA fonte que o resto da fase usa como identidade de boss.
    """
    termos: set[str] = set()
    for boss in bosses:
        nome = boss.nome.strip()
        if len(nome) >= TAMANHO_MINIMO_DO_TOKEN:
            termos.add(nome.casefold())
        for pedaco in nome.split():
            if len(pedaco) >= TAMANHO_MINIMO_DO_TOKEN:
                termos.add(pedaco.casefold())
    return termos


def primeiro_token(bosses) -> str:
    """O primeiro token do primeiro boss — a forma exata em que a mentira existia.

    Usado pelos testes de prova-vazia. Escrever aqueles testes com o NOME
    COMPLETO reproduziria o defeito dentro do proprio guarda que existe para
    preveni-lo: eles passariam enquanto o detector continuasse cego para o token
    curto.
    """
    for boss in bosses:
        for pedaco in boss.nome.split():
            if len(pedaco) >= TAMANHO_MINIMO_DO_TOKEN:
                return pedaco
    raise AssertionError("nenhum boss do config tem token utilizavel")


def sem_tokens_estaveis(texto: str) -> str:
    """Apaga a flag e o nome do `.bat` do texto, ignorando a caixa."""
    for token in TOKENS_ESTAVEIS:
        texto = re.sub(re.escape(token), " ", texto, flags=re.IGNORECASE)
    return texto


def literais_da_funcao(fonte: str, nome_da_funcao: str = FUNCAO) -> list[str]:
    """Todo `str` literal dentro da funcao, a docstring inclusive."""
    arvore = ast.parse(fonte)
    for no in ast.walk(arvore):
        if (
            isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))
            and no.name == nome_da_funcao
        ):
            return [
                filho.value
                for filho in ast.walk(no)
                if isinstance(filho, ast.Constant) and isinstance(filho.value, str)
            ]
    raise AssertionError(
        f"a funcao {nome_da_funcao!r} sumiu do fonte; o guarda ficou sem objeto"
    )


def acusacoes(textos, termos) -> list[tuple[str, str]]:
    """Os pares (termo, texto) em que um mob foi nomeado, sem diferenciar caixa."""
    achados: list[tuple[str, str]] = []
    for texto in textos:
        limpo = sem_tokens_estaveis(texto).casefold()
        for termo in sorted(termos):
            if termo in limpo:
                achados.append((termo, texto))
    return achados


@pytest.fixture(scope="module")
def bosses():
    """Os `[[boss]]` do `config.toml` do repositorio.

    Lista vazia PULA o arquivo inteiro, com a razao dita em voz alta: um teste
    que passa por falta de dado e pior do que um teste que nao existe.
    """
    achados = ler_bosses(CONFIG)
    if not achados:
        pytest.skip(
            "o config.toml do repositorio nao tem nenhum [[boss]]; sem nome de "
            "mob para procurar, este guarda passaria sem provar nada"
        )
    return achados


@pytest.fixture(scope="module")
def termos(bosses) -> set[str]:
    achados = termos_procurados(bosses)
    if not achados:
        pytest.skip("nenhum token com tamanho utilizavel saiu dos [[boss]]")
    return achados


class TestOTextoDaCalibracaoNaoNomeiaUmMob:
    """OPER-01: a regiao e do CHAT e do ALVO, e a calibracao e uma so."""

    def test_nenhum_literal_da_funcao_nomeia_um_mob(self, termos):
        literais = literais_da_funcao(FONTE.read_text(encoding="utf-8"))
        assert literais, "a funcao vigiada nao tem literal nenhum; leitura vazia"
        achados = acusacoes(literais, termos)
        assert not achados, (
            f"o texto de {FUNCAO} voltou a nomear um mob: {achados}. A regiao e "
            f"do CHAT e do ALVO, e a mesma calibracao serve para qualquer boss "
            f"da lista do config.toml."
        )

    def test_nenhuma_linha_do_bat_nomeia_um_mob(self, termos):
        linhas = BAT.read_text(encoding="cp1252").splitlines()
        assert linhas, "o .bat ficou vazio; leitura vazia"
        achados = acusacoes(linhas, termos)
        assert not achados, (
            f"o calibrar-tiat.bat voltou a nomear um mob: {achados}. O .bat marca "
            f"duas regioes do HUD, e nao um mob."
        )

    def test_a_funcao_afirma_que_a_calibracao_serve_para_qualquer_boss(self):
        """Nao basta parar de mentir: a ferramenta tem de dizer a verdade.

        Sem esta afirmacao explicita, o usuario continua sem saber que
        acrescentar um `[[boss]]` no config nao pede recalibracao — que e a
        conclusao errada inteira que OPER-01 existe para desfazer.
        """
        literais = literais_da_funcao(FONTE.read_text(encoding="utf-8"))
        juntos = " ".join(literais).casefold()
        assert "qualquer boss" in juntos, (
            "nenhum texto da funcao afirma que a mesma calibracao vale para "
            "qualquer boss da lista"
        )


class TestOGuardaPegaDeVerdade:
    """Guarda contra prova vazia, nas duas direcoes.

    Um detector que nao achasse NADA passaria nos testes acima sem provar coisa
    alguma; um detector que achasse TUDO pediria a quebra da flag que ninguem
    quer. Os dois lados sao afirmados aqui.
    """

    def test_o_detector_acusa_uma_fonte_com_o_TOKEN_CURTO(self, bosses, termos):
        """A forma exata em que a mentira existia: o primeiro token, sozinho."""
        curto = primeiro_token(bosses)
        sintetica = (
            f"def {FUNCAO}(titulo=None):\n"
            f'    """Marca o chat e o alvo."""\n'
            f'    print("1/2 - marque o CHAT onde aparece o anuncio de {curto}.")\n'
            f"    return 0\n"
        )
        achados = acusacoes(literais_da_funcao(sintetica), termos)
        assert achados, (
            f"o detector nao acharia nem um {curto!r} literal impresso pela "
            f"ferramenta — o conjunto de termos esta cego para o token curto"
        )

    def test_o_detector_acusa_uma_linha_de_bat_com_o_TOKEN_CURTO(self, bosses, termos):
        curto = primeiro_token(bosses)
        linhas = [f"REM  O scanner avisa se {curto} aparecer no chat."]
        assert acusacoes(linhas, termos), (
            f"o detector nao acharia um {curto!r} num comentario REM do .bat"
        )

    def test_um_conjunto_so_com_nomes_completos_ficaria_cego(self, bosses, termos):
        """O defeito que `termos_procurados` existe para nao ter.

        Este e o teste que separa este guarda de um decorativo: ele demonstra,
        no proprio arquivo, que procurar so `Tiat North` / `Tiat South` deixaria
        passar a string que a ferramenta REALMENTE tinha.
        """
        curto = primeiro_token(bosses)
        sintetica = (
            f"def {FUNCAO}(titulo=None):\n"
            f'    print("Aviso de {curto} calibrado.")\n'
        )
        literais = literais_da_funcao(sintetica)
        so_nomes_completos = {boss.nome.casefold() for boss in bosses}

        assert not acusacoes(literais, so_nomes_completos), (
            "premissa quebrada: o nome COMPLETO aparece na fonte sintetica, "
            "entao ela nao demonstra mais a cegueira"
        )
        assert acusacoes(literais, termos), (
            "o conjunto real de termos tambem ficou cego para o token curto — "
            "este guarda voltou a ser decorativo"
        )

    def test_o_conjunto_de_termos_tem_o_token_curto_alem_do_nome_completo(
        self, bosses, termos
    ):
        curto = primeiro_token(bosses)
        completo = bosses[0].nome
        assert curto.casefold() in termos
        assert completo.casefold() in termos
        assert curto.casefold() != completo.casefold(), (
            "o primeiro boss tem nome de um token so; escolha um caso de teste "
            "com nome composto ou este arquivo nao esta provando o que diz"
        )


class TestOsTokensDeEntradaNaoSaoAcusados:
    """O caso simetrico. Sem ele, a remocao podia estar quebrada em silencio."""

    def test_a_flag_de_linha_de_comando_sozinha_nao_e_acusada(self, termos):
        literal = 'Use: python -m l2scanner.calibrar --tiat --janela "TITULO"'
        assert not acusacoes([literal], termos), (
            "a flag de linha de comando foi acusada; ela continua com esse nome "
            "de proposito e o guarda estaria pedindo uma quebra que ninguem quer"
        )

    def test_o_nome_do_bat_sozinho_nao_e_acusado(self, termos):
        linha = '".venv\\Scripts\\python.exe" -m l2scanner.calibrar --tiat %*'
        assert not acusacoes([linha], termos)
        assert not acusacoes(["REM  Rode o calibrar-tiat.bat uma vez."], termos)

    def test_a_remocao_ignora_a_caixa(self, termos):
        assert not acusacoes(["Rode o CALIBRAR-TIAT.BAT", "use --TIAT"], termos)
