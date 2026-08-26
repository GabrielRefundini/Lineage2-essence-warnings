---
quick_id: 260826-skp
slug: dry-run-nao-pode-queimar-marcador
subsystem: agenda
tags: [dry-run, registro-em-disco, o-excl, marcador, simulacao, agenda]

requires:
  - phase: 10
    provides: "_PREFIXOS_CONHECIDOS e a poda com prefixo derivado; o fechamento de lista que virou o quarto sitio de marcar"
provides:
  - "RegistroEmDisco(pasta, simulando=False): em simulacao marcar devolve True sem tocar no disco e podar nao apaga nada"
  - "Os quatro sitios de marcar herdam a guarda pela construcao do registro, sem nenhum if dry_run novo"
  - "A frase de simulacao do console agora fala do disco, nao so do envio"
affects: [agenda, presenca, comandos, qualquer sitio futuro de marcar]

actuals:
  tokens: 5808
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "A guarda de modo mora no OBJETO que conhece o efeito colateral, nunca no chamador"

key-files:
  created: []
  modified:
    - l2scanner/agenda.py
    - l2scanner/__main__.py
    - tests/test_agenda.py
    - tests/test_sessao.py

key-decisions:
  - "O registro sabe que esta simulando; os quatro chamadores nao. Um if args.dry_run por sitio resolveria os quatro de hoje e faria o quinto nascer errado."
  - "Em simulacao marcar devolve True (finge que ganhou) em vez de False: o console tem que mostrar o aviso, que e o produto do --dry-run."
  - "enviados() continua lendo o disco de verdade nos dois modos: uma simulacao cega mentiria sobre o que teria acontecido."
  - "podar nao roda em simulacao, e a guarda ficou DENTRO dela e nao no __init__, pela mesma razao que a de marcar nao ficou nos chamadores."
  - "Em simulacao nem a pasta .agenda/ e criada: nada em modo simulacao precisa dela, e enviados() ja devolve vazio quando ela falta."
  - "entrar e sair seguem escrevendo: so sao alcancadas por comando, e em --dry-run montar_leitor_de_comandos devolve None na primeira linha. Decisao documentada na docstring de marcar."

patterns-established:
  - "Guarda de modo no objeto: quem conhece o efeito colateral e quem decide se ele acontece"
  - "Guarda contra prova vazia: todo teste que afirma que nada foi gravado vem acompanhado do mesmo tick SEM simulacao provando que algo seria gravado"

coverage:
  - id: D1
    description: "Em modo simulacao o registro nao cria nem apaga arquivo, e nao rouba a vez da instancia real"
    verification:
      - kind: unit
        ref: "tests/test_agenda.py#TestRegistroSimulando (5 testes)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Um tick do laco_da_agenda (--so-agenda) em simulacao avisa no console e deixa a .agenda/ intacta"
    verification:
      - kind: integration
        ref: "tests/test_agenda.py#TestSimulacaoNoLacoDaAgenda (3 testes, um deles a guarda contra prova vazia)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Um tick do laco principal via Sessao em simulacao avisa e nao deixa marcador"
    verification:
      - kind: integration
        ref: "tests/test_sessao.py#TestSimulacaoNoLacoPrincipal (3 testes)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A guarda mora no registro: sessao.py nao conhece dry_run e os dois lacos constroem com simulando="
    verification:
      - kind: unit
        ref: "tests/test_agenda.py#TestOndeMoraAGuardaDeSimulacao (3 testes, AST + fonte)"
        status: pass
    human_judgment: false
  - id: D5
    description: "A frase de simulacao no console menciona que nada e gravado em .agenda/"
    verification:
      - kind: unit
        ref: "tests/test_agenda.py#TestOndeMoraAGuardaDeSimulacao::test_a_frase_do_console_fala_do_disco"
        status: pass
      - kind: manual_procedural
        ref: "python -m l2scanner --testar-agenda --dry-run"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-08-26
status: complete
---

# Quick 260826-skp: o `--dry-run` nao pode queimar marcador Summary

**`RegistroEmDisco` passou a saber que esta simulando: em `--dry-run` o `marcar` devolve `True` sem escrever e o `podar` nao apaga nada, entao os quatro sitios de `marcar` herdam a guarda sem nenhum `if dry_run` novo.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-26T20:36:00-03:00
- **Completed:** 2026-08-26T20:48:05-03:00
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- O incidente de campo esta reproduzido em teste e corrigido: uma simulacao nao tira mais a vez da instancia real na disputa do `O_CREAT|O_EXCL`, e o aviso das 19:30 nao pode mais ser apagado por um processo que nao ia falar.
- A correcao e estrutural e mora num lugar so. `cancelar` e `fechar` herdam pelo `marcar` sem saber que a guarda existe, e `grep -n "dry_run" l2scanner/sessao.py` continua devolvendo nada.
- `podar`, a unica funcao da classe que APAGA arquivo e que roda no construtor, ficou inerte em simulacao: subir um `--dry-run` ao lado do scanner de verdade nao apaga mais marcador dele pela porta dos fundos.
- A frase do console parou de ser meia verdade: ela prometia "nada e enviado" e calava sobre o disco, que era exatamente o que fazia parecer seguro rodar uma simulacao ao lado do scanner real.
- 14 testes novos, incluindo uma guarda contra prova vazia em CADA laco (o mesmo tick sem simulacao tem que gravar o marcador), para que nenhum "nada foi gravado" passe por um tick que simplesmente nunca chegou ao aviso.

