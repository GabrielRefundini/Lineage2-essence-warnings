# Phase 2: Aprender sozinho - Context

**Gathered:** 2026-08-31
**Workstream:** identidade
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — 4 areas, 9 decisoes

<domain>
## Phase Boundary

Uma linha OCUPADA cuja imagem de nome nao casa com nada conhecido deixa de ser
misterio permanente: o scanner grava a assinatura dela sozinho, depois de
estavel, sem calibracao e sem intervencao — e sem gravar a mesma pessoa duas
vezes.

DENTRO DA FASE: a decisao de que uma linha e candidata, a regra de estabilidade,
a gravacao no acervo da Fase 1, a entrada imediata da recem-aprendida no
reconhecimento vivo, e o diagnostico que torna a regra de estabilidade
AFERIVEL em campo.

FORA DA FASE: perguntar no WhatsApp (BATI-01, Fase 3), dar nome (BATI-02),
corrigir nome (BATI-05). Esta fase grava ANONIMO e continua CALADA. Nenhum
alerta novo sai dela, nem no console, nem no WhatsApp.

</domain>

<decisions>
## Implementation Decisions

### Area 1: Quando uma linha vira candidata

- **D-01. So e candidata a linha `COM_MEMBRO`, num frame com `ui_visivel`
  verdadeiro, e que produziu recorte de nome.** Cegueira nao ensina. O
  `ui_visivel` ja cai quando a moldura da barra some (outra janela por cima) e
  quando a party window aparece sem nenhum icone — os dois casos em que os
  pixels da linha nao sao a pessoa. Aprender sob cegueira gravaria a janela do
  navegador como se fosse gente, e a gravacao e IRREVERSIVEL: o acervo nao tem
  comando de esquecer no v1 (decisao da Fase 1).

- **D-02. So aprende quando o melhor casamento ficou ABAIXO de
  `LIMIAR_DE_CASAMENTO` (0.75). Falha por MARGEM nao aprende, cala.**

  Esta e a decisao que da corpo ao APRE-04, e ela e mais forte do que o
  requisito pede. "O casamento contra as ja gravadas vem antes" nao pode
  significar apenas RODAR antes: tem de VETAR. `identificar_linhas` devolve
  `Casamento(None, ...)` por DOIS motivos diferentes, e eles pedem desfechos
  opostos:

  | Motivo | O que significa | Aprender? |
  |---|---|---|
  | melhor pontuacao < 0.75 | "nao conheco ninguem parecido com isto" | SIM |
  | pontuacao >= 0.75, margem < 0.12 | "conheco DOIS parecidos demais" | NAO |

  Aprender no segundo caso e o pior desfecho que este workstream tem, e ele ja
  esta escrito na docstring de `acervo.carregar_identidades`: acrescentar ao
  acervo um quase-duplicado de alguem faz essa pessoa PARAR de ser reconhecida
  — as duas assinaturas se sombreiam e as duas caem no silencio pela margem. A
  medida da Fase 1: virando 8 celulas de uma mascara, a original casa 1.000 e a
  copia 0.921, diferenca 0.079, ABAIXO da margem de 0.12. Doze celulas ja
  quebram de vez.

  O dado necessario JA EXISTE e nao custa campo novo: `LeituraDeLinha` carrega
  `confianca_do_nome`, que e a melhor pontuacao. `nome is None and
  confianca_do_nome < LIMIAR_DE_CASAMENTO` e a condicao inteira.

- **D-03. A pessoa recem-gravada entra no reconhecimento VIVO no mesmo tick, e
  isso e o que fecha o criterio 5.**

  Gravada a assinatura, ela e acrescentada a lista que `identificar_linhas`
  recebe. Sem isso, a mesma pessoa voltaria a ser candidata no tick seguinte, e
  como o recorte muda por uma celula aqui e ali, ela geraria uma chave nova e
  uma entrada nova a cada N ticks — o acervo inchando com a MESMA pessoa, que e
  exatamente o que o APRE-04 proibe. Com ela na lista, o tick seguinte casa
  ~1.000 contra ela mesma e a linha deixa de ser candidata por D-02.

  Note que a dedupicacao real acontece AQUI, pela correlacao, e nao pela chave
  de conteudo. A chave e exata; a correlacao tolera ruido. E por isso que
  "sai da party e volta" (criterio 4) funciona mesmo com o recorte diferindo
  do gravado.

  O silencio continua valendo de graca: a assinatura entra com `nome=""`, e
  `Assinatura.anonima` ja foi desenhada na Fase 1 para que a string vazia caia
  por `linha.nome or f"#linha{N}"` sem uma linha de mudanca no rastreador.

