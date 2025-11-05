"""
PDF Logo Replacement Backend - Cloud Run Deployment
Uses PyMuPDF for pixel-perfect logo replacement
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import fitz  # PyMuPDF
import io
import base64
from PIL import Image
import json
from typing import List

app = FastAPI(title="PDF Logo Replacer API")

# Enable CORS for Chrome Extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (Chrome Extension)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": "PDF Logo Replacer API",
        "status": "running",
        "version": "1.0.3",
        "endpoints": {
            "/replace-logos": "POST - Replace logos in PDF",
            "/health": "GET - Health check"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "pdf-logo-replacer"}

@app.post("/replace-logos")
async def replace_logos(
    pdf_file: UploadFile = File(...),
    detections: str = Form(...),
    replace_logo: str = Form(...)
):
    """
    Replace logos in PDF using PyMuPDF insert_image()
    
    Args:
        pdf_file: PDF file to process
        detections: JSON array of logo locations [{page, x, y, width, height}]
                   x, y from bottom-left corner
        replace_logo: Base64 encoded replacement logo image
    
    Returns:
        Modified PDF file
    """
    try:
        print(f"📄 Received PDF: {pdf_file.filename}")
        
        # Parse detections
        detections_list = json.loads(detections)
        print(f"🔍 Processing {len(detections_list)} logo(s)")
        
        # Decode replacement logo
        if replace_logo.startswith('data:image'):
            replace_logo = replace_logo.split(',')[1]
        replace_logo_bytes = base64.b64decode(replace_logo)
        
        # Load replacement logo with PIL to get dimensions
        replace_img = Image.open(io.BytesIO(replace_logo_bytes))
        replace_width, replace_height = replace_img.size
        print(f"🎨 Replacement logo original: {replace_width}x{replace_height}")
        
        # Read PDF
        pdf_bytes = await pdf_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        print(f"📖 PDF opened: {doc.page_count} pages")
        
        # Process each detection
        for idx, det in enumerate(detections_list):
            page_num = det['page'] - 1  # 0-based index
            x = det['x']
            y = det['y']
            width = det.get('width', replace_width)
            height = det.get('height', replace_height)
            
            print(f"\n[Logo {idx+1}/{len(detections_list)}]")
            print(f"  Page: {page_num + 1}")
            print(f"  📥 Received: x={x}, y={y}, w={width}, h={height}")
            
            page = doc[page_num]
            page_width = page.rect.width
            page_height = page.rect.height
            
            print(f"  📐 PDF page: {page_width:.1f}x{page_height:.1f}")
            
            # FIX: Use exact dimensions from Extension - NO aspect ratio adjustment!
            # Extension already calculated correct size
            print(f"  ✅ Using exact dimensions from Extension")
            
            # Create rectangle (PyMuPDF uses bottom-left origin)
            x0 = x
            y0 = y
            x1 = x + width
            y1 = y + height
            
            print(f"  📍 Rectangle: ({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f})")
            
            rect = fitz.Rect(x0, y0, x1, y1)
            
            # Insert logo with keep_proportion=False to use EXACT dimensions
            try:
                page.insert_image(
                    rect,
                    stream=replace_logo_bytes,
                    keep_proportion=False,  # Use EXACT rect dimensions!
                    overlay=True
                )
                print(f"  ✅ Logo inserted with exact dimensions!")
                    
            except Exception as img_error:
                print(f"  ❌ Error inserting image: {img_error}")
                raise
        
        # Save modified PDF
        output_bytes = doc.tobytes(
            garbage=4,  # Maximum compression
            deflate=True,
            clean=True
        )
        doc.close()
        
        print(f"\n✅ PDF processing complete!")
        print(f"📦 Output size: {len(output_bytes)} bytes")
        
        # Return modified PDF
        return Response(
            content=output_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=modified_{pdf_file.filename}"
            }
        )
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid detections JSON: {str(e)}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
