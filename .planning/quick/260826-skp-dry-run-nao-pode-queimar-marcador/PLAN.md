---
quick_id: 260826-skp
slug: dry-run-nao-pode-queimar-marcador
created: 2026-08-26
autonomous: true
files_modified:
  - l2scanner/agenda.py
  - l2scanner/sessao.py
  - l2scanner/__main__.py
  - tests/test_agenda.py
  - tests/test_sessao.py
---

# O `--dry-run` nao pode queimar marcador da instancia real

## O defeito, medido em campo

Hoje, 2026-08-26 as 19:30, uma simulacao (`--so-agenda --dry-run`) rodava ao mesmo
tempo que o scanner de verdade do usuario. O marcador
`.agenda/2026-08-26_tvt-1930_agora` foi escrito as **19:30:00.629** e o
`outbox.jsonl` registra o envio real no mesmo instante — a instancia REAL ganhou a
corrida do `O_EXCL` por milissegundos e a mensagem saiu.

Foi sorte. Se a simulacao tivesse ganhado, `registro.marcar()` teria devolvido
`True` para ela e `False` para a instancia real, e o aviso das 19:30 **nunca teria
sido enviado** — sem erro, sem log, sem nada. O modo que existe para nao ter efeito
colateral e o unico que pode apagar um aviso.

