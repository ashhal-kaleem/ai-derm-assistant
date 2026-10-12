-- DermAssist AI — Supabase Cloud Database & Storage Schema
-- Run this in your Supabase Project Dashboard -> SQL Editor

-- 1. Create Scans Table
CREATE TABLE IF NOT EXISTS public.scans (
    id UUID PRIMARY KEY,
    image_url TEXT NOT NULL,
    heatmap_url TEXT,
    predicted_class TEXT NOT NULL,
    raw_confidence FLOAT NOT NULL,
    calibrated_confidence FLOAT NOT NULL,
    temperature FLOAT NOT NULL,
    uncertainty_score FLOAT NOT NULL,
    risk_level TEXT NOT NULL,
    gemini_summary TEXT,
    feedback TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW())
);

-- 2. Indexes for fast retrieval
CREATE INDEX IF NOT EXISTS idx_scans_created_at ON public.scans (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scans_predicted_class ON public.scans (predicted_class);

-- 3. Row Level Security (RLS)
ALTER TABLE public.scans ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access to scans" 
ON public.scans FOR SELECT 
USING (true);

CREATE POLICY "Allow public insert to scans" 
ON public.scans FOR INSERT 
WITH CHECK (true);

CREATE POLICY "Allow public update to scans" 
ON public.scans FOR UPDATE 
USING (true);

-- 4. Storage Bucket Setup (Run if bucket does not exist)
INSERT INTO storage.buckets (id, name, public)
VALUES ('scans', 'scans', true)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Allow public uploads to scans bucket"
ON storage.objects FOR INSERT
WITH CHECK (bucket_id = 'scans');

CREATE POLICY "Allow public view from scans bucket"
ON storage.objects FOR SELECT
USING (bucket_id = 'scans');

-- 5. Longitudinal Lesion Visits Table
CREATE TABLE IF NOT EXISTS public.lesion_visits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visit_id TEXT UNIQUE NOT NULL,
    lesion_id TEXT NOT NULL,
    lesion_name TEXT NOT NULL,
    date TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    predicted_class TEXT NOT NULL,
    class_name TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    risk_level TEXT NOT NULL,
    risk_label TEXT NOT NULL,
    image_thumb TEXT,
    llm_explanation TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW())
);

CREATE INDEX IF NOT EXISTS idx_lesion_visits_lesion_id ON public.lesion_visits (lesion_id);
CREATE INDEX IF NOT EXISTS idx_lesion_visits_date ON public.lesion_visits (date DESC);

ALTER TABLE public.lesion_visits ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read access to lesion_visits" ON public.lesion_visits;
CREATE POLICY "Allow public read access to lesion_visits" 
ON public.lesion_visits FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow public insert to lesion_visits" ON public.lesion_visits;
CREATE POLICY "Allow public insert to lesion_visits" 
ON public.lesion_visits FOR INSERT WITH CHECK (true);
