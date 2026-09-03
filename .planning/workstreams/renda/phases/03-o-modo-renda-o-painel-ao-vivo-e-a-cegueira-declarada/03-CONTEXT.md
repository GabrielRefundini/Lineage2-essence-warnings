# Phase 3: O modo `--renda` — Context

**Gathered:** 2026-09-03
**Status:** Ready for planning
**Mode:** Áreas cinzentas decididas pelo agente, com a alternativa registrada. O usuário aprovou
seguir ("sim") depois de perguntar se já dava para ver no dashboard — e a resposta foi não,
porque **ninguém está gravando ainda**. Esta fase é quem grava.

<domain>
## Phase Boundary

Esta fase entrega **o processo que roda a noite inteira**: captura em laço, chama a leitura da
Fase 1, chama a conta e o registro da Fase 2, e mostra o resultado numa tela que se atualiza.

Dentro: o laço, o lançador, o painel, e os motivos de cegueira que só um laço ao vivo produz.

Fora: **nenhuma regra de leitura nova, nenhuma conta nova, nenhum segundo portão de admissão.**
A fronteira do roadmap vale inteira — esta fase produz motivos de recusa e os entrega ao portão
que a Fase 2 já tem. Duas portas para o mesmo arquivo é como um arquivo passa a ter duas verdades.

O precedente estrutural literal é `mercado_modo.py`, cuja própria docstring se descreve como
*"o CHAMADOR que faltava"* — a Fase 2 do mercado entregou leitor e registro sem chamador, e o
modo os ligou. Aqui é idêntico: `renda_leitura`, `renda_conta` e `renda_registro` existem sem
chamador de produção, de propósito.

</domain>

<decisions>
## Implementation Decisions

### Área 1 — A tela: o roadmap está errado sobre ela, duas vezes

- **`rich` NÃO está instalado e não é importado em lugar nenhum.** Confirmado agora:
  `ModuleNotFoundError: No module named 'rich'`, e zero ocorrências em `l2scanner/`. O
  `ROADMAP.md` e o `CLAUDE.md` citam `rich.Live` como se existisse; **os dois estão velhos.**
  Este é o mesmo tipo de premissa que a Fase 1 derrubou cinco vezes, e ela cai antes de custar
  uma onda.
- **E a segunda metade também cai:** o "ao vivo" desta casa **não é um painel de tabela**. É
  `mercado_console.linha_ao_vivo`, que devolve **uma linha** repintada, sobre
  `console.py` (`LARGURA = 58`, `moldurar`, `destacar`, `_pintar`) — feito à mão, sem
  dependência. O critério 1 do roadmap diz "no mesmo `rich.Live` das telas que já existem" e
  **nenhuma tela existente usa isso**.
- **Decisão: seguir o que existe, não o que o roadmap imaginou.** A tela da renda é construída
  sobre `console.py`, na forma do `mercado_console`. Sem dependência nova.
  *Alternativa registrada:* instalar `rich` e fazer um `Live` com tabela. Custa uma dependência
  nova num produto que hoje sobe com `uv sync` e nada mais, e cria a segunda convenção de tela
  do repositório. Se o usuário quiser a tabela, é troca dele — não do executor.
- **Dez a doze números não cabem numa linha de 58 colunas.** O plano decide a forma (bloco
  repintado com múltiplas linhas, ou uma linha densa com o resto em `moldurar`), mas **decide
  medindo**: escreve a linha mais longa possível com os valores reais medidos
  (`nível 67 · EXP 79,2568% · adena 17.592.060 · 2,41 M XP/h · 466 mil adena/h · falta 3h20`) e
  vê o que cabe. `console.LARGURA` é 58 e não vai ser aumentado por esta fase sem argumento.

### Área 2 — "Parado" e "cego" são coisas diferentes, e a fase existe por causa disso

- **Três estados, não dois:** *lendo* (tudo normal), *cego* (não estou vendo — jogo fechado,
  minimizado, tela de login, frame congelado) e *parado* (estou vendo, e os valores não mudam).
  O terceiro é o que o roadmap chama de CEGO-02 e é o caso mais provável de todos: o usuário
  senta e para de matar. `SaudeDoFrame` diria "saudável" — o frame muda, a nuvem passa.
- **A staleness de VALOR é uma camada nova, acima da de pixel — e ela não pode virar recusa.**
  Renda zero é um fato legítimo sobre o farm; cegueira é uma falha da medição. Se "parado"
  virasse recusa, o arquivo perderia justamente a evidência de que o usuário ficou uma hora
  parado, e a taxa da sessão mentiria para cima (o denominador encolheria).
  **Decisão: "parado" GRAVA normalmente e só muda a TELA.** Só a cegueira suspende a gravação.
  *Alternativa registrada:* tratar parado como lacuna. Mais simples, e apaga a informação que o
  usuário mais quer de manhã: "quanto tempo eu fiquei parado?".
- **Cegueira é REUSO, e reescrevê-la é passivo.** `frames.SaudeDoFrame`,
  `FRAMES_IDENTICOS_PARA_CONGELADO = 30`, `cliente.EstadoDoCliente.TELA_DE_LOGIN`,
  `esta_na_tela_de_login`, `captura_janela.JanelaSource` — quatro rodadas de correção no v1.
  Esta fase **classifica e nomeia**, não detecta de novo.
