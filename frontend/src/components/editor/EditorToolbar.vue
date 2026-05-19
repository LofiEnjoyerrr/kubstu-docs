<template>
  <div class="border-b border-slate-200 bg-white select-none">
    <!-- ── Row 1: file / history / find / page-setup ────────────────────────── -->
    <div class="flex flex-wrap items-center gap-0.5 px-2 py-1 border-b border-slate-100">
      <Btn title="Отменить (Ctrl+Z)" @click="editor.chain().focus().undo().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12.5 8c-2.65 0-5.05.99-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z"/></svg>
      </Btn>
      <Btn title="Повторить (Ctrl+Y)" @click="editor.chain().focus().redo().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M18.4 10.6C16.55 8.99 14.15 8 11.5 8c-4.65 0-8.58 3.03-9.96 7.22L3.9 16c1.05-3.19 4.05-5.5 7.6-5.5 1.95 0 3.73.72 5.12 1.88L13 16h9V7l-3.6 3.6z"/></svg>
      </Btn>

      <Sep />

      <Btn title="Очистить форматирование" @click="editor.chain().focus().clearNodes().unsetAllMarks().resetParagraphSpacing().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M3.27 5L2 6.27l6.97 6.97L6.5 19h3l1.57-3.66L16.73 21 18 19.73 3.55 5.27 3.27 5zM6 5v.18l3 3V7h2v2.18l1.78 1.78L13.4 7H20V5H6z"/></svg>
      </Btn>

      <Sep />

      <Btn title="Найти и заменить (Ctrl+F)" :active="showFind" @click="toggleFind">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
      </Btn>

      <Sep />

      <!-- DOCX import / export -->
      <input
        ref="docxInputRef"
        type="file"
        accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        class="sr-only"
        @change="onDocxImport"
      />
      <Btn title="Импорт DOCX" :disabled="isImporting || !docId" @click="docxInputRef?.click()">
        <svg v-if="!isImporting" class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
        <svg v-else class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/></svg>
      </Btn>
      <Btn title="Экспорт в DOCX" :disabled="isExporting" @click="onDocxExport">
        <svg v-if="!isExporting" class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 14l-5-5 1.41-1.41L11 14.17V7h2v7.17l2.59-2.58L17 13l-5 5z"/></svg>
        <svg v-else class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/></svg>
      </Btn>

      <Sep />

      <!-- Page layout / paragraph / header-footer popovers -->
      <Btn title="Параметры страницы" :active="popover === 'page'" @click="togglePop('page')">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M6 2c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6H6zm7 7V3.5L18.5 9H13z"/></svg>
      </Btn>
      <Btn title="Интервалы абзаца" :active="popover === 'para'" @click="togglePop('para')">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M3 5h18v2H3zm0 6h12v2H3zm0 6h18v2H3z"/></svg>
      </Btn>
      <Btn title="Колонтитулы" :active="popover === 'hf'" @click="togglePop('hf')">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M4 3h16v3H4zm0 5h16v8H4zm0 10h16v3H4z"/></svg>
      </Btn>

      <Sep />

      <Btn title="Разрыв страницы (Ctrl+Enter)" :disabled="!editor" @click="insertPageBreak">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M9 4H5v4h4V4zm0 12H5v4h4v-4zm6-12h-4v4h4V4zm0 12h-4v4h4v-4zM5 10h14v2H5z"/></svg>
      </Btn>
      <Btn title="Разрыв раздела (новая нумерация страниц)" :disabled="!editor" @click="insertSectionBreak">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M4 4h16v2H4V4zm0 6h16v2H4v-2zm0 8h16v2H4v-2zM7 8l3 3-3 3v-2H3v-2h4V8zm10 0v2h4v2h-4v2l-3-3 3-3z"/></svg>
      </Btn>
