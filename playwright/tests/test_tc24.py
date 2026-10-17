# -*- coding: utf-8 -*-
# TC-24: Piso de R$ 12,00 da plataforma
# Livros 4 e 14 constam na Lista do Livreiro com preços abaixo do piso (R$ 7,00 e R$ 7,42).
# LIMIAR INCLUSIVO: exatamente R$ 12,00 é exibido; abaixo disso, o anúncio fica invisível.
# Passos do caso: 1) buscar cada título na vitrine 2) verificar exibição 3) registrar o resultado
# ACHADO EV-01 (plataforma): a EV não exibe anúncios abaixo de R$ 12,00

import json
import os
from playwright.sync_api import sync_playwright

CAMINHO_JSON = "playwright/data/livros.json"
PASTA_EVIDENCIA = "evidencias/2026-10-17"

# Locator dos cards (herdado do test_tc18_fotos.py)
CARDS = ".product-list__items .product-item"

# Os dois objetos do caso, identificados por id
IDS_DO_CASO = ["L-04", "L-14"]
PISO_PLATAFORMA = 12.00

with open(CAMINHO_JSON, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

url_vitrine = dados["vitrine_ev"]

with sync_playwright() as p:

    navegador = p.chromium.launch(headless=False)
    pagina = navegador.new_page()

    # O caso tem DOIS livros: o fluxo roda uma vez para cada
    for id_alvo in IDS_DO_CASO:

        # Achar o livro pelo id no JSON (sem depender de índice)
        livro = None
        for item in dados["livros"]:
            if item["id"] == id_alvo:
                livro = item
        if livro is None:
            print(f"ATENÇÃO: o id {id_alvo} não existe no livros.json (adicionar antes de rodar)")
            continue

        print("=" * 50)
        print(f"Testando {livro['id']}: {livro['titulo']} (preço na lista: R$ {livro['preco']:.2f})")

        # PASSO 1: buscar o título na vitrine
        pagina.goto(url_vitrine)

        # POPUP DE ANIVERSÁRIO: pode demorar, esperamos até 8s
        try:
            pagina.locator("g > path").click(timeout=8000)
            print("Pop-up de aniversário fechado")
        except Exception:
            print("Pop-up não apareceu, seguindo")

        campo_busca = pagina.get_by_role("textbox", name="O que você está procurando?")
        campo_busca.fill(livro["titulo"])
        pagina.get_by_role("button", name="buscar produtos na loja").click()

        # PASSO 2: verificar se o anúncio é exibido
        termo = livro["titulo"][:20]
        anuncios = pagina.locator(CARDS).filter(has_text=termo)
        total_anuncios = anuncios.count()
        print(f"Anúncios na vitrine para '{termo}': {total_anuncios}")

        # Verificação cruzada: o título aparece em algum texto da página?
        texto_pagina = pagina.locator("body").inner_text()
        titulo_na_pagina = termo.lower() in texto_pagina.lower()
        print(f"Verificação cruzada: título presente no texto da página: {titulo_na_pagina}")

        # PASSO 3: registrar o resultado
        if total_anuncios == 0 and not titulo_na_pagina:
            print(f"TC-24: anúncio de {livro['id']} NÃO EXIBIDO: R$ {livro['preco']:.2f} está abaixo "
                  f"do piso da plataforma (R$ 12,00) — achado EV-01 confirmado para este título")
        elif total_anuncios == 0 and titulo_na_pagina:
            print("ATENÇÃO: contagem por cards deu 0 mas o título aparece na página (conferir evidência)")
        else:
            # Rota de surpresa: se aparecer, registrar e conferir o preço contra o piso
            texto_card = anuncios.first.inner_text()
            print("Texto do card:", texto_card.replace("\n", " | ")[:200])
            if livro["preco"] < PISO_PLATAFORMA:
                print("TC-24: ATENÇÃO: anúncio EXIBIDO com preço abaixo do piso — atualizar o achado EV-01")

        # Evidência individual por livro (nomes distintos)
        os.makedirs(PASTA_EVIDENCIA, exist_ok=True)
        nome_livro = livro["id"].replace("L-", "livro")
        pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-24_{nome_livro}_busca_vitrine.png", full_page=True)

    print("Evidências salvas em:", PASTA_EVIDENCIA)

    navegador.close()