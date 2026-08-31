---
workstream: tiat
created: 2026-08-29
---

# Project State

## Project Reference

**Core Value:** A party fica sabendo no WhatsApp que o Tiat nasceu, em
segundos, sem ninguem estar olhando a tela — e sabe com antecedencia quando a
proxima janela de respawn abre.

**Current Focus:** Fase 1 — reconhecimento preciso (a frase inteira do anuncio
do servidor, e QUAL boss) e lista de bosses no `config.toml`.

**Ponto de partida:** `l2scanner/tiat.py` ja existe, ja esta ligado em
`sessao._processar_tiat` e tem 7 testes. O encanamento ate o WhatsApp esta
inteiro; falta a PRECISAO e a PREVISAO.

## Current Position

**Status:** Roadmap criado, aguardando planejamento da Fase 1
**Current Phase:** 1 — Reconhecimento preciso e lista de bosses no config
**Last Activity:** 2026-08-30
**Last Activity Description:** ROADMAP.md criado — 2 fases, 18/18 requisitos mapeados

## Progress

**Phases Complete:** 0 / 2
**Current Plan:** N/A

```
Fase 1  [          ]  0%   Reconhecimento preciso e lista de bosses
Fase 2  [          ]  0%   Janela de respawn
```

## Accumulated Context

### Decisoes travadas (do usuario, anteriores ao roadmap)

- **D-01** O gatilho exige a frase completa do anuncio do servidor
  (`<Nome> [Lv. NN] has spawned!`), nao a mera presenca do nome. Requerer a
  frase captura North/South de graca.
- **D-02** A lista de bosses vigiados mora no `config.toml`, no molde dos
  `[[evento]]`. Mob novo e bloco novo, nunca edicao de codigo. Tiat: 6h e 8h.
- **D-03** A janela e ancorada no NASCIMENTO, nao na morte. O usuario rejeitou
  `/morreu` e rejeitou detectar a morte pela tela. O erro e conhecido e
  aceito; a mensagem tem que ser honesta sobre ele (JANE-03).
- **D-04** Dois avisos: quando a janela ABRE (min) e quando o limite passa
  (max).
- **D-05** Os avisos de janela funcionam com o jogo FECHADO, pelo relogio,
  como a agenda de TvT.

### Decisoes do roadmap

- **D-06** A ancora mora em `.agenda/`, com prefixo novo, e NAO em `.loot/`.
  `.agenda/` poda em 3 dias; a ancora vale no maximo 8h. Uma ancora imortal
  em `.loot/` produziria janelas erradas com cara de certas. Ver a secao
  "Onde o historico de spawn mora em disco" no ROADMAP.md.
- **D-07** A precisao (RECO+VIGI) vem ANTES da janela (JANE) por correcao, nao
  por gosto: ancorar uma contagem de 6h num falso positivo de chat digitado e
  pior do que nao ter previsao nenhuma.
- **D-08** JANE-04 (reancorar) e ESTRUTURAL, sem marcador de cancelamento: o
  calculo so olha a ancora mais recente por boss, entao as chaves do ciclo
  anterior deixam de vencer sozinhas.

### Contas que o planejamento nao pode pular

- **A direcao do erro da janela e sempre a mesma.** Boss nasce em `T`, morre em
  `T+k`, renasce em `[T+k+min, T+k+max]`. Ancorados em `T`, os dois avisos saem
  `k` CEDO demais, nunca tarde. Logo o aviso de `max` NAO PODE afirmar que a
  janela fechou — em `T+max` ela pode nem ter aberto. "Perdemos a janela" e
  falso.

### Riscos abertos

- **R-01** A frase `<Nome> [Lv. NN] has spawned!` e asserção do usuario, nunca
  capturada por este projeto. Confrontar com gravacao real na Fase 1.
- **R-02** Gate estrito demais na parte fixa da frase troca o falso positivo de
  hoje por um falso NEGATIVO silencioso, que e pior.
- **R-03** O guarda de `_PREFIXOS_CONHECIDOS` varre `vars(agenda)` — um
  prefixo declarado em modulo novo passa por ele sem levantar nada.
- **R-04** Dois lugares de fiacao para JANE-05: `laco_da_agenda` e
  `laco_principal`. Consertar so um faz os dois divergirem.

## Session Continuity

**Stopped At:** ROADMAP.md escrito e traceability preenchida
**Resume File:** `.planning/workstreams/tiat/ROADMAP.md`
**Next:** planejar a Fase 1

## Estado

Milestone COMPLETO. Duas fases, ambas verificadas por execucao.

| Fase | Entrega | Verificacao |
|------|---------|-------------|
| 1 | Reconhecimento preciso: so o anuncio do servidor dispara, a mensagem diz QUAL boss, e a lista mora no config.toml | 8/8 criterios; G-01 achado e corrigido |
| 2 | Janela de respawn: ancora em disco com a origem no nome, avisos de abertura e limite, funcionando com o jogo fechado | 8/8 criterios, 0 gap |

