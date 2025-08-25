import discord

token = "MTQwOTM5OTc0NzY5NzA0OTcwMQ.GsLIBP.JdGC-ks5UksLfqeVRp32xchH1G8oD7kgXqb47w"

client = discord.Client(intents=discord.Intents.all())

@client.event
async def on_message(message: discord.Message):
  if message.author.bot:
    return
  elif message.content.lower().startswith("bonjour"):
    await message.channel.send("Bonjour, c'est le bot")


@client.event
async def on_message_delete(message: discord.Message):
  await message.channel.send(f"{message.author.name} a supprimé {message.content}")


@client.event
async def on_message_edit(before: discord.Message, after: discord.Message):
  await after.channel.send(f"{before.content} est devenu {after.content}")


@client.event
async def on_ready():
  print("Le bot est prêt")


client.run(token=token)
