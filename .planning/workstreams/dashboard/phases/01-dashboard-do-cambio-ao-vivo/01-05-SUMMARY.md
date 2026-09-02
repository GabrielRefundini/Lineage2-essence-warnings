---
phase: 01-dashboard-do-cambio-ao-vivo
plan: 05
subsystem: infra
tags: [http.server, stdlib, csrf, csp, path-traversal, cache, socket, windows]

requires:
  - phase: 01-01
    provides: "montar_servidor, Manipulador, Servidor, CSP e PASTA_DOS_ESTATICOS — o tracer que esta fase endureceu, mais a fixture de porta efemera com poll_interval medido"
  - phase: 01-02
    provides: "payload(pasta, agora, cambio=None) — a montagem do JSON, que continua pura e entra no cache sem saber que existe cache"
  - phase: 01-03
    provides: "gravar_o_cambio, ler_o_cambio, CambioInvalido, HistoricoDoCambioIlegivel e MENSAGEM_DE_CAMBIO_INVALIDO — o portao de duas camadas que o POST CHAMA em vez de repetir"
  - phase: 01-04
    provides: "a biblioteca vendorizada em vendor/, que virou o diretorio sem indice do teste de listagem e o alvo do controle positivo de travessia"
provides:
  - "Servidor com allow_reuse_address DESLIGADO: dois dashboards na mesma porta falham em voz alta, com frase acionavel em vez de traceback"
  - "list_directory sobrescrito para 404: a listagem de diretorio nunca aparece"
  - "origem_permitida(cabecalhos, porta) — funcao PURA, o unico ponto de decisao do portao de CSRF, com controle negativo de seis assercoes"
  - "do_POST em /cambio com os portoes na ordem (caminho, origem, teto do corpo, formato, valor), cada falha com resposta propria"
  - "CacheDaLeitura por (tamanho, mtime_ns) + minuto + identidade do cambio, com invalidacao apos gravar"
  - "main(argv) com --porta e --sem-navegador, e o bloco de execucao direta do modulo (DASH-06)"
  - "PORTA_PADRAO, INTERVALO_DE_POLLING_MS, TETO_DO_CORPO_DO_POST e as quatro mensagens de recusa, todas com a razao escrita"
  - "tests/test_dashboard_servidor.py — 79 provas sem navegador: travessia com controle positivo E negativo, VEND-4 diretiva a diretiva, origem, porta, cache, desligamento e a sessao inteira de somente-leitura"
affects: [01-06, 01-07, 01-08]

actuals:
  tokens: 23320
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Portao de CSRF em funcao pura, testavel sem servidor, com controle negativo cobrindo os dois sentidos do sinal moderno"
    - "Cache com chave composta (arquivo + tempo + dependencia externa) em vez de so o arquivo, quando o valor cacheado depende do relogio"
    - "Controle negativo de sonda de seguranca com alvo FALSO em tmp_path: prova que a sonda tem dentes sem expor a arvore real"
    - "Uma mensagem por CAUSA, nunca a frase da vizinha reaproveitada"

key-files:
  created:
    - tests/test_dashboard_servidor.py
  modified:
    - l2scanner/dashboard.py

key-decisions:
  - "allow_reuse_address = False, com a medicao refeita nesta arvore: com o padrao (=1) o segundo bind na mesma porta passa CALADO; com False ele levanta errno 10048, que e o unico desfecho que da para mostrar ao usuario"
  - "PORTA_PADRAO = 8787, escolhida por TRES restricoes (abaixo de 49152; fora das portas de dev disputadas; livre na medicao), com as faixas excluidas pelo Windows coladas do netsh e o aviso de que elas mudam a cada boot"
  - "O portao de origem confere os DOIS sinais: Sec-Fetch-Site presente manda; ausente, a decisao cai para o Origin — nem recusa universal nem permissao universal"
  - "So http://127.0.0.1:<porta>, nunca localhost: um nome resolvivel por DNS e a porta de entrada classica para um dominio externo apontar para o endereco local"
  - "A chave do cache carrega o MINUTO e a identidade do cambio, e nao so (tamanho, mtime_ns): a chave so-de-arquivo congelaria o aviso de dado velho, e a tela afirmaria frescor sobre um numero de horas atras"
  - "O gerado_em nunca sai do cache — ele e sempre o instante real, porque um carimbo congelado por ate 59 s seria lido pela pagina como servidor mudo"
  - "Cada falha do POST tem resposta propria: 400 do cambio invalido (frase travada), 400 do corpo ilegivel, 409 do historico ilegivel, 500 da gravacao. 409 e nao 400 no historico: o pedido esta certo, o disco e que nao esta"
  - "O Decimal vira string na fronteira HTTP, declarado no ponto exato: JSON nao tem Decimal, e um numero voltaria float do outro lado"

