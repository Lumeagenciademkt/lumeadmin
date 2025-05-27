import discord
import os
import json
import re
from collections import defaultdict

intents = discord.Intents.all()
client = discord.Client(intents=intents)

discord_token = os.getenv("DISCORD_TOKEN")

# ==== Memoria contextual por canal ====
message_history = defaultdict(list)

def get_history(channel_id):
    return message_history[channel_id][-8:]  # Últimos 8 turnos para que no explote

def add_to_history(channel_id, role, content):
    message_history[channel_id].append({"role": role, "content": content})
    if len(message_history[channel_id]) > 8:
        message_history[channel_id] = message_history[channel_id][-8:]

# ==== Helper para extraer JSON ====
def extract_json(text):
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
    category = discord.utils.get(guild.categories, name=categoria) if categoria else None
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

async def crear_rol(guild, nombre):
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

async def enviar_mensaje(guild, canal_nombre, contenido):
    canal = discord.utils.get(guild.text_channels, name=canal_nombre.replace(" ", "-").lower())
    if canal:
        await canal.send(contenido)
        return f"📨 Mensaje enviado a #{canal_nombre}"
    return f"❌ No encontré el canal #{canal_nombre}"

# ==== Mapeador de acciones ====
ACTION_MAP = {
    "crear_canal": crear_canal,
    "eliminar_canal": eliminar_canal,
    "renombrar_canal": renombrar_canal,
    "crear_categoria": crear_categoria,
    "eliminar_categoria": eliminar_categoria,
    "crear_rol": crear_rol,
    "eliminar_rol": eliminar_rol,
    "asignar_rol": asignar_rol,
    "quitar_rol": quitar_rol,
    "enviar_mensaje": enviar_mensaje,
    # Aliases inglés
    "create_channel": crear_canal,
    "delete_channel": eliminar_canal,
    "rename_channel": renombrar_canal,
    "create_category": crear_categoria,
    "delete_category": eliminar_categoria,
    "create_role": crear_rol,
    "delete_role": eliminar_rol,
    "assign_role": asignar_rol,
    "remove_role": quitar_rol,
    "send_message": enviar_mensaje,
}

# ==== Prompt sencillo para pruebas ====
system_prompt = """
Eres Lume, un asistente virtual administrativo para Discord. Puedes crear, eliminar o renombrar canales, categorías y roles, asignar o quitar roles y enviar mensajes. Solo responde con un bloque JSON (sin explicación), usando los siguientes nombres de acción:
crear_canal, eliminar_canal, renombrar_canal, crear_categoria, eliminar_categoria, crear_rol, eliminar_rol, asignar_rol, quitar_rol, enviar_mensaje.
Si falta algún dato, pide ese dato de forma breve y amigable.
"""

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

    # Prueba con OpenAI GPT-3.5 si quieres ahorrar tokens (puedes cambiar a gpt-4-turbo si quieres)
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=history,
        temperature=0.2
    )
    content = response.choices[0].message.content.strip()

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
                # Cada acción requiere params distintos
                if action in ["crear_canal", "create_channel"]:
                    resultado = await funcion(message.guild, params.get("nombre"), params.get("categoria"))
                elif action in ["eliminar_canal", "delete_channel"]:
                    resultado = await funcion(message.guild, params.get("nombre"))
                elif action in ["renombrar_canal", "rename_channel"]:
                    resultado = await funcion(message.guild, params.get("actual"), params.get("nuevo"))
                elif action in ["crear_categoria", "create_category"]:
                    resultado = await funcion(message.guild, params.get("nombre"))
                elif action in ["eliminar_categoria", "delete_category"]:
                    resultado = await funcion(message.guild, params.get("nombre"))
                elif action in ["crear_rol", "create_role"]:
                    resultado = await funcion(message.guild, params.get("nombre"))
                elif action in ["eliminar_rol", "delete_role"]:
                    resultado = await funcion(message.guild, params.get("nombre"))
                elif action in ["asignar_rol", "assign_role"]:
                    resultado = await funcion(message.guild, params.get("usuario"), params.get("rol"))
                elif action in ["quitar_rol", "remove_role"]:
                    resultado = await funcion(message.guild, params.get("usuario"), params.get("rol"))
                elif action in ["enviar_mensaje", "send_message"]:
                    resultado = await funcion(message.guild, params.get("canal"), params.get("contenido"))
                else:
                    resultado = "🔔 Acción reconocida, pero aún no implementada."
            else:
                resultado = "🤖 Acción reconocida pero no está implementada en el bot."
            await message.channel.send(resultado)
            return
        except Exception as ex:
            await message.channel.send(f"⚠️ Error ejecutando el comando: {ex}")
            return

    await message.channel.send(content if content else "⚠️ No entendí el mensaje, ¿puedes explicarlo de otra forma?")

client.run(discord_token)

