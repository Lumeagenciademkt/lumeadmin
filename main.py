import discord
import openai
import os
import asyncio
import json

intents = discord.Intents.all()
client = discord.Client(intents=intents)

discord_token = os.getenv("DISCORD_TOKEN")
openai.api_key = os.getenv("OPENAI_API_KEY")

async def crear_canal(guild, nombre):
    channel_name = nombre.replace(" ", "-")[:100]
    existing = discord.utils.get(guild.text_channels, name=channel_name)
    if not existing:
        await guild.create_text_channel(channel_name)
        return f"✅ Canal creado: #{channel_name}"
    return f"⚠️ Ya existe un canal llamado #{channel_name}"

async def eliminar_canal(guild, nombre):
    canal = discord.utils.get(guild.text_channels, name=nombre.replace(" ", "-").lower())
    if canal:
        await canal.delete()
        return f"🗑️ Canal eliminado: #{nombre}"
    return f"❌ No encontré el canal #{nombre}"

async def enviar_mensaje(guild, canal_nombre, contenido):
    canal = discord.utils.get(guild.text_channels, name=canal_nombre.replace(" ", "-").lower())
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
    miembro = discord.utils.find(lambda m: m.name == miembro_nombre or m.display_name == miembro_nombre, guild.members)
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
Eres Lume, un asistente virtual con acceso total al servidor de Discord. Tu función es interpretar comandos de lenguaje natural y transformarlos en acciones dentro del servidor. Si la acción es clara, responde únicamente en JSON con el formato:
{
  "action": "nombre_funcion",
  "params": {
    "param1": "valor1",
    "param2": "valor2"
  }
}
Si es una conversación trivial o cultural, responde de forma conversacional.
"""

    try:
        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content.strip()

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
                resultado = "🤖 Aún no sé cómo hacer eso, pero estoy aprendiendo."

            await message.channel.send(resultado)

        except json.JSONDecodeError:
            if content:
                await message.channel.send(content)
            else:
                await message.channel.send("⚠️ No entendí el mensaje. ¿Puedes reformularlo?")

    except Exception as e:
        print("❌ Error:", e)
        await message.channel.send("⚠️ Hubo un error interno. Intenta de nuevo o revisa el formato del comando.")

client.run(discord_token)
