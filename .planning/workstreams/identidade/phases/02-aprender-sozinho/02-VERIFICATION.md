---
phase: 02-aprender-sozinho
workstream: identidade
verified: 2026-08-31T15:30:39Z
status: human_needed
score: 5/5 criterios verificados
behavior_unverified: 0
overrides_applied: 0
method: goal-backward + verificacao por MUTACAO independente do fonte de producao
suite:
  comando: "python -m pytest tests/ -q"
  resultado: "3514 passed, 2 skipped, 0 failed, 155.74s"
  jogo_aberto: false
  rede: false
mutacoes_executadas: 21
mutacoes_mortas: 18
mutacoes_sobreviventes: 3
warnings:
  - id: W-01
    severidade: alta
    titulo: "A forma do defeito da Fase 1 REAPARECEU: tres linhas de producao sem guarda nenhuma"
    detalhe: >
      A ligacao do aprendiz ao laco de producao existe e esta correta HOJE, mas
      nenhum dos 3514 testes cai se ela for removida. Tres mutacoes rodadas
      contra a suite INTEIRA sobreviveram com 3514 passed / 0 failed:
      (a) `l2scanner/__main__.py:2204` `aprendiz=aprendiz` -> `aprendiz=None`
          (a feature inteira desligada em campo, suite verde);
      (b) `l2scanner/__main__.py:2076` `cal.assinaturas = identidades.assinaturas`
          removido (o acervo deixa de entrar na lista viva no arranque — elo
          herdado da Fase 1);
      (c) `l2scanner/__main__.py:2087` `Aprendiz(acervo, ajustes_do_aprendiz or ...)`
          -> `Aprendiz(acervo, AjustesDoAprendiz())` (o `[identidade]` do
          config.toml para de chegar no aprendiz).
      A Fase 1 CONSTRUIU a guarda equivalente para o elo dela
      (`tests/test_acervo.py::TestNenhumRastreadorNasceMudo::test_toda_chamada_em_producao_decide_sobre_a_flag`,
      que MORRE quando `assinaturas_configuradas=identidades.configuradas` e
      removido — conferido). A Fase 2 nao construiu a dela.
    impacto: "O objetivo esta alcancado; a garantia de que continue alcancado, nao."
    decisao_humana: true
  - id: W-02
    severidade: baixa
    titulo: "LEITURAS_PARA_APRENDER = 5 nao esta preso por nenhum teste"
    detalhe: >
      Trocar o default de 5 para 1 deixa a suite inteira verde (3514 passed).
      Todos os casos passam `leituras_para_aprender=` explicito. O MECANISMO da
      estabilidade esta provado; o NUMERO escolhido, nao. Com 1 o scanner
      gravaria na SEGUNDA leitura em vez da quinta.
  - id: W-03
    severidade: baixa
    titulo: "Bookkeeping desatualizado apos a onda 02-02"
    detalhe: >
      `.planning/workstreams/identidade/ROADMAP.md` ainda lista
      `- [ ] 02-02-PLAN.md` e a tabela Progress diz "1/2 | In progress".
      `.planning/workstreams/identidade/REQUIREMENTS.md` ainda tem
      `- [ ] **APRE-04**` e "APRE-04 | Phase 2 | Pending".
      Os tres estao desmentidos pelo codigo e pela suite.
fronteiras_aceitas:
  - id: T-02-18
    estado: "CONHECIDA, MEDIDA e AFIRMADA como aceita — nao disfarcada de resolvida"
    medida: "42 celulas -> 0.7531 (nada nasce) / 43 celulas -> 0.7492 (segunda entrada nasce)"
  - id: T-02-07
    estado: "accept, registrado no plano com as tres consequencias escritas"
    medida: "recorte contaminado pontua 0.0 contra tudo e pode ser aprendido se ficar N leituras parado"
