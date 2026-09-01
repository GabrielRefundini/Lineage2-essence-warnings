# Fase 1: Fundação — firewall, gravador e spike de campo — Pattern Map

**Mapeado:** 2026-08-27
**Arquivos analisados:** 12 (novos/modificados)
**Analogs encontrados:** 10 / 12 (2 são docs de fase, sem analog de código)

## File Classification

| Arquivo novo/modificado | Role | Data Flow | Analog mais próximo | Qualidade do match |
|---|---|---|---|---|
| `l2scanner/gravador.py` (fix imwrite + modo janela-completa) | service (I/O de disco) | file-I/O | `l2scanner/calibrar.py::_gravar_conferencia` (388-434) | exact — mesmo bug, fix já escrito |
| `l2scanner/__main__.py` (flag janela-completa + resumo honesto) | entrypoint/config | request-response (CLI) | ele mesmo: extras opcionais (1436-1442) e resumo (1703-1709) | exact |
| `tests/test_firewall_escopo.py` | test (controle estrutural) | batch (varredura) | `tests/test_conferencia_gravada.py::test_existe_um_unico_ponto_de_escrita_no_modulo` (217-227) + skip pattern | role-match |
| Testes do gravador (FUND-01) | test | file-I/O | `tests/test_conferencia_gravada.py` (inteiro) | exact |
| `ROTEIRO-SPIKE.md` | doc de fase | — | sem analog (checklist markdown, decisão travada) | — |
| `SPIKE-RESPOSTAS.md` | doc de fase | — | sem analog | — |
| `l2scanner/calibrar_mercado.py` | tool (calibração) | file-I/O + interativo | `l2scanner/calibrar.py` (selectROI 363-385; load-mutate-save 637-664; `_gravar_conferencia`) | exact |
| `calibrar-mercado.bat` | config/launcher | — | `calibrar-solo.bat` | exact |
| `l2scanner/calibracao.py` (chaves de mercado) | model/config | file-I/O (JSON) | padrão `banner_manutencao` no próprio módulo (196-213, 308-311, 357-365) | exact |
| `l2scanner/mercado_visao.py` | service puro (detecção) | transform (pixels → bool) | `l2scanner/identidade.py::_correlacionar` (187-212) + charter `visao.py:1-7` | exact |
| `l2scanner/visao.py` — campo novo em `Observacao` | model | transform | `Observacao.hp_proprio_aparente` / `estado_do_cliente` (79-118) | exact |
| Teste de regressão 27x + `tests/fixtures/mercado/` | test | batch (replay) | `tests/test_inventario_por_cima_da_barra_propria.py` (518-537, 858-935) | exact |

## Pattern Assignments

### `l2scanner/gravador.py` — fix do imwrite (FUND-01)

**Estado atual (o bug), `gravador.py:39-54`:**
```python
def gravar(self, frame: Frame, momento: float) -> None:
    import cv2
    caminho = self.pasta / f"frame_{frame.indice:06d}.png"
    cv2.imwrite(str(caminho), frame.pixels)        # retorno jogado fora
    linha = {"indice": frame.indice, "momento": momento,
             "saude": frame.saude.value, "arquivo": caminho.name}
    self._arquivo_meta.write(json.dumps(linha, ensure_ascii=False) + "\n")
    self._arquivo_meta.flush()
    self.frames_gravados += 1                      # conta a TENTATIVA
```
As três saídas (contador, linha do JSONL, resumo) precisam ficar condicionadas à escrita confirmada — não só o contador.

**Padrão de fix a copiar — `calibrar.py:407-415` (`_gravar_conferencia.tentar`):**
```python
def tentar(caminho: Path) -> bool:
    # O try/except existe ALEM do retorno booleano para que o `False`
    # documentado e uma excecao inesperada caiam no MESMO caminho de
    # falha. Tratar so um dos dois deixaria a outra metade calada, que e
    # exatamente o defeito que esta funcao veio consertar.
    try:
        return bool(cv2.imwrite(str(caminho), imagem))
    except Exception:  # noqa: BLE001
        return False
```
Nota de contexto de chamada: `Gravador.gravar` roda dentro de `Sessao.tick` (`sessao.py:199-200`) e o laço principal (`__main__.py:1615`) não tem try/except no tick — a falha NÃO pode levantar exceção; devolve `False`, incrementa `falhas_de_gravacao`, loga `log.error`.

