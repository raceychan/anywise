"""
a command line interface for anywise
maybe we can also build a tui for anywise


anywise --help

anywise todo_app.main
# this would serve the message source, such as kafka, rabbitmq, etc


anywise todo_app.main --sink
# this would poll the outbox table and send the messages to the event sink

"""

# from sqlalchemy import select, update, func
# from sqlalchemy.ext.asyncio import AsyncEngine

# class OutboxEventProcessor:
#     def __init__(self, engine: AsyncEngine):
#         self._engine = engine

#     def fetch_pending_events(self):
#         """Fetch all pending events by joining outbox_events with events."""
#         stmt = (
#             select(
#                 outbox_events.c.id,
#                 outbox_events.c.event_id,
#                 outbox_events.c.status,
#                 outbox_events.c.retry_count,
#                 events.c.aggregate_id,
#                 events.c.event_type,
#                 events.c.payload
#             )
#             .join_from(outbox_events, events, outbox_events.c.event_id == events.c.id)
#             .where(outbox_events.c.status == 'pending')
#             .order_by(outbox_events.c.id)  # Optional: order by outbox event ID
#         )
#         async with self._engine.connect() as connection:
#             # Build the SQLAlchemy Core SELECT statement with JOIN
#             result = connection.execute(stmt)
#             events = result.fetchall()

#         return events

#     def process_event(self, event):
#         """Simulate processing an event (e.g., sending it to a message queue)."""

#     def update_event_status(self, event_id, status, retry_count):
#         """Update the status of the event in the outbox_events table."""
#         with self._engine.connect() as connection:
#             stmt = (
#                 update(outbox_events)
#                 .where(outbox_events.c.event_id == event_id)
#                 .values(status=status, retry_count=retry_count + 1, processed_at=func.now())
#             )
#             connection.execute(stmt)
#             print(f"Event {event_id} status updated to {status}.")

#     def poll_outbox():
#         """Periodically poll the outbox_events table for pending events."""
#         while True:
#             print("Polling for pending events...")
#             events_to_process = fetch_pending_events()

#             if events_to_process:
#                 print(f"Found {len(events_to_process)} pending events to process.")
#                 for event in events_to_process:
#                     try:
#                         # Process the event
#                         process_event(event)

#                         # Update status to 'sent' after successful processing
#                         update_event_status(event['event_id'], 'sent', event['retry_count'])
#                     except Exception as e:
#                         print(f"Error processing event {event['event_id']}: {e}")

#                         # If processing fails, increment retry count and set status to 'failed'
#                         retry_count = event['retry_count'] + 1
#                         update_event_status(event['event_id'], 'failed', retry_count)
#             else:
#                 print("No pending events found, waiting for the next poll...")

#             # Wait for a few seconds before polling again (adjust as needed)
#             time.sleep(5)  # Poll every 5 seconds