human_verification:
  - test: "Rodar uma sessao real de farm e ler a linha de resumo de D-07 no logs/scanner.log"
    expected: "A faixa (minimo, maximo, mediana) das distancias de Hamming entre leituras consecutivas aparece, e o usuario consegue escolher `celulas_toleradas` com esse numero"
    why_human: "Nao existe gravacao multi-frame da party no repositorio. As duas capturas versionadas sao BYTE A BYTE identicas (medido na onda 02-01), entao compara-las mede uma imagem consigo mesma. O default 0 e a escolha certa por AUSENCIA de evidencia, e nao por evidencia de suficiencia."
  - test: "Ler, apos a primeira sessao real, o `log.warning` da virada de regime no scanner.log"
    expected: "O texto explica a mudanca bem o bastante para o usuario NAO concluir que o scanner quebrou quando as mortes param de sair por nome"
    why_human: "Declarado `human_judgment: true` pelo executor (D3). A frase e a ordem das duas linhas estao presas por teste; a suficiencia do texto para um humano no meio do farm nao e afirmavel por grep."
  - test: "Julgar se 43 celulas de drift num nick de 60 pixels de texto e MUITO ou POUCO numa sessao real"
    expected: "Uma decisao sobre valer ou nao um segundo limiar abaixo de 0.75 (a metade de D-02 que nao existe)"
    why_human: "Declarado `human_judgment: true` pelo executor (D22). O par medido e de laboratorio e o modelo de drift e OTIMISTA — ele ACENDE celulas (60 -> 101 pixels); um drift que APAGA texto derruba a correlacao mais rapido."
  - test: "Decidir se a guarda de W-01 entra agora ou na Fase 3"
    expected: "Um caso, no molde de TestNenhumRastreadorNasceMudo, que MORRA quando `aprendiz=aprendiz` sair do `__main__.py`"
    why_human: "E uma decisao de escopo, e nao um defeito de comportamento: as tres linhas existem e estao corretas hoje. O custo de nao decidir e que a Fase 3 constroi o batismo em cima de uma ligacao que some em silencio."
divida_para_a_fase_3:
  - "W-01: as tres linhas de producao sem guarda (a mais grave e `aprendiz=aprendiz`)"
  - "W-02: o 5 de LEITURAS_PARA_APRENDER nao esta preso"
  - "W-03: ROADMAP.md e REQUIREMENTS.md desatualizados (APRE-04 e o plano 02-02)"
  - "T-02-18: uma entrada nunca respondida no batismo + outra da mesma sessao com confianca entre 0.70 e 0.75 no scanner.log = a MESMA pessoa perguntada duas vezes"
  - "T-02-07: uma entrada de lixo gera uma pergunta absurda no grupo do WhatsApp"
  - "A armadilha: baixar LIMIAR_DO_ORNAMENTO abaixo de LIMIAR_DE_CASAMENTO reabre o caminho do operador"
  - "O criterio 5 e NECESSARIO e NAO SUFICIENTE: os casos de replay sozinhos nao pegam D-03 desligado (confirmado por mutacao)"
---

# Fase 2: Aprender sozinho — Relatorio de Verificacao

**Objetivo da fase (ROADMAP.md):** Uma linha ocupada que nao casa com nenhuma
assinatura conhecida deixa de ser um misterio permanente: o scanner grava a
assinatura dela sozinho, depois de estavel, sem calibracao e sem intervencao —
e sem gravar a mesma pessoa duas vezes.

**Verificado:** 2026-08-31T15:30:39Z
**Status:** human_needed
**Placar:** 5/5 criterios verificados
**Metodo:** goal-backward, e a evidencia NAO e "o teste existe". Para cada
criterio a pergunta respondida foi *"o teste cairia se o codigo de producao
parasse de fazer isso?"* — respondida por **21 mutacoes rodadas por mim no
fonte de producao**, e nao pela leitura dos SUMMARY.

---

## 1. Os cinco criterios

