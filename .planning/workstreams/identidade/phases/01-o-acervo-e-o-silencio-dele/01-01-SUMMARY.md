---
phase: 01-o-acervo-e-o-silencio-dele
workstream: identidade
plan: 01
subsystem: identity
tags: [sha256, hashlib, o_excl, ast-gate, disk-store, opencv, party-window]

requires: []
provides:
  - "l2scanner/acervo.py — o acervo duravel de assinaturas em `.identidades/`, fora do calibration.json"
  - "chave_da_assinatura: sha256 completo, 64 hex, sobre `altura x largura : bits` (D-06)"
  - "AcervoDeIdentidades: chaves(), assinaturas(), gravar() tri-estado, _nome_de()"
  - "carregar_identidades(calibradas, acervo) -> Identidades (calibradas primeiro)"
  - "Assinatura.anonima; Casamento.identificado passa a ser bool(self.nome)"
  - "O elo `assinaturas_configuradas` fechado em producao pela PRIMEIRA vez"
  - "Portao AST permanente: toda chamada Rastreador(...) em l2scanner/ decide sobre a flag"
  - "acervo.py na tupla MODULOS do portao de relogio proprio"
affects:
  - "Fase 2 (aprender assinaturas): consome gravar() e APAGA/AJUSTA os dois portoes de fronteira de fase"
  - "Fase 3 (batizar): escreve `nome_<hash>` e vai pinar a chave"
  - "plano 01-02: deduplicacao (OPER-02) e o portao do calibrar.bat"

actuals:
  tokens: 16770   # chars/4 sobre o diff realizado (67080 chars, 18d0c71..2474624)
  tasks: 3
  commits: 3

tech-stack:
  added: []   # zero dependencia nova: hashlib, os, re, json e pathlib sao stdlib
  patterns:
    - "Acervo duravel em pasta propria, um arquivo por entrada, sem poda (molde do .loot/)"
    - "Nome de arquivo como SOMA DE VERIFICACAO: a chave e recalculada do conteudo na leitura"
    - "Portao AST de construcao explicita, com guarda contra prova vazia E contra vacuidade"

key-files:
  created:
    - "l2scanner/acervo.py"
    - "tests/test_acervo.py"
  modified:
    - "l2scanner/identidade.py"
    - "l2scanner/calibracao.py"
    - "l2scanner/__main__.py"
    - "tests/test_presenca.py"
    - ".gitignore"

key-decisions:
  - "D-06 implementado como travado: sha256, 64 digitos hex, material `f\"{altura}x{largura}:{bits}\"`, sem truncar"
  - "Tri-estado do loot (criado|ja_existia|falhou), e NAO o colapso-em-True da agenda"
  - "Identidades expoe conhecidas/sem_nome/resumo/configuradas como PROPRIEDADES derivadas, nao campos guardados"
  - "gravar() APAGA o arquivo quando a escrita do corpo falha, para nao deixar um `ja_existia` permanente sobre uma entrada ilegivel"
  - "O portao 'quem conhece o acervo' usa AST de imports, e nao varredura textual: prosa de docstring nao e conhecimento do modulo"

patterns-established:
  - "Chave por conteudo: hash das dimensoes + bits, nome fora do material (D-01/D-03)"
  - "Leitura defensiva por arquivo: (OSError, ValueError, TypeError, KeyError) pula e segue"
  - "Ordem estavel por chave, porque a ordem alimenta o desempate do guloso de identificar_linhas"
  - "Portao de FRONTEIRA DE FASE, com a docstring dizendo qual fase o apaga de proposito"

requirements-completed: [DURA-02, DURA-03, DURA-04, APRE-03, OPER-01]

