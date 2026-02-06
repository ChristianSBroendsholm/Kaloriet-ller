import requests
import customtkinter as ctk
from datetime import date
import sqlite3
from PIL import Image


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


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
    
    def get_daily_totals(self):
        self.cur.execute(
            "SELECT SUM(calories), SUM(protein) FROM foods WHERE day = ?",
            (date.today().isoformat(),)
        )
        return self.cur.fetchone()



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
        nutriments = product.get("nutriments", {})

        return {
            "kcal": nutriments.get("energy-kcal_100g", 0) * factor,
            "protein": nutriments.get("proteins_100g", 0) * factor,
            "fat": nutriments.get("fat_100g", 0) * factor,
            "carbs": nutriments.get("carbohydrates_100g", 0) * factor,
        }


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

        self.facts_label = ctk.CTkLabel(self, text="", justify="left")
        self.facts_label.grid(row=5, column=0, padx=20)

        self.unit_var = ctk.StringVar(value="gram")
        
        self.gram_radio = ctk.CTkRadioButton(self, text="Gram", variable=self.unit_var, value="gram", command=self.on_unit_change)
        self.portion_radio = ctk.CTkRadioButton(self, text="Portion", variable=self.unit_var, value="portion", command=self.on_unit_change)

        self.gram_radio.grid(row=6, column=0, sticky="w", padx=40)
        self.portion_radio.grid(row=6, column=0, sticky="e", padx=40)

        self.input_entry = ctk.CTkEntry(self, placeholder_text="Gram")
        self.input_entry.grid(row=7, column=0, padx=20, pady=5, sticky="ew")

        self.add_button = ctk.CTkButton(self, text="Tilføj", command=self.on_add)
        self.add_button.grid(row=8, column=0, padx=20, pady=10, sticky="ew")

        self.result_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 15))
        self.result_label.grid(row=9, column=0, padx=20, pady=10)


    def clear_products(self):
        for widget in self.listbox.winfo_children():
            widget.destroy()

    def show_products(self, products):
        self.clear_products()
        for i, product in enumerate(products):
            name = product.get("product_name", "Ukendt produkt")
            btn = ctk.CTkButton(
                self.listbox,
                text=name,
                anchor="w",
                command=lambda i=i: self.controller.select_product(i)
            )
            btn.pack(fill="x", pady=2)

    def show_product_facts(self, product):
        nutr = product.get("nutriments", {})
        text = (
            f"Pr. 100 g\n"
            f"Kcal: {nutr.get('energy-kcal_100g', 0)}\n"
            f"Protein: {nutr.get('proteins_100g', 0)} g\n"
            f"Fedt: {nutr.get('fat_100g', 0)} g\n"
            f"Kulhydrat: {nutr.get('carbohydrates_100g', 0)} g"
        )
        self.facts_label.configure(text=text)


    def show_selected_product(self, name):
        self.product_label.configure(text=name)

    def show_added_result(self, kcal, protein):
        self.result_label.configure(
            text=f"{kcal:.0f} kcal  |  {protein:.1f} g protein"
        )

    def on_search(self):
        self.controller.search(self.search_entry.get())

    def on_add(self):
        self.controller.add(self.input_entry.get())
    
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

    def on_unit_change(self):
        unit = self.unit_var.get()
        self.input_entry.configure(placeholder_text="Gram") if unit == "gram" else self.input_entry.configure(placeholder_text="Portioner")
        self.result_label.configure(text="")
            



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
        self.view.show_product_image(self.selected_product.get("image_front_small_url"))
        self.view.show_product_facts(self.selected_product)

    def add(self, amount_str):
        if not self.selected_product:
            return

        amount = float(amount_str)
        unit = self.view.unit_var.get()

        if unit == "portion":
            s_size = self.selected_product.get("serving_size", 100).replace("g", "")
            grams = float(s_size) * amount
            print(grams)
        else:
            grams = amount

        data = self.model.calc_nutrition(self.selected_product, grams)
        self.model.add_entry(self.selected_product, grams, data["kcal"], data["protein"])

        totals = self.model.db.get_daily_totals()
        self.view.show_added_result(data["kcal"], data["protein"])
        self.view.result_label.configure(
            text=f"Tilføjet: {data['kcal']:.0f} kcal | {data['protein']:.1f} g protein\n"
                f"I dag: {totals[0]:.0f} kcal | {totals[1]:.1f} g protein"
        )


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Kalorietæller")
        self.geometry("520x960")

        db = Database("data.db")
        model = Model(db)
        view = View(self)
        view.pack(fill="both", expand=True)

        Controller(model, view)


if __name__ == "__main__":
    app = App()
    app.mainloop()
