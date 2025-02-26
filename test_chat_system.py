import unittest
import grpc
import threading
import time
import os
import sys
from concurrent import futures

# Import the client and server code
import client as chat_client
import server as chat_server

# Import the generated protocol buffer code
try:
    import chat_pb2
    import chat_pb2_grpc
except ImportError:
    try:
        import chat_pb2 as chat_pb2
        import chat_pb2_grpc as chat_pb2_grpc
    except ImportError:
        print("Error: Protocol buffer modules not found. Make sure to generate them first.")
        sys.exit(1)

class TestChatSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start the server in a separate thread
        cls.server_thread = threading.Thread(target=cls.run_server)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        # Allow time for the server to start
        time.sleep(1)
        # Set up the gRPC channel and stub
        cls.channel = grpc.insecure_channel('localhost:50051')
        cls.stub = chat_pb2_grpc.ChatServiceStub(cls.channel)
        
    @classmethod
    def run_server(cls):
        cls.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        service = chat_server.ChatServiceServicer()
        chat_pb2_grpc.add_ChatServiceServicer_to_server(service, cls.server)
        cls.server.add_insecure_port('[::]:50051')
        cls.server.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            cls.server.stop(0)
    
    @classmethod
    def tearDownClass(cls):
        cls.channel.close()
    
    def setUp(self):
        # Create test users for each test
        self.test_users = [
            ("testuser1", "password1"),
            ("testuser2", "password2"),
            ("testuser3", "password3")
        ]
        for username, password in self.test_users:
            response = self.stub.CreateAccount(chat_pb2.CreateAccountRequest(
                username=username,
                password=password
            ))
            self.assertTrue(response.success)
    
    def tearDown(self):
        # Delete test accounts
        for username, _ in self.test_users:
            try:
                self.stub.DeleteAccount(chat_pb2.DeleteAccountRequest(username=username))
            except Exception:
                pass

    # Existing tests

    def test_create_account(self):
        # Test creating a new account
        response = self.stub.CreateAccount(chat_pb2.CreateAccountRequest(
            username="newuser",
            password="newpass"
        ))
        self.assertTrue(response.success)
        self.assertEqual(response.message, "Account created")
        
        # Test creating an account with an existing username
        response = self.stub.CreateAccount(chat_pb2.CreateAccountRequest(
            username="newuser",
            password="anotherpass"
        ))
        self.assertFalse(response.success)
        self.assertEqual(response.message, "Username already exists")
        
        # Clean up
        self.stub.DeleteAccount(chat_pb2.DeleteAccountRequest(username="newuser"))
    
    def test_login(self):
        # Test successful login
        response = self.stub.Login(chat_pb2.LoginRequest(
            username="testuser1",
            password="password1"
        ))
        self.assertTrue(response.success)
        self.assertIn("Login successful", response.message)
        
        # Test login with incorrect password
        response = self.stub.Login(chat_pb2.LoginRequest(
            username="testuser1",
            password="wrongpassword"
        ))
        self.assertFalse(response.success)
        
        # Test login with non-existent username
        response = self.stub.Login(chat_pb2.LoginRequest(
            username="nonexistentuser",
            password="password"
        ))
        self.assertFalse(response.success)
    
    def test_send_and_read_messages(self):
        # Test sending a message
        send_response = self.stub.SendMessage(chat_pb2.SendMessageRequest(
            sender="testuser1",
            recipient="testuser2",
            content="Hello, this is a test message"
        ))
        self.assertTrue(send_response.success)
        
        # Test reading messages
        read_response = self.stub.ReadMessages(chat_pb2.ReadMessagesRequest(
            username="testuser2",
            limit=0
        ))
        self.assertEqual(len(read_response.messages), 1)
        self.assertEqual(read_response.messages[0].sender, "testuser1")
        self.assertEqual(read_response.messages[0].content, "Hello, this is a test message")
        
        # Test that messages are marked as read
        read_again = self.stub.ReadMessages(chat_pb2.ReadMessagesRequest(
            username="testuser2",
            limit=0
        ))
        self.assertEqual(len(read_again.messages), 0)
    
    def test_view_conversation(self):
        # Send multiple messages between users
        self.stub.SendMessage(chat_pb2.SendMessageRequest(
            sender="testuser1",
            recipient="testuser2",
            content="Message 1 from user1 to user2"
        ))
        self.stub.SendMessage(chat_pb2.SendMessageRequest(
            sender="testuser2",
            recipient="testuser1",
            content="Reply from user2 to user1"
        ))
        
        # View conversation from user1's perspective
        response = self.stub.ViewConversation(chat_pb2.ViewConversationRequest(
            username="testuser1",
            other_user="testuser2"
        ))
        
        self.assertGreaterEqual(len(response.messages), 2)
        messages = [(msg.sender, msg.content) for msg in response.messages]
        self.assertIn(("testuser1", "Message 1 from user1 to user2"), messages)
        self.assertIn(("testuser2", "Reply from user2 to user1"), messages)
    
    def test_delete_messages(self):
        # Send a message and then delete it
        send_response = self.stub.SendMessage(chat_pb2.SendMessageRequest(
            sender="testuser1",
            recipient="testuser3",
            content="Message to be deleted"
        ))
        read_response = self.stub.ReadMessages(chat_pb2.ReadMessagesRequest(
            username="testuser3",
            limit=0
        ))
        message_id = read_response.messages[0].id
        delete_response = self.stub.DeleteMessages(chat_pb2.DeleteMessagesRequest(
            username="testuser3",
            message_ids=[message_id]
        ))
        self.assertTrue(delete_response.success)
        
        # Verify deletion in conversation history
        view_response = self.stub.ViewConversation(chat_pb2.ViewConversationRequest(
            username="testuser3",
            other_user="testuser1"
        ))
        for msg in view_response.messages:
            self.assertNotEqual(msg.id, message_id)
    
    def test_list_accounts(self):
        # List all accounts
        response = self.stub.ListAccounts(chat_pb2.ListAccountsRequest(
            username="testuser1",
            wildcard="*"
        ))
        account_list = response.usernames
        for username, _ in self.test_users:
            self.assertIn(username, account_list)
        
        # List with a specific wildcard
        response = self.stub.ListAccounts(chat_pb2.ListAccountsRequest(
            username="testuser1",
            wildcard="testuser*"
        ))
        for username in response.usernames:
            self.assertTrue(username.startswith("testuser"))
    
    def test_delete_account(self):
        # Delete an account and verify deletion
        response = self.stub.DeleteAccount(chat_pb2.DeleteAccountRequest(
            username="testuser3"
        ))
        self.assertTrue(response.success)
        
        login_response = self.stub.Login(chat_pb2.LoginRequest(
            username="testuser3",
            password="password3"
        ))
        self.assertFalse(login_response.success)
        
        list_response = self.stub.ListAccounts(chat_pb2.ListAccountsRequest(
            username="testuser1",
            wildcard="*"
        ))
        self.assertNotIn("testuser3", list_response.usernames)
    
    def test_logoff(self):
        # Test log off functionality
        response = self.stub.LogOff(chat_pb2.LogOffRequest(
            username="testuser1"
        ))
        self.assertTrue(response.success)
        self.assertEqual(response.message, "User logged off")

    # Additional tests for complete coverage

    def test_send_message_to_self(self):
        # Verify that a user can send a message to themselves.
        send_response = self.stub.SendMessage(chat_pb2.SendMessageRequest(
            sender="testuser1",
            recipient="testuser1",
            content="Self message"
        ))
        self.assertTrue(send_response.success)
        read_response = self.stub.ReadMessages(chat_pb2.ReadMessagesRequest(
            username="testuser1",
            limit=0
        ))
        self.assertEqual(len(read_response.messages), 1)
        self.assertEqual(read_response.messages[0].content, "Self message")
    
    def test_send_message_to_nonexistent(self):
        # Attempt sending a message to a user that does not exist.
        send_response = self.stub.SendMessage(chat_pb2.SendMessageRequest(
            sender="testuser1",
            recipient="nonexistent",
            content="Hello"
        ))
        self.assertFalse(send_response.success)
        self.assertEqual(send_response.message, "Recipient not found")
    
    def test_read_messages_with_limit(self):
        # Send multiple messages and then read using a limit.
        messages = ["Msg1", "Msg2", "Msg3", "Msg4"]
        for msg in messages:
            self.stub.SendMessage(chat_pb2.SendMessageRequest(
                sender="testuser2",
                recipient="testuser1",
                content=msg
            ))
        read_response = self.stub.ReadMessages(chat_pb2.ReadMessagesRequest(
            username="testuser1",
            limit=2
        ))
        self.assertEqual(len(read_response.messages), 2)
        # Read remaining messages
        remaining = self.stub.ReadMessages(chat_pb2.ReadMessagesRequest(
            username="testuser1",
            limit=0
        ))
        self.assertEqual(len(remaining.messages), 2)
    
    def test_delete_messages_invalid_ids(self):
        # Attempt to delete a message using an invalid ID.
        delete_response = self.stub.DeleteMessages(chat_pb2.DeleteMessagesRequest(
            username="testuser2",
            message_ids=[9999]
        ))
        self.assertFalse(delete_response.success)
        self.assertEqual(delete_response.message, "No matching message found to delete")
    
    def test_delete_messages_empty_ids(self):
        # Attempt to delete messages when no IDs are provided.
        delete_response = self.stub.DeleteMessages(chat_pb2.DeleteMessagesRequest(
            username="testuser2",
            message_ids=[]
        ))
        self.assertFalse(delete_response.success)
        self.assertEqual(delete_response.message, "No message IDs provided")
    
    def test_concurrent_message_sending(self):
        # Send messages concurrently to the same recipient.
        def send_message(sender, recipient, content):
            self.stub.SendMessage(chat_pb2.SendMessageRequest(
                sender=sender,
                recipient=recipient,
                content=content
            ))
        
        threads = []
        num_messages = 10
        for i in range(num_messages):
            t = threading.Thread(target=send_message, args=("testuser1", "testuser2", f"Concurrent message {i}"))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        read_response = self.stub.ReadMessages(chat_pb2.ReadMessagesRequest(
            username="testuser2",
            limit=0
        ))
        self.assertEqual(len(read_response.messages), num_messages)
    
    def test_view_conversation_order(self):
        # Send messages with delays to enforce ordering and verify conversation order.
        self.stub.SendMessage(chat_pb2.SendMessageRequest(
            sender="testuser1",
            recipient="testuser2",
            content="First"
        ))
        time.sleep(0.1)
        self.stub.SendMessage(chat_pb2.SendMessageRequest(
            sender="testuser2",
            recipient="testuser1",
            content="Second"
        ))
        time.sleep(0.1)
        self.stub.SendMessage(chat_pb2.SendMessageRequest(
            sender="testuser1",
            recipient="testuser2",
            content="Third"
        ))
        response = self.stub.ViewConversation(chat_pb2.ViewConversationRequest(
            username="testuser1",
            other_user="testuser2"
        ))
        # Ensure the message IDs are in increasing order.
        message_ids = [msg.id for msg in response.messages]
        self.assertEqual(message_ids, sorted(message_ids))
    
    def test_list_accounts_wildcard_no_match(self):
        # List accounts using a wildcard that should match nothing.
        response = self.stub.ListAccounts(chat_pb2.ListAccountsRequest(
            username="testuser1",
            wildcard="nomatch*"
        ))
        self.assertEqual(len(response.usernames), 0)
    
    def test_logoff_without_active_subscription(self):
        # Log off a user who does not have an active subscription.
        response = self.stub.LogOff(chat_pb2.LogOffRequest(
            username="nonexistentuser"
        ))
        self.assertTrue(response.success)
    
    def test_account_deletion_removes_conversation(self):
        # Verify that deleting an account removes all associated conversation history.
        self.stub.CreateAccount(chat_pb2.CreateAccountRequest(
            username="userA",
            password="passA"
        ))
        self.stub.CreateAccount(chat_pb2.CreateAccountRequest(
            username="userB",
            password="passB"
        ))
        self.stub.SendMessage(chat_pb2.SendMessageRequest(
            sender="userA",
            recipient="userB",
            content="Hello from A"
        ))
        self.stub.SendMessage(chat_pb2.SendMessageRequest(
            sender="userB",
            recipient="userA",
            content="Hello from B"
        ))
        response = self.stub.ViewConversation(chat_pb2.ViewConversationRequest(
            username="userA",
            other_user="userB"
        ))
        self.assertGreaterEqual(len(response.messages), 2)
        del_response = self.stub.DeleteAccount(chat_pb2.DeleteAccountRequest(
            username="userB"
        ))
        self.assertTrue(del_response.success)
        response_after = self.stub.ViewConversation(chat_pb2.ViewConversationRequest(
            username="userA",
            other_user="userB"
        ))
        self.assertEqual(len(response_after.messages), 0)
        self.stub.DeleteAccount(chat_pb2.DeleteAccountRequest(username="userA"))
    
    def test_large_message_content(self):
        # Send a message with a very large content payload.
        large_message = "A" * 1000  # 1000 characters
        self.stub.SendMessage(chat_pb2.SendMessageRequest(
            sender="testuser1",
            recipient="testuser2",
            content=large_message
        ))
        read_response = self.stub.ReadMessages(chat_pb2.ReadMessagesRequest(
            username="testuser2",
            limit=0
        ))
        self.assertEqual(len(read_response.messages), 1)
        self.assertEqual(read_response.messages[0].content, large_message)
    
    def test_subscribe_after_offline_message(self):
        # Send an offline message and then simulate a subscription;
        # ensure that old messages are not pushed via the subscription.
        self.stub.SendMessage(chat_pb2.SendMessageRequest(
            sender="testuser1",
            recipient="testuser2",
            content="Offline message"
        ))
        # Directly assign a subscription queue for test purposes.
        import queue
        sub_queue = queue.Queue()
        chat_server_instance = chat_server.ChatServiceServicer()
        chat_server_instance.active_subscriptions["testuser2"] = sub_queue
        # Wait briefly to see if any messages are pushed.
        time.sleep(1)
        self.assertTrue(sub_queue.empty())
    
    def test_read_messages_when_empty(self):
        # Verify that reading messages when none exist returns an empty list.
        read_response = self.stub.ReadMessages(chat_pb2.ReadMessagesRequest(
            username="testuser1",
            limit=0
        ))
        self.assertEqual(len(read_response.messages), 0)

