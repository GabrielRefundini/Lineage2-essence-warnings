
## 2026-08-31 — worktree com trabalho não mesclado de OUTRO agente

`worktree-agent-ad4547ac54a9fd3fe` (`.claude/worktrees/agent-ad4547ac54a9fd3fe`) contém
**3 commits que não estão no HEAD** e que **não são deste milestone**:

    d96fa45 test(discord-01): o pre-voo tem TRES saidas, e a do meio e a que salva o dia
    1e899ee feat(discord-01): a config errada morre no arranque, nomeando a chave
    a3f7295 test(discord-01): o arranque tem de morrer alto, e cada morte tem um teste

São do agente que trabalha em paralelo nesta mesma árvore. **Não foram mesclados nem
apagados por mim**, de propósito: mesclar seria decidir por outro workstream, e apagar
destruiria trabalho que não existe em mais lugar nenhum.

**Consequência operacional:** NÃO rodar `worktree.cleanup-wave` nesta árvore enquanto esses
commits existirem só ali. A limpeza por manifesto apagaria a branch junto.

Os outros três worktrees (`a04ac4d2`, `a1d2baed`, `a2bf3ab0`) estão em zero commits fora do
HEAD — já mesclados, nada a perder e nada a ganhar apagando.
