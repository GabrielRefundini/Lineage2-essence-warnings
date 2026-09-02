# Fase 1: Dashboard do cambio ao vivo — Mapa de Padroes

**Mapeado:** 2026-09-01
**Arquivos analisados:** 14 a criar/alterar
**Analogos encontrados:** 9 / 14 (5 sem analogo — nao ha codigo web nesta arvore)

> **Como este documento e usado.** O planejador cita a linha `arquivo:linha` do analogo dentro da
> acao do plano. Onde a coluna diz "sem analogo", o que esta escrito e a **convencao** que o
> arquivo novo tem de seguir, e nao um arquivo para copiar — dizer "copie de X" quando X nao
> existe e pior que dizer "nao existe".

---

## File Classification

| Arquivo novo/alterado | Papel | Fluxo de dado | Analogo mais proximo | Qualidade |
|---|---|---|---|---|
| `l2scanner/raiz.py` | config (modulo-folha) | constante | `l2scanner/config.py:48` (`RAIZ = Path(...)`) | exato (extracao literal) |
| `l2scanner/mercado_catalogo.py` (1 linha) | config | — | `mercado_registro.py:70` (importa em vez de redefinir) | exato |
| `l2scanner/dashboard.py` — servidor HTTP | service / servidor | request-response | **sem analogo** (nao ha servidor na arvore) → forma medida em `01-RESEARCH.md:482-527` | sem analogo |
| `l2scanner/dashboard.py` — leitor ao vivo do CSV | service | file-I/O (somente leitura) | `mercado_registro.observacoes_do_arquivo` (`:516-605`) | exato |
| `l2scanner/dashboard.py` — cambio XM→BRL | model + persistencia | file-I/O (escrita atomica) | `calibracao.py:764-768` e `loot.py:263-280` | exato |
| `l2scanner/dashboard.py` — agregacao por balde | utility (puro) | transform | `mercado_analise.mediana_dos_unitarios` (`:341-373`) | exato |
| `l2scanner/dashboard.py` — montagem do JSON exibido | service | transform | `mercado_console._linha_do_menor` / `_linha_da_mediana` (`:522-598`) | exato |
| `l2scanner/recursos/dashboard/index.html` | view | static | **sem analogo** (`.html` zero na arvore) | sem analogo |
| `l2scanner/recursos/dashboard/dashboard.css` | view | static | **sem analogo** | sem analogo |
| `l2scanner/recursos/dashboard/dashboard.js` | view/controller | request-response (polling) | **sem analogo** | sem analogo |
| `l2scanner/recursos/dashboard/vendor/uplot.min.js` + `.LICENSE` + `README.md` | vendor | static | **sem analogo** — VEND-1..4 do UI-SPEC | sem analogo |
| `dashboard.bat` | launcher | — | `vigiar-mercado.bat` | exato |
| `tests/test_firewall_dashboard.py` | test | — | `tests/test_firewall_escopo.py` (FIRE-01) | exato |
| `tests/test_dashboard*.py` | test | — | `tests/test_mercado_analise.py` + `tests/test_mercado_registro.py` | exato |

---

## Pattern Assignments

### `l2scanner/raiz.py` + a linha de `mercado_catalogo.py` (config, folha)

**Analogo:** `l2scanner/config.py:48`

A definicao atual, que sai inteira para o modulo-folha:

```python
RAIZ = Path(__file__).resolve().parent.parent
```

**O ponto de consumo a trocar** — `l2scanner/mercado_catalogo.py:95`:

```python
from .config import RAIZ          # ANTES
from .raiz import RAIZ            # DEPOIS
```

E o uso, intocado, em `mercado_catalogo.py:670`:

```python
PASTA_DO_MERCADO = RAIZ / ".mercado"
```

**Padrao de "importar em vez de redefinir"** — a doutrina que autoriza o modulo-folha esta escrita
em `mercado_registro.py:65-70`, e o planejador deve reusar a mesma frase no `raiz.py`:

