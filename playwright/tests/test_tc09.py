# -*- coding: utf-8 -*-
# TC-09: Anúncio faltante
# O Livro 21 consta na Lista do Livreiro e nunca foi cadastrado na EV.
# Procuramos o título na vitrine:
#   0 anúncios   = faltante CONFIRMADO (caso Reprovado, conforme o plano 2.1)
#   1+ anúncios  = o livro existe na EV (premissa cai, caso Aprovado)

import json
import os
from playwright.sync_api import sync_playwright

CAMINHO_JSON = "playwright/data/livros.json"
PASTA_EVIDENCIA = "evidencias/2026-10-17"

# Locator dos cards (herdado do test_tc18_fotos.py)
CARDS = ".product-list__items .product-item"

with open(CAMINHO_JSON, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

url_vitrine = dados["vitrine_ev"]
livro = dados["livros"][6]  # L-21, objeto do TC-09

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

    # PASSO 3: rolagem completa antes de ler (carregamento preguiçoso, lição do TC-08)
    altura_total = pagina.evaluate("document.body.scrollHeight")
    posicao = 0
    while posicao < altura_total:
        posicao += 600
        pagina.evaluate(f"window.scrollTo(0, {posicao})")
        pagina.wait_for_timeout(400)
        altura_total = pagina.evaluate("document.body.scrollHeight")
    pagina.evaluate("window.scrollTo(0, 0)")
    pagina.wait_for_timeout(1000)

    # VALIDAÇÃO: o anúncio do Livro 21 existe na vitrine?
    termo = livro["titulo"][:20]
    anuncios = pagina.locator(CARDS).filter(has_text=termo)
    total_anuncios = anuncios.count()
    print(f"Anúncios na vitrine para '{termo}': {total_anuncios}")

    # Verificação cruzada: o título aparece em algum texto da página?
    texto_pagina = pagina.locator("body").inner_text()
    titulo_na_pagina = livro["titulo"][:20].lower() in texto_pagina.lower()
    print(f"Verificação cruzada: título presente no texto da página: {titulo_na_pagina}")

    if total_anuncios == 0 and not titulo_na_pagina:
        print("TC-09: ANÚNCIO FALTANTE CONFIRMADO: Livro 21 consta na Lista do Livreiro e não existe na EV")
    elif total_anuncios == 0 and titulo_na_pagina:
        print("ATENÇÃO: contagem por cards deu 0 mas o título aparece na página (conferir evidência)")
    else:
        texto_card = anuncios.first.inner_text()
        print("Texto do card:", texto_card.replace("\n", " | ")[:200])
        print("TC-09: o Livro 21 EXISTE na vitrine: a premissa do faltante cai (caso Aprovado)")

    print("Livro testado:", livro["titulo"])

    # EVIDÊNCIA: a página de resultados (vazia ou não) é a prova do caso
    os.makedirs(PASTA_EVIDENCIA, exist_ok=True)
    pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-09_livro21_anuncio_faltante.png", full_page=True)
    print("Evidência salva em:", PASTA_EVIDENCIA)

    navegador.close()