# Phase 10: Lista de presenca do Solo Boss pelo WhatsApp - Pattern Map

**Mapped:** 2026-08-26
**Files analyzed:** 7 (6 modificados + 1 novo de teste, no minimo)
**Analogs found:** 7 / 7 (nenhum arquivo desta fase e uma categoria nova no projeto)

Nao houve RESEARCH.md nesta fase de proposito: o codigo existente E a fonte da
verdade. Tudo abaixo e codigo real, com caminho e numero de linha.

---

## File Classification

| Arquivo (novo/modificado) | Papel | Fluxo de dados | Analogo mais proximo | Qualidade |
|---|---|---|---|---|
| `l2scanner/agenda.py` (mod) — `TipoDeAviso.CHAMADA`, `chamar_minutos_antes`, prefixo `presenca_`, API de lista | model + registro em disco | event-driven + file-I/O | ele mesmo: `TipoDeAviso.ANTES/AGORA` (l.70-73), `avisar_no_horario` (l.90), `RegistroEmDisco.marcar` (l.292), `PREFIXO_CANCELADO`/`cancelar`/`cancelados` (l.243, 311-326) | exact |
| `l2scanner/comandos.py` (mod) — `Comando.JOIN`/`LEAVE`, `_VOCABULARIO`, `_AJUDA`, autorizacao de 2o nivel | controller (parser) | request-response | `Comando.SOLO`/`PARTY` + `_VOCABULARIO` (l.79-83, 128-137) e `autor_autorizado` (l.~665) | exact |
| `l2scanner/config.py` (mod) — `[[membro]]` e `chamar_minutos_antes` | config | file-I/O / transform | `ler_agenda` + `_evento_de_dict` (l.127-228) e o bloco de `conversas_de_comando` em `config_do_chatwoot` (l.78-105) | exact |
| `l2scanner/loot.py` (mod) — le a lista fechada e sugere a vez | service | CRUD sobre disco | `responder_designacao` (l.802-838) + `nicks_conhecidos` (l.518) | exact |
| `l2scanner/sessao.py` (mod) — fechamento da lista no horario do boss | service (orquestrador do tick) | event-driven | `_processar_agenda` -> `self.loot.consumir(agora)` (l.245-282) | exact |
| `l2scanner/__main__.py` (mod) — ramos `.join`/`.leave` no despacho de comandos | controller | request-response | ramo `Comando.LOOT_DESIGNAR` (l.589-600) e o eco `avisar_o_grupo` (l.655-668) | exact |
| `tests/test_presenca.py` (novo) ou blocos nos testes existentes | test | — | `tests/test_loot.py::TestCorridaDeDuasInstancias` (l.87) e `tests/test_agenda.py::TestRegistroEmDisco` (l.426) | exact |

Decisao de arquivo aberta ao planejador: a lista de presenca pode nascer como
uma classe dentro de `agenda.py` (o `.agenda/` e dela) ou como
`l2scanner/presenca.py` novo. **Se nascer arquivo novo, ele NAO pode importar
`comandos` nem `sessao`** — mesma regra escrita no fim da docstring de
`loot.py` (l.27-28). E se o `loot.py` for ler a lista, o modulo da lista tem
que estar ABAIXO do `loot` na direcao da dependencia (ou a leitura acontece na
borda, em `__main__.py`, e chega no `loot` como parametro).

---

## Pattern Assignments

### `l2scanner/agenda.py` — o terceiro `TipoDeAviso` (model, event-driven)

**Analogo:** o proprio arquivo. O enum e de dois valores hoje
(`l2scanner/agenda.py:70-73`):

```python
class TipoDeAviso(Enum):
    ANTES = "antes"
    AGORA = "agora"
```

**Padrao do campo opt-in por evento** — copiar literalmente a forma de
`avisar_no_horario`, incluindo o comentario que explica POR QUE o campo existe
com medida de campo (`agenda.py:84-95`):

```python
    # Mandar tambem o aviso NO horario, alem do de antecedencia.
    #
    # Existe porque nem todo evento merece dois avisos. Um Solo Boss de duas em
    # duas horas sao 12 ocorrencias por dia; com dois avisos cada, viram 24
    # mensagens no grupo — mais do que TvT e Prime somados, tres vezes. Para
    # esses, o lembrete de antecedencia basta: quem ia, ja se preparou.
    avisar_no_horario: bool = True
```

