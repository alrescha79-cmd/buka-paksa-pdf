"""
Custom Dialog Component
Komponen dialog kustom dengan font besar dan tombol deskriptif
"""
import tkinter as tk

class CustomDialog:
    """Custom dialog dengan font lebih besar dan tombol yang jelas"""
    
    def __init__(self, parent, title, message, buttons):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("600x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        
        # Safe grab_set with error handling
        try:
            self.dialog.grab_set()
        except tk.TclError:
            # If grab fails, continue without grab (dialog still works)
            pass
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - self.dialog.winfo_width()) // 2
        y = (self.dialog.winfo_screenheight() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        # Icon frame
        icon_frame = tk.Frame(self.dialog)
        icon_frame.pack(pady=20)
        
        # Message
        message_frame = tk.Frame(self.dialog)
        message_frame.pack(expand=True, fill='both', padx=30, pady=10)
        
        message_label = tk.Label(
            message_frame, 
            text=message, 
            font=("Arial", 14), 
            wraplength=500,
            justify='center'
        )
        message_label.pack(expand=True)
        
        # Buttons
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(pady=20)
        
        for i, (text, value, color) in enumerate(buttons):
            btn = tk.Button(
                button_frame,
                text=text,
                font=("Arial", 12, "bold"),
                bg=color,
                fg="white",
                width=15,
                height=2,
                command=lambda v=value: self.button_clicked(v)
            )
            btn.pack(side=tk.LEFT, padx=10)
    
    def button_clicked(self, value):
        self.result = value
        self.dialog.destroy()
    
    def show(self):
        self.dialog.wait_window()
        return self.result

def show_custom_dialog(parent, title, message, buttons):
    """Show custom dialog dengan tombol yang dapat dikustomisasi"""
    dialog = CustomDialog(parent, title, message, buttons)
    return dialog.show()