# Evidencia medida do anuncio de nascimento

**Capturado:** 2026-08-30, prints do usuario, cliente XM Essence
**Status:** MEDIDO. Nao e suposicao e nao e memoria — sao pixels que o usuario mandou.

Este arquivo existe porque o ROADMAP registrou, como risco, que a frase do
anuncio era ASSERCAO do usuario e nunca tinha sido capturada por este projeto.
Ele tinha suposto `[Lv. 80]`. Agora ha medida.

## A linha, exata

```
Tiat North [Lv. 60] has spawned!
```

Nivel **60**, nao 80. E por isso que o numero do nivel entra no PADRAO (prova
que a linha veio do servidor) e sai da DECISAO (nao e conferido, nao vai para a
mensagem): supor um valor teria produzido um gate que nunca casaria.

## O nome no ALVO, exato

O quadro de alvo mostra **so o nome**, sem nivel e sem colchetes:

```
Tiat North
```

Confirma que a deteccao por alvo procura o nome puro, e nao a frase.

## As TRES cores do chat, e a correcao

O orquestrador tinha afirmado que o anuncio saia em "laranja de sistema".
**Errado.** Medido no print, as tres classes de linha sao visualmente distintas:

| Linha | Cor |
|---|---|
| `Cegatt : 2:30 da manha eu to tomando meu cafe...` (jogador) | laranja |
| `-> Dragon Belt - 1 pcs: added on the market [15,54 XM Coin]` | laranja/dourado, com icone de sino |
| `Tiat North [Lv. 60] has spawned!` | **VERDE**, com icone de sino |

Consequencia para a ideia adiada de usar cor como segunda confirmacao: ela vale
MAIS do que se pensava. O verde separa o anuncio de boss ate das outras
notificacoes de sistema, nao apenas do texto dos jogadores. Continua adiada
(o padrao da frase basta hoje), mas quando for retomada o alvo e o verde.

## Caso negativo NOVO, e ele e real

```
-> Dragon Belt - 1 pcs: added on the market [15,54 XM Coin]
```

E uma linha de SISTEMA, com o MESMO icone de sino do anuncio de boss, com
COLCHETES e com NUMERO dentro dos colchetes. E o falso positivo mais plausivel
que existe neste chat — muito mais perigoso que um jogador digitando "tiat",
porque compartilha a estrutura visual do anuncio verdadeiro.

Ela nao contem `has spawned`, entao o padrao atual a rejeita. Mas ela precisa
ser um TESTE, e nao uma coincidencia: sem o caso escrito, qualquer afrouxamento
futuro do padrao pode passar a aceita-la sem ninguem perceber.

Outro caso do mesmo print, mais fraco mas gratuito:

```
Christine : PROCURO PT EM PLAINS ARCHER LVL 62 127GS
```

Jogador, com `LVL 62` — parecido com `[Lv. 60]` sem os colchetes.

## O icone antes do texto

As duas linhas de sistema tem um icone de sino desenhado ANTES do texto. Ele
vira lixo de OCR no comeco da linha. E a medida que justifica a decisao do
plano de NAO ancorar o padrao no inicio da linha (`^`) — uma ancora ali
quebraria contra o proprio anuncio verdadeiro.

## O chat e movimentado

O print mostra seis linhas em poucos segundos, de quatro pessoas diferentes,
falando de cafe, recrutamento de PT e futebol. E o que torna RECO-01 urgente e
nao cosmetico: com o gatilho antigo (`t[i1l][a4@][t7]` em qualquer lugar do
recorte), bastava um deles escrever "tiat" para a party inteira receber
mensagem.
