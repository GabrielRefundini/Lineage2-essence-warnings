---
quick_id: 260826-lcl
slug: membros-fora-do-git
created: 2026-08-26
autonomous: true
files_modified:
  - l2scanner/config.py
  - config.toml
  - .gitignore
  - README.md
  - tests/test_config.py
---

# Os `[[membro]]` saem do arquivo versionado

## O problema

O `config.toml` e VERSIONADO, e ele mesmo declara, no comentario do bloco de
membros: *"Descomente e troque pelos seus. O arquivo do repositorio nao carrega
telefone de ninguem."*

Hoje o usuario precisou por cinco telefones reais de party-mates ali para o
`.join` funcionar. Isso poe telefone de OUTRAS PESSOAS num arquivo rastreado —
e telefone que entra em historico de git nao sai mais, nem apagando depois.
O usuario ja falou em abrir PR desta branch, entao isto nao e hipotetico.

## Por que NAO simplesmente por o config.toml no .gitignore

Foi a primeira ideia, e ela quebra um guarda real. `tests/test_agenda.py`
`TestAgendaRealDoUsuario` (linha ~529) le o `config.toml` DO REPOSITORIO e
afirma os horarios de TvT, Prime e Solo Boss. A docstring diz por que:

> Estes testes existem para pegar um dedo errado no arquivo. A agenda e dado,
> nao codigo — mas um dado errado aqui significa a party esperando um TvT que
> nao vai acontecer, ou perdendo um que vai.

Se o arquivo sair do git, esse teste passa a vigiar um `config.exemplo.toml`
que ninguem usa. O guarda continua verde e para de guardar — que e pior do que
nao existir, porque parece protecao.

## A correcao

Um segundo arquivo, `config.local.toml`, no `.gitignore`, carregando SO os
`[[membro]]`. A agenda continua no `config.toml` versionado e continua guardada
pelo teste. Os telefones ficam na maquina.

Separacao pela mesma linha que o projeto ja usa entre `config.toml` e
`calibration.json`: o que e do PROJETO e versionado, o que e da MAQUINA nao.
Telefone de party-mate e da maquina.

## Tarefas

### Tarefa 1 — `ler_membros` passa a ler o arquivo local

<read_first>
- `l2scanner/config.py` — `ler_membros` e a validacao de nick duplicado que ela ja faz
- `tests/test_config.py` (ou onde os testes de `ler_membros` moram — procure)
</read_first>

<action>
`ler_membros()` passa a ler `config.local.toml` quando ele existe, e continua
lendo `config.toml` quando ele NAO existe.

**Precedencia e um ou outro, nunca soma.** Se o local existe, ele e a fonte
inteira dos membros. Somar os dois arquivos faria um nick removido do
`config.toml` reaparecer pelo local sem ninguem entender por que, e a validacao
de nick duplicado teria que decidir qual dos dois ganha — decisao que nao tem
resposta obvia e que ninguem quer descobrir as 2h da manha.

Quando os DOIS tem `[[membro]]`, avisar alto no arranque que o `config.toml`
esta sendo ignorado, nomeando o arquivo que venceu. Um bloco que nao faz nada e
invisivel; um bloco que nao faz nada e nao avisa e uma armadilha.

A validacao que ja existe (nick duplicado, minimo de digitos) vale igual, venha
de onde vier — nao duplicar a regra num segundo caminho.

RED antes: teste com `tmp_path` cobrindo os quatro estados — so config.toml; so
config.local.toml; os dois (local vence + aviso); nenhum dos dois (lista vazia,
sem erro).
</action>

<acceptance_criteria>
- Com `config.local.toml` presente, os membros vem dele e os do `config.toml` sao ignorados
- Sem ele, o comportamento de hoje e identico — nenhum teste existente muda
- Os dois presentes: o local vence E o arranque avisa, nomeando os dois arquivos
- Nenhum dos dois: lista vazia, sem excecao
- A validacao de nick duplicado e de digitos minimos vale nas duas origens, escrita UMA vez
</acceptance_criteria>

### Tarefa 2 — o repositorio volta a nao carregar telefone de ninguem

<read_first>
- `config.toml` — o bloco de comentario dos `[[membro]]`, linhas ~68-112
- `.gitignore` — em especial o comentario do `.env` e o do `calibration.json`,
  para escrever a entrada nova no mesmo idioma
- `README.md` — a secao de instalacao/configuracao
</read_first>

<action>
1. Criar `config.local.exemplo.toml` versionado: so o cabecalho explicativo e
   dois `[[membro]]` comentados. Curto — quem le ja leu a explicacao longa no
   `config.toml`.
2. Tirar os cinco `[[membro]]` reais do `config.toml` e devolve-lo ao estado do
   repositorio (bloco comentado). **Os cinco reais vao para
   `config.local.toml`, que NAO e commitado** — o arquivo ja existe na maquina
   do usuario quando voce terminar, senao o scanner dele para de reconhecer a
   party.
3. `.gitignore`: `config.local.toml`, com comentario explicando POR QUE (telefone
   de terceiro em historico de git nao sai mais), na mesma voz das outras entradas.
4. Atualizar o comentario do `config.toml` para apontar o arquivo novo, e o
   `README.md` para mencionar o passo.

**Cuidado de execucao:** o usuario tem um scanner RODANDO agora que carregou os
membros do `config.toml`. Nao apague os cinco blocos sem antes ter escrito o
`config.local.toml` com eles.
</action>

<acceptance_criteria>
- `git status --porcelain config.local.toml` nao mostra nada: o arquivo e ignorado
- `git show HEAD:config.toml | grep -c "^\[\[membro\]\]"` devolve 0 apos o commit
- O `config.local.toml` na maquina tem os cinco membros e o scanner os carrega
- `TestAgendaRealDoUsuario` continua lendo o `config.toml` versionado e verde
- README menciona o arquivo novo
</acceptance_criteria>

## Restricoes do projeto

- Portugues SEM acento em identificador, docstring, comentario e texto de WhatsApp
- Nenhuma dependencia nova (`tomllib` e stdlib)
- Baseline: `python -m pytest tests/ -q` -> **1066 passed, 2 skipped**. Usar o
  `python` do sistema (o `.venv` nao tem pytest). Nenhum teste enfraquecido.
- NAO commitar `config.local.toml` nem os telefones em lugar nenhum
