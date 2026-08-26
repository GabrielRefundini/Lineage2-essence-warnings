---
phase: 10-lista-de-presenca-do-solo-boss-pelo-whatsapp
plan: 03b
type: execute
wave: 4
depends_on: ["10-03"]
files_modified:
  - l2scanner/__main__.py
  - tests/test_presenca.py
autonomous: true
requirements: [PRES-05, PRES-06, PRES-08, PRES-09]

estimate:
  tokens: 52000
  raw_tokens: 26000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "Um `.join` de um telefone de membro produz DOIS despachos com textos DIFERENTES: um na conversa de origem e um no grupo (D-09)"
    - "Um `.join` repetido produz UM despacho, so na conversa de origem (D-08)"
    - "Os oito ramos ja existentes de `atender_comandos` mantem exatamente o destino que tinham antes desta fase"
    - "`comandos_novos` recebe `membros` nas DUAS chamadas de `atender_comandos` — sem isso o nivel de membro existe e nunca e consultado"
  artifacts:
    - l2scanner/__main__.py
    - tests/test_presenca.py
  key_links:
    - "atender_comandos -> RespostaDePresenca(privado, grupo|None) -> despachante.despachar(texto, categoria, conversa)"
    - "leitor.membros -> comandos_novos(membros=) — o elo que liga o plano 10-01 ao caminho real"
---

<objective>
Ligar o `.join` e o `.leave` ao despacho, e generalizar o bloco que hoje manda
o MESMO texto para os dois destinos.

**Por que este plano existe separado do 10-03.** A generalizacao do bloco final
de `atender_comandos` toca os OITO ramos de comando ja existentes, num arquivo
com 19-20% de cobertura — o mesmo `__main__.py` onde os 3 de 3 warnings do
ultimo code review moravam, e onde o projeto ja teve o defeito de responder no
grupo uma pergunta feita no privado (medido ao vivo: pergunta as 23:04:42 na
conversa 1, resposta as 23:04:52 na 13). Deixar essa mudanca no mesmo plano
que carrega a maior superficie nova da fase poria o risco de regressao dos
comandos ANTIGOS dentro do plano que ja e o mais pesado. Aqui ele fica
sozinho, com o teste tabelado dos oito destinos ao lado.

Purpose: a resposta chega onde a pergunta foi feita, e o grupo recebe a sua
propria redacao.
Output: os ramos `Comando.JOIN` e `Comando.LEAVE`, o bloco de despacho
falando privado-mais-grupo, e o teste tabelado que protege os oito ramos
antigos.

## Legenda das decisoes
Ver a tabela D-01..D-14 em `10-01-PLAN.md`. Este plano implementa D-08, D-09 e
D-10 no ponto de despacho.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/10-lista-de-presenca-do-solo-boss-pelo-whatsapp/10-CONTEXT.md
@.planning/phases/10-lista-de-presenca-do-solo-boss-pelo-whatsapp/10-PATTERNS.md
@.planning/phases/10-lista-de-presenca-do-solo-boss-pelo-whatsapp/10-01-SUMMARY.md
@.planning/phases/10-lista-de-presenca-do-solo-boss-pelo-whatsapp/10-03-SUMMARY.md
</context>

<interface_context>
Tudo o que este plano consome ja existe quando ele comeca:

```
comandos.Comando.JOIN / .LEAVE          # plano 10-01
comandos.MensagemDeComando.nick         # plano 10-01, vindo do mapa [[membro]]
comandos.LeitorDeComandos.membros       # plano 10-01
presenca.RespostaDePresenca(privado, grupo)   # plano 10-03
presenca.responder_join / responder_leave     # plano 10-03
```

Este plano NAO cria simbolo novo em modulo de biblioteca. Ele muda so o
orquestrador (`l2scanner/__main__.py`) e acrescenta teste.

**O bloco a generalizar**, hoje em `__main__.py:658-667`: despacha `resposta`
na conversa de origem e, quando `avisar_o_grupo`, despacha a MESMA `resposta`
no grupo. Os oito ramos antigos produzem `(str, bool)`; os dois novos produzem
`RespostaDePresenca`. O bloco final passa a falar UMA lingua so — privado mais
grupo-ou-`None` — e `avisar_o_grupo = True` vira "o grupo recebe o mesmo texto
do privado", que e exatamente o que ele ja significa.

