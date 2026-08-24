---
phase: 7
phase_name: "Silenciamento por janela de evento"
project: "L2 Party Scanner"
generated: "2026-08-24"
counts:
  decisions: 7
  lessons: 5
  patterns: 5
  surprises: 3
missing_artifacts:
  - "VERIFICATION.md"
  - "UAT.md"
---

# Phase 7 Learnings: Silenciamento por janela de evento

## Decisions

### O silenciamento vive no TRANSPORTE, nunca na detecção
O rastreador segue decidindo e registrando tudo; o corte é uma categoria no
`despachar()`.

**Rationale:** silenciar na detecção corromperia o estado — quem morre e
ressuscita durante o silêncio precisa sair do outro lado com o estado certo — e
apagaria o log, que é a única ferramenta de depuração pós-farm do projeto. A
decisão decorre direto do enquadramento: os alertas durante um TvT são
**verdadeiros**, só não são notícia.
**Source:** PLAN.md

---

### `Categoria.NORMAL` é o padrão, e isso é de segurança
**Rationale:** uma fonte de eventos futura que esqueça de declarar categoria cai
no lado seguro — calada durante o evento — em vez de vazar.
**Source:** SUMMARY.md

---

### Janelas sobrepostas são UNIÃO, não substituição
**Rationale:** não é refinamento, é correção. De segunda a quinta o Prime vai
das 20:00 às 22:00 e o TvT das 21:50 vai até 22:05. Substituir faria o silêncio
acabar às 22:00 e os últimos cinco minutos de TvT vazariam alerta — bem no auge
do evento, que é quando mais gente morre.
**Source:** PLAN.md, SUMMARY.md

---

### Os avisos de agenda atravessam o silêncio sempre
**Rationale:** sem isso, de segunda a quinta o lembrete do TvT das 21h40 cairia
dentro do silêncio do Prime e o usuário nunca receberia aviso do TvT das 21h50
em quatro dias da semana. A funcionalidade se anularia sozinha.
**Source:** PLAN.md

---

### O silenciado não entra no `outbox.jsonl`
**Rationale:** o outbox existe para garantir que nada se perca no caminho da
**rede**. Uma mensagem que decidimos não enviar não está a caminho de lugar
nenhum — ela está no log, que é onde pertence.
**Source:** PLAN.md, SUMMARY.md

---

### A busca do diálogo ganha cadência de 5 s
**Rationale:** medido, `matchTemplate` custava 47 ms contra 0,7 ms de toda a
análise da party window — ~98% do CPU do scanner, gasto a 1 Hz para procurar um
evento que acontece uma vez por manutenção. Um diálogo de desconexão não pisca:
aparece e fica até alguém clicar. O título continua sendo lido a cada tick,
porque custa microssegundos e a tela de login não pode esperar.
**Source:** REVIEW.md (segunda passada)

---

### O veredito de desconexão gruda entre buscas
**Rationale:** sem isso o estado oscilaria DESCONECTADO/EM_JOGO a cada tick, as
confirmações do rastreador nunca chegariam a duas seguidas, e o alerta
simplesmente não sairia. A otimização teria desligado a funcionalidade em
silêncio.
**Source:** REVIEW.md (segunda passada)

---

## Lessons

### O bug de começo frio apareceu pela QUARTA vez neste projeto
No `ControleDoSilencio`, "acabei de entrar na janela" e "subi já dentro dela"
eram indistinguíveis: nos dois casos a janela anterior era `None`.

**Context:** as outras três foram a entrada de membro na party, o "você em
party", e o cliente caído. Todas exigiram o mesmo remédio — um terceiro estado
que registre "já observei o mundo no estado oposto".
**Source:** SUMMARY.md

---

### Três de três warnings do code review moravam em `__main__.py`
E a cobertura desse arquivo é 20%, contra 98% do `rastreador.py`.

**Context:** duas fontes independentes — leitura de código e medição de
cobertura — apontando o mesmo risco. Nenhum problema estava nos algoritmos; os
três viviam na **costura**: ordem de execução, uma condição a mais num `if`, um
contador que ninguém lê.
**Source:** REVIEW.md

---

### A agenda estava depois do `try` da extração, contradizendo o próprio docstring
Um erro de leitura de pixel fazia o `continue` engolir o lembrete de TvT junto.

