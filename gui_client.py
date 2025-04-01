import threading
from client import ChatClient
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

class ChatGUI:
    def __init__(self, username):
        self.username = username
        self.chat_client = ChatClient(username=self.username, on_message_callback=self.display_message)
        self.window = tk.Tk()
        self.window.title(f"Chatroom - Logged in as {username}")

        # chat log area (read only)
        self.chat_display = ScrolledText(self.window, state='disabled', wrap=tk.WORD, height=20, width=50)
        self.chat_display.pack(padx=50, pady=50)

        # message entry box
        self.input_field = tk.Entry(self.window, width=50)
        self.input_field.pack(padx=10, pady=(0,10))
        self.input_field.bind("<Return>", self.on_enter_pressed)

        # start GUI loop
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_enter_pressed(self, event=None):
        message = self.input_field.get().strip()
        if message:
            self.chat_client.send_message(message)
            self.input_field.delete(0, tk.END)
    
    def display_message(self, sender, message):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, f"{'You' if sender == self.username else sender}: {message}\n")
        self.chat_display.yview(tk.END)
        self.chat_display.config(state='disabled')
    
    def on_close(self):
        self.chat_client.close()
        self.window.destroy()

    def run(self):
        threading.Thread(target=self.chat_client.receive_messages, daemon=True).start()
        self.window.mainloop()
        
if __name__ == "__main__":
    username = input("Enter your username: ")
    gui = ChatGUI(username)
    gui.run()