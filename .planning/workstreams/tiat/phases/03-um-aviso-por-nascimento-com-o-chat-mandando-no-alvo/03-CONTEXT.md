# Phase 3: Um aviso por nascimento, com o chat mandando no alvo - Context

**Gathered:** 2026-08-30
**Workstream:** tiat
**Status:** Ready for planning
**Origem:** DEFEITO DE CAMPO. A Fase 1 e a 2 foram verificadas e passaram; este
defeito so aparece com duas instancias reais e um humano remarcando o alvo.

<domain>
## Phase Boundary

O aviso de nascimento para de repetir. Hoje ele sai uma vez por instancia, e de
novo a cada vez que o usuario remarca o boss no alvo.

DENTRO DA FASE: o marcador duravel do aviso de nascimento; a precedencia do
chat sobre o alvo; o silencio de um aviso por boss por janela.

FORA DA FASE: o reconhecimento (Fase 1) e o calculo da janela (Fase 2), os dois
verificados. A ancora NAO muda de comportamento — ela continua sendo gravada
como esta, inclusive pelo alvo; o que muda e o ANUNCIO.

</domain>

<o_defeito_medido>
## O que o usuario recebeu, em 2026-08-30

    21:59  Tiat South nasceu! (visto no chat do jogo)      x3
    22:01  Tiat South nasceu! (seu alvo virou Tiat South)
    22:02  Tiat South nasceu! (seu alvo virou Tiat South)   x2

Seis mensagens para UM nascimento. Duas causas independentes, somadas:

**CAUSA 1 — o aviso de nascimento nao tem marcador duravel.**
`sessao._processar_bosses` chama `self._despachar(...)` DIRETO, sem
`registro.marcar()`. Todo outro aviso do projeto passa por ele: a agenda em
`sessao.py:530`, a janela de respawn em `sessao.py:605`. Este nao. Entao as
DUAS instancias do usuario (Yazalaque e Faerlina, ambas rodando, confirmado por
`Win32_Process`) anunciam cada uma, e reiniciar anuncia de novo.

Nao e bug de implementacao: e lacuna de REQUISITO. RECO-05 pedia "chat e alvo
no mesmo tick geram UM alerta". Ninguem escreveu "um alerta por nascimento,
entre instancias e entre reinicios" — e por isso nenhum teste pegou.

**CAUSA 2 — o alvo rearma quando o usuario remarca o boss.**
Isto ja esta DOCUMENTADO em `sessao.py`, no comentario de `_processar_bosses`,
como custo aceito de D-15:

  "o alvo REARMA quando ele desmarca e remarca o boss, entao um Tiat South
   retomado as 15h grava uma ancora nova sobre a mesma criatura que ja estava
   viva as 14h30, e a conta reinicia. Foi escolha por COBERTURA, com o preco
   apresentado."

O preco foi apresentado e aceito. O campo mostrou que ele e mais alto do que
parecia no papel: nao e uma repeticao ocasional, e uma por remarcacao.

</o_defeito_medido>

<decisions>
## Implementation Decisions

### A regra, ditada pelo usuario em 2026-08-30

1. **O CHAT SEMPRE AVISA.** Nunca e suprimido pela logica de deduplicacao do
   alvo. A razao e do usuario, e ela decide o desenho: *"pois eu posso estar
   longe do computador"*. O anuncio do servidor e o unico sinal que existe
   quando ninguem esta olhando a tela — e o caminho confiavel, e o produto
   inteiro depende dele.

2. **O ALVO AVISA SO COMO FALLBACK.** Se o chat nao pegou aquele boss nesta
   janela, o alvo fala. Se pegou, o alvo cala. Ele continua existindo para o
   caso real que o usuario descreveu: o scanner perdeu o anuncio (estava
   fechado, ou o OCR falhou) e o boss esta na frente dele.

3. **UM AVISO POR BOSS POR JANELA.** Depois de anunciar um boss, o scanner cala
   sobre ele ate a janela de respawn daquele boss passar. O que se perde e o
   caso de o MESMO boss nascer duas vezes dentro da mesma janela — impossivel
   pela regra do servidor (8h a 10h entre nascimentos).

### O que NAO muda

- **A ancora continua sendo gravada como hoje**, inclusive pelo alvo. D-15
  (os dois sinais ancoram) segue valendo — o usuario escolheu cobertura e nao
  voltou atras. O que esta fase muda e o ANUNCIO, nao a ancoragem.
- **D-16 continua valendo**: a mensagem cita qual sinal ancorou.
- Nenhum comportamento da Fase 1 ou 2, ambas verificadas.

### Claude's Discretion

- Nome e forma da chave do marcador de anuncio.
- Como "nesta janela" e calculado — o `respawn.py` ja sabe montar as ancoras e
  as janelas por boss; reusar em vez de reimplementar.
- Se o silencio por janela e um marcador proprio ou deriva da ancora existente.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`agenda.RegistroEmDisco.marcar`** — `O_CREAT|O_EXCL`, a decisao de
  despachar. Provado em quatro lugares do projeto. A docstring proibe por
  escrito uma checagem anterior: ela reintroduz a corrida entre ler e escrever,
  e o resultado e um aviso PERDIDO, nao duplicado.
- **`sessao.py:530` e `sessao.py:605`** — os dois sitios que ja fazem certo. O
  aviso de nascimento e o unico que nao faz.
- **`respawn.py`** — ja monta ancoras e janelas por boss a partir do disco. E
  quem sabe dizer "esta janela".
- **`agenda._PREFIXOS_CONHECIDOS` + o guarda derivado** — todo prefixo novo
  entra na poda, e ha teste que deriva a lista por introspecao.
- **`bosses.VigiaDeBosses`** — o rearme em memoria continua util como primeiro
  filtro barato (evita bater no disco a cada tick); o marcador e a garantia.

### Established Patterns

- **Tempo por parametro**; portao AST sobre `agenda`, `loot`, `presenca`,
  `bosses`, `respawn`.
- **Portugues SEM acento**; sem travessao em texto de usuario.
- **A decisao de despachar E a chamada de `marcar`.**

### Integration Points

- `l2scanner/sessao.py` — `_processar_bosses`, o sitio do defeito
- `l2scanner/respawn.py` — de onde vem "qual janela"
- `l2scanner/agenda.py` — o prefixo novo e a poda
- `l2scanner/bosses.py` — se a precedencia chat-sobre-alvo morar no vigia

</code_context>

<specifics>
## Specific Ideas

- Confirmado por `Win32_Process` em 2026-08-30: DUAS instancias rodando,
  ambas `-m l2scanner --janela`, subidas as 21:28:47.
- O usuario roda duas instancias por desenho (Yazalaque e Faerlina), e isso e
  premissa do projeto desde a Fase 1 — nao e configuracao acidental.
- O paliativo dado ao usuario enquanto isso: fechar uma instancia corta a
  duplicacao pela metade; nao remarcar o boss evita o resto.

</specifics>

<deferred>
## Deferred Ideas

- Revisitar D-15 (o alvo ancorar). Esta fase resolve o RUIDO sem mexer na
  ancoragem; se a imprecisao da ancora por alvo incomodar depois, e outra
  conversa e tem o `/morreu` (MORT-01) como saida.

</deferred>
