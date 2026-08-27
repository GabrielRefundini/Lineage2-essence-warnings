---
phase: 10-lista-de-presenca-do-solo-boss-pelo-whatsapp
reviewed: 2026-08-26T00:00:00Z
depth: deep
files_reviewed: 8
files_reviewed_list:
  - l2scanner/comandos.py
  - l2scanner/config.py
  - l2scanner/agenda.py
  - l2scanner/presenca.py
  - l2scanner/loot.py
  - l2scanner/sessao.py
  - l2scanner/__main__.py
  - config.toml
findings:
  critical: 2
  warning: 11
  info: 0
  total: 13
status: fixed
fixed_at: 2026-08-26
fixed: 13
declined: 0
baseline_antes: "1003 passed, 2 skipped"
baseline_depois: "1051 passed, 2 skipped"
---

# Phase 10: Code Review Report

> **DISPOSICAO (2026-08-26).** Os 13 achados foram consertados; nenhum foi
> recusado. A tabela abaixo diz onde cada um foi parar. Suite: **1003 -> 1051
> passed, 2 skipped**, verde. `ruff check l2scanner/` continua com os mesmos 2
> `E741` pre-existentes de `visao.py` e nenhum lint novo. Nenhum teste foi
> enfraquecido: os tres que mudaram estao justificados na secao "Testes que
> mudaram", no fim deste arquivo.
>
> **Onde os gates rodaram:** no worktree isolado
> `.claude/worktrees/agent-ad448455e64873dcc`, que compartilha o interpretador
> do sistema (`python -m pytest`, `python -m ruff`) — o projeto nao depende de
> `node_modules` nem de venv para a suite, entao os numeros sao reproduzives no
> checkout principal depois do merge.

| Achado | Disposicao | Commit | Onde |
|---|---|---|---|
| CR-01 | corrigido | `2ec5289` | `comandos.py`, `config.py`, `__main__.py` |
| CR-02 | corrigido | `c8c190e` | `loot.py`, `presenca.py`, `sessao.py`, `__main__.py` |
| WR-01 | corrigido | `c8c190e` | `presenca.py` |
| WR-02 | corrigido | `c8c190e` | `presenca.py` |
| WR-03 | corrigido | `2ec5289` + `72d3290` | `__main__.py`, `config.toml` |
| WR-04 | corrigido | `2ec5289` | `config.py` |
| WR-05 | corrigido | `2ec5289` | `config.py` |
| WR-06 | corrigido | `615fe11` | `__main__.py` |
| WR-07 | corrigido | `615fe11` | `__main__.py` |
| WR-08 | corrigido | `c8c190e` | `presenca.py`, `sessao.py`, `__main__.py` |
| WR-09 | corrigido | `12eb580` | `agenda.py` |
| WR-10 | corrigido | `c8c190e` | `presenca.py` |
| WR-11 | corrigido | `2e8bac0` | `comandos.py` |

**Sobre a atomicidade dos commits.** Cinco achados dividem `c8c190e` porque
reescrevem as MESMAS duas funcoes (`fechar_ocorrencias` e o bloco de
fechamento): separa-los produziria commits que nao compilam ou que passam por
um estado intermediario com o defeito ainda em pe. WR-03 aparece em `2ec5289`
porque mora dentro de `montar_leitor_de_comandos`, a mesma funcao que CR-01
reescreve. O resto e um achado por commit.

**Reviewed:** 2026-08-26
**Depth:** deep (analise cruzada entre modulos + probes executaveis)
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Baseline reproduzido: `python -m pytest tests/ -q` -> **1003 passed, 2 skipped**.
`python -m ruff check l2scanner/` -> apenas os 2 `E741` pre-existentes em
`visao.py`, ja registrados. Nenhum lint novo foi introduzido.

O que a fase promete e que **eu verifiquei como correto**, para nao gastar
tinta com falso alarme:

- **A poda falha em SEGURO.** Probe direto contra `podar()` com dez nomes
  plantados: `comando_12345` (sem data), `lixo_qualquer.txt`, `presenca_` e
  `fechado_` truncados sobrevivem intactos; so os quatro marcadores datados de
  20/08 sumiram. Um prefixo desconhecido cai no `except ValueError` e e DEIXADO
  EM PAZ, que e o comportamento certo.
- **`sugerir_a_vez` e mesmo somente-leitura contra `.loot/`.** A cadeia inteira
  e `resumo -> registros -> iterdir`. Nao ha `open`, `mkdir`, `unlink` nem
  `replace` no caminho. `responder_designacao(presenca=...)` so chama
  `.presentes()`, tambem leitura.
- **Nenhum destino mudou nos oito ramos antigos do despacho.** A traducao
  `RespostaDePresenca(privado=resposta, grupo=resposta if avisar_o_grupo else
  None)` reproduz exatamente o par de `despachar` anterior, e o log so ganha uma
  segunda linha quando os textos DIFEREM (nunca acontece nos ramos antigos).