A causa e que `marcar` roda ANTES de qualquer checagem de despacho, e nao olha
para `dry_run`. Isso e correto por si so — a docstring de
`RegistroEmDisco.marcar` exige exatamente isso ("A decisao de despachar tem que
ser esta chamada, nunca uma checagem anterior"), e e o que garante que as duas
instancias do usuario nao anunciem em dobro. O erro nao esta no `marcar`: esta em
deixar um processo que NAO vai despachar participar da disputa.

## Sao QUATRO sitios, nao um

- `l2scanner/sessao.py:283` — laco principal
- `l2scanner/sessao.py:358` — laco principal
- `l2scanner/__main__.py:1113` — `laco_da_agenda`, o `--so-agenda`
- `_processar_agenda` (`__main__.py:~1005`) — o `fechado_` que a Fase 10 acrescentou

Por um `if args.dry_run:` em cada chamada resolve os quatro de hoje e **garante que
o quinto nasca errado** — e a mesma forma do defeito da poda que a Fase 10 acabou
de consertar (`_PREFIXOS_CONHECIDOS`), e da recusa derivada de `set(Comando)` do
plano 10-01. A correcao tem que ser estrutural, num lugar so.

## Abordagem

Fazer o REGISTRO saber que esta simulando, e nao cada chamador.

`RegistroEmDisco(pasta, simulando=False)`. Quando `simulando` e verdadeiro,
`marcar` devolve `True` sem tocar no disco: o processo se comporta como se
tivesse ganhado (para o console mostrar o aviso, que e o ponto do `--dry-run`) e
nao disputa nada com ninguem. `enviados()` continua LENDO normalmente — uma
simulacao deve enxergar o que ja foi enviado de verdade, senao ela mente sobre o
que teria acontecido.

Os quatro sitios passam a herdar o comportamento sem saber que ele existe, e um
quinto sitio futuro nasce correto.

`montar_despachante` ja imprime "Modo simulacao: alertas so no console, nada e
enviado". Essa frase agora esta incompleta e vira mentira parcial: ela promete que
nada e enviado, sem dizer que o disco tambem nao e tocado. Completar.

## Tarefas

### Tarefa 1 — o registro passa a saber que esta simulando

<read_first>
- `l2scanner/agenda.py` — a classe `RegistroEmDisco` inteira, com atencao a
  docstring de `marcar` (a razao do `O_CREAT|O_EXCL` e do tri-estado)
- `tests/test_agenda.py` — a classe de testes do registro, para escrever o novo
  no mesmo idioma
</read_first>

<action>
RED primeiro: um teste com dois `RegistroEmDisco` sobre a MESMA pasta, um
`simulando=True` e outro normal, provando que:

1. o simulando devolve `True` no `marcar` e **nao cria arquivo nenhum** (comparar
   `sorted(pasta.iterdir())` antes e depois);
2. o real, marcando a MESMA chave depois, tambem devolve `True` — ou seja, a
   simulacao nao roubou a vez dele. Este e o teste que reproduz o incidente de
   campo e o que falha sem o conserto;
3. `enviados()` do simulando continua enxergando o que o real ja escreveu.

Depois o conserto em `agenda.py`. A docstring de `marcar` tem que explicar POR QUE
o simulando devolve `True` sem escrever — nao e "nao faz nada", e "finge que
ganhou para o console funcionar, sem tirar a vez de quem vai mesmo falar" — e
citar a data e a hora do incidente, na disciplina do resto do arquivo.

`podar()` no construtor: decidir explicitamente se roda em modo simulacao. Ela
APAGA arquivo. Uma simulacao que poda mexe no disco compartilhado, o que
contradiz a razao inteira desta correcao — nao deve rodar. Escrever a decisao.
</action>

<acceptance_criteria>
- Um `RegistroEmDisco(simulando=True)` nao cria nem apaga um unico arquivo, provado
  por comparacao do conteudo da pasta antes e depois
- Marcar a mesma chave no simulando NAO impede o registro real de marca-la depois
- `enviados()` continua lendo o disco de verdade nos dois modos
- Sem o conserto, o teste do item 2 falha — confirmar rodando contra o codigo antigo
</acceptance_criteria>

### Tarefa 2 — os quatro sitios herdam, e o console para de mentir

<read_first>
- `l2scanner/__main__.py:179-195` (`montar_despachante`, onde a frase de simulacao
  e impressa hoje)
- `l2scanner/__main__.py:1054-1130` (`laco_da_agenda`)
- `l2scanner/sessao.py:270-365` (os dois `marcar` do laco principal)
</read_first>

<action>
Passar `simulando=args.dry_run` na construcao do `RegistroEmDisco` nos dois lacos.
Nenhum `if args.dry_run` novo perto de um `marcar` — se aparecer um, a correcao
foi feita no lugar errado.

Completar a frase do console para dizer as duas coisas: nada e enviado E nada e
gravado em `.agenda/`, entao a simulacao pode rodar com o scanner de verdade de pe.

Um teste de integracao por laco provando que um tick em modo simulacao, com um
aviso vencido, NAO cria marcador — o do `--so-agenda` importa mais, porque e o
modo em 19-20% de cobertura e foi onde o incidente aconteceu.
</action>

<acceptance_criteria>
- Um tick de `laco_da_agenda` em simulacao com aviso vencido: o texto aparece no
  console e a pasta `.agenda/` fica byte-a-byte igual
- O mesmo para o laco principal via `Sessao`
- `grep -n "dry_run" l2scanner/sessao.py` nao devolve nada: o laco principal nao
  precisa conhecer o conceito, so o registro que ele recebe
- A frase do console menciona o disco
</acceptance_criteria>

## Fora de escopo

- O `marcar` do dedup de COMANDOS (`__main__.py:696`). Em `--dry-run` o leitor de
  comandos e `None` (`montar_leitor_de_comandos` devolve `None` na primeira
  linha), entao aquele caminho nao roda em simulacao e nao participa do defeito.
- Mudar o `--dry-run` para passar a ESCUTAR comandos. E uma decisao de superficie
  de ataque, tomada de proposito na Fase 8, e nao se resolve de passagem.

## Restricoes do projeto

- Portugues SEM acento em identificador, docstring, comentario e texto de WhatsApp
- Nenhuma dependencia nova
- Sem `datetime.now()` em `agenda.py` — ha portao de AST sobre tres modulos
- Baseline: `python -m pytest tests/ -q` -> **1052 passed, 2 skipped**. Usar o
  `python` do sistema (o `.venv` nao tem pytest). Nenhum teste enfraquecido.