```python
# IMPORTADOS, E NAO REDEFINIDOS. Duas definicoes do mesmo ponto-e-virgula e como
# elas divergem: bastaria um dos dois arquivos mudar de dialeto para a pasta
# `.mercado/` passar a ter dois formatos e nenhum aviso.
from .mercado_catalogo import PASTA_DO_MERCADO, SEPARADOR
```

`config.py` deve **re-exportar** `RAIZ` (`from .raiz import RAIZ`) para nenhum consumidor existente
quebrar — e essa re-exportacao e o que mantem DASH-06 como "comportamento identico".

---

### O leitor ao vivo do CSV (service, file-I/O somente leitura)

**Analogo:** `l2scanner/mercado_registro.py:516-605` — `observacoes_do_arquivo`. **Nao e um parser
novo, e nao pode virar um.**

O corpo inteiro, que e o que o leitor ao vivo tem de **chamar**, nunca reescrever
(`mercado_registro.py:583-605`):

```python
    try:
        with arquivo.open("r", encoding="utf-8", newline="") as fonte:
            bruto = fonte.read()
    except FileNotFoundError:
        return []

    if not bruto:
        return []

    conferir_o_terminador(bruto, arquivo)
    linhas = list(csv.reader(io.StringIO(bruto, newline=""), delimiter=SEPARADOR))
    conferir_o_cabecalho(linhas, arquivo)
```

**Os dois portoes, como funcoes de modulo** (`mercado_registro.py:412` e `:480`) — eles existem
FORA da classe exatamente para haver um segundo chamador sem uma segunda implementacao:

```python
def conferir_o_terminador(bruto: str, arquivo: Path) -> None:
    if bruto.endswith("\n"):
        return
    cauda = bruto[bruto.rfind("\n") + 1 :]
    ...
    raise ContratoDoArquivoQuebrado(mensagem % (arquivo, cauda))


def conferir_o_cabecalho(linhas: list[list[str]], arquivo: Path) -> None:
    encontrado = tuple(campo.strip() for campo in linhas[0]) if linhas else ()
    if encontrado == COLUNAS:
        return
    ...
    raise ContratoDoArquivoQuebrado(mensagem % (arquivo, COLUNAS, encontrado))
```

**A divergencia que este arquivo tem de declarar no proprio fonte.** O dashboard corta em
`rfind("\n")` **antes** de chamar `conferir_o_terminador` — ou seja, ele deliberadamente **nao**
falha fechado no terminador, ao contrario do escritor. O molde de como se escreve uma divergencia
assim esta no proprio `conferir_o_terminador` (`mercado_registro.py:428-471`), que lista as duas
saidas recusadas com o motivo:

```
    AS DUAS OUTRAS SAIDAS FORAM CONSIDERADAS E RECUSADAS, e um numero que
    caiu precisa dizer que caiu:

    (a) REMOVER A CAUDA DO DISCO (truncar ate a ultima quebra de linha).
        Seria o programa apagando bytes do usuario num caminho de LEITURA. ...

    (b) COMPLETAR A CAUDA COM UMA QUEBRA DE LINHA antes do proximo append.
        E a PIOR das tres, porque preserva a linha possivelmente truncada E
        A PROMOVE ...

    CUSTO ACEITO, E ELE E REAL: ...
```

O `dashboard.py` escreve o par simetrico: **por que o corte antes do portao e correto na leitura**
(o escritor abre/escreve/fecha por linha — 0 leituras parciais em 22.970 tentativas medidas na
`01-RESEARCH.md`), e **que a regra continua sendo rede de seguranca, nao caminho normal**.

**A linha ruim que cai sozinha, e o log que NOMEIA o numero dela**
(`mercado_registro.py:577-582`) — o dashboard reusa isso, nao inventa outro nivel de log:

