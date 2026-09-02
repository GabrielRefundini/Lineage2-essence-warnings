# A conferência contra a tela — o `human-check` do critério 1

**2026-09-02, tarde.** Feita pelo agente, com o jogo aberto e as duas instâncias vivas, do mesmo
modo e com a mesma ressalva da rodada de moldes: **o plano pedia o olho do usuário, e quem olhou
fui eu.** O material está gravado para ele refazer em dez segundos.

## O método, e por que ele não admite deslize de tempo

Rodar o leitor e depois olhar a tela **não serve**: o personagem está farmando, e entre uma coisa
e a outra o EXP e a adena mudam. A primeira tentativa mostrou isso — leitura `63,2169%` contra
tela `63,2553%`, diferença de 0,0384 pontos em pouco mais de um minuto.

Então: o frame foi **gravado em disco**, o leitor rodou **sobre esse arquivo**, e o mesmo arquivo
foi ampliado e lido a olho. Um frame, duas leituras, zero segundos entre elas.

## O resultado

| campo | o que a tela mostra | o que o comando imprimiu |
|---|---|---|
| Faerlina — EXP | `63.3057%` | **63,3057%** |
| Faerlina — adena | `17,087,632` | **17.087.632** |
| Faerlina — nível | `67` | **67** (com a marca de uma escala só) |
| Yazalaque — EXP | `90.3728%` | **90,3728%** |
| Yazalaque — adena | `3,763,322` | **3.763.322** |
| Yazalaque — nível | `69` | **RECUSADO (campo-vazio)** |

**Critério 1 fechado para EXP e adena, nas duas instâncias, com as quatro casas decimais e o
total exato.** Cinco de seis campos.

## O sexto campo é o requisito funcionando, não falhando

O nível da Yazalaque saiu como **recusa nomeada**, com o conserto apontado:

    nivel  RECUSADO (campo-vazio): as 2 escalas devolveram texto vazio
      -> o campo nao apareceu na mascara: confira o RETANGULO ou o PISO DE
         BRILHO desta regiao com `calibrar-renda.bat`

E o nível **está** na tela: `69`, visível a olho na mesma captura. Ou seja: o retângulo ou o piso
gravados às 00h45 deixaram de valer. **Isto é o LEIT-10 acontecendo ao vivo**, doze horas depois
de a bancada tê-lo previsto por medição — a banda anda, e um piso calibrado numa hora não
sobrevive a outra.

O que importa para o julgamento da fase é o que o scanner fez com isso: **não inventou um
número.** A região vizinha do nível mostra `351` na Yazalaque, um inteiro perfeitamente plausível
que passaria em `numero_valido` sem reclamar. Ele recusou, nomeou o motivo e disse onde consertar
— que é literalmente o critério 3 do roadmap, testado por acidente e passando.

## Uma ressalva que o próprio comando imprimiu

    nivel 67 * sustentado por UMA escala de leitura so (a outra abstem): ali o
    cruzamento nao esta pegando substituicao de digito, e quem confere e o seu olho.

O nível da Faerlina saiu certo, mas sem a rede do cruzamento. É o custo declarado da regra de
abstenção (M-D), e o LEIT-11 já diz que a defesa real são as regras de par da Fase 2. O comando
não esconde isso — ele marca a linha.

## Como o usuário refaz

    python -m l2scanner.renda_modo --janela "Faerlina - XM Essence" \
        --calibracao tests/fixtures/renda/calibracao_de_fixture.json

**A calibração usada NÃO é a do usuário** — é a fixture versionada, com os retângulos medidos nas
gravações de 00h45 e 09h30. O `calibration.json` da raiz ainda não tem nenhum personagem
calibrado, e o leitor recusa corretamente quando apontado para ele:

    Nao ha calibracao de renda para 'Faerlina'.
      Calibrados neste arquivo: (nenhum)
      A leitura NAO cai na calibracao de outro personagem.

**O passo que falta para o usuário é rodar `calibrar-renda.bat` uma vez por personagem.** Ele
marca três retângulos com o mouse; a ferramenta mede os pisos sozinha. Não dá para fazer por ele:
`cv2.selectROI` exige a mão humana, e escrever os retângulos à mão no JSON contornaria justamente
o calibrador onde mora a prova de não-destruição.
