# Itens adiados — quick 260825-c6g

Descobertos durante a execucao, FORA do escopo deste plano. Nao foram
corrigidos de proposito: a regra de escopo so autoriza corrigir o que a
propria tarefa quebrou.

## ~~6 testes de `tests/test_agenda.py` falhando por deriva do `config.toml`~~

**RESOLVIDO em `42f3ed3`.** As expectativas foram atualizadas e config e teste
foram commitados juntos. Suite verde: 491 passed.

**Correcao de dois enganos deste registro**, para quem ler depois:

1. **Nao eram pre-existentes.** A suite estava em 491 passed no commit anterior
   ao plano — medido revertendo o `config.toml` e rodando. As 6 falhas nasceram
   da edicao do usuario, feita enquanto este plano executava.
2. **O acoplamento ao `config.toml` real nao e defeito, e o recurso.** Um
   horario digitado errado no config aparece como teste VERMELHO, em vez de
   aparecer como um aviso que nao saiu as 19:20 no meio do farm. Trocar por
   fixture compraria uma suite que nunca quebra e que tambem nunca avisa.

Registro original abaixo.

O `config.toml` do usuario ganhou um TvT as **19:30** que os testes de
`TestAgendaRealDoUsuario` nao esperam — eles afirmam
`((15,0), (17,0), (21,50), (23,0))` e a config tem
`((15,0), (17,0), (19,30), (21,50), (23,0))`.

Testes afetados:

- `TestAgendaRealDoUsuario::test_tvt_tem_os_horarios_do_config_todo_dia`
- `TestAgendaRealDoUsuario::test_tvt_e_prime_numa_segunda_saem_na_ordem_e_hora_certas`
- `TestAgendaRealDoUsuario::test_o_volume_diario_total_e_o_esperado`
- `TestAgendaRealDoUsuario::test_no_sabado_o_prime_nao_aparece`
- `TestRegistroEmDisco::test_a_agenda_inteira_com_registro_duravel_nao_duplica`
- `TestJanelaDeSilencio::test_uma_segunda_inteira_minuto_a_minuto`

Nada a ver com o relogio: `test_agenda.py` nao importa `__main__.py` nem
`relogio.py`. A causa e que esses testes leem o `config.toml` REAL do usuario
em vez de uma fixture — entao qualquer evento que ele acrescente quebra a
suite. E esse acoplamento, e nao o horario, o defeito a consertar.

**Alem disso:** `config.toml` esta modificado na arvore de trabalho e NAO foi
commitado por esta tarefa. E edicao do usuario; nao foi revertida.

## 23 avisos de `ruff` em arquivos nao tocados

Pre-existentes (`F401` de `pytest` nao usado em varios testes, entre outros).
Os quatro arquivos tocados por este plano passam limpos.