**Destinos de hoje, que este plano tem de preservar caractere a caractere:**

| Comando | Origem | Grupo |
|---|---|---|
| `.cancelar` | sim | sim (mesmo texto) |
| `.solo` / `.party` | sim | sim (mesmo texto) |
| `.status` | sim | nao |
| `.help` | sim | nao |
| `.loot-<nick>` | sim | nao |
| `.loot-` | sim | nao |
| `.<nick>` | sim | nao |
| `.corrigir-<nick>` | sim | nao |
| `.pegou <hora> <nick>` | sim | nao |
</interface_context>

<tasks>

<task type="auto">
  <name>Tarefa 1: A rede de seguranca dos oito ramos, ANTES de mexer neles</name>
  <files>tests/test_presenca.py</files>
  <read_first>
    - `l2scanner/__main__.py` linhas 525-668 — `atender_comandos` inteiro, com atencao ao bloco final (658-667) e ao comentario "RESPONDE ONDE PERGUNTARAM", que carrega a medicao ao vivo do defeito que o bloco conserta.
    - `tests/test_comandos.py` linhas 140-230 — o idioma de montar mensagem crua com telefone de allowlist e passar pelo caminho real.
    - `tests/test_sessao.py` linhas 60-90 — o despachante falso e o formato `(texto, categoria, conversa)`.
  </read_first>
  <action>
Escrever o teste tabelado ANTES de tocar no `__main__.py`. E a ordem que
importa: um teste escrito depois da refatoracao prova que a refatoracao
concorda consigo mesma; escrito antes, ele e a rede.

Uma classe em `tests/test_presenca.py` que exercita `atender_comandos` de
verdade, com:
- um leitor falso devolvendo uma lista de mensagens cruas,
- um `RegistroEmDisco` sobre `tmp_path`,
- um despachante falso que grava `(texto, categoria, conversa)`,
- o telefone de dono, para que TODOS os ramos sejam alcancaveis.

A tabela dos casos e a do `<interface_context>` acima: para cada um dos nove
comandos ja existentes, a sintaxe, o destino esperado na origem e o destino
esperado no grupo. Asserção sobre a LISTA de despachos: quantos sairam, em
qual conversa cada um, e — para os que ecoam — que o texto do grupo e IGUAL ao
da origem. Nada de afirmar a redacao inteira; o que se afirma e o destino e a
igualdade ou diferenca entre os dois textos.

Este teste tem de passar contra o codigo COMO ELE ESTA HOJE, sem nenhuma
mudanca no `__main__.py`. Rodar e ver verde e o criterio de conclusao da
tarefa. Se algum caso ja falhar agora, isso e uma descoberta sobre o
comportamento atual e tem de ser registrada no SUMMARY antes de seguir — nao
ajustar o teste ao que saiu.
  </action>
  <verify>
    <automated>python -m pytest tests/test_presenca.py -q -k "destino"</automated>
  </verify>
  <acceptance_criteria>
    - A classe cobre os NOVE comandos ja existentes (`.cancelar`, `.solo`, `.party`, `.status`, `.help`, `.loot-<nick>`, `.loot-`, `.<nick>`, `.corrigir-<nick>`, `.pegou`), cada um com o destino esperado.
    - O teste passa contra o `__main__.py` intocado — provado rodando antes de qualquer edicao de codigo de producao.
    - Para `.cancelar`, `.solo` e `.party` o teste afirma que o texto do grupo e IGUAL ao da origem; para os demais, afirma que nao houve despacho de grupo.
    - Nenhuma asserção depende da redacao completa de uma mensagem.
  </acceptance_criteria>
  <done>Os oito ramos antigos tem prova de destino, verde, antes de alguem encostar no bloco de despacho.</done>
</task>

