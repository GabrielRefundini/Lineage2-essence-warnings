---
task: 260831-buo
workstream: default
verified: 2026-08-31T15:05:49Z
status: passed
score: 9/9 must-haves verified
behavior_unverified: 0
overrides_applied: 0
mode: quick-full
diff_verified: "b9d2e46..HEAD, restrito a 3520a83 + c5e8ddf + 7c30981 (merge 3733262)"
observations: # Nao bloqueiam. Nenhuma contradiz uma decisao travada.
  - id: OBS-1
    severity: cosmetic
    where: "l2scanner/agenda.py — responder_lista_de_presenca, ramo do boss CALADO"
    what: "A frase montada emenda 'Mande /ativarsoloboss se quiser o lembrete de volta. e o historico de loot ... continua inteiro.' — minuscula depois de ponto final, numa mensagem que o usuario le no WhatsApp."
    why_not_blocker: "O conteudo e verdadeiro e completo; e defeito de prosa, nao de fato. O ramo do boss FALANDO nao tem o problema (termina em virgula, de proposito)."
  - id: OBS-2
    severity: low
    where: "l2scanner/comandos.py — _AJUDA[Comando.DESATIVAR_LISTA]; README.md"
    what: "A ajuda e o README dizem '10 minutos' como LITERAL, enquanto responder_lista_de_presenca deriva os minutos de evento.avisar_minutos_antes (provado com um evento de 25)."
    why_not_blocker: "O config.toml do repositorio diz 10, entao hoje a ajuda e verdadeira. Se o usuario editar avisar_minutos_antes, a ajuda e o README passam a divergir da resposta do comando."
  - id: OBS-3
    severity: cosmetic
    where: "README.md — a tabela das quatro combinacoes"
    what: "As colunas tem o nome do comando que DESLIGA (`/desativarsoloboss`) mas as celulas dizem 'ligado'/'desligada', que descrevem o estado do RECURSO. Ler o cabecalho como estado do comando inverte as linhas 1 e 3."
    why_not_blocker: "A terceira coluna desambigua cada linha, e a prosa acima da tabela ja diz o recorte. Nenhuma afirmacao e falsa."
  - id: OBS-4
    severity: latent
    where: "l2scanner/presenca.py — _evento_com_lista_desligada"
    what: "O helper recusa /entrar e /sair se QUALQUER evento com chamar_minutos_antes > 0 tiver a lista desligada — nao so o evento do proximo /entrar."
    why_not_blocker: "Nao alcancavel no config.toml real: so o Solo Boss tem chamar_minutos_antes. E coerente com o modulo, que ja era de lista unica (/entrar e /sair nao tem argumento de evento). Nao foi introduzido por esta mudanca."
---

# Quick 260831-buo — Relatorio de Verificacao

**A barra de aceite:** com a lista desligada, o aviso de ANTECEDENCIA de 10
minutos do Solo Boss ainda sai. Se parar de chegar, a mudanca nao vale nada.

**Veredito:** a barra foi atendida, e as quatro decisoes travadas (D1–D4) se
sustentam **quando as funcoes sao dirigidas de verdade**, e nao so lidas.

**Metodo.** Tudo abaixo foi produzido chamando as funcoes reais com uma pasta
de marcadores temporaria e comparando disco antes/depois. A suite completa e o
`ruff` NAO foram re-rodados (o orquestrador ja os mediu); o esforco foi todo no
que aquela checagem nao conseguia ver.

## Verdades Observaveis

| # | Verdade | Status | Evidencia |
|---|---|---|---|
| 1 | Com a lista desligada, a CHAMADA para de sair | VERIFICADA | `avisos_devidos(18:10)` -> `NADA`, pelo `config.toml` real |
| 2 | Com a lista desligada, o lembrete de 10 min CONTINUA | VERIFICADA | `19:50` -> Solo Boss **e** Prime, nas duas pontas do cenario |
| 3 | `/entrar` e `/sair` recusam e NAO escrevem em disco | VERIFICADA | disco byte a byte igual antes/depois; ver abaixo |
| 4 | O fechamento nao sai e o `fechado_` NAO queima | VERIFICADA | `fechar_ocorrencias` -> `[]`, nenhum `fechado_*` criado |
| 5 | `/loot-<nick>` recusa; a linha `Loot:` some | VERIFICADA | `.loot/` inalterado; aviso sem a cauda `Loot:` |
| 6 | `/pegou`, `/corrigir`, `/<nick>` e o consumo ficam intactos | VERIFICADA | 5 respostas identicas ligada-vs-desligada, pasta identica |
| 7 | Sobrevive ao restart e nao expira na poda | VERIFICADA | novo `RegistroEmDisco` + `podar(2030-01-01)` |
| 8 | `/status` diz a verdade nas QUATRO combinacoes | VERIFICADA | as quatro rodadas, cada chave nomeada separadamente |
| 9 | A CHAMADA e o texto curto de D4 | VERIFICADA | `Solo Boss as 20:00. Quem vai? (/entrar /sair no privado)` |

