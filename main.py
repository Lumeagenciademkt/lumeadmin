import discord
import openai
import os
import asyncio
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict

intents = discord.Intents.all()
client = discord.Client(intents=intents)

discord_token = os.getenv("DISCORD_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")

# ==== Memoria contextual por canal ====
message_history = defaultdict(list)

def get_history(channel_id):
    return message_history[channel_id][-12:]  # Últimos 12 turnos

def add_to_history(channel_id, role, content):
    message_history[channel_id].append({"role": role, "content": content})
    if len(message_history[channel_id]) > 12:
        message_history[channel_id] = message_history[channel_id][-12:]

# ==== Helper para extraer JSON ====
def extract_json(text):
    # Busca el primer bloque JSON en la respuesta
    match = re.search(r'\{[\s\S]*?\}', text)
    if match:
        try:
            json.loads(match.group(0))
            return match.group(0)
        except Exception as e:
            print("Error decoding JSON:", e)
            return None
    return None

# ==== Funciones administrativas Discord ====
async def crear_canal(guild, nombre, categoria=None):
    channel_name = nombre.replace(" ", "-")[:100]
    if discord.utils.get(guild.text_channels, name=channel_name):
        return f"⚠️ Ya existe un canal llamado #{channel_name}"
    category = None
    if categoria:
        category = discord.utils.get(guild.categories, name=categoria)
    await guild.create_text_channel(channel_name, category=category)
    return f"✅ Canal creado: #{channel_name}"

async def eliminar_canal(guild, nombre):
    canal = discord.utils.get(guild.text_channels, name=nombre.replace(" ", "-").lower())
    if canal:
        await canal.delete()
        return f"🗑️ Canal eliminado: #{nombre}"
    return f"❌ No encontré el canal #{nombre}"

async def renombrar_canal(guild, canal_actual, canal_nuevo):
    canal = discord.utils.get(guild.text_channels, name=canal_actual.replace(" ", "-").lower())
    if canal:
        await canal.edit(name=canal_nuevo.replace(" ", "-"))
        return f"✏️ Canal renombrado a #{canal_nuevo}"
    return f"❌ No encontré el canal #{canal_actual}"

async def mover_canal(guild, nombre, categoria):
    canal = discord.utils.get(guild.text_channels, name=nombre.replace(" ", "-").lower())
    categoria_obj = discord.utils.get(guild.categories, name=categoria)
    if canal and categoria_obj:
        await canal.edit(category=categoria_obj)
        return f"🚚 Canal movido a categoría {categoria}"
    return f"❌ No encontré el canal o categoría"

async def crear_categoria(guild, nombre):
    if discord.utils.get(guild.categories, name=nombre):
        return f"⚠️ Ya existe la categoría {nombre}"
    await guild.create_category(nombre)
    return f"📂 Categoría creada: {nombre}"

async def eliminar_categoria(guild, nombre):
    cat = discord.utils.get(guild.categories, name=nombre)
    if cat:
        await cat.delete()
        return f"🗑️ Categoría eliminada: {nombre}"
    return f"❌ No encontré la categoría {nombre}"

async def renombrar_categoria(guild, actual, nuevo):
    cat = discord.utils.get(guild.categories, name=actual)
    if cat:
        await cat.edit(name=nuevo)
        return f"✏️ Categoría renombrada a {nuevo}"
    return f"❌ No encontré la categoría {actual}"

async def crear_rol(guild, nombre, color=None):
    if discord.utils.get(guild.roles, name=nombre):
        return f"⚠️ Ya existe el rol {nombre}"
    await guild.create_role(name=nombre)
    return f"👤 Rol creado: {nombre}"

async def eliminar_rol(guild, nombre):
    rol = discord.utils.get(guild.roles, name=nombre)
    if rol:
        await rol.delete()
        return f"🗑️ Rol eliminado: {nombre}"
    return f"❌ No encontré el rol {nombre}"

async def renombrar_rol(guild, actual, nuevo):
    rol = discord.utils.get(guild.roles, name=actual)
    if rol:
        await rol.edit(name=nuevo)
        return f"✏️ Rol renombrado a {nuevo}"
    return f"❌ No encontré el rol {actual}"

async def asignar_rol(guild, usuario, rol_nombre):
    miembro = discord.utils.find(lambda m: usuario in [m.name, m.display_name, m.mention], guild.members)
    rol = discord.utils.get(guild.roles, name=rol_nombre)
    if miembro and rol:
        await miembro.add_roles(rol)
        return f"🎭 Rol '{rol_nombre}' asignado a {miembro.mention}"
    return "❌ Usuario o rol no encontrado."

