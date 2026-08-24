"""Rastreador: decide o que aconteceu, a partir do que foi lido.

Camada pura. Nao tem relogio proprio (o tempo entra por parametro), nao tem
rede, nao abre arquivo. Isso e o que torna trinta segundos de debounce
testaveis em fracao de milissegundo — e e a diferenca entre um projeto com um
teste de caminho feliz e um com cobertura dos casos raros que a ferramenta
existe para pegar.

TRES PROPRIEDADES QUE SAO DE CORRETUDE, NAO DE GOSTO:

1. **O portao de visibilidade e avaliado ANTES das linhas.** Se fosse depois,
   um unico alt-tab produziria quatro alertas de "saiu da party" ao mesmo
   tempo. A ordem aqui nao e otimizacao, e a diferenca entre util e inutil.

2. **Cegueira CONGELA os contadores, nao zera.** Uma morte que comecou 200 ms
   antes de um alt-tab ainda precisa alertar quando a visao voltar. Zerar
   perderia exatamente o evento mais importante.

3. **Sair do estado morto exige MAIS confirmacoes do que entrar.** Sem essa
   assimetria, um piscar de um frame no HP produz "ressuscitou" seguido
   imediatamente de "morreu" — o efeito de bate-estaca que sistemas de alerta
   maduros combatem com histerese.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .visao import EstadoDaLinha, Observacao


class EstadoDoMembro(Enum):
    VIVO = "vivo"
    MORTO = "morto"
    AUSENTE = "ausente"  # linha nao existe: saiu da PT, ou nunca esteve
    DESCONHECIDO = "desconhecido"  # ainda nao vimos o suficiente


class PortaoGlobal(Enum):
    """Estado da visao do scanner sobre a party window."""

    RASTREANDO = "rastreando"
    CEGO = "cego"
    REAQUISICAO = "reaquisicao"  # acabou de voltar; ainda em tolerancia


class TipoDeEvento(Enum):
    MORREU = "morreu"
    RESSUSCITOU = "ressuscitou"
    SAIU = "saiu"
    ENTROU = "entrou"
    CEGUEIRA_LONGA = "cegueira_longa"
    VISAO_RECUPERADA = "visao_recuperada"


@dataclass(frozen=True)
class Evento:
    """Algo que o rastreador confirmou. Entrada do notificador."""

    tipo: TipoDeEvento
    momento: float
    membro: str | None = None
    detalhe: str | None = None
    segundos_no_estado: float | None = None


@dataclass
class Ajustes:
    """Quanto o rastreador espera antes de acreditar no que ve.

    Todos configuraveis: a orientacao operacional para falso alarme em todo
    sistema de alerta maduro e "aumente a contagem de confirmacao", entao esses
    numeros nao podem ser constantes escondidas no codigo.
    """

    # Quantas leituras seguidas de HP zerado confirmam uma morte.
    confirmacoes_para_morte: int = 3

    # Quantas leituras seguidas de HP acima de zero confirmam ressurreicao.
    # MAIOR que o de morte, de proposito — histerese assimetrica.
    confirmacoes_para_ressurreicao: int = 5

    # Quantas leituras seguidas de linha ausente confirmam saida da PT.
    # Mais alto porque a UI pode redesenhar parcialmente.
    confirmacoes_para_saida: int = 5

    # Quantas leituras de linha presente confirmam que alguem entrou.
    confirmacoes_para_entrada: int = 3

    # Tolerancia depois de recuperar a visao: a UI redesenha em partes e as
    # barras leem zero por um ou dois frames. Alertar nesse intervalo inventaria
    # mortes que nunca aconteceram.
    segundos_de_tolerancia_na_volta: float = 3.0

    # Cegueira mais longa que isto vira um aviso. Perda de cobertura silenciosa
    # e o pior modo de falha do dominio: a party aprende que silencio significa
    # seguranca, e um travamento de vinte minutos passa despercebido.
    segundos_para_cegueira_longa: float = 300.0

    # Abaixo disto o HP conta como zerado. Nao e exatamente 0.0 porque a borda
    # da barra pode deixar um ou dois pixels de residuo.
    fracao_hp_considerada_zero: float = 0.02


@dataclass
class _EstadoInterno:
    """Contadores por linha. Detalhe de implementacao."""

    estado: EstadoDoMembro = EstadoDoMembro.DESCONHECIDO
    desde: float = 0.0
    contador_morte: int = 0
    contador_ressurreicao: int = 0
    contador_saida: int = 0
    contador_entrada: int = 0
    hp_visto: float | None = None


@dataclass
class Rastreador:
    """Transforma uma sequencia de observacoes em eventos confirmados."""

    ajustes: Ajustes = field(default_factory=Ajustes)
    nomes: list[str] = field(default_factory=list)

    _linhas: dict[int, _EstadoInterno] = field(default_factory=dict, init=False)
    _portao: PortaoGlobal = field(default=PortaoGlobal.CEGO, init=False)
    _cego_desde: float | None = None
    _cegueira_ja_avisada: bool = field(default=False, init=False)
    _fim_da_tolerancia: float = field(default=0.0, init=False)
    _primeira_observacao: bool = field(default=True, init=False)

    @property
    def portao(self) -> PortaoGlobal:
        return self._portao

    def estado_de(self, indice: int) -> EstadoDoMembro:
        return self._linhas.get(indice, _EstadoInterno()).estado

    def hp_de(self, indice: int) -> float | None:
        return self._linhas.get(indice, _EstadoInterno()).hp_visto

    def nome_de(self, indice: int) -> str:
        if 0 <= indice < len(self.nomes):
            return self.nomes[indice]
        return f"Membro {indice + 1}"

    def observar(self, obs: Observacao, agora: float) -> list[Evento]:
        """Processa uma observacao e devolve os eventos confirmados nela."""
        eventos: list[Evento] = []

        # --- PORTAO GLOBAL PRIMEIRO. Nunca depois das linhas. ---
        if not obs.ui_visivel:
            if self._portao is not PortaoGlobal.CEGO:
                self._portao = PortaoGlobal.CEGO
                self._cego_desde = agora
                self._cegueira_ja_avisada = False

            elif (
                self._cego_desde is not None
                and not self._cegueira_ja_avisada
                and agora - self._cego_desde
                >= self.ajustes.segundos_para_cegueira_longa
            ):
                self._cegueira_ja_avisada = True
                eventos.append(
                    Evento(
                        tipo=TipoDeEvento.CEGUEIRA_LONGA,
                        momento=agora,
                        segundos_no_estado=agora - self._cego_desde,
                    )
                )

            # Cego: NAO mexe nos contadores das linhas. Congelar, nao zerar —
            # uma morte iniciada logo antes do alt-tab sobrevive a pausa.
            return eventos

        # --- Visao presente ---
        if self._portao is PortaoGlobal.CEGO:
            duracao = agora - self._cego_desde if self._cego_desde else 0.0
            self._portao = PortaoGlobal.REAQUISICAO
            self._fim_da_tolerancia = (
                agora + self.ajustes.segundos_de_tolerancia_na_volta
            )

            # So vale a pena contar que ficou cego se ja tinhamos avisado —
            # senao todo alt-tab de dois segundos vira mensagem.
            if self._cegueira_ja_avisada:
                eventos.append(
                    Evento(
                        tipo=TipoDeEvento.VISAO_RECUPERADA,
                        momento=agora,
                        segundos_no_estado=duracao,
                    )
                )
            self._cego_desde = None
            self._cegueira_ja_avisada = False

        if self._portao is PortaoGlobal.REAQUISICAO:
            if agora < self._fim_da_tolerancia:
                # Dentro da tolerancia: le, mas nao conclui nada. A UI ainda
                # esta se desenhando e as barras mentem por um ou dois frames.
                self._registrar_hp(obs)
                return eventos
            self._portao = PortaoGlobal.RASTREANDO

        eventos.extend(self._processar_linhas(obs, agora))
        self._primeira_observacao = False
        return eventos

    def _registrar_hp(self, obs: Observacao) -> None:
        for linha in obs.linhas:
            interno = self._linhas.setdefault(linha.indice, _EstadoInterno())
            interno.hp_visto = linha.hp

    def _processar_linhas(self, obs: Observacao, agora: float) -> list[Evento]:
        eventos: list[Evento] = []

        for linha in obs.linhas:
            interno = self._linhas.setdefault(linha.indice, _EstadoInterno())
            interno.hp_visto = linha.hp

            # O nome reconhecido pela imagem vence a posicao da linha. A party
            # window compacta as linhas quando alguem sai, entao a posicao e um
            # lugar, nao uma identidade — e um alerta com o nome errado manda a
            # party socorrer a pessoa errada.
            nome = linha.nome or self.nome_de(linha.indice)

            if linha.estado is EstadoDaLinha.VAZIA:
                interno.contador_morte = 0
                interno.contador_ressurreicao = 0
                interno.contador_entrada = 0
                interno.contador_saida += 1

                if interno.estado in (EstadoDoMembro.VIVO, EstadoDoMembro.MORTO):
                    if interno.contador_saida >= self.ajustes.confirmacoes_para_saida:
                        interno.estado = EstadoDoMembro.AUSENTE
                        interno.desde = agora
                        eventos.append(
                            Evento(
                                tipo=TipoDeEvento.SAIU, momento=agora, membro=nome
                            )
                        )
                elif interno.estado is EstadoDoMembro.DESCONHECIDO:
                    # Comeco frio: linha vazia desde o inicio nao e "saiu"
                    if interno.contador_saida >= self.ajustes.confirmacoes_para_saida:
                        interno.estado = EstadoDoMembro.AUSENTE
                        interno.desde = agora
                continue

            # --- Linha com membro ---
            interno.contador_saida = 0
            morto_agora = (
                linha.hp is not None
                and linha.hp <= self.ajustes.fracao_hp_considerada_zero
            )

            if interno.estado in (EstadoDoMembro.AUSENTE, EstadoDoMembro.DESCONHECIDO):
                interno.contador_entrada += 1
                if interno.contador_entrada >= self.ajustes.confirmacoes_para_entrada:
                    entrou_de_verdade = interno.estado is EstadoDoMembro.AUSENTE
                    interno.estado = (
                        EstadoDoMembro.MORTO if morto_agora else EstadoDoMembro.VIVO
                    )
                    interno.desde = agora
                    interno.contador_entrada = 0
                    # Comeco frio nao anuncia que a party inteira "entrou"
                    if entrou_de_verdade and not self._primeira_observacao:
                        eventos.append(
                            Evento(
                                tipo=TipoDeEvento.ENTROU, momento=agora, membro=nome
                            )
                        )
                continue

            if interno.estado is EstadoDoMembro.VIVO:
                interno.contador_ressurreicao = 0
                if morto_agora:
                    interno.contador_morte += 1
                    if interno.contador_morte >= self.ajustes.confirmacoes_para_morte:
                        interno.estado = EstadoDoMembro.MORTO
                        interno.desde = agora
                        interno.contador_morte = 0
                        eventos.append(
                            Evento(
                                tipo=TipoDeEvento.MORREU, momento=agora, membro=nome
                            )
                        )
                else:
                    interno.contador_morte = 0

            elif interno.estado is EstadoDoMembro.MORTO:
                interno.contador_morte = 0
                if not morto_agora:
                    interno.contador_ressurreicao += 1
                    if (
                        interno.contador_ressurreicao
                        >= self.ajustes.confirmacoes_para_ressurreicao
                    ):
                        tempo_morto = agora - interno.desde
                        interno.estado = EstadoDoMembro.VIVO
                        interno.desde = agora
                        interno.contador_ressurreicao = 0
                        eventos.append(
                            Evento(
                                tipo=TipoDeEvento.RESSUSCITOU,
                                momento=agora,
                                membro=nome,
                                segundos_no_estado=tempo_morto,
                            )
                        )
                else:
                    interno.contador_ressurreicao = 0

        return eventos

    def encerrar(self, agora: float, jogo_fechou: bool = False) -> list[Evento]:
        """Chamado quando o scanner para.

        Se o jogo foi fechado de proposito, NAO anunciar que a party inteira
        saiu. Fechar o cliente as duas da manha nao deve acordar quatro pessoas.
        """
        if jogo_fechou:
            for interno in self._linhas.values():
                interno.estado = EstadoDoMembro.AUSENTE
                interno.contador_saida = 0
        return []
