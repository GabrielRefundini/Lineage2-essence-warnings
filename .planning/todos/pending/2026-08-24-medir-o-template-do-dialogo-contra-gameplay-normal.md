---
created: 2026-08-24T22:02:48.835Z
title: Medir o template do diálogo contra gameplay normal
area: testing
severity: minor
files:
  - l2scanner/cliente.py:130 (casar_dialogo)
  - l2scanner/cliente.py:151 (estado_do_cliente, limiar_do_dialogo=0.90)
  - l2scanner/recursos/dialogo_desconexao.png (o template, 320x62)
  - tests/test_cliente.py (TestTemplateDoDialogo)
  - tests/fixtures/cliente/dialogo_desconexao_recorte.png (o único positivo)
---

## Problem

A Fase 5 detecta "desconectado do servidor" casando um template (a faixa de
baixo do diálogo: botão OK sobre a caixa cinza) contra o frame COMPLETO da
janela, com limiar em 0.90.

**O que foi medido ao vivo em 2026-08-24:**

| Frame | Score | Veredito |
|---|---|---|
| `Faerlina - XM Essence` com o diálogo aberto | **0.9997** | positivo real |
| `XM Essence` na tela de login | **0.5051** | negativo real |

**O que NÃO foi medido:** o template contra um frame de janela inteira com o
jogo rodando normalmente — party window visível, personagem no mundo, farm em
andamento. Esse é justamente o frame contra o qual o scanner roda 99% do tempo.

Por que a lacuna existe: quando a Fase 5 foi construída, as duas instâncias do
usuário estavam caídas (servidor em manutenção). Não havia um cliente jogando
de onde capturar. Todas as fixtures que já existiam em `tests/fixtures/` são
RECORTES da party window (menores que o template de 320x62), então
`casar_dialogo` devolve `None` nelas — elas não servem de negativo.

**Risco concreto se o limiar estiver errado:** um frame de gameplay que passe
de 0.90 faz o bot anunciar "o jogo caiu" no WhatsApp no meio do farm. É
exatamente a classe de alarme falso que o dia 2026-08-24 inteiro foi gasto
corrigindo (ver `.planning/debug/resolved/alarme-falso-no-arranque.md` e
`.planning/debug/resolved/party-entra-sai-em-loop.md`), e o custo dela não é
técnico: é a party parar de acreditar no scanner.

O risco é BAIXO — a margem entre 0.9997 e 0.5051 é enorme, e terreno de jogo
com textura não se parece com uma caixa cinza uniforme. Mas "baixo" aqui é
inferência, não medição, e a regra do projeto é explícita: nada de limiar no
chute (`.claude/CLAUDE.md`, "Hardcoded HSV constants" em *What NOT to Use*).

## Solution

Com o jogo aberto e rodando normal (não precisa estar em party):

1. Capturar um frame de janela INTEIRA de cada cliente aberto. O script usado
   na Fase 5 está descrito abaixo — o essencial é `JanelaSource(...).capturar_completo()`,
   que devolve a janela toda em vez do recorte calibrado:

   ```python
   from l2scanner.calibracao import Regiao
   from l2scanner.captura_janela import JanelaSource, listar_janelas_do_jogo
   for titulo in listar_janelas_do_jogo():
       fonte = JanelaSource(titulo, Regiao(esquerda=0, topo=0, largura=10, altura=10), relativa=True)
       px = fonte.capturar_completo()   # janela inteira
       fonte.fechar()
   ```

2. Rodar `casar_dialogo(px, carregar_template())` e anotar o score.

3. **Critério de aceite:** score de gameplay normal < 0.70. Isso deixa 0.20 de
   folga até o limiar de 0.90. Se ficar acima de 0.70, o template precisa
   mudar — não o limiar. Subir o limiar aperta a margem do lado do positivo,
   que é o lado que não pode falhar (AFK + desconectado é o caso que a Fase 5
   existe para pegar).

4. Guardar o frame como fixture negativa e travar com teste. **Recortar antes
   de commitar**: o frame inteiro contém o chat com nomes e mensagens de outros
   jogadores. O positivo já foi recortado por esse motivo — só a caixa do
   diálogo, sem chat. Fazer o mesmo aqui: pegar a faixa central da tela, longe
   do chat (que fica embaixo à esquerda) e do nome do personagem.

5. Cobrir também o caso do INVENTÁRIO ABERTO. `coberta_por_inventario.png` já
   existe como fixture (recorte) e o inventário é um painel cinza grande —
   é o negativo mais parecido com o diálogo que o jogo produz naturalmente, e
   portanto o mais provável de casar por engano.

**Enquanto isso não é feito:** a detecção de TELA DE LOGIN não depende disto.
Ela vem do título da janela (`XM Essence` sem prefixo de personagem), que é
texto do Windows — sem limiar, sem pixel, sem risco. Só a detecção de
DESCONECTADO carrega essa incerteza.