patterns-established:
  - "Controle negativo de sonda de seguranca: alem do controle positivo (um arquivo que existe responde 200), a bateria de travessia prova que as sondas ALCANCAM o alvo quando a defesa e removida — 6 das 10 vazam com o directory= um nivel acima, medido"
  - "Chave de cache composta quando o valor depende do relogio: arquivo + janela de tempo, com os campos verdadeiramente instantaneos reescritos a cada resposta"
  - "Recusa antes da leitura: origem e Content-Length sao conferidos antes de o corpo existir na memoria, e a conexao e fechada porque os bytes ficaram no soquete"

requirements-completed: [DASH-01, DASH-02, DASH-04, DASH-06]

coverage:
  - id: D1
    description: "Dois dashboards abertos por engano nao dividem a porta em silencio: o segundo bind levanta erro de endereco em uso e o programa mostra uma frase acionavel, nunca um traceback"
    requirement: DASH-06
    verification:
      - kind: unit
        ref: "tests/test_dashboard_servidor.py::TestAPortaNaoEDIVISIVEL::test_o_SEGUNDO_bind_na_mesma_porta_LEVANTA_endereco_em_uso"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_servidor.py::TestOMainSobeECaiEmVozAlta::test_main_sobre_uma_porta_ja_OCUPADA_devolve_1_sem_levantar"
        status: pass
    human_judgment: false
  - id: D2
    description: "Uma pagina de outro site aberta no mesmo navegador nao consegue gravar o cambio: POST com origem ausente ou diferente e recusado com 403, e o cambio anterior continua valendo"
    requirement: DASH-02
    verification:
      - kind: unit
        ref: "tests/test_dashboard_servidor.py::TestOPortaoDeOrigemEUmaFuncaoPURA (6 assercoes, controle negativo sobre a funcao pura)"
        status: pass
      - kind: integration
        ref: "tests/test_dashboard_servidor.py::TestOPOSTDoCambio::test_a_origem_de_OUTRO_SITE_e_recusada_com_403_e_NADA_e_gravado"
        status: pass
    human_judgment: false
  - id: D3
    description: "Nenhuma sonda de travessia de caminho alcanca arquivo fora do diretorio dos estaticos, e as sondas provadamente TEM dentes"
    requirement: DASH-01
    verification:
      - kind: integration
        ref: "tests/test_dashboard_servidor.py::TestATravessiaNaoPassa (10 sondas + controle positivo + controle negativo)"
        status: pass
    human_judgment: false
  - id: D4
    description: "VEND-4: toda resposta carrega a CSP com default-src 'none' e connect-src 'self', afirmavel sem navegador, diretiva a diretiva, no estatico e no endpoint"
    verification:
      - kind: integration
        ref: "tests/test_dashboard_servidor.py::TestOsCabecalhosDeSeguranca (7 diretivas x 2 caminhos + erro + igualdade com a constante)"
        status: pass
    human_judgment: false
  - id: D5
    description: "O CSV so e relido quando tamanho ou mtime mudam, e o aviso de dado velho continua aparecendo mesmo com o arquivo parado"
    requirement: DASH-04
    verification:
      - kind: unit
        ref: "tests/test_dashboard_servidor.py::TestOCacheDaLeitura (7 testes, incluindo o do minuto e o do dado velho)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Derrubar o dashboard nao derruba a coleta, e a unica escrita do servidor e o cambio.json: uma sessao inteira nao muda um byte do observacoes.csv"
    requirement: DASH-01
    verification:
      - kind: integration
        ref: "tests/test_dashboard_servidor.py::TestOServidorNaoEscreveNoCSV::test_cinquenta_pedidos_e_um_POST_nao_mudam_um_BYTE_do_CSV"
        status: pass
      - kind: unit
        ref: "tests/test_dashboard_servidor.py::TestOMainSobeECaiEmVozAlta::test_o_modulo_tem_o_bloco_de_EXECUCAO_DIRETA_que_o_lancador_chama"
        status: pass
    human_judgment: false
  - id: D7
    description: "O desligamento e limpo: shutdown, server_close e join encerram a thread e devolvem a porta ao sistema"
    verification:
      - kind: unit
        ref: "tests/test_dashboard_servidor.py::TestODesligamentoELimpo (2 testes)"
        status: pass
    human_judgment: false
  - id: D8
    description: "O `main` abre o navegador no endereco em que o servidor subiu, e o usuario ve a pagina sem digitar URL"
    requirement: DASH-06
    verification: []
    human_judgment: true
    rationale: "`webbrowser.open` entrega o endereco ao navegador padrao do sistema; o que acontece a partir dali (a janela abrindo, a aba certa, a pagina renderizando) so e observavel com um navegador de verdade. O CONTEXT desta fase declarou verificacao humana para o desenho na tela e recusou Playwright por instalador pesado. O caminho testavel — o servidor subir, a porta, o codigo de saida e a recusa em voz alta — esta coberto por D1."

