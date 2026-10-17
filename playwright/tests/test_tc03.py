# -*- coding: utf-8 -*-
# TC-03: Consistência de preço
# O preço exibido no anúncio do Livro 6 deve ser idêntico ao da Lista do Livreiro

import json
import os
from playwright.sync_api import sync_playwright

CAMINHO_JSON = "playwright/data/livros.json"
PASTA_EVIDENCIA = "evidencias/2026-10-17"

with open(CAMINHO_JSON, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

url_vitrine = dados["vitrine_ev"]
livro = dados["livros"][2]  # L-06, objeto do TC-03

# Formata o preço do JSON (19.0) para o texto como aparece na página (R$ 19,00)
preco_esperado = f"R$ {livro['preco']:.2f}".replace(".", ",")

with sync_playwright() as p:

    navegador = p.chromium.launch(headless=False)
    pagina = navegador.new_page()

    # PASSO 1: acessar a vitrine
    pagina.goto(url_vitrine)

    # PASSO 2: buscar pelo título (locators calibrados no TC-01)
    campo_busca = pagina.get_by_role("textbox", name="O que você está procurando?")
    campo_busca.fill(livro["titulo"])
    pagina.get_by_role("button", name="buscar produtos na loja").click()

    # PASSO 3: abrir o anúncio do livro
    anuncio = pagina.get_by_role("link", name="A Hipótese do Amor").first
    anuncio.click()

    # POPUP DE ANIVERSÁRIO: pode ou não aparecer
    try:
        pagina.locator("g > path").click(timeout=3000)
        print("Pop-up de aniversário fechado")
    except Exception:
        print("Pop-up não apareceu desta vez, seguindo sem fechar")

    # VALIDAÇÃO 1: o exemplar do nosso sebo precisa estar na página do produto
    try:
        vendedor = pagina.get_by_text("E O Bento Levou").first
        vendedor.wait_for(state="visible", timeout=5000)
        print("Vendedor do sebo presente na página do anúncio")
    except Exception:
        print("ATENÇÃO: card do vendedor E O Bento Levou não localizado")

    # VALIDAÇÃO 2: o preço esperado precisa aparecer na página
    try:
        preco_na_pagina = pagina.get_by_text(preco_esperado).first
        preco_na_pagina.wait_for(state="visible", timeout=5000)
        print("TC-03: preço", preco_esperado, "exibido na página")
    except Exception:
        print("TC-03: ATENÇÃO, preço", preco_esperado, "NÃO encontrado na página")

    print("Preço da lista:", preco_esperado)

    # EVIDÊNCIA
    os.makedirs(PASTA_EVIDENCIA, exist_ok=True)
    pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-03_livro06_preco_consistente.png", full_page=True)
    print("Evidência salva em:", PASTA_EVIDENCIA)

    navegador.close()