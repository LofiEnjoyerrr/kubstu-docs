export interface User {
  id: number
  username: string
  first_name: string
  last_name: string
  email: string
  is_staff: boolean
  is_active: boolean
  date_joined: string
  last_login: string | null
  avatar: string | null
  color: string
}

export interface Document {
  id: number
  title: string
  content: string
  is_public: boolean
  owner: string
  owner_id: number
  dt_created: string
  dt_updated: string
}

export interface DocumentAccess {
  id: number
  user_id: number
  username: string
  first_name: string
  last_name: string
  avatar: string | null
  color: string
  role: 'viewer' | 'editor'
  dt_created: string
  dt_updated: string
}

export interface AvailableDocuments {
  owner_documents: Document[]
  opened_documents: Document[]
}

export interface CollaboratorInfo {
  user_id: number | null
  username: string
  color: string
  avatar?: string | null
}

export interface CursorPosition {
  from: number
  to: number
}

export interface CollaboratorCursor extends CollaboratorInfo {
  position: CursorPosition | null
}

export interface Comment {
  id: number
  author_id: number
  author_username: string
  author_color: string
  author_avatar: string | null
  quote: string
  from_pos: number
  to_pos: number
  content: string
  dt_created: string
}
