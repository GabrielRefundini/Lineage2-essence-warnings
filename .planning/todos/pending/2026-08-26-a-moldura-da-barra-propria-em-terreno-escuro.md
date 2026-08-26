---
created: 2026-08-26T00:00:00.000Z
title: A moldura da barra própria em terreno escuro
area: detection
severity: major
files:
  - l2scanner/visao.py (BRILHO_MINIMO_DA_MOLDURA_PROPRIA = 60.0)
  - l2scanner/visao.py (_moldura_da_barra_propria, barra_propria_legivel)
  - tests/fixtures/barra_propria/quase_vazia_terreno_atras.png (o proxy, 191x24)
  - tests/test_inventario_por_cima_da_barra_propria.py (TestAMorteDeVerdadeContinuaSaindo)
---

## Problem

A quick task `260826-dxm` fechou o falso positivo do inventário: um recorte da
barra própria cuja **moldura** (menor média de cinza entre as quatro bordas)
fica abaixo de **60.0** é declarado ILEGÍVEL, e `hp_proprio` sai `None` em vez
de `0.0`. Isso apagou as 27 mortes falsas + 27 ressurreições falsas que estavam
no `logs/scanner.log` real.

**O portão SUPÕE uma coisa que só foi medida num cenário:** que a parte vazia da
barra mostra terreno mais claro que 60. A região `hp_proprio` calibrada
(esquerda 294, topo 716, 191x24) não tem margem sobrando — as quatro bordas do
recorte caem DENTRO do campo da barra. Quando a barra está cheia, o campo é
vermelho e claro; quando está vazia, o campo é **transparente e mostra o
terreno do jogo**.

**A DIREÇÃO DO DANO é a ruim.** Este não é um risco de alarme falso — é um
risco de SILÊNCIO:

    terreno escuro atrás da barra vazia
      -> moldura abaixo de 60
      -> barra própria declarada ILEGÍVEL
      -> hp_proprio = None
      -> o rastreador CONGELA o estado em vez de concluir
      -> MORTE REAL NÃO É ANUNCIADA

O roadmap chama isso pelo nome: *"morrer calado enquanto a party acha que está
coberta"*. É o pior desfecho declarado deste projeto, e o remédio de hoje é
exatamente o tipo de mudança que pode causá-lo.

**O que foi medido, e onde:**

| Amostra | moldura | Ambiente |
|---|---|---|
| barra de MP a 6.6% (`quase_vazia_terreno_atras.png`) | **78.73** | grama, luz do dia (cinza ~95) |
| as 4 `livre_*.png` | 86.42 | mesma sessão |
| as 4 `coberta_*.png` | 28.00 a 48.92 | inventário aberto |

Folga real da barra vazia até o limiar: **18.73 pontos**. Foi por causa dessa
folga estreita que o limiar ficou no **pé** da faixa medida (60) e não no meio
do vão (63.8) — cada ponto a mais no limiar é folga tirada do lado que não pode
falhar.

**O que NÃO foi medido:** a mesma barra vazia sobre terreno escuro — masmorra,
caverna, à noite, chão de pedra escura. Se o terreno atrás da parte vazia cair
abaixo de 60, a barra vazia de verdade vira "não consigo ler".

**Agravante:** o único proxy de barra vazia que o repositório tem é a barra de
**MP**, não a de HP. Nenhuma amostra alinhada de HP próprio em nível baixo
existe — as 8 fixtures, as 4 `*__hp_proprio*.png` e todos os frames de janela em
`recordings/` estão a 100%. O `recordings/base_janela.png`, que parecia HP
baixo, é na verdade a região DESALINHADA depois da janela ser movida.

## Solution

O que fecha a pendência é uma MEDIÇÃO que hoje não existe, não um ajuste de
número:

1. **Gravar a própria barra com HP baixo em ambiente escuro.** Com o scanner
   rodando, entrar numa masmorra/caverna (ou jogar à noite), deixar o HP cair
   e disparar o gravador de frames. O recorte precisa ser da região
   `hp_proprio` calibrada, alinhada — um recorte desalinhado não serve, como o
   `base_janela.png` já provou.

2. **Rodar `_moldura_da_barra_propria` sobre esse recorte e anotar o número.**

3. **Critério de aceite:** moldura > 70 (10 pontos de folga até o limiar). Se
   ficar entre 60 e 70, a folga é fina demais e o limiar precisa descer. Se
   ficar abaixo de 60, o portão de moldura **está suprimindo morte real hoje** e
   precisa de outro discriminador — não de outro limiar.

4. **Se o limiar não puder separar os dois casos**, o caminho é o mesmo que a
   party já usa: olhar chrome que existe FORA do campo da barra, onde o terreno
   não entra. Isso exige recalibrar a região `hp_proprio` com 1-2 px de margem
   sobrando, o que hoje ela não tem.

5. Guardar o recorte como fixture e travar com teste, ao lado de
   `quase_vazia_terreno_atras.png`.

**Enquanto isso não é feito:** o risco é assimétrico e conhecido. O defeito que
o portão corrigiu era CONSTANTE (o usuário abre o inventário o tempo todo, e a
prova são 27 ocorrências num único log); o risco que ele abriu é
CONDICIONAL (exige terreno escuro E barra quase vazia ao mesmo tempo) e nunca
foi observado. A troca vale, mas não é de graça, e o preço está escrito aqui
para não ser esquecido.

**Sinal de que a pendência virou defeito:** aparecer no `scanner.log` uma
sequência de leituras da barra própria ILEGÍVEL durante combate em ambiente
escuro. Ilegibilidade que aparece só ao morrer, e não ao abrir o inventário, é
esta pendência se realizando.
