---
gsd_state_version: 1.0
milestone: v1-mercado
milestone_name: (não é regressão, é melhoria)
status: Awaiting next milestone
stopped_at: "Onda 2 da Fase 5 FECHADA — 05-02 e 05-03 em paralelo. 05-02: PORTAO DE PARADA NAO DISPAROU, 8 casas medidas com o limiar 0,73 intocado (negociacao 1,0000/1,0000/0,1331/-0,0027; adena 0,1331/0,1331/1,0000/-0,0029). ACHADO: o vao e SIMETRICO ate a decima casa, o que CORRIGE a suposicao A1 da pesquisa — casamento_da_ancora e correlacao normalizada, e correlacao normalizada e simetrica. busca fica FORA dos candidatos, e a exclusao e load-bearing: medida por mutacao, reintroduzi-la faz o veredito da janela de negociacao virar de negociacao para None, ou seja a pagina e RECUSADA. 05-03: a EXIBICAO da taxa em XM por milhao, com a conta RECALCULADA — 05-RESEARCH.md:621 erra por um fator de dez. A analise continua PURA e o CSV continua com SEIS colunas, e o ADEN-03 virou medicao com dois mutantes rodados. BUG DO SDK, terceira ocorrencia: state.advance-plan e state.record-session ESCREVEM no STATE.md mesmo devolvendo erro, corrompendo o progress do milestone ARQUIVADO. Restaurado nas tres vezes. state.update-progress e o unico que se recusa corretamente."
last_updated: "2026-09-01T18:05:00.000Z"
last_activity: 2026-09-01
last_activity_desc: Milestone v1-mercado completed and archived
state_head: 5a0b81c
progress:
  total_phases: 4
  completed_phases: 4
  total_plans: 21
  completed_plans: 21
  percent: 100
current_phase: 4
current_phase_name: Modo --mercado, analise e console
---

Total Phases: 4

# Project State

## Project Reference

**Core value:** Cada abertura do World Exchange vira coleta de dados — preços lidos passivamente da tela, sem nunca enviar input ao jogo.
**Current focus:** Phase 1 — Fundação — firewall, gravador e spike de campo
**Delivery decision (locked):** console-only na v1; comandos WhatsApp de mercado são v2.

## Current Position

Phase: Milestone v1-mercado complete
Plan: —
Status: Awaiting next milestone
Last activity: 2026-09-01 — Milestone v1-mercado completed and archived

## Accumulated Context

### Decisions

- F0 (firewall de escopo) dobrada na Fase 1: FIRE-01 é um teste de CI + Out of Scope já registrado; fase própria seria cerimônia (granularity: coarse)
- DETC-02 e LEIT-04 vivem na Fase 4: são a fiação do laço `--mercado` e a superfície de console, conforme a espinha da pesquisa
- Fase 3 paraleliza com a Fase 2: depende só do formato da página aceita, não da leitura pronta
- Slugs de fase levam prefixo `mercado-` para não colidir com o workstream default
- [Phase 1]: O log ALTO da falha de gravacao mora em gravador.py, nao em Sessao.tick: o modulo que possui a verdade do disco e o que reporta a mentira, e assim sessao.py fica byte-identico
- [Phase 1]: Contagem do disco usa is_file(): um diretorio com nome de PNG seria contado por um glob cru, reintroduzindo a mentira dentro da propria conferencia
- [Phase 1]: O firewall FIRE-01 prova o vermelho por mutacao e por dist-info fabricada; instalar uma banida de verdade num teste seria cometer o proprio pecado
- **[2026-08-29] PERSISTÊNCIA É CSV, NÃO SQLITE.** Decisão do usuário. O motivo que decidiu:
  ele quer ler o dado a olho nu, importar no Google Sheets e entregar para outra IA analisar
  — CSV serve os três, um `.db` não serve nenhum sem ferramenta no meio. Das três
  justificativas do SQLite, duas já tinham caído (só o Yazalaque escreve, então não há
  concorrência e a dedup cabe em memória) e a terceira estava dimensionada errada. Separador
  de campo `;`, porque a vírgula decimal travada colapsaria um CSV separado por vírgula.
  Reescrito em REQUIREMENTS.md e ROADMAP.md; a pesquisa está marcada como superseded nessa
  parte.

- **[2026-08-29] A calibração PROPÕE e o usuário confirma.** A ferramenta pedia ao humano
  para adivinhar o sentido de uma frase e aceitava calado o retângulo desenhado — violando a
  disciplina do próprio projeto, que mede em vez de supor. Agora cada retângulo vem
  pré-desenhado a partir de medição (`mercado_geometria.py`) e o ENTER confirma. Três
  defeitos que só o uso humano encontrou: instruções ambíguas, a mensagem final descrevendo
  uma imagem que não era a gravada (chip aberto), e a contagem de linhas truncando `447//45`
  em 9 — três pixels de erro de mão custavam um anúncio por página.

