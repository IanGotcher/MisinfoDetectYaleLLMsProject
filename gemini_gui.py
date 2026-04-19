import tkinter as tk
from tkinter import scrolledtext, messagebox
import google.generativeai as genai
import threading
import re

class GeminiGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MisinfoDetect - Gemini API Chat")
        self.root.geometry("700x700")

        # API Key Frame
        api_frame = tk.Frame(self.root)
        api_frame.pack(padx=10, pady=10, fill=tk.X)
        
        tk.Label(api_frame, text="Gemini API Key:").pack(side=tk.LEFT)
        self.api_key_entry = tk.Entry(api_frame, show="*", width=50)
        self.api_key_entry.pack(side=tk.LEFT, padx=5)

        # Verdict Label
        self.verdict_label = tk.Label(
            self.root, 
            text="No Statement Given", 
            bg="white", 
            fg="black", 
            font=("Arial", 16, "bold"), 
            pady=10, 
            relief=tk.RAISED
        )
        self.verdict_label.pack(padx=10, pady=(0, 10), fill=tk.X)

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
            
            system_prompt = (
                "Your task is to take the statement given by the user and classify it based on whether it is a true statement or a false statement/statement of misinformation.\n\n"
                "Here are the five verdict categories you will choose from when classifying the user's statement:\n"
                "1. No statement given: Choose this verdict if the user's chat input did not contain an statement to verify as true or as misinformation. (If this occurs, respond as normal, but ensure that whatever you say, put \"Verdict: No Statement Given\" at the end of your response.)\n"
                "2. True: The statement given by the user is true.\n"
                "3. False: The statement given by the user is false. (Choose this is the statement is misinformation and therefore false)\n"
                "4. Needs context: The statement given by the user is such that it should not be marked true or false, as it: blends true statements with false/misinformed statements; is true but it was taken out of relevant context that is essential to understanding it correctly; or the like.\n"
                "5. Unknowable: Nobody can say whether it is true or false.\n\n"
                "Respond in the following format:\n"
                "Explanation: <Give an explanation that explains whether this statement is true, false, needs context, or unknowable.>\n\n"
                "Verdict: <Respond \"True\", \"False\", \"Needs Context\", or \"Unknowable\", e.g. \"Verdict: True\">"
            )
            # Use 'gemini-3.1-flash-lite-preview'
            model = genai.GenerativeModel('gemini-3.1-flash-lite-preview', system_instruction=system_prompt) 
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

        # Add waiting message
        self.chat_history.config(state=tk.NORMAL)
        self.waiting_index = self.chat_history.index("end-1c")
        self.chat_history.insert(tk.END, "System: ", "System Note")
        self.chat_history.insert(tk.END, "chat message sent to Gemini API, please wait a few seconds...\n\n", "System Note")
        self.chat_history.config(state=tk.DISABLED)
        self.chat_history.yview(tk.END)

        # Run API call in a thread to keep GUI responsive
        threading.Thread(target=self.get_gemini_response, args=(user_text,)).start()

    def process_verdict(self, response_text):
        # Look for the last line that starts with "Verdict:"
        lines = response_text.strip().split('\n')
        verdict_line = None
        for line in reversed(lines):
            stripped_line = line.strip()
            if stripped_line.lower().startswith("verdict:"):
                verdict_line = stripped_line
                break
        
        if verdict_line:
            val = verdict_line.lower().replace("verdict:", "").strip()
            # Clean up potential punctuation like asterisks or quotes
            val = re.sub(r'[^a-z\s]', '', val).strip()
            
            if "no statement given" in val:
                v_text, bg, fg = "No Statement Given", "white", "black"
            elif "true" in val and "not" not in val: # Simple check to prevent missing "not true"
                v_text, bg, fg = "True", "darkgreen", "white"
            elif "false" in val:
                v_text, bg, fg = "False", "darkred", "white"
            elif "needs context" in val:
                v_text, bg, fg = "Needs Context", "yellow", "black"
            elif "unknowable" in val or "unknown" in val:
                v_text, bg, fg = "Unknown", "#800080", "white" # #800080 is Purple
            else:
                v_text, bg, fg = "Error", "gray", "white"
        else:
             v_text, bg, fg = "Error", "gray", "white"
            
        self.verdict_label.config(text=v_text, bg=bg, fg=fg)

    def get_gemini_response(self, user_text):
        try:
            response = self.chat_session.send_message(user_text)
            # Replace waiting message with the actual response text in UI thread
            self.root.after(0, self.replace_waiting_with_response, "Gemini", response.text)
            # Update the verdict label based on the response text in UI thread
            self.root.after(0, self.process_verdict, response.text)
        except Exception as e:
            self.root.after(0, self.replace_waiting_with_response, "System Error", str(e))
            self.root.after(0, lambda: self.verdict_label.config(text="Error", bg="gray", fg="white"))
            # Reset session so user can re-enter valid API key if that was the issue
            self.chat_session = None 
        finally:
            self.root.after(0, lambda: self.send_button.config(state=tk.NORMAL, text="Send"))

    def replace_waiting_with_response(self, sender, message):
        self.chat_history.config(state=tk.NORMAL)
        if hasattr(self, 'waiting_index'):
            self.chat_history.delete(self.waiting_index, "end-1c")
        self.chat_history.config(state=tk.DISABLED)
        self.append_to_chat(sender, message)

if __name__ == "__main__":
    root = tk.Tk()
    app = GeminiGUI(root)
    # Tag configuration for bolding sender
    app.chat_history.tag_config("You", font=("Arial", 10, "bold"), foreground="blue")
    app.chat_history.tag_config("Gemini", font=("Arial", 10, "bold"), foreground="green")
    app.chat_history.tag_config("System Error", font=("Arial", 10, "bold"), foreground="red")
    app.chat_history.tag_config("System Note", font=("Arial", 10, "italic"), foreground="gray")
    root.mainloop()
