# Code Review — Fases 5, 6 e 7 (revisão completa do código novo)

**Data:** 2026-08-24
**Escopo:** `l2scanner/agenda.py`, `l2scanner/cliente.py`, e as mudanças em
`notificador.py`, `rastreador.py`, `visao.py`, `captura_janela.py`, `__main__.py`
**Profundidade:** deep — análise entre arquivos, com medição
**Baseline:** 338 testes verdes, ruff em 23 erros pré-existentes
**Status:** todos os 5 achados CORRIGIDOS e travados com teste — 344 testes

## Resumo

| Severidade | Quantidade |
|---|---|
| Crítico | 0 |
| Warning | 3 |
| Info | 2 |

Nenhum problema de correção nos algoritmos puros — a agenda, o silêncio e a
identificação do cliente estão certos e bem cobertos. Os três warnings são
todos de **integração**: coisas que os testes unitários não alcançam porque
vivem no laço principal.

---

## W-01 — O template do diálogo varre a janela inteira: 121 ms por frame

**Arquivo:** `l2scanner/cliente.py:130` (`casar_dialogo`)
**Severidade:** Warning

`casar_dialogo` roda `cv2.matchTemplate` do template 320×62 contra o frame
completo de 1720×1392, **a cada tick**, mesmo quando o cliente está claramente
em jogo.

**Medido:**

```
matchTemplate do dialogo: 121.2 ms por frame
a 1 Hz isso e 12.1% do orcamento de um tick
```

12% de CPU contínuo numa máquina que também roda **dois clientes de Lineage 2**
não é gratuito. E é desperdício puro: o diálogo de desconexão é **modal e
centrado** — medido, o centro do template cai em x=860 numa janela de 1720, ou
seja, exatamente no centro.

**Correção:** restringir a busca à faixa central. Frações, não pixels, para
sobreviver a mudança de resolução.

**Risco da correção:** se o cliente algum dia desenhar o diálogo fora do centro,
a detecção falha. Aceito: o comportamento modal-centrado é como a UI do jogo
funciona, e a alternativa é pagar 12% de CPU para sempre por um evento que
acontece uma vez por manutenção.

---

## W-02 — A agenda é pulada quando a extração de frame falha

**Arquivo:** `l2scanner/__main__.py` (laço principal)
**Severidade:** Warning

O bloco da agenda fica **depois** do `try: extrair(frame, cal)`. Quando a
extração lança, o `except` faz `continue` — e o tick inteiro é perdido,
inclusive os avisos de TvT e Prime.

Isso contradiz o princípio que justifica a fase inteira: **o aviso vem do
relógio, não da tela**. Não faz sentido um erro de leitura de pixel calar um
lembrete que não depende de pixel nenhum.

**Correção:** mover o bloco da agenda para antes do `try` da extração,
computando o instante logo após a captura.

---

## W-03 — No modo `--so-agenda`, o encerramento não é logado sem despachante

**Arquivo:** `l2scanner/__main__.py` (`laco_da_agenda`)
**Severidade:** Warning

```python
if encerrou and despachante:      # <-- o `and despachante` cala o console também
    log.info(destacar(encerrou))
    despachante.despachar(encerrou, Categoria.SEMPRE)
```

O laço principal faz certo (loga sempre, despacha se houver despachante). Aqui,
quem roda sem `.env` e sem `--dry-run` perde a mensagem **até no console**.

É a mesma classe de erro que o projeto vem combatendo o dia inteiro: silêncio
que não deveria existir.

---

## I-01 — O contador de silenciados nunca chega ao usuário

**Arquivo:** `l2scanner/notificador.py` + resumo de sessão
**Severidade:** Info

`Despachante.silenciados` conta o que foi engolido, e nada o exibe. Depois de um
TvT, o usuário não tem como saber se o silêncio engoliu 3 eventos ou 300 — e
essa diferença é exatamente o sinal de que o silêncio está fazendo o trabalho
dele.

**Correção:** incluir no resumo de fim de sessão, junto de entregues e falhados.

---

## I-02 — Ordem de import fora do padrão

**Arquivo:** `l2scanner/notificador.py`
**Severidade:** Info

`from enum import Enum` entrou depois de `from pathlib import Path`. O ruff não
reclama porque a regra de ordenação não está ligada, mas destoa do resto do
arquivo.

---

## O que foi verificado e está correto

