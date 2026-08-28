# Fase 1: Ponte viva — conexao provada e texto real — Mapa de Padroes

**Mapeado:** 2026-08-28
**Workstream:** discord
**Arquivos novos classificados:** 6
**Analogos encontrados:** 5 exatos / 1 sem analogo (async)

> ATENCAO PARA O PLANEJADOR: o `CLAUDE.md` deste repo descreve um stack
> (`requests`, `rich`, `pydantic`, `python-dotenv`, `uv`) que **o codigo nao usa**.
> O `requirements.txt` real tem 10 linhas e nenhuma delas e essas. Tudo que e
> HTTP, config, secret e console e **stdlib pura**. Nao planeje contra o
> `CLAUDE.md`; planeje contra o que esta abaixo.

---

## Classificacao dos arquivos

| Arquivo novo | Papel | Fluxo de dados | Analogo mais proximo | Qualidade |
|---|---|---|---|---|
| `l2scanner/ponte_discord.py` (nome sugerido) | service / ponte | event-driven, **async** | *nenhum* (ver item 9) | **SEM ANALOGO** |
| entrypoint (`main()` + guarda `__main__`) | entrypoint CLI | request-response | `l2scanner/calibrar.py:943` | exato |
| `ponte-discord.bat` | launcher | — | `avisos-tvt.bat` (inteiro) | exato |
| secao `[discord]` no `config.toml` | config | leitura + validacao no arranque | `l2scanner/config.py:167` (`_evento_de_dict`) + `calibracao.py:442` | exato |
| chave `DISCORD_BOT_TOKEN` no `.env` | config/segredo | leitura no arranque | `l2scanner/config.py:40-115` | exato |
| marca-dagua "ja vi" em disco | persistencia | escrita atomica de estado pequeno | `l2scanner/loot.py:260-305` | exato |
| `tests/test_ponte_discord.py` | teste | — | `tests/test_notificador.py`, `test_agenda.py` | exato |

---

## 1. Carregamento de config + validacao de arranque (CONF-03)

**Analogo primario:** `l2scanner/config.py:167` (`_evento_de_dict`)
**Analogo secundario (mais recente, e o melhor modelo de mensagem):** `l2scanner/calibracao.py:442` (`_conferir_as_chaves_de_mercado`)

O TOML e lido com `tomllib` stdlib. Nao ha pydantic. A validacao e **funcao a
mao** que levanta uma excecao de dominio com uma mensagem que **nomeia o campo,
diz o que veio, e diz o conserto**.

Leitura (`config.py:152-164`):

```python
caminho = caminho or ARQUIVO_CONFIG
if not caminho.exists():
    return []          # ARQUIVO AUSENTE NAO E ERRO
try:
    with caminho.open("rb") as arquivo:
        dados = tomllib.load(arquivo)
except tomllib.TOMLDecodeError as erro:
    raise AgendaInvalida(f"{caminho.name} nao e um TOML valido: {erro}") from erro
```

Validacao de um campo (`config.py:180-197`) — repare no `onde`, que cita o nome
do bloco quando ele existe:

```python
onde = f"evento '{bruto['nome']}'" if bruto.get("nome") else f"[[evento]] #{indice + 1}"
...
raise AgendaInvalida(
    f"{onde}: horario '{texto}' nao esta no formato HH:MM."
)
```

Validacao de tipo + faixa, com a armadilha do `bool` (`calibracao.py:466-480`):

```python
limiar = dados.get("mercado_limiar_da_ancora")
if limiar is not None:
    # `bool` e subclasse de `int`: `True` passaria como numero calado.
    if isinstance(limiar, bool) or not isinstance(limiar, (int, float)):
        raise CalibracaoInvalida(
            f"mercado_limiar_da_ancora precisa ser um numero, veio "
            f"{type(limiar).__name__} ({limiar!r}). Recalibre o mercado."
        )
```

Onde a excecao vira saida de processo (`__main__.py:1994-2002`) — **`log.error` +
`return 2`, nunca traceback cru**:

```python
try:
    cal = Calibracao.carregar(ARQUIVO_CALIBRACAO)
except CalibracaoInvalida as erro:
    log.error("%s", erro)
    return 2
```

