export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'https://ai-derm-assistant-api.onrender.com';

export const CLASS_METADATA = {
  mel: { name: 'Melanoma', risk: 'urgent', riskLabel: 'High Risk' },
  nv: { name: 'Melanocytic Nevus', risk: 'benign', riskLabel: 'Benign' },
  bcc: { name: 'Basal Cell Carcinoma', risk: 'urgent', riskLabel: 'High Risk' },
  akiec: { name: 'Actinic Keratosis', risk: 'monitor', riskLabel: 'Moderate Risk' },
  bkl: { name: 'Benign Keratosis', risk: 'benign', riskLabel: 'Benign' },
  df: { name: 'Dermatofibroma', risk: 'benign', riskLabel: 'Benign' },
  vasc: { name: 'Vascular Lesion', risk: 'monitor', riskLabel: 'Moderate Risk' }
};

export const STATIC_KNOWLEDGE_CARDS = {
  'Melanoma': 'Malignant melanocytic neoplasm. Requires urgent formal clinical evaluation, dermoscopic inspection, and potential excision biopsy.',
  'Melanocytic Nevus': 'Common benign mole produced by proliferation of melanocytes. Routine periodic self-monitoring recommended.',
  'Basal Cell Carcinoma': 'Slow-growing locally invasive epidermal skin cancer. Requires specialist evaluation for excision or Mohs micrographic surgery.',
  'Actinic Keratosis': 'Pre-cancerous keratinocytic intraepidermal neoplasm caused by chronic ultraviolet radiation damage.',
  'Benign Keratosis': 'Benign epidermal lesion such as seborrheic keratosis, solar lentigo, or lichen planus-like keratosis.',
  'Dermatofibroma': 'Benign cutaneous fibrohistiocytic lesion, commonly found on extremities with characteristic dimple sign.',
  'Vascular Lesion': 'Benign vascular proliferation including cherry angiomas, pyogenic granulomas, or hemangiomas.'
};
