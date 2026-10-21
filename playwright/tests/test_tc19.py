# -*- coding: utf-8 -*-
# TC-19: Coerência completa da avaria — descrição genérica que omite as avarias
# Massa: Livro 7 'Eu Duvido Você Terminar Este Grimório' (frente3_livros.json)
# Semiautomatizado: o script conta fotos, lê a descrição e pré-checa os termos;
# o julgamento humano confirma a omissão contra a Lista do Livreiro

import json
import os
import time
from playwright.sync_api import sync_playwright

CAMINHO_JSON = "playwright/data/frente3_livros.json"
PASTA_EVIDENCIA = "evidencias/2026-10-20"

ID_ALVO = "L-7"

# Termos do dicionário que a descrição DEVERIA citar (Lista do Livreiro: grifo
# e linha sublinhada) — a omissão deles é a não conformidade que o caso caça
TERMOS_ESPERADOS = ["grifo", "sublinhado"]


def abrir_vitrine(pagina, url):
    pagina.goto(url, wait_until="domcontentloaded")
    pagina.wait_for_timeout(2000)
    print("Vitrine carregada (DOM pronto)")
    try:
        pagina.locator("g > path").click(timeout=8000)
        print("Pop-up de aniversário fechado")
    except Exception:
        print("Pop-up não apareceu na vitrine, seguindo")


def fechar_popup_se_aparecer(pagina, onde):
    # O pop-up aparece depois da navegação ao detalhe
    try:
        pagina.locator("g > path").click(timeout=5000)
        print(f"Pop-up de aniversário fechado ({onde})")
    except Exception:
        print(f"Pop-up não apareceu ({onde}), seguindo")


def rolar_pagina(pagina):
    # Cards só renderizam ao entrar na tela
    altura_total = pagina.evaluate("document.body.scrollHeight")
    posicao = 0
    while posicao < altura_total:
        posicao += 600
        pagina.evaluate(f"window.scrollTo(0, {posicao})")
        pagina.wait_for_timeout(400)
        altura_total = pagina.evaluate("document.body.scrollHeight")
    pagina.evaluate("window.scrollTo(0, 0)")
    pagina.wait_for_timeout(1000)


def src_foto_principal(pagina):
    # A foto principal é a maior imagem renderizada da página
    return pagina.evaluate("""() => {
        const imgs = Array.from(document.querySelectorAll('img'));
        let maior = null, area = 0;
        for (const im of imgs) {
            const r = im.getBoundingClientRect();
            const a = r.width * r.height;
            if (a > area && im.src) { area = a; maior = im; }
        }
        return maior ? maior.src : null;
    }""")


def esperar_src_mudar(pagina, src_anterior, timeout_ms):
    inicio = time.time()
    while (time.time() - inicio) * 1000 < timeout_ms:
        atual = src_foto_principal(pagina)
        if atual and atual != src_anterior:
            return atual
        pagina.wait_for_timeout(300)
    return src_foto_principal(pagina)


def contar_por_diretorio(pagina):
    # Contagem por srcs únicos do diretório do CDN (query string removida antes
    # de derivar o diretório — a query contém barras)
    src_principal = src_foto_principal(pagina)
    if not src_principal:
        print("Diretório: sem imagem principal")
        return 0, []
    diretorio = src_principal.split("?")[0].rsplit("/", 1)[0] + "/"
    srcs = pagina.evaluate("""(dir) => {
        const imgs = Array.from(document.querySelectorAll('img'));
        const unicos = new Set();
        for (const im of imgs) {
            const r = im.getBoundingClientRect();
            if (im.src && im.src.startsWith(dir) && r.width > 100) {
                unicos.add(im.src.split('?')[0]);
            }
        }
        return Array.from(unicos);
    }""", diretorio)
    print(f"Diretório das fotos do anúncio: {diretorio}")
    return len(srcs), srcs


def contar_fotos(pagina):
    # Camada 1: walk com espera ativa (carrossel que troca o src)
    # Camada 2: carrossel deslizante — contagem por srcs únicos do diretório
    # Foto única: sem botão Next
    botao_next = pagina.get_by_role("button", name="Next slide")
    if botao_next.count() == 0:
        print("Botão 'Next slide' ausente — galeria de foto única")
        return 1, ["foto única (sem botão Next)"]
    botao = botao_next.first
    vistos = []
    for passo in range(10):
        src = src_foto_principal(pagina)
        if src and src in vistos:
            print(f"Walk: src repetiu no passo {passo + 1} — fim da galeria")
            break
        if src:
            vistos.append(src)
        try:
            if botao.is_disabled():
                print("Walk: botão desabilitado — última foto alcançada")
                break
        except Exception:
            break
        botao.click()
        novo_src = esperar_src_mudar(pagina, src, 5000)
        if novo_src == src:
            print(f"Walk: src NÃO mudou após o Next (passo {passo + 1}) — carrossel desliza, fotos já no DOM")
            return contar_por_diretorio(pagina)
    return len(vistos), vistos


def contar_fotos_dupla(pagina):
    # Walk + diretório sempre, com reconciliação — divergência é sinal de drift
    total_walk, fontes_walk = contar_fotos(pagina)
    total_dir, fontes_dir = contar_por_diretorio(pagina)
    if total_walk == total_dir:
        print(f"Contagem dupla CONFERE: {total_walk} fotos (walk + diretório)")
        return total_walk, fontes_walk
    print(f"ATENÇÃO: contagens divergem — walk/carrossel: {total_walk} | diretório do CDN: {total_dir}")
    print("O carrossel mostra o que o comprador navega; o diretório pode guardar fotos removidas. Conferir visualmente antes de protocolar.")
    return total_walk, fontes_walk + fontes_dir