Docstring que fixa a regra do repo (`config.py:144-151`):
"ARQUIVO AUSENTE NAO E ERRO. (...) Arquivo PRESENTE E MAL FORMADO, sim, e erro —
e erro de ARRANQUE. Um horario com erro de digitacao tem que derrubar o scanner
enquanto o usuario olha para o console, nunca as 15h enquanto ele esta AFK."

> **Entao o novo codigo deve:** ler `[discord]` do `config.toml` com `tomllib`,
> validar num `_conferir_as_chaves_de_discord(dados)` no estilo do
> `calibracao.py:442`, levantar uma excecao propria de dominio (ex.
> `PonteInvalida`, irma de `AgendaInvalida`) com mensagem no formato
> `"<campo>: <o que veio>. <o conserto>"`, e o entrypoint captura com
> `log.error("%s", erro); return 2`.

> **Decisao consciente do planejador:** a secao `[discord]` e OBRIGATORIA (a
> ponte nao existe sem ela) ou opcional? A agenda e o mercado escolheram
> "ausente nao e erro" porque sao acessorios do scanner. A ponte e um processo
> DEDICADO — aqui "ausente E erro" e defensavel e provavelmente certo.

---

## 2. Segredo do `.env`

**Analogo:** `l2scanner/config.py:40-115` (`ler_env` + `config_do_chatwoot`)

**Nao ha `python-dotenv`.** Ha um parser de 13 linhas escrito a mao, e a
docstring do modulo (`config.py:1-7`) diz o porque. `os.environ` nao e usado
para segredo em lugar nenhum.

```python
ARQUIVO_ENV = RAIZ / ".env"

def ler_env(caminho: Path | None = None) -> dict[str, str]:
    """Le o .env sem depender de biblioteca externa."""
    caminho = caminho or ARQUIVO_ENV
    if not caminho.exists():
        return {}
    valores: dict[str, str] = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        valores[chave.strip()] = valor.strip().strip('"').strip("'")
    return valores
```

Ausencia do token (`config.py:56-86`) — tres checagens em cascata, cada uma com
o comando exato que conserta:

```python
class ConfigAusente(Exception):
    """Falta configuracao para enviar alertas."""

...
if not env:
    raise ConfigAusente(
        "Nao encontrei o .env.\n"
        "Copie ENV-EXEMPLO.txt para .env e preencha os dados do Chatwoot."
    )
faltando = [c for c in ("CHATWOOT_URL", "CHATWOOT_ACCOUNT", "CHATWOOT_TOKEN") if not env.get(c)]
if faltando:
    raise ConfigAusente("Faltam valores no .env: " + ", ".join(faltando))
if env["CHATWOOT_TOKEN"] == "cole_seu_token_aqui":
    raise ConfigAusente("O CHATWOOT_TOKEN ainda esta com o valor de exemplo.")
```

Convencao de nome: `MAIUSCULA_COM_UNDERSCORE`, prefixada pelo servico
(`CHATWOOT_URL`, `CHATWOOT_TOKEN`, `CHATWOOT_CONVERSAS`). Listas viajam como
CSV e sao partidas com `.split(",")` + `strip()` (`config.py:77-81`).

O `ENV-EXEMPLO.txt` e um arquivo COMENTADO que ensina onde achar cada valor no
painel — e o unico arquivo do repo com acentos de proposito (e prosa para o
usuario, nao codigo).

> **Entao o novo codigo deve:** usar `DISCORD_BOT_TOKEN` (e
> `DISCORD_CANAIS=id1,id2` se os ids forem segredo — mas veja abaixo), le-lo via
> `ler_env()` do `config.py`, levantar `ConfigAusente` com a frase
> "Faltam valores no .env: DISCORD_BOT_TOKEN" + a linha do conserto, recusar o
> placeholder literal, e adicionar um bloco comentado ao `ENV-EXEMPLO.txt`.

> **Decisao do planejador:** ids de canal do Discord **nao sao segredo** — pelo
> mesmo raciocinio escrito em `config.py:266-289` sobre `[[membro]]` vs
> `CHATWOOT_TELEFONES_COMANDO`. O precedente do repo manda por os ids no
> `config.toml` (`[discord] canais = [...]`) e so o token no `.env`.

---

## 3. Entrypoint + convencao de `.bat`

**Analogo do entrypoint:** `l2scanner/calibrar.py:943-944`

```python
if __name__ == "__main__":
    sys.exit(main())
```

