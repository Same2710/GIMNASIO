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
import os
from datetime import datetime
from flask import request, flash, redirect, url_for
from flask import render_template_string
from datetime import datetime
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
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Pago - Control Fit Gym</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; font-family: 'Segoe UI', sans-serif; }
        .card { border-radius: 20px; box-shadow: 0 15px 40px rgba(0,0,0,0.3); }
        .opcion { background: white; border-radius: 18px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); height: 100%; }
        .upload-area { border: 3px dashed #ffc107; border-radius: 16px; padding: 40px; text-align: center; cursor: pointer; background: #fffbeb; transition: 0.3s; }
        .upload-area:hover { background: #fff3cd; border-color: #ffa500; }
        .btn-culqi { background: linear-gradient(45deg, #667eea, #764ba2); color: white; font-weight: bold; }
        .qr-img { max-height: 280px; border-radius: 15px; border: 6px solid white; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
    </style>
</head>
<body>
<div class="container my-5">
    <div class="card">
        <div class="card-header bg-primary text-white text-center py-4">
            <h2>SELECCIONA TU MÉTODO DE PAGO</h2>
            <h4>{{ plan_info.nombre }} → S/ {{ plan_info.precio }}</h4>
        </div>
        <div class="card-body p-5">
            <div class="row g-4">

                <!-- 1. YAPE / TRANSFERENCIA -->
                <div class="col-lg-4">
                    <div class="opcion text-center">
                        <h4 class="text-success mb-4">YAPE / TRANSFERENCIA</h4>
                        <img src="{{ url_for('static', filename='img/qr_pago_gimnasio.jpg') }}" class="qr-img img-fluid">
                        <p class="mt-3 fw-bold text-danger fs-3">987 654 321</p>
                        <hr>
                        <small class="text-muted">
                            Yape/Plin: 987 654 321<br>
                            BCP: 191-45678923-0-15<br>
                            Titular: GIMNASIO FITPOWER SAC
                        </small>
                    </div>
                </div>

                <!-- 2. TARJETA (CULQI) -->
<div class="col-lg-4">
    <div class="opcion">
        <h4 class="text-primary text-center mb-4">TARJETA</h4>

        <div class="text-center mb-4">
            <img src="{{url_for('static', filename='img/culqi-logo.png')}}" height="30">
            <div class="d-flex justify-content-center gap-3">
                <img src="{{ url_for('static', filename='img/visa.png') }}" height="38">
                <img src="{{ url_for('static', filename='img/mastercard.png') }}" height="38">
            </div>
        </div>

        <form id="culqi-form">

            <!-- ⭐ NÚMERO DE TARJETA -->
            <label class="form-label fw-bold">Número de Tarjeta</label>
            <div class="mb-3">
                <div id="card-number" class="form-control p-3" style="height:50px;"></div>
            </div>

            <!-- ⭐ NOMBRE DEL TITULAR -->
            <label class="form-label fw-bold">Nombre del Titular</label>
            <div class="mb-3">
                <input type="text" id="card-name" class="form-control" placeholder="Nombre del titular" required>
            </div>

            <div class="row">

                <!-- ⭐ FECHA DE VENCIMIENTO -->
                <div class="col-6">
                    <label class="form-label fw-bold">Fecha de Vencimiento</label>
                    <div id="card-expiry" class="form-control p-3" style="height:50px;"></div>
                </div>

                <!-- ⭐ CVV -->
                <div class="col-6">
                    <label class="form-label fw-bold">CVV</label>
                    <div id="card-cvv" class="form-control p-3" style="height:50px;"></div>
                </div>
            </div>

            <button type="submit" class="btn btn-culqi w-100 mt-3 py-3 fw-bold">
                PAGAR S/ {{ plan_info.precio }}
            </button>
        </form>
    </div>
</div>

                <!-- 3. SUBIR COMPROBANTE (TU DISEÑO ORIGINAL QUE TE GUSTABA) -->
                <div class="col-lg-4">
                    <div class="opcion">
                        <h4 class="text-warning text-center mb-4">SUBIR COMPROBANTE</h4>
                        <form method="POST" action="/subir-comprobante" enctype="multipart/form-data">
                            <input type="hidden" name="plan" value="{{ plan_info.tipo }}">
                            <input type="hidden" name="precio" value="{{ plan_info.precio }}">

                            <div class="upload-area" onclick="document.getElementById('comprobante').click()">
                                <div style="font-size: 60px;">Subir</div>
                                <p class="fw-bold mt-3">Haz clic para seleccionar tu comprobante</p>
                                <p style="font-size: 13px; color: #666;">JPG, PNG o PDF · Máx. 16MB</p>
                            </div>

                            <input type="file" id="comprobante" name="comprobante"
                                   accept=".jpg,.jpeg,.png,.pdf" required
                                   style="display: none;" onchange="previewFile(event)">

                            <div id="file-preview" class="text-center mt-3"></div>

                            <button type="submit" class="btn btn-warning w-100 mt-4 py-3 fw-bold text-white">
                                ENVIAR COMPROBANTE
                            </button>
                        </form>
                    </div>
                </div>

            </div>

            <div class="text-center mt-4">
                <a href="/planes" class="btn btn-outline-light btn-lg">Volver a planes</a>
            </div>
        </div>
    </div>
</div>

<script src="https://checkout.culqi.com/js/v4"></script>
<script>
Culqi.publicKey = 'pk_test_46Z9L4qO8lY2nr7v';
Culqi.settings({ title: 'Control Fit Gym', currency: 'PEN', description: '{{ plan_info.nombre }}', amount: {{ (plan_info.precio | replace(".", "") | int) * 100 }} });
Culqi.init();

window.addEventListener('load', () => {
    Culqi.createCardNumberElement(document.getElementById('card-number'));
    Culqi.createCardExpiryElement(document.getElementById('card-expiry'));
    Culqi.createCardCvvElement(document.getElementById('card-cvv'));
});

document.getElementById('culqi-form').onsubmit = e => { e.preventDefault(); Culqi.createToken(); };

function culqi() {
    if (Culqi.token) {
        fetch('/procesar-pago-culqi', { method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ token: Culqi.token.id, plan: '{{ plan_info.tipo }}', precio: '{{ plan_info.precio }}' })
        }).then(r => r.json()).then(data => {
            if (data.success) { alert('¡Pago exitoso!'); location.href = '/usuario'; }
            else { alert('Error: ' + data.error); }
        });
    } else if (Culqi.error) { alert(Culqi.error.user_message); }
}

// Vista previa del comprobante
function previewFile(event) {
    const preview = document.getElementById('file-preview');
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = () => {
            if (file.type.startsWith('image/')) {
                preview.innerHTML = `<img src="${reader.result}" style="max-width:100%; border-radius:12px; margin-top:10px; box-shadow:0 5px 15px rgba(0,0,0,0.2);">`;
            } else {
                preview.innerHTML = `<p class="text-success fw-bold mt-3">PDF listo: ${file.name}</p>`;
            }
        }
        reader.readAsDataURL(file);
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
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
    <style>
        body { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; 
            font-family: 'Segoe UI', sans-serif;
        }
        .card { 
            max-width: 740px; margin: 40px auto; 
            border: none; border-radius: 24px; 
            overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.35);
        }
        .header-profile {
            background: linear-gradient(135deg, #2c3e50, #34495e);
            color: white; padding: 35px; text-align: center;
        }
        .header-profile h2 { margin: 0; font-size: 2.2rem; }
        .info-row { 
            padding: 16px 25px; border-bottom: 1px solid #eee; 
            display: flex; justify-content: space-between; align-items: center; font-size: 1.1rem;
        }
        .label { font-weight: 600; color: #444; }
        .value { color: #2c3e50; font-weight: 500; }

        /* CUENTA REGRESIVA PREMIUM */
        .countdown-card {
            margin: 30px 25px; padding: 28px; border-radius: 20px;
            text-align: center; color: white; font-weight: bold;
            box-shadow: 0 12px 35px rgba(0,0,0,0.25);
        }
        .countdown-ok     { background: linear-gradient(135deg, #56ab2f, #a8e063); }
        .countdown-alert  { background: linear-gradient(135deg, #f39c12, #f1c40f); color: #2c3e50; }
        .countdown-danger { background: linear-gradient(135deg, #e74c3c, #c0392b); }
        .countdown-card h3 { margin: 0 0 12px 0; font-size: 1.5rem; opacity: 0.95; }
        .countdown-card .time { font-size: 4rem; margin: 0; letter-spacing: 4px; }

        .qr-section { background: #f8f9fa; padding: 35px; border-radius: 20px; margin: 30px 25px; text-align: center; }
        .qr-image { 
            max-width: 260px; max-height: 260px; padding: 15px; background: white; 
            border-radius: 20px; box-shadow: 0 15px 40px rgba(0,0,0,0.2);
        }

        .btn-renovar {
            display: block; width: 88%; margin: 25px auto; padding: 18px;
            background: linear-gradient(135deg, #27ae60, #2ecc71);
            color: white; font-weight: bold; font-size: 1.3rem; border-radius: 16px;
            text-align: center; text-decoration: none; box-shadow: 0 10px 25px rgba(39,174,96,0.4);
            transition: all 0.3s;
        }
        .btn-renovar:hover { transform: translateY(-4px); box-shadow: 0 15px 30px rgba(39,174,96,0.5); }
    </style>
</head>
<body>
    <div class="card">
        <div class="header-profile">
            <h2><i class="fas fa-user-circle fa-2x"></i> Perfil del Socio</h2>
            <p class="mt-2 fs-3">¡Hola, <strong>{{ miembro.nombre }} {{ miembro.apellidos or '' }}</strong>!</p>
        </div>

        <div class="container-fluid px-4 py-3">
            <div class="info-row"><span class="label"><i class="fas fa-envelope"></i> Email</span><span class="value">{{ miembro.email }}</span></div>
            <div class="info-row"><span class="label"><i class="fas fa-id-card"></i> DNI</span><span class="value">{{ miembro.dni or '-' }}</span></div>
            <div class="info-row"><span class="label"><i class="fas fa-phone"></i> Celular</span><span class="value">{{ miembro.celular or '-' }}</span></div>
            <div class="info-row"><span class="label"><i class="fas fa-dumbbell"></i> Plan</span><span class="value fw-bold text-primary">{{ miembro.tipo_membresia or 'Sin plan' }}</span></div>
            <div class="info-row"><span class="label"><i class="fas fa-calendar-check"></i> Inicio</span><span class="value">{{ miembro.fecha_inicio or '-' }}</span></div>
            <div class="info-row"><span class="label"><i class="fas fa-calendar-times text-danger"></i> Vence</span><span class="value fw-bold text-danger">{{ miembro.fecha_fin or '-' }}</span></div>
            <div class="info-row"><span class="label"><i class="fas fa-money-check-alt"></i> Pago</span>
                <span class="value">
                    {% if miembro.pago_verificado %}    <span class="text-success fw-bold"><i class="fas fa-check-circle"></i> VERIFICADO</span>
                    {% elif miembro.comprobante_path %} <span class="text-warning fw-bold"><i class="fas fa-clock"></i> EN REVISIÓN</span>
                    {% else %}                          <span class="text-danger fw-bold"><i class="fas fa-times-circle"></i> PENDIENTE</span>
                    {% endif %}
                </span>
            </div>
            <div class="info-row"><span class="label"><i class="fas fa-running"></i> Estado</span>
                <span class="value fw-bold" style="color: {{ 'green' if miembro.estado == 'Activa' else '#e74c3c' }};">
                    {{ miembro.estado or 'Inactiva' }}
                </span>
            </div>

            <!-- CUENTA REGRESIVA -->
            {{ countdown | safe }}

            <!-- QR -->
            {% if miembro.pago_verificado and miembro.estado == 'Activa' %}
            <div class="qr-section">
                <h3 class="mb-4"><i class="fas fa-qrcode fa-2x"></i><br>Tu Código QR de Acceso</h3>
                {% if qr_image %}
                    <img src="{{ qr_image }}" class="qr-image" alt="QR">
                {% else %}
                    <div style="width:260px;height:260px;background:#ddd;margin:0 auto;border-radius:20px;display:flex;align-items:center;justify-content:center;color:#666;font-size:1.2rem;">
                        QR NO GENERADO
                    </div>
                {% endif %}
                <p class="mt-3 text-muted">Muéstralo en recepción para entrar</p>
            </div>
            {% endif %}

            <!-- BOTÓN RENOVAR SIEMPRE VISIBLE -->
            <a href="/planes" class="btn-renovar">
                RENOVAR O CAMBIAR MI PLAN
            </a>

            <a href="/logout" class="btn btn-outline-light d-block w-88 mx-auto mb-4 text-center px-4 py-3 rounded-pill">
                <i class="fas fa-sign-out-alt"></i> Cerrar sesión
            </a>
        </div>
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
                        <th>Días Restantes</th>
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
        {% if miembro.fecha_fin %}
            {% set dias = (miembro.fecha_fin - now).days %}

            {% if dias > 5 %}
                <span class="text-success fw-bold">{{ dias }} días</span>
            {% elif dias >= 1 %}
                <span class="text-warning fw-bold">{{ dias }} días</span>
            {% elif dias == 0 %}
                <span class="text-danger fw-bold">Hoy vence</span>
            {% else %}
                <span class="text-danger fw-bold">Vencido</span>
            {% endif %}
        {% else %}
            <span class="text-muted">—</span>
        {% endif %}
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

                        <strong>Comprobante:</strong><br>
                        {% if pago.comprobante_path %}
                            {% set filename = pago.comprobante_path %}
                            <a href="{{ url_for('serve_uploaded_file', filename=filename) }}" target="_blank">
                                <img src="{{ url_for('serve_uploaded_file', filename=filename) }}" 
                                     alt="Comprobante de {{ pago.nombre }}" 
                                     class="comprobante-img"
                                     style="max-width: 300px; border-radius: 10px; border: 3px solid #ffc107;
                                            box-shadow: 0 5px 20px rgba(0,0,0,0.3); cursor: zoom-in;">
                            </a>
                            <br><small class="text-success">Click en la imagen para verla grande</small>
                        {% else %}
                            <span class="text-muted">No disponible</span>
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
        return "No se seleccionó archivo", 400
    
    file = request.files['comprobante']
    if file.filename == '':
        return "No se seleccionó archivo", 400
    
    if file:
        # NOMBRE LIMPIO
        filename = secure_filename(
            f"{session['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        )

        # RUTA COMPLETA DONDE SE GUARDARÁ
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # GUARDAR ARCHIVO EN /uploads/
        file.save(upload_path)

        # GUARDAR SOLO EL NOMBRE EN LA BD (NO LA RUTA COMPLETA)
        miembro = Miembro.query.get(session['user_id'])
        miembro.comprobante_path = filename     # ← IMPORTANTE
        miembro.pago_verificado = False
        miembro.fecha_pago = datetime.now()
        miembro.estado = 'Pendiente'

        db.session.commit()
        return redirect('/usuario')

    return "Error inesperado", 500


    # Si es GET, mostrar el formulario
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Subir Comprobante</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background: linear-gradient(135deg, #667eea, #764ba2); min-height: 100vh; display: flex; align-items: center; }
            .card { max-width: 500px; margin: 0 auto; border-radius: 20px; }
        </style>
    </head>
    <body>
    <div class="container">
        <div class="card shadow">
            <div class="card-body p-5">
                <h2 class="text-center mb-4">Subir Comprobante</h2>
                <form method="post" enctype="multipart/form-data">
                    <input type="hidden" name="plan" value="Membresía Mensual">
                    <input type="hidden" name="precio" value="99.90">
                    
                    <div class="mb-4 text-center">
                        <div class="border border-3 border-dashed rounded-4 p-5 bg-light">
                            <i class="fas fa-cloud-upload-alt fa-4x text-muted mb-3"></i>
                            <p class="fw-bold">Haz clic para subir tu comprobante</p>
                            <input type="file" name="comprobante" accept="image/*,.pdf" required 
                                   class="form-control form-control-lg" style="margin-top: 15px;">
                        </div>
                    </div>
                    
                    <button type="submit" class="btn btn-success btn-lg w-100">
                        ENVIAR COMPROBANTE
                    </button>
                    <a href="/planes" class="btn btn-outline-secondary w-100 mt-2">Volver</a>
                </form>
            </div>
        </div>
    </div>
    </body>
    </html>
    '''

@app.route('/usuario')
@login_required
def usuario_dashboard():
    # Verificar que sea miembro
    if session.get('user_type') != 'miembro':
        if session.get('user_type') == 'admin':
            return redirect('/')
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

    # ==================== CUENTA REGRESIVA TIPO RELOJ ====================
    from datetime import datetime, timedelta

    countdown_html = '<div class="text-center my-4"><small class="text-muted">Sin membresía activa</small></div>'

    if miembro.fecha_fin and miembro.estado == 'Activa':
        try:
            fecha_fin_dt = datetime.strptime(miembro.fecha_fin, '%Y-%m-%d')
            ahora = datetime.now()
            diferencia = fecha_fin_dt - ahora

            if diferencia.total_seconds() > 0:
                dias = diferencia.days
                horas, resto = divmod(diferencia.seconds, 3600)
                minutos, _ = divmod(resto, 60)

                if dias > 0:
                    countdown_html = f'''
                    <div class="text-center my-4 p-4 bg-light rounded shadow">
                        <h5 class="text-success mb-3">Tu membresía vence en:</h5>
                        <h1 class="display-4 fw-bold text-success">{dias} <small class="fs-3">días</small></h1>
                    </div>
                    '''
                else:
                    countdown_html = f'''
                    <div class="text-center my-4 p-4 bg-warning rounded shadow">
                        <h5 class="text-dark mb-3">¡Vence en menos de 24 horas!</h5>
                        <h1 class="display-4 fw-bold text-dark">{horas}h {minutos}m</h1>
                    </div>
                    '''
            else:
                # Ya venció
                dias_vencidos = abs(diferencia.days)
                countdown_html = f'''
                <div class="text-center my-4 p-4 bg-danger text-white rounded shadow">
                    <h5 class="mb-3">Membresía vencida</h5>
                    <h1 class="display-4 fw-bold">Hace {dias_vencidos} día{"s" if dias_vencidos != 1 else ""}</h1>
                </div>
                '''
                # Opcional: marcar como vencida automáticamente
                if miembro.estado == 'Activa':
                    miembro.estado = 'Vencida'
                    db.session.commit()

        except Exception as e:
            countdown_html = '<div class="text-center text-danger">Error en fecha</div>'
    # =====================================================================

    return render_template_string(USUARIO_HTML, miembro=miembro, qr_image=qr_image, countdown=countdown_html)
from datetime import datetime

@app.route('/membresias')
@admin_required
def membresias():
    admin = Administrador.query.get(session['user_id'])
    if not admin:
        return redirect('/login')

    miembros = Miembro.query.all()

    # 🔥 CONVERTIR fecha_fin A datetime SI ES STRING
    for m in miembros:
        if isinstance(m.fecha_fin, str):
            try:
                # intentamos el formato más común YYYY-MM-DD
                m.fecha_fin = datetime.strptime(m.fecha_fin, "%Y-%m-%d")
            except:
                try:
                    # formato DD/MM/YYYY
                    m.fecha_fin = datetime.strptime(m.fecha_fin, "%d/%m/%Y")
                except:
                    # si no se puede convertir → dejamos None
                    m.fecha_fin = None

    return render_template_string(
        MEMBRESIAS_HTML,
        miembros=miembros,
        admin_nombre=admin.nombre,
        now=datetime.now()   # requerido para días restantes
    )


@app.route('/verificar-pago/<int:miembro_id>')
@admin_required
def verificar_pago(miembro_id):
    admin = Administrador.query.get(session['user_id'])
    if not admin:
        return redirect('/login')
    
    miembro = Miembro.query.get(miembro_id)
    if not miembro:
        return redirect('/verificar-pagos')
    
    # Extraemos solo el nombre del archivo de forma segura
    comprobante_filename = None
    if miembro.comprobante_path:
        comprobante_filename = miembro.comprobante_path.split('\\')[-1].split('/')[-1]

    HTML_VERIFICAR_PAGO = '''
<!DOCTYPE html>
<html lang="es">
<head>
    <title>Verificar Pago - Control Fit</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; font-family: 'Segoe UI', sans-serif; }
        .card { max-width: 900px; margin: 40px auto; border-radius: 20px; overflow: hidden; box-shadow: 0 20px 50px rgba(0,0,0,0.4); }
        .header { background: linear-gradient(135deg, #2c3e50, #34495e); color: white; padding: 30px; text-align: center; }
        .comprobante-img { max-width: 100%; max-height: 650px; border-radius: 16px; border: 6px solid #ffc107; box-shadow: 0 15px 40px rgba(0,0,0,0.4); transition: transform 0.3s; }
        .comprobante-img:hover { transform: scale(1.02); }
        .info-box { background: #f8f9fa; padding: 20px; border-radius: 12px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>Verificar Pago</h1>
            <p class="fs-4">Administrador: <strong>{{ admin_nombre }}</strong></p>
            <div class="mt-3">
                <a href="/verificar-pagos" class="btn btn-light btn-lg">Volver a Pendientes</a>
                <a href="/logout" class="btn btn-outline-light btn-lg">Cerrar Sesión</a>
            </div>
        </div>

        <div class="card-body p-5 bg-white">
            <h2 class="text-center text-primary mb-4">{{ miembro.nombre }} {{ miembro.apellidos or '' }}</h2>

            <div class="row text-center mb-4 info-box">
                <div class="col-md-4"><strong>Email:</strong> {{ miembro.email }}</div>
                <div class="col-md-4"><strong>DNI:</strong> {{ miembro.dni or '—' }}</div>
                <div class="col-md-4"><strong>Celular:</strong> {{ miembro.celular or '—' }}</div>
            </div>

            <div class="text-center mb-4">
                <h4>Plan seleccionado:</h4>
                <h3 class="text-success fw-bold">{{ miembro.plan_seleccionado or miembro.tipo_membresia or 'No especificado' }}</h3>
                <p class="text-muted">
                    Fecha: {{ miembro.fecha_pago.strftime('%d/%m/%Y a las %H:%M') if miembro.fecha_pago else 'No registrada' }}
                </p>
            </div>

            <hr class="my-5">

            <h3 class="text-center mb-4">Comprobante de Pago</h3>
            <div class="text-center">
                {% if comprobante_filename %}
                    <a href="{{ url_for('serve_uploaded_file', filename=comprobante_filename) }}" target="_blank">
                        <img src="{{ url_for('serve_uploaded_file', filename=comprobante_filename) }}" 
                             alt="Comprobante" class="comprobante-img">
                    </a>
                    <div class="mt-4">
                        <p class="text-success fw-bold fs-4">Click en la imagen para verla en tamaño completo</p>
                    </div>
                {% else %}
                    <div class="alert alert-danger fs-4">No se ha subido ningún comprobante</div>
                {% endif %}
            </div>

            <div class="text-center mt-5">
                <h3>Acciones</h3>

                <!-- SIN CONFIRMACIONES -->
                <a href="/aprobar-pago/{{ miembro.id }}" 
                   class="btn btn-success btn-lg px-5 py-3 me-4">Aprobar y Activar</a>

                <a href="/rechazar-pago/{{ miembro.id }}" 
                   class="btn btn-danger btn-lg px-5 py-3">Rechazar</a>
            </div>
        </div>
    </div>
</body>
</html>
'''


    return render_template_string(
        HTML_VERIFICAR_PAGO,
        admin_nombre=admin.nombre,
        miembro=miembro,
        comprobante_filename=comprobante_filename
    )
    

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
    
    return render_template_string(
        VERIFICAR_PAGOS_HTML,
        pagos_pendientes=pagos_pendientes, 
        admin_nombre=admin.nombre,
        url_for=url_for,          # ← obligatorio cuando usas render_template_string
        request=request           # ← opcional pero recomendado
    )

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

    return redirect('/verificar-pagos')

@app.route('/rechazar-pago/<int:miembro_id>')
@admin_required
def rechazar_pago(miembro_id):
    miembro = Miembro.query.get(miembro_id)
    if miembro:

        # Eliminar archivo del comprobante
        if miembro.comprobante_path:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], miembro.comprobante_path)
            if os.path.exists(file_path):
                os.remove(file_path)

        miembro.comprobante_path = None
        miembro.pago_verificado = False
        miembro.estado = 'Inactiva'
        miembro.plan_seleccionado = None
        miembro.tipo_membresia = 'Por activar'

        db.session.commit()

    return redirect('/verificar-pagos')

# ---------------------------
# RUTA NUEVA AGREGADA - SERVIR ARCHIVOS SUBIDOS
# ---------------------------

# ===========================================
# RUTA PARA VER COMPROBANTES - 100% FUNCIONAL
# ===========================================
@app.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
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


@app.route('/procesar-pago-culqi', methods=['POST'])
@login_required
def procesar_pago_culqi():
    if session.get('user_type') != 'miembro':
        return jsonify({'success': False, 'error': 'No autorizado'})

    data = request.get_json()
    token = data['token']
    precio = float(data['precio'].replace('S/', '').strip())

    payload = {
        "amount": int(precio * 100),
        "currency_code": "PEN",
        "email": data['email'],
        "source_id": token
    }

    headers = {
        
    }

    try:
        response = requests.post("https://api.culqi.com/v2/charges", json=payload, headers=headers)
        result = response.json()

        if response.status_code == 201:
            # PAGO EXITOSO → ACTIVAR MEMBRESÍA AUTOMÁTICAMENTE
            miembro = Miembro.query.get(session['user_id'])
            plan_info = {
                '1_mes': ('Mensual', 30),
                '3_meses': ('Trimestral', 90),
                '6_meses': ('Semestral', 180),
                '1_anio': ('Anual', 365)
            }
            nombre_plan, dias = plan_info.get(data['plan'], ('Mensual', 30))
            miembro.tipo_membresia = nombre_plan
            miembro.estado = 'Activa'
            miembro.pago_verificado = True
            miembro.fecha_inicio = datetime.now().strftime('%Y-%m-%d')
            miembro.fecha_fin = (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d')
            qr_image, qr_data = generar_codigo_qr(miembro.id, miembro.dni, miembro.nombre)
            miembro.codigo_qr = qr_data
            db.session.commit()

            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': result.get('user_message', 'Error en el pago')})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
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
