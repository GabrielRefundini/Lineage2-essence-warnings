# Phase 02: Leitura de página - Pattern Map

**Mapped:** 2026-08-29
**Files analyzed:** 8 (3 novos de produção, 1 novo de catálogo, 3 modificados, N de teste)
**Analogs found:** 8 / 8 — nenhum arquivo desta fase estreia sem precedente no repositório

> **A conclusão que muda o plano:** esta fase é, em grande parte, **PROMOÇÃO**. As primitivas
> de segmentação e classificação de glifo já existem, medidas e testadas, dentro de
> `l2scanner/calibrar_mercado.py`. E o repositório **já tem o padrão exato de como mover uma
> primitiva sem duplicá-la** — ele foi executado na Fase 1, entre `calibrar.py` e
> `calibrar_mercado.py`, e o comentário que documenta a decisão está citado abaixo.

---

## File Classification

| Novo/Modificado | Role | Data Flow | Analog mais próximo | Match |
|---|---|---|---|---|
| `l2scanner/mercado_leitura.py` (NOVO) | service / transform puro | transform (pixels → valor) | `l2scanner/mercado_geometria.py` (charter) + `l2scanner/calibrar_mercado.py` (as primitivas que migram) | **exact** (é literalmente o código de lá, com o charter de cá) |
| `l2scanner/mercado_catalogo.py` (NOVO) | model + file-I/O | file-I/O / append acumulado | `l2scanner/loot.py` (`RegistroDeLoot`) | **role-match** (durável, acumulado, escrita atômica; muda json→csv) |
| `l2scanner/mercado_pagina.py` (NOVO) | state machine | event-driven / stateful por tick | `l2scanner/manutencao.py` (`VigiaDeManutencao`) e `mercado_visao.RastreioDoPainel` | **exact** (acordo entre duas leituras + memória entre ticks, os dois já existem) |
| `l2scanner/calibracao.py` (MOD) | config / model | CRUD de arquivo | ele mesmo — as 9 chaves `mercado_*` já lá | **exact** (copiar o padrão da chave irmã) |
| `l2scanner/mercado_visao.py` (MOD) | model / desserialização não confiável | transform + validação | `glifos_de_calibracao` no próprio arquivo | **exact** |
| `l2scanner/calibrar_mercado.py` (MOD) | tool / CLI interativa | request-response (humano) | ele mesmo — o fluxo propor-e-confirmar de `propor_rotulo` + `_pedir_rotulo` | **exact** |
| `l2scanner/mercado_geometria.py` (MOD) | service / medição pura | transform | `fim_da_alternancia` no próprio arquivo | **exact** |
| `tests/test_mercado_leitura.py` etc. (NOVOS) | test | file-I/O de fixture | `tests/test_mercado_glifos.py` + `tests/test_mercado_27x.py` | **exact** (o segundo tem o `skip` de `recordings/`) |

---

## Pattern Assignments

### `l2scanner/mercado_leitura.py` (NOVO — transform puro)

**Analog de CHARTER:** `l2scanner/mercado_geometria.py:1-6`
**Analog de CONTEÚDO:** `l2scanner/calibrar_mercado.py` (as primitivas migram de lá)

**Docstring de charter — copiar a forma** (`mercado_geometria.py:1-6`):
```python
"""Onde ficam as regioes do painel do mercado, MEDIDAS a partir dos pixels.

Este modulo nao abre janela, nao le teclado, nao escreve arquivo e nao pergunta
nada. Ele olha um frame gravado e responde "a grade comeca aqui, tem tantas
linhas de tanto". Quem mostra isso a um humano e quem aceita a correcao dele e
`calibrar_mercado.py`.
"""
```

**Bloco de imports — a convenção da casa é import relativo, e `mercado_geometria.py:79-90` é o modelo:**
```python
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .mercado_visao import (...)
```
Nota: módulos puros (`identidade.py:39-44`, `mercado_geometria.py:79-85`, `mercado_visao.py:79-84`)
importam apenas `dataclasses`/`numpy`/`cv2` + irmãos `.puros`. As tools
(`calibrar.py:19-51`, `calibrar_mercado.py:45-91`) é que carregam `argparse`, `sys`, `cv2.imshow`
**e o `from .dpi import tornar_consciente_de_dpi` ANTES de tudo, com `# noqa: E402` no resto.**
`mercado_leitura.py` NÃO pode ter esse cabeçalho.

