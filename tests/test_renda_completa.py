"""Os TRES campos da renda: o nivel e a adena ao lado do EXP, e o comando.

O QUE ESTE ARQUIVO EXISTE PARA IMPEDIR
======================================
1. **Que a adena volte a ser lida por OCR.** Ela saiu por MEDICAO e nao por
   gosto: sobre o recorte mascarado, a regra de abstencao aceitou `106.020` no
   lugar de `1.696.020` e `91` no lugar de `13.160.684` (M-G); e exigir que as
   duas escalas CONCORDEM tambem nao salvava — em 173 concordancias da
   Faerlina, as 173 liam a **L-Coin** (M-H). Nenhuma regra sobre DUAS LEITURAS
   resolve um problema de QUAL CAMPO. Um portao de arvore de sintaxe prende a
   volta por atalho.
2. **Que um conjunto de moldes pela metade leia com a confianca do conjunto
   inteiro.** Meio conjunto falha ABERTO: um `8` sem molde de `8` casa com `0`
   a 0,7826 contra piso 0,4698, e a margem tambem nao pega. Conjunto ausente e
   conjunto incompleto recusam **igual**, nomeando o que falta.
3. **Que um icone de moeda vire digito.** Os icones das pontas sao descartados
   por LARGURA e o descarte e POSICIONAL: um run largo no MEIO derruba a
   leitura em vez de encurtar o numero — encurtar produziria um numero
   plausivel e errado, que e o defeito que esta fase inteira existe para nao
   produzir.
4. **Que a leitura de um personagem caia na calibracao do outro.** O retangulo
   do vizinho nao devolve campo vazio: devolve `349` ou `112`, numeros
   desenhados ao lado do nivel que passam por qualquer validacao.
5. **Que o cruzamento de escalas volte a exigir IGUALDADE.** O nivel da
   Faerlina sai `67` numa escala so, com a outra abstendo. Sob a regra antiga
   ele seria recusado PARA SEMPRE.
6. **Que um campo recusado saia com codigo 0.** "Leu", "recusou" e "quebrou"
   sao tres codigos de saida diferentes, porque quem le o codigo e a fase
   seguinte e nao um humano.

A VERDADE DE CAMPO QUE ESTE ARQUIVO AFIRMA
==========================================
Lida a olho sobre a gravacao das duas instancias vivas, e escrita em
`01-MEDICOES-DE-CAMPO.md` e em `tests/fixtures/renda/LEIA-ME.md`:

    Faerlina    nivel 67   EXP 8,0012%    adena 13.160.684   L-Coin 13.091
    Yazalaque   nivel 69   EXP 76,6646%   adena  1.696.020   L-Coin  9.790

    segundo cenario, 8h30 depois:
    Faerlina    adena 15.134.779      Yazalaque   adena 4.497.890
    gravacao antiga:
    aba_para_calibrar   adena 2.207.577

O SKIP POR AUSENCIA DE OCR, E ELE E O UNICO LEGITIMO NESTE ARQUIVO
==================================================================
As bindings do WinRT sao modulares e nao existem no Python que roda esta suite
por padrao. As classes que dependem do motor pulam, e a razao carrega o comando
que as faz rodar. **Nenhum outro motivo de skip passa aqui** — e em particular
o caso do conjunto COMPLETO nao pula: se a fixtura chegasse pela metade, o
desfecho certo seria PARAR e pedir outra rodada do cortador, e nunca pintar o
arquivo de verde com um `skip`.

**O caminho de GLIFO nao precisa de OCR nenhum**, e essa e a melhor noticia
desta onda: a adena — o campo mais perigoso da fase — e verificavel em qualquer
clone, contra pixel real, sem motor de texto instalado.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

import l2scanner.ocr as ocr
from l2scanner import renda_leitura as rl
from l2scanner import renda_modo
from l2scanner.calibracao import Calibracao
from l2scanner.frames import Regiao
from l2scanner.mercado_leitura import inteiro_de_quantidade, numero_valido
from l2scanner.mercado_visao import glifos_de_calibracao

FIXTURAS = Path(__file__).parent / "fixtures" / "renda"
CALIBRACAO_DE_FIXTURE = FIXTURAS / "calibracao_de_fixture.json"
MONTAGEM_COM_O_NIVEL_PRETO = FIXTURAS / "montagem_da_janela.png"
MONTAGEM_COMPLETA = FIXTURAS / "montagem_completa.png"

FONTE_DO_MODULO_PURO = Path(__file__).parent.parent / "l2scanner" / "renda_leitura.py"

TEM_OCR = ocr.disponivel()
MOTIVO_SEM_OCR = ocr.motivo_indisponivel()
ocr._resetar_cache()

RAZAO_DO_SKIP = (
    "Este Python nao tem as bindings de OCR do Windows"
    f" ({MOTIVO_SEM_OCR.splitlines()[0] if MOTIVO_SEM_OCR else 'motivo desconhecido'})."
    " O ambiente de producao tem, e o global tem pytest: rode com os dois,"
    ' PYTHONPATH=".;<repo>/.venv/Lib/site-packages" python -m pytest'
    " tests/test_renda_completa.py"
)

precisa_de_ocr = pytest.mark.skipif(not TEM_OCR, reason=RAZAO_DO_SKIP)

# Os ONZE rotulos que um numero desta barra pode conter. Escritos aqui, e nao
# importados, DE PROPOSITO: este e o portao do merge, e um portao que importasse
# a lista do modulo que ele confere seria verde por construcao.
ROTULOS_DA_BARRA = sorted("0123456789,")

# A VERDADE DE CAMPO, por fixtura de recorte da barra direita.
ADENA_POR_FIXTURA = {
    "campo_faerlina_f000": 13_160_684,
    "campo_yazalaque_f001": 1_696_020,
    "segundo_cenario_faerlina": 15_134_779,
    "segundo_cenario_yazalaque": 4_497_890,
    "aba_para_calibrar_f000": 2_207_577,
}

NIVEL_POR_PERSONAGEM = {"Faerlina": 67, "Yazalaque": 69}

# A BANDA DE GLIFO MEDIDA (M-J), e o piso calibrado esta dentro dela.
BANDA_DE_GLIFO = (180, 185, 190)

# OS TRES NUMEROS QUE A MEDICAO CAPTUROU ERRADOS, e o achado que mediu cada um.
NUMEROS_ERRADOS_DE_CAMPO = {
    106_020: "M-G: a Yazalaque lida por OCR num piso, verdade 1.696.020",
    91: "M-G: a Faerlina lida por OCR no piso vizinho, verdade 13.160.684",
    13_091: "M-H: a L-Coin da Faerlina, em 173 concordancias de 173",
    9_790: "M-H: a L-Coin da Yazalaque, em 70 concordancias de 110",
}


def calibracao() -> Calibracao:
    return Calibracao.carregar(CALIBRACAO_DE_FIXTURE)


def conjunto_de_moldes() -> dict:
    return calibracao().renda_moldes_da_barra


def moldes_decodificados() -> dict:
    return glifos_de_calibracao(conjunto_de_moldes()["moldes"])


def recorte_da_adena(fixtura: str) -> np.ndarray:
    return cv2.imread(str(FIXTURAS / f"{fixtura}__barra_direita.png"))


def recorte_do_nivel(personagem: str) -> np.ndarray:
    arquivo = {
        "Faerlina": "campo_faerlina_f000__nivel.png",
        "Yazalaque": "campo_yazalaque_f001__nivel.png",
    }[personagem]
    return cv2.imread(str(FIXTURAS / arquivo))


def ler_a_adena(recorte, *, piso_de_brilho: int, moldes=None):
    """A chamada de PRODUCAO, com os limiares vindos do conjunto gravado."""
    conjunto = conjunto_de_moldes()
    return rl.adena_da_barra(
        recorte,
        piso_de_brilho=piso_de_brilho,
        moldes=moldes_decodificados() if moldes is None else moldes,
        piso_de_leitura=conjunto["piso_de_leitura"],
        margem_de_leitura=conjunto["margem_de_leitura"],
        folga_de_cola=conjunto["folga_de_cola"],
    )


class TestOMergeDosMoldesNaFixturaDeCalibracao:
    """A Tarefa 1 do `01-04` funde os moldes, e o merge e LOAD-MUTATE-SAVE.

    O `01-01` criou esta fixtura na onda 1, sem moldes — eles nao existiam. O
    `01-05` os cortou na onda 2. Sem o merge, `conjunto_descreve_numeros`
    receberia `None` e a adena recusaria por conjunto ausente em TODA rodada,
    com a mensagem CERTA para o motivo ERRADO: quem lesse "faltam digitos"
    rodaria o cortador de novo, quando o que falta e o merge.
    """

    def test_A_CHAVE_CARREGA_OS_ONZE_ROTULOS(self):
        moldes = moldes_decodificados()
        faltam = [r for r in ROTULOS_DA_BARRA if r not in moldes]
        assert not faltam, (
            f"o conjunto da fixtura esta INCOMPLETO: faltam {faltam}. "
            "A saida NAO e inventar molde nem pular o teste — um molde "
            "inventado passa em `conjunto_descreve_numeros` e transforma a "
            "guarda do LEIT-09 em cerimonia. A saida e rodar o cortador do "
            "`01-05` apontando o campo da barra onde eles aparecem"
        )
        assert sorted(moldes) == ROTULOS_DA_BARRA

    def test_O_MERGE_NAO_APAGOU_OS_DOIS_PERSONAGENS(self):
        """Uma remontagem do arquivo apagaria o achado M-F por dentro."""
        cal = calibracao()
        assert sorted(cal.renda_por_personagem) == ["Faerlina", "Yazalaque"]

    def test_OS_DOIS_RETANGULOS_DE_NIVEL_CONTINUAM_DISTINTOS(self):
        """O M-F preso dentro da fixtura: as duas janelas de status DIFEREM."""
        cal = calibracao()
        faerlina = cal.renda_do_personagem("Faerlina")["nivel"]["regiao"]
        yazalaque = cal.renda_do_personagem("Yazalaque")["nivel"]["regiao"]
        assert faerlina != yazalaque, (
            "os dois retangulos de nivel viraram um so: ou a fixtura foi "
            "remontada a partir do que alguem lembrava, ou o M-F foi desfeito"
        )

    def test_O_CONJUNTO_TRAZ_OS_DOIS_LIMIARES_E_A_FOLGA_FECHADA(self):
        conjunto = conjunto_de_moldes()
        assert isinstance(conjunto["piso_de_leitura"], float)
        assert isinstance(conjunto["margem_de_leitura"], float)
        assert conjunto["folga_de_cola"] is None, (
            "a folga de cola da barra nasce fechada: com uma folga inteira, "
            "`particionar_run` fatiaria um icone de moeda em tres digitos de "
            "largura permitida e a ferramenta FABRICARIA numero"
        )

    def test_O_ARQUIVO_CONTINUA_SENDO_JSON_LEGIVEL_A_MAO(self):
        dados = json.loads(CALIBRACAO_DE_FIXTURE.read_text(encoding="utf-8"))
        assert "renda_moldes_da_barra" in dados
        assert "renda_por_personagem" in dados


class TestQueAAdenaSaiuDoOCR:
    """O portao da troca de leitor, sobre a ARVORE DE SINTAXE e nao sobre grep.

    A adena saiu do OCR por medicao (M-G, M-H). Voltar por atalho — "e so
    chamar o motor de texto aqui, e mais simples" — tem de derrubar um teste em
    vez de passar despercebido.
    """

    @staticmethod
    def _corpo_de(nome: str) -> ast.FunctionDef:
        arvore = ast.parse(FONTE_DO_MODULO_PURO.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.FunctionDef) and no.name == nome:
                return no
        raise AssertionError(f"{nome} sumiu de renda_leitura.py")

    def test_O_CORPO_DE_adena_da_barra_NAO_CHAMA_O_MOTOR_DE_TEXTO(self):
        proibidos = {"ler_texto", "ler_texto_" + "ampliado"}
        chamados = {
            getattr(no.func, "id", None)
            for no in ast.walk(self._corpo_de("adena_da_barra"))
            if isinstance(no, ast.Call)
        }
        assert not (chamados & proibidos), (
            f"a adena voltou a chamar OCR ({chamados & proibidos}). Medido: a "
            "regra de abstencao aceita 106.020 e 91 naquele campo (M-G), e "
            "quando as duas escalas concordam elas concordam na L-Coin, 173 "
            "vezes em 173 (M-H)"
        )

    def test_CONTROLE_O_NIVEL_E_O_EXP_CONTINUAM_CHAMANDO_O_MOTOR(self):
        """Sem este controle, o portao acima passaria num modulo sem OCR nenhum."""
        for nome in ("nivel_da_regiao", "exp_da_barra"):
            chamados = {
                getattr(no.func, "id", None)
                for no in ast.walk(self._corpo_de(nome))
                if isinstance(no, ast.Call)
            }
            assert "ler_texto" in chamados, nome

    def test_A_REFUTACAO_DOS_MOLDES_DO_NIVEL_ESTA_NO_FONTE(self):
        """O `ROADMAP.md` exige a medicao ao lado de todo numero que caiu."""
        corpo = FONTE_DO_MODULO_PURO.read_text(encoding="utf-8")
        assert "conjunto_descreve_numeros" in corpo

    def test_A_PENEIRA_DE_FORMA_CONTINUA_SENDO_UMA_SO(self):
        """Ela e do `01-05`. Esta onda a CONSOME e nao escreve uma segunda."""
        arvore = ast.parse(FONTE_DO_MODULO_PURO.read_text(encoding="utf-8"))
        definicoes = [
            no.name
            for no in ast.walk(arvore)
            if isinstance(no, ast.FunctionDef) and no.name == "_glifos_do_numero"
        ]
        assert len(definicoes) == 1, (
            "nasceu uma segunda peneira: os moldes seriam cortados de um "
            "conjunto de corridas e lidos de outro, e o desalinhamento "
            "apareceria como pontuacao baixa que alguem consertaria baixando "
            "o piso"
        )


class TestAAdenaContraPixelReal:
    """Cinco fixturas de campo, verdade escrita, e NENHUM OCR envolvido."""

    @pytest.mark.parametrize("fixtura,verdade", sorted(ADENA_POR_FIXTURA.items()))
    def test_A_ADENA_SAI_COMO_A_VERDADE_DE_CAMPO(self, fixtura, verdade):
        lido = ler_a_adena(recorte_da_adena(fixtura), piso_de_brilho=185)
        assert isinstance(lido, rl.ValorDaAdena), lido
        assert lido.valor == verdade, f"{fixtura}: {lido}"

    @pytest.mark.parametrize("piso", BANDA_DE_GLIFO)
    @pytest.mark.parametrize(
        "fixtura", ["campo_faerlina_f000", "campo_yazalaque_f001"]
    )
    def test_A_BANDA_DE_GLIFO_E_LARGA_E_OS_DOIS_EXTREMOS_LEEM_IGUAL(
        self, fixtura, piso
    ):
        """A banda larga foi o que a troca de leitor COMPROU.

        O OCR daquele campo tinha banda de largura UM passo (M-G): o piso
        vizinho devolvia lixo valido. Afirmar os dois extremos e o que impede
        alguem de estreita-la de volta sem perceber.
        """
        lido = ler_a_adena(recorte_da_adena(fixtura), piso_de_brilho=piso)
        assert isinstance(lido, rl.ValorDaAdena), (piso, lido)
        assert lido.valor == ADENA_POR_FIXTURA[fixtura], (piso, lido)

    def test_A_ADENA_NAO_FINGE_UMA_GUARDA_QUE_NAO_TEM(self):
        """`escalas` afirmaria um cruzamento que este campo nao faz (T-01-43)."""
        lido = ler_a_adena(recorte_da_adena("campo_faerlina_f000"), piso_de_brilho=185)
        assert not hasattr(lido, "escalas"), (
            "a adena ganhou `escalas`. Ela tem UM metodo de leitura: um "
            "`escalas = 1` aqui seria indistinguivel do `escalas = 1` do "
            "nivel, que significa outra coisa — la a segunda escala existe e "
            "ABSTEVE, aqui ela nunca existiu"
        )
        assert lido.glifos == 10, (
            "o que ela carrega e a guarda que ela REALMENTE tem: 13.160.684 "
            f"sao oito digitos e duas virgulas, e saiu {lido}"
        )

    def test_A_STRING_DOS_GLIFOS_PASSA_PELAS_DUAS_FUNCOES_DO_MERCADO(self):
        lido = ler_a_adena(recorte_da_adena("campo_yazalaque_f001"), piso_de_brilho=185)
        assert numero_valido(lido.texto)
        assert inteiro_de_quantidade(lido.texto) == lido.valor


class TestOsControlesNegativosReais:
    """Os tres numeros que a medicao capturou errados NAO voltam. Grade inteira.

    Sem esta classe, a troca de leitor e uma afirmacao de prosa.
    """

    def test_A_GRADE_DE_PISOS_INTEIRA_NUNCA_DEVOLVE_UM_DOS_TRES(self):
        achados = []
        for fixtura in ADENA_POR_FIXTURA:
            recorte = recorte_da_adena(fixtura)
            for piso in range(0, 256, 5):
                lido = ler_a_adena(recorte, piso_de_brilho=piso)
                if not isinstance(lido, rl.ValorDaAdena):
                    continue
                if lido.valor in NUMEROS_ERRADOS_DE_CAMPO:
                    achados.append((fixtura, piso, lido.valor))
        assert not achados, (
            "o caminho de glifo devolveu um dos numeros que a medicao de campo "
            "capturou ERRADOS:\n  "
            + "\n  ".join(
                f"{fix} piso {piso} -> {valor} "
                f"({NUMEROS_ERRADOS_DE_CAMPO[valor]})"
                for fix, piso, valor in achados
            )
        )

    def test_DENTRO_DA_BANDA_MEDIDA_E_O_VALOR_CERTO_OU_RECUSA(self):
        """Na banda, nao existe terceiro desfecho. FORA dela existe — ver abaixo."""
        errados = []
        for fixtura, verdade in ADENA_POR_FIXTURA.items():
            recorte = recorte_da_adena(fixtura)
            for piso in BANDA_DE_GLIFO:
                lido = ler_a_adena(recorte, piso_de_brilho=piso)
                if isinstance(lido, rl.ValorDaAdena) and lido.valor != verdade:
                    errados.append((fixtura, piso, lido.valor, verdade))
        assert not errados, errados

    def test_O_CAMINHO_DE_GLIFO_NAO_E_IMUNE_A_SUBSTITUICAO_FORA_DA_BANDA(self):
        """MEDIDO NESTA ARVORE, e escrito em vez de vendido como fechado.

        Varrida a grade inteira, a Yazalaque le `1.646.020` no lugar de
        `1.696.020` num piso ABAIXO da banda: um `9` casado como `4`, com a
        gramatica de milhar inteira satisfeita e a forma do recorte perfeita.

        **Este teste existe para que a frase "o caminho de glifo resolveu a
        adena" nunca seja escrita sem qualificacao.** Ele resolveu o problema
        de QUAL CAMPO — a L-Coin nunca mais sai —, e nao resolveu o de QUAL
        DIGITO. Contra substituicao a defesa continua sendo a regra de par
        (`tests/test_renda_par.py`), e nao a peneira de forma.

        Se um dia esta busca nao achar mais nenhuma substituicao, o teste
        FALHA: o mundo mudou, e o comentario acima precisa mudar junto.
        """
        substituicoes = []
        for fixtura, verdade in ADENA_POR_FIXTURA.items():
            recorte = recorte_da_adena(fixtura)
            for piso in range(0, 256):
                lido = ler_a_adena(recorte, piso_de_brilho=piso)
                if isinstance(lido, rl.ValorDaAdena) and lido.valor != verdade:
                    substituicoes.append((fixtura, piso, lido.valor, verdade))
        assert substituicoes, (
            "nenhuma substituicao apareceu na grade inteira. Isso e bom, e "
            "muda a prosa deste arquivo: a docstring afirma que o caminho de "
            "glifo NAO defende contra substituicao, e a afirmacao precisa ser "
            "remedida antes de continuar escrita"
        )
        for _, piso, _, _ in substituicoes:
            assert piso < min(BANDA_DE_GLIFO), (
                "uma substituicao apareceu DENTRO da banda medida, e a banda "
                f"era o que a troca de leitor comprou: {substituicoes}"
            )


class TestOParPosicionalDoDescarte:
    """Descartar por largura sem olhar a POSICAO apagaria um digito.

    O par exercita `adena_da_barra` e nao a peneira isolada — os casos
    unitarios de `_glifos_do_numero` sao do `01-05`.
    """

    def test_UM_ICONE_LARGO_EM_CADA_PONTA_E_O_NUMERO_DO_MEIO_SAI(self):
        lido = ler_a_adena(recorte_da_adena("campo_faerlina_f000"), piso_de_brilho=185)
        assert isinstance(lido, rl.ValorDaAdena)
        assert lido.valor == 13_160_684

    def test_UM_RUN_LARGO_NO_MEIO_DERRUBA_A_LEITURA_INTEIRA(self):
        """Ele NAO e descartado: descartar devolveria um numero mais curto.

        O recorte e montado colando o icone da ponta esquerda no meio dos
        digitos. Um leitor que descartasse "todo run largo" leria oito digitos
        onde ha um icone no meio, e devolveria um numero plausivel e errado.
        """
        original = recorte_da_adena("campo_faerlina_f000")
        icone = original[:, 0:14]
        com_icone_no_meio = np.concatenate(
            [original[:, :100], icone, original[:, 100:]], axis=1
        )
        lido = ler_a_adena(com_icone_no_meio, piso_de_brilho=185)
        assert isinstance(lido, rl.RecusaDaRenda), lido
        assert lido.motivo == rl.MOTIVO_DA_FORMA
        assert "MEIO" in lido.detalhe or "PONTA" in lido.detalhe

    def test_UMA_PONTA_LARGA_SO_E_RECUSA_DE_FORMA(self):
        """Zero ou duas de um lado: o recorte deixou de conter UM numero."""
        sem_o_icone_da_esquerda = recorte_da_adena("campo_faerlina_f000")[:, 20:]
        lido = ler_a_adena(sem_o_icone_da_esquerda, piso_de_brilho=185)
        assert isinstance(lido, rl.RecusaDaRenda), lido
        assert lido.motivo == rl.MOTIVO_DA_FORMA


class TestAGuardaDoConjuntoDeMoldes:
    """A clausula 3 do LEIT-09: meio conjunto NAO produz meia leitura."""

    def test_AUSENTE_E_INCOMPLETO_PRODUZEM_A_MESMA_RECUSA(self):
        """O conserto e o mesmo, e quem le a tela nao precisa da distincao."""
        recorte = recorte_da_adena("campo_faerlina_f000")
        ausente = ler_a_adena(recorte, piso_de_brilho=185, moldes={})
        incompletos = {k: v for k, v in moldes_decodificados().items() if k != "8"}
        incompleto = ler_a_adena(recorte, piso_de_brilho=185, moldes=incompletos)
        assert ausente.motivo == incompleto.motivo == rl.MOTIVO_DO_CONJUNTO_DE_MOLDES

    def test_A_MENSAGEM_LISTA_OS_ROTULOS_QUE_FALTAM_POR_NOME(self):
        """"faltam 3" nao diz onde procurar; "faltam '5', '7'" diz."""
        incompletos = {
            k: v for k, v in moldes_decodificados().items() if k not in "57"
        }
        recusa = ler_a_adena(
            recorte_da_adena("campo_faerlina_f000"),
            piso_de_brilho=185,
            moldes=incompletos,
        )
        assert "'5'" in recusa.detalhe and "'7'" in recusa.detalhe, recusa.detalhe

    def test_O_CONSERTO_ANUNCIADO_E_UM_COMANDO_E_NAO_O_TEMPO(self):
        """O M-L derrubou o conserto antigo, e a mensagem mudou junto.

        Ate o M-L, a recusa mandava FARMAR ate o digito aparecer. Medido, o `5`
        e o `7` ja estao na tela em outros campos da mesma barra, e o cortador
        colhe de qualquer campo. Um conserto que aponta para o TEMPO e um que
        aponta para um COMANDO sao coisas diferentes de dizer a um usuario.
        """
        recusa = ler_a_adena(
            recorte_da_adena("campo_faerlina_f000"), piso_de_brilho=185, moldes={}
        )
        assert "calibrar-renda-moldes" in recusa.detalhe
        assert "--campo" in recusa.detalhe

    def test_COM_UM_CONJUNTO_SEM_O_CINCO_UM_RECORTE_COM_CINCO_RECUSA(self):
        """O caso que torna a guarda NAO-cerimonial.

        `15.134.779` contem um `5`. Sem o molde do `5`, um leitor sem esta
        guarda casaria aquele glifo contra o molde mais parecido e devolveria
        um numero com o digito TROCADO — que passa na gramatica inteira. A
        medicao que sustenta isso esta na docstring de
        `conjunto_descreve_numeros`: um `8` sem molde de `8` casa com `0` a
        0,7826 contra piso 0,4698, e a margem tambem nao pega.
        """
        sem_o_cinco = {k: v for k, v in moldes_decodificados().items() if k != "5"}
        lido = ler_a_adena(
            recorte_da_adena("segundo_cenario_faerlina"),
            piso_de_brilho=185,
            moldes=sem_o_cinco,
        )
        assert isinstance(lido, rl.RecusaDaRenda), (
            "a adena devolveu numero com o conjunto pela metade. Esta e a "
            f"falha ABERTA do LEIT-09 acontecendo: {lido}"
        )
        assert lido.motivo == rl.MOTIVO_DO_CONJUNTO_DE_MOLDES

    def test_A_RECUSA_DE_CONJUNTO_E_DISTINTA_DAS_OUTRAS_TRES(self):
        recorte = recorte_da_adena("campo_faerlina_f000")
        conjunto = ler_a_adena(recorte, piso_de_brilho=185, moldes={}).motivo
        vazio = ler_a_adena(np.zeros_like(recorte), piso_de_brilho=185).motivo
        forma = ler_a_adena(recorte[:, 20:], piso_de_brilho=185).motivo
        assert len({conjunto, vazio, forma, rl.MOTIVO_DA_GRAMATICA}) == 4, (
            "dois motivos com consertos diferentes viraram um so: "
            f"{conjunto}, {vazio}, {forma}, {rl.MOTIVO_DA_GRAMATICA}"
        )


class TestAGramaticaAconteceDEPOISDosGlifos:
    """A validacao nao esta no lugar dos glifos: ela esta DEPOIS deles."""

    def test_UMA_VIRGULA_FORA_DO_LUGAR_E_RECUSA_DE_GRAMATICA(self, monkeypatch):
        """`1,69,6020` — a virgula de milhar no lugar errado.

        O caso e montado interceptando `ler_glifos` porque nenhum pixel desta
        arvore produz essa string: o que se afirma aqui e a ORDEM das etapas, e
        nao a probabilidade da entrada. Um leitor que convertesse direto do
        casamento devolveria `1696020` — o numero certo por acidente, a partir
        de uma leitura que a tela nunca mostrou.
        """
        monkeypatch.setattr(rl, "ler_glifos", lambda *a, **k: "1,69,6020")
        lido = ler_a_adena(
            recorte_da_adena("campo_yazalaque_f001"), piso_de_brilho=185
        )
        assert isinstance(lido, rl.RecusaDaRenda), lido
        assert lido.motivo == rl.MOTIVO_DA_GRAMATICA
        assert "1,69,6020" in lido.detalhe

    def test_UMA_PONTUACAO_QUE_NAO_FECHA_E_RECUSA_PROPRIA_E_NAO_GRAMATICA(
        self, monkeypatch
    ):
        """TUDO OU NADA: `ler_glifos` devolvendo nada tem motivo proprio."""
        monkeypatch.setattr(rl, "ler_glifos", lambda *a, **k: None)
        lido = ler_a_adena(
            recorte_da_adena("campo_yazalaque_f001"), piso_de_brilho=185
        )
        assert lido.motivo == rl.MOTIVO_DA_PONTUACAO
        assert lido.motivo != rl.MOTIVO_DA_GRAMATICA

    def test_UM_RECORTE_TODO_PRETO_E_CAMPO_VAZIO(self):
        recorte = np.zeros_like(recorte_da_adena("campo_faerlina_f000"))
        lido = ler_a_adena(recorte, piso_de_brilho=185)
        assert lido.motivo == rl.MOTIVO_DO_CAMPO_VAZIO


class TestAGramaticaDoNivel:
    """Ela nao precisa de OCR: e string entrando e inteiro saindo."""

    @pytest.mark.parametrize("texto,esperado", [("67", 67), (" 69 ", 69), ("1", 1)])
    def test_UM_INTEIRO_NU_ATRAVESSA(self, texto, esperado):
        assert rl.inteiro_do_nivel(texto) == esperado

    @pytest.mark.parametrize("texto", ["6b", "(37", "6 7", "", None, "67%"])
    def test_UM_CARACTERE_QUE_NAO_E_DIGITO_E_RECUSA_E_NAO_TRUNCAMENTO(self, texto):
        """M20: a leitura errada que o proprio roadmap cita ja cai aqui.

        E o ponto nao e ela cair: e ela cair INTEIRA. Extrair "os digitos que
        der" de `(37` devolveria `37`, que e um nivel plausivel e errado.
        """
        assert rl.inteiro_do_nivel(texto) is None

    def test_M22_NENHUMA_DAS_DUAS_FUNCOES_DO_MERCADO_BASTA_SOZINHA(self):
        """O XM, vizinho de recorte da adena, e a prova com nome de campo."""
        assert numero_valido("58,40") is True
        assert inteiro_de_quantidade("58,40") is None
        assert numero_valido("1234") is False
        assert inteiro_de_quantidade("1234") == 1234
        assert rl.inteiro_do_nivel("58,40") is None
        assert rl.inteiro_do_nivel("1234") is None

    def test_M18_O_L_COIN_PASSA_NA_GRAMATICA_INTEIRA(self):
        """A forma NAO distingue L-Coin de adena. So a POSICAO distingue.

        E foi por isso que a adena saiu do OCR: um cruzamento entre duas
        leituras do mesmo pixel nao tem como distinguir "leu o campo certo
        errado" de "leu o campo do lado certo".
        """
        assert numero_valido("13,091") is True
        assert inteiro_de_quantidade("13,091") == 13_091


@precisa_de_ocr
class TestONivelContraPixelReal:
    """Os dois recortes RESGATADOS da gravacao de campo, verdade lida a olho."""

    @pytest.mark.parametrize(
        "personagem,verdade", sorted(NIVEL_POR_PERSONAGEM.items())
    )
    def test_O_NIVEL_SAI_COMO_A_VERDADE_DE_CAMPO(self, personagem, verdade):
        piso = calibracao().renda_do_personagem(personagem)["nivel"]["piso_de_brilho"]
        lido = rl.nivel_da_regiao(recorte_do_nivel(personagem), piso_de_brilho=piso)
        assert isinstance(lido, rl.ValorDaRenda), lido
        assert lido.valor == verdade

    def test_O_NIVEL_DA_FAERLINA_SAI_POR_UMA_ESCALA_SO(self):
        """O caso de campo do M-D, e ele e a razao de a regra ser por ABSTENCAO.

        A escala 2x devolve vazio em toda a banda util deste campo. Sob a regra
        antiga — "as duas tem de dar o mesmo numero" — este nivel seria
        recusado PARA SEMPRE, e recusar 100% das amostras e o mesmo que nao ter
        medidor.
        """
        piso = calibracao().renda_do_personagem("Faerlina")["nivel"]["piso_de_brilho"]
        lido = rl.nivel_da_regiao(recorte_do_nivel("Faerlina"), piso_de_brilho=piso)
        assert lido.valor == 67
        assert lido.escalas == 1, (
            "o nivel da Faerlina passou a sair por duas escalas. Se isso for "
            "verdade, otimo — mas a docstring de `_cruzar_as_escalas` cita "
            f"este campo como o caso de abstencao, e precisa mudar junto: {lido}"
        )

    def test_A_REGIAO_PRETA_DA_MONTAGEM_E_CAMPO_VAZIO(self):
        montagem = cv2.imread(str(MONTAGEM_COM_O_NIVEL_PRETO))
        cal = calibracao()
        bloco = cal.renda_do_personagem("Faerlina")["nivel"]
        recorte = rl.recortar(
            montagem, Regiao.de_dict(bloco["regiao"]), campo=rl.CAMPO_DO_NIVEL
        )
        lido = rl.nivel_da_regiao(recorte, piso_de_brilho=bloco["piso_de_brilho"])
        assert lido.motivo == rl.MOTIVO_DO_CAMPO_VAZIO
        assert lido.motivo != rl.MOTIVO_DA_GRAMATICA, (
            "campo vazio e gramatica PARECEM a mesma coisa e nao sao: o "
            "primeiro aponta para o retangulo ou o piso, o segundo so para o "
            "piso"
        )


@precisa_de_ocr
class TestOControleDaMascara:
    """As DUAS quedas da premissa do LEIT-03, cada uma com o seu numero.

    O `ROADMAP.md` dizia: *"o OCR ja devolve a adena do recorte cru, sem
    pre-processamento"*. As duas metades cairam.
    """

    def test_O_RECORTE_CRU_DA_ADENA_DEVOLVE_VAZIO_NAS_DUAS_ESCALAS(self):
        """M-E: com fundo de grama clara, o cru nao mostra a adena."""
        for fixtura in ("campo_faerlina_f000", "campo_yazalaque_f001"):
            recorte = recorte_da_adena(fixtura)
            assert ocr.ler_texto(recorte).strip() == "", fixtura
            assert ocr.ler_texto_ampliado(recorte).strip() == "", fixtura

    def test_E_A_MASCARA_SOZINHA_TAMBEM_NAO_BASTAVA(self):
        """A segunda metade, e ela e a que tirou o campo do OCR.

        NO PISO CALIBRADO — o mesmo em que o caminho de glifo le os oito
        digitos certos — as duas escalas de OCR devolvem texto que nao passa na
        gramatica. Nao e uma leitura pior: e nenhuma leitura, no ponto em que o
        outro caminho le perfeito.

        (Os numeros do M-G — `106.020` e `91` — foram medidos sobre o retangulo
        `1500,1360 200x32`, que o M-O depois refutou. Este teste afirma o que a
        MESMA falha produz sobre o retangulo que vale hoje, em vez de citar um
        numero de um recorte que nao existe mais.)
        """
        from l2scanner.mercado_leitura import mascara_de_numero

        for fixtura in ("campo_faerlina_f000", "campo_yazalaque_f001"):
            recorte = recorte_da_adena(fixtura)
            tinta = (mascara_de_numero(recorte, 185) * 255).astype(np.uint8)
            por_ocr = [
                rl.inteiro_do_nivel(ocr.ler_texto(tinta)),
                rl.inteiro_do_nivel(ocr.ler_texto_ampliado(tinta)),
            ]
            assert por_ocr == [None, None], (
                f"{fixtura}: o OCR mascarado leu {por_ocr} no piso calibrado. "
                "Se ele passou a ler certo, a decisao de tirar a adena do OCR "
                "continua valendo pelo M-H (173 concordancias na L-Coin), mas "
                "esta docstring precisa ser remedida"
            )

    def test_E_O_CAMINHO_DE_GLIFO_LE_NO_MESMO_PISO_EM_QUE_O_OCR_E_CEGO(self):
        for fixtura, verdade in (
            ("campo_faerlina_f000", 13_160_684),
            ("campo_yazalaque_f001", 1_696_020),
        ):
            lido = ler_a_adena(recorte_da_adena(fixtura), piso_de_brilho=185)
            assert lido.valor == verdade


@precisa_de_ocr
class TestALeituraEDeUmPersonagemNomeado:
    """LEIT-07: nunca ha queda para a entrada do vizinho."""

    def test_O_FRAME_DA_FAERLINA_LIDO_COMO_YAZALAQUE_NAO_DEVOLVE_67(self):
        cal = calibracao()
        frame = cv2.imread(str(MONTAGEM_COMPLETA))
        campos = rl.ler_os_tres_campos(
            frame, personagem="Yazalaque", calibracao=cal
        )
        faerlina = cal.renda_do_personagem("Faerlina")["nivel"]["regiao"]
        yazalaque = cal.renda_do_personagem("Yazalaque")["nivel"]["regiao"]
        valor = getattr(campos.nivel, "valor", None)
        assert valor != 67, (
            "a leitura caiu no retangulo do vizinho e devolveu o nivel da "
            f"Faerlina.\n  retangulo da Faerlina:  {faerlina}\n"
            f"  retangulo da Yazalaque: {yazalaque}\n"
            "O retangulo do vizinho nao devolve campo vazio que alguem nota: "
            "devolve 349 ou 112, que passam por qualquer validacao"
        )

    def test_UM_PERSONAGEM_SEM_CALIBRACAO_RECUSA_NOS_TRES_CAMPOS(self):
        frame = cv2.imread(str(MONTAGEM_COMPLETA))
        campos = rl.ler_os_tres_campos(
            frame, personagem="Korzis", calibracao=calibracao()
        )
        motivos = {r.motivo for r in campos.por_campo.values()}
        assert motivos == {rl.MOTIVO_DO_PERSONAGEM}
        assert rl.MOTIVO_DO_PERSONAGEM not in {
            rl.MOTIVO_DO_CAMPO_VAZIO,
            rl.MOTIVO_DA_GRAMATICA,
        }

    def test_A_RECUSA_DE_PERSONAGEM_NOMEIA_QUEM_ESTA_CALIBRADO(self):
        campos = rl.ler_os_tres_campos(
            cv2.imread(str(MONTAGEM_COMPLETA)),
            personagem="Korzis",
            calibracao=calibracao(),
        )
        assert "Korzis" in campos.nivel.detalhe
        assert "Faerlina" in campos.nivel.detalhe


@precisa_de_ocr
class TestACompoicaoDosTresCampos:
    """Um campo que recusou NAO impede os outros dois de serem lidos."""

    def test_A_MONTAGEM_COMPLETA_DA_OS_TRES_COMO_NUMERO(self):
        campos = rl.ler_os_tres_campos(
            cv2.imread(str(MONTAGEM_COMPLETA)),
            personagem="Faerlina",
            calibracao=calibracao(),
        )
        assert campos.nivel.valor == 67
        assert campos.exp.valor == 80_012
        assert campos.adena.valor == 13_160_684

    def test_COM_O_NIVEL_PRETO_OS_OUTROS_DOIS_CONTINUAM_SAINDO(self):
        """O criterio 1 pede os TRES na tela, inclusive quando um recusou."""
        campos = rl.ler_os_tres_campos(
            cv2.imread(str(MONTAGEM_COM_O_NIVEL_PRETO)),
            personagem="Faerlina",
            calibracao=calibracao(),
        )
        assert campos.nivel.motivo == rl.MOTIVO_DO_CAMPO_VAZIO
        assert campos.exp.valor == 80_012
        assert campos.adena.valor == 13_160_684

    def test_ler_a_renda_DEVOLVE_A_LEITURA_QUANDO_OS_TRES_SAEM(self):
        leitura = rl.ler_a_renda(
            cv2.imread(str(MONTAGEM_COMPLETA)),
            personagem="Faerlina",
            calibracao=calibracao(),
            carimbo=1.0,
        )
        assert isinstance(leitura, rl.LeituraDaRenda)
        assert (leitura.nivel, leitura.exp, leitura.adena) == (
            67,
            80_012,
            13_160_684,
        )
        assert leitura.carimbo == 1.0
        assert leitura.personagem == "Faerlina"

    def test_ler_a_renda_DEVOLVE_A_RECUSA_DO_PRIMEIRO_CAMPO_EM_FALTA(self):
        """A ordem e DECLARADA para que duas rodadas iguais recusem igual."""
        recusa = rl.ler_a_renda(
            cv2.imread(str(MONTAGEM_COM_O_NIVEL_PRETO)),
            personagem="Faerlina",
            calibracao=calibracao(),
            carimbo=1.0,
        )
        assert isinstance(recusa, rl.RecusaDaRenda)
        assert recusa.campo == rl.ORDEM_DOS_CAMPOS[0] == rl.CAMPO_DO_NIVEL

    def test_TUDO_QUE_ATRAVESSA_A_FRONTEIRA_E_INTEIRO(self):
        leitura = rl.ler_a_renda(
            cv2.imread(str(MONTAGEM_COMPLETA)),
            personagem="Faerlina",
            calibracao=calibracao(),
            carimbo=1.0,
        )
        for campo in ("nivel", "exp", "adena"):
            valor = getattr(leitura, campo)
            assert isinstance(valor, int) and not isinstance(valor, bool), campo


class TestOsDoisLeitoresDeOCRCruzamAsEscalas:
    """A decisao e a de PRODUCAO, e nao uma comparacao escrita a mao."""

    def test_O_NIVEL_USA_A_MESMA_FUNCAO_QUE_O_EXP(self):
        arvore = ast.parse(FONTE_DO_MODULO_PURO.read_text(encoding="utf-8"))
        chamadas = [
            no
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call)
            and getattr(no.func, "id", None) == "_cruzar_as_escalas"
        ]
        assert len(chamadas) >= 2, (
            "so um campo cruza as escalas. Uma segunda implementacao da regra "
            "e uma segunda chance de implementar a regra errada"
        )

    def test_UMA_VALIDA_COM_A_OUTRA_ABSTENDO_ACEITA_COM_UMA_ESCALA(self):
        """Sem OCR: o cruzamento e testavel com um par montado a mao."""
        lido = rl._cruzar_as_escalas(rl.CAMPO_DO_NIVEL, [("", None), ("67", 67)])
        assert isinstance(lido, rl.ValorDaRenda)
        assert (lido.valor, lido.escalas) == (67, 1)

    def test_DUAS_VALIDAS_E_DIFERENTES_RECUSAM_COM_AS_CRUAS_NO_DETALHE(self):
        lido = rl._cruzar_as_escalas(rl.CAMPO_DO_NIVEL, [("67", 67), ("57", 57)])
        assert lido.motivo == rl.MOTIVO_DA_DISCORDANCIA
        assert ">>>67<<<" in lido.detalhe and ">>>57<<<" in lido.detalhe


@precisa_de_ocr
class TestOComandoImprimeOsTresCampos:
    """O criterio 1 num olhar, e verificavel SEM o jogo aberto."""

    @staticmethod
    def _rodar(imagem, personagem="Faerlina"):
        return renda_modo.main(
            [
                "--imagem",
                str(imagem),
                "--personagem",
                personagem,
                "--calibracao",
                str(CALIBRACAO_DE_FIXTURE),
            ]
        )

    def test_A_MONTAGEM_COMPLETA_IMPRIME_OS_TRES_E_SAI_EM_ZERO(self, capsys):
        """O DESFECHO (a): "criterio 1 fechado", com a adena como NUMERO."""
        codigo = self._rodar(MONTAGEM_COMPLETA)
        saida = capsys.readouterr().out
        assert codigo == renda_modo.SAIDA_OK, saida
        assert "67" in saida
        assert "8,0012%" in saida
        assert "13.160.684" in saida, (
            "a adena nao saiu na grafia de milhar do jogo. O criterio 1 e uma "
            "comparacao entre o terminal e o monitor, e uma comparacao so "
            f"funciona se as duas grafias forem a mesma:\n{saida}"
        )

    def test_AS_TRES_LINHAS_SAEM_NA_ORDEM_DA_TELA(self, capsys):
        self._rodar(MONTAGEM_COMPLETA)
        saida = capsys.readouterr().out
        posicoes = [saida.find("67"), saida.find("8,0012%"), saida.find("13.160.684")]
        assert all(p >= 0 for p in posicoes), saida
        assert posicoes == sorted(posicoes), saida

    def test_A_MONTAGEM_COM_O_NIVEL_PRETO_SAI_COM_O_CODIGO_DE_RECUSA(self, capsys):
        codigo = self._rodar(MONTAGEM_COM_O_NIVEL_PRETO)
        capturado = capsys.readouterr()
        saida = capturado.out + capturado.err
        assert codigo == renda_modo.SAIDA_RECUSA, saida
        assert codigo not in (renda_modo.SAIDA_OK, renda_modo.SAIDA_OPERACIONAL)
        assert rl.MOTIVO_DO_CAMPO_VAZIO in saida
        assert "8,0012%" in saida, (
            "o EXP sumiu porque o nivel recusou. O criterio 1 pede os TRES na "
            f"tela, inclusive quando um recusou:\n{saida}"
        )
        assert "13.160.684" in saida

    def test_UM_CAMPO_DE_UMA_ESCALA_SO_SAI_MARCADO_COM_LEGENDA(self, capsys):
        """O nivel da Faerlina e o caso de campo: 3x le, 2x abstem (M-D)."""
        self._rodar(MONTAGEM_COMPLETA)
        saida = capsys.readouterr().out
        linha_do_nivel = [
            linha for linha in saida.splitlines() if "67" in linha and "*" in linha
        ]
        assert linha_do_nivel, (
            "o nivel saiu sem marca. Naquele campo o cruzamento NAO esta "
            "pegando substituicao de digito, e o unico verificador que resta e "
            f"o olho de quem compara o terminal com o monitor:\n{saida}"
        )
        assert "escala" in saida.lower()

    def test_UM_CAMINHO_DE_CALIBRACAO_INEXISTENTE_SAI_EM_UM_SEM_TRACEBACK(
        self, capsys, tmp_path
    ):
        """Quebrou e recusou sao desfechos diferentes."""
        codigo = renda_modo.main(
            [
                "--imagem",
                str(MONTAGEM_COMPLETA),
                "--personagem",
                "Faerlina",
                "--calibracao",
                str(tmp_path / "nao-existe.json"),
            ]
        )
        erro = capsys.readouterr().err
        assert codigo == renda_modo.SAIDA_OPERACIONAL
        assert "Traceback" not in erro

    def test_O_CABECALHO_TRAZ_O_PERSONAGEM_E_A_FONTE_DE_PIXEL(self, capsys):
        """Com duas instancias abertas, uma leitura anonima nao descreve ninguem."""
        self._rodar(MONTAGEM_COMPLETA)
        saida = capsys.readouterr().out
        assert "Faerlina" in saida
        assert MONTAGEM_COMPLETA.name in saida


class TestQueOComandoNaoTemUmaSegundaEscala:
    """A grafia e FORMATACAO, e nao uma segunda escala escrita a mao."""

    def test_NENHUM_NUMERO_DA_ESCALA_DO_EXP_ENTROU_COMO_LITERAL(self):
        fonte = Path(__file__).parent.parent / "l2scanner" / "renda_modo.py"
        arvore = ast.parse(fonte.read_text(encoding="utf-8"))
        proibidos = {685_632, 1368, 1230}
        achados = [
            (no.lineno, no.value)
            for no in ast.walk(arvore)
            if isinstance(no, ast.Constant)
            and not isinstance(no.value, bool)
            and isinstance(no.value, int)
            and no.value in proibidos
        ]
        assert not achados, achados


class TestAsDuasMontagensNaoSaoRascunhoUmaDaOutra:
    """Cada uma prova um desfecho do comando, e as duas ficam versionadas."""

    def test_A_MONTAGEM_ANTIGA_CONTINUA_COM_A_REGIAO_DO_NIVEL_PRETA(self):
        cal = calibracao()
        regiao = Regiao.de_dict(cal.renda_do_personagem("Faerlina")["nivel"]["regiao"])
        montagem = cv2.imread(str(MONTAGEM_COM_O_NIVEL_PRETO))
        recorte = montagem[
            regiao.topo : regiao.topo + regiao.altura,
            regiao.esquerda : regiao.esquerda + regiao.largura,
        ]
        assert int(recorte.max()) == 0

    def test_A_MONTAGEM_COMPLETA_TEM_O_RECORTE_DE_CAMPO_NO_LUGAR(self):
        cal = calibracao()
        regiao = Regiao.de_dict(cal.renda_do_personagem("Faerlina")["nivel"]["regiao"])
        montagem = cv2.imread(str(MONTAGEM_COMPLETA))
        colado = montagem[
            regiao.topo : regiao.topo + regiao.altura,
            regiao.esquerda : regiao.esquerda + regiao.largura,
        ]
        assert np.array_equal(colado, recorte_do_nivel("Faerlina"))

    def test_AS_DUAS_SO_DIFEREM_NA_REGIAO_DO_NIVEL(self):
        """Elas sao a MESMA tela com uma diferenca so, e isso e o controle."""
        antiga = cv2.imread(str(MONTAGEM_COM_O_NIVEL_PRETO))
        completa = cv2.imread(str(MONTAGEM_COMPLETA))
        cal = calibracao()
        regiao = Regiao.de_dict(cal.renda_do_personagem("Faerlina")["nivel"]["regiao"])
        diferenca = np.any(antiga != completa, axis=2)
        diferenca[
            regiao.topo : regiao.topo + regiao.altura,
            regiao.esquerda : regiao.esquerda + regiao.largura,
        ] = False
        assert not diferenca.any(), (
            "as duas montagens divergem fora da regiao do nivel: elas deixaram "
            "de ser um par controlado e viraram duas telas diferentes"
        )