- [Phase 02]: A coluna do nome termina no rotulo `Quantity` do cabecalho, e nao no texto da pagina: medir pelo texto daria 263 px (os dez nomes do frame sao o mesmo item) e truncaria nome longo. Os 270 px do plano viraram PISO afirmado em teste; o medido e 324 px.
- [Phase 02]: O fim do icone do item sai da SATURACAO, com referencia medida nas colunas de numero da mesma linha. Maior-vao e Otsu foram TENTADOS e pousam no miolo escuro do icone (84-107 entre bordas de 193-255), devolvendo 22 onde a resposta e 42 — as duas refutacoes ficaram escritas na docstring de `_fim_do_icone`.
- [Phase 02]: As colunas de numero sao contadas A PARTIR DA DIREITA, com `Buy` de ancora: da esquerda a contagem quebra quando o icone e o nome se fundem (vao de 5 px em 063752/frame_000000 contra 13 px em pagina-cheia/frame_000010).
- [Phase 02]: As 3 ancoras gravadas no calibration.json sao NOVAS, recortadas de 063752/frame_000000, porque as originais do usuario foram apagadas pelo incidente da janela quebrada 13. Ele conferiu na imagem de conferencia e aprovou.
- [Phase 02]: Rotular linha limpa/coberta pela PASTA de origem foi REFUTADO por medicao — as 6 gravacoes "sem oclusao deliberada" contem tooltip (a pesquisa nomeia `scroll/frame_000084`), e com esse rotulo as populacoes se sobrepoem nos 214 trechos candidatos varridos. O rotulo passou a ser o GABARITO DE CAMPO nomeado frame a frame e linha a linha, em `tools/medir_oclusao.py`.
- [Phase 02]: Escolher o trecho da sonda por "menor dispersao mediana" tambem foi REFUTADO: o trecho de mediana zero rejeita 22,4% de TODAS as linhas de campo. A escolha e a MAIOR FOLGA RELATIVA contra o gabarito, e um candidato cuja pior limpa e exatamente 0 e descartado — a razao contra zero nao e medicao. Escolhido `x em [207, 417)` com folga 7,67x.
- [Phase 02]: O piso de LEITURA de glifo e 0,4698 e a margem 0,0370, MEDIDOS sobre 55.342 runs de 4.374 linhas. O limiar de COLISAO 0,8555 rejeitaria 39,4% dos glifos reais e a margem 0,12 herdada de identidade.py rejeitaria 26,7% — por isso os dois vivem em chaves proprias. A margem medida confirma de forma independente os 0,0370 do par `0`x`8` da pesquisa.
- [Phase 02]: A guarda de cruzamento `Total / Quantity` REPROVOU e ficou DESLIGADA (`mercado_tolerancia_do_cruzamento = None`): tolerancia 1273 centesimos por unidade contra o maximo 1,0, fechamento no limite derivado 0,6525, deteccao 0,0164 sobre 1.893 substituicoes `0`<->`8` injetadas. O 02-04 Task 4 le a linha `GUARDA REPROVADA por tolerancia, 1273.0000 centesimos por unidade (maximo 1.0)` e registra a refutacao em vez de ligar o mecanismo.
- [Phase 2]: [Phase 02]: A trava de digitos e o que torna o corte PROPONIVEL, e agora e numero: sem ela as populacoes se sobrepoem (vao -0,054416, 182 pares, '+6 Agathion' x 'Agathion' a 0,9492); com ela o vao e +0,022010. Corte 0,894737, piso 0,883732 (o MEIO do vao, nao o extremo — no extremo 'Wind Spirit Evolution Stone' ficaria permanentemente invisivel).
- [Phase 2]: [Phase 02]: A suposicao A8 esta REFUTADA. Com a posicao do digito dada DE FORA o molde acerta 9 de 9 contra o gabarito de encanto; com a regra de producao (cada run sozinho, digito quando passa no piso) acerta 0 de 10 e devolve '7655' onde a resposta e '6'. Os 13 moldes NAO TEM CLASSE DE REJEICAO: nao ha molde de letra. Ha vao entre digito verdadeiro (min 0,8510) e falso positivo (max 0,6947), mas o piso de hoje (0,4698, medido em colunas de NUMERO) nao separa.
- [Phase 2]: [Phase 02]: As duas populacoes de uma medicao tem de se apoiar na MESMA nocao de confianca. Aqui e o VOCABULARIO DE CONSENSO (50 nomes que as duas escalas leram identicos). Sem ele, '-ano' x '\ufffdano' (duas leituras FALHADAS) puxava o corte de 0,8947 para 0,7500, e leituras corrompidas por oclusao entravam como 'itens diferentes'.
- [Phase 2]: [Phase 02]: A rota 'ocr-igualdade' NAO cria as series duplicadas que a hipotese previa: ZERO nas 8 gravacoes. Ela recusa a linha antes de duplicar, e em troca perde 5 linhas a mais que 'ocr-estrito'. O argumento contra ela virou 'estritamente dominada', e nao 'suja o catalogo'.
- [Phase 2]: [Phase 02]: A FONTE da assinatura de digitos da chave da serie e o OCR (rota `ocr-estrito`), escolhida pelo usuario no portao do 02-03 em 2026-08-30. A `molde` caiu apesar dos 95,32% (A8 refutada: 0 de 10 sob a regra de producao; chave `7655` inutil num CSV que se le a olho); a `ocr-igualdade` caiu por dominancia estrita. Custo aceito: 8,86% das linhas caem, as vezes pagina inteira. Caminho de volta medido (vao +0,1563 entre 0,8510 e 0,6947) na docstring de assinatura_por_molde.
- [Phase 02]: [Phase 02]: A guarda de cruzamento foi CONSTRUIDA e ficou DESLIGADA, pela rota REPROVADA do 02-02 (`GUARDA REPROVADA por tolerancia, 1273.0000 centesimos por unidade (maximo 1.0)`, fechamento 0,6525, deteccao 0,0164). Ela degradou para OBSERVACAO: o residuo e calculado, guardado em `LinhaLida.residuo_do_cruzamento` e logado, e a refutacao esta escrita no fonte no padrao de `ocr.py:34-52`. Descartar dado bom com sinal nao provado faria da guarda o defeito.
- [Phase 02]: [Phase 02]: A TERCEIRA leitura de numero (a coluna do unitario) esta provada por CONTAGEM, e nao por existencia: linhas com `residuo_do_cruzamento` nao nulo == linhas lidas, 2/2 em f010 e 4/4 em f005. Sem esse criterio a guarda inteira seria codigo morto que todos os outros testes aprovariam, porque "nao opino" e resultado legitimo (T-02-39).
- [Phase 02]: [Phase 02]: MEDIDO nas fixturas e novo: o cliente parece TRUNCAR o unitario, e nao arredondar. Em f005 linha 5 a tela mostra `11,39` por 6 com unitario `1,89`, mas `1139/6 = 1,8983` arredondaria para `1,90`. O limite derivado dobraria (um centesimo por unidade em vez de meio), e o residuo de 5 daquela linha caberia. E mais uma explicacao para o fechamento de 0,6525 que reprovou a guarda; esta na docstring de `limite_derivado_do_cruzamento`.
- [Phase 02]: [Phase 02]: A guarda de cruzamento entra DEPOIS das tres celulas e da gramatica e ANTES do OCR — uma linha que ela derruba nunca vira dado, entao pagar ~7 ms de OCR por ela seria pagar por nada. Preso por teste: o descarte do cruzamento faz ZERO chamadas das duas escalas.
- [Phase 02]: A folga de cola do glifo foi MEDIDA em 1 e a guarda do run largo entrou em ler_glifos: 69 leituras erradas e plausiveis do censo viraram ZERO, e o rendimento subiu de 1135 para 1148 linhas completas — Um run mais largo que o maior molde de um caractere era casado contra UM molde e virava UM digito (44 lia 4, 149,44 lia 14,44), com score e margem que atravessavam as duas peneiras - a unica falha ABERTA da Fase 2, violando LEIT-02. O limite ficou DERIVADO dos moldes (max(largura)=6) e nao virou chave, porque uma copia gravada seria a segunda verdade sobre uma so geometria; o vale medido de quatro niveis (7 a 10 px, ZERO celulas aceitas) prova que a escolha dentro dele nao muda nada. So a folga de cola e livre, e por isso e a unica chave nova - medida pela varredura, com o balde LE ERRADO vazio nas duas populacoes rotuladas.
- [Phase 02]: A MEDICAO refutou duas afirmacoes do plano 02-08: afrouxar a folga nao inventa numero (folgas 2-4 leem IDENTICO a folga 1), e o pior caso da particao e 17x abaixo do tick e nao tres ordens de grandeza — particionar_run escolhe pelo PIOR segmento do corte, entao larguras permitidas a mais so acrescentam candidatos piores, que perdem - a sondagem do planejador previa 54 invencoes na variante D e mediu outra regra de escolha. A afirmacao 'a largura de corte decide entre conserto e invencao' e verdadeira sobre a ESCOLHA DO CORTE e falsa sobre a LARGURA PERMITIDA. O relogio: 9,02 ms medio e 60,16 ms no pior caso, contra o teto declarado de 200 ms - passa, mas com menos folga do que o plano supunha.
- [Phase 02]: O piso de brilho PROPRIO da coluna Quantity foi MEDIDO em 161 e PROPOSTO: LE CERTO 2133, NAO LE 114, LE ERRADO ZERO sobre 2247 celulas rotuladas do censo — E o ULTIMO PISO SEGURO com PASSO_DA_VARREDURA = 1, com a propria linha na tabela de candidatos e o balde LE ERRADO vazio. Folga (a) ate o primeiro piso que erra = 1; folga (b) ate o tronco remedido do 1 (V=174, e nao os 177 da sondagem) = 13. O rendimento da coluna foi de 541 para 2133, e o rotulo 1 (n=1680) foi de 0 para 1590. A REPROVA anterior caiu por REMOCAO DA CAUSA: as 14 celulas que sujavam o balde do piso compartilhado eram o glifo COLADO, consertado pelo 02-08.
- [Phase 2]: [Phase 02] O rendimento da Fase 2 esta MEDIDO e nao estimado: replay das 8 gravacoes NOMEADAS do censo, 517 frames, 478 ticks com painel aberto -> li 151, perdi 189, 7 vazias, 131 de outro layout, 1.007 linhas descartadas, 39 series distintas, ZERO frames congelados. Das 189 perdas, 136 (72%) sao o piso de posicoes comparadas (T-02-26) fazendo o trabalho para o qual foi medido, 34 sao o primeiro frame do par e 19 sao discordancia real.
- [Phase 2]: [Phase 02] O congelamento de captura roda ANTES da busca do painel, e a janela anterior e guardada por COPIA. A ordem: captura congelada e propriedade da CAPTURA e nao da pagina, e procurar o painel em pixels mortos produziria um voto 'aberto' convincente. A copia: um backend que reusa o proprio buffer produziria congelamento ETERNO sobre captura viva — o falso positivo exato que o detector existe para nao produzir, invertido.
- [Phase 2]: [Phase 02] A regra que decide se uma chave ausente desliga a leitura: mercado_minimo_de_linhas_comparadas ENTRA em _calibrado e mercado_folga_de_cola_do_glifo NAO. A ausencia da folga degrada para MAIS SEGURO (a celula com run largo cai fechada); a ausencia do piso degrada para o ACORDO TRIVIAL, que aceita como lida uma pagina em que quase nada atravessou. So a primeira pode sobreviver sem a chave.
- [Phase 2]: [Phase 02] REFUTADO por medicao no 02-05: 'linhas descartadas' NAO e sinonimo de 'linhas cobertas'. A gravacao scroll-transicao, escrita por mim como controle 'sem oclusao', descarta 6,30 linhas por frame contra 3,62 da gravacao de tooltip deliberado e 0,74 da de alvo-sobreposto. Durante a rolagem o fundo alternado esta em transicao e a sonda o le nao-uniforme: recusa legitima e fail-closed, mas nao oclusao. O teste falso saiu; as taxas medidas entraram no relatorio.
- [Phase 2]: [Phase 3] D-17 virou codigo: arquivo de observacoes que NAO termina em quebra de linha e CONTRATO QUEBRADO — a feature desliga alto, NADA e lido, e nenhum byte do arquivo do usuario e tocado. Medido: 5 de 5 cortes byte a byte recusados, contra 3 de 5 da contagem de campos. As duas saidas alternativas (truncar a cauda; completa-la com \n) estao refutadas por escrito no fonte e presas por AST
- [Phase 2]: [Phase 3] UM NUMERO QUE CAIU: o criterio de aceitacao 'cv2 e numpy ausentes de sys.modules apos importar mercado_registro' e IMPOSSIVEL — mercado_catalogo SOZINHO ja os traz, via .config -> .visao. Como importar dele e must-have da fase, as duas exigencias se contradiziam. Substituido pelo que mede a mesma intencao: o registro acrescenta EXATAMENTE UM modulo ao processo, e mercado_leitura fica fora de sys.modules
- [Phase 2]: [Phase 3] A montagem do mercado captura ContratoDoArquivoQuebrado AO LADO do OSError: divergencia de UM tipo com a regra da casa, justificada no fonte — contrato quebrado nao e falha de sistema de arquivos, mas o desfecho e o mesmo (feature desligada, scanner de pe). Sem ela a excecao subiria do arranque como traceback cru
- [Phase 2]: [Phase 3] O tipo de retorno de montar_registro_de_mercado NAO foi anotado, contra a letra do plano e a favor do vizinho: montar_vigia_do_mercado tambem nao anota, porque o tipo so existe atras do import ADIADO. Anotar deixaria um nome que typing.get_type_hints nao resolve, e resolve-lo exigiria um bloco TYPE_CHECKING no topo do __main__.py — arquivo disputado com o workstream tiat nesta wave
- [Phase 2]: [Phase 3] O LEIAME.txt e escrito UMA VEZ, na criacao da pasta, e NUNCA sobrescrito: e um texto para humano, na pasta do humano, e reescreve-lo a cada arranque apagaria a anotacao do usuario calado. As duas alternativas foram RECUSADAS com motivo — instrucao no topo do CSV quebraria o cabecalho-contrato e o Sheets a importaria como dado; coluna total_exibido seria dois campos para o mesmo fato
- [Phase 3]: 03-03: a recusa da pasta de producao como saida do replay e MECANICA — resolve() + os.path.normcase, comparando caminhos e nunca texto, e rodando antes do primeiro mkdir
- [Phase 3]: 03-03: o codigo de saida diferente de zero significa 'nao viu observacao nenhuma', e nao 'nao gravou nova' — a leitura literal do plano faria a segunda rodada (a prova de campo do PERS-02) reportar falha ao dar certo
- [Phase 3]: 03-03: a Contagem separa 'duplicada' de 'perdida' — registrar() devolve False por dois motivos, e somar os dois faria o relatorio afirmar dedup sobre uma feature morta
- [Phase 4]: O modo --mercado RECUSA a subir (codigo 2) quando falta OCR, calibracao ou o layout de negociacao: aqui a feature E o produto, ao contrario do scanner de party onde a montagem degrada para None
- [Phase 4]: `pecas_de_calibracao_de_mercado_faltando` e a verdade UNICA sobre "calibrado para mercado" — 15 chaves num lugar so (nao 14: `_calibrado` sempre conferiu 12, e os comentarios do 02-05/02-07 numeravam sem contar `mercado_grade`)
- [Phase 4]: `minimum_update_interval=250` so no mercado e a UNICA alavanca real de DETC-02; o padrao `None` da `JanelaSource` e o contrato que mantem o caminho da party byte-identico. 250 e ESCOLHA (margem de 4x contra o falso congelamento), nao medicao
- [Phase 4]: Um modulo do pacote NUNCA faz `from .__main__ import` — por `python -m` isso reexecuta o arranque sob outro nome de logger e as mensagens de erro saem para um logger sem manipulador. `_modulo_do_arranque()` resolve por `sys.modules['__main__']` com fallback
- [Phase 4]: Tripwire de arquitetura por AST (imports, `__module__` do namespace, codigo com docstring arrancada), e nao por substring no fonte cru — que reprovaria a propria documentacao do firewall
- [Phase 4]: O `rich` fica fora por DOUTRINA DE ZERO-INSTALL, e NAO pelo FIRE-01: a banlist do FIRE-01 e so de sintese de input. A justificativa errada do CONTEXT esta corrigida no fonte de `mercado_console.py`
- [Phase 4]: A analise NAO reescreve o CSV e nao tem um segundo parser: os portoes do terminador e do cabecalho viraram funcoes de modulo em `mercado_registro.py` e os metodos da classe delegam. Duas leituras divergentes reintroduziriam a truncagem parseavel (`80` virando `8`) que a Fase 3 gastou um plano inteiro para pegar. `tests/test_mercado_registro.py` seguiu verde sem uma edicao de expectativa — a prova de que a extracao foi refactor puro (04-02)
- [Phase 4]: O comparavel entre ofertas e `Fraction(total, quantidade)`, nunca `float`, e a mediana e `median_low` — as duas pela MESMA razao do D-02: um numero exibido tem de ter existido na tela. `median` de `n` par inventa meio centavo, exatamente como o unitario arredondado que a Fase 3 recusou guardar. Preso por `n=6` (par e acima do piso), afirmando que o valor esta na lista de entrada E difere de `statistics.median` (04-02)
- [Phase 4]: A tendencia roda sobre o ORDINAL das ofertas distintas, nunca sobre o carimbo. MEDIDO nesta sessao sobre dez ofertas em queda de 100 para 55: o ordinal devolve -42,86%, e o eixo do carimbo devolve inclinacao de -135.104 por segundo e percentual de -5e-7% — ele APAGA a queda e nao levanta `StatisticsError`. Os carimbos distam microssegundos porque `gravar_as_paginas` chama o relogio POR LINHA (04-02)
- [Phase 4]: Os pisos de evidencia (menor=1, mediana=5, tendencia=8) sao ESCOLHA declarada em constantes nomeadas no fonte, e NAO moram no `calibration.json`. Duas razoes escritas la: aquele arquivo e lido e nunca escrito por este modo, e estes numeros nao sao calibracao de pixel — sao julgamento de produto. Nenhum piso desse tipo foi medido; os numeros medidos que existem (151 lidas, 189 perdidas, 39 series) sao sobre a LEITURA (04-02)
- [Phase 4]: `unitario` recusa quantidade nao positiva e as agregacoes tiram essas ofertas da conta E do `n`. NAO estava no plano: o CSV e editado a mao no Sheets, `quantidade=0` passa em `chave_dos_campos` como inteiro valido e derrubaria o console, e quantidade NEGATIVA inverteria o sinal do unitario fazendo a oferta ganhar a disputa do menor pedido visivel (04-02)
- [Phase 4]: [Phase 4/04-03] A watchlist e FILTRO DE DESTAQUE e nunca porta de entrada: sem ela o console responde para as series com MAIS EVIDENCIA (SERIES_NO_TOPO=8, ESCOLHA), com ela as dela vem primeiro e MARCADAS e o resto continua visivel abaixo. Contraria a LETRA do criterio 3 do ROADMAP de proposito, e a divergencia esta escrita na docstring de ordenar_para_o_console. O casamento e EXATO sobre casefold + espacos colapsados, nunca fuzzy: +3 e +4 diferem em um caractere e sao series deliberadamente separadas.
- [Phase 4]: [Phase 4/04-03] ANAL-02: a ordem do tick e quatro passos NUMERADOS no laco — julgar contra o modelo COMO ELE ESTA, catalogo, registro, e so entao acrescentar (apenas com registrar()==True). O teste que a prende DISCRIMINA: cinco ofertas de unitarios 100..140 dao median_low=120 e a sexta muito barata levaria a mediana de seis para 110; o teste afirma PRIMEIRO que os dois numeros diferem. O CSV e lido UMA vez no arranque — reler a 1 Hz abriria corrida com o usuario editando no Sheets.
- [Phase 4]: [Phase 4/04-03] Dois criterios do plano REPROVAM e foram rodados como escritos, com o que discrimina acrescentado ao lado. (a) 'calibrar_mercado not in getsource(config)' ja reprovava na arvore PRISTINA — a unica ocorrencia e um comentario em 9dcccbf:791 que a restricao 3 do proprio plano proibe tocar; o que discrimina e a leitura dos imports pelo AST. (b) 'grep ultima_vez no console sem ocorrencia' e insatisfazivel junto do teste que o 04-02 travou exigindo essa mesma palavra na prosa; o que discrimina e a assercao sobre o CODIGO com docstrings arrancadas pelo AST, com controle negativo medido.
- [Phase 4]: [Phase 4] Casamento de nome DIGITADO pelo usuario e por igualdade EXATA sobre nome_normalizado, e a ambiguidade QUEBRA listando as candidatas. O corte calibrado de similaridade (0.8947) foi medido para agrupar duas leituras de OCR do MESMO pixel: aplicado a texto humano ele juntaria +3 x +4 Dragon Belt (0,9286), B-grade x C-grade Gemstone (0,9375) e Leonard x Leonarde (0,9333), e deixaria passar +3 Dragon Belt x Dragon Belt (0,88) — ele nao erra sempre, erra de forma imprevisivel
- [Phase 4]: [Phase 4] ReceitaInvalida e classe PROPRIA e a receita torta RECUSA O ARRANQUE, ao contrario da watchlist, cuja AgendaInvalida o laco CAPTURA de proposito. A assimetria tem razao: a watchlist so promove series no console e um erro nela nao pode custar a coleta da noite; a receita e uma CONTA, e uma conta torta que degradasse para 'sem margem' sairia calada
- [Phase 4]: [Phase 4] HORAS_PARA_MARCAR_COMPONENTE_VELHO = 24 ficou FORA do __all__ de mercado_analise, ao contrario dos pisos de evidencia. Com o nome na lista, o criterio de grep do plano (index + 900 chars) ancoraria no __all__ e a janela cairia no bloco dos pisos, que ja dizia ESCOLHA desde o 04-02: o criterio passaria com a constante muda. Fora da lista, index == rindex == 34615, medido
- [Phase 4]: 04-05: a mira do vigiar-mercado.bat vem da chave [jogo] personagem (com PERSONAGEM_PADRAO como ultimo recurso), e nao de --janela pelado — com DUAS instancias do jogo abertas e sem cal.janela, o --janela sem valor enumera, acha duas e RECUSA, e um lancador de dois cliques que morre pedindo linha de comando nao entrega DETC-02
- [Phase 4]: 04-05: os blocos de erro do vigiar-mercado.bat moram ACIMA da linha de execucao, com goto por cima. Isso torna ESTRUTURAL (e nao dependente de guarda lida a olho) a promessa de nao imprimir nada depois de o programa rodar — o defeito medido no calibrar-mercado.bat em 2026-08-28
- [Phase 4]: 04-05: os criterios da forma 'test -z $(git diff -- X)' ficam CEGOS depois do commit, e o de zero remocoes do config.toml vira FALSO NEGATIVO (cut -f2 sai vazio, e test vazio = 0 e falso). Medido nos dois estados, com controle negativo: a comparacao contra a base do plano (git diff <base>..HEAD -- X) e a unica que sobrevive ao commit
- [Phase 5]: A quantidade da Adena e DERIVADA das duas colunas de moeda (5.000.000 x round(total/incremento)), nao lida: a coluna Auction List nao se le com os moldes deste projeto em piso de brilho nenhum (varrido 180..250, None nas dez linhas da fixtura)
- [Phase 5]: O cruzamento e GUARDA na Adena e continua OBSERVACAO na negociacao. A comparacao e residuo <= limite_derivado_do_cruzamento(n), e o sinal e LOAD-BEARING: com < o caso legitimo 133,33/66,66 (residuo 1 contra limite 1,0) reprovaria
- [Phase 5]: A Adena e UMA serie so, com chave-sentinela adena# montada do SEPARADOR_DA_ASSINATURA (decisao do usuario): a chave derivada do nome faria a trava de digitos D-03 partir 5M/10M/15M em tres series e a mediana da taxa nasceria partida

