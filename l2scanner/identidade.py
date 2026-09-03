"""Quem e cada membro, pela imagem do nome na tela.

O PROBLEMA QUE ISTO RESOLVE

Sem isto, os nomes vem da lista do config POR POSICAO DE LINHA. Se a ordem da
party muda — alguem sai e as linhas compactam, ou o lider reorganiza — os
alertas saem com o nome errado.

Essa e a pior categoria de falha do produto. Nao e ruido: e uma mentira
plausivel. "Korzis morreu" quando quem morreu foi o Kaus manda a party socorrer
a pessoa errada, e ninguem desconfia porque a mensagem parece perfeitamente
normal.

POR QUE COMPARACAO DE IMAGEM E NAO OCR

Os nomes sao um conjunto FECHADO e conhecido, e o cliente renderiza o texto de
forma deterministica — o mesmo nome produz os mesmos pixels toda vez. Entao nao
precisamos *ler* o nome, precisamos *reconhecer* qual dos N conhecidos esta ali.
Isso e classificacao, nao leitura, e e muito mais confiavel.

OCR seria pior em tres frentes: exige instalador de ~100 MB (contra o "clica e
roda" do projeto), um glifo lido errado inventa um membro fantasma entrando e
saindo da party, e nada disso compra precisao que ja nao tenhamos aqui.

O QUE FEZ A COMPARACAO FUNCIONAR

Medido na tela real, entre capturas separadas por 4 segundos (o cenario muda por
tras do texto, que e transparente):

    cinza bruto, recorte largo    : mesmo nome 0.751  outro 0.707  margem 0.045
    mascara de texto, largo       : mesmo nome 0.831  outro 0.793  margem 0.038
    mascara de texto, recorte justo: mesmo nome 1.000 outro 0.454  margem 0.546

Duas coisas viraram o jogo: **recortar justo** (num recorte largo o terreno
domina a correlacao) e **isolar o texto por claro-e-dessaturado** (o texto e
branco, o terreno e colorido).
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# Um pixel conta como texto se for CLARO. So isso.
#
# A versao anterior exigia tambem ser dessaturado, o que funcionava ate o
# usuario virar lider da party: o jogo pinta o nome do lider de AMARELO, com
# saturacao 118, e a regra o rejeitava. O membro simplesmente sumia do
# reconhecimento.
#
# Medido na tela real: texto branco V=206 S=5, texto amarelo do lider V=206
# S=118, terreno V=83 S=96. O brilho separa os tres com folga; a saturacao nao
# separa o amarelo do terreno. Entao o brilho e o unico criterio.
VALOR_MINIMO_DO_TEXTO = 180

# A COROA DO LIDER — resolvida pelo segundo passe, ver `_reancorar_apos_ornamento`.
#
# O jogo desenha uma coroa antes do nome do lider, o que desloca o texto. Houve
# uma tentativa de tolerar isso deslizando o casamento (`matchTemplate(...).max()`
# sobre uma regiao de busca alargada). Ela foi removida por duas razoes medidas:
#
#   1. Nao funcionava. A busca alargava para a ESQUERDA e a coroa empurra o
#      texto para a DIREITA. O alinhamento necessario estava fora do recorte.
#   2. Custava caro. Em 8 casamentos CORRETOS medidos (duas calibracoes, dois
#      conjuntos de frames) o deslize rendeu +0.000 — eles sempre vencem no
#      alinhamento calibrado. Nos casamentos ERRADOS rendeu ate +0.373,
#      levando o pior errado a 0.586 contra um limiar de 0.75.
#
# O caso que ficou sem cobertura foi o membro calibrado SEM coroa que depois
# VIRA lider — e ele aconteceu, em 2026-08-25. O usuario era lider quando
# calibrou (o lider nao aparece na propria party window, entao NENHUMA das
# assinaturas gravadas tem coroa), entrou numa party alheia as 10:03, e o membro
# que ficou na linha do lider passou DUAS HORAS como "Membro 1" — atravessando
# ate um reinicio do scanner, porque a assinatura gravada nao muda.
#
# Medido com os pixels reais da coroa: o membro casa 0.266 contra a PROPRIA
# assinatura, enquanto os outros tres da mesma party casam 0.960 / 0.957 / 0.992.
# Nao e "perto do limiar": esta a 0.484 dele.
#
# A resposta NAO e voltar ao `.max()` irrestrito — ele devolve as 24 chances
# extras de falso positivo que produziram o bug do "entra e sai". E um SEGUNDO
# PASSE que testa UM alinhamento a mais, escolhido pelo conteudo do proprio
# recorte, so nas linhas que o primeiro passe deixou sem nome.
#
# O SENTIDO INVERSO, medido em campo em 2026-08-31.
#
# O paragrafo acima descreve a coroa aparecendo NO RECORTE ao vivo. Ela quebra o
# reconhecimento tambem no sentido oposto: gravada NA ASSINATURA e sumida da
# tela — quem calibrou ENQUANTO era lider e depois deixou de ser.
#
# Party de quatro, os quatro calibrados, e mesmo assim dois viraram "Membro N".
# Os dois que falharam foram exatamente os dois cuja condicao de lideranca mudou
# entre a calibracao e o dia:
#
#     assinatura de Mostarda -> a imagem dela COM a coroa (era lider entao)
#     recorte de hoje        -> "ostarda", sem coroa (nao e mais lider)
#     assinatura de Welazkez -> sem coroa; recorte de hoje COM coroa
#
# Os outros dois, cuja lideranca nao mudou, casaram sem tropeco. O discriminador
# do defeito e a MUDANCA, e ela acontece nas duas direcoes.
#
# O desenho e o MESMO, e de proposito: um alinhamento a mais por par, lido da
# estrutura "bloco, lacuna, bloco" de um dos lados e ancorado no outro, cobrado
# com limiar e margem mais caros. Muda so de que lado a lacuna e lida:
#
#     lacuna no RECORTE     -> desloca o RECORTE   (`_pontuar_com_ornamento`)
#     lacuna na ASSINATURA  -> desloca a ASSINATURA
#                              (`_pontuar_sem_o_ornamento_da_assinatura`)
#
# Medido com os pixels reais da coroa, o recorte do ex-lider contra as quatro
# assinaturas da fixture:
#
#     primeiro passe   0.266  0.146  0.252  0.298   <- a propria em 0.266
#     sentido inverso  1.000  0.000  0.000  0.000
#
# Os tres zeros nao sao sorte: as outras assinaturas nao tem lacuna nenhuma,
# entao elas nem entram neste sentido.
#
# E O SENTIDO INVERSO NASCEU SEM PEGAR O CASO REAL, medido em 2026-09-01.
#
# O desenho acima estava certo e a constante estava errada. A largura da lacuna
# entre a coroa e o nome foi calibrada num unico exemplo com coroa (a fixture do
# Korzis, 4 colunas em branco), e a coroa real do usuario tem 3. Como
# `_inicio_do_nome_apos_ornamento` exigia 4, a assinatura do Welazkez era lida
# como "bloco unico" e o sentido inverso nao comecava.
#
# O sintoma em campo: apos um disconnect que remontou a party, ele virou
# "Membro 2" e o aprendiz gravou uma assinatura NOVA E ANONIMA dele — copia
# limpa do nome sem coroa. Uma duplicata anonima de quem JA TEM NOME e pior do
# que o silencio: no dia em que ele deixar a lideranca, ela sequestra a linha,
# ele fica "Membro N" para sempre e o nome batizado fica orfao.
#
# A separacao esta medida em COLUNAS_DE_LACUNA_DO_ORNAMENTO, junto com a razao
# pela qual baixar a exigencia nao compra risco.


# O MINIMO de colunas em branco que separam a coroa do nome que ela empurrou.
#
# A coroa e um bloco de pixels claros ANTES do nome, com uma faixa vazia entre
# os dois. `_inicio_do_nome_apos_ornamento` cobra `diff > esta constante`, e
# `diff` e "colunas em branco + 1" — entao o valor aqui E o numero minimo de
# brancos que delata uma coroa.
#
# ELE JA VALEU 4, E 4 ESTAVA ERRADO. Medido em 20 mascaras reais (4 assinaturas
# calibradas do usuario, 4 do acervo aprendido dele, 4 assinaturas da fixture e
# 8 recortes ao vivo das duas fixtures de tela), maior lacuna de cada uma:
#
#     SEM coroa (16 mascaras)  2 brancos, TODAS as dezesseis
#     COM coroa ( 4 mascaras)  3, 4, 4, 4
#
# A unica de 3 e a coroa REAL do usuario, na assinatura do Welazkez. As de 4 sao
# a fixture do Korzis e os recortes ao vivo dela. Com a constante em 4 o
# reconhecimento passava raspando na fixture e falhava em campo — a regressao de
# 2026-09-01, em que o Welazkez virou "Membro 2" depois de um disconnect e o
# aprendiz gravou uma duplicata ANONIMA de quem ja tinha nome.
#
# Nao ha zona cinzenta em 3: nenhuma mascara sem coroa passa de 2 brancos. E a
# mesma qualidade de evidencia que sustenta FATOR_MAXIMO_DE_CONTAMINACAO.
#
# E BAIXAR ISTO NAO COMPRA RISCO, porque o pico e agudo. Medido com o recorte
# real do Welazkez sem coroa contra a assinatura dele com coroa, deslocando a
# assinatura para a esquerda de 0 a 29 px:
#
#      0 px -> 0.1843    12 px -> 0.2098
#      2 px -> 0.2645    14 px -> 0.3245
#      4 px -> 0.2124    16 px -> 0.3187
#      6 px -> 0.2342    18 px -> 0.2901
#      8 px -> 0.2697    19 px -> 0.9667   <<< a lacuna manda ancorar aqui
#     10 px -> 0.2755    20 px -> 0.3015
#                        24 px -> 0.3428
#
# Um pixel para o lado e a correlacao desaba. Entao uma coroa lida onde nao ha
# nao produz um nome errado: produz um alinhamento qualquer, um alinhamento
# qualquer pontua ~0.30, e LIMIAR_DO_ORNAMENTO = 0.85 recusa com folga. O que
# esta constante controla nao e a chance de acertar errado, e a chance de sequer
# TENTAR quando ha o que acertar.
#
# Ler a lacuna continua sendo reconhecer uma estrutura que so a coroa produz,
# nao chutar um deslocamento.
COLUNAS_DE_LACUNA_DO_ORNAMENTO = 3

# O segundo passe afirma mais do que o primeiro — ele diz "isto aqui e um nome
# empurrado por um ornamento" — entao paga mais caro para ser aceito. Os
# casamentos certos sobram: medidos em 0.946 a 0.992 no alinhamento correto.
LIMIAR_DO_ORNAMENTO = 0.85
MARGEM_DO_ORNAMENTO = 0.25

# Abaixo disto, nao afirmamos quem e. Fica bem acima do melhor caso de nomes
# diferentes (0.454) e bem abaixo do pior caso do mesmo nome (1.000).
LIMIAR_DE_CASAMENTO = 0.75

# Se o segundo melhor chega perto do primeiro, o casamento nao e confiavel.
# Melhor dizer "nao sei" do que apontar o nome errado com confianca.
MARGEM_MINIMA_SOBRE_O_SEGUNDO = 0.12

# Recorte com pouquissimo texto e linha vazia, nao nome
PIXELS_MINIMOS_DE_TEXTO = 12

# Quantas vezes o recorte pode ter mais pixels claros que a assinatura antes de
# ser considerado CONTAMINADO.
#
# A mascara de texto so tem piso de brilho (V > 180), sem teto. Quando algo
# claro passa na regiao do nome — medido: V mediano 230, S mediano 6, ou seja
# BRANCO, nao terreno colorido — esses pixels entram na mascara e destroem a
# correlacao. Um teto de saturacao nao ajuda: com S<=30 ainda sobravam 200 dos
# 251 pixels. O sinal confiavel e o TAMANHO da mascara.
#
# Medido nas fixtures, recorte / assinatura:
#     limpo         0.82  0.90  0.92  0.98  1.05  1.09
#     contaminado   3.29  4.90
# Nao ha zona cinzenta. 2.0 fica no meio do vazio.
FATOR_MAXIMO_DE_CONTAMINACAO = 2.0


def mascara_de_texto(bgr: np.ndarray) -> np.ndarray:
    """Marca os pixels que sao texto da UI, descartando o cenario.

    So brilho, de proposito: o nome do LIDER da party e amarelo e seria
    rejeitado por qualquer filtro de saturacao que ainda barrasse o terreno.
    """
    if bgr.size == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return (hsv[:, :, 2] > VALOR_MINIMO_DO_TEXTO).astype(np.uint8)


@dataclass(frozen=True, eq=False)
class Assinatura:
    """A impressao digital visual do nome de um membro.

    `eq=False` porque a classe carrega ndarray. O `__eq__` de dataclass compara
    os campos como tupla, `array == array` devolve um ARRAY, e `bool()` dele
    levanta `ValueError`. O atalho de identidade de `PyObject_RichCompareBool`
    esconde isso em quase todo teste, e foi assim que o crash de 02/09/2026
    chegou ao usuario por `aprendiz._Vigia`. Ver a docstring de `_Vigia` e o
    portao em `tests/test_dataclass_com_ndarray.py`.

    Quem quiser comparar duas assinaturas PELO CONTEUDO tem `chave_da_assinatura`,
    que e o que o acervo ja usa para deduplicar em disco.
    """

    nome: str
    mascara: np.ndarray  # 0/1, do recorte do nome

    @property
    def pixels_de_texto(self) -> int:
        return int(self.mascara.sum())

    @property
    def anonima(self) -> bool:
        """Esta assinatura existe, e nao sabemos de quem e.

        E o estado normal de uma entrada do acervo antes do batismo: o scanner
        reconhece a linha, e nao tem nome nenhum para chamar aquela pessoa.

        A string VAZIA foi escolhida em vez de `None` porque ela e FALSY, e e a
        falsidade dela que faz `_chave_da_linha` (`linha.nome or f"#linha{...}"`)
        e `_rotular` (`if linha.nome:`) degradarem para `#linha{N}` e
        "Membro N" sem uma linha de mudanca no rastreador. O silencio de quem
        nao foi reconhecido e HERDADO pelo anonimo, e nao remendado por cima —
        e o remendo por cima e exatamente onde uma linha anonima ganharia
        permissao para virar sujeito de alerta.
        """
        return not self.nome

    def como_dict(self) -> dict:
        """Serializa para o arquivo de calibracao.

        Guardamos a mascara empacotada em bits: e 8x menor que um PNG e nao
        depende de codec nenhum para voltar.
        """
        altura, largura = self.mascara.shape
        empacotado = np.packbits(self.mascara.flatten())
        return {
            "nome": self.nome,
            "altura": int(altura),
            "largura": int(largura),
            "bits": empacotado.tobytes().hex(),
        }

    @classmethod
    def de_dict(cls, dados: dict) -> "Assinatura":
        altura, largura = int(dados["altura"]), int(dados["largura"])
        bytes_ = bytes.fromhex(dados["bits"])
        plano = np.unpackbits(np.frombuffer(bytes_, dtype=np.uint8))
        return cls(
            nome=dados["nome"],
            mascara=plano[: altura * largura].reshape(altura, largura),
        )


def criar_assinatura(nome: str, recorte_do_nome: np.ndarray) -> Assinatura:
    return Assinatura(nome=nome, mascara=mascara_de_texto(recorte_do_nome))


def _correlacionar(alvo: np.ndarray, molde: np.ndarray) -> float:
    """Compara o recorte com o molde NO ALINHAMENTO CALIBRADO.

    Uma posicao so, de proposito. A versao anterior tomava o MAXIMO sobre 25
    deslocamentos horizontais, e cada deslocamento e uma chance independente de
    um nome errado encontrar um alinhamento sortudo e passar do limiar.

    Medido em 60 frames reais e na fixture, alinhado -> maximo deslizante:

        casamentos CORRETOS   0.877 -> 0.877   0.907 -> 0.907   (+0.000, 8 de 8)
        casamentos ERRADOS    0.213 -> 0.586   0.199 -> 0.530   (ate +0.373)

    O deslize nao dava nada a quem estava certo e dava quase quatro decimos a
    quem estava errado. Ele comia metade da margem ate o limiar de 0.75.
    """
    if alvo.size == 0 or molde.size == 0:
        return 0.0
    if molde.shape[0] > alvo.shape[0] or molde.shape[1] > alvo.shape[1]:
        return 0.0

    fa, fm = alvo.astype(np.float32), molde.astype(np.float32)
    # mascara uniforme (tudo 0 ou tudo 1) tem desvio zero e quebra a correlacao
    if fa.std() < 1e-6 or fm.std() < 1e-6:
        return 0.0
    # [0, 0] e o molde na origem do recorte — a posicao que a calibracao gravou.
    return float(cv2.matchTemplate(fa, fm, cv2.TM_CCOEFF_NORMED)[0, 0])


@dataclass(frozen=True)
class Casamento:
    """Resultado de identificar um recorte de nome."""

    nome: str | None  # None quando nao da para afirmar
    confianca: float
    segundo_melhor: float = 0.0

    @property
    def identificado(self) -> bool:
        """Sabemos QUEM esta nesta linha?

        Um casamento com uma assinatura ANONIMA e um CASAMENTO, e nao uma
        IDENTIFICACAO: o scanner achou a mesma pessoa de sempre e continua sem
        saber o nome dela. `self.nome is not None` responderia "sim, sei quem e"
        sobre uma linha que ninguem batizou — e o acervo existe justamente para
        guardar entradas antes do batismo.

        A distincao esta aqui, e nao no chamador, para que a Fase 2 (aprender) e
        a Fase 3 (batizar) nao herdem uma propriedade que mente por omissao.
        """
        return bool(self.nome)


def _primeira_coluna_com_texto(mascara: np.ndarray) -> int | None:
    colunas = np.flatnonzero(mascara.any(axis=0))
    return int(colunas[0]) if colunas.size else None


def _inicio_do_nome_apos_ornamento(mascara: np.ndarray) -> int | None:
    """Onde o nome comeca, quando ha um ornamento (a coroa) na frente dele.

    Devolve None quando a mascara e um bloco unico — ou seja, quando NAO ha
    ornamento nenhum, que e o caso de todo membro que nao e lider. Assim o
    segundo passe simplesmente nao acontece para eles.
    """
    colunas = np.flatnonzero(mascara.any(axis=0))
    if colunas.size == 0:
        return None
    lacunas = np.flatnonzero(np.diff(colunas) > COLUNAS_DE_LACUNA_DO_ORNAMENTO)
    if lacunas.size == 0:
        return None
    # A PRIMEIRA lacuna: a coroa vem antes do nome, e o nome pode ter lacunas
    # internas maiores em fontes largas.
    return int(colunas[lacunas[0] + 1])


def _deslocar_para_a_esquerda(
    mascara: np.ndarray, deslocamento: int
) -> np.ndarray | None:
    """Puxa a mascara `deslocamento` colunas para tras, preenchendo com vazio.

    UMA funcao para os dois sentidos do ornamento, e nao duas iguais. As duas
    reancoragens fazem exatamente este recorte-e-cola; escrever o `zeros_like` e
    a fatia duas vezes seria duas chances de elas divergirem numa correcao
    futura, e o sintoma de uma divergencia aqui e um alinhamento de 1 px errado
    — que derruba a correlacao de 1.000 para 0.24 sem quebrar teste nenhum do
    outro sentido.

    Devolve None quando o deslocamento nao e para a ESQUERDA, ou quando ele
    engoliria a mascara inteira. "Nao e para a esquerda" e recusa deliberada, e
    nao defesa contra indice negativo: um ornamento so empurra o texto para a
    direita, entao descontar um so pode puxa-lo de volta. Aceitar o sentido
    contrario seria um alinhamento que a coroa nunca produz — pura chance extra
    de um nome errado dar sorte.
    """
    if deslocamento <= 0:
        return None
    largura = mascara.shape[1] - deslocamento
    if largura <= 0:
        return None
    reancorada = np.zeros_like(mascara)
    reancorada[:, :largura] = mascara[:, deslocamento:]
    return reancorada


def _reancorar_apos_ornamento(
    mascara: np.ndarray, inicio_do_nome: int, assinatura: Assinatura
) -> np.ndarray | None:
    """Puxa o nome para o lugar onde ESTA assinatura o gravou.

    O sentido em que a coroa esta NO RECORTE ao vivo e falta na assinatura: quem
    foi calibrado sem coroa e depois virou lider.

    Alinhar na coluna 0 nao serve: assinaturas reais comecam na coluna 0 OU na
    1, conforme o nome, e 1 px de erro derruba a correlacao de 1.000 para 0.24.
    Entao o deslocamento e sempre medido contra a primeira coluna da assinatura.
    """
    coluna_da_assinatura = _primeira_coluna_com_texto(assinatura.mascara)
    if coluna_da_assinatura is None:
        return None
    return _deslocar_para_a_esquerda(
        mascara, inicio_do_nome - coluna_da_assinatura
    )


def _reancorar_a_assinatura_sem_ornamento(
    assinatura: Assinatura, coluna_do_recorte: int | None
) -> np.ndarray | None:
    """Tira a coroa DA ASSINATURA e poe o nome onde o recorte o mostra.

    O sentido inverso do de cima, e o que faltava: a coroa esta gravada na
    ASSINATURA e sumiu da tela — quem calibrou enquanto era lider e depois
    deixou de ser. Visto em campo em 2026-08-31; ver a nota da coroa no topo.

    O que se desloca aqui e a ASSINATURA, e nao o recorte, porque e nela que
    esta o ornamento a descontar. O destino e a primeira coluna DO RECORTE, pelo
    mesmo motivo que o outro sentido ancora na primeira coluna da assinatura:
    um nome sem coroa comeca na coluna 0, 1 ou 2 conforme o nome, e ancorar na
    origem erraria por ate 2 px — 1 px ja leva 1.000 para 0.24.

    Devolve None quando a assinatura nao tem ornamento (bloco unico, que e o
    caso de todo membro que nao e lider) ou quando o recorte esta vazio. E a
    trava que faz quase todo o trabalho e nao custa nada: medido em 20 mascaras
    reais, as 16 sem coroa nao passam de 2 colunas em branco de lacuna, e por
    isso nenhuma delas chega a ser deslocada.
    """
    if coluna_do_recorte is None:
        return None
    depois_do_ornamento = _inicio_do_nome_apos_ornamento(assinatura.mascara)
    if depois_do_ornamento is None:
        return None
    return _deslocar_para_a_esquerda(
        assinatura.mascara, depois_do_ornamento - coluna_do_recorte
    )


def _pontuar_com_ornamento(
    mascara: np.ndarray, assinaturas: list[Assinatura]
) -> list[float] | None:
    """Pontuacao supondo que um ornamento empurrou o nome para a direita.

    A coroa esta NO RECORTE ao vivo e falta na assinatura.

    Devolve None quando a mascara nao tem a estrutura "bloco, lacuna, bloco" —
    isto e, quando nao ha ornamento para descontar.
    """
    inicio = _inicio_do_nome_apos_ornamento(mascara)
    if inicio is None:
        return None

    pontos: list[float] = []
    for assinatura in assinaturas:
        reancorada = _reancorar_apos_ornamento(mascara, inicio, assinatura)
        if reancorada is None or int(reancorada.sum()) < PIXELS_MINIMOS_DE_TEXTO:
            pontos.append(0.0)
            continue
        pontos.append(_correlacionar(reancorada, assinatura.mascara))
    return pontos


def _pontuar_sem_o_ornamento_da_assinatura(
    mascara: np.ndarray, assinaturas: list[Assinatura]
) -> list[float] | None:
    """Pontuacao supondo que a assinatura foi gravada COM um ornamento que sumiu.

    O sentido inverso do de cima, e o que faltava. Aqui quem carrega a estrutura
    "bloco, lacuna, bloco" e a ASSINATURA, entao a pergunta e feita uma vez por
    assinatura e nao uma vez pela linha.

    Devolve None quando NENHUMA assinatura tem ornamento — o caso comum, em que
    este sentido nem existe. Uma lista de zeros diria outra coisa: diria "avaliei
    e nao casou com ninguem", e faria a linha entrar na disputa do segundo passe
    sem ter candidato nenhum.
    """
    coluna_do_recorte = _primeira_coluna_com_texto(mascara)

    pontos: list[float] = []
    algum_ornamento = False
    for assinatura in assinaturas:
        molde = _reancorar_a_assinatura_sem_ornamento(assinatura, coluna_do_recorte)
        if molde is None or int(molde.sum()) < PIXELS_MINIMOS_DE_TEXTO:
            pontos.append(0.0)
            continue
        algum_ornamento = True
        pontos.append(_correlacionar(mascara, molde))
    return pontos if algum_ornamento else None


def _pontuar(
    recorte: np.ndarray, assinaturas: list[Assinatura]
) -> list[float] | None:
    """Pontuacao do recorte contra cada assinatura, na ordem recebida.

    Devolve None quando o recorte nao tem texto suficiente para ser um nome —
    linha vazia, nao um nome que falhamos em ler.
    """
    return _pontuar_mascara(mascara_de_texto(recorte), assinaturas)


def _pontuar_mascara(
    mascara: np.ndarray, assinaturas: list[Assinatura]
) -> list[float] | None:
    pixels = int(mascara.sum())
    if pixels < PIXELS_MINIMOS_DE_TEXTO:
        return None

    pontos: list[float] = []
    for assinatura in assinaturas:
        # Um recorte com MUITO mais pixels claros do que este nome tem nao pode
        # ser este nome — tem outra coisa dentro dele. Zerar o par e melhor do
        # que deixar uma correlacao degradada disputar a linha: e assim que uma
        # assinatura errada ganha um recorte que ninguem deveria ter ganhado.
        #
        # Note que isto NAO tenta salvar o reconhecimento do membro
        # contaminado. Ele fica sem nome nesse frame, o que e a resposta
        # honesta. O que a regra impede e a vaga vazia ser ocupada por outro.
        excedente = (
            assinatura.pixels_de_texto
            and pixels > assinatura.pixels_de_texto * FATOR_MAXIMO_DE_CONTAMINACAO
        )
        pontos.append(
            0.0 if excedente else _correlacionar(mascara, assinatura.mascara)
        )
    return pontos


def identificar_linhas(
    recortes: dict[int, np.ndarray], assinaturas: list[Assinatura]
) -> dict[int, Casamento]:
    """Resolve o frame INTEIRO de uma vez, com UNICIDADE.

    POR QUE NAO DA PARA DECIDIR UMA LINHA POR VEZ

    Decidindo linha a linha, nada impede a mesma assinatura de ganhar duas
    linhas no mesmo frame. Isso nao e teorico: aconteceu 8 vezes em
    logs/scanner.log, e uma delas foi

        17:21:04  KAUS SAIU DA PARTY
        17:21:09  status: Korzis, Korzis, TioMad, J4guar
        17:21:42  KAUS ENTROU NA PARTY

    O Korzis casou tambem na linha do Kaus. Como o rastreador guarda estado por
    IDENTIDADE, o Kaus simplesmente sumiu do conjunto de presentes, e a mentira
    virou um par de alertas. Numa party estavel isso rendeu 52 eventos falsos em
    25 minutos.

    A pessoa em cada linha e uma pessoa DIFERENTE — essa e uma restricao do
    dominio, e restricao de dominio pertence ao algoritmo, nao a um teste que
    torce para nao acontecer.

    COMO RESOLVE

    Guloso pelo melhor par global: pega a maior pontuacao ainda disponivel,
    confirma que ela passa do limiar e tem margem sobre a melhor alternativa que
    AINDA sobrou para aquela linha, e ai consome a linha E a assinatura. Uma
    assinatura consumida nao volta para a mesa.

    Guloso e nao otimo (Hungarian seria), mas com 4 a 8 linhas a diferenca e
    irrelevante e o resultado e explicavel: da para olhar as pontuacoes e dizer
    por que cada linha recebeu o nome que recebeu.
    """
    resultado = {i: Casamento(nome=None, confianca=0.0) for i in recortes}
    if not assinaturas:
        return resultado

    mascaras: dict[int, np.ndarray] = {
        indice: mascara_de_texto(recorte) for indice, recorte in recortes.items()
    }

    pontos: dict[int, list[float]] = {}
    for indice, mascara in mascaras.items():
        p = _pontuar_mascara(mascara, assinaturas)
        if p is not None:
            pontos[indice] = p

    linhas_livres = set(pontos)
    assinaturas_livres = set(range(len(assinaturas)))

    while linhas_livres and assinaturas_livres:
        # O melhor par (linha, assinatura) ainda em jogo. O desempate por
        # indice mantem o resultado deterministico: mesmo frame, mesma saida.
        valor, i, j = max(
            (pontos[i][j], -i, -j)
            for i in linhas_livres
            for j in assinaturas_livres
        )
        i, j = -i, -j

        if valor < LIMIAR_DE_CASAMENTO:
            break

        # A margem e medida contra o que AINDA esta disponivel. Se a segunda
        # opcao ja foi consumida por outra linha, ela nao e mais uma duvida.
        outras = [pontos[i][k] for k in assinaturas_livres if k != j]
        segundo = max(outras) if outras else 0.0

        if valor - segundo < MARGEM_MINIMA_SOBRE_O_SEGUNDO:
            # Dois candidatos empatados significam que a assinatura nao
            # discrimina. Dizer "nao sei" e mais util do que escolher no
            # desempate — e a linha sai de jogo sem consumir assinatura nenhuma.
            resultado[i] = Casamento(None, valor, segundo)
            linhas_livres.discard(i)
            continue

        resultado[i] = Casamento(assinaturas[j].nome, valor, segundo)
        linhas_livres.discard(i)
        assinaturas_livres.discard(j)

    _segundo_passe_do_ornamento(
        mascaras, assinaturas, resultado, linhas_livres, assinaturas_livres
    )

    # Sobrou linha sem nome: guardamos a melhor pontuacao mesmo assim, porque e
    # ela que aparece no diagnostico quando alguem pergunta "por que nao
    # reconheceu?".
    for i in linhas_livres:
        ordenado = sorted(pontos[i], reverse=True)
        resultado[i] = Casamento(
            None, ordenado[0], ordenado[1] if len(ordenado) > 1 else 0.0
        )

    return resultado


def _melhor_dos_dois_sentidos(
    mascara: np.ndarray, assinaturas: list[Assinatura]
) -> list[float] | None:
    """A pontuacao do segundo passe: o melhor dos dois sentidos, par a par.

    QUANTOS ALINHAMENTOS ISSO CUSTA, que e a unica pergunta que importa aqui.
    No maximo DOIS por par (linha, assinatura), e cada um sai da estrutura dos
    pixels — nao ha varredura. O `.max()` que foi removido testava 25 por par e
    levava o pior casamento errado de 0.213 para 0.586. Dois alinhamentos
    determinados nao sao meio caminho de volta para aquilo: sao dois.

    E na pratica quase sempre e UM so. Os dois sentidos pedem lacunas em lados
    opostos — um no recorte, outro na assinatura — e uma pessoa e lider ou nao
    e. Os dois valerem ao mesmo tempo significa recorte E assinatura com coroa,
    e nesse caso o alinhamento calibrado ja casa e o primeiro passe resolveu a
    linha antes de este codigo rodar.

    Devolve None quando NENHUM dos dois sentidos se aplica, e ai a linha nem
    entra na disputa.
    """
    no_recorte = _pontuar_com_ornamento(mascara, assinaturas)
    na_assinatura = _pontuar_sem_o_ornamento_da_assinatura(mascara, assinaturas)

    if no_recorte is None:
        return na_assinatura
    if na_assinatura is None:
        return no_recorte
    return [max(a, b) for a, b in zip(no_recorte, na_assinatura)]


def _segundo_passe_do_ornamento(
    mascaras: dict[int, np.ndarray],
    assinaturas: list[Assinatura],
    resultado: dict[int, Casamento],
    linhas_livres: set[int],
    assinaturas_livres: set[int],
) -> None:
    """A repescagem da coroa do lider. Modifica `resultado` no lugar.

    POR QUE ELE EXISTE

    O lider da party ganha uma coroa antes do nome, e a coroa empurra o texto
    para a direita. Quem foi calibrado SEM coroa e depois virou lider casa 0.266
    contra a propria assinatura (medido com os pixels reais) — some do
    reconhecimento e nao volta nem apos reiniciar o scanner. Aconteceu, e custou
    duas horas de operacao cega em 2026-08-25.

    O INVERSO custa o mesmo e acontece igual: quem foi calibrado ENQUANTO era
    lider e depois deixou de ser tem a coroa gravada na ASSINATURA e ausente da
    tela. Visto em 2026-08-31, numa party de quatro com os quatro calibrados,
    onde os dois membros perdidos foram exatamente os dois cuja lideranca havia
    mudado. Os dois sentidos entram por `_melhor_dos_dois_sentidos`.

    POR QUE ELE E SEGURO

    Tres travas, e cada uma sozinha ja limita o estrago:

      1. So olha linhas que o primeiro passe deixou SEM NOME, e so usa
         assinaturas que ele NAO consumiu. E estritamente aditivo: nao existe
         caminho por onde ele tire ou troque um nome que o primeiro passe deu.
      2. Testa UM alinhamento a mais POR SENTIDO, e nao um leque. O alinhamento
         nao e varrido: sai da estrutura de um dos lados (a lacuna entre a coroa
         e o nome) e e ancorado na primeira coluna do outro. Deslizar 0..14 px
         levaria o pior casamento errado de 0.371 para 0.579 — foi o que produziu
         o bug do "entra e sai". Aqui nao ha deslize. Com os dois sentidos o teto
         por par vai a DOIS alinhamentos, e a conta de por que dois nao e meio
         caminho de volta para vinte e cinco esta em `_melhor_dos_dois_sentidos`.
      3. Cobra mais caro: LIMIAR_DO_ORNAMENTO e MARGEM_DO_ORNAMENTO sao bem
         acima dos do primeiro passe. Uma afirmacao mais forte precisa de
         evidencia mais forte.

    E, antes das tres, a trava que faz quase todo o trabalho: um nome sem coroa e
    um bloco unico de texto, entao `_inicio_do_nome_apos_ornamento` devolve None
    e o passe nem comeca para ele — vale para o recorte no primeiro sentido e
    para a assinatura no segundo. Medido em 20 mascaras reais: as 16 sem coroa
    nao passam de 2 colunas em branco de lacuna, e as 4 que se partem em dois
    sao exatamente as 4 do lider. Ver COLUNAS_DE_LACUNA_DO_ORNAMENTO, cuja
    calibragem em 4 (e nao 3) foi a regressao de 2026-09-01.
    """
    # Sem guarda de saida antecipada aqui de proposito: o `while` abaixo ja nao
    # roda com qualquer um dos dois conjuntos vazio. Um `if not ... : return`
    # seria um ramo que nenhum teste consegue distinguir do codigo sem ele —
    # teste de mutacao confirmou que era equivalente.
    candidatos: dict[int, list[float]] = {}
    for i in linhas_livres:
        p = _melhor_dos_dois_sentidos(mascaras[i], assinaturas)
        if p is not None:
            candidatos[i] = p

    # Mesmo criterio guloso do primeiro passe, e pelo mesmo motivo: com um
    # recorte contaminado, mais de uma linha pode parecer ter ornamento, e a
    # unicidade continua valendo — duas linhas sao duas pessoas diferentes.
    while candidatos and assinaturas_livres:
        valor, i, j = max(
            (candidatos[i][j], -i, -j)
            for i in candidatos
            for j in assinaturas_livres
        )
        i, j = -i, -j

        if valor < LIMIAR_DO_ORNAMENTO:
            break

        outras = [candidatos[i][k] for k in assinaturas_livres if k != j]
        segundo = max(outras) if outras else 0.0
        if valor - segundo < MARGEM_DO_ORNAMENTO:
            del candidatos[i]
            continue

        resultado[i] = Casamento(assinaturas[j].nome, valor, segundo)
        linhas_livres.discard(i)
        assinaturas_livres.discard(j)
        del candidatos[i]


def identificar(
    recorte_do_nome: np.ndarray, assinaturas: list[Assinatura]
) -> Casamento:
    """De quem e este nome? Caso de uma linha so.

    Devolve `nome=None` quando nao da para afirmar. Isso e deliberado: o
    rastreador degrada para "Membro N", que e feio mas honesto. Chutar um nome
    seria pior do que nao ter nome nenhum — um alerta com o nome errado manda
    a party socorrer a pessoa errada.
    """
    return identificar_linhas({0: recorte_do_nome}, assinaturas)[0]