coverage:
  - id: D1
    description: "Uma entrada colocada A MAO em `.identidades/`, SEM nome, e lida no arranque, casa com a linha da party window e deixa aquela linha como `#linhaN`: zero eventos e rotulo `Membro N`"
    requirement: APRE-03
    verification:
      - kind: integration
        ref: "tests/test_acervo.py#TestUmaEntradaAMaoAtravessaOScanner::test_sem_nome_a_MESMA_entrada_e_reconhecida_e_CALA"
        status: pass
      - kind: integration
        ref: "tests/test_acervo.py#TestUmaEntradaAMaoAtravessaOScanner::test_com_nome_a_linha_e_reconhecida_e_o_alerta_sai_no_nome_dela"
        status: pass
    human_judgment: false
  - id: D2
    description: "O acervo atravessa o reinicio: mesma contagem, mesmo conjunto de chaves, mesma ordem"
    requirement: DURA-02
    verification:
      - kind: unit
        ref: "tests/test_acervo.py#TestOAcervoAtravessaOReinicio::test_uma_instancia_nova_ve_o_MESMO_acervo"
        status: pass
    human_judgment: false
  - id: D3
    description: "Duas instancias gravando a MESMA assinatura produzem UMA entrada; falha de disco devolve `falhou` e nao deixa entrada pela metade"
    requirement: DURA-03
    verification:
      - kind: unit
        ref: "tests/test_acervo.py#TestGravar::test_duas_instancias_na_mesma_pasta_produzem_UMA_entrada"
        status: pass
      - kind: unit
        ref: "tests/test_acervo.py#TestGravar::test_falha_de_disco_devolve_falhou_e_nao_deixa_entrada"
        status: pass
      - kind: unit
        ref: "tests/test_acervo.py#TestGravar::test_falha_no_meio_da_escrita_nao_deixa_entrada_pela_metade"
        status: pass
    human_judgment: false
  - id: D4
    description: "Envelhecer os arquivos em 400 dias nao remove nem uma entrada, e acervo.py nao tem relogio proprio"
    requirement: DURA-04
    verification:
      - kind: unit
        ref: "tests/test_acervo.py#TestOAcervoNaoEnvelhece::test_entradas_de_400_dias_atras_continuam_todas_presentes"
        status: pass
      - kind: unit
        ref: "tests/test_presenca.py#TestSemRelogioProprio::test_nenhum_now_de_datetime_na_arvore[acervo.py]"
        status: pass
    human_judgment: false
  - id: D5
    description: "O arranque imprime quantas assinaturas o scanner conhece e quantas estao sem nome"
    requirement: OPER-01
    verification:
      - kind: unit
        ref: "tests/test_acervo.py#TestFusaoComACalibracao::test_resumo_conta_conhecidas_e_sem_nome"
        status: pass
    human_judgment: true
    rationale: "A string do resumo esta provada, mas o texto que o usuario ve no console no arranque real (com o jogo aberto e o calibration.json dele) so um humano confere. O teste prova a frase; nao prova que ela aparece no momento certo da tela."
  - id: D6
    description: "TODA chamada Rastreador(...) em l2scanner/ decide explicitamente sobre `assinaturas_configuradas`, provado por varredura AST com guarda contra prova vazia e contra vacuidade"
    requirement: APRE-03
    verification:
      - kind: unit
        ref: "tests/test_acervo.py#TestNenhumRastreadorNasceMudo::test_toda_chamada_em_producao_decide_sobre_a_flag"
        status: pass
      - kind: unit
        ref: "tests/test_acervo.py#TestNenhumRastreadorNasceMudo::test_o_detector_acusa_um_caso_plantado"
        status: pass
      - kind: unit
        ref: "tests/test_acervo.py#TestNenhumRastreadorNasceMudo::test_o_portao_nao_passa_por_vacuidade"
        status: pass
    human_judgment: false
  - id: D7
    description: "Um arquivo de assinatura adulterado e DESCARTADO na leitura, e um `nome_<hash>` malformado degrada para anonimo (T-01-01/T-01-02)"
    verification:
      - kind: unit
        ref: "tests/test_acervo.py#TestLeituraDoAcervo::test_conteudo_adulterado_e_descartado"
        status: pass
      - kind: unit
        ref: "tests/test_acervo.py#TestLeituraDoAcervo::test_nome_invalido_degrada_para_anonimo"
        status: pass
    human_judgment: false

