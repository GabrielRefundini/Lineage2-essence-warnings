"""A RAIZ do projeto, e SO ela. O modulo FOLHA que corta uma cadeia de import.

ELE E UMA FOLHA, E ISSO E O CRITERIO INTEIRO
=============================================
Este arquivo nao importa NADA de dentro do pacote. Nao e estilo: e a unica
propriedade que faz o corte funcionar. Qualquer `from .alguma_coisa import ...`
acrescentado aqui refaz, por baixo, exatamente a cadeia que este modulo existe
para desfazer — e o proximo a chegar nao teria como saber disso lendo o arquivo
que importou. Ha portao de AST no criterio de aceitacao deste plano exigindo
zero import relativo neste arquivo.

A doutrina da casa e "IMPORTADOS, E NAO REDEFINIDOS" (`mercado_registro.py:65`):
duas definicoes da mesma raiz e como elas divergem. Por isso `config.py` passa a
RE-EXPORTAR daqui em vez de manter a sua propria — a definicao continua uma so,
ela so mudou de casa.

A CADEIA QUE ELE CORTA, COM ARQUIVO E LINHA
============================================
Ate hoje, `mercado_catalogo.py:95` fazia `from .config import RAIZ` — por UMA
constante — e com isso arrastava o pacote inteiro:

    l2scanner.mercado_registro   :70  from .mercado_catalogo import PASTA_DO_MERCADO, SEPARADOR
    l2scanner.mercado_catalogo   :95  from .config import RAIZ            <-- A ARESTA CARA
    l2scanner.config             :37  from .notificador import ConfigChatwoot
    l2scanner.notificador        :36  from .rastreador import Evento, TipoDeEvento
    l2scanner.rastreador         :56  from .visao import EstadoDaLinha, LeituraDeLinha, Observacao
    l2scanner.visao              :30  import cv2
    l2scanner.visao              :31  import numpy as np

As quatro metricas medidas na pesquisa desta fase, nas DUAS arvores (com a
aresta e sem ela), lado a lado:

    modulos em `sys.modules`   280   contra    52
    pesados presentes          cv2 e numpy     nenhum
    tempo de import        175 a 371 ms    contra    40 a 65 ms
    working set              44,3 MB       contra    17,3 MB

Medido de novo NESTA arvore, no dia do corte, para o numero nao virar folclore:
`import l2scanner.mercado_catalogo` trazia **341 modulos** com `cv2` presente,
765 ms de import acumulado. Depois do corte, os numeros de depois estao no
SUMMARY deste plano e o tripwire de `tests/test_mercado_firewall_de_fase.py`
passa a PRENDER a ausencia — antes ele prendia a presenca.

O QUE ESTE CORTE **NAO** COMPRA — a refutacao, medida hoje
===========================================================
UM NUMERO QUE CAIU PRECISA DIZER QUE CAIU, e o que cai aqui e uma frase que o
proprio projeto escreveu: a justificativa do DASH-06 antecipava que o processo
do dashboard deixaria de carregar OpenCV. **Ele carrega.**

Medido nesta arvore hoje: `import l2scanner.mercado_console` traz **350 modulos,
com `cv2` e `numpy`**, por uma SEGUNDA aresta que este corte nao toca:

    l2scanner.mercado_console    :42  from . import console
    l2scanner.console            :16  from .rastreador import TipoDeEvento   <-- A SEGUNDA ARESTA

Cortar essa segunda aresta exigiria mexer em `console.py` ou em `rastreador.py`,
e nenhum dos dois esta autorizado: a decisao do usuario em 2026-09-01 (CTX-2)
nomeia `mercado_catalogo.py` como o UNICO arquivo do workstream `mercado` que
esta fase pode tocar. E o dashboard e OBRIGADO a usar os formatadores de
`mercado_console` — o DASH-03 proibe um segundo formatador. Logo: o processo do
dashboard carrega OpenCV apesar deste corte, e isso e um fato, nao uma pendencia
escondida. O `dashboard.bat` passa a sondar `cv2` e `numpy` para que o custo
fique visivel em vez de suposto.

O que ESTE corte compra continua sendo real e continua valendo: `mercado_registro`
e `mercado_catalogo` saem da cadeia de `config`, e um interpretador que importe
so o catalogo nao ve mais `config`, `rastreador` nem `cv2`. E isso que o tripwire
consertado prova.

Medido junto, e vale registrar porque limita o tamanho do problema: `mss`,
`windows_capture` e `winrt` **nao** entram por nenhuma dessas arestas, e
`import l2scanner.mercado_analise` sozinho fica em **102 modulos, sem `cv2`**.

Cortar a segunda aresta e REVERSIVEL e e o mesmo movimento deste: um modulo
folha para `moldurar` ou para `TipoDeEvento`, mais re-exportacao. Pode acontecer
numa fase futura do workstream `mercado` sem desfazer uma linha escrita aqui.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["RAIZ"]

# Copiada LITERALMENTE de `config.py:48`, e nao reescrita: o arquivo mudou de
# lugar, a conta nao. `raiz.py` mora em `l2scanner/`, entao `parent.parent` e a
# raiz do repositorio — a mesma profundidade que `config.py` tinha.
RAIZ = Path(__file__).resolve().parent.parent