### Blockers

- **Nenhum bloqueio ativo.** O portao do 02-03 fechou em 2026-08-30: o usuario escolheu
  `ocr-estrito`.

- O bloqueio da Fase 1 (só o usuário podia gravar o World
  Exchange) foi cumprido: 8 gravações feitas, spike respondido e validado seção por seção,
  calibração completa pela mão do usuário em 2026-08-29.

- JANELA 13 ABERTA: `l2scanner/calibrar.py` (calibracao de PARTY) apaga TODA a calibracao de mercado — `calibrar_selecionando` monta uma Calibracao do zero (calibrar.py:353) e o fluxo grava por cima do arquivo inteiro (calibrar.py:1244). Confirmado em campo 2026-08-30. Enquanto nao for consertado, recalibrar a party DE NOVO custa a calibracao de mercado outra vez. Resgate em calibration.RESGATE-13-glifos.json.
- ~~DECISAO PENDENTE (02-03 Task 2): a fonte da assinatura de digitos.~~ **RESOLVIDA em 2026-08-30: `ocr-estrito`.** O usuario aceitou o custo de 8,86% das linhas caindo (as vezes pagina inteira) para nao pagar uma chave `7655` que ele nao consegue ler no CSV. O caminho de volta da rota `molde` esta medido e escrito na docstring de `mercado_catalogo.assinatura_por_molde` (vao +0,1563, entre 0,8510 e 0,6947).
- VERIFICACAO HUMANA DE FIM DE FASE, o que nenhuma fixtura alcanca: (1) o OCR REAL com WinRT — o pytest roda no Python GLOBAL e injeta as leitoras, entao nenhum teste desta fase chamou o motor de verdade; a leitura de nome precisa ser conferida com o jogo aberto; (2) o congelamento de captura — frames_congelados = ZERO em todo o censo, e a borda de TRES so foi exercitada por fixtura sintetica: minimize a janela do jogo ou pause a captura e confira que o aviso alto sai e nenhuma pagina e aceita; (3) o rendimento 151/189 e um julgamento de produto — 72% das perdas sao o piso de 7 posicoes, e baixa-lo reabre o acordo trivial e exige varredura nova.
- [Phase 3, achado do 03-02] tests/test_mercado_leitura.py::TestOAcordoEntreAsDuasEscalas::test_as_duas_leitoras_sao_CHAMADAS_em_toda_linha_que_vira_LinhaLida esta VERMELHO no commit-base f03eee80, e falha TAMBEM em isolamento. Sem vinculo de import com o 03-02 (grep por __main__/mercado_registro no grafo de leitura devolve zero). A wave 1 mediu zero failed no base 0820587: ou algo entre os dois commits quebrou, ou a medicao nao alcancou o arquivo. Investigacao em deferred-items.md da fase

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|

