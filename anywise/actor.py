import asyncio
import threading
from queue import Queue
from typing import Any


class Message:
    """Message class containing content and sender's address."""

    def __init__(self, content: Any, sender: "Address | AsyncAddress"):
        self.content = content
        self.sender = sender


class Address:
    """Abstract Address class to support message forwarding."""

    def __init__(self, actor: "Actor"):
        self.actor = actor

    def send(self, message: Message):
        """Send a message in threading mode."""
        self.actor.queue.put(message)


class AsyncAddress:
    def __init__(self, actor: "AsyncActor"):
        self.actor = actor

    async def send(self, message: Message):
        """Send a message in asyncio mode."""
        await self.actor.queue.put(message)


class Actor:
    """Thread-based Actor."""

    def __init__(self, name: str):
        self.name = name
        self.queue = Queue[Any]()
        self.address = Address(self)
        self.running = True

    def process_messages(self):
        """Process messages sequentially in threading environment."""
        while self.running:
            message = self.queue.get()
            result = self.handle_message(message.content)
            message.sender.send(Message(result, self.address))

    def handle_message(self, content: Any) -> Any:
        """Handle a message (synchronous work)."""
        import time

        time.sleep(0.1)  # Simulate work
        return f"Processed by {self.name}: {content}"


class AsyncActor:
    """Asyncio-based Actor."""

    def __init__(self, name: str):
        self.name = name
        self.queue = asyncio.Queue[Any]()
        self.address = AsyncAddress(self)
        self.running = True

    async def process_messages(self):
        """Process messages sequentially in asyncio environment."""
        while self.running:
            message = await self.queue.get()
            result = await self.handle_message(message.content)
            await message.sender.send(Message(result, self.address))

    async def handle_message(self, content: Any) -> Any:
        """Handle a message (asynchronous work)."""
        await asyncio.sleep(0.1)  # Simulate async work
        return f"Processed by {self.name}: {content}"


# Example usage
def threading_example():
    actor1 = Actor("ThreadActor1")
    actor2 = Actor("ThreadActor2")

    threading.Thread(target=actor1.process_messages, daemon=True).start()
    threading.Thread(target=actor2.process_messages, daemon=True).start()

    sender_address = Address(actor2)  # Pass the response queue to the address
    actor1.queue.put(Message("Hello from Thread", sender_address))

    resp = actor2.queue.get()
    print(resp.content)


async def asyncio_example():
    actor1 = AsyncActor("AsyncActor1")
    actor2 = AsyncActor("AsyncActor2")

    asyncio.create_task(actor1.process_messages())
    asyncio.create_task(actor2.process_messages())

    sender_address = AsyncAddress(actor2)
    await actor1.queue.put(Message("Hello from Thread", sender_address))

    resp = await actor1.queue.get()
    print(resp.content)


# Run examples
if __name__ == "__main__":
    # Threading example
    threading_example()

    # Asyncio example
    asyncio.run(asyncio_example())


"""
import asyncio
from dataclasses import dataclass
from typing import Optional

@dataclass
class CreateUser:
    username: str
    email: str
    reply_to: asyncio.Queue  # Reply channel

class UserActor:
    def __init__(self, name: str):
        self.name = name
        self.users = {}
        self.mailbox = asyncio.Queue()

    async def run(self):
        while True:
            message = await self.mailbox.get()
            await self.handle_message(message)

    async def handle_message(self, message):
        if isinstance(message, CreateUser):
            # Process the message
            user_id = len(self.users) + 1
            self.users[user_id] = {
                "username": message.username,
                "email": message.email
            }
            # Send response through reply channel
            await message.reply_to.put({
                "user_id": user_id,
                "status": "created"
            })

async def main():
    # Create actor
    user_actor = UserActor("user_manager")
    
    # Create reply channel
    reply_channel = asyncio.Queue()
    
    # Create message with reply channel
    create_cmd = CreateUser(
        username="john_doe",
        email="john@example.com",
        reply_to=reply_channel
    )
    
    # Start actor
    actor_task = asyncio.create_task(user_actor.run())
    
    # Send message
    await user_actor.mailbox.put(create_cmd)
    
    # Wait for response
    response = await reply_channel.get()
    print(f"Response: {response}")
    
    # Cleanup
    actor_task.cancel()
"""
