# -*- coding: utf-8 -*-
# TC-01: Conferência de existência do livro
# Locators calibrados com o codegen em 17/10/2026

import json
import os
from playwright.sync_api import sync_playwright

CAMINHO_JSON = "playwright/data/livros.json"
PASTA_EVIDENCIA = "evidencias/2026-10-17"

with open(CAMINHO_JSON, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

url_vitrine = dados["vitrine_ev"]
livro = dados["livros"][0]  # L-01, objeto do TC-01

with sync_playwright() as p:

    navegador = p.chromium.launch(headless=False)
    pagina = navegador.new_page()

    # PASSO 1: acessar a vitrine
    pagina.goto(url_vitrine)

    # PASSO 2: buscar pelo título (campo e botão calibrados com o codegen)
    campo_busca = pagina.get_by_role("textbox", name="O que você está procurando?")
    campo_busca.fill(livro["titulo"])
    pagina.get_by_role("button", name="buscar produtos na loja").click()

    # PASSO 3: abrir o anúncio do livro (nome parcial, igual ao gravado no codegen)
    anuncio = pagina.get_by_role("link", name="A Psicologia da Alquimia").first
    anuncio.click()

    # POPUP DE ANIVERSÁRIO: pode ou não aparecer. Tenta fechar por 3 segundos;
    # se não aparecer, o teste continua normalmente.
    try:
        pagina.locator("g > path").click(timeout=3000)
        print("Pop-up de aniversário fechado")
    except Exception:
        print("Pop-up não apareceu desta vez, seguindo sem fechar")

    # VALIDAÇÃO: o título precisa estar visível na página do anúncio
    titulo_na_pagina = pagina.get_by_text("A Psicologia da Alquimia").first
    titulo_na_pagina.wait_for(state="visible")

    print("TC-01: anúncio localizado e aberto com sucesso")
    print("Título conferido:", livro["titulo"])

    # EVIDÊNCIA
    os.makedirs(PASTA_EVIDENCIA, exist_ok=True)
    pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-01_livro01_anuncio_localizado.png", full_page=True)
    print("Evidência salva em:", PASTA_EVIDENCIA)

    navegador.close()