<!--      <Btn title="Вставить номер страницы" :disabled="!editor" @click="editor.chain().focus().insertPageNumber().run()">-->
<!--        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M6 4h2v16H6zm10 0c2 0 3 1.5 3 4 0 1.5-1 2.5-2 3v.5c1 .5 2 1.5 2 3 0 2.5-1 4.5-3 4.5h-3v-2h3c.5 0 1-1 1-2.5s-.5-2-1-2h-2v-2h2c.5 0 1-.5 1-2s-.5-2-1-2h-3V4h3z"/></svg>-->
<!--      </Btn>-->

      <span v-if="importError" class="text-xs text-red-500 ml-2">{{ importError }}</span>
    </div>

    <!-- ── Row 2: formatting toolbar ────────────────────────────────────────── -->
    <div class="flex flex-wrap items-center gap-0.5 px-2 py-1">
      <select
        :value="currentFontFamily"
        class="toolbar-select w-36"
        title="Шрифт"
        @change="e => applyFontFamily((e.target as HTMLSelectElement).value)"
      >
        <option v-for="f in FONTS" :key="f" :value="f" :style="{ fontFamily: f }">{{ f }}</option>
      </select>

      <select
        :value="currentFontSize"
        class="toolbar-select w-16"
        title="Размер шрифта"
        @change="e => applyFontSize((e.target as HTMLSelectElement).value)"
      >
        <option v-for="s in SIZES" :key="s" :value="`${s}pt`">{{ s }}</option>
      </select>

      <Sep />

      <select :value="currentHeading" class="toolbar-select w-32" @change="setHeading">
        <option value="0">Обычный текст</option>
        <option value="1">Заголовок 1</option>
        <option value="2">Заголовок 2</option>
        <option value="3">Заголовок 3</option>
        <option value="4">Заголовок 4</option>
        <option value="5">Заголовок 5</option>
        <option value="6">Заголовок 6</option>
      </select>

      <Sep />

      <Btn :active="editor.isActive('bold')"      title="Полужирный (Ctrl+B)"      @click="editor.chain().focus().toggleBold().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M15.6 11.8A4 4 0 0013 5H7v14h6.5a4.5 4.5 0 002.1-8.2zM9 7h4a2 2 0 010 4H9V7zm4.5 10H9v-4h4.5a2.5 2.5 0 010 5z"/></svg>
      </Btn>
      <Btn :active="editor.isActive('italic')"    title="Курсив (Ctrl+I)"    @click="editor.chain().focus().toggleItalic().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M10 4v3h2.21l-3.42 8H6v3h8v-3h-2.21l3.42-8H18V4z"/></svg>
      </Btn>
      <Btn :active="editor.isActive('underline')" title="Подчёркнутый (Ctrl+U)" @click="editor.chain().focus().toggleUnderline().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 17c3.31 0 6-2.69 6-6V3h-2.5v8c0 1.93-1.57 3.5-3.5 3.5S8.5 12.93 8.5 11V3H6v8c0 3.31 2.69 6 6 6zm-7 2v2h14v-2H5z"/></svg>
      </Btn>
      <Btn :active="editor.isActive('strike')"    title="Зачёркнутый"      @click="editor.chain().focus().toggleStrike().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M10 19h4v-3h-4v3zM5 4v3h5v3h4V7h5V4H5zM3 14h18v-2H3v2z"/></svg>
      </Btn>
      <Btn :active="editor.isActive('code')"      title="Моноширинный код"        @click="editor.chain().focus().toggleCode().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/></svg>
      </Btn>
      <Btn :active="editor.isActive('subscript')" title="Нижний индекс" @click="editor.chain().focus().toggleSubscript().run()">x₂</Btn>
      <Btn :active="editor.isActive('superscript')" title="Верхний индекс" @click="editor.chain().focus().toggleSuperscript().run()">x²</Btn>

      <label class="w-7 h-7 flex items-center justify-center rounded cursor-pointer hover:bg-slate-100 transition-colors relative" title="Цвет текста">
        <span class="flex flex-col items-center gap-px">
          <span class="text-[11px] font-bold text-slate-700 leading-none">A</span>
          <span class="w-4 h-1 rounded-sm" :style="{ background: currentColor }" />
        </span>
        <input type="color" :value="currentColor" class="absolute inset-0 opacity-0 cursor-pointer w-full h-full" @input="e => applyColor((e.target as HTMLInputElement).value)" />
      </label>

      <label class="w-7 h-7 flex items-center justify-center rounded cursor-pointer hover:bg-slate-100 transition-colors relative" title="Цвет выделения">
        <span class="flex flex-col items-center gap-px">
          <svg class="w-3.5 h-3.5 text-slate-700" fill="currentColor" viewBox="0 0 24 24"><path d="M6 14l3 3v5h6v-5l3-3V9H6v5zM11 3h2v6h-2z"/></svg>
          <span class="w-4 h-1 rounded-sm" :style="{ background: currentHighlight || '#fef08a' }" />
        </span>
        <input type="color" :value="currentHighlight || '#fef08a'" class="absolute inset-0 opacity-0 cursor-pointer w-full h-full" @input="e => applyHighlight((e.target as HTMLInputElement).value)" />
      </label>
      <Btn title="Убрать выделение" @click="editor.chain().focus().unsetHighlight().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M5 17h14v2H5zm9.92-9.51l-1.42 1.42-3.51-3.51 1.42-1.42c.39-.39 1.02-.39 1.41 0l2.1 2.1c.39.39.39 1.02 0 1.41zM6 17l-2-2 8-8 4 4-6 6H6z"/></svg>
      </Btn>

      <Sep />

      <Btn :active="editor.isActive({ textAlign: 'left' })"    title="По левому краю"   @click="editor.chain().focus().setTextAlign('left').run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M15 15H3v2h12v-2zm0-8H3v2h12V7zM3 13h18v-2H3v2zm0 8h18v-2H3v2zM3 3v2h18V3H3z"/></svg>
      </Btn>
      <Btn :active="editor.isActive({ textAlign: 'center' })"  title="По центру"       @click="editor.chain().focus().setTextAlign('center').run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M7 15v2h10v-2H7zm-4 6h18v-2H3v2zm0-8h18v-2H3v2zm4-6v2h10V7H7zM3 3v2h18V3H3z"/></svg>
      </Btn>
      <Btn :active="editor.isActive({ textAlign: 'right' })"   title="По правому краю"  @click="editor.chain().focus().setTextAlign('right').run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M3 21h18v-2H3v2zm6-4h12v-2H9v2zm-6-4h18v-2H3v2zm6-4h12V7H9v2zM3 3v2h18V3H3z"/></svg>
      </Btn>
      <Btn :active="editor.isActive({ textAlign: 'justify' })" title="По ширине"      @click="editor.chain().focus().setTextAlign('justify').run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M3 21h18v-2H3v2zm0-4h18v-2H3v2zm0-4h18v-2H3v2zm0-4h18V7H3v2zm0-6v2h18V3H3z"/></svg>
      </Btn>

      <select
        :value="currentLineHeight"
        class="toolbar-select w-24"
        title="Межстрочный интервал"
        @change="e => applyLineHeight((e.target as HTMLSelectElement).value)"
      >
        <option value="">Интервал</option>
        <option v-for="lh in LINE_HEIGHTS" :key="lh" :value="lh">{{ lh }}</option>
      </select>

      <Sep />

      <Btn :active="editor.isActive('bulletList')"  title="Маркированный список"                @click="editor.chain().focus().toggleBulletList().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M4 10.5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5 1.5-.67 1.5-1.5-.67-1.5-1.5-1.5zm0-6c-.83 0-1.5.67-1.5 1.5S3.17 7.5 4 7.5 5.5 6.83 5.5 6 4.83 4.5 4 4.5zm0 12c-.83 0-1.5.68-1.5 1.5s.68 1.5 1.5 1.5 1.5-.68 1.5-1.5-.67-1.5-1.5-1.5zM7 19h14v-2H7v2zm0-6h14v-2H7v2zm0-8v2h14V5H7z"/></svg>
      </Btn>
      <Btn :active="editor.isActive('orderedList')" title="Нумерованный список"              @click="editor.chain().focus().toggleOrderedList().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M2 17h2v.5H3v1h1v.5H2v1h3v-4H2v1zm1-9h1V4H2v1h1v3zm-1 3h1.8L2 13.1v.9h3v-1H3.2L5 10.9V10H2v1zm5-6v2h14V5H7zm0 14h14v-2H7v2zm0-6h14v-2H7v2z"/></svg>
      </Btn>
      <Btn :active="editor.isActive('taskList')" title="Список задач (флажки)" @click="editor.chain().focus().toggleTaskList().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zM10 17l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/></svg>
      </Btn>
      <Btn title="Увеличить отступ (Tab)"    @click="editor.chain().focus().sinkListItem('listItem').run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="2"/><rect x="9" y="9" width="12" height="2"/><rect x="9" y="13" width="9" height="2"/><rect x="9" y="17" width="12" height="2"/><path d="M3 7v8l4-4z"/></svg>
      </Btn>
      <Btn title="Уменьшить отступ (Shift+Tab)" @click="editor.chain().focus().liftListItem('listItem').run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="2"/><rect x="3" y="9" width="12" height="2"/><rect x="3" y="13" width="9" height="2"/><rect x="3" y="17" width="12" height="2"/><path d="M21 7v8l-4-4z"/></svg>
      </Btn>

      <Sep />

      <Btn :active="editor.isActive('blockquote')" title="Цитата" @click="editor.chain().focus().toggleBlockquote().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M6 17h3l2-4V7H5v6h3zm8 0h3l2-4V7h-6v6h3z"/></svg>
      </Btn>
      <Btn :active="editor.isActive('codeBlock')"  title="Блок кода" @click="editor.chain().focus().toggleCodeBlock().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M20 3H4v10c0 2.21 1.79 4 4 4h6c2.21 0 4-1.79 4-4v-3h2c1.11 0 2-.89 2-2V5c0-1.11-.89-2-2-2zm0 5h-2V5h2v3zM4 19h16v2H4z"/></svg>
      </Btn>
      <Btn title="Горизонтальная линия" @click="editor.chain().focus().setHorizontalRule().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 13H5v-2h14v2z"/></svg>
      </Btn>

      <Sep />

      <Btn :active="editor.isActive('link')" title="Вставить ссылку" @click="onInsertLink">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z"/></svg>
      </Btn>
      <Btn v-if="editor.isActive('link')" title="Убрать ссылку" @click="editor.chain().focus().unsetLink().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M14.39 11l2-2H17a3 3 0 0 1 0 6h-2v2h2a5 5 0 0 0 5-5 5 5 0 0 0-5-5h-3.61l1 1zM2.83 2.41 1.41 3.83l4.66 4.66A5 5 0 0 0 7 17h3v-2H7a3 3 0 0 1 0-6h.17l8 8 1.42-1.41L2.83 2.41z"/></svg>
      </Btn>

      <input ref="imageInputRef" type="file" accept="image/*" class="sr-only" @change="onImageSelected" />
      <Btn title="Вставить изображение" @click="imageInputRef?.click()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg>
      </Btn>

      <Sep />

      <Btn title="Вставить таблицу" @click="editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M3 3h18v18H3V3zm2 4v3h6V7H5zm0 5v3h6v-3H5zm0 5v2h6v-2H5zm8-10v3h6V7h-6zm0 5v3h6v-3h-6zm0 5v2h6v-2h-6z"/></svg>
      </Btn>
      <Btn v-if="editor.isActive('table')" title="Добавить столбец" @click="editor.chain().focus().addColumnAfter().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M4 4h7v16H4V4zm9 0h2v3h3v2h-3v3h-2V9h-3V7h3V4z"/></svg>
      </Btn>
      <Btn v-if="editor.isActive('table')" title="Добавить строку" @click="editor.chain().focus().addRowAfter().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M4 4h16v7H4V4zm0 9h7v3h3v2h-3v3H4v-8zm9 4h2v-3h3v-2h-3v-3h-2v8z"/></svg>
      </Btn>
      <Btn v-if="editor.isActive('table')" title="Удалить столбец" @click="editor.chain().focus().deleteColumn().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M4 4h7v16H4V4zm10 6 2-2 2 2-2 2 2 2-2 2-2-2-2 2-2-2 2-2-2-2 2-2z"/></svg>
      </Btn>
      <Btn v-if="editor.isActive('table')" title="Удалить строку" @click="editor.chain().focus().deleteRow().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M4 4h16v7H4V4zm6 10 2-2 2 2 2-2 2 2-2 2 2 2-2 2-2-2-2 2-2-2 2-2-2-2z"/></svg>
      </Btn>
      <Btn v-if="editor.isActive('table')" title="Удалить таблицу" @click="editor.chain().focus().deleteTable().run()">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
      </Btn>
    </div>

    <!-- Page setup popover -->
    <div v-if="popover === 'page'" class="px-4 py-3 border-t border-slate-100 bg-slate-50 flex flex-wrap items-end gap-4 text-xs">
      <NumberField label="Ширина (px)" :value="pageLayout.page_width" :min="320" :max="2400" @change="v => updateLayout({ page_width: v })" />
      <NumberField label="Высота (px)" :value="pageLayout.page_height" :min="320" :max="3600" @change="v => updateLayout({ page_height: v })" />
      <NumberField label="Отступ сверху"    :value="pageLayout.margin_top"    :min="0" :max="600" @change="v => updateLayout({ margin_top: v })" />
      <NumberField label="Отступ справа"  :value="pageLayout.margin_right"  :min="0" :max="600" @change="v => updateLayout({ margin_right: v })" />
      <NumberField label="Отступ снизу" :value="pageLayout.margin_bottom" :min="0" :max="600" @change="v => updateLayout({ margin_bottom: v })" />
      <NumberField label="Отступ слева"   :value="pageLayout.margin_left"   :min="0" :max="600" @change="v => updateLayout({ margin_left: v })" />
      <div class="flex gap-2 ml-auto">
        <button type="button" class="btn-secondary btn-sm" @click="setPreset('a4')">A4</button>
        <button type="button" class="btn-secondary btn-sm" @click="setPreset('letter')">Letter</button>
        <button type="button" class="btn-secondary btn-sm" @click="setPreset('wide')">Широкая</button>
      </div>
    </div>

    <!-- Paragraph spacing popover -->
    <div v-if="popover === 'para'" class="px-4 py-3 border-t border-slate-100 bg-slate-50 flex flex-wrap items-end gap-4 text-xs">
      <PxField label="Отступ сверху"    :value="paragraphAttrs.marginTop"    @change="v => $emit('setParagraphAttr', 'marginTop', v)" />
      <PxField label="Отступ снизу" :value="paragraphAttrs.marginBottom" @change="v => $emit('setParagraphAttr', 'marginBottom', v)" />
      <PxField label="Отступ слева"   :value="paragraphAttrs.marginLeft"   @change="v => $emit('setParagraphAttr', 'marginLeft', v)" />
      <PxField label="Отступ справа"  :value="paragraphAttrs.marginRight"  @change="v => $emit('setParagraphAttr', 'marginRight', v)" />
      <PxField label="Отступ первой строки" :value="paragraphAttrs.textIndent" @change="v => $emit('setParagraphAttr', 'textIndent', v)" />
      <button type="button" class="btn-ghost btn-sm" @click="resetParagraph">Сбросить абзац</button>
    </div>

    <!-- Header / footer / page-number controls popover -->
    <div v-if="popover === 'hf'" class="px-4 py-3 border-t border-slate-100 bg-slate-50 flex flex-wrap items-end gap-4 text-xs">
      <button type="button" class="btn-secondary btn-sm" @click="$emit('toggleHeader')">
        {{ headerActive ? 'Закрыть верхний колонтитул' : 'Изменить верхний колонтитул' }}
      </button>
      <button type="button" class="btn-secondary btn-sm" @click="$emit('toggleFooter')">
        {{ footerActive ? 'Закрыть нижний колонтитул' : 'Изменить нижний колонтитул' }}
      </button>
      <label class="flex items-center gap-1 text-slate-600">
        <input
          type="checkbox"
          :checked="showPageNumbers"
          @change="e => $emit('setPageNumbers', (e.target as HTMLInputElement).checked)"
        />
        Показывать номера страниц
      </label>
      <NumberField label="Начать со страницы" :value="pageNumberStart" :min="1" :max="99999" @change="v => $emit('setPageNumberStart', v)" />
      <button
        type="button"
        class="btn-secondary btn-sm"
        title="Перезапустить нумерацию страниц с позиции курсора"
        @click="insertRestartBreak"
      >
        Вставить разрыв «новая нумерация»
      </button>
    </div>

    <!-- Find &amp; replace bar -->
    <div v-if="showFind" class="px-4 py-2 border-t border-slate-100 bg-slate-50 flex flex-wrap items-center gap-2 text-xs">
      <input
        v-model="findQuery"
        type="text"
        class="input h-8 w-48"
        placeholder="Найти"
        @keydown.enter.prevent="goNext"
        @input="onFindInput"
      />
      <input
        v-model="replaceText"
        type="text"
        class="input h-8 w-48"
        placeholder="Заменить на"
      />
      <label class="flex items-center gap-1 text-slate-600">
        <input type="checkbox" v-model="caseSensitive" @change="onFindInput" />
        С учётом регистра
      </label>
      <span v-if="findResults.length" class="text-slate-500">
        {{ findActive + 1 }} / {{ findResults.length }}
      </span>
      <span v-else-if="findQuery" class="text-slate-400">Ничего не найдено</span>
      <div class="flex gap-1 ml-auto">
        <Btn title="Предыдущее (Shift+Enter)" @click="goPrev"><svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M14 7l-5 5 5 5V7z"/></svg></Btn>
        <Btn title="Следующее (Enter)" @click="goNext"><svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M10 17l5-5-5-5v10z"/></svg></Btn>
        <button class="btn-secondary btn-sm" @click="doReplace" :disabled="!findResults.length">Заменить</button>
        <button class="btn-secondary btn-sm" @click="doReplaceAll" :disabled="!findResults.length">Заменить всё</button>
        <button class="btn-ghost btn-sm" @click="toggleFind">Закрыть</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, defineComponent, h, onMounted, onBeforeUnmount } from 'vue'
