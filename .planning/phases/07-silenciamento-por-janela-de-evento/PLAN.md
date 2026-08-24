# Fase 7: Silenciamento por janela de evento

**Objetivo**: Durante TvT e Prime o scanner cala, porque em evento morre todo
mundo o tempo todo e cada morte vira uma mensagem que ninguém quer ler.

**Depende de**: Fase 6 (as janelas de silêncio SÃO a agenda)
**Requisitos**: MUTE-01 a MUTE-08

## Não é correção de bug — é filtro de relevância

Os alertas durante um TvT são **verdadeiros**: as pessoas morreram mesmo. Eles
só não são notícia. Essa distinção decide onde o código mora.

O silenciamento vive no **transporte**, depois do rastreador ter decidido e
registrado tudo normalmente. Silenciar na detecção:

- corromperia o estado — quem morre e ressuscita durante o silêncio precisa
  sair do outro lado com o estado certo;
- apagaria o log, que é a única ferramenta de depuração pós-farm do projeto.

## Onde o corte acontece

O `Despachante` recebe texto puro e não sabe de onde veio. Precisa saber, porque
**a agenda atravessa o silêncio e o resto não**. A mudança é uma categoria no
`despachar()`: `SEMPRE` para os avisos de agenda, `NORMAL` para o resto.

Alternativa descartada: um wrapper que só o caminho do rastreador consulta.
Espalharia a decisão por dois lugares e a próxima fonte de eventos esqueceria de
consultar.

---

## Tarefa 1 — A janela de silêncio, com união

**Requisitos**: MUTE-02, MUTE-03, MUTE-04

Função pura em `agenda.py`: `silencio_ativo(agora, eventos) -> JanelaDeSilencio
| None`. Junta todas as janelas que cobrem `agora` e devolve a **união**.

A união não é refinamento — é correção. De segunda a quinta o Prime vai das
20:00 às 22:00 e o TvT das 21:50 vai até 22:05. Substituir em vez de unir faria
o silêncio acabar às 22:00 e os últimos 5 minutos de TvT vazariam alerta.

O nome que vai na mensagem de encerramento é o do evento que **termina por
último** — é ele que ainda estava acontecendo.

**Verificação**:
- Teste: TvT às 15:00 com 15 min → silêncio de 15:00 a 15:15
- Teste: uma segunda às 21:55, dentro de Prime E de TvT → união termina 22:05
- Teste: a mesma segunda às 22:02 → ainda em silêncio (o Prime já acabou)
- Teste: às 22:06 → sem silêncio
- Teste: sábado às 21:55 → só TvT, termina 22:05
- Teste: varredura minuto a minuto de uma segunda inteira, comparando com as
  janelas esperadas

**Commit**: `feat(silencio): a janela de silencio, com uniao das sobrepostas`

---

## Tarefa 2 — O corte no transporte

**Requisitos**: MUTE-01, MUTE-05, MUTE-07

1. `Despachante.despachar(texto, categoria=NORMAL)`. `SEMPRE` ignora o silêncio.
2. Os avisos de agenda passam `SEMPRE`; tudo do rastreador passa `NORMAL`.
3. O que foi silenciado **continua indo para o log e para o console**. Silêncio é
   do WhatsApp, nunca do registro — sem isso um falso positivo que aconteça
   durante um TvT fica invisível para sempre.
4. O outbox: um evento silenciado **não** entra nele. O outbox existe para
   garantir que nada se perca no caminho da rede; um evento que decidimos não
   enviar não está a caminho de lugar nenhum. Ele está no log.

**MUTE-05 é o que impede a funcionalidade de se anular.** De segunda a quinta o
lembrete do TvT das 21h40 cai dentro do silêncio do Prime. Sem a categoria
`SEMPRE`, ele nunca sairia.

**Verificação**:
- Teste: com silêncio ativo, um evento de morte não chega ao notificador
- Teste: com silêncio ativo, um aviso de agenda **chega**
- Teste: o evento silenciado aparece no log
- Teste: o evento silenciado não entra no outbox
- Teste: sem silêncio, tudo passa igual a antes

**Commit**: `feat(silencio): o corte mora no transporte, e a agenda atravessa`

---

## Tarefa 3 — O fim do silêncio, e o console

**Requisitos**: MUTE-06, MUTE-08

1. Ao sair da janela, **uma** mensagem: o evento encerrou e os convites de party
   estão sendo reenviados. Sem resumo do que foi engolido — decisão do usuário.
2. **O scanner nunca envia convite no jogo.** A mensagem apenas avisa que os
   convites estão sendo reenviados; quem convida é uma pessoa. Restrição dura do
   projeto.
3. Console mostra que está em silêncio e até quando. Um scanner calado precisa
   parecer calado de propósito.
4. Vale nos dois laços — o principal e o `--so-agenda`.

**Verificação**:
- Teste: atravessar a janela produz exatamente 1 mensagem de encerramento
- Teste: a mensagem nomeia o evento que terminou por último
- Teste: ficar em silêncio por horas não repete a mensagem
- Teste: começo frio dentro de uma janela não anuncia encerramento de um evento
  que o scanner nunca viu começar
- Manual: `--so-agenda --dry-run` mostra o silêncio no console

**Commit**: `feat(silencio): o aviso de encerramento e o console`

## Fora de escopo

- Resumo do que foi silenciado — o usuário escolheu explicitamente só o aviso de
  encerramento
- Enviar convite de party — restrição dura; o scanner é somente leitura
