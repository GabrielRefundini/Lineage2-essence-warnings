---
slug: total-da-adena-em-ciano-nao-se-le
workstream: mercado
created: 2026-09-01
status: investigating
severity: alta
hypothesis: >
  Os 13 moldes de digito foram cortados sobre texto BRANCO. A coluna Total Price da
  aba Adena renderiza ALGUMAS linhas em CIANO, e em ciano o canal vermelho cai antes
  nas bordas antialiasadas — o traco fica com outro perfil em escala de cinza e a
  largura do run muda, que e o que decide qual molde casa.
next_action: >
  MEDIR o que a conversao para cinza faz com o glifo ciano contra o branco, e decidir
  entre normalizar por canal ou cortar um segundo conjunto de moldes.
---

# A coluna Total Price da Adena tem valores em ciano, e eles nao se leem

## Sintoma, em campo, depois da calibracao do usuario

A aba Adena foi calibrada por ele em 2026-09-01 17:26. O bloco aninhado foi gravado
corretamente, **nenhuma chave de topo tocada**, e o portao de layout passou a ACEITAR
(a mensagem `PARADO` sumiu do console).

**E mesmo assim todas as paginas sao perdidas.**

## A verdade de campo

Frame `recordings/20260901-172911-adena-diagnostico/frame_000003.png`, comparado com
o que o leitor de producao devolveu na sessao das 17:28:

    linha | Total Price | 5 mln increment | o leitor devolveu
        3 |     100,00  |          50,00  | total=18888  incremento=5000
        5 |     100,00  |          50,00  | total=18888  incremento=5000
        9 |     104,00  |          52,00  | total=18488  incremento=5200

**O incremento le CERTO. So o total erra**, trocando `0` por `8` — com os MESMOS
digitos que a outra coluna acerta na MESMA linha. Isso ja descarta "o par 0x8 e
ambiguo": se fosse so isso, a coluna do incremento erraria junto.

## A causa, MEDIDA nos canais de cor

    linha 0  total  (98,00)   B=214.2  G=214.2  R=214.2   <- branco neutro
    linha 3  total  (100,00)  B=236.0  G=236.0  R=128.7   <- CIANO
    linha 0  increm (49,00)   B=217.1  G=217.1  R=217.1   <- branco
    linha 3  increm (50,00)   B=220.3  G=220.3  R=220.3   <- branco

A coluna `Total Price` renderiza ALGUMAS linhas em ciano (vermelho ~129 contra ~236
dos outros dois canais); a do incremento e sempre branca. **As linhas recusadas sao
exatamente as cianas.**

## O que FUNCIONOU, e nao pode ser desfeito

**A guarda de cruzamento rejeitou TODAS as linhas corrompidas** — `total=18888` com
`incremento=5000` da residuo 1112 contra limite 2,0. O `.mercado/observacoes.csv`
ficou em **93 linhas antes e depois**: nenhuma taxa falsa entrou.

Sem ela, `188,88 por 10 milhoes` viraria observacao de taxa e a mediana do cambio
nasceria envenenada. Foi o modo de falha CERTO: nao coletou, em vez de coletar errado.

## Direcoes a MEDIR (nenhuma escolhida)

1. **Normalizar por canal antes de segmentar** — usar `max(B,G,R)` em vez da escala
   de cinza ponderada, que penaliza o vermelho (`0,299·R`). Barato, e nao cria molde
   novo. Mede-se o efeito sobre as larguras de run do glifo ciano contra o branco.
2. **Cortar um segundo conjunto de moldes sobre texto ciano.** Caro (13 moldes a mao)
   e dobra o material a manter, mas nao mexe no caminho que hoje funciona.

## Restricoes invioláveis

- **NAO afrouxar a guarda de cruzamento.** Ela e o unico motivo de o dado estar limpo
  agora. Afrouxa-la troca "nao coletou" por "coletou errado".
- **NAO baixar o corte de brilho as cegas.** O ciano tem brilho ALTO (236) — o
  problema nao e passar do corte, e o PERFIL DA BORDA.
- **NAO tocar** o caminho da negociacao, que foi conferido em campo hoje: 353 paginas
  lidas contra 2 perdidas. Qualquer mudanca em `ler_celula_de_numero` ou na
  segmentacao **precisa de controle negativo sobre a negociacao**.
- **NAO tocar** `rastreador.py` nem o gate de brilho da barra propria em `visao.py`.
- Nao tocar `respawn.py`, `bosses.py`, `agenda.py`, `sessao.py`, `test_bosses.py` —
  outro agente trabalha neles nesta arvore.
- **NAO escrever** em `.mercado/` nem em `calibration.json`. Nenhuma dependencia nova.
- `recordings/` somente-leitura, **nunca glob amplo**.

## Material que discrimina, e ele EXISTE

`recordings/20260901-172911-adena-diagnostico` (11 frames de janela completa) tem
linhas **brancas E cianas na mesma pagina** — o par que discrimina, no mesmo frame,
com a mesma fonte e o mesmo tamanho. Os dois defeitos de calibracao desta sessao
nasceram de escolher numero contra material sem o caso dificil; aqui o caso dificil
esta no disco.

**A verdade de campo de cada linha esta na tabela acima**, lida do proprio frame.
