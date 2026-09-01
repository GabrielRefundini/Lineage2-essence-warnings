# Phase 03: Persistência de observações - Pattern Map

**Mapped:** 2026-08-30
**Files analyzed:** 4 (2 novos, 2 modificados)
**Analogs found:** 4 / 4 (todos com analog no repositório)

> A RESEARCH já nomeou `mercado_catalogo.py` como precedente literal. Este documento **não
> repete** isso — ele fecha as cinco lacunas que a pesquisa deixou apontadas mas não resolveu:
> o padrão de montagem, o relógio, o padrão de teste de disco, os campos exatos dos dataclasses
> e o `.gitignore`.

## File Classification

| Novo/Modificado | Papel | Fluxo de dados | Analog mais próximo | Qualidade |
|---|---|---|---|---|
| `l2scanner/mercado_registro.py` (NOVO) | model + service (duas metades) | file-I/O append-only + CRUD em memória | `l2scanner/mercado_catalogo.py` | **exact** (mesma pasta, mesmo `;`, mesmo `csv`) |
| `l2scanner/__main__.py` → `montar_registro_de_mercado` (MODIFICADO) | montagem / factory | request-response (tenta → degrada → `None`) | `montar_gravador` (`__main__.py:227-262`) | **exact** |
| `tests/test_mercado_registro.py` (NOVO) | test | file-I/O sobre `tmp_path` | `tests/test_mercado_catalogo.py:504-800` + `tests/test_gravador_honesto.py:478-501` | **exact** (dois analogs, um por metade) |
| `.mercado/LEIAME.txt` (NOVO, escrito uma vez) | doc/artefato | file-I/O write-once | — | **sem analog** |

---

## 1. O padrão de MONTAGEM que falha para o lado certo (é o `PERS-03` inteiro)

A pesquisa acertou: **`Catalogo.__init__` é o anti-padrão**, e `montar_gravador` é a correção
que a casa já escreveu. Lado a lado:

### O anti-padrão — `l2scanner/mercado_catalogo.py:426-434`

```python
    def __init__(self, pasta: Path) -> None:
        # A pasta chega no construtor, e nao derivada aqui dentro, pelo mesmo
        # motivo de `RegistroDeLoot.__init__`: e o que permite ao teste apontar
        # para `tmp_path` sem nunca tocar a `.mercado/` do usuario, que e dado
        # acumulado e sem desfazer. Producao passa `PASTA_DO_MERCADO`.
        self._pasta = pasta
        self._pasta.mkdir(parents=True, exist_ok=True)   # <-- LEVANTA, fora de try
        self.series: dict[str, SerieDeNome] = {}
        self.carregar()                                  # <-- este SIM tem try dentro
```

Duas metades com doutrinas opostas no mesmo construtor: `carregar()` é defensivo por dentro
(`mercado_catalogo.py:460-472`, `FileNotFoundError` → vazio, `OSError` → aviso e vazio), mas o
`mkdir` da linha acima **não tem rede nenhuma**. `FileExistsError` (errno 17, winerror 183) sobe
cru. `Catalogo` sobrevive a isso hoje só porque **não tem instanciador de produção** — só testes
e `tools/`.

### O padrão da casa — `l2scanner/__main__.py:227-262`

