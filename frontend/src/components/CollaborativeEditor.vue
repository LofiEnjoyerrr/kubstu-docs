<template>
  <div class="mb-5 page-header">
    <v-btn
      elevation="0"
      color="#FF8C00"
      @click="backToMainPage()"
    >
      Главная страница
    </v-btn>

    <div>
      <span 
        style="font-size: 20px;"
        class="mr-2"
      >{{ user.userName }}</span>

      <v-btn 
        variant="plain"
        @click="logout"
      >Выйти</v-btn>
    </div>
  </div>

  <div class="wrapper">
    <div class="header">
      <span class="title">Название документа</span>
      <span class="badge" :class="status === 'connected' ? 'online' : 'connecting'">
        {{ status === 'connected' ? '' : 'Подключаемся…' }}
      </span>
      <div class="avatars">
        <div
          v-for="(user, i) in users" :key="i"
          class="avatar"
          :style="{ background: user?.color }"
          :title="user?.name"
        >{{ user?.name?.[0] }}</div>
      </div>
    </div>

    <div v-if="editor" class="toolbar">
      <button @click="editor.chain().focus().toggleBold().run()" :class="editor.isActive('bold') ? 'btn active' : 'btn'"><b>B</b></button>
      <button @click="editor.chain().focus().toggleItalic().run()" :class="editor.isActive('italic') ? 'btn active' : 'btn'"><i>I</i></button>
      <button @click="editor.chain().focus().toggleStrike().run()" :class="editor.isActive('strike') ? 'btn active' : 'btn'"><s>S</s></button>
      <div class="divider" />
      <button v-for="level in [1, 2, 3]" :key="level"
        @click="editor.chain().focus().toggleHeading({ level }).run()"
        :class="editor.isActive('heading', { level }) ? 'btn active' : 'btn'"
      >H{{ level }}</button>
      <div class="divider" />
      <button @click="editor.chain().focus().toggleBulletList().run()" :class="editor.isActive('bulletList') ? 'btn active' : 'btn'">• List</button>
      <button @click="editor.chain().focus().toggleOrderedList().run()" :class="editor.isActive('orderedList') ? 'btn active' : 'btn'">1. List</button>
      <button @click="editor.chain().focus().toggleBlockquote().run()" :class="editor.isActive('blockquote') ? 'btn active' : 'btn'">❝</button>
      <div class="divider" />
      <button class="btn" @click="editor.chain().focus().undo().run()">↩</button>
      <button class="btn" @click="editor.chain().focus().redo().run()">↪</button>
    </div>

    <editor-content :editor="editor" class="editor" />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Collaboration from '@tiptap/extension-collaboration'
import * as Y from 'yjs'
import { WebsocketProvider } from 'y-websocket'
import { useRouter, useRoute } from 'vue-router'
import { useDocumentStore } from '@/stores/document'
import { useUserStore } from '@/stores/user';

const USER_COLORS = ['#F98181', '#FBBC88', '#FAF594', '#70CFF8', '#94FADB', '#B9F18D']
const randomColor = () => USER_COLORS[Math.floor(Math.random() * USER_COLORS.length)]
const randomName  = () => `User ${Math.floor(Math.random() * 1000)}`

const ydoc = new Y.Doc()
const router = useRouter()
const route = useRoute()
const document = useDocumentStore();
const user = useUserStore();

const provider = new WebsocketProvider('ws://localhost:1234', 'my-document-room', ydoc)

const status = ref('connecting')
const users  = ref([])

provider.on('status', ({ status: s }) => { status.value = s })
provider.awareness.on('change', () => {
    users.value = [...provider.awareness.getStates().values()]
      .map(s => s.user)
      .filter(Boolean)
  })
const editor = useEditor({
  extensions: [
    StarterKit.configure({ history: false }),
    Collaboration.configure({ document: ydoc }),
  ],

  onSelectionUpdate({ editor }) {
    const { from, to } = editor.state.selection

    console.log('Позиция каретки:', from)
    console.log('Выделено от/до:', from, to)
    console.log('Есть выделение:', from !== to)
  },
})

const backToMainPage = () => {
  router.push('/');
}

onMounted(async () => {
  let documentObj;

  try {
    documentObj = await document.fetchDocument(route.params.id)
  } catch (error) {
    console.error(error)

    editor.value.commands.setContent('жопа')

    return
  }

  if (documentObj.content) {
    editor.value.commands.setContent(documentObj.content)
  } 
})

onBeforeUnmount(() => {
  editor.value?.destroy()
  provider.destroy()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
}
.wrapper {
  max-width: 95vw;
  flex: 1;
  font-family: 'Segoe UI', sans-serif;
  border: 1px solid #e2e8f0; border-radius: 12px;
  overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,.08);
}
.header {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 20px; background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}
.title { font-weight: 700; font-size: 16px; flex: 1; }
.badge { padding: 3px 10px; border-radius: 99px; color: #fff; font-size: 12px; font-weight: 600; }
.badge.online     { background: #22c55e; }
.badge.connecting { background: #f59e0b; }
.avatars { display: flex; gap: 6px; }
.avatar {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 700; font-size: 13px;
  border: 2px solid #fff; box-shadow: 0 0 0 1px #cbd5e1;
}
.toolbar {
  display: flex; gap: 4px; padding: 8px 16px;
  background: #fff; border-bottom: 1px solid #e2e8f0; flex-wrap: wrap;
}
.btn {
  padding: 4px 10px; border: 1px solid #e2e8f0;
  border-radius: 6px; cursor: pointer; background: #fff;
  font-size: 13px; color: #374151; transition: all 0.15s;
}
.btn:hover  { background: #f1f5f9; }
.btn.active { border-color: #6366f1; background: #eef2ff; color: #4f46e5; }
.divider    { width: 1px; background: #e2e8f0; margin: 0 4px; }
.editor     { min-height: 500px; padding: 32px; font-size: 15px; line-height: 1.7; color: #1e293b; }

:deep(.collaboration-cursor__caret) {
  border-left: 2px solid; border-right: 2px solid;
  margin-left: -1px; margin-right: -1px;
  word-break: normal; pointer-events: none;
}
:deep(.collaboration-cursor__label) {
  border-radius: 4px 4px 4px 0; color: #fff;
  font-size: 11px; font-weight: 600; padding: 1px 5px;
  position: absolute; top: -1.4em; left: -1px;
  white-space: nowrap; user-select: none;
}
:deep(.tiptap)            { outline: none; }
:deep(.tiptap h1)         { font-size: 2em; margin: 0.5em 0; }
:deep(.tiptap h2)         { font-size: 1.5em; margin: 0.5em 0; }
:deep(.tiptap h3)         { font-size: 1.2em; margin: 0.5em 0; }
:deep(.tiptap ul),
:deep(.tiptap ol)         { padding-left: 1.5em; }
:deep(.tiptap blockquote) { border-left: 3px solid #6366f1; padding-left: 1em; color: #64748b; margin: 0.5em 0; }
:deep(.tiptap p)          { margin: 0.25em 0; }
</style>