### Area 2: O que "estavel por N leituras" quer dizer

- **D-04. A estabilidade e julgada sobre a MASCARA DE TEXTO, nunca sobre os
  pixels crus.** O texto do nome e opaco e o painel e semitransparente: o
  cenario que anda por tras muda os pixels crus a cada frame e nao muda a
  mascara. Julgar por pixel cru seria julgar o cenario, e o candidato nunca
  seria estavel num campo aberto de dia.

- **D-05. Duas leituras sao "a mesma" quando a distancia de Hamming entre as
  mascaras e no maximo `celulas_toleradas`, com DEFAULT 0** — ou seja, por
  padrao a mesma chave de conteudo, exatamente. A tolerancia e um numero de
  CELULAS porque e a unidade em que a unica medida que temos foi feita (8 e 12
  celulas), e comparar contra ela e comparar contra o perigo real.

  O default e 0 porque a fase nao tem medicao de campo do ruido entre frames
  consecutivos — nao existe gravacao multi-frame da party no repositorio, so
  imagens soltas. Adotar uma tolerancia inventada seria adotar exatamente o
  tipo de constante que este projeto proibe.

- **D-06. Ha um TETO DURO: `celulas_toleradas` tem de ficar estritamente abaixo
  da faixa em que duas mascaras deixam de ser a mesma pessoa para o
  reconhecedor.** Uma tolerancia maior chamaria de "estaveis" duas leituras que
  o proprio reconhecedor considera pessoas diferentes — e a assinatura gravada
  seria uma media de duas pessoas. O teto e derivado da medida da Fase 1, nao
  escolhido, e um valor acima dele e recusado no arranque, com mensagem.

- **D-07. A RECUSA POR INSTABILIDADE E REGISTRADA COM A DISTANCIA MEDIDA.**
  Esta e a peca que substitui uma ferramenta de spike. Se o default 0 nunca
  disparar em campo, o `scanner.log` da primeira sessao dira, com numero, o
  quanto as leituras diferem entre si — e o usuario sobe a tolerancia com um
  numero medido na mao, em vez de tentar valores.

  Sem isso, o desfecho de um default errado e a feature simplesmente nao
  acontecer, em silencio, sem nada no log dizendo por que. Com isso, o modo de
  falha da fase e AUTO-DIAGNOSTICO. E a razao de este item ser requisito de
  plano e nao "nice to have".

- **D-08. O contador de estabilidade e POR CONTEUDO, nunca por indice de
  linha.** A party window compacta quando alguem sai: a linha 2 de agora pode
  ser outra pessoa daqui a um tick. Um contador por indice somaria leituras de
  pessoas diferentes ate atingir N e gravaria uma assinatura de ninguem. Uma
  leitura que nao e "a mesma" que a anterior REINICIA a sequencia — nao a
  media, nao a mediana. Instabilidade e recusada, nao mediada (criterio 2).

### Area 3: Onde o aprendizado mora

- **D-09. Modulo novo, `l2scanner/aprendiz.py`, SEM RELOGIO, e ele entra na
  tupla `MODULOS` do portao AST de `tests/test_presenca.py`.** Contar leituras
  e nao segundos e deliberado: o tick nao e garantido e um "N segundos" viraria
  uma dependencia de relogio dentro da unica logica nova da fase. O aprendiz
  fala `Assinatura` e `AcervoDeIdentidades`, e nada mais — o mesmo isolamento
  que o `acervo` conquistou.

### Claude's Discretion

- O valor default de N leituras estaveis, e se ele e configuravel no
  `config.toml` ou constante do modulo com justificativa na docstring.
