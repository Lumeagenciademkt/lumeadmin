import discord
import openai
import os
import asyncio
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict

# Intents y cliente Discord
intents = discord.Intents.all()
client = discord.Client(intents=intents)

# API KEYS
discord_token = os.getenv("DISCORD_TOKEN")
openai_api_key = os.getenv("OPENAI_API_KEY")
client_openai = openai.OpenAI(api_key=openai_api_key)

# ==== Memoria contextual por canal ====
message_history = defaultdict(list)

def get_history(channel_id):
    return message_history[channel_id][-12:]

def add_to_history(channel_id, role, content):
    message_history[channel_id].append({"role": role, "content": content})
    if len(message_history[channel_id]) > 12:
        message_history[channel_id] = message_history[channel_id][-12:]

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

# ==== Funciones administrativas Discord (las más usadas) ====
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

async def crear_categoria(guild, nombre):
    if discord.utils.get(guild.categories, name=nombre):
        return f"⚠️ Ya existe la categoría {nombre}"
    await guild.create_category(nombre)
    return f"📂 Categoría creada: {nombre}"

async def crear_rol(guild, nombre):
    if discord.utils.get(guild.roles, name=nombre):
        return f"⚠️ Ya existe el rol {nombre}"
    await guild.create_role(name=nombre)
    return f"👤 Rol creado: {nombre}"

async def asignar_rol(guild, usuario, rol_nombre):
    miembro = discord.utils.find(lambda m: usuario in [m.name, m.display_name, m.mention], guild.members)
    rol = discord.utils.get(guild.roles, name=rol_nombre)
    if miembro and rol:
        await miembro.add_roles(rol)
        return f"🎭 Rol '{rol_nombre}' asignado a {miembro.mention}"
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
    "crear_categoria": crear_categoria,
    "crear_rol": crear_rol,
    "asignar_rol": asignar_rol,
    "enviar_mensaje": enviar_mensaje,
}

# ==== Prompt FULL optimizado ====
system_prompt = """
Eres Lume, el asistente virtual con acceso total a todas las funciones administrativas de este servidor de Discord. 
Siempre responde con un bloque JSON usando estos nombres de acción en español: crear_canal, eliminar_canal, crear_categoria, crear_rol, asignar_rol, enviar_mensaje.
Si falta algún dato clave para ejecutar la acción, pregunta solo por ese dato de forma breve y jovial y espera respuesta antes de continuar.
Si la petición es trivial o conversación general, responde conversacionalmente.
No expliques el bloque JSON, solo genera el bloque limpio.
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

    print("🔴 Mensaje recibido:", user_prompt)

    add_to_history(channel_id, "user", user_prompt)
    history = [{"role": "system", "content": system_prompt}] + get_history(channel_id)

    try:
        response = client_openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=history,
            temperature=0.2
        )
        content = response.choices[0].message.content.strip()
        print("🟠 Respuesta GPT:", content)

        add_to_history(channel_id, "assistant", content)
        json_block = extract_json(content)
        print("🟡 JSON extraído:", json_block)

        if json_block:
            try:
                data = json.loads(json_block)
                action = data.get("action")
                params = data.get("params", {})
                print("🟢 Acción:", action)
                print("🟢 Params:", params)
                funcion = ACTION_MAP.get(action)
                resultado = None
                if funcion:
                    if action == "crear_canal":
                        resultado = await funcion(message.guild, params.get("nombre"), params.get("categoria"))
                    elif action == "eliminar_canal":
                        resultado = await funcion(message.guild, params.get("nombre"))
                    elif action == "crear_categoria":
                        resultado = await funcion(message.guild, params.get("nombre"))
                    elif action == "crear_rol":
                        resultado = await funcion(message.guild, params.get("nombre"))
                    elif action == "asignar_rol":
                        resultado = await funcion(message.guild, params.get("usuario"), params.get("rol"))
                    elif action == "enviar_mensaje":
                        resultado = await funcion(message.guild, params.get("canal"), params.get("contenido"))
                    else:
                        resultado = "🔔 Acción reconocida, pero aún no implementada."
                else:
                    resultado = "🤖 Acción reconocida pero no está implementada en el bot."

                await message.channel.send(resultado)
                print("🟣 Resultado enviado:", resultado)
                return

            except Exception as ex:
                print("❌ Error ejecutando acción:", ex)
                await message.channel.send(f"⚠️ Error ejecutando el comando: {ex}")
                return

        await message.channel.send(content if content else "⚠️ No entendí el mensaje, ¿puedes explicarlo de otra forma?")
        print("🔵 Mensaje no ejecutado, solo respuesta GPT.")
        return

    except Exception as e:
        print("❌ Error general:", e)
        await message.channel.send(f"⚠️ Error interno: {e}")

client.run(discord_token)

