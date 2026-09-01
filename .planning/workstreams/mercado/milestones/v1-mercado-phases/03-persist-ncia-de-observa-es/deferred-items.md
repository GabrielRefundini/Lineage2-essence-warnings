# Itens adiados da Fase 03 — fora do escopo dos planos que os encontraram

Registro de coisas encontradas durante a execucao que NAO foram consertadas, com
o motivo. A regra de escopo e a da casa: so se conserta o que a propria task
quebrou. O resto vira linha aqui em vez de virar diff furtivo.

---

## 1. `test_mercado_leitura.py::TestOAcordoEntreAsDuasEscalas::test_as_duas_leitoras_sao_CHAMADAS_em_toda_linha_que_vira_LinhaLida` esta VERMELHO na base

**Encontrado em:** 03-02, na suite completa de verificacao (2026-08-31).

**Sintoma:** o teste falha, e falha TAMBEM em isolamento (`pytest <so ele>`), com
quatro avisos identicos:

```
WARNING l2scanner.mercado_leitura:1615 linha 0 RECUSADA (numero): a coluna Total nao se leu inteira
WARNING ... linha 1 ... linha 2 ... linha 3 (idem)
```

Nenhuma linha do `janela_negociacao_f010.png` sobrevive a leitura de numero,
entao `len(ambas) > 0` cai. Os vizinhos da mesma classe passam porque um afirma
so que os dois recortes sao o mesmo objeto e o outro afirma `linhas == ()`, que
e verdade trivial quando tudo foi recusado.

**Por que NAO foi consertado aqui:** e da Fase 2 e nao tem nenhum vinculo com o
que o 03-02 mexeu. O 03-02 alterou quatro arquivos — `.gitignore`,
`l2scanner/__main__.py`, `l2scanner/mercado_registro.py` e
`tests/test_mercado_registro.py` — e NENHUM deles aparece no grafo de import de
`tests/test_mercado_leitura.py`:

```
grep -n "__main__\|mercado_registro" tests/test_mercado_leitura.py \
    l2scanner/mercado_leitura.py l2scanner/mercado_pagina.py \
    l2scanner/mercado_visao.py tests/conftest.py   ->  zero linhas
```

Python nao e afetado por arquivo que nunca importa, e o teste falha em processo
limpo sem nenhum teste do 03-02 coletado. A conclusao que da para afirmar: ele ja
estava vermelho no commit-base `f03eee80` desta arvore.

**A discrepancia que fica aberta, e ela e o achado:** a wave 1 mediu, no
commit-base `0820587`, **2754 passed, 23 skipped, zero failed**. Nesta arvore, no
commit-base `f03eee80` (que ja inclui a wave 1), a mesma suite da **1 failed**.
Ou alguma coisa entre os dois commits o quebrou, ou a medicao da wave 1 nao
alcancou este arquivo. As duas hipoteses cabem, e nenhuma delas se resolve de
dentro do 03-02.

**Quem deve pegar:** o portao humano do 03-03, ou um `/gsd-debug` proprio. Os
dois primeiros passos, na ordem: rodar o teste no commit `0820587` para datar a
quebra, e comparar a versao de `opencv-python` desta maquina com a da medicao,
porque leitura de digito por casamento de molde e sensivel a isso.

**O que NAO fazer:** relaxar o assert. Ele existe para pegar exatamente o defeito
de "leu com uma escala so", e um teste afrouxado aprovaria esse defeito calado.