**Score: 9/9.** Nenhuma verdade ficou "presente mas nao exercitada".

---

## 1. D2 (b), (c) e (d) dirigidos, nao lidos

### (b) `/entrar` e `/sair` — recusam E nao escrevem

Com `TioMad` **ja na lista** e a lista desligada em seguida:

```
disco antes : ['lista_desligada_solo-boss', 'presenca_2026-08-31_solo-boss-2000_tiomad']
disco depois: ['lista_desligada_solo-boss', 'presenca_2026-08-31_solo-boss-2000_tiomad']
INALTERADO: True
```

- `responder_join` -> privado com a recusa, **`grupo=None`**.
- `responder_leave` -> a mesma recusa, **`grupo=None`**, e `presentes(...)`
  continua `frozenset({'tiomad'})` — o `/sair` tambem nao **remove**.
- Com a lista **ligada**, `/entrar` volta a gravar
  `presenca_2026-08-31_solo-boss-2000_tiomad`. O caminho ligado nao regrediu.

**O guarda e mesmo prependido — provado por acidente.** Uma primeira rodada
minha passou os argumentos na ordem errada (`nick` no lugar de `agora`). Com a
lista **desligada** as duas funcoes responderam certo e **nao levantaram**;
com a lista ligada a mesma chamada estourou `AttributeError` em
`ocorrencia_do_join`. So um guarda que roda antes de qualquer resolucao produz
esse par de resultados. O caso do dono sem `[[membro]]` (`nick=""`) tambem
recebe a recusa da lista, e nao o "Adicione um bloco `[[membro]]`".

### (c) O fechamento — nao sai E nao queima o marcador

```
presentes na ocorrencia: frozenset({'tiomad'})
fechar_ocorrencias(20:01) -> []
marcadores fechado_ criados: []
disco INALTERADO: True
```

E o contra-teste que da sentido ao `continue` estar **antes** do `fechar`:

```
religar -> religada
fechar_ocorrencias(20:03) -> [Fechamento(evento='Solo Boss', alvo=20:00, nicks=('tiomad',))]
fechado_ agora: ['fechado_2026-08-31_solo-boss-2000']
```

Religar dentro da tolerancia ainda fecha. Se o marcador tivesse queimado no
tick mudo, aquela lista ficaria muda para sempre.

### (d) A designacao de loot

```
aviso (lista LIGADA)  : ... Hora de voltar para a cidade e se preparar. Loot: J4guar.
aviso (lista DESLIGADA): ... Hora de voltar para a cidade e se preparar.
```

`/loot-<nick>` com a lista desligada: recusa, **`.loot/` inalterado**, e a
designacao anterior segue intacta. Reproduzido tambem pelo `config.toml` real.

**A armadilha de tipo nao foi pisada.** Nos tres pontos de costura o valor
passado e um `bool` derivado de `apelido_do_evento(NOME_DO_SOLO_BOSS) in ...`,
nunca o `frozenset`. Dirigido: com a lista do Solo Boss desligada, o booleano
do TvT continua `False` — a linha `Loot:` do TvT nao cairia junto.

---

## 2. D3 — o historico de loot esta genuinamente intocado

Duas execucoes gemeas, unica diferenca o marcador em disco:

| Comando | Ligada vs Desligada |
|---|---|
| `/pegou 18:00 TioMad` | IGUAL |
| `/corrigir Kaus` | IGUAL |
| `/Kaus` | IGUAL |
| `/TioMad` | IGUAL |
| `/loot-` (cancelar) | IGUAL |

