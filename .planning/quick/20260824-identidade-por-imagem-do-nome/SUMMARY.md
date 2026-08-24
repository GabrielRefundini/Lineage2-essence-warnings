---
quick_id: 260824-jv0
slug: identidade-por-imagem-do-nome
date: 2026-08-24
status: complete
---

# Identidade do membro pela imagem do nome — concluído

## O que mudou

O nome no alerta agora vem de **reconhecer a imagem do nome na tela**, não da
posição da linha na lista do config. A calibração grava uma impressão digital
visual do nome de cada membro; em execução, cada linha é comparada contra todas
as assinaturas conhecidas.

## Por que não OCR

Os nomes são um conjunto fechado e o cliente renderiza o texto de forma
determinística — o mesmo nome dá os mesmos pixels toda vez. Então o problema é
*classificar entre N conhecidos*, não *ler texto livre*. Isso é mais preciso, e
evita o instalador de ~100 MB do Tesseract, que contradiz o "clica e roda".

## O que fez funcionar

Duas medições guiaram o desenho, comparando capturas separadas por 4 segundos
(o cenário muda por trás do texto, que é transparente):

| Abordagem | Mesmo nome | Nomes diferentes | Margem |
|---|---|---|---|
| Cinza bruto, recorte largo | 0.751 | 0.707 | 0.045 ✗ |
| Máscara de texto, recorte largo | 0.831 | 0.793 | 0.038 ✗ |
| **Máscara de texto, recorte justo** | **1.000** | **0.454** | **0.546** ✓ |

- **Recorte justo**: num recorte largo o terreno domina a correlação
- **Máscara de texto**: o texto é claro e dessaturado, o terreno é colorido

## Verificado

Contra um frame real da party, com as linhas remontadas em várias ordens:

| Cenário | Resultado |
|---|---|
| Ordem original | ✓ |
| Dois membros trocados | ✓ |
| Ordem invertida | ✓ |
| Primeiro sai, os outros sobem | ✓ |

O último é o caso que motivou tudo: a party window compacta as linhas, e sem
isso o alerta sairia com o nome do membro errado.

## Decisões de projeto

- **Não reconheceu, não chuta.** Abaixo do limiar, ou com dois candidatos
  empatados, devolve `None` e o rastreador cai para "Membro N". Feio, mas
  honesto — um alerta com o nome errado manda a party socorrer a pessoa errada.
- **Degrada em vez de quebrar.** Calibração antiga sem assinaturas continua
  funcionando: o nome volta a vir da ordem, como era antes.

## Também nesta tarefa

O calibrador ganhou um plano B: se a party window estiver coberta por outra
janela do jogo, ele lê a janela por dentro em vez de desistir. Descoberto na
prática — a calibração falhou duas vezes porque o inventário estava aberto.

## Arquivos

- `l2scanner/identidade.py` — máscara de texto, assinatura, casamento
- `l2scanner/calibracao.py` — região do nome e assinaturas persistidas
- `l2scanner/calibrar.py` — grava assinaturas; plano B por janela
- `l2scanner/visao.py` — identifica cada linha
- `l2scanner/rastreador.py` — o nome reconhecido vence a posição
- `tests/test_identidade.py` — 18 testes, incluindo os de reordenação
