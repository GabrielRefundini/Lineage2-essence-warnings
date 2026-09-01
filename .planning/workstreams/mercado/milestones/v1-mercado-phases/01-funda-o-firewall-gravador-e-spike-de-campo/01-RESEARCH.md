# Fase 1: Fundação — firewall, gravador e spike de campo — Research

**Pesquisado:** 2026-08-27
**Domínio:** Recorder confiável (cv2.imwrite), firewall de dependências (importlib.metadata), calibração/templates de mercado sobre frames gravados, detecção positiva do painel XM Market
**Confiança:** HIGH — quase tudo verificado no repo e na máquina-alvo nesta sessão; UI do mercado parcialmente verificada em frame real já existente no disco

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Roteiro das gravações do spike (FUND-02)**
- Roteiro entregue como **checklist markdown** (`ROTEIRO-SPIKE.md` no diretório da fase): cada cenário numerado, com o rótulo exato de `--record` a usar e o que fazer na tela. O usuário segue com o arquivo aberto no segundo monitor.
- Cenários obrigatórios: mercado fechado, mercado aberto, com scroll, página cheia.
- Cenários extras decididos: **tooltip por cima das linhas** (gêmeo do incidente 27x); **marcação de alvo/vida do próprio char sobrepondo levemente o painel**; **mercado aberto durante o farm com party window visível**; **scroll no meio do movimento**.
- **Fato de campo (usuário, 2026-08-27): o inventário NUNCA sobrepõe o mercado — abrir o inventário FECHA o painel do mercado.** Outras janelas do menu podem sobrepor em edge cases raros → ideia deferida, fora do roteiro do v1.
- **Uma sessão por cenário**, com rótulo fixo definido no checklist (ex.: `--record mercado-aberto`, `--record mercado-tooltip`). Pastas pequenas e nomeadas viram fixtures estáveis que os testes citam pelo nome.
- Respostas das perguntas de campo: **Claude analisa os frames gravados e propõe as respostas em `SPIKE-RESPOSTAS.md`** no diretório da fase, citando frames específicos como evidência; o usuário valida ou corrige. Perguntas mínimas: linhas por página, separador de milhar, moeda, colunas, preço total vs unitário, onde fica o preço médio embutido, confirmação da renderização do encanto.

**Variantes de encanto (+3 vs +4) na watchlist**
- **Variantes importam e entram no v1.**
- **Renderização confirmada pelo usuário: o encanto aparece como prefixo de texto no nome — `+3 <nome do item>`.** O spike só valida com frames o que já foi confirmado.
- Template único: **nome-como-renderizado incluindo o prefixo `+N` no recorte** — `+3 Bota X` e `+4 Bota X` são dois templates distintos. Mesma técnica medida do `identidade.py`, zero lógica nova de dois passos.
- Semântica da watchlist: **só o que está listado explicitamente** no `config.toml`. Conjunto fechado puro; adicionar variante = editar config.
- Análise: **cada variante é uma série independente de ponta a ponta**.

**Ferramenta de calibração do mercado (FUND-03)**
- **Estender o fluxo de calibração existente com um modo mercado** — nasce um `calibrar-mercado.bat` seguindo o precedente `calibrar.bat` / `calibrar-solo.bat`, reusando o código de calibração atual.
- Interação no **mesmo estilo da ferramenta atual**: seleção de regiões sobre um frame com confirmação visual.
- Fonte do frame: **frame GRAVADO do spike (replay)**, nunca captura ao vivo.
- Templates de dígito e de nomes: **cortados da gravação pela própria ferramenta, com confirmação visual e matriz de confusão medida** contra linhas negativas reais. Critério: nunca editar JSON à mão.
- Chaves novas em `calibration.json` são opcionais via `.get` (padrão `banner_manutencao`).

**Firewall FIRE-01**
- Banlist **ampla e nomeada**: `pyautogui`, `pydirectinput`, `pynput`, `keyboard`, `mouse`, `autoit`/wrappers de AHK.
- Mecanismo: **teste pytest que varre a árvore INSTALADA do venv** (`importlib.metadata.distributions`) além do `requirements.txt`.
- Vive em **`tests/test_firewall_escopo.py` na suíte normal**.
- Mensagem de falha **explica o porquê**: cita a constraint fundadora e aponta a tabela Out of Scope de REQUIREMENTS.md.

### Claude's Discretion
- Detalhes internos do fix do `imwrite` (FUND-01): checagem de retorno + erro alto e visível; forma exata da mensagem/exceção a critério de Claude, desde que o contador só conte escritas confirmadas.
- Implementação da âncora/template do painel (DETC-01): âncora positiva própria do mercado, jamais estender o gate de brilho da barra própria (`visao.py`); verificada no replay da gravação do incidente 27x com ZERO alertas de morte.

### Deferred Ideas (OUT OF SCOPE)
- **Outras janelas do menu sobrepondo o mercado (edge cases raros)** — anotado para versão futura, fora do roteiro do v1
- Spike validado não-empacotado `wgc-janela-em-segundo-plano` — `/gsd-spike --wrap-up` fora desta fase
- Comandos WhatsApp de mercado (WAPP-01/02) — v2 em REQUIREMENTS.md
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Descrição | Suporte da pesquisa |
|----|-----------|---------------------|
| FIRE-01 | Build quebra se lib de síntese de input entrar na árvore de dependências | Mecanismo verificado empiricamente nesta sessão: pytest roda no Python GLOBAL (não no venv) — o teste precisa varrer requirements.txt + ambiente corrente + `.venv` via `distributions(path=...)`. Ver "Descoberta 4" |
| FUND-01 | Gravador só conta frames confirmados; `cv2.imwrite` checado; falha alta | Bug localizado em `gravador.py:43,54`; modos de falha já MEDIDOS no repo (`calibrar.py:_gravar_conferencia`); padrão de teste pronto em `tests/test_conferencia_gravada.py`. Ver "Descoberta 1" |
| FUND-02 | Sessões reais do World Exchange gravadas com `--record` + perguntas respondidas | **`--record` hoje grava SÓ o recorte da party window — inútil para o spike.** Precisa de modo de gravação da janela completa (`capturar_completo()` já existe). Ver "Descoberta 2". Frame real já no disco pré-responde parte das perguntas — ver "Descoberta 3" |
| FUND-03 | Calibração do mercado persiste em `calibration.json` via ferramenta própria | Fluxo, esquema (v2 congelado, chaves `.get`), armazenamento de templates (precedente `Assinatura` hex-bits) e tripwire estrutural do `calibrar.py` mapeados. Ver seção FUND-03 |
| DETC-01 | "World Exchange aberto" por âncora positiva; sinal compartilhado com oclusão do detector de morte | Material do incidente 27x localizado e verificado visualmente: `recordings/inv3/` (painel XM Market aberto sobre a barra própria). `--replay` NÃO funciona nele (naming incompatível) — regressão via pytest com fixtures resgatadas. Ver seção DETC-01 |
</phase_requirements>

## Summary

