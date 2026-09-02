---
phase: quick-260902-pqf
plan: 01
type: execute
wave: 1
quick_id: 260902-pqf
base_commit: 33ebb56
depends_on: []
files_modified:
  - l2scanner/mercado_leitura.py
  - l2scanner/mercado_pagina.py
  - l2scanner/mercado_analise.py
  - l2scanner/mercado_modo.py
  - tests/test_mercado_leitura.py
  - tests/test_mercado_adena.py
  - tests/test_mercado_ciano.py
  - tests/test_mercado_modo.py
autonomous: true
requirements: [LEIT-04, ANAL-02]

estimate:
  tokens: 95000
  raw_tokens: 95000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - "Uma oferta parada na tela produz UMA linha `RECUSADA` no log por sessao, e nao uma por tick."
    - "A supressao e do LOG e nunca do dado: os cinco ticks continuam devolvendo cinco `Descarte`."
    - "Duas linhas DIFERENTES recusadas pelo mesmo motivo continuam saindo as duas."
    - "As quatro ofertas de uma pagina sao julgadas contra a MESMA mediana e o MESMO n."
    - "A mesma pagina em duas ordens diferentes anuncia exatamente os mesmos textos."
    - "A docstring de `_recusar` diz o custo medido, e nao mais que a repeticao e decisao."
  artifacts:
    - "l2scanner/mercado_leitura.py::TravaDaRecusa"
    - "l2scanner/mercado_analise.py::ModeloDeMercado.vereditos_da_pagina"
    - "l2scanner/mercado_modo.py::processar_a_pagina_aceita"
  key_links:
    - "LeitorDePagina.trava_da_recusa -> ler_linha / ler_linha_de_adena -> _recusar"
    - "laco_do_mercado -> processar_a_pagina_aceita -> ModeloDeMercado.vereditos_da_pagina"
---

<objective>
Dois defeitos de RUIDO vistos hoje em producao (2026-09-02 18:27), e nenhum deles e
falha de leitura: a recusa sai sem trava a 1 Hz e afoga o `scanner.log` rotativo, e a
mediana de referencia se move POR DENTRO da pagina, fazendo o destaque depender da
posicao da linha na grade.

Purpose: o log rotativo e a unica ferramenta de forense pos-farm deste projeto, e o
destaque e a unica resposta que o modo da em tempo real. Os dois estao mentindo — um por
volume, o outro por ordem.

Output: uma setima trava (`TravaDaRecusa`), uma referencia CONGELADA por pagina
(`vereditos_da_pagina`), e a extracao que torna a segunda mensuravel.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@.planning/workstreams/mercado/STATE.md
@.claude/CLAUDE.md
@l2scanner/mercado_leitura.py
@l2scanner/mercado_pagina.py
@l2scanner/mercado_analise.py
@l2scanner/mercado_modo.py
</context>

<restricoes_inegociaveis>
Estas valem para as DUAS tasks. Violar qualquer uma invalida o plano inteiro.

- NAO tocar no criterio `median_low`. Um numero exibido tem de ter existido na tela.
- NAO tocar em `mercado_minimo_de_linhas_comparadas` (7).
- NAO afrouxar o corte de similaridade (0,8947), o piso (0,8837), a trava de digitos
  (D-03), a trava de palavra (D-09) nem a letra de grade na assinatura.
- NAO ligar `mercado_tolerancia_do_cruzamento` — continua `None`.
- NUNCA commitar `calibration.json` (gitignored, estado de maquina).
- NUNCA escrever em `.mercado/` — dado de producao do usuario, VIVO neste momento. Todo
  teste usa `tmp_path`.
- `recordings/` e somente leitura e NUNCA por glob amplo.
- NENHUMA dependencia nova, e JAMAIS uma biblioteca de sintese de input.
- NAO tocar em `l2scanner/rastreador.py` nem no portao da propria barra em
  `l2scanner/visao.py`.
