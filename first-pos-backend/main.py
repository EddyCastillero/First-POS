from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {
        "status": "success",
        "message": "¡El Reverse Proxy funciona, bro! Saludos desde FastAPI detrás de Nginx."
    }