- **A fronteira de autorizacao esta escrita como inclusao e o tripwire e
  derivado** (`set(Comando) - COMANDOS_DE_MEMBRO`, com guarda contra prova
  vazia). O nivel de dono e avaliado primeiro e e aditivo, como anunciado.
- **As escritas duraveis novas usam `O_CREAT|O_EXCL`** (`entrar`, `fechar`), e o
  tri-estado de `entrar` e deliberado e coerente com `RegistroDeLoot._criar`.

Dito isso, a fase **nao esta pronta para o grupo**. Encontrei duas falhas de
comportamento que so aparecem em cenarios que o usuario vive todo dia:

1. A unica defesa contra a escalada de privilegio membro -> dono e um aviso de
   arranque, e existe uma classe de configuracao plausivel em que esse aviso
   **e deliberadamente suprimido enquanto a escalada acontece** (CR-01).
2. A mensagem que fecha a lista **contradiz, no grupo e no pior momento, a
   designacao de loot que o proprio bot acabou de consumir para aquele mesmo
   boss** (CR-02).

Alem disso, varias justificativas escritas nas docstrings da fase descrevem um
comportamento que o codigo nao tem (WR-01, WR-02). Como este projeto usa a
docstring como contrato de manutencao, um comentario falso e um defeito real:
ele fara o proximo mantenedor "consertar" o que ja estava certo.

---

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: `_mesma_pessoa` cala o aviso de colisao justamente no par que ESCALA privilegio

**File:** `l2scanner/comandos.py:481-534` (`_mesma_pessoa`, `colisoes_de_telefone`)
**Severity:** BLOCKER

**Issue:**
`colisoes_de_telefone` e a UNICA mitigacao da fase para o par perigoso
dono x membro — a propria docstring nomeia isso de "**ESCALADA DE PRIVILEGIO, E
SILENCIOSA**", e o `config.toml` promete ao usuario "o scanner avisa no arranque
quando isso acontece". Mas a linha 530 (`if _mesma_pessoa(...): continue`)
descarta o par sempre que a forma canonica de um for SUFIXO da do outro — e essa
condicao e satisfeita por entradas curtas que `telefone_equivalente` aceita como
validas para autorizar.

Probe executado:

```python
dono   = ["99998888"]                                    # .env com o numero local
membros = [Membro(nick="Korzis", telefone="+5544999998888")]
colisoes_de_telefone(dono, membros)                      # -> []      <-- CALADO
autorizado_para(Comando.LOOT_CORRIGIR,
                {"phone_number": "+5544999998888"}, dono, membros)  # -> True
```

Resultado: **Korzis alcanca `.corrigir` e `.pegou`**, que reescrevem a
estatistica permanente do `.loot/` (pasta sem poda e sem backup), e o console
nao imprime uma unica linha sobre isso. E exatamente o modo de falha que a
funcao foi escrita para impedir.

`_mesma_pessoa` tambem e ruidosa no sentido oposto (`"5544999998888"` x
`"44999998888"`, o MESMO numero, e reportado como colisao), o que mostra que a
heuristica de sufixo nao responde a pergunta que ela diz responder.

**Fix:** parar de suprimir por heuristica e passar a suprimir por prova de
identidade — dois textos so sao "a mesma pessoa" quando as formas canonicas sao
IGUAIS, nunca quando uma e sufixo da outra. E, para o par dono x membro,
nao basta avisar: recuse subir.

```python
def _mesma_pessoa(a: str | None, b: str | None) -> bool:
    ca, cb = _forma_canonica(a), _forma_canonica(b)
    # IGUALDADE, e nao sufixo: um numero curto e sufixo de meio mundo, e e
    # justamente ele que faz a colisao dono x membro passar despercebida.
    return bool(ca) and ca == cb
```

E, em `colisoes_de_telefone`, devolver tambem a ORIGEM de cada lado
(`"dono"`/`"membro"`) para o arranque poder tratar os dois casos com pesos
diferentes — em `__main__.montar_leitor_de_comandos`, um par dono x membro deve
`raise` (ou `return None` derrubando o canal de comandos), nao apenas
`log.warning`. Enquanto for so aviso, um usuario que rode com o console
rolando nunca vai ver.

Independente disso, `_membro_de_dict` deve exigir um telefone com pelo menos
`DIGITOS_FINAIS_DO_TELEFONE` digitos, e o arranque deve exigir o mesmo de
`CHATWOOT_TELEFONES_COMANDO` — um numero mais curto que o corte de comparacao
nao e configuracao valida para uma allowlist.

---

### CR-02: a lista fechada sugere um loot que CONTRADIZ a designacao consumida do mesmo boss

**File:** `l2scanner/presenca.py:418`, `l2scanner/sessao.py:311-322`, `l2scanner/__main__.py:938-945`
**Severity:** BLOCKER

