---
phase: 03-persist-ncia-de-observa-es
workstream: mercado
verified: 2026-08-31T00:00:00Z
status: passed
score: 1/5 must-haves verificados por codigo (4/5 sao portao humano por natureza)
behavior_unverified: 0
overrides_applied: 0
human_verification:

  - test: "Roteiro 1, passos 1-2 — produzir o `observacoes.csv` real do censo (`.venv/Scripts/python.exe tools/gerar_observacoes_do_censo.py --saida C:/temp/portao-fase3`) e abrir no editor"
    expected: "O usuario le e ENTENDE: uma linha por observacao, `primeira_vez` com o carimbo ancorado, `total_em_centesimos` e `quantidade` em colunas separadas, NENHUMA coluna de unitario, `6200` = `62,00`"
    why_human: "Criterio 1 do ROADMAP e sobre COMPREENSAO humana. A suite prova a forma do arquivo; so o olho dele prova que ele entende. Alem disso `recordings/` + `calibration.json` + motor de OCR so existem no checkout PRINCIPAL"

  - test: "Roteiro 1, passo 3 — importar esse mesmo arquivo no Google Sheets (Arquivo > Importar > Enviar; separador Personalizado, digitar `;`)"
    expected: "As colunas caem uma por coluna, nada colapsado numa so"
    why_human: "Criterio 2 diz literalmente 'Testado com importacao real, nao presumido'. O Google Sheets nao tem linha de comando"

  - test: "Roteiro 1, passo 4 — no Sheets, procurar uma linha cujo nome comece com `+` (o censo tem 15, ex.: `+6 Agathion Alpha Hunter Sealed`)"
    expected: "A celula mostra o NOME, nao um erro de formula. Se der erro, reportar qual"
    why_human: "Risco ALTO e NAO MEDIDO (T-03-18, disposicao `accept`). O nome NAO e saneado no arquivo, de proposito — o conserto, se preciso, e na planilha, nunca sujando o dado"

  - test: "Roteiro 1, passo 5 — conferir a coluna `residuo_do_cruzamento` no Sheets"
    expected: "Existem celulas VAZIAS e celulas com `0`, e elas nao viraram a mesma coisa"
    why_human: "A suite prova a distincao na ida e na volta em memoria e em disco; o que so a mao dele fecha e se o SHEETS preserva a distincao na importacao"

  - test: "Roteiro 1, passo 6 — rodar a MESMA ferramenta uma segunda vez, mesma saida e mesmo subconjunto; contar as linhas do arquivo antes e depois"
    expected: "Relatorio diz ZERO observacoes gravadas, todas duplicadas, imprime a frase de desfecho esperado, e SAI COM CODIGO 0. A contagem de linhas nao muda"
    why_human: "Criterio 3 e explicitamente 'o usuario pode contar antes e depois'. Sobre material REAL, nao sobre paginas de teste"

  - test: "Roteiro 2, passos 1-4 — quebrar a saida de proposito (arquivo ocupando o nome da pasta; `observacoes.csv` somente-leitura; cabecalho editado a mao) e olhar o CONSOLE, depois `logs/scanner.log`"
    expected: "Duas linhas ERROR: a primeira diz que o mercado desligou e por que; a segunda diz que morte/saida/ressurreicao seguem sendo detectadas e entregues. Sem traceback. As mesmas duas mensagens no log. No caso do cabecalho, o arquivo em disco NAO foi alterado"
    why_human: "A metade CONSOLE do criterio 5 so se prova olhando o console. A suite prova que os registros ERROR existem e que o texto e o da montagem; que eles CHEGAM aos olhos dele, nao. O passo somente-leitura depende das propriedades do Windows"

  - test: "Roteiro 2, passo 5 — rodar o scanner normalmente e confirmar que nada mudou"
    expected: "Ele sobe, detecta e entrega igual"
    why_human: "Nesta fase isso e esperado POR CONSTRUCAO (ausencia de acoplamento). O passo existe para pegar regressao acidental, nao para provar fiacao — a fiacao e Fase 4"
