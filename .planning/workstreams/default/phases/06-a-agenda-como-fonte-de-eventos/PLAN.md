# Fase 6: A agenda como fonte de eventos

**Objetivo**: O grupo recebe lembrete de TvT e Prime nos horários certos, com o
jogo fechado, sem ninguém precisar lembrar.

**Depende de**: Fase 4 (o caminho de entrega)
**Requisitos**: AGEN-01 a AGEN-08, OPER-09, OPER-10, OPER-11
**Pesquisa**: [RESEARCH.md](RESEARCH.md)

## A ideia que organiza a fase

O relógio é uma **segunda fonte de eventos**, igual à tela. Ela entra pelo mesmo
`Despachante` que o rastreador usa — nunca chamando `enviar()` direto. Se furar
esse seam, o silenciamento da Fase 7 fica impossível de acrescentar sem
reescrever esta fase.

E a agenda nasce **pura**, como o rastreador: o tempo entra por parâmetro. Sem
isso, testar "o aviso das 21h50 de uma quinta" exigiria esperar até quinta.

## Ordem: fatia vertical primeiro

A Tarefa 1 é uma fatia fina de ponta a ponta — do arquivo de config até a
mensagem entregue — com qualidade de produção. Nada se expande antes dela
funcionar. Se a fatia furar, o problema aparece com um evento e uma linha de
config, não com a agenda inteira montada.

---

## Tarefa 1 — TRACER: do relógio até a mensagem, ponta a ponta

**Entrega**: um evento configurado em `config.toml` produz um aviso entregue
pelo `Despachante`.

**Arquivos**:
- `config.toml` (novo, na raiz) — **versionado**, um único evento para a fatia.
  Ao contrário do `.env` ele não tem segredo nenhum, e os horários são
  informação que a party quer preservada. Sem arquivo de exemplo separado: o
  próprio `config.toml` comentado cumpre esse papel
- `l2scanner/agenda.py` (novo) — camada pura
- `l2scanner/config.py` — passa a ler o TOML além do `.env`
- `tests/test_agenda.py` (novo)

**`config.toml` AUSENTE não é erro.** O scanner de hoje roda sem agenda nenhuma
e precisa continuar rodando. Arquivo ausente = agenda vazia = zero avisos, sem
aviso de erro e sem exceção. Só o arquivo PRESENTE E MAL FORMADO falha no
arranque. Sem essa distinção, esta fase quebra todo mundo que já usa o scanner.

**Como**:

1. `agenda.py` define `EventoAgendado` (nome, horários, dias, minutos de
   antecedência, minutos de silêncio) e `Aviso` (evento, tipo, momento alvo).
2. Função pura: `avisos_devidos(agora: datetime, eventos, ja_enviados: set[str])
   -> list[Aviso]`. Sem relógio próprio, sem I/O, sem rede.
3. `config.py` ganha `ler_agenda(caminho) -> list[EventoAgendado]` usando
   `tomllib` (stdlib — confirmado no 3.12.10 do ambiente).
4. Validação **no arranque**: horário mal formatado, dia inexistente ou lista
   vazia falham na hora de subir, com mensagem que diz qual linha está errada.
   Nunca às 15h, no meio do farm.
5. Ligação mínima no `__main__`: a cada tick, chamar `avisos_devidos` e
   `despachante.despachar(...)`.

**Verificação** (todas sem esperar relógio real):
- Teste: um evento às 15:00, `agora` = 14:50 → devolve o aviso "antes"
- Teste: `agora` = 15:00 → devolve o aviso "agora"
- Teste: `agora` = 14:30 → não devolve nada
- Teste: config com `horarios = ["25:00"]` → erro claro no arranque
- Teste: `config.toml` ausente → agenda vazia, zero avisos, zero exceção
- Teste: **a suíte inteira de 255 testes continua verde** — nenhum caminho
  existente pode mudar de comportamento por causa desta fase
- Manual: `--dry-run` com um evento posto para daqui a 1 minuto, o aviso aparece
  no console

**Commit**: `feat(agenda): o relogio vira fonte de eventos, ponta a ponta`

---

## Tarefa 2 — A agenda de verdade

**Entrega**: os dois avisos por evento, os três horários de TvT todo dia, e o
Prime de segunda a quinta.

**Requisitos**: AGEN-01, AGEN-02, AGEN-03, AGEN-04

**Como**:

1. Dois avisos por ocorrência: um em `horário - avisar_minutos_antes`, outro no
   horário. Textos diferentes — o de antes serve para se deslocar, o de agora
   para dizer que começou.
2. Filtro por dia da semana. TvT nos sete dias; Prime `seg` a `qui`.
3. `config.toml` completo, com o comentário dizendo que os horários mudam com
   atualizações e é ali que se edita.
4. O campo `silenciar_minutos` já entra no esquema e é **lido e ignorado** nesta
   fase. É a Fase 7 que passa a usá-lo — assim o usuário não edita o arquivo
   duas vezes.

