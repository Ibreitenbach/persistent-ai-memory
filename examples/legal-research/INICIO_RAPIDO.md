# Legal Hub - Guía de Inicio Rápido

**¡Pon tu Legal Hub en funcionamiento en 15 minutos!**

[🇺🇸 English Version](QUICKSTART.md)

---

## Lo Que Obtendrás

Un asistente completo de investigación legal con:
- ✅ Búsqueda de casos de tribunales federales (CourtListener)
- ✅ Casos de tribunales estatales (tu jurisdicción)
- ✅ Seguimiento de citas y análisis de precedentes
- ✅ Memoria persistente con aprendizaje de feromonas
- ✅ Búsqueda instantánea (0ms después de cargar la sesión)

---

## Requisitos Previos

Antes de comenzar, asegúrate de tener:

- [ ] **PostgreSQL 14+** instalado
  ```bash
  # Verificar versión
  psql --version
  ```

- [ ] **Python 3.9+** instalado
  ```bash
  # Verificar versión
  python3 --version
  ```

- [ ] **Git** instalado
  ```bash
  # Verificar versión
  git --version
  ```

- [ ] **Claude Code CLI** (opcional, para integración con RLM)
  ```bash
  # Verificar si está instalado
  which claude
  ```

---

## Paso 1: Clonar el Repositorio

```bash
# Clonar el repositorio
git clone https://github.com/Ibreitenbach/Legal-Claw-RLMemory
cd Legal-Claw-RLMemory/examples/legal-research

# Hacer ejecutable el script de instalación
chmod +x setup.sh
```

**Qué hace esto:** Descarga todo el código que necesitas.

---

## Paso 2: Ejecutar la Instalación Automatizada

```bash
# Ejecutar el script de instalación
./setup.sh

# Esto hará:
# 1. Crear base de datos PostgreSQL
# 2. Instalar paquetes Python requeridos
# 3. Configurar tablas de base de datos
# 4. Pedir tu clave API de CourtListener
```

**Lo que necesitarás:**
- Clave API de CourtListener (gratis - la obtendremos en el Paso 3)

**Tiempo:** ~5 minutos

---

## Paso 3: Obtener Clave API de CourtListener (GRATIS)

CourtListener proporciona acceso **gratuito** a opiniones de tribunales federales y estatales.

### 3.1. Crear Cuenta

1. Ir a: https://www.courtlistener.com/
2. Hacer clic en **"Sign Up"** (arriba a la derecha)
3. Crear cuenta gratuita con tu correo electrónico

### 3.2. Obtener Token API

1. Después de iniciar sesión, haz clic en tu nombre de usuario (arriba a la derecha)
2. Selecciona **"Profile"** (Perfil)
3. Haz clic en la pestaña **"API"**
4. Haz clic en **"Generate New API Token"** (Generar Nuevo Token API)
5. **Copia el token** (se ve como: `a1b2c3d4e5f6...`)

### 3.3. Guardar Token API

```bash
# Guardar tu token API
export COURTLISTENER_API_TOKEN="tu_token_aquí"

# Hacerlo permanente (agregar a tu .bashrc o .zshrc)
echo 'export COURTLISTENER_API_TOKEN="tu_token_aquí"' >> ~/.bashrc
```

**Importante:** ¡Reemplaza `tu_token_aquí` con tu token real!

---

## Paso 4: Probar Tu Instalación

```bash
# Probar conexión a base de datos
psql -d legal_hub -c "SELECT COUNT(*) FROM legal_cases;"
# Debe mostrar: 0 (sin casos todavía - ¡eso es correcto!)

# Probar API de CourtListener
python3 scripts/test_courtlistener.py
# Debe mostrar: ✅ Conexión exitosa
```

**Si ves errores:**
- Verifica que tu token API esté configurado correctamente
- Asegúrate de que PostgreSQL esté corriendo: `sudo systemctl status postgresql`

---

## Paso 5: Importar Tus Primeros Casos

Importemos algunos casos de la Corte Suprema sobre derechos constitucionales:

```bash
# Importar 25 casos de la Corte Suprema
python3 scripts/ingest_courtlistener.py \
    "constitutional rights" \
    --court scotus \
    --limit 25

# Esto hará:
# - Buscar en CourtListener
# - Descargar detalles de casos
# - Almacenar en tu base de datos
# - Generar incrustaciones para búsqueda

# Tarda unos 2-3 minutos
```

