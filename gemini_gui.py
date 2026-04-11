import tkinter as tk
from tkinter import scrolledtext, messagebox
import google.generativeai as genai
import threading

class GeminiGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gemini API Chat")
        self.root.geometry("700x600")

        # API Key Frame
        api_frame = tk.Frame(self.root)
        api_frame.pack(padx=10, pady=10, fill=tk.X)
        
        tk.Label(api_frame, text="Gemini API Key:").pack(side=tk.LEFT)
        self.api_key_entry = tk.Entry(api_frame, show="*", width=50)
        self.api_key_entry.pack(side=tk.LEFT, padx=5)

        # Chat History
        self.chat_history = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, state=tk.DISABLED, font=("Arial", 10))
        self.chat_history.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        # Input Frame
        input_frame = tk.Frame(self.root)
        input_frame.pack(padx=10, pady=10, fill=tk.X)

        self.user_input = tk.Text(input_frame, height=4, wrap=tk.WORD, font=("Arial", 10))
        self.user_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.send_button = tk.Button(input_frame, text="Send", command=self.send_message, width=10, height=2, bg="lightblue")
        self.send_button.pack(side=tk.RIGHT, padx=10)

        self.chat_session = None

        # Bind Enter key to send message (Shift-Enter for new line)
        self.user_input.bind("<Return>", self.handle_enter)

    def handle_enter(self, event):
        # Allow Shift-Enter to create a new line without sending
        if event.state & 0x0001:  # Shift key is pressed
            return None
        self.send_message()
        return "break"  # Prevent default behavior (inserting a newline)

    def initialize_gemini(self):
        api_key = self.api_key_entry.get().strip()
        if not api_key:
            messagebox.showwarning("Warning", "Please enter your Gemini API Key in the top field.")
            return False

        try:
            genai.configure(api_key=api_key)
            # Use gemini-1.5-flash or gemini-1.5-pro for text tasks
            model = genai.GenerativeModel('gemini-3.1-flash-lite-preview') 
            self.chat_session = model.start_chat(history=[])
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize Gemini API:\n{str(e)}")
            return False

    def append_to_chat(self, sender, message):
        self.chat_history.config(state=tk.NORMAL)
        self.chat_history.insert(tk.END, f"{sender}: ", sender)
        self.chat_history.insert(tk.END, f"{message}\n\n")
        self.chat_history.config(state=tk.DISABLED)
        self.chat_history.yview(tk.END)

    def send_message(self):
        user_text = self.user_input.get("1.0", tk.END).strip()
        if not user_text:
            return

        if self.chat_session is None:
            if not self.initialize_gemini():
                return
        
        self.append_to_chat("You", user_text)
        self.user_input.delete("1.0", tk.END)
        self.send_button.config(state=tk.DISABLED, text="Thinking...")

        # Run API call in a thread to keep GUI responsive
        threading.Thread(target=self.get_gemini_response, args=(user_text,)).start()

    def get_gemini_response(self, user_text):
        try:
            response = self.chat_session.send_message(user_text)
            self.root.after(0, self.append_to_chat, "Gemini", response.text)
        except Exception as e:
            self.root.after(0, self.append_to_chat, "System Error", str(e))
            # Reset session so user can re-enter valid API key if that was the issue
            self.chat_session = None 
        finally:
            self.root.after(0, lambda: self.send_button.config(state=tk.NORMAL, text="Send"))

if __name__ == "__main__":
    root = tk.Tk()
    app = GeminiGUI(root)
    # Tag configuration for bolding sender
    app.chat_history.tag_config("You", font=("Arial", 10, "bold"), foreground="blue")
    app.chat_history.tag_config("Gemini", font=("Arial", 10, "bold"), foreground="green")
    app.chat_history.tag_config("System Error", font=("Arial", 10, "bold"), foreground="red")
    root.mainloop()
