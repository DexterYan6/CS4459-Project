import grpc
import chatservice_pb2
import chatservice_pb2_grpc

from concurrent import futures
from pymongo import MongoClient
import time

class ChatService(chatservice_pb2_grpc.ChatServiceServicer):
    def __init__(self):
        # initialize mongodb service, currently on local
        self.mongo_client = MongoClient('localhost', 27017)
        self.db = self.mongo_client.chat_db
        self.connected_users = set()

    def ChatStream(self, request_iterator, context):
        lastindex = 0

        while True:
            while len(self.get_chat_history()) > lastindex:
                message = self.get_chat_history()[lastindex]
                lastindex += 1
                yield message

    def SendMessage(self, request, context):
        metadata = dict(context.invocation_metadata())
        message_type = metadata.get('message-type', 'chat')
       
        # Handle connection request
        if message_type == 'connect':
            if request.username in self.connected_users:
                # Username is taken, return error message
                return chatservice_pb2.MessageResponse(
                    username="System",
                    message=f"ERROR: Username '{request.username}' is already taken."
                )
            else:
                # Register the username and return success
                self.connected_users.add(request.username)
                return chatservice_pb2.MessageResponse(
                    username="System",
                    message=f"SUCCESS: Connected as '{request.username}'."
                )
       
        # Handle disconnection request
        if message_type == 'disconnect':
            if request.username in self.connected_users:
                self.connected_users.remove(request.username)
            return chatservice_pb2.MessageResponse(
                username="System",
                message=f"User '{request.username}' has disconnected."
            )
       
        self.save_history(request)
        print(f"{request.username}: {request.message}")

        return chatservice_pb2.MessageResponse(username=request.username, message=request.message)

    def save_history(self, request):
        #mongodb insert
        message_doc = {
            'message': request.message,
            'user': request.username,
        }

        self.db.messages.insert_one(message_doc)
        print(message_doc)

    def get_chat_history(self):
        chat_history = self.db.messages.find()

        message_list = [chatservice_pb2.MessageResponse(
            username=message['user'],
            message=message['message'],
        ) for message in chat_history]

        return message_list

    def print_previous_history(self):
        previous_history = self.get_chat_history()
        print("Previous Chat History:")
        for message in previous_history:
            print(f"{message.username}: {message.message}")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_service = ChatService()
    chatservice_pb2_grpc.add_ChatServiceServicer_to_server(chat_service, server)
    server.add_insecure_port('[::]:50051')
    server.start()

    # chat_service.print_previous_history()

    print("Server started")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        print("\nClosing server")
        server.stop(0)


if __name__ == '__main__':
    serve()