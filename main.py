import discord
import openai
import os
import asyncio
import json
import re

intents = discord.Intents.all()
client = discord.Client(intents=intents)

discord_token = os.getenv("DISCORD_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")

# ========== EXTRAE JSON GPT ==========
def extract_json(text):
    # Busca el primer bloque JSON válido y lo devuelve como dict
    try:
        matches = re.findall(r'\{[\s\S]*?\}', text)
        for match in matches:
            try:
                return json.loads(match)
            except Exception:
                continue
    except Exception as e:
        print("Error buscando JSON:", e)
    return None

# ========== FUNCIONES DISCORD ==========
async def crear_canal(guild, nombre, categoria=None):
    nombre = nombre.replace(" ", "-").lower()
    if discord.utils.get(guild.text_channels, name=nombre):
        return f"⚠️ Ya existe un canal llamado #{nombre}"
    await guild.create_text_channel(nombre)
    return f"✅ Canal creado: #{nombre}"

async def enviar_mensaje(channel, contenido):
    await channel.send(contenido)
    return "✅ Mensaje enviado."

# ========== MAPA DE ACCIONES ==========
ACTION_MAP = {
    "crear_canal": crear_canal,
    "enviar_mensaje": enviar_mensaje,
}

# ========== PROMPT PARA GPT ==========
system_prompt = """
Eres Lume, un asistente para Discord capaz de ejecutar acciones administrativas. Responde SIEMPRE SOLO con un bloque JSON que indique la acción y sus parámetros. Ejemplos:
Usuario: crea un canal ventas
Respuesta:
{
  "action": "crear_canal",
  "params": { "nombre": "ventas" }
}
Usuario: manda mensaje hola
Respuesta:
{
  "action": "enviar_mensaje",
  "params": { "contenido": "hola" }
}
Si no se entiende, responde:
{
  "action": "enviar_mensaje",
  "params": { "contenido": "Hola! ¿En qué puedo ayudarte hoy?" }
}
"""

# ========== EVENTOS DISCORD ==========
@client.event
async def on_ready():
    print(f"✅ Bot Lume conectado como {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    prompt = message.content
    history = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    try:
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=history,
            temperature=0.1
        )
        content = response.choices[0].message.content.strip()
        data = extract_json(content)

        if not data:
            await message.channel.send(f"❌ No entendí tu mensaje. Respuesta GPT: {content}")
            return

        action = data.get("action")
        params = data.get("params", {})

        if action in ACTION_MAP:
            # Llama la función adecuada con los parámetros correctos
            if action == "crear_canal":
                resultado = await ACTION_MAP[action](message.guild, **params)
            elif action == "enviar_mensaje":
                resultado = await ACTION_MAP[action](message.channel, **params)
            else:
                resultado = "⚠️ Acción reconocida pero no implementada aún."
            await message.channel.send(resultado)
        else:
            await message.channel.send(f"🤖 Acción reconocida pero no implementada: {action}")

    except Exception as e:
        print("❌ Error:", e)
        await message.channel.send(f"⚠️ Error interno del bot: {e}")

client.run(discord_token)