- NAO tocar nos arquivos do agente paralelo: `respawn.py`, `bosses.py`, `agenda.py`,
  `sessao.py`, `test_bosses.py`, `identidade.py`, `discord/`, `dashboard.py`, `renda*`.
- NUNCA `git commit --amend`, NUNCA `git stash`. NAO mexer em `VERSAO_DO_ESQUEMA` (2).
- Comentarios e mensagens de commit em portugues, na voz do modulo vizinho.
- O vigia do mercado esta RODANDO na maquina do usuario. Nao matar, nao reiniciar.
- A suite ABORTA em `tests/test_agenda.py:1231` (KeyboardInterrupt deliberado,
  pre-existente, area de outro agente). Rodar SEMPRE
  `python -m pytest -q --ignore=tests/test_agenda.py`. Base: **4865 passed, 29 skipped**.
- CUIDADO COM O HOMONIMO: existe `mercado_modo._recusar` (recusa de ARRANQUE, recebe uma
  lista de linhas) e existe `mercado_leitura._recusar` (recusa de LINHA). A Task 1 mexe
  SO no segundo.
</restricoes_inegociaveis>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: A setima trava — a recusa fala UMA vez por linha e por sessao</name>

  <files>
l2scanner/mercado_leitura.py,
l2scanner/mercado_pagina.py,
tests/test_mercado_leitura.py,
tests/test_mercado_adena.py,
tests/test_mercado_ciano.py
  </files>

  <read_first>
- `l2scanner/mercado_leitura.py:1576-1655` — `TravaDaObservacao` inteira. E o molde: conjunto
  publico, `anunciar` devolvendo o TEXTO, identidade sem o indice, da SESSAO.
- `l2scanner/mercado_leitura.py:2540-2552` — `_recusar` como esta hoje.
- `l2scanner/mercado_console.py:381-446` — `TravaDoDestaque`, a doutrina em prosa.
- `l2scanner/mercado_pagina.py:636-648` — onde `trava_da_observacao` nasce no leitor.
- `l2scanner/mercado_pagina.py:1036-1097` — os DOIS ramos de `_ler_a_pagina` (adena e
  negociacao), que sao os dois pontos por onde a trava nova tem de descer.
- `tests/test_mercado_leitura.py:1071-1120` — o helper `chamar_ler_linha` e a convencao
  "trava omitida vira uma trava NOVA".
- `tests/test_mercado_leitura.py:2049-2270` — a classe de testes de `TravaDaObservacao`,
  incluindo `test_o_leitor_PASSA_A_SUA_trava_a_cada_ler_linha`. Espelhar, nao reinventar.
  </read_first>

  <behavior>
Escrever estes testes ANTES da implementacao, todos em `tests/test_mercado_leitura.py`,
numa classe nova `TestATravaDaRecusa`:

- Teste 1 (O NUMERO DO DEFEITO): cinco chamadas com a MESMA trava, o MESMO indice e a
  MESMA linha recusada -> `caplog` tem EXATAMENTE 1 registro com `RECUSADA` no texto.
  Controle negativo na MESMA funcao de teste: cinco chamadas com trava NOVA a cada
  volta -> EXATAMENTE 5 registros. Os dois numeros no mesmo teste, porque um sozinho nao
  discrimina entre "travou" e "parou de logar".
- Teste 2 (A SUPRESSAO E DO LOG E NUNCA DO DADO): as mesmas cinco chamadas com a MESMA
  trava devolvem CINCO `Descarte`, todos com o mesmo `motivo`, enquanto o log tem 1.
  Sem este teste a trava poderia estar engolindo a linha e a suite aprovaria.
- Teste 3 (O INDICE ESTA NA CHAVE, E E DELIBERADO): na MESMA trava, recusar o indice 3 e
  o indice 7 pelo MESMO motivo e com o MESMO detalhe -> DOIS registros. E recusar o
  indice 5 cinco vezes -> UM. As duas afirmacoes juntas, porque e a divergencia contra
  `TravaDaObservacao` que este teste existe para fixar.
