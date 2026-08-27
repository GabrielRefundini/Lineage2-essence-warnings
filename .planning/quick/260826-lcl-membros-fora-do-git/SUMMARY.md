---
phase: quick/260826-lcl
plan: membros-fora-do-git
subsystem: config
tags: [tomllib, gitignore, config, privacidade, pytest]

requires:
  - phase: 10-solo-boss-join
    provides: "os [[membro]] e o `.join`/`.leave` que dependem deles"
provides:
  - "`config.local.toml` (ignorado pelo git) como fonte dos [[membro]]"
  - "precedencia local-vence-versionado em `ler_membros`, com aviso de arranque"
  - "`config.local.exemplo.toml` versionado como modelo a copiar"
  - "guarda de teste no modelo versionado, alem do ja existente no config.toml"
affects: [config, comandos, presenca, onboarding]

actuals:
  tokens: 36076
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Par arquivo-versionado / arquivo-local com precedencia explicita e aviso quando ambos existem"
    - "Leitura crua separada da validacao, para validar so o arquivo vencedor"

key-files:
  created:
    - config.local.exemplo.toml
  modified:
    - l2scanner/config.py
    - config.toml
    - .gitignore
    - README.md
    - tests/test_comandos.py

key-decisions:
  - "O `config.toml` continua versionado: por ele no .gitignore deixaria `TestAgendaRealDoUsuario` vigiando um exemplo que ninguem edita — verde e inutil, que e pior que ausente"
  - "Precedencia e um-ou-outro, nunca soma: somar faria um nick apagado reaparecer e poria a validacao de nick repetido para arbitrar entre arquivos"
  - "Com os dois arquivos carregando bloco, o arranque avisa em WARNING nomeando vencedor e ignorado"
  - "Um `caminho` explicito le SO aquele arquivo, sem procurar vizinho — do contrario o guarda do arquivo versionado passaria a ler a maquina de quem roda o teste"
  - "So o arquivo vencedor e validado: derrubar o arranque por um bloco ja sem efeito aponta para o arquivo errado"

patterns-established:
  - "Divisao projeto/maquina: o que e do PROJETO fica versionado (agenda), o que e da MAQUINA nao (calibracao, telefones)"
  - "Todo arquivo `*.exemplo.*` versionado ganha um teste afirmando que nao carrega dado real"

requirements-completed: []