| # | Criterio (ROADMAP) | Producao faz? | O teste cai se parar? | Status |
|---|---|---|---|---|
| 1 | Linha ocupada + nao reconhecida por N leituras estaveis -> EXATAMENTE uma entrada, SEM nome, e a linha continua calada (APRE-01) | Sim — `sessao._aprender` -> `aprendiz.observar` -> `acervo.gravar`, com `nome=""` | **Sim.** Desligar D-03 derruba 5 casos; desligar o elo derruba 3; gravar com nome de mentira derruba 6; nao propagar o aprendizado ao resultado derruba 4 | ✓ VERIFIED |
| 2 | Recorte MUDANDO nao grava nada; instabilidade recusada e nao mediada; estabilidade por CONTEUDO e nunca por indice (APRE-02) | Sim — `_Vigia` com ancora fixa + `distancia_de_hamming <= tolerado` | **Sim.** Aceitar qualquer distancia derruba 11 casos; casar vigia por INDICE derruba 10; ancora virando ultima-leitura derruba 1; distancia falsificada derruba 2; default 0 -> 12 derruba 7 | ✓ VERIFIED |
| 3 | Linha que casa com o acervo — com nome ou sem — nao gera entrada nova: o casamento VETA antes de aprender (APRE-04) | Sim — DOIS portoes sobrepostos: `linha.nome is None` (sessao) e `confianca >= 0.75` (aprendiz) | **Sim.** Trocar o operador derruba 2 casos; desligar D-02 derruba 2; `>=` virando `>` derruba 1 | ✓ VERIFIED |
| 4 | Sai da party e volta, na mesma sessao e depois de um reinicio, continua UMA entrada (APRE-04) | Sim — a dedupe e por CORRELACAO (D-03), nao por chave | **Sim.** Desligar D-03 derruba exatamente estes casos. E a FAIXA de validade esta medida e declarada (ver §4) | ✓ VERIFIED |
| 5 | Reproduzir a mesma gravacao duas vezes deixa a mesma contagem (APRE-01, APRE-04) | Sim — chave `sha256` deterministica + `ja_existia` tratado como sucesso | **Parcialmente, e o executor foi honesto sobre isso.** Os tres casos de replay sozinhos NAO pegam D-03 desligado — confirmei por mutacao. Quem prende o criterio sao os casos de sai-e-volta. Como conjunto, o criterio esta coberto | ✓ VERIFIED (ver ressalva) |

**Placar: 5/5.** Nenhum criterio ficou PRESENT_BEHAVIOR_UNVERIFIED: todos os cinco
sao afirmados por casos comportamentais que rodam `Sessao.tick` de verdade sobre
um PNG real da party window, atravessando `extrair`, `_recorte_do_nome`,
`mascara_de_texto` e `identificar_linhas`, e eu vi cada um deles CAIR sob mutacao.

---

## 2. A tabela de mutacoes — a prova de que os testes nao sao vacuos

Rodadas por mim, no fonte de producao, com restauracao do arquivo depois de cada
uma. `tests/test_aprendiz.py` tem 85 casos e roda em ~2 s; as mutacoes de
`__main__.py` foram rodadas contra a suite INTEIRA (3514 casos, ~2,5 min cada).

### Mortas (18) — o comportamento esta preso

| # | Mutacao | Arquivo | Casos derrubados |
|---|---|---|---|
| M1 | `linha.nome is not None` -> `linha.nome` (o operador de D-02/APRE-04) | sessao.py | 2 |
| M2 | `cal.assinaturas.append(...)` removido (D-03 desligado) | sessao.py | 5 |
| M3 | `assinaturas_configuradas = True` removido (o ELO) | sessao.py | 3 |
| M4 | portao `confianca >= LIMIAR_DE_CASAMENTO` removido (D-02) | aprendiz.py | 2 |
| M5 | portao `PIXELS_MINIMOS_DE_TEXTO` removido | aprendiz.py | 1 |
| M6 | `not observacao.ui_visivel` removido de `_aprender` (cegueira) | sessao.py | 1 |
| M6b | `not observacao.ui_visivel` removido de `_candidatas_para_aprender` | sessao.py | 1 |
| M7 | `distancia <= tolerado` -> qualquer distancia (estabilidade off) | aprendiz.py | 11 |
| M8 | `falhou` colapsado em `criado` | aprendiz.py | 2 |
| M10 | ancora atualizada para a ultima leitura (deriva) | aprendiz.py | 1 |
| M11 | `distancia=distancia` -> `distancia=0` (D-07 mentindo) | aprendiz.py | 2 |
| M12 | portao `EstadoDaLinha.COM_MEMBRO` removido | sessao.py | 1 |
| M14 | `celulas_toleradas` default 0 -> 12 | aprendiz.py | 7 |
| M15 | `resultado.aprendizados.extend(...)` removido | sessao.py | 4 |
| M17 | `self._registrar_recusas(...)` removido | sessao.py | 2 |
| M20 | `assinaturas_configuradas=identidades.configuradas` removido (elo da Fase 1) | \_\_main\_\_.py | 1 |
| M23 | `mascaras_de_nome` sempre vazio | visao.py | 27 |
| M24 | vigia casado por INDICE em vez de conteudo (D-08 off) | aprendiz.py | 10 |
| M25 | assinatura gravada com nome de mentira em vez de `""` | aprendiz.py | 6 |
| M26 | o `log.warning` da virada vira `log.debug` | sessao.py | 2 |

