"""A varredura de piso do calibrador da renda, sem OCR e sem disco.

O DANO QUE ESTE ARQUIVO IMPEDE. Um calibrador que aceita a primeira leitura
NAO-VAZIA grava um piso de brilho que le um digito ERRADO -- e um digito errado
gravado e indistinguivel de um certo. A curva do roadmap tem exatamente essa
forma: piso baixo devolve vazio, piso do meio devolve `6b`, piso alto devolve
`66`. Um calibrador com DOIS veredictos ("leu" / "nao leu") aceitaria o piso do
meio de bom grado, porque `6b` nao e vazio.

Sao TRES veredictos e nao dois porque os CONSERTOS sao dois diferentes: campo
vazio aponta para o retangulo ou para o jogo estar noutra tela; leitura que nao
respeita a gramatica aponta para o piso de brilho. Somar os dois num veredicto
so faria dois consertos diferentes parecerem o mesmo.

O LIMITE HONESTO DESTA GUARDA, e ele vai escrito para ninguem confundir o que
ela prova: ela pega o `6b` porque o caractere errado NAO E DIGITO. Ela NAO
pegaria a substituicao de um digito por outro -- `66` lido onde a tela diz `68`
passa inteiro. E por isso que a decisao final e do olho do usuario e por isso
que o calibrador imprime a curva em vez de escolher calado.

TODOS OS CASOS DESTE ARQUIVO SAO MONTADOS A MAO. Nenhum abre imagem, nenhum
chama o motor de OCR, nenhum toca disco -- e por isso ele roda no Python global,
que nao tem as bindings de WinRT, sem um skip sequer. A fronteira que torna
isso possivel e o parametro `ler_escalas` de `varrer_o_piso`: ele nao e um
atalho de teste, e a separacao entre o laco que faz OCR e as funcoes puras que
decidem.

A VARREDURA DA `barra_direita` TEM O SEU PROPRIO CONJUNTO DE CASOS, no fim
deste arquivo, e ela nao e a mesma varredura. Aquele campo e classificado pelo
veredicto de GLIFO -- a FORMA das corridas, pela peneira
`renda_leitura._glifos_do_numero`, que este calibrador IMPORTA e nunca
redefine. Duas peneiras seriam duas formas, e o modo de falha seria silencioso
nos dois sentidos por causa da divergencia de convencao de largura do M-P
(`larguras_de_molde` mede `fim - inicio`, o documento de campo mede
`fim - inicio + 1`).

E POR ISSO AS LARGURAS DOS CASOS DE FORMA DESTE ARQUIVO ESTAO TRADUZIDAS. O
criterio de aceitacao do plano cita a sequencia
`[15, 5, 2, 5, 5, 5, 2, 5, 5, 5, 16]`, que esta na convencao INCLUSIVA; na
convencao do CODIGO -- a que a peneira roda -- ela vale
`[14, 4, 1, 4, 4, 4, 1, 4, 4, 4, 15]`. Escrever a primeira aqui teria produzido
uma suite verde medindo uma barra que nao existe.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pytest

import l2scanner.calibrar_renda as cr
from l2scanner.calibracao import Calibracao

RAIZ = Path(__file__).resolve().parent.parent
FONTE_DO_CALIBRADOR = RAIZ / "l2scanner" / "calibrar_renda.py"

GRAMATICA = cr.inteiro_pela_gramatica_do_jogo
DETECCAO = cr.ESCALA_DE_DETECCAO
CONFERENCIA = cr.ESCALA_DE_CONFERENCIA


def _identificadores_do_calibrador() -> set[str]:
    """Todo nome que o calibrador usa COMO CODIGO -- docstring nao conta.

    A distincao existe porque este arquivo tem portoes nos DOIS sentidos: um
    nome que precisa estar no fonte como codigo (`_cruzar_as_escalas`) e um que
    precisa estar SO na prosa (`intersecao_das_bandas`, cuja refutacao fica
    escrita justamente para a funcao nao voltar). Uma busca crua nao distingue
    os dois, e o portao da refutacao nasceria vermelho pedindo que alguem
    apagasse a explicacao para satisfaze-lo.
    """
    arvore = ast.parse(FONTE_DO_CALIBRADOR.read_text(encoding="utf-8"))
    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Name):
            nomes.add(no.id)
        elif isinstance(no, ast.Attribute):
            nomes.add(no.attr)
        elif isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nomes.add(no.name)
        elif isinstance(no, ast.alias):
            nomes.add(no.asname or no.name)
    return nomes


def _varrer(curva: dict[int, tuple[str | None, str | None]]):
    """`{piso: (texto da 2x, texto da 3x)}` -> as linhas da varredura.

    O recorte vai `None` de proposito: se algum caminho desta varredura
    passasse a olhar pixel, ele estouraria aqui em vez de passar medindo outra
    coisa.
    """
    return cr.varrer_o_piso(
        None,
        sorted(curva),
        campo="teste",
        gramatica=GRAMATICA,
        ler_escalas=lambda _recorte, piso: {
            DETECCAO: curva[piso][0],
            CONFERENCIA: curva[piso][1],
        },
    )


class TestOsTresVeredictos:
    """Tres, e nao dois -- e eles precisam ser DISTINGUIVEIS entre si."""

    def test_TEXTO_VAZIO_CLASSIFICA_COMO_VAZIO(self):
        assert cr.classificar_a_leitura("", gramatica=GRAMATICA) == cr.VEREDICTO_VAZIO

    def test_TEXTO_NULO_TAMBEM_CLASSIFICA_COMO_VAZIO(self):
        assert cr.classificar_a_leitura(None, gramatica=GRAMATICA) == cr.VEREDICTO_VAZIO

    def test_SO_ESPACO_EM_BRANCO_CLASSIFICA_COMO_VAZIO(self):
        assert (
            cr.classificar_a_leitura("   ", gramatica=GRAMATICA) == cr.VEREDICTO_VAZIO
        )

    def test_O_6b_CLASSIFICA_COMO_NAO_E_NUMERO(self):
        """O piso do meio da curva do roadmap. Procedencia: `01-ROADMAP`,

        criterio 5, e `01-RESEARCH.md` "Armadilha 5" -- um piso errado por
        vinte devolve digito ERRADO e nao vazio.
        """
        assert (
            cr.classificar_a_leitura("6b", gramatica=GRAMATICA)
            == cr.VEREDICTO_NAO_E_NUMERO
        )

    def test_O_66_CLASSIFICA_COMO_NUMERO_COM_O_INTEIRO_AO_LADO(self):
        assert (
            cr.classificar_a_leitura("66", gramatica=GRAMATICA) == cr.VEREDICTO_NUMERO
        )
        assert GRAMATICA("66") == 66

    def test_OS_TRES_VEREDICTOS_SAO_DISTINTOS_ENTRE_SI(self):
        """Sem este caso, uma implementacao que devolvesse o MESMO simbolo para

        vazio e para nao-numero passaria em todos os outros casos do arquivo --
        e o calibrador voltaria a ter dois veredictos com nome de tres.
        """
        assert len(set(cr.VEREDICTOS)) == 3, cr.VEREDICTOS
        for um in cr.VEREDICTOS:
            for outro in cr.VEREDICTOS:
                if um is not outro:
                    assert um != outro


class TestACurvaDoRoadmap:
    """A curva de tres pisos que o roadmap descreve, exercitada inteira.

    Procedencia: `01-ROADMAP.md`, criterio 5 -- "um piso baixo devolve vazio, o
    do meio devolve `6b`, o alto devolve `66`". Ela e o caso canonico desta
    tarefa e nao um exemplo inventado.
    """

    CURVA = {
        100: ("", ""),
        105: ("6b", "6b"),
        110: ("66", "66"),
    }

    def test_A_BANDA_UTIL_CONTEM_APENAS_O_PISO_ALTO(self):
        banda = cr.resumir_a_banda_util(_varrer(self.CURVA))
        assert banda.pisos == (110,), (
            "o piso do meio entrou na banda util: o calibrador aceitou uma "
            "leitura que NAO E NUMERO e gravaria um piso que le digito errado"
        )

    def test_O_PISO_DO_MEIO_APARECE_NA_SAIDA_COM_O_VEREDICTO_ESCRITO(self):
        linha = {cada.piso: cada for cada in _varrer(self.CURVA)}[105]
        assert not linha.aceito
        assert "NAO E NUMERO" in linha.desfecho, linha.desfecho
        assert "NAO E NUMERO" in linha.como_texto()

    def test_O_PISO_BAIXO_APARECE_COMO_CAMPO_VAZIO_E_NAO_COMO_NAO_NUMERO(self):
        """Os dois consertos sao diferentes; a saida tem de distingui-los."""
        linha = {cada.piso: cada for cada in _varrer(self.CURVA)}[100]
        assert "vazio" in linha.desfecho.lower()
        assert "NAO E NUMERO" not in linha.desfecho


class TestOCruzamentoDecideOQueEntraNaBanda:
    """A decisao vem de `renda_leitura._cruzar_as_escalas`, e nao daqui."""

    def test_AS_DUAS_ESCALAS_COM_NUMEROS_DIFERENTES_FICA_FORA_DA_BANDA(self):
        linhas = _varrer({100: ("66", "68")})
        assert not linhas[0].aceito
        assert "DIFERENTES" in linhas[0].desfecho

    def test_CONTROLE_AS_DUAS_ESCALAS_CONCORDANDO_FICA_DENTRO(self):
        """Sem este controle ao lado, uma implementacao que recusasse TUDO

        passaria no caso acima.
        """
        linhas = _varrer({100: ("66", "66")})
        assert linhas[0].aceito
        assert linhas[0].valor == 66
        assert linhas[0].escalas_que_sustentaram == (DETECCAO, CONFERENCIA)

    def test_UMA_LE_E_A_OUTRA_ABSTEM_FICA_DENTRO_DA_BANDA(self):
        """ABSTENCAO NAO E DISCORDANCIA -- o caso que a medicao de campo obrigou.

        Medido (M-D, `01-MEDICOES-DE-CAMPO.md`): o nivel da Faerlina so sai na
        escala 3x, com a 2x devolvendo vazio em TODA a banda util. Com a regra
        antiga -- "as duas leituras tem que dar o mesmo numero" -- a banda util
        daquele campo seria VAZIA e o calibrador NAO TERIA PISO NENHUM PARA
        GRAVAR.
        """
        linhas = _varrer({100: ("", "67")})
        assert linhas[0].aceito, (
            "um piso em que uma escala le e a outra ABSTEM ficou fora da banda. "
            "Com esta regra o nivel da Faerlina nao teria piso nenhum para "
            "gravar, hoje nem nunca (M-D)."
        )
        assert linhas[0].valor == 67
        assert linhas[0].escalas_que_sustentaram == (CONFERENCIA,)

    def test_UM_PISO_ACEITO_POR_UMA_ESCALA_SO_ENTRA_MARCADO(self):
        linhas = _varrer({100: ("", "67")})
        assert "1 escala" in linhas[0].desfecho, linhas[0].desfecho

    def test_NENHUMA_LINHA_SAI_SEM_O_PISO_AO_LADO(self):
        """Uma linha sem o valor que a produziu e inutil para quem compara com

        a tela do jogo.
        """
        for linha in _varrer({100: ("66", "66"), 105: ("", "")}):
            assert str(linha.piso) in linha.como_texto()


class TestABandaUtilEContigua:
    def test_DOIS_PISOS_COM_UM_BURACO_NO_MEIO_NAO_SAO_UMA_BANDA_DE_DOIS(self):
        """Dois pisos que funcionam com um buraco no meio sao coincidencia, e o

        centro entre eles cai DENTRO do buraco.
        """
        banda = cr.resumir_a_banda_util(
            _varrer({100: ("66", "66"), 105: ("", ""), 110: ("66", "66")})
        )
        assert banda.largura == 1
        assert banda.pisos == (100,)

    def test_A_MAIOR_CORRIDA_CONTIGUA_VENCE_UMA_CURTA_ANTERIOR(self):
        banda = cr.resumir_a_banda_util(
            _varrer(
                {
                    100: ("66", "66"),
                    105: ("", ""),
                    110: ("66", "66"),
                    115: ("66", "66"),
                    120: ("66", "66"),
                }
            )
        )
        assert banda.pisos == (110, 115, 120)


class TestOPisoEscolhidoEOCentro:
    def test_UMA_BANDA_DE_TRES_DEVOLVE_O_DO_MEIO_E_NAO_O_PRIMEIRO(self):
        """Um piso na BORDA da banda funciona hoje e esta a uma mudanca de

        gamma, de monitor ou de skin de cair fora dela. O centro e o unico
        ponto com folga dos dois lados.
        """
        banda = cr.BandaUtil(pisos=(150, 155, 160), sustentada_por=(DETECCAO,))
        assert cr.escolher_o_piso(banda) == 155
        assert cr.escolher_o_piso(banda) != banda.pisos[0]

    def test_UMA_BANDA_DE_CINCO_DEVOLVE_O_TERCEIRO(self):
        banda = cr.BandaUtil(
            pisos=(140, 145, 150, 155, 160), sustentada_por=(DETECCAO,)
        )
        assert cr.escolher_o_piso(banda) == 150

    def test_BANDA_VAZIA_NAO_ESCOLHE_PISO_NENHUM(self):
        assert cr.escolher_o_piso(cr.BandaUtil(pisos=(), sustentada_por=())) is None


class TestALarguraDaBandaEProdutoDePrimeiraClasse:
    """A largura sai junto do piso, e largura 1 ou 2 vira AVISO em voz alta.

    Medido (M-E): a banda util da adena da Faerlina tinha largura 1 -- um unico
    `vmin` funcionava e os vizinhos nao. Isso nao e margem, e sorte: a barra e
    semitransparente e naquele instante o fundo era grama clara. A BANDA UTIL
    MUDA COM O CENARIO.

    E O CASO CANONICO DELE MORREU, e isso fica escrito porque e um resultado: a
    banda de largura 1 era da adena NO CAMINHO DE OCR, e a adena saiu daquele
    caminho (LEIT-09). Medido depois (M-J), a segmentacao por glifo do mesmo
    campo e estavel de 180 a 190 nas duas instancias. O aviso fica inteiro
    porque ele agora guarda o EXP e o nivel.
    """

    def test_UMA_BANDA_DE_LARGURA_1_SAI_MARCADA_COMO_FRAGIL(self):
        banda = cr.resumir_a_banda_util(_varrer({100: ("66", "66"), 105: ("", "")}))
        assert banda.largura == 1
        assert banda.fragil

    def test_UMA_BANDA_DE_LARGURA_2_TAMBEM_E_FRAGIL(self):
        banda = cr.resumir_a_banda_util(
            _varrer({100: ("66", "66"), 105: ("66", "66"), 110: ("", "")})
        )
        assert banda.largura == 2
        assert banda.fragil

    def test_CONTROLE_UMA_BANDA_DE_LARGURA_5_NAO_E_MARCADA(self):
        """Sem este controle, uma implementacao que marcasse TUDO como fragil

        passaria nos dois casos acima -- e o aviso viraria ruido que o usuario
        aprende a ignorar.
        """
        banda = cr.resumir_a_banda_util(
            _varrer({piso: ("66", "66") for piso in (100, 105, 110, 115, 120)})
        )
        assert banda.largura == 5
        assert not banda.fragil

    def test_O_AVISO_DE_BANDA_FRAGIL_APARECE_NO_TEXTO_PARA_O_USUARIO(self):
        banda = cr.resumir_a_banda_util(_varrer({100: ("66", "66"), 105: ("", "")}))
        # Uma linha so, com o espaco em branco colapsado: a mensagem e
        # quebrada em varias linhas para caber no terminal do usuario, e uma
        # afirmacao sobre a frase inteira nao pode depender de ONDE ela quebra.
        texto = " ".join(" ".join(cr.descrever_a_banda("nivel", banda)).split())
        assert "AVISO" in texto
        assert "largura 1" in texto
        assert "lugar de farm" in texto, (
            "o aviso nao diz O QUE VAI ACONTECER; um aviso sem consequencia "
            "escrita e um aviso que o usuario ignora"
        )

    def test_A_LARGURA_VAI_GRAVADA_JUNTO_DO_PISO(self):
        """A gravacao e `(piso, largura)` -- e o esquema ja tem a sub-chave."""
        banda = cr.resumir_a_banda_util(
            _varrer({piso: ("66", "66") for piso in (100, 105, 110)})
        )
        cal = Calibracao.carregar(
            RAIZ / "tests" / "fixtures" / "renda" / "calibracao_de_fixture.json"
        )
        cr._mutar_a_entrada_do_personagem(
            cal,
            "Faerlina",
            retangulos={},
            pisos={"nivel": (cr.escolher_o_piso(banda), banda.largura)},
            geometria={"largura": 1720, "altura": 1392},
        )
        bloco = cal.renda_por_personagem["Faerlina"]["nivel"]
        assert bloco["piso_de_brilho"] == 105
        assert bloco["largura_da_banda"] == 3


class TestABandaSustentadaPorUmaEscalaSo:
    """M-D: a banda INTEIRA de um campo pode ser assim, e o usuario tem direito

    de saber disso antes de gravar. E uma calibracao com uma guarda a menos:
    com uma escala so, o cruzamento deixa de pegar substituicao de digito.
    """

    def test_QUATRO_PISOS_SEGUIDOS_COM_A_2x_ABSTENDO_DAO_BANDA_DE_QUATRO(self):
        banda = cr.resumir_a_banda_util(
            _varrer({piso: ("", "67") for piso in (170, 175, 180, 185)})
        )
        assert banda.largura == 4, (
            "a banda saiu vazia: alguem voltou a exigir CONCORDANCIA entre as "
            "escalas. Com essa regra o nivel da Faerlina seria recusado para "
            "sempre (M-D)."
        )
        assert banda.de_uma_escala_so
        assert set(banda.sustentada_por) == {CONFERENCIA}

    def test_O_NOME_DA_ESCALA_QUE_SUSTENTOU_APARECE_PARA_O_USUARIO(self):
        banda = cr.resumir_a_banda_util(
            _varrer({piso: ("", "67") for piso in (170, 175, 180, 185)})
        )
        texto = "\n".join(cr.descrever_a_banda("nivel", banda))
        assert CONFERENCIA in texto
        assert "AVISO" in texto

    def test_CONTROLE_UMA_BANDA_COM_AS_DUAS_ESCALAS_NAO_E_MARCADA_ASSIM(self):
        banda = cr.resumir_a_banda_util(
            _varrer({piso: ("67", "67") for piso in (170, 175, 180, 185)})
        )
        assert not banda.de_uma_escala_so


class TestAGradeAndaDeCincoEmCinco:
    def test_O_PASSO_DA_GRADE_E_5_E_NUNCA_10(self):
        """MEDIDO: o passo de 10 do M-E PULOU O 155 e concluiu que a Yazalaque

        nao lia a adena -- quando ela lia. A leitura que passou por certa era
        `106.020` contra a verdade `1.696.020`, errada por seis ordens de
        grandeza. Um passo grosso NAO ERRA PARA O LADO SEGURO: ele produz uma
        conclusao errada com a aparencia de uma medicao, e aquela conclusao
        entrou num documento e do documento entrou num plano.
        """
        assert cr.PASSO_DA_GRADE_DE_PISOS == 5, (
            "o passo da grade mudou. Com passo 10 o 155 e pulado, e foi assim "
            "que o M-E concluiu que a Yazalaque nao lia a adena quando ela lia "
            "(M-G)."
        )

    def test_A_GRADE_INCLUI_O_155_QUE_O_PASSO_DE_DEZ_PULAVA(self):
        assert 155 in cr.grade_de_pisos(100, 200)

    def test_A_GRADE_E_FECHADA_DOS_DOIS_LADOS(self):
        grade = cr.grade_de_pisos(100, 200)
        assert grade[0] == 100
        assert grade[-1] == 200

    def test_A_GRADE_ANDA_DE_CINCO_ENTRE_VIZINHOS(self):
        grade = cr.grade_de_pisos(100, 200)
        assert {b - a for a, b in zip(grade, grade[1:])} == {5}


class TestUmPisoPorRegiaoENuncaUmSo:
    """O ramo `intersecao_das_bandas` SAIU, e a refutacao fica escrita.

    Ele era o ramo que o item M9 obrigava: as duas metades da barra dividiam UM
    campo de calibracao, e o M9 mostrava uma metade lendo num piso em que a
    outra nao lia. O achado M-E transformou a hipotese em fato e a mudanca de
    codigo foi feita: a banda do nivel (190-220) e a da adena (150) NAO TEM
    INTERSECAO NENHUMA. O esquema carrega um piso por regiao, e a situacao que
    aquele ramo detectava deixou de ser possivel.
    """

    def test_NAO_EXISTE_intersecao_das_bandas_COMO_CODIGO(self):
        """Como CODIGO, e nao como texto -- e a distincao e o ponto do caso.

        Uma busca crua acharia o nome dentro da propria docstring que explica
        por que a funcao nao existe, e o portao nasceria vermelho pedindo que
        alguem apagasse a refutacao para satisfaze-lo. O que se proibe e o
        IDENTIFICADOR na arvore de sintaxe; o que se EXIGE e a prosa.
        """
        assert "intersecao_das_bandas" not in _identificadores_do_calibrador(), (
            "a funcao voltou a existir como codigo. O ramo que ela guardava "
            "deixou de ser possivel quando o esquema passou a ter um piso por "
            "regiao (M-E)."
        )

    def test_A_REFUTACAO_DO_RAMO_ESTA_ESCRITA_CITANDO_M9_E_M_E(self):
        """Uma funcao que some sem explicacao volta em seis meses."""
        fonte = FONTE_DO_CALIBRADOR.read_text(encoding="utf-8")
        assert "intersecao_das_bandas" in fonte, (
            "a refutacao do ramo sumiu do fonte junto com a funcao"
        )
        assert "M9" in fonte and "M-E" in fonte

    def test_NENHUMA_FUNCAO_COMBINA_BANDAS_DE_REGIOES_DIFERENTES(self):
        """A varredura roda UMA VEZ POR REGIAO e cada regiao grava o seu piso.

        `resumir_a_banda_util` recebe as linhas de UMA varredura. Uma funcao
        que recebesse duas bandas seria o retrocesso que este caso guarda.
        """
        arvore = ast.parse(FONTE_DO_CALIBRADOR.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if not isinstance(no, ast.FunctionDef):
                continue
            nomes = [arg.arg for arg in no.args.args]
            bandas = [nome for nome in nomes if "banda" in nome]
            assert len(bandas) <= 1, (
                f"`{no.name}` recebe {bandas}: uma funcao que combina bandas de "
                f"regioes diferentes e um retrocesso -- cada regiao tem o SEU "
                f"piso, medido (M-E)."
            )

    def test_AS_TRES_REGIOES_ESTAO_COBERTAS_E_CADA_UMA_TEM_O_SEU_CAMINHO(self):
        from l2scanner.calibracao import REGIOES_DA_RENDA

        cobertas = set(cr.REGIOES_VARRIDAS_POR_OCR) | {cr.REGIAO_VARRIDA_POR_GLIFO}
        assert cobertas == set(REGIOES_DA_RENDA)
        assert cr.REGIAO_VARRIDA_POR_GLIFO not in cr.REGIOES_VARRIDAS_POR_OCR, (
            "a adena entrou na varredura de OCR: aquele campo trocou de leitor "
            "(LEIT-09) e os dois pisos nem se tocam -- 150 no OCR contra "
            "180-190 no glifo"
        )


class TestAVarreduraUsaADecisaoDeProducao:
    def test_O_FONTE_CHAMA_cruzar_as_escalas_COMO_CODIGO(self):
        assert "_cruzar_as_escalas" in _identificadores_do_calibrador(), (
            "a varredura parou de usar a decisao de PRODUCAO. Uma segunda "
            "particao de desfechos aqui mediria a ferramenta e nao o produto: "
            "o piso calibrado descreveria uma regra que o leitor nao aplica."
        )

    def test_NAO_EXISTE_UMA_SEGUNDA_EXPRESSAO_REGULAR_DE_NUMERO(self):
        """Uma segunda gramatica aqui mediria a ferramenta e nao o produto: o

        piso calibrado descreveria uma regra que o leitor nao aplica.
        """
        arvore = ast.parse(FONTE_DO_CALIBRADOR.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                assert all(alias.name != "re" for alias in no.names), (
                    "o calibrador importou `re`: a gramatica de numero e "
                    "importada do modulo puro, nunca reescrita aqui"
                )
            if isinstance(no, ast.ImportFrom):
                assert no.module != "re"

    def test_NAO_EXISTE_UMA_SEGUNDA_PARTICAO_DE_DESFECHOS(self):
        """Os desfechos sao um MAPA sobre as constantes do modulo puro.

        Um desfecho novo la aparece aqui como KeyError alto, e nao como linha
        silenciosamente rotulada errado.
        """
        from l2scanner import renda_leitura

        assert set(cr._DESFECHO_DA_RECUSA) == {
            renda_leitura.MOTIVO_DO_CAMPO_VAZIO,
            renda_leitura.MOTIVO_DA_GRAMATICA,
            renda_leitura.MOTIVO_DA_DISCORDANCIA,
        }


class TestAOrdemDeOperacaoApareceParaOUsuario:
    """Ninguem tem como adivinhar essa ordem, e ela precisa sair no terminal."""

    def test_OS_TRES_PASSOS_ESTAO_NA_SAIDA_E_NA_ORDEM(self):
        texto = "\n".join(cr.ordem_de_operacao())
        pos_calibrar = texto.find("calibrar-renda.bat")
        pos_moldes = texto.find("calibrar-renda-moldes.bat")
        pos_medir = texto.find("--so-medir")
        assert -1 not in (pos_calibrar, pos_moldes, pos_medir)
        assert pos_calibrar < pos_moldes < pos_medir

    def test_ELA_DIZ_QUE_A_ADENA_NAO_E_LIDA_POR_OCR(self):
        texto = "\n".join(cr.ordem_de_operacao())
        assert "GLIFO" in texto
        assert "150" in texto and "180-190" in texto, (
            "os dois pisos que nem se tocam precisam aparecer com numero: e a "
            "evidencia de que varrer OCR aqui calibraria um piso que a "
            "producao nao usa"
        )


class TestASugestaoVemDoDiscoENuncaDeUmLiteral:
    """E a sugestao do VIZINHO e sempre anunciada como tal.

    Sugerir e confirmado por um humano; CAIR e silencioso. As duas parecem a
    mesma coisa e nao sao, e a proxima pessoa a ler os dois caminhos vai achar
    que sao -- por isso o caso existe e por isso ele afirma o TEXTO tambem, e
    nao so a sugestao.
    """

    def _cal_com_um_personagem_so(self):
        return Calibracao.carregar(
            RAIZ / "tests" / "fixtures" / "renda" / "calibracao_de_fixture.json"
        )

    def test_A_SUGESTAO_DE_UM_PERSONAGEM_JA_CALIBRADO_E_A_DELE_MESMO(self):
        cal = self._cal_com_um_personagem_so()
        sugestao, vizinho = cr._sugestao_de_retangulo(cal, "Faerlina", "nivel")
        assert vizinho is None
        assert sugestao == (246, 736, 30, 20)

    def test_SEM_ENTRADA_PROPRIA_A_SUGESTAO_VEM_DO_VIZINHO_E_DIZ_DE_QUEM(self):
        cal = self._cal_com_um_personagem_so()
        cal.renda_por_personagem = {
            "Yazalaque": cal.renda_por_personagem["Yazalaque"]
        }
        sugestao, vizinho = cr._sugestao_de_retangulo(cal, "Faerlina", "nivel")
        assert vizinho == "Yazalaque"
        assert sugestao == (236, 750, 30, 20), (
            "a sugestao nao e a do vizinho: sem entrada propria e sem vizinho "
            "o usuario arrastaria do zero, o que e pior mas nao errado -- "
            "errado seria a LEITURA cair no vizinho"
        )

    def test_SEM_NINGUEM_CALIBRADO_NAO_HA_SUGESTAO_NENHUMA(self):
        cal = self._cal_com_um_personagem_so()
        cal.renda_por_personagem = None
        sugestao, vizinho = cr._sugestao_de_retangulo(cal, "Faerlina", "nivel")
        assert sugestao is None and vizinho is None

    def test_A_RODADA_DIZ_EM_TEXTO_QUE_A_SUGESTAO_VEIO_DE_OUTRO_PERSONAGEM(
        self, monkeypatch, tmp_path, capsys
    ):
        """A rodada inteira, com a selecao dublada, para um personagem AUSENTE.

        O que se afirma aqui sao duas coisas juntas: que a sugestao OFERECIDA
        foi a do vizinho, e que a saida DISSE isso em texto. Sem a segunda
        metade, o usuario apertaria ENTER num retangulo de outra instancia
        achando que era o dele.
        """
        alvo = tmp_path / "calibration.json"
        origem = RAIZ / "tests" / "fixtures" / "renda" / "calibracao_de_fixture.json"
        dados = json.loads(origem.read_text(encoding="utf-8"))
        dados["renda_por_personagem"] = {
            "Yazalaque": dados["renda_por_personagem"]["Yazalaque"]
        }
        alvo.write_text(json.dumps(dados), encoding="utf-8")
        # DISCIPLINA INEGOCIAVEL: o `calibration.json` da maquina do usuario
        # fica fora do alcance da suite. Quem remover esta linha achando que e
        # ruido reproduz o incidente de 2026-08-30 dentro do CI.
        monkeypatch.setattr(cr, "ARQUIVO_CALIBRACAO", alvo)

        sugestoes = {}

        def _selecao_falsa(_pixels, titulo, _instrucao, sugestao=None):
            sugestoes[titulo] = sugestao
            return sugestao

        monkeypatch.setattr(cr, "_selecionar_regiao", _selecao_falsa)
        monkeypatch.setattr(cr, "_gravar_conferencia", lambda _tela: None)
        # A varredura de OCR e dublada para fora: este caso mede a SUGESTAO e o
        # texto que a acompanha, e rodar 51 pisos x 2 escalas x 2 regioes de
        # OCR aqui mediria o motor de OCR junto -- e faria o caso pular quando
        # ele nao estivesse disponivel.
        monkeypatch.setattr(cr, "_varrer_as_regioes_de_ocr", lambda *a, **k: {})

        frame = np.zeros((1392, 1720, 3), dtype=np.uint8)
        monkeypatch.setattr(
            cr, "_resolver_a_fonte", lambda _args, _cal: (frame, "Faerlina", None, None)
        )

        cr.main(["--imagem", "qualquer.png", "--personagem", "Faerlina"])
        saida = capsys.readouterr().out

        assert sugestoes[cr.ROTULO_DA_REGIAO["nivel"]] == (236, 750, 30, 20)
        assert "OUTRO PERSONAGEM" in saida
        assert "Yazalaque" in saida


class TestAMedicaoDaFormaDaAdenaMedeENaoClassifica:
    """A altura de faixa e as larguras do recorte escolhido, para o OLHO.

    ELA NAO E A PENEIRA, e a diferenca e o que a mantem deste lado da fronteira
    do `01-05`: ela nao devolve veredicto nenhum, nao decide dentro/fora de
    banda e nao grava piso. Ela imprime numeros crus.

    POR QUE ELA EXISTE ASSIM MESMO (T-01-61): quem escolhe o retangulo aqui
    escolhe a ALTURA DE FAIXA que a guarda do `01-05` vai usar. Um recorte que
    pega o icone seguinte travaria o cortador de moldes inteiro, e o conserto
    seria AQUI, no retangulo -- mas sem esta medicao na tela o usuario so
    descobriria duas ferramentas depois.

    ESTES CASOS NAO PRECISAM DE OCR: `segmentar_glifos_no_brilho` e so cv2.
    """

    CROP_DE_CAMPO = (
        RAIZ / "tests" / "fixtures" / "renda" / "campo_faerlina_f000__barra_direita.png"
    )

    # MEDIDO nesta arvore, na convencao EXCLUSIVA (`fim - inicio`), com piso
    # 185. Bate caractere por caractere com a verdade de campo `13.160.684`:
    # dez caracteres no meio, entre os dois icones de moeda.
    LARGURAS_DE_CAMPO = [14, 4, 4, 1, 4, 4, 4, 1, 4, 4, 6, 15]
    ALTURA_DE_FAIXA_DE_CAMPO = 16

    def _crop(self):
        import cv2

        imagem = cv2.imread(str(self.CROP_DE_CAMPO))
        assert imagem is not None, f"a fixtura {self.CROP_DE_CAMPO} nao abriu"
        return imagem

    def _bloco(self, imagem, piso=185):
        return {
            "regiao": {
                "esquerda": 0,
                "topo": 0,
                "largura": int(imagem.shape[1]),
                "altura": int(imagem.shape[0]),
            },
            "piso_de_brilho": piso,
        }

    def test_O_RECORTE_DE_CAMPO_DA_A_ALTURA_E_AS_LARGURAS_MEDIDAS(self):
        imagem = self._crop()
        texto = "\n".join(cr.medir_a_forma_da_adena(imagem, self._bloco(imagem)))
        assert f"altura de faixa {self.ALTURA_DE_FAIXA_DE_CAMPO}" in texto, texto
        assert str(self.LARGURAS_DE_CAMPO) in texto, texto

    def test_A_CONVENCAO_DE_LARGURA_VAI_DECLARADA_NA_SAIDA(self):
        """O "17" do M-I e o "5" do M-O ja custaram duas refutacoes a esta fase,

        e as duas foram numero sem convencao declarada. A saida diz qual e.
        """
        imagem = self._crop()
        texto = "\n".join(cr.medir_a_forma_da_adena(imagem, self._bloco(imagem)))
        assert "EXCLUSIVA" in texto
        assert "fim - inicio" in texto

    def test_O_RECORTE_DE_CAMPO_NAO_DISPARA_O_AVISO_DE_RUN_LARGO_NO_MEIO(self):
        """O CONTROLE NEGATIVO. Sem ele, um aviso que disparasse sempre passaria

        no caso positivo abaixo e o usuario aprenderia a ignora-lo.
        """
        imagem = self._crop()
        texto = "\n".join(cr.medir_a_forma_da_adena(imagem, self._bloco(imagem)))
        assert "AVISO" not in texto, texto

    def test_UM_RUN_LARGO_NO_MEIO_DISPARA_O_AVISO_CITANDO_A_REFUTACAO(self):
        """O caso positivo, montado a mao.

        A montagem sintetica e necessaria porque `montagem_da_janela.png` e um
        COMPOSTO: o recorte da adena foi colado na posicao do retangulo certo,
        entao o retangulo refutado (`1500,1360 200x32`) sobre ela devolve os
        MESMOS runs -- conferido. A refutacao do M-N e do M-Q foi medida nos
        frames de campo INTEIROS, que nao vem de clone limpo. Reproduzir a forma
        e o que se pode fazer a partir do clone.
        """
        largura_do_icone = 15
        # icone | digito | ICONE NO MEIO | digito | icone
        blocos = [largura_do_icone, 4, 18, 4, largura_do_icone]
        colunas = sum(blocos) + len(blocos)
        imagem = np.zeros((20, colunas, 3), dtype=np.uint8)
        x = 0
        for bloco in blocos:
            imagem[5:15, x : x + bloco] = 255
            x += bloco + 1

        texto = "\n".join(cr.medir_a_forma_da_adena(imagem, self._bloco(imagem)))
        assert "AVISO" in texto, texto
        assert "run LARGO NO MEIO" in texto
        assert "1500,1360 200x32" in texto, (
            "o aviso nao cita o retangulo refutado; sem o endereco o usuario "
            "nao liga o sintoma a causa"
        )

    def test_UM_RECORTE_SEM_TINTA_NO_PISO_DIZ_ISSO_EM_VEZ_DE_CALAR(self):
        imagem = np.zeros((20, 100, 3), dtype=np.uint8)
        texto = "\n".join(cr.medir_a_forma_da_adena(imagem, self._bloco(imagem)))
        assert "nao tem tinta nenhuma" in texto

    def test_SEM_BLOCO_EM_DISCO_A_MEDICAO_NAO_INVENTA_NADA(self):
        imagem = self._crop()
        assert cr.medir_a_forma_da_adena(imagem, None) == []
        assert cr.medir_a_forma_da_adena(imagem, {"regiao": {}}) == []

    def test_ELA_NAO_DEVOLVE_VEREDICTO_NENHUM(self):
        """A fronteira, afirmada: esta funcao MEDE. Quem classifica e a peneira

        do `01-05`, e uma segunda forma aqui faria os moldes serem cortados de
        um conjunto de corridas e lidos de outro.
        """
        imagem = self._crop()
        texto = "\n".join(cr.medir_a_forma_da_adena(imagem, self._bloco(imagem)))
        for veredicto in cr.VEREDICTOS:
            assert veredicto not in texto, veredicto


class TestOFonteNaoCarregaNumeroDeGEOMETRIA:
    """A sugestao vem do disco, e isso e afirmado por CODIGO e nao por leitura."""

    def test_NENHUM_Regiao_COM_QUATRO_INTEIROS_LITERAIS(self):
        arvore = ast.parse(FONTE_DO_CALIBRADOR.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Call):
                continue
            nome = getattr(no.func, "id", None) or getattr(no.func, "attr", None)
            if nome != "Regiao":
                continue
            literais = [
                arg
                for arg in no.args
                if isinstance(arg, ast.Constant) and isinstance(arg.value, int)
            ]
            assert len(literais) < 4, (
                f"linha {no.lineno}: `Regiao(...)` com quatro inteiros "
                f"literais. O retangulo tem de vir do disco -- um literal aqui "
                f"e o comeco do caminho que o criterio 4 do roadmap existe "
                f"para fechar."
            )

    def test_NENHUM_PISO_DE_BRILHO_ATRIBUIDO_A_PARTIR_DE_UM_LITERAL(self):
        arvore = ast.parse(FONTE_DO_CALIBRADOR.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Assign):
                continue
            if not (
                isinstance(no.value, ast.Constant) and isinstance(no.value.value, int)
            ):
                continue
            for alvo in no.targets:
                rotulo = ""
                if isinstance(alvo, ast.Subscript) and isinstance(
                    alvo.slice, ast.Constant
                ):
                    rotulo = str(alvo.slice.value)
                elif isinstance(alvo, ast.Attribute):
                    rotulo = alvo.attr
                elif isinstance(alvo, ast.Name):
                    rotulo = alvo.id
                assert "piso_de_brilho" not in rotulo, (
                    f"linha {no.lineno}: piso de brilho atribuido a partir de "
                    f"um literal. Ele e MEDIDO pela varredura, e escrever o "
                    f"numero no fonte transformaria uma medicao numa constante."
                )


class TestOModuloCarregaAntesDeMutar:
    """Toda a nao-destruicao desta fase pende desta ordem, e ela e verificavel.

    A ordem e afirmada por ARVORE DE SINTAXE e nao por leitura: um refator que
    movesse o `carregar` para depois da mutacao passaria em todos os testes de
    comportamento deste repositorio e reproduziria o incidente de 2026-08-30.
    """

    def _funcao_principal(self):
        arvore = ast.parse(FONTE_DO_CALIBRADOR.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.FunctionDef) and no.name == "calibrar_renda":
                return no
        pytest.fail("a funcao principal `calibrar_renda` sumiu do modulo")

    def _linhas_de(self, funcao, predicado) -> list[int]:
        return [
            no.lineno
            for no in ast.walk(funcao)
            if isinstance(no, ast.Call) and predicado(no)
        ]

    def test_O_CARREGAR_ACONTECE_ANTES_DA_MUTACAO_E_DA_GRAVACAO(self):
        funcao = self._funcao_principal()
        carregar = self._linhas_de(
            funcao, lambda no: getattr(no.func, "attr", None) == "carregar"
        )
        mutar = self._linhas_de(
            funcao,
            lambda no: getattr(no.func, "id", None)
            == "_mutar_a_entrada_do_personagem",
        )
        salvar = self._linhas_de(
            funcao, lambda no: getattr(no.func, "attr", None) == "salvar"
        )
        assert carregar, "o calibrador nao chama `Calibracao.carregar`"
        assert mutar and salvar
        assert min(carregar) < min(mutar), (
            "a mutacao vem ANTES do carregar: e exatamente a forma do incidente "
            "de 2026-08-30, um escritor montando do zero o que devia ter "
            "carregado"
        )
        assert min(carregar) < min(salvar)

    def test_A_MUTACAO_MORA_NUMA_FUNCAO_SO(self):
        """Um segundo ponto de mutacao seria um segundo lugar para esquecer o

        `dict(...)` que preserva a sub-chave desconhecida e o vizinho.
        """
        fonte = FONTE_DO_CALIBRADOR.read_text(encoding="utf-8")
        codigo = "\n".join(
            linha for linha in fonte.splitlines() if not linha.strip().startswith("#")
        )
        assert codigo.count("cal.renda_por_personagem =") == 1


# ===========================================================================
# A VARREDURA DA `barra_direita`: FORMA DE GLIFO, E NAO CRUZAMENTO DE OCR
# ===========================================================================
#
# AS LARGURAS DAQUI ESTAO NA CONVENCAO EXCLUSIVA (`fim - inicio`), que e a do
# codigo. A verdade de campo da Faerlina de 00h45 (`13.160.684`, dez
# caracteres) mede, nesta convencao, `[14, 4, 4, 1, 4, 4, 4, 1, 4, 4, 6, 15]`:
# icone, dez caracteres no meio, icone. Na convencao INCLUSIVA do
# `01-MEDICOES-DE-CAMPO.md` cada numero desses vale um a mais.

#: A forma canonica de um numero desta barra, medida em campo e traduzida.
FORMA_DE_UM_NUMERO = (14, 4, 1, 4, 4, 4, 1, 4, 4, 4, 15)

#: A altura da FONTE da barra, na convencao exclusiva (M-K reconferido pelo
#: `01-05`: 9 exclusiva, 10 inclusiva). Ela e o que a faixa PENEIRADA devolve.
ALTURA_DA_FONTE = 9

#: A altura do ICONE de moeda. Ela e maior que a da fonte, e e por isso que a
#: faixa BRUTA vale 16 e a peneirada vale 9 sobre os mesmos pixels.
ALTURA_DO_ICONE = 16


def _forma(larguras, *, altura_do_glifo: int = ALTURA_DA_FONTE):
    """`(mascara, faixa bruta, corridas)` para uma sequencia de larguras.

    Os icones das PONTAS sao desenhados mais ALTOS que os glifos do meio, de
    proposito: e essa diferenca que faz a faixa bruta valer `ALTURA_DO_ICONE` e
    a peneirada valer `altura_do_glifo`, que e o achado M-K inteiro. Uma
    mascara com tudo da mesma altura passaria nos casos de forma e nao provaria
    nada sobre a altura.

    Uma coluna vazia separa cada corrida da seguinte, que e exatamente a regra
    de `segmentar_glifos_no_brilho`: qualquer coluna vazia separa, sem
    tolerancia de lacuna.
    """
    corridas = []
    coluna = 1
    for largura in larguras:
        corridas.append((coluna, coluna + int(largura)))
        coluna += int(largura) + 1
    mascara = np.zeros((ALTURA_DO_ICONE + 4, coluna + 1), dtype=np.uint8)
    ultimo = len(corridas) - 1
    topo_do_glifo = (ALTURA_DO_ICONE - int(altura_do_glifo)) // 2
    for indice, (inicio, fim) in enumerate(corridas):
        if indice in (0, ultimo):
            mascara[0:ALTURA_DO_ICONE, inicio:fim] = 1
        else:
            mascara[topo_do_glifo : topo_do_glifo + int(altura_do_glifo), inicio:fim] = 1
    return mascara, (0, ALTURA_DO_ICONE), corridas


def _varrer_forma(curva, *, moldes_da_barra=None, ler_valor=None):
    """`{piso: larguras exclusivas}` -> as linhas da varredura de forma.

    O recorte vai `None` de proposito, pelo mesmo motivo de `_varrer`: se algum
    caminho desta varredura passasse a olhar pixel por fora do `medir`
    injetado, ele estouraria aqui em vez de passar medindo outra coisa.
    """
    formas = {piso: _forma(larguras) for piso, larguras in curva.items()}
    return cr.varrer_a_forma(
        None,
        sorted(curva),
        moldes_da_barra=moldes_da_barra,
        medir=lambda _recorte, piso: formas[piso],
        ler_valor=ler_valor,
    )


def _conjunto_de_moldes(larguras, *, altura: int = ALTURA_DA_FONTE) -> dict:
    """Um `renda_moldes_da_barra` de verdade, pela ida e volta de producao.

    Os moldes passam por `glifos_para_calibracao` e voltam por
    `glifos_de_calibracao` -- os mesmos dois lados que o cortador usa. Um dict
    falso aqui mediria o teste e nao o produto, e o limite derivado deles e
    justamente o numero que o achado M-U poe em duvida.
    """
    from l2scanner.mercado_visao import glifos_para_calibracao

    moldes = {
        str(rotulo): np.ones((int(altura), int(largura)), dtype=np.uint8)
        for rotulo, largura in larguras.items()
    }
    return {
        "moldes": glifos_para_calibracao(moldes),
        "piso_de_leitura": 0.8,
        "margem_de_leitura": 0.1,
        "folga_de_cola": None,
    }


class TestAAdenaEClassificadaPelaFORMAEnaoPeloValor:
    """A forma e a primeira peneira, e neste calibrador ela e a UNICA.

    Um piso em que a segmentacao devolve uma contagem de corridas diferente da
    esperada fica FORA da banda mesmo que a leitura devolva uma string -- sem
    esse controle, uma varredura que so olhasse o texto aceitaria de bom grado
    uma segmentacao quebrada, e o piso gravado descreveria outra coisa.
    """

    def test_A_FORMA_MEDIDA_EM_CAMPO_FICA_DENTRO_DA_BANDA(self):
        linhas = _varrer_forma({185: FORMA_DE_UM_NUMERO})
        assert linhas[0].aceito, linhas[0].desfecho
        assert cr.resumir_a_banda_util(linhas).pisos == (185,)

    def test_O_MIOLO_ACEITO_TEM_OS_CARACTERES_E_NAO_OS_ICONES(self):
        """Nove caracteres no meio de onze corridas: os dois icones sairam."""
        linha = _varrer_forma({185: FORMA_DE_UM_NUMERO})[0]
        assert linha.corridas_do_numero == len(FORMA_DE_UM_NUMERO) - 2

    def test_CONTROLE_UMA_CONTAGEM_DIFERENTE_FICA_FORA_MESMO_COM_TEXTO_LIDO(
        self,
    ):
        """O CONTROLE que a acceptance exige: valor lido NAO salva a forma.

        Um icone no MEIO (largura de icone entre os digitos) e a forma medida
        do retangulo refutado pelo M-N. A leitura injetada devolve uma string
        perfeitamente plausivel, e mesmo assim o piso fica FORA: quem decide e
        a forma.
        """
        quebrada = (14, 4, 1, 4, 14, 4, 1, 4, 4, 4, 15)
        linhas = _varrer_forma(
            {185: quebrada},
            moldes_da_barra=_conjunto_de_moldes({"4": 6, "1": 1}),
            ler_valor=lambda *_a, **_k: "13,160,684",
        )
        assert not linhas[0].aceito
        assert cr.resumir_a_banda_util(linhas).vazia
        assert linhas[0].valor is None, (
            "a leitura foi feita sobre um recorte que a forma RECUSOU: a ordem "
            "e o contrato, e o valor so existe depois do veredicto"
        )

    def test_A_SAIDA_NOMEIA_O_METODO_COMO_GLIFO_E_NAO_COMO_OCR(self):
        linhas = _varrer_forma({185: FORMA_DE_UM_NUMERO})
        texto = "\n".join(cr.descrever_a_forma("ADENA", linhas))
        assert cr.METODO_POR_GLIFO in texto
        assert cr.METODO_POR_OCR in texto, (
            "o metodo do OUTRO caminho tem de aparecer NEGADO: sem isso o "
            "usuario compara o piso de glifo com o de OCR, e medido (M-E) as "
            "duas bandas nem se tocam"
        )

    def test_A_ADENA_NAO_ESTA_NA_VARREDURA_DE_OCR(self):
        assert cr.REGIAO_VARRIDA_POR_GLIFO not in cr.REGIOES_VARRIDAS_POR_OCR

    def test_A_VARREDURA_DE_FORMA_NAO_CHAMA_O_CRUZAMENTO_DE_ESCALAS(self):
        """Nenhum caminho varre a `barra_direita` pelos quatro desfechos.

        Verificado na ARVORE DE SINTAXE das funcoes de forma, e nao por leitura:
        `_cruzar_as_escalas` continua sendo chamada neste arquivo -- pelas OUTRAS
        duas regioes --, entao uma busca crua nao discriminaria nada.
        """
        arvore = ast.parse(FONTE_DO_CALIBRADOR.read_text(encoding="utf-8"))
        de_forma = {"varrer_a_forma", "descrever_a_forma", "_medir_as_corridas"}
        for no in ast.walk(arvore):
            if not isinstance(no, ast.FunctionDef) or no.name not in de_forma:
                continue
            chamados = {
                filho.attr if isinstance(filho, ast.Attribute) else filho.id
                for filho in ast.walk(no)
                if isinstance(filho, (ast.Name, ast.Attribute))
            }
            assert "_cruzar_as_escalas" not in chamados, (
                f"`{no.name}` cruza escalas de OCR num campo lido por GLIFO: o "
                f"piso calibrado assim nao e o que a producao usa"
            )


class TestAAlturaDeFaixaSaiComACONVENCAODeclarada:
    """Dois numeros, duas convencoes, e a fase ja pagou por confundi-las.

    A faixa BRUTA carrega os icones e vale 16 exclusiva (17 inclusiva) -- e o
    `17` do M-I. A faixa PENEIRADA, depois de os icones sairem, vale 9 exclusiva
    (10 inclusiva) -- e o `10` do M-K. Uma guarda calibrada contra 10 rodando na
    convencao do codigo recusaria TODO molde legitimo desta barra, e o modo de
    falha seria um cortador que roda, sai com codigo 0 e nunca corta nada.
    """

    def test_A_ALTURA_DEVOLVIDA_E_A_PENEIRADA_E_VALE_9_NA_CONVENCAO_DO_CODIGO(
        self,
    ):
        linha = _varrer_forma({185: FORMA_DE_UM_NUMERO})[0]
        assert linha.altura_da_faixa == ALTURA_DA_FONTE, (
            "a altura devolvida e a BRUTA e nao a peneirada: medir antes do "
            "descarte dos icones e reproduzir o M-I por dentro da ferramenta "
            "que existe para nao repeti-lo"
        )

    def test_A_FAIXA_BRUTA_DA_MESMA_MASCARA_E_MAIOR_QUE_A_PENEIRADA(self):
        """O controle que prova que os dois numeros sao dos MESMOS pixels."""
        _mascara, bruta, _corridas = _forma(FORMA_DE_UM_NUMERO)
        assert bruta[1] - bruta[0] == ALTURA_DO_ICONE > ALTURA_DA_FONTE

    def test_A_CONVENCAO_VAI_DECLARADA_NA_SAIDA_COM_OS_DOIS_NUMEROS(self):
        linhas = _varrer_forma({185: FORMA_DE_UM_NUMERO})
        texto = "\n".join(cr.descrever_a_forma("ADENA", linhas))
        assert "EXCLUSIVA" in texto
        assert str(ALTURA_DA_FONTE) in texto
        assert str(ALTURA_DA_FONTE + 1) in texto, (
            "a saida da so um dos dois numeros: quem ler vai comparar com o "
            "documento de campo, que esta na outra convencao"
        )
        assert "M-K" in texto


class TestOCasoSemMoldesQueEAPrimeiraRodadaDeTodoUsuario:
    """O buraco de ordem que a suite sintetica nao pegaria sozinha.

    `ler_glifos` sem moldes nao le nada, e os moldes so nascem na rodada humana
    do cortador. Uma varredura acoplada ao VALOR devolveria banda vazia em todos
    os pisos na estreia -- e o usuario concluiria que a adena nao tem piso
    nenhum, enquanto os casos montados a mao continuariam verdes.
    """

    def test_SEM_MOLDES_A_BANDA_NAO_SAI_VAZIA(self):
        linhas = _varrer_forma(
            {piso: FORMA_DE_UM_NUMERO for piso in (180, 185, 190)},
            moldes_da_barra=None,
        )
        banda = cr.resumir_a_banda_util(linhas)
        assert not banda.vazia, (
            "a banda saiu vazia sem moldes: e a primeira rodada de TODO "
            "usuario, e ele concluiria que a adena nao tem piso nenhum"
        )
        assert banda.pisos == (180, 185, 190)

    def test_SEM_MOLDES_A_LEITURA_POR_GLIFO_NAO_E_CHAMADA(self, monkeypatch):
        """Espionando o `ler_glifos` DE VERDADE, e nao o injetavel.

        Com o `ler_valor` injetado o caso nao provaria nada: ele mediria o
        proprio teste. O que se afirma aqui e que o caminho de producao nao
        chega na leitura quando nao ha molde.
        """
        chamadas = []
        monkeypatch.setattr(
            cr, "ler_glifos", lambda *a, **k: chamadas.append(a) or "x"
        )
        _varrer_forma({185: FORMA_DE_UM_NUMERO}, moldes_da_barra=None)
        assert chamadas == []

    def test_SEM_MOLDES_A_SAIDA_TRAZ_A_ORDEM_DE_OPERACAO(self, capsys):
        """A informacao que o usuario NAO tem como adivinhar, no terminal dele.

        Ele ve tres retangulos, uma curva e um numero. Sem esta saida ele nao
        tem como saber que falta um passo entre esta rodada e a leitura da
        adena funcionando, e concluiria que a ferramenta esta quebrada.
        """
        cv2 = pytest.importorskip("cv2")
        caminho = (
            RAIZ
            / "tests"
            / "fixtures"
            / "renda"
            / "campo_faerlina_f000__barra_direita.png"
        )
        imagem = cv2.imread(str(caminho))
        bloco = {
            "regiao": {
                "esquerda": 0,
                "topo": 0,
                "largura": int(imagem.shape[1]),
                "altura": int(imagem.shape[0]),
            },
            "piso_de_brilho": 185,
        }
        cal = Calibracao.carregar(
            RAIZ / "tests" / "fixtures" / "renda" / "calibracao_de_fixture.json"
        )
        # O CASO E "SEM MOLDES", E ELE E CONSTRUIDO AQUI EM VEZ DE HERDADO.
        #
        # Este teste nasceu (01-03) lendo a ausencia de moldes DA FIXTURA, e a
        # fixtura os ganhou uma onda depois (01-04, que fundiu
        # `renda_moldes_da_barra` nela para virar a unica verdade versionada
        # dos moldes). O merge das duas ondas quebrou o teste, e a quebra era
        # justa: um teste sobre a PRIMEIRA RODADA de um usuario nao pode
        # depender de um arquivo compartilhado continuar vazio -- basta alguem
        # cortar um molde para ele passar a medir outra coisa em silencio.
        # Zerar a chave aqui torna a premissa explicita e local.
        cal.renda_moldes_da_barra = None
        assert cal.renda_moldes_da_barra is None
        cr._imprimir_a_varredura_da_adena(
            cal, imagem, bloco, cr.grade_de_pisos(1, 254)
        )
        saida = capsys.readouterr().out
        assert "calibrar-renda-moldes.bat" in saida
        assert "--so-medir" in saida
        assert "O VALOR NAO FOI LIDO" in saida
        assert "NENHUM gravado ainda" in saida

    def test_CONTROLE_COM_MOLDES_O_VALOR_APARECE_E_A_BANDA_NAO_MUDA(self):
        """O par que a acceptance exige: o valor entra, o dentro/fora nao muda.

        Os moldes deste caso tem a MESMA largura maxima que o arranque mediria
        no recorte, de proposito: assim a UNICA coisa que muda entre as duas
        varreduras e a coluna de valor. Se a banda mudasse aqui, o piso gravado
        passaria a depender de o conjunto de moldes estar completo ou nao -- e a
        calibracao dependeria de um artefato que ela mesma nao produz.
        """
        curva = {piso: FORMA_DE_UM_NUMERO for piso in (180, 185, 190)}
        sem = _varrer_forma(curva, moldes_da_barra=None)
        com = _varrer_forma(
            curva,
            moldes_da_barra=_conjunto_de_moldes({"4": 4, "1": 1}),
            ler_valor=lambda *_a, **_k: "13,160,684",
        )
        assert cr.resumir_a_banda_util(sem).pisos == cr.resumir_a_banda_util(com).pisos
        assert all(linha.valor is None for linha in sem)
        assert all(linha.valor == "13,160,684" for linha in com)

    def test_O_VALOR_E_INFORMATIVO_E_NAO_DECIDE_NADA(self):
        """Leitura `None` com moldes presentes NAO derruba o piso."""
        linhas = _varrer_forma(
            {185: FORMA_DE_UM_NUMERO},
            moldes_da_barra=_conjunto_de_moldes({"4": 4, "1": 1}),
            ler_valor=lambda *_a, **_k: None,
        )
        assert linhas[0].aceito
        assert linhas[0].valor is None


class TestAPeneiraEUmaSoNestaFase:
    """Duas peneiras seriam duas formas, e o desalinhamento seria calado.

    O par de portoes e o mesmo que o cortador de moldes aplica, pela mesma
    razao: os moldes seriam cortados de um conjunto de corridas e lidos de
    outro, e ninguem veria a diferenca ate a leitura de producao errar.
    """

    def test_O_CALIBRADOR_NAO_REDEFINE_A_PENEIRA(self):
        """Por ARVORE DE SINTAXE e tambem por texto cru.

        Pela arvore porque e o que de fato se proibe -- uma definicao. E por
        texto cru tambem porque o criterio de aceitacao do plano e um `grep`, e
        um `grep` nao distingue codigo de prosa: uma frase de comentario com a
        assinatura dentro faria o portao do plano nascer vermelho e alguem
        "consertaria" apagando a explicacao.
        """
        arvore = ast.parse(FONTE_DO_CALIBRADOR.read_text(encoding="utf-8"))
        definidas = {
            no.name for no in ast.walk(arvore) if isinstance(no, ast.FunctionDef)
        }
        assert "_glifos_do_numero" not in definidas
        assert FONTE_DO_CALIBRADOR.read_text(encoding="utf-8").count(
            "def _glifos_do_numero"
        ) == 0

    def test_O_CALIBRADOR_IMPORTA_E_USA_A_PENEIRA(self):
        assert "_glifos_do_numero" in _identificadores_do_calibrador()

    def test_A_PENEIRA_USADA_E_A_DO_MODULO_PURO(self):
        from l2scanner.renda_leitura import _glifos_do_numero

        assert cr._glifos_do_numero is _glifos_do_numero


class TestOLimiteHerdadoNaoPodeCulparORetanguloInocente:
    """M-U: a recusa da peneira culpa o retangulo, e o retangulo esta certo.

    Medido na rodada de moldes de 2026-09-02: cortando em ordem alfabetica, o
    primeiro recorte e `2.207.577`, so com digitos de largura 4; o limite trava
    em 4 e os tres recortes seguintes sao RECUSADOS, porque `4`, `8` e `9`
    medem 5 e 6. A mensagem dizia "o recorte pegou o campo vizinho junto" -- e o
    que estava estreito era o LIMITE HERDADO.

    Reconferido deste lado, com o limite preso em 4 sobre as CINCO fixturas de
    `barra_direita`: duas ficam com a banda inteiramente vazia, e as recusas dos
    pisos 181, 186 e 191 mandariam remarcar um retangulo correto.
    """

    def _com_limite_estreito(self):
        return _varrer_forma(
            {185: FORMA_DE_UM_NUMERO[:-2] + (6, FORMA_DE_UM_NUMERO[-1])},
            moldes_da_barra=_conjunto_de_moldes({"2": 4, "0": 4, "1": 1}),
        )

    def test_A_RECUSA_POR_LIMITE_ESTREITO_E_MARCADA_COMO_ATRIBUICAO_ERRADA(
        self,
    ):
        linhas = self._com_limite_estreito()
        assert not linhas[0].aceito
        assert linhas[0].origem_do_limite == "moldes"
        assert linhas[0].culpa_o_retangulo_sem_razao, (
            "a recusa passou sem marca: o limite veio dos moldes e o arranque "
            "medido NESTE recorte e maior que ele, o que quer dizer que falta "
            "molde e nao que o retangulo esta errado (M-U)"
        )

    def test_O_AVISO_DIZ_PARA_NAO_REMARCAR_O_RETANGULO(self):
        texto = "\n".join(cr.avisar_sobre_o_limite_herdado(self._com_limite_estreito()))
        assert "M-U" in texto
        assert "FALTA MOLDE" in texto
        assert "Nao remarque o retangulo" in texto
        assert "MAIS" in texto and "LARGO" in texto, (
            "o aviso nao diz a ordem que conserta: cortar do recorte mais "
            "largo para o mais estreito e o que fez os onze rotulos fecharem"
        )

    def test_CONTROLE_SEM_MOLDES_NAO_HA_ATRIBUICAO_ERRADA_A_DESFAZER(self):
        """O limite de ARRANQUE e medido no proprio recorte.

        Ele nao pode ser estreito demais por culpa de um conjunto incompleto,
        entao o aviso do M-U nao se aplica -- e um aviso que aparecesse aqui
        seria ruido no unico caminho que nao tem o defeito.
        """
        linhas = _varrer_forma(
            {185: (14, 4, 14, 4, 15)}, moldes_da_barra=None
        )
        assert not linhas[0].aceito
        assert linhas[0].origem_do_limite == "arranque"
        assert cr.avisar_sobre_o_limite_herdado(linhas) == []

    def test_CONTROLE_UM_CONJUNTO_LARGO_O_BASTANTE_NAO_DISPARA_O_AVISO(self):
        """Sem o controle, uma implementacao que avisasse SEMPRE passaria."""
        linhas = _varrer_forma(
            {185: (14, 4, 14, 4, 15)},
            moldes_da_barra=_conjunto_de_moldes({"4": 6, "1": 1}),
        )
        assert not linhas[0].aceito
        assert linhas[0].origem_do_limite == "moldes"
        assert cr.avisar_sobre_o_limite_herdado(linhas) == [], (
            "o aviso disparou num caso em que o arranque NAO e maior que o "
            "limite: ali a forma esta mesmo errada, e culpar os moldes mandaria "
            "o usuario para o lugar errado"
        )

    def test_O_AVISO_NAO_APARECE_QUANDO_NAO_HA_RECUSA_NENHUMA(self):
        linhas = _varrer_forma(
            {185: FORMA_DE_UM_NUMERO},
            moldes_da_barra=_conjunto_de_moldes({"4": 4, "1": 1}),
        )
        assert cr.avisar_sobre_o_limite_herdado(linhas) == []


@pytest.fixture(scope="module")
def fixturas():
    """As CINCO fixturas versionadas da `barra_direita`, abertas uma vez so.

    Elas sao o unico pixel de campo que esta suite toca, e nao precisam de OCR:
    `mascara_de_numero` e `segmentar_glifos_no_brilho` sao so cv2. A contagem
    e afirmada aqui e nao la embaixo -- uma fixtura que sumisse faria os casos
    passarem medindo menos tela.
    """
    cv2 = pytest.importorskip("cv2")
    caminhos = sorted(
        (RAIZ / "tests" / "fixtures" / "renda").glob("*__barra_direita.png")
    )
    assert len(caminhos) == 5, caminhos
    return {caminho.name: cv2.imread(str(caminho)) for caminho in caminhos}


class TestAVarreduraDeFormaContraAsFixturasDeCAMPO:
    """As cinco fixturas versionadas da barra, sem OCR e sem `recordings/`.

    Os casos acima sao montados a mao e provam a REGRA; estes provam que a
    regra descreve a tela. Sem eles, uma peneira coerente com uma barra
    imaginaria passaria em tudo.
    """

    def test_AS_CINCO_TEM_BANDA_E_O_CENTRO_CAI_NA_BANDA_DE_GLIFO_MEDIDA(
        self, fixturas
    ):
        """Medido: o piso escolhido cai em 181 ou 186 nas cinco.

        A banda de glifo medida em campo (M-J) e 180-190 nas duas instancias.
        Este caso e o que liga a regra de CENTRO ao numero de campo: as bandas
        de forma comecam antes de 180 -- em piso baixo glifos vizinhos colam e
        o arranque adota a largura do par --, e e o centro que salva a escolha.
        """
        pisos = cr.grade_de_pisos(1, 254)
        escolhidos = {}
        for nome, imagem in fixturas.items():
            banda = cr.resumir_a_banda_util(cr.varrer_a_forma(imagem, pisos))
            assert not banda.vazia, nome
            escolhidos[nome] = cr.escolher_o_piso(banda)
        assert all(181 <= piso <= 186 for piso in escolhidos.values()), escolhidos

    def test_A_FAIXA_PENEIRADA_VALE_9_NOS_PISOS_DA_BANDA_DE_CAMPO(
        self, fixturas
    ):
        """9 exclusiva, 10 inclusiva -- nas cinco fixturas e nos tres pisos.

        E o numero que a guarda de altura do cortador compara. O plano escreveu
        `10`, que e o INCLUSIVO; uma guarda escrita contra ele na convencao do
        codigo recusaria todo molde legitimo desta barra.
        """
        medidas = {}
        for nome, imagem in fixturas.items():
            linhas = cr.varrer_a_forma(imagem, (181, 186, 191))
            medidas[nome] = [linha.altura_da_faixa for linha in linhas]
        assert all(
            alturas == [ALTURA_DA_FONTE] * 3 for alturas in medidas.values()
        ), medidas

    def test_UM_LIMITE_HERDADO_ESTREITO_ESVAZIA_A_BANDA_DE_FIXTURA_CORRETA(
        self, fixturas
    ):
        """O M-U medido sobre pixel de campo, e nao sobre forma montada.

        Com o conjunto de moldes travado nas larguras estreitas -- o que a
        ordem alfabetica produz --, a fixtura da Faerlina de 09h30 fica com a
        banda INTEIRAMENTE VAZIA. O retangulo dela e o mesmo que funciona no
        caso acima.
        """
        imagem = fixturas["segundo_cenario_faerlina__barra_direita.png"]
        estreito = _conjunto_de_moldes({"2": 4, "0": 4, "7": 4, "5": 4, "1": 1})
        linhas = cr.varrer_a_forma(
            imagem, cr.grade_de_pisos(1, 254), moldes_da_barra=estreito
        )
        assert cr.resumir_a_banda_util(linhas).vazia
        assert any(linha.culpa_o_retangulo_sem_razao for linha in linhas), (
            "a banda esvaziou e NENHUMA linha ficou marcada: o usuario levaria "
            "a recusa ao pe da letra e remarcaria um retangulo correto"
        )
