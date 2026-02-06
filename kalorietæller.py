# https://world.openfoodfacts.org/data 

import requests
import tkinter as tk
from tkinter import ttk
from datetime import date
import sqlite3

#url = "https://world.openfoodfacts.org/data"

#response = requests.get(url)

#eksempel på search: https://world.openfoodfacts.org/cgi/search.pl?search_terms=oatmeal&search_simple=1&action=process

def search(word):
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": word,
        "search_simple": 1,
        "action": "process",
        "json": 1
    }

    r = requests.get(url, params=params)
    data = r.json()
    return data

#print(search("oatmeal"))

class Database:
    def __init__(self, name):
        sql_statements = [

        """CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            name TEXT NOT NULL,
            weight REAL NOT NULL,
            calories REAL NOT NULL,
            protein REAL NOT NULL,
            day DATE NOT NULL
        );"""  
        ]
        self.name = name
        self.conn = sqlite3.connect(self.name)
        self.cur = self.conn.cursor()
        for statement in sql_statements:
            self.cur.execute(statement)
        #sqlite3.SQLITE_CREATE_TABLE[]
        #self.create_table = "foods"
        
        #self.conn.commit()
        #self.cur.execute(self.create_table)
        self.cur.execute("SELECT * FROM foods")
        #self.conn.commit()
        self.all_food = self.cur.fetchall() 

        self.name = name
    
    def insert_entry(self, product_id, name, grams, calories, protein):
        # (id, name, weight, calories, protein, day)
        self.cur.execute(
        "INSERT INTO foods (product_id, name, weight, calories, protein, day) VALUES (?, ?, ?, ?, ?, ?)",
        (product_id, name, grams, calories, protein, date.today()))
        self.conn.commit()
        self.cur.execute("SELECT * FROM foods WHERE id = last_insert_rowid()")
        self.all_food.append(self.cur.fetchone())

        #self.conn.commit(self.all_food)
        
    
    def sum_today(self):
        daily_calories = 0
        daily_protein = 0 
        current_date = date.today().isoformat()
        for food in self.all_food:
            if food[6] == current_date:
                daily_calories += food[4]
                daily_protein += food[5]
            #if food["Dag tilføjet"] == current_date:
                #daily_calories += food["Kalorier"]
                #daily_protein += food["Protein"]
        return daily_calories, daily_protein
"""
    def add_to_file(self):

        with open(self.name, "w", encoding="utf-8", newline="") as csvfile:
            element_writer = csv.writer(csvfile)
            for element in list:
                element_writer.writerow(element.split(", "))
"""        



class Model:
    def __init__(self, database):
        self.db = database

    def search_product(self, word):
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "search_terms": word,
            "search_simple": 1,
            "action": "process",
            "json": 1
        }
        r = requests.get(url, params=params)
        data = r.json()
        return data["products"]

    def add_entry(self, product_id, name, grams, calories, protein):
        self.db.insert_entry(product_id, name, grams, calories, protein)

    def get_daily_total(self):
        return self.db.sum_today()
    
    def calc_nutrition(self, product, grams):
        factor = grams / 100
        calories = product["nutriments"].get("energy-kcal_100g", 0) * factor
        protein = product["nutriments"].get("proteins_100g", 0) * factor
        return calories, protein



class View(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.search_var = tk.StringVar()
        self.entry_grams = tk.StringVar()

        # søgefelt
        self.search_entry = ttk.Entry(self, textvariable=self.search_var)
        self.search_button = ttk.Button(self, text="Søg", command=self.on_search)
        self.search_entry.grid(row=0, column=0)
        self.search_button.grid(row=0, column=1)
        # resultater
        self.result_list = tk.Listbox(self)
        self.result_list.bind("<<ListboxSelect>>", self.on_select)
        self.result_list.grid(row=1, column=0, columnspan=2)

        # produktdetaljer
        self.product_label = ttk.Label(self, text="")
        self.grams_entry = ttk.Entry(self, textvariable=self.entry_grams)
        self.add_button = ttk.Button(self, text="Tilføj", command=self.on_add)
        self.product_label.grid(row=2, column=0, columnspan=2)
        self.grams_entry.grid(row=3, column=0)
        self.add_button.grid(row=3, column=1)

        # total
        self.total_label = ttk.Label(self, text="")
        self.total_label.grid(row=4, column=0, columnspan=2)
        
        self.controller = None

    
    def set_controller(self, controller):
        self.controller = controller
    
    def on_select(self, event):
        if not self.result_list.curselection():
            return
        index = self.result_list.curselection()[0]
        self.controller.select_product(index)

    def on_search(self):
        if self.controller:
            self.controller.search(self.search_var.get())

    def on_add(self):
        if self.controller:
            self.controller.add_amount(self.entry_grams.get())

    def show_products(self, products):
        self.result_list.delete(0, tk.END)
        for p in products:
            self.result_list.insert(tk.END, p.get("product_name", "Ukendt produkt"))

    def show_product_details(self, data):
        self.product_label["text"] = data.get("product_name", "Ukendt produkt")
    
    def show_daily_total(self, total):
        kcal, protein = total
        self.total_label["text"] = f"Kalorier: {kcal:.0f}, Protein: {protein:.1f} g"
    
    def show_added_item(self, kcal, protein):
        self.total_label["text"] = f"Kalorier: {kcal:.0f}, Protein: {protein:.1f} g"


            


class Controller:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.view.set_controller(self)
        self.selected_product = None

    def search(self, word):
        products = self.model.search_product(word)
        self.result_products = products
        self.view.show_products(products)

    def select_product(self, index):
        self.selected_product = self.result_products[index]
        self.view.show_product_details(self.selected_product)

    def add_amount(self, grams_str):
        grams = float(grams_str)
        kcal, protein = self.model.calc_nutrition(self.selected_product, grams)

        self.model.add_entry(
            product_id=self.selected_product["id"],
            name=self.selected_product.get("product_name", "Ukendt produkt"),
            grams=grams,
            calories=kcal,
            protein=protein
        )

        self.view.show_added_item(kcal, protein)
        


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Kalorietæller")

        # Model skal oprettes med databaseforbindelse
        database = Database("data.db")
        model = Model(database)

        # View placeres i appen
        view = View(self)
        view.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Controller forbinder model og view
        controller = Controller(model, view)

        # View skal kende controlleren for events
        view.set_controller(controller)

        # Gør rammen fleksibel i vinduet
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

if __name__ == '__main__':
    app = App()
    app.mainloop()
