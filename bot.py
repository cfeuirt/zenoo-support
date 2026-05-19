import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import os
from datetime import datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

GUILD_ID = 1506035311048917052
CATEGORY_NAME = "Besoin d'aide 🆘"
STAFF_ROLES = ['Fondateur', 'Modérateur', 'Staff']
LOGS_CHANNEL = 'logs-tickets'
MOD_FILE = 'mods.json'
TICKETS_FILE = 'tickets.json'

def load_mods():
    if os.path.exists(MOD_FILE):
        with open(MOD_FILE, 'r') as f:
            return json.load(f)
    return {}

def load_tickets():
    if os.path.exists(TICKETS_FILE):
        with open(TICKETS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_tickets(tickets):
    with open(TICKETS_FILE, 'w') as f:
        json.dump(tickets, f)

def is_staff(member):
    return any(role.name in STAFF_ROLES for role in member.roles)

class TicketButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='📩 Créer un ticket', style=discord.ButtonStyle.green, custom_id='create_ticket')
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        existing = discord.utils.get(guild.channels, name=f'ticket-{interaction.user.name.lower()}')
        if existing:
            await interaction.response.send_message(f'❌ Tu as déjà un ticket ouvert : {existing.mention}', ephemeral=True)
            return
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for role_name in STAFF_ROLES:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        channel = await guild.create_text_channel(
            f'ticket-{interaction.user.name.lower()}',
            category=category,
            overwrites=overwrites
        )
        tickets = load_tickets()
        tickets[str(interaction.user.id)] = str(channel.id)
        save_tickets(tickets)
        await channel.send(
            f'👋 Bonjour {interaction.user.mention} ! Un membre du staff va vous répondre.\n\nUtilisez les boutons ci-dessous :',
            view=CombinedView()
        )
        try:
            await interaction.user.send(f'✅ Ton ticket a été créé ! Tu peux répondre directement ici en MP et le staff te verra dans le salon.')
        except:
            pass
        await interaction.response.send_message(f'✅ Ticket créé : {channel.mention}', ephemeral=True)

class CombinedView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='✅ Claim', style=discord.ButtonStyle.blurple, custom_id='claim_ticket')
    async def claim_ticket(self, interaction: discord.Interaction, button: Button):
        if not is_staff(interaction.user) and not any(role.name == "Fondateur" for role in interaction.user.roles):
            await interaction.response.send_message('❌ Tu n\'as pas la permission.', ephemeral=True)
            return
        mods = load_mods()
        numero = mods.get(str(interaction.user.id))
        if numero:
            await interaction.response.send_message(f'Le modérateur {numero} a pris votre ticket.')
        else:
            await interaction.response.send_message(f'{interaction.user.display_name} a pris votre ticket.')

    @discord.ui.button(label='🔒 Fermer', style=discord.ButtonStyle.red, custom_id='close_ticket')
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        if not is_staff(interaction.user) and not any(role.name == "Fondateur" for role in interaction.user.roles):
            await interaction.response.send_message('❌ Tu n\'as pas la permission.', ephemeral=True)
            return
        logs_channel = discord.utils.get(interaction.guild.channels, name=LOGS_CHANNEL)
        messages = []
        async for message in interaction.channel.history(limit=200, oldest_first=True):
            messages.append(f'[{message.created_at.strftime("%H:%M:%S")}] {message.author.name}: {message.content}')
        logs_text = '\n'.join(messages)
        if logs_channel:
            embed = discord.Embed(
                title=f'📜 Logs - {interaction.channel.name}',
                description=f'```{logs_text[:3900]}```',
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text=f'Fermé par {interaction.user.name}')
            await logs_channel.send(embed=embed)
        tickets = load_tickets()
        for user_id, channel_id in list(tickets.items()):
            if channel_id == str(interaction.channel.id):
                del tickets[user_id]
                save_tickets(tickets)
                try:
                    user = await bot.fetch_user(int(user_id))
                    await user.send('🔒 Votre ticket a été fermé.')
                except:
                    pass
                break
        await interaction.response.send_message('🔒 Fermeture du ticket...')
        await interaction.channel.delete()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if isinstance(message.channel, discord.DMChannel):
        tickets = load_tickets()
        channel_id = tickets.get(str(message.author.id))
        if channel_id:
            guild = bot.get_guild(GUILD_ID)
            channel = guild.get_channel(int(channel_id))
            if channel:
                embed = discord.Embed(
                    description=message.content,
                    color=discord.Color.green()
                )
                embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
                await channel.send(embed=embed)
        return
    if isinstance(message.channel, discord.TextChannel):
        if message.channel.category and message.channel.category.name == CATEGORY_NAME:
            if message.author.bot:
                return
            tickets = load_tickets()
            for user_id, channel_id in tickets.items():
                if channel_id == str(message.channel.id):
                    if str(message.author.id) != user_id:
                        try:
                            user = await bot.fetch_user(int(user_id))
                            embed = discord.Embed(
                                description=message.content,
                                color=discord.Color.blue()
                            )
                            embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
                            await user.send(embed=embed)
                        except:
                            pass
                    break
    await bot.process_commands(message)

@bot.event
async def on_ready():
    bot.add_view(TicketButton())
    bot.add_view(CombinedView())
    print(f'Bot tickets connecte : {bot.user}')

@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    embed = discord.Embed(
        title='🎫 Support Zenoo RP',
        description='Clique sur le bouton ci-dessous pour ouvrir un ticket.\nNotre staff vous répondra dès que possible.',
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketButton())
    await ctx.message.delete()

TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)
