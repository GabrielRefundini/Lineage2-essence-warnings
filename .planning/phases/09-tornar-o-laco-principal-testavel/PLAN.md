# Fase 9: Tornar o laço principal testável

**Objetivo**: Fechar a fonte de todos os bugs de integração deste projeto —
`laco_principal`, 279 linhas que só um jogo aberto consegue exercitar.

## A evidência é forte e vem de três lugares independentes

**Cobertura medida:**

| Camada | Cobertura |
|---|---|
| `rastreador.py` | 98% |
| `visao.py` / `agenda.py` / `identidade.py` | 94–95% |
| **`__main__.py`** | **20%** |

**O code review:** 3 de 3 warnings estavam em `__main__.py`. Nenhum nos
algoritmos.

**Os bugs de produção, todos depois disso:**

| Bug | Onde | O que teria pego |
|---|---|---|
| `destacar(texto)` com 1 argumento | laço | um tick que dispara aviso de agenda |
| Dois relógios trocados | laço | um tick chamado com os tipos reais, duas vezes |
| Resposta no destino errado | laço | um tick que afirma **onde** a mensagem saiu |

Os três eram invisíveis para os 420 testes porque nenhum teste chama o laço.

## A ideia: humble object

O laço tem duas responsabilidades misturadas. Separá-las é o trabalho:

```
CASCA (intestável, e tudo bem)      NÚCLEO (testável)
- construir a fonte de frames        - o que fazer com UM frame
- while True                         - decidir, despachar, registrar
- time.sleep                         - devolver o que aconteceu
- tratar exceção e sair
```

A casca fica com o mínimo irredutível: capturar, chamar o núcleo, dormir. Tudo
que **decide** alguma coisa vai para o núcleo, que recebe um frame e devolve o
que aconteceu — e um teste pode chamá-lo com frames fabricados, mil vezes por
segundo, sem jogo nenhum.

**Não é reescrita.** É mover código de dentro do `while` para um método,
mantendo o comportamento idêntico. As 420 testes existentes são a rede: se
alguma quebrar, o refactor mudou comportamento e está errado.

---

## Tarefa 1 — Extrair o estado da sessão

**Entrega**: uma classe `Sessao` que carrega o que hoje são variáveis locais do
laço — rastreador, registro, silêncio, leitor, despachante, contadores, gravador.

Hoje esses objetos nascem soltos dentro de `laco_principal` e só existem
enquanto ele roda. É por isso que nenhum teste alcança: não há como construir a
situação sem construir o laço inteiro.

**Verificação**: a suíte inteira continua verde. Nenhum comportamento muda —
só onde as variáveis moram.

**Commit**: `refactor(laco): o estado da sessao sai das variaveis locais`

---

## Tarefa 2 — Extrair o tick

**Entrega**: `Sessao.tick(frame, agora) -> ResultadoDoTick`, com todo o corpo
do `while` menos capturar e dormir.

`laco_principal` vira:

```python
while True:
    frame = fonte.capturar()
    sessao.tick(frame, time.time())
    dormir()
```

**Verificação**: suíte verde, e o `--so-agenda` e o `vigiar-party` rodando de
verdade — o refactor não pode ser verificado só por teste, porque o que ele
mexe é justamente o que os testes não cobriam.

**Commit**: `refactor(laco): o tick vira uma funcao que recebe um frame`

---

## Tarefa 3 — Os testes que os três bugs exigiam

**Entrega**: testes que dirigem `tick()` com frames fabricados e **teriam
pego** cada bug de produção de hoje.

Um por bug, nomeados pelo que aconteceu:

1. Um tick que dispara aviso de agenda → pegaria o `destacar`
2. Vários ticks seguidos com os tipos reais → pegaria os dois relógios
3. Um tick com comando → afirma **em qual conversa** a resposta saiu

Mais os caminhos que nunca tiveram teste: frame com falha de captura, frame
congelado, cegueira longa, erro de extração, encerramento.

**Critério de aceite**: `__main__.py` sai de 20% para **acima de 60%**, e cada
um dos três bugs tem um teste que falha se ele voltar.

**Commit**: `test(laco): os tres bugs de producao viram regressao`

---

## O que NÃO fazer

**Não mudar comportamento.** Se uma decisão parecer errada durante o refactor,
anotar e tratar depois. Misturar refactor com correção torna impossível saber
qual dos dois quebrou algo.

**Não perseguir 100%.** A casca — `while True`, `sleep`, montar a fonte — não
precisa de teste e não vai ter. O alvo é o que **decide**.

**Não tocar no `laco_da_agenda` além do necessário.** Ele tem 80 linhas e
menos risco; se a extração servir para ele de graça, ótimo, mas não é o alvo.
