# PDF Logo Replacement Backend

Backend service for Chrome Extension - uses PyMuPDF for pixel-perfect logo replacement.

## Deployment to Railway

### Quick Deploy (5 minutes):

1. **Go to Railway**: https://railway.app/

2. **Sign up with GitHub** (free, no credit card needed)

3. **Create New Project** → **Deploy from GitHub repo**

4. **Upload these files**:
   - `main.py`
   - `requirements.txt`
   - `railway.json`

5. **Railway will auto-deploy!**

6. **Get your URL**: 
   - Go to Settings → Generate Domain
   - Copy the URL (e.g., `https://your-app.railway.app`)

7. **Update Chrome Extension**:
   - Open `js/config.js`
   - Change `BACKEND_URL` to your Railway URL

## API Endpoints

### `POST /replace-logos`

Replace logos in PDF file.

**Request:**
```
FormData:
  - pdf_file: PDF file
  - detections: JSON string [{page, x, y, width, height}]
  - replace_logo: Base64 encoded image
```

**Response:**
```
application/pdf - Modified PDF file
```

### `GET /health`

Check service health.

**Response:**
```json
{
  "status": "healthy",
  "service": "pdf-logo-replacer"
}
```

## Local Testing

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Visit: http://localhost:8000

## Environment Variables

- `PORT` - Server port (Railway sets this automatically)

## Tech Stack

- FastAPI - Web framework
- PyMuPDF - PDF manipulation
- Pillow - Image processing
- Uvicorn - ASGI server