### Verificação Diferida — Fase 2

| Fase | Estado | Retomar |
|------|--------|---------|
| 2 | verification_deferred_human | `/gsd-verify-work 2 --ws mercado` |

A Fase 2 fechou 8/8 planos e a verificação deu **`human_needed`, 2 de 3 critérios**. As duas
decisões de PRODUTO foram tomadas pelo usuário em 2026-08-30 (a borda 2×3 do congelamento é
aceitável; o rendimento 151/189 basta para a Fase 3 começar). **Sobram duas conferências que
só a mão dele fecha, e nenhuma bloqueia a Fase 3:**

1. **O OCR real dentro do tick.** O motor WinRT rodou de verdade na ferramenta de censo
   (`tools/medir_agrupamento_de_nome.py` chama `ocr.ler_texto` com portão `ocr.disponivel()`),
   e o replay prova que o recorte de produção é **byte-idêntico** ao que o motor leu — o
   casamento é por `ndarray.tobytes()`, então um pixel de diferença derrubaria toda linha. O
   que falta é o motor rodando DENTRO do laço, com o jogo aberto. Ninguém constrói
   `LeitorDePagina` em produção ainda; isso nasce na Fase 4.

2. **O congelamento provocado.** `frames_congelados = 0` em todo o censo, porque não existe
   gravação de captura travada. Minimizar a janela ou pausar a captura por 3+ ticks, e
   conferir que o aviso alto sai e nenhuma página nova é aceita.