Esta fase é quase toda intra-repo: o domínio técnico já existe, medido e documentado, dentro de `l2scanner/`. A pesquisa desta sessão verificou empiricamente os cinco pontos que o planner precisa acertar, e encontrou **três fatos novos que mudam o desenho dos planos**:

1. **`--record` hoje não serve para o spike.** O `Gravador` salva apenas `frame.pixels` — o recorte da party window (172×522 px) — e descarta os `extras`. O painel do mercado nunca entra na gravação. A `JanelaSource` já guarda o frame completo da janela internamente (`capturar_completo()`, usado pelo calibrador e pelo vigia do cliente); o gravador precisa de um modo janela-completa. Sem isso, FUND-02 é impossível por construção.
2. **A gravação do incidente 27x existe, está em `recordings/inv3/`, e mostra o painel "XM Market" — não o inventário.** Verificado abrindo `f000_JANELA.png` (1720×1392): painel de mercado aberto ao centro, party window visível à esquerda (Korzis/Kaus/J4guar/TioMad), barra própria visível (HP 3707/3707). O `leitura.txt` da pasta registra `propria=0%(ok)` por 40+ frames seguidos — a matéria-prima exata das 27 mortes falsas. Esse material pré-responde perguntas do spike (colunas "Total" E "Unit price" coexistem; vírgula decimal; ~10 slots de linha) e permite começar a âncora do DETC-01 ANTES das gravações novas do usuário.
3. **A suíte de testes roda no Python GLOBAL, não no venv.** O venv (3.12.10, 15 distribuições) não tem pytest; o pytest 9.1.1 vive no Python312 global (101 distribuições). Um `importlib.metadata.distributions()` ingênuo dentro do teste varreria o ambiente errado. Verificado nesta sessão: `distributions(path=[r".venv\Lib\site-packages"])` enumera corretamente as 15 distribuições do venv a partir de outro interpretador — o firewall precisa varrer os DOIS ambientes mais o `requirements.txt`.

**Primary recommendation:** estruturar a fase em dois blocos separados pelo gate externo — Bloco A (construível agora, sem o usuário): fix do gravador + modo janela-completa, `tests/test_firewall_escopo.py`, `ROTEIRO-SPIKE.md`, e medição preliminar da âncora do painel sobre `recordings/inv3/` (já no disco); **checkpoint: usuário grava**; Bloco B (pós-gravações): `SPIKE-RESPOSTAS.md`, `calibrar-mercado.bat` + templates + matriz de confusão, âncora final do DETC-01 + regressão do 27x com fixtures resgatadas para `tests/fixtures/`.

## Architectural Responsibility Map

| Capability | Camada primária | Camada secundária | Rationale |
|------------|-----------------|-------------------|-----------|
| Fix do imwrite + contador honesto (FUND-01) | `l2scanner/gravador.py` | `__main__.py` (resumo final) | O único ponto de escrita de frames; o resumo final deve reportar a verdade do disco |
| Gravação da janela completa (FUND-02) | `gravador.py` + `__main__.py` (flag) | `captura_janela.py` (fonte do frame completo — já existe) | `capturar_completo()` já é API pública da `JanelaSource` |
| Firewall (FIRE-01) | `tests/test_firewall_escopo.py` (novo) | `requirements.txt` (comentário já existe) | Controle estrutural, não de runtime — vive na suíte |
| Roteiro + respostas do spike (FUND-02) | `.planning/workstreams/mercado/phases/01-.../` (docs) | — | Artefatos de fase, não código |
| Calibração de mercado (FUND-03) | `l2scanner/calibrar_mercado.py` (novo) + `calibracao.py` (chaves opcionais) | `calibrar-mercado.bat` | `calibrar.py` tem 943 linhas e um tripwire estrutural que conta `imwrite` no módulo — módulo novo evita colisão |
| Âncora do painel (DETC-01) | `l2scanner/mercado_visao.py` (novo, puro) | `visao.py`/`sessao.py` NUNCA estendidos no gate de brilho; consumo via extra opcional | Charter de pureza de `visao.py:1-7`; lição do consumidor único em `visao.py:85-111` |
| Regressão do 27x (DETC-01) | `tests/` + `tests/fixtures/mercado/` (novo) | `recordings/inv3/` (fonte, gitignored) | Padrão estabelecido: fixtures resgatadas + `pytest.skip` para populações de `recordings/` |

## Standard Stack

### Core — ZERO dependências novas

`requirements.txt` não muda nesta fase. Verificado empiricamente nesta sessão na máquina-alvo:

| Ferramenta | Versão verificada | Papel nesta fase | Evidência |
|------------|-------------------|------------------|-----------|
| Python (venv `.venv`) | **3.12.10** | Runtime de produção | `[VERIFIED: .venv/Scripts/python.exe --version executado nesta sessão]` — confirma a nota do orquestrador; CLAUDE.md diz 3.13 (discrepância conhecida de docs) |
| Python (global) | 3.12.x + pytest **9.1.1** | Runtime da suíte de testes | `[VERIFIED: python -m pytest --collect-only → 1166 testes coletados]`; venv NÃO tem pytest (`ModuleNotFoundError` verificado) |
| `opencv-python` | pin `>=4.10,<5` | `imwrite`, `matchTemplate`, `selectROI`, overlay de conferência | `[VERIFIED: requirements.txt + presente nos dois ambientes]` |
| `numpy` | pin `>=2.0` | máscaras, projeções, empacotamento de templates | `[VERIFIED: requirements.txt]` |
| `mss`, `windows-capture`, `winrt-*` | pins atuais | captura (inalterada nesta fase) | `[VERIFIED: requirements.txt]` |
| `importlib.metadata` | stdlib 3.12 | varredura do firewall | `[VERIFIED: executado nesta sessão nos dois ambientes — ver Descoberta 4]` |

### Instalação

```bash
# NADA a instalar. requirements.txt não muda nesta fase.
```

## Package Legitimacy Audit

**Nenhum pacote externo é instalado nesta fase.** A fase existe, em parte, para IMPEDIR pacotes de entrar (FIRE-01). Auditoria vazia por construção.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## As cinco descobertas verificadas (o coração desta pesquisa)

### Descoberta 1 — FUND-01: o bug exato e o padrão de fix já existente no repo

O bug, verificado por leitura do fonte:

```python
# l2scanner/gravador.py:39-54 [VERIFIED: gravador.py:39-54, lido nesta sessão]
def gravar(self, frame: Frame, momento: float) -> None:
    import cv2
    caminho = self.pasta / f"frame_{frame.indice:06d}.png"
    cv2.imwrite(str(caminho), frame.pixels)          # <- retorno jogado fora
    linha = { "indice": frame.indice, "momento": momento,
              "saude": frame.saude.value, "arquivo": caminho.name }
    self._arquivo_meta.write(json.dumps(linha, ensure_ascii=False) + "\n")
    self._arquivo_meta.flush()
    self.frames_gravados += 1                        # <- conta a TENTATIVA
```

