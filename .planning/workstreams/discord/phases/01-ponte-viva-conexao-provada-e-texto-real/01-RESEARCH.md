# Fase 1: Ponte viva — conexão provada e texto real — Research

**Pesquisado:** 2026-08-28
**Workstream:** discord
**Domínio:** cliente de gateway do Discord em Python (recebimento de mensagem), detecção da intent MESSAGE CONTENT, deduplicação por snowflake, ciclo de vida de conexão async no Windows
**Confiança global:** **HIGH** — a resposta da pergunta central (detecção da intent) foi verificada lendo o **código-fonte do wheel `discord.py` 2.7.1 baixado do PyPI nesta sessão**, não da memória. Os pontos MEDIUM/UNVERIFIED estão marcados um a um e cada um vem com o experimento que o resolve.

---

## Sumário

O `discord.py` continua sendo a escolha certa e **não** foi superado: repositório ativo (último push 2026-07-27), 16 158 estrelas, não arquivado, commits ao longo de julho de 2026. A versão a fixar é **2.7.1 (2026-03-03)**, wheel `py3-none-any` (Python puro), e ela traz **10 distribuições novas** para o `.venv` deste projeto (que hoje tem 16) — nenhuma delas na banlist do `tests/test_firewall_escopo.py`.

A pergunta cara desta fase — *"como a ponte descobre que a intent MESSAGE CONTENT está desligada, em vez de replicar branco para sempre?"* — tem uma resposta **determinística e de arranque**, não uma heurística. Duas descobertas, ambas lidas no fonte:

1. **Se a intent está declarada no código e DESLIGADA no painel**, o gateway fecha com o código **4014** e o `discord.py` levanta `discord.errors.PrivilegedIntentsRequired`, que **aborta o laço de conexão mesmo com `reconnect=True`** (`client.py:774-775`). O processo morre alto. Ou seja: **o caso (a) já é barulhento de fábrica.**
2. Melhor ainda: `Client.login()` sempre chama `GET /applications/@me` e guarda as flags da aplicação em `self.application_flags` **antes** de rodar o `setup_hook()` e **antes** do IDENTIFY (`client.py:681`, `client.py:690-693`). As flags `gateway_message_content` (1<<18) e `gateway_message_content_limited` (1<<19) dizem, direto da API, se o botão do painel está ligado. Isso permite um **pré-voo determinístico** que morre com uma mensagem escrita por nós, em português, dizendo os 4 cliques do conserto — em vez de um traceback de biblioteca.

O modo de falha que sobra é o **caso (b): intent LIGADA no painel e NÃO declarada no código.** Esse é silencioso por desenho do Discord e é o único que precisa de heurística de runtime. A heurística existe e é quase exata (uma mensagem comum com `content`, `attachments`, `embeds`, `stickers`, `components`, `poll` e `message_snapshots` **todos vazios** não é postável pela UI do Discord) — mas há **uma armadilha de teste** que precisa entrar no roteiro do portão humano: **uma mensagem que MENCIONA o bot chega com texto mesmo com a intent desligada.** Se o usuário testar escrevendo `@ponte oi`, o teste passa verde com a intent desligada e o modo de falha mais caro do projeto se esconde até o primeiro anúncio de verdade.

