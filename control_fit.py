from flask import Flask, render_template_string, request, redirect, session, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import hashlib
from functools import wraps
import os
from werkzeug.utils import secure_filename
import qrcode
from io import BytesIO
import base64

# Configuración mínima
app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_super_secreta_control_fit_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gimnasio_completo_nuevo_v3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

# Crear directorio de uploads si no existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Modelo para Administradores
class Administrador(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

# Modelo para Miembros - CON TODOS LOS CAMPOS NUEVOS
class Miembro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50))
    apellidos = db.Column(db.String(50))
    edad = db.Column(db.Integer)
    dni = db.Column(db.String(8))
    celular = db.Column(db.String(9))
    email = db.Column(db.String(50))
    tipo_membresia = db.Column(db.String(20))
    fecha_inicio = db.Column(db.String(10))
    fecha_fin = db.Column(db.String(10))
    estado = db.Column(db.String(10))
    password = db.Column(db.String(128))
    # NUEVOS CAMPOS PARA EL SISTEMA DE PAGOS
    plan_seleccionado = db.Column(db.String(20))
    comprobante_path = db.Column(db.String(200))
    pago_verificado = db.Column(db.Boolean, default=False)
    codigo_qr = db.Column(db.String(100))
    fecha_pago = db.Column(db.DateTime)

# Función para hashear contraseñas
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Función para generar QR
def generar_codigo_qr(miembro_id, dni, nombre):
    # Crear datos únicos para el QR
    datos_qr = f"CONTROLFIT#{miembro_id}#{dni}#{nombre}#{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Generar QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(datos_qr)
    qr.make(fit=True)
    
    # Crear imagen QR
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Guardar en buffer
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    # Convertir a base64 para mostrar en HTML
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}", datos_qr

# Función para hacer backup automático de la base de datos
def hacer_backup():
    """Crea una copia de seguridad de la base de datos"""
    try:
        import shutil
        import time
        
        # Nombre del archivo de backup con timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_gimnasio_{timestamp}.db"
        
        # Copiar el archivo de la base de datos
        shutil.copy2('gimnasio_completo_nuevo_v3.db', backup_file)
        print(f"✅ Backup creado: {backup_file}")
        
    except Exception as e:
        print(f"❌ Error al crear backup: {e}")

# Función para cargar datos de ejemplo (opcional)
def cargar_datos_ejemplo():
    """Cargar datos de ejemplo si la base de datos está vacía"""
    try:
        # Verificar si hay miembros
        total_miembros = Miembro.query.count()
        total_admins = Administrador.query.count()
        
        print(f"📊 Estado de la base de datos:")
        print(f"   👥 Miembros registrados: {total_miembros}")
        print(f"   👑 Administradores: {total_admins}")
        
        return total_miembros, total_admins
        
    except Exception as e:
        print(f"❌ Error al verificar datos: {e}")
        return 0, 0

# Middleware para verificar autenticación
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# Middleware específico para admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'admin':
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# ---------------------------
# PLANTILLAS HTML (embebidas)
# ---------------------------

LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Login - Control Fit</title>
    <meta charset="UTF-8">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 0; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
        }
        .logo {
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
            box-sizing: border-box;
        }
        input:focus {
            border-color: #667eea;
            outline: none;
        }
        .btn {
            width: 100%;
            padding: 12px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .register-link {
            text-align: center;
            margin-top: 20px;
        }
        .alert {
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            text-align: center;
        }
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="logo">🏋️</div>
        <h1>Control Fit</h1>
        
        {% if mensaje %}
        <div class="alert {{ 'alert-error' if 'Error' in mensaje or 'incorrecto' in mensaje.lower() else 'alert-success' }}">
            {{ mensaje }}
        </div>
        {% endif %}
        
        <form method="POST">
            <div class="form-group">
                <label>Email:</label>
                <input type="email" name="email" required placeholder="tuemail@gmail.com">
            </div>
            
            <div class="form-group">
                <label>Contraseña:</label>
                <input type="password" name="password" required placeholder="••••••••">
            </div>
            
            <button type="submit" class="btn">🔐 Iniciar Sesión</button>
        </form>
        
        <div class="register-link">
            <p>¿No tienes cuenta? 
                <a href="/register-admin">Registro Admin</a> | 
                <a href="/register-miembro">Registro Miembro</a>
            </p>
        </div>
    </div>
</body>
</html>
'''

PLANES_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Planes - Control Fit</title>
    <meta charset="UTF-8">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 0; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        .planes-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 30px;
            margin-top: 40px;
        }
        .plan-card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s, box-shadow 0.3s;
            border: 3px solid transparent;
        }
        .plan-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }
        .plan-card.popular {
            border-color: #ff6b6b;
            position: relative;
            transform: scale(1.05);
        }
        .popular-badge {
            position: absolute;
            top: -15px;
            left: 50%;
            transform: translateX(-50%);
            background: #ff6b6b;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }
        .plan-name {
            font-size: 24px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }
        .plan-price {
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 20px;
        }
        .plan-duration {
            color: #666;
            margin-bottom: 20px;
        }
        .plan-features {
            list-style: none;
            padding: 0;
            margin-bottom: 30px;
        }
        .plan-features li {
            padding: 8px 0;
            border-bottom: 1px solid #eee;
            color: #555;
        }
        .btn-plan {
            width: 100%;
            padding: 15px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn-plan:hover {
            transform: translateY(-2px);
        }
        .user-info {
            background: rgba(255,255,255,0.1);
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        .logout-btn {
            background: #e74c3c;
            padding: 8px 15px;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            float: right;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="user-info">
            👤 Bienvenido, <strong>{{ user_nombre }}</strong>
            <a href="/logout" class="logout-btn" onclick="return confirm('¿Cerrar sesión?')">🚪 Cerrar Sesión</a>
        </div>
        
        <div class="header">
            <h1>🏋️ ELIGE TU PLAN DE ENTRENAMIENTO</h1>
            <p>Selecciona el plan que mejor se adapte a tus objetivos</p>
        </div>
        
        <div class="planes-container">
            <!-- Plan 1 Mes -->
            <div class="plan-card">
                <div class="plan-name">PLAN BÁSICO</div>
                <div class="plan-price">S/ 80.00</div>
                <div class="plan-duration">1 MES</div>
                <ul class="plan-features">
                    <li>✅ Acceso a todas las áreas</li>
                    <li>✅ Entrenamiento personalizado</li>
                    <li>✅ Lockers gratuitos</li>
                    <li>✅ Asesoría nutricional básica</li>
                </ul>
                <form method="POST" action="/seleccionar-plan">
                    <input type="hidden" name="plan" value="1_mes">
                    <input type="hidden" name="precio" value="80.00">
                    <button type="submit" class="btn-plan">🎯 ELEGIR ESTE PLAN</button>
                </form>
            </div>
            
            <!-- Plan 3 Meses -->
            <div class="plan-card popular">
                <div class="popular-badge">MÁS POPULAR</div>
                <div class="plan-name">PLAN AVANZADO</div>
                <div class="plan-price">S/ 210.00</div>
                <div class="plan-duration">3 MESES</div>
                <ul class="plan-features">
                    <li>✅ Todo lo del Plan Básico</li>
                    <li>✅ Clases grupales incluidas</li>
                    <li>✅ Evaluación física completa</li>
                    <li>✅ Plan nutricional avanzado</li>
                    <li>✅ 15% de descuento</li>
                </ul>
                <form method="POST" action="/seleccionar-plan">
                    <input type="hidden" name="plan" value="3_meses">
                    <input type="hidden" name="precio" value="210.00">
                    <button type="submit" class="btn-plan">🔥 ELEGIR ESTE PLAN</button>
                </form>
            </div>
            
            <!-- Plan 6 Meses -->
            <div class="plan-card">
                <div class="plan-name">PLAN PRO</div>
                <div class="plan-price">S/ 400.00</div>
                <div class="plan-duration">6 MESES</div>
                <ul class="plan-features">
                    <li>✅ Todo lo del Plan Avanzado</li>
                    <li>✅ Acceso ilimitado 24/7</li>
                    <li>✅ Entrenador personal 2 sesiones</li>
                    <li>✅ Suplementación básica</li>
                    <li>✅ 17% de descuento</li>
                </ul>
                <form method="POST" action="/seleccionar-plan">
                    <input type="hidden" name="plan" value="6_meses">
                    <input type="hidden" name="precio" value="400.00">
                    <button type="submit" class="btn-plan">💪 ELEGIR ESTE PLAN</button>
                </form>
            </div>
            
            <!-- Plan 1 Año -->
            <div class="plan-card">
                <div class="plan-name">PLAN PREMIUM</div>
                <div class="plan-price">S/ 850.00</div>
                <div class="plan-duration">1 AÑO</div>
                <ul class="plan-features">
                    <li>✅ Todo lo del Plan Pro</li>
                    <li>✅ Entrenador personal ilimitado</li>
                    <li>✅ Suplementación premium</li>
                    <li>✅ Acceso a zona VIP</li>
                    <li>✅ 20% de descuento</li>
                    <li>✅ Invitado 1 mes gratis</li>
                </ul>
                <form method="POST" action="/seleccionar-plan">
                    <input type="hidden" name="plan" value="1_anio">
                    <input type="hidden" name="precio" value="850.00">
                    <button type="submit" class="btn-plan">⭐ ELEGIR ESTE PLAN</button>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
'''

PAGO_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Pago - Control Fit</title>
    <meta charset="UTF-8">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 0; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        .payment-info {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            margin-bottom: 40px;
        }
        .qr-section, .upload-section {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
        }
        .qr-code {
            text-align: center;
            margin-bottom: 20px;
        }
        .qr-placeholder {
            width: 200px;
            height: 200px;
            background: #e9ecef;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 10px;
            font-size: 14px;
            color: #666;
        }
        .account-info {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-top: 20px;
        }
        .account-detail {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .upload-area {
            border: 2px dashed #667eea;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            margin-bottom: 20px;
            cursor: pointer;
            transition: background 0.3s;
        }
        .upload-area:hover {
            background: #f0f4ff;
        }
        .btn {
            padding: 12px 25px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .user-info {
            background: #34495e;
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .logout-btn {
            background: #e74c3c;
            padding: 8px 15px;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            float: right;
        }
        .plan-summary {
            background: #e8f5e8;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="user-info">
            👤 {{ user_nombre }} - Plan: {{ plan_info.nombre }}
            <a href="/planes" class="logout-btn" style="background: #3498db; margin-right: 10px;">← Volver</a>
            <a href="/logout" class="logout-btn">🚪 Cerrar Sesión</a>
        </div>
        
        <div class="header">
            <h1>💳 PAGO DE MEMBRESÍA</h1>
            <p>Realiza el pago y sube tu comprobante para activar tu membresía</p>
        </div>
        
        <div class="plan-summary">
            <h3>📋 Resumen de tu compra:</h3>
            <p><strong>Plan:</strong> {{ plan_info.nombre }}</p>
            <p><strong>Duración:</strong> {{ plan_info.duracion }}</p>
            <p><strong>Precio:</strong> S/ {{ plan_info.precio }}</p>
            <p><strong>Fecha de vencimiento:</strong> {{ plan_info.vencimiento }}</p>
        </div>
        
        <div class="payment-info">
            <div class="qr-section">
                <h3>📱 Pago con Yape</h3>
                <div class="qr-code">
                    <div class="qr-placeholder">
                        [CÓDIGO QR YAPE]<br>
                        948315642
                    </div>
                </div>
                <div class="account-info">
                    <h4>💳 Datos para transferencia:</h4>
                    <div class="account-detail">
                        <span>Banco:</span>
                        <span>BCP</span>
                    </div>
                    <div class="account-detail">
                        <span>N° Cuenta:</span>
                        <span>191-45678923-0-15</span>
                    </div>
                    <div class="account-detail">
                        <span>Titular:</span>
                        <span>CONTROL FIT GYM</span>
                    </div>
                    <div class="account-detail">
                        <span>Yape:</span>
                        <span>948315642</span>
                    </div>
                    <div class="account-detail">
                        <span>Plin:</span>
                        <span>948315642</span>
                    </div>
                </div>
            </div>
            
            <div class="upload-section">
                <h3>📤 Subir Comprobante</h3>
                <p>Una vez realizado el pago, sube una foto o captura de pantalla de tu comprobante:</p>
                
                <form method="POST" action="/subir-comprobante" enctype="multipart/form-data">
                    <input type="hidden" name="plan" value="{{ plan_info.tipo }}">
                    <input type="hidden" name="precio" value="{{ plan_info.precio }}">
                    
                    <div class="upload-area" onclick="document.getElementById('comprobante').click()">
                        <div style="font-size: 48px;">📁</div>
                        <p>Haz clic aquí para seleccionar tu comprobante</p>
                        <p style="font-size: 12px; color: #666;">Formatos: JPG, PNG, PDF (Máx. 16MB)</p>
                    </div>
                    
                    <input type="file" id="comprobante" name="comprobante" 
                           accept=".jpg,.jpeg,.png,.pdf" required 
                           style="display: none;" onchange="previewFile()">
                    
                    <div id="file-preview" style="margin-top: 20px;"></div>
                    
                    <button type="submit" class="btn" style="width: 100%; margin-top: 20px;">
                        ✅ ENVIAR COMPROBANTE
                    </button>
                </form>
            </div>
        </div>
        
        <div style="background: #fff3cd; padding: 15px; border-radius: 10px; margin-top: 20px;">
            <h4>📝 Instrucciones importantes:</h4>
            <ul>
                <li>Realiza el pago exacto del monto indicado</li>
                <li>Incluye tu nombre y DNI en el concepto del pago</li>
                <li>Sube una imagen clara del comprobante</li>
                <li>Tu membresía se activará en 24 horas después de la verificación</li>
                <li>Recibirás un código QR de acceso una vez verificado el pago</li>
            </ul>
        </div>
    </div>
    
    <script>
        function previewFile() {
            const file = document.getElementById('comprobante').files[0];
            const preview = document.getElementById('file-preview');
            
            if (file) {
                preview.innerHTML = `
                    <div style="background: #e8f5e8; padding: 10px; border-radius: 5px;">
                        <strong>Archivo seleccionado:</strong> ${file.name}<br>
                        <strong>Tamaño:</strong> ${(file.size / 1024 / 1024).toFixed(2)} MB
                    </div>
                `;
            }
        }
    </script>
</body>
</html>
'''

USUARIO_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Perfil - Control Fit</title>
    <style>
        body { font-family: Arial; background: #f2f4f7; padding: 20px; }
        .card { max-width: 700px; margin: 30px auto; background: white; border-radius: 8px; padding: 20px; box-shadow: 0 6px 18px rgba(0,0,0,0.08); }
        h2 { text-align: center; color: #333; margin-bottom: 10px; }
        .row { display:flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }
        .label { color: #555; font-weight: bold; width: 45%; }
        .value { color: #333; width: 50%; }
        .btn { display:block; width: 100%; padding:10px; margin-top:15px; text-align:center; background:#3b82f6; color:white; text-decoration:none; border-radius:6px; }
        .user-header { background: #34495e; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; }
        .qr-section { text-align: center; margin: 20px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; }
        .qr-code { width: 200px; height: 200px; background: #e9ecef; margin: 0 auto; display: flex; align-items: center; justify-content: center; border-radius: 8px; }
        .status-pendiente { color: #f39c12; font-weight: bold; }
        .status-activo { color: #27ae60; font-weight: bold; }
        .status-inactivo { color: #e74c3c; font-weight: bold; }
        .qr-image { max-width: 200px; max-height: 200px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="user-header">
            <h2>👤 Perfil del Socio</h2>
            <p>Bienvenido, <strong>{{ miembro.nombre }}</strong></p>
        </div>
        
        <div class="row"><div class="label">Nombre</div><div class="value">{{ miembro.nombre }} {{ miembro.apellidos or '' }}</div></div>
        <div class="row"><div class="label">Email</div><div class="value">{{ miembro.email }}</div></div>
        <div class="row"><div class="label">DNI</div><div class="value">{{ miembro.dni or '-' }}</div></div>
        <div class="row"><div class="label">Celular</div><div class="value">{{ miembro.celular or '-' }}</div></div>
        <div class="row"><div class="label">Tipo Membresía</div><div class="value">{{ miembro.tipo_membresia or 'Por seleccionar' }}</div></div>
        <div class="row"><div class="label">Fecha de ingreso</div><div class="value">{{ miembro.fecha_inicio or '-' }}</div></div>
        <div class="row"><div class="label">Fecha de vencimiento</div><div class="value">{{ miembro.fecha_fin or '-' }}</div></div>
        <div class="row"><div class="label">Estado de pago</div>
            <div class="value">
                {% if miembro.pago_verificado %}
                    <span class="status-activo">✅ VERIFICADO</span>
                {% elif miembro.comprobante_path %}
                    <span class="status-pendiente">⏳ EN REVISIÓN</span>
                {% else %}
                    <span class="status-inactivo">❌ PENDIENTE</span>
                {% endif %}
            </div>
        </div>
        <div class="row"><div class="label">Estado membresía</div>
            <div class="value">
                <span style="color: {{ 'green' if miembro.estado == 'Activa' else 'red' }}; font-weight: bold;">
                    {{ miembro.estado or 'Inactiva' }}
                </span>
            </div>
        </div>

        {% if miembro.pago_verificado and miembro.estado == 'Activa' %}
        <div class="qr-section">
            <h3>🎫 Tu Código QR de Acceso</h3>
            {% if qr_image %}
                <img src="{{ qr_image }}" alt="Código QR" class="qr-image">
                <p style="margin-top: 10px; font-size: 12px; color: #666;">
                    Muestra este código QR en recepción para ingresar al gimnasio
                </p>
            {% else %}
                <div class="qr-code">
                    CÓDIGO QR<br>
                    {{ miembro.id }}-{{ miembro.dni }}
                </div>
            {% endif %}
        </div>
        {% elif not miembro.pago_verificado %}
        <div style="text-align: center; margin: 20px 0;">
            <a href="/planes" class="btn" style="background: #27ae60;">🎯 ELEGIR PLAN DE MEMBRESÍA</a>
        </div>
        {% endif %}

        <a class="btn" href="/logout">Cerrar sesión</a>
    </div>
</body>
</html>
'''

MEMBRESIAS_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Gestión de Miembros - Control Fit</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial; background: #f2f4f7; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #34495e; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: bold; }
        .btn { padding: 8px 15px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn-success { background: #27ae60; color: white; }
        .btn-warning { background: #f39c12; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-info { background: #3498db; color: white; }
        .btn-primary { background: #9b59b6; color: white; }
        .status-activo { color: #27ae60; font-weight: bold; }
        .status-pendiente { color: #f39c12; font-weight: bold; }
        .status-inactivo { color: #e74c3c; font-weight: bold; }
        .search-box { margin-bottom: 20px; }
        .search-box input { padding: 10px; width: 300px; border: 1px solid #ddd; border-radius: 5px; }
        .action-buttons { display: flex; gap: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>👥 Gestión de Miembros</h1>
            <p>Administrador: <strong>{{ admin_nombre }}</strong></p>
            <div>
                <a href="/" class="btn btn-info">← Volver al Panel</a>
                <a href="/verificar-pagos" class="btn btn-warning">💳 Verificar Pagos</a>
                <a href="/agregar-miembro" class="btn btn-primary">➕ Agregar Miembro</a>
                <a href="/logout" class="btn btn-danger" style="float: right;">🚪 Cerrar Sesión</a>
            </div>
        </div>

        <div class="card">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="🔍 Buscar por nombre, email o DNI..." onkeyup="searchMembers()">
            </div>

            <table id="membersTable">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Nombre</th>
                        <th>Email</th>
                        <th>DNI</th>
                        <th>Celular</th>
                        <th>Membresía</th>
                        <th>Estado Pago</th>
                        <th>Estado</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody>
                    {% for miembro in miembros %}
                    <tr>
                        <td>{{ miembro.id }}</td>
                        <td>{{ miembro.nombre }} {{ miembro.apellidos or '' }}</td>
                        <td>{{ miembro.email }}</td>
                        <td>{{ miembro.dni or '-' }}</td>
                        <td>{{ miembro.celular or '-' }}</td>
                        <td>{{ miembro.tipo_membresia or 'Por activar' }}</td>
                        <td>
                            {% if miembro.pago_verificado %}
                                <span class="status-activo">✅ Verificado</span>
                            {% elif miembro.comprobante_path %}
                                <span class="status-pendiente">⏳ Pendiente</span>
                            {% else %}
                                <span class="status-inactivo">❌ Sin pago</span>
                            {% endif %}
                        </td>
                        <td>
                            <span class="status-{{ miembro.estado.lower() if miembro.estado else 'inactivo' }}">
                                {{ miembro.estado or 'Inactiva' }}
                            </span>
                        </td>
                        <td>
                            <div class="action-buttons">
                                {% if miembro.comprobante_path and not miembro.pago_verificado %}
                                    <a href="/verificar-pago/{{ miembro.id }}" class="btn btn-success">✅ Verificar</a>
                                {% endif %}
                                <a href="/editar-miembro/{{ miembro.id }}" class="btn btn-info">✏️ Editar</a>
                                <a href="/eliminar-miembro/{{ miembro.id }}" class="btn btn-danger" onclick="return confirm('¿Estás seguro de eliminar a {{ miembro.nombre }}?')">🗑️ Eliminar</a>
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function searchMembers() {
            var input = document.getElementById("searchInput");
            var filter = input.value.toLowerCase();
            var table = document.getElementById("membersTable");
            var tr = table.getElementsByTagName("tr");

            for (var i = 1; i < tr.length; i++) {
                var tdNombre = tr[i].getElementsByTagName("td")[1];
                var tdEmail = tr[i].getElementsByTagName("td")[2];
                var tdDNI = tr[i].getElementsByTagName("td")[3];
                
                if (tdNombre || tdEmail || tdDNI) {
                    var nombre = tdNombre.textContent || tdNombre.innerText;
                    var email = tdEmail.textContent || tdEmail.innerText;
                    var dni = tdDNI.textContent || tdDNI.innerText;
                    
                    if (nombre.toLowerCase().indexOf(filter) > -1 || 
                        email.toLowerCase().indexOf(filter) > -1 ||
                        dni.toLowerCase().indexOf(filter) > -1) {
                        tr[i].style.display = "";
                    } else {
                        tr[i].style.display = "none";
                    }
                }
            }
        }
    </script>
</body>
</html>
'''

VERIFICAR_PAGOS_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Verificar Pagos - Control Fit</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial; background: #f2f4f7; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #34495e; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .btn { padding: 8px 15px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn-success { background: #27ae60; color: white; }
        .btn-warning { background: #f39c12; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-info { background: #3498db; color: white; }
        .payment-item { border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 8px; }
        .payment-info { margin-bottom: 10px; }
        .comprobante-img { max-width: 300px; max-height: 300px; border: 1px solid #ddd; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💳 Verificación de Pagos Pendientes</h1>
            <p>Administrador: <strong>{{ admin_nombre }}</strong></p>
            <div>
                <a href="/" class="btn btn-info">← Volver al Panel</a>
                <a href="/membresias" class="btn btn-warning">👥 Ver Miembros</a>
                <a href="/logout" class="btn btn-danger" style="float: right;">🚪 Cerrar Sesión</a>
            </div>
        </div>

        <div class="card">
            <h3>Pagos Pendientes de Verificación</h3>
            
            {% if pagos_pendientes %}
                {% for pago in pagos_pendientes %}
                <div class="payment-item">
                    <div class="payment-info">
                        <strong>Miembro:</strong> {{ pago.nombre }} {{ pago.apellidos or '' }}<br>
                        <strong>Email:</strong> {{ pago.email }}<br>
                        <strong>DNI:</strong> {{ pago.dni or '-' }}<br>
                        <strong>Plan:</strong> {{ pago.plan_seleccionado or pago.tipo_membresia }}<br>
                        <strong>Fecha de Pago:</strong> {{ pago.fecha_pago.strftime('%d/%m/%Y %H:%M') if pago.fecha_pago else 'No registrada' }}<br>
                        <strong>Comprobante:</strong>
                        {% if pago.comprobante_path %}
                            <br><img src="/uploads/{{ pago.comprobante_path.split('/')[-1] }}" alt="Comprobante" class="comprobante-img">
                        {% else %}
                            No disponible
                        {% endif %}
                    </div>
                    
                    <div>
                        <a href="/aprobar-pago/{{ pago.id }}" class="btn btn-success">✅ Aprobar Pago</a>
                        <a href="/rechazar-pago/{{ pago.id }}" class="btn btn-danger">❌ Rechazar Pago</a>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <p>No hay pagos pendientes de verificación.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

EDITAR_MIEMBRO_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Editar Miembro - Control Fit</title>
    <meta charset="UTF-8">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 0; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input, select {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
            box-sizing: border-box;
        }
        input:focus, select:focus {
            border-color: #667eea;
            outline: none;
        }
        .btn {
            padding: 12px 25px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
            text-decoration: none;
            display: inline-block;
            margin-right: 10px;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .btn-danger {
            background: #e74c3c;
        }
        .btn-secondary {
            background: #95a5a6;
        }
        .button-group {
            display: flex;
            justify-content: space-between;
            margin-top: 30px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✏️ Editar Miembro</h1>
            <p>Administrador: <strong>{{ admin_nombre }}</strong></p>
        </div>

        <form method="POST">
            <div class="form-group">
                <label>Nombre:</label>
                <input type="text" name="nombre" value="{{ miembro.nombre }}" required>
            </div>
            
            <div class="form-group">
                <label>Apellidos:</label>
                <input type="text" name="apellidos" value="{{ miembro.apellidos or '' }}">
            </div>
            
            <div class="form-group">
                <label>Email:</label>
                <input type="email" name="email" value="{{ miembro.email }}" required>
            </div>
            
            <div class="form-group">
                <label>DNI:</label>
                <input type="text" name="dni" value="{{ miembro.dni or '' }}" pattern="[0-9]{8}">
            </div>
            
            <div class="form-group">
                <label>Celular:</label>
                <input type="text" name="celular" value="{{ miembro.celular or '' }}" pattern="[0-9]{9}">
            </div>
            
            <div class="form-group">
                <label>Edad:</label>
                <input type="number" name="edad" value="{{ miembro.edad or '' }}" min="16" max="100">
            </div>
            
            <div class="form-group">
                <label>Tipo de Membresía:</label>
                <select name="tipo_membresia">
                    <option value="Por activar" {{ 'selected' if miembro.tipo_membresia == 'Por activar' else '' }}>Por activar</option>
                    <option value="1 Mes" {{ 'selected' if miembro.tipo_membresia == '1 Mes' else '' }}>1 Mes</option>
                    <option value="3 Meses" {{ 'selected' if miembro.tipo_membresia == '3 Meses' else '' }}>3 Meses</option>
                    <option value="6 Meses" {{ 'selected' if miembro.tipo_membresia == '6 Meses' else '' }}>6 Meses</option>
                    <option value="1 Año" {{ 'selected' if miembro.tipo_membresia == '1 Año' else '' }}>1 Año</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Estado de Pago:</label>
                <select name="pago_verificado">
                    <option value="false" {{ 'selected' if not miembro.pago_verificado else '' }}>Pendiente</option>
                    <option value="true" {{ 'selected' if miembro.pago_verificado else '' }}>Verificado</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Estado de Membresía:</label>
                <select name="estado">
                    <option value="Inactiva" {{ 'selected' if miembro.estado == 'Inactiva' else '' }}>Inactiva</option>
                    <option value="Activa" {{ 'selected' if miembro.estado == 'Activa' else '' }}>Activa</option>
                    <option value="Pendiente" {{ 'selected' if miembro.estado == 'Pendiente' else '' }}>Pendiente</option>
                    <option value="Vencida" {{ 'selected' if miembro.estado == 'Vencida' else '' }}>Vencida</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>Fecha de Inicio:</label>
                <input type="date" name="fecha_inicio" value="{{ miembro.fecha_inicio or '' }}">
            </div>
            
            <div class="form-group">
                <label>Fecha de Fin:</label>
                <input type="date" name="fecha_fin" value="{{ miembro.fecha_fin or '' }}">
            </div>

            <div class="button-group">
                <a href="/membresias" class="btn btn-secondary">← Cancelar</a>
                <button type="submit" class="btn">💾 Guardar Cambios</button>
            </div>
        </form>
    </div>
</body>
</html>
'''

# ---------------------------
# RUTAS BÁSICAS
# ---------------------------

@app.route('/')
@login_required
def inicio():
    if session.get('user_type') == 'admin':
        admin = Administrador.query.get(session['user_id'])
        if not admin:
            session.clear()
            return redirect('/login')
            
        return f"""
        <html>
        <body style="font-family: Arial; padding: 20px; background: #f0f2f5;">
            <div style="max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="background: #34495e; color: white; padding: 15px 20px; border-radius: 5px; margin-bottom: 20px;">
                    👤 Administrador: <strong>{admin.nombre}</strong>
                    <a href="/logout" style="background: #e74c3c; padding: 8px 15px; color: white; text-decoration: none; border-radius: 5px; float: right;">🚪 Cerrar Sesión</a>
                </div>
                
                <h1>🏋️ CONTROL FIT GYM</h1>
                <p style="text-align: center; font-size: 20px; color: #27ae60;">✅ PANEL DE ADMINISTRADOR</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="/membresias" style="display: inline-block; padding: 15px 30px; margin: 10px; background: #3498db; color: white; text-decoration: none; border-radius: 5px; font-size: 18px;">📋 Ver Miembros</a>
                    <a href="/verificar-pagos" style="display: inline-block; padding: 15px 30px; margin: 10px; background: #f39c12; color: white; text-decoration: none; border-radius: 5px; font-size: 18px;">💳 Verificar Pagos</a>
                    <a href="/agregar-miembro" style="display: inline-block; padding: 15px 30px; margin: 10px; background: #9b59b6; color: white; text-decoration: none; border-radius: 5px; font-size: 18px;">➕ Agregar Miembro</a>
                </div>
                
                <p style="text-align: center; color: #666;">
                    Sistema de gestión de membresías - Acceso Administrativo
                </p>
            </div>
        </body>
        </html>
        """
    else:
        return redirect('/usuario')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if session.get('user_type') == 'admin':
            return redirect('/')
        else:
            return redirect('/usuario')

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        hashed_password = hash_password(password)

        print(f"🔍 Intentando login para: {email}")

        # Buscar en administradores
        admin = Administrador.query.filter_by(email=email).first()
        if admin:
            print(f"✅ Admin encontrado: {admin.nombre}")
            if admin.password == hashed_password:
                session['user_id'] = admin.id
                session['user_type'] = 'admin'
                session['user_nombre'] = admin.nombre
                print("✅ Login admin exitoso")
                return redirect('/')
            else:
                print("❌ Contraseña admin incorrecta")

        # Buscar en miembros
        miembro = Miembro.query.filter_by(email=email).first()
        if miembro:
            print(f"✅ Miembro encontrado: {miembro.nombre}")
            if miembro.password and miembro.password.strip():
                if miembro.password == hashed_password:
                    session['user_id'] = miembro.id
                    session['user_type'] = 'miembro'
                    session['user_nombre'] = miembro.nombre
                    print("✅ Login miembro exitoso")
                    return redirect('/usuario')
                else:
                    print("❌ Contraseña miembro incorrecta")
            else:
                print("❌ Miembro sin contraseña configurada")

        print("❌ Login fallido")
        return render_template_string(LOGIN_HTML, mensaje='❌ Error: Email o contraseña incorrectos')

    return render_template_string(LOGIN_HTML)

@app.route('/register-admin', methods=['GET', 'POST'])
def register_admin():
    if 'user_id' in session:
        return redirect('/')
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            return '''
            <script>
                alert("Las contraseñas no coinciden");
                window.history.back();
            </script>
            '''
        
        if len(password) < 6:
            return '''
            <script>
                alert("La contraseña debe tener al menos 6 caracteres");
                window.history.back();
            </script>
            '''
        
        # Verificar si el email ya existe
        existe_admin = Administrador.query.filter_by(email=email).first()
        if existe_admin:
            return '''
            <script>
                alert("Este email ya está registrado");
                window.history.back();
            </script>
            '''
        
        # Crear nuevo administrador
        nuevo_admin = Administrador(
            nombre=nombre,
            email=email,
            password=hash_password(password)
        )
        
        try:
            db.session.add(nuevo_admin)
            db.session.commit()
            
            return '''
            <script>
                alert("✅ Administrador registrado exitosamente");
                window.location.href = "/login";
            </script>
            '''
            
        except Exception as e:
            return f'''
            <script>
                alert("Error al registrar: {str(e)}");
                window.history.back();
            </script>
            '''
    
    # FORMULARIO DE REGISTRO ADMIN (HTML)
    return '''
    <html>
    <head>
        <title>Registro Admin - Control Fit</title>
        <meta charset="UTF-8">
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 0; 
                padding: 0; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .register-container {
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 400px;
            }
            .logo {
                text-align: center;
                font-size: 2.5em;
                margin-bottom: 10px;
            }
            h1 {
                text-align: center;
                color: #333;
                margin-bottom: 30px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #555;
            }
            input {
                width: 100%;
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s;
                box-sizing: border-box;
            }
            input:focus {
                border-color: #667eea;
                outline: none;
            }
            .btn {
                width: 100%;
                padding: 12px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                transition: transform 0.2s;
            }
            .btn:hover {
                transform: translateY(-2px);
            }
            .login-link {
                text-align: center;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="register-container">
            <div class="logo">👑</div>
            <h1>Registro Administrador</h1>
            
            <form method="POST">
                <div class="form-group">
                    <label>Nombre Completo:</label>
                    <input type="text" name="nombre" required placeholder="Administrador Principal">
                </div>
                
                <div class="form-group">
                    <label>Email:</label>
                    <input type="email" name="email" required placeholder="admin@controlfit.com">
                </div>
                
                <div class="form-group">
                    <label>Contraseña:</label>
                    <input type="password" name="password" required placeholder="Mínimo 6 caracteres" minlength="6">
                </div>
                
                <div class="form-group">
                    <label>Confirmar Contraseña:</label>
                    <input type="password" name="confirm_password" required placeholder="Repite tu contraseña">
                </div>
                
                <button type="submit" class="btn">👑 Registrar Administrador</button>
            </form>
            
            <div class="login-link">
                <p>¿Ya tienes cuenta? <a href="/login">Inicia sesión aquí</a></p>
                <p><a href="/register-miembro">Registrarse como Miembro</a></p>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/register-miembro', methods=['GET', 'POST'])
def register_miembro():
    if 'user_id' in session:
        return redirect('/usuario' if session.get('user_type') == 'miembro' else '/')
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellidos = request.form['apellidos']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        dni = request.form['dni']
        celular = request.form['celular']
        edad = request.form['edad']
        
        if password != confirm_password:
            return render_template_string(LOGIN_HTML, mensaje='❌ Las contraseñas no coinciden')
        
        if len(password) < 6:
            return render_template_string(LOGIN_HTML, mensaje='❌ La contraseña debe tener al menos 6 caracteres')
        
        existe_miembro = Miembro.query.filter_by(email=email).first()
        if existe_miembro:
            return render_template_string(LOGIN_HTML, mensaje='❌ Este email ya está registrado')
        
        nuevo_miembro = Miembro(
            nombre=nombre,
            apellidos=apellidos,
            email=email,
            password=hash_password(password),
            dni=dni,
            celular=celular,
            edad=edad,
            tipo_membresia='Por activar',
            fecha_inicio=datetime.now().strftime('%Y-%m-%d'),
            fecha_fin=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            estado='Inactiva'
        )
        
        try:
            db.session.add(nuevo_miembro)
            db.session.commit()
            
            session['user_id'] = nuevo_miembro.id
            session['user_type'] = 'miembro'
            session['user_nombre'] = nuevo_miembro.nombre
            
            return redirect('/usuario')
            
        except Exception as e:
            return render_template_string(LOGIN_HTML, mensaje=f'❌ Error al registrar: {str(e)}')
    
    return '''
    <html>
    <body style="font-family: Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 100vh; display: flex; align-items: center; justify-content: center;">
        <div style="background: white; padding: 40px; border-radius: 15px; box-shadow: 0 15px 35px rgba(0,0,0,0.1); width: 100%; max-width: 400px;">
            <div style="text-align: center; font-size: 2.5em; margin-bottom: 10px;">🏋️</div>
            <h1 style="text-align: center; color: #333; margin-bottom: 30px;">Registro Miembro</h1>
            
            <form method="POST">
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: bold; color: #555;">Nombre:</label>
                    <input type="text" name="nombre" required placeholder="Juan" style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; box-sizing: border-box;">
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: bold; color: #555;">Apellidos:</label>
                    <input type="text" name="apellidos" required placeholder="Pérez García" style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; box-sizing: border-box;">
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: bold; color: #555;">Email:</label>
                    <input type="email" name="email" required placeholder="miembro@ejemplo.com" style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; box-sizing: border-box;">
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: bold; color: #555;">DNI:</label>
                    <input type="text" name="dni" required placeholder="12345678" pattern="[0-9]{8}" style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; box-sizing: border-box;">
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: bold; color: #555;">Celular:</label>
                    <input type="text" name="celular" required placeholder="987654321" pattern="[0-9]{9}" style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; box-sizing: border-box;">
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: bold; color: #555;">Edad:</label>
                    <input type="number" name="edad" required min="16" max="100" placeholder="25" style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; box-sizing: border-box;">
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: bold; color: #555;">Contraseña:</label>
                    <input type="password" name="password" required placeholder="Mínimo 6 caracteres" minlength="6" style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; box-sizing: border-box;">
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: bold; color: #555;">Confirmar Contraseña:</label>
                    <input type="password" name="confirm_password" required placeholder="Repite tu contraseña" style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; box-sizing: border-box;">
                </div>
                
                <button type="submit" style="width: 100%; padding: 12px; background: linear-gradient(45deg, #667eea, #764ba2); color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer;">📝 Registrarse como Miembro</button>
            </form>
            
            <div style="text-align: center; margin-top: 20px;">
                <p>¿Ya tienes cuenta? <a href="/login">Inicia sesión aquí</a></p>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/agregar-miembro', methods=['GET', 'POST'])
@admin_required
def agregar_miembro():
    admin = Administrador.query.get(session['user_id'])
    if not admin:
        return redirect('/login')
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellidos = request.form['apellidos']
        email = request.form['email']
        password = request.form['password']
        dni = request.form['dni']
        celular = request.form['celular']
        edad = request.form['edad']
        tipo_membresia = request.form['tipo_membresia']
        estado = request.form['estado']
        fecha_inicio = request.form['fecha_inicio']
        fecha_fin = request.form['fecha_fin']
        
        # Verificar si el email ya existe
        existe_miembro = Miembro.query.filter_by(email=email).first()
        if existe_miembro:
            return f'''
            <script>
                alert("❌ Este email ya está registrado");
                window.history.back();
            </script>
            '''
        
        # Crear nuevo miembro
        nuevo_miembro = Miembro(
            nombre=nombre,
            apellidos=apellidos,
            email=email,
            password=hash_password(password),
            dni=dni,
            celular=celular,
            edad=edad,
            tipo_membresia=tipo_membresia,
            estado=estado,
            fecha_inicio=fecha_inicio or datetime.now().strftime('%Y-%m-%d'),
            fecha_fin=fecha_fin or (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            pago_verificado=True if estado == 'Activa' else False
        )
        
        try:
            db.session.add(nuevo_miembro)
            db.session.commit()
            
            return f'''
            <script>
                alert("✅ Miembro agregado exitosamente");
                window.location.href = "/membresias";
            </script>
            '''
            
        except Exception as e:
            return f'''
            <script>
                alert("Error al agregar miembro: {str(e)}");
                window.history.back();
            </script>
            '''
    
    # FORMULARIO PARA AGREGAR MIEMBRO
    return f'''
    <html>
    <head>
        <title>Agregar Miembro - Control Fit</title>
        <meta charset="UTF-8">
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                margin: 0; 
                padding: 0; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .form-group {{
                margin-bottom: 20px;
            }}
            label {{
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #555;
            }}
            input, select {{
                width: 100%;
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s;
                box-sizing: border-box;
            }}
            input:focus, select:focus {{
                border-color: #667eea;
                outline: none;
            }}
            .btn {{
                padding: 12px 25px;
                background: linear-gradient(45deg, #667eea, #764ba2);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                transition: transform 0.2s;
                text-decoration: none;
                display: inline-block;
                margin-right: 10px;
            }}
            .btn:hover {{
                transform: translateY(-2px);
            }}
            .btn-secondary {{
                background: #95a5a6;
            }}
            .button-group {{
                display: flex;
                justify-content: space-between;
                margin-top: 30px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>➕ Agregar Miembro</h1>
                <p>Administrador: <strong>{admin.nombre}</strong></p>
            </div>

            <form method="POST">
                <div class="form-group">
                    <label>Nombre:</label>
                    <input type="text" name="nombre" required>
                </div>
                
                <div class="form-group">
                    <label>Apellidos:</label>
                    <input type="text" name="apellidos">
                </div>
                
                <div class="form-group">
                    <label>Email:</label>
                    <input type="email" name="email" required>
                </div>
                
                <div class="form-group">
                    <label>Contraseña:</label>
                    <input type="password" name="password" required minlength="6">
                </div>
                
                <div class="form-group">
                    <label>DNI:</label>
                    <input type="text" name="dni" pattern="[0-9]{{8}}">
                </div>
                
                <div class="form-group">
                    <label>Celular:</label>
                    <input type="text" name="celular" pattern="[0-9]{{9}}">
                </div>
                
                <div class="form-group">
                    <label>Edad:</label>
                    <input type="number" name="edad" min="16" max="100">
                </div>
                
                <div class="form-group">
                    <label>Tipo de Membresía:</label>
                    <select name="tipo_membresia">
                        <option value="Por activar">Por activar</option>
                        <option value="1 Mes">1 Mes</option>
                        <option value="3 Meses">3 Meses</option>
                        <option value="6 Meses">6 Meses</option>
                        <option value="1 Año">1 Año</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>Estado de Membresía:</label>
                    <select name="estado">
                        <option value="Inactiva">Inactiva</option>
                        <option value="Activa">Activa</option>
                        <option value="Pendiente">Pendiente</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>Fecha de Inicio:</label>
                    <input type="date" name="fecha_inicio" value="{datetime.now().strftime('%Y-%m-%d')}">
                </div>
                
                <div class="form-group">
                    <label>Fecha de Fin:</label>
                    <input type="date" name="fecha_fin" value="{(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')}">
                </div>

                <div class="button-group">
                    <a href="/membresias" class="btn btn-secondary">← Cancelar</a>
                    <button type="submit" class="btn">➕ Agregar Miembro</button>
                </div>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/editar-miembro/<int:miembro_id>', methods=['GET', 'POST'])
@admin_required
def editar_miembro(miembro_id):
    admin = Administrador.query.get(session['user_id'])
    if not admin:
        return redirect('/login')
    
    miembro = Miembro.query.get(miembro_id)
    if not miembro:
        return redirect('/membresias')
    
    if request.method == 'POST':
        miembro.nombre = request.form['nombre']
        miembro.apellidos = request.form['apellidos']
        miembro.email = request.form['email']
        miembro.dni = request.form['dni']
        miembro.celular = request.form['celular']
        miembro.edad = request.form['edad']
        miembro.tipo_membresia = request.form['tipo_membresia']
        miembro.pago_verificado = request.form['pago_verificado'] == 'true'
        miembro.estado = request.form['estado']
        miembro.fecha_inicio = request.form['fecha_inicio']
        miembro.fecha_fin = request.form['fecha_fin']
        
        # Si el pago se verifica y la membresía se activa, generar QR
        if miembro.pago_verificado and miembro.estado == 'Activa' and not miembro.codigo_qr:
            qr_image, qr_data = generar_codigo_qr(miembro.id, miembro.dni, miembro.nombre)
            miembro.codigo_qr = qr_data
        
        try:
            db.session.commit()
            return f'''
            <script>
                alert("✅ Miembro actualizado exitosamente");
                window.location.href = "/membresias";
            </script>
            '''
        except Exception as e:
            return f'''
            <script>
                alert("Error al actualizar: {str(e)}");
                window.history.back();
            </script>
            '''
    
    return render_template_string(EDITAR_MIEMBRO_HTML, miembro=miembro, admin_nombre=admin.nombre)

@app.route('/eliminar-miembro/<int:miembro_id>')
@admin_required
def eliminar_miembro(miembro_id):
    miembro = Miembro.query.get(miembro_id)
    if miembro:
        # Eliminar comprobante si existe
        if miembro.comprobante_path and os.path.exists(miembro.comprobante_path):
            os.remove(miembro.comprobante_path)
        
        db.session.delete(miembro)
        db.session.commit()
        
        return f'''
        <script>
            alert("✅ Miembro eliminado exitosamente");
            window.location.href = "/membresias";
        </script>
        '''
    
    return redirect('/membresias')

@app.route('/planes')
@login_required
def planes():
    if session.get('user_type') != 'miembro':
        return redirect('/')
    
    return render_template_string(PLANES_HTML, user_nombre=session.get('user_nombre'))

@app.route('/seleccionar-plan', methods=['POST'])
@login_required
def seleccionar_plan():
    if session.get('user_type') != 'miembro':
        return redirect('/')
    
    plan = request.form['plan']
    precio = request.form['precio']
    
    planes_map = {
        '1_mes': {'nombre': 'PLAN BÁSICO (1 MES)', 'duracion': '1 mes', 'dias': 30},
        '3_meses': {'nombre': 'PLAN AVANZADO (3 MESES)', 'duracion': '3 meses', 'dias': 90},
        '6_meses': {'nombre': 'PLAN PRO (6 MESES)', 'duracion': '6 meses', 'dias': 180},
        '1_anio': {'nombre': 'PLAN PREMIUM (1 AÑO)', 'duracion': '1 año', 'dias': 365}
    }
    
    plan_info = planes_map.get(plan, {})
    fecha_vencimiento = (datetime.now() + timedelta(days=plan_info.get('dias', 30))).strftime('%d/%m/%Y')
    
    return render_template_string(PAGO_HTML, 
                                user_nombre=session.get('user_nombre'),
                                plan_info={
                                    'tipo': plan,
                                    'nombre': plan_info.get('nombre', ''),
                                    'duracion': plan_info.get('duracion', ''),
                                    'precio': precio,
                                    'vencimiento': fecha_vencimiento
                                })

@app.route('/subir-comprobante', methods=['POST'])
@login_required
def subir_comprobante():
    if session.get('user_type') != 'miembro':
        return redirect('/')
    
    if 'comprobante' not in request.files:
        return "No se seleccionó ningún archivo", 400
    
    file = request.files['comprobante']
    if file.filename == '':
        return "No se seleccionó ningún archivo", 400
    
    if file:
        filename = secure_filename(f"{session['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        miembro = Miembro.query.get(session['user_id'])
        if miembro:
            plan = request.form['plan']
            planes_map = {
                '1_mes': {'nombre': '1 Mes', 'dias': 30},
                '3_meses': {'nombre': '3 Meses', 'dias': 90},
                '6_meses': {'nombre': '6 Meses', 'dias': 180},
                '1_anio': {'nombre': '1 Año', 'dias': 365}
            }
            
            plan_info = planes_map.get(plan, {})
            miembro.plan_seleccionado = plan_info.get('nombre', '')
            miembro.tipo_membresia = plan_info.get('nombre', '')
            miembro.comprobante_path = filepath
            miembro.pago_verificado = False
            miembro.fecha_pago = datetime.now()
            miembro.fecha_inicio = datetime.now().strftime('%Y-%m-%d')
            miembro.fecha_fin = (datetime.now() + timedelta(days=plan_info.get('dias', 30))).strftime('%Y-%m-%d')
            miembro.estado = 'Pendiente'
            
            db.session.commit()
        
        return redirect('/usuario')
    
    return "Error al subir el archivo", 400

@app.route('/usuario')
@login_required
def usuario_dashboard():
    # Verificar que sea miembro
    if session.get('user_type') != 'miembro':
        # Si es admin, redirigir al panel admin
        if session.get('user_type') == 'admin':
            return redirect('/')
        # Si no es ni miembro ni admin, cerrar sesión
        else:
            session.clear()
            return redirect('/login')

    miembro_id = session.get('user_id')
    miembro = Miembro.query.get(miembro_id)
    if not miembro:
        session.clear()
        return redirect('/login')

    # Generar QR si el pago está verificado y la membresía está activa
    qr_image = None
    if miembro.pago_verificado and miembro.estado == 'Activa':
        qr_image, qr_data = generar_codigo_qr(miembro.id, miembro.dni, miembro.nombre)
        miembro.codigo_qr = qr_data
        db.session.commit()

    return render_template_string(USUARIO_HTML, miembro=miembro, qr_image=qr_image)

@app.route('/membresias')
@admin_required
def membresias():
    admin = Administrador.query.get(session['user_id'])
    if not admin:
        return redirect('/login')
    
    miembros = Miembro.query.all()
    return render_template_string(MEMBRESIAS_HTML, miembros=miembros, admin_nombre=admin.nombre)

# ---------------------------
# RUTA NUEVA AGREGADA - VERIFICAR PAGO ESPECÍFICO
# ---------------------------

@app.route('/verificar-pago/<int:miembro_id>')
@admin_required
def verificar_pago(miembro_id):
    """Página para verificar un pago específico"""
    admin = Administrador.query.get(session['user_id'])
    if not admin:
        return redirect('/login')
    
    miembro = Miembro.query.get(miembro_id)
    if not miembro:
        return redirect('/verificar-pagos')
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Verificar Pago - Control Fit</title>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial; background: #f2f4f7; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .header {{ background: #34495e; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
            .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            .btn {{ padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }}
            .btn-success {{ background: #27ae60; color: white; }}
            .btn-danger {{ background: #e74c3c; color: white; }}
            .btn-info {{ background: #3498db; color: white; }}
            .payment-details {{ margin: 20px 0; }}
            .comprobante-img {{ max-width: 100%; max-height: 500px; border: 1px solid #ddd; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>💳 Verificar Pago</h1>
                <p>Administrador: <strong>{admin.nombre}</strong></p>
                <div>
                    <a href="/verificar-pagos" class="btn btn-info">← Volver a Pagos Pendientes</a>
                    <a href="/logout" class="btn btn-danger" style="float: right;">🚪 Cerrar Sesión</a>
                </div>
            </div>

            <div class="card">
                <h2>Detalles del Pago - {miembro.nombre} {miembro.apellidos or ''}</h2>
                
                <div class="payment-details">
                    <p><strong>Miembro:</strong> {miembro.nombre} {miembro.apellidos or ''}</p>
                    <p><strong>Email:</strong> {miembro.email}</p>
                    <p><strong>DNI:</strong> {miembro.dni or 'No registrado'}</p>
                    <p><strong>Celular:</strong> {miembro.celular or 'No registrado'}</p>
                    <p><strong>Plan Seleccionado:</strong> {miembro.plan_seleccionado or miembro.tipo_membresia or 'No especificado'}</p>
                    <p><strong>Fecha de Pago:</strong> {miembro.fecha_pago.strftime('%d/%m/%Y %H:%M') if miembro.fecha_pago else 'No registrada'}</p>
                    
                    <p><strong>Comprobante:</strong></p>
                    {f'<img src="/uploads/{miembro.comprobante_path.split("/")[-1]}" alt="Comprobante" class="comprobante-img">' if miembro.comprobante_path else '<p>No disponible</p>'}
                </div>
                
                <div style="margin-top: 30px;">
                    <h3>Acciones:</h3>
                    <a href="/aprobar-pago/{miembro.id}" class="btn btn-success" onclick="return confirm('¿Estás seguro de APROBAR este pago?')">✅ Aprobar Pago y Activar Membresía</a>
                    <a href="/rechazar-pago/{miembro.id}" class="btn btn-danger" onclick="return confirm('¿Estás seguro de RECHAZAR este pago? Se eliminará el comprobante.')">❌ Rechazar Pago</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/verificar-pagos')
@admin_required
def verificar_pagos():
    admin = Administrador.query.get(session['user_id'])
    if not admin:
        return redirect('/login')
    
    # Obtener miembros con comprobante subido pero no verificado
    pagos_pendientes = Miembro.query.filter(
        Miembro.comprobante_path.isnot(None),
        Miembro.pago_verificado == False
    ).all()
    
    return render_template_string(VERIFICAR_PAGOS_HTML, 
                                pagos_pendientes=pagos_pendientes, 
                                admin_nombre=admin.nombre)

@app.route('/aprobar-pago/<int:miembro_id>')
@admin_required
def aprobar_pago(miembro_id):
    miembro = Miembro.query.get(miembro_id)
    if miembro:
        miembro.pago_verificado = True
        miembro.estado = 'Activa'
        
        # Generar código QR
        qr_image, qr_data = generar_codigo_qr(miembro.id, miembro.dni, miembro.nombre)
        miembro.codigo_qr = qr_data
        
        db.session.commit()
        
        return f'''
        <script>
            alert("✅ Pago aprobado y QR generado exitosamente");
            window.location.href = "/verificar-pagos";
        </script>
        '''
    
    return redirect('/verificar-pagos')

@app.route('/rechazar-pago/<int:miembro_id>')
@admin_required
def rechazar_pago(miembro_id):
    miembro = Miembro.query.get(miembro_id)
    if miembro:
        # Eliminar comprobante y resetear estado
        if miembro.comprobante_path and os.path.exists(miembro.comprobante_path):
            os.remove(miembro.comprobante_path)
        
        miembro.comprobante_path = None
        miembro.pago_verificado = False
        miembro.estado = 'Inactiva'
        miembro.plan_seleccionado = None
        miembro.tipo_membresia = 'Por activar'
        
        db.session.commit()
        
        return f'''
        <script>
            alert("❌ Pago rechazado y comprobante eliminado");
            window.location.href = "/verificar-pagos";
        </script>
        '''
    
    return redirect('/verificar-pagos')

# ---------------------------
# RUTA NUEVA AGREGADA - SERVIR ARCHIVOS SUBIDOS
# ---------------------------

@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    """Servir archivos subidos desde la carpeta uploads"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# INICIALIZAR BASE DE DATOS - VERSIÓN PERSISTENTE
with app.app_context():
    try:
        # SOLO CREAR LAS TABLAS SI NO EXISTEN
        db.create_all()
        
        # Verificar si ya existe el administrador por defecto
        admin_existente = Administrador.query.filter_by(email='admin@controlfit.com').first()
        if not admin_existente:
            # Crear administrador por defecto solo si no existe
            admin_default = Administrador(
                nombre='Administrador Principal',
                email='admin@controlfit.com',
                password=hash_password('admin123')
            )
            db.session.add(admin_default)
            print("✅ Administrador por defecto creado")
        
        # Verificar si ya existe el miembro de ejemplo
        miembro_existente = Miembro.query.filter_by(email='juan@ejemplo.com').first()
        if not miembro_existente:
            # Crear miembro de ejemplo solo si no existe
            miembro_ejemplo = Miembro(
                nombre='Juan Pérez',
                apellidos='García López',
                edad=25,
                dni='12345678',
                celular='987654321',
                email='juan@ejemplo.com',
                tipo_membresia='Por activar',
                fecha_inicio=datetime.now().strftime('%Y-%m-%d'),
                fecha_fin=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
                estado='Inactiva',
                password=hash_password('clave123')
            )
            db.session.add(miembro_ejemplo)
            print("✅ Miembro de ejemplo creado")
        
        db.session.commit()
        
        # Mostrar estado de la base de datos
        total_miembros = Miembro.query.count()
        total_admins = Administrador.query.count()
        
        print("✅ BASE DE DATOS INICIALIZADA CORRECTAMENTE!")
        print(f"📊 Estado actual:")
        print(f"   👥 Miembros registrados: {total_miembros}")
        print(f"   👑 Administradores: {total_admins}")
        print("✅ Usuarios disponibles:")
        print("   👑 Admin: admin@controlfit.com / admin123")
        print("   👤 Miembro: juan@ejemplo.com / clave123")
        
    except Exception as e:
        print(f"❌ Error al inicializar la base de datos: {e}")
        db.session.rollback()

if __name__ == '__main__':
    print("=" * 60)
    print("🏋️  CONTROL FIT - SISTEMA COMPLETO CON PERSISTENCIA")
    print("=" * 60)
    print("💰 PLANES DISPONIBLES:")
    print("   📅 1 Mes: S/80.00")
    print("   📅 3 Meses: S/210.00")
    print("   📅 6 Meses: S/400.00") 
    print("   📅 1 Año: S/850.00")
    print("=" * 60)
    print("🌐 ACCESO: http://localhost:8000")
    print("💾 DATOS: Se guardarán permanentemente en la base de datos")
    print("=" * 60)
    
    try:
        app.run(host='127.0.0.1', port=8000, debug=True, use_reloader=False)
    except Exception as e:
        print(f"🔧 Usando puerto alternativo...")
        app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)