# Fase 1 (tiat) — Verificacao humana

**Origem:** `01-VERIFICATION.md` (status `gaps_found`)
**Itens:** 2. Os dois exigem o jogo aberto; nenhum e verificavel sem ele.

Tudo o mais desta fase ja foi verificado por execucao, com o jogo fechado e sem
rede. Estes dois sobraram porque abrem janelas interativas do OpenCV, exigem
arrastar o mouse sobre a janela do jogo e ESCREVEM no `calibration.json`.

---

## 1. `calibrar-tiat.bat` continua marcando as duas regioes — e nao nomeia mob nenhum

**Contexto:** criterio 8 / OPER-01. A metade "o texto nao nomeia um mob" ja esta
provada por um guarda AST que fica VERMELHO contra o fonte de antes da fase (11
acusacoes) e VERDE hoje (zero). A metade "continua marcando as duas regioes"
nao tem teste e nao pode ter: e um caminho interativo.

O diff da fase dentro de `calibrar_tiat` mexeu **so em literais de texto** — as
duas chamadas de `_selecionar_regiao` e as duas gravacoes estao intactas. Isto
e leitura de codigo, nao execucao.

**Como testar**

1. Abra o jogo.
2. Rode `calibrar-tiat.bat`.
3. Marque a regiao 1/2 (as linhas do chat) e confirme com ENTER.
4. Marque a regiao 2/2 (somente o NOME do alvo) e confirme com ENTER.

**O que tem que acontecer**

- O console pede `1/2` e `2/2`, e diz antes que "As duas regioes valem para
  QUALQUER boss da sua lista do config.toml".
- As janelas de selecao se chamam **`Regiao do chat`** e **`Regiao do alvo`** —
  **nao** `Tiat: chat` / `Tiat: alvo`.
- **Nenhum texto na tela nomeia um mob.** Nem "Tiat", nem "North", nem "South".
- A imagem de conferencia sai com os rotulos **`CHAT`** (amarelo) e **`ALVO`**
  (verde) — nao `TIAT CHAT` / `TIAT ALVO`.
- A linha final diz "Regioes do chat e do alvo calibradas na janela ...".
- O `calibration.json` fica com `tiat_chat` e `tiat_alvo` preenchidos. (As
  CHAVES continuam com o nome antigo de proposito: renomea-las desligaria a
  vigilancia de boss em silencio em toda calibracao que ja existe.)

**Por que humano:** janela interativa do OpenCV sobre a janela do jogo, com
arrasto de mouse e escrita em disco. Nenhum teste da suite exercita isso e
nenhum poderia sem o jogo aberto.

---

## 2. A ferramenta de conferencia sem `--recorte` — confirmar a correcao de G-01

**Contexto:** este item so faz sentido **depois** que o gap G-01 for corrigido.
Hoje o comando abaixo recusa a imagem inteira e sai com codigo 1, porque
`regiao_da_calibracao` subtrai da regiao uma origem de janela que nao deveria
ser aplicada (a regiao ja esta em coordenadas de janela).

**Como testar** (depois de ter rodado o item 1)

```
.venv\Scripts\python.exe tools\conferir_anuncio_de_boss.py ^
    recordings\20260828-061409-mercado-alvo-sobreposto ^
    --regiao chat
```

(sem `--recorte`)

**O que tem que acontecer**

- A linha `regiao ...........` deve mostrar um retangulo com coordenadas
  **positivas** e compativel com o tamanho do frame.
- O `texto cru` deve sair legivel, com as linhas do chat.
- Nos frames `000011` a `000046` o veredito de `Tiat North` deve ser
  `anuncio=SIM`.
- Codigo de saida **0**.

**Referencia medida:** com `--recorte 8 878 625 455` (o proprio `tiat_chat`
usado CRU) isso ja funciona hoje. E a prova de que a subtracao e o unico
problema.

**Por que humano:** depende de o item 1 ter sido feito nesta maquina e de a
geometria da janela do jogo bater com a das gravacoes.

---

## O que NAO precisa de humano

Registrado para ninguem gastar tempo a toa. Ja foi verificado por execucao:

- O anuncio real dispara e a pergunta digitada nao (2.074 frames de chat de
  jogador de verdade, zero falso positivo; 36 frames de nascimento real, zero
  falso negativo).
- North vs. South, e a frase degradada pelo OCR.
- Chat e alvo no mesmo tick; bosses diferentes no mesmo tick; rearme por boss.
- Boss inventado no `config.toml` passando a ser vigiado sem tocar em `.py`.
- Bloco torto derrubando o arranque com codigo 2 e mensagem nomeando boss e campo.
- Lista vazia e arquivo ausente subindo com codigo 0 e a linha que diz como ligar.
- O texto da calibracao nao nomear um mob.