import type { Editor } from '@tiptap/vue-3'
import apiClient from '../../api/client'
import { findReplaceKey } from './FindReplace'
import type { PageLayout } from '../../types'

const props = defineProps<{
  editor: Editor
  docId?: number
  docTitle?: string
  pageLayout: PageLayout
  showPageNumbers?: boolean
  pageNumberStart?: number
  headerActive?: boolean
  footerActive?: boolean
  /** Tiptap JSON for the header band (or empty doc). */
  headerJson?: unknown
  /** Tiptap JSON for the footer band (or empty doc). */
  footerJson?: unknown
  paragraphAttrs: {
    marginTop: string
    marginBottom: string
    marginLeft: string
    marginRight: string
    textIndent: string
  }
}>()

const emit = defineEmits<{
  docxImported: [payload: { content: unknown }]
  updatePageLayout: [layout: Partial<PageLayout> & {
    show_page_numbers?: boolean
    page_number_start?: number
  }]
  toggleHeader: []
  toggleFooter: []
  setPageNumbers: [v: boolean]
  setPageNumberStart: [v: number]
  setParagraphAttr: [which: 'marginTop' | 'marginRight' | 'marginBottom' | 'marginLeft' | 'textIndent', value: string]
}>()

// ── constants ─────────────────────────────────────────────────────────────────

