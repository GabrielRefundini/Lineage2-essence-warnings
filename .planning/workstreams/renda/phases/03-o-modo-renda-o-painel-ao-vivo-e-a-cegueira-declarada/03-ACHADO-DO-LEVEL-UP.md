# O level up de 2026-09-03, e o limite do LEIT-10 que ele expôs

**Achado rodando o `--renda` de verdade**, logo depois de fundir o `03-01`, com o jogo aberto.
Não é hipótese de planejamento: é o produto encontrando o mundo.

## O que aconteceu, em três camadas ao mesmo tempo

1. **A Faerlina subiu de nível: 67 → 68.**
2. **O painel de status moveu ~90 px para cima.** O retângulo gravado (`251,738 20x16`) passou a
   apontar para **grama pura** — confirmado a olho no recorte ampliado, não havia painel nenhum ali.
3. **O nível passou a recusar 100% dos tiques**, contra os 79% medidos na Fase 1.

O `--renda` não inventou nada em nenhuma das três. Ele recusou, nomeou o motivo (`campo-vazio`),
gravou a recusa no CSV e continuou lendo EXP e adena. É o comportamento que o LEIT-04 pediu.

## M-Y — O LEIT-10 NÃO cobre este caso, e o plano precisa dizer isso

Este é o achado que muda documento.

O `LEIT-10` existe porque **a banda de brilho anda com o cenário** — medido três vezes: a banda do
EXP da Faerlina foi de `140..170` para `160..180` em 8,5 h. A resposta desenhada é varrer os
**pisos vizinhos** antes de declarar cegueira, com alcance de 4 passos.

**Mas o que quebrou hoje não foi brilho: foi POSIÇÃO.** Nenhum piso, em nenhum alcance, lê um
número num retângulo que contém grama. A varredura teria pagado as oito leituras extras por tique,
perdido as oito, e declarado cegueira do mesmo jeito — só que mais devagar.

Os dois modos de falha se parecem de fora (o campo para de sair) e **exigem conserto oposto**:

| o que mudou | como se vê | conserto |
|---|---|---|
| brilho do fundo | o campo sai em piso vizinho | **varredura** — LEIT-10 |
| posição do painel | o campo não sai em piso NENHUM | **recalibrar** — `calibrar-renda.bat` |

**Consequência para o `03-03`:** a varredura, ao perder em **todos** os pisos do alcance, não deve
só declarar cegueira — deve dizer que **o retângulo é o suspeito, não o piso**, e mandar o usuário
ao calibrador. Isso é barato (uma frase na mensagem) e é a diferença entre o usuário passar a noite
achando que o scanner travou e ele rodar dois cliques de manhã.

E casa com o mecanismo de carência que o plan-checker já obrigou: perder em todos os pisos é
justamente o sinal de que insistir não adianta.

## M-Z — A ponte de XP do nível 67 virou histórica no instante do level up

O `REND-08` diz que a constante é **por nível**, e hoje isso deixou de ser precaução e virou fato:
`renda_ponte_de_xp` tem `Faerlina/67` e o personagem está no 68. Pelo desenho, o XP absoluto sai
**declaradamente indisponível** até alguém medir o 68 — nunca convertido com a constante do 67.

Vale escrever o tamanho do erro que essa regra evita. O nível 67 custou **38,87 milhões**. Níveis
seguintes custam mais; se o 68 custar, digamos, 20% a mais, converter a porcentagem do 68 com a
constante do 67 subestimaria o XP/h em ~17% — um número plausível, com cara de medido, e errado.
É exatamente o modo de falha que o workstream inteiro existe para impedir.

**O que isto torna urgente:** a ferramenta que mede a ponte estava listada como *ideia adiada* no
`03-CONTEXT.md`, com a nota "ela vira necessária no próximo level up". O próximo level up
aconteceu **no mesmo dia**. Ela deixou de ser adiável.

## O que foi feito agora

Recalibrado o nível pela via não-destrutiva do calibrador (`_mutar_a_entrada_do_personagem` +
`Calibracao.salvar`), com o retângulo escolhido por robustez sobre **10 frames**:

    rect (262, 648) 22x18   piso 190   banda 5   ->  10/10 certos, 0 errados

Yazalaque intacta, `renda_ponte_de_xp` intacta, 47 chaves antes e depois. Backup em
`calibration.antes-do-nivel-68.bak`. Leitura ao vivo confirmada três vezes:

    nivel 68  EXP 48,0075%  adena 23.986.985
    nivel 68  EXP 48,0088%  adena 23.987.425
    nivel 68  EXP 48,0099%  adena 23.987.688
