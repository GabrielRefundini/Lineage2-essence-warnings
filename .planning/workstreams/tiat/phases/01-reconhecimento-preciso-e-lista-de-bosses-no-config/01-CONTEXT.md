# Phase 1: Reconhecimento preciso e lista de bosses no config - Context

**Gathered:** 2026-08-30
**Workstream:** tiat
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — 1 area, 6 decisoes, todas aceitas como propostas

<domain>
## Phase Boundary

O alerta de boss raro para de disparar com qualquer "tiat" no recorte do chat e
passa a exigir o ANUNCIO DO SERVIDOR. Junto, ele passa a dizer QUAL boss
nasceu, e a lista de vigiados sai do codigo para o `config.toml`.

DENTRO DA FASE: a regra de reconhecimento; a identidade do boss; os blocos
`[[boss]]` no config e sua validacao; o debounce virando estado por boss; o
renomeio do modulo; o texto da mensagem.

FORA DA FASE: a janela de respawn e tudo que depende dela (Fase 2). Os campos
`respawn_horas_min` / `respawn_horas_max` sao LIDOS e VALIDADOS aqui, e
IGNORADOS — moram no esquema desde ja para o usuario nao ter que editar duas
vezes o mesmo arquivo. Mesma tecnica que `silenciar_minutos` usou na Fase 6.

</domain>

<decisions>
## Implementation Decisions

### Area 1: Reconhecimento do anuncio

- **A frase e casada com FOLGA na parte fixa.** O padrao e
  `<nome> [Lv. <numero>] has spawned`, com a tolerancia de OCR aplicada tambem
  a parte fixa (`5`/`s`, `0`/`o`, e as trocas que o modulo ja trata). O `!`
  final e OPCIONAL: pontuacao e o que o OCR mais perde, e exigi-la trocaria o
  falso positivo de hoje por um falso NEGATIVO silencioso — que e pior, porque
  ninguem percebe que o aviso nao saiu.
- **A identidade vem do config, nao de regex por boss.** O nome declarado no
  `[[boss]]` e procurado imediatamente antes de `[Lv.`. `Tiat North` e
  `Tiat South` saem distintos de graca, sem o usuario escrever expressao
  regular nenhuma — ele so escreve o nome como aparece no jogo.
- **O nivel entra no PADRAO e sai da DECISAO.** `[Lv. NN]` existe para provar
  que a linha e anuncio do servidor e nao alguem digitando; o numero em si e
  ignorado. Se o servidor mudar o nivel do Tiat, nada quebra e ninguem precisa
  editar config. Nao e conferido contra o config e nao vai para a mensagem.
- **O modulo e renomeado para `l2scanner/bosses.py`**, com `VigiaDeBosses`.
  `tiat.py` vira mentira no instante em que a lista e configuravel, e nome
  errado e divida que so fica mais cara. RESTRICAO DURA: os 7 testes de
  `tests/test_tiat.py` migram INTACTOS — so o import muda. Eles sao a regua do
  debounce, que e o ativo mais valioso do modulo.
- **Dois blocos, nao um com lista.** `Tiat North` e `Tiat South` sao dois
  `[[boss]]` separados, porque sao dois bosses: nascem em horarios
  independentes e cada um tera sua propria ancora na Fase 2. Um bloco com lista
  de nomes colapsaria as duas ancoras numa so.
- **A mensagem comeca pelo nome do boss.** `Tiat North nasceu! (visto no chat
  do jogo)` / `(seu alvo virou Tiat North)`. O nome primeiro porque e a
  informacao que decide para onde a party se desloca; o "TIAT DETECTADO" de
  hoje enterra isso.

### Claude's Discretion

- Nome exato dos campos do `[[boss]]` alem de `nome` (a proposta e
  `respawn_horas_min` / `respawn_horas_max`).
- Como a tolerancia de OCR e escrita (tabela de substituicao vs. regex por
  caractere) — desde que valha para o nome E para a parte fixa.
