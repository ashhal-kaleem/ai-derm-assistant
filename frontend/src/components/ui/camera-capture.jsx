import React, { useCallback, useEffect, useRef, useState } from "react";
import { Camera, X, RefreshCw, Loader2 } from "lucide-react";

// Opens the device camera (laptop webcam, phone front/back) in a live preview
// using getUserMedia. Falls back to the native file input with `capture`
// (which opens the phone camera app) when live camera access isn't possible.
export function CameraCapture({ onCapture, onError }) {
  const [open, setOpen] = useState(false);
  const [starting, setStarting] = useState(false);
  const [facingMode, setFacingMode] = useState("environment");
  const [hasMultipleCameras, setHasMultipleCameras] = useState(false);
  const [error, setError] = useState(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const fallbackInputRef = useRef(null);

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const startStream = useCallback(
    async (mode) => {
      stopStream();
      setStarting(true);
      setError(null);
      try {
        let stream;
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: { ideal: mode }, width: { ideal: 1920 }, height: { ideal: 1080 } },
            audio: false,
          });
        } catch (err) {
          if (err?.name === "NotAllowedError" || err?.name === "SecurityError") throw err;
          // Some laptops reject facingMode/resolution constraints; retry with any camera.
          stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch(() => {});
        }
        try {
          const devices = await navigator.mediaDevices.enumerateDevices();
          setHasMultipleCameras(devices.filter((d) => d.kind === "videoinput").length > 1);
        } catch {
          /* ignore */
        }
      } catch (err) {
        const msg =
          err?.name === "NotAllowedError" || err?.name === "SecurityError"
            ? "Camera permission was blocked. Allow camera access in your browser's site settings, then try again."
            : err?.name === "NotFoundError" || err?.name === "OverconstrainedError"
            ? "No camera was found on this device."
            : err?.name === "NotReadableError"
            ? "The camera is being used by another app. Close it and try again."
            : "Couldn't open the camera.";
        setError(msg);
        onError?.(msg);
      } finally {
        setStarting(false);
      }
    },
    [stopStream, onError]
  );

  const openCamera = () => {
    if (!navigator.mediaDevices?.getUserMedia || !window.isSecureContext) {
      // No live camera API (old browser / non-HTTPS): use the native camera picker.
      fallbackInputRef.current?.click();
      return;
    }
    setOpen(true);
  };

  useEffect(() => {
    if (open) startStream(facingMode);
    return () => {
      if (!open) stopStream();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, facingMode]);

  useEffect(() => () => stopStream(), [stopStream]);

  const close = () => {
    stopStream();
    setOpen(false);
    setError(null);
  };

  const takePhoto = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (facingMode === "user") {
      // Un-mirror the selfie preview so the saved photo matches reality.
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const file = new File([blob], `camera-${Date.now()}.jpg`, { type: "image/jpeg" });
        onCapture?.(file);
        close();
      },
      "image/jpeg",
      0.92
    );
  };

  return (
    <>
      <button
        type="button"
        onClick={openCamera}
        className="flex items-center gap-2 text-xs font-medium text-slate-600 hover:text-emerald-700 cursor-pointer p-2 rounded-xl hover:bg-emerald-50 transition-colors"
      >
        <Camera className="w-4 h-4 text-emerald-600" />
        <span>Capture via Device Camera</span>
      </button>

      <input
        ref={fallbackInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onCapture?.(f);
          e.target.value = "";
        }}
      />

      {open && (
        <div className="fixed inset-0 z-[100] bg-black/90 flex flex-col items-center justify-center p-4">
          <button
            type="button"
            onClick={close}
            aria-label="Close camera"
            className="absolute top-4 right-4 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white"
          >
            <X className="w-6 h-6" />
          </button>

          <div className="relative w-full max-w-2xl aspect-[4/3] bg-black rounded-2xl overflow-hidden">
            <video
              ref={videoRef}
              playsInline
              muted
              autoPlay
              className={`w-full h-full object-cover ${facingMode === "user" ? "scale-x-[-1]" : ""}`}
            />
            {starting && (
              <div className="absolute inset-0 flex items-center justify-center text-white">
                <Loader2 className="w-8 h-8 animate-spin" />
              </div>
            )}
            {error && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center text-white p-6 gap-4">
                <p className="text-sm">{error}</p>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => startStream(facingMode)}
                    className="px-4 py-2 rounded-xl bg-emerald-600 text-sm font-semibold"
                  >
                    Try again
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      close();
                      fallbackInputRef.current?.click();
                    }}
                    className="px-4 py-2 rounded-xl bg-white/15 text-sm font-semibold"
                  >
                    Choose a photo instead
                  </button>
                </div>
              </div>
            )}
          </div>

          {!error && (
            <div className="mt-6 flex items-center gap-8">
              {hasMultipleCameras ? (
                <button
                  type="button"
                  onClick={() => setFacingMode((m) => (m === "user" ? "environment" : "user"))}
                  aria-label="Switch camera"
                  className="p-3 rounded-full bg-white/10 hover:bg-white/20 text-white"
                >
                  <RefreshCw className="w-6 h-6" />
                </button>
              ) : (
                <span className="w-12" />
              )}
              <button
                type="button"
                onClick={takePhoto}
                disabled={starting}
                aria-label="Take photo"
                className="w-16 h-16 rounded-full bg-white border-4 border-emerald-500 disabled:opacity-50"
              />
              <span className="w-12" />
            </div>
          )}
          <p className="mt-3 text-xs text-white/60">Hold the camera close to the skin area in good light.</p>
        </div>
      )}
    </>
  );
}

export default CameraCapture;
