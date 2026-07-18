# AI-Powered Cloud SBAR Voice Handover System

An end-to-end, serverless cloud architecture designed to modernize clinical shift handovers in hospitals. This system allows doctors and nurses to verbally record patient handovers (supporting English and "Minglish") and automatically converts them into structured SBAR (Situation, Background, Assessment, Recommendation) formats using AI.

## ⚠️ The Problem
In fast-paced clinical environments (particularly in Southeast Asia/Pakistan), shift handovers are often rushed, informal, or jotted down on scattered pieces of paper. Doctors frequently communicate in a mix of English and local languages (e.g., Urdu/Hindi written as English alphabets, known as "Minglish"). This leads to:
- Critical patient information being lost or misunderstood between shifts.
- Lack of standardized medical documentation.
- Significant time wasted manually transcribing or structuring handover notes.

## 💡 The Solution
A seamless, voice-first web dashboard that completely automates the SBAR reporting process. 
1. **Record:** A medical professional taps the microphone and speaks naturally about the patient.
2. **Process:** The audio is securely uploaded to the cloud, where it is transcribed.
3. **Analyze:** A Large Language Model processes the raw (potentially Minglish) transcript and maps it directly into the gold-standard SBAR clinical format.
4. **Dashboard:** The structured data is instantly available on a responsive, modern web dashboard for the incoming shift team to review.

## 🚀 Tech Stack & Architecture

This project is built heavily around **AWS Serverless** technologies to ensure high availability, zero maintenance overhead, and HIPAA-compliant scalability.

### Frontend
- **React & Vite:** Lightning-fast, modern single-page application.
- **Tailwind CSS & Radix UI:** Premium, accessible, and highly responsive user interface designed for clinical visibility.
- **TanStack Router:** Type-safe routing and layout management.
- **Vercel:** (Targeted) Seamless global edge deployment.

### Cloud Backend (AWS)
- **AWS API Gateway:** RESTful entry point with strict CORS policies and routing.
- **AWS Lambda:** Serverless compute powering the core business logic (fetching records, generating upload URLs, and processing audio).
- **Amazon S3:** Secure, durable object storage for handling raw `.webm` voice recordings. Utilizes pre-signed URLs to allow secure, direct-from-browser uploads without passing heavy files through API Gateway.
- **Amazon DynamoDB:** Fully managed NoSQL database storing structured SBAR reports with sub-millisecond retrieval times.

### AI Pipeline
- **Transcription Engine:** Custom API integration capable of parsing "Minglish" phonetic text accurately.
- **LLM Structuring:** System-prompted AI generation that identifies medical entities and categorizes them strictly into the `Situation`, `Background`, `Assessment`, and `Recommendation` schema.