Três coisas mentem juntas quando o `imwrite` falha: o contador (`frames_gravados += 1` incondicional), o `observacoes.jsonl` (linha escrita citando um `arquivo` que não existe) e o resumo final (`__main__.py:1703-1709` imprime `gravador.frames_gravados`). O fix precisa condicionar **as três** à escrita confirmada — não só o contador.

**Modos de falha já MEDIDOS nesta máquina** — não precisam ser re-descobertos. A docstring de `_gravar_conferencia` registra: "Medido nesta maquina: destino somente-leitura, destino ocupado por um diretorio e pasta inexistente devolvem `False`, e nenhum dos tres levanta excecao" `[VERIFIED: calibrar.py:388-405]`. O padrão de fix também já existe no mesmo lugar:

```python
# l2scanner/calibrar.py:407-414 — o padrão a replicar no gravador
# [VERIFIED: calibrar.py:407-414, lido nesta sessão]
def tentar(caminho: Path) -> bool:
    # O try/except existe ALEM do retorno booleano para que o `False`
    # documentado e uma excecao inesperada caiam no MESMO caminho de falha.
    try:
        return bool(cv2.imwrite(str(caminho), imagem))
    except Exception:  # noqa: BLE001
        return False
```

**Contexto de chamada — decide a forma do "erro alto":** `Gravador.gravar` é chamado em `Sessao.tick` (`sessao.py:199-200`) **ANTES** do `try/except` da extração (`sessao.py:217-227`), e `sessao.tick(frame, momento)` é chamado no laço principal **SEM** try/except próprio (`__main__.py:1615`; só a captura tem um). Uma exceção em `gravar` derruba o scanner inteiro `[VERIFIED: sessao.py:187-243 e __main__.py:1569-1615, lidos nesta sessão]`. Como `--record` roda DURANTE o farm com alertas ativos, matar o processo por disco cheio contradiz a doutrina da casa ("degrada a feature, nunca o produto" — `ocr.py`, citada em research/ARCHITECTURE.md). **Recomendação (discrição de Claude, forma sugerida):** `gravar` não levanta — devolve/contabiliza `falhas_de_gravacao`, loga `log.error` visível a cada falha (ou na primeira + a cada N), e o resumo final reporta as duas metades E a verdade do disco:

```
Sessao gravada: 118 frames confirmados, 3 FALHAS de escrita, em recordings/...
  no disco: 118 frame_*.png            # len(list(pasta.glob("frame_*.png")))
```

O critério de sucesso 1 pede exatamente "contador bate com os arquivos no disco" — reportar o glob ao lado do contador torna a prova trivial (mesma filosofia do "snapshots hoje é SELECT COUNT(*)" de PITFALLS Pitfall 14).

**Padrão de teste pronto:** `tests/test_conferencia_gravada.py` já resolve todos os problemas de testar isso no Windows: redirecionar a escrita para `tmp_path` via `monkeypatch` de uma global, o caso determinístico "diretório ocupando o nome do arquivo" (funciona em qualquer SO), o caso somente-leitura com `pytest.skip` quando o SO ignora, e a assertiva "nenhum caminho citado na saída pode não existir no disco" `[VERIFIED: tests/test_conferencia_gravada.py, lido nesta sessão]`. Para o `Gravador`, `pasta_base` já entra por parâmetro no construtor — nem monkeypatch precisa.

### Descoberta 2 — FUND-02: `--record` hoje NÃO grava o mercado (bloqueador de desenho)

Verificado por leitura do fonte:

- `Gravador.gravar` salva **apenas `frame.pixels`** `[VERIFIED: gravador.py:39-54]`.
- No caminho `--janela`, `frame.pixels` é o **recorte da party window** (a região calibrada, 172×522 px medido em `recordings/inv3/f001.png` nesta sessão), e os `extras` (barra própria, banner) são recortes nomeados que o gravador **nunca salva** `[VERIFIED: captura_janela.py:356-369 + gravador.py]`.
- `ReplaySource` também **nunca reconstrói extras** — só `frame_*.png` + momentos do JSONL `[VERIFIED: frames.py:190-244]`.

Ou seja: uma sessão `--record` de hoje não contém um único pixel do painel do mercado. E há um problema de ovo-e-galinha: a região do mercado só será conhecida DEPOIS da calibração (FUND-03), que por decisão travada roda sobre frames GRAVADOS.

**Resolução recomendada: gravar a JANELA COMPLETA no spike.** `JanelaSource` já mantém o frame completo internamente a cada captura (os extras são recortados dele — `captura_janela.py:356-360`) e expõe `capturar_completo()` (usado por `calibrar.py:620-624` e pelo vigia do cliente). O custo de fio é pequeno: um modo (flag nova tipo `--record-janela`, ou `--record` + `--janela` passando o frame completo ao gravador) em que o PNG gravado é a janela inteira. Frame completo elimina o ovo-e-galinha (o calibrador corta QUALQUER região depois) e é exatamente o formato que `inv3/f*_JANELA.png` provou útil.

**Custo de disco medido:** janela completa 1720×1392 = **3,5 MB/PNG** (`f000_JANELA.png`, medido nesta sessão) → a ~1 Hz, **~210 MB/min**. O ROTEIRO deve prescrever sessões curtas (30–60 s por cenário) e o teste de disco-cheio do critério 1 fica até fácil de provocar. `[VERIFIED: os.path.getsize executado nesta sessão]`

**Naming das gravações:** `Gravador` cria `pasta_base/{YYYYmmdd-HHMMSS}-{rotulo}` `[VERIFIED: gravador.py:28-32]`. O ROTEIRO fixa os rótulos (`mercado-fechado`, `mercado-aberto`, `mercado-scroll`, `mercado-pagina-cheia`, `mercado-tooltip`, `mercado-alvo-sobreposto`, `mercado-farm-com-party`, `mercado-scroll-transicao`); testes e SPIKE-RESPOSTAS referenciam por sufixo (`recordings/*-mercado-aberto/`).

### Descoberta 3 — DETC-01: o material do incidente 27x existe, e é o painel "XM Market"

**Localização:** `recordings/inv3/` — 45 recortes de party window (`f000.png`–`f044.png`), **10 frames de janela completa** (`f000_JANELA.png`, `f005_...`, a cada 5, até `f040_...`), e um `leitura.txt` diagnóstico `[VERIFIED: ls recordings/inv3 nesta sessão]`.

**Conteúdo verificado visualmente** (`f000_JANELA.png` aberto nesta sessão): painel **"XM Market"** aberto ao centro da janela "Yazalaque - XM Essence"; party window visível à esquerda (Korzis, Kaus, J4guar, TioMad); barra própria visível (HP 3707/3707) parcialmente sob o painel. Elementos estáveis do painel: barra de título "XM Market" com X de fechar; botões "Check the Market" / "My Transactions"; abas "Adena | Equipment | Enhancement | Product List | Characters"; sub-abas "Weapons | Armor | Accessories | Misc."; cabeçalhos de coluna "Goods | Quantity | Total ▲ | Unit price | Buy"; botão "Refresh". Linhas visíveis: "Pendant Petram Lv. 1 | 1 | 40,00 XM Coin | 40,00", "…50,00 XM Coin | 50,00" — **vírgula decimal com 2 casas** e moeda "XM Coin" nessa aba; ~10 slots de linha, 3 preenchidos; painel de fundo **opaco** (arte interna própria, não transparência sobre o terreno). `[VERIFIED: recordings/inv3/f000_JANELA.png, inspecionado visualmente nesta sessão]`

