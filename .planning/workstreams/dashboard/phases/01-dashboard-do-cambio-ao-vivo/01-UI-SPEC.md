---
phase: 1
slug: dashboard-do-cambio-ao-vivo
workstream: dashboard
status: approved
shadcn_initialized: false
preset: none
created: 2026-09-01
approved: 2026-09-01
---

# Fase 1 — Contrato de Design da Interface

> Contrato visual e de interação do dashboard do câmbio. Gerado por `gsd-ui-researcher`,
> verificado por `gsd-ui-checker`. **Prescritivo, não exploratório** — o executor implementa
> daqui sem decidir cor, tamanho ou frase.

**Fonte das decisões:** `01-CONTEXT.md` (4 áreas, todas aceitas pelo usuário) + `REQUIREMENTS.md`
(DASH-01..06) + `ROADMAP.md`. Nada aqui reabre decisão travada; o que este documento acrescenta é
a camada visual, que o CONTEXT deixou como "tema de Lineage 2, sem custar legibilidade".

---

## Estado do projeto no momento da escrita — medido, não suposto

| Fato | Medição |
|---|---|
| `.mercado/observacoes.csv` existe | sim — 93 linhas |
| Linhas com a sentinela `adena#` | **0** |
| Ativos web na árvore (`.css`/`.html`/`.js` fora do `.venv`) | **nenhum** |
| `components.json`, `package.json`, `tailwind.config.*` | **não existem** |

**Consequência direta:** o estado vazio não é um caso de borda — é a **primeira tela que o
usuário vai ver**. Ele é especificado aqui com o mesmo cuidado do estado povoado.

---

## Design System

| Propriedade | Valor |
|-------------|-------|
| Tool | **none** — projeto Python; sem React/Next/Vite, sem npm, sem bundler, sem etapa de build |
| Preset | não se aplica |
| Component library | **nenhuma** — HTML + CSS escritos à mão |
| Icon library | **nenhuma** — SVG inline autorado por nós, no máximo 2 glifos; nenhum arquivo de ícone baixado |
| Font | **somente fontes do sistema** (stacks abaixo) — nenhum webfont, nenhuma requisição de rede |

**Por que o portão do shadcn não roda:** shadcn pressupõe React + Tailwind + um passo de build. O
CONTEXT trava "HTML simples + CSS + um arquivo JS vendorizado + um endpoint JSON. Sem npm, sem
bundler". Portão não aplicável, e não é omissão.

**Superfície de entrega:**

| Arquivo | Papel |
|---|---|
| `index.html` | estrutura, sem `<script>` e sem `<style>` inline (exigido pela CSP, ver Registry Safety) |
| `dashboard.css` | tema inteiro, escrito à mão |
| `dashboard.js` | nosso código: polling, formatação de estados, instanciação da série |
| `vendor/<lib>.min.js` + `vendor/<lib>.LICENSE` + `vendor/README.md` | a biblioteca de gráfico, arquivo único, com proveniência |

---

## Spacing Scale

Escala de 4 pontos. Nenhum valor fora dela no CSS.

| Token | Valor | Uso nesta tela |
|-------|-------|----------------|
| `--sp-xs` | 4px | vão entre o número e sua etiqueta de unidade; padding interno de *chip* |
| `--sp-sm` | 8px | vão entre `n` e recência; padding vertical do rodapé |
| `--sp-md` | 16px | padding interno dos painéis; vão entre linhas do rodapé |
| `--sp-lg` | 24px | vão entre os dois números do destaque; padding do painel do gráfico |
| `--sp-xl` | 32px | vão entre as três regiões (destaque / gráfico / rodapé); altura mínima de alvo clicável |
| `--sp-2xl` | 48px | respiro acima do destaque; altura do bloco de estado vazio |
| `--sp-3xl` | 64px | margem lateral máxima da página em telas largas |

**Exceções declaradas (não são espaçamento — são traço):**

- Larguras de borda `1px` e `2px`, usadas pelo relevo dos painéis. Borda não é espaço e não entra
  na escala; declarar aqui evita que o checker leia como violação.
- Espessura de linha do gráfico: `2px` (menor pedido) e `1.5px` (mediana). São parâmetros da
  biblioteca, não CSS de layout.
- Anel de foco: `2px` de traço com `2px` de deslocamento.

**Alvo clicável mínimo:** 32px de altura para o campo de câmbio e para o botão. Está na escala
(`--sp-xl`), então não é exceção.

---

## Typography

Três famílias, **quatro tamanhos, dois pesos**. Nada além disso entra no CSS.

### Famílias (todas do sistema — zero download, zero rede)

```css
--font-display: "Trajan Pro", "Cinzel", "Palatino Linotype", "Book Antiqua",
                Georgia, "Times New Roman", serif;
--font-ui:      "Segoe UI", system-ui, -apple-system, "Noto Sans", sans-serif;
--font-num:     Consolas, "Cascadia Mono", "SF Mono", "DejaVu Sans Mono", monospace;
```

