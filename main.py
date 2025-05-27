import discord
import openai
import os
import asyncio
import json

intents = discord.Intents.all()
client = discord.Client(intents=intents)

discord_token = os.getenv("DISCORD_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Funciones administrativas
async def crear_canal(guild, nombre):
    nombre = nombre.replace(" ", "-").lower()
    existente = discord.utils.get(guild.text_channels, name=nombre)
    if not existente:
        await guild.create_text_channel(nombre)
        return f"✅ Canal creado: #{nombre}"
    return f"⚠️ Ya existe el canal #{nombre}"

async def eliminar_canal(guild, nombre):
    nombre = nombre.replace(" ", "-").lower()
    canal = discord.utils.get(guild.text_channels, name=nombre)
    if canal:
        await canal.delete()
        return f"🗑️ Canal eliminado: #{nombre}"
    return f"❌ No encontré el canal #{nombre}"

async def enviar_mensaje(guild, canal_nombre, contenido):
    canal_nombre = canal_nombre.replace(" ", "-").lower()
    canal = discord.utils.get(guild.text_channels, name=canal_nombre)
    if canal:
        await canal.send(contenido)
        return f"📨 Mensaje enviado a #{canal_nombre}"
    return f"❌ No encontré el canal #{canal_nombre}"

async def crear_categoria(guild, nombre):
    existente = discord.utils.get(guild.categories, name=nombre)
    if not existente:
        await guild.create_category(nombre)
        return f"📂 Categoría creada: {nombre}"
    return f"⚠️ Ya existe la categoría {nombre}"

async def asignar_rol(guild, miembro_nombre, rol_nombre):
    miembro = discord.utils.get(guild.members, name=miembro_nombre)
    rol = discord.utils.get(guild.roles, name=rol_nombre)
    if miembro and rol:
        await miembro.add_roles(rol)
        return f"🎭 Rol '{rol_nombre}' asignado a {miembro.mention}"
    return "❌ Usuario o rol no encontrado."

async def programar_recordatorio(message, segundos, contenido):
    await message.channel.send(f"⏳ Te recordaré eso en {segundos} segundos.")
    await asyncio.sleep(segundos)
    await message.channel.send(f"🔔 Recordatorio: {contenido}")

@client.event
async def on_ready():
    print(f"✅ Lume está conectado como {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    user_prompt = message.content
    guild = message.guild

    system_prompt = """
Eres Lume, un asistente virtual con permisos administrativos en este servidor. Si el usuario da una orden clara relacionada a Discord, responde en formato JSON con:
{
  "action": "nombre_funcion",
  "params": {
    "param1": "valor1"
  }
}
Si no es una orden o no estás seguro, responde normalmente como asistente conversacional.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content.strip()

        # Intentar decodificar JSON si es un comando
        try:
            data = json.loads(content)
            action = data.get("action")
            params = data.get("params", {})

            resultado = ""
            if action == "crear_canal":
                resultado = await crear_canal(guild, params.get("nombre", "sin-nombre"))
            elif action == "eliminar_canal":
                resultado = await eliminar_canal(guild, params.get("nombre", ""))
            elif action == "enviar_mensaje":
                resultado = await enviar_mensaje(guild, params.get("canal", ""), params.get("contenido", ""))
            elif action == "crear_categoria":
                resultado = await crear_categoria(guild, params.get("nombre", ""))
            elif action == "asignar_rol":
                resultado = await asignar_rol(guild, params.get("usuario", ""), params.get("rol", ""))
            elif action == "recordatorio":
                await programar_recordatorio(message, int(params.get("segundos", 60)), params.get("contenido", ""))
                return
            else:
                resultado = "⚠️ Comando no reconocido."

            await message.channel.send(resultado)

        except json.JSONDecodeError:
            # No es un comando, solo responder como asistente
            await message.channel.send(content)

    except Exception as e:
        print("❌ Error general:", e)
        await message.channel.send("⚠️ Hubo un error interno. Intenta de nuevo.")

client.run(discord_token)
