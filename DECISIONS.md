# 📝 Bitácora de Decisiones — First-POS

> Registro de decisiones estratégicas tomadas en conversación con el asistente, para dar contexto rápido al retomar el proyecto en otra sesión. El detalle técnico vigente vive en `CONTEXT.md`; aquí queda el **porqué** detrás de los cambios recientes.

---

## 2026-10-07 — Dominio Personalizado, SSL Automático y Pipeline CI/CD

**Decisiones tomadas:**
1. **Dominio Propio y Subdominios:** Dominio `leonelproyectos.me` registrado vía Namecheap (GitHub Student Developer Pack). DNS configurado con registro tipo A (`pos-qa`) apuntando a IP fija de GCP (`35.222.226.192`).
2. **Cifrado SSL / TLS con Let's Encrypt:** Certificados emitidos de forma automatizada y gratuita con Certbot en modo standalone, montados en Nginx en modo solo lectura (`/etc/letsencrypt`). Redirección permanente (301) de HTTP (80) hacia HTTPS (443).
3. **Pipeline CI/CD con GitHub Actions:** Creado workflow `.github/workflows/deploy-qa.yml` activado en pushes a la rama `qa`. Despliegue seguro mediante SSH (llave ed25519 en GitHub Secrets) que ejecuta pull, build de contenedores y migraciones Alembic de forma autónoma.
4. **Diseño Visual de Alto Contraste:** Cambio de paleta de colores de acento de azul a negro/neutral para mayor contraste y formalidad, con favicon personalizado integrado.

---

## 2026-10-06 — Despliegue de QA en GCP y Finalización del Backend/Frontend

**Decisiones tomadas:**
1. **Regla de Merma por Proceso (Operativa):** Se implementó la regla de Peso Bruto vs Peso Neto ($Merma = Bruto - Neto$), calculando porcentaje de merma automáticamente y descontando del inventario atómicamente.
2. **Turnos de Caja con Fondos Fijos:** Restricción estricta de fondo inicial a $1,000, $2,000 o $3,000 MXN para evitar descuadres de cajeros.
3. **Platillos vinculados a Recetas:** Todo `MenuItem` apunta a una `Recipe`, unificando el descuento recursivo de insumos crudos y subrecetas (mise en place).
4. **Cobro Atómico (ACID):** Validación y descuento con bloqueo pesimista (`SELECT ... FOR UPDATE`) en PostgreSQL para consistencia total en caja.
5. **Frontend Ligero:** SPA en HTML5 + Tailwind CSS servida directamente por Nginx en el puerto 80 sin runtime de Node.js, ahorrando memoria RAM para la VM `e2-micro`.
6. **Estrategia de Ambientes y Ramas:** 
   - `dev`: Desarrollo local.
   - `qa`: Ambiente de pruebas en la nube (desplegado en Compute Engine VM `e2-micro` en `us-central1`, IP `35.222.226.192`).
   - `main`: Producción aislada.
7. **Memoria SWAP en GCP:** 2 GB de SWAP configurados en el disco estándar de 30 GB para evitar que Docker agote el 1 GB de RAM física.

---

## 2026-10-04 — Cambio de nube: GCP (se descarta AWS)

**Contexto previo:** El 2026-09-30 se eligió AWS (ver entrada siguiente).

**Decisión:** Se cambia a **Google Cloud Platform (GCP)**.

**Por qué:**
- El usuario quiere aprender GCP a fondo y usar este proyecto como su caso práctico.
- **Free tier para un demo de portafolio:** la e2-micro de GCP es *Always Free* (no expira), así que el proyecto puede quedarse en línea indefinidamente para reclutadores. Las cuentas nuevas de AWS (desde julio 2025) ya no tienen los 12 meses de EC2/RDS gratis: reciben créditos (~$200) por un máximo de 6 meses.
- Los fundamentos (cómputo, redes, IAM, IaC, CI/CD, observabilidad) son transferibles; el curso de AWS Cloud Practitioner no se pierde, sirve como base conceptual y para comparar servicios.