Nao ha `pyproject.toml`, nao ha `setup.py`, nao ha `console_scripts`. Um
entrypoint e simplesmente **um modulo do pacote com `main()` e a guarda acima**,
invocado como `-m l2scanner.<modulo>`. `l2scanner/calibrar.py` prova que isso ja
funciona sem tocar em `__main__.py`:

```
".venv\Scripts\python.exe" -m l2scanner.calibrar --solo %*
```

`main()` devolve `int` (`0` ok, `2` erro de configuracao) — ver
`__main__.py:2000-2043`.

**Analogo do `.bat`:** `avisos-tvt.bat` (o mais proximo: modo que nao olha para a
tela). Forma compartilhada, na ordem:

```bat
@echo off
setlocal

REM ============================================================
REM  <Titulo> — <uma linha do que faz>
REM
REM  Basta dar dois cliques neste arquivo.
REM  <o que o usuario precisa saber antes>
REM ============================================================

cd /d "%~dp0"

REM O ambiente e o mesmo do vigiar-party.bat. Se ele ainda nao existe,
REM mandamos rodar aquele primeiro em vez de montar um segundo por conta.
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo  O ambiente ainda nao foi preparado.
    echo  Rode vigiar-party.bat uma vez primeiro — ele monta tudo.
    echo.
    pause
    exit /b 1
)

if not exist "config.toml" ( ... pause & exit /b 1 )

echo.
echo  <o que esta janela e>. Deixe esta janela aberta. Feche com Ctrl+C ou no X.
echo.

".venv\Scripts\python.exe" -m l2scanner.<modulo> %*

echo.
pause
```

Regras destiladas: **sem `uv`**; **sem `activate`** (chama o
`.venv\Scripts\python.exe` por caminho literal entre aspas); `cd /d "%~dp0"`
sempre; `%*` repassa argumentos; `pause` no fim SEMPRE (dois cliques = a janela
fecharia); cabecalho REM em portugues sem acento explicando para leigo;
`exit /b 1` nas pre-condicoes. **So o `vigiar-party.bat` monta o venv** (ele tem
a deteccao de Python de 30 linhas); todos os outros exigem que ele tenha rodado
antes.

> **Entao o novo codigo deve:** criar `l2scanner/ponte_discord.py` com
> `main() -> int` e `if __name__ == "__main__": sys.exit(main())`, e um
> `ponte-discord.bat` que e o `avisos-tvt.bat` com o titulo trocado e a ultima
> linha virando `-m l2scanner.ponte_discord %*`. `__main__.py` fica intocado.

> **Decisao do planejador:** a ponte tem uma dependencia nova
> (`discord.py`/`websockets`) que NAO esta no `requirements.txt`, e o guarda de
> dependencias do `vigiar-party.bat` (`python -c "import mss,cv2,..."`) nao a
> cobre. Decida: (a) somar ao `requirements.txt` e ao `import` de conferencia, ou
> (b) o `ponte-discord.bat` fazer o proprio `pip install --quiet` condicional.

---

## 4. Log rotativo (OPER-02)

**Analogo:** `l2scanner/__main__.py:145-176` (`configurar_log`)

```python
PASTA_LOGS = RAIZ / "logs"          # __main__.py:110

def configurar_log(verboso: bool) -> None:
    PASTA_LOGS.mkdir(exist_ok=True)

    # O console do Windows abre em cp1252 e engasga em acento e travessao.
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    formato = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S"
    )
    arquivo = RotatingFileHandler(
        PASTA_LOGS / "scanner.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    arquivo.setFormatter(formato)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formato)

    log.setLevel(logging.DEBUG if verboso else logging.INFO)
    log.addHandler(arquivo)
    log.addHandler(console)
```

Estado em disco confirmado: `logs/scanner.log` e `logs/scanner.log.1`.

Convencao de logger: `log = logging.getLogger("l2scanner")` no `__main__.py:142`,
`log = logging.getLogger("l2scanner.relogio")` em `relogio.py:41`,
`log = logging.getLogger(__name__)` nos modulos de biblioteca (`config.py:30`).

> **Entao o novo codigo deve:** copiar `configurar_log` inteiro para o modulo da
> ponte trocando so `"scanner.log"` por `"ponte-discord.log"` e o logger raiz por
> `logging.getLogger("l2scanner.ponte_discord")`. Mesmos `maxBytes=2_000_000`,
> `backupCount=3`, `encoding="utf-8"`, mesmo formatter, mesma pasta `logs/`, mesmo
> `reconfigure` de stdout — o cp1252 vai morder o texto vindo do Discord na
> primeira mensagem com emoji.

