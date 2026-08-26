# L2 Party Scanner

Vigia a party window do Lineage 2 XM Essence enquanto você farma e avisa no
WhatsApp quando alguém da PT morre, sai do grupo ou ressuscita. A entrega das
mensagens passa pelo Chatwoot que já roda na sua VPS.

## Como ele funciona (e o que ele NÃO faz)

O scanner **lê a tela**, como se fosse alguém olhando o monitor. Ele mede o
preenchimento das barras de HP na party window e decide o que aconteceu a partir
disso. Nada além disso.

Concretamente, o scanner **nunca**:

- envia teclas, cliques ou qualquer input para o jogo
- lê a memória do processo do jogo
- injeta código, faz hook de renderização ou modifica o cliente
- intercepta ou descriptografa tráfego de rede
- automatiza qualquer ação dentro do jogo

Essas garantias não são só promessa de documentação: **nenhuma biblioteca de
automação de input entra na lista de dependências** (`pyautogui`, `pydirectinput`
e afins estão fora por decisão de projeto), o que torna a violação estruturalmente
impossível em vez de apenas proibida. Há um teste que quebra o build se alguém
adicionar uma.

**Sobre risco de banimento — sem promessa vazia:** capturar a tela é
categoricamente menos arriscado do que ler memória, injetar código ou automatizar
input, que são os vetores que anticheats de L2 efetivamente perseguem. Mas
nenhuma fonte oficial declara que ler a tela é *explicitamente permitido*, e
sistemas anticheat são opacos por design. Portanto: **risco mínimo, não risco
zero.** Use com essa informação em mãos.

## Começando

### 1. Configure a entrega

Copie `ENV-EXEMPLO.txt` para um arquivo chamado `.env` e preencha com os dados do
seu Chatwoot. O `.env` está no `.gitignore` — o token não é commitado e nunca
aparece em log.

Depois rode, nesta ordem:

```bash
python tools/check_whatsapp.py inboxes
```

Descobre qual provedor de WhatsApp está por trás de cada inbox e diz se mensagem
livre é permitida.

```bash
python tools/check_whatsapp.py conversas
```

Lista as conversas com seus IDs. Escolha os destinos e preencha
`CHATWOOT_CONVERSAS` no `.env`.

```bash
python tools/check_whatsapp.py enviar
```

Envia uma mensagem de teste. **Confirme no celular** — resposta `200` do Chatwoot
não prova entrega.

> **Por que esse teste importa tanto:** na API oficial da Meta, mensagens
> iniciadas pelo negócio fora de uma janela de 24 horas exigem template
> previamente aprovado — e o Chatwoot responde `200 OK` enquanto a Meta descarta
> a mensagem em silêncio. Como quem está AFK não mandou mensagem nenhuma, *todos*
> os alertas cairiam nesse caso.
>
> **No seu caso isso não é problema:** você usa o fork `fazer-ai/chatwoot` com
> Baileys, que é um bridge não-oficial. A regra das 24 horas não se aplica e o
> envio para grupo funciona.
>
> **Armadilha do teste:** se você mandar mensagem para o número e logo depois
> testar, a janela abre e o teste passa por engano. Teste com um número calado há
> mais de um dia.

### 2. Calibre

Com o jogo aberto e a party window visível na tela, **dois cliques em
`calibrar.bat`** (ele pergunta os nomes da party). Ou:

```bash
python -m l2scanner.calibrar --auto --nomes "J4guar,Kaus,TioMad,Korzis"
```

Ele procura o padrão das barras na tela, deduz todo o layout sozinho e grava
`calibration.json`. Também gera `calibracao-conferencia.png` com as regiões
desenhadas por cima — **abra essa imagem e confira**. Número conferindo com número
não prova que a região está no lugar certo; ver a imagem prova.

Se a detecção automática errar:

```bash
python -m l2scanner.calibrar --selecionar --nomes "J4guar,Kaus,TioMad,Korzis"
```

Aí você marca a party window arrastando o mouse.

### Duas instâncias do jogo abertas

A calibração descobre **sozinha** a qual cliente a party window pertence — ela
verifica qual janela do jogo contém a região que você calibrou — e grava o
título junto. O scanner então lê exatamente aquela janela.

As janelas são filtradas pelo executável do jogo, então uma aba de navegador
chamada "XM Essence" não entra na conta.

