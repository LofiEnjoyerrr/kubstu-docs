import json
from collections import defaultdict

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import F

from docs.models import Document, DocumentAccess
from notifications.tasks import enqueue_edit_notification

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
        # Populated by ``_check_access`` and read by ``_handle_edit`` so we
        # know who to notify (owner) and whether to skip (self-edit).
        self.doc_owner_id: int | None = None
        self.doc_title: str = ''
        self.edit_notification_sent = False
        self.notified_edit_sessions: set[str] = set()
        self.can_edit_document = False

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
        if not self.can_edit_document:
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

        # Newer clients send a fresh edit_notification_session_id for every
        # document entry. That lets the frontend decide when "the first edit
        # after opening" begins, while the backend still deduplicates retries
        # for the same entry. Older clients fall back to one notification per
        # WebSocket consumer session.
        notification_session_id = data.get('edit_notification_session_id')
        has_client_session = (
            isinstance(notification_session_id, str)
            and bool(notification_session_id)
        )
        if has_client_session:
            should_notify_owner = (
                data.get('notify_owner') is True
                and notification_session_id not in self.notified_edit_sessions
            )
        else:
            should_notify_owner = not self.edit_notification_sent

        user = self.user
        if (
            user.is_authenticated
            and self.doc_owner_id is not None
            and self.doc_owner_id != user.pk
            and should_notify_owner
        ):
            if has_client_session:
                self.notified_edit_sessions.add(notification_session_id)
            else:
                self.edit_notification_sent = True
            try:
                enqueue_edit_notification(
                    owner_id=self.doc_owner_id,
                    doc_id=int(self.doc_id),
                    editor_id=user.pk,
                    editor_username=user.username,
                    doc_title=self.doc_title,
                )
            except Exception:  # noqa: BLE001
                # Notification dispatch must never break the edit pipeline.
                pass

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
            'avatar': event.get('avatar'),
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

    async def broadcast_full_replace(self, event):
        """
        A full-document rewrite (e.g. DOCX import) issued over HTTP.
        Sent to every connected client including the originator so that
        any of them whose editor state is older gets resynced.
        """
        await self.send(text_data=json.dumps({
            'type': 'full_replace',
            'content': event['content'],
            'version': event['version'],
            'user_id': event.get('user_id'),
            'username': event.get('username'),
        }))

    async def broadcast_page_layout(self, event):
        await self.send(text_data=json.dumps({
            'type': 'page_layout',
            'page_width': event['page_width'],
            'page_height': event.get('page_height'),
            'margin_top': event['margin_top'],
            'margin_right': event['margin_right'],
            'margin_bottom': event['margin_bottom'],
            'margin_left': event['margin_left'],
            'header_content': event.get('header_content', ''),
            'footer_content': event.get('footer_content', ''),
            'show_page_numbers': event.get('show_page_numbers', False),
            'page_number_start': event.get('page_number_start', 1),
        }))

    # ------------------------------------------------------------------ helpers

    def _build_user_info(self) -> dict:
        user = self.user
        if user.is_authenticated:
            avatar_url = self._get_avatar_url(user)
            return {
                'user_id': user.id,
                'username': user.username,
                'color': getattr(user, 'color', '#808080'),
                'avatar': avatar_url,
            }
        return {'user_id': None, 'username': 'Гость', 'color': '#808080', 'avatar': None}

    @staticmethod
    def _get_avatar_url(user) -> str | None:
        """Avatar URL with a cache-busting query string so updates show up
        for clients that may already have an older copy cached."""
        avatar = getattr(user, 'avatar', None)
        if not avatar or not getattr(avatar, 'name', ''):
            return None
        dt_updated = getattr(user, 'dt_updated', None)
        if dt_updated is None:
            return avatar.url
        return f'{avatar.url}?v={int(dt_updated.timestamp())}'

    @database_sync_to_async
    def _check_access(self) -> bool:
        try:
            doc = Document.objects.only(
                'id', 'is_public', 'owner_id', 'title',
            ).get(pk=self.doc_id)
        except Document.DoesNotExist:
            return False

        # Stash the owner + title so ``_handle_edit`` can dispatch
        # notifications without a second query per edit.
        self.doc_owner_id = doc.owner_id
        self.doc_title = doc.title

        user = self.user
        if not user.is_authenticated:
            return doc.is_public
        if doc.owner_id == user.pk:
            self.can_edit_document = True
            return True
        access = DocumentAccess.objects.filter(
            document_id=self.doc_id,
            user=user,
        ).only('role').first()
        if access:
            self.can_edit_document = access.role == 'editor'
            return True
        return doc.is_public

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
