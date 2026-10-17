# -*- coding: utf-8 -*-
# TC-06: Estoque por título
# A Lista do Livreiro registra 3 cópias físicas do Livro 8, mas a vitrine
# mostra 1 anúncio. O teste confirma a divergência (cópias sem anúncio)

import json
import os
from playwright.sync_api import sync_playwright

CAMINHO_JSON = "playwright/data/livros.json"
PASTA_EVIDENCIA = "evidencias/2026-10-17"

# Locator dos cards de resultado (herdado do test_tc18_fotos.py)
CARDS = ".product-list__items .product-item"

COPIAS_NA_LISTA = 3  # Livro 8: 3 físicos registrados na Lista do Livreiro

with open(CAMINHO_JSON, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

url_vitrine = dados["vitrine_ev"]
livro = dados["livros"][3]  # L-08, objeto do TC-06

with sync_playwright() as p:

    navegador = p.chromium.launch(headless=False)
    pagina = navegador.new_page()

    # PASSO 1: acessar a vitrine
    pagina.goto(url_vitrine)

    # PASSO 2: buscar pelo título (a busca da loja só retorna anúncios do nosso sebo)
    campo_busca = pagina.get_by_role("textbox", name="O que você está procurando?")
    campo_busca.fill(livro["titulo"])
    pagina.get_by_role("button", name="buscar produtos na loja").click()

    # POPUP DE ANIVERSÁRIO: pode demorar, esperamos até 8s
    try:
        pagina.locator("g > path").click(timeout=8000)
        print("Pop-up de aniversário fechado")
    except Exception:
        print("Pop-up não apareceu, seguindo")

    # VALIDAÇÃO: contar os anúncios do título na página de resultados
    # Usamos o início do título porque o card pode truncar o final com reticência
    termo = livro["titulo"][:25]
    anuncios = pagina.locator(CARDS).filter(has_text=termo)
    total_anuncios = anuncios.count()
    print(f"Anúncios na vitrine contendo '{termo}': {total_anuncios}")

    if total_anuncios == 0:
        # fallback: o componente de cards pode ser diferente na página de busca
        try:
            resultado = pagina.get_by_text(termo).first
            resultado.wait_for(state="visible", timeout=5000)
            print("Título presente nos resultados (contagem por cards falhou, conferir evidência)")
        except Exception:
            print("Nenhum resultado visível para o título buscado")

    # COMPARAÇÃO com a Lista do Livreiro (a regra de negócio do caso)
    if total_anuncios < COPIAS_NA_LISTA:
        diferenca = COPIAS_NA_LISTA - total_anuncios
        print(f"TC-06: DIVERGÊNCIA CONFIRMADA: {COPIAS_NA_LISTA} cópias na lista x {total_anuncios} na vitrine")
        print(f"Cópias sem anúncio: {diferenca}")
    elif total_anuncios == COPIAS_NA_LISTA:
        print("TC-06: sem divergência: quantidade da vitrine bate com a lista")
    else:
        print("TC-06: ATENÇÃO: mais anúncios na vitrine do que cópias na lista (verificar)")

    print("Livro testado:", livro["titulo"])

    # EVIDÊNCIA
    os.makedirs(PASTA_EVIDENCIA, exist_ok=True)
    pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-06_livro08_estoque_divergente.png", full_page=True)
    print("Evidência salva em:", PASTA_EVIDENCIA)

    navegador.close()