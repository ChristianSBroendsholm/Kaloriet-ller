import requests
import customtkinter as ctk
from datetime import date
import sqlite3
from PIL import Image


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class Database:
    def __init__(self, name):
        self.conn = sqlite3.connect(name)
        self.cur = self.conn.cursor()
        self.cur.execute(
            """CREATE TABLE IF NOT EXISTS foods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                name TEXT NOT NULL,
                weight REAL NOT NULL,
                calories REAL NOT NULL,
                protein REAL NOT NULL,
                day DATE NOT NULL
            )"""
        )
        self.conn.commit()

    def insert_entry(self, product_id, name, grams, calories, protein):
        self.cur.execute(
            "INSERT INTO foods (product_id, name, weight, calories, protein, day) VALUES (?, ?, ?, ?, ?, ?)",
            (product_id, name, grams, calories, protein, date.today().isoformat())
        )
        self.conn.commit()


class Model:
    def __init__(self, db):
        self.db = db

    def search_product(self, word):
        r = requests.get(
            "https://world.openfoodfacts.org/cgi/search.pl",
            params={
                "search_terms": word,
                "search_simple": 1,
                "action": "process",
                "json": 1
            }
        )
        products = r.json()["products"]
        term = word.lower()

        def relevance(product):
            name = product.get("product_name", "").lower()
            ingredients = product.get("ingredients_text", "").lower()
            score = 0
            if name == term:
                score += 5
            elif term in name:
                score += 3
            if term in ingredients:
                score += 1
            return (-score, len(name))

        products.sort(key=relevance)
        return products

    def calc_nutrition(self, product, grams):
        factor = grams / 100
        kcal = product.get("nutriments", {}).get("energy-kcal_100g", 0) * factor
        protein = product.get("nutriments", {}).get("proteins_100g", 0) * factor
        return kcal, protein

    def add_entry(self, product, grams, kcal, protein):
        self.db.insert_entry(
            product_id=product.get("id"),
            name=product.get("product_name", "Ukendt produkt"),
            grams=grams,
            calories=kcal,
            protein=protein
        )


class View(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.controller = None
        self.build_ui()

    def set_controller(self, controller):
        self.controller = controller

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self,
            text="Kalorietæller",
            font=("Segoe UI", 22, "bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.search_entry = ctk.CTkEntry(self, placeholder_text="Søg efter produkt")
        self.search_entry.grid(row=1, column=0, padx=20, pady=(20, 10), sticky="ew")

        self.search_button = ctk.CTkButton(self, text="Søg", command=self.on_search)
        self.search_button.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        self.listbox = ctk.CTkScrollableFrame(self, height=180)
        self.listbox.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")

        self.product_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 16, "bold"))
        self.product_label.grid(row=4, column=0, padx=20, pady=(10, 5))

        self.image_label = ctk.CTkLabel(self, text="")
        self.image_label.grid(row=5, column=0, pady=10)

        self.grams_entry = ctk.CTkEntry(self, placeholder_text="Gram")
        self.grams_entry.grid(row=6, column=0, padx=20, pady=5, sticky="ew")

        self.add_button = ctk.CTkButton(self, text="Tilføj", command=self.on_add)
        self.add_button.grid(row=7, column=0, padx=20, pady=10, sticky="ew")

        self.result_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 15))
        self.result_label.grid(row=8, column=0, padx=20, pady=10)

    def clear_list(self):
        for widget in self.listbox.winfo_children():
            widget.destroy()
        self.listbox.configure(height=0)

    def show_products(self, products):
        self.clear_list()
        for i, product in enumerate(products):
            name = product.get("product_name", "Ukendt produkt")
            btn = ctk.CTkButton(
                self.listbox,
                text=name,
                anchor="w",
                command=lambda i=i: self.controller.select_product(i)
            )
            self.add_product_widget(btn)

    def show_selected_product(self, name):
        self.product_label.configure(text=name)

    def show_added_result(self, kcal, protein):
        self.result_label.configure(
            text=f"{kcal:.0f} kcal  |  {protein:.1f} g protein"
        )

    def on_search(self):
        self.controller.search(self.search_entry.get())

    def on_add(self):
        self.controller.add(self.grams_entry.get())
    
    def show_product_image(self, url):
        if not url:
            self.image_label.configure(image=None, text="")
            return

        response = requests.get(url, stream=True)
        image = Image.open(response.raw).resize((160, 160))
        ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(160, 160))

        self.image_label.configure(image=ctk_image, text="")
        self.image_label.image = ctk_image

    def add_product_widget(self, widget):
        widget.pack(fill="x", pady=2)
        self.listbox.update_idletasks()
        self.listbox.yview_moveto(1.0)




class Controller:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.set_controller(self)
        self.products = []
        self.selected_product = None

    def search(self, word):
        self.products = self.model.search_product(word)
        self.view.show_products(self.products)

    def select_product(self, index):
        self.selected_product = self.products[index]
        self.view.show_selected_product(self.selected_product.get("product_name", "Ukendt produkt"))
        image_url = self.selected_product.get("image_front_small_url")
        self.view.show_product_image(image_url)
        self.view.add_product_widget

    def add(self, grams_str):
        if not self.selected_product:
            return
        grams = float(grams_str)
        kcal, protein = self.model.calc_nutrition(self.selected_product, grams)
        self.model.add_entry(self.selected_product, grams, kcal, protein)
        self.view.show_added_result(kcal, protein)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Kalorietæller")
        self.geometry("520x720")

        db = Database("data.db")
        model = Model(db)
        view = View(self)
        view.pack(fill="both", expand=True)

        Controller(model, view)


if __name__ == "__main__":
    app = App()
    app.mainloop()