import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import json
from kiteconnect import KiteConnect
from PIL import Image, ImageTk
import threading
import time
import requests
import os
import time
from datetime import datetime, timedelta

# p8Z4okq4L0Opn2yuKlFdQoMyvItig6IM

class StockWishlistApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Wishlist")
        self.root.geometry("800x600")

        self.credentials_list = self.load_credentials_list()  # Load credentials list from file
        self.buy_kite_instances = []
        self.sell_kite_instances = []

        # Initialize KiteConnect instances for all credentials
        for creds in self.credentials_list:
            buy_kite = KiteConnect(api_key=creds["api_key"])
            sell_kite = KiteConnect(api_key=creds["api_key"])
            buy_kite.set_access_token(creds["access_token"])
            sell_kite.set_access_token(creds["access_token"])
            self.buy_kite_instances.append(buy_kite)
            self.sell_kite_instances.append(sell_kite)


        # GUI components
        self.logo_photo = None
        self.search_entry = None
        self.suggestion_listbox = None
        self.notebook = None
        self.stock_trees = []
        self.buy_sell_frame = None
        self.quantity_label = None
        self.quantity_entry = None
        self.remove_button = None
        self.add_account_button = None  # Button to add account
        self.account_dropdown = None  # Dropdown to display added accounts

        self.result_label = None
        
        # Initialize stock prices
        self.stock_prices = {}
        self.subscribed_instruments = [[] for _ in range(10)]  # List of lists for 10 wishlists

        # Create a separate thread for real-time updates
        self.update_thread = threading.Thread(target=self.update_stock_prices_thread, daemon=True)
        self.update_thread.start()

        # Fetch all instruments from Kite API
        self.all_instruments = self.get_all_instruments()

        self.create_widgets()
        self.update_suggestions()
        
        # Load subscribed instruments from JSON files
        self.load_subscribed_instruments()

        

    def create_widgets(self):
        self.create_logo_and_text()
        self.create_new_account_entry_fields()
        self.create_wishlist_tabs()
        self.create_remove_button()
        self.create_search_bar()
        self.create_buy_sell_frame()
        
        # self.create_result_label()
        # self.create_footer()

    def create_new_account_entry_fields(self):
        # Frame for New Account Entry Fields
        new_account_frame = tk.Frame(self.root, bg="#000000")
        new_account_frame.pack(side=tk.TOP, fill=tk.X)

        self.username_label = tk.Label(new_account_frame, text="Username", fg="white", bg="#000000")
        self.username_label.pack(side=tk.LEFT, padx=5, pady=5)

        self.username_entry = tk.Entry(new_account_frame, width=30)
        self.username_entry.pack(side=tk.LEFT, padx=5, pady=5)

        self.api_key_label = tk.Label(new_account_frame, text="API Key", fg="white", bg="#000000")
        self.api_key_label.pack(side=tk.LEFT, padx=5, pady=5)

        self.api_key_entry = tk.Entry(new_account_frame, width=30)
        self.api_key_entry.pack(side=tk.LEFT, padx=5, pady=5)

        self.api_secret_label = tk.Label(new_account_frame, text="API Secret", fg="white", bg="#000000")
        self.api_secret_label.pack(side=tk.LEFT, padx=5, pady=5)

        self.api_secret_entry = tk.Entry(new_account_frame, width=30)
        self.api_secret_entry.pack(side=tk.LEFT, padx=5, pady=5)

        self.access_token_label = tk.Label(new_account_frame, text="Access Token", fg="white", bg="#000000")
        self.access_token_label.pack(side=tk.LEFT, padx=5, pady=5)

        self.access_token_entry = tk.Entry(new_account_frame, width=30)
        self.access_token_entry.pack(side=tk.LEFT, padx=5, pady=5)

        self.add_account_button = tk.Button(new_account_frame, text="Add New Account", command=self.add_new_account)
        self.add_account_button.pack(side=tk.LEFT, padx=5, pady=10)

        # Button to change access token
        self.change_access_token_button = tk.Button(new_account_frame, text="Change Access Token", command=self.change_access_token)
        self.change_access_token_button.pack(side=tk.LEFT, padx=5, pady=10)

        # Dropdown to display added account usernames and funds
        self.account_dropdown = ttk.Combobox(new_account_frame, values=self.get_account_usernames(), width=40)
        self.account_dropdown.pack(side=tk.LEFT, padx=5, pady=10)


    def get_account_usernames(self):
        return [f"{creds['username']} (Funds: {creds['funds']})" for creds in self.credentials_list]

    def fetch_funds(self, credentials):
        try:
            kite = KiteConnect(api_key=credentials["api_key"])
            kite.set_access_token(credentials["access_token"])
            funds = kite.margins()["equity"]["available"]["live_balance"]
            return funds
        except Exception as e:
            print(f"Error fetching funds for {credentials['username']}: {e}")
            return 0




    def update_dropdown(self):
        self.account_dropdown['menu'].delete(0, 'end')
        account_usernames = self.get_account_usernames()
        for username in account_usernames:
            self.account_dropdown['menu'].add_command(label=username, command=tk._setit(self.selected_account, username))
        self.selected_account.set(account_usernames[0] if account_usernames else "")

    
    def display_access_token_dialog(self, username, current_access_token):
        dialog = tk.Toplevel(self.root)
        dialog.title("Change Access Token")

        tk.Label(dialog, text="Username:").grid(row=0, column=0, padx=10, pady=10)
        username_label = tk.Label(dialog, text=username)
        username_label.grid(row=0, column=1, padx=10, pady=10)

        tk.Label(dialog, text="Access Token:").grid(row=1, column=0, padx=10, pady=10)
        access_token_entry = tk.Entry(dialog, width=30)
        access_token_entry.grid(row=1, column=1, padx=10, pady=10)
        access_token_entry.insert(0, current_access_token)

        def save_access_token():
            new_access_token = access_token_entry.get().strip()
            if new_access_token:
                self.update_access_token(username, new_access_token)
                dialog.destroy()

        save_button = tk.Button(dialog, text="Save", command=save_access_token)
        save_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

    def change_access_token(self):
        selected_username = self.account_dropdown.get()
        new_access_token = simpledialog.askstring("Change Access Token", f"Enter new access token for {selected_username}:")

        if new_access_token:
            for creds in self.credentials_list:
                if creds["username"] == selected_username:
                    creds["access_token"] = new_access_token
                    self.save_credentials_list(self.credentials_list)
                    messagebox.showinfo("Access Token Updated", f"Access token updated successfully for {selected_username}.")
                    break

    
    def change_access_token(self):
        selected_account = self.account_dropdown.get().split(" - ")[0]
        for creds in self.credentials_list:
            if creds["username"] == selected_account:
                self.display_access_token_dialog(creds["username"], creds["access_token"])
                break

    
    def update_access_token(self, username, new_access_token):
        for creds in self.credentials_list:
            if creds["username"] == username:
                creds["access_token"] = new_access_token
                self.save_credentials_list(self.credentials_list)
                messagebox.showinfo("Access Token Updated", f"Access token updated successfully for {username}.")
                break


    def get_account_usernames_with_funds(self):
        account_info = []
        for creds, buy_kite in zip(self.credentials_list, self.buy_kite_instances):
            try:
                balance = buy_kite.margins()["equity"]["available"]["cash"]
                account_info.append(f"{creds['username']} - Funds: {balance}")
            except Exception as e:
                print(f"Error fetching balance for {creds['username']}: {e}")
        return account_info


    def add_new_account(self):
        username = self.username_entry.get().strip()
        api_key = self.api_key_entry.get().strip()
        api_secret = self.api_secret_entry.get().strip()
        access_token = self.access_token_entry.get().strip()

        if username and api_key and api_secret and access_token:
            new_credentials = {
                "username": username,
                "api_key": api_key,
                "api_secret": api_secret,
                "access_token": access_token
            }
            self.credentials_list.append(new_credentials)
            self.save_credentials_list(self.credentials_list)
            self.initialize_kite_connect(new_credentials)
            self.update_suggestions()

            # Update KiteConnect instances for buying and selling with new credentials
            buy_kite = KiteConnect(api_key=new_credentials["api_key"])
            sell_kite = KiteConnect(api_key=new_credentials["api_key"])

            # Set access tokens
            buy_kite.set_access_token(new_credentials["access_token"])
            sell_kite.set_access_token(new_credentials["access_token"])

            # Append to the list of KiteConnect instances
            self.buy_kite_instances.append(buy_kite)
            self.sell_kite_instances.append(sell_kite)

            # Clear the textboxes after adding the account
            self.username_entry.delete(0, tk.END)
            self.api_key_entry.delete(0, tk.END)
            self.api_secret_entry.delete(0, tk.END)
            self.access_token_entry.delete(0, tk.END)

            # Update the dropdown menu with the new username
            self.account_dropdown['values'] = self.get_account_usernames()

            messagebox.showinfo("Account Added", "New account credentials added successfully.")
        else:
            messagebox.showinfo("Error", "Please fill in all fields.")

    def get_account_usernames(self):
        accounts_with_funds = []
        for creds in self.credentials_list:
            funds = self.fetch_funds(creds)
            accounts_with_funds.append(f"{creds['username']} - Funds: {funds}")
        return accounts_with_funds


    # def create_footer(self):
    #         # Create a frame for the footer
    #         footer_frame = tk.Frame(self.root, bg="black", height=30)
    #         footer_frame.pack(side=tk.BOTTOM, fill=tk.X)

    #         # Add content to the footer frame
    #         footer_label = tk.Label(footer_frame, text="© 2024 BlauStocks. All rights reserved.", font=('Helvetica', 12), fg="white", bg="black")
    #         footer_label.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)

    def add_existing_account(self):
        if self.credentials:
            access_token = simpledialog.askstring("Access Token", "Please enter your access token:")
            if access_token:
                self.credentials["access_token"] = access_token
                self.save_credentials(self.credentials)
                self.initialize_kite_connect(self.credentials)
                self.update_suggestions()  # Update suggestions after adding an existing account
        else:
            messagebox.showinfo("Error", "No existing account found. Please add a new account.")

    def initialize_kite_connect(self, credentials):
        # Initialize KiteConnect instances for buying and selling
        self.buy_kite = KiteConnect(api_key=credentials["api_key"])
        self.sell_kite = KiteConnect(api_key=credentials["api_key"])

        # Set access tokens
        self.buy_kite.set_access_token(credentials["access_token"])
        self.sell_kite.set_access_token(credentials["access_token"])

        messagebox.showinfo("Account Added", "Account credentials added successfully. Application is now ready to use.")

    def create_logo_and_text(self):
        # Load logo image
        logo_image = Image.open("logo.jpg").resize((150, 70), Image.ANTIALIAS if hasattr(Image, 'ANTIALIAS') else Image.BICUBIC)
        self.logo_photo = ImageTk.PhotoImage(logo_image)

        # Create a frame for the title
        title_frame = tk.Frame(self.root, bg="#3498db")
        title_frame.pack(side=tk.TOP, fill=tk.X)

        # Title label
        title_label = tk.Label(title_frame, text="BLAUSTOCKS", font=('Consolas', 20, 'bold'), fg="white", bg="#3498db")
        title_label.grid(row=0, column=0, padx=20, pady=10)

        # Logo labelvh
        logo_label = tk.Label(title_frame, image=self.logo_photo, bg="#17202A", font=('Consolas', 85, 'bold'))
        logo_label.grid(row=0, column=1, padx=1150, pady=10)

        ## footer part##

    def create_search_bar(self):
        search_frame = ttk.Frame(self.root)
        search_frame.pack(side=tk.LEFT, padx=10, pady=80, anchor='n')

        self.search_entry = ttk.Entry(search_frame, font=('Consolas', 12))
        self.search_entry.pack(side=tk.TOP, padx=0, pady=0)

        self.suggestion_listbox = tk.Listbox(search_frame, font=('Consolas', 12), height=15, width=35)
        # Initially hide the suggestion listbox
        self.suggestion_listbox.pack_forget()

        self.search_entry.bind('<KeyRelease>', self.update_suggestions)
        self.suggestion_listbox.bind('<<ListboxSelect>>', self.add_to_wishlist)

    def create_wishlist_tabs(self):
        left_frame = ttk.Frame(self.root)
        left_frame.pack(side=tk.LEFT, padx=30, pady=30, anchor='nw')  # Adjusted anchor to northwest

        self.notebook = ttk.Notebook(left_frame, width=600, height=500)  # Adjust the width and height as needed
        self.notebook.pack(side=tk.TOP, padx=0, pady=0)  # Expanded to occupy all available space

        for i in range(10):
            wishlist_tab = ttk.Frame(self.notebook)
            self.notebook.add(wishlist_tab, text=f"WISHLIST {i + 1}".upper(), padding=10)  # Convert text to uppercase
            # Adjust padding as needed

            columns = ("Stock", "Price")
            stock_tree = ttk.Treeview(wishlist_tab, columns=columns, show="headings", height=6)  # Adjusted height to 5
            stock_tree.heading("Stock", text="Stock")
            stock_tree.heading("Price", text="Price")
            stock_tree.pack(side=tk.TOP, padx=0, pady=0, fill=tk.BOTH, expand=True)  # Expanded to occupy all available space
            # stock_tree.bind('<Double-1>', self.show_wishlist_options)
            self.stock_trees.append(stock_tree)

        # Add note below the tabs
        note_label = ttk.Label(left_frame, text="Note: Only 10 instruments can be added to each wishlist.", font=('Consolas', 10, 'italic'))
        note_label.pack(side=tk.TOP, padx=0, pady=10)


    def create_remove_button(self):
            left_frame = ttk.Frame(self.root)
            left_frame.pack(side=tk.BOTTOM, padx=80, pady=10, anchor='sw') 
            self.remove_button = ttk.Button(left_frame, text="Remove", command=self.remove_from_wishlist)
            self.remove_button.pack(side=tk.LEFT, padx=80, pady=50) # Pack it at the top side




            
    def create_buy_sell_frame(self):
        # Create the main frame for buying/selling
        self.buy_sell_frame = ttk.Frame(self.root)
        self.buy_sell_frame.pack(side=tk.LEFT, padx=10, pady=10, anchor='nw')  # Adjust padding and alignment as needed

        # Quantity Label and Entry
        self.quantity_label = ttk.Label(self.buy_sell_frame, text="Quantity:", font=('Consolas', 12))
        self.quantity_label.pack(anchor='w', padx=5, pady=5)
        
        self.quantity_entry = ttk.Entry(self.buy_sell_frame, font=('Consolas', 12))
        self.quantity_entry.pack(anchor='w', padx=5, pady=5)

        # Create a frame for market/limit price selection
        self.price_frame = ttk.Frame(self.buy_sell_frame)
        self.price_frame.pack(anchor='w', padx=5, pady=5)

        # Market Price Checkbox
        self.market_price_var = tk.BooleanVar(value=True)  # Default to market price
        self.market_price_checkbox = ttk.Checkbutton(self.price_frame, text="Market Price", variable=self.market_price_var, command=self.toggle_price_entry)
        self.market_price_checkbox.pack(side=tk.LEFT, padx=5)

        # Limit Price Label and Entry
        self.limit_price_label = ttk.Label(self.price_frame, text="Limit Price:", font=('Consolas', 12))
        self.limit_price_entry = ttk.Entry(self.price_frame, font=('Consolas', 12))
        
        # Initially hide the limit price entry
        self.limit_price_label.pack_forget()
        self.limit_price_entry.pack_forget()

        # Buy and Sell Buttons
        self.buy_button = ttk.Button(self.buy_sell_frame, text="Buy", command=self.buy_stock)
        self.buy_button.pack(side=tk.LEFT, padx=5, pady=10)
        
        self.sell_button = ttk.Button(self.buy_sell_frame, text="Sell", command=self.sell_stock)
        self.sell_button.pack(side=tk.LEFT, padx=5, pady=10)

    def toggle_price_entry(self):
        # Toggle the visibility of the limit price entry based on the checkbox state
        if self.market_price_var.get():
            self.limit_price_label.pack_forget()
            self.limit_price_entry.pack_forget()
        else:
            self.limit_price_label.pack(side=tk.LEFT, padx=5, pady=5)
            self.limit_price_entry.pack(side=tk.LEFT, padx=5, pady=5)


    def update_suggestions(self, event=None):
        query = self.search_entry.get().strip().upper()
        self.suggestion_listbox.delete(0, tk.END)

        if query:
            suggestions = [instrument["tradingsymbol"] for instrument in self.all_instruments if query in instrument["tradingsymbol"]]
            for suggestion in suggestions:
                self.suggestion_listbox.insert(tk.END, suggestion)
            self.suggestion_listbox.pack(side=tk.TOP, padx=0, pady=0)  # Show the listbox
        else:
            self.suggestion_listbox.pack_forget()  # Hide the listbox if no query

    def add_to_wishlist(self, event):
        selected_stock = self.suggestion_listbox.get(tk.ACTIVE)
        current_tab = self.notebook.index(self.notebook.select())

        if selected_stock:
            tree = self.stock_trees[current_tab]
            if not any(tree.item(item)["values"][0] == selected_stock for item in tree.get_children()):
                tree.insert("", tk.END, values=(selected_stock, "0.00"))
                self.subscribed_instruments[current_tab].append(selected_stock)
                self.save_subscribed_instruments()

    def remove_from_wishlist(self):
        current_tab = self.notebook.index(self.notebook.select())
        tree = self.stock_trees[current_tab]

        selected_item = tree.selection()
        if selected_item:
            stock = tree.item(selected_item[0])["values"][0]
            self.subscribed_instruments[current_tab].remove(stock)
            tree.delete(selected_item)
            self.save_subscribed_instruments()

    def get_all_instruments(self):
        url = "https://api.kite.trade/instruments"
        url = "https://api.kite.trade/instruments?exchange=NFO"
        response = requests.get(url)
        data = response.text.splitlines()

        headers = data[0].split(",")
        instruments = []

        for row in data[1:]:
            values = row.split(",")
            instrument = {headers[i]: values[i] for i in range(len(headers))}
            instruments.append(instrument)

        return instruments

    def update_stock_prices_thread(self):
        while True:
            for i in range(10):
                subscribed_instruments = self.subscribed_instruments[i]
                if subscribed_instruments:
                    for stock in subscribed_instruments:
                        ltp = self.get_ltp(stock)
                        self.update_stock_price(i, stock, ltp)

            time.sleep(1)

    def get_ltp(self, stock):
        try:
            url = f"https://api.kite.trade/quote?i=NSE:{stock}"
            # url = f"https://api.kite.trade/quote?i=NFO:{stock}"
            headers = {
                "X-Kite-Version": "3",
                "Authorization": f"token {self.credentials_list[0]['api_key']}:{self.credentials_list[0]['access_token']}"
            }
            response = requests.get(url, headers=headers)
            data = response.json()
            return data["data"][f"NSE:{stock}"]["last_price"]
        except Exception as e:
            print(f"Error fetching LTP for {stock}: {e}")
            return "0.00"

    def update_stock_price(self, tab_index, stock, ltp):
        tree = self.stock_trees[tab_index]

        for item in tree.get_children():
            if tree.item(item)["values"][0] == stock:
                tree.item(item, values=(stock, ltp))
                break

    def buy_stock(self):
        self.select_account_dialog()
        stock_symbol = self.get_selected_stock()
        quantity = self.quantity_entry.get()
        limit_price = None

        if not stock_symbol:
            messagebox.showinfo("Error", "Please select a stock from the list.")
            return

        if not quantity.isdigit():
            messagebox.showinfo("Error", "Please enter a valid quantity.")
            return

        quantity = int(quantity)

        if not self.market_price_var.get():  # If the market price checkbox is not selected
            limit_price_entry = self.limit_price_entry.get()
            if not limit_price_entry:
                messagebox.showinfo("Error", "Please enter a limit price.")
                return
            try:
                limit_price = float(limit_price_entry)
            except ValueError:
                messagebox.showinfo("Error", "Invalid limit price. Please enter a number.")
                return

        for account in self.selected_accounts:
            try:
                # Place the order
                order_id = self.buy_stock_for_account(account, stock_symbol, quantity, "regular", limit_price)
                messagebox.showinfo("Success", f"Successfully bought {quantity} of {stock_symbol} for account {account}. Order ID: {order_id}")
                # Start monitoring the order
                self.monitor_order(account, order_id)
            except Exception as e:
                messagebox.showerror("Error", f"Error buying stock for account {account}: {e}")

        self.search_entry.delete(0, tk.END)

    def sell_stock(self):
        self.select_account_dialog()
        stock_symbol = self.get_selected_stock()
        quantity = self.quantity_entry.get()
        limit_price = None

        if not stock_symbol:
            messagebox.showinfo("Error", "Please select a stock from the list.")
            return

        if not quantity.isdigit():
            messagebox.showinfo("Error", "Please enter a valid quantity.")
            return

        quantity = int(quantity)

        if not self.market_price_var.get():  # If the market price checkbox is not selected
            limit_price_entry = self.limit_price_entry.get()
            if not limit_price_entry:
                messagebox.showinfo("Error", "Please enter a limit price.")
                return
            try:
                limit_price = float(limit_price_entry)
            except ValueError:
                messagebox.showinfo("Error", "Invalid limit price. Please enter a number.")
                return

        for account in self.selected_accounts:
            try:
                # Place the order
                order_id = self.sell_stock_for_account(account, stock_symbol, quantity, "regular", limit_price)
                messagebox.showinfo("Success", f"Successfully sold {quantity} of {stock_symbol} for account {account}. Order ID: {order_id}")
                # Start monitoring the order
                self.monitor_order(account, order_id)
            except Exception as e:
                messagebox.showerror("Error", f"Error selling stock for account {account}: {e}")

        self.search_entry.delete(0, tk.END)

    def buy_stock_for_account(self, account_username, stock_symbol, quantity, variety, limit_price=None):
        kite = self.get_kite_instance_for_account(account_username)
        if kite:
            try:
                # Determine the order type and price
                order_type = "LIMIT" if limit_price else "MARKET"
                order_params = {
                    "exchange": "NSE",
                    "tradingsymbol": stock_symbol,
                    "transaction_type": "BUY",
                    "quantity": quantity,
                    "order_type": order_type,
                    "product": "MIS",
                    "variety": variety
                }
                if limit_price is not None:
                    order_params["price"] = limit_price

                # Place the order
                order_id = kite.place_order(**order_params)
                return order_id
            except Exception as e:
                raise Exception(f"Error placing buy order for account {account_username}: {e}")
        else:
            raise Exception(f"No KiteConnect instance found for account username '{account_username}'.")

    def sell_stock_for_account(self, account_username, stock_symbol, quantity, variety, limit_price=None):
        kite = self.get_kite_instance_for_account(account_username)
        if kite:
            try:
                # Determine the order type and price
                order_type = "LIMIT" if limit_price else "MARKET"
                order_params = {
                    "exchange": "NSE",
                    "tradingsymbol": stock_symbol,
                    "transaction_type": "SELL",
                    "quantity": quantity,
                    "order_type": order_type,
                    "product": "MIS",
                    "variety": variety
                }
                if limit_price is not None:
                    order_params["price"] = limit_price

                # Place the order
                order_id = kite.place_order(**order_params)
                return order_id
            except Exception as e:
                raise Exception(f"Error placing sell order for account {account_username}: {e}")
        else:
            raise Exception(f"No KiteConnect instance found for account username '{account_username}'.")

    def monitor_order(self, account_username, order_id):
        kite = self.get_kite_instance_for_account(account_username)
        if kite:
            start_time = datetime.now()
            timeout = timedelta(minutes=5)  # Set the timeout period here

            while datetime.now() - start_time < timeout:
                try:
                    order = kite.order_history(order_id)
                    if order and order[0]['status'] == 'COMPLETE':
                        return  # Order completed successfully
                    time.sleep(10)  # Check every 10 seconds
                except Exception as e:
                    print(f"Error checking order status for account {account_username}: {e}")

            # Cancel the order if not completed
            try:
                kite.cancel_order(order_id)
                messagebox.showinfo("Order Cancelled", f"Order {order_id} has been cancelled after timeout.")
            except Exception as e:
                messagebox.showerror("Error", f"Error cancelling order {order_id} for account {account_username}: {e}")
        else:
            raise Exception(f"No KiteConnect instance found for account username '{account_username}'.")
    
    def get_kite_instance_for_account(self, account_username):
        for creds in self.credentials_list:
            if creds["username"] == account_username:
                # Assuming buy_kite_instances and credentials_list are aligned by index
                index = self.credentials_list.index(creds)
                if index < len(self.buy_kite_instances):
                    return self.buy_kite_instances[index]
                else:
                    return None
        return None





    def select_account_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Accounts")

        tk.Label(dialog, text="Select accounts for the transaction:").pack(padx=10, pady=10)

        self.selected_accounts = []

        for i, creds in enumerate(self.credentials_list):
            var = tk.BooleanVar()
            chk = tk.Checkbutton(dialog, text=creds["username"], variable=var)
            chk.pack(anchor="w", padx=20)
            self.selected_accounts.append((creds["username"], var))

        def on_select():
            selected = [username for username, var in self.selected_accounts if var.get()]
            self.selected_accounts = selected
            dialog.destroy()

        select_button = tk.Button(dialog, text="Select", command=on_select)
        select_button.pack(pady=10)

        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

        return self.selected_accounts




    def get_selected_stock(self):
        current_tab = self.notebook.index(self.notebook.select())
        tree = self.stock_trees[current_tab]
        selected_item = tree.selection()

        if selected_item:
            return tree.item(selected_item[0])["values"][0]
        return None

    def save_credentials_list(self, credentials_list):
        with open("credentials_list.json", "w") as file:
            json.dump(credentials_list, file)

    def load_credentials_list(self):
        try:
            with open("credentials_list.json", "r") as file:
                return json.load(file)
        except FileNotFoundError:
            return []

    def save_subscribed_instruments(self):
        for i in range(10):
            filename = f"wishlist_{i + 1}.json"
            with open(filename, "w") as file:
                json.dump(self.subscribed_instruments[i], file)

    def load_subscribed_instruments(self):
        for i in range(10):
            filename = f"wishlist_{i + 1}.json"
            try:
                with open(filename, "r") as file:
                    self.subscribed_instruments[i] = json.load(file)
                    for stock in self.subscribed_instruments[i]:
                        self.stock_trees[i].insert("", tk.END, values=(stock, "0.00"))
            except FileNotFoundError:
                self.subscribed_instruments[i] = []

if __name__ == "__main__":
    root = tk.Tk()
    app = StockWishlistApp(root)
    root.mainloop()
    