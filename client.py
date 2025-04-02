import grpc
import chatservice_pb2
import chatservice_pb2_grpc
from google.protobuf.empty_pb2 import Empty

import sys
import threading

class ChatClient:
    def __init__(self, username, on_message_callback=None):
        self.channel = grpc.insecure_channel('localhost:50051')
        self.stub = chatservice_pb2_grpc.ChatServiceStub(self.channel)
        self.username = username
        self.stop_event = threading.Event()
        self.receive_thread = None
        self.input_buffer = ""
        self.on_message_callback = on_message_callback
        self.connected = False

    def send_message(self, message):
        message_request = chatservice_pb2.MessageRequest(username=self.username, message=message)
        self.stub.SendMessage(message_request)

    def receive_messages(self):
        try:
            for message in self.stub.ChatStream(Empty()):
                if self.stop_event.is_set():
                    break
                
                # sys.stdout.write('\r' + ' ' * (len(self.input_buffer) + 2))
                # sys.stdout.write('\r')

                # if message.username == self.username:
                #     sys.stdout.write(f"You: {message.message}\n")
                # else:
                #     sys.stdout.write(f"{message.username}: {message.message}\n")
                    
                # #print(f"\r{message.username}: {message.message}")
                # #print("> ", end='', flush=True)

                # sys.stdout.write(f"> {self.input_buffer}")
                # sys.stdout.flush()

                if self.on_message_callback:
                    self.on_message_callback(message.username, message.message)
        except grpc.RpcError:
            if self.on_message_callback:
                self.on_message_callback("System", "Connection to server lost")

    def start_chat(self):
        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.daemon = True
        receive_thread.start()
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
            # sys.exit(0)

    def check_username_available(self):
        try:
            connect_request = chatservice_pb2.MessageRequest(username=self.username, message="")

            metadata = [('message-type', 'connect')]
            response = self.stub.SendMessage(connect_request, metadata=metadata)

            if response.message.startswith("SUCCESS"):
                self.connected = True
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
                self.connected = False
            except grpc.RpcError:
                pass
            finally:
                self.connected = False

    def close(self):
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