const FONTS = [
  'Arial', 'Times New Roman', 'Courier New', 'Georgia', 'Verdana',
  'Trebuchet MS', 'Comic Sans MS', 'Impact', 'Tahoma', 'Calibri',
  'Cambria', 'Garamond', 'Palatino',
]

const SIZES = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 32, 36, 40, 48, 60, 72]

const LINE_HEIGHTS = ['1', '1.15', '1.5', '2', '2.5', '3']
// Note: font and size lists stay as-is — they're proper names and numbers.

// ── reactive state ────────────────────────────────────────────────────────────

const imageInputRef = ref<HTMLInputElement | null>(null)
const docxInputRef  = ref<HTMLInputElement | null>(null)
const isImporting   = ref(false)
const isExporting   = ref(false)
const importError   = ref('')

const popover = ref<'' | 'page' | 'para' | 'hf'>('')

const showFind = ref(false)
const findQuery = ref('')
const replaceText = ref('')
const caseSensitive = ref(false)
const findResults = ref<Array<{ from: number; to: number }>>([])
const findActive = ref(-1)

let unbindEditorUpdate: (() => void) | null = null

onMounted(() => {
  const handler = () => {
    const s = findReplaceKey.getState(props.editor.state)
    if (s) {
      findResults.value = s.results
      findActive.value = s.active
    }
  }
  props.editor.on('transaction', handler)
  unbindEditorUpdate = () => props.editor.off('transaction', handler)

  document.addEventListener('keydown', onGlobalKeydown)
})

