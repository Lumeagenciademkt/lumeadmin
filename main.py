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

# ==== Helpers ====

def extract_json(text):
    """Extrae el primer bloque JSON de un texto."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            # Validar si realmente es un JSON decodable
            json.loads(match.group(0))
            return match.group(0)
        except:
            return None
    return None

# ==== Acciones Discord ====

async def crear_canal(guild, nombre):
    if not nombre:
        return "❌ Falta el nombre del canal."
    channel_name = nombre.replace(" ", "-")[:100]
    existing = discord.utils.get(guild.text_channels, name=channel_name)
    if not existing:
        await guild.create_text_channel(channel_name)
        return f"✅ Canal creado: #{channel_name}"
    return f"⚠️ Ya existe un canal llamado #{channel_name}"

async def eliminar_canal(guild, nombre):
    if not nombre:
        return "❌ Falta el nombre del canal."
    canal = discord.utils.get(guild.text_channels, name=nombre.replace(" ", "-").lower())
    if canal:
        await canal.delete()
        return f"🗑️ Canal eliminado: #{nombre}"
    return f"❌ No encontré el canal #{nombre}"

async def enviar_mensaje(guild, canal_nombre, contenido):
    if not canal_nombre or not contenido:
        return "❌ Falta el canal o el contenido."
    canal = discord.utils.get(guild.text_channels, name=canal_nombre.replace(" ", "-").lower())
    if canal:
        await canal.send(contenido)
        return f"📨 Mensaje enviado a #{canal_nombre}"
    return f"❌ No encontré el canal #{canal_nombre}"

async def crear_categoria(guild, nombre):
    if not nombre:
        return "❌ Falta el nombre de la categoría."
    existente = discord.utils.get(guild.categories, name=nombre)
    if not existente:
        await guild.create_category(nombre)
        return f"📂 Categoría creada: {nombre}"
    return f"⚠️ Ya existe la categoría {nombre}"

async def asignar_rol(guild, miembro_nombre, rol_nombre):
    if not miembro_nombre or not rol_nombre:
        return "❌ Falta el usuario o el rol."
    miembro = discord.utils.find(lambda m: m.name == miembro_nombre or m.display_name == miembro_nombre, guild.members)
    rol = discord.utils.get(guild.roles, name=rol_nombre)
    if miembro and rol:
        await miembro.add_roles(rol)
        return f"🎭 Rol '{rol_nombre}' asignado a {miembro.mention}"
    return "❌ Usuario o rol no encontrado."

async def programar_recordatorio(message, segundos, contenido):
    if not contenido:
        await message.channel.send("❌ Falta el contenido del recordatorio.")
        return
    try:
        segundos = int(segundos)
    except:
        await message.channel.send("❌ El tiempo debe ser un número de segundos.")
        return
    await message.channel.send(f"⏳ Te recordaré eso en {segundos} segundos.")
    await asyncio.sleep(segundos)
    await message.channel.send(f"🔔 Recordatorio: {contenido}")

# ==== Discord Events ====

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
        print("🔎 Respuesta GPT:", content)  # LOG para debug

        json_block = extract_json(content)
        if json_block:
            try:
                data = json.loads(json_block)
                action = data.get("action")
                params = data.get("params", {})

                resultado = ""
                if action == "crear_canal":
                    resultado = await crear_canal(guild, params.get("nombre"))
                elif action == "eliminar_canal":
                    resultado = await eliminar_canal(guild, params.get("nombre"))
                elif action == "enviar_mensaje":
                    resultado = await enviar_mensaje(guild, params.get("canal"), params.get("contenido"))
                elif action == "crear_categoria":
                    resultado = await crear_categoria(guild, params.get("nombre"))
                elif action == "asignar_rol":
                    resultado = await asignar_rol(guild, params.get("usuario"), params.get("rol"))
                elif action == "recordatorio":
                    await programar_recordatorio(message, params.get("segundos", 60), params.get("contenido", ""))
                    return
                else:
                    resultado = "🤖 Acción no reconocida o aún no implementada."

                await message.channel.send(resultado)
                return

            except Exception as ex:
                print("❌ Error al procesar el JSON:", ex)
                await message.channel.send(f"⚠️ Error al procesar comando: {ex}")
                return

        # Si no se detecta JSON, muestra la respuesta de GPT
        await message.channel.send(content if content else "⚠️ No entendí el mensaje. ¿Puedes reformularlo?")
        return

    except Exception as e:
        print("❌ Error general:", e)
        await message.channel.send(f"⚠️ Error interno: {e}")

client.run(discord_token)