O `chamar_minutos_antes: int = 0` entra ao lado, com `0` significando
"desligado" — o mesmo idioma de `silenciar_minutos: int = 0` (l.95), cujo
"desligado" ja e testado por `silencio_ativo` em `if evento.silenciar_minutos
<= 0: continue` (l.405-406).

**Padrao do candidato + guarda de opt-in** (`agenda.py:163-176`) — a chamada
entra como TERCEIRO item da lista `candidatos`, com uma guarda irma da do
`AGORA`:

```python
                candidatos = [
                    (
                        TipoDeAviso.ANTES,
                        alvo - timedelta(minutes=evento.avisar_minutos_antes),
                    ),
                    (TipoDeAviso.AGORA, alvo),
                ]
                for tipo, devido_em in candidatos:
                    if tipo is TipoDeAviso.AGORA and not evento.avisar_no_horario:
                        continue
                    if evento.avisar_minutos_antes <= 0 and tipo is TipoDeAviso.ANTES:
                        # Antecedencia zero: o aviso "antes" coincidiria com o
                        # "agora" e a party receberia a mesma coisa duas vezes.
                        continue
```

Atencao a `devidos.sort(key=lambda a: (a.devido_em, a.tipo.value))` (l.186): o
desempate e por `tipo.value` alfabetico — `"agora" < "antes" < "chamada"`. Com
`chamar_minutos_antes = 110` nunca ha empate real, mas o teste de ordem em
`tests/test_agenda.py::TestAvisosDevidos` (l.44) e onde isso se afirma.

**A chave duravel sai de graca** (`agenda.py:107-120`) — nada a mudar, so a
citar no plano como a razao de o desenho ser um tipo novo:

```python
    @property
    def chave(self) -> str:
        apelido = re.sub(r"[^a-z0-9]+", "-", self.evento.lower()).strip("-")
        return (
            f"{self.alvo.date().isoformat()}"
            f"_{apelido}-{self.alvo.hour:02d}{self.alvo.minute:02d}"
            f"_{self.tipo.value}"
        )
```

**Texto do aviso** — `texto_do_aviso` ja e um `if` por tipo (`agenda.py:225-235`):

```python
    hora = f"{aviso.alvo.hour:02d}:{aviso.alvo.minute:02d}"
    if aviso.tipo is TipoDeAviso.ANTES:
        ...
        return texto
    return f"{aviso.evento} comecou agora, as {hora}."
```

O ramo da CHAMADA vira um `if aviso.tipo is TipoDeAviso.CHAMADA: return ...`
ANTES do `return` final. A docstring dessa funcao (l.216-218) ja da o argumento
que o CONTEXT reusa: "textos diferentes porque servem a acoes diferentes".

---

### `l2scanner/agenda.py` — a lista de presenca em disco (model, file-I/O)

**Analogo:** `PREFIXO_CANCELADO` + `cancelar()` + `cancelados()`
(`agenda.py:240-326`). E o precedente EXATO de "um segundo namespace de arquivo
vazio na mesma pasta, com a poda e a atomicidade de graca":

```python
# Prefixo dos marcadores de CANCELAMENTO, para nao se confundirem com os de
# "ja avisei". Namespaces diferentes no mesmo diretorio: a poda, a atomicidade
# e o compartilhamento entre instancias valem para os dois de graca.
PREFIXO_CANCELADO = "cancelado_"
```

```python
    def cancelar(self, chave_da_ocorrencia: str) -> bool:
        """Marca uma ocorrencia como cancelada. True se ESTE processo marcou."""
        return self.marcar(PREFIXO_CANCELADO + chave_da_ocorrencia)

    def cancelados(self) -> set[str]:
        """Ocorrencias canceladas, sem o prefixo."""
        return {
            nome[len(PREFIXO_CANCELADO) :]
            for nome in self.enviados()
            if nome.startswith(PREFIXO_CANCELADO)
        }
```

O nome decidido no CONTEXT e `presenca_<chave-da-ocorrencia>_<apelido>`. Copiar
essa forma: constante `PREFIXO_PRESENCA = "presenca_"`, um `entrar(chave, nick)
-> bool` sobre `marcar`, e um `presentes(chave) -> list[str]` sobre `enviados()`
com `startswith` + `partition`.

