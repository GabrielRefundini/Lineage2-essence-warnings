# Itens adiados da Fase 04 — fora do escopo dos planos que os encontraram

Registro de coisas encontradas durante a execucao que NAO foram consertadas, com
o motivo. A regra de escopo e a da casa: so se conserta o que a propria task
quebrou. O resto vira linha aqui em vez de virar diff furtivo.

---

## 1. `import l2scanner.mercado_catalogo` arrasta `rastreador` e `visao` junto

**Encontrado em:** 04-01 Task 2, no RED do tripwire simetrico (2026-08-31).

**Sintoma:** o plano pedia um teste afirmando que *"o modulo de mercado,
importado, nao traz `l2scanner.rastreador` para `sys.modules` quando este ainda
nao estava la"*. O teste nasceu VERMELHO, e a causa nao e desta fase:

```
python -X importtime -c "import l2scanner.mercado_modo"

  l2scanner.mercado_pagina
    l2scanner.mercado_catalogo
      l2scanner.config
        l2scanner.notificador
          l2scanner.rastreador
            l2scanner.visao
```

A ponta da cadeia e uma linha so, em `l2scanner/mercado_catalogo.py:87`:

```python
from .config import RAIZ
```

`mercado_catalogo` quer UMA constante de caminho, e paga por ela o modulo de
configuracao inteiro — que importa o notificador, que importa o rastreador, que
importa a visao. Isso existe desde a Fase 2, antes de o modo `--mercado`
nascer.

**Por que NAO foi consertado aqui:** cortar a cadeia exige mexer em
`l2scanner/config.py` e `l2scanner/notificador.py`, que nao estao na lista de
arquivos deste plano e sao caminho quente do produto (alerta de morte). O
`rastreador.py` e intocavel por decisao explicita do `04-CONTEXT.md`, e a Task 2
tinha um teto mecanico de diff no `__main__.py` justamente porque a arvore esta
compartilhada com outro agente. Um refactor de import de tres modulos do caminho
da party, no meio de uma fase de mercado, e exatamente o tipo de diff furtivo
que este arquivo existe para impedir.

**O que foi feito no lugar:** o teste foi INVERTIDO e agora PRENDE a cadeia
preexistente (`test_o_rastreador_chega_por_uma_CADEIA_PREEXISTENTE_do_config`),
com a explicacao no corpo. Se alguem cortar a cadeia um dia, ele cai e obriga a
atualizar a historia em vez de deixar um comentario mentindo.

**O que continua provado, e e o que importa:** o mercado nao USA a party. Tres
testes seguram isso em `tests/test_mercado_firewall_de_fase.py`:

  - nenhum modulo da party e importado por `mercado_modo` (lido do AST, inclusive
    os imports adiados dentro de funcao);
  - nenhum nome no namespace de `mercado_modo` tem `__module__` de um modulo da
    party (a prova em memoria, que pega reexportacao e `getattr`);
  - `laco_do_mercado` roda inteiro com `Rastreador` substituido por um objeto que
    levanta ao ser chamado, e nao levanta.

**Quem deve pegar:** um `/gsd-quick` proprio, fora de uma fase de mercado. O
conserto plausivel e mover `RAIZ` para um modulo folha (ou calcula-lo em
`mercado_catalogo` do mesmo jeito que `config` calcula), medindo antes se algum
outro modulo depende do efeito colateral de `config` ser importado cedo.

**O que NAO fazer:** usar "o mercado ja importa o rastreador de qualquer jeito"
como licenca para acopla-los de verdade. A cadeia e de import, nao de uso, e os
tres testes acima existem para manter essa diferenca.

---

## [04-05] A recusa por OCR do `mercado_modo.py` aponta o `.bat` errado

**Achado durante:** Task 1 do 04-05, ao escrever o `vigiar-mercado.bat`.

`l2scanner/mercado_modo.py:245-252` recusa o arranque quando o OCR nao responde, e o
conselho que ela da e:

    "Rode pelo .venv (vigiar-party.bat ja faz isso). Sem OCR nao ha nome de item,
     e sem nome nao ha serie."

**Foi medido em campo em 2026-08-31**: o usuario rodou o `--mercado` pelo Python global, o
OCR nao estava la, e a mensagem mandou ele rodar o lancador da **party** para consertar o
**mercado**. Conselho torto. Agora existe o `vigiar-mercado.bat`, e e ele que a mensagem
deveria citar.

**Por que NAO foi consertado aqui:** `l2scanner/mercado_modo.py` esta **fora do
`files_modified` do 04-05**, e o criterio de aceitacao da Task 2 daquele plano
(o que exige diff vazio em `l2scanner/`) proibe explicitamente tocar naquela pasta nesta
fase. `l2scanner/ocr.py:90` tem a mesma frase, pelo mesmo motivo.

**Quem deve pegar:** um `/gsd-quick` de uma linha. O conserto e trocar o nome do `.bat`
citado nas duas mensagens (e conferir se `ocr.py:90`, que e generico, deve citar os dois).

---

## [04-05] O exemplo comentado do `config.toml` nao tem teste duravel