**Verificação**:
- Teste parametrizado nos 7 dias: TvT dispara em todos; Prime só seg-qui
- Teste: uma sexta-feira às 20:00 não produz aviso de Prime
- Teste: os três horários de TvT produzem 6 avisos no dia (3 × antes+agora)
- Teste: mudar `avisar_minutos_antes` para 15 desloca o aviso, sem tocar em código

**Commit**: `feat(agenda): TvT todo dia, Prime de segunda a quinta`

---

## Tarefa 3 — Nunca avisar duas vezes

**Entrega**: reiniciar o scanner não reenvia; duas instâncias não duplicam; subir
atrasado não dispara aviso velho.

**Requisitos**: AGEN-06, AGEN-07, AGEN-08

**Esta é a tarefa de maior risco da fase** e a que o usuário vai notar primeiro
se falhar — ele roda **duas instâncias lado a lado** (Yazalaque e Faerlina).

**Como**:

1. Marcador por aviso em `.agenda/`, criado com `os.open(..., O_CREAT | O_EXCL)`.
   A chave é estruturada — `{data}_{evento}-{horario}_{tipo}` — nunca o texto da
   mensagem, que muda quando alguém melhora a redação.
2. `O_EXCL` é atômico no Windows: entre duas instâncias competindo, exatamente
   uma cria o arquivo. Quem criou despacha; quem levou `FileExistsError` cala.
   A mesma checagem resolve o restart, porque o marcador está em disco.
3. Janela de tolerância: um aviso só dispara até **5 minutos** depois do alvo.
   Subir o scanner às 16h não solta o aviso das 15h. Constante no código, não
   config: é uma propriedade do laço (que roda a 1 Hz), não uma preferência do
   usuário, e mais um botão no `config.toml` é mais uma coisa para ele errar.
   Cinco minutos absorve um restart demorado sem ressuscitar aviso velho.
4. Poda no arranque: marcadores de mais de alguns dias são apagados.

**Verificação**:
- Teste: dois `Agendador` sobre o mesmo diretório temporário, mesmo instante →
  exatamente 1 despacho, não 2
- Teste: despachar, recriar o agendador do zero, rodar de novo → 0 despachos
- Teste: `agora` = 16:00 com evento às 15:00 → nada
- Teste: `agora` = 15:02 com tolerância de 5 min → dispara
- Teste: poda apaga marcador velho e preserva o de hoje

**Commit**: `feat(agenda): um aviso, uma vez — a prova de restart e de duas instancias`

---

## Tarefa 4 — Rodar sem o jogo, e poder testar sem esperar as 15h

**Entrega**: o modo que roda só o relógio, o teste sob demanda, e o console.

**Requisitos**: AGEN-05, OPER-09, OPER-10, OPER-11

**Como**:

1. `--so-agenda`: laço curto e **separado**, sem fonte de frames, sem
   rastreador, sem calibração. Não é um `if` dentro do laço de captura — o laço
   de captura é o código mais crítico do projeto e não ganha ramos mortos.
2. `--testar-agenda`: despacha um aviso de exemplo agora e sai. Mesmo espírito
   do `--test-alert` que já existe.
3. Console: mostrar a próxima ocorrência e quanto falta. Um scanner que não diz
   quando vai falar de novo é indistinguível de um scanner quebrado.
4. `--dry-run` cobre tudo isso de graça, porque a agenda despacha pelo
   `Despachante` — nada a fazer além de confirmar.
5. README: a linha honesta de que **máquina desligada não avisa**. "Independente
   do jogo" não é "independente do PC".

**Verificação**:
- Manual: `--so-agenda --dry-run` roda com o jogo **fechado** e não estoura
- Manual: `--testar-agenda` chega no WhatsApp
- Teste: o cálculo de "próxima ocorrência" acerta a virada de dia (23:50 → o
  próximo TvT é às 15:00 de amanhã)
- Suíte inteira verde

**Commit**: `feat(agenda): modo so-agenda, teste sob demanda e proxima ocorrencia no console`

---

## Critérios de sucesso da fase

Copiados do ROADMAP, com como verificar cada um:

1. **Dois avisos por evento, nos horários certos** → testes das Tarefas 1 e 2
2. **Horário editável em `config.toml` sem tocar em Python** → teste da Tarefa 2
   que muda a antecedência só pelo arquivo
3. **Roda com o jogo fechado** → verificação manual da Tarefa 4
4. **Não reenvia no restart, não dispara atrasado** → testes da Tarefa 3
5. **Duas instâncias, um aviso só** → teste de concorrência da Tarefa 3

## Fora de escopo desta fase

- O silenciamento (Fase 7). O campo `silenciar_minutos` entra no esquema mas não
  é usado.
- Detectar na tela que o TvT começou. O relógio já sabe.
- Ajustar horários sozinho depois de uma atualização do jogo. Não há fonte
  confiável; é por isso que AGEN-04 existe.

## Nota de contexto

Esta fase não passou por `/gsd-discuss-phase` porque a definição do milestone
(commit `16d6804`) já resolveu as ambiguidades que importavam: antecedência,
dias, dependência do jogo, escopo do silêncio, e a fronteira de que o scanner
nunca envia convite no jogo. As respostas estão em `.planning/REQUIREMENTS.md`
e em `.planning/PROJECT.md`.