onBeforeUnmount(() => {
  unbindEditorUpdate?.()
  document.removeEventListener('keydown', onGlobalKeydown)
})

function onGlobalKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f') {
    e.preventDefault()
    toggleFind()
  }
}

function togglePop(name: 'page' | 'para' | 'hf') {
  popover.value = popover.value === name ? '' : name
}

// ── computed from editor state ────────────────────────────────────────────────

const currentFontFamily = computed(() => {
  // Empty fontFamily mark = use the editor's CSS default, which is Times
  // New Roman. Show that in the dropdown so the user sees the truth.
  return props.editor.getAttributes('textStyle').fontFamily || 'Times New Roman'
})

const currentFontSize = computed(() => {
  // Sizes are emitted as a CSS unit string ("12pt"). Older documents may
  // still hold "12px" — strip the unit and re-emit as pt so the dropdown
  // option matches.
  const raw = props.editor.getAttributes('textStyle').fontSize ?? ''
  if (!raw) return ''
  const m = String(raw).match(/^([\d.]+)/)
  if (!m) return ''
  const n = parseFloat(m[1])
  if (isNaN(n)) return ''
  return `${Math.round(n)}pt`
})
const currentColor = computed(() => props.editor.getAttributes('textStyle').color ?? '#000000')
const currentHighlight = computed(() => props.editor.getAttributes('highlight').color ?? '')

