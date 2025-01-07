# AWS Source
# https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html

# # Define some functions to perform the CRUD operations
# import asyncio
# import typing as ty

# from ..anywise import Anywise

# Event = ty.NewType("Event", dict[str, ty.Any])
# Context = ty.NewType("Context", dict[str, ty.Any])

# anywise = Anywise()


# class UserCreated: ...


# def lambda_handler(event: UserCreated, context: Context):
#     """Provide an event that contains the following keys:
#     - operation: one of the operations in the operations dict below
#     - payload: a JSON object containing parameters to pass to the
#       operation being performed
#     """

#     # operation = event["operation"]
#     # payload = event["payload"]

#     asyncio.run(anywise.send(event))


# GRPC Source
# import grpc
# import asyncio

# async def run() -> None:
#     async with grpc.aio.insecure_channel("localhost:50051") as channel:
#         stub = helloworld_pb2_grpc.GreeterStub(channel)
#         response = await stub.SayHello(helloworld_pb2.HelloRequest(name="you"))

# _cleanup_coroutines = []


# class Greeter(helloworld_pb2_grpc.GreeterServicer):
#     async def SayHello(
#         self,
#         request: helloworld_pb2.HelloRequest,
#         context: grpc.aio.ServicerContext,
#     ) -> helloworld_pb2.HelloReply:
#         logging.info("Received request, sleeping for 4 seconds...")
#         await asyncio.sleep(4)
#         logging.info("Sleep completed, responding")
#         return helloworld_pb2.HelloReply(message="Hello, %s!" % request.name)


# async def serve() -> None:
#     server = grpc.aio.server()
#     helloworld_pb2_grpc.add_GreeterServicer_to_server(Greeter(), server)
#     listen_addr = "[::]:50051"
#     server.add_insecure_port(listen_addr)
#     logging.info("Starting server on %s", listen_addr)
#     await server.start()

#     async def server_graceful_shutdown():
#         logging.info("Starting graceful shutdown...")
#         # Shuts down the server with 5 seconds of grace period. During the
#         # grace period, the server won't accept new connections and allow
#         # existing RPCs to continue within the grace period.
#         await server.stop(5)

#     _cleanup_coroutines.append(server_graceful_shutdown())
#     await server.wait_for_termination()


# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     loop = asyncio.get_event_loop()
#     try:
#         loop.run_until_complete(serve())
#     finally:
#         loop.run_until_complete(*_cleanup_coroutines)
#         loop.close()

# import typing as ty


# class ICommandEnvelope(ty.Protocol):
#     """
#     Meta data of event
#     encryption type, schema, key, and serialization format. etc.

#     express the whole process chain of command

#     command -> handler -> response | errors
#     """

#     headers: "CommandMeta"
#     command: "ICommand"


# class CommandMeta:
#     # source: uri, post: users/sessions/chats
#     command_source: ...  # commands/command/v1,
#     answer: type
#     errors: list[Exception]


# class ICommand:
#     entity_id: str
#     command_id: str


# class HttpSource: 
#     "Uvicorn"
#     ...


# class KafkaSource: ...


# class GRPCSource: ...
# """
# class KafkaSource:
#     def __init__(self, client, anywise: Anywise)
#         self.client = client
#         self.anywise = anywise

    
#     async def start(self): ...
#     async def stop(self): ...

    
#     async def polling(self):
#         ...

        
# async def main():
#     async with KafkaSource() as source:
#         await source.polling()
# """


# class RedisJobQueue:
#     "https://arq-docs.helpmanual.io/"

#     """
#     async def main():

#     redis = await create_pool(REDIS_SETTINGS)

#     source = RedisJobSource(redis, anywise)
        
#     # server code
#     for url in ('https://facebook.com', 'https://microsoft.com', 'https://github.com'):
#         command = DownloadContent(url)
#         await source.send(command)
    
#     # client code
#     async with source:
#         await source.run_forever()
#     """
#     ...