duration: 33min
completed: 2026-09-02
status: complete
---

# Phase 01 Plan 05: O servidor endurecido Summary

**O `http.server` da stdlib virou um servidor que recusa: porta nao roubavel com frase acionavel, listagem desligada, dez sondas de travessia com controle negativo medido, `POST /cambio` com portao de origem em funcao pura, e um cache cuja chave sabe que o tempo passa.**

## Performance

- **Duration:** 33 min
- **Started:** 2026-09-01T23:35Z (aproximado — leitura do plano e dos quatro SUMMARYs anteriores)
- **Completed:** 2026-09-02T00:08Z
- **Tasks:** 3
- **Files modified:** 2 (1 criado, 1 modificado)

## Accomplishments

- **A porta deixou de ser roubavel, e a medicao esta no fonte.** Reproduzida nesta arvore hoje: `http.server.HTTPServer.allow_reuse_address` vale `1` por padrao, dois processos bindam `127.0.0.1:8791` sem erro nenhum, e com `False` o segundo levanta `errno 10048`. Dois cliques no `.bat` agora produzem uma frase que o usuario consegue agir, e nao dois `python.exe` disputando o `accept`.
- **O portao de CSRF existe, e ele e uma funcao pura com controle negativo de seis assercoes.** E a defesa que a CSP nao cobre: a politica protege a NOSSA pagina de carregar coisa de fora, e nao impede uma pagina de fora de mandar um POST para a NOSSA API. As duas assercoes finais do controle negativo prendem a metade do `Sec-Fetch-Site` nos dois sentidos — ela nao pode ser omitida nem invertida.
- **As dez sondas de travessia ganharam DENTES.** O controle positivo (um arquivo que existe responde 200) ja impedia um servidor que negasse tudo de passar. O que faltava era provar que as sondas alcancam alguma coisa: com o `directory=` apontado um nivel acima, **6 das 10 vazam** (medido). Sem isso, dez `404` eram um silencio com cara de verde.
- **VEND-4 fechado.** A CSP e afirmada diretiva a diretiva, num estatico e no endpoint, e tambem nas respostas de ERRO — que sao HTML que o navegador renderiza e que ficariam descobertas se a CSP morasse em cada rota em vez de no funil de `end_headers`.
- **O cache sabe que o tempo passa.** A chave `(tamanho, mtime_ns)` que o plano pedia congelaria o aviso de dado velho; a chave implementada carrega tambem o minuto e a identidade do cambio, e o `gerado_em` nunca sai do cache.
- **A promessa de somente-leitura esta provada no nivel do SERVIDOR.** 50 `GET /dados` mais um `POST /cambio` valido nao mudam tamanho, `mtime_ns` nem `sha256` do `observacoes.csv`, o unico arquivo novo na pasta e o `cambio.json`, e nenhum temporario ficou para tras.

## Task Commits

1. **Tarefa 1: o bind exclusivo, a listagem desligada, o cache e o `main`** — `0c6bfc0` (feat)
2. **Tarefa 2: `POST /cambio` com portao de origem** — `da23d35` (test, RED) e `d365bd1` (feat, GREEN)
3. **Tarefa 3: a bateria de provas sem navegador** — `df3d1c4` (test)