const currentHeading = computed(() => {
  for (let lvl = 1; lvl <= 6; lvl++) {
    if (props.editor.isActive('heading', { level: lvl })) return String(lvl)
  }
  return '0'
})

const currentLineHeight = computed(() => {
  const fromBlock =
    props.editor.getAttributes('paragraph').lineHeight ||
    props.editor.getAttributes('heading').lineHeight
  return fromBlock ?? ''
})

const paragraphAttrs = computed(() => props.paragraphAttrs)

// ── formatting commands ───────────────────────────────────────────────────────

function applyFontFamily(value: string) {
  if (value) props.editor.chain().focus().setFontFamily(value).run()
  else props.editor.chain().focus().unsetFontFamily().run()
}
function applyFontSize(value: string) {
  if (value) props.editor.chain().focus().setFontSize(value).run()
  else props.editor.chain().focus().unsetFontSize().run()
}
function applyColor(value: string) {
  props.editor.chain().focus().setColor(value).run()
}
function applyHighlight(value: string) {
  props.editor.chain().focus().setHighlight({ color: value }).run()
}
function applyLineHeight(value: string) {
  if (value) props.editor.chain().focus().setLineHeight(value).run()
  else props.editor.chain().focus().unsetLineHeight().run()
}

function setHeading(e: Event) {
  const level = parseInt((e.target as HTMLSelectElement).value)
  if (level === 0) {
    props.editor.chain().focus().setParagraph().run()
  } else {
    props.editor.chain().focus().toggleHeading({ level: level as 1 | 2 | 3 | 4 | 5 | 6 }).run()
  }
}