coverage:
  - id: D1
    description: "`ler_membros` le o `config.local.toml` quando ele tem bloco e o `config.toml` quando nao tem, nos quatro estados de presenca dos dois arquivos"
    verification:
      - kind: unit
        ref: "tests/test_comandos.py#TestMembrosNoArquivoLocal::test_so_o_versionado_le_do_versionado"
        status: pass
      - kind: unit
        ref: "tests/test_comandos.py#TestMembrosNoArquivoLocal::test_so_o_local_le_do_local"
        status: pass
      - kind: unit
        ref: "tests/test_comandos.py#TestMembrosNoArquivoLocal::test_os_dois_o_local_vence_e_NAO_soma"
        status: pass
      - kind: unit
        ref: "tests/test_comandos.py#TestMembrosNoArquivoLocal::test_nenhum_dos_dois_e_lista_vazia_sem_excecao"
        status: pass
    human_judgment: false
  - id: D2
    description: "Com bloco nos dois arquivos, o arranque avisa alto nomeando o vencedor e o ignorado"
    verification:
      - kind: unit
        ref: "tests/test_comandos.py#TestMembrosNoArquivoLocal::test_os_dois_o_arranque_AVISA_nomeando_os_dois_arquivos"
        status: pass
      - kind: unit
        ref: "tests/test_comandos.py#TestMembrosNoArquivoLocal::test_so_o_versionado_NAO_avisa"
        status: pass
    human_judgment: false
  - id: D3
    description: "A validacao (nick repetido, telefone curto, charset) e escrita uma vez e vale nas duas origens"
    verification:
      - kind: unit
        ref: "tests/test_comandos.py#TestMembrosNoArquivoLocal::test_a_validacao_vale_igual_vinda_do_local"
        status: pass
      - kind: unit
        ref: "tests/test_comandos.py#TestMembrosNoArquivoLocal::test_telefone_curto_no_local_tambem_derruba_no_arranque"
        status: pass
    human_judgment: false
  - id: D4
    description: "O caminho padrao (`ler_membros()` sem argumento), que e o que o `__main__` chama, aplica a precedencia"
    verification:
      - kind: unit
        ref: "tests/test_comandos.py#TestMembrosNoArquivoLocal::test_o_caminho_local_PADRAO_e_o_que_o_arranque_usa"
        status: pass
    human_judgment: false
  - id: D5
    description: "Nem o `config.toml` nem o `config.local.exemplo.toml` versionados carregam telefone de ninguem"
    verification:
      - kind: unit
        ref: "tests/test_comandos.py#TestMembroNoConfigToml::test_o_config_toml_do_REPOSITORIO_nao_carrega_telefone_de_ninguem"
        status: pass
      - kind: unit
        ref: "tests/test_comandos.py#TestMembrosNoArquivoLocal::test_o_EXEMPLO_do_repositorio_tambem_nao_carrega_telefone_de_ninguem"
        status: pass
      - kind: other
        ref: "git show HEAD:config.toml | grep -c '^\\[\\[membro\\]\\]' => 0"
        status: pass
    human_judgment: false
  - id: D6
    description: "`config.local.toml` e ignorado pelo git e `config.local.exemplo.toml` nao e"
    verification:
      - kind: other
        ref: "git check-ignore -v config.local.toml => .gitignore:51"
        status: pass
      - kind: other
        ref: "git status --short => config.local.exemplo.toml aparece untracked, depois commitado"
        status: pass
    human_judgment: false
  - id: D7
    description: "`TestAgendaRealDoUsuario` continua lendo o `config.toml` DO REPOSITORIO e continua verde"
    verification:
      - kind: unit
        ref: "tests/test_agenda.py#TestAgendaRealDoUsuario (12 passed)"
        status: pass
    human_judgment: false
  - id: D8
    description: "O usuario cria o proprio `config.local.toml` com os cinco party-mates e o scanner volta a reconhece-los"
    verification: []
    human_judgment: true
    rationale: "O arquivo carrega telefones reais e nao existe neste worktree de proposito. So o usuario, na maquina dele, pode criar o arquivo e confirmar que um `.join` de cada membro e aceito."

duration: 25min
completed: 2026-08-26
status: complete
---

# Quick 260826-lcl: Membros fora do git — Summary

**Os `[[membro]]` mudam do `config.toml` versionado para um `config.local.toml` ignorado pelo git, com precedencia um-ou-outro e aviso de arranque quando os dois carregam bloco — e o `config.toml` continua versionado para nao cegar o teste que vigia a agenda.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-08-26T21:07-03:00 (aprox.)
- **Completed:** 2026-08-26T21:29:41-03:00
- **Tasks:** 2
- **Files modified:** 5 modificados + 1 criado

## Accomplishments

- `ler_membros` passa a preferir o `config.local.toml` e a cair no `config.toml` quando ele nao existe ou nao tem bloco — **um ou outro, nunca a soma**.
- Com bloco nos dois arquivos, o arranque grita em WARNING e **nomeia os dois**: qual vale e qual esta sendo ignorado. Sem isso, o usuario reeditaria o arquivo morto a noite inteira.
- `config.local.toml` entrou no `.gitignore` com o porque escrito por extenso; `config.local.exemplo.toml` entrou versionado como modelo a copiar.
- O bloco de comentario do `config.toml` parou de mandar escrever os telefones nele mesmo e passou a apontar o arquivo novo, explicando por que a agenda fica e o telefone sai.
- Onze testes novos: os quatro estados de presenca dos dois arquivos, o aviso (e a ausencia dele quando nao ha conflito), a validacao valendo nas duas origens, o caminho padrao que o `__main__` usa, e dois guardas de vazamento.

