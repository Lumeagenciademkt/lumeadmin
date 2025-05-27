import discord
import openai
import os
import asyncio
import json
import re
from datetime import datetime, timedelta

intents = discord.Intents.all()
client = discord.Client(intents=intents)

discord_token = os.getenv("DISCORD_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Helper para extraer JSON
def extract_json(text):
    match = re.search(r'\{[\s\S]*?\}', text)
    if match:
        try:
            json.loads(match.group(0))
            return match.group(0)
        except:
            return None
    return None

# === ACCIONES ADMINISTRATIVAS ===

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
    except:
        return "❌ No se pudo pinear el mensaje."

async def despin_mensaje(message_id, canal):
    try:
        msg = await canal.fetch_message(int(message_id))
        await msg.unpin()
        return "📍 Mensaje despineado."
    except:
        return "❌ No se pudo despinear el mensaje."

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

# === SYSTEM PROMPT UNIVERSAL Y ROBUSTO ===

system_prompt = """
Eres Lume, un asistente virtual con acceso ilimitado a TODAS las herramientas administrativas, colaborativas y de organización de este servidor de Discord. 
Tu misión es entender cualquier petición, aunque esté en lenguaje natural, coloquial, joven, profesional, ambigua o indirecta, y transformarla en la acción administrativa más adecuada.

Tus capacidades incluyen, pero no se limitan a:
- Crear, eliminar, renombrar y mover canales y categorías.
- Crear, eliminar, renombrar y asignar roles.
- Modificar permisos de canales, roles y usuarios.
- Asignar o quitar roles y responsabilidades.
- Crear, completar, asignar y eliminar tareas o recordatorios.
- Agendar y eliminar eventos y notificaciones.
- Pinar/despinar mensajes.
- Enviar mensajes, notificaciones y avisos.
- Cambiar nombre, icono y configuración general del servidor.
- Organizar flujos, tareas, calendarios y permisos avanzados.
- TODO lo posible en Discord para admins.

INSTRUCCIONES:
1. Interpreta siempre la intención, aunque sea vaga o imprecisa. Si te falta algún dato (nombre, usuario, fecha, canal, etc), pregunta SOLO eso y espera respuesta.
2. Si tienes todo lo necesario, responde ÚNICAMENTE en JSON, así:
{
  "action": "nombre_funcion",
  "params": {
    "param1": "valor1",
    "param2": "valor2"
  }
}
3. Si el mensaje es trivial, saludo o conversación casual, responde de forma conversacional.
4. Sé amable, jovial y colaborativo siempre.

EJEMPLOS:
- "Haz un canal para ideas locas" → JSON para crear canal llamado ideas-locas.
- "Haz que solo ventas vea este canal" → Si tienes canal y rol, ejecuta; si no, pregunta.
- "Ponme un recordatorio mañana a las 3 de la reunión" → JSON para recordatorio, pide fecha si no está clara.
- "Agrega el rol 'staff' a María" → JSON para asignar rol.
- "Pina este mensaje" → JSON para pinar con id de mensaje.
"""

# === EVENTOS DISCORD ===

@client.event
async def on_ready():
    print(f"✅ Lume está conectado como {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    user_prompt = message.content
    guild = message.guild

    try:
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2
        )
        content = response.choices[0].message.content.strip()
        print("🔎 GPT:", content)

        json_block = extract_json(content)
        if json_block:
            try:
                data = json.loads(json_block)
                action = data.get("action")
                params = data.get("params", {})

                # === Despacho centralizado de ACCIONES ===
                resultado = "Acción ejecutada."

                if action == "crear_canal":
                    resultado = await crear_canal(guild, params.get("nombre"), params.get("categoria"))
                elif action == "eliminar_canal":
                    resultado = await eliminar_canal(guild, params.get("nombre"))
                elif action == "renombrar_canal":
                    resultado = await renombrar_canal(guild, params.get("actual"), params.get("nuevo"))
                elif action == "mover_canal":
                    resultado = await mover_canal(guild, params.get("nombre"), params.get("categoria"))
                elif action == "crear_categoria":
                    resultado = await crear_categoria(guild, params.get("nombre"))
                elif action == "eliminar_categoria":
                    resultado = await eliminar_categoria(guild, params.get("nombre"))
                elif action == "renombrar_categoria":
                    resultado = await renombrar_categoria(guild, params.get("actual"), params.get("nuevo"))
                elif action == "crear_rol":
                    resultado = await crear_rol(guild, params.get("nombre"))
                elif action == "eliminar_rol":
                    resultado = await eliminar_rol(guild, params.get("nombre"))
                elif action == "renombrar_rol":
                    resultado = await renombrar_rol(guild, params.get("actual"), params.get("nuevo"))
                elif action == "asignar_rol":
                    resultado = await asignar_rol(guild, params.get("usuario"), params.get("rol"))
                elif action == "quitar_rol":
                    resultado = await quitar_rol(guild, params.get("usuario"), params.get("rol"))
                elif action == "modificar_permisos_canal":
                    resultado = await modificar_permisos_canal(guild, params.get("canal"), params.get("rol"), params.get("permisos", {}))
                elif action == "enviar_mensaje":
                    resultado = await enviar_mensaje(guild, params.get("canal"), params.get("contenido"))
                elif action == "pinar_mensaje":
                    canal = discord.utils.get(guild.text_channels, name=params.get("canal", "").replace(" ", "-").lower())
                    resultado = await pinar_mensaje(params.get("id"), canal)
                elif action == "despinar_mensaje":
                    canal = discord.utils.get(guild.text_channels, name=params.get("canal", "").replace(" ", "-").lower())
                    resultado = await despin_mensaje(params.get("id"), canal)
                elif action == "cambiar_nombre_servidor":
                    resultado = await cambiar_nombre_servidor(guild, params.get("nombre"))
                elif action == "cambiar_icono_servidor":
                    resultado = await cambiar_icono_servidor(guild, params.get("url"))
                elif action == "recordatorio":
                    await programar_recordatorio(message, params.get("segundos", 60), params.get("contenido", ""))
                    return
                elif action == "crear_evento":
                    resultado = await crear_evento(guild, params.get("nombre"), params.get("descripcion"), params.get("inicio"), params.get("canal"))
                elif action == "eliminar_evento":
                    resultado = await eliminar_evento(guild, params.get("nombre"))
                else:
                    resultado = "🤖 Acción reconocida pero aún no implementada."

                await message.channel.send(resultado)
                return

            except Exception as ex:
                print("❌ Error ejecutando JSON:", ex)
                await message.channel.send(f"⚠️ Error ejecutando comando: {ex}")
                return

        # Conversación casual o pregunta por dato faltante
        await message.channel.send(content if content else "⚠️ No entendí el mensaje. ¿Puedes explicarme mejor?")
        return

    except Exception as e:
        print("❌ Error general:", e)
        await message.channel.send(f"⚠️ Error interno: {e}")

client.run(discord_token)

