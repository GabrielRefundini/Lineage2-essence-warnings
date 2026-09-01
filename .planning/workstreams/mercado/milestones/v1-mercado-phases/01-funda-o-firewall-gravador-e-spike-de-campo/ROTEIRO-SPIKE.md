# ROTEIRO DO SPIKE — gravações do World Exchange (XM Market)

**Para quem lê:** você, com o jogo aberto. Deixe este arquivo aberto no segundo monitor e vá
marcando as caixas. Cada cenário é uma sessão curta e independente.

**Por que isto existe:** o painel do mercado nunca foi gravado por este projeto. Sem estas 8
gravações, a calibração, os templates de item e a detecção do painel não têm evidência real
para nascer — e a fase inteira fica parada aqui. Estas sessões são o recurso escasso: só você
pode produzi-las (é a sua conta, o seu cliente, o seu servidor).

> **CUSTO DE DISCO — MEDIDO, não estimado.** A janela completa do jogo sai a **~3,5 MB por
> PNG** (medido em `recordings/inv3/f000_JANELA.png`, 1720×1392). A gravação roda a ~1 Hz,
> então **~210 MB por minuto**. É exatamente por isso que cada cenário é uma sessão **curta,
> de 30 a 60 segundos**. As 8 sessões juntas devem ficar entre **1,5 e 3 GB**.
> **Garanta espaço em disco antes de começar.**

---

## Antes de começar (uma vez só)

- [ ] Confirme que há pelo menos **5 GB livres** no disco onde este projeto está.
- [ ] Abra o jogo, entre com o personagem e deixe a **janela do jogo visível** (não
      minimizada — janela minimizada não produz frames e a gravação falha fechada).
- [ ] Abra um terminal na pasta do projeto.
- [ ] Deixe este arquivo aberto no segundo monitor.

> **POR QUE `.venv\Scripts\python.exe` E NAO SO `python`.** MEDIDO EM CAMPO
> 2026-08-28: no PowerShell o `python` puro funcionava, mas no `cmd` deu
> `'python' nao e reconhecido como um comando`. O caminho explicito do venv
> funciona nos dois, e e o mesmo que todos os `.bat` do projeto ja usam. Rode
> sempre a partir da pasta do projeto.

**Como parar uma sessão:** `Ctrl+C` no terminal. O scanner imprime um **resumo final com três
números** — frames confirmados, falhas de escrita e a contagem lida do disco. Os três precisam
fechar (confirmados = disco, falhas = 0).

**Por que `--dry-run` está em todos os comandos:** durante o spike você não quer disparar
alertas de WhatsApp para a party a cada leitura. O `--dry-run` mostra os alertas no console e
não envia nada. A gravação funciona igual.

---

## Cenário 0 — PRÉ-VOO (obrigatório, 5 segundos)

**Não pule.** Este cenário existe para provar que você está gravando a **janela inteira** e não
o recorte da party window. Descobrir isso agora custa 5 segundos; descobrir depois custa as
oito sessões.

```
.venv\Scripts\python.exe -m l2scanner --janela --record-janela --rotulo pre-voo --dry-run
```

- [ ] Rodei o comando acima e parei com `Ctrl+C` depois de ~5 segundos.
- [ ] Abri a pasta nova em `recordings/` (o nome termina em `-pre-voo`) e abri um
      `frame_*.png`.

**Critério de aprovação — os dois tamanhos:**

| O que você vê | Veredito |
|---|---|
| PNG de **~3,5 MB**, mostrando a **janela inteira** do jogo | ✅ certo, siga para o cenário 1 |
| PNG de **~170 KB**, mostrando só a faixa estreita da party window | ❌ **PARE** |

- [ ] O PNG tem ~3,5 MB e mostra a janela inteira.

> **Se veio o PNG de ~170 KB:** é o modo errado (voltou a gravar o recorte da party). **Não
> grave mais nada** — avise e espere. Gastar as 8 sessões assim perderia o spike inteiro.

---

## Os 8 cenários

Regras que valem para todos:

- **Uma sessão por cenário**, com o rótulo exato escrito no comando. O rótulo vira o nome da
  pasta em `recordings/` e é assim que os testes e a análise vão te citar depois.
- **30 a 60 segundos** cada. Mais que isso só gasta disco.
- Se um cenário sair errado (esqueceu de abrir o painel, por exemplo), **regrave só aquele** —
  a pasta antiga pode ficar, a conferência final usa a mais recente de cada rótulo.

---

### 1. `mercado-fechado` — o negativo da âncora

```
.venv\Scripts\python.exe -m l2scanner --janela --record-janela --rotulo mercado-fechado --dry-run
```

**Duração:** 30 a 60 segundos.

**O que fazer na tela:** jogo normal, **o painel do mercado nunca aberto**. Ande, mire em algo,
deixe a interface do jeito de sempre. É deste material que sai a prova de que a detecção do
painel **não** dispara quando o painel não está lá.

**Pedido extra, e ele vale ouro:**

- [ ] Se aparecer o aviso de sistema **"Someone has registered an item on XM Market!"** no log
      do jogo durante esta sessão, ótimo — deixe rolar. Se der para provocar (esperando um
      pouco mais), melhor ainda.

