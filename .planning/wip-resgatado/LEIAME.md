# WIP resgatado antes da higiene de worktrees (2026-09-03)

## `discord-ponte-nao-commitado-20260903.patch`

Quatrocentas e quarenta linhas de trabalho **nao commitado** que viviam no worktree
`.claude/worktrees/agent-ad4547ac54a9fd3fe`, em `l2scanner/ponte_discord.py` (+288) e
`l2scanner/ponte_nucleo.py` (+176). Nenhum processo estava mexendo nelas no momento do
resgate.

**Por que virou patch e nao commit.** Os TRES commits terminados daquela branch
(`discord-01`) foram mesclados no tronco normalmente. Estas alteracoes soltas, nao. Elas
nao passaram por teste nem por revisao, e empurrar trabalho pela metade para o tronco
compartilhado — onde outros agentes trabalham — trocaria a limpeza por um risco maior do
que ela resolve. Um patch nao roda sozinho; um commit no tronco, sim.

**Como retomar:**

    git apply .planning/wip-resgatado/discord-ponte-nao-commitado-20260903.patch

Se o `ponte_discord.py` ou o `ponte_nucleo.py` tiverem andado desde entao, o `git apply`
vai recusar em vez de estragar — e ai o caminho e `git apply --3way`, que resolve o que
consegue e deixa os conflitos marcados.

**Quando apagar:** depois de o trabalho ser retomado e commitado, ou depois de quem o
escreveu decidir que nao serve mais. Ate la ele e a unica copia.