- **`--font-display`** carrega o peso de fantasia dos títulos. O efeito de placa entalhada do L2 não
  vem de uma fonte baixada — vem de **serifa + `text-transform: uppercase` + `letter-spacing: 0.12em`**.
  Isso é reprodutível em qualquer Windows 11 sem um único byte de rede.
- **`--font-num`** vale para **todo número na tela**, sempre com `font-variant-numeric: tabular-nums`.
  Sem largura tabular, um número que se atualiza a cada 2 s "dança" horizontalmente — ruído puro ao
  lado do jogo.

### Escala

| Papel | Tamanho | Peso | Altura de linha | Família |
|------|------|--------|-------------|---------|
| Body | 16px | 400 | 1.5 | `--font-ui` |
| Label | 14px | 400 | 1.4 | `--font-ui` (etiquetas, `n`, recência, rodapé) |
| Heading | 24px | 700 | 1.2 | `--font-display`, maiúsculas, `letter-spacing: 0.12em` |
| Display | **`clamp(32–48px)`** | 700 | 1.1 | `--font-num` — **os dois números de agora** |

**Guarda de estouro do Display:** `font-size: clamp(32px, 6vw, 48px)`.

O piso e o teto estão declarados **dentro da linha `Display` da tabela acima**, e não como uma nota
de rodapé, porque é lá que o teto de quatro tamanhos é cobrado. `32px` aqui é **um extremo do papel
Display**, e não o token de espaçamento `--sp-xl` — os dois valerem 32 é coincidência aritmética, não
parentesco. O papel Display continua sendo **um** papel na escala; ele apenas respira entre dois
limites declarados. Efeito: um número muito grande **encolhe, nunca quebra linha e nunca vaza do
painel**.

Nenhum outro papel da escala usa `clamp`. Body, Label e Heading são fixos.

**Regra dura:** o Display usa `--font-num`, não `--font-display`. A fonte de fantasia é para o
título da placa; o valor que decide dinheiro é lido em monoespaçada tabular. Se as duas
disputarem, **o ornamento sai** — é a regra do usuário aplicada à tipografia.

---

## Color

Paleta tirada da cromática do painel do cliente de L2: carvão quente, relevo em madeira/bronze,
dourado nas letras, pergaminho no corpo. **Toda ela é CSS puro** — gradientes, bordas e sombras.
Nenhuma textura, nenhum print do jogo, nenhum asset que não exista no repositório.

| Papel | Token | Valor | Uso |
|-------|-------|-------|-----|
| Dominante (60%) | `--cor-fundo` | `#14110D` | fundo da página |
| Secundária (30%) | `--cor-painel` | `#1F1A14` | painéis (destaque, gráfico, rodapé) |
| Acento (10%) | `--cor-ouro` | `#E0B450` | lista explícita abaixo |
| Destrutiva / ausência | `--cor-alerta` | `#E06A5C` | ausência de dado e erro de contrato — **e nada mais** |

Estes quatro papéis são um **recorte** do bloco de tokens abaixo, e não uma segunda paleta: cada
linha nomeia o token que a implementa. O valor aparece aqui só para o papel 60/30/10 ser legível de
uma olhada.

### Tokens completos

```css
--cor-fundo:         #14110D;  /* 60% */
--cor-painel:        #1F1A14;  /* 30% */
--cor-relevo-topo:   #241E17;  /* topo do gradiente da placa */
--cor-relevo-base:   #171310;  /* base do gradiente da placa */
--cor-relevo-baixo:  #0B0906;  /* sombra do chanfro */
--cor-relevo-alto:   #3A3026;  /* borda do chanfro */
--cor-relevo-luz:    #5A4A35;  /* fio de luz superior do chanfro */
--cor-ouro:          #E0B450;  /* 10% — acento */
--cor-serie-tipica:  #C9BFA8;  /* a linha da mediana e o rótulo dela na legenda */
--cor-texto:         #E8E0D0;  /* pergaminho: corpo e o número em R$ */
--cor-texto-fraco:   #A79880;  /* n, recência, procedência do rodapé */
--cor-alerta:        #E06A5C;  /* ausência / erro */
--cor-frio:          #9FB0C4;  /* dado velho: recência estourada */
--cor-grade:         #2A231A;  /* linhas de grade do gráfico */
```

**Este bloco é a única declaração de cor do projeto.** Fora dele não existe literal hexadecimal —
nem no `dashboard.css`, nem no `dashboard.js`, nem na configuração do gráfico. (A tabela de papéis
acima repete quatro valores por legibilidade, mas nomeia o token de cada um: é recorte, não fonte.)

Essa regra não é estética: o `dashboard.js` é obrigado a ler cor por
`getPropertyValue`, e uma cor sem nome de token é **uma cor que o gráfico não consegue pedir**. Foi
por isso que a linha da mediana ganhou `--cor-serie-tipica` em vez de continuar sendo um `#C9BFA8`
solto: ela é passada para a configuração da biblioteca, e o que não tem nome não atravessa.

### Contraste — medido, não estimado