## Task Commits

1. **Tarefa 1 (RED): os quatro estados dos dois arquivos** — `c6711fc` (test)
2. **Tarefa 1 (GREEN): `ler_membros` le o arquivo local** — `6dcabaa` (feat)
3. **Tarefa 2: o repositorio volta a nao carregar telefone de ninguem** — `7f57320` (feat)

## Files Created/Modified

- `config.local.exemplo.toml` — **criado.** Modelo versionado, so cabecalho e dois `[[membro]]` comentados com numeros de exemplo. A explicacao longa de cada campo continua no `config.toml`; aqui vai so o formato e o porque da separacao.
- `l2scanner/config.py` — `ler_membros(caminho, caminho_local)` com a precedencia e o aviso; `_blocos_de_membro` extraido para ler cru sem validar; `ARQUIVO_CONFIG_LOCAL`; logger de modulo; o comentario da secao de membros reescrito com a decisao inteira.
- `config.toml` — o bloco de comentario aponta o `config.local.toml`. O exemplo continua comentado; zero `[[membro]]` ativos.
- `.gitignore` — `config.local.toml`, com o porque na mesma voz das entradas do `.env` e do `calibration.json`.
- `README.md` — paragrafo novo em "Mandar comando pelo WhatsApp": onde os party-mates ficam, o que um `[[membro]]` alcanca e o que nao alcanca, e o passo de copiar o exemplo.
- `tests/test_comandos.py` — `TestMembrosNoArquivoLocal` (11 testes).

## Decisions Made

**1. O `config.toml` continua versionado.** Por ele no `.gitignore` era a primeira ideia e a mais simples, e quebrava um guarda real: `tests/test_agenda.py::TestAgendaRealDoUsuario` le o `config.toml` **do repositorio** para afirmar os horarios de TvT, Prime e Solo Boss. Fora do git, aquele teste passaria a vigiar um `config.exemplo.toml` que ninguem edita — continuaria verde e pararia de guardar, que e pior do que nao existir porque parece protecao. Entao o telefone e que sai do arquivo, nao o arquivo do git.

**2. Precedencia e um-ou-outro, nunca soma.** Somar os dois arquivos faria um nick apagado do `config.toml` reaparecer pelo local sem ninguem entender por que, e poria a validacao de nick repetido para decidir qual dos dois arquivos ganha — decisao sem resposta obvia, tomada as 2h da manha. A precedencia inteira cabe num `or`.

**3. Um `caminho` explicito le SO aquele arquivo.** A alternativa (derivar o irmao `config.local.toml` ao lado de qualquer caminho passado) parecia mais consistente e teria quebrado silenciosamente o `test_o_config_toml_do_REPOSITORIO_nao_carrega_telefone_de_ninguem` **na maquina do usuario**, onde o `config.local.toml` existe: aquele guarda passaria a ler os telefones reais e acusaria o arquivo errado. So a chamada sem argumento nenhum — que e como o `__main__` chama — aplica a precedencia entre os dois arquivos padrao. Ha um teste dedicado a cada metade dessa regra.

**4. So o arquivo vencedor e validado.** A leitura crua saiu para `_blocos_de_membro` por causa disso: para saber qual arquivo manda e preciso primeiro saber quais tem bloco. Validar o perdedor derrubaria o arranque por causa de um bloco que ja nao autoriza ninguem — erro que aponta para o arquivo errado, pior do que erro nenhum. Erro de sintaxe TOML, esse sim, derruba vindo de qualquer um dos dois, e a mensagem cita o **nome do arquivo**: com dois arquivos em jogo, "o TOML esta quebrado" sem dizer qual e um convite a editar o errado.

## Deviations from Plan

### Ajuste de escopo recebido do orquestrador (nao e desvio auto-decidido)

