# Sistema de interfaz de RitaCart

RitaCart es una herramienta local para entender la compra del hogar. La interfaz debe ayudar a encontrar una cifra, comprobar su origen y actuar con confianza. Prioriza datos legibles, lenguaje cotidiano y una acción principal por contexto. Conserva el verde de la marca y utiliza superficies neutras para dar protagonismo a la información.

## Principios

- **Estado visible:** indicar carga, resultado y error; explicar cuándo no hay datos suficientes y ofrecer recuperación cuando sea posible.
- **Control y prevención:** mantener el PDF original accesible y pedir confirmación antes de unir productos o reprocesar un ticket. No usar el color como única señal de estado o variación.
- **Reconocimiento:** mostrar etiquetas, unidades, periodo y contexto junto a cada dato. Los gráficos de líneas ofrecen también sus valores en texto.
- **Jerarquía y consistencia:** títulos breves, métricas destacadas y controles cercanos a los datos que modifican. Evitar duplicar acciones y detalles que no ayuden a tomar decisiones.
- **Accesibilidad desde el diseño:** utilizar controles HTML nativos, etiquetas asociadas, orden lógico, foco visible y navegación con teclado. No asumir que toda persona utiliza ratón, distingue colores o ve la pantalla al tamaño predeterminado.

Referencias: [heurísticas de Nielsen Norman Group](https://www.nngroup.com/articles/ten-usability-heuristics/), [IBM Carbon: accesibilidad](https://carbondesignsystem.com/guidelines/accessibility/overview/) y [WCAG 2.2](https://www.w3.org/TR/WCAG22/). Estas guías orientan el diseño; una revisión automática aislada no certifica conformidad WCAG.

## Fundamentos visuales

Los valores compartidos están en `frontend/src/styles.css`. Usar las variables existentes antes de añadir valores nuevos.

| Token | Valor | Uso |
| --- | --- | --- |
| `--ink` | `#183329` | Texto principal |
| `--muted` | `#4c6257` | Texto secundario |
| `--canvas` | `#f4f7f3` | Fondo de la aplicación |
| `--surface` | `#ffffff` | Tarjetas y controles |
| `--line` | `#d9e3da` | Separación visual |
| `--green` | `#216443` | Acción principal y selección |
| `--green-dark` | `#123d2d` | Énfasis e interacción |
| `--green-soft` | `#e8f2e9` | Fondo de selección |
| `--focus` | `#1358b5` | Contorno visible del foco |

La tipografía utiliza la pila de sistema, sin descarga externa. El texto base es de 16 px; los títulos se escalan de forma fluida. La separación habitual sigue incrementos de aproximadamente 4, 8, 12, 16, 24 y 32 px. Tarjetas y controles comparten bordes suaves, sin sombras fuertes. No codificar significado exclusivamente mediante tonalidades verdes.

## Componentes y contenido

- **Navegación:** Inicio, Compras, Productos, Análisis y Ajustes. Análisis contiene Gastos, Categorías, Precios y Hábitos; el periodo solo se ofrece donde el endpoint lo aplica. En móvil, todas las secciones principales deben estar visibles.
- **Botones y campos:** usar verbos claros, etiquetas visibles y foco perceptible. Los objetivos principales miden al menos 44 px de alto; comprobar también los controles nativos y excepciones en contexto. Los botones deshabilitados deben explicar el requisito que falta cuando no sea evidente.
- **Tarjetas y métricas:** una etiqueta y un valor principal; añadir contexto, unidad y periodo cuando cambien la interpretación. No convertir ausencia de observaciones en una conclusión.
- **Listas y detalles:** permitir reconocer el elemento seleccionado. Los filtros no deben mostrar como seleccionado un detalle que queda fuera de los resultados. En pantallas estrechas las columnas pasan a una sola y las listas largas tienen desplazamiento propio.
- **Gráficos:** mostrar título, periodo, unidades y valores; incluir alternativa textual para series. Las flechas y las cifras acompañan al color en las variaciones.
- **Estados:** comunicar importación y errores mediante `role="status"`; presentar mensajes claros y accionables. La ausencia de datos debe explicar cómo empezar o por qué aún no hay datos suficientes.
- **Formatos:** `Intl` con `es-ES`: euros con dos decimales, porcentajes y cantidades con coma decimal, fechas comprensibles y unidades de precio visibles. No presentar precios por unidad como precios por kilogramo ni inventar pesos.

## Implementación y revisión

Las páginas están en `frontend/src/pages`, los componentes compartidos en `frontend/src/components`, los tipos en `types.ts` y los formatos en `format.ts`. Añadir componentes solo cuando reduzcan duplicación real y mantener la lógica de dominio y los endpoints en el backend existente. Las decisiones visuales deben funcionar a 320 px, 390 px y escritorio, con zoom y teclado. Validar cambios con la compilación, las pruebas y una inspección real de los estados y recorridos afectados. Los criterios WCAG 2.2 AA incluyen contraste, orden y visibilidad del foco, reflujo, nombres accesibles y tamaño mínimo de objetivos; requieren comprobaciones manuales además de herramientas automáticas.

Para ejecutar las comprobaciones de frontend: `npm ci`, `npm run build` y `node --test tests/*.test.ts` desde `frontend` (Node 24). El backend se comprueba con `PYTHONPATH=backend python -m pytest backend/tests -q`, usando las dependencias de desarrollo y datos temporales de las pruebas.
