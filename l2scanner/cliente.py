"""Em que estado o CLIENTE esta — jogando, na tela de login, ou desconectado.

Isto responde a pergunta que faltava. Ate agora o scanner so sabia dizer "nao
consigo ler a party window", e essa frase cobria coisas muito diferentes: o
jogo coberto por uma janela, um menu aberto por cima, o servidor caindo, e o
cliente de volta na tela de login. As tres ultimas sao a mesma coisa para quem
esta no WhatsApp — *o jogo caiu* — e nenhuma delas era dita.

Foi exatamente o que aconteceu na sessao de 2026-08-24: o servidor entrou em
manutencao, o cliente caiu, e o scanner passou 90 s e depois 5 min repetindo
"sem visao da party" sem nunca dizer o motivo. Cego com causa conhecida nao e
cegueira, e um evento.

DOIS SINAIS, DE FORCAS BEM DIFERENTES:

1. **O TITULO DA JANELA** decide "tela de login". Jogando, o cliente chama a
   janela de `Yazalaque - XM Essence`; na tela de login ela vira `XM Essence`,
   sem o prefixo do personagem. Isto e texto do proprio Windows: nao tem
   limiar, nao tem HSV, nao depende de calibracao e nao quebra quando o usuario
   muda a resolucao. E o sinal mais confiavel do projeto inteiro.

   Verificado ao vivo com as duas instancias do usuario abertas ao mesmo tempo:
   `Faerlina - XM Essence` (jogando) e `XM Essence` (na tela de login).

2. **UM TEMPLATE** decide "dialogo de desconexao". Esse precisa de pixels
   porque o cliente continua se chamando `Faerlina - XM Essence` com o dialogo
   aberto — pela janela, ele ainda esta no jogo. E o caso MAIS importante dos
   dois: se voce esta AFK quando cai, o dialogo fica parado na tela para sempre
   e o titulo nunca muda. Sem isto, AFK + desconectado e silencio permanente.

ARMADILHA MEDIDA, NAO SUPOSTA: `windows-capture` casa `window_name` por
SUBSTRING. Pedir `XM Essence` devolve o frame de `Faerlina - XM Essence`, que e
outra janela e outro personagem. Por isso a tela de login nunca e detectada
capturando "a janela de login" — ela e detectada relendo o titulo do hwnd que
ja temos.
"""

from __future__ import annotations

import ctypes
from enum import Enum
from pathlib import Path

import cv2
import numpy as np

_user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None

# Sufixo do titulo da janela do cliente, sem personagem nenhum.
NOME_DO_CLIENTE = "XM Essence"

# O separador que o cliente poe entre o personagem e o nome do jogo.
SEPARADOR = " - "

# Onde mora o template do dialogo. Fica junto do pacote e nao na calibracao
# porque nao e uma medida da tela DESTE usuario: e um pedaco da UI do cliente,
# igual em qualquer maquina na mesma resolucao de UI.
CAMINHO_DO_TEMPLATE = Path(__file__).parent / "recursos" / "dialogo_desconexao.png"


class EstadoDoCliente(Enum):
    """O que o cliente esta fazendo, do ponto de vista do scanner."""

    EM_JOGO = "em_jogo"
    TELA_DE_LOGIN = "tela_de_login"
    DESCONECTADO = "desconectado"

    # Nao deu para decidir (sem handle, sem template carregado). Nunca vira
    # evento: na duvida o scanner nao inventa nada.
    DESCONHECIDO = "desconhecido"


def titulo_da_janela(hwnd: int) -> str | None:
    """Le o titulo ATUAL da janela. None se ela nao existe mais.

    Relido a cada frame de proposito. O titulo muda embaixo de nos quando o
    cliente volta para a tela de login, e e justamente essa mudanca que
    queremos ver — guardar o titulo do arranque perderia o evento inteiro.
    """
    if _user32 is None or not hwnd:
        return None
    if not _user32.IsWindow(hwnd):
        return None
    tamanho = _user32.GetWindowTextLengthW(hwnd)
    if tamanho <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(tamanho + 1)
    _user32.GetWindowTextW(hwnd, buffer, tamanho + 1)
    return buffer.value