### Corrida autônoma em curso — 2026-08-31 (madrugada)

O usuário foi dormir e autorizou execução autônoma das **Fases 3 e 4** do `v1-mercado`,
tomando as decisões recomendadas. Regras que valem até ele voltar:

- **PARAR antes de arquivar o milestone.** `audit-milestone` é leitura e pode rodar;
  `complete-milestone` e `cleanup` ficam para ele.

- **Outro agente trabalha no workstream `tiat` NESTA MESMA ÁRVORE, em paralelo.** Executores
  do mercado rodam em **worktree isolado** sempre que a task não precisar de `recordings/`
  nem do `calibration.json` (ambos gitignored, só no checkout principal). A Fase 3 não
  precisa — os testes dela usam `tmp_path`. **NUNCA usar `git commit --amend`**: hoje um
  amend caiu sobre commit alheio e precisou de `git reset --soft` para reparar.

- **Não abrir pergunta ao usuário.** Decisão recomendada é tomada e REGISTRADA com a razão.
- Contexto do orquestrador quase cheio: delegar, não explorar.

### Todos

- [ ] ~~**DEFINIR A `[mercado] watchlist` no `config.toml`**~~ — **DEIXOU DE SER BLOQUEIO
      em 2026-08-29** (quick `260829-rd9`). O motivo escrito aqui era o critério 1 da Fase 2,
      que dizia "todo item da watchlist visível é reconhecido" — esse critério foi substituído.
      LEIT-01 agora lê o nome por OCR e agrupa por similaridade; item desconhecido vira série
      nova sozinho. A watchlist não é mais a porta de entrada do que é registrado. Se
      sobreviver, é como filtro de DESTAQUE no console (Fase 4). Fecha a janela quebrada 12.