E a pasta resultante e a mesma lista de arquivos nas duas
(`nick_kaus`, `nick_tiomad`, `pegou_2026-08-31-1800_kaus`).

**A designacao anterior continua sendo consumida** — o comportamento que o
SUMMARY declara deliberado, agora confirmado:

```
DESLIGA a lista -> desligada
consumir(20:00) -> Designacao(nick='J4guar', alvo=20:00, ...)
.loot depois: ['nick_j4guar', 'pegou_2026-08-31-2000_j4guar']
resumo J4guar: (1, 20:00)
```

---

## 3. Durabilidade e poda

```
_PREFIXOS_SEM_DATA   : ('evento_calado_', 'lista_desligada_')
_PREFIXOS_CONHECIDOS : ('cancelado_', 'presenca_', 'fechado_', 'nascimento_', 'anuncio_')
LISTA_DESLIGADA em SEM_DATA   : True
LISTA_DESLIGADA em CONHECIDOS : False
baldes disjuntos              : True
```

Novo `RegistroEmDisco` na mesma pasta -> `frozenset({'solo-boss'})`.
`podar(hoje=2030-01-01)` (quatro anos depois) -> marcador **ainda em disco**.
Mais um restart depois da poda -> ainda desligada. Nada religa sozinho.

---

## 4. `/status` nas quatro combinacoes

| soloboss | lista | Resposta real de `_obedecer_status` |
|---|---|---|
| ON | ON | `Scanner: Vigiando normalmente, proximo: Solo Boss as 20:00.` |
| ON | OFF | `..., lista de presenca DESLIGADA de Solo Boss, proximo: ...` |
| OFF | ON | `..., avisos DESATIVADOS de Solo Boss, proximo: ...` |
| OFF | OFF | `..., avisos DESATIVADOS de Solo Boss, lista de presenca DESLIGADA de Solo Boss, proximo: ...` |

As quatro sao verdadeiras, e as duas chaves aparecem **com nomes diferentes**:
o usuario consegue dizer qual comando desfaz qual estado.

**E a resposta do proprio comando consulta a outra chave.** Dirigido:

- boss falando: `O lembrete de 10 minutos antes CONTINUA chegando,`
- boss calado: `O lembrete de 10 minutos antes tambem nao esta saindo, mas por
  outro motivo: os avisos do Solo Boss estao desativados. Mande
  /ativarsoloboss ...`

Com um evento de `avisar_minutos_antes = 25` a frase diz **25** — os minutos
saem do `EventoAgendado`, nao de um literal. (Ver OBS-1 sobre a emenda da
frase no ramo calado.)

---

## 5. Fronteira de autorizacao

```
COMANDOS_DE_MEMBRO: ['JOIN', 'LEAVE']
DESATIVAR_LISTA fora: True
ATIVAR_LISTA fora   : True
```

O conjunto **nao foi alargado**: continua com exatamente `{JOIN, LEAVE}`, e o
diff de `l2scanner/comandos.py` nao toca a linha 237. Um party-mate nao
desliga a lista de presenca dos outros.

---

## 6. Os quatro tripwires — satisfeitos, nao enfraquecidos

| # | Onde | Asercao hoje | Veredito |
|---|---|---|---|
| 1 | `test_a_ajuda_cobre_todo_comando` | `set(Comando) - set(_AJUDA)` **e** `set(_AJUDA) - set(Comando)`, os dois vazios | igualdade bidirecional, intacta |
| 2 | `test_o_membro_e_RECUSADO_em_tudo_que_nao_e_dele` | `set(Comando) - COMANDOS_DE_MEMBRO`, derivado, com guarda contra prova vazia | derivado, intacto |
| 3 | `TestDestinoDosComandosAntigos` | `antigos - cobertos` vazio, com `assert antigos` contra prova vazia | exaustivo, intacto |
| 4 | `test_o_vocabulario_e_fechado` | `assert set(Comando) == { ...literal... }` | **igualdade**, nao subset |

**Diffs somente-insercao, conferido por `git --numstat`:**

- `tests/test_presenca.py`: **8 insercoes / 0 delecoes** no commit `7c30981`.
- `tests/test_comandos.py`: **14 insercoes / 0 delecoes** no commit `c5e8ddf`.
- (`tests/test_presenca.py` mostra 24/0 no intervalo cheio `b9d2e46..HEAD`
  porque o merge do workstream `identidade` contribui as outras 16.)