def esta_na_tela_de_login(titulo: str | None) -> bool:
    """O titulo diz que o cliente esta na tela de login?

    Jogando : "Yazalaque - XM Essence"  -> tem prefixo de personagem
    Login   : "XM Essence"              -> nao tem

    Comparacao exata contra o nome do cliente, e nao "termina com": um
    personagem chamado `XM Essence` e impossivel (o cliente nao aceita espaco
    em nome), mas `endswith` tambem casaria `Faerlina - XM Essence`, que e o
    oposto do que queremos.
    """
    if titulo is None:
        return False
    limpo = titulo.strip()
    if not limpo:
        return False
    return limpo == NOME_DO_CLIENTE


def nome_do_personagem(titulo: str | None) -> str | None:
    """`Yazalaque - XM Essence` -> `Yazalaque`. None se nao houver."""
    if not titulo or SEPARADOR not in titulo:
        return None
    personagem = titulo.rsplit(SEPARADOR, 1)[0].strip()
    return personagem or None


def carregar_template(caminho: Path | None = None) -> np.ndarray | None:
    """Carrega o template do dialogo. None quando ele nao foi gravado ainda."""
    alvo = caminho or CAMINHO_DO_TEMPLATE
    if not alvo.exists():
        return None
    return cv2.imread(str(alvo))


# Faixa da janela onde o dialogo modal pode aparecer, em FRACOES da janela.
#
# O dialogo e modal e CENTRADO — medido no frame real: o centro dele cai em
# x=860 numa janela de 1720, ou seja, exatamente no meio. Fracoes em vez de
# pixels para sobreviver a mudanca de resolucao.
#
# Isto nao e microotimizacao. Varrer a janela inteira custava 121 ms POR FRAME,
# medido — 12% do orcamento de um tick a 1 Hz, gastos continuamente numa maquina
# que tambem roda dois clientes de Lineage 2, para procurar um evento que
# acontece uma vez por manutencao.
#
# A margem e generosa de proposito: o template real ocupa x entre 0.41 e 0.59 e
# y entre 0.53 e 0.58, bem dentro da faixa abaixo.
FAIXA_DO_DIALOGO = (0.20, 0.30, 0.80, 0.80)  # (x0, y0, x1, y1)


def casar_dialogo(
    pixels: np.ndarray | None, template: np.ndarray | None
) -> float | None:
    """Quanto o frame se parece com o dialogo de desconexao, de 0.0 a 1.0.

    None quando a pergunta nao e respondivel — sem template gravado, ou frame
    menor que ele. `None` e "nao sei", nunca 0.0: um scanner que confunde as
    duas coisas anuncia o contrario do que esta vendo.

    A busca cobre so a faixa central da janela (ver `FAIXA_DO_DIALOGO`). Se a
    faixa nao couber o template — janela pequena demais — cai de volta para o
    frame inteiro, porque perder a deteccao e pior do que gastar o tempo.
    """
    if pixels is None or template is None:
        return None
    if pixels.size == 0 or template.size == 0:
        return None
    if (
        pixels.shape[0] < template.shape[0]
        or pixels.shape[1] < template.shape[1]
    ):
        return None

    altura, largura = pixels.shape[:2]
    fx0, fy0, fx1, fy1 = FAIXA_DO_DIALOGO
    recorte = pixels[
        int(altura * fy0) : int(altura * fy1),
        int(largura * fx0) : int(largura * fx1),
    ]
    if (
        recorte.shape[0] < template.shape[0]
        or recorte.shape[1] < template.shape[1]
    ):
        recorte = pixels

    resultado = cv2.matchTemplate(recorte, template, cv2.TM_CCOEFF_NORMED)
    return float(resultado.max())