<task type="auto" tdd="true">
  <name>Tarefa 2: Os ramos novos e o par de destinos</name>
  <files>l2scanner/__main__.py, tests/test_presenca.py</files>
  <read_first>
    - `l2scanner/__main__.py` linhas 589-600 — o ramo `LOOT_DESIGNAR`, a forma a copiar, incluindo a guarda de recurso ausente e o comentario que justifica nao ecoar.
    - `l2scanner/__main__.py` linhas 1190-1300 e 795-870 — as DUAS chamadas de `atender_comandos` (laco principal e `--so-agenda`).
    - `l2scanner/presenca.py` (plano 10-03) — `RespostaDePresenca`, `responder_join`, `responder_leave`.
    - `l2scanner/__main__.py` linhas 505-522 — `_para_o_console` e a regra de nao moldurar texto com quebra de linha.
  </read_first>
  <behavior>
    - `.join` de telefone de membro: DOIS despachos — um na conversa de origem, um sem conversa alvo (o grupo) — com textos DIFERENTES.
    - `.join` repetido: UM despacho, na conversa de origem (D-08).
    - `.leave` de quem estava na lista: DOIS despachos, textos diferentes.
    - `.leave` de quem nunca joinou: UM despacho, na conversa de origem.
    - `.join` de um dono que NAO esta em `[[membro]]`: UM despacho na origem, explicando que nao ha nick; nenhum despacho de grupo, e nenhum nick inventado (D-10).
    - Os nove ramos antigos: destino identico ao da Tarefa 1.
    - Sem despachante, nada levanta e o log continua saindo.
  </behavior>
  <action>
Em `l2scanner/__main__.py`, `atender_comandos`:

1. Dois ramos novos, `Comando.JOIN` e `Comando.LEAVE`, na forma do ramo
   `LOOT_DESIGNAR`. Chamam `responder_join` / `responder_leave` com
   `pedido.nick` — o nick vindo do mapa `[[membro]]` (plano 10-01) — e recebem
   uma `RespostaDePresenca`.

2. Generalizar o bloco final de despacho. Os ramos antigos continuam
   produzindo uma string e o booleano `avisar_o_grupo`; converter, ao fim da
   cadeia de ramos, o resultado de cada ramo numa unica representacao —
   privado mais grupo-ou-`None` — e deixar o bloco de despacho falar so essa
   lingua. `avisar_o_grupo = True` vira "o grupo recebe o mesmo texto do
   privado". Comentario dizendo que esta e a primeira vez no projeto em que os
   dois destinos recebem redacoes DIFERENTES, e por que (D-09): sem o eco
   privado, um `.join` recusado por autorizacao e um que funcionou sao
   indistinguiveis para quem digitou.

3. `_para_o_console` continua recebendo o texto do PRIVADO, que e a resposta a
   quem perguntou. Havendo texto de grupo diferente, logar os dois, cada um na
   sua linha — a regra de nao moldurar texto com quebra de linha continua
   valendo.

4. `pedido.nick` pode ser `None` (dono fora do `[[membro]]`). O ramo passa
   `None` adiante e quem responde e `presenca.py`, que ja tem esse caminho.
   Nao inventar nick aqui, em nenhuma hipotese (D-10).

5. Passar `membros=leitor.membros` na chamada de `comandos_novos` dentro de
   `atender_comandos`. Conferir as DUAS chamadas de `atender_comandos` (laco
   principal e `--so-agenda`) — sem isso o nivel de membro existe e nunca e
   consultado, e a fase inteira fica muda para os party-mates.

