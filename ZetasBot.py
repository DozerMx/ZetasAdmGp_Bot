import asyncio
import os
import json
from datetime import datetime, timedelta
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import wikipedia
import subprocess

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuración de Wikipedia en español
wikipedia.set_lang("es")

# Diccionario para almacenar datos del grupo
group_data = {
    'welcome_message': 'Bienvenido al grupo!',
    'goodbye_message': 'Hasta pronto!',
    'rules': 'No hay reglas establecidas.',
    'warned_users': {}
}

# Funciones de gestión de datos
def save_data():
    with open('group_data.json', 'w', encoding='utf-8') as f:
        json.dump(group_data, f, ensure_ascii=False)

def load_data():
    global group_data
    try:
        with open('group_data.json', 'r', encoding='utf-8') as f:
            group_data = json.load(f)
    except FileNotFoundError:
        save_data()

# Función para crear el menú principal
def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📋 Ver Todos los Comandos", callback_data='show_all_commands')],
        [InlineKeyboardButton("ℹ️ Información", callback_data='show_info')],
        [InlineKeyboardButton("📖 Reglas", callback_data='show_rules_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "¡Hola! 👋 Soy ZetasBot, tu asistente de grupo multifunción.\n\n"
        "Puedo ayudarte con:\n"
        "• Administración del grupo 🛡️\n"
        "• Descargas de YouTube 📱\n"
        "• Búsquedas en Wikipedia 🔍\n"
        "• Y mucho más!\n\n"
        "Selecciona una opción para comenzar:"
    )
    await update.message.reply_text(
        welcome_message,
        reply_markup=get_main_menu_keyboard()
    )

# Manejador de callbacks para los botones
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    logger.info(f"Callback recibido: {query.data}")

    if query.data == 'show_all_commands':
        commands = """
📋 Todos los Comandos Disponibles:

🛡️ Comandos de Administración:
/ban - Banear usuario
/unban - Desbanear usuario
/mute - Silenciar usuario
/unmute - Quitar silencio
/warn - Advertir usuario
/unwarn - Quitar advertencia
/setwelcome - Configurar mensaje de bienvenida
/setgoodbye - Configurar mensaje de despedida
/setrules - Configurar reglas

📱 Comandos Multimedia:
/yt_video [URL] - Descargar video de YouTube
/yt_audio [URL] - Descargar audio de YouTube

🔧 Utilidades:
/tag_all - Mencionar a todos los usuarios
/wikipedia [término] - Buscar en Wikipedia
/rules - Ver reglas del grupo

Nota: Los comandos de administración solo pueden ser usados por administradores
"""
        keyboard = [[InlineKeyboardButton("⬅️ Volver al Menú Principal", callback_data='back_to_main')]]
        try:
            await query.edit_message_text(
                text=commands,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error al mostrar comandos: {str(e)}")
            await query.answer("Hubo un error al mostrar los comandos. Por favor, intenta de nuevo.")
    elif query.data == 'back_to_main':
        await query.edit_message_text(
            "📱 *Menú Principal*\n\nSelecciona una opción:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    elif query.data == 'show_info':
        info_text = """
*ℹ️ Información del Bot*

Este bot fue creado para ayudar en la gestión de grupos de Telegram, proporcionando herramientas útiles para administradores y usuarios.

*Características principales:*
• Gestión de usuarios
• Sistema de advertencias
• Descargas multimedia
• Utilidades de grupo
• Y más...

_Para empezar, usa el comando /start_
"""
        keyboard = [[InlineKeyboardButton("⬅️ Volver al Menú Principal", callback_data='back_to_main')]]
        await query.edit_message_text(
            info_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    elif query.data == 'show_rules_menu':
        rules_text = f"""
*📖 Reglas del Grupo*

{group_data['rules']}

_Los administradores pueden cambiar las reglas usando /setrules_
"""
        keyboard = [[InlineKeyboardButton("⬅️ Volver al Menú Principal", callback_data='back_to_main')]]
        await query.edit_message_text(
            rules_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        logger.warning(f"Callback no reconocido: {query.data}")
        await query.edit_message_text(
            f"Lo siento, no pude procesar tu solicitud. Botón presionado: {query.data}",
            reply_markup=get_main_menu_keyboard()
        )

# Funciones de administración
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        return
    
    try:
        user_to_ban = update.message.reply_to_message.from_user
        await context.bot.ban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_to_ban.id
        )
        await update.message.reply_text(f"Usuario {user_to_ban.first_name} ha sido baneado.")
    except Exception as e:
        await update.message.reply_text(f"Error al banear usuario: {str(e)}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        return
    
    try:
        user_to_unban = update.message.reply_to_message.from_user
        await context.bot.unban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_to_unban.id
        )
        await update.message.reply_text(f"Usuario {user_to_unban.first_name} ha sido desbaneado.")
    except Exception as e:
        await update.message.reply_text(f"Error al desbanear usuario: {str(e)}")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        return
    
    try:
        user_to_mute = update.message.reply_to_message.from_user
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_to_mute.id,
            permissions={"can_send_messages": False}
        )
        await update.message.reply_text(f"Usuario {user_to_mute.first_name} ha sido silenciado.")
    except Exception as e:
        await update.message.reply_text(f"Error al silenciar usuario: {str(e)}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        return
    
    try:
        user_to_unmute = update.message.reply_to_message.from_user
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_to_unmute.id,
            permissions={
                "can_send_messages": True,
                "can_send_media_messages": True,
                "can_send_other_messages": True,
                "can_add_web_page_previews": True
            }
        )
        await update.message.reply_text(f"Usuario {user_to_unmute.first_name} ya no está silenciado.")
    except Exception as e:
        await update.message.reply_text(f"Error al quitar silencio: {str(e)}")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        return
    
    try:
        user_to_warn = update.message.reply_to_message.from_user
        user_id = str(user_to_warn.id)
        
        if user_id not in group_data['warned_users']:
            group_data['warned_users'][user_id] = 1
        else:
            group_data['warned_users'][user_id] += 1
        
        save_data()
        
        warn_count = group_data['warned_users'][user_id]
        await update.message.reply_text(
            f"⚠️ {user_to_warn.first_name} ha sido advertido.\n"
            f"Advertencias: {warn_count}/3"
        )
        
        if warn_count >= 3:
            await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=user_to_warn.id
            )
            await update.message.reply_text(
                f"Usuario {user_to_warn.first_name} ha sido baneado por acumular 3 advertencias."
            )
            del group_data['warned_users'][user_id]
            save_data()
            
    except Exception as e:
        await update.message.reply_text(f"Error al advertir usuario: {str(e)}")

async def unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        return
    
    try:
        user_to_unwarn = update.message.reply_to_message.from_user
        user_id = str(user_to_unwarn.id)
        
        if user_id in group_data['warned_users']:
            group_data['warned_users'][user_id] -= 1
            if group_data['warned_users'][user_id] <= 0:
                del group_data['warned_users'][user_id]
            save_data()
            
            remaining_warns = group_data['warned_users'].get(user_id, 0)
            await update.message.reply_text(
                f"Se ha quitado una advertencia a {user_to_unwarn.first_name}.\n"
                f"Advertencias restantes: {remaining_warns}"
            )
        else:
            await update.message.reply_text(
                f"{user_to_unwarn.first_name} no tiene advertencias."
            )
            
    except Exception as e:
        await update.message.reply_text(f"Error al quitar advertencia: {str(e)}")

# Funciones multimedia
async def download_yt_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Por favor, proporciona el enlace del video de YouTube.")
        return

    try:
        url = context.args[0]
        await update.message.reply_text("⏳ Descargando video...")
        
        # Usar yt-dlp para descargar el video
        result = subprocess.run(['yt-dlp', '-f', 'best[ext=mp4]', '-o', '%(title)s.%(ext)s', url], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Buscar el archivo descargado
            video_file = next((f for f in os.listdir() if f.endswith('.mp4')), None)
            if video_file:
                with open(video_file, 'rb') as video:
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id,
                        video=video,
                        caption=f"📹 {video_file}"
                    )
                os.remove(video_file)
            else:
                await update.message.reply_text("No se pudo encontrar el archivo de video descargado.")
        else:
            await update.message.reply_text(f"Error al descargar el video: {result.stderr}")
        
    except Exception as e:
        await update.message.reply_text(f"Error al descargar el video: {str(e)}")

async def download_yt_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Por favor, proporciona el enlace del video de YouTube.")
        return

    try:
        url = context.args[0]
        await update.message.reply_text("⏳ Descargando audio...")
        
        # Usar yt-dlp para extraer el audio
        result = subprocess.run(['yt-dlp', '-x', '--audio-format', 'mp3', '-o', '%(title)s.%(ext)s', url], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Buscar el archivo descargado
            audio_file = next((f for f in os.listdir() if f.endswith('.mp3')), None)
            if audio_file:
                with open(audio_file, 'rb') as audio:
                    await context.bot.send_audio(
                        chat_id=update.effective_chat.id,
                        audio=audio,
                        caption=f"🎵 {audio_file}"
                    )
                os.remove(audio_file)
            else:
                await update.message.reply_text("No se pudo encontrar el archivo de audio descargado.")
        else:
            await update.message.reply_text(f"Error al descargar el audio: {result.stderr}")
        
    except Exception as e:
        await update.message.reply_text(f"Error al  descargar el audio: {str(e)}")

# Funciones de configuración
async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        return
    
    if not context.args:
        await update.message.reply_text("Por favor, proporciona un mensaje de bienvenida.")
        return
    
    group_data['welcome_message'] = ' '.join(context.args)
    save_data()
    await update.message.reply_text("Mensaje de bienvenida actualizado.")

async def set_goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        return
    
    if not context.args:
        await update.message.reply_text("Por favor, proporciona un mensaje de despedida.")
        return
    
    group_data['goodbye_message'] = ' '.join(context.args)
    save_data()
    await update.message.reply_text("Mensaje de despedida actualizado.")

async def set_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        return
    
    if not context.args:
        await update.message.reply_text("Por favor, proporciona las reglas del grupo.")
        return
    
    group_data['rules'] = ' '.join(context.args)
    save_data()
    await update.message.reply_text("Reglas actualizadas.")

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"*Reglas del grupo:*\n\n{group_data['rules']}",
        parse_mode=ParseMode.MARKDOWN
    )

# Funciones de utilidad
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        return
    
    try:
        chat_id = update.effective_chat.id
        members = []
        
        # Obtener administradores
        admins = await context.bot.get_chat_administrators(chat_id)
        for admin in admins:
            if not admin.user.is_bot:
                members.append(f"[{admin.user.first_name}](tg://user?id={admin.user.id})")
        
        # Obtener número total de miembros
        member_count = await context.bot.get_chat_member_count(chat_id)
        
        if members:
            # Dividir la lista de miembros en grupos de 5 para evitar límites de mensaje
            chunk_size = 5
            for i in range(0, len(members), chunk_size):
                chunk = members[i:i + chunk_size]
                message = (
                    "🔔 *Atención:*\n\n" + 
                    "\n".join(chunk) +
                    f"\n\n*Total de miembros en el grupo: {member_count}*"
                )
                await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("No se encontraron miembros para mencionar.")
            
    except Exception as e:
        await update.message.reply_text(f"Error al mencionar usuarios: {str(e)}")

async def search_wikipedia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Por favor, proporciona un término de búsqueda.")
        return
    
    try:
        search_term = ' '.join(context.args)
        result = wikipedia.summary(search_term, sentences=3)
        await update.message.reply_text(f"*Resultado de Wikipedia:*\n\n{result}", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"Error en la búsqueda: {str(e)}")

# Funciones de eventos
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_member in update.message.new_chat_members:
        if not new_member.is_bot:
            await update.message.reply_text(
                f"{group_data['welcome_message']}\n"
                f"¡Bienvenido/a {new_member.first_name}!"
            )

async def goodbye_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    left_member = update.message.left_chat_member
    if not left_member.is_bot:
        await update.message.reply_text(
            f"{group_data['goodbye_message']}\n"
            f"¡Hasta pronto {left_member.first_name}!"
        )

# Función auxiliar para verificar si el usuario es administrador
async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        is_admin = member.status in ['administrator', 'creator']
        
        if not is_admin:
            await update.message.reply_text(
                "❌ Este comando solo puede ser usado por administradores."
            )
        
        return is_admin
    except Exception as e:
        await update.message.reply_text(f"Error al verificar permisos: {str(e)}")
        return False

def main():
    # Configurar el bot
    token = "7875246449:AAGMHVJOc2_z1fPjyu9j_vxaOYSnr-XwgOM"
    
    # Crear la aplicación
    application = Application.builder().token(token).build()
    
    # Registrar comando start y callback de botones
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Registrar comandos de administración
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("unmute", unmute))
    application.add_handler(CommandHandler("warn", warn))
    application.add_handler(CommandHandler("unwarn", unwarn))
    
    # Registrar comandos multimedia
    application.add_handler(CommandHandler("yt_video", download_yt_video))
    application.add_handler(CommandHandler("yt_audio", download_yt_audio))
    
    # Registrar utilidades
    application.add_handler(CommandHandler("tag_all", tag_all))
    application.add_handler(CommandHandler("wikipedia", search_wikipedia))
    
    # Registrar comandos de configuración
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CommandHandler("setgoodbye", set_goodbye))
    application.add_handler(CommandHandler("setrules", set_rules))
    application.add_handler(CommandHandler("rules", show_rules))
    
    # Registrar manejadores de eventos
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_member))
    
    # Cargar datos guardados
    load_data()
    
    return application

if __name__ == '__main__':
    try:
        # Crear y ejecutar el bot
        print("Iniciando bot...")
        app = main()
        print("Bot iniciado. Presiona Ctrl+C para detener.")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\nBot detenido.")
    except Exception as e:
        print(f"Error: {e}")