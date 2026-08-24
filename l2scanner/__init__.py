"""L2 Party Scanner — vigia a party window e avisa no WhatsApp.

INVARIANTE DE SEGURANCA (nao negociavel, reverificado a cada fase):

Este programa SOMENTE LE A TELA. Ele nunca envia input ao jogo, nunca le a
memoria do processo, nunca injeta codigo, nunca faz hook de renderizacao e
nunca intercepta trafego de rede.

A garantia e estrutural, nao apenas politica: nenhuma biblioteca de sintese de
input (pyautogui, pydirectinput, keyboard, pynput...) entra na lista de
dependencias. Nao ha como violar o invariante sem primeiro adicionar uma
dependencia nova — o que e visivel em qualquer revisao.
"""

__version__ = "0.1.0"