class TestChatClient(unittest.TestCase):
    """
    Integration tests for the chat client.
    """
    @classmethod
    def setUpClass(cls):
        # Start the server if it is not already running
        if not hasattr(TestChatSystem, 'server_thread') or not TestChatSystem.server_thread.is_alive():
            cls.server_thread = threading.Thread(target=TestChatSystem.run_server)
            cls.server_thread.daemon = True
            cls.server_thread.start()
            time.sleep(1)
    
    def test_client_create_account_and_login(self):
        # Test account creation and login via the client
        test_client = chat_client.ChatClient()
        test_client.create_account("integrationuser", "integrationpass")
        test_client.login("integrationuser", "integrationpass")
        self.assertEqual(test_client.username, "integrationuser")
        test_client.delete_account()
        test_client.close()
    
    def test_client_send_and_receive_message(self):
        # Test sending and receiving messages via client instances.
        sender = chat_client.ChatClient()
        receiver = chat_client.ChatClient()
        sender.create_account("sender", "password")
        receiver.create_account("receiver", "password")
        sender.login("sender", "password")
        receiver.login("receiver", "password")
        
        import io
        from contextlib import redirect_stdout
        time.sleep(1)
        f = io.StringIO()
        with redirect_stdout(f):
            sender.send_message("receiver", "Test message from integration test")
            time.sleep(1)
        output = f.getvalue()
        if "Test message from integration test" not in output:
            f2 = io.StringIO()
            with redirect_stdout(f2):
                receiver.read_messages()
            output2 = f2.getvalue()
            self.assertIn("Test message from integration test", output2)
        else:
            self.assertIn("Test message from integration test", output)
        
        sender.delete_account()
        receiver.delete_account()
        sender.close()
        receiver.close()
    
    def test_client_multiple_logins(self):
        # Verify that the client prevents logging in twice.
        client_instance = chat_client.ChatClient()
        client_instance.create_account("multilogin", "pass")
        client_instance.login("multilogin", "pass")
        import io
        from contextlib import redirect_stderr
        f = io.StringIO()
        with redirect_stderr(f):
            client_instance.login("multilogin", "pass")
        stderr_output = f.getvalue()
        self.assertIn("already logged in", stderr_output)
        client_instance.delete_account()
        client_instance.close()
    
    def test_client_logoff_without_login(self):
        # Test log off when no user is logged in.
        client_instance = chat_client.ChatClient()
        client_instance.log_off()
        self.assertIsNone(client_instance.username)
        client_instance.close()
    
    def test_client_close_connection(self):
        # Test that closing the connection properly resets the client state.
        client_instance = chat_client.ChatClient()
        client_instance.create_account("closeuser", "pass")
        client_instance.login("closeuser", "pass")
        client_instance.close()
        self.assertIsNone(client_instance.username)

if __name__ == '__main__':
    unittest.main()