function onInsertLink() {
  const current = props.editor.getAttributes('link').href ?? ''
  const url = window.prompt('Введите URL', current)
  if (url === null) return
  if (url === '') {
    props.editor.chain().focus().unsetLink().run()
    return
  }
  props.editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
}

// ── page layout ───────────────────────────────────────────────────────────────

function updateLayout(patch: Partial<PageLayout>) {
  emit('updatePageLayout', patch)
}

function setPreset(name: 'a4' | 'letter' | 'wide') {
  if (name === 'a4') {
    updateLayout({ page_width: 794, page_height: 1123, margin_top: 96, margin_right: 96, margin_bottom: 96, margin_left: 96 })
  } else if (name === 'letter') {
    updateLayout({ page_width: 816, page_height: 1056, margin_top: 96, margin_right: 96, margin_bottom: 96, margin_left: 96 })
  } else {
    updateLayout({ page_width: 1120, page_height: 1400, margin_top: 64, margin_right: 96, margin_bottom: 64, margin_left: 96 })
  }
}

// ── paragraph / page break ────────────────────────────────────────────────────

function resetParagraph() {
  props.editor.chain().focus().resetParagraphSpacing().run()
}

function insertPageBreak() {
  props.editor.chain().focus().insertPageBreak().run()
}

function insertSectionBreak() {
  const startAtStr = window.prompt(
    'Перезапустить нумерацию страниц с (оставьте пустым, чтобы продолжить с предыдущей):',
    '1',
  )
  if (startAtStr === null) return
  if (startAtStr.trim() === '') {
    props.editor.chain().focus().insertSectionBreak({ restartNumbering: false }).run()
    return
  }
  const startAt = parseInt(startAtStr, 10)
  props.editor.chain().focus().insertSectionBreak({
    restartNumbering: true,
    numberStart: isNaN(startAt) ? 1 : startAt,
  }).run()
}

function insertRestartBreak() {
  const startAtStr = window.prompt('Перезапустить нумерацию страниц с:', '1')
  if (startAtStr === null) return
  const startAt = parseInt(startAtStr, 10)
  props.editor.chain().focus().insertPageBreakResetNumbering(isNaN(startAt) ? 1 : startAt).run()
}

// ── find &amp; replace ─────────────────────────────────────────────────────────

function toggleFind() {
  showFind.value = !showFind.value
  if (showFind.value) {
    setTimeout(() => onFindInput(), 0)
  } else {
    props.editor.commands.clearSearch()
  }
}

function onFindInput() {
  props.editor.commands.setSearch(findQuery.value, caseSensitive.value)
  scrollActiveMatchIntoView()
}
function goNext() {
  props.editor.commands.gotoNextMatch()
  scrollActiveMatchIntoView()
}
function goPrev() {
  props.editor.commands.gotoPrevMatch()
  scrollActiveMatchIntoView()
}
function doReplace() {
  props.editor.commands.replaceCurrent(replaceText.value)
  scrollActiveMatchIntoView()
}
function doReplaceAll() { props.editor.commands.replaceAll(replaceText.value) }

/**
 * The editor's scrollable container is two ancestors above the
 * contenteditable element, so ProseMirror's built-in ``tr.scrollIntoView()``
 * does not always succeed in scrolling the active match into view —
 * especially when the toolbar's find input owns focus. We manually walk to
 * the active-match decoration and centre it in its scroll parent on the
 * next tick.
 */
function scrollActiveMatchIntoView() {
  // Wait for the editor to flush its decorations to the DOM.
  requestAnimationFrame(() => {
    const root = props.editor.view.dom as HTMLElement
    const target = root.querySelector<HTMLElement>('.find-match-active')
    if (!target) return
    target.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' })
  })
}

// ── image upload ──────────────────────────────────────────────────────────────

async function onImageSelected(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file || !props.docId) return
  if (imageInputRef.value) imageInputRef.value.value = ''

  try {
    const formData = new FormData()
    formData.append('image', file)
    const { data } = await apiClient.post<{ url: string }>(
      `/api/docs/${props.docId}/images/`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    // resolveMediaUrl applies API base when the URL is relative.
    const { resolveMediaUrl } = await import('../../utils/media')
    const src = resolveMediaUrl(data.url) ?? data.url
    props.editor.chain().focus().setImage({ src }).run()
  } catch (err) {
    console.error('Image upload failed', err)
  }
}

