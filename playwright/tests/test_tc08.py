# -*- coding: utf-8 -*-
# TC-08: Quantidade total de exemplares
# Conta EXEMPLARES ativos na vitrine somando o marcador "N usado(s)" de cada card.
# RODADA 1: 16 de 19 cards vieram sem o marcador — a vitrine carrega o badge e o
# preço só quando o card entra na tela. Correção: rolar a página inteira ANTES de ler.

import json
import os
import re
from playwright.sync_api import sync_playwright

CAMINHO_JSON = "playwright/data/livros.json"
PASTA_EVIDENCIA = "evidencias/2026-10-17"

# Locator dos cards (herdado do test_tc18_fotos.py)
CARDS = ".product-list__items .product-item"

# Referência do plano de testes 2.1: unidades físicas dos Livros 1 a 20 na Lista
COPIAS_NA_LISTA = 22

with open(CAMINHO_JSON, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

url_vitrine = dados["vitrine_ev"]

with sync_playwright() as p:

    navegador = p.chromium.launch(headless=False)
    pagina = navegador.new_page()

    # PASSO 1: acessar a vitrine completa (sem busca: é o inventário global do sebo)
    pagina.goto(url_vitrine)

    # POPUP DE ANIVERSÁRIO: pode demorar, esperamos até 8s
    try:
        pagina.locator("g > path").click(timeout=8000)
        print("Pop-up de aniversário fechado")
    except Exception:
        print("Pop-up não apareceu, seguindo")

    # PASSO 2: esperar a grade de produtos carregar
    cards = pagina.locator(CARDS)
    try:
        cards.first.wait_for(state="visible", timeout=10000)
    except Exception:
        print("ATENÇÃO: nenhum card visível na vitrine (checar evidência)")

    # PASSO 3: rolagem progressiva até o fim da página
    # O badge "N usado" e o preço só são renderizados quando o card entra na tela.
    # A altura é relida a cada volta porque a página pode crescer ao carregar.
    print("Rolando a página para forçar o carregamento de todos os cards...")
    altura_total = pagina.evaluate("document.body.scrollHeight")
    posicao = 0
    while posicao < altura_total:
        posicao += 600
        pagina.evaluate(f"window.scrollTo(0, {posicao})")
        pagina.wait_for_timeout(400)
        altura_total = pagina.evaluate("document.body.scrollHeight")
    pagina.evaluate("window.scrollTo(0, 0)")
    pagina.wait_for_timeout(1000)

    # PASSO 4: inventário card por card — soma dos exemplares ("N usado(s)")
    total_cards = cards.count()
    total_exemplares = 0
    cards_sem_marcador = 0
    print("--- Inventário da vitrine, card por card ---")
    for i in range(total_cards):
        card = cards.nth(i)
        texto = card.inner_text()
        resumo = " | ".join(texto.split("\n"))[:120]
        quantidade = re.search(r"(\d+)\s*usad", texto, flags=re.IGNORECASE)
        if quantidade:
            qtd = int(quantidade.group(1))
            total_exemplares += qtd
            print(f"Card {i + 1}: {qtd} exemplar(es) ativo(s) | {resumo}")
        else:
            cards_sem_marcador += 1
            print(f"Card {i + 1}: SEM marcador de quantidade (conferir manualmente) | {resumo}")

    # Verificação cruzada: quantos badges "N usado" existem no texto da página inteira
    texto_pagina = pagina.locator("body").inner_text()
    badges = len(re.findall(r"\d+\s*usad", texto_pagina, flags=re.IGNORECASE))
    print(f"Verificação cruzada: badges 'N usado' no texto da página: {badges}")

    # PASSO 5: veredito global (os dois números, para o comparativo no Sheets)
    print("---")
    print(f"Títulos na vitrine (cards): {total_cards}")
    print(f"Exemplares ativos na EV (soma dos usados): {total_exemplares}")
    print(f"Cópias físicas na Lista do Livreiro (plano): {COPIAS_NA_LISTA}")

    if cards_sem_marcador > 0:
        print(f"ATENÇÃO: {cards_sem_marcador} card(s) ficaram sem marcador mesmo após a rolagem — "
              "podem ser cards genuinamente sem cópia ativa (checar na evidência)")
    elif total_exemplares < COPIAS_NA_LISTA:
        print(f"TC-08: DIVERGÊNCIA GLOBAL CONFIRMADA: {COPIAS_NA_LISTA} cópias na lista x {total_exemplares} ativas na EV (diferença: {COPIAS_NA_LISTA - total_exemplares})")
    elif total_exemplares == COPIAS_NA_LISTA:
        print("TC-08: contagem global consistente com a lista")
    else:
        print("TC-08: ATENÇÃO: mais exemplares ativos na EV do que cópias na lista (conferir na planilha)")

    # EVIDÊNCIA
    os.makedirs(PASTA_EVIDENCIA, exist_ok=True)
    pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-08_inventario_global.png", full_page=True)
    print("Evidência salva em:", PASTA_EVIDENCIA)

    navegador.close()