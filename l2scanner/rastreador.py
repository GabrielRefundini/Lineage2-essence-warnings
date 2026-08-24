"""Rastreador: decide o que aconteceu, a partir do que foi lido.

Camada pura. Nao tem relogio proprio (o tempo entra por parametro), nao tem
rede, nao abre arquivo. Isso e o que torna trinta segundos de debounce
testaveis em fracao de milissegundo — e e a diferenca entre um projeto com um
teste de caminho feliz e um com cobertura dos casos raros que a ferramenta
existe para pegar.

QUATRO PROPRIEDADES QUE SAO DE CORRETUDE, NAO DE GOSTO:

1. **O estado e guardado POR PESSOA, nunca por posicao de linha.** A party
   window reordena: quando alguem sai, os outros sobem, e o lider pode ir para
   o topo. Guardar estado por linha faz "a linha 3 esvaziou" virar "saiu quem a
   lista diz que ocupa a posicao 3" — que quase nunca e quem realmente saiu.
   Isso aconteceu de verdade: o TioMad saiu e o alerta anunciou o Korzis.

2. **O portao de visibilidade e avaliado ANTES das linhas.** Se fosse depois,
   um unico alt-tab produziria varios alertas de "saiu da party" ao mesmo
   tempo. A ordem aqui nao e otimizacao, e a diferenca entre util e inutil.

3. **Cegueira CONGELA os contadores, nao zera.** Uma morte que comecou 200 ms
   antes de um alt-tab ainda precisa alertar quando a visao voltar. Zerar
   perderia exatamente o evento mais importante.

4. **Sair do estado morto exige MAIS confirmacoes do que entrar.** Sem essa
   assimetria, um piscar de um frame no HP produz "ressuscitou" seguido
   imediatamente de "morreu" — o efeito de bate-estaca que sistemas de alerta
   maduros combatem com histerese.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .visao import EstadoDaLinha, LeituraDeLinha, Observacao


class EstadoDoMembro(Enum):
    VIVO = "vivo"
    MORTO = "morto"
    AUSENTE = "ausente"  # nao esta na party: saiu, ou nunca esteve
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

    confirmacoes_para_morte: int = 3

    # MAIOR que o de morte, de proposito — histerese assimetrica.
    confirmacoes_para_ressurreicao: int = 5

    # Mais alto porque a UI pode redesenhar parcialmente.
    confirmacoes_para_saida: int = 5

    confirmacoes_para_entrada: int = 3

    # Tolerancia depois de recuperar a visao: a UI redesenha em partes e as
    # barras leem zero por um ou dois frames.
    segundos_de_tolerancia_na_volta: float = 3.0

    # Cegueira mais longa que isto vira um aviso. Perda de cobertura silenciosa
    # e o pior modo de falha do dominio.
    segundos_para_cegueira_longa: float = 300.0

    # Abaixo disto o HP conta como zerado. Nao e exatamente 0.0 porque a borda
    # da barra pode deixar um ou dois pixels de residuo.
    fracao_hp_considerada_zero: float = 0.02


@dataclass
class _EstadoInterno:
    """Contadores de UM membro. Detalhe de implementacao."""

    estado: EstadoDoMembro = EstadoDoMembro.DESCONHECIDO
    desde: float = 0.0
    contador_morte: int = 0
    contador_ressurreicao: int = 0
    contador_saida: int = 0
    contador_entrada: int = 0
    hp_visto: float | None = None


def _chave_da_linha(linha: LeituraDeLinha) -> str:
    """A identidade sob a qual esta linha e rastreada.

    Nome reconhecido pela imagem sempre que houver. Sem reconhecimento, cai
    para uma chave presa a posicao — que e pior, mas e o melhor possivel quando
    nao sabemos quem esta ali, e nao contamina os membros que foram
    reconhecidos.
    """
    return linha.nome or f"#linha{linha.indice}"


@dataclass
class Rastreador:
    """Transforma uma sequencia de observacoes em eventos confirmados."""

    ajustes: Ajustes = field(default_factory=Ajustes)
    nomes: list[str] = field(default_factory=list)

    # Estado POR PESSOA. A chave e a identidade, nunca a posicao — a party
    # window reordena, e guardar por posicao atribui eventos a quem nao os
    # viveu.
    _membros: dict[str, _EstadoInterno] = field(default_factory=dict, init=False)

    # So para exibicao: qual identidade estava em cada linha no ultimo frame.
    _identidade_por_linha: dict[int, str] = field(default_factory=dict, init=False)

    # Chave de estado -> nome legivel. Para uma linha reconhecida os dois sao o
    # mesmo. Para uma linha NAO reconhecida a chave e presa a posicao
    # (`#linha2`), mas o nome exibido vem da lista configurada — porque
    # "#linha2 morreu" nao ajuda ninguem, e o nome por posicao ainda e o melhor
    # palpite disponivel quando a imagem nao foi reconhecida.
    _rotulo: dict[str, str] = field(default_factory=dict, init=False)

    _portao: PortaoGlobal = field(default=PortaoGlobal.CEGO, init=False)
    _cego_desde: float | None = None
    _cegueira_ja_avisada: bool = field(default=False, init=False)
    _fim_da_tolerancia: float = field(default=0.0, init=False)
    _primeira_observacao: bool = field(default=True, init=False)

    # Vira True quando o primeiro membro sai de DESCONHECIDO. Antes disso
    # estamos aquecendo e ninguem 'entrou' — a party ja estava formada
    # quando o scanner ligou. Depois disso, uma identidade nova aparecendo
    # e uma entrada de verdade.
    _aquecido: bool = field(default=False, init=False)

    @property
    def portao(self) -> PortaoGlobal:
        return self._portao

    def nome_de(self, indice: int) -> str:
        """Nome configurado para uma POSICAO. Usado so como ultimo recurso."""
        if 0 <= indice < len(self.nomes):
            return self.nomes[indice]
        return f"Membro {indice + 1}"

    def estado_de_membro(self, identidade: str) -> EstadoDoMembro:
        return self._membros.get(identidade, _EstadoInterno()).estado

    def hp_de_membro(self, identidade: str) -> float | None:
        return self._membros.get(identidade, _EstadoInterno()).hp_visto

    def identidade_na_linha(self, indice: int) -> str | None:
        """Quem estava nesta linha no ultimo frame. So para o console."""
        return self._identidade_por_linha.get(indice)

    def estado_de(self, indice: int) -> EstadoDoMembro:
        """Compatibilidade para exibicao: o estado de quem esta nesta linha."""
        identidade = self._identidade_por_linha.get(indice)
        if identidade is None:
            return EstadoDoMembro.DESCONHECIDO
        return self.estado_de_membro(identidade)

    def hp_de(self, indice: int) -> float | None:
        identidade = self._identidade_por_linha.get(indice)
        return self.hp_de_membro(identidade) if identidade else None

    def _nome_exibido(self, identidade: str) -> str:
        """Nome que vai no alerta. Nunca a chave interna."""
        return self._rotulo.get(identidade, identidade)

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

            # Cego: NAO mexe nos contadores. Congelar, nao zerar — uma morte
            # iniciada logo antes do alt-tab sobrevive a pausa.
            return eventos

        # --- Visao presente ---
        if self._portao is PortaoGlobal.CEGO:
            duracao = agora - self._cego_desde if self._cego_desde else 0.0
            self._portao = PortaoGlobal.REAQUISICAO
            self._fim_da_tolerancia = (
                agora + self.ajustes.segundos_de_tolerancia_na_volta
            )

            # So vale contar que ficou cego se ja tinhamos avisado — senao todo
            # alt-tab de dois segundos vira mensagem.
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
                self._registrar_leituras(obs)
                return eventos
            self._portao = PortaoGlobal.RASTREANDO

        eventos.extend(self._processar(obs, agora))
        self._primeira_observacao = False
        return eventos

    def _registrar_leituras(self, obs: Observacao) -> None:
        """Atualiza HP e o mapa de exibicao, sem concluir nada."""
        self._identidade_por_linha = {}
        for linha in obs.linhas:
            if linha.estado is not EstadoDaLinha.COM_MEMBRO:
                continue
            identidade = _chave_da_linha(linha)
            self._identidade_por_linha[linha.indice] = identidade
            self._rotulo[identidade] = linha.nome or self.nome_de(linha.indice)
            self._membros.setdefault(identidade, _EstadoInterno()).hp_visto = linha.hp

    def _processar(self, obs: Observacao, agora: float) -> list[Evento]:
        eventos: list[Evento] = []

        # Quem esta na tela AGORA, por identidade
        presentes: dict[str, LeituraDeLinha] = {}
        self._identidade_por_linha = {}
        for linha in obs.linhas:
            if linha.estado is not EstadoDaLinha.COM_MEMBRO:
                continue
            identidade = _chave_da_linha(linha)
            presentes[identidade] = linha
            self._identidade_por_linha[linha.indice] = identidade
            self._rotulo[identidade] = linha.nome or self.nome_de(linha.indice)

        # --- Quem sumiu da party ---
        # Comparar CONJUNTOS de identidade, e nao posicoes, e o que faz "TioMad
        # saiu" ser atribuido ao TioMad mesmo quando a party inteira reordena.
        for identidade, interno in self._membros.items():
            if identidade in presentes:
                continue

            interno.contador_morte = 0
            interno.contador_ressurreicao = 0
            interno.contador_entrada = 0
            interno.contador_saida += 1

            if interno.contador_saida < self.ajustes.confirmacoes_para_saida:
                continue

            se_estava_na_party = interno.estado in (
                EstadoDoMembro.VIVO,
                EstadoDoMembro.MORTO,
            )
            interno.estado = EstadoDoMembro.AUSENTE
            interno.desde = agora
            if se_estava_na_party:
                eventos.append(
                    Evento(
                        tipo=TipoDeEvento.SAIU,
                        momento=agora,
                        membro=self._nome_exibido(identidade),
                    )
                )

        # --- Quem esta presente ---
        for identidade, linha in presentes.items():
            interno = self._membros.setdefault(identidade, _EstadoInterno())
            interno.hp_visto = linha.hp
            interno.contador_saida = 0

            morto_agora = (
                linha.hp is not None
                and linha.hp <= self.ajustes.fracao_hp_considerada_zero
            )

            if interno.estado in (
                EstadoDoMembro.AUSENTE,
                EstadoDoMembro.DESCONHECIDO,
            ):
                interno.contador_entrada += 1
                if interno.contador_entrada < self.ajustes.confirmacoes_para_entrada:
                    continue

                # AUSENTE -> presente e sempre uma entrada. DESCONHECIDO ->
                # presente so e entrada se o scanner ja passou do aquecimento;
                # antes disso e so a party que ja existia sendo descoberta.
                entrou_de_verdade = (
                    interno.estado is EstadoDoMembro.AUSENTE or self._aquecido
                )
                interno.estado = (
                    EstadoDoMembro.MORTO if morto_agora else EstadoDoMembro.VIVO
                )
                interno.desde = agora
                interno.contador_entrada = 0
                # Comeco frio nao anuncia que a party inteira "entrou"
                if entrou_de_verdade:
                    eventos.append(
                        Evento(
                            tipo=TipoDeEvento.ENTROU,
                            momento=agora,
                            membro=self._nome_exibido(identidade),
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
                                tipo=TipoDeEvento.MORREU,
                                momento=agora,
                                membro=self._nome_exibido(identidade),
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
                                membro=self._nome_exibido(identidade),
                                segundos_no_estado=tempo_morto,
                            )
                        )
                else:
                    interno.contador_ressurreicao = 0

        # O aquecimento termina quando o primeiro membro assume um estado real.
        # Marcar DEPOIS do laco evita que os membros processados mais tarde na
        # mesma iteracao sejam lidos como recem-chegados.
        if not self._aquecido and any(
            m.estado in (EstadoDoMembro.VIVO, EstadoDoMembro.MORTO)
            for m in self._membros.values()
        ):
            self._aquecido = True

        return eventos

    def encerrar(self, agora: float, jogo_fechou: bool = False) -> list[Evento]:
        """Chamado quando o scanner para.

        Se o jogo foi fechado de proposito, NAO anunciar que a party inteira
        saiu. Fechar o cliente as duas da manha nao deve acordar a party.
        """
        if jogo_fechou:
            for interno in self._membros.values():
                interno.estado = EstadoDoMembro.AUSENTE
                interno.contador_saida = 0
        return []