deferred:

  - truth: "Criterio 5, metade 'os alertas de party continuam chegando' provada por FIACAO REAL (o mercado ligado dentro do scanner e falhando sem derrubar a party)"
    addressed_in: "Phase 4"
    evidence: "ROADMAP Fase 4, requisito DETC-02 e criterio 1: 'O usuario inicia --mercado como terceira invocacao ao lado das duas instancias de party, e o modo party segue intocado'. Nesta fase PERS-03 e verdadeiro por AUSENCIA DE ACOPLAMENTO, e a fase DECLARA isso em tres lugares (docstring de `montar_registro_de_mercado`, cabecalho do Roteiro 2, e o passo 5 dele)"
audit_acknowledged:
  milestone: v1-mercado
  at: 2026-09-01
  status: human_needed
---

# Fase 3: Persistencia de observacoes — Relatorio de Verificacao

**Goal:** Cada pagina aceita vira linhas num arquivo CSV que o usuario abre e le — sem duplicar, sem adivinhar, e sem jamais derrubar o nucleo de alertas.
**Verificado:** 2026-08-31
**Status:** `human_needed`
**Re-verificacao:** Nao — verificacao inicial

## Veredito de uma linha

**O codigo esta la, e ele e bom.** Nenhum stub, nenhum caminho de dado desligado, nenhuma
regressao fora do escopo. Mas **quatro dos cinco criterios do ROADMAP sao portoes humanos por
natureza** — "o usuario ABRE e ENTENDE", "IMPORTA no Sheets", "CONTA antes e depois", "VE o
aviso alto" — e nenhum deles foi fechado, porque o usuario esta dormindo. A fase entregou o
MATERIAL para os portoes (`tools/gerar_observacoes_do_censo.py`) e os dois roteiros. O que
falta e a mao dele.

## Realizacao do objetivo

### Verdades observaveis (os 5 criterios do ROADMAP)

| # | Criterio | Status | Evidencia |
|---|----------|--------|-----------|
| 1 | O usuario abre o CSV num editor e ENTENDE: uma linha por observacao, carimbo ancorado, total e quantidade em colunas separadas (unitario derivado, nunca confundido), precos como inteiros em centesimos | ? PORTAO HUMANO — forma provada, compreensao nao | `COLUNAS` tem exatamente 6 campos e a ordem esta travada por teste (`test_as_seis_colunas_na_ordem_travada`); `test_NAO_ha_coluna_de_unitario_derivado` e `test_NAO_ha_coluna_de_proveniencia_de_bancada` provam as ausencias; `test_a_unidade_esta_no_NOME_da_coluna` prova `total_em_centesimos`; `test_o_relogio_entra_por_PARAMETRO_e_nao_de_dentro` prova que o carimbo nunca vem de `datetime.now()`. **O que a suite NAO prova: que ele entende.** |
| 2 | Importa no Google Sheets e as colunas caem certas — separador `;`, testado com importacao REAL | ? PORTAO HUMANO — nao ha como automatizar | `SEPARADOR` e importado do `mercado_catalogo` e nao redefinido (`test_o_separador_e_a_pasta_vem_do_CATALOGO_e_nao_sao_redefinidos`); `TEXTO_DO_LEIAME` ensina o dialogo exato ("escolha PERSONALIZADO (Custom) e digite `;`") e ha teste para isso (`test_ele_ensina_o_separador_PERSONALIZADO_do_dialogo_do_sheets`). O proprio criterio diz "nao presumido" |
| 3 | Reler ou revisitar a mesma pagina nao aumenta a contagem de linhas | ✓ VERIFIED em teste / ? PORTAO HUMANO sobre material real | `registrar` confere `chave in self.chaves` ANTES de abrir o arquivo (l. 680-682) — dedup em memoria, literal do PERS-02. Testes verdes: `test_a_MESMA_observacao_de_novo_devolve_False_e_NAO_cresce`, `test_uma_SESSAO_NOVA_reconstroi_o_indice_do_disco`, `test_o_mesmo_anuncio_em_OUTRO_DIA_continua_False`, `test_a_costura_rodada_DUAS_VEZES_nao_aumenta_as_linhas_do_arquivo`. O passo 6 do Roteiro 1 e o mesmo fato sobre material REAL |
| 4 | Escrita interrompida no meio de uma linha: a leitura seguinte descarta APENAS a linha truncada, com aviso — nunca o arquivo inteiro como corrompido, nunca o pedaco como observacao valida | ✓ VERIFIED (com uma leitura do criterio que MUDOU, e a mudanca esta justificada) | **Este e o unico criterio inteiramente fechado por codigo.** Ver a secao D-17 abaixo |
| 5 | Arquivo quebrado (travado, read-only, pasta inexistente): o usuario ve o aviso ALTO de que o mercado desligou — e os alertas de party continuam chegando | ? PORTAO HUMANO (metade console) + verdadeiro por AUSENCIA DE ACOPLAMENTO (metade party) | `registrar` captura `OSError` estreito, poe `ligado = False`, emite DOIS `log.error` e devolve `False` — nunca levanta. `montar_registro_de_mercado` captura `(OSError, ContratoDoArquivoQuebrado)`, emite as mesmas duas mensagens e devolve `None`, nunca levanta (`test_nao_ha_raise_em_lugar_nenhum_da_montagem`, por AST). A metade "party continua" e ausencia de acoplamento — ver abaixo |