- [ ] Registrar/atualizar a discrepância de docs: CLAUDE.md diz Python 3.13, venv real é 3.12.10 (não bloqueia)

### Fatos operacionais que só existiam na conversa

- **FLAKE CONHECIDO, PRÉ-EXISTENTE:** `tests/test_agenda.py` vaza um `KeyboardInterrupt` que
  aborta a sessão inteira do pytest perto de ~88 testes. Medido: 5 abortos em 60 rodadas,
  reproduzido em commit anterior a todo o trabalho do mercado. **Abortar não é falhar** —
  rode de novo. Baseline verde nesta árvore em 2026-08-30, depois do 02-02:
  **1934 passed, 2 skipped** (1881 antes dos 53 testes novos do 02-02).

- **pytest roda no Python GLOBAL, não no `.venv`** (o venv não tem pytest). Isso é
  load-bearing para o firewall FIRE-01, que por isso varre três lugares.

- **`calibration.json` é gitignored** — estado de máquina, nunca commitado. Hoje carrega:
  3 âncoras, grade de 10 linhas de 45 px em layout **`negociacao`** (deslocamento
  `dx=-427 dy=256`), geometria 1720x1392, **13 moldes de glifo completos**
  (`0-9`, `,`, `XM Coin`, `Adena`), as quatro colunas e o molde do cabeçalho (02-01), e
  os **seis números medidos pelo 02-02**: `mercado_sonda_do_fundo`
  `{dx0: 207, dx1: 417, folga: 2}`, `mercado_limiar_de_dispersao_do_fundo` 0.026377,
  `mercado_minimo_de_linhas_comparadas` 7, `mercado_limiar_de_leitura_de_glifo` 0.469831,
  `mercado_margem_de_leitura_de_glifo` 0.036984, e `mercado_tolerancia_do_cruzamento`
  **`None`** (guarda REPROVADA e desligada de propósito). `mercado_templates_de_nome` e
  `mercado_limiar_de_template` continuam `null` — sem número inventado.