Implicações:

1. **O nome nativo do painel é "XM Market", não "World Exchange".** Para a âncora isso é irrelevante (template é pixel, não texto), mas o ROTEIRO e o SPIKE-RESPOSTAS devem usar o nome real, e o spike precisa responder: a aba **"Adena"** é o World Exchange de adena propriamente dito? Formato de preço/separador/colunas naquela aba segue **UNVERIFIED** — o frame verificado é da aba Equipment/Accessories em XM Coin.
2. **Duas perguntas do spike já têm pré-resposta com evidência:** (a) as colunas "Total" e "Unit price" **coexistem** na mesma grade (o dilema total-vs-unitário do Pitfall 6 pode se resolver lendo as duas); (b) o cabeçalho "Total ▲" é ordenável. Confirmar na aba Adena.
3. **O `leitura.txt` registra o desastre em andamento:** `propria= 0%(ok)` por 40+ frames (a barra própria coberta lendo 0% = leitura de morte da época), `ui=N` na maior parte, e leituras de HP da party de 38%/83% plausíveis-mas-erradas com o painel presente `[VERIFIED: recordings/inv3/leitura.txt, lido nesta sessão]`. É exatamente a matéria-prima do replay de regressão do critério 4.

**Restrições de uso do inv3 que o planner precisa saber:**

- `recordings/` está no `.gitignore` (`recordings/` + `*.png`, com exceções só para `tests/fixtures/**/*.png` e `l2scanner/recursos/*.png`) `[VERIFIED: .gitignore:6-24]`. **Qualquer teste de regressão permanente precisa RESGATAR os frames necessários para `tests/fixtures/`** — padrão já estabelecido e documentado em `tests/test_inventario_por_cima_da_barra_propria.py:858-935` (classe `TestOCasamentoNasFixturesVERSIONADAS` + `pytest.skip` com razão dita para as populações que só existem em `recordings/`).
- **`--replay recordings/inv3` NÃO funciona:** `ReplaySource` faz glob de `frame_*.png` `[VERIFIED: frames.py:201]` e o inv3 usa `f0NN.png` — resultado seria `FileNotFoundError`. O "replay da gravação do incidente 27x" do critério 4 deve ser um **harness pytest** sobre fixtures resgatadas (alimentando `extrair` + `Rastreador` frame a frame), não a flag `--replay`. Precedente completo do aquecimento do rastreador com pixels reais: `frame_de_party()` em `test_inventario_por_cima_da_barra_propria.py:518-537`.
- Os recortes da barra própria não foram salvos no inv3 (só no inv2); para o replay, derivá-los dos 10 frames `_JANELA` usando a região `hp_proprio` do `calibration.json` vigente (presente na raiz, v2, janela "Yazalaque - XM Essence" `[VERIFIED: calibration.json inspecionado nesta sessão]`). **Verificação obrigatória na execução:** conferir que a geometria da calibração atual ainda corresponde aos frames do inv3 (janela 1720×1392) antes de confiar nos recortes.

### Descoberta 4 — FIRE-01: o pytest roda no ambiente ERRADO para uma varredura ingênua

Verificado nesta sessão, na máquina-alvo:

- `.venv` (Python **3.12.10**): **15 distribuições** — `['coverage', 'mss', 'numpy', 'opencv-python', 'pip', 'typing_extensions', 'windows-capture', 'winrt-runtime', 'winrt-windows.foundation', 'winrt-windows.foundation.collections', 'winrt-windows.globalization', 'winrt-windows.graphics.imaging', 'winrt-windows.media.ocr', 'winrt-windows.security.cryptography', 'winrt-windows.storage.streams']`. **Sem pytest.** `[VERIFIED: importlib.metadata.distributions() executado no venv nesta sessão]`
- Python global (`C:\...\Python312`): **101 distribuições**, incluindo pytest 9.1.1, ruff, pyinstaller, flask etc. É ele quem coleta os 1166 testes da suíte. `[VERIFIED: executado nesta sessão]`
- Banidas presentes hoje: **nenhuma, nos dois ambientes** (`pyautogui`, `pydirectinput`, `pynput`, `keyboard`, `mouse` ausentes). `[VERIFIED: interseção computada nesta sessão]`
- **O mecanismo que fecha o buraco:** `importlib.metadata.distributions(path=[r".venv\Lib\site-packages"])` executado do interpretador global enumera corretamente as 15 distribuições do venv. `[VERIFIED: executado nesta sessão]`

**Desenho recomendado para `tests/test_firewall_escopo.py` — três varreduras, cada uma um teste:**

```python
# Esqueleto verificado — as chamadas de API foram executadas nesta sessão
import importlib.metadata as md
from pathlib import Path

BANIDAS = {
    "pyautogui", "pydirectinput", "pynput", "keyboard", "mouse",
    "autoit", "pyautoit", "ahk",   # wrappers de AutoIt/AutoHotkey
}

def _nomes(dists):
    return {(d.metadata["Name"] or "").lower() for d in dists}

# 1) requirements.txt declarado (pega a intenção antes do install)
# 2) ambiente que roda a suíte:      _nomes(md.distributions())
# 3) venv de produção, se existir:   _nomes(md.distributions(
#        path=[str(Path(".venv/Lib/site-packages"))]))
#    -> sem .venv (clone limpo/CI): pytest.skip com a razão dita,
#       no padrão de TestOCasamentoNasFixturesVERSIONADAS
```

Complemento barato que fecha a transitiva DECLARADA (além da instalada): varrer `d.requires` (Requires-Dist) de cada distribuição instalada procurando nomes banidos — pega uma dependência que PUXARIA uma banida antes mesmo de ela ser instalada. `[ASSUMED — API `Distribution.requires` é stdlib documentada, mas o formato das strings de requirement exige parse tolerante; validar na implementação]`

**Mensagem de falha (decisão travada):** citar a constraint fundadora ("o scanner é somente leitura, nunca envia input ao jogo") e apontar a tabela Out of Scope de `REQUIREMENTS.md` — o texto-fonte já existe no bloco final de `requirements.txt` `[VERIFIED: requirements.txt, bloco "NAO ADICIONE AQUI, POR DECISAO DE PROJETO"]`.

**Critério de sucesso 5 ("o usuário pode ver o teste vermelho ao tentar"):** provar por teste-do-teste (injetar uma distribuição falsa/banida na lista e afirmar que o detector acusa — mesmo espírito da "verificação por mutação" registrada no SUMMARY do quick 260826-dxm), mais uma instrução de demonstração manual no ROTEIRO ou no summary da fase: `pip install keyboard` no venv → suíte vermelha → `pip uninstall keyboard`. Instalar uma banida de verdade num teste automatizado seria o próprio pecado.

