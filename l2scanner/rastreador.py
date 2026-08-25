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

    # Voce saiu (ou foi expulso) da party. Nao da para distinguir os dois pela
    # tela — os dois deixam a party window sumir e a sua barra intacta.
    VOCE_SEM_PARTY = "voce_sem_party"
    VOCE_ENTROU_EM_PARTY = "voce_entrou_em_party"

    # O CLIENTE caiu: dialogo de desconexao na tela, ou de volta na tela de
    # login. Cegueira com causa conhecida nao e cegueira — e um evento, e e o
    # evento que explica todos os outros silencios que vierem depois dele.
    JOGO_CAIU = "jogo_caiu"
    JOGO_VOLTOU = "jogo_voltou"


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

    # Quantas leituras seguidas com o cliente caido ate anunciar. Baixo de
    # proposito, ao contrario de todos os outros: o titulo da janela e prova,
    # nao inferencia sobre pixels, e nao pisca. Duas leituras existem so para
    # atravessar o frame exato da troca de tela.
    confirmacoes_para_jogo_caiu: int = 2

    # Voltar exige mais, pela mesma histerese assimetrica das mortes: a tela de
    # selecao de personagem passa rapido e nao e "voltou a jogar".
    confirmacoes_para_jogo_voltou: int = 4

    # Quantas leituras seguidas sem party window, COM a sua barra visivel, ate
    # concluir que voce nao esta mais em party. Alto de proposito: trocar de
    # zona e abrir menu tambem escondem a party window por alguns frames.
    confirmacoes_para_voce_sem_party: int = 8

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

    # Quantas linhas a party window tinha da ultima vez que vimos este membro.
    # E o que distingue "ele saiu" de "o reconhecimento falhou": quando alguem
    # sai de verdade a party window ENCOLHE, porque as linhas compactam. Uma
    # falha de reconhecimento nao muda a contagem de linhas nenhuma.
    #
    # O mesmo sinal, ao contrario, separa "entrou" de "passei a reconhecer":
    # quem entra faz a janela CRESCER; um nome que so agora foi reconhecido nao
    # muda contagem nenhuma.
    linhas_quando_visto: int = 0

    # Se a party window CRESCEU no frame em que este membro apareceu. Guardado
    # em vez de reavaliado: a entrada so confirma apos N leituras, e no
    # enesimo frame a janela ja parou de crescer. Reavaliar perderia o evento.
    apareceu_com_crescimento: bool = False


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

    # Nome do proprio personagem. Ele nao aparece na propria party window, mas
    # o estado dele e rastreado igual ao dos outros — inclusive porque e quem
    # tem mais chance de morrer sem ninguem perceber.
    nome_proprio: str | None = None

    # MODO SOLO: voce nao esta em party, e isso e escolha, nao problema.
    #
    # A diferenca em relacao a "party window sumiu" e toda: ali o scanner nao
    # sabe se voce saiu, se a UI travou ou se o jogo caiu, e reclamar e o certo.
    # Aqui ele SABE que nao ha party — voce disse — entao reclamar da ausencia
    # seria ruido garantido, a cada tick, pela sessao inteira.
    #
    # O que NAO muda: a sua morte continua sendo vigiada com o mesmo debounce, e
    # a agenda continua igual. Solo e justamente quando morrer AFK passa mais
    # despercebido — em party alguem nota.
    modo_solo: bool = False

    # Se ha assinaturas visuais gravadas. Quando ha, a lista `nomes` deixa de
    # valer como identidade por posicao — ela so serviria para atribuir o nome
    # de uma pessoa a uma linha que nao e dela.
    assinaturas_configuradas: bool = False

    # Nomes que tem assinatura visual gravada. Eles nunca servem de rotulo por
    # POSICAO: a assinatura e quem diz onde a pessoa esta.
    nomes_reservados: set[str] = field(default_factory=set)

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

    # Quantas linhas a party window tinha no ultimo frame processado. E a
    # referencia para decidir se ela cresceu ou encolheu.
    #
    # None ate o primeiro frame rastreado, e a distincao importa: com 0 como
    # valor inicial, o primeiro frame comparava 4 linhas contra uma linha de
    # base que nunca existiu e concluia "a party cresceu de 0 para 4". Esse
    # True ficava gravado por membro (`apareceu_com_crescimento` e guardado, nao
    # reavaliado), e quem confirmasse a entrada depois do aquecimento disparava
    # um ENTROU falso — bastava UM frame de falha de reconhecimento para
    # atrasar alguem o suficiente. Foi o "TioMad entrou na party" as 18:18 com
    # a party parada desde antes do scanner ligar.
    #
    # Sem linha de base nao existe crescimento: o primeiro frame so a
    # estabelece. Uma entrada de verdade nos primeiros segundos passa calada, o
    # que e o mesmo comeco frio que `_aquecido` ja aplica ao resto.
    _ultima_contagem_estavel: int | None = field(default=None, init=False)

    # Rastreio de "voce esta em party?". So faz sentido quando a barra propria
    # esta calibrada: e ela que distingue "sai da party" de "perdi a visao".

    _voce_em_party: bool | None = field(default=None, init=False)
    _contador_sem_party: int = field(default=0, init=False)
    _contador_com_party: int = field(default=0, init=False)

    # Se o scanner ja conseguiu ver a party window pelo menos UMA vez.
    #
    # Enquanto for False, o veredito "voce nao esta em party" nao e
    # conhecimento — e so a ausencia de leitura. A diferenca importa na volta:
    # sem isto, um arranque que demora a enxergar a tela fixava False em
    # silencio e depois anunciava "voce entrou em party" quando a visao voltava,
    # com voce na mesma party o tempo todo. Aconteceu as 18:08.
    #
    # Os pixels de "liguei fora de party e entrei" e de "liguei e demorei para
    # ler a tela" sao IDENTICOS, entao nao da para separar os dois por imagem.
    # Entre anunciar uma entrada que voce mesmo fez (e portanto ja sabe) e
    # inventar uma que nao houve, calar e a escolha certa.
    _ja_viu_party_window: bool = field(default=False, init=False)

    # O cliente esta caido (tela de login ou dialogo de desconexao) AGORA.
    _cliente_caido: bool = field(default=False, init=False)
    _contador_cliente_caido: int = field(default=0, init=False)
    _contador_cliente_de_pe: int = field(default=0, init=False)

    # Ja vimos o cliente JOGANDO alguma vez. Antes disso, "caido" e o estado
    # em que o scanner encontrou o mundo, nao uma queda que aconteceu.
    _cliente_ja_esteve_de_pe: bool = field(default=False, init=False)

    # A queda que esta valendo agora chegou a ser anunciada. Sem isto, um
    # scanner ligado com o jogo fechado anunciaria "o jogo voltou" no primeiro
    # login do dia sem nunca ter dito que caiu.
    _queda_anunciada: bool = field(default=False, init=False)

    # Se o veredito "voce nao esta em party" que esta valendo agora foi firmado
    # COM a party window ja tendo sido vista alguma vez. Guardado no instante em
    # que o veredito e firmado, e nao consultado na volta: quando a entrada
    # confirma, a party window ja esta visivel ha varios frames e
    # `_ja_viu_party_window` ja virou True — perguntar naquele momento sempre
    # responderia "sim" e a guarda seria inutil.
    _sem_party_era_confiavel: bool = field(default=False, init=False)

    @property
    def portao(self) -> PortaoGlobal:
        return self._portao

    def nome_de(self, indice: int) -> str:
        """Nome configurado para uma POSICAO. Usado so como ultimo recurso.

        Nomes com assinatura gravada ficam de fora: se a assinatura nao casou
        nesta linha, esta linha nao e daquela pessoa, e usar o nome dela aqui
        produz um alerta com o nome errado — o pior modo de falha do produto.
        """
        if 0 <= indice < len(self.nomes):
            nome = self.nomes[indice]
            if nome not in self.nomes_reservados:
                return nome
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

    def _rotular(self, linha: LeituraDeLinha, identidade: str) -> str:
        """Como esta linha deve ser CHAMADA num alerta.

        Regra dura: uma linha NAO reconhecida jamais pega emprestado o nome de
        outra pessoa. A lista do config e ordenada por posicao, e a posicao nao
        e identidade — usar `nomes[1]` para uma linha desconhecida faz o alerta
        sair com o nome de quem esta vivo em outra linha.

        Isso quase aconteceu de verdade: a linha 1, nao reconhecida e com HP
        zerado, estava rotulada "Korzis" enquanto o Korzis real estava vivo na
        linha 0. Faltava um debounce para anunciar a morte da pessoa errada.

        "Membro 2" e feio. Anunciar a morte de quem esta vivo e pior.
        """
        if linha.nome:
            return linha.nome
        if self.assinaturas_configuradas:
            return f"Membro {linha.indice + 1}"
        # Sem assinatura nenhuma nao ha identidade visual em jogo, e o nome por
        # posicao e a unica informacao que existe.
        return self.nome_de(linha.indice)

    def observar(self, obs: Observacao, agora: float) -> list[Evento]:
        """Processa uma observacao e devolve os eventos confirmados nela."""
        eventos: list[Evento] = []

        # --- O CLIENTE CAIU? Antes de tudo. ---
        # Esta pergunta vem primeiro porque a resposta dela EXPLICA todas as
        # outras. Com o jogo caido, a party window nao esta escondida: ela nao
        # existe. Deixar as avaliacoes seguintes rodarem produziria "voce saiu
        # da party" e "fulano saiu" a partir de uma tela de login — que foi
        # exatamente a familia de alarme falso corrigida hoje mais cedo.
        eventos.extend(self._avaliar_o_cliente(obs, agora))
        if self._cliente_caido:
            # Caido congela tudo, igual a cegueira. A diferenca e que agora o
            # silencio tem nome, e a party ja foi avisada do motivo.
            return eventos

        # --- VOCE ESTA EM PARTY? ---
        # A pergunta so e respondivel porque a SUA barra e lida separado da
        # party window. A combinacao "minha barra esta la, a party window nao"
        # e unica:
        #   alt-tab / jogo coberto -> a captura por janela ve tudo, nada some
        #   tela de loading        -> some tudo, a sua barra inclusive
        #   voce fora da party     -> so a party window some
        # Sem a barra propria, "sair da party" era indistinguivel de "perdi a
        # visao" e o scanner ficava calado.
        # No solo a pergunta "voce esta em party?" nao tem sentido: a resposta
        # e nao, por escolha sua, e anunciar isso todo tick seria ruido.
        if obs.hp_proprio is not None and not self.modo_solo:
            eventos.extend(self._avaliar_se_voce_esta_em_party(obs, agora))

        # --- PORTAO GLOBAL. Nunca depois das linhas. ---
        if not obs.ui_visivel:
            if self._portao is not PortaoGlobal.CEGO:
                self._portao = PortaoGlobal.CEGO
                self._cego_desde = agora
                self._cegueira_ja_avisada = False

            elif (
                self._cego_desde is not None
                and not self._cegueira_ja_avisada
                # No solo nao HA party window para enxergar. Avisar "sem visao
                # da party ha 5min" seria reclamar da ausencia de algo que o
                # usuario decidiu nao ter.
                and not self.modo_solo
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

            # SOLO, OU PARTY WINDOW COBERTA: a SUA barra pode continuar
            # perfeitamente legivel mesmo sem party window nenhuma.
            #
            # O portao de cegueira fala da PARTY WINDOW. Deixa-lo bloquear a
            # avaliacao da sua propria barra confunde "nao vejo a party" com
            # "nao vejo voce" — e o resultado media era o pior possivel: upando
            # solo, o scanner ficava CEGO permanentemente e a sua morte nunca
            # era detectada. Medido: 30 frames com o HP proprio em ZERO
            # produziam ZERO eventos.
            #
            # Isso vale tambem com o inventario aberto por cima da party
            # window: se a sua barra continua visivel, morrer continua sendo
            # detectavel.
            eventos.extend(self._avaliar_so_o_proprio(obs, agora))

            # Cego para o RESTO: nao mexe nos contadores dos outros. Congelar,
            # nao zerar — uma morte iniciada logo antes do alt-tab sobrevive.
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

    def _avaliar_o_cliente(self, obs: Observacao, agora: float) -> list[Evento]:
        """O cliente caiu, ou voltou? Debounce proprio, estado proprio.

        Cegueira com causa conhecida nao e cegueira. Ate hoje o scanner so
        sabia dizer "sem visao da party", e essa frase cobria o jogo coberto,
        um menu aberto, o servidor em manutencao e o cliente na tela de login.
        Para quem esta no WhatsApp as tres ultimas sao a mesma coisa — o jogo
        caiu — e nenhuma delas era dita.

        Na sessao de 2026-08-24 o servidor entrou em manutencao e o scanner
        passou 90 s, e depois 5 min, repetindo "sem visao" sem nunca dizer o
        motivo. O `outbox.jsonl` registra os dois silencios.
        """
        estado = obs.estado_do_cliente
        if estado is None:
            return []

        from .cliente import EstadoDoCliente

        if estado is EstadoDoCliente.DESCONHECIDO:
            # Nao da para decidir. Congela os dois contadores: nao e evidencia
            # de que caiu nem de que esta de pe.
            return []

        caido_agora = estado in (
            EstadoDoCliente.TELA_DE_LOGIN,
            EstadoDoCliente.DESCONECTADO,
        )

        if caido_agora:
            self._contador_cliente_de_pe = 0
            self._contador_cliente_caido += 1
        else:
            self._contador_cliente_caido = 0
            self._contador_cliente_de_pe += 1

        if self._contador_cliente_caido >= self.ajustes.confirmacoes_para_jogo_caiu:
            if not self._cliente_caido:
                self._cliente_caido = True
                # COMECO FRIO: ligar o scanner com o jogo ja na tela de login
                # nao e "o jogo caiu" — o usuario esta olhando para a tela.
                # A guarda e "ja vi o cliente de pe alguma vez", e nao
                # `_primeira_observacao`: essa fica presa em True para sempre
                # quando o cliente ja sobe caido, porque `_processar` (o unico
                # lugar que a limpa) nunca chega a rodar.
                if self._cliente_ja_esteve_de_pe:
                    self._queda_anunciada = True
                    return [
                        Evento(
                            tipo=TipoDeEvento.JOGO_CAIU,
                            momento=agora,
                            membro=self.nome_proprio,
                            detalhe=(
                                "tela de login"
                                if estado is EstadoDoCliente.TELA_DE_LOGIN
                                else "desconectado do servidor"
                            ),
                        )
                    ]

        elif (
            self._contador_cliente_de_pe
            >= self.ajustes.confirmacoes_para_jogo_voltou
        ):
            estava_caido = self._cliente_caido
            self._cliente_caido = False
            self._cliente_ja_esteve_de_pe = True
            # So anuncia a volta se a QUEDA foi anunciada. Senao um scanner
            # ligado com o jogo fechado diria "o jogo voltou" no primeiro
            # login do dia, sem nunca ter dito que caiu.
            if estava_caido and self._queda_anunciada:
                self._queda_anunciada = False
                return [
                    Evento(
                        tipo=TipoDeEvento.JOGO_VOLTOU,
                        momento=agora,
                        membro=self.nome_proprio,
                    )
                ]

        return []

    def _avaliar_se_voce_esta_em_party(
        self, obs: Observacao, agora: float
    ) -> list[Evento]:
        """Decide se o usuario ainda esta em party, e avisa quando muda.

        SAIR DA PARTY NAO ENCOSTA NO SEU HP. Essa e a assimetria que separa os
        dois casos que a party window sumindo produz:

          voce saiu da party -> a party window some, a SUA barra continua
                                sendo lida normalmente
          o scanner cegou    -> a party window "some" porque nao da para le-la,
                                e a sua barra le 0% porque o recorte tambem
                                esta ilegivel

        `medir_barra` devolve 0.0 para um recorte preto, nunca None, entao
        `hp_proprio is not None` so quer dizer "a regiao esta calibrada" — nao
        "a minha barra esta visivel". Sem esta guarda, 90 s de cegueira leram
        como "minha barra esta la a 0%, a party window sumiu" e produziram
        "YAZALAQUE SAIU OU FOI REMOVIDO DA PARTY" as 18:19:50 seguido de
        "YAZALAQUE ENTROU EM PARTY" as 18:21:19, com a party intacta o tempo
        todo (logs/scanner.log mostra "[SEM VISAO] Yazalaque (voce) ok HP 0%"
        nos 90 s entre os dois).

        Na duvida, congelar. Um alerta de saida que nao veio e recuperavel; um
        que veio errado destroi a confianca na ferramenta inteira.
        """
        hp_proprio_zerado = (
            obs.hp_proprio is not None
            and obs.hp_proprio <= self.ajustes.fracao_hp_considerada_zero
        )
        if not obs.ui_visivel and hp_proprio_zerado:
            # Cegueira, nao saida. Congela os dois contadores — nem "sem party"
            # nem "com party" avancam — pelo mesmo motivo que o portao global
            # congela morte e ressurreicao: uma leitura impossivel nao e
            # evidencia de nada.
            return []

        tem_party = obs.ui_visivel and obs.membros_presentes > 0

        if tem_party:
            self._ja_viu_party_window = True
            self._contador_sem_party = 0
            self._contador_com_party += 1
        else:
            self._contador_com_party = 0
            self._contador_sem_party += 1

        limite = self.ajustes.confirmacoes_para_voce_sem_party

        if self._contador_sem_party >= limite:
            if self._voce_em_party is not False:
                # "Sem party" so vale como conhecimento se ja tivermos visto a
                # party window alguma vez. Antes disso e ausencia de leitura, e
                # tratar as duas coisas como iguais e o que fazia a volta da
                # visao virar um "voce entrou em party" que nunca aconteceu.
                era_conhecido = (
                    self._voce_em_party is True and self._ja_viu_party_window
                )
                self._voce_em_party = False
                self._sem_party_era_confiavel = self._ja_viu_party_window
                # Comeco frio: se voce ja estava sem party quando o scanner
                # ligou, nao anunciamos nada.
                if era_conhecido:
                    return [
                        Evento(
                            tipo=TipoDeEvento.VOCE_SEM_PARTY,
                            momento=agora,
                            membro=self.nome_proprio,
                        )
                    ]

        elif self._contador_com_party >= self.ajustes.confirmacoes_para_entrada:
            if self._voce_em_party is not True:
                era_conhecido = (
                    self._voce_em_party is False and self._sem_party_era_confiavel
                )
                self._voce_em_party = True
                if era_conhecido:
                    return [
                        Evento(
                            tipo=TipoDeEvento.VOCE_ENTROU_EM_PARTY,
                            momento=agora,
                            membro=self.nome_proprio,
                        )
                    ]

        return []

    def _avaliar_so_o_proprio(self, obs: Observacao, agora: float) -> list[Evento]:
        """Morte e ressurreicao SUAS, sem depender da party window.

        E o caminho de quem esta upando SOLO — e exatamente quem mais precisa,
        porque em party alguem nota que voce caiu, e sozinho ninguem nota.

        `hp_proprio` so chega aqui como numero quando a barra e LEGIVEL: a
        `visao` devolve None para recorte degenerado. Sem essa garantia isto
        seria uma maquina de anunciar a morte de quem esta vivo toda vez que a
        captura falhasse — o mesmo defeito que produziu o falso "Yazalaque nao
        esta mais na party" as 18:19.

        Mesmo debounce e mesma histerese assimetrica dos outros membros: nao ha
        motivo para a sua morte ser julgada com criterio diferente.
        """
        if obs.hp_proprio is None or not self.nome_proprio:
            return []

        chave = f"@{self.nome_proprio}"
        interno = self._membros.setdefault(chave, _EstadoInterno())
        self._rotulo[chave] = self.nome_proprio
        interno.hp_visto = obs.hp_proprio

        morto_agora = obs.hp_proprio <= self.ajustes.fracao_hp_considerada_zero

        if interno.estado is EstadoDoMembro.DESCONHECIDO:
            # Aquecimento: so passa a valer depois de algumas leituras seguidas,
            # para o primeiro frame do arranque nao virar veredito.
            interno.contador_entrada += 1
            if interno.contador_entrada < self.ajustes.confirmacoes_para_entrada:
                return []
            interno.estado = (
                EstadoDoMembro.MORTO if morto_agora else EstadoDoMembro.VIVO
            )
            interno.desde = agora
            interno.contador_entrada = 0
            return []

        if interno.estado is EstadoDoMembro.VIVO:
            interno.contador_ressurreicao = 0
            if not morto_agora:
                interno.contador_morte = 0
                return []
            interno.contador_morte += 1
            if interno.contador_morte < self.ajustes.confirmacoes_para_morte:
                return []
            interno.estado = EstadoDoMembro.MORTO
            interno.desde = agora
            interno.contador_morte = 0
            return [
                Evento(
                    tipo=TipoDeEvento.MORREU, momento=agora, membro=self.nome_proprio
                )
            ]

        if interno.estado is EstadoDoMembro.MORTO:
            interno.contador_morte = 0
            if morto_agora:
                interno.contador_ressurreicao = 0
                return []
            interno.contador_ressurreicao += 1
            if (
                interno.contador_ressurreicao
                < self.ajustes.confirmacoes_para_ressurreicao
            ):
                return []
            tempo_morto = agora - interno.desde
            interno.estado = EstadoDoMembro.VIVO
            interno.desde = agora
            interno.contador_ressurreicao = 0
            return [
                Evento(
                    tipo=TipoDeEvento.RESSUSCITOU,
                    momento=agora,
                    membro=self.nome_proprio,
                    segundos_no_estado=tempo_morto,
                )
            ]

        return []

    def _registrar_leituras(self, obs: Observacao) -> None:
        """Atualiza HP e o mapa de exibicao, sem concluir nada."""
        self._identidade_por_linha = {}
        for linha in obs.linhas:
            if linha.estado is not EstadoDaLinha.COM_MEMBRO:
                continue
            identidade = _chave_da_linha(linha)
            self._identidade_por_linha[linha.indice] = identidade
            self._rotulo[identidade] = self._rotular(linha, identidade)
            interno = self._membros.setdefault(identidade, _EstadoInterno())
            interno.hp_visto = linha.hp
            interno.linhas_quando_visto = obs.membros_presentes

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
            self._rotulo[identidade] = self._rotular(linha, identidade)

        # O proprio personagem entra como mais um membro, com a leitura vinda
        # da barra dele no topo da tela. Tratar igual aos outros faz morte e
        # ressurreicao dele passarem pelo mesmo debounce e pela mesma
        # histerese, sem codigo duplicado.
        if obs.hp_proprio is not None and self.nome_proprio:
            chave = f"@{self.nome_proprio}"
            presentes[chave] = LeituraDeLinha(
                indice=-1,
                estado=EstadoDaLinha.COM_MEMBRO,
                hp=obs.hp_proprio,
                mp=None,
                nome=self.nome_proprio,
                confianca_do_nome=1.0,
            )
            self._rotulo[chave] = self.nome_proprio

        # --- Quem sumiu da party ---
        # Comparar CONJUNTOS de identidade, e nao posicoes, e o que faz "TioMad
        # saiu" ser atribuido ao TioMad mesmo quando a party inteira reordena.
        #
        # MAS: se alguma linha esta OCUPADA e nao foi reconhecida, nao da para
        # afirmar que ninguem saiu — o membro "sumido" pode ser exatamente quem
        # esta naquela linha, so que a imagem falhou naquele frame. Congelar os
        # contadores aqui e o que impede um piscar de reconhecimento de virar
        # "Korzis saiu da party" com o Korzis na tela. Aconteceu de verdade.
        # A regra so vale quando ha identidade em jogo. Sem nenhum membro
        # rastreado por nome, estamos no modo antigo (chave por posicao) e
        # congelar travaria a deteccao de saida para sempre.
        ha_membro_nomeado = any(not k.startswith("#linha") for k in self._membros)

        # Quantas linhas a party window tem AGORA. A comparacao com quantas ela
        # tinha da ultima vez que vimos cada membro e o que separa os dois
        # motivos de alguem sumir do conjunto de identidades.
        linhas_agora = obs.membros_presentes

        for identidade, interno in self._membros.items():
            if identidade in presentes:
                continue

            # A PARTY WINDOW ENCOLHEU? Se nao encolheu, ninguem saiu.
            #
            # Quando alguem sai de verdade, as linhas compactam e a janela fica
            # com uma linha a menos. Quando o RECONHECIMENTO falha, a linha
            # continua la — so nao sabemos de quem ela e. Nos dois casos a
            # identidade some de `presentes`, e sem esta checagem os dois viram
            # "saiu da party".
            #
            # A versao anterior congelava a saida sempre que QUALQUER linha
            # ocupada estivesse sem identidade. Parecia conservador e era: com
            # dois membros da party sem assinatura gravada, a condicao valia em
            # 100% dos frames e a deteccao de saida ficava COMPLETAMENTE
            # DESLIGADA. Medido: Kaus saia de verdade e `contador_saida` nem
            # chegava a incrementar uma vez.
            if linhas_agora >= interno.linhas_quando_visto:
                continue
            # Uma chave de POSICAO (`#linhaN`) so existe porque o
            # reconhecimento falhou naquele frame. Quando ele volta, ela some —
            # e anunciar isso como saida inventaria um membro que nunca
            # existiu, com o rotulo de quem ainda esta na tela.
            if ha_membro_nomeado and identidade.startswith("#linha"):
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
            interno.linhas_quando_visto = linhas_agora

            morto_agora = (
                linha.hp is not None
                and linha.hp <= self.ajustes.fracao_hp_considerada_zero
            )

            if interno.estado in (
                EstadoDoMembro.AUSENTE,
                EstadoDoMembro.DESCONHECIDO,
            ):
                if interno.contador_entrada == 0:
                    # Primeiro frame em que vemos esta identidade: e AGORA que
                    # a pergunta "a party cresceu?" tem resposta. Guardar em vez
                    # de reavaliar, porque a entrada so confirma depois de N
                    # leituras e ate la a janela ja parou de crescer.
                    interno.apareceu_com_crescimento = (
                        self._ultima_contagem_estavel is not None
                        and linhas_agora > self._ultima_contagem_estavel
                    )
                interno.contador_entrada += 1
                if interno.contador_entrada < self.ajustes.confirmacoes_para_entrada:
                    continue

                # AUSENTE -> presente e sempre uma entrada. DESCONHECIDO ->
                # presente so e entrada se o scanner ja passou do aquecimento;
                # antes disso e so a party que ja existia sendo descoberta.
                # Uma linha NAO reconhecida vira uma chave `#linhaN`. Se ela
                # aparecesse como "entrou", um piscar de reconhecimento criaria
                # um membro fantasma entrando na party — o espelho do falso
                # "saiu" que a mesma piscada causava.
                e_chave_de_posicao = identidade.startswith("#linha")

                # A PARTY WINDOW CRESCEU? Se nao cresceu, ninguem entrou.
                #
                # Mesmo raciocinio da saida, espelhado. Uma identidade nova
                # aparece por dois motivos bem diferentes: alguem entrou de
                # verdade (a janela ganha uma linha), ou o reconhecimento
                # passou a funcionar para quem ja estava la (a contagem nao
                # muda). Sem esta checagem, o segundo caso vira "Kaus entrou na
                # party" com o Kaus na party o tempo todo — foi o que apareceu
                # no arranque de uma sessao com a party parada.
                entrou_de_verdade = (
                    (interno.estado is EstadoDoMembro.AUSENTE or self._aquecido)
                    and not (e_chave_de_posicao and ha_membro_nomeado)
                    and interno.apareceu_com_crescimento
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

        self._ultima_contagem_estavel = linhas_agora

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
