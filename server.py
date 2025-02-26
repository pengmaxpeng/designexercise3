import grpc
import time
import datetime
import hashlib
import fnmatch
import threading
from collections import OrderedDict
from concurrent import futures

# Import the generated gRPC code
import chat_pb2
import chat_pb2_grpc

class ChatServiceServicer(chat_pb2_grpc.ChatServiceServicer):
    def __init__(self):
        # Maps usernames to their data (password hash and unread messages)
        self.users = OrderedDict()     
        # Maps usernames to their active subscription channels
        self.active_subscriptions = {}
        # Maps a sorted tuple of two usernames to a list of message entries (conversation history)
        self.conversations = {}
        self.next_msg_id = 1  # Global counter for assigning unique message IDs
    
    # Hash a password using SHA256
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def Login(self, request, context):
        username = request.username
        password = request.password
        
        if username not in self.users:
            return chat_pb2.LoginResponse(
                success=False,
                message="Username does not exist"
            )
        
        stored_hash = self.users[username]["password_hash"]
        if stored_hash != self.hash_password(password):
            return chat_pb2.LoginResponse(
                success=False,
                message="Incorrect password"
            )
        
        # For gRPC, we don't need to check for active users the same way
        # since we use streaming for message delivery
        
        unread_count = len(self.users[username]["messages"])
        return chat_pb2.LoginResponse(
            success=True,
            message=f"Login successful. Unread messages: {unread_count}",
            unread_count=unread_count
        )
    
    def CreateAccount(self, request, context):
        username = request.username
        password = request.password
        
        if username in self.users:
            return chat_pb2.CreateAccountResponse(
                success=False,
                message="Username already exists"
            )
        
        self.users[username] = {
            "password_hash": self.hash_password(password),
            "messages": []
        }
        
        return chat_pb2.CreateAccountResponse(
            success=True,
            message="Account created"
        )
    
    def LogOff(self, request, context):
        username = request.username
        
        # Remove active subscription if exists
        if username in self.active_subscriptions:
            del self.active_subscriptions[username]
        
        return chat_pb2.LogOffResponse(
            success=True,
            message="User logged off"
        )
    
    def DeleteAccount(self, request, context):
        username = request.username
        
        if username not in self.users:
            return chat_pb2.DeleteAccountResponse(
                success=False,
                message="User does not exist"
            )
        
        # Delete the user's data
        del self.users[username]
        
        # Remove active subscription if it exists
        if username in self.active_subscriptions:
            del self.active_subscriptions[username]
        
        # Remove all conversation history involving this user
        keys_to_delete = [key for key in self.conversations if username in key]
        for key in keys_to_delete:
            del self.conversations[key]
        
        return chat_pb2.DeleteAccountResponse(
            success=True,
            message="Account and all conversation history deleted"
        )

    
    def SendMessage(self, request, context):
        sender = request.sender
        recipient = request.recipient
        content = request.content
        timestamp = datetime.datetime.now().isoformat()
        
        if recipient not in self.users:
            return chat_pb2.SendMessageResponse(
                success=False,
                message="Recipient not found"
            )
        
        # Create message entry
        msg_id = self.next_msg_id
        self.next_msg_id += 1
        
        message_entry = chat_pb2.ChatMessage(
            id=msg_id,
            sender=sender,
            content=content,
            timestamp=timestamp
        )
        
        # Store in conversation history
        conv_key = tuple(sorted([sender, recipient]))
        if conv_key not in self.conversations:
            self.conversations[conv_key] = []
        
        self.conversations[conv_key].append(message_entry)
        
        # Add to recipient's unread messages if they're not actively listening
        if recipient not in self.active_subscriptions:
            self.users[recipient]["messages"].append(message_entry)
        else:
            # Forward message to active subscription
            try:
                self.active_subscriptions[recipient].put(message_entry)
            except Exception as e:
                print(f"Error forwarding message to {recipient}: {e}")
                self.users[recipient]["messages"].append(message_entry)
        
        return chat_pb2.SendMessageResponse(
            success=True,
            message="Message sent"
        )
    
    def ReadMessages(self, request, context):
        username = request.username
        limit = request.limit
        
        if username not in self.users:
            return chat_pb2.ReadMessagesResponse()
        
        user_messages = self.users[username]["messages"]
        
        if limit > 0:
            messages_to_view = user_messages[:limit]
            self.users[username]["messages"] = user_messages[limit:]
        else:
            messages_to_view = user_messages
            self.users[username]["messages"] = []
        
        return chat_pb2.ReadMessagesResponse(messages=messages_to_view)
    
    def DeleteMessages(self, request, context):
        username = request.username
        message_ids = request.message_ids
        
        if username not in self.users:
            return chat_pb2.DeleteMessagesResponse(
                success=False,
                message="User not found"
            )
        
        if not message_ids:
            return chat_pb2.DeleteMessagesResponse(
                success=False,
                message="No message IDs provided"
            )
        
        # Check if any of the messages exist
        message_exists = False
        for msg in self.users[username]["messages"]:
            if msg.id in message_ids:
                message_exists = True
                break
        
        if not message_exists:
            for conv_key in self.conversations:
                if username in conv_key:
                    for msg in self.conversations[conv_key]:
                        if msg.id in message_ids:
                            message_exists = True
                            break
                    if message_exists:
                        break
        
        if not message_exists:
            return chat_pb2.DeleteMessagesResponse(
                success=False,
                message="No matching message found to delete"
            )
        
        # Delete from unread messages
        current_unread = self.users[username]["messages"]
        self.users[username]["messages"] = [msg for msg in current_unread if msg.id not in message_ids]
        
        # Delete from conversation history
        for conv_key in self.conversations:
            if username in conv_key:
                conv = self.conversations[conv_key]
                self.conversations[conv_key] = [msg for msg in conv if msg.id not in message_ids]
        
        return chat_pb2.DeleteMessagesResponse(
            success=True,
            message="Specified messages deleted"
        )
    
    def ViewConversation(self, request, context):
        username = request.username
        other_user = request.other_user
        
        if other_user not in self.users:
            return chat_pb2.ViewConversationResponse()
        
        conv_key = tuple(sorted([username, other_user]))
        conversation = self.conversations.get(conv_key, [])
        
        # Mark unread messages from the other user as read
        if username in self.users:
            current_unread = self.users[username]["messages"]
            self.users[username]["messages"] = [msg for msg in current_unread if msg.sender != other_user]
        
        return chat_pb2.ViewConversationResponse(messages=conversation)
    
    def ListAccounts(self, request, context):
        username = request.username
        wildcard = request.wildcard if request.wildcard else "*"
        
        matching_users = fnmatch.filter(list(self.users.keys()), wildcard)
        return chat_pb2.ListAccountsResponse(usernames=matching_users)
    
    def SubscribeToMessages(self, request, context):
        username = request.username
        import queue
        message_queue = queue.Queue()
        self.active_subscriptions[username] = message_queue

        try:
            # Do not yield stored (offline) messages.
            # Only yield messages that arrive after the user has subscribed.
            while context.is_active():
                try:
                    msg = message_queue.get(block=True, timeout=1.0)
                    yield msg
                except queue.Empty:
                    continue
        except Exception as e:
            print(f"Error in subscription for {username}: {e}")
        finally:
            if username in self.active_subscriptions:
                del self.active_subscriptions[username]

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServiceServicer_to_server(ChatServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server started on port 50051")
    try:
        while True:
            time.sleep(86400)  # One day in seconds
    except KeyboardInterrupt:
        server.stop(0)
        print("Server stopped")

if __name__ == '__main__':
    serve()