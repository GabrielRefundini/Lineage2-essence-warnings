# Itens adiados — quick 20260904 (ETA do pack de adena)

Descobertas fora do escopo desta tarefa. **Nenhuma foi consertada aqui**, pela
regra de fronteira do executor: so se auto-conserta o que a mudanca da propria
tarefa causou.

---

## D-1 — `_linhas_do_eta` estoura as 76 colunas em DOIS dos tres casos de ausencia

**Descoberto durante:** a Tarefa 3, ao desenhar as linhas de ausencia do pack —
que tem exatamente a mesma forma.

**O que acontece.** `renda_console._linhas_do_eta` monta a linha de ausencia com
`_linha(rotulo, texto)`, que acolchoa o rotulo a `COLUNA_DO_ROTULO = 32` e soma o
texto inteiro depois. Medido chamando o proprio `renda_console._linha` de
producao (Licao 1), com o rotulo real `falta para o nivel 69`:

```
TEXTO_DA_TAXA_ZERADA    52 chars  ->  87 colunas   ESTOURA
TEXTO_DA_TAXA_NEGATIVA  53 chars  ->  88 colunas   ESTOURA
TEXTO_SEM_EVIDENCIA     38 chars  ->  73 colunas   cabe
```

O teto e `LARGURA_DO_BLOCO = LARGURA_DO_AVISO = 76` — *"a largura em que ela cabe
num console padrao de 80"*.

**Por que a suite nao pega.** `TestALarguraDoBloco` tem duas medicoes de largura e
as duas rodam com um **ETA NUMERICO** (`bloco()` traz `TempoAteONivel(segundos=
Fraction(3h20))`); a segunda troca as TAXAS por motivos longos, nao o ETA. Os dois
caminhos que estouram nunca sao renderizados sob medicao de largura.

**Por que nao foi consertado aqui.** E defeito pre-existente do `03-01`, em linha
que esta tarefa nao toca. A tarefa era o pack.

**O que a tarefa fez a respeito.** As linhas NOVAS nao repetem o defeito: elas
passam por `renda_console._linha_dobrada`, que emite o rotulo sozinho e dobra o
texto com `textwrap` contra `LARGURA_DO_BLOCO` — o teto vale por construcao e nao
por sorte. O molde ja existia em `_linhas_de_uma_taxa`; `_linhas_do_eta` e que nao
o usa. Ha teste medindo as linhas novas nos QUATRO casos
(`TestOProximoPackDeAdena::test_NENHUMA_LINHA_NOVA_PASSA_DE_76_COLUNAS`), e a
mutacao que troca `_dobrar` por `_linha` o deixa vermelho com **89 colunas**.

**O conserto, quando alguem for fazer.** Trocar as duas primeiras linhas de
`_linhas_do_eta` por `_linha_dobrada(rotulo, texto)` (a funcao ja existe e ja e
usada pelo pack), e estender `TestALarguraDoBloco` para rodar tambem com os tres
ETAs ausentes — sem isso o conserto nao tem como ficar preso.

---

## D-2 — `PYTHONPATH` com o `site-packages` do `.venv` e RECUSADO neste worktree

**Descoberto durante:** a medicao do piso da suite, antes da primeira edicao.

O comando canonico da tarefa era

```
PYTHONPATH=".;C:/Users/refun/Desktop/Lineage2-warnings/.venv/Lib/site-packages" python -m pytest
```

e o sandbox deste worktree o recusa — ele nao consegue provar que um `python` com
`PYTHONPATH` apontando para FORA do worktree nao e uma operacao de git fora do
proprio worktree. A rodada foi feita sem a variavel, no python global.

**Consequencia medida:** **87 skips** em vez dos 85 que o `quick/260903-bd8` mediu
no checkout principal. Os dois a mais sao de ambiente (bindings WinRT), e nao de
codigo. O piso desta tarefa foi medido e comparado com a variavel AUSENTE nas duas
pontas, entao a comparacao antes/depois continua valida.