**Modo janela-completa (FUND-02):** a fonte do frame completo já existe — `JanelaSource` recorta os extras do frame completo (`captura_janela.py:356-360`) e expõe `capturar_completo()` (usada em `calibrar.py:620`). O naming de pastas do gravador é `pasta_base/{YYYYmmdd-HHMMSS}-{rotulo}` (`gravador.py:28-32`) — os rótulos do ROTEIRO viram sufixos de pasta.

**Docstring com comportamento medido — estilo da casa (`calibrar.py:396-401`):** registrar no fonte que "destino somente-leitura, destino ocupado por diretório e pasta inexistente devolvem `False` e nenhum levanta exceção — medido nesta máquina".

---

### `l2scanner/__main__.py` — flag + resumo honesto

**Resumo final atual (`__main__.py:1703-1709`) — o ponto a mudar:**
```python
if gravador:
    gravador.fechar()
    log.info(
        "Sessao gravada: %d frames em %s",
        gravador.frames_gravados,
        gravador.pasta,
    )
```
Estender para reportar frames confirmados, falhas e a verdade do disco (`len(list(pasta.glob("frame_*.png")))`), no formato sugerido pela RESEARCH.

**Padrão de extra opcional (para o consumo da âncora do mercado no DETC-01) — `__main__.py:1436-1442`:**
```python
extras: dict[str, Regiao] = {}
if cal.hp_proprio:
    extras["hp_proprio"] = cal.hp_proprio
if vigia_manutencao is not None:
    extras["banner_manutencao"] = cal.regiao_do_banner(
        na_janela=bool(args.janela)
    )
```
A região da âncora do mercado só entra no dict quando a calibração tem a chave — trilho literal do `banner_manutencao`.

---

### `tests/test_firewall_escopo.py` (FIRE-01)

**Sem analog direto de varredura de dependências** — o esqueleto verificado está na RESEARCH (Descoberta 4). Padrões de teste a copiar:

**Tripwire estrutural por leitura do fonte — `test_conferencia_gravada.py:217-227`:**
```python
def test_existe_um_unico_ponto_de_escrita_no_modulo() -> None:
    total = inspect.getsource(l2scanner.calibrar).count("imwrite")
    no_auxiliar = inspect.getsource(_gravar_conferencia).count("imwrite")
    assert no_auxiliar >= 1
    assert total == no_auxiliar, "ha gravacao de imagem fora de _gravar_conferencia"
```
(mesmo espírito para "varrer requirements.txt como texto declarado").

**`pytest.skip` com a razão dita quando o ambiente não existe — `test_inventario_por_cima_da_barra_propria.py:919-925`:**
```python
def test_as_populacoes_de_recordings_nao_sao_afirmaveis_num_clone_limpo(self):
    if not (RECORDINGS / "inv2").is_dir() or not (RECORDINGS / "inv3").is_dir():
        pytest.skip(
            "recordings/ e gitignored: as 45 livres de inv2/ e as 8 "
            "cobertas de inv3/ nao existem num clone limpo. ..."
        )
```
Aplicar o mesmo formato ao skip da varredura de `.venv` em clone limpo/CI. As três varreduras (requirements.txt, `md.distributions()`, `md.distributions(path=[".venv/Lib/site-packages"])`) estão prontas e verificadas no `01-RESEARCH.md` (Descoberta 4). Mensagem de falha cita a constraint fundadora + tabela Out of Scope de REQUIREMENTS.md.

---

### Testes do gravador (FUND-01)

**Analog:** `tests/test_conferencia_gravada.py` inteiro. Padrões concretos:

**Caso determinístico "diretório ocupando o nome" (linhas 230-236):**
```python
(raiz / "calibracao-conferencia.png").mkdir()
```
Para o `Gravador`, `pasta_base` já é parâmetro do construtor — nem monkeypatch precisa; usar `tmp_path` direto.

**Somente-leitura com chmod (linhas 108-110):**
```python
def _travar_com_arquivo_somente_leitura(caminho: Path) -> None:
    caminho.write_bytes(b"imagem velha, a que engana o usuario")
    os.chmod(caminho, stat.S_IREAD)
```