**A poda funciona sem tocar em nada** (`agenda.py:341-348`) — porque ela retira
o prefixo e le a data do INICIO do nome, e `chave_da_ocorrencia` comeca com
`YYYY-MM-DD`:

```python
            nome = caminho.name
            if nome.startswith(PREFIXO_CANCELADO):
                nome = nome[len(PREFIXO_CANCELADO) :]
            try:
                dia = date.fromisoformat(nome.split("_", 1)[0])
            except (ValueError, IndexError):
                continue  # nao e um marcador nosso; nao mexer
```

**ARESTA REAL, e o planejador tem que resolver explicitamente:** este `podar`
so retira UM prefixo, o de cancelamento. `presenca_2026-08-26_solo-boss-2000_j4guar`
cai no `except` e **nunca e podado** — o oposto da decisao do CONTEXT ("a poda
de 3 dias e CORRETA aqui"). O conserto e uma tupla de prefixos conhecidos, ou
um `for prefixo in (...)`. Isso e um item de plano, nao um detalhe.

**A escolha tri-estado, obrigatoria e deliberada.** Os dois precedentes sao
opostos e estao documentados. `agenda.RegistroEmDisco.marcar` colapsa falha de
disco em `True` (`agenda.py:300-309`):

```python
        except OSError:
            # Disco cheio, permissao, pasta sumiu. Preferir o aviso duplicado
            # ao aviso perdido: a party consegue ignorar uma repeticao, mas nao
            # consegue adivinhar um TvT que ninguem anunciou.
            return True
```

`loot.RegistroDeLoot._criar` faz o CONTRARIO, com tres estados
(`l2scanner/loot.py:197-215`):

```python
    def _criar(self, nome: str) -> str:
        """Cria um marcador vazio. Tri-estado: criado | ja_existia | falhou."""
        try:
            descritor = os.open(
                self._pasta / nome, os.O_CREAT | os.O_EXCL | os.O_WRONLY
            )
        except FileExistsError:
            return "ja_existia"
        except OSError:
            return "falhou"
        os.close(descritor)
        return "criado"
```

Para o `.join`, `ja_existia` E informacao de produto (a decisao "join repetido
nao repete no grupo" depende de distinguir criado de ja_existia), entao o
tri-estado do `loot` e o analogo certo — mas a docstring nova tem que dizer o
que fazer com `"falhou"`, no mesmo tom de `loot.py:16-22`.

---

### `l2scanner/comandos.py` — `.join` / `.leave` (controller, request-response)

**Analogo:** `Comando.SOLO` / `Comando.PARTY`. Sao o par sem argumento mais
recente e estao no `_VOCABULARIO` fixo (`comandos.py:79-83`):

```python
    # Entrar e sair do modo solo sem reiniciar. E o comando que mais faz
    # sentido vir do WhatsApp: a hora de virar solo e quando a party se
    # desfaz, e nesse momento o usuario esta no jogo, nao no console.
    SOLO = "solo"
    PARTY = "party"
```

`.join` e `.leave` nao tem argumento -> `_VOCABULARIO`, nao
`interpretar_dinamico` (a discricao do CONTEXT fica assim resolvida pelo
padrao). Forma a copiar (`comandos.py:128-137`):

```python
    "solo": Comando.SOLO,
    "soloplay": Comando.SOLO,
    "party": Comando.PARTY,
    "pt": Comando.PARTY,
    "grupo": Comando.PARTY,
```

**COLISAO A VERIFICAR ANTES DE ESCREVER:** `interpretar_dinamico` tem o ramo
`.{nick}` (`comandos.py:453-461`), e ele so devolve consulta quando a palavra
NAO esta no `_VOCABULARIO`:

```python
    if len(palavras) == 1 and _NICK_VALIDO.fullmatch(crua):
        baixo = crua.lower()
        if baixo in _VOCABULARIO or baixo == _PALAVRA_HUMANA:
            return None
        if apelido(crua) in nicks_conhecidos:
            return (Comando.LOOT_CONSULTA, crua)
```

Ou seja: por em `_VOCABULARIO` ja protege `.join` de virar consulta de um
personagem chamado "Join". A precedencia tambem ja e garantida em
`comandos_novos` (l.489-497), que tenta `interpretar` primeiro. Nada novo a
inventar — so nao inverter.

**O TRIPWIRE que vai quebrar a suite (de proposito).** A tabela `_AJUDA`
(`comandos.py:172-198`) e chaveada pelo ENUM, e `tests/test_comandos.py:161-178`
falha assim que `Comando` cresce:

```python
        faltando = set(Comando) - set(_AJUDA)
        assert not faltando, (
            "comando novo sem entrada na tabela de ajuda: "
            + ", ".join(sorted(c.name for c in faltando))
        )
```

E ha um SEGUNDO tripwire, mais exigente, em `tests/test_comandos.py:179-202`:
cada `sintaxe` anunciada e passada pelo caminho real (`comandos_novos` ->
`interpretar` -> `interpretar_dinamico`) com as cinco travas ligadas, incluindo
a allowlist de telefone. **Isso importa muito nesta fase:** o teste manda a
sintaxe com `TELEFONE = "+5544997077000"`, que e um telefone de
`CHATWOOT_TELEFONES_COMANDO`. Se `.join` passar a exigir o nivel novo de
autorizacao de um jeito que EXCLUA o nivel antigo, esse teste quebra. A decisao
do CONTEXT ja resolve — `CHATWOOT_TELEFONES_COMANDO` alcanca todo comando —
mas o plano precisa dizer isso, senao a implementacao "so membro pode dar
`.join`" derruba a suite.

Linha de ajuda a copiar em forma (`comandos.py:194-196`):

```python
    Comando.PARTY: LinhaDeAjuda(
        "Vigilancia", ".party", "Volto a vigiar a party inteira", (".pt",)
    ),
```

E ha um teste de ORDEM das familias (`tests/test_comandos.py:216-222`, contra
`_FAMILIAS_ESPERADAS`): uma familia nova ("Solo Boss" / "Presenca") tem que
entrar tambem nessa lista do teste, na posicao combinada.

**Autorizacao — o segundo nivel.** O nivel unico de hoje (`comandos.py:~658-671`):

```python
def autor_autorizado(remetente: dict, telefones: list[str]) -> bool:
    """Quem mandou pode mandar?

    Lista VAZIA aceita qualquer um — e a compatibilidade com quem ja tinha
    configurado comandos so por conversa.
    """
    if not telefones:
        return True
    numero = remetente.get("phone_number")
    return any(telefone_equivalente(numero, permitido) for permitido in telefones)
```

O nivel novo REUSA `telefone_equivalente` (`comandos.py:~640-654`) — nunca
reimplementa o corte de 8 digitos:

```python
def telefone_equivalente(a: str | None, b: str | None) -> bool:
    da, db = so_digitos(a), so_digitos(b)
    if not da or not db:
        return False
    corte = DIGITOS_FINAIS_DO_TELEFONE
    if len(da) < corte or len(db) < corte:
        return da == db
    return da[-corte:] == db[-corte:]
```

E a trava fica onde a trava de hoje ja fica, dentro de `comandos_novos`
(l.499-503):

```python
        # TRAVA 5: quem mandou pode mandar? Vale ate dentro de um grupo, onde a
        # allowlist de conversa sozinha liberaria todo mundo.
        remetente = bruta.get("sender") or {}
        if not autor_autorizado(remetente, telefones or []):
            continue
```

O padrao a seguir: `comandos_novos` ganha um parametro a mais (membros), com
default vazio — exatamente como `nicks_conhecidos: frozenset[str] = frozenset()`
ja fez (l.466), preservando toda chamada existente. E o NICK do autor sai desse
mapa, nunca de `remetente.get("name")` (que hoje so alimenta o log, l.568) —
a disciplina "nome sempre da configuracao" do CONTEXT.

---

### `l2scanner/config.py` — `[[membro]]` e `chamar_minutos_antes` (config, file-I/O)

**Analogo para `chamar_minutos_antes`:** a validacao de `avisar_minutos_antes`
(`config.py:203-213`) — copiar literalmente, trocando o nome:

```python
    antes = bruto.get("avisar_minutos_antes", 10)
    if not isinstance(antes, int) or antes < 0:
        raise AgendaInvalida(
            f"{onde}: 'avisar_minutos_antes' precisa ser um numero inteiro >= 0."
        )

    no_horario = bruto.get("avisar_no_horario", True)
    if not isinstance(no_horario, bool):
        raise AgendaInvalida(
            f"{onde}: 'avisar_no_horario' precisa ser true ou false."
        )
```

O `onde` vem de `config.py:160` e e o padrao de mensagem de erro do projeto
(cita o NOME do evento, nao o indice):

```python
    onde = f"evento '{bruto['nome']}'" if bruto.get("nome") else f"[[evento]] #{indice + 1}"
```

**Analogo para `[[membro]]`:** `ler_agenda` (`config.py:127-150`) — mesma
estrutura de leitura, mesma tolerancia a arquivo ausente, mesmo `raise` em
arquivo mal formado:

```python
    caminho = caminho or ARQUIVO_CONFIG
    if not caminho.exists():
        return []

    try:
        with caminho.open("rb") as arquivo:
            dados = tomllib.load(arquivo)
    except tomllib.TOMLDecodeError as erro:
        raise AgendaInvalida(
            f"{caminho.name} nao e um TOML valido: {erro}"
        ) from erro

    return [_evento_de_dict(bruto, i) for i, bruto in enumerate(dados.get("evento", []))]
```

Nasce um `ler_membros(caminho=None) -> list[Membro]` com `dados.get("membro", [])`.
O `Membro` e um `@dataclass(frozen=True)` com `nick: str` e `telefone: str` —
mesma forma de `EventoAgendado` (`agenda.py:75-95`). O nick deve passar por
`NICK_VALIDO` do `loot.py` (l.65) na validacao, para o mesmo charset valer nos
dois lados.

**Nao por o mapa de membros no `.env`.** O precedente esta explicito: o `.env`
guarda segredo (`config.py:111-118`), o `config.toml` e "feito para ser aberto,
editado a mao e ate versionado". Um telefone de party-mate nao e token. Mas
note que `CHATWOOT_TELEFONES_COMANDO` mora no `.env` (`config.py:99-103`) — a
assimetria e proposital e vale um comentario no codigo novo.

**Analogo de config.toml (documentacao do usuario):** o bloco de comentario do
Solo Boss em `config.toml:38-46` — comentario que explica o volume de mensagem
antes de mostrar o campo. O `chamar_minutos_antes = 110` entra ali, e o cabecalho
"Campos de cada [[evento]]" (`config.toml:9-19`) tem que crescer junto, senao a
documentacao do arquivo mente por omissao.

---

### `l2scanner/sessao.py` — o fechamento no horario (service, event-driven)

**Analogo exato:** `self.loot.consumir(agora)` dentro de `_processar_agenda`
(`sessao.py:278-282`). Mesma posicao, mesmo racional de ordem deterministica:

```python
        # DEPOIS dos avisos, de proposito. A ordem e indiferente no relogio —
        # o aviso ANTES vence 10 min antes do alvo e o consumo so dispara no
        # alvo — mas fixa-la torna o tick deterministico para o teste.
        if self.loot:
            resultado.loot_consumado = self.loot.consumir(agora)
```

Como o resultado vira teste — `ResultadoDoTick` estruturado, nunca texto
(`sessao.py:71-81`):

```python
    # Avisos de agenda que venceram neste tick.
    avisos: list[str] = field(default_factory=list)

    # A designacao de loot que ESTE tick consumiu (o horario do boss passou e
    # esta instancia venceu a corrida do registro). Estruturado, nao texto —
    # pelo mesmo motivo de `despachos` existir: teste afirma estrutura, nao
    # redacao.
    loot_consumado: Designacao | None = None
```

O campo novo (`presenca_fechada: ... | None = None`) segue essa forma, com o
mesmo comentario de POR QUE ser estruturado.

**Injecao opcional com default `None`** (`sessao.py:100-124`) — e o que mantem
toda chamada existente e todo teste existente intactos:

```python
        # O registro de loot do Solo Boss. Default None mantem toda chamada
        # existente intacta — sem ele o tick simplesmente nao fala de loot.
        self.loot = loot
```

**O `marcar` E a decisao de despachar** — a regra escrita em
`sessao.py:290-296` e repetida em `_processar_manutencao:303`:

```python
        for aviso in self.manutencao.avaliar(...):
            if not self.registro.marcar(aviso.chave):
                continue
```

O fechamento tem que passar pelo mesmo portao (uma chave `fechou_presenca_<chave>`
ou equivalente), senao as DUAS instancias do usuario mandam a lista final em
dobro. E "zero joins produz zero mensagem" (CONTEXT) tem que ser checado ANTES
ou DEPOIS do marcar de forma deliberada — o plano precisa dizer qual.

**Moldura no despacho, cru no resultado** (`sessao.py:267-276`), a repetir:

```python
            resultado.avisos.append(texto)
            # CRU no resultado, MOLDURADO no despacho. O console monta a
            # propria moldura (com cor) a partir de `avisos`; moldurar aqui
            # tambem faria o bloco sair dentro de outro bloco na tela.
            self._despachar(
                moldurar(texto, agora.strftime("%H:%M")),
                Categoria.SEMPRE,
                resultado=resultado,
            )
```

---

### `l2scanner/loot.py` — a lista sugere a vez (service, CRUD)

**Analogo:** `responder_designacao` (`loot.py:802-838`), que e a funcao que ja
recebe `eventos` e `agora` e decide sobre o proximo boss:

```python
def responder_designacao(
    registro: RegistroDeLoot,
    eventos: list[EventoAgendado],
    agora: datetime,
    nick: str,
) -> str:
    evento = next((e for e in eventos if eh_solo_boss(e.nome)), None)
    proximo = proxima_ocorrencia(agora, [evento]) if evento is not None else None
    if proximo is None:
        return (
            "Nao achei o Solo Boss na agenda do config.toml — "
            "nao da para marcar o loot."
        )
    nome_do_evento, alvo = proximo
    anterior = registro.designacao()
    registro.designar(nick, alvo, agora)
```

**A decisao "SUGERE, nao manda" tem precedente literal.** O idioma de
"avisa e obedece" ja existe em `responder_designacao`, que grava mesmo quando
substitui alguem e so ACRESCENTA a informacao (l.833-838):

```python
    if (
        anterior is not None
        and anterior.alvo == alvo
        and apelido(anterior.nick) != apelido(nick)
    ):
        resposta += f" (Era do {exibir(anterior.nick)}.)"
```

O `.loot-<nick>` de quem nao joinou segue essa forma: grava, e a resposta ganha
um sufixo do tipo "(Ele nao estava na lista de presenca.)". Nunca um `return`
de recusa.

**Direcao da dependencia — restricao dura** (`loot.py:27-28`):

```python
Este modulo NUNCA importa `comandos` nem `sessao`: sao eles que importam
daqui, e um ciclo mataria os dois.
```

`loot.py` ja importa de `agenda` (l.39-45). Se a lista de presenca morar em
`agenda.py`, o `loot` pode le-la direto. Se morar em `presenca.py` novo, esse
modulo nao pode importar `loot` (que precisa de `apelido`) e ser importado por
ele ao mesmo tempo — `apelido` e `NICK_VALIDO` moram no `loot` justamente por
essa razao (`loot.py:59-65`). A saida limpa: `presenca.py` importa de `agenda`
apenas, e recebe o slug ja pronto de quem chama.

**Nicks conhecidos** — se `.join` deve abrir o `.<nick>` para o membro, o ponto
e `nicks_conhecidos` (`loot.py:518-544`), que ja e uma UNIAO de tres fontes:

```python
        conhecidos = {
            nome[len(_PREFIXO_NICK) :]
            for nome in nomes
            if nome.startswith(_PREFIXO_NICK)
        }
        conhecidos.update(slug for slug, _ in self.registros())
```

---

### `l2scanner/__main__.py` — os ramos `.join` / `.leave` (controller)

**Analogo:** o ramo `LOOT_DESIGNAR` (`__main__.py:589-600`), incluindo a
guarda de recurso ausente e o comentario que justifica o eco:

```python
        elif pedido.comando is Comando.LOOT_DESIGNAR:
            if loot is None:
                resposta = "Nao consigo mexer no loot agora."
            else:
                resposta = responder_designacao(
                    loot, eventos_agendados, agora, pedido.argumento
                )
            # O grupo vai ficar sabendo pelo proprio aviso de antecedencia,
            # que sai com "Loot: X" no fim. Ecoar agora seria dizer a mesma
            # coisa duas vezes — e o grupo nem entrega incoming; os comandos
            # chegam pelo privado.
            avisar_o_grupo = False
```

**A confirmacao nos dois lugares e literalmente `avisar_o_grupo = True`**
(`__main__.py:655-668`) — a decisao do CONTEXT ja tem mecanismo pronto:

```python
        # RESPONDE ONDE PERGUNTARAM. Sem isto, um `.status` mandado no privado
        # era respondido no grupo — medido ao vivo: pergunta as 23:04:42 na
        # conversa 1, resposta as 23:04:52 na 13, e o usuario achou que nao
        # tinha funcionado.
        if pedido.conversa:
            despachante.despachar(resposta, Categoria.SEMPRE, pedido.conversa)
            if avisar_o_grupo:
                despachante.despachar(resposta, Categoria.SEMPRE)
        else:
            despachante.despachar(resposta, Categoria.SEMPRE)
```

**ARESTA:** esse mecanismo manda O MESMO TEXTO nos dois destinos. O CONTEXT
pede textos DIFERENTES ("uma linha curta no privado" vs. a confirmacao no
grupo). Isso e trabalho real: ou o ramo despacha o do grupo por conta propria
antes de cair no bloco comum, ou `resposta` vira um par. O plano tem que
escolher; hoje nao ha analogo de resposta em duas redacoes.

**Marca ANTES de agir** (`__main__.py:562-566`) — vale igual para `.join`:

```python
        # Marca ANTES de agir. Se o processo morrer no meio, o pior caso e um
        # comando perdido — nao um comando obedecido em laco a cada tick.
        if not registro.marcar(chave_da_mensagem(pedido.id)):
            continue
```

---

## Shared Patterns

### Atomicidade entre as duas instancias
**Fonte:** `l2scanner/agenda.py:292-309` (`marcar`) e `l2scanner/loot.py:197-215` (`_criar`).
**Aplicar a:** lista de presenca (`.join`), fechamento no horario.
O usuario roda DUAS instancias (Yazalaque e Faerlina) na mesma pasta. Toda
escrita nova em `.agenda/` e `os.O_CREAT | os.O_EXCL | os.O_WRONLY` sobre um
arquivo VAZIO cujo NOME e a identidade. Nunca "le JSON, checa, escreve JSON".

### O tempo entra por parametro
**Fonte:** `l2scanner/agenda.py:6-10` e `l2scanner/loot.py:23-26`.
**Aplicar a:** todo codigo novo em `agenda.py`, `loot.py` e no modulo de presenca.
Nenhum `datetime.now()`. `avisos_devidos(agora, ...)`, `consumir(agora)`,
`designar(nick, alvo, agora)` — a assinatura sempre comeca ou termina no
instante. E o que permite testar o fechamento atrasado em milissegundos.

### Funcao pura primeiro, IO na borda
**Fonte:** `l2scanner/agenda.py:148-152` ("Funcao pura: mesmo instante, mesma
agenda, mesmo conjunto de enviados -> mesma resposta, sempre. Sem relogio, sem
disco, sem rede") e `comandos.comandos_novos:475-477`.
**Aplicar a:** a decisao de "quem esta na lista" e "o que dizer" deve ser pura,
recebendo o set de presentes ja lido. O disco fica na classe de registro.

### Estruturado, nunca o texto
**Fonte:** `agenda.Aviso.chave:109-113` ("ESTRUTURADA, jamais o texto da
mensagem") e `sessao.ResultadoDoTick:54-58`.
**Aplicar a:** chave de presenca, chave de fechamento, campo novo no
`ResultadoDoTick`. Teste afirma estrutura; a redacao muda toda semana.

### Docstring que explica POR QUE, com medida de campo
**Fonte:** `comandos.py:52-64` (o nono digito, `+5544997077000` vs
`554497077000`), `agenda.py:86-89` (12 ocorrencias/dia -> 24 mensagens),
`__main__.py:655-659` (pergunta as 23:04:42 na conversa 1, resposta na 13).
**Aplicar a:** todo bloco novo. Em particular a chamada de 1h50: a medida esta
no CONTEXT — 1h50 e dez minutos DEPOIS do boss anterior, o unico instante do
ciclo em que a party esta reunida. Essa frase pertence ao codigo.

### Sem acento em identificador, docstring e comentario
**Fonte:** o arquivo inteiro de `agenda.py`, `loot.py`, `comandos.py`
(`apelido`, `ocorrencia`, `duravel`, `silencio`). Excecao historica:
`sessao.py` e `visao.py` tem acento na prosa. **Codigo novo desta fase segue o
`agenda`/`loot`/`comandos`: sem acento.**

### Recurso ausente nao derruba nada
**Fonte:** `sessao.py:118-124` (default `None`) e `config.py:130-133`
("ARQUIVO AUSENTE NAO E ERRO").
**Aplicar a:** sem `[[membro]]` no config, sem `chamar_minutos_antes`, o
scanner roda exatamente como hoje. Nenhum teste existente pode precisar mudar.

---

## Onde os testes vao

| O que | Arquivo | Classe-analogo a imitar |
|---|---|---|
| `TipoDeAviso.CHAMADA`, `chamar_minutos_antes`, chave duravel, texto | `tests/test_agenda.py` | `TestAvisosDevidos` (l.44), `TestChaveDoAviso` (l.151), `TestTextoDoAviso` (l.175), `TestAgendaRealDoUsuario` (l.292) |
| `chamar_minutos_antes` e `[[membro]]` lidos do TOML | `tests/test_agenda.py` | `TestLerAgenda` (l.213) — e onde a validacao do config ja e testada |
| Lista de presenca em disco, corrida das duas instancias, poda | `tests/test_agenda.py` | `TestRegistroEmDisco` (l.426) — inclui `test_competicao_de_verdade_com_threads` (l.456), que e o teste que o plano deve replicar para `presenca_*` |
| `.join`/`.leave` no parser, tripwire da ajuda, autorizacao de 2 niveis | `tests/test_comandos.py` | a classe do tripwire (l.~130-230); `_FAMILIAS_ESPERADAS` precisa crescer |
| Fechamento dentro do tick | `tests/test_sessao.py` | `TestLootNoTick` (l.454) — ja monta `EventoAgendado(nome="Solo Boss", ..., avisar_no_horario=False)` e afirma sobre `r.avisos`/`r.despachos` |
| Sugestao de vez a partir da lista fechada | `tests/test_loot.py` | `TestResponderDesignacao` (l.368), `TestNicksConhecidos` (l.196) |

Um `tests/test_presenca.py` novo so se a lista virar `l2scanner/presenca.py`.
Convencao observada: um arquivo de teste por modulo, com `class TestX` sem
`unittest`, `tmp_path` do pytest para tudo que toca disco, e helper local
`def em(hora, minuto)` fixando a data (`tests/test_loot.py:46-47`,
`tests/test_sessao.py:84`).

---

## No Analog Found

| Coisa | Papel | Por que nao ha analogo |
|---|---|---|
| Resposta com DUAS redacoes (uma para o privado, outra para o grupo) | controller | Todo comando hoje despacha o MESMO texto nos dois destinos (`__main__.py:661-664`). O CONTEXT pede textos diferentes. E desenho novo, pequeno mas real. |
| Autorizacao POR COMANDO (um nivel que alcanca so `.join`/`.leave`) | middleware | `autor_autorizado` (`comandos.py:~658`) e binario e global. O mecanismo de comparacao (`telefone_equivalente`) se reusa inteiro; a estrutura da decisao ("este telefone alcanca ESTE comando") nao existe em lugar nenhum. |
| Poda de um segundo prefixo em `.agenda/` | model | `podar` (`agenda.py:328-354`) so retira `PREFIXO_CANCELADO`. Um terceiro prefixo exige mudar essa funcao — e o teste que prova a poda tem que nascer junto. |

---

## Metadata

**Escopo da busca:** `l2scanner/` (24 modulos) e `tests/` (23 arquivos)
**Arquivos lidos por inteiro:** `agenda.py`, `config.py`, `sessao.py`, `comandos.py`, `config.toml`
**Arquivos lidos por trecho dirigido:** `loot.py` (l.1-130, 177-360, 491-560, 709-860), `__main__.py` (l.440-500, 540-670), `notificador.py` (l.223-247), `tests/test_comandos.py` (l.140-230), `tests/test_agenda.py` (l.426-470), `tests/test_loot.py` (l.30-90), `tests/test_sessao.py` (l.454-520)
**Data:** 2026-08-26
