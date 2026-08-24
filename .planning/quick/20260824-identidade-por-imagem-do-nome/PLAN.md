---
quick_id: 260824-jv0
slug: identidade-por-imagem-do-nome
date: 2026-08-24
status: in-progress
---

# Identidade do membro pela imagem do nome

## Problema

Os nomes vêm da lista do `config` **por posição de linha**. Se a ordem da party
mudar — alguém sai e as linhas compactam, ou o líder reorganiza — os alertas
saem com o nome errado.

Isso é a pior categoria de falha do produto: não é ruído, é uma mentira
plausível. "Korzis morreu" quando quem morreu foi o Kaus manda a party socorrer
a pessoa errada, e ninguém desconfia.

## Abordagem: comparação de imagem, não OCR

Os nomes são um **conjunto fechado e conhecido**, e o cliente renderiza o texto
de forma determinística. Então não precisamos *ler* o nome — precisamos
*reconhecer* qual dos N conhecidos está ali.

A calibração grava uma assinatura visual do nome de cada membro. Em execução,
o recorte de cada linha é comparado contra todas as assinaturas, e o melhor
casamento acima de um limiar define quem é.

### Por que não OCR

- Tesseract exige instalador de ~100 MB, contra o "clica e roda" do projeto
- Um glifo lido errado inventa um membro fantasma entrando e saindo da party
- Comparação de imagem contra conjunto fechado é mais precisa aqui: o texto na
  tela é *pixel a pixel o mesmo* toda vez

### Medições que sustentam a decisão

Feitas na tela real, comparando capturas separadas por 4 segundos (cenário
mudando por trás do texto, que é transparente):

| Isolamento | Mesmo nome | Nomes diferentes | Margem |
|---|---|---|---|
| Cinza bruto, recorte largo | 0.751 | 0.707 | 0.045 ✗ |
| Máscara de texto, recorte largo | 0.831 | 0.793 | 0.038 ✗ |
| **Máscara de texto, recorte justo** | **1.000** | **0.454** | **0.546** ✓ |

O que fez a diferença: **recortar justo** (o terreno dominava a correlação num
recorte largo) e **isolar o texto por claro + dessaturado** (o texto é branco,
o terreno é colorido).

## Tarefas

1. `l2scanner/identidade.py` — máscara de texto, assinatura e casamento
2. Calibração grava as assinaturas dos nomes junto com as coordenadas
3. `visao.py` devolve, por linha, qual assinatura casou
4. `rastreador.py` passa a chavear por identidade, não por índice de linha
5. Testes: ordem trocada, membro ausente, nome desconhecido, empate

## Definição de pronto

- Trocar dois membros de posição na party não faz o alerta sair com nome errado
- Um nome não reconhecido degrada para "Membro N" em vez de chutar
- A lógica continua testável sem jogo e sem rede