**Core pattern 1 — segmentação por projeção de coluna** (`calibrar_mercado.py:406-428`, mover inteira):
```python
    mascara = mascara_de_texto(recorte)
    if mascara.size == 0:
        return None, []

    linhas = np.flatnonzero(mascara.any(axis=1))
    if linhas.size == 0:
        return None, []
    faixa = (int(linhas[0]), int(linhas[-1]) + 1)

    runs: list[tuple[int, int]] = []
    inicio: int | None = None
    for coluna, tem_texto in enumerate(mascara.any(axis=0)):
        if tem_texto and inicio is None:
            inicio = coluna
        elif not tem_texto and inicio is not None:
            runs.append((inicio, coluna))
            inicio = None
    if inicio is not None:
        runs.append((inicio, int(mascara.shape[1])))

    return faixa, runs
```
A docstring de 45 linhas (`calibrar_mercado.py:362-405`) **vai junto** — é ela que carrega a
convenção de faixa compartilhada e a medição 8/8.

**Core pattern 2 — argmax + margem, o classificador a promover** (`calibrar_mercado.py:1620-1643`):
```python
    de_um_caractere = {r: m for r, m in moldes.items() if len(r) == 1}
    if not de_um_caractere or not runs:
        return None

    topo, base = faixa
    lido: list[str] = []
    for inicio, fim in runs:
        recorte = mascara[topo:base, inicio:fim]
        pontuados: list[tuple[float, str]] = []
        for rotulo, molde in de_um_caractere.items():
            a, b = _alinhar_por_preenchimento(recorte, molde)
            if _par_incalculavel(a, b):
                continue
            pontuados.append((casamento_da_ancora(a, b), rotulo))
        if not pontuados:
            return None
        pontuados.sort(reverse=True)
        melhor_score, melhor_rotulo = pontuados[0]
        if melhor_score < MINIMO_PARA_PROPOR_ROTULO:
            return None
        segundo = pontuados[1][0] if len(pontuados) > 1 else -1.0
        if melhor_score - segundo < MARGEM_MINIMA_PARA_PROPOR:
            return None
        lido.append(melhor_rotulo)
    return "".join(lido)
```
**TUDO OU NADA é a falha fechada desta função e ela já está escrita.** Em produção os dois
números NÃO podem ser `MINIMO_PARA_PROPOR_ROTULO`/`MARGEM_MINIMA_PARA_PROPOR` reaproveitados
sem medição (a margem `0`×`8` de 0,0370 da §Pitfall 2 da pesquisa é menor que 0,12): ver
"Shared Patterns → constante medida".

**Alinhamento — a convenção OPOSTA de propósito** (`calibrar_mercado.py:501-527`):
```python
def _alinhar_por_preenchimento(a, b):
    """Iguala os dois PREENCHENDO ate a maior caixa comum, com zeros.
    ... Medido: 0.1918 preenchendo, 0.5000 cortando.
    """
    altura = max(a.shape[0], b.shape[0])
    largura = max(a.shape[1], b.shape[1])
    saida = []
    for arranjo in (a, b):
        caixa = np.zeros((altura, largura), dtype=arranjo.dtype)
        if arranjo.size:
            caixa[: arranjo.shape[0], : arranjo.shape[1]] = arranjo
        saida.append(caixa)
    return saida[0], saida[1]
```

**Error handling — nunca levantar dentro do tick** (`ocr.py:195-217`, o modelo exato para
`ler_linha`):
```python
def _ler(pixels, escala: int) -> str | None:
    """O texto que o OCR viu no recorte, ou None. NUNCA levanta.

    Nunca levanta porque roda DENTRO do tick de captura. Uma excecao aqui
    pararia o scanner de olhar a party — e a proxima morte real passaria
    despercebida, que e o unico defeito que este projeto trata como
    inaceitavel.
    """
    if pixels is None:
        return None
    if getattr(pixels, "size", 0) == 0:
        return None
    if not disponivel():
        return None
    try:
        return _reconhecer(pixels, escala)
    except Exception as erro:
        log.debug("OCR falhou neste recorte: %s", erro)
        return None
```