duration: 19min
completed: 2026-08-31
status: complete
---

# Phase 1 Plan 01: O Acervo e o Silencio Dele — Summary

**`.identidades/` nasce como acervo duravel chaveado por sha256 de 64 digitos sobre o conteudo da mascara, e o elo `assinaturas_configuradas` — que existia so nos testes — passa a ser ligado em producao, de modo que uma entrada sem nome e reconhecida na tela sem gerar evento nem nome nenhum.**

## Performance

- **Duration:** ~19 min
- **Started:** 2026-08-31T06:35:31-03:00 (base 18d0c71)
- **Completed:** 2026-08-31T06:54:46-03:00
- **Tasks:** 3
- **Files modified:** 7 (2 criados, 5 modificados)

## Accomplishments

- **`l2scanner/acervo.py`**: pasta propria `.identidades/`, um arquivo por entrada, sem poda. A chave e `sha256` completo (64 hex) sobre `f"{altura}x{largura}:{bits}"`, exatamente como D-06 travou. As dimensoes entram no material porque `packbits` de uma 2x8 e de uma 4x4 produz os MESMOS bytes — colisao que nao depende de sorte.
- **A leitura confere o que le.** A chave e RECALCULADA a partir do conteudo e comparada com a chave do nome do arquivo; divergiu, a entrada e descartada. O nome do arquivo deixou de ser uma afirmacao e virou soma de verificacao (T-01-02).
- **O nome so vem do irmao `nome_<hash>`**, validado por `[A-Za-z0-9]{2,16}` depois de `.strip()`. Ausente, vazio, multilinha, com barra ou longo demais devolve `""` — o desfecho de um arquivo de nome ruim e SILENCIO, nunca um nome errado (T-01-01).
- **O DEFEITO VIVO FOI CONSERTADO.** `Rastreador.assinaturas_configuradas` nunca era atribuido em producao: `__main__.py` nao passava o argumento e o default era `False`. O silencio do `#linhaN` estava verde na suite e DESLIGADO em campo, e uma linha nao reconhecida pegava emprestado `nomes[indice]` para anunciar morte com o nome de quem estava vivo. Agora `__main__` passa `assinaturas_configuradas=identidades.configuradas`.
- **A CLASSE do defeito tambem.** Um portao AST varre `l2scanner/*.py` e exige que TODA chamada `Rastreador(...)` decida explicitamente sobre a flag, nomeando arquivo e linha de cada faltante. Ele carrega as duas guardas: uma arvore fabricada com `Rastreador(nomes=[])` e ACUSADA, e o detector tem de achar pelo menos uma chamada real em `l2scanner/`.
- **A escrita tri-estado** `criado | ja_existia | falhou` no molde do `loot.RegistroDeLoot` (e nao do `agenda.RegistroEmDisco`), com a docstring nomeando os dois precedentes e dizendo por que este escolheu o outro.
- **Sem relogio e sem poda:** `acervo.py` entrou na tupla `MODULOS` do portao AST de `tests/test_presenca.py` antes de ter uma linha de logica de tempo.

## Task Commits

1. **Tarefa 1 (tracer, tdd): a fatia inteira — uma entrada a mao, sem nome, reconhecida e calada** — `8862f78` (feat)
2. **Tarefa 2 (tdd): a escrita que duas instancias disputam, e a falha de disco que nao mente** — `e081eec` (feat)
3. **Tarefa 3: sem relogio, sem poda, e sem gravar nas costas de ninguem** — `2474624` (test)

## Files Created/Modified