### Sobreviventes (3) — nenhuma quebra um criterio, todas sao divida

| # | Mutacao | Suite | Leitura |
|---|---|---|---|
| **M19** | `aprendiz=aprendiz` -> `aprendiz=None` em `__main__.py:2204` | **3514 passed, 0 failed** | **A feature inteira desligada em campo, e nada acusa.** Ver W-01 |
| **M21** | `cal.assinaturas = identidades.assinaturas` removido em `__main__.py:2076` | **3514 passed, 0 failed** | O acervo para de entrar na lista viva no arranque. Elo herdado da Fase 1 |
| **M18** | `Aprendiz(acervo, ajustes_do_aprendiz or ...)` -> `Aprendiz(acervo, AjustesDoAprendiz())` | **3514 passed, 0 failed** | O `[identidade]` do `config.toml` para de chegar ao aprendiz |
| M9 | `LEITURAS_PARA_APRENDER = 5` -> `1` | **3514 passed, 0 failed** | O numero nao esta preso. Ver W-02 |

---

## 3. Os seis pontos pedidos, um a um

### 3.1 O elo do `assinaturas_configuradas` esta LIGADO em producao?

**SIM — e por dois caminhos, os dois em codigo de producao, os dois provados.**

1. **No arranque** (elo da Fase 1): `l2scanner/__main__.py:2099`
   `assinaturas_configuradas=identidades.configuradas`. Guardado por
   `tests/test_acervo.py::TestNenhumRastreadorNasceMudo::test_toda_chamada_em_producao_decide_sobre_a_flag`
   — removi a linha e o caso MORREU (M20). A Fase 1 construiu a guarda dela.
2. **No primeiro aprendizado** (elo da Fase 2): `l2scanner/sessao.py:729`
   `self.rastreador.assinaturas_configuradas = True`, dentro do laco dos
   aprendizados de `_aprender`. Removi a linha e caem 3 casos (M3), entre eles
   `test_antes_morre_com_o_nome_da_lista_e_depois_nao_morre`, que afirma a
   transicao de regime pelas duas metades: **antes** do aprendizado a morte sai
   com o nome da lista por posicao, **depois** nao sai evento nenhum.

**MAS a forma do defeito REAPAREGEU noutro lugar** (W-01). O defeito da Fase 1
era "oito atribuicoes, todas em teste, zero em producao". A Fase 2 nao repetiu
isso — a atribuicao esta em producao. O que ela repetiu foi a **falta de guarda**:
tres linhas em `__main__.py` que so existem em producao, e que a suite inteira
nao defende. A mais grave e `aprendiz=aprendiz`: **e a unica linha que liga a
feature inteira ao laco, e apaga-la deixa 3514 testes verdes.**

O caso `tests/test_acervo.py::TestQuemConheceOAcervoEOQueOLacoFazComEle::test_o_laco_real_ESCREVE_no_acervo_e_escreve_uma_vez_so`
chama-se "o laco real", mas **monta a `Sessao` a mao** (linhas 1026-1038) — ele
prova a cadeia `sessao.tick -> aprendiz.observar -> acervo.gravar`, e nao a
cadeia `main() -> laco_principal -> Sessao(aprendiz=...)`.

### 3.2 Existe algum criterio cujo teste passaria com o comportamento DESLIGADO?

**Nenhum dos cinco.** As 18 mutacoes mortas cobrem todos os mecanismos que os
cinco criterios afirmam. O relato do executor da onda 2 — "nenhum caso ficou
vermelho contra o codigo de producao, o RED veio por mutacao" — e **legitimo e
confirmado**: reproduzi as mutacoes dele e encontrei mais 13, e o padrao se
sustenta.

**Uma ressalva, que o proprio executor levantou e eu confirmei:** o **criterio 5
isolado e vacuo contra D-03 desligado**. Reproduzir o mesmo frame regrava a mesma
chave `sha256` deterministica e recebe `ja_existia`, entao a contagem nao muda
nem sem a lista viva. Removi `cal.assinaturas.append(...)` e os tres casos de
`TestOReplayNaoEngorda` **continuaram verdes** — quem caiu foram os de
sai-e-volta e os quatro de fronteira. O criterio 5 e necessario e nao suficiente,
e so nao e um buraco porque o criterio 4 existe no mesmo arquivo.