---

### `l2scanner/mercado_catalogo.py` (NOVO — model + file-I/O acumulado)

**Analog:** `l2scanner/loot.py` (`RegistroDeLoot`)
**Ressalva honesta:** não há precedente de `csv` no repositório inteiro
(`grep "import csv" l2scanner/ tests/` → vazio). O analog cobre **onde o arquivo mora, como se
escreve e como se lê defensivamente**, não o formato.

**Imports/constantes de caminho** (`config.py:32`):
```python
RAIZ = Path(__file__).resolve().parent.parent
```
Caminho SEMPRE derivado da raiz do projeto, nunca de entrada do usuário (V12 da pesquisa).

**Construtor + posse da pasta** (`loot.py:192-194`):
```python
    def __init__(self, pasta: Path) -> None:
        self._pasta = pasta
        self._pasta.mkdir(parents=True, exist_ok=True)
```

**Escrita atômica — copiar literalmente** (`loot.py:264-281`):
```python
        temporario = self._pasta / f"{_ARQUIVO_PROXIMO}.tmp-{os.getpid()}"
        temporario.write_text(json.dumps({...}), encoding="utf-8")
        os.replace(temporario, self._pasta / _ARQUIVO_PROXIMO)
```
Com a razão registrada em `calibracao.py:433-441` (o mesmo mecanismo, escrito com mais palavras):
```python
        # `os.replace` e atomico no mesmo volume: ou fica o arquivo antigo
        # inteiro, ou o novo inteiro. Nunca meio. O temporario vive ao lado do
        # destino, e nao no %TEMP%, porque `os.replace` entre volumes
        # diferentes nao e atomico (e no Windows nem funciona).
        temporario = caminho.with_name(caminho.name + ".tmp")
        temporario.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temporario, caminho)
```

**Leitura defensiva de arquivo acumulado** (`loot.py:286-295`, docstring):
> *"Leitura defensiva de proposito: a outra instancia pode ter morrido no meio de uma escrita,
> e um arquivo meio-escrito nao pode derrubar o..."*

É o precedente exato da regra da pesquisa: **descartar a última linha malformada com aviso,
nunca tratar o arquivo inteiro como corrompido.**

**Modo de abertura deliberado** (`gravador.py:81-86`) — quando o arquivo NÃO pode existir:
```python
        # `"x"` e nao `"w"`: a pasta acabou de ser criada por nos, entao o
        # indice NAO pode existir. Se existir, alguma coisa esta muito errada e
        # truncar em silencio seria a pior resposta possivel.
        self._arquivo_meta = (self.pasta / "observacoes.jsonl").open("x", encoding="utf-8")
```
Para o catálogo o modo é o oposto (`"a"`), mas **a exigência de justificar o modo por escrito
é o padrão da casa.**

**Sem poda, de propósito** (`loot.py:189`): `# NAO tem poda, de proposito: estatistica de loot e para sempre.`
Vale igual para o catálogo de nomes.

---

### `l2scanner/mercado_pagina.py` (NOVO — máquina de estado)

**Analog primário:** `l2scanner/manutencao.py` (`VigiaDeManutencao`) — o acordo entre duas
leituras dentro do tick.
**Analog secundário:** `l2scanner/mercado_visao.py:447-510` (`RastreioDoPainel`) — memória
entre ticks e as duas cadências.

**O acordo entre dois métodos, com o desacordo tratado como estado próprio**
(`manutencao.py:466-504`):
```python
    def _ler_com_as_duas_escalas(self, pixels, agora: datetime):
        """O acordo de D-d, dentro do tick. Devolve (implicado, duracao) ou None.

        QUALQUER REPROVACAO DEVOLVE None SEM TOCAR EM `_candidata` NEM NA
        ANCORA. Uma discordancia nao confirma e tambem nao destroi: ...
        """
        barato = self._ler(self._ler_texto, pixels)
        if not eh_banner_de_manutencao(barato):
            return None  # D-e: a cara nem e tocada

        caro = self._ler(self._ler_texto_conferencia, pixels)
        if not eh_banner_de_manutencao(caro):
            self._registrar_desacordo(barato, caro)
            return None
        ...
        if not self._bate(agora + duracao_barata, agora + duracao_cara):
            self._registrar_desacordo(barato, caro)
            return None
```
**Este é o esqueleto do acordo 2x/3x de LEIT-01, incluindo o predicado revisado:** o `_bate`
já é um predicado de TOLERÂNCIA, não igualdade de string — exatamente a forma que o CONTEXT.md
revisado pede ("as duas leituras caem na MESMA SÉRIE"). Trocar `_bate` por
`mesma_serie(catalogo, a) == mesma_serie(catalogo, b)`.

