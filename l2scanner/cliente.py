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


def casar_dialogo(
    pixels: np.ndarray | None, template: np.ndarray | None
) -> float | None:
    """Quanto o frame se parece com o dialogo de desconexao, de 0.0 a 1.0.

    None quando a pergunta nao e respondivel — sem template gravado, ou frame
    menor que ele. `None` e "nao sei", nunca 0.0: um scanner que confunde as
    duas coisas anuncia o contrario do que esta vendo.
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
    resultado = cv2.matchTemplate(pixels, template, cv2.TM_CCOEFF_NORMED)
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
