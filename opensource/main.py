from tkinter import *
from tkinter import ttk, messagebox, scrolledtext, filedialog
import socket
import threading
import json
import os
from datetime import datetime
import sys

class Server:
    def __init__(self, host='0.0.0.0', port=10000):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}
        self.running = False

    def start(self):
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        self.running = True
        print(f"Сервер запущен на {self.host}:{self.port}")

    def accept_connection(self):
        if not self.running:
            return None
        client_socket, addr = self.socket.accept()
        return client_socket, addr

    def receive_message(self, client_socket):
        try:
            data = client_socket.recv(1024).decode('utf-8')
            return data if data else None
        except:
            return None

    def broadcast_message(self, message, exclude=None):
        for client_socket in list(self.clients.keys()):
            if client_socket != exclude:
                try:
                    client_socket.send(message.encode('utf-8'))
                except:
                    self.remove_client(client_socket)

    def remove_client(self, client_socket):
        if client_socket in self.clients:
            username = self.clients[client_socket]
            del self.clients[client_socket]
            print(f"Клиент {username} отключен")

    def stop(self):
        self.running = False
        for client_socket in list(self.clients.keys()):
            client_socket.close()
        self.socket.close()
        print("Сервер остановлен")

class Client:
    def __init__(self, host='127.0.0.1', port=10000):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.socket.connect((self.host, self.port))

    def send_message(self, message):
        self.socket.send(message.encode('utf-8'))

    def receive_message(self):
        try:
            data = self.socket.recv(1024).decode('utf-8')
            return data if data else None
        except:
            return None

    def disconnect(self):
        self.socket.close()

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FlowerHand")
        self.root.geometry("800x600")
        
        # Загрузка ника из файла
        self.nickname = self.load_nickname() or ("User" + str(int(datetime.now().timestamp()))[-4:])
        self.username = self.nickname

        self.chat_history = []
        self.history_file = "chat_history.json"
        
        self.api_names = {
            "26.22.97.228": "Рок-клуб",
            "localhost": "Локальный сервер",
            "127.0.0.1": "Локальный сервер"
        }
        
        self.load_history()
        self.setup_mode_selection()

    def load_nickname(self):
        if os.path.exists("nickname.json"):
            try:
                with open("nickname.json", 'r') as f:
                    data = json.load(f)
                    return data.get("nickname", "")
            except:
                return ""
        return ""

    def save_nickname(self, nickname):
        with open("nickname.json", 'w') as f:
            json.dump({"nickname": nickname}, f)

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    self.chat_history = json.load(f)
            except:
                self.chat_history = []

    def save_history(self):
        with open(self.history_file, 'w') as f:
            json.dump(self.chat_history, f, indent=2)

    def setup_mode_selection(self):
        self.clear_window()
        
        main_frame = Frame(self.root)
        main_frame.pack(expand=True, fill=BOTH, padx=20, pady=20)
        
        Label(main_frame, text="Выберите режим работы", font=('Arial', 14)).pack(pady=20)
        
        user_frame = Frame(main_frame)
        user_frame.pack(pady=10)
        
        Label(user_frame, text="Ваш никнейм:").pack(side=LEFT)
        self.username_entry = Entry(user_frame, width=20)
        self.username_entry.pack(side=LEFT, padx=5)
        self.username_entry.insert(0, self.username)
        
        btn_frame = Frame(main_frame)
        btn_frame.pack(pady=20)
        
        Button(btn_frame, text="Сервер", command=self.setup_server, width=15).pack(side=LEFT, padx=10)
        Button(btn_frame, text="Клиент", command=self.setup_client, width=15).pack(side=LEFT, padx=10)
        
        Button(main_frame, text="Просмотреть историю", command=self.show_history).pack(pady=20)

    def setup_server(self):
        self.username = self.username_entry.get().strip() or self.username
        self.save_nickname(self.username)  # сохраняем ник
        self.clear_window()
        self.root.title(f"FlowerHand - Server Mode ({self.username})")
        
        self.server = Server()
        self.server_thread = threading.Thread(target=self.run_server, daemon=True)
        self.server_thread.start()
        
        info_frame = Frame(self.root)
        info_frame.pack(fill=X, padx=10, pady=5)
        Label(info_frame, text=f"Сервер запущен | Ник: {self.username}", font=('Arial', 12)).pack(side=LEFT)
        
        clients_frame = Frame(self.root)
        clients_frame.pack(fill=X, padx=10, pady=5)
        Label(clients_frame, text="Подключенные клиенты:").pack(side=LEFT)
        self.clients_listbox = Listbox(clients_frame, height=4)
        self.clients_listbox.pack(side=LEFT, fill=X, expand=True, padx=5)
        
        self.log_area = scrolledtext.ScrolledText(self.root, wrap=WORD, width=80, height=20)
        self.log_area.pack(expand=True, fill=BOTH, padx=10, pady=5)
        self.log_message(f">>> Сервер запущен. Никнейм: {self.username}")
        self.log_area.config(state=DISABLED)
        
        msg_frame = Frame(self.root)
        msg_frame.pack(fill=X, padx=10, pady=5)
        self.server_msg_entry = Entry(msg_frame)
        self.server_msg_entry.pack(side=LEFT, fill=X, expand=True, padx=5)
        self.server_msg_entry.bind("<Return>", lambda e: self.broadcast_message())
        Button(msg_frame, text="Отправить всем", command=self.broadcast_message).pack(side=LEFT)
        
        ctrl_frame = Frame(self.root)
        ctrl_frame.pack(pady=5)
        Button(ctrl_frame, text="Остановить сервер", command=self.stop_server).pack(side=LEFT, padx=5)
        Button(ctrl_frame, text="История", command=self.show_history).pack(side=LEFT, padx=5)
        
        self.root.protocol("WM_DELETE_WINDOW", self.stop_server)

    def run_server(self):
        self.server.start()
        while True:
            try:
                client_socket, addr = self.server.accept_connection()
                if client_socket:
                    threading.Thread(
                        target=self.handle_client,
                        args=(client_socket,),
                        daemon=True
                    ).start()
            except Exception as e:
                self.log_message(f"Ошибка сервера: {str(e)}")
                break

    def handle_client(self, client_socket):
        while True:
            try:
                message = self.server.receive_message(client_socket)
                if not message:
                    break
                    
                if message.startswith("USERNAME:"):
                    username = message.split(":", 1)[1].strip()
                    self.server.clients[client_socket] = username
                    self.update_clients_list()
                    self.log_message(f">>> {username} присоединился к чату")
                else:
                    username = self.server.clients.get(client_socket, "Unknown")
                    timestamp = datetime.now().timestamp()
                    self.chat_history.append({
                        'timestamp': timestamp,
                        'username': username,
                        'message': message,
                        'type': 'received'
                    })
                    self.save_history()
                    self.log_message(f"{username}: {message}")
                    self.server.broadcast_message(f"{username}: {message}", exclude=client_socket)
                    
            except Exception as e:
                break
                
        username = self.server.clients.get(client_socket, "Unknown")
        self.log_message(f">>> {username} покинул чат")
        self.server.remove_client(client_socket)
        self.update_clients_list()
        client_socket.close()

    def update_clients_list(self):
        self.clients_listbox.delete(0, END)
        for username in self.server.clients.values():
            self.clients_listbox.insert(END, username)

    def broadcast_message(self):
        message = self.server_msg_entry.get().strip()
        if not message:
            return
        
        timestamp = datetime.now().timestamp()
        self.chat_history.append({
            'timestamp': timestamp,
            'username': self.username,
            'message': message,
            'type': 'broadcast'
        })
        self.save_history()
        
        self.log_message(f"Вы (всем): {message}")
        self.server_msg_entry.delete(0, END)
        self.server.broadcast_message(f"{self.username}: {message}")

    def setup_client(self):
        self.username = self.username_entry.get().strip() or self.username
        self.save_nickname(self.username)  # сохраняем ник
        self.clear_window()
        self.root.title(f"FlowerHand - Client Mode ({self.username})")
        
        conn_frame = Frame(self.root)
        conn_frame.pack(fill=X, padx=10, pady=5)
        Label(conn_frame, text="Адрес сервера:").pack(side=LEFT)
        
        self.server_combobox = ttk.Combobox(conn_frame, width=20)
        self.server_combobox['values'] = list(self.api_names.values()) + ["Другой..."]
        self.server_combobox.pack(side=LEFT, padx=5)
        self.server_combobox.set("Рок-клуб")
        
        self.custom_ip_entry = Entry(conn_frame, width=15)
        self.custom_ip_entry.pack(side=LEFT, padx=5)
        self.custom_ip_entry.insert(0, "192.168.0.107")
        self.custom_ip_entry.pack_forget()
        
        def on_server_select(event):
            if self.server_combobox.get() == "Другой...":
                self.custom_ip_entry.pack(side=LEFT, padx=5)
            else:
                self.custom_ip_entry.pack_forget()
        
        self.server_combobox.bind("<<ComboboxSelected>>", on_server_select)
        
        Button(conn_frame, text="Подключиться", command=self.connect_to_server).pack(side=LEFT, padx=5)
        Label(conn_frame, text=f"Ник: {self.username}").pack(side=RIGHT)
        
        self.chat_area = scrolledtext.ScrolledText(self.root, wrap=WORD, width=80, height=20)
        self.chat_area.pack(expand=True, fill=BOTH, padx=10, pady=5)
        self.chat_area.config(state=DISABLED)
        
        msg_frame = Frame(self.root)
        msg_frame.pack(fill=X, padx=10, pady=5)
        self.message_entry = Entry(msg_frame)
        self.message_entry.pack(side=LEFT, fill=X, expand=True, padx=5)
        self.message_entry.bind("<Return>", lambda e: self.send_message())
        Button(msg_frame, text="Отправить", command=self.send_message).pack(side=LEFT)
        
        ctrl_frame = Frame(self.root)
        ctrl_frame.pack(pady=5)
        Button(ctrl_frame, text="Отключиться", command=self.disconnect_client).pack(side=LEFT, padx=5)
        Button(ctrl_frame, text="История", command=self.show_history).pack(side=LEFT, padx=5)
        
        self.client = None
        self.connected = False
        self.server_ip = None
        self.server_display_name = None

    def connect_to_server(self):
        selected_server = self.server_combobox.get()
        
        if selected_server == "Другой...":
            host = self.custom_ip_entry.get().strip()
            display_name = host
        else:
            host = next((ip for ip, name in self.api_names.items() if name == selected_server), selected_server)
            display_name = selected_server
        
        if not host:
            messagebox.showerror("Ошибка", "Введите адрес сервера")
            return
        
        try:
            self.client = Client(host, 10000)
            self.client.connect()
            self.client.send_message(f"USERNAME:{self.username}")
            
            self.connected = True
            self.server_ip = host
            self.server_display_name = display_name
            self.update_chat(f">>> Подключено к серверу '{display_name}' как {self.username}\n")
            
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Ошибка подключения", f"Не удалось подключиться к {display_name}: {str(e)}")

    def send_message(self):
        if not self.connected or not self.client:
            messagebox.showwarning("Ошибка", "Нет подключения к серверу")
            return
        
        message = self.message_entry.get().strip()
        if not message:
            return
        
        timestamp = datetime.now().timestamp()
        self.chat_history.append({
            'timestamp': timestamp,
            'username': self.username,
            'message': message,
            'type': 'sent',
            'server': self.server_display_name
        })
        self.save_history()
        
        try:
            self.client.send_message(message)
            self.update_chat(f"Вы: {message}\n")
            self.message_entry.delete(0, END)
        except Exception as e:
            self.update_chat(f"❗ Ошибка отправки: {str(e)}\n")
            self.connected = False

    def receive_messages(self):
        while self.connected and self.client:
            try:
                response = self.client.receive_message()
                if not response:
                    break
                    
                if ":" in response:
                    username, msg = response.split(":", 1)
                    username = username.strip()
                    msg = msg.strip()
                else:
                    username = "Сервер"
                    msg = response
                
                timestamp = datetime.now().timestamp()
                self.chat_history.append({
                    'timestamp': timestamp,
                    'username': username,
                    'message': msg,
                    'type': 'received',
                    'server': self.server_display_name
                })
                self.save_history()
                self.update_chat(f"{username}: {msg}\n")
                
            except ConnectionError as e:
                self.update_chat(f"❗ Соединение с сервером '{self.server_display_name}' потеряно: {str(e)}\n")
                self.connected = False
                break
            except Exception as e:
                self.update_chat(f"❗ Ошибка получения: {str(e)}\n")
                self.connected = False
                break

    def disconnect_client(self):
        if self.client:
            try:
                self.client.disconnect()
            except:
                pass
        self.connected = False
        self.update_chat(f">>> Отключено от сервера '{self.server_display_name}'\n")

    def show_history(self):
        history_win = Toplevel(self.root)
        history_win.title("История переписки")
        history_win.geometry("600x400")
        
        history_text = scrolledtext.ScrolledText(history_win, wrap=WORD, width=70, height=20)
        history_text.pack(expand=True, fill=BOTH, padx=10, pady=10)
        
        if not self.chat_history:
            history_text.insert(END, "История переписки пуста\n")
        else:
            for message in self.chat_history:
                timestamp = datetime.fromtimestamp(message['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                history_text.insert(END, f"[{timestamp}] {message['username']}: {message['message']}\n")
        
        history_text.config(state=DISABLED)
        
        btn_frame = Frame(history_win)
        btn_frame.pack(pady=10)
        Button(btn_frame, text="Экспорт в файл", command=self.export_history).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Очистить историю", command=self.clear_history).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Закрыть", command=history_win.destroy).pack(side=LEFT, padx=5)

    def export_history(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Сохранить историю как"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    for message in self.chat_history:
                        timestamp = datetime.fromtimestamp(message['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                        f.write(f"[{timestamp}] {message['username']}: {message['message']}\n")
                messagebox.showinfo("Успех", "История успешно экспортирована")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось экспортировать историю: {str(e)}")

    def clear_history(self):
        if messagebox.askyesno("Подтверждение", "Вы действительно хотите очистить историю переписки?"):
            self.chat_history = []
            self.save_history()
            messagebox.showinfo("Успех", "История переписки очищена")

    def stop_server(self):
        if messagebox.askokcancel("Выход", "Остановить сервер и выйти?"):
            if hasattr(self, 'server') and self.server:
                self.server.stop()
            self.save_history()
            self.root.destroy()
            sys.exit(0)

    def log_message(self, message):
        self.log_area.config(state=NORMAL)
        self.log_area.insert(END, message + "\n")
        self.log_area.see(END)
        self.log_area.config(state=DISABLED)

    def update_chat(self, message):
        self.chat_area.config(state=NORMAL)
        self.chat_area.insert(END, message)
        self.chat_area.see(END)
        self.chat_area.config(state=DISABLED)

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    root = Tk()
    root.iconbitmap(default="icon.ico")
    app = ChatApp(root)
    root.mainloop()