O que sobrevive nao e criterio, e **tuning**: o `5` de `LEITURAS_PARA_APRENDER`
(W-02) e a ligacao em `__main__.py` (W-01).

### 3.3 A cadeia do T-02-13 (`LIMIAR_DO_ORNAMENTO` > `LIMIAR_DE_CASAMENTO`)

**CONFIRMADA no codigo real, e o executor estava certo contra a previsao do plano.**

Em `l2scanner/identidade.py` existem **exatamente dois** lugares que atribuem um
nome a uma linha, e li os dois:

- `identificar_linhas`, primeiro passe: o `while` faz `break` quando
  `valor < LIMIAR_DE_CASAMENTO`, entao toda atribuicao `resultado[i] = Casamento(assinaturas[j].nome, valor, ...)`
  tem `valor >= 0.75` (linhas 429 e 448).
- `_segundo_passe_do_ornamento`, a repescagem da coroa: `break` quando
  `valor < LIMIAR_DO_ORNAMENTO`, e `LIMIAR_DO_ORNAMENTO = 0.85` (linhas 104, 524, 535).

Como **0.85 > 0.75**, "a linha TEM nome" IMPLICA "a confianca passou de 0.75", que
e exatamente a condicao que o portao de D-02 (`aprendiz.py`: `if candidata.confianca >= LIMIAR_DE_CASAMENTO: continue`)
veta. Os dois portoes se sobrepoem por construcao, sem sobra e sem vao — e o caso
`test_o_invariante_que_faz_D02_bastar_ACIMA_do_limiar` varre 0..59 celulas e prova
a juncao exata.

**Rodei a mutacao (M1)** e o resultado bate com o relato: `linha.nome is None` ->
`not linha.nome` derruba **2 casos** —
`TestQuemNuncaECandidato::test_uma_linha_ja_reconhecida_e_anonima_nunca_e_candidata`
(o unitario da onda 1, que le `_candidatas_para_aprender` diretamente, a unica
camada onde o operador E observavel) e o caso novo que a onda 2 escreveu para
registrar a medicao. **O caso de ponta a ponta continua verde**, exatamente como
o executor descreveu. A correcao dele foi na PROVA (mensagem de falha que mentia
sobre a causa), e nao no codigo — e essa e a decisao certa.

### 3.4 A fronteira T-02-18 esta declarada, e nao disfarcada?

**DECLARADA, em voz alta, e no lugar mais dificil de ignorar: na mensagem de falha
do proprio caso.**

`TestAFronteiraDaDedupe::test_logo_ABAIXO_do_limiar_uma_SEGUNDA_chave_NASCE_e_isso_e_ACEITO`
afirma `len(novas) == 1` — ou seja, **afirma que a segunda entrada NASCE** — com
a mensagem: *"ESTE DESFECHO E CONHECIDO E ACEITO (T-02-18), e nao um defeito a
consertar aqui... Se este caso comecou a falhar, alguem MUDOU o comportamento:
confira o que, antes de mexer no teste."* E ainda afirma `antes < depois`, isto e,
**as duas entradas da mesma pessoa convivem** no acervo que nao tem comando de
esquecer.

O irmao logo acima (`42 celulas -> 0.7531`) mora no mesmo arquivo de proposito,
"para ninguem ler o de cima sozinho e concluir que a dedupe vale sempre". A
docstring da classe traz os quatro argumentos (a-d) e o veto explicito *"NAO
'CONSERTE' ESTE CASO"*.

Os dois numeros sao reproduziveis por comando com o jogo fechado. **Nada esta
disfarcado de resolvido.**

### 3.5 Tudo demonstravel sem jogo aberto e sem rede?

**SIM, e conferido rodando.** `python -m pytest tests/ -q` -> **3514 passed, 2
skipped, 0 failed em 155,74 s**, com o jogo fechado nesta maquina.
`tests/test_aprendiz.py` nao importa `requests`, `socket`, `mss` nem `dxcam`
(conferido por grep); ele le um PNG versionado e roda `Sessao.tick` com
`momento=` por parametro.

A recusa por tolerancia alem do teto e demonstrada por `main()` **chamada de
verdade** (`test_main_chamada_de_verdade_devolve_2_com_o_jogo_fechado`), com
`laco_principal` monkeypatchado para ACUSAR se a execucao chegar nele — e isso so
funciona porque a leitura da configuracao ficou num `try` LOCAL, ANTES de qualquer
fonte de captura. O desvio que o executor registrou na onda 1 esta correto e e o
que torna esta linha verificavel sem tela viva.