```python
def montar_gravador(args, fonte) -> Gravador | None:
    """Monta o gravador, ou explica por que nao montou. Nunca levanta.

    Mesmo trilho de `montar_despachante` e `montar_vigia_de_manutencao`: tenta,
    degrada com log, devolve None e deixa o scanner subir. O recurso e
    opcional; o scanner nao e.

    `Gravador.__init__` faz `mkdir` e `open`, e era construido fora de qualquer
    try. `main()` so pega `JanelaNaoEncontrada` e `ConfiguracaoPerigosa`, entao
    um `recordings/` somente-leitura, um disco cheio, um caminho travado pelo
    antivirus ou um arquivo ocupando o nome `recordings` derrubavam o scanner
    inteiro com um traceback cru. Gravar e a feature mais opcional do projeto e
    era a unica capaz de impedir o produto de subir.

    ERROR e nao WARNING de proposito: quem esta seguindo o ROTEIRO-SPIKE.md
    precisa abortar e consertar, nao farmar 60 segundos gravando em lugar
    nenhum.
    """
    if not args.record:
        return None
    ...
    try:
        gravador = Gravador(
            PASTA_GRAVACOES, args.rotulo, fonte_completa=fonte_completa
        )
    except OSError as erro:
        log.error("GRAVACAO DESATIVADA — nao consegui criar a pasta: %s", erro)
        log.error(
            "Todo o resto do scanner continua igual: morte, saida e "
            "ressurreicao seguem sendo detectadas e entregues."
        )
        return None
```

### O veredito, em cinco regras que o planejador copia

O padrão da casa para uma função de montagem que pode falhar é:

1. **A montagem envolve o construtor inteiro num `try`**, não o construtor se defende. O
   construtor pode ser ingênuo — o que não pode é ser chamado nu.
2. **`except OSError`, e só.** Cobre os quatro modos medidos na § Lacuna 5 da pesquisa
   (`PermissionError` 13, `FileNotFoundError` 2, diretório-ocupando-nome 13, `FileExistsError` 17).
3. **`log.error`, não `log.warning`** — precedente explícito na docstring acima. `warning` é para
   linha descartada (`mercado_catalogo.py:498-506`); `error` é para feature desligada.
4. **DUAS mensagens de erro, e a segunda diz o que CONTINUA funcionando.** `"Todo o resto do
   scanner continua igual: morte, saida e ressurreicao seguem sendo detectadas e entregues."`
   é literalmente o `PERS-03` já escrito uma vez. A frase-irmã em `montar_despachante`
   (`__main__.py:216-218`) é `"O scanner continua util no console."`.
5. **`return None`, nunca `raise`.** A assinatura é `-> X | None` e o chamador (Fase 4) trata
   `None` como "feature off".

Nota de fiação: `montar_gravador` tem um portão de curto-circuito na entrada
(`if not args.record: return None`, `:255-256`). `montar_registro_de_mercado` não tem flag hoje
— a flag `--mercado` é DETC-02, Fase 4. A função nasce sem chamador (Armadilha 5 da pesquisa).

---

## 2. Onde mora o carimbo de tempo ancorado

**Arquivo:** `l2scanner/relogio.py`. **Classe:** `Relogio`. **Método:** `agora()`, linha **156**.

```python
# l2scanner/relogio.py:146-163
    def agora_epoch(self) -> float:
        if self._ancora_epoch is None:
            # Sem ancora a hora E a do Windows, defeito e tudo. O arranque
            # avisa em WARNING justamente porque este caminho e o honesto,
            # nao o bom.
            return self._parede()
        # ESTA LINHA E A CORRECAO: o avanco vem do monotonico, entao um pulo
        # de 3h no relogio do Windows nao move a hora que a agenda usa.
        return self._ancora_epoch + (self._monotonico() - self._ancora_mono)

    def agora(self) -> datetime:
        """Datetime ingenuo, hora local, de proposito.

        A agenda inteira trabalha com datetime ingenuo, e o fuso do Windows
        continua correto mesmo quando o relogio nao esta — o dual boot estraga
        o RELOGIO, nao a configuracao de fuso.
        """
        return datetime.fromtimestamp(self.agora_epoch())
```

**Assinatura:** `Relogio.agora(self) -> datetime` — **datetime ingênuo (naive), hora local**. Sem
`tzinfo`. Isso importa para a coluna: `.isoformat()` sai `2026-08-30T21:15:00`, sem offset — e
`datetime.fromisoformat` na leitura o remonta igual. É o mesmo formato que
`mercado_catalogo.py:609-610` já grava e `:518-519` já lê.

**Chamador real** — `l2scanner/__main__.py:1225-1229`:

```python
    # Processo SEPARADO do scanner, entao monta o proprio relogio: com o
    # relogio do Windows adiantado, --cancelar-silencio escolheria a
    # ocorrencia errada e calaria justamente a que o usuario queria ouvir.
    relogio = montar_relogio(args)
    agora = relogio.agora()
```

O relógio é montado por `montar_relogio(args, fonte=None) -> Relogio` (`__main__.py:481`) —
note que ele retorna `Relogio`, **nunca `None`**: o relógio não é feature opcional. Outros
chamadores reais em `__main__.py:1466, 1468, 1471, 1583, 1608, 1933, 1956, 2056`.

**A regra da fronteira** (`mercado_catalogo.py:542-544`, o precedente que a pesquisa cita): o
`Relogio` **não entra no `RegistroDeObservacoes`**. Entra o `datetime`, por parâmetro:

```python
    def registrar(
        self, chave: str | None, nome_exibido: str, agora: datetime
    ) -> SerieDeNome | None:
```

Por quê: `relogio.py:1-13` explica que o PC é dual boot e o Windows fica ~3h adiantado. Se o
registro chamasse `Relogio` por dentro, o teste precisaria de monkeypatch. Com `agora: datetime`
por parâmetro, o teste passa `datetime(2026, 8, 30, 21, 15, 0)` e pronto — que é exatamente o
que `tests/test_mercado_catalogo.py:513-514` faz com as constantes `AGORA` e `DEPOIS`.

---

## 3. Como os testes desta casa provam ESCRITA EM DISCO

Há **dois padrões distintos**, um por metade, e o plano precisa dos dois.

### 3a. Metade de disco → `tmp_path`, pasta pelo construtor

**Analog:** `tests/test_mercado_catalogo.py:504-545`. O comentário-régua no topo é a doutrina:

```python
# tests/test_mercado_catalogo.py:504-514
# ===========================================================================
# A METADE DE ARQUIVO (02-05): o catalogo duravel em `.mercado/`
# ===========================================================================
#
# Nada aqui toca a `.mercado/` REAL. Toda instancia recebe `tmp_path`, pelo
# mesmo motivo de `RegistroDeLoot` receber a pasta no construtor em vez de
# derivar uma: um teste que escrevesse na pasta de producao contaminaria a
# estatistica do usuario, que e dado ACUMULADO e sem poda — nao ha desfazer.

AGORA = datetime(2026, 8, 30, 21, 15, 0)
DEPOIS = datetime(2026, 8, 31, 9, 0, 0)
```

Helper de leitura crua — copiar tal e qual (`:521-522`):

```python
def _linhas_cruas(pasta: Path) -> list[str]:
    return (pasta / ARQUIVO_DO_CATALOGO).read_text(encoding="utf-8").splitlines()
```

Helper de escrita de arquivo corrompido, para os testes de leitura defensiva (`:713-718`):

```python
    def _escrever(self, tmp_path: Path, corpo: str) -> Path:
        pasta = tmp_path / ".mercado"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / ARQUIVO_DO_CATALOGO).write_text(corpo, encoding="utf-8")
        return pasta
```

Forma do teste de linha truncada, com `caplog` conferindo que o aviso **nomeia a linha**
(`:719-737`):

```python
        with caplog.at_level("WARNING", logger="l2scanner.mercado_catalogo"):
            catalogo = Catalogo(pasta)
        assert set(catalogo.series) == {"a#0", "b#0"}
        assert catalogo.series["b#0"].avistamentos == 5
        assert "c#0" in caplog.text
        assert "linha 4" in caplog.text
```

Para esta fase o logger vira `logger="l2scanner.mercado_registro"`.

### 3b. Metade de montagem → `monkeypatch.setattr` da CONSTANTE de caminho

**Analog:** `tests/test_gravador_honesto.py:478-501`. Este é o padrão para testar
`montar_registro_de_mercado`, porque a montagem lê a constante do módulo, não recebe pasta:

