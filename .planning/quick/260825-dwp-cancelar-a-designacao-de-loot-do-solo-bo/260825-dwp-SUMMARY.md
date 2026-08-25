---
phase: quick-260825-dwp
plan: 01
subsystem: loot
tags: [loot, comandos, whatsapp, agenda, solo-boss]
status: complete

requires:
  - RegistroDeLoot e Designacao (quick 260825-cou)
  - interpretar_dinamico com o prefixo `loot-` (quick 260825-cou)
  - as quatro travas de comandos_novos (quick 20260824-comandos-so-do-meu-numero)
provides:
  - "`Comando.LOOT_CANCELAR` — o primeiro comando DESTRUTIVO da superficie dinamica"
  - "`RegistroDeLoot.cancelar()` — apaga a vez, idempotente entre instancias"
  - "`responder_cancelamento()` — o texto que nomeia quem perdeu a vez e qual boss"
affects:
  - l2scanner/loot.py
  - l2scanner/comandos.py
  - l2scanner/__main__.py

tech-stack:
  added: []
  patterns:
    - "Palavra reservada testada ANTES do charset de nick, nos dois ramos"
    - "Apagar nao depende da agenda; gravar depende (assimetria deliberada)"
    - "unlink(missing_ok=True) como idempotencia entre as duas instancias"

key-files:
  created: []
  modified:
    - l2scanner/loot.py
    - l2scanner/comandos.py
    - l2scanner/__main__.py
    - tests/test_loot.py
    - tests/test_comandos.py
    - tests/test_sessao.py

decisions:
  - "APAGAR nunca depende da agenda: um config.toml quebrado prenderia a designacao para sempre"
  - "`.loot cancelar` cancela — antes desta tarefa ele DESIGNAVA um personagem chamado cancelar"
  - "`.loot` sozinho continua sendo nada, com a razao escrita na linha do return"

metrics:
  duration: ~15min
  completed: 2026-08-25
  tasks: 2
  commits: 4
  tests_before: 566
  tests_after: 581

actuals:
  tokens: 38700
  tasks: 2
  commits: 4
---

# Quick 260825-dwp: Cancelar a designacao de loot do Solo Boss — Summary

O `.loot-` passou a APAGAR a designacao do proximo Solo Boss: o registro volta
ao estado "sem dono" pelo WhatsApp, e o aviso de antecedencia volta a sair sem
a linha "Loot:" — provado por teste de tick, nao por leitura de codigo.

## O que foi construido

Antes desta tarefa dava para designar (`.loot-j4guar`) e dava para trocar (a
ultima palavra vence, com "(Era do TioMad.)"), mas **nao havia como deixar o
proximo boss sem ninguem**. A sintaxe que o usuario queria para isso — `.loot-`
— caia no `_NICK_VALIDO.fullmatch("")`, falhava e morria em silencio. Quando a
party desmarcava o revezamento, a unica saida era editar arquivo e reiniciar o
scanner.

Quatro pecas, uma linha fina de ponta a ponta:

| Peca | Onde | O que faz |
|---|---|---|
| `Comando.LOOT_CANCELAR` | `comandos.py` | O primeiro comando destrutivo do vocabulario |
| ramo de cancelamento | `interpretar_dinamico` | Reconhece `.loot-` e as quatro palavras reservadas, nos dois ramos |
| `RegistroDeLoot.cancelar()` | `loot.py` | Apaga `proximo.json`, devolve quem perdeu a vez |
| `responder_cancelamento()` | `loot.py` | Diz de QUEM era e de QUAL boss |
| dispatch | `__main__.py` | Liga o comando a acao, sem eco no grupo |

O texto real, medido:

```
designa : Tiomad pega o loot do proximo Solo Boss, as 10:00.
cancela : Loot do Solo Boss das 10:00 cancelado — era do Tiomad. O aviso sai sem nome.
de novo : Nao havia loot marcado para o Solo Boss das 10:00.
```

## As tres coisas que nao sao detalhe

**1. A ordem dentro do ramo do parser.** O cancelamento e testado ANTES do
`_NICK_VALIDO`, porque "cancelar" casa o charset de nick perfeitamente. Sem
essa ordem, `.loot-cancelar` designaria um personagem chamado "Cancelar" — e a
party ficaria sem jeito nenhum de desmarcar. O preco de D-03 (um char chamado
"Cancelar" nao pode ser designado) esta pago e escrito no codigo.

**2. Apagar nao pode depender da agenda.** `responder_designacao` recusa gravar
sem um Solo Boss na agenda, e esta certo: uma designacao sem alvo nunca consome
e nunca some. `responder_cancelamento` faz o CONTRARIO — chama `cancelar()`
antes de olhar a agenda. Se dependesse, um `config.toml` quebrado ou o Solo Boss
renomeado por engano prenderia a designacao corrente para sempre, sem nenhuma
forma de solta-la pelo WhatsApp. A assimetria esta documentada na docstring e
coberta por teste.

**3. Cancelar e sobre a VEZ, nunca sobre a estatistica.** `cancelar()` toca so o
`proximo.json`; os `pegou_*` e os `nick_*` ficam intactos. Apagar o historico
junto faria meses de loot sumirem num comando de sete letras — teste explicito
garante que `resumo()` e `nicks_conhecidos()` sobrevivem ao cancelamento.

