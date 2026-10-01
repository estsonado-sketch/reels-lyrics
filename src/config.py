import os

# ---- Video ----
MAX_SECONDS = 25.0          # duración máxima del reel
W, H, FPS = 1080, 1920, 60
BG_SECONDS = 0.50           # duración de cada foto de fondo
ZOOM = 1.0                  # zoom fijo inicial sobre las fotos (1.0 = sin zoom fijo)
ZOOM_END = 1.58             # zoom animado: el fondo se acerca de 1.0 a este valor durante el video
DARKEN = 0.09               # 1.0 = sin oscurecer, menor = más oscuro
PURPLE = (120, 50, 210)     # color del filtro
PURPLE_AMOUNT = 0.16        # intensidad del filtro púrpura (leve)
FLIP = "all"                # "alternate": foto normal y luego volteada | "all": todas volteadas | "none"

# ---- Texto ----
# Opciones (todas están en /fonts):
#   "Jost Bold Italic"        -> estilo Futura Bold Italic (Futura es de pago; Jost es la alternativa libre)
#   "Barlow Condensed Black"  -> extra condensada black cursiva (ver LYRIC_ITALIC)
#   "Bebas Neue"              -> la anterior
FONT_NAME = "Jost Bold Italic"
LYRIC_ITALIC = 0            # 0 si el archivo ya es cursiva; 1 para inclinar una fuente recta
LYRIC_SIZE = 64
LYRIC_Y = 930               # centro de la letra (pantalla = 1920 de alto)
MAX_CHARS_LINE = 18         # máx. de caracteres por línea de letra
WATERMARK_FONT = "Bebas Neue"   # la marca de agua se queda como estaba
WATERMARK = "ESTÁ SONANDO"
WATERMARK_SIZE = 40
WATERMARK_Y = 1000          # debajo de la letra

# ---- Whisper (transcripción gratis en el runner) ----
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3")   # small < medium < large-v3 (más preciso, más lento)

# ---- Publicación ----
GRAPH_VERSION = os.getenv("GRAPH_VERSION", "v25.0")
SLOTS_UTC = [(20, 0), (23, 0)]  # 17:00 y 20:00 de Uruguay (UTC-3)
MAX_WAIT_MIN = 40

HASHTAGS = [
    "#musica", "#canciones", "#letrasdecanciones", "#paradedicar",
    "#rolitasparadedicar", "#rolitas", "#indirectasmuydirectas",
    "#IndirectaDirecta", "#paraestados", "#indirectas", "#indirectasdeamor",
    "#rolitas30segundos", "#musicaparastatus", "#rolas",
]
