---
quick_id: 260824-yaz
slug: monitorar-proprio-personagem
date: 2026-08-24
status: in-progress
---

# Monitorar o próprio personagem

## Problema

O scanner vigia só a party window. O personagem do próprio usuário
(`Yazalaque`) **não aparece nela** — a barra dele fica no topo da tela, num
lugar completamente diferente da UI.

Consequência prática: quando o usuário morre, ninguém é avisado. E ele é
justamente quem tem mais chance de morrer AFK, porque é o único que não tem
outra pessoa olhando.

Isso era o requisito DTCT-06 do roadmap. Eu o marquei como entregue quando
não estava: a calibração tem o campo `hp_proprio`, mas ele nunca é preenchido
e nada o lê.

## Medições da tela real

Janela do Yazalaque, 1720x1392. Coordenadas relativas ao canto da janela:

| Elemento | Posição | Tamanho |
|---|---|---|
| Barra de HP própria | (87, 60) | 191x24 |
| Barra de MP própria | (86, 84) | 183x24 |

**Diferença importante em relação à party window:** o texto `HP 3597/3597` fica
desenhado POR CIMA da barra. Isso poderia quebrar a medição por corrida de
colunas — mas não quebra: a barra tem 24 px de altura e as letras não ocupam
metade de nenhuma coluna, então o teste "maioria das linhas casa a cor"
sobrevive. Verificado: leitura de 100% com HP cheio.

## Tarefas

1. Captura de uma segunda região, longe da party window
2. Calibrador detecta a barra própria sozinho e pergunta o nome do personagem
3. Leitura mede a barra própria junto com as da party
4. Rastreador trata o próprio personagem como mais um membro
5. Console mostra o próprio personagem destacado dos outros

## Fora de escopo

**"Sair da própria party"** não é detectável pela barra do personagem — ela
continua igual. O sinal disso seria a party window inteira sumir, mas isso é
indistinguível de alt-tab e de tela de loading. Fica registrado como limite
conhecido, não implementado.

## Definição de pronto

- Morte do próprio personagem gera alerta com o nome dele
- Ressurreição também
- O próprio personagem aparece no console junto com a party
- Calibração antiga, sem a barra própria, continua funcionando
