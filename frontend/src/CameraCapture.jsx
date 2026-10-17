import React, { useRef, useState, useEffect } from 'react'

const CameraCapture = ({ onCapture, onClose }) => {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const [stream, setStream] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const startCamera = async () => {
      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480 }
        })
        setStream(mediaStream)
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream
        }
      } catch (err) {
        setError('Cannot access camera: ' + err.message)
      }
    }
    startCamera()

    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  const capture = () => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    canvas.toBlob((blob) => {
      const file = new File([blob], `camera_${Date.now()}.jpg`, { type: 'image/jpeg' })
      onCapture(file)
      closeCamera()
    }, 'image/jpeg', 0.9)
  }

  const closeCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
    }
    onClose()
  }

  return (
    <div style={{
      position: 'fixed', inset: 0,
      background: 'rgba(0,0,0,0.9)',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      zIndex: 2000, padding: '20px'
    }}>
      <h2 style={{ color: 'white', marginBottom: '20px' }}>📷 Camera Capture</h2>

      {error ? (
        <div style={{ color: '#f87171', padding: '20px', background: '#1a2332', borderRadius: '10px' }}>
          {error}
        </div>
      ) : (
        <>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            style={{
              width: '100%', maxWidth: '640px',
              borderRadius: '12px',
              border: '2px solid #3b82f6',
              transform: 'scaleX(-1)'
            }}
          />
          <canvas ref={canvasRef} style={{ display: 'none' }} />

          <div style={{ display: 'flex', gap: '16px', marginTop: '20px' }}>
            <button
              onClick={capture}
              className="btn-primary"
              style={{ padding: '14px 32px', fontSize: '16px' }}
            >
              📸 Capture
            </button>
            <button
              onClick={closeCamera}
              className="btn-secondary"
              style={{ padding: '14px 32px', fontSize: '16px' }}
            >
              ✕ Cancel
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default CameraCapture
