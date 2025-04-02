import grpc
import chatservice_pb2
import chatservice_pb2_grpc

from concurrent import futures
from pymongo import MongoClient
import time
import threading

class ChatService(chatservice_pb2_grpc.ChatServiceServicer):
    def __init__(self):
        # initialize mongodb service, currently on local
        self.mongo_client = MongoClient('localhost', 27017)
        self.db = self.mongo_client.chat_db
        self.connected_users = {}  # Dictionary to store user data
        self.lock = threading.Lock()  # Add lock for thread safety

        # Start the heartbeat checking thread
        self.heartbeat_thread = threading.Thread(target=self._check_heartbeats, daemon=True)
        self.heartbeat_thread.start()

    def _check_heartbeats(self):
        HEARTBEAT_TIMEOUT = 15  
        
        while True:
            current_time = time.time()
            users_to_remove = []
            
            with self.lock:
                for username, user_data in self.connected_users.items():
                    last_heartbeat = user_data.get('last_heartbeat', 0)
                    if current_time - last_heartbeat > HEARTBEAT_TIMEOUT:
                        users_to_remove.append(username)
            
            # Remove disconnected users
            for username in users_to_remove:
                with self.lock:
                    if username in self.connected_users:
                        del self.connected_users[username]
                        print(f"Removed inactive user: {username}")

    def ChatStream(self, request_iterator, context):
        lastindex = 0

        while True:
            while len(self.get_chat_history()) > lastindex:
                message = self.get_chat_history()[lastindex]
                lastindex += 1
                yield message
            time.sleep(0.1)

    def SendMessage(self, request, context):
        metadata = dict(context.invocation_metadata())
        message_type = metadata.get('message-type', 'chat')
        
        # Handle heartbeat message
        if message_type == 'heartbeat':
            with self.lock:
                if request.username in self.connected_users:
                    self.connected_users[request.username]['last_heartbeat'] = time.time()
                    return chatservice_pb2.MessageResponse(
                        username="System",
                        message="Heartbeat acknowledged"
                    )
                else:
                    # Username not found, might have been timed out
                    return chatservice_pb2.MessageResponse(
                        username="System",
                        message="ERROR: Not connected"
                    )
        
        # Handle connection request
        if message_type == 'connect':
            with self.lock:
                if request.username in self.connected_users:
                    # Username is taken, return error message
                    return chatservice_pb2.MessageResponse(
                        username="System",
                        message=f"ERROR: Username '{request.username}' is already taken."
                    )
                else:
                    # Register the username and return success
                    self.connected_users[request.username] = {
                        'last_heartbeat': time.time()
                    }
                    print(f"User connected: {request.username}")
                    return chatservice_pb2.MessageResponse(
                        username="System",
                        message=f"SUCCESS: Connected as '{request.username}'."
                    )
       
        # Handle disconnection request
        if message_type == 'disconnect':
            with self.lock:
                if request.username in self.connected_users:
                    del self.connected_users[request.username]
                    print(f"User disconnected: {request.username}")
            
            return chatservice_pb2.MessageResponse(
                username="System",
                message=f"User '{request.username}' has disconnected."
            )
       
        # For normal chat messages, verify user is connected
        with self.lock:
            if request.username not in self.connected_users:
                # If the user isn't connected, reject the message
                return chatservice_pb2.MessageResponse(
                    username="System",
                    message="ERROR: Not connected"
                )
            
            # Update the heartbeat time for the user
            self.connected_users[request.username]['last_heartbeat'] = time.time()
       
        # Process the message
        self.save_history(request)
        print(f"{request.username}: {request.message}")

        return chatservice_pb2.MessageResponse(username=request.username, message=request.message)

    def save_history(self, request):
        # Only save user messages, not system messages
        if request.username != "System":
            message_doc = {
                'message': request.message,
                'user': request.username,
            }
            self.db.messages.insert_one(message_doc)

    def get_chat_history(self):
        # Exclude system messages from chat history
        chat_history = self.db.messages.find()

        message_list = [chatservice_pb2.MessageResponse(
            username=message['user'],
            message=message['message'],
        ) for message in chat_history]

        return message_list

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_service = ChatService()
    chatservice_pb2_grpc.add_ChatServiceServicer_to_server(chat_service, server)
    server.add_insecure_port('[::]:50051')
    server.start()

    print("Server started")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        print("\nClosing server")
        server.stop(0)

if __name__ == '__main__':
    serve()