- Teste 4 (A TRAVA QUE CHEGA E A DO LEITOR, MEDIDA POR CHAMADA): espelhar
  `test_o_leitor_PASSA_A_SUA_trava_a_cada_ler_linha` — monkeypatch em
  `mercado_pagina.ler_linha` coletando `kwargs["trava_da_recusa"]`, rodar
  `LeitorDePagina.observar`, afirmar que houve ao menos UMA chamada e que TODAS
  receberam `leitor.trava_da_recusa` por identidade (`is`). Repetir para
  `ler_linha_de_adena` no ramo da adena.
- Teste 5 (A DOCSTRING FOI CORRIGIDA): `inspect.getdoc(_recusar)` cita `TravaDaRecusa`,
  cita `3.600` e cita `2026-09-02`.
  </behavior>

  <action>
Implementar a trava depois de os cinco testes estarem VERMELHOS.

1. `TravaDaRecusa` em `l2scanner/mercado_leitura.py`, colada LOGO DEPOIS de
   `TravaDaObservacao` — as duas tem de se ler como irmas na mesma tela.
   - `__init__` cria `self.ja_recusadas: set[tuple[int, str, str]] = set()`, PUBLICO,
     no padrao de `ja_observadas` e `ja_anunciadas`.
   - `anunciar(self, indice: int, motivo: str, detalhe: str) -> str | None`: monta
     `chave = (int(indice), motivo, detalhe)`; se ja esta no conjunto devolve `None`;
     senao acrescenta e devolve o texto
     `f"linha {indice} RECUSADA ({motivo}): {detalhe}"`.
   - O TEXTO E BYTE-IDENTICO ao que `log.warning` renderiza hoje. Ha teste vivo lendo
     essa string em `tests/test_mercado_leitura.py:1654`; mudar a forma quebraria
     forense de campo por nada.
   - `None` e nao string vazia, pela razao ja escrita nas duas irmas.
   - Docstring obrigatoria, na voz das vizinhas, dizendo:
     (a) o defeito medido: producao 2026-09-02 18:27, a linha 5 recusada pelo motivo do
     cruzamento uma vez por segundo, com `total=11999 incremento=5949 n=2 residuo=101` —
     a 1 Hz sao ~3.600 linhas por hora num log ROTATIVO;
     (b) que ela e a SETIMA trava do modo e a QUINTA do leitor: conte nomeando
     `transicao_do_painel`, `_layout_ja_recusado`, `_congelamento_ja_avisado`,
     `_falta_ja_avisada`, `TravaDoDestaque`, `TravaDaObservacao`;
     (c) POR QUE O INDICE ENTRA NA CHAVE AQUI e sai na de `TravaDaObservacao`: la a
     identidade da oferta existe nos tres numeros; aqui o `detalhe` de metade dos motivos
     nao carrega identidade nenhuma (o do motivo da oclusao e a mesma frase constante em
     toda linha), e sem o indice a primeira linha coberta calaria todas as outras da
     sessao. O custo esta limitado e escrito: uma rolagem reanuncia a oferta no maximo
     uma vez por posicao da grade — dez linhas contra 3.600 por hora;
     (d) que ela e da SESSAO e nao uma janela de tempo, e que o conjunto NAO e podado,
     pelas mesmas razoes das irmas;
     (e) que ela trava o LOG e nunca o `Descarte` — o dado recusado continua recusado
     em todo tick.

2. `_recusar` ganha um quarto parametro POSICIONAL e obrigatorio:
   `_recusar(indice: int, motivo: str, detalhe: str, trava: TravaDaRecusa) -> Descarte`.
   Sem valor de fabrica, pelo charter do modulo — um default esconderia quem forneceu a
   trava e devolveria o defeito inteiro em silencio. O corpo vira: pedir o texto a trava,
   `log.warning("%s", texto)` SO quando o texto nao for `None`, e devolver
   `Descarte(indice=indice, motivo=motivo)` SEMPRE.

