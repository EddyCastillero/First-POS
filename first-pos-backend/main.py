from fastapi import FastAPI
from routers.inventory import router as inventory_router

app = FastAPI(
    title="First-POS API",
    version="1.0.0",
    description="API profesional de Punto de Venta e Inventario para Restaurante / Comedor.",
)

# Conectar el router de inventario
app.include_router(inventory_router)


@app.get("/")
def read_root():
    return {
        "status": "success",
        "message": "¡El Reverse Proxy funciona, bro! Saludos desde FastAPI detrás de Nginx.",
        "docs_url": "/docs",
    }