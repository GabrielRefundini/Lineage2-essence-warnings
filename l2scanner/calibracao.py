"""Calibracao: onde ficam as coisas na tela e que cores contam como barra cheia.

Separada da configuracao escrita a mao de proposito. A calibracao e gerada por
ferramenta e sobrescrita a cada recalibragem; a configuracao e escrita pelo
usuario. Se morassem no mesmo arquivo, a ferramenta apagaria os ajustes manuais
na primeira vez que rodasse.

A calibracao guarda a geometria de tela sob a qual foi feita. Se a resolucao ou
o arranjo de monitores mudar, os retangulos gravados nao significam mais a mesma
coisa — e o scanner se recusa a iniciar em vez de medir a regiao errada calado.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .frames import Regiao
from .identidade import Assinatura

VERSAO_DO_ESQUEMA = 2

# Faixa padrao onde procurar o banner de manutencao, derivada da party window.
#
# O banner do jogo aparece POR CIMA da party window, na faixa superior
# esquerda, e e MUITO mais largo que as barras (o texto tem umas 60 colunas
# contra os 120 px das barras).
#
# ESTES NUMEROS DEIXARAM DE SER PALPITE (D-f). Agora existe a conta, feita
# contra a calibracao REAL do usuario (`party_window_na_janela` topo=222,
# medida em 2026-08-24) e contra a estimativa do banner no screenshot dele:
#
#     numeros antigos (60/140) -> faixa em y 162..302 na janela
#     banner estimado          -> y ~168..253
#     folga no topo            -> ~6 px
#
# SEIS PIXELS DE FOLGA CONTRA UMA ESTIMATIVA QUE TEM INCERTEZA. Errar por 6 px
# corta o titulo `Server Maintence`, que e literalmente o que
# `eh_banner_de_manutencao` procura — e o recurso inteiro cala, sem sintoma
# nenhum alem do silencio.
#
#     numeros novos (130/240)  -> faixa em y 92..332
#     folga                    -> ~76 px em cima, ~79 px embaixo
#
# A MEDICAO QUE AUTORIZA A FOLGA: area extra NAO piora a precisao. Na fixture
# real, a imagem INTEIRA em cinza tambem leu 0:40:26 — o motor nao se perde por
# receber vizinhanca.
#
# O CUSTO DA FAIXA MAIOR FOI MEDIDO, e nao extrapolado: na banda de 732x240 ja
# aquecida, a passada de deteccao (cinza 2x) custa 23 ms e a de conferencia
# (3x) custa 31 ms. A cada 5 s isso e ~0,5% de um nucleo. A folga vertical sai
# de graca.
#
# O PRECO NOVO QUE A FOLGA CRIA, real e aceito: mais area significa mais texto
# vizinho dentro da faixa, e a guarda estrutural de `interpretar_banner` (D-b)
# prefere calar a arriscar. Se um texto vizinho trouxer uma forma que pareca
# unidade de minutos sem numero, a leitura se perde. Perder uma leitura custa 5
# segundos; cortar o titulo custa o recurso inteiro.
#
# Generoso e melhor que justo aqui: veja `Calibracao.regiao_do_banner`.
MARGEM_ESQUERDA_DO_BANNER = 40
MARGEM_ACIMA_DO_BANNER = 130
LARGURA_EXTRA_DO_BANNER = 560
ALTURA_DA_FAIXA_DO_BANNER = 240


class CalibracaoInvalida(Exception):
    """A calibracao nao existe, esta corrompida ou nao vale para esta tela."""


@dataclass(frozen=True)
class LimiaresDeCor:
    """Que pixels contam como preenchimento de uma barra.

    A SATURACAO e o discriminador principal, nao o matiz. Motivo medido na tela
    real: a parte vazia da barra e transparente e mostra o terreno do jogo
    (S~75), enquanto a barra cheia e solida (S~210). O terreno muda de cor entre
    zonas, mas nunca fica saturado como a barra.

    Para o vermelho, `matiz_min` > `matiz_max` sinaliza a volta no circulo de
    matiz: a faixa vale de matiz_min ate 179 E de 0 ate matiz_max.
    """

    matiz_min: int
    matiz_max: int
    saturacao_min: int
    valor_min: int


@dataclass(frozen=True)
class LayoutDaParty:
    """Geometria das linhas de membro, tudo RELATIVO a party_window.

    As linhas sao uniformes e igualmente espacadas, entao um passo unico
    descreve todas — nao e preciso listar retangulo por retangulo.
    """

    # Icone de classe — o indicador de presenca da linha
    icone_x: int
    icone_y: int  # do primeiro membro
    icone_tamanho: int

    # Barras (HP e MP compartilham x, largura e altura)
    barra_x: int
    barra_largura: int
    barra_altura: int
    hp_y: int  # do primeiro membro
    mp_y: int  # do primeiro membro

    passo: int  # distancia vertical entre membros consecutivos
    max_linhas: int

    # Recorte do NOME, relativo ao icone da mesma linha. Fica logo acima dele.
    # O recorte precisa ser JUSTO: medido na tela real, um recorte largo deixa
    # o terreno dominar a comparacao e a margem entre nomes cai de 0.55 para
    # 0.04 — a diferenca entre funcionar e nao funcionar.
    nome_dx: int = 26  # a partir do icone, pulando o emblema de classe
    nome_dy: int = -24
    nome_largura: int = 100
    nome_altura: int = 20

    # Limiares de contraste para "tem icone aqui".
    # Medidos na tela real: linha com membro da desvio 43-52 e 46-52% de pixels
    # escuros; linha vazia da desvio 9-10 e 0% escuros. O corte fica no meio da
    # margem, bem longe dos dois lados.
    icone_desvio_min: float = 25.0
    icone_escuros_min: float = 0.15

    # A ancora da janela e mais fraca que o icone (moldura fina), entao seu
    # corte e mais baixo. Medido: canto da moldura da desvio 35, terreno da 8-12.
    ancora_desvio_min: float = 20.0
    ancora_escuros_min: float = 0.02

    # Brilho maximo da borda vertical da barra para ela contar como intacta.
    # A UI desenha uma linha escura nas duas pontas de cada barra, e ela existe
    # igual com a barra cheia ou vazia — e chrome, nao preenchimento. Some
    # apenas quando outra janela do jogo cobre a party window.
    # Medido na tela real: barra livre da V~8-11 (cheia OU vazia, identico),
    # coberta pelo inventario da V~72-112. O corte fica no meio dessa margem.
    borda_v_max: float = 40.0


@dataclass
class Calibracao:
    """Onde ficam as coisas na tela deste usuario."""

    # A janela inteira da party — e o que o scanner captura a cada tick
    party_window: Regiao

    # Ancora de visibilidade da UI, RELATIVA a party_window.
    # Fica no TOPO porque a janela e ancorada em cima e encolhe por baixo
    # conforme a PT diminui; uma ancora embaixo sumiria sozinha com menos gente.
    ancora: Regiao

    layout: LayoutDaParty
    limiares_hp: LimiaresDeCor
    limiares_mp: LimiaresDeCor

    # Geometria da tela quando isto foi calibrado, para detectar mudanca
    geometria_da_tela: str

    # Barra de HP do proprio personagem. Fica no TOPO da janela do jogo, longe
    # da party window — o usuario nao aparece na propria party window, entao
    # sem isto a morte DELE nunca seria detectada. E justamente quem tem mais
    # chance de morrer AFK, porque e o unico sem outra pessoa olhando.
    #
    # Guardada em coordenadas RELATIVAS a janela do jogo, como a party window.
    hp_proprio: Regiao | None = None

    # Nome do proprio personagem, para o alerta dizer quem morreu.
    nome_proprio: str | None = None

    # Nomes dos membros, em ordem de linha. Fonte da verdade para identidade —
    # nunca leitura de texto da tela, que erraria um glifo e inventaria um
    # membro fantasma entrando e saindo da party.
    nomes: list[str] = field(default_factory=list)

    # Assinaturas visuais dos nomes, gravadas na calibracao. Sao elas que
    # permitem dizer QUEM morreu mesmo quando a ordem da party muda — sem elas
    # a identidade viria da posicao da linha, e um alerta com o nome errado
    # manda a party socorrer a pessoa errada.
    assinaturas: list = field(default_factory=list)

    # Titulo da janela do jogo a que esta party window pertence. Descoberto
    # pela calibracao. Com duas instancias abertas, adivinhar daria errado — e
    # errar aqui significa vigiar a party do personagem errado.
    janela: str | None = None

    # A MESMA party window, mas em coordenadas relativas ao canto da janela do
    # jogo. `party_window` esta em coordenadas de desktop, que so valem
    # enquanto a janela nao se mexer; esta aqui sobrevive a arrastar o jogo
    # para outro lugar da tela, porque acompanha a janela.
    party_window_na_janela: Regiao | None = None

    # Onde o banner de manutencao aparece, se o usuario quiser dizer.
    #
    # OPCIONAL de proposito, e por isso a VERSAO_DO_ESQUEMA SEGUE EM 2: o
    # `carregar` recusa qualquer versao diferente da constante, entao subir para
    # 3 invalidaria o `calibration.json` que o usuario mediu a mao e o obrigaria
    # a recalibrar tudo por causa de um campo opcional.
    #
    # A regiao padrao (`regiao_do_banner`) e um palpite educado sobre onde o
    # banner cai, e `python -m l2scanner --testar-manutencao` e como o usuario
    # descobre se o palpite acertou. Errando, ele corrige AQUI — sem tocar em
    # codigo.
    #
    # REFERENCIAL: como `hp_proprio`, esta regiao vale para o caminho
    # `--janela` (coordenadas relativas ao canto da janela do jogo). Quem
    # configurar a mao para o caminho `mss` precisa escrever coordenadas de
    # DESKTOP. O `--testar-manutencao` imprime a regiao justamente para essa
    # conferencia.
    banner_manutencao: Regiao | None = None

    # --- Mercado (World Exchange / "XM Market") ---
    #
    # OPCIONAIS de proposito, e por isso a VERSAO_DO_ESQUEMA SEGUE EM 2, pelo
    # mesmo motivo escrito acima para o `banner_manutencao`: o `carregar` recusa
    # qualquer versao diferente da constante, entao subir para 3 invalidaria o
    # `calibration.json` que o usuario mediu a mao e o obrigaria a recalibrar
    # tudo por causa de campos que ele talvez nem use. Uma instalacao sem
    # calibracao de mercado carrega igual e a feature simplesmente fica OFF.
    #
    # Onde fica a faixa de titulo do painel, em coordenadas da JANELA do jogo.
    #
    # ATENCAO, medido em `recordings/inv3/`: o painel ANDA. Entre dois frames da
    # mesma gravacao ele apareceu 181 px a esquerda e 143 px abaixo, com a mesma
    # arte casando 0.9996. Este retangulo e a posicao de REFERENCIA de onde o
    # molde foi cortado — nao a promessa de que o painel estara sempre ali. Quem
    # consome precisa localizar antes de comparar (ver `mercado_visao`).
    mercado_ancora: Regiao | None = None

    # O molde da ancora empacotado: {"altura", "largura", "bytes" em hex}.
    #
    # Guardado como dict CRU, sem decodificar. Decodificar aqui obrigaria
    # `calibracao.py` a importar numpy so para carregar um arquivo de
    # configuracao. Quem decodifica e `mercado_visao.molde_de_hex`, que ja
    # confere as dimensoes declaradas contra o tamanho real dos bytes.
    mercado_molde_da_ancora: dict | None = None

    # O limiar de casamento desta instalacao. A calibracao do usuario e a
    # autoridade sobre a tela dele; `mercado_visao.CASAMENTO_MINIMO_DA_ANCORA`
    # e so o padrao medido para quem ainda nao calibrou.
    mercado_limiar_da_ancora: float | None = None

    # Carimbo de contexto da captura: as dimensoes da janela no momento em que o
    # molde foi cortado. Com a janela em outro tamanho, o molde foi cortado numa
    # escala diferente e o casamento cai sem explicacao. Isto existe para o
    # arranque RECUSAR a leitura de mercado com "recalibre", em vez de ler
    # degradado calado.
    mercado_geometria_da_captura: dict | None = None

    versao: int = VERSAO_DO_ESQUEMA

    def regiao_do_nome(self, indice: int) -> Regiao:
        """Onde fica o texto do nome da linha `indice`, dentro da party window."""
        lay = self.layout
        deslocamento = indice * lay.passo
        return Regiao(
            esquerda=lay.icone_x + lay.nome_dx,
            topo=lay.icone_y + deslocamento + lay.nome_dy,
            largura=lay.nome_largura,
            altura=lay.nome_altura,
        )

    @property
    def nomes_com_assinatura(self) -> set[str]:
        """Quem tem impressao digital visual gravada."""
        return {a.nome for a in self.assinaturas}

    def nome_da_linha(self, indice: int) -> str:
        """Rotulo de uma linha que NAO foi reconhecida.

        Um nome que tem assinatura gravada nunca pode ser usado aqui. A
        assinatura e a autoridade sobre onde aquela pessoa esta: se ela nao
        casou nesta linha, esta linha nao e dela.

        Sem esta regra o rotulo por posicao mente exatamente como o alerta
        mentia. Visto ao vivo: Korzis reconhecido na linha 0, linha 1 sem
        reconhecimento e com HP 0% — e `nomes[1]` era "Korzis". O scanner
        estava a um debounce de anunciar "Korzis morreu" com o Korzis vivo a
        57% na linha de cima.

        Sem assinatura NENHUMA, o nome por posicao volta a valer: e o modo
        antigo, e ali ele e o melhor palpite disponivel.
        """
        if 0 <= indice < len(self.nomes):
            nome = self.nomes[indice]
            if nome not in self.nomes_com_assinatura:
                return nome
        return f"Membro {indice + 1}"

    def regiao_do_banner(self, na_janela: bool) -> Regiao | None:
        """Onde procurar o banner de manutencao. None = o recurso nao liga.

        Tres respostas, nesta ordem:

        1. A regiao CALIBRADA, quando o usuario configurou uma. Ela vence
           sempre — foi ele que olhou o PNG do `--testar-manutencao` e viu onde
           o banner cai de verdade.
        2. Uma faixa derivada da party window, no caminho `--janela`. O banner
           aparece POR CIMA da party window e e mais largo que as barras.
        3. None, no caminho `mss` sem configuracao (D-07). Ali nao existe
           janela de referencia, entao qualquer padrao seria um palpite sobre
           coordenadas de desktop — e inventar deteccao onde nao ha pixels e
           pior do que nao ligar o recurso.

        A faixa derivada e GENEROSA de proposito, e nao justa. Texto vizinho
        que caia dentro dela e so ruido: `eh_banner_de_manutencao` exige a raiz
        `mainten`, que nada mais na tela produz. Uma faixa apertada, ao
        contrario, erra por pouco e nao le NADA — e o modo de falha caro e
        esse.
        """
        if self.banner_manutencao is not None:
            return self.banner_manutencao
        if not na_janela or self.party_window_na_janela is None:
            return None

        party = self.party_window_na_janela
        return Regiao(
            esquerda=max(0, party.esquerda - MARGEM_ESQUERDA_DO_BANNER),
            topo=max(0, party.topo - MARGEM_ACIMA_DO_BANNER),
            largura=party.largura + LARGURA_EXTRA_DO_BANNER,
            altura=ALTURA_DA_FAIXA_DO_BANNER,
        )

    def salvar(self, caminho: Path) -> None:
        dados = {
            "versao": self.versao,
            "geometria_da_tela": self.geometria_da_tela,
            "party_window": self.party_window.como_dict(),
            "ancora": self.ancora.como_dict(),
            "layout": asdict(self.layout),
            "limiares_hp": asdict(self.limiares_hp),
            "limiares_mp": asdict(self.limiares_mp),
            "hp_proprio": self.hp_proprio.como_dict() if self.hp_proprio else None,
            "nome_proprio": self.nome_proprio,
            "nomes": self.nomes,
            "assinaturas": [a.como_dict() for a in self.assinaturas],
            "janela": self.janela,
            "party_window_na_janela": (
                self.party_window_na_janela.como_dict()
                if self.party_window_na_janela
                else None
            ),
            "banner_manutencao": (
                self.banner_manutencao.como_dict() if self.banner_manutencao else None
            ),
            # Serializacao condicional, trilho do `banner_manutencao`: um campo
            # nao preenchido vira `null` e o `.get` do `carregar` o devolve como
            # None, sem migracao.
            "mercado_ancora": (
                self.mercado_ancora.como_dict() if self.mercado_ancora else None
            ),
            "mercado_molde_da_ancora": self.mercado_molde_da_ancora,
            "mercado_limiar_da_ancora": self.mercado_limiar_da_ancora,
            "mercado_geometria_da_captura": self.mercado_geometria_da_captura,
        }
        caminho.write_text(
            json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @classmethod
    def carregar(cls, caminho: Path) -> "Calibracao":
        if not caminho.exists():
            raise CalibracaoInvalida(
                f"Nao encontrei {caminho}.\n"
                f"Rode a calibracao:  python -m l2scanner.calibrar"
            )

        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except json.JSONDecodeError as erro:
            raise CalibracaoInvalida(f"{caminho} esta corrompido: {erro}") from erro

        versao = dados.get("versao")
        if versao != VERSAO_DO_ESQUEMA:
            raise CalibracaoInvalida(
                f"{caminho} foi gravado no formato v{versao}, "
                f"mas este scanner espera v{VERSAO_DO_ESQUEMA}. Recalibre."
            )

        _conferir_as_chaves_de_mercado(dados)

        return cls(
            party_window=Regiao.de_dict(dados["party_window"]),
            ancora=Regiao.de_dict(dados["ancora"]),
            layout=LayoutDaParty(**dados["layout"]),
            limiares_hp=LimiaresDeCor(**dados["limiares_hp"]),
            limiares_mp=LimiaresDeCor(**dados["limiares_mp"]),
            geometria_da_tela=dados["geometria_da_tela"],
            hp_proprio=(
                Regiao.de_dict(dados["hp_proprio"]) if dados.get("hp_proprio") else None
            ),
            nome_proprio=dados.get("nome_proprio"),
            nomes=list(dados.get("nomes", [])),
            assinaturas=[
                Assinatura.de_dict(a) for a in dados.get("assinaturas", [])
            ],
            janela=dados.get("janela"),
            party_window_na_janela=(
                Regiao.de_dict(dados["party_window_na_janela"])
                if dados.get("party_window_na_janela")
                else None
            ),
            # `.get`, exatamente como `hp_proprio`: e o que faz um
            # calibration.json v2 gravado antes desta funcionalidade carregar
            # sem uma linha de migracao.
            banner_manutencao=(
                Regiao.de_dict(dados["banner_manutencao"])
                if dados.get("banner_manutencao")
                else None
            ),
            # As quatro de mercado seguem o MESMO `.get`: e o que faz um
            # calibration.json v2 gravado antes desta funcionalidade carregar
            # sem uma linha de migracao.
            mercado_ancora=(
                Regiao.de_dict(dados["mercado_ancora"])
                if dados.get("mercado_ancora")
                else None
            ),
            mercado_molde_da_ancora=dados.get("mercado_molde_da_ancora"),
            mercado_limiar_da_ancora=dados.get("mercado_limiar_da_ancora"),
            mercado_geometria_da_captura=dados.get("mercado_geometria_da_captura"),
            versao=versao,
        )

    def conferir_geometria(self, atual: str) -> None:
        """Recusa se a tela mudou desde a calibracao (CAPT-07).

        Falhar alto aqui e muito melhor do que medir a regiao errada calado.
        """
        if self.geometria_da_tela != atual:
            raise CalibracaoInvalida(
                "A configuracao de tela mudou desde a calibracao.\n"
                f"  calibrado sob: {self.geometria_da_tela}\n"
                f"  agora:         {atual}\n"
                "As coordenadas gravadas nao valem mais. Recalibre."
            )


def _conferir_as_chaves_de_mercado(dados: dict) -> None:
    """As chaves de mercado sao ENTRADA NAO CONFIAVEL. Confere tipo e faixa.

    Mora AQUI, ao lado do portao de versao, e nao no consumidor, porque e no
    arranque que a mensagem ainda pode dizer "recalibre" com o usuario olhando
    para o console. O consumidor roda as duas da manha, no meio do farm.

    As tres chaves saiam de `dados.get(...)` direto para dentro da `Calibracao`
    sem uma checagem. `molde_de_hex` ja tratava o dict como entrada nao
    confiavel e a versao ja tinha portao; o LIMIAR nao tinha nada, e e o mais
    perigoso dos tres:

    - `mercado_limiar_da_ancora: 0` ou `-1` faz `mercado_aberto` devolver True
      para TODO recorte. O detector deixa de detectar e passa a AFIRMAR — o
      fail-open exato que o charter do `mercado_visao` existe para impedir.
    - `mercado_limiar_da_ancora: "0.73"` (numero entre aspas, o deslize de
      edicao mais comum) viraria `TypeError: '>=' not supported between
      'float' and 'str'` dentro de `mercado_aberto`, no meio do farm.
    - `mercado_molde_da_ancora: [1, 2, 3]` viraria `TypeError: list indices
      must be integers` dentro de `molde_de_hex`.

    `None` sempre passa: e o estado legitimo de "nao calibrei o mercado", e uma
    instalacao sem calibracao de mercado precisa continuar subindo igual.
    """
    limiar = dados.get("mercado_limiar_da_ancora")
    if limiar is not None:
        # `bool` e subclasse de `int`: `True` passaria como numero e viraria
        # limiar 1.0 calado.
        if isinstance(limiar, bool) or not isinstance(limiar, (int, float)):
            raise CalibracaoInvalida(
                f"mercado_limiar_da_ancora precisa ser um numero, veio "
                f"{type(limiar).__name__} ({limiar!r}). Recalibre o mercado."
            )
        if not 0.0 < limiar <= 1.0:
            raise CalibracaoInvalida(
                f"mercado_limiar_da_ancora={limiar} esta fora de (0, 1]. Um "
                f"limiar <= 0 faz TODO recorte virar 'mercado aberto'. O "
                f"padrao medido e 0.73. Recalibre o mercado."
            )

    molde = dados.get("mercado_molde_da_ancora")
    if molde is not None and not isinstance(molde, dict):
        raise CalibracaoInvalida(
            f"mercado_molde_da_ancora precisa ser um objeto com altura, "
            f"largura e bytes, veio {type(molde).__name__}. Recalibre o "
            f"mercado."
        )

    geometria = dados.get("mercado_geometria_da_captura")
    if geometria is not None and not isinstance(geometria, dict):
        raise CalibracaoInvalida(
            f"mercado_geometria_da_captura precisa ser um objeto, veio "
            f"{type(geometria).__name__}. Recalibre o mercado."
        )

    ancora = dados.get("mercado_ancora")
    if isinstance(ancora, dict):
        # `Regiao.de_dict` aceita largura/altura <= 0, e faz bem em nao
        # reclamar de `esquerda`/`topo` negativos (monitor a esquerda do
        # principal). Mas uma ancora de area zero ou negativa nao recorta nada
        # — e este retangulo e a forma esperada contra a qual o molde e
        # conferido (`mercado_visao.molde_de_hex`, argumento `forma_esperada`).
        try:
            largura, altura = int(ancora["largura"]), int(ancora["altura"])
        except (KeyError, TypeError, ValueError) as erro:
            raise CalibracaoInvalida(
                f"mercado_ancora nao tem largura/altura inteiras utilizaveis "
                f"({erro}). Recalibre o mercado."
            ) from erro
        if largura <= 0 or altura <= 0:
            raise CalibracaoInvalida(
                f"mercado_ancora tem dimensao nao-positiva "
                f"({largura}x{altura}). Recalibre o mercado."
            )


def descrever_geometria_da_tela() -> str:
    """Assinatura estavel do arranjo de monitores."""
    import mss

    with mss.mss() as sct:
        partes = [
            f"{m['width']}x{m['height']}+{m['left']}+{m['top']}"
            for m in sct.monitors[1:]
        ]
    return ";".join(partes)


# Valores medidos na tela real do usuario em 2026-08-24, cliente XM Essence,
# janela do Yazalaque em (1713,0) num monitor de 3440x1440. Servem de ponto de
# partida; a ferramenta de calibracao regrava tudo isto.
LIMIARES_HP_PADRAO = LimiaresDeCor(
    matiz_min=168,  # > matiz_max: volta no circulo, duas faixas combinadas
    matiz_max=12,
    saturacao_min=120,  # barra cheia da ~210, terreno da ~75
    valor_min=60,
)

LIMIARES_MP_PADRAO = LimiaresDeCor(
    matiz_min=95,
    matiz_max=130,
    saturacao_min=120,  # barra cheia da ~195
    valor_min=60,
)
