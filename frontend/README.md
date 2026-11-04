# AutoValue frontend

Next.js App Router + TypeScript + Tailwind frontend for the Used Car Appraisal and Management System.

## Setup

```bash
npm install
cp .env.example .env.local # optional
npm run dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` to the backend base URL. The UI
uses `POST /api/appraisals` and `GET /api/inventory`; without an API URL it
uses a small local inventory preview so the screens remain usable.