**Achado durante:** Task 2 do 04-05.

O criterio de aceitacao "o exemplo comentado precisa parsear quando descomentado" foi
escrito no plano como **um comando**, nao como um teste. Ele foi rodado e passou (extraiu o
bloco do fim do arquivo, descomentou, passou por `tomllib.loads` e por `ler_receitas`, e
afirmou `Dragon Belt` / `rende=1` / `Common Aztac x5` / `Leonard x20`) -- mas **nada guarda
essa propriedade daqui para a frente**.

Se alguem reescrever o comentario do `config.toml` e quebrar a sintaxe do exemplo, nenhum
teste cai, e o usuario so descobre ao descomentar e ver o arranque recusar.

**Por que NAO foi feito aqui:** o `files_modified` do 04-05 nao inclui
`tests/test_mercado_receitas.py` (o arquivo natural, entregue pelo 04-04), e o plano
especificou o criterio como comando.

**Quem deve pegar:** um `/gsd-quick`. Cinco linhas em `tests/test_mercado_receitas.py`, no
molde do que ja foi rodado.

---

## [260901-t4h] A moldura do destaque tem 153 colunas e rola para fora do console

**Achado durante:** o quick `260901-t4h` (a trava do destaque), 2026-09-01.

**Medido, e nao estimado.** Com o nome real da sessao de campo
(`Protecting Scroll: Enchant C-grade Armor`), `destaque_ao_vivo` devolve um bloco
de tres linhas de **153 colunas cada**:

```
0    ''
153  '****************************************...'
153  '  Protecting Scroll: Enchant C-grade Arm...'
153  '****************************************...'
```

A causa e `console.moldurar`, que CRESCE para caber o texto
(`largura = max(LARGURA, len(miolo) + len(carimbo))`, com `LARGURA = 58`). O
destaque carrega nome + unitario + mediana + `n` numa linha so, entao a moldura
acompanha e estoura a janela.

**O precedente do conserto ja existe nesta fase:** o `04-04` resolveu o MESMO
problema no aviso da secao de margem com `textwrap.wrap` em
`LARGURA_DO_AVISO = 76` (`l2scanner/mercado_console.py:515` e `:699`), stdlib,
sem dependencia nova, e com a razao escrita no lugar: *"QUEBRADA, e nao numa
linha so de 180 caracteres. Uma advertencia que rola para fora da janela do
console e uma advertencia que ninguem le."* A mesma frase se aplica aqui.

**Por que NAO foi consertado junto — decisao minha, do agente executor, e nao do
usuario.** O usuario pediu para alinhar *"se couber sem inchar"*, e nao coube.
Os dois caminhos possiveis sao ambos maiores que este quick:

1. **Fazer `console.moldurar` quebrar linha.** Ela e COMPARTILHADA: a docstring
   dela diz que *"o WhatsApp usa a MESMA moldura"*, e `console.destacar` a usa
   para os eventos de morte da party. Mudar a geometria dela mexeria no caminho
   quente do alerta de WhatsApp — o produto inteiro — a partir de um quick sobre
   spam de log do mercado. Isso e mudanca estrutural, e nao conserto de exibicao.
2. **Montar um bloco de varias linhas dentro de `destaque_ao_vivo`.** Isso
   contradiz uma decisao ESCRITA na propria docstring da funcao:
   *"`console.moldurar` E NAO UMA REGUA DE CARACTERES MONTADA A MAO: a geometria
   da moldura ja e uma so no projeto, e um bloco desalinhado ao lado dos outros
   pareceria outro programa."* Improvisar uma quinta geometria de moldura aqui
   seria desfazer em silencio uma decisao que o fonte defende por extenso.

**O que MUDOU, e por que o adiamento e barato agora:** antes deste quick o bloco
de 153 colunas saia a 1 Hz por oferta — pelo censo, ~10.800 linhas por hora, que
e o que destruia a forense do `scanner.log`. Com a trava ele sai UMA vez por
oferta distinta, ou seja, algumas dezenas de vezes numa sessao longa. O dano
saiu de **forense** (o log fica inutil) para **cosmetico** (uma moldura larga
rola para o lado). O problema urgente foi o que este quick consertou; o que
sobrou e o desconforto visual.

**Quem deve pegar:** um `/gsd-quick` proprio, com `l2scanner/console.py` no
`files_modified` e `tests/test_console.py` + `tests/test_notificador.py` na
verificacao — porque o que se decide la e a geometria do bloco que vai para o
WhatsApp tambem. O conserto plausivel e dar a `moldurar` um parametro de largura
maxima com o padrao de HOJE (crescer), para que nenhum chamador existente mude
de comportamento, e so o destaque pedir a quebra em `LARGURA_DO_AVISO`.

**O que NAO fazer:** encurtar o texto do destaque para caber em 58 colunas. A
mediana de referencia e o `n` estao ali por exigencia do ANAL-02, e a docstring
de `destaque_ao_vivo` explica que sem eles *"esta barata"* vira *"uma opiniao com
cara de medicao, e o usuario nao teria como discordar"*. Caber na moldura nao
vale perder a evidencia.
