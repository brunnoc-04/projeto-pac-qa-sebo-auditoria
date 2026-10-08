import json
import re
from pathlib import Path
from playwright.sync_api import Page, expect

# --- Caminhos robustos (independem de onde o pytest roda) ---
TESTS = Path(__file__).parent          # .../playwright/tests
RAIZ = TESTS.parent.parent             # raiz do projeto

# --- Gabarito (massa de dados) ---
dados = json.loads((TESTS.parent / "data" / "livros.json").read_text(encoding="utf-8"))
VITRINE = dados["vitrine_ev"]
LIVROS = dados["livros"]

# --- Seletores descobertos no DevTools ---
CARDS = ".product-list__items .product-item"                              # anúncios da vitrine
LINK = ".product-item__link"                                              # link do card (title = título completo)
FOTOS = ".pictures__carousel .swiper-slide:not(.swiper-slide-duplicate)"  # slides reais (sem clones)
SLIDE_COM_ROTULO = ".pictures__carousel .swiper-slide[aria-label*=' / ']" # slide que carrega o "1 / 2"
IMG_GALERIA = ".pictures__carousel img"                                   # a tag <img> dentro da galeria
SETA_PROXIMA = ".swiper-button-next"                                      # seta de próxima foto

DATA_CICLO = "2026-10-07"


def esperar_foto_carregada(page: Page) -> None:
    """Espera condicional: só libera o print quando a imagem EXISTE de verdade.
    Camada 1: visível na tela. Camada 2: pixels baixados (complete + naturalWidth)."""
    img = page.locator(IMG_GALERIA).first
    expect(img).to_be_visible(timeout=10_000)   # espera até 10s; se demorar mais, falha com motivo claro
    page.wait_for_function(
        "() => { const i = document.querySelector('.pictures__carousel img');"
        " return i && i.complete && i.naturalWidth > 0; }",
        timeout=10_000,
    )


def total_de_fotos(page: Page) -> int:
    """Lê o total de fotos do rótulo de acessibilidade 'X / Y' do carrossel."""
    slide = page.locator(SLIDE_COM_ROTULO).first
    rotulo = slide.get_attribute("aria-label")   # ex.: "1 / 2"
    match = re.search(r"\d+\s*/\s*(\d+)", rotulo)
    return int(match.group(1)) if match else 0


def capturar_galeria(page: Page, id_livro: str, destino_dir: Path):
    """Prova visual: espera carregar → foto 1 → navega → espera carregar → foto 2."""
    esperar_foto_carregada(page)
    page.screenshot(path=str(destino_dir / f"TC-18_{id_livro}_ev_foto1.png"))

    if page.locator(FOTOS).count() > 1:
        page.locator(SETA_PROXIMA).click()
        page.wait_for_timeout(800)        # aguarda a animação do carrossel terminar
        esperar_foto_carregada(page)      # a foto 2 também precisa ter carregado antes do print
        page.screenshot(path=str(destino_dir / f"TC-18_{id_livro}_ev_foto2.png"))


def test_tc18_padrao_de_fotos_da_vitrine(page: Page):
    """TC-18 (RN-08): nenhum anúncio da vitrine pode ter 1 ou 3 fotos."""
    page.goto(VITRINE)

    cards = page.locator(CARDS)
    expect(cards.first).to_be_visible()

    resultados = []   # coleta o que cada anúncio respondeu, pro log no final

    for i in range(cards.count()):
        card = cards.nth(i)
        titulo = card.locator(LINK).get_attribute("title")   # título completo, sem reticência
        card.locator(LINK).click()                           # entra no anúncio

        n_fotos = total_de_fotos(page)                       # fonte 1: o rótulo "1 / 2"
        n_slides = page.locator(FOTOS).count()               # fonte 2: contagem dos slides
        assert n_fotos == n_slides, f"{titulo}: rótulo diz {n_fotos}, slides = {n_slides}"

        assert n_fotos not in (1, 3), f"{titulo}: {n_fotos} foto(s) viola a RN-08"

        id_livro = LIVROS[i]["id"] if i < len(LIVROS) else f"card-{i+1}"
        destino_dir = RAIZ / "evidencias" / DATA_CICLO
        destino_dir.mkdir(parents=True, exist_ok=True)
        capturar_galeria(page, id_livro, destino_dir)

        resultados.append((id_livro, titulo, n_fotos))
        page.go_back()   # volta pra vitrine pro próximo anúncio

    # Log de auditoria: o veredito legível em 5 segundos
    destino_dir = RAIZ / "evidencias" / DATA_CICLO
    with open(destino_dir / "TC-18_log.csv", "w", encoding="utf-8", newline="") as f:
        f.write("id_livro;titulo;fotos_encontradas;veredito\n")
        for id_livro, titulo, n_fotos in resultados:
            f.write(f"{id_livro};{titulo};{n_fotos};PASSOU\n")