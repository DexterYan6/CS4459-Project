import grpc
import chatservice_pb2
import chatservice_pb2_grpc
from google.protobuf.empty_pb2 import Empty

import sys
import threading

class ChatClient:
    def __init__(self, username):
        self.channel = grpc.insecure_channel('localhost:50051')
        self.stub = chatservice_pb2_grpc.ChatServiceStub(self.channel)
        self.username = username
        self.stop_event = threading.Event()
        self.receive_thread = None
        self.input_buffer = ""

    def send_message(self, message):
        message_request = chatservice_pb2.MessageRequest(username=self.username, message=message)
        self.stub.SendMessage(message_request)

    def receive_messages(self):
        try:
            for message in self.stub.ChatStream(Empty()):
                if self.stop_event.is_set():
                    break
                
                sys.stdout.write('\r' + ' ' * (len(self.input_buffer) + 2))
                sys.stdout.write('\r')
                print(f"{message.username}: {message.message}")
 
                sys.stdout.write(f"> {self.input_buffer}")
                sys.stdout.flush()
        except grpc.RpcError as e:
            print("Connection to server lost" + str(e))

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

if __name__ == "__main__":
    try:
        username = input("Enter your username: ")
        client = ChatClient(username)
        client.start_chat()
    except KeyboardInterrupt:
        print("\nChat client terminated.")
        sys.exit(0)