# A calibração do usuário — feita pelo agente, e o que ela ensinou

**2026-09-02, tarde.** O usuário rodou o comando, viu os três campos recusados, e pediu
explicitamente: *"rode você e configure você, tem acesso a minha tela, computador"*.

## O que estava errado

Entre a conferência da manhã e a rodada dele, **o conteúdo da janela subiu ~8 px** e a janela de
status mudou de lugar. As três regiões calibradas nas gravações de 00h45/09h30 deixaram de valer
todas de uma vez. É o `LEIT-10` pela terceira vez, agora por **geometria** e não por brilho.

## O método — varredura + voto, com os leitores de PRODUÇÃO

Nada foi reimplementado. Para cada região, varri retângulos e pisos chamando `exp_da_barra`,
`adena_da_barra` e `nivel_da_regiao`, e escolhi o candidato cujo **valor teve mais votos
independentes**. Depois conferi a olho, ampliado, contra a tela.

O voto pagou por si na adena da Yazalaque: `3.998.426` com 26 votos contra `3.498.426` com 8 —
uma substituição de `9` por `4`, que é exatamente o M-V. O olho confirmou o de 26 votos.

A gravação foi por `calibrar_renda._mutar_a_entrada_do_personagem` + `Calibracao.salvar`, o
caminho não-destrutivo do próprio calibrador. Medido depois: **46 chaves antes, 46 depois,
nenhuma perdida, só `renda_por_personagem` mudou.** Backup em
`calibration.antes-da-calibracao-automatica.bak`.

## M-X — Folga no retângulo do nível PIORA a leitura, e a ferramenta aconselha o contrário

Este é o achado da rodada.

Primeira tentativa, retângulo folgado `(243,733) 40x24`: **5 de 8 frames** na Faerlina e
**1 de 8** na Yazalaque. Ao vivo, a Yazalaque chegou a devolver `60` no lugar de `69` — número
errado ACEITO, o pior desfecho possível.

A causa está visível quando se amplia: o nível fica sobre a arte do retrato, e a folga do
retângulo **inclui a arte**. Na Yazalaque a arte ali é pele clara, e texto branco sobre pele
clara desaparece na máscara. Na Faerlina o mesmo lugar é escuro e o problema é menor — a mesma
região, dois personagens, dificuldades opostas.

Apertando o retângulo em torno dos dígitos, `(251,738) 20x16`:

| personagem | folgado (40x24) | apertado (20x16) |
|---|---|---|
| Faerlina | 5/8 certos | **14/14, zero erros** |
| Yazalaque | 1/8 certos | **14/14, zero erros** |

Banda de piso limpa nas duas: **190–210**, ótimo em 210. Fora dela o custo é alto e silencioso:
com `(250,737) 22x18` no piso 215, a Yazalaque devolve `139` e `60` — **zero acertos em 8
leituras**, todas aceitas.

**A ferramenta aconselha o oposto.** A mensagem de recusa por forma diz, com todas as letras:

    Marque de novo, com folga em cima e embaixo.

Isso está certo para a adena, onde a folga garante que os ícones das pontas entrem e sejam
descartados por largura. **Está errado para o nível**, onde a folga entra arte animada em vez de
fundo neutro. Uma mensagem só para duas regiões com geometrias opostas manda o usuário piorar a
calibração metade das vezes. Fica como defeito nomeado, não consertado nesta rodada.

## O que ficou gravado

| região | retângulo | piso | banda |
|---|---|---|---|
| `barra_esquerda` (EXP) | `0,1356 520x26` | 155 | 4 |
| `barra_direita` (adena) | `1520,1348 170x34` | 190 | 3 |
| `nivel` | `251,738 20x16` | 210 | 5 |

Iguais para os dois personagens **nesta configuração de janela** — o que não contradiz o
`LEIT-07`: eles coincidiram hoje porque o usuário arrastou os dois clientes para o mesmo layout,
e o esquema continua por personagem justamente porque isso pode deixar de valer a qualquer
momento. Foi o que aconteceu com a calibração de 00h45.

## A prova

Dez leituras consecutivas ao vivo, cinco por personagem, com a calibração do usuário:

    Faerlina:  nivel 67  EXP 70,8571%  adena 17.589.587
    Faerlina:  nivel 67  EXP 70,8655%  adena 17.590.176
    Faerlina:  nivel 67  EXP 70,8740%  adena 17.590.780
    Faerlina:  nivel 67  EXP 70,8801%  adena 17.591.286
    Faerlina:  nivel 67  EXP 70,8917%  adena 17.592.060

    Yazalaque: nivel 69  EXP 92,9357%  adena 4.413.339
    Yazalaque: nivel 69  EXP 92,9370%  adena 4.413.339
    Yazalaque: nivel 69  EXP 92,9383%  adena 4.413.761
    Yazalaque: nivel 69  EXP 92,9422%  adena 4.414.993
    Yazalaque: nivel 69  EXP 92,9460%  adena 4.416.220

Nível estável, EXP e adena **monotônicos crescentes** — que é o comportamento que a Fase 2 vai
transformar em taxa. Nenhum campo recusado, nenhum valor andando para trás.