**Score: 1/5 fechados por codigo.** Os outros quatro nao estao FALHOS: estao **abertos, com o
material pronto e o roteiro escrito.**

### Criterio 4 e o D-17 — o ponto mais forte da fase, e a leitura que mudou

O criterio literal do ROADMAP diz "descarta APENAS a linha truncada". A implementacao faz
algo **mais duro**: um arquivo que nao termina em quebra de linha e **contrato quebrado** — a
feature desliga alto e **nada** e lido dele. A justificativa esta medida e escrita no fonte
(`_conferir_o_terminador`, l. 460-505) e ela procede:

- Sobre a linha de seis campos cortada byte a byte a partir do fim, os **5 cortes** deixam o
  arquivo sem quebra final — mas **2 deles produzem seis campos todos parseaveis**, com `80`
  virando `8`. A contagem de campos aprovaria esses dois. Pior: a linha truncada viraria
  **chave de dedup**, bloqueando para sempre a gravacao da observacao correta.

- Portanto "descartar so a linha truncada" **nao e alcancavel** com a informacao disponivel —
  o programa nao consegue distinguir "linha truncada" de "linha boa salva sem newline". A
  fase escolheu recusar o arquivo em vez de adivinhar, e **nao tocar nenhum byte**.

- As duas saidas alternativas estao **refutadas por escrito no fonte** (truncar a cauda;
  completa-la com `\n`) — a doutrina da casa "um numero que caiu precisa dizer que caiu".

**A rede por linha continua existindo** para o corpo do arquivo: `chave_dos_campos` derruba
linha a linha com `warning` e as demais carregam (`test_linha_do_meio_com_campos_A_MENOS_cai_e_as_demais_CARREGAM`,
`test_a_rede_de_TIPO_pega_cada_campo_e_as_demais_carregam`). A metade "nunca trata o arquivo
inteiro como corrompido" do criterio 4 vale para linha ruim; o portao do terminador e um caso
diferente e o fonte diz por que.

**T-03-01b existe, tem criterio de AST, e esta VERDE.**

```
tests/test_mercado_registro.py::TestALeituraNAO_ESCREVE::test_o_modulo_nao_chama_truncate_em_lugar_nenhum
  assert "truncate" not in chamadas, chamadas   # ast.walk sobre o modulo inteiro
```

Rodado nesta arvore: **PASSED**. Acompanhado de
`test_NENHUM_byte_do_arquivo_do_usuario_e_tocado_na_recusa` e
`test_a_recusa_por_cabecalho_tambem_nao_toca_BYTE_nenhum`. A decisao esta presa
estruturalmente, nao por comentario. **O D-17 nao pode ser desfeito por descuido.**

Custo aceito e real, e ele esta declarado: uma queda de energia de verdade desliga o registro
ate intervencao manual. A mensagem de erro diz ao usuario exatamente o que fazer para religar.

### `residuo_do_cruzamento`: `None` e `0` nao colapsam — VERIFICADO nos dois sentidos

