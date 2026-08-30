"""O que o OCR LEU, ao lado do que o padrao DECIDIU, para cada boss da lista.

Esta ferramenta existe para fechar R-01: a frase `<Nome> [Lv. NN] has spawned!`
e asserção do usuario, medida de um print em 2026-08-30, e nunca atravessou o
pipeline de OCR deste projeto. Toda a suite alimenta o vigia com texto JA
decodificado. Ate esta ferramenta rodar sobre pixels de verdade, a tolerancia
de OCR de `l2scanner/bosses.py` e palpite fundamentado, nao medicao.

POR QUE O `--replay` DO SCANNER NAO SERVE, E ESTE E O BURACO QUE ELA TAPA
-------------------------------------------------------------------------
`ReplaySource.capturar` (`l2scanner/frames.py`) monta o `Frame` **sem**
`extras`: o laco de captura da JANELA recorta o chat e o alvo do frame
completo, mas o replay le um PNG e para por ai. Entao, num `--replay`,
`frame.extras.get("tiat_chat")` e sempre `None`, `VigiaDeBosses.avaliar` recebe
`None` nos dois recortes e devolve `[]` — para SEMPRE, com qualquer gravacao.
Reproduzir uma sessao gravada nao confronta a frase; ela so PARECE confrontada.
Esta ferramenta faz o recorte que o replay nao faz.

O QUE ELA IMPRIME, E POR QUE O TEXTO CRU VEM ANTES DO VEREDITO
---------------------------------------------------------------
Um veredito NAO, sozinho, nao diz nada acionavel — ele nao distingue "o OCR
perdeu um caractere" de "o OCR leu lixo" de "o padrao esta errado". O texto CRU
distingue os tres, e por isso ele sai SEMPRE, em REPRESENTACAO (`repr`) e linha
a linha. Solto, um espaco final ou um caractere de controle ficaria invisivel
exatamente no relatorio que existe para mostra-lo — e um espaco a mais e uma
das coisas que mais derruba um casamento.

AS DUAS ESCALAS SAEM LADO A LADO, E A DIVERGENCIA E O ACHADO
-------------------------------------------------------------
`ocr.ler_texto` le em 2x (a passada de DETECCAO, a que o scanner roda na
cadencia) e `ocr.ler_texto_ampliado` le em 3x (a de CONFERENCIA). A precisao do
motor NAO e monotonica na escala — a tabela no topo de `l2scanner/ocr.py`
registra uma medicao anterior que foi refutada por isso mesmo. Entao:

    as duas leem e casam ......... o reconhecimento esta bom nesta fonte
    so a de CONFERENCIA casa ..... a correcao NAO e afrouxar o padrao. E o
                                   scanner ler o recorte do chat na escala
                                   maior. Isso e item de roadmap, nao remendo.
    nenhuma le nada reconhecivel . o problema esta antes do padrao: recorte
                                   errado, fonte pequena demais, ou contraste.
    as duas leem e nenhuma casa ... AI sim o padrao e o suspeito, e a linha
                                   PISTA diz qual caractere se perdeu.

A LINHA `PISTA`, E O QUE ELA TEM DIREITO DE PEDIR
--------------------------------------------------
Quando nenhum boss casa mas o texto lido tem um trecho PARECIDO com o nome, a
ferramenta imprime o primeiro ponto de divergencia: a posicao, o caractere
esperado e o caractere lido, os dois em `repr`. E o que transforma um "nao
casou" numa acao — o caractere medido vira UMA entrada a mais em
`_FOLGA_DE_OCR` mais um teste com a string exata.

A divergencia e calculada PERGUNTANDO A MECANICA DE PRODUCAO, e nao por
igualdade crua: `padrao_do_nome(caractere)` responde se aquele par ja e
tolerado. Sem isso a pista acusaria o `0` lido no lugar do `o`, que a folga JA
aceita — e mandaria alguem afrouxar uma tolerancia existente, que e o primeiro
passo do caminho que devolve o padrao ao curinga (T-04-01).

**A pista SUGERE, e nunca decide.** Ela nao altera veredito nenhum, e o
afrouxamento que ela indica nao pertence a esta ferramenta: `_FOLGA_DE_OCR` e
`_DIGITO_COM_FOLGA` moram em `l2scanner/bosses.py`. Cada tolerancia nova entra
NOMEANDO o caractere medido que a justificou, com um teste do sentido negativo
ao lado. Afrouxar a parte fixa inteira de uma vez desfaria RECO-01 sem deixar
nenhum teste vermelho.

NENHUMA EXPRESSAO REGULAR NASCE AQUI (T-04-03)
-----------------------------------------------
`padrao_do_anuncio` e `padrao_do_nome` sao IMPORTADOS de `l2scanner.bosses`. E
o que garante duas coisas ao mesmo tempo: que o `nome` do `[[boss]]` nunca
chegue cru a um `re.compile` (a construcao escapa caractere a caractere), e que
o veredito desta ferramenta signifique a MESMA coisa que o veredito do scanner.
Medir com uma convencao e decidir com outra seria comparar convencoes. A
convencao de casamento tambem e copiada e nao reinventada: o ANUNCIO e
procurado LINHA A LINHA (`splitlines`), como em `VigiaDeBosses.avaliar`, para
que o `\\s+` da parte fixa nao costure a linha de um jogador com a de outro; o
NOME e procurado no blob, porque o recorte do ALVO nao tem linhas.

Uso (no checkout PRINCIPAL — `recordings/` e gitignored e nao se materializa em
worktree; e o `.venv` e onde as bindings de OCR estao instaladas):

    .venv/Scripts/python.exe -m tools.conferir_anuncio_de_boss PRINT.png
        --regiao chat --recorte 20 880 600 470

    .venv/Scripts/python.exe -m tools.conferir_anuncio_de_boss recordings
        --regiao chat --recorte 20 880 600 470

Codigo de saida 0 quando a varredura COMPLETOU, inclusive sem casamento nenhum
— ausencia de casamento e um resultado, e no sentido negativo e o resultado
desejado. Codigo 1 so quando a ferramenta nao conseguiu MEDIR: motor de OCR
ausente, regiao desconhecida, nenhuma imagem, recorte fora da imagem. A
distincao e a mitigacao de T-04-02: uma varredura vazia confundida com "nenhum
boss apareceu" levaria a afrouxar um padrao que estava certo.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable

import cv2

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from l2scanner import ocr  # noqa: E402
from l2scanner.bosses import padrao_do_anuncio, padrao_do_nome  # noqa: E402
from l2scanner.calibracao import Calibracao  # noqa: E402
from l2scanner.config import ler_bosses  # noqa: E402
from l2scanner.frames import Regiao  # noqa: E402

# Quanta semelhanca um trecho do texto lido precisa ter com o nome do boss para
# merecer uma linha PISTA.
#
# ESTE NUMERO NAO DECIDE NADA. Ele so escolhe quando vale a pena GASTAR UMA
# LINHA de saida apontando uma divergencia; o veredito ja foi calculado antes,
# pelos padroes de producao, e nao muda. Mexer nele nunca produz um casamento a
# mais nem a menos.
#
# 0,65 E MEDIDO, e o 0,6 que estava aqui antes (o corte que
# `difflib.get_close_matches` usa por padrao) foi REFUTADO pela varredura de
# 2.110 frames de chat real. As duas populacoes, medidas contra `tiat north`:
#
#     NEAR-MISS de verdade      0,700  'T1at N0rlh'  (t -> l, o pior do lote)
#                               0,900  'Tiat Nortb'  (h -> b)
#                               0,947  'Tiat Nort'   (o h sumiu)
#     RUIDO de chat real        0,600  'tion for T'  (112 ocorrencias)
#                               0,600  'target. Th'  (68)
#                               0,600  'Team: Norm'  (20)
#                               0,400  'ta sozinho'
#
# Em 0,6 a varredura cuspiu 320 linhas PISTA com ZERO near-miss de verdade no
# meio — e uma pista que dispara 320 vezes enterra a unica que importa no dia
# em que o usuario colar o print do spawn. Como as duas populacoes nao se
# sobrepoem (pior near-miss 0,700, pior ruido 0,600), o corte vai no meio.
#
# A margem e fina dos DOIS lados, e por isso vale dizer para onde o erro cai:
# uma pista que deixa de disparar custa uma linha a menos para um humano que ja
# tem o texto CRU impresso logo acima; uma pista que dispara demais custa o
# relatorio inteiro. Por isso o corte sobe ate onde a populacao de near-miss
# medida permite, e nao mais.
SEMELHANCA_MINIMA_PARA_PISTA = 0.65

# A ultima varredura, para os testes afirmarem sobre a ESTRUTURA em vez de
# sobre a formatacao do relatorio. Uma asseracao contra texto impresso quebra
# quando alguem alinha uma coluna, e passaria a medir o alinhamento.
ULTIMA_VARREDURA: "Varredura | None" = None


# ---------------------------------------------------------------------------
# O motor de OCR, injetavel
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MotorDeOcr:
    """De onde o texto vem, e como perguntar se da para ler.

    E um parametro, e nao um import direto, porque os testes desta ferramenta
    rodam com o jogo FECHADO e sem as bindings WinRT instaladas. Sem a
    injecao, a mecanica de veredito — o unico pedaco que decide alguma coisa —
    so seria exercitada nas maquinas que ja tem o motor, que sao justamente as
    unicas onde ela nao precisa ser provada.
    """

    disponivel: Callable[[], bool]
    motivo: Callable[[], "str | None"]
    escalas: "tuple[tuple[str, Callable], ...]"


def motor_do_windows() -> MotorDeOcr:
    """As duas passadas reais, na ordem em que o scanner as usa."""
    return MotorDeOcr(
        disponivel=ocr.disponivel,
        motivo=ocr.motivo_indisponivel,
        escalas=(
            ("deteccao", ocr.ler_texto),
            ("conferencia", ocr.ler_texto_ampliado),
        ),
    )


# ---------------------------------------------------------------------------
# O que a varredura produz
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VereditoDeBoss:
    boss: str
    casou_anuncio: bool
    casou_nome: bool


@dataclass(frozen=True)
class Pista:
    """Uma divergencia MEDIDA entre o texto lido e o nome esperado."""

    boss: str
    trecho: str
    semelhanca: float
    posicao: int
    esperado: str
    lido: str

    def como_linha(self) -> str:
        return (
            f"PISTA  {self.boss}: o trecho {self.trecho!r} parece o nome "
            f"({self.semelhanca:.2f} de semelhanca) e diverge na posicao "
            f"{self.posicao}: esperado {self.esperado!r}, lido {self.lido!r}"
        )


@dataclass(frozen=True)
class LeituraDeEscala:
    escala: str
    texto: "str | None"
    vereditos: "tuple[VereditoDeBoss, ...]"
    pistas: "tuple[Pista, ...]"


@dataclass(frozen=True)
class LeituraDeImagem:
    arquivo: Path
    escalas: "tuple[LeituraDeEscala, ...]"


@dataclass(frozen=True)
class Varredura:
    imagens: "tuple[LeituraDeImagem, ...]"

    @property
    def casamentos_de_anuncio(self) -> int:
        return sum(
            1
            for imagem in self.imagens
            for escala in imagem.escalas
            for veredito in escala.vereditos
            if veredito.casou_anuncio
        )

    @property
    def casamentos_de_nome(self) -> int:
        return sum(
            1
            for imagem in self.imagens
            for escala in imagem.escalas
            for veredito in escala.vereditos
            if veredito.casou_nome
        )

    @property
    def leituras_vazias(self) -> int:
        """Quantas passadas o motor devolveu sem texto nenhum.

        Sai no resumo porque uma varredura de zero casamentos sobre um monte de
        leituras vazias nao mede o padrao — ela mede que o recorte esta errado.
        """
        return sum(
            1
            for imagem in self.imagens
            for escala in imagem.escalas
            if not escala.texto
        )

    def por_boss(self) -> "dict[str, tuple[int, int]]":
        contagem: dict[str, list[int]] = {}
        for imagem in self.imagens:
            for escala in imagem.escalas:
                for veredito in escala.vereditos:
                    alvo = contagem.setdefault(veredito.boss, [0, 0])
                    alvo[0] += int(veredito.casou_anuncio)
                    alvo[1] += int(veredito.casou_nome)
        return {nome: (a, n) for nome, (a, n) in contagem.items()}


# ---------------------------------------------------------------------------
# A mecanica de veredito — importada, nunca reescrita
# ---------------------------------------------------------------------------


def julgar(texto: "str | None", bosses) -> "tuple[VereditoDeBoss, ...]":
    """O veredito por boss, na convencao EXATA de `VigiaDeBosses.avaliar`.

    O ANUNCIO e procurado linha a linha e o NOME no blob, e as duas escolhas
    sao copias literais do vigia. Ali o recorte do chat tem varias linhas de
    jogadores diferentes (por isso `splitlines`) e o recorte do alvo tem so o
    nome do mob (por isso o blob). Divergir aqui faria esta ferramenta aprovar
    frase que o scanner reprova, e o relatorio inteiro perderia o sentido.
    """
    linhas = (texto or "").splitlines()
    vereditos = []
    for boss in bosses:
        nome = boss.nome
        anuncio = padrao_do_anuncio(nome)
        so_o_nome = padrao_do_nome(nome)
        vereditos.append(
            VereditoDeBoss(
                boss=nome,
                casou_anuncio=any(
                    anuncio.search(linha) for linha in linhas
                ),
                casou_nome=bool(texto and so_o_nome.search(texto)),
            )
        )
    return tuple(vereditos)


def primeira_divergencia(nome: str, trecho: str):
    """`(posicao, esperado, lido)` do primeiro caractere que o trecho perde.

    Alinha com `difflib` e depois PERGUNTA `padrao_do_nome(caractere)` se o par
    alinhado ja e tolerado. Perguntar por igualdade crua acusaria o `0` lido no
    lugar do `o` e o `7` no lugar do `t` — trocas que a folga JA aceita — e a
    pista mandaria afrouxar o que nao esta apertado.

    `None` quando cada caractere do nome esta coberto pela folga; nesse caso o
    padrao ja teria casado e nao existe pista para dar.
    """
    casador = SequenceMatcher(None, nome, trecho, autojunk=False)
    for etiqueta, i1, i2, j1, j2 in casador.get_opcodes():
        if etiqueta == "equal":
            continue
        if etiqueta == "replace":
            for passo in range(max(i2 - i1, j2 - j1)):
                i, j = i1 + passo, j1 + passo
                esperado = nome[i] if i < i2 else ""
                lido = trecho[j] if j < j2 else ""
                if (
                    esperado
                    and lido
                    and padrao_do_nome(esperado).fullmatch(lido)
                ):
                    continue
                return i, esperado, lido
            continue
        # `delete` e `insert`: o OCR comeu ou inventou caractere. Nao ha par
        # para perguntar a folga, e a posicao ja e a informacao.
        return i1, nome[i1:i2], trecho[j1:j2]
    return None


def pista_do_boss(texto: "str | None", nome: str) -> "Pista | None":
    """O trecho mais parecido com o nome, e onde ele diverge. `None` se longe.

    Varre janelas do tamanho do nome, mas so nas posicoes cujo PRIMEIRO
    caractere a folga ja aceitaria — em uma linha de chat isso descarta a
    maioria das posicoes e mantem a varredura barata sobre milhares de frames,
    sem mudar o resultado: uma janela cuja primeira letra ja esta fora nao vai
    ganhar de uma que comeca certo.
    """
    if not texto or not nome:
        return None
    primeiro = padrao_do_nome(nome[0])
    alvo = nome.lower()
    melhor = None
    for linha in texto.splitlines():
        limite = len(linha) - len(nome) + 1
        for i in range(max(limite, 0)):
            if not primeiro.fullmatch(linha[i]):
                continue
            janela = linha[i : i + len(nome)]
            semelhanca = SequenceMatcher(
                None, alvo, janela.lower(), autojunk=False
            ).ratio()
            if semelhanca < SEMELHANCA_MINIMA_PARA_PISTA:
                continue
            if melhor is None or semelhanca > melhor[0]:
                melhor = (semelhanca, janela)
    if melhor is None:
        return None
    semelhanca, janela = melhor
    divergencia = primeira_divergencia(nome, janela)
    if divergencia is None:
        return None
    posicao, esperado, lido = divergencia
    return Pista(
        boss=nome,
        trecho=janela,
        semelhanca=semelhanca,
        posicao=posicao,
        esperado=esperado,
        lido=lido,
    )


# ---------------------------------------------------------------------------
# De onde vem a imagem e de onde vem o retangulo
# ---------------------------------------------------------------------------

# A ordem de busca dentro de uma pasta. `frame_*.png` ganha de `*.png` EM
# QUALQUER NIVEL, e essa precedencia foi MEDIDA e nao escolhida: o
# `recordings/` real tem 12 PNGs avulsos soltos na raiz (`agora_janela.png`,
# `base_party.png`, recortes de party de outro recurso) e 2.110 frames de
# gravacao nas subpastas. Com `*.png` antes de `*/frame_*.png`, apontar a
# ferramenta para `recordings` mediria os 12 avulsos e nunca desceria — uma
# varredura que parece completa e cobre 0,5% do material.
#
# O nivel de baixo existe porque `recordings/` e uma pasta DE gravacoes: parar
# no nivel zero devolveria "nenhuma imagem" com dois mil frames em disco, que e
# a forma mais cara de nao medir nada.
PADROES_DE_BUSCA = ("frame_*.png", "*/frame_*.png", "*.png", "*/*.png")


def imagens_de(caminho: Path) -> "list[Path]":
    if caminho.is_file():
        return [caminho]
    if not caminho.is_dir():
        return []
    for padrao in PADROES_DE_BUSCA:
        encontradas = sorted(caminho.glob(padrao))
        if encontradas:
            return encontradas
    return []


def regiao_da_calibracao(caminho: Path, qual: str):
    """O retangulo do chat ou do alvo, COMO ESTA GRAVADO.

    `tiat_chat` e `tiat_alvo` ja estao em coordenada de JANELA, e por isso nao
    ha conversao nenhuma a fazer: `calibrar_tiat` captura com
    `JanelaSource(...).capturar_completo()` — o frame COMPLETO DA JANELA — e
    roda `_selecionar_regiao` sobre ele. Nao existe caminho neste projeto que
    grave essas duas regioes em coordenada de desktop. Elas sao diferentes de
    `party_window`, que vem de uma varredura do desktop e por isso PRECISA da
    origem.

    A producao concorda: `laco_principal` passa
    `relativa=cal.party_window_na_janela is not None`, e o ramo `relativa` de
    `_extra_para_janela` usa `extra.esquerda` CRU.

    ESTA FUNCAO JA SUBTRAIU UMA ORIGEM AQUI (G-01, corrigido em 2026-08-30), e
    a condicao estava INVERTIDA: ela convertia exatamente no caso em que a
    producao usa o valor cru. MEDIDO contra a calibracao real: origem
    (1720,0) e `tiat_chat.esquerda = 8` davam -1712, a ferramenta recusava
    tudo e saia com 1 — enquanto o mesmo retangulo por `--recorte 8 878 625
    455` lia o chat e casava `Tiat North` no `frame_000030`. O defeito
    atravessou porque este era o unico trecho da fase sem teste; agora tem
    `TestAsRegioesDoTiatSaoRELATIVASAJanela`.

    Devolve `(regiao, explicacao)` ou `(None, motivo)`.
    """
    if not caminho.exists():
        return None, f"nao achei a calibracao em {caminho}"
    try:
        cal = Calibracao.carregar(caminho)
    except Exception as erro:  # calibracao de outra versao, JSON torto, etc.
        return None, f"nao consegui ler {caminho}: {erro}"

    regiao = cal.tiat_chat if qual == "chat" else cal.tiat_alvo
    if regiao is None:
        return None, (
            f"a calibracao {caminho.name} nao tem a regiao '{qual}' "
            "(rode calibrar-tiat.bat, ou passe --recorte)"
        )

    return regiao, f"{caminho.name}, como esta gravada (coordenada de janela)"


def recortar(imagem, regiao: Regiao):
    """O recorte, ou `None` quando o retangulo nao cabe.

    Falha FECHADA, como `_extra_para_janela`: um recorte truncado produziria
    meia linha de chat e um "nao casou" que nao mede o padrao.
    """
    if regiao.esquerda < 0 or regiao.topo < 0:
        return None
    recorte = imagem[
        regiao.topo : regiao.topo + regiao.altura,
        regiao.esquerda : regiao.esquerda + regiao.largura,
    ]
    if (
        recorte.shape[0] != regiao.altura
        or recorte.shape[1] != regiao.largura
    ):
        return None
    return recorte


# ---------------------------------------------------------------------------
# O relatorio
# ---------------------------------------------------------------------------


def imprimir_texto_cru(escala: str, texto: "str | None") -> None:
    """Sempre em REPRESENTACAO, e sempre antes do veredito."""
    if texto is None:
        print(f"    [{escala}] o motor nao devolveu texto (None)")
        return
    linhas = texto.splitlines() or [texto]
    print(f"    [{escala}] texto cru, {len(linhas)} linha(s):")
    for numero, linha in enumerate(linhas, start=1):
        print(f"      {numero:>2}  {linha!r}")
    if len(linhas) == 1 and linhas[0] == texto:
        # Uma linha so: a representacao acima ja e a do texto inteiro, e
        # repeti-la seria ruido. Duas ou mais, o blob completo importa porque e
        # nele que o casamento do NOME e procurado.
        pass
    else:
        print(f"      blob {texto!r}")


def imprimir_leitura(leitura: LeituraDeImagem, nome_curto: str) -> None:
    print(f"  {nome_curto}")
    for escala in leitura.escalas:
        imprimir_texto_cru(escala.escala, escala.texto)
        print(f"    [{escala.escala}] veredito:")
        for veredito in escala.vereditos:
            print(
                f"      {veredito.boss:<20} "
                f"anuncio={'SIM' if veredito.casou_anuncio else 'NAO'}  "
                f"nome={'SIM' if veredito.casou_nome else 'NAO'}"
            )
        for pista in escala.pistas:
            print(f"      {pista.como_linha()}")


def imprimir_resumo(varredura: Varredura) -> None:
    print("")
    print("RESUMO")
    passadas = sum(len(i.escalas) for i in varredura.imagens)
    print(f"  imagens varridas ............ {len(varredura.imagens)}")
    print(f"  passadas de OCR ............. {passadas}")
    print(f"  passadas sem texto nenhum ... {varredura.leituras_vazias}")
    print(f"  casamentos de ANUNCIO ....... {varredura.casamentos_de_anuncio}")
    print(f"  casamentos de NOME .......... {varredura.casamentos_de_nome}")
    print("")
    print("  POR BOSS (anuncio / nome):")
    for nome, (anuncios, nomes) in varredura.por_boss().items():
        print(f"    {nome:<20} {anuncios:>6} / {nomes:>6}")

    if varredura.casamentos_de_anuncio == 0:
        print("")
        print(
            "  ZERO casamentos de anuncio. Sobre chat REAL de jogadores isso e"
        )
        print(
            "  o resultado desejado: e a medicao do sentido NEGATIVO de "
            "RECO-01."
        )
        print(
            "  Sobre uma imagem que CONTEM o anuncio, e o resultado UTIL: o "
            "texto"
        )
        print("  cru acima diz qual caractere o OCR perdeu.")
    if varredura.leituras_vazias:
        print("")
        print(
            "  ATENCAO: houve passada sem texto nenhum. Zero casamentos sobre "
            "leitura"
        )
        print(
            "  vazia nao mede o padrao — mede que o recorte esta no lugar "
            "errado."
        )


# ---------------------------------------------------------------------------
# A varredura
# ---------------------------------------------------------------------------


def varrer(arquivos, regiao: Regiao, bosses, motor: MotorDeOcr, silencioso=False):
    """Le, julga e imprime cada imagem.

    UMA imagem que nao cabe no recorte e PULADA COM O MOTIVO NOMEADO, e nao
    derruba a varredura. A distincao foi medida contra o `recordings/` real:
    ele mistura frames de janela inteira (1720x1392) com recortes de party
    window (172x522) de outro recurso, e abortar no primeiro recorte que nao
    coubesse jogaria fora dois mil frames bons por causa de um arquivo que nem
    era chat.

    O que continua FECHADO e o que importa: nenhuma imagem e recortada
    truncada (`recortar` devolve `None` em vez de meia linha de chat), e uma
    varredura em que NENHUMA imagem coube devolve `None` para virar codigo 1.
    Zero casamentos por zero leituras nao pode ser confundido com zero
    casamentos por ausencia de boss (T-04-02).
    """
    leituras = []
    fora_do_recorte = []
    for arquivo in arquivos:
        imagem = cv2.imread(str(arquivo), cv2.IMREAD_COLOR)
        if imagem is None:
            print(f"  {_nome_curto(arquivo)}: nao consegui abrir a imagem")
            continue
        recorte = recortar(imagem, regiao)
        if recorte is None:
            altura, largura = imagem.shape[:2]
            fora_do_recorte.append(arquivo)
            print(
                f"  {_nome_curto(arquivo)}: PULADA — tem {largura}x{altura} e "
                f"o recorte pedido (esquerda={regiao.esquerda} "
                f"topo={regiao.topo} largura={regiao.largura} "
                f"altura={regiao.altura}) nao cabe"
            )
            continue

        escalas = []
        for nome_da_escala, ler in motor.escalas:
            try:
                texto = ler(recorte)
            except Exception as erro:  # o motor nunca pode derrubar a medicao
                print(f"    [{nome_da_escala}] o motor levantou: {erro}")
                texto = None
            vereditos = julgar(texto, bosses)
            pistas = tuple(
                pista
                for veredito in vereditos
                if not veredito.casou_anuncio and not veredito.casou_nome
                for pista in [pista_do_boss(texto, veredito.boss)]
                if pista is not None
            )
            escalas.append(
                LeituraDeEscala(
                    escala=nome_da_escala,
                    texto=texto,
                    vereditos=vereditos,
                    pistas=pistas,
                )
            )

        leitura = LeituraDeImagem(arquivo=arquivo, escalas=tuple(escalas))
        leituras.append(leitura)
        if not silencioso:
            imprimir_leitura(leitura, _nome_curto(arquivo))

    if fora_do_recorte and not leituras:
        print("")
        print(
            f"Nenhuma das {len(fora_do_recorte)} imagens cabe no recorte "
            "pedido, entao nao medi nada."
        )
        print(
            "  Passe --recorte ESQUERDA TOPO LARGURA ALTURA em pixels da "
            "propria imagem."
        )
        return None
    if fora_do_recorte:
        print("")
        print(
            f"  ({len(fora_do_recorte)} imagem(ns) pulada(s) por nao caberem "
            "no recorte — os nomes estao acima.)"
        )
    return Varredura(imagens=tuple(leituras))


def _nome_curto(arquivo: Path) -> str:
    """`pasta/frame_000000.png` — a pasta importa numa varredura de varias."""
    return f"{arquivo.parent.name}/{arquivo.name}"


# ---------------------------------------------------------------------------
# A linha de comando
# ---------------------------------------------------------------------------


def main(argv=None, motor: "MotorDeOcr | None" = None) -> int:
    global ULTIMA_VARREDURA

    analisador = argparse.ArgumentParser(
        description=(
            "Mostra o que o OCR leu na regiao do chat (ou do alvo) e o que o "
            "padrao de cada [[boss]] decidiu sobre aquele texto."
        ),
        epilog=(
            "Codigo 0 quando a varredura completou, mesmo sem casamento "
            "nenhum. Codigo 1 so quando nao deu para medir."
        ),
    )
    analisador.add_argument(
        "alvo",
        help=(
            "um PNG, uma pasta de gravacao com frame_*.png, ou a pasta que "
            "contem as gravacoes"
        ),
    )
    analisador.add_argument(
        "--regiao",
        choices=("chat", "alvo"),
        default="chat",
        help="qual regiao calibrada usar (padrao: chat)",
    )
    analisador.add_argument("--config", default=str(RAIZ / "config.toml"))
    analisador.add_argument(
        "--calibracao", default=str(RAIZ / "calibration.json")
    )
    analisador.add_argument(
        "--recorte",
        nargs=4,
        type=int,
        metavar=("ESQUERDA", "TOPO", "LARGURA", "ALTURA"),
        help=(
            "o retangulo, em pixels da propria imagem. Use quando o arquivo e "
            "um print da tela inteira, ou quando a calibracao nao tem a regiao"
        ),
    )
    opcoes = analisador.parse_args(argv)

    motor = motor or motor_do_windows()

    print("CONFERENCIA DO ANUNCIO DE BOSS")

    # A PRIMEIRA RECUSA E O MOTOR (T-04-02). Antes de qualquer outra coisa,
    # porque uma varredura sem motor produziria zero casamentos por AUSENCIA de
    # leitura, e zero casamentos e exatamente o resultado que alguem usaria
    # para afrouxar um padrao que estava certo.
    if not motor.disponivel():
        print("")
        print("Nao da para ler texto nesta maquina, entao nao ha o que medir.")
        print(f"  {motor.motivo()}")
        return 1

    caminho = Path(opcoes.alvo)
    arquivos = imagens_de(caminho)
    if not arquivos:
        print("")
        print(f"Nenhuma imagem em {caminho}.")
        print(
            "  Procurei, nesta ordem: " + ", ".join(PADROES_DE_BUSCA) + "."
        )
        return 1

    if opcoes.recorte:
        esquerda, topo, largura, altura = opcoes.recorte
        regiao = Regiao(
            esquerda=esquerda, topo=topo, largura=largura, altura=altura
        )
        origem_do_retangulo = "--recorte explicito"
    else:
        regiao, explicacao = regiao_da_calibracao(
            Path(opcoes.calibracao), opcoes.regiao
        )
        if regiao is None:
            print("")
            print("Nao sei onde olhar nesta imagem, entao nao vou medir nada.")
            print(f"  {explicacao}")
            print(
                "  Passe --recorte ESQUERDA TOPO LARGURA ALTURA em pixels da "
                "propria imagem."
            )
            return 1
        origem_do_retangulo = explicacao

    bosses = ler_bosses(Path(opcoes.config))
    if not bosses:
        print("")
        print(
            f"Nenhum bloco [[boss]] em {opcoes.config}, entao nao ha veredito "
            "para dar."
        )
        return 1

    print(f"  imagens .......... {len(arquivos)} a partir de {caminho}")
    print(
        f"  regiao ........... {opcoes.regiao}  ->  "
        f"esquerda={regiao.esquerda} topo={regiao.topo} "
        f"largura={regiao.largura} altura={regiao.altura}  "
        f"({origem_do_retangulo})"
    )
    print(
        "  bosses ........... "
        + ", ".join(b.nome for b in bosses)
        + f"  ({opcoes.config})"
    )
    print(
        "  escalas .......... "
        + ", ".join(nome for nome, _ in motor.escalas)
    )
    print("")

    varredura = varrer(arquivos, regiao, bosses, motor)
    ULTIMA_VARREDURA = varredura
    if varredura is None:
        return 1

    imprimir_resumo(varredura)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