- **A união de janelas de silêncio.** Varredura minuto a minuto de uma segunda
  inteira bate exatamente com o esperado, incluindo o 20:00+125min = 22:05.
- **O registro atômico.** 16 threads competindo produzem exatamente um envio. A
  escolha de `O_CREAT | O_EXCL` elimina a janela de corrida que um
  "lê-checa-escreve" teria.
- **A disciplina de tempo.** Depois da correção de `9bf763f`, a agenda usa o
  mesmo instante do rastreador, então o replay reproduz o silêncio gravado.
- **O começo frio**, nas quatro máquinas de estado novas (entrada, você-em-party,
  cliente caído, silêncio). Todas distinguem "mudou" de "foi assim que encontrei".
- **A fronteira de somente-leitura.** Um teste afirma que a mensagem de
  encerramento não promete convidar ninguém.
- **`config.toml` ausente não quebra** quem nunca usou a agenda.


---

## Correções aplicadas — 2026-08-24

| Achado | Resultado |
|---|---|
| W-01 busca do diálogo | **121,2 ms → 45,5 ms** por frame (2,7×). Score do positivo real intacto |
| W-02 agenda depois da extração | Movida para antes do `try`. Erro de pixel não cala mais o lembrete |
| W-03 encerramento não logado | Loga sempre, despacha se houver para onde |
| I-01 silenciados invisíveis | Entrou no resumo de fim de sessão |
| I-02 ordem de import | Corrigida |

**6 testes de regressão** adicionados. Três deles leem a fonte do laço — é a
única forma de afirmar *ordem de execução* sem subir o scanner com um jogo
aberto, e ordem de execução é exatamente o que um refactor desfaz sem perceber.

### O padrão por trás dos três warnings

Nenhum estava nos algoritmos. A agenda, o silêncio e a identificação do cliente
estão corretos e bem cobertos por teste unitário. **Os três viviam na costura
com o laço principal** — ordem de execução, uma condição a mais num `if`, um
contador que ninguém lê.

É o mesmo lugar onde os bugs de hoje de manhã moravam. Vale como sinal: neste
projeto, a lógica pura está sólida e o risco mora na integração.

---

## Segunda passada — cobertura e caminho quente (2026-08-24, após as correções)

### A cobertura confirma o achado da revisão, de forma independente

| Camada | Cobertura |
|---|---|
| `rastreador.py` | 98% |
| `visao.py` / `agenda.py` / `identidade.py` | 94–95% |
| **`__main__.py`** | **20%** |
| **`captura_janela.py`** | **19%** |

Os **3 de 3 warnings** desta revisão moravam em `__main__.py`. A revisão chegou
nisso lendo código; a cobertura chega no mesmo lugar por medição. Duas fontes
independentes apontando o mesmo risco: **a lógica pura está sólida e o perigo
mora na integração.**

### O caminho quente era 98% um só `matchTemplate`

| Operação | Custo |
|---|---|
| `extrair()` — toda a análise da party window | **0,7 ms** |
| `matchTemplate` do diálogo (após W-01) | **47 ms** |

O scanner gastava ~98% do CPU procurando, a 1 Hz, um evento que acontece uma vez
por manutenção.

**Correção:** cadência. Um diálogo de desconexão não pisca — aparece e fica até
alguém clicar. Conferir a cada 5 s detecta a mesma coisa: **47 ms/s → 9,4 ms/s**,
e o tick inteiro passa a custar 1% do orçamento. O título continua sendo lido a
cada tick, porque custa microssegundos e a tela de login não pode esperar.

O veredito de desconexão **gruda** entre buscas. Sem isso o estado oscilaria a
cada tick, as confirmações nunca chegariam a duas seguidas, e o alerta
simplesmente não sairia.

### A lógica saiu da camada intestável

A cadência foi implementada em `captura_janela.py` (19%) e **movida** para
`cliente.py` (85%) antes de ser considerada pronta. Lógica que *decide* alguma
coisa não pode viver onde só um jogo aberto consegue exercitá-la — que é
exatamente a condição que deixou os três warnings passarem.

Resultado: `cliente.py` 81% → 85%, com 7 testes cobrindo a cadência, o veredito
grudento e o título continuando fresco.

### Código morto removido

`RegistroEmMemoria` (28 linhas) ficou órfão quando a Tarefa 3 da Fase 6 o
substituiu por `RegistroEmDisco`. Nada o referenciava.