| Sentido | Onde | Teste | Resultado |
|---------|------|-------|-----------|
| Ida (memoria -> campos) | `campos_da_observacao`: `"" if residuo is None else str(residuo)` | `test_None_sai_VAZIO_e_zero_sai_ZERO` | PASSED |
| Volta (campos -> memoria) | `residuo_dos_campos`: `if not bruto: return None` | `test_a_volta_devolve_None_e_zero_e_NUNCA_um_pelo_outro` (assert `is None`, `== 0` **e** `is not None`) | PASSED |
| Ida e volta com valor medido | idem | `test_um_residuo_medido_sobrevive_a_ida_e_volta` (80) | PASSED |
| Em disco | leitura de arranque | `test_uma_linha_de_residuo_ZERO_carrega_normalmente` | PASSED |

`residuo_dos_campos` mora **no modulo**, nao no teste — a docstring diz explicitamente que uma
volta que morasse no teste seria "o teste provando a si mesmo". Correto.

O que **falta**: se o **Google Sheets** preserva a distincao celula-vazia vs `0` na importacao.
Isso e o passo 5 do Roteiro 1, e e portao humano.

### A dedup e a borda do congelamento — VERIFICADO, e o teste CITA o `WINDOWS.md`

`tests/test_mercado_registro.py:415` —
`test_a_MESMA_observacao_de_novo_devolve_False_e_NAO_cresce`. A docstring nomeia a borda:

> "A dedup que tapa a **borda 33 do `WINDOWS.md`** [...] ACEITO PELO USUARIO EM 2026-08-30:
> numa captura TRAVADA uma pagina e aceita antes de o congelamento disparar — o acordo fecha
> com 2 frames identicos e `JANELAS_IGUAIS_PARA_CONGELAR` e 3 [...] **Esta dedup e o que
> impede aquela pagina de virar linha duplicada no CSV** — foi com essa rede na mesa que a
> borda foi aceita em vez de baixar o limiar para 2."

A dependencia esta explicita, com data e com o motivo de a alternativa ter sido recusada. Nao
e "dedup generica". **PASSED.**

### PERS-03 e a ausencia de acoplamento — a fase DECLARA, nao finge

O ceticismo estava certo em perguntar. A resposta e boa **nos tres lugares**:

1. **No fonte** — `l2scanner/__main__.py`, docstring de `montar_registro_de_mercado`:
   *"ELA NASCE SEM CHAMADOR, E ISSO E DESENHO. `montar_gravador` tem um portao de
   curto-circuito na entrada (`if not args.record`) porque existe a flag `--record`; aqui nao
   ha flag, porque `--mercado` e DETC-02, Fase 4."*

2. **No cabecalho do Roteiro 2** (03-03-SUMMARY): *"Declaracao honesta do que esta fase pode e
   nao pode provar aqui: nesta fase o mercado **nao tem chamador dentro do scanner** [...]
   Entao 'os alertas de party continuam' e verdadeiro por **ausencia de acoplamento**: o
   scanner nem sabe que o registro existe."*

3. **No passo 5 do proprio roteiro**: *"Nesta fase isso e esperado **por construcao** — o passo
   existe para pegar uma regressao acidental, nao para provar a fiacao, que e da Fase 4."*

Confirmado mecanicamente: `montar_registro_de_mercado` tem **zero chamadores em `l2scanner/`**
(o unico chamador fora de teste e `tools/gerar_observacoes_do_censo.py:402`, que e bancada).
A prova de ponta a ponta e da Fase 4 — registrada em `deferred` no frontmatter, nao como gap.

### As tres divergencias declaradas pelo executor — as tres PROCEDEM

| # | Divergencia | Veredito | Razao |
|---|-------------|----------|-------|
| 1 | `Contagem` ganhou um TERCEIRO campo (`perdidas`), contra a letra do plano que pedia dois | **PROCEDE** | `registrar` devolve `False` por dois motivos distintos — chave repetida e registro DESLIGADO. Somar os dois faria o relatorio dizer "descartei 300 duplicadas" sobre uma sessao em que o disco encheu na terceira linha. Isso e exatamente o silencio que o PERS-03 proibe. Preso por `test_o_registro_DESLIGADO_conta_perdida_e_nunca_duplicada` |
| 2 | O codigo de saida da segunda rodada: nao-zero passa a significar "nao viu observacao NENHUMA", nao "nao gravou nada novo" | **PROCEDE, e era bug de contrato** | A leitura literal do plano faria o **passo 6 do proprio `<human-check>` do plano** — a prova de campo do PERS-02 — sair com erro exatamente quando desse certo, ensinando o usuario a ignorar o codigo de saida. A correcao poe o `<action>` de acordo com o `<human-check>` do MESMO plano |
| 3 | A conferencia de `l2scanner/` intocado foi feita contra o hash `61d789f`, e nao contra `git log --grep='03-02'` | **PROCEDE** | Reproduzido aqui: as mensagens de commit do 03-03 **citam** o 03-02 no corpo, entao `--grep` casa com commits do proprio 03-03. Nao e mudanca de codigo, e correcao de procedimento — e a mais honesta das tres, porque o executor podia ter usado o criterio errado e reportado verde |

