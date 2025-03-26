import grpc
import time
import datetime
import hashlib
import fnmatch
import threading
from collections import OrderedDict
from concurrent import futures
import os
import json
import argparse

import chat_pb2
import chat_pb2_grpc

class ChatServiceServicer(chat_pb2_grpc.ChatServiceServicer):
    def __init__(self, server_id, replicas):
        super().__init__()

        self.server_id = server_id
        self.replicas = replicas

        # Each server has its own .json file, so no single point of failure.
        self.data_file = f"chat_data_{self.server_id}.json"

        # Determine leader as smallest ID among [myself] + replicas
        all_ids = [r["server_id"] for r in self.replicas] + [self.server_id]
        self.leader_id = min(all_ids)
        self.is_leader = (self.server_id == self.leader_id)

        self.data_lock = threading.Lock()

        # In-memory data
        self.users = OrderedDict()
        self.active_subscriptions = {}
        self.conversations = {}
        self.next_msg_id = 1

        # Load data from file at startup
        self.load_data()

    def load_data(self):
        if not os.path.exists(self.data_file):
            return
        with self.data_lock:
            try:
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                self.next_msg_id = data.get("next_msg_id", 1)
                self.users = OrderedDict(data.get("users", {}))

                loaded_convs = data.get("conversations", {})
                self.conversations = {}
                for key_str, msg_list in loaded_convs.items():
                    key_tuple = tuple(key_str.split("::"))
                    converted = []
                    for m in msg_list:
                        converted.append(chat_pb2.ChatMessage(
                            id=m["id"],
                            sender=m["sender"],
                            content=m["content"],
                            timestamp=m["timestamp"]
                        ))
                    self.conversations[key_tuple] = converted
            except Exception as e:
                print(f"[load_data] Error: {e}")

    def save_data(self):
        with self.data_lock:
            data = {}
            data["next_msg_id"] = self.next_msg_id

            # Convert users to a serializable dict
            users_dict = {}
            for username, user_data in self.users.items():
                msg_list_dicts = []
                for msg in user_data["messages"]:
                    msg_list_dicts.append({
                        "id": msg.id,
                        "sender": msg.sender,
                        "content": msg.content,
                        "timestamp": msg.timestamp
                    })
                users_dict[username] = {
                    "password_hash": user_data["password_hash"],
                    "messages": msg_list_dicts
                }
            data["users"] = users_dict

            # Convert conversations to a serializable dict
            conv_dict = {}
            for key_tuple, msg_list in self.conversations.items():
                key_str = "::".join(key_tuple)
                msg_list_dicts = []
                for msg in msg_list:
                    msg_list_dicts.append({
                        "id": msg.id,
                        "sender": msg.sender,
                        "content": msg.content,
                        "timestamp": msg.timestamp
                    })
                conv_dict[key_str] = msg_list_dicts
            data["conversations"] = conv_dict

            try:
                with open(self.data_file, "w") as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                print(f"[save_data] Error: {e}")

    def replicate_to_followers(self, operation_type, data_dict):
        """
        Helper that sends a ReplicateMutation to all replicas if we're leader.
        """
        if not self.is_leader:
            return

        import json
        payload_str = json.dumps(data_dict)
        for rep in self.replicas:
            if rep["server_id"] == self.server_id:
                continue  # skip self
            target_addr = f'{rep["host"]}:{rep["port"]}'
            channel = grpc.insecure_channel(target_addr)
            stub = chat_pb2_grpc.ChatServiceStub(channel)

            req = chat_pb2.ReplicateMutationRequest(
                operation_type=operation_type,
                payload=payload_str
            )
            try:
                resp = stub.ReplicateMutation(req)
                if not resp.success:
                    print(f"[LEADER] Replicate {operation_type} to s{rep['server_id']} failed: {resp.message}")
            except Exception as e:
                print(f"[LEADER] Error replicating {operation_type} to s{rep['server_id']}: {e}")

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    # -------------------------------
    # gRPC Methods
    # -------------------------------

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
        self.save_data()

        # replicate if leader
        data_dict = {
            "username": username,
            "password_hash": self.users[username]["password_hash"]
        }
        self.replicate_to_followers("CREATE_ACCOUNT", data_dict)

        return chat_pb2.CreateAccountResponse(
            success=True,
            message="Account created"
        )

    def LogOff(self, request, context):
        username = request.username
        if username in self.active_subscriptions:
            del self.active_subscriptions[username]
        return chat_pb2.LogOffResponse(success=True, message="User logged off")

    def DeleteAccount(self, request, context):
        username = request.username
        if username not in self.users:
            return chat_pb2.DeleteAccountResponse(success=False, message="User does not exist")

        del self.users[username]
        if username in self.active_subscriptions:
            del self.active_subscriptions[username]
        
        # remove all conversation history involving this user
        keys_to_delete = [k for k in self.conversations if username in k]
        for k in keys_to_delete:
            del self.conversations[k]
        
        self.save_data()

        data_dict = { "username": username }
        self.replicate_to_followers("DELETE_ACCOUNT", data_dict)

        return chat_pb2.DeleteAccountResponse(success=True, message="Account and conversation deleted")

    def SendMessage(self, request, context):
        sender = request.sender
        recipient = request.recipient
        content = request.content
        timestamp = datetime.datetime.now().isoformat()
        
        if recipient not in self.users:
            return chat_pb2.SendMessageResponse(success=False, message="Recipient not found")

        msg_id = self.next_msg_id
        self.next_msg_id += 1

        message_entry = chat_pb2.ChatMessage(
            id=msg_id,
            sender=sender,
            content=content,
            timestamp=timestamp
        )
        conv_key = tuple(sorted([sender, recipient]))
        if conv_key not in self.conversations:
            self.conversations[conv_key] = []
        self.conversations[conv_key].append(message_entry)

        if recipient not in self.active_subscriptions:
            self.users[recipient]["messages"].append(message_entry)
        else:
            try:
                self.active_subscriptions[recipient].put(message_entry)
            except Exception as e:
                print(f"Error forwarding message to {recipient}: {e}")
                self.users[recipient]["messages"].append(message_entry)

        self.save_data()

        # replicate if leader
        data_dict = {
            "sender": sender,
            "recipient": recipient,
            "message_entry": {
                "id": msg_id,
                "sender": sender,
                "content": content,
                "timestamp": timestamp
            }
        }
        self.replicate_to_followers("SEND_MESSAGE", data_dict)

        return chat_pb2.SendMessageResponse(success=True, message="Message sent")

    def ReadMessages(self, request, context):
        username = request.username
        if username not in self.users:
            return chat_pb2.ReadMessagesResponse()

        limit = request.limit
        user_messages = self.users[username]["messages"]
        
        if limit > 0:
            messages_to_view = user_messages[:limit]
            self.users[username]["messages"] = user_messages[limit:]
        else:
            messages_to_view = user_messages
            self.users[username]["messages"] = []

        self.save_data()

        # replicate removal of these messages from unread
        removed_ids = [m.id for m in messages_to_view]
        if removed_ids:
            data_dict = {
                "username": username,
                "message_ids": removed_ids
            }
            self.replicate_to_followers("DELETE_MESSAGES", data_dict)

        return chat_pb2.ReadMessagesResponse(messages=messages_to_view)

    def DeleteMessages(self, request, context):
        username = request.username
        message_ids = request.message_ids

        if username not in self.users:
            return chat_pb2.DeleteMessagesResponse(success=False, message="User not found")

        if not message_ids:
            return chat_pb2.DeleteMessagesResponse(success=False, message="No message IDs provided")

        # check existence
        message_exists = False
        for msg in self.users[username]["messages"]:
            if msg.id in message_ids:
                message_exists = True
                break
        if not message_exists:
            # check conversation history
            for conv_key in self.conversations:
                if username in conv_key:
                    for msg in self.conversations[conv_key]:
                        if msg.id in message_ids:
                            message_exists = True
                            break
                    if message_exists:
                        break

        if not message_exists:
            return chat_pb2.DeleteMessagesResponse(success=False, message="No matching message found to delete")

        # remove from unread
        self.users[username]["messages"] = [m for m in self.users[username]["messages"] if m.id not in message_ids]
        # remove from conversation
        for conv_key in self.conversations:
            if username in conv_key:
                self.conversations[conv_key] = [m for m in self.conversations[conv_key] if m.id not in message_ids]

        self.save_data()

        data_dict = {
            "username": username,
            "message_ids": list(message_ids)
        }
        self.replicate_to_followers("DELETE_MESSAGES", data_dict)

        return chat_pb2.DeleteMessagesResponse(success=True, message="Messages deleted")

    def ViewConversation(self, request, context):
        username = request.username
        other_user = request.other_user

        if other_user not in self.users:
            return chat_pb2.ViewConversationResponse()

        conv_key = tuple(sorted([username, other_user]))
        conversation = self.conversations.get(conv_key, [])

        # remove from unread
        current_unread = self.users[username]["messages"]
        removed_ids = []
        new_unread = []
        for msg in current_unread:
            if msg.sender == other_user:
                removed_ids.append(msg.id)
            else:
                new_unread.append(msg)
        self.users[username]["messages"] = new_unread

        self.save_data()

        if removed_ids:
            data_dict = {
                "username": username,
                "message_ids": removed_ids
            }
            self.replicate_to_followers("DELETE_MESSAGES", data_dict)

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

    def ReplicateMutation(self, request, context):
        import json
        try:
            op_type = request.operation_type
            data = json.loads(request.payload)

            if op_type == "CREATE_ACCOUNT":
                username = data["username"]
                pw_hash = data["password_hash"]
                self.users[username] = {
                    "password_hash": pw_hash,
                    "messages": []
                }

            elif op_type == "SEND_MESSAGE":
                sender = data["sender"]
                recipient = data["recipient"]
                msg_obj = data["message_entry"]
                chatmsg = chat_pb2.ChatMessage(
                    id=msg_obj["id"],
                    sender=msg_obj["sender"],
                    content=msg_obj["content"],
                    timestamp=msg_obj["timestamp"]
                )
                conv_key = tuple(sorted([sender, recipient]))
                if conv_key not in self.conversations:
                    self.conversations[conv_key] = []
                self.conversations[conv_key].append(chatmsg)

                if recipient not in self.active_subscriptions:
                    self.users[recipient]["messages"].append(chatmsg)
                else:
                    try:
                        self.active_subscriptions[recipient].put(chatmsg)
                    except:
                        self.users[recipient]["messages"].append(chatmsg)

            elif op_type == "DELETE_ACCOUNT":
                username = data["username"]
                if username in self.users:
                    del self.users[username]
                if username in self.active_subscriptions:
                    del self.active_subscriptions[username]
                keys_to_delete = [k for k in self.conversations if username in k]
                for k in keys_to_delete:
                    del self.conversations[k]

            elif op_type == "DELETE_MESSAGES":
                username = data["username"]
                msg_ids = data["message_ids"]
                self.users[username]["messages"] = [
                    m for m in self.users[username]["messages"] if m.id not in msg_ids
                ]
                for ckey in self.conversations:
                    if username in ckey:
                        self.conversations[ckey] = [
                            m for m in self.conversations[ckey] if m.id not in msg_ids
                        ]

            self.save_data()
            return chat_pb2.ReplicateMutationResponse(success=True, message="Replication applied")

        except Exception as e:
            return chat_pb2.ReplicateMutationResponse(success=False, message=str(e))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json", help="Path to the config file")
    return parser.parse_args()

def load_config(config_path):
    with open(config_path, "r") as f:
        return json.load(f)

def serve():
    try:
        args = parse_args()
        config = load_config(args.config)

        server_id = config["server_id"]
        listen_port = config["listen_port"]
        replicas = config["replicas"]

        service = ChatServiceServicer(server_id=server_id, replicas=replicas)

        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        chat_pb2_grpc.add_ChatServiceServicer_to_server(service, server)
        server.add_insecure_port(f'[::]:{listen_port}')
        server.start()
        print(f"Server #{server_id} started on port {listen_port}")

        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)
        print(f"Server #{server_id} stopped")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Caught top-level exception: {e}")

if __name__ == '__main__':
    serve()
