# Persistent AI Memory: RLM + Mempheromone

Dale a tu IA memoria persistente que se carga una vez por sesión y consulta instantáneamente.

[🇺🇸 English Version](README.md)

## ¿Qué Es Esto?

Un sistema completo para memoria conversacional de IA que:
- ✅ Carga historial filtrado **una vez** al inicio de la sesión
- ✅ Responde consultas con **latencia de recuperación de 0ms**
- ✅ Usa **aprendizaje de feromonas** para priorizar memorias útiles
- ✅ **Probado en batalla** con más de 4,994 conversaciones reales

## ¿Por Qué Precarga > RAG?

**Sistemas RAG Tradicionales** (Mem0, MemGPT):
- Recuperan en CADA consulta → latencia de 150-1,440ms
- Contexto parcial → conexiones perdidas
- Costo acumulativo → $0.01-0.10 por consulta

**Arquitectura de Precarga** (RLM + Mempheromone):
- Carga una vez por sesión → latencia de consulta de 0ms
- Contexto filtrado completo → comprensión total
- Costo marginal cero → consultas ilimitadas

**Para una conversación de 10 consultas:**
- RAG: 1.5-14 segundos de tiempo de recuperación
- Precarga: 0 segundos (¡ya está en el contexto!)

## Inicio Rápido

```bash
# 1. Clonar repositorio
git clone https://github.com/Ibreitenbach/Legal-Claw-RLMemory
cd Legal-Claw-RLMemory

# 2. Configurar base de datos
./scripts/setup.sh

# 3. Instalar plugin RLM
cp -r rlm-plugin ~/.claude/plugins/rlm-mempheromone

# 4. Empezar a usar - ¡la memoria se carga automáticamente!
```

## Resultados de Producción

**Uso Real** (4,994 conversaciones):
- Carga de sesión: 1.5 MB (27,036 líneas)
- Tamaño de contexto: ~50K tokens (cabe en ventana de 200K)
- Latencia de consulta: 0ms (¡ya está en contexto!)
- Fallos de recuperación: 0 (¡imposible - todo está ahí!)

**Benchmarks** (50 consultas):
- Hybrid RRF: P@5 = 0.144 (+80% de mejora)
- Latencia promedio: 21ms
- Costo: $0 (auto-alojado)

**Membox** (Memoria de Continuidad Temática):
- 755 cajas de memoria con enlaces de rastreo
- Procesamiento automático en segundo plano
- Aprendizaje de calidad basado en feromonas

## Componentes

### 1. Plugin RLM (Despertar de Sesión)
- Se activa al inicio de sesión
- Carga memorias de alta calidad (feromona >= 10)
- Exporta ~50K tokens al contexto
- Latencia de consulta cero después de cargar

### 2. Base de Datos Mempheromone
- PostgreSQL + pgvector
- Puntuaciones de feromonas (señales de calidad entrenadas por RL)
- Cajas de memoria de continuidad temática (membox)
- Gráficos de citas y enlaces de rastreo

### 3. Membox (Memoria de Continuidad Temática)
- Agrupa memorias relacionadas por tema
- Enlaces a través de límites temáticos mediante eventos
- Estructura de memoria navegable
- Procesamiento automático en segundo plano

### 4. Herramientas de Gestión de Base de Datos
- Monitoreo de salud y estadísticas
- Análisis y limpieza de calidad
- Regeneración de incrustaciones
- Optimización de rendimiento

## Documentación

- [Análisis Profundo de Arquitectura](docs/ARCHITECTURE.md) - Próximamente
- [Documento Técnico RLM](docs/RLM_WHITEPAPER.md) - Documentación técnica completa
- [Guía de Configuración Membox](docs/MEMBOX_SETUP.md) - Guía de integración
- [Gestión de Base de Datos](docs/DATABASE_MANAGEMENT_TOOLS.md) - Referencia de herramientas DB
- [Ejemplo Legal Hub](.ai/BUILD_LEGAL_HUB.md) - Variante específica del dominio
- [Guía de Inicio Rápido Legal Hub](examples/legal-research/INICIO_RAPIDO.md) - Configuración en español

## Construible por IA

**Característica Especial**: El directorio `.ai/` contiene documentos de traspaso legibles por IA.
Agentes de IA como Claude Code pueden construir el sistema completo a partir de instrucciones de forma autónoma.

## Comparación de Rendimiento

| Métrica | RLM+Mempheromone | Mem0 | MemGPT |
|---------|------------------|------|---------|
| Latencia de Consulta | **0ms** | 1,440ms | 150ms |
| Conv. 10 Consultas | **0ms** | 14,400ms | 1,500ms |
| Calidad de Contexto | Historial completo | Top-K | Top-K |
| Fallos de Recuperación | **0** | Posible | Posible |
| Costo por Consulta | **$0** | $0.10 | $0.05 |

## Cuándo Usar Esto

**Usar Precarga Cuando:**
- ✅ Conversaciones basadas en sesiones
- ✅ Necesitas comprensión de contexto completo
- ✅ Quieres latencia de recuperación cero
- ✅ El contexto cabe en la ventana (~50K tokens)
- ✅ Implementación auto-alojada

**Usar RAG Cuando:**
- ⚠️ Consultas únicas (sin sesión)
- ⚠️ Contexto demasiado grande para ventana (>100K tokens)
- ⚠️ Corpus dinámico (cambia durante la sesión)

## Requisitos

- PostgreSQL 14+ con extensión pgvector
- Python 3.9+
- Claude Code CLI (para plugin RLM)
- ~50K tokens de ventana de contexto disponible

## Licencia

Licencia MIT - ver archivo LICENSE

## Contribuciones

¡Contribuciones bienvenidas! Este es un sistema probado en producción con uso en el mundo real.

---

**Construido por Ike Breitenbach**
**Probado en producción con más de 4,994 conversaciones**
**Endurecido en batalla con uso multi-agente diario**