**Assertiva "todo caminho citado existe" (linhas 49-66):**
```python
def _afirmar_que_todo_png_citado_existe(saida: str) -> None:
    for nome in _pngs_citados(saida):
        caminho = Path(nome)
        assert caminho.is_absolute(), f"a saida cita {nome} sem o caminho completo"
        assert caminho.exists(), f"a saida cita {nome}, que nao existe no disco"
```
Adaptar: nenhuma linha do `observacoes.jsonl` pode citar `arquivo` inexistente no disco.

---

### `l2scanner/calibrar_mercado.py` (FUND-03)

**Analog:** `l2scanner/calibrar.py` — três trechos a copiar; **módulo NOVO** porque o tripwire `test_existe_um_unico_ponto_de_escrita_no_modulo` conta `imwrite` no fonte de `calibrar.py` (importar `_gravar_conferencia` de lá, e replicar o tripwire para o módulo novo).

**Seleção de região com escala e confirmação — `calibrar.py:363-385`:**
```python
def calibrar_selecionando(pixels: np.ndarray, ox: int, oy: int) -> Calibracao | None:
    altura, largura = pixels.shape[:2]
    escala = min(1.0, 1600 / largura)
    visao = cv2.resize(pixels, None, fx=escala, fy=escala) if escala < 1.0 else pixels
    print("\nArraste o mouse em volta da party window e tecle ENTER.")
    caixa = cv2.selectROI("Marque a party window", visao, showCrosshair=False)
    cv2.destroyAllWindows()
    if caixa[2] == 0 or caixa[3] == 0:
        print("Nada selecionado.")
        return None
    x, y, larg, alt = (int(valor / escala) for valor in caixa)
    recorte = pixels[y : y + alt, x : x + larg]
```
Diferença: a fonte do frame é um PNG gravado do spike (replay), nunca captura ao vivo.

**Load-mutate-save (nunca JSON parcial) — `calibrar.py:637-664` (modo solo):**
```python
cal = Calibracao.carregar(ARQUIVO_CALIBRACAO)
anterior = cal.hp_proprio
cal.janela = alvo
cal.hp_proprio = barra
# ... e no fim cal.salvar() regrava o arquivo INTEIRO
```
Se não existe calibração anterior, recusar com explicação (mesmo tom das linhas 643-652).

**Imagem de conferência:** chamar `_gravar_conferencia` importada de `calibrar.py` — jamais um `imwrite` próprio.

**Matriz de confusão:** medir todo template × todo template com o `_correlacionar` de `identidade.py` (abaixo); registrar pior score inter-classe e recusar ALTO na calibração se dois itens da watchlist colidem.

---

### `calibrar-mercado.bat`

**Analog:** `calibrar-solo.bat` — copiar o esqueleto inteiro:
```bat
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo  O ambiente ainda nao foi preparado.
    echo  Rode vigiar-party.bat uma vez primeiro.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m l2scanner.calibrar --solo %*
REM ... bloco final instruindo a conferencia visual do PNG
```
Trocar por `-m l2scanner.calibrar_mercado` e adaptar o cabeçalho REM e a instrução de conferência.

---

### `l2scanner/calibracao.py` — chaves de mercado

**Analog:** padrão `banner_manutencao` no próprio módulo. Três pontos, todos a replicar por chave nova:

**Campo opcional com doutrina de versão — `calibracao.py:196-215`:**
```python
# OPCIONAL de proposito, e por isso a VERSAO_DO_ESQUEMA SEGUE EM 2: o
# `carregar` recusa qualquer versao diferente da constante, entao subir para
# 3 invalidaria o `calibration.json` que o usuario mediu a mao ...
banner_manutencao: Regiao | None = None
```

**Serialização condicional em `salvar` — `calibracao.py:308-311`:**
```python
"banner_manutencao": (
    self.banner_manutencao.como_dict() if self.banner_manutencao else None
),
```

**`.get` em `carregar` — `calibracao.py:357-365`:**
```python
# `.get`, exatamente como `hp_proprio`: e o que faz um calibration.json v2
# gravado antes desta funcionalidade carregar sem uma linha de migracao.
banner_manutencao=(
    Regiao.de_dict(dados["banner_manutencao"])
    if dados.get("banner_manutencao")
    else None
),
```
NUNCA subir `VERSAO_DO_ESQUEMA` (anti-pattern documentado no próprio módulo). Junto das chaves de mercado, gravar carimbo de contexto de captura (dimensões da janela no momento do corte); `conferir_geometria` (`calibracao.py:368+`) é o precedente da recusa por geometria divergente.