- **"Coberto por outra janela" NÃO é cegueira, e isso agora é medição.** Toda a medição de campo
  da Fase 1 foi feita com o jogo atrás do navegador, nas duas instâncias — o `mss` devolvia a
  tela do browser e a `JanelaSource` leu o jogo normalmente. **Minimizado continua impossível** e
  a fase declara a pausa em vez de prometer contorná-la.

### Área 3 — O LEIT-10, que é desta fase e o roadmap não listou

- **A banda de brilho anda com o cenário, e isso está medido três vezes.** A do EXP da Faerlina
  foi de `140..170` para `160..180` em 8,5 horas; e no dia seguinte a janela inteira subiu ~8 px
  e as três regiões morreram de uma vez, com o usuário vendo os três campos recusados.
- **Decisão: antes de declarar cegueira, o laço tenta os pisos VIZINHOS da banda gravada** e usa
  o que produzir leitura válida, **registrando qual piso usou**. É o `LEIT-10`, cujo dono
  declarado é esta fase — a Fase 1 não podia fazê-lo porque seria estado dentro de uma função
  que a fase inteira definiu como pura.
- **O piso que funcionou não é gravado de volta no `calibration.json` automaticamente.** Ele vai
  para a tela e para o registro. Um laço que reescreve a calibração sozinho tira do usuário a
  única âncora que ele tem para saber que a calibração envelheceu.
  *Alternativa registrada:* auto-recalibrar. Mais confortável e muito mais difícil de auditar.

### Área 4 — O processo e o lançador

- **`vigiar-renda.bat`, processo separado**, na família dos quatro `.bat` que já existem.
  Derrubar um não derruba os outros — critério 2 do roadmap.
- **`--janela` obrigatório**, como no `--mercado`, e pelo mesmo motivo: duas instâncias, e renda
  é do personagem. Herdar a resolução do título pela chave `[jogo] personagem`, não reinventar.
- **A cadência é calibrada, não fixa.** Medido: uma leitura completa dos três campos custa
  dezenas de ms a alguns segundos (o OCR domina), e o EXP a 55 Hz mostrou que o degrau de um
  abate é 0,001 pp — não há razão para ler mais que ~1 Hz. O default vai no `config.toml`, na
  seção `[renda]` que o `02-01` já criou.

### Claude's Discretion

- Nomes de módulo e função; a forma exata do painel dentro da restrição de `console.LARGURA`.
- Se o laço vive em `renda_modo.py` (que já existe, com o comando de leitura única) ou em módulo
  próprio.
- Quantos pisos vizinhos tentar e em que ordem.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `l2scanner/mercado_modo.py` — **o precedente estrutural exato**: o laço que liga captura,
  leitura e registro, com `Contagem` e as duas metades contadas honestamente.
- `l2scanner/renda_leitura.py`, `renda_conta.py`, `renda_registro.py`, `renda_ponte.py` — as
  Fases 1 e 2, todas sem chamador de produção.
- `l2scanner/console.py` — `LARGURA = 58`, `moldurar`, `destacar`, `_pintar`, e a marca de
  componente velho.
- `l2scanner/mercado_console.py` — `linha_ao_vivo`, e a disciplina de `n` e recência.
- `l2scanner/frames.py`, `cliente.py`, `captura_janela.py` — a cegueira já resolvida.
- `l2scanner/relogio.py` — o tempo por parâmetro.

### Established Patterns
- O laço é casca fina; a decisão mora em módulo puro testável sem jogo aberto.
- Recusa nomeada em vez de valor degradado.
- Nada de constante mágica no fonte.

### Integration Points
- `.renda/` — nasce de verdade nesta fase (a Fase 2 escreveu o escritor; ninguém o chamou).
- `config.toml`, seção `[renda]` — já existe, criada pelo `02-01`.
- **Nenhum arquivo do workstream `dashboard`.** O contrato é o arquivo em disco.

</code_context>

<specifics>
## Specific Ideas

- O usuário perguntou explicitamente se já dava para ver no dashboard. Não dava, e o motivo é
  esta fase. **O produto desta fase, do ponto de vista dele, é `.renda/` deixando de estar
  vazio.**
- Valores reais para a tela caber: `nível 67`, `EXP 79,2568%`, `adena 17.592.060`,
  `2,41 M XP/h`, `466 mil adena/h`, `falta 3h20`.
- Taxas de recusa medidas em campo, que o painel vai exibir de verdade: nível 79%, adena 21%,
  EXP 0%. Um painel que não mostre isso faz o usuário achar que o scanner travou.

</specifics>

<deferred>
## Deferred Ideas

- A **ferramenta que mede a ponte de XP** em laço (ler o chat em cadência alta e calcular a
  constante do nível novo). Hoje existe como script de bancada; ela vira necessária no próximo
  level up, e é candidata natural a esta fase — mas nenhum requisito a pede e ela não bloqueia
  nada. Se o plano couber, entra; se não, é tarefa própria.
- A página da renda no navegador — workstream `dashboard`, não este.
- Avisar no WhatsApp quando a renda cair (ALER-01, v2).

</deferred>