3. Reescrever a docstring de `_recusar`. A razao dos delimitadores `>>><<<` FICA
   (espaco em branco importa). A frase que hoje trata a repeticao como decisao SAI e da
   lugar ao custo medido: 2026-09-02 18:27, ~3.600 linhas por hora, e o nome
   `TravaDaRecusa`. Escrever tambem que a supressao alcanca so o log — o `Descarte`
   continua saindo em todo tick, e e por isso que a contagem "li 7, perdi 3" do console
   nao muda de valor nenhum.

4. Descer a trava ate os quinze pontos de chamada:
   - `ler_linha` ganha `trava_da_recusa: TravaDaRecusa` como keyword-only SEM default,
     ao lado de `trava_da_observacao`. Documentar no docstring, na mesma prosa que ja
     explica por que a trava da observacao chega de fora.
   - `ler_linha_de_adena` ganha o mesmo parametro keyword-only sem default. Ela nao tem
     `trava_da_observacao` (a guarda do cruzamento la e GUARDA, nao observacao), e essa
     assimetria continua — a trava nova entra nas DUAS porque as duas recusam.
   - `_ler_o_nome` ganha o parametro e o repassa nos seus tres pontos de recusa.
   - Atualizar TODAS as chamadas de `_recusar` nos tres corpos.
5. `LeitorDePagina.__init__` (`l2scanner/mercado_pagina.py`) cria
   `self.trava_da_recusa = TravaDaRecusa()`, publica, colada ao lado de
   `self.trava_da_observacao`, com comentario curto dizendo que ela e a QUINTA do leitor
   e por que mora aqui e nao dentro do laco de linhas. Importar `TravaDaRecusa` no bloco
   de import que ja traz `TravaDaObservacao`. `_ler_a_pagina` passa
   `trava_da_recusa=self.trava_da_recusa` nos DOIS ramos (adena e negociacao) — o ramo
   esquecido seria metade do defeito de volta.

6. Consertar os helpers e as chamadas diretas nos testes, seguindo a convencao que ja
   existe: parametro `trava_da_recusa=None` vira uma trava NOVA por chamada, que e o
   equivalente de "um tick isolado". Sao `tests/test_mercado_leitura.py:1071`
   (`chamar_ler_linha`), `tests/test_mercado_adena.py:183`
   (`chamar_ler_linha_da_adena`) e as quatro chamadas diretas em
   `tests/test_mercado_ciano.py` (linhas ~422, ~471, ~1108, ~1224).
  </action>

  <verify>
    <automated>
python -m pytest -q --ignore=tests/test_agenda.py tests/test_mercado_leitura.py tests/test_mercado_adena.py tests/test_mercado_ciano.py tests/test_mercado_pagina.py tests/test_mercado_adena_pagina.py -x
    </automated>
    <automated>
python -m pytest -q --ignore=tests/test_agenda.py -k "TestATravaDaRecusa" -v
    </automated>
    <automated>
python -c "import inspect, l2scanner.mercado_leitura as m; d=inspect.getdoc(m._recusar); assert 'TravaDaRecusa' in d and '3.600' in d and '2026-09-02' in d, d; assert 'sem rate-limit' not in d, 'a frase antiga sobreviveu'; print('docstring OK')"
    </automated>
    <automated>
python -c "import inspect, l2scanner.mercado_leitura as m; p=inspect.signature(m.ler_linha).parameters; q=inspect.signature(m.ler_linha_de_adena).parameters; assert p['trava_da_recusa'].default is inspect.Parameter.empty; assert q['trava_da_recusa'].default is inspect.Parameter.empty; print('sem valor de fabrica nas duas')"
    </automated>
    <automated>