Acrescentar a classe de teste dos ramos NOVOS ao lado da tabela da Tarefa 1,
no mesmo idioma (leitor falso, despachante falso, asserção sobre a lista de
despachos).
  </action>
  <verify>
    <automated>python -m pytest tests/test_presenca.py tests/test_comandos.py -q</automated>
  </verify>
  <acceptance_criteria>
    - O teste tabelado da Tarefa 1 continua verde DEPOIS da generalizacao, sem uma linha alterada nele. E esse o criterio de que os oito ramos antigos nao regrediram.
    - Um `.join` de membro produz dois despachos com textos diferentes; um `.join` repetido produz um.
    - Um `.leave` de quem nunca joinou produz um despacho, na conversa de origem.
    - `.join` de dono fora do `[[membro]]` nao produz despacho de grupo e nao inventa nick.
    - `comandos_novos` recebe `membros` nas duas chamadas de `atender_comandos` — afirmado por teste que constroi o leitor com membros e ve o `.join` atravessar.
    - `python -m pytest tests/ -q` passa inteiro; a contagem coletada nao caiu (linha de base 785 em 2026-08-26).
  </acceptance_criteria>
  <reversibility rating="costly">
    O bloco de despacho e o funil por onde TODA resposta de comando passa. Um
    erro aqui nao quebra um recurso — muda o destino de todos eles ao mesmo
    tempo, e o modo de falha e silencioso (a mensagem chega, no lugar errado).
    E por isso que a rede da Tarefa 1 vem antes.
  </reversibility>
  <done>Quem manda `.join` no privado ve uma linha curta chegar, o grupo ve o nick entrar na lista, e os comandos antigos respondem onde sempre responderam.</done>
</task>

</tasks>

<artifacts_produced>
## Artifacts this phase produces — parte do plano 10-03b

Este plano nao cria simbolo novo em modulo de biblioteca. Ele produz
comportamento no orquestrador e a rede de teste que o protege.

**`l2scanner/__main__.py`**
| Mudanca | Tipo |
|---|---|
| ramos `Comando.JOIN` e `Comando.LEAVE` em `atender_comandos` | comportamento novo |
| bloco de despacho falando privado-mais-grupo-ou-`None` | generalizacao dos oito ramos existentes |
| `membros=leitor.membros` em `comandos_novos` | elo que ativa o nivel de membro do plano 10-01 |

**`tests/test_presenca.py`**
| Classe | Papel |
|---|---|
| tabela de destino dos nove comandos existentes | rede de regressao, escrita e verde ANTES da refatoracao |
| classe dos ramos `.join`/`.leave` | prova das duas redacoes (D-09) e do eco unico (D-08) |
</artifacts_produced>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `atender_comandos` -> `despachante` | O funil unico por onde toda resposta de comando sai |
| conversa de origem vs. conversa de aviso | Duas listas de destinatarios diferentes; trocar uma pela outra e vazamento |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-10-21 | Information Disclosure | generalizacao do bloco de despacho trocando o destino de um ramo antigo | high | mitigate | Teste tabelado dos nove comandos escrito e VERDE antes da refatoracao, e re-executado sem alteracao depois. O modo de falha e silencioso (a mensagem chega, no lugar errado) e ja aconteceu neste projeto — medido ao vivo em 2026-08-25 (Tarefas 1 e 2) |
| T-10-11 | Denial of Service | `.join` repetido ecoando no grupo a cada mensagem | medium | mitigate | O tri-estado `ja_existia` do plano 10-03 devolve `grupo is None`; criterio de aceite CONTA os despachos (Tarefa 2) |
| T-10-22 | Spoofing | nick inventado no despacho quando `pedido.nick` e `None` | medium | mitigate | O ramo repassa `None` e quem responde e `presenca.py`; criterio de aceite dedicado ao dono fora do `[[membro]]` (D-10, Tarefa 2) |
| T-10-SC | Tampering | instalacao de pacote | high | mitigate | Zero dependencia nova |
</threat_model>

<verification>
1. `python -m pytest tests/ -q` — suite inteira passa; contagem coletada nao caiu (linha de base 785).
2. `python -m pytest tests/test_presenca.py -q -k "destino"` — a tabela dos nove comandos existentes esta verde.
3. `git diff tests/test_presenca.py` mostra que a classe da tabela de destino nao foi alterada depois de escrita.
4. `git diff --stat` nao toca arquivo de dependencia.
</verification>

<success_criteria>
- PRES-05, PRES-06, PRES-08 e PRES-09 chegam ao caminho real de despacho.
- Os nove comandos ja existentes respondem exatamente onde respondiam antes.
- O nivel de membro do plano 10-01 deixa de ser codigo inalcancavel.
</success_criteria>

<output>
Create `.planning/phases/10-lista-de-presenca-do-solo-boss-pelo-whatsapp/10-03b-SUMMARY.md` when done
</output>
