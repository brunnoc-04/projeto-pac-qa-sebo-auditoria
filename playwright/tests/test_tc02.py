# -*- coding: utf-8 -*-
# TC-02: Consistência de título
# O título exibido no anúncio deve ser idêntico ao registrado na Lista do Livreiro

import json
import os
from playwright.sync_api import sync_playwright

CAMINHO_JSON = "playwright/data/livros.json"
PASTA_EVIDENCIA = "evidencias/2026-10-17"

with open(CAMINHO_JSON, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

url_vitrine = dados["vitrine_ev"]
livro = dados["livros"][1]  # L-05, objeto do TC-02

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
    anuncio = pagina.get_by_role("link", name="Hábitos Atômicos").first
    anuncio.click()

    # POPUP DE ANIVERSÁRIO: pode ou não aparecer
    try:
        pagina.locator("g > path").click(timeout=3000)
        print("Pop-up de aniversário fechado")
    except Exception:
        print("Pop-up não apareceu desta vez, seguindo sem fechar")

    # VALIDAÇÃO: o título na página precisa ser IDÊNTICO ao da lista
    try:
        titulo_exato = pagina.get_by_role("heading", name=livro["titulo"], exact=True).first
        titulo_exato.wait_for(state="visible", timeout=5000)
        print("TC-02: título exibido é IDÊNTICO ao da lista")
    except Exception:
        print("TC-02: ATENÇÃO, título exibido NÃO é idêntico ao registrado (conferir evidência)")

    print("Título da lista:", livro["titulo"])

    # EVIDÊNCIA
    os.makedirs(PASTA_EVIDENCIA, exist_ok=True)
    pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-02_livro05_titulo_consistente.png", full_page=True)
    print("Evidência salva em:", PASTA_EVIDENCIA)

    navegador.close()