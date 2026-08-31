# Requirements: Aviso de nascimento de boss raro

**Defined:** 2026-08-30
**Workstream:** tiat
**Core Value:** A party fica sabendo no WhatsApp que o Tiat nasceu, em segundos, sem ninguem estar olhando a tela.

## Contexto herdado (o que ja existe e NAO se reconstroi)

`l2scanner/tiat.py` ja detecta a palavra `Tiat` no chat e no alvo, ja tem
debounce por rearme (duas leituras limpas), ja esta ligado em
`sessao._processar_tiat` e ja despacha com `Categoria.SEMPRE` — atravessando o
silencio de TvT. O caminho ate o WhatsApp esta inteiro e testado (7 testes).

O que falta nao e o encanamento: e a PRECISAO do que ele reconhece e a
previsao da proxima janela.

## v1 Requirements

### Reconhecimento (RECO)

- [ ] **RECO-01**: O disparo exige a frase completa do anuncio do servidor
      (`<Nome> [Lv. NN] has spawned!`), nao a mera presenca do nome. Alguem
      digitando "tiat" no chat geral NAO gera alerta.
- [ ] **RECO-02**: O nome capturado distingue `Tiat North` de `Tiat South`, e a
      mensagem do WhatsApp diz QUAL nasceu — sao dois bosses diferentes e a
      party se desloca para lugares diferentes.
- [ ] **RECO-03**: A deteccao pelo ALVO continua valendo e tambem identifica
      qual dos dois, lendo o nome do alvo selecionado.
- [ ] **RECO-04**: A normalizacao de OCR existente (I/1/l, A/4/@, T/7) continua
      valendo sobre o nome, para a fonte fina do jogo nao derrubar o
      reconhecimento.
- [ ] **RECO-05**: Chat e alvo detectando o mesmo boss no mesmo instante geram
      UM alerta, nao dois.

### Vigilancia configuravel (VIGI)

- [ ] **VIGI-01**: A lista de bosses vigiados mora no `config.toml`, no mesmo
      molde dos `[[evento]]` da agenda. Acrescentar um mob novo e acrescentar
      um bloco — nunca editar codigo.
- [ ] **VIGI-02**: Cada boss declara seu nome como aparece no jogo e a regra de
      respawn (minimo e maximo de horas). O Tiat entra com 6h e 8h.
- [ ] **VIGI-03**: Um bloco mal escrito faz o scanner recusar a subir dizendo
      qual boss e qual campo — nunca subir vigiando errado em silencio.
- [ ] **VIGI-04**: Com a lista vazia, a vigilancia de boss fica desligada e o
      arranque diz isso, do mesmo jeito que ja diz sobre o aviso de Tiat hoje.

### Janela de respawn (JANE)

- [ ] **JANE-01**: Ao detectar um nascimento, o scanner grava o horario em
      disco, de forma duravel, sobrevivendo a reinicio e as duas instancias.
- [ ] **JANE-02**: O scanner avisa no WhatsApp quando a janela ABRE (minimo de
      horas apos o nascimento anterior) e de novo quando ela FECHA (o maximo),
      para a party saber que passou da hora.
- [ ] **JANE-03**: A mensagem da janela e HONESTA sobre a origem do numero: ela
      cita o NASCIMENTO que ancorou a conta, nunca promete um horario exato.
      A ancora e o nascimento, nao a morte, e o erro de cada ciclo e quanto
      tempo o boss ficou vivo — o texto nao pode esconder isso.
- [ ] **JANE-04**: Um nascimento novo reancora a conta e cancela os avisos de
      janela pendentes do ciclo anterior.
- [ ] **JANE-05**: Os avisos de janela funcionam com o jogo FECHADO, pelo
      relogio, do mesmo jeito que a agenda de TvT — quem esta offline e
      justamente quem mais precisa do lembrete.
- [ ] **JANE-06**: Cada aviso sai UMA vez, mesmo com as duas instancias do
      usuario rodando lado a lado e mesmo apos reiniciar o scanner.

### Operacao (OPER)

- [ ] **OPER-01**: O `calibrar-tiat.bat` continua marcando as duas regioes e
      passa a valer para qualquer boss da lista — a regiao e do CHAT e do
      ALVO, nao de um mob especifico.
- [ ] **OPER-02**: O console mostra, no arranque, quais bosses estao sendo
      vigiados e qual a proxima janela prevista, se houver.
- [ ] **OPER-03**: Tudo e demonstravel sem o jogo aberto e sem rede: o tempo
      entra por parametro e o texto do OCR entra por dado.

### Unicidade do aviso (UNIC)

Derivados em 2026-08-30 a partir do DEFEITO DE CAMPO da Fase 3: seis mensagens
de WhatsApp para um unico nascimento de `Tiat South`, com as duas instancias do
usuario rodando e ele remarcando o boss no alvo.

Nao sao requisitos "novos" no sentido de funcionalidade nova. Sao a lacuna que
RECO-05 deixou: ele pedia "chat e alvo no mesmo tick geram UM alerta", e
ninguem escreveu "UM alerta por nascimento, entre instancias e entre reinicios".
E por isso que nenhum teste pegou.

- [ ] **UNIC-01**: O aviso de nascimento passa por um marcador duravel em
      `.agenda/`. Duas instancias sobre a mesma pasta produzem UMA mensagem por
      nascimento, e reiniciar qualquer uma delas nao reenvia. A decisao de
      despachar E a chamada de `marcar`, nunca uma checagem anterior.
- [ ] **UNIC-02**: O anuncio do CHAT nunca e calado pelo estado de deduplicacao
      do ALVO — nem em memoria nem em disco. O anuncio do servidor e o unico
      sinal que existe quando ninguem esta olhando a tela.
- [ ] **UNIC-03**: O ALVO so anuncia se o chat nao anunciou aquele boss no
      episodio corrente. Com o chat tendo falado, remarcar o boss vinte vezes
      produz zero mensagem nova.
- [ ] **UNIC-04**: Sem o chat ter falado (scanner fechado na hora do anuncio, ou
      OCR falhou), o alvo anuncia — UMA vez. O fallback continua existindo.
- [ ] **UNIC-05**: Depois de anunciado, o boss fica em silencio ate o proximo
      nascimento voltar a ser POSSIVEL pela regra do `[[boss]]`, e nao mais que
      isso. O que se perde e o mesmo boss nascer duas vezes dentro da mesma
      janela, impossivel pela regra do servidor.
- [ ] **UNIC-06**: A ancora continua sendo gravada como hoje, inclusive pelo
      alvo e inclusive quando o anuncio e suprimido. D-15 e D-16 seguem valendo:
      esta familia muda o ANUNCIO, nao a ancoragem.
- [ ] **UNIC-07**: O prefixo novo entra em `_PREFIXOS_CONHECIDOS` e na poda, e o
      guarda derivado por introspecao continua verde. Um marcador de silencio
      imortal calaria aquele boss para sempre.
- [ ] **UNIC-08**: Tudo demonstravel com o jogo fechado e sem rede.

## v2 Requirements

- **MORT-01**: Comando `/morreu <boss>` (com horario opcional) para reancorar a
  janela na MORTE em vez do nascimento, eliminando o erro do tempo em que o
  boss ficou vivo. Descartado no v1 por decisao do usuario: ele prefere zero
  esforco manual. Fica registrado porque e o unico jeito de a previsao ficar
  exata.
- **APRE-01**: Aprender o tempo tipico entre nascimento e morte a partir do
  historico, e descontar isso da previsao.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Ler memoria do jogo ou pacotes para saber o spawn | Restricao dura do projeto: deteccao 100% passiva por tela |
| Prever o horario exato do nascimento | A regra tem 2h de aleatoriedade REAL do servidor; prometer exatidao seria mentir |
| Detectar a morte do boss pela tela | Nao ha sinal visual confiavel conhecido; o usuario optou por ancorar no nascimento |
| Avisar sobre mobs comuns | Volume de mensagem inviabiliza; a lista e para boss raro |

## Traceability

Preenchida na criacao do roadmap (2026-08-30). Ver `ROADMAP.md`.

| Requirement | Phase | Status |
|-------------|-------|--------|
| RECO-01 | Phase 1 | Pending |
| RECO-02 | Phase 1 | Pending |
| RECO-03 | Phase 1 | Pending |
| RECO-04 | Phase 1 | Pending |
| RECO-05 | Phase 1 | Pending |
| VIGI-01 | Phase 1 | Pending |
| VIGI-02 | Phase 1 | Pending |
| VIGI-03 | Phase 1 | Pending |
| VIGI-04 | Phase 1 | Pending |
| OPER-01 | Phase 1 | Pending |
| JANE-01 | Phase 2 | Pending |
| JANE-02 | Phase 2 | Pending |
| JANE-03 | Phase 2 | Pending |
| JANE-04 | Phase 2 | Pending |
| JANE-05 | Phase 2 | Pending |
| JANE-06 | Phase 2 | Pending |
| OPER-02 | Phase 2 | Pending |
| OPER-03 | Phase 2 | Pending |
| UNIC-01 | Phase 3 | Pending |
| UNIC-02 | Phase 3 | Pending |
| UNIC-03 | Phase 3 | Pending |
| UNIC-04 | Phase 3 | Pending |
| UNIC-05 | Phase 3 | Pending |
| UNIC-06 | Phase 3 | Pending |
| UNIC-07 | Phase 3 | Pending |
| UNIC-08 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 26 total (18 do roadmap original + 8 da Fase 3)
- Mapped to phases: 26
- Unmapped: 0

**Nota sobre a familia UNIC:** ela nasceu depois de as Fases 1 e 2 terem sido
verificadas e aprovadas, a partir de um defeito medido em campo. Os oito
requisitos sao a escrita explicita de uma propriedade que o milestone assumia
sem nunca ter afirmado: um nascimento produz um alerta, e nao um alerta por
processo por deteccao. Ver `phases/03-*/03-CONTEXT.md` para as seis mensagens
reais e as duas causas independentes.

**Nota sobre OPER-02:** o requisito e da Fase 2 porque so ali ele existe
inteiro — a metade "proxima janela prevista" depende da ancora. A metade
"quais bosses estao sendo vigiados" e entregue na Fase 1 por VIGI-04.

**Nota sobre OPER-03:** a disciplina ja vale na Fase 1 por heranca
(`VigiaDoTiat` recebe `agora` e um `ler_texto` injetavel). O requisito e da
Fase 2 porque e la que nasce um modulo com logica de tempo que precisa ENTRAR
no portao AST de relogio.

---
*Requirements defined: 2026-08-30*
