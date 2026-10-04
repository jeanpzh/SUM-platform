import { createFileRoute } from '@tanstack/react-router'
import { ChatView } from '#/components/admin/chat-view'

export const Route = createFileRoute('/admin/chat')({ component: ChatView })