### Descoberta 5 — FUND-03: os três trilhos que a ferramenta de calibração deve seguir

**(a) Esquema congelado, chaves opcionais.** `VERSAO_DO_ESQUEMA = 2` e `carregar` recusa qualquer outra versão; o precedente `banner_manutencao` existe justamente para adicionar campo SEM subir a versão: campo `| None = None` no dataclass, `dados.get(...)` no `carregar`, serialização condicional no `salvar` `[VERIFIED: calibracao.py:22, 196-215, 308-311, 357-365]`. As chaves novas de mercado (âncora, grade, templates) seguem exatamente esse trilho — calibração antiga carrega, feature de mercado fica OFF.

**(b) Armazenamento de templates: dentro do `calibration.json`, padrão `Assinatura`.** Três opções avaliadas:

| Opção | Veredito | Por quê |
|---|---|---|
| PNGs em `l2scanner/recursos/` (precedente `dialogo_desconexao.png`) | **Não** | `recursos/` é dado de pacote VERSIONADO (`.gitignore` o excepciona); templates de mercado são específicos da máquina/janela do usuário — commitá-los seria hardcode de calibração |
| PNGs soltos numa pasta `templates/` | Aceitável | `*.png` na raiz já é gitignored; mas quebra a disciplina "a calibração é UM arquivo que a ferramenta regrava inteiro" e cria estado órfão |
| **Embutir no `calibration.json`, como `Assinatura.como_dict`** | **Recomendado** | Precedente direto: máscaras empacotadas em bits hex, "8x menor que um PNG e nao depende de codec nenhum para voltar" `[VERIFIED: identidade.py:157-180]`. Para templates em tons de cinza, bytes crus em hex (âncora ~40×20 = ~1,6 KB hex; 12 glifos de dígito ~10×14 = ~4 KB total) — tamanho trivial |

Junto dos templates, gravar o **carimbo de contexto de captura** (Pitfall 5): dimensões da janela do jogo e da região no momento do corte + a `geometria_da_tela` que `Calibracao` já carrega — no arranque, janela com dimensão diferente ⇒ recusar a leitura de mercado com "recalibre o mercado", nunca ler degradado.

**(c) O tripwire estrutural do `calibrar.py` e a decisão de módulo.** `test_existe_um_unico_ponto_de_escrita_no_modulo` conta ocorrências da string `imwrite` no FONTE de `l2scanner.calibrar` e exige que todas estejam em `_gravar_conferencia` `[VERIFIED: tests/test_conferencia_gravada.py:217-227]`. Qualquer escrita de imagem nova em `calibrar.py` fora do auxiliar quebra a suíte. **Recomendação: módulo novo `l2scanner/calibrar_mercado.py`** (o `calibrar.py` já tem 943 linhas), importando `_gravar_conferencia` para a imagem de conferência e replicando o teste estrutural para o módulo novo. O `calibrar-mercado.bat` segue o esqueleto do `calibrar-solo.bat` (checa `.venv`, chama `python -m l2scanner.calibrar_mercado`, instrui a conferência) `[VERIFIED: calibrar-solo.bat lido nesta sessão]`.

**Fluxo da ferramenta (decisões travadas + precedentes):** entrada = pasta de gravação do spike (`--frame recordings/...-mercado-aberto/frame_000012.png` ou a pasta com escolha do frame); seleção de regiões com `cv2.selectROI` (precedente `calibrar_selecionando`, `calibrar.py:363-385`); recorte dos templates de dígito e nomes-como-renderizados da própria gravação; **matriz de confusão medida na hora** (todo template × todo template; pior score inter-classe registrado; limiar acima dele com margem; recusar ALTO na calibração se dois itens da watchlist colidem em forma truncada — Pitfall 7.3); imagem de conferência com todos os retângulos desenhados via `_gravar_conferencia`; `cal.salvar()` regrava o `calibration.json` inteiro (a ferramenta parte do arquivo existente, como o modo solo faz — `calibrar.py:637-664`).

## Architecture Patterns

### Diagrama — um sinal, dois consumidores, e o gate externo

```
BLOCO A (construível agora)                    BLOCO B (pós-gravações do usuário)
┌──────────────────────────────┐               ┌─────────────────────────────────────┐
│ FUND-01 gravador.py          │               │ SPIKE-RESPOSTAS.md                  │
│  - imwrite checado           │               │  (Claude analisa frames, cita       │
│  - contador = confirmados    │    usuário    │   evidência; usuário valida)        │
│  - modo janela-completa      │    grava      │                                     │
│ FIRE-01 test_firewall_escopo │──[CHECKPOINT]►│ FUND-03 calibrar_mercado.py         │
│ ROTEIRO-SPIKE.md             │   8 sessões   │  regiões + âncora + templates +     │
│ (opcional: medição prévia    │   rotuladas   │  matriz de confusão → calibration   │
│  da âncora sobre inv3)       │               │  .json (chaves .get, versão 2)      │
└──────────────────────────────┘               │                                     │
                                               │ DETC-01 mercado_visao.py            │
        recordings/inv3 (JÁ NO DISCO)          │  mercado_aberto(recorte, cal)->bool │
        10 frames _JANELA com o painel ───────►│  = âncora positiva, função pura     │
        + leitura.txt do desastre              └───────────────┬─────────────────────┘
                                                               │ UM sinal
                                          ┌────────────────────┴────────────────────┐
                                          ▼                                         ▼
                              consumidor 1 (Fase 4):                consumidor 2 (ESTA fase):
                              laço --mercado usa como               caminho da party trata como
                              interruptor idle/ativo                oclusão CONHECIDA (extra
                                                                    opcional + campo exibicional)
                                          verificação: pytest sobre fixtures resgatadas de inv3 —
                                          âncora dispara E zero eventos MORREU no rastreador
```

### Pattern 1: Âncora positiva por template em posição calibrada (DETC-01)

**O quê:** `mercado_aberto(recorte_da_ancora, cal) -> bool` em módulo novo e puro `l2scanner/mercado_visao.py` (mesmo charter de `visao.py:1-7`: sem relógio, sem rede, sem disco, sem decisão). Correlação do recorte contra o template gravado, **no alinhamento calibrado, posição única** — a lição medida de `identidade.py`:

```python
# Precedente medido — identidade.py:187-212 [VERIFIED: lido nesta sessão]
# "[0, 0] e o molde na origem do recorte — a posicao que a calibracao gravou."
# Deslizar deu +0.000 aos casamentos certos e ate +0.373 aos ERRADOS.
return float(cv2.matchTemplate(fa, fm, cv2.TM_CCOEFF_NORMED)[0, 0])
```