**Lo que verás:**
```
🔍 Buscando en CourtListener: constitutional rights
📊 Encontrados 25 opiniones
  ✓ Almacenado: Roe v. Wade (410 U.S. 113)
  ✓ Almacenado: Brown v. Board of Education (347 U.S. 483)
  ✓ Almacenado: Miranda v. Arizona (384 U.S. 436)
  ...
✅ Importación Completa
   Almacenados: 25 casos nuevos
```

---

## Paso 6: Buscar Tus Casos

Ahora puedes buscar en tu base de datos legal:

```bash
# Buscar casos sobre registro e incautación
python3 scripts/search_cases.py "Fourth Amendment search seizure"

# Buscar casos en una jurisdicción específica
python3 scripts/search_cases.py "due process" --jurisdiction federal

# Encontrar precedentes para un tema legal
python3 scripts/search_cases.py "unreasonable search" --min-pheromone 10
```

**Ejemplo de salida:**
```
Encontrados 8 casos:

1. Mapp v. Ohio
   Citación: 367 U.S. 643
   Tribunal: Corte Suprema de los Estados Unidos
   Decidido: 1961-06-19
   Feromona: 10.0
   Resumen: La regla de exclusión se aplica a los estados...
   URL: https://www.courtlistener.com/...

2. Terry v. Ohio
   Citación: 392 U.S. 1
   ...
```

---

## Paso 7: Agregar Tus Tribunales Estatales/Locales (Opcional)

### 7.1. Encontrar Tu Sistema de Tribunales Estatales

**Patrón de búsqueda en Google:**
```
"registros judiciales [Tu Estado] en línea"
"sistema judicial [Tu Estado] búsqueda de casos"
```

**Ejemplo para Oklahoma:**
1. Buscar: "Oklahoma court records online"
2. Encontrar: https://www.oscn.net/ (Red de Tribunales del Estado de Oklahoma)
3. ¡No se necesita clave API - registros públicos!

**Para estados hispanohablantes:**
- Puerto Rico: https://www.ramajudicial.pr/
- Nuevo México: https://www.nmcourts.gov/
- California (en español): https://www.courts.ca.gov/

### 7.2. Personalizar Raspador

```bash
# Copiar el raspador de plantilla
cp scripts/ingest_state_courts_template.py scripts/ingest_mi_estado.py

# Editar para tu estado
nano scripts/ingest_mi_estado.py

# Personalizar la función scrape_state_case()
# (Proporcionamos ejemplos, ver el código)
```

### 7.3. Importar Casos Estatales

```bash
# Importar un caso de tu tribunal estatal
python3 scripts/ingest_mi_estado.py CF-2020-123 --county MiCondado

# Importar múltiples casos
python3 scripts/ingest_mi_estado.py CF-2020-123 CF-2020-456 CF-2021-789
```

---

## Paso 8: Configurar Integración con Claude Code (Opcional)

Si usas Claude Code, integra Legal Hub para acceso instantáneo:

```bash
# Copiar configuración del plugin
cp claude_plugin/legal_hub_plugin.json ~/.claude/plugins/

# Editar configuración
nano ~/.claude/plugins/legal_hub_plugin.json

# Actualizar cadena de conexión a base de datos:
# "POSTGRES_CONNECTION_STRING": "postgresql://tuusuario@/legal_hub?host=/var/run/postgresql"
```

**Ahora cuando inicies Claude Code:**
- Tus casos legales se cargan automáticamente
- Búsqueda con latencia de 0ms
- Las puntuaciones de feromonas mejoran a medida que usas los casos

---

## Paso 9: Explorar Funciones Avanzadas

### 9.1. Seguimiento de Citas

```bash
# Encontrar todos los casos que citan un caso específico
python3 scripts/track_citations.py "410 U.S. 113"  # Roe v. Wade

# Ver en qué casos se basa una decisión
python3 scripts/track_citations.py "410 U.S. 113" --direction cited
```

### 9.2. Análisis de Precedentes

```bash
# Encontrar precedentes para un tema legal
python3 scripts/analyze_precedents.py "privacy rights abortion"

# Filtrar por jurisdicción y calidad
python3 scripts/analyze_precedents.py \
    "equal protection" \
    --jurisdiction federal \
    --min-pheromone 12
```