**O log de desacordo — a recusa nunca é silenciosa** (`manutencao.py:506-527`):
```python
        log.warning(
            "As duas escalas de OCR DISCORDAM sobre o banner — nada sera "
            "anunciado. barata=>>>%s<<< conferencia=>>>%s<<<",
            barato,
            caro,
        )
```
Note os delimitadores `>>><<<` (espaço em branco importa) e a decisão explícita de **não** ter
rate-limit. Copiar as duas para o log de linha descartada por oclusão.

**Memória entre ticks + duas cadências** (`mercado_visao.py:470-502`):
```python
    def __init__(self, ancoras, limiar=CASAMENTO_MINIMO_DA_ANCORA,
                 ticks_entre_varreduras=TICKS_ENTRE_VARREDURAS_OCIOSAS) -> None:
        self._ancoras = list(ancoras)
        self._origem: tuple[int, int] | None = None
        self._desde_a_varredura = self._ticks_entre_varreduras
        self.varreduras = 0

    def observar(self, janela: np.ndarray) -> VotoDoPainel:
        if not self._ancoras:
            return VotoDoPainel(aberto=False, melhor=0.0)
        if self._origem is not None:
            voto = conferir_painel(janela, self._origem, self._ancoras, self._limiar)
            if voto.aberto:
                return voto
            # Saiu de onde estava. Procurar AGORA — nao na proxima volta.
            self._origem = None
            return self._varrer(janela)
```
**`mercado_pagina.py` NÃO reimplementa isto — ele instancia `RastreioDoPainel`.** Contador
público (`self.varreduras`) para o teste afirmar cadência sem relógio é o padrão a copiar
para `frames_congelados`.

O precedente de intervalo: `captura_janela.py:43 SEGUNDOS_ENTRE_BUSCAS_DO_DIALOGO = 5.0`,
citado por `mercado_visao.py:175` e `manutencao.py:44`.

---

### `l2scanner/calibracao.py` (MOD — chaves novas do `calibration.json`)

**Analog:** as 9 chaves `mercado_*` já existentes. Uma chave nova toca **quatro** lugares:

**1. Campo com docstring de razão** (`calibracao.py:288-304`):
```python
    mercado_templates_de_digito: list | None = None
    ...
    mercado_limiar_de_glifo: float | None = None
```

**2. `como_dict` / `salvar`** (`calibracao.py:405-416`):
```python
            "mercado_grade": self.mercado_grade,
            "mercado_templates_de_nome": self.mercado_templates_de_nome,
            "mercado_templates_de_digito": self.mercado_templates_de_digito,
            "mercado_limiar_de_template": self.mercado_limiar_de_template,
            "mercado_limiar_de_glifo": self.mercado_limiar_de_glifo,
```

**3. `carregar` via `.get` — e o comentário que explica por quê** (`calibracao.py:494-510`):
```python
            # As quatro de mercado seguem o MESMO `.get`: e o que faz um
            # calibration.json v2 gravado antes desta funcionalidade carregar
            # sem uma linha de migracao.
            mercado_grade=dados.get("mercado_grade"),
            mercado_templates_de_digito=dados.get("mercado_templates_de_digito"),
            mercado_limiar_de_glifo=dados.get("mercado_limiar_de_glifo"),
```
**`.get`, sempre. Nunca `dados["..."]` para chave nova, nunca bump de `VERSAO_DO_ESQUEMA`** —
o `calibration.json` do usuário tem 13 moldes e 3 âncoras que não podem sumir.

