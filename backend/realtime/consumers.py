import json
from channels.generic.websocket import AsyncWebsocketConsumer

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from docs.models import Document

class DocumentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.doc_id = self.scope["url_route"]["kwargs"]["doc_id"]
        self.group_name = f"doc_{self.doc_id}"

        # Добавляем пользователя в группу
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Отправляем текущее состояние документа
        content = await self.get_document_content(self.doc_id)
        await self.send(text_data=json.dumps({
            "type": "init",
            "content": content
        }))

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
        delta = data.get("delta")
        if delta is None:
            return

        user = self.scope["user"].username if self.scope["user"].is_authenticated else "anon"
        await self.update_document(self.doc_id, delta)

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "broadcast_edit",
                "user": user,
                "delta": delta,
                "sender_channel": self.channel_name,  # ← добавляем отправителя
            }
        )

    async def broadcast_edit(self, event):
        # Не отправляем обратно тому кто прислал
        if event.get("sender_channel") == self.channel_name:
            return

        await self.send(text_data=json.dumps({
            "type": "edit",
            "user": event["user"],
            "delta": event["delta"],
        }))

    @database_sync_to_async
    def update_document(self, doc_id, delta):
        if delta is None:
            return
        doc = Document.objects.get(pk=doc_id)
        doc.content = json.dumps(delta) if isinstance(delta, dict) else delta
        doc.save(update_fields=['content'])

    @database_sync_to_async
    def get_document_content(self, doc_id):
        doc = Document.objects.get(pk=doc_id)
        # Пытаемся вернуть как dict (TipTap JSON), иначе как строку
        try:
            return json.loads(doc.content) if doc.content else {}
        except (json.JSONDecodeError, TypeError):
            return doc.content or {}