**Persistência de templates — padrão `Assinatura` hex-bits, `identidade.py:157-180`:**
```python
def como_dict(self) -> dict:
    altura, largura = self.mascara.shape
    empacotado = np.packbits(self.mascara.flatten())
    return {"nome": self.nome, "altura": int(altura),
            "largura": int(largura), "bits": empacotado.tobytes().hex()}

@classmethod
def de_dict(cls, dados: dict) -> "Assinatura":
    altura, largura = int(dados["altura"]), int(dados["largura"])
    bytes_ = bytes.fromhex(dados["bits"])
    plano = np.unpackbits(np.frombuffer(bytes_, dtype=np.uint8))
    return cls(nome=dados["nome"],
               mascara=plano[: altura * largura].reshape(altura, largura))
```
Para templates em tons de cinza (âncora, dígitos), bytes crus em hex com dimensões declaradas — mesma estrutura, sem `packbits`.

---

### `l2scanner/mercado_visao.py` (DETC-01)

**Charter de pureza — copiar o cabeçalho de `visao.py:1-7`:**
```python
"""Extracao pura: de um frame + calibracao para uma observacao.

Esta camada nao tem relogio, nao tem rede, nao abre arquivo e nao decide nada.
"""
```

**Correlação em posição calibrada — `identidade.py:187-212` (copiar literal, incluindo o porquê medido):**
```python
def _correlacionar(alvo: np.ndarray, molde: np.ndarray) -> float:
    """Compara o recorte com o molde NO ALINHAMENTO CALIBRADO.

    Uma posicao so, de proposito. [...] alinhado -> maximo deslizante:
        casamentos CORRETOS  +0.000 (8 de 8)
        casamentos ERRADOS   ate +0.373
    """
    if alvo.size == 0 or molde.size == 0:
        return 0.0
    if molde.shape[0] > alvo.shape[0] or molde.shape[1] > alvo.shape[1]:
        return 0.0
    fa, fm = alvo.astype(np.float32), molde.astype(np.float32)
    if fa.std() < 1e-6 or fm.std() < 1e-6:
        return 0.0
    # [0, 0] e o molde na origem do recorte — a posicao que a calibracao gravou.
    return float(cv2.matchTemplate(fa, fm, cv2.TM_CCOEFF_NORMED)[0, 0])
```

**Constante de limiar com a medição escrita ao lado — estilo `visao.py:209-220`:**
```python
# Desvio minimo de cinza para um recorte da barra propria valer como LEGIVEL.
#
# Medido nas fixtures reais da barra do usuario: desvio 38,6. Um recorte preto
# ou uniforme [...] da 0,00. A margem e enorme, entao o piso fica bem baixo
# de proposito — ele so precisa rejeitar o degenerado, nunca uma barra real.
DESVIO_MINIMO_DA_BARRA_PROPRIA = 3.0
```
O limiar da âncora do mercado sai MEDIDO das fixtures (positivos do inv3 + negativos mercado-fechado/outros painéis), com os números no comentário.

**Proibição herdada:** jamais estender `barra_propria_legivel` / gate de brilho — a lição está medida em `visao.py:85-111` (abaixo).

---

### `l2scanner/visao.py` — campo novo em `Observacao`

**Analog:** os dois campos opcionais existentes de `Observacao` (`visao.py:79-118`):
```python
# SO PARA MOSTRAR. Nenhuma decisao pode sair deste campo, nunca.
# [...] A seguranca aqui NAO vem de guardas no rastreador — vem de esta
# leitura NAO EXISTIR para ele. `rastreador.py` nao le este campo, e ha um
# tripwire de arquitetura na suite que quebra se ele passar a ler.
hp_proprio_aparente: float | None = None

# [...] `None` significa "ninguem perguntou", e nunca vira evento.
estado_do_cliente: EstadoDoCliente | None = None
```
O campo "mercado aberto" segue exatamente esse molde: opcional, default `None`/`False`, sem consumidor de decisão no rastreador nesta fase; serve ao console/log ("oclusão conhecida") e à regressão. Replicar/estender o tripwire de arquitetura que verifica que `rastreador.py` não lê o campo.

---

### Teste de regressão 27x + `tests/fixtures/mercado/`

**Analog:** `tests/test_inventario_por_cima_da_barra_propria.py`.