O unico arquivo de teste com delecoes e `test_desativar_solo_boss.py` (5/5), e
as cinco sao **exclusivamente** o rename `nomes_calados` -> `nomes_dos_eventos`:
nenhum valor de asercao mudou.

Rodei os arquivos alcancados: `test_desativar_lista_de_presenca.py`,
`test_comandos.py`, `test_presenca.py`, `test_desativar_solo_boss.py`,
`test_agenda.py`, `test_loot.py` -> **780 passed**.

---

## 7. Os dois desvios documentados

### (i) O rename arrastado para a Tarefa 2 — o motivo e real

Extrai a arvore do commit intermediario `c5e8ddf` e importei:

```
IMPORT OK em c5e8ddf
```

O commit da Tarefa 2 e importavel. Se o rename tivesse ficado sem as quatro
referencias, `from .agenda import nomes_calados` estouraria `ImportError` no
`__main__.py` e derrubaria a suite inteira, nao tres testes. O desvio comprou
atomicidade real. Nao sobrou nenhuma referencia a `nomes_calados` na arvore
rastreada (as unicas que o `grep` encontra vivem em `.claude/worktrees/`, que
`git ls-files` confirma **nao ser rastreado**).

### (ii) O `909` — o bug era real, e o conserto exercita o que promete

Escrevi um teste de mutacao que restaura o codigo **como estava antes do
conserto** (os dois comandos com `ident=909`) e mede o resultado:

```
eventos_calados   : frozenset({'solo-boss'})
listas_desligadas : frozenset()
```

O segundo comando morre mesmo no dedup do `comando_<id>`: com o id
compartilhado, `test_as_duas_chaves_convivem_pelo_caminho_real` passaria
**mesmo que o ramo de despacho novo nao existisse**. Com `ident=1` / `ident=2`
as duas asercoes ficam verdadeiras por merito. O conserto e real e o teste
agora exercita o despacho.

Bonus verificado: o commit de teste `3520a83` era genuinamente **vermelho** —
`ImportError: cannot import name 'PREFIXO_LISTA_DESLIGADA'`. A ordem
teste-antes-do-codigo e verdadeira.

---

## 8. Documentacao vs comportamento

**A pergunta central — o README ou o `config.toml` prometem o lembrete num
estado onde `/desativarsoloboss` tambem esta ligado? NAO.**

- O README qualifica a promessa com a tabela das quatro combinacoes, cuja
  linha `desligado | desligada` diz **"nada"**.
- O `config.toml` descreve `/desativarsoloboss` como *"cala o evento INTEIRO —
  nem a chamada de 1h50, nem o lembrete de 10 minutos"*, o que e verdade
  medida, e so entao promete o lembrete para `/desativarlista`.
- E a superficie que o usuario realmente le no momento do risco — a resposta do
  proprio comando — **troca a frase** quando o boss esta calado (secao 4).

O bloco novo do `config.toml` sobre autorizacao (`NEM /desativarsoloboss,
/desativarlista ... ficam de fora`) confere com o codigo (secao 5).

Ver OBS-2 e OBS-3 para duas imprecisoes menores que nao chegam a mentir.

---

## Anti-padroes e higiene

- `TBD` / `FIXME` / `XXX` nos arquivos tocados: **nenhum**.
- `TODO` / `HACK` / `PLACEHOLDER`: os acertos do `grep` sao todos a palavra
  portuguesa **TODO/TODOS** ("todos os avisos"), nao marcadores de divida.
- `ruff check` nos seis modulos e nos quatro arquivos de teste: **All checks
  passed** (re-conferido).
- Vocabulario: `/desativarlista`, `/desativarpresenca`, `/ativarlista`,
  `/ativarpresenca`, `/desativar-lista` e `/desativar lista` todos resolvem;
  `/lista` e `/presenca` sozinhos resolvem para `None`, como documentado.

## Fora de escopo, declarado no SUMMARY e confirmado

O painel do console (`desenhar_status`) nao mostra a lista desligada. O
requisito acordado era o `/status`, e ele esta cumprido nas quatro combinacoes.

---

_Verificado: 2026-08-31T15:05:49Z_
_Verificador: Claude (gsd-verifier), modo quick-full_
