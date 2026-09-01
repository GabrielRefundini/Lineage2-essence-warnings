---
title: Dashboard do câmbio — as decisões e os porquês
date: 2026-09-01
context: /gsd-explore, conversa socrática antes de existir qualquer plano
workstream: dashboard
---

# Dashboard do câmbio — o que foi decidido, e por quê

Sete decisões saíram desta conversa. As razões importam mais que as escolhas, porque é a razão
que diz quando a escolha deixa de valer.

## 1. É superfície nova, não evolução do console

O pedido original poderia ter sido "deixa o console `--mercado` mais bonito". Não é. O usuário
quer **parar de jogar tudo no Google Sheets** e ter um lugar visual dedicado. O console
continua existindo e continua sendo a saída de quem está no terminal; o dashboard é outra
janela para o mesmo dado.

Consequência prática: o `--mercado` não muda. Nem uma linha.

## 2. Tempo real, para decidir — não análise pós-sessão

> *"Tempo real para ajudar a tomar decisoes"*

Isso descarta a rota mais barata (gerar um relatório estático ao final da sessão) e obriga a
página a se atualizar sozinha enquanto o scanner coleta. É também o que torna a regra do
terminador do CSV inadequada aqui — ver a decisão 6.

## 3. Só Adena no v1

O v2-mercado já tinha decidido que a aba Adena é "o oráculo do câmbio". O dashboard segue a
mesma linha: uma série só, a que responde a pergunta que o usuário faz todo dia. A aba de
negociação tem dezenas de séries e nenhuma delas é urgente.

## 4. A conta é Adena → XM → BRL, e o R$ é o que decide

> *"Sempre temos que fazer a conversao Adena - XM - Real (BRL) para saber em Real (BRL)
> quanto vale cada coisa e podermos tomar a decisao melhor dos cambios"*

Esta é a descoberta que muda o produto. O jogo só fornece **metade** da conta (Adena → XM).
A metade que decide — quanto isso vale em dinheiro de verdade — depende de um câmbio que não
existe dentro do jogo. Por isso:

- o câmbio XM→BRL é **entrada manual** no v1 (`1 XM = R$ 0,50`, valor de hoje);
- todo valor em R$ é **derivado e declarado como tal**, nunca apresentado como medido;
- sem câmbio informado, o R$ **some da tela** em vez de aparecer chutado. Um câmbio inventado
  vira uma decisão de dinheiro real errada, que é uma categoria de dano diferente de um preço
  de item lido errado.

A coleta automática desse número (listener dos grupos de venda do WhatsApp) virou semente:
`.planning/seeds/cambio-xm-brl-pelo-listener-do-whatsapp.md`.

## 5. Histórico com zoom, e o componente nasce genérico

> *"um historico visual eh interessante e ja fazemos um template para replicar em todos os
> itens"*

O gráfico não é uma tela da Adena — é um **componente de série** que hoje só tem uma
instância. A generalidade é barata agora e cara depois, e o usuário já disse em voz alta que
vai querer replicá-la. Zoom de horas do dia até dias atrás, porque as duas perguntas são
diferentes: *"o câmbio mexeu na última hora?"* e *"esta semana está caro?"*.

Duas linhas sobrepostas, não uma: **menor pedido visível** é o que ele pagaria agora,
**mediana `median_low`** é o preço típico sem se deixar levar por uma oferta isolada. Os dois
números já são calculados pelo console — reaproveitá-los custa quase nada e responde às duas
perguntas de uma vez.

## 6. A regra do terminador não sobrevive à leitura ao vivo

Esta é a tensão técnica que a conversa expôs e que o planejamento tem que resolver com os
olhos abertos.

A Fase 3 do mercado decidiu — corretamente, para o caso dela — que um `observacoes.csv` que
não termina em quebra de linha é **contrato quebrado**: a feature desliga alto e nada é lido.
Para um leitor ao vivo essa regra é a errada: o scanner apenda continuamente, e o dashboard
pegaria o arquivo no meio de uma escrita o tempo todo, entrando em cegueira por um defeito que
não existe.

A degradação certa aqui é **"leio até a última linha completa"**. É uma divergência
deliberada de uma regra existente, e por isso precisa estar escrita no fonte como a casa
escreve refutação — senão alguém a "conserta" por simetria seis meses depois.

## 7. Processo separado, lançador próprio

`dashboard.bat` sobe só a interface. O motivo é o mesmo do `minimum_update_interval` da Fase 4
do mercado: **o caminho da coleta fica byte-idêntico**. Se o dashboard quebrar, a coleta da
noite continua. E como ele lê um arquivo, também funciona com o jogo fechado, sobre dados já
gravados — de graça.

A rota "página estática sem servidor" foi recusada: o navegador bloqueia `fetch` de `file://`,
e o contorno vira atrito recorrente.

## 8. Workstream próprio (`dashboard`), não fase do `mercado`

Decisão de processo, não de produto. O usuário tem chats rodando em paralelo no `mercado`, e
GSD guarda progresso por workstream — dois agentes no mesmo `STATE.md` colidem. Como a
dependência entre os dois é **um arquivo** (`.mercado/observacoes.csv`) e não código
compartilhado, separar sai de graça.

## O que ficou em aberto de propósito

- **A stack do gráfico** sob a doutrina de zero-install: JS vendorizado na árvore + `http.server`
  da stdlib, CDN, ou render no servidor. É pesquisa da fase.
- **Onde a taxa XM→BRL é persistida**: fora do `calibration.json` e fora do `config.toml` (o
  `tomllib` da stdlib é read-only e quem escreve é o navegador). Provavelmente um JSON pequeno,
  do dashboard.
- **O que um ponto do gráfico significa quando o zoom é largo** e vários ticks caem no mesmo
  pixel. A disciplina D-02 vale inteira: o número exibido tem de ter existido.
