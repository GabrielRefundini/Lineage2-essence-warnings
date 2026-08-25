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

from dataclasses import dataclass, field, replace
from datetime import datetime

from .agenda import avisos_devidos, texto_do_aviso
from .console import moldurar
from .frames import Frame, SaudeDoFrame
from .loot import Designacao, nick_para_o_aviso
from .notificador import Categoria
from .rastreador import Evento
from .visao import EstadoDaLinha, Observacao, extrair


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

        resultado.observacao = observacao

        if not observacao.ui_visivel:
            self.ticks_cego += 1
        else:
            self.ticks_cego = 0
            self._contar_linhas_sem_nome(observacao)

        for evento in eventos:
            self.total_eventos += 1
            resultado.eventos.append(evento)
            self._ao_registrar(evento)
            self._despachar(texto_do_evento(evento), resultado=resultado)

        return resultado

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
            agora, self.eventos_agendados, self.registro.enviados()
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