_A tarefa 2 era `tdd="true"`: o RED foi commitado com 22 falhas, e as duas que passavam sao esperadas (uma da tarefa 1 apanhada pelo seletor por substring — `test_a_re**post**a...` —, e a outra afirmando que um GET no caminho do cambio nao grava nada, um invariante que ja valia porque nao havia escritor nenhum). Nenhum REFACTOR foi necessario._

**Nota sobre metadados:** este plano rodou como agente paralelo em worktree; `STATE.md` e `ROADMAP.md` sao do orquestrador, e nao ha commit de metadados aqui.

## Files Created/Modified

- `l2scanner/dashboard.py` — modificado. Ganhou `PORTA_PADRAO`, `INTERVALO_DE_POLLING_MS`, `TETO_DO_CORPO_DO_POST`, `RESOLUCAO_DO_CACHE`, `CAMPO_DO_POST`, `CAMINHO_DO_CAMBIO`, as cinco mensagens de recusa e a de confirmacao, `origem_permitida`, `CacheDaLeitura`, `Manipulador.list_directory`, `Manipulador.do_POST`, `Manipulador._recusar`, `Servidor.allow_reuse_address = False`, `Servidor.__init__` com o cache, `main(argv)` e o bloco de execucao direta.
- `tests/test_dashboard_servidor.py` — criado. 79 testes coletados, 78 passam e 1 pula com a razao dita.

## Decisions Made

- **`PORTA_PADRAO = 8787`, por tres restricoes e nao por gosto.** Abaixo de 49152 (acima disso o Windows reserva blocos inteiros para WinNAT/Hyper-V, e essas faixas **mudam a cada reinicializacao** — por isso a restricao e a FAIXA e nao a lista medida); fora de 3000/5000/8000/8080, que estao livres mas sao as mais disputadas por qualquer outra ferramenta; e livre na medicao de hoje.
- **`allow_reuse_port` nao foi tocado.** Ele existe desde o 3.11 (medido: `hasattr` verdadeiro, valor `False`) e mapeia `SO_REUSEPORT`, que nao existe no Windows. Mexer nele seria escrever uma linha que nao faz nada na unica plataforma em que este programa roda.
- **So `http://127.0.0.1:<porta>`, nunca `localhost`.** O lancador abre o navegador no numero, entao o caminho honesto sempre casa. Aceitar o nome acrescentaria uma resolucao de DNS, que e a porta de entrada classica para um dominio externo apontar para o endereco local.
- **404 e nao 403 na listagem de diretorio.** "Existe mas voce nao pode ver" e uma informacao; "nao existe" nao e. Nao ha aqui um usuario a quem explicar a diferenca.
- **409 e nao 400 para `HistoricoDoCambioIlegivel`.** O pedido esta certo; o estado do disco e que nao esta. Um 400 diria ao usuario que ele digitou errado.
- **A frase de confirmacao sai do Python, em ASCII sem acento.** O `## Copywriting Contract` trava `Câmbio salvo — 1 XM = R$ 0,50, informado por você em 01/09 14:32.`; a implementada e a mesma modulo acentuacao, seguindo o precedente que o `01-03` ja abriu com `MENSAGEM_DE_CAMBIO_INVALIDO`. As duas aparecem no MESMO canto da tela, e duas frases irmas com acentuacao diferente sao um defeito visivel. Reescreve-la no JS seria o segundo formatador que o DASH-03 proibe.
- **`--sem-navegador` acrescentado ao `main`.** Sem ele, exercitar o `main` na suite abriria o navegador do usuario a cada rodada. Ele tambem serve ao `.bat` de quem ja tem a aba aberta.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] A chave do cache pedida pelo plano congelaria o aviso de dado velho**
- **Found during:** Tarefa 1 (o cache)
- **Issue:** O plano pedia `CacheDaLeitura` com chave `(st_size, st_mtime_ns)`. Mas o payload **nao depende so do arquivo**: `payload` decide `velho` comparando `agora` com o carimbo da ultima observacao, e monta `recencia` a partir da mesma diferenca. Com a chave so-de-arquivo, um CSV parado as 14:10 devolveria, as 19:00, o mesmo dicionario com `velho=False` — e a tela afirmaria frescor sobre um numero de cinco horas atras. Esse e exatamente o modo de falha que o DASH-04 e o `## Copywriting Contract` existem para proibir ("a tela nunca afirma 'agora'"), e ele so apareceria **depois de uma hora de janela aberta**, que e quando ninguem esta olhando para descobrir. O `gerado_em` congelado tem um segundo efeito: a pagina o leria como servidor mudo.
- **Fix:** A chave carrega `(tamanho, mtime_ns)` **mais** o minuto de `agora` truncado por `RESOLUCAO_DO_CACHE` **mais** a identidade do cambio. Um minuto e a menor unidade que qualquer texto derivado de tempo neste payload chega a mostrar (`ha 8 h (31/08 10:00)`), entao recalcular mais de uma vez por minuto nao muda um caractere do que o usuario le. A economia continua valendo: a 2 s de polling, isso troca 30 recalculos por minuto por UM — com o arquivo de 60.000 linhas medido na pesquisa (540 ms por recalculo), a diferenca entre ~27% de um nucleo e ~0,9%. E o `gerado_em` e reescrito com o instante real a cada resposta, nunca saindo do cache.
- **Files modified:** `l2scanner/dashboard.py`
- **Verification:** `test_o_MINUTO_novo_recalcula_mesmo_com_o_arquivo_PARADO` (o mecanismo), `test_o_aviso_de_DADO_VELHO_aparece_mesmo_com_o_arquivo_PARADO` (a consequencia visivel) e `test_o_gerado_em_do_cache_e_SEMPRE_o_instante_de_verdade`
- **Committed in:** `0c6bfc0`

