import pygame
import requests
import io
import sys
import threading

API_BASE = "https://images-api.nasa.gov/search?media_type=image" # Link do strony NASA z której pobieramy zdjęcia
THUMB_SIZE = (160, 120) # Rozmiar miniaturki
GRID_COLS = 4 # Liczba kolumn
GRID_ROWS = 5 # Liczba wierszy
NUM_IMAGES = GRID_COLS * GRID_ROWS # Łączna liczba zdjęć na stronie
PADDING = 10 # Odstępy między zdjęciami
WINDOW_SIZE = (GRID_COLS * (THUMB_SIZE[0] + PADDING) + PADDING, # Obliczenie wielkości okna
               GRID_ROWS * (THUMB_SIZE[1] + PADDING) + PADDING + 40)
FPS = 30

QUERY = "" # Domyślne zapytanie

# Klasa reprezentująca pojedyncze zdjęcie
class ImageTile:
    def __init__(self, thumb_url, full_url, position):
        self.thumb_url = thumb_url # URL miniaturki
        self.full_url = full_url # URL zdjęcia
        self.position = position # Pozycja zdjęcia w oknie
        self.thumb_surface = self.get_placeholder() # Placeholder
        self.loaded = False # Sprawdza czy zdjęcie zostało załadowane
        threading.Thread(target=self.async_load_thumbnail, daemon=True).start() # Asynchroniczne wczytywanie zdjęć

    # Placeholder
    def get_placeholder(self):
        surface = pygame.Surface(THUMB_SIZE)
        surface.fill((100, 100, 100))
        return surface
    # Ładowanie miniaturek
    def async_load_thumbnail(self):
        try:
            response = requests.get(self.thumb_url, timeout=10) # Pobiera miniaturkę z internetu
            image_bytes = io.BytesIO(response.content) # Tworzy obiekt ze zdjęcia
            image = pygame.image.load(image_bytes) # Wczytuje zdjęcie do Pygame
            self.thumb_surface = pygame.transform.scale(image, THUMB_SIZE) # Skaluje do THUMB_SIZE
            self.loaded = True
        except Exception as e:
            print("Nie udało się wczytać miniaturki:", e) # Wiadomość w konsoli w wypadku błędu

    # Ładowanie zdjęć
    def load_full_image(self):
        try:
            response = requests.get(self.full_url, timeout=10) # Pobiera zdjęcia
            image_bytes = io.BytesIO(response.content) # Konwertuje na bajty
            img = pygame.image.load(image_bytes) # Wczytuje zdjęcie do Pygame
            screen_w, screen_h = pygame.display.get_surface().get_size() # Pobiera rozmiar okna
            img_rect = img.get_rect()
            scale = min(screen_w / img_rect.width, screen_h / img_rect.height)
            new_size = (int(img_rect.width * scale), int(img_rect.height * scale))
            return pygame.transform.scale(img, new_size) # Skaluje zdjęcie
        except Exception as e:
            print("Błąd przy wczytywaniu zdjęcia:", e) # Wiadomość w konsoli w wypadku błędu
            return None

# Funkcja pobierająca zdjęcia
def fetch_nasa_images(query, page=1):
    url = f"{API_BASE}&q={query}&page={page}" # Tworzy URL zapytania
    print("Fetching:", url)
    try:
        r = requests.get(url, timeout=10) # Wysyła żądanie do API
        data = r.json()
    except Exception as e:
        print("Błąd przy pobieraniu danych:", e) # Wiadomość w konsoli w wypadku błędu
        return []

    items = data.get("collection", {}).get("items", []) # Pobiera listę elementów
    tiles = [] # Lista zdjęć
    count = 0 # Licznik zdjęć
    for item in items:
        if count >= NUM_IMAGES:
            break
        links = item.get("links", []) # Pobiera miniaturkę
        if links:
            thumb_url = links[0].get("href") # URL miniaturki
            nasa_id = item.get("data", [{}])[0].get("nasa_id") # ID zdjęcia
            asset_url = f"https://images-api.nasa.gov/asset/{nasa_id}" # link do danych
            try:
                asset_response = requests.get(asset_url, timeout=10) # Pobiera dane
                asset_data = asset_response.json()
                full_url = thumb_url
                for url_candidate in asset_data.get("collection", {}).get("items", []):
                    candidate_href = url_candidate.get("href", "")
                    if candidate_href.lower().endswith(".jpg"): # Wybiera pierwsze zdjęcie
                        full_url = candidate_href
                        break
            except Exception:
                full_url = thumb_url

            col = count % GRID_COLS     # Oblicza kolumnę
            row = count // GRID_COLS    # Oblicza wiersz
            x = PADDING + col * (THUMB_SIZE[0] + PADDING)
            y = PADDING + row * (THUMB_SIZE[1] + PADDING)
            tile = ImageTile(thumb_url, full_url, (x, y)) # Tworzy kafelek
            tiles.append(tile) # Dodaje go do listy
            count += 1

    return tiles