**Implicaciones técnicas:**
- **Cloud SQL no tiene free tier** → etapa 1 con Postgres en contenedor dentro de una **e2-micro** (Always Free, solo `us-central1`/`us-west1`/`us-east1`). Cloud SQL + Cloud Run se prueban después con los $300 de crédito de prueba.
- El `docker-compose.yml` actual (nginx + backend + postgres con redes pública/privada) se puede llevar casi tal cual a la VM.
- Mapeo completo de servicios en `CONTEXT.md` sección C.
- **Regla:** antes de cambiar de nube otra vez, terminar al menos la etapa 1 del despliegue. El objetivo es tener algo corriendo, no elegir la nube perfecta.

---

## 2026-09-30 — Elección de nube: AWS (se descarta Azure)

**Contexto previo:** `CONTEXT.md` apuntaba a Azure, pensando en aprovechar los créditos de GitHub Student Pack.

**Decisión:** Se cambia a **AWS**.

**Por qué:**
- El usuario está cursando *AWS Cloud Practitioner Essentials* — aprovechar ese momentum en vez de dividir el aprendizaje entre dos nubes.
- AWS concentra la mayor demanda laboral en Cloud/DevOps; los conceptos aprendidos ahí se traducen directo a GCP/Azure después, pero no al revés con la misma facilidad.
- Se evaluó la idea de irse "por lo nicho" (GCP/Azure) para tener menos competencia a futuro. Conclusión: el nicho rinde **después** de tener una base sólida en el proveedor dominante, no como reemplazo de esa base. Plan a futuro: una vez sólido en AWS, portar/replicar parte del proyecto a GCP o Azure como segundo showcase de "no soy AWS-only".
- AWS sí tiene free tier suficiente para un proyecto chico (ver `CONTEXT.md` sección C para el mapeo de servicios).

---

## 2026-09-30 — Alcance recortado: solo Caja (POS) + Inventario

**Contexto previo:** El usuario tiene un proyecto anterior más grande y ambicioso, **Brote** (`/home/leonel-420/Desktop/Proyectos/Brote`), con backend FastAPI + dos frontends Next.js (admin y cliente), que quedó a medias por exceso de alcance (paquetes/beneficios, constructor de platillos, licencias, QR, integración de terminal Banorte, IA, bitácoras de merma/temperatura, etc.).

**Decisión:** First-POS se inspira en Brote pero **no lo replica**. Se recorta a dos módulos: **Caja Registradora (POS)** e **Inventario**.

**Por qué:**
- Mantener el software chico pero funcional y pulido, evitando el mismo patrón de sobre-alcance que dejó a Brote inconcluso.
- De los modelos de Brote (`app/models/`), se rescatan como referencia: `menu_item.py`, `order.py`, `stock_movement.py`, `recipe.py`, `cash_cut.py`, `supplier.py`.
- Se descartan explícitamente: `benefit_package`, `configured_package`, `configured_favorito`, `garden_bowl`, `plate_component`, `licence`, `qr_transaction`, `temperature.py`, `waste.py`, `invitation.py`, y servicios como `banorte_service.py`, `nvidia_ai.py`, `package_builder_service.py`, `plate_builder_service.py`.

---

## 2026-09-30 — Pausa en Docker/Kubernetes profundo

**Decisión:** El usuario pausa seguir profundizando en Docker/Kubernetes por ahora.

**Por qué:**
- Prioriza avanzar el desarrollo funcional del POS (backend + frontend) primero.
- Una vez el POS esté funcional, el foco vuelve a la parte de nube: despliegue y monitoreo en AWS (que es el objetivo central de aprendizaje del proyecto, por encima del desarrollo del software en sí).

---

## Pendiente / próxima conversación

- Definir el modelo de datos recortado (tablas exactas de Caja + Inventario) partiendo de `first-pos-backend/models/product.py` y los modelos rescatados de Brote.
- Decidir si se expande el backend actual o se reinicia con los modelos de Brote como base.
- Más adelante: aprovisionar infraestructura GCP (Compute Engine e2-micro, Artifact Registry, Cloud Storage, Secret Manager, Cloud Monitoring — ver `CONTEXT.md` sección C) y escribir IaC con Terraform.