A Tarefa 2 do PLAN.md mandava mover os cinco `[[membro]]` reais do `config.toml` para um `config.local.toml` na maquina. O worktree parte do HEAD, onde o `config.toml` ja e a versao limpa do repositorio — **nao havia telefone nenhum aqui para mover, e nenhum foi escrito.** O orquestrador retem o roster real e cria o `config.local.toml` no checkout principal apos o merge. Verificado: `git show HEAD:config.toml | grep -c "^\[\[membro\]\]"` devolve **0**, e `config.local.toml` nao existe neste worktree.

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Guarda no `config.local.exemplo.toml`**

- **Found during:** Tarefa 2
- **Issue:** A tarefa fecha a porta do `config.toml` e abre um arquivo versionado novo, feito **para ser copiado**. Um "salvar" no arquivo errado poe o telefone de um party-mate no repositorio pela porta que acabou de ser fechada — com o agravante de que ninguem olha duas vezes para um arquivo chamado "exemplo". O plano nao pedia guarda para ele.
- **Fix:** `test_o_EXEMPLO_do_repositorio_tambem_nao_carrega_telefone_de_ninguem`, espelhando o guarda que ja existe do outro lado. Afirma tambem que o arquivo **existe** — sem isso, o README mandaria copiar um arquivo ausente e o usuario voltaria a escrever os telefones no `config.toml`.
- **Files modified:** `tests/test_comandos.py`
- **Verification:** teste verde; o modelo parseia como TOML valido e devolve zero membros.
- **Committed in:** `7f57320`

---

**Total deviations:** 1 auto-fix (Rule 2 — guarda de seguranca ausente). Zero scope creep: nenhuma funcionalidade nova, so cobertura para a superficie que esta tarefa criou.

## Issues Encountered

Nenhum. A suite subiu de **1066 passed, 2 skipped** para **1077 passed, 2 skipped** (11 testes novos), nenhum teste existente alterado nem enfraquecido, e `TestAgendaRealDoUsuario` continua lendo o `config.toml` versionado (12 passed).

## Deferred Issues

`python -m ruff check .` acusa 26 achados **pre-existentes** (E741 `l` ambiguo em `l2scanner/visao.py`, `tests/test_console.py`, `test_identidade.py`, `test_party_estavel.py`, `test_visao.py`; F401 em `test_sessao.py` e `test_voce_na_party.py`). Nenhum nos arquivos desta tarefa — `ruff check l2scanner/ tests/test_comandos.py` passa limpo antes e depois. Fora de escopo por serem anteriores a esta mudanca e nao terem relacao com ela.

## Known Stubs

Nenhum.

## User Setup Required

**O `config.local.toml` do usuario ainda nao existe.** Enquanto ele nao for criado no checkout principal, o `.join` para de reconhecer os party-mates — o `config.toml` nao tem mais bloco ativo e nao vai voltar a ter. Passo: copiar `config.local.exemplo.toml` para `config.local.toml` e preencher os cinco membros. O orquestrador retem o roster.

## Next Phase Readiness

- O caminho de leitura esta fechado e coberto; nada mais depende desta tarefa no codigo.
- Pendencia unica e a de operacao: o `config.local.toml` na maquina do usuario (D8, acima).
- Nota para quem for abrir o PR desta branch: o historico **desta** branch nunca recebeu telefone real. Se algum commit anterior a `2fb2001` tiver recebido, este trabalho nao o remove — apagar dado de historico exige reescrita, que e outra conversa.

---
*Quick: 260826-lcl-membros-fora-do-git*
*Completed: 2026-08-26*

## Self-Check: PASSED

Os 7 arquivos declarados existem em disco e os 3 hashes de commit existem no historico (`7f57320`, `6dcabaa`, `c6711fc`). Verificado tambem: `git show HEAD:config.toml | grep -c "^[[membro]]"` devolve 0, `git check-ignore config.local.toml` casa em `.gitignore:51`, e `config.local.toml` nao existe neste worktree.
