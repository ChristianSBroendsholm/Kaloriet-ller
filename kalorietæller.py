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
            id INTEGER PRIMARY KEY, 
            name text NOT NULL, 
            weight INT NOT NULL, 
            calories INT NOT NULL,
            protein INT NOT NULL,
            day date NOT NULL
        );""",
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
        new_food = {"ID": product_id, "Navn": name, "Vægt": grams, "Kalorier": calories, "Protein": protein, "Dag tilføjet": date.today()}
        self.cur.execute(
            "INSERT INTO foods (id, name, weight, calories, protein, day) VALUES (?, ?, ?, ?, ?, ?)",
            (product_id, name, grams, calories, protein, date.today())
        )
        self.conn.commit()
        self.all_food.append(new_food)

        #self.conn.commit(self.all_food)
        
    
    def sum_today(self):
        daily_calories = 0
        daily_protein = 0 
        current_date = date.today()
        for food in self.all_food:
            if food["Dag tilføjet"] == current_date:
                daily_calories += food["Kalorier"]
                daily_protein += food["Protein"]
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
        calories = product["nutriments"]["energy-kcal_100g"] * factor
        protein = product["nutriments"]["proteins_100g"] * factor
        return calories, protein



class View(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.search_var = tk.StringVar()
        self.entry_grams = tk.StringVar()

        # søgefelt
        self.search_entry = ttk.Entry(self, textvariable=self.search_var)
        self.search_button = ttk.Button(self, text="Søg", command=self.on_search)

        # resultater
        self.result_list = tk.Listbox(self)

        # produktdetaljer
        self.product_label = ttk.Label(self, text="")
        self.grams_entry = ttk.Entry(self, textvariable=self.entry_grams)
        self.add_button = ttk.Button(self, text="Tilføj", command=self.on_add)

        # total
        self.total_label = ttk.Label(self, text="")
        
        self.controller = None

    def set_controller(self, controller):
        self.controller = controller

    def on_search(self):
        if self.controller:
            self.controller.search(self.search_var.get())

    def on_add(self):
        if self.controller:
            self.controller.add_amount(self.entry_grams.get())

    def show_products(self, products):
        self.result_list.delete(0, tk.END)
        for p in products:
            self.result_list.insert(tk.END, p["product_name"])

    def show_products(self, data):
        self.product_label["text"] = f"{data["name"]}"

            


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
            name=self.selected_product["product_name"],
            product_id=self.selected_product["id"],
            grams=grams,
            calories=kcal,
            protein=protein
        )

        total = self.model.get_daily_total()
        self.view.show_daily_total(total)
        

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Kalorietæller")

        # model skal oprettes med databaseforbindelse
        database = Database("data.db")
        model = Model(database)

        # view placeres i appen
        view = View(self)
        view.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # controller forbinder model og view
        controller = Controller(model, view)

        # view skal kende controlleren for events
        view.set_controller(controller)

        # gøre rammen fleksibel i vinduet
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

if __name__ == '__main__':
    app = App()
    app.mainloop()

     