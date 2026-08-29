# Evidência: o OCR do Windows lê NOME, não lê NÚMERO

**Medido em:** 2026-08-29
**Contra:** as gravações de campo da Fase 1 (`recordings/2026 0828-*-mercado-*`)
**Ferramenta:** `l2scanner.ocr._reconhecer` (Windows.Media.Ocr via WinRT), escalas 2x/3x/4x
**Ambiente:** bindings `winrt-*` 3.2.1 já instaladas no `.venv`; `C:\Windows\OCR` traz `en-us` e `pt-br`

> Esta medição EXISTE PORQUE A EXCLUSÃO NÃO TINHA NENHUMA. A linha
> `| OCR aberto para nomes de item | ... |` da tabela Out of Scope nasceu em
> `db751c7` (2026-08-27), e a primeira gravação do World Exchange é de
> 2026-08-28 05:31. O OCR foi descartado **um dia antes de existir um frame do
> mercado no disco**. A justificativa escrita — "a watchlist é conjunto fechado" —
> é uma decisão de PRODUTO registrada como se fosse um achado TÉCNICO. O que caiu
> em 2026-08-29 não foi uma medição: foi a premissa.

## Metodologia

Para seis frames de gravações distintas: localizar o painel por âncora
(`localizar_painel`), recortar a região da grade a partir de `mercado_grade`,
fatiar as 10 linhas de 45 px e passar cada linha inteira pelo motor em três
escalas. Sem pré-processamento além do cinza que `_reconhecer` já faz (D-a).

O painel foi localizado em 6 de 6 frames, incluindo o frame com tooltip aberta e
o frame com marcação de alvo sobreposta.

## Resultado 1 — os NOMES são lidos, e de forma estável

```
Relic Summon Coupon - 1-time
Earth Spirit Evolution Stone
Common Aztac
Common Aztac M. Def. +200
Common Fafuri
```

Erros observados são de baixa amplitude e majoritariamente CONSISTENTES dentro de
uma mesma escala (`I-time` por `1-time`). O erro que varia com a escala —
`Evolution` (2x, 3x) contra `Ewlution` (4x) — é o argumento para FIXAR uma escala
de leitura de nome, e não para alternar entre elas.

Isto basta para agrupamento por similaridade: o objetivo não é obter o nome
verdadeiro, é obter uma CHAVE ESTÁVEL mais um rótulo legível que o usuário
corrige uma vez.

## Resultado 2 — os NÚMEROS não são lidos, e o modo de falha é o pior possível

A vírgula decimal DESAPARECE. Amostras do mesmo recorte em escalas diferentes:

| frame / linha | 2x | 3x | 4x |
|---|---|---|---|
| mercado-aberto f100 #8 | `1650` | `16,50` | `1650` |
| pagina-cheia #8 | `750` | `7,50` | `750` |
| mercado-aberto f100 #2 | `026` | `or26` | *(omitido)* |
| mercado-aberto f100 #4 | `033` | *(omitido)* | `or33` |
| tooltip #3 | `380,00` | `380,00` | `380m` |
| tooltip #2 | `79;00` | `79,00` | `79m` |

`16,50` lido como `1650` é erro de 100x que produz um número PLAUSÍVEL. É
exatamente a família de defeito que LEIT-02 existe para impedir, e é a razão de a
vírgula ser um dos 13 moldes de dígito já cortados e certificados na Fase 1
(pior par inter-classe `0`×`8` = 0.7110; limiar 0.8554).

**Conclusão travada: nome por OCR, preço e quantidade por molde. LEIT-02 não muda.**

## Resultado 3 — a tooltip VAZA para dentro da linha (achado não previsto)

No frame `20260828-061253-mercado-tooltip/frame_000010.png`, lendo a linha
INTEIRA, o texto da tooltip entra na leitura misturado ao nome do item:

```
linha 5: 'In case of success, you will get a Common Fafuri 1 higher-level doll that cannot be 125,00 XM Coin'
linha 7: 'Common Fafuri Can be stored in the private warehouse and transferred within the 1 140,00 XM Coin'
```

Sem defesa, `Can be stored in the private warehouse` vira nome de item e cria uma
série fantasma no CSV. Duas defesas, e as duas são baratas:

1. **Recortar SOMENTE a coluna do nome**, não a linha inteira. A coluna do nome
   ainda NÃO está calibrada — `mercado_grade` só tem a grade de linhas.
   Isto é requisito novo, e é o único item desta mudança que toca a calibração.
2. O acordo entre dois frames consecutivos que LEIT-03 já exige.

## Reprodução

O script do spike é descartável e viveu no scratchpad da sessão. Para refazer:
localizar o painel com `mercado_visao.localizar_painel`, recortar por
`mercado_grade`, fatiar em `altura_da_linha`, chamar `l2scanner.ocr._reconhecer`
por escala. Roda contra `recordings/`, que é somente-leitura e só existe no
checkout principal.
