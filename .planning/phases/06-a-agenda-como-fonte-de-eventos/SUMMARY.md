# Fase 6 — A agenda como fonte de eventos

**Concluída:** 2026-08-24
**Commits:** `44328de`, `5437b3b`, `57923e9`, `000b8d1`
**Testes:** 255 → 310 (55 novos)

## Critérios de sucesso, um a um

| # | Critério | Como foi verificado |
|---|---|---|
| 1 | Dois avisos por evento, nos horários certos | Varredura de uma segunda-feira **minuto a minuto** (1440 iterações) afirmando a sequência exata dos 8 avisos do dia, na ordem e no horário |
| 2 | Horário editável em `config.toml` sem tocar em Python | Teste que muda `avisar_minutos_antes` para 25 só pelo arquivo e vê o aviso deslocar |
| 3 | Roda com o jogo fechado | Rodado ao vivo com o cliente fechado; e um teste por subprocesso que executa `--testar-agenda --dry-run` de verdade |
| 4 | Não reenvia no restart, não dispara atrasado | Registro recriado do zero devolve `False`; `agora=16:00` com evento às 15:00 não produz nada |
| 5 | Duas instâncias, um aviso só | 16 threads largando ao mesmo tempo na mesma chave; exatamente uma vence |

## O que a execução ensinou

**A disciplina do rastreador transferiu inteira.** A agenda nasceu sem relógio
próprio — o tempo entra por parâmetro — e por isso os 7 dias da semana, a
virada de meia-noite e um dia inteiro minuto a minuto são testados em
milissegundos. Se ela tivesse chamado `datetime.now()` por dentro, o teste do
"TvT das 21h50 de uma quinta" seria impossível de escrever.

**Três arestas que pareciam detalhe:**

1. O dia da semana vale para o **evento**, não para o aviso. Um evento a 00:05
   de segunda avisa às 23:55 de **domingo**. Checar o dia do aviso faria esse
   evento nunca ser anunciado.
2. Ontem e amanhã entram na varredura, pelo mesmo motivo.
3. Aviso vencido não ressuscita — 5 minutos de tolerância. Subir o scanner às
   16h não pode soltar o lembrete das 15h de um TvT que já acabou.

**AGEN-06 e AGEN-07 eram o mesmo problema.** Sobreviver ao restart e não
duplicar entre as duas instâncias do usuário pedem a mesma coisa: um registro
durável fora do processo. `O_CREAT | O_EXCL` resolve os dois de uma vez, e é
atômico no Windows — sem lock, sem biblioteca, e **sem janela de corrida entre
ler e escrever**, que é o furo de um "lê o JSON, checa, escreve o JSON".

Por isso o teste decisivo não é sequencial. Um registro com janela de corrida
passaria no teste sequencial e falharia no de threads.

**O laço `--so-agenda` ficou separado.** Um `if` dentro do laço principal seria
mais curto e pior: aquele laço é o código mais crítico do projeto e não ganha
ramos que só existem para um modo.

## Decisões tomadas na execução

- **`config.toml` ausente não é erro.** O scanner roda sem agenda desde a v1 e
  precisa continuar rodando. Só arquivo presente-e-mal-formado falha, e falha no
  **arranque** — o usuário está olhando para o console quando sobe o programa;
  às 15h ele está AFK confiando no silêncio.
- **Erro de disco em `marcar` devolve `True`.** Preferir o aviso duplicado ao
  aviso perdido: a party ignora uma repetição, mas não adivinha um TvT que
  ninguém anunciou.
- **`.agenda/` entra no `.gitignore`.** Versionar faria um clone novo achar que
  já avisou o TvT de um dia que nunca viveu — e calar de verdade.
- **`silenciar_minutos` já está no `config.toml`**, lido e ignorado. A Fase 7
  passa a usar, e o usuário não edita à mão um arquivo que já editou.

## Pendência

Nenhuma bloqueante. Falta a **confirmação em campo**: deixar `--so-agenda`
rodando e ver o aviso chegar no WhatsApp num horário real. Tudo até aqui foi
verificado com relógio controlado e um envio de teste.
