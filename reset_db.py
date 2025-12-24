import database
import models

def reset():
    print("Conectando a la base de datos de Render...")
    try:
        # Esto borra la tabla 'operadores' vieja
        models.Base.metadata.drop_all(bind=database.engine)
        # Esto crea la tabla 'operadores' nueva con las columnas de la Matriz
        models.Base.metadata.create_all(bind=database.engine)
        print("✅ ÉXITO: La base de datos ha sido reseteada.")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    reset()