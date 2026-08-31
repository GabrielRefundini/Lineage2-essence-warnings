"""O que fazer com UM frame. O núcleo testável do scanner.

POR QUE ESTE ARQUIVO EXISTE
===========================

O laço principal tinha 279 linhas e 20% de cobertura, contra 98% do
`rastreador`. Não era descuido: ele misturava duas responsabilidades, e uma
delas é intestável por natureza.

    CASCA (intestavel, e tudo bem)     NUCLEO (aqui)
    - montar a fonte de frames          - o que fazer com UM frame
    - while True                        - decidir, despachar, registrar
    - time.sleep                        - devolver o que aconteceu
    - sair no Ctrl-C

Enquanto tudo morava dentro do `while`, nenhum teste alcançava — não dá para
construir a situação sem construir o laço inteiro, e o laço precisa de um jogo
aberto.

OS TRÊS BUGS QUE ISSO DEIXOU PASSAR, todos em produção, todos no mesmo dia:

1. `destacar(texto)` chamado com um argumento só, numa função de três. O
   scanner morreria no instante em que fosse falar sobre um TvT — e o marcador
   "já avisei" é gravado ANTES, então o aviso sumiria em silêncio.

2. Um parâmetro `agora` usado para dois relógios incompatíveis: o `datetime` de
   parede que a agenda entende, e os segundos corridos que o limitador de taxa
   entende. `TypeError` no SEGUNDO tick — o primeiro passava porque a
   comparação nem acontecia.

3. Resposta de comando indo para o grupo em vez de para quem perguntou.
   Funcionou, no lugar errado, e pareceu quebrado.

Os três eram invisíveis para 420 testes, porque nenhum teste chamava o laço.
Agora chamam: `tick()` recebe um frame fabricado e devolve o que aconteceu.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import datetime

from .agenda import avisos_devidos, texto_do_aviso
# `Candidata` vem do `aprendiz` e nao o contrario: `aprendiz` fala `Assinatura`,
# `AcervoDeIdentidades` e stdlib, e NUNCA `sessao` (D-09, com portao AST em
# `tests/test_aprendiz.py`). Declarar a candidata aqui obrigaria o aprendiz a
# importar a sessao, e o ciclo fecharia no primeiro uso.
from .aprendiz import Candidata
from .console import moldurar
from .frames import Frame, SaudeDoFrame
from .loot import Designacao, nick_para_o_aviso
from .notificador import Categoria
from .presenca import fechar_e_narrar
from .rastreador import Evento
from .respawn import (
    anunciar_janelas,
    anunciar_nascimento,
    chave_do_nascimento,
)
from .visao import EstadoDaLinha, Observacao, extrair

log = logging.getLogger("l2scanner")


@dataclass
class ResultadoDoTick:
    """O que aconteceu com um frame. Existe para o teste poder AFIRMAR.

    Sem ele, verificar um tick significaria vasculhar log — e log é texto, que
    muda quando alguém melhora a redação. O resultado é estruturado pelo mesmo
    motivo que a chave do aviso é estruturada.
    """

    eventos: list[Evento] = field(default_factory=list)
    observacao: Observacao | None = None

    # Textos despachados, na ordem, com o destino. `None` de destino = as
    # conversas de aviso. É o que permite afirmar ONDE a mensagem saiu, que é
    # exatamente o que faltava quando o `.status` respondia no grupo errado.
    despachos: list[tuple[str, Categoria, str | None]] = field(default_factory=list)

    # Avisos de agenda que venceram neste tick.
    avisos: list[str] = field(default_factory=list)

    # A designacao de loot que ESTE tick consumiu (o horario do boss passou e
    # esta instancia venceu a corrida do registro). Estruturado, nao texto —
    # pelo mesmo motivo de `despachos` existir: teste afirma estrutura, nao
    # redacao.
    loot_consumado: Designacao | None = None

    # Tipos de aviso de manutencao que sairam neste tick. Estruturado, e nao
    # so texto, pelo mesmo motivo de `despachos` existir: teste afirma
    # estrutura, e a redacao muda toda vez que alguem a melhora.
    avisos_de_manutencao: list = field(default_factory=list)

    # Avisos de nascimento de boss emitidos neste tick, como pares
    # `(boss, origem)`. Estruturado para os testes afirmarem QUEM nasceu e por
    # qual sinal (chat, alvo ou ambos), sem depender da redacao do WhatsApp.
    #
    # O BOSS ENTRA NO PAR porque um tick pode entregar mais de um aviso: com
    # dois avisos, a origem sozinha nao diz mais de quem ela e.
    #
    # DESDE A FASE 3 ELE SIGNIFICA O QUE FOI ANUNCIADO, e nao o que foi
    # detectado. Nao e mudanca de contrato — o comentario acima ja dizia
    # "EMITIDOS neste tick" — e o que foi detectado e CALADO passou a ter campo
    # proprio logo abaixo.
    avisos_de_boss: list = field(default_factory=list)

    # As deteccoes de nascimento que este tick CALOU, como pares
    # `(boss, origem)`, porque o boss ja tinha sido anunciado neste episodio.
    #
    # ELE EXISTE PARA O SILENCIO DEIXAR RASTRO (T-03-05). Sem este campo e sem
    # a linha de log que o acompanha, o unico sintoma de uma supressao errada
    # seria o silencio — e ninguem percebe um alerta que nao chegou. Esse e
    # exatamente o modo de falha que a Fase 3 esta tentando NAO introduzir
    # enquanto conserta o oposto, entao ele nasce observavel.
    nascimentos_calados: list = field(default_factory=list)

    # As ANCORAS de nascimento que ESTE tick gravou, como pares
    # `(boss, origem)`. Estruturado e nao texto, no mesmo molde de
    # `avisos_de_boss`: o teste precisa afirmar QUE a contagem comecou e por
    # qual sinal, e casar isso com o nome do arquivo prenderia o teste a um
    # formato que a chave estruturada existe justamente para poder mudar.
    #
    # SO ENTRA QUANDO O MARCADOR FOI CRIADO POR ESTE PROCESSO. Com as duas
    # instancias do usuario sobre a mesma pasta, a que perde a corrida do
    # `O_CREAT|O_EXCL` nao gravou nada e nao pode dizer que gravou.
    ancoras_gravadas: list = field(default_factory=list)

    # Os avisos de janela de respawn deste tick, como pares `(boss, tipo)`.
    # Estruturado pela mesma razao de sempre: a redacao das quatro frases muda
    # toda vez que alguem a melhora, e a chave em disco nao muda junto.
    avisos_de_janela: list = field(default_factory=list)

    # As listas de presenca que ESTE tick fechou (`presenca.Fechamento`).
    # Estruturado, e nao so texto, pelo mesmo motivo de `despachos` existir: o
    # teste precisa afirmar QUEM confirmou e de QUAL ocorrencia, e casar isso
    # com a frase quebraria na primeira melhoria de redacao.
    #
    # LISTA VAZIA E O ESTADO NORMAL, e nao um erro: o boss nasce doze vezes por
    # dia e na maioria delas ninguem mandou `.join`. Zero confirmacoes produz
    # zero mensagem (D-12).
    presencas_fechadas: list = field(default_factory=list)

    # As assinaturas que ESTE tick gravou no acervo (`aprendiz.Aprendizado`).
    # Estruturado, e nao texto, pelo mesmo motivo de `despachos` existir: o
    # teste precisa afirmar QUE chave nasceu, de QUAL linha e com QUE confianca,
    # e casar isso com a redacao do log quebraria na primeira melhoria de frase.
    #
    # LISTA VAZIA E O ESTADO NORMAL, e nao um erro: na esmagadora maioria dos
    # ticks a party inteira ja e conhecida e nao ha nada a aprender.
    aprendizados: list = field(default_factory=list)

    # As recusas por instabilidade deste tick (`aprendiz.RecusaPorInstabilidade`),
    # com a DISTANCIA MEDIDA em celulas. E a peca de D-07: sem ela o desfecho de
    # um `celulas_toleradas` errado seria a feature nao acontecer, em silencio.
    #
    # LISTA VAZIA TAMBEM E O ESTADO NORMAL, pela mesma razao da vizinha.
    recusas_de_aprendizado: list = field(default_factory=list)

    # A extração falhou e o tick não concluiu nada sobre a party.
    falhou_ao_analisar: bool = False


class Sessao:
    """Estado de UMA execução do scanner, e o que fazer a cada frame.

    Tudo aqui eram variáveis locais do `laco_principal`. Movê-las para um
    objeto é o que torna a situação construível num teste.
    """

    def __init__(
        self,
        cal,
        rastreador,
        eventos_agendados,
        registro,
        silencio,
        despachante=None,
        leitor_de_comandos=None,
        gravador=None,
        fonte=None,
        ao_registrar=None,
        loot=None,
        manutencao=None,
        membros=(),
        mercado=None,
        bosses=None,
        regras_de_respawn=(),
        aprendiz=None,
    ) -> None:
        self.cal = cal
        self.rastreador = rastreador
        self.eventos_agendados = eventos_agendados
        self.registro = registro
        self.silencio = silencio
        self.despachante = despachante
        self.leitor_de_comandos = leitor_de_comandos
        self.gravador = gravador
        self.fonte = fonte
        # O registro de loot do Solo Boss. Default None mantem toda chamada
        # existente intacta — sem ele o tick simplesmente nao fala de loot.
        self.loot = loot
        # O vigia do banner de manutencao. Tambem default None, e pela mesma
        # razao: sem as bindings de OCR ou sem regiao calibrada o recurso se
        # desliga inteiro e nada mais no tick muda.
        self.manutencao = manutencao
        # Os `[[membro]]` do config.toml, so para a lista fechada sair com a
        # grafia que o usuario escreveu (D-10). Default vazio pela mesma razao
        # do `loot`: toda chamada existente continua valida, e sem o mapa o
        # tick simplesmente exibe a lista com a caixa do slug — cosmetico, e
        # nunca mudo.
        self.membros = membros
        # O `mercado_visao.RastreioDoPainel`. Default None pela mesma razao do
        # `loot` e do `manutencao`: sem calibracao de mercado o recurso fica
        # inteiro OFF e nada mais no tick muda.
        #
        # ELE MORA AQUI, e nao dentro de `extrair`, porque tem ESTADO: onde o
        # painel foi visto da ultima vez, e ha quantos ticks nao se varre. O
        # `extrair` e uma funcao pura por contrato — mesmo frame, mesma saida —
        # e essa pureza e o que torna o resto da leitura testavel sem laco.
        self.mercado = mercado
        # O `bosses.VigiaDeBosses`. Default None pela mesma razao do `loot`, do
        # `manutencao` e do `mercado`: sem bloco `[[boss]]` no config, sem
        # calibracao dos recortes ou sem OCR o recurso fica inteiro OFF, o tick
        # simplesmente nao fala de boss, e nada mais muda.
        self.bosses = bosses
        # Os `[[boss]]` do config.toml, so as REGRAS de respawn — a lista de
        # `bosses.Boss` que diz de quantas em quantas horas cada um nasce.
        #
        # KWARG SEPARADO DE `bosses`, E A SEPARACAO E A DECISAO. Aquele e o
        # `VigiaDeBosses`, que precisa de OCR e de recortes calibrados; este e
        # so a regra em horas. Os avisos de janela tem que existir MESMO com o
        # vigia desligado, porque a ancora ja esta em disco e a previsao
        # continua correta: amarrar a previsao ao vigia faria uma calibracao
        # quebrada apagar, em silencio, uma funcionalidade que so depende do
        # relogio e do disco.
        #
        # Default vazio pela mesma razao do `loot`, do `manutencao` e do
        # `mercado`: toda construcao de `Sessao` que ja existe continua valida
        # sem edicao, e sem regra nenhuma o tick simplesmente nao preve nada.
        self.regras_de_respawn = regras_de_respawn
        # O `aprendiz.Aprendiz`. Default None pela mesma razao do `loot`, do
        # `manutencao`, do `mercado` e do `bosses`: toda construcao de `Sessao`
        # que ja existe continua valida sem edicao, e sem ele o tick
        # simplesmente nao aprende nada e nada mais muda.
        self.aprendiz = aprendiz
        # Ja avisamos que o aprendiz explodiu? Uma vez por sessao, e so uma.
        #
        # Mesmo trilho dos dois vizinhos do mercado, e pela mesma razao: um
        # recurso ligado que nunca produz nada e degradacao SILENCIOSA, e
        # repetir o aviso a cada tick e a outra forma de nao ser lido.
        self._ja_avisou_da_falha_do_aprendiz = False
        # Ja avisamos que o regime da party virou? Uma vez, no instante da
        # virada. Sinalizador PROPRIO, e nao a flag do rastreador: quem decide
        # se o aviso ja saiu e esta sessao, e ler a decisao no objeto de outro
        # faria o aviso repetir se alguem mexesse na flag por fora.
        self._ja_avisou_da_virada_de_identidade = False
        # O ultimo retrato de recusas que ja foi para o log. A linha de resumo
        # so sai quando ele MUDA — ver `_registrar_recusas`.
        self._ultimo_retrato_de_recusas = None
        # Ja avisamos que o recorte da janela nao chega? Uma vez, e so uma.
        #
        # Um vigia ligado que nunca recebe pixels e degradacao SILENCIOSA — o
        # console simplesmente nunca fala do mercado e o usuario conclui que o
        # painel nunca abriu. Repetir o aviso a cada tick seria 1 linha por
        # segundo no `scanner.log`, que e a outra forma de nao ser lido.
        self._ja_avisou_do_mercado_sem_recorte = False
        # E a mesma pergunta para o OUTRO jeito de o mercado sumir calado: a
        # leitura explodindo. Um molde corrompido, uma janela num formato
        # inesperado ou um `cv2.error` persistente produzem o desfecho identico
        # -- console sem a linha do mercado, para sempre -- e isso saia so em
        # DEBUG, que nao esta ligado num farm normal. `NUNCA LEVANTA` esta
        # certo; ficar mudo nao.
        self._ja_avisou_da_falha_do_mercado = False
        # Chamado a cada mensagem despachada. A casca usa para logar; o teste
        # usa para nada — ele lê o `ResultadoDoTick`.
        self._ao_registrar = ao_registrar or (lambda *_: None)

        self.contagem = {estado: 0 for estado in SaudeDoFrame}
        self.saude_anterior = None
        self.total_eventos = 0
        self.ticks_cego = 0
        # Ha quantas leituras seguidas cada linha esta OCUPADA e SEM NOME.
        #
        # Existe porque a falha de identidade era estruturalmente invisivel. O
        # scanner sempre soube contar cegueira de CAPTURA (`ticks_cego`) e
        # reclamar dela, mas nunca soube contar "estou vendo a linha e nao faco
        # ideia de quem esta nela". Em 2026-08-25 isso durou DUAS HORAS, e o
        # usuario so descobriu por causa de alertas errados que vieram depois.
        #
        # Chaveado por linha, e nao um contador global, para que o aviso possa
        # dizer QUAL linha — e para que a piscada de uma linha nao zere a conta
        # de outra que esta parada de verdade.
        self.ticks_sem_reconhecer: dict[int, int] = {}
        self.ultima_observacao: Observacao | None = None

    # -- despacho -----------------------------------------------------------

    def _despachar(
        self,
        texto: str,
        categoria: Categoria = Categoria.NORMAL,
        conversa_alvo: str | None = None,
        resultado: ResultadoDoTick | None = None,
    ) -> None:
        """Um único ponto de saída, e é de propósito.

        Com o despacho espalhado por cinco lugares do laço, cada um podia
        errar o destino sozinho — e um errou. Aqui todo despacho passa pelo
        mesmo caminho e cai no resultado, onde o teste consegue ver.
        """
        if resultado is not None:
            resultado.despachos.append((texto, categoria, conversa_alvo))
        if self.despachante:
            self.despachante.despachar(texto, categoria, conversa_alvo)

    # -- o tick -------------------------------------------------------------

    def tick(self, frame: Frame, momento: float | None = None) -> ResultadoDoTick:
        """Processa UM frame. Sem dormir, sem capturar, sem laço.

        `momento` vem do FRAME quando existe — num replay é o que faz uma
        sessão de uma hora produzir os mesmos eventos em trinta segundos.
        """
        resultado = ResultadoDoTick()

        self.contagem[frame.saude] += 1
        if frame.saude is not self.saude_anterior:
            self.saude_anterior = frame.saude

        if self.gravador:
            self.gravador.gravar(frame, momento or 0.0)

        if momento is None:
            momento = frame.momento if frame.momento is not None else 0.0
        agora = datetime.fromtimestamp(momento)

        # A AGENDA VEM ANTES DA EXTRACAO. Ela não depende de um único pixel, e
        # deixá-la depois faria um erro de leitura engolir o lembrete de TvT
        # junto — o que contradiz a razão inteira de a agenda existir.
        self._processar_agenda(agora, resultado)

        # PELO MESMO MOTIVO QUE A AGENDA VEM ANTES: o `except` do bloco abaixo
        # retorna cedo, entao um erro de leitura da party engoliria o aviso de
        # manutencao junto — e manutencao e justamente o que costuma DERRUBAR a
        # leitura da party.
        self._processar_manutencao(agora, frame, resultado)
        self._processar_bosses(frame, agora, resultado)

        # ANCORAR ANTES DE ANUNCIAR, e a ordem e a propria regra de D-20 valendo
        # dentro de UM tick — nao so entre ticks.
        #
        # Um nascimento novo e a janela do ciclo anterior podem cair no mesmo
        # tick (o boss de 6h nascendo de novo as 20:30, quando o aviso de
        # abertura do ciclo das 14:30 vence). Com a ancora nova ja em disco,
        # `anunciar_janelas` monta as ancoras e enxerga so a mais recente: a
        # chave velha nao e gerada e o aviso obsoleto nao sai. Invertidas, as
        # duas linhas anunciariam uma janela que o proprio tick acabou de
        # invalidar.
        #
        # Fica ANTES da extracao pela mesma razao que a agenda: nao depende de
        # um unico pixel, e o `except` do bloco abaixo retorna cedo — um erro
        # de leitura da party engoliria a previsao junto.
        self._processar_janelas(agora, resultado)

        try:
            observacao = extrair(frame, self.cal)
            if self.fonte is not None and hasattr(self.fonte, "estado_do_cliente"):
                observacao = replace(
                    observacao, estado_do_cliente=self.fonte.estado_do_cliente()
                )
            eventos = self.rastreador.observar(observacao, momento)
            self.ultima_observacao = observacao
        except Exception:
            resultado.falhou_ao_analisar = True
            return resultado

        # O MERCADO ENTRA DEPOIS DO RASTREADOR JA TER DECIDIDO, de proposito.
        #
        # Nao e ordem estetica: nesta posicao e IMPOSSIVEL o sinal do mercado
        # influenciar a lista de eventos deste tick, porque ela ja existe. A
        # protecao contra repetir o incidente 27x fica na forma do codigo, e nao
        # numa regra que alguem precisa lembrar de seguir.
        observacao = replace(
            observacao, mercado_aberto_aparente=self._olhar_o_mercado(frame)
        )
        self.ultima_observacao = observacao

        resultado.observacao = observacao

        if not observacao.ui_visivel:
            self.ticks_cego += 1
        else:
            self.ticks_cego = 0
            self._contar_linhas_sem_nome(observacao)

        # O APRENDIZADO ENTRA DEPOIS DO RASTREADOR JA TER DECIDIDO, e pela mesma
        # razao escrita no bloco do mercado logo acima: nesta posicao e
        # ESTRUTURALMENTE IMPOSSIVEL o aprendizado influenciar a lista de
        # eventos deste tick, porque ela ja existe.
        #
        # O preco disso esta escrito e e aceito: nas N leituras ate a primeira
        # assinatura existir, `assinaturas_configuradas` ainda e `False`, e uma
        # instalacao sem assinatura nenhuma continua, nessa janela, com o
        # comportamento de hoje. Esta fase ENCURTA para N leituras uma janela
        # que hoje dura a sessao inteira; ela nao a fecha.
        self._aprender(observacao, resultado)

        for evento in eventos:
            self.total_eventos += 1
            resultado.eventos.append(evento)
            self._ao_registrar(evento)
            self._despachar(texto_do_evento(evento), resultado=resultado)

        return resultado

    def _processar_bosses(
        self, frame: Frame, agora: datetime, resultado: ResultadoDoTick
    ) -> None:
        """Le chat/alvo fora do rastreador: e aviso, nunca automacao de jogo.

        ITERA UMA LISTA porque um tick pode entregar mais de um aviso: chat e
        alvo mostrando bosses DIFERENTES produzem um alerta para cada
        (RECO-05). Cada um passa pelo `_despachar`, que e o funil unico de
        saida — e por isso os dois aparecem em `resultado.despachos`.

        AS CHAVES DE `extras` CONTINUAM `tiat_chat` E `tiat_alvo`. Renomea-las
        seria degradacao silenciosa: `Calibracao.de_dict` le as chaves de mesmo
        nome com `dados.get(...)` e devolve `None` quando faltam, entao todo
        `calibration.json` ja existente na maquina do usuario passaria a subir
        com a vigilancia de boss desligada, sem uma linha de aviso.
        """
        if self.bosses is None:
            return
        avisos = self.bosses.avaliar(
            frame.extras.get("tiat_chat"), frame.extras.get("tiat_alvo"), agora
        )
        for aviso in avisos:
            # PRIMEIRO A ANCORA, SEMPRE, FORA DE QUALQUER CONDICAO LIGADA AO
            # ANUNCIO. Isto e D-27: a ancoragem nao muda de comportamento nesta
            # fase, e continua acontecendo inclusive quando o anuncio e calado.
            #
            # A ORDEM NAO E ESTETICA. A chave do episodio e calculada a partir
            # das ancoras que estao EM DISCO, e a ancora desta deteccao precisa
            # estar la antes. Invertida, a PRIMEIRA deteccao de um episodio
            # cairia no caminho do episodio vazio, as duas instancias — ticando
            # em minutos diferentes — produziriam duas chaves e duas mensagens,
            # e o defeito de campo voltaria inteiro. Com uma instancia so, a
            # ordem e indiferente e todo o resto continuaria verde; por isso o
            # portao de `tests/test_anuncio_unico.py` afirma a POSICAO por AST.
            #
            # ESTE E O UNICO SITIO DE ESCRITA DE ANCORA DO PROJETO, e a
            # assimetria com os avisos de janela e o ponto que precisa ficar
            # escrito. ANCORAR exige pixels, e so o laco principal tem pixels;
            # ANUNCIAR exige apenas o relogio e o disco, e por isso o anuncio
            # tem DOIS sitios (aqui e o `--so-agenda`) e a ancora tem UM. Quem
            # for procurar a simetria vai concluir que falta uma escrita no
            # `--so-agenda`: ela nao falta, e por-la la faria um modo sem tela
            # inventar nascimentos.
            #
            # O CUSTO DE D-15, MEDIDO EM CAMPO E ACEITO PELO USUARIO: o alvo
            # REARMA quando ele desmarca e remarca o boss, entao um `Tiat
            # South` retomado as 15h grava uma ancora nova sobre a mesma
            # criatura que ja estava viva as 14h30, e a conta reinicia. Foi
            # escolha por COBERTURA, com o preco apresentado; a mitigacao e
            # D-16 — a mensagem cita que a origem foi o alvo, e quem le julga.
            # O que a Fase 3 mudou foi o ANUNCIO, e nao esta escrita.
            if self.registro.registrar_nascimento(
                chave_do_nascimento(aviso.boss, agora, aviso.origem)
            ):
                resultado.ancoras_gravadas.append((aviso.boss, aviso.origem))

            # DEPOIS O ANUNCIO, e a decisao inteira mora em
            # `respawn.anunciar_nascimento` pela mesma razao que a decisao da
            # janela mora em `anunciar_janelas`: uma copia aqui divergiria da
            # de la no primeiro ajuste.
            if not anunciar_nascimento(
                self.registro, aviso.boss, agora, self.regras_de_respawn
            ):
                resultado.nascimentos_calados.append(
                    (aviso.boss, aviso.origem)
                )
                log.info(
                    "%s calado: este nascimento ja foi anunciado neste "
                    "episodio (origem desta deteccao: %s)",
                    aviso.boss,
                    aviso.origem.value,
                )
                continue

            resultado.avisos_de_boss.append((aviso.boss, aviso.origem))
            # Nascimento e alvo novo sao urgentes e devem atravessar o silencio
            # de TvT: um boss nascendo durante o Prime e exatamente a
            # informacao que ninguem quer perder.
            self._despachar(aviso.texto, Categoria.SEMPRE, resultado=resultado)

    def _processar_janelas(self, agora: datetime, resultado: ResultadoDoTick) -> None:
        """As janelas de respawn que venceram. Sempre categoria SEMPRE.

        A SEQUENCIA INTEIRA MORA EM `respawn.anunciar_janelas`, e nao aqui,
        pela mesma razao que o fechamento de lista mora em
        `presenca.fechar_e_narrar`: o plano 02-02 leva o mesmo anuncio ao
        `--so-agenda`, e as duas copias escreveriam na MESMA `.agenda/` e
        falariam no MESMO grupo. Aqui fica so o que e do tick — o resultado, a
        moldura e o despacho.

        `Categoria.SEMPRE` (D-23): um boss nascendo durante o Prime e
        exatamente a informacao que ninguem quer perder, que e a mesma razao ja
        escrita em `_processar_bosses`.
        """
        if not self.regras_de_respawn:
            return

        for aviso, texto in anunciar_janelas(
            self.registro, self.regras_de_respawn, agora
        ):
            resultado.avisos_de_janela.append((aviso.boss, aviso.tipo))
            # CRU no resultado, MOLDURADO no despacho — o console monta a
            # propria moldura (com cor) a partir de `avisos`; moldurar aqui
            # tambem faria o bloco sair dentro de outro bloco na tela.
            resultado.avisos.append(texto)
            self._despachar(
                moldurar(texto, agora.strftime("%H:%M")),
                Categoria.SEMPRE,
                resultado=resultado,
            )

    def _olhar_o_mercado(self, frame: Frame) -> bool | None:
        """O painel do World Exchange esta aberto? `None` = ninguem olhou.

        SO PRODUZ TEXTO. O retorno vai para `Observacao.mercado_aberto_aparente`
        e de la para o console — nenhuma decisao de alerta sai daqui nesta fase.
        Ver o comentario do campo em `visao.py` e o bloco
        `<detc01_reconciliation>` do `01-04-PLAN.md`.

        O extra e a JANELA INTEIRA e nao um retangulo fixo porque o painel ANDA:
        entre dois frames do proprio incidente 27x ele apareceu 181 px a
        esquerda e 143 px abaixo, com a mesma arte casando 0.9996. Um recorte
        fixo mediria grama na maior parte dos frames.

        NUNCA LEVANTA. Um campo de mostrar nao pode custar a deteccao de morte:
        se o molde estiver corrompido ou a janela vier num formato inesperado, o
        certo e o console ficar sem a linha do mercado — e nao o tick inteiro
        virar `falhou_ao_analisar`, que apagaria a party junto.
        """
        if self.mercado is None:
            return None

        recorte = frame.extras.get("mercado_janela")
        if recorte is None:
            # `captura_janela._extra_para_janela` devolve `None` quando a regiao
            # nao cabe inteira na janela — falha FECHADA que ja existe. Inventar
            # `False` aqui faria o console afirmar "mercado fechado" sobre
            # pixels que ninguem capturou.
            if not self._ja_avisou_do_mercado_sem_recorte:
                self._ja_avisou_do_mercado_sem_recorte = True
                log.warning(
                    "Mercado calibrado, mas o recorte da janela nao esta "
                    "chegando: a janela do jogo provavelmente mudou de tamanho "
                    "desde a calibracao. Rode calibrar-mercado.bat. Todo o "
                    "resto do scanner continua igual."
                )
            return None

        try:
            return bool(self.mercado.observar(recorte).aberto)
        except Exception:
            # MESMO TRILHO DO VIZINHO DEZ LINHAS ACIMA: um WARNING uma vez,
            # DEBUG nos demais. So `log.debug` deixava esta falha invisivel num
            # farm normal, e o desfecho e identico ao do recorte ausente -- "o
            # console simplesmente nunca fala do mercado e o usuario conclui que
            # o painel nunca abriu". Um molde corrompido nao e um tropeco de um
            # tick: ele vai falhar tambem nos proximos, e o texto diz isso.
            if not self._ja_avisou_da_falha_do_mercado:
                self._ja_avisou_da_falha_do_mercado = True
                log.warning(
                    "Leitura do mercado falhando neste frame e provavelmente "
                    "nos proximos (molde corrompido ou janela em formato "
                    "inesperado). Rode calibrar-mercado.bat. Todo o resto do "
                    "scanner continua igual.",
                    exc_info=True,
                )
            else:
                log.debug("Leitura do mercado falhou neste tick", exc_info=True)
            return None

    # -- o aprendizado (Fase 2 do workstream identidade) --------------------

    def _candidatas_para_aprender(self, observacao: Observacao) -> tuple:
        """As linhas que o scanner esta vendo e nao sabe de quem sao (D-01).

        A CONDICAO E `linha.nome is None`, E NUNCA `not linha.nome`.

        `Casamento.nome` de uma entrada anonima do acervo e a string VAZIA, e
        nao `None`. `""` significa "reconheci esta pessoa e ninguem a batizou";
        `None` significa "nao sei quem e". Escrever `not linha.nome` colapsaria
        os dois: toda pessoa ja aprendida voltaria a ser candidata em todo tick,
        o recorte dela mudaria por uma celula aqui e ali, e o acervo ganharia
        uma entrada nova a cada N ticks — para a MESMA pessoa. E o inchaco que o
        APRE-04 existe para proibir, escrito num operador.

        `ui_visivel` E O PORTAO CERTO, e nao um portao a mais. Ele ja cai quando
        a moldura da barra some (outra janela do jogo por cima) e quando a party
        window aparece sem nenhum icone, que sao exatamente os dois casos em que
        os pixels da linha nao sao a pessoa. Aprender sob cegueira gravaria a
        janela do navegador como se fosse gente, e a gravacao e IRREVERSIVEL: o
        acervo nao tem comando de esquecer no v1.

        A leitura do dicionario de mascaras parte SEMPRE de uma linha de
        `observacao.linhas`, e nunca itera as chaves do dicionario: ele pode ter
        mais chaves do que ha linhas ocupadas, porque `_truncar_no_primeiro_vao`
        roda depois da coleta dos recortes. Ver o comentario do campo em
        `visao.py`.

        Metodo PURO: nao grava, nao registra e nao decide nada. So diz quem
        pode ser considerado.
        """
        if not observacao.ui_visivel:
            return ()

        candidatas = []
        for linha in observacao.linhas:
            if linha.estado is not EstadoDaLinha.COM_MEMBRO:
                continue
            if linha.nome is not None:
                continue
            mascara = observacao.mascaras_de_nome.get(linha.indice)
            if mascara is None:
                continue
            candidatas.append(
                Candidata(
                    indice=linha.indice,
                    mascara=mascara,
                    confianca=linha.confianca_do_nome,
                )
            )
        return tuple(candidatas)

    def _aprender(self, observacao: Observacao, resultado: ResultadoDoTick) -> None:
        """Grava a assinatura de quem ficou parado tempo suficiente.

        SAI CEDO SOB CEGUEIRA, e o portao repete de proposito o que
        `_candidatas_para_aprender` ja faz: nao chamar o aprendiz e o que CONGELA
        a contagem em vez de zera-la, exatamente como `_contar_linhas_sem_nome`.
        Nao dava para ver, entao nao da para afirmar nada — nem que reconheceu,
        nem que deixou de reconhecer. O congelamento e seguro justamente porque
        a contagem e por CONTEUDO: se a pessoa mudou durante a cegueira, a
        mascara muda e o vigia cai na primeira leitura visivel.

        NUNCA LEVANTA, no precedente ja escrito para o mercado: uma falha aqui
        nao pode derrubar o farm, e tambem nao pode ficar muda para sempre.

        NADA E DESPACHADO. Esta fase e CALADA por decisao de escopo: perguntar e
        a Fase 3 inteira (BATI-01).
        """
        if self.aprendiz is None or not observacao.ui_visivel:
            return

        try:
            saida = self.aprendiz.observar(
                self._candidatas_para_aprender(observacao)
            )
        except Exception:
            if not self._ja_avisou_da_falha_do_aprendiz:
                self._ja_avisou_da_falha_do_aprendiz = True
                log.warning(
                    "O aprendizado de identidades falhou neste frame e "
                    "provavelmente nos proximos. Nenhuma assinatura nova sera "
                    "gravada. Todo o resto do scanner continua igual.",
                    exc_info=True,
                )
            else:
                log.debug("Aprendizado falhou neste tick", exc_info=True)
            return

        resultado.aprendizados.extend(saida.aprendizados)
        resultado.recusas_de_aprendizado.extend(saida.recusas)

        for aprendizado in saida.aprendizados:
            if aprendizado.desfecho not in ("criado", "ja_existia"):
                continue

            # O `log.info` DO APRENDIZADO SAI ANTES DO `log.warning` DA VIRADA,
            # e a ordem nao e estetica: as duas linhas caem no MESMO tick, e com
            # o aviso primeiro o `scanner.log` da primeira sessao real anuncia a
            # mudanca de regime da party ANTES de dizer o que a causou.
            #
            # O PIXEL e a CONFIANCA nao sao enfeite. O pixel torna
            # diagnosticavel, depois, um aprendizado de recorte contaminado
            # (T-02-07, aceito e registrado). A confianca torna diagnosticavel
            # uma SEGUNDA entrada da MESMA pessoa nascida abaixo do limiar, que
            # D-02 nao guarda (T-02-18): uma sequencia de aprendizados com
            # confianca em torno de 0.70 e a assinatura desse caso, e sem o
            # numero no log ele e invisivel.
            log.info(
                "Aprendi uma assinatura nova (%s) da linha %d: chave %s, "
                "%d pixels de texto, confianca %.4f. Ela entra sem nome; "
                "a linha continua aparecendo como Membro %d.",
                aprendizado.desfecho,
                aprendizado.indice + 1,
                aprendizado.chave,
                aprendizado.assinatura.pixels_de_texto,
                aprendizado.confianca,
                aprendizado.indice + 1,
            )

            # A LISTA VIVA (D-03). Sem esta insercao a mesma pessoa voltaria a
            # ser candidata no tick seguinte, o recorte mudaria por uma celula
            # aqui e ali, e o acervo ganharia uma entrada nova a cada N ticks
            # para a MESMA pessoa — o inchaco que o APRE-04 proibe. Com ela na
            # lista, o proximo `extrair` casa ~1.000 contra ela mesma e a linha
            # deixa de ser candidata por D-02.
            self.cal.assinaturas.append(aprendizado.assinatura)

            # O ELO QUE FALTAVA, e sem ele esta fase entrega o defeito que a
            # Fase 1 acabou de consertar, por outra porta: numa instalacao que
            # comecou sem assinatura nenhuma, `_rotular` continuaria caindo em
            # `nome_de(indice)`, e a pessoa que o scanner acabou de aprender
            # como ANONIMA seria anunciada com o nome de OUTRA.
            virou = not self.rastreador.assinaturas_configuradas
            self.rastreador.assinaturas_configuradas = True
            if virou and not self._ja_avisou_da_virada_de_identidade:
                # A VIRADA NAO PODE SER MUDA. Ela muda o comportamento da party
                # INTEIRA, e nao so o da linha aprendida: a partir daqui
                # `_rotular` devolve "Membro N" para toda linha nao reconhecida,
                # `_e_so_uma_posicao` VETA MORREU e RESSUSCITOU para toda
                # identidade `#linhaN`, e a purga da chave posicional passa a
                # valer. Para quem nunca calibrou assinatura mas preencheu a
                # lista de nomes, o efeito visivel e o scanner PARAR de anunciar
                # mortes por nome no meio do farm.
                #
                # A virada continua sendo a decisao certa — silencio vence
                # mentira plausivel, e e a mesma regra que ja vale hoje para
                # qualquer instalacao que tenha uma assinatura — mas o usuario
                # nao pode descobri-la pela ausencia de alertas.
                self._ja_avisou_da_virada_de_identidade = True
                log.warning(
                    "A partir de agora ha identidade visual em jogo: o scanner "
                    "gravou a primeira assinatura sozinho. Linhas que ele nao "
                    "reconhecer passam a aparecer como Membro N, em vez de "
                    "pegar o nome da lista por posicao, e nenhum alerta sai em "
                    "nome delas. Isso vale para a party inteira, e nao so para "
                    "a linha aprendida."
                )

    def _contar_linhas_sem_nome(self, observacao: Observacao) -> None:
        """Quanto tempo cada linha ocupada esta sem ser reconhecida.

        So e chamado com a UI visivel. Cegueira CONGELA a conta, pela mesma
        razao que congela todos os outros contadores do rastreador: nao dava
        para ver, entao nao da para afirmar nada — nem que reconheceu, nem que
        deixou de reconhecer.
        """
        for linha in observacao.linhas:
            ocupada = linha.estado is EstadoDaLinha.COM_MEMBRO
            if ocupada and linha.nome is None:
                self.ticks_sem_reconhecer[linha.indice] = (
                    self.ticks_sem_reconhecer.get(linha.indice, 0) + 1
                )
            else:
                # Reconheceu, ou a linha esvaziou: a conta recomeca do zero.
                self.ticks_sem_reconhecer.pop(linha.indice, None)

    def _processar_agenda(self, agora: datetime, resultado: ResultadoDoTick) -> None:
        """Fim de silêncio e avisos que venceram. Sempre categoria SEMPRE.

        Os lembretes ATRAVESSAM o silêncio: de segunda a quinta o aviso do TvT
        das 21h40 cai dentro do silêncio do Prime, e sem isso a funcionalidade
        se anularia sozinha.
        """
        encerrou = self.silencio.atualizar(agora)
        if encerrou:
            resultado.avisos.append(encerrou)
            self._despachar(encerrou, Categoria.SEMPRE, resultado=resultado)

        # Lida UMA vez, antes do loop: todos os avisos deste tick enxergam a
        # mesma designacao, e um json trocado no meio nao produz avisos
        # contraditorios no mesmo segundo.
        designacao = self.loot.designacao() if self.loot else None

        for aviso in avisos_devidos(
            agora,
            self.eventos_agendados,
            self.registro.enviados(),
            # O que o usuario desligou por `/desativarsoloboss`. Lido do DISCO
            # a cada tick, e nao guardado na sessao: o comando pode chegar na
            # OUTRA instancia, e um cache aqui faria este processo continuar
            # anunciando o boss que o outro acabou de calar.
            eventos_calados=self.registro.eventos_calados(),
        ):
            if not self.registro.marcar(aviso.chave):
                continue
            texto = texto_do_aviso(aviso, nick_para_o_aviso(aviso, designacao))
            resultado.avisos.append(texto)
            # CRU no resultado, MOLDURADO no despacho. O console monta a
            # propria moldura (com cor) a partir de `avisos`; moldurar aqui
            # tambem faria o bloco sair dentro de outro bloco na tela.
            self._despachar(
                moldurar(texto, agora.strftime("%H:%M")),
                Categoria.SEMPRE,
                resultado=resultado,
            )

        # DEPOIS dos avisos, de proposito. A ordem e indiferente no relogio —
        # o aviso ANTES vence 10 min antes do alvo e o consumo so dispara no
        # alvo — mas fixa-la torna o tick deterministico para o teste.
        if self.loot:
            resultado.loot_consumado = self.loot.consumir(agora)

        # E o fechamento por ULTIMO, pela mesma razao que o loot vem depois dos
        # avisos: a ordem e indiferente no relogio, mas fixa-la torna o tick
        # deterministico. A posicao especifica nao e arbitraria — no plano
        # 10-05 o fechamento passa a depender do que o consumo de loot acabou
        # de registrar, entao ele tem que enxergar o disco ja atualizado.
        #
        # NAO passa por `avisos_devidos` (D-12): o Solo Boss do usuario tem
        # `avisar_no_horario = false`, e pendurar o fechamento no aviso de
        # AGORA o obrigaria a religar as doze mensagens diarias que desligou.
        #
        # A SEQUENCIA INTEIRA MORA EM `presenca.fechar_e_narrar`, e nao aqui:
        # ela estava duplicada literalmente com `__main__._fechar_listas_de_
        # presenca` (WR-08). As duas escrevem no MESMO `.agenda/` e falam no
        # MESMO grupo, e o usuario roda os dois modos — uma correcao aplicada
        # so de um lado faria os dois anunciarem coisas diferentes sobre o
        # mesmo boss. Aqui fica so o que e do tick: o resultado e o despacho.
        for fechamento, texto in fechar_e_narrar(
            self.registro,
            self.eventos_agendados,
            agora,
            self.membros,
            self.loot,
        ):
            resultado.presencas_fechadas.append(fechamento)
            resultado.avisos.append(texto)
            # CRU no resultado, MOLDURADO no despacho — a mesma separacao de
            # tres linhas acima.
            #
            # `Categoria.SEMPRE` e nao `NORMAL`: a lista fechada e organizacao
            # de party, e nao alerta de morte. Silencia-la dentro de uma janela
            # de Prime esconderia justamente a mensagem que diz quem esta indo.
            self._despachar(
                moldurar(texto, agora.strftime("%H:%M")),
                Categoria.SEMPRE,
                resultado=resultado,
            )


    def _processar_manutencao(
        self, agora: datetime, frame: Frame, resultado: ResultadoDoTick
    ) -> None:
        """O banner de manutencao vira aviso no grupo. Sempre categoria SEMPRE.

        `Categoria.SEMPRE` porque manutencao durante TvT ou Prime e exatamente
        quando o silencio esta ligado — e e quando mais importa saber (D-08).

        O `marcar` E a decisao de despachar, nunca uma checagem anterior: e o
        mesmo O_CREAT|O_EXCL que ja impede as duas instancias do usuario de
        mandarem o aviso de TvT em dobro.
        """
        if self.manutencao is None:
            return

        for aviso in self.manutencao.avaliar(
            lambda: frame.extras.get("banner_manutencao"), agora
        ):
            if not self.registro.marcar(aviso.chave):
                continue
            # CRU no resultado, MOLDURADO no despacho — o console monta a
            # propria moldura a partir de `avisos` (D-11).
            resultado.avisos.append(aviso.texto)
            resultado.avisos_de_manutencao.append(aviso.tipo)
            self._despachar(
                moldurar(aviso.texto, agora.strftime("%H:%M")),
                Categoria.SEMPRE,
                resultado=resultado,
            )


def texto_do_evento(evento: Evento) -> str:
    """Import tardio para não criar ciclo com o notificador."""
    from .notificador import formatar

    return formatar(evento)
