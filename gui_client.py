import threading
from client import ChatClient
# import tkinter as tk
# from tkinter import ttk
# from tkinter.scrolledtext import ScrolledText
# import tkinter.font as tkFont
import customtkinter as ctk
import tkinter.messagebox as mb 
from customtkinter import CTkInputDialog

current_users = []

class ChatGUI:
    def __init__(self, username):
        self.emoji_list = ["😊", "😂", "😍", "👍", "🔥", "😭", "😎"]
        
        self.emoji_index = 0

        self.username = username
        self.chat_client = ChatClient(username=self.username, on_message_callback=self.display_message)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.window = ctk.CTk()
        self.window.title(f"Chatroom - Logged in as {username}")

        self.header = ctk.CTkLabel(self.window, text="Welcome to the CS4459 Chatroom!", font=('Helvetica', 16, 'bold'))
        self.header.pack(pady=(10, 0))

        # chat display area (not readonly, but we avoid user typing into it)
        self.chat_frame = ctk.CTkScrollableFrame(self.window, width=500, height=400, fg_color="transparent")
        self.chat_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # --- Message input row ---
        self.input_row = ctk.CTkFrame(self.window, fg_color="transparent")
        self.input_row.pack(fill="x", padx=20, pady=(0, 10))

        # Emoji button (left)
        self.emoji_menu = ctk.CTkOptionMenu(
            self.input_row,
            values=self.emoji_list,
            command=self.insert_emoji,
            width=60
        )
        self.emoji_menu.set("😊")
        self.emoji_menu.pack(side="left", padx=(0, 10))

        # Entry field (center)
        self.input_field = ctk.CTkTextbox(
            self.input_row,
            height=30,
            width=300,
            corner_radius=6
        )
        self.input_field.pack(side="left", fill="x", expand=True)
        self.input_field.bind("<Return>", self.on_enter_pressed)

        # Send button (right)
        self.send_button = ctk.CTkButton(
            self.input_row,
            text="Send",
            command=self.on_enter_pressed
        )
        self.send_button.pack(side="left", padx=(10, 0))

        # close protocol
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        # start receiving messages only after full GUI is built
        threading.Thread(target=self.chat_client.receive_messages, daemon=True).start()

    def on_enter_pressed(self, event=None):
        message = self.input_field.get("0.0","end").strip()
        if message:
            self.chat_client.send_message(message)
            self.input_field.delete("0.0", "end")
    
    def insert_emoji(self, emoji):
        self.input_field.insert("end", emoji)
    
    def display_message(self, sender, message):
        #self.chat_display.configure(state='normal')
        is_you = sender == self.username
        display_name = "You" if is_you else sender
    
        bubble = ctk.CTkFrame(
            self.chat_frame,
            fg_color="#3b82f6" if is_you else "#4b5563",  # blue / gray
            corner_radius=15
        )
        bubble.pack(pady=5, padx=10, anchor="w" if is_you else "e")

        msg_label = ctk.CTkLabel(
            bubble,
            text=f"{display_name}: {message}",
            wraplength=160,
            font=("Helvetica", 13),
            justify="left",
            text_color="white"
        )
        msg_label.pack(padx=10, pady=6)
        # tag = 'you' if sender == self.username else 'other'
        # display_name = "You" if sender == self.username else sender
        # self.chat_display.insert("end", f"{display_name}: {message}\n", tag)
        # self.chat_display.configure(state='disabled')
        # self.chat_display.yview("end")
        self.chat_frame._parent_canvas.yview_moveto(1.0)
        
    def on_close(self):
        try:
            # Close client connection
            self.chat_client.close()

            # ✅ Safely destroy all children of chat_frame
            if hasattr(self, "chat_frame"):
                for child in self.chat_frame.winfo_children():
                    try:
                        child.destroy()
                    except Exception as e:
                        print(f"Child destroy failed: {e}")

            # Delay final destroy slightly to let GUI settle
            self.window.after(50, self.window.destroy)

        except Exception as e:
            print(f"[on_close] Error: {e}")


    def run(self):
        self.window.mainloop()
        
if __name__ == "__main__":
    app = ctk.CTk()
    app.withdraw()  # hide root window temporarily

    dialog = CTkInputDialog(title="Username", text="Enter your username:")
    username = dialog.get_input()

    if not username:
        print("No username entered. Exiting.")
        exit()

    app.destroy()  # destroy temp window

    gui = ChatGUI(username)
    gui.run()