python -m pytest -q --ignore=tests/test_agenda.py
    </automated>
  </verify>

  <prova_por_mutacao>
OBRIGATORIA e nao opcional. Depois de a task estar VERDE:

1. Em `TravaDaRecusa.anunciar`, apagar as duas linhas do portao
   (`if chave in self.ja_recusadas: return None`), deixando-a sempre devolver o texto.
2. Rodar `python -m pytest -q --ignore=tests/test_agenda.py -k "TestATravaDaRecusa"`.
3. Confirmar VERMELHO nos Testes 1 e 3, e VERDE no Teste 2 (o dado nunca dependeu da
   trava — se o Teste 2 ficar vermelho aqui, a implementacao esta engolindo `Descarte` e
   isso e um segundo defeito).
4. COPIAR A LINHA DE RESUMO DO PYTEST VERBATIM para o corpo do commit.
5. Reverter a mutacao e reconfirmar o verde.
  </prova_por_mutacao>

  <done>
- Cinco ticks da MESMA linha recusada = 1 registro no log e 5 `Descarte`. Medido, nao afirmado.
- Cinco ticks com trava NOVA a cada volta = 5 registros. Controle negativo no mesmo teste.
- Indice 3 e indice 7, mesmo motivo e mesmo detalhe, mesma trava = 2 registros.
- Toda chamada de `ler_linha` e de `ler_linha_de_adena` dentro de um `observar` recebe
  `leitor.trava_da_recusa` por identidade, e o teste afirma que houve ao menos uma chamada.
- `inspect.getdoc(mercado_leitura._recusar)` contem `TravaDaRecusa`, `3.600` e
  `2026-09-02`, e NAO contem mais a frase `sem rate-limit`.
- `trava_da_recusa` nao tem valor de fabrica em nenhuma das duas leitoras.
- Suite completa sem regressao contra a base **4865 passed, 29 skipped**.
- A prova por mutacao rodou e o resumo do pytest esta no commit.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: A mediana CONGELADA por pagina — o anuncio para de depender da ordem da linha</name>

  <files>
l2scanner/mercado_analise.py,
l2scanner/mercado_modo.py,
tests/test_mercado_modo.py
  </files>

  <read_first>
- `l2scanner/mercado_analise.py:636-700` — `veredito_do_destaque` inteira, com a regra
  "a mediana e a de ANTES deste tick" ja escrita.
- `l2scanner/mercado_analise.py:600-640` — `acrescentar`, que e o que move a populacao.
- `l2scanner/mercado_modo.py:580-670` — o bloco `if pagina is not None:` inteiro, os
  quatro passos numerados e os comentarios do ANAL-02. E este bloco que vira funcao.
- `l2scanner/mercado_console.py:341-378` — `destaque_ao_vivo`, que e quem imprime a
  mediana e o `n` que o usuario viu discordarem.
- `tests/test_mercado_modo.py:1070-1170` — `TestODestaqueEContraAHistoriaDeANTES`. O teste
  de 1088 ja usa a tecnica de afirmar PRIMEIRO que dois numeros diferem; reusar a tecnica.
  </read_first>

  <behavior>
Escrever ANTES da implementacao, em `tests/test_mercado_modo.py`, numa classe nova
`TestAMedianaNaoSeMoveDebaixoDaPagina`:

- Teste 1 (ORDEM NAO IMPORTA — o criterio central): montar um modelo com SETE observacoes
  de UMA serie (acima do piso da mediana). Montar QUATRO linhas da mesma serie, todas
  abaixo da mediana e com unitarios distintos. Rodar `processar_a_pagina_aceita` duas
  vezes, cada uma com um modelo NOVO semeado identicamente, uma na ordem `[1,2,3,4]` e
  outra na ordem `[4,3,2,1]`. Afirmar que o mapeamento {linha -> texto anunciado} e
  IDENTICO entre as duas rodadas. O texto, e nao um campo: e o texto que o usuario copia
  para o WhatsApp, e e nele que a mediana e o `n` aparecem.