### Escopo — nada da Fase 2, do `tiat` nem do `identidade` foi tocado

`git log --oneline c4a6172~1..HEAD -- <arquivo>`, contagem de commits:

| Arquivo | Commits no intervalo da Fase 3 |
|---------|-------------------------------|
| `l2scanner/rastreador.py` | **0** |
| `l2scanner/visao.py` (gate de brilho) | **0** |
| `l2scanner/respawn.py` | **0** |
| `l2scanner/bosses.py` | **0** |
| `l2scanner/agenda.py` | **0** |
| `l2scanner/sessao.py` | **0** |
| `config.toml` | **0** |

Diff acumulado do intervalo sobre `l2scanner/`, `tools/`, `tests/` — **3479 insercoes, ZERO
delecoes**, em 6 arquivos:

```
l2scanner/__main__.py                    |   78 ++     (so a funcao nova, aditiva)
l2scanner/mercado_registro.py            |  730 ++     (novo)
tests/test_gerar_observacoes_do_censo.py |  647 ++     (novo)
tests/test_mercado_leitura.py            |   17 ++     <- NAO e da Fase 3
tests/test_mercado_registro.py           | 1532 ++     (novo)
tools/gerar_observacoes_do_censo.py      |  475 ++     (novo)
```

`tests/test_mercado_leitura.py` foi tocado por `c4e73fe` — o **debug do `id()` reciclado**, que
fechou nesta sessao e e da Fase 2, nao desta fase. Rastreado por `git log -- <arquivo>`.

**`calibration.json` nunca commitado.** `git ls-files | grep -i calibration` devolve apenas
`.planning/estimation-calibration.json` (arquivo do GSD, nao a calibracao do scanner) e dois
markdown de planejamento. O `.gitignore` linha 45 tem `calibration.json`. Os seis
`calibration.*.json/.bak` do working tree aparecem em `git status` como **untracked**, e assim
ficam.

### Artefatos exigidos

| Artefato | Esperado | Status | Detalhe |
|----------|----------|--------|---------|
| `l2scanner/mercado_registro.py` | Registro, dedup, portao de contrato | ✓ VERIFIED | 730 linhas. Metade pura (`chave_da_observacao`, `campos_da_observacao`, `chave_dos_campos`, `residuo_dos_campos`) + metade de disco (`RegistroDeObservacoes`). Substantivo, sem stub |
| `montar_registro_de_mercado` em `__main__.py` | Tenta, degrada, devolve `None`, nunca levanta | ✓ VERIFIED (⚠️ sem chamador — POR DESENHO, declarado) | l. 468-543. Captura estreita `(OSError, ContratoDoArquivoQuebrado)`, dois `log.error`, `return None`. `test_nao_ha_raise_em_lugar_nenhum_da_montagem` por AST |
| `.mercado/LEIAME.txt` | Roteiro de importacao no Sheets | ✓ VERIFIED (como CODIGO; o arquivo so nasce quando o registro e construido) | `TEXTO_DO_LEIAME` + `escrever_leiame`, escrito UMA VEZ e nunca reescrito. 5 testes: separador Personalizado, centesimos com exemplo concreto, celula vazia vs zero, o sinal de `+` como pergunta em aberto, e `test_um_leiame_EDITADO_A_MAO_sobrevive_ao_proximo_arranque`. **`.mercado/` nao existe em disco — consistente: nao ha chamador ainda** |
| `tools/gerar_observacoes_do_censo.py` | Replay que produz o CSV real dos portoes | ✓ VERIFIED | 475 linhas. `razao_para_recusar_a_saida` (guarda pura, `resolve()` + `os.path.normcase`, roda ANTES do primeiro `mkdir`), `gravar_as_paginas`, `Contagem` de 3 campos, `main(argv)` |
| Dois roteiros humanos | Passo a passo executavel | ✓ VERIFIED | Dentro de `03-03-SUMMARY.md` (nao em arquivo proprio). Roteiro 1 = 6 passos (criterios 1, 2, 3); Roteiro 2 = 5 passos (criterio 5). Comandos literais, com o interpretador certo (`.venv/Scripts/python.exe`) e o aviso de rodar no checkout PRINCIPAL |