Candidatos de âncora no painel real (verificados no `f000_JANELA.png`): a faixa de título "XM Market" ou a linha de cabeçalhos de coluna "Goods|Quantity|Total|Unit price" — ambos sempre presentes com o painel aberto, sobre fundo opaco do próprio painel (não sobre terreno variável, ao contrário dos nomes da party — condição MELHOR que a que já deu correlação 1.000). A escolha final e o limiar saem MEDIDOS das fixtures, com a margem escrita no módulo ao lado da constante (estilo `visao.py:186-193`).

**Custo por tick:** correlação em posição única sobre um recorte pequeno é da ordem de microssegundos (a análise inteira da party custa 0,7 ms; a busca de matchTemplate na janela INTEIRA custa ~45 ms e por isso o vigia do cliente só roda a cada 5 s — `[VERIFIED: captura_janela.py:38-43]`). Se o spike mostrar que o painel é ARRASTÁVEL (posição não fixa — pergunta aberta), o fallback é busca em faixa com cadência limitada, precedente `SEGUNDOS_ENTRE_BUSCAS_DO_DIALOGO = 5.0`.

**Consumo no caminho da party (o segundo consumidor):** a região da âncora entra como **extra opcional** — o trilho exato do `banner_manutencao` em `__main__.py:1436-1442` (só entra no dict de extras quando a calibração tem a chave) `[VERIFIED: lido nesta sessão]`. O resultado vira um campo novo em `Observacao` no molde de `estado_do_cliente`/`hp_proprio_aparente` (campo opcional, default `None`/`False`, sem NENHUM consumidor de decisão no rastreador nesta fase — serve ao console/log como "painel de mercado aberto — oclusão conhecida" e à regressão). **Proibições herdadas com evidência:** jamais estender `barra_propria_legivel`/`_moldura_da_barra_propria`/`_bordas_da_barra_intactas` — a lição do consumidor único está medida e escrita em `visao.py:85-111` (o campo `hp_proprio_aparente` existe porque promover um sinal a segundo uso produziu 2 classes de alerta falso e atraso de morte SIMULADOS); o tripwire de arquitetura em `tests/test_inventario_por_cima_da_barra_propria.py` quebra se `rastreador.py` passar a ler campo proibido `[VERIFIED: visao.py:79-111]`.

### Pattern 2: Regressão por fixtures resgatadas (o "replay do 27x")

**O quê:** teste pytest que percorre os frames do incidente e afirma as duas metades do critério 4: (1) `mercado_aberto(...)` responde `True` nos frames com painel; (2) o pipeline `extrair` → `Rastreador.observar` não emite NENHUM evento de morte na sequência inteira.

**Como, com os materiais reais:**
- Resgatar de `recordings/inv3/` para `tests/fixtures/mercado/` os recortes necessários: da âncora (dos 10 `_JANELA`), da barra própria (região `hp_proprio` da calibração aplicada aos `_JANELA`), e os recortes de party `f0NN.png` que alimentam `extrair`. Manter os testes de população grande atrás de `pytest.skip` quando `recordings/` não existe — padrão literal de `TestOCasamentoNasFixturesVERSIONADAS` `[VERIFIED: test_inventario_por_cima_da_barra_propria.py:858-935]`.
- Aquecer o rastreador com pixels reais antes da sequência coberta — precedente `frame_de_party()` (`limpo.png` + extras) `[VERIFIED: test_inventario_por_cima_da_barra_propria.py:518-537]`.
- Nota honesta para o planner: a metade "zero mortes" já é garantida HOJE pelo portão de moldura do quick 260826-dxm (as `coberta_0..3` vêm do mesmo material). O que o DETC-01 ADICIONA é a identificação positiva ("é o mercado, oclusão conhecida") sobre a mesma sequência — o teste novo prende as duas coisas juntas para que nenhuma regressão futura desfaça uma delas isoladamente.

### Pattern 3: Estrutura de planos em torno do gate externo

O bloqueio é estrutural (só o usuário grava) e a ordem é travada no CONTEXT: fix do gravador + firewall + roteiro → **PAUSA** → análise/calibração/detecção. Recomendação de estrutura:

| Plano | Conteúdo | Depende de |
|---|---|---|
| 01 (Bloco A) | FUND-01 completo (fix + modo janela-completa + testes) e FIRE-01 (`test_firewall_escopo.py` + teste-do-teste) | nada |
| 02 (Bloco A) | `ROTEIRO-SPIKE.md` (8 cenários rotulados, instruções de duração ~30-60s pelo custo de 3,5 MB/frame) + **medição preliminar da âncora sobre inv3** (de-risking: margens medidas ANTES de o usuário gravar) + **checkpoint: usuário grava as sessões** | 01 (o gravador precisa estar consertado ANTES de gravar — ordem travada) |
| 03 (Bloco B) | `SPIKE-RESPOSTAS.md` (Claude analisa, cita frames; usuário valida) + FUND-03 (`calibrar_mercado.py` + `.bat` + chaves + templates + matriz de confusão) + DETC-01 (âncora final + extra opcional + campo em `Observacao` + regressão do 27x com fixtures resgatadas) | 02 (gravações no disco) |

A medição preliminar sobre inv3 no plano 02 é opcional mas barata e valiosa: os 10 frames `_JANELA` já contêm o painel, então a técnica da âncora pode ser validada com números reais sem esperar o usuário — e se a margem for ruim, o ROTEIRO ainda pode ser ajustado antes das gravações (ex.: pedir um cenário extra).

### Anti-Patterns a evitar (com a evidência do porquê)

- **Estender o gate de brilho da barra própria para detectar o mercado** — decisão travada + lição medida (`visao.py:85-111`): tudo que aquele casamento certifica pode ser recorte parcialmente ocluído (`coberta_0` casa +0.999 lendo 86,91%).
- **`--replay recordings/inv3` como verificação** — glob incompatível (`frame_*.png` vs `f0NN.png`); harness pytest é o caminho.
- **Testes permanentes apontando para `recordings/`** — gitignored; clone limpo fica vermelho. Resgatar fixtures + `pytest.skip` documentado.
- **Templates de mercado em `l2scanner/recursos/`** — recursos é versionado; calibração é da máquina.
- **`imwrite` novo em `calibrar.py` fora de `_gravar_conferencia`** — o teste estrutural conta ocorrências no fonte do módulo e cai `[VERIFIED: test_conferencia_gravada.py:217-227]`.
- **Firewall varrendo só `md.distributions()` do processo do pytest** — varre o Python global, não o venv de produção (verificado nesta sessão). Usar também `path=[.venv/Lib/site-packages]` + requirements.txt.
- **Exceção de gravação escapando de `Sessao.tick`** — o laço não tem try/except no tick; derrubaria os alertas por causa de disco cheio. Falha alta = log ERROR + contador de falhas + resumo com a verdade do disco, processo vivo.
- **Subir `VERSAO_DO_ESQUEMA` para 3** — invalidaria a calibração medida à mão do usuário por causa de campos opcionais (razão documentada em `calibracao.py:196-206`).

## Don't Hand-Roll