**4. Validação no portão de carga** (`calibracao.py:463` + `555-570`):
```python
        _conferir_as_chaves_de_mercado(dados)
```
```python
def _conferir_as_chaves_de_mercado(dados: dict) -> None:
    """As chaves de mercado sao ENTRADA NAO CONFIAVEL. Confere tipo e faixa.

    Mora AQUI, ao lado do portao de versao, e nao no consumidor, porque e no
    arranque que a mensagem ainda pode dizer "recalibre" com o usuario olhando
    para o console. O consumidor roda as duas da manha, no meio do farm.
    """
```
As chaves novas desta fase (coluna do nome, molde de cabeçalho, limiar de dispersão da sonda,
piso/margem de leitura de glifo) entram TODAS aqui.

---

### `l2scanner/mercado_visao.py` (MOD — desserializar o molde de cabeçalho)

**Analog:** `glifos_de_calibracao` (`mercado_visao.py:667-741`) — copiar a estrutura inteira.

```python
def glifos_de_calibracao(dados: list[dict] | None) -> dict[str, np.ndarray]:
    """ENTRADA NAO CONFIAVEL, pelo mesmo criterio de `ancoras_de_calibracao`. ..."""
    if not dados:
        return {}
    for indice, bruto in enumerate(dados):
        if not isinstance(bruto, dict):
            raise ValueError(f"... precisa ser um objeto, veio {type(bruto).__name__}. "
                             f"Recalibre os digitos do mercado.")
        rotulo = bruto.get("glifo")
        if not isinstance(rotulo, str) or not rotulo:
            raise ValueError("... O rotulo E a identidade do glifo ... Recalibre ...")
        if rotulo in moldes:
            raise ValueError(f"... tem o rotulo '{rotulo}' repetido. Um dos dois moldes "
                             f"seria descartado calado ... Recalibre ...")
        # A forma irma, quando o arquivo a traz. `None` quando nao traz, e nao
        # recusa: um calibration.json gravado antes desta chave continua carregando.
        forma = None
        alt, larg = bruto.get("altura"), bruto.get("largura")
        if isinstance(alt, int) and isinstance(larg, int) and not isinstance(alt, bool) ...:
            forma = (alt, larg)
        moldes[rotulo] = molde_de_hex(molde, forma_esperada=forma)
```
**Três invariantes a copiar:** (a) `None`/vazio → dict vazio, que é "feature OFF" e não erro;
(b) toda mensagem de erro termina com o CONSERTO ("Recalibre..."); (c) `isinstance(x, bool)`
excluído explicitamente do `int`.

**E a conferência de bytes antes do `reshape`** (`mercado_visao.py:246-260`):
```python
    altura, largura = int(dados["altura"]), int(dados["largura"])
    if altura <= 0 or largura <= 0:
        raise ValueError(f"molde da ancora com dimensao nao-positiva ({altura}x{largura}). "
                         f"Recalibre o mercado.")
    brutos = bytes.fromhex(dados["bytes"])
    if len(brutos) != altura * largura:
        raise ValueError(f"molde da ancora corrompido: altura {altura} x largura {largura} "
                         f"pedem {altura * largura} bytes, mas ha {len(brutos)}. ...")
```

---

### `l2scanner/calibrar_mercado.py` (MOD — marcar a coluna do nome + molde de cabeçalho)

**Analog:** o próprio fluxo propor-e-confirmar já dentro do arquivo.

**Propor-e-confirmar** (`calibrar_mercado.py:1648-1665`, docstring de `_pedir_rotulo`):
```python
    """... COM `proposta`, O USUARIO VIRA REVISOR EM VEZ DE OPERADOR. A ferramenta ja
    leu o numero comparando cada glifo com os que ele mesmo ja certificou (ver
    `propor_rotulo`), e o ENTER vazio confirma. Digitar continua valendo e
    continua vencendo -- a proposta e um rascunho, nunca uma decisao.
    """
```
A marcação da coluna do nome segue isto: `mercado_geometria` PROPÕE o retângulo medido, a
ferramenta desenha, o usuário dá ENTER ou corrige.

**E o import da tool sobre o módulo puro** — `_selecionar_regiao`/`_gravar_conferencia` vêm de
`calibrar.py` (`calibrar_mercado.py:63-68`):
```python
from .calibrar import (  # noqa: E402
    ARQUIVO_CALIBRACAO,
    RAIZ,
    _gravar_conferencia,
    _selecionar_regiao,
)
```