**2. [Rule 2 - Missing Critical] A porta reservada pelo Windows precisa de mensagem PROPRIA**
- **Found during:** Tarefa 1 (o `main`)
- **Issue:** O plano manda traduzir "endereco em uso" para `MENSAGEM_DE_PORTA_OCUPADA`. Mas o Pitfall 4 da pesquisa descreve uma **segunda** falha de bind que chega por outro caminho: uma porta dentro das faixas que o Windows reserva. Medido nesta arvore hoje, bindar 49200 ou 53500 levanta `PermissionError`, `errno 13`, `winerror 10013` — e nao `10048`. Se as duas caissem na mesma frase, o usuario leria "o dashboard ja esta aberto" para uma porta em que nao ha dashboard nenhum, iria fechar janelas que nao existem, e a instrucao seria uma mentira educada. Se nenhuma das duas fosse tratada, ele leria um traceback.
- **Fix:** `MENSAGEM_DE_PORTA_RESERVADA`, com instrucao propria (trocar de porta, e o comando do `netsh` para ver as faixas), mais um ramo generico que imprime o motivo do sistema operacional sem traceback para qualquer outro `OSError`.
- **Files modified:** `l2scanner/dashboard.py`
- **Verification:** `test_a_MENSAGEM_DE_PORTA_RESERVADA_NAO_manda_fechar_janela_nenhuma` — afirma que ela cita a porta, diz "RESERVADA", e **nao** contem "ja esta aberto"
- **Committed in:** `0c6bfc0`

**3. [Rule 2 - Missing Critical] Duas falhas do POST precisavam de resposta propria, e uma delas foi apontada pelo 01-03 por nome**
- **Found during:** Tarefa 2 (o `do_POST`)
- **Issue:** O plano especifica 200, 403, 400 (cambio invalido) e 413. Faltavam duas. (a) `HistoricoDoCambioIlegivel` — o `01-03` deixou escrito, endereçado a este plano: *"ela nao e culpa do que o usuario digitou, e a frase de cambio invalido mentiria sobre a causa"*. (b) Um corpo que nao e JSON, ou sem o campo esperado: servir "informe um numero maior que zero" para quem nao mandou numero nenhum descreve um problema que nao e o dele.
- **Fix:** `MENSAGEM_DE_CORPO_ILEGIVEL` com 400 proprio, `HistoricoDoCambioIlegivel` com **409** (o pedido esta certo, o disco e que nao esta) carregando a mensagem da propria excecao — que ja traz a anatomia completa —, e `MENSAGEM_DE_GRAVACAO_FALHOU` com 500 para qualquer outro `OSError`.
- **Files modified:** `l2scanner/dashboard.py`
- **Verification:** `test_um_corpo_ILEGIVEL_nao_recebe_a_frase_de_cambio_invalido` e `test_o_historico_ILEGIVEL_tem_resposta_PROPRIA_e_o_arquivo_fica_INTACTO` (que tambem afirma a impressao digital de tres componentes do arquivo corrompido, intacto)
- **Committed in:** `da23d35` (RED) e `d365bd1` (GREEN)

