# Phase 2: Janela de respawn - Context

**Gathered:** 2026-08-30
**Workstream:** tiat
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — 2 decisoes do usuario, o resto herdado do ROADMAP

<domain>
## Phase Boundary

O scanner passa a PREVER, e nao so a reagir. Ao ver um nascimento, ele grava o
instante em disco e, `min` horas depois, avisa que a janela abriu; em `max`,
avisa que o limite otimista passou. Funciona com o jogo fechado, pelo relogio.

DENTRO DA FASE: a ancora em disco; o calculo da janela; os dois avisos; a
fiacao nos DOIS lacos; a linha de arranque com a previsao; o modulo novo no
portao AST de relogio.

FORA DA FASE: qualquer mudanca no reconhecimento (Fase 1, fechada e verificada).
O comando `/morreu` (MORT-01, v2) e o aprendizado do tempo-de-vida (APRE-01, v2).

</domain>

<decisions>
## Implementation Decisions

### As duas decisoes do usuario (2026-08-30)

- **OS DOIS SINAIS ANCORAM.** Tanto o anuncio no CHAT quanto o boss no ALVO
  iniciam a contagem. O usuario escolheu isto sabendo do preco, que foi
  apresentado: ter o boss marcado NAO prova que ele acabou de nascer — pode
  ser um boss de pe ha duas horas, que foi exatamente o caso observado hoje as
  14h30. Ancorar no alvo pode adiantar a previsao em horas.

  A escolha foi por COBERTURA: se o scanner estava fechado quando o anuncio
  passou, o alvo e a unica chance de ter alguma previsao. Uma previsao com erro
  conhecido vale mais que nenhuma previsao — DESDE QUE o erro seja legivel.

- **A MENSAGEM CITA QUAL SINAL ANCOROU.** E isto que torna a decisao acima
  segura, e nao uma armadilha. "o servidor anunciou as 14:30" e "seu alvo virou
  Tiat South as 14:30" sao frases diferentes, e quem le julga sozinho o quanto
  confiar. Nao ha um terceiro texto de ressalva: a propria citacao da origem E
  a ressalva. Isto satisfaz JANE-03 sem inventar decisao nova.

- **DOIS AVISOS POR CICLO, e nenhum lembrete de antecedencia.** Um quando a
  janela ABRE (`min`) e um quando o limite passa (`max`). O usuario recusou um
  terceiro aviso ~30min antes: com dois Tiats vigiados, seriam seis mensagens
  por ciclo, e o volume e exatamente o que fez o Solo Boss perder o
  `avisar_no_horario` na Fase 6.

### Herdadas do ROADMAP (nao sao decisao nova, sao restricao)

- **A ancora mora em `.agenda/`**, marcador vazio, prefixo proprio, forma
  `nascimento_<YYYY-MM-DD>_<boss-slug>-<HHMM>_<origem>`.

  A ORIGEM ENTRA NO NOME, e nao no conteudo (decidido pelo usuario em
  2026-08-30, no checkpoint bloqueante do plano 02-01). D-16 exige que a
  mensagem cite qual sinal ancorou, e essa informacao precisa sobreviver as 6
  horas entre o nascimento e o aviso — inclusive a um reinicio. Poe-la no
  CONTEUDO quebraria a propriedade que sustenta tudo: o marcador e VAZIO, e a
  criacao atomica com `O_CREAT|O_EXCL` E a decisao inteira de despacho. Um
  "cria e depois escreve" abriria uma janela em que a outra instancia le um
  arquivo vazio e nao sabe a origem.

  Esta forma SUBSTITUI a escrita mais acima nesta secao; ela e a que vale.
  A decisao e de mao unica: depois que o primeiro arquivo existir, mudar o
  formato invalida as ancoras ja gravadas. A poda de 3 dias e a razao da
  escolha, e nao um efeito colateral: uma ancora velha NAO e neutra, e
  PERIGOSA — no `.loot/`, que nunca poda, uma ancora de duas semanas
  continuaria produzindo janelas erradas com cara de certas. 3 dias e 9x a vida
  util maxima de 8h.
- **A mensagem de `max` NAO pode afirmar que a janela fechou.** Ancorados no
  nascimento e nao na morte, os dois avisos saem `k` cedo demais (onde `k` e
  quanto o boss ficou vivo), nunca tarde. Em `T+max` a janela pode nem ter
  aberto. "Perdemos a janela" seria uma afirmacao FALSA entregue no grupo.
- **JANE-04 e estrutural, sem marcador de cancelamento:** o calculo olha so a
  ancora MAIS RECENTE por boss, entao as chaves do ciclo anterior deixam de
  vencer sozinhas.
- **A decisao de despachar E a chamada de `marcar`**, nunca uma checagem
  anterior — a docstring de `RegistroEmDisco.marcar` proibe por escrito, e e o
  que garante que as duas instancias nao anunciem em dobro.
