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
  is_favorite?: boolean
}

export interface PageLayout {
  page_width: number
  page_height: number
  margin_top: number
  margin_right: number
  margin_bottom: number
  margin_left: number
}

export interface PageSettings {
  header_content: string
  footer_content: string
  show_page_numbers: boolean
  page_number_start: number
}

export interface Document extends PageLayout, PageSettings {
  id: number
  title: string
  content: string
  is_public: boolean
  status_text: string
  status_color: string
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
  is_favorite?: boolean
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
