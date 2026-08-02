import { useEffect, useRef } from 'react'
import type { ClassNameProps } from '../../types'

export default function BrandLogo({ className = 'h-8 w-auto' }: ClassNameProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const image = new Image()
    image.src = '/brand-logo-chroma.png'
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
        const greenDominance = green - Math.max(red, blue)

        if (green > 150 && greenDominance > 55) {
          pixels[index + 3] = Math.max(0, 255 - greenDominance * 3)
        }

        pixels[index] = 37
        pixels[index + 1] = 99
        pixels[index + 2] = 235
      }
      context.putImageData(frame, 0, 0)
    }
  }, [])

  return <canvas ref={canvasRef} className={className} role="img" aria-label="joopjoop" />
}
