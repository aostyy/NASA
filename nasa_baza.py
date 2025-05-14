import pygame
import requests
import io
import sys
import threading
import sqlite3

API_BASE = "https://images-api.nasa.gov/search?media_type=image" # Link do strony NASA z której pobieramy zdjęcia
THUMB_SIZE = (160, 120) # Rozmiar miniaturki
GRID_COLS = 4 # Liczba kolumn
GRID_ROWS = 5 # Liczba wierszy
NUM_IMAGES = GRID_COLS * GRID_ROWS # Łączna liczba zdjęć na stronie
PADDING = 10 # Odstępy między zdjęciami
# Obliczenie wielkości okna
WINDOW_SIZE = (
    GRID_COLS * (THUMB_SIZE[0] + PADDING) + PADDING,
    GRID_ROWS * (THUMB_SIZE[1] + PADDING) + PADDING + 40
)
FPS = 30
QUERY = "" # Domyślne zapytanie
DB_FILE = 'cache.db' # Nazwa pliku bazy danych SQLite

# Inicjalizacja baze danych SQLite
def init_db():
    conn = sqlite3.connect(DB_FILE)  # Połączenie z plikiem bazy danych
    c = conn.cursor()  # Obiekt do wykonywania zapytań
    # Tworzenie tabeli
    c.execute(
        '''
        CREATE TABLE IF NOT EXISTS cache (
            query TEXT,            -- fraza wyszukiwania
            page INTEGER,          -- numer strony wyników
            img_index INTEGER,     -- indeks obrazka w siatce
            thumb_url TEXT,        -- URL miniaturki
            full_url TEXT,         -- URL pełnego zdjęcia
            PRIMARY KEY (query, page, img_index)  -- unikalny klucz
        )
        '''
    )
    conn.commit()  # Zapis zmian
    return conn  # Zwrócenie połączenia do dalszego użycia

# Funkcja do całkowitego wyczyszczenia bazy danych
def clear_db(db_conn):
    c = db_conn.cursor()
    c.execute('DELETE FROM cache')  # usunięcie wszystkich rekordów
    db_conn.commit()  # zapis zmian
    print("Baza danych została wyczyszczona.")

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
        surface = pygame.Surface(THUMB_SIZE)  # Utworzenie powierzchni o rozmiarze miniaturki
        surface.fill((100, 100, 100))
        return surface

    # Asynchroniczne pobieranie miniaturki z internetu
    def async_load_thumbnail(self):
        try:
            r = requests.get(self.thumb_url, timeout=10)  # Pobranie danych zdjęcia
            buf = io.BytesIO(r.content)  # Zapis bajtów
            img = pygame.image.load(buf)  # Wczytanie zdjęcia do Pygame
            self.thumb_surface = pygame.transform.scale(img, THUMB_SIZE) # Skalowanie do rozmiaru miniaturki
            self.loaded = True  # Oznaczenie jako załadowane
        except Exception as e:
            print("Nie udało się wczytać miniaturki:", e)  # Błąd

    # Pobranie i skalowanie pełnego zdjęcia
    def load_full_image(self):
        try:
            r = requests.get(self.full_url, timeout=10)  # Pobiera zdjęcia
            buf = io.BytesIO(r.content)  # Zapis bajtów
            img = pygame.image.load(buf)  # Wczytanie do Pygame
            sw, sh = pygame.display.get_surface().get_size()  # rozmiar okna
            iw, ih = img.get_size()  # Oryginalne wymiary zdjęcia
            scale = min(sw/iw, sh/ih)  # Współczynnik skalowania
            new_size = (int(iw*scale), int(ih*scale))  # Nowe wymiary
            return pygame.transform.scale(img, new_size)  # Zwrócenie przeskalowanego zdjęcia
        except Exception as e:
            print("Błąd przy wczytywaniu zdjęcia:", e)
            return None

# Funkcja pobierająca zdjęcia
def fetch_nasa_images(query, page, db_conn):
    tiles = []
    c = db_conn.cursor()
    # Próba pobrania z cache
    c.execute(
        'SELECT img_index, thumb_url, full_url FROM cache WHERE query=? AND page=? ORDER BY img_index',
        (query, page)
    )
    rows = c.fetchall()  # Pobranie wszystkich pasujących wierszy
    if rows:
        print(f"Ładowanie z cache: {query}, strona {page}")
        for img_index, thumb, full in rows:
            col = img_index % GRID_COLS
            row = img_index // GRID_COLS
            x = PADDING + col*(THUMB_SIZE[0]+PADDING)
            y = PADDING + row*(THUMB_SIZE[1]+PADDING)
            tiles.append(ImageTile(thumb, full, (x, y)))
        return tiles  # Zwrócenie kafelków

    # Jeśli brak w bazie danych, pobierz ze strony
    url = f"{API_BASE}&q={query}&page={page}"
    print("Fetching from API:", url)
    try:
        r = requests.get(url, timeout=10)  # Wysłanie zapytania
        data = r.json()
    except Exception as e:
        print("Błąd pobierania danych:", e)
        return []

    items = data.get('collection', {}).get('items', [])  # Lista elementów
    count = 0  # Licznik załadowanych miniaturek
    for item in items:
        if count >= NUM_IMAGES:
            break  
        links = item.get('links', [])  # Linki do miniaturki
        if not links:
            continue
        thumb_url = links[0].get('href')  # URL miniaturki
        nasa_id = item.get('data', [{}])[0].get('nasa_id')  # Unikalne ID
        full_url = thumb_url
        # Próba pobrania pliku JPG
        try:
            asset = requests.get(f"https://images-api.nasa.gov/asset/{nasa_id}", timeout=10).json()
            for i in asset.get('collection', {}).get('items', []):
                href = i.get('href', '')
                if href.lower().endswith('.jpg'):
                    full_url = href
                    break
        except:
            pass

        # Zapis do cache
        c.execute(
            'INSERT OR REPLACE INTO cache(query,page,img_index,thumb_url,full_url) VALUES (?,?,?,?,?)',
            (query, page, count, thumb_url, full_url)
        )
        db_conn.commit()  # zapis zmian

        # Obliczenie pozycji kafelka
        col = count % GRID_COLS
        row = count // GRID_COLS
        x = PADDING + col*(THUMB_SIZE[0]+PADDING)
        y = PADDING + row*(THUMB_SIZE[1]+PADDING)
        tiles.append(ImageTile(thumb_url, full_url, (x, y)))  # Dodanie do listy
        count += 1

    return tiles

