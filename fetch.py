import requests
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from io import BytesIO

# Funkcja pobierająca zdjęcia ze strony
def Fetch_Nasa_Images(query):  
    url = "https://images-api.nasa.gov/search"  # link do strony
    params_q = {'q': query}  # Ustala parametry
    response = requests.get(url, params=params_q)
    if response.status_code == 200:  # Sprawdza, czy odpowiedź była poprawna
        return response.json()
    else:
        raise Exception(f'Nie udało się pobrać danych, kod błędu {response.status_code}')  # Informacja w wypadku błędu

 # Funkcja wyświetlająca powiększony obraz po kliknięciu
def Image_Click(img_data): 
    for widget in image_display_area.winfo_children():  # Czyści miejsce dla obrazu
        widget.destroy()

    img = Image.open(BytesIO(img_data))
    img.thumbnail((600, 600))  # Zmienia rozmiar zdjęcia na 600x600
    img_tk = ImageTk.PhotoImage(img)  # Konwertuje zdjęcie na format Tkinter
    lbl = tk.Label(image_display_area, image=img_tk, bg='black')  # Tworzy etykietę
    lbl.image = img_tk  # Zachowuje referencję do obrazu
    lbl.pack()

# Funkcja do wyświetlania zdjęć
def display_images(query):
    try:
        result_label.config(text="")  # Usuwa ewentualny tekst o braku wyników
        data = Fetch_Nasa_Images(query)  # Pobiera dane ze strony NASA
        items = data.get('collection', {}).get('items', [])  # Odczytuje wyniki wyszukiwania

        # Komunikat w wypadku braku wyników
        if not items: 
            result_label.config(text="Brak wyników wyszukiwania")
            return

        # Czyści miejsce dla nowych wyników
        for widget in frame.winfo_children():
            widget.destroy()

        # Przetwarza pierwsze znalezione 18 zdjęć
        for idx, item in enumerate(items[:18]):
            item_data = item.get('data', [])
            title = item_data[0].get("title")  # Pobiera tytuł zdjęcia

            links = item.get('links', [])  # Pobiera linki do zdjęć

            # Sprawdza czy istnieje link
            if links:
                href = links[0].get('href', '')  # Pobiera URL zdjęcia
                if href:  # Sprawdza czy URL jest dostępny
                    response = requests.get(href)  # Pobiera dane zdjęcia
                    if "image" in response.headers.get("Content-Type", ""):  # Sprawdza, czy plik jest zdjęciem
                        img_data = response.content  # Pobiera dane zdjęcia
                        img = Image.open(BytesIO(img_data)) 
                        img.thumbnail((180, 180))  # Zmienia rozmiar zdjęcia na 180x180
                        img_tk = ImageTk.PhotoImage(img)  # Konwertuje zdjęcie na format Tkinter
                    else:
                        continue
                    img_tk = ImageTk.PhotoImage(img)  # Ponownie przypisuje zdjęcie do zmiennej

                    img_frame = tk.Frame(frame, bg='black')  # Tworzy obramówkę dla zdjęcia
                    img_frame.grid(row=idx // 6, column=idx % 6, padx=10, pady=10)  # Układa zdjęcia

                    panel = tk.Label(img_frame, image=img_tk, bg='black', cursor="hand2")  # Tworzy etykietę
                    panel.image = img_tk  # Zachowuje referencję do zdjęcia
                    panel.pack()  # Dodaje etykietę
                    panel.bind("<Button-1>", lambda e, d=img_data: Image_Click(d))  # Dodaje możliwość powiększania zdjęcia po kliknięciu

                    title_label = tk.Label(img_frame, text=title, fg='lime green', bg='black', wraplength=180, font=('Courier', 10))  # Tworzy etykietę z tytułem
                    title_label.pack()  # Dodaje etykietę

    # Jeżeli wystąpi błąd wyświetla komunikat
    except Exception as e:
        result_label.config(text=f"Wystąpił błąd: {e}")

# Funkcja obsługująca wyszukiwanie obrazów dla podanej frazy
def search():
    query = entry.get()  # Pobiera tekst
    if query:  # Sprawdza czy tekst został podany
        display_images(query)  # Wywołuje funkcję do wyświetlania zdjęć

root = tk.Tk()  # Tworzy okno dla aplikacji
root.title("NASA Images")  # Zmienia tytuł aplikacji
root.configure(bg='black')  # Ustawia kolor tła

# Modyfikacje graficzne dla pola wyszukiwania
entry = tk.Entry(root, width=50, bg='light gray', fg='green')
entry.pack(pady=10)

# Modyfikacje graficzne dla przycisku wyszukiwania
search_button = tk.Button(root, text="Szukaj", command=search, bg='light gray', fg='green')
search_button.pack() 

# Modyfikacje graficzne etykiet
result_label = tk.Label(root, text="", fg='red', bg='black')
result_label.pack()

# Grupuje elementy wyszukiwania
frame = tk.Frame(root, bg='black')
frame.pack()

# Tworzy miejsce do wyświetlania klikniętych zdjęć
image_display_area = tk.Frame(root, bg='black')
image_display_area.pack(pady=20)

root.mainloop()  # Sprawia że aplikacja może działać dopóki użytkownik nie zamknie okna
