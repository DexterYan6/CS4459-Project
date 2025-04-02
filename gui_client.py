import threading
from client import ChatClient
# import tkinter as tk
# from tkinter import ttk
# from tkinter.scrolledtext import ScrolledText
# import tkinter.font as tkFont
import customtkinter as ctk
import tkinter.messagebox as mb 
from customtkinter import CTkInputDialog

class ChatGUI:
    def __init__(self, username):
        self.emoji_list = ["😊", "😂", "😍", "👍", "🔥", "😭", "😎"]
        
        self.emoji_index = 0

        self.username = username
        self.chat_client = ChatClient(username=self.username, on_message_callback=self.display_message)

        try:
            self.chat_client = ChatClient(username=self.username, on_message_callback=self.display_message)
            
            if not self.chat_client.check_username_available():
                # Handle username already taken
                mb.showerror("Username Error", f"Username '{username}' is already taken!")
                raise ValueError(f"Username '{username}' is already taken")
                
        except ConnectionError:
            mb.showerror("Server Error", "Cannot connect to the chatroom. Please try again later.")
            raise

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

        self.window.after(100, self.scroll_to_bottom)

    #when messages are sent, scroll to bottom - not sure why this wasn't happening before
    def scroll_to_bottom(self):
        try:
            self.window.after_idle(lambda: self.chat_frame._parent_canvas.yview_moveto(1.0))
        except Exception as e:
            if not self.is_closing:
                print(f"Error scrolling: {e}")

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
        self.scroll_to_bottom()       

    def on_close(self):
        # Set closing flag immediately to prevent new operations
        self.is_closing = True
        
        # First close the chat client
        try:
            if hasattr(self, 'chat_client'):
                self.chat_client.close()
        except Exception:
            pass  # Ignore any errors here
            
        # Use a clean approach to destroy the window
        try:
            # This avoids CustomTkinter's internal problems during destroy
            self.window.quit()
        except Exception:
            pass

    def run(self):
        self.window.mainloop()

    def _safe_destroy(self):
        """Final destruction step that handles any remaining cleanup"""
        try:
            # Destroy any remaining widgets if needed
            if self.window.winfo_exists():
                self.window.destroy()
        except Exception:
            self.window.quit()


    def run(self):
        self.window.mainloop()
        
if __name__ == "__main__":
    app = ctk.CTk()
    app.withdraw()  # hide root window temporarily
    
    # Set a proper minsize to ensure the window is truly invisible
    app.minsize(0, 0)
    app.geometry("0x0")
    app.overrideredirect(True)  # Remove window decorations
    
    while True:
        dialog = CTkInputDialog(text="Enter your username:", title="Username")
        username = dialog.get_input()
        
        if username != None and username.strip() == "":
            print("No username entered. Try again.")
            continue
        elif username == None:
            print("User clicked cancel or close")
            app.quit()
            exit()
        try:
            gui = ChatGUI(username)
            app.quit()
            gui.run()
            break
        except ValueError as e:
            print(f"Error: {e}")