| Par | Razão | Piso |
|---|---|---|
| `--cor-texto` sobre `--cor-fundo` | **14,34:1** | AAA |
| `--cor-texto` sobre `--cor-painel` | **13,16:1** | AAA |
| `--cor-serie-tipica` sobre `--cor-painel` | **9,46:1** | AAA |
| `--cor-ouro` sobre `--cor-painel` | **8,89:1** | AAA |
| `--cor-frio` sobre `--cor-painel` | **7,80:1** | AAA |
| `--cor-texto-fraco` sobre `--cor-painel` | **6,12:1** | AA (corpo) · AAA (texto grande) |
| `--cor-alerta` sobre `--cor-painel` | **5,25:1** | AA (corpo) · AAA (texto grande) |

> **Dois rótulos desta tabela estavam errados, e o executor do 01-06 pegou (2026-09-02).** Os
> **números** foram recalculados a partir dos tokens e batem com esta tabela **dígito a dígito**
> — a medição estava certa. O que estava errado era a coluna do piso: `6,12:1` vinha rotulado
> `AAA (corpo)`, e a norma exige **7:1** para AAA em texto de corpo; e `AA+` **não é um nível
> que exista** na WCAG. Nenhum token mudou: trocar uma cor legível para perseguir um rótulo
> seria trocar uma cor boa por um adesivo bom. O piso que o teste cobra é o **4,5:1** que a
> prosa desta seção sempre exigiu, e os dois pares o cumprem com folga.

`--cor-serie-tipica` entra na tabela porque **ela não é só traço**: o mesmo valor pinta o rótulo
`mediana` na legenda, e legenda é texto. Uma cor medida apenas como linha de gráfico teria passado
sem nunca ser cobrada como texto — que é exatamente o buraco que a linha acima fecha. Medida sobre
`--cor-relevo-topo` (o extremo mais claro do gradiente da placa) ela ainda dá **9,03:1**, então o
gradiente não a derruba em ponto nenhum do painel.

Nenhum texto da tela fica abaixo de 4,5:1. **Isto é o que "o tema nunca custa legibilidade"
significa em número** — se o executor trocar um valor, a razão tem que ser recalculada, não
estimada no olho.

### O acento é reservado para — lista fechada

1. O número de **XM por milhão** no destaque.
2. A linha do **menor pedido visível** no gráfico.
3. O **título de cada painel** (`Heading`, maiúsculas).
4. O **fio de luz superior** do chanfro dos painéis (`--cor-relevo-luz` é derivado dele, não é ouro cheio).
5. O **anel de foco** do campo de câmbio e do botão.
6. O **preenchimento do botão primário** (`Salvar câmbio`).

**Nunca:** texto de corpo, rodapé, bordas gerais, fundo de painel, hover de qualquer coisa que não
esteja nesta lista.

### A hierarquia de cor carrega significado, e é isso que a justifica

| Número | Cor | Porque |
|---|---|---|
| **XM por milhão** | `--cor-ouro` | derivado **só** do que o scanner leu na tela |
| **R$ por milhão** | `--cor-texto` | derivado da leitura **× uma taxa que você digitou** |

A diferença de cor entre os dois é a diferença epistêmica entre eles. Um usuário que olha a tela de
relance vê qual metade o jogo sustenta e qual metade depende dele. Não é decoração — é o D-02 do
projeto virado em pixel.

### O gráfico não pode distinguir só por cor

| Série | Traço | Cor |
|---|---|---|
| Menor pedido visível | **sólido**, 2px | `--cor-ouro` |
| Mediana (`median_low`) | **tracejado** `[6, 4]`, 1.5px | `--cor-serie-tipica` |

Sólido × tracejado sobrevive a daltonismo, a monitor mal calibrado e a `Gamma=1.16`. Cor sozinha
não sobreviveria.

---

## Copywriting Contract

**Idioma: pt-BR.** Frases escritas por nós levam acento (é HTML em UTF-8, não há o problema de
encoding do console).