### Ligacoes-chave

| De | Para | Via | Status |
|----|------|-----|--------|
| `tools/gerar_observacoes_do_censo.py` | `l2scanner/__main__.py::montar_registro_de_mercado` | import direto, l. 78 / chamada l. 402 | ✓ WIRED — e por isso o texto do aviso que o usuario ve e byte a byte o da Fase 4 |
| `mercado_registro` | `mercado_catalogo` | `SEPARADOR` e `PASTA_DO_MERCADO` importados, nao redefinidos | ✓ WIRED, com teste |
| `mercado_registro` | `mercado_leitura.LinhaLida` | `TYPE_CHECKING` apenas | ✓ WIRED — `test_mercado_leitura_NAO_e_carregado_pelo_registro` prova que o registro nao arrasta cv2/numpy |
| `l2scanner` (scanner de party) | `montar_registro_de_mercado` | **NENHUMA** | ✓ ESPERADO — a ausencia E o mecanismo do PERS-03 nesta fase, declarada em 3 lugares |

### Fluxo de dados (Nivel 4)

| Valor no CSV | Origem | Dado real | Status |
|--------------|--------|-----------|--------|
| `chave_da_serie`, `nome_exibido` | `LinhaLida` da Fase 2, via `PaginaAceita` | Sim, via `LeitorDePagina` sobre `recordings/` | ✓ FLOWING (na bancada; em producao so na Fase 4) |
| `primeira_vez` | `Relogio.agora()` passado por PARAMETRO | Sim | ✓ FLOWING |
| `total_em_centesimos`, `quantidade` | leitura por molde de digito da Fase 2 | Sim | ✓ FLOWING |
| `residuo_do_cruzamento` | `LinhaLida.residuo_do_cruzamento` | Sim, `None` quando nao mediu | ✓ FLOWING |

Nenhum valor fixo, nenhum `return []` de fachada, nenhum mock no caminho de producao.

### Verificacoes comportamentais

| Comportamento | Comando | Resultado | Status |
|---------------|---------|-----------|--------|
| Os testes da fase passam | `pytest tests/test_mercado_registro.py tests/test_gerar_observacoes_do_censo.py -q` | **139 passed** em 1,92 s | ✓ PASS |
| T-03-01b (AST, `'truncate' not in nomes`) + a dedup do `WINDOWS.md` + o residuo `None`/`0` nos dois sentidos | `pytest -k "truncate or WINDOWS or MESMA_observacao or None_sai_VAZIO or a_volta_devolve"` | **4 passed** | ✓ PASS |
| Suite completa, sem o arquivo do flake conhecido | `pytest -q --ignore=tests/test_agenda.py` | **2819 passed, 2 skipped, 2 warnings** em 112 s, exit 0 | ✓ PASS |
| Varredura do censo (10 min) e ferramenta de replay | **NAO RODADO** | — | ? SKIP (instrucao operacional: e portao humano e pede o checkout principal) |

**Nota sobre a suite completa:** rodada UMA vez neste checkout, `--ignore=tests/test_agenda.py`
(o flake conhecido da linha 1141 levanta `KeyboardInterrupt` de proposito; abortar nao e
falhar). **Medido aqui, nao aceito do SUMMARY: `2819 passed, 2 skipped`, exit 0.** Bate com o
que a fase afirmou — **zero falhas** nos
modulos desta fase, que sao os que a fase pode ter quebrado. O `02-05-SUMMARY.md` ja foi
corrigido nesta sessao pelo debug do `id()` reciclado, entao a contagem antiga daquele arquivo
nao e mais a referencia.

### Cobertura de requisitos