def estado_do_cliente(
    titulo: str | None,
    pixels: np.ndarray | None = None,
    template: np.ndarray | None = None,
    limiar_do_dialogo: float = 0.90,
) -> EstadoDoCliente:
    """Junta os dois sinais numa resposta so.

    A ORDEM IMPORTA: a tela de login e decidida primeiro porque o titulo e
    prova, e o template e evidencia. Um dialogo aberto na tela de login (que o
    cliente mostra ao ser derrubado antes de logar) deve ser lido como tela de
    login — que e o estado mais informativo dos dois.
    """
    if titulo is None:
        return EstadoDoCliente.DESCONHECIDO

    if esta_na_tela_de_login(titulo):
        return EstadoDoCliente.TELA_DE_LOGIN

    pontuacao = casar_dialogo(pixels, template)
    if pontuacao is None:
        # Sem template carregado so sabemos o que o titulo disse, e ele disse
        # "tem personagem". Isso e o melhor que da para afirmar.
        return EstadoDoCliente.EM_JOGO
    if pontuacao >= limiar_do_dialogo:
        return EstadoDoCliente.DESCONECTADO
    return EstadoDoCliente.EM_JOGO


class VigiaDoCliente:
    """Decide o estado do cliente, com CADENCIA para a busca cara.

    Mora aqui, e nao no `JanelaSource`, por um motivo de testabilidade que a
    cobertura tornou obvio: `captura_janela.py` esta em 19% e `rastreador.py`
    em 98%, e os tres warnings do code review moravam todos na camada de baixa
    cobertura. Logica que decide alguma coisa nao pode viver onde so um jogo
    aberto consegue exercita-la.

    A CADENCIA existe porque as duas perguntas tem custos absurdamente
    diferentes:

      titulo da janela  ~0.001 ms  -> a cada tick, sempre
      matchTemplate     ~45 ms     -> a cada poucos segundos

    Medido: o matchTemplate sozinho seria ~98% do CPU do scanner a 1 Hz (contra
    0,7 ms de toda a analise da party window). E ele nao precisa dessa
    frequencia — um dialogo de desconexao nao pisca, ele aparece e FICA ate
    alguem clicar.

    O VEREDITO DE DESCONEXAO GRUDA entre buscas. Sem isso o estado oscilaria
    DESCONECTADO/EM_JOGO a cada tick e o debounce do rastreador nunca fecharia
    as confirmacoes — o alerta simplesmente nunca sairia.
    """

    def __init__(
        self,
        template: np.ndarray | None,
        segundos_entre_buscas: float = 5.0,
        limiar_do_dialogo: float = 0.90,
    ) -> None:
        self._template = template
        self._intervalo = segundos_entre_buscas
        self._limiar = limiar_do_dialogo
        self._ultima_busca: float | None = None
        self._viu_dialogo = False

    def avaliar(self, titulo: str | None, obter_pixels, agora: float):
        """`obter_pixels` so e chamado quando a busca vence.

        Passar um chamavel em vez dos pixels e o que faz a cadencia valer a
        pena: nos ticks em que nao ha busca, o frame nem chega a ser copiado.
        """
        if titulo is None:
            return EstadoDoCliente.DESCONHECIDO

        # O titulo e prova e custa quase nada — sempre primeiro, sempre fresco.
        if esta_na_tela_de_login(titulo):
            self._viu_dialogo = False
            return EstadoDoCliente.TELA_DE_LOGIN

        vencido = (
            self._ultima_busca is None
            or agora - self._ultima_busca >= self._intervalo
        )
        if vencido:
            self._ultima_busca = agora
            pontuacao = casar_dialogo(obter_pixels(), self._template)
            if pontuacao is not None:
                self._viu_dialogo = pontuacao >= self._limiar

        return (
            EstadoDoCliente.DESCONECTADO
            if self._viu_dialogo
            else EstadoDoCliente.EM_JOGO
        )