**4. [Rule 2 - Missing Critical] As dez sondas de travessia nao provavam ter dentes**
- **Found during:** Tarefa 3 (a bateria)
- **Issue:** O plano pede o controle POSITIVO (um arquivo que existe responde 200), que impede um servidor que negue tudo de passar. Ele nao pede o controle que responde a outra pergunta: **as sondas alcancam alguma coisa quando a defesa sai?** Sem isso, dez `404` sao compativeis com sondas mal formadas — por exemplo, com um cliente que normalizasse o caminho antes de enviar, que e justamente o defeito que a escolha do `http.client` existe para evitar. Um guarda cuja saida nao muda com o fato que ele julga e o padrao que `test_mercado_firewall_de_fase.py:449-470` ja nomeia nesta arvore.
- **Fix:** `test_o_CONTROLE_NEGATIVO_as_sondas_ALCANCAM_quando_a_defesa_sai` monta um manipulador com `directory=` um nivel acima de um diretorio publico de mentira, e afirma que ao menos uma sonda alcanca o "segredo". Medido fora da suite contra a raiz real do repo, para o comentario: **6 das 10 sondas vazam** (`../`, `../../`, `..%2f`, `%2e%2e/`, `//`, `vendor/../../`); as duas de contrabarra devolvem 301 e as outras duas 404 em ambos os mundos, e por isso provam menos — mas continuam na bateria porque uma implementacao futura pode mudar isso.
- **Files modified:** `tests/test_dashboard_servidor.py`
- **Verification:** o proprio teste, com a mensagem de falha dizendo por extenso o que um resultado zero significaria ("as dez sondas acima nao estao medindo nada")
- **Committed in:** `df3d1c4`
- **Nota de seguranca:** o segredo do controle negativo e um arquivo FALSO em `tmp_path`. Reproduzir a medicao contra a arvore de verdade dentro da suite exporia o repo inteiro num soquete, ainda que por milissegundos, para provar um ponto que um arquivo falso prova igual.

**5. [Rule 2 - Missing Critical] A recusa sem leitura precisava fechar a conexao**
- **Found during:** Tarefa 2 (o `do_POST`)
- **Issue:** As recusas por origem e por tamanho respondem **sem ter lido o corpo** — que e o desenho correto, porque carregar o ataque na memoria para so entao dizer nao seria pagar duas vezes. Mas os bytes do pedido continuam no soquete, e o HTTP/1.1 reaproveita conexao por padrao: o proximo pedido comecaria no meio do corpo do anterior.
- **Fix:** `close_connection = True` em `_recusar`, com a razao escrita.
- **Files modified:** `l2scanner/dashboard.py`
- **Verification:** `test_um_corpo_MAIOR_que_o_teto_e_recusado_sem_ser_lido` e `test_a_recusa_por_origem_NAO_le_o_corpo` — os dois declaram um `Content-Length` maior que os bytes enviados; se o servidor tentasse ler, ficaria pendurado e o teste falharia por tempo esgotado. A resposta rapida E a prova.
- **Committed in:** `d365bd1`

---

**Total deviations:** 5 auto-fixed (1 bug, 4 missing critical)
**Impact on plan:** Sem scope creep. A 1 conserta um defeito que a instrucao literal do plano criaria e que so apareceria em campo, depois de uma hora de janela aberta. A 2, a 3 e a 5 fecham caminhos de falha que o plano nao especificou, e as tres estao dentro dos limites travados dele (falha fechada, mensagem que diz o que fazer, nada e apagado). A 4 e a que transforma a bateria de travessia de uma afirmacao numa medicao. `requirements.txt` sem uma linha nova; nenhum arquivo da cerca dura tocado; `index.html` e `dashboard.css` — do plano irmao 01-06 — intocados.

## Issues Encountered

