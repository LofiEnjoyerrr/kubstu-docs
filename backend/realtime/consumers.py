import json
from collections import defaultdict

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import F

from docs.models import Document, DocumentAccess

# In-process presence registry: group_name -> {channel_name -> user_info dict}
# NOTE: per-worker; acceptable for single-node deployments.
_rooms: dict[str, dict[str, dict]] = defaultdict(dict)


class DocumentConsumer(AsyncWebsocketConsumer):

    # ------------------------------------------------------------------ connect

    async def connect(self):
        self.doc_id = self.scope['url_route']['kwargs']['doc_id']
        self.group_name = f'doc_{self.doc_id}'
        self.user = self.scope['user']
        self.user_info: dict = {}

        if not await self._check_access():
            await self.close(code=4003)
            return

        self.user_info = self._build_user_info()

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        _rooms[self.group_name][self.channel_name] = self.user_info

        await self.accept()

        content, version = await self._get_document()
        current_users = [
            info for ch, info in _rooms[self.group_name].items()
            if ch != self.channel_name
        ]
        await self.send(text_data=json.dumps({
            'type': 'init',
            'content': content,
            'version': version,
            'users': current_users,
        }))

        await self.channel_layer.group_send(self.group_name, {
            'type': 'broadcast_user_join',
            'sender_channel': self.channel_name,
            **self.user_info,
        })

    # --------------------------------------------------------------- disconnect

    async def disconnect(self, close_code):
        _rooms[self.group_name].pop(self.channel_name, None)
        if not _rooms[self.group_name]:
            _rooms.pop(self.group_name, None)

        await self.channel_layer.group_send(self.group_name, {
            'type': 'broadcast_user_leave',
            'sender_channel': self.channel_name,
            **self.user_info,
        })

        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # ------------------------------------------------------------------ receive

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            return

        event_type = data.get('type')

        if event_type == 'edit':
            await self._handle_edit(data)
        elif event_type == 'cursor':
            await self._handle_cursor(data)

    # --------------------------------------------------------- inbound handlers

    async def _handle_edit(self, data):
        """
        Expected payload:
          {
            "type":    "edit",
            "delta":   <change ops — format defined by frontend editor>,
            "state":   <new full document state to persist — optional>,
            "version": <int — client's current version before this change>
          }

        "delta" is the minimal change description broadcast to peers so they
        can apply it locally without receiving the whole document.
        "state" (if present) is persisted server-side as the canonical content.
        If "state" is absent the server falls back to persisting "delta" itself
        (backward-compatible with clients that still send full content as delta).
        """
        delta = data.get('delta')
        if delta is None:
            return

        # Prefer an explicit separate state for persistence; fall back to delta.
        to_persist = data.get('state', delta)
        new_version = await self._save_edit(to_persist)

        await self.channel_layer.group_send(self.group_name, {
            'type': 'broadcast_edit',
            'sender_channel': self.channel_name,
            'delta': delta,
            'version': new_version,
            **self.user_info,
        })

    async def _handle_cursor(self, data):
        """
        Expected payload:
          {
            "type":     "cursor",
            "position": {"from": <int>, "to": <int>}
          }
        """
        position = data.get('position')
        if position is None:
            return

        await self.channel_layer.group_send(self.group_name, {
            'type': 'broadcast_cursor',
            'sender_channel': self.channel_name,
            'position': position,
            **self.user_info,
        })

    # -------------------------------------------------------- broadcast handlers

    async def broadcast_edit(self, event):
        if event['sender_channel'] == self.channel_name:
            return
        await self.send(text_data=json.dumps({
            'type': 'edit',
            'user_id': event['user_id'],
            'username': event['username'],
            'color': event['color'],
            'delta': event['delta'],
            'version': event['version'],
        }))

    async def broadcast_cursor(self, event):
        if event['sender_channel'] == self.channel_name:
            return
        await self.send(text_data=json.dumps({
            'type': 'cursor',
            'user_id': event['user_id'],
            'username': event['username'],
            'color': event['color'],
            'position': event['position'],
        }))

    async def broadcast_user_join(self, event):
        if event['sender_channel'] == self.channel_name:
            return
        await self.send(text_data=json.dumps({
            'type': 'user_join',
            'user_id': event['user_id'],
            'username': event['username'],
            'color': event['color'],
        }))

    async def broadcast_user_leave(self, event):
        if event['sender_channel'] == self.channel_name:
            return
        await self.send(text_data=json.dumps({
            'type': 'user_leave',
            'user_id': event['user_id'],
            'username': event['username'],
        }))

    async def broadcast_comment_add(self, event):
        await self.send(text_data=json.dumps({
            'type': 'comment_add',
            'comment': event['comment'],
        }))

    async def broadcast_comment_delete(self, event):
        await self.send(text_data=json.dumps({
            'type': 'comment_delete',
            'comment_id': event['comment_id'],
        }))

    async def broadcast_comment_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'comment_update',
            'comment': event['comment'],
        }))

    # ------------------------------------------------------------------ helpers

    def _build_user_info(self) -> dict:
        user = self.user
        if user.is_authenticated:
            return {
                'user_id': user.id,
                'username': user.username,
                'color': getattr(user, 'color', '#808080'),
            }
        return {'user_id': None, 'username': 'Гость', 'color': '#808080'}

    @database_sync_to_async
    def _check_access(self) -> bool:
        try:
            doc = Document.objects.only('id', 'is_public', 'owner_id').get(pk=self.doc_id)
        except Document.DoesNotExist:
            return False

        if doc.is_public:
            return True

        user = self.user
        if not user.is_authenticated:
            return False
        if doc.owner_id == user.pk:
            return True
        return DocumentAccess.objects.filter(document_id=self.doc_id, user=user).exists()

    @database_sync_to_async
    def _get_document(self) -> tuple:
        doc = Document.objects.only('content', 'version').get(pk=self.doc_id)
        try:
            content = json.loads(doc.content) if doc.content else {}
        except (json.JSONDecodeError, TypeError):
            content = doc.content or {}
        return content, doc.version

    @database_sync_to_async
    def _save_edit(self, new_content) -> int:
        content_str = (
            json.dumps(new_content)
            if isinstance(new_content, (dict, list))
            else new_content
        )
        Document.objects.filter(pk=self.doc_id).update(
            content=content_str,
            version=F('version') + 1,
        )
        return Document.objects.values_list('version', flat=True).get(pk=self.doc_id)