**Context:** o módulo declara "o aviso vem do relógio, não da tela" e o código
foi colocado no lugar que viola isso. Declarar um princípio no comentário não o
faz valer no fluxo.
**Source:** REVIEW.md (W-02)

---

### O status ao vivo tinha ficado sem o silêncio
Só o "estado final" mostrava a janela de silêncio — ou seja, o usuário só
descobriria o motivo depois de encerrar o scanner.

**Context:** a linha que aparece a cada 30 s durante o farm é a única que ele
realmente lê. Um teste que varre **todas** as chamadas de `desenhar_status`
pegou o caso.
**Source:** SUMMARY.md

---

### Otimizar pode desligar a funcionalidade em silêncio
A cadência de 5 s, sozinha, teria feito o estado oscilar e o debounce nunca
fechar.

**Context:** a otimização estava correta em custo e errada em comportamento. O
sintoma seria "o alerta não sai", sem erro nenhum — o modo de falha mais caro
deste projeto.
**Source:** REVIEW.md (segunda passada)

---

## Patterns

### Testes que leem a fonte para travar ORDEM DE EXECUÇÃO
`inspect.getsource(laco_principal)` e asserções sobre posições relativas.

**When to use:** quando a correção é sobre *onde* o código está no fluxo, e
exercitá-lo de verdade exigiria a aplicação inteira rodando. É a única forma de
travar ordem sem subir o scanner com um jogo aberto — e ordem é exatamente o que
um refactor desfaz sem perceber.
**Source:** REVIEW.md

---

### Distinguir "mudou" de "foi assim que eu encontrei"
Toda máquina de estado que anuncia transições precisa de um terceiro estado que
registre ter observado o mundo no estado oposto.

**When to use:** em qualquer detector de transição que rode desde o arranque.
Quatro ocorrências neste projeto; a regra vale como padrão, não como caso.
**Source:** SUMMARY.md

---

### Padrão seguro por omissão
O valor default do parâmetro é o mais conservador (`Categoria.NORMAL` = pode ser
silenciado).

**When to use:** quando um ponto de extensão vai ser usado por código futuro que
pode esquecer de declarar a intenção. O esquecimento tem que cair no lado que
não causa dano.
**Source:** SUMMARY.md

---

### Fronteira travada por asserção, não por intenção
Um teste afirma que a mensagem de encerramento **não** contém promessa de
convidar ninguém.

**When to use:** quando existe uma restrição dura de projeto (aqui: o scanner é
somente leitura e nunca envia input ao jogo). A restrição deixa de depender de
alguém lembrar dela.
**Source:** SUMMARY.md

---

### Mover a lógica para fora da camada intestável antes de considerá-la pronta
A cadência foi escrita em `captura_janela.py` (19% de cobertura) e movida para
`cliente.py` (85%) antes do commit final.

**When to use:** sempre que uma decisão nova cair num módulo que só o ambiente
real exercita. É a condição que deixou os três warnings passarem.
**Source:** REVIEW.md (segunda passada)

---

## Surprises

### Um único `matchTemplate` era 98% do CPU do scanner
`extrair()` — **toda** a análise da party window, com HSV, máscaras e template
de nomes — custa 0,7 ms. A busca do diálogo custava 47 ms.

**Impact:** a otimização óbvia (restringir a faixa) rendeu 2,7×, e a não óbvia
(cadência) rendeu mais 5×. O tick inteiro passou a custar 1% do orçamento.
Também mudou onde procurar performance neste projeto: não é a visão
computacional, é o que roda ao lado dela.
**Source:** REVIEW.md

---

### A cobertura confirmou o achado da revisão sem saber dele
A revisão chegou a "o risco mora na integração" lendo código; a cobertura chegou
ao mesmo lugar por medição, depois.

**Impact:** eleva a conclusão de opinião a evidência, e dá um alvo concreto para
o próximo trabalho de qualidade — `__main__.py`, 379 statements, 20%.
**Source:** REVIEW.md (segunda passada)

---

### Havia código morto de uma tarefa da fase anterior
`RegistroEmMemoria` ficou órfão quando a Tarefa 3 da Fase 6 o substituiu.

**Impact:** 28 linhas mantidas, testadas e lidas por ninguém. O padrão
"implementa a versão simples, troca pela real" deixa lixo quando a troca é
limpa demais para doer.
**Source:** REVIEW.md (segunda passada)