## Task Commits

1. **Tarefa 1: o registro passa a saber que esta simulando** - `4112787` (fix)
2. **Tarefa 2: os quatro sitios herdam, e o console para de mentir** - `0fcd674` (fix)

## Files Created/Modified

- `l2scanner/agenda.py` - `RegistroEmDisco.__init__` ganhou `simulando`; guardas em `marcar` e `podar`; a docstring de `marcar` documenta o incidente de 2026-08-26 19:30, por que a decisao mora no registro e por que `entrar`/`sair` ficaram de fora
- `l2scanner/__main__.py` - `laco_da_agenda` e `laco_principal` constroem o registro com `simulando=args.dry_run`; a frase de simulacao de `montar_despachante` passou a citar a `.agenda/`
- `tests/test_agenda.py` - `TestRegistroSimulando` (5), `TestSimulacaoNoLacoDaAgenda` (3), `TestOndeMoraAGuardaDeSimulacao` (3)
- `tests/test_sessao.py` - `nova_sessao` aceita `registro=`; `TestSimulacaoNoLacoPrincipal` (3)

## Decisions Made

Ver `key-decisions` no frontmatter. As duas que mais moldaram o codigo:

- **`marcar` devolve `True`, e nao `False`, em simulacao.** `False` calaria o console e mataria o produto do `--dry-run`. O comportamento certo e "finge que ganhou, sem tirar a vez de quem vai mesmo falar", e a docstring diz isso com essas palavras, porque "nao faz nada" convidaria a proxima pessoa a trocar por `False`.
- **A guarda de `podar` ficou dentro de `podar`, nao no `__init__`.** Um `if not simulando: self.podar()` no construtor deixaria uma chamada direta a `registro.podar()` apagando disco em modo simulacao: a mesma classe de furo que espalhar `if dry_run` pelos chamadores.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Os testes novos nasceram com `NameError` porque `test_agenda.py` importa `RegistroEmDisco` localmente em cada metodo em vez de no topo. Seguido o idioma do arquivo (import local por teste) em vez de mudar o cabecalho de um arquivo de 1400 linhas.
- O `--dry-run` do `laco_da_agenda` nunca tinha sido executado por teste nenhum (so lido por AST). O tick precisou de `monkeypatch` em `PASTA_AGENDA`, `PASTA_LOOT`, `ler_agenda`, `montar_relogio` e `time.sleep`, este ultimo levantando `KeyboardInterrupt`, que o proprio laco ja trata, para dar exatamente uma volta.

## Verificacao

- RED confirmado antes do conserto: contra o codigo antigo, `simulacao=True real=False` para a chave `2026-08-26_tvt-1930_agora`. O aviso desapareceria.
- RED confirmado tambem para a fiacao: desfazendo so o `simulando=args.dry_run` do `laco_da_agenda`, 3 testes caem, entre eles o que pergunta se a instancia real ainda consegue avisar.
- Suite completa: **1066 passed, 2 skipped** (baseline 1052 + 14 novos). Nenhum teste enfraquecido.
- `grep -n "dry_run" l2scanner/sessao.py` devolve nada.
- `python -m ruff check` limpo nos quatro arquivos tocados.
- `python -m l2scanner --testar-agenda --dry-run` imprime a frase nova e nao deixa rastro no `git status`.

## Fora de escopo encontrado

- `tests/test_sessao.py` tem 2 `F401` pre-existentes (`VigiaDeManutencao` importado e nao usado, linhas ~1038 e ~1069), e o resto de `tests/` soma 24 avisos de ruff. Nada disso vem destas mudancas e nada foi tocado.
- `comando_cancelar_silencio` (`__main__.py:960`) monta um `RegistroEmDisco` sem `simulando`. Deixado de proposito: e um comando de UMA acao explicita do usuario, nao um laco, e fazer um `--cancelar-silencio --dry-run` "cancelar sem cancelar" e uma decisao de produto, nao a correcao deste defeito.

## Next Phase Readiness

- Um quinto sitio de `marcar` nasce correto sem ninguem lembrar da regra.
- Fica aberta a pergunta de produto sobre `--cancelar-silencio --dry-run` e sobre `entrar`/`sair` caso o `--dry-run` um dia passe a escutar comandos, que a Fase 8 decidiu de proposito que ele nao faria.

---
*Quick task: 260826-skp-dry-run-nao-pode-queimar-marcador*
*Completed: 2026-08-26*

## Self-Check: PASSED

- Arquivos citados existem: l2scanner/agenda.py, l2scanner/__main__.py, tests/test_agenda.py, tests/test_sessao.py
- Commits citados existem no git log: 4112787, 0fcd674
- Suite completa verde na ultima execucao: 1066 passed, 2 skipped
