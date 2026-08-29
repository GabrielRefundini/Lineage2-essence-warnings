---
phase: 01-funda-o-firewall-gravador-e-spike-de-campo
workstream: mercado
verified: 2026-08-29T01:17:44Z
status: gaps_found
score: 4/5 must-haves verificados
behavior_unverified: 0
overrides_applied: 0
suite: "1558 passed, 2 skipped (Python GLOBAL, medido pelo verificador)"
gaps:
  - truth: "O usuario roda a ferramenta de calibracao sobre um frame gravado e ve as regioes da janela, a ancora do painel e os templates de digito persistidos em calibration.json — sem editar JSON a mao"
    status: partial
    reason: >-
      Duas das tres coisas que o criterio 3 enumera estao persistidas e medidas
      (regioes da janela via mercado_grade, ancora do painel via mercado_ancoras
      com 3 ancoras). A TERCEIRA — os templates de digito — nao existe no disco E
      nao existe como capacidade: `l2scanner/calibrar_mercado.py` nao tem uma
      unica ocorrencia de "digito" / "glifo" / "algarismo". A chave
      `mercado_templates_de_digito` e apenas um campo de passagem em
      `calibracao.py` (declarado, serializado, desserializado) sem NENHUM
      produtor em todo o repositorio. O 01-04-SUMMARY lista a chave entre as
      "5 chaves opcionais novas", o que da a entender que ela e produzida.
    artifacts:
      - path: "l2scanner/calibrar_mercado.py"
        issue: "Zero codigo de corte de template de digito. `grep -in 'digito|glifo|algarismo'` devolve nada em 43.527 bytes."
      - path: "calibration.json"
        issue: "`mercado_templates_de_digito: null`. Nunca foi escrito porque nada o escreve."
      - path: "01-04-PLAN.md:308"
        issue: >-
          O portao de verificacao do proprio plano exigia que
          `mercado_templates_de_nome` E `mercado_templates_de_digito` estivessem
          "presentes e nao vazias". Nenhuma das duas esta, e so a primeira foi
          reconhecida no SUMMARY.
    missing:
      - "Modo de corte de templates de digito (0-9 + separadores) em calibrar_mercado.py, com conferencia visual, no mesmo trilho dos moldes de nome"
      - "OU: mover explicitamente o corte de digitos para a Fase 2 no ROADMAP.md e aceitar um override aqui — o produtor hoje esta orfao, nao adiado"
      - "Corrigir a linha 17 do 01-04-SUMMARY.md, que conta mercado_templates_de_digito como entregue"