---

## 5. Console / status (OPER-03)

**Analogos:** `l2scanner/console.py` (inteiro, 148 linhas) e
`l2scanner/__main__.py:409` (`desenhar_status`)

**`rich` NAO e usado.** Nao esta no `requirements.txt` e nao e importado em lugar
nenhum. Nao ha `Live`, nao ha `Table`. O que existe:

1. **ANSI a mao, com deteccao** (`console.py:31-76`): `_habilitar_cor()` respeita
   `NO_COLOR`, checa `sys.stdout.isatty()`, e no Windows liga
   `ENABLE_VIRTUAL_TERMINAL_PROCESSING` via `ctypes.windll.kernel32`. Se algo
   falhar, `_pintar` devolve o texto cru.
2. **Molduras de texto** (`console.py:97-119`, `moldurar`) — tres linhas de
   `*`/`!`/`+`, largura 58, com carimbo de hora a direita. Usada tanto no console
   (com cor, via `destacar`) quanto no WhatsApp (sem cor) — a docstring explica
   que a geometria e uma so de proposito.
3. **Status como STRING montada e impressa**, nao como widget vivo
   (`__main__.py:409-475`): `desenhar_status` retorna uma `str` de varias linhas,
   `[vigiando]` no topo e uma linha por membro:

```python
linhas = [f"[{portao}]"]
...
linhas.append(f"  {nome:<12s} {simbolos[estado]:<6s} HP {hp}")
```

O comentario em `__main__.py:445-448` e a regra de produto que a ponte herda:
"Um scanner calado precisa PARECER calado de proposito. Sem esta linha, 'nao
chegou nada no WhatsApp' e ambiguo entre 'esta tudo bem', 'estou em silencio' e
'o scanner quebrou'."

> **Entao o novo codigo deve:** usar `logging` para o fluxo (cada mensagem
> recebida vira uma linha de `log.info`) e `console.destacar()` / `moldurar()`
> para os poucos eventos que precisam saltar aos olhos (conectou, desconectou,
> reconectando). NAO introduza `rich`. Para "a ponte esta viva", siga
> `desenhar_status`: uma funcao pura que devolve `str` (testavel!) mostrando
> `[conectado]` / `[reconectando]`, os canais vigiados e o contador de mensagens
> vistas.

---

## 6. Persistencia de estado pequeno (ENTR-04) — **o item mais importante**

Sim, o repo ja persiste estado pequeno, e ja tomou a decisao **tres vezes, com
tres idiomas diferentes e deliberados**. A marca-dagua tem que escolher um
deles, nao inventar o quarto.

### Idioma A — marcador vazio `O_CREAT | O_EXCL` (fatos discretos, "isto ja saiu")

`l2scanner/agenda.py:374-421` (`RegistroEmDisco.marcar`), pasta `.agenda/`
(`__main__.py:114`). Mesmo idioma em `loot.py:198-216` (`_criar`, tri-estado) e
`agenda.py:442-477` (`entrar`, tri-estado).

```python
def marcar(self, chave: str) -> bool:
    """True se ESTE processo deve enviar. False se alguem ja enviou."""
    if self._simulando:
        return True
    alvo = self._pasta / chave
    try:
        descritor = os.open(alvo, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    except OSError:
        # Disco cheio, permissao, pasta sumiu. Preferir o aviso duplicado
        # ao aviso perdido.
        return True
    os.close(descritor)
    return True
```

A docstring da classe (`agenda.py:312-343`) e a justificativa completa, e **fala
direto com o problema da marca-dagua**:

> "AGEN-06 reiniciar o scanner nao pode reenviar um aviso ja enviado / AGEN-07
> duas instancias rodando nao podem fazer o grupo receber em dobro. (...) Essa
> combinacao e ATOMICA no Windows: entre duas instancias competindo (...)
> exatamente uma cria o arquivo e a outra leva FileExistsError. (...) nao tem
> janela de corrida entre ler e escrever — **que e justamente o furo de um 'le o
> JSON, checa, escreve o JSON'**."
>
> "POR QUE NAO DERIVAR DO outbox.jsonl: (...) exigiria casar o TEXTO da mensagem
> (...) Registro de intencao precisa de chave estruturada."