// ── DOCX import (server-side) ─────────────────────────────────────────────────

async function onDocxImport(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (docxInputRef.value) docxInputRef.value.value = ''
  if (!props.docId) {
    importError.value = 'Документ должен быть сохранён перед импортом.'
    return
  }

  isImporting.value = true
  importError.value = ''
  try {
    const formData = new FormData()
    formData.append('file', file)
    // The backend parses the DOCX, rewrites the document, broadcasts a
    // full_replace over the WS and returns the updated record. We hand
    // the resulting content up to DocumentView so it can update local
    // state without waiting for the WS round-trip.
    const { data } = await apiClient.post<{ content: string }>(
      `/api/docs/${props.docId}/import-docx/`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    )
    let parsed: unknown = data.content
    if (typeof parsed === 'string') {
      try { parsed = JSON.parse(parsed) } catch { /* leave as string */ }
    }
    emit('docxImported', { content: parsed })
  } catch (err: any) {
    console.error('DOCX import failed', err)
    importError.value =
      err?.response?.data?.file?.[0]
      ?? err?.response?.data?.detail
      ?? 'Не удалось импортировать этот DOCX-файл.'
  } finally {
    isImporting.value = false
  }
}

async function onDocxExport() {
  isExporting.value = true
  try {
    const { exportToDocx } = await import('../../utils/docxExport')
    await exportToDocx(
      props.editor.getJSON(),
      props.docTitle ?? 'document',
      {
        pageLayout: props.pageLayout,
        headerJson: props.headerJson ?? null,
        footerJson: props.footerJson ?? null,
        showPageNumbers: !!props.showPageNumbers,
        pageNumberStart: props.pageNumberStart ?? 1,
      },
    )
  } catch (err) {
    console.error('DOCX export failed', err)
  } finally {
    isExporting.value = false
  }
}

// ── sub-components ────────────────────────────────────────────────────────────

const Btn = defineComponent({
  props: { active: Boolean, title: String, disabled: Boolean },
  emits: ['click'],
  setup(p, { slots, emit }) {
    return () =>
      h('button', {
        type: 'button',
        title: p.title,
        disabled: p.disabled,
        class: [
          'w-7 h-7 flex items-center justify-center rounded text-xs transition-colors',
          p.disabled
            ? 'text-slate-300 cursor-not-allowed'
            : p.active
            ? 'bg-primary-100 text-primary-700'
            : 'text-slate-500 hover:bg-slate-100 hover:text-slate-800',
        ],
        onClick: () => !p.disabled && emit('click'),
      }, slots.default?.())
  },
})

const Sep = defineComponent({
  setup: () => () => h('div', { class: 'w-px h-5 bg-slate-200 mx-0.5 shrink-0' }),
})

const NumberField = defineComponent({
  props: { label: String, value: Number, min: Number, max: Number },
  emits: ['change'],
  setup(p, { emit }) {
    return () =>
      h('div', { class: 'flex flex-col gap-1' }, [
        h('label', { class: 'text-slate-600 font-medium' }, p.label),
        h('input', {
          type: 'number',
          min: p.min,
          max: p.max,
          step: 8,
          value: p.value,
          class: 'input w-24 h-8',
          onChange: (e: Event) => {
            const n = (e.target as HTMLInputElement).valueAsNumber
            if (!isNaN(n)) emit('change', Math.min(p.max ?? 9999, Math.max(p.min ?? 0, n)))
          },
        }),
      ])
  },
})

const PxField = defineComponent({
  props: { label: String, value: String },
  emits: ['change'],
  setup(p, { emit }) {
    return () => {
      const numeric = parseInt((p.value ?? '').toString(), 10)
      return h('div', { class: 'flex flex-col gap-1' }, [
        h('label', { class: 'text-slate-600 font-medium' }, p.label),
        h('div', { class: 'flex items-center gap-1' }, [
          h('input', {
            type: 'number',
            step: 4,
            value: isNaN(numeric) ? '' : numeric,
            class: 'input w-20 h-8',
            onChange: (e: Event) => {
              const n = (e.target as HTMLInputElement).valueAsNumber
              if (isNaN(n)) emit('change', '')
              else emit('change', `${n}px`)
            },
          }),
          h('button', {
            type: 'button',
            class: 'btn-ghost btn-sm px-2 py-0.5',
            onClick: () => emit('change', ''),
          }, '✕'),
        ]),
      ])
    }
  },
})
</script>

<style scoped>
.toolbar-select {
  @apply h-7 px-1.5 rounded text-xs border border-slate-200 text-slate-700 bg-white focus:outline-none focus:border-primary-400;
}
</style>