```python
def test_um_recordings_que_nao_da_para_criar_nao_derruba_o_scanner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Um ARQUIVO ocupando o nome `recordings` — falha deterministica em todo SO.

    Mesmo padrao do diretorio-com-nome-de-PNG usado acima: nao depende de
    permissao, que varia entre maquinas.
    """
    import l2scanner.__main__ as principal

    ocupado = tmp_path / "recordings"
    ocupado.write_text("nao sou uma pasta", encoding="utf-8")
    monkeypatch.setattr(principal, "PASTA_GRAVACOES", ocupado)

    with caplog.at_level(logging.ERROR, logger="l2scanner.__main__"):
        gravador = montar_gravador(_ArgsDeGravacao(), fonte=None)

    assert gravador is None, "a gravacao desliga; o scanner segue"
    erros = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert erros, "sair calado faria o usuario farmar 60 segundos para nada"
    assert any("GRAVACAO DESATIVADA" in r.getMessage() for r in erros)
    assert any(
        "continua igual" in r.getMessage() for r in erros
    ), "o log precisa dizer que morte, saida e ressurreicao seguem valendo"
```

Três coisas para copiar literalmente:
- `import l2scanner.__main__ as principal` **dentro** da função, e `monkeypatch.setattr` sobre o
  nome **importado no `__main__`**, não sobre o módulo de origem.
- **Nome-ocupado-por-arquivo** como forma de falha, com a justificativa por escrito: *"nao depende
  de permissao, que varia entre maquinas"*. Casa exatamente com a Armadilha 6 da pesquisa
  (`os.chmod(pasta, S_IREAD)` não faz nada no Windows).
- **Assert no conteúdo da mensagem**, não só no nível — inclusive na segunda frase
  (`"continua igual"`), que é o `PERS-03` sendo testado como texto.

### 3c. Portão de digest? **NÃO EXISTE precedente.**

Varri `tests/` inteiro: a única ocorrência de `sha256`/`digest` é
`tests/test_mercado_pagina.py:689`, e é uma **medição de performance**, não um portão:

```python
        """MEDIDO: `np.array_equal` 0,89 ms contra sha256 3,70 e blake2b 6,81.
```

**Não há, neste repositório, nenhum teste que tire digest do arquivo real do usuário para provar
que não o tocou.** A garantia é **estrutural, não verificada**: a pasta chega pelo construtor
(`mercado_catalogo.py:426-430`) ou pela constante monkeypatchada
(`test_gravador_honesto.py:492`), e nenhum caminho de teste consegue chegar em `PASTA_DO_MERCADO`.
Recomendação ao planejador: **manter a garantia estrutural** — é o padrão da casa — e, se quiser
uma rede a mais, um teste barato do tipo *"o construtor com `tmp_path` não cria nada em
`config.RAIZ / '.mercado'`"*. Não inventar portão de digest sem precedente.

---

## 4. Os dataclasses que atravessam a fronteira — campos exatos

### `LinhaLida` — `l2scanner/mercado_leitura.py:1156-1162`

```python
    indice: int
    chave_da_serie: str
    nome_exibido: str
    total_em_centesimos: int
    quantidade: int
    serie_nova: bool
    residuo_do_cruzamento: int | None
```

**Respondendo item a item ao que foi perguntado:**

| O que o CONTEXT chama de… | O campo REAL, hoje | Tipo |
|---|---|---|
| o total | `total_em_centesimos` | `int` (nunca float) |
| a quantidade | `quantidade` | `int` |
| a chave da série | `chave_da_serie` | `str` |
| o nome legível | `nome_exibido` | `str` |
| o resíduo do cruzamento | `residuo_do_cruzamento` | **`int \| None`** |

Dois avisos que o planejador **não pode** perder:

- **`residuo_do_cruzamento` é `int | None`**, e o `None` é o caso normal — a docstring
  (`:1145-1149`) diz: *"`|total - unitario x quantidade|` em centesimos, ou `None` quando alguma
  das tres celulas nao leu"*. A coluna do CSV tem de ter uma representação de "não medido" que
  volte como `None` no `fromisoformat`-equivalente. Campo vazio (`""`) é o candidato natural, e o
  `csv.reader` o devolve como `''` — distinguível de `'0'`, que significa "conferi e bateu".