> **Por quê:** já medimos esse aviso num frame antigo. Ele coloca as palavras **"XM Market" na
> tela com o painel FECHADO** — é a armadilha perfeita para um detector que procurasse o texto.
> Nossa âncora casa a *arte* do painel e leu 0,4624 ali (bem abaixo do corte de 0,73), mas é o
> negativo mais difícil que temos e quanto mais exemplos dele, mais firme fica o limiar.

- [ ] Gravado.

---

### 2. `mercado-aberto` — o painel parado, nas duas abas

```
.venv\Scripts\python.exe -m l2scanner --janela --record-janela --rotulo mercado-aberto --dry-run
```

**Duração:** 30 a 60 segundos.

**O que fazer na tela:**

1. Abra o painel do mercado (**XM Market** — é esse o nome nativo na barra de título).
2. Fique na aba **Adena** por ~15 segundos, com o painel **parado** (sem rolar).
3. Troque para a aba **Equipment** e fique mais ~15 segundos, também parado.
4. Se der, volte para a **Adena** antes de encerrar.

> **Por que as duas abas:** o formato dos números pode ser diferente entre elas. O frame que já
> temos no disco é da aba de equipamento e mostra `40,00 XM Coin` — vírgula decimal e moeda
> "XM Coin". A aba **Adena** é a que interessa para preçar, e o formato dela ainda é
> desconhecido. Sem as duas na gravação, os templates de dígito seriam calibrados na aba errada.

**Bloco extra deste cenário — ARRASTE O PAINEL (3 posições):**

> **Já sabemos que o painel anda — isto foi MEDIDO, não suposto.** Na gravação do incidente das
> 27 mortes falsas, o painel aparece em **duas posições diferentes** na mesma sessão: 181 px à
> esquerda e 143 px abaixo, com a arte casando 0,9996 nas duas. Ou seja: um retângulo fixo
> **não** encontra o painel, e a detecção vai precisar **procurar**. O que ainda não sabemos é
> o **alcance**: até onde ele pode ir, e se ele reabre onde foi fechado.

- [ ] Arrastei o painel pela barra de título para uma **segunda** posição e deixei ~10 s parado.
- [ ] Arrastei para uma **terceira** posição, o mais longe que der (um canto), e deixei ~10 s.
- [ ] **Fechei e reabri** o painel no fim da sessão, e anotei aqui onde ele reapareceu:
      `[ ] no lugar onde foi fechado   [ ] sempre no mesmo lugar padrão`

> **Por que as três posições:** com duas posições sabemos que ele anda; com três e com o
> fecha-reabre sabemos **onde procurar** e **com que frequência**. Procurar o painel na janela
> inteira custa ~45 ms e por isso não pode rodar a cada volta. A diferença entre "procurar numa
> faixa" e "procurar na janela toda" é decidida por esta gravação.

- [ ] Gravado.

---

### 3. `mercado-scroll` — rolando a lista devagar

```
.venv\Scripts\python.exe -m l2scanner --janela --record-janela --rotulo mercado-scroll --dry-run
```

**Duração:** 30 a 60 segundos.

**O que fazer na tela:** painel aberto, **role a lista devagar**, com **pausas de 2 a 3
segundos** entre um movimento e outro. As pausas são o ponto: é nelas que a página fica parada
o suficiente para ser lida, e é isso que a leitura precisa aprender a esperar.

- [ ] Gravado.

---

### 4. `mercado-pagina-cheia` — o máximo de linhas preenchidas

```
.venv\Scripts\python.exe -m l2scanner --janela --record-janela --rotulo mercado-pagina-cheia --dry-run
```

**Duração:** 30 a 60 segundos.

**O que fazer na tela:** encontre uma página com o **máximo de linhas preenchidas** que você
conseguir (idealmente sem nenhum slot vazio) e deixe parada. Se sobrar tempo, mostre também uma
página com **alguns slots vazios**, para a análise ver a diferença entre "linha vazia" e "linha
com item".

- [ ] Gravado.

---

### 5. `mercado-tooltip` — a tooltip cobrindo linhas vizinhas

```
.venv\Scripts\python.exe -m l2scanner --janela --record-janela --rotulo mercado-tooltip --dry-run
```

**Duração:** 30 a 60 segundos.

**O que fazer na tela:** painel aberto, **deixe o mouse parado sobre uma linha** até a tooltip
aparecer, e **mantenha** até ela cobrir as linhas vizinhas. Repita em 2 ou 3 linhas diferentes.

> **Por que este cenário existe:** ele é o gêmeo do incidente das 27 mortes falsas. Naquele
> caso, um pedaço da tela ficou parcialmente coberto e o scanner leu com **confiança total** um
> valor errado. Uma tooltip por cima de uma linha de preço é exatamente a mesma armadilha, um
> nível acima. Precisamos deste material para que a leitura aprenda a **recusar** a linha
> coberta em vez de inventar um preço.

- [ ] Gravado.

---

### 6. `mercado-alvo-sobreposto` — marcação de alvo por cima do painel

