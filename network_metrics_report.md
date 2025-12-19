# Análisis de Métricas de Red de Posts LLM

## Resumen de Métricas
La red se construyó conectando **Keywords (Palabras clave)** que aparecen simultáneamente en los mismos posts.

*   **Average Degree (Grado Promedio):** 6.33
    *   *Interpretación:* En promedio, cada palabra clave aparece junto a otras ~6 palabras clave distintas. Esto indica una alta interconexión en los temas tratados.
*   **Average Strength (Fuerza Promedio):** 62.56
    *   *Interpretación:* La fuerza representa la frecuencia total de co-ocurrencias. Un valor alto sugiere que no solo se conectan con varios temas, sino que lo hacen muy frecuentemente.
*   **Global Clustering Coefficient (Coeficiente de Agrupamiento):** 0.7016
    *   *Interpretación:* Un valor de 0.7 es extremadamente alto (el máximo es 1.0). Indica que si la palabra A aparece con B, y B con C, es muy probable que A aparezca con C. Los temas forman "cliques" o grupos semánticos muy compactos.

## Principales Concurrencias (Co-occurrences)
Las conexiones más fuertes (pares de temas que más se repiten juntos) son:

| Keyword 1 | Keyword 2 | Frecuencia (Peso) |
|-----------|-----------|-------------------|
| emissions | renewable energy | 64 |
| green transition | renewable energy | 47 |
| emissions | global warming | 43 |
| greenhouse effect | global warming | 31 |
| green transition | emissions | 26 |

Básicamente, el discurso gira en torno a la **transición verde** y **energías renovables** como respuesta a las **emisiones** y el **calentamiento global**.

## Visualización: Grafo Circular
A continuación se muestra el grafo de co-ocurrencias en disposición circular. El grosor de las líneas representa la fuerza de la conexión (concurrencia).

![Grafo Circular de Keywords](/circular_graph_llm_posts.png)