```python
            log.warning(
                "Observacoes, linha %d DESCARTADA na leitura da analise (%s): "
                "%r. As demais linhas do arquivo carregaram normalmente — uma "
                "linha ruim nunca condena o arquivo inteiro.",
                numero, erro, SEPARADOR.join(campos),
            )
```

---

### A agregacao por balde de tempo (utility, transform, pura)

**Analogo:** `l2scanner/mercado_analise.py:341-373` — `mediana_dos_unitarios`.

O corpo, que estabelece as tres regras que o bucketizador herda (piso → `Fraction` → `median_low`):

```python
    comparaveis = _comparaveis(observacoes)
    evidencia = Evidencia(n=len(comparaveis), piso=N_MINIMO_PARA_MEDIANA)
    if not evidencia.suficiente:
        return MedianaDosUnitarios(evidencia=evidencia, unitario=None)

    unitarios = [
        unitario(obs.total_em_centesimos, obs.quantidade) for obs in comparaveis
    ]
    return MedianaDosUnitarios(
        evidencia=evidencia, unitario=statistics.median_low(unitarios)
    )
```

**`Evidencia` viaja DENTRO do resultado, nunca ao lado** (`mercado_analise.py:226-254`) — o
`dataclass` de cada ponto agregado do grafico tem de ter a mesma forma:

```python
@dataclass(frozen=True)
class Evidencia:
    n: int
    piso: int

    @property
    def suficiente(self) -> bool:
        return self.n >= self.piso

    @property
    def faltam(self) -> int:
        """Quantas ofertas distintas ainda faltam para o piso. Zero se ja da."""
        return max(0, self.piso - self.n)
```

**O comparavel exato** (`mercado_analise.py:178-207`) — nenhuma conta do dashboard pode usar
`float`:

```python
def unitario(total_em_centesimos: int, quantidade: int) -> Fraction:
    if quantidade <= 0:
        raise ValueError(
            f"quantidade tem de ser positiva para haver unitario, veio {quantidade}"
        )
    return Fraction(total_em_centesimos, quantidade)
```

**Os pisos, declarados como ESCOLHA** (`mercado_analise.py:152/162/170`) — `N_MINIMO_PARA_MENOR = 1`,
`N_MINIMO_PARA_MEDIANA = 5`, `N_MINIMO_PARA_TENDENCIA = 8`, cada um com o comentario
"ESCOLHA, NAO MEDICAO". Qualquer constante nova do dashboard (largura do balde, porta, intervalo de
polling) se escreve nesse mesmo molde.

**Os dois anti-padroes medidos** que o bucketizador tem de recusar por escrito:
`statistics.median` (inventa `13/42` sobre uma lista que nao o contem) e `total_seconds()`
(devolve `float 69713.696`; use `(t - epoca) // largura`, que devolve `int 69713`).

---

### A montagem do JSON exibido (service, transform)

**Analogo:** `l2scanner/mercado_console.py:522-598` — `_linha_do_menor` e `_linha_da_mediana`. O
endpoint devolve **as mesmas strings**, montadas pelas mesmas funcoes.

O ponto de decisao unico, que o dashboard **chama** e nao replica
(`mercado_console.py:305-322`):

```python
def formatador_do_unitario(chave_da_serie: str):
    """A serie -> qual das duas irmas a desenha. UM ponto de decisao, e so um.

    QUATRO `if` ESPALHADOS PELOS QUATRO PONTOS DE CHAMADA DIVERGIRIAM, e o dia
    em que um deles divergisse ele imprimiria `0,00` ...
    """
    if chave_da_serie == CHAVE_DA_SERIE_DA_ADENA:
        return formatar_taxa_derivada
    return formatar_unitario_derivado
```

A string do destaque de XM (`mercado_console.py:265,301-304`):

```python
UNIDADE_DA_TAXA = 1_000_000

    return (
        f"{formatar_centesimos(round(taxa * UNIDADE_DA_TAXA))} "
        f"XM por milhao de adena (derivado)"
    )
```