- Como o candidato chega ao aprendiz: campo novo na `Observacao`, retorno extra
  de `extrair`, ou colaborador passado. `Observacao` e `frozen=True` mas
  NENHUM teste compara observacoes com `==` (conferido: 71 usos, zero
  comparacoes), entao um campo com ndarray dentro nao quebra igualdade.
- Nome exato da classe do aprendiz e do campo de configuracao.
- Se a ferramenta autonoma de medicao (`tools/medir_...`) e escrita agora ou
  fica para depois do primeiro log de campo — o D-07 ja entrega o numero.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`l2scanner/acervo.py`** (Fase 1) — `AcervoDeIdentidades.gravar` ja e o
  tri-estado `criado | ja_existia | falhou`, com `O_CREAT|O_EXCL` para as duas
  instancias. A docstring dele ja ANTECIPA esta fase: "Colapsar `falhou` em
  `criado` faria a Fase 2 acreditar que aprendeu uma pessoa que nao esta em
  disco". O aprendiz tem de honrar isso: `falhou` NAO conta como aprendido, e a
  proxima passada tenta de novo.
- **`l2scanner/identidade.py`** — `criar_assinatura(nome, recorte)`,
  `mascara_de_texto`, `LIMIAR_DE_CASAMENTO = 0.75`,
  `MARGEM_MINIMA_SOBRE_O_SEGUNDO = 0.12`. Nada aqui muda nesta fase.
- **`l2scanner/visao.py:683`** — `identificar_linhas(recortes_de_nome,
  cal.assinaturas)` e o unico ponto onde os recortes existem. E de la que o
  candidato sai.
- **`l2scanner/rastreador.py:206`** — `_chave_da_linha` e
  `linha.nome or f"#linha{indice}"`. O silencio da recem-aprendida e HERDADO
  daqui pela string vazia; nao ha nada a acrescentar no rastreador.
- **`l2scanner/__main__.py:2020`** — `carregar_identidades(...)` no arranque, e
  `cal.assinaturas = identidades.assinaturas`. E a lista viva que o D-03
  precisa acrescer.

### Established Patterns

- **Tempo por parametro**, portao AST sobre `agenda`, `loot`, `presenca`,
  `bosses`, `respawn`, `acervo` — `aprendiz` entra na tupla.
- **Portugues SEM acento**; sem travessao em texto que o usuario le.
- **Docstrings explicam POR QUE, com medida de campo.**
- **Nenhuma dependencia nova.** Hamming sobre mascara e `numpy`, que ja esta.

### Integration Points

- `l2scanner/visao.py` — de onde vem o recorte do candidato
- `l2scanner/acervo.py` — onde a assinatura e gravada
- `l2scanner/__main__.py` — a lista viva de assinaturas e o laco
- `tests/test_presenca.py` — a tupla `MODULOS` do portao AST
- `config.toml` — se a tolerancia e o N virarem ajuste

</code_context>

<specifics>
## Specific Ideas

- O usuario roda DUAS instancias (Yazalaque e Faerlina) sobre a mesma pasta.
  As duas vao APRENDER agora, e nao so ler. O `O_EXCL` da Fase 1 ja cobre a
  corrida; o que a fase precisa garantir e que `ja_existia` seja tratado como
  sucesso, e nao como motivo para tentar de novo para sempre.
- O acervo e IRREVERSIVEL no v1: nao ha comando de esquecer. Toda decisao desta
  fase deve preferir NAO gravar quando ha duvida. Uma pessoa nao aprendida
  custa um "Membro N" no console; uma entrada de lixo gravada fica para sempre
  e ainda pode sombrear gente de verdade pela margem.

</specifics>

<deferred>
## Deferred Ideas

- Ferramenta autonoma de medicao do ruido entre frames. O D-07 entrega o mesmo
  numero pelo log da primeira sessao real, sem codigo novo.
- Comando para esquecer uma entrada (ja adiado na Fase 1).
- Perguntar no WhatsApp ao aprender — e a Fase 3 inteira (BATI-01).

</deferred>
