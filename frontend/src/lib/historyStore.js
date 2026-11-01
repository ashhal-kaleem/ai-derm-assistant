// Keeps track of WHICH lesions this device has saved.
// The backend has no "list all lesions" endpoint (only GET /history/{lesion_id}),
// so we remember the lesion_ids here and fetch each timeline from the server.
// Thumbnails are kept here too because the backend only stores a truncated image string.

const KEY = "dermassist.tracked_lesions.v1";

export function loadTracked() {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function persist(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch {
    // storage full or blocked: history still works from the server, only thumbnails are lost
  }
}

export function trackVisit({ lesion_id, lesion_name, visit_id, thumb }) {
  const list = loadTracked();
  const now = new Date().toISOString();
  const existing = list.find((l) => l.lesion_id === lesion_id);
  if (existing) {
    existing.lesion_name = lesion_name;
    existing.thumbs = { ...(existing.thumbs || {}), [visit_id]: thumb };
    existing.updated_at = now;
  } else {
    list.unshift({
      lesion_id,
      lesion_name,
      thumbs: { [visit_id]: thumb },
      updated_at: now,
    });
  }
  persist(list);
}

export function removeTracked(lesion_id) {
  persist(loadTracked().filter((l) => l.lesion_id !== lesion_id));
}

// Shrinks a data URL to a small square JPEG so it fits comfortably in localStorage.
export function makeThumb(dataUrl, size = 240) {
  return new Promise((resolve) => {
    if (!dataUrl) return resolve(null);
    const img = new Image();
    img.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext("2d");
        const side = Math.min(img.width, img.height);
        const sx = (img.width - side) / 2;
        const sy = (img.height - side) / 2;
        ctx.drawImage(img, sx, sy, side, side, 0, 0, size, size);
        resolve(canvas.toDataURL("image/jpeg", 0.72));
      } catch {
        resolve(null);
      }
    };
    img.onerror = () => resolve(null);
    img.src = dataUrl;
  });
}