### 9.3. Importación en Lote

```bash
# Importar 100 casos sobre un tema
python3 scripts/ingest_courtlistener.py \
    "contract law" \
    --limit 100 \
    --jurisdiction ca  # California

# Importar de múltiples tribunales
python3 scripts/batch_import.py temas.txt
# (temas.txt contiene un tema por línea)
```

---

## Solución de Problemas

### Problema: "psql: command not found"

**Solución:** PostgreSQL no está instalado
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql
```

### Problema: "API 401: Unauthorized"

**Solución:** Token API no configurado o inválido
```bash
# Verificar si el token está configurado
echo $COURTLISTENER_API_TOKEN

# Si está vacío, configurarlo de nuevo
export COURTLISTENER_API_TOKEN="tu_token_aquí"

# Probar el token
curl -H "Authorization: Token $COURTLISTENER_API_TOKEN" \
  "https://www.courtlistener.com/api/rest/v3/search/?q=test&type=o"
```

### Problema: "Database 'legal_hub' does not exist"

**Solución:** Ejecutar el script de instalación de nuevo
```bash
./setup.sh
```

### Problema: "No cases found" (No se encontraron casos)

**Solución:** Verifica tu consulta de búsqueda
```bash
# Intenta una búsqueda más amplia
python3 scripts/search_cases.py "rights"

# Verifica cuántos casos hay en la base de datos
psql -d legal_hub -c "SELECT COUNT(*) FROM legal_cases;"
```

### Problema: El raspador del tribunal estatal no funciona

**Solución:** Los sitios web de tribunales estatales cambian frecuentemente
1. Visita el sitio web de tu tribunal estatal
2. Abre las herramientas de desarrollador del navegador (F12)
3. Inspecciona la estructura HTML
4. Actualiza el raspador para que coincida con la estructura actual
5. Ver `scripts/ingest_state_courts_template.py` para ejemplos

---

## Próximos Pasos

**Ahora que estás configurado:**

1. **Importar más casos** sobre temas relevantes para tu trabajo
2. **Configurar importaciones automáticas** (cron job) para casos nuevos
3. **Personalizar para tu área de práctica** (agregar tablas especializadas)
4. **Integrar con Claude Code** para investigación potenciada por IA
5. **Construir gráficos de citas** para entender redes de precedentes

---

## Recursos

### Documentación
- [Guía Completa de Legal Hub](../../.ai/BUILD_LEGAL_HUB.md) - Documentación técnica completa
- [Esquema de Base de Datos](schema_extensions.sql) - Tablas específicas legales
- [Referencia API](API.md) - Todas las funciones disponibles

### Fuentes de Datos
- **CourtListener**: https://www.courtlistener.com/
- **Free Law Project**: https://free.law/
- **Justia**: https://www.justia.com/
- **Google Scholar (Legal)**: https://scholar.google.com/ (seleccionar "Jurisprudencia")

### Directorios de Tribunales Estatales
- **Enlaces de Tribunales Estatales NCSC**: https://www.ncsc.org/information-and-resources/state-court-websites
- Encuentra tu sistema de tribunales estatales y busca registros en línea

### Recursos en Español
- **Rama Judicial de Puerto Rico**: https://www.ramajudicial.pr/
- **Tribunales de Nuevo México**: https://www.nmcourts.gov/
- **Tribunales de California (Español)**: https://www.courts.ca.gov/

---

## Soporte

**¿Necesitas ayuda?**

1. Consulta la sección de solución de problemas arriba
2. Ver documentación completa: [BUILD_LEGAL_HUB.md](../../.ai/BUILD_LEGAL_HUB.md)
3. Abrir un issue en GitHub: https://github.com/Ibreitenbach/Legal-Claw-RLMemory/issues

---

## Lista de Verificación de Éxito

Después de completar esta guía, deberías tener:

- [x] Base de datos PostgreSQL creada
- [x] Token API de CourtListener configurado
- [x] 25+ casos de Corte Suprema importados
- [x] Capacidad de buscar casos
- [x] Comprensión de cómo agregar tribunales estatales/locales
- [x] (Opcional) Integración con Claude Code funcionando

**¡Felicidades! ¡Tu Legal Hub está listo!** 🎉

---

**Siguiente:** [Versión en Inglés →](QUICKSTART.md)