- Teste 2 (O `n` NAO SOBE DENTRO DA PAGINA): nos quatro anuncios de uma rodada, o `n=`
  citado e o MESMO nas quatro (sete), e a mediana citada e a MESMA nas quatro. E o
  desmentido direto da sequencia `n=7 -> n=8 -> n=9 -> n=10` vista em producao.
- Teste 3 (O TESTE DISCRIMINA, e nao passa por vacuidade): afirmar PRIMEIRO que a mediana
  do modelo DEPOIS da pagina difere da mediana de antes. Se as quatro ofertas nao
  movessem a populacao, os Testes 1 e 2 passariam sobre nada. Mesma tecnica do teste de
  `tests/test_mercado_modo.py:1088`.
- Teste 4 (A RAZAO ESTA ESCRITA): `inspect.getdoc(ModeloDeMercado.vereditos_da_pagina)`
  nomeia o custo aceito (uma pagina inteira de ofertas baratas anuncia todas contra a
  referencia congelada) E nomeia o que foi recusado (a comparacao dependendo da posicao
  da linha na grade). Um dos dois sozinho seria meia decisao.
  </behavior>

  <action>
1. `ModeloDeMercado.vereditos_da_pagina(self, linhas) -> tuple[Destaque, ...]` em
   `l2scanner/mercado_analise.py`, imediatamente depois de `veredito_do_destaque`.
   Ela julga TODAS as linhas contra o modelo como ele esta AGORA e devolve a tupla
   alinhada com `linhas`, na mesma ordem. Ela nao escreve nada, nao chama `acrescentar` e
   continua PURA como o resto do modulo.

   A docstring carrega a DECISAO, porque e ela que substitui um comportamento que estava
   em producao:
   - O DEFEITO MEDIDO: em 2026-09-02, quatro ofertas de Adena anunciadas no MESMO segundo
     citaram medianas diferentes — `11,00 contra 13,87 n=7`, `11,20 contra 13,00 n=8`,
     `11,40 contra 13,00 n=9`, `11,70 contra 12,00 n=10`. Cada oferta entrava na
     populacao antes de a seguinte ser comparada, entao a MESMA oferta era noticia forte
     na primeira fatia e quase nada na ultima.
   - O QUE FOI RECUSADO: o veredito dependendo de onde a linha calhou de estar na grade.
     Isso nao e opiniao sobre preco, e artefato de varredura.
   - O CUSTO ACEITO, escrito e nao escondido: uma pagina inteira de ofertas baratas passa
     a anunciar TODAS contra a referencia congelada, em vez de a segunda ja se comparar
     com a primeira. O custo e conhecido e limitado a uma pagina; o defeito trocado por
     ele nao tinha limite nenhum e era invisivel na leitura do log.
   - Que a referencia congelada e a de ANTES DA PAGINA, e nao a de antes do TICK: sao a
     mesma coisa hoje porque o laco so acrescenta dentro deste bloco, e escrever isso
     evita que um refactor futuro acredite que a distincao nao existe.
   - `veredito_do_destaque` CONTINUA existindo e publica (ela e a primitiva de UMA linha
     e ha teste vivo sobre ela), mas o laco nao a chama mais: quem julga pagina julga a
     pagina inteira de uma vez.

