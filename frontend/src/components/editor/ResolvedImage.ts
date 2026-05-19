import Image from '@tiptap/extension-image'
import { mergeAttributes } from '@tiptap/core'
import { resolveMediaUrl } from '../../utils/media'

/**
 * Drop-in replacement for Tiptap's ``Image`` that resolves relative
 * ``/media/...`` URLs (the ones our DOCX importer and image-upload
 * endpoint produce) through ``resolveMediaUrl`` whenever the editor
 * renders the ``<img>`` element.
 *
 * Why we need this:
 *   The browser sees ``<img src="/media/docs/4/x.png">`` and resolves it
 *   against the current page origin — in dev that's ``http://localhost:5173``
 *   (Vite), which has no media to serve, so the request 404s. The Django
 *   API lives at ``http://localhost:8000``. Prepending the API base at
 *   render time fixes the request without requiring a Vite proxy restart
 *   and without baking an environment-specific absolute URL into the
 *   document's stored JSON (which would break across deployments).
 *
 * The stored ``src`` attribute is unchanged — only the rendered DOM is
 * rewritten. ``editor.getJSON()`` still returns the original relative
 * path, so saves and round-trips remain portable.
 */
export const ResolvedImage = Image.extend({
  renderHTML({ HTMLAttributes }) {
    const attrs = { ...HTMLAttributes }
    const src = attrs.src
    if (typeof src === 'string') {
      attrs.src = resolveMediaUrl(src) ?? src
    }
    return [
      'img',
      mergeAttributes(this.options.HTMLAttributes, attrs),
    ]
  },
})
