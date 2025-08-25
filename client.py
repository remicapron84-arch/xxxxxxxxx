import discord

token = "MTQwOTM5OTc0NzY5NzA0OTcwMQ.GsLIBP.JdGC-ks5UksLfqeVRp32xchH1G8oD7kgXqb47w"

client = discord.Client(intents=discord.Intents.all())

client.run(token=token)
