import requests
import json
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from io import BytesIO
import webbrowser

def Fetch_Nasa_Images(query):
    url = "https://images-api.nasa.gov/search"
    
    params_q = {
        'q': query
    }
    
    response = requests.get(url, params=params_q)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'Nie udało się pobrać danych, kod błędu {response.status_code}')

# Funkcja otwierająca obraz w przeglądarce
def open_image(url):
    webbrowser.open(url)

def display_images(query):
    try:
        data = Fetch_Nasa_Images(query) # Pobranie danych z API
        items = data.get('collection', {}).get('items', []) # Pobranie listy wyników
        
        if not items:
            result_label.config(text="Brak wyników wyszukiwania")
            return
        
        for widget in frame.winfo_children():  # Czyści poprzednie wyniki
            widget.destroy()
        
        for item in items[:5]:
            item_data = item.get('data', [])
            title = item_data[0].get("title", "Brak tytułu")
            
            links = item.get('links', [])
            if links:
                href = links[0].get('href', '')
                if href:
                    response = requests.get(href)
                    img = Image.open(BytesIO(response.content))
                    img.thumbnail((200, 200))
                    img = ImageTk.PhotoImage(img)
                    
                    panel = tk.Label(frame, image=img, cursor="hand2")
                    panel.image = img
                    panel.bind("<Button-1>", lambda e, url=href: open_image(url))
                    panel.pack(pady=5)
                    
                    title_label = tk.Label(frame, text=title, wraplength=200)
                    title_label.pack()
                    
    except Exception as e:
        result_label.config(text=f"Wystąpił błąd: {e}")

def search():
    query = entry.get()
    if query:
        display_images(query)

root = tk.Tk()
root.title("NASA Image Viewer")

entry = ttk.Entry(root, width=50)
entry.pack(pady=10)

search_button = ttk.Button(root, text="Szukaj", command=search)
search_button.pack()

result_label = tk.Label(root, text="")
result_label.pack()

frame = tk.Frame(root)
frame.pack()

root.mainloop()
