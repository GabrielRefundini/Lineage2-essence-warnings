---
phase: 1
slug: dashboard-do-cambio-ao-vivo
workstream: dashboard
status: draft
shadcn_initialized: false
preset: none
created: 2026-09-01
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
| Display | 48px | 700 | 1.1 | `--font-num` — **os dois números de agora** |

**Guarda de estouro do Display:** `font-size: clamp(32px, 6vw, 48px)`. Os dois extremos são tokens
declarados da escala tipográfica/espacial; um número muito grande **encolhe, nunca quebra linha e
nunca vaza do painel**.

**Regra dura:** o Display usa `--font-num`, não `--font-display`. A fonte de fantasia é para o
título da placa; o valor que decide dinheiro é lido em monoespaçada tabular. Se as duas
disputarem, **o ornamento sai** — é a regra do usuário aplicada à tipografia.

---

## Color

Paleta tirada da cromática do painel do cliente de L2: carvão quente, relevo em madeira/bronze,
dourado nas letras, pergaminho no corpo. **Toda ela é CSS puro** — gradientes, bordas e sombras.
Nenhuma textura, nenhum print do jogo, nenhum asset que não exista no repositório.

| Papel | Valor | Uso |
|-------|-------|-----|
| Dominante (60%) | `#14110D` | fundo da página |
| Secundária (30%) | `#1F1A14` | painéis (destaque, gráfico, rodapé) |
| Acento (10%) | `#E0B450` | lista explícita abaixo |
| Destrutiva / ausência | `#E06A5C` | ausência de dado e erro de contrato — **e nada mais** |

### Tokens completos

```css
--cor-fundo:        #14110D;  /* 60% */
--cor-painel:       #1F1A14;  /* 30% */
--cor-relevo-baixo: #0B0906;  /* sombra do chanfro */
--cor-relevo-alto:  #3A3026;  /* borda do chanfro */
--cor-relevo-luz:   #5A4A35;  /* fio de luz superior do chanfro */
--cor-ouro:         #E0B450;  /* 10% — acento */
--cor-texto:        #E8E0D0;  /* pergaminho: corpo e o número em R$ */
--cor-texto-fraco:  #A79880;  /* n, recência, procedência do rodapé */
--cor-alerta:       #E06A5C;  /* ausência / erro */
--cor-frio:         #9FB0C4;  /* dado velho: recência estourada */
--cor-grade:        #2A231A;  /* linhas de grade do gráfico */
```

### Contraste — medido, não estimado

| Par | Razão | Piso |
|---|---|---|
| `--cor-texto` sobre `--cor-fundo` | **14,35:1** | AAA |
| `--cor-ouro` sobre `--cor-painel` | **8,90:1** | AAA |
| `--cor-texto-fraco` sobre `--cor-painel` | **6,13:1** | AAA (corpo) |
| `--cor-alerta` sobre `--cor-painel` | **5,25:1** | AA+ |
| `--cor-frio` sobre `--cor-painel` | **7,80:1** | AAA |

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
| Mediana (`median_low`) | **tracejado** `[6, 4]`, 1.5px | `#C9BFA8` |

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
  background: linear-gradient(180deg, #241E17 0%, var(--cor-painel) 42%, #171310 100%);
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
  `--cor-ouro` / `#C9BFA8`; a paleta é do tema, não do componente.

### O gráfico é tematizado pela superfície da própria biblioteca

A biblioteca (classe uPlot, ~40KB, arquivo único — escolha do planejador) recebe cor **em
configuração**, não por seletor CSS. Para não haver duas paletas:

```js
const css = getComputedStyle(document.documentElement);
const ouro = css.getPropertyValue('--cor-ouro').trim();
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
| Zoom do gráfico | Roda do mouse e arrasto, pela biblioteca. Botão **`Ver tudo`** (texto, sem ícone) restaura o alcance total — sem isso o usuário fica preso no zoom. |
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

**Resolvidas: 9 aplicáveis — 7 ✅ covered, 2 🧪 backstop, 0 ⚠ unresolved.**

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

---

## Registry Safety

Não há shadcn nem registro de componentes. **Mas há um artefato de terceiros entrando na árvore —
a biblioteca de gráfico vendorizada — e ele tem exatamente a forma de risco que esta seção existe
para conter.** O portão abaixo é obrigatório e vale como o portão de registro desta fase.

| Origem | Artefato | Portão de segurança |
|----------|-------------|-------------|
| stdlib Python (`http.server`, `json`, `pathlib`) | servidor e endpoint | não requerido |
| Código do projeto (`mercado_registro`, `mercado_analise`, `mercado_console`) | parser, contas, formatação | não requerido — é o único parser, e continua sendo |
| **Terceiro, vendorizado** | `vendor/<lib>.min.js` (classe uPlot, ~40KB, licença permissiva) | **leitura do fonte + proveniência + teste de firewall + CSP — as quatro, antes do merge** |

### O portão, em quatro provas

1. **Proveniência escrita** em `vendor/README.md`: nome, versão exata, licença (MIT/Apache-2.0/ISC —
   copyleft é recusado), URL de origem, **SHA-256 do arquivo**, e a data. É o que o CONTEXT já exige;
   o SHA-256 é o que torna a linha verificável em vez de declaratória.
2. **Leitura do fonte** procurando: `fetch(`, `XMLHttpRequest`, `navigator.sendBeacon`, `eval(`,
   `new Function`, `import(` com URL externa, e `document.createElement('script')`. Uma biblioteca de
   gráfico não precisa de nenhum deles. **Qualquer ocorrência bloqueia o merge** até o desenvolvedor
   revisar e aprovar explicitamente, com a linha citada por arquivo:linha.
3. **Teste de firewall** — `tests/test_firewall_dashboard.py`, no mesmo molde do FIRE-01: um `grep`
   sobre `vendor/*.js` que falha se qualquer primitiva de rede aparecer. Uma promessa de que "não vai
   para a rede" que ninguém executa não vale nada; **um teste que quebra no CI vale**. O FIRE-01 já
   provou que esse formato funciona nesta árvore.
4. **CSP servida pelo próprio servidor**, em todas as respostas HTML:

   ```
   Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self';
                            connect-src 'self'; img-src 'self' data:; base-uri 'none';
                            form-action 'none'
   ```

   Isto torna "sem rede em tempo de execução" **estrutural, não uma intenção** — mesmo uma versão
   futura da biblioteca com telemetria seria barrada pelo navegador. É o mesmo raciocínio pelo qual
   `pyautogui` fica fora da árvore em vez de ficar numa regra de estilo.

   **Consequência de projeto:** `script-src 'self'` proíbe `<script>` e `<style>` inline. Por isso
   `dashboard.css` e `dashboard.js` são arquivos separados — está no topo deste documento como
   restrição de entrega, não como preferência.

**Superfície do servidor:** *bind* em `127.0.0.1` apenas (travado no CONTEXT), estáticos servidos de
um diretório explícito — nunca `SimpleHTTPRequestHandler` sobre o diretório de trabalho, que
exporia a árvore inteira, incluindo o `.env` com o token do Chatwoot.

---

## Checker Sign-Off

- [ ] Dimensão 1 Copywriting: PASS
- [ ] Dimensão 2 Visuais: PASS
- [ ] Dimensão 3 Cor: PASS
- [ ] Dimensão 4 Tipografia: PASS
- [ ] Dimensão 5 Espaçamento: PASS
- [ ] Dimensão 6 Registry Safety: PASS

**Aprovação:** pendente

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
