import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog
import threading
import grpc
import time
import datetime
import sys

# Import the generated gRPC code
import chat_pb2
import chat_pb2_grpc

# -------------------------------
# gRPC Chat Client (backend)
# -------------------------------
class ChatClient:
    def __init__(self, server_host='localhost', server_port=50051):
        self.server_address = f"{server_host}:{server_port}"
        self.channel = grpc.insecure_channel(self.server_address)
        self.stub = chat_pb2_grpc.ChatServiceStub(self.channel)
        self.username = None
        self.running = True

    def login(self, username, password):
        try:
            response = self.stub.Login(chat_pb2.LoginRequest(
                username=username,
                password=password
            ))
            return response
        except grpc.RpcError as e:
            print(f"RPC Error during login: {e.details()}", file=sys.stderr)
            return chat_pb2.LoginResponse(
                success=False, 
                message=f"Connection error: {e.details()}"
            )

    def create_account(self, username, password):
        try:
            response = self.stub.CreateAccount(chat_pb2.CreateAccountRequest(
                username=username,
                password=password
            ))
            return response
        except grpc.RpcError as e:
            print(f"RPC Error during account creation: {e.details()}", file=sys.stderr)
            return chat_pb2.CreateAccountResponse(
                success=False, 
                message=f"Connection error: {e.details()}"
            )

    def send_message(self, recipient, message):
        try:
            response = self.stub.SendMessage(chat_pb2.SendMessageRequest(
                sender=self.username,
                recipient=recipient,
                content=message
            ))
            return response
        except grpc.RpcError as e:
            print(f"RPC Error sending message: {e.details()}", file=sys.stderr)
            return chat_pb2.SendMessageResponse(
                success=False, 
                message=f"Failed to send: {e.details()}"
            )

    def list_accounts(self, wildcard="*"):
        try:
            response = self.stub.ListAccounts(chat_pb2.ListAccountsRequest(
                username=self.username,
                wildcard=wildcard
            ))
            return response
        except grpc.RpcError as e:
            print(f"RPC Error listing accounts: {e.details()}", file=sys.stderr)
            return chat_pb2.ListAccountsResponse(usernames=[])

    def read_messages(self, limit=0):
        try:
            response = self.stub.ReadMessages(chat_pb2.ReadMessagesRequest(
                username=self.username,
                limit=int(limit) if limit else 0
            ))
            return response
        except grpc.RpcError as e:
            print(f"RPC Error reading messages: {e.details()}", file=sys.stderr)
            return chat_pb2.ReadMessagesResponse(messages=[])

    def delete_messages(self, id_list):
        try:
            response = self.stub.DeleteMessages(chat_pb2.DeleteMessagesRequest(
                username=self.username,
                message_ids=id_list
            ))
            return response
        except grpc.RpcError as e:
            print(f"RPC Error deleting messages: {e.details()}", file=sys.stderr)
            return chat_pb2.DeleteMessagesResponse(
                success=False, 
                message=f"Failed to delete messages: {e.details()}"
            )

    def view_conversation(self, other_user):
        try:
            response = self.stub.ViewConversation(chat_pb2.ViewConversationRequest(
                username=self.username,
                other_user=other_user
            ))
            return response
        except grpc.RpcError as e:
            print(f"RPC Error viewing conversation: {e.details()}", file=sys.stderr)
            return chat_pb2.ViewConversationResponse(messages=[])

    def delete_account(self):
        try:
            response = self.stub.DeleteAccount(chat_pb2.DeleteAccountRequest(
                username=self.username
            ))
            return response
        except grpc.RpcError as e:
            print(f"RPC Error deleting account: {e.details()}", file=sys.stderr)
            return chat_pb2.DeleteAccountResponse(
                success=False, 
                message=f"Failed to delete account: {e.details()}"
            )

    def log_off(self):
        if not self.username:
            return chat_pb2.LogOffResponse(success=True, message="Not logged in")
        try:
            response = self.stub.LogOff(chat_pb2.LogOffRequest(
                username=self.username
            ))
            return response
        except grpc.RpcError as e:
            print(f"RPC Error logging off: {e.details()}", file=sys.stderr)
            return chat_pb2.LogOffResponse(
                success=False, 
                message=f"Failed to log off: {e.details()}"
            )

    def subscribe_to_messages(self, callback):
        """Subscribe to incoming messages and call the callback for each one"""
        try:
            subscription_request = chat_pb2.SubscribeRequest(username=self.username)
            for message in self.stub.SubscribeToMessages(subscription_request):
                if not self.running:
                    break
                callback(message)
        except grpc.RpcError as e:
            if self.running:
                print(f"Error in message subscription: {e.details()}", file=sys.stderr)

    def close(self):
        self.running = False
        self.log_off()
        self.channel.close()