# Ekran wprowadzania zapytania przez użytkownika
def search_input_screen():
    global QUERY
    pygame.init()  # Inicjalizacja Pygame
    screen = pygame.display.set_mode((600,200))  # Tymczasowe okno
    pygame.display.set_caption("Wpisz frazę wyszukiwania NASA")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None,36)  # Czcionka
    input_box = pygame.Rect(50,80,500,40)  # Pole tekstowe
    color_active = pygame.Color('dodgerblue2')  # Kolor aktywnego pola
    color_inactive = pygame.Color('lightskyblue3')  # Kolor nieaktywnego pole
    active = False 
    text = ''  # Aktualny tekst
    done = False  # Status pętli
    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()  # Zamknięcie programu
            if event.type == pygame.MOUSEBUTTONDOWN:
                active = input_box.collidepoint(event.pos)
            if event.type == pygame.KEYDOWN and active:
                if event.key == pygame.K_RETURN:
                    QUERY = text.strip() or 'space'
                    done = True
                elif event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                else:
                    text += event.unicode
        screen.fill((30,30,30))  # Tło
        label = font.render("Wpisz zapytanie:", True, (255,255,255))
        screen.blit(label,(50,30))
        txt_surf = font.render(text, True, color_active if active else color_inactive)
        input_box.w = max(500, txt_surf.get_width()+10)  # Szerokość
        screen.blit(txt_surf,(input_box.x+5,input_box.y+5))
        pygame.draw.rect(screen, color_active if active else color_inactive, input_box,2)  # Obramowanie
        pygame.display.flip()
        clock.tick(30)  # Ograniczenie pętli do 30 FPS

def main():
    global QUERY
    db_conn = init_db()  # Utworzenie/otwarcie bazy danych
    search_input_screen()  # Ekran z wpisywaniem zapytania
    screen = pygame.display.set_mode(WINDOW_SIZE)  # Główne okno
    pygame.display.set_caption("Wyszukiwarka zdjęć NASA")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None,24)
    current_page = 1  # Strona początkowa
    tiles = fetch_nasa_images(QUERY, current_page, db_conn)  # Pobiera pierwszą stronę zdjęć
    fullscreen = None
    running = True  # Status pętli
    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_n and not fullscreen:
                    current_page += 1
                    tiles = fetch_nasa_images(QUERY, current_page, db_conn)  # Następna strona
                elif event.key == pygame.K_b and current_page>1 and not fullscreen:
                    current_page -= 1
                    tiles = fetch_nasa_images(QUERY, current_page, db_conn)  # Poprzednia strona
                elif event.key == pygame.K_r and not fullscreen:
                    search_input_screen()
                    current_page = 1
                    tiles = fetch_nasa_images(QUERY, current_page, db_conn)  # Nowe wyszukiwanie
                elif event.key == pygame.K_ESCAPE and fullscreen:
                    fullscreen = None  # Zamknięcie pełnego ekranu
                elif event.key == pygame.K_c and not fullscreen:
                    clear_db(db_conn)
                    tiles = fetch_nasa_images(QUERY, current_page, db_conn)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button==1 and not fullscreen:
                for tile in tiles:
                    rect = pygame.Rect(tile.position, THUMB_SIZE)
                    if rect.collidepoint(event.pos):
                        img = tile.load_full_image()  # Ładowanie pełnego ekranu
                        if img:
                            fullscreen = img
                        break
        screen.fill((50,50,50))
        if fullscreen:
            rect = fullscreen.get_rect(center=screen.get_rect().center)
            screen.blit(fullscreen, rect)  # Wyświetlenie pełnego ekranu
        else:
            info = f"Zapytanie: {QUERY} |  n: dalej, b: wstecz, r: szukaj, q: wyjście, c: czyść db, ESC: zamknij zdj)"
            screen.blit(font.render(info, True, (255,255,255)), (PADDING, WINDOW_SIZE[1]-30)) # Pasek z informacjami
            for t in tiles:
                screen.blit(t.thumb_surface, t.position)  # Miniaturki
        pygame.display.flip()  # Odświeżenie ekranu
    pygame.quit()  # Zamyka pygame
    sys.exit()  # Kończy program

# Uruchomienie programu
if __name__=='__main__':
    main()