**Issue:**
No tick do horario do boss a ordem e `self.loot.consumir(agora)` e SO DEPOIS
`fechar_ocorrencias(...)`. Quando existia designacao para aquela ocorrencia, o
`consumir` ja creditou o loot ao designado — e a sugestao, calculada em seguida,
enxerga esse credito e aponta para OUTRA pessoa. A frase resultante e colada
numa mensagem que fala do boss que esta COMECANDO AGORA, entao a party le a
sugestao como a instrucao daquele boss.

Probe executado (designacao `.loot-Kaus` para as 20:00, Kaus e J4guar na lista):

```
consumido: Designacao(nick='Kaus', alvo=2026-08-26 20:00, ...)
MENSAGEM NO GRUPO: Solo Boss das 20:00 comecando. Confirmaram: J4guar, Kaus.
                   Sugestao de loot: J4guar (ainda nenhum).
```

Dez minutos antes, o aviso de antecedencia do MESMO boss saiu no MESMO grupo
com `Loot: Kaus`. O bot agora se desmente. Pior: a sugestao muda de significado
conforme o estado do disco — **sem** designacao consumida ela quer dizer "de
quem e a vez NESTE boss"; **com** designacao consumida ela quer dizer "de quem
sera a vez no PROXIMO" — e nada no texto distingue os dois. Quem obedecer a
sugestao errada grava `.pegou`/`.loot-` em `.loot/`, que nao tem poda nem
backup, e o rodizio fica torto para sempre.

O `10-05-SUMMARY.md` trata esse comportamento como acerto
(`test_o_consumo_do_boss_ANTERIOR_ja_conta_na_sugestao`), o que confirma que a
semantica pretendida e "proximo boss" — mas a redacao entregue diz outra coisa.

**Fix:** desambiguar no unico lugar que a party le. Duas saidas, ambas baratas:

```python
# (a) calar a sugestao quando ESTE boss ja tem dono decidido
consumida = self.loot.consumir(agora) if self.loot else None
...
ja_tem_dono = consumida is not None and consumida.alvo == fechamento.alvo
sugestao = (
    sugerir_a_vez(self.loot, frozenset(fechamento.nicks))
    if self.loot and not ja_tem_dono
    else None
)

# (b) OU dizer de qual boss a sugestao fala, em texto_de_fechamento:
texto += f" Sugestao para o proximo boss: {nome} ({quanto})."
```

A opcao (a) e a mais honesta: quando o loot deste boss ja esta decidido e
registrado, a mensagem de fechamento nao tem opiniao nenhuma a dar sobre ele.

---

## Warnings

### WR-01: a justificativa central de `fechar_ocorrencias` descreve um caso que NAO existe

**File:** `l2scanner/presenca.py:337-352` (docstring), com origem em `presenca.py:219`
**Severity:** WARNING

**Issue:** A docstring defende "ler antes de marcar" com um cenario concreto:
*"as 20:00:03 chega o `.join` que saiu do celular as 19:59:58 ... o tick de
20:00:04 encontra a ocorrencia JA fechada e essa pessoa nunca vira mensagem."*
Esse cenario e impossivel. `responder_join` resolve a ocorrencia por
`ocorrencia_da_chamada` -> `proxima_ocorrencia`, que exige `alvo > agora`
ESTRITAMENTE. Probe:

```
join as 20:00:03 -> "Anotado. Voce esta na lista do Solo Boss das 22:00."
presentes(20:00) = frozenset()          <-- a pessoa NUNCA entra na lista que fecha
presentes(22:00) = {'j4guar'}
fechar_ocorrencias @20:00:04 -> []
```

Duas consequencias reais. (1) O `.join` atrasado pela ponte Baileys cai
silenciosamente no boss de DUAS HORAS DEPOIS — a pessoa acha que confirmou o
boss que esta comecando. O eco privado cita o horario (mitigacao D-07), mas nao
ha janela de tolerancia nenhuma. (2) O proximo mantenedor que ler essa docstring
e testar o cenario vai concluir que "ler antes de marcar" nao serve para nada e
pode inverter a ordem, perdendo a propriedade de D-12 (lista vazia nao queima o
marcador), que essa ordem SIM garante.

**Fix:** reescrever a docstring com a justificativa verdadeira (lista vazia nao
pode queimar o marcador, ponto) e, se o `.join` atrasado importa, dar a
`ocorrencia_da_chamada` a mesma tolerancia que o fechamento usa:

```python
def ocorrencia_da_chamada(agora, eventos):
    # Um .join que a ponte entregou com atraso ainda fala do boss que acabou
    # de nascer, e nao do de daqui a duas horas.
    recem = ocorrencias_na_janela(agora, eventos)
    if recem:
        return recem[-1]
    return proxima_ocorrencia(agora, _com_chamada(eventos))
```