| Problema | Não construir | Usar em vez | Por quê |
|----------|---------------|-------------|---------|
| Enumerar pacotes instalados | parser de `pip freeze`/varredura manual de site-packages | `importlib.metadata.distributions()` (+ `path=` para o venv) | stdlib, verificado nesta sessão nos dois ambientes |
| Ler nomes/dígitos do painel | OCR aberto | template de conjunto fechado (`identidade.py`, margens 1.000 vs 0.454 medidas) | decisão de projeto já vencedora; OCR falha ABERTO (inventa) |
| Detectar o painel | heurística de brilho/borda genérica | template de âncora em posição calibrada (`_correlacionar` posição única) | brilho é sinal NEGATIVO ambíguo (inventário/ficha/loja leem igual — `visao.py:230-234`); deslizar dá +0.373 só aos casamentos errados |
| Persistir template | codec/formatos próprios | hex-bits no JSON (padrão `Assinatura.como_dict`) | precedente no repo, sem dependência de codec |
| Conferência visual da calibração | novo caminho de escrita de imagem | `_gravar_conferencia` (fallback + verdade sobre falha já resolvidos) | é literalmente o fix do mesmo bug que FUND-01 corrige no gravador |
| Overlay/seleção de regiões | UI própria | `cv2.selectROI` + `cv2.rectangle` (precedentes em `calibrar.py`) | já é o estilo travado pela decisão do usuário |

## Common Pitfalls

### Pitfall 1: Consertar o contador e esquecer o JSONL
**O que dá errado:** o fix checa `imwrite` e condiciona `frames_gravados`, mas a linha do `observacoes.jsonl` continua saindo — o replay e a auditoria leem um índice que cita arquivo inexistente.
**Como evitar:** escrita confirmada é o gate das TRÊS saídas (contador, JSONL, resumo). Teste: pasta com nome ocupado por diretório → 0 contados, 0 linhas no JSONL, erro visível.

### Pitfall 2: Gravar o spike com o `--record` atual e descobrir tarde que só há party window nos PNGs
**O que dá errado:** o usuário gasta as sessões (o recurso escasso da fase) e as gravações não contêm o painel.
**Como evitar:** o modo janela-completa é PRÉ-REQUISITO do ROTEIRO; o próprio ROTEIRO instrui uma sessão de teste de 5 s e a conferência visual de um PNG antes das sessões reais. Warning sign: PNG de ~170 KB (recorte) em vez de ~3,5 MB (janela).

### Pitfall 3: Firewall verde para sempre porque varre o ambiente errado
**O que dá errado:** teste varre só `md.distributions()` do processo → global; `pip install pyautogui` no `.venv` passa despercebido (ou vice-versa).
**Como evitar:** três varreduras (requirements.txt, ambiente corrente, `.venv` via `path=`); teste-do-teste injetando distribuição banida falsa; skip com razão quando `.venv` não existe (CI/clone limpo).

### Pitfall 4: Âncora recortada de UMA condição e limiar sem negativo
**O que dá errado:** template cortado só do `mercado-aberto` casa mal sob tooltip/marcação de alvo, ou — pior — um painel DIFERENTE (ficha, loja) casa fraco mas acima de um limiar chutado.
**Como evitar:** medir o limiar contra negativos reais: frames `mercado-fechado`, frames com OUTROS painéis (o material do inv2/inventario serve), e as variantes de oclusão parcial do roteiro. Registrar a margem no módulo, estilo `visao.py`.

### Pitfall 5: Regressão do 27x que passa por motivo errado
**O que dá errado:** o teste "zero mortes" já passa HOJE (portão de moldura do dxm) — um teste que só afirma isso não prende o DETC-01.
**Como evitar:** o teste afirma as DUAS metades: âncora dispara nos frames com painel E zero eventos de morte; mais um teste de mutação mental: sem a âncora, a primeira metade cai.

### Pitfall 6: Ferramenta de calibração que grava JSON parcial ou pede edição manual
**O que dá errado:** critério 3 exige "sem editar JSON à mão"; uma ferramenta que imprime valores para o usuário colar viola o critério e o precedente (a calibração é regravada INTEIRA por `cal.salvar`).
**Como evitar:** a ferramenta carrega a calibração existente, muta os campos de mercado e regrava — trilho do modo solo (`calibrar.py:637-664`).

## Code Examples

### FUND-01 — forma sugerida do fix (discrição de Claude, contrato fixo)

```python
# gravador.py — o contrato: contador só conta escrita CONFIRMADA;
# falha é visível e não derruba o tick.
def gravar(self, frame: Frame, momento: float) -> bool:
    import cv2
    caminho = self.pasta / f"frame_{frame.indice:06d}.png"
    try:
        gravou = bool(cv2.imwrite(str(caminho), frame.pixels))
    except Exception:            # mesmo caminho de falha do False documentado
        gravou = False           # (padrão calibrar.py:407-414)
    if not gravou:
        self.falhas_de_gravacao += 1
        return False             # quem loga ALTO é o chamador/Sessao — decisão do planner
    # JSONL SÓ para frames confirmados
    ...linha + flush...
    self.frames_gravados += 1
    return True
```

### FIRE-01 — as chamadas verificadas nesta sessão

```python
import importlib.metadata as md
# ambiente que roda a suíte (global hoje):
instaladas = {(d.metadata["Name"] or "").lower() for d in md.distributions()}
# venv de produção, de QUALQUER interpretador (verificado):
no_venv = {(d.metadata["Name"] or "").lower()
           for d in md.distributions(path=[r".venv\Lib\site-packages"])}
```

### DETC-01 — correlação em posição calibrada (precedente literal)

```python
# identidade.py:207-212 — replicar para a âncora do painel
fa, fm = alvo.astype(np.float32), molde.astype(np.float32)
if fa.std() < 1e-6 or fm.std() < 1e-6:
    return 0.0
return float(cv2.matchTemplate(fa, fm, cv2.TM_CCOEFF_NORMED)[0, 0])
```

## Environment Availability

| Dependência | Exigida por | Disponível | Versão | Fallback |
|-------------|-------------|------------|--------|----------|
| `.venv` Python | produção (`vigiar-party.bat`) | ✓ | 3.12.10 | — |
| Python global + pytest | suíte de testes (1166 testes coletam) | ✓ | 3.12.x / pytest 9.1.1 | — |
| cv2/numpy/mss/windows-capture | tudo | ✓ (nos dois ambientes) | pins do requirements | — |
| `calibration.json` v2 | replay/derivação de recortes do inv3 | ✓ (raiz, janela "Yazalaque - XM Essence", `hp_proprio` presente) | v2 | conferir geometria vs inv3 na execução |
| `recordings/inv3` (27x) | DETC-01 regressão + medição prévia | ✓ (45 crops + 10 `_JANELA` + leitura.txt) | — | gitignored: resgatar para `tests/fixtures/` |
| Gravações do World Exchange (8 cenários) | FUND-02/03, DETC-01 final | ✗ — **só o USUÁRIO produz** | — | NENHUM. É o gate externo da fase |
| Disco para o spike | gravação janela-completa | ~3,5 MB/frame ≈ 210 MB/min | — | sessões de 30–60 s por cenário no ROTEIRO |