## Um bug real que a Task 2 pegou

`.loot cancelar` (duas palavras) nao caia no ramo do hifen e chegava intacto ao
`_NICK_VALIDO`, que aceitava "cancelar" como nick valido. O comando **designava
um personagem inexistente chamado "cancelar"** — exatamente o acidente que as
palavras reservadas de D-03 existem para evitar, acontecendo pela porta do lado.
O teste RED da Task 2 falhou com:

```
assert (<Comando.LOOT_DESIGNAR>, 'cancelar') == (<Comando.LOOT_CANCELAR>, '')
```

Corrigido aplicando a mesma ordem do ramo com hifen ao ramo sem hifen.

## Verificacao

| Criterio | Como foi provado |
|---|---|
| `.loot-` apaga | `TestCancelamento`, e a costura em `TestLootNaCostura` |
| O aviso perde a linha "Loot:" | `test_depois_do_cancelamento_o_aviso_sai_sem_a_linha` — tick de 09:50 |
| `.loot` sozinho nao faz nada (D-02) | `test_loot_SOZINHO_continua_sendo_nada` + verify do plano |
| As 4 palavras reservadas cancelam | laco em `test_as_palavras_reservadas_tambem_cancelam`, com maiusculas |
| `.loot-J4guar` continua designando | `test_o_nick_normal_nao_virou_cancelamento` |
| A troca continua anunciando o substituido | `test_substituir_menciona_o_substituido` (ja existia), mais o novo teste de que apos cancelar NAO ha "(Era do X.)" |
| Cancelar 2x nao levanta | `test_cancelar_duas_vezes_nao_levanta` |
| As 4 travas continuam valendo | o comando passa pelo mesmo `comandos_novos`; nenhum caminho de entrada novo |
| Zero dependencia nova | `git diff pyproject.toml` vazio |
| Nada de deteccao/transporte tocado | so `loot.py`, `comandos.py`, `__main__.py` e testes |

**Suite: 566 -> 581 testes, todos verdes**, sem o jogo aberto e sem rede.

## Deviations from Plan

**1. [Rule 3 - Bloqueio] `test_o_vocabulario_e_fechado` precisou crescer**
- **Found during:** Task 1
- **Issue:** O teste afirma o conjunto EXATO de `Comando`; acrescentar
  `LOOT_CANCELAR` o quebrava. O plano nao o mencionava.
- **Fix:** O membro novo entrou na assercao com o comentario dizendo por que
  cresceu — o teste existe justamente para que o vocabulario so cresca DE
  PROPOSITO, entao contorna-lo teria anulado a razao dele existir.
- **Commit:** `9ff4f1c`

**2. [Ajuste de sequencia] A reescrita de `test_loot_sem_nick_nao_faz_nada`
veio na Task 1, nao na Task 2**
- **Issue:** Aquele teste afirmava `.loot-` is None — a verdade que a Task 1
  troca. A restricao de rodar a suite INTEIRA verde antes de cada commit
  tornava impossivel deixa-lo para a Task 2.
- **Fix:** A divisao nos dois testes que o plano pedia (um afirmando que
  `.loot-` cancela, outro que `.loot` sozinho e nada) aconteceu na Task 1. A
  assercao antiga nao ficou viva em lugar nenhum — nem comentada, nem com skip.
- **Commit:** `8278548`

**3. [Gate do tracer] Verificado automaticamente em vez de por checkpoint**
- A Task 1 e `type="tracer"`, o que normalmente pediria um checkpoint humano
  antes da expansao. Com `auto_advance: false` mas `human_verify_mode:
  "end-of-phase"` no config, e com a instrucao explicita do orquestrador de
  executar todas as tarefas, o gate foi cumprido rodando o `<verify>` do tracer
  de ponta a ponta (suite verde + os dois checks de parser e de ciclo de
  import) antes de qualquer tarefa de expansao. Nenhuma camada foi construida
  sobre fundacao nao provada.

## Observacao (fora de escopo, nao tocado)

O `git status` do inicio da sessao mostrava `M config.toml`. Ao fim da execucao
o arquivo aparece limpo, e **nenhum dos quatro commits o toca** (verificado com
`git diff --name-only 8278548~1 HEAD`). Provavelmente o proprio scanner ou o
usuario reverteu a edicao durante a sessao. Registrado por honestidade, sem
acao — mexer em `config.toml` estaria fora do escopo desta tarefa.

## Threat Flags

Nenhuma superficie nova. O comando entra pelo mesmo `comandos_novos` e herda as
quatro travas (so `incoming`, nao `private`, dedupe por id, allowlist de
telefone). O unico risco novo — T-dwp-02, apagar por acidente — esta mitigado
por D-02 (`.loot` sozinho nunca cancela) e pelo dano maximo ser uma linha a
menos num aviso, recomponivel em tres segundos com `.loot-<nick>`.

## Self-Check: PASSED

- `l2scanner/loot.py` — `cancelar` e `responder_cancelamento` presentes (AST)
- `l2scanner/comandos.py` — `LOOT_CANCELAR` e `_PALAVRAS_DE_CANCELAMENTO`
- `l2scanner/__main__.py` — ramo de dispatch com `avisar_o_grupo = False`
- Commits `8278548`, `9ff4f1c`, `e46fba7`, `4eed537` existem no `git log`
- 581 testes passando
