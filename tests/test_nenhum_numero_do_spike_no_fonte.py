"""O criterio 4 do roadmap, como PORTAO QUE RODA -- e sobre arvore de sintaxe.

O CRITERIO COMO ESTA ESCRITO NO ROADMAP FOI REFUTADO POR MEDICAO, e a refutacao
abre este arquivo porque sem ela alguem reescreve o portao errado amanha.

O texto pede: *"uma busca no fonte por qualquer um dos numeros do spike
(`1368`, `246`, `210`) nao acha nenhum deles fora de teste"*. Medido nesta
arvore, com `(?<!\\d)N(?!\\d)` sobre todo `l2scanner/*.py`:

    1368 -> 4     1230 -> 0    1200 -> 1     736 -> 4
     520 -> 2      470 -> 4     246 -> 8     210 -> 11
     190 -> 10     170 -> 6      26 -> 58

**108 ocorrencias, e NENHUMA delas e codigo.** Todas moram em comentario ou
docstring -- inclusive `calibrar_mercado.py`, cuja frase e literalmente
*"Escrever 210 no fonte seria transformar uma medicao numa constante"*, e o
proprio `calibrar_renda.py`, que cita `246,736` e `236,750` para explicar por
que o calibrador nao comeca sem saber de quem e a tela.

Um portao por `grep` nasceria VERMELHO e seria "consertado" apagando
comentarios que valem mais do que ele. **O portao e sobre a ARVORE DE SINTAXE,
e conta apenas LITERAL INTEIRO.** Docstring e comentario nao sao literal
inteiro, entao a prosa que explica os numeros fica -- que e exatamente o que se
quer: a explicacao sobrevive e o atalho nao.

DOIS CONJUNTOS, E A SEPARACAO E JUSTIFICADA POR COLISAO MEDIDA
==============================================================
Os **DISTINTIVOS** -- os que so poderiam ter vindo do spike -- sao verificados
em TODO `l2scanner/*.py`.

Os **AMBIGUOS** sao verificados SO NOS MODULOS DA RENDA, e a razao tem endereco:

- `150` aparece tres vezes em `calibrar.py:105,182,262`, e la ele e o piso de
  SATURACAO HSV da barra de vida vermelha da party -- a deteccao de morte;
- `180` aparece em `identidade.py:56` como `VALOR_MINIMO_DO_TEXTO`;
- `500` aparece em `dashboard.py:616` e em `notificador.py:678`, onde
  `erro.code >= 500` e uma familia de CODIGO DE STATUS HTTP.

Um portao de arvore inteira sobre esses tres exigiria apagar a deteccao de
morte para satisfazer um teste de renda. As colisoes estao nomeadas por arquivo
e linha aqui em cima para que ninguem "conserte" o teste ALARGANDO o escopo --
que e a unica maneira de este arquivo causar dano.

O PORTAO NASCE VERDE, E POR ISSO O CONTROLE POSITIVO E OBRIGATORIO
===================================================================
Medido: zero ocorrencias dos onze distintivos e dos tres ambiguos, hoje, antes
de este arquivo existir. Isso e boa noticia -- o portao mede uma regressao
futura de verdade em vez de nascer vermelho e virar divida --, mas um portao
que nasce verde e INDISTINGUIVEL de um portao que nao varre nada. O controle
passa ao MESMO verificador um fonte sintetico e afirma que ele e acusado, com o
numero citado na mensagem.

O verificador e UMA funcao, usada pelo portao e pelo controle. Um controle que
reimplementasse a varredura nao controlaria nada.
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MODULOS = sorted((RAIZ / "l2scanner").glob("*.py"))

# OS ONZE NUMEROS DO SPIKE que so poderiam ter vindo dele: coordenadas e
# dimensoes dos retangulos medidos a mao numa unica maquina, numa unica
# resolucao, num unico instante. Eles nao descrevem a tela de mais ninguem --
# nem a do proprio usuario depois de ele arrastar a janela.
DISTINTIVOS = frozenset({1368, 1230, 1200, 736, 520, 470, 246, 210, 190, 170, 26})

# Os que COLIDEM com numeros legitimos de outras features. Ver a docstring do
# modulo para o endereco de cada colisao.
AMBIGUOS = frozenset({150, 180, 500})

MODULOS_DA_RENDA = ("renda_leitura.py", "renda_modo.py", "calibrar_renda.py")


def literais_inteiros_proibidos(
    caminhos, proibidos: frozenset[int]
) -> list[tuple[str, int, int]]:
    """`[(arquivo, linha, valor)]` -- so LITERAL INTEIRO na arvore de sintaxe.

    ESTA E A FUNCAO QUE O PORTAO E O CONTROLE COMPARTILHAM, e compartilhar e o
    ponto: um controle que reimplementasse a varredura provaria que a
    reimplementacao funciona, e nao que o portao funciona.

    `bool` e excluido explicitamente porque e subclasse de `int`: sem a
    exclusao, `True` num fonte qualquer seria lido como o inteiro 1 e o portao
    passaria a acusar coisas que nao sao numero.

    Docstring e comentario NAO sao literal inteiro e por isso atravessam: e
    exatamente essa a diferenca entre este portao e o `grep` que o roadmap
    descreve em prosa.
    """
    achados: list[tuple[str, int, int]] = []
    for caminho in caminhos:
        arvore = ast.parse(Path(caminho).read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Constant):
                continue
            if isinstance(no.value, bool) or not isinstance(no.value, int):
                continue
            if no.value in proibidos:
                achados.append((str(caminho), no.lineno, no.value))
    return achados


def _fonte_sintetico(tmp_path: Path, corpo: str) -> Path:
    alvo = tmp_path / "sintetico.py"
    alvo.write_text(corpo, encoding="utf-8")
    return alvo


class TestOPortao:
    def test_NENHUM_DISTINTIVO_E_LITERAL_INTEIRO_EM_l2scanner(self):
        achados = literais_inteiros_proibidos(MODULOS, DISTINTIVOS)
        assert not achados, (
            "numero do spike de volta ao fonte como LITERAL INTEIRO:\n  "
            + "\n  ".join(f"{a}:{linha} -> {valor}" for a, linha, valor in achados)
            + "\nToda geometria vem do `calibration.json`, medida no frame do "
            "proprio usuario. Um literal aqui e a diferenca entre consertar uma "
            "janela movida com uma rodada do calibrador e consertar com um "
            "commit."
        )

    def test_NENHUM_AMBIGUO_E_LITERAL_INTEIRO_NOS_MODULOS_DA_RENDA(self):
        """Escopo estreito DE PROPOSITO. Ver as colisoes na docstring."""
        da_renda = [
            caminho for caminho in MODULOS if caminho.name in MODULOS_DA_RENDA
        ]
        assert da_renda, "os modulos da renda sumiram; o portao ficou vazio"
        achados = literais_inteiros_proibidos(da_renda, AMBIGUOS)
        assert not achados, (
            "piso de brilho do spike de volta ao fonte da renda:\n  "
            + "\n  ".join(f"{a}:{linha} -> {valor}" for a, linha, valor in achados)
        )

    def test_O_PORTAO_VARRE_TODOS_OS_MODULOS_E_NAO_UMA_LISTA_PARADA(self):
        """A lista de arquivos vem do `glob`, e nao de nomes escritos a mao.

        Um modulo novo nasce VARRIDO por omissao. Uma lista a mao deixaria o
        proximo modulo da renda fora do portao sem ninguem notar -- que e o
        mesmo defeito da "lista de preservados" que o `CAMPOS_DA_PARTY` ja
        derrubou uma vez neste repositorio.
        """
        assert len(MODULOS) > 10
        nomes = {caminho.name for caminho in MODULOS}
        for esperado in MODULOS_DA_RENDA:
            assert esperado in nomes, esperado


class TestOControlePositivo:
    """Sem esta classe o portao acima e indistinguivel de um que nao varre nada."""

    def test_UM_FONTE_COM_A_REGIAO_LITERAL_E_ACUSADO(self, tmp_path):
        alvo = _fonte_sintetico(
            tmp_path,
            "from l2scanner.frames import Regiao\n"
            "REGIAO_DO_EXP = Regiao(0, 1368, 520, 26)\n",
        )
        achados = literais_inteiros_proibidos([alvo], DISTINTIVOS)
        valores = sorted(valor for _, _, valor in achados)
        assert valores == [26, 520, 1368], (
            "o verificador NAO acusou coordenadas literais: o portao acima "
            "esta verde por nao varrer nada, e nao por a arvore estar limpa"
        )

    def test_A_ACUSACAO_CITA_O_NUMERO_E_A_LINHA(self, tmp_path):
        alvo = _fonte_sintetico(tmp_path, "\n\nPISO = 246\n")
        achados = literais_inteiros_proibidos([alvo], DISTINTIVOS)
        assert achados == [(str(alvo), 3, 246)]

    def test_O_CONTROLE_CHAMA_A_MESMA_FUNCAO_QUE_O_PORTAO(self):
        """Afirmado por leitura do proprio arquivo: uma segunda implementacao

        aqui controlaria a si mesma.
        """
        fonte = Path(__file__).read_text(encoding="utf-8")
        arvore = ast.parse(fonte)
        definicoes = [
            no.name for no in ast.walk(arvore) if isinstance(no, ast.FunctionDef)
        ]
        assert definicoes.count("literais_inteiros_proibidos") == 1, (
            "o verificador foi duplicado; o controle deixou de controlar o "
            "portao e passou a controlar a copia"
        )
        chamadas = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call)
            and getattr(no.func, "id", None) == "literais_inteiros_proibidos"
        ]
        assert len(chamadas) >= 4


class TestOPortaoNaoAcusaProsa:
    """A metade que o `grep` erra, afirmada como comportamento e nao como fe."""

    def test_UM_NUMERO_DO_SPIKE_NUM_COMENTARIO_ATRAVESSA(self, tmp_path):
        alvo = _fonte_sintetico(tmp_path, "# o retangulo media 0,1368 520x26\nX = 1\n")
        assert literais_inteiros_proibidos([alvo], DISTINTIVOS) == []

    def test_UM_NUMERO_DO_SPIKE_NUMA_DOCSTRING_ATRAVESSA(self, tmp_path):
        alvo = _fonte_sintetico(
            tmp_path,
            'def f():\n    """A banda util do nivel e 190-220 e a da adena e 150."""\n'
            "    return None\n",
        )
        assert literais_inteiros_proibidos([alvo], DISTINTIVOS | AMBIGUOS) == []

    def test_UMA_STRING_COM_O_NUMERO_TAMBEM_ATRAVESSA(self, tmp_path):
        alvo = _fonte_sintetico(tmp_path, 'MENSAGEM = "o retangulo 246,736"\n')
        assert literais_inteiros_proibidos([alvo], DISTINTIVOS) == []

    def test_MAS_O_MESMO_NUMERO_COMO_CODIGO_AO_LADO_E_ACUSADO(self, tmp_path):
        """O par que prova que a distincao e entre PROSA e CODIGO, e nao entre

        "aparece" e "nao aparece".
        """
        alvo = _fonte_sintetico(
            tmp_path,
            "# o retangulo media 0,1368 520x26\n"
            'MENSAGEM = "o retangulo 246,736"\n'
            "TOPO = 1368\n",
        )
        achados = literais_inteiros_proibidos([alvo], DISTINTIVOS)
        assert [valor for _, _, valor in achados] == [1368]
        assert achados[0][1] == 3


class TestBoolNaoEContadoComoInteiro:
    def test_UM_True_NAO_E_LIDO_COMO_O_INTEIRO_1(self, tmp_path):
        """`bool` e subclasse de `int`. Sem a exclusao explicita, um portao que

        proibisse o 1 acusaria todo `True` do repositorio.
        """
        alvo = _fonte_sintetico(tmp_path, "LIGADO = True\nDESLIGADO = False\n")
        assert literais_inteiros_proibidos([alvo], frozenset({0, 1})) == []

    def test_CONTROLE_O_INTEIRO_1_DE_VERDADE_E_ACUSADO(self, tmp_path):
        alvo = _fonte_sintetico(tmp_path, "UM = 1\n")
        assert literais_inteiros_proibidos([alvo], frozenset({1})) == [
            (str(alvo), 1, 1)
        ]
