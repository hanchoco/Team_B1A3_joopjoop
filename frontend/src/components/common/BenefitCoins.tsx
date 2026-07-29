import { useEffect, useRef } from 'react'
import type { ClassNameProps } from '../../types'

export default function BenefitCoins({ className = 'h-20 w-24' }: ClassNameProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const image = new Image()
    image.src = '/benefit-coins-simple-chroma.png'
    image.onload = () => {
      const canvas = canvasRef.current
      if (!canvas) return
      const context = canvas.getContext('2d', { willReadFrequently: true })
      if (!context) return
      canvas.width = image.naturalWidth
      canvas.height = image.naturalHeight
      context.drawImage(image, 0, 0)

      const frame = context.getImageData(0, 0, canvas.width, canvas.height)
      const pixels = frame.data
      for (let index = 0; index < pixels.length; index += 4) {
        const red = pixels[index]
        const green = pixels[index + 1]
        const blue = pixels[index + 2]
        const dominance = green - Math.max(red, blue)
        if (green > 145 && dominance > 45) {
          pixels[index + 3] = Math.max(0, 255 - dominance * 3.2)
        }
      }
      context.putImageData(frame, 0, 0)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className={className}
      role="img"
      aria-label="쌓여 있는 파란 동전 두 더미"
    />
  )
}
