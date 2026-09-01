# RitaCart

RitaCart es una aplicación local para analizar tickets de compra recibidos por correo electrónico.

La idea es sencilla: importar automáticamente los tickets digitales del supermercado, extraer sus datos y convertirlos en un histórico útil para entender cuánto gastamos, qué compramos, cómo cambian los precios y cuáles son nuestros hábitos de compra.

## Objetivo

RitaCart no pretende ser un gestor de gastos general ni una plataforma multiusuario. Está pensada para ejecutarse en una red local, principalmente mediante Docker, con una instalación pequeña y fácil de mantener.

El primer supermercado soportado será **Mercadona**. La arquitectura permitirá añadir otros parsers más adelante, por ejemplo Carrefour, sin mezclar su lógica con la de Mercadona.

## Qué queremos analizar

- Gasto total por semana, mes y año.
- Evolución del gasto a lo largo del tiempo.
- Histórico de precios por producto.
- Incrementos y descensos de precio.
- Frecuencia con la que se compra cada producto.
- Cantidades compradas por periodo.
- Productos más habituales.
- Días de la semana en los que solemos comprar.
- Horas habituales de compra.
- Número de visitas al supermercado.
- Tiempo medio entre compras.
- Comparaciones entre meses y años.

## Flujo previsto

```text
Correo electrónico
       │
       ▼
Ticket PDF
       │
       ▼
Extracción de texto
       │
       ▼
Parser específico del supermercado
       │
       ▼
Normalización de productos y precios
       │
       ▼
SQLite
       │
       ▼
Dashboard y gráficas
```

Los tickets digitales de Mercadona contienen texto, por lo que el objetivo inicial es procesarlos de forma determinista sin OCR ni modelos de IA.

## Stack previsto

### Backend

- Python 3.13
- FastAPI
- SQLAlchemy
- PyMuPDF para extracción de texto de PDF

### Frontend

- TypeScript
- React
- Vite
- Tailwind CSS

### Datos

- SQLite

### Despliegue

- Docker
- Un único contenedor para la aplicación siempre que sea razonable
- Volumen persistente `/data`

El objetivo es poder ejecutarla fácilmente en Unraid u otro host Docker sin depender de Redis, PostgreSQL, MySQL u otros servicios externos.

## Modelo conceptual inicial

RitaCart distinguirá entre el ticket original y el producto normalizado.

```text
Receipt
 └── ReceiptItem
       └── ProductAlias
             └── Product
```

Esto permite conservar exactamente lo que aparecía en el ticket y, al mismo tiempo, agrupar variantes del nombre de un mismo producto para hacer análisis históricos.

Para precios y cantidades se evitarán números de coma flotante cuando puedan provocar errores de precisión. Los datos monetarios se tratarán como valores decimales.

## Principios del proyecto

- Local-first.
- Sin autenticación compleja mientras la instalación permanezca en una red privada.
- Sin permisos y roles innecesarios.
- Sin OCR si el documento ya contiene texto utilizable.
- Sin IA para tareas que puedan resolverse de forma determinista.
- Mantener siempre el PDF y los valores originales como evidencia de la importación.
- Evitar duplicados usando identificadores del correo y hashes de los archivos.
- Priorizar una arquitectura pequeña y comprensible frente a una plataforma genérica.

## MVP

La primera versión útil deberá poder:

1. Detectar automáticamente nuevos tickets de Mercadona recibidos por email.
2. Descargar y almacenar el PDF.
3. Extraer fecha, hora, total y líneas de producto.
4. Guardar productos, cantidades y precios en SQLite.
5. Evitar importar dos veces el mismo ticket.
6. Mostrar el histórico de compras.
7. Mostrar gasto mensual y anual.
8. Mostrar evolución de precios por producto.
9. Mostrar cuándo solemos hacer la compra por día de la semana y hora.

## Estado

Proyecto en fase inicial de diseño y desarrollo.