---

### `l2scanner/mercado_geometria.py` (MOD — `nivel_de_fundo_da_linha`)

**Analog:** `fim_da_alternancia` no mesmo arquivo (`mercado_geometria.py:437-486` é a região
de `medir_a_grade` que a chama; a folga de 2 linhas está em `:470-472`).

O padrão da função nova: recebe `cinza` + retângulo, devolve `(moda, dispersao)`, **retorna
`None` em vez de levantar** quando não dá para medir — como todo o arquivo faz:
```python
    faixa = extensao_do_separador(cinza, topo - 1)
    if faixa is None:
        return None
    esquerda, limite = faixa
    direita = fim_da_alternancia(cinza, cadeia, esquerda, limite)
    if direita is None or direita <= esquerda:
        direita = limite
    if direita - esquerda < 2:
        return None
```
**O limiar de dispersão NÃO mora aqui** — a geometria mede, `mercado_leitura.py` decide.

---

### Testes (`tests/test_mercado_leitura.py`, `test_mercado_catalogo.py`, `test_mercado_pagina.py`)

**Analog primário:** `tests/test_mercado_glifos.py` — o teste que roda sobre fixtures
versionadas resgatadas de `recordings/`.

**Cabeçalho que declara o material e a razão** (`test_mercado_glifos.py:1-16`):
```python
"""O corte de glifos: a metade PURA, afirmada contra pixels REAIS do jogo.

Tudo aqui roda sobre duas fixtures RESGATADAS de uma gravacao de verdade
(`recordings/20260828-060622-mercado-pagina-cheia/frame_000010.png`), e nunca
sobre `recordings/` — a pasta e gitignored e nao vem de clone limpo, entao um
teste que dependesse dela ficaria verde nesta maquina e amarelo em toda outra.

    tests/fixtures/mercado/glifos_precos_f010.png     240x45 px, coluna Total
"""
FIXTURES = Path(__file__).parent / "fixtures" / "mercado"
```

**Como um teste PODE citar `recordings/` — o skip explícito** (`test_mercado_27x.py:50` e `:268-278`):
```python
RECORDINGS = Path(__file__).resolve().parents[1] / "recordings"
...
class TestOReplayCOMPLETO:
    """Os 45 recortes e os 10 frames de janela — so onde `recordings/` existe."""

    def test_o_replay_completo_nao_e_afirmavel_num_clone_limpo(self):
        if not (RECORDINGS / "inv3").is_dir():
            pytest.skip(
                "recordings/inv3/ e gitignored e nao se materializa num "
                "worktree nem num clone limpo. As duas metades acima rodam "
                "sobre as fixtures VERSIONADAS resgatadas de la."
            )
```
**A regra derivada, e ela decide o plano:** todo critério de sucesso desta fase que precise ser
verde num worktree tem de vir de fixture VERSIONADA em `tests/fixtures/mercado/`. O replay das
335 gravações vive atrás de `pytest.skip`.

**O que NÃO se prende em teste** (`test_mercado_glifos.py:33-39`):
> *"QUAL par e o pior. Ele muda de convencao para convencao ... e prende-lo transformaria um
> detalhe de recorte em promessa. O que se afirma e a RELACAO ... mais a FAIXA de valores."*

**`tests/conftest.py`** já cala o log nativo do OpenCV — nada a acrescentar; testes novos
herdam.

**Onde os testes desta fase são especiais:** `pytest` roda no Python GLOBAL, que **não** tem
WinRT. Todo teste que toque OCR precisa do padrão de dublê já usado por `VigiaDeManutencao`
(`_ler_texto` e `_ler_texto_conferencia` são injetados no `__init__`, `manutencao.py:384-402`)
— **injeção de leitora, não monkeypatch de módulo.** É o mesmo desenho a replicar em
`mercado_pagina.py`.

---

## Shared Patterns

### 1. Mover a primitiva, não copiá-la — e o precedente é da Fase 1

**Source:** `l2scanner/calibrar_mercado.py:70-76`
**Apply to:** toda primitiva que migra de `calibrar_mercado.py` para `mercado_leitura.py`

