"""
PDF Logo Replacement Backend - Railway Deployment
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
        "version": "1.0.0",
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
    Replace logos in PDF using PyMuPDF img_replace()
    
    Args:
        pdf_file: PDF file to process
        detections: JSON array of logo locations [{page, x, y, width, height}]
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
        print(f"🎨 Replacement logo: {replace_width}x{replace_height}")
        
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
            print(f"  Position: x={x}, y={y}")
            print(f"  Size: {width}x{height}")
            
            page = doc[page_num]
            page_height = page.rect.height
            
            # Calculate aspect ratio
            original_aspect = replace_width / replace_height
            target_aspect = width / height if height > 0 else original_aspect
            
            # Preserve aspect ratio
            if abs(original_aspect - target_aspect) > 0.1:
                # Adjust height to match aspect ratio
                height = width / original_aspect
                print(f"  ✅ Adjusted height to preserve aspect ratio: {height}")
            
            # PDF coordinates: (0,0) is bottom-left
            # rect = (x0, y0, x1, y1) where (x0,y0) is bottom-left
            x0 = x
            y0 = y  # Already in PDF coordinates (from bottom)
            x1 = x0 + width
            y1 = y0 + height
            
            rect = fitz.Rect(x0, y0, x1, y1)
            
            print(f"  📍 Rectangle: ({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f})")
            
            # Replace logo using PyMuPDF's img_replace()
            # This is THE CORRECT WAY according to the documentation!
            try:
                # Find all images on page
                images = page.get_images(full=True)
                print(f"  🖼️ Found {len(images)} images on page")
                
                # Try to find and replace the logo image
                replaced = False
                for img_idx, img in enumerate(images):
                    xref = img[0]
                    img_rect = page.get_image_bbox(img)
                    
                    # Check if this image intersects with our target rectangle
                    if img_rect.intersects(rect):
                        print(f"  🎯 Found target image at xref={xref}")
                        
                        # Replace the image
                        page.replace_image(
                            xref=xref,
                            stream=replace_logo_bytes
                        )
                        
                        print(f"  ✅ Logo replaced successfully!")
                        replaced = True
                        break
                
                if not replaced:
                    # If no existing image found, insert new one
                    print(f"  ℹ️ No existing image found, inserting new logo...")
                    page.insert_image(
                        rect,
                        stream=replace_logo_bytes,
                        keep_proportion=True
                    )
                    print(f"  ✅ New logo inserted!")
                    
            except Exception as img_error:
                print(f"  ⚠️ Error replacing image: {img_error}")
                # Fallback: just insert the new image
                try:
                    page.insert_image(
                        rect,
                        stream=replace_logo_bytes,
                        keep_proportion=True
                    )
                    print(f"  ✅ Logo inserted (fallback method)")
                except Exception as fallback_error:
                    print(f"  ❌ Fallback failed: {fallback_error}")
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
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