A recencia em duas formas (`mercado_console.py:500-521`) — o JSON entrega isto pronto, em ASCII, e
o JS **exibe como recebeu**:

```python
    segundos = (agora - quando).total_seconds()
    absoluta = quando.strftime("%d/%m %H:%M")
    if segundos < 60:
        return f"agora mesmo ({absoluta})"
    if segundos < 3600:
        return f"ha {int(segundos // 60)} min ({absoluta})"
    if segundos < 86400:
        return f"ha {int(segundos // 3600)} h ({absoluta})"
    return f"ha {int(segundos // 86400)} dias ({absoluta})"
```

E a frase de piso, que substitui o numero quando a evidencia nao chega
(`mercado_console.py:588-593`) — e exatamente ela que a UI mostra na maior parte do grafico hoje:

```python
        return (
            f"    mediana: sem evidencia - {mediana.evidencia.n} de "
            f"{mediana.evidencia.piso} ofertas distintas, faltam "
            f"{mediana.evidencia.faltam}"
        )
```

---

### O escritor do `.mercado/cambio.json` (persistencia, file-I/O)

**Analogo primario:** `l2scanner/calibracao.py:764-768`. **Analogo secundario** (pid no nome do
temporario, para duas instancias): `l2scanner/loot.py:269-280`.

```python
        temporario = caminho.with_name(caminho.name + ".tmp")
        temporario.write_text(
            json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        os.replace(temporario, caminho)
```

O comentario que acompanha (`calibracao.py:745-763`) e o molde da justificativa, e a frase
operacional a reusar e:

> `os.replace` e atomico no mesmo volume: ou fica o arquivo antigo inteiro, ou o novo inteiro.
> Nunca meio. O temporario vive ao lado do destino, e nao no `%TEMP%`, porque `os.replace` entre
> volumes diferentes nao e atomico (e no Windows nem funciona).

A variante do `loot.py:269` para o caso de duas abas/processos:

```python
        temporario = self._pasta / f"{_ARQUIVO_PROXIMO}.tmp-{os.getpid()}"
```

**Estrutura de append com carimbo** — `loot.py:271-278` ja mostra o formato de registro carimbado
(`isoformat()` para cada campo de tempo); o `cambio.json` e uma lista desses, e o ultimo vence.

---

### `dashboard.bat` (launcher)

**Analogo:** `vigiar-mercado.bat`. Copiar **a estrutura**, nao o conteudo — o dashboard nao mira
janela, nao faz OCR e (apos o corte de `RAIZ`) nao precisa do `.venv`.

Descoberta do Python, incluindo a recusa do stub da Microsoft Store
(`vigiar-mercado.bat:52-62`):

```bat
set "PY="
for /f "delims=" %%i in ('where py 2^>nul') do if not defined PY set "PY=%%i"
if not defined PY for /f "delims=" %%i in ('where python 2^>nul') do if not defined PY set "PY=%%i"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Launcher\py.exe"
...
REM O alias da Microsoft Store e um stub que so abre a loja -- nao serve.
if defined PY if not "%PY%"=="%PY:WindowsApps=%" set "PY="
```

**A regra estrutural, e ela e o coracao do molde** (`vigiar-mercado.bat:129-136`):

```bat
REM OS BLOCOS DE ERRO VEM ANTES DA LINHA DE EXECUCAO, e nao depois dela.
REM Nao e estilo: e o que torna ESTRUTURAL a promessa de que nada e impresso
REM depois de o programa rodar. O defeito medido em campo no
REM calibrar-mercado.bat, em 2026-08-28, foi exatamente um bloco de
REM encerramento saindo depois de a ferramenta ter saido em codigo 1 --
REM anunciando um desfecho que o .bat nao conferiu.
goto executar

:erro_venv
...
exit /b 1

:executar
".venv\Scripts\python.exe" -m l2scanner --mercado --janela "%JANELA%" %*
```

