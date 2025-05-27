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

# Tokens
discord_token = os.getenv("DISCORD_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Memoria contextual por canal
message_history = defaultdict(list)

def get_history(channel_id):
    return message_history[channel_id][-12:]  # Últimos 12 turnos

def add_to_history(channel_id, role, content):
    message_history[channel_id].append({"role": role, "content": content})
    if len(message_history[channel_id]) > 12:
        message_history[channel_id] = message_history[channel_id][-12:]

# Helper para extraer JSON de la respuesta de OpenAI
def extract_json(text):
    match = re.search(r'\{[\s\S]*?\}', text)
    if match:
        try:
            json.loads(match.group(0))
            return match.group(0)
        except Exception:
            return None
    return None

# ==== Funciones administrativas Discord (solo las principales para testear) ====
async def crear_canal(guild, nombre, categoria=None):
    channel_name = nombre.replace(" ", "-").lower()[:100]
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

# ==== Mapeo de acciones ====
ACTION_MAP = {
    "crear_canal": crear_canal,
    "eliminar_canal": eliminar_canal,
    "crear_categoria": crear_categoria,
    "crear_rol": crear_rol,
    "asignar_rol": asignar_rol,
    "enviar_mensaje": enviar_mensaje,
    # Aliases en inglés
    "create_channel": crear_canal,
    "delete_channel": eliminar_canal,
    "create_category": crear_categoria,
    "create_role": crear_rol,
    "assign_role": asignar_rol,
    "send_message": enviar_mensaje,
}

# ==== Prompt mejorado FULL (simple) ====
system_prompt = """
Eres Lume, el asistente virtual administrativo de este servidor de Discord. Recibes pedidos en lenguaje natural y debes responder SOLO con un bloque JSON usando uno de estos nombres de acción (en español):

- crear_canal, eliminar_canal, crear_categoria, crear_rol, asignar_rol, enviar_mensaje

Si falta un dato, pregunta amablemente cuál falta. Ejemplo:
{
  "action": "crear_canal",
  "params": {
    "nombre": "ideas-locas"
  }
}
"""

# ==== Eventos de Discord ====
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
        # OpenAI v1 API (nuevo)
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
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
                    # Soporte flexible para params (nombre/canal/categoria)
                    if action in ["crear_canal", "create_channel"]:
                        resultado = await funcion(
                            message.guild,
                            params.get("nombre") or params.get("name") or params.get("canal"),
                            params.get("categoria") or params.get("category"),
                        )
                    elif action in ["eliminar_canal", "delete_channel"]:
                        resultado = await funcion(
                            message.guild,
                            params.get("nombre") or params.get("name") or params.get("canal")
                        )
                    elif action in ["crear_categoria", "create_category"]:
                        resultado = await funcion(
                            message.guild,
                            params.get("nombre") or params.get("name")
                        )
                    elif action in ["crear_rol", "create_role"]:
                        resultado = await funcion(
                            message.guild,
                            params.get("nombre") or params.get("name")
                        )
                    elif action in ["asignar_rol", "assign_role"]:
                        resultado = await funcion(
                            message.guild,
                            params.get("usuario") or params.get("user"),
                            params.get("rol") or params.get("role"),
                        )
                    elif action in ["enviar_mensaje", "send_message"]:
                        resultado = await funcion(
                            message.guild,
                            params.get("canal") or params.get("nombre") or params.get("channel"),
                            params.get("contenido") or params.get("content"),
                        )
                    else:
                        resultado = "🤖 Acción reconocida pero no está implementada en el bot."
                else:
                    resultado = "🤖 Acción reconocida pero no está implementada en el bot."

                await message.channel.send(resultado)
                return

            except Exception as ex:
                await message.channel.send(f"⚠️ Error ejecutando el comando: {ex}")
                return

        # Si no hay JSON válido, responde conversacional
        await message.channel.send(content if content else "⚠️ No entendí el mensaje, ¿puedes explicarlo de otra forma?")
        return

    except Exception as e:
        await message.channel.send(f"⚠️ Error interno: {e}")

client.run(discord_token)