- `l2scanner/acervo.py` — **criado.** `chave_da_assinatura`, `Identidades`, `AcervoDeIdentidades` (`chaves`, `assinaturas`, `gravar`, `_nome_de`), `carregar_identidades`. Nao importa `calibracao`, `rastreador` nem `visao`; nao tem relogio.
- `tests/test_acervo.py` — **criado.** 52 casos: a chave, a leitura defensiva, a fatia disco→console, a escrita, a ausencia de poda, o reinicio, os dois portoes de fronteira de fase e o portao de construcao explicita do `Rastreador`.
- `l2scanner/identidade.py` — `Assinatura.anonima`; `Casamento.identificado` passa de `self.nome is not None` para `bool(self.nome)`.
- `l2scanner/calibracao.py` — uma linha em `nomes_com_assinatura`: `if a.nome`.
- `l2scanner/__main__.py` — `PASTA_IDENTIDADES`, a fusao em memoria, `log.info(identidades.resumo)` e o argumento `assinaturas_configuradas` no `Rastreador`.
- `tests/test_presenca.py` — `"acervo.py"` na tupla `MODULOS` e o paragrafo do modulo novo na docstring da classe.
- `.gitignore` — `.identidades/`, junto de `.agenda/`, `.loot/` e `.mercado/`.

## Registros exigidos pelo `<output>` do plano

**1. `grep` por consumidores de `Casamento.identificado` ANTES da mudanca:**

```
$ grep -rn "\.identificado" l2scanner/ tests/ tools/
Binary file l2scanner/__pycache__/identidade.cpython-312.pyc matches
```

**Zero consumidores em codigo-fonte.** O unico acerto foi bytecode compilado. Trocar `self.nome is not None` por `bool(self.nome)` nao tinha como quebrar nada, e a mudanca existe para que a Fase 2 e a Fase 3 nao herdem uma propriedade que responde "sim, sei quem e" sobre uma linha que ninguem batizou.

**2. Contagem de testes:**

| Momento | Passaram | Skipped |
|---------|----------|---------|
| Linha de base (18d0c71) | 3050 | 23 |
| Depois da Tarefa 1 | 3087 | 23 |
| Fim do plano | **3104** | 23 |

Delta: **+54** (52 casos novos em `tests/test_acervo.py`, 2 casos parametrizados novos em `tests/test_presenca.py` por conta do `acervo.py` na tupla). Nenhum teste existente foi editado, afrouxado ou removido. Os 23 skipped sao os mesmos da linha de base (OCR/WinRT, cujas bindings vivem na `.venv` e nao no `python` do sistema).

**3. Saida do portao de construcao explicita do `Rastreador`:**

```
__main__.py:2026 decide= True
TOTAL 1
```

Existe **UMA** chamada `Rastreador(...)` em `l2scanner/`, e ela decide sobre `assinaturas_configuradas`. Era exatamente essa a que estava muda antes deste plano. O portao nao passa por vacuidade (`TOTAL >= 1`) e acusa um caso plantado.

## Decisions Made

- **D-06 implementado sem re-abrir.** Nao houve checkpoint: a porta ja tinha sido atravessada pelo usuario em 2026-08-31.
- **`Identidades` guarda UMA lista e deriva o resto.** `configuradas`, `conhecidas`, `sem_nome` e `resumo` sao propriedades. Um par de contadores gravado ao lado da lista e um par de contadores que pode discordar dela — e a linha de arranque que o usuario le seria justamente onde a discordancia apareceria.
- **`gravar` apaga o arquivo quando a escrita do corpo falha.** Deixa-lo faria a proxima tentativa receber `"ja_existia"` sobre uma entrada que a leitura descarta: o acervo diria para sempre que conhece alguem que nao consegue ler. `O_EXCL` garante que este processo criou o arquivo, entao remove-lo nao atropela a outra instancia.
- **Escrita parcial e `close` que levanta contam como falha.** No Windows os bytes so chegam ao disco no fechamento; um `close` que levanta e uma gravacao que nao aconteceu.
- **Round-trip canonico.** `de_dict` → `como_dict` e estavel porque o padding do `packbits` e zero. Efeito colateral desejado: um arquivo escrito a mao com bits de padding sujos, ou com hex maiusculo, e descartado pela conferencia de chave. Canonizacao, e nao tolerancia.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] O portao "quem conhece o acervo" nasceria vermelho na forma textual escrita no plano**

