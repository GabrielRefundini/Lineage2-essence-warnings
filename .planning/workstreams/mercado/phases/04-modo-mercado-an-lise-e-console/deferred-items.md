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
