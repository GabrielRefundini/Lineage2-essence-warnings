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