deferred:
  - truth: "Os moldes de nome da watchlist cortados pela ferramenta (metade de D-05/D-06)"
    addressed_in: "Fase 2"
    evidence: >-
      Adiamento REGISTRADO em dois lugares independentes e honestos:
      `calibrar_mercado.py:595` ("da para calibrar as ancoras e a grade sem
      watchlist nenhuma, e a Fase 2 e que vai precisar dos moldes de nome") e
      01-04-SUMMARY.md ("O que NAO ficou, e por que"). A Fase 2 consome via
      LEIT-01 ("Itens da watchlist reconhecidos ... por template de conjunto
      fechado"). A CAPACIDADE existe e avisa alto quando nao corta nada; o que
      falta e a entrada — `[mercado] watchlist` segue comentada em
      config.toml:149-154. Ao contrario dos digitos, aqui nada esta orfao.
human_verification:
  - test: >-
      Rodar `.\calibrar-mercado.bat --gravacao recordings\20260828-063752-mercado-aberto`
      e desenhar as cinco regioes COM O MOUSE, ate ver
      "Calibracao de mercado gravada em calibration.json".
    expected: >-
      As janelas de selecao abrem no tamanho da imagem (nao reescaladas), o ENTER
      do navegador de frames nao vaza para o selectROI seguinte, e cada arrasto
      devolve uma caixa nao-vazia.
    why_human: >-
      Nenhuma mao humana jamais completou este fluxo. As tres tentativas do
      usuario abortaram num defeito real (ENTER vazando, resolvido em 03b3e26) e
      depois ele delegou; as regioes atuais foram MEDIDAS por um agente, nunca
      desenhadas. O defeito CR-01 (janela de selecao em escala errada, que
      corromperia qualquer retangulo desenhado a mao) esta corrigido e coberto
      por teste, mas corrigido-e-testado nao e o mesmo que exercitado por um
      humano — e esta e exatamente a metade do criterio 3 que grep nao alcanca.
  - test: >-
      Recalibrar depois de descomentar `[mercado] watchlist` em config.toml e
      conferir que os moldes de nome aparecem em calibration.json e que a matriz
      de confusao roda de verdade.
    expected: >-
      `mercado_templates_de_nome` deixa de ser `[]`, e
      `mercado_limiar_de_template` deixa de ser o 0.5 sem significado.
    why_human: "Exige a watchlist real do usuario — so ele sabe quais itens quer precar."
decision_coverage:
  honored: 9
  total: 10
  not_honored:
    - "D-06 (parcial): 'templates cortados pela ferramenta com conferencia visual e matriz de confusao' vale para os moldes de NOME; para os de DIGITO nao ha ferramenta"
---

# Fase 1: Fundação — firewall, gravador e spike de campo — Relatório de Verificação

**Objetivo da fase:** O usuário consegue produzir evidência de campo confiável do World Exchange, e dessa evidência saem a calibração, os templates e a detecção do painel — o sinal único que também protege o detector de morte.

**Verificado:** 2026-08-29T01:17:44Z
**Status:** `gaps_found` — 1 lacuna bloqueante
**Re-verificação:** Não — verificação inicial

---

## Veredito em uma frase

Quatro dos cinco critérios do ROADMAP estão verificados, e três deles com evidência empírica que eu mesmo produzi (não com base no SUMMARY). O critério 3 falha numa metade concreta e observável: **os templates de dígito, que o critério nomeia explicitamente, não existem no disco e não existem como capacidade** — a ferramenta de calibração não tem uma linha de código que os corte.

---

## Verdades Observáveis (os 5 critérios de sucesso do ROADMAP)

| # | Verdade | Status | Evidência |
|---|---------|--------|-----------|
| 1 | `--record` com contador batendo com o disco; `imwrite` que falha vira erro alto, nunca frame contado | ✓ VERIFICADO | `gravador.py` põe as TRÊS saídas (contador, JSONL, resumo) atrás de `bool(cv2.imwrite(...))`; PNG órfão é apagado quando o índice recusa a linha; `_contabilizar_falha` grita na 1ª e a cada 10. `alarme_de_divergencia` (`__main__.py:269`) COMPARA os dois números e sobe o bloco para `ERROR`. 23 testes comportamentais exercitam os caminhos de falha reais. **Evidência de campo:** o portão do spike aprovou 8 sessões reais com JSONL == PNGs e zero falhas de escrita. |
| 2 | Sessões reais gravadas e perguntas de campo respondidas por escrito, incl. variantes de encanto | ✓ VERIFICADO | 8 pastas em `recordings/` com os rótulos fixos do roteiro; `tools/conferir_gravacoes_do_spike.py` → **APROVADO**, todas em 1720x1392 (dimensão da JANELA, não do recorte da party). `tools/conferir_spike_respostas.py` → **APROVADO**, 43 caminhos de frame resolvidos no disco. As 7 perguntas exigidas pelo critério estão em §1-§5 e §7, todas **VERIFICADO**; a única **NAO RESPONDIDO** (§6, idade do anúncio) não é exigida pelo critério — e é a prova de que a falha honesta funciona. Validação do usuário registrada em 5 seções datadas (D-04 cumprido). |
| 3 | Ferramenta de calibração sobre frame gravado, persistindo regiões/âncora/**templates de dígito** em `calibration.json` | ✗ **FALHOU** | Regiões ✓ (`mercado_grade`: 10 linhas de 45 px, dx/dy relativo). Âncora ✓ (`mercado_ancoras`: 3 âncoras com molde). Sem editar JSON à mão ✓ (regrava o arquivo inteiro). **Templates de dígito ✗**: `mercado_templates_de_digito: null` e `calibrar_mercado.py` não contém "digito"/"glifo"/"algarismo" em lugar nenhum. Ver Lacuna G-01. |
| 4 | No replay do 27x: painel reconhecido **E** ZERO alertas de morte — um sinal, dois consumidores | ✓ VERIFICADO | `test_a_sequencia_do_27x_COM_o_mercado_ligado_segue_em_ZERO_eventos` prende **as duas metades no mesmo laço**: 40 ticks com o painel aberto por cima da barra, `assert all(v is True for v in vistas)` **e** `assert eventos == []`. Roda sobre fixtures COMMITADAS (`tests/fixtures/mercado/`, 36 arquivos), não sobre `recordings/` — 22 testes, 0 skips. |
| 5 | Adicionar biblioteca de síntese de input deixa o teste de firewall vermelho | ✓ VERIFICADO **empiricamente** | Eu mesmo executei: `pip install keyboard` no `.venv` → `test_o_venv_de_producao_nao_tem_biblioteca_de_input` **FALHOU** com a mensagem completa citando a constraint fundadora; `pip uninstall -y keyboard` → **18 passed**. Ambiente restaurado e conferido (`pip list` sem `keyboard`). |

**Score: 4/5 verdades verificadas** (0 present-behavior-unverified)

---

## Itens Adiados (não são lacunas acionáveis)

| # | Item | Endereçado em | Evidência |
|---|------|---------------|-----------|
| 1 | Moldes de nome da watchlist cortados pela ferramenta | Fase 2 | Adiamento registrado no próprio código (`calibrar_mercado.py:595`) e no SUMMARY; consumido pela LEIT-01. A capacidade EXISTE e avisa alto quando não corta nada — falta a entrada (`[mercado] watchlist` comentada em `config.toml:149-154`). |
| 2 | Consumidores do sinal "mercado aberto" (laço `--mercado` e oclusão do detector de morte) | Fase 4 (junto de DETC-02) | Reconciliação `<detc01_reconciliation>` **presente e completa** em `01-04-PLAN.md:118-151`, com tabela metade-a-metade, e reproduzida como "Nota de escopo de DETC-01" no `ROADMAP.md:62`. Não aceitei o adiamento em silêncio: o registro existe nos dois lugares. |

---

## Artefatos Exigidos

| Artefato | Existe | Substantivo | Ligado | Dados fluem | Status |
|----------|--------|-------------|--------|-------------|--------|
| `l2scanner/gravador.py` | ✓ | ✓ 11 KB, `falhas_de_gravacao` | ✓ `__main__.py:241,244` | ✓ disco real | ✓ VERIFICADO |
| `tests/test_firewall_escopo.py` | ✓ | ✓ 3 varreduras + teste-do-teste + prova de mecanismo | ✓ suíte normal | ✓ | ✓ VERIFICADO |
| `tests/test_gravador_honesto.py` | ✓ | ✓ 23 testes | ✓ | ✓ | ✓ VERIFICADO |
| `l2scanner/mercado_visao.py` | ✓ | ✓ 27 KB, limiar MEDIDO e REMEDIDO | ✓ `__main__.py:373` | ✓ fixtures reais | ✓ VERIFICADO |
| `ROTEIRO-SPIKE.md` | ✓ | ✓ 8 cenários rotulados | ✓ rótulos = pastas reais | ✓ | ✓ VERIFICADO |
| `tools/conferir_gravacoes_do_spike.py` | ✓ | ✓ | ✓ executado: APROVADO | ✓ | ✓ VERIFICADO |
| `SPIKE-RESPOSTAS.md` | ✓ | ✓ 9 seções seladas | ✓ 43 frames resolvidos | ✓ | ✓ VERIFICADO |
| `tools/conferir_spike_respostas.py` | ✓ | ✓ | ✓ executado: APROVADO | ✓ | ✓ VERIFICADO |
| `l2scanner/calibrar_mercado.py` | ✓ | ✓ 43 KB, matriz de confusão | ✓ `.bat` + `_selecionar_regiao` compartilhado | ⚠️ **parcial** | ⚠️ **INCOMPLETO** — sem corte de dígitos |
| `calibrar-mercado.bat` | ✓ | ✓ | ✓ `-m l2scanner.calibrar_mercado` | ✓ | ✓ VERIFICADO |
| `tests/test_mercado_27x.py` | ✓ | ✓ 22 testes, duas metades | ✓ fixtures commitadas | ✓ | ✓ VERIFICADO |
| `l2scanner/visao.py` (`mercado_aberto_aparente`) | ✓ | ✓ campo + 34 linhas de razão | ✓ `sessao.py:263` | ✓ | ✓ VERIFICADO |
| `calibration.json` (chaves de mercado) | ✓ | ⚠️ 2 de 4 chaves de conteúdo preenchidas | ✓ | ⚠️ | ⚠️ **PARCIAL** |

---

## Ligações-Chave (wiring)

| De | Para | Via | Status |
|----|------|-----|--------|
| `__main__.py` | `gravador.py` | `fonte_completa=fonte.completo_do_frame_atual` (`:241`) | ✓ LIGADO |
| `gravador.py` | disco | `bool(cv2.imwrite(...))` guardando as 3 saídas | ✓ LIGADO |
| `test_firewall_escopo.py` | `.venv/Lib/site-packages` | `md.distributions(path=[...])` | ✓ LIGADO — **provado por instalação real** |
| `calibracao.py` | `calibration.json` | `dados.get('mercado_ancoras')`, `VERSAO_DO_ESQUEMA` segue 2 | ✓ LIGADO |
| `calibrar_mercado.py` | `calibrar.py` | `from .calibrar import _gravar_conferencia, _selecionar_regiao` (`:63-67`) | ✓ LIGADO — não duplicado |
| `__main__.py` | `mercado_visao.py` | `montar_vigia_do_mercado` → `RastreioDoPainel` (`:355-382`) | ✓ LIGADO |
| `sessao.py` | `visao.Observacao` | `replace(observacao, mercado_aberto_aparente=...)` **depois** de `rastreador.observar` (`:250-264`) | ✓ LIGADO |
| `visao.Observacao` | console | `__main__.py:576` — **única consumidora do campo no projeto** | ✓ LIGADO |
| `test_mercado_27x.py` | `rastreador.py` | tripwire de arquitetura: o fonte NÃO cita mercado | ✓ LIGADO |

### Rastreamento de fluxo de dados (Nível 4)

`calibration.json` → `montar_vigia_do_mercado` → `RastreioDoPainel.observar` → `sessao._olhar_o_mercado` → `Observacao.mercado_aberto_aparente` → linha do console. **FLUINDO** com dados reais (fixtures do 27x, casamento 0.9999/0.9996). Nenhum valor estático, nenhum mock no caminho de produção.

---

## Execução de Portões (probes)

| Portão | Comando | Resultado | Status |
|--------|---------|-----------|--------|
| Gravações do spike | `python tools/conferir_gravacoes_do_spike.py` | `APROVADO — as 8 gravacoes do spike servem` (exit 0) | ✓ PASS |
| Respostas do spike | `python tools/conferir_spike_respostas.py` | `APROVADO -- as 9 respostas do spike se sustentam` (exit 0) | ✓ PASS |
| Suíte completa | `python -m pytest tests/ -q` | `1558 passed, 2 skipped in 30.99s` | ✓ PASS |
| Testes da fase | 13 arquivos de teste da fase | `336 passed in 5.64s`, 0 skips | ✓ PASS |
| **Firewall vermelho** | `pip install keyboard` + pytest | **1 failed, 17 passed** → depois do uninstall: **18 passed** | ✓ PASS |

Os 2 skips da suíte são `pytest.skip` condicionais e explicados sobre `recordings/` (gitignored) — o padrão da casa. Os testes permanentes rodam sobre fixtures commitadas.

---

## Proibições (verificação negativa)

| Proibição | Status | Evidência |
|-----------|--------|-----------|
| `rastreador.py` NÃO pode ler o sinal de mercado | ✓ **VERIFICADO** | `grep -in "mercado" l2scanner/rastreador.py` → **zero ocorrências**. Reforçado por 2 tripwires de arquitetura em `test_mercado_27x.py:254,262`. A segurança vem da leitura NÃO EXISTIR, não de um guard. |
| NÃO estender o gate de brilho da barra própria (`barra_propria_legivel`, `_moldura_da_barra_propria`, `_bordas_da_barra_intactas`) | ✓ **VERIFICADO** | Único commit da fase que toca `visao.py` é `f54ba5c`: **34 inserções, 0 remoções**, todas comentário + o campo do dataclass. As três funções estão intocadas. |
| NÃO chutar o limiar da âncora | ✓ VERIFICADO | `mercado_visao.py:140-171`: pior positivo / melhor negativo / margem escritos, MEDIDOS no 27x e REMEDIDOS em campo contra 91 frames fechados adversariais. |
| NÃO subir `VERSAO_DO_ESQUEMA` | ✓ VERIFICADO | `calibracao.py:23` → `2`; `calibration.json` → `versao: 2`. |
| NÃO escrever imagem em `calibrar_mercado.py` | ✓ VERIFICADO | `grep -c imwrite` → **0**; importa `_gravar_conferencia`. |
| NÃO duplicar a mecânica de `selectROI` | ✓ VERIFICADO | `_selecionar_regiao` extraído e importado, não copiado. |
| NÃO deixar falha de gravação derrubar os alertas | ✓ VERIFICADO | `test_gravar_nunca_levanta_nem_quando_o_imwrite_explode`, `test_o_indice_que_recusa_a_linha_nao_derruba_o_scanner`. |
| NÃO cair no recorte da party quando a janela não produzir frame | ✓ VERIFICADO | `gravador.py` `_contabilizar_falha` + `return False`; `test_a_janela_sem_frame_falha_fechada_em_vez_de_gravar_o_recorte`. |
| NÃO aceitar frame citado que não existe no disco | ✓ VERIFICADO | Portão executado: 43 caminhos resolvidos. |
| NÃO permitir biblioteca de síntese de input | ✓ VERIFICADO **empiricamente** | Ver critério 5. |

**Nenhuma proibição foi violada.** As duas mais caras — as que o prompt destacou — estão limpas com evidência direta.

---

## Cobertura de Requisitos

| Requisito | Plano | Descrição | Status | Evidência |
|-----------|-------|-----------|--------|-----------|
| **FIRE-01** | 01-01 | Build quebra se lib de síntese de input entrar na árvore | ✓ SATISFEITO | Provado empiricamente com `keyboard`; 3 varreduras + teste-do-teste; 9 nomes na banlist |
| **FUND-01** | 01-01 | Gravador só conta frames confirmados no disco | ✓ SATISFEITO | Código + 23 testes + 8 sessões de campo sem divergência |
| **FUND-02** | 01-01/02/03 | Sessões gravadas + perguntas de campo respondidas | ✓ SATISFEITO | 8 sessões aprovadas; 9 respostas seladas; validadas pelo usuário |
| **FUND-03** | 01-04 | Calibração do mercado (**regiões, âncora, templates de dígito**) persiste via ferramenta própria | ✗ **BLOQUEADO** | Regiões ✓, âncora ✓, **templates de dígito ausentes e sem produtor** — ver G-01 |
| **DETC-01** | 01-02/04 | "World Exchange aberto" por âncora positiva, sinal compartilhado | ✓ SATISFEITO **no escopo reconciliado** | Sinal medido + superfície exibicional; reconciliação registrada em PLAN e ROADMAP; consumidores na Fase 4 por desenho |

**Requisitos órfãos:** nenhum. Os 5 IDs do ROADMAP aparecem no frontmatter dos planos e todos foram avaliados.

---

## Anti-Padrões

| Categoria | Resultado |
|-----------|-----------|
| Marcadores de dívida (`TBD`/`FIXME`/`XXX`) | **ZERO** nos 18 arquivos da fase |
| `TODO`/`HACK`/`PLACEHOLDER` | 6 ocorrências, **todas falso-positivo** — é a palavra portuguesa "TODO" (= "cada/todo"), como em "TODO recorte vira 'mercado aberto'" |
| Retornos vazios / stubs | Nenhum no caminho de produção |
| Testes desabilitados sobre requisito | Nenhum. Os 2 skips são condicionais, explicados, e cobertos por fixtures commitadas equivalentes |
| Testes circulares | Nenhum. Os valores esperados vêm de frames reais do jogo (fonte externa), não de saída do próprio sistema |
| Força de asserção | Nível **comportamental** nos testes críticos (27x: 40 ticks através de `sessao.tick`; gravador: caminhos de falha reais) |

---

## Cobertura de Decisões (D-01 … D-10)

**9 de 10 honradas.** D-01 (roteiro), D-02 (8 cenários), D-03 (uma sessão por cenário), D-04 (validação do usuário), D-05 (variantes `+N`), D-07 (chaves opcionais, esquema 2), D-08 (firewall), D-09 (imwrite), D-10 (âncora própria, gate intocado) — todas verificadas acima.

**D-06 parcialmente honrada:** "templates cortados pela própria ferramenta, com conferência visual e matriz de confusão" vale para os moldes de **nome** (capacidade completa, matriz de confusão medida, recusa alta em colisão — `test_dois_moldes_QUASE_IDENTICOS_sao_RECUSADOS_com_o_par_nomeado`). Para os moldes de **dígito** não há ferramenta nenhuma.

---

## Lacunas

### G-01 (🛑 BLOCKER) — Os templates de dígito não existem, e não estão adiados: estão órfãos

O objetivo da fase diz que da evidência saem "a calibração, **os templates** e a detecção do painel". O critério 3 é ainda mais específico e nomeia "os templates de dígito".

**O que eu encontrei:**

```
mercado_grade                : preenchido  (10 linhas de 45 px, dx/dy)      OK
mercado_ancoras              : 3 ancoras com molde                          OK
mercado_templates_de_nome    : []                                           adiado p/ Fase 2
mercado_templates_de_digito  : None                                         ORFAO
mercado_limiar_de_template   : 0.5   <- de uma matriz de confusao VAZIA
```

`grep -in "digito|glifo|algarismo" l2scanner/calibrar_mercado.py` devolve **nada**. A chave só aparece em `calibracao.py` como campo de passagem (`:288` declara, `:402` serializa, `:495` desserializa) — declarada, nunca produzida.

**Por que isto não é o mesmo caso dos moldes de nome.** Os moldes de nome têm um adiamento *registrado em dois lugares* e um consumidor nomeado na Fase 2 (LEIT-01); a capacidade existe e avisa alto quando não corta nada; só falta a entrada do usuário. Os templates de dígito não têm nada disso: nenhum SUMMARY, REVIEW ou PLAN reconhece a ausência, e os critérios da Fase 2 descrevem **ler** dígitos (LEIT-02), nunca **cortá-los**. Apliquei o filtro de adiamento do Step 9b de forma conservadora e não achei evidência específica em fase posterior — o produtor está hoje sem dono.

**Agravante de auditoria:** `01-04-SUMMARY.md:17` lista `mercado_templates_de_digito` entre as "5 chaves opcionais novas em calibration.json", e a seção "O que NÃO ficou, e por que" reconhece honestamente os moldes de nome e o limiar 0.5 — mas **não menciona os dígitos**. Um leitor do SUMMARY concluiria que a chave é produzida.

**Fechamento (escolher um):**
1. Acrescentar o modo de corte de dígitos (0-9 + separadores) a `calibrar_mercado.py`, no mesmo trilho dos moldes de nome; **ou**
2. Mover explicitamente o corte de dígitos para a Fase 2 no `ROADMAP.md`, ajustar o critério 3 da Fase 1, e registrar um override aqui.

Se a opção 2 for a escolhida, o override cabível é:

```yaml
overrides:
  - must_have: "templates de digito persistidos em calibration.json pela ferramenta de calibracao"
    reason: "Corte de glifos movido para a Fase 2, junto do consumidor LEIT-02 que os le — cortar digitos sem o leitor que os valida repetiria o erro de calibrar contra nada"
    accepted_by: "<usuario>"
    accepted_at: "<ISO timestamp>"
```

### ⚠️ WARNING-01 — `calibration.json` no disco carrega dano residual de CR-03/CR-04

O código está corrigido (a guarda `if moldes_de_nome:` impede apagar moldes anteriores; o limiar só é escrito quando `limiar_sugerido is not None`), mas o **arquivo no disco ainda está no estado velho**: `mercado_templates_de_nome: []`, `mercado_limiar_de_template: 0.5` (de uma matriz vazia, sem significado), e a chave singular antiga `mercado_ancora` convive com a nova `mercado_ancoras`.

**Impacto real: baixo.** Confirmei que a produção lê **apenas** `mercado_ancoras` (`__main__.py:355,373`) — a chave singular é vestigial e inerte. O `0.5` só passa a valer quando houver moldes. Nenhum caminho de produção lê hoje o dano. Fecha sozinho na próxima recalibração com watchlist.

### ⚠️ WARNING-02 — Bookkeeping do ROADMAP desatualizado

`ROADMAP.md:48-60` marca só `01-01-PLAN.md` como `[x]` e diz "**Plans**: 1/4 plans executed", mas os quatro SUMMARYs existem e os quatro planos foram executados. A tabela de Progress diz "1/4 — In Progress". Sem impacto funcional; corrigir ao fechar a fase.

---

## Verificação Humana Necessária

Registrada mesmo com `gaps_found`, porque não é absorvida pela lacuna — sobrevive a ela.

### 1. Uma mão humana precisa desenhar os cinco retângulos

**Teste:** `.\calibrar-mercado.bat --gravacao recordings\20260828-063752-mercado-aberto`, desenhando as cinco regiões com o mouse até ver "Calibracao de mercado gravada em calibration.json".
**Esperado:** janelas de seleção no tamanho da imagem; o ENTER do navegador não vaza para o `selectROI` seguinte; cada arrasto devolve caixa não-vazia.
**Por que humano:** o critério 3 começa com "**O usuário roda a ferramenta**". Ele nunca rodou até o fim — três tentativas abortaram num defeito real (resolvido em `03b3e26`) e depois ele delegou; as regiões atuais foram medidas por um agente (âncora de título casando 0.9999 contra o molde do 27x, passo de linha de 45 px por perfil de intensidade) e a imagem de conferência foi vista. Isso é evidência forte de que os **números** estão certos, e é boa evidência. Mas o CR-01 — a janela de seleção renderizando em escala errada, que corromperia qualquer retângulo desenhado à mão — foi corrigido e coberto por teste (`test_a_janela_tem_o_tamanho_da_imagem`) **sem nunca ter sido exercitado por uma mão humana**. Essa é a única metade do critério 3 que grep não alcança.

### 2. Recalibrar com a watchlist real

**Teste:** descomentar `[mercado] watchlist` em `config.toml` (hoje `config.toml:149-154`) e recalibrar.
**Esperado:** `mercado_templates_de_nome` deixa de ser `[]`; a matriz de confusão roda de verdade e `mercado_limiar_de_template` deixa de ser o `0.5` sem significado.
**Por que humano:** exige a watchlist real — só o usuário sabe quais itens quer preçar.

---

## Resumo Narrativo

Esta fase é forte. O gravador ficou honesto de verdade — não apenas o contador, mas as **três** saídas (contador, JSONL e resumo) atrás do retorno do `imwrite`, com o PNG órfão apagado quando o índice recusa a linha, e um `alarme_de_divergencia` que de fato **compara** os dois números em vez de só imprimi-los lado a lado. O firewall não é teatro: instalei `keyboard` no `.venv` e vi o vermelho com a mensagem certa, desinstalei e vi o verde de volta. As 8 gravações existem, passam no portão executável na dimensão da janela, e as respostas de campo estão seladas com 43 caminhos de frame que resolvem no disco — com uma pergunta honestamente marcada NÃO RESPONDIDA em vez de preenchida com o plausível. E a disciplina mais cara do projeto foi mantida com rigor: `rastreador.py` não tem **uma única** ocorrência da palavra "mercado", o gate de brilho da barra própria está literalmente intocado (o único commit que toca `visao.py` é 34 inserções de comentário e um campo), e o sinal do mercado entra em `sessao.tick` **depois** de a lista de eventos já existir — a proteção mora na forma do código, não numa regra a lembrar. O critério 4 prende as duas metades no mesmo laço, como o plano prometeu.

A lacuna é específica e não é sobre qualidade: é sobre escopo entregue. O critério 3 enumera três coisas e duas chegaram. Os templates de dígito não estão adiados — estão órfãos: nenhuma linha de código os corta, nenhum documento reconhece a ausência, e o SUMMARY os conta entre as chaves entregues. Os moldes de **nome**, por contraste, são um adiamento legítimo e bem documentado, e por isso os classifiquei como `deferred`, não como lacuna. A distinção entre os dois casos é o núcleo deste relatório.

Fica também, honestamente, o fato de que nenhum humano jamais completou o fluxo de calibração pelo mouse. O defeito que impedia isso foi encontrado, corrigido e testado, e as regiões foram medidas com rigor por um agente — mas "corrigido e coberto por teste" não é a mesma afirmação que "um humano desenhou um retângulo e funcionou", e o critério 3 pede a segunda.

---

_Verificado: 2026-08-29T01:17:44Z_
_Verificador: Claude (gsd-verifier) — suíte, portões e o teste vermelho do firewall executados pelo próprio verificador; ambiente restaurado_