async def quitar_rol(guild, usuario, rol_nombre):
    miembro = discord.utils.find(lambda m: usuario in [m.name, m.display_name, m.mention], guild.members)
    rol = discord.utils.get(guild.roles, name=rol_nombre)
    if miembro and rol:
        await miembro.remove_roles(rol)
        return f"🎭 Rol '{rol_nombre}' quitado de {miembro.mention}"
    return "❌ Usuario o rol no encontrado."

async def modificar_permisos_canal(guild, canal_nombre, rol_nombre, permisos_dict):
    canal = discord.utils.get(guild.text_channels, name=canal_nombre.replace(" ", "-").lower())
    rol = discord.utils.get(guild.roles, name=rol_nombre)
    if canal and rol:
        overwrite = canal.overwrites_for(rol)
        for k, v in permisos_dict.items():
            setattr(overwrite, k, v)
        await canal.set_permissions(rol, overwrite=overwrite)
        return f"🔒 Permisos modificados para {rol_nombre} en #{canal_nombre}"
    return "❌ No se encontró el canal o el rol."

async def enviar_mensaje(guild, canal_nombre, contenido):
    canal = discord.utils.get(guild.text_channels, name=canal_nombre.replace(" ", "-").lower())
    if canal:
        await canal.send(contenido)
        return f"📨 Mensaje enviado a #{canal_nombre}"
    return f"❌ No encontré el canal #{canal_nombre}"

async def pinar_mensaje(message_id, canal):
    try:
        msg = await canal.fetch_message(int(message_id))
        await msg.pin()
        return "📌 Mensaje pineado."
    except Exception as e:
        return f"❌ No se pudo pinear el mensaje: {e}"

async def despinar_mensaje(message_id, canal):
    try:
        msg = await canal.fetch_message(int(message_id))
        await msg.unpin()
        return "📍 Mensaje despineado."
    except Exception as e:
        return f"❌ No se pudo despinear el mensaje: {e}"

async def cambiar_nombre_servidor(guild, nuevo_nombre):
    await guild.edit(name=nuevo_nombre)
    return f"🏷️ Servidor renombrado a: {nuevo_nombre}"

async def cambiar_icono_servidor(guild, url_icono):
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url_icono) as resp:
                if resp.status != 200:
                    return "❌ No se pudo descargar el icono."
                data = await resp.read()
        await guild.edit(icon=data)
        return "🖼️ Icono del servidor actualizado."
    except Exception as e:
        return f"❌ No se pudo actualizar el icono: {e}"

async def programar_recordatorio(message, segundos, contenido):
    await message.channel.send(f"⏳ Te recordaré eso en {segundos} segundos.")
    await asyncio.sleep(int(segundos))
    await message.channel.send(f"🔔 Recordatorio: {contenido}")

async def crear_evento(guild, nombre, descripcion, inicio, canal_nombre):
    canal = discord.utils.get(guild.voice_channels, name=canal_nombre.replace(" ", "-").lower())
    if not canal:
        canal = discord.utils.get(guild.text_channels, name=canal_nombre.replace(" ", "-").lower())
    if canal:
        try:
            start_time = datetime.strptime(inicio, "%Y-%m-%d %H:%M")
            event = await guild.create_scheduled_event(
                name=nombre,
                start_time=start_time,
                channel=canal,
                description=descripcion,
                entity_type=discord.EntityType.voice if isinstance(canal, discord.VoiceChannel) else discord.EntityType.external
            )
            return f"📅 Evento '{nombre}' creado para el {inicio}."
        except Exception as e:
            return f"❌ Error creando el evento: {e}"
    return f"❌ No encontré el canal {canal_nombre}"

async def eliminar_evento(guild, nombre):
    event = discord.utils.find(lambda e: e.name == nombre, await guild.fetch_scheduled_events())
    if event:
        await event.delete()
        return f"🗑️ Evento eliminado: {nombre}"
    return f"❌ No se encontró el evento."