O bloco de `.venv` (`:75-87`) e a sonda de dependencias (`:96-105`) **saem** do `dashboard.bat`:
com o corte de `RAIZ` o dashboard e stdlib puro. Isso e DASH-06 virando estrutura.

**O teste do .bat ja tem molde tambem** — `tests/test_vigiar_mercado_bat.py:53-78` traz
`_linhas_de_echo` e `_posicao_da_execucao`, e a leitura em `cp1252` (`_texto()`), com o teste
`test_o_bat_e_ascii_puro`.

---

### `tests/test_firewall_dashboard.py` (VEND-3)

**Analogo:** `tests/test_firewall_escopo.py` (FIRE-01). O molde tem quatro pecas, e a quarta e a
que o planejador nao pode esquecer.

**1. Banlist nomeada e ampla** (`test_firewall_escopo.py:70-80`) — aqui vira a lista de primitivas
de rede do VEND-2 (`fetch(`, `XMLHttpRequest`, `navigator.sendBeacon`, `eval(`, `new Function`,
`import(`, `document.createElement('script')`).

**2. Uma funcao PURA como unico ponto de decisao** (`:107-113`):

```python
def _banidas_presentes(nomes: set[str]) -> set[str]:
    """O UNICO ponto de decisao do modulo — e por isso o alvo da mutacao.

    Manter a decisao numa funcao pura e o que permite provar que o detector
    acusa sem instalar nada de verdade.
    """
    return {_normalizar(nome) for nome in nomes} & BANIDAS
```

**3. Mensagem de falha que explica o porque e aponta o documento** (`:115-131`), com o teste
`test_a_mensagem_de_falha_explica_o_porque` (`:383`) prendendo isso.

**4. O CONTROLE NEGATIVO — a prova de que o guarda reprova** (`:261-276`):

```python
def test_o_detector_acusa_uma_distribuicao_banida_injetada() -> None:
    """A prova do vermelho SEM instalar nada.

    Sem este teste, um bug no normalizador (ou uma banlist vazia por acidente
    numa refatoracao) deixaria as tres varreduras acima verdes para sempre, e
    o firewall viraria teatro de controle. A mutacao acontece na entrada da
    funcao pura de decisao, nao no ambiente.
    """
    assert _banidas_presentes({"numpy", "opencv-python", "keyboard"}) == {"keyboard"}
    assert _banidas_presentes({"numpy", "opencv-python"}) == set()
```

O `test_firewall_dashboard.py` precisa do equivalente: alimentar a funcao pura com um trecho
fabricado contendo `fetch(` e exigir que ela acuse. **Sem isso, um `grep` sobre um `vendor/` vazio
fica verde para sempre.** A doutrina da casa esta escrita em
`tests/test_mercado_firewall_de_fase.py:452-470`: "ao lado da afirmacao, o CONTROLE NEGATIVO que
prova que o guarda reprova quando o fato acontece".

**Peca extra desta fase, do mesmo molde:** `test_o_requirements_nao_ganhou_linha_nesta_fase`
(`test_mercado_firewall_de_fase.py:438-440`), com a lista de distribuicoes escrita **a mao**:

```python
class TestNenhumaDependenciaNova:
    def test_o_requirements_nao_ganhou_linha_nesta_fase(self) -> None:
        assert _distribuicoes_declaradas() == DISTRIBUICOES_ANTES_DA_FASE_4
```

> Comentario em `:400-403`: "A lista esta escrita a mao de proposito: deriva-la do proprio arquivo
> faria o teste concordar com qualquer coisa que alguem acrescentasse."

---

### `tests/test_dashboard*.py` (testes de endpoint, leitor, cambio, agregacao)

**Analogos:** `tests/test_mercado_analise.py` e `tests/test_mercado_registro.py`.

