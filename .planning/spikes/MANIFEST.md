# Spike Manifest

## Ideas

### captura-em-segundo-plano

Hoje o scanner só enxerga a party window se ela estiver visível na tela: ele
captura o desktop composto, então qualquer janela por cima esconde o jogo. Isso
obriga o usuário a deixar o jogo à vista enquanto farma, o que atrapalha usar o
PC para outra coisa. A ideia é ler a janela do jogo diretamente, pela API de
captura de janela do Windows, para que alt+tab deixe de cegar o scanner.

**Requirements:**

- Janela **minimizada** está fora de escopo — nenhuma API do Windows resolve
  isso, a janela para de produzir frames. O escopo é "coberta por outra janela".
- O backend de captura é escolhido por configuração, não trocado à força: o
  `mss` continua sendo o padrão por ser mais simples e ter menos modos de falha.
- O critério de aprovação de qualquer backend novo é "os valores de HP continuam
  MUDANDO", nunca "chegou um frame não-preto". Dado velho parecendo válido é
  pior do que erro claro.

## Spikes

| # | Idea | Name | Type | Validates | Verdict | Tags |
|---|------|------|------|-----------|---------|------|
| 001 | captura-em-segundo-plano | wgc-janela-em-segundo-plano | standard | Jogo coberto e sem foco → HP continua mudando | **VALIDATED** | captura, wgc, windows, alt-tab |