Leitura do conjunto (`agenda.py:362-372`) e tolerante a pasta ausente:

```python
try:
    return {caminho.name for caminho in self._pasta.iterdir()}
except OSError:
    return set()
```

### Idioma B — JSON unico com escrita atomica (`tmp` + `os.replace`) (estado corrente mutavel)

`l2scanner/loot.py:260-305` (`designar` / `designacao`). **Este e o analogo mais
proximo de uma marca-dagua**, porque uma marca-dagua e um valor que muda, nao um
fato que acumula.

```python
temporario = self._pasta / f"{_ARQUIVO_PROXIMO}.tmp-{os.getpid()}"
temporario.write_text(
    json.dumps({"nick": nick, "alvo": alvo.isoformat(),
                "designado_em": agora.isoformat()}),
    encoding="utf-8",
)
os.replace(temporario, self._pasta / _ARQUIVO_PROXIMO)
```

Docstring (`loot.py:263-266`): "A escrita e ATOMICA: escreve num tmp com o pid no
nome e `os.replace` por cima. O replace e atomico no Windows no mesmo volume,
entao a outra instancia nunca le um json pela metade; o pid no nome impede uma
instancia de atropelar o tmp da outra."

Arquivo corrompido/truncado (`loot.py:286-305`) — **le tudo dentro de um `try`
com a tupla de excecoes larga, e devolve `None`**:

```python
def designacao(self) -> Designacao | None:
    """A designacao corrente. Ausente, ilegivel ou invalida -> None.

    Leitura defensiva de proposito: a outra instancia pode ter morrido no
    meio de uma escrita, e um arquivo meio-escrito nao pode derrubar o
    laco — o pior aceitavel e perder a designacao, nunca o scanner.
    """
    try:
        bruto = (self._pasta / _ARQUIVO_PROXIMO).read_text(encoding="utf-8")
        dados = json.loads(bruto)
        nick = dados["nick"]
        if not isinstance(nick, str) or not nick:
            return None
        return Designacao(nick=nick, alvo=datetime.fromisoformat(dados["alvo"]), ...)
    except (OSError, ValueError, TypeError, KeyError):
        return None
```

Precedente irmao para nome malformado em disco (`loot.py:227-250`, `registros`):
"Nome malformado e pulado sem levantar: a pasta e compartilhada e duravel, e
qualquer lixo que caia nela nao pode virar excecao no meio do farm."

### Idioma C — JSONL append-only (trilha auditavel, nunca lida de volta pelo programa)

`l2scanner/notificador.py:382-385` (o `outbox.jsonl` da raiz, 68 KB hoje) e
`l2scanner/gravador.py:182` (`observacoes.jsonl`).

```python
if self._outbox:
    registro = {"momento": time.time(), "texto": texto}
    with self._outbox.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
```

Note `ensure_ascii=False` nos dois lugares. O `outbox` e escrito **antes** de
qualquer tentativa de rede (`notificador.py:366`), e a `agenda.py:335`
explicitamente **proibe** deriva-lo como fonte de verdade.

> **Entao o novo codigo deve:** implementar a marca-dagua com o **Idioma B**
> (`loot.py:260-305`): um `.discord/marca-dagua.json` (ou dentro do `.agenda/`)
> com `{"canal_id": "<ultimo_message_id>"}`, escrito em
> `f"marca-dagua.json.tmp-{os.getpid()}"` + `os.replace`, e lido dentro de um
> `try/except (OSError, ValueError, TypeError, KeyError)` que devolve `None`
> ("nunca vi nada") em vez de levantar. Se a semantica virar "esta mensagem
> especifica ja foi processada?" em vez de "ate onde eu li", troque para o
> **Idioma A** (`agenda.py:374`) — marcador vazio por `message_id`, que da a
> protecao contra duas instancias de graca. Use o **Idioma C** so para a trilha
> de auditoria, nunca como fonte da marca-dagua (`agenda.py:335` diz por que).

> **Decisao consciente do planejador:** o Idioma A da imunidade a duas
> instancias, o B nao. O usuario **roda duas instancias** do scanner
> (Yazalaque e Faerlina, `agenda.py:322`). Duas pontes Discord vao existir? Se
> sim, o Idioma A e obrigatorio.

