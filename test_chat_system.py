# test_chat_system.py
import unittest
import grpc
import threading
import time
import os
import sys
from concurrent import futures

# Import the client and server code
# Assuming your files are named client.py and server.py
import client as chat_client
import server as chat_server

# Import the generated protocol buffer code
# Update these imports if needed based on your generated files
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
        
        # Set up the client stub for direct API testing
        cls.channel = grpc.insecure_channel('localhost:50051')
        cls.stub = chat_pb2_grpc.ChatServiceStub(cls.channel)
        
    @classmethod
    def run_server(cls):
        # Create a server instance
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
        # Clean up the channel
        cls.channel.close()
        
    def setUp(self):
        # Create test users for each test
        self.test_users = [
            ("testuser1", "password1"),
            ("testuser2", "password2"),
            ("testuser3", "password3")
        ]
        
        # Create the test accounts
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
                self.stub.DeleteAccount(chat_pb2.DeleteAccountRequest(
                    username=username
                ))
            except:
                pass
    
    def test_create_account(self):
        # Test creating a new account
        response = self.stub.CreateAccount(chat_pb2.CreateAccountRequest(
            username="newuser",
            password="newpass"
        ))
        self.assertTrue(response.success)
        self.assertEqual(response.message, "Account created")
        
        # Test creating an account with existing username
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
        
        # Here we don't hardcode the expected number of messages because the server implementation
        # might include previous test messages in the conversation history.
        # Instead, we just verify the specific messages we sent are present
        self.assertGreaterEqual(len(response.messages), 2)
        
        # Extract the sender-content pairs for easier verification
        messages = [(msg.sender, msg.content) for msg in response.messages]
        self.assertIn(("testuser1", "Message 1 from user1 to user2"), messages)
        self.assertIn(("testuser2", "Reply from user2 to user1"), messages)
    
    def test_delete_messages(self):
        # Send a message
        send_response = self.stub.SendMessage(chat_pb2.SendMessageRequest(
            sender="testuser1",
            recipient="testuser3",
            content="Message to be deleted"
        ))
        
        # Read the message to get its ID
        read_response = self.stub.ReadMessages(chat_pb2.ReadMessagesRequest(
            username="testuser3",
            limit=0
        ))
        
        message_id = read_response.messages[0].id
        
        # Delete the message
        delete_response = self.stub.DeleteMessages(chat_pb2.DeleteMessagesRequest(
            username="testuser3",
            message_ids=[message_id]
        ))
        
        self.assertTrue(delete_response.success)
        
        # View conversation to confirm deletion
        view_response = self.stub.ViewConversation(chat_pb2.ViewConversationRequest(
            username="testuser3",
            other_user="testuser1"
        ))
        
        # Check specifically for the deleted message
        for msg in view_response.messages:
            self.assertNotEqual(msg.id, message_id)
    
    def test_list_accounts(self):
        # Test listing all accounts
        response = self.stub.ListAccounts(chat_pb2.ListAccountsRequest(
            username="testuser1",
            wildcard="*"
        ))
        
        account_list = response.usernames
        for username, _ in self.test_users:
            self.assertIn(username, account_list)
        
        # Test listing with wildcard
        response = self.stub.ListAccounts(chat_pb2.ListAccountsRequest(
            username="testuser1",
            wildcard="testuser*"
        ))
        
        for username in response.usernames:
            self.assertTrue(username.startswith("testuser"))
    
    def test_delete_account(self):
        # Delete an account
        response = self.stub.DeleteAccount(chat_pb2.DeleteAccountRequest(
            username="testuser3"
        ))
        
        self.assertTrue(response.success)
        
        # Verify the account is gone by trying to log in
        login_response = self.stub.Login(chat_pb2.LoginRequest(
            username="testuser3",
            password="password3"
        ))
        
        self.assertFalse(login_response.success)
        
        # Also verify by listing accounts
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

class TestChatClient(unittest.TestCase):
    """
    Integration tests for the chat client.
    These tests verify that the client can interact with the server correctly.
    """
    
    @classmethod
    def setUpClass(cls):
        # Start the server in a separate thread if it's not already running
        if not hasattr(TestChatSystem, 'server_thread') or not TestChatSystem.server_thread.is_alive():
            cls.server_thread = threading.Thread(target=TestChatSystem.run_server)
            cls.server_thread.daemon = True
            cls.server_thread.start()
            time.sleep(1)  # Give server time to start
    
    def test_client_create_account_and_login(self):
        # Create a client instance
        test_client = chat_client.ChatClient()
        
        # Create a test account
        test_client.create_account("integrationuser", "integrationpass")
        
        # Login with the account
        test_client.login("integrationuser", "integrationpass")
        
        # Verify successful login
        self.assertEqual(test_client.username, "integrationuser")
        
        # Clean up
        test_client.delete_account()
        test_client.close()
    
    def test_client_send_and_receive_message(self):
        # Create two client instances
        sender = chat_client.ChatClient()
        receiver = chat_client.ChatClient()
        
        # Create test accounts and login
        sender.create_account("sender", "password")
        receiver.create_account("receiver", "password")
        
        sender.login("sender", "password")
        receiver.login("receiver", "password")
        
        # Capture stdout to verify message reception in streaming
        # This is more reliable than checking read_messages output
        import io
        from contextlib import redirect_stdout
        
        # Setup the streaming thread for receiver
        # Wait briefly for streaming to initialize
        time.sleep(1)
        
        # Send a message
        f = io.StringIO()
        with redirect_stdout(f):
            sender.send_message("receiver", "Test message from integration test")
            # Wait for the streaming thread to receive the message
            time.sleep(1)
        
        # Check the message was delivered via subscription stream
        output = f.getvalue()
        
        # If streaming doesn't work or output doesn't show reception,
        # check via direct message reading
        if "Test message from integration test" not in output:
            # Try reading messages directly
            f2 = io.StringIO()
            with redirect_stdout(f2):
                receiver.read_messages()
            
            output2 = f2.getvalue()
            self.assertIn("Test message from integration test", output2)
        else:
            self.assertIn("Test message from integration test", output)
        
        # Clean up
        sender.delete_account()
        receiver.delete_account()
        sender.close()
        receiver.close()

if __name__ == '__main__':
    unittest.main()