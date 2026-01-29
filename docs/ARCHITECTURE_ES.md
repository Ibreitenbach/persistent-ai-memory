# Arquitectura Profunda: Legal-Claw-RLMemory

**Arquitectura técnica completa del sistema RLM + Mempheromone**

[🇺🇸 Full English Version](ARCHITECTURE.md) *(Versión completa en inglés con 1,100+ líneas de documentación técnica)*

---

## Resumen Ejecutivo

**Legal-Claw-RLMemory** demuestra un cambio fundamental en la arquitectura de memoria de IA:

**De:** Recuperar-en-cada-consulta (RAG)
**A:** Cargar-una-vez-por-sesión (Precarga)

### Innovaciones Clave

1. **RLM (Reinforcement Learning Memory)** - El despertar de sesión elimina la latencia de recuperación
2. **Aprendizaje de Feromonas** - Señales de calidad entrenadas por RL
3. **Cajas de Memoria** - Organización de continuidad temática
4. **Observador Silencioso** - Refuerzo automático
5. **Probado en Producción** - 4,994 conversaciones reales

**Resultado:** Latencia de recuperación de 0ms, comprensión de contexto completo, costo marginal cero.

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                     Sesión de Claude Code                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Hook de Inicio de Sesión (RLM)                        │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │ 1. Consultar base de datos mempheromone          │  │ │
│  │  │ 2. Filtrar: pheromone_score >= 10                │  │ │
│  │  │ 3. Exportar ~50K tokens al contexto              │  │ │
│  │  │ 4. Inyectar en prompt del sistema                │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Consulta del Usuario → Respuesta (0ms latencia)      │ │
│  │  ↓                                                     │ │
│  │  ¡La memoria ya está en el contexto!                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Observador Silencioso                                 │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │ Código de salida 0 → +0.5 feromona              │  │ │
│  │  │ Código de salida 1+ → -0.3 feromona             │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                  PostgreSQL + pgvector                       │
│  ┌────────────────┬────────────────┬───────────────────┐    │
│  │ debugging_facts│ memory_boxes   │ embeddings        │    │
│  │ (112K filas)   │ (755 cajas)    │ (búsqueda sem.)   │    │
│  └────────────────┴────────────────┴───────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Componentes Principales

### 1. RLM (Reinforcement Learning Memory)

**Qué es:** Sistema de despertar de sesión que carga el historial de conversación filtrado una vez al inicio de la sesión.

**Proceso de Despertar:**
1. Usuario inicia sesión de Claude Code
2. Hook SessionStart se activa
3. Script exporta memorias (feromona >= 10)
4. ~50K tokens inyectados en contexto
5. Sesión lista con memoria completa cargada
6. Consultas respondidas con latencia de 0ms

**Ventaja clave:** Elimina la recuperación por consulta.

### 2. Aprendizaje de Feromonas

**Escala de Puntuación:**
```
20.0  ━━━━━━━━━━━━━━━━━━━  Experto+    (Lo mejor de lo mejor)
15.0  ━━━━━━━━━━━━━━━━━━━  Experto     (Probado en batalla)
12.0  ━━━━━━━━━━━━━━━━━━━  Sólido+     (Consistentemente bueno)
10.0  ━━━━━━━━━━━━━━━━━━━  Sólido      (Probado, confiable)
 5.0  ━━━━━━━━━━━━━━━━━━━  No probado  (Nuevo, necesita validación)
 0.0  ━━━━━━━━━━━━━━━━━━━  Fallido     (Incorrecto/dañino)
```

**Mecanismo de Refuerzo:**
- **Éxito** (código de salida 0): +0.5 feromona
- **Fallo** (código de salida 1+): -0.3 feromona
- **Decaimiento** (no usado en 90+ días): -0.1 feromona

**Observador Silencioso:** Refuerzo automático basado en resultados de comandos shell.

### 3. Cajas de Memoria (Memoria de Continuidad Temática)

**Concepto:** Agrupa memorias relacionadas por tema, preservando la continuidad entre conversaciones.

**Componentes:**
- **Topic Loom (Telar de Temas):** Agrupa memorias en cajas
- **Trace Weaver (Tejedor de Rastreo):** Enlaces entre temas

**Procesamiento en Segundo Plano:**
```bash
# Cron job ejecuta cada hora
0 * * * * python3 membox_worker.py --since 1h
```

**Estadísticas de Producción:**
- 755 cajas de memoria creadas
- 84 enlaces de rastreo entre temas
- Promedio 1.4 memorias por caja

### 4. Arquitectura de Base de Datos

**Tablas Principales:**
```
Memoria Central:
├── debugging_facts        (112K filas)  Pares problema-solución
├── claude_memories        (45K filas)   Memorias generales
├── session_narratives     (1.2K filas)  Resúmenes de sesión
└── crystallization_events (94 filas)    Momentos WYKYK

Búsqueda Semántica:
└── embeddings             (68K filas)   Incrustaciones vectoriales

Memoria de Continuidad Temática:
├── memory_boxes           (755 filas)   Grupos de temas
├── memory_box_items       (1.1K filas)  Pertenencia a cajas
└── trace_links            (84 filas)    Conexiones entre temas
```

**Optimizaciones:**
- Índices en puntuaciones de feromonas
- Índice vectorial HNSW para búsqueda rápida
- Índices de timestamp para consultas recientes
- Índices GIN para búsquedas JSONB

---

## Análisis de Rendimiento

### Comparación de Latencia

**Conversación de 10 consultas:**

