# -*- coding: utf-8 -*-
# TC-07: Livro esgotado
# O Livro 9 está esgotado conforme a Lista do Livreiro. O teste verifica
# como a vitrine/anúncio da EV apresenta esse livro (esgotado ou disponível)

import json
import os
from playwright.sync_api import sync_playwright

CAMINHO_JSON = "playwright/data/livros.json"
PASTA_EVIDENCIA = "evidencias/2026-10-17"

# Locators calibrados
CARDS = ".product-list__items .product-item"
LINK = ".product-item__link"

with open(CAMINHO_JSON, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

url_vitrine = dados["vitrine_ev"]
livro = dados["livros"][4]  # L-09, objeto do TC-07

with sync_playwright() as p:

    navegador = p.chromium.launch(headless=False)
    pagina = navegador.new_page()

    # PASSO 1: acessar a vitrine
    pagina.goto(url_vitrine)

    # PASSO 2: buscar pelo título
    campo_busca = pagina.get_by_role("textbox", name="O que você está procurando?")
    campo_busca.fill(livro["titulo"])
    pagina.get_by_role("button", name="buscar produtos na loja").click()

    # POPUP DE ANIVERSÁRIO: pode demorar, esperamos até 8s
    try:
        pagina.locator("g > path").click(timeout=8000)
        print("Pop-up de aniversário fechado")
    except Exception:
        print("Pop-up não apareceu, seguindo")

    # VALIDAÇÃO 1: o esgotado ainda aparece na vitrine?
    termo = livro["titulo"][:20]
    anuncios = pagina.locator(CARDS).filter(has_text=termo)
    total_anuncios = anuncios.count()
    print(f"Anúncios na vitrine para '{termo}': {total_anuncios}")

    if total_anuncios == 0:
        print("TC-07: livro esgotado NÃO aparece na vitrine (consistente com a lista)")
    else:
        # VALIDAÇÃO 2: o card marca o livro como esgotado?
        texto_card = anuncios.first.inner_text()
        print("Texto do card:", texto_card.replace("\n", " | ")[:200])
        texto_lower = texto_card.lower()
        if "esgotad" in texto_lower or "indispon" in texto_lower:
            print("TC-07: card marca o livro como ESGOTADO (consistente com a lista)")
        else:
            print("TC-07: card SEM marcação de esgotado, abrindo o anúncio para conferir")

            # VALIDAÇÃO 3: como a página do anúncio apresenta o estoque?
            anuncios.first.locator(LINK).first.click(timeout=5000)

            # POPUP DE ANIVERSÁRIO: pode aparecer de novo na página do produto
            try:
                pagina.locator("g > path").click(timeout=8000)
                print("Pop-up de aniversário fechado")
            except Exception:
                print("Pop-up não apareceu na página do produto, seguindo")

            texto_pagina = pagina.locator("body").inner_text()
            texto_lower = texto_pagina.lower()
            tem_esgotado = ("esgotad" in texto_lower) or ("indispon" in texto_lower)
            tem_disponivel = ("disponível" in texto_lower) or ("disponivel" in texto_lower)
            if tem_esgotado:
                print("TC-07: anúncio marca o livro como ESGOTADO (consistente com a lista)")
            elif tem_disponivel:
                print("TC-07: ATENÇÃO: anúncio apresenta o livro como DISPONÍVEL apesar de esgotado na lista")
            else:
                print("TC-07: nenhum marcador de esgotado/disponível localizado (conferir evidência)")

    print("Livro testado:", livro["titulo"])

    # EVIDÊNCIA
    os.makedirs(PASTA_EVIDENCIA, exist_ok=True)
    pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-07_livro09_esgotado.png", full_page=True)
    print("Evidência salva em:", PASTA_EVIDENCIA)

    navegador.close()