```
.venv\Scripts\python.exe -m l2scanner --janela --record-janela --rotulo mercado-alvo-sobreposto --dry-run
```

**Duração:** 30 a 60 segundos.

**O que fazer na tela:** com o painel aberto, **selecione um alvo** para que a barra de vida /
marcação do alvo apareça **sobrepondo levemente o painel**. Você já relatou que isso acontece
de verdade — é este o frame que precisamos.

- [ ] Gravado.

---

### 7. `mercado-farm-com-party` — o caso real de uso

```
.venv\Scripts\python.exe -m l2scanner --janela --record-janela --rotulo mercado-farm-com-party --dry-run
```

**Duração:** 30 a 60 segundos.

**O que fazer na tela:** **em party**, durante o farm, com a **party window visível** e o painel
do mercado **aberto** ao mesmo tempo. É assim que você vai usar de verdade, e é o material que
prova que o mesmo sinal serve às duas coisas: ler o mercado **e** avisar o detector de morte de
que a tela está parcialmente coberta.

- [ ] Gravado.

---

### 8. `mercado-scroll-transicao` — o meio do movimento, de propósito

```
.venv\Scripts\python.exe -m l2scanner --janela --record-janela --rotulo mercado-scroll-transicao --dry-run
```

**Duração:** 30 a 60 segundos.

**O que fazer na tela:** role a lista **de forma contínua**, sem parar, para que os frames
peguem a lista **no meio da transição** (linhas borradas, meio-caminho, texto cortado). Aqui
gravações "feias" são o objetivo: elas são o material com que a leitura vai aprender a
**descartar** uma página em movimento em vez de ler metade de uma linha e metade da seguinte.

- [ ] Gravado.

---

## O que estas gravações precisam deixar visível

Depois que você gravar, a análise dos frames vai propor as respostas destas perguntas num
`SPIKE-RESPOSTAS.md`, citando frames específicos como evidência — e você valida ou corrige.
Para que isso seja possível, **estas coisas precisam estar na tela em algum momento**:

1. **Quantas linhas cabem numa página** e como é um **slot vazio** (cenário 4).
2. **Separador de milhar e casas decimais** — um preço com valor alto o suficiente para mostrar
   como o jogo separa os milhares (cenários 2 e 4).
3. **Qual é a moeda** em cada aba (Adena vs Equipment) — cenário 2.
4. **Quais são as colunas** e em que ordem (`Goods | Quantity | Total | Unit price | Buy`).
5. **Preço total × preço unitário** — as duas colunas aparecem juntas? Alguma some em alguma aba?
6. **Onde fica o preço médio embutido**, se ele existir em algum lugar do painel.
7. **A idade do anúncio** (há quanto tempo o item está listado) aparece em algum lugar?

**Pedido explícito — itens encantados:**

- [ ] Garanta que **pelo menos um item encantado** esteja na tela em `mercado-aberto` **ou**
      `mercado-pagina-cheia`. Você já confirmou que o encanto aparece como **prefixo de texto no
      nome** (`+3 <nome do item>`); precisamos ver isso renderizado num frame para os templates
      nascerem certos, porque `+3 Bota X` e `+4 Bota X` serão **dois itens diferentes** para o
      scanner.
- [ ] Se der, garanta que apareça um **nome longo com o prefixo `+N`** — é ele que mostra se o
      jogo **trunca** o nome, e truncamento é o que faria dois itens diferentes virarem o mesmo
      texto.

---

## Nota de escopo — inventário e mercado

**Não existe cenário de "inventário por cima do mercado", e isso não é esquecimento.** Você
confirmou que **abrir o inventário FECHA o painel do mercado** — os dois são mutuamente
exclusivos na interface. Outras janelas do menu podem sobrepor em casos raros; isso ficou
anotado como ideia para uma versão futura e está deliberadamente fora deste roteiro.

## Nota de privacidade

As gravações contêm **nomes de personagens e o chat do jogo**. A pasta `recordings/` está no
`.gitignore` e **nada dela vai para o repositório**. Só recortes mínimos — o pedaço da barra de
título do painel, sem nomes e sem chat — são copiados para `tests/fixtures/` para virarem teste
permanente. Você pode conferir exatamente o que foi copiado: é a lista no resumo desta fase.

---

## Checklist de encerramento

- [ ] As 8 pastas aparecem em `recordings/`, uma por rótulo.
- [ ] Em cada sessão, o **resumo final** fechou: `confirmados = no disco` e `falhas = 0`.
- [ ] Rodei o portão de conferência:

```
.venv\Scripts\python.exe tools\conferir_gravacoes_do_spike.py
```

- [ ] Li o relatório do portão e ele **passou** (saiu sem apontar problema).

> **Se o portão reprovar**, ele nomeia a pasta e o problema — sufixo faltando, `observacoes.jsonl`
> vazio, arquivo citado que não existe no disco, contagem de linhas diferente da contagem de
> PNGs (sinal de escrita perdida), ou PNG na dimensão errada. Regrave **só** o cenário apontado.

**Quando tudo passar:** avise ("pronto") e a análise das gravações começa.