```python
# A MESMA mascara de brilho ja medida para os nomes de party, e nao uma copia:
# ela carrega no docstring a razao de ser SO brilho (o nome do lider e amarelo e
# qualquer filtro de saturacao o rejeitava). A propriedade que valia para o
# amarelo do lider vale aqui para o dourado do `Adena` e o ciano da linha
# destacada do mercado.
from .identidade import mascara_de_texto  # noqa: E402
```

**A mecânica completa do movimento, como o repositório já a executa (3 precedentes):**

| primitiva | mora em (puro) | quem importa (tool) | linha |
|---|---|---|---|
| `mascara_de_texto` | `identidade.py:134` | `calibrar_mercado.py` | `:76` |
| `medir_a_grade`, `localizar_o_titulo` | `mercado_geometria.py` | `calibrar_mercado.py` | `:77-82` |
| `casamento_da_ancora`, `glifos_de_calibracao` | `mercado_visao.py` | `calibrar_mercado.py` | `:83-91` |
| `ARQUIVO_CALIBRACAO`, `_selecionar_regiao` | `calibrar.py` | `calibrar_mercado.py` | `:63-68` |

**Nenhum módulo de produção importa `calibrar_mercado`** (`grep "import calibrar_mercado"
l2scanner/*.py` → vazio). A seta aponta sempre tool → puro. Isso é o que `mercado_leitura.py`
precisa preservar, e é por isso que a promoção é MOVER, não copiar.

**Checklist do movimento, por primitiva:**
1. Cortar a função INTEIRA com a docstring — a docstring é onde a medição que a justifica vive.
2. Colar em `mercado_leitura.py`.
3. Em `calibrar_mercado.py`, adicionar ao bloco `from .mercado_leitura import (...)  # noqa: E402`.
4. Em `tests/test_mercado_glifos.py:51-58`, trocar a origem do import (o teste existente é o
   detector de regressão do movimento — ele importa `_alinhar_por_preenchimento`,
   `_par_incalculavel`, `segmentar_glifos`, `recortar_sufixo` de `calibrar_mercado`).
5. Rodar a suíte: baseline **1704 passed, 2 skipped**.

### 2. Constante medida, com a medição refutada preservada ao lado

**Source:** `calibrar_mercado.py:1358-1387` e `ocr.py:34-52`
**Apply to:** todo número novo desta fase (corte de similaridade, limiar de dispersão da sonda,
piso/margem de leitura de glifo, `V > 210` do cabeçalho)

```python
# OS NUMEROS SAO MEDIDOS, e a primeira tentativa (piso unico de 0.95) foi
# derrubada pela medicao. Eu supus que o mesmo digito no mesmo frame casaria
# 1.000 por ser o mesmo desenho. Ele nao casa: o FUNDO da linha alterna entre 48
# e 66 ...
#     acerto  PIOR    0.837  (o `9` contra o `9` da linha de fundo oposto)
#     ERRO    MELHOR  0.717  (o `5` contra o `6`)
# Com 0.95 a ferramenta nao propunha NADA -- feature morta e ninguem saberia.
MINIMO_PARA_PROPOR_ROTULO = 0.80
MARGEM_MINIMA_PARA_PROPOR = 0.12
```
E a forma de registrar uma refutação (`ocr.py:36-39`):
```python
# ESTA TABELA SUBSTITUI UMA MEDICAO ANTERIOR QUE FOI REFUTADA. O registro da
# refutacao fica aqui de proposito: este projeto documenta numero medido, e um
# numero que caiu precisa dizer que caiu, senao ele volta na proxima leitura.
```
**Consequência dura para o plano:** o corte de similaridade e o limiar de dispersão **não
podem ser escritos antes da onda de medição**. E `mercado_limiar_de_glifo = 0.8555` não é
piso de leitura (Pitfall 1 da pesquisa).

### 3. Argmax + margem, nunca piso absoluto

