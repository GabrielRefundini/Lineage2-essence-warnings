"""Aprender sozinho a assinatura de quem o scanner nunca viu.

POR QUE ESTE MODULO CONTA LEITURAS E NAO SEGUNDOS

O tick nao e garantido. A captura mira ~1 Hz, mas um frame doente, uma cegueira
ou uma varredura de mercado mudam o intervalo real, e "N segundos" viraria uma
dependencia de RELOGIO dentro da unica logica nova desta fase. Contando
leituras, um `--replay` de uma sessao gravada produz o MESMO acervo que a sessao
ao vivo produziu, que e a propriedade que torna esta fase depuravel sem morrer
no jogo de novo.

Este modulo nao tem relogio nenhum — nem `datetime.now()`, nem `time.time()` — e
a proibicao esta presa pelo portao AST de `tests/test_presenca.py`, ao lado de
`agenda`, `loot`, `presenca`, `bosses`, `respawn` e `acervo`.

POR QUE A ESTABILIDADE E JULGADA SOBRE A MASCARA E NUNCA SOBRE OS PIXELS CRUS

O texto do nome e opaco e o painel da party window e SEMITRANSPARENTE. O cenario
que anda por tras muda os pixels crus a cada frame e nao muda a mascara —
`identidade.mascara_de_texto` e so um piso de brilho (`V > 180`). Julgar por
pixel cru seria julgar o CENARIO: num campo aberto de dia o candidato nunca
seria estavel, e a feature simplesmente nao aconteceria, sem erro em lugar
nenhum e sem uma linha de log dizendo por que.

POR QUE A GRAVACAO PREFERE NAO ACONTECER QUANDO HA DUVIDA

O acervo e IRREVERSIVEL no v1: nao ha comando de esquecer (decisao da Fase 1 —
o usuario viu os 562 bytes por assinatura e dispensou a limpeza). Uma pessoa nao
aprendida custa um "Membro N" no console; uma entrada de lixo gravada fica para
sempre, conta na linha de arranque, e ainda pode SOMBRAR gente de verdade pela
margem — e uma pessoa sombreada para de ser reconhecida em silencio.

O QUE ESTE MODULO NAO CONHECE

Ele nao importa `visao`, `sessao`, `rastreador` nem `calibracao`. Fala
`Assinatura` e `AcervoDeIdentidades`, e so — o mesmo isolamento que o `acervo`
conquistou. Quem sabe o que e uma linha da party window e o `sessao`, e e la que
a candidatura por `COM_MEMBRO` e por `ui_visivel` mora (D-01).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from .acervo import AcervoDeIdentidades, chave_da_assinatura
from .identidade import LIMIAR_DE_CASAMENTO, PIXELS_MINIMOS_DE_TEXTO, Assinatura

# Quantas leituras seguidas com o recorte estavel bastam para gravar.
#
# O NUMERO E DERIVADO DO QUE O PROJETO JA MEDIU, E NAO ESCOLHIDO NO OLHO.
# `rastreador.Ajustes` tem duas familias de confirmacao, e a docstring dele
# chama isso de histerese assimetrica: as direcoes BARATAS de reverter custam 3
# leituras (`confirmacoes_para_morte`, `confirmacoes_para_entrada`) e as CARAS
# custam 5 (`confirmacoes_para_ressurreicao`, `confirmacoes_para_saida`).
#
# Gravar num acervo irreversivel e a direcao cara POR DEFINICAO — nao existe
# desfazer — entao ela paga o preco da familia cara. A ~1 Hz sao ~5 segundos:
# quem vai ficar horas na party espera cinco segundos, e uma linha que pisca por
# quatro leituras nunca chega a ser gravada.
LEITURAS_PARA_APRENDER = 5


@dataclass(frozen=True)
class AjustesDoAprendiz:
    """Os dois numeros que governam o aprendizado.

    `celulas_toleradas` NASCE ZERO, e o zero e a decisao (D-05). Esta fase nao
    tem medicao de campo do ruido entre frames consecutivos — nao existe
    gravacao multi-frame da party no repositorio, so imagens soltas — e adotar
    uma tolerancia inventada seria adotar exatamente o tipo de constante que
    este projeto proibe. Com zero, "a mesma leitura" quer dizer a mesma chave de
    conteudo, exatamente.

    O numero certo para a maquina do usuario sai do `scanner.log` da primeira
    sessao real: toda recusa por instabilidade registra a DISTANCIA MEDIDA, e o
    comentario do `[identidade]` no `config.toml` diz onde acha-la. E o circuito
    de D-07 — o modo de falha de um default errado e auto-diagnostico, e nao
    silencio.
    """

    leituras_para_aprender: int = LEITURAS_PARA_APRENDER
    celulas_toleradas: int = 0


@dataclass(frozen=True)
class Candidata:
    """Uma linha que o scanner esta vendo e nao sabe de quem e.

    O `indice` viaja SO PARA O DIAGNOSTICO — e o que faz a linha de log de D-07
    poder dizer QUAL linha recusou. Ele NUNCA entra em decisao nenhuma: a party
    window compacta quando alguem sai, e a linha 2 de agora pode ser outra
    pessoa daqui a um tick. O contador de estabilidade e por CONTEUDO (D-08), e
    um contador por indice somaria leituras de pessoas diferentes ate atingir N
    e gravaria uma assinatura de ninguem.
    """

    indice: int
    mascara: np.ndarray
    confianca: float


@dataclass(frozen=True)
class Aprendizado:
    """Uma entrada que ESTE tick fez existir no acervo.

    Estruturado, e nao texto, pelo mesmo motivo que `ResultadoDoTick.despachos`
    e estruturado: o teste afirma estrutura, e a redacao muda toda vez que
    alguem a melhora.

    O CAMPO `confianca` NAO E ENFEITE. Ele e a melhor pontuacao que aquela linha
    teve contra tudo que o scanner ja conhecia no instante em que decidiu
    aprender. Ele existe porque D-02 so guarda UMA das duas fronteiras: veta
    acima do limiar, e nao tem nada a dizer sobre uma pessoa que volta
    correlacionando 0.70 contra a propria entrada ja gravada. Nesse caso ela E
    candidata, uma SEGUNDA entrada da mesma pessoa nasce, e as duas depois se
    sombreiam pela margem.

    Nao ha medida de campo do drift entre sessoes para fechar essa porta agora
    (e por isso que a tolerancia nasce em zero), entao o que esta fase pode fazer
    e o mesmo que D-07 faz pela recusa: gravar o NUMERO junto do fato. Uma
    sequencia de aprendizados com confianca em torno de 0.70 e a assinatura
    desse caso; sem o numero no log ele e invisivel. Um aprendizado sem confianca
    registrada, num acervo irreversivel, tem como unico modo de falha o
    silencio. Ver T-02-18 no plano 02-02.
    """

    chave: str
    indice: int
    desfecho: str
    assinatura: Assinatura
    confianca: float


@dataclass(frozen=True)
class RecusaPorInstabilidade:
    """Uma leitura que NAO continuou a sequencia, com a distancia que mediu.

    Sem este numero, o desfecho de um `celulas_toleradas` errado e a feature
    simplesmente NAO ACONTECER, em silencio, sem nada no log dizendo por que. O
    default e zero porque esta fase nao tem medicao de campo do ruido entre
    frames consecutivos — nao existe gravacao multi-frame da party no
    repositorio, so imagens soltas — e inventar uma tolerancia seria adotar
    exatamente o tipo de constante que este projeto proibe.

    Registrar a distancia MEDIDA troca esse silencio por auto-diagnostico: o
    `scanner.log` da primeira sessao real diz, com numero, o quanto as leituras
    diferem entre si, e o usuario sobe a tolerancia com um numero medido em vez
    de tentar valores. E por isso que isto e requisito de plano, e nao um "nice
    to have": ele substitui uma ferramenta de spike que nao foi escrita.

    `distancia` e `None` quando nao havia nenhum vigia de FORMA IGUAL para
    comparar. Forma diferente nao e "muito diferente": e uma pergunta sem
    sentido, porque as duas mascaras nao descrevem o mesmo retangulo de tela.
    """

    indice: int
    distancia: int | None
    tolerado: int


@dataclass(frozen=True)
class RetratoDasRecusas:
    """A faixa das distancias medidas nesta sessao, para uma linha de log.

    A MEDIANA entra ao lado do minimo e do maximo porque um unico outlier — um
    frame com o inventario passando por cima do nome — esticaria o maximo e
    faria o usuario escolher uma tolerancia grande demais. O par (minimo,
    mediana) e o que descreve o ruido normal.
    """

    recusas: int = 0
    menor: int | None = None
    maior: int | None = None
    mediana: float | None = None


@dataclass(frozen=True)
class ResultadoDoAprendiz:
    """O que uma leitura produziu. As duas listas VAZIAS sao o estado normal."""

    aprendizados: list[Aprendizado] = field(default_factory=list)
    recusas: list[RecusaPorInstabilidade] = field(default_factory=list)


def distancia_de_hamming(a: np.ndarray, b: np.ndarray) -> int | None:
    """Em quantas CELULAS as duas mascaras diferem, ou `None` se nem da.

    A unidade e a celula porque e a unidade em que a unica medida que este
    projeto tem foi feita: 8 e 12 celulas viradas numa mascara de 2000 (Fase 1,
    bloco `BITS_VIRADOS` de `tests/test_acervo.py`). Comparar contra ela e
    comparar contra o perigo real, e nao contra uma fracao inventada.

    FORMA DIFERENTE DEVOLVE `None`, e nao um numero grande. "Muito diferente"
    seria uma resposta errada com cara de certa: duas mascaras de retangulos
    diferentes nao sao duas leituras da mesma coisa, e a distancia entre elas
    nao existe.
    """
    if a.shape != b.shape:
        return None
    return int(np.count_nonzero(a != b))


@dataclass
class _Vigia:
    """Uma sequencia de leituras em andamento, chaveada pelo CONTEUDO.

    A `ancora` e a PRIMEIRA mascara da sequencia e nunca e atualizada. Ver
    `Aprendiz.observar` para a razao inteira.
    """

    ancora: np.ndarray
    leituras: int
    indice: int


class Aprendiz:
    """Grava sozinho a assinatura de quem ficou parado tempo suficiente.

    Recebe `Candidata`s — linhas que o `sessao` ja julgou candidatas por D-01 —
    e devolve o que aconteceu. Nao sabe o que e uma linha, um frame ou um tick.
    """

    def __init__(
        self,
        acervo: AcervoDeIdentidades,
        ajustes: AjustesDoAprendiz | None = None,
    ) -> None:
        self._acervo = acervo
        self._ajustes = ajustes or AjustesDoAprendiz()
        self._vigias: list[_Vigia] = []
        self._distancias: list[int] = []
        self._recusas = 0

    @property
    def ajustes(self) -> AjustesDoAprendiz:
        return self._ajustes

    def retrato(self) -> RetratoDasRecusas:
        """O acumulado da sessao, ignorando as distancias que nao existem."""
        if not self._distancias:
            return RetratoDasRecusas(recusas=self._recusas)
        ordenadas = sorted(self._distancias)
        meio = len(ordenadas) // 2
        mediana = (
            float(ordenadas[meio])
            if len(ordenadas) % 2
            else (ordenadas[meio - 1] + ordenadas[meio]) / 2
        )
        return RetratoDasRecusas(
            recusas=self._recusas,
            menor=ordenadas[0],
            maior=ordenadas[-1],
            mediana=mediana,
        )

    def observar(self, candidatas: Sequence[Candidata]) -> ResultadoDoAprendiz:
        """Uma leitura. Devolve o que gravou e o que recusou.

        A ORDEM DOS PORTOES E A REGRA, e cada um tem uma razao propria.

        1. RECORTE QUASE SEM TEXTO E DESCARTADO. O motivo nao e obvio:
           `identificar_linhas` devolve `Casamento(None, 0.0)` para uma linha sem
           texto suficiente, e `0.0` passa folgado na condicao de D-02. Pior,
           com a lista de assinaturas VAZIA — a instalacao nova, que e onde esta
           fase mais importa — `identificar_linhas` retorna cedo e o portao de
           pixel de `_pontuar_mascara` nem chega a rodar. O portao daqui e o
           UNICO que existe nesse caminho, e sem ele a primeira coisa que o
           scanner aprenderia numa instalacao nova seria uma linha vazia.

        2. CASAMENTO ACIMA DO LIMIAR E DESCARTADO (D-02). `Casamento(None, ...)`
           chega por DOIS motivos diferentes, que pedem desfechos opostos:

               melhor pontuacao < 0.75      "nao conheco ninguem parecido"  APRENDE
               >= 0.75 e sem margem         "conheco DOIS parecidos demais"  CALA

           Aprender no segundo caso e o pior desfecho deste workstream:
           acrescentar ao acervo um quase-duplicado de alguem faz essa pessoa
           PARAR de ser reconhecida — as duas assinaturas se sombreiam e as duas
           caem no silencio pela margem. Medido na Fase 1: virando 8 celulas, a
           original casa 1.000 e a copia 0.921, diferenca 0.079, ABAIXO dos 0.12
           de `MARGEM_MINIMA_SOBRE_O_SEGUNDO`.

        3. CASAMENTO COM O VIGIA MAIS PROXIMO DE FORMA IGUAL. Distancia
           `<= celulas_toleradas` conta como "a mesma leitura" e incrementa
           aquele vigia. Distancia maior RECUSA, e a candidata vira um vigia NOVO
           com contagem 1 — que e a forma exata de "instabilidade REINICIA a
           sequencia" de D-08. Nada de media e nada de mediana: uma assinatura
           media de duas leituras diferentes e uma assinatura de ninguem.

        4. VIGIAS QUE NINGUEM CASOU NESTA LEITURA SAO DESCARTADOS. Isso mantem a
           estrutura limitada pelo numero de linhas da party window (T-02-09) e e
           a outra metade do reinicio de D-08.

        5. VIGIA QUE CHEGOU A `leituras_para_aprender` GRAVA, com `nome=""`.

        A MASCARA GRAVADA E A ANCORA DA SEQUENCIA, E NAO A ULTIMA LEITURA. Com
        `celulas_toleradas` maior que zero, comparar cada leitura com a ANTERIOR
        deixaria uma deriva de uma celula por leitura somar N celulas ao longo da
        sequencia, e a sequencia seria chamada de estavel com a ultima leitura
        longe da primeira. Comparando com a ancora, a deriva total fica limitada
        pela propria tolerancia — que e o unico numero desta fase com um teto
        medido.

        UMA PRIMEIRA APARICAO NAO E UMA RECUSA. Quando nao havia vigia nenhum
        sobrando para comparar, a candidata simplesmente comeca uma sequencia:
        chamar isso de `RecusaPorInstabilidade` poria, no retrato de D-07, um
        evento que nao mediu instabilidade nenhuma — e o retrato existe
        justamente para o usuario ler a faixa real das distancias.
        """
        aprendizados: list[Aprendizado] = []
        recusas: list[RecusaPorInstabilidade] = []

        disponiveis = list(self._vigias)
        sobreviventes: list[_Vigia] = []
        tolerado = self._ajustes.celulas_toleradas

        for candidata in sorted(candidatas, key=lambda c: c.indice):
            if int(candidata.mascara.sum()) < PIXELS_MINIMOS_DE_TEXTO:
                continue
            if candidata.confianca >= LIMIAR_DE_CASAMENTO:
                continue

            havia_com_quem_comparar = bool(disponiveis)
            vigia, distancia = self._mais_proximo(disponiveis, candidata.mascara)

            if vigia is not None and distancia is not None and distancia <= tolerado:
                disponiveis.remove(vigia)
                vigia.leituras += 1
                vigia.indice = candidata.indice
            else:
                if havia_com_quem_comparar:
                    self._recusas += 1
                    if distancia is not None:
                        self._distancias.append(distancia)
                    recusas.append(
                        RecusaPorInstabilidade(
                            indice=candidata.indice,
                            distancia=distancia,
                            tolerado=tolerado,
                        )
                    )
                sobreviventes.append(
                    _Vigia(
                        ancora=candidata.mascara,
                        leituras=1,
                        indice=candidata.indice,
                    )
                )
                continue

            if vigia.leituras < self._ajustes.leituras_para_aprender:
                sobreviventes.append(vigia)
                continue

            aprendizado = self._gravar(vigia, candidata.confianca)
            if aprendizado is not None:
                aprendizados.append(aprendizado)
            # O vigia sai da mesa nos TRES desfechos. Em `criado` e em
            # `ja_existia` porque a entrada existe; em `falhou` porque a proxima
            # sequencia tem de comecar do zero, e nao repetir a gravacao a cada
            # tick para sempre.

        self._vigias = sobreviventes
        return ResultadoDoAprendiz(aprendizados=aprendizados, recusas=recusas)

    @staticmethod
    def _mais_proximo(
        vigias: list[_Vigia], mascara: np.ndarray
    ) -> tuple[_Vigia | None, int | None]:
        """O vigia de FORMA IGUAL mais perto desta mascara, e a distancia.

        Devolve `(None, None)` quando nenhum vigia tem a mesma forma — e o caso
        em que a distancia nao existe, e nao o caso em que ela e grande.
        """
        melhor: _Vigia | None = None
        menor: int | None = None
        for vigia in vigias:
            distancia = distancia_de_hamming(mascara, vigia.ancora)
            if distancia is None:
                continue
            if menor is None or distancia < menor:
                melhor, menor = vigia, distancia
        return melhor, menor

    def _gravar(self, vigia: _Vigia, confianca: float) -> Aprendizado | None:
        """Grava a ANCORA no acervo. `falhou` NAO conta como aprendido.

        `ja_existia` CONTA como sucesso, e a razao esta escrita na docstring de
        `acervo.gravar`: o usuario roda DUAS instancias (Yazalaque e Faerlina)
        sobre a mesma pasta, e o `O_CREAT|O_EXCL` decide a corrida. Tratar
        `ja_existia` como motivo para tentar de novo faria a instancia perdedora
        ficar tentando para sempre, e a entrada JA esta em disco — o objetivo foi
        cumprido, so nao por este processo.

        `falhou` e o oposto, e colapsa-lo em `criado` faria esta fase acreditar
        que aprendeu uma pessoa que nao esta em disco: ela pararia de ser
        candidata, ninguem perguntaria por ela na Fase 3, e ela ficaria anonima
        para sempre sem erro em lugar nenhum.
        """
        assinatura = Assinatura(nome="", mascara=vigia.ancora)
        desfecho = self._acervo.gravar(assinatura)
        if desfecho == "falhou":
            return None
        return Aprendizado(
            chave=chave_da_assinatura(assinatura),
            indice=vigia.indice,
            desfecho=desfecho,
            assinatura=assinatura,
            confianca=confianca,
        )