2. `processar_a_pagina_aceita` em `l2scanner/mercado_modo.py`, funcao de MODULO acima de
   `laco_do_mercado`. Assinatura:

       processar_a_pagina_aceita(linhas, *, modelo, catalogo, registro,
                                 trava_do_destaque, contagem, agora)
           -> tuple[list[str], str | None]

   Ela e a EXTRACAO LITERAL do corpo do `for linha in pagina.linhas:` de hoje — os quatro
   passos numerados e os comentarios do ANAL-02 vem JUNTOS, nao se reescrevem. As unicas
   duas mudancas de comportamento:
   - ela comeca com `vereditos = modelo.vereditos_da_pagina(linhas)` e o `for` passa a
     iterar `zip(linhas, vereditos)`;
   - em vez de `log.info` no lugar, ela ACUMULA os anuncios devolvidos por
     `trava_do_destaque.anunciar` numa lista e a devolve — a mesma doutrina de
     `TravaDoDestaque` e de `destaque_ao_vivo`, que devolvem texto em vez de imprimir, e
     e o que torna esta funcao afirmavel sem `caplog` e sem fixtura.
   O segundo valor devolvido e o `ultimo_item` (`None` quando `linhas` vem vazia).
   `contagem` continua sendo MUTADA no lugar, como hoje.

   Comentario obrigatorio no topo da funcao dizendo por que o congelamento e a PRIMEIRA
   linha dela: se ele descesse para dentro do laco, a referencia voltaria a se mover e a
   suite continuaria verde em tudo menos no teste de ordem — e e por isso que o teste de
   ordem existe.

3. `laco_do_mercado` passa a chamar a funcao no lugar do `for`:
   `anuncios, novo_item = processar_a_pagina_aceita(pagina.linhas, ...)`, depois
   `for anuncio in anuncios: log.info("%s", anuncio)` e
   `if novo_item is not None: ultimo_item = novo_item`.
   `paginas_desde_a_gravacao` e a gravacao do catalogo a cada N paginas FICAM no laco,
   fora da funcao — elas sao cadencia do laco e nao processamento de pagina.

4. A EXTRACAO TEM DE SER REFACTOR PURO, no precedente ja registrado do 04-02: os testes
   ponta a ponta de `laco_do_mercado` que ja existem em `tests/test_mercado_modo.py`
   seguem verdes SEM UMA EDICAO DE EXPECTATIVA. Se algum deles precisar de ajuste, a
   extracao mudou comportamento e o certo e voltar atras, nao ajustar o teste.
  </action>

  <verify>
    <automated>
python -m pytest -q --ignore=tests/test_agenda.py tests/test_mercado_modo.py tests/test_mercado_analise.py tests/test_mercado_console.py tests/test_mercado_receitas.py -x
    </automated>
    <automated>
python -m pytest -q --ignore=tests/test_agenda.py -k "TestAMedianaNaoSeMoveDebaixoDaPagina" -v
    </automated>
    <automated>
python -c "import inspect; from l2scanner.mercado_analise import ModeloDeMercado as M; d=inspect.getdoc(M.vereditos_da_pagina); assert 'congelada' in d and 'grade' in d, d; print('a decisao esta escrita')"
    </automated>
    <automated>
git diff 33ebb56..HEAD -- tests/test_mercado_modo.py | grep '^-' | grep -v '^---' | wc -l
    </automated>
    <automated>
python -m pytest -q --ignore=tests/test_agenda.py
    </automated>
  </verify>

  <prova_por_mutacao>
OBRIGATORIA. Depois de a task estar VERDE:

1. Em `processar_a_pagina_aceita`, apagar a linha do congelamento e voltar a julgar linha
   a linha dentro do laco (`destaque = modelo.veredito_do_destaque(linha)`) — que e
   exatamente o codigo de producao de hoje.
2. Rodar `python -m pytest -q --ignore=tests/test_agenda.py -k "TestAMedianaNaoSeMoveDebaixoDaPagina"`.
3. Confirmar VERMELHO nos Testes 1 e 2, e VERDE no Teste 3 (o Teste 3 e sobre a populacao
   se mover, e ela se move nos dois mundos — se ele ficar vermelho, ele nao estava
   discriminando o que dizia discriminar).
4. COPIAR A LINHA DE RESUMO DO PYTEST VERBATIM para o corpo do commit.
5. Reverter a mutacao e reconfirmar o verde.
  </prova_por_mutacao>

  <done>