- Se `VigiaDeBosses` recebe os bosses no construtor ou por parametro.
- Redacao exata das mensagens de erro de validacao, respeitando o formato de
  `_evento_de_dict` ("o boss 'X' tem ...").

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`l2scanner/tiat.py` inteiro** — `VigiaDoTiat` ja tem o debounce por rearme
  (duas leituras limpas rearmam; uma falha isolada de OCR nao), ja e injetavel
  (`ler_texto`, `agora` por parametro), ja trata excecao de OCR sem derrubar o
  tick. E o ponto de partida, nao uma pagina em branco.
- **`sessao._processar_tiat`** — ja chama o vigia a cada tick com os dois
  recortes e ja despacha com `Categoria.SEMPRE`, atravessando o silencio de
  TvT. Nao precisa mudar de forma.
- **`__main__.montar_vigia_do_tiat`** — ja monta a partir da calibracao e ja
  degrada com mensagem quando falta calibracao. E o molde de VIGI-04.
- **`config._evento_de_dict`** — a validacao dos `[[evento]]` e o analogo exato
  da validacao dos `[[boss]]`: mesma forma de mensagem, mesma recusa de subir.
- **`calibracao.tiat_chat` / `tiat_alvo`** — as regioes ja existem no esquema e
  ja sao lidas/gravadas. OPER-01 e sobre o TEXTO nao nomear um mob, nao sobre
  mudar o formato.
- **`gravador` + `--replay`** — o instrumento para confrontar a frase real sem
  esperar um spawn.

### Established Patterns

- **Tempo por parametro; nenhum `datetime.now()`** nos modulos de logica.
- **Nome sempre da configuracao**, nunca lido de fora e usado como identidade.
- **Validacao de config derruba o arranque nomeando o campo** — nunca sobe
  vigiando errado em silencio.
- **Portugues SEM acento** em identificador, docstring, comentario e texto de
  WhatsApp.
- **Docstrings explicam POR QUE, com medida de campo.**

### Integration Points

- `l2scanner/tiat.py` -> `l2scanner/bosses.py` (renomeio)
- `l2scanner/config.py` — leitura e validacao dos `[[boss]]`
- `l2scanner/__main__.py` — `montar_vigia_do_tiat` vira `montar_vigia_de_bosses`
- `l2scanner/sessao.py` — o import e o nome do campo
- `config.toml` — os dois blocos do Tiat
- `tests/test_tiat.py` -> `tests/test_bosses.py`
- `calibrar-tiat.bat` e o texto de `calibrar.py --tiat`

</code_context>

<specifics>
## Specific Ideas

- **A frase real, medida do print do usuario (2026-08-30):**
  `Tiat North [Lv. 60] has spawned!`
  O ROADMAP supos `[Lv. 80]`; o print mostra **60**. Isto e evidencia, nao
  suposicao — e o motivo de o numero do nivel nao entrar em decisao nenhuma.
- A linha aparece no chat com icone proprio e em COR de sistema (laranja),
  distinta do texto dos jogadores. A cor NAO e usada nesta fase (o padrao da
  frase basta), mas fica registrada porque e o reforco disponivel se um falso
  positivo aparecer em campo.
- O chat geral do usuario e movimentado — o print mostra varias conversas
  simultaneas. E o que torna RECO-01 urgente e nao cosmetico.
- Regra de respawn do servidor: 6h fixas + 0 a 2h aleatorias apos a MORTE.
  Registrada aqui porque alimenta os campos do config; usada so na Fase 2.

</specifics>

<deferred>
## Deferred Ideas

- Usar a COR da linha do chat como segunda confirmacao. So se um falso positivo
  real aparecer — hoje seria complexidade sem defeito observado.
- Conferir o nivel lido contra o config. Descartado: quebraria calado no dia em
  que o servidor mudasse o nivel.
- Comando `/morreu <boss>` para ancorar a janela na morte (MORT-01, v2).
- Vigiar mobs comuns. O volume de mensagem inviabiliza.

</deferred>