- **`indice` e `serie_nova` NÃO vão para o CSV.** `indice` é posição na grade daquele frame (é
  artefato de tela, mesma família do "frame 78" que o CONTEXT proíbe); `serie_nova` é sinal de
  console para a Fase 4. Nenhum dos dois é decisão travada, mas os dois cairiam no critério
  *"nada de gravação ou frame"*.
- **Não existe campo de unitário.** A docstring `:1137-1143` é explícita: *"O UNITARIO EXIBIDO NAO
  ESTA AQUI, E NUNCA VAI ESTAR."* Não há o que a Fase 3 possa gravar por acidente.

### `PaginaAceita` — `l2scanner/mercado_pagina.py:182-187`

```python
@dataclass
class PaginaAceita:
    """Uma pagina que DOIS frames consecutivos afirmaram igual."""

    linhas: tuple[LinhaLida, ...]
    descartadas: tuple[int, ...] = ()
    motivos: tuple[str, ...] = ()
```

Três campos, e **só `linhas` é consumido por esta fase**. `descartadas` e `motivos` são proibidos
no CSV pela D-17 da Fase 2, reescrita em `mercado_leitura.py:1174-1176`:

```python
    NADA disto vai para o CSV (D-17): escrever a linha recusada misturaria
    descarte com dado, que e a confusao que a falha fechada existe para evitar.
```

### Contrato lateral: `chave_da_serie` pode ser `None` na origem

`mercado_catalogo.py:175-186`:

```python
def chave_da_serie(nome: str | None, assinatura: str) -> str | None:
    """A identidade estavel da serie, ou `None` quando nao ha nome.
    ...
    `None` para nome vazio, so espaco, ou `None`. Uma leitura vazia nunca produz
    chave nem serie — e nao produzir e diferente de produzir uma chave vazia,
    que iria para o CSV e a Fase 3 referenciaria como se fosse item.
    """
```

A última frase **nomeia esta fase**. O campo `LinhaLida.chave_da_serie` é declarado `str` (não
`str | None`), o que significa que a Fase 2 já filtrou — mas a Fase 3 é a destinatária do aviso, e
a leitura de arranque tem de recusar chave vazia, exatamente como
`mercado_catalogo.py:512-515` faz (`if not chave: recusar("chave vazia")`).

---

## 5. O `.gitignore` e o `.mercado/`

**Linha exata: `.gitignore:38`.** Com o comentário que a Fase 2 escreveu, `:34-38`:

```
# .mercado/ guarda o catalogo de nomes do World Exchange — pelo mesmo motivo
# do .loot/: estado local, DURAVEL e sem poda, porque estatistica de item e
# para sempre. Versionar misturaria o que duas maquinas viram na tela, e
# nenhuma das duas saberia dizer qual metade e sua.
.mercado/
```

**Veredito: o arquivo novo JÁ ESTÁ COBERTO. Nenhuma entrada nova é necessária.** O padrão é
`.mercado/` com barra final — um **ignore de diretório**, que cobre recursivamente todo o
conteúdo. `observacoes.csv`, `LEIAME.txt` e qualquer temporário caem dentro dele sem tocar no
arquivo.

