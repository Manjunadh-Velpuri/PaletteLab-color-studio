"""
Root entry point for PaletteLab Web.
Provides compatibility with standard Python ASGI servers and Vercel dev command (uvicorn main:app).
"""
import sys
from api.index import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
