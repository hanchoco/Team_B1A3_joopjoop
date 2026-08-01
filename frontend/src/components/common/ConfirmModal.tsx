import type { ReactNode } from 'react'

interface ConfirmModalProps {
  title: string
  description?: ReactNode
  icon?: ReactNode
  confirmLabel?: string
  onConfirm: () => void
  cancelLabel?: string
  onCancel?: () => void
  titleId?: string
}

export default function ConfirmModal({
  title,
  description,
  icon,
  confirmLabel = '확인',
  onConfirm,
  cancelLabel,
  onCancel,
  titleId = 'confirm-modal-title',
}: ConfirmModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-gray-950/35 px-5"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <div className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-6 text-center shadow-xl">
        {icon && <div className="mx-auto flex justify-center">{icon}</div>}
        <h2 id={titleId} className="mt-2 text-xl font-black">
          {title}
        </h2>
        {description && (
          <p className="mt-2 text-sm leading-6 text-gray-500">{description}</p>
        )}
        <div className={`mt-6 grid gap-3 ${cancelLabel && onCancel ? 'grid-cols-2' : 'grid-cols-1'}`}>
          {cancelLabel && onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="rounded-lg border border-gray-300 bg-white py-3 text-sm font-bold text-gray-700"
            >
              {cancelLabel}
            </button>
          )}
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-lg bg-blue-600 py-3 text-sm font-bold text-white"
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