- **`urllib` esconderia metade das sondas, e o cliente cru foi escolhido antes de escrever a primeira.** Isso ja estava decidido desde o tracer (01-01), e a medicao do controle negativo confirmou por que: as sondas que vazam com a defesa removida sao justamente as que `urllib` normalizaria antes de enviar.
- **O fantasma do `KeyboardInterrupt` reapareceu, exatamente como o 01-04 registrou.** Uma rodada de `python -m pytest tests/ -q` parou em `tests/test_agenda.py:1231` — aquele teste **levanta `KeyboardInterrupt` de proposito**, e a interrupcao veio do ambiente. A re-execucao completou: **4.709 passed, 26 skipped em 126 s**. Registrado de novo para ninguem gastar tempo cacando o mesmo fantasma numa terceira vez.
- **O `-k "porta or listagem or cache or main"` da Tarefa 1 nao alcanca duas provas do proprio escopo dela** (as duas de `TestOBindENoEnderecoDeRetornoLocal`). Nao e defeito do codigo nem do teste: o criterio de aceitacao da tarefa cobra o portao do bind por um comando `python -c` separado sobre o AST, que foi executado e sai com codigo 0. A rodada completa do arquivo cobre as duas. E a mesma familia de friccao que o `01-04` registrou entre o seletor de uma tarefa e os criterios dela.
- **O `.env` nao existe nesta copia da arvore** (ele e ignorado pelo git, e worktrees nascem sem ele). Ver `## Known Stubs`.

## User Setup Required

None — nenhuma configuracao de servico externo. O `.mercado/cambio.json` nasce sozinho na primeira vez que o usuario salvar uma taxa pela pagina, e a porta padrao nao precisa de nada aberto no firewall porque o bind e so no endereco de retorno local.

## Next Phase Readiness

**Pronto para quem consumir:**

- **O `01-07` (o JS) tem tres contratos ja fixados no servidor, e nenhum deles deve ser reescrito no navegador:**
  - `GET /dados` devolve o payload com **`intervalo_de_polling_ms` dentro**. O JS deve usar ESSE numero para agendar o proximo `fetch`, e nunca um literal proprio: um intervalo escrito em dois lugares nao fica errado nos dois, fica errado em UM.
  - `POST /cambio` espera `{"cambio": "0,50"}` (a chave e `dashboard.CAMPO_DO_POST`) e devolve `{"reais_por_xm", "informado_em", "mensagem"}`. **A `mensagem` sai pronta do Python** — exibir como recebeu; remonta-la no JS seria o segundo formatador que o DASH-03 proibe.
  - As recusas devolvem `{"erro": "<frase>"}` com 400, 403, 409, 413 ou 500. **A frase e para exibir como veio**, e cada status tem uma causa diferente: 403 nao e erro de digitacao, e 409 nao e culpa do que o usuario escreveu.
- **O `fetch` do JS precisa mandar a origem.** Um `fetch` relativo do proprio documento ja envia `Origin` e `Sec-Fetch-Site: same-origin` sozinho — nao ha nada a configurar. Mas `mode: "no-cors"` ou um `Origin` mexido a mao **quebraria o POST com 403**, e o sintoma seria "o botao salvar nao faz nada".
- **O `01-08` (o `.bat`) chama `python -m l2scanner.dashboard`.** O `__main__.py` continua intocado e nao conhece o dashboard — ha teste prendendo a independencia nos dois sentidos. As opcoes disponiveis sao `--porta` e `--sem-navegador`. O `main` devolve **1** com frase acionavel quando a porta esta ocupada ou reservada, entao o `.bat` pode simplesmente propagar o codigo de saida, e o bloco de erro dele deve vir **antes** da linha de execucao (a regra estrutural do `vigiar-mercado.bat`).
- **VEND-4 esta fechado.** As quatro tarefas do portao de registro do UI-SPEC estao completas: VEND-1..3 no `01-04`, VEND-4 aqui.

**O que o proximo planejador precisa saber:**

- **A colisao `form-action 'none'` x `<form>` de verdade continua de pe** (Pitfall 6 da pesquisa, nao medivel sem navegador). O `submit` handler com `preventDefault()` + `fetch()` e **obrigatorio**, nao opcional: sem ele o `Enter` dispara um submit nativo que a CSP bloqueia, e o navegador nao mostra nada alem de um erro no console. E a falha fechada certa — o formulario nao envia em vez de recarregar a pagina para lugar nenhum —, mas ela precisa estar escrita no JS.
- **O `maxlength` do campo deve ser `TETO_DE_DIGITOS_INTEIROS + 1 + TETO_DE_CASAS_DECIMAIS` = 12** (recado que o `01-03` deixou). O servidor nao acredita no `maxlength`, mas um campo que deixa digitar o que o servidor vai recusar e uma frustracao evitavel.
- **O teto do corpo do POST e 1024 bytes**, conferido no `Content-Length` **antes** da leitura. Nenhum pedido honesto chega perto disso.
- **A porta 8787 e revisavel.** Se ela colidir com alguma ferramenta do usuario, e uma linha — e o `--porta` resolve na hora, sem editar codigo.

