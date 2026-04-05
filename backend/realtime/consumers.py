import json
from channels.generic.websocket import AsyncWebsocketConsumer

class DocumentConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.doc_id = self.scope["url_route"]["kwargs"]["doc_id"]
        self.group_name = f"doc_{self.doc_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)

        event_type = data.get("type")

        if event_type == "edit":
            await self.handle_edit(data)

    async def handle_edit(self, data):
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "broadcast_edit",
                "user": self.scope["user"].username if self.scope["user"].is_authenticated else "anon",
                "delta": data["delta"],
            }
        )

    async def broadcast_edit(self, event):
        await self.send(text_data=json.dumps({
            "type": "edit",
            "user": event["user"],
            "delta": event["delta"],
        }))