# ==== Mapeador de acciones (español e inglés) ====
ACTION_MAP = {
    "crear_canal": crear_canal,
    "eliminar_canal": eliminar_canal,
    "renombrar_canal": renombrar_canal,
    "mover_canal": mover_canal,
    "crear_categoria": crear_categoria,
    "eliminar_categoria": eliminar_categoria,
    "renombrar_categoria": renombrar_categoria,
    "crear_rol": crear_rol,
    "eliminar_rol": eliminar_rol,
    "renombrar_rol": renombrar_rol,
    "asignar_rol": asignar_rol,
    "quitar_rol": quitar_rol,
    "modificar_permisos_canal": modificar_permisos_canal,
    "enviar_mensaje": enviar_mensaje,
    "pinar_mensaje": pinar_mensaje,
    "despinar_mensaje": despinar_mensaje,
    "cambiar_nombre_servidor": cambiar_nombre_servidor,
    "cambiar_icono_servidor": cambiar_icono_servidor,
    "programar_recordatorio": programar_recordatorio,
    "crear_evento": crear_evento,
    "eliminar_evento": eliminar_evento,
    # Aliases
    "create_channel": crear_canal,
    "delete_channel": eliminar_canal,
    "rename_channel": renombrar_canal,
    "move_channel": mover_canal,
    "create_category": crear_categoria,
    "delete_category": eliminar_categoria,
    "rename_category": renombrar_categoria,
    "create_role": crear_rol,
    "delete_role": eliminar_rol,
    "rename_role": renombrar_rol,
    "assign_role": asignar_rol,
    "remove_role": quitar_rol,
    "modify_channel_permissions": modificar_permisos_canal,
    "send_message": enviar_mensaje,
    "pin_message": pinar_mensaje,
    "unpin_message": despinar_mensaje,
    "change_server_name": cambiar_nombre_servidor,
    "change_server_icon": cambiar_icono_servidor,
    "set_reminder": programar_recordatorio,
    "create_event": crear_evento,
    "delete_event": eliminar_evento,
}

# ==== Prompt mejorado FULL ====
system_prompt = """
Eres Lume, el asistente virtual con acceso total a todas las funciones administrativas, organizativas y colaborativas de este servidor de Discord. 
Tu misión es interpretar cualquier petición, incluso si está escrita en lenguaje coloquial, natural, joven, profesional, ambigua o indirecta, y ejecutarla usando las funciones del bot.

**Instrucciones importantes:**
1. Siempre responde con un bloque JSON usando estos nombres de acción en español SIEMPRE (aunque el usuario lo pida en inglés o de manera informal):
    - crear_canal, eliminar_canal, renombrar_canal, mover_canal
    - crear_categoria, eliminar_categoria, renombrar_categoria
    - crear_rol, eliminar_rol, renombrar_rol, asignar_rol, quitar_rol
    - modificar_permisos_canal
    - enviar_mensaje
    - programar_recordatorio
    - crear_evento, eliminar_evento
    - pinar_mensaje, despinar_mensaje
    - cambiar_nombre_servidor, cambiar_icono_servidor
2. Si falta algún dato clave para ejecutar la acción (nombre, usuario, fecha, canal, etc.), pregunta solo por ese dato de forma amable, breve y jovial, y espera respuesta antes de continuar.
3. Si la petición es trivial o conversación general, responde conversacionalmente.
4. No expliques el bloque JSON, solo genera el bloque limpio.
5. Hazlo lo más natural y accesible posible: actúa como un asistente amigable, proactivo y jovial.

**Ejemplos:**
- Usuario: “Hazme un canal para ideas locas”
  Responde: 
  {
    "action": "crear_canal",
    "params": {
      "nombre": "ideas-locas"
    }
  }
- Usuario: “Dale el rol ‘Moderador’ a Renzo”
  Responde:
  {
    "action": "asignar_rol",
    "params": {
      "usuario": "Renzo",
      "rol": "Moderador"
    }
  }
- Usuario: “Manda un mensaje a general: Bienvenidos”
  Responde:
  {
    "action": "enviar_mensaje",
    "params": {
      "canal": "general",
      "contenido": "Bienvenidos"
    }
  }
Si el usuario dice: “Hazme un canal para ventas” pero no especifica nombre, pregunta: “¿Qué nombre quieres ponerle al canal?”
"""

# ==== Discord Events ====