# Ekran wprowadzania zapytania przez użytkownika
def search_input_screen():
    global QUERY
    pygame.init()
    screen = pygame.display.set_mode((600, 200)) # Tymczasowe okno
    pygame.display.set_caption("Wpisz frazę wyszukiwania NASA")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)

    input_box = pygame.Rect(50, 80, 500, 40) # Pole tekstowe
    color_active = pygame.Color('dodgerblue2')
    color_inactive = pygame.Color('lightskyblue3')
    color = color_inactive
    active = False
    text = ''
    done = False
    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: # Zamknięcie programu
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos):
                    active = True
                else:
                    active = False
                color = color_active if active else color_inactive
            elif event.type == pygame.KEYDOWN:
                if active:
                    if event.key == pygame.K_RETURN: # Zatwierdzenie frazy
                        QUERY = text.strip() or "space"
                        done = True
                    elif event.key == pygame.K_BACKSPACE:
                        text = text[:-1] # Usuwanie znaku
                    else:
                        text += event.unicode # Dodawanie znaku

        screen.fill((30, 30, 30))  # Tło
        label = font.render("Wpisz zapytanie:", True, (255, 255, 255))
        screen.blit(label, (50, 30))  # Wyświetla instrukcję

        txt_surface = font.render(text, True, color)  # Tekst użytkownika
        width = max(500, txt_surface.get_width()+10)
        input_box.w = width
        screen.blit(txt_surface, (input_box.x+5, input_box.y+5))
        pygame.draw.rect(screen, color, input_box, 2)

        pygame.display.flip()
        clock.tick(30)

def main():
    global QUERY
    search_input_screen() # Ekran z wpisywaniem zapytania
    screen = pygame.display.set_mode(WINDOW_SIZE) # Główne okno
    pygame.display.set_caption("Wyszukiwarka zdjęć NASA")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    current_page = 1 # Strona początkowa
    tiles = fetch_nasa_images(QUERY, current_page) # Pobiera pierwszą stronę zdjęć
    fullscreen_image = None # Sprawdza czy zdjęcie jest powiększone

    running = True
    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q: # Wyjście za pomocą q
                    running = False
                elif event.key == pygame.K_n and fullscreen_image is None: # Następna strona
                    current_page += 1
                    tiles = fetch_nasa_images(QUERY, current_page)
                elif event.key == pygame.K_b and current_page > 1 and fullscreen_image is None: # Poprzednia strona
                    current_page -= 1
                    tiles = fetch_nasa_images(QUERY, current_page)
                elif event.key == pygame.K_ESCAPE and fullscreen_image is not None:
                    fullscreen_image = None # Zamknięcie powiększonego zdjęcia
                elif event.key == pygame.K_r and fullscreen_image is None: # Nowe wyszukiwanie
                    search_input_screen()
                    screen = pygame.display.set_mode(WINDOW_SIZE)
                    current_page = 1
                    tiles = fetch_nasa_images(QUERY, current_page)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if fullscreen_image is None and event.button == 1:
                    mouse_pos = event.pos
                    for tile in tiles:
                        thumb_rect = pygame.Rect(tile.position, THUMB_SIZE)
                        if thumb_rect.collidepoint(mouse_pos):
                            full_img = tile.load_full_image() # Powiększanie zdjęciu
                            if full_img:
                                fullscreen_image = full_img
                            break
        if fullscreen_image:
            screen.fill((0, 0, 0))
            img_rect = fullscreen_image.get_rect(center=screen.get_rect().center)
            screen.blit(fullscreen_image, img_rect)
        else:
            screen.fill((50, 50, 50))
            info = f"Zapytanie: {QUERY} | n: dalej, b: wstecz, r: wyszukaj, q: wyjście, ESC: zamknij zdjęcie)"
            page_text = font.render(info, True, (255, 255, 255))
            screen.blit(page_text, (PADDING, WINDOW_SIZE[1] - 30)) # Pasek z informacjami
            for tile in tiles:
                screen.blit(tile.thumb_surface, tile.position) # Miniaturki

        pygame.display.flip() # Odświeżenie ekranu

    pygame.quit() # Zamyka pygame
    sys.exit() # Kończy program

# Uruchomienie programu
if __name__ == '__main__':
    main()