def ler_descricao(pagina):
    # Expande o 'Veja mais' DENTRO do bloco de descrição e lê o maior elemento
    resultado = pagina.evaluate("""() => {
        const els = Array.from(document.querySelectorAll('*'));
        let bloco = null;
        for (const el of els) {
            const t = (el.innerText || '').trim();
            if (t.startsWith('Descrição:') && (!bloco || t.length > (bloco.innerText || '').trim().length)) bloco = el;
        }
        if (!bloco) return 'bloco não encontrado';
        for (const a of bloco.querySelectorAll('*')) {
            const txt = (a.textContent || '').trim();
            if (txt === 'Veja mais' || txt === 'Fechar') { a.click(); return 'expandido'; }
        }
        return 'sem veja mais';
    }""")
    if resultado == "expandido":
        pagina.wait_for_timeout(1000)
        print("Bloco de descrição expandido")
    else:
        print(f"Expansão: {resultado}")
    texto = pagina.evaluate("""() => {
        const els = Array.from(document.querySelectorAll('*'));
        let melhor = '';
        for (const el of els) {
            const t = (el.innerText || '').trim();
            if (t.startsWith('Descrição:') && t.length > melhor.length) melhor = t;
        }
        return melhor;
    }""")
    return texto.replace("\n", " ").replace("Veja mais", "").replace("Fechar", "").strip()


with open(CAMINHO_JSON, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

livro = None
for item in dados["livros"]:
    if item["id"] == ID_ALVO:
        livro = item
if livro is None:
    print(f"ATENÇÃO: o id {ID_ALVO} não existe no frente3_livros.json (validar a massa)")
    raise SystemExit

termo = livro["titulo"][:20]
regua = dados["regua_fotos"]
minimo_regua = regua["bom_estado"] if livro["estado"] == "bom" else regua["avariado"]
rotulo_estado = "em bom estado" if livro["estado"] == "bom" else "avariado"
print(f"Testando {livro['id']}: {livro['titulo']} (estado na lista: {livro['estado']}; régua: {minimo_regua} fotos)")

with sync_playwright() as p:

    navegador = p.chromium.launch(headless=False)
    contexto = navegador.new_context(locale="pt-BR", viewport={"width": 1440, "height": 900})
    pagina = contexto.new_page()

    # PASSO 1: vitrine, rolagem e abertura do anúncio
    abrir_vitrine(pagina, dados["vitrine_ev"])
    rolar_pagina(pagina)
    print("Rolagem concluída — cards renderizados")

    link_card = pagina.get_by_role("link", name=termo).first
    if link_card.count() == 0:
        total_cards = pagina.locator(".product-list__items .product-item").count()
        print(f"ATENÇÃO: link do card não encontrado após a rolagem | cards no DOM: {total_cards}")
        if total_cards > 0:
            primeiro = pagina.locator(".product-list__items .product-item").first.inner_text()
            print("Texto do 1º card:", primeiro.replace("\n", " | ")[:150])
        raise SystemExit

    link_card.click()
    pagina.wait_for_load_state("domcontentloaded")
    pagina.wait_for_timeout(2000)
    print("Página de detalhe aberta:", pagina.url)
    if "/livro/" not in pagina.url:
        print("ATENÇÃO: a URL não é de página de detalhe — conferir evidência")

    fechar_popup_se_aparecer(pagina, "página de detalhe")

    # PASSO 2: contar as fotos da galeria (contagem dupla: walk + diretório)
    total_fotos, fontes = contar_fotos_dupla(pagina)
    print(f"Fotos contadas na galeria: {total_fotos}")
    for f in fontes[:6]:
        print("  foto:", str(f)[:100])
    print(f"Anunciadas na massa: {livro['fotos_anunciadas']}")

    # PASSO 3: ler a descrição publicada
    descricao = ler_descricao(pagina)
    print("Descrição publicada:", descricao[:300])

    # PASSO 4: régua + dicionário — caso NEGATIVO (a descrição deve OMITIR as avarias)
    print("---")
    fotos_ok = total_fotos >= minimo_regua
    if fotos_ok:
        print(f"Régua de fotos ATENDIDA: {total_fotos} fotos >= mínimo de {minimo_regua} para livro {rotulo_estado}")
    else:
        print(f"ATENÇÃO: {total_fotos} fotos < mínimo de {minimo_regua} da régua (não é o foco deste caso, mas registrar)")

    descricao_baixa = descricao.lower()
    termos_ausentes = [t for t in TERMOS_ESPERADOS if t not in descricao_baixa]
    if termos_ausentes:
        print(f"Não conformidade IDENTIFICADA: a descrição NÃO cita as avarias da Lista (termos ausentes: {termos_ausentes})")
        print("TC-19: Aprovado — a omissão foi identificada e registrada com precisão")
        print("O ANÚNCIO é reprovado (falta de transparência: avarias existentes não descritas); bug vai para o Jira")
    else:
        print(f"ATENÇÃO: a descrição cita os termos {TERMOS_ESPERADOS} — o caso esperava a omissão (descrição genérica na massa)")
        print("TC-19: conferir a massa e o anúncio antes de protocolar")

    # EVIDÊNCIA
    os.makedirs(PASTA_EVIDENCIA, exist_ok=True)
    pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-19_livro7_detalhe_fotos.png", full_page=True)
    print("Evidência salva em:", PASTA_EVIDENCIA)

    contexto.close()
    navegador.close()