- **Found during:** Tarefa 3
- **Issue:** O plano especificava "remove as linhas de comentario de cada fonte, e monta o conjunto dos arquivos cujo texto restante menciona o modulo do acervo", esperando `{"acervo.py", "__main__.py"}`. Mas `l2scanner/identidade.py` (linhas 161 e 247) e `l2scanner/calibracao.py` (linha 522) citam o acervo em PROSA de docstring, ao explicar por que uma assinatura anonima existe — docstring nao e linha de comentario e nao seria removida. O portao acusaria exatamente a documentacao que protege a regra, e o conjunto viria `{"acervo.py", "__main__.py", "identidade.py", "calibracao.py"}`.
- **Fix:** O portao pergunta "quem IMPORTA o acervo", lido da arvore sintatica (`ast.ImportFrom` / `ast.Import`), unido ao arquivo que DEFINE o modulo. Igualdade de conjuntos preservada, `{"acervo.py", "__main__.py"}`, e `sessao.py`/`visao.py` continuam presos do lado de fora. E o mesmo motivo que fez `_modulos_importados` nascer em `tests/test_presenca.py`, e a docstring do caso registra isso.
- **Files modified:** `tests/test_acervo.py`
- **Verification:** `python -m pytest tests/test_acervo.py -q` — 52 passed. O conjunto observado e exatamente `{"acervo.py", "__main__.py"}`.
- **Committed in:** `2474624`

**2. [Rule 2 - Missing Critical] Nao-vacuidade no portao comportamental da `Sessao`**

- **Found during:** Tarefa 3
- **Issue:** "a pasta fica byte a byte identica depois de rodar a `Sessao`" passa trivialmente se o tick falhar na analise, se o frame for rejeitado, ou se as assinaturas nunca entrarem em jogo. `Sessao.tick` engole falha de analise em `resultado.falhou_ao_analisar` de proposito, entao um erro silencioso deixaria o portao verde sem nunca ter chegado perto de uma escrita — a mesma forma de defeito que o proprio plano manda evitar.
- **Fix:** Antes da comparacao de bytes, o caso afirma que o ultimo tick produziu observacao e que alguma linha foi reconhecida por uma assinatura ANONIMA do acervo (`nome == ""` com `confianca > 0.9`). O laco tem de ter usado o acervo para o "nao escreveu nele" significar alguma coisa.
- **Files modified:** `tests/test_acervo.py`
- **Verification:** `python -m pytest tests/test_acervo.py -q` — passa; removendo o acervo da fusao, o caso falha na assercao de nao-vacuidade.
- **Committed in:** `2474624`

**3. [Rule 2 - Missing Critical] Escrita parcial e falha de `close` tratadas em `gravar`**

- **Found during:** Tarefa 2
- **Issue:** O plano pedia `os.write` dentro do mesmo `try` do `os.open`. Isso cobre `OSError`, mas nao cobre `os.write` devolvendo MENOS bytes do que pediram (nao levanta nada) nem `close` levantando — e no Windows os bytes so chegam ao disco no fechamento. Qualquer um dos dois produziria um corpo truncado devolvendo `"criado"`: o acervo gravando lixo com cara de sucesso.
- **Fix:** `gravar` compara o retorno de `os.write` com `len(dados)`, trata `close` como ponto de falha proprio, e apaga o arquivo em qualquer dos desfechos ruins antes de devolver `"falhou"`.
- **Files modified:** `l2scanner/acervo.py`, `tests/test_acervo.py`
- **Verification:** `tests/test_acervo.py::TestGravar::test_uma_escrita_parcial_tambem_e_falha` e `::test_falha_no_meio_da_escrita_nao_deixa_entrada_pela_metade`.
- **Committed in:** `e081eec`