---

## 7. Convencoes de teste

**Analogos:** `tests/test_notificador.py`, `tests/test_agenda.py`,
`tests/conftest.py`

- **Classes agrupando funcoes**, nao funcoes soltas: `class TestTextoDoAlerta:`
  com `def test_...(self)`. `test_agenda.py` tem 131 dessas linhas.
  Nome da classe em CamelCase portugues: `TestAvisosDevidos`,
  `TestAgendaRealDoUsuario`.
- **Nome do teste e uma FRASE afirmando o comportamento**, nao o metodo:
  `test_morte_e_fraseada_para_sobreviver_a_falso_positivo`,
  `test_alerta_sempre_nomeia_o_membro`,
  `test_toml_quebrado_diz_que_e_toml_quebrado`,
  `test_arquivo_ausente_nao_e_erro`.
- **Docstring no teste explicando o custo humano** de a asercao quebrar:

```python
def test_morte_e_fraseada_para_sobreviver_a_falso_positivo(self):
    """"MORREU" nao sobrevive a um erro; "possivel morte" sobrevive.

    O scanner le pixels, nao le a verdade. O texto precisa ser honesto
    sobre isso, senao o primeiro falso positivo destroi a confianca em
    todos os alertas seguintes.
    """
```

- **Docstring de modulo** dizendo por que a suite roda em milissegundos
  (`test_agenda.py:1-7`).
- **Helpers de fabrica no topo do arquivo**, fora das classes
  (`test_agenda.py:32-40`):

```python
def evento(**kwargs) -> EventoAgendado:
    padroes = dict(nome="TvT", horarios=((15, 0),), dias=TODOS_OS_DIAS, ...)
    padroes.update(kwargs)
    return EventoAgendado(**padroes)
```

- **Constante de tempo fixa** no lugar de `datetime.now()`:
  `MOMENTO = 1787583219.0  # 2026-08-24, horario fixo para o texto ser estavel`
  (`test_notificador.py:18`) e `SEGUNDA = datetime(2026, 8, 24)` seguido de
  `assert SEGUNDA.weekday() == 0` (`test_agenda.py:29-30`).
- **Fixtures do pytest usadas: `tmp_path` (muito), `caplog`, `capsys`,
  `monkeypatch`, `@pytest.mark.parametrize`.** O `conftest.py` NAO define
  fixture nenhuma — so um `pytest_configure` que cala o log nativo do OpenCV.
  Nao ha `pytest-asyncio` instalado.
- **Dubles em memoria moram no CODIGO DE PRODUCAO, nao nos testes**:
  `NotificadorEmMemoria` em `l2scanner/notificador.py:209`:

```python
class NotificadorEmMemoria:
    """Para testes: guarda o que seria enviado."""
    def __init__(self) -> None:
        self.enviados: list[str] = []
        self.destinos: list[tuple[str, str | None]] = []
```

  Irmao: `NotificadorDeConsole` (`notificador.py:198`), o modo `--dry-run`.
- **Relogio falsificado por INJECAO, nunca por monkeypatch**
  (`l2scanner/relogio.py:83-88`):

```python
def __init__(self, fonte=None, monotonico=time.monotonic, parede=time.time) -> None:
```

  A docstring do modulo (`relogio.py:25-28`) e a lei: "MESMA DISCIPLINA DE
  `agenda.py`: nao ha relogio proprio escondido aqui. Fonte, monotonico e parede
  entram por parametro, e e por isso que os testes nao precisam de rede nem de
  monkeypatch." Idem `Sessao.tick(frame, momento)` (`sessao.py:187`), que recebe
  o instante.

> **Entao o novo codigo deve:** escrever `tests/test_ponte_discord.py` com
> classes `TestX`, nomes-frase em portugues sem acento, docstrings que dizem o
> custo, `tmp_path` para a marca-dagua, e um `ClienteDiscordEmMemoria` **em
> `l2scanner/ponte_discord.py`** (ao lado de `NotificadorEmMemoria`) que
> entrega mensagens fabricadas. O nucleo da ponte deve ser uma funcao/metodo
> SINCRONO que recebe uma mensagem ja normalizada e devolve estrutura — como
> `Sessao.tick` — para que os testes nunca precisem de `asyncio`.

---

## 8. Idioma de modulo e nomenclatura