| Requisito | Descricao | Status | Evidencia |
|-----------|-----------|--------|-----------|
| PERS-01 | Linhas num CSV com carimbo ancorado, legivel a olho e importavel no Sheets | ⚠️ CODIGO COMPLETO, PORTAO HUMANO ABERTO | Forma provada por teste; "legivel a olho" e "importavel" sao criterios 1 e 2 — Roteiro 1, passos 2 e 3 |
| PERS-02 | Dedup por chave de conteudo, conferida em memoria antes de escrever | ✓ SATISFIED (codigo); portao humano sobre material real | `if chave in self.chaves: return False` ANTES do `open`. A chave so entra no indice DEPOIS de a linha chegar ao disco — o comentario explica por que o contrario bloquearia para sempre a observacao correta |
| PERS-03 | Falha de escrita desliga so o mercado e avisa alto | ⚠️ METADE PROVADA | "Desliga e avisa alto": provado por teste (dois `log.error`, `ligado=False`, nunca levanta, sem retry). "Nunca derruba o nucleo": verdadeiro por ausencia de acoplamento — declarado, nao fingido. Fiacao real na Fase 4 |

**Nota:** `REQUIREMENTS.md` ja marca os tres como `[x] Complete`. Isso e **prematuro** enquanto
os portoes humanos estao abertos, mas nao e gap de codigo — e contabilidade. Vale corrigir para
`Complete (pendente portao humano)` ou deixar como esta ate o usuario aprovar os roteiros.

### Anti-padroes

| Arquivo | Padrao procurado | Achado |
|---------|-----------------|--------|
| `l2scanner/mercado_registro.py` | `TODO`/`FIXME`/`TBD`/`XXX`/`HACK`/`PLACEHOLDER` | **Nenhum** |
| `l2scanner/__main__.py` (trecho novo) | idem | **Nenhum** |
| `tools/gerar_observacoes_do_censo.py` | idem | **Nenhum** |
| todos | `return null`/`return []` de fachada, dado fixo | **Nenhum** — cada `return False` tem motivo escrito e teste |
| todos | `except Exception` largo | **Nenhum** — `test_nao_ha_except_largo_em_lugar_nenhum` (AST) e verde; a captura e `OSError` estreito, com os 4 modos medidos nomeados no comentario |

**Zero marcadores de debito.** A densidade de comentario-que-explica-o-porque (nao o-que) e a
mais alta do repositorio, e cada numero citado (`0,0037 ms` vs `1,5990 ms`, `5 de 5 cortes`,
`2 de 5 aprovados pela contagem`) esta ligado a uma medicao, nao a uma estimativa.

## O que falta, em ordem executavel

Tudo roda no **checkout PRINCIPAL** (`recordings/`, `calibration.json` e o motor de OCR nao se
materializam em worktree), com `.venv/Scripts/python.exe`.

1. **Produzir o arquivo** (~10 min, ou 1 min com `--gravacao 20260828-053105-mercado-aberto`):
   `.venv/Scripts/python.exe tools/gerar_observacoes_do_censo.py --saida C:/temp/portao-fase3`
   — anotar o numero de "observacoes GRAVADAS".

2. **Abrir no Bloco de Notas** (criterio 1) — entende as colunas? `6200` = `62,00`? sem coluna
   de unitario?

3. **Importar no Sheets** (criterio 2) — Arquivo > Importar > Enviar, separador **Personalizado**,
   digitar `;`. Nao existe opcao pronta de ponto-e-virgula na lista.

4. **Procurar um nome comecando em `+`** (o unico risco ALTO e NAO MEDIDO) — a celula mostra o
   nome ou um erro de formula?

5. **Olhar a coluna do residuo** — ha celulas VAZIAS e celulas com `0`, e elas continuam
   diferentes?

6. **Rodar de novo, mesma saida** (criterio 3) — zero gravadas, codigo de saida **0**, mesma
   contagem de linhas antes e depois.

7. **Quebrar a saida de proposito** (criterio 5) — arquivo ocupando o nome da pasta, depois
   `observacoes.csv` somente-leitura, depois cabecalho editado a mao. Duas linhas `ERROR` no
   console, sem traceback, e as mesmas duas em `logs/scanner.log`. **Desmarcar o somente-leitura
   no fim.**

8. **Subir o scanner normal** — nada mudou (esperado por construcao).