**Uma ressalva de precisão para o plano:** o comentário atual diz *"guarda o catalogo de nomes"* —
singular, e agora incompleto. A pasta passa a ter dois arquivos com donos distintos. Estender o
comentário para citar as observações é edição de uma linha e mantém a doutrina da casa (*"um
número que caiu precisa dizer que caiu"*). Não é obrigatório e não muda comportamento.

---

## Shared Patterns

### Constantes de contrato no topo da metade de arquivo
**Fonte:** `l2scanner/mercado_catalogo.py:369-383` — **aplicar a:** `mercado_registro.py`

```python
# `.mercado/` e o TERCEIRO diretorio-ponto de estado local duravel deste
# repositorio, ao lado de `.loot/` e `.agenda/` ... O caminho vem SEMPRE da
# RAIZ do projeto e NUNCA de entrada do usuario — um caminho vindo de fora
# seria uma travessia de diretorio de graca, e nada aqui precisa dessa
# liberdade.
PASTA_DO_MERCADO = RAIZ / ".mercado"
ARQUIVO_DO_CATALOGO = "catalogo-de-nomes.csv"

# PONTO-E-VIRGULA, E NAO VIRGULA, e a escolha vale por dois: a Fase 3 herda
# este dialeto. A decisao travada da exibicao usa VIRGULA DECIMAL (`62,00`), e
# um CSV separado por virgula colapsaria a planilha inteira numa coluna so no
# instante em que o usuario abrisse o arquivo no Sheets.
SEPARADOR = ";"

COLUNAS = ("chave", "nome_exibido", "primeira_vez", "ultima_vez", "avistamentos")
```

O comentário do `SEPARADOR` **fala com esta fase por nome** (*"a Fase 3 herda este dialeto"*).
Decisão de fiação para o planejador: **importar `PASTA_DO_MERCADO` e `SEPARADOR` de
`mercado_catalogo`** (não redefinir — duas definições do mesmo `;` é como elas divergem), e
declarar em `mercado_registro.py` só o que é próprio: `ARQUIVO_DE_OBSERVACOES` e o `COLUNAS`
desta fase.

### O aviso que NOMEIA a linha ruim
**Fonte:** `l2scanner/mercado_catalogo.py:488-506` — **aplicar a:** toda leitura de arranque

```python
        def recusar(motivo: str) -> None:
            log.warning(
                "Catalogo de nomes, linha %d DESCARTADA (%s): %r. As demais "
                "linhas do arquivo carregaram normalmente — uma linha ruim "
                "nunca condena o arquivo inteiro.",
                numero,
                motivo,
                SEPARADOR.join(campos),
            )
```

Três invariantes: `%d` do número da linha (vem de `enumerate(..., start=1)`,
`mercado_catalogo.py:474`), o motivo em texto, e o **conteúdo cru** em `%r`. A segunda frase é a
promessa de que o arquivo não foi condenado — e o teste a confere por substring.

### Leitura defensiva com três saídas distintas
**Fonte:** `l2scanner/mercado_catalogo.py:459-472` — **aplicar a:** `RegistroDeObservacoes.carregar`

```python
        self.series = {}
        try:
            with self.arquivo.open("r", encoding="utf-8", newline="") as fonte:
                linhas = list(csv.reader(fonte, delimiter=SEPARADOR))
        except FileNotFoundError:
            return self.series
        except OSError as erro:
            log.warning(
                "Nao consegui ler o catalogo de nomes em %s (%s). A leitura "
                "segue com o catalogo VAZIO desta sessao; o arquivo em disco "
                "nao foi tocado.",
                self.arquivo,
                erro,
            )
            return self.series
```

`FileNotFoundError` **antes** de `OSError` e **calado** — primeira execução é estado legítimo.
`OSError` avisa e a frase promete *"o arquivo em disco nao foi tocado"*.

**⚠️ Aqui esta fase DIVERGE, e a divergência é travada:** o CONTEXT manda o `OSError` de leitura
**DESLIGAR ALTO** (`log.error` + feature off), não seguir com índice vazio. Seguir vazio faria a
dedup falhar e reescrever tudo que já está no disco. É a segunda divergência estrutural com o
analog, ao lado do `"a"` vs `"w"`.

### O cabeçalho — INVERTER o analog
**Fonte:** `l2scanner/mercado_catalogo.py:476-481`

```python
            if numero == 1 and tuple(campo.strip() for campo in campos) == COLUNAS:
                # O cabecalho. Ele e conveniencia para o olho humano, nao a
                # identidade do arquivo — um arquivo sem ele ainda carrega.
                continue
```

**NÃO copiar — inverter.** Lá o cabeçalho é conveniência; aqui é contrato. Os três estados que o
CONTEXT trava: (a) arquivo ausente → cria com cabeçalho; (b) cabeçalho idêntico a `COLUNAS` →
segue; (c) divergente **ou ausente num arquivo não-vazio** → `log.error` + feature off. A
comparação usa a mesma forma (`tuple(campo.strip() for campo in campos) == COLUNAS`), só o `else`
muda.

### Escrita — a forma, com a única linha que não se transporta
**Fonte:** `l2scanner/mercado_catalogo.py:598-613`

```python
        temporario = self._pasta / f"{ARQUIVO_DO_CATALOGO}.tmp-{os.getpid()}"
        with temporario.open("w", encoding="utf-8", newline="") as destino:
            escritor = csv.writer(destino, delimiter=SEPARADOR)
            escritor.writerow(COLUNAS)
            ...
        os.replace(temporario, self.arquivo)
```

Copiar: `encoding="utf-8"`, `newline=""`, `csv.writer(..., delimiter=SEPARADOR)`, `.isoformat()`
nas datas. **Não** copiar: o temporário, o `"w"` e o `os.replace`. A justificativa do `"w"` está
escrita no fonte (`:592-596`) e é *"porque o destino aqui e o TEMPORARIO"* — some junto com ele.

### `flush()` sem `fsync`, e o precedente já existe
**Fonte:** `l2scanner/gravador.py:181-192` — **aplicar a:** `RegistroDeObservacoes.registrar`

```python
        try:
            self._arquivo_meta.write(json.dumps(linha, ensure_ascii=False) + "\n")
            self._arquivo_meta.flush()  # sobrevive a um Ctrl+C ou queda de energia
        except Exception:  # noqa: BLE001
```

O append-com-flush-e-nunca-levantar já é padrão da casa para arquivo de linha por evento. A
docstring de `Gravador.gravar` (`:140-150`) é o `PERS-03` em outras palavras: *"uma excecao aqui
derrubaria o scanner inteiro por causa de disco cheio, levando os alertas de morte da party
junto. A doutrina da casa e degradar a feature, nunca o produto."*

Duas diferenças desta fase: (1) o `Gravador` mantém a alça aberta a sessão toda; a pesquisa mediu
que **abrir/fechar por linha** custa 0,1295 ms e ganha o critério 5 — divergir aqui é
justificado por medição. (2) `except Exception` é largo demais; a pesquisa mediu que os quatro
modos são `OSError`.

---

## No Analog Found

| Arquivo | Papel | Fluxo | Motivo |
|---|---|---|---|
| `.mercado/LEIAME.txt` | doc write-once | file-I/O | Nenhum artefato deste repositório escreve documentação ao lado do dado. `.loot/` e `.agenda/` não têm LEIAME. É invenção desta fase (§ Lacuna 1, saída (c), da pesquisa) — o planejador escreve do zero, sem padrão a seguir. |
| A rede "termina em newline" | validação | file-I/O | `Catalogo` grava por `os.replace` atômico e **não pode** truncar, então nunca precisou dessa rede. É a única lógica genuinamente nova da leitura, e a pesquisa já a mediu (5 de 5 cortes). |

## Metadata

**Escopo da busca:** `l2scanner/` (todos os `.py`), `tests/` (todos os `.py`), `.gitignore`
**Arquivos lidos nesta sessão:** `mercado_catalogo.py` (trechos :175-187, :364-445, :445-487,
:488-545, :590-620), `mercado_leitura.py:1131-1181`, `mercado_pagina.py:182-227`,
`relogio.py:1-13,140-175`, `gravador.py:140-200`, `__main__.py:185-265,1225-1233`,
`tests/test_mercado_catalogo.py:500-545,705-760`, `tests/test_gravador_honesto.py:478-530`,
`.gitignore:28-42`
**Data:** 2026-08-30