(Se essa mudanca for feita, ela precisa vir junto com um teste de que
`fechar_ocorrencias` reabre e anuncia dentro da tolerancia — que e exatamente
o que a docstring de hoje ja afirma acontecer.)

---

### WR-02: `.leave` fica bloqueado por 5 minutos a cada boss, e recusa citando a ocorrencia ERRADA

**File:** `l2scanner/presenca.py:276-284`
**Severity:** WARNING

**Issue:** A recusa de reabrir historico e consultada ANTES de qualquer coisa e
nao distingue de qual lista a pessoa quer sair. `.leave` nao tem argumento,
entao quem estava na lista que acabou de fechar nao consegue sair da lista
SEGUINTE durante toda a tolerancia de 5 minutos. Probe:

```
20:00 = {'kaus'}   22:00 = {'kaus'}
.leave as 20:01 -> "O Solo Boss das 20:00 ja comecou e a lista fechou.
                    Nao da mais para sair dela."
22:00 continua = {'kaus'}        <-- ele queria sair DESTA, e nao conseguiu
```

Com 12 ocorrencias por dia isso e uma hora inteira por dia em que `.leave` esta
quebrado, e a mensagem culpa uma ocorrencia que o usuario nem mencionou.

**Fix:** so recusar quando a pessoa nao tem nada a ganhar com a saida — isto e,
quando ela NAO esta na lista da proxima ocorrencia:

```python
proximo = ocorrencia_da_chamada(agora, eventos)
if proximo is None:
    return _sem_chamada_na_agenda()
nome, alvo = proximo
if registro.sair(chave_da_ocorrencia(nome, alvo), slug):
    return RespostaDePresenca(privado=..., grupo=...)

# so agora a recusa de historico faz sentido: nao havia nada a tirar adiante
fechada = ocorrencia_recem_fechada(agora, eventos)
if fechada is not None and slug in registro.presentes(chave_da_ocorrencia(*fechada)):
    return RespostaDePresenca(privado="... ja comecou e a lista fechou ...")
return RespostaDePresenca(privado=f"Voce nao estava na lista do {nome} das {hora}.")
```

A propriedade que D-14 exige (lista fechada e historico) continua valendo: nada
acima toca na chave da ocorrencia fechada.

---

### WR-03: o log de arranque afirma "Nenhum deles alcanca comando de loot" mesmo quando TODOS alcancam

**File:** `l2scanner/__main__.py:529-538`
**Severity:** WARNING

**Issue:** `autor_autorizado` devolve `True` para qualquer remetente quando
`telefones` esta vazio, e `autorizado_para` consulta esse nivel PRIMEIRO. Probe:

```python
autorizado_para(Comando.LOOT_CORRIGIR, {"phone_number": "+5500000000000"}, [], membros)
# -> True
```

Nesse estado o arranque imprime o aviso `COMANDOS ABERTOS` (linha 515) e, logo
em seguida, incondicionalmente:

```
Presenca: 2 party-mate(s) podem dar .join/.leave (Korzis, J4guar).
Nenhum deles alcanca comando de loot.
```

A segunda frase e falsa exatamente quando importa, e ela e a frase que da
confianca ao usuario. O `config.toml` repete a mesma promessa ("E MAIS NADA").

**Fix:** condicionar a afirmacao ao estado que a sustenta.

```python
if membros:
    if config.telefones_de_comando:
        log.info("Presenca: %d party-mate(s) podem dar .join/.leave (%s). "
                 "Nenhum deles alcanca comando de loot.", ...)
    else:
        log.warning("Presenca: os [[membro]] NAO estao contidos — com "
                    "CHATWOOT_TELEFONES_COMANDO vazio qualquer remetente "
                    "alcanca TODO comando, inclusive .corrigir e .pegou.")
```

---

### WR-04: `ler_membros` estoura `AttributeError` num erro de digitacao plausivel do config.toml

**File:** `l2scanner/config.py:301-314` (`_membro_de_dict`), chamada em `config.py:296`
**Severity:** WARNING

**Issue:** A docstring de `ler_membros` promete: *"ARQUIVO PRESENTE E MAL
FORMADO E ERRO DE ARRANQUE ... um `.join` que some em silencio, e quem digitou
conclui que o bot esta quebrado"*. Mas `_membro_de_dict` assume `dict` sem
verificar. Probe:

```
membro = "isto nao e uma lista de tabelas"  -> AttributeError: 'str' object has no attribute 'get'
membro = [1, 2]                             -> AttributeError: 'int' object has no attribute 'get'
```

`AgendaInvalida` nao e capturada em `__main__` (grep confirma: nenhum
`except AgendaInvalida` no pacote fora de quem levanta), entao o usuario ja
recebe traceback nos dois casos — mas no caso do `AttributeError` ele recebe um
traceback que nao diz NADA sobre o `config.toml`, que e o oposto do contrato
escrito. `membro = "Kaus"` no lugar de `[[membro]]` e o erro exato que um
nao-desenvolvedor comete.