- **A tolerancia de 5 minutos vale aqui.** Um aviso vencido ha tres horas nao
  pode sair quando o usuario sobe o scanner as 22h.
- **`Categoria.SEMPRE`** — os avisos de janela atravessam o silencio de TvT,
  como os de nascimento ja fazem.

### Claude's Discretion

- Nome do modulo novo e da classe.
- Se `TipoDeAviso` do `agenda.py` ganha `ABRE`/`FECHA` ou se o modulo novo tem
  tipo proprio dividindo so a convencao de chave. O ROADMAP aponta o tipo
  proprio como leitura padrao, mas exige a justificativa escrita.
- Redacao exata das quatro mensagens (abre/fecha x ancorado-em-chat/alvo).
- Onde mora a funcao compartilhada pelos dois lacos (o molde e
  `_fechar_listas_de_presenca`).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`agenda.RegistroEmDisco`** — `marcar()` com `O_CREAT|O_EXCL` resolve
  restart E corrida entre as duas instancias de uma vez. A ancora e os avisos
  reusam isso.
- **`agenda.RegistroEmDisco.podar` + `_PREFIXOS_CONHECIDOS`** — a poda ja
  alcanca todo prefixo declarado, e ha um teste que DERIVA a tupla por
  introspecao de `vars(agenda)`. ATENCAO: esse guarda so varre `agenda.py` —
  um `PREFIXO_*` declarado em modulo novo passa por ele sem levantar nada.
  Ou o prefixo e declarado dentro de `agenda.py`, ou o guarda e estendido.
- **`agenda.Aviso.chave`** — a convencao `<data>_<apelido>-<HHMM>_<tipo>`, que
  faz a poda por data funcionar sem regra nova e impede que melhorar a redacao
  reenvie um aviso.
- **`agenda.chave_da_ocorrencia`** — o idioma de identidade ja usado por
  `.loot/` e pela lista de presenca.
- **`presenca.fechar_ocorrencias` + `_fechar_listas_de_presenca`** — o molde
  EXATO de "logica de tempo extraida do laco, fiada nos dois lacos". A Fase 10
  do workstream `default` resolveu o mesmo problema; copiar a forma.
- **`bosses.VigiaDeBosses`** — ja devolve `list[AvisoDeBoss]` com `origem`
  (CHAT / ALVO), que e exatamente o dado que a mensagem precisa citar.

### Established Patterns

- **Tempo por parametro.** Portao AST sobre `agenda.py`, `loot.py`,
  `presenca.py`, `bosses.py` — o modulo novo entra na tupla.
- **Funcoes puras primeiro, IO na borda.**
- **Portugues SEM acento** em identificador, docstring, comentario e texto de
  WhatsApp. Sem travessao em texto de usuario.
- **Docstrings explicam POR QUE, com medida de campo.**
- **`loot.py` nunca importa `comandos`, `sessao` nem `presenca`** — ha portao
  de AST; o modulo novo nao pode fechar ciclo.

### Integration Points

- `l2scanner/bosses.py` — de onde vem `AvisoDeBoss.origem`
- `l2scanner/agenda.py` — `RegistroEmDisco`, o prefixo novo, a poda
- `l2scanner/sessao.py` e `l2scanner/__main__.py` — os DOIS lacos
- `config.toml` — `respawn_horas_min` / `respawn_horas_max`, ja lidos e
  validados na Fase 1 e ate agora IGNORADOS. Esta fase e quem os usa.
- `tests/test_presenca.py` — a tupla `MODULOS` do portao AST

</code_context>

<specifics>
## Specific Ideas

- Regra do servidor, dita pelo usuario: apos a MORTE, 6h fixas + 0 a 2h
  aleatorias. Nasce entre 6h e 8h depois de morrer.
- O usuario tem DOIS Tiats vigiados (North e South), que nascem
  independentemente. Sao duas ancoras separadas, e o volume de mensagem dobra.
- Medido em campo hoje: um `Tiat South` estava no alvo do usuario as 14h30 sem
  ter acabado de nascer — a party estava no meio da luta. E o caso concreto que
  torna a ancora por alvo imprecisa, e o motivo de a mensagem ter de citar a
  origem.
- O erro NAO se acumula entre ciclos: cada nascimento detectado reancora.

</specifics>

<deferred>
## Deferred Ideas

- `/morreu <boss>` para ancorar na morte (MORT-01, v2) — o unico jeito de a
  previsao ficar exata.
- Aprender o tempo tipico entre nascimento e morte e descontar (APRE-01, v2).
- Lembrete de antecedencia antes de a janela abrir — recusado por volume.
- Usar a cor CIANO da linha do anuncio como segunda confirmacao. Medido na
  Fase 1: ciano e o anuncio, laranja e o trade dos jogadores. Continua adiado.

</deferred>
