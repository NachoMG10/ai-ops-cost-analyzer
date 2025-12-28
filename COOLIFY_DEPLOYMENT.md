# Guía de Despliegue en Coolify - AI Ops Cost Analyzer

Esta guía te ayudará a desplegar el AI Ops Cost Analyzer en tu servidor Hetzner usando Coolify.

## 📋 Prerrequisitos

- Servidor Hetzner con Coolify instalado y configurado
- Acceso a la interfaz web de Coolify
- Repositorio GitHub con el código del proyecto

## 🚀 Pasos para el Despliegue

### 1. Crear Nueva Aplicación en Coolify

1. Accede a tu panel de Coolify
2. Haz clic en **"New Resource"** o **"Nueva Aplicación"**
3. Selecciona **"Docker Image"** o **"GitHub Repository"**
4. Si usas GitHub:
   - Conecta tu repositorio: `NachoMG10/ai-ops-cost-analyzer`
   - Selecciona la rama: `main`
   - Coolify detectará automáticamente el Dockerfile

### 2. Configuración de la Aplicación

#### Configuración Básica

- **Nombre de la aplicación**: `ai-ops-cost-analyzer` (o el que prefieras)
- **Puerto interno**: `8000` (ya configurado en el Dockerfile)
- **Tipo de despliegue**: `Dockerfile` (Coolify lo detectará automáticamente)

#### Variables de Entorno

Añade las siguientes variables de entorno en la configuración de Coolify:

| Variable | Valor | Requerido | Descripción |
|----------|-------|-----------|-------------|
| `PORT` | `8000` | No* | Puerto donde corre la aplicación (Coolify puede establecerlo automáticamente) |
| `OPENAI_API_KEY` | `tu_api_key_aqui` | No | Clave API de OpenAI (opcional, usa mock si no se proporciona) |

\* *Coolify puede establecer automáticamente la variable `PORT`, pero el Dockerfile tiene un valor por defecto de 8000.*

**Cómo añadir variables de entorno en Coolify:**
1. Ve a la configuración de tu aplicación
2. Busca la sección **"Environment Variables"** o **"Variables de Entorno"**
3. Añade cada variable con su valor correspondiente
4. Guarda los cambios

### 3. Configuración del Healthcheck

El Dockerfile ya incluye un healthcheck configurado:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

**Nota importante**: Coolify detectará automáticamente este healthcheck. No necesitas configurarlo manualmente en la UI de Coolify.

### 4. Configuración del Puerto

El Dockerfile expone el puerto 8000 y está configurado para usar la variable de entorno `PORT` si Coolify la proporciona:

```dockerfile
ENV PORT=8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

Coolify mapeará automáticamente este puerto. No necesitas configurar nada adicional.

### 5. Desplegar la Aplicación

1. Una vez configurada la aplicación, haz clic en **"Deploy"** o **"Desplegar"**
2. Coolify comenzará a:
   - Clonar el repositorio
   - Construir la imagen Docker
   - Iniciar el contenedor
   - Verificar el healthcheck

### 6. Verificar el Despliegue

Una vez completado el despliegue:

1. **Verifica los logs**: En la sección de logs de Coolify, deberías ver:
   ```
   INFO:     Started server process
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://0.0.0.0:8000
   ```

2. **Prueba el endpoint de health**:
   ```bash
   curl https://tu-dominio.com/health
   ```
   Deberías recibir:
   ```json
   {"status": "healthy", "records_count": 0}
   ```

3. **Accede a la documentación interactiva**:
   - Swagger UI: `https://tu-dominio.com/docs`
   - ReDoc: `https://tu-dominio.com/redoc`

## 🔧 Troubleshooting

### Problema: Healthcheck falla

**Síntomas:**
- El contenedor se inicia pero el healthcheck marca "unhealthy"
- Logs muestran errores de conexión

**Soluciones:**
1. Verifica que el puerto 8000 esté correctamente expuesto
2. Revisa los logs del contenedor para ver si hay errores de inicio
3. Asegúrate de que `curl` esté instalado en la imagen (ya está en el Dockerfile)
4. Aumenta el `start-period` en el healthcheck si la app tarda en iniciar

### Problema: Error de recursión en Pydantic

**Síntomas:**
- Logs muestran: `RecursionError: maximum recursion depth exceeded`
- La aplicación no inicia

**Solución:**
Este error ya está corregido en el código actualizado. Asegúrate de tener la última versión del código que usa Pydantic v2 correctamente.

### Problema: La aplicación no responde

**Síntomas:**
- El contenedor está corriendo pero no responde a las peticiones

**Soluciones:**
1. Verifica que el puerto esté correctamente mapeado en Coolify
2. Revisa los logs para ver si hay errores de inicio
3. Asegúrate de que la variable `PORT` esté configurada correctamente
4. Prueba acceder directamente al contenedor:
   ```bash
   docker exec -it <container_id> curl http://localhost:8000/health
   ```

### Problema: Error al construir la imagen

**Síntomas:**
- El build de Docker falla
- Errores relacionados con dependencias

**Soluciones:**
1. Verifica que todas las dependencias en `requirements.txt` sean correctas
2. Revisa los logs del build para ver el error específico
3. Asegúrate de que el Dockerfile esté en la raíz del repositorio

## 📝 Configuración Recomendada

### Recursos del Contenedor

Para producción, se recomienda:

- **CPU**: Mínimo 0.5 cores (1 core recomendado)
- **RAM**: Mínimo 512MB (1GB recomendado)
- **Storage**: 1GB es suficiente

### Dominio y SSL

1. En Coolify, configura tu dominio personalizado
2. Coolify configurará automáticamente SSL con Let's Encrypt
3. Asegúrate de que el dominio apunte correctamente a tu servidor

### Backup

Aunque la aplicación no tiene base de datos persistente (usa almacenamiento en memoria), considera:

- Hacer backup del código fuente (ya está en GitHub)
- Documentar las variables de entorno configuradas
- Guardar cualquier configuración personalizada

## 🧪 Probar la Aplicación

Una vez desplegada, puedes probar los siguientes endpoints:

### 1. Health Check
```bash
curl https://tu-dominio.com/health
```

### 2. Análisis con datos de ejemplo
```bash
curl -X POST https://tu-dominio.com/analyze
```

### 3. Documentación interactiva
Abre en tu navegador:
```
https://tu-dominio.com/docs
```

### 4. Subir CSV personalizado
```bash
curl -X POST https://tu-dominio.com/api/v1/upload-csv \
  -F "file=@tu_archivo.csv"
```

## 🔄 Actualizaciones

Para actualizar la aplicación:

1. Haz push de los cambios a la rama `main` en GitHub
2. Coolify detectará automáticamente los cambios (si tienes webhooks configurados)
3. O manualmente, ve a la aplicación en Coolify y haz clic en **"Redeploy"**

## 📞 Soporte

Si encuentras problemas:

1. Revisa los logs en Coolify
2. Verifica que todas las variables de entorno estén configuradas
3. Asegúrate de tener la última versión del código
4. Revisa esta guía de troubleshooting

## ✅ Checklist de Despliegue

- [ ] Repositorio conectado en Coolify
- [ ] Dockerfile detectado correctamente
- [ ] Puerto 8000 configurado
- [ ] Variables de entorno añadidas (si es necesario)
- [ ] Healthcheck funcionando
- [ ] Aplicación desplegada exitosamente
- [ ] Endpoint `/health` responde correctamente
- [ ] Documentación accesible en `/docs`
- [ ] Dominio y SSL configurados (opcional)

---

**Última actualización**: Diciembre 2024
**Versión del proyecto**: 1.0.0
