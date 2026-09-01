---
slug: redesenho-do-sinal-de-oclusao
workstream: mercado
created: 2026-09-01
status: investigating
severity: alta
hypothesis: >
  A premissa do sinal esta errada, nao a sua posicao. "Existe uma faixa
  HORIZONTAL vazia a direita do nome" e falso para os nomes reais do mercado do
  usuario. Mover a faixa so adia o defeito ate o proximo item de nome mais longo.
next_action: >
  MEDIR sinais alternativos que nao competem com o texto (margens verticais da
  linha; a moldura entre linhas) contra o gabarito COM os frames de nome longo.
---

# O sinal de oclusao precisa parar de depender de espaco vazio horizontal

## O que ja falhou, duas vezes, medido

**Sonda original `207..417`** — sobrepunha 159 px da coluna do nome (49% dela).
Recusava as 4 linhas de `Protecting Scroll: Enchant C-grade Armor` (40 chars).
Consertado em 31/08 movendo para `246..396`.

**Sonda atual `246..396`** — RECUSA AS DEZ LINHAS de
`Protecting Scroll: Enchant C-grade Weapon` (41 chars).

    gravacao: recordings/20260901-000043-nome-longo-weapon (5 frames, janela completa)
    ponta da tinta: 255 em TODAS as 10 linhas, em TODOS os 5 frames
    sonda dx0:      246
    MARGEM:         -9 px

## A progressao que prova a premissa errada

    nome                                 chars   ponta da tinta
    Protecting Scroll: Enchant C-grade Armor    40   247
    Protecting Scroll: Enchant C-grade Weapon   41   255

Um caractere empurrou 8 px. A sonda em 246 ja estava **1 px atras** do `Armor` —
o conserto de 31/08 nasceu com margem NEGATIVA e passou nos testes porque o
gabarito nao continha o pior caso. **E o mesmo defeito do GABARITO_LIMPAS,
repetido seis horas depois por quem o consertou.**

Nomes mais longos existem (`...Enchant B-grade Weapon`). Mover de novo adia.

## O que a investigacao anterior ja mediu, e que sustenta o redesenho

- **Nao existe faixa horizontal limpa de 210 px no pior caso.** Maximo 172 px
  contra frames verificados; **56 a 91 px contra o censo de 3994 linhas**. A
  sonda precisa de 150.
- **O corredor alternativo `433..514` esta DESQUALIFICADO**: uma linha coberta
  le dispersao 0,0000 dentro dele — seria CEGO para tooltip.
- **Em todos os candidatos quem aperta e o MARCADOR DE ALVO** (0,077 / 0,022 /
  0,021), nunca a tooltip (0,32 a 0,62).

## Direcoes a MEDIR (nenhuma escolhida)

1. **Margens VERTICAIS da linha** — a linha tem 45 px de altura e o glifo nao
   ocupa tudo. Espaco acima/abaixo do texto existe por construcao, e nao encolhe
   quando o nome cresce.
2. **A moldura entre linhas** — separador da grade, desenho FIXO da UI, com
   tamanho independente do nome.

Qualquer uma precisa ser medida contra o gabarito COM os frames de nome longo,
e precisa mostrar separacao entre linha limpa e linha coberta comparavel ou
melhor que a atual.

## Restricoes invioláveis

- **NAO afrouxar o sinal.** Ele e a guarda contra tooltip SEMITRANSPARENTE — ela
  nao apaga o numero, ela o MISTURA, e numero misturado produz glifo plausivel
  com valor errado e confianca alta. E o modo de falha do incidente 27x.
- **NAO baixar** `mercado_minimo_de_linhas_comparadas` (7).
- Limiar mora no `calibration.json`, NUNCA no fonte.
- **O gabarito da ferramenta TEM de incluir os frames de nome longo**, e
  `conferir_o_gabarito_limpo` deve reprovar varredura sem eles.
- **NAO escrever** em `calibration.json` sem dizer ao usuario o comando; **NAO
  escrever** em `.mercado/`.
- **NAO tocar** `rastreador.py` nem o gate de brilho da barra propria em
  `visao.py`. Nao tocar `respawn.py`, `bosses.py`, `agenda.py`, `sessao.py`,
  `test_bosses.py` — outro agente trabalha neles nesta arvore.
- `recordings/` e somente-leitura. **NUNCA usar glob amplo nela** — `pre-voo`
  sozinha tem 1502 PNGs e varreduras assim ja mataram dois agentes por rate
  limit. As gravacoes uteis aqui sao nomeadas: as 8 do censo mais
  `20260901-000043-nome-longo-weapon`.
- Nenhuma dependencia nova (FIRE-01). Nenhum `--amend`.

## Se a conclusao for que nenhum sinal serve

E um achado legitimo. Reporte em vez de forcar — e nesse caso o paliativo
declarado e voltar a sonda para `207..417`, que ao menos le os nomes curtos.