### 3.6 O acervo e irreversivel — algum caminho por onde lixo vira entrada?

**Seis portoes, em ordem, e cada um com mutacao que o mata:**

| Portao | Onde | Recusa | Mutacao |
|---|---|---|---|
| `ui_visivel` | `sessao._aprender` + `_candidatas_para_aprender` | frame doente, ancora sem contraste, moldura da barra quebrada (janela por cima), party window sem nenhum icone | M6, M6b |
| `EstadoDaLinha.COM_MEMBRO` | `_candidatas_para_aprender` | linha vazia | M12 |
| `linha.nome is None` | `_candidatas_para_aprender` | ja reconhecida (com nome ou anonima) | M1 |
| `mascaras_de_nome.get(indice)` | `_candidatas_para_aprender` | sem recorte de nome | M23 |
| `< PIXELS_MINIMOS_DE_TEXTO` | `aprendiz.observar` | recorte quase sem texto — e este e o UNICO portao que existe na instalacao nova, porque `identificar_linhas` retorna cedo com a lista vazia | M5 |
| `confianca >= LIMIAR_DE_CASAMENTO` | `aprendiz.observar` | falha por MARGEM (dois parecidos demais) | M4 |
| N leituras estaveis por CONTEUDO | `aprendiz.observar` | qualquer coisa que pisque ou mude | M7, M24, M10 |

**"Janela por cima"** desce por `visao.py:684`: `_bordas_da_barra_intactas` falha
-> `ui_visivel = False` no frame INTEIRO -> `_aprender` sai cedo. **"Frame cego"**:
`SaudeDoFrame != OK` -> `Observacao(ui_visivel=False, linhas=())`. **"Linha vazia"**:
o portao de estado. E a cegueira **CONGELA** a contagem em vez de zerar, provado
pelos dois casos de `TestCegueiraNaoEnsina`.

**A porta que fica aberta, e ela esta declarada:** **T-02-07** — um recorte
*contaminado* (algo claro por cima do nome, com a moldura da barra e a ancora
intactas) pontua 0.0 contra tudo, passa em D-02, e **pode ser aprendido se ficar
N leituras parado**. Aceito e registrado no `02-01-PLAN.md:1044` com as tres
consequencias escritas, e diagnosticavel depois porque o `log.info` do
aprendizado grava a contagem de pixels (caso
`test_o_log_do_aprendizado_diz_a_confianca_e_os_pixels`).

---

## 4. As duas fronteiras medidas

| Fronteira | Numero | Estado |
|---|---|---|
| T-02-18 — a pessoa que volta com drift | 42 celulas -> 0.7531 (**nada nasce**) / 43 celulas -> 0.7492 (**segunda entrada nasce**) | Uma UNICA celula separa a faixa em que a dedupe vale da faixa em que ela nao vale. Declarada aceita |
| T-02-07 — recorte contaminado | pontua 0.0 contra tudo | Aceito; o rastro e a contagem de pixels no log |

**A leitura que generaliza, e ela nao e o 2,15%:** 43 celulas sao **71,7% do
sinal de texto** (43 de 60 pixels) daquele nick. **Num nick curto a fronteira
chega muito antes.** E o modelo de drift usado **ACENDE** celulas (o recorte
ganha pixels, de 60 para 101) — um drift que **APAGA** texto derruba a correlacao
mais rapido. **A tabela e um limite otimista**, e o proprio arquivo de teste diz
isso.

---

## 5. Artefatos e elos

| Artefato | Existe | Substantivo | Ligado | Dados fluem | Status |
|---|---|---|---|---|---|
| `l2scanner/aprendiz.py` | 503 linhas | Sim — 12 simbolos, todos com teste | Sim (`sessao`, `config`, `__main__`) | Sim | ✓ VERIFIED |
| `l2scanner/sessao.py` (`_aprender`, `_candidatas_para_aprender`, `_registrar_recusas`) | Sim | Sim | Sim | Sim | ✓ VERIFIED |
| `l2scanner/visao.py` (`Observacao.mascaras_de_nome`) | Sim | Sim | Sim | Sim (M23 derruba 27 casos) | ✓ VERIFIED |
| `l2scanner/config.py` (`ler_ajustes_do_aprendiz`) | Sim | Sim | Sim (`main()`) | **Parcial** — M18 mostra que `laco_principal` pode descartar os ajustes sem nada acusar | ⚠️ ver W-01(c) |
| `l2scanner/__main__.py` (acervo, aprendiz, ajustes) | Sim | Sim | **Sim, mas sem guarda** | Sim | ⚠️ ver W-01 |
| `config.toml` `[identidade]` | Sim, comentada, com o teto e a frase de D-07 | Sim | Sim | Sim | ✓ VERIFIED |
| `tests/test_aprendiz.py` | 2794 linhas, 85 casos | Sim | — | — | ✓ VERIFIED |
| `aprendiz.py` na tupla `MODULOS` (portao AST de relogio) | Sim | Sim | Sim | — | ✓ VERIFIED |