## Known Stubs

Nenhum stub de codigo: nao ha valor fabricado, padrao chutado, componente recebendo dado vazio nem caminho que responda com placeholder. As cinco mensagens de recusa e a de confirmacao sao texto final, e todas as constantes tem a razao escrita ao lado.

**Um teste pula condicionalmente, e o pulo tem razao dita:**

| Item | Arquivo | Motivo |
|---|---|---|
| `test_o_ENV_da_raiz_e_o_alvo_REAL_e_nenhuma_sonda_o_alcanca` | `tests/test_dashboard_servidor.py` | O `.env` e ignorado pelo git, e uma worktree nasce sem ele. O teste pula com a mensagem nomeando o caminho e explicando que as dez sondas seguem rodando contra os arquivos versionados da raiz. **Na arvore do usuario, onde o `.env` existe, ele roda.** |

Este pulo **nao abre buraco**: a fixture `arquivos_de_fora` foi desenhada de proposito para que as dez sondas nunca dependam de um arquivo ignorado pelo git — elas rodam sempre, contra `requirements.txt` e `config.toml`, e cada uma afirma tambem que uma resposta 200 so pode carregar bytes de dentro da pasta dos estaticos. Uma sonda que pula nao e uma sonda, e um silencio com cara de verde.

**Nao registrado no `.planning/WINDOWS.md` de proposito:** este plano rodou como agente paralelo em worktree, e o ledger e um arquivo compartilhado com contadores no frontmatter que o agente irmao (01-06) tambem tocaria. A escrita e do orquestrador; o item esta aqui para ele decidir.

## Self-Check: PASSED

- **Arquivos:** `l2scanner/dashboard.py` e `tests/test_dashboard_servidor.py` conferidos no disco — ambos presentes e nao vazios.
- **Commits:** `0c6bfc0`, `da23d35`, `d365bd1` e `df3d1c4` conferidos no `git log 5a10ee5..HEAD`.
- **Sem delecoes:** `git diff --diff-filter=D --name-only` contra a base nao lista nenhum arquivo removido.
- **Suite completa:** `python -m pytest tests/ -q` -> **4.709 passed, 26 skipped**, 0 falhas.
- **Este arquivo:** `python -m pytest tests/test_dashboard_servidor.py -q` -> **78 passed, 1 skipped**; `--collect-only` -> **79 testes** (o criterio pedia >= 25).
- **`<verification>` do plano, item a item:** `pytest tests/test_dashboard_servidor.py -q` -> 0; `pytest tests/ -q` -> 0; `git status --porcelain .mercado/` -> vazio; `git diff --stat l2scanner/__main__.py l2scanner/mercado_modo.py requirements.txt` -> vazio.
- **Criterio executavel da Tarefa 1:** o `python -c` do AST sobre `dashboard.py` (nenhuma constante `0.0.0.0`) sai com codigo **0**.
- **Seletores das tarefas:** `-k "porta or listagem or cache or main"` -> 18 passed; `-k "origem or cambio or post"` -> 24 passed.
- **Cerca dura de escopo:** `git diff --stat` contra a base sobre os dez arquivos proibidos (`rastreador.py`, `visao.py`, `console.py`, `mercado_registro.py`, `mercado_analise.py`, `mercado_console.py`, `config.py`, `mercado_catalogo.py`, `index.html`, `dashboard.css`) -> **saida vazia**. `git status --short` limpo.
- **Lint:** `python -m ruff check` nos dois arquivos -> `All checks passed!`.
- **Nenhuma escrita fora de `tmp_path`:** `.mercado/` do repo intocada depois da suite completa.
- **Nenhum comando destrutivo:** nenhum `git clean`, `git stash`, `git reset --hard` ou `git update-ref` foi usado em momento algum.

---
*Phase: 01-dashboard-do-cambio-ao-vivo*
*Completed: 2026-09-02*