- A mesma pagina em duas ordens (`[1,2,3,4]` e `[4,3,2,1]`) produz o MESMO conjunto de
  textos anunciados, casados linha a linha. Medido comparando texto, nao campo.
- Os quatro anuncios de uma rodada citam a MESMA mediana e o MESMO `n`.
- O teste afirma PRIMEIRO que a mediana de depois da pagina difere da de antes — sem isso
  ele passaria sobre nada.
- A docstring de `vereditos_da_pagina` nomeia o custo aceito E o que foi recusado.
- Zero linhas REMOVIDAS de `tests/test_mercado_modo.py` contra `33ebb56` — a prova de que
  a extracao foi refactor puro.
- Suite completa sem regressao contra a base **4865 passed, 29 skipped**.
- A prova por mutacao rodou e o resumo do pytest esta no commit.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| tela do jogo -> leitor | pixels nao confiaveis viram numero; ja coberto pelas peneiras existentes |
| processo -> `scanner.log` | o log rotativo e o unico artefato de forense; volume e o vetor |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-PQF-01 | Denial of Service | `scanner.log` rotativo | medium | mitigate | `TravaDaRecusa` corta ~3.600 linhas/hora por oferta parada; o rodizio deixa de apagar a forense que existe para guardar |
| T-PQF-02 | Tampering | dado do CSV | high | mitigate | a trava alcanca SO o log; o `Descarte` continua saindo em todo tick, preso pelo Teste 2 da Task 1 |
| T-PQF-03 | Information disclosure | anuncio de destaque | low | accept | o texto anunciado nao ganha campo novo; so para de variar com a ordem da linha |
| T-PQF-SC | Tampering | instalacao de pacote | n/a | accept | nenhuma dependencia nova neste plano — nao ha superficie de cadeia de suprimento a auditar |
</threat_model>

<verification>
Antes de fechar, conferir na arvore:

1. `python -m pytest -q --ignore=tests/test_agenda.py` — sem regressao contra
   **4865 passed, 29 skipped** (os 27 skips de `tests/test_renda_tracer.py` sao o venv
   sem as bindings WinRT e nao sao deste plano).
2. `git status --porcelain -- calibration.json .mercado/` sai VAZIO.
3. `git diff 33ebb56..HEAD --name-only` nao lista `rastreador.py`, `visao.py`,
   `respawn.py`, `bosses.py`, `agenda.py`, `sessao.py`, `identidade.py`, `dashboard.py`,
   nem nada em `discord/` ou `renda*`.
4. `grep -rn "mercado_tolerancia_do_cruzamento" l2scanner/ | grep -v "None"` — a guarda
   continua desligada.
5. `git diff 33ebb56..HEAD -- l2scanner/ | grep -c "pyautogui\|pynput\|keyboard\|mouse"`
   devolve 0.
</verification>

<success_criteria>
- Os dois defeitos vistos em produca 2026-09-02 estao MEDIDOS por teste, e cada teste
  conta emissoes ou compara textos anunciados — nenhum deles afirma que um simbolo existe.
- As duas provas por mutacao rodaram, cada uma com o resumo do pytest copiado verbatim
  para o corpo do commit.
- A regra da casa foi cumprida: a frase de `_recusar` mudou porque o codigo mudou.
- Dois commits atomicos, mensagem em portugues, um por task.
</success_criteria>

<output>
Sem SUMMARY.md — e a convencao deste workstream para quicks (PLAN + codigo).
Registrar o quick na tabela `Quick Tasks Completed` de
`.planning/workstreams/mercado/STATE.md`, e acrescentar em `Decisions` as duas decisoes
tomadas aqui: o indice DENTRO da chave de `TravaDaRecusa` (com a razao), e a referencia
CONGELADA por pagina (com o custo aceito).
</output>