**REGRA DURA — a string que vem do Python não é reescrita no navegador.** `formatar_taxa_derivada`,
`formatar_centesimos`, `_recencia_em_duas_formas` e as frases de piso de evidência chegam prontas do
servidor, em ASCII (`"11,60 XM por milhao de adena (derivado)"`, `"ha 8 h (31/08 10:00)"`,
`"sem evidencia - 2 de 5 ofertas distintas"`). O JS **exibe como recebeu**. Acentuar no navegador
significaria um segundo formatador — exatamente o que DASH-03 proíbe ("mesma fonte, mesma conta,
sem um segundo parser"). A divergência de acentuação entre a moldura e o valor é **intencional e
fica escrita no fonte**.

| Elemento | Texto |
|----------|-------|
| CTA primário | **`Salvar câmbio`** |
| Rótulo do campo | **`1 XM = R$`** com `placeholder="0,50"`, `inputmode="decimal"` |
| Confirmação de salvo | **`Câmbio salvo — 1 XM = R$ 0,50, informado por você em 01/09 14:32.`** |
| Título — estado vazio | **`Nenhuma leitura da Adena ainda`** |
| Corpo — estado vazio | **`O painel de Adena nunca foi lido nesta máquina. Para começar: deixe o vigiar-mercado.bat rodando e abra a aba Adena da World Exchange no cliente. Cada página lida vira um ponto aqui sozinha, sem recarregar.`** |
| Prova de que não quebrou | **`O arquivo foi lido: 93 linhas, 0 da série Adena.`** — números reais, do endpoint |
| R$ indisponível | **`R$ indisponível — nenhum câmbio informado.`** + o campo logo abaixo |
| Aviso do câmbio histórico | **`R$ calculado com o câmbio informado hoje, aplicado a toda a série.`** |
| Dado velho | **`Sem leitura nova há 3 h. O valor abaixo é de 31/08 10:00, não de agora.`** |
| Servidor mudo | **`Sem contato com o servidor local há 12 s. A tela mostra a última resposta recebida, não o agora.`** |
| Erro — arquivo ausente | **`Arquivo de observações não encontrado (.mercado/observacoes.csv). O --mercado ainda não gravou nada nesta máquina. Rode o vigiar-mercado.bat uma vez.`** |
| Erro — cabeçalho quebrado | **`O cabeçalho de .mercado/observacoes.csv não é o esperado. O dashboard não vai adivinhar as colunas.`** |
| Erro — câmbio inválido | **`Câmbio não salvo: informe um número maior que zero, como 0,50.`** |
| Nota de linha parcial | **`Última linha ignorada: incompleta (o scanner estava escrevendo).`** |
| Confirmação destrutiva | **não se aplica — nenhuma ação destrutiva nesta fase.** Cada câmbio é apendado com carimbo em `.mercado/cambio.json`; nada é sobrescrito e nada é apagado. |

### Frases proibidas na tela

Herdadas de `mercado_console`, onde já há teste prendendo-as:

- **`preço de venda`**, **`vendido por`**, **`valor de mercado`** — o scanner vê **ofertas**, não
  transações. O rótulo é **`menor pedido visível`**.
- **`agora`** colado num número cuja recência passou do limiar de frescor.
- Qualquer valor em R$ sem a marca de **informado por você**.
- **`0,00`** como espaço reservado enquanto carrega. Ausência se escreve com palavra, nunca com zero.

---

## Layout & Componentes

Três regiões, em coluna, largura máxima `960px`, centralizada, margem lateral até `--sp-3xl`.

```
┌─ #destaque ────────────────────────────────────────────┐
│  QUANTO VALE 1 MILHÃO DE ADENA        (Heading, ouro)  │
│  ┌──────────────────────┐ ┌──────────────────────┐     │
│  │ 11,60         (48px) │ │ 5,80          (48px) │     │
│  │ XM por milhão  ouro  │ │ R$ por milhão pergam.│     │
│  │ n=12 · há 4 min      │ │ derivado do câmbio   │     │
│  └──────────────────────┘ └──────────────────────┘     │
└────────────────────────────────────────────────────────┘
┌─ #serie ───────────────────────────────────────────────┐
│  HISTÓRICO DA TAXA                                     │
│  [ gráfico — 2 linhas · zoom horas ↔ dias ]            │
│  legenda: ▬ menor pedido visível   ┄ mediana           │
└────────────────────────────────────────────────────────┘
┌─ #procedencia ─────────────────────────────────────────┐
│  1 XM = R$ [0,50] (Salvar câmbio)  informado 01/09 14:32│
│  fonte: .mercado/observacoes.csv · somente leitura      │
│  n=12 · oferta mais nova ha 4 min (01/09 14:28)         │
│  R$ calculado com o câmbio informado hoje...            │
└────────────────────────────────────────────────────────┘
```

### A receita do relevo — CSS puro, sem imagem

```css
.painel {
  background: linear-gradient(180deg,
              var(--cor-relevo-topo) 0%, var(--cor-painel) 42%, var(--cor-relevo-base) 100%);
  border: 1px solid var(--cor-relevo-alto);
  border-radius: 2px;                        /* L2 é anguloso, não arredondado */
  box-shadow:
    inset 0 1px 0 var(--cor-relevo-luz),     /* fio de luz no topo */
    inset 0 -1px 0 var(--cor-relevo-baixo),  /* sombra na base */
    0 2px 8px rgba(0,0,0,.55);               /* a placa flutua sobre o fundo */
  padding: var(--sp-md);
}
```

O título de cada painel leva **um filete dourado de 1px** abaixo, com `opacity: .45` — a placa
entalhada sem custar contraste ao que vem depois.

**Ornamento de canto (opcional, `--font-display`-adjacente):** no máximo **um** SVG inline de canto,
com `opacity: .28` e `pointer-events: none`, replicado nos quatro cantos por `transform`. Ele existe
sob condição: **se em qualquer largura de tela ele encostar no número de 48px, ele sai.** É a regra
do usuário aplicada literalmente.

### O componente de série é genérico (DASH-05)

A palavra `adena` **não aparece** no CSS nem no módulo do gráfico.

- Seletores: `.serie`, `.serie__linha--principal`, `.serie__linha--tipica` — nunca `.adena`.
- O componente recebe: `{ titulo, unidade, pontos[], formatador, rotulo_principal, rotulo_tipico }`.
- **O formatador vem de fora**, do `formatador_do_unitario(chave_da_serie)` do Python. Isso é o que
  faz "instanciar uma segunda série não exige código de gráfico novo" ser verdade **e** mantém o
  ponto de decisão único que a Fase 4 do mercado construiu.
- A escolha da cor de uma segunda instância é do chamador. A instância da Adena usa
  `--cor-ouro` / `--cor-serie-tipica`; a paleta é do tema, não do componente.

### O gráfico é tematizado pela superfície da própria biblioteca

A biblioteca (classe uPlot, ~40KB, arquivo único — escolha do planejador) recebe cor **em
configuração**, não por seletor CSS. Para não haver duas paletas:

```js
const css = getComputedStyle(document.documentElement);
const ouro   = css.getPropertyValue('--cor-ouro').trim();
const tipica = css.getPropertyValue('--cor-serie-tipica').trim();
const grade  = css.getPropertyValue('--cor-grade').trim();
```

**Regra:** nenhum literal hexadecimal em `dashboard.js`. A paleta mora em um lugar só —
`dashboard.css`. O planejador não pode exigir da biblioteca nada além de: duas séries, traço
sólido e tracejado, cor de eixo/grade, fonte dos rótulos, zoom e pan. Toda biblioteca dessa classe
faz isso com config.

| Elemento do gráfico | Valor |
|---|---|
| Fundo da área de plotagem | transparente (o painel já é o fundo) |
| Grade | `--cor-grade`, 1px |
| Eixos e rótulos | `--cor-texto-fraco`, 14px, `--font-num` |
| Ponto sob o cursor | círculo de 4px na cor da série |
| *Tooltip* | painel com a mesma receita de relevo, mostrando instante, os dois valores, `n` |

**Um ponto = um instante de leitura (`primeira_vez`).** Com zoom largo, vários instantes caem no
mesmo pixel e a agregação é **`median_low`, nunca média** — um número exibido tem de ter existido
(D-02). Essa escolha fica escrita no fonte, ao lado do código que a executa.

---

## Interação

| Gatilho | Comportamento |
|---|---|
| Polling (~2 s) | Sem *spinner*. Polling não é carregamento; girar um indicador a cada 2 s ao lado do jogo é ruído. |
| Valor mudou | Pulso de fundo de 200 ms no painel do número (`--cor-relevo-alto` → transparente). Nada se move, nada pisca. |
| `prefers-reduced-motion: reduce` | Todo pulso e toda transição viram `none`. Sem exceção. |
| Foco de teclado | Anel `2px` `--cor-ouro`, deslocamento `2px`. `:focus-visible`, nunca `outline: none` cru. |
| Zoom do gráfico | Roda do mouse e arrasto, pela biblioteca. Botão **`Ver todo o período`** (texto, sem ícone) restaura o alcance total — sem isso o usuário fica preso no zoom. |
| Envio do câmbio | `<form>` de verdade, `Enter` submete. Salva, mostra a confirmação, e o R$ aparece **sem recarregar**. |
| Primeira pintura | Painéis desenhados com o rótulo `Lendo o arquivo…` no lugar do número. **Nunca `0,00`.** |

---

## Estados da tela e sua precedência

Vários podem ser verdade ao mesmo tempo. A ordem é fechada, e o primeiro que casar manda no
destaque e no gráfico:

1. **Erro de contrato** (cabeçalho inesperado) → falha fechada. Sem destaque, sem gráfico, só a
   mensagem. Nunca adivinhar colunas.
2. **Arquivo ausente** → mensagem + como gerar.
3. **Sem leitura da Adena** (`n = 0`) → o estado vazio completo. **É o estado de hoje.**
4. **Abaixo do piso de evidência** → mostra o que dá, e escreve o que falta, com a frase exata do
   Python.
5. **Série presente** → destaque + gráfico normais.

**Ortogonais** — modificam a tela sem tomar a precedência:

- **Sem câmbio informado:** o cartão de R$ desaparece da tela (não fica cinza, não fica zerado). O
  cartão de XM ocupa a largura toda. O rodapé mostra o campo com `R$ indisponível`.
- **Dado velho:** a recência vira `--cor-frio` e ganha a frase de dado velho acima do destaque. O
  número continua na tela — o que sai é a **afirmação de "agora"**.
- **Servidor mudo:** faixa no topo, valores mantidos, marcados como da última resposta.

### O estado vazio, desenhado

**Gráfico vazio mudo está proibido.** A área do gráfico no estado vazio renderiza:

- Os eixos e a grade tematizados (prova de que a área existe e está viva),
- Uma placa centralizada com o título, o corpo e a linha de prova (`93 linhas, 0 da série Adena`),
- A legenda das duas linhas **já visível**, em `--cor-texto-fraco`, para o usuário saber o que vai
  aparecer.

Um retângulo em branco seria indistinguível de "o dashboard quebrou" — que é exatamente o erro que
esta fase existe para não cometer.

---

## UI Considerations

Cobertura de **estado** enraizada na forma da tela. As frases de estado vazio e de erro moram no
`## Copywriting Contract` — aqui as linhas **referenciam**, não repetem.

**Como esta seção foi produzida.** A tabela abaixo foi escrita à mão e depois **conferida pela
sonda** `ui-consideration-probe`, com os tipos de elemento autorados (`#destaque` =
`static-content`; `#serie` = `interactive-control` + `list-collection` + `static-content`;
`#procedencia` = `form` + `static-content`). A primeira passagem da sonda devolveu os três
elementos como `unclassified` — as pistas do motor são em inglês e a prosa deste documento é em
português. **Isso é registrado porque importa:** um `unclassified` que passasse batido teria
dado cobertura zero com cara de "nada se aplica". Com os tipos corrigidos a sonda levantou **16
considerações**, contra as 9 escritas à mão, e as sete a mais estão nas linhas marcadas
`(sonda)` — todas no rodapé `#procedencia`, cujo formulário não tinha estados especificados.

**Resolvidas: 16 aplicáveis — 13 ✅ covered, 3 🧪 backstop, 0 ⚠ unresolved.**

| Categoria | Elemento(s) | Status | Resolução / Razão |
|-----------|-------------|--------|---------------------|
| empty | `#destaque`, `#serie` | ✅ covered | Sem linha `adena#`, a tela renderiza a placa de estado vazio com a contagem real do arquivo e a grade do gráfico desenhada; gráfico mudo é proibido. Cópia em Copywriting. |
| loading | `#destaque`, `#serie` | ✅ covered | Primeira pintura mostra `Lendo o arquivo…` no lugar do número; `0,00` como espaço reservado é proibido. O polling seguinte não reintroduz estado de carregamento. |
| error | página inteira | ✅ covered | Três erros distintos, cada um com uma causa e um próximo passo: arquivo ausente, cabeçalho quebrado, servidor mudo. Falha fechada — nunca adivinhar coluna. Cópia em Copywriting. |
| populated | `#destaque`, `#serie`, `#procedencia` | ✅ covered | Dois números lado a lado, cada um com `n` e recência; duas linhas no gráfico; rodapé com fonte, `n`, recência e o carimbo do câmbio. |
| partial | `#destaque`, `#serie` | ✅ covered | Pisos de evidência já existem no código (`menor` n≥1, `mediana` n≥5, `tendência` n≥8). Abaixo do piso a tela mostra a frase de falta vinda do Python, nunca um número. Linha final incompleta do CSV é descartada e a nota aparece no rodapé (DASH-01). |
| overflow | `#destaque`, `#serie` | ✅ covered | Display em `clamp(32px, 6vw, 48px)` com `tabular-nums`: número grande encolhe, não quebra e não vaza. Zoom largo agrega por `median_low`, nunca média, então densidade de pontos não vira ruído. |
| long-text | `#serie` (título da série) | ✅ covered | O componente é genérico e o `nome_exibido` vem de OCR, que oscila. Título com `text-overflow: ellipsis`, uma linha, `title=` com o texto completo. Nunca invade a área do número. |
| zero-one-many | componente de série (DASH-05) | 🧪 backstop | Zero e um estão desenhados. **Muitas** séries não têm tela no v1 por decisão travada; a generalidade é provada por teste instanciando uma segunda série sem código de gráfico novo. Sem evidência explícita de que a segunda instância renderiza, isto vira `human_needed` — não passa calado. |
| stale | `#destaque`, `#procedencia` | 🧪 backstop | Com o scanner parado, o valor permanece e a recência vira `--cor-frio` com a frase de dado velho; a tela nunca afirma "agora". A regra de precedência é testável no endpoint, mas **o desenho do estado velho é verificação humana declarada** no fim da fase, como a casa já faz com OCR real. |
| long-text | `#destaque` **(sonda)** | ✅ covered | O número não é o único texto do cartão: o rótulo de unidade (`XM por milhão de adena (derivado)`) vem inteiro do Python e é longo. Ele quebra em até duas linhas dentro do cartão, `--font-num` 14px, e **nunca empurra o número de 48px** — o cartão cresce em altura, não em largura. Encurtar a string no JS é proibido: seria o segundo formatador que DASH-03 recusa. |
| error | `#procedencia` **(sonda)** | ✅ covered | **Câmbio inválido é a consideração mais cara desta tela, porque é dinheiro real.** Texto que não seja um número positivo (letras, vazio, `0`, negativo, mais de uma vírgula) **não é salvo**: o formulário recusa com uma frase que diz o que se espera (`Digite quantos reais vale 1 XM — por exemplo 0,50`), **o câmbio anterior continua valendo**, e o R$ na tela continua sendo o do câmbio antigo, nunca um valor calculado a partir do texto recusado. Falha fechada, igual ao resto do projeto. |
| empty | `#procedencia` **(sonda)** | ✅ covered | Sem nenhum câmbio já informado, o campo nasce **vazio com placeholder `0,50`** (exemplo, não valor), o carimbo de "informado em" não aparece, e a linha diz `R$ indisponível — informe o câmbio`. O cartão de R$ some do destaque pela regra ortogonal já declarada. Placeholder nunca é submetido como valor. |
| loading | `#procedencia` **(sonda)** | ✅ covered | Enquanto o `POST` do câmbio está em voo, o botão fica desabilitado com o rótulo `Salvando…`; ele **não** vira spinner e o campo não é limpo. Se a resposta demorar ou falhar, o botão volta e a frase de erro de gravação aparece — o valor digitado **permanece no campo** para o usuário não redigitar. |
| partial | `#procedencia` **(sonda)** | ✅ covered | O rodapé mostra cada peça de procedência que existe e **nomeia a que falta**, em vez de sumir com a linha: sem `n` suficiente, a frase de piso do Python; sem câmbio, `R$ indisponível`; com linha final incompleta descartada, a nota de DASH-01. Rodapé com buraco silencioso seria pior que rodapé feio. |
| overflow | `#procedencia` **(sonda)** | ✅ covered | O campo do câmbio tem `maxlength` e largura fixa em `ch`; um número absurdamente longo é recusado pela validação antes de virar layout. O caminho do arquivo na linha de fonte usa `text-overflow: ellipsis` com `title=` completo. |
| long-text | `#procedencia` **(sonda)** | 🧪 backstop | A frase de recência e a de piso de evidência vêm do Python em ASCII (`ha 8 h (31/08 10:00)`), com comprimento que varia com o estado. Elas envolvem em várias linhas sem empurrar o formulário para fora do painel. **Reacentuar ou reescrever essas strings no JS é proibido** — seria o segundo formatador. Sem teste de layout de navegador, isto fica como verificação humana declarada. |

---

## Registry Safety

Não há shadcn nem registro de componentes. **Mas há um artefato de terceiros entrando na árvore —
a biblioteca de gráfico vendorizada — e ele tem exatamente a forma de risco que esta seção existe
para conter.** O portão abaixo é obrigatório e vale como o portão de registro desta fase.

| Origem | Artefato | Portão de segurança |
|----------|-------------|-------------|
| stdlib Python (`http.server`, `json`, `pathlib`) | servidor e endpoint | não requerido |
| Código do projeto (`mercado_registro`, `mercado_analise`, `mercado_console`) | parser, contas, formatação | não requerido — é o único parser, e continua sendo |
| **Terceiro, vendorizado** | `vendor/<lib>.min.js` (classe uPlot, ~40KB, licença permissiva — **biblioteca ainda não escolhida, por decisão travada**) | **VEND-1..4, quatro tarefas separadas de plano. Incompletas no merge = BLOCK no portão de verificação.** |

### A biblioteca ainda não foi escolhida — e este documento não a escolhe

A escolha é do planejador por decisão travada no `01-CONTEXT.md` ("qual biblioteca de gráfico
exatamente" está em *Claude's Discretion*). Portanto **o portão não pode ser executado agora**: não
há arquivo para ler nem SHA-256 para calcular.

O que este contrato faz, então, é a única coisa honesta: **converter o portão em quatro tarefas de
plano separadas e individualmente verificáveis**, cada uma com o artefato que a prova. Um portão
escrito como parágrafo de intenção ("vetar antes do merge") é indistinguível de portão nenhum —
ninguém consegue apontar onde ele falhou.

### As quatro tarefas — cada uma verificável sozinha

| # | Tarefa do plano | Artefato que a prova | Como se verifica |
|---|---|---|---|
| **VEND-1** | Registrar proveniência em `vendor/README.md`: nome, versão exata, licença (MIT / Apache-2.0 / ISC — **copyleft é recusado**), URL de origem, data e **SHA-256 do arquivo vendorizado** | `vendor/README.md` | O SHA-256 do arquivo em disco bate com o registrado. É o que torna a linha conferível em vez de declaratória. |
| **VEND-2** | Ler o fonte da biblioteca procurando `fetch(`, `XMLHttpRequest`, `navigator.sendBeacon`, `eval(`, `new Function`, `import(` com URL externa, `document.createElement('script')` | Nota de revisão no `vendor/README.md`, com `arquivo:linha` para cada ocorrência | Zero ocorrências → aprovado. Qualquer ocorrência → **revisão humana explícita e registrada** antes de seguir; uma biblioteca de gráfico não precisa de nenhuma dessas primitivas. |
| **VEND-3** | Escrever `tests/test_firewall_dashboard.py` no molde do FIRE-01: `grep` sobre `vendor/*.js` que falha se qualquer primitiva de rede aparecer | O teste, verde na suíte | Roda no CI. Uma promessa que ninguém executa não vale nada; **um teste que quebra vale**. O FIRE-01 já provou o formato nesta árvore. |
| **VEND-4** | Servir a CSP abaixo em toda resposta HTML do processo Python | Teste sobre o cabeçalho da resposta do endpoint | `default-src 'none'; connect-src 'self'` presente no cabeçalho. Afirmável sem navegador, como o resto da prova desta fase. |

```
Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self';
                         connect-src 'self'; img-src 'self' data:; base-uri 'none';
                         form-action 'none'
```

A CSP torna "sem rede em tempo de execução" **estrutural, não uma intenção** — mesmo uma versão
futura da biblioteca com telemetria seria barrada pelo navegador, sem ninguém precisar reler o
`.min.js`. É o mesmo raciocínio pelo qual `pyautogui` fica fora da árvore em vez de virar uma regra
de estilo que alguém lembra de seguir.

**Consequência de projeto:** `script-src 'self'` proíbe `<script>` e `<style>` inline. Por isso
`dashboard.css` e `dashboard.js` são arquivos separados — está no topo deste documento como
restrição de entrega, não como preferência.

### A condição de bloqueio, dita por extenso

> **Biblioteca vendorizada sem VEND-1..4 completas no momento do merge é BLOCK no portão de
> verificação da fase.** Não é ressalva, não é dívida técnica anotada, não é "resolve depois". Um
> arquivo de terceiro de ~40KB minificado, executando no navegador do usuário, na mesma máquina em
> que o jogo roda e na mesma árvore em que mora o `.env` com o token do Chatwoot, **não entra sem
> as quatro provas**.

O verificador da fase cobra as quatro pelo artefato, não pela intenção: `vendor/README.md` existe e o
SHA-256 bate; a nota de revisão existe; `tests/test_firewall_dashboard.py` está verde; o cabeçalho
CSP aparece na resposta.

**Superfície do servidor:** *bind* em `127.0.0.1` apenas (travado no CONTEXT), estáticos servidos de
um diretório explícito — nunca `SimpleHTTPRequestHandler` sobre o diretório de trabalho, que
exporia a árvore inteira, incluindo o `.env` com o token do Chatwoot.

---

## Checker Sign-Off

- [x] Dimensão 1 Copywriting: PASS
- [x] Dimensão 2 Visuais: PASS
- [x] Dimensão 3 Cor: PASS
- [x] Dimensão 4 Tipografia: PASS
- [x] Dimensão 5 Espaçamento: PASS
- [x] Dimensão 6 Registry Safety: PASS

**Aprovação:** aprovado em 2026-09-01 — 6/6 dimensões, nenhum BLOCK.

### Os quatro FLAGs do checker, e o que mudou

| # | FLAG | Correção aplicada |
|---|---|---|
| 1 | Copywriting — `Ver tudo` é verbo sem objeto, ambíguo ao lado de um gráfico que já dá zoom e pan | Rótulo passou a **`Ver todo o período`**, na única ocorrência |
| 2 | Cor — três literais hexadecimais fora do bloco de tokens; a cor da mediana ficava **impronunciável** para o `getPropertyValue` do gráfico | Criados `--cor-serie-tipica`, `--cor-relevo-topo`, `--cor-relevo-base`; literais substituídos em todas as ocorrências; regra de "nenhum hex fora do bloco" escrita; `--cor-serie-tipica` **medida e adicionada à tabela de contraste (9,46:1)**, porque ela também pinta o rótulo da legenda, que é texto |
| 3 | Tipografia — o `clamp` fazia o Display renderizar num quinto tamanho, e o piso citado era o token de **espaçamento** `--sp-xl` | O piso e o teto passaram para **dentro da linha `Display`** da tabela da escala (`clamp(32–48px)`), que é onde o teto de quatro tamanhos é cobrado; registrado que 32px ali é extremo do papel Display e não parentesco com `--sp-xl` |
| 4 | Registry Safety — portão de quatro provas escrito como intenção ("antes do merge"), com a biblioteca ainda não escolhida por decisão travada | Biblioteca **não foi escolhida** (respeita o CONTEXT). O portão virou **VEND-1..4, quatro tarefas de plano separadas**, cada uma com artefato e forma de verificação; acrescentada a condição de bloqueio dita por extenso: incompletas no merge = **BLOCK no portão de verificação** |

---

## Rastreabilidade

| Requisito | Onde este contrato o atende |
|---|---|
| DASH-01 | Nota de linha parcial (Copywriting); precedência de erro; linha `somente leitura` no rodapé; UI Considerations `partial` |
| DASH-02 | Campo `1 XM = R$`, CTA `Salvar câmbio`, carimbo `informado por você`, R$ some sem taxa, aviso do câmbio de hoje |
| DASH-03 | Duas linhas sólido/tracejado, zoom, agregação `median_low`, formatador vindo do Python (sem segundo parser) |
| DASH-04 | Destaque com dois números de 48px, `n` e recência em cada, estado velho com `--cor-frio` e a frase que recusa "agora" |
| DASH-05 | Seletores `.serie*` sem `adena`, contrato de props, formatador injetado, `zero-one-many` como backstop |
| DASH-06 | Nenhum requisito visual toca o caminho do `--mercado`; a tela consome as strings dele sem reescrevê-las |