**Nomes em portugues, descritivos, com a asserção em CAIXA ALTA no ponto que importa**
(`test_mercado_analise.py:92-166`):

```
test_os_numeros_voltam_INTEIROS_e_o_carimbo_volta_DATETIME
test_o_ultimo_byte_cortado_deixa_seis_campos_PARSEAVEIS_e_ainda_LEVANTA
test_arquivo_AUSENTE_devolve_lista_vazia_sem_levantar
test_a_leitura_NAO_CRIA_o_arquivo_ausente
test_o_aviso_NOMEIA_o_numero_da_linha
```

**Agrupamento por `class Test...` sem herança**, uma classe por invariante
(`TestOPortaoDeContratoEOMESMO`, `TestUmaLinhaRuimCaiSOZINHA`, `TestOResiduoQueNaoColapsa`).

**`tmp_path` sempre; nunca a `.mercado/` real** (`test_mercado_registro.py:3-8`):

> NADA AQUI TOCA A `.mercado/` REAL. Toda instancia recebe `tmp_path` ... um teste que escrevesse
> na pasta de producao contaminaria dado ACUMULADO e sem poda — nao ha desfazer.

**Construtor de fixture a mao, sem disco nem frame** (`test_mercado_analise.py:283-300`):

```python
def _oferta(
    *, chave: str = "common-aztac#0", nome: str = "Common Aztac",
    carimbo: datetime = AGORA, total: int = 6200, quantidade: int = 48,
    residuo: int | None = 0,
) -> ObservacaoLida:
    """Uma oferta montada a mao — a analise nunca precisa de disco nem de frame."""
    return ObservacaoLida(...)
```

**Tripwire de arquitetura por leitura de fonte** — o molde exato para provar DASH-01
("o dashboard nunca abre o CSV para escrita"), em `test_mercado_analise.py:261-268`:

```python
    def test_a_leitura_nova_NAO_abre_o_arquivo_para_escrita(self):
        import inspect
        from l2scanner import mercado_registro

        fonte = inspect.getsource(mercado_registro.observacoes_do_arquivo)
        assert '"w"' not in fonte and '"a"' not in fonte
        assert "mkdir" not in fonte
```

**Tripwire de import por AST** — `tests/test_mercado_firewall_de_fase.py:250-271`
(`_modulos_importados`), que enxerga inclusive os imports adiados dentro de funcao. E o
instrumento correto para provar que `dashboard.py` nao arrasta `cv2`/`numpy`/`mss`.

---

### Os arquivos web — SEM ANALOGO, e isso e medido

`index.html`, `dashboard.css`, `dashboard.js`, `vendor/*`: **nao existe um unico `.css`/`.html`/`.js`
fora do `.venv` nesta arvore** (`01-UI-SPEC.md`, tabela "Estado do projeto"). Nao ha de onde copiar
padrao, e forcar um analogo Python aqui seria ruido.

O que substitui o analogo, e o que o plano deve citar no lugar:

| Arquivo | Contrato prescritivo a seguir |
|---|---|
| `index.html` | `01-UI-SPEC.md` § Layout & Componentes (tres regioes `#destaque`/`#serie`/`#procedencia`); **sem `<script>` e sem `<style>` inline**, exigido pela CSP |
| `dashboard.css` | `01-UI-SPEC.md` § Color (bloco de tokens — **unica declaracao de cor do projeto**), § Spacing Scale, § Typography, e a receita de relevo pronta em CSS |
| `dashboard.js` | `01-UI-SPEC.md` § "O grafico e tematizado pela superficie da propria biblioteca" (`getPropertyValue`); **nenhum literal hexadecimal**; **nenhuma reescrita das strings vindas do Python** |
| `vendor/README.md` | VEND-1: nome, versao, licenca, URL, data, **SHA-256**; VEND-2: nota de revisao com `arquivo:linha` |

---

## Shared Patterns