**Portugues do Brasil SEM ACENTO** em identificadores — confirmado: zero
`def` com caractere acentuado em todo o `l2scanner/`. Exemplos reais:
`configurar_log`, `desenhar_status`, `ler_membros`, `_recusar_nicks_repetidos`,
`RegistroEmDisco.marcar`, `Despachante`, `ErroDeEntrega`, `CalibracaoInvalida`,
`so_digitos`, `moldurar`, `destacar`, `apelido`.

Em prosa (comentarios e docstrings) o padrao tambem e **sem acento**: 18 dos 22
modulos nao tem um acento sequer. Os 4 que tem (`agenda.py`, `calibrar.py`,
`ocr.py`, `sessao.py`) sao os mais antigos; todo modulo novo
(`calibracao.py`, `presenca.py`, `loot.py`, `gravador.py`, `mercado_visao.py`)
e limpo. **Escreva sem acento.** Excecao: `ENV-EXEMPLO.txt`, que e texto para
o usuario final.

Excecoes: `AgendaInvalida`, `ConfigAusente`, `CalibracaoInvalida`,
`ConfiguracaoPerigosa`, `ErroDeEntrega`, `JanelaNaoEncontrada` — substantivo +
adjetivo, sempre em portugues.

**A voz da casa: a docstring justifica com evidencia medida, e cita horario.**

`notificador.py:256-261`:

```python
"""Sem alvo, vai para as conversas de AVISO. Com alvo, so para ela.

O alvo existe para RESPONDER onde perguntaram. Sem ele, um `.status`
mandado no privado era respondido no grupo — mediu-se isso ao vivo:
pergunta as 23:04:42 na conversa 1, resposta as 23:04:52 na 13.
"""
```

`agenda.py:385-393`: "POR QUE, MEDIDO EM CAMPO. 2026-08-26, 19:30: uma simulacao
(`--so-agenda --dry-run`) rodava ao lado do scanner de verdade (...) O arquivo
foi criado as 19:30:00.629 (...) Foi sorte: tivesse a simulacao ganhado (...) o
lembrete de TvT NUNCA teria sido enviado — sem erro, sem log, sem nada."

`ocr.py:226-230`: "Medido contra `tests/fixtures/manutencao/banner_40min26s.png`
(...) em COR o motor leu `__40nin? es` (...) a MESMA imagem em CINZA leu
`40 minutes`. Nao e ajuste fino — e a diferenca entre acertar e errar por 40
minutos."

`sessao.py:20-34`: a docstring de modulo LISTA os tres bugs que a refatoracao
deixou passar, numerados.