# -------------------------------
# Tkinter GUI (refactored layout)
# -------------------------------
class ChatGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("gRPC Chat Client")
        self.client = None
        self.user_list = []  # available users for dropdowns

        # Create three frames: login, chat, and commands.
        self.login_frame = tk.Frame(master)
        self.chat_frame = tk.Frame(master)
        self.command_frame = tk.Frame(master)

        self.setup_login_frame()
        self.setup_chat_frame()
        self.setup_command_frame()

        self.login_frame.pack(fill=tk.BOTH, expand=True)
        self.master.protocol("WM_DELETE_WINDOW", self.close)

    def setup_login_frame(self):
        tk.Label(self.login_frame, text="Server IP:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.server_ip_entry = tk.Entry(self.login_frame)
        self.server_ip_entry.insert(0, "localhost")
        self.server_ip_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self.login_frame, text="Username:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.username_entry = tk.Entry(self.login_frame)
        self.username_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(self.login_frame, text="Password:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.password_entry = tk.Entry(self.login_frame, show="*")
        self.password_entry.grid(row=2, column=1, padx=5, pady=5)

        self.login_button = tk.Button(self.login_frame, text="Login", command=self.login)
        self.login_button.grid(row=3, column=0, padx=5, pady=5)

        self.create_button = tk.Button(self.login_frame, text="Create Account", command=self.create_account)
        self.create_button.grid(row=3, column=1, padx=5, pady=5)

        self.exit_button = tk.Button(self.login_frame, text="Exit", command=self.close)
        self.exit_button.grid(row=4, column=0, columnspan=2, padx=5, pady=5)

        self.status_label = tk.Label(self.login_frame, text="", fg="red")
        self.status_label.grid(row=5, column=0, columnspan=2, padx=5, pady=5)

    def setup_chat_frame(self):
        # Main chat display
        self.chat_display = scrolledtext.ScrolledText(self.chat_frame, state="disabled", width=80, height=20)
        self.chat_display.grid(row=0, column=0, columnspan=3, padx=10, pady=10)

        # Recipient dropdown
        tk.Label(self.chat_frame, text="Recipient:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.recipient_var = tk.StringVar()
        self.recipient_var.set("All")
        self.recipient_menu = tk.OptionMenu(self.chat_frame, self.recipient_var, "All")
        self.recipient_menu.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # Message entry and send button
        tk.Label(self.chat_frame, text="Message:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.msg_entry = tk.Entry(self.chat_frame, width=60)
        self.msg_entry.grid(row=2, column=1, padx=5, pady=5)
        self.msg_entry.bind("<Return>", lambda event: self.send_chat())
        self.send_button = tk.Button(self.chat_frame, text="Send", command=self.send_chat)
        self.send_button.grid(row=2, column=2, padx=5, pady=5)

    def setup_command_frame(self):
        # Command buttons and dropdown for conversation viewing.
        self.list_button = tk.Button(self.command_frame, text="List Accounts", command=self.list_accounts)
        self.list_button.grid(row=0, column=0, padx=5, pady=5)

        self.delete_msg_button = tk.Button(self.command_frame, text="Delete Messages", command=self.delete_messages)
        self.delete_msg_button.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self.command_frame, text="View Conversation:").grid(row=1, column=0, padx=5, pady=5)
        self.view_conv_var = tk.StringVar()
        self.view_conv_var.set("Select User")
        self.view_conv_menu = tk.OptionMenu(self.command_frame, self.view_conv_var, "Select User")
        self.view_conv_menu.grid(row=1, column=1, padx=5, pady=5)
        self.view_conv_button = tk.Button(self.command_frame, text="View", command=self.view_conversation)
        self.view_conv_button.grid(row=1, column=2, padx=5, pady=5)

        self.delete_acc_button = tk.Button(self.command_frame, text="Delete Account", command=self.delete_account)
        self.delete_acc_button.grid(row=0, column=2, padx=5, pady=5)

        self.logoff_button = tk.Button(self.command_frame, text="Log Off", command=self.logout)
        self.logoff_button.grid(row=0, column=3, padx=5, pady=5)

        self.refresh_button = tk.Button(self.command_frame, text="Refresh Users", command=self.refresh_users)
        self.refresh_button.grid(row=1, column=3, padx=5, pady=5)

        self.read_button = tk.Button(self.command_frame, text="Read Unread Messages", command=self.read_messages)
        self.read_button.grid(row=1, column=4, padx=5, pady=5)

        self.close_button = tk.Button(self.command_frame, text="Close", command=self.close)
        self.close_button.grid(row=0, column=4, padx=5, pady=5)

    # -------------------------------
    # GUI event handlers and actions
    # -------------------------------
    def login(self):
        server_ip = self.server_ip_entry.get().strip()
        port = 50051  # Default gRPC port
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not server_ip or not username or not password:
            self.status_label.config(text="Please fill in all fields.")
            return

        if self.client is None:
            self.client = ChatClient(server_ip, port)
        response = self.client.login(username, password)
        if response.success:
            self.client.username = username
            self.status_label.config(text=f"Login successful. Unread messages: {response.unread_count}")
            # Start the subscription thread for incoming messages.
            threading.Thread(target=self.client.subscribe_to_messages,
                             args=(self.handle_incoming_message,), daemon=True).start()
            # Switch to chat and command frames.
            self.login_frame.pack_forget()
            self.chat_frame.pack(fill=tk.BOTH, expand=True)
            self.command_frame.pack(fill=tk.X)
            self.refresh_users()
        else:
            self.status_label.config(text=f"Login failed: {response.message}")

    def create_account(self):
        server_ip = self.server_ip_entry.get().strip()
        port = 50051
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not server_ip or not username or not password:
            self.status_label.config(text="Please fill in all fields.")
            return

        if self.client is None:
            self.client = ChatClient(server_ip, port)
        response = self.client.create_account(username, password)
        self.status_label.config(text=response.message)

    def send_chat(self):
        if not self.client or not self.client.username:
            messagebox.showerror("Error", "Not logged in.")
            return
        recipient = self.recipient_var.get()
        message = self.msg_entry.get().strip()
        if not message:
            return
        response = self.client.send_message(recipient, message)
        if response.success:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.append_text(f"[{timestamp}] {self.client.username} -> {recipient}: {message}")
            self.msg_entry.delete(0, tk.END)
        else:
            messagebox.showerror("Error", response.message)

    def list_accounts(self):
        if not self.client or not self.client.username:
            messagebox.showerror("Error", "Not logged in.")
            return
        response = self.client.list_accounts("*")
        if response:
            self.user_list = response.usernames
            self.update_recipient_menu()
            self.update_view_conv_menu()
            self.append_text("Available users: " + ", ".join(self.user_list))

    def delete_messages(self):
        if not self.client or not self.client.username:
            return
        id_str = simpledialog.askstring("Delete Messages",
                                        "Enter message IDs to delete (comma separated):",
                                        parent=self.master)
        if not id_str:
            return
        try:
            id_list = [int(x.strip()) for x in id_str.split(",") if x.strip()]
            if not id_list:
                return
            response = self.client.delete_messages(id_list)
            messagebox.showinfo("Delete Messages", response.message)
        except ValueError:
            messagebox.showerror("Error", "Invalid format. Use comma-separated numbers.")

    def view_conversation(self):
        if not self.client or not self.client.username:
            return
        other_user = self.view_conv_var.get()
        if other_user == "Select User":
            messagebox.showerror("Error", "Select a valid user.")
            return
        response = self.client.view_conversation(other_user)
        if response and response.messages:
            conv_text = f"Conversation with {other_user}:\n"
            # Display each message with its ID, sender, timestamp (from the message), and content.
            for msg in response.messages:
                conv_text += f"[ID {msg.id}]({msg.timestamp}): {msg.content}\n"
            self.append_text(conv_text)
        else:
            self.append_text(f"No conversation with {other_user}.")

    def read_messages(self):
        if not self.client or not self.client.username:
            return
        response = self.client.read_messages()
        if not response.messages:
            messagebox.showinfo("Messages", "No unread messages.")
            return
        # Display unread messages in a new window.
        msg_window = tk.Toplevel(self.master)
        msg_window.title("Unread Messages")
        msg_text = scrolledtext.ScrolledText(msg_window, width=60, height=20)
        msg_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        for msg in response.messages:
            msg_text.insert(tk.END, f"[ID {msg.id}] {msg.sender}: {msg.content}\n\n")
        msg_text.config(state="disabled")

    def delete_account(self):
        if not self.client or not self.client.username:
            return
        confirm = messagebox.askyesno("Confirm",
                                      "Are you sure you want to delete your account? This cannot be undone.")
        if not confirm:
            return
        response = self.client.delete_account()
        messagebox.showinfo("Delete Account", response.message)
        if response.success:
            self.logout()

    def logout(self):
        if not self.client:
            return
        self.client.log_off()
        self.client.username = None
        self.chat_frame.pack_forget()
        self.command_frame.pack_forget()
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.configure(state="disabled")
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        self.status_label.config(text="")
        self.user_list = []
        self.update_recipient_menu()
        self.update_view_conv_menu()

    def refresh_users(self):
        if self.client and self.client.username:
            response = self.client.list_accounts("*")
            if response:
                self.user_list = response.usernames
                self.update_recipient_menu()
                self.update_view_conv_menu()

    def update_recipient_menu(self):
        menu = self.recipient_menu["menu"]
        menu.delete(0, "end")
        options = ["All"] + [user for user in self.user_list if user != self.client.username]
        for option in options:
            menu.add_command(label=option, command=lambda value=option: self.recipient_var.set(value))
        self.recipient_var.set(options[0] if options else "All")

    def update_view_conv_menu(self):
        menu = self.view_conv_menu["menu"]
        menu.delete(0, "end")
        options = ["Select User"] + [user for user in self.user_list if user != self.client.username]
        for option in options:
            menu.add_command(label=option, command=lambda value=option: self.view_conv_var.set(value))
        self.view_conv_var.set(options[0] if options else "Select User")

    def handle_incoming_message(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        text = f"[{timestamp}] {message.sender}: {message.content}"
        self.append_text(text)

    def append_text(self, text):
        def update():
            self.chat_display.configure(state="normal")
            self.chat_display.insert(tk.END, text + "\n")
            self.chat_display.configure(state="disabled")
            self.chat_display.see(tk.END)
        self.master.after(0, update)

    def close(self):
        if self.client:
            self.client.close()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatGUI(root)
    root.mainloop()