**Fix:**

```python
def _membro_de_dict(bruto, indice: int) -> Membro:
    onde = f"[[membro]] #{indice + 1}"
    if not isinstance(bruto, dict):
        raise AgendaInvalida(
            f"{onde}: precisa ser um bloco [[membro]] com nick e telefone, "
            f"e nao {type(bruto).__name__}."
        )
    if bruto.get("nick"):
        onde = f"membro '{bruto['nick']}'"
    ...
```

(Enquanto se esta ali: `_evento_de_dict` carrega o mesmo buraco. Nao pertence a
esta fase, mas o conserto e a mesma linha.)

---

### WR-05: dois `[[membro]]` com o mesmo nick sao aceitos e passam a compartilhar uma vaga

**File:** `l2scanner/config.py:301-335`
**Severity:** WARNING

**Issue:** Nada valida unicidade de `nick`. Probe:

```
[[membro]] nick="Kaus" telefone="+5544999998888"
[[membro]] nick="Kaus" telefone="+5544977776666"
-> [Membro(nick='Kaus', ...), Membro(nick='Kaus', ...)]     # aceito
```

Como a lista de presenca e indexada por `apelido(nick)`, as duas pessoas
disputam o mesmo arquivo `presenca_<chave>_kaus`: a segunda a mandar `.join`
recebe *"Voce ja esta na lista"* sem nunca ter entrado, e o `.leave` de uma
retira a outra. `nomes_dos_membros` tambem colapsa silenciosamente (dict por
slug). E o modo de falha que `colisoes_de_telefone` foi escrita para tratar no
eixo do telefone, deixado aberto no eixo do nick.

**Fix:** em `ler_membros`, depois de montar a lista:

```python
vistos: dict[str, str] = {}
for m in membros:
    slug = apelido(m.nick)          # ja importado via NICK_VALIDO/loot
    if slug in vistos:
        raise AgendaInvalida(
            f"membro '{m.nick}': o nick colide com '{vistos[slug]}' — dois "
            f"[[membro]] nao podem dividir a mesma vaga na lista de presenca."
        )
    vistos[slug] = m.nick
```

---

### WR-06: `avisar_o_grupo` nunca e inicializado, e os ramos novos nao o definem

**File:** `l2scanner/__main__.py:746-750` (uso), ramos `JOIN`/`LEAVE` em `__main__.py:714-728`
**Severity:** WARNING

**Issue:** `avisar_o_grupo` e uma variavel de escopo de funcao atribuida dentro
de oito ramos e lida na linha 749. Os dois ramos novos (`JOIN`, `LEAVE`) NAO a
atribuem — hoje isso e inofensivo apenas porque eles produzem um
`RespostaDePresenca` e o `isinstance` da linha 746 curto-circuita antes da
leitura. Nao ha nada no codigo que preserve essa coincidencia: o primeiro ramo
futuro que devolver `str` sem setar a flag herda **em silencio** o valor do
comando ANTERIOR da mesma iteracao do laco, e o efeito e uma resposta privada
vazando para o grupo (ou o contrario). O proprio comentario acima do bloco diz
que um erro ali "muda o destino de todos ao mesmo tempo, em silencio".

**Fix:** inicializar por iteracao, imediatamente depois de `quem = ...`:

```python
# Default explicito, por iteracao: nenhum comando novo pode herdar o
# destino do comando anterior por esquecimento.
avisar_o_grupo = False
```

---

### WR-07: `.join`/`.leave` sem `conversation_id` publicam no grupo o texto do PRIVADO e descartam o do grupo

**File:** `l2scanner/__main__.py:779-784`
**Severity:** WARNING