Para monitorar o outro personagem, recalibre com a party window **dele** visível.
Para monitorar os dois ao mesmo tempo, seria preciso rodar duas cópias com
arquivos de calibração separados — não suportado hoje.

**Recalibre sempre que** mover a party window dentro do jogo, mudar a resolução
ou trocar o arranjo de monitores. O scanner se recusa a iniciar se a geometria da tela mudou
desde a calibração — é melhor falhar alto do que medir a região errada calado.

### 3. Vigie

**Dois cliques em `vigiar-party.bat`.** Ele monta o ambiente sozinho na primeira
execução, acha o Python mesmo que ele não esteja no PATH da sua janela de
terminal, e não depende de você estar na pasta certa.

Pela linha de comando funciona também, mas aí você precisa estar na pasta do
projeto e ter o Python no PATH:

```bash
cd C:\Users\refun\Desktop\Lineage2-warnings
python -m l2scanner
```

> **Duas pegadinhas do cmd nesta máquina:**
>
> Se ele disser que **`python` não é reconhecido** mesmo estando instalado, é
> porque aquela janela foi aberta antes da instalação e carregou um PATH antigo.
> Fechar e abrir o cmd resolve.
>
> Se ele disser que **`vigiar-party.bat` não é reconhecido** mesmo você estando
> dentro da pasta, é a variável `NoDefaultCurrentDirectoryInExePath=1` — uma
> proteção do Windows que impede o cmd de procurar programas na pasta atual.
> Use `.igiar-party.bat` (com o `.\` na frente), ou dê dois cliques pelo
> Explorer, onde a restrição não vale.

Deixe a janela aberta enquanto farma. `Ctrl+C` encerra.

**Funciona com o jogo coberto por outras janelas.** O `.bat` já usa `--janela`,
que lê a janela do jogo diretamente em vez do desktop — então você pode navegar,
assistir vídeo ou trabalhar por cima do jogo sem cegar o scanner.

> **O que a leitura por janela resolve e o que não resolve:**
>
> | Situação | Funciona? |
> |---|---|
> | Navegador, Discord ou qualquer programa por cima do jogo | Sim |
> | Jogo arrastado para outro lugar da tela | Sim, acompanha |
> | Jogo sem foco, em segundo plano | Sim |
> | **Inventário ou ficha aberta dentro do jogo** | **Não** — quem desenha é o próprio jogo, sobre a mesma imagem |
> | **Janela minimizada** | **Não** — o Windows para de produzir frames, e nenhuma API contorna |
>
> Nos dois casos que não funcionam, o scanner entra em modo cego e não alerta
> nada — em vez de ler errado e inventar quatro mortes.

Para voltar a ler o desktop (mais simples, menos peças, mas exige o jogo
visível):

```bash
python -m l2scanner
```

Antes de confiar, rode uma vez em modo simulação para ver os alertas sem enviar
nada:

```bash
python -m l2scanner --dry-run
```

## Gravar uma sessão

O evento que o scanner existe para pegar — alguém da PT morrer — é raro e não se
reproduz sob demanda. Por isso vale farmar com gravação ligada: quando alguém
morrer numa sessão gravada, aquele frame vira ao mesmo tempo a base de calibração
e um teste de regressão permanente.

```bash
python -m l2scanner --record --rotulo farm
```

A sessão fica em `recordings/`, com um PNG por frame e um `observacoes.jsonl`.
PNG porque é sem perda — compressão com perda destruiria justamente as bordas de
barra que precisamos medir.

Para reproduzir uma sessão gravada, sem o jogo aberto e sem rede:

```bash
python -m l2scanner --replay recordings/20260824-120000-farm --dry-run
```

O replay usa os **horários gravados**, não o relógio: uma sessão de uma hora
reproduzida em trinta segundos produz exatamente os mesmos eventos.

## Opções

| Opção | O que faz |
|---|---|
| `--dry-run` | Mostra os alertas no console sem enviar nada |
| `--test-alert` | Envia um alerta de teste e sai (não precisa do jogo) |
| `--record` | Grava a sessão em disco |
| `--replay PASTA` | Reproduz uma sessão gravada |
| `--janela` | Lê a janela do jogo — funciona com ela coberta |
| `--intervalo N` | Segundos entre capturas (padrão: 1) |
| `--status-a-cada N` | Segundos entre blocos de status no console |
| `--sem-aviso-de-inicio` | Não avisa no WhatsApp ao ligar e desligar |
| `-v` | Log detalhado |

## Como ele evita alarme falso

Um scanner que acerta 90% das vezes é pior do que nenhum scanner: a party silencia
o grupo e o único alerta verdadeiro se perde junto. Por isso a maior parte do
código é sobre *não* alertar:

- **Morte só é confirmada após leituras seguidas de HP zerado.** Um frame borrado
  ou um efeito passando por cima da barra não dispara nada.
- **Sair do estado morto exige mais confirmações do que entrar.** Sem essa
  assimetria, um piscar de HP produziria "ressuscitou" seguido de "morreu" sem
  fim.
- **Enquanto a party window não estiver visível, nada é enviado** — e essa
  verificação acontece *antes* das verificações por membro. Se fosse depois, um
  único alt-tab viraria quatro alertas de "saiu da party".
- **Perder a visão congela os contadores em vez de zerar.** Uma morte que começou
  logo antes de um alt-tab ainda alerta quando a visão volta.
- **Ao recuperar a visão há um período de tolerância**, porque a UI redesenha em
  partes e as barras leem zero por um ou dois frames.
- **Cada evento gera exatamente um alerta.** Um morto por cinco minutos não vira
  cinco minutos de mensagens.
- **Outra janela do jogo por cima da party window cega o scanner.** Com o
  inventário aberto, as barras ficam cortadas em ~2% — e como o limiar de morte
  é 2%, os quatro membros seriam anunciados mortos de uma vez. O desempate é a
  moldura da barra: ela é desenhada pela UI e existe igual com a barra cheia ou
  vazia, mas some quando algo cobre.
- **O texto é fraseado para sobreviver a um erro:** "HP zerado — possível morte",
  nunca "MORREU".

## Avisos de TvT e Prime

O scanner também vigia o **relógio**, não só a tela. Ele avisa a party 10
minutos antes de cada evento e de novo na hora que começa.

Os horários ficam em `config.toml`, na raiz do projeto:

```toml
[[evento]]
nome = "TvT"
horarios = ["15:00", "17:00", "21:50"]
dias = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
avisar_minutos_antes = 10
silenciar_minutos = 15
```

**Os horários do jogo mudam com atualização.** Quando mudarem, corrija esse
arquivo — nunca é preciso mexer em código. Se você errar a digitação, o scanner
recusa a subir e diz qual evento e qual campo estão errados, em vez de descobrir
o problema às 15h enquanto você está AFK.

### Rodar só os avisos, sem o jogo aberto

**Dois cliques em `avisos-tvt.bat`.**

Esse modo não vigia party nenhuma: ele só olha o relógio. Serve para deixar
rodando enquanto ninguém está jogando — que é justamente quando o lembrete de
TvT vale mais, porque quem está online já vê o evento na tela.

Para testar sem esperar o horário, numa janela de comando **nesta pasta**:

```
.venv\Scripts\python -m l2scanner --testar-agenda --dry-run
```

> Use sempre `.venv\Scripts\python`, não `python`. O projeto tem um ambiente
> próprio, montado pelo `vigiar-party.bat` na primeira execução, e o `python`
> do sistema pode nem estar no PATH.

### Mandar comando pelo WhatsApp

O scanner pode **ouvir**, além de falar. Está desligado por padrão — com o
`CHATWOOT_CONVERSAS_COMANDO` vazio no `.env`, ele nunca lê nada.

Comandos, sempre com ponto na frente:

| Comando | O que faz |
|---|---|
| `.help` | Responde com esta mesma lista, direto no WhatsApp |
| `.cancelar` | Tira o silêncio de TvT/Prime que estiver rolando |
| `.status` | Diz se está vigiando ou calado, e qual o próximo evento |
| `.solo` | Vigia só o seu personagem e para de reclamar de party ausente |
| `.party` | Volta a vigiar a party inteira |
| `.loot-<nick>` | Marca quem pega o loot do próximo Solo Boss |
| `.loot-` | Desmarca (o aviso volta a sair sem nome) |
| `.<nick>` | Quantos loots o char já pegou, e quando foi o último |
| `.corrigir-<nick>` | Troca o dono do último loot já registrado |
| `.pegou <hora> <nick>` | Registra quem pegou o loot de um boss que já passou, mesmo sem ter sido marcado antes |

Também valem `.ajuda`, `.comandos` e `.?` no lugar de `.help` — quem está no
jogo pergunta pelo WhatsApp e recebe a lista sem sair da tela. **Essa lista é
gerada a partir do próprio código**, não escrita à mão: um comando novo que
não seja documentado quebra a suíte de testes de propósito, porque ajuda
desatualizada é pior que ajuda nenhuma (ela ensina sintaxe que não funciona).

**Quando usar `.pegou` e quando usar `.corrigir`.** O `.corrigir-Korzis` é o
atalho para o boss que *acabou de passar*: ele não aceita horário, e por isso
não tem como errar de boss. O `.pegou 18:00 Korzis` fala de um horário
**específico**, e serve para o caso que o `.corrigir` não alcança — ninguém
tinha marcado nada, então não existe registro nenhum para corrigir (o scanner
estava fechado quando o boss passou, por exemplo).

O horário digitado é **encaixado no Solo Boss mais próximo**, e o registro fica
com o horário do boss, não com o que você digitou: `.pegou 18h20 Korzis`
registra o boss das 18:00. Se não houver boss por perto, ele recusa e diz quais
horários existem — em vez de criar um registro num horário que nenhum boss
produz, que ficaria na estatística para sempre.

Sem data, o horário vale para a ocorrência **mais recente que já passou**: às
2h da manhã, `.pegou 18:00 Korzis` fala do boss de *ontem*. Por isso a resposta
sempre diz o dia de volta ("de ontem as 18:00", "de 23/08 as 18:00") — é assim
que você confere, na hora, que ele acertou o boss. Para ser explícito:
`.pegou 23/08 18:00 Korzis`. Todas as formas valem com hífen
(`.pegou-18:00 Korzis`) e com `h` no lugar dos dois pontos (`18h`, `18h30`).

Para descobrir em qual conversa configurar:

```
.venv\Scripts\python tools\check_whatsapp.py entrada
```

**Mensagens de grupo podem não chegar ao Chatwoot.** A ponte do WhatsApp
costuma vir com a ingestão de grupo desligada. Se for o seu caso, mande o
comando no **privado** do número do bot — a resposta continua indo para o
grupo normalmente.

**Só o seu número manda.** Ponha o seu telefone em
`CHATWOOT_TELEFONES_COMANDO` e o scanner ignora comando de qualquer outra
pessoa — inclusive dentro de um grupo, onde liberar a *conversa* liberaria os
doze membros. A comparação usa os últimos 8 dígitos, então o formato não
importa e o nono dígito não atrapalha: `+5544997077000` e `554497077000` são a
mesma pessoa para o scanner.

Com a lista vazia, qualquer um da conversa manda — e o scanner avisa isso no
arranque, em vez de deixar você descobrir por acidente.

**Etiqueta como interruptor.** Se preferir ligar e desligar pelo painel do
Chatwoot em vez do arquivo, ponha um nome em `CHATWOOT_ETIQUETA_COMANDO` e
marque a conversa com essa etiqueta. Vale na hora, sem reiniciar. A etiqueta
diz *onde* ele escuta; o telefone diz *quem* pode mandar.

**Por que o ponto é obrigatório:** sem ele, alguém dizendo "vamos cancelar o
silêncio?" faria o scanner agir no meio de uma conversa. E se o seu Chatwoot
atende clientes, uma mensagem qualquer com a palavra "cancelar" viraria um
comando. O ponto separa falar sobre a ação de pedir a ação.

### Um limite honesto

**"Independente do jogo" não é "independente do PC".** Se a máquina estiver
desligada às 15h, não sai aviso nenhum. O scanner precisa estar rodando em
algum lugar. Resolver isso de verdade exigiria um agendamento no servidor, o
que é outro projeto.

### Duas instâncias não avisam em dobro

Se você roda dois clientes com dois scanners, o grupo recebe cada aviso **uma
vez só**. Os dois processos disputam o mesmo marcador em disco e exatamente um
vence. O mesmo mecanismo faz reiniciar o scanner não reenviar o que já saiu.

## Requisitos

Python 3.12 ou superior.

O gate de entrega (`tools/check_whatsapp.py`) usa apenas a biblioteca padrão.

O scanner precisa de `mss`, `opencv-python` e `numpy` (veja `requirements.txt`).
Os arquivos `.bat` montam o ambiente sozinhos na primeira execução.

Para rodar os testes:

```bash
python -m pytest tests/ -q
```
