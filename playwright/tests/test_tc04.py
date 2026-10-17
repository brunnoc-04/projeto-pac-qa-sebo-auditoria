# -*- coding: utf-8 -*-
# TC-04: Avaria falsa na descrição
# O anúncio do Livro 10 declara "rasgado", mas a Lista do Livreiro registra o livro em bom estado
# FLUXO: 1) validar fotos (régua: mínimo 2) 2) expandir a descrição 3) procurar "rasgado"

import json
import os
import re
from playwright.sync_api import sync_playwright

CAMINHO_JSON = "playwright/data/livros.json"
PASTA_EVIDENCIA = "evidencias/2026-10-17"

# Locators calibrados
# Galeria (herdados do test_tc18_fotos.py)
FOTOS_REAIS = ".pictures__carousel .swiper-slide:not(.swiper-slide-duplicate)"
SLIDE_COM_ROTULO = ".pictures__carousel .swiper-slide[aria-label*=' / ']"
SETA_PROXIMA = ".swiper-button-next"
# Veja mais da descrição (calibrado no DevTools em 17/10/2026)
VEJA_MAIS = ".book-copy__info .see-more"

with open(CAMINHO_JSON, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

url_vitrine = dados["vitrine_ev"]
livro = dados["livros"][5]  # L-10, objeto do TC-04

with sync_playwright() as p:

    navegador = p.chromium.launch(headless=False)
    pagina = navegador.new_page()

    # PASSO 1: acessar a vitrine
    pagina.goto(url_vitrine)

    # PASSO 2: buscar pelo título
    campo_busca = pagina.get_by_role("textbox", name="O que você está procurando?")
    campo_busca.fill(livro["titulo"])
    pagina.get_by_role("button", name="buscar produtos na loja").click()

    # PASSO 3: abrir o anúncio do livro
    anuncio = pagina.get_by_role("link", name="A Cabeça do Golem").first
    anuncio.click()

    # POPUP DE ANIVERSÁRIO: pode demorar, esperamos até 8s
    try:
        pagina.locator("g > path").click(timeout=8000)
        print("Pop-up de aniversário fechado")
    except Exception:
        print("Pop-up não apareceu, seguindo")

    # VALIDAÇÃO 1: fotos (rótulo do carrossel + slides reais, verificação cruzada)
    total_fotos = 0
    try:
        rotulo = pagina.locator(SLIDE_COM_ROTULO).first.get_attribute("aria-label", timeout=5000)
        total_fotos = int(re.search(r"\d+\s*/\s*(\d+)", rotulo).group(1))
        print(f"Fonte 1 (rótulo do carrossel): {total_fotos} fotos")
    except Exception:
        print("Fonte 1: rótulo do carrossel não localizado")

    n_slides = pagina.locator(FOTOS_REAIS).count()
    print(f"Fonte 2 (slides reais): {n_slides} fotos")

    if total_fotos == n_slides and total_fotos > 0:
        qtd_fotos = total_fotos
    elif total_fotos == 0 and n_slides == 0:
        qtd_fotos = pagina.locator(".pictures__carousel img").count()
        print(f"Fonte 3 (imagens da galeria): {qtd_fotos} fotos")
    else:
        qtd_fotos = max(total_fotos, n_slides)
        print("ATENÇÃO: fontes divergem, adotando a maior contagem")

    # Prova visual: avança o carrossel uma vez
    if qtd_fotos > 1:
        try:
            pagina.locator(SETA_PROXIMA).click(timeout=3000)
            pagina.wait_for_timeout(800)
            print("Setinha clicada: carrossel avançou para a próxima foto")
        except Exception:
            print("Setinha não respondeu ao clique")

    if qtd_fotos >= 2:
        print(f"VALIDAÇÃO 1 OK: {qtd_fotos} fotos na galeria (régua de 2 atendida)")
    else:
        print(f"VALIDAÇÃO 1 ATENÇÃO: {qtd_fotos} foto(s) na galeria, régua de 2 violada")

    # VALIDAÇÃO 2: expandir a descrição com o locator calibrado no DevTools
    # O span fica dentro do parágrafo da descrição, então o escopo evita
    # clicar em qualquer outro "Veja mais" que exista na página
    try:
        pagina.locator(VEJA_MAIS).first.click(timeout=5000)
        print("VALIDAÇÃO 2: descrição expandida com o Veja mais (locator calibrado)")
        pagina.wait_for_timeout(1000)
    except Exception:
        print("VALIDAÇÃO 2: Veja mais não localizado pelo locator calibrado")

    # DIAGNÓSTICO: o que o script realmente enxerga na descrição
    try:
        descricao = pagina.get_by_text("Livro em bom estado").first
        print("Descrição lida pelo script:", descricao.inner_text()[:200])
    except Exception:
        print("Descrição não localizada pelo texto inicial 'Livro em bom estado'")

    # Evidência intermediária da descrição expandida
    pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-04_livro10_descricao_expandida.png", full_page=True)

    # VALIDAÇÃO 3: procurar o radical "rasgad" (cobre rasgado, rasgada, rasgadas)
    # ACHAR = avaria falsa confirmada (bug do anúncio, não erro do script)
    try:
        palavra = pagina.get_by_text("rasgad").first
        palavra.wait_for(state="visible", timeout=5000)
        print("TC-04: AVARIA FALSA CONFIRMADA: anúncio declara avaria de rasgado num livro em bom estado")
        print("Trecho encontrado:", palavra.inner_text()[:100])
    except Exception:
        print("TC-04: radical 'rasgad' não encontrado na página expandida")

    print("Livro testado:", livro["titulo"])

    # EVIDÊNCIA
    os.makedirs(PASTA_EVIDENCIA, exist_ok=True)
    pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-04_livro10_avaria_falsa.png", full_page=True)
    print("Evidência salva em:", PASTA_EVIDENCIA)

    navegador.close()