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
impossível em vez de apenas proibida.

**Sobre risco de banimento — sem promessa vazia:** capturar a tela é
categoricamente menos arriscado do que ler memória, injetar código ou automatizar
input, que são os vetores que anticheats de L2 efetivamente perseguem. Mas
nenhuma fonte oficial declara que ler a tela é *explicitamente permitido*, e
sistemas anticheat são opacos por design. Portanto: **risco mínimo, não risco
zero.** Use com essa informação em mãos.

## Estado atual

Em construção. Veja `.planning/ROADMAP.md` para o plano completo.

| Fase | O que entrega | Status |
|------|---------------|--------|
| 1 | Gate de entrega no WhatsApp + fundação de captura e gravação | Em andamento |
| 2 | Calibração visual e leitura das barras | Não iniciada |
| 3 | Rastreador de estado, console ao vivo e replay | Não iniciada |
| 4 | Entrega no WhatsApp e vigilância do próprio scanner | Não iniciada |

## Configuração

Copie `ENV-EXEMPLO.txt` para um arquivo chamado `.env` na raiz do projeto e
preencha com os dados do seu Chatwoot. O `.env` está no `.gitignore` — o token
não é commitado e não aparece em nenhum log.

## Gate de entrega (Fase 1)

Antes de qualquer código de detecção, é preciso provar que uma mensagem
**iniciada pelo scanner** chega de verdade no celular de quem está AFK. Rode na
ordem:

```bash
python tools/check_whatsapp.py inboxes
```

Descobre qual provedor de WhatsApp está por trás de cada inbox e diz se
mensagem livre é permitida.

```bash
python tools/check_whatsapp.py conversas
```

Lista as conversas com seus IDs, para você escolher os destinos dos alertas e
preencher `CHATWOOT_CONVERSAS` no `.env`.

```bash
python tools/check_whatsapp.py enviar
```

Envia uma mensagem de teste.

> **Por que isso importa tanto:** na API oficial da Meta, mensagens iniciadas
> pelo negócio fora de uma janela de 24 horas exigem template previamente
> aprovado — e o Chatwoot responde `200 OK` enquanto a Meta descarta a mensagem
> em silêncio. Como quem está AFK não mandou mensagem nenhuma, *todos* os
> alertas cairiam nesse caso. Com um bridge não-oficial (Baileys, Evolution,
> WAHA) a regra não existe. O comando `inboxes` diz em qual caso você está.
>
> **Armadilha do teste:** se você mandar mensagem para o número e logo depois
> testar, a janela de 24h abre e o teste passa por engano. Teste com um número
> que esteja calado há mais de um dia — e confirme no celular. Resposta `200`
> do Chatwoot não prova entrega.

## Gravar uma sessão de farm

O evento que o scanner existe para pegar — alguém da PT morrer — é raro e não se
reproduz sob demanda. Por isso o gravador vem antes da detecção: você farma com
ele ligado, banca uma morte de verdade, e aquela sessão vira ao mesmo tempo a
base de calibração e um teste de regressão permanente.

Abra `gravar-sessao.bat`, troque os números da linha `--regiao` pelas
coordenadas da sua party window (`esquerda,topo,largura,altura`) e dê dois
cliques. Deixe rodando enquanto farma; `Ctrl+C` encerra e fecha a gravação
direito.

Ou pela linha de comando:

```bash
python -m l2scanner --record --rotulo farm --regiao 1713,330,450,300
```

A sessão fica em `recordings/`, com um PNG por frame e um `observacoes.jsonl`.
PNG porque é sem perda — compressão com perda destruiria justamente as bordas de
barra que precisamos medir.

## Requisitos

Python 3.12 ou superior.

O gate de entrega (`tools/check_whatsapp.py`) usa apenas a biblioteca padrão —
roda sem instalar nada.

O scanner precisa das dependências de `requirements.txt` (`mss`, `opencv-python`,
`numpy`). O `gravar-sessao.bat` monta o ambiente sozinho na primeira execução.

Para rodar os testes:

```bash
python -m pytest tests/ -q
```