- **Recordings ficam só no checkout principal** (gitignored). Um executor em worktree tem de
  lê-los por caminho absoluto, somente leitura.

- **Worktree:** `worktree.baseRef: "head"` fixado em `.claude/settings.local.json` porque o
  repo não tem remote — sem isso o `base-check` degrada para execução sequencial (#683).

## Session Continuity

**Last session:** 2026-09-01T16:04:33.490Z

**Stopped At:** Completed 05-02-PLAN.md (onda 2 da Fase 5). PORTAO DE PARADA NAO DISPAROU: 8 casas medidas, limiar 0,73 intocado. Molde negociacao 1,0000/1,0000/0,1331/-0,0027 e molde adena 0,1331/0,1331/1,0000/-0,0029 sobre goods/unitprice/adena/busca. ACHADO: o vao e SIMETRICO (0,1331 nos dois sentidos), o que CORRIGE a suposicao A1 da pesquisa. mercado_layouts entra OPCIONAL com VERSAO_DO_ESQUEMA em 2 e a lista das quinze sem crescer. busca fica FORA dos candidatos (derivados do registro de leitoras): MEDIDO por mutacao, reintroduzi-la faz o veredito da janela de negociacao virar de negociacao para None. janela_adena_f014.png da 9 linhas com sentinela adena#, linha 5 cai por cruzamento, zero OCR. Suite 4144 passed + 24 skipped, base do worktree 4077 + 24: +67, 0 regressoes. calibration.json e .mercado/ intocados, nenhuma dependencia nova, rastreador.py e visao.py nao tocados. NAO FEITO de proposito: requirements.mark-complete de ADEN-01/ADEN-02, tambem reivindicados pelo 05-04.
**Resume File:** None
**Next:** `/gsd-plan-phase 1` (workstream mercado) após aprovação

## Performance Metrics

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 1 P1 | 8 min | 3 tasks | 4 files |
| Phase 02 P01 | 8h 14m | 3 tasks | 9 files |
| Phase 02 P02 | 1h 25m | 2 tasks | 12 files |
| Phase 02 P03 | 1h 45m | 1 tasks | 8 files |
| Phase 02 P04 | 3h 25m | 3 tasks | 18 files |
| Phase 02 P06 | 25 min | 1 tasks | 5 files |
| Phase 02 P08 | 95 min | 2 tasks | 14 files |
| Phase 02 P07 | 1h 8m | 2 tasks | 10 files |
| Phase 02 P05 | 105 min | 3 tasks | 7 files |
| Phase 03 P01 | 18min | 3 tasks | 2 files |
| Phase 03 P02 | 18min | 2 tasks | 5 files |
| Phase 03 P03 | 9min | 2 tasks | 2 files |
| Phase 4 P01 | 16min | 3 tasks | 9 files |
| Phase 4 P02 | 11min | 3 tasks | 3 files |
| Phase 4 P3 | 34min | 3 tasks | 6 files |
| Phase 4 P4 | 18m | 3 tasks | 5 files |
| Phase 04 P05 | 30min | 2 tasks | 3 files |
| Phase 05 P01 | 17 | 2 tasks | 3 files |

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone

## Deferred Items

Itens reconhecidos e adiados no fechamento do milestone, mais recentes primeiro:

| Categoria | Item | Estado | Adiado em | Milestone |
|---|---|---|---|---|
| deferred_items | Fase 04: a cadeia de import `mercado_catalogo` -> `config` -> `notificador` -> `rastreador` | **ABERTO, nao suprimido** | 2026-09-01 | v1-mercado |
| debug_sessions | knowledge-base | falso positivo do scanner | 2026-09-01 | v1-mercado |
| quick_tasks | 5 quicks sem SUMMARY.md | convencao do workstream (PLAN + codigo) | 2026-09-01 | v1-mercado |

**Sobre o primeiro:** o CLI `audit-open acknowledge` RECUSOU suprimi-lo — o
`deferred-items.md` usa a forma delimitada por cabecalho (#3457), fora do que o
escritor suporta. Tentei marcar a mao com comentario HTML e o scanner nao o le.
Removi o marcador falso: **um marcador que afirma suprimir e nao suprime e pior que
nenhum.** O item fecha o milestone DECLARADO ABERTO, e esta carregado para o v2
pelo REQUIREMENTS de la, que nao depende deste registro para existir.

**Known verification overrides:** 0 recem-reconhecidos que importem para o
veredito, 6 carregados de reconhecimentos desta mesma sessao, 1 ABERTO e
declarado. As quatro fases fecharam `verified_closeout` (todas
`phase_complete=true` e `verification_status=passed`).
