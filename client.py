import grpc
import chatservice_pb2
import chatservice_pb2_grpc
from google.protobuf.empty_pb2 import Empty

import sys
import threading
import time

class ChatClient:
    def __init__(self, username, on_message_callback=None):
        self.channel = grpc.insecure_channel('localhost:50051')
        self.stub = chatservice_pb2_grpc.ChatServiceStub(self.channel)
        self.username = username
        self.stop_event = threading.Event()
        self.receive_thread = None
        self.heartbeat_thread = None
        self.input_buffer = ""
        self.on_message_callback = on_message_callback
        self.connected = False
        self.is_closing = False

    def send_message(self, message):
        try:
            message_request = chatservice_pb2.MessageRequest(username=self.username, message=message)
            response = self.stub.SendMessage(message_request)
            
            # Check if server responded with an error about not being connected
            if response.username == "System" and "not connected" in response.message.lower():
                self.connected = False
                if self.on_message_callback:
                    self.on_message_callback("System", "You are not connected to the server.")
                return False
                
            return True
        except grpc.RpcError:
            self.connected = False
            if self.on_message_callback and not self.is_closing:
                self.on_message_callback("System", "Server error. Cannot send message.")
            return False

    def send_heartbeat(self):
        """Send periodic heartbeats to server"""
        while not self.stop_event.is_set():
            try:
                if self.connected and not self.is_closing:
                    message_request = chatservice_pb2.MessageRequest(username=self.username, message="")
                    metadata = [('message-type', 'heartbeat')]
                    response = self.stub.SendMessage(message_request, metadata=metadata)
                    
                    # Check if server indicates we're not connected
                    if "ERROR:" in response.message:
                        self.connected = False
                        if self.on_message_callback:
                            self.on_message_callback("System", "Connection to server lost")
                        break
            except grpc.RpcError:
                # If we can't send heartbeats, the connection might be down
                if not self.is_closing and self.connected:
                    self.connected = False
                    if self.on_message_callback:
                        self.on_message_callback("System", "Connection to server lost")
                break

            time.sleep(15)  # Send heartbeat every 15 seconds

    def receive_messages(self):
        try:
            for message in self.stub.ChatStream(Empty()):
                if self.stop_event.is_set():
                    break
                
                if message.username != "System" or "ERROR:" in message.message:
                    if self.on_message_callback:
                        self.on_message_callback(message.username, message.message)
        except grpc.RpcError:
            if not self.is_closing and self.connected:
                self.connected = False
                if self.on_message_callback:
                    self.on_message_callback("System", "Connection to server lost")

    def start_chat(self):
        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()

        self.heartbeat_thread = threading.Thread(target=self.send_heartbeat)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        
        try:
            while True:
                self.input_buffer = input("> ")
                
                if self.input_buffer.lower() == 'quit':
                    print("\nExiting chat")
                    break
                
                if self.input_buffer.strip():
                    self.send_message(self.input_buffer)
                self.input_buffer = ""

        except KeyboardInterrupt:
            print("\nExiting chat")
        finally:
            self.stop_event.set()
            self.channel.close()

    def check_username_available(self):
        try:
            connect_request = chatservice_pb2.MessageRequest(username=self.username, message="")

            metadata = [('message-type', 'connect')]
            response = self.stub.SendMessage(connect_request, metadata=metadata)

            if response.message.startswith("SUCCESS"):
                self.connected = True
                self.heartbeat_thread = threading.Thread(target=self.send_heartbeat)
                self.heartbeat_thread.daemon = True
                self.heartbeat_thread.start()
                return True
            return False
        except grpc.RpcError as e:
            status_code = e.code()
            if status_code == grpc.StatusCode.UNAVAILABLE:
                raise ConnectionError("Chat server is unavailable")
            return False
    
    def disconnect(self):
        if self.connected:
            try:
                disconnect_request = chatservice_pb2.MessageRequest(username=self.username, message="")
                metadata = [('message-type', 'disconnect')]

                self.stub.SendMessage(disconnect_request, metadata=metadata)
            except grpc.RpcError:
                pass
            finally:
                self.connected = False

    def close(self):
        self.is_closing = True
        self.stop_event.set()
        try:
            self.disconnect()
        except Exception:
            pass
        try:
            self.channel.close()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        username = input("Enter your username: ")
        client = ChatClient(username)

        if client.check_username_available():
            print('Welcome!')
            client.start_chat()
        else:
            print('Username is already taken.')
            client.close()
    except KeyboardInterrupt:
        print("\nChat client terminated.")
        client.disconnect()
        sys.exit(0)