**Issue:** No ramo `else` (sem conversa de origem) o codigo despacha
`resposta.privado` para o grupo. Para os oito comandos antigos isso e
indiferente (os dois textos sao o mesmo). Para presenca, e a escolha errada dos
dois: o grupo recebe *"Anotado. Voce esta na lista do Solo Boss das 22:00."* —
sem nick, inutil para quem le — e a redacao feita para o grupo (*"J4guar vai no
Solo Boss das 22:00."*) e **descartada**.

**Fix:** preferir a redacao de grupo quando o destino e o grupo.

```python
else:
    # Sem conversa de origem so ha um destino: o grupo. Entao mande a
    # redacao FEITA para o grupo, e caia no privado so quando nao houver.
    despachante.despachar(resposta.grupo or resposta.privado, Categoria.SEMPRE)
```

---

### WR-08: o bloco de fechamento esta duplicado literalmente entre `sessao.py` e `__main__.py`

**File:** `l2scanner/sessao.py:311-334` e `l2scanner/__main__.py:938-951`
**Severity:** WARNING

**Issue:** As duas copias fazem a mesma sequencia (`fechar_ocorrencias` ->
`nomes_dos_membros` -> `sugerir_a_vez` -> `texto_de_fechamento` -> `moldurar` ->
`despachar SEMPRE`), com ate os comentarios repetidos. Uma serve o laco
principal e a outra o `--so-agenda`, e as duas escrevem no MESMO estado duravel
(`.agenda/`) e no MESMO grupo. Qualquer conserto de CR-02, WR-09 ou da redacao
precisa ser aplicado duas vezes; aplicado uma so, os dois modos do scanner
passam a anunciar coisas diferentes sobre o mesmo boss — e essa divergencia so
aparece para quem roda os dois modos, que e exatamente o usuario deste projeto.

**Fix:** manter uma unica implementacao. `_fechar_listas_de_presenca` ja e
generica o bastante; `Sessao._processar_agenda` pode chamar a mesma funcao pura
"fecha e formata" e so ficar com o `resultado.presencas_fechadas` /
`resultado.avisos` / `self._despachar`:

```python
# presenca.py
def fechar_e_narrar(registro, eventos, agora, membros, loot=None):
    """Devolve [(Fechamento, texto)] — a UNICA implementacao desta sequencia."""
```

---

### WR-09: falha de disco no `fechar` faz a lista fechada ser reanunciada no grupo a cada tick

**File:** `l2scanner/agenda.py:485-491` (`marcar`) via `agenda.py:474` (`fechar`), consumido em `presenca.py:365-368`
**Severity:** WARNING

**Issue:** `marcar` devolve `True` em `OSError` ("preferir o duplicado ao
perdido"). Com a pasta `.agenda/` legivel mas NAO gravavel (permissao, disco
cheio, pasta em rede), `presentes()` continua devolvendo a lista, `fechar()`
levanta `PermissionError` a cada tick e devolve `True`, e `fechar_ocorrencias`
produz um `Fechamento` **em todo tick durante os 5 minutos de tolerancia**. A
1 Hz isso e ~300 mensagens de WhatsApp identicas no grupo, por ocorrencia — o
oposto exato da disciplina de volume que motivou D-12 e o
`avisar_no_horario = false`.

O caminho de `avisos_devidos` tem o mesmo formato, mas ali o dano e um aviso
repetido; aqui e uma lista de nomes repetida centenas de vezes.

**Fix:** limitar o "duplicado" a UM por processo quando o marcador nao pode ser
escrito — um `set` em memoria de chaves ja anunciadas nesta execucao e
suficiente e nao introduz estado duravel novo:

```python
def fechar(self, chave_da_ocorrencia: str) -> bool:
    chave = PREFIXO_FECHADO + chave_da_ocorrencia
    if chave in self._anunciados_nesta_execucao:
        return False
    ok = self.marcar(chave)
    if ok:
        self._anunciados_nesta_execucao.add(chave)
    return ok
```

---

### WR-10: o conteudo anunciado vem da leitura ANTERIOR ao marcador, e nao da leitura que ganhou a corrida

**File:** `l2scanner/presenca.py:363-372`
**Severity:** WARNING

**Issue:** A regra do projeto ("a decisao de despachar tem que ser o `marcar`,
nunca uma checagem anterior") esta respeitada para o SE anunciar. Mas o QUE se
anuncia vem de `presentes = registro.presentes(chave)` lido antes de
`registro.fechar(chave)`. Com as duas instancias do usuario sobre a mesma pasta,
um `.join` gravado entre essas duas linhas existe em disco e nao aparece na
mensagem que foi ao grupo — e nunca aparecera, porque o marcador ja foi
queimado. A janela e de microssegundos, mas o efeito e permanente e invisivel: a
pessoa esta na lista em disco e ausente da lista que a party leu.

**Fix:** reler depois de vencer, e usar a leitura vencedora:

```python
presentes = registro.presentes(chave)
if not presentes:
    continue
if not registro.fechar(chave):
    continue
# Reler DEPOIS de ganhar: quem anuncia tem que anunciar o estado que existe
# no instante em que o marcador foi criado, e nao o de antes dele.
presentes = registro.presentes(chave) or presentes
```

---

### WR-11: `nick_do_membro` roda duas vezes por mensagem, por dois caminhos independentes

**File:** `l2scanner/comandos.py:439` (dentro de `autorizado_para`) e `l2scanner/comandos.py:752` (campo `nick=`)
**Severity:** WARNING

**Issue:** Toda mensagem autorizada varre `membros` duas vezes: uma para decidir
se o remetente e membro, outra para descobrir o nick dele. Alem do trabalho
repetido, sao **dois pontos de decisao sobre a mesma pergunta** ("quem e este
telefone?"). A docstring de `nick_do_membro` argumenta, com razao, que duas
implementacoes do corte de 8 digitos divergiriam; duas CHAMADAS em pontos
diferentes tem o mesmo risco se um dia uma delas ganhar um filtro (por exemplo
"membro desativado") e a outra nao — o resultado seria uma mensagem autorizada
entrando na lista com `nick=None`, que hoje responde "nao sei que nick por na
lista" a alguem que esta corretamente configurado.

**Fix:** resolver o membro UMA vez, antes da trava, e derivar as duas respostas
do mesmo valor:

```python
membro = _membro_do_remetente(remetente, membros)   # None quando nao e membro
if not autorizado_para(comando, remetente, telefones or [], membro=membro):
    continue
achados.append(MensagemDeComando(..., nick=membro.nick if membro else None))
```

---

## Disposicao detalhada (2026-08-26)

### CR-01 — corrigido (`2ec5289`)

`_mesma_pessoa` suprime so por IGUALDADE canonica. Junto veio um conserto que a
prescricao nao pedia e que a recusa de arranque tornou necessario:
`_forma_canonica` passou a tirar tambem o codigo de pais, porque o proprio
review mediu o ruido no sentido oposto (`5544999998888` x `44999998888`, o mesmo
numero, reportado como colisao). Enquanto a colisao era so aviso, esse ruido
custava um warning; virando recusa de arranque, ele custaria o scanner de quem
escreveu o proprio numero das duas maneiras.

`colisoes_de_telefone` devolve `Colisao(primeiro, segundo, origem_do_primeiro,
origem_do_segundo)` com `escala_privilegio`, e `montar_leitor_de_comandos`
levanta `ConfiguracaoPerigosa` no par dono x membro — capturada em `main()` nos
dois lacos, entao o usuario ve uma mensagem e um exit 2, e nao um traceback.
Pares do mesmo nivel continuam so avisando. `_membro_de_dict` e a allowlist de
dono passaram a exigir `DIGITOS_FINAIS_DO_TELEFONE` digitos.

Testes: `TestOSufixoNaoProvaIdentidade` reproduz o probe do review na integra
(as duas metades: a colisao calada e a autorizacao que ela escondia), mais
`test_o_probe_do_review_derruba_o_arranque` pelo caminho real de
`montar_leitor_de_comandos`.

### CR-02 — corrigido (`c8c190e`)

Opcao (a) do review: a sugestao e CALADA quando este boss ja tem dono. A
deteccao le o DISCO (`loot.dono_do_loot`) em vez de olhar o retorno de
`consumir`, porque `consumir` devolve `None` quando a outra instancia venceu a
corrida do `pegou_` — e ela pode ter perdido a corrida do `fechado_`, entao
quem escreve a mensagem nao saberia do consumo. Cobre tambem o `.pegou` mandado
a mao. D-13 intocado: `responder_designacao` continua avisando e obedecendo.

### WR-01 — corrigido (`c8c190e`)

Docstring reescrita com a justificativa verdadeira (lista vazia nao queima o
marcador), com um paragrafo que registra por escrito que o cenario antigo era
falso. E a tolerancia foi dada, como o review condicionou — mas em
`ocorrencia_do_join`, funcao NOVA, e nao dentro de `ocorrencia_da_chamada`.
Razao: `responder_leave` usa a mesma funcao, e dar tolerancia la faria um
`.leave` as 20:01 apagar alguem da lista das 20:00, que ja fechou — violando
D-14 e brigando com o conserto do WR-02. O teste que o review pediu
(`fechar_ocorrencias` anuncia dentro da tolerancia) e
`test_o_join_de_200003_entra_na_lista_das_2000_e_e_ANUNCIADO`.

### WR-02 — corrigido (`c8c190e`)

Ordem invertida como prescrito. A garantia de D-14 nao dependia da recusa: ela
depende da CHAVE, e `registro.sair` opera sempre sobre a ocorrencia
estritamente futura. Ha um teste explicito de que a lista fechada continua
intocada depois de um `.leave` as 20:01.

### WR-03 — corrigido (`2ec5289`, `72d3290`)

Afirmacao condicionada ao estado que a sustenta, com `log.warning` no ramo
oposto nomeando `.corrigir` e `CHATWOOT_TELEFONES_COMANDO`. O `config.toml`
ganhou o mesmo aviso, porque ele repetia a promessa.

### WR-04 — corrigido (`2ec5289`)

`isinstance` na primeira linha de `_membro_de_dict`, com a mensagem citando o
bloco e mostrando a forma certa. `_evento_de_dict` NAO foi tocado: o proprio
review diz que nao pertence a esta fase, e mexer nele agora seria alargar o
escopo de um conserto de arranque sem teste de fase que o cubra.

### WR-05 — corrigido (`2ec5289`)

`_recusar_nicks_repetidos` compara pelo SLUG, e nao pelo texto: `Kaus` e `kaus`
sao dois blocos no TOML e um arquivo so em disco.

### WR-06 — corrigido (`615fe11`)

`avisar_o_grupo = False` no topo de cada volta. Provado por AST, e nao por
comportamento: nao ha entrada que produza o defeito HOJE, entao um teste de
comportamento passaria provando nada — o que se afirma e a propriedade que
impede o defeito de nascer.

### WR-07 — corrigido (`615fe11`)

`resposta.grupo or resposta.privado`, como prescrito. Continua saindo UMA
mensagem so, e ha teste para o caso em que nao ha redacao de grupo
(`.join` repetido).

### WR-08 — corrigido (`c8c190e`)

`presenca.fechar_e_narrar` e a unica implementacao. Nao foi opcional: sem ela,
o conserto do CR-02 precisaria ser aplicado duas vezes e `--so-agenda` e o laco
principal passariam a anunciar coisas diferentes sobre o mesmo boss. `presenca`
importar `loot.sugerir_a_vez` nao fecha ciclo — a direcao permitida e
`presenca -> loot -> agenda`, e os gates de AST continuam verdes. A docstring
de `texto_de_fechamento`, que afirmava o contrario, foi corrigida junto: ela
continua sendo formatador puro e quem decide agora e `fechar_e_narrar`.
`TestUmaImplementacaoSoDoFechamento` guarda a propriedade por AST nos dois
lados.

### WR-09 — corrigido (`12eb580`)

Teto por ocorrencia, em memoria, dentro do `RegistroEmDisco.fechar`. O teste
trava `os.open` e roda 300 ticks. A garantia entre as duas instancias continua
sendo o `O_CREAT|O_EXCL`, com teste proprio. O caminho de `avisos_devidos` NAO
foi tocado: o review mede o dano ali como "um aviso repetido", e mudar o
`marcar` generico afetaria os quatro namespaces da pasta.

### WR-10 — corrigido (`c8c190e`)

Releitura depois de vencer, com o `or presentes` do review. O teste injeta um
`.join` exatamente na janela entre a leitura e o marcador, e ha um segundo
teste para o `or` (releitura vazia nao pode apagar a lista que ia ser
anunciada).

### WR-11 — corrigido (`2e8bac0`)

`membro_do_remetente` vira o unico lugar que responde "quem e este telefone?";
`nick_do_membro` e casca fina sobre ela; `autorizado_para` aceita a resposta ja
resolvida por palavra-chave, com SENTINELA — um `None` default colapsaria
"procurei e nao era membro" com "nao resolvi" e faria a trava recusar todo
party-mate em silencio. Ha um teste que simula o filtro futuro que o review
descreve e afirma que as duas respostas mudam JUNTAS.

## Testes que mudaram, e por que nao e enfraquecimento

Tres testes existentes foram reescritos. Nenhum perdeu forca; dois ganharam.

1. **`test_a_colisao_dono_contra_membro_GRITA_nomeando_os_dois`** ->
   `test_a_colisao_dono_contra_membro_RECUSA_A_SUBIR`. Ele afirmava
   `leitor is not None` justificando com "entre dois MEMBROS ela nao escala
   privilegio nenhum" — a justificativa esta certa e o CASO estava errado: o par
   usado era dono x membro, exatamente o que escala. O caso que a justificativa
   descreve virou teste proprio
   (`test_a_colisao_entre_dois_MEMBROS_avisa_e_deixa_subir`), entao a cobertura
   aumentou de um caso para dois.
2. **`test_o_consumo_do_boss_ANTERIOR_ja_conta_na_sugestao`** (test_sessao).
   Ele designava para o boss das 10:00 e afirmava a sugestao contraditoria — era
   o CR-02 escrito como acerto, e o proprio review aponta isso. Virou dois
   testes: um que afirma o silencio quando ESTE boss ja tem dono, e outro que
   mantem o nome e a propriedade original (a ordem consumo-antes-de-fechamento
   importa) usando o boss ANTERIOR, que e o que o nome sempre disse.
3. **`test_quem_entrou_na_lista_das_2200_sai_dela_as_2001`** ->
   `test_quem_entrou_na_lista_das_2200_sai_dela`. O `.join` era as 20:01, que
   passou a estar DENTRO da tolerancia nova (WR-01) e portanto fala do boss das
   20:00. O horario foi movido para 20:06 e a propriedade testada e identica; o
   comportamento das 20:01 ganhou cobertura nova em `TestOJoinAtrasadoPelaPonte`
   e `TestOLeaveNaoFicaQuebradoCincoMinutosPorBoss`.

Os tripwires citados como intocaveis continuam verdes e nao foram editados: o
`_AJUDA` (`test_toda_sintaxe_anunciada_volta_como_o_comando_certo`,
`test_a_tabela_cobre_todo_comando_ANTIGO_do_enum`), os volumes de 36/dia e
72/dois-dias, os gates de AST de `datetime.now()` nos tres modulos e o de
direcao de importacao.

---

_Reviewed: 2026-08-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
_Fixed: 2026-08-26 — Claude (gsd-code-fixer). 13/13 corrigidos, 0 recusados._