**Dependência sem fallback:** as gravações do usuário — o plano DEVE modelar o checkpoint explicitamente.

## Security Domain

Fase sem superfície de rede, sem autenticação e sem entrada externa não confiável — o escopo de ASVS aplicável é estreito e o controle central da fase É um controle de segurança:

| Categoria ASVS | Aplica | Controle |
|----------------|--------|----------|
| V1/V14 Configuração & supply chain | **sim** | FIRE-01 é um controle de cadeia de suprimentos: banlist de bibliotecas de síntese de input verificada em CI/suíte (requirements + ambientes instalados). É a materialização do requisito de segurança fundador do projeto (zero input ao jogo = zero risco de ban) |
| V5 Validação de entrada | sim (limitada) | `calibration.json` parseado com recusa de versão e `CalibracaoInvalida` alta (`calibracao.py:316-366`, já existente); chaves novas seguem o mesmo trilho; templates hex decodificados com dimensões declaradas (padrão `Assinatura.de_dict`) |
| V2/V3/V4 Auth/Sessão/Acesso | não | sem usuários, sem rede nesta fase |
| V6 Criptografia | não | nada cifrado nesta fase |
| Dados locais | sim (nota) | gravações contêm nomes de personagens e chat do jogo; permanecem locais e gitignored — não commitá-las além dos recortes mínimos resgatados como fixture |

Padrões de ameaça relevantes: o único vetor real é o retorno silencioso de biblioteca de input via dependência transitiva — coberto pela varredura de instalados + Requires-Dist (FIRE-01).

## Assumptions Log

| # | Afirmação | Seção | Risco se errado |
|---|-----------|-------|-----------------|
| A1 | O painel XM Market abre em posição FIXA na janela (âncora em retângulo calibrado basta; sem busca) | Pattern 1 | Se for arrastável, âncora fixa falha silenciosamente com painel movido → fallback: busca em faixa com cadência (precedente 5 s do diálogo). **Responder no spike** |
| A2 | A aba "Adena" do XM Market é o "World Exchange" de adena, com formato de número próprio (separador de milhar etc.) possivelmente diferente do "40,00 XM Coin" verificado na aba Equipment | Descoberta 3 | Templates de dígito calibrados na aba errada; o ROTEIRO já manda gravar a aba de adena — **responder no spike** |
| A3 | `Distribution.requires` (Requires-Dist) é parseável de forma tolerante para a varredura transitiva declarada | Descoberta 4 | Varredura transitiva declarada vira best-effort; as varreduras de instalados (que são o mecanismo principal) não dependem disso |
| A4 | A geometria do `calibration.json` atual corresponde aos frames de `recordings/inv3` (janela 1720×1392) para derivar recortes | Pattern 2 | Recortes derivados errados → o teste de regressão mede a região errada; verificação explícita no plano (conferir dimensões + inspeção visual de um recorte) |
| A5 | O painel é totalmente opaco (template estável independente do cenário atrás) | Descoberta 3 | Se houver translucidez em alguma região, a âncora deve ser cortada da faixa de título (visivelmente opaca no frame verificado); margem medida denuncia |

## Open Questions (viram perguntas do ROTEIRO/SPIKE)

1. **A aba Adena: layout, separador de milhar, decimais, moeda, colunas** — o frame verificado é da aba Equipment (XM Coin, vírgula decimal, colunas Total + Unit price). O que muda na aba de adena?
2. **Posição do painel: fixa ou arrastável?** (A1) — decide âncora fixa vs busca em faixa.
3. **Linhas por página e aparência do slot vazio** — o frame mostra ~10 slots/3 preenchidos; confirmar por aba e com página cheia.
4. **Preço médio embutido: onde fica?** — não visível no frame verificado; pergunta mínima do CONTEXT.
5. **Idade do listing é exibida?** — não visível no frame verificado.
6. **Renderização do encanto `+N` na LISTA do mercado** (confirmada pelo usuário no jogo; validar com frame, incluindo truncamento de nomes longos com o prefixo).
7. **Tooltip e marcação de alvo: o que exatamente cobrem?** — cenários dedicados do roteiro; alimentam o limiar negativo da âncora e o estabilizador da Fase 2.

## Sources

### Primárias (HIGH — verificadas nesta sessão)
- `l2scanner/gravador.py`, `frames.py`, `sessao.py:140-259`, `__main__.py:1410-1800`, `captura_janela.py:30-60,340-421`, `visao.py`, `identidade.py`, `calibracao.py`, `calibrar.py`, `cliente.py` (trechos) — lidos integralmente ou nas faixas citadas
- `tests/test_conferencia_gravada.py`, `tests/test_inventario_por_cima_da_barra_propria.py` (faixas citadas) — padrões de teste
- **Execução empírica na máquina-alvo (2026-08-27):** versões dos dois Pythons; distribuições instaladas nos dois ambientes; `distributions(path=...)` cruzando ambientes; coleta da suíte (1166 testes); dimensões e tamanhos dos frames de `recordings/inv3`
- **Inspeção visual de `recordings/inv3/f000_JANELA.png`** — conteúdo do painel XM Market; `recordings/inv3/leitura.txt` e `recordings/inventario/leitura.txt`
- `.gitignore`, `requirements.txt`, `calibration.json` (estrutura), `calibrar.bat`/`calibrar-solo.bat`/`vigiar-party.bat`, `.planning/config.json`
- `.planning/quick/260826-dxm-.../260826-dxm-SUMMARY.md` — forense do incidente e padrões (tripwire de medição, verificação por mutação)

### Secundárias (MEDIUM — pesquisa de milestone já feita, não refeita)
- `.planning/workstreams/mercado/research/SUMMARY.md`, `ARCHITECTURE.md`, `PITFALLS.md`, `STACK.md` — camadas, pitfalls numerados, verificação empírica de SQLite/Python (fases seguintes)

### Terciárias (LOW/UNVERIFIED)
- Especificidades da aba Adena do XM Market e comportamento de arrasto do painel — gated no spike (Open Questions)

## Metadata

**Confidence breakdown:**
- FUND-01 (fix + testes): HIGH — bug, padrão de fix e padrão de teste todos no repo, medidos nesta máquina
- FUND-02 (gravação): HIGH no mecanismo (capturar_completo verificado; custo medido); a execução depende do usuário (gate externo, não incerteza técnica)
- FIRE-01: HIGH — APIs executadas nesta sessão nos dois ambientes reais
- FUND-03: HIGH nos trilhos (esquema, tripwire, precedentes); MEDIUM no conteúdo dos templates (depende dos frames do spike)
- DETC-01: HIGH na técnica e no material de regressão (inv3 verificado visualmente); MEDIUM no limiar/posição da âncora (medir nas fixtures; A1/A5)

**Research date:** 2026-08-27
**Valid until:** ~30 dias (código interno estável; nenhuma dependência externa em movimento). As respostas do spike substituem as seções [ASSUMED] assim que as gravações existirem.
