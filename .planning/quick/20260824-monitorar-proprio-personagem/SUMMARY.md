---
quick_id: 260824-yaz
slug: monitorar-proprio-personagem
date: 2026-08-24
status: complete
---

# Monitorar o próprio personagem — concluído

## O que mudou

O scanner agora vigia também a barra de HP do próprio usuário, que fica no topo
da janela do jogo — fora da party window, onde ele nunca aparece.

Isso era o requisito DTCT-06. Eu o havia marcado como entregue quando não
estava: o campo existia na calibração, mas nunca era preenchido e nada o lia.

## Medições reais

Janela do Yazalaque, coordenadas relativas ao canto dela:

| Elemento | Posição | Tamanho |
|---|---|---|
| Barra de HP própria | (87, 60) | 191x24 |
| Party window | (18, 325) | 174x522 |

O texto `HP 3597/3597` fica desenhado sobre a barra e poderia quebrar a medição
por corrida de colunas. Não quebra: a barra tem 24 px de altura e as letras não
ocupam metade de nenhuma coluna. Verificado — leitura de 100% com HP cheio.

## Como foi feito

A barra própria é capturada como uma **região extra**, separada da party
window. Pelo caminho `--janela` isso é de graça (o frame completo já está em
mãos); pelo desktop exigiria uma segunda captura, e por isso o modo desktop
avisa que a barra própria não será lida.

No rastreador, o próprio personagem entra como **mais um membro**, com chave
`@Nome`. Assim morte e ressurreição dele passam pelo mesmo debounce e pela
mesma histerese dos outros, sem código duplicado.

## Três bugs encontrados no caminho

**1. Barra errada.** Eu escolhia a candidata mais larga, e quando há um alvo
selecionado a barra dele é mais larga que a do jogador. Trocado para a mais à
esquerda e mais acima — a barra do personagem é ancorada no canto da UI, a do
alvo flutua no centro.

**2. Busca no monitor errado.** Eu procurava nos 260 pixels do topo da imagem,
que num arranjo de três monitores é outro monitor. Agora a busca é ancorada no
topo da janela do jogo.

**3. Party atribuída ao cliente errado.** O calibrador decidia a janela pelo
CANTO da party window. Com duas instâncias lado a lado, a detecção marcou o
canto 12 px à esquerda da borda e o ponto caiu dentro da janela vizinha — a
calibração inteira saiu no cliente errado. Agora decide pelo CENTRO.

## Dois falsos positivos corrigidos junto

Descobertos rodando ao vivo, ambos causados por **piscar de reconhecimento**:

- Um frame sem reconhecer o Korzis fazia a identidade dele virar `#linha0`, o
  "Korzis" sumir do conjunto de presentes, e o scanner anunciar **"Korzis saiu
  da party"** com ele na tela.
- O espelho disso: a chave `#linha0` depois "entrava" e "saía", inventando um
  membro fantasma.

Corrigido com duas regras: se alguma linha ocupada não foi reconhecida, nenhuma
saída é confirmada naquele frame (o membro "sumido" pode ser justamente quem
está nela); e chaves de posição nunca geram evento quando há identidade em jogo.

## Fora de escopo

**"Sair da própria party"** não é detectável pela barra do personagem — ela
continua igual. O sinal seria a party window inteira sumir, mas isso é
indistinguível de alt-tab e de tela de loading. Limite conhecido, não
implementado.

## Arquivos

- `l2scanner/frames.py` — `Frame.extras`, captura de regiões adicionais
- `l2scanner/captura_janela.py` — recorte dos extras do frame da janela
- `l2scanner/calibracao.py` — `hp_proprio` e `nome_proprio` persistidos
- `l2scanner/calibrar.py` — detecção da barra própria; atribuição pelo centro
- `l2scanner/visao.py` — leitura da barra própria
- `l2scanner/rastreador.py` — próprio como membro; guardas contra piscada
- `l2scanner/__main__.py` — captura, rastreio e exibição

168 testes.