@client.event
async def on_ready():
    print(f"✅ Lume está conectado como {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    channel_id = str(message.channel.id)
    user_prompt = message.content

    add_to_history(channel_id, "user", user_prompt)
    history = [{"role": "system", "content": system_prompt}] + get_history(channel_id)

    try:
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=history,
            temperature=0.2
        )
        content = response.choices[0].message.content.strip()
        print("🔎 GPT:", content)

        add_to_history(channel_id, "assistant", content)
        json_block = extract_json(content)
        if json_block:
            try:
                data = json.loads(json_block)
                action = data.get("action")
                params = data.get("params", {})
                funcion = ACTION_MAP.get(action)

                resultado = None
                if funcion:
                    # Despacho dinámico (ajusta según parámetros de cada función)
                    if action in ["crear_canal", "create_channel"]:
                        resultado = await funcion(message.guild, params.get("nombre"), params.get("categoria"))
                    elif action in ["eliminar_canal", "delete_channel"]:
                        resultado = await funcion(message.guild, params.get("nombre"))
                    elif action in ["renombrar_canal", "rename_channel"]:
                        resultado = await funcion(message.guild, params.get("actual"), params.get("nuevo"))
                    elif action in ["mover_canal", "move_channel"]:
                        resultado = await funcion(message.guild, params.get("nombre"), params.get("categoria"))
                    elif action in ["crear_categoria", "create_category"]:
                        resultado = await funcion(message.guild, params.get("nombre"))
                    elif action in ["eliminar_categoria", "delete_category"]:
                        resultado = await funcion(message.guild, params.get("nombre"))
                    elif action in ["renombrar_categoria", "rename_category"]:
                        resultado = await funcion(message.guild, params.get("actual"), params.get("nuevo"))
                    elif action in ["crear_rol", "create_role"]:
                        resultado = await funcion(message.guild, params.get("nombre"))
                    elif action in ["eliminar_rol", "delete_role"]:
                        resultado = await funcion(message.guild, params.get("nombre"))
                    elif action in ["renombrar_rol", "rename_role"]:
                        resultado = await funcion(message.guild, params.get("actual"), params.get("nuevo"))
                    elif action in ["asignar_rol", "assign_role"]:
                        resultado = await funcion(message.guild, params.get("usuario"), params.get("rol"))
                    elif action in ["quitar_rol", "remove_role"]:
                        resultado = await funcion(message.guild, params.get("usuario"), params.get("rol"))
                    elif action in ["modificar_permisos_canal", "modify_channel_permissions"]:
                        resultado = await funcion(message.guild, params.get("canal"), params.get("rol"), params.get("permisos", {}))
                    elif action in ["enviar_mensaje", "send_message"]:
                        resultado = await funcion(message.guild, params.get("canal"), params.get("contenido"))
                    elif action in ["pinar_mensaje", "pin_message"]:
                        canal = discord.utils.get(message.guild.text_channels, name=params.get("canal", "").replace(" ", "-").lower())
                        resultado = await funcion(params.get("id"), canal)
                    elif action in ["despinar_mensaje", "unpin_message"]:
                        canal = discord.utils.get(message.guild.text_channels, name=params.get("canal", "").replace(" ", "-").lower())
                        resultado = await funcion(params.get("id"), canal)
                    elif action in ["cambiar_nombre_servidor", "change_server_name"]:
                        resultado = await funcion(message.guild, params.get("nombre"))
                    elif action in ["cambiar_icono_servidor", "change_server_icon"]:
                        resultado = await funcion(message.guild, params.get("url"))
                    elif action in ["programar_recordatorio", "set_reminder"]:
                        await funcion(message, params.get("segundos", 60), params.get("contenido", ""))
                        return
                    elif action in ["crear_evento", "create_event"]:
                        resultado = await funcion(
                            message.guild, params.get("nombre"),
                            params.get("descripcion"), params.get("inicio"), params.get("canal")
                        )
                    elif action in ["eliminar_evento", "delete_event"]:
                        resultado = await funcion(message.guild, params.get("nombre"))
                    else:
                        resultado = "🔔 Acción reconocida, pero aún no implementada."
                else:
                    resultado = "🤖 Acción reconocida pero no está implementada en el bot."

                await message.channel.send(resultado)
                return

            except Exception as ex:
                print("❌ Error ejecutando acción:", ex)
                await message.channel.send(f"⚠️ Error ejecutando el comando: {ex}")
                return

        # Si no hay JSON: es charla, saludo o GPT pide info faltante
        await message.channel.send(content if content else "⚠️ No entendí el mensaje, ¿puedes explicarlo de otra forma?")
        return

    except Exception as e:
        print("❌ Error general:", e)
        await message.channel.send(f"⚠️ Error interno: {e}")

client.run(discord_token)