### 1. Refutacao mora no fonte

**Fonte:** `l2scanner/mercado_registro.py:19-28` (cabecalho do modulo) e `:428-471` (docstring de
`conferir_o_terminador`).
**Aplicar a:** `dashboard.py` (todos os submodulos), `vendor/README.md`.

```
UM NUMERO QUE CAIU PRECISA DIZER QUE CAIU: o plano cobrava a forma mais forte
disto — `cv2` e `numpy` ausentes de `sys.modules` depois do import. Medido:
IMPOSSIVEL, e nao por culpa deste modulo. ... Ficou a que da para afirmar e que
mede a mesma coisa ...
```

As duas refutacoes que **esta fase e obrigada a escrever no fonte**:

1. **No leitor ao vivo:** que ele diverge do portao do terminador (corta em `rfind("\n")` antes),
   por que isso e correto na leitura e errado na escrita, e a medicao (0 leituras parciais em
   22.970 tentativas — o escritor abre/escreve/fecha por linha).
2. **Ao lado do wheel-zoom em `dashboard.js`:** que o UI-SPEC supos "toda biblioteca dessa classe
   faz wheel zoom por config" e a medicao **refutou** — uPlot registra **zero** listeners de
   `wheel`, dygraphs zero, e a documentacao oficial do uPlot diz "No built-in drag
   scrolling/panning". As ~30 linhas de hooks sao consequencia disso, e nao capricho.

### 2. Todo numero exibido carrega `n` e recencia, e o derivado diz que e derivado

**Fonte:** `mercado_analise.py:226-254` (`Evidencia` dentro do resultado) + `mercado_console.py:301`
(o sufixo `(derivado)`).
**Aplicar a:** toda chave do JSON servido e todo cartao do `#destaque`.

### 3. `Fraction` na conta, arredondamento so na formatacao

**Fonte:** `mercado_analise.py:178-207` e `mercado_console.py:219-229`:

```python
def formatar_centesimos(centesimos: int) -> str:
    inteiro, resto = divmod(int(centesimos), 100)
    return f"{inteiro:,}".replace(",", ".") + f",{resto:02d}"
```

**Aplicar a:** agregacao, cambio, e a fronteira do JSON — onde o `float` aparece (JSON nao tem
`Fraction`), isso e **declarado em voz alta no fonte**, no ponto exato da conversao.

### 4. Falha fechada com mensagem que diz O QUE FAZER

**Fonte:** `mercado_registro.py:472-479` e `:502-515`. Toda mensagem tem a mesma anatomia:
`ESTADO DESLIGADO — <o que> ... NENHUM byte foi alterado ... O QUE FAZER: <passo> ... Enquanto
isso, <o que continua funcionando>`.
**Aplicar a:** as tres mensagens de erro do `## Copywriting Contract` (arquivo ausente, cabecalho
quebrado, cambio invalido) e a recusa do bind duplo (`OSError` errno 10048).

### 5. Escrita atomica por temporario + `os.replace`

**Fonte:** `calibracao.py:764-768`, `loot.py:269-280`, `acervo.py:534-549`. Tres escritores, um
padrao. **Aplicar a:** `cambio.json` — o unico arquivo que este processo escreve.

### 6. Texto do usuario em ASCII, sem acento

**Fonte:** `mercado_registro.py:299-301`:

> SEM ACENTO, como todo texto que este projeto poe na frente do usuario: o console do Windows abre
> em cp1252 e a mesma frase acaba colada num log, numa mensagem de erro e num editor qualquer.

**Aplicar a:** tudo que sai do Python. O HTML/CSS/JS **leva acento** (UTF-8), e essa divergencia e
intencional e fica escrita no fonte — ver `01-UI-SPEC.md` § Copywriting Contract.

---

## O tripwire quebrado que esta fase tem de consertar