---

**Total deviations:** 3 auto-fixed (1 bug, 2 missing critical)
**Impact on plan:** Nenhum escopo novo. As tres correcoes atendem criterios que o proprio plano escreveu (nao-vacuidade dos portoes, `"falhou"` que nao mente); a primeira troca a TECNICA de um portao preservando a assercao exata que o plano pediu. Nenhuma decisao travada foi tocada.

## Issues Encountered

- Uma execucao da suite completa foi interrompida por um `KeyboardInterrupt` do ambiente durante `tests/test_agenda.py`, sem relacao com este plano. A re-execucao imediata terminou verde (3104 passed).
- Conflito com o workstream `mercado` em `l2scanner/calibracao.py`: **nao houve.** A mudanca ficou dentro de `nomes_com_assinatura`, uma propriedade do lado da party. Nada do lado do mercado foi lido, ajustado ou reformatado.

## Known Stubs

Nenhum. Nao ha valor vazio codificado, texto de placeholder nem componente sem fonte de dados neste plano.

O que **deliberadamente nao existe** (e nao e stub, e fronteira de fase declarada no plano):

- `AcervoDeIdentidades.nomear` — batizar e Fase 3 (D-03).
- Qualquer chamador de `gravar` no laco do scanner — aprender e Fase 2. Provado por dois portoes que dizem, na propria docstring, que a Fase 2 os altera de proposito.
- Deduplicacao entre calibracao e acervo — plano 01-02 (OPER-02).

## Threat Flags

Nenhuma superficie nova fora do `<threat_model>` do plano. `.identidades/` e a unica fronteira acrescentada e ela esta registrada (T-01-01 a T-01-07), com T-01-01, T-01-02, T-01-04 e T-01-05 mitigadas e provadas por teste nesta entrega. Zero dependencia nova (`hashlib`, `os`, `re`, `json`, `pathlib` sao stdlib), entao T-01-SC continua valendo.

## User Setup Required

Nenhuma. A pasta `.identidades/` e criada em tempo de execucao (`mkdir(parents=True, exist_ok=True)`) e ja esta no `.gitignore`.

## Next Phase Readiness

**Pronto para o plano 01-02:** `carregar_identidades` esta escrito como concatenacao com ordem documentada (calibradas primeiro), que e exatamente o ponto onde a deduplicacao de OPER-02 entra. A invariante "o scanner nao regrava o `calibration.json`" esta implementada (atribuicao em memoria, com o comentario dizendo por que) e falta o portao que a prende.

**Pronto para a Fase 2:** `gravar` existe, esta provada e nao tem chamador. Os dois portoes de fronteira de fase (`test_so_dois_modulos_conhecem_o_acervo` e `test_o_laco_real_nao_encosta_no_acervo`) vao ficar vermelhos assim que a Fase 2 comecar a aprender — **isso e esperado e esta escrito na docstring da classe deles.** Apagar o segundo e ajustar o primeiro faz parte da Fase 2; interpreta-los como regressao seria desfazer o proprio trabalho.

**Pronto para a Fase 3:** a chave que o batismo vai pinar (BATI-03) e estavel entre reinicios, independente de posicao e independente de nome, com as tres propriedades provadas por teste.

## Self-Check: PASSED

Arquivos afirmados como criados, conferidos em disco:

- FOUND `l2scanner/acervo.py`
- FOUND `tests/test_acervo.py`
- FOUND `.planning/workstreams/identidade/phases/01-o-acervo-e-o-silencio-dele/01-01-SUMMARY.md`

Commits afirmados, conferidos em `git log`:

- FOUND `8862f78`
- FOUND `e081eec`
- FOUND `2474624`

Suite conferida por execucao: `python -m pytest tests/ -q` — 3104 passed, 23 skipped.

---
*Phase: 01-o-acervo-e-o-silencio-dele*
*Workstream: identidade*
*Completed: 2026-08-31*
