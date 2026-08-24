---
spike: 001
idea: captura-em-segundo-plano
name: wgc-janela-em-segundo-plano
type: standard
validates: "Dado o jogo aberto mas coberto por outra janela e sem foco, quando capturamos pela API de janela do Windows, entao os valores de HP continuam MUDANDO"
verdict: VALIDATED
related: []
tags: [captura, wgc, windows, alt-tab]
---

# Spike 001: Captura com o jogo em segundo plano

## O que valida

**Dado** o jogo aberto mas coberto por outra janela e sem foco,
**quando** capturamos pela Windows Graphics Capture em vez do desktop composto,
**então** os valores de HP continuam mudando entre frames.

O critério é deliberadamente exigente. "Chegou um frame não-preto" não basta: o
risco real não é a captura falhar de forma óbvia, é o cliente **parar de
renderizar sem foco** e a captura devolver o último frame para sempre. Dado
velho parecendo válido é pior do que erro — o scanner acharia que está cobrindo
a party e estaria olhando uma foto.

## Pesquisa

| Método | Vê janela coberta? | Vê minimizada? |
|---|---|---|
| `mss` (GDI) — o que usamos hoje | Não: captura o desktop composto, vê a janela de cima | Não |
| `dxcam` (DXGI Desktop Duplication) | Não: mesmo motivo, duplica o desktop | Não |
| `pywin32 PrintWindow` | Não para DirectX — devolve preto. UE2 é D3D | Não |
| **`windows-capture` (WGC)** | **Sim, verificado aqui** | **Não** |

**Escolhido:** `windows-capture` 2.x — bindings Python sobre a Windows Graphics
Capture. O DWM mantém uma superfície de composição por janela, e a WGC lê dela
em vez de ler o desktop.

**Ressalva que continua valendo:** WGC **não** resolve janela minimizada. Uma
janela minimizada para de produzir frames, ponto. O escopo é "coberta por outra
janela", não "minimizada".

## Como rodar

```bash
cd .planning/spikes/001-wgc-janela-em-segundo-plano
python testar_wgc.py 30          # captura a janela do Yazalaque e lê a party
python testar_sem_foco.py "Faerlina - XM Essence" 15
```

## Trilha da investigação

**Primeira tentativa (`testar_wgc.py`)** — capturou a janela do Yazalaque e
extraiu a party window dela. Funcionou: 495 frames em 12s, HP lido corretamente
em ~94% com 6 leituras distintas. Mas **inconclusivo**: o jogo permaneceu em
primeiro plano o tempo todo, então a pergunta sobre foco continuou aberta.

**Segunda tentativa (`testar_sem_foco.py`)** — em vez de tirar o foco do jogo e
atrapalhar o usuário, aproveitei um experimento natural: ele roda **duas
instâncias**. Apenas uma pode estar em primeiro plano, então a outra está por
definição sem foco — e estava coberta pela janela do Claude.

Isso deu a resposta sem tocar na tela dele, o que também torna o teste
repetível: qualquer pessoa com duas janelas pode rodá-lo.

## Resultados

**VALIDADO.**

Cliente `Faerlina`, sem foco e coberto, 12 segundos de captura:

| Medida | Valor |
|---|---|
| Frames recebidos | 456 |
| Frames sem foco | 456 (100%) |
| Frames **distintos** | 443 (97%) |
| Frames pretos | 0 |
| Maior sequência idêntica | 2 frames |

O XM Essence **continua renderizando normalmente sem foco e coberto**. Não há
throttling de renderização, que era o risco apontado pela pesquisa inicial.

**Surpresa:** a taxa de frames é muito alta (~38 fps), bem acima do 1 Hz que o
scanner precisa. A implementação vai precisar descartar frames em vez de pedir
por eles — a WGC é orientada a evento, empurra frames, não é sob demanda como o
`mss`.

**Limite que permanece:** janela minimizada não produz frame nenhum. Isso não é
contornável por nenhuma API — é como o Windows funciona.

## Implicações para a implementação

1. A captura vira uma **porta com dois adaptadores**: `mss` (desktop, atual) e
   `wgc` (janela). A escolha vai para o arquivo de configuração.
2. As coordenadas mudam de referencial: a calibração está em coordenadas de
   **desktop**, e o frame WGC começa no canto da **janela**. É preciso descontar
   a origem da janela — e ela muda se o usuário arrastar o jogo.
3. WGC é **push**, não pull: um callback recebe frames a ~38 fps. O adaptador
   precisa guardar o último frame e devolvê-lo quando o laço pedir.
4. O detector de frame congelado continua necessário — agora protege contra a
   janela minimizada, que entrega o último frame ou nada.