## Resumo

Nada esta faltando no codigo. **O que falta e o usuario acordar.**

A fase se defendeu bem exatamente onde o ceticismo apontou: o D-17 esta preso por AST e nao por
comentario; o `None`/`0` do residuo tem volta que mora no MODULO e nao no teste; o teste da
dedup NOMEIA a borda do `WINDOWS.md` com data e com a alternativa recusada; e o PERS-03 declara
a ausencia de acoplamento em tres lugares — no fonte, no cabecalho do roteiro e dentro do proprio
passo 5 — em vez de fingir cobertura. As tres divergencias do executor procedem, e a terceira
(o `--grep` que casava a mensagem errada) e a mais honesta, porque ele podia ter reportado verde
com o criterio errado.

---
*Verificado: 2026-08-31*
*Verificador: Claude (gsd-verifier)*


---

## OS PORTOES HUMANOS FECHARAM — 2026-09-01

Onze passos, todos exercitados. Os de terminal rodados por Claude na maquina do
usuario; os tres do Google Sheets por ele, com captura de tela conferida.

### Roteiro 1 — o arquivo, a importacao e a contagem

| Passo | Resultado |
|---|---|
| 1. Produzir o arquivo | Censo replayado: **159 paginas aceitas, 166 observacoes, 39 series** |
| 2. Abrir no editor | APROVADO pelo usuario — colunas legiveis, preco em centesimos, sem coluna de unitario |
| 3. Importacao real no Sheets | APROVADO — separador Personalizado `;`, seis colunas uma por coluna |
| 4. O sinal de mais (**risco ALTO, era NAO MEDIDO**) | **NAO se materializou.** `+3 Hunter's Breastplate` e `+5 Hunter's Gaiters` aparecem como TEXTO, nao como erro de formula. Conferido em captura de tela |
| 5. A coluna do residuo | **INSATISFAZIVEL com este material — ver achado abaixo** |
| 6. A contagem (dedup) | **APROVADO com prova mais forte que a pedida**: segunda rodada com zero observacoes novas, 1496 duplicadas descartadas, e o arquivo saiu com o **MESMO sha256** — byte a byte, nao so a mesma contagem |

### Roteiro 2 — o desligamento alto

| Passo | Resultado |
|---|---|
| 1. Pasta ocupada por arquivo | Duas linhas de erro na ordem certa, terceira da ferramenta, **zero traceback**, codigo 7 |
| 2. Arquivo somente-leitura | `MERCADO DESLIGADO — Permission denied`, sem traceback, codigo 7 — **ver achado abaixo** |
| 3. Cabecalho quebrado | Desligou alto e **nao alterou byte nenhum** (119 linhas antes e depois). A mensagem nomeia o esperado CONTRA o encontrado, diz que nada foi tocado e por que, e o que fazer para religar |
| 4. O log | As duas mensagens presentes em `logs/scanner.log` |
| 5. Scanner de pe | Party viva durante todo o exercicio, lendo os quatro membros |

### DOIS ACHADOS NO PROPRIO ROTEIRO

**1. O passo 2 do Roteiro 2 nao testava o que afirma.** Rodar a MESMA gravacao de
novo grava zero linhas (tudo duplicata), entao o arquivo somente-leitura nunca e
aberto para escrita e o passo fica verde sem exercitar nada. Refeito com uma
gravacao DIFERENTE — ai sim ele tentou escrever e desligou corretamente. **Quem
reescrever este roteiro precisa manter a gravacao diferente**, senao o passo volta
a ser vacuo.

**2. O passo 5 do Roteiro 1 e insatisfazivel com este material.** Ele pede para
conferir que existem celulas VAZIAS e celulas com `0` na coluna do residuo, e que
nao viraram a mesma coisa. Medido sobre as 166 observacoes do censo:

    VAZIO (nao deu para medir) : 0
    zero  (conferi e bateu)    : 127
    outro (residuo != 0)       : 39

**O censo nunca produz vazio.** A distincao EXISTE no codigo — `residuo_dos_campos`
faz campo vazio -> `None` e `"0"` -> `0`, "NUNCA um pelo outro", com teste de ida e
volta — mas nao ha como VE-LA nesta planilha. O passo cobra do usuario uma
observacao que o material nao contem.
