# Research — Fase 6: A agenda como fonte de eventos

**Data:** 2026-08-24
**Método:** leitura do código atual + verificação no ambiente real. Nenhuma
afirmação aqui é suposição de biblioteca: tudo que diz "verificado" foi rodado.

## 1. O projeto NÃO tem `config.toml`. Isso é uma descoberta, não um detalhe

`.claude/CLAUDE.md` documenta a stack como `config.toml` (humano) +
`calibration.json` (máquina). A realidade divergiu: existe `.env` +
`calibration.json`, e `l2scanner/config.py` só lê o `.env`.

```
$ ls config.toml
(nao existe config.toml na raiz)
```

AGEN-04 exige horários editáveis à mão com comentário. As três opções e por que
só uma serve:

| Onde | Veredito |
|---|---|
| `calibration.json` | **Não.** É escrito pela ferramenta de calibração. Rodar `calibrar.bat` apagaria os horários. É exatamente o cenário que a separação de dois arquivos existe para impedir. |
| `.env` | **Não.** Formato plano de `CHAVE=valor`, sem estrutura para uma lista de eventos com múltiplos horários e dias, e sem comentário multi-linha decente. |
| `config.toml` novo | **Sim.** É o que o próprio projeto já tinha decidido e nunca precisou até agora. TOML tem comentário, tem tabela de array, e o leitor é stdlib. |

**Verificado no ambiente real:**

```
Python 3.12.10 | tomllib OK
```

`tomllib` entrou na stdlib no 3.11. Zero dependência nova, o que preserva a
propriedade de instalação do projeto. `tomllib` é **somente leitura**, e isso
aqui é vantagem, não limitação: nada no código deve escrever este arquivo.

## 2. O seam de transporte já existe e a agenda tem que entrar por ele

`l2scanner/notificador.py:283` — `Despachante` é fila + thread, com uma API
pequena:

- `iniciar()`
- `despachar(texto)` — grava no `outbox.jsonl` **antes** de qualquer tentativa
  de rede, depois enfileira
- `encerrar()`
- `.entregues` / `.falhados`

A agenda despacha por aqui e ganha de graça: durabilidade no outbox, retry com
backoff, falha visível no console, e o `--dry-run` funcionando sem código novo.

**Consequência para a Fase 7:** o silenciamento vai viver neste mesmo ponto. Se
a agenda furar o seam e chamar `enviar()` direto, o silenciamento fica
impossível de acrescentar depois sem reescrever a Fase 6. É a regra 6 do
roadmap v1 aplicada à segunda fonte de eventos.

## 3. Duas exigências que parecem separadas são o mesmo problema

- AGEN-06: reiniciar o scanner não reenvia um aviso já enviado
- AGEN-07: duas instâncias rodando não fazem o grupo receber tudo em dobro

Os dois pedem a mesma coisa: **um registro durável, fora do processo, de qual
aviso de qual dia já saiu.** Resolver um sem o outro deixa metade do bug em pé.

### Por que não derivar do `outbox.jsonl`

Ele já registra tudo que foi enviado, com timestamp. Tentador e errado: exigiria
casar o TEXTO da mensagem para saber o que era, e o texto é justamente a parte
que muda quando alguém melhora a redação. Um registro de intenção precisa de
chave estruturada, não de texto.

### A opção que resolve as duas de uma vez

Um arquivo-marcador por aviso, criado com `O_CREAT | O_EXCL`:

```
.agenda/2026-08-24_tvt-1500_antes
.agenda/2026-08-24_tvt-1500_agora
```

`os.open` com `O_EXCL` é **atômico no Windows**: entre duas instâncias
competindo, exatamente uma cria o arquivo e as outras recebem `FileExistsError`.
Quem criou envia; quem falhou cala. Não precisa de lock, não precisa de
biblioteca, e a mesma checagem que impede a duplicata entre instâncias é a que
sobrevive ao restart — o marcador está em disco.

Alternativas descartadas: um JSON único com `msvcrt.locking` (mais código, mais
modos de falha, e ainda precisa de leitura-modificação-escrita); um lock de
socket (some se o processo morrer sujo).

**Limpeza:** marcadores mais velhos que alguns dias são apagados no arranque.
Sem isso o diretório cresce para sempre — devagar, mas para sempre.

## 4. O laço principal hoje EXIGE uma fonte de frames

`l2scanner/__main__.py:199-232` — os três caminhos (`--replay`, `--janela`,
`mss`) todos constroem uma fonte antes do laço. Não existe caminho que rode sem
capturar. AGEN-05 e OPER-09 pedem exatamente isso: rodar só o relógio.

O caminho de menor risco é um laço separado e curto, não um `if` espalhado pelo
laço de captura. O laço de agenda não tem frame, não tem rastreador, não tem
calibração — só relógio, agenda e despachante. Misturar os dois criaria ramos
mortos dentro do laço mais crítico do projeto.

## 5. Disciplina de tempo: copiar a do rastreador

`l2scanner/rastreador.py` é puro de propósito — "não tem relógio próprio (o
tempo entra por parâmetro)". É o que torna 30 s de debounce testáveis em fração
de milissegundo.

A agenda tem que nascer com a mesma disciplina: `avisos_devidos(agora,
eventos, ja_enviados) -> list[Aviso]`. Sem isso, testar "o aviso das 21h50 de
uma quinta-feira" exigiria esperar até quinta às 21h50.

## 6. Aresta de fuso horário: baixa, mas vale dizer

Os horários são hora local da máquina, que é a mesma hora que o usuário observa
no jogo. O Brasil não tem horário de verão desde 2019, então não há
deslocamento sazonal. `datetime.now()` local resolve. **Não** usar UTC: os
horários foram informados em hora de parede local, e converter só adicionaria
uma chance de errar por 3 horas.

## 7. Esquema de config desenhado agora para a Fase 7 não ter que migrar

A Fase 7 (silenciamento) precisa de duração de janela por evento. Se a Fase 6
definir o esquema sem esse campo, a Fase 7 força uma migração de arquivo que o
usuário já editou à mão.

O esquema abaixo já reserva `silenciar_minutos`. A Fase 6 lê e ignora; a Fase 7
passa a usar. Nenhuma migração.

```toml
# Eventos agendados do jogo.
# Os horarios MUDAM com atualizacoes — e so editar aqui, nunca no codigo.

[[evento]]
nome = "TvT"
horarios = ["15:00", "17:00", "21:50"]
dias = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
avisar_minutos_antes = 10
silenciar_minutos = 15        # usado a partir da Fase 7

[[evento]]
nome = "Prime"
horarios = ["20:00"]
dias = ["seg", "ter", "qua", "qui"]
avisar_minutos_antes = 10
silenciar_minutos = 120       # usado a partir da Fase 7
```

## 8. Riscos

| Risco | Gravidade | Tratamento |
|---|---|---|
| Máquina desligada no horário | Alta, **não tratável** | Está no Out of Scope e no README. "Independente do jogo" não é "independente do PC" |
| Config com erro de digitação derruba o scanner no meio do farm | Média | Validar a agenda **no arranque** e falhar com mensagem legível, nunca às 15h |
| Relógio da máquina errado | Baixa | Fora do nosso controle; o log registra a hora usada, o que torna o diagnóstico possível |
| Marcadores acumulando | Baixa | Poda no arranque |
| Scanner sobe às 16h e dispara o aviso das 15h atrasado | Média | AGEN-08: só dispara dentro de uma janela de tolerância curta a partir do horário |