**Recomendação primária:** `discord.py>=2.7.1,<3` declarado **direto no `requirements.txt`** (nunca via `-r`, que o firewall recusa por construção); `Intents.none()` + `guilds` + `guild_messages` + `message_content`; pré-voo determinístico em `setup_hook()` que mata o arranque; heurística de runtime como segunda linha; livro de já-vistos como **conjunto limitado de IDs em JSONL append-only** (não marca-d'água), gravado ANTES de qualquer entrega.

---

## Architectural Responsibility Map

| Capacidade | Camada dona | Camada secundária | Por que essa camada |
|---|---|---|---|
| Receber mensagem do Discord | `discord.py` (gateway WebSocket) | — | É a única que fala o protocolo; reimplementar é fora de escopo por definição |
| Filtrar guild + 2 canais | Nossa (`on_message`) | — | O gateway não filtra por canal; a assinatura de intents é o mais estreito que dá |
| Descobrir intent desligada | Nossa (`setup_hook`, pré-voo REST) | `discord.py` (exceção 4014) | A exceção da lib cobre o caso (a); o caso (b) só a API de flags resolve |
| Livro de já-vistos (ENTR-04) | Nossa (disco, stdlib `json`) | — | O gateway não garante exactly-once; a lib não persiste nada |
| Resolver menções (FORM-03) | `discord.py` (`clean_content`) | Nossa (emoji custom, `<t:>`, `</cmd:>`) | `clean_content` cobre 3 dos 4 casos do FORM-03; o quarto é nosso |
| Reconexão / backoff de socket | `discord.py` (`connect(reconnect=True)`) | — | `ExponentialBackoff` + RESUME já embutidos; reimplementar é regressão |
| Log rotativo próprio (OPER-02) | Nossa (`logging.handlers`) | — | `Client.run(log_handler=None)` desliga o log da lib e devolve o controle |
| Entrega no Chatwoot (Fase 3) | `l2scanner/notificador.py` (intocado) | — | Já existe e roda em produção |

---

## Project Constraints (do `.claude/CLAUDE.md` e do repositório)

> **Aviso herdado do `01-PATTERNS.md` desta mesma fase, e ele está certo:** a tabela de stack do `.claude/CLAUDE.md` descreve `requests`, `rich`, `pydantic`, `python-dotenv` e `uv` — **o código não usa nenhum deles.** O `requirements.txt` real tem 10 linhas e tudo que é HTTP, config, segredo e console é **stdlib pura**. Esta pesquisa planeja contra o código, não contra o `CLAUDE.md`.

Diretivas que valem como decisão travada:

1. **Nenhuma biblioteca de síntese de input na árvore.** Invariante fundador (`l2scanner/__init__.py:9-12`), com portão executável em `tests/test_firewall_escopo.py`. → auditado abaixo, passa limpo.
2. **`l2scanner/notificador.py` e `l2scanner/__main__.py` não são modificados.** O `__main__.py` está sendo editado em paralelo pelo workstream `mercado`.
3. **Código, comentários, docstrings e identificadores em português SEM acento.** Documentos de planejamento (este) usam acento; código não.
4. **Segredo no `.env`, configuração no `config.toml` lido com `tomllib` stdlib.**
5. **Config inválida derruba no ARRANQUE, nomeando a chave e o conserto** (`config.py:167-260`, `calibracao.py:442`).
6. **Captura de tela é somente leitura** — irrelevante para esta fase (a ponte não toca a tela), mas o firewall vale para toda a árvore.

---

<phase_requirements>
## Phase Requirements

| ID | Descrição | Suporte desta pesquisa |
|---|---|---|
| PONTE-01 | Conecta com token próprio e permanece conectada | §1 (biblioteca), §5 (ciclo de vida, `reconnect=True`, backoff embutido) |
| PONTE-02 | Lê só os dois canais, ignora o resto do servidor | §5 (assinatura de intents mínima), §"Code Examples" (filtro por `channel.id`) |
| PONTE-03 | TODA mensagem é replicada, sem filtro de autor/cargo/menção | §"Common Pitfalls" #4 (o filtro `author.bot` é o erro clássico) |
| PONTE-04 | Ignora as próprias mensagens, ACEITA bot e webhook | §"Code Examples" (`author.id == self.user.id`; `webhook_id` nunca colide) |
| PONTE-05 | Processo separado do scanner | §7 (entrypoint async próprio), §"Common Pitfalls" #7 (venv compartilhado) |
| FORM-03 (prep) | Marcação crua vira texto legível | §3 — decide o que é grátis e o que é escrito à mão na Fase 2 |
| FORM-05 (prep) | Mensagem longa truncada em vez de recusada | §6 — teto do Chatwoot medido no fonte; 422 é definitivo |
| ENTR-04 | Nunca entrega o mesmo anúncio duas vezes | §4 — abordagem de persistência decidida e justificada |
| CONF-01 | Token no `.env` | §"Code Examples" (reusa `ler_env` de `config.py:40`) |
| CONF-02 | Guild, canais e conversa no `config.toml` | Ver `01-PATTERNS.md` §1 (idioma de validação já mapeado) |
| CONF-03 | Config inválida mata no arranque | §2 (o pré-voo da intent é a mesma disciplina, aplicada ao painel) |
| CONF-04 | Modo simulação | §5 (nesta fase a ponte **só** simula; não há caminho de entrega) |
| OPER-01 | `.bat` próprio no padrão da raiz | §7 + §"Common Pitfalls" #7 (linha de sonda de dependência) |
| OPER-02 | Log rotativo próprio, separado do scanner | §7 (`Client.run(log_handler=None)` — **verificado no fonte**) |
| OPER-03 | Console mostra que está viva e a última mensagem | §5 — **`Client.is_closed()` NÃO serve**, e o porquê está medido |
</phase_requirements>

---

## §1 — Biblioteca cliente do Discord

### A decisão

| Biblioteca | Versão | Data | `requires_python` | Wheel | Veredito |
|---|---|---|---|---|---|
| **`discord.py`** | **2.7.1** | **2026-03-03** | `>=3.8` | `discord_py-2.7.1-py3-none-any.whl` | **ESCOLHIDA** |
| `py-cord` | 2.8.1 | 2026-07-25 | `>=3.10,<3.15` | py3-none-any | fork; sem vantagem aqui |
| `disnake` | 2.12.1 | 2026-07-22 | `>=3.10` | py3-none-any | fork; sem vantagem aqui |
| `nextcord` | 3.2.0 | 2026-05-21 | `>=3.12,<4.0` | py3-none-any | fork; sem vantagem aqui |
| `hikari` | 2.6.0 | 2026-08-19 | `>=3.10,<3.15` | py3-none-any | API de baixo nível; mais trabalho |
| `interactions.py` | 5.16.0 | 2026-02-02 | `>=3.10` | py3-none-any | orientado a slash command; 10+ deps |

`[VERIFIED: PyPI JSON API, consultado em 2026-08-28 nesta sessão via urllib]`

### Existe preocupação de manutenção em ago/2026? **Não.**

`[VERIFIED: GitHub API /repos/Rapptz/discord.py, consultado 2026-08-28]`

- `archived: false`, `stargazers_count: 16158`, `pushed_at: 2026-07-27T18:33:15Z`, branch padrão `master`.
- Commits recentes na `master`: `2026-07-22 Fix DeprecationWarning in escape_markdown()`, `2026-07-11 Fix Message.edit suppress default`, `2026-07-10 Validate message file upload limit`, `2026-07-10 Fixed grammar error for WebhookMessage.clean_content`.

**O único fato que merece nota:** o último release **no PyPI** é 2.7.1 de **2026-03-03**, ou seja ~6 meses atrás, enquanto a `master` recebe commits até julho. Esse é o ritmo histórico do projeto (2.5.2 em mar/2025 → 2.6.0 em ago/2025 → 2.7.0 em fev/2026), **não** um sinal de abandono. `[VERIFIED: histórico completo de releases do PyPI JSON]`

### Suporte a Python 3.13

O wheel é `py3-none-any` — Python puro, sem extensão C, então roda em qualquer 3.8+. `[VERIFIED: nome do arquivo no PyPI JSON de 2.7.1]`

> ⚠️ **O `.venv` deste repositório é Python 3.12.10, não 3.13.** `[VERIFIED: .venv/Scripts/python.exe --version, executado nesta sessão]` O contexto da fase diz "Python 3.13 64-bit"; a máquina diz 3.12.10. Isso **não** bloqueia nada (discord.py aceita `>=3.8`) e na verdade **economiza uma dependência** — ver a tabela abaixo.

### Dependências transitivas (o projeto conta cada uma)

Resolução real, sem instalar, via `pip install --dry-run --report`:

**No `.venv` atual (Python 3.12.10) — 11 distribuições, 10 novas:**

| Distribuição | Versão resolvida | Já está no `.venv`? |
|---|---|---|
| `discord.py` | 2.7.1 | não |
| `aiohttp` | 3.14.3 | não |
| `multidict` | 6.7.1 | não |
| `yarl` | 1.24.5 | não |
| `aiohappyeyeballs` | 2.7.1 | não |
| `aiosignal` | 1.4.0 | não |
| `attrs` | 26.1.0 | não |
| `frozenlist` | 1.8.0 | não |
| `idna` | 3.19 | não |
| `propcache` | 0.5.2 | não |
| `typing_extensions` | 4.16.0 | **sim, já presente** |

`[VERIFIED: pip 26.2.1 --dry-run --report contra o .venv do repo, 2026-08-28]`

O `.venv` tem **16 distribuições** hoje; passa a **26**. `[VERIFIED: .venv/Scripts/python.exe -m pip list]`

**Em Python 3.13 seriam 12** — o `METADATA` do wheel declara `Requires-Dist: audioop-lts; python_version >= "3.13"` **fora de qualquer extra**, então em 3.13 entra também `audioop-lts` (extensão C de áudio, inútil para nós, herdada da remoção do `audioop` da stdlib pelo PEP 594). `[VERIFIED: METADATA do wheel discord_py-2.7.1-py3-none-any.whl, baixado do PyPI nesta sessão]`

> **Consequência de planejamento:** ficar no Python 3.12.10 que a máquina já tem economiza uma extensão C irrelevante. Não há motivo para subir para 3.13 nesta fase.

**Nenhum extra é necessário.** `[voice]`, `[speed]`, `[test]`, `[docs]` ficam fora — a ponte não faz voz e o ganho de `orjson` é irrelevante para ~10 mensagens por dia.

### Instalação e declaração

```
# requirements.txt — acrescentar
discord.py>=2.7.1,<5
```

Prescrição de pin: `>=2.7.1,<3`. Segue o idioma do próprio arquivo (`mss>=10.2.0`, `opencv-python>=4.10,<5`): piso na versão exercitada, teto abaixo do próximo major.

> 🔴 **REGRA DURA, medida no firewall:** declare `discord.py` **DIRETO no `requirements.txt`**. Um segundo arquivo trazido por `-r requirements-ponte.txt` faz o teste `test_as_linhas_que_trazem_pacote_por_fora_sao_RECUSADAS` **levantar `AssertionError`** — a varredura declarada recusa `-r`, `--requirement`, `-e` e `--editable` de propósito. `[VERIFIED: tests/test_firewall_escopo.py:95, 157-167, 312-337]`

---

## Package Legitimacy Audit

| Pacote | Registro | Idade | Downloads | Repositório | Veredito do seam | Disposição |
|---|---|---|---|---|---|---|
| `discord.py` | PyPI | 2.7.1 de 2026-03-03; projeto desde 2015 | não exposto pela API | `github.com/Rapptz/discord.py` (16.1k ★, ativo) | `SUS` | **Aprovado** — falso positivo, ver nota |
| `aiohttp` | PyPI | 3.14.3 de 2026-07-23 | não exposto | `github.com/aio-libs/aiohttp` | `SUS` | **Aprovado** — falso positivo |
| `audioop-lts` | PyPI | 0.2.2 | não exposto | `github.com/AbstractUmbra/audioop` | `SUS` | **Aprovado** — só entra em py3.13 |

`[VERIFIED: gsd-tools query package-legitimacy check --ecosystem pypi, executado 2026-08-28]`

**Por que os três `SUS` são falso positivo, e não vale checkpoint humano:** os motivos devolvidos foram exclusivamente `unknown-downloads` e `no-repository`. `unknown-downloads` é limitação do PyPI (a JSON API não expõe contagem de download). `no-repository` no caso do `discord.py` acontece porque o `project_urls` do pacote declara `Documentation` e `Issue tracker`, mas não uma chave `Repository` — o repositório **existe** e foi confirmado por outra via. Independentemente do seam, **o fonte do wheel 2.7.1 foi baixado e lido nesta sessão** (arquivos `client.py`, `flags.py`, `message.py`, `errors.py`, `gateway.py`, `state.py`, `member.py`, `utils.py`): é o `discord.py` legítimo do Rapptz. `audioop-lts` é de `AbstractUmbra`, contribuidor conhecido do próprio `discord.py`, e é o backport oficial-de-facto do `audioop` removido do stdlib.

**Pacotes removidos por `SLOP`:** nenhum.
**Pacotes que exigem `checkpoint:human-verify`:** nenhum.

### O firewall de escopo passa? **Sim — e por quê.**

A banlist é `{pyautogui, pydirectinput, pynput, keyboard, mouse, autoit, pyautoit, ahk, pywinauto}` `[VERIFIED: tests/test_firewall_escopo.py:68-78]`. Nenhum dos 11 nomes resolvidos está nela, e nenhum deles **declara** um banido em `Requires-Dist` (`aiohttp` declara `aiohappyeyeballs`, `aiosignal`, `attrs`, `frozenlist`, `multidict`, `propcache`, `yarl`; `yarl` declara `idna`, `multidict`, `propcache`).

**Mas o roadmap manda VER passar, não supor** — e está certo. A prova é uma linha:

```
.venv\Scripts\python.exe -m pip install -r requirements.txt
python -m pytest tests/test_firewall_escopo.py -v
```

As quatro varreduras (declarada, ambiente da suíte, `.venv` de produção, `Requires-Dist`) precisam estar verdes **depois** da instalação, não antes.

---

## §2 — ⚠️ A PERGUNTA CENTRAL: detectar a intent MESSAGE CONTENT faltando

Esta é a seção que decide a fase. Tudo aqui foi lido no fonte do wheel 2.7.1 baixado nesta sessão.

### 2.1 — Os três casos, separados

| Caso | Intent no CÓDIGO | Botão no PAINEL | O que acontece | Detectável? |
|---|---|---|---|---|
| **(a)** | declarada `message_content = True` | **DESLIGADO** | Gateway fecha com **4014**; `discord.py` levanta `PrivilegedIntentsRequired` e **aborta** | **SIM, de fábrica — e agora antes disso, no pré-voo REST** |
| **(b)** | **NÃO declarada** | LIGADO | Conecta normalmente, `on_message` dispara, **`content` sempre `""`** | **SIM, pelo pré-voo** (`intents.message_content is False`) — trivial, é só ler o próprio objeto |
| **(c)** | declarada | LIGADO | Funciona | — |

**Caso (a) — o que exatamente acontece, verbatim do fonte:**

```python
# discord/client.py:773-779
if isinstance(exc, ConnectionClosed):
    if exc.code == 4014:
        raise PrivilegedIntentsRequired(exc.shard_id) from None
    if exc.code != 1000:
        await self.close()
        raise
```

`[VERIFIED: discord/client.py:773-779 do wheel discord_py-2.7.1]`

Repare em duas coisas que importam:

1. Isso está **dentro** do `except` que já tratou `reconnect`, e o `raise` é **incondicional** — `PrivilegedIntentsRequired` sobe **mesmo com `reconnect=True`**. A ponte não fica num laço eterno de reconexão silenciosa.
2. A exceção nomeia a intent explicitamente:

```python
# discord/errors.py:252-262
class PrivilegedIntentsRequired(ClientException):
    """Exception that's raised when the gateway is requesting privileged intents
    but they're not ticked in the developer page yet.
    ...
    - :attr:`Intents.members`
    - :attr:`Intents.presences`
    - :attr:`Intents.message_content`
    """
```

`[VERIFIED: discord/errors.py:252-277]`

E o Discord confirma o significado do 4014 do lado do protocolo: *"a privileged intent that hasn't been configured or approved for your app"*. `[CITED: docs.discord.com/developers/events/gateway — tabela de close codes]`

### 2.2 — O sinal MELHOR: pré-voo determinístico, antes do gateway

O 4014 é bom mas chega **depois** de abrir o WebSocket, e a mensagem que o usuário lê é em inglês, da biblioteca. Existe um sinal **anterior, determinístico e nosso**.

`Client.login()` faz isto, nesta ordem:

```python
# discord/client.py:679-693
data = await self.http.static_login(token)
self._connection.user = ClientUser(state=self._connection, data=data)
self._application = await self.application_info()       # GET /applications/@me
if self._connection.application_id is None:
    self._connection.application_id = self._application.id
...
if not self._connection.application_flags:
    self._connection.application_flags = self._application.flags
await self.setup_hook()
```

`[VERIFIED: discord/client.py:679-693]`

Ou seja: **quando o `setup_hook()` roda, `self.application_flags` já está preenchido, e o gateway ainda nem foi aberto.** As duas flags que interessam:

```python
# discord/flags.py:1668-1679
@flag_value
def gateway_message_content(self):
    """...Returns ``True`` if the application is verified and is allowed to
    read message content in guilds."""
    return 1 << 18

@flag_value
def gateway_message_content_limited(self):
    """...Returns ``True`` if the application is unverified and is allowed to
    read message content in guilds."""
    return 1 << 19
```

`[VERIFIED: discord/flags.py:1668-1679]`

E o Discord documenta os mesmos dois bits, dizendo de onde eles vêm:

- `1 << 18` `GATEWAY_MESSAGE_CONTENT` — *"Intent required for bots in 100 or more servers to receive message content"*
- `1 << 19` `GATEWAY_MESSAGE_CONTENT_LIMITED` — *"Intent required for bots in under 100 servers to receive message content, **found on the Bot page in your app's settings**"*

`[CITED: docs.discord.com/developers/resources/application — Application Flags]`

**A ponte roda em 1 guild** (XM Games), então o bit que vai ligar é o **`1 << 19` (`gateway_message_content_limited`)**. Testar os dois com `or` cobre também o dia em que o bot entrar em 100 servidores.

### 2.3 — O código concreto que torna o caso (a) alto em vez de mudo

```python
# l2scanner/ponte_discord.py  (identificadores em portugues sem acento)

import discord

# Assinatura MINIMA. `none()` e a base, e cada bit ligado tem motivo escrito.
INTENCOES = discord.Intents.none()
INTENCOES.guilds = True            # 1 << 0  — cache de guild, canal e cargo
INTENCOES.guild_messages = True    # 1 << 9  — o que dispara on_message
INTENCOES.message_content = True   # 1 << 15 — PRIVILEGIADA: o texto em si
# valor final: 1 | 512 | 32768 == 33281


class IntentDeConteudoDesligada(Exception):
    """A intent MESSAGE CONTENT nao esta ligada no painel do Discord."""


CONSERTO_DA_INTENT = (
    "A intent MESSAGE CONTENT esta DESLIGADA no painel do Discord.\n"
    "\n"
    "Sem ela o bot conecta, parece saudavel, e recebe TODA mensagem com o\n"
    "texto VAZIO. A ponte replicaria mensagem em branco para sempre — e por\n"
    "isso ela prefere nao subir.\n"
    "\n"
    "Conserto (so voce pode fazer, leva 30 segundos):\n"
    "  1. Abra https://discord.com/developers/applications\n"
    "  2. Escolha a aplicacao do bot e clique em 'Bot' no menu da esquerda\n"
    "  3. Em 'Privileged Gateway Intents', ligue MESSAGE CONTENT INTENT\n"
    "  4. Clique em 'Save Changes'\n"
    "  5. Suba a ponte de novo\n"
)


class Ponte(discord.Client):

    async def setup_hook(self) -> None:
        """Pre-voo. Roda DEPOIS do login REST e ANTES do IDENTIFY.

        `Client.login` acabou de chamar GET /applications/@me e guardou as
        flags da aplicacao — entao da para perguntar ao proprio Discord se o
        botao do painel esta ligado, sem abrir o WebSocket e sem esperar a
        primeira mensagem chegar vazia.

        Isto NAO substitui o 4014 da biblioteca; ele continua valendo como
        rede. Isto existe para que a mensagem que o usuario le seja a nossa,
        em portugues, com os cliques do conserto.
        """
        flags = self.application_flags
        ligada_no_painel = (
            flags.gateway_message_content            # app verificado (>= 100 guilds)
            or flags.gateway_message_content_limited  # app nao verificado (< 100)
        )
        if not ligada_no_painel:
            raise IntentDeConteudoDesligada(CONSERTO_DA_INTENT)

        # Caso (b): ligada no painel, esquecida no codigo. Barato de conferir.
        if not self.intents.message_content:
            raise IntentDeConteudoDesligada(
                "A intent MESSAGE CONTENT esta ligada no painel mas NAO foi "
                "declarada no codigo (INTENCOES.message_content). Sem a "
                "declaracao o Discord nao manda o texto."
            )
```

**Uma exceção levantada no `setup_hook()` propaga para fora de `Client.run()`?** Sim: `login()` → `start()` → `runner()` → `asyncio.run()` dentro de `run()`, e o único `except` de `run()` é `KeyboardInterrupt`. `[VERIFIED: discord/client.py:920-938]` O `async with self` garante que o HTTP client fecha limpo antes de a exceção subir.

O arranque então segue o idioma que o repositório já usa para config inválida (`log.error` + `return 2`, nunca traceback cru — ver `01-PATTERNS.md` §1):

```python
try:
    ponte.run(token, log_handler=None)
except IntentDeConteudoDesligada as erro:
    log.error("%s", erro)
    return 2
except discord.PrivilegedIntentsRequired as erro:
    # Rede de seguranca: se a API de flags mentir, o gateway ainda fecha 4014.
    log.error("%s\n\n%s", erro, CONSERTO_DA_INTENT)
    return 2
except discord.LoginFailure:
    log.error("DISCORD_BOT_TOKEN invalido ou revogado. Gere outro no painel.")
    return 2
```

### 2.4 — A heurística de runtime (segunda linha) e como ela erra

O pré-voo cobre arranque. Se o usuário desligar o botão **com a ponte rodando**, o Discord não derruba a sessão existente — o texto simplesmente começa a chegar vazio. Para isso, e porque o critério de sucesso 2 pede explicitamente *"se o texto chegar VAZIO, a ponte diz isso alto e nomeia a intent como causa provável"*, vale a heurística.

**A base factual.** Sem a intent, estes quatro campos ficam vazios — e só estes:

> `content`: *"If `Intents.message_content` is not enabled this will always be an empty string unless the bot is mentioned or the message is a direct message."*
> `embeds`, `attachments`, `components`: mesma frase, com "empty list".

`[VERIFIED: discord/message.py:2010-2013, 2017-2020, 2068-2071, 2099-2103]`

`mentions`, `role_mentions`, `channel_mentions`, `stickers`, `poll` e `message_snapshots` **não** carregam essa nota — e `mentions` é construído da carga útil do evento, não do cache (`message.py:2473-2487`).

**A heurística:**

```python
def parece_intent_desligada(msg: discord.Message) -> bool:
    """Assinatura de 'chegou vazio porque a intent caiu'.

    O Discord NAO deixa postar uma mensagem sem nada dentro: ou tem texto, ou
    anexo, ou embed, ou figurinha, ou enquete, ou componente, ou e um
    encaminhamento. Uma mensagem COMUM com tudo isso vazio nao e postavel pela
    interface do Discord — ela e o retrato da intent desligada.
    """
    if msg.type not in (discord.MessageType.default, discord.MessageType.reply):
        return False   # mensagem de sistema e vazia POR DIREITO
    return not (
        msg.content
        or msg.attachments
        or msg.embeds
        or msg.stickers
        or msg.components
        or msg.poll
        or msg.message_snapshots
    )
```

**Como ela produz falso positivo — honestamente:**

| Falso positivo | Por quê | Mitigação |
|---|---|---|
| Mensagem de sistema (entrou no servidor, fixou mensagem, criou thread, boost) | `content` legitimamente vazio | O `msg.type not in (...)` já corta — **é a linha que faz a heurística funcionar** |
| Enquete pura | `content` vazio, `poll` preenchido | `or msg.poll` cobre. **UNVERIFIED** se `poll` é bloqueado pela intent (a doc do Discord não lista `poll` entre os campos censurados; a `discord.py` também não anota) |
| Mensagem encaminhada (forward) | conteúdo mora em `message_snapshots`, não no `content` externo | `or msg.message_snapshots` cobre. **UNVERIFIED** se o conteúdo do snapshot também é censurado |
| Um `MessageType` novo que o Discord criar amanhã | Não estará na tupla | Aceito: a consequência é um aviso a mais, não um anúncio perdido |

**Como ela produz falso NEGATIVO — e este é o perigoso:** `msg.content` vem preenchido **mesmo sem a intent** quando (i) o bot é mencionado, (ii) é DM, ou (iii) a mensagem foi enviada pelo próprio bot. `[VERIFIED: discord/flags.py:1256-1262]`

> 🔴 **ISTO PRECISA ENTRAR NO ROTEIRO DO PORTÃO HUMANO, LITERALMENTE:**
> **A mensagem de teste do critério 2 NÃO pode mencionar o bot e NÃO pode ser postada pelo próprio bot.** Postar `@ponte teste` faz o texto chegar certinho **mesmo com a intent desligada** — o teste passa verde e o modo de falha mais caro do projeto fica escondido até o primeiro anúncio de guild de verdade.
> Texto de teste correto: `teste da ponte 1` — sem `@`, postado por uma pessoa.

**Por que a heurística nunca vira o mecanismo principal:** ela é probabilística e o pré-voo é determinístico. A ponte deve *morrer no arranque* pelo pré-voo, e *gritar em runtime* pela heurística. Ela nunca deve **descartar** a mensagem — grita, registra, e segue (nesta fase, imprimindo o vazio no console com o aviso ao lado).

### 2.5 — Recado curto para o `01-PLAN.md`

- Pré-voo em `setup_hook()` usando `application_flags`, **matando o arranque** — é o mecanismo.
- Heurística de runtime como segunda linha, **avisando, não descartando**.
- `except discord.PrivilegedIntentsRequired` como terceira rede.
- Teste unitário: um `Message` falso (ou um `SimpleNamespace` com os campos) alimentando `parece_intent_desligada` — cobre mensagem de sistema, anexo puro, enquete e o caso todo-vazio. Não precisa de rede.

---

## §3 — Resolução de menções e marcação (decide quanto do FORM-03 é grátis)

### `clean_content` existe e é uma `property` de `Message`

Implementação verbatim do que importa:

```python
# discord/message.py:2611
result = re.sub(r'<(@[!&]?|#)([0-9]{15,20})>', repl, self.content)
return escape_mentions(result)
```

`[VERIFIED: discord/message.py:2556-2613]`

### O que ele RESOLVE

| Marcação crua | Vira | Fallback quando não resolve |
|---|---|---|
| `<@123>` e `<@!123>` (usuário) | `@{display_name}` | **`@deleted-user`** |
| `<@&123>` (cargo) | `@{role.name}` | **`@deleted-role`** |
| `<#123>` (canal) | `#{channel.name}` | **`#deleted-channel`** |
| `@everyone` / `@here` | `@` + `U+200B` + `everyone` / `here` (zero-width space no meio, vira não-menção) | — |

`[VERIFIED: discord/message.py:2574-2584 e discord/utils.py:1016-1039]`

### O que ele NÃO resolve — e portanto é código nosso na Fase 2

| Marcação crua | Sai como | Precisa? |
|---|---|---|
| `<:nome:123>` (emoji custom) | **intocado, cru** | **SIM — FORM-03 pede `:nome:` explicitamente** |
| `<a:nome:123>` (emoji animado) | intocado | SIM, mesmo tratamento |
| `<t:1724800000:R>` (timestamp) | intocado | não pedido, mas fica número cru no celular |
| `</comando:123>` (menção de slash command) | intocado | não pedido; canal de anúncio raramente usa |
| Markdown (`**negrito**`, `||spoiler||`, `# titulo`) | intocado — **a docstring diz isso explicitamente** | decisão de Fase 2 |

O regex começa em `<` seguido de `@`, `@!`, `@&` ou `#`. `:`, `a:`, `t:` e `/` não casam com nada. `[VERIFIED: o regex acima, discord/message.py:2611]`

### Nuances que mudam o plano da Fase 2

**1. `display_name` de usuário resolve SEM a intent SERVER MEMBERS.** `clean_content` faz `self.guild.get_member(id) or utils.get(self.mentions, id=id)`. O cache de membros exige a intent privilegiada `members`, mas o fallback usa `Message.mentions` — que é montado do payload do evento via `Member._try_upgrade`, e o Discord manda a chave `member` embutida em cada objeto de `mentions` para mensagens de guild. Com a chave presente vira um `Member` de verdade, **com apelido de servidor**. `[VERIFIED: discord/message.py:2473-2487 e discord/member.py:383-391]`

> **Conclusão prescritiva: NÃO ligue a intent SERVER MEMBERS.** Ela é privilegiada (mais um clique no portão humano, mais uma superfície) e não compra nada para o FORM-03. Se a chave `member` vier ausente por algum motivo, o fallback degrada para `User.display_name` = `global_name or name` `[VERIFIED: discord/user.py:313-322]` — nome global em vez de apelido de servidor. Legível do mesmo jeito.

**2. Cargo e canal dependem da intent `guilds` (não-privilegiada, `1 << 0`).** `resolve_role` usa `guild.get_role`, `resolve_channel` usa `guild._resolve_channel` — ambos alimentados pelo `GUILD_CREATE`. Sem `Intents.guilds` o cache fica vazio e **toda** menção de cargo vira `@deleted-role`, toda menção de canal vira `#deleted-channel`. `[VERIFIED: discord/message.py:2578-2584; discord/flags.py:845-872]` Por isso `guilds = True` está na assinatura mínima.

**3. `clean_content` injeta um `U+200B` (zero-width space) logo depois do `@` em `@everyone`/`@here`.** A substituição é `re.sub(r'@(everyone|here|[!&]?[0-9]{17,20})', '@<U+200B>\\1', text)`. É invisível no console e viaja para o WhatsApp. Não quebra nada, mas se a Fase 2 comparar strings em teste, o caractere está lá — o `assert` tem de escrever `"@<U+200B>everyone"`, nunca `"@everyone"`. `[VERIFIED: discord/utils.py:1039]`

**4. Se a intent MESSAGE CONTENT estiver desligada, `clean_content` devolve `""`** — ele opera sobre `self.content`. Mais um motivo para o §2 vir antes do §3 na ordem das fases, como o roadmap já decidiu.

### Veredito para o planejador

**FORM-03 é ~75% grátis.** Usuário, cargo e canal: `msg.clean_content`, zero código. Emoji custom: um `re.sub` de uma linha por cima do resultado, algo como `r'<a?:([A-Za-z0-9_]+):[0-9]+>'` → `r':\1:'`. Menção não-resolvível já vira `@deleted-user` / `@deleted-role` / `#deleted-channel` sozinha, o que **já satisfaz o critério de sucesso 3 da Fase 2** ("vira algo legível em vez de `<@123456>` cru") sem uma linha escrita.

---

## §4 — Deduplicação que sobrevive a restart (ENTR-04)

### A pergunta anterior: restart faz backfill?

**Não — e isso é o mais importante desta seção.**

- **RESUME** (reconexão rápida, mesma sessão): *"allows your app to replay any lost events starting from the last sequence number it received. After Resuming, your app will receive the missed events in the same way it would have had the connection had stayed active."* `[CITED: docs.discord.com/developers/events/gateway]`
- **IDENTIFY novo** (o que acontece quando o processo morre e sobe de novo, ou quando a sessão expira e vem `Invalid Session` op 9): o app *"should create a new connection ... then send an Identify event"*. A documentação **não menciona replay nenhum** para sessão nova. `[CITED: mesma página]`

> **Consequência direta:** um restart da ponte **não pode inundar o grupo**, porque não existe backfill — a menos que alguém chame `channel.history()`. A marca-d'água **não é gatilho de backfill**; ela é puramente guarda de duplicata. E "histórico retroativo" já está Out of Scope no `REQUIREMENTS.md`, então **o plano não pode conter nenhuma chamada a `channel.history()` / `async for ... in channel.history(...)`**. Vale um teste de grep na suíte.

### Uma marca-d'água de "maior ID visto por canal" basta?

**Quase — e o "quase" é do tipo errado.**

Snowflake do Discord: 42 bits de timestamp (ms desde 2015) nos bits 63–22, depois **5 bits de worker ID**, 5 bits de process ID e 12 bits de incremento. `[CITED: docs.discord.com/developers/reference — Snowflakes]` A documentação garante **unicidade**, mas **não garante ordenação total**: dois IDs gerados no mesmo milissegundo por workers diferentes podem sair fora da ordem real de criação. E a documentação **não diz nada** sobre entrega exactly-once nem sobre eventos duplicados. `[CITED: mesma página; ausência confirmada na leitura da página de gateway]`

Isso importa porque a marca-d'água tem um modo de falha **assimétrico e caro**: se um anúncio real chegar com ID abaixo da marca, ele é **descartado calado** — um falso negativo exatamente na coisa que o projeto existe para não perder. Uma duplicata é constrangedora; um anúncio perdido é a falha que o milestone inteiro tenta evitar.

Fontes reais de duplicata, avaliadas:

| Fonte | Acontece? | Nota |
|---|---|---|
| Replay de RESUME | **Sim, por desenho** | Mas `self.sequence = seq` é atribuído **antes** do parser rodar (`gateway.py:526-527`), então o replay começa depois do último evento *recebido*, não do último *processado*. Duplicata é improvável, perda é o risco simétrico. MEDIUM |
| `Invalid Session` (op 9) → IDENTIFY novo | Sim, mas **sem replay** | `self.sequence = None` (`gateway.py:565`). Não duplica; perde o intervalo |
| **Duas cópias da ponte rodando** (dois duplos cliques no `.bat`) | **Sim, e é a mais provável na prática** | Duas conexões independentes recebem o mesmo evento. É a duplicata que o usuário realmente vai ver |
| Edição de mensagem | Não é `on_message` | `on_message_edit` é evento separado; EDIT-01 está em Future Requirements |

`[VERIFIED: gateway.py:519-570 do wheel 2.7.1]`

### A recomendação — UMA abordagem, decidida

**Conjunto limitado de IDs já vistos, em JSONL append-only, gravado ANTES de qualquer entrega.** Não marca-d'água pura.

```
.ponte/vistos.jsonl        # uma linha por mensagem aceita, JSON
```

Formato de cada linha (idioma do `outbox.jsonl` que o repo já usa em `notificador.py:382-385`):

```json
{"id": 1538202612762022020, "canal": 1536506379752185953, "momento": 1756400000.0}
```

Comportamento:

- **Arranque:** lê o arquivo inteiro para um `set[int]` na memória. Linha corrompida (processo morto no meio da escrita) é **ignorada em silêncio**, nunca derruba o arranque — mesma leitura defensiva de `loot.py:293-305`.
- **Cada mensagem que passa pelo filtro de canal:** `if msg.id in vistos: return` **antes** de imprimir/entregar.
- **Aceitou:** `append` + `flush()` **antes** de imprimir/entregar. Isso é *at-most-once* deliberado — ENTR-04 diz "nunca entregue duas vezes", e essa é a troca que a exigência pede.
- **Compactação:** quando o arquivo passar de `TETO` linhas (sugestão: **2000**), reescreve só as últimas `TETO // 2` num `.tmp-<pid>` e faz `os.replace` — **exatamente o padrão atômico que `loot.py:269-280` já usa e que a docstring de lá justifica para Windows**. `[VERIFIED: l2scanner/loot.py:263-280]`

**Por que JSONL e não SQLite:** o repositório já usa JSONL append-only para estado durável (`outbox.jsonl`, `events.jsonl`, ambos no `.gitignore`), já usa `os.replace` para estado pequeno atômico (`.loot/`), e ambos são stdlib. `sqlite3` também é stdlib e seria mais duro, mas traria arquivo de lock, journal e um vocabulário que o repositório inteiro não fala. Consistência com o idioma existente ganha aqui.

**Por que conjunto e não marca-d'água:** um `set` de até 2000 IDs custa ~100 KB de RAM e **não assume ordenação nenhuma** — a única propriedade que a documentação do Discord garante é unicidade, e o conjunto é a estrutura que usa exatamente essa garantia e nada além. A marca-d'água máxima **também deve ser gravada**, mas só para o console e o log (`ultima mensagem vista: <id> as <hora>`, que é o que OPER-03 pede).

**Onde o arquivo mora:** `.ponte/` na raiz, seguindo o precedente de `.agenda/` e `.loot/`. → **o plano precisa acrescentar `.ponte/` ao `.gitignore`**; sem isso o estado local de uma máquina entra no git, que é a regra que o próprio `.gitignore` explica em detalhe nas linhas do `.agenda/`. `[VERIFIED: .gitignore, seção "Saída em tempo de execução"]`

**O guarda de segunda cópia (opcional, barato, resolve a duplicata mais provável):** um arquivo `.ponte/rodando.pid` escrito no arranque; se ele existir e o PID ainda estiver vivo, a ponte recusa subir dizendo "já tem uma ponte rodando". Não é exigido por nenhum REQ, mas é a defesa contra a única fonte de duplicata que o usuário vai realmente encontrar.

---

## §5 — Ciclo de vida da conexão e sinal honesto de vida (OPER-03)

### Os ganchos

| Evento | Quando dispara | Confiabilidade |
|---|---|---|
| `on_connect` | WebSocket aberto e IDENTIFY aceito | dispara também em cada reconexão |
| `on_ready` | READY recebido, cache preenchido | **pode disparar mais de uma vez** por processo |
| `on_resumed` | RESUMED recebido (sessão retomada) | o sinal de "voltei sem perder nada" |
| `on_disconnect` | qualquer queda **e também** cada ciclo normal de RESUME | dispara mais do que se imagina |
| `on_socket_event_type` | **todo** frame de dispatch do gateway | ótimo para "tempo desde o último sinal de vida" |

`[VERIFIED: discord/state.py:650, 676, 680 (dispatch de ready/connect/resumed); discord/client.py:734, 747 (dispatch de disconnect); discord/gateway.py:519-521 (socket_event_type)]`

### 🔴 O sinal que MENTE

```python
# discord/client.py:942-944
def is_closed(self) -> bool:
    """:class:`bool`: Indicates if the websocket connection is closed."""
    return self._closing_task is not None
```

`[VERIFIED: discord/client.py:942-944]`

**`is_closed()` só vira `True` quando `close()` foi chamado de propósito.** Um socket morto, um cabo arrancado, um gateway que parou de responder — nada disso muda esse valor. É **exatamente** o sinal que "continua mostrando verde depois que o socket morreu" que a pergunta descreve. **Não use `is_closed()` como indicador de saúde no console.**

### O sinal honesto

Três coisas juntas, e nenhuma sozinha:

1. **Máquina de estado nossa**, dirigida por `on_connect` / `on_ready` / `on_resumed` / `on_disconnect`. `CONECTANDO → CONECTADA → CAIU → RETOMADA`.
2. **`client.latency`** — o ida-e-volta entre HEARTBEAT e HEARTBEAT_ACK, em segundos. Devolve `float('nan')` se não há socket e `float('inf')` se não há keep-alive. `[VERIFIED: discord/client.py:375-381; discord/gateway.py:619-622]`
3. **Tempo desde o último frame do gateway**, atualizado em `on_socket_event_type`. Num canal de anúncio parado isso pode ser minutos — então mostre o número, não um semáforo.

**A garantia que fecha o buraco:** o `KeepAliveHandler` do `discord.py` tem cão-de-guarda próprio. Se nenhum frame chegar dentro de `heartbeat_timeout` (**padrão 60.0 s**, ajustável por `Client(heartbeat_timeout=...)`), ele fecha o socket e força reconexão. `[VERIFIED: discord/gateway.py:155-159, 640; parâmetro em state.py]` Isso significa: **um socket zumbi vira `on_disconnect` em no máximo ~60 segundos.** Então a máquina de estado, alimentada pelos ganchos, é honesta — desde que o console mostre "conectada há X" e "último evento há Y", e não só uma bolinha verde.

Além disso, ele já loga sozinho quando a coisa aperta: `"Can't keep up, shard ID %s websocket is %.1fs behind."` `[VERIFIED: discord/gateway.py:149, 222]` — capturar o logger `discord.gateway` no nosso arquivo rotativo entrega esse diagnóstico de graça.

### Reconexão

`Client.connect(reconnect=True)` (padrão de `run()`) tem `ExponentialBackoff` embutido, tenta RESUME primeiro, e só faz IDENTIFY novo quando o gateway invalida a sessão. `[VERIFIED: discord/client.py:720-790]` **Não escreva laço de reconexão à mão** — o único caso que ele deliberadamente NÃO reconecta é 4014 (intent) e códigos de estado ruim, que é o comportamento que queremos.

---

## §6 — Tamanho máximo de mensagem no Chatwoot (dimensiona FORM-05)

### O teto do Chatwoot: **150 000 caracteres**

```ruby
# app/models/message.rb:80
validates :content, length: { maximum: 150_000 }
```

`[VERIFIED: github.com/chatwoot/chatwoot, branch develop, app/models/message.rb:80, lido 2026-08-28]`

### O que a API devolve quando estoura: **HTTP 422**

O controller de criação de mensagem faz:

```ruby
# app/controllers/api/v1/accounts/conversations/messages_controller.rb
def create
  ...
rescue StandardError => e
  render_could_not_create_error(e.message)
end
```

e

```ruby
# app/controllers/concerns/request_exception_handler.rb:46-47
def render_could_not_create_error(error)
  render json: { error: sanitized_error_message(error) }, status: :unprocessable_entity
end
```

`[VERIFIED: ambos os arquivos lidos do branch develop do chatwoot/chatwoot em 2026-08-28]`

> 🔴 **A consequência para a Fase 3 é dura e o planejador precisa saber agora:** `notificador.py:299` classifica como transitório apenas `code >= 500 or code == 429`. **422 é 4xx → DEFINITIVO → não é repetido → o anúncio é registrado no log e perdido.** É exatamente o cenário que o FORM-05 existe para impedir, e é por isso que a truncagem tem de acontecer **antes** do POST, nunca depender de retentativa.

### Bônus achado no mesmo arquivo: limite de vazão por conversa

```ruby
if conversation.messages.where('created_at >= ?', 1.minute.ago).count >= Limits.conversation_message_per_minute_limit
  errors.add(:base, 'Too many messages')
end
```

com

```ruby
def self.conversation_message_per_minute_limit
  ENV.fetch('CONVERSATION_MESSAGE_PER_MINUTE_LIMIT', '200').to_i
end
```

`[VERIFIED: app/models/message.rb (prevent_message_flooding) e lib/limits.rb, branch develop, 2026-08-28]`

**200 mensagens por minuto por conversa**, e o estouro também vira **422 definitivo**. Irrelevante para um canal de anúncio de guild (que faz unidades por dia), mas é o teto real se alguém algum dia fizer a ponte replicar um canal movimentado.

### O limite que MANDA de verdade não é o do Chatwoot

O caminho é Discord → ponte → Chatwoot → provedor não-oficial (Baileys, segundo o comentário de `config.py:94-96`) → WhatsApp. O teto de 150 000 do Chatwoot é ordens de grandeza acima do que o WhatsApp entrega.

- **Meta Cloud API:** máximo **4096** caracteres em `text.body`; recomendação de manter abaixo de ~1600 para renderizar bem. `[ASSUMED — fontes secundárias (360dialog, engageSPARK, tyntec), não a documentação oficial da Meta; e o usuário NÃO usa a Cloud API]`
- **Baileys / provedor não-oficial:** **UNVERIFIED.** Não achei número autoritativo, e ele depende da ponte específica.
- **Discord (origem):** o `content` de uma mensagem do Discord é limitado a 2000 caracteres (4000 com Nitro), então o insumo já é pequeno. `[ASSUMED — não consta na página `docs.discord.com/developers/resources/message` que consultei, que só documenta o teto de 6000 caracteres somados nos embeds; é conhecimento de treino]`

> **Recomendação prescritiva para FORM-05, sem inventar precisão:** truncar em **1500 caracteres** com marca visível de corte (ex.: `\n[... cortado, veja no Discord]`). Justificativas: (a) é confortavelmente abaixo de qualquer teto plausível de qualquer provedor de WhatsApp; (b) é uma decisão de LEITURA no celular, não de API — um anúncio de 3000 caracteres é ilegível no WhatsApp mesmo que entregue; (c) o número vira uma chave do `config.toml` (`truncar_em = 1500`), então o usuário ajusta sem tocar código, no mesmo idioma do resto da configuração.

**Experimento que resolve o UNVERIFIED em 5 minutos** (Fase 3, não agora): postar uma mensagem de 2000 caracteres na conversa dedicada com `tools/check_whatsapp.py` e conferir no celular se chegou inteira, cortada, ou se o Chatwoot marcou a mensagem como `failed`. Uma execução responde a pergunta para este provedor específico, que é a única que importa.

---

## §7 — Bot async ao lado deste código base (Windows)

### Forma do entrypoint

O `Client.run()` já resolve Ctrl+C:

```python
# discord/client.py:920-938
async def runner():
    async with self:
        await self.start(token, reconnect=reconnect)
...
try:
    asyncio.run(runner())
except KeyboardInterrupt:
    # nothing to do here
    # `asyncio.run` handles the loop cleanup
    # and `self.start` closes all sockets and the HTTPClient instance.
    return
```

`[VERIFIED: discord/client.py:920-938]`

> **Prescrição: use `client.run(token, log_handler=None)`.** Não escreva `asyncio.run()` à mão. O `async with self` garante `close()` no `__aexit__`, e o `KeyboardInterrupt` já é engolido limpo. **E como o livro de já-vistos grava com `flush()` antes da entrega (§4), não há fila para drenar no Ctrl+C** — nada se perde numa saída abrupta. Essa é a razão de a ordem "gravar antes de entregar" ter sido escolhida.

### 🔴 `log_handler=None` não é detalhe — é o OPER-02

```python
# discord/client.py:924-930
if log_handler is not None:
    utils.setup_logging(handler=log_handler, ...)
```

O padrão do parâmetro é `MISSING` (que **não é `None`**), então **por padrão o `discord.py` instala um `StreamHandler` próprio no logger `discord`** e o console ganha um log paralelo que a ponte não controla. `[VERIFIED: discord/client.py:858, 924-930]`

Passar `log_handler=None` desliga isso e devolve o controle. Aí configuramos como o scanner já faz (`__main__.py:145-176`): `RotatingFileHandler` + `StreamHandler`, anexados **ao nosso logger e também ao logger `discord`**, para que os avisos de gateway (`"Can't keep up..."`, `"session has been invalidated"`) caiam no arquivo rotativo da ponte.

```python
# logs/ponte-discord.log  — separado de logs/scanner.log (OPER-02)
arquivo = RotatingFileHandler(
    PASTA_LOGS / "ponte-discord.log", maxBytes=2_000_000, backupCount=3,
    encoding="utf-8",
)
```

Espelha `l2scanner/__main__.py:166-168` (`scanner.log`, `maxBytes=2_000_000`, `backupCount=3`). `[VERIFIED: l2scanner/__main__.py:166-168]` `logs/` e `*.log` já estão no `.gitignore`. `[VERIFIED: .gitignore]`

### 🔴 Console em UTF-8 — obrigatório aqui, mais do que no scanner

```python
for fluxo in (sys.stdout, sys.stderr):
    try:
        fluxo.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
```

`[VERIFIED: l2scanner/__main__.py:156-160]`

O scanner faz isso porque os alertas têm acento. **A ponte precisa disso muito mais**: ela imprime **texto arbitrário de usuário do Discord** — emoji, cirílico, kaomoji, o que a pessoa digitar. O console do Windows abre em cp1252; sem o `reconfigure`, um `print()` de uma mensagem com emoji levanta `UnicodeEncodeError` e **derruba o handler**. O `errors="replace"` é a rede: caractere que a fonte do console não tem vira `?` em vez de exceção.

### Ressalva de event loop no Windows

O laço padrão no Windows desde o Python 3.8 é o `ProactorEventLoop`. `[CITED: docs.python.org/3/library/asyncio-platforms.html]`

> **Prescrição: NÃO troque a política de event loop.** Trocar para `WindowsSelectorEventLoopPolicy` (receita muito copiada da internet, herdada de problemas com `aiodns`) é uma regressão: o `SelectSelector` limita a 512 sockets e não suporta subprocesso. `[CITED: mesma página]` A ponte não usa `aiodns` — o `discord.py` só o declara no extra `[speed]` e ainda assim com marcador `sys_platform != "win32"`. `[VERIFIED: requires_dist do PyPI JSON de discord.py 2.7.1]`

**Ruído conhecido no Ctrl+C (MEDIUM):** há relato recorrente de `RuntimeError: Event loop is closed` vindo de `_ProactorBasePipeTransport.__del__` **depois** que o programa já saiu limpo, no Windows. `[CITED: Rapptz/discord.py issues #4203, #5209, #1490, discussion #5938 — relatos de comunidade, a maioria da era Python 3.8]` **UNVERIFIED em Python 3.12.10 nesta máquina.** É cosmético (o processo sai com o código certo), mas se aparecer, um usuário não-desenvolvedor vai achar que quebrou.

**Experimento de 2 minutos que resolve** (vale como tarefa do plano): depois que a ponte conectar uma vez, apertar Ctrl+C no console e olhar. Se o traceback aparecer, o conserto é o `.bat` imprimir uma linha de despedida limpa (`echo Ponte encerrada.`) depois do comando Python, ou um `atexit`/`try/finally` que imprima "Ponte encerrada." por último — de qualquer jeito **não** tentar suprimir a exceção do `__del__`, que é do interpretador.

### PONTE-05 — processo separado, mesmo `.venv`

Os dois processos compartilham o `.venv`, o que é certo (um `requirements.txt`, um firewall). O `.bat` da ponte segue `vigiar-party.bat` inteiro (busca do Python, criação do venv, instalação) com **uma linha diferente**, a sonda de dependências:

```bat
".venv\Scripts\python.exe" -c "import discord" >nul 2>&1
if errorlevel 1 (
    echo  Faltam dependencias novas. Instalando...
    ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
    if errorlevel 1 goto erro_deps
)
```

Espelhando `vigiar-party.bat`, que sonda `import mss,cv2,numpy,windows_capture,winrt.windows.media.ocr,winrt.windows.graphics.imaging`. `[VERIFIED: vigiar-party.bat]`

**Consequência que o plano precisa registrar:** `vigiar-party.bat` **não** ganha `discord` na sua linha de sonda. Ele continua sondando só o que ele usa — mas como os dois usam o mesmo `requirements.txt`, subir o scanner depois de acrescentar `discord.py` **vai** instalar a biblioteca no venv dele também. Isso é inofensivo (o scanner nunca a importa) e é o preço de ter um arquivo de dependências só, que é o que o firewall exige.

---

## Don't Hand-Roll

| Problema | Não construa | Use | Por quê |
|---|---|---|---|
| Falar o protocolo do gateway | Cliente WebSocket próprio | `discord.py` | Handshake, IDENTIFY, RESUME, sequência, heartbeat, compressão zlib, sharding |
| Reconectar após queda | Laço `while True` com `sleep` | `run(..., reconnect=True)` | `ExponentialBackoff` + RESUME + invalidação de sessão já implementados (`client.py:720-790`) |
| Cão-de-guarda de socket morto | Timer próprio | `KeepAliveHandler` embutido | Já fecha e reconecta em `heartbeat_timeout` (60 s) `[VERIFIED: gateway.py:155-159]` |
| Resolver `<@123>` / `<@&123>` / `<#123>` | Regex própria + chamadas REST | `Message.clean_content` | Já resolve os três com fallback legível `[VERIFIED: message.py:2556-2613]` |
| Descobrir se a intent está ligada | Esperar a primeira mensagem vazia | `Client.application_flags` | Resposta determinística da API, antes do gateway (§2.2) |
| Cliente HTTP do Chatwoot | Novo cliente com `requests` | `NotificadorChatwoot` (Fase 3) | Já existe, roda em produção, usa `urllib` stdlib, `ErroDeEntrega` já separa transitório de definitivo |
| Ler `.env` | `python-dotenv` | `l2scanner.config.ler_env` | Já existe (`config.py:40-53`), stdlib, e o repositório não usa `python-dotenv` |
| Escrita atômica de estado pequeno | `open("w")` direto | `.tmp-<pid>` + `os.replace` | Padrão já justificado para Windows em `loot.py:263-280` |

**Insight central:** o `discord.py` não é "uma dependência a mais", é o **contrato do protocolo**. Tudo que ele já faz — reconexão, heartbeat, cache de guild, resolução de menção, exceção de intent — é código que este projeto não vai escrever nem manter. O que **não** pode ser delegado a ele é o que é do domínio: qual canal, qual mensagem já foi vista, e o que dizer no console.

---

## Common Pitfalls

### 1. Testar o critério 2 mencionando o bot — o mais caro de todos
**O que acontece:** o usuário posta `@ponte teste`, o texto chega perfeito, todo mundo comemora, e a intent nunca esteve ligada.
**Por quê:** `content` vem preenchido sem a intent quando o bot é mencionado, é DM, ou a mensagem é do próprio bot. `[VERIFIED: discord/flags.py:1256-1262]`
**Como evitar:** o roteiro do portão humano diz, com estas palavras: **"poste `teste da ponte 1`, sem @ nenhum, com a sua conta"**.
**Sinal de alerta:** a única mensagem que já chegou com texto é a que mencionava o bot.

### 2. Usar `is_closed()` como "estou vivo"
**O que acontece:** o console mostra "CONECTADA" para sempre depois que a rede caiu.
**Por quê:** `is_closed()` reflete `close()` deliberado, não o estado do socket. `[VERIFIED: client.py:942-944]`
**Como evitar:** máquina de estado por gancho + `client.latency` + tempo desde o último evento (§5).

### 3. Chamar `channel.history()` "só para pegar o que perdi"
**O que acontece:** o primeiro restart vira um flood no grupo do WhatsApp.
**Por quê:** o gateway não faz backfill; a única forma de trazer histórico é pedir por REST — e "histórico retroativo" está Out of Scope no `REQUIREMENTS.md`.
**Como evitar:** um teste que faz grep por `.history(` no módulo da ponte e falha se encontrar. Custa 4 linhas e trava a decisão.

### 4. Filtrar `if message.author.bot: return`
**O que acontece:** o anúncio de guild — que é o **caso principal** — é descartado.
**Por quê:** é o recorte mais copiado de tutorial de bot do Discord, e ele existe para bots que respondem a comandos, não para pontes.
**Como evitar:** o filtro é **só** `message.author.id == self.user.id`. PONTE-04 diz isso explicitamente. Vale um teste com um `Message` falso de webhook confirmando que ele **passa**.
**Nota:** mensagem de webhook nunca colide com esse teste — `message.author.id` de webhook é o ID do webhook, e `message.webhook_id` fica preenchido.

### 5. Declarar `discord.py` num segundo arquivo trazido por `-r`
**O que acontece:** `tests/test_firewall_escopo.py` fica **vermelho** com `AssertionError`.
**Por quê:** a varredura declarada recusa `-r`, `--requirement`, `-e` e `--editable` de propósito, com a razão escrita na mensagem. `[VERIFIED: tests/test_firewall_escopo.py:95, 157-167]`
**Como evitar:** uma linha `discord.py>=2.7.1,<3` no `requirements.txt`.

### 6. Esquecer o `reconfigure(encoding="utf-8")` no console
**O que acontece:** a primeira mensagem com emoji derruba o handler com `UnicodeEncodeError`.
**Por quê:** console do Windows em cp1252, e a ponte imprime texto arbitrário de usuário.
**Como evitar:** copiar `__main__.py:156-160` verbatim. Teste: postar `🎉 teste` e ver imprimir.

### 7. Deixar o `discord.py` instalar seu `StreamHandler`
**O que acontece:** OPER-02 quebra — o log da ponte aparece duplicado no console e parcialmente fora do arquivo rotativo.
**Por quê:** `log_handler` tem padrão `MISSING`, não `None`, e `if log_handler is not None` é verdadeiro. `[VERIFIED: client.py:858, 924-930]`
**Como evitar:** `run(token, log_handler=None)` e configurar `logging` nós mesmos, anexando também ao logger `discord`.

### 8. Trocar a política de event loop para `WindowsSelectorEventLoopPolicy`
**O que acontece:** limite de 512 sockets, sem subprocesso, nenhum ganho.
**Por quê:** receita copiada de problemas com `aiodns`, que este projeto não usa.
**Como evitar:** não mexer. O `ProactorEventLoop` é o padrão certo. `[CITED: docs.python.org/3/library/asyncio-platforms.html]`

### 9. Ligar mais intents "por garantia"
**O que acontece:** `members` e `presences` são privilegiadas — cada uma vira mais um clique no portão humano e mais uma chance de o bot não subir.
**Por quê:** `members` parece necessária para resolver menção de usuário, mas **não é** — o fallback via `Message.mentions` já entrega `Member` com apelido de servidor (§3).
**Como evitar:** `Intents.none()` como base, três bits ligados, cada um com comentário dizendo o que compra.

---

## Code Examples

Todos os trechos abaixo derivam do fonte lido nesta sessão. Identificadores em português sem acento, como manda o repositório.

### Esqueleto completo do recebimento

```python
"""ponte_discord.py — a metade de ENTRADA da ponte.

O scanner e um laco sincrono de 1 Hz; esta ponte e async e orientada a evento.
Sao processos SEPARADOS de proposito: subir, cair ou reiniciar um nao afeta o
outro, e nenhum dos dois toca o `__main__.py` de 2047 linhas.
"""
from __future__ import annotations

import logging

import discord

log = logging.getLogger("ponte")

# Assinatura MINIMA de intents. `none()` e a base; cada bit ligado abaixo tem
# um motivo escrito, e nenhum privilegiado alem do MESSAGE CONTENT entra.
INTENCOES = discord.Intents.none()
INTENCOES.guilds = True            # 1 << 0  — sem isto, cargo e canal viram "deleted"
INTENCOES.guild_messages = True    # 1 << 9  — e o que dispara on_message
INTENCOES.message_content = True   # 1 << 15 — PRIVILEGIADA: o texto em si


class Ponte(discord.Client):

    def __init__(self, guild: int, canais: frozenset[int], vistos) -> None:
        super().__init__(intents=INTENCOES)
        self._guild = guild
        self._canais = canais
        self._vistos = vistos
        self.ultima_vista: str = "(nenhuma ainda)"

    # -- pre-voo (ver secao 2) --------------------------------------------
    async def setup_hook(self) -> None:
        flags = self.application_flags
        if not (flags.gateway_message_content or flags.gateway_message_content_limited):
            raise IntentDeConteudoDesligada(CONSERTO_DA_INTENT)
        if not self.intents.message_content:
            raise IntentDeConteudoDesligada(
                "MESSAGE CONTENT esta ligada no painel mas nao foi declarada "
                "no codigo. Sem a declaracao o Discord nao manda o texto."
            )

    # -- ciclo de vida (OPER-03, ver secao 5) ------------------------------
    async def on_ready(self) -> None:
        nomes = ", ".join(str(c) for c in sorted(self._canais))
        log.info("Conectada como %s. Ouvindo os canais: %s", self.user, nomes)

    async def on_resumed(self) -> None:
        log.info("Sessao RETOMADA — nada foi perdido no intervalo.")

    async def on_disconnect(self) -> None:
        # Dispara tambem em ciclo NORMAL de RESUME. Nao e alarme por si so.
        log.debug("Socket caiu; a biblioteca vai tentar retomar sozinha.")

    # -- recebimento --------------------------------------------------------
    async def on_message(self, msg: discord.Message) -> None:
        # PONTE-02: so os dois canais. Um ID de thread nunca casa com um ID
        # de canal, entao isto tambem deixa thread de fora sem uma linha extra.
        if msg.channel.id not in self._canais:
            return

        # PONTE-04: so as MINHAS mensagens sao descartadas. Bot e webhook
        # PASSAM — anuncio de guild costuma vir de bot, e esse e o caso
        # principal. `author.id` de webhook e o ID do webhook, nunca o meu.
        if self.user is not None and msg.author.id == self.user.id:
            return

        # ENTR-04: grava ANTES de qualquer entrega. At-most-once e a troca
        # que a exigencia pede: "nunca entregue duas vezes".
        if self._vistos.ja_vi(msg.id):
            log.debug("Mensagem %s ja vista; ignorando.", msg.id)
            return
        self._vistos.marcar(msg.id, msg.channel.id)

        if parece_intent_desligada(msg):
            log.error(
                "MENSAGEM VAZIA de %s no canal %s. Causa provavel: a intent "
                "MESSAGE CONTENT foi DESLIGADA no painel do Discord com a "
                "ponte rodando.\n%s",
                msg.author, msg.channel.id, CONSERTO_DA_INTENT,
            )

        # Fase 1 para AQUI: sem formato, sem entrega. So a prova do texto.
        self.ultima_vista = f"[{msg.channel.id}] {msg.author}: {msg.content}"
        log.info("%s", self.ultima_vista)
```

### Arranque

```python
def main() -> int:
    configurar_log()          # espelha __main__.py:145-176, mas ponte-discord.log
    try:
        cfg = ler_config_da_ponte()      # config.toml [discord] — CONF-02/CONF-03
        token = ler_token_do_discord()   # .env DISCORD_BOT_TOKEN — CONF-01
    except ConfigDaPonteInvalida as erro:
        log.error("%s", erro)
        return 2

    ponte = Ponte(cfg.guild, frozenset(cfg.canais), LivroDeVistos(PASTA_PONTE))

    try:
        # log_handler=None: o log e NOSSO (OPER-02). Ver client.py:924-930.
        ponte.run(token, log_handler=None)
    except IntentDeConteudoDesligada as erro:
        log.error("%s", erro)
        return 2
    except discord.PrivilegedIntentsRequired as erro:
        log.error("%s\n\n%s", erro, CONSERTO_DA_INTENT)
        return 2
    except discord.LoginFailure:
        log.error(
            "DISCORD_BOT_TOKEN invalido ou revogado.\n"
            "Gere outro em https://discord.com/developers/applications > Bot > Reset Token."
        )
        return 2
    return 0
```

---

## State of the Art

| Antes | Agora | Quando mudou | O que significa aqui |
|---|---|---|---|
| Bot lia o texto de toda mensagem sem pedir nada | MESSAGE CONTENT é intent privilegiada, ligada por humano no painel | set/2022 | É a razão de existir o portão humano e a §2 inteira |
| `client.run()` com laço de reconexão escrito à mão | `reconnect=True` + `ExponentialBackoff` + RESUME embutidos | `discord.py` 1.x → 2.x | Não escreva laço de reconexão |
| `Client(...)` sem `intents` | `intents` é obrigatório no construtor desde a 2.0 | 2.0 (2022) | O código tem de declarar a assinatura explicitamente |
| `@client.event async def on_ready` como único gancho | `setup_hook()` roda **antes** do gateway | 2.0 | É o que torna o pré-voo determinístico possível |
| Descobrir intent faltando esperando mensagem vazia | `ApplicationFlags.gateway_message_content[_limited]` via `GET /applications/@me` | 2.0 | A descoberta central desta pesquisa |

**Descontinuado / não use:**
- `discord.Client(...)` sem `intents` — `TypeError` na 2.x.
- `@bot.command` / `commands.Bot` — a ponte não tem comando nenhum. `commands.Bot` traria o aviso `"Privileged message content intent is missing"` (`ext/commands/bot.py:228-235`) que **não** é o mecanismo que queremos: ele é `_log.warning`, não uma exceção, e só dispara se houver prefixo de comando configurado.

---

## Environment Availability

| Dependência | Exigida por | Disponível | Versão | Fallback |
|---|---|---|---|---|
| CPython 64-bit | tudo | ✓ | **3.12.10** (`.venv`), 3.12.10 (global) | — |
| `pip` | instalação | ✓ | 26.2.1 | — |
| `.venv` do projeto | os dois `.bat` | ✓ | 16 distribuições instaladas | — |
| `discord.py` | a ponte inteira | **✗** | — | **sem fallback** — é a dependência da fase |
| Acesso a `discord.com` (HTTPS + WSS) | gateway | UNVERIFIED | — | sem fallback |
| Token de bot do Discord | PONTE-01 | **✗ — portão humano** | — | **sem fallback** |
| Intent MESSAGE CONTENT ligada | critério 2 | **✗ — portão humano** | — | **sem fallback** |
| Bot convidado no guild `936957935572103169` com `View Channel` | PONTE-02 | **✗ — portão humano** | — | sem fallback |
| `conversation_id` do Chatwoot dedicado | ENTR-02 (Fase 3) | **✗ — portão humano** | — | modo simulação (CONF-04) cobre a Fase 1 |

`[VERIFIED: .venv/Scripts/python.exe --version e -m pip list, executados 2026-08-28]`

**Faltando sem fallback (bloqueia execução):** `discord.py` (resolve com `pip install -r requirements.txt`) e os **4 passos do portão humano**, que nenhum agente pode fazer.

**Nota sobre `Read Message History`:** o `REQUIREMENTS.md` pede `View Channel` + `Read Message History` no convite. `View Channel` é **necessária** — sem ela o gateway simplesmente não manda `MESSAGE_CREATE` daquele canal. `Read Message History` só é exigida para buscas REST de histórico, que esta ponte **não faz** e não pode fazer (Out of Scope). Pedir as duas é inofensivo e mantém a porta aberta; só não é verdade que a segunda seja obrigatória. `[ASSUMED — comportamento de permissão do gateway, não verificado contra documentação nesta sessão]`

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1` no `.planning/config.json`. `[VERIFIED: .planning/config.json]`

### Categorias ASVS aplicáveis

| Categoria ASVS | Aplica | Controle padrão |
|---|---|---|
| V2 Authentication | sim | Token de bot no `.env`, nunca no `config.toml`. `.env` já está no `.gitignore` `[VERIFIED: .gitignore linha 2]`. O token **nunca** entra em log nem em mensagem de erro — é a regra já escrita no cabeçalho de `config.py:6` |
| V3 Session Management | não | Não há sessão de usuário; a sessão do gateway é gerida pela biblioteca |
| V4 Access Control | **sim** | Lista fechada de canais (`frozenset` de dois IDs) e de guild. O gateway entrega tudo que o bot enxerga; o recorte é nosso |
| V5 Input Validation | **sim** | Config validada no arranque com mensagem que nomeia a chave (CONF-03, idioma de `config.py:167-260`). Texto do Discord é **entrada não confiável** — ver abaixo |
| V6 Cryptography | não | TLS é do `aiohttp`; nada de cripto próprio |
| V7 Error Handling / Logging | **sim** | Log rotativo próprio (OPER-02); nenhum segredo no log |

### Ameaças específicas desta ponte

| Padrão | STRIDE | Mitigação |
|---|---|---|
| Token de bot vazando em screenshot do `config.toml` | Information Disclosure | `.env` + `.gitignore`, mesma regra do token do Chatwoot (CONF-01) |
| Token em traceback ou log | Information Disclosure | Nunca formatar o token em mensagem; `discord.LoginFailure` não o inclui |
| **Texto do Discord é entrada de terceiro não confiável** — qualquer pessoa no servidor pode postar | Tampering / Spoofing | O texto **só** é impresso e (na Fase 3) posto como `content` num JSON. Não é `eval`, não vira comando, não é interpolado em shell. O `notificador.py` monta o corpo com `json.dumps` `[VERIFIED: notificador.py:280-282]`, então injeção de JSON está fechada |
| Confusão com o canal de COMANDO do scanner | Elevation of Privilege | ENTR-02 já exige conversa do Chatwoot **separada**. Crítico: o scanner aceita comando de `CHATWOOT_CONVERSAS_COMANDO` `[VERIFIED: config.py:97-101]` — a conversa da ponte **nunca** pode ser uma dessas, senão um anúncio do Discord contendo `.status` viraria comando no scanner |
| Flood do Discord virando flood no WhatsApp | Denial of Service | Fase 3: o `Despachante` tem fila `maxsize=200` `[VERIFIED: notificador.py:347]` e o Chatwoot corta em 200 msg/min por conversa (§6) |
| Segunda cópia da ponte duplicando tudo | — | Guarda de PID (§4) |

> 🔴 **Item de segurança concreto para o plano:** a validação de arranque (CONF-03) deve **recusar** uma `conversa_de_destino` que também apareça em `CHATWOOT_CONVERSAS_COMANDO`. Sem esse guarda, `<@everyone> use .status` postado por qualquer membro do servidor XM Games vira um comando executado no scanner. É uma comparação de duas listas e um `raise`.

---

## Assumptions Log

| # | Afirmação | Seção | Risco se estiver errado |
|---|---|---|---|
| A1 | `poll` **não** é censurado pela intent MESSAGE CONTENT | §2.4 | Enquete pura com a intent desligada não dispara o aviso — falso negativo raro; o pré-voo já cobriu |
| A2 | Conteúdo de `message_snapshots` (encaminhamento) **é** censurado pela intent | §2.4 | Mesma consequência de A1 |
| A3 | Limite do WhatsApp via Baileys é ≥ 1500 caracteres | §6 | Truncagem de FORM-05 no lugar errado; o experimento de 5 min resolve |
| A4 | Meta Cloud API limita `text.body` a 4096 | §6 | Irrelevante — o usuário não usa a Cloud API |
| A5 | `content` do Discord limita em 2000 (4000 com Nitro) | §6 | Só afeta o dimensionamento do pior caso; a truncagem em 1500 protege de qualquer jeito |
| A6 | `Read Message History` não é obrigatória para `on_message` | Env. Availability | Nenhum — a permissão está sendo pedida de qualquer forma |
| A7 | Ruído `RuntimeError: Event loop is closed` no Ctrl+C ainda ocorre em py3.12/Windows | §7 | Só cosmético; experimento de 2 min resolve |
| A8 | Toggle do painel reflete instantaneamente nas `ApplicationFlags` para app não-verificado (<100 guilds) | §2.2 | Se houver atraso, o pré-voo daria falso alarme depois de o usuário ligar; a rede do 4014 e a heurística continuam valendo |

---

## Open Questions (com o experimento que resolve cada uma)

1. **`poll` e `message_snapshots` são censurados pela intent?**
   O que sabemos: a documentação do Discord e as docstrings da `discord.py` listam só `content`, `embeds`, `attachments` e `components` como censurados.
   O que falta: confirmação para `poll` e `message_snapshots`.
   **Experimento (5 min, depois do portão humano):** com a intent LIGADA, postar uma enquete e um encaminhamento nos canais alvo e olhar os campos no console. Depois DESLIGAR a intent no painel, repostar, e comparar. Duas execuções respondem as duas perguntas.
   Recomendação até lá: manter `poll` e `message_snapshots` na heurística. O pior caso é um aviso a menos, nunca um anúncio perdido.

2. **Qual o teto real de texto do provedor de WhatsApp do usuário?**
   O que sabemos: Chatwoot aceita 150 000 e devolve 422 acima disso (VERIFICADO no fonte).
   O que falta: o que o Baileys/WAHA entrega.
   **Experimento (5 min, Fase 3):** `tools/check_whatsapp.py` postando 2000 caracteres na conversa dedicada; conferir no celular se chegou inteiro, cortado, ou se o Chatwoot marcou `failed`.
   Recomendação até lá: truncar em 1500, configurável.

3. **O Ctrl+C imprime traceback nesta máquina?**
   **Experimento (2 min):** subir a ponte, esperar `on_ready`, Ctrl+C, olhar.
   Recomendação até lá: `.bat` com linha de despedida depois do comando Python.

4. **A latência ponta-a-ponta cabe no "em segundos" do Core Value?**
   O gateway entrega em ~centenas de ms; o gargalo será o POST do Chatwoot mais o provedor de WhatsApp — o mesmo caminho que os alertas de party já usam e que o usuário já mediu como aceitável.
   **Experimento:** na Fase 3, postar no Discord olhando o relógio e o celular.

---

## Sources

### Primárias (HIGH — fonte lida nesta sessão)
- **Wheel `discord_py-2.7.1-py3-none-any.whl`**, baixado do PyPI e extraído em 2026-08-28. Arquivos lidos: `client.py`, `errors.py`, `flags.py`, `gateway.py`, `message.py`, `member.py`, `state.py`, `user.py`, `utils.py`, `ext/commands/bot.py`, `appinfo.py`. **Toda linha citada com número de linha veio daqui.**
- **PyPI JSON API** (`/pypi/{pkg}/json`) para `discord.py`, `py-cord`, `nextcord`, `disnake`, `hikari`, `interactions.py`, `audioop-lts` — versões, datas, `requires_python`, `requires_dist`, tipos de distribuição.
- **`METADATA` do wheel 2.7.1**, buscado direto de `files.pythonhosted.org/...whl.metadata`.
- **`pip install --dry-run --report`** contra o `.venv` real do repositório (pip 26.2.1) — árvore transitiva resolvida, 11 distribuições.
- **GitHub API** `/repos/Rapptz/discord.py` e `/commits` — atividade de manutenção.
- **`github.com/chatwoot/chatwoot`, branch `develop`**: `app/models/message.rb`, `app/controllers/api/v1/accounts/conversations/messages_controller.rb`, `app/controllers/concerns/request_exception_handler.rb`, `lib/limits.rb`.
- **Este repositório**, lido nesta sessão: `l2scanner/__init__.py`, `l2scanner/config.py`, `l2scanner/notificador.py`, `l2scanner/loot.py:250-320`, `l2scanner/__main__.py:140-195`, `tests/test_firewall_escopo.py`, `requirements.txt`, `vigiar-party.bat`, `.gitignore`, `.planning/config.json`, `.planning/workstreams/discord/REQUIREMENTS.md`, `.planning/workstreams/discord/ROADMAP.md`, `01-PATTERNS.md`.

### Secundárias (MEDIUM — documentação oficial, lida via fetch)
- `docs.discord.com/developers/resources/application` — tabela de Application Flags, `1 << 18` e `1 << 19`.
- `docs.discord.com/developers/events/gateway` — close code 4014, Resume/replay, Invalid Session op 9.
- `docs.discord.com/developers/reference` — layout do snowflake, garantia de unicidade.
- `docs.discord.com/developers/resources/message` — limite de 6000 caracteres somados em embeds.
- `docs.python.org/3/library/asyncio-platforms.html` — `ProactorEventLoop` padrão no Windows desde 3.8; limitações do `SelectorEventLoop`.
- `gsd-tools query package-legitimacy check --ecosystem pypi`.

### Terciárias (LOW — comunidade, marcadas como tal no texto)
- Rapptz/discord.py issues [#4203](https://github.com/Rapptz/discord.py/issues/4203), [#5209](https://github.com/Rapptz/discord.py/issues/5209), [#1490](https://github.com/Rapptz/discord.py/issues/1490), [discussion #5938](https://github.com/Rapptz/discord.py/discussions/5938) — ruído de `Event loop is closed` no Windows.
- [360dialog](https://docs.360dialog.com/partner/messaging/sending-and-receiving-messages/text-messages), [engageSPARK](https://www.engagespark.com/support/whatsapp-business-limits/), [tyntec](https://www.tyntec.com/helpcenter/docs/faqs/whatsapp-business/message-types-templates/use-cases-what-are-the-character-limits-with-media-message-templates/) — limite de 4096 caracteres da WhatsApp Cloud API. **Não é a documentação da Meta, e não é o provedor deste usuário.**

---

## Metadata

**Confiança por área:**

| Área | Nível | Motivo |
|---|---|---|
| Escolha e versão da biblioteca | **HIGH** | PyPI JSON + GitHub API + resolução real de dependências, tudo nesta sessão |
| **§2 Detecção da intent** | **HIGH** | Fonte da biblioteca lido linha a linha; corroborado pela documentação oficial do Discord nos dois bits de flag e no close code |
| §3 `clean_content` | **HIGH** | Implementação lida verbatim, incluindo o regex e os três fallbacks |
| §4 Dedupe / backfill | **HIGH** para "restart não faz backfill" (doc oficial + fonte do gateway); **MEDIUM** para a frequência real de duplicata em RESUME (a documentação não define semântica de entrega) |
| §5 Ciclo de vida | **HIGH** | Todos os pontos de dispatch e o corpo de `is_closed()` lidos no fonte |
| §6 Teto do Chatwoot | **HIGH** para os 150 000 e o 422 (fonte Ruby lido); **UNVERIFIED** para o teto do WhatsApp do provedor deste usuário |
| §7 Windows / asyncio | **HIGH** para `run()`/`log_handler`/política de loop; **MEDIUM** para o ruído do Ctrl+C |
| Firewall de escopo | **HIGH** | Banlist e as quatro varreduras lidas no teste; nenhum dos 11 nomes casa |

**Data da pesquisa:** 2026-08-28
**Válida até:** 2026-09-27 (30 dias). O `discord.py` é estável; o item que envelhece mais rápido é a versão fixada — reconferir se saiu uma 2.7.x nova antes de instalar.