O que falta e VALIDACAO EM CAMPO, nao implementacao: ver o anuncio real do
Tiat disparar o aviso no WhatsApp, e ver a janela abrir 6h depois.

A vigia esta calibrada na janela do Yazalaque (medida 2026-08-30 as 14:27,
regioes tiat_chat 8,878 625x455 e tiat_alvo 350,772 160x24, provadas contra
OCR real). A SEGUNDA instancia usa a mesma calibracao e NAO foi conferida.

## Fase 3 (2026-08-30) — defeito de campo, fechado

Seis mensagens para um nascimento viraram uma. Duas causas, as duas medidas:

1. O aviso de nascimento era o UNICO do projeto sem marcador duravel, entao as
   duas instancias anunciavam cada uma. Agora passa por `marcar()`, com a chave
   ancorada no nascimento MAIS ANTIGO do episodio — nao no instante da
   deteccao (as instancias ticam em minutos diferentes: 21:59 contra 22:01) e
   nao na ancora mais recente (a remarcacao a reescreve).

2. ACHADO DURANTE O PLANEJAMENTO, e pior que o spam: o chat ja era engolido
   pelo alvo. `_armado[boss]` era um flag so, entao um boss segurado no alvo
   descartava a frase do servidor DENTRO do vigia, antes de qualquer disco —
   sem ancora, sem log, sem rastro. Era o inverso exato da regra do usuario
   ("o chat sempre avisa, pois eu posso estar longe do computador"). O rearme
   passou a ser por (canal, boss).

Os sete testes de rearme atravessaram byte a byte: `git diff` sobre
`tests/test_bosses.py` deu 126 adicoes e 0 remocoes.

Suite: 2821 passando, zero falha.

## A margem foi DESCARTADA pela medicao (2026-08-31)

O usuario tinha aprovado um campo `margem_apos_nascimento_minutos`. A medicao
derrubou a ideia, e o raciocinio vale ficar escrito porque ele reaparece.

**A deriva por remarcacao NAO e defeito.** Seis ancoras de `Tiat North` entre
22:22 e 22:29 pareciam deriva de 7 minutos "para depois". Mas o usuario estava
LUTANDO nesse intervalo, e a luta termina na MORTE. A ultima marcacao nao esta
se afastando da verdade: esta caminhando para ela. `22:29` e uma estimativa
melhor da morte que `22:22`.

**As duas perguntas sao diferentes e o codigo ja as separa:**

  - "qual nascimento e este?"  -> ancora MAIS ANTIGA (identidade do episodio,
    usada pelo marcador do anuncio desde a Fase 3)
  - "quando ele morreu?"       -> ancora MAIS RECENTE (previsao da janela,
    usada por `ancoras_mais_recentes` desde a Fase 2)

O orquestrador chegou a recomendar trocar a previsao para a mais antiga. Teria
PIORADO a previsao. A recomendacao foi retirada antes de virar plano.

**Os numeros do usuario, ditos por ele:**

  - lutando: ele segura o alvo ate a morte; a ultima marcacao cai 5 a 10 min
    depois do nascimento -> a ancora JA E a morte, erro ~= zero
  - ausente: so o chat, ancora no nascimento, erro de 5 a 10 min ADIANTADO —
    o lado que ele escolheu, e que ele avaliou como "ja esta otimo"

Nos dois caminhos o desenho atual acerta. Uma margem de 15 min empurraria o
caminho do chat para o lado ERRADO (atrasado), que e o que faz perder o boss.

MORT-01 (o comando `/morreu`) continua sendo a unica saida exata, e continua
em v2 — agora com a razao mais forte: ele so vale a pena para quem NAO luta.

## Medido: os dois avisos chegaram (31/08)

Tiat South nasceu 30/08 21:59 (chat) -> janela abriu 31/08 05:59
Tiat North ancorado 30/08 22:29 (alvo) -> janela abriu 31/08 06:29

**CONFIRMADO PELO USUARIO em 31/08: os dois chegaram no WhatsApp.** JANE-02 e
JANE-05 ficam validados EM CAMPO, e nao so por teste.

O que isso prova, e que a suite nao provava: o caminho inteiro atravessou —
ancora gravada na noite anterior por DOIS caminhos diferentes (o chat para o
South, o alvo para o North), a conta de 8h+2h sobrevivendo a um scanner que
dorme e acorda, e o despacho saindo com o jogo FECHADO. Este ultimo e o
proposito declarado do JANE-05: quem mais precisa saber que a janela abriu e
justamente quem nao esta com o jogo aberto.

Fica de fora do que foi validado: se a janela ACERTOU o nascimento. O aviso
chegou na hora certa da CONTA; se o boss nasceu perto dela e outra medicao, e
ela precisa do proximo episodio com horario de morte conhecido.