**Elos verificados**

| De | Para | Via | Status |
|---|---|---|---|
| `visao.extrair` | `Observacao.mascaras_de_nome` | `mascara_de_texto(recorte)` recalculada, funcao continua PURA | ✓ WIRED |
| `sessao.tick` | `aprendiz.observar` | `_aprender` -> `_candidatas_para_aprender` | ✓ WIRED |
| `aprendiz._gravar` | `acervo.gravar` | tri-estado `criado \| ja_existia \| falhou` honrado | ✓ WIRED |
| `aprendiz` | `cal.assinaturas` (lista viva, D-03) | `sessao._aprender` append | ✓ WIRED |
| `aprendiz` | `rastreador.assinaturas_configuradas` | `sessao._aprender`, com aviso da virada | ✓ WIRED |
| `config.toml [identidade]` | `AjustesDoAprendiz` | `main()` -> `laco_principal(ajustes)` -> `Aprendiz(...)` | ⚠️ WIRED SEM GUARDA (M18) |
| `main()` | `Sessao(aprendiz=...)` | `__main__.py:2204` | ⚠️ **WIRED SEM GUARDA (M19)** |

---

## 6. Cobertura de requisitos

| Requisito | Descricao | Status no codigo | Status no REQUIREMENTS.md |
|---|---|---|---|
| APRE-01 | linha desconhecida vira UMA entrada anonima | ✓ SATISFEITO | `[x]` Complete |
| APRE-02 | so grava depois de estavel por N frames | ✓ SATISFEITO | `[x]` Complete |
| APRE-04 | aprender a mesma pessoa duas vezes nao acontece | ✓ SATISFEITO (dentro da faixa medida, com T-02-18 declarado) | ⚠️ **`[ ]` Pending — desatualizado** |

---

## 7. Anti-padroes

Nenhum marcador de divida (`TODO`, `FIXME`, `XXX`, `TBD`, `HACK`, `PLACEHOLDER`)
nos arquivos da fase. Os acertos de grep sao palavras portuguesas
(`TODO caminho`, `TODOS_OS_DIAS`, `TODO comando`), e nao marcadores.
Nenhum stub. Nenhum `return None` vacuo. Nenhuma dependencia nova.

---

## 8. Veredito

**GOAL ACHIEVED.** Os cinco criterios sao verdadeiros no codigo de producao, e
cada um deles morre sob mutacao do fonte — nao ha criterio sustentado por um
teste vacuo. As duas fronteiras que a fase nao fecha estao **medidas e
declaradas**, e a mais perigosa delas (T-02-18) esta afirmada na mensagem de
falha do proprio caso que a demonstra.

**O status e `human_needed`, e nao `passed`,** por quatro itens que so um humano
resolve: o numero de campo do drift (que nao existe no repositorio), a
suficiencia do texto do aviso da virada, o julgamento sobre um segundo limiar, e
a decisao de escopo sobre a guarda de W-01.

**O que a Fase 3 herda como divida** esta na frontmatter (`divida_para_a_fase_3`).
O item que merece atencao antes de qualquer outro e o **W-01**: a Fase 1 gastou
uma onda inteira descobrindo que uma garantia provada na suite estava desligada
em campo, e construiu uma guarda contra isso. A Fase 2 entregou a ligacao
correta — e nao construiu a guarda equivalente. Hoje `aprendiz=aprendiz` pode
sumir do `__main__.py` e os 3514 testes continuam verdes.

---

_Verificado: 2026-08-31T15:30:39Z_
_Verificador: Claude (gsd-verifier) — 21 mutacoes rodadas, arvore restaurada e conferida limpa ao final_