**Arquivo:** `tests/test_mercado_firewall_de_fase.py:315-346` —
`test_o_rastreador_chega_por_uma_CADEIA_PREEXISTENTE_do_config`.

A docstring promete: *"Se a cadeia for cortada um dia, ele cai e obriga quem cortou a atualizar a
historia."* O corpo nao cumpre:

```python
        codigo = (
            "import sys\n"
            "import l2scanner.config\n"
            "assert 'l2scanner.rastreador' in sys.modules\n"
            "import l2scanner.mercado_catalogo\n"
            "assert 'l2scanner.config' in sys.modules\n"
        )
        resultado = subprocess.run(
            [sys.executable, "-c", codigo],
            cwd=str(RAIZ), capture_output=True, text=True,
        )
        assert resultado.returncode == 0, resultado.stderr
```

**O defeito, ao pe da letra:** a segunda asserção (`'l2scanner.config' in sys.modules`) e
**tautologica** — `l2scanner.config` foi importado na linha 2 do proprio subprocesso, entao ela e
verdadeira independentemente de `mercado_catalogo` ainda importar `config` ou nao. Com o corte de
`RAIZ` aplicado, este teste **continua verde** e a historia que ele prende continua mentindo.

**O conserto** e importar `mercado_catalogo` **primeiro, num interpretador limpo**, e afirmar sobre
o que ELE trouxe:

```python
        codigo = (
            "import sys\n"
            "import l2scanner.mercado_catalogo\n"
            "assert 'l2scanner.config' not in sys.modules, sorted(sys.modules)\n"
            "assert 'l2scanner.rastreador' not in sys.modules\n"
            "assert 'cv2' not in sys.modules\n"
        )
```

Isto e o mesmo padrao de defeito que `tests/test_mercado_firewall_de_fase.py:449-470` ja nomeia
como "a OITAVA instancia do mesmo padrao de defeito na fase — um guarda cuja saida nao muda com o
fato que ele julga", com o antidoto escrito ali: o **controle negativo** ao lado da afirmacao. Esta
fase acrescenta a nona instancia a lista se o planejador nao a tratar como tarefa propria.

---

## No Analog Found

| Arquivo | Papel | Fluxo | Razao |
|---|---|---|---|
| `l2scanner/dashboard.py` (metade do servidor HTTP) | service | request-response | Nao ha nenhum servidor, socket ou handler HTTP nesta arvore. A forma medida esta em `01-RESEARCH.md:482-527` e deve ser copiada de la literalmente (`allow_reuse_address = False`, `ThreadingHTTPServer`, `directory=`, `list_directory` desligado, cabecalho CSP em `end_headers`). |
| `l2scanner/recursos/dashboard/index.html` | view | static | Zero `.html` na arvore. Contrato: `01-UI-SPEC.md`. |
| `l2scanner/recursos/dashboard/dashboard.css` | view | static | Zero `.css` na arvore. Contrato: `01-UI-SPEC.md` § Color/Spacing/Typography. |
| `l2scanner/recursos/dashboard/dashboard.js` | view | polling | Zero `.js` autorado na arvore. Contrato: `01-UI-SPEC.md`. |
| `l2scanner/recursos/dashboard/vendor/*` | vendor | static | Primeiro artefato de terceiro vendorizado do projeto. Contrato: VEND-1..4 do `01-UI-SPEC.md` § Registry Safety. |

---

## Metadata

**Escopo da busca:** `l2scanner/` (49 modulos), `tests/` (93 arquivos), `*.bat` (9 lancadores),
`.planning/workstreams/dashboard/phases/01-*/`
**Analogos lidos por extenso:** `mercado_registro.py`, `mercado_analise.py`, `mercado_console.py`,
`test_firewall_escopo.py`, `test_mercado_firewall_de_fase.py`, `test_mercado_analise.py`,
`vigiar-mercado.bat`, `calibracao.py` (escritor), `loot.py` (escritor)
**Data da extracao:** 2026-09-01