| Sistema | Tiempo de Recuperación | Sobrecarga Total |
|---------|------------------------|------------------|
| RLM+Mempheromone | 0ms (precargado) | 0ms |
| MemGPT | 150ms × 10 | 1,500ms (1.5s) |
| Mem0 | 1,440ms × 10 | 14,400ms (14.4s) |

**RLM gana por 1.5-14 segundos en cada 10 consultas.**

### Uso de Memoria

**Carga de sesión:**
- Tamaño de exportación: ~1.5 MB (27,036 líneas)
- Conteo de tokens: ~50K tokens
- Uso de ventana de contexto: 25% (de 200K)

### Resultados de Benchmarks (Datos Reales)

**50 consultas sobre base de datos mempheromone:**
- **Hybrid RRF**: P@5 = 0.144 (+80% mejora sobre línea base)
- **Latencia promedio**: 21ms
- **Costo**: $0 (auto-alojado)

---

## Decisiones de Diseño

### ¿Por qué Precarga vs RAG?

**Decisión:** Usar arquitectura de precarga para conversaciones de IA basadas en sesiones.

**Justificación:**
1. Las sesiones tienen localidad temporal
2. Ventanas de contexto ahora son lo suficientemente grandes (200K+ tokens)
3. Filtrado de feromonas asegura solo memorias de alta calidad
4. Costo marginal cero supera costo acumulativo de recuperación
5. Contexto completo permite mejor coherencia

### ¿Por qué Feromonas vs Puntuaciones Estáticas?

**Decisión:** Usar puntuaciones de feromonas entrenadas por RL que evolucionan con el uso.

**Justificación:**
1. Puntuaciones estáticas no se adaptan a utilidad cambiante
2. Incrustaciones LLM solas pierden utilidad pragmática
3. Retroalimentación del usuario (códigos de salida) es verdad fundamental
4. Decaimiento archiva naturalmente memorias obsoletas

### ¿Por qué PostgreSQL vs Base de Datos Vectorial?

**Decisión:** PostgreSQL + extensión pgvector.

**Justificación:**
1. Transacciones ACID (almacenamiento de memoria es crítico)
2. Capacidades de consulta ricas (JOINs, agregaciones, CTEs)
3. Ecosistema maduro (respaldo, replicación, monitoreo)
4. pgvector proporciona indexación HNSW
5. No necesita sistemas separados

---

## Comparación con Otros Sistemas

### vs Mem0

**Ventajas de RLM+Mempheromone:**
- **Más rápido**: 0ms vs 1,440ms recuperación
- **Más barato**: $0 vs $0.10 por consulta
- **Mejor calidad**: Aprendizaje de feromonas vs similitud de incrustación estática
- **Contexto completo**: Todas las memorias vs top-K
- **Auto-alojado**: Sin dependencias externas

### vs MemGPT

**Ventajas de RLM+Mempheromone:**
- **Más simple**: No se necesita resumir recursivo
- **Más rápido**: 0ms vs 150ms recuperación
- **PostgreSQL**: Base de datos de grado de producción vs SQLite
- **Aprendizaje de feromonas**: Se adapta vs estático
- **Datos de producción reales**: 4,994 conversaciones vs prototipo de investigación

---

## Patrones de Implementación

### Agregar un Nuevo Tipo de Memoria

```sql
-- 1. Crear tabla
CREATE TABLE mi_nueva_memoria (
    id UUID PRIMARY KEY,
    contenido TEXT NOT NULL,
    pheromone_score FLOAT DEFAULT 10.0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. Agregar índice
CREATE INDEX idx_mi_memoria_pheromone
    ON mi_nueva_memoria(pheromone_score DESC);

-- 3. Actualizar exportación RLM (en mempheromone_export.py)
```

### Refuerzo Personalizado de Feromonas

```python
def reforzar_desde_calificacion(memory_id, calificacion):
    """Reforzar memoria basada en calificación explícita del usuario (1-5 estrellas)."""
    mapa_delta = {
        5: +2.0,  # Excelente
        4: +1.0,  # Bueno
        3: +0.0,  # Neutral
        2: -0.5,  # Pobre
        1: -1.5   # Terrible
    }
    delta = mapa_delta.get(calificacion, 0.0)
    # Actualizar pheromone_score en base de datos
```

---

## Extensiones Futuras

1. **Memoria Jerárquica**: Hechos Crudos → Cristalizaciones → Principios de Sabiduría
2. **Aprendizaje Entre Sesiones**: Rastrear patrones a través de múltiples sesiones
3. **Memoria Federada**: Compartir patrones anonimizados entre usuarios
4. **Decaimiento Temporal**: Archivar automáticamente memorias antiguas
5. **Memoria Multi-Modal**: Soportar imágenes, código, diagramas

---

## Conclusión

**Legal-Claw-RLMemory** representa un cambio fundamental en la arquitectura de memoria de IA, demostrando que la precarga supera a RAG para conversaciones basadas en sesiones.

**Perfecto para:**
- Conversaciones de IA basadas en sesiones
- Investigación legal (variante Legal Hub)
- Desarrollo de software
- Sistemas multi-agente
- Cualquier dominio con conocimiento en evolución

---

**Para documentación técnica completa (1,100+ líneas):**
👉 [**Ver versión completa en inglés**](ARCHITECTURE.md)

---

**Construido por Ike Breitenbach**
**Probado en producción con 4,994+ conversaciones**
**GitHub:** https://github.com/Ibreitenbach/Legal-Claw-RLMemory

**Licencia:** MIT
