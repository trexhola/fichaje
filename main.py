import datetime
import discord #SOLO ES ISTALAR LA LIBERIA DE DISCORD
import json
import os

#EL BOT TIENE QUE SI UNA PERSONA ESTA FICHANDO Y EL BOT SE APAGA NO SE PIERDE EL TIEMPO QUE LLEVA

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

FICHAJES_FILE = 'fichajes.json'# ARCHIVO PARA GUARDAR LOS FICHAJES
ROL_ESPECIFICO = 'ROL ESPESIFIVO'  # Cambia esto al nombre del rol específico

def load_fichajes():
    if os.path.exists(FICHAJES_FILE):
        try:
            with open(FICHAJES_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

fichajes = load_fichajes()

def save_fichajes():
    with open(FICHAJES_FILE, 'w') as f:
        json.dump(fichajes, f)

def format_time(seconds):
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return f"{int(days)} días, {int(hours)} horas"
    elif hours > 0:
        return f"{int(hours)} horas, {int(minutes)} minutos"
    else:
        return f"{int(minutes)} minutos"

async def ensure_role_members_fichados():
    for guild in client.guilds:
        role = discord.utils.get(guild.roles, name=ROL_ESPECIFICO)
        if role is None:
            continue
        for member in guild.members:
            if role in member.roles:
                usuario_id = str(member.id)
                if usuario_id not in fichajes:
                    fichajes[usuario_id] = {'tiempo_acumulado': 0, 'entradas': []}
    save_fichajes()

@client.event
async def on_ready():
    await ensure_role_members_fichados()
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content
    author = message.author
    usuario_id = str(author.id)
    ahora = datetime.datetime.now()

    #COMANDOS DEL BOT
    if content.startswith('!entrada'):# PARA EMPESAR A FICHAR
        await handle_entrada(message, usuario_id, author.display_name, ahora)
    elif content.startswith('!salida'):# PARA DEGAR DE FICHAR
        await handle_salida(message, usuario_id, author.display_name, ahora)
    elif content.startswith('!tiempopersonal'):# PARA VER CUANTO TIEMPO LLEVA
        await handle_tiempopersonal(message, author.display_name)
    elif content.startswith('!agregarminutos'):# PARA PONER O QUITAR MINUTOS A LOS USUARIOS
        await handle_agregar_minutos(message)
    elif content.startswith('!eliminar_fichajes'):# PARA ELIMINAR EL TIEMPO DE ALGUN USUARIO
        await handle_eliminar_fichajes(message)
    elif content.startswith('!tiempogeneral'):# PARA VER EL TIEMPO DE TODOS
        await handle_tiempogeneral(message, author.display_name)
    elif content.startswith('!patrullando'):#PARA VER QUIEN ESTRA TRABAJANDO
        await handle_patrullando(message)
    elif content.startswith('!resetusuario'):# PARA RESETEAR SU TIEMPO
        await handle_resetusuario(message)
    elif content.startswith('!resetgeneral'):# ELIMINA TODOS LOS FICHAJES
        await handle_resetgeneral(message)
    elif content.startswith('!forzarsalida'):# PARA SACAR DEL FICHAJE A UNA PESONA ESPESIFICA
        await handle_forzarsalida(message)

#FUNSIONAMIENTO DEL EL COMANDO DE ENTRADA
async def handle_entrada(message, usuario_id, display_name, ahora):
    ahora_iso = ahora.isoformat()
    if usuario_id not in fichajes:
        fichajes[usuario_id] = {'tiempo_acumulado': 0, 'entradas': []}
    if 'entrada_actual' in fichajes[usuario_id]:
        await message.channel.send(f'{display_name}, ya has iniciado sesión. Utiliza !salida para registrar tu salida.')
        await message.delete()
        return
    fichajes[usuario_id]['entrada_actual'] = ahora_iso
    fichajes[usuario_id]['entradas'].append(ahora_iso)
    await send_entry_exit_embed(message.channel, 'Entrada', f'{display_name} ha comenzado a trabajar correctamente.\nActualmente hay {sum(1 for f in fichajes.values() if "entrada_actual" in f)} miembros trabajando.', ahora, color=discord.Color.green())  # Cambiado a verde
    save_fichajes()
    await message.delete()
#FUNSIONAMIENTO DEL COMANDO DE SALIDA
async def handle_salida(message, usuario_id, display_name, ahora):
    if usuario_id not in fichajes or 'entrada_actual' not in fichajes[usuario_id]:
        await message.channel.send(f'{display_name}, primero debes comenzar a trabajar usando !entrada.')
        await message.delete()
        return
    entrada_time = datetime.datetime.fromisoformat(fichajes[usuario_id]['entrada_actual'])
    duration = ahora - entrada_time
    fichajes[usuario_id]['tiempo_acumulado'] += duration.total_seconds()
    minutes = duration.total_seconds() // 60
    await send_entry_exit_embed(message.channel, 'Salida', f'{display_name} ha registrado su salida a las {ahora.strftime("%Y-%m-%d %H:%M:%S")}\nDuración: {int(minutes)} minutos.\nActualmente hay {sum(1 for f in fichajes.values() if "entrada_actual" in f) - 1} miembros trabajando.', ahora, color=discord.Color.red())  # Cambiado a rojo
    del fichajes[usuario_id]['entrada_actual']
    save_fichajes()
    await message.delete()
#FUNSIONAMIENTO DEL COMANDO DE TIEMPO PERSONAL
async def handle_tiempopersonal(message, requester_name):
    usuario_id = str(message.author.id)

    if usuario_id not in fichajes:
        await message.channel.send('No tienes fichajes registrados.')
        return

    tiempo_acumulado = fichajes[usuario_id]['tiempo_acumulado']
    if 'entrada_actual' in fichajes[usuario_id]:
        entrada_time = datetime.datetime.fromisoformat(fichajes[usuario_id]['entrada_actual'])
        tiempo_acumulado += (datetime.datetime.now() - entrada_time).total_seconds()

    if tiempo_acumulado < 60:
        await message.channel.send('No tienes suficiente tiempo trabajado registrado (menos de 1 minuto).')
        return

    formatted_time = format_time(tiempo_acumulado)
    description = f"{message.author.display_name} ha trabajado {formatted_time} en total."

    embed = discord.Embed(title='Tiempo trabajado', description=description, color=discord.Color.blue(), timestamp=datetime.datetime.now())
    embed.set_footer(text=f"Solicitado por: {requester_name}")
    await message.channel.send(embed=embed)
#FUNSIONAMIENTO DEL COMANDO DE PARA AGREGAR MINUTOS
async def handle_agregar_minutos(message):
    if len(message.mentions) != 1:
        await message.channel.send('Debes mencionar a un usuario para agregar o quitar minutos.')
        await message.delete()
        return
    member = message.mentions[0]
    member_id = str(member.id)
    args = message.content.split()
    if len(args) < 3:
        await message.channel.send('Debes especificar la cantidad de minutos a agregar o quitar.')
        await message.delete()
        return
    try:
        minutos = int(args[2])
    except ValueError:
        await message.channel.send('El valor de minutos debe ser un número entero.')
        await message.delete()
        return
    if member_id in fichajes:
        fichajes[member_id]['tiempo_acumulado'] += minutos * 60  # Convierte minutos a segundos
        save_fichajes()
        operacion = "agregado" if minutos >= 0 else "quitado"
        await message.channel.send(f'Se han {operacion} {abs(minutos)} minutos a {member.display_name}.')
    else:
        await message.channel.send(f'{member.display_name} no tiene fichajes registrados.')
    await message.delete()
#FUNSIONAMIENTO DEL COMANDO DE ELIMINASION EL TIEMPOD DE ALGUN USUARIO
async def handle_eliminar_fichajes(message):
    if len(message.mentions) != 1:
        await message.channel.send('Debes mencionar a un usuario para eliminar sus fichajes.')
        await message.delete()
        return
    member = message.mentions[0]
    member_id = str(member.id)
    if member_id in fichajes:
        del fichajes[member_id]
        save_fichajes()
        await message.channel.send(f'Se han eliminado todos los fichajes de {member.display_name}.')
    else:
        await message.channel.send(f'{member.display_name} no tiene fichajes registrados.')
    await message.delete()
#FUNSIONAMIENTO DEL COMANDO PARA VER TODOS LOS TIEMPOS DE LOS USUARIOS
async def handle_tiempogeneral(message, requester_name):
    if not fichajes:
        await message.channel.send('No hay fichajes registrados.')
        return

    description = "Usuario                                  Duración\n"
    sorted_fichajes = sorted(fichajes.items(), key=lambda x: x[1]['tiempo_acumulado'], reverse=True)
    for usuario_id, data in sorted_fichajes:
        tiempo_acumulado = data['tiempo_acumulado']
        if tiempo_acumulado < 60:
            continue
        user = await client.fetch_user(int(usuario_id))
        display_name = user.display_name
        member = message.guild.get_member(int(usuario_id))
        if member:
            nickname = member.nick
            if nickname:
                display_name = nickname
        formatted_time = format_time(tiempo_acumulado)
        description += f"{display_name:<30} {formatted_time}\n"

    if description == "Usuario                                Duración\n":
        description = "No hay usuarios con más de 1 minuto registrado."

    embed = discord.Embed(title='Tiempo trabajado', description=description, color=discord.Color.blue(), timestamp=datetime.datetime.now())
    embed.set_footer(text=f"Solicitado por: {requester_name}")
    await message.channel.send(embed=embed)
#FUNSIONAMIENTO DEL COMANDO PARA VER QUIE ESA TRABAJANDO
async def handle_patrullando(message):
    patrullando = [usuario_id for usuario_id, data in fichajes.items() if 'entrada_actual' in data]
    if not patrullando:
        await message.channel.send('No hay miembros fichando en este momento.')
        return

    description = "\n".join([message.guild.get_member(int(id)).nick or (await client.fetch_user(int(id))).display_name for id in patrullando])
    embed = discord.Embed(title='Miembros fichando', description=description, color=discord.Color.blue(), timestamp=datetime.datetime.now())
    embed.set_footer(text=" ")
    await message.channel.send(embed=embed)
#FUNSIONAMIENTO DEL COMANDO PARA ELIMINAR EL TIEMPO DE UNA PERSONA ESPASIFICA
async def handle_resetusuario(message):
    if len(message.mentions) != 1:
        await message.channel.send('Debes mencionar a un usuario para resetear sus fichajes.')
        await message.delete()
        return
    member = message.mentions[0]
    member_id = str(member.id)
    if member_id in fichajes:
        fichajes[member_id] = {'tiempo_acumulado': 0, 'entradas': []}
        save_fichajes()
        await message.channel.send(f'Se han reseteado los fichajes de {member.display_name}.')
    else:
        await message.channel.send(f'{member.display_name} no tiene fichajes registrados.')
    await message.delete()
#FUNSIONAMIENTO DEL COMANDO PAR ELIMINAR TODOS LOS TIEMPOS
async def handle_resetgeneral(message):
    fichajes.clear()
    save_fichajes()
    await ensure_role_members_fichados()
    await message.channel.send('Se han reseteado todos los fichajes.')
    await message.delete()
#FUNSIONAMIENTO DEL COMANDO PARA QUE SIEREN FICHAJE SI DEJARON ABIRTO
async def handle_forzarsalida(message):
    if len(message.mentions) != 1:
        await message.channel.send('Debes mencionar a un usuario para forzar su salida.')
        await message.delete()
        return
    member = message.mentions[0]
    member_id = str(member.id)
    ahora = datetime.datetime.now()

    if member_id not in fichajes or 'entrada_actual' not in fichajes[member_id]:
        await message.channel.send(f'{member.display_name} no tiene una sesión activa.')
        await message.delete()
        return

    entrada_time = datetime.datetime.fromisoformat(fichajes[member_id]['entrada_actual'])
    duration = ahora - entrada_time
    fichajes[member_id]['tiempo_acumulado'] += duration.total_seconds()
    minutes = duration.total_seconds() // 60
    await send_entry_exit_embed(message.channel, 'Salida Forzada', f'{member.display_name} ha sido forzadamente registrado su salida a las {ahora.strftime("%Y-%m-%d %H:%M:%S")}\nDuración: {int(minutes)} minutos.\nActualmente hay {sum(1 for f in fichajes.values() if "entrada_actual" in f) - 1} miembros trabajando.', ahora, color=discord.Color.red())
    del fichajes[member_id]['entrada_actual']
    save_fichajes()
    await message.delete()

async def send_entry_exit_embed(channel, title, description, timestamp, color):
    embed = discord.Embed(title=title, description=description, color=color, timestamp=timestamp)
    embed.set_footer(text=" ")
    await channel.send(embed=embed)
#PARA INISIAR BOT
client.run('token del Bot')