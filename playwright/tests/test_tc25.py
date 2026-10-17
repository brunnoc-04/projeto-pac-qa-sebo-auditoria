# -*- coding: utf-8 -*-
# TC-25: Anúncio fantasma
# "O Aprendiz da Torre das Sete Chaves" está publicado na vitrine da EV (R$ 19,00)
# e NÃO consta na Lista do Livreiro (campo na_lista: false no JSON).
# Partição de equivalência: "está na vitrine e não consta na lista".
# Passos do caso: 1) localizar o anúncio na vitrine 2) consultar a Lista
#                 3) verificar se o título consta
# ACHAR o anúncio + não constar na lista = FANTASMA CONFIRMADO (caso Reprovado)

import json
import os
import re
from playwright.sync_api import sync_playwright

CAMINHO_JSON = "playwright/data/livros.json"
PASTA_EVIDENCIA = "evidencias/2026-10-17"

# Locator dos cards (herdado do test_tc18_fotos.py)
CARDS = ".product-list__items .product-item"

ID_ALVO = "L-22"

with open(CAMINHO_JSON, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

url_vitrine = dados["vitrine_ev"]

# Achar o livro pelo id (lição do TC-24: id não depende da ordem do array)
livro = None
for item in dados["livros"]:
    if item["id"] == ID_ALVO:
        livro = item
if livro is None:
    print(f"ATENÇÃO: o id {ID_ALVO} não existe no livros.json (ajustar a massa)")
    raise SystemExit

# O termo ignora os 2 primeiros caracteres do título ("O " ou "0 "):
# lição do zero/O — o caso não pode depender do artigo estar correto na massa.
# 20 caracteres úteis, mesma régua dos demais testes.
termo = livro["titulo"][2:22]
print(f"Buscando por: '{termo}' (título completo na massa: {livro['titulo']})")

with sync_playwright() as p:

    navegador = p.chromium.launch(headless=False)
    pagina = navegador.new_page()

    # PASSO 1: acessar a vitrine
    pagina.goto(url_vitrine)

    # POPUP DE ANIVERSÁRIO: pode demorar, esperamos até 8s
    try:
        pagina.locator("g > path").click(timeout=8000)
        print("Pop-up de aniversário fechado")
    except Exception:
        print("Pop-up não apareceu, seguindo")

    # PASSO 2: localizar o anúncio na vitrine
    campo_busca = pagina.get_by_role("textbox", name="O que você está procurando?")
    campo_busca.fill(termo)
    pagina.get_by_role("button", name="buscar produtos na loja").click()

    anuncios = pagina.locator(CARDS).filter(has_text=termo)
    total_anuncios = anuncios.count()
    print(f"Anúncios na vitrine contendo '{termo}': {total_anuncios}")

    if total_anuncios > 0:
        texto_card = anuncios.first.inner_text()
        print("Texto do card:", texto_card.replace("\n", " | ")[:200])

        preco_card = re.search(r"R\$\s*[\d.,]+", texto_card)
        if preco_card:
            print("Preço publicado no card:", preco_card.group(0))

        # PASSO 3: verificar na Lista do Livreiro (fonte da verdade, digitalizada no JSON)
        if livro.get("na_lista") is False:
            print("TC-25: ANÚNCIO FANTASMA CONFIRMADO: está na vitrine e NÃO consta na Lista do Livreiro")
        elif livro.get("na_lista") is True:
            print("ATENÇÃO: anúncio na vitrine e o JSON marca na_lista=true — massa divergente da Lista, conferir")
        else:
            print("ATENÇÃO: o campo na_lista não existe no item do JSON")
    else:
        print("TC-25: nenhum anúncio na vitrine: sem fantasma, consistente com a lista (caso Aprovado)")

    print("Livro testado:", livro["titulo"])

    # EVIDÊNCIA
    os.makedirs(PASTA_EVIDENCIA, exist_ok=True)
    pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-25_livro22_anuncio_fantasma.png", full_page=True)
    print("Evidência salva em:", PASTA_EVIDENCIA)

    navegador.close()