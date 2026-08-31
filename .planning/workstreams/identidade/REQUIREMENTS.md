# Requirements: O scanner aprende quem e a party sozinho

**Defined:** 2026-08-30
**Workstream:** identidade
**Core Value:** Trocar a composicao da party deixa de exigir uma rodada de calibracao.

## O problema, medido e nao suposto

Hoje o usuario roda `calibrar.bat --nomes "A,B,C,D"` toda vez que a party muda.
O `identidade.py` grava uma assinatura de imagem por nome e depois RECONHECE
qual dos N conhecidos esta em cada linha. Isso funciona bem — medido:

| Metodo | Mesmo nome | Outro nome | Margem |
|---|---|---|---|
| mascara de texto, recorte justo | **1.000** | **0.454** | **0.546** |

**OCR NAO substitui isso, e foi medido hoje** contra a party real do usuario
(`Welazkez`, `TiTANDER`, `Mostarda`, `PIRULITO`), nas duas passadas que o
projeto tem:

| Esperado | OCR 2x | OCR 3x |
|---|---|---|
| Welazkez | `Welazkez` OK | `V Welazkez` |
| TiTANDER | `ITANDEk` | `iTANDEk` |
| Mostarda | `bstarda` | `bstarda` |
| PIRULITO | `IRUUTO` | `IRUUTO` |

**1 acerto em 4.** A mascara de texto do `identidade.py` zera o OCR (ela e
binaria; serve para correlacao, nao para leitura). Ler o nome esta fora de
questao — e por isso este workstream ataca o CADASTRO, nao a leitura.

O perigo ja esta resolvido e nao e o alvo: quando o reconhecimento falha nasce
uma chave `#linhaN`, e o `rastreador.py` recusa anunciar em nome dela — "um
evento sem sujeito". Ele cala em vez de mentir. O que sobra e o INCOMODO.

## v1 Requirements

### Aprendizado (APRE)

- [x] **APRE-01**: Ao ver uma linha cuja imagem de nome nao casa com nenhuma
      assinatura conhecida, o scanner GRAVA essa assinatura sozinho, sem
      calibracao e sem intervencao.
- [x] **APRE-02**: A assinatura so e gravada depois de estavel por N frames.
      O texto e transparente e o cenario anda por tras dele; gravar no primeiro
      frame guardaria terreno junto com o nome.
- [x] **APRE-03**: Uma assinatura recem-aprendida NAO recebe nome automatico e
      NAO vira sujeito de alerta. Ate ser batizada ela e uma linha anonima, e
      o comportamento de calar continua valendo.
- [x] **APRE-04**: Aprender a mesma pessoa duas vezes (ela sai e volta) nao
      cria duas assinaturas: o casamento contra as ja gravadas vem antes.

### Batismo pelo WhatsApp (BATI)

- [x] **BATI-01**: Ao aprender uma assinatura nova, o scanner PERGUNTA no
      WhatsApp quem e, citando a posicao onde a viu.
- [x] **BATI-02**: O usuario responde por comando e a assinatura recebe o nome.
      A partir dali os alertas daquela pessoa saem com o nome certo.
- [x] **BATI-03**: A resposta e casada com a assinatura PINADA no momento da
      pergunta, nunca com "a linha 3 de agora". A party se reorganiza entre a
      pergunta e a resposta, e resolver por posicao batizaria a pessoa errada —
      que e exatamente a mentira plausivel que o `identidade.py` existe para
      impedir.
- [ ] **BATI-04**: Batizar duas assinaturas com o mesmo nome e recusado,
      dizendo qual ja tem aquele nome.
- [ ] **BATI-05**: Um batismo errado pode ser corrigido sem recalibrar.

### Durabilidade (DURA)

- [x] **DURA-01**: As assinaturas aprendidas SOBREVIVEM a `calibrar.bat`.
      ISTO E O REQUISITO QUE MATA A FEATURE SE FALHAR. Ver WINDOWS #13,
      confirmado em campo em 2026-08-30: `calibrar.py` monta uma `Calibracao`
      do zero e grava por cima do arquivo inteiro; o usuario rodou
      `calibrar.bat` e perdeu 13 moldes de glifo e 3 ancoras do mercado. Uma
      assinatura aprendida por semanas nao pode morrer numa recalibracao de
      party.
- [x] **DURA-02**: Sobrevivem a reinicio do scanner.
- [x] **DURA-03**: As duas instancias do usuario (Yazalaque e Faerlina)
      aprendem sobre o mesmo acervo sem corromper nem duplicar.
- [x] **DURA-04**: O acervo NAO e podado por tempo. Assinatura e igual a
      estatistica de loot: "quem e o Fulano" e uma pergunta sobre meses.

### Operacao (OPER)

- [x] **OPER-01**: O arranque diz quantas assinaturas conhece e quantas estao
      sem nome.
- [x] **OPER-02**: `--nomes` continua funcionando. Quem prefere digitar segue
      digitando; o aprendizado e adicional, nao substituto.
- [x] **OPER-03**: Demonstravel sem jogo aberto e sem rede.

## v2 Requirements

- **OCRB-01**: O OCR PROPOR o nome no momento do batismo, como chute a
  confirmar. Medido em 1 de 4 hoje — util como atalho, inutil como fonte.
  So faz sentido depois que o batismo manual existir.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Ler o nick por OCR como fonte da verdade | MEDIDO: 1 acerto em 4; um glifo errado inventa membro fantasma |
| Reconhecer jogador fora da party | A party window e o unico lugar com recorte estavel e calibrado |
| Adivinhar o nome sem perguntar | Nome errado plausivel e a pior falha do produto |

## Traceability

Preenchida na criacao do roadmap em 2026-08-30.

| Requirement | Phase | Status |
|-------------|-------|--------|
| APRE-01 | Phase 2 | Complete (02-01) |
| APRE-02 | Phase 2 | Complete (02-01) |
| APRE-03 | Phase 1 | Complete |
| APRE-04 | Phase 2 | Complete |
| BATI-01 | Phase 3 | Complete (03-01) |
| BATI-02 | Phase 3 | Complete (03-01) |
| BATI-03 | Phase 3 | Complete (03-01) |
| BATI-04 | Phase 3 | Pending |
| BATI-05 | Phase 3 | Pending |
| DURA-01 | Phase 1 | Complete |
| DURA-02 | Phase 1 | Complete |
| DURA-03 | Phase 1 | Complete |
| DURA-04 | Phase 1 | Complete |
| OPER-01 | Phase 1 | Complete |
| OPER-02 | Phase 1 | Complete |
| OPER-03 | Phase 3 | Complete (03-01) |

APRE-03 caiu na Fase 1 (e nao na 2) porque o que ele exige e o TIPO — uma
assinatura sem nome precisa existir e nao produzir nome — e nao o instante do
aprendizado. OPER-03 caiu na Fase 3 porque so ali ele custa alguma coisa.
Justificativa completa em ROADMAP.md, secao Coverage.

**Coverage:** 16 requisitos, 16 mapeados, 0 orfaos.

---
*Requirements defined: 2026-08-30*