Traços marcantes: **MAIUSCULAS para a afirmacao central** ("ARQUIVO AUSENTE NAO
E ERRO", "A DECISAO MORA AQUI, E NAO NOS CHAMADORES"); secoes separadas por
`# ---...---`; comentario explicando por que uma alternativa obvia foi
REJEITADA ("POR QUE NAO DERIVAR DO outbox.jsonl"); e citacao do requisito por
codigo (`CAPT-07`, `AGEN-06`, `MUTE-08`, `D-12`, `WR-08`).

> **Entao o novo codigo deve:** nomear tudo em portugues sem acento
> (`PonteDiscord`, `MarcaDagua`, `ler_marca_dagua`, `PonteInvalida`,
> `ClienteEmMemoria`), abrir cada modulo com uma docstring que diz por que ele
> existe, e justificar cada decisao nao-obvia com o modo de falha concreto que
> ela evita — citando `CONF-03`, `OPER-02`, `OPER-03`, `ENTR-04` como o codigo
> ja cita `AGEN-06`.

---

## 9. SEM ANALOGO: o laco async e o cliente Discord

**Nao ha analogo de servico async neste repo.** O unico `async` existente e
`l2scanner/ocr.py:259` (`_reconhecer_async`), e ele e o oposto do que a ponte
precisa: uma corrotina de vida curta escondida atras de um `asyncio.run()`
sincrono (`ocr.py:256`), chamada de dentro do laco sincrono.

```python
return asyncio.run(_reconhecer_async(codificado.tobytes()))
```

Todo o resto da concorrencia do projeto e **`threading` com daemon + `Queue`**:

- `notificador.py:353-358` — `Despachante`: `threading.Thread(target=self._laco,
  name="despachante", daemon=True)` + `Queue(maxsize=200)`.
- `relogio.py:125-142` — `iniciar_sincronizacao_periodica`, thread daemon com
  `while True: time.sleep(intervalo)`.

A razao escrita (`relogio.py:131-133`): "Daemon e separada pela mesma razao pela
qual o `Despachante` existe: o laco de captura NUNCA pode bloquear em rede. E
daemon para que um Ctrl+C encerre o scanner na hora."

E todo HTTP e **`urllib.request` stdlib** (`notificador.py:284-302`,
`relogio.py:197-207`), com `add_header` a mao e `except (urllib.error.URLError,
TimeoutError, OSError)`. Nao ha `requests` no `requirements.txt`.

> **DECISAO QUE O PLANEJADOR TEM QUE TOMAR CONSCIENTEMENTE.** A ponte Discord e
> o primeiro processo genuinamente async do repo. Nao force o padrao `Despachante`
> sobre ela; um gateway WebSocket e event-driven por natureza. Mas:
>
> 1. **Fronteira async/sync.** O precedente do `ocr.py` e "o async fica na
>    beirada; o miolo e sincrono e testavel". Aplique: `async def on_message` so
>    normaliza e chama um metodo sincrono `receber(mensagem) -> Resultado` no
>    estilo `Sessao.tick` (`sessao.py:187`). Isso mantem os testes sem
>    `pytest-asyncio` (que nao esta instalado e teria que entrar no
>    `requirements.txt`).
> 2. **Dependencia nova.** `discord.py` seria a primeira dependencia de rede do
>    projeto — hoje ate o cliente HTTP e stdlib. Justifique explicitamente, ou
>    avalie o gateway sobre `websockets`.
> 3. **Retentativa/reconexao.** O analogo mais proximo e a distincao transitorio
>    vs definitivo de `ErroDeEntrega` (`notificador.py:241-247`,
>    `notificador.py:296-302`): 4xx nao se repete, 5xx e 429 sim. Reuse esse
>    vocabulario para a reconexao do gateway em vez de inventar outro.
> 4. **Encerramento.** Todos os `.bat` fecham com "Feche com Ctrl+C ou no X" —
>    a ponte precisa de um `KeyboardInterrupt` limpo que grave a marca-dagua
>    antes de sair.

---

## Padroes compartilhados (aplicam a todos os arquivos novos)

### Constantes de caminho
**Fonte:** `l2scanner/__main__.py:107-114` e `l2scanner/config.py:32-33`
```python
RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_CALIBRACAO = RAIZ / "calibration.json"
PASTA_LOGS = RAIZ / "logs"
PASTA_AGENDA = RAIZ / ".agenda"
```
Sempre `Path`, sempre ancorado em `RAIZ`, nunca caminho relativo ao cwd.
Toda funcao que le arquivo aceita `caminho: Path | None = None` e cai no
default — e o que torna os testes com `tmp_path` possiveis (`config.py:40`,
`config.py:141`).

### `from __future__ import annotations`
Primeira linha de codigo de **todo** modulo e **todo** teste. Sem excecao.

### Ordem de import
stdlib, linha em branco, terceiros, linha em branco, `from .modulo import ...`
relativo dentro do pacote (`config.py:9-28`).

### Fail-loud no arranque, fail-soft no laco
Regra escrita em `calibracao.py:429-432` ("Falhar alto aqui e muito melhor do
que medir a regiao errada calado") e em `loot.py:289-291` ("um arquivo
meio-escrito nao pode derrubar o laco — o pior aceitavel e perder a designacao,
nunca o scanner"). No arranque: levante e `return 2`. Em regime: engula, logue,
siga.

---

## Metadados

**Escopo da busca:** `l2scanner/` (22 modulos), `tests/` (29 arquivos), raiz
(5 `.bat`, `requirements.txt`, `config.toml`, `ENV-EXEMPLO.txt`, `outbox.jsonl`),
`tools/`
**Arquivos lidos na integra:** `config.py`, `console.py`, `sessao.py`,
`relogio.py`, `conftest.py`, os 4 `.bat`, `ENV-EXEMPLO.txt`
**Arquivos lidos em trechos dirigidos:** `__main__.py`, `agenda.py`, `loot.py`,
`notificador.py`, `calibracao.py`, `ocr.py`, `test_notificador.py`,
`test_agenda.py`
**Data:** 2026-08-28
