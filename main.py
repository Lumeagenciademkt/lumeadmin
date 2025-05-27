import discord
import os

intents = discord.Intents.all()
client = discord.Client(intents=intents)

discord_token = os.getenv("DISCORD_TOKEN")

@client.event
async def on_ready():
    print(f"✅ Bot conectado como {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Comando: !canal nombre-del-canal
    if message.content.startswith("!canal "):
        nombre_canal = message.content.replace("!canal ", "").strip().replace(" ", "-").lower()
        print(f"Intentando crear canal: {nombre_canal}")
        guild = message.guild

        # Verifica si ya existe el canal
        if discord.utils.get(guild.text_channels, name=nombre_canal):
            await message.channel.send(f"⚠️ Ya existe un canal llamado #{nombre_canal}")
        else:
            await guild.create_text_channel(nombre_canal)
            await message.channel.send(f"✅ Canal creado: #{nombre_canal}")

client.run(discord_token)

