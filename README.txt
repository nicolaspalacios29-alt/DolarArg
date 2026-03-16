App lista para deploy simple

Opción más fácil: Streamlit Community Cloud
1. Crear una cuenta en GitHub.
2. Subir estos 2 archivos al repositorio:
   - app.py
   - requirements.txt
3. Ir a Streamlit Community Cloud.
4. Elegir el repositorio y app.py.
5. Deploy.

Qué hace
- Proyección mensual del dólar 2026-2028
- Monte Carlo a dic-2026, dic-2027 y dic-2028
- Índice Big Mac
- Datos reales opcionales desde BCRA

Limitación
La parte de datos reales usa búsqueda heurística en BCRA. Para producción conviene fijar IDs exactos.