**Source:** `identidade.py:109-113`
**Apply to:** classificação de glifo e casamento do molde de cabeçalho
```python
# Abaixo disto, nao afirmamos quem e. Fica bem acima do melhor caso de nomes
# diferentes (0.454) e bem abaixo do pior caso do mesmo nome (1.000).
LIMIAR_DE_CASAMENTO = 0.75

# Se o segundo melhor chega perto do primeiro, o casamento nao e confiavel.
# Melhor dizer "nao sei" do que apontar o nome errado com confianca.
MARGEM_MINIMA_SOBRE_O_SEGUNDO = 0.12
```

### 4. Feature OFF é o default seguro; ausência de calibração nunca derruba o produto

**Source:** `mercado_visao.py:465-467` + `ocr.py:116-122`
```python
    Sem ancora nenhuma (instalacao que nunca calibrou o mercado) ele nunca abre
    — a feature fica OFF, que e o unico padrao seguro para um sinal que a Fase 4
    vai usar perto do detector de morte.
```
```python
def _checar() -> None:
    """Descobre PREGUICOSAMENTE se da para usar o OCR.

    Preguicosamente porque importar este modulo nao pode custar o import do
    WinRT: quem so carrega o scanner e nunca liga o recurso nao deve pagar nada
    — nem tempo, nem risco de um import estranho derrubar o arranque.
    """
```
`calibration.json` sem a coluna do nome → a leitura de mercado simplesmente não acontece, com
aviso alto. Nunca `raise` no arranque.

### 5. Toda mensagem de erro diz o CONSERTO

**Source:** `ocr.py:88-98`, `mercado_visao.py:695-741`, `calibracao.py:445-449`
```python
SEM_BINDINGS = (
    "As bibliotecas de OCR do Windows nao estao instaladas neste ambiente.\n"
    "  Conserto: rode o vigiar-party.bat uma vez — ele reinstala sozinho\n"
    "  (ou, na mao: pip install -r requirements.txt)."
)
```
```python
            raise CalibracaoInvalida(
                f"Nao encontrei {caminho}.\n"
                f"Rode a calibracao:  python -m l2scanner.calibrar"
            )
```

### 6. Firewall de escopo — a dependência nova passa por teste

**Source:** `tests/test_firewall_escopo.py:60-113`
**Apply to:** a decisão `rapidfuzz` vs `difflib`. A banlist tem 9 nomes com normalização PEP
503 e varre o venv INSTALADO. `difflib` (stdlib) não passa nem perto disso — é mais um
argumento a favor da decisão já travada no CONTEXT.md revisado.

---

## No Analog Found

| Arquivo | Role | Data Flow | Motivo |
|---|---|---|---|
| `mercado_catalogo.py` — o **formato CSV** | file-I/O | append | `import csv` não existe em lugar nenhum do repositório. Analog cobre caminho/atomicidade/leitura defensiva, não o dialeto. A Fase 3 (separador `;`) vai herdar o que esta fase decidir — **escolher aqui vale por dois**. |
| A **trava de dígitos** do agrupamento de nome (`+6` ≠ `+4`, `Lv. 1` ≠ `Lv. 3`) | transform | — | Regra nova, sem precedente. O mais próximo em espírito é `manutencao._normalizar_digitos` (`manutencao.py:133`) — normaliza dígito lido por OCR — mas resolve o problema oposto. Usar RESEARCH.md §3. |
| A **ferramenta de medição do corte** (Wave 0) | tool / one-shot | batch sobre `recordings/` | Precedente parcial: `tools/conferir_gravacoes_do_spike.py` (citado em `gravador.py:110`) e `tests/test_conferir_gravacoes_do_spike.py`. É uma tool de medição que lê `recordings/` e imprime histograma; nenhuma existente faz exatamente isso. |

---

## Metadata

**Analog search scope:** `l2scanner/` (28 módulos, 18.371 linhas), `tests/` (42 arquivos),
`tests/fixtures/mercado/` (26 PNGs versionados)
**Files scanned:** 12 lidos por trecho dirigido
**Analogs extraídos:** `calibrar_mercado.py`, `mercado_geometria.py`, `mercado_visao.py`,
`identidade.py`, `ocr.py`, `manutencao.py`, `loot.py`, `calibracao.py`, `gravador.py`,
`config.py`, `test_mercado_glifos.py`, `test_mercado_27x.py`, `conftest.py`
**Pattern extraction date:** 2026-08-29