**Fixtures resgatadas + valores medidos parametrizados (linhas 868-902):**
```python
@pytest.mark.parametrize(
    ("rotulo", "esperado"),
    [("livre_0", 1.0000), ("livre_1", 0.9992), ...],
)
def test_as_livres_casam_alto(self, rotulo, esperado):
    valor = _casamento_do_perfil_proprio(recorte(rotulo))
    assert valor >= CASAMENTO_MINIMO_DO_PERFIL_PROPRIO, (...)
    assert abs(valor - esperado) < 0.001, (...)
```
Formato a replicar para a âncora do mercado: positivos (frames com painel) parametrizados com o score medido; negativos abaixo do limiar.

**Aquecimento do rastreador com pixels reais — linhas 518-537:**
```python
def frame_de_party(rotulo_da_barra: str | None) -> Frame:
    barra = cv2.imread(str(CALIBRACAO.parent / "limpo__hp_proprio.png"))
    return Frame(
        pixels=cv2.imread(str(CALIBRACAO.parent / "limpo.png")),
        indice=0, saude=SaudeDoFrame.OK,
        extras={"hp_proprio": barra},
    )
```

**Cuidados de replay:** `--replay recordings/inv3` NÃO funciona (`ReplaySource` faz glob de `frame_*.png` em `frames.py:201`; inv3 usa `f0NN.png`) — o replay do 27x é um harness pytest alimentando `extrair` + `Rastreador` frame a frame. O teste afirma as DUAS metades: âncora dispara nos frames com painel E zero eventos de morte (Pitfall 5 da RESEARCH).

## Shared Patterns

### Escrita de imagem checada (falha fechada)
**Fonte:** `calibrar.py:407-415` (`tentar`)
**Aplicar a:** `gravador.py` (fix FUND-01) e `calibrar_mercado.py` (via import de `_gravar_conferencia`, nunca `imwrite` próprio). Tripwire estrutural por módulo (`test_conferencia_gravada.py:217-227`).

### Chave opcional de calibração via `.get`
**Fonte:** `calibracao.py:196-215, 308-311, 357-365` (`banner_manutencao`)
**Aplicar a:** todas as chaves novas de mercado (âncora, grade, templates, carimbo de geometria). Versão do esquema fica em 2.

### Extra opcional no pipeline de captura
**Fonte:** `__main__.py:1436-1442` + `captura_janela.py:371-388` (`_extra_para_janela` devolve `None` quando a região cai fora — falha fechada)
**Aplicar a:** região da âncora do mercado como extra, consumida por `mercado_visao` e exibida como oclusão conhecida.

### `pytest.skip` com a razão dita para populações gitignored
**Fonte:** `test_inventario_por_cima_da_barra_propria.py:919-925`
**Aplicar a:** firewall (varredura de `.venv` ausente) e testes de população grande sobre `recordings/`.

### Constantes com a medição escrita ao lado
**Fonte:** `visao.py:186-193, 209-239` e `identidade.py:194-200`
**Aplicar a:** limiar da âncora, limiares da matriz de confusão de templates, e o comportamento medido do `imwrite` na docstring do gravador.

## No Analog Found

| Arquivo | Role | Data Flow | Motivo |
|---|---|---|---|
| `ROTEIRO-SPIKE.md` | doc de fase | — | Checklist markdown novo; conteúdo (8 rótulos, durações 30-60s por custo de 3,5 MB/frame) já especificado em CONTEXT/RESEARCH |
| `SPIKE-RESPOSTAS.md` | doc de fase | — | Documento de análise pós-gravações; formato livre com citação de frames como evidência |

## Metadata

**Escopo da busca de analogs:** `l2scanner/`, `tests/`, raiz (`*.bat`), guiado pelas referências verificadas do 01-RESEARCH.md
**Arquivos lidos:** `gravador.py` (inteiro), `calibrar.py` (355-434, 610-669), `identidade.py` (150-219), `visao.py` (1-120, 180-239), `calibracao.py` (190-219, 300-369), `__main__.py` (1425-1454, 1595-1619, 1695-1714), `captura_janela.py` (340-421), `calibrar-solo.bat` (inteiro), `test_conferencia_gravada.py` (1-120, 200-239), `test_inventario_por_cima_da_barra_propria.py` (510-544, 855-939)
**Data da extração:** 2026-08-27
