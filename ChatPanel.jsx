import { useState, useRef, useEffect } from 'react'

export default function ChatPanel({ fetchDevices, messages, setMessages }) {
  const [inputText, setInputText] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [ttsEnabled, setTtsEnabled] = useState(true)
  const [loadingStatus, setLoadingStatus] = useState(null)
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const [toastMessage, setToastMessage] = useState(null)
  
  const showToast = (msg) => {
    setToastMessage(msg)
    if (window.toastTimeout) {
      clearTimeout(window.toastTimeout)
    }
    window.toastTimeout = setTimeout(() => {
      setToastMessage(null)
    }, 5000)
  }
  
  const ttsEnabledRef = useRef(true)
  const feedRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const activeAudioRef = useRef(null)
  const isCancelledRef = useRef(false)

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight
    }
  }, [messages, isLoading])

  const playTTS = async (text) => {
    const res = await fetch('/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    })
    
    if (isCancelledRef.current) {
      throw new Error("Playback cancelled")
    }

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}))
      throw new Error(errData.error || "TTS failed")
    }
    
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const audio = new Audio(url)
    
    if (isCancelledRef.current) {
      return
    }

    // Stop currently playing audio
    if (activeAudioRef.current) {
      activeAudioRef.current.pause()
    }
    activeAudioRef.current = audio
    
    return new Promise((resolve, reject) => {
      audio.onplay = () => {
        setIsAudioPlaying(true)
        resolve()
      }
      audio.onended = () => {
        setIsAudioPlaying(false)
      }
      audio.onpause = () => {
        setIsAudioPlaying(false)
      }
      audio.onerror = (e) => {
        setIsAudioPlaying(false)
        reject(new Error("Audio playback failed"))
      }
      
      if (isCancelledRef.current) {
        setIsAudioPlaying(false)
        reject(new Error("Playback cancelled"))
        return
      }

      audio.play().catch(err => {
        setIsAudioPlaying(false)
        console.error("Audio play failed, showing text fallback:", err)
        resolve()
      })
    })
  }

  const sendMessage = async (textOverride = null, isAudioInput = false) => {
    const textToSend = textOverride !== null ? textOverride : inputText.trim()
    if (!textToSend) return
    
    const userMessage = { sender: 'user', text: textToSend }
    setMessages(prev => [...prev, userMessage])
    
    if (textOverride === null) {
      setInputText('')
    }
    
    setIsLoading(true)
    setLoadingStatus('thinking')
    isCancelledRef.current = false

    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 15000)

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage.text }),
        signal: controller.signal
      })
      clearTimeout(timeoutId)
      const data = await res.json()
      fetchDevices() // Force state update if device was modified
      
      if (isCancelledRef.current) return

      const shouldPlayAudio = isAudioInput || ttsEnabledRef.current
      
      if (shouldPlayAudio) {
        setLoadingStatus('generating_audio')
        try {
          await playTTS(data.response)
          if (!isCancelledRef.current) {
            setMessages(prev => [...prev, { sender: 'bot', text: data.response }])
          }
        } catch (err) {
          console.error("Error playing TTS: ", err)
          if (isCancelledRef.current) return
          
          // Show the bottom toast warning popup
          showToast(`⚠️ Audio compilation failed: ${err.message}`)
          
          // Fallback: ALWAYS show the bot's text response in chat feed
          setMessages(prev => [...prev, { sender: 'bot', text: data.response }])
        }
      } else {
        // Non-audio mode: show text instantly
        setMessages(prev => [...prev, { sender: 'bot', text: data.response }])
      }
      
    } catch (err) {
      if (!isCancelledRef.current) {
        setMessages(prev => [...prev, { sender: 'bot', text: '[Failed to connect with EcoWise. Ensure python server is running and GROQ_API_KEY is configured.]' }])
      }
    } finally {
      setLoadingStatus(null)
      setIsLoading(false)
    }
  }

  const handleStop = () => {
    isCancelledRef.current = true
    
    // Stop active audio
    if (activeAudioRef.current) {
      activeAudioRef.current.pause()
      activeAudioRef.current = null
    }
    setIsAudioPlaying(false)
    
    // Stop loading states
    setLoadingStatus(null)
    setIsLoading(false)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      sendMessage()
    }
  }

       const clearChat = async () => {
     try {
       await fetch('/api/chat/clear', { method: 'POST' })
       setMessages([{
         sender: 'bot',
         text: "Hello there, buddy! EcoWise here. I'm all booted up, synced with your home's telemetry, and ready to keep you company. Let's make some simple, green choices today!"
       }])
     } catch (e) {
       console.error("Error clearing chat memory: ", e)
     }
   }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = event => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        audioChunksRef.current = []
        
        setIsLoading(true)
        setLoadingStatus('transcribing')
        isCancelledRef.current = false
        try {
          const formData = new FormData()
          formData.append('audio', audioBlob, 'recording.webm')
          
          const res = await fetch('/api/stt', {
            method: 'POST',
            body: formData
          })
          
          if (isCancelledRef.current) return
          const data = await res.json()
          
          const transcribedText = (data.text && typeof data.text === 'object') 
            ? (data.text.text || '') 
            : (data.text || '')
            
          if (transcribedText.trim()) {
             sendMessage(transcribedText.trim(), true)
          } else {
             setLoadingStatus(null)
             setIsLoading(false)
          }
        } catch (err) {
          console.error("Error transcribing audio:", err)
          if (!isCancelledRef.current) {
            setLoadingStatus(null)
            setIsLoading(false)
          }
        }
        
        // Cleanup tracks
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (err) {
      console.error("Error accessing microphone:", err)
      alert("Microphone access is required for speech-to-text.")
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  const handleToggleTts = () => {
    const newVal = !ttsEnabled
    setTtsEnabled(newVal)
    ttsEnabledRef.current = newVal
    if (!newVal && activeAudioRef.current) {
      activeAudioRef.current.pause()
      activeAudioRef.current = null
      setIsAudioPlaying(false)
    }
  }

  return (
    <div className="panel" style={{ position: 'relative' }}>
        <div className="panel-header">
            <div className="panel-title">
                <span className="dot-pulse" style={isAudioPlaying ? { background: '#3b82f6', boxShadow: '0 0 8px rgba(59,130,246,0.5)' } : {}}></span>
                <span>{isAudioPlaying ? 'EcoWise is speaking...' : 'Chatting with EcoWise'}</span>
            </div>
            <button className="btn btn-secondary" style={{ padding: '0.5rem 1.2rem', fontSize: '0.85rem' }} onClick={clearChat}>
              Clear Chat
            </button>
        </div>
        <div className="chat-body" id="chat-feed" ref={feedRef}>
            {messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.sender}`}>
                  <div className="message-header">{msg.sender === 'user' ? 'You' : 'EcoWise'}</div>
                  <div>{msg.text}</div>
              </div>
            ))}
             {loadingStatus === 'thinking' && (
               <div className="message loading">
                   <div className="dots-wave">
                       <span></span>
                       <span></span>
                       <span></span>
                   </div>
               </div>
             )}
             {loadingStatus === 'transcribing' && (
               <div className="message loading" style={{ width: 'auto', minWidth: '200px' }}>
                   <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                       <span style={{ fontSize: '1.1rem' }}>🎙️</span>
                       <span style={{ fontSize: '0.85rem', opacity: 0.85, color: 'var(--text-secondary)' }}>Transcribing voice...</span>
                   </div>
               </div>
             )}
             {loadingStatus === 'generating_audio' && (
               <div className="message loading" style={{ width: 'auto', minWidth: '210px' }}>
                   <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                       <span style={{ fontSize: '1.1rem' }}>🔊</span>
                       <span style={{ fontSize: '0.85rem', opacity: 0.85, color: 'var(--text-secondary)' }}>Converting to audio...</span>
                   </div>
               </div>
             )}
          </div>
              <div className="chat-footer-senior">
              {/* Row 1: Voice Accessibility Controls (Highlighting Speech Features) */}
              <div className="voice-controls-row">
                  <button 
                      className={`btn-voice-speak ${isRecording ? 'recording' : ''}`}
                      onClick={toggleRecording}
                      title={isRecording ? "Stop Recording" : "Start Voice Input"}
                  >
                      {isRecording ? '🛑 Tap to Stop Listening' : '🎙️ Tap to Speak (Voice Control)'}
                  </button>
                  
                  <button 
                      className={`btn-voice-toggle ${ttsEnabled ? 'active' : 'inactive'}`} 
                      onClick={handleToggleTts}
                      title={ttsEnabled ? "Mute responses reading" : "Enable responses reading"}
                  >
                      {ttsEnabled ? '🔊 Reads Responses' : '🔇 Reads Responses Muted'}
                  </button>
              </div>

              {/* Row 2: Standard Text Input (with larger input and clear buttons) */}
              <div className="text-input-row">
                  <input 
                    type="text" 
                    className="chat-input-large" 
                    placeholder={isRecording ? "Listening to your voice..." : "Or type your message here..."}
                    value={inputText}
                    onChange={e => setInputText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={isRecording}
                  />
                  {(isLoading || loadingStatus || isAudioPlaying) ? (
                    <button 
                      className="btn-stop-large" 
                      onClick={handleStop} 
                      title="Stop speaking or loading"
                    >
                      🛑 Stop
                    </button>
                  ) : (
                    <button className="btn-send-large" onClick={() => sendMessage(null)}>Send</button>
                  )}
              </div>
          </div>
         {toastMessage && (
           <div className="toast-popup" style={{
             position: 'absolute',
             bottom: '85px',
             left: '50%',
             transform: 'translateX(-50%)',
             background: 'rgba(30, 30, 30, 0.95)',
             color: '#93c5fd',
             padding: '0.75rem 1.5rem',
             borderRadius: '14px',
             boxShadow: '0 8px 24px rgba(0, 0, 0, 0.5)',
             fontSize: '0.88rem',
             fontWeight: '500',
             zIndex: 1000,
             textAlign: 'center',
             backdropFilter: 'blur(12px)',
             border: '1px solid rgba(59, 130, 246, 0.3)',
             animation: 'toastIn 0.3s ease-out',
             maxWidth: '90%',
             whiteSpace: 'nowrap'
           }}>
             {toastMessage}
           </div>
         )}
    </div>
  )
}
