# 🎯 TUBBY APP - Sistema Municipal de Gestión

[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## 📋 Descripción

**TUBBY APP** es un sistema integral de gestión municipal que administra múltiples servicios:

- 📚 **Gestión de Obras** - Control de inspecciones y obras públicas
- 🚗 **Vía Pública** - Manejo de espacios y servicios de vía pública
- 🗺️ **SIG Municipal** - Capas GIS y datos geoespaciales
- 📦 **Inventario** - Gestión de activos y material
- 🛋️ **Mobiliario Urbano** - Control de bancos, farolas, etc.
- 🅿️ **Parking de Camiones** - Sistema de reservas y ocupación
- 🌳 **Patrulla Verde** - Incidencias ambientales
- 👕 **Vestuario Personal** - Gestión de equipamiento de personal
- 🚨 **Plan de Emergencias** - Coordinación de emergencias

## 🚀 INICIO RÁPIDO

### Requisitos
- Python 3.8+
- MySQL Server
- Git

### Instalación

1. **Clonar repositorio**
   ```bash
   git clone https://github.com/thierro23-cloud/tubby_app.git
   cd tubby_app
   ```

2. **Crear entorno virtual**
   ```bash
   python -m venv venv
   source venv/bin/activate    # Linux/Mac
   # o
   venv\Scripts\activate       # Windows
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Edita .env con tus credenciales MySQL
   ```

5. **Ejecutar aplicación**
   ```bash
   python app.py
   ```

   Accede a: `http://localhost:5000`

## 📚 DOCUMENTACIÓN

- **[SETUP.md](SETUP.md)** - Guía detallada de configuración
- **[.env.example](.env.example)** - Variables de entorno requeridas

## 🏗️ ESTRUCTURA DEL PROYECTO

```
tubby_app/
├── .env.example              # Plantilla de variables
├── .gitignore                # Archivos ignorados por Git
├── config.py                 # Configuración centralizada
├── app.py                    # Aplicación principal
├── db.py                     # Gestión de conexiones
├── requirements.txt          # Dependencias Python
│
├── blueprints/               # Módulos/APIs
│   ├── agenda_core/
│   ├── inspecciones_obras/
│   ├── control_contenedores/
│   └── ...
│
├── core/                     # Lógica de negocio central
├── services/                 # Servicios auxiliares
├── forms/                    # Formularios Flask
├── templates/                # Vistas HTML
├── static/                   # CSS, JS, imágenes
├── sql/                      # Scripts de base de datos
├── tools/                    # Herramientas de utilidad
└── logs/                     # Archivos de log
```

## 🔐 SEGURIDAD

### Gestión de Credenciales

Las credenciales de base de datos están **aseguradas con variables de entorno**:

- ✅ Las credenciales se guardan en `.env` (NO en Git)
- ✅ El archivo `.env` está en `.gitignore`
- ✅ Se proporciona `.env.example` como plantilla
- ✅ `config.py` es seguro y se puede commitear

**NUNCA hagas esto:**
```bash
git add .env              # ❌ NO commitees credenciales
```

**SÍ hace esto:**
```bash
git add .env.example      # ✅ Plantilla de ejemplo
```

## 📊 BASES DE DATOS

El sistema gestiona 10 bases de datos MySQL:

| BD | Propósito |
|---|---|
| `bd_tbl_comunes` | Usuarios, roles, login |
| `control_via_publica` | Obras e inspecciones |
| `gis_municipal` | Datos geoespaciales |
| `inventario` | Gestión de activos |
| `mobiliario_urbano` | Bancos, farolas, etc. |
| `parquin_camiones` | Parking y reservas |
| `patrulla_verde` | Incidencias ambientales |
| `personal_vestuario` | Equipamiento personal |
| `plan_de_emergencias` | Planes y simulacros |

## 🔧 CONFIGURACIÓN

Todas las variables se configuran en `.env`:

```env
# Ejemplo: Base de datos común
COMUNES_HOST=localhost
COMUNES_USER=root
COMUNES_PASSWORD=tu_contraseña
COMUNES_DB=bd_tbl_comunes
COMUNES_PORT=3306
```

Ver [.env.example](.env.example) para todas las variables.

## 🛠️ DESARROLLO

### Crear nueva rama
```bash
git checkout -b feature/mi-feature
```

### Instalar dependencias de desarrollo
```bash
pip install pytest black flake8
```

### Ejecutar tests
```bash
pytest
```

### Formatear código
```bash
black .
```

## 📝 LOGS

Los logs se guardan en:
```
logs/endpoints_watcher.log
```

Configurable en `.env`:
```env
LOG_FILE=endpoints_watcher.log
LOG_LEVEL=INFO
```

## 🤝 CONTRIBUCIONES

1. Fork el repositorio
2. Crea una rama (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

**IMPORTANTE:** Nunca commitees `.env` o credenciales.

## ⚠️ SOLUCIÓN DE PROBLEMAS

### Conexión MySQL rechazada
- Verifica que MySQL está corriendo
- Revisa credenciales en `.env`
- Comprueba que la BD existe

### Módulo no encontrado
```bash
pip install -r requirements.txt
source venv/bin/activate
```

### Puerto 5000 en uso
```bash
# Cambiar puerto en app.py
app.run(port=5001)
```

## 📄 LICENCIA

MIT License - Ver [LICENSE](LICENSE) para detalles.

## 👤 AUTOR

**thierro23-cloud**
- GitHub: [@thierro23-cloud](https://github.com/thierro23-cloud)

## 📞 SOPORTE

Para reportar bugs o solicitar features, abre un [Issue](https://github.com/thierro23-cloud/tubby_app/issues).

---

**Última actualización:** Julio 2026  
